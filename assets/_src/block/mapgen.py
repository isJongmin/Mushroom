"""블록 버섯마을 맵 레이어 (월드 아트 1200 x 270, 지면선 y=220, 잔디 윗면 첫 행 y=218).

레이어 (뒤 -> 앞, assets/map/manifest.json)
  sky.png     16 x 270   y 0    parallax 0.0  repeatX  하늘 띠 5단
  clouds.png  640 x 90   y 10   parallax 0.1  repeatX  블록 구름
  far.png     640 x 100  y 122  parallax 0.3  repeatX  먼 계단식 블록 산 (아래 끝 222, 지면 뒤로 숨음)
  mid.png     640 x 110  y 112  parallax 0.6  repeatX  중경 블록 나무 숲 실루엣 (아래 끝 222)
  ground.png  1200 x 210 y 60   parallax 1.0  -        잔디/흙/돌 타일 + 지면 위 소품 (버섯 집, 나무, 울타리...)
소품은 캐릭터와 같은 상자 렌더러(사선 A=0.2)로 그린다. 소품 밑면 = 잔디 윗면 첫 행(218)의 윗선 -> 마지막 행 217.
캐릭터 기준점(지면선 220)은 잔디 윗면 한가운데라 캐릭터가 소품 앞을 걷는다. 소품은 충돌 없음.
반복 레이어는 좌우 끝이 이어지게(감싸 붙이기) 그린다.
"""
import os
import json
import math
from PIL import Image

from palette import PAL, rgba
from render import Box, render, to_image
from parts import nz, fl

WORLD_W, WORLD_H = 1200, 270
GROUND_TOP = 218
GROUND_Y = 220
T = 16
PROP_BASE = GROUND_TOP          # 소품 상자 y=0 이 놓이는 아트 y (행 217 까지 채움)
GROUND_LAYER_Y = 60


def fill(img, x0, y0, x1, y1, c):
    img.paste(rgba(c), (x0, y0, x1, y1))


def paste_grid(img, g, ox, oy, wrap=False):
    px = img.load()
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c is None:
                continue
            X, Y = ox + x, oy + y
            if wrap:
                X %= img.width
            if 0 <= X < img.width and 0 <= Y < img.height:
                px[X, Y] = rgba(c)


def paste_wrap(dst, src, x, y):
    for dx in (-dst.width, 0, dst.width):
        X = x + dx
        if X + src.width <= 0 or X >= dst.width:
            continue
        # 잘라서 붙이기 (alpha_composite 는 음수 좌표 불가)
        sx0 = max(0, -X)
        sy0 = max(0, -y)
        sx1 = min(src.width, dst.width - X)
        sy1 = min(src.height, dst.height - y)
        if sx1 <= sx0 or sy1 <= sy0:
            continue
        dst.alpha_composite(src.crop((sx0, sy0, sx1, sy1)), (X + sx0, y + sy0))


def prop_image(boxes, W=320, H=260):
    """상자 묶음 -> (잘라낸 이미지, 원점의 이미지 내 x, y). 원점 = 상자 공간 (0,0,0)."""
    ax, ay = W // 2, H - 20
    buf = render(boxes, 'front', None, W, H, ax, ay)
    im = to_image(buf.col, Image)
    bb = im.getbbox()
    assert bb[0] > 0 and bb[1] > 0 and bb[2] < W and bb[3] < H, ('prop clipped', bb)
    return im.crop(bb), ax - bb[0], ay - bb[1]


def place(img, boxes, x, base_y, wrap=False, W=None, H=None):
    im, ax, ay = prop_image(boxes)
    if wrap:
        paste_wrap(img, im, x - ax, base_y - ay)
    else:
        img.alpha_composite(im, (x - ax, base_y - ay))


