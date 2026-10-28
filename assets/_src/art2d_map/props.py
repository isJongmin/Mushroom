"""2D 메이플풍 소품. 모두 Scene 에 그리기 명령을 더한다. 좌표는 레이어 px.

셀 셰이딩 규칙: 빛은 왼쪽 위. 그늘 톤으로 전체를 칠하고(외곽선 포함) → 빛 쪽으로 옮긴 같은 모양을 기본 톤으로
→ 작은 하이라이트(hi). 외곽선은 재질의 line 톤, 기본 굵기 LW(약 2.5px).
"""
import numpy as np
from geom import (circle, ellipse, catmull, rrect, rect, poly, move, scale, rot, blob, scallop, qbez, bez, flipx)
from pal import M, H, mix

LW = 2.5


def _centroid(p):
    return p[:, 0].mean(), p[:, 1].mean()


def toon(s, polys, m, lw=LW, shift=(-0.06, -0.10), shrink=0.94, hi=None, line=True):
    """셀 셰이딩 2단 + 선택적 하이라이트. polys 는 한 물체(합집합 외곽선)."""
    if isinstance(polys, np.ndarray):
        polys = [polys]
    s.shape(polys, m['shade'], m['line'] if line else None, lw)
    s.clip(polys)
    for p in polys:
        cx, cy = _centroid(p)
        w = p[:, 0].max() - p[:, 0].min()
        h = p[:, 1].max() - p[:, 1].min()
        q = scale(p, shrink, shrink, cx, cy)
        s.fill(move(q, shift[0] * w, shift[1] * h), m['base'])
    if hi is not None:
        for p in hi:
            s.fill(p, m['hi'])
    s.unclip()


# ---------------------------------------------------------------------------
# 구름

def cloud(s, cx, cy, w, h, rng, m=None, lw=2.2):
    m = m or M['cloud']
    n = max(3, int(w / (h * 0.55)))
    polys = [ellipse(cx, cy + h * 0.12, w * 0.5, h * 0.32)]
    xs = np.linspace(cx - w * 0.36, cx + w * 0.36, n)
    tops = []
    for i, x in enumerate(xs):
        t = 1 - abs((i / max(1, n - 1)) * 2 - 1)
        r = h * (0.28 + 0.30 * t) * rng.uniform(0.85, 1.15)
        y = cy - h * (0.02 + 0.18 * t) + rng.uniform(-2, 2)
        tops.append((x, y, r))
        polys.append(circle(x, y, r))
    s.shape(polys, m['shade'], m['line'], lw)
    s.clip(polys)
    s.fill(move(ellipse(cx, cy + h * 0.06, w * 0.48, h * 0.26), -w * 0.02, -h * 0.06), m['base'])
    for (x, y, r) in tops:
        s.fill(circle(x - r * 0.10, y - r * 0.14, r * 0.92), m['base'])
    # 아래 그늘 띠
    s.fill(ellipse(cx + w * 0.04, cy + h * 0.40, w * 0.52, h * 0.16), m['shade'])
    s.fill(ellipse(cx + w * 0.08, cy + h * 0.47, w * 0.48, h * 0.10), m['deep'], alpha=0.6)
    s.unclip()


# ---------------------------------------------------------------------------
# 나무

def canopy(s, cx, cy, rx, ry, rng, m, k=9, lw=LW, tufts=True):
    """둥근 덩어리 여러 개로 된 수관. 덩어리마다 셀 셰이딩."""
    cl = []
    for i in range(k):
        a = rng.uniform(0, 2 * np.pi)
        d = np.sqrt(rng.uniform(0.15, 1.0))
        x = cx + np.cos(a) * rx * 0.55 * d
        y = cy + np.sin(a) * ry * 0.50 * d
        r = (rx + ry) * 0.5 * rng.uniform(0.38, 0.52)
        cl.append((x, y, r))
    # 큰 바탕 덩어리
    cl.append((cx, cy + ry * 0.08, (rx + ry) * 0.5 * 0.62))
    cl.sort(key=lambda c: c[1] + c[2] * 0.3, reverse=False)
    polys = [circle(x, y, r) for (x, y, r) in cl]
    s.shape(polys, m['deep'], m['line'], lw)
    s.clip(polys)
    # 아래쪽 어두운 덩어리 → 위쪽 밝은 덩어리 순으로 겹쳐 칠한다
    for (x, y, r) in sorted(cl, key=lambda c: -c[1]):
        s.fill(circle(x + r * 0.05, y + r * 0.04, r * 0.98), m['shade'])
        s.fill(circle(x - r * 0.10, y - r * 0.14, r * 0.86), m['base'])
    for (x, y, r) in cl:
        if y < cy + ry * 0.1:
            s.fill(ellipse(x - r * 0.32, y - r * 0.42, r * 0.36, r * 0.22), m['hi'])
    if tufts:
        # 잎 결(짧은 호) 몇 개
        for (x, y, r) in cl:
            for _ in range(2):
                a = rng.uniform(0.3, 2.6)
                px_, py_ = x + np.cos(a) * r * 0.55, y + np.sin(a) * r * 0.45
                arc = ellipse(px_, py_, r * 0.16, r * 0.10, 8, np.pi * 0.15, np.pi * 0.85)
                s.stroke(arc, m['deep'], lw * 0.7)
    s.unclip()
    return cl


