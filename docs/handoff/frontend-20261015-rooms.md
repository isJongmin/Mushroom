# frontend → main / qa / backend / design: 로그인 제거 + 채팅방 (사이클 4, 2026-10-15)

정본: ARCHITECTURE 결정 3~6, "화면 흐름 (사이클 4)", "데이터 모델", "알려진 한계" / backend-20261015-rooms.md, supabase/README.md / design-20261015-rooms.md, screens/{profile,lobby,room}.md, style-guide v4 11장, ui-kit 14~23절, 시안 ref/c4.
커밋하지 않음. 쓰기는 index.html(변경 없음), src/client/, 이 문서만. tests/, docs/design/, supabase/ 수정 없음.

## 1. 구조 변경

| 파일 | 상태 | 내용 |
|---|---|---|
| `src/client/main.js` | 재작성 | 화면 `profile → lobby → room`. 부팅: 프로필(localStorage) 없으면 profile, 있으면 lobby. sessionStorage `mushroom:room` 있으면 `init → joinRoom(비번 없이) → listRooms(이름 조회) → room`, 실패하면 세션 삭제 + 로비 배너. `app.ensureInit()`(익명 로그인 1회, 실패 시 다음 호출에서 재시도). 배경 `.bk-world`는 boot/profile/lobby 유지, room에서 제거. getState 확장 |
| `src/client/screens/profile.js` | 신규 (create.js 이동·개정) | 탭/슬롯/프리셋/회전 미리보기 그대로. 닉네임 형식 검사만(중복 검사·서버 통신 없음), 카운터 N/12, 모드 first("입장하기") / edit("취소"+"저장", Esc=취소) |
| `src/client/screens/lobby.js` | 신규 | 머리줄(작은 로고, 모드 칩, 내 캐릭터 카드 + 꾸미기), 방 목록, 모달 3종, 배너 |
| `src/client/screens/room.js` | 신규 (game.js 이동·개정) | 캔버스/이동/터치/입력은 v3 그대로. 방 HUD, 채팅 로그, 서버 chat 기반 말풍선, 재연결/NOT_MEMBER/나가기 |
| `src/client/ui/modal.js` | 신규 | 모달 공통(focus trap, inert, Esc, 딤 클릭 무시, 포커스 복귀, 1개만) |
| `src/client/ui/chatlog.js` | 신규 | 채팅 로그 패널(데스크톱 접기/펼치기 + sessionStorage `mushroom:logOpen`, 모바일 토글, 배지, 새 메시지 버튼, 자동 스크롤, 200개 상한) |
| `src/client/store.js` | 신규 | `mushroom:profile` 읽기/쓰기(형식 불일치면 null), `mushroom:room` 읽기/쓰기/삭제 |
| `src/client/backend/identity.js` | 신규 | local 모드 userId (브라우저 프로필 단위 + 테스트 훅 `?as=`) |
| `src/client/backend/local.js` | 재작성 | 2.2절 |
| `src/client/backend/supabase.js` | 재작성 | 2.1절 |
| `src/client/backend/common.js` | 재작성 | trim/제어문자/코드포인트 길이, 방 이름·비번·채팅 검사, Presence/chat 페이로드 정리, move throttle |
| `src/client/errors.js` | 재작성 | 오류 코드 13종(ARCHITECTURE 6) + 화면별 문구 표(design handoff 4장 그대로, NETWORK 4맥락) |
| `src/client/constants.js` | 수정 | 로그인 상수(ID_RE, PW_MIN, CHANNEL_NAME, NICK_DEBOUNCE) 삭제. 방/저장소/타이머 상수 추가 |
| `src/client/style.css` | 수정 | 로그인 규칙 삭제, 프로필/로비/모달/로그 보조 규칙 |
| `src/client/ui-kit.css` | 복사 | `docs/design/ui-kit.css` v4 그대로 (직접 수정 금지 규칙 유지) |
| `src/client/screens/login.js`, `create.js`, `game.js` | 삭제 | (create/game은 profile/room으로 이동) |

## 2. 어댑터 구현 요약 (인터페이스는 ARCHITECTURE 6 그대로)

`init() → {userId}`, `listRooms() → [{id,name,locked,members,createdAt}]`, `createRoom({name,password,nickname}) → {roomId}`, `joinRoom({roomId,password,nickname})`, `leaveRoom(id)`, `heartbeat(id)`, `recentMessages(id)`, `sendChat(id,text) → msg`, `connectRoom(id, handlers, self) → {sendMove, updateSelf, leave}`.
handlers: `onSync(list)`(전체 Presence, 나 포함), `onJoin(state)`/`onLeave(state)`(첫 sync 이후의 새 입장/완전 퇴장만, 나 제외, track 갱신은 제외), `onMove(p)`, `onChat(msg)`(id 중복 제거됨), `onStatus('connected'|'disconnected'|'not_member')`.
오류는 항상 `AppError`(`.code` = 13종 중 하나).

