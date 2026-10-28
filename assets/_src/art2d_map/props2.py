"""v2 감성 일러스트 소품. 얇은 색조 외곽선(LW 1.5), 셀 셰이딩 + 붓 터치(작은 점, 결)로 질감.
빛은 왼쪽 위. 좌표는 레이어 px.
"""
import numpy as np
from geom import circle, ellipse, catmull, rrect, rect, poly, move, scale, blob, qbez, bez
from pal2 import M, tone
from vec import mix

LW = 1.5


def toon(s, polys, m, lw=LW, shift=(-0.06, -0.10), shrink=0.94, hi=None, line=True):
    if isinstance(polys, np.ndarray):
        polys = [polys]
    s.shape(polys, m['shade'], m['line'] if line else None, lw)
    s.clip(polys)
    for p in polys:
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        w = p[:, 0].max() - p[:, 0].min()
        h = p[:, 1].max() - p[:, 1].min()
        s.fill(move(scale(p, shrink, shrink, cx, cy), shift[0] * w, shift[1] * h), m['base'])
    for p in hi or []:
        s.fill(p, m['hi'])
    s.unclip()


def dabs(s, x0, y0, x1, y1, n, rng, cols, rmin=1.5, rmax=3.5, alpha=1.0):
    """붓 터치 점(잎, 이끼, 흙 질감)."""
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(rmin, rmax)
        s.fill(ellipse(x, y, r, r * rng.uniform(0.55, 0.85), 8), cols[int(rng.integers(len(cols)))], alpha=alpha)


def rough_line(x0, x1, y, rng, amp=1.5, step=5.0):
    xs = np.arange(x0, x1 + step, step)
    xs[-1] = x1
    ys = y + rng.uniform(-amp, amp, len(xs))
    return np.stack([xs, ys], -1)


# ---------------------------------------------------------------------------
# 하늘

def sun_glow(s, x, y, r, col='#FFF1DC', strength=0.5, n=26):
    for i in range(n):
        t = (i + 1) / n
        s.fill(circle(x, y, r * (1 - t * 0.92), 96), col, alpha=strength / n * 1.6)


def soft_cloud(s, cx, cy, w, h, rng, pal=None, far=0.0):
    """볼륨 적운: 작은 뭉게 여러 겹의 윗선, 납작한 그늘진 바닥. 외곽선 없음, 반투명 테."""
    pal = pal or dict(shadow='#C9C0CA', mid='#ECE2DD', light='#FFF8EE', warm='#F7E2CF')
    if far > 0:
        pal = {k: mix(v, '#C9D2DA', far) for k, v in pal.items()}
    base_y = cy + h * 0.3
    puffs = []
    # 몸통 덩어리 2~3개
    for k in range(int(rng.integers(2, 4))):
        bx = cx + rng.uniform(-w * 0.2, w * 0.2)
        br = h * rng.uniform(0.38, 0.5)
        puffs.append((bx, base_y - br * 0.7, br * rng.uniform(1.2, 1.6), br))
    # 윗선 작은 뭉게
    n = max(6, int(w / (h * 0.22)))
    for i in range(n):
        t = i / (n - 1)
        bell = np.sin(t * np.pi) ** 0.8
        r = h * (0.12 + 0.2 * bell) * rng.uniform(0.8, 1.2)
        x = cx - w * 0.46 + t * w * 0.92
        y = base_y - r * 0.6 - bell * h * 0.55 + rng.uniform(-4, 4)
        puffs.append((x, y, r, r))
    for _ in range(int(n * 0.5)):
        x, y, r, _r = puffs[int(rng.integers(len(puffs)))]
        puffs.append((x + rng.uniform(-r, r), y - r * rng.uniform(0.2, 0.5), r * 0.55, r * 0.55))
    polys = [ellipse(x, y, rx, ry) for (x, y, rx, ry) in puffs]
    s.clip(rect(cx - w, cy - h * 3, cx + w, base_y))
    s.fill([scale(p, 1.03, 1.05, p[:, 0].mean(), p[:, 1].mean()) for p in polys], pal['mid'], alpha=0.3)
    s.fill(polys, pal['shadow'])
    s.clip(polys)
    for (x, y, rx, ry) in sorted(puffs, key=lambda q: -q[1]):
        s.fill(ellipse(x - rx * 0.12, y - ry * 0.22, rx * 0.86, ry * 0.8), pal['mid'], alpha=0.92)
    for (x, y, rx, ry) in puffs:
        if y < base_y - h * 0.25:
            s.fill(ellipse(x - rx * 0.28, y - ry * 0.38, rx * 0.55, ry * 0.42), pal['light'], alpha=0.85)
    # 햇빛 받은 왼쪽 위 따뜻한 테
    s.fill(rect(cx - w, base_y - h * 0.22, cx + w, base_y + 2), pal['shadow'], agrad=[(base_y - h * 0.22, 0.0), (base_y, 0.8)])
    s.unclip()
    s.unclip()


# ---------------------------------------------------------------------------
# 식물

