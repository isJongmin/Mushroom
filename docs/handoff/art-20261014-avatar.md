# 핸드오프: 아바타 파츠 SVG와 맵 배경 (2026-10-14)

작성: 아트 팀. 대상: 프런트(src/client/), 메인, QA.
정본: docs/design/style-guide.md 5장(아바타 규격), docs/ARCHITECTURE.md 인터페이스 계약.

## 1. 산출 파일

아바타 파츠 16개 (style-guide 5.4와 id 일치):
- assets/avatar/skin/: skin-light, skin-tan, skin-dark (3)
- assets/avatar/hair/: hair-round-black, hair-round-chestnut, hair-spiky-black, hair-spiky-chestnut (4)
- assets/avatar/eyes/: eyes-dot, eyes-round, eyes-happy (3)
- assets/avatar/top/: top-tee-red, top-hoodie-blue, top-vest-green (3)
- assets/avatar/bottom/: bottom-shorts-navy, bottom-jeans-blue, bottom-skirt-pink (3)

매니페스트: assets/avatar/manifest.json
- canvas 64x96, anchor (32, 92), layerOrder [skin, bottom, top, eyes, hair]
- 각 part 배열의 첫 항목이 기본값. 기본 조합은 style-guide 5.5와 같다.

맵 배경: assets/map/background.svg (viewBox 0 0 2400 540, 3150 B)
- 하늘 그라데이션, 구름, 먼 언덕, 잔디 띠(y 440~468), 흙(y 468~540), 버섯 집 3채(발 y=440).

## 2. 프런트 참조 방법

- 경로: `assets/avatar/<part>/<id>.svg`. 모든 파츠는 64x96 투명 배경이다.
- 기준점 (32, 92). 캔버스 전체를 같은 위치에 겹친다. 파츠마다 위치 보정은 없다.
- 레이어 순서: skin, bottom, top, eyes, hair (아래 -> 위).
- 왼쪽을 보려면 캔버스 전체를 x=32 기준으로 좌우 반전한다 (scaleX(-1), 캔버스 폭 64 기준).
- 파츠 SVG는 `<img>`로 로드한다. 외부 리소스가 없다.

## 3. 검증 결과

- 구조 검증 151/151 통과 (스크래치 디렉터리의 validate.py).
  - manifest id 목록 = 파일 목록, 추가 파일과 누락 파일 없음
  - 모든 SVG XML 파싱 가능, viewBox와 width/height 일치, svg 네임스페이스
  - <script>, on* 속성, 외부 href/url(), image/foreignObject/use/style 없음
  - 모든 색이 style-guide 팔레트 HEX 안에 있음
  - 파츠 파일 5KB 이하 (최대 skin 1398 B), 배경 15KB 이하 (3150 B)
  - 배경의 잔디 시작 y=440, 흙 시작 y=468
- 렌더 검증 (Playwright Chromium, 레이어 순서대로 겹침):
  - 기본 조합 + 3가지 다른 조합, D 조합의 좌우 반전 확인
  - 16개 파츠 개별 렌더 확인
  - 배경 위 아바타 배치 확인
  - 스크린샷: render_combos.png, render_parts.png, render_bg.png (스크래치 디렉터리 art/)
  - 발견 문제 1개 수정: 뾰족 머리의 골짜기가 y 13에 있어서 두피 윤곽이 머리 위로 비쳐 보였다. 골짜기를 y 8로 올려 해결.

## 4. 알려진 문제 (프런트/메인 확인 필요)

1. 방향: 요청은 "오른쪽을 보는 3/4뷰"였으나, style-guide 5.3의 눈 좌표 (25,31), (39,31)와 "얼굴은 정면 좌우 대칭"을 따랐다. 파츠는 정면 기준이고, 좌우 반전은 프런트가 처리한다. 3/4뷰가 필요하면 디자인 팀이 눈 좌표를 먼저 정해야 한다.
2. 파일 경로: art.md의 예시 `assets/<종류>/<이름>-<변형>.svg`는 ARCHITECTURE 정본 `assets/avatar/<part>/<id>.svg`와 다르다. 이 문서는 정본을 따랐다.
3. 뾰족 머리는 스파이크가 짧다 (끝 y 1.5~2.5, 골짜기 y 8). 두피 윤곽이 비치지 않도록 한 결과다.
4. 바지 사이에 다리 사이 틈이 있다 (반바지, 치마). 스타일 가이드 좌표 그대로다.
5. 모바일에서 아바타 표시 크기가 작다 (style-guide 4 항목 6). 얼굴 특징은 작은 크기에서 점 눈과 볼터치 정도만 식별된다. 실제 크기 확인은 QA 단계에서 한다.
6. 파츠 색은 style-guide 팔레트만 사용했다. 음영, 하이라이트 색은 만들지 않았다 (단색 채움). 머리 금발/분홍 (예약 색)은 id가 없어 파일이 없다.
7. 배경의 버섯 집 색은 팔레트 값으로 처리했다 (지붕 cloth-red, 기둥 cloth-white, 문 shoe 색). 배경 전용 색이 없으므로 디자인 팀이 확인한다.
