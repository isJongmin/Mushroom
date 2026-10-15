# art -> main: 사이클 3 블록 스타일 최종 에셋 (아바타 + 맵)

날짜: 2026-10-14 / 담당: 아트
상태: 납품 완료. docs/ARCHITECTURE.md "블록 아트 계약" 기준. `check.py` 전 항목 통과.
기반: 승인된 샘플 block_v1 -> 정식 소스 `assets/_src/block/` 로 옮겨 정리(block_v1, sample_v3, 사이클 2 소스/에셋 삭제).

## 1. 빌드 방법

```
python3 assets/_src/block/build.py                    # assets/avatar/**, assets/map/** 전체 재생성 (약 4초)
python3 assets/_src/block/build.py --preview <폴더>   # + 미리보기 PNG/GIF (저장소 밖 폴더 권장)
python3 assets/_src/block/check.py                    # 납품 검사 (결정적 빌드 포함)
```
- Pillow만 사용. 난수 없음(좌표 해시 노이즈), 빌드 시 `assets/avatar`, `assets/map` 을 비우고 다시 만든다.
- 소스: `palette.py`(42색 + 재질 램프 + DARKER/LINE 표), `render.py`(상자 렌더러, 사선 A=0.2), `parts.py`(마네킹 치수, 모든 파츠, 프리셋, 프레임 포즈), `avatar.py`(레이어 분리, 시트/manifest/outline.json, 프런트와 같은 합성·외곽선 기준 구현 `compose()`/`silhouette()`), `mapgen.py`(타일, 소품, 맵 레이어), `build.py`, `preview.py`, `check.py`.

## 2. 파일 목록 (납품 52개)

- `assets/avatar/manifest.json`, `assets/avatar/outline.json`
- `assets/avatar/<layer>/<id>.png` 47장 (모두 336x64, 7프레임): skin 3, face 4, hair_back 8, hair_front 8, top 6, bottom 5, shoes 4, hat 5 (`hat/none` 파일 없음)
- `assets/map/manifest.json` + `sky.png`, `clouds.png`, `far.png`, `mid.png`, `ground.png`
- 삭제: `assets/ui/` 전체(계약상 PNG UI 스킨 폐기), 사이클 2 `assets/avatar/{skin,eyes,hair,top,bottom}`, `assets/map/{mountains,hills,trees,village}.png` 등, `assets/_src/*.py`, `assets/_src/data/`, `assets/_src/sample_v3/`, `assets/_src/block_v1/`

## 3. 아바타 규격 (계약 그대로)

| 항목 | 값 |
|---|---|
| 프레임 / 시트 | 48x64 / 336x64, 순서 `front, side_idle, side_walk0..3, back` (프레임 i의 x = 48i) |
| 기준점 | (24, 60). 지면선 y에 서면 프레임 왼쪽 위 = (x-24, y-60) |
| 실제 범위 | 모든 프리셋 + 무작위 200조합 합성의 불투명 픽셀 x 5..44, y 8..60 (외곽선 포함 x 4..45, y 7..61, 프레임 안) |
| 키 | 발~머리 위 약 43px(머리카락 포함 약 45px), 버섯 모자 쓰면 52px |
| 레이어 순서 | `hair_back, skin, face, bottom, shoes, top, hair_front, hat` |
| 애니메이션 | idle = 프레임 1 (500ms), walk = 2,3,4,5 (150ms). 왼쪽 = x 24 기준 좌우 반전 |
| 외곽선 | 레이어 PNG에는 없음. 합성 후 바깥 실루엣 1px, 이웃 탐색 아래/왼쪽/오른쪽/위, 색은 `outline.json` (아바타에 쓰인 38색 전부, 대문자 HEX) |

### 파츠 id 전체 (manifest `parts` 순서 = 첫 항목이 기본값)

