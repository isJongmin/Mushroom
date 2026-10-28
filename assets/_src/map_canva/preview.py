"""미리보기 (사이클 10, Canva 그림 맵).

python3 assets/_src/map_canva/preview.py MAPDIR OUTDIR [--k 1.0]
  MAPDIR: build.py --out 결과 폴더 (manifest.json 의 src 는 파일 이름만 사용)
  view_<n>.png        1280x720 게임 화면(시차 적용, 카메라는 world.js 와 같은 규칙)
  view_<n>_debug.png  같은 화면 + 발판 빨간 선, 지면선, 스폰 구역(주황), 로프 파란 선
  view_<n>_chars.png  같은 화면 + 프리셋 캐릭터와 몬스터
  map_full.png        전체 축소 + 발판 선
"""
import os, sys, json, argparse
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def load(mapdir):
    man = json.load(open(os.path.join(mapdir, 'manifest.json'), encoding='utf-8'))
    layers = [(l, Image.open(os.path.join(mapdir, os.path.basename(l['src']))).convert('RGBA')) for l in man['layers']]
    return man, layers


def compose(man, layers, camx, camy, vw, vh, k):
    D = man['density']
    out = Image.new('RGBA', (round(vw * k), round(vh * k)), (0, 0, 0, 255))
    for l, im in layers:
        s = k / D
        y0 = round((l['y'] - camy) * k)
        if l.get('stretchX'):
            sim = im.resize((out.width, round(im.height * s)), Image.BILINEAR)
            out.alpha_composite(sim.crop((0, max(0, -y0), sim.width, sim.height)), (0, max(0, y0)))
            continue
        sim = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        ox = round(-camx * l['parallax'] * k)
        xs = []
        if l['repeatX']:
            x = ox % sim.width - sim.width
            while x < out.width:
                xs.append(x); x += sim.width
        else:
            xs = [ox]
        for x in xs:
            c = sim.crop((max(0, -x), max(0, -y0), min(sim.width, out.width - x), sim.height))
            if c.width > 0 and c.height > 0:
                out.alpha_composite(c, (max(0, x), max(0, y0)))
    return out


