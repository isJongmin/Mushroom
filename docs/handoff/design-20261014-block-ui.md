# design -> main: 사이클 3 블록 스타일 UI (스타일 가이드 v3, 화면 설계 3종, ui-kit.css)

날짜: 2026-10-14 / 담당: 디자인
상태: 완료. ARCHITECTURE "블록 아트 계약"과 아트 최종 납품(`art-20261014-block-final.md`, `assets/avatar`, `assets/map`) 기준.

## 1. 작성/개정 문서

| 파일 | 내용 |
|---|---|
| `docs/design/style-guide.md` | v3.0 전면 개정. 팔레트 42색(정본, palette.py와 일치 검사함), 블록 아트 요약(수치는 ARCHITECTURE 참조만), UI 토큰, 블록 UI 원칙, 컴포넌트 14종, 게임 배율/카메라, 라벨/말풍선 Canvas 레시피, 모바일. 사이클 2 픽셀 규격(32x48, 해부도, 맵 7레이어, UI 스킨 PNG) 삭제 |
| `docs/design/ui-kit.css` | 신규. 토큰 + 컴포넌트 + 화면 배치 CSS (순수 CSS, 이미지 요청 없음, 약 35KB) |
| `docs/design/screens/login.md` | v3.0. CSS 블록 배경, 블록 로고, 패널/필드/버튼. 문구·검증·동작 유지 |
| `docs/design/screens/character-create.md` | v3.0. 카테고리 탭 7개 + 슬롯 그리드 + 프리셋 + 회전 미리보기(앞/옆/뒤 + 걷기). 좌/우 파츠 행 폐기. 저장 값 7개 키. 닉네임 규칙·문구 유지, `MANIFEST` 오류 1개 추가 |
| `docs/design/screens/game.md` | v3.0. 블록 HUD, 모바일 조작 영역 124 -> 132px, 아바타 표시는 ARCHITECTURE 참조, 말풍선 기준선 |
| `docs/design/tools/tile_svg.py` | `assets/map/ground.png`에서 16x16 잔디/흙 타일을 잘라 `--tile-*` SVG URI 생성 |
| `docs/design/ref/c3/*.png` | 시안 스크린샷 8장 (아래 5장) |

`docs/design/ref/` 바로 아래 사이클 2 시안 11장은 폐기 자료다(삭제는 하지 않음).

## 2. 핵심 결정

1. **버튼 테마: primary = 잔디 블록(초록), secondary = 돌 블록(회색).** 빨강은 오류(`r3` 글자/테두리, `r1` 링)와 겹쳐 "제출=오류"로 읽히고, 빨강 바탕은 글자 대비가 AA 경계(ink 4.3:1). 잔디는 화면 아래 잔디 띠/맵 지면과 이어지고 `ink` on `g2` 8.1:1. 버튼 아래 두께를 흙색(`w3`)으로 칠해 "윗면 잔디 + 옆면 흙" 블록으로 읽힌다. 버섯 빨강은 로고와 아이콘에만.
2. **패널 = 크림 인벤토리 창**: `c1` 바탕, 위/왼 white 베벨, 아래/오른 c2 베벨, `w4` 계단 테두리, 아래 블록 두께 4px `c3`.
3. **눌림 = 2px 아래로 + 베벨 반전 + 두께 제거** → 아래 끝 위치는 그대로(바닥에 눌린 블록).
4. **로그인 배경 = CSS만**: 하늘 5단 하드 스톱 띠 + 블록 구름(240초 흐름) + 민트 블록 언덕 + 잔디/흙 타일 띠 96px. 장면 이미지를 흐리게 깔지 않는다.
5. **슬롯 88px, 썸네일 = 아트 40x40 영역 2배**: 최종 에셋의 가장 넓은 모자(탐험가 x 5–43)까지 잘리지 않게 정함. 모바일 3열, 데스크톱 5열.
6. **말풍선 기준선 고정**: 꼬리 끝 = 발 위 `52*P + 4` CSS px(프레임 y 8 = 가장 높은 버섯 모자 위). 모자/머리와 무관하게 높이가 맞는다.
7. **미리보기**: 아트 56x72 무대, 데스크톱 4배(224x288), 모바일 3배(168x216, 방향 버튼을 오른쪽 세로 배치). 기본 = 앞, 걷기 꺼짐. 걷기 켜면 옆모습으로 전환.

## 3. CSS 토큰 (프런트/아트가 그대로 쓰는 값)

