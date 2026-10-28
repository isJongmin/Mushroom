"""도형 도우미 (레이어 px 좌표). 모두 (N,2) float 배열을 돌려준다."""
import numpy as np

TAU = 2 * np.pi


def circle(cx, cy, r, n=None):
    return ellipse(cx, cy, r, r, n)


def ellipse(cx, cy, rx, ry, n=None, a0=0.0, a1=TAU):
    if n is None:
        n = int(max(16, min(160, (rx + ry) * 0.9)))
    t = np.linspace(a0, a1, n, endpoint=(a1 - a0) < TAU - 1e-9)
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t)], -1)


def catmull(pts, closed=True, seg=10, tension=0.5):
    """점들을 지나는 부드러운 곡선(Catmull-Rom)."""
    P = np.asarray(pts, np.float64)
    n = len(P)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if (closed or i > 0) else P[i]
        p1 = P[i]
        p2 = P[(i + 1) % n]
        p3 = P[(i + 2) % n] if (closed or i + 2 < n) else P[(i + 1) % n]
        t = np.linspace(0, 1, seg, endpoint=False)[:, None]
        m1 = (p2 - p0) * tension
        m2 = (p3 - p1) * tension
        t2, t3 = t * t, t * t * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        out.append(h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2)
    if not closed:
        out.append(P[-1:])
    return np.concatenate(out, 0)


def bez(p0, p1, p2, p3, n=16):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def qbez(p0, p1, p2, n=16):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = map(np.asarray, (p0, p1, p2))
    return ((1 - t) ** 2) * p0 + 2 * (1 - t) * t * p1 + t * t * p2


def rrect(x0, y0, x1, y1, r, n=8):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = []
    for (cx, cy, a) in ((x1 - r, y0 + r, -np.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, np.pi / 2), (x0 + r, y0 + r, np.pi)):
        t = np.linspace(a, a + np.pi / 2, n)
        pts.append(np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], -1))
    return np.concatenate(pts, 0)


def rect(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float64)


def poly(pts):
    return np.asarray(pts, np.float64)


def move(p, dx, dy):
    return np.asarray(p) + (dx, dy)


def scale(p, sx, sy=None, cx=0.0, cy=0.0):
    sy = sx if sy is None else sy
    q = np.asarray(p, np.float64).copy()
    q[:, 0] = cx + (q[:, 0] - cx) * sx
    q[:, 1] = cy + (q[:, 1] - cy) * sy
    return q


def rot(p, ang, cx, cy):
    c, s = np.cos(ang), np.sin(ang)
    q = np.asarray(p, np.float64) - (cx, cy)
    return np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], -1) + (cx, cy)


def flipx(p, cx):
    q = np.asarray(p, np.float64).copy()
    q[:, 0] = 2 * cx - q[:, 0]
    return q[::-1]


def blob(cx, cy, rx, ry, rng, k=9, jit=0.12, seg=8):
    """울퉁불퉁한 둥근 덩어리."""
    a = np.linspace(0, 2 * np.pi, k, endpoint=False) + rng.uniform(0, 0.5)
    r = 1 + rng.uniform(-jit, jit, k)
    pts = np.stack([cx + rx * r * np.cos(a), cy + ry * r * np.sin(a)], -1)
    return catmull(pts, True, seg)


def wave_edge(x0, x1, y, amp, period, rng, phase=None, step=4.0):
    """x0→x1 물결선 점들."""
    xs = np.arange(x0, x1 + step, step)
    xs[-1] = x1
    ph = rng.uniform(0, 6.28) if phase is None else phase
    ys = y + amp * np.sin(xs / period * 2 * np.pi + ph) + amp * 0.4 * np.sin(xs / (period * 0.37) * 2 * np.pi + ph * 1.7)
    return np.stack([xs, ys], -1)


def scallop(x0, x1, y, depth, width, rng, step=3.0):
    """아래로 늘어진 둥근 물결(잔디 가장자리) 점들, x0→x1."""
    pts = []
    x = x0
    while x < x1 - 1e-6:
        w = width * rng.uniform(0.7, 1.3)
        w = min(w, x1 - x)
        d = depth * rng.uniform(0.6, 1.25)
        n = max(4, int(w / step))
        t = np.linspace(0, 1, n, endpoint=False)
        xs = x + t * w
        ys = y + d * np.sin(t * np.pi) ** 0.8
        pts.append(np.stack([xs, ys], -1))
        x += w
    pts.append(np.array([[x1, y]]))
    return np.concatenate(pts, 0)
