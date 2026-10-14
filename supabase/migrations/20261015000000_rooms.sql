-- =============================================================================
-- 버섯마을: 로그인 없는 채팅방 (사이클 4)
-- 마이그레이션: 20261015000000_rooms.sql
--
-- 정본: docs/ARCHITECTURE.md 결정 3~6, "데이터 모델 (사이클 4)", "알려진 한계".
--
--  - 익명 로그인(auth.signInAnonymously) 사용자 = authenticated 역할 + auth.uid().
--  - 테이블: rooms, room_members, room_messages, room_join_failures(비밀번호 실패 기록).
--  - 클라이언트는 테이블에 직접 접근하지 못한다(select 포함). 모든 읽기/쓰기는
--    security definer RPC로만: list_rooms, create_room, join_room, leave_room,
--    heartbeat, recent_messages, send_message.
--  - 채팅은 send_message가 저장 후 realtime.send로 비공개 채널 room:<id>에 직접 보낸다.
--  - realtime.messages RLS: 해당 방 멤버만 room:<id> 채널 수신/송신(broadcast, presence).
--
-- [실행 방법]
-- SQL Editor에 파일 전체를 한 번에 붙여넣고 Run (단일 트랜잭션으로 실행됨).
-- CLI: supabase db push. psql: psql -1 -f <파일>.
-- begin/commit은 넣지 않는다(기존 마이그레이션과 같은 이유).
--
-- [시간 상수] (바꾸려면 새 마이그레이션에서 함수를 교체)
--  ACTIVE      60초   : last_seen_at이 이 안이면 "활성 멤버"(인원 수, 닉네임 중복 판정)
--  MEMBER_TTL  10분   : last_seen_at이 이 안이면 "유효 멤버"(재접속 시 비밀번호 생략,
--                       채팅 읽기/쓰기, Realtime 채널 접근). 지나면 멤버 행은 무효이며
--                       join_room이 기회가 될 때 삭제한다 → 다시 비밀번호 필요.
--  ROOM_EXPIRE 30분   : 활성 멤버 0명으로 30분 → 만료. 판정식은
--                       last_active_at < now()-30분 이고 last_seen_at >= now()-30분 인
--                       멤버가 없음 (30분 > 60초이므로 "활성 0명 상태로 30분 경과"와 같다).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 0. 사이클 1~3 정리 (배포 전, 데이터 없음)
-- cascade 없이 지운다. 예상 못 한 의존 객체가 있으면 실패하고 전체가 롤백된다.
-- -----------------------------------------------------------------------------
drop function if exists public.is_nickname_taken(text);
drop table if exists public.characters;


-- -----------------------------------------------------------------------------
-- 1. 확장
-- Supabase에서는 pgcrypto가 이미 extensions 스키마에 설치되어 있다(no-op).
-- 함수 안에서는 search_path = '' 이므로 extensions.crypt / extensions.gen_salt로 호출한다.
-- -----------------------------------------------------------------------------
create extension if not exists pgcrypto with schema extensions;


-- -----------------------------------------------------------------------------
-- 2. 내부 헬퍼 스키마
-- PostgREST(Data API)에 노출되지 않는 스키마. RPC로 직접 호출할 수 없다.
-- authenticated에는 Realtime 정책이 쓰는 can_access_room_topic 실행 권한만 준다.
-- -----------------------------------------------------------------------------
create schema if not exists app_private;
revoke all on schema app_private from public;
grant usage on schema app_private to authenticated;


-- 앞뒤 공백 제거. JS String.prototype.trim과 비슷하게 일반 공백/탭/개행과
-- NBSP(U+00A0), 전각 공백(U+3000), BOM(U+FEFF)을 제거한다.
create or replace function app_private.trim_ws(p text)
returns text
language sql
immutable
set search_path = ''
as $$
  select pg_catalog.regexp_replace(
    p,
    '^[[:space:] 　﻿]+|[[:space:] 　﻿]+$',
    '',
    'g'
  );
$$;

