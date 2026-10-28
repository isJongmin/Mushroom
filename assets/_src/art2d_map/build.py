"""버섯마을 사이클 9 맵 빌드: 레이어 렌더 → assets/map/*.webp, sky.png, manifest.json.

python3 assets/_src/art2d_map/build.py [--only ground,mid] [--jobs 2]
결정적: 장면은 고정 시드, 렌더는 타일 독립, WebP 는 고정 옵션.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'map')

import layers as L  # noqa: E402
from vec import render, to_rgba8, hexc  # noqa: E402
from platforms import PLATFORMS, SPAWNS, SPAWN, WORLD_W, WORLD_H, GROUND_Y, DENSITY  # noqa: E402

WEBP = dict(format='WEBP', quality=90, method=6, alpha_quality=100, exact=False)
OLD_FILES = ('clouds.webp', 'far.webp', 'mid.webp', 'ground.webp', 'sky.png')


def sky_png(path):
    h = int(WORLD_H * DENSITY)
    ys = np.arange(h) + 0.5
    st = L.SKY_STOPS
    col = np.stack([np.interp(ys, [a for a, _ in st], [hexc(c)[i] for _, c in st]) for i in range(3)], -1)
    # 아주 약한 디더(밴딩 방지, 결정적)
    rng = np.random.default_rng(7)
    img = np.repeat(col[:, None, :], 16, 1) + rng.uniform(-0.5, 0.5, (h, 16, 1)) / 255.0
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(path, optimize=True)


def haze_post(rgba, t, to='#CDEBFA'):
    if t <= 0:
        return rgba
    c = hexc(to) * 255
    o = rgba.astype(np.float32)
    o[..., :3] = o[..., :3] * (1 - t) + c * t
    return (o + 0.5).astype(np.uint8)


def build_layer(name, jobs):
    spec = L.LAYERS[name]
    t = time.time()
    sc = getattr(L, 'build_' + name)()
    pm = render(sc, tile=320, jobs=jobs)
    rgba = to_rgba8(pm)
    rgba = haze_post(rgba, spec['haze'])
    # 완전 투명 픽셀 색은 0 으로 (용량, 결정성)
    rgba[rgba[..., 3] == 0] = 0
    path = os.path.join(OUT, name + '.webp')
    Image.fromarray(rgba, 'RGBA').save(path, **WEBP)
    print(f'{name}: {rgba.shape[1]}x{rgba.shape[0]} ops={len(sc.ops)} {time.time() - t:.1f}s {os.path.getsize(path) / 1024:.0f} KB')
    return rgba


def manifest():
    layers = [dict(name='sky', src='assets/map/sky.png', parallax=0.0, y=0, w=round(16 / DENSITY, 3), h=WORLD_H,
                   repeatX=False, stretchX=True)]
    for name in ('clouds', 'far', 'mid', 'ground'):
        sp = L.LAYERS[name]
        layers.append(dict(name=name, src=f'assets/map/{name}.webp', parallax=sp['parallax'], y=sp['y'],
                           w=round(sp['w'] / DENSITY, 3), h=round(sp['h'] / DENSITY, 3), repeatX=sp['repeat']))
    return {
        'density': DENSITY,
        'width': WORLD_W,
        'height': WORLD_H,
        'groundY': GROUND_Y,
        'spawn': dict(SPAWN),
        'layers': layers,
        'platforms': [dict(id=p['id'], x1=p['x1'], x2=p['x2'], y=p['y']) for p in PLATFORMS],
        'spawns': [dict(id=s['id'], platform=s['platform'], x1=s['x1'], x2=s['x2'], mobs=list(s['mobs']), max=s['max']) for s in SPAWNS],
    }


def write_manifest():
    m = manifest()
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write('\n')
    # manifest 에 없는 옛 파일 정리
    keep = {os.path.basename(l['src']) for l in m['layers']} | {'manifest.json'}
    for fn in os.listdir(OUT):
        if fn not in keep:
            os.remove(os.path.join(OUT, fn))
            print('removed', fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--jobs', type=int, default=2)
    a = ap.parse_args()
    names = [n for n in a.only.split(',') if n] or ['sky', 'clouds', 'far', 'mid', 'ground']
    os.makedirs(OUT, exist_ok=True)
    for n in names:
        if n == 'sky':
            sky_png(os.path.join(OUT, 'sky.png'))
        else:
            build_layer(n, a.jobs)
    write_manifest()
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(f'total {total / 1024 / 1024:.2f} MB')


if __name__ == '__main__':
    main()
