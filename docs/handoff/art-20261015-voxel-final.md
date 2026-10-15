# art -> main/frontend: 사이클 5 복셀 아바타 전체 파츠 (최종)

날짜: 2026-10-15 / 담당: 아트
상태: 납품 완료. docs/ARCHITECTURE.md "복셀 아트 계약" 기준. `check.py` 전 항목 통과(결정적 빌드 포함).
기반: 승인 샘플 voxel_v1 -> 정식 소스 `assets/_src/voxel/`. 이전 48x64 시트와 `outline.json`은 삭제되고 `assets/avatar/`가 새 산출물로 교체됨.
참고: `assets/_src/voxel_v1/`은 지우지 않고 남겼다. 맵 에이전트가 `voxel_v1/vox.py`를 복사해 쓴다고 했는데 아직 `assets/_src/voxel_map/`이 없어서다. 맵 쪽 복사가 끝나면 지워도 된다(git 이력에도 있음).

## 1. 빌드 방법

```
python3 assets/_src/voxel/build.py                    # assets/avatar/** 전체 재생성 + 검증용 정답 렌더 (2코어 약 7분)
python3 assets/_src/voxel/build.py --preview <폴더>   # + presets.png, parts_<part>.png, walk.gif, walk_frames.png, compare.png, ingame_scale.png
python3 assets/_src/voxel/check.py                    # 납품 검사 (임시 폴더 재빌드로 결정성 확인 포함, 약 6분)
python3 assets/_src/voxel/check.py --fast             # 결정성 재빌드 생략
옵션: --jobs N (multiprocessing, 기본 2), --out DIR, --src-out DIR, --no-truth
```
- numpy, scipy, Pillow만 사용. 난수는 고정 seed의 `default_rng`과 좌표 해시만 쓴다. 빌드는 `assets/avatar`를 비우고 다시 만든다.
- 소스:
  - `vox.py`: 공용 레이캐스터. 상자 ray-slab, 4x4 슈퍼샘플, 키라이트와 소프트 섀도, 하늘/지면/정면 필, 백라이트, 26방향 AO, 베벨, 화면 공간 림, 발광(눈 하이라이트). 맵 쪽 voxel_v1 사본과 비교하면 render()가 서브샘플 버퍼(img/a/zbuf)를 반환하고, emit을 지원하고, 그림자/AO 샘플링이 최적화되어 있다.
  - `model.py`: 마네킹, 파츠 35개, 라벨, 프리셋, 포즈(무릎 관절, 자동 접지), 레이어 분리용 프록시.
  - `build.py`: 렌더 작업 병렬화, 레이어 분리, shade, 시트, manifest, 정답 비교. 프런트와 같은 합성 기준 구현 `composite()`도 여기 있다.
  - `preview.py`, `check.py`
- 검증용 산출물(게임은 쓰지 않음): `assets/_src/voxel/out/truth/preset1..6.png`(조합 전체를 한 번에 렌더한 정답), `out/build_report.json`(시간, 차이).

## 2. 규격

| 항목 | 값 |
|---|---|
| 시트 | 1152x192 RGBA, 가로 8프레임 `front, front_b, side, walk0, walk1, walk2, walk3, back` (프레임 i의 x = 144i) |
| 프레임 / 기준점 | 144x192 px / (72, 180) = 발 중앙 바닥. 밀도 1.5px = 월드 1단위 |
| 키 | 머리카락 포함 약 140px = 월드 약 93단위. 모자 포함 최대 157px(버섯 모자) |
| 실제 범위 | 프리셋 6 + 무작위 40조합, 불투명(a>8) x 13..137, y 23..186. 측면/걷기의 발끝은 y=180 기준 최대 6px 아래(pitch 15도라 신발 앞코가 내려옴) |
| 뷰 | front/front_b yaw 25(정면에서 오른쪽으로 돈 3/4), side/walk yaw 62(오른쪽 보기, 얼굴이 보이는 측면), back yaw 160. pitch 15, 직교. 복셀 1칸 = 2.75px |
| 애니메이션 | `idle_front` [0,1] 600ms (숨쉬기 약 1px), `idle` [2], `walk` [3,4,5,6] 150ms (허벅지 ±30, 무릎 굽힘 최대 48도, 팔 ±40, 자동 접지 바운스, 몸 기울기 3도) |
| 알파 | 반투명 가장자리 있음, 외곽선 없음 |
| 용량 | assets/avatar 전체 1.8MB (PNG 65장 + manifest) |

## 3. layerOrder와 blend (manifest 정본)