def leafy_canopy(s, cx, cy, rx, ry, rng, m, k=14, lw=LW, texture=1.0):
    """여러 잎 덩어리로 된 수관. 덩어리마다 울퉁불퉁한 외곽, 셀 셰이딩, 잎 터치."""
    cl = []
    for i in range(k):
        a = rng.uniform(0, 2 * np.pi)
        d = np.sqrt(rng.uniform(0.1, 1.0))
        cl.append((cx + np.cos(a) * rx * 0.6 * d, cy + np.sin(a) * ry * 0.55 * d, (rx + ry) * 0.5 * rng.uniform(0.32, 0.46)))
    cl.append((cx, cy + ry * 0.1, (rx + ry) * 0.5 * 0.6))
    polys = [blob(x, y, r, r * 0.88, rng, k=9, jit=0.1) for (x, y, r) in cl]
    s.shape(polys, m['deep'], m['line'], lw)
    s.clip(polys)
    order = sorted(range(len(cl)), key=lambda i: -cl[i][1])
    for i in order:
        x, y, r = cl[i]
        p = polys[i]
        s.fill(move(p, r * 0.04, r * 0.05), m['shade'])
        s.fill(move(scale(p, 0.84, 0.82, x, y), -r * 0.1, -r * 0.14), m['base'])
    if texture > 0:
        for (x, y, r) in cl:
            # 위쪽에 빛 받은 잎 터치
            for _ in range(int(5 * texture)):
                a = rng.uniform(-2.6, -0.5)
                d = rng.uniform(0.3, 0.75)
                lx, ly = x + np.cos(a) * r * d, y + np.sin(a) * r * d
                s.fill(ellipse(lx, ly, r * rng.uniform(0.06, 0.1), r * rng.uniform(0.035, 0.06), 8), m['hi'], alpha=0.75)
            # 아래쪽 어두운 잎 터치
            for _ in range(int(3 * texture)):
                a = rng.uniform(0.4, 2.7)
                d = rng.uniform(0.4, 0.9)
                lx, ly = x + np.cos(a) * r * d, y + np.sin(a) * r * d
                s.fill(ellipse(lx, ly, r * rng.uniform(0.06, 0.1), r * rng.uniform(0.035, 0.06), 8), m['deep'], alpha=0.5)
    s.unclip()
    return cl


def trunk(s, x, gy, top_y, w, rng, m, lean=0.0, lw=LW, branches=2):
    h = gy - top_y
    pts = [(x - w * 0.95, gy + 2), (x - w * 0.55, gy - h * 0.1), (x - w * 0.42 + lean * 0.5, gy - h * 0.55),
           (x - w * 0.32 + lean, top_y), (x + w * 0.32 + lean, top_y), (x + w * 0.42 + lean * 0.5, gy - h * 0.55),
           (x + w * 0.55, gy - h * 0.1), (x + w * 1.0, gy + 2)]
    p = np.concatenate([catmull(pts, False, 8), [[x, gy + 6]]])
    polys = [p]
    for i in range(branches):
        sgn = -1 if i % 2 == 0 else 1
        by = top_y + h * rng.uniform(0.05, 0.3)
        bx = x + lean * 0.8
        polys.append(catmull([(bx, by + w * 0.5), (bx + sgn * w * 0.9, by - h * 0.06), (bx + sgn * w * 1.9, by - h * 0.2),
                              (bx + sgn * w * 1.75, by - h * 0.22), (bx + sgn * w * 0.6, by - h * 0.02), (bx, by + w * 0.1)], True, 5))
    s.shape(polys, m['shade'], m['line'], lw)
    s.clip(polys)
    s.fill(move(p, -w * 0.3, 0), m['base'])
    for i in range(4):
        xx = x + (i - 1.5) * w * 0.3 + lean * 0.5
        ln = catmull([(xx, gy - 2), (xx + rng.uniform(-3, 3), gy - h * 0.5), (xx + lean * 0.5, top_y + 4)], False, 8)
        s.stroke(ln, m['deep'], 1.0, alpha=0.6)
    s.fill(ellipse(x - w * 0.32, gy - h * 0.55, w * 0.1, h * 0.22), m['hi'], alpha=0.7)
    # 이끼
    s.fill(np.concatenate([rough_line(x - w * 1.1, x + w * 0.2, gy - h * 0.08, rng, 4), [[x + w * 0.2, gy + 4], [x - w * 1.1, gy + 4]]]),
           M['moss']['shade'], alpha=0.8)
    s.unclip()


def tree(s, x, gy, size, rng, kind='leaf', lw=LW, haze=0.0):
    m = tone(kind, haze)
    mt = tone('trunk', haze)
    th = size * 0.85
    trunk(s, x, gy, gy - th, size * 0.11, rng, mt, lean=rng.uniform(-6, 6) * size / 100, lw=lw)
    leafy_canopy(s, x, gy - th - size * 0.25, size * 0.8, size * 0.6, rng, m, k=12, lw=lw)


def conifer(s, x, gy, h, rng, m, lw=LW):
    w = h * 0.38
    s.shape(rect(x - h * 0.03, gy - h * 0.2, x + h * 0.03, gy + 2), M['trunk']['base'], M['trunk']['line'], lw)
    tiers = 4
    for i in range(tiers):
        t0 = gy - h * 0.12 - i * h * 0.2
        ww = w * (1 - i * 0.2)
        p = catmull([(x - ww / 2, t0), (x - ww * 0.2, t0 - h * 0.22), (x, t0 - h * 0.34), (x + ww * 0.2, t0 - h * 0.22),
                     (x + ww / 2, t0), (x + ww * 0.15, t0 + h * 0.03), (x - ww * 0.2, t0 + h * 0.02)], True, 6)
        toon(s, [p], m, lw, shift=(-0.14, -0.04), shrink=0.86)


