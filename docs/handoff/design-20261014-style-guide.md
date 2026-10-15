# 핸드오프: 디자인 스타일 가이드와 화면 설계 (2026-10-14)

작성: 디자인 팀. 대상: 아트(assets/), 프런트(index.html, src/client/), 메인.

## 1. 산출물

| 파일 | 내용 |
|---|---|
| docs/design/style-guide.md | 팔레트, 폰트, 간격, 월드 규격, 아바타 규격, 닉네임 라벨, 말풍선 (정본) |
| docs/design/screens/login.md | 로그인/회원가입 화면, 입력 규칙, 오류 문구, 상태 |
| docs/design/screens/character-create.md | 캐릭터 생성 화면, 닉네임 확인, 파츠 좌/우 선택, 미리보기 |
| docs/design/screens/game.md | 인게임 HUD, 채팅 입력, 조작, 360px 배치, 터치 버튼, 배너 |

## 2. 아트가 지켜야 할 값 (assets/)

- 캔버스: 64 x 96 캔버스 px 고정. SVG `viewBox="0 0 64 96"`, 배경 투명.
- 기준점 (anchor): 발 중앙 (32, 92). 발바닥이 y=92.
- 외곽선: `#2B2118`, 1.5 캔버스 px, round join.
- 레이어 순서 (아래 -> 위): skin, bottom, top, eyes, hair.
- 좌우 반전: 기준점 x=32 기준 `scale(-1,1)`. 얼굴은 정면 좌우 대칭.
- 경로: `assets/avatar/<part>/<id>.svg` (ARCHITECTURE 정본). 예: `assets/avatar/hair/hair-round-black.svg`.
- 영역 좌표 (캔버스 px): 얼굴 x16~48 y8~44 / 머리카락 윗부분 y0~26, 앞머리 아랫선 y 24.5 이하 / 눈 영역 x20~44 y26~38 (눈 중심 (25,31), (39,31)) / 몸통 x21~43 y46~68 / 다리 x24~31, x33~40 y66~84 / 신발 y83~92 / 허리 밴드 y63~77.
- 색: 아래 팔레트 HEX만 사용. 음영과 하이라이트 전용 색은 만들지 않는다.
- 파츠 목록 (id, 한글 label):

| part | id | label |
|---|---|---|
| skin | `skin-light` | 밝은 피부 |
| skin | `skin-tan` | 보통 피부 |
| skin | `skin-dark` | 진한 피부 |
| hair | `hair-round-black` | 둥근 단발 · 흑발 |
| hair | `hair-round-chestnut` | 둥근 단발 · 밤색 |
| hair | `hair-spiky-black` | 뾰족 머리 · 흑발 |
| hair | `hair-spiky-chestnut` | 뾰족 머리 · 밤색 |
| eyes | `eyes-dot` | 점 눈 |
| eyes | `eyes-round` | 큰 눈 |
| eyes | `eyes-happy` | 웃는 눈 |
| top | `top-tee-red` | 빨간 티셔츠 |
| top | `top-hoodie-blue` | 파란 후드티 |
| top | `top-vest-green` | 초록 조끼 |
| bottom | `bottom-shorts-navy` | 네이비 반바지 |
| bottom | `bottom-jeans-blue` | 청바지 |
| bottom | `bottom-skirt-pink` | 분홍 치마 |

- 파츠 내용: skin은 얼굴, 목, 몸통, 팔, 다리, 손 (신발 제외). eyes는 눈 2개와 볼터치 2개 포함. bottom은 하의와 신발 (신발은 3종 모두 `#6B4226`, 좌 x23~32 / 우 x32~41, y83~92). 세부 형태는 style-guide 5.4.
- 기본 조합: `{"skin":"skin-light","hair":"hair-round-black","eyes":"eyes-dot","top":"top-tee-red","bottom":"bottom-shorts-navy"}`
- manifest 권장 형태 (ARCHITECTURE 계약): `{"canvas":{"w":64,"h":96},"anchor":{"x":32,"y":92},"parts":{...},"layerOrder":["skin","bottom","top","eyes","hair"]}`. 파츠 옵션 순서는 style-guide 5.6과 같아야 한다 (캐릭터 생성 좌/우 순서).