-- 현재 사용자 uid. 없으면(토큰 없음/서비스 키) NOT_MEMBER.
create or replace function app_private.require_uid()
returns uuid
language plpgsql
stable
set search_path = ''
as $$
declare
  v uuid := auth.uid();
begin
  if v is null then
    raise exception using message = 'NOT_MEMBER';
  end if;
  return v;
end;
$$;

-- -----------------------------------------------------------------------------
-- 3. 테이블
-- -----------------------------------------------------------------------------
create table public.rooms (
  id             uuid        not null default gen_random_uuid()
                 constraint rooms_pkey primary key,
  -- 1~24자, 앞뒤 공백 없음(RPC가 trim 후 저장), 제어문자 금지.
  name           text        not null
                 constraint rooms_name_format check (
                   char_length(name) between 1 and 24
                   and name !~ '[[:cntrl:]]'
                   and name !~ '^[[:space:] 　﻿]'
                   and name !~ '[[:space:] 　﻿]$'
                 ),
  -- bcrypt 해시. null = 공개 방. 클라이언트는 이 컬럼을 어떤 경로로도 읽을 수 없다.
  password_hash  text
                 constraint rooms_password_hash_format check (password_hash is null or password_hash like '$2%'),
  locked         boolean     generated always as (password_hash is not null) stored,
  created_by     uuid        not null references auth.users (id) on delete cascade,
  created_at     timestamptz not null default now(),
  last_active_at timestamptz not null default now()
);

create index rooms_created_by_idx on public.rooms (created_by);

comment on table  public.rooms is '채팅방. 직접 접근 불가, RPC 전용. 활성 0명 30분이면 만료.';
comment on column public.rooms.password_hash is 'bcrypt(pgcrypto). null=공개. 클라이언트 읽기 불가.';


create table public.room_members (
  room_id      uuid        not null references public.rooms (id) on delete cascade,
  user_id      uuid        not null references auth.users (id) on delete cascade,
  nickname     text        not null
               constraint room_members_nickname_format
               check (nickname ~ '^[가-힣A-Za-z0-9]{2,12}$'),
  joined_at    timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  constraint room_members_pkey primary key (room_id, user_id)
);

create index room_members_room_seen_idx on public.room_members (room_id, last_seen_at);

-- 같은 방 안에서 닉네임 중복 금지(대소문자 무시)의 최종 방어선.
-- "활성 멤버 사이에서만" 금지가 규칙이므로, join_room은 같은 닉네임을 가진 비활성
-- (60초 초과) 멤버 행을 먼저 지운 뒤 입장시킨다.
create unique index room_members_room_nick_key on public.room_members (room_id, lower(nickname));

comment on table public.room_members is '방 멤버. 활성=last_seen_at 60초 이내, 유효=10분 이내.';


create table public.room_messages (
  id         bigint      generated always as identity
             constraint room_messages_pkey primary key,
  room_id    uuid        not null references public.rooms (id) on delete cascade,
  user_id    uuid        not null references auth.users (id) on delete cascade,
  nickname   text        not null
             constraint room_messages_nickname_format
             check (nickname ~ '^[가-힣A-Za-z0-9]{2,12}$'),
  text       text        not null
             constraint room_messages_text_format
             check (char_length(text) between 1 and 80 and text !~ '[[:cntrl:]]'),
  created_at timestamptz not null default now()
);

create index room_messages_room_id_idx on public.room_messages (room_id, id desc);
create index room_messages_user_created_idx on public.room_messages (user_id, created_at desc);

comment on table public.room_messages is '방 채팅. 방당 최근 50개만 유지. 멤버만 RPC로 읽음.';


-- 잠금 방 비밀번호 실패 기록(사용자당 방당 1분 5회 제한). 10분 지난 기록은 정리.
create table public.room_join_failures (
  id         bigint      generated always as identity
             constraint room_join_failures_pkey primary key,
  room_id    uuid        not null references public.rooms (id) on delete cascade,
  user_id    uuid        not null references auth.users (id) on delete cascade,
  created_at timestamptz not null default now()
);

