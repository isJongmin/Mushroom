"""미리보기: python3 preview.py OUT_DIR [scale]
- frames.png: 모든 시트 전 프레임(확대, 체커 배경, 기준점 표시)
- sizes.png: 크기 비교(캐릭터 프레임 높이 기준선 포함)
- scene.png: 맵 배경 위 합성(1배, 2배 확대)
"""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def checker(w, h, s=8):
    im = Image.new('RGBA', (w, h), (236, 236, 242, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if (x // s + y // s) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=(214, 216, 226, 255))
    return im


def load(p):
    return Image.open(os.path.join(ROOT, p)).convert('RGBA')


def frames_png(man, out, sc):
    rows = []
    items = [(k, v) for k, v in man['mobs'].items()]
    items += [('ghost', man['ghost']), ('tombstone', man['tombstone']), ('dropBag', man['dropBag']), ('slash', man['fx']['slash'])]
    for k, v in items:
        sh = load(v['sheet'])
        fw, fh = v['frame']['w'], v['frame']['h']
        n = sh.width // fw
        row = checker(sh.width * sc + (n - 1) * 6, fh * sc)
        for i in range(n):
            f = sh.crop((i * fw, 0, (i + 1) * fw, fh)).resize((fw * sc, fh * sc), Image.NEAREST)
            x0 = i * (fw * sc + 6)
            row.alpha_composite(f, (x0, 0))
            d = ImageDraw.Draw(row)
            ax, ay = v['anchor']['x'] * sc + x0, v['anchor']['y'] * sc
            d.line([ax - 6, ay, ax + 6, ay], fill=(255, 0, 80, 255))
            d.line([ax, ay - 6, ax, ay + 6], fill=(255, 0, 80, 255))
            if 'size' in v and k in man['mobs']:
                w, h = v['size']['w'] * 1.5 * sc, v['size']['h'] * 1.5 * sc
                d.rectangle([ax - w / 2, ay - h, ax + w / 2, ay], outline=(0, 160, 255, 160))
        lab = Image.new('RGBA', (row.width, 16), (40, 36, 60, 255))
        ImageDraw.Draw(lab).text((4, 2), f'{k}  frame {fw}x{fh}  n={n}  anim={v.get("animations", "")}', fill=(255, 255, 255, 255))
        rows += [lab, row]
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows) + 4 * len(rows)
    im = Image.new('RGBA', (W, H), (60, 56, 80, 255))
    y = 0
    for r in rows:
        im.alpha_composite(r, (0, y))
        y += r.height + 4
    im.save(os.path.join(out, 'frames.png'))


def sizes_png(man, out, sc=2):
    av = load('assets/avatar/skin/' + sorted(os.listdir(os.path.join(ROOT, 'assets/avatar/skin')))[0]) if os.path.isdir(os.path.join(ROOT, 'assets/avatar/skin')) else None
    items = list(man['mobs'].items()) + [('ghost', man['ghost']), ('tombstone', man['tombstone'])]
    W = 60 + sum(v['frame']['w'] for _, v in items) + 160
    H = 230
    im = Image.new('RGBA', (W, H), (190, 228, 250, 255))
    d = ImageDraw.Draw(im)
    gy = 205
    d.rectangle([0, gy, W, H], fill=(110, 190, 80, 255))
    x = 20
    if av is not None:
        f = av.crop((0, 0, 144, 192))
        im.alpha_composite(f, (x, gy - 180))
        d.text((x + 40, gy + 8), 'avatar', fill=(0, 0, 0, 255))
        x += 120
    for k, v in items:
        sh = load(v['sheet'])
        fw, fh = v['frame']['w'], v['frame']['h']
        f = sh.crop((0, 0, fw, fh))
        lift = 60 if k == 'bat' else 0
        im.alpha_composite(f, (x, gy - v['anchor']['y'] - lift))
        d.text((x + 4, gy + 8), k, fill=(0, 0, 0, 255))
        x += fw + 4
    d.line([0, gy - 60 * 1.5, W, gy - 60 * 1.5], fill=(255, 255, 255, 120))
    im = im.resize((im.width * sc, im.height * sc), Image.LANCZOS)
    im.save(os.path.join(out, 'sizes.png'))


def scene_png(man, out):
    mm = json.load(open(os.path.join(ROOT, 'assets/map/manifest.json')))
    W, H = 1100, 330
    gy_world = mm['groundY']
    x0w = 300
    im = Image.new('RGBA', (W, H), (160, 220, 250, 255))
    for L in mm['layers']:
        try:
            lay = load(L['src'])
        except Exception:
            continue
        top = L['y'] * 1.5 - (gy_world * 1.5 - (H - 60))
        sx = int(x0w * 1.5 * L.get('parallax', 1)) % max(1, lay.width)
        crop = lay.crop((sx, 0, min(lay.width, sx + W), lay.height))
        if L.get('stretchX'):
            crop = lay.resize((W, lay.height))
        im.alpha_composite(crop, (0, int(top)))
    gy = H - 60
    pos = [('snail', 110, 0), ('mushroom', 260, 3), ('slime', 420, 1), ('bat', 560, 0), ('golem', 760, 1)]
    for k, x, fi in pos:
        v = man['mobs'][k]
        sh = load(v['sheet'])
        fw, fh = v['frame']['w'], v['frame']['h']
        f = sh.crop((fi * fw, 0, (fi + 1) * fw, fh))
        lift = 75 if k == 'bat' else 0
        im.alpha_composite(f, (x - v['anchor']['x'], gy - v['anchor']['y'] - lift))
    for k, x, fi in (('tombstone', 930, 0), ('ghost', 1010, 0), ('dropBag', 330, 0)):
        v = man[k]
        sh = load(v['sheet'])
        fw, fh = v['frame']['w'], v['frame']['h']
        f = sh.crop((fi * fw, 0, (fi + 1) * fw, fh))
        im.alpha_composite(f, (x - v['anchor']['x'], gy - v['anchor']['y']))
    v = man['fx']['slash']
    sh = load(v['sheet'])
    f = sh.crop((v['frame']['w'], 0, 2 * v['frame']['w'], v['frame']['h']))
    im.alpha_composite(f, (640 - v['anchor']['x'], gy - v['anchor']['y']))
    im.save(os.path.join(out, 'scene.png'))
    im.resize((W * 2, H * 2), Image.LANCZOS).crop((0, 100, 1200, 660)).save(os.path.join(out, 'scene_zoom.png'))


def main():
    out = sys.argv[1]
    sc = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    os.makedirs(out, exist_ok=True)
    man = json.load(open(os.path.join(ROOT, 'assets/mob/manifest.json'), encoding='utf-8'))
    frames_png(man, out, sc)
    sizes_png(man, out)
    scene_png(man, out)
    print('ok', out)


if __name__ == '__main__':
    main()