### 2.1 supabase.js (코드 리뷰 수준, 실 프로젝트 미검증)
- supabase-js 동적 import(고정 CDN URL), 실패 시 NETWORK(다음 호출에서 재시도). anon key만.
- `init`: `getSession` → 없으면 `signInAnonymously`. `onAuthStateChange`(TOKEN_REFRESHED/SIGNED_IN) → `realtime.setAuth(access_token)` 1회 등록.
- RPC 오류: `error.message`가 알려진 코드면 그 코드, 네트워크(fetch 실패/오프라인) → NETWORK, `42501`/`PGRST301`/401 → 세션 복구 후 1회 재시도, 그 밖 UNKNOWN. `join_room` 반환 `'WRONG_PASSWORD'` → `AppError('WRONG_PASSWORD')`, `'OK'` 외 반환 → UNKNOWN.
- `connectRoom`(join 성공 후 호출됨): `setAuth(access_token)` → `channel('room:<id>', { config: { private: true, presence: { key: userId }, broadcast: { self: false } } })` → SUBSCRIBED 시 `track(self)`. CHANNEL_ERROR/TIMED_OUT/CLOSED: 첫 구독 전이면 reject(NETWORK), 후면 `onStatus('disconnected')`(화면이 1·2·4초 재연결). 구독 10초 타임아웃.
- move: 10회/초 throttle(마지막 값은 반드시 송신) + 정지 600ms 후 `track` 좌표 갱신. 서버 `chat`: 형식 검사(`cleanChatMessage`) + id 중복 제거. `sendChat` 반환값도 같은 `deliver` 경로(브로드캐스트가 안 와도 내 로그에는 남음).
- 하트비트 20초 `setInterval` → NOT_MEMBER면 `onStatus('not_member')`. pagehide → `untrack()`만. `leave()` = interval/timer/리스너 해제 + untrack + removeChannel.

### 2.2 local.js — 서버 규칙 대응표

저장: localStorage `mushroom.local.v4.db` 한 키. 쓰기는 `navigator.locks.request('mushroom.local.v4.db')`로 탭 사이 직렬화(미지원 브라우저는 직렬화 없음, 주석 명시). 실시간: 방별 BroadcastChannel `mushroom:room:<id>`.

| 서버 규칙 (backend handoff / README) | local 구현 |
|---|---|
| 익명 uid | `identity.js`: 브라우저 프로필 단위 `mushroom.local.v4.uid`, 테스트 훅 `?as=` (4장) |
| 방 이름 trim(공백·탭·개행·NBSP·U+3000·BOM) 후 1~24자, 제어문자 금지 → ROOM_NAME_FORMAT | `common.cleanRoomName` (코드포인트 길이, `[\u0000-\u001F\u007F-\u009F]`) |
| 비번 null/'' = 공개, 4~32자(trim 안 함) → PASSWORD_FORMAT, bcrypt | 같은 검사, PBKDF2-SHA256(무작위 salt 16B, 10만 회) 해시만 저장 |
| 닉네임 정규식 → NICK_FORMAT | 같음 |
| 1인당 살아 있는 방 3개 → TOO_MANY_ROOMS (만료 방 제외) | 같음 |
| 만료: last_active_at 30분 지남 + 30분 안에 본 멤버 없음 → 목록 제외, list_rooms 때 삭제 | `roomAlive` 같음, listRooms에서 삭제(멤버/메시지/실패 기록 포함) |
| list_rooms: 활성(60초) 인원, 인원 desc → 최근 활동 desc → 생성 desc, 100개 | 같음 |
| join: 없음/만료 → ROOM_NOT_FOUND, 10분 지난 멤버 행 삭제 | 같음 |
| 잠금 + 비멤버: 1분 5회 실패 → RATE_LIMITED, 비번 없음 = WRONG_PASSWORD(미기록), 틀림 = 기록 후 WRONG_PASSWORD | 같음 (실패 기록은 커밋 후 오류로 던짐), 기록 10분 보관 |
| 재접속(유효 멤버 10분) = 비번 생략 | 같음 |
| 활성 타인 20명 → ROOM_FULL | 같음 |
| 활성 타인 같은 닉(대소문자 무시) → NICK_TAKEN, 비활성(60초 초과) 같은 닉 행은 삭제(양보) | 같음 |
| 본인 재입장 시 닉네임 변경 허용, last_seen 갱신, room.last_active_at 갱신 | 같음 |
| leave_room 멱등, 있으면 last_active 갱신 | 같음 |
| heartbeat: 유효 멤버 아니면 NOT_MEMBER, 60초 넘게 비활성 후 방이 20명이면 NOT_MEMBER | 같음 |
| recent_messages: 유효 멤버만(NOT_MEMBER), 최근 50개 오래된 순 | 같음 |
| send_message: 유효 멤버(NOT_MEMBER), trim 후 1~80자·제어문자 금지(TEXT_FORMAT), 사용자당 1초(모든 방 합산, RATE_LIMITED), 닉네임 = 멤버 행, 방당 50개 유지, 저장 후 채널로 chat | 같음 (`lastChat[uid]`), 저장 후 같은 BroadcastChannel로 `{type:'chat', payload}` 송신 = 서버 송신 흉내 |
| 비공개 채널: 유효 멤버만 구독 | `connectRoom`이 유효 멤버 확인, 아니면 NOT_MEMBER |
| Presence key = user_id, `{user_id,nickname,avatar,x,y}` | join → 2초 heartbeat → 6초 무소식 제거, 응답 `presence-here`는 "이미 있던 사람"(onJoin 없음), pagehide = presence-leave(untrack) |

