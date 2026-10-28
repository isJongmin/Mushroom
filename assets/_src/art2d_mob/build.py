"""사이클 9 몬스터/전투 에셋 빌드.

python3 assets/_src/art2d_mob/build.py            # 전체
python3 assets/_src/art2d_mob/build.py snail bat  # 일부 몬스터만(manifest는 항상 갱신)

출력: assets/mob/<id>.png, ghost.png, tombstone.png, drop_bag.png, manifest.json, assets/fx/slash.png
"""
import json
import math
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MOB_DIR = os.path.join(ROOT, 'assets', 'mob')
FX_DIR = os.path.join(ROOT, 'assets', 'fx')

from vec import Canvas, puff, sparkle, twinkle  # noqa: E402
from mobs import MOBS  # noqa: E402
import extras  # noqa: E402

# 몬스터 정보(게임 수치). 속도 = 월드 단위/초. 드롭 id는 캐릭터 아트와 공유하는 목록.
INFO = {
    'snail': dict(name='달팽이', hp=25, speed=22, touchDamage=6, behavior='walk',
                  drops=[('hat:snail-shell', 0.18), ('shoes:snail-boots', 0.16)]),
    'mushroom': dict(name='주황버섯', hp=45, speed=48, touchDamage=9, behavior='hop',
                     drops=[('hat:mushroom-cap', 0.16), ('bottom:mushroom-shorts', 0.16)]),
    'slime': dict(name='슬라임', hp=60, speed=42, touchDamage=11, behavior='hop',
                  drops=[('top:slime-hood', 0.15), ('bottom:slime-pants', 0.15)]),
    'bat': dict(name='박쥐', hp=35, speed=70, touchDamage=10, behavior='fly',
                drops=[('top:bat-cape', 0.15), ('shoes:bat-boots', 0.15)]),
    'golem': dict(name='돌골렘', hp=220, speed=26, touchDamage=20, behavior='walk',
                  drops=[('hat:golem-helm', 0.2), ('top:golem-armor', 0.2), ('shoes:snail-boots', 0.1)]),
}
ORDER = ['snail', 'mushroom', 'slime', 'bat', 'golem']


def render(spec, fn):
    fw, fh = spec['frame']
    ax, ay = spec['anchor']
    c = Canvas(fw, fh, ax, ay)
    fn(c)
    return c


def die_frames(spec):
    """사망 4프레임: 쓰러짐 -> 흐려지며 연기/별 -> 연기 -> 반짝이만."""
    draw = spec['draw']
    w, h = spec['size']
    cy = -h * 0.5
    r = max(5.0, min(w, h) * 0.2)
    top = -spec['anchor'][1] / 1.5 + r * 0.7   # 프레임 위쪽 넘침 방지
    _sp, _tw = sparkle, twinkle

    def sparkle_(c, x, y, rr, a=1.0):
        _sp(c, x, max(y, top + rr * 0.3), rr, a)

    def twinkle_(c, x, y, rr, a=1.0, col='#FFFFFF'):
        _tw(c, x, max(y, top + rr * 0.3), rr, a, col)
    out = []

    def f0(c):
        draw(c, 'dead')
    out.append(render(spec, f0))

    def f1(c):
        b = c.blank()
        draw(b, 'dead')
        c.over(b, 0.55)
        puff(c, -w * 0.28, cy + h * 0.22, r * 0.85, 0.95)
        puff(c, w * 0.30, cy + h * 0.15, r * 0.75, 0.95)
        puff(c, 0.0, cy - h * 0.05, r * 0.95, 0.9)
        sparkle_(c, -w * 0.18, cy - h * 0.38, r * 0.5)
        sparkle_(c, w * 0.32, cy - h * 0.25, r * 0.42)
    out.append(render(spec, f1))

    def f2(c):
        b = c.blank()
        draw(b, 'dead')
        c.over(b, 0.18)
        puff(c, -w * 0.32, cy + h * 0.12, r * 1.05, 0.9)
        puff(c, w * 0.34, cy + h * 0.05, r * 0.95, 0.9)
        puff(c, 0.0, cy - h * 0.18, r * 1.15, 0.85)
        sparkle_(c, -w * 0.25, cy - h * 0.55, r * 0.46, 0.95)
        sparkle_(c, w * 0.38, cy - h * 0.45, r * 0.38, 0.95)
        twinkle_(c, w * 0.05, cy - h * 0.62, r * 0.55)
    out.append(render(spec, f2))

    def f3(c):
        puff(c, -w * 0.36, cy + h * 0.02, r * 1.2, 0.45)
        puff(c, w * 0.38, cy - h * 0.05, r * 1.05, 0.45)
        puff(c, 0.0, cy - h * 0.3, r * 1.25, 0.4)
        sparkle_(c, -w * 0.3, cy - h * 0.68, r * 0.36, 0.7)
        sparkle_(c, w * 0.42, cy - h * 0.6, r * 0.3, 0.7)
        twinkle_(c, w * 0.02, cy - h * 0.78, r * 0.45, 0.85)
        twinkle_(c, -w * 0.05, cy + h * 0.1, r * 0.35, 0.6)
    out.append(render(spec, f3))
    return out


