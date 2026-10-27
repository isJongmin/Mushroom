# 버섯마을 Supabase 백엔드 (사이클 4: 로그인 없는 채팅방, 사이클 8: 방 삭제)

정본 설계는 `docs/ARCHITECTURE.md`의 결정 3~6, "데이터 모델 (사이클 4)", "알려진 한계"다. 이 문서는 그 내용을 Supabase에 적용하는 방법과 프런트가 쓸 API를 정리한다.

사이클 1~3의 이메일 로그인, `characters` 테이블, `is_nickname_taken`, 공개 채널 `map:village`는 **폐기**되었다(`20261015000000_rooms.sql`이 테이블과 함수를 삭제한다).

## 마이그레이션 목록 (적용 순서)

| 순서 | 파일 | 내용 |
|---|---|---|
| 1 | `migrations/20261014000000_characters.sql` | (폐기됨) `characters` 테이블, `is_nickname_taken`. 4번이 삭제한다 |
| 2 | `migrations/20261014000100_realtime.sql` | 주석만(no-op) |
| 3 | `migrations/20261014000200_avatar_v3.sql` | (폐기됨) characters 아바타 7키 변환 |
| 4 | `migrations/20261015000000_rooms.sql` | **현재 스키마.** characters/is_nickname_taken 삭제, rooms/room_members/room_messages/room_join_failures, RPC 7개, `realtime.messages` 정책 |
| 5 | `migrations/20261027000000_fk_indexes.sql` | FK 인덱스 2개(`room_join_failures.room_id`, `room_members.user_id`) |
| 6 | `migrations/20261028000000_delete_room.sql` | (사이클 8) `delete_room` RPC 추가, `list_rooms`에 `mine` 컬럼 추가(drop 후 재생성 + 권한 재부여) |

규칙: 이미 적용된 마이그레이션은 수정하지 않는다. 변경은 항상 새 타임스탬프 파일로 추가한다.

1~3을 아직 적용하지 않은 새 프로젝트라도 순서대로 1→4를 모두 적용한다(4번이 `drop ... if exists`라 1~3 없이도 동작하지만, CLI 이력과 맞추기 위해 순서대로 적용).

## 적용 방법

### A. 대시보드 SQL Editor

1. Supabase 대시보드 > 프로젝트 > **SQL Editor** > New query.
2. 아직 적용하지 않은 파일을 위 순서대로 하나씩, **파일 전체를 한 번에** 붙여넣고 **Run**. (일부만 선택해 실행하지 말 것. 한 번에 보내면 하나의 트랜잭션으로 실행되어 중간에 실패해도 전체가 취소된다.)
3. 확인
   - **Table Editor**: `rooms`, `room_members`, `room_messages`, `room_join_failures`가 있고 모두 "RLS enabled". `characters`는 없어야 한다.
   - **Database > Functions**: `list_rooms, create_room, join_room, leave_room, heartbeat, recent_messages, send_message, delete_room`.
   - 아래 쿼리 결과가 2행(`mushroom_room_members_receive`, `mushroom_room_members_send`)이어야 한다.
     ```sql
     select policyname from pg_policies where schemaname = 'realtime' and policyname like 'mushroom_%';
     ```

`20261015000000_rooms.sql`을 두 번 실행하면 `relation "rooms" already exists` 오류가 나고 전체가 취소된다. 이미 적용되었다는 뜻이며 정상이다.

### B. supabase CLI

```sh
supabase login
supabase link --project-ref <프로젝트 ref>   # Project Settings > General 의 Reference ID
supabase db push                              # 미적용 파일을 타임스탬프 순서로 실행
supabase migration list
```

psql로 직접 적용할 때는 파일마다 `psql -1 -f <파일>`(단일 트랜잭션).

## 대시보드에서 사용자가 할 설정

1. **Authentication > Sign In / Providers**: **"Allow anonymous sign-ins" 켜기.** (필수. 꺼져 있으면 `signInAnonymously()`가 실패한다)
2. **Realtime > Settings** (`https://supabase.com/dashboard/project/<ref>/realtime/settings`): **"Allow public access" 끄기 (권장).** 끄면 비공개 채널만 허용되어 `realtime.messages` 정책이 반드시 적용된다. 켜 둬도 프런트가 `private: true`로 구독하는 한 정책은 적용되지만, 공개 채널을 누구나 만들 수 있게 된다.
3. Email provider / **Confirm email** 설정은 더 이상 무관하다(이메일 로그인 폐기).
4. (선택) **Authentication > Rate Limits**: 익명 로그인 요청 제한 확인. QA가 같은 IP에서 많은 익명 계정을 만들면 429가 날 수 있다. 공개 운영 시 **Attack Protection > CAPTCHA**를 켜는 것을 권장(알려진 한계 2).

