# 버섯마을 스타일 가이드

버전: 2.0 (2026-10-14, 사이클 2 픽셀아트 전면 개정)
정본(canonical) 범위: 픽셀 팔레트, 폰트, 간격, 배율, 게임 월드 규격, 아바타 해부도와 프레임, 파츠 목록, 맵 레이어, UI 스킨, 닉네임 라벨, 말풍선.
상위 계약: `docs/ARCHITECTURE.md` "픽셀아트 계약" (프레임 32x48, 기준점 (16,46), 시트 192x48, 프레임 순서, 타이밍, 경로, 매니페스트 형식). 이 문서는 그 계약 안에서 값을 정한다.
아트(Pillow 스크립트)와 프런트(Canvas, DOM)는 이 문서의 값을 그대로 쓴다. 값을 바꾸려면 디자인 팀이 이 문서를 먼저 고친다.

사이클 1(v1.0)에서 바뀌지 않은 것: 화면 흐름, 모든 문구, 입력 규칙, 아바타 data 키(`skin, hair, eyes, top, bottom`), 월드 2400x540, 지면 y=440, 이동 속도 160/초, 이동 범위, 말풍선 표시 규칙(5초, 4줄, 80자), 접근성 규칙.
폐기된 것: SVG 64x96 캔버스, 벡터 외곽선, 둥근 모서리 CSS UI, 정면 대칭 얼굴, 사인파 흔들림.

## 0. 표기와 단위

| 단위 | 뜻 | 관계 |
|---|---|---|
| 아트 px | PNG 한 픽셀 | 월드 2단위 = 아트 1px |
| 월드 단위 | 게임 로직 좌표 (이동, 실시간 메시지) | 2400 x 540, 지면 y=440 |
| CSS px | 화면 표시 크기 | 아트 1px = `P` CSS px (P = 픽셀 배율, 4.2절) |
| UI 배율 `U` | UI 스킨 PNG 1px의 CSS 크기 | 항상 2 (화면 크기와 무관) |

- 좌표 `(x, y)`는 왼쪽 위가 (0,0)이고, 픽셀 `(x, y)`는 x열 y행 한 칸을 뜻한다. 범위 `x 12–14`는 양 끝을 포함한다.
- 색은 HEX 대문자 6자리. 팔레트 토큰 이름(`r2`, `w4` 등)으로 부른다.
- 모든 PNG 픽셀은 완전 불투명 또는 완전 투명이다. 반투명, 안티에일리어싱, 디더링 금지.

참고 시안 (디자인 초안, 값 검증용): `docs/design/ref/` (11장). 시안과 이 문서가 다르면 이 문서가 정본이다.

---

## 1. 픽셀 팔레트 (42색, 정본)

규칙
- 아트 PNG는 아래 42색만 쓴다. 새 색을 만들지 않는다. 필요하면 디자인에 요청한다.
- 외곽선은 순검정을 쓰지 않는다. 각 재료 램프의 가장 어두운 톤이 그 재료의 외곽선이다.
- 램프 순서: 하이라이트(hl) → 기본(base) → 그림자(shade) → 외곽선(line). 3단 램프는 그림자와 외곽선을 같은 톤으로 쓴다.
- 여러 재료가 같은 HEX를 공유한다 (예: 밤색 머리 = 나무, 분홍 머리 = 분홍 치마). 표의 "공유" 열이 그 관계다.

### 1.1 전체 색표

| 토큰 | HEX | 램프 | 공유 / 주 용도 |
|---|---|---|---|
| `ink` | `#1A1626` | 잉크 | 흑발 외곽선, 눈동자, 말풍선/라벨 외곽선, 본문 글자, 반바지(네이비) 외곽선 |
| `hb1` | `#4A4560` | 흑발 hl | 흑발 하이라이트, 돌 외곽선, 굴뚝 외곽선 |
| `hb2` | `#2E2A3E` | 흑발 base | 흑발 기본, 다른 사람 닉네임 라벨 배경, 말풍선 외곽선 |
| `w1` | `#E0A868` | 나무 hl | 나무 하이라이트, 패널 테두리 윗줄 |
| `w2` | `#B97A4A` | 나무 base | 나무, 문, 울타리, 밤색 머리 hl, 신발 hl, 진한 피부 base, 밝은 피부 외곽선 |
| `w3` | `#8A5232` | 나무 shade | 흙 base, 밤색 머리 base, 신발 base, 보통 피부 외곽선, 진한 피부 shade, 보조 글자 |
| `w4` | `#5E3620` | 나무 line | 나무/흙/밤색 머리/신발 외곽선, 진한 피부 외곽선, 눈썹, 패널 외곽선 |
| `s1` | `#FFE3CC` | 피부 | 밝은 피부 base |
| `s2` | `#F5C29A` | 피부 | 밝은 피부 shade, 보통 피부 base |
| `s3` | `#D99464` | 피부 | 보통 피부 shade |
| `white` | `#FFFFFF` | 공통 | 눈빛, 말풍선 바탕, 구름, 크림 원단 hl, 입력창 바탕 |
| `y1` | `#FFF2A8` | 노랑 | 금발 hl, 창문 불빛, 버튼 hl |
| `y2` | `#F7C948` | 노랑 | 금발 base, 주황 갓 hl, 주 버튼 바탕, 단추, 꽃 |
| `y3` | `#F08A2E` | 주황 | 주황 갓 base, 버튼 아래 그늘, 내 닉네임 라벨 배경 |
| `y4` | `#A84A1E` | 주황 line | 금발/주황 갓 외곽선, 버튼 립(lip), 내 닉네임 라벨 외곽선 |
| `p1` | `#FFC8DC` | 분홍 | 분홍 머리/치마 hl |
| `p2` | `#F58AB4` | 분홍 | 분홍 머리/치마 base, 볼터치, 꽃 |
| `p3` | `#B04A78` | 분홍 line | 분홍 머리/치마 외곽선, 치마 주름 |
| `r1` | `#FF8E7A` | 빨강 | 빨강 원단/갓 hl, 빨간 신발 hl, 입력 오류 링 |
| `r2` | `#E8483E` | 빨강 | 빨간 티셔츠, 빨간 갓, 망토, 꽃 |
| `r3` | `#9E2838` | 빨강 line | 빨강 외곽선, 오류 글자 |
| `u1` | `#9CC8FF` | 파랑 | 파랑 원단/갓 hl, 포커스 링 안쪽 |
| `u2` | `#4D7CFE` | 파랑 | 후드티, 청바지, 파란 갓, 멜빵, 눈 홍채 |
| `u3` | `#2E3E9E` | 파랑 line | 파랑 외곽선, 네이비 hl, 포커스 링 |
| `u4` | `#232A5E` | 네이비 | 네이비 반바지 base |
| `g1` | `#B6E86A` | 초록 | 잔디 윗줄, 나무잎 hl, 호박바지 hl |
| `g2` | `#6CC443` | 초록 | 잔디, 나무잎, 호박바지 base |
| `g3` | `#3E8A2E` | 초록 | 잔디 그늘, 잎 그늘, 줄기, 아바타 발 그림자 |
| `g4` | `#23562A` | 초록 line | 잔디/잎/호박바지 외곽선, 성공 글자 |
| `c1` | `#FFF6E4` | 크림 | 버섯 기둥, 패널 바탕, 크림 셔츠, 갓 점, 연기 |
| `c2` | `#F2DDB8` | 크림 | 크림 그늘, 패널 안쪽 그림자, 비활성 버튼 |
| `c3` | `#C9A47A` | 크림 line | 크림 셔츠 외곽선, 버섯 주름, 입력창 안쪽 그림자 |
| `m1` | `#BFF0DC` | 민트 | 먼 산, 민트 머리 hl, 언덕 윗줄 |
| `m2` | `#7ED6B4` | 민트 | 가까운 언덕, 민트 머리 base |
| `m3` | `#3E9A86` | 민트 line | 민트 머리 외곽선 |
| `k1` | `#6EC6F5` | 하늘 1 | 하늘 맨 위 밴드, 월드 위쪽(y<0) 채움 |
| `k2` | `#86D2F8` | 하늘 2 | 하늘 밴드 |
| `k3` | `#A0DDFA` | 하늘 3 | 하늘 밴드 |
| `k4` | `#BBE8FC` | 하늘 4 | 하늘 밴드, 구름 아랫줄 |
| `k5` | `#D8F3FE` | 하늘 5 | 지평선 밴드, 구름 그늘 |
| `st1` | `#C8C4D0` | 돌 | 돌 hl, 굴뚝, 디딤돌 |
| `st2` | `#8E88A0` | 돌 | 돌 base (외곽선은 `hb1`) |

합계 42색 (48색 한도 중 6색 여유, 추가는 디자인 승인 필요).

### 1.2 재료별 램프 (hl / base / shade / line)

| 재료 | hl | base | shade | line |
|---|---|---|---|---|
| 피부: 밝은 (`skin-light`) | - | `s1` | `s2` | `w2` |
| 피부: 보통 (`skin-tan`) | - | `s2` | `s3` | `w3` |
| 피부: 진한 (`skin-dark`) | - | `w2` | `w3` | `w4` |
| 머리: 흑발 `black` | `hb1` | `hb2` | `ink` | `ink` |
| 머리: 밤색 `chestnut` | `w2` | `w3` | `w4` | `w4` |
| 머리: 금발 `blonde` | `y1` | `y2` | `y4` | `y4` |
| 머리: 분홍 `pink` | `p1` | `p2` | `p3` | `p3` |
| 머리: 민트 `mint` | `m1` | `m2` | `m3` | `m3` |
| 원단: 빨강 `red` | `r1` | `r2` | `r3` | `r3` |
| 원단: 파랑 `blue` | `u1` | `u2` | `u3` | `u3` |
| 원단: 네이비 `navy` | `u3` | `u4` | `ink` | `ink` |
| 원단: 분홍 `pink` | `p1` | `p2` | `p3` | `p3` |
| 원단: 초록 `green` | `g1` | `g2` | `g3` | `g4` |
| 원단: 크림 `cream` | `white` | `c1` | `c3` | `c3` |
| 신발: 갈색 | `w2` | `w3` | `w4` | `w4` |
| 신발: 빨강 | `r1` | `r2` | `r3` | `r3` |
| 버섯 갓: 빨강 | `r1` | `r2` | `r3` | `r3` |
| 버섯 갓: 주황 | `y2` | `y3` | `y4` | `y4` |
| 버섯 갓: 파랑 | `u1` | `u2` | `u3` | `u3` |
| 버섯 기둥 | `white` | `c1` | `c2` | `w3` |
| 갓 점 무늬 | - | `c1` | `c2` | - (외곽선 없음) |
| 잔디 | `g1` | `g2` | `g3` | `g4` |
| 흙 | `w2` (작은 반점) | `w3` | `w4` (반점) | `w4` |
| 나무(목재) | `w1` | `w2` | `w3` | `w4` |
| 나무(잎) | `g1` | `g2` | `g3` | `g4` |
| 돌 | `st1` | `st2` | `hb1` | `hb1` |
| 하늘 밴드 (위→아래) | `k1` → `k2` → `k3` → `k4` → `k5` | | | |
| 먼 산 | `white` (능선 1줄) | `m1` | - | - |
| 가까운 언덕 | `m1` (능선 1줄) | `m2` | - | - |
| 구름 | - | `white` | `k5` (아래 2줄) | `k4` (맨 아랫줄) |
| 눈 | 눈빛 `white` | 눈동자 `ink` | 홍채 `u2` | - |
| 볼터치 | - | `p2` | - | - |