| # | layer | part | blend | 내용 |
|---|---|---|---|---|
| 1 | hair_back | hair | source-over | 옷 입은 몸보다 뒤에 있는 머리카락 (긴 머리 등판, 양갈래 먼 쪽 꼬리) |
| 2 | top_back | top | source-over | 바지/신발보다 뒤에 있는 상의 (망토 등판 등) |
| 3 | skin | skin | source-over | 마네킹 전체 (머리, 목, 몸, 팔, 손, 다리, 발) |
| 4 | face | face | source-over | 얼굴 데칼 |
| 5 | bottom | bottom | source-over | |
| 6 | shoes | shoes | source-over | |
| 7 | shade_top | top | **source-atop** | 상의가 몸/다리에 드리우는 그림자 |
| 8 | top | top | source-over | |
| 9 | shade_hair | hair | **source-atop** | 머리카락이 얼굴/어깨에 드리우는 그림자 (앞머리 그늘) |
| 10 | hat_back | hat | source-over | 머리카락 껍데기보다 뒤에 있는 모자 조각 (뒷모습의 챙 등) |
| 11 | hair_front | hair | source-over | 나머지 머리카락 |
| 12 | shade_hat | hat | **source-atop** | 모자가 머리카락/얼굴에 드리우는 그림자 |
| 13 | hat | hat | source-over | |

- 파일: `assets/avatar/<layer>/<id>.png`. **파일이 없으면 건너뛴다.** 빈 레이어는 파일을 만들지 않는다. 예: `hat/none`, 대부분 머리의 `hair_back`, 일부 모자의 `hat_back`.
- 현재 파일: skin 3, face 4, hair_front 8, hair_back 2(pink-long, black-twintail), shade_hair 8, top 6, top_back 6, shade_top 6, bottom 5, shoes 4, hat 5, hat_back 3(beanie-yellow, cap-white, ribbon-pink), shade_hat 5.
- 앞/뒤 레이어 소속은 프레임마다 깊이로 자동 결정된다. 프록시(옷 입은 몸 / 바지·신발 / 머리카락 껍데기)보다 뒤에 있는 서브픽셀이 *_back으로 간다. 그래서 뒷모습에서는 긴 머리와 망토가 앞 레이어로, 측면에서는 먼 쪽 양갈래가 hair_back으로 간다.

## 4. 파츠 id (사이클 3과 같은 키, 같은 id, manifest `parts` 첫 항목이 기본값)

| part | id: 복셀 디자인 |
|---|---|
| skin | `light` #FAD3BA, `medium` #E2A982, `dark` #A3684A. 통통한 몸, 큰 뭉툭한 손발, 모서리를 깎은 상자 |
| face | `basic` 큰 세로 눈(얼굴 높이 약 37%, 갈색 그라데이션 홍채, 발광 하이라이트 3개, 바깥 속눈썹) + 볼터치 + 작은 입. `smile` ^^ 눈 + 벌린 입. `wink` 한쪽 ^ + 미소. `sleepy` 반쯤 감은 눈 + 작은 입 |
| hair | `black-short` 참고 소년의 검은 곱슬 덩어리. `brown-short` 단정한 큰 판 + 옆으로 쓸린 앞머리 + 더듬이. `blonde-spiky` 불꽃처럼 뻗은 굵은 덩어리 12개 + 뾰족 앞머리. `pink-long` 일자 앞머리 + 얼굴 옆 가닥 + 허리까지 층층 뒷머리. `sky-bob` 턱선 단발, 안으로 말린 끝. `tan-ponytail` 높이 묶은 꼬리 + 빨간 끈. `black-twintail` 옆에서 묶은 두 꼬리(어깨 높이) + 빨간 끈. `mint-curly` 크고 둥근 곱슬 |
| top | `hoodie-black`/`hoodie-white` 목 뒤 후드 덩어리, 끈, 캥거루 주머니, 립 소매. `blouse-white` 둥근 칼라, 분홍 리본, 퍼프 소매, 프릴 밑단. `overalls-green` 크림 티 + 초록 가슴판/멜빵(등 교차)/노란 단추. `tee-stripe-red` 흰 티 + 빨간 줄 3개. `cape-blue` 흰 셔츠 + 파란 케이프렛, 등판 망토, 세운 깃, 금색 브로치 |
| bottom | `pants-navy`, `pants-black` 긴 바지(무릎 분리). `skirt-pink` 2단 A라인 + 흰 레이스 단. `shorts-brown` 무릎 위 반바지. `jeans-blue` 밝은 접단 |
| shoes | `sneakers-white`, `sneakers-black` 밑창 + 끈 + 앞코. `maryjane-red` 흰 양말 + 빨간 구두 + 끈과 금색 버클. `boots-brown` 정강이 중간까지, 접힌 윗단 |
| hat | `none` 파일 없음. `cap-white` 3단 둥근 크라운 + 챙 + 빨간 버섯 로고. `mushroom-red` 4단 갓 + 흰 점 + 크림 밑면. `explorer-brown` 넓은 챙 + 진갈색 띠. `beanie-yellow` 둥근 윗단 + 골지 + 접단 + 방울. `ribbon-pink` 머리 위 오른쪽의 큰 리본 |