def trunk(s, x, gy, top_y, w, rng, m, lean=0.0, branches=True, lw=LW):
    h = gy - top_y
    pts = [(x - w * 0.9, gy + 2), (x - w * 0.55, gy - h * 0.12), (x - w * 0.42 + lean * 0.5, gy - h * 0.55),
           (x - w * 0.36 + lean, top_y), (x + w * 0.36 + lean, top_y), (x + w * 0.42 + lean * 0.5, gy - h * 0.55),
           (x + w * 0.55, gy - h * 0.12), (x + w * 0.95, gy + 2)]
    p = catmull(pts, False, 8)
    p = np.concatenate([p, [[x, gy + 6]]])
    polys = [p]
    if branches:
        for sgn in (-1, 1):
            by = top_y + h * rng.uniform(0.15, 0.3)
            bx = x + lean * 0.8
            br = poly([(bx, by + w * 0.25), (bx + sgn * w * 1.6, by - h * 0.18), (bx + sgn * w * 1.75, by - h * 0.12),
                       (bx, by + w * 0.65)])
            polys.append(br)
    s.shape(polys, m['shade'], m['line'], lw)
    s.clip(polys)
    s.fill(move(p, -w * 0.28, 0), m['base'])
    # 나무결
    for i in range(3):
        xx = x + (i - 1) * w * 0.35 + lean * 0.6
        ln = catmull([(xx, gy - 4), (xx + rng.uniform(-3, 3), gy - h * 0.45), (xx + lean * 0.4, top_y + 6)], False, 8)
        s.stroke(ln, m['deep'], lw * 0.6, alpha=0.7)
    s.fill(ellipse(x - w * 0.3, gy - h * 0.6, w * 0.14, h * 0.18), m['hi'], alpha=0.8)
    s.unclip()


def tree(s, x, gy, size, rng, kind='leaf', lw=LW, haze=0.0):
    m = H(kind, haze)
    mt = H('trunk', haze)
    th = size * 0.9
    tw = size * 0.13
    trunk(s, x, gy, gy - th, tw, rng, mt, lean=rng.uniform(-6, 6) * size / 100, lw=lw)
    cl = canopy(s, x, gy - th - size * 0.28, size * 0.78, size * 0.62, rng, m, k=10, lw=lw)
    if kind == 'cherry':
        # 꽃잎 점
        for _ in range(int(size * 0.12)):
            a = rng.uniform(0, 2 * np.pi)
            d = rng.uniform(0.2, 1.0)
            px_ = x + np.cos(a) * size * 0.7 * d
            py_ = gy - th - size * 0.28 + np.sin(a) * size * 0.5 * d
            s.fill(circle(px_, py_, rng.uniform(1.6, 2.8)), m['hi'])
    return cl


def pine(s, x, gy, h, rng, m, lw=LW):
    """뾰족 침엽수(원경)."""
    w = h * 0.42
    tiers = 3
    s.shape(rect(x - h * 0.04, gy - h * 0.2, x + h * 0.04, gy + 2), M['trunk']['base'], M['trunk']['line'], lw)
    polys = []
    for i in range(tiers):
        t0 = gy - h * 0.15 - i * h * 0.27
        ww = w * (1 - i * 0.25)
        polys.append(catmull([(x - ww / 2, t0), (x - ww * 0.15, t0 - h * 0.25), (x, t0 - h * 0.42),
                              (x + ww * 0.15, t0 - h * 0.25), (x + ww / 2, t0), (x, t0 + h * 0.05)], True, 6))
    for p in polys:
        toon(s, [p], m, lw, shift=(-0.12, -0.04), shrink=0.88)