## 프런트가 쓸 값

| 값 | 위치 | 프런트에 넣어도 되나 |
|---|---|---|
| Project URL | Project Settings > API | 예 → `SUPABASE_URL` |
| anon / publishable key | Project Settings > API Keys | 예 → `SUPABASE_ANON_KEY` |
| **service_role / secret key** | Project Settings > API Keys | **절대 안 됨.** RLS를 우회한다 |

## 프런트용 API 명세 (supabase-js 2.45.4)

### 0. 익명 로그인

```js
let { data: { session } } = await supabase.auth.getSession();
if (!session) ({ data: { session } } = await supabase.auth.signInAnonymously());
const userId = session.user.id;
```

### 오류 처리 공통

RPC는 `raise exception using message = '<코드>'`로 실패한다. supabase-js에서 `error.message === '<코드>'`(SQLSTATE `P0001`).
그 밖의 경우: `error.code === '42501'`(권한 없음, 보통 세션 없음) → 재로그인 / 네트워크 오류 → `NETWORK` / 나머지 → `UNKNOWN`.

```js
const KNOWN = new Set(['ROOM_NOT_FOUND','WRONG_PASSWORD','ROOM_FULL','NICK_TAKEN','NICK_FORMAT',
  'ROOM_NAME_FORMAT','PASSWORD_FORMAT','TOO_MANY_ROOMS','RATE_LIMITED','NOT_MEMBER','TEXT_FORMAT','NOT_OWNER']);
const code = KNOWN.has(error.message) ? error.message : 'UNKNOWN';
```

### RPC

모두 `authenticated`(익명 로그인 포함)만 호출 가능. anon key만 있고 세션이 없으면 `42501`.

| RPC | 인자 | 반환 | 오류 코드 |
|---|---|---|---|
| `list_rooms` | 없음 | `[{ id, name, locked, members, created_at, mine }]` 최대 100개, 인원 desc → 최근 활동 desc. `mine` = 내가 만든 방(`created_by = auth.uid()`) | `NOT_MEMBER`(세션 없음) |
| `create_room` | `p_name, p_password, p_nickname` | `uuid` (방 id). 만든 사람 자동 입장 | `ROOM_NAME_FORMAT, PASSWORD_FORMAT, NICK_FORMAT, TOO_MANY_ROOMS` |
| `join_room` | `p_room_id, p_password, p_nickname` | **`'OK'` 또는 `'WRONG_PASSWORD'`** (아래 주의) | `NICK_FORMAT, ROOM_NOT_FOUND, RATE_LIMITED, ROOM_FULL, NICK_TAKEN` |
| `leave_room` | `p_room_id` | `null` (멱등, 멤버 아니어도 성공) | 없음 |
| `heartbeat` | `p_room_id` | `null` | `NOT_MEMBER` |
| `recent_messages` | `p_room_id` | `[{ id, user_id, nickname, text, created_at }]` 최근 50개, 오래된 것부터 | `NOT_MEMBER` |
| `send_message` | `p_room_id, p_text` | `{ id, user_id, nickname, text, created_at }` | `NOT_MEMBER, TEXT_FORMAT, RATE_LIMITED` |
| `delete_room` | `p_room_id` | `null`. 방장만. 삭제 직전 `room_closed` broadcast, 멤버/메시지/실패 기록 cascade 삭제 | `ROOM_NOT_FOUND`(없음/만료/이미 삭제), `NOT_OWNER`(방장 아님), `NOT_MEMBER`(세션 없음) |