| part | id (label) |
|---|---|
| skin | `light` 밝은 피부, `medium` 보통 피부, `dark` 진한 피부 |
| face | `basic` 기본(동그란 눈+볼터치), `smile` 웃음(^^), `wink` 윙크, `sleepy` 졸린 눈 — 옆모습 눈도 각각 |
| hair | `black-short` 검은 짧은 머리, `brown-short` 밤색 짧은 머리, `blonde-spiky` 금발 뻗친 머리, `pink-long` 분홍 긴 머리, `sky-bob` 하늘색 단발, `tan-ponytail` 갈색 포니테일, `black-twintail` 검은 양갈래, `mint-curly` 민트 곱슬 |
| top | `hoodie-black` 검은 후드티, `hoodie-white` 흰 후드티, `blouse-white` 흰 블라우스, `overalls-green` 초록 멜빵, `tee-stripe-red` 빨간 줄무늬 티, `cape-blue` 파란 망토 셔츠 |
| bottom | `pants-navy` 남색 바지, `pants-black` 검은 바지, `skirt-pink` 분홍 치마, `shorts-brown` 갈색 반바지, `jeans-blue` 청바지 |
| shoes | `sneakers-white` 흰 운동화, `maryjane-red` 빨간 메리제인, `boots-brown` 갈색 부츠, `sneakers-black` 검은 운동화 |
| hat | `none` 없음, `cap-white` 흰 야구모자, `mushroom-red` 빨간 버섯 모자, `explorer-brown` 갈색 탐험가 모자, `beanie-yellow` 노란 비니, `ribbon-pink` 분홍 리본 |

hair id 하나 = `hair_back/<id>.png` + `hair_front/<id>.png` (뒤로 넘어가는 부분이 없으면 hair_back 은 완전 투명 시트).

### presets (manifest `presets`, 6종)

| label | skin | hair | face | top | bottom | shoes | hat |
|---|---|---|---|---|---|---|---|
| 후드 소년 | light | black-short | basic | hoodie-black | pants-navy | sneakers-white | none |
| 분홍 소녀 | light | pink-long | basic | blouse-white | skirt-pink | maryjane-red | none |
| 모자 소년 | light | brown-short | smile | hoodie-white | pants-black | sneakers-black | cap-white |
| 버섯 꼬마 | light | blonde-spiky | basic | overalls-green | jeans-blue | boots-brown | mushroom-red |
| 하늘 마법사 | medium | sky-bob | wink | cape-blue | pants-navy | boots-brown | none |
| 탐험가 | dark | black-twintail | smile | tee-stripe-red | shorts-brown | sneakers-white | explorer-brown |

(앞 4종 = 승인 샘플 c1~c4 의 새 id 버전. 샘플의 빨간 운동화는 목록에 없어 c3 은 검은 운동화, c4 금발은 뻗친 머리 + 청바지로 대체)

### 레이어 독립성
각 파츠는 혼자 렌더한 뒤 공통 몸(skin 기하)이 더 앞에 있는 픽셀만 지운다. 다른 옷/머리 파츠에 의존하지 않으므로 어떤 조합이든 layerOrder 대로 쌓으면 맞물린다(무작위 200조합 프레임 경계 검사, 12조합 육안 검사). 머리카락은 "옷 입은 몸"(몸통/팔/다리 1px 부풀림)보다 뒤인 픽셀만 hair_back.

## 4. 맵 (`assets/map/manifest.json`, 앞쪽이 뒤에 그려짐)

| src | 크기 | y | parallax | repeatX | 내용 |
|---|---|---|---|---|---|
| sky.png | 16x270 | 0 | 0.0 | true | 하늘 띠 k1(0-59) k2(60-109) k3(110-149) k4(150-184) k5(185-269) |
| clouds.png | 640x90 | 10 | 0.1 | true | 블록 구름 5덩이 (이음매 없음) |
| far.png | 640x100 | 122 | 0.3 | true | 8px 열 x 6px 계단 블록 산 (윗면 white, 정면 m1, 옆면 k5). 아래 끝 222 |
| mid.png | 640x110 | 112 | 0.6 | true | 민트톤 블록 나무 숲(둥근 나무/뾰족 나무) + 덤불 띠. 아래 끝 222 |
| ground.png | 1200x210 | 60 | 1.0 | false | 잔디 타일 윗면 첫 행 y=218, 지면선 220, 흙/돌 타일 ~270 + 지면 위 소품 |

- 헤더: `{ "scale": 2, "groundY": 220, "width": 1200, "layers": [...] }`. 반복 레이어의 아래 끝은 잔디(218, 완전 불투명 행) 뒤에 숨는다.
- 지면: y 218, 220, 269 행이 x 0..1199 전부 불투명(검사). 걷는 면은 평평. 소품 밑면은 잔디 윗면의 뒤 가장자리(마지막 행 217)라 캐릭터(기준점 220)가 항상 소품 앞을 걷는다. 소품은 충돌 없음.
- 소품 배치 (x = 아트 px 중심): 뾰족 나무 26, 둥근 나무 74, 덤불 116, 빨간 버섯 집 162(갓 3단, 굴뚝, 문 높이 50, 창 2), 울타리 228-288, 가로등 314, 주황 버섯 집 384(작음, 문 48, 창 1), 둥근 나무 454, 돌 블록 3개 486, 우물 556, 표지판(버섯 아이콘) 618, 덤불 650, 파란 버섯 집 722(가장 큼, 문 50), 뾰족 나무 800/834, 가로등 870, 보라 버섯 집 950(문 48), 울타리 1010-1058, 덤불 1046, 둥근 나무 1094, 뾰족 나무 1150, 돌 블록 2개 1168, 꽃 블록 20개.
- 나무 7그루(둥근 3, 뾰족 4), 집 4채(빨강/주황/파랑/보라). 문 높이 48~50 >= 캐릭터 키 45.

