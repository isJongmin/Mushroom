"""voxel_v1 미리보기 (저장소 밖 폴더에 저장): compare, sheet_3x, walk.gif, swap, ingame."""
import os
import sys
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
W, H = 96, 128
BG = (236, 232, 224, 255)


def frame(sheet, i):
    return Image.fromarray(sheet[:, i * W:(i + 1) * W], 'RGBA')


def on_bg(im, bg=BG):
    b = Image.new('RGBA', im.size, bg)
    b.alpha_composite(im)
    return b


def label(d, xy, text, fill=(60, 50, 70)):
    d.text(xy, text, fill=fill)


def make_compare(dirp, full, frames):
    refs = [Image.open(os.path.join(dirp, n)).convert('RGBA') for n in ('ref_sit.png', 'ref_desk.png', 'ref_back.png')]
    th = 384
    refs = [r.resize((round(r.width * th / r.height), th), Image.LANCZOS) for r in refs]
    s = full['A_curly_hoodie']
    mine = [frame(s, frames.index(f)).resize((W * 3, H * 3), Image.NEAREST) for f in ('side', 'front', 'back')]
    pad = 12
    wl = sum(r.width for r in refs) + pad * (len(refs) + 1)
    wr = sum(m.width for m in mine) + pad * 4
    im = Image.new('RGBA', (wl + wr, th + 40), BG)
    d = ImageDraw.Draw(im)
    x = pad
    for r, n in zip(refs, ('ref_sit', 'ref_desk', 'ref_back')):
        im.alpha_composite(r, (x, 30)); label(d, (x, 10), n); x += r.width + pad
    x += pad
    for m, n in zip(mine, ('side (3x)', 'front (3x)', 'back (3x)')):
        im.alpha_composite(m, (x, 30)); label(d, (x, 10), 'voxel_v1 ' + n); x += m.width + pad
    im.save(os.path.join(dirp, 'compare.png'))


def make_sheet(dirp, full, frames):
    s = full['A_curly_hoodie']
    n = len(frames)
    pad = 8
    im = Image.new('RGBA', (n * (W * 3 + pad) + pad, H + H * 3 + 60), BG)
    d = ImageDraw.Draw(im)
    for i, f in enumerate(frames):
        fr = frame(s, i)
        x = pad + i * (W * 3 + pad)
        im.alpha_composite(fr, (x, 20))
        label(d, (x, 6), f)
        im.alpha_composite(fr.resize((W * 3, H * 3), Image.NEAREST), (x, H + 40))
    # 기준점 표시 (1x)
    for i in range(n):
        x = pad + i * (W * 3 + pad)
        d.point((x + 48, 20 + 120), fill=(255, 0, 0, 255))
    im.save(os.path.join(dirp, 'sheet_3x.png'))


def make_walk(dirp, full, frames):
    s = full['A_curly_hoodie']
    ims = [on_bg(frame(s, frames.index(f))).resize((W * 2, H * 2), Image.NEAREST).convert('P', palette=Image.ADAPTIVE)
           for f in ('walk0', 'walk1', 'walk2', 'walk3')]
    ims[0].save(os.path.join(dirp, 'walk.gif'), save_all=True, append_images=ims[1:], duration=150, loop=0)