```js
const { data: rooms }  = await supabase.rpc('list_rooms');
const { data: roomId } = await supabase.rpc('create_room', { p_name, p_password: pw || null, p_nickname });
const { data: r, error } = await supabase.rpc('join_room', { p_room_id, p_password: pw || null, p_nickname });
if (!error && r === 'WRONG_PASSWORD') throw Object.assign(new Error('WRONG_PASSWORD'), { code: 'WRONG_PASSWORD' });
await supabase.rpc('heartbeat', { p_room_id });            // 20초마다
const { data: msgs } = await supabase.rpc('recent_messages', { p_room_id });
const { data: msg }  = await supabase.rpc('send_message', { p_room_id, p_text });
await supabase.rpc('leave_room', { p_room_id });
await supabase.rpc('delete_room', { p_room_id });     // 방장만. 성공 시 room_closed가 본인에게도 온다
```

**주의: `join_room`의 `WRONG_PASSWORD`는 예외가 아니라 반환값이다.** 실패 횟수 제한을 위해 실패 기록을 커밋해야 하는데, 예외를 던지면 그 호출의 트랜잭션 전체가 롤백되어 기록이 남지 않기 때문이다. 어댑터에서 `data === 'WRONG_PASSWORD'`를 `Error.code = 'WRONG_PASSWORD'`로 바꿔 던지면 인터페이스는 같다.

규칙 상세

- 방 이름: 앞뒤 공백(일반 공백, 탭, 개행, NBSP, 전각 공백, BOM) 제거 후 1~24자, 제어문자 금지.
- 비밀번호: `null` 또는 `''`이면 공개 방. 그 외 4~32자(문자 종류 제한 없음, trim 안 함). bcrypt(cost 8)로 저장.
- 닉네임: `^[가-힣A-Za-z0-9]{2,12}$`. 같은 방의 **활성 멤버**(60초 이내 하트비트) 사이에서만 중복 금지(대소문자 무시). 본인 재입장은 허용(닉네임 바꿔도 됨). 같은 닉네임을 가진 **비활성** 멤버 행은 입장 시 지워진다(그 사람은 돌아오면 비밀번호부터 다시).
- 정원: 활성 멤버(본인 제외) 20명 이상이면 `ROOM_FULL`.
- 소유 제한: 본인이 만든 살아 있는 방 3개 → 4번째 `TOO_MANY_ROOMS`. 만료된 방은 세지 않는다.
- 비밀번호 실패: 사용자당 방당 1분 안에 5회 틀리면 그 뒤 시도는(맞는 비밀번호여도) `RATE_LIMITED`. 비밀번호 없이(`null`/`''`) 시도한 것은 세지 않는다.
- **재접속(비밀번호 생략)**: 본인 멤버 행의 `last_seen_at`이 10분 이내면 잠금 방이라도 `p_password` 없이 `join_room` 성공. `leave_room`을 했거나 10분 넘게 하트비트가 없었으면 다시 비밀번호가 필요하다.
- `heartbeat`: 유효 멤버 행이 없으면 `NOT_MEMBER`. 60초 넘게 비활성이었다가 돌아왔는데 그 사이 방이 20명으로 찼거나, 그 사이 다른 사람이 같은 닉네임으로 들어왔으면 `NOT_MEMBER` → 클라이언트는 `join_room`을 다시 시도해 정확한 사유(`ROOM_FULL`, `NICK_TAKEN`)를 받는다.
- 채팅: 앞뒤 공백 제거 후 1~80자, 제어문자(개행 포함) 금지 → `TEXT_FORMAT`. 사용자당 1초 1회(모든 방 합산) → `RATE_LIMITED`. `nickname`은 서버의 멤버 행 값. 방당 최근 50개만 남는다.
- 만료: 활성 멤버 0명으로 30분이 지난 방은 목록에서 빠지고 `join_room`은 `ROOM_NOT_FOUND`. 실제 삭제는 `list_rooms` 호출 때.
- 세션 없이(토큰 없이 서비스 키 등) 호출하면 `NOT_MEMBER`.
- **방 삭제(`delete_room`, 사이클 8)**: `rooms.created_by`가 본인일 때만. 방 행을 `for update`로 잠그므로 동시에 들어온 `join_room`은 삭제 커밋 후 `ROOM_NOT_FOUND`. 삭제 후 다른 멤버의 `heartbeat`·`recent_messages`·`send_message`는 `NOT_MEMBER`, `join_room`은 `ROOM_NOT_FOUND`. 방장이 이미 나가 멤버 행이 없어도 삭제할 수 있다(`by_nickname`이 `null`). 만료된 방은 `ROOM_NOT_FOUND`(목록에 없으므로).

### Realtime 채널 `room:<room_id>` (비공개)

ARCHITECTURE 결정 5를 그대로 따른다.

