# 아바타 선택 폭 확장 (2026-10-29)

기존 6 추천 코디, 모든 기존 파츠 ID/PNG를 유지하며 7 파츠와 추천 6 코디를 추가했다. 원격/커밋 변경 없음.

## 추가 파츠

| 카테고리 | ID | 내용 |
|---|---|---|
| hair | espresso-crop | 이마가 보이는 짧은 크롭. 새 SDF 실루엣, 짧은 뒤/옆머리와 위로 빗은 가닥 |
| hair | copper-spacebuns | 코퍼색 양쪽 번. 새 SDF 연결부/코일/가르마/잔머리 |
| hair | silver-bob | 기존 sky-bob 실루엣의 실버 소재 팔레트 |
| top | varsity-burgundy | 버건디 몸판, 기존 크림 소매/이너/패치 유지 |
| top | cardigan-sage | 세이지 니트. 흰 이너, 갈색 가방/넥타이, 금속 장식 유지 |
| bottom | widepants-cream | 크림 와이드 팬츠. 솔기/접은 단 명암과 라벤더 탭 유지 |
| hat | beanie-sage | 세이지 니트/크림 방울. 새 크롭을 담도록 넉넉한 전용 SDF 크라운 |

파츠 수: skin 3 / face 4 / hair 15 / top 12 / bottom 10 / shoes 7 / hat 9(none 포함). 기존 ID를 덮어쓰거나 바꾸지 않았다. `variety.py`의 소재 팔레트 대응은 지정한 원소재 색과 그 명암에만 적용된다.

## 추천 7~12

| 번호 | 이름 | 피부 / 얼굴 | 머리 | 상의 / 하의 | 신발 / 모자 |
|---|---|---|---|---|---|
| 7 | 버건디 크롭 | dark / smile | espresso-crop | varsity-burgundy / widepants-cream | chunky-white / none |
| 8 | 코퍼 가든 | medium / wink | copper-spacebuns | cardigan-sage / skirt-check | loafer-socks / none |
| 9 | 실버 스트리트 | dark / basic | silver-bob | hoodie-black / cargo-beige | hightop-black / none |
| 10 | 민트 데이 | medium / smile | mint-curly | tee-stripe-red / widepants-cream | sneakers-white / none |
| 11 | 세이지 산책 | light / sleepy | espresso-crop | cardigan-sage / denim-wide | boots-brown / beanie-sage |
| 12 | 트윈 리본 | medium / wink | black-twintail | varsity-burgundy / skirt-pink | maryjane-red / none |

## 계약과 생성

144×192 프레임, 13 포즈, 시트 1872×192, anchor (72,180), density 1.5, 레이어 순서/블렌드 유지. `SHADE_RGB=(52,31,33)`, 상의 shade gain 0.4, 공용 vox.py 수정 없음. revision `fine-pixel-variety-20261029-v2`.

원본: `assets/_src/voxel/model.py`, `variety.py`, `build.py`, `check.py`, `variety_preview.py`.
납품: `assets/avatar/manifest.json`과 신규 ID PNG(19장), 총 131 레이어 시트.

```bash
OPENBLAS_NUM_THREADS=1 python3 assets/_src/voxel/build.py \
  --only hair:espresso-crop,hair:copper-spacebuns,hair:silver-bob,top:varsity-burgundy,top:cardigan-sage,bottom:widepants-cream,hat:beanie-sage \
  --src-out assets/_src/voxel/out/variety --jobs 3
OPENBLAS_NUM_THREADS=1 python3 assets/_src/voxel/check.py --fast --src-out assets/_src/voxel/out/variety
OPENBLAS_NUM_THREADS=1 python3 assets/_src/voxel/variety_preview.py
```

`--only`는 입력 ID를 먼저 검증하고 선택한 파츠의 13 프레임만 렌더한다. 필요한 receiver IRR0를 준비하고 기존 PNG를 유지한다. PNG를 메모리에서 완전히 인코딩한 뒤 임시 파일에서 원자적으로 교체한다. 선택 파츠를 쓰는 추천의 전체 렌더만 갱신한다. 기존 6 full reference는 `out/fine-pixel/truth`를 그대로 복사했고, 새 6 reference는 합성 이미지가 아닌 별도 full render 78프레임으로 생성했다.

## 시안/검증

- 추가 6 코디 정면: `assets/_src/voxel/out/variety/additional6-front.png`
- 기존+추가 12 코디 정면: `assets/_src/voxel/out/variety/all12-front.png`
- 추가 6 코디 × 13 포즈: `assets/_src/voxel/out/variety/additional6-all13poses.png`
- full reference: `assets/_src/voxel/out/variety/truth/preset1.png`~`preset12.png`
- 빌드/검사: `assets/_src/voxel/out/variety/build_report.json`, `check.log`

계약 검사 1~7 통과: 총 131 시트의 RGBA/13프레임/파일 목록/기존 ID/추천12 검증. 기존 112 PNG는 git의 원본 blob 해시와 모두 일치한다. 12 추천 + 40 무작위 조합의 13 포즈 범위는 x 6~136 / y 15~183, 접지 최대 오차 3px, prone 비율은 무모자 0.41~0.44 / 모자 0.42~0.45다. 신규6 full render 대비 평균 RGB 차이는 2.929 / 3.168 / 3.403 / 3.463 / 5.139 / 4.081 (허용 6), alpha MAE 최대 0.087 (허용 2)다. 기존6 reference와의 차이는 원래 값을 유지한다. `check.py --only hair:espresso-crop`로 새 크롭의 13프레임을 임시 폴더에 다시 렌더한 뒤 전체 132파일 해시가 동일함을 확인했다. 초기 정면 샘플에서 비니 앞머리 관통을 발견해 크라운을 보정했다. 새 6 코디의 전체 13 포즈, 정면 6/12 코디를 합성 contact sheet로 직접 확인했다. 전체 옷 조합의 full render 일치와 전체 767-task 재빌드는 이번 증분 작업의 검증 범위에 포함하지 않는다.
