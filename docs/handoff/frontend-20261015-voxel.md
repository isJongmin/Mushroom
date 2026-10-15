# frontend -> main/qa: 사이클 5 복셀 렌더 아트 연결

날짜: 2026-10-15 / 담당: 프런트
기준: docs/ARCHITECTURE.md "복셀 아트 계약 (사이클 5)", art-20261015-voxel-final.md, art-20261015-voxel-map.md
상태: 구현 완료. 자체 검증(local 모드) 콘솔 에러/경고 0, 네트워크 4xx 0. 기존 e2e는 블록 계약 항목만 실패(6장).

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| src/client/constants.js | `ART`(아트 px 2:1) 삭제 → `WORLD`(월드 단위, bottomY 540, minViewH 160), `HEAD`(말풍선 기준 기본 104 + 여백 4), `FOOT_SHADOW`(타원 rx 22 ry 5 알파 0.25). `AVATAR` 기본값을 144x192/(72,180)/density 1.5/8프레임/3애니로. `DEFAULT_LAYER_ORDER`를 `{layer,part,blend}` 13개로. `LAYER_PART` 삭제, `REQUIRED_LAYERS` 추가 (`SPARSE_LAYER_FILES`는 manifest files 도입으로 삭제, 3장) |
| src/client/assets.js | 아바타: 부팅 때 manifest만 받음. `layerOrder{layer,part,blend}`, density, animations(idle_front/idle/walk) 읽기. `files` 검사 + `hasLayer`/`getLayer`(지연 로드, 캐시)/`peekLayer`. outline.json 요청 삭제. 맵: 새 manifest(density, groundY 440, width, y 월드, .webp, repeatX, stretchX), 레이어 w/h = px / density |
| src/client/avatar.js | 전면 교체: 지연 로드 → 조합별 1152x192 합성(blend) → 반전 시트(필요할 때) → headTop. 외곽선/outline 로직 삭제. 그리기는 호출 쪽 백킹 컨텍스트에 고품질 스무딩 |
| src/client/game/world.js | 월드 단위 카메라, 장치 px 정수 경계로 레이어 그리기(반복 타일 틈 없음), stretchX, 발 그림자 타원 |
| src/client/game/overlay.js | `drawBubble(ctx, layout, ax, fy, head, canvasW, alpha)`: 머리 위 기준선을 조합별 높이(head, CSS px)로 |
| src/client/screens/room.js | 아트 해상도 오프스크린 + 정수 확대 파이프라인 폐기. 메인 캔버스에 직접. 시야 = 월드, 테스트 훅에 composite/k 추가 |
| src/client/screens/profile.js | 무대 112x144 월드(CSS 크기 그대로), drawMap 미니 장면 배경, 앞 = 숨쉬기 0/1, 썸네일 크롭 재조정, 합성 끝나면 다시 칠하기 |
| src/client/screens/lobby.js | 내 캐릭터 썸네일 크롭/스무딩, 합성 끝나면 칠하기 |
| src/client/style.css | 캐릭터/맵 캔버스 `image-rendering: auto` (ui-kit의 `canvas { pixelated }` 덮어씀) |

index.html, 백엔드 어댑터, 로비/모달/채팅 구조는 그대로.

## 2. 렌더 파이프라인

- 단위: 로직/네트워크/그리기 모두 월드 단위. 화면 CSS px = 월드 x P/2. 장치 px = 월드 x k, `k = (P/2) x dpr`. 시트 px / 1.5 = 월드.
- 방 프레임: `drawMap`(setTransform 단위행렬, smoothing true/high) → 발 그림자 → 아바타(장치 px, 기준점을 장치 px 정수로 반올림) → `setTransform(dpr)` 후 라벨/말풍선(CSS px).
- 맵 레이어: y0 = round((y - camY) k), x 시작 = -camX x parallax x k, repeatX면 주기 w x k로 `xa = round(start + i tw)`, `xb = round(start + (i+1) tw)`로 그려 이음매 틈이 없다. stretchX(하늘)는 캔버스 전체 폭, 시야가 월드 위로 넘치면(키 큰 모바일) 첫 행을 늘려 채움.
- 카메라: camX = clamp(x - viewW/2, 0, 2400 - viewW), camY = 540 - viewH, 둘 다 1/k 단위로 맞춤(장치 px 정수). 화면 아래 끝 = 월드 540(앞 단면 흙/돌 포함, art 미리보기와 같음).
- 아바타 합성: 조합(7키)마다 투명 OffscreenCanvas 1152x192에 layerOrder 순서로 시트 전체를 `globalCompositeOperation = blend`로 1:1 drawImage, 끝나면 'source-over'로 복구. 반전 시트는 왼쪽을 볼 때 처음 만든다(프레임마다 좌우 반전, 프레임 중심 72 = 기준점 x).
- 그리기: 프레임 (i x 144, 0, 144, 192)를 기준점 기준 (x - 72s, y - 180s, 144s, 192s), s = k / 1.5. P=2/dpr1이면 2/3 축소, P=3이면 1:1.
- 애니메이션: 인게임 idle = [2], walk = [3..6] 150ms. 프로필 미리보기 앞 = idle_front [0,1] 600ms(숨쉬기), 옆 = 2, 뒤 = 7, 걷기 = walk. 미리보기 rAF는 앞/걷기일 때만 돌고, 프레임이 바뀔 때만 다시 그린다.
- 지연 로드: 레이어 PNG는 그릴 조합이 생겼을 때만 받는다. 방에서는 내 조합 합성까지 기다린 뒤 그리기 시작, 다른 사람 조합은 처음 그릴 때 요청(그 사이 라벨만 보임). 프로필은 보이는 슬롯/프리셋 조합만 받고 합성이 끝나면 다음 프레임에 다시 칠한다. 디코드 실패/시간 초과(15초) 레이어는 null → 그 레이어만 빼고 합성, `console.warn` 1회(에러 아님).
- 로딩 표시: 기존 그대로(부팅 점 3개, 방 joining 점 3개 + 배너, 프로필 무대 점 3개는 첫 합성이 끝날 때 숨김).

