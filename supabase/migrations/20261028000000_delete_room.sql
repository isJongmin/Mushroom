-- =============================================================================
-- 버섯마을: 방장 방 삭제 (사이클 8)
-- 마이그레이션: 20261028000000_delete_room.sql
--
-- 정본: docs/ARCHITECTURE.md "사이클 8 계약" - 방 삭제.
--
--  - public.delete_room(p_room_id uuid) returns void (새 RPC, authenticated 전용)
--      방장(rooms.created_by)만 삭제 가능. 삭제 직전 비공개 채널 room:<id>로
--      broadcast 'room_closed' { room_id, by_nickname } 을 보낸 뒤 rooms 행을 지운다.
--      FK on delete cascade로 room_members, room_messages, room_join_failures가 함께 지워진다.
--      오류: ROOM_NOT_FOUND(없음/만료), NOT_OWNER(방장 아님), NOT_MEMBER(세션 없음).
--  - public.list_rooms(): 반환에 mine boolean(created_by = auth.uid()) 추가.
--      반환 타입이 바뀌므로 drop 후 다시 만들고 권한을 다시 부여한다. 정렬/동작은 그대로.
--
-- [실행 방법] 기존 마이그레이션과 같다. 파일 전체를 한 번에 실행(단일 트랜잭션).
-- begin/commit은 넣지 않는다.
--
-- [room_closed 전달 시점]
-- realtime.send는 realtime.messages에 행을 insert하는 함수다. Realtime 서버는 커밋된
-- 행만(복제 스트림으로) 읽어 broadcast하므로, 같은 트랜잭션에서 send 후 delete를 해도
-- 둘은 원자적으로 커밋된다:
--   - 커밋되면: 방 삭제 + room_closed 전달.
--   - 삭제가 실패해 롤백되면: room_closed도 전달되지 않는다(거짓 "방 삭제됨" 없음).
-- realtime.messages에는 rooms를 참조하는 FK가 없으므로 rooms 삭제가 이 행에 영향을 주지 않는다.
-- 이미 구독 중인 멤버는 구독 시점에 정책 검사를 통과했으므로(연결 동안 캐시) 멤버 행이
-- 같은 트랜잭션에서 지워져도 이 이벤트를 받는다.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. delete_room(p_room_id) → void
--
-- [동시성] 방 행을 for update로 잠근다. join_room/heartbeat(복귀 시)도 같은 행을 for update로
-- 잠그므로, 삭제와 동시에 들어온 입장은 삭제 커밋 후 재검사에서 ROOM_NOT_FOUND가 된다.
-- [만료 방] 만료(활성 0명 30분)된 방은 다른 RPC와 같이 ROOM_NOT_FOUND로 본다
-- (목록에 없고 입장도 불가. 실제 행은 list_rooms가 정리한다).
-- [by_nickname] 방장의 이 방 멤버 행 닉네임(유효기간 무관). 멤버 행이 없으면 null.
-- -----------------------------------------------------------------------------
create or replace function public.delete_room(p_room_id uuid)
returns void
language plpgsql
volatile
security definer
set search_path = ''
as $$
declare
  v_uid  uuid := app_private.require_uid();
  v_room public.rooms%rowtype;
  v_nick text;
begin
  select * into v_room
  from public.rooms r
  where r.id = p_room_id
  for update;

  if not found or not app_private.room_alive(v_room.id, v_room.last_active_at) then
    raise exception using message = 'ROOM_NOT_FOUND';
  end if;

  if v_room.created_by <> v_uid then
    raise exception using message = 'NOT_OWNER';
  end if;

  select m.nickname into v_nick
  from public.room_members m
  where m.room_id = p_room_id
    and m.user_id = v_uid;

  -- 삭제 전에 보낸다. 같은 트랜잭션이므로 커밋되어야 전달된다(파일 머리 주석 참고).
  perform realtime.send(
    pg_catalog.jsonb_build_object('room_id', p_room_id, 'by_nickname', v_nick),
    'room_closed',
    'room:' || p_room_id::text,
    true
  );

  -- cascade: room_members, room_messages, room_join_failures.
  delete from public.rooms r where r.id = p_room_id;
end;
$$;

revoke all on function public.delete_room(uuid) from public, anon;
grant execute on function public.delete_room(uuid) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. list_rooms() 교체: mine boolean 추가
-- 본문은 20261015000000_rooms.sql 5.1과 같고 mine 컬럼만 추가했다.
-- -----------------------------------------------------------------------------
drop function public.list_rooms();

create function public.list_rooms()
returns table (id uuid, name text, locked boolean, members int, created_at timestamptz, mine boolean)
language plpgsql
volatile
security definer
set search_path = ''
as $$
#variable_conflict use_column
declare
  v_uid uuid := app_private.require_uid();
begin
  delete from public.rooms d
  where d.id in (
    select r.id
    from public.rooms r
    where not app_private.room_alive(r.id, r.last_active_at)
    for update skip locked
  );

  return query
  select s.id, s.name, s.locked, s.members, s.created_at, s.mine
  from (
    select
      r.id, r.name, r.locked, r.created_at,
      (r.created_by = v_uid) as mine,
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

revoke all on function public.list_rooms() from public, anon;
grant execute on function public.list_rooms() to authenticated;