### 1.3 UI 글자/CSS 색 토큰 (팔레트에서 파생)

DOM CSS는 아래 토큰만 쓴다. `:root`에 CSS 변수로 정의한다.

| 토큰 | 값 | 용도 | 대비 (바탕 `c1` 기준) |
|---|---|---|---|
| `--text` | `#1A1626` (ink) | 본문, 버튼 글자, 라벨 | 16.5:1 |
| `--text-strong` | `#5E3620` (w4) | 부제, 소제목 | 9.7:1 |
| `--text-muted` | `#8A5232` (w3) | 도움말, 카운터, 비활성 탭 글자, 비활성 버튼 글자 | 5.9:1 (`c2` 위 4.7:1) |
| `--error` | `#9E2838` (r3) | 오류 글자, 오류 배너 테두리 | 6.9:1 (`p1` 위 5.2:1) |
| `--error-bg` | `#FFC8DC` (p1) | 오류 배너 바탕 (7.11절) | |
| `--success` | `#23562A` (g4) | 사용 가능 표시 | 8.0:1 |
| `--focus` | `#2E3E9E` (u3) | 키보드 포커스 외곽선 2px + 간격 2px | 8.5:1 |
| `--panel` | `#FFF6E4` (c1) | 패널 바탕 (스킨이 없을 때 대체) | |
| `--letterbox` | `#1A1626` (ink) | 게임 캔버스 바깥 | |
| `--sky` | `#6EC6F5` (k1) | 맵 로딩 전 화면 바탕 | |

글자-바탕 대비: 주 버튼 `ink` on `y2` 11.3:1, 호버 `ink` on `y1` 15.6:1, 내 라벨 `ink` on `y3` 7.1:1, 다른 사람 라벨 `white` on `hb2` 13.8:1, 말풍선 `ink` on `white` 17.7:1. 모두 WCAG AA 이상.

---

## 2. 타이포그래피

### 2.1 폰트

외부 폰트 로드 금지. 시스템 폰트, 굵게 위주. 픽셀 한글 폰트(Galmuri)는 후속 과제다 (ARCHITECTURE).

```
--font-ui: system-ui, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", "Noto Sans CJK KR", "Segoe UI", sans-serif;
```

- 모든 텍스트는 화면 해상도(CSS px x devicePixelRatio)에서 그린다. 아트 해상도 버퍼에 글자를 그린 뒤 확대하지 않는다.
- Canvas: `ctx.font = "700 12px " + FONT_UI`, `ctx.textBaseline = "top"`. 글자 x, y는 정수 CSS px로 반올림한다.

### 2.2 크기 단계

| 토큰 | 크기 / 줄간격 | 굵기 | 용도 |
|---|---|---|---|
| `fs-xs` | 12px / 16px | 700 | 닉네임 라벨, 도움말, 카운터, LOCAL MODE 칩(11px 예외) |
| `fs-sm` | 14px / 18px | 700 | 말풍선 글자, 필드 라벨, 배지, 탭, 부제 |
| `fs-md` | 16px / 22px | 700 (입력 글자는 400) | 버튼 글자, 파츠 값 |
| `fs-lg` | 20px / 26px | 700 | 화면 제목 |
| `fs-xl` | 32px / 38px | 800 (없으면 700) | 로고 "버섯마을" |

규칙: 입력 필드 글자는 16px 이상 (모바일 Safari 확대 방지). 본문 굵기는 700이 기본이다 (픽셀 UI 위에서 가는 글자가 묻히지 않게).

### 2.3 픽셀 느낌 글자 규칙 (1px 그림자)

| 대상 | 글자색 | 그림자 | 비고 |
|---|---|---|---|
| 다른 사람 닉네임 | `white` | `ink`, 오프셋 (+1, +1) CSS px | 라벨 바탕 `hb2` |
| 내 닉네임 | `ink` | `y1`, 오프셋 (0, +1) | 라벨 바탕 `y3` |
| 말풍선 글자 | `ink` | `c2`, 오프셋 (+1, +1) | 바탕 `white` |
| 버튼 글자 (주/보조) | `ink` | `white`, 오프셋 (0, +1). 호버와 비활성은 그림자 없음 | 7.3 표 |
| 로고 "버섯마을" | `c1` | `w4` 8방향 2px 외곽 + 아래 (0, +4) `w4` | CSS `text-shadow` 9개. 시안 `ref/login-desktop.png` |
| 패널 안 본문 | `--text` | 없음 | |

Canvas 그림자는 `shadowBlur`를 쓰지 않는다. 그림자 색으로 오프셋 위치에 한 번, 본색으로 한 번, 총 두 번 `fillText`한다. CSS는 `text-shadow: 1px 1px 0 <색>` (블러 0).

---

## 3. 간격, 격자, 모서리

### 3.1 간격 (DOM 레이아웃, 4px 기준, 사이클 1과 같음)

| 토큰 | 값 | 용도 |
|---|---|---|
| `sp-1` | 4px | 아이콘과 글자 사이 |
| `sp-2` | 8px | 요소 내부 작은 간격, 버튼 그룹 간격, 모바일 세로 간격 |
| `sp-3` | 12px | HUD 여백, 칩 가로 패딩 |
| `sp-4` | 16px | 필드 사이, 모바일 좌우 여백 |
| `sp-5` | 24px | 패널 안쪽 여백 (스킨 테두리 16 + 8) |
| `sp-6` | 32px | 화면 블록 사이 |

### 3.2 픽셀 격자 규칙

- UI 스킨 요소의 CSS 크기(가로, 세로, 위치)는 2의 배수로 맞춘다 (U=2). 홀수 크기면 9-slice 가운데가 반 픽셀로 늘어나 흐려진다.
- `border-radius`, 블러가 있는 `box-shadow`, 그라데이션은 쓰지 않는다 (블러 0 오프셋 그림자는 허용). 둥근 모서리와 입체감은 스킨 PNG의 픽셀로 표현한다.
- 스킨 PNG를 쓰는 모든 요소에 `image-rendering: pixelated;`를 준다 (border-image에도 적용된다. Chromium, Firefox, Safari 확인 필요 항목으로 QA에 넘긴다).
- 포커스 표시: `outline: 2px solid var(--focus); outline-offset: 2px;` (모든 버튼, 입력, 파츠 행, 캔버스).

---

## 4. 게임 월드 규격

### 4.1 월드 (사이클 1과 같음)

| 항목 | 월드 단위 | 아트 px | 설명 |
|---|---|---|---|
| 월드 크기 | 2400 x 540 | 1200 x 270 | |
| 지면 (발 위치) | y = 440 | y = 220 | 아바타 기준점 y. 잔디 윗면 첫 줄이 아트 y 220 |
| 이동 속도 | 160 / 초 | 80 / 초 | 등속, 가속 없음 |
| 이동 범위 | 기준점 x 32 ~ 2368 | 16 ~ 1184 | |
| 이동 방향 | 좌우만 | | 점프, 상하 이동 없음 |
| 시작 위치 | 기존 프런트 규칙 유지 | | |

사이클 1의 "이동 중 상하 2px 사인 흔들림"은 폐기한다. 흔들림은 프레임 애니메이션(5.4절)이 담당한다.

### 4.2 픽셀 배율 P와 캔버스 크기

정수 배율만 쓴다. `P` = 아트 1px의 CSS px 크기.

| 조건 | P | 캔버스 CSS 가로 | 캔버스 CSS 세로 |
|---|---|---|---|
| 모바일 (`innerWidth < 720`) | 2 | `floor(innerWidth / 2) * 2` (좌우 여백 없음, 화면 꽉 채움) | `floor((innerHeight - 124) / 2) * 2` (아래 조작 영역 124px을 뺀 전부) |
| 데스크톱 (`innerWidth >= 720`) | 2 | `min(floor(innerWidth / 2) * 2, 1280)` | `min(540, floor((innerHeight - 72) / 2) * 2)` |
| 큰 데스크톱 (`innerWidth >= 1600` 그리고 `innerHeight >= 900`) | 3 | `min(floor(innerWidth / 3) * 3, 1920)` | `min(810, floor((innerHeight - 72) / 3) * 3)` |

- 시야(아트 px): `viewW = cssW / P`, `viewH = cssH / P`. 데스크톱 최대 640 x 270, 모바일 360x640 폰에서 180 x 258.
- 세로 최소: `viewH`가 80 미만이면 80(CSS 160px)으로 두고 페이지 세로 스크롤을 허용한다 (가로 모드 폰, 소프트 키보드 대비). viewH 80이면 아트 y 170–250이 보여 아바타 전신과 라벨이 들어온다.
- 크기는 `resize`와 `visualViewport.resize`(모바일 소프트 키보드)마다 다시 계산한다.
- `P=1`은 쓰지 않는다 (아바타가 32x48 CSS px로 너무 작다). 1배는 화면 폭 360px 미만에서도 쓰지 않고 가로를 그대로 줄인다.

### 4.3 카메라 (아트 px)

```
camX = clamp(round(playerArtX - viewW / 2), 0, max(0, 1200 - viewW))
camY = 250 - viewH        // 화면 아래 끝 = 아트 y 250 (지면 아래 흙 30px 고정)
```

- 화면 아래 끝은 항상 아트 y 250이다. 지면(220) 아래로 흙 30 아트 px(= 60 CSS px)가 보이고, 닉네임 라벨은 이 안에 들어간다 (사이클 1 QA: 모바일 라벨 잘림 해결).
- `camY`가 음수이면(시야가 250보다 큼) 월드 위쪽 바깥(y<0)은 `k1`로 채운다. 큰 화면, 세로가 긴 폰에서 하늘이 위로 늘어난다.
- `camX`, `camY`는 정수 아트 px. 월드 단위로는 `camX * 2`.

### 4.4 렌더 파이프라인 (권장, 결과 기준은 필수)

1. 오프스크린 캔버스(아트 해상도 `viewW x viewH`)에 `k1`로 채운 뒤 맵 레이어 → 발 그림자 → 아바타를 그린다. `imageSmoothingEnabled = false`.
2. 메인 캔버스(백킹 `cssW x dpr`, `cssH x dpr`)에 오프스크린을 정수 배율 없이 한 번에 확대해 그린다 (`drawImage(off, 0, 0, W, H)`, 스무딩 끔).
3. 메인 캔버스에 화면 해상도로 닉네임 라벨, 말풍선(스킨 9-slice는 U=2 x dpr 배율, 스무딩 끔), 글자를 그린다.