## 5. 프리셋 (manifest `presets`, 사이클 3과 같은 조합)

| label | skin | hair | face | top | bottom | shoes | hat |
|---|---|---|---|---|---|---|---|
| 후드 소년 | light | black-short | basic | hoodie-black | pants-navy | sneakers-white | none |
| 분홍 소녀 | light | pink-long | basic | blouse-white | skirt-pink | maryjane-red | none |
| 모자 소년 | light | brown-short | smile | hoodie-white | pants-black | sneakers-black | cap-white |
| 버섯 꼬마 | light | blonde-spiky | basic | overalls-green | jeans-blue | boots-brown | mushroom-red |
| 하늘 마법사 | medium | sky-bob | wink | cape-blue | pants-navy | boots-brown | none |
| 탐험가 | dark | black-twintail | smile | tee-stripe-red | shorts-brown | sneakers-white | explorer-brown |

## 6. 검사 결과 (`check.py`, 전 항목 통과)

1. manifest 형식: frame, anchor, density, frames 8개, animations, layerOrder `{layer,part,blend}`, shade_*=source-atop, parts 개수(3/4/8/6/5/4/6), 프리셋 6.
2. 파일과 manifest 일치: 알 수 없는 파일 없음. 필수 레이어(skin, face, hair_front, top, bottom, shoes, hat) 모든 id에 존재. hat/none 파일 없음.
3. 65장 모두 1152x192 RGBA.
4. 기준점이 프레임 안.
5. 프리셋 6 + 무작위 40조합 합성이 프레임 안(x 13..137, y 23..186). 측면 발끝은 기준선에서 최대 6px 차이.
6. 레이어 합성과 전체 렌더의 차이(프리멀티 RGB 평균 절대차 /255, 허용 6.0, 알파 허용 2.0):

   | 프리셋 | 평균 | p95 | 알파 |
   |---|---|---|---|
   | 1 후드 소년 | 3.08 | 16.0 | 0.04 |
   | 2 분홍 소녀 | 4.71 | 21.3 | 0.10 |
   | 3 모자 소년 | 4.30 | 26.3 | 0.05 |
   | 4 버섯 꼬마 | 4.37 | 25.0 | 0.03 |
   | 5 하늘 마법사 | 4.13 | 15.3 | 0.03 |
   | 6 탐험가 | 3.50 | 14.7 | 0.04 |

7. 결정적 빌드: 임시 폴더에 다시 빌드한 66개 파일의 해시가 같음.

## 7. 렌더 시간 (2코어, `--jobs 2`)

- 전체 빌드 약 7분 (`out/build_report.json` 기준 421.7초). 마네킹 조도 캐시 16개 21초, 레이어 작업 280개 299초(작업당 평균 2.1초, shade 포함), 정답 렌더 48프레임 96초.
- 단일 렌더(144x192, 4x4 슈퍼샘플)는 프레임당 약 3.2초.
- `check.py` 전체(재빌드 포함) 약 5분 30초.

## 8. 알려진 문제

- 모자와 큰 머리: 모자는 머리카락 껍데기(머리 +2.4칸)를 감싸도록 키웠다. 그래도 곱슬/뻗친 머리의 바깥 덩어리는 전체 렌더에서 모자를 뚫고 나오고, 레이어 합성에서는 모자가 덮는다(합성 쪽이 더 깔끔). 버섯 모자 아래 금발 덩어리는 챙 밑으로 삐져나온다(의도된 모습).
- shade 레이어는 마네킹 표면(모자는 머리카락 껍데기 근사) 기준이라, 옷 표면과 0.5~2칸 어긋난 곳에서 그림자 경계가 조금 다르다. 프리셋 평균 차이는 3~5/255로 눈으로는 구분되지 않는다.
- 레이어 마스크는 맨 몸 마네킹 기준이다. 걷기 측면에서 먼 쪽 소매가 가까운 다리 바지 가장자리에 1px 정도 겹칠 수 있다.
- 왼쪽 보기는 좌우 반전이라 왼쪽 위 키라이트가 오른쪽 위로 바뀐다(계약상 수용).
- side 뷰의 light 피부는 키라이트를 받는 머리 옆면이 밝게 떠 보인다(거의 흰색).
- 망토, 치마, 머리카락은 걷기에서 흔들리지 않는다(고정).
- 맵은 맵 에이전트가 새 계약으로 교체 중이다. ingame_scale.png는 현재 assets/map(이전 계약)으로 합성한 것이라 스타일 비교가 아니라 크기 확인용이다. 키는 이전 블록 캐릭터(월드 86)와 비슷한 월드 약 93이다.

