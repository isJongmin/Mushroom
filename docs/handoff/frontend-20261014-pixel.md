# frontend → main: 픽셀아트 렌더러와 UI 재스킨 (사이클 2, 2026-10-14)

정본: docs/ARCHITECTURE.md "픽셀아트 계약", docs/design/style-guide.md v2.0, docs/design/screens/*.md, docs/handoff/design-20261014-pixel.md (프런트 체크리스트), docs/handoff/art-20261014-pixel.md.
사이클 1의 게임 로직, 백엔드 어댑터, 테스트 훅(data-testid, `window.__mushroom.getState()`)은 그대로 두었다. 비주얼 계층만 바꿨다. SVG 경로 참조는 0건이다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `src/client/constants.js` | 팔레트(`PAL`), 월드/아트 좌표(`ART`), `pixelScale()`(P=2, 1600x900 이상 3), 아바타 계약 값(32x48, 기준점 16,46, idle/walk), 파츠 22종 대체 목록(5.10 순서와 label), 예전 id 별칭, 라벨/말풍선 규격. 사이클 1 값(COLORS, VIEW_*, bob) 삭제 |
| `src/client/assets.js` | 로더 3개. `loadAvatarAssets`(계약 형식 검증, 사이클 1 형식은 폴백, PNG 시트 22장, aliases 평면/파츠별 형식 모두 수용), `loadMapAssets`(레이어 7장, 실패한 레이어만 빠짐), `loadUiAssets`(9-slice와 스프라이트를 불러와 `:root` CSS 변수 `--ui-*`와 html 클래스 `skin-panel/skin-btn/skin-input/skin-chip/skin-icon-*` 설정). 매니페스트 src는 `assets/…png`만 허용 |
| `src/client/avatar.js` | layerOrder로 파츠 시트를 192x48 한 장으로 합성, 좌우 반전 시트(프레임마다 열 c→31-c)와 함께 조합별 LRU 64 캐시. `frameAt(anim, ms)`(매니페스트 frames/ms), `draw()`는 아트 해상도 컨텍스트에 정수 좌표로. PNG가 없는 파츠는 5.3 포즈표 기반 단색 픽셀 도형(6프레임) 폴백. `idleOffset(user_id)` 0~499ms |
| `src/client/game/world.js` | 맵 레이어 패럴랙스(`ox = -floor(camX*parallax)`, repeatX 타일링), k1 채움, 단색 폴백 맵, 발 그림자(g3 2줄), 카메라(4.3) |
| `src/client/game/overlay.js` | 라벨/말풍선을 화면 해상도로. UI 스킨 9-slice(U=2)를 Canvas로 직접 그림, 스킨이 없으면 같은 크기 픽셀 상자. 글자는 `fillText` 2회(1px 그림자, 블러 없음). 크기 2의 배수, 꼬리/세로 화면 안 보정(9장) |
| `src/client/bgmap.js` (신규) | 로그인/생성 배경. 레이어마다 아트 해상도 캔버스 + CSS P배(pixelated), 카메라 왕복 초당 10 아트 px를 Web Animations `steps()`로(정수 아트 px 단위, JS 프레임 루프 없음). reduced-motion이면 camX 300 고정. 로그인↔생성 사이 유지, 게임 진입 시 제거 |
| `src/client/screens/game.js` | 레이아웃 4.2(P, 캔버스 크기, 최소 시야 80, `visualViewport.resize`), 파이프라인 4.4(오프스크린 → 정수 배율 확대 → 글자), idle/walk 상태 머신(바뀌면 첫 프레임부터), 원격 보간을 등속 추적(160/초 + 뒤처짐 가속, 400 넘으면 순간 이동)으로 바꾸고 마지막 이동 150ms 안이면 walk. HUD를 캔버스 위 겹침으로, LOCAL MODE 칩은 접속자 배지 옆 슬롯 |
| `src/client/screens/login.js`, `create.js` | 픽셀 패널/탭/버튼/입력 스킨 마크업, 로고(icon-mushroom 4배), 로딩 점, LOCAL MODE 줄을 패널 맨 아래에. 생성 미리보기: 아트 48x60 캔버스를 CSS 4배(192x240), walk 반복, ↔ 방향 버튼, reduced-motion이면 idle0, 땅은 ground.png 일부 |
| `src/client/main.js` | 에셋 3종 로드(UI 스킨은 첫 화면 전에 최대 1.5초 대기), 배경 맵 생성/제거, LOCAL MODE 칩을 `position: fixed` 없이 화면 슬롯에 배치(`app.placeModeBadge`), supabase 모드에서는 숨김 |
| `src/client/style.css` | 전면 재작성. style-guide 1.3 토큰, 9-slice `border-image`(+`image-rendering: pixelated`), 상태별 파일 교체(7.10), 눌림 시 내용 4px 아래, 블러/둥근 모서리 없음, 포커스 2px u3. 스킨이 없을 때 같은 크기의 단색 + 2px 외곽선 대체 |

구현 메모
- 스킨 요소는 `border: 2px solid transparent` + `border-image-width`(패널/버튼 16px, 입력 8px, 칩 6px)로 그린다. 테두리 그림은 디자인 두께 그대로이고, 내용 위치는 padding으로 맞췄다(패널 내용 24px 안쪽 등).
- `getState().players[]`와 `me`에 `anim: 'idle'|'walk'` 추가. `assets`는 `{ source, images(아바타 시트 수), background(맵 레이어 有), mapLayers, ui }`.
- DOM에 `<img>`를 쓰지 않는다(아이콘은 CSS 배경). innerHTML 사용 0건, 사용자 문자열은 textContent/fillText만.
- 해제 경로: 게임 rAF/리스너/타이머(사이클 1 그대로), 생성 미리보기 rAF는 unmount에서 취소, 배경은 WAAPI 애니메이션 cancel + 리스너 AbortController + 리사이즈 타이머 해제.

## 1.1 메인 리뷰 반영 (2026-10-14)

1. 게임 캔버스 포커스 테두리: 자동 포커스(게임 진입, Esc 복귀)와 마우스 포커스에는 표시하지 않는다. Tab 키로 캔버스에 들어온 경우에만 `:focus-visible` + `.kbd-focus`일 때 캔버스 안쪽(offset -4px) 2px `rgba(247,201,72,0.85)`(y2 계열) 테두리. 클릭하면 바로 지운다 (`screens/game.js`의 tabNav 추적, `style.css`).
2. 데스크톱 게임 배치: 캔버스 → 12px → 채팅 행 묶음을 세로 가운데로 (채팅 아래 여백 16px 제거, 위아래 여백이 같음). 캔버스 바깥 배경을 검정 대신 하늘(k1, 캔버스 아래 끝까지)과 흙(w3, 그 아래)으로 이어 그려 맵이 화면 끝까지 이어져 보이게 했다. 경계는 `computeLayout()`이 `--ground-y`로 넣는다. 모바일 레이아웃은 그대로.
- 재검증: e2e 11/12 (실패는 항목 11의 328px 기대값 1건만), 콘솔 에러 0. 포커스: 자동 포커스 테두리 없음, Tab 포커스 테두리 있음, 클릭 후 없음. 스크린샷 `.../scratchpad/fe2/run2/d1280-3-game.png`, `.../run2/d1920-3-game.png`.
- 디자인 확인 요청: 데스크톱 캔버스 바깥 배경(하늘/흙 연장)과 포커스 테두리 색(y2 85%)은 style-guide에 없는 값이라 문서 반영이 필요하다.

## 2. 검증 결과 (2026-10-14, Chromium headless, 실제 에셋: 아바타 22, 맵 7, UI 19)

| 항목 | 결과 |
|---|---|
| `python3 tests/e2e_local.py` | 11/12 PASS. 실패는 항목 11의 한 검사 "캔버스 328px 폭"뿐 (실제 360x516). 아래 3장 참고. 항목 11의 나머지(가로 스크롤 없음, 터치 버튼 56px, 터치 이동 dx 165px, 채팅 입력 화면 안)는 통과 |
| 콘솔 에러 | 0건 (e2e 항목 10, 스크린샷 실행 3개 뷰포트 경고 포함 0건) |
| 원격 walk/idle | 이동 중 walk, 정지 후 idle, 연속 이동 중 idle 섞임 없음(20회 샘플 모두 walk) |
| 픽셀 선명도 | 게임 캔버스 1280x300 영역에서 아트 픽셀 블록 균일: dpr 1 2x2 블록 0/96000 불일치, dpr 2 4x4 블록 0/96000 불일치. 스크린샷 확대 확인(패널, 버튼, 라벨, 말풍선 테두리 선명) |
| 폴백 (모든 assets 404) | 로그인/생성/게임 동작, 말풍선/라벨/단색 맵/단색 아바타 표시. 콘솔은 의도한 404 3건 + 경고 3건(매니페스트별 1회) |
| 예전 id 호환 | `eyes-round→eyes-sparkle`, `top-vest-green→top-overalls-blue`, 없는 id → 기본값 |
| reduced-motion | 배경 애니메이션 0개(정지), 미리보기 idle0 |
| 배경 이동 | 1.2초 동안 레이어별 오프셋이 패럴랙스 비율로 증가, 모든 오프셋이 P(2)의 배수 |
| 360x640 | 캔버스 360x516(시야 180x258), 아래 터치 행 + 채팅 행 = 124px, 하단 빈 공간 없음, 라벨이 캔버스 안, HUD 한 줄(배지, LOCAL MODE, 로그아웃), 로그인/생성 LOCAL MODE 칩이 패널 안 |

스크린샷 (스크래치, 저장소 밖): `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/fe2/run1/`
- `d1280-1-login.png`, `d1280-2-create.png`, `d1280-3-game.png`(B 말풍선, A 걷는 중), `d1280-4-game-idle.png`
- `d1920-*` (P=3), `m360-*` (dpr 2, `m360-2b-create-scrolled.png` 포함)
- `fallback-login.png`, `fallback-create.png`, `fallback-game.png`
- 확대: `zoom-game.png`, `zoom-login.png`, `zoom-hud.png`
- 스크립트: `../shots.py`(3 뷰포트 스크린샷), `../checks.py`(walk/idle, 픽셀 균일성, 폴백, reduced-motion, 배경 이동)

## 3. 테스트와 디자인이 충돌하는 항목 (QA 수정 요청)

- `tests/e2e_local.py` 항목 11 "캔버스 328px 폭"은 사이클 1 레이아웃(좌우 16px 여백)을 검사한다. v2 디자인은 모바일 캔버스를 화면 폭 전체로 바꿨다(style-guide 4.2 `floor(innerWidth/2)*2`, game.md 3장/10장 "캔버스 360 x 516 CSS px", 사이클 1 QA "하단 빈 공간" 해결). 프런트는 디자인을 따랐다. QA가 기대값을 `360x516`(또는 `floor(vw/2)*2` x `floor((vh-124)/2)*2`)으로 바꿔 주면 12/12가 된다. 테스트 파일은 수정하지 않았다.

## 4. 다른 팀 요청

- 메인: ARCHITECTURE 계약 보강 제안. (1) `assets/avatar/manifest.json`의 `aliases`(평면 `{old: new}`)와 `frameOrder` 키를 계약에 기록. (2) 디자인 handoff 6장 1~3번(상태별 개별 파일, P=2/3, 가변 시야) 결정 기록. (3) getState에 `anim`이 추가되었음을 테스트 훅 문서에 기록.
- 디자인: (1) 로그인 Tab 순서 모순(사이클 1 handoff 8장)은 그대로다. (2) 생성 화면 파츠 행에 `tabindex="0"`을 줬다(행 포커스 + 방향키 규칙을 지키려면 필요). 의도와 다르면 알려 달라. (3) 게임 캔버스 포커스 표시를 메인 요청으로 바꿨다 (1.1절): Tab 진입 시에만 y2 계열 2px. style-guide 3.2/game.md 9장 갱신 요청.
- 아트: 요청 없음. 매니페스트 3종 모두 계약 형식 그대로 수용했다.
- 백엔드: 없음.

## 5. QA 확인 항목

1. 위 3장 기대값 수정 후 `python3 tests/e2e_local.py` 12/12.
2. 360x640 체크리스트 (login.md 9장, character-create.md 10장, game.md 10장): 특히 라벨 아래 끝 < 캔버스 아래 끝, 하단 빈 공간 없음, LOCAL MODE 칩 겹침 없음, 생성 화면 sticky 버튼 뒤 `c1` 띠.
3. dpr 1/2/3에서 아트 픽셀 정사각형과 스킨 테두리 선명. `border-image` + `image-rendering: pixelated`의 Safari/Firefox 표시(미검증).
4. 걷기 120ms x 4, 대기 500ms x 2, 좌우 반전 시 레이어 어긋남 없음, 여러 아바타의 idle 위상이 다름.
5. 원격 아바타: 이동 중 walk, 멈춘 뒤 약 150ms 안에 idle, 순간 이동(400 이상 차이) 시 걷기 잔상 없음.
6. 버튼 상태: 호버/눌림(내용 4px 아래)/비활성 스킨, 탭 활성 = primary-pressed, 입력 포커스/오류/비활성 스킨.
7. 폴백: `assets/` 일부 파일 삭제(예: hair 하나, map 레이어 하나, ui 버튼 하나) 시 그 부분만 대체되고 조작 가능.
8. 소프트 키보드(실기기): `visualViewport` 기준으로 캔버스가 줄고 채팅 행이 키보드 위에 남는지.
9. 로그인 → 생성 전환 시 배경 맵이 끊기지 않고 이어지는지, 게임 → 로그아웃 시 배경이 새로 생기는지.

## 6. 알려진 한계

- 모바일 소프트 키보드 동작은 headless에서 확인하지 못했다(`visualViewport.resize` 처리만 구현).
- dpr이 1.25처럼 P x dpr이 정수가 아니면 아트 픽셀 크기가 1px씩 고르지 않을 수 있다(브라우저 확대 배율 문제, 디자인 결과 기준은 dpr 1, 2).
- 텍스트는 시스템 폰트(이 환경은 Noto Sans CJK)라 플랫폼마다 글자 폭과 말풍선 줄바꿈 위치가 다르다. 픽셀 한글 폰트는 후속 과제(ARCHITECTURE).
- 폴백 아바타는 단색 상자형으로 단순하다(에셋 실패 시 조작 유지가 목적).
- 배경 맵은 WAAPI로 움직이므로 아주 오래된 브라우저(`Element.animate` 없음)에서는 정지 화면이 된다.
- Safari/Firefox, 실제 Supabase 모드는 이번에도 미검증이다.