def bush(s, x, gy, w, h, rng, m=None, lw=LW, flowers=None):
    m = m or M['leaf']
    k = max(3, int(w / (h * 0.65)))
    cl = []
    for i in range(k):
        t = (i + 0.5) / k
        r = h * (0.4 + 0.24 * np.sin(t * np.pi)) * rng.uniform(0.9, 1.1)
        cl.append((x - w / 2 + t * w, gy - r * 0.8, r))
    polys = [blob(cx, cy, r, r * 0.9, rng, k=8, jit=0.1) for cx, cy, r in cl] + [rrect(x - w / 2, gy - h * 0.4, x + w / 2, gy + 3, h * 0.2)]
    s.shape(polys, m['shade'], m['line'], lw)
    s.clip(polys)
    for (cx, cy, r) in cl:
        s.fill(ellipse(cx - r * 0.12, cy - r * 0.16, r * 0.82, r * 0.74), m['base'])
    dabs(s, x - w / 2, gy - h * 1.2, x + w / 2, gy - h * 0.4, int(w / 6), rng, [m['hi']], 1.5, 3.2)
    dabs(s, x - w / 2, gy - h * 0.5, x + w / 2, gy, int(w / 8), rng, [m['deep']], 1.5, 3.0)
    s.unclip()
    if flowers:
        for (cx, cy, r) in cl:
            for _ in range(2):
                a = rng.uniform(3.4, 6.0)
                daisy(s, cx + np.cos(a) * r * 0.6, cy + np.sin(a) * r * 0.5, rng.uniform(2.6, 3.4), flowers[int(rng.integers(len(flowers)))])


def blade_row(s, x0, x1, Y, rng, m=None, hmin=4, hmax=10, density=0.45):
    """잔디 끝선: 위로 솟은 가는 풀잎 줄(윗면 Y 에서 시작)."""
    m = m or M['grass']
    x = x0
    polys = {k: [] for k in ('shade', 'base', 'hi')}
    while x < x1:
        h = rng.uniform(hmin, hmax)
        w = rng.uniform(1.6, 2.6)
        lean = rng.uniform(-2.5, 2.5)
        k = ('shade', 'base', 'hi')[int(rng.choice(3, p=[0.35, 0.45, 0.2]))]
        polys[k].append(poly([(x - w, Y + 2), (x + lean, Y - h), (x + w, Y + 2)]))
        x += rng.uniform(1.5, 4.5) / density
    for k in ('shade', 'base', 'hi'):
        if polys[k]:
            s.fill(polys[k], m[k])


def tuft(s, x, gy, h, rng, m=None, lw=1.2, n=None):
    m = m or M['grass']
    n = n or int(rng.integers(4, 8))
    blades = []
    for i in range(n):
        t = (i - (n - 1) / 2) / max(1, n - 1)
        bh = h * (1 - abs(t) * 0.45) * rng.uniform(0.75, 1.1)
        bx = x + t * h * 0.7
        lean = t * h * 0.9 + rng.uniform(-2, 2)
        bw = h * 0.09
        blades.append(catmull([(bx - bw, gy + 2), (bx + lean * 0.45, gy - bh * 0.6), (bx + lean, gy - bh), (bx + bw, gy + 2)], False, 5))
    s.shape(blades, m['base'], m['line'], lw)
    s.clip(blades)
    for b in blades:
        s.fill(move(b, 1.0, 1.2), m['shade'])
    s.unclip()


def daisy(s, x, y, r, col='cream', stem=False):
    pm = M[col]
    if stem:
        s.stroke(qbez((x, y + r * 4), (x - r * 0.6, y + r * 2), (x, y)), M['grass']['shade'], 1.3)
    petals = [ellipse(x + np.cos(a) * r * 0.7, y + np.sin(a) * r * 0.7, r * 0.55, r * 0.4, 10) for a in np.linspace(0, 2 * np.pi, 6, endpoint=False)]
    s.shape(petals, pm['base'], pm['line'], 0.9)
    s.fill(circle(x - r * 0.15, y - r * 0.2, r * 0.5, 10), pm['hi'], alpha=0.7)
    s.fill(circle(x, y, r * 0.32, 10), M['terracotta']['base'] if col == 'cream' else M['cream']['base'])