## 3. 화면별 구현

### profile (profile.md)
- 최초: 작은 로고(h1) + "프로필 만들기"(h2, 진입 포커스) + "입장하기". 수정: 로고 없음, "프로필 수정", "취소"+"저장"(`.cta-pair`), Esc=취소, 취소 후 로비의 "꾸미기"로 포커스.
- 닉네임: 카운터 N/12, 상태 `empty|ok|format`(`data-state`). IME 조합 중 검사 보류, 1자는 안내, 2자 이상 불일치/blur/버튼 → 오류, 한 번 오류 후 즉시 갱신. 주 버튼은 `aria-disabled`(클릭 시 오류 표시 + 필드 포커스).
- 저장: `{nickname, avatar(7키)}`. 실패(STORAGE) → 메모리로 진행 + 로비 정보 배너 1회. 수정 모드 초기 아바타 = 저장 값 sanitize.
- 하단 `.card-foot`: (local) 모드 칩 + "프로필은 이 브라우저에만 저장돼요"(supabase 모드도 문구는 표시).

### lobby (lobby.md)
- 첫 로딩: `ensureInit` + `listRooms` 동안 뼈대 3행 + 개수 자리 로딩 점, 새로고침/만들기 비활성. 실패 → `.bk-empty--error` + "다시 시도"(init 실패면 init부터). 빈 목록 → `.bk-empty` + "방 만들기".
- 행: 방 id 키로 DOM 재사용(순서만 `insertBefore`), 스크롤·포커스 유지, 포커스 행 삭제 시 `#lobby-title`로. 자물쇠, 메타("공개 방 · N분 전 생성"), 인원 칩, 가득 참(행/칩 `.is-full`, 버튼 "가득 참" 비활성), 입장 버튼 aria-label.
- 폴링: 응답 후 5초 `setTimeout` 사슬. 숨김 탭 정지 → 보이면 즉시 1회. 입장/만들기 요청 중 정지(모달이 열려 있기만 하면 계속). 수동 새로고침: 최소 400ms 로딩 점, 끝나면 `role=status` "방 목록을 새로 고쳤어요. N개". 갱신 실패 → 고정 배너, 다음 성공 때 제거.
- 배너: 한 번에 하나, 다음 동작 때 제거, 8초 후 자동 제거(갱신 실패 배너 제외). ROOM_FULL/ROOM_NOT_FOUND → 배너 + 즉시 갱신.
- 방 만들기 모달: 이름 카운터(trim 기준, 입력 시작 후), 제어문자 즉시 오류, 비번 도움말 3상태(빈/4~32 자물쇠/1~3자 오류는 blur·제출 후), 보기 토글(aria-pressed). 오류: 필드(ROOM_NAME_FORMAT, PASSWORD_FORMAT) / 모달 배너(TOO_MANY_ROOMS, RATE_LIMITED + 10초 "N초 뒤 다시", NETWORK_CREATE, UNKNOWN).
- 비밀번호 모달: 1자 이상이면 전송. WRONG_PASSWORD → 필드 오류 + 입력 비움 + 포커스. NICK_TAKEN → 닉네임 모달(비번 메모리 보관, 포커스 복귀 생략).
- 닉네임 모달: 제안값 프로필+"2"(12자면 11자+"2") 전체 선택, 재실패 문구, WRONG_PASSWORD → 비번 모달 오류 상태로, 취소 시 보관 비번 삭제. 프로필은 그대로, 쓴 닉네임은 `mushroom:room.nickname`.
- 모달 공통: `ui/modal.js` — `main#lobby.inert`(미지원 시 aria-hidden) + Tab 순환 직접 구현 + focusin 가드, Esc=취소(처리 중·IME 조합 중 무시), 딤 클릭 무시, 닫으면 연 버튼(사라졌으면 제목)으로 포커스.
- 입장 성공 → sessionStorage `mushroom:room` = `{roomId, nickname}`(키 2개 정확히) → room.

