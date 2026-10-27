"""미리보기 (저장소 밖 폴더 권장): presets.png(사이클 7: 6종 x 앞/옆/뒤/점프/숙이기), parts_<part>.png, walk.gif,
compare.png(사이클 7: 위 Canva 시안 4종 / 아래 프리셋 1~4 front, 시안 폴더는 환경변수 MUSHROOM_CANVA_DIR), ingame_scale.png(= ingame.png),
(사이클 6) poses.png (프리셋 x side/jump/fall/crouch, 2배), jump.gif (idle -> crouch -> jump -> fall -> idle, 높이는 물리로 이동).
모든 합성은 build.composite (프런트와 같은 규칙)로 레이어 시트에서 만든다."""
import os
import json
import numpy as np
from PIL import Image, ImageDraw

import build as B
from model import PRESETS, LABELS, CATS

W, H = B.W, B.H
BG = (232, 236, 242, 255)
INK = (50, 44, 64)


def frame(sheet, i):
    return Image.fromarray(np.ascontiguousarray(sheet[:, i * W:(i + 1) * W]), 'RGBA')


def up(im, k):
    return im.resize((int(im.width * k), int(im.height * k)), Image.NEAREST)


def views(sheets, outfit, names=('front', 'side', 'back')):
    c = B.composite(sheets, outfit)
    return [frame(c, B.FRAMES.index(n)) for n in names]


def make_presets(d, sheets, names=('front', 'side', 'back', 'jump', 'crouch')):
    """(사이클 7) 프리셋 6 x 앞/옆/뒤/점프/숙이기, 1.5배."""
    k = 1.5
    cw, ch = int(W * k), int(H * k)
    im = Image.new('RGBA', (len(names) * cw + 24, len(PRESETS) * (ch + 20) + 8), BG)
    dr = ImageDraw.Draw(im)
    for i, (lab, av) in enumerate(PRESETS):
        y0 = 8 + i * (ch + 20)
        dr.text((12, y0), 'preset %d' % (i + 1), fill=INK)
        for j, v in enumerate(views(sheets, av, names)):
            im.alpha_composite(up(v, k), (12 + j * cw, y0 + 14))
    im.save(os.path.join(d, 'presets.png'))


def make_parts(d, sheets):
    base = dict(PRESETS[0][1])
    k = 1.0
    for cat in CATS:
        ids = [i for i, _ in LABELS[cat]]
        per_row = 4
        rows = (len(ids) + per_row - 1) // per_row
        im = Image.new('RGBA', (per_row * (3 * W + 16) + 8, rows * (H + 22) + 8), BG)
        dr = ImageDraw.Draw(im)
        for n, pid in enumerate(ids):
            av = dict(base); av[cat] = pid
            x0 = 8 + (n % per_row) * (3 * W + 16); y0 = 4 + (n // per_row) * (H + 22)
            dr.text((x0, y0), pid, fill=INK)
            for j, v in enumerate(views(sheets, av)):
                im.alpha_composite(up(v, k), (x0 + j * W, y0 + 14))
        im.save(os.path.join(d, 'parts_%s.png' % cat))


def make_walk(d, sheets):
    comps = [B.composite(sheets, av) for _, av in PRESETS]
    frames = []
    for n in ('walk0', 'walk1', 'walk2', 'walk3'):
        im = Image.new('RGBA', (W * 6, H), BG)
        for i, c in enumerate(comps):
            im.alpha_composite(frame(c, B.FRAMES.index(n)), (i * W, 0))
        frames.append(im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255))
    frames[0].save(os.path.join(d, 'walk.gif'), save_all=True, append_images=frames[1:], duration=150, loop=0)
    # 정지 프레임 확인용 (1.5x)
    im = Image.new('RGBA', (int(W * 1.5) * 4, int(H * 1.5) * 2), BG)
    for r, i in enumerate((0, 3)):
        for j, n in enumerate(('walk0', 'walk1', 'walk2', 'walk3')):
            im.alpha_composite(up(frame(comps[i], B.FRAMES.index(n)), 1.5), (j * int(W * 1.5), r * int(H * 1.5)))
    im.save(os.path.join(d, 'walk_frames.png'))


CANVA = ('c1_hoodie_bucket.png', 'c2_cardigan_skirt.png', 'c3_varsity_cap.png', 'c4_puffer_ponytail.png')


