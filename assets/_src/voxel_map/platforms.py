"""버섯마을 발판(플랫폼) 정본 + 복셀 모델 (사이클 8).

PLATFORMS 표가 정본이다. build.py 가 manifest `platforms` 를 이 표에서 쓰고(id, x1, x2, y),
scene.py 가 같은 값으로 발판 모델을 만든다. check.py 는 렌더 마스크로 그림과 좌표가 맞는지 검사한다.

지면 레이어 좌표: 모델 1단위 = 월드 2, 원점 = 월드 (0, 440), 시점 pitch 15도(직교).
화면 월드 y = 440 - 2 * (cos15 * Y - sin15 * Z).  발판 윗면 높이 Y 는 '서는 선' 깊이 z0 에서
화면 y 가 정확히 발판 y 가 되도록 정한다(top_Y). 윗면은 z0 앞뒤로 펼쳐져 있어 발이 윗면 위에 놓여 보인다.
x 는 회전 없이 모델 x = 월드 x / 2 이므로 윗면 좌우 끝 = x1, x2 그대로.
"""
import numpy as np
from vox import Box, rot_z, rot_x, hex2lin
import props as P
from props import B, BR, placed, octo

GROUND_Y = 440
C15, S15 = np.cos(np.radians(15.0)), np.sin(np.radians(15.0))

GRASS = ('#7FD04A', '#86D650', '#78C846', '#8FDB58', '#74C244')
GRASS_HI = ('#98DE60', '#A0E266', '#8FDB58')
DIRT = ('#7E4A2C', '#714126', '#87522F', '#784530')
STONE = ('#8A849A', '#7C7690', '#948EA6', '#857F95')
WOOD_TOP = ('#E0A868', '#D69A5A', '#E8B478', '#DDA262')

# kind: shelf(나무 선반) | house(버섯 집 갓 윗면) | island(떠 있는 잔디 섬) | bridge(흔들다리) | cliff(잔디 단구)
# secret: 슈퍼 점프(최고 약 225)로만 닿는 높은 발판
PLATFORMS = [
    dict(id='shelf-left', kind='shelf', x1=120, x2=260, y=350),
    dict(id='red-cap', kind='house', x1=320, x2=460, y=260, cap='red'),
    dict(id='isle-cherry', kind='island', x1=490, x2=640, y=170),
    dict(id='orange-cap', kind='house', x1=790, x2=910, y=350, cap='orange'),
    dict(id='rope-bridge', kind='bridge', x1=940, x2=1210, y=260),
    dict(id='isle-falls', kind='island', x1=1240, x2=1390, y=170),
    dict(id='blue-cap', kind='house', x1=1640, x2=1780, y=260, cap='blue'),
    dict(id='cliff-right', kind='cliff', x1=1840, x2=2020, y=350),
    dict(id='secret-sky', kind='island', x1=230, x2=320, y=85, secret=True),
    dict(id='secret-chest', kind='island', x1=1540, x2=1630, y=100, secret=True),
]


def top_Y(y, z0):
    """서는 선 깊이 z0 에서 화면 y 가 월드 y 가 되는 윗면 높이(모델 단위)."""
    return ((GROUND_Y - y) / 2 + S15 * z0) / C15


def _strip(rng, x1, x2, wmin, wmax):
    """x1~x2 를 정확히 덮는 블록 구간들."""
    xs = [x1]
    while xs[-1] < x2 - 1e-6:
        xs.append(min(x2, xs[-1] + float(rng.uniform(wmin, wmax))))
    if len(xs) > 2 and xs[-1] - xs[-2] < wmin * 0.5:     # 너무 얇은 마지막 조각은 합친다
        xs.pop(-2)
    return list(zip(xs[:-1], xs[1:]))


def _pick(rng, pal):
    return pal[int(rng.integers(0, len(pal)))]


