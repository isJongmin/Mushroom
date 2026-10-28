"""사이클 10 fx 규격(순수 데이터). fx/build.py와 art2d_mob/build.py가 함께 쓴다."""

BUFFS = ['range', 'multi', 'element', 'power', 'speed']   # 순서 고정(구슬 시트 프레임 순서)

ICON = 64           # 아이콘 64x64
ORB = 48            # 구슬 프레임 48x48
SLASH = dict(frame=(150, 135), anchor=(24, 128))   # slash.png와 같음

# 몬스터별 버프 드롭 확률 / 개수(계약: ARCHITECTURE 사이클 10)
BUFF_DROP = {'snail': 0.35, 'bat': 0.4, 'mushroom': 0.45, 'slime': 0.5, 'golem': 1.0}
BUFF_DROP_COUNT = {'golem': 2}

_SLASH_NOTE = '기준점 = 공격자 발 위치. 오른쪽 공격 기준, 왼쪽은 좌우 반전. slash와 같은 규격·같은 호, 색만 다르다.'


def _slash_entry(name, el):
    return {
        'sheet': f'assets/fx/{name}.png', 'frame': {'w': SLASH['frame'][0], 'h': SLASH['frame'][1]},
        'anchor': {'x': SLASH['anchor'][0], 'y': SLASH['anchor'][1]}, 'frames': 2, 'fps': 16,
        'element': el, 'note': _SLASH_NOTE,
    }


FX_MANIFEST = {
    'buffOrb': {
        'sheet': 'assets/fx/buff_orb.png', 'frame': {'w': ORB, 'h': ORB}, 'anchor': {'x': ORB // 2, 'y': ORB // 2},
        'frames': len(BUFFS), 'order': BUFFS,
        'note': '정적 시트, 프레임 i = order[i]. 기준점 = 구슬 중심. 구슬 지름 약 28px(월드 약 19), 바깥은 글로우. 위아래 흔들림은 프런트가 처리. 좌우 반전하지 않는다.',
    },
    'buffIcons': {
        'dir': 'assets/fx/buff', 'pattern': 'assets/fx/buff/{id}.png', 'size': {'w': ICON, 'h': ICON},
        'ids': BUFFS,
        'note': '64x64 투명 배경 원형 배지(지름 약 62). HUD에서 32~40px로 축소 표시해도 읽히게 그렸다.',
    },
    'slashFire': _slash_entry('slash_fire', 1),
    'slashIce': _slash_entry('slash_ice', 2),
    'slashBolt': _slash_entry('slash_bolt', 3),
}