create index room_join_failures_lookup_idx on public.room_join_failures (user_id, room_id, created_at);
create index room_join_failures_created_idx on public.room_join_failures (created_at);


-- -----------------------------------------------------------------------------
-- 3.1 테이블을 참조하는 내부 헬퍼 (sql 함수는 생성 시 본문을 검사하므로 테이블 뒤에 둔다)
-- -----------------------------------------------------------------------------
-- 방이 살아 있는가(만료 아님). p_last_active = rooms.last_active_at.
create or replace function app_private.room_alive(p_room_id uuid, p_last_active timestamptz)
returns boolean
language sql
stable
set search_path = ''
as $$
  select p_last_active >= now() - interval '30 minutes'
      or exists (
           select 1
           from public.room_members m
           where m.room_id = p_room_id
             and m.last_seen_at >= now() - interval '30 minutes'
         );
$$;

-- 유효 멤버(MEMBER_TTL 10분 이내 행 존재)인가.
create or replace function app_private.is_member(p_room_id uuid, p_user_id uuid)
returns boolean
language sql
stable
set search_path = ''
as $$
  select exists (
    select 1
    from public.room_members m
    where m.room_id = p_room_id
      and m.user_id = p_user_id
      and m.last_seen_at > now() - interval '10 minutes'
  );
$$;


-- -----------------------------------------------------------------------------
-- 4. 권한 + RLS
--
-- Supabase는 public 스키마 새 테이블/시퀀스에 anon/authenticated 전체 권한을 기본 부여한다.
-- 모두 회수한다. select도 주지 않는다(password_hash 보호, 읽기는 RPC로만).
-- RLS를 켜고, 의도를 명시하는 "직접 접근 금지" 정책(using false)을 둔다.
-- (권한이 없어 정책까지 가지 않지만, 누가 실수로 grant해도 행이 보이지 않게 하는 이중 방어)
-- service_role/postgres는 관리용으로 그대로 둔다.
-- -----------------------------------------------------------------------------
revoke all on table public.rooms              from public, anon, authenticated;
revoke all on table public.room_members       from public, anon, authenticated;
revoke all on table public.room_messages      from public, anon, authenticated;
revoke all on table public.room_join_failures from public, anon, authenticated;
revoke all on sequence public.room_messages_id_seq      from public, anon, authenticated;
revoke all on sequence public.room_join_failures_id_seq from public, anon, authenticated;

alter table public.rooms              enable row level security;
alter table public.room_members       enable row level security;
alter table public.room_messages      enable row level security;
alter table public.room_join_failures enable row level security;

create policy rooms_no_direct_access on public.rooms
  as restrictive for all to anon, authenticated using (false) with check (false);
create policy room_members_no_direct_access on public.room_members
  as restrictive for all to anon, authenticated using (false) with check (false);
create policy room_messages_no_direct_access on public.room_messages
  as restrictive for all to anon, authenticated using (false) with check (false);
create policy room_join_failures_no_direct_access on public.room_join_failures
  as restrictive for all to anon, authenticated using (false) with check (false);


-- -----------------------------------------------------------------------------
-- 5. RPC
-- 모두 security definer + search_path = ''. 오류는 raise exception using message = '<코드>'.
-- (예외: join_room의 WRONG_PASSWORD는 반환값. 아래 join_room 주석 참고)
-- -----------------------------------------------------------------------------