# ---------------------------------------------------------------- 나무 선반
def shelf(p, seed=0, z0=-20.0):
    rng = np.random.default_rng(seed)
    x1, x2 = p['x1'] / 2, p['x2'] / 2
    Yt = top_Y(p['y'], z0)
    zf, zb = z0 + 4.5, z0 - 11.0
    zc, dz = (zf + zb) / 2, zf - zb
    bx = []
    th = 2.6
    for (a, b) in _strip(rng, x1, x2, 5.0, 8.0):
        bx.append(B((a + b) / 2, Yt - th / 2, zc + rng.uniform(-0.2, 0.2) * 0, b - a, th, dz, _pick(rng, WOOD_TOP),
                    noise=0.09, bevel=0.45, tag='top'))
        # 못 자국
        for zz in (zf - 2.2, zb + 2.2):
            bx.append(B((a + b) / 2, Yt + 0.02, zz, 0.7, 0.2, 0.7, '#8A5232', bevel=0.05, noise=0, decal=True, tag='top'))
    cx, w = (x1 + x2) / 2, x2 - x1
    # 앞 띠판 + 아래 보
    bx.append(B(cx, Yt - th - 1.5, zf - 0.9, w - 0.6, 3.0, 1.8, 'wood3', noise=0.08))
    bx.append(B(cx, Yt - th - 1.6, zb + 1.6, w - 2, 3.2, 3.2, 'wood3', noise=0.08))
    # 기둥 4개 + 가새 (지면까지)
    ytop = Yt - th - 3.0
    for px in (x1 + 3.2, x2 - 3.2):
        for pz, col in ((zf - 2.6, 'wood2'), (zb + 2.4, 'wood3')):
            bx.append(B(px, ytop / 2, pz, 3.2, ytop, 3.2, col, noise=0.1))
        bx.append(B(px, 1.0, zf - 2.6, 4.6, 2.0, 4.6, 'stone2', noise=0.1))
    # X 가새 (앞)
    L = np.hypot(w - 6.4, ytop * 0.45)
    ang = np.degrees(np.arctan2(ytop * 0.45, w - 6.4))
    for sgn in (-1, 1):
        bx.append(BR(cx, ytop * 0.6, zf - 2.0, L, 1.6, 1.2, 'wood3', rot_z(sgn * ang), noise=0.06, bevel=0.2))
    bx.append(B(cx, ytop * 0.2, zf - 2.0, w - 6.4, 1.8, 1.4, 'wood3', noise=0.06, bevel=0.2))
    # 덩굴/잎 매달림
    for k in range(5):
        vx = rng.uniform(x1 + 2, x2 - 2); ln = rng.uniform(3, 9)
        bx.append(B(vx, Yt - th - ln / 2, zf + 0.2, 1.4, ln, 1.0, _pick(rng, ('leaf3', 'leaf4', 'leaf2')), noise=0.05,
                    bevel=0.2))
        bx.append(B(vx + rng.uniform(-1, 1), Yt - th - ln, zf + 0.4, 2.4, 2.0, 1.4, 'leaf2', noise=0.05, bevel=0.3))
    # 매단 랜턴 (앞 띠판 아래 가운데)
    bx += placed(hanging_lantern(), cx + w * 0.28, Yt - th - 3.0, zf - 1.0)
    # 위 소품 (뒤쪽): 화분 2 + 작은 버섯
    bx += placed(flower_pot(seed + 1, 'pink3'), x1 + 6, Yt, zb + 3.5)
    bx += placed(flower_pot(seed + 2, 'yellow'), x1 + 12, Yt, zb + 3.2)
    bx += placed(P.mushroom_small(seed + 3, 'red', 0.9), x2 - 7, Yt, zb + 3.5, 12)
    return bx


