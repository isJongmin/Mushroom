"""미리보기: 프런트 drawLayer 와 같은 규칙으로 레이어를 합성한다.

python3 assets/_src/art2d_map/preview.py OUTDIR [--platforms]
- overview.png : 월드 전체(4800x1000)를 카메라가 지나가며 본 모습을 이어 붙인 축소본(가로 2400)
- crop_*.png   : 실제 배율(P=3, 에셋 1:1) 화면 1920x1080 = 월드 1280x720 시야 3곳
--platforms    : 발판 서는 선(빨강)과 스폰 구역(색 띠)을 겹쳐 그린다(검증용 사본 *_dbg.png 도)
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def load(mapdir=None):
    mapdir = mapdir or os.path.join(ROOT, 'assets', 'map')
    m = json.load(open(os.path.join(mapdir, 'manifest.json')))
    layers = []
    for l in m['layers']:
        im = Image.open(os.path.join(mapdir, os.path.basename(l['src']))).convert('RGBA')
        layers.append((l, im))
    return m, layers


def view(m, layers, camX, camY, Ww, Hw, k=1.5):
    """시야(월드 Ww x Hw, 왼쪽 위 camX, camY)를 배율 k(px/월드)로 그린다."""
    Wd, Hd = int(round(Ww * k)), int(round(Hw * k))
    out = Image.new('RGBA', (Wd, Hd), (110, 198, 245, 255))
    for (l, im) in layers:
        dens = m['density']
        lw, lh = im.width / dens, im.height / dens
        y0 = round((l['y'] - camY) * k)
        y1 = round((l['y'] + lh - camY) * k)
        if l.get('stretchX'):
            if y0 > 0:
                out.alpha_composite(im.crop((0, 0, im.width, 1)).resize((Wd, y0)), (0, 0))
            out.alpha_composite(im.resize((Wd, y1 - y0), Image.BILINEAR), (0, y0))
            continue
        tw = lw * k
        start = -camX * l['parallax'] * k
        xs = []
        if l.get('repeatX'):
            start %= tw
            if start > 0:
                start -= tw
            i = 0
            while start + i * tw < Wd:
                xs.append((round(start + i * tw), round(start + (i + 1) * tw)))
                i += 1
        else:
            xs.append((round(start), round(start + tw)))
        for (xa, xb) in xs:
            if xb <= 0 or xa >= Wd:
                continue
            # 보이는 부분만 잘라 리사이즈
            sx0 = max(0, -xa) / (xb - xa) * im.width
            sx1 = (min(Wd, xb) - xa) / (xb - xa) * im.width
            dx0 = max(0, xa)
            dx1 = min(Wd, xb)
            src = im.crop((int(sx0), 0, int(np.ceil(sx1)), im.height))
            if k == dens and abs((dx1 - dx0) - src.width) <= 1 and (y1 - y0) == im.height:
                piece = src.crop((0, 0, dx1 - dx0, im.height)) if src.width >= dx1 - dx0 else src.resize((dx1 - dx0, y1 - y0))
            else:
                piece = src.resize((dx1 - dx0, y1 - y0), Image.LANCZOS)
            out.alpha_composite(piece, (dx0, y0))
    return out


def overlay(img, m, camX, camY, k):
    d = ImageDraw.Draw(img)
    for p in m['platforms']:
        y = (p['y'] - camY) * k
        d.line([((p['x1'] - camX) * k, y), ((p['x2'] - camX) * k, y)], fill=(255, 0, 0, 255), width=1)
    cols = {'snail': (255, 200, 0), 'mushroom': (255, 120, 0), 'slime': (0, 200, 255), 'bat': (160, 0, 255), 'golem': (120, 120, 120)}
    plat = {p['id']: p for p in m['platforms']}
    for s in m['spawns']:
        y = m['groundY'] if s['platform'] == 'ground' else plat[s['platform']]['y']
        c = cols[s['mobs'][0]]
        d.rectangle([((s['x1'] - camX) * k, (y - 30 - camY) * k), ((s['x2'] - camX) * k, (y - 26 - camY) * k)], fill=c + (255,))
    sp = m['spawn']
    d.ellipse([((sp['x'] - camX) * k - 6, (sp['y'] - camY) * k - 6), ((sp['x'] - camX) * k + 6, (sp['y'] - camY) * k + 6)], outline=(255, 255, 255, 255), width=3)


CROPS = [('west', 160, 280), ('town', 1760, 280), ('east', 3320, 230)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--platforms', action='store_true')
    ap.add_argument('--map', default=None, help='맵 폴더 (기본 assets/map)')
    ap.add_argument('--k', type=float, default=1.5, help='크롭 배율 px/월드 (1.5 = P3 에셋 1:1, 1.0 = P2)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    m, layers = load(a.map)
    W, Hw = m['width'], m['height']
    # 전체 축소본: 모든 레이어를 parallax 없이(카메라 0) 월드 전체 폭으로 펼쳐 합성(축소 0.5)
    k = 0.5
    flat = [(dict(l, parallax=0.0) if not l.get('stretchX') else l, im) for (l, im) in layers]
    full = view(m, flat, 0, 0, W, Hw, k)
    full.convert('RGB').save(os.path.join(a.out, 'overview.png'))
    if a.platforms:
        dbg = full.copy()
        overlay(dbg, m, 0, 0, k)
        dbg.convert('RGB').save(os.path.join(a.out, 'overview_dbg.png'))
    for (name, cx, cy) in CROPS:
        vw, vh = 1920 / a.k if a.k == 1.5 else 1280 / a.k, 1080 / a.k if a.k == 1.5 else 720 / a.k
        v = view(m, layers, cx, cy, vw, vh, a.k)
        v.convert('RGB').save(os.path.join(a.out, f'crop_{name}.png'))
        if a.platforms:
            overlay(v, m, cx, cy, a.k)
            v.convert('RGB').save(os.path.join(a.out, f'crop_{name}_dbg.png'))
    print('ok', a.out)


if __name__ == '__main__':
    main()