### room (room.md)
- HUD: 방 이름 칩(잠금 방 자물쇠 + 숨김 "비밀번호 방", 최대 360 말줄임) + 인원 칩 "N/20명"(Presence 인원, 20 이상 `.is-full`, 끊김 중 `.bk-dot-off`) + 모드 칩(데스크톱 첫 줄 / 모바일 2줄째) + 힌트(900 미만 숨김) + 나가기(화살표 + "나가기", 처리 중 "나가는 중").
- 로그: 데스크톱 (12,56) 320 x clamp(120, H-328, 240) — CSS가 계산, `.game-stage` = 캔버스 크기. 접기/펼치기(sessionStorage `mushroom:logOpen`) + 접힘 배지, `.game-stage.log-open`(720~1039 배너 이동). 모바일 접힘 기본, "채팅 기록" 토글 + 배지, 펼치면 "닫기"로 포커스, 닫으면 토글로.
- 내용: 입장 시 `recentMessages` → "이전 대화 N개" + 기록 → "<나>님이 들어왔어요". 실시간 chat id 중복 제거, 내 메시지 `--self` + 숨김 "나:". 시스템 입장/퇴장은 Presence join/leave(첫 sync 제외), 퇴장 3초 지연 후 그 사이 재입장이면 둘 다 버림. 연결 끊김/다시 연결됨 + 재연결 후 `recentMessages` id 순서 삽입. 200개 상한. 시각 HH:MM(오늘 아니면 "M월 D일 HH:MM", `<time datetime>`).
- 자동 스크롤: 바닥 24px 이내면 붙임, 아니면 "새 메시지 N개" 버튼(시스템 제외, 99+), 내 메시지는 항상 바닥.
- 말풍선: 서버 chat 이벤트(= onChat)로만. 내 말풍선도 RPC 성공 후(작업 지시대로; design room.md 6장 "보내는 즉시"와 다름 → 7장 참고). 입력 비우기는 전송 시작 시, 실패하면 복구.
- 전송 오류: NETWORK/UNKNOWN "메시지를 보내지 못했어요." 배너 2초, RATE_LIMITED 힌트 칩 "잠시 후 다시 보내 주세요.", TEXT_FORMAT 배너, NOT_MEMBER → 방 연결 끊김 흐름. 클라이언트 1초 쿨다운 유지.
- 상태: joining(방 이름 + 나가기만, 로딩 점, 로그 로딩) / connected / disconnected(재연결 1·2·4초) / failed("다시 연결") / lost(NOT_MEMBER: 같은 닉네임·비번 없이 자동 재입장 1회 → 실패 시 "로비로") / fatal("다시 시도", 로그 숨김).
- 나가기: 확인 없음, `leave()`(채널) + `leaveRoom` 최대 1.5초 → 세션 삭제 → 로비(즉시 목록 갱신). pagehide: 채널 untrack만(작업 지시대로 leave_room 안 보냄; room.md 1.2의 "최선으로 leaveRoom 1회"와 다름 → 7장).
- 정리: rAF, 타이머 Set, AbortController 리스너, 채널 leave, 퇴장 지연 타이머, 로그 DOM, 렌더러 캐시.

## 4. 테스트 훅

### data-testid
- 유지: `mode-badge, global-error, nickname-input, nickname-status(data-state: empty|ok|format), create-submit(프로필 주 버튼: 입장하기/저장), avatar-preview, tab-<part>, slot-<part>-<id>, slot-grid, preset-<0..5>, view-front|side|back, preview-walk, current-part, manifest-error, world-bg, game-canvas, player-count("N/20명"), chat-input, chat-send, chat-counter, chat-hint, chat-error, move-left, move-right, game-banner, reconnect-button(배너 버튼: 다시 연결/다시 시도/로비로)`
- 삭제: `login-*, toggle-*, pw-confirm 등 로그인 전부, error-message(생성 배너), logout`
- 추가
  - 프로필: `profile-title, profile-card, profile-cancel, profile-note, nickname-counter`
  - 로비: `me-card, me-thumb, me-nickname, profile-edit, room-count, room-refresh, room-create, lobby-banner, lobby-status, room-wrap, room-list, room-row(data-room-id, data-locked), room-name, room-meta, room-members, room-enter, room-empty, empty-create, room-error, room-retry, room-limit-note`
  - 모달: `modal-dim, modal-create|modal-password|modal-nick, modal-banner, modal-cancel, pw-toggle, create-name, create-name-counter, create-name-help, create-password, create-password-help, create-submit-room, join-password, join-password-help, join-submit, modal-room-name, room-nick-input, room-nick-status(data-state: empty|ok|format|taken), room-nick-submit`
  - 방: `room-title, room-title-text, room-count-chip, room-leave, log-panel, log-fold(접기/펼치기/닫기), log-unread, log-toggle, log-toggle-unread, chat-log(ol), log-item(data-kind: chat|self|sys|history, data-id), log-loading, log-new`