def bush(s, x, gy, w, h, rng, m=None, lw=LW, flowers=None):
    m = m or M['leaf']
    k = max(3, int(w / (h * 0.7)))
    cl = []
    for i in range(k):
        t = (i + 0.5) / k
        r = h * (0.42 + 0.22 * np.sin(t * np.pi)) * rng.uniform(0.9, 1.1)
        cl.append((x - w / 2 + t * w, gy - r * 0.85, r))
    polys = [circle(cx, cy, r) for cx, cy, r in cl] + [rrect(x - w / 2, gy - h * 0.45, x + w / 2, gy + 3, h * 0.2)]
    s.shape(polys, m['shade'], m['line'], lw)
    s.clip(polys)
    for (cx, cy, r) in cl:
        s.fill(circle(cx - r * 0.12, cy - r * 0.16, r * 0.84), m['base'])
        s.fill(ellipse(cx - r * 0.35, cy - r * 0.45, r * 0.3, r * 0.18), m['hi'])
    s.fill(rect(x - w, gy - 3, x + w, gy + 4), m['deep'], alpha=0.5)
    s.unclip()
    if flowers:
        for (cx, cy, r) in cl:
            for _ in range(2):
                a = rng.uniform(3.4, 6.0)
                flower(s, cx + np.cos(a) * r * 0.6, cy + np.sin(a) * r * 0.55, rng.uniform(3, 4.2),
                       flowers[rng.integers(len(flowers))], stem=False)


# ---------------------------------------------------------------------------
# 풀, 꽃, 돌

def tuft(s, x, gy, h, rng, m=None, lw=1.8, n=None):
    m = m or M['grass']
    n = n or int(rng.integers(3, 6))
    blades = []
    for i in range(n):
        t = (i - (n - 1) / 2) / max(1, n - 1)
        bh = h * (1 - abs(t) * 0.5) * rng.uniform(0.75, 1.1)
        bx = x + t * h * 0.9
        lean = t * h * 0.7 + rng.uniform(-2, 2)
        bw = h * 0.16
        blades.append(catmull([(bx - bw, gy + 2), (bx - bw * 0.3 + lean * 0.5, gy - bh * 0.55),
                               (bx + lean, gy - bh), (bx + bw * 0.6 + lean * 0.4, gy - bh * 0.5), (bx + bw, gy + 2)], False, 5))
    s.shape(blades, m['base'], m['line'], lw)
    s.clip(blades)
    for b in blades:
        s.fill(move(b, 1.4, 1.5), m['shade'])
    s.unclip()


def flower(s, x, y, r, col, stem=True, lw=1.6, rng=None):
    pm = M[col] if isinstance(col, str) and col in M else col
    if stem:
        s.stroke(qbez((x, y + r * 4.5), (x - r * 0.5, y + r * 2), (x, y)), M['grass']['line'], lw * 1.6)
        s.stroke(qbez((x, y + r * 4.5), (x - r * 0.5, y + r * 2), (x, y)), M['grass']['shade'], lw * 0.7)
    petals = [circle(x + np.cos(a) * r * 0.75, y + np.sin(a) * r * 0.75, r * 0.62, 14)
              for a in np.linspace(0, 2 * np.pi, 5, endpoint=False) - np.pi / 2]
    s.shape(petals, pm['base'], pm['line'], lw)
    s.clip(petals)
    for a in np.linspace(0, 2 * np.pi, 5, endpoint=False) - np.pi / 2:
        s.fill(circle(x + np.cos(a) * r * 0.75 - r * 0.15, y + np.sin(a) * r * 0.75 - r * 0.15, r * 0.42, 12), pm['hi'])
    s.unclip()
    s.shape(circle(x, y, r * 0.38, 12), '#FFD24A', '#A86A1E', lw * 0.7)


def rock(s, x, gy, r, rng, m=None, lw=LW, flat=0.7):
    m = m or M['stone']
    p = blob(x, gy - r * flat * 0.8, r, r * flat, rng, k=7, jit=0.14)
    p = p[p[:, 1] <= gy + 2] if (p[:, 1] > gy + 2).sum() < len(p) - 3 else p
    p = np.concatenate([p, [[x + r, gy + 2], [x - r, gy + 2]]]) if p[:, 1].max() < gy else p
    toon(s, [p], m, lw, shift=(-0.08, -0.12), shrink=0.86,
         hi=[ellipse(x - r * 0.35, gy - r * flat * 1.15, r * 0.3, r * flat * 0.18)])


def pebble_in(s, x, y, r, rng, m=None, lw=2.0):
    m = m or M['stone']
    p = blob(x, y, r, r * 0.72, rng, k=7, jit=0.15)
    toon(s, [p], m, lw, shift=(-0.07, -0.12), shrink=0.84,
         hi=[ellipse(x - r * 0.35, y - r * 0.32, r * 0.28, r * 0.15)])


# ---------------------------------------------------------------------------
# 지면 / 흙

