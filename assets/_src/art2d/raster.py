"""2D 벡터 → 래스터 (사이클 9, 메이플풍 셀 셰이딩).

- 좌표: 프레임 px(144x192, 기준점 (72,180)). 내부는 SS배 슈퍼샘플 캔버스에 그린 뒤 박스 평균으로 줄인다.
- 도형 = 닫힌 폴리곤(베지어/캣멀롬으로 촘촘히 샘플). 칠하기 순서: 바탕 -> 그늘(빛 반대쪽 초승달 자동 + 명시 그늘) ->
  디테일(도형 안으로 잘림) -> 외곽선(각 색의 진한 톤, 중심선 스트로크).
- 결정적: 난수는 seed 고정 numpy RandomState만 쓴다.
"""
import colorsys
import math
import numpy as np
from PIL import Image, ImageDraw

SS = 4
FW, FH = 144, 192
AX, AY = 72, 180
LW = 2.3          # 외곽선 두께 (출력 px)
LIGHT = (1.0, 1.25)   # 그늘 초승달: 도형을 빛 쪽(왼쪽 위)으로 민 거리 (출력 px)


# ---------------------------------------------------------------- 색
def rgb(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        return tuple(int(c[i:i + 2], 16) / 255.0 for i in range(0, 6, 2))
    return tuple(c)


def hexs(c):
    c = rgb(c)
    return '#%02X%02X%02X' % tuple(int(round(max(0, min(1, v)) * 255)) for v in c)


def _hsv(c):
    return colorsys.rgb_to_hsv(*rgb(c))


def _shift_h(h, target, k):
    d = ((target - h + 0.5) % 1.0) - 0.5
    return (h + d * k) % 1.0


def shade(c, k=1.0):
    """셀 그늘 1단: 어둡게, 채도 올리고 색상을 보라/빨강 쪽으로 약간."""
    h, s, v = _hsv(c)
    if s < 0.08:
        h, s = 0.66, s + 0.05 * k
    h = _shift_h(h, 0.78 if (h > 0.25 and h < 0.85) else 0.98, 0.10 * k)
    s = min(1.0, s * (1 + 0.22 * k) + 0.05 * k)
    v = v * (1 - 0.16 * k)
    return colorsys.hsv_to_rgb(h, s, v)


def deep(c, k=1.0):
    return shade(shade(c, k), k)


def light(c, k=1.0):
    h, s, v = _hsv(c)
    s = s * (1 - 0.40 * k)
    v = min(1.0, v + (1 - v) * 0.55 * k + 0.06 * k)
    return colorsys.hsv_to_rgb(h, s, v)


def line_of(c):
    """외곽선: 같은 색의 진한 톤 (검정 금지)."""
    h, s, v = _hsv(c)
    if s < 0.10:
        # 무채색: 차가운 회보라 계열
        return colorsys.hsv_to_rgb(0.70, 0.22 + s, max(0.22, v * 0.50))
    h = _shift_h(h, 0.80 if (h > 0.25 and h < 0.85) else 0.98, 0.12)
    return colorsys.hsv_to_rgb(h, min(1.0, s * 1.05 + 0.25), max(0.14, v * 0.46))


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


# ---------------------------------------------------------------- 기하
def rot(p, deg, o=(0, 0)):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    p = np.asarray(p, float)
    q = p - o
    return np.stack([q[..., 0] * ca - q[..., 1] * sa, q[..., 0] * sa + q[..., 1] * ca], -1) + o


class Xf:
    """2x3 아핀 변환. 회전은 화면 기준 시계방향이 +."""

    def __init__(self, m=None):
        self.m = np.eye(3) if m is None else m

    def __matmul__(self, o):
        return Xf(self.m @ o.m)

    @staticmethod
    def T(x, y):
        m = np.eye(3); m[0, 2] = x; m[1, 2] = y
        return Xf(m)

    @staticmethod
    def R(deg):
        a = math.radians(deg)
        m = np.eye(3); m[0, 0] = math.cos(a); m[0, 1] = -math.sin(a); m[1, 0] = math.sin(a); m[1, 1] = math.cos(a)
        return Xf(m)

    @staticmethod
    def S(sx, sy=None):
        m = np.eye(3); m[0, 0] = sx; m[1, 1] = sx if sy is None else sy
        return Xf(m)

    def __call__(self, pts):
        p = np.asarray(pts, float)
        return p @ self.m[:2, :2].T + self.m[:2, 2]

    def lin(self, v):
        return np.asarray(v, float) @ self.m[:2, :2].T

    @property
    def scale(self):
        return math.sqrt(abs(np.linalg.det(self.m[:2, :2])))


def cr(pts, n=7, closed=True):
    """캣멀롬 스플라인. 점 (x,y,'c')는 모서리(그 점에서 꺾임)."""
    P, C = [], []
    for p in pts:
        P.append((float(p[0]), float(p[1])))
        C.append(len(p) > 2)
    N = len(P)
    out = []
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p1 = np.array(P[i]); p2 = np.array(P[(i + 1) % N])
        if closed:
            p0 = np.array(P[(i - 1) % N]); p3 = np.array(P[(i + 2) % N])
        else:
            p0 = np.array(P[i - 1]) if i > 0 else p1 * 2 - p2
            p3 = np.array(P[i + 2]) if i + 2 < N else p2 * 2 - p1
        if C[i]:
            p0 = p1 * 2 - p2 if False else p1 - (p2 - p1) * 0.0001
        if C[(i + 1) % N]:
            p3 = p2 + (p2 - p1) * 0.0001
        # centripetal 근사: 표준 균일 CR + 접선 0.5
        m1 = (p2 - p0) * 0.5
        m2 = (p3 - p1) * 0.5
        if C[i]:
            m1 = (p2 - p1) * 0.35
        if C[(i + 1) % N]:
            m2 = (p2 - p1) * 0.35
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            h00 = 2 * t3 - 3 * t2 + 1; h10 = t3 - 2 * t2 + t; h01 = -2 * t3 + 3 * t2; h11 = t3 - t2
            out.append(h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2)
    if not closed:
        out.append(np.array(P[-1]))
    return np.array(out)


def bez(p0, c1, c2, p3, n=12):
    p0, c1, c2, p3 = map(lambda q: np.asarray(q, float), (p0, c1, c2, p3))
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * p3


def quad(p0, c, p2, n=12):
    p0, c, p2 = map(lambda q: np.asarray(q, float), (p0, c, p2))
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t * t * p2


def ellipse(cx, cy, rx, ry, n=40, a0=0, a1=360):
    a = np.radians(np.linspace(a0, a1, n, endpoint=(a1 - a0) < 360))
    return np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], -1)


