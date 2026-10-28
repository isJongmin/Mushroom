"""버섯마을 사이클 9 맵 정본: 월드 크기, 발판(PLATFORMS), 몬스터 스폰(SPAWNS), 부활 지점(SPAWN).

build.py 가 manifest 의 platforms/spawns/spawn 을 이 표에서 그대로 쓰고,
layers.py 가 같은 값으로 발판 그림을 그린다. check.py 가 그림과 좌표를 대조한다.

좌표는 월드 단위. 발판 y = 윗면 = 서는 높이. 그림 px = 월드 x 1.5 (DENSITY).
층: 지면 900 → 810 → 720 → 630 → 540 → 450 (간격 90). 슈퍼 점프 전용 층은 330.
kind: grass(떠 있는 잔디 흙 발판) | plank(나무 판자 발판) | bridge(밧줄 흔들다리)
      | deck(기둥 받친 나무 데크, 마을) | sky(슈퍼 점프 전용 작은 하늘섬)
"""

WORLD_W = 4800
WORLD_H = 1000
GROUND_Y = 900
DENSITY = 1.5
SPAWN = {'x': 2400, 'y': 900}

PLATFORMS = [
    # 서쪽 들판 (헤네시스)
    dict(id='w1', kind='grass', x1=140, x2=400, y=810),
    dict(id='w2', kind='grass', x1=330, x2=590, y=720),
    dict(id='w3', kind='plank', x1=120, x2=360, y=630),
    dict(id='w4', kind='grass', x1=290, x2=560, y=540),
    dict(id='w5', kind='grass', x1=700, x2=980, y=810),
    dict(id='w6', kind='plank', x1=880, x2=1170, y=720),
    dict(id='w7', kind='grass', x1=740, x2=980, y=630),
    dict(id='w8', kind='bridge', x1=960, x2=1360, y=540),
    dict(id='w9', kind='grass', x1=1180, x2=1420, y=450),
    dict(id='w10', kind='grass', x1=1260, x2=1500, y=810),
    dict(id='w-sky', kind='sky', x1=1460, x2=1580, y=330, secret=True),
    # 마을 (중앙, 몬스터 없음)
    dict(id='t1', kind='deck', x1=1700, x2=1900, y=810),
    dict(id='t2', kind='deck', x1=1830, x2=2040, y=720),
    dict(id='tc1', kind='plank', x1=2190, x2=2370, y=810),
    dict(id='tc2', kind='plank', x1=2320, x2=2560, y=720),
    dict(id='tc3', kind='grass', x1=2170, x2=2390, y=630),
    dict(id='tc4', kind='plank', x1=2340, x2=2600, y=540),
    dict(id='t3', kind='deck', x1=2780, x2=2980, y=810),
    dict(id='t4', kind='deck', x1=2650, x2=2850, y=720),
    # 동쪽 숲 (엘리니아)
    dict(id='e1', kind='grass', x1=3240, x2=3520, y=810),
    dict(id='e2', kind='plank', x1=3420, x2=3700, y=720),
    dict(id='e3', kind='grass', x1=3240, x2=3490, y=630),
    dict(id='e4', kind='plank', x1=3410, x2=3700, y=540),
    dict(id='e5', kind='grass', x1=3630, x2=3880, y=450),
    dict(id='e-sky', kind='sky', x1=3950, x2=4070, y=330, secret=True),
    dict(id='e6', kind='grass', x1=3860, x2=4140, y=810),
    dict(id='e7', kind='bridge', x1=4000, x2=4420, y=720),
    dict(id='e8', kind='grass', x1=4300, x2=4560, y=630),
    dict(id='e9', kind='plank', x1=4420, x2=4720, y=540),
    dict(id='e10', kind='grass', x1=4500, x2=4760, y=810),
]

# 몬스터 스폰 구역 (사이클 9 계약). 마을(x 1600~3200)에는 두지 않는다.
SPAWNS = [
    dict(id='field-west', platform='ground', x1=120, x2=1520, mobs=['snail'], max=5),
    dict(id='forest-east', platform='ground', x1=3260, x2=4740, mobs=['golem', 'snail'], max=4),
    dict(id='w2-slime', platform='w2', x1=345, x2=575, mobs=['slime'], max=2),
    dict(id='w5-shroom', platform='w5', x1=715, x2=965, mobs=['mushroom', 'slime'], max=3),
    dict(id='w6-shroom', platform='w6', x1=895, x2=1155, mobs=['mushroom'], max=2),
    dict(id='w8-bat', platform='w8', x1=980, x2=1340, mobs=['bat'], max=2),
    dict(id='e2-shroom', platform='e2', x1=3435, x2=3685, mobs=['mushroom'], max=2),
    dict(id='e6-mix', platform='e6', x1=3875, x2=4125, mobs=['mushroom', 'slime'], max=3),
    dict(id='e7-slime', platform='e7', x1=4020, x2=4400, mobs=['slime'], max=2),
    dict(id='e5-bat', platform='e5', x1=3645, x2=3865, mobs=['bat'], max=2),
    dict(id='e9-bat', platform='e9', x1=4435, x2=4705, mobs=['bat'], max=2),
]

MOB_IDS = ('snail', 'mushroom', 'slime', 'bat', 'golem')


def px(v):
    return v * DENSITY