- 팔레트: `--pal-<토큰>` 42개 (style-guide 1장 표 = `assets/_src/block/palette.py` PAL과 동일).
- 의미 색: `--text #1A1626`, `--text-strong #5E3620`, `--text-muted #8A5232`, `--text-on-dark #FFFFFF`, `--error #9E2838`, `--error-bg #FFC8DC`, `--success #23562A`, `--focus #2E3E9E`, `--panel #FFF6E4`, `--letterbox #1A1626`, `--sky #6EC6F5`.
- 간격(4px 단위): `--u 2px`(UI 픽셀), `--sp-1 4`, `--sp-2 8`, `--sp-3 12`, `--sp-4 16`, `--sp-5 20`, `--sp-6 24`, `--sp-8 32`, `--sp-10 40`.
- 글자: `--font-ui: system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif;` 크기/줄 `--fs-xs 12/16`, `--fs-sm 14/18`, `--fs-md 16/22`, `--fs-lg 20/26`, `--fs-xl 40/48`(모바일 32/40). 기본 굵기 700, 입력 400, 로고 900.
- 크기: `--h-ctl 44`, `--h-touch 56`, `--h-sm 32`, `--h-chip 28`, `--slot 88`.
- 아바타/맵 규격: ARCHITECTURE 블록 아트 계약(프레임 48x64, 기준점 (24,60), 지면 아트 y 220) — 스타일 가이드는 재정의하지 않음.

## 4. 컴포넌트 목록 (`ui-kit.css` 클래스)

| 컴포넌트 | 클래스 | 상태 |
|---|---|---|
| 패널 / 오목 칸 / 구분선 | `.bk-panel`, `.bk-well`, `.bk-divider` | - |
| 버튼 | `.bk-btn` (secondary 돌), `.bk-btn--primary` (잔디), `--block`, `--sm`, `--touch`, `--icon` | 기본 / `:hover`·`.is-hover` / `:active`·`.is-pressed` / `:disabled` / `:focus-visible` |
| 탭 | `.bk-tabs > .bk-btn[aria-selected]`, `.bk-tabs--cat` | 활성 = 잔디 눌림 |
| 입력 | `.bk-field`, `.bk-label-text`, `.bk-input-wrap`, `.bk-input`, `.bk-input--with-end`, `.bk-input-end`, `.bk-help(--error/--ok)`, `.bk-counter` | 기본 / `:focus` / `[aria-invalid=true]` / `:disabled` |
| 토글 링크 | `.bk-link[aria-pressed]` | 보기/숨기기 |
| 칩/배지 | `.bk-chip`, `.bk-chip--hint`, `.bk-chip--mode`, `.bk-dot-off` | - |
| 배너 | `.bk-banner`, `.bk-banner--error` | - |
| 도트 아이콘 | `.bk-ico--mush`, `.bk-ico--arrow`(+`--left`), `.bk-ico--check` | - |
| 로딩 점 | `.bk-dots > i*3` | 동작 줄이기 시 정지 |
| 로고 | `.bk-logo`, `.bk-logo-sub` | - |
| 배경 | `.bk-world`, `.bk-clouds > .bk-cloud(--b)`, `.bk-world__hills`, `.bk-world__ground` | 동작 줄이기 시 구름 정지 |
| 슬롯/프리셋/미리보기 | `.bk-slots > .bk-slot[aria-checked]`, `.bk-slot__none`, `.bk-presets`, `.bk-preview(--pv)`, `.bk-preview__stage`, `.bk-preview__ctrl` | 선택 / hover |
| 말풍선/라벨 (DOM 판) | `.bk-bubble`, `.bk-name`, `.bk-name--self` | Canvas 레시피는 style-guide 7·8장 |
| 화면 배치 | `.scr-auth`, `.card-login`, `.card-create`, `.card-head`, `.card-foot`, `.create-grid`(`.create-prev/parts/nick/cta`), `.scr-game`, `.game-stage`, `.hud`, `.hud-l/-r`, `.hud-banner`, `.chat-row`, `.touch-row`, `.hint-desktop` | 720px 미만 모바일 |

## 5. ui-kit.css 사용법

1. `docs/design/ui-kit.css`를 `src/client/`(예: `src/client/ui-kit.css`)로 복사하거나 index.html에서 직접 링크한다. 기존 style.css의 픽셀 스킨(`border-image`, `assets/ui/*`) 규칙은 지운다(아트가 `assets/ui/` 삭제함).
2. 마크업은 시안 HTML과 각 screens 문서의 DOM 골격을 따른다. 상태는 클래스가 아니라 속성으로 바꾼다: `disabled`, `aria-selected`, `aria-checked`, `aria-pressed`, `aria-invalid`. 터치 버튼만 `.is-pressed`를 JS로 붙인다.
3. 디자인이 값을 바꾸면 이 파일을 다시 복사한다. 프런트 전용 규칙은 별도 파일에 두고 ui-kit.css를 직접 고치지 않는다(덮어쓰기 충돌 방지).
4. 시안 HTML(참고용, 저장소 밖): `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c3design/{login,create,game,kit}.html` (같은 폴더 `img/`에 에셋 합성 이미지). 스크래치라 사라질 수 있으니 구조는 screens 문서를 정본으로 본다.

## 6. 시안 스크린샷

저장소: `docs/design/ref/c3/`
- `login-desktop.png` (1280x800), `login-mobile.png` (360x640)
- `create-desktop.png`, `create-mobile.png`, `create-mobile-full.png`
- `game-desktop.png`, `game-mobile.png`
- `kit-desktop.png` (컴포넌트 상태 시트)