```js
await supabase.realtime.setAuth();   // 세션 토큰을 Realtime에 전달 (비공개 채널에 필요)
const ch = supabase.channel(`room:${roomId}`, {
  config: { private: true, presence: { key: userId } },
});
ch.on('presence', { event: 'sync' }, () => { /* ch.presenceState() */ })
  .on('broadcast', { event: 'move' }, ({ payload }) => { /* { user_id, x, y, dir } */ })
  .on('broadcast', { event: 'chat' }, ({ payload }) => { /* { id, user_id, nickname, text, created_at } */ })
  .on('broadcast', { event: 'room_closed' }, ({ payload }) => { /* { room_id, by_nickname } → 채널 닫고 로비 */ })
  .subscribe(async (status) => {
    if (status === 'SUBSCRIBED') await ch.track({ user_id: userId, nickname, avatar, x, y });
  });
```

- **반드시 `join_room`(또는 `create_room`) 성공 후 구독한다.** 정책이 구독 시점에 멤버 행을 확인한다. 멤버가 아니면 구독이 `CHANNEL_ERROR`로 끝난다.
- `chat`은 서버(`send_message` → `realtime.send`)만 보낸다. 페이로드는 `send_message` 반환값과 같다. 보낸 사람도 같은 이벤트를 받으므로 `id`로 중복 제거한다(반환값으로 먼저 그렸다면).
- 클라이언트가 직접 보낸 `chat` 이벤트는 무시해야 하지만, 수신 측에서 서버 송신과 멤버의 위조 송신을 구분할 확실한 방법은 없다(정책은 채널 접근만 판단, 페이로드 형식은 흉내 낼 수 있음). **신뢰할 기록은 `recent_messages`와 `send_message` 반환값**이다. 알려진 한계 1 참고.
- `move`: `{ user_id, x, y, dir }`, 최대 10회/초. 서버 검증 없음.
- `room_closed` (사이클 8): `{ room_id: uuid, by_nickname: string | null }`. `delete_room`만 보낸다(`realtime.send(..., 'room_closed', 'room:<id>', true)`). `by_nickname`은 방장의 이 방 멤버 행 닉네임(없으면 `null`). 받은 클라이언트(방장 포함)는 `removeChannel` → sessionStorage `mushroom:room` 삭제 → 로비 + "방장이 방을 삭제했어요" 배너. 놓친 클라이언트는 다음 `heartbeat`(`NOT_MEMBER`) → `join_room`(`ROOM_NOT_FOUND`)으로 같은 처리.
  - 전달 시점: `realtime.send`는 `realtime.messages` insert이고 Realtime은 커밋된 행만 내보낸다. `delete_room`은 send → delete를 한 트랜잭션에서 하므로 삭제가 커밋될 때 함께 전달되고, 실패·롤백되면 전달되지 않는다. 이미 구독 중인 멤버는 구독 시점에 권한 검사를 통과했으므로 멤버 행이 지워져도 이 이벤트를 받는다.
  - 멤버가 `room_closed`를 직접 위조해 보낼 수도 있다(알려진 한계 1). 받으면 바로 로비로 가되, 방이 실제로 남아 있으면 `list_rooms`에 계속 보인다. 걱정되면 수신 후 `heartbeat`로 확인해 `NOT_MEMBER`/`ROOM_NOT_FOUND`일 때만 배너를 띄운다.

**`realtime.messages` 정책** (마이그레이션 7절)

| 정책 | 대상 | 조건 |
|---|---|---|
| `mushroom_room_members_receive` | select, authenticated | `extension in ('broadcast','presence')` 이고 `realtime.topic()`이 `room:<uuid>`이며 그 방의 유효 멤버(10분 이내) |
| `mushroom_room_members_send` | insert, authenticated | 위와 같음 |

정책은 security definer 헬퍼 `app_private.can_access_room_topic(topic)`을 호출한다(authenticated는 `room_members`를 직접 읽을 수 없으므로). `app_private` 스키마는 Data API에 노출되지 않는다.

`realtime.send` 확인: Supabase 문서 "Broadcast"(Broadcast from the Database 절)에 `realtime.send(payload jsonb, event text, topic text, private boolean)` 시그니처와 "private: true가 기본, 비공개 채널에만 도달" 설명이 있음을 확인했다(2026-10-15). 문서상 `realtime.send`는 실패 시 예외를 삼키고 로그만 남긴다 → 브로드캐스트가 실패해도 메시지 저장은 유지된다. 또 그날의 `realtime.messages` 파티션은 클라이언트가 Realtime에 접속해야 만들어진다(방 멤버는 이미 접속 중이므로 문제없음).