-- 5.1 list_rooms() -----------------------------------------------------------
-- 살아 있는 방 최대 100개. 인원(활성 60초) 많은 순 → 최근 활동 순.
-- 만료 방은 제외하고 기회적으로 삭제한다(다른 트랜잭션이 잠근 방은 건너뜀).
create or replace function public.list_rooms()
returns table (id uuid, name text, locked boolean, members int, created_at timestamptz)
language plpgsql
volatile
security definer
set search_path = ''
as $$
#variable_conflict use_column
begin
  perform app_private.require_uid();

  delete from public.rooms d
  where d.id in (
    select r.id
    from public.rooms r
    where not app_private.room_alive(r.id, r.last_active_at)
    for update skip locked
  );

  return query
  select s.id, s.name, s.locked, s.members, s.created_at
  from (
    select
      r.id, r.name, r.locked, r.created_at,
      (select count(*)::int
         from public.room_members m
        where m.room_id = r.id
          and m.last_seen_at > now() - interval '60 seconds') as members,
      greatest(
        r.last_active_at,
        (select max(m.last_seen_at) from public.room_members m where m.room_id = r.id)
      ) as last_act
    from public.rooms r
    where app_private.room_alive(r.id, r.last_active_at)
  ) s
  order by s.members desc, s.last_act desc, s.created_at desc
  limit 100;
end;
$$;


-- 5.2 create_room(p_name, p_password, p_nickname) → uuid ---------------------
create or replace function public.create_room(p_name text, p_password text, p_nickname text)
returns uuid
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid   uuid := app_private.require_uid();
  v_name  text := app_private.trim_ws(p_name);
  v_hash  text;
  v_count int;
  v_id    uuid;
begin
  if v_name is null or char_length(v_name) not between 1 and 24 or v_name ~ '[[:cntrl:]]' then
    raise exception using message = 'ROOM_NAME_FORMAT';
  end if;

  if p_password is null or p_password = '' then
    v_hash := null;
  elsif char_length(p_password) between 4 and 32 then
    v_hash := extensions.crypt(p_password, extensions.gen_salt('bf', 8));
  else
    raise exception using message = 'PASSWORD_FORMAT';
  end if;

  if p_nickname is null or p_nickname !~ '^[가-힣A-Za-z0-9]{2,12}$' then
    raise exception using message = 'NICK_FORMAT';
  end if;

  -- 같은 사용자의 동시 생성을 직렬화(3개 제한 race 방지).
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('create_room:' || v_uid::text, 0));

  select count(*) into v_count
  from public.rooms r
  where r.created_by = v_uid
    and app_private.room_alive(r.id, r.last_active_at);

  if v_count >= 3 then
    raise exception using message = 'TOO_MANY_ROOMS';
  end if;

  insert into public.rooms (name, password_hash, created_by)
  values (v_name, v_hash, v_uid)
  returning public.rooms.id into v_id;

  insert into public.room_members (room_id, user_id, nickname)
  values (v_id, v_uid, p_nickname);

  return v_id;
end;
$$;


-- 5.3 join_room(p_room_id, p_password, p_nickname) → text --------------------
-- 반환: 'OK' | 'WRONG_PASSWORD'
--
-- [WRONG_PASSWORD를 예외가 아닌 반환값으로 주는 이유]
-- 실패 시도 제한을 하려면 실패 기록이 커밋되어야 한다. RPC가 예외를 던지면 그 호출의
-- 트랜잭션 전체가 롤백되어 기록도 사라진다(Postgres에는 자율 트랜잭션이 없다).
-- 그래서 비밀번호 불일치만 정상 반환 'WRONG_PASSWORD'로 끝내 기록을 커밋한다.
-- 나머지 오류(ROOM_NOT_FOUND, RATE_LIMITED, ROOM_FULL, NICK_TAKEN, NICK_FORMAT)는 예외.
--
-- [재접속] 본인의 유효 멤버 행(last_seen_at 10분 이내)이 있으면 비밀번호 검사를 생략한다.
-- leave_room을 호출했거나 10분 넘게 하트비트가 없었으면 다시 비밀번호가 필요하다.
--
-- [동시성] 방 행을 for update로 잠가 같은 방의 입장을 직렬화한다(21번째 입장,
-- 같은 닉네임 동시 입장). unique 인덱스 room_members_room_nick_key가 최종 방어선.
create or replace function public.join_room(p_room_id uuid, p_password text, p_nickname text)
returns text
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid       uuid := app_private.require_uid();
  v_room      public.rooms%rowtype;
  v_is_member boolean;
  v_fails     int;
  v_active    int;