def fern(s, x, gy, size, rng, m=None, flip=1):
    m = m or M['leaf2']
    for i in range(5):
        ang = np.radians(-160 + i * 30 + rng.uniform(-8, 8))
        L = size * rng.uniform(0.7, 1.0) * (1 - abs(i - 2) * 0.12)
        ex, ey = x + np.cos(ang) * L, gy + np.sin(ang) * L * 0.9
        cx_, cy_ = x + np.cos(ang) * L * 0.5, gy + np.sin(ang) * L * 0.9 - L * 0.25
        rib = qbez((x, gy), (cx_, cy_), (ex, ey), 12)
        s.stroke(rib, m['line'], 2.4)
        for j in range(2, 11):
            px_, py_ = rib[j]
            d = rib[j] - rib[j - 1]
            nrm = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9)
            ll = size * 0.12 * (1 - j / 12)
            for sgn in (-1, 1):
                q = poly([(px_, py_), (px_ + nrm[0] * ll * sgn + d[0] * 0.6, py_ + nrm[1] * ll * sgn + d[1] * 0.6), (px_ + d[0], py_ + d[1])])
                s.fill(q, m['base'] if sgn > 0 else m['shade'])
        s.stroke(rib, m['shade'], 1.0)


def mossy_rock(s, x, gy, r, rng, lw=LW):
    st = M['stone']
    p = blob(x, gy - r * 0.55, r, r * 0.65, rng, k=8, jit=0.12)
    p[:, 1] = np.minimum(p[:, 1], gy + 2)
    toon(s, [p], st, lw, shift=(-0.08, -0.12), shrink=0.86, hi=[ellipse(x - r * 0.35, gy - r * 0.95, r * 0.25, r * 0.1)])
    s.clip([p])
    moss = np.concatenate([rough_line(x - r * 1.1, x + r * 0.5, gy - r * 1.05, rng, 2), np.stack([np.linspace(x + r * 0.5, x - r * 1.1, 8), gy - r * 0.75 + rng.uniform(-4, 6, 8)], -1)])
    s.fill(moss, M['moss']['base'])
    dabs(s, x - r, gy - r * 1.2, x + r * 0.4, gy - r * 0.8, int(r / 2), rng, [M['moss']['hi'], M['moss']['shade']], 1, 2.2)
    s.unclip()


def small_shroom(s, x, gy, r, rng, cap='terracotta', lw=1.2):
    cm = M[cap]
    st = M['cream']
    sh = r * 1.2
    s.shape(rrect(x - r * 0.3, gy - sh, x + r * 0.3, gy + 1, r * 0.15), st['base'], st['line'], lw)
    cp = catmull([(x - r, gy - sh + 2), (x - r * 0.75, gy - sh - r * 0.5), (x, gy - sh - r * 0.7),
                  (x + r * 0.75, gy - sh - r * 0.5), (x + r, gy - sh + 2), (x, gy - sh + r * 0.12)], True, 6)
    toon(s, [cp], cm, lw, shift=(-0.07, -0.12), shrink=0.88, hi=[ellipse(x - r * 0.4, gy - sh - r * 0.38, r * 0.2, r * 0.1)])


def vine(s, x, y, length, rng, m=None):
    m = m or M['leaf2']
    pts = [(x, y)] + [(x + rng.uniform(-4, 4), y + length * i / 4) for i in range(1, 5)]
    ln = catmull(pts, False, 8)
    s.stroke(ln, m['shade'], 1.6)
    n = int(length / 8)
    for i in range(n):
        idx = int((i + 0.6) / (n + 0.4) * (len(ln) - 1))
        px_, py_ = ln[idx]
        sgn = 1 if i % 2 else -1
        r = rng.uniform(2.6, 4.2)
        p = catmull([(px_, py_), (px_ + sgn * r, py_ - r * 0.4), (px_ + sgn * r * 1.8, py_ + r * 0.3), (px_ + sgn * r * 0.7, py_ + r * 0.6)], True, 5)
        s.fill(p, m['base'] if rng.random() < 0.6 else m['hi'])


def hanging_moss(s, x0, x1, y, rng, m=None, maxlen=22):
    m = m or M['moss']
    x = x0
    while x < x1:
        L = rng.uniform(5, maxlen)
        w = rng.uniform(4, 9)
        p = catmull([(x - w / 2, y - 2), (x - w * 0.3, y + L * 0.6), (x + rng.uniform(-2, 2), y + L), (x + w * 0.3, y + L * 0.5), (x + w / 2, y - 2)], False, 5)
        s.fill(p, m['shade'] if rng.random() < 0.5 else m['base'])
        x += rng.uniform(5, 12)


def rope(s, pts, m=None, w=3.0):
    m = m or M['wood']
    ln = np.asarray(pts) if isinstance(pts, np.ndarray) else catmull(pts, False, 10)
    s.stroke(ln, m['line'], w + 1.8)
    s.stroke(ln, m['hi'], w)
    return ln


# ---------------------------------------------------------------------------
# 마을 소품

def string_lights(s, x0, y0, x1, y1, sag, rng, n=None):
    xs = np.linspace(0, 1, 40)
    ln = np.stack([x0 + (x1 - x0) * xs, y0 + (y1 - y0) * xs + sag * 4 * xs * (1 - xs)], -1)
    s.stroke(ln, '#4A4440', 1.2)
    n = n or max(4, int(abs(x1 - x0) / 22))
    for i in range(1, n):
        t = i / n
        bx, by = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t) + 4
        s.fill(circle(bx, by, 7, 24), '#FFE9C4', alpha=0.22)
        s.shape(ellipse(bx, by, 2.4, 3.0, 12), '#FFF2D6', '#9C7A52', 0.8)


