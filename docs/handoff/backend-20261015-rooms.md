# backend 2026-10-15: 로그인 없는 채팅방 (사이클 4)

정본: docs/ARCHITECTURE.md 결정 3~6, "데이터 모델 (사이클 4)", "알려진 한계". 상세 명세: `supabase/README.md`.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `supabase/migrations/20261015000000_rooms.sql` (신규) | characters/is_nickname_taken 삭제(cascade 없음), pgcrypto(extensions), `app_private` 헬퍼 스키마, 테이블 4개, RLS, RPC 7개, `realtime.messages` 정책 2개 |
| `supabase/README.md` (전면 갱신) | 적용 순서, 대시보드 설정, RPC/채널 명세, 알려진 한계. 사이클 1~3 이메일 로그인/characters/map:village 내용 제거 |

기존 마이그레이션 3개는 수정하지 않았다.

## 2. 스키마 요약

- `rooms(id uuid PK, name, password_hash null=공개, locked generated, created_by→auth.users, created_at, last_active_at)` idx `(created_by)`
- `room_members(PK(room_id,user_id), nickname, joined_at, last_seen_at)` unique `(room_id, lower(nickname))`, idx `(room_id, last_seen_at)`
- `room_messages(id bigint identity PK, room_id, user_id, nickname, text 1~80, created_at)` idx `(room_id, id desc)`, `(user_id, created_at desc)`
- `room_join_failures(id, room_id, user_id, created_at)` — 비밀번호 실패 기록(데이터 모델에 추가된 테이블)
- FK 전부 on delete cascade. RLS 전부 on + `*_no_direct_access`(restrictive, using false). anon/authenticated 테이블·시퀀스 권한 전부 회수(select 포함).
- 헬퍼(`app_private` 스키마, Data API 비노출): `trim_ws, require_uid, room_alive, is_member, can_access_room_topic`. authenticated는 `can_access_room_topic`만 실행 가능(Realtime 정책용).
- 시간 상수: 활성 60초 / 유효 멤버 10분(재접속 비밀번호 생략, 채팅 읽기·쓰기, 채널 접근) / 만료 30분 / 실패 1분 5회 / 채팅 1초.

## 3. RPC 명세 (프런트용)

모두 security definer, `search_path = ''`, authenticated만 execute. 오류는 `error.message === '<코드>'`.

| RPC | 인자 | 반환 | 오류 |
|---|---|---|---|
| `list_rooms()` | - | `[{id, name, locked, members, created_at}]` ≤100, members desc → 최근 활동 desc | NOT_MEMBER(세션 없음) |
| `create_room(p_name, p_password, p_nickname)` | password null/'' = 공개 | `uuid` | ROOM_NAME_FORMAT, PASSWORD_FORMAT, NICK_FORMAT, TOO_MANY_ROOMS |
| `join_room(p_room_id, p_password, p_nickname)` | | **`'OK' \| 'WRONG_PASSWORD'`** | NICK_FORMAT, ROOM_NOT_FOUND, RATE_LIMITED, ROOM_FULL, NICK_TAKEN |
| `leave_room(p_room_id)` | | null (멱등) | - |
| `heartbeat(p_room_id)` | | null | NOT_MEMBER |
| `recent_messages(p_room_id)` | | `[{id, user_id, nickname, text, created_at}]` 50개 오래된 순 | NOT_MEMBER |
| `send_message(p_room_id, p_text)` | | `{id, user_id, nickname, text, created_at}` | NOT_MEMBER, TEXT_FORMAT, RATE_LIMITED |

**ARCHITECTURE와 다른 점 (메인 확인 요청)**
1. `join_room`의 WRONG_PASSWORD는 예외가 아니라 반환값. 예외를 던지면 트랜잭션이 롤백되어 실패 기록이 남지 않아 시도 제한이 불가능하기 때문. 어댑터가 `data === 'WRONG_PASSWORD'`면 `Error.code='WRONG_PASSWORD'`로 던지면 인터페이스는 동일. ARCHITECTURE 결정 6 문구 보완 요청.
2. 재접속 기간 = 멤버 행 `last_seen_at` 10분 이내. leave_room 후나 10분 초과 시 비밀번호 다시 필요.
3. 같은 닉네임의 비활성(60초 초과) 멤버 행은 다른 사람 입장 시 삭제(닉네임 양보). 그 사람은 heartbeat에서 NOT_MEMBER.
4. heartbeat: 60초 넘게 비활성이었다가 돌아왔는데 방이 20명 차 있으면 NOT_MEMBER(정원 초과 부활 방지). 클라이언트는 join_room 재시도로 정확한 사유를 받는다.
5. 채팅/방 이름에 제어문자(개행 포함) 금지, trim은 공백·탭·개행·NBSP·U+3000·BOM 제거. local 모드도 같게 맞춰 달라(프런트).
6. 비밀번호 null/''로 잠금 방 시도는 WRONG_PASSWORD지만 실패 횟수에 세지 않음(새로고침 재입장 흐름 보호).
7. 채팅 1초 제한은 사용자당 모든 방 합산.

