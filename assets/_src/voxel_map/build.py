"""버섯마을 복셀 맵 빌드: 레이어별 복셀 장면을 조명 렌더해 assets/map/ 에 쓴다.

python3 assets/_src/voxel_map/build.py                 # 전체 (2코어)
python3 assets/_src/voxel_map/build.py --only ground   # 한 레이어만 (manifest는 기존 파일 크기로 갱신)
python3 assets/_src/voxel_map/build.py --preview DIR   # + 미리보기(preview.py)
"""
import os, sys, json, time, argparse
from multiprocessing import Pool
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'map')

from vox import Cfg, render_tiled, add_glow, lin2srgb, hex2lin
import scene
import layers_bg
import platforms

DENSITY = 1.5
GROUND_Y = 440
WORLD_W = 2400
PITCH = 15.0
WEBP = dict(format='WEBP', lossless=True, quality=100, method=6, exact=False)   # 무손실: 반복 이음매가 정확히 맞고 용량도 충분


def wrap_boxes(boxes, period_units):
    out = []
    for b in boxes:
        out.append(b)
        for k in (-1, 1):
            out.append(b.moved((k * period_units, 0, 0)))
    return out


LAYERS = [
    # name, parallax, y(월드, 레이어 윗변), repeatX, stretchX
    dict(name='sky', parallax=0.0, y=0, repeatX=False, stretchX=True),
    dict(name='clouds', parallax=0.12, y=10, repeatX=True, stretchX=False),
    dict(name='far', parallax=0.3, y=120, repeatX=True, stretchX=False),
    dict(name='mid', parallax=0.65, y=170, repeatX=True, stretchX=False),
    dict(name='ground', parallax=1.0, y=0, repeatX=False, stretchX=False),
]


def spec(name):
    """레이어 렌더 설정: (boxes, scale px/단위, W px, H px, anchor px, cfg, period px | None, glow)."""
    L = next(l for l in LAYERS if l['name'] == name)
    if name == 'ground':
        H = int((540 - L['y']) * DENSITY)
        ay = (GROUND_Y - L['y']) * DENSITY
        cfg = Cfg(ss=3, grid=1.0, sh_step=1.3, sh_n=100, bounce=1.9, sky=1.05)
        return dict(boxes=scene.ground(), scale=3.0, W=WORLD_W * 3 // 2, H=H, anchor=(0.0, ay), cfg=cfg, period=None,
                    glow=(6.0, 1.6, 20.0, 0.6), tile=200)
    return layers_bg.spec(name, L, DENSITY)


def render_layer(name, pool):
    s = spec(name)
    t = time.time()
    if s.get('image') is not None:
        im = s['image']
    else:
        boxes = s['boxes']
        if s['period']:
            boxes = wrap_boxes(boxes, s['period'] / s['scale'])
        rgba, em, ec = render_tiled(boxes, 0.0, PITCH, s['scale'], s['cfg'], W=s['W'], H=s['H'], anchor=s['anchor'],
                                    tile=s.get('tile', 200), pool=pool)
        if s.get('glow'):
            g = s['glow']
            rgba = add_glow(rgba, em, ec, g[0], g[1], g[2], g[3])
        if s.get('post'):
            rgba = s['post'](rgba)
        im = Image.fromarray(rgba, 'RGBA')
    print('%-7s %dx%d %.1fs' % (name, im.width, im.height, time.time() - t), flush=True)
    return im


def save(name, im):
    L = next(l for l in LAYERS if l['name'] == name)
    os.makedirs(OUT, exist_ok=True)
    if name == 'sky':
        fn = name + '.png'
        im.save(os.path.join(OUT, fn), optimize=True)
    else:
        fn = name + '.webp'
        im.save(os.path.join(OUT, fn), **WEBP)
    return fn


def write_manifest():
    man = dict(density=DENSITY, groundY=GROUND_Y, width=WORLD_W, layers=[])
    for L in LAYERS:
        fn = next(f for f in os.listdir(OUT) if os.path.splitext(f)[0] == L['name'])
        im = Image.open(os.path.join(OUT, fn))
        e = dict(name=L['name'], src='assets/map/' + fn, parallax=L['parallax'], y=L['y'],
                 w=round(im.width / DENSITY, 3), h=round(im.height / DENSITY, 3), repeatX=L['repeatX'])
        if L['stretchX']:
            e['stretchX'] = True
        man['layers'].append(e)
    # 발판 정본 (사이클 8): 월드 단위, y = 윗면 = 서는 높이. 한 방향 통과.
    man['platforms'] = [dict(id=p['id'], x1=p['x1'], x2=p['x2'], y=p['y']) for p in platforms.PLATFORMS]
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--preview')
    ap.add_argument('--raw', help='렌더 원본 PNG도 여기에 저장 (미리보기용)')
    a = ap.parse_args()
    names = a.only or [l['name'] for l in LAYERS]
    t0 = time.time()
    with Pool(2) as pool:
        for n in names:
            im = render_layer(n, pool)
            save(n, im)
            if a.raw:
                os.makedirs(a.raw, exist_ok=True)
                im.save(os.path.join(a.raw, n + '.png'))
    # 이전 블록 맵 PNG 정리
    keep = set()
    for L in LAYERS:
        for f in os.listdir(OUT):
            if os.path.splitext(f)[0] == L['name']:
                keep.add(f)
    for f in os.listdir(OUT):
        if f != 'manifest.json' and f not in keep:
            os.remove(os.path.join(OUT, f))
    for L in LAYERS:   # 같은 이름 다른 확장자 정리 (예: ground.png → ground.webp)
        fs = [f for f in os.listdir(OUT) if os.path.splitext(f)[0] == L['name']]
        want = L['name'] + ('.png' if L['name'] == 'sky' else '.webp')
        for f in fs:
            if f != want:
                os.remove(os.path.join(OUT, f))
    if all(any(os.path.splitext(f)[0] == L['name'] for f in os.listdir(OUT)) for L in LAYERS):
        write_manifest()
    print('total %.1fs' % (time.time() - t0))
    if a.preview:
        import preview
        preview.main(a.preview)


if __name__ == '__main__':
    main()