## 3. 프런트가 지켜야 할 값 (index.html, src/client/)

### 3.1 팔레트 (CSS 토큰, `:root`에 정의)

| 토큰 | HEX |
|---|---|
| primary | `#FF8A3D` (hover `#FF9A57`, shadow `#C9510F`, 글자 `#2B1A10`) |
| secondary | `#4DA3FF` (soft `#E6F2FF`, 글자 `#1F4E8C`) |
| text / muted / disabled | `#2B2118` / `#6B5A4B` / `#A89A8C` (비활성만) |
| panel / panel-alt | `#FFF9F0` / `#FFF1DE` |
| border / border-strong | `#D9C8B4` / `#8C7360` |
| focus | `#4DA3FF` (3px 링, 투명도 40%) |
| error / error-bg | `#D62E2E` / `#FDECEC` |
| success / success-bg | `#1F7A44` / `#E6F6EC` |
| letterbox | `#1B140E` |
| label-bg / label-text | `rgba(43,33,24,0.72)` / `#FFFFFF` |
| label-self-bg / label-self-text | `#FF8A3D` / `#2B1A10` |
| bubble-bg / bubble-border / bubble-text | `#FFFFFF` / `#2B2118` / `#2B2118` |
| 월드 하늘 / 잔디 / 흙 | `#8FD8FF`->`#D6F3FF` / `#9BE35A` `#6CC443` `#3E9A2A` / `#C98B55` `#A46A3C` `#7A4A28` |

다크 모드는 이번 범위가 아니다.

### 3.2 폰트, 간격, 모서리

- 폰트 스택 (외부 로드 금지): `system-ui, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif`. Canvas 텍스트도 같은 스택.
- 크기: 12 / 14 / 16 / 20 / 28 px. 입력 글자 16px 이상.
- 간격 4px 단위: 4, 8, 12, 16, 24, 32. 모바일 좌우 여백 16px.
- 모서리: 4 (라벨), 8 (입력/버튼), 12 (패널/말풍선), 999 (배지).
- 그림자: 패널 `0 4px 12px rgba(43,33,24,0.18)`, 주 버튼 `0 3px 0 #C9510F`.

### 3.3 월드 규격

| 항목 | 값 |
|---|---|
| 월드 크기 | 가로 2400, 세로 540 (논리 px) |
| 지면 y (발 위치) | 440. 잔디 띠 440~468, 흙 468~540 |
| 이동 속도 | 160 px/초, 등속, 좌우만 |
| 이동 범위 (기준점 x) | 32 ~ 2368 |
| 데스크톱 시야 | 960 x 540 (뷰포트 폭 720 이상), 카메라 `camY = 0` |
| 모바일 시야 | 480 x 270 (뷰포트 폭 720 미만), 카메라 `camY = 200` |
| 카메라 X | `clamp(playerX - viewW/2, 0, 2400 - viewW)` |
| 배율 | `min(canvasCssW/viewW, canvasCssH/viewH)`, 백킹 스토어 x devicePixelRatio |
| 아바타 화면 위치 | 캔버스 좌상단 = `(x - 32*s, 440 - 92*s)` |
| 흔들림 | 이동 중 상하 2px, 주기 0.4초 |

### 3.4 라벨과 말풍선 (화면 px 기준, 카메라 배율과 무관)

- 닉네임 라벨: 발 아래, 라벨 상단 = 발 화면 y + 4px. 12px 700, 패딩 2px 6px, 모서리 4px. 최대 12자.
- 말풍선: 꼬리 끝 = 아바타 캔버스 y=4 위 6px, 꼬리 중심 x = 기준점 x. 꼬리 밑변 12, 높이 8. 본체 최대 폭 200, 최소 폭 40, 패딩 8px 12px, 글자 14px / 줄간격 18px, 테두리 2px, 모서리 12px.
- 줄 수 최대 4, 초과는 `…`. 표시 5초 + 마지막 0.5초 페이드. 같은 사용자의 새 말풍선은 즉시 교체.
- 화면 밖 보정: 좌우 8px 여백 안으로 밀기. 꼬리는 아바타 x를 계속 가리킨다.
- 글자는 Canvas `fillText`만 사용. 사용자 입력을 DOM에 넣을 때는 `textContent`로만 넣는다 (XSS).