## 4. 채널 / 정책

- 채널 `room:<room_id>`, `{ config: { private: true, presence: { key: userId } } }`, 구독 전 `supabase.realtime.setAuth()`. join_room 성공 **후** 구독.
- `chat` 이벤트(서버만 송신): payload = send_message 반환값 `{ id, user_id, nickname, text, created_at }`. `realtime.send(payload, 'chat', 'room:'||id, true)`.
- 정책: `mushroom_room_members_receive`(select), `mushroom_room_members_send`(insert), 둘 다 authenticated, `extension in ('broadcast','presence')` 이고 `realtime.topic()`의 방에 유효 멤버 행이 있을 때.

## 5. 검증 결과 (로컬 PostgreSQL 16.15 + Supabase 스텁, 4개 마이그레이션 순서대로 적용)

기능 163/163 PASS, 동시성 7/7 PASS. 스크립트: 스크래치 `c4db/{stub.sql,setup.sh,test.sql,conc.sh}` (클러스터 정리 완료).

| 항목 | 결과 |
|---|---|
| 공개/잠금 방 생성, bcrypt(`$2a$08$`) 저장, ''=공개, 자동 멤버 | PASS |
| 4번째 방 TOO_MANY_ROOMS, 만료 방은 제외하고 셈 | PASS |
| 이름(빈/공백/null/25자/개행) ROOM_NAME_FORMAT, 24자+전각공백 trim OK | PASS |
| 비번 3자/33자 PASSWORD_FORMAT, 닉네임 1자/밑줄/13자/null NICK_FORMAT, 세션 없음 NOT_MEMBER | PASS |
| 틀린 비번 WRONG_PASSWORD+기록, null 비번 미기록, 맞는 비번 OK, 재접속 비번 생략 | PASS |
| 5회 실패 후 6번째(맞는 비번이어도) RATE_LIMITED, 다른 사용자 무관, 1분 후 OK | PASS |
| leave 후 / 멤버 행 10분 초과 시 비번 다시 필요, 무효 행 삭제 | PASS |
| 20명 방 21번째 ROOM_FULL, 기존 멤버 재입장 OK, 61초 비활성 제외 후 입장 OK, 비활성자 복귀 ROOM_FULL/heartbeat NOT_MEMBER | PASS |
| 같은 방 닉네임 대소문자 중복 NICK_TAKEN, 다른 방 허용, 본인 재입장(닉 변경) OK, 비활성 보유자 닉 양보 | PASS |
| list_rooms 인원/정렬(인원→최근 활동)/잠금 표시, 만료 방 제외+삭제(cascade) | PASS |
| password_hash 노출: 직접 select(anon/auth) 거부, 컬럼 select 거부, RPC 결과·인자명에 없음 | PASS |
| send_message 비멤버/81자/공백/null/개행 거부, 80자 trim OK, nickname=멤버 행 값, user_id 서버값, 1초 제한, 51번째부터 오래된 것 삭제(50 유지), realtime.send 기록(topic/event/private/payload 일치), 제한된 호출은 브로드캐스트 안 함 | PASS |
| recent_messages 비멤버/10분 초과 멤버 거부, 50개 오래된 순 | PASS |
| realtime.messages 정책(authenticated로 실제 RLS 평가): 멤버 select/insert(broadcast, presence) 허용, postgres_changes 불가, 비멤버·다른 방·잘못된 topic·map:village·anon 거부, leave 후/10분 초과 거부 | PASS |
| 직접 insert/update/delete/truncate (anon, authenticated) 4개 테이블 전부 거부, anon RPC 실행 거부 | PASS |
| characters/is_nickname_taken 삭제, RLS 4개 테이블 on, public definer 7개 모두 search_path='' | PASS |
| 동시성: 같은 닉네임 2세션(잠금 보유 중) → 1 OK/1 NICK_TAKEN | PASS |
| 동시성: 같은 닉네임 10세션 버스트 → 정확히 1 OK | PASS |
| 동시성: 19명 방에 3명 동시 입장 → 1 OK/2 ROOM_FULL, 활성 20 | PASS |
| 동시성: 같은 사용자 create_room 5개 동시 → 3 OK/2 TOO_MANY_ROOMS | PASS |
| 동시성: 같은 사용자 send_message 3개 동시 → 1 OK/2 RATE_LIMITED | PASS |