def build_mob(mid):
    spec = MOBS[mid]
    frames = []
    n = spec['move']
    for i in range(n):
        frames.append(render(spec, lambda c, i=i: spec['draw'](c, 'move', i / n)))

    def hit(c):
        spec['draw'](c, 'hit')
        c.tint((1, 1, 1), 0.22)
    frames.append(render(spec, hit))
    frames += die_frames(spec)
    fw, fh = spec['frame']
    sheet = Image.new('RGBA', (fw * len(frames), fh), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f.image(), (i * fw, 0))
    sheet.save(os.path.join(MOB_DIR, f'{mid}.png'), optimize=True)
    return dict(move=list(range(n)), hit=[n], die=list(range(n + 1, n + 5))), len(frames)


def manifest():
    mobs = {}
    for mid in ORDER:
        spec, info = MOBS[mid], INFO[mid]
        n = spec['move']
        mobs[mid] = {
            'name': info['name'], 'hp': info['hp'], 'speed': info['speed'], 'touchDamage': info['touchDamage'],
            'size': {'w': spec['size'][0], 'h': spec['size'][1]},
            'anchor': {'x': spec['anchor'][0], 'y': spec['anchor'][1]},
            'frame': {'w': spec['frame'][0], 'h': spec['frame'][1]},
            'sheet': f'assets/mob/{mid}.png',
            'frames': n + 5,
            'animations': {'move': list(range(n)), 'hit': [n], 'die': list(range(n + 1, n + 5))},
            'fps': spec['fps'],
            'behavior': info['behavior'],
            'drops': [{'item': it, 'p': p} for it, p in info['drops']],
        }
    m = {
        'density': 1.5,
        'note': 'frame/anchor = 에셋 px(시트 좌표), size = 월드 단위 판정 상자(기준점 = 상자 아래 중앙). 기본 방향은 오른쪽, 왼쪽은 좌우 반전. hop은 뜀 높이가 프레임에 들어 있다.',
        'mobs': mobs,
    }
    m.update(extras.MANIFEST)
    with open(os.path.join(MOB_DIR, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main(argv):
    os.makedirs(MOB_DIR, exist_ok=True)
    os.makedirs(FX_DIR, exist_ok=True)
    want = [a for a in argv if a in MOBS] or ([] if argv else ORDER)
    for mid in want:
        anim, n = build_mob(mid)
        print(mid, n, 'frames', anim)
    if not argv or 'extras' in argv:
        extras.build(MOB_DIR, FX_DIR)
        print('extras ok')
    manifest()
    print('manifest ok')


if __name__ == '__main__':
    main(sys.argv[1:])