- 아바타 아트 좌표 = `round(worldX / 2)`. 라벨과 말풍선도 이 반올림한 좌표를 기준으로 계산해서 스프라이트와 함께 움직이게 한다 (떨림 방지).
- 레이어 x 오프셋: `ox = -floor(camX * parallax)`. `repeatX: true`면 `ox mod 이미지폭`부터 시야 끝까지 반복해서 그린다. 레이어 y = 매니페스트 `y - camY`.
- 결과 기준: 모든 아트 픽셀이 같은 크기의 정사각형으로 보이고(dpr 1, 2 기준), 흐린 가장자리가 없어야 한다.

### 4.5 그리기 순서 (뒤 → 앞)

1. `k1` 채움
2. 맵 레이어 (매니페스트 순서: 하늘 → 구름 → 먼 산 → 언덕 → 중경 나무 → 마을 소품 → 지면)
3. 발 그림자 (모든 아바타): 아트 y 220 줄에 x `ax-6 ~ ax+5`, y 221 줄에 x `ax-5 ~ ax+4`를 `g3`로 칠한다 (`ax` = 기준점 아트 x)
4. 아바타 (다른 사용자 먼저, 내 캐릭터 마지막)
5. 닉네임 라벨
6. 말풍선
7. DOM HUD (캔버스 위에 겹치는 배지, 버튼)

---

## 5. 아바타 규격 (가장 중요)

### 5.1 프레임과 기준점 (ARCHITECTURE 계약 재확인)

| 항목 | 값 |
|---|---|
| 프레임 | 32 x 48 아트 px, 배경 투명 |
| 시트 | 가로 한 줄 6프레임 192 x 48: `idle0, idle1, walk0, walk1, walk2, walk3` (프레임 i의 x = 32i) |
| 기준점 | (16, 46). 픽셀 열 15와 16 사이 선, 행 46의 윗선. 발바닥 마지막 불투명 줄은 y 45 |
| 방향 | 기본은 오른쪽을 보는 3/4뷰. 왼쪽은 프레임 전체를 좌우 반전 (픽셀 열 c → 31 - c). 기준점은 반전해도 같다 |
| 표시 | 아트 1px = 월드 2단위. 월드 `(x, 440)`에 서면 프레임 왼쪽 위 = 월드 `(x - 32, 348)` = 아트 `(round(x/2) - 16, 174)` |
| 등신 | 머리(머리카락 포함) 약 18줄 : 몸 약 22줄 (2~2.5등신, 큰 머리) |
| 행 46, 47 | 항상 투명 (그림자는 프런트가 그린다, 4.5절) |

해부도 시안: `docs/design/ref/anatomy-14x.png` (14배, 4px마다 진한 격자, 파란 상자 = 눈 상자, 분홍 십자 = 기준점, 주황선 = 머리/몸통/다리/신발 경계).

### 5.2 해부도 (idle0 기준 좌표, 다른 프레임은 5.3 오프셋 적용)

| 영역 | 좌표 (아트 px) | 설명 |
|---|---|---|
| 머리카락 외곽 최대 | x 3–28, y 1–29 | 머리 모양별 5.6.2 격자. 긴머리만 y 29까지 |
| 머리 피부(두상) | x 7–24, y 8–24 | 행별 범위는 5.5.1 격자. 턱 끝은 오른쪽(앞)으로 치우침 |
| 얼굴 (앞머리 아래 보이는 피부) | x 12–23, y 15–23 | 앞머리 아랫선은 눈 상자 열에서 y 14 이하 |
| 뒷눈 상자 | x 13–15, y 15–19 | 첫 줄(y 15)은 눈썹 줄. 실제 눈은 주로 x 14–15 |
| 앞눈 상자 | x 19–21, y 15–19 | 첫 줄(y 15)은 눈썹 줄. 실제 눈은 주로 x 19–20 |
| 두 눈 사이 | x 16–18 | 3px 피부. 3/4뷰라 두 눈이 머리 중심(x 15.5)보다 오른쪽에 있다 |
| 귀 (뒤쪽) | x 10–11, y 16–18 | 피부 shade, 귀 안쪽 (11,17) 피부 line |
| 볼터치 | (13,21), (21,21), (22,21) | `p2`. 웃는 눈은 (12,21) 추가 |
| 입 | (18,22), (19,22) | 피부 line (skin 레이어) |
| 몸통 | x 11–19, y 25–33 (y 25는 x 12–18) | 상의 y 25–32, 하의 허리 y 33 |
| 앞팔 (가까운 팔, 몸통 위에 그림) | x 10–12: 윗팔 y 26–28, 아래팔 y 29–30, 손 y 31–32 | 화면 왼쪽(등 쪽)에 걸친다 |
| 뒷팔 (먼 팔, 몸통 뒤) | x 20–21: 윗팔 y 26–28 (y 26은 x 20만), 아래팔 y 29–30, 손 y 31–32 | 몸통 오른쪽(가슴 쪽)으로 살짝 보인다 |
| 앞다리 (가까운 다리) | x 12–14, y 34–42 | 화면 왼쪽 |
| 뒷다리 (먼 다리) | x 16–18, y 34–42 | 화면 오른쪽 |
| 앞발 (신발) | y 43: x 12–14, y 44–45: x 12–15 | 앞코가 오른쪽으로 1px |
| 뒷발 (신발) | y 43: x 16–18, y 44–45: x 16–19 | |

### 5.3 프레임별 오프셋 표

`dy` = 머리(두상, 얼굴, 눈, 머리카락), 몸통, 양팔 전체의 세로 이동량. 다리는 엉덩이(몸통 아래) 바로 아래에서 시작해 y 42에서 끝나므로 `dy`만큼 길이가 바뀐다. 발은 땅에 있는 한 y 43–45 고정.

| 프레임 | 시간 | dy | 앞다리 / 앞발 | 뒷다리 / 뒷발 | 앞팔 | 뒷팔 |
|---|---|---|---|---|---|---|
| idle0 | 500ms | 0 | 기본 (x 12–14) | 기본 (x 16–18) | 기본 (x 10–12) | 기본 (x 20–21) |
| idle1 | 500ms | +1 (숨 내쉼) | 기본, y 35–42 | 기본, y 35–42 | 기본 +1 | 기본 +1 |
| walk0 | 120ms | 0 | 앞으로 뻗음 (오른쪽 대각선, 발 x 19–22) | 뒤로 뻗음 (왼쪽 대각선, 발 x 9–12) | 뒤로 흔듦 (손 x 7–9) | 앞으로 흔듦 (손 x 21–23) |
| walk1 | 120ms | -1 (몸 올라감) | 디딤 (곧게, x 13–15, 발 x 13–16) | 들어 올림 (x 15–17, 발이 y 41–43, 땅에서 2px 뜸) | 기본 -1 | 기본 -1 |
| walk2 | 120ms | 0 | 뒤로 뻗음 (발 x 9–12) | 앞으로 뻗음 (발 x 19–22) | 앞으로 흔듦 (몸통 위, 손 x 14–17) | 뒤로 흔듦 (몸통 왼쪽 뒤, 손 x 9–10) |
| walk3 | 120ms | -1 | 들어 올림 (발 y 41–43) | 디딤 (곧게, x 15–17, 발 x 15–18) | 기본 -1 | 기본 -1 |

walk0과 walk2의 다리 실루엣은 같은 "ㅅ" 모양이고, 어느 다리가 앞(가까운)인지만 바뀐다. 다리가 X자로 꼬이지 않도록 두 다리 모두 엉덩이 가운데(x 13–17)에서 시작한다.

#### 5.3.1 영역 지도 (정본, x 4–27 / y 24–45)

모든 파츠가 이 지도로 레이어를 맞춘다. 글자: `T` 몸통, `A` 앞팔 윗팔, `a` 앞팔 아래팔, `H` 앞손, `B` 뒷팔 윗팔, `b` 뒷팔 아래팔, `h` 뒷손, `L` 앞다리, `F` 앞발, `M` 뒷다리, `G` 뒷발, `.` 비어 있음. 겹치는 곳은 앞에 그리는 영역의 글자가 적혀 있다.
레이어 안 그리기 순서 (뒤 → 앞): `B b h` → `M G` → `T` → `L F` → `A a H`.
맨 위 줄 숫자는 x 좌표의 일의 자리 (첫 칸 = x 4).

