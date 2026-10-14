# 핸드오프: 픽셀아트 비주얼 전면 개정 (사이클 2, 2026-10-14)

작성: 디자인 팀. 대상: 아트(assets/), 프런트(index.html, src/client/), QA, 메인.
정본: `docs/design/style-guide.md` v2.0. 상위 계약: `docs/ARCHITECTURE.md` "픽셀아트 계약" (변경하지 않음).

## 1. 작성/수정한 문서

| 파일 | 내용 |
|---|---|
| `docs/design/style-guide.md` | 전면 개정 v2.0: 42색 팔레트, 글자 규칙, P 배율과 카메라, 아바타 해부도와 프레임 영역 지도, 파츠 22종, 맵 레이어 7개와 버섯 집 설계, UI 스킨 9-slice, 라벨/말풍선 |
| `docs/design/screens/login.md` | v2.0: 마을 배경 + 픽셀 패널, 스킨 적용, 로딩 점. 흐름과 문구는 v1 그대로 |
| `docs/design/screens/character-create.md` | v2.0: 4배 걷기 미리보기, 파츠 목록 확장, 행 스킨. 흐름과 문구는 v1 그대로 |
| `docs/design/screens/game.md` | v2.0: 정수 배율 캔버스, HUD 겹침 배치, 모바일 하단 빈 공간 제거, 배너 스킨 |
| `docs/design/ref/*.png` | 디자인 검증 시안 (아바타 5조합 x 6프레임, 해부도, 게임 화면, 맵 전체, 로그인 2종, 패널/버튼 확대) |
| `docs/design/ref/draft-src/*.py` | 시안 생성 Pillow 스크립트 (디자인 검증용. 아트 정본은 `assets/_src/`) |

## 2. 바뀐 점 (사이클 1 대비)

- SVG 64x96 정면 아바타 → PNG 32x48 오른쪽 3/4뷰, 6프레임 시트. 사인 흔들림 폐기, idle/walk 프레임 애니메이션.
- 팔레트 28색 단색 → 42색 재료별 램프. 외곽선은 재료의 가장 어두운 톤 (순검정 없음).
- 파츠 16종 → 22종: skin 3, eyes 4, hair 7, top 4, bottom 4. 기본 조합은 그대로.
- 맵: SVG 1장 → 패럴랙스 레이어 7장 (하늘 밴드, 구름, 먼 산, 언덕, 중경 나무, 버섯 집 4채 마을, 16px 지면 타일).
- UI: CSS 둥근 모서리 → 나무/크림 픽셀 9-slice 스킨 (패널, 버튼 4상태, 입력 4상태, 칩, 말풍선, 라벨).
- 로그인/생성 화면 배경 = 게임 맵 레이어 재사용 (자동 좌우 이동).
- 카메라: 화면 아래 끝 = 아트 y 250 고정, 캔버스는 정수 배율 P(2, 큰 화면 3)로 가용 영역을 채운다.
- 사이클 1 QA 낮음 3건 해결 설계: 모바일 라벨 잘림 (4.3 카메라), 모바일 하단 빈 공간 (game 3장), LOCAL MODE 배지 겹침 (7.9, fixed 금지).

## 3. 아트팀 체크리스트

핵심 값
- 프레임 32x48, 기준점 (16,46), 발바닥 마지막 줄 y 45, 행 46–47 투명. 시트 192x48 `idle0 idle1 walk0 walk1 walk2 walk3`.
- 팔레트는 style-guide 1.1의 42색만. 램프는 1.2.
- 파츠 영역은 style-guide 5.3.1 영역 지도(프레임 6개)가 정본. 외곽선/음영 자동 규칙 5.4.1.
- 맵 파일/크기/y/parallax는 style-guide 6.1 표. 지면 잔디 윗면 = 아트 y 220.

