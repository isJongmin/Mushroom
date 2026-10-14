# frontend → main: 블록 스타일 반영 (사이클 3, 2026-10-14)

정본: docs/ARCHITECTURE.md "인터페이스 계약", "블록 아트 계약" / art-20261014-block-final.md / design-20261014-block-ui.md, style-guide v3, screens/*.md v3 / backend-20261014-avatar-v3.md.
커밋하지 않음. assets/, docs/design/, tests/ 수정 없음.

## 1. 변경 구조

| 파일 | 내용 |
|---|---|
| `index.html` | `src/client/ui-kit.css` → `src/client/style.css` 순서로 로드 |
| `src/client/ui-kit.css` (신규) | `docs/design/ui-kit.css` **그대로 복사** (직접 수정 금지, 디자인이 바꾸면 다시 복사) |
| `src/client/style.css` | 전면 교체. 사이클 2 픽셀 스킨/`border-image`/`assets/ui` 참조 전부 삭제. 프런트 전용 규칙만 (`[hidden]`, `p.bk-help` 여백, 방향 버튼 `aria-checked` 활성 모양, 미리보기 캔버스 배치, HUD/채팅 힌트 위치, 데스크톱 `보내기` 숨김, 패널 페이드 200ms) |
| `src/client/constants.js` | 아바타 계약값(48x64, 기준점 24,60, 7프레임, idle [1] 500ms / walk [2..5] 150ms), `PART_KEYS` 7개, `DEFAULT_LAYER_ORDER` 8레이어, `LAYER_PART`, `CATEGORY_ORDER`, `DEFAULT_AVATAR`, `LEGACY_ALIASES`(art 5장 매핑표), 라벨/말풍선 v3 값, `ART.headLine 52`, `MOBILE_CONTROLS_H 132`. 사이클 2 파츠 목록/eyes/UI_SCALE 삭제 |
| `src/client/avatar-data.js` (신규) | `normalizeAvatar`, `isValidAvatarShape`(정확히 7키), `pickAvatar` — DOM 없는 순수 함수 |
| `src/client/assets.js` | manifest + outline.json + 레이어 PNG 43장 로더(hair → hair_back/hair_front, hat none 파일 없음), presets 정규화, `sanitizeAvatar`. 맵 로더 groundY 확인. `loadUiAssets` 삭제 |
| `src/client/avatar.js` | 새 렌더러 (2장) |
| `src/client/game/overlay.js` | 라벨/말풍선을 style-guide 7·8장 Canvas 레시피(fillRect + fillText)로 재작성. 9-slice 삭제 |
| `src/client/game/world.js` | 발 그림자 = 지면선 한 줄 x ax-7..ax+6 `g3` |
| `src/client/bgmap.js` | **삭제** (로그인/생성 배경은 CSS `.bk-world`, main.js에서 생성) |
| `src/client/main.js` | `.bk-world`(구름 3개 x 2벌, 언덕, 잔디/흙 띠) 생성·제거(boot/login/create 유지, game 제거), 모드 칩 `.bk-chip--mode`, getState에 `create` 추가 |
| `src/client/screens/login.js` | ui-kit 마크업 (`.scr-auth`, `.bk-logo`, `.bk-panel.card-login`, `.bk-tabs`, `.bk-field`, `.bk-link`, `.bk-btn--primary`). 로직 그대로 |
| `src/client/screens/create.js` | 전면 재작성 (탭 7 + 슬롯 + 프리셋 6 + 회전 미리보기 + 닉네임). 3장 |
| `src/client/screens/game.js` | HUD/배너/터치/채팅 ui-kit 마크업, 모바일 132px(최소 캔버스 160), 새 라벨/말풍선/그림자, 원격 walk 유지 200ms, getState players에 avatar/dir/frame |
| `src/client/backend/{common,local,supabase}.js` | 7키 검증/저장, 읽을 때 `readAvatar`(=normalize) — 옛 localStorage·DB 행도 7키로 |

## 2. 렌더 파이프라인

아바타 (`avatar.js`, 외형 조합당 1회, LRU 64):
1. 합성: `layerOrder`(hair_back → skin → face → bottom → shoes → top → hair_front → hat)대로 336x64 오프스크린에 겹침. hat `none`·로드 실패 레이어는 뺀다.
2. 외곽선: 원본 합성의 투명 픽셀마다 이웃을 아래/왼/오/위 순서로 보고, 처음 만난 불투명 이웃 색을 outline.json으로 매핑(없으면 RGB x0.45 내림). 같은 프레임(48px) 안에서만.
3. 반전: 외곽선 끝난 시트를 프레임마다 좌우 반전(열 c → 47-c)해 한 장 더 캐시.
4. 그리기: 기준점 아트 좌표 (x, 220)에 `drawImage`, 왼쪽 위 = (x-24, y-60). 인게임 = side_idle(1) / side_walk(2..5, 150ms), 왼쪽 보기 = 반전 시트.
- 썸네일: 같은 1~2단계를 front 프레임 하나에, style-guide 5.12 표의 파츠만 합성(LRU 256) → 40x40 자르기 → 슬롯 2배 / 프리셋 1배 (backing x dpr).
- 아트 기준 구현(assets/_src/block/avatar.py `compose`+`silhouette`과 같은 알고리즘)과 비교: 프리셋 6종 x 7프레임 + 반전 **픽셀 차이 0**.

게임 프레임: k1 채움 → 맵 레이어(manifest 순서, `ox=-floor(camX*parallax)`, repeatX 타일) → 발 그림자 → 아바타(원격 x 오름차순, 나 마지막) [아트 해상도 오프스크린] → 메인 캔버스로 정수 배율 확대(스무딩 끔) → 라벨 → 말풍선(먼저 받은 것부터) [CSS px x dpr]. 카메라 camY = 250 - viewH. P = 2(1600x900 이상 3), 데스크톱 캔버스 min(W,1280) x min(540, H-72), 모바일 W x (H-132).
미리보기: 아트 56x72 무대(하늘 k3/k4/k5 + ground.png 잔디 윗면 행 10줄 + 발 그림자 y64 x21–34), 프레임 왼쪽 위 (4,4), `--pv`(4/3) x dpr로 확대. 걷기 켤 때만 rAF.

## 3. normalize 규칙 (`avatar-data.js normalizeAvatar`)

1. 입력이 일반 객체가 아니면 `{}`.
2. `face`가 없으면 옛 `eyes` 값을 face로.
3. 문자열 + `^[a-z0-9-]{1,32}$` 아니면 버림.
4. manifest에 없는 id면 별칭 적용: `LEGACY_ALIASES`(art handoff 5장 표: `skin-light→light`, `hair-round-black→black-short`, `eyes-dot/round/sparkle→basic`, `eyes-happy→smile`, `top-tee-red→tee-stripe-red`, `bottom-pumpkin-green→shorts-brown` 등) → manifest `aliases`(있으면).
5. manifest id 집합이 있으면(`assets.sanitizeAvatar`) 거기 없는 id는 그 파츠 첫 항목.
6. 누락 키 = 기본값. 결과는 항상 정확히 7키(추가 키 버림).
- 적용 지점: 백엔드 `getMyCharacter`(형식 단계), 게임 시작/Presence 수신/프리셋(manifest 단계). 저장(`createCharacter`)은 `isValidAvatarShape` 통과한 `pickAvatar` 7키만. 저장된 옛 값은 덮어쓰지 않는다.

## 4. data-testid / 테스트 훅

- 유지: `mode-badge, error-message, global-error, login-id, login-pw, login-pw-confirm, login-submit, toggle-login, toggle-signup, pw-toggle, error-id, error-pw, error-pw-confirm, nickname-input, nickname-status(data-state), create-submit, logout, avatar-preview, game-canvas, player-count, chat-input, chat-send, chat-counter, chat-hint, chat-error, move-left, move-right, game-banner, reconnect-button`
- 추가: `tab-<part>`(skin/face/hair/hat/top/bottom/shoes), `slot-<part>-<id>`(현재 탭 것만 DOM에 있음, `aria-checked`), `slot-grid`, `preset-<0..5>`, `view-front|view-side|view-back`(`aria-checked`), `preview-walk`(`aria-pressed`), `current-part`(현재 값 줄), `manifest-error`, `world-bg`
- 삭제: `part-row-*`, `part-prev-*`, `part-next-*`, `part-value-*` (좌/우 행 UI 폐기)
- `getState()`: `players[]`/`me` = `{ user_id, nickname, avatar(7키), x, y, dir, lastChat, anim, frame }`. `assets` = `{ source, images, imageTotal, background, mapLayers, sheets, layout{P,cssW,cssH,viewW,viewH} }` (`ui` 필드 삭제). 신규 `create` = `{ ready, avatar, tab, view, walking, frame, slots, presets }` (생성 화면일 때만, 아니면 null).

## 5. 자체 검증 결과 (Chromium headless, local 모드, 스크립트 `scratchpad/c3fe/verify.py`) — 51/51 PASS

- 가입 → 생성: 초기값 = manifest 첫 항목 7키, 첫 탭 머리(슬롯 8), 탭 7개, 프리셋 6개. 모자 탭 슬롯 6(없음 선택) → 버섯 모자 선택, 현재 값 줄 문구, 슬롯 방향키 이동+선택, 탭 방향키 순환, 프리셋 7키 덮어쓰기 + 슬롯 표시 따라감, 앞/옆/뒤 = 프레임 0/1/6, 걷기 = 옆 + 2..5 순환, 걷기 중 앞 → 걷기 꺼짐.
- 저장 avatar(localStorage) 정확히 7키 = 선택 값.
- 두 페이지: 서로 보임, players에 avatar 7키, 접속 중 2명, 이동 시 상대 화면 walk(2..5) → 정지 후 idle(1), 왼쪽 dir, 채팅 양방향, XSS 미실행.
- 호환: 옛 5키 Presence(eyes, 옛 id) → `{medium, pink-long, smile, tee-stripe-red, skirt-pink, sneakers-white, none}`, 깨진 값 → 기본값. localStorage에 사이클 1/2 캐릭터(eyes, 옛 id / 없는 id·누락 키) 넣고 새로고침 → 에러 없이 게임, 정규화 값으로 그림.
- 에셋 43/43 + 맵 5레이어, 콘솔 에러 0, HTTP 4xx/요청 실패 0.
- 레이아웃: 1280x800 캔버스 1280x540 P2, 1920x1080 1920x810 P3, 360x640 캔버스 360x508 + 터치 56px + 채팅/보내기 한 줄, 가로 스크롤 0(로그인/생성/게임), 모바일 미리보기 176x224, 탭 7칸 한 줄, 슬롯 3열 88px.
- 선명도: 게임 캔버스 2x2 블록 균일. HUD 숨기고 QA `pixel_check`로 재면 1280/360에서 비정렬 0·불균일 0, 하늘 밴드 색 5~9개.
- 스크린샷 비교 2회 (시안 docs/design/ref/c3/): 1회차에서 `<p class="bk-help">` 기본 여백으로 로그인 도움말 아래가 벌어진 것, 모바일 채팅 입력 2px 어긋남 발견 → 수정. 2회차 로그인은 시안과 같은 배치. 외곽선 6배 확대(`sheet-preset3-6x.png`)·미리보기 확대로 확인.
- 스크린샷: `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c3fe/run2/` — `d-1-login, d-1b-login-error, d-2-create, d-2b-create-preset, d-2-preview-{front,side,back}, d-3-game-{a,b}, d-4-legacy, m-1-login, m-2-create(-full), m-3-game, w-3-game(1920), sheet-preset3-6x`.

## 6. 기존 QA 테스트 `tests/e2e_local.py` 결과: 9 PASS / 8 FAIL (새 UI·계약 때문, 테스트 갱신 필요)

| 항목 | 원인 | QA가 바꿀 것 |
|---|---|---|
| 1 | `part-next-hair` 없음 (좌/우 행 UI 폐기) | `tab-hair` → `slot-hair-<id>` 클릭으로 교체, 저장 값 7키 확인 |
| 3, 4 | 테스트 `AVATAR` 상수가 5키+`eyes`라 어댑터가 `AVATAR_FORMAT` 반환(계약대로, DB도 23514). 기대한 `NICK_TAKEN`/`CHAR_EXISTS`/`NICK_FORMAT` 전에 형식에서 거부됨 | `AVATAR`를 7키(`light, black-short, basic, hoodie-black, pants-navy, sneakers-white, none`)로 |
| 11 | 기대 캔버스 360x516 (조작 영역 124) | 132px → 360x508 |
| 13 | DOM HUD 칩 글자(안티에일리어싱)가 캔버스 스크린샷에 겹쳐 잡힘. HUD 숨기면 비정렬 0 | 검사 전 `.hud`를 숨기거나 HUD 사각형을 마스크. P=3에서 라벨(U=2 고정, 박스 아래 끝 = 글자 y+18)이 마스크(±12) 밖으로 6px 나와 50블록 불균일 — 디자인상 라벨은 P와 무관한 2px 격자이므로 마스크를 라벨 박스(글자 y-8 ~ +18)로 |
| 15 | `ui/manifest.json`, 아바타 22, 맵 7, UI 스킨 기대 | ui 검사 삭제, 아바타 레이어 43(`imageTotal`과 같음), 맵 5, PNG 48 |
| 16 | LOCAL MODE 칩 "겹침": 게임은 HUD가 캔버스 위에 겹치는 설계(game.md 1장) → `game-canvas` 제외 필요. 1280x800 생성은 장식 배경 `.bk-world`의 언덕 div(aria-hidden, 패널 뒤) | 배지 겹침 검사에서 `game-canvas`와 `[data-testid=world-bg]` 하위 제외 |
| 17 | 아트 빌드 재현성 테스트 (`assets/avatar/bottom/jeans-blue.png` 없음 — 테스트가 복사본에서 파일을 찾는 시점 문제로 보임). 프런트 무관 | QA/아트 확인 |

## 7. 요청

- 아트: handoff에 "아바타 PNG 47장"이라 적혀 있으나 실제 파일·manifest 기준 43장(3+4+8+8+6+5+4+5). 문서만 정정 요청.
- 디자인: (1) style-guide 6.1은 1280 폭에서 캔버스 1280px인데 시안 game-desktop.png는 960px(시야 480). 정본(6.1)을 따랐다 — 시안 갱신 또는 6.1 수정 중 결정 필요. (2) 사이클 2 메인 리뷰로 넣었던 데스크톱 캔버스 바깥 하늘/흙 연장 배경은 v3("게임 바탕 = letterbox")에 따라 없앴다. (3) 라벨/말풍선 글자 세로 위치는 DOM 판(.bk-name line-height 20, .bk-bubble 18)과 맞도록 Canvas `top` 기준에서 (줄높이-글자)/2 = 2px 내렸다(라벨 글자 위 by+4, 말풍선 by+8). 레시피 문구(by+2 / by+6)와 2px 차이 — 의도 확인 요청.
- 메인: ARCHITECTURE 테스트 훅 항목에 getState `create`, players `avatar/dir/frame` 추가 기록 요청. 백엔드 요청 없음(7키 형식 그대로 보냄).

## 8. QA 확인 항목

1. 6장 표대로 e2e 갱신 후 전부 PASS.
2. character-create.md 10장, game.md 10장, login.md 9장 360px 체크리스트 (특히 sticky 만들기 버튼 뒤 c1 띠, 슬롯 선택 테두리 잘림 없음).
3. 생성: 탭 방향키/Home/End, 슬롯 방향키(그리드 열 수 기준 위/아래), 프리셋 → 7파츠 한 번에, 걷기 토글/앞·뒤 시 걷기 꺼짐, 썸네일이 피부/얼굴/머리 변경에 따라 다시 그려짐.
4. 옛 데이터: 실제 Supabase에서 마이그레이션된 행(face=`eyes-dot` 등 옛 id)으로 로그인 → 정상 외형.
5. Presence 위조(옛 5키/깨진 avatar track) 시 다른 클라이언트가 깨지지 않음.
6. Safari/Firefox: ui-kit box-shadow 계단 테두리, `image-rendering: pixelated`, OffscreenCanvas `getImageData`(외곽선) 동작.
7. dpr 2/3에서 아바타 외곽선·맵 픽셀 정사각, 라벨/말풍선 글자 선명.

## 9. 알려진 한계

- 외곽선 계산은 조합당 1회 336x64 `getImageData` 순회(수 ms). 접속자가 많고 외형이 모두 다르면 입장 직후 몇 프레임 끊길 수 있다(캐시 64조합 초과 시 재계산).
- 매니페스트가 아예 없으면 생성 화면은 `MANIFEST` 배너 + 생성 불가, 게임은 단색 블록 인형으로 그린다(외형 구분 없음).
- 생성 화면 Tab 순서는 DOM 순서(미리보기 → 프리셋 → 탭 → 슬롯 → 닉네임 → 만들기)이고 로그아웃이 맨 앞. 디자인 9장 순서와 같다.
- 데스크톱 1280 폭에서 조작 힌트 칩과 로그아웃이 캔버스 오른쪽 위에 붙는다(시안보다 캔버스가 넓음, 7장 디자인 1번).
- 소프트 키보드(visualViewport)와 실제 Supabase 모드는 headless에서 미검증. Safari/Firefox 미검증.
- 텍스트는 시스템 폰트라 플랫폼마다 말풍선 줄바꿈 위치가 다르다.

## 8. 사이클 3 수정: 모바일 생성 화면 겹침

- 원인: 모바일(≤719px)의 `.create-cta`는 `position: sticky; bottom: 0`(ui-kit 13.1)이라 스크롤 중에는 뷰포트 아래 62px를 덮는다. 문서 순서(닉네임 → 만들기 → LOCAL MODE)는 맞고 스크롤 끝에서는 겹침이 없다. 하지만 닉네임 입력에 focus/`scrollIntoView`/Tab 이동하면 브라우저가 입력을 뷰포트 맨 아래에 맞춰 바 뒤로 완전히 가려졌다 (360x640 재현: 입력 596~640, 바 578~640).
  QA의 전체 페이지 캡처(`qa3/create-mobile-full.png`)에서 버튼이 닉네임 라벨 위에 찍힌 것은 Playwright `full_page`가 sticky 요소를 캡처 직전 스크롤 위치의 고정 좌표로 그리는 캡처 현상이다(수정 후에도 full_page에서는 같은 모양). 실제 뷰포트 확인은 뷰포트 캡처로 해야 한다.
- 수정 (`src/client/style.css` 모바일 미디어 쿼리만, ui-kit 복사본 그대로):
  - `--create-bar-h: calc(62px + env(safe-area-inset-bottom))`, 바 `padding-bottom: calc(10px + safe-area)` (홈 인디케이터 기기).
  - `html:has(body[data-screen="create"]) { scroll-padding-bottom: bar + 8px }` → focus·scrollIntoView·Tab 시 모든 요소가 바 위에서 멈춤.
  - `.create-nick .bk-input { scroll-margin-bottom: 32px }` → 입력 아래 상태 문구까지 바 위에 보임.
- 결과 (뷰포트 캡처, `scratchpad/fe-fix/after/`): focus 시 360x640 입력 494~538 / 상태 544~564 / 바 578 (14px 여유), 375x667·390x844 동일 여백, Tab 이동(마지막 슬롯 → 닉네임)도 바 위. 스크롤 끝은 기존과 같음(라벨 → 입력 → 상태 → 만들기 → LOCAL MODE, 겹침 없음). 1280x800 생성·로그인·게임 좌표 변화 없음, 가로 스크롤 0, 콘솔 에러 0.
- `tests/e2e_local.py` 21/21 PASS.
- QA 확인: 실기기(iOS Safari 홈 인디케이터, 소프트 키보드 열림)에서 닉네임 입력이 바/키보드에 가리지 않는지. `:has()` 미지원 브라우저(Firefox <121)는 `@supports not selector(:has(a))` 대체 규칙으로 입력 scroll-margin-bottom = 바 높이 + 40px (슬롯 등 다른 요소는 대체 없음).