# ---------------------------------------------------------------- 캐릭터 / 몬스터
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
        if e.get('blend') == 'source-atop':
            acc[..., :3] = src[..., :3] * sa + acc[..., :3] * (1 - sa)
        else:
            da = acc[..., 3:4]
            oa = sa + da * (1 - sa)
            acc[..., :3] = np.where(oa > 0, (src[..., :3] * sa + acc[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
            acc[..., 3:4] = oa
    return Image.fromarray(np.round(acc * 255).astype(np.uint8), 'RGBA'), am


def shadow(img, sx, sy, k, w=44):
    sh = Image.new('RGBA', (round(w * k), round(10 * k)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(40, 26, 20, 64))
    img.alpha_composite(sh, (round(sx - w / 2 * k), round(sy - 5 * k)))


def put_char(img, sheet, am, frame, wx, wy, k, camx, camy, flip=False):
    fw, fh = am['frame']['w'], am['frame']['h']
    ax, ay = am['anchor']['x'], am['anchor']['y']
    fr = sheet.crop((fw * frame, 0, fw * frame + fw, fh))
    if flip:
        fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
    s = k / am['density']
    fr = fr.resize((round(fw * s), round(fh * s)), Image.LANCZOS)
    sx, sy = (wx - camx) * k, (wy - camy) * k
    shadow(img, sx, sy, k)
    img.alpha_composite(fr, (round(sx - ax * s), round(sy - ay * s)))


def put_mob(img, mm, kind, frame, wx, wy, k, camx, camy, flip=False):
    m = mm['mobs'][kind]
    sheet = Image.open(os.path.join(ROOT, m['sheet'])).convert('RGBA')
    fw, fh = m['frame']['w'], m['frame']['h']
    fr = sheet.crop((fw * frame, 0, fw * frame + fw, fh))
    if flip:
        fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
    s = k / mm['density']
    fr = fr.resize((max(1, round(fw * s)), max(1, round(fh * s))), Image.LANCZOS)
    sx, sy = (wx - camx) * k, (wy - camy) * k
    if m.get('behavior') != 'fly':
        shadow(img, sx, sy, k, m['size']['w'])
    img.alpha_composite(fr, (round(sx - m['anchor']['x'] * s), round(sy - m['anchor']['y'] * s)))


def debug_overlay(img, man, k, camx, camy):
    d = ImageDraw.Draw(img)
    plat = {p['id']: p for p in man['platforms']}
    for s in man.get('spawns', []):
        y = man['groundY'] if s['platform'] == 'ground' else plat[s['platform']]['y']
        d.rectangle(((s['x1'] - camx) * k, (y - 6 - camy) * k, (s['x2'] - camx) * k, (y - 2 - camy) * k),
                    fill=(255, 150, 0, 255))
    for p in man['platforms']:
        x1, x2, y = (p['x1'] - camx) * k, (p['x2'] - camx) * k, (p['y'] - camy) * k
        d.line((x1, y, x2, y), fill=(255, 0, 0, 255), width=2)
        d.line((x1, y - 5, x1, y + 5), fill=(255, 0, 0, 255), width=2)
        d.line((x2, y - 5, x2, y + 5), fill=(255, 0, 0, 255), width=2)
        d.text((x1 + 3, y + 4), '%s y%d' % (p['id'], p['y']), fill=(255, 255, 255, 255), stroke_width=2,
               stroke_fill=(140, 0, 0, 255))
    for r in man.get('ropes', []):
        x, y1, y2 = (r['x'] - camx) * k, (r['y1'] - camy) * k, (r['y2'] - camy) * k
        d.line((x, y1, x, y2), fill=(30, 110, 255, 255), width=3)
        d.line((x - 6, y2, x + 6, y2), fill=(30, 110, 255, 255), width=2)
        d.text((x + 6, (y1 + y2) / 2), r['id'], fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 50, 160, 255))
    gy = (man['groundY'] - camy) * k
    d.line((0, gy, img.width, gy), fill=(255, 0, 0, 255), width=1)
    sp = man['spawn']
    d.ellipse(((sp['x'] - camx) * k - 5, (sp['y'] - camy) * k - 5, (sp['x'] - camx) * k + 5, (sp['y'] - camy) * k + 5),
              outline=(0, 120, 255, 255), width=2)


def views(man, vw):
    W = man['width']
    mx = max(0, W - vw)
    return [('west', 0), ('center', mx / 2), ('east', mx)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mapdir'); ap.add_argument('outdir')
    ap.add_argument('--k', type=float, default=1.0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    man, layers = load(a.mapdir)
    k = a.k
    vw, vh = 1280 / k, 720 / k
    camy = max(0, man['height'] - vh)          # world.js camYTarget: 지면 근처 = 화면 아래 끝이 월드 아래 끝
    mm = json.load(open(os.path.join(ROOT, 'assets', 'mob', 'manifest.json'), encoding='utf-8'))
    am = json.load(open(os.path.join(ROOT, 'assets', 'avatar', 'manifest.json'), encoding='utf-8'))
    sheets = [avatar_sheet(p['avatar'])[0] for p in am['presets']]
    plat = {p['id']: p for p in man['platforms']}
    gy = man['groundY']
    suffix = '' if k == 1.0 else '_k%g' % k
    for i, (name, camx) in enumerate(views(man, vw)):
        camx = round(camx * k) / k
        base = compose(man, layers, camx, camy, vw, vh, k)
        base.convert('RGB').save(os.path.join(a.outdir, 'view_%s%s.png' % (name, suffix)))
        dbg = base.copy(); debug_overlay(dbg, man, k, camx, camy)
        dbg.convert('RGB').save(os.path.join(a.outdir, 'view_%s%s_debug.png' % (name, suffix)))
        ch = base.copy()
        cx = camx + vw / 2
        # 캐릭터: 지면 2명, 발판 위 2명 / 몬스터: 스폰 구역에 1~2마리
        put_char(ch, sheets[i % len(sheets)], am, 0, cx - 90, gy, k, camx, camy)
        put_char(ch, sheets[(i + 3) % len(sheets)], am, 1, cx + 150, gy, k, camx, camy, flip=True)
        vis = [p for p in man['platforms'] if p['x1'] > camx + 20 and p['x2'] < camx + vw - 20]
        for j, p in enumerate(sorted(vis, key=lambda p: p['y'])[:2]):
            put_char(ch, sheets[(i + j + 1) % len(sheets)], am, 0, (p['x1'] + p['x2']) / 2 - 30, p['y'], k, camx, camy,
                     flip=bool(j))
        n = 0
        for s in man['spawns']:
            y = gy if s['platform'] == 'ground' else plat[s['platform']]['y']
            x = s['x1'] * 0.3 + s['x2'] * 0.7
            if not (camx + 30 < x < camx + vw - 30) or n >= 3:
                continue
            kind = s['mobs'][0]
            yy = y - 40 if kind == 'bat' else y
            put_mob(ch, mm, kind, 0, x, yy, k, camx, camy, flip=bool(n % 2))
            n += 1
        if n == 0:
            put_mob(ch, mm, 'mushroom', 0, cx + 40, gy, k, camx, camy)
            put_mob(ch, mm, 'slime', 0, cx + 260, gy, k, camx, camy, flip=True)
        ch.convert('RGB').save(os.path.join(a.outdir, 'view_%s%s_chars.png' % (name, suffix)))
    # 전체 축소
    kk = min(1.0, 1800 / man['width'])
    full = compose(man, layers, 0, 0, man['width'], man['height'], kk)
    debug_overlay(full, man, kk, 0, 0)
    full.convert('RGB').save(os.path.join(a.outdir, 'map_full.png'))
    print('wrote', a.outdir)


if __name__ == '__main__':
    main()