def grass_cap(s, x0, x1, Y, thick, rng, m=None, round_ends=True, lw=LW, drip=8.0):
    """윗면이 정확히 Y 인 잔디 덮개. 아래 가장자리는 둥글게 늘어진 물결."""
    m = m or M['grass']
    b = scallop(x0, x1, Y + thick, drip, 26, rng)
    top = [(x0, Y), (x1, Y)]
    if round_ends:
        e = 4.0
        right = catmull([(x1, Y), (x1 + e * 0.8, Y + 2), (x1 + e, Y + thick * 0.6), (x1 + e * 0.4, Y + thick + drip * 0.8)], False, 6)
        left = catmull([(x0 - e * 0.4, Y + thick + drip * 0.8), (x0 - e, Y + thick * 0.6), (x0 - e * 0.8, Y + 2), (x0, Y)], False, 6)
        p = np.concatenate([poly(top), right[1:], b[::-1][1:-1], left[:-1]])
    else:
        p = np.concatenate([poly(top), b[::-1]])
    s.shape(p, m['shade'], m['line'], lw)
    s.clip(p)
    s.fill(move(p, 0, -5), m['base'])
    s.fill(rect(x0 - 12, Y - 2, x1 + 12, Y + 4.5), m['hi'])
    # 잎결 무늬: 짧은 풀잎 획(아래가 넓고 위가 뾰족)
    n = int((x1 - x0) / 13)
    for i in range(n):
        xx = x0 + (i + rng.uniform(0.1, 0.9)) * (x1 - x0) / max(1, n)
        yy = Y + rng.uniform(9, thick + 2)
        hh = rng.uniform(4, 7)
        lean = rng.uniform(-2, 2)
        s.fill(poly([(xx - 1.8, yy), (xx + lean, yy - hh), (xx + 1.8, yy)]), m['shade'] if rng.random() < 0.6 else m['deep'])
    for i in range(int((x1 - x0) / 40)):
        xx = x0 + rng.uniform(0, 1) * (x1 - x0)
        s.fill(ellipse(xx, Y + 6.5, rng.uniform(5, 10), 1.6, 10), m['hi'])
    s.unclip()
    return p


def grass_top_blades(s, x0, x1, Y, rng, m=None, every=26, hmax=9):
    """윗면 위로 살짝 솟은 풀잎(장식). 서는 선 위는 성기게."""
    m = m or M['grass']
    x = x0 + rng.uniform(4, every)
    while x < x1 - 6:
        tuft(s, x, Y + 2, rng.uniform(hmax * 0.6, hmax), rng, m, lw=1.6, n=int(rng.integers(2, 4)))
        x += every * rng.uniform(0.8, 1.8)


def dirt_body(s, poly_, m, rng, Y0, strata=True, stones=0, lw=LW, stone_m=None):
    s.shape(poly_, m['shade'], m['line'], lw)
    s.clip(poly_)
    w = poly_[:, 0].max() - poly_[:, 0].min()
    h = poly_[:, 1].max() - poly_[:, 1].min()
    s.fill(move(poly_, -w * 0.015 - 4, -h * 0.12), m['base'])
    x0, x1 = poly_[:, 0].min(), poly_[:, 0].max()
    if strata:
        yy = Y0 + 14
        while yy < poly_[:, 1].max():
            ln = catmull([(x0 - 10, yy + rng.uniform(-3, 3)), ((x0 + x1) / 2, yy + rng.uniform(-5, 5)),
                          (x1 + 10, yy + rng.uniform(-3, 3))], False, 20)
            s.stroke(ln, m['deep'], 1.6, alpha=0.55)
            yy += rng.uniform(18, 30)
    sm = stone_m or M['stone']
    for _ in range(stones):
        sx = rng.uniform(x0 + 12, x1 - 12)
        sy = rng.uniform(Y0 + 14, Y0 + h * 0.75)
        pebble_in(s, sx, sy, rng.uniform(5, 10), rng, sm, lw=2.0)
    # 작은 흙 점
    for _ in range(int(w * h / 900)):
        dx, dy = rng.uniform(x0, x1), rng.uniform(Y0 + 8, poly_[:, 1].max())
        s.fill(ellipse(dx, dy, rng.uniform(1.5, 3), rng.uniform(1, 2), 8), m['deep'], alpha=0.6)
    s.unclip()


def vine(s, x, y, length, rng, m=None, lw=1.8):
    m = m or M['leaf']
    pts = [(x, y)]
    for i in range(1, 5):
        pts.append((x + rng.uniform(-5, 5), y + length * i / 4))
    ln = catmull(pts, False, 8)
    s.stroke(ln, m['line'], 4.4)
    s.stroke(ln, m['shade'], 2.0)
    n = int(length / 11)
    for i in range(n):
        t = (i + 0.7) / (n + 0.5)
        idx = int(t * (len(ln) - 1))
        px_, py_ = ln[idx]
        sgn = 1 if i % 2 else -1
        leaf(s, px_, py_, sgn, rng.uniform(4.5, 6.5), m)


