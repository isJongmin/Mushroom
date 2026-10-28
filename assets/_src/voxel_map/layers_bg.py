"""배경 레이어 (사이클 10): sky(그라데이션), clouds(볼륨 구름), far(대기원근 능선 + 침엽수림), mid(숲 언덕).

모델 1단위 = 월드 1 = 1.5px (scale 1.5). 반복 레이어는 period(px) 주기로 상자를 좌우 복제해 렌더하므로 이음매 없이
이어진다. 높이장/분포는 주기 함수와 좌표 해시만 쓴다(결정적).
"""
import numpy as np
from PIL import Image
from vox import Cfg, hex2lin, lin2srgb
from common import B, BR, placed, pick, vol_boxes, ellipsoid_grid, cell_hash, C
import props as P

TAU = 2 * np.pi

# ====================================================================== sky
SKY_STOPS = [(0.00, '#94B3C8'), (0.18, '#A6C0CE'), (0.36, '#BFCED2'), (0.50, '#D9D6CC'), (0.62, '#EED8C2'),
             (0.74, '#F8D3B2'), (0.86, '#F9CBA4'), (1.00, '#F4C39E')]


def sky_image(W=16, H=1500):
    t = (np.arange(H) + 0.5) / H
    pos = np.array([s[0] for s in SKY_STOPS]); cols = np.array([hex2lin(s[1]) for s in SKY_STOPS])
    lin = np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], -1)
    srgb = lin2srgb(lin)
    bay = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
    img = np.repeat(srgb[:, None, :], W, 1) * 255
    img += bay[np.arange(H)[:, None] % 4, np.arange(W)[None, :] % 4][..., None] * 0.9
    img = np.clip(np.round(img), 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([img, np.full((H, W), 255, np.uint8)]), 'RGBA')


# ====================================================================== clouds
def cloud(seed, w, cell=4.0):
    """볼륨 적운: 평평한 바닥 + 둥근 퍼프 여러 개(타원체 합집합)를 복셀로."""
    rng = np.random.default_rng(seed)
    h = w * 0.42
    d = w * 0.36
    nx, ny, nz = int(w / cell) + 4, int(h / cell) + 4, int(d / cell) + 4
    xs = (np.arange(nx) + 0.5) * cell - nx * cell / 2
    ys = (np.arange(ny) + 0.5) * cell
    zs = (np.arange(nz) + 0.5) * cell - nz * cell / 2
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    m = np.zeros(X.shape, bool)
    puffs = [(0.0, h * 0.18, 0.0, w * 0.48, h * 0.22, d * 0.45)]        # 바닥 판
    n = 3 + int(w / 90)
    for k in range(n):
        fx = ((k + 0.5) / n * 2 - 1) * 0.34 * w + rng.uniform(-0.03, 0.03) * w
        edge = abs(fx) / (0.34 * w)
        r = w * rng.uniform(0.15, 0.2) * (1 - 0.35 * edge)
        puffs.append((fx, h * 0.28 + r * 0.55 * (1 - 0.3 * edge), rng.uniform(-0.1, 0.1) * d, r * 1.15, r, min(r, d * 0.5)))
    for k in range(1 + int(w / 160)):
        fx = rng.uniform(-0.14, 0.14) * w
        r = w * rng.uniform(0.17, 0.22)
        puffs.append((fx, h * 0.45 + r * 0.6, rng.uniform(-0.06, 0.06) * d, r * 1.1, r, min(r, d * 0.5)))
    for (px, py, pz, rx, ry, rz) in puffs:
        m |= ((X - px) / rx) ** 2 + ((Y - py) / ry) ** 2 + ((Z - pz) / rz) ** 2 <= 1
    m &= Y >= cell * 0.5 + h * 0.02          # 바닥 평평하게
    hs = cell_hash(X, Y, Z, seed, cell * 2)
    idx = np.where(m, np.where(hs < 0.22, 2, np.where(hs > 0.9, 3, 1)), 0).astype(np.int16)
    return vol_boxes(idx, ['#FFF4E6', '#FCEBDA', '#FFFAF2'], (-nx * cell / 2, 0.0, -nz * cell / 2), cell,
                     noise=0.015, bevel=0.9)


def clouds_scene(period_u):
    bx = []
    # (x 비율, y(모델, 위로 +), 너비)
    items = [(0.04, 330, 300), (0.20, 410, 130), (0.33, 250, 220), (0.47, 380, 170), (0.60, 300, 340), (0.74, 430, 110),
             (0.84, 260, 200), (0.95, 390, 150)]
    for i, (fx, y, w) in enumerate(items):
        bx += placed(cloud(300 + i, w), fx * period_u, y - w * 0.2, -60 - i * 9)
    return bx


