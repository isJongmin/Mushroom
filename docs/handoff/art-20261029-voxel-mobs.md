# Original 3D voxel monsters — 2026-10-29

기존 2D 몬스터를 필터 처리한 결과가 아니라, 5종을 새 solid 3D Box 모델로 만들고 아바타의 `assets/_src/voxel/vox.py` 분석적 직교 raycaster로 렌더링했다. 상자의 실제 깊이, 계단형 외곽선, 윗면·앞면·옆면 조명, warm key light와 AO를 사용한다. 눈·무늬·핵도 기하 상자로 구성된다. 기존 2D 원본, 벡터 실루엣, 팔레트 축소나 픽셀화 후처리는 사용하지 않는다.

## Models and sources

- `assets/_src/voxel_mob/model.py`: 종마다 독립적인 원본 모델과 move/hit/die 포즈. 모델당 21–49 boxes.
- `assets/_src/voxel_mob/build.py`: shared renderer/SS4 downsample, 4-worker build, runtime PNG 설치, contact sheets/GIFs, art metadata.
- `assets/_src/voxel_mob/check.py`: 기존 gameplay/frame 계약 비교, 49개 프레임의 RGBA/bounds/중복 검사, 대표 5프레임 byte-identical 재렌더 검사.

| Kind | 새 입체 디자인 | Runtime sheet | Frame | Frames |
| --- | --- | --- | --- | --- |
| snail | 낮은 jade 발판몸, amber 계단껍질과 돌출 사각 나선, 두 눈자루 | 810 × 72 | 90 × 72 | 9 |
| mushroom | 비대칭 terracotta 계단갓, 크림색 줄기, 돌출 cream 갓무늬 | 1188 × 126 | 108 × 126 | 11 |
| slime | mint cube jelly, 3단 crown, 입체 반사광 조각 | 1188 × 114 | 108 × 114 | 11 |
| bat | 두꺼운 plum 블록날개·날개마디, amber 눈, 사각 귀와 송곳니 | 1080 × 102 | 120 × 102 | 9 |
| golem | mossy sandstone 분절 팔다리, 함몰 turquoise 광물핵 | 1944 × 198 | 216 × 198 | 9 |

## Runtime contract

`assets/mob/{snail,mushroom,slime,bat,golem}.png` 5개를 교체했다. 기존 density=1.5, 모든 frame/anchor/size, 애니메이션 인덱스, move 4 또는 6프레임, hit 1프레임, die 4프레임, FPS를 그대로 유지한다. 따라서 월드 크기와 발 기준점은 바뀌지 않는다. 오른쪽을 보는 원본을 사용하고 왼쪽 방향은 기존 runtime 반전을 사용한다. hop 높이는 프레임 안에 들어 있다.

HP, speed, touchDamage, behavior, buffDrop, buffDropCount를 포함한 게임 설정은 원본과 같다. manifest 변경은 revision=`fine-voxel-mobs-20261029-v2`, 종별 `artStyle=fine-voxel-3d`, 공통 `mobArt` 원본/렌더러 설명, `pixelArt=false`뿐이다. SS4의 미세한 가장자리 커버리지를 표시하므로 이전 2D pixelArt 전용 nearest 필터를 끈다.

전체 runtime mob PNG 8개 중 5종만 교체했다. `ghost.png`, `tombstone.png`, `drop_bag.png` 3개와 manifest의 ghost/tombstone/dropBag/fx 메타데이터, `assets/fx/**`는 그대로다. 아바타·배경·클라이언트 코드·기존 voxel 소스는 이 작업에서 수정하지 않았다.

## Build and validation

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 assets/_src/voxel_mob/build.py --static --jobs 4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 assets/_src/voxel_mob/build.py --jobs 4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 assets/_src/voxel_mob/check.py
```

5종 정지 프레임을 먼저 렌더링하고 `out/static-contact.png`를 직접 확인했다. 이후 전체 49프레임을 렌더링하고 `out/all-frames.png`를 확인했다. 첫 빌드에서 발견한 달팽이 사망 프레임의 가로 넘침은 모델 산개량을 줄여 해결했다. 최종 검사 결과:

- 49/49 프레임에 불투명 본체가 있고 네 변 모두 transparent 여백이 남으며 clipping이 없다.
- 49프레임 모두 각 종 안에서 서로 다른 픽셀을 갖는다.
- 원본 gameplay/frame/animation 계약과 추가 metadata가 유지된다.
- 대표 5프레임을 모델부터 다시 렌더링한 결과 runtime PNG crop과 byte-identical이다.
- 기타 mob PNG 3개는 HEAD와 byte-identical이며 effects 변경이 없다.

검사 상세 및 SHA256: `assets/_src/voxel_mob/out/validation.json`. 개별 frame bounds/box count/render time: `out/build-report.json`. 정지 미리보기: `out/static-contact.png`; 전체 프레임: `out/all-frames.png`; 움직임: `out/{kind}-move.gif`.

제약: 이 결과는 실제 3D 기하를 미리 렌더링한 PNG이며 runtime 3D 모델은 아니다. 슬라임의 투명한 느낌은 불투명 mint 재질과 입체 반사광으로 표현했다. 사망은 기하 상자의 압축·산개와 기존 runtime fade를 결합한다. commit/push는 하지 않았다.