def leaf(s, x, y, sgn, r, m, lw=1.5):
    p = catmull([(x, y), (x + sgn * r * 0.8, y - r * 0.55), (x + sgn * r * 1.8, y + r * 0.1), (x + sgn * r * 0.8, y + r * 0.55)], True, 6)
    s.shape(p, m['base'], m['line'], lw)
    s.stroke(poly([(x + sgn * r * 0.2, y), (x + sgn * r * 1.3, y + r * 0.05)]), m['shade'], 1.0)


def rope(s, pts, m=None, w=4.0, twist=True):
    m = m or M['rope']
    ln = np.asarray(pts) if isinstance(pts, np.ndarray) else catmull(pts, False, 10)
    s.stroke(ln, m['line'], w + 2.6)
    s.stroke(ln, m['base'], w)
    if twist:
        # 꼬임 무늬
        d = np.diff(ln, axis=0)
        L = np.concatenate([[0], np.cumsum(np.hypot(d[:, 0], d[:, 1]))])
        step = w * 1.3
        t = step / 2
        while t < L[-1]:
            i = np.searchsorted(L, t)
            i = min(max(i, 1), len(ln) - 1)
            p0, p1 = ln[i - 1], ln[i]
            dv = (p1 - p0) / (np.hypot(*(p1 - p0)) + 1e-9)
            nv = np.array([-dv[1], dv[0]])
            c = p0 + dv * 0.0
            a = c + nv * w * 0.45 - dv * w * 0.3
            b = c - nv * w * 0.45 + dv * w * 0.3
            s.stroke(poly([a, b]), m['shade'], 1.2)
            t += step
    return ln


def rope_coil_hang(s, x, y, length, rng, m=None):
    m = m or M['rope']
    pts = [(x, y), (x + rng.uniform(-3, 3), y + length * 0.5), (x + rng.uniform(-4, 4), y + length)]
    rope(s, pts, m, 3.6)
    # 매듭
    s.shape(ellipse(pts[-1][0], pts[-1][1] + 2, 4.2, 5), m['base'], m['line'], 1.6)


# ---------------------------------------------------------------------------
# 마을 소품

def fence(s, x0, x1, gy, h=34, m=None, lw=2.2, rng=None):
    m = m or M['wood']
    step = 22
    posts = []
    x = x0
    while x <= x1 + 0.1:
        posts.append(x)
        x += step
    rails = [rrect(x0 - 4, gy - h * 0.72, x1 + 4, gy - h * 0.72 + 6, 2), rrect(x0 - 4, gy - h * 0.36, x1 + 4, gy - h * 0.36 + 6, 2)]
    for r_ in rails:
        toon(s, [r_], m, lw, shift=(0, -0.3), shrink=1.0)
    for x in posts:
        p = poly([(x - 5, gy + 2), (x - 5, gy - h + 6), (x, gy - h), (x + 5, gy - h + 6), (x + 5, gy + 2)])
        s.shape(p, m['shade'], m['line'], lw)
        s.clip(p)
        s.fill(rect(x - 6, gy - h - 2, x + 1.5, gy + 3), m['base'])
        s.fill(rect(x - 4, gy - h + 6, x - 2, gy - 4), m['hi'])
        s.unclip()


def lamp(s, x, gy, h=110, lw=LW):
    mm = M['metal']
    s.shape(rrect(x - 4, gy - h, x + 4, gy + 2, 3), mm['base'], mm['line'], lw)
    s.shape(rrect(x - 10, gy - 10, x + 10, gy + 2, 3), mm['shade'], mm['line'], lw)
    # 팔
    s.stroke(qbez((x, gy - h + 10), (x + 6, gy - h - 6), (x + 22, gy - h + 2)), mm['line'], 6)
    s.stroke(qbez((x, gy - h + 10), (x + 6, gy - h - 6), (x + 22, gy - h + 2)), mm['base'], 3)
    # 등
    lx, ly = x + 22, gy - h + 16
    s.fill(circle(lx, ly + 2, 26), '#FFF3B0', alpha=0.25)
    s.fill(circle(lx, ly + 2, 16), '#FFF3B0', alpha=0.35)
    s.shape(poly([(lx - 9, ly - 8), (lx + 9, ly - 8), (lx + 7, ly + 10), (lx - 7, ly + 10)]), M['window']['base'], mm['line'], lw)
    s.fill(poly([(lx - 6, ly - 6), (lx - 1, ly - 6), (lx - 2, ly + 8), (lx - 5, ly + 8)]), M['window']['hi'])
    s.shape(poly([(lx - 12, ly - 8), (lx, ly - 17), (lx + 12, ly - 8)]), mm['base'], mm['line'], lw)
    s.shape(rect(lx - 8, ly + 10, lx + 8, ly + 13), mm['base'], mm['line'], 1.6)


