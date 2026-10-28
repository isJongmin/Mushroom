"""버섯마을 사이클 10 맵: Canva 원본 그림 패널 표 (정본).

패널은 왼쪽 → 오른쪽 순서로 이어 붙는다. 파일이 없는 패널은 건너뛴다(중앙 하나로도 동작).
좌표는 모두 **원본 그림 px** 기준이다. build.py 가 배율(UPSCALE)과 패널 위치로 월드 단위로 바꾼다.

- ground: 그림 속 잔디 윗면(지면)의 서는 높이 행. 패널마다 측정해 적고, 이어 붙일 때 이 행이 같은 높이가 되게 맞춘다.
- platforms: (id, x1, x2, y) 서는 선. y = 윗면 앞쪽 윗끝 + 약 3px(발이 윗면 위에 놓여 보이는 높이).
  측정법: 잔디 섬은 잔디색 비율이 행 기준 90%를 넘는 첫 행(=윗면 윗끝), x1~x2 는 그 아래 4px 행의 잔디 연속 구간.
  지붕 턱과 처마, 벤치 등받이는 확대 크롭(scratchpad c10map/meas)에서 직접 읽었다.
- spawns: (id, platform id | 'ground', x1, x2, mobs, max). ground 의 x 는 패널 px.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, 'orig')

PANELS = [
    dict(name='left', file=os.path.join(ORIG, 'left.png'), ground=None, platforms=[], spawns=[]),
    dict(
        name='center', file=os.path.join(ORIG, 'center.png'),
        ground=790,                       # 잔디 윗면 띠 784~797 의 가운데
        platforms=[
            ('c-isle-lt', 3, 148, 305),          # 왼쪽 위 섬 (스트링 라이트, 화분)
            ('c-isle-cherry', 267, 504, 355),    # 벚나무 섬
            ('c-isle-lamp', 140, 250, 465),      # 가로등 작은 섬
            ('c-isle-low', 545, 702, 549),       # 가운데 낮은 꽃 섬
            ('c-isle-fence', 676, 941, 381),     # 펜스와 가로등 섬
            ('c-isle-flower', 934, 1135, 499),   # 오른쪽 꽃 섬
            ('c-isle-bench', 1245, 1464, 355),   # 벤치 섬 (스트링 라이트)
            ('c-isle-cherry2', 1556, 1772, 437), # 오른쪽 벚나무 섬
            ('c-cafe-ledge', 192, 516, 580),     # 이끼 돔 카페 돔 아래 턱
            ('c-bakery-eave', 1188, 1592, 580),  # 테라코타 베이커리 처마 맨 아래 단
            ('c-bench', 870, 1037, 727),         # 광장 벤치와 펜스 등받이
        ],
        spawns=[
            ('c-cherry-slime', 'c-isle-cherry', 285, 486, ['slime'], 2),
            ('c-fence-shroom', 'c-isle-fence', 700, 920, ['mushroom'], 2),
            ('c-flower-snail', 'c-isle-flower', 950, 1120, ['snail', 'mushroom'], 2),
            ('c-bench-bat', 'c-isle-bench', 1265, 1445, ['bat'], 2),
            ('c-cherry2-slime', 'c-isle-cherry2', 1575, 1755, ['slime', 'mushroom'], 2),
            ('c-ground-w', 'ground', 10, 150, ['snail'], 1),
            ('c-ground-e', 'ground', 1630, 1766, ['snail'], 1),
        ],
        spawn_x=800,                      # 플레이어 시작: 파라솔과 벤치 사이 광장 앞 지면
    ),
    dict(name='right', file=os.path.join(ORIG, 'right.png'), ground=None, platforms=[], spawns=[]),
]

UPSCALE = 1.25          # 원본 px → 에셋 px (최대 1.25)
DENSITY = 1.5           # 에셋 px / 월드 단위 (계약)
SKY_PAD = 141.667       # 그림 위에 덧붙이는 하늘 (월드). groundY 가 정수(800)가 되도록 고른 값
OVERLAP = 120           # 패널 이음매 겹침 (원본 px)
EDGE_FADE = 90          # 맵 양 끝 마감 폭 (에셋 px)