# ---------------------------------------------------------------- 떠 있는 잔디 섬
def island(p, seed=0, z0=-24.0, depth=28.0, under=None):
    rng = np.random.default_rng(seed)
    x1, x2 = p['x1'] / 2, p['x2'] / 2
    Yt = top_Y(p['y'], z0)
    zf = z0 + 5.0
    zb = zf - depth
    zc = (zf + zb) / 2
    w = x2 - x1
    cx = (x1 + x2) / 2
    bx = []
    # 윗면 잔디 (앞줄은 정확히 x1~x2, 뒷줄은 들쭉날쭉)
    zm = zf - 12.0
    for (a, b) in _strip(rng, x1, x2, 5.0, 10.0):
        col = _pick(rng, GRASS if rng.random() < 0.75 else GRASS_HI)
        bx.append(B((a + b) / 2, Yt - 2.5, (zf + zm) / 2, b - a, 5.0, zf - zm, col, noise=0.05, tag='top'))
    for (a, b) in _strip(rng, x1 + 1.5, x2 - 1.5, 4.0, 9.0):
        back = zb + rng.uniform(-1.5, 3.5)
        bx.append(B((a + b) / 2, Yt - 2.5 - rng.choice([0.0, 0.0, 0.6]), (zm + back) / 2, b - a, 5.0, zm - back,
                    _pick(rng, GRASS), noise=0.05))
    # 잔디 술(앞면 윗단 늘어짐)
    x = x1 + 1
    while x < x2 - 2:
        ww = rng.uniform(2, 4.5); hh = rng.uniform(1.5, 3.2)
        bx.append(B(min(x + ww / 2, x2 - ww / 2), Yt - 5 - hh / 2 + 0.4, zf + 0.35, ww, hh, 1.0, _pick(rng, GRASS[:3]),
                    noise=0.04, bevel=0.25))
        x += ww + rng.uniform(1.5, 5)
    # 아래: 흙 → 돌, 점점 좁아지는 역피라미드 (블록 결)
    y = Yt - 5.0
    layers = under or [(0.6, 5.5, DIRT), (0.07, 6.0, DIRT), (0.16, 6.0, STONE), (0.26, 6.0, STONE), (0.35, 5.5, STONE),
                       (0.43, 5.0, STONE)]
    off = 0.0
    for li, (ins, h, pal) in enumerate(layers):
        inset = ins if ins >= 0.5 else ins * w + 1.5
        lw = w - 2 * inset
        if lw < 5:
            break
        off += rng.uniform(-0.04, 0.04) * w
        ld = depth * max(0.45, 1 - li * 0.11)
        dk = 1 - 0.07 * li
        for (a, b) in _strip(rng, cx + off - lw / 2, cx + off + lw / 2, 4.0, 8.0):
            col = hex2lin(_pick(rng, pal)) * dk
            bx.append(Box(((a + b) / 2, y - h / 2, zc + li * 0.6), ((b - a) / 2, h / 2, ld / 2), None, col, noise=0.07))
        # 박힌 돌/뿌리
        if li < 2:
            for k in range(int(lw / 10)):
                sx = rng.uniform(cx + off - lw / 2 + 2, cx + off + lw / 2 - 2)
                s = rng.uniform(1.4, 2.6)
                bx.append(B(sx, y - h * rng.uniform(0.3, 0.7), zc + li * 0.6 + ld / 2 + 0.2, s, s * 0.8, 0.8,
                            _pick(rng, STONE), noise=0.05, bevel=0.2))
        y -= h
    bottom = y
    # 덩굴
    for k in range(int(w / 9)):
        vx = rng.uniform(x1 + 4, x2 - 4); ln = rng.uniform(5, 16)
        vz = zf + 0.2 if abs(vx - cx) > w * 0.36 else zc + depth * 0.5 + 0.3
        top_ = Yt - 5.0
        bx.append(B(vx, top_ - ln / 2, vz, 1.3, ln, 1.0, _pick(rng, ('leaf3', 'leaf4')), noise=0.05, bevel=0.2))
        for j in range(int(ln / 4)):
            bx.append(B(vx + rng.choice([-1.1, 1.1]), top_ - 2 - j * 4, vz + 0.2, 2.0, 1.6, 1.2, 'leaf2', noise=0.05,
                        bevel=0.3))
        if rng.random() < 0.4:
            bx.append(B(vx, top_ - ln - 0.6, vz + 0.3, 2.0, 2.0, 1.6, _pick(rng, ('pink2', 'white', 'yellow')),
                        bevel=0.3, noise=0.03))
    return bx, dict(Yt=Yt, zf=zf, zb=zb, zc=zc, bottom=bottom, cx=cx, w=w)