# ====================================================================== 공용: 침엽수/둥근 나무 (원경용 단순 모델)
def conifer(seed, h, r, pal=('pine2', 'pine1', 'pine3'), cell=2.0):
    """층층 원뿔 침엽수 (계단 복셀)."""
    rng = np.random.default_rng(seed)
    bx = [B(0, h * 0.06, 0, max(cell, r * 0.18), h * 0.12, max(cell, r * 0.18), 'wood3', noise=0.05)]
    tiers = 4 if h > 30 else 3
    y = h * 0.1
    for t in range(tiers):
        f = t / tiers
        tw = r * 2 * (1 - f * 0.72)
        th = (h * 0.9) / tiers * 1.25
        steps = max(2, int(th / cell))
        for s in range(steps):
            ww = tw * (1 - s / steps * 0.62)
            ww = max(cell, round(ww / cell) * cell)
            c = pal[(t + s) % 2] if s < steps - 1 else pal[0]
            if s == 0:
                c = pal[2]
            bx.append(B(0, y + (s + 0.5) * cell, 0, ww, cell, ww * 0.9, c, noise=0.04))
        y += th * 0.72
    bx.append(B(0, y + cell * 0.5, 0, cell, cell * 1.5, cell, pal[1], noise=0.03))
    return bx


def round_tree(seed, h, r, pal=('leaf3', 'leaf2', 'leaf4'), cell=2.0, trunk='wood3'):
    rng = np.random.default_rng(seed)
    bx = [B(0, h * 0.25, 0, max(cell, r * 0.22), h * 0.5, max(cell, r * 0.22), trunk, noise=0.05)]
    m, (X, Y, Z), org = ellipsoid_grid(r, r * 0.85, r * 0.8, cell)
    hs = cell_hash(X, Y, Z, seed, cell * 2)
    idx = np.where(m, np.where(Y > r * 0.35, 2, np.where(hs < 0.3, 3, 1)), 0).astype(np.int16)
    bx += placed(vol_boxes(idx, list(pal), org, cell, noise=0.04), 0, h * 0.45 + r * 0.6, 0)
    return bx


# ====================================================================== far
def ridge_columns(period_u, z_front, depth, cell_x, cell_z, hfun, cols, seed, trees=None):
    """x-z 높이장 기둥 지형 (앞으로 갈수록 낮아짐). hfun(x, zrel 0=뒤..1=앞) -> 높이."""
    rng = np.random.default_rng(seed)
    bx = []
    nz = int(depth / cell_z)
    nxc = int(round(period_u / cell_x))
    cx_ = period_u / nxc
    tops = []
    for k in range(nz):
        zr = (k + 0.5) / nz
        z = z_front - depth + (k + 0.5) * cell_z
        for i in range(nxc):
            x = (i + 0.5) * cx_
            hgt = max(4.0, round(hfun(x, zr) / 4) * 4)
            c = cols[0] if zr < 0.5 else cols[1]
            bx.append(B(x, hgt / 2, z, cx_ + 0.02, hgt, cell_z + 0.02, c, noise=0.035, bevel=0.6))
            tops.append((x, hgt, z))
    if trees:
        dens, hmin, hmax, pal = trees
        for (x, hgt, z) in tops:
            if rng.random() < dens:
                th = rng.uniform(hmin, hmax)
                bx += placed(conifer(int(rng.integers(1 << 30)), th, th * 0.3, pal), x + rng.uniform(-cx_ / 3, cx_ / 3),
                             hgt - 1, z + rng.uniform(-cell_z / 3, cell_z / 3))
    return bx


def far_scene(period_u):
    """모델 원점 y = 월드 940. 위로 + . 주기 period_u."""
    bx = []

    def per(x, terms):
        f = x / period_u * TAU
        return sum(a * np.sin(f * n + p) for (n, a, p) in terms)

    # 가장 먼 능선 (산): 뾰족 봉우리 + 완만한 어깨
    def h_back(x, zr):
        base = 330 + per(x, [(3, 70, 0.4), (5, 46, 2.1), (11, 22, 0.7), (17, 10, 1.3)])
        peaks = 0.0
        for (fx, ph, pw) in ((0.08, 170, 0.05), (0.27, 120, 0.04), (0.46, 190, 0.055), (0.63, 110, 0.04),
                             (0.81, 160, 0.05), (0.93, 90, 0.035)):
            dxp = (x / period_u - fx + 0.5) % 1 - 0.5
            peaks = max(peaks, ph * max(0.0, 1 - abs(dxp) / pw))
        return (base + peaks) * (1 - 0.25 * zr)
    bx += ridge_columns(period_u, -520, 80, 6, 20, h_back, ('#A9B3C6', '#B3BCCB'), 11,
                        trees=(0.18, 18, 30, ('#8E9EAF', '#9AA9B8', '#8293A6')))

    # 중간 능선: 침엽수 숲 경사
    def h_midr(x, zr):
        return (215 + per(x, [(4, 60, 1.2), (7, 34, 0.2), (13, 16, 2.4), (23, 7, 0.4)])) * (1 - 0.45 * zr)
    bx += ridge_columns(period_u, -330, 90, 6, 15, h_midr, ('#8FA7A2', '#98AFA5'), 12,
                        trees=(0.62, 20, 36, ('#6F8F84', '#7C9B8E', '#62827A')))

    # 앞 능선: 낮은 숲 언덕
    def h_front(x, zr):
        return (120 + per(x, [(5, 34, 2.0), (9, 20, 0.9), (19, 9, 1.7)])) * (1 - 0.5 * zr)
    bx += ridge_columns(period_u, -170, 70, 6, 14, h_front, ('#7F9E86', '#88A68A'), 13,
                        trees=(0.8, 22, 40, ('#5E866C', '#6B9276', '#557C64')))
    return bx


