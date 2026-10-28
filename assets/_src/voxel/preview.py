"""미리보기 (저장소 밖 폴더 권장): presets.png(사이클 7: 6종 x 앞/옆/뒤/점프/숙이기), parts_<part>.png, walk.gif,
compare.png(사이클 7: 위 Canva 시안 4종 / 아래 프리셋 1~4 front, 시안 폴더는 환경변수 MUSHROOM_CANVA_DIR), ingame_scale.png(= ingame.png),
(사이클 6) poses.png (프리셋 x side/jump/fall/prone, 2배), jump.gif (idle -> prone -> jump -> fall -> idle, 높이는 물리로 이동).
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


def make_presets(d, sheets, names=('front', 'side', 'jump', 'prone')):
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


REF = os.environ.get('MUSHROOM_REF', '')       # (사이클 10) 배경 화풍 6인 시안 (chars_bgstyle_orig.png, 1680x944, 6명 등간격)
BG_ORIG = os.path.join(B.ROOT, 'assets', '_src', 'map_canva', 'orig', 'center.png')


def make_compare(d, sheets, ref=None):
    """(사이클 10) 위: 시안 6인 (같은 높이로), 아래: 프리셋 1~6 front 레이어 합성 (2.5배)."""
    ref = ref or REF
    k = 2.5
    cw, ch = int(W * k), int(H * k)
    im = Image.new('RGBA', (6 * (cw + 8) + 8, 2 * ch + 44), (244, 238, 230, 255))
    dr = ImageDraw.Draw(im)
    if ref and os.path.exists(ref):
        r = Image.open(ref).convert('RGBA')
        sw = r.width / 6
        for j in range(6):
            c = r.crop((int(j * sw), int(r.height * 0.17), int((j + 1) * sw), int(r.height * 0.90)))
            c = c.resize((int(ch * c.width / c.height), ch), Image.LANCZOS)
            im.alpha_composite(c, (8 + j * (cw + 8) + (cw - c.width) // 2, 8))
    for j in range(6):
        v = views(sheets, PRESETS[j][1], ('front',))[0]
        im.alpha_composite(v.resize((cw, ch), Image.LANCZOS), (8 + j * (cw + 8), ch + 36))
        dr.text((12 + j * (cw + 8), ch + 18), 'preset %d front (layer composite)' % (j + 1), fill=INK)
    im.save(os.path.join(d, 'compare.png'))


def make_presets_c10(d, sheets, names=('front', 'side', 'walk1', 'attack0', 'attack1')):
    """(사이클 10) presets_1x.png / presets_2x.png: 6종 x 정면, 옆, 걷기 1, 공격 2. 1배는 최근접(실제 픽셀), 2배는 최근접 확대."""
    for k in (1, 2):
        cw, ch = W * k, H * k
        im = Image.new('RGBA', (len(names) * cw + 16, len(PRESETS) * (ch + 14) + 20), BG)
        dr = ImageDraw.Draw(im)
        for j, n in enumerate(names):
            dr.text((8 + j * cw + 4, 4), n, fill=INK)
        for i, (lab, av) in enumerate(PRESETS):
            y0 = 18 + i * (ch + 14)
            for j, v in enumerate(views(sheets, av, names)):
                im.alpha_composite(up(v, k), (8 + j * cw, y0))
        im.save(os.path.join(d, 'presets_%dx.png' % k))


def _ground_strip(P):
    """현재 assets/map (Canva 원본 배경, 한 장) 을 표시 배율 P 로."""
    mm = json.load(open(os.path.join(B.ROOT, 'assets', 'map', 'manifest.json')))
    spx = P / 2
    L = [l for l in mm['layers'] if l.get('parallax', 0) == 1.0][0]
    src = Image.open(os.path.join(B.ROOT, L['src'])).convert('RGBA')
    k = spx / mm['density']
    return src.resize((round(src.width * k), round(src.height * k)), Image.LANCZOS), mm['groundY'] * spx, spx


def make_ingame(d, sheets):
    """(사이클 10) ingame.png: 실제 배경 위 실제 게임 배율 (P=2: 2/3 축소, P=3: 1:1) 크롭, 프리셋 6종 (front/side/attack1)."""
    panels = []
    for P in (2, 3):
        bg, gy, spx = _ground_strip(P)
        k = spx / B.DENSITY
        wx0 = 560
        crop = bg.crop((int(wx0 * spx), int(gy - 300 * spx / 1.5), int(wx0 * spx) + 960, int(gy - 300 * spx / 1.5) + int(360 * spx / 1.5)))
        gy2 = gy - int(gy - 300 * spx / 1.5)
        for i, (_, av) in enumerate(PRESETS):
            c = B.composite(sheets, av)
            fr = frame(c, B.FRAMES.index(('side', 'front', 'attack1')[i % 3]))
            s = fr if k == 1 else fr.resize((round(W * k), round(H * k)), Image.LANCZOS)
            x = int(90 * spx + i * 125 * spx * 0.75)
            crop.alpha_composite(s, (int(x - B.ANCHOR[0] * k), int(gy2 - B.ANCHOR[1] * k)))
        ImageDraw.Draw(crop).text((6, 6), 'P=%d  sheet x%.3f' % (P, k), fill=(40, 30, 20, 255))
        panels.append(crop)
    out = Image.new('RGBA', (max(p.width for p in panels), sum(p.height for p in panels)), BG)
    y = 0
    for p in panels:
        out.alpha_composite(p, (0, y)); y += p.height
    out.save(os.path.join(d, 'ingame.png'))


def make_on_bg(d, sheets):
    """(사이클 10) on_bg.png: center.png x1.25 (= 에셋 1:1, P=3 화면) 를 1280x720 으로 크롭, 지면선 원본 y 790,
    프리셋 6종을 실제 게임 배율(시트 1:1)로 세운다. on_bg_zoom.png 는 2배 확대."""
    if not os.path.exists(BG_ORIG):
        return
    bg = Image.open(BG_ORIG).convert('RGBA')
    bg = bg.resize((round(bg.width * 1.25), round(bg.height * 1.25)), Image.LANCZOS)
    gy = 790 * 1.25
    x0, y0 = 250, int(gy - 600)
    bg = bg.crop((x0, y0, x0 + 1280, y0 + 720))
    names = ('front', 'side', 'front', 'attack0', 'front', 'side')
    for i, (_, av) in enumerate(PRESETS):
        c = B.composite(sheets, av)
        f = frame(c, B.FRAMES.index(names[i]))
        cx = 300 + i * 140
        bg.alpha_composite(f, (int(cx - B.ANCHOR[0]), int(gy - y0 - B.ANCHOR[1])))
    bg.save(os.path.join(d, 'on_bg.png'))
    z = bg.crop((200, 360, 1180, 660))
    z.resize((z.width * 2, z.height * 2), Image.LANCZOS).save(os.path.join(d, 'on_bg_zoom.png'))


def make_attack(d, sheets):
    """(사이클 10) attack.gif: side -> attack0 -> attack1 -> side (120ms)."""
    comps = [B.composite(sheets, av) for _, av in PRESETS]
    frames = []
    for n in ('side', 'attack0', 'attack1', 'attack1', 'side', 'side'):
        im = Image.new('RGBA', (W * 6, H), BG)
        for i, c in enumerate(comps):
            im.alpha_composite(frame(c, B.FRAMES.index(n)), (i * W, 0))
        frames.append(im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255))
    frames[0].save(os.path.join(d, 'attack.gif'), save_all=True, append_images=frames[1:], duration=120, loop=0)


def make_poses(d, sheets, k=2):
    names = ('side', 'jump', 'fall', 'prone')
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
    seq = [('side', 0.0)] * 14
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


def make_prone(d, sheets, k=3):
    """(사이클 8) prone.png: 프리셋 6종 엎드리기 확대 (3배, 기준선 y=180 빨강, 기준점 x=72 파랑, 프레임 테두리)."""
    cw, ch = W * k, int(110 * k)                 # 프레임 아래쪽 110px 만 (엎드리기는 낮다)
    y_off = H - 110
    im = Image.new('RGBA', (2 * (cw + 12) + 12, 3 * (ch + 22) + 8), BG)
    dr = ImageDraw.Draw(im)
    for n, (lab, av) in enumerate(PRESETS):
        c = B.composite(sheets, av)
        f = frame(c, B.FRAMES.index('prone')).crop((0, y_off, W, H))
        x0, y0 = 12 + (n % 2) * (cw + 12), 8 + (n // 2) * (ch + 22)
        dr.text((x0, y0), 'preset %d prone' % (n + 1), fill=INK)
        y0 += 14
        dr.rectangle([x0, y0, x0 + cw - 1, y0 + ch - 1], outline=(190, 190, 205, 255))
        gy = y0 + (B.ANCHOR[1] - y_off) * k
        dr.line([(x0, gy), (x0 + cw, gy)], fill=(220, 110, 110, 255))
        dr.line([(x0 + B.ANCHOR[0] * k, y0), (x0 + B.ANCHOR[0] * k, y0 + ch)], fill=(150, 160, 230, 255))
        im.alpha_composite(f.resize((cw, ch), Image.LANCZOS), (x0, y0))
    im.save(os.path.join(d, 'prone.png'))


def make_socks(d, sheets, k=2):
    """(사이클 8) socks.png: 로퍼+니삭스 / 하이탑 / 메리제인을 긴 바지, 치마, 반바지와 (front, side). shoes_under 확인용."""
    base = dict(PRESETS[1][1])
    combos = [(sh, bt) for sh in ('loafer-socks', 'hightop-black', 'maryjane-red') for bt in ('denim-wide', 'pants-navy', 'skirt-check', 'shorts-brown')]
    cw, ch = W * k // 2, int(H * k * 0.45)
    im = Image.new('RGBA', (len(combos) * 2 * cw // 3 + 16, 2 * ch + 40), BG)
    dr = ImageDraw.Draw(im)
    for n, (sh, bt) in enumerate(combos):
        av = dict(base, shoes=sh, bottom=bt)
        for r, v in enumerate(views(sheets, av, ('front', 'side'))):
            f = v.crop((0, int(H * 0.55), W, H)).resize((W * k // 2, int(H * 0.45 * k)), Image.LANCZOS).crop((cw // 6, 0, cw - cw // 6, ch))
            im.alpha_composite(f, (8 + n * (2 * cw // 3), 20 + r * ch))
        if n % 4 == 0:
            dr.text((8 + n * (2 * cw // 3), 4), sh, fill=INK)
    im.save(os.path.join(d, 'socks.png'))


def make_all(d, sheets, jobs=2):
    os.makedirs(d, exist_ok=True)
    make_presets(d, sheets)
    make_presets_c10(d, sheets)
    make_parts(d, sheets)
    make_walk(d, sheets)
    make_compare(d, sheets)
    make_ingame(d, sheets)
    make_on_bg(d, sheets)
    make_attack(d, sheets)
    make_poses(d, sheets)
    make_jump(d, sheets)
    make_prone(d, sheets)
    make_socks(d, sheets)


if __name__ == '__main__':
    import sys
    sh = B.load_sheets(os.path.join(B.ROOT, 'assets', 'avatar'))
    if '--av' in sys.argv:                        # (사이클 10) 설치 전 빌드 폴더로 미리보기
        sh = B.load_sheets(sys.argv[sys.argv.index('--av') + 1])
    if '--poses' in sys.argv:                     # poses.png + jump.gif 만
        os.makedirs(sys.argv[1], exist_ok=True)
        make_poses(sys.argv[1], sh)
        make_jump(sys.argv[1], sh)
    else:
        make_all(sys.argv[1], sh)