# ---------------------------------------------------------------- 흔들다리
ROPE = '#D9B98A'


def bridge(p, seed=0, z0=-22.0):
    rng = np.random.default_rng(seed)
    x1, x2 = p['x1'] / 2, p['x2'] / 2
    Yt = top_Y(p['y'], z0)
    zf, zb = z0 + 4.0, z0 - 9.0
    zc, dz = (zf + zb) / 2, zf - zb
    bx = []
    # 발판 널
    i = 0
    for (a, b) in _strip(rng, x1, x2, 3.0, 3.6):
        col = WOOD_TOP[i % 2] if rng.random() < 0.8 else '#C98E54'
        bx.append(B((a + b) / 2, Yt - 1.1, zc + rng.uniform(-0.6, 0.6), b - a, 2.2, dz - 1.2 + rng.uniform(0, 1.0), col,
                    noise=0.08, bevel=0.4, tag='top'))
        i += 1
    # 널 아래 받침 밧줄 2줄
    for zz in (zf - 1.2, zb + 1.2):
        bx.append(B((x1 + x2) / 2, Yt - 2.6, zz, x2 - x1, 1.0, 1.0, '#8A5232', noise=0.04, bevel=0.2))
    # 양 끝 받침: 돌 기둥 (지면에서) + 나무 기둥
    piers = []
    for (pa, pb) in ((x1, x1 + 15), (x2 - 15, x2)):
        pc = (pa + pb) / 2
        piers.append(pc)
        ytop = Yt - 3.2
        yy = 0.0
        k = 0
        while yy < ytop - 0.01:
            h = min(rng.uniform(4.5, 6.0), ytop - yy)
            ww = 15.0 - 2.0 * (1 - yy / ytop) * 0 + (1.6 if k < 2 else 0.0)
            sp = pc - ww / 2 + (ww * (0.38 if k % 2 else 0.62)) + rng.uniform(-1, 1)
            for (a, b_) in ((pc - ww / 2, sp), (sp, pc + ww / 2)):
                col = hex2lin(_pick(rng, STONE + ('#A8A2B8', '#9A94AC'))) * (0.9 + 0.1 * yy / ytop)
                if rng.random() < 0.12:
                    col = hex2lin(_pick(rng, ('#7FA86A', '#6E9A5E')))        # 이끼 낀 돌
                bx.append(Box(((a + b_) / 2, yy + h / 2, zc - 3.0), ((b_ - a) / 2, h / 2, 7.0 + (0.8 if k < 2 else 0)),
                              None, col, noise=0.08))
            yy += h; k += 1
        # 이끼 띠 + 덩굴
        bx.append(B(pc, ytop - 1.0, zc - 3.0, 15.0, 2.2, 14.6, 'leaf3', noise=0.06))
        for j in range(3):
            ln = rng.uniform(6, 18)
            bx.append(B(pc + rng.uniform(-5.5, 5.5), ytop - 2 - ln / 2, zc + 4.2, 1.3, ln, 1.0, 'leaf4', noise=0.05,
                        bevel=0.2))
        # 나무 기둥 (난간 지지) 앞/뒤
        for pz in (zf + 0.6, zb - 0.6):
            bx.append(B(pc, Yt + 9.0, pz, 2.8, 22.0, 2.8, 'wood3', noise=0.1))
            bx.append(B(pc, Yt + 20.6, pz, 3.6, 1.4, 3.6, 'wood4', noise=0.06))
    # 앞 기둥 위 랜턴 (왼쪽)
    bx += placed(lantern_top(), piers[0], Yt + 21.3, zb - 0.6)
    bx += placed(lantern_top(), piers[1], Yt + 21.3, zb - 0.6)
    # 난간 밧줄 (처짐) + 세로 줄
    xa, xb = piers[0], piers[1]
    n = int((xb - xa) / 1.6)
    for pz, top in ((zf + 0.6, Yt + 16.5), (zb - 0.6, Yt + 16.5)):
        prev = None
        for k in range(n + 1):
            t = k / n
            xx = xa + (xb - xa) * t
            yy = top - 9.0 * (1 - (2 * t - 1) ** 2)
            bx.append(B(xx, yy, pz, 1.9, 0.9, 0.9, ROPE, noise=0.03, bevel=0.2))
            if k % 6 == 3 and pz < zc:
                hh = yy - Yt
                bx.append(B(xx, Yt + hh / 2, pz, 0.6, hh, 0.6, ROPE, noise=0.0, bevel=0.1))
    return bx