def make_swap(dirp, full, comp, frames):
    names = list(comp)
    sel = ('front', 'side', 'back')
    pad = 8
    cw = W * 2
    im = Image.new('RGBA', (pad + (cw + pad) * (len(sel) * 2 + 1), len(names) * (H * 2 + 30) + 30), BG)
    d = ImageDraw.Draw(im)
    label(d, (pad, 6), 'left: layer composite (swap)   |   right: full render (truth)   |   last: |diff| x4')
    for r, n in enumerate(names):
        y = 30 + r * (H * 2 + 30)
        label(d, (pad, y), n)
        x = pad
        for src in (comp[n], full[n]):
            for f in sel:
                im.alpha_composite(frame(src, frames.index(f)).resize((cw, H * 2), Image.NEAREST), (x, y + 14))
                x += cw + pad
        fi = frames.index('front')
        a = comp[n][:, fi * W:(fi + 1) * W].astype(float); b = full[n][:, fi * W:(fi + 1) * W].astype(float)
        pa = a[..., :3] * a[..., 3:4] / 255; pb = b[..., :3] * b[..., 3:4] / 255
        df = np.clip(np.abs(pa - pb).max(-1) * 4, 0, 255).astype(np.uint8)
        dimg = Image.fromarray(np.dstack([df, df, df, np.full_like(df, 255)]), 'RGBA')
        im.alpha_composite(dimg.resize((cw, H * 2), Image.NEAREST), (x, y + 14))
    im.save(os.path.join(dirp, 'swap.png'))


def old_avatar_frame(fi=1):
    sys.path.insert(0, os.path.join(ROOT, 'assets', '_src', 'block'))
    m = json.load(open(os.path.join(ROOT, 'assets', 'avatar', 'manifest.json')))
    av = m['presets'][0]['avatar']
    acc = Image.new('RGBA', (48 * 7, 64), (0, 0, 0, 0))
    for layer in m['layerOrder']:
        key = 'hair' if layer in ('hair_back', 'hair_front') else layer
        pid = av.get(key)
        p = os.path.join(ROOT, 'assets', 'avatar', layer, '%s.png' % pid)
        if pid and pid != 'none' and os.path.exists(p):
            acc.alpha_composite(Image.open(p).convert('RGBA'))
    from avatar import silhouette  # 기존 기준 구현 (읽기만)
    outline = json.load(open(os.path.join(ROOT, 'assets', 'avatar', 'outline.json')))
    acc = silhouette(acc, outline)
    return acc.crop((48 * fi, 0, 48 * fi + 48, 64))


def make_ingame(dirp, full, comp, frames):
    mm = json.load(open(os.path.join(ROOT, 'assets', 'map', 'manifest.json')))
    art = Image.new('RGBA', (mm['width'], 270), (0, 0, 0, 255))
    for L in mm['layers']:
        src = Image.open(os.path.join(ROOT, L['src'])).convert('RGBA')
        x = 0
        while x < mm['width']:
            art.alpha_composite(src, (x, L['y']))
            if not L.get('repeatX'):
                break
            x += src.width
    x0, x1 = 360, 660
    crop = art.crop((x0, 0, x1, 270)).resize(((x1 - x0) * 2, 540), Image.NEAREST)
    gy = mm['groundY'] * 2
    old = old_avatar_frame(1).resize((96, 128), Image.NEAREST)
    crop.alpha_composite(old, (90 - 48, gy - 120))
    A = full['A_curly_hoodie']
    crop.alpha_composite(frame(A, frames.index('side')), (220 - 48, gy - 120))
    crop.alpha_composite(frame(A, frames.index('front')), (330 - 48, gy - 120))
    crop.alpha_composite(frame(comp['C_wavy_hoodie'] if 'C_wavy_hoodie' in comp else A, frames.index('side')), (440 - 48, gy - 120))
    crop.alpha_composite(frame(comp.get('B_curly_tee', A), frames.index('walk1')), (530 - 48, gy - 120))
    d = ImageDraw.Draw(crop)
    label(d, (40, gy + 20), 'old block (preset 1, 2x)', fill=(255, 255, 255))
    label(d, (170, gy + 36), 'voxel_v1 (1x screen = same display size as 48x64@2x)', fill=(255, 255, 255))
    crop.save(os.path.join(dirp, 'ingame.png'))


def make_all(dirp, full, comp, sheets, frames):
    os.makedirs(dirp, exist_ok=True)
    make_compare(dirp, full, frames)
    make_sheet(dirp, full, frames)
    make_walk(dirp, full, frames)
    if len(comp) > 1:
        make_swap(dirp, full, comp, frames)
    make_ingame(dirp, full, comp, frames)