### `window.__mushroom.getState()`
```
{ screen: 'boot'|'profile'|'lobby'|'room', mode, userId, as,
  profile: { nickname, avatar(7키) } | null,
  create: { mode:'first'|'edit', ready, avatar, nickname, nicknameStatus, tab, view, walking, frame, slots, presets } | null,  // 프로필 화면
  lobby: { state:'loading'|'ready'|'error', busy, banner:{kind,text}|null, modal:'create'|'password'|'nick'|null, count } | null,
  rooms: [{ id, name, locked, members, createdAt }],
  room: { id, name, locked, members(Presence 인원), nickname(방에서 쓰는 닉네임) } | null,
  chatLog: [{ id, user_id, nickname, text, system:false, self } | { id:null, text, system:true, kind:'sys'|'history', error }] (최근 50),
  log: { mobile, open, unread, newMessages, items } | null,
  connection: 'joining'|'connected'|'disconnected'|'failed'|'lost'|'fatal' | null,
  assets, me, players: [{ user_id, nickname, avatar, x, y, dir, lastChat, bubble, anim, frame }] }
```

### local 모드 사용자 흉내 (`?as=`)
- `index.html?as=a` → 그 탭 userId = `as-a`, 프로필 키 = `mushroom:profile:as:a`(사용자별 분리). 값은 그 탭 sessionStorage `mushroom.local.as`에 저장되어 새로고침에도 유지. URL 없이 쓰려면 sessionStorage `mushroom.local.as`에 이름을 넣고 새로고침. 허용 `[A-Za-z0-9_-]{1,32}`(소문자로 정규화).
- `as` 없으면 같은 브라우저 프로필의 모든 탭이 같은 사용자(같은 방에 두 탭 = 같은 멤버 행, Presence 키도 같음).
- 서버 DB: localStorage `mushroom.local.v4.db` (QA가 직접 조작해 만료/정원 등 상황을 만들 수 있음: `rooms[id].last_active_at`, `members[roomId][uid].last_seen_at` ms 값).

## 5. 자체 검증 결과 (Chromium headless, local 모드) — 83/83 PASS