# ===================================================================== tiles
def tile(kind, tx=0, seed=0):
    g = [[None] * T for _ in range(T)]
    for y in range(T):
        for x in range(T):
            n = nz(seed + 101, x + tx * 16, y)
            if kind in ('grass', 'dirt'):
                c = 'w3'
                n2 = nz(seed + 101, x // 2 + tx * 8, y // 2 + 50)   # 2x2 덩어리 반점 (소금후추 방지)
                if n2 < 0.05:
                    c = 'w4'
                elif n2 > 0.96:
                    c = 'w2'
            elif kind == 'stone':
                c = 'st2'
                n2 = nz(seed + 103, x // 2 + tx * 8, y // 2)
                if n2 < 0.06:
                    c = 'hb1'
                elif n2 > 0.93:
                    c = 'st1'
            g[y][x] = c
    if kind == 'grass':
        for x in range(T):
            n = nz(seed + 7, x + tx * 16)
            drip = 6 + (1 if n > 0.5 else 0) + (1 if n > 0.8 else 0) + (1 if (x + tx) % 5 == 0 else 0)
            for y in range(drip):
                if y < 4:
                    c = 'g1' if nz(seed + 9, x + tx * 16, y) > 0.1 else 'g2'
                elif y == 4:
                    c = 'g2'
                else:
                    c = 'g2' if y < drip - 1 else 'g3'
                g[y][x] = c
    if kind == 'stone':
        for (x, y) in ((3, 4), (4, 5), (4, 6), (5, 7), (11, 10), (12, 10), (12, 11)):
            g[y][x] = 'hb1'
        for (x, y) in ((3, 3), (11, 9)):
            g[y][x] = 'st1'
    # 타일 경계: 돌만 오른쪽 열/아래 행 한 톤 어둡게 (블록 이음매). 흙은 이음매 없이 (점선 격자 방지)
    if kind == 'stone':
        dk = {'w2': 'w3', 'w3': 'w4', 'w4': 'w4', 'st1': 'st2', 'st2': 'hb1', 'hb1': 'hb1'}
        for i in range(T):
            if True:
                g[T - 1][i] = dk[g[T - 1][i]]
                g[i][T - 1] = dk[g[i][T - 1]]
    return g


# ===================================================================== props
def dot_tex(mat, seed, cell=13, size=(5, 4), side_faces=True):
    """버섯 갓: 좌표 해시로 흩뿌린 흰 점 (면별 격자 칸마다 하나, 확률 0.55)."""
    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'front':
            u, v = ix, iy
        elif face in ('left', 'right'):
            if not side_faces:
                return mat
            u, v = iz, iy
        elif face == 'top':
            u, v = ix, iz
        else:
            return mat
        cu, cv = u // cell, v // cell
        if nz(seed, cu, cv, len(face)) < 0.55:
            ou = int(nz(seed + 1, cu, cv) * (cell - size[0]))
            ov = int(nz(seed + 2, cu, cv) * (cell - size[1]))
            if cu * cell + ou <= u < cu * cell + ou + size[0] and cv * cell + ov <= v < cv * cell + ov + size[1]:
                return 'dot'
        return mat
    return t


def house(cap, w=64, h=72, d=26, seed=1, chimney=1, door_h=50, windows=2):
    hw = w // 2
    dw = 20 if w >= 60 else 18

    def stem(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            # 문 (위가 계단형 아치)
            dx0, dx1 = -dw // 2, dw // 2 - 1
            if dx0 <= ix <= dx1 and iy >= -door_h:
                inset = 0
                k = iy + door_h            # 문 위에서 몇 번째 행
                if k < 2:
                    inset = 4
                elif k < 4:
                    inset = 2
                elif k < 6:
                    inset = 1
                if dx0 + inset <= ix <= dx1 - inset:
                    if ix in (dx0 + inset, dx1 - inset) or k == (0 if inset else 0) and inset == 4:
                        return 'w4'
                    if ix in (dx0 + inset + 1,) or k in (0, 1) and inset:
                        return 'w4'
                    if ix == dx1 - 4 and iy == -door_h // 2:
                        return 'y2'           # 손잡이
                    if (ix - dx0) % 5 == 4:
                        return 'w3'           # 판자 이음
                    return 'w2'
            # 창문 (문 양옆, 십자 창살)
            if windows:
                for wx in ((-hw + 6, hw - 6 - 13) if windows > 1 else (hw - 6 - 13,)):
                    if wx <= ix <= wx + 12 and -door_h + 4 <= iy <= -door_h + 18:
                        if ix in (wx, wx + 12) or iy in (-door_h + 4, -door_h + 18):
                            return 'w4'
                        if ix == wx + 6 or iy == -door_h + 11:
                            return 'w3'
                        return 'y1' if iy < -door_h + 11 else 'y2'
            if iy >= -3:
                return ('stem', 1)            # 아랫단(기초)
        if face == 'left':
            iz = fl(z)
            if 6 <= iz <= 16 and -h + 14 <= iy <= -h + 24 and windows:
                if iz in (6, 16) or iy in (-h + 14, -h + 24):
                    return 'w4'
                return 'y2'
        n = nz(seed + 51, ix, iy, fl(z), len(face))
        return ('stem', 1) if n < 0.025 else 'stem'

    gill = lambda face, x, y, z, view: ('stem', 1)
    capt = dot_tex(cap, seed + 7)
    cz = d / 2
    boxes = [Box(-hw, hw, -h, 0, 0, d, 'p', 'x', stem, 'stem')]
    rim = hw + 18
    boxes.append(Box(-rim + 6, rim - 6, -h - 4, -h, cz - (rim - 6) * 0.55, cz + (rim - 6) * 0.55, 'p', 'x', gill, 'gill'))
    lv = [(rim, 18), (rim - 12, 16), (rim - 26, 12)]
    y = -h - 4
    for i, (r, hh) in enumerate(lv):
        dz = r * 0.6
        boxes.append(Box(-r, r, y - hh, y, cz - dz, cz + dz, 'p', 'x', capt, 'cap%d' % i))
        y -= hh
    if chimney:
        cx = rim - 26 - 2
        boxes.append(Box(cx - 10, cx, y - 14, y + 14, cz - 3, cz + 7, 'p', 'x',
                         lambda face, x, yy, z, view: ('stone', 1) if fl(yy) == y - 11 and face != 'top' else 'stone', 'chim'))
    # 문 앞 디딤돌
    boxes.append(Box(-dw // 2 - 2, dw // 2 + 2, -2, 0, -4, 0, 'p', 'x', lambda *a: 'stone', 'step'))
    return boxes


def oak(seed=3, s=1.0):
    def trunk(face, x, y, z, view):
        u = fl(x) if face in ('front', 'back') else fl(z)
        return ('wood', 1) if u % 3 == 0 and face != 'top' else 'wood'

    def leaf(face, x, y, z, view):
        n = nz(seed + 61, fl(x) // 2, fl(y) // 2, fl(z) // 2, len(face))
        if n < 0.09:
            return ('leaf', 1)
        if n > 0.93:
            return ('leaf', -1)
        return 'leaf'
    r = int(20 * s)
    return [Box(-4, 4, -34, 0, 8, 16, 'p', 'x', trunk, 'trunk'),
            Box(-r, r, -int(66 * s), -30, 12 - r * 0.8, 12 + r * 0.8, 'p', 'x', leaf, 'leaf1'),
            Box(-r + 7, r - 7, -int(80 * s), -int(66 * s), 12 - (r - 7) * 0.8, 12 + (r - 7) * 0.8, 'p', 'x', leaf, 'leaf2'),
            Box(r - 4, r + 6, -int(56 * s), -40, 6, 16, 'p', 'x', leaf, 'leaf3')]


def pine(seed=4, s=1.0):
    def trunk(face, x, y, z, view):
        return 'wood'

    def lf(face, x, y, z, view):
        iy = fl(y)
        if face != 'top' and nz(seed + 3, fl(x) // 2, iy // 2, fl(z) // 2) < 0.12:
            return ('pine', 1)
        return 'pine'
    tiers = [(18, 18), (13, 16), (8, 14), (3, 6)]
    out = [Box(-3, 3, -14, 0, 7, 13, 'p', 'x', trunk, 'trunk')]
    y = -12
    for i, (r, hh) in enumerate(tiers):
        r = int(r * s)
        hh = int(hh * s)
        out.append(Box(-r, r, y - hh, y, 10 - r * 0.7, 10 + r * 0.7, 'p', 'x', lf, 'tier%d' % i))
        y -= hh - 2
    return out


def fence(length):
    """x 0..length 울타리 (기둥 12px 간격)."""
    wood = lambda face, x, y, z, view: ('wood', 1) if face == 'front' and fl(y) in (-14,) else 'wood'
    rail = lambda face, x, y, z, view: 'plank'
    out = []
    for px in range(0, length + 1, 12):
        out.append(Box(px - 2, px + 2, -18, 0, 4, 8, 'p', 'x', wood, 'post'))
        out.append(Box(px - 1, px + 1, -20, -18, 5, 7, 'p', 'x', wood, 'cap'))
    out.append(Box(-1, length + 1, -14, -11, 5, 7, 'p', 'x', rail, 'rail1'))
    out.append(Box(-1, length + 1, -8, -5, 5, 7, 'p', 'x', rail, 'rail2'))
    return out


SIGN_ICON = [   # 버섯 아이콘 (표지판 판자 앞면), 14 x 11
    "....rrrrrr....",
    "..rrwwrrrrrr..",
    ".rrwwrrrrwwrr.",
    "rrrrrrrrrwwrrr",
    "rrwwrrrrrrrrrr",
    "RRRRRRRRRRRRRR",
    "....cccccc....",
    "....cckcck....",
    "....cccccc....",
    "....cccccC....",
    "....CCCCCC....",
]
ICON_C = {'r': 'r2', 'R': 'r3', 'w': 'white', 'c': 'c1', 'C': 'c2', 'k': 'ink'}


def signpost():
    def board(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            if ix in (-16, 15) or iy in (-40, -23):
                return ('plank', 1)
            u, v = ix + 7, iy + 37
            if 0 <= v < len(SIGN_ICON) and 0 <= u < 14:
                ch = SIGN_ICON[v][u]
                if ch != '.':
                    return ICON_C[ch]
            return 'plank'
        return 'plank'
    return [Box(-2, 2, -24, 0, 6, 10, 'p', 'x', lambda *a: 'wood', 'post'),
            Box(-16, 16, -40, -22, 5, 8, 'p', 'x', board, 'board')]


def lamp():
    def lantern(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face in ('front', 'left') and iy not in (-60, -49):
            u = ix if face == 'front' else fl(z)
            lo = -5 if face == 'front' else 1
            if (face == 'front' and ix not in (-5, 4)) or (face == 'left' and fl(z) not in (1, 8)):
                return 'y1' if iy < -54 else 'y2'
        return 'dark'
    return [Box(-5, 5, -4, 0, 1, 9, 'p', 'x', lambda *a: 'stone', 'base'),
            Box(-1, 2, -49, -4, 4, 6, 'p', 'x', lambda *a: 'dark', 'pole'),
            Box(-5, 5, -61, -49, 1, 9, 'p', 'x', lantern, 'lantern'),
            Box(-6, 6, -63, -61, 0, 10, 'p', 'x', lambda *a: 'dark', 'roof'),
            Box(-2, 2, -65, -63, 3, 7, 'p', 'x', lambda *a: 'dark', 'knob')]


def well():
    def ring(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'top':
            if -12 <= ix <= 11 and 4 <= iz <= 15:
                return 'water' if not (ix in (-12, 11) or iz in (4, 15)) else ('stone', 1)
            return 'stone'
        u = ix if face in ('front', 'back') else iz
        # 벽돌 줄눈
        if (iy % 5 == 0) or ((u + (4 if (iy // 5) % 2 else 0)) % 8 == 0):
            return ('stone', 1)
        return 'stone'

    def roof(face, x, y, z, view):
        u = fl(x) if face != 'left' else fl(z)
        if face == 'top':
            return ('cap_red', 0) if fl(z) % 4 else ('cap_red', 1)
        return 'cap_red'
    post = lambda face, x, y, z, view: 'wood'
    return [Box(-16, 16, -14, 0, 0, 20, 'p', 'x', ring, 'ring'),
            Box(-15, -12, -44, -14, 8, 12, 'p', 'x', post, 'postR'),
            Box(12, 15, -44, -14, 8, 12, 'p', 'x', post, 'postL'),
            Box(-15, 15, -42, -40, 9, 11, 'p', 'x', post, 'bar'),
            Box(-1, 0, -40, -27, 10, 11, 'p', 'x', lambda *a: 'w4', 'rope'),
            Box(-3, 3, -27, -21, 8, 13, 'p', 'x', lambda face, x, y, z, v: ('wood', 1) if fl(y) == -25 else 'wood', 'bucket'),
            Box(-20, 20, -50, -44, 2, 18, 'p', 'x', roof, 'roof1'),
            Box(-14, 14, -55, -50, 5, 15, 'p', 'x', roof, 'roof2')]


def stone_blocks(layout):
    """layout: [(bx, by, bz)] 블록 좌표(16 단위). 각 블록은 돌 타일 무늬."""
    g = tile('stone', seed=5)
    out = []
    for i, (bx, by, bz) in enumerate(layout):
        x0, y0, z0 = bx * 16, -16 - by * 16, bz * 16

        def t(face, x, y, z, view, x0=x0, y0=y0):
            if face == 'front':
                return g[min(15, max(0, fl(y) - y0))][min(15, max(0, fl(x) - x0))]
            return ('stone', 0)
        out.append(Box(x0, x0 + 16, y0, y0 + 16, z0, z0 + 16, 'p', 'x', t, 'blk%d' % i))
    return out


def flower_grid(petal):
    hl = {'r2': 'r1', 'p2': 'p1', 'y2': 'y1', 'white': 'white', 'u2': 'u1'}[petal]
    dk = {'r2': 'r3', 'p2': 'p3', 'y2': 'y3', 'white': 'c2', 'u2': 'u3'}[petal]
    P, L, D, Y = petal, hl, dk, ('y2' if petal != 'y2' else 'y3')
    return [
        [None, L, L, L, None],
        [L, P, P, P, D],
        [P, P, Y, P, D],
        [P, P, P, D, D],
        [None, D, 'g3', D, None],
        [None, 'g2', 'g3', None, None],
        ['g2', 'g3', 'g3', 'g2', None],
        [None, None, 'g3', None, None],
    ]


def bush(w, seed=9):
    def lf(face, x, y, z, view):
        return ('leaf', 1) if nz(seed, fl(x) // 2, fl(y) // 2, len(face)) < 0.15 else 'leaf'
    return [Box(-w // 2, w // 2, -10, 0, 2, 12, 'p', 'x', lf, 'b1'),
            Box(-w // 2 + 4, w // 2 - 6, -15, -10, 4, 10, 'p', 'x', lf, 'b2')]


# ===================================================================== layers
def build_sky():
    im = Image.new('RGBA', (16, WORLD_H), (0, 0, 0, 0))
    for c, a, b in (('k1', 0, 60), ('k2', 60, 110), ('k3', 110, 150), ('k4', 150, 185), ('k5', 185, WORLD_H)):
        fill(im, 0, a, 16, b, c)
    return im


def cloud(w, seed):
    def t(face, x, y, z, view):
        return ('cloud', 1) if fl(y) >= -2 and face == 'front' else 'cloud'
    a = int(w * 0.3)
    o = int(nz(seed, 1) * 10) - 5
    return [Box(-w // 2, w // 2, -8, 0, 0, 14, 'p', 'x', t, 'c1'),
            Box(-a + o, a + o, -16, -8, 2, 12, 'p', 'x', t, 'c2'),
            Box(-w // 2 + 6, -w // 2 + 6 + a, -13, -8, 3, 11, 'p', 'x', t, 'c3'),
            Box(a // 2 + o, a // 2 + o + 10, -21, -16, 4, 10, 'p', 'x', t, 'c4')]


def build_clouds():
    im = Image.new('RGBA', (640, 90), (0, 0, 0, 0))
    for x, y, w, s in ((60, 40, 60, 1), (210, 24, 84, 2), (350, 62, 44, 3), (470, 34, 70, 4), (590, 70, 50, 5)):
        place(im, cloud(w, s), x, y, wrap=True, W=140, H=50)
    return im


def build_far():
    W, H = 640, 100
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # 주기 640 높이 함수 -> 8px 열 단위, 6px 계단
    def hgt(cx):
        t = cx / W * 2 * math.pi
        v = 44 + 22 * math.sin(t * 2 + 0.6) + 14 * math.sin(t * 3 + 2.1) + 8 * math.sin(t * 5 + 0.3)
        return int(v // 6) * 6 + 6
    cols = [hgt(c * 8 + 4) for c in range(W // 8)]
    n = len(cols)
    for c in range(n):
        h = cols[c]
        top = H - h
        x0 = c * 8
        fill(im, x0, top, x0 + 8, H, 'm1')
        fill(im, x0, top, x0 + 8, top + 2, 'white')     # 윗면
        nxt = cols[(c + 1) % n]
        if nxt < h:                                      # 오른쪽으로 내려가면 옆면(어두운 톤) 2px
            fill(im, x0 + 6, top + 2, x0 + 8, H - nxt, 'k5')
        # 눈 덮인 봉우리 (높은 곳)
        if h >= 72:
            fill(im, x0, top, x0 + 8, top + 4, 'white')
    return im


def mid_tree(kind, seed):
    def lf(face, x, y, z, view):
        return ('midleaf', 1) if nz(seed, fl(x) // 2, fl(y) // 2, fl(z) // 2, len(face)) < 0.1 else 'midleaf'
    trunk = lambda *a: 'midwood'
    if kind == 0:
        return [Box(-3, 3, -22, 0, 6, 12, 'p', 'x', trunk, 't'),
                Box(-15, 15, -46, -20, 0, 18, 'p', 'x', lf, 'l1'),
                Box(-9, 9, -56, -46, 4, 14, 'p', 'x', lf, 'l2')]
    out = [Box(-2, 2, -10, 0, 6, 10, 'p', 'x', trunk, 't')]
    y = -8
    for i, (r, hh) in enumerate(((13, 14), (9, 12), (5, 12), (2, 5))):
        out.append(Box(-r, r, y - hh, y, 8 - r * 0.6, 8 + r * 0.6, 'p', 'x', lf, 'tier%d' % i))
        y -= hh - 2
    return out


def build_mid():
    W, H = 640, 110
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    base = H - 6     # 나무 밑동 행 (= 아트 y 216, 지면 뒤)
    x = 8
    i = 0
    while x < W - 8:
        k = int(nz(41, i) * 3) % 2
        s = 0.8 + nz(42, i) * 0.5
        place(im, mid_tree(k, 50 + i), x, base, wrap=True, W=90, H=90)
        x += 26 + int(nz(43, i) * 22)
        i += 1
    # 덤불 띠 (계단)
    for c in range(W // 4):
        h = 8 + int(nz(44, c // 3) * 3) * 3
        fill(im, c * 4, H - h, c * 4 + 4, H, 'm2')
        fill(im, c * 4, H - h, c * 4 + 4, H - h + 1, 'm1')
    return im


def build_ground():
    W, H = WORLD_W, WORLD_H - GROUND_LAYER_Y
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gt = GROUND_TOP - GROUND_LAYER_Y
    # 타일
    for tx in range(W // T):
        paste_grid(im, tile('grass', tx), tx * T, gt)
        for ty in range(1, 4):
            kind = 'stone' if (ty == 3 and nz(77, tx) < 0.45) or (ty == 2 and nz(78, tx) < 0.12) else 'dirt'
            paste_grid(im, tile(kind, tx * 4 + ty, seed=ty), tx * T, gt + ty * T)
    base = PROP_BASE - GROUND_LAYER_Y
    P = lambda boxes, x, W_=220, H_=200: place(im, boxes, x, base, W=W_, H=H_)
    # 뒤쪽 소품부터 (서로 겹치지 않게 배치)
    P(pine(1, 1.0), 26, 90, 120)
    P(oak(2, 1.0), 74, 90, 120)
    P(house('cap_red', w=70, h=76, d=28, seed=1), 162)
    P(fence(60), 228, 100, 60)
    P(lamp(), 314, 40, 90)
    P(house('cap_orange', w=56, h=62, d=22, seed=2, door_h=48, windows=1), 384)
    P(oak(3, 0.9), 454, 90, 120)
    P(stone_blocks([(0, 0, 0), (1, 0, 0), (0, 1, 0)]), 486, 80, 60)
    P(well(), 556, 70, 80)
    P(signpost(), 618, 50, 60)
    P(bush(30, 11), 650, 50, 40)
    P(house('cap_blue', w=74, h=80, d=30, seed=3), 722)
    P(pine(5, 1.1), 800, 90, 120)
    P(pine(6, 0.85), 834, 90, 120)
    P(lamp(), 870, 40, 90)
    P(house('cap_purple', w=62, h=68, d=24, seed=4, door_h=48), 950)
    P(fence(48), 1010, 90, 60)
    P(oak(7, 1.05), 1094, 90, 125)
    P(pine(8, 0.95), 1150, 90, 120)
    P(stone_blocks([(0, 0, 0), (1, 0, 0)]), 1168, 80, 50)
    P(bush(24, 12), 116, 50, 40)
    P(bush(26, 13), 1046, 50, 40)
    # 꽃 (밑동 행 217)
    for x, p in ((8, 'white'), (52, 'r2'), (100, 'p2'), (210, 'y2'), (232, 'r2'), (254, 'white'), (276, 'p2'),
                 (340, 'y2'), (430, 'r2'), (520, 'p2'), (600, 'white'), (676, 'y2'), (774, 'p2'),
                 (890, 'r2'), (906, 'white'), (1004, 'y2'), (1026, 'p2'), (1062, 'r2'), (1124, 'white'), (1190, 'y2')):
        g = flower_grid(p)
        paste_grid(im, g, x - 2, base - len(g))
    return im


def build(root):
    out = os.path.join(root, 'assets', 'map')
    os.makedirs(out, exist_ok=True)
    layers = [
        ('sky', build_sky(), 0.0, 0, True),
        ('clouds', build_clouds(), 0.1, 10, True),
        ('far', build_far(), 0.3, 122, True),
        ('mid', build_mid(), 0.6, 112, True),
        ('ground', build_ground(), 1.0, GROUND_LAYER_Y, False),
    ]
    man = {'scale': 2, 'groundY': GROUND_Y, 'width': WORLD_W, 'layers': []}
    imgs = {}
    for name, im, par, y, rep in layers:
        im.save(os.path.join(out, name + '.png'), optimize=False)
        man['layers'].append({'src': 'assets/map/%s.png' % name, 'parallax': par, 'y': y, 'repeatX': rep})
        imgs[name] = (im, y, rep)
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return man, imgs


def compose_world(imgs):
    """parallax 무시 전체 합성 (미리보기용)."""
    world = Image.new('RGBA', (WORLD_W, WORLD_H), (0, 0, 0, 255))
    for name in ('sky', 'clouds', 'far', 'mid', 'ground'):
        im, y, rep = imgs[name]
        if rep:
            for x in range(0, WORLD_W, im.width):
                world.alpha_composite(im, (x, y))
        else:
            world.alpha_composite(im, (0, y))
    return world