def signpost(s, x, gy, rng, lw=LW):
    m = M['wood']
    s.shape(rrect(x - 5, gy - 70, x + 5, gy + 2, 2), m['shade'], m['line'], lw)
    s.fill(rect(x - 4, gy - 68, x, gy), m['base'])
    b1 = poly([(x - 30, gy - 66), (x + 26, gy - 66), (x + 38, gy - 56), (x + 26, gy - 46), (x - 30, gy - 46)])
    b2 = poly([(x + 30, gy - 40), (x - 26, gy - 40), (x - 38, gy - 30), (x - 26, gy - 20), (x + 30, gy - 20)])
    for b in (b1, b2):
        toon(s, [b], m, lw, shift=(0, -0.25), shrink=1.0)
        cy = b[:, 1].mean()
        s.stroke(poly([(b[:, 0].min() + 10, cy), (b[:, 0].max() - 14, cy)]), m['deep'], 2.0)


def barrel(s, x, gy, r=16, lw=LW):
    m = M['wood']
    h = r * 2.3
    p = catmull([(x - r * 0.85, gy), (x - r, gy - h / 2), (x - r * 0.85, gy - h), (x + r * 0.85, gy - h), (x + r, gy - h / 2), (x + r * 0.85, gy)], True, 6)
    toon(s, [p], m, lw, shift=(-0.12, 0), shrink=0.95)
    s.clip(p)
    for yy in (gy - h * 0.22, gy - h * 0.78):
        s.fill(rect(x - r - 2, yy - 3, x + r + 2, yy + 3), M['metal']['base'])
        s.fill(rect(x - r - 2, yy - 3, x + r + 2, yy - 1.5), M['metal']['hi'])
    s.unclip()
    s.shape(ellipse(x, gy - h, r * 0.8, r * 0.22), m['shade'], m['line'], 1.8)


def crate(s, x, gy, w=30, lw=LW):
    m = M['wood']
    p = rect(x - w / 2, gy - w, x + w / 2, gy + 1)
    toon(s, [p], m, lw, shift=(-0.06, -0.06), shrink=0.98)
    s.stroke(poly([(x - w / 2 + 4, gy - w + 4), (x + w / 2 - 4, gy - 3)]), m['line'], 2.4)
    s.outline(rect(x - w / 2 + 4, gy - w + 4, x + w / 2 - 4, gy - 3), m['deep'], 1.0)


def small_shroom(s, x, gy, r, cap, rng, lw=1.8):
    cm = M[cap]
    st = M['stem']
    sh = r * 1.1
    s.shape(rrect(x - r * 0.36, gy - sh, x + r * 0.36, gy + 1, r * 0.2), st['base'], st['line'], lw)
    s.fill(rect(x + r * 0.08, gy - sh + 2, x + r * 0.3, gy - 1), st['shade'])
    cp = catmull([(x - r, gy - sh + 2), (x - r * 0.8, gy - sh - r * 0.55), (x, gy - sh - r * 0.85),
                  (x + r * 0.8, gy - sh - r * 0.55), (x + r, gy - sh + 2), (x, gy - sh + r * 0.15)], True, 6)
    toon(s, [cp], cm, lw, shift=(-0.07, -0.12), shrink=0.9,
         hi=[ellipse(x - r * 0.4, gy - sh - r * 0.45, r * 0.22, r * 0.14)])
    s.clip(cp)
    for (dx, dy, rr) in ((0.25, -0.45, 0.17), (-0.55, -0.15, 0.13), (0.65, -0.12, 0.11)):
        s.fill(circle(x + dx * r, gy - sh + dy * r, rr * r, 10), '#FFF8EA')
    s.unclip()


def well(s, x, gy, lw=LW):
    st = M['stone']
    w = 70
    body = rrect(x - w / 2, gy - 40, x + w / 2, gy + 2, 6)
    toon(s, [body], st, lw, shift=(-0.04, -0.08), shrink=0.98)
    s.clip(body)
    for row in range(3):
        yy = gy - 40 + row * 14
        off = 0 if row % 2 else 12
        for xx in np.arange(x - w / 2 - 12 + off, x + w / 2, 24):
            s.outline(rrect(xx + 1, yy + 1, xx + 23, yy + 13, 4), st['deep'], 0.9)
    s.unclip()
    s.shape(ellipse(x, gy - 40, w / 2 + 2, 8), st['base'], st['line'], lw)
    s.fill(ellipse(x, gy - 39, w / 2 - 6, 5), M['water']['deep'])
    wd = M['darkwood']
    for sx in (-1, 1):
        s.shape(rect(x + sx * (w / 2 - 6) - 4, gy - 100, x + sx * (w / 2 - 6) + 4, gy - 40), wd['base'], wd['line'], lw)
    roof = poly([(x - w / 2 - 16, gy - 92), (x, gy - 128), (x + w / 2 + 16, gy - 92), (x + w / 2 + 10, gy - 86), (x - w / 2 - 10, gy - 86)])
    toon(s, [roof], M['cap_red'], lw, shift=(-0.04, -0.15), shrink=0.95)
    s.stroke(poly([(x - w / 2 + 2, gy - 72), (x + w / 2 - 2, gy - 72)]), wd['line'], 5)
    s.stroke(poly([(x, gy - 72), (x, gy - 54)]), M['rope']['line'], 2)
    s.shape(rrect(x - 7, gy - 56, x + 7, gy - 44, 2), M['wood']['base'], M['wood']['line'], 1.8)