스크립트: `scratchpad/c4fe/verify.py`(+ `extra.py`). 한 컨텍스트에 A(`?as=a`), B(`?as=b`), C(`?as=c`), D(`?as=d`), 모바일 컨텍스트 M, supabase 모드 컨텍스트 S.
- 프로필: 첫 방문 = profile, userId `as-a`, 1자 안내/형식 오류, 저장 7키(as 키).
- 로비/모달: 빈 목록, 만들기 모달 포커스·`inert`, 비번 3자 blur 오류 + 만들기 비활성, focus trap(Tab 7회), Esc 취소 + 포커스 복귀 + inert 해제.
- 방: 생성 → `mushroom:room` 키 정확히 `{roomId,nickname}`, 내 입장 메시지, B 로비 목록에 인원 1, B 입장 → 서로 보임, A에 "하늘이님이 들어왔어요", B에는 A 입장 메시지 없음(첫 sync), HUD 2/20명, 이동 반영, 채팅 양쪽 로그 + 말풍선(A 자신·B 화면) + 중복 0, XSS 문자열 그대로·미실행, 1초 쿨다운 힌트, 접힘 배지 1 → 펼치면 0.
- B 새로고침 → 같은 방 재입장 + "이전 대화 N개" + 방 이름 복구, A에 퇴장/입장 메시지 없음(3초 규칙). B 나가기 → 로비 + 세션 삭제, A에 3초 뒤 "하늘이님이 나갔어요".
- 잠금 방: HUD/목록 자물쇠, 비밀번호 모달, 틀린 비번 → 필드 오류 + 입력 비움, 맞는 비번 → 입장. C(프로필 닉 = A와 같음) → NICK_TAKEN 닉네임 모달, 제안 "버섯이2" 전체 선택, 비번 재입력 없이 입장, 방 닉네임/세션 = 버섯이2, 프로필 그대로. C 새로고침 → 잠금 방 비번 없이 재입장, 나간 뒤 비번 없이 → WRONG_PASSWORD. D 5회 실패 후 6번째 RATE_LIMITED 배너 + "N초 뒤 다시".
- 누수: 방 3회 입퇴장 후 live interval·열린 BroadcastChannel 증가 0, `.screen` 1개. 숨김 탭 6초 동안 폴링 0, 보이면 즉시 1회.
- 모바일 360x640: 로비 가로/페이지 스크롤 없음, 로그 기본 접힘, 캔버스 360x508, 토글 → 펼침 344x282 + "닫기" 포커스 → 닫으면 토글 포커스.
- 데스크톱 로그 320x212 at (12,56). 1920x1080: 캔버스 1920x810, 로그 240. 900x700: 로그 212, `.log-open`, 24자 방 이름 칩 347px 인원 칩과 안 겹침. 가로 스크롤 없음.
- 프로필 수정: 꾸미기 → edit, Esc → 로비 + 꾸미기 포커스, 저장 → 로비 닉네임 갱신. ROOM_NOT_FOUND → 배너 + 목록에서 제거. 방이 사라진 뒤 새로고침 → 로비 + 재입장 실패 배너.
- supabase 모드(config.js를 라우트로 가짜 URL/키 서빙, jsdelivr·supabase 차단): 프로필 → 로비 첫 로딩 오류 + 다시 시도(재시도도 오류 상태, 예외 없음), 고정 CDN URL 요청 확인, 재입장 실패 → 로비 배너, 모드 칩 숨김.
- 콘솔 에러/경고 0 (S의 차단 요청에 대한 브라우저 자체 `net::ERR_FAILED` 2건 제외).
- 시안 비교: lobby-desktop/mobile, lobby-empty, modal-create/password/nick, room-desktop/collapsed/mobile/mobile-log, profile-first/desktop/mobile와 배치·크기·문구 일치 확인. 1회차 수정: 진입 포커스를 받은 제목(h2 tabindex=-1)에 포커스 링이 그려짐 → 제목 포커스 링 제거.

스크린샷 `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c4fe/shots/`:
`d-1-profile-first, d-2-lobby-empty, d-3-modal-create-error, d-4-room-desktop, d-4b-room-desktop-B, d-5-room-collapsed, d-6-lobby-desktop, d-7-modal-password-wrong, d-9-profile-edit, d-10-lobby-notfound, d-11-lobby-error-supabase, m-1-profile, m-2-lobby, m-3-room, m-4-room-log, m-5-modal-password, m-6-modal-create, m-8-modal-nick, w-1920-room, w-900-room`

## 6. 기존 `tests/e2e_local.py` 영향 (수정하지 않음): 3 PASS / 18 FAIL

| 항목 | 결과 | 원인 | QA가 바꿀 것 |
|---|---|---|---|
| 1 가입→생성→게임, 세션 복구 | FAIL | 로그인/가입 화면·`toggle-signup` 등 삭제. 화면 이름 `login/create/game` → `profile/lobby/room` | profile(닉네임+슬롯) → lobby → 방 만들기 → room, 새로고침 재입장 |
| 2 가입/로그인 오류 문구 | FAIL | 기능 폐기 | 삭제. 대신 로비 오류 문구(lobby.md 9장) |
| 3 닉네임 중복/형식 | FAIL | 전역 중복 검사 폐기(같은 방 활성 멤버만). 문구 해요체 | NICK_TAKEN 모달(같은 방), 형식은 `nickname-status=format`, 어댑터 `joinRoom` 직접 호출 |
| 4 계정당 캐릭터 1개 | FAIL | characters 폐기 | 삭제 (또는 TOO_MANY_ROOMS 4번째 방) |
| 5 두 페이지 동시 접속 | FAIL | 같은 컨텍스트 두 탭이 같은 사용자. 맵 → 방 | `?as=a`/`?as=b` + 같은 방 입장 |
| 6 XSS | FAIL | 부트 화면 기대 불일치 | 채팅 + 방 이름 + 방 닉네임에 페이로드, 로그(`log-item`)/목록 확인 |
| 7 80자, 1초 쿨다운 | FAIL | 같음 | 방 안에서 동일 검사 + 서버 RATE_LIMITED 힌트 |
| 8 탭 닫기 → 제거 6초 | FAIL | 같음 | `?as=` 두 탭, 방에서 닫기 → Presence 제거 + 3초 뒤 퇴장 메시지 |
| 9 로그아웃 | FAIL | 기능 폐기 | "나가기" → 로비, 세션 삭제, 상대 퇴장 메시지 |
| 11 모바일 360x640 | FAIL | 부트 기대 | 방 화면에서 동일(캔버스 360x508), 로그 접힘 |
| 12 로그인/로그아웃 3회 누수 | FAIL | 같음 | 방 입퇴장 3회 (자체 검증과 같은 방식) |
| 13 픽셀 선명도 | FAIL | 게임 진입 불가 | 방 화면에서 HUD + `.room-log` + `.hud-row2` 숨기고 측정 (로그 패널이 캔버스 위 겹침) |
| 14 애니메이션 | FAIL | 같음 | 방에서 동일 |
| 15 에셋 로드 | FAIL | 부트 기대 | 방 화면에서 동일(에셋 경로/개수 변화 없음) |
| 16 레이아웃/모드 칩 겹침 | FAIL | 같음 | 방 화면: 겹침 검사에서 `game-canvas`, `log-panel` 제외(설계상 캔버스 위 겹침). 로비/프로필 추가 |
| 19 생성 화면 | FAIL | `create` 화면 없음 | profile 화면에서 동일(testid 유지), getState `create.mode` 추가 확인 |
| 20 저장 avatar 7키 | FAIL | 저장 위치 변경 | localStorage `mushroom:profile`(또는 `:as:<이름>`) `.avatar` |
| 21 사이클 1 호환 | FAIL | 저장 위치(`mushroom.local.characters.v1`) 폐기 | `mushroom:profile.avatar`에 옛 5키를 넣고 로비/방에서 정규화 확인, Presence 옛 형식 |
| 10 콘솔 에러 0 | PASS | | |
| 17, 18 아트 빌드 | PASS | 프런트 무관 | |

