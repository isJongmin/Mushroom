-- =============================================================================
-- 버섯마을: characters 테이블
-- 마이그레이션: 20261014000000_characters.sql
--
-- 계정당 캐릭터 1개(user_id PK), 닉네임 중복 불가(대소문자 무시), 아바타 jsonb 형식 검증,
-- RLS + 컬럼 단위 권한, 닉네임 중복 확인 RPC.
--
-- SQL Editor에 그대로 붙여넣어 실행하거나 supabase CLI(`supabase db push`)로 적용한다.
-- begin/commit은 넣지 않는다. CLI는 마이그레이션 파일 단위로 트랜잭션을 감싸므로
-- 명시적 commit이 있으면 그 트랜잭션을 조기에 끝내 버린다.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. 테이블
-- -----------------------------------------------------------------------------
create table public.characters (
  -- 계정당 캐릭터 1개를 PK로 강제한다. 같은 user_id로 두 번째 insert 시
  -- 23505 / constraint "characters_pkey".
  user_id    uuid        not null
             constraint characters_pkey primary key
             references auth.users (id) on delete cascade,

  -- 2~12자, 한글 완성형/영문/숫자만. 위반 시 23514 / "characters_nickname_format".
  nickname   text        not null
             constraint characters_nickname_format
             check (nickname ~ '^[가-힣A-Za-z0-9]{2,12}$'),

  -- { "skin", "hair", "eyes", "top", "bottom" } 5개 키만, 각 값은 ^[a-z0-9-]{1,32}$ 문자열.
  -- 계약에 없는 키는 거부한다(임의 데이터 적재 방지). 파트가 늘어나면 새 마이그레이션에서
  -- 이 제약을 교체한다. 위반 시 23514 / "characters_avatar_shape".
  avatar     jsonb       not null
             constraint characters_avatar_shape
             -- 주의: 키가 없으면 jsonb_typeof(...)가 NULL이 되고, CHECK는 NULL을 통과로 본다.
             -- 그래서 전체를 coalesce(..., false)로 감싸 누락 키를 위반으로 만든다.
             check (coalesce(
               jsonb_typeof(avatar) = 'object'
               and avatar ?& array['skin', 'hair', 'eyes', 'top', 'bottom']
               and jsonb_typeof(avatar -> 'skin')   = 'string'
               and jsonb_typeof(avatar -> 'hair')   = 'string'
               and jsonb_typeof(avatar -> 'eyes')   = 'string'
               and jsonb_typeof(avatar -> 'top')    = 'string'
               and jsonb_typeof(avatar -> 'bottom') = 'string'
               and (avatar ->> 'skin')   ~ '^[a-z0-9-]{1,32}$'
               and (avatar ->> 'hair')   ~ '^[a-z0-9-]{1,32}$'
               and (avatar ->> 'eyes')   ~ '^[a-z0-9-]{1,32}$'
               and (avatar ->> 'top')    ~ '^[a-z0-9-]{1,32}$'
               and (avatar ->> 'bottom') ~ '^[a-z0-9-]{1,32}$'
               and (avatar - array['skin', 'hair', 'eyes', 'top', 'bottom']) = '{}'::jsonb,
               false
             )),

  created_at timestamptz not null default now()
);

comment on table  public.characters          is '플레이어 캐릭터. 계정당 1개.';
comment on column public.characters.nickname is '2~12자 한글/영문/숫자. 대소문자 무시 unique. 생성 후 변경 불가.';
comment on column public.characters.avatar   is '{skin,hair,eyes,top,bottom} 파트 id. assets/avatar/<part>/<id>.svg';

-- 닉네임 중복 불가(대소문자 무시). 동시 생성 race는 이 인덱스가 최종 판정한다.
-- 위반 시 23505 / "characters_nickname_lower_key".
create unique index characters_nickname_lower_key
  on public.characters (lower(nickname));

-- -----------------------------------------------------------------------------
-- 2. 권한 (테이블/컬럼 단위)
--
-- Supabase는 public 스키마의 새 테이블에 anon/authenticated/service_role 전체 권한을
-- 기본 부여(default privileges)한다. 먼저 모두 회수하고 필요한 것만 다시 준다.
-- -----------------------------------------------------------------------------
revoke all on table public.characters from public;
revoke all on table public.characters from anon;
revoke all on table public.characters from authenticated;

-- 조회: 맵에 다른 사람을 그려야 하므로 모든 컬럼 조회 허용(행 범위는 RLS가 결정).
-- 컬럼을 명시해 두면 이후 추가되는 컬럼이 자동으로 노출되지 않는다.
grant select (user_id, nickname, avatar, created_at) on table public.characters to authenticated;

-- 생성: created_at은 서버 기본값만 사용하도록 제외.
grant insert (user_id, nickname, avatar) on table public.characters to authenticated;

-- 수정: avatar 컬럼만.
--
-- [nickname 변경 불가를 컬럼 권한으로 강제한 이유]
--  - 트리거 방식은 함수 하나와 트리거를 추가로 유지해야 하고, 트리거 로직 버그나
--    이후 마이그레이션에서 실수로 drop될 때 조용히 뚫린다.
--  - 컬럼 권한은 Postgres가 파싱 단계에서 거부하므로(42501 permission denied)
--    RLS 평가 이전에 차단되고, user_id/created_at 변경도 같은 방식으로 함께 막힌다.
--  - 운영자(service_role, postgres)는 이 제한을 받지 않으므로 관리자 닉네임 변경
--    (신고 처리 등)은 대시보드/서버에서 가능하다. 이는 의도된 동작이다.
grant update (avatar) on table public.characters to authenticated;

-- delete: 권한 없음(정책도 없음). 캐릭터 삭제는 auth.users 삭제 시 cascade로만 발생.

-- -----------------------------------------------------------------------------
-- 3. RLS
-- -----------------------------------------------------------------------------
alter table public.characters enable row level security;

-- select: 로그인한 사용자는 모든 캐릭터 조회 가능. anon은 테이블 권한부터 없음.
create policy characters_select_authenticated
  on public.characters
  for select
  to authenticated
  using (true);

-- insert: 본인 user_id로만.
create policy characters_insert_own
  on public.characters
  for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

-- update: 본인 행만. (변경 가능한 컬럼은 위의 컬럼 권한으로 avatar로 제한됨)
create policy characters_update_own
  on public.characters
  for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- delete: 정책 없음 → 불가.

-- -----------------------------------------------------------------------------
-- 4. RPC: 닉네임 중복 확인
--
-- UX용 사전 확인일 뿐이다. 확인과 insert 사이에 다른 사용자가 같은 닉네임을 만들 수
-- 있으므로 최종 판정은 unique 인덱스(23505)다.
-- security definer + search_path = '' : 모든 객체를 스키마 한정 이름으로 참조한다.
-- -----------------------------------------------------------------------------
create or replace function public.is_nickname_taken(p_nickname text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.characters c
    where lower(c.nickname) = lower(p_nickname)
  );
$$;

comment on function public.is_nickname_taken(text) is
  '닉네임 사용 여부(대소문자 무시). authenticated 전용. 최종 판정은 unique 인덱스.';

revoke all on function public.is_nickname_taken(text) from public;
revoke all on function public.is_nickname_taken(text) from anon;
grant execute on function public.is_nickname_taken(text) to authenticated;