## 5. 사이클 2 id -> 새 id 매핑 제안 (프런트/백엔드 참고)

키 변경: `eyes` -> `face`. 새 키 `shoes`(기본 `sneakers-white`), `hat`(기본 `none`).

| part | 예전 id | 새 id | 비고 |
|---|---|---|---|
| skin | skin-light / skin-tan / skin-dark | light / medium / dark | |
| hair | hair-round-black | black-short | |
| hair | hair-round-chestnut | brown-short | |
| hair | hair-spiky-black | black-short | 뾰족 흑발 없음, 색 유지 |
| hair | hair-spiky-chestnut | brown-short | 색 유지 |
| hair | hair-spiky-mint | mint-curly | 색 유지 |
| hair | hair-long-pink | pink-long | |
| hair | hair-long-blonde | blonde-spiky | 긴 금발 없음, 색 유지 |
| face(eyes) | eyes-dot / eyes-round / eyes-sparkle | basic | |
| face(eyes) | eyes-happy | smile | |
| face(eyes) | eyes-sleepy | sleepy | |
| top | top-tee-red | tee-stripe-red | |
| top | top-hoodie-blue | hoodie-white | 파란 후드 없음(형태 유지). 색 우선이면 cape-blue |
| top | top-overalls-blue, top-vest-green | overalls-green | |
| top | top-cape-mushroom | cape-blue | |
| bottom | bottom-shorts-navy | pants-navy | 색 유지 (형태 우선이면 shorts-brown) |
| bottom | bottom-jeans-blue | jeans-blue | |
| bottom | bottom-skirt-pink | skirt-pink | |
| bottom | bottom-pumpkin-green | shorts-brown | |
| 그 밖 | 목록에 없는 id | 해당 part 첫 항목 | 계약 규칙 |

## 6. 검증 결과 (`check.py`, 실행 결과: ALL CHECKS PASSED)

- 파일 1:1: manifest가 가리키는 파일 + manifest 2개 + outline.json = assets/ (`_src` 제외) 전체 52개, 누락/잉여 없음
- 아바타 PNG 47장 모두 336x64 RGBA, 맵 5장 크기/위치 계약 일치(ground 1200 폭, y+높이 = 270)
- 알파 0/255만, 팔레트 42색 외 색 0
- outline.json 38색 = 아바타에 실제로 쓰인 불투명 색 38색 전부, 키/값 대문자 #RRGGBB, 값도 팔레트 색
- manifest 형식(frame/anchor/scale/frames/animations/layerOrder/parts/presets), id 소문자-하이픈, hat 첫 항목 none, presets id 유효
- 프레임 여백: 프리셋 6 + 무작위 200조합 합성 bbox x 5..44 / y 8..60 (외곽선 1px 여유 확보)
- 결정적 빌드: 임시 폴더 2회 빌드 md5 전부 동일, 저장소 파일과도 동일

미리보기 (스크래치, 저장소 밖): `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c3art/`
`parts_4x.png`, `parts_back_4x.png`, `presets_6x.png`, `walk.gif`, `walk_frames_6x.png`, `random_combos.png`, `world_2x.png`

## 7. 회차 기록 (매 회 Read로 확대본 확인)

