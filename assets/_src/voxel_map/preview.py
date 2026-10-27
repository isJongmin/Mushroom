"""미리보기 (사이클 8).

python3 assets/_src/voxel_map/preview.py OUTDIR [--ref 시안.png]
  map_full.png         전체 맵(시차 없이) 축소. --ref 를 주면 시안을 왼쪽에 나란히.
  view_desktop.png     1280x540(P=2) 화면 3곳 (시차 적용)
  platforms_debug.png  manifest platforms 를 빨간 선으로 겹친 전체 맵 + 확대 띠
  with_char.png        assets/avatar 프리셋 캐릭터를 지면과 발판 여러 층에 세운 화면 2개 (P=2)
  with_char_p3.png     같은 장면 P=3(에셋 1:1) 확대
"""
import os, sys, json, argparse
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def load():
    man = json.load(open(os.path.join(ROOT, 'assets', 'map', 'manifest.json'), encoding='utf-8'))
    layers = [(l, Image.open(os.path.join(ROOT, l['src'])).convert('RGBA')) for l in man['layers']]
    return man, layers


def compose(man, layers, camx, vw, vh=540, k=1.0, parallax=True):
    """월드 단위 화면(vw x vh)을 배율 k(화면 px / 월드 단위)로 합성."""
    D = man['density']
    out = Image.new('RGBA', (round(vw * k), round(vh * k)), (0, 0, 0, 255))
    for l, im in layers:
        s = k / D
        if l.get('stretchX'):
            sim = im.resize((out.width, round(im.height * s)), Image.BILINEAR)
            out.alpha_composite(sim, (0, round(l['y'] * k)))
            continue
        sim = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        par = l['parallax'] if parallax else 1.0
        ox = round(-camx * par * k)
        y = round(l['y'] * k)
        xs = []
        if l['repeatX']:
            w = sim.width
            x = ox % w - w
            while x < out.width:
                xs.append(x); x += w
        else:
            xs = [ox]
        for x in xs:
            c = sim.crop((max(0, -x), 0, min(sim.width, out.width - x), sim.height))
            if c.width > 0:
                out.alpha_composite(c, (max(0, x), y))
    return out