할 일
- [ ] `assets/_src/`에 팔레트 상수 42색과 5.3.1 영역 지도, 5.5.1 skin 격자, 5.6.1 눈 격자, 5.7.1 머리 격자 3종, 7장 UI 격자를 데이터로 옮긴다.
- [ ] 아바타 파츠 22개 시트 (`assets/avatar/<part>/<id>.png`, 각 192x48) + `manifest.json` (계약 형식, `parts` 순서는 style-guide 5.10).
- [ ] 레이어 금지 픽셀 지키기: top/bottom은 손(`H h`)을 칠하지 않음, top은 머리 영역(y ≤ 24+dy) 금지, hair는 눈 상자 금지와 y ≥ 25+dy에서 앞팔 영역 삭제 (style-guide 5.4).
- [ ] 5개 조합 이상 x 6프레임 합성 확대 PNG로 레이어가 맞는지 눈으로 확인 (특히 walk0/walk2 팔 교차, idle1 손과 허리, walk1/walk3 들린 발).
- [ ] 좌우 반전(열 c → 31-c) 합성 확인.
- [ ] 맵 7장 (`assets/map/*.png`) + `assets/map/manifest.json` (style-guide 6.1 예시 그대로). repeatX 레이어 이음매 확인 (이미지 두 장 이어 붙여 렌더).
- [ ] 버섯 집 4채 배치와 디자인 (style-guide 6.5 표: 갓 반타원, 점 6개, 아치 문, 둥근 창, 굴뚝은 갓 뒤).
- [ ] UI 스킨 19개 파일 (`assets/ui/`, style-guide 7.1 표) + `assets/ui/manifest.json`. 9-slice 가운데가 단색이라 늘려도 깨지지 않는지 확인.
- [ ] 모든 PNG: 반투명 픽셀 0개, 팔레트 밖 색 0개 검증 스크립트.
- [ ] 시안(`docs/design/ref/`)보다 품질을 올리는 것은 자유. 단 좌표, 크기, 색, 영역 규칙을 바꾸려면 디자인에 요청.
- [ ] 사이클 1 SVG(`assets/avatar/**/*.svg`, `assets/map/background.svg`) 삭제 여부는 메인 결정 (프런트 전환 후 삭제 권장).

## 4. 프런트팀 체크리스트

UI 스킨 적용
- [ ] `:root` CSS 변수: style-guide 1.3 (`--text #1A1626`, `--text-strong #5E3620`, `--text-muted #8A5232`, `--error #9E2838`, `--error-bg #FFC8DC`, `--success #23562A`, `--focus #2E3E9E`, `--panel #FFF6E4`, `--letterbox #1A1626`, `--sky #6EC6F5`).
- [ ] `border-image` 9-slice: 패널 `8 fill / 16px`, 버튼 `8 fill / 16px`, 입력 `4 fill / 8px`, 칩 `3 fill / 6px`. 모두 `image-rendering: pixelated`. 상태별 파일 교체 (style-guide 7.10 표). 눌림은 내용 4px 아래로 (`pressedShift` 2 x U).
- [ ] `border-radius`와 블러 그림자 제거. 포커스 `outline: 2px solid var(--focus); outline-offset: 2px`.
- [ ] 스킨 로딩 실패 시 대체 배경/테두리 (style-guide 7.10 끝).
- [ ] LOCAL MODE: `position: fixed` 제거. 로그인/생성은 패널 맨 아래 줄, 게임은 접속자 배지 오른쪽. supabase 모드에서는 숨김.
- [ ] 글자: 시스템 폰트 700 기본, 라벨/말풍선/버튼 1px 그림자 (style-guide 2.3). Canvas는 `shadowBlur` 대신 두 번 `fillText`.
- [ ] 로그인/생성 배경 맵 캔버스 (login 2.1): 초당 10 아트 px 왕복, reduced-motion이면 정지, 화면 전환 시 유지.

애니메이션 타이밍
- [ ] idle 프레임 [0,1] 500ms, walk [2,3,4,5] 120ms (매니페스트 값 사용). 상태가 바뀌면 첫 프레임부터.
- [ ] 다른 사용자: 마지막 move 후 200ms 안에 위치 변화가 있으면 walk. idle 시작에 user_id 기반 0–499ms 오프셋.
- [ ] 사인 흔들림(`bobAmp`, `bobPeriod`) 제거.
- [ ] 캐릭터 생성 미리보기: 아트 48x60 캔버스 4배 (192x240), walk 반복, 방향 버튼, reduced-motion이면 idle0 정지.

