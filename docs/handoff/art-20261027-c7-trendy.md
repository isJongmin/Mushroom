# art -> main/frontend: 사이클 7 트렌디 캐릭터 (Canva 시안 반영)

날짜: 2026-10-27 / 담당: 아트
상태: 납품 완료. docs/ARCHITECTURE.md "복셀 아트 계약"의 시트 규격(144x192, 기준점 (72,180), 11프레임 순서, layerOrder, blend)은 그대로다. `check.py` 결과는 7절에 있다.
변경 범위: `assets/_src/voxel/{model,vox,build,check,preview}.py`, 새 `assets/_src/voxel/legacy_v5.py`(사이클 5 모델 보관본, 모자 형상만 가져다 씀), `assets/avatar/**` 전체 재렌더. commit 안 함. src/client 수정 없음.

## 1. 변경 요약

- 마네킹을 Canva 시안 비율로 다시 잡았다. 머리(머리카락 포함)는 키의 약 40%로 줄였고, 다리와 몸통은 길게 늘렸다. 몸은 상자 대신 어깨와 골반이 있는 몸으로 바꿨다.
- 복셀 1칸은 2.75px에서 **1.82px**로 줄였다. 머리가 22칸에서 28칸이 되어 큐브가 잘고 형태가 부드럽다.
- 얼굴: 큰 눈(굵은 위 속눈썹 라인, 짙은 홍채, 하이라이트 2개), 2단 볼터치, 작은 입이다. 앞머리 바로 아래에 놓았다. 얼굴 4종(basic/smile/wink/sleepy) 모두 새로 그렸다.
- 머리카락: 계단식 앞머리 가닥, 얼굴 가장자리를 덮는 옆머리(볼 감쌈), 정수리 돔 볼륨으로 만들었다. 새 4종에 더해, 기존 8종도 같은 키트로 다시 만들었다(id, 색, 실루엣 의도는 유지).
- 옷: 오버사이즈 핏(떨어진 어깨, 손등을 덮는 소매), 와이드 팬츠, 청키 신발, 가방 끈 디테일을 넣었다. 기존 상의/하의/신발도 새 몸에 맞춰 다시 만들었다. 기존 모자 5종은 사이클 5 형상을 키워 씌웠다.
- 정면 프레임(0 front, 1 front_b)은 시안처럼 캐릭터 왼쪽에서 보는 각도(yaw +25에서 -25)로 바꿨다. 옆/걷기/뒤/점프/하강/숙이기는 그대로다.
- 조명은 시안의 밝은 톤에 맞춰 하늘 필 0.62에서 0.70, 정면 필 0.30에서 0.40, 노출 1.0에서 1.05로 조금 밝혔다.
- 로고와 글자는 없다. 캡은 무지 캡에 크림 둥근 패치만 달았고, 바시티 패치도 크림 원 + 빨간 점이다.

## 2. 새 파츠 id / 라벨 (manifest `parts` 순서: 새 파츠가 앞, 기존 파츠가 뒤)

| 파츠 | 새 id (라벨) |
|---|---|
| hair | `ash-twoblock`(애쉬브라운 투블럭), `black-seethrough`(시스루뱅 긴 흑발, 헤어핀 2개), `black-wolfcut`(검은 울프컷), `pink-bridge-ponytail`(핑크 브릿지 포니테일) |
| top | `hoodie-lavender`(라벤더 오버핏 후드), `cardigan-cream`(크림 가디건과 숄더백), `varsity-navy`(네이비 바시티 재킷), `puffer-mint`(민트 크롭 패딩과 크로스백) |
| bottom | `denim-wide`(연청 와이드 데님), `skirt-check`(체크 플리츠 스커트), `cargo-black`(검정 카고 조거), `cargo-beige`(베이지 와이드 카고) |
| shoes | `chunky-white`(흰 청키 스니커즈), `loafer-socks`(로퍼와 니삭스), `hightop-black`(검정 하이탑) |
| hat | `bucket-white`(흰 버킷햇), `cap-black`(검정 무지 캡). 첫 항목은 계속 `none` |