## 3. 레이어 존재 판단 근거 (404 0건) — 갱신: manifest `files` 정본

- 정본: `assets/avatar/manifest.json`의 `files: { <layer>: [id...] }` (art-20261015-voxel-final.md 10절). 프런트는 이것으로만 판단한다. 이전의 하드코딩 표 `SPARSE_LAYER_FILES`(constants.js)는 삭제했다.
- `assets.js hasLayer(layer, id)`: 아래 네 조건을 모두 만족할 때만 true이고, false면 요청하지 않는다.
  - 레이어가 layerOrder에 있다.
  - id가 해당 파츠의 manifest id다.
  - hat `none`이 아니다.
  - `files[layer]`에 id가 있다.
- 형식 검사(`normalizeFiles`): 아래를 모두 만족해야 유효하다. 하나라도 어긋나면 "files 없음"으로 본다.
  - files가 객체다.
  - layerOrder의 13개 레이어 키가 모두 배열(최대 64개)이다.
  - 원소가 모두 id 형식(`^[a-z0-9-]{1,32}$`)이다.
- files가 없거나 깨졌을 때(대체 모드, 메인 결정 2026-10-15): 필수 레이어만 요청한다. 대상은 `constants.js REQUIRED_LAYERS` = skin, face, hair_front, top, bottom, shoes, hat(none 제외)이다.
  - 근거: art check.py 2번에 따라 이 레이어들은 해당 파츠의 모든 id에 파일이 있으므로 404가 나지 않는다.
  - 그림자(shade_*)와 뒷 레이어(hair_back, top_back, hat_back)는 그리지 않는다(메인이 감수하기로 함).
  - `console.warn`은 시작 때 "manifest files가 없거나 형식이 아닙니다 (필수 레이어만 그립니다: 그림자/뒷 레이어 생략)" 1회만 남긴다. 레이어별 경고는 files가 있는데 목록의 파일이 실패할 때만 1회씩 찍는다.
- 대체 모드 검증: Playwright로 manifest 응답만 바꿔 files를 삭제한 경우와 깨뜨린 경우를 각각 확인했다(assets 수정 없음, fallback.py).
  - 두 경우 모두 프리셋 6종이 정상 표시됐다.
  - PNG 200 32건, 404 0건, 콘솔 error 0건, warn 1건.
  - 이전의 "모두 요청" 방식(404 8건과 브라우저 콘솔 error 8건)은 폐기했다.
- 현재 manifest(files 있음) 검증 결과:
  - 404 0건, requestfailed 0건, 콘솔 error/warn 0건.
  - 프리셋 6종 합성 결과가 files 적용 전과 같다(4장 표 수치 동일).

## 4. composite() 비교 결과

방법: 브라우저에서 `createAvatarRenderer(...).ready(preset)` 후 8프레임을 k = 1.5(1:1, 정수 위치)로 빈 캔버스에 그려 getImageData, `assets/_src/voxel/build.py`의 `load_sheets` + `composite()` 결과와 비교. 반전 시트는 프레임별 좌우 반전과 비교.