def make_compare(d, sheets, canva_dir=None):
    """(사이클 7) 위: Canva 시안 4종, 아래: 프리셋 1~4 front (레이어 합성). 시안 폴더가 없으면 아래 줄만."""
    canva_dir = canva_dir or os.environ.get('MUSHROOM_CANVA_DIR', '')
    k = 2.5
    cw, ch = int(W * k), int(H * k)
    im = Image.new('RGBA', (4 * (cw + 10) + 10, 2 * ch + 40), BG)
    dr = ImageDraw.Draw(im)
    for j in range(4):
        p = os.path.join(canva_dir, CANVA[j])
        if canva_dir and os.path.exists(p):
            r = Image.open(p).convert('RGBA')
            r = r.resize((int(ch * r.width / r.height), ch), Image.LANCZOS)
            im.alpha_composite(r, (10 + j * (cw + 10) + (cw - r.width) // 2, 10))
        v = views(sheets, PRESETS[j][1], ('front',))[0]
        im.alpha_composite(v.resize((cw, ch), Image.LANCZOS), (10 + j * (cw + 10), ch + 30))
        dr.text((14 + j * (cw + 10), ch + 14), 'preset %d front (composite)' % (j + 1), fill=INK)
    im.save(os.path.join(d, 'compare.png'))


def map_strip(P):
    """현재 assets/map 을 표시 배율 P 의 화면으로 합성 (월드 x 0..900 구간)."""
    mm = json.load(open(os.path.join(B.ROOT, 'assets', 'map', 'manifest.json')))
    spx = P / 2                                    # 화면 px / 월드 단위
    if 'density' in mm:
        img_scale = spx / mm['density']; yk = spx; gy = mm['groundY']
    else:                                          # 이전 계약 (아트 1px = 월드 2)
        img_scale = spx * 2; yk = spx * 2; gy = mm['groundY'] * 2
    wx = 900
    sw, sh = int(wx * spx), int(540 * spx)
    im = Image.new('RGBA', (sw, sh), (120, 180, 230, 255))
    for L in mm['layers']:
        src = Image.open(os.path.join(B.ROOT, L['src'])).convert('RGBA')
        s = src.resize((max(1, round(src.width * img_scale)), max(1, round(src.height * img_scale))), Image.NEAREST)
        x = 0
        while x < sw:
            im.alpha_composite(s, (x, int(L['y'] * yk)))
            if not L.get('repeatX'):
                break
            x += s.width
    return im, gy * spx, spx


def make_ingame(d, sheets):
    panels = []
    for P in (2, 3):
        im, gy, spx = map_strip(P)
        k = spx / B.DENSITY
        dr = ImageDraw.Draw(im)
        for i, (_, av) in enumerate(PRESETS):
            c = B.composite(sheets, av)
            fr = frame(c, B.FRAMES.index('side' if i % 2 == 0 else 'front'))
            s = fr.resize((round(W * k), round(H * k)), Image.LANCZOS)
            wx = 120 + i * 120
            im.alpha_composite(s, (int(wx * spx - B.ANCHOR[0] * k), int(gy - B.ANCHOR[1] * k)))
        # 이전 블록 캐릭터 키(월드 86) 표시
        x = int(40 * spx)
        dr.line([(x, gy), (x, gy - 86 * spx)], fill=(255, 60, 60, 255), width=2)
        dr.text((x + 4, gy - 86 * spx), 'old 86', fill=(255, 60, 60, 255))
        dr.text((8, 8), 'P=%d (screen px per world unit = %.1f), sheet scaled x%.3f smooth' % (P, spx, k), fill=(0, 0, 0, 255))
        panels.append(im)
    w = max(p.width for p in panels)
    out = Image.new('RGBA', (w, sum(p.height for p in panels)), BG)
    y = 0
    for p in panels:
        out.alpha_composite(p, (0, y)); y += p.height
    out.save(os.path.join(d, 'ingame_scale.png'))
    out.save(os.path.join(d, 'ingame.png'))


def make_poses(d, sheets, k=2):
    names = ('side', 'jump', 'fall', 'crouch')
    cw, ch = W * k, H * k
    im = Image.new('RGBA', (len(names) * cw + 16, len(PRESETS) * (ch + 18) + 8), BG)
    dr = ImageDraw.Draw(im)
    for r, (lab, av) in enumerate(PRESETS):
        y0 = 8 + r * (ch + 18)
        for j, v in enumerate(views(sheets, av, names)):
            x0 = 8 + j * cw
            dr.text((x0 + 4, y0), 'preset %d  %s' % (r + 1, names[j]), fill=INK)
            gy = y0 + 14 + B.ANCHOR[1] * k
            dr.line([(x0 + 4, gy), (x0 + cw - 4, gy)], fill=(200, 120, 120, 255))
            im.alpha_composite(up(v, k), (x0, y0 + 14))
    im.save(os.path.join(d, 'poses.png'))


def jump_timeline(dt=1 / 30):
    """(프레임 이름, 높이 px) 목록. 물리 = 계약 값(중력 2000, 초속 650 월드/s), 시트 px = 월드 x 1.5."""
    seq = [('side', 0.0)] * 10 + [('crouch', 0.0)] * 4
    t = 0.0
    while True:
        t += dt
        h = 650 * t - 1000 * t * t
        if h <= 0:
            break
        seq.append(('jump' if 650 - 2000 * t > 0 else 'fall', h * B.DENSITY))
    return seq + [('side', 0.0)] * 12


def make_jump(d, sheets):
    comps = [B.composite(sheets, av) for _, av in PRESETS]
    top = 170
    frames = []
    for name, h in jump_timeline():
        im = Image.new('RGBA', (W * len(comps), H + top), BG)
        dr = ImageDraw.Draw(im)
        gy = top + B.ANCHOR[1]
        dr.rectangle([0, gy, im.width, im.height], fill=(196, 214, 170, 255))
        for i, c in enumerate(comps):
            im.alpha_composite(frame(c, B.FRAMES.index(name)), (i * W, top - int(round(h))))
        dr.text((6, 6), name, fill=INK)
        frames.append(im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255))
    frames[0].save(os.path.join(d, 'jump.gif'), save_all=True, append_images=frames[1:], duration=33, loop=0)


def make_all(d, sheets, jobs=2):
    os.makedirs(d, exist_ok=True)
    make_presets(d, sheets)
    make_parts(d, sheets)
    make_walk(d, sheets)
    make_compare(d, sheets)
    make_ingame(d, sheets)
    make_poses(d, sheets)
    make_jump(d, sheets)


if __name__ == '__main__':
    import sys
    sh = B.load_sheets(os.path.join(B.ROOT, 'assets', 'avatar'))
    if '--poses' in sys.argv:                     # poses.png + jump.gif 만
        os.makedirs(sys.argv[1], exist_ok=True)
        make_poses(sys.argv[1], sh)
        make_jump(sys.argv[1], sh)
    else:
        make_all(sys.argv[1], sh)