**`realtime.send` 실제 도달은 로컬에서 확인 불가**(스텁으로 호출 기록만 확인). 실 프로젝트에서 `chat`이 오지 않으면: (1) Realtime 로그의 `WarnSendingBroadcastMessage` 확인 (2) `select rolbypassrls from pg_roles where rolname = 'postgres';`가 `true`인지 확인(security definer 함수 소유자 postgres가 `realtime.messages`에 insert한다). 대안: 프런트가 `send_message` 반환값을 직접 `chat`으로 broadcast — 단 이 경우 같은 방 멤버가 다른 사람인 척 채팅을 위장할 수 있다(저장된 기록·`recent_messages`는 위장 불가).

## 테이블 요약

모든 테이블: RLS 켜짐 + `*_no_direct_access` 제한 정책(using false). anon/authenticated는 select/insert/update/delete/truncate 권한이 전혀 없다. 접근은 RPC로만.

| 테이블 | 컬럼 | 제약/인덱스 |
|---|---|---|
| `rooms` | `id uuid PK`, `name`, `password_hash`(null=공개), `locked`(생성 컬럼), `created_by → auth.users`, `created_at`, `last_active_at` | `rooms_name_format`, `rooms_password_hash_format`, idx `(created_by)` |
| `room_members` | PK `(room_id, user_id)`, `nickname`, `joined_at`, `last_seen_at` | `room_members_nickname_format`, unique `(room_id, lower(nickname))`, idx `(room_id, last_seen_at)` |
| `room_messages` | `id bigint identity PK`, `room_id`, `user_id`, `nickname`, `text`, `created_at` | text 1~80자/제어문자 금지, idx `(room_id, id desc)`, `(user_id, created_at desc)` |
| `room_join_failures` | `id`, `room_id`, `user_id`, `created_at` | idx `(user_id, room_id, created_at)`, `(created_at)`. 10분 지난 기록은 `join_room`이 정리 |

FK는 모두 `on delete cascade`(방 삭제 → 멤버/메시지/실패 기록 삭제, auth 사용자 삭제 → 그 사람의 방/멤버/메시지 삭제).

시간 상수: 활성 60초, 유효 멤버(재접속·채팅·채널) 10분, 방 만료 30분, 비밀번호 실패 창 1분/5회, 채팅 1초.

## 알려진 한계

1. **같은 방 멤버끼리의 위장**: `move`와 Presence 상태(닉네임, 아바타)는 같은 방 멤버가 위조할 수 있다. 클라이언트가 `chat` 이벤트를 직접 보내는 것도 정책으로 막지 못한다(프런트가 무시해야 함). 저장되는 채팅은 서버가 발신자·닉네임을 채우므로 위장 불가. 방 밖 사용자는 채널 접근 불가.
2. **익명 계정 무제한**: 방 3개 제한, 비밀번호 시도 제한, 채팅 1초 제한은 계정을 새로 만들면 우회된다. 공개 운영 시 CAPTCHA(Supabase Auth 지원) 추가.
3. **즉시 강퇴 아님**: Realtime은 구독 시점(및 새 JWT 전달 시)에만 정책을 검사하고 연결 동안 캐시한다. 멤버 행이 지워져도 이미 연결된 채널은 JWT 갱신/재연결 때까지 유지된다.
4. **위치 검증 없음**.
5. **bcrypt 72바이트 한계**: 비밀번호 앞 72바이트만 비교된다. 한글 32자(96바이트)는 뒤쪽 일부가 무시될 수 있다(실질적 위험 낮음).
6. **정원 경계**: 비활성(60초~10분) 멤버가 돌아올 때 `heartbeat`가 정원을 확인하지만, 활성 인원 판정은 시각 기준이라 하트비트 직전 순간에는 실제 접속자 수와 다를 수 있다.
7. **만료 방 삭제는 기회적**: 아무도 `list_rooms`를 호출하지 않으면 만료된 방 행이 남는다(목록·입장에서는 이미 제외됨).
8. 채팅 욕설 필터, 신고, 관리자 도구 없음.