def lamp(s, x, gy, h=118):
    mm = M['metal']
    s.shape(rrect(x - 3, gy - h, x + 3, gy + 2, 2), mm['base'], mm['line'], LW)
    s.shape(rrect(x - 8, gy - 12, x + 8, gy + 2, 3), mm['shade'], mm['line'], LW)
    ly = gy - h - 12
    s.fill(circle(x, ly, 34, 48), '#FFE9C4', alpha=0.16)
    s.fill(circle(x, ly, 18, 32), '#FFE9C4', alpha=0.28)
    s.shape(poly([(x - 8, ly - 10), (x + 8, ly - 10), (x + 6, ly + 10), (x - 6, ly + 10)]), M['glow']['base'], mm['line'], LW)
    s.fill(poly([(x - 5, ly - 8), (x - 1, ly - 8), (x - 1.5, ly + 8), (x - 4, ly + 8)]), M['glow']['hi'])
    s.shape(poly([(x - 12, ly - 10), (x, ly - 19), (x + 12, ly - 10)]), mm['base'], mm['line'], LW)
    s.shape(rect(x - 7, ly + 10, x + 7, ly + 13), mm['base'], mm['line'], 1.0)
    return (x, ly - 19)


def bench(s, x, gy, w=64):
    wd = M['wood']
    mm = M['metal']
    for lx in (x - w * 0.38, x + w * 0.38):
        s.stroke(poly([(lx, gy + 1), (lx, gy - 30)]), mm['line'], 3.2)
    for i, yy in enumerate((gy - 34, gy - 26)):
        toon(s, [rrect(x - w / 2, yy - 3 - i * 4, x + w / 2, yy + 2 - i * 4, 1.5)], wd, 1.2, shift=(0, -0.3), shrink=1.0)
    toon(s, [rrect(x - w / 2 - 2, gy - 18, x + w / 2 + 2, gy - 13, 1.5)], wd, 1.2, shift=(0, -0.3), shrink=1.0)


def pot(s, x, gy, r, rng, plant='leaf'):
    tc = M['terracotta']
    p = poly([(x - r, gy - r * 1.4), (x + r, gy - r * 1.4), (x + r * 0.75, gy + 1), (x - r * 0.75, gy + 1)])
    leafy = M[plant]
    # 식물
    if rng.random() < 0.5:
        cl = [(x + rng.uniform(-r * 0.6, r * 0.6), gy - r * rng.uniform(2.0, 2.8), r * rng.uniform(0.6, 0.9)) for _ in range(4)]
        polys = [blob(a, b, c, c * 0.9, rng, 7, 0.12) for a, b, c in cl]
        toon(s, polys, leafy, 1.1, shift=(-0.1, -0.15), shrink=0.8)
        dabs(s, x - r, gy - r * 3.4, x + r, gy - r * 2, 5, rng, [leafy['hi']], 1, 2)
    else:
        for i in range(6):
            ang = np.radians(-150 + i * 24)
            L = r * rng.uniform(1.8, 2.6)
            tip = (x + np.cos(ang) * L, gy - r * 1.3 + np.sin(ang) * L)
            lf = catmull([(x - 1.5, gy - r * 1.3), ((x + tip[0]) / 2 - 3, (gy - r * 1.3 + tip[1]) / 2), tip, ((x + tip[0]) / 2 + 3, (gy - r * 1.3 + tip[1]) / 2 + 2), (x + 1.5, gy - r * 1.3)], False, 4)
            s.shape(lf, leafy['base'] if i % 2 else leafy['shade'], leafy['line'], 0.9)
    toon(s, [p], tc, 1.2, shift=(-0.12, 0), shrink=0.95)
    s.shape(rrect(x - r * 1.1, gy - r * 1.55, x + r * 1.1, gy - r * 1.25, 1), tc['base'], tc['line'], 1.2)


def awning(s, x0, x1, y, depth, cols, scallop_n=None):
    """줄무늬 차양 (위 y, 아래로 depth). cols = (a, b) 재질 이름."""
    w = x1 - x0
    n = scallop_n or max(4, int(w / 16))
    top = poly([(x0 + 4, y), (x1 - 4, y), (x1 + 6, y + depth), (x0 - 6, y + depth)])
    sx = np.linspace(x0 - 6, x1 + 6, n + 1)
    bottom = []
    for a, b in zip(sx[:-1], sx[1:]):
        t = np.linspace(0, 1, 6)
        bottom.append(np.stack([a + (b - a) * t, y + depth + 6 * np.sin(t * np.pi)], -1))
    bottom = np.concatenate(bottom)
    shape = np.concatenate([[[x0 + 4, y], [x1 - 4, y]], bottom[::-1]])
    ma, mb = M[cols[0]], M[cols[1]]
    s.shape(shape, ma['base'], ma['line'], LW)
    s.clip(shape)
    for i, (a, b) in enumerate(zip(sx[:-1], sx[1:])):
        if i % 2:
            ta = x0 + 4 + (a - (x0 - 6)) / (w + 12) * (w - 8)
            tb = x0 + 4 + (b - (x0 - 6)) / (w + 12) * (w - 8)
            s.fill(poly([(ta, y - 2), (tb, y - 2), (b, y + depth + 8), (a, y + depth + 8)]), mb['base'])
    s.fill(rect(x0 - 10, y + depth - 2, x1 + 10, y + depth + 10), '#000000', alpha=0.07)
    s.fill(rect(x0 - 10, y - 2, x1 + 10, y + 3), '#FFFFFF', alpha=0.25)
    s.unclip()