def lantern_top():
    """기둥 꼭대기에 얹는 작은 랜턴."""
    bx = []
    for sx in (-2.2, 2.2):
        for sz in (-2.2, 2.2):
            bx.append(B(sx, 3.6, sz, 1.0, 6.4, 1.0, 'ink', bevel=0.15, noise=0.03))
    bx.append(B(0, 3.6, 0, 4.2, 6.0, 4.2, 'glass', noise=0.05, emit=('#FFB850', 1.5)))
    bx.append(B(0, 7.2, 0, 6.2, 1.2, 6.2, 'wood4', noise=0.05))
    bx.append(B(0, 8.4, 0, 3.8, 1.2, 3.8, 'wood4', noise=0.05))
    return bx


def hanging_lantern():
    """원점 = 매다는 점. 아래로 늘어진다."""
    bx = [B(0, -2.0, 0, 0.5, 4.0, 0.5, 'ink', bevel=0.1, noise=0)]
    bx.append(B(0, -4.4, 0, 4.6, 1.0, 4.6, 'wood4', noise=0.05))
    bx.append(B(0, -7.6, 0, 3.8, 5.4, 3.8, 'glass', noise=0.05, emit=('#FFB850', 1.4)))
    for sx in (-1.9, 1.9):
        bx.append(B(sx, -7.6, 1.9, 0.7, 5.6, 0.7, 'ink', bevel=0.1, noise=0.02))
    bx.append(B(0, -10.6, 0, 4.4, 1.0, 4.4, 'wood4', noise=0.05))
    return bx


def flower_pot(seed=0, col='pink3'):
    rng = np.random.default_rng(seed)
    bx = [B(0, 1.8, 0, 4.4, 3.6, 4.4, '#C0603A', noise=0.08, bevel=0.3),
          B(0, 3.8, 0, 5.0, 0.8, 5.0, '#A84A2E', noise=0.05, bevel=0.2),
          B(0, 4.2, 0, 3.6, 0.4, 3.6, 'wood4', noise=0.0, bevel=0.1)]
    for k in range(4):
        x, z = rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4)
        bx.append(B(x, 5.3, z, 0.6, 2.2, 0.6, 'leaf4', bevel=0.1, noise=0))
        bx.append(B(x, 6.8, z, 2.0, 1.6, 2.0, col if k % 3 else 'white', bevel=0.3, noise=0.04))
    return bx