| 프리셋 | RGBA 평균 절대차 (/255) | 프리멀티 RGB 가중 평균 | 알파 평균 | 최대 | 반전 일치 | headTop(월드) |
|---|---|---|---|---|---|---|
| 1 후드 소년 | 0.027 | 0.074 | 0.000 | 2 | 일치 | 90.7 |
| 2 분홍 소녀 | 0.028 | 0.074 | 0.000 | 2 | 일치 | 89.3 |
| 3 모자 소년 | 0.029 | 0.083 | 0.000 | 2 | 일치 | 94.0 |
| 4 버섯 꼬마 | 0.034 | 0.085 | 0.000 | 2 | 일치 | 100.7 |
| 5 하늘 마법사 | 0.028 | 0.082 | 0.000 | 2 | 일치 | 88.7 |
| 6 탐험가 | 0.039 | 0.101 | 0.000 | 2 | 일치 | 97.3 |

허용 오차(평균 1/255) 안. 남은 차이는 캔버스의 8비트 프리멀티 저장 반올림(반투명 가장자리)이다.

## 5. 배율 / 위치 값

| 항목 | 값 |
|---|---|
| P | 기본 2, 뷰포트 1600x900 이상 3 (모바일 2) |
| 데스크톱 캔버스 | 1280x540 CSS (P2), 1920x810 CSS (P3): 시야 둘 다 월드 1280x540 |
| 모바일 360x640 | 360x508 CSS, 시야 월드 360x508 (아래 끝 540) |
| 캐릭터 화면 크기 | 프레임 월드 96x128. P2에서 키 약 90~100 CSS px, P3에서 135~150 |
| 기준점 | 월드 y 440 (잔디 윗면, 앞 가장자리 446보다 6 뒤) |
| 발 그림자 | 기준점 중심 타원 rx 22, ry 5 (월드), rgba(26,22,38,0.25) |
| 닉네임 라벨 | 발바닥 선 + 6 CSS px (기존 규칙 유지) |
| 말풍선 꼬리 끝 | 발바닥 선 - (headTop + 4) x P/2 - 4 CSS px. headTop = 조합별 idle 프레임 맨 위 불투명(알파>8) 행. 합성 전 기본 104 |
| 프로필 무대 | 월드 112x144 (CSS 224x288 데스크톱, 168x216 모바일), 기준점 (56,128), 배경 = drawMap 카메라 (1460, 312) |
| 썸네일 크롭(시트 px) | 얼굴/머리/모자/프리셋/로비: (16,26) 112; 상의 (22,92) 100; 하의 (27,104) 90; 신발 (32,112) 80 |

## 6. 성능 / 메모리

- 조합 합성(13레이어 drawImage, 레이어 받은 뒤): 평균 0.3~0.7ms, 최대 0.8ms. headTop 읽기 포함 6조합 15.9ms(조합당 약 2.7ms). 첫 조합은 레이어 받기 포함 4~9ms(로컬 서버).
- 합성 시트: 1152x192 RGBA ≈ 0.88MB, 반전 포함 1.77MB. LRU `SHEET_CACHE_MAX = 48` → 최악 약 85MB, 방 20명(전원 좌우 다 봄) 약 35MB. 썸네일 LRU 72장 x 0.1MB ≈ 7.7MB.
- 디코드된 레이어 이미지: 장당 0.88MB, 앱 수명 동안 보관. 방에서 실제로 쓰는 조합만 받으므로 보통 10~30장(9~26MB), 프로필에서 모든 탭을 훑으면 최대 64장(약 57MB).
- 맵 디코드: ground 3600x645(9.3MB) + far/mid 3000폭 2장(10.6MB) + clouds(3.6MB) ≈ 24MB.
- 모바일 메모리가 문제가 되면 SHEET_CACHE_MAX를 24로 낮추고 레이어 이미지를 합성 후 해제하는 방안 검토(지금은 수용).

## 7. 기존 tests/e2e_local.py 결과 (테스트 수정 안 함, QA 영역)

PASS 22 / FAIL 6 / UNVERIFIED 3 (UNVERIFIED 12, 20, 30은 사이클 4와 같은 사유).

