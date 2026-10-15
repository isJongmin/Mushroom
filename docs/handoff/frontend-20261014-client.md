# frontend → main: 정적 웹 클라이언트 1차 (2026-10-14)

정본: docs/ARCHITECTURE.md, docs/design/style-guide.md, docs/design/screens/*.md, docs/handoff/backend-20261014-schema.md.
빌드 도구 없음. 네이티브 ES 모듈. 외부 라이브러리는 supabase 모드일 때만 supabase-js(고정 CDN)를 동적 import 한다.
모든 경로는 상대 경로라 GitHub Pages 하위 경로(`https://<user>.github.io/Mushroom/`)에서 그대로 동작한다.

## 1. 파일 구조

| 파일 | 설명 |
|---|---|
| `index.html` | 진입점. `#app` 하나, `src/client/style.css`, `src/client/main.js`(module). favicon 요청 404 방지용 `data:` 아이콘 |
| `src/client/config.js` | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (기본 빈 값 → local 모드). service_role 금지 주석 |
| `src/client/constants.js` | style-guide 값(색, 월드, 시야, 아바타, 라벨, 말풍선), 정규식, 네트워크 제한, CDN URL, 기본 파츠 목록 |
| `src/client/errors.js` | `AppError(code)`, 화면별 오류 문구 표(디자인 문서 문장 그대로) |
| `src/client/dom.js` | `h()` DOM 헬퍼(문자열은 항상 텍스트 노드), `setText()`(textContent), `wait()` |
| `src/client/main.js` | 부트(세션 복구, 3초 제한), 화면 전환(직렬화, 이전 화면 unmount 후 mount), 모드 배지, `window.__mushroom` |
| `src/client/assets.js` | `assets/avatar/manifest.json` fetch + 검증, 파츠 SVG/`assets/map/background.svg` 로드, `sanitizeAvatar()` |
| `src/client/avatar.js` | layerOrder로 파츠 합성 → 조합+해상도별 캔버스 캐시(LRU 96). SVG가 없는 파츠는 style-guide 5.3 좌표의 단색 도형 폴백. x=32 기준 반전 |
| `src/client/backend/index.js` | config로 어댑터 선택. local 모드에서는 `supabase.js`를 import하지 않는다 |
| `src/client/backend/common.js` | 아이디/비밀번호/닉네임/아바타 형식 검사(DB 제약과 동일 규칙) |
| `src/client/backend/local.js` | local 어댑터 (아래 3장) |
| `src/client/backend/supabase.js` | supabase 어댑터 (아래 3장) |
| `src/client/screens/login.js` | 로그인/회원가입 (screens/login.md) |
| `src/client/screens/create.js` | 캐릭터 생성 (screens/character-create.md) |
| `src/client/screens/game.js` | 인게임: 루프, 입력, 네트워크, HUD, 재연결, 정리 |
| `src/client/game/world.js` | 배경. background.svg가 있으면 월드 크기로 래스터화해 캐시, 없으면 팔레트로 직접 그림 |
| `src/client/game/overlay.js` | 닉네임 라벨, 말풍선(줄바꿈/4줄/…/페이드/화면 안 보정) — Canvas `fillText`만 사용 |
| `src/client/game/input.js` | 누른 순서 기반 이동 입력(키보드+터치 공통, 나중 누른 방향 우선) |
| `src/client/style.css` | CSS 토큰(:root), 세 화면 데스크톱/모바일(720px 미만) 레이아웃 |

## 2. 실행 방법

### local 모드 (기본, 개발·QA)
```sh
# 저장소 루트에서
python3 -m http.server 8123
# http://localhost:8123/ 접속. 화면 왼쪽 위에 "LOCAL MODE" 배지
```
- `file://`로 열면 ES 모듈과 Web Crypto가 막힌다. 반드시 http(s) 또는 localhost로 연다.
- 같은 브라우저의 여러 탭이 같은 마을에 들어온다. 탭마다 다른 계정을 쓸 수 있다(세션은 탭별 sessionStorage).
- 데이터 초기화: 개발자 도구에서 `localStorage.removeItem('mushroom.local.accounts.v1')`, `...characters.v1`.

### supabase 모드
1. supabase/README.md 대로 마이그레이션 적용, Confirm email 끄기.
2. `src/client/config.js`에 Project URL, anon key 입력. 배지가 "SUPABASE MODE"로 바뀐다.
3. supabase-js는 `https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm`에서 처음 필요할 때 로드된다.

## 3. backend 어댑터

공통 인터페이스(두 어댑터 동일, 모두 async):
`signUp(id, pw)`, `signIn(id, pw)`, `signOut()`, `getSession()`, `getMyCharacter()`, `createCharacter(nickname, avatar)`, `isNicknameTaken(nickname)`, `joinMap(handlers, self) → { sendMove({x,y,dir}), sendChat(text), leave() }`, `leaveMap()`.
- `handlers = { onPresence(list), onMove(payload), onChat(payload), onStatus('connected'|'disconnected') }`
- `self = { user_id, nickname, avatar, x, y }` (Presence 상태). `dir`는 `'left'|'right'`로 송신(수신은 ±1도 허용).
- 실패는 항상 `AppError(code)`: `ID_FORMAT, PW_SHORT, ID_TAKEN, LOGIN_FAILED, NICK_FORMAT, NICK_TAKEN, CHAR_EXISTS, AVATAR_FORMAT, AUTH_REQUIRED, NETWORK, SERVER`. 화면이 code를 디자인 문구로 바꾼다.
- ARCHITECTURE의 `leaveMap`도 구현했다. `joinMap`이 Promise를 반환한다는 점(연결 완료 후 resolve)은 ARCHITECTURE에 명시되어 있지 않다 → 메인이 기록해 주면 좋다.

local (`backend/local.js`, 개발용임을 파일 주석에 명시):
- 계정: localStorage, 비밀번호는 PBKDF2-SHA256(무작위 16바이트 salt, 100,000회) 해시만 저장. 로그인 실패 시 계정 유무와 관계없이 해시 계산(응답 시간 차이 완화).
- 캐릭터: localStorage. 계정당 1개(`CHAR_EXISTS`), 닉네임 대소문자 무시 중복(`NICK_TAKEN`), 형식 검사는 DB 제약과 동일.
- 실시간: `BroadcastChannel('mushroom:map:village')`. join → heartbeat 2초 → 6초 무응답 제거, join 받으면 즉시 heartbeat 응답, `pagehide`에서 leave 송신, 탭이 다시 보이면 즉시 heartbeat. 메시지 형식은 Supabase와 같은 payload.

supabase (`backend/supabase.js`): 오류 매핑은 backend handoff 그대로.
- Auth: `user_already_exists`→ID_TAKEN, `invalid_credentials`→LOGIN_FAILED, `weak_password`→PW_SHORT, 429/`over_request_rate_limit`→SERVER, `email_not_confirmed`/가입 후 session 없음→SERVER, fetch 실패→NETWORK.
- insert: 23505+`characters_nickname_lower_key`→NICK_TAKEN, 23505+`characters_pkey`→CHAR_EXISTS(재조회 후 게임으로), 23514+`characters_nickname_format`→NICK_FORMAT, 23514+`characters_avatar_shape`→AVATAR_FORMAT, 23502→SERVER, 42501→AUTH_REQUIRED(로그아웃 후 로그인 화면).
- 채널: `channel('map:village', { presence: { key: uid }, broadcast: { self: false } })`, public. SUBSCRIBED 후 `track`. 정지 600ms 뒤 Presence 좌표 재-track(새로 들어온 사람이 올바른 위치를 보도록).

## 4. 화면/게임 구현 요약
- 흐름: 부트 스피너(세션 확인 최대 3초, 넘으면 로그인+NETWORK 배너) → 로그인/가입 → 캐릭터 없으면 생성 → 게임. 새로고침 시 세션 복구. 전환 페이드 200ms, 히스토리를 쌓지 않음.
- 로그인: 탭(role=tablist), blur/제출 검증, 첫 오류 필드 포커스, LOGIN_FAILED 시 비밀번호만 비우고 포커스, IME 조합 중 Enter 무시, 아이디에서 Enter → 비밀번호로, 처리 중 전체 비활성+스피너.
- 생성: 미리보기(데스크톱 3배/모바일 2.5배), 파츠 행 순환/방향키/aria-live, 닉네임 상태 7종(500ms 디바운스+blur 확인, 오래된 응답 무시), 생성 실패 처리 표대로.
- 게임: Canvas 2D, 시야 960x540(모바일 480x270, camY 200), 카메라/배율/dpr 규칙, 160px/s, dt 0.1초 클램프, 이동 흔들림 2px/0.4초, 그리기 순서(배경→다른 아바타→나→라벨→말풍선). 원격 아바타는 지수 보간(400px 넘게 차이 나면 순간 이동).
- 입력: ←/→, A/D(`e.code` 기준이라 한글 자판에서도 동작), 나중 누른 방향 우선, repeat 무시, 창 blur/숨김/채팅 포커스 시 눌림 초기화. Enter 채팅 포커스/전송, Esc 해제. 모바일 터치 버튼 pointer 이벤트.
- 네트워크: move 100ms 간격 이하 + 좌표/방향 변화 시에만. chat trim, 80자, 1초 쿨다운(힌트 0.8초), 내 말풍선 즉시 표시, 전송 실패 시 입력 복구+2초 오류. 수신: Presence에 없는 user_id의 move/chat 버림, chat 80자 초과는 버림, 제어 문자는 공백으로, 닉네임 형식이 틀리면 `???`, 아바타 id는 manifest 목록에 없으면 기본값.
- 연결: 입장 중/정상/끊김(자동 재연결 1·2·4초 3회)/재연결 실패("다시 연결")/치명적 오류("다시 시도") 배너. 끊김 중 이동 정지, 접속자 배지 옆 `•`.
- 정리: 로그아웃/화면 전환 시 rAF 취소, AbortController로 모든 리스너 해제, 타이머 해제, 채널 leave(BroadcastChannel close / removeChannel), 상태 공급자 해제.
- XSS: innerHTML 사용 0건. 사용자 문자열은 textContent 또는 Canvas fillText로만 출력.
- 처리되지 않은 Promise 거부는 `unhandledrejection`에서 막고 상단 토스트(SERVER 문구)로 표시.

## 5. 테스트 훅

data-testid:

| 화면 | testid |
|---|---|
| 공통 | `mode-badge`, `error-message`(현재 화면의 오류 배너), `global-error`(전역 토스트) |
| 로그인 | `login-id`, `login-pw`, `login-pw-confirm`, `login-submit`, `toggle-login`, `toggle-signup`, `pw-toggle`, `error-id`, `error-pw`, `error-pw-confirm` |
| 생성 | `nickname-input`, `nickname-status`(속성 `data-state` = empty/format/unchecked/checking/available/taken/failed), `create-submit`, `logout`, `avatar-preview`, `part-row-<part>`, `part-prev-<part>`, `part-next-<part>`, `part-value-<part>` (part = skin/hair/eyes/top/bottom) |
| 게임 | `game-canvas`, `player-count`, `logout`, `chat-input`, `chat-send`(모바일), `chat-counter`, `chat-hint`, `chat-error`, `move-left`, `move-right`, `game-banner`, `reconnect-button` |

`window.__mushroom.getState()` (읽기 전용: 재할당 불가, 반환값 deep-freeze된 복사본):
```js
{
  screen: 'boot'|'login'|'create'|'game',
  mode: 'local'|'supabase',
  connection: null|'joining'|'connected'|'disconnected'|'failed'|'fatal',
  assets: null | { source: 'manifest'|'fallback', images: <로드된 파츠 SVG 수>, background: <bool> },
  me: { user_id, nickname, avatar, x, y, dir, lastChat } | null,
  players: [{ user_id, nickname, x, y, lastChat }]   // 나 포함, x는 화면에 그려지는(보간된) 값
}
```
`lastChat`은 마지막으로 받은(내 것은 보낸) 채팅 문자열이며 말풍선이 사라져도 남는다.

## 6. 자체 검증 결과 (2026-10-14)
환경: Python Playwright + Chromium(headless), `python3 -m http.server 8123`. 스크립트와 스크린샷: 스크래치 디렉터리 `.../scratchpad/fe/` (저장소 밖).
같은 브라우저 컨텍스트에 페이지 A·B를 열어 각각 가입 → 캐릭터 생성 → 게임 입장.

| 항목 | 폴백(에셋 404 강제) | 실제 에셋(manifest + SVG 16 + 배경) |
|---|---|---|
| 모드 배지 LOCAL MODE, 로그인 화면 | 통과 | 통과 |
| 가입 필드 오류(ID_FORMAT) | 통과 | 통과 |
| A·B 가입→생성→입장, 서로 2명으로 보임, "접속 중 2명" | 통과 | 통과 |
| 닉네임 대소문자 무시 중복 → "이미 사용 중" | 통과 | 통과 |
| A 오른쪽 1초 이동 ≈160px, B의 getState에 A 좌표 반영(오차 1.5px 이내) | 통과 | 통과 |
| KeyA 왼쪽 이동, Enter 채팅 포커스, 입력 중 방향키 무시, Esc 해제 | 통과 | 통과 |
| A 채팅 → B `lastChat` 수신, `<b>` 문자열이 DOM에 주입되지 않음 | 통과 | 통과 |
| 1초 쿨다운 힌트 + 입력 유지, 쿨다운 뒤 전송, maxlength 80 | 통과 | 통과 |
| Presence에 없는 user_id(move/chat) 무시, 81자 chat 버림 | 통과 | 통과 |
| `__mushroom` 재할당/변경 불가 | 통과 | 통과 |
| 새로고침 세션 복구 → 게임, 상대 목록 유지 | 통과 | 통과 |
| B 탭 닫기 → A에서 즉시 제거(pagehide leave) | 통과 | 통과 |
| 로그아웃 → 로그인, 틀린 비밀번호 LOGIN_FAILED 문구 + 비밀번호 비움, 재로그인 → 게임 | 통과 | 통과 |
| 비밀번호 평문 미저장(해시만) | 통과 | 통과 |
| 360x640 모바일: 캔버스 328x185, 가로 스크롤 없음, 터치 버튼 56px, 터치 이동 | 통과 | 통과 |
| 에셋 소스(fallback 0장 / manifest 16장+배경) | 통과 | 통과 |
| 콘솔 에러 0건 | 통과(의도한 에셋 404 로그만 제외) | 통과 |

추가 확인:
- 누수: 로그인→게임→로그아웃 3회 반복. 게임 중 [BroadcastChannel 1, interval 2, rAF 1] → 로그아웃 후 [0, 0, 0]. 통과.
- supabase 모드 오류 경로: config를 채우고 CDN 차단 → 배지 SUPABASE MODE, 0.5초 안에 로그인 화면 + NETWORK 배너, 로그인 제출 시 NETWORK 배너, 화면 멈춤 없음. 통과 (브라우저 자체의 `net::ERR_FAILED` 로그 1건은 남는다).
- 스크린샷을 직접 보고 확인: 로그인 카드/탭/버튼 색, 생성 화면 2열 배치와 상태 줄, 게임 HUD 위치, 내 라벨 주황/상대 라벨 어두운 반투명, 말풍선 4줄+`…`, 모바일 세로 순서(상단 바 → 캔버스 → 터치 → 채팅).
- 검증 중 고친 결함: (1) 정규식 리터럴 안의 U+2028/2029 문자로 모듈 파싱 실패 → 이스케이프로 수정, (2) 모바일에서 첫 배치 때 HUD가 잠깐 넘쳐 `innerWidth`가 커지고 캔버스가 448px로 고정되던 문제 → `documentElement.clientWidth` 기준으로 수정, (3) 폴백 구름 타원 사이 연결선 잔상 → 타원마다 경로 분리.

미검증: 실제 Supabase 프로젝트(인증, RPC, insert 오류 형식, Realtime Presence/Broadcast, 재연결), Safari/Firefox, 실제 터치 기기, 한글 IME 실입력(headless에서는 조합 이벤트를 재현하지 않았다).

## 7. QA 확인 항목
1. 위 6장 표 전 항목을 tests/에서 재현 (local 모드, 한 컨텍스트 두 페이지).
2. 디자인 문구 정확성: login.md 4장, character-create.md 7장, game.md 5.2/7장 문장과 화면 문구 비교.
3. 키보드: 로그인 Tab 순서, 생성 화면 파츠 행 좌/우 방향키, 게임 Enter/Esc, 두 방향 키 동시 누름(나중 키 우선, 한쪽 떼면 남은 쪽).
4. 한글 IME: 조합 중 Enter로 전송/제출되지 않는지(실제 브라우저에서).
5. 360px 체크리스트(game.md 10장), 소프트 키보드 표시 시 채팅 행 보임.
6. 말풍선: 공백 없는 긴 한글, 4줄 초과 `…`, 화면 가장자리에서 8px 안으로 밀림과 꼬리 방향, 5초+0.5초 페이드, 같은 사용자의 새 말풍선 교체.
7. supabase 모드(프로젝트 준비 후): backend handoff QA 1~8, 18, 19를 실제 UI로 확인. 두 브라우저(컨텍스트)로 실시간 확인.
8. 재연결 배너: supabase 모드에서 네트워크 끊기(오프라인 전환) → 끊김 배너 → 복구 시 0.5초 페이드, 3회 실패 시 "다시 연결".

## 8. 알려진 한계
- local 모드는 개발용이다. localStorage 동시 쓰기에 잠금이 없어(탭 간 경쟁) 같은 닉네임을 정확히 같은 순간에 만들면 둘 다 성공할 수 있다.
- local 모드에서 같은 계정을 두 탭에서 열면 같은 user_id라 서로를 보지 못한다(자기 자신으로 취급).
- 숨김 탭은 브라우저가 타이머를 늦춘다. 5분 이상 숨겨 두면(Chrome intensive throttling) heartbeat가 6초를 넘겨 다른 탭에서 잠시 사라질 수 있다. 다시 보이면 즉시 복귀한다.
- supabase 모드에서 한 브라우저의 탭들은 supabase-js 세션(localStorage)을 공유한다. 탭마다 다른 계정을 쓰려면 다른 브라우저/프로필(QA는 다른 컨텍스트)을 써야 한다.
- Broadcast 발신자 위조는 ARCHITECTURE 한계 그대로(Presence에 있는 다른 user_id로 위조하면 통과). Presence의 nickname/avatar는 DB와 대조하지 않는다(형식/목록 검사만).
- 재연결 시 supabase-js 자체 재접속과 클라이언트 재시도가 함께 동작한다. 실제 환경에서 확인 필요.
- 80자 채팅은 말풍선 4줄을 넘으면 `…`로 잘린다(디자인 결정). 채팅 기록 없음.
- 로그인 화면 Tab 순서는 디자인 문서 두 문장이 서로 다르다("탭→아이디→비밀번호→(확인)→보기 토글→제출" vs "토글은 비밀번호 필드 바로 뒤"). 구현은 DOM상 비밀번호 바로 뒤에 토글을 두었다(아이디→비밀번호→보기→확인→제출). 디자인 확인 요청.

## 9. 다른 팀 요청
- 메인: ARCHITECTURE 5번 어댑터 인터페이스에 `joinMap(handlers, self)` 시그니처, Promise 반환, `onStatus`, `dir` 값(`'left'|'right'`) 기록 요청.
- 디자인: 위 Tab 순서 모순 정리. 로그인 아이디/비밀번호 도움말 문구("영문 소문자, 숫자, 밑줄(_) 4~16자", "8자 이상")는 문서에 없어 프런트가 정했다. 확정 요청.
- 아트: 현재 manifest와 SVG 16개, background.svg(2400x540)로 정상 동작 확인. background.svg는 월드 전체(0,0)~(2400,540)에 그대로 깐다는 가정이다. 이 가정을 ARCHITECTURE 계약에 넣어 주면 좋다.
- 백엔드: 없음.
