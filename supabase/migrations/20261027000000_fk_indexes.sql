-- =============================================================================
-- 버섯마을: 외래 키 인덱스 (Supabase performance advisor 권고, 2026-10-27)
-- room_join_failures.room_id, room_members.user_id 에 커버링 인덱스가 없어
-- 방/사용자 삭제(cascade) 시 전체 스캔이 발생할 수 있다.
-- =============================================================================
create index if not exists room_join_failures_room_id_idx on public.room_join_failures (room_id);
create index if not exists room_members_user_id_idx on public.room_members (user_id);