```
idle0 (dy 0)                 idle1 (dy +1)                walk0 (dy 0)
   456789012345678901234567     456789012345678901234567     456789012345678901234567
24 ........................  24 ........................  24 ........................
25 ........TTTTTTT.........  25 ........................  25 ........TTTTTTT.........
26 ......AAATTTTTTTB.......  26 ........TTTTTTT.........  26 ......AAATTTTTTTB.......
27 ......AAATTTTTTTBB......  27 ......AAATTTTTTTB.......  27 .....AAATTTTTTTTBB......
28 ......AAATTTTTTTBB......  28 ......AAATTTTTTTBB......  28 .....AAATTTTTTTTBBB.....
29 ......aaaTTTTTTTbb......  29 ......AAATTTTTTTBB......  29 ....aaaTTTTTTTTT.bb.....
30 ......aaaTTTTTTTbb......  30 ......aaaTTTTTTTbb......  30 ....aaaTTTTTTTTT.bbb....
31 ......HHHTTTTTTThh......  31 ......aaaTTTTTTTbb......  31 ...HHH.TTTTTTTTT.hhh....
32 ......HHHTTTTTTThh......  32 ......HHHTTTTTTThh......  32 ...HHH.TTTTTTTTT..hh....
33 .......TTTTTTTTT........  33 ......HHHTTTTTTThh......  33 .......TTTTTTTTT........
34 ........LLL.MMM.........  34 .......TTTTTTTTT........  34 .........MMLLL..........
35 ........LLL.MMM.........  35 ........LLL.MMM.........  35 .........MMLLL..........
36 ........LLL.MMM.........  36 ........LLL.MMM.........  36 ........MMM.LLL.........
37 ........LLL.MMM.........  37 ........LLL.MMM.........  37 ........MMM.LLL.........
38 ........LLL.MMM.........  38 ........LLL.MMM.........  38 .......MMM...LLL........
39 ........LLL.MMM.........  39 ........LLL.MMM.........  39 .......MMM...LLL........
40 ........LLL.MMM.........  40 ........LLL.MMM.........  40 ......MMM.....LLL.......
41 ........LLL.MMM.........  41 ........LLL.MMM.........  41 ......MMM.....LLL.......
42 ........LLL.MMM.........  42 ........LLL.MMM.........  42 .....MMM.......LLL......
43 ........FFF.GGG.........  43 ........FFF.GGG.........  43 .....GGG.......FFF......
44 ........FFFFGGGG........  44 ........FFFFGGGG........  44 .....GGGG......FFFF.....
45 ........FFFFGGGG........  45 ........FFFFGGGG........  45 .....GGGG......FFFF.....

walk1 (dy -1)                walk2 (dy 0)                 walk3 (dy -1)
   456789012345678901234567     456789012345678901234567     456789012345678901234567
24 ........TTTTTTT.........  24 ........................  24 ........TTTTTTT.........
25 ......AAATTTTTTTB.......  25 ........TTTTTTT.........  25 ......AAATTTTTTTB.......
26 ......AAATTTTTTTBB......  26 .......AAATTTTTT........  26 ......AAATTTTTTTBB......
27 ......AAATTTTTTTBB......  27 ......BTAAATTTTT........  27 ......AAATTTTTTTBB......
28 ......aaaTTTTTTTbb......  28 ......BTTAAATTTT........  28 ......aaaTTTTTTTbb......
29 ......aaaTTTTTTTbb......  29 ......bTTaaaTTTT........  29 ......aaaTTTTTTTbb......
30 ......HHHTTTTTTThh......  30 .....hhTTTaaaTTT........  30 ......HHHTTTTTTThh......
31 ......HHHTTTTTTThh......  31 .....hhTTTHHHTTT........  31 ......HHHTTTTTTThh......
32 .......TTTTTTTTT........  32 .......TTTTHHHTT........  32 .......TTTTTTTTT........
33 .........LLLMM..........  33 .......TTTTTTTTT........  33 ........LLLMMM..........
34 .........LLLMM..........  34 .........LLLMM..........  34 ........LLLMMM..........
35 .........LLLMM..........  35 .........LLLMM..........  35 ........LLLMMM..........
36 .........LLLMM..........  36 ........LLL.MMM.........  36 ........LLLMMM..........
37 .........LLLMM..........  37 ........LLL.MMM.........  37 ........LLLMMM..........
38 .........LLLMM..........  38 .......LLL...MMM........  38 ........LLLMMM..........
39 .........LLLMM..........  39 .......LLL...MMM........  39 .........LLLMM..........
40 .........LLLMM..........  40 ......LLL.....MMM.......  40 .........LLLMM..........
41 .........LLLGG..........  41 ......LLL.....MMM.......  41 .........FFFMM..........
42 .........LLLGGG.........  42 .....LLL.......MMM......  42 .........FFFFM..........
43 .........FFFGGG.........  43 .....FFF.......GGG......  43 .........FFFFG..........
44 .........FFFF...........  44 .....FFFF......GGGG.....  44 ...........GGGG.........
45 .........FFFF...........  45 .....FFFF......GGGG.....  45 ...........GGGG.........
```

walk1의 뒷다리 `M`은 x 15–17, y 33–40이며 앞다리 뒤에 가려 x 16–17만 보인다. 뒷발 `G`는 y 41: x 15–17, y 42–43: x 15–18.
walk3의 앞다리 `L`은 y 33–38: x 12–14, y 39–40: x 13–15, 앞발 `F`는 y 41: x 13–15, y 42–43: x 13–16.

### 5.4 레이어 구성과 담당 범위

레이어 순서 (아래 → 위, 계약): `skin → bottom → top → eyes → hair`.

| 레이어 | 담당 | 금지 |
|---|---|---|
| `skin` | 두상, 얼굴, 귀, 입, 몸통 피부, 양팔, 양손, 양다리(맨다리), 발 영역 피부(신발 아래 숨음) | 눈, 눈썹, 볼터치 |
| `bottom` | 엉덩이(몸통 y 31–33 + dy), 바지/치마, 양발 신발 | 손(`H`, `h`) 픽셀, 머리 영역 |
| `top` | 몸통 천(y 25–32 + dy), 소매, 망토/후드 같은 장식 | 손(`H`, `h`), 소매가 아닌 팔 영역(짧은 소매의 `a`, `b`), 머리 영역(y ≤ 24 + dy) |
| `eyes` | 눈 2개, 눈썹 2개, 볼터치 | 눈 상자와 볼터치 좌표 밖 |
| `hair` | 앞머리, 정수리, 옆머리, 뒷머리 (어깨 뒤로 내려오는 부분 포함) | 눈 상자 (x 13–15, x 19–21, y 15–19, + dy). 머리 아래쪽(y ≥ 25 + dy)에서는 앞팔 영역(`A a H`) 픽셀 |

"금지" 픽셀은 투명으로 남긴다. 예: 짧은 소매 티셔츠의 아래팔(`a`)과 손(`H`)은 top에서 투명이므로 아래 skin이 보인다. 긴머리가 앞팔과 겹치면 hair에서 그 픽셀을 지운다 (팔이 머리카락 앞에 보인다).

#### 5.4.1 외곽선과 음영 자동 규칙 (모든 몸 파츠 공통)

아트 스크립트가 영역 지도에서 픽셀을 칠할 때 쓰는 규칙이다.

1. 한 레이어 안에서 영역 그룹을 뒤 → 앞 순서로 칠한다: 뒷팔(`B b h`) → 뒷다리(`M G`) → 몸통(`T`) → 앞다리(`L F`) → 앞팔(`A a H`).
2. 픽셀의 상하좌우 이웃 중 하나라도 "비어 있음" 또는 "더 뒤에 그린 그룹"이면 그 픽셀은 외곽선(line)이다. 같은 그룹이나 더 앞 그룹과 닿은 쪽은 외곽선을 넣지 않는다.
3. 외곽선이 아닌 픽셀은 기본(base). 단, skin 레이어의 먼 쪽 팔다리(`B b h M G`) 안쪽은 shade로 칠한다 (깊이감).
4. 머리 피부: 두상 실루엣의 바깥 테두리 1px가 line, 안쪽은 base. shade: x 8의 y 12–20 (뒤통수 쪽 세로줄), (9,21), (10,22), (11,22), (11,23), 귀 (10,16) (11,16) (10,17) (10,18) (11,18). 모두 + dy.

### 5.5 skin 파츠

#### 5.5.1 skin 레이어 격자 (`skin-light`, idle0, 정본)

글자: `O` line, `s` base, `d` shade. 다른 피부는 램프만 바꾼다 (1.2절). 다른 프레임은 머리(y 8–24)를 dy만큼 옮기고, 몸(y 25 이하)은 5.3.1 영역 지도와 5.4.1 규칙으로 만든다.

```
   456789012345678901234567
 8 .......OOOOOOOOOO.......
 9 .....OOssssssssssOO.....
10 ....OssssssssssssssO....
11 ...OssssssssssssssssO...
12 ...OdsssssssssssssssO...
13 ...OdsssssssssssssssO...
14 ...OdsssssssssssssssO...
15 ...OdsssssssssssssssO...
16 ...OdsddssssssssssssO...
17 ...OdsdOssssssssssssO...
18 ...OdsddssssssssssssO...
19 ...OdsssssssssssssssO...
20 ...OdsssssssssssssssO...
21 ....OdssssssssssssssO...
22 .....OddssssssOOsssO....
23 ......OdssssssssssO.....
24 ........OOOOOOOOOO......
25 ........OOOOOOO.........
26 ......OOOssssssOO.......
27 ......OsOssssssOdO......
28 ......OsOssssssOdO......
29 ......OsOssssssOdO......
30 ......OsOssssssOdO......
31 ......OsOssssssOdO......
32 ......OOOssssssOOO......
33 .......OsssOOOOO........
34 ........OOO.OdO.........
35 ........OsO.OdO.........
36 ........OsO.OdO.........
37 ........OsO.OdO.........
38 ........OsO.OdO.........
39 ........OsO.OdO.........
40 ........OsO.OdO.........
41 ........OsO.OdO.........
42 ........OsO.OdO.........
43 ........OsO.OdO.........
44 ........OssOdddO........
45 ........OOOOOOOO........
```

두상 행별 범위 (외곽선 포함, + dy): y 8: x 11–20 / y 9: 9–22 / y 10: 8–23 / y 11–20: 7–24 / y 21: 8–24 / y 22: 9–23 / y 23: 10–22 / y 24: 12–21.
머리는 몸통보다 나중에 그린다 (턱이 목을 덮는다).

#### 5.5.2 skin 목록

| id | label | base / shade / line |
|---|---|---|
| `skin-light` | 밝은 피부 | `s1` / `s2` / `w2` |
| `skin-tan` | 보통 피부 | `s2` / `s3` / `w3` |
| `skin-dark` | 진한 피부 | `w2` / `w3` / `w4` |

### 5.6 eyes 파츠

#### 5.6.1 눈 격자 (눈 상자 안, idle0 y 15–19, + dy)

글자: `W` 눈썹 `w4`, `K` 눈동자 `ink`, `N` 눈빛 `white`, `U` 홍채 `u2`, `.` 투명. 뒷눈 상자 x 13–15, 앞눈 상자 x 19–21. 각 줄 왼쪽 글자가 상자의 첫 열.

| id | label | 뒷눈 (y15 → y19) | 앞눈 (y15 → y19) | 볼터치 (`p2`) |
|---|---|---|---|---|
| `eyes-dot` | 기본 눈 | `.WW` `.KK` `.KN` `.KK` `.UU` | `WW.` `KK.` `KN.` `KK.` `UU.` | (13,21) (21,21) (22,21) |
| `eyes-happy` | 웃는 눈 | `.WW` `...` `.K.` `K.K` `...` | `WW.` `...` `.K.` `K.K` `...` | (12,21) (13,21) (21,21) (22,21) |
| `eyes-sleepy` | 졸린 눈 | `...` `.WW` `...` `KKK` `.UU` | `...` `WW.` `...` `KKK` `UU.` | (13,21) (21,21) (22,21) |
| `eyes-sparkle` | 반짝 눈 | `.WW` `.KK` `.KN` `.NK` `.UU` | `WWW` `KKK` `KNK` `KKN` `UUU` | (13,21) (21,21) (22,21) |

- 기본 눈: 세로 2x4 눈, 오른쪽 위 눈빛 1px, 아래 홍채 줄. 눈빛이 두 눈 모두 오른쪽(얼굴이 향한 쪽)에 있다.
- 웃는 눈: `^ ^` 모양. 볼터치가 1px 넓다.
- 졸린 눈: 눈썹이 1줄 내려오고(y 16), 눈꺼풀 선 3px(y 18) 아래 홍채만 보인다.
- 반짝 눈: 앞눈이 3px 폭으로 크고 눈빛이 2개다.
- 눈썹 색은 머리색과 관계없이 `w4`.

### 5.7 hair 파츠

#### 5.7.1 머리 모양 격자 (idle0, 정본, + dy)

글자: `O` line, `b` base, `h` hl. 색은 1.2절 머리 램프를 적용한다. 바깥 테두리는 line, 앞머리 가닥 사이 선(`O`)은 손으로 넣은 선이다.
지켜야 할 경계: 눈 상자(x 13–15, 19–21, y 15–19)에 픽셀이 없어야 한다. 앞머리 끝(y 15)은 눈 사이 x 16–18 또는 x 22 이상에만 내려온다.