def window(s, x, y, w, h, frame='darkwood', arch=False, box=True, rng=None, lit=True):
    fr = M[frame]
    g = M['glow'] if lit else M['glass']
    outer = rrect(x - w / 2 - 4, y - 4, x + w / 2 + 4, y + h + 4, 3)
    if arch:
        outer = np.concatenate([ellipse(x, y + w / 2, w / 2 + 4, w / 2 + 4, 24, np.pi, 2 * np.pi), [[x + w / 2 + 4, y + h + 4], [x - w / 2 - 4, y + h + 4]]])
    s.shape(outer, fr['base'], fr['line'], LW)
    inner = rrect(x - w / 2, y, x + w / 2, y + h, 2)
    if arch:
        inner = np.concatenate([ellipse(x, y + w / 2, w / 2, w / 2, 24, np.pi, 2 * np.pi), [[x + w / 2, y + h], [x - w / 2, y + h]]])
    s.fill(inner, g['base'])
    s.clip(inner)
    s.fill(poly([(x - w, y + h), (x + w, y - h * 0.2), (x + w, y + h)]), g['shade'])
    s.fill(poly([(x - w / 2, y + h * 0.15), (x - w * 0.1, y - 2), (x + w * 0.05, y - 2), (x - w / 2, y + h * 0.5)]), g['hi'], alpha=0.8)
    s.unclip()
    s.stroke(poly([(x, y), (x, y + h)]), fr['line'], 2.2)
    s.stroke(poly([(x - w / 2, y + h * 0.5), (x + w / 2, y + h * 0.5)]), fr['line'], 2.2)
    if box and rng is not None:
        bx0, bx1, by = x - w / 2 - 6, x + w / 2 + 6, y + h + 4
        for fx in np.linspace(bx0 + 5, bx1 - 5, 5):
            if rng.random() < 0.6:
                blob_ = blob(fx, by - 4, 5, 4, rng, 6, 0.15)
                s.shape(blob_, M['leaf']['base'], M['leaf']['line'], 0.9)
            else:
                daisy(s, fx, by - 5, 2.6, ['cream', 'rose', 'dustyblue'][int(rng.integers(3))])
        toon(s, [rrect(bx0, by, bx1, by + 9, 2)], M['terracotta'], 1.2, shift=(0, -0.3), shrink=1.0)


def door(s, x, gy, w, h, m='darkwood', glass=True):
    dm = M[m]
    fr = np.concatenate([ellipse(x, gy - h + w / 2, w / 2 + 5, w / 2 + 5, 24, np.pi, 2 * np.pi), [[x + w / 2 + 5, gy + 1], [x - w / 2 - 5, gy + 1]]])
    s.shape(fr, M['warmgray']['base'], M['warmgray']['line'], LW)
    dp = np.concatenate([ellipse(x, gy - h + w / 2, w / 2, w / 2, 24, np.pi, 2 * np.pi), [[x + w / 2, gy + 1], [x - w / 2, gy + 1]]])
    toon(s, [dp], dm, 1.2, shift=(-0.14, 0), shrink=1.0)
    if glass:
        gp = np.concatenate([ellipse(x, gy - h + w / 2 + 3, w / 2 - 6, w / 2 - 6, 20, np.pi, 2 * np.pi), [[x + w / 2 - 6, gy - h * 0.5], [x - w / 2 + 6, gy - h * 0.5]]])
        s.shape(gp, M['glow']['base'], dm['line'], 1.0)
        s.fill(poly([(x - w / 2 + 6, gy - h * 0.55), (x - 2, gy - h + w * 0.3), (x + 2, gy - h + w * 0.3), (x - w / 2 + 6, gy - h * 0.62)]), M['glow']['hi'])
    s.shape(circle(x + w * 0.3, gy - h * 0.42, 2.4, 10), M['cream']['shade'], M['cream']['line'], 0.8)
    s.shape(rrect(x - w / 2 - 9, gy - 4, x + w / 2 + 9, gy + 3, 2), M['stone']['base'], M['stone']['line'], 1.2)