begin
  if p_nickname is null or p_nickname !~ '^[가-힣A-Za-z0-9]{2,12}$' then
    raise exception using message = 'NICK_FORMAT';
  end if;

  select * into v_room
  from public.rooms r
  where r.id = p_room_id
  for update;

  if not found or not app_private.room_alive(v_room.id, v_room.last_active_at) then
    raise exception using message = 'ROOM_NOT_FOUND';
  end if;

  -- 무효(10분 초과) 멤버 행 정리. 본인 행이 무효였다면 여기서 지워져 비밀번호가 필요해진다.
  delete from public.room_members m
  where m.room_id = p_room_id
    and m.last_seen_at <= now() - interval '10 minutes';

  -- 오래된 실패 기록 정리(전역).
  delete from public.room_join_failures f
  where f.created_at < now() - interval '10 minutes';

  v_is_member := exists (
    select 1 from public.room_members m
    where m.room_id = p_room_id and m.user_id = v_uid
  );

  if v_room.password_hash is not null and not v_is_member then
    select count(*) into v_fails
    from public.room_join_failures f
    where f.user_id = v_uid
      and f.room_id = p_room_id
      and f.created_at > now() - interval '1 minute';

    if v_fails >= 5 then
      raise exception using message = 'RATE_LIMITED';
    end if;

    if p_password is null or p_password = '' then
      -- 비밀번호 미입력(예: 새로고침 재입장인데 멤버 행이 만료됨). 추측 시도가 아니므로 기록하지 않는다.
      return 'WRONG_PASSWORD';
    end if;

    if extensions.crypt(p_password, v_room.password_hash) <> v_room.password_hash then
      insert into public.room_join_failures (room_id, user_id) values (p_room_id, v_uid);
      return 'WRONG_PASSWORD';
    end if;
  end if;

  select count(*) into v_active
  from public.room_members m
  where m.room_id = p_room_id
    and m.user_id <> v_uid
    and m.last_seen_at > now() - interval '60 seconds';

  if v_active >= 20 then
    raise exception using message = 'ROOM_FULL';
  end if;

  if exists (
    select 1 from public.room_members m
    where m.room_id = p_room_id
      and m.user_id <> v_uid
      and m.last_seen_at > now() - interval '60 seconds'
      and lower(m.nickname) = lower(p_nickname)
  ) then
    raise exception using message = 'NICK_TAKEN';
  end if;

  -- 같은 닉네임의 비활성 멤버 행은 닉네임을 내준다(행 삭제 → 그 사용자는 재입장 시 비밀번호 필요).
  delete from public.room_members m
  where m.room_id = p_room_id
    and m.user_id <> v_uid
    and lower(m.nickname) = lower(p_nickname);

  begin
    insert into public.room_members as m (room_id, user_id, nickname)
    values (p_room_id, v_uid, p_nickname)
    on conflict (room_id, user_id)
    do update set nickname = excluded.nickname, last_seen_at = now();
  exception
    when unique_violation then
      raise exception using message = 'NICK_TAKEN';
  end;

  update public.rooms r set last_active_at = now() where r.id = p_room_id;

  return 'OK';
end;
$$;


-- 5.4 leave_room(p_room_id) --------------------------------------------------
-- 멤버 행 삭제. 멤버가 아니거나 방이 없어도 오류 없이 끝난다(멱등).
create or replace function public.leave_room(p_room_id uuid)
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid uuid := app_private.require_uid();
begin
  delete from public.room_members m
  where m.room_id = p_room_id and m.user_id = v_uid;

  if found then
    update public.rooms r set last_active_at = now() where r.id = p_room_id;
  end if;
end;
$$;


-- 5.5 heartbeat(p_room_id) ---------------------------------------------------
-- 20초마다 호출. 유효 멤버 행이 없으면 NOT_MEMBER(→ 클라이언트는 join_room 재시도 또는 로비).
-- 비활성(60초 초과) 상태에서 돌아온 경우: 그 사이 다른 사람이 들어와 활성 인원(본인 제외)이
-- 20명 이상이면 NOT_MEMBER(→ join_room이 ROOM_FULL을 알려 준다). 정원 초과 부활 방지.
create or replace function public.heartbeat(p_room_id uuid)
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid       uuid := app_private.require_uid();
  v_last_seen timestamptz;