단발 `round` (x 3–28, y 1–22)
```
   34567890123456789012345678
 4 ........OOOOOOOOO.........
 5 ......OObbbbbbbbbOO.......
 6 ....OObbbbhhhhhbbbbOO.....
 7 ...ObbbbbhhhhhhhbbbbbO....
 8 ..ObbbbbbbbbbbbbbbbbbbO...
 9 ..ObbbbbbbbbbbbbbbbbbbO...
10 ..ObbbbbbbbbbbbbbbbbbbO...
11 ..ObbbbbbbbbbbbbbbbbbbO...
12 ..ObbbbbbbbbOObbbbObbbbO..
13 ..ObbbbbbbbObbbbbbbbObbO..
14 ..ObbbbbbOO.OOOOOObO.ObO..
15 ..ObbbbbO.........O...OO..
16 ..ObbbbbO.............OO..
17 ..ObbbbbO.............OO..
18 ..ObbbbbO.............O...
19 ..ObbbbO..................
20 ..ObbbbO..................
21 ...ObbbO..................
22 ....OOO...................
```
턱선까지 오는 단발. 뒷머리가 귀를 덮고(y 22까지), 앞쪽 옆머리는 x 25–26 가는 줄로 y 18까지.

뾰족 `spiky` (x 3–28, y 1–17)
```
   34567890123456789012345678
 2 .......O......O...........
 3 .......OO....ObO....O.....
 4 .......ObO..ObbbO..OO.....
 5 ......ObbbOObbbbbOObO.....
 6 ...OOObbbbhhhhhbbbbbbO....
 7 ..ObbbbbbhhhhhhhbbbbbbOO..
 8 .ObbbbbbbbbbbbbbbbbbbbbbOO
 9 ..ObbbbbbbbbbbbbbbbbbbbbO.
10 ..ObbbbbbbbbbbbbbbbbbbbbbO
11 .ObbbbbbbbbbbbbbbbbbbbbbO.
12 ..ObbbbbbbbbbbbbbbbbbbbbbO
13 ...ObbbbbObbbObbbbObbbbbO.
14 ..ObbbbbO.ObO.ObOO.OObbO..
15 ...ObbbO...O...O.....OO...
16 ...ObbO..............O....
17 ....OOO...................
```
정수리에 뾰족한 끝 3개(x 10, 17, 23 부근, y 2–4), 좌우로 삐친 끝(y 8, 10, 12의 바깥 1px). 뒷머리가 짧아 귀(x 10–11, y 16–18) 일부가 보인다.

긴머리 `long` (x 3–28, y 1–29)
```
   34567890123456789012345678
 4 ........OOOOOOOOO.........
 5 ......OObbbbbbbbbOO.......
 6 ....OObbbbhhhhhbbbbOO.....
 7 ...ObbbbbhhhhhhhbbbbbO....
 8 ..ObbbbbbbbbbbbbbbbbbbO...
 9 ..ObbbbbbbbbbbbbbbbbbbO...
10 .ObbbbbbbbbbbbbbbbbbbbbO..
11 .ObbbbbbbbbbbbbbbbbbbbbO..
12 .ObbbbbbbbbbbbbbbbbbbbbbO.
13 .ObbbbbbbbbObbbbbbbbbObbO.
14 .ObbbbbbbOO.OOOOOObOO.ObO.
15 .ObbbbbbO.........O...ObO.
16 .ObbbbbbO.............ObO.
17 .ObbbbbbO.............ObO.
18 .ObbbbbO..............ObO.
19 .ObbbbbO..............ObO.
20 .ObbbbbO..............ObO.
21 .ObbbbbO...............OO.
22 .ObbbbbO..................
23 .ObbbbbO..................
24 .ObbbbbO..................
25 .ObbbbbO..................
26 .ObbbbO...................
27 .ObbbbO...................
28 ..ObObO...................
29 ..OO.OO...................
```
등 뒤로 y 29까지 내려오는 생머리 (끝이 두 갈래). 앞쪽 옆머리 x 25–27, y 21까지. 앞팔과 겹치는 픽셀(walk0의 x 7–10 등)은 지운다 (5.4절).

#### 5.7.2 hair 목록 (7종 = 모양 3 x 색 조합)

| id | label | 모양 | 색 |
|---|---|---|---|
| `hair-round-black` | 단발 · 흑발 | round | black |
| `hair-round-chestnut` | 단발 · 밤색 | round | chestnut |
| `hair-spiky-black` | 뾰족 · 흑발 | spiky | black |
| `hair-spiky-chestnut` | 뾰족 · 밤색 | spiky | chestnut |
| `hair-spiky-mint` | 뾰족 · 민트 | spiky | mint |
| `hair-long-pink` | 긴머리 · 분홍 | long | pink |
| `hair-long-blonde` | 긴머리 · 금발 | long | blonde |

같은 모양은 격자가 같고 램프만 다르다. 새 색 조합을 추가할 때는 이 표에 id를 먼저 추가한다.

### 5.8 top 파츠

#### 5.8.1 공통 규칙

- 몸통 천 = 영역 `T` 중 y ≤ 32 + dy. (`T`의 마지막 줄 33 + dy는 하의 허리)
- 짧은 소매 = `A`, `B`. 긴 소매 = `A a`, `B b`. 손 `H h`는 칠하지 않는다.
- 그룹 순서 뒷소매 → 몸통 → 앞소매, 외곽선은 5.4.1 규칙 2 (원단 램프의 line).
- 어깨 하이라이트: x 13–17, y 26 + dy를 원단 hl로.
- 머리 영역(y ≤ 24 + dy)에 칠하지 않는다.

#### 5.8.2 top 목록

| id | label | 원단 | 모양 (도트 단위, + dy) |
|---|---|---|---|
| `top-tee-red` | 빨간 티셔츠 | red | 짧은 소매. 공통 규칙 그대로 |
| `top-hoodie-blue` | 파란 후드티 | blue | 긴 소매. 후드 접힘 y 25: x 11 `u3`, x 12–13 `u1`, x 14 `u3`. 앞주머니 선 y 30, x 14–18 `u3`. 후드 끈 (17,26) (17,27) `white` |
| `top-overalls-blue` | 파란 멜빵 | cream 셔츠 + blue 멜빵 | 셔츠는 cream 짧은 소매. 가슴판 x 13–18, y 29–31 `u2`, y 32 `u3`. 멜빵 끈 x 14와 x 18, y 25–28 `u3`. 단추 (14,29) (18,29) `y2` |
| `top-cape-mushroom` | 버섯 망토 | cream 셔츠 + red 망토 | 셔츠는 cream 긴 소매. 망토(어깨를 덮는 짧은 케이프) 행별 범위: y 25: x 10–20 / y 26: 9–21 / y 27: 8–22 / y 28: 8–22 / y 29: 8–22 중 짝수 x만 (물결 끝단). 망토는 `a H h b` 픽셀을 칠하지 않는다. red 램프, 외곽선 규칙은 단독 실루엣 기준. 흰 점 `c1`: (9,28) (11,26) (13,28) (15,25) (17,27) (19,26) (21,28) 중 망토 안쪽 픽셀만. 여밈 단추 (15,30) `y2` |

후드 모자 자체는 머리 뒤에 그려야 하지만 레이어 순서상 불가능하므로(top은 skin 위, hair 아래) 목 뒤 접힘으로만 표현한다.

### 5.9 bottom 파츠

#### 5.9.1 공통 규칙

- 엉덩이 = 영역 `T` 중 y ≥ 31 + dy (31–32는 상의에 덮이고 y 33 + dy만 보인다).
- 다리 덮개 = 각 다리(`L`, `M`)의 맨 위 줄부터 n줄 (각 다리 자신의 첫 줄 기준이라 프레임마다 위치가 따라간다).
- 그룹 순서 뒷다리 → 엉덩이 → 앞다리, 외곽선 규칙 동일.
- 신발 = `F`, `G` 전체. 그룹 순서 `G` → `F`. 신발 램프 (갈색 기본, 치마만 빨강).
- 손 `H h` 픽셀은 칠하지 않는다 (idle1의 손 y 32–33이 엉덩이와 겹친다).

#### 5.9.2 bottom 목록

| id | label | 원단 / 신발 | 모양 (+ dy) |
|---|---|---|---|
| `bottom-shorts-navy` | 네이비 반바지 | navy / 갈색 | 엉덩이 + 다리 위 4줄 |
| `bottom-jeans-blue` | 청바지 | blue / 갈색 | 엉덩이 + 다리 전체 (y 42까지). 신발 바로 위까지 |
| `bottom-skirt-pink` | 분홍 치마 | pink / 빨강 | 다리와 무관한 사다리꼴. 행별: y 31–32: x 11–19 / y 33–34: x 10–20 / y 35–36: x 9–21. 주름 `p3` (12,34) (15,34) (18,34) (12,35) (15,35) (18,35). 걷기에서도 모양 고정 (dy만 적용) |
| `bottom-pumpkin-green` | 초록 호박바지 | green / 갈색 | 엉덩이 + 다리 위 3줄, 각 다리 덮개를 좌우 1px씩 넓힌다 (부푼 모양) |

### 5.10 기본 조합, 순서, 예전 id 처리

기본 조합 (사이클 1과 같음):

```json
{ "skin": "skin-light", "hair": "hair-round-black", "eyes": "eyes-dot", "top": "top-tee-red", "bottom": "bottom-shorts-navy" }
```

매니페스트 `parts` 순서 = 캐릭터 생성 화면 좌/우 순서 (첫 항목이 기본값):

- skin: `skin-light`, `skin-tan`, `skin-dark`
- hair: `hair-round-black`, `hair-round-chestnut`, `hair-spiky-black`, `hair-spiky-chestnut`, `hair-spiky-mint`, `hair-long-pink`, `hair-long-blonde`
- eyes: `eyes-dot`, `eyes-happy`, `eyes-sleepy`, `eyes-sparkle`
- top: `top-tee-red`, `top-hoodie-blue`, `top-overalls-blue`, `top-cape-mushroom`
- bottom: `bottom-shorts-navy`, `bottom-jeans-blue`, `bottom-skirt-pink`, `bottom-pumpkin-green`

사이클 1 id 호환 (저장된 캐릭터 대비, DB 변경 없음). 프런트가 읽을 때 바꿔서 그린다. 저장 값은 고치지 않는다.

| 예전 id | 새 id |
|---|---|
| `eyes-round` | `eyes-sparkle` |
| `top-vest-green` | `top-overalls-blue` |
| 그 밖에 목록에 없는 id | 해당 part의 기본값 (첫 항목) |

나머지 사이클 1 id(`skin-*`, `hair-round-*`, `hair-spiky-*`, `eyes-dot`, `eyes-happy`, `top-tee-red`, `top-hoodie-blue`, `bottom-*` 3종)는 그대로 유지된다.

### 5.11 애니메이션

