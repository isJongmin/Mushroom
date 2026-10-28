"""버섯마을 사이클 10 맵: Canva 원본 그림 패널 표 (정본).

패널은 왼쪽 → 오른쪽 순서로 이어 붙는다. 파일이 없는 패널은 건너뛴다(중앙 하나로도 동작).
좌표는 모두 **원본 그림 px** 기준이다. build.py 가 배율(UPSCALE)과 패널 위치로 월드 단위로 바꾼다.

- ground: 그림 속 잔디 윗면(지면)의 서는 높이 행. 패널마다 측정해 적고, 이어 붙일 때 이 행이 같은 높이가 되게 맞춘다.
- platforms: (id, x1, x2, y) 서는 선. y = 윗면 앞쪽 윗끝 + 약 3px(발이 윗면 위에 놓여 보이는 높이).
  측정법: 잔디 섬은 잔디색 비율이 행 기준 90%를 넘는 첫 행(=윗면 윗끝), x1~x2 는 그 아래 4px 행의 잔디 연속 구간.
  지붕 턱과 처마, 벤치 등받이는 확대 크롭(scratchpad c10map/meas)에서 직접 읽었다.
- spawns: (id, platform id | 'ground', x1, x2, mobs, max). ground 의 x 는 패널 px.
- ropes: (id, x, 위 발판 id, 아래 'ground' | 발판 id).
- protect: 이음매가 자르면 안 되는 사각형 (x1, y1, x2, y2). 발판(윗면 위 30 ~ 아래 45)은 자동으로 보호한다.
- overlap: 앞 패널과 겹치는 폭(원본 px). None 이면 OVERLAP.
- hide: 겹친 구간에서 이 패널 그림을 감출 사각형(옆 패널 그림을 쓴다).
- xmax: 이 열 이후는 쓰지 않는다(다음 패널과 내용이 겹치는 패널).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, 'orig')

PANELS = [
    dict(
        name='left', file=os.path.join(ORIG, 'left.png'),
        ground=790,                       # 잔디 윗면 띠 780~797 (개울 구간 888~1180 은 다리 아래 물가라 조금 낮다)
        # 오른쪽 600px(x 1176~)은 중앙 패널 왼쪽 600px 을 다시 그린 것(같은 구도, 모양은 조금 다름: 카페, 벚나무 섬,
        # 가로등 섬). 겹침 탐색(check.py --find-overlap 결과 600, dy 0)대로 x 1326 에서 자르고 중앙과 150px 겹쳐 섞는다.
        xmax=1326,
        platforms=[
            ('l-isle-bench', 28, 316, 197),       # 왼쪽 위 벤치 섬 (스트링 라이트)
            ('l-isle-cherry', 31, 240, 533),      # 왼쪽 벚나무 섬
            ('l-isle-bench2', 660, 855, 336),     # 가운데 벤치 섬
            ('l-isle-lights', 917, 1190, 236),    # 스트링 라이트 섬
            ('l-cafe1-ledge', 258, 598, 565),     # 왼쪽 회색 돔 상점 돔 아래 턱
            ('l-bridge', 955, 1085, 735),         # 아치 나무다리 가운데(꼭대기 판)
        ],
        spawns=[
            ('l-ground-w', 'ground', 20, 240, ['snail'], 2),
            ('l-ground-pond', 'ground', 640, 880, ['snail'], 2),
            ('l-cherry-slime', 'l-isle-cherry', 50, 225, ['slime'], 2),
            ('l-bench2-shroom', 'l-isle-bench2', 675, 840, ['mushroom'], 2),
            ('l-lights-bat', 'l-isle-lights', 935, 1175, ['bat'], 2),
        ],
        ropes=[
            ('l-rope-cafe1', 588, 'l-cafe1-ledge', 'ground'),       # 돔 상점 턱 오른쪽 끝(굴뚝 아래) → 지면
            ('l-rope-bench', 300, 'l-isle-bench', 'l-cafe1-ledge'),  # 턱 왼쪽 → 왼쪽 위 벤치 섬
            ('l-rope-bench2', 840, 'l-isle-bench2', 'ground'),       # 가운데 벤치 섬 오른쪽 끝 → 지면
        ],
        protect=[],
        hide=[(1176, 280, 1326, 450)],    # 겹친 구간의 가로등 섬(중앙 c-isle-lamp 와 같은 물체의 다른 그림) → 중앙 그림으로
    ),
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
        ],
        # 로프 (id, x 원본 px, 위끝 발판 id, 아래끝이 닿는 곳 'ground' | 발판 id). 위끝 y = 위 발판 서는 높이,
        # 아래끝 y = 아래 서는 높이 - ROPE_REACH(월드). x 는 두 발판 x 범위 안.
        ropes=[
            ('c-rope-cafe', 506, 'c-cafe-ledge', 'ground'),        # 카페 턱 오른쪽 끝 → 지면
            ('c-rope-bakery', 1200, 'c-bakery-eave', 'ground'),    # 베이커리 처마 왼쪽 끝 → 지면
            ('c-rope-lt', 144, 'c-isle-lt', 'c-isle-lamp'),        # 가로등 섬 → 왼쪽 위 섬
            ('c-rope-bench', 1446, 'c-isle-bench', 'c-bakery-eave'),   # 처마 → 벤치 섬
            ('c-rope-cherry2', 1574, 'c-isle-cherry2', 'c-bakery-eave'),  # 처마 → 오른쪽 벚나무 섬
        ],
        spawn_x=800,                      # 플레이어 시작: 파라솔과 벤치 사이 광장 앞 지면
        overlap=150,                      # 왼쪽 패널 x 1176~1326 과 같은 구도
        protect=[(0, 440, 190, 780),      # 왼쪽 끝 벚나무
                 (1500, 180, 1776, 490)],  # 오른쪽 끝 벚나무 섬 (나무 포함)
    ),
    dict(
        name='right', file=os.path.join(ORIG, 'right.png'),
        ground=790,                       # 잔디 윗면 띠 776~797
        overlap=None,
        platforms=[
            ('r-isle-a', 246, 426, 320),          # 왼쪽 위 섬 (가로등, 화분)
            ('r-isle-lights', 598, 831, 363),     # 스트링 라이트와 벤치 섬
            ('r-isle-low', 427, 583, 508),        # 낮은 가로등 섬
            ('r-isle-lamp', 1013, 1151, 466),     # 가운데 가로등 섬
            ('r-isle-bench', 1299, 1524, 287),    # 오른쪽 위 벤치 섬
            ('r-tower-deck', 212, 366, 655),      # 전망대 난간 안 마루
            ('r-tower-roof', 208, 368, 567),      # 전망대 지붕 처마
            ('r-stairs', 1268, 1366, 715),        # 돌계단 꼭대기
        ],
        spawns=[
            ('r-ground-w', 'ground', 400, 1000, ['snail', 'golem'], 3),
            ('r-ground-e', 'ground', 1380, 1760, ['golem', 'snail'], 3),
            ('r-ground-mid', 'ground', 1000, 1250, ['snail'], 2),
            ('r-isle-a-slime', 'r-isle-a', 260, 410, ['slime'], 2),
            ('r-lights-shroom', 'r-isle-lights', 615, 815, ['mushroom', 'slime'], 3),
            ('r-low-shroom', 'r-isle-low', 440, 570, ['mushroom'], 2),
            ('r-lamp-slime', 'r-isle-lamp', 1025, 1140, ['slime'], 2),
            ('r-bench-bat', 'r-isle-bench', 1315, 1510, ['bat'], 3),
            ('r-tower-bat', 'r-tower-roof', 215, 360, ['bat'], 1),
        ],
        ropes=[
            ('r-rope-tower', 360, 'r-tower-deck', 'ground'),       # 전망대 마루 오른쪽 → 지면
            ('r-rope-isle-a', 256, 'r-isle-a', 'r-tower-roof'),    # 지붕 처마 왼쪽 → 왼쪽 위 섬
            ('r-rope-lights', 612, 'r-isle-lights', 'ground'),     # 스트링 라이트 섬 왼쪽 끝 → 지면 (바위 앞)
            ('r-rope-lamp', 1140, 'r-isle-lamp', 'ground'),        # 가운데 가로등 섬 → 지면
            ('r-rope-bench', 1330, 'r-isle-bench', 'r-stairs'),    # 돌계단 꼭대기 → 오른쪽 위 벤치 섬
        ],
        protect=[(0, 500, 200, 780)],     # 왼쪽 아래 벚나무 (위쪽 침엽수 꼭대기는 중앙 패널 벚나무 섬 뒤로 가려도 된다)
    ),
]

UPSCALE = 1.25          # 원본 px → 에셋 px (최대 1.25)
DENSITY = 1.5           # 에셋 px / 월드 단위 (계약)
SKY_PAD = 141.667       # 그림 위에 덧붙이는 하늘 (월드). groundY 가 정수(800)가 되도록 고른 값
OVERLAP = 120           # 패널 이음매 겹침 기본값 (원본 px). 패널 overlap 으로 바꿀 수 있다(앞 패널과의 겹침)
EDGE_FADE = 90          # 맵 양 끝 마감 폭 (에셋 px)
ROPE_REACH = 15         # 로프 아래끝을 서는 높이보다 이만큼 위에 (월드)