def shroom_sign(s, x, y, r, rng, motif='shroom'):
    """둥근 걸이 간판: 은은한 버섯(또는 빵, 찻잔) 아이콘."""
    wd = M['darkwood']
    s.stroke(poly([(x - r * 0.6, y - r - 10), (x - r * 0.6, y - r + 2)]), wd['line'], 1.4)
    s.stroke(poly([(x + r * 0.6, y - r - 10), (x + r * 0.6, y - r + 2)]), wd['line'], 1.4)
    toon(s, [circle(x, y, r, 40)], M['cream'], LW, shift=(-0.05, -0.08), shrink=0.95)
    s.outline(circle(x, y, r - 3, 40), M['cream']['deep'], 0.7)
    if motif == 'shroom':
        cap = catmull([(x - r * 0.55, y), (x - r * 0.4, y - r * 0.35), (x, y - r * 0.5), (x + r * 0.4, y - r * 0.35), (x + r * 0.55, y), (x, y + r * 0.08)], True, 6)
        s.fill(rrect(x - r * 0.14, y - r * 0.05, x + r * 0.14, y + r * 0.5, 2), M['warmgray']['base'])
        s.fill(cap, M['terracotta']['base'])
        s.fill(circle(x - r * 0.15, y - r * 0.25, r * 0.08, 8), M['cream']['hi'])
    elif motif == 'bread':
        b = ellipse(x, y + r * 0.05, r * 0.55, r * 0.32)
        s.fill(b, M['wood']['base'])
        for k in (-1, 0, 1):
            s.stroke(poly([(x + k * r * 0.25 - 3, y + 3), (x + k * r * 0.25 + 3, y - 5)]), M['cream']['base'], 1.6)
    elif motif == 'cup':
        s.fill(rrect(x - r * 0.35, y - r * 0.2, x + r * 0.3, y + r * 0.35, 3), M['sage']['base'])
        s.outline(ellipse(x + r * 0.38, y + r * 0.05, r * 0.12, r * 0.14, 12), M['sage']['base'], 1.4)
        for k in (-1, 1):
            s.stroke(qbez((x + k * 3, y - r * 0.3), (x + k * 3 + 3, y - r * 0.45), (x + k * 3, y - r * 0.6), 6), M['warmgray']['base'], 1.1)


def building(s, x, gy, w, h, rng, roof='terracotta', wall='plaster', kind='cafe', awn=('cream', 'terracotta'), lw=LW):
    """나무와 흰 벽 건물. 지붕은 둥근 곡선(버섯 갓을 은은하게 닮은 돔형 처마)."""
    wm = M[wall]
    wd = M['darkwood']
    rm = M[roof]
    wall_top = gy - h
    # 벽
    body = rect(x - w / 2, wall_top, x + w / 2, gy + 1)
    s.shape(body, wm['base'], wm['line'], lw)
    s.clip(body)
    s.fill(rect(x + w * 0.28, wall_top, x + w / 2 + 2, gy + 2), wm['shade'])
    # 벽 아래 돌 띠
    s.fill(rect(x - w / 2 - 2, gy - 22, x + w / 2 + 2, gy + 2), M['stone']['base'])
    for i, xx in enumerate(np.arange(x - w / 2 - 10, x + w / 2 + 10, 20)):
        s.outline(rrect(xx + (i % 2) * 4, gy - 21, xx + 18 + (i % 2) * 4, gy - 11, 3), M['stone']['deep'], 0.6)
        s.outline(rrect(xx + 9, gy - 10, xx + 27, gy + 1, 3), M['stone']['deep'], 0.6)
    s.stroke(poly([(x - w / 2, gy - 22), (x + w / 2, gy - 22)]), M['stone']['line'], 1.2)
    # 목조 띠(하프팀버)
    for bx in (x - w / 2 + 5, x + w / 2 - 5):
        s.fill(rect(bx - 5, wall_top, bx + 5, gy - 22), wd['base'])
    s.fill(rect(x - w / 2, wall_top + h * 0.42, x + w / 2, wall_top + h * 0.42 + 8), wd['base'])
    s.fill(rect(x - w / 2, wall_top + h * 0.42, x + w / 2, wall_top + h * 0.42 + 2), wd['hi'])
    # 회벽 얼룩 질감
    dabs(s, x - w / 2, wall_top, x + w / 2, gy - 24, int(w * h / 1400), rng, [wm['shade'], wm['hi']], 2, 6, alpha=0.5)
    s.unclip()
    # 지붕: 둥근 돔형(버섯 갓 곡선), 넓은 처마
    ov = w * 0.14
    rh = h * 0.55
    ry0 = wall_top + 6
    roofp = catmull([(x - w / 2 - ov, ry0 + 4), (x - w / 2 - ov * 0.6, ry0 - rh * 0.35), (x - w * 0.3, ry0 - rh * 0.82), (x, ry0 - rh),
                     (x + w * 0.3, ry0 - rh * 0.82), (x + w / 2 + ov * 0.6, ry0 - rh * 0.35), (x + w / 2 + ov, ry0 + 4),
                     (x + w * 0.3, ry0 + 8), (x - w * 0.3, ry0 + 8)], True, 10)
    # 굴뚝
    cx_ = x + w * 0.24
    chim = rect(cx_ - 8, ry0 - rh * 1.05, cx_ + 8, ry0 - rh * 0.6)
    toon(s, [chim], M['stone'], lw, shift=(-0.2, 0), shrink=1.0)
    s.shape(rect(cx_ - 11, ry0 - rh * 1.05 - 5, cx_ + 11, ry0 - rh * 1.05 + 1), M['stone']['shade'], M['stone']['line'], 1.2)
    for i in range(3):
        rr = 5 + i * 3
        s.fill(circle(cx_ + 4 + i * 9, ry0 - rh * 1.05 - 14 - i * 13, rr), '#F4EEE6', alpha=0.45 - i * 0.12)
    s.shape(roofp, rm['shade'], rm['line'], lw)
    s.clip(roofp)
    s.fill(move(scale(roofp, 0.97, 0.9, x, ry0), -w * 0.03, -rh * 0.08), rm['base'])
    # 기와 결: 아래로 볼록한 비늘 줄
    yy = ry0 - rh + 14
    row = 0
    while yy < ry0 + 8:
        off = (row % 2) * 9
        for xx in np.arange(x - w / 2 - ov - 18 + off, x + w / 2 + ov + 18, 18):
            s.stroke(qbez((xx, yy), (xx + 9, yy + 8), (xx + 18, yy), 6), rm['deep'], 1.0, alpha=0.55)
        yy += 11
        row += 1
    s.fill(ellipse(x - w * 0.2, ry0 - rh * 0.72, w * 0.18, rh * 0.1), rm['hi'], alpha=0.8)
    s.fill(rect(x - w, ry0 - 2, x + w, ry0 + 12), rm['deep'])
    s.unclip()
    # 처마 아래 그늘
    s.clip(body)
    s.fill(rect(x - w / 2, wall_top, x + w / 2, wall_top + 14), wm['deep'], alpha=0.55)
    s.unclip()
    # 창, 문, 차양, 간판
    dw, dh = 34, 60
    if kind == 'cafe':
        dx = x - w * 0.22
        door(s, dx, gy - 1, dw, dh, 'darkwood')
        window(s, x + w * 0.2, gy - 76, 52, 44, rng=rng)
        awning(s, x + w * 0.2 - 40, x + w * 0.2 + 40, gy - 102, 20, awn)
        window(s, x - w * 0.18, wall_top + 18, 26, 26, arch=True, box=False, rng=rng)
        window(s, x + w * 0.2, wall_top + 18, 26, 26, arch=True, box=False, rng=rng)
        shroom_sign(s, x - w / 2 - 2, wall_top + h * 0.42 + 34, 15, rng, 'cup')
    elif kind == 'bakery':
        dx = x + w * 0.24
        door(s, dx, gy - 1, dw, dh, 'wood')
        window(s, x - w * 0.15, gy - 74, 66, 42, rng=rng)
        # 진열 빵
        for i in range(4):
            bx = x - w * 0.15 - 24 + i * 16
            s.shape(ellipse(bx, gy - 40, 6, 4, 12), M['wood']['base'], M['wood']['line'], 0.8)
        awning(s, x - w * 0.15 - 46, x - w * 0.15 + 46, gy - 100, 20, awn)
        window(s, x, wall_top + 16, 30, 30, arch=True, box=True, rng=rng)
        shroom_sign(s, x + w / 2 + 2, wall_top + h * 0.42 + 34, 15, rng, 'bread')
    else:  # shop
        door(s, x + w * 0.18, gy - 1, dw, dh, 'darkwood')
        s.clip(body)
        s.unclip()
        window(s, x - w * 0.2, gy - 72, 40, 38, rng=rng)
        awning(s, x - w * 0.2 - 30, x + w * 0.18 + 26, gy - 96, 18, awn)
        window(s, x, wall_top + 16, 26, 26, arch=True, box=False, rng=rng)
        shroom_sign(s, x - w / 2 - 2, wall_top + h * 0.42 + 34, 14, rng, 'shroom')