| 상태 | 프레임 | 프레임당 | 한 바퀴 |
|---|---|---|---|
| 대기 `idle` | 0, 1 | 500ms | 1000ms |
| 걷기 `walk` | 2, 3, 4, 5 | 120ms | 480ms |

- 이동 중이면 walk, 아니면 idle. 상태가 바뀌는 순간 해당 애니메이션의 첫 프레임부터 시작한다 (walk는 walk0).
- 다른 사용자: 마지막 `move` 수신 후 200ms 안에 위치가 바뀌고 있으면 walk, 아니면 idle. 방향은 `dir`.
- 같은 화면의 여러 아바타가 똑같이 숨 쉬지 않도록 idle 시작 시각에 user_id 기반 0~499ms 오프셋을 준다.
- `prefers-reduced-motion: reduce`: 게임 안 애니메이션은 유지한다 (이동 표현에 필요). 캐릭터 생성 미리보기와 로그인 배경 자동 이동만 멈춘다.
- 성능 권장: 아바타 조합마다 5개 레이어를 한 번 합성해 192x48 시트로 캐시하고, 좌우 반전 시트도 캐시한다.

---

## 6. 맵 (아트 좌표 1200 x 270, 지면 y 220)

### 6.1 레이어 목록 (`assets/map/manifest.json`, 앞에 적힌 것부터 그린다)

| 순서 | 파일 | 크기 (아트 px) | y | parallax | repeatX | 내용 |
|---|---|---|---|---|---|---|
| 1 | `sky.png` | 16 x 270 | 0 | 0.0 | true | 하늘 밴드 5단 (디더링 없음) |
| 2 | `clouds.png` | 480 x 70 | 18 | 0.25 | true | 구름 4덩이 |
| 3 | `mountains.png` | 640 x 110 | 110 | 0.2 | true | 먼 산 (`m1`) |
| 4 | `hills.png` | 640 x 80 | 142 | 0.3 | true | 가까운 언덕 (`m2`) |
| 5 | `trees.png` | 640 x 120 | 104 | 0.5 | true | 중경 나무 7그루 + 덤불 띠 |
| 6 | `village.png` | 1200 x 160 | 60 | 1.0 | false | 버섯 집 4채, 울타리 3구간, 표지판, 꽃 |
| 7 | `ground.png` | 1200 x 54 | 216 | 1.0 | false | 지면 타일 (16 x 16 격자) |

```json
{ "scale": 2, "layers": [
  { "src": "assets/map/sky.png",       "parallax": 0.0,  "y": 0,   "repeatX": true },
  { "src": "assets/map/clouds.png",    "parallax": 0.25, "y": 18,  "repeatX": true },
  { "src": "assets/map/mountains.png", "parallax": 0.2,  "y": 110, "repeatX": true },
  { "src": "assets/map/hills.png",     "parallax": 0.3,  "y": 142, "repeatX": true },
  { "src": "assets/map/trees.png",     "parallax": 0.5,  "y": 104, "repeatX": true },
  { "src": "assets/map/village.png",   "parallax": 1.0,  "y": 60,  "repeatX": false },
  { "src": "assets/map/ground.png",    "parallax": 1.0,  "y": 216, "repeatX": false }
] }
```

- repeatX 레이어는 왼쪽 끝과 오른쪽 끝이 이어지게 그린다 (이음매 없음).
- 반복 레이어의 아래 끝은 지면(216 이상) 뒤에 숨는다: 산 110+110=220, 언덕 142+80=222, 나무 104+120=224.
- 마을 레이어의 아래 끝은 y 220 (소품의 맨 아래 불투명 줄 = y 219 = 이미지 행 159). 지면 레이어의 풀잎(y 216–219)이 소품 밑동 앞에 겹친다.

### 6.2 하늘 `sky.png`

| 밴드 | 색 | y 범위 |
|---|---|---|
| 1 | `k1` | 0–59 |
| 2 | `k2` | 60–104 |
| 3 | `k3` | 105–139 |
| 4 | `k4` | 140–169 |
| 5 | `k5` | 170–269 |

밴드는 아래로 갈수록 좁아지다가 지평선(5)에서 넓다. 경계에 디더링, 중간색을 넣지 않는다. y < 0(카메라가 위로 넓을 때)은 프런트가 `k1`로 채운다.

### 6.3 원경

- 구름 `clouds.png`: 덩어리 4개 (가로 28, 32, 48, 60 정도). 원 5개를 합친 뭉게 모양, 아랫면은 평평. 몸통 `white`, 맨 아랫줄 `k4`, 그 위 2줄 `k5`. 외곽선 없음.
- 먼 산 `mountains.png`: 부드러운 봉우리 5개 (높이 45–85, 가장 높은 봉우리가 이미지 위 끝 근처). 채움 `m1`, 능선 맨 윗줄 1px `white`.
- 언덕 `hills.png`: 완만한 언덕 4개 (높이 28–48). 채움 `m2`, 능선 맨 윗줄 1px `m1`.

### 6.4 중경 나무 `trees.png`

- 나무 7그루, 가로 중심 x 40, 130, 175, 300, 420, 520, 600, 잎 반지름 14–24. 밑동 y 112 (이미지 기준).
- 줄기: 폭 5, `w3` 채움, 왼쪽 둘째 열 `w2`, 양 끝 `w4`. 높이 = 잎 반지름.
- 잎: 원 3개 (가운데 r, 좌우 0.7r을 아래로 r/3 내림)의 합집합. 외곽 `g4`, 채움 `g3`, 왼쪽 위 영역 `g2`, 왼쪽 위 끝 `g1` 하이라이트.
- 아래 덤불 띠: 높이 6–11 물결, `g3` 채움, 윗줄 `g4`.

### 6.5 근경 마을 `village.png` (1200 x 160, 이미지 행 159 = 아트 y 219)

배치 (가로 중심, 아트 x):

| 소품 | x | 크기 |
|---|---|---|
| 버섯 집 A (빨강, 큰 집) | 130 | 갓 80 x 40, 기둥 44 x 44 |
| 울타리 1 | 200–245 | 말뚝 8개 |
| 버섯 집 B (주황) | 440 | 갓 66 x 33, 기둥 36 x 36 |
| 울타리 2 | 520–553 | 말뚝 6개 |
| 표지판 | 600 | 판 29 x 14, 기둥 높이 22 |
| 버섯 집 C (파랑) | 790 | 갓 76 x 38, 기둥 42 x 42 |
| 울타리 3 | 880–931 | 말뚝 9개 |
| 버섯 집 D (빨강, 작은 집) | 1060 | 갓 58 x 29, 기둥 32 x 32 |
| 꽃 15송이 | 20, 26, 250, 258, 300, 380, 386, 560, 640, 700, 706, 940, 990, 1150, 1156 | 3 x 4 |

버섯 집 디자인 (모든 집 공통, 크기만 다름):

| 부분 | 규칙 |
|---|---|
| 기둥(벽) | 위 폭 = 기둥 폭, 아래로 갈수록 양쪽 3px까지 넓어지는 종 모양 (넓어짐 = 3 x t², t = 0 위 → 1 아래). 채움 `c1`, 왼쪽 2열 `c2`, 오른쪽 2열 `c2`/`c3`(바깥 `c3`), 외곽 `w3`, 맨 아랫줄 `w3` (기둥보다 3px 넓게) |
| 갓 | 반타원 돔 (가로 = 갓 폭, 높이 = 폭/2). 갓 아랫선 = 기둥 윗선 + 4 (기둥 위를 덮는다). 챙 처짐: 중심에서 반폭의 55% 바깥은 1줄, 80% 바깥은 2줄 더 내려온다. 외곽 line, 채움 base, 맨 아래 2줄 line (갓 그늘) |
| 갓 하이라이트 | 갓 위쪽 3–4번째 줄, 중심 왼쪽(반폭의 -55% ~ -10%)에 hl 2줄 (외곽에서 3px 안쪽) |
| 갓 점 무늬 | 원 6개 (반지름 2–5), 갓 안쪽에만 (외곽선 위에 그리지 않음). 원의 위쪽 `c1`, 아래 1/2 `c2`. 위치(반폭 a, 갓 높이 b 비율, 중심 기준): (-0.55a, 0.35b) r4 / (-0.15a, 0.7b) r3 / (0.25a, 0.4b) r5 / (0.62a, 0.25b) r3 / (-0.35a, 0.12b) r2 / (0.05a, 0.15b) r3 |
| 주름 | 갓 바로 아래 1줄, 기둥 폭만큼 `c3` |
| 문 | 아치형 14 x 22, 왼쪽 끝 = 기둥 중심 -12, 아래 끝 = 이미지 행 157 (아트 y 217). 채움 `w2`, 판자선 `w3` (문 왼쪽 +5, +9 열, 아치 아래부터), 외곽 `w4`, 위 3줄은 계단식 아치 (안쪽으로 3, 1, 1px). 손잡이 (문 왼쪽 +10, 아래 끝 -9) `y2`, 그 오른쪽 1px `y4` |
| 디딤돌 | 문 바로 아래 16 x 2 (문 왼쪽 -1 ~ 문 오른쪽 +1), 이미지 행 158 `st1`, 행 159 `st2` |
| 창문 | 둥근 창 10 x 10, 위치 (기둥 중심 +10, 기둥 위 +12). 유리 `y1` (불 켜진 창), 틀과 십자 `w3`, 반짝임 (2,2) (7,7) `y2` |
| 굴뚝 | 8 x 16, 갓 중심 + 반폭 x 0.45, 위 끝 = 갓 꼭대기 + 2. 갓보다 먼저 그린다 (갓 뒤에서 솟음). 채움 `st1`, 오른쪽 2열 `st2`, 외곽 `hb1`, 맨 위 테 10 x 2 (`hb1` + `st2`) |
| 연기 | 굴뚝 위 원 2개 (r3, r4), 위로 갈수록 오른쪽. `c1`, 맨 아랫줄 `c2`. 정지 이미지 |

- 갓 색: A, D 빨강 / B 주황 / C 파랑 (1.2절 갓 램프).
- 울타리: 말뚝 폭 3 (6px 간격), 높이 12 + 뾰족 끝 1px. 채움 `w2`, 양쪽 `w4`, 끝 아래 1px `w1`. 가로대 2개 (바닥 -9, 바닥 -4), 각 `w3` 1줄 + 아래 `w4` 1줄.
- 표지판: 기둥 3 x 22 (`w3`, 양쪽 `w4`), 판 29 x 14 (`w2`, 윗줄 안쪽 `w1`, 아랫줄 안쪽 `w3`, 외곽 `w4`). 판 가운데 빨간 버섯 문양 (갓 `r2` 4줄 + 점 `c1` 2개 + 기둥 `c1` 3x3). 글자는 넣지 않는다 (픽셀 한글 폰트 없음).
- 꽃: 꽃잎 십자 (위, 좌, 우 1px + 가운데), 색 순서 `r2`, `y2`, `p2`, `white` 반복, 가운데 `y2` (노란 꽃은 `y4`). 줄기 2px `g3`.

