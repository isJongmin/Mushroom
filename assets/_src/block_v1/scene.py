"""블록 지형: 16x16 타일 4종 + 소품(버섯 집, 나무, 구름, 꽃) + 480x270 장면 (캐릭터 스케일 확인용).

타일 규칙: 윗면(밟는 면)은 타일 맨 위 4행(밝은 톤), 그 아래가 정면. 지면선 = 잔디 윗면 첫 행 + 2
(캐릭터 기준점 y). 소품은 캐릭터와 같은 상자 렌더러(A=0.2)로 그린다.
"""
import os
from PIL import Image
from palette import PAL
from render import Box, render, to_image
from chars import nz, fl

T = 16
GROUND_TOP = 206          # 잔디 윗면 첫 행
GROUND_Y = GROUND_TOP + 2  # 캐릭터/소품 기준점 y


def tile(kind, tx=0, seed=0):
    g = [[None] * T for _ in range(T)]
    for y in range(T):
        for x in range(T):
            n = nz(seed + 101, x + tx * 16, y)
            if kind in ('grass', 'dirt'):
                c = 'w3'
                if n < 0.045:
                    c = 'w4'
                elif n > 0.95:
                    c = 'w2'
                g[y][x] = c
            elif kind == 'stone':
                c = 'st2'
                if n < 0.06:
                    c = 'hb1'
                elif n > 0.90:
                    c = 'st1'
                g[y][x] = c
            elif kind == 'plank':
                row = y % 4
                c = 'w2'
                if row == 0:
                    c = 'w1'
                elif row == 3:
                    c = 'w3'
                seam = 7 if (y // 4) % 2 == 0 else 15
                if x == seam and row != 0:
                    c = 'w3'
                if n < 0.04 and row in (1, 2):
                    c = 'w3'
                g[y][x] = c
    if kind == 'grass':
        for x in range(T):
            n = nz(seed + 7, x + tx * 16)
            drip = 6 + (1 if n > 0.5 else 0) + (1 if n > 0.8 else 0) + (1 if (x + tx) % 5 == 0 else 0)
            for y in range(drip):
                if y < 4:
                    c = 'g1' if nz(seed + 9, x + tx * 16, y) > 0.12 else 'g2'
                elif y == 4:
                    c = 'g2'
                else:
                    c = 'g2' if y < drip - 1 else 'g3'
                g[y][x] = c
    if kind == 'stone':   # 금 2개
        for (x, y) in ((3, 4), (4, 5), (4, 6), (5, 7), (11, 10), (12, 10), (12, 11)):
            g[y][x] = 'hb1'
        for (x, y) in ((3, 3), (11, 9)):
            g[y][x] = 'st1'
    return g


def paste_grid(img, g, ox, oy):
    px = img.load()
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c is not None and 0 <= ox + x < img.width and 0 <= oy + y < img.height:
                h = PAL[c]
                px[ox + x, oy + y] = (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)


def fill(img, x0, y0, x1, y1, c):
    h = PAL[c]
    img.paste((int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255), (x0, y0, x1, y1))


# ------------------------------------------------------------------ props (상자)
def house_boxes():
    def stem(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            # 문 (아치 대신 계단 윗선)
            if -7 <= ix <= 6 and -26 <= iy:
                top = -26 if -5 <= ix <= 4 else -24
                if iy >= top:
                    if ix in (-7, 6) or iy == top:
                        return 'w4'
                    if ix == 3 and iy == -13:
                        return 'y2'
                    if ix == -1 or ix == 0:
                        return 'w3'
                    return 'w2'
            # 창문
            for wx in (-20, 11):
                if wx <= ix <= wx + 8 and -38 <= iy <= -30:
                    if ix in (wx, wx + 8) or iy in (-38, -30):
                        return 'w4'
                    if ix == wx + 4 or iy == -34:
                        return 'w3'
                    return 'y1' if iy < -34 else 'y2'
            if iy >= -2:
                return ('stem', 1)
        n = nz(51, ix, iy, fl(z), len(face))
        return ('stem', 1) if n < 0.03 else 'stem'

    dots = [(-38, -70, 5, 4), (-20, -62, 6, 5), (2, -68, 5, 4), (22, -63, 6, 5), (34, -71, 4, 4),
            (-24, -84, 5, 4), (-4, -80, 6, 4), (14, -86, 5, 4), (-8, -96, 5, 4), (6, -93, 4, 3)]
    side_dots = [(-24, -66, 5, 4), (4, -70, 5, 5), (-14, -82, 5, 4), (-6, -95, 4, 3), (10, -63, 4, 4)]
    top_dots = [(-30, -20, 6, 6), (14, -14, 6, 6), (-6, 10, 6, 6), (24, 16, 6, 5), (-10, -8, 5, 5)]

    def inr(lst, a, b):
        return any(x0 <= a < x0 + w and y0 <= b < y0 + h for x0, y0, w, h in lst)

    def cap(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'front' and inr(dots, ix, iy):
            return 'dot'
        if face in ('left',) and inr(side_dots, iz, iy):
            return 'dot'
        if face == 'top' and inr(top_dots, ix, iz):
            return 'dot'
        return 'cap_red'

    def gill(face, x, y, z, view):
        return ('stem', 1)

    def chim(face, x, y, z, view):
        return ('stone', 1) if fl(y) == -102 else 'stone'
    return [
        Box(-24, 24, -54, 0, -12, 12, 'p', 'x', stem),
        Box(-40, 40, -58, -54, -26, 26, 'p', 'x', gill),
        Box(-44, 44, -76, -58, -30, 30, 'p', 'x', cap),
        Box(-32, 32, -90, -76, -22, 22, 'p', 'x', cap),
        Box(-16, 16, -100, -90, -12, 12, 'p', 'x', cap),
        Box(18, 26, -104, -80, 0, 8, 'p', 'x', chim),
    ]


def tree_boxes():
    def trunk(face, x, y, z, view):
        ix = fl(x) if face != 'left' else fl(z)
        return ('wood', 1) if ix % 3 == 0 else 'wood'

    def leaf(face, x, y, z, view):
        n = nz(61, fl(x), fl(y), fl(z), len(face))
        if n < 0.10:
            return ('leaf', 1)
        if n > 0.92:
            return ('leaf', -1)
        return 'leaf'
    return [Box(-4, 4, -34, 0, -4, 4, 'p', 'x', trunk),
            Box(-22, 22, -66, -32, -18, 18, 'p', 'x', leaf),
            Box(-14, 14, -80, -66, -12, 12, 'p', 'x', leaf)]


def cloud_boxes(w=56):
    def t(face, x, y, z, view):
        return ('cloud', 1) if fl(y) >= -2 and face != 'top' else 'cloud'
    return [Box(-w // 2, w // 2, -8, 0, -8, 8, 'p', 'x', t),
            Box(-w // 4, w // 5, -15, -8, -6, 6, 'p', 'x', t)]


def block_boxes(mat_tile):
    """지면 위에 놓인 1x1 블록 (타일 텍스처를 정면에)"""
    g = tile(mat_tile, seed=5)
    top = {'stone': 'st1', 'plank': 'w1'}[mat_tile]
    side = {'stone': 'hb1', 'plank': 'w3'}[mat_tile]

    def t(face, x, y, z, view):
        if face == 'front':
            return (None, g[min(15, fl(y) + 16)][min(15, fl(x) + 8)]) if False else g[min(15, fl(y) + 16)][min(15, fl(x) + 8)]
        return top if face == 'top' else side
    return [Box(-8, 8, -16, 0, -8, 8, 'p', 'x', t)]


def draw_props(img, boxes, ax, ay, W=140, H=140):
    buf = render(boxes, 'front', None, W, H, W // 2, H - 4)
    im = to_image(buf.col, Image)
    img.alpha_composite(im, (ax - W // 2, ay - (H - 4)))


def flower(img, x, petal):
    # 블록 꽃: 4x4 꽃잎 큐브(윗줄 밝게, 오른쪽 열 어둡게) + 노란 심 + 줄기/잎
    hl = {'r2': 'r1', 'p2': 'p1', 'y2': 'y1', 'white': 'white'}[petal]
    dk = {'r2': 'r3', 'p2': 'p3', 'y2': 'y3', 'white': 'c2'}[petal]
    P, L, D, Y = petal, hl, dk, ('y2' if petal != 'y2' else 'y3')
    g = [
        [L, L, L, None],
        [P, Y, P, D],
        [P, P, P, D],
        [None, 'g3', None, None],
        ['g2', 'g3', None, None],
        [None, 'g3', 'g2', None],
    ]
    paste_grid(img, g, x - 1, GROUND_Y - 5)


def build(out, comps):
    os.makedirs(os.path.join(out, 'tiles'), exist_ok=True)
    for k in ('grass', 'dirt', 'stone', 'plank'):
        im = Image.new('RGBA', (T, T), (0, 0, 0, 0))
        paste_grid(im, tile(k), 0, 0)
        im.save(os.path.join(out, 'tiles', k + '.png'))

    img = Image.new('RGBA', (480, 270), (0, 0, 0, 255))
    bands = [('k1', 0, 56), ('k2', 56, 100), ('k3', 100, 140), ('k4', 140, 172), ('k5', 172, 206)]
    for c, a, b in bands:
        fill(img, 0, a, 480, b, c)
    # 먼 언덕 (계단 블록)
    for i, (x0, w, h) in enumerate([(-10, 120, 34), (90, 90, 22), (160, 140, 40), (290, 110, 26), (380, 120, 36)]):
        fill(img, x0, GROUND_TOP - h, x0 + w, GROUND_TOP, 'm1')
        fill(img, x0 + 8, GROUND_TOP - h - 6, x0 + w - 8, GROUND_TOP - h, 'm1')
        fill(img, x0 + 8, GROUND_TOP - h - 6, x0 + w - 8, GROUND_TOP - h - 5, 'white')
        fill(img, x0, GROUND_TOP - h, x0 + 8, GROUND_TOP - h + 1, 'white')
        fill(img, x0 + w - 8, GROUND_TOP - h, x0 + w, GROUND_TOP - h + 1, 'white')
    for i, (x0, w, h) in enumerate([(30, 70, 14), (200, 100, 18), (340, 80, 12)]):
        fill(img, x0, GROUND_TOP - h, x0 + w, GROUND_TOP, 'm2')
        fill(img, x0, GROUND_TOP - h, x0 + w, GROUND_TOP - h + 1, 'm1')
    # 구름
    for cx, cy, w in ((70, 40, 56), (250, 26, 72), (410, 60, 48)):
        draw_props(img, cloud_boxes(w), cx, cy, W=100, H=40)
    # 지면 타일
    for tx in range(30):
        paste_grid(img, tile('grass', tx), tx * T, GROUND_TOP)
        for ty in range(1, 4):
            kind = 'stone' if (ty == 3 and nz(77, tx) < 0.45) or (ty == 2 and nz(78, tx) < 0.12) else 'dirt'
            paste_grid(img, tile(kind, tx * 4 + ty, seed=ty), tx * T, GROUND_TOP + ty * T)
    # 소품
    draw_props(img, tree_boxes(), 52, GROUND_Y, W=80, H=100)
    draw_props(img, house_boxes(), 360, GROUND_Y, W=130, H=124)
    draw_props(img, block_boxes('plank') + [], 438, GROUND_Y, W=30, H=30)
    draw_props(img, block_boxes('stone'), 110, GROUND_Y, W=30, H=30)
    for x, p in ((96, 'r2'), (128, 'p2'), (276, 'y2'), (300, 'white'), (420, 'r2'), (466, 'p2'), (20, 'white')):
        flower(img, x, p)
    # 캐릭터 (기준점 = 지면선), 발 그림자 g3
    cids = sorted({c for c, _ in comps})
    for i, (cid, xpos, fr) in enumerate(zip(cids, (156, 196, 236, 276), (0, 1, 0, 6))):
        variant = comps[(cid, 'sil')]
        for dx in range(-7, 7):
            fill(img, xpos + dx, GROUND_Y, xpos + dx + 1, GROUND_Y + 1, 'g3')
        fr = (0, 0, 2, 0)[i] if False else fr
        im = variant.crop((48 * fr, 0, 48 * (fr + 1), 64))
        img.alpha_composite(im, (xpos - 24, GROUND_Y - 60))
    img.save(os.path.join(out, 'scene.png'))
    return img