# ---------------------------------------------------------------- 잔디 단구 (지면에서 솟은 절벽)
def cliff(p, seed=0, z0=-24.0, depth=34.0):
    rng = np.random.default_rng(seed)
    x1, x2 = p['x1'] / 2, p['x2'] / 2
    Yt = top_Y(p['y'], z0)
    zf = z0 + 5.0
    zb = zf - depth
    zc = (zf + zb) / 2
    w = x2 - x1
    bx = []
    zm = zf - 12.0
    for (a, b) in _strip(rng, x1, x2, 6.0, 11.0):
        bx.append(B((a + b) / 2, Yt - 2.5, (zf + zm) / 2, b - a, 5.0, zf - zm,
                    _pick(rng, GRASS if rng.random() < 0.75 else GRASS_HI), noise=0.05, tag='top'))
    for (a, b) in _strip(rng, x1, x2, 5.0, 10.0):
        back = zb + rng.uniform(-1, 2.5)
        bx.append(B((a + b) / 2, Yt - 2.5, (zm + back) / 2, b - a, 5.0, zm - back, _pick(rng, GRASS), noise=0.05))
    x = x1 + 1
    while x < x2 - 2:
        ww = rng.uniform(2, 4.5); hh = rng.uniform(1.5, 3.4)
        bx.append(B(min(x + ww / 2, x2 - ww / 2), Yt - 5 - hh / 2 + 0.4, zf + 0.35, ww, hh, 1.0, _pick(rng, GRASS[:3]),
                    noise=0.04, bevel=0.25))
        x += ww + rng.uniform(1.5, 5)
    # 앞면: 흙/돌 벽돌 (지면까지)
    y = Yt - 5.0
    k = 0
    while y > 0.01:
        h = min(7.0, y)
        p_stone = min(0.65, 0.08 + k * 0.1)
        for (a, b) in _strip(rng, x1 + 0.3, x2 - 0.3, 6.0, 12.0):
            pal = STONE if rng.random() < p_stone else DIRT
            col = hex2lin(_pick(rng, pal)) * (1 - 0.035 * k)
            bx.append(Box(((a + b) / 2, y - h / 2, zc - 0.5), ((b - a) / 2, h / 2, (depth - 1) / 2), None, col,
                          noise=0.07))
        y -= h; k += 1
    # 사다리 (장식)
    lx = x1 + w * 0.7
    for sx in (-3.4, 3.4):
        bx.append(B(lx + sx, (Yt - 3) / 2, zf + 0.6, 1.4, Yt - 3, 1.4, 'wood2', noise=0.08, bevel=0.2))
    yy = 3.0
    while yy < Yt - 4:
        bx.append(B(lx, yy, zf + 0.9, 7.4, 1.1, 1.1, 'wood1', noise=0.06, bevel=0.2))
        yy += 4.4
    # 덩굴 + 꽃
    for k in range(9):
        vx = rng.uniform(x1 + 3, x2 - 3)
        if abs(vx - lx) < 6:
            continue
        ln = rng.uniform(6, 22)
        bx.append(B(vx, Yt - 5 - ln / 2, zf + 0.3, 1.4, ln, 1.0, _pick(rng, ('leaf3', 'leaf4')), noise=0.05, bevel=0.2))
        for j in range(int(ln / 5)):
            bx.append(B(vx + rng.choice([-1.1, 1.1]), Yt - 7 - j * 5, zf + 0.5, 2.0, 1.6, 1.2, 'leaf2', noise=0.05,
                        bevel=0.3))
        if rng.random() < 0.5:
            bx.append(B(vx, Yt - 5 - ln - 0.6, zf + 0.6, 2.2, 2.2, 1.6, _pick(rng, ('pink2', 'white', 'yellow')),
                        bevel=0.3, noise=0.03))
    return bx, dict(Yt=Yt, zf=zf, zb=zb, x1=x1, x2=x2)


# ---------------------------------------------------------------- 버섯 집 (갓 윗면 = 발판)
def house(p, seed=0, z0=-22.0, s=1.0, stem_w=48.0):
    """갓 맨 위 슬랩 너비 = x2 - x1(월드) 가 되도록 슬랩을 짜고, 서는 선 z0 에서 화면 y 가 맞도록 기둥 높이를 정한다."""
    x1, x2 = p['x1'] / 2, p['x2'] / 2
    tw = (x2 - x1) / s                         # 로컬 단위 윗면 너비
    td = tw * 0.82
    cut = 0.15
    slabs = [(tw + 36, 4, td + 28), (tw + 40, 6, td + 32), (tw + 37, 6, td + 29), (tw + 31, 6, td + 24),
             (tw + 23, 6, td + 17), (tw + 14, 6, td + 10), (tw + 6, 5, td + 4), (tw, 4, td)]
    zoff = td / 2 * (1 - 2 * cut) - 3.0        # 집 중심에서 서는 선까지 (로컬, 앞쪽 +)
    Yt = top_Y(p['y'], z0)
    H = Yt / s - sum(sl[1] for sl in slabs)
    info = {}
    hb = P.mushroom_house(p['cap'], H, seed=seed, chimney=False, slabs=slabs, top_cut=cut, info=info, sw=stem_w)
    zc = z0 - zoff * s
    return placed(hb, (x1 + x2) / 2, 0, zc, 0.0, s), dict(Yt=Yt, zc=zc, z0=z0, H=H, s=s, info=info)