def through(p0, p1, p2, n=20):
    """p1을 t=0.5에서 지나는 2차 곡선 (팔다리 중심선)."""
    p0, p1, p2 = map(lambda q: np.asarray(q, float), (p0, p1, p2))
    c = 2 * p1 - (p0 + p2) / 2
    return quad(p0, c, p2, n)


def resample(pts, n):
    pts = np.asarray(pts, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    if d[-1] < 1e-6:
        return np.repeat(pts[:1], n, 0)
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], -1)


def sub(pts, t0, t1, n=None):
    """중심선의 [t0,t1] 구간 (호 길이 기준)."""
    pts = np.asarray(pts, float)
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    L = d[-1]
    n = n or len(pts)
    s = np.linspace(t0 * L, t1 * L, n)
    return np.stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], -1)


def ribbon(c, w, cap0=True, cap1=True, ncap=7):
    """중심선 c 와 폭 w(스칼라 / 배열 / (t,w) 목록)로 폴리곤."""
    c = np.asarray(c, float)
    n = len(c)
    t = np.linspace(0, 1, n)
    if callable(w):
        W = np.array([w(x) for x in t])
    elif np.isscalar(w):
        W = np.full(n, float(w))
    else:
        w = list(w)
        if isinstance(w[0], (tuple, list)):
            W = np.interp(t, [a for a, b in w], [b for a, b in w])
        else:
            W = np.interp(t, np.linspace(0, 1, len(w)), w)
    tg = np.gradient(c, axis=0)
    tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
    nm = np.stack([-tg[:, 1], tg[:, 0]], -1)
    L = c + nm * (W[:, None] / 2)
    R = c - nm * (W[:, None] / 2)
    out = [L]
    if cap1 and W[-1] > 0.05:
        a0 = math.atan2(nm[-1, 1], nm[-1, 0])
        aa = np.linspace(a0, a0 - math.pi, ncap + 2)[1:-1]
        out.append(np.stack([c[-1, 0] + W[-1] / 2 * np.cos(aa), c[-1, 1] + W[-1] / 2 * np.sin(aa)], -1))
    out.append(R[::-1])
    if cap0 and W[0] > 0.05:
        a0 = math.atan2(-nm[0, 1], -nm[0, 0])
        aa = np.linspace(a0, a0 - math.pi, ncap + 2)[1:-1]
        out.append(np.stack([c[0, 0] + W[0] / 2 * np.cos(aa), c[0, 1] + W[0] / 2 * np.sin(aa)], -1))
    return np.concatenate(out, 0)


def taper(c, w, a=0.25, b=0.25, wmin=0.0):
    """양끝이 뾰족한 획."""
    def f(t):
        k = 1.0
        if a > 0 and t < a:
            k = min(k, t / a)
        if b > 0 and t > 1 - b:
            k = min(k, (1 - t) / b)
        return wmin + (w - wmin) * math.sin(k * math.pi / 2)
    return ribbon(c, f, cap0=False, cap1=False)