## 7. 다른 역할에 요청 / 확인

- 메인/디자인 (정본 불일치, 작업 지시를 따름)
  1. 내 말풍선: 작업 지시 "RPC 성공 후" ↔ room.md 6장 "보내는 즉시". 지시대로 구현(로컬 수십 ms, supabase는 RPC 왕복만큼 늦게 뜸). 정본 문구 정리 요청.
  2. pagehide: 작업 지시 "untrack만" ↔ room.md 1.2 "leaveRoom 최선 1회". 지시대로(멤버 행은 60초 활성 규칙 + 새로고침 재입장 보호). room.md 갱신 요청.
  3. ARCHITECTURE 테스트 훅 항목에 4장(getState 필드, `?as=`) 기록 요청.
- 백엔드: 요청 없음. `heartbeat`의 NOT_MEMBER 원인이 정원/닉네임 양보일 때 클라이언트는 자동 `join_room` 1회로 정확한 사유를 받지만, 화면은 사유와 무관하게 "방과 연결이 끊어졌어요" 배너로 끝낸다.
- 아트: 요청 없음.

## 8. QA 확인 항목

1. 6장 표대로 e2e 갱신 후 전부 PASS. 자체 검증 스크립트(`verify.py`)의 시나리오를 참고.
2. profile.md 9장, lobby.md 11장, room.md 10장 체크리스트 (특히 360px 모달 키보드 상태, 실기기 소프트 키보드에서 로그 높이 최소 96).
3. 실 Supabase(backend handoff 7장): 익명 로그인, 두 브라우저(다른 uid) 실시간 chat/move/presence, `chat`이 서버에서 오는지(안 오면 README 점검), 토큰 갱신 후 채널 유지, 비멤버 구독 CHANNEL_ERROR → 화면 "방에 들어갈 수 없어요"(fatal) 처리.
4. 모달 접근성: Safari 15.4 미만(`inert` 미지원) focus trap 대체 경로, 스크린 리더로 로그 `role=log` 읽기(기록 50개 일괄 삽입 시 aria-busy).
5. 동시성(local): Web Locks 없는 브라우저에서 같은 닉네임 동시 입장(알려진 한계).
6. 방 닉네임/방 이름/채팅에 HTML·제어문자·전각 공백·이모지 입력 → 서버와 같은 판정, 화면 주입 없음.

## 9. 알려진 한계