### 6.6 지면 `ground.png` (1200 x 54, y 216, 16 x 16 타일)

| 이미지 행 | 아트 y | 타일 |
|---|---|---|
| 0–19 | 216–235 | `grass-top` 16 x 20 (위 4줄은 풀잎이 튀어나오는 투명 영역) |
| 20–35 | 236–251 | `dirt` 16 x 16 |
| 36–51 | 252–267 | `dirt-stone` 16 x 16 |
| 52–53 | 268–269 | `w3` 채움 |

- `grass-top`: 행 0–3 풀잎 (타일마다 3px 높이 잎 2개, 끝 1px `g1` 또는 `g2`, 1px 잎 3개 `g2`), 행 4 `g1` (잔디 윗면, 아바타 발이 닿는 줄 = 아트 y 220), 행 5–9 `g2`, 행 10 `g3`, 행 11은 3px 묶음마다 번갈아 `g3`/`g4`로 물결 끝단, 그 아래 1줄 `g4`, 나머지 `w3`.
- `dirt`: `w3` 바탕에 `w4` 2x1 반점 4개, `w2` 1px 반점 2개.
- `dirt-stone`: `dirt` + 돌 1개 (5 x 4 둥근 덩어리 `st2`, 왼쪽 위 3px `st1`, 아래 3px `hb1` 그림자). 돌 위치는 타일마다 두 가지(왼쪽 위 / 오른쪽 아래)를 번갈아 써서 줄무늬처럼 보이지 않게 한다.
- 세로 경계에서 타일이 이어져야 한다 (무늬가 타일 경계에서 끊기지 않음).

참고 시안: `ref/map-draft.png` (960 x 540, P=2), `ref/world-1x.png` (전체 1200 x 270 1배).

---

## 7. UI 스킨 (`assets/ui/`, U = 2)

### 7.1 파일 목록과 9-slice 값

DOM은 CSS `border-image`로, Canvas는 직접 9-slice로 그린다. CSS `border-image`는 시트의 일부를 잘라 쓸 수 없으므로 상태마다 파일을 나눈다.

| 파일 | 크기 | slice (위 오른 아래 왼) | 화면 테두리 두께 | 용도 |
|---|---|---|---|---|
| `panel.png` | 24 x 24 | 8 8 8 8 | 16px | 로그인/생성 카드, 배너 |
| `button-primary-normal.png` | 24 x 24 | 8 8 8 8 | 16px | 주 버튼 기본 |
| `button-primary-hover.png` | 24 x 24 | 8 8 8 8 | 16px | 주 버튼 호버 |
| `button-primary-pressed.png` | 24 x 24 | 8 8 8 8 | 16px | 주 버튼 눌림, 활성 탭 |
| `button-primary-disabled.png` | 24 x 24 | 8 8 8 8 | 16px | 비활성 (주/보조 공용) |
| `button-secondary-normal.png` | 24 x 24 | 8 8 8 8 | 16px | 보조 버튼, 비활성 탭, ◀ ▶, 터치 버튼, 로그아웃 |
| `button-secondary-hover.png` | 24 x 24 | 8 8 8 8 | 16px | |
| `button-secondary-pressed.png` | 24 x 24 | 8 8 8 8 | 16px | |
| `input-normal.png` | 12 x 12 | 4 4 4 4 | 8px | 입력창 |
| `input-focus.png` | 12 x 12 | 4 4 4 4 | 8px | 입력창 포커스 |
| `input-error.png` | 12 x 12 | 4 4 4 4 | 8px | 입력창 오류 |
| `input-disabled.png` | 12 x 12 | 4 4 4 4 | 8px | 입력창 비활성 |
| `chip.png` | 8 x 8 | 3 3 3 3 | 6px | 접속자 배지, 조작 힌트, 쿨다운 힌트, 정보 배너 |
| `bubble.png` | 12 x 12 | 4 4 4 4 | 8px | 말풍선 몸통 (Canvas) |
| `bubble-tail.png` | 8 x 4 | - | 16 x 8px | 말풍선 꼬리 (Canvas) |
| `label-other.png` | 8 x 8 | 3 3 3 3 | 6px | 다른 사람 닉네임 (Canvas) |
| `label-self.png` | 8 x 8 | 3 3 3 3 | 6px | 내 닉네임 (Canvas) |
| `icon-mushroom.png` | 9 x 8 | - | 18 x 16px | 접속자 배지 아이콘, 로고 옆 |
| `icon-arrow.png` | 4 x 7 | - | 8 x 14px | ▶ (왼쪽은 CSS `scaleX(-1)`) |

`assets/ui/manifest.json` 형식 (ARCHITECTURE "슬라이스 값은 manifest에"):

```json
{ "scale": 2,
  "nine": {
    "panel":            { "src": "assets/ui/panel.png", "slice": [8,8,8,8] },
    "button-primary":   { "states": { "normal": "assets/ui/button-primary-normal.png", "hover": "assets/ui/button-primary-hover.png", "pressed": "assets/ui/button-primary-pressed.png", "disabled": "assets/ui/button-primary-disabled.png" }, "slice": [8,8,8,8], "pressedShift": 2 },
    "button-secondary": { "states": { "normal": "...", "hover": "...", "pressed": "...", "disabled": "assets/ui/button-primary-disabled.png" }, "slice": [8,8,8,8], "pressedShift": 2 },
    "input":            { "states": { "normal": "...", "focus": "...", "error": "...", "disabled": "..." }, "slice": [4,4,4,4] },
    "chip":             { "src": "assets/ui/chip.png", "slice": [3,3,3,3] },
    "bubble":           { "src": "assets/ui/bubble.png", "slice": [4,4,4,4] },
    "label-other":      { "src": "assets/ui/label-other.png", "slice": [3,3,3,3] },
    "label-self":       { "src": "assets/ui/label-self.png", "slice": [3,3,3,3] }
  },
  "sprites": { "bubble-tail": "assets/ui/bubble-tail.png", "icon-mushroom": "assets/ui/icon-mushroom.png", "icon-arrow": "assets/ui/icon-arrow.png" } }
```

`pressedShift`: 눌림 스킨은 윗면이 2 아트 px 내려와 있으므로 글자도 4 CSS px 아래로 옮긴다.

### 7.2 패널 `panel.png` (24 x 24, 정본)

글자: `D` `w4`, `h` `w1`, `w` `w2`, `m` `w3`, `c` `c2`, `f` `c1`, `y` `y2` (못), `.` 투명.

```
..DDDDDDDDDDDDDDDDDDDD..
.DhhhhhhhhhhhhhhhhhhhhD.
DhwwwwwwwwwwwwwwwwwwwwmD
DhwywwwwwwwwwwwwwwwwywmD
DhwwmmmmmmmmmmmmmmmmwwmD
DhwwmDDDDDDDDDDDDDDmwwmD
DhwwmDcccccccccccfDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDcfffffffffffDmwwmD
DhwwmDffffffffffffDmwwmD
DhwwmDDDDDDDDDDDDDDmwwmD
DhwwmmmmmmmmmmmmmmmmwwmD
DhwywwwwwwwwwwwwwwwwywmD
DhwwwwwwwwwwwwwwwwwwwwmD
.DmmmmmmmmmmmmmmmmmmmmD.
..DDDDDDDDDDDDDDDDDDDD..
```

나무 테두리(바깥 외곽 `w4`, 위/왼쪽 하이라이트 `w1`, 아래/오른쪽 그늘 `w3`, 나무 `w2` 2줄, 안쪽 홈 `w3` + `w4`) 안에 크림 바탕(`c1`, 위/왼쪽 안쪽 그림자 `c2` 1줄). 네 모서리에 노란 못 `y2`.
가운데(행/열 8–15)는 단색 `c1`이라 늘려도 깨지지 않는다.

CSS:
```css
.px-panel { border: 16px solid transparent; border-image: url(assets/ui/panel.png) 8 fill / 16px / 0 stretch; image-rendering: pixelated; padding: 8px; }
```

### 7.3 버튼 (24 x 24, 정본 틀)

틀 (기본/호버/비활성): 글자 `L` line, `H` hl, `B` body, `D` low, `P` lip, `.` 투명.
```
행 0      .LLLLLLLLLLLLLLLLLLLLLL.
행 1      LHHHHHHHHHHHHHHHHHHHHHHL
행 2–17   LBBBBBBBBBBBBBBBBBBBBBBL
행 18–20  LDDDDDDDDDDDDDDDDDDDDDDL
행 21–22  LPPPPPPPPPPPPPPPPPPPPPPL
행 23     .LLLLLLLLLLLLLLLLLLLLLL.
```
눌림 틀: 윗면이 2줄 내려오고 립이 없다.
```
행 0–1    ........................ (투명)
행 2      .LLLLLLLLLLLLLLLLLLLLLL.
행 3      LPPPPPPPPPPPPPPPPPPPPPPL   (안쪽 위 그림자, lip 색)
행 4–20   LBBBBBBBBBBBBBBBBBBBBBBL
행 21–22  LDDDDDDDDDDDDDDDDDDDDDDL
행 23     .LLLLLLLLLLLLLLLLLLLLLL.
```

| 스킨 | L | H | B | D | P | 글자 |
|---|---|---|---|---|---|---|
| primary normal | `w4` | `y1` | `y2` | `y3` | `y4` | `ink` + `white` 그림자 (0,+1) |
| primary hover | `w4` | `white` | `y1` | `y2` | `y4` | `ink`, 그림자 없음 |
| primary pressed | `w4` | - | `y2` | `y3` | `y4` | `ink`, 4px 아래로 |
| secondary normal | `w3` | `white` | `c1` | `c2` | `c3` | `ink` + `white` 그림자 |
| secondary hover | `w3` | `white` | `white` | `c1` | `c3` | `ink` |
| secondary pressed | `w3` | - | `c1` | `c2` | `c3` | `ink`, 4px 아래로 |
| disabled (공용) | `c3` | `c1` | `c2` | `c2` | `c3` | `--text-muted` (`w3`), 그림자 없음 |

- 높이 48px 버튼 = 위 16 + 가운데 16 + 아래 16. 40px(탭) = 16 + 8 + 16. 56px(터치) = 16 + 24 + 16. 32px(로그아웃 작은 버튼) = 16 + 0 + 16.
- 글자는 위아래 테두리 사이 가운데가 아니라 "립을 뺀 윗면" 가운데에 둔다: 기본/호버는 `padding-bottom: 4px`, 눌림은 `padding-top: 4px`.
- 시안: `ref/buttons-8x.png` (윗줄 primary 4상태, 아랫줄 secondary).

### 7.4 입력창 (12 x 12, 정본)