begin
  select m.last_seen_at into v_last_seen
  from public.room_members m
  where m.room_id = p_room_id
    and m.user_id = v_uid
    and m.last_seen_at > now() - interval '10 minutes';

  if not found then
    raise exception using message = 'NOT_MEMBER';
  end if;

  if v_last_seen <= now() - interval '60 seconds' then
    -- join_room과 같은 잠금으로 직렬화한 뒤 정원 확인.
    perform 1 from public.rooms r where r.id = p_room_id for update;
    if (select count(*)
          from public.room_members m
         where m.room_id = p_room_id
           and m.user_id <> v_uid
           and m.last_seen_at > now() - interval '60 seconds') >= 20 then
      raise exception using message = 'NOT_MEMBER';
    end if;
  end if;

  update public.room_members m
     set last_seen_at = now()
   where m.room_id = p_room_id
     and m.user_id = v_uid;

  if not found then
    raise exception using message = 'NOT_MEMBER';
  end if;
end;
$$;


-- 5.6 recent_messages(p_room_id) → 최근 50개, 오래된 것부터 -------------------
create or replace function public.recent_messages(p_room_id uuid)
returns table (id bigint, user_id uuid, nickname text, text text, created_at timestamptz)
language plpgsql
stable
security definer
set search_path = ''
as $$
#variable_conflict use_column
declare
  v_uid uuid := app_private.require_uid();
begin
  if not app_private.is_member(p_room_id, v_uid) then
    raise exception using message = 'NOT_MEMBER';
  end if;

  return query
  select x.id, x.user_id, x.nickname, x.text, x.created_at
  from (
    select rm.id, rm.user_id, rm.nickname, rm.text, rm.created_at
    from public.room_messages rm
    where rm.room_id = p_room_id
    order by rm.id desc
    limit 50
  ) x
  order by x.id asc;
end;
$$;


-- 5.7 send_message(p_room_id, p_text) → jsonb { id, user_id, nickname, text, created_at }
-- 저장 후 같은 객체를 비공개 채널 room:<id>에 broadcast 이벤트 'chat'으로 보낸다.
-- nickname은 멤버 행 값(클라이언트 값 아님). 사용자당 1초 1회. 방당 50개 유지.
create or replace function public.send_message(p_room_id uuid, p_text text)
returns jsonb
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := app_private.require_uid();
  v_text    text := app_private.trim_ws(p_text);
  v_nick    text;
  v_msg     public.room_messages%rowtype;
  v_payload jsonb;
  v_cutoff  bigint;
begin
  -- 같은 사용자의 동시 전송을 직렬화(1초 제한 race 방지).
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('send_message:' || v_uid::text, 0));

  -- 유효 멤버의 닉네임(서버 값). last_seen_at은 heartbeat만 갱신한다.
  select m.nickname into v_nick
  from public.room_members m
  where m.room_id = p_room_id
    and m.user_id = v_uid
    and m.last_seen_at > now() - interval '10 minutes';

  if v_nick is null then
    raise exception using message = 'NOT_MEMBER';
  end if;

  if v_text is null or char_length(v_text) not between 1 and 80 or v_text ~ '[[:cntrl:]]' then
    raise exception using message = 'TEXT_FORMAT';
  end if;

  if exists (
    select 1 from public.room_messages rm
    where rm.user_id = v_uid
      and rm.created_at > now() - interval '1 second'
  ) then
    raise exception using message = 'RATE_LIMITED';
  end if;

  insert into public.room_messages (room_id, user_id, nickname, text)
  values (p_room_id, v_uid, v_nick, v_text)
  returning * into v_msg;

  -- 방당 최근 50개만 유지.
  select rm.id into v_cutoff
  from public.room_messages rm
  where rm.room_id = p_room_id
  order by rm.id desc
  offset 49
  limit 1;

  if v_cutoff is not null then
    delete from public.room_messages rm
    where rm.room_id = p_room_id and rm.id < v_cutoff;
  end if;

  v_payload := pg_catalog.jsonb_build_object(
    'id',         v_msg.id,
    'user_id',    v_msg.user_id,
    'nickname',   v_msg.nickname,
    'text',       v_msg.text,
    'created_at', v_msg.created_at
  );

  -- Supabase realtime.send(payload jsonb, event text, topic text, private boolean).
  -- 내부에서 realtime.messages에 insert하며, 실패해도 예외를 삼키고 로그만 남긴다
  -- (그래서 전송 실패가 메시지 저장을 롤백하지 않는다).
  perform realtime.send(v_payload, 'chat', 'room:' || p_room_id::text, true);

  return v_payload;