- 가방은 파츠 키를 늘리지 않으려고 상의에 포함했다(cardigan-cream = 숄더백, puffer-mint = 크로스백).
- 개수: skin 3, face 4, hair 12, top 10, bottom 9, shoes 7, hat 8(none 포함). 사이클 5 id 35개는 모두 유지되고, 저장된 프로필은 그대로 동작한다.
- 각 파츠의 첫 항목(=manifest에 없는 id의 대체값)이 바뀌었다: hair `ash-twoblock`, top `hoodie-lavender`, bottom `denim-wide`, shoes `chunky-white`. skin/face/hat은 그대로다.

## 3. 프리셋 (manifest `presets`, 6종)

| # | 라벨 | skin / face / hair / top / bottom / shoes / hat |
|---|---|---|
| 1 | 라벤더 후드 (시안 1) | light / basic / ash-twoblock / hoodie-lavender / denim-wide / chunky-white / bucket-white |
| 2 | 가디건 걸 (시안 2) | light / basic / black-seethrough / cardigan-cream / skirt-check / loafer-socks / none |
| 3 | 바시티 캡 (시안 3) | light / basic / black-wolfcut / varsity-navy / cargo-black / hightop-black / cap-black |
| 4 | 민트 패딩 (시안 4) | light / basic / pink-bridge-ponytail / puffer-mint / cargo-beige / chunky-white / none |
| 5 | 분홍 소녀 (기존 2) | light / basic / pink-long / blouse-white / skirt-pink / maryjane-red / none |
| 6 | 버섯 꼬마 (기존 4) | light / basic / blonde-spiky / overalls-green / jeans-blue / boots-brown / mushroom-red |

기존 프리셋 중 후드 소년, 모자 소년, 하늘 마법사, 탐험가는 목록에서 빠졌다. 파츠는 그대로 남아 있다.

## 4. 비율과 해상도 (복셀 단위, 발바닥 y=0)

| 항목 | 사이클 6 | 사이클 7 |
|---|---|---|
| 복셀 1칸 | 2.75px | **1.82px** (`build.py SCALE`) |
| 머리 | 22 x 20 x 20 | 28 x 25.6 x 25.6 |
| 다리(엉덩이 관절 높이) | 10 | 27.5 (허벅지 14 + 정강이/발 13.5) |
| 몸통(엉덩이~목) | 12.5 | 20.5 (몸통 뼈 세로 1.17배) |
| 어깨 반폭 / 골반 반폭 | 8.9 / 3.5 | 9.1 / 3.9 (다리 사이 간격 넓힘) |
| 머리+머리카락 / 키 | 약 50% | 약 40% |
| 시트 위 끝 (모자 없음 / 모자 / 포니테일) | y 23~30 | TBD |

- 프레임 안 높이는 6절의 실측을 참고한다. 프런트의 머리 위 기준(headTop)은 합성 시트에서 계산하므로 코드 수정은 필요 없다.

## 5. 프런트 참조 (변경 없음)

- 경로 `assets/avatar/<layer>/<id>.png`, manifest `layerOrder` 순서로 합성하고, `files`에 없는 (layer, id)는 요청하지 않는다. 시트 1584x192, 프레임 144x192, 기준점 (72,180), 11프레임 순서와 animations는 사이클 6과 같다.
- UI 썸네일 크롭(profile.js HEAD_CROP (16,26,112), TOP/BOTTOM/SHOES_CROP, lobby THUMB_CROP)은 그대로 써도 된다. 머리는 y 약 29~95, 어깨는 약 95, 허리는 약 130, 무릎은 약 155에 있다. 모자 꼭대기(버섯 모자 y 약 19, 포니테일 y 약 15)는 HEAD_CROP 위로 몇 px 잘린다(사이클 6도 같음).

## 6. 렌더 시간 / 용량

TBD

## 7. 검사 결과 (`python3 assets/_src/voxel/check.py`)

TBD

## 8. 품질 루프 (스크래치, 저장소 밖)

`/tmp/claude-0/-home-claude/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c7art/`

TBD

## 9. 자기 평가 (10점)

TBD

## 10. 남은 한계

TBD