| 항목 | 결과 | 원인 | QA 대체 제안 |
|---|---|---|---|
| 22 픽셀 선명도 | FAIL (P 배율 정사각 블록 불균일, 상단 밴드 3312~7190색) | 블록 아트의 "정수 배율 + 스무딩 끔" 검사. 복셀 계약은 스무딩 렌더 + 반투명 가장자리라 정의상 맞지 않음 | 캔버스 버퍼 = CSS x dpr, 캐릭터 영역에 계단(인접 열 반복) 없음, 기준점 행이 잔디색, 반복 타일 이음매에 투명/배경색 열 없음 |
| 23 에셋 로드 | FAIL 3건: outline.json 200 없음, 레이어 43 → 58/58, PNG 48 → 59 | outline.json 폐기(계약), 레이어 수/PNG 수가 블록 기준. 지연 로드라 수는 방문한 조합에 따라 달라짐 | 4xx 0, requestfailed 0, 콘솔 경고 0(통과 중), `images == imageTotal`, outline.json 요청 0건 |
| 24 빌드 재현성 | FAIL | `assets/_src/block/build.py` 삭제됨(아트 사이클 5) | `assets/_src/voxel/check.py`, `voxel_map/check.py --determinism` (프런트 무관) |
| 25 정적 검사 스크립트 | FAIL | 같은 이유(block/check.py 없음) | 위와 같음 |
| 26 꾸미기 화면 | FAIL 3건: 옆 frame 1, 뒤 frame 6, 걷기 2..5 | 프레임 번호 변경: 옆 2, 뒤 7, 걷기 3..6. "앞 frame 0"은 숨쉬기라 0/1 번갈아 → 이번엔 통과했지만 타이밍에 따라 실패 가능 | 앞 ∈ {0,1}, 옆 2, 뒤 7, 걷기 ⊆ {3,4,5,6} |
| 28 애니메이션 | FAIL 6건: idle frame 1, walk 2..5 | 인게임 idle 2, walk 3..6 | idle == 2, walk ⊆ {3..6}, dir 검사는 그대로 |

그 밖의 항목(채팅, 방, 모바일 겹침, XSS, 콘솔 에러 0 등)은 모두 통과.

## 8. 요청

- QA: 7장 표의 22, 23, 26, 28 갱신과 24, 25의 voxel 빌드/검사 경로 교체. 테스트 훅 `assets.images/imageTotal`은 이제 "지금까지 받은/요청한 레이어 수"(부팅 시 0). `assets.composite`({count, avgMs, maxMs}), `assets.layout.k` 추가.
- 디자인: ui-kit.css의 `canvas { image-rendering: pixelated }`(79행), `.bk-slot canvas`, `.bk-presets canvas`, `.bk-thumb canvas`의 pixelated를 복셀 계약에 맞게 정본에서 정리해 주면 style.css 덮어쓰기를 지운다. 프로필 무대 CSS 배경(블록 하늘 밴드 + 잔디 타일, 캔버스가 덮어 보이지 않음)과 무대 배경 장면(맵 x 1460, 뒤에 숲 띠가 머리 뒤에 옴) 검토. 라벨/말풍선은 CSS px 고정 크기라 P3에서 캐릭터 대비 작게 보임 — 규칙 유지 여부 판단.
- 아트: `files` 필드 반영 완료(10절). 추가 요청 없음.
- 메인: files가 없을 때의 동작은 결정 반영 완료(필수 레이어만 요청, 3장).
- 백엔드: 없음.

## 9. QA 확인 항목

1. 콘솔 에러/경고 0, 네트워크 4xx 0, `assets/avatar/outline.json` 요청 0건, 요청한 레이어 PNG가 모두 manifest `files` 목록 안에 있음.
2. 프리셋 6종 적용 → 미리보기 앞(0/1 숨쉬기), 옆(2), 뒤(7), 걷기(3..6). 슬롯/프리셋 썸네일이 비지 않고 채워짐(지연 로드 후).
3. 방: 캐릭터 발이 잔디 위(그림자 타원 아래 흙 단면이 아님), 크기 약 월드 90~105, 흐림/계단 없음, 왼쪽 이동 시 반전, 기준점 x 유지(반전 순간 좌우로 튀지 않음).
4. 말풍선 꼬리가 모자(버섯 모자 포함) 바로 위, 닉네임 라벨은 발 아래.
5. 1280x800(P2), 1920x1080(P3), 360x640(dpr2) 레이아웃과 가로 스크롤 없음(기존 항목 13, 21 통과).
6. 방 입퇴장 반복 시 rAF/리스너 누수 없음(프로필 숨쉬기 rAF는 화면을 떠나면 멈춤, renderer.clear()가 onUpdate 해제).
7. 레이어 이미지 하나가 깨졌을 때(예: 이름 바꾼 사본) 그 레이어만 빠지고 콘솔 에러 없음(warn 1회).

## 10. 스크린샷 (스크래치)

/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c5fe/
- room-desktop.png (1280x800 P2, 두 사람 + 말풍선 + B 왼쪽 반전), room-p3.png (1920x1080 P3), room-mobile.png (360x640 dpr2)
- profile-desktop.png (모자 탭), profile-top.png, profile-hair.png, profile-mobile.png, preview-side.png, preview-back.png, lobby-desktop.png
- 비교 스크립트: verify.py(시나리오), cmp.py(composite 비교), fallback.py(files 없음/깨짐 대체 모드), e2e.log(기존 e2e 전체 로그)