- supabase 모드는 실제 프로젝트 없이 코드 리뷰 + CDN 차단 오류 경로만 확인. `presence` join/leave 판정(currentPresences 기준)과 `realtime.setAuth(token)` 동작은 supabase-js 2.45.4 소스 기준 추정.
- 서버 `chat` 브로드캐스트와 멤버의 위조 `chat` 브로드캐스트는 수신 측에서 구분할 수 없다(형식 검사만). 위조는 로그·말풍선에 보일 수 있으나 새로고침/재연결 시 `recent_messages`(신뢰 기록)에는 없다(ARCHITECTURE 알려진 한계 1).
- local 모드: Web Locks 미지원 브라우저에서는 탭 간 쓰기 직렬화 없음. 같은 브라우저 프로필 안에서만 동작. `?as=` 없이 두 탭 = 같은 사용자.
- 재연결 후 `recentMessages` 병합은 id 순서 삽입이라, 로그 위쪽에 끼워 들어간 메시지는 "새 메시지" 수에 세지 않는다.
- 탭을 닫으면 멤버 행은 60초 동안 활성으로 남아 목록 인원이 최대 60초 늦게 줄어든다(설계 수용).
- NOT_MEMBER 자동 재입장은 비번을 보관하지 않으므로 멤버 행이 지워진 잠금 방이면 실패 → "로비로" 배너(design handoff 8장 확인 요청 사항 그대로).
- 시스템 폰트라 플랫폼마다 말풍선/로그 줄바꿈 위치가 다르다. Safari/Firefox, dpr 2/3 미검증.

## 10. QA 사이클 4 수정 (2026-10-15, docs/qa/qa-20261015-cycle4.md)

### D-1 (중간, 항목 16): 두 번째 끊김부터 자동 재입장 안 함
- 원인: `room.js` `memberLost()`의 `rejoinTried`가 재입장 **실패** 경로(firstJoin NOT_MEMBER)에서만 초기화되고, 재입장 **성공** 뒤에는 true로 남았다 → 같은 세션의 두 번째 NOT_MEMBER는 곧바로 `lost` 배너.
- **메인 결정 (기록)**: "NOT_MEMBER 시 자동 재입장 1회"는 세션당 1회가 아니라 **끊김이 생길 때마다 1회**다.
  - 끊김 하나에 재입장(`joinRoom` 같은 닉네임, 비밀번호 없음 → 채널 재연결) 시도 1번. 그 시도가 실패하면 배너 "방과 연결이 끊어졌어요. 로비에서 다시 들어와 주세요." + "로비로".
  - 재입장 성공(정상 연결 복구) 시 플래그 초기화 → 다음 끊김에서 다시 1회 시도.
  - 무한 루프 방지: 직전 시도 시작 후 **최소 10초**(`REJOIN_MIN_GAP_MS`)가 지나기 전에 새 끊김이 오면 남은 시간만큼 기다렸다가 시도한다(즉시 배너가 아니라 지연 시도). 시도 중·대기 중 들어오는 추가 NOT_MEMBER 신호(하트비트, 전송 실패, 재연결 실패)는 같은 끊김으로 보고 무시. 대기 타이머는 화면 타이머 Set에 있어 나가기/unmount 때 해제.
  - design `room.md` 7장 문구 정리는 메인 담당(이 문서만 기록, room.md 수정 안 함).
- 수정: `memberLost()` → `rejoinBusy` + `lastRejoinAt` + `tryRejoin()` (src/client/screens/room.js).

### D-2 (낮음): 360x640에서 펼친 로그가 HUD 2줄째와 LOCAL MODE 칩을 덮음
- 원인: ui-kit 23절 모바일 `.room-log { top: 46px }`가 2줄째(top 46, 높이 32 + 아래 두께 4)와 같은 위치에서 시작.
- 수정: `src/client/style.css` 모바일 미디어 쿼리에서만 `.game-stage .room-log { top: 88px; height: clamp(96px, calc(100% - 268px), 320px) }` (ui-kit 복사본은 그대로). 아래 끝 = 캔버스 아래에서 180px(내 캐릭터 머리 위) 유지.
- 결과: 360x640에서 펼친 로그 (8, 88) 344 x **240**, 2줄째(46~78)와 칩(50~74) 안 덮음. 데스크톱 1280x800은 그대로 (12, 56) 320 x 212.
- **디자인 요청**: room.md 4.2의 모바일 펼친 패널 규격(top 46, 344 x 282, `clamp(96, H - 226, 320)`)을 top 88, `clamp(96, H - 268, 320)`(360x640 → 240)으로 갱신하고, 같은 값을 ui-kit 23절에 반영하면 style.css의 덮어쓰기를 지운다.
- 캡처: `scratchpad/c4fe/shots/m-5-room-log-fixed.png`

### 함께 고친 것 (작은 표시 결함)
- 입장 직후 내 메시지가 기록보다 먼저 실시간으로 도착하면, "이전 대화 N개"가 이미 있는 메시지까지 세었다 → 실제로 끼워 넣은 기록 수로 센다(0개면 구분 줄 없음). `src/client/ui/chatlog.js`.

### 검증
- `python3 tests/e2e_local.py` 전체 (QA 갱신본, 수정 없음): **PASS 28 / FAIL 0 / UNVERIFIED 3 (12, 20, 30)**. 항목 16 PASS(두 번째 끊김 자동 복구 포함), 13·21 PASS.
- 콘솔 에러 0.