다듬은 회차 (매회 playwright 1280x800 / 360x640 캡처를 Read로 확인):
1. 첫 렌더: 비활성 탭 글자(`w3` on `st1` 3.7:1) 대비 부족, 구름이 화면 밖으로 나가 안 보임, 버튼 베벨이 1x에서 약함.
2. 버튼을 3면 톤(위 4/왼 2 밝게, 오른 4/아래 2 어둡게)으로, 탭 글자 `hb1`(5.3:1), 구름을 200% 묶음 흐름으로 교체.
3. 픽셀 확대 검사에서 버튼 흙색 두께가 안 보이는 문제 발견: 대각 오프셋 그림자(-2px 2px)가 아래 띠까지 덮음 → 두께 띠를 먼저 적도록 순서 수정(패널, 오류 배너 동일). 말풍선 꼬리를 3단 계단으로 키움, 모바일 미리보기 3배 + 방향 버튼 세로 배치로 첫 화면에 탭까지 보이게, 모바일 HUD/조작 영역 실측(가로 스크롤 0, 캔버스 360x508).
4. 아트 최종 납품 반영: 썸네일/프리셋/게임 장면을 최종 에셋으로 다시 합성, 슬롯 72 -> 88(모자 범위), 프리셋 6종 3열, 타일 SVG를 `ground.png`에서 재생성, 슬롯 오목 베벨 `c3` -> `w2`(경계 대비 3:1 이상).

## 7. 프런트 구현 시 주의점

- **box-shadow 순서를 바꾸지 말 것.** 바깥 그림자는 옮긴 상자 전체라, 대각 그림자가 두께 띠를 덮는다. 두께 띠(`0 2px`/`0 4px`)가 대각 그림자보다 앞에 있어야 한다.
- **계단 테두리와 두께는 레이아웃 밖에 그려진다.** 버튼 아래 4px, 패널 아래 6px, 위/좌/우 2px 여유를 두고, 조상에 `overflow: hidden`을 쓰지 말 것(게임 캔버스 래퍼 포함 — HUD는 캔버스 가장자리에서 8px 이상).
- **포커스 링은 `outline-offset: 4px`**(테두리 바깥). 입력은 outline 대신 테두리 색이 바뀐다. 캔버스와 토글 링크는 안쪽(-4px).
- **글리프 화살표/체크(◀ ▶ ✓) 금지** — iOS에서 이모지로 바뀐다. 도트 아이콘 클래스 사용.
- **라벨/말풍선은 Canvas 레시피(style-guide 7·8장)를 정수 CSS px x dpr로.** 위치 기준은 기준점(`round(worldX/2)` 아트 x, 지면 220)과 머리 위 기준선(52 아트 px)뿐. DOM 판(`.bk-bubble`, `.bk-name`)은 시안용이며 Canvas로 옮길 때 색/두께가 같아야 한다. 텍스트는 `fillText`/`textContent`만.
- **모바일 게임 조작 영역 132px**(이동 버튼 행 64 + 채팅 행 68). 캔버스 세로 = `floor((innerHeight - 132)/2)*2`, 키보드 시 `visualViewport.height - 132`.
- **슬롯 썸네일**: 게임과 같은 합성 + 실루엣 외곽선 파이프라인으로 front 프레임을 만들고 style-guide 5.12 표의 40x40 영역을 2배로. 피부/머리가 바뀌면 다시 만든다(캐시 권장). 프리셋 버튼은 (4,6)~(44,46) 1배.
- **캐릭터 생성 저장 값은 7개 키**(skin, face, hair, hat, top, bottom, shoes). 초기값 = manifest 각 파츠 첫 항목(hat = `none`). 탭/슬롯 목록은 manifest만 보고 만든다(하드코딩 금지, 사이클 2 `constants.js` 파츠 목록 제거).
- **미리보기 회전**: 앞=frame 0, 옆=1(걷기 2–5), 뒤=6. 걷기 켜면 옆으로 전환, 앞/뒤 누르면 걷기 끔. 게임 안에서는 front/back을 쓰지 않는다.
- **동작 줄이기**: 로그인 구름과 로딩 점만 정지. 게임 안 걷기는 유지. 미리보기 걷기는 기본 꺼짐(사용자가 켜면 재생).
- **배경 `.bk-world`는 로그인 → 생성 전환 때 유지, 게임 진입 때 제거.** 게임 화면 바탕은 `--letterbox`.
- 오류 문구, 검증 정규식, 쿨다운, 재연결 규칙은 바뀌지 않았다. 신규 문구는 캐릭터 생성 `MANIFEST` 하나.

## 8. 메인에게 (결정/확인 필요)

- ARCHITECTURE "UI: ... 정본은 docs/design/style-guide.md" 항목과 일치. ARCHITECTURE 변경 요청 없음.
- 모바일 게임 조작 영역을 124 -> 132px로 늘렸다(블록 테두리/두께 공간). 프런트와 QA 체크 항목(360x508 캔버스)에 반영 필요.
- QA 요청: 블록 테두리 모서리(2x2 빈칸)와 버튼 두께가 Safari/Firefox에서도 같은지(box-shadow 다중 레이어, `image-rendering: pixelated` 타일 SVG) 확인.