### 3.5 그리기 순서

하늘 -> 구름 -> 먼 언덕 -> 잔디/흙 -> 다른 아바타 -> 내 아바타 -> 닉네임 라벨 -> 말풍선 -> DOM HUD.

### 3.6 화면 흐름과 조작

- 로그인 성공: 캐릭터 있음 -> 인게임, 없음 -> 캐릭터 생성. 회원가입 성공 -> 캐릭터 생성.
- 아이디 정규식 `^[a-z0-9_]{4,16}$`, 비밀번호 8자 이상, 비밀번호 확인 필드 (회원가입).
- 닉네임 정규식 `^[가-힣a-zA-Z0-9]{2,12}$`. 중복 확인은 500ms 디바운스 + blur. 최종 판단은 서버.
- 캐릭터 생성 저장 값: `{ nickname, avatar: { skin, hair, eyes, top, bottom } }`.
- 키: 방향키 또는 A/D 이동, Enter 채팅 포커스 또는 전송, Esc 포커스 해제. 입력 포커스 중에는 이동 키 무시. IME 조합 중 Enter 무시. 창 blur 시 이동 정지.
- 채팅: trim, 빈 값 무시, 최대 80자, 1초 쿨다운 (디자인 추가 값, 힌트 "1초 뒤에 다시 보낼 수 있습니다."), 내 말풍선은 서버 왕복 없이 즉시 표시.
- 이동 broadcast: ARCHITECTURE의 10회/초 제한 유지 (100ms 간격 송신, 정지 시 마지막 좌표 1회 추가 송신).
- 재연결: 자동 3회 (1, 2, 4초 간격) 후 "다시 연결" 버튼.
- 모바일 터치 버튼: `pointerdown` 시작, `pointerup`/`pointercancel`/`pointerleave` 정지. `touch-action: none`.
- 모바일 레이아웃 세로 순서: 상단 바 48px -> 캔버스 185px (328 x 185 CSS) -> 터치 버튼 행 56px -> 채팅 입력 행 44px. 여백 8px.

## 4. 메인이 확인할 사항 (디자인이 정한 값과 상충 가능성)

1. 경로 불일치: ARCHITECTURE는 `assets/avatar/<part>/<id>.svg`, art.md 예시는 `assets/avatar/hair-short-brown.svg` (평면). 이 문서는 ARCHITECTURE를 따랐다. art.md 예시를 고치거나 역할 정의에 맞출지 메인이 정한다.
2. 머리색: 팔레트에 4색을 두되 id는 2 모양 x 2 색 (흑발, 밤색)만 쓴다. 금발과 분홍 머리는 예약 색이다. 추가 id는 디자인 팀이 먼저 확정한다.
3. 디자인 추가 값 (요구에 없던 항목): 비밀번호 확인 필드, 채팅 1초 쿨다운, 말풍선 4줄 제한, 모바일 카메라 `camY=200`, 캔버스 배율 규칙, 아바타 흔들림 2px.
4. 말풍선 4줄 제한으로 80자 메시지 일부가 보이지 않는다. 필요하면 최대 줄 수 또는 글자 크기를 메인이 조정한다.
5. 폰트: 한글 시스템 폰트가 없는 Linux 환경에서는 `sans-serif` 대체 글꼴로 줄바꿈이 달라질 수 있다. QA는 Noto Sans KR 설치 환경에서 확인해야 한다.
6. 게임 캔버스 16:9 고정 때문에 모바일에서 아바타 표시 크기가 작다 (발 기준 약 44 x 65 화면 px). 아트가 작은 크기에서 얼굴 특징이 보이는지 확인해야 한다.

## 5. 후속 요청 후보

- 아트: 파츠 SVG 16개 (skin 3, hair 4, eyes 3, top 3, bottom 3) 제작 및 `assets/avatar/manifest.json`.
- 프런트: 로그인/캐릭터 생성 화면 구현 (`login.md`, `character-create.md`), 인게임 HUD (`game.md`), 라벨/말풍선 렌더링 (`style-guide.md` 6, 7장).
- QA: 360px 체크리스트 (`game.md` 10장), 오류 문구 정확성, 키보드 조작, 한글 IME 전송.