# ---------------------------------------------------------------- 래스터
def _bbox(polys, pad):
    allp = np.concatenate([np.asarray(p, float).reshape(-1, 2) for p in polys], 0) * SS
    x0 = int(math.floor(allp[:, 0].min() - pad)); y0 = int(math.floor(allp[:, 1].min() - pad))
    x1 = int(math.ceil(allp[:, 0].max() + pad)); y1 = int(math.ceil(allp[:, 1].max() + pad))
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(FW * SS, x1); y1 = min(FH * SS, y1)
    return x0, y0, x1, y1


def _mask(poly, box, stroke=None):
    x0, y0, x1, y1 = box
    im = Image.new('L', (x1 - x0, y1 - y0), 0)
    d = ImageDraw.Draw(im)
    p = np.asarray(poly, float) * SS - (x0, y0)
    pts = [tuple(q) for q in p]
    if len(pts) < 2:
        return np.zeros((y1 - y0, x1 - x0), np.float32)
    if stroke is None:
        if len(pts) >= 3:
            d.polygon(pts, fill=255)
    else:
        w = max(1, int(round(stroke * SS)))
        d.line(pts + pts[:2], fill=255, width=w, joint='curve')
    return np.asarray(im, np.float32) / 255.0


class Layer:
    def __init__(self):
        self.buf = np.zeros((FH * SS, FW * SS, 4), np.float32)   # 프리멀티플라이드
        self.used = False

    def over(self, box, a, col):
        x0, y0, x1, y1 = box
        if x1 <= x0 or y1 <= y0:
            return
        a = np.clip(a, 0, 1)
        if a.max() <= 0.002:
            return
        self.used = True
        dst = self.buf[y0:y1, x0:x1]
        if np.ndim(col) == 1:
            src = np.empty(a.shape + (4,), np.float32)
            src[..., :3] = np.asarray(col, np.float32)[None, None, :] * a[..., None]
            src[..., 3] = a
        else:
            src = np.concatenate([col * a[..., None], a[..., None]], -1)
        dst *= (1 - a[..., None])
        dst += src

    def image(self):
        b = self.buf.reshape(FH, SS, FW, SS, 4).mean(axis=(1, 3))
        a = b[..., 3:4]
        c = np.where(a > 1e-6, b[..., :3] / np.maximum(a, 1e-6), 0)
        out = np.concatenate([np.clip(c, 0, 1), np.clip(a, 0, 1)], -1)
        return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def fig(L, poly, col, *, line=None, lw=LW, shd=True, sd=None, sh=None, shapes=(), noline=False, alpha=1.0,
        hl=None, line_alpha=1.0, inner_line=False):
    """도형 하나를 칠한다.

    shd: 자동 그늘 초승달(빛 반대쪽). sd=(dx,dy) 민 거리. sh: 그늘 색.
    shapes: [(poly, color, alpha)] 도형 안으로 잘리는 추가 칠 (명시 그늘, 하이라이트, 무늬, 주름선).
    """
    poly = np.asarray(poly, float)
    col = rgb(col)
    pad = lw * SS + 3
    box = _bbox([poly], pad)
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        return
    m = _mask(poly, box)
    C = np.empty(m.shape + (3,), np.float32)
    C[...] = col
    if shd:
        sdv = sd if sd is not None else LIGHT
        shc = rgb(sh) if sh is not None else shade(col)
        m2 = _mask(poly - np.asarray(sdv), box)
        s = m * (1 - m2)
        C = C * (1 - s[..., None]) + np.asarray(shc, np.float32) * s[..., None]
    for item in shapes:
        sp, sc = item[0], item[1]
        sa = item[2] if len(item) > 2 else 1.0
        if sp is None or len(sp) < 3:
            continue
        mm = _mask(sp, box) * sa
        C = C * (1 - mm[..., None]) + np.asarray(rgb(sc), np.float32) * mm[..., None]
    L.over(box, m * alpha, C)
    if not noline:
        lc = rgb(line) if line is not None else line_of(col)
        o = _mask(poly, box, stroke=lw)
        if inner_line:
            o = o * m
        L.over(box, o * line_alpha * min(1.0, alpha * 1.5), lc)


def paint(L, poly, col, alpha=1.0):
    """외곽선 없는 칠 (볼터치, 그림자 레이어 등)."""
    poly = np.asarray(poly, float)
    box = _bbox([poly], 3)
    if box[2] <= box[0] or box[3] <= box[1]:
        return
    L.over(box, _mask(poly, box) * alpha, rgb(col))


def stroke(L, pts, col, w, alpha=1.0, closed=False):
    pts = np.asarray(pts, float)
    box = _bbox([pts], w * SS + 3)
    if box[2] <= box[0] or box[3] <= box[1]:
        return
    if closed:
        m = _mask(pts, box, stroke=w)
    else:
        m = _mask(ribbon(pts, w), box)
    L.over(box, m * alpha, rgb(col))