def crate(s, x, gy, w=28, produce=None, rng=None):
    m = M['wood']
    p = rect(x - w / 2, gy - w * 0.7, x + w / 2, gy + 1)
    if produce and rng is not None:
        pm = M[produce]
        for i in range(5):
            s.shape(circle(x - w * 0.36 + i * w * 0.18, gy - w * 0.72 - rng.uniform(0, 3), w * 0.12, 12), pm['base'], pm['line'], 0.9)
    toon(s, [p], m, 1.2, shift=(-0.05, -0.05), shrink=0.98)
    s.stroke(poly([(x - w / 2, gy - w * 0.35), (x + w / 2, gy - w * 0.35)]), m['line'], 1.0)


def barrel(s, x, gy, r=14):
    m = M['wood']
    h = r * 2.2
    p = catmull([(x - r * 0.85, gy), (x - r, gy - h / 2), (x - r * 0.85, gy - h), (x + r * 0.85, gy - h), (x + r, gy - h / 2), (x + r * 0.85, gy)], True, 6)
    toon(s, [p], m, 1.2, shift=(-0.12, 0), shrink=0.95)
    s.clip(p)
    for yy in (gy - h * 0.22, gy - h * 0.78):
        s.fill(rect(x - r - 2, yy - 2.5, x + r + 2, yy + 2.5), M['metal']['shade'])
    s.unclip()
    s.shape(ellipse(x, gy - h, r * 0.8, r * 0.2), m['shade'], m['line'], 1.0)


def fence(s, x0, x1, gy, h=30):
    m = M['wood']
    for yy in (gy - h * 0.7, gy - h * 0.35):
        toon(s, [rrect(x0 - 3, yy, x1 + 3, yy + 5, 2)], m, 1.2, shift=(0, -0.3), shrink=1.0)
    x = x0
    while x <= x1 + 0.1:
        p = poly([(x - 4, gy + 2), (x - 4, gy - h + 5), (x, gy - h), (x + 4, gy - h + 5), (x + 4, gy + 2)])
        toon(s, [p], m, 1.2, shift=(-0.25, 0), shrink=1.0)
        x += 20