## 9. 프런트 구현 포인트

1. **합성 순서**: manifest `layerOrder`를 순서대로 돈다. `avatar[part]` 값이 id. `assets/avatar/<layer>/<id>.png`가 있으면 그린다(404면 건너뜀, `hat: 'none'`이면 요청하지 않음). `ctx.globalCompositeOperation = entry.blend`, 그린 뒤 `'source-over'`로 되돌린다.
2. **source-atop 그림자**: shade_*는 지금까지 합성된 픽셀에만 덮인다. 반드시 조합 전용 오프스크린 캔버스(투명에서 시작)에 합성한다. 맵 위에 바로 그리면 맵까지 어두워진다.
3. **캐시**: 외형 조합(7키)마다 1152x192 합성 시트를 1회 만들어 캐시한다. 프리뷰 회전, 인게임 모두 이 시트의 프레임을 쓴다.
4. **표시**: 프레임 (i*144, 0, 144, 192)를 월드 (x-48, y-120)에 월드 96x128 크기로 그린다. 화면 크기 = 월드 x P/2, P=2이면 시트 x 2/3 축소, P=3이면 1:1. `imageSmoothingEnabled = true`, `imageSmoothingQuality = 'high'`. 외곽선은 그리지 않는다.
5. **반전(왼쪽 보기)**: 프레임을 좌우 반전해 그리되 기준점 x=72(월드 48)를 유지한다. 예: `ctx.translate(x, 0); ctx.scale(-1, 1)`로 (-48..48) 범위에 그린다.
6. **애니메이션**: 인게임 정지 = `idle` [2], 걷기 = `walk` [3..6] 150ms. 캐릭터 꾸미기 미리보기는 front [0,1] 600ms 숨쉬기, 회전 미리보기는 front/side/back(0/2/7).
7. **로딩**: 조합 하나에 최대 13장(평균 10장 내외, 장당 약 10~60KB). 파츠 목록 화면은 필요한 것만 지연 로딩한다.

## 10. manifest files 필드

`assets/avatar/manifest.json`에 레이어별 실제 파일 목록 `files`를 추가했다. 이제 이것이 정본이다. 프런트는 `SPARSE_LAYER_FILES` 하드코딩 대신 이 필드를 쓰면 된다(assets.js에 우선 사용 코드 준비됨).

- 형식: `"files": { "<layer>": ["<id>", ...] }`. 키는 `layerOrder`의 13개 레이어 전부(같은 순서), id는 사전순 정렬. 파일이 없는 레이어는 빈 배열.
- 의미: `assets/avatar/<layer>/<id>.png`가 존재하는 경우에만 목록에 있다. 목록에 없는 (layer, id)는 요청하지 않는다(404 없음). `hat: "none"`은 어느 레이어에도 없다.
- 생성: `build.py`가 PNG를 쓴 뒤 디스크의 실제 파일을 읽어 채운다. `python3 assets/_src/voxel/build.py --manifest-only`는 PNG를 건드리지 않고 manifest.json만 다시 쓴다.
- 현재 값(파일 65장): hair_back 2 (black-twintail, pink-long), top_back 6, skin 3, face 4, bottom 5, shoes 4, shade_top 6, top 6, shade_hair 8, hat_back 3 (beanie-yellow, cap-white, ribbon-pink), hair_front 8, shade_hat 5, hat 5. 프런트 handoff의 `SPARSE_LAYER_FILES`와 같다.
- 검사(`check.py` 2번에 추가): files 키 = layerOrder 레이어 전부, id 정렬/중복 없음, files와 실제 파일 정확히 일치, 필수 레이어(skin, face, hair_front, top, bottom, shoes, hat(none 제외))는 해당 파트의 모든 id 포함.
- 전체 재빌드로 PNG 65장이 바이트 단위로 같음을 확인했고, 바뀐 파일은 manifest.json(files 추가)뿐이다.