참고: 샌드박스가 다른 uid의 스크래치 접근을 막아 postgres는 user namespace(`unshare --map-user`)로 실행했다.

## 6. realtime.send / Realtime Authorization 확인 여부

- 확인함: Supabase 문서 "Broadcast"(https://supabase.com/docs/guides/realtime/broadcast) — `realtime.send(payload, event, topic, private)`, private 기본 true, 비공개 브로드캐스트는 비공개 채널에만 도달, 실패 시 예외 대신 로그.
- 확인함: "Realtime Authorization"(https://supabase.com/docs/guides/realtime/authorization) — `realtime.topic()` + `extension in ('broadcast','presence')` 정책 패턴, "Allow public access" 끄기 위치(Realtime Settings), 정책은 구독/JWT 갱신 시에만 검사·캐시.
- **미확인**: 실제 Supabase에서 security definer 함수(소유자 postgres)의 `realtime.send` insert가 `realtime.messages` RLS를 통과하는지(postgres의 BYPASSRLS 여부). 로컬 스텁은 superuser라 검증 불가. 실패해도 메시지 저장은 유지되고 로그만 남는다. 점검 방법과 대안(클라이언트 직접 broadcast, 위장 가능)은 README에 기록.

## 7. QA 확인 항목 (실 Supabase 프로젝트)

1. 익명 로그인 후 방 생성/목록/입장/퇴장 흐름. 브라우저 2개(다른 익명 uid)로 실시간 chat/move/presence.
2. 잠금 방: 틀린 비번 5회 → 6번째 RATE_LIMITED, 1분 뒤 성공. 새로고침 재입장 시 비번 없이 성공. 나가기 후 재입장은 비번 필요.
3. 닉네임 중복(대소문자), 21명째 ROOM_FULL(가능하면 스크립트로 익명 계정 21개).
4. chat 이벤트가 **서버에서** 도착하는지(send_message 후 상대 브라우저에 `{id,...}` 수신). 안 오면 README 점검 절차.
5. 권한 우회 시도
   - anon key만으로(세션 없이) `rpc('list_rooms')` → 42501.
   - `from('rooms').select('*')`, `select('password_hash')` → 거부(42501).
   - `from('room_members').insert/update/delete`, `from('room_messages').insert` → 거부.
   - 비멤버가 `channel('room:<id>', {config:{private:true}})` 구독 → CHANNEL_ERROR(수신 없음). `private` 없이 같은 topic 구독 → "Allow public access" 끈 상태에서 거부.
   - 비멤버 `recent_messages`/`send_message` → NOT_MEMBER.
   - 멤버가 직접 `ch.send({type:'broadcast', event:'chat', payload:{...위조}})` → 프런트가 무시하는지(서버 기록에는 없음).
   - `send_message`에 81자, 개행 포함, 0.5초 간격 연속 → TEXT_FORMAT / RATE_LIMITED.
   - 방을 나간 뒤 기존 채널 연결은 JWT 갱신 전까지 유지됨(알려진 한계, 즉시 강퇴 아님) — 재연결 시 거부 확인.
6. 활성 0명 30분 후 목록에서 사라지는지(시간이 걸리면 SQL로 last_active_at/last_seen_at 조정).

## 8. 사용자 작업

1. SQL Editor에서 `20261015000000_rooms.sql` 전체 한 번에 실행(1~3이 미적용이면 순서대로 먼저).
2. Authentication > Sign In / Providers > **Allow anonymous sign-ins 켜기**.
3. Realtime > Settings > **Allow public access 끄기**(권장).
4. (선택) 공개 운영 전 Attack Protection > CAPTCHA.

## 9. 다른 역할에 요청

- 메인: ARCHITECTURE 결정 6에 "join_room의 WRONG_PASSWORD는 반환값" 및 3절 2~7 반영, 데이터 모델에 `room_join_failures` 추가.
- 프런트: 어댑터에서 join_room 반환값 처리, join 성공 후 채널 구독, `setAuth()`, chat 중복 제거(id), 클라이언트 송신 chat 무시, local 모드 규칙(trim/제어문자/10분 재접속/닉 양보) 맞춤.