배율과 카메라
- [ ] P: 모바일 2, 데스크톱 2, `innerWidth >= 1600 && innerHeight >= 900`이면 3. 캔버스 CSS 크기 = style-guide 4.2 표 (모바일 세로 `innerHeight - 124`, 데스크톱 `min(540, innerHeight - 72)`), P의 배수로 내림, 최소 시야 세로 80 아트 px.
- [ ] 카메라: `camX = clamp(round(playerArtX - viewW/2), 0, max(0, 1200 - viewW))`, `camY = 250 - viewH` (음수면 위를 `k1`로 채움).
- [ ] 렌더 파이프라인: 아트 해상도 오프스크린 → 메인 캔버스로 확대 (스무딩 끔) → 라벨/말풍선/글자는 화면 해상도 (style-guide 4.4). 아바타 아트 x = `round(worldX/2)`, 라벨/말풍선도 같은 값 기준.
- [ ] 발 그림자 `g3` 2줄 (style-guide 4.5).
- [ ] 모바일 레이아웃: 캔버스 화면 폭 전체 + HUD 겹침, 아래 터치 버튼 행(8+56)과 채팅 행(8+44+8). `visualViewport.resize`로 다시 계산.
- [ ] 데스크톱: 캔버스 아래 12px에 채팅 입력. HUD는 캔버스 위 겹침, 조작 힌트는 캔버스 가로 900px 미만이면 숨김.
- [ ] 닉네임 라벨 높이 20, 위 = 발 + 4, 가로 2의 배수. 말풍선 꼬리 끝 = 머리 기준선(아트 y 176) - 4, 크기 2의 배수, 세로 화면 안 보정 추가 (style-guide 8, 9장).

데이터
- [ ] 파츠 목록은 매니페스트 우선. `src/client/constants.js`의 대체 목록(DEFAULT_PARTS, 라벨)을 style-guide 5.10 순서와 새 label로 교체.
- [ ] 예전 id 변환: `eyes-round → eyes-sparkle`, `top-vest-green → top-overalls-blue`, 목록에 없는 id → part 기본값. 저장 값은 고치지 않는다.
- [ ] `src/client/avatar.js`의 SVG/색 직접 그리기 코드 제거, PNG 시트 합성으로 교체.

## 5. QA 확인 항목 (추가)

- 360x640: 라벨 아래 끝 < 캔버스 아래 끝, 하단 빈 공간 없음, LOCAL MODE 칩 겹침 없음 (screens 각 문서 끝 체크 항목).
- dpr 1/2/3에서 아트 픽셀이 같은 크기 정사각형, 스킨 테두리 선명.
- 걷기/대기 타이밍, 좌우 반전 시 레이어 어긋남 없음.
- `border-image` + `image-rendering: pixelated`가 Safari, Firefox에서도 선명한지 (미확인 항목).

## 6. 계약 변경 요청 (메인 결정 필요)

ARCHITECTURE.md는 수정하지 않았다. 아래는 확인 또는 기록 요청이다.

1. UI 스킨 파일명: 계약 예시는 "button.png 상태별"이지만 CSS `border-image`는 시트 일부를 잘라 쓸 수 없어 상태마다 파일을 나눴다 (`button-primary-normal.png` 등, style-guide 7.1). 계약 문구를 "상태별 개별 파일"로 고쳐 주기 바람.
2. 배율: 계약은 "데스크톱 2배 표시"다. 디자인은 큰 화면(1600x900 이상)에서 정수 3배를 허용했다 (아트 1px = 월드 2단위는 그대로, 표시 배율만 다름). 계약에 "표시 배율 P는 정수 2 또는 3"으로 기록 요청. 원하지 않으면 3배 행을 지우면 된다 (다른 값 영향 없음).
3. 카메라/시야: 사이클 1의 고정 시야(데스크톱 960x540, 모바일 480x270 + camY 200)를 폐기하고 가변 시야 + 화면 아래 끝 고정(아트 y 250)으로 바꿨다. 시야 위쪽이 월드 밖(y<0)으로 나갈 수 있다 (`k1`로 채움). 월드 크기와 지면은 그대로.
4. `docs/PROJECT.md` 기술 스택 "아트: SVG 기본"을 "픽셀아트 PNG (Pillow 생성)"로 갱신 요청.
5. backend: `characters.avatar` 컬럼 주석이 `assets/avatar/<part>/<id>.svg`를 가리킨다. 새 id는 모두 기존 CHECK(`^[a-z0-9-]{1,32}$`)를 통과하므로 스키마 변경은 필요 없고, 주석만 `.png` 시트로 바꾸면 된다 (선택).
6. 파츠 id 추가/변경: 새 id 8개(`hair-spiky-mint`, `hair-long-pink`, `hair-long-blonde`, `eyes-sleepy`, `eyes-sparkle`, `top-overalls-blue`, `top-cape-mushroom`, `bottom-pumpkin-green`), 폐기 2개(`eyes-round`, `top-vest-green`, 프런트에서 변환). 라벨 변경: 머리 "둥근 단발 · 흑발" → "단발 · 흑발" 등 (모바일 폭), 눈 "점 눈" → "기본 눈".