# ====================================================================== mid
def cherry_small(seed, h, r):
    """중경용 벚나무."""
    return round_tree(seed, h, r, pal=('pink3', 'pink2', 'pink4'), trunk='wood4')


def mid_scene(period_u):
    """모델 원점 y = 월드 930. 숲 언덕 + 침엽수/둥근 나무/벚나무."""
    rng = np.random.default_rng(91)
    bx = []

    def per(x, terms):
        f = x / period_u * TAU
        return sum(a * np.sin(f * n + p) for (n, a, p) in terms)

    def h_hill(x, zr):
        return (90 + per(x, [(3, 30, 0.3), (7, 18, 1.9), (13, 8, 0.4)])) * (1 - 0.55 * zr)
    cols_hill = ('#7EA86A', '#88B272')
    nz, cz, cxu = 4, 14, 6
    nxc = int(round(period_u / cxu)); cxu = period_u / nxc
    tops = []
    for k in range(nz):
        zr = (k + 0.5) / nz
        z = -150 + (k + 0.5) * cz
        for i in range(nxc):
            x = (i + 0.5) * cxu
            hgt = max(4.0, round(h_hill(x, zr) / 4) * 4)
            bx.append(B(x, hgt / 2, z, cxu + 0.02, hgt, cz + 0.02, cols_hill[k % 2], noise=0.035, bevel=0.6))
            tops.append((x, hgt, z, zr))
    # 숲: 뒤쪽은 침엽수 빽빽, 앞쪽 띄엄띄엄 둥근 나무/벚나무
    for (x, hgt, z, zr) in tops:
        p = 0.55 if zr < 0.5 else 0.2
        if rng.random() > p:
            continue
        kind = rng.random()
        sd = int(rng.integers(1 << 30))
        xx = x + rng.uniform(-cxu / 3, cxu / 3)
        if zr < 0.5 or kind < 0.55:
            th = rng.uniform(46, 86)
            bx += placed(conifer(sd, th, th * 0.28, ('pine2', 'pine1', 'pine3')), xx, hgt - 1, z)
        elif kind < 0.82:
            bx += placed(round_tree(sd, rng.uniform(30, 44), rng.uniform(16, 24)), xx, hgt - 1, z)
        else:
            bx += placed(cherry_small(sd, rng.uniform(30, 42), rng.uniform(18, 26)), xx, hgt - 1, z)
    return bx


# ====================================================================== spec
def bg_cfg(**kw):
    """모델 1단위 = 1.5px: 점유 격자 2단위(3px), AO/그림자 거리 2배."""
    base = dict(ss=3, grid=2.0, ao_radii=(2.4, 5.2, 9.2, 15.0), sh_step=2.6, sh_n=50)
    base.update(kw)
    return Cfg(**base)


def spec(name, L, D):
    if name == 'sky':
        return dict(image=sky_image(16, int(1000 * D)))
    if name == 'clouds':
        period_px, sc, H = 3600, 1.5, int(L['h'] * D)
        cfg = bg_cfg(sh_n=30, haze='#F2DCCB', haze_amt=0.16, bounce=0.9, sky=1.5, rim=0.7, soft=0.18)
        return dict(boxes=clouds_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, float(H)),
                    cfg=cfg, period=period_px, glow=None, tile=300)
    if name == 'far':
        period_px, sc, H = 3600, 1.5, int(L['h'] * D)
        cfg = bg_cfg(haze='#D3D3D2', haze_amt=0.30, haze_add=0.34, haze_z=(-150, -560), bounce=1.0, rim=0.35,
                     sh_n=40)
        return dict(boxes=far_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, (940 - L['y']) * D),
                    cfg=cfg, period=period_px, glow=None, tile=300)
    if name == 'mid':
        period_px, sc, H = 4500, 1.5, int(L['h'] * D)
        cfg = bg_cfg(haze='#D9D7CC', haze_amt=0.22, haze_add=0.06, haze_z=(-100, -160), bounce=1.3, rim=0.55)
        return dict(boxes=mid_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, (930 - L['y']) * D),
                    cfg=cfg, period=period_px, glow=None, tile=300)
    raise KeyError(name)