end;
$$;


-- -----------------------------------------------------------------------------
-- 6. 함수 권한
-- Supabase는 새 함수에 anon/authenticated 실행 권한을 기본 부여한다. 회수 후 필요한 것만.
-- -----------------------------------------------------------------------------
revoke all on function app_private.trim_ws(text)                    from public, anon, authenticated;
revoke all on function app_private.require_uid()                    from public, anon, authenticated;
revoke all on function app_private.room_alive(uuid, timestamptz)    from public, anon, authenticated;
revoke all on function app_private.is_member(uuid, uuid)            from public, anon, authenticated;

revoke all on function public.list_rooms()                          from public, anon;
revoke all on function public.create_room(text, text, text)         from public, anon;
revoke all on function public.join_room(uuid, text, text)           from public, anon;
revoke all on function public.leave_room(uuid)                      from public, anon;
revoke all on function public.heartbeat(uuid)                       from public, anon;
revoke all on function public.recent_messages(uuid)                 from public, anon;
revoke all on function public.send_message(uuid, text)              from public, anon;

grant execute on function public.list_rooms()                       to authenticated;
grant execute on function public.create_room(text, text, text)      to authenticated;
grant execute on function public.join_room(uuid, text, text)        to authenticated;
grant execute on function public.leave_room(uuid)                   to authenticated;
grant execute on function public.heartbeat(uuid)                    to authenticated;
grant execute on function public.recent_messages(uuid)              to authenticated;
grant execute on function public.send_message(uuid, text)           to authenticated;


-- -----------------------------------------------------------------------------
-- 7. Realtime Authorization (비공개 채널 room:<room_id>)
--
-- 정책은 authenticated 역할로 평가된다. authenticated는 room_members를 읽을 권한이 없으므로
-- security definer 헬퍼로 멤버 여부를 판정한다.
-- Realtime은 채널 join(구독) 시와 새 JWT 전달 시에만 정책을 검사하고 연결 동안 결과를
-- 캐시한다(즉시 강퇴 아님 — ARCHITECTURE "알려진 한계").
-- -----------------------------------------------------------------------------
create or replace function app_private.can_access_room_topic(p_topic text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null
     or p_topic is null
     or p_topic !~ '^room:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return false;
  end if;
  return app_private.is_member(substr(p_topic, 6)::uuid, v_uid);
end;
$$;

revoke all on function app_private.can_access_room_topic(text) from public, anon, authenticated;
grant execute on function app_private.can_access_room_topic(text) to authenticated;

drop policy if exists mushroom_room_members_receive on realtime.messages;
drop policy if exists mushroom_room_members_send    on realtime.messages;

-- 수신(구독, presence 상태 수신)
create policy mushroom_room_members_receive
  on realtime.messages
  for select
  to authenticated
  using (
    realtime.messages.extension in ('broadcast', 'presence')
    and app_private.can_access_room_topic((select realtime.topic()))
  );

-- 송신(broadcast move, presence track)
create policy mushroom_room_members_send
  on realtime.messages
  for insert
  to authenticated
  with check (
    realtime.messages.extension in ('broadcast', 'presence')
    and app_private.can_access_room_topic((select realtime.topic()))
  );