# ---------------------------------------------------------------- 보상 장식 (비밀 발판)
def golden_mushroom(s=1.0):
    bx = [B(0, 2.6 * s, 0, 3.2 * s, 5.2 * s, 3.2 * s, 'cream', noise=0.03),
          B(0, 6.0 * s, 0, 9.0 * s, 2.6 * s, 9.0 * s, '#FFD24A', noise=0.04, emit=('#FFC23A', 0.35)),
          B(0, 7.9 * s, 0, 6.0 * s, 1.6 * s, 6.0 * s, '#FFE27A', noise=0.04, emit=('#FFD25A', 0.35)),
          B(-2.0 * s, 6.3 * s, 4.55 * s, 1.6 * s, 1.4 * s, 0.4, 'white', bevel=0.1, noise=0),
          B(2.2 * s, 6.5 * s, 4.55 * s, 1.2 * s, 1.2 * s, 0.4, 'white', bevel=0.1, noise=0)]
    return bx


def sparkles(seed, w, h, n=8):
    rng = np.random.default_rng(seed)
    bx = []
    for k in range(n):
        x, y = rng.uniform(-w / 2, w / 2), rng.uniform(2, h)
        s = rng.uniform(0.8, 1.5)
        bx.append(BR(x, y, rng.uniform(-2, 4), s, s, s, '#FFF4C0', rot_z(45), bevel=0.1, noise=0,
                     emit=('#FFE8A0', 1.2)))
    return bx


def chest():
    bx = [B(0, 3.0, 0, 10, 6.0, 7, '#B97A4A', noise=0.08),
          B(0, 7.2, -0.6, 10.4, 2.6, 7.4, '#C98E54', noise=0.08),
          B(0, 8.8, -1.0, 9.0, 1.4, 6.0, '#C98E54', noise=0.08)]
    for sx in (-4.0, 4.0):
        bx.append(B(sx, 5.0, 3.6, 1.2, 9.0, 0.6, '#F7C948', noise=0.02, bevel=0.15))
    bx.append(B(0, 6.0, 3.8, 2.0, 2.4, 0.8, '#F7C948', noise=0.02, bevel=0.2, emit=('#FFD25A', 0.3)))
    # 열린 틈에서 새는 빛
    bx.append(B(0, 6.1, 3.2, 8.0, 0.4, 0.3, '#FFF2A8', noise=0, bevel=0.05, emit=('#FFE08A', 1.2)))
    return bx


# ---------------------------------------------------------------- 전체 발판 모델
def build_all():
    """(boxes, info dict by id)."""
    bx, info = [], {}
    for i, p in enumerate(PLATFORMS):
        sd = 500 + i * 17
        k = p['kind']
        if k == 'shelf':
            bx += shelf(p, sd)
        elif k == 'bridge':
            bx += bridge(p, sd)
        elif k == 'house':
            hut = p['y'] >= 340
            hb, inf = house(p, sd, s=0.5 if hut else 1.0, stem_w=66.0 if hut else 50.0)
            bx += hb; info[p['id']] = inf
        elif k == 'cliff':
            cb, inf = cliff(p, sd)
            bx += cb; info[p['id']] = inf
        elif k == 'island':
            depth = 22.0 if p.get('secret') else 28.0
            ib, inf = island(p, sd, depth=depth)
            bx += ib; info[p['id']] = inf
    return bx, info