# ---------------------------------------------------------------- 아바타 합성 (manifest layerOrder)
def avatar_sheet(avatar):
    am = json.load(open(os.path.join(ROOT, 'assets', 'avatar', 'manifest.json'), encoding='utf-8'))
    acc = None
    for e in am['layerOrder']:
        pid = avatar.get(e['part'])
        p = os.path.join(ROOT, 'assets', 'avatar', e['layer'], '%s.png' % pid)
        if not pid or not os.path.exists(p):
            continue
        src = np.asarray(Image.open(p).convert('RGBA')).astype(float) / 255
        if acc is None:
            acc = np.zeros_like(src)
        sa = src[..., 3:4]
        if e['blend'] == 'source-atop':
            acc[..., :3] = src[..., :3] * sa + acc[..., :3] * (1 - sa)
        else:
            da = acc[..., 3:4]
            oa = sa + da * (1 - sa)
            acc[..., :3] = np.where(oa > 0, (src[..., :3] * sa + acc[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
            acc[..., 3:4] = oa
    return Image.fromarray(np.round(acc * 255).astype(np.uint8), 'RGBA'), am


def presets():
    am = json.load(open(os.path.join(ROOT, 'assets', 'avatar', 'manifest.json'), encoding='utf-8'))
    return [avatar_sheet(p['avatar'])[0] for p in am['presets']], am


def put_char(img, sheet, am, frame, wx, wy, k, camx=0, flip=False):
    fw, fh = am['frame']['w'], am['frame']['h']
    ax, ay = am['anchor']['x'], am['anchor']['y']
    D = am['density']
    fr = sheet.crop((fw * frame, 0, fw * frame + fw, fh))
    if flip:
        fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
    s = k / D
    fr = fr.resize((round(fw * s), round(fh * s)), Image.LANCZOS)
    sx = (wx - camx) * k
    sh = Image.new('RGBA', (round(44 * k), round(10 * k)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(26, 22, 38, 64))
    img.alpha_composite(sh, (round(sx - 22 * k), round((wy - 5) * k)))
    img.alpha_composite(fr, (round(sx - ax * s), round(wy * k - ay * s)))


def draw_platforms(img, man, k, camx=0, label=True):
    d = ImageDraw.Draw(img)
    for p in man.get('platforms', []):
        x1, x2, y = (p['x1'] - camx) * k, (p['x2'] - camx) * k, p['y'] * k
        d.line((x1, y, x2, y), fill=(255, 0, 0, 255), width=max(1, round(k)))
        d.line((x1, y - 4 * k, x1, y + 4 * k), fill=(255, 0, 0, 255), width=1)
        d.line((x2, y - 4 * k, x2, y + 4 * k), fill=(255, 0, 0, 255), width=1)
        if label:
            d.text((x1 + 2, y + 3), '%s y%d' % (p['id'], p['y']), fill=(255, 255, 255, 255), stroke_width=2,
                   stroke_fill=(120, 0, 0, 255))
    gy = man['groundY'] * k
    d.line((0, gy, img.width, gy), fill=(255, 0, 0, 160), width=1)


def main(outdir, ref=None):
    os.makedirs(outdir, exist_ok=True)
    man, layers = load()
    full = compose(man, layers, 0, man['width'], k=0.5, parallax=False)
    if ref:
        r = Image.open(ref).convert('RGBA')
        r = r.resize((round(r.width * full.height / r.height), full.height), Image.LANCZOS)
        both = Image.new('RGBA', (r.width + 8 + full.width, full.height), (20, 18, 30, 255))
        both.alpha_composite(r, (0, 0)); both.alpha_composite(full, (r.width + 8, 0))
        both.convert('RGB').save(os.path.join(outdir, 'map_full.png'))
    else:
        full.convert('RGB').save(os.path.join(outdir, 'map_full.png'))
    # 화면 3곳
    cams = (0, 560, 1120)
    vd = Image.new('RGBA', (1280, 540 * 3 + 16), (20, 18, 30, 255))
    for i, c in enumerate(cams):
        vd.alpha_composite(compose(man, layers, c, 1280, k=1.0), (0, i * 548))
    vd.convert('RGB').save(os.path.join(outdir, 'view_desktop.png'))
    # 발판 디버그
    dbg = compose(man, layers, 0, man['width'], k=0.75, parallax=False)
    draw_platforms(dbg, man, 0.75)
    dbg.convert('RGB').save(os.path.join(outdir, 'platforms_debug.png'))
    zoom = []
    for p in man.get('platforms', []):
        cx = (p['x1'] + p['x2']) / 2
        x0 = max(0, min(man['width'] - 260, cx - 130))
        v = compose(man, layers, x0, 260, k=2.0, parallax=False).crop((0, round((p['y'] - 70) * 2), 520,
                                                                        round((p['y'] + 40) * 2)))
        d = ImageDraw.Draw(v)
        y = 140
        d.line(((p['x1'] - x0) * 2, y, (p['x2'] - x0) * 2, y), fill=(255, 0, 0, 255), width=1)
        d.text((4, 4), p['id'], fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        zoom.append(v)
    if zoom:
        cols = 5
        rows = (len(zoom) + cols - 1) // cols
        zs = Image.new('RGBA', (cols * 524, rows * 224), (20, 18, 30, 255))
        for i, v in enumerate(zoom):
            zs.alpha_composite(v, ((i % cols) * 524, (i // cols) * 224))
        zs.convert('RGB').save(os.path.join(outdir, 'platforms_zoom.png'))
    # 캐릭터
    sheets, am = presets()
    P = {p['id']: p for p in man.get('platforms', [])}

    def on(pid, t):
        p = P[pid]
        return p['x1'] + (p['x2'] - p['x1']) * t, p['y']
    scenes = [
        (0, [('g', 70, 440), on('shelf-left', 0.4), on('red-cap', 0.5), on('isle-cherry', 0.55), on('secret-sky', 0.5),
             ('g', 700, 440), on('orange-cap', 0.25), on('rope-bridge', 0.12)]),
        (1100, [on('rope-bridge', 0.7), on('isle-falls', 0.4), on('secret-chest', 0.5), on('blue-cap', 0.5),
                on('cliff-right', 0.3), ('g', 1480, 440), on('cliff-right', 0.85), ('g', 2240, 440)]),
    ]
    wc = Image.new('RGBA', (1280, 540 * 2 + 8), (20, 18, 30, 255))
    for i, (cam, pts) in enumerate(scenes):
        v = compose(man, layers, cam, 1280, k=1.0)
        for j, pt in enumerate(pts):
            wx, wy = (pt[1], pt[2]) if pt[0] == 'g' else pt
            put_char(v, sheets[(j + i * 3) % len(sheets)], am, (2, 0, 2, 3, 0, 2, 5, 2)[j % 8], wx, wy, 1.0, cam,
                     flip=(j % 3 == 1))
        wc.alpha_composite(v, (0, i * 548))
    wc.convert('RGB').save(os.path.join(outdir, 'with_char.png'))
    v3 = compose(man, layers, 180, 853, k=1.5)
    for j, pt in enumerate([on('shelf-left', 0.6), on('red-cap', 0.3), on('isle-cherry', 0.5), ('g', 560, 440),
                            on('secret-sky', 0.6), on('orange-cap', 0.5)]):
        wx, wy = (pt[1], pt[2]) if pt[0] == 'g' else pt
        put_char(v3, sheets[j % len(sheets)], am, (2, 0, 4, 2, 0, 2)[j], wx, wy, 1.5, 180, flip=(j == 1))
    v3.convert('RGB').save(os.path.join(outdir, 'with_char_p3.png'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--ref')
    a = ap.parse_args()
    main(a.out, a.ref)