# ---------------------------------------------------------------------------
# 버섯 집

def mushroom_house(s, x, gy, w, h, cap, rng, lw=LW, haze=0.0, door=True, windows=2, chimney=True, detail=1.0):
    cm = H(cap, haze)
    st = H('stem', haze)
    wd = H('wood', haze)
    win = H('window', haze)
    sw = w * 0.62           # 기둥 폭
    sh = h * 0.52           # 기둥 높이
    capY = gy - sh          # 갓 아래 가장자리
    cw = w
    ch = h * 0.55
    # 기둥
    stem = catmull([(x - sw * 0.52, gy + 2), (x - sw * 0.56, gy - sh * 0.45), (x - sw * 0.44, capY - 6),
                    (x + sw * 0.44, capY - 6), (x + sw * 0.56, gy - sh * 0.45), (x + sw * 0.52, gy + 2)], False, 8)
    stem = np.concatenate([stem, [[x, gy + 4]]])
    toon(s, [stem], st, lw, shift=(-0.16, 0), shrink=0.98,
         hi=[ellipse(x - sw * 0.3, gy - sh * 0.55, sw * 0.06, sh * 0.25)])
    # 기둥 아래 이끼/풀
    if detail > 0:
        s.clip([stem])
        s.fill(np.concatenate([scallop(x - sw, x + sw, gy - 12, 7, 16, rng), [[x + sw, gy + 6], [x - sw, gy + 6]]]),
               M['grass']['base'] if haze == 0 else H('grass', haze)['base'])
        s.unclip()
    # 갓 아래 그늘(기둥 위)과 벽 무늬
    s.clip([stem])
    s.fill(ellipse(x + sw * 0.05, capY + ch * 0.06, sw * 0.75, ch * 0.2), st['shade'])
    s.fill(ellipse(x + sw * 0.08, capY + ch * 0.02, sw * 0.72, ch * 0.12), st['deep'])
    if detail > 0:
        for (bx, by) in ((-0.36, 0.30), (0.34, 0.78), (-0.2, 0.86)):
            bx_, by_ = x + bx * sw, gy - sh + by * sh
            s.outline(rrect(bx_ - 9, by_ - 5, bx_ + 9, by_ + 5, 3), st['deep'], 0.9)
    s.unclip()
    # 창문
    wins = []
    if windows >= 1:
        wins.append((x - sw * 0.27 if door else x, gy - sh * 0.58, sw * 0.12))
    if windows >= 2:
        wins.append((x + sw * 0.30, gy - sh * 0.74, sw * 0.09))
    for (wx, wy, wr) in wins:
        s.fill(circle(wx, wy, wr * 2.0), win['hi'], alpha=0.18)
        s.shape(circle(wx, wy, wr + 4), wd['base'], wd['line'], lw)
        s.shape(circle(wx, wy, wr), win['base'], wd['line'], 1.6)
        s.clip(circle(wx, wy, wr))
        s.fill(circle(wx + wr * 0.35, wy + wr * 0.35, wr), win['shade'])
        s.fill(circle(wx - wr * 0.25, wy - wr * 0.25, wr * 0.55), win['hi'])
        s.unclip()
        s.stroke(poly([(wx - wr, wy), (wx + wr, wy)]), wd['line'], 2.4)
        s.stroke(poly([(wx, wy - wr), (wx, wy + wr)]), wd['line'], 2.4)
        if detail > 0:
            # 꽃 상자
            bx0, bx1 = wx - wr - 6, wx + wr + 6
            by = wy + wr + 6
            for fx in np.linspace(bx0 + 5, bx1 - 5, 4):
                flower(s, fx, by - 5, 3.4, ['cap_pink', 'cap_red', 'cap_yellow', 'cap_purple'][int(rng.integers(4))], stem=False, lw=1.2)
            s.shape(rrect(bx0, by - 2, bx1, by + 8, 2), wd['base'], wd['line'], 1.8)
            s.fill(rect(bx0 + 1, by - 1, bx1 - 1, by + 2), wd['hi'])
    # 문
    if door:
        dw, dh = sw * 0.34, sh * 0.62
        dx = x + sw * (0.06 if windows >= 2 else 0.12)
        fr = np.concatenate([ellipse(dx, gy - dh + dw * 0.5 + 4, dw * 0.5 + 5, dw * 0.5 + 5, 24, np.pi, 2 * np.pi), [[dx + dw / 2 + 5, gy + 1], [dx - dw / 2 - 5, gy + 1]]])
        s.shape(fr, H('stone', haze)['base'], H('stone', haze)['line'], lw)
        dp = np.concatenate([ellipse(dx, gy - dh + dw * 0.5 + 4, dw * 0.5, dw * 0.5, 24, np.pi, 2 * np.pi), [[dx + dw / 2, gy + 1], [dx - dw / 2, gy + 1]]])
        toon(s, [dp], wd, 1.8, shift=(-0.14, 0), shrink=1.0)
        s.clip(dp)
        for k_ in (-1, 0, 1):
            s.stroke(poly([(dx + k_ * dw * 0.3, gy - dh), (dx + k_ * dw * 0.3, gy)]), wd['deep'], 1.6)
        s.unclip()
        s.shape(circle(dx + dw * 0.28, gy - dh * 0.42, 3.2, 10), H('cap_yellow', haze)['base'], H('cap_yellow', haze)['line'], 1.2)
        # 계단 돌
        s.shape(rrect(dx - dw / 2 - 10, gy - 5, dx + dw / 2 + 10, gy + 3, 3), H('stone', haze)['base'], H('stone', haze)['line'], 1.8)
    # 굴뚝 (갓 뒤)
    capP = catmull([(x - cw * 0.5, capY + 2), (x - cw * 0.47, capY - ch * 0.38), (x - cw * 0.3, capY - ch * 0.82),
                    (x, capY - ch), (x + cw * 0.3, capY - ch * 0.82), (x + cw * 0.47, capY - ch * 0.38),
                    (x + cw * 0.5, capY + 2), (x + cw * 0.3, capY + ch * 0.13), (x, capY + ch * 0.16), (x - cw * 0.3, capY + ch * 0.13)], True, 10)
    if chimney:
        cx_ = x + cw * 0.22
        cy0 = capY - ch * 0.78
        chp = rrect(cx_ - 9, cy0 - ch * 0.38, cx_ + 9, cy0 + 10, 2)
        toon(s, [chp], H('stone', haze), lw, shift=(-0.2, 0), shrink=1.0)
        s.shape(rrect(cx_ - 12, cy0 - ch * 0.38 - 6, cx_ + 12, cy0 - ch * 0.38 + 2, 2), H('stone', haze)['shade'], H('stone', haze)['line'], 1.8)
        for i in range(3):
            r_ = 6 + i * 3
            s.shape(circle(cx_ + 6 + i * 10, cy0 - ch * 0.38 - 14 - i * 14, r_), '#FFFFFF', '#C9DCF3', 1.5, alpha=0.85 - i * 0.2)
    # 갓
    s.shape(capP, cm['shade'], cm['line'], lw)
    s.clip(capP)
    s.fill(move(scale(capP, 0.96, 0.92, x, capY), -cw * 0.04, -ch * 0.12), cm['base'])
    # 아래 가장자리 어두운 띠
    s.fill(ellipse(x, capY + ch * 0.17, cw * 0.55, ch * 0.13), cm['deep'])
    # 하이라이트
    s.fill(ellipse(x - cw * 0.22, capY - ch * 0.7, cw * 0.14, ch * 0.08), cm['hi'])
    s.fill(ellipse(x - cw * 0.36, capY - ch * 0.48, cw * 0.05, ch * 0.08), cm['hi'])
    # 점무늬
    spots = [(-0.05, -0.62, 0.11), (0.28, -0.42, 0.085), (-0.33, -0.25, 0.075), (0.12, -0.18, 0.06), (-0.17, -0.86, 0.05), (0.40, -0.08, 0.05)]
    for (dx_, dy_, rr) in spots:
        sx, sy = x + dx_ * cw, capY + dy_ * ch
        sp = ellipse(sx, sy, rr * cw, rr * cw * 0.72)
        s.fill(sp, mix(st['base'], cm['line'], 0.45))
        s.fill(move(sp, -1.2, -1.6), st['base'])
        s.fill(ellipse(sx + rr * cw * 0.25, sy + rr * cw * 0.3, rr * cw * 0.6, rr * cw * 0.25), st['shade'])
    s.unclip()
    return capY - ch
