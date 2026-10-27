# backend → main / frontend / qa: 사이클 8 방 삭제 (2026-10-28)

정본: `docs/ARCHITECTURE.md` "사이클 8 계약" - 방 삭제. 상세 명세: `supabase/README.md`.

## 1. 변경 사항

새 마이그레이션 `supabase/migrations/20261028000000_delete_room.sql` (기존 파일 수정 없음, 테이블 구조 변경 없음).

- `public.delete_room(p_room_id uuid) returns void`: security definer, `search_path = ''`, authenticated만 실행(public/anon 회수).
  1. `app_private.require_uid()` (세션 없음 → `NOT_MEMBER`)
  2. 방 행 `for update` 잠금. 없거나 만료 → `ROOM_NOT_FOUND`
  3. `created_by <> auth.uid()` → `NOT_OWNER`
  4. 방장의 이 방 멤버 행 닉네임 조회(없으면 null)
  5. `realtime.send({room_id, by_nickname}, 'room_closed', 'room:<id>', true)`
  6. `delete from rooms` → cascade로 room_members, room_messages, room_join_failures 삭제
- `public.list_rooms()`: drop 후 재생성. 반환에 `mine boolean`(= `created_by = auth.uid()`) 추가. 정렬(인원 desc → 최근 활동 desc → 생성 desc), 만료 방 정리, 100개 제한은 그대로. 권한은 authenticated에만 다시 부여.
- 전달 순서: `realtime.send`는 `realtime.messages` insert이고 Realtime은 커밋된 행만 내보낸다. send → delete가 한 트랜잭션이라 커밋 시 함께 반영되고, 롤백되면 이벤트도 사라진다. `realtime.messages`에는 rooms FK가 없어 cascade 영향이 없다. 이미 구독 중인 멤버는 구독 시 정책 검사가 캐시되어 있으므로 멤버 행이 지워져도 이벤트를 받는다.
- 동시성: `join_room`/`heartbeat`(복귀 시)와 같은 행 잠금을 쓴다. 삭제 트랜잭션이 끝날 때까지 기다린 `join_room`은 `ROOM_NOT_FOUND`를 받는다(로컬 2세션 테스트로 확인).

메인 적용: SQL Editor에 파일 전체를 한 번에 Run 또는 `supabase db push`. 적용 후 `select pg_get_function_result('public.list_rooms()'::regprocedure);` 끝에 `mine boolean`이 있는지 확인.

## 2. 프런트용 요약

| 항목 | 내용 |
|---|---|
| RPC | `supabase.rpc('delete_room', { p_room_id })` → `data: null` |
| 오류 | `ROOM_NOT_FOUND`(없음/만료/이미 삭제) · `NOT_OWNER`(방장 아님, 새 코드) · `NOT_MEMBER`(세션 없음). `KNOWN` 집합에 `NOT_OWNER` 추가 |
| 이벤트 | 채널 `room:<id>` broadcast `room_closed`, payload `{ room_id: uuid, by_nickname: string \| null }`. 방장 본인에게도 온다 |
| 수신 처리 | `removeChannel` → sessionStorage `mushroom:room` 삭제 → 로비 + "방장이 방을 삭제했어요" 배너 |
| 놓친 경우 | 다음 `heartbeat` → `NOT_MEMBER` → `join_room` 재시도 → `ROOM_NOT_FOUND` → 같은 처리 |
| list_rooms | 각 행에 `mine: boolean` 추가. `mine === true`인 방에 로비 삭제 버튼 표시 |
| 방 HUD | 방장 판단: 입장한 방이 `list_rooms`의 `mine` 행이거나 `create_room`으로 만든 방. 버튼을 숨겨도 서버가 `NOT_OWNER`로 막는다 |

- 방장이 HUD에서 삭제할 때: RPC 성공 응답과 `room_closed` 수신 중 먼저 오는 쪽으로 로비 이동, 다른 쪽은 무시(중복 처리 방지).
- `delete_room` 실패가 `ROOM_NOT_FOUND`면 이미 지워진 방이므로 목록만 갱신.
- `room_closed`는 같은 방 멤버가 위조해 보낼 수 있다(알려진 한계 1과 같은 성격). 엄격히 하려면 수신 후 `heartbeat`로 확인해 `NOT_MEMBER`일 때만 배너를 띄운다.

## 3. QA 확인 항목

정상
- [ ] 방장이 HUD 삭제 → 확인 모달 → 본인과 다른 멤버 모두 로비 + 배너
- [ ] 로비 목록에서 내 방(mine)에만 삭제 버튼, 삭제 후 목록에서 사라짐
- [ ] 삭제된 방 재입장(새로고침 포함) → `ROOM_NOT_FOUND` → 로비
- [ ] 삭제 시 탭이 백그라운드였던 멤버 → 다음 heartbeat(20초 내)로 로비
- [ ] 방장이 방을 나간 뒤 로비에서 삭제 → 성공(by_nickname null, 배너 문구가 깨지지 않는지)

권한 우회 시도
- [ ] 콘솔에서 비방장이 `supabase.rpc('delete_room', { p_room_id: <남의 방> })` → `NOT_OWNER`, 방 유지
- [ ] 존재하지 않는 uuid / null → `ROOM_NOT_FOUND`
- [ ] 세션 없이 anon key만으로 호출 → 42501
- [ ] REST로 `DELETE /rest/v1/rooms?id=eq.<id>` 직접 삭제 → 권한 거부
- [ ] 멤버가 콘솔에서 `room_closed`를 직접 broadcast → 다른 사람이 로비로 가더라도 방은 남아 있고 재입장 가능(알려진 한계, 심각도 낮음으로 기록)
- [ ] 같은 방을 두 번 삭제(빠른 더블클릭) → 두 번째는 `ROOM_NOT_FOUND`, UI가 오류 없이 처리

## 4. 로컬 검증 (PostgreSQL 16 + Supabase 스텁)

모든 마이그레이션 1→6 순서 적용 후 48개 검사 통과, 0 실패.
결과: `/tmp/claude-0/-home-claude/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c8db/run.txt` (스크립트 `run.sh`, `00_stub.sql`, `10_tests.sql`).

- 방장 삭제 성공, cascade(멤버/메시지/실패 기록 0행), 다른 방 영향 없음
- 비방장 `NOT_OWNER`, 없는 방·null `ROOM_NOT_FOUND`, 세션 없음 `NOT_MEMBER`, 만료 방 `ROOM_NOT_FOUND`, 재삭제 `ROOM_NOT_FOUND`
- anon 실행 불가(delete_room, list_rooms), public 실행 권한 없음, 테이블 직접 delete/select 42501
- realtime.send 기록: event `room_closed`, topic `room:<id>`, private true, payload `{room_id, by_nickname:"Owner1"}` / 방장 퇴장 후 `by_nickname: null`. 실패 호출과 롤백된 삭제에서는 기록 없음
- list_rooms `mine` true/false(사용자별), 정렬 유지, 반환 타입 확인
- 삭제 후 다른 멤버: heartbeat/recent_messages/send_message `NOT_MEMBER`, join_room `ROOM_NOT_FOUND`, 채널 접근 헬퍼 false
- 동시성: 삭제 트랜잭션 진행 중 join_room은 대기 후 `ROOM_NOT_FOUND`

실제 Realtime 전달은 로컬에서 확인할 수 없다(스텁). 실 프로젝트에서 `room_closed`가 오지 않으면 README의 `realtime.send` 점검 절차(Realtime 로그 `WarnSendingBroadcastMessage`, postgres `rolbypassrls`)를 따른다.