1. 샘플 지적 사항 1차 반영 후 첫 렌더: 옆면 얼굴 창을 머리 앞 2/3(14/22열)로 넓히고 눈을 화면 앞쪽 3px 안으로, 다리 깊이 8 -> 6, 옆모습 먼 쪽 팔다리 한 톤 어둡게, 머리카락 무작위 노이즈 제거(끝단 결만). 문제: 진한 피부 + 갈색 포니테일 + 탐험가 모자가 전부 같은 갈색, 단발 옆판이 헬멧/귀마개처럼 보임, 금발 옆 삐침이 깊이 그늘 때문에 동그라미(안경)처럼 보임, 긴 머리 뒷모습 윗부분이 여전히 한 판.
2. 긴 머리 뒷머리를 정수리부터 내려오는 다발 5개(길이 -10/-6/-4/-5/-9, 깊이 엇갈림) + 아래층 2다발 + 끝단 계단/세로 결로 재구성. 단발은 옆 다발 3개(앞이 길고 뒤가 짧은 라인) + 뒤 다발 4개. 삐침 상자에 깊이 그늘을 끄는 `noao` 추가, 옆 삐침을 얼굴 창 뒤로. 프리셋 6을 양갈래로 교체. 맵 1차: 흙 소금후추 반점 -> 2x2 덩어리, 굴뚝 키움, 구름 4단.
3. 무작위 조합 검사: 갈색 포니테일이 보통/진한 피부와 비슷 -> 적갈색 램프(w2/y4/w4)로 변경. 반바지가 진한 피부와 같은 w2 -> 짙은 갈색(w3/w4)으로, 길이 3 -> 4행. 걷기 스윙 다리 4.5 -> 5.5px, 팔 4.5 -> 5px. 리본 날개 높이 축소(옆모습 지느러미 느낌 완화), 망토 깊이 +1. 주황 집 창 1개로 차별화.
4. 맵 확대 검사: 흙 타일의 점선 이음매가 바느질처럼 보여 흙 이음매 제거(돌 블록만 이음매). 최종 빌드/검사 통과.

## 8. 자기 평가 (10점)

| 항목 | 점수 | 근거 |
|---|---|---|
| 옆모습 얼굴 | 8 | 얼굴 창이 머리 옆면 2/3, 눈/볼/입이 한눈에 보인다. 윙크/졸린 눈도 옆에서 읽힌다 |
| 긴 머리/포니테일 뒷모습 | 7 | 다발/층/계단 끝단으로 판 느낌은 사라짐. 정수리 쪽은 여전히 넓은 면 |
| 걷기 | 8 | 먼 쪽 다리/팔이 한 톤 어둡고 발 두 개가 매 프레임 분리, 교차 프레임에서 발이 2px 들린다 |
| 모자-머리 겹침 | 8 | 모든 모자 x 모든 머리에서 머리 윗부분이 모자 실루엣 안에 숨는다. 리본은 뾰족 머리 위에 얹혀 보임(의도) |
| 커스터마이징 폭 | 8 | 피부 3 x 표정 4 x 머리 8 x 모자 6 x 상의 6 x 하의 5 x 신발 4 = 69,120 조합, 모두 맞물림 |
| 맵 | 8 | 블록 집 4채/나무 7/우물/표지판/가로등/울타리/돌/꽃, 캐릭터와 스케일 일치. 구름과 먼 산은 단순한 편 |
| 깔끔함 | 8 | 노이즈는 나뭇잎/흙의 덩어리 반점만. 깨진 픽셀 없음 |

## 9. 알려진 문제 / 요청

- [프런트 필수] `assets/ui/` 를 삭제했다(계약: PNG UI 스킨 폐기). 현재 `src/client/style.css`/assets.js 가 `assets/ui/manifest.json` 을 읽는 코드가 있으니 CSS 블록 UI로 교체 또는 404 폴백 확인 필요. `src/client/constants.js` 의 사이클 2 파츠 목록/`eyes` 키도 manifest 기준으로 교체 필요.
- [디자인] `docs/design/style-guide.md` 는 아직 v2.0 픽셀 규격(32x48, 맵 7레이어)이다. 팔레트(1절)는 그대로 유효하고 새 색은 쓰지 않았다. 4~6절 블록 규격 개정은 디자인 담당 작업.
- 보라 갓은 팔레트에 보라가 없어 p2/p3/hb1 (자두색 계열)로 표현했다. 진짜 보라가 필요하면 팔레트 추가 승인 필요.
- 정면(front) 뷰는 사선 투영이라 캐릭터 오른쪽 옆면(화면 왼쪽)이 안 보인다. 단발/긴 머리의 얼굴 옆 머리가 화면 오른쪽에서 더 두껍게 보인다(블록 3/4 시점의 특성). 인게임은 옆모습만 쓴다.
- 왼쪽 보기는 반전이라 비대칭 요소(리본 위치, 머리끈, 탐험가 모자 접힘)와 광원 방향이 같이 뒤집힌다.
- 적갈색 포니테일 + 진한 피부는 명도 차가 크지 않다(색상은 구분됨).
- idle 숨쉬기 프레임 없음(계약 범위: idle = 프레임 1 한 장).
