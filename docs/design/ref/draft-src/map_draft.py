"""Design draft: map layers + UI skin mock (validation of style-guide values)."""
import sys, os, math, random
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from draft import PAL, rgb, compose, ORDER, W as AW, H as AH

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
C = lambda k: rgb(PAL[k]) + (255,)

WORLD_W, WORLD_H, GROUND = 1200, 270, 220

def px(img, x, y, k):
    if 0 <= x < img.width and 0 <= y < img.height: img.putpixel((x, y), C(k))

def hline(img, x0, x1, y, k):
    for x in range(x0, x1 + 1): px(img, x, y, k)

def fill_rows(img, spans, k):
    for (y, a, b) in spans: hline(img, a, b, y, k)

# ---------- sky (16 x 270, repeatX) ----------
SKY_BANDS = [('k1', 0, 59), ('k2', 60, 104), ('k3', 105, 139), ('k4', 140, 169), ('k5', 170, 269)]
def sky():
    im = Image.new('RGBA', (16, 270))
    for k, a, b in SKY_BANDS:
        for y in range(a, b + 1): hline(im, 0, 15, y, k)
    return im

# ---------- clouds (480 x 70, repeatX, parallax .2) ----------
def cloud(im, cx, cy, w):
    # puffy: union of circles, flat bottom
    pts = set()
    r1 = w // 4
    for (ox, r) in [(-w // 3, r1), (0, int(r1 * 1.4)), (w // 3, r1), (-w // 6, int(r1 * 1.15)), (w // 6, int(r1 * 1.2))]:
        for y in range(-r, 1):
            for x in range(-r, r + 1):
                if x * x + y * y <= r * r: pts.add((cx + ox + x, cy + y))
    maxy = max(p[1] for p in pts)
    for (x, y) in pts:
        k = 'white'
        if y == maxy: k = 'k4'
        elif y >= maxy - 2: k = 'k5'
        px(im, x, y, k)
def clouds():
    im = Image.new('RGBA', (480, 70), (0, 0, 0, 0))
    cloud(im, 60, 34, 48); cloud(im, 210, 22, 32); cloud(im, 330, 44, 60); cloud(im, 440, 28, 28)
    return im

# ---------- hills ----------
def ridge(width, height, base, peaks, k_fill, k_top, seed):
    im = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    hs = []
    for x in range(width):
        h = base
        for (cx, amp, wid) in peaks:
            for off in (-width, 0, width):  # seamless wrap
                d = (x - cx - off) / wid
                h = max(h, base + amp * math.exp(-d * d))
        hs.append(int(round(h)))
    for x, h in enumerate(hs):
        top = height - h
        for y in range(top, height): px(im, x, y, k_fill)
        px(im, x, top, k_top)
    return im
def hills_far():
    return ridge(640, 110, 20, [(60, 70, 50), (200, 50, 60), (330, 85, 55), (470, 45, 50), (580, 65, 45)], 'm1', 'white', 1)
def hills_near():
    im = ridge(640, 80, 18, [(100, 40, 70), (280, 30, 60), (430, 48, 70), (590, 28, 50)], 'm2', 'm1', 2)
    return im

# ---------- mid trees (640 x 120, parallax .5) ----------
def tree(im, cx, base_y, r):
    # trunk
    for y in range(base_y - r, base_y + 1):
        hline(im, cx - 2, cx + 2, y, 'w3'); px(im, cx - 2, y, 'w4'); px(im, cx + 2, y, 'w4'); px(im, cx - 1, y, 'w2')
    cy = base_y - r - r // 2
    pts = set()
    for (ox, oy, rr) in [(0, 0, r), (-r // 2 - 2, r // 3, int(r * .7)), (r // 2 + 2, r // 3, int(r * .7))]:
        for y in range(-rr, rr + 1):
            for x in range(-rr, rr + 1):
                if x * x + y * y <= rr * rr: pts.add((cx + ox + x, cy + oy + y))
    for (x, y) in pts:
        edge = any((x + dx, y + dy) not in pts for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        k = 'g4' if edge else 'g3'
        if not edge and (x - cx) + (y - cy) < -r * 0.6: k = 'g2'
        if not edge and (x - cx) + (y - cy) < -r * 1.1: k = 'g1'
        px(im, x, y, k)
def trees_mid():
    im = Image.new('RGBA', (640, 120), (0, 0, 0, 0))
    for (cx, r) in [(40, 16), (130, 22), (175, 14), (300, 20), (420, 17), (520, 24), (600, 15)]:
        tree(im, cx, 112, r)
    # bush band at bottom
    for x in range(640):
        h = 6 + int(3 * math.sin(x / 7.0) + 2 * math.sin(x / 3.1))
        for y in range(120 - h, 120): px(im, x, y, 'g3')
        px(im, x, 120 - h, 'g4')
    return im

# ---------- ground (1200 x 54 at y=216) ----------
def ground():
    im = Image.new('RGBA', (1200, 54), (0, 0, 0, 0))
    random.seed(3)
    for tx in range(0, 1200, 16):
        # tufts rows 0..3 (y 216..219)
        for x in range(tx, tx + 16):
            t = (x * 7) % 16
            if t in (2, 9):
                px(im, x, 3, 'g2'); px(im, x, 2, 'g2'); px(im, x, 1, 'g1' if t == 2 else 'g2')
            elif t in (3, 10, 13):
                px(im, x, 3, 'g2')
        # grass tile rows 4..19 (y 220..235): 6 rows grass then dirt lip
        for x in range(tx, tx + 16):
            hline(im, x, x, 4, 'g1')
            for y in range(5, 10): px(im, x, y, 'g2')
            # wavy grass bottom edge
            d = 10 + (1 if (x // 3) % 2 == 0 else 0)
            for y in range(10 - 0, d + 1): px(im, x, y, 'g3')
            px(im, x, d + 1, 'g4')
            for y in range(d + 2, 20): px(im, x, y, 'w3')
        # dirt rows 20..35, stone-dirt 36..51, 52..53
        for y in range(20, 54):
            for x in range(tx, tx + 16): px(im, x, y, 'w3')
        for (dx, dy) in [(3, 24), (11, 29), (6, 33), (13, 22)]:
            px(im, tx + dx, dy, 'w4'); px(im, tx + dx + 1, dy, 'w4')
        for (dx, dy) in [(8, 26), (2, 30)]:
            px(im, tx + dx, dy, 'w2')
        # stones
        if (tx // 16) % 2 == 0:
            sx, sy = tx + 4, 40
        else:
            sx, sy = tx + 9, 44
        for (ox, oy) in [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3)]:
            px(im, sx + ox, sy + oy, 'st2')
        px(im, sx + 1, sy + 1, 'st1'); px(im, sx + 2, sy + 1, 'st1'); px(im, sx + 1, sy, 'st1')
        hline(im, sx + 1, sx + 3, sy + 4, 'hb1')
    return im

# ---------- mushroom house ----------
def house(im, cx, base, cap='red', w=72, stem_w=40, stem_h=40):
    capR = {'red': ('r1', 'r2', 'r3'), 'orange': ('y2', 'y3', 'y4'), 'blue': ('u1', 'u2', 'u3')}[cap]
    hl, bs, ln = capR
    # stem: slightly flared bottom
    top = base - stem_h
    for y in range(top, base):
        t = (y - top) / stem_h
        half = stem_w // 2 + int(3 * t * t)
        hline(im, cx - half, cx + half, y, 'c1')
        px(im, cx - half, y, 'w3'); px(im, cx + half, y, 'w3')
        px(im, cx - half + 1, y, 'c2'); px(im, cx - half + 2, y, 'c2')
        px(im, cx + half - 1, y, 'c3'); px(im, cx + half - 2, y, 'c2')
    hline(im, cx - stem_w // 2 - 3, cx + stem_w // 2 + 3, base - 1, 'w3')
    # door (arched) 14x22, offset left
    dx0, dw, dh = cx - 12, 14, 22
    for y in range(base - dh, base):
        r = y - (base - dh)
        inset = 3 if r == 0 else (1 if r < 3 else 0)
        hline(im, dx0 + inset, dx0 + dw - 1 - inset, y, 'w2')
        px(im, dx0 + inset, y, 'w4'); px(im, dx0 + dw - 1 - inset, y, 'w4')
        if r == 0: hline(im, dx0 + inset, dx0 + dw - 1 - inset, y, 'w4')
    for y in range(base - dh + 3, base):
        px(im, dx0 + 5, y, 'w3'); px(im, dx0 + 9, y, 'w3')
    px(im, dx0 + 10, base - 11, 'y2'); px(im, dx0 + 11, base - 11, 'y4')
    # step stone
    hline(im, dx0 - 1, dx0 + dw, base, 'st1'); hline(im, dx0 - 1, dx0 + dw, base + 1, 'st2')
    # round window 10x10 right
    wx, wy = cx + 10, top + 12
    win = [(0, 3, 6), (1, 1, 8), (2, 0, 9), (3, 0, 9), (4, 0, 9), (5, 0, 9), (6, 0, 9), (7, 0, 9), (8, 1, 8), (9, 3, 6)]
    for (r, a, b) in win:
        hline(im, wx + a, wx + b, wy + r, 'y1')
        px(im, wx + a, wy + r, 'w3'); px(im, wx + b, wy + r, 'w3')
    hline(im, wx + 3, wx + 6, wy, 'w3'); hline(im, wx + 3, wx + 6, wy + 9, 'w3')
    for r in range(1, 9): px(im, wx + 5, wy + r, 'w3')
    hline(im, wx + 1, wx + 8, wy + 5, 'w3')
    px(im, wx + 2, wy + 2, 'y2'); px(im, wx + 7, wy + 7, 'y2')
    # cap: half-ellipse dome w x capH, bottom at top+4 (overhang)
    capH = int(w * 0.5)
    cb = top + 4
    pts = set()
    a, b = w / 2, capH
    for y in range(cb - capH, cb + 1):
        dy = (cb - y) / b
        if dy > 1: continue
        half = int(a * math.sqrt(max(0, 1 - dy * dy)))
        for x in range(cx - half, cx + half + 1): pts.add((x, y))
    # brim droop: extra 2 rows at edges
    for x in range(cx - int(a), cx + int(a) + 1):
        if abs(x - cx) > a * 0.55:
            pts.add((x, cb + 1))
            if abs(x - cx) > a * 0.8: pts.add((x, cb + 2))
    # chimney (behind cap, right)
    chx = cx + int(a * 0.45)
    cht = cb - capH + 2
    for y in range(cht, cht + 16):
        hline(im, chx, chx + 7, y, 'st1'); px(im, chx, y, 'hb1'); px(im, chx + 7, y, 'hb1'); px(im, chx + 5, y, 'st2'); px(im, chx + 6, y, 'st2')
    hline(im, chx - 1, chx + 8, cht, 'hb1'); hline(im, chx - 1, chx + 8, cht + 1, 'st2')
    # smoke
    for (sx, sy, rr) in [(chx + 4, cht - 6, 3), (chx + 8, cht - 13, 4)]:
        for y in range(-rr, rr + 1):
            for x in range(-rr, rr + 1):
                if x * x + y * y <= rr * rr: px(im, sx + x, sy + y, 'c1' if y < rr - 1 else 'c2')
    maxy = max(p[1] for p in pts)
    for (x, y) in pts:
        edge = any((x + ddx, y + ddy) not in pts for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        k = ln if edge else bs
        if not edge and y >= maxy - 2: k = ln
        px(im, x, y, k)
    # highlight arc
    for y in range(cb - capH + 3, cb - capH + 7):
        for x in range(cx - int(a * 0.55), cx - int(a * 0.1)):
            dy = (cb - y) / b; half = int(a * math.sqrt(max(0, 1 - dy * dy)))
            if (x, y) in pts and abs(x - cx) < half - 3 and (x + y) % 1 == 0:
                if y < cb - capH + 5: px(im, x, y, hl)
    # dots (cream)
    for (ox, oy, rr) in [(-0.55, 0.35, 4), (-0.15, 0.7, 3), (0.25, 0.4, 5), (0.62, 0.25, 3), (-0.35, 0.12, 2), (0.05, 0.15, 3)]:
        dcx, dcy = cx + int(ox * a), cb - int(oy * capH)
        for y in range(-rr, rr + 1):
            for x in range(-rr, rr + 1):
                if x * x + y * y <= rr * rr and (dcx + x, dcy + y) in pts:
                    edge = any((dcx + x + ddx, dcy + y + ddy) not in pts for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if edge: continue
                    px(im, dcx + x, dcy + y, 'c2' if y > rr // 2 else 'c1')
    # gills under cap
    hline(im, cx - stem_w // 2, cx + stem_w // 2, cb + 1, 'c3')

def fence(im, x0, n, base):
    for i in range(n):
        x = x0 + i * 6
        for y in range(base - 12, base):
            hline(im, x, x + 2, y, 'w2'); px(im, x, y, 'w4'); px(im, x + 2, y, 'w4')
        px(im, x + 1, base - 13, 'w4'); hline(im, x, x + 2, base - 12, 'w4')
        px(im, x + 1, base - 11, 'w1')
    for ry in (base - 9, base - 4):
        hline(im, x0, x0 + n * 6 - 4, ry, 'w3'); hline(im, x0, x0 + n * 6 - 4, ry + 1, 'w4')

def sign(im, cx, base):
    for y in range(base - 22, base): hline(im, cx - 1, cx + 1, y, 'w3'); px(im, cx - 1, y, 'w4'); px(im, cx + 1, y, 'w4')
    bx, by = cx - 14, base - 30
    for y in range(by, by + 14): hline(im, bx, bx + 28, y, 'w2')
    hline(im, bx, bx + 28, by, 'w4'); hline(im, bx, bx + 28, by + 13, 'w4')
    for y in range(by, by + 14): px(im, bx, y, 'w4'); px(im, bx + 28, y, 'w4')
    hline(im, bx + 1, bx + 27, by + 1, 'w1'); hline(im, bx + 1, bx + 27, by + 12, 'w3')
    # mushroom emblem
    for (r, a, b) in [(3, 12, 16), (4, 11, 17), (5, 10, 18), (6, 10, 18)]:
        hline(im, bx + a, bx + b, by + r, 'r2')
    px(im, bx + 12, by + 4, 'c1'); px(im, bx + 16, by + 5, 'c1')
    for r in (7, 8, 9): hline(im, bx + 13, bx + 15, by + r, 'c1')

def flowers(im, xs, base):
    for i, x in enumerate(xs):
        k = ['r2', 'y2', 'p2', 'white'][i % 4]
        px(im, x, base - 1, 'g3'); px(im, x, base - 2, 'g3')
        px(im, x, base - 4, k); px(im, x - 1, base - 3, k); px(im, x + 1, base - 3, k); px(im, x, base - 3, 'y2' if k != 'y2' else 'y4')

def village():
    im = Image.new('RGBA', (1200, 160), (0, 0, 0, 0))
    base = 160 - 1 - 1  # village.png placed at y=62 -> row 158 == y 220? (keep feet at 219)
    # layer y = 60 -> row r is world y 60+r ; ground 220 => row 160 (bottom). houses base row 159 (y=219)
    B = 159
    house(im, 130, B + 1, 'red', 80, 44, 44)
    house(im, 440, B + 1, 'orange', 66, 36, 36)
    house(im, 790, B + 1, 'blue', 76, 42, 42)
    house(im, 1060, B + 1, 'red', 58, 32, 32)
    fence(im, 200, 8, B + 1); fence(im, 520, 6, B + 1); fence(im, 880, 9, B + 1)
    sign(im, 600, B + 1)
    flowers(im, [20, 26, 250, 258, 300, 380, 386, 560, 640, 700, 706, 940, 990, 1150, 1156], B + 1)
    return im

LAYERS = [
    ('sky', sky, 0.0, 0, True),
    ('clouds', clouds, 0.2, 18, True),
    ('hills-far', hills_far, 0.2, 110, True),
    ('hills-near', hills_near, 0.3, 142, True),
    ('trees-mid', trees_mid, 0.5, 104, True),
    ('village', village, 1.0, 60, False),
    ('ground', ground, 1.0, 216, False),
]

def render_view(camX, vw, vh, camY=0):
    view = Image.new('RGBA', (vw, vh), C('k1'))
    for name, fn, par, y, rep in LAYERS:
        im = fn()
        ox = -int(round(camX * par))
        if rep:
            start = ox % im.width - im.width
            x = start
            while x < vw:
                view.alpha_composite(im, (x, y - camY)) if y - camY >= 0 else view.paste(im, (x, y - camY), im)
                x += im.width
        else:
            view.paste(im, (ox, y - camY), im)
    return view

def font(sz):
    for p in ['/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
              '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

if __name__ == '__main__':
    avs = [
        dict(skin='skin-light', hair=('round', 'chestnut'), eyes='eyes-dot', top='top-tee-red', bottom='bottom-shorts-navy'),
        dict(skin='skin-dark', hair=('long', 'pink'), eyes='eyes-sparkle', top='top-overalls', bottom='bottom-skirt-pink'),
        dict(skin='skin-tan', hair=('spiky', 'mint'), eyes='eyes-happy', top='top-mushroom-cape', bottom='bottom-pumpkin-green'),
    ]
    camX = 340
    view = render_view(camX, 480, 270)
    # avatars at art x
    spots = [(470, 'walk0', False), (540, 'idle0', True), (610, 'walk2', True)]
    for (x, fr, flip), av in zip(spots, avs):
        s = compose(fr, av)
        if flip: s = s.transpose(Image.FLIP_LEFT_RIGHT)
        view.alpha_composite(s, (x - camX - 16, GROUND - 46))
    P = 2
    big = view.resize((480 * P, 270 * P), Image.NEAREST)
    d = ImageDraw.Draw(big)
    f12 = font(12); f14 = font(14)
    names = ['버섯이', '핑크곰', '민트초코']
    for i, ((x, fr, flip), nm) in enumerate(zip(spots, names)):
        sx = (x - camX) * P; sy = GROUND * P + 4
        tw = d.textlength(nm, font=f12)
        w = int(tw) + 12; w += w % 2; h = 18
        bg = PAL['y3'] if i == 0 else PAL['hb2']; ln = PAL['y4'] if i == 0 else PAL['ink']
        x0 = sx - w // 2
        d.rectangle([x0, sy, x0 + w - 1, sy + h - 1], fill=bg)
        d.rectangle([x0, sy, x0 + w - 1, sy + 1], fill=ln); d.rectangle([x0, sy + h - 2, x0 + w - 1, sy + h - 1], fill=ln)
        d.rectangle([x0, sy, x0 + 1, sy + h - 1], fill=ln); d.rectangle([x0 + w - 2, sy, x0 + w - 1, sy + h - 1], fill=ln)
        tc = PAL['ink'] if i == 0 else '#FFFFFF'
        if i != 0: d.text((x0 + 6 + 1, sy + 1 + 1), nm, font=f12, fill=PAL['ink'])
        d.text((x0 + 6, sy + 1), nm, font=f12, fill=tc)
    # bubble over avatar 1
    msg = '안녕! 버섯마을에 온 걸 환영해'
    sx = (540 - camX) * P
    tw = int(d.textlength(msg, font=f14)); bw = tw + 24; bw += bw % 2; bh = 18 + 16
    tail_tip = (GROUND - 46 + 4) * P - 4
    by1 = tail_tip - 8; by0 = by1 - bh
    bx0 = sx - bw // 2
    d.rectangle([bx0 + 2, by0, bx0 + bw - 3, by1 - 1], fill='#FFFFFF')
    d.rectangle([bx0, by0 + 2, bx0 + bw - 1, by1 - 3], fill='#FFFFFF')
    # border 2px
    d.rectangle([bx0 + 2, by0, bx0 + bw - 3, by0 + 1], fill=PAL['hb2']); d.rectangle([bx0 + 2, by1 - 2, bx0 + bw - 3, by1 - 1], fill=PAL['hb2'])
    d.rectangle([bx0, by0 + 2, bx0 + 1, by1 - 3], fill=PAL['hb2']); d.rectangle([bx0 + bw - 2, by0 + 2, bx0 + bw - 1, by1 - 3], fill=PAL['hb2'])
    d.rectangle([bx0 + 2, by1 - 4, bx0 + bw - 3, by1 - 3], fill=PAL['c2'])
    for r in range(3):
        d.rectangle([sx - 6 + r * 2, by1 - 2 + r * 2, sx + 5 - r * 2, by1 - 1 + r * 2], fill='#FFFFFF')
        d.rectangle([sx - 6 + r * 2, by1 - 2 + r * 2, sx - 5 + r * 2, by1 - 1 + r * 2], fill=PAL['hb2'])
        d.rectangle([sx + 4 - r * 2, by1 - 2 + r * 2, sx + 5 - r * 2, by1 - 1 + r * 2], fill=PAL['hb2'])
    d.text((bx0 + 12 + 1, by0 + 7 + 1), msg, font=f14, fill=PAL['c2'])
    d.text((bx0 + 12, by0 + 7), msg, font=f14, fill=PAL['ink'])
    big.save(os.path.join(OUT, 'map-draft.png'))
    # whole world strip at 1x
    render_view(0, 1200, 270).save(os.path.join(OUT, 'world-1x.png'))
    print('ok')