```
normal            focus             error             disabled
..OOOOOOOO..      ..OOOOOOOO..      (focus 틀,        (normal 틀,
.OssssssssO.      .OuuuuuuuuO.       O=r3, u=r1)       O=c3, s=c2, W=c2)
OsWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
OWWWWWWWWWWO      OuWWWWWWWWuO
.OWWWWWWWWO.      .OuuuuuuuuO.
..OOOOOOOO..      ..OOOOOOOO..
```
normal: `O` `w3`, `s` `c3` (안쪽 위 그림자), `W` `white`. focus: `O` `u3`, `u` `u1`.

- 높이 44px = 테두리 8 + 내용 28 + 8. CSS: `border: 8px solid transparent; border-image: url(input-normal.png) 4 fill / 8px / 0 stretch; padding: 0 4px; font-size: 16px; background: none; outline: none;` (포커스는 스킨이 표시하므로 이 요소만 `outline` 대신 `input-focus.png`를 쓴다)
- 오류 상태는 `aria-invalid="true"`일 때 `input-error.png`.

### 7.5 칩 `chip.png` (8 x 8)

```
.OOOOOO.
OHHHHHHO
OBBBBBBO
OBBBBBBO
OBBBBBBO
OBBBBBBO
OSSSSSSO
.OOOOOO.
```
`O` `w3`, `H` `white`, `B` `c1`, `S` `c2`. 높이 28px (6 + 16 + 6), 가로 패딩 `0 6px`(테두리 포함 12px), 글자 `fs-sm` 14px 700 `ink`. 아이콘이 있으면 왼쪽에 18 x 16 아이콘 + 4px 간격.

### 7.6 말풍선 (Canvas)

`bubble.png` 12 x 12:
```
..OOOOOOOO..
.OWWWWWWWWO.
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
OWWWWWWWWWWO
.OccccccccO.
..OOOOOOOO..
```
`bubble-tail.png` 8 x 4:
```
OccccccO
.OWWWWO.
..OWWO..
...OO...
```
`O` `hb2`, `W` `white`, `c` `c2`.

꼬리는 말풍선 아래 가운데에 붙인다. 꼬리 0행이 말풍선 마지막 행(외곽선)과 겹친다 (꼬리 위 끝 = 말풍선 아래 끝 - 2 CSS px). 크기와 위치 규칙은 9장.

### 7.7 닉네임 라벨 (Canvas)

```
label-other        label-self
.OOOOOO.           (같은 틀,
OHHHHHHO            O=y4, H=y2, B=y3)
OBBBBBBO
OBBBBBBO
OBBBBBBO
OBBBBBBO
OBBBBBBO
.OOOOOO.
```
label-other: `O` `ink`, `H` `hb1`, `B` `hb2`. 크기와 위치 규칙은 8장.

### 7.8 아이콘

`icon-mushroom.png` 9 x 8:
```
..OOOOO..
.ORRRWRO.
ORWRRRRRO
ORRRRWRRO
OOOOOOOOO
..SCCCS..
..SCCCS..
..SSSSS..
```
`O` `r3`, `R` `r2`, `W` `c1`, `S` `w3`, `C` `c1`.

`icon-arrow.png` 4 x 7 (오른쪽 화살표, 전부 `w4`):
```
X...
XX..
XXX.
XXXX
XXX.
XX..
X...
```

### 7.9 LOCAL MODE 칩 (CSS만, PNG 없음)

- 모양: 배경 `hb2`, 글자 `y2` 11px 700, 글자 간격 0.5px, `border: 2px solid #1A1626`, 패딩 `2px 6px`, 높이 20px, 모서리 없음.
- 위치: `position: fixed`를 쓰지 않는다 (사이클 1 QA: 카드와 겹침). 로그인/생성 화면은 패널 맨 아래 줄 안 가운데 ("LOCAL MODE" 칩 + 오른쪽 4px에 `fs-xs` `--text-muted` "이 브라우저에만 저장됩니다"). 게임 화면은 HUD 왼쪽 위 접속자 배지 오른쪽 8px (세로 가운데 맞춤).
- supabase 모드에서는 표시하지 않는다.

### 7.10 상태별 적용 요약 (DOM)

| 요소 | 기본 | 호버 | 눌림 (`:active`) | 포커스 (`:focus-visible`) | 비활성 |
|---|---|---|---|---|---|
| 주 버튼 | primary-normal | primary-hover | primary-pressed | 기본 스킨 + 포커스 외곽선 | primary-disabled |
| 보조 버튼 | secondary-normal | secondary-hover | secondary-pressed | 기본 스킨 + 포커스 외곽선 | primary-disabled |
| 탭 (활성/비활성) | 활성 = primary-pressed, 비활성 = secondary-normal | 비활성만 secondary-hover | - | 포커스 외곽선 | primary-disabled |
| 입력 | input-normal | (변화 없음) | - | input-focus | input-disabled |
| 입력 오류 | input-error | - | - | input-focus (포커스 중에는 포커스 우선, 오류 문구는 계속 표시) | - |

### 7.11 배너

| 종류 | 모양 | 글자 |
|---|---|---|
| 정보 배너 (입장 중, 재연결 중 안내 등) | `chip.png` 9-slice, 패딩 `2px 10px` (테두리 6px 별도) | `fs-sm` 14px 700 `ink` |
| 오류 배너 (카드 상단 오류, 연결 끊김, 재연결 실패) | CSS: `background: #FFC8DC; border: 2px solid #9E2838; box-shadow: 0 2px 0 #9E2838;` 패딩 `8px 12px`, 모서리 없음 | `fs-sm` 14px 700 `--error` |

블러 없는 오프셋 그림자(`0 2px 0`)는 픽셀 립으로 보므로 허용한다.

스킨 PNG 로딩 실패 시 대체: 같은 요소에 `background: var(--panel); border: 2px solid #5E3620;` (주 버튼은 `background: #F7C948`)를 먼저 깔고 `border-image`를 덮는다. 스킨이 없어도 조작 가능해야 한다.

---

## 8. 닉네임 라벨

| 항목 | 값 |
|---|---|
| 스킨 | 다른 사람 `label-other`, 내 캐릭터 `label-self` (7.7) |
| 크기 | 높이 20 CSS px. 가로 = 글자 폭 + 12, 2의 배수로 올림. 최소 24 |
| 위치 | 가로 중심 = 기준점 화면 x (2의 배수로 반올림). 위 끝 = 발바닥 화면 y + 4 (발바닥 화면 y = `(220 - camY) * P`) |
| 글자 | `fs-xs` 12px 700. 다른 사람 `white` + `ink` 그림자 (+1,+1). 나 `ink` + `y1` 그림자 (0,+1). 글자 위 = 라벨 위 + 2 |
| 최대 길이 | 닉네임 최대 12자 (라벨 폭은 글자에 따름) |
| 화면 안 보정 | 가로가 캔버스 밖으로 나가면 좌우 4px 안으로 밀어 넣는다 |
| 크기 기준 | CSS px (U=2 고정). 카메라 배율 P와 무관 |

4.3절 카메라 규칙상 지면 아래로 항상 60 CSS px(P=2) 이상이 보이므로 라벨(발 + 4 ~ 발 + 24)은 잘리지 않는다.
Canvas `fillText`만 쓴다. DOM으로 만들면 `textContent`만 쓴다 (XSS 방지).

---

## 9. 말풍선

| 항목 | 값 |
|---|---|
| 스킨 | `bubble.png` 9-slice + `bubble-tail.png` (7.6) |
| 꼬리 끝 위치 | 가로 = 기준점 화면 x. 세로 = 머리 위 기준선 화면 y - 4. 머리 위 기준선 = 아트 y `220 - 44` (프레임 y 2, 머리 모양과 무관하게 고정) |
| 몸통 위치 | 몸통 아래 끝 = 꼬리 끝 - 6. 꼬리 그림 위 끝 = 몸통 아래 끝 - 2 |
| 글자 | `fs-sm` 14px 700 / 줄간격 18px, `ink` + `c2` 그림자 (+1,+1) |
| 안쪽 여백 | 바깥 끝에서 가로 12px, 세로 8px (스킨 테두리 8px 포함) |
| 크기 | 가로 = 가장 긴 줄 폭 + 24, 최소 40, 최대 200. 세로 = 줄 수 x 18 + 16. 둘 다 2의 배수로 올림 |
| 줄바꿈 | 공백 기준. 공백 없는 긴 글은 글자 단위 |
| 최대 줄 수 | 4줄. 넘으면 4번째 줄 끝을 `…`으로 자른다 |
| 표시 시간 | 5초, 마지막 0.5초 동안 `globalAlpha` 1 → 0 |
| 중복 | 같은 사용자의 새 말풍선은 기존 것을 즉시 교체 |
| 화면 안 보정 | 가로: 좌우 8px 안으로 밀어 넣는다 (꼬리는 아바타 x를 계속 가리키되 몸통 안쪽 8px 범위로 제한). 세로: 몸통 위 끝이 캔버스 위 4px보다 위면 4px로 내린다 (꼬리 생략) |
| 텍스트 처리 | Canvas `fillText`만. HTML 금지 |
| 채팅 저장 | 없음 |

---

## 10. 모바일 대응 요약

- 720px 미만은 모바일 레이아웃. 기준 폭 360px.
- 픽셀 배율 P=2 고정 (4.2절). 캔버스는 화면 폭을 꽉 채우고, 세로는 아래 조작 영역(124px)을 뺀 나머지를 모두 쓴다 → 하단 빈 공간 없음 (사이클 1 QA 해결).
- 카메라 아래 끝 고정(4.3절) → 닉네임 라벨이 캔버스 안에 들어온다 (사이클 1 QA 해결).
- LOCAL MODE 칩은 문서 흐름 안에 둔다 (7.9절) → 카드와 겹치지 않는다 (사이클 1 QA 해결).
- 좌우 여백: 패널과 조작 영역 16px. 캔버스는 여백 없음. 가로 스크롤 금지.
- 터치 목표 최소 44 x 44 px.
- 세부 배치: `screens/login.md`, `screens/character-create.md`, `screens/game.md`.

---

## 11. 참고 시안 (`docs/design/ref/`)

디자인이 이 문서의 값으로 직접 찍어 본 검증용 초안이다. 아트는 품질을 더 올려도 되지만 좌표, 팔레트, 크기, 영역 규칙은 이 문서를 따른다.

| 파일 | 내용 |
|---|---|
| `avatar-draft.png` | 5개 조합 x 6프레임, 6배 확대 |
| `anatomy-14x.png` | idle0 해부도 격자 |
| `map-draft.png` | 게임 화면 시안 960 x 540 (P=2), 라벨/말풍선 포함 |
| `world-1x.png` | 맵 전체 1200 x 270, 1배 |
| `login-desktop.png`, `login-mobile.png` | 로그인 화면 시안 (960 x 600, 360 x 640) |
| `panel-8x.png`, `buttons-8x.png` | 패널, 버튼 스킨 8배 |
| `draft-src/*.py` | 위 시안을 만든 Pillow 스크립트 (디자인 검증용, 아트 정본 아님. 정본 스크립트는 `assets/_src/`) |
