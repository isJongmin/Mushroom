"""버섯마을 2D 벡터 일러스트 미니 래스터라이저 (몬스터/비석/유령/fx 공용).

- 좌표: 월드 단위, 원점 = 프레임 기준점(발 바닥 중앙), y는 아래로 +.
- 4배 슈퍼샘플로 그린 뒤 박스 필터로 축소한다(결정적, 난수 없음).
- 내부 버퍼는 premultiplied RGBA float32.
- 메이플풍: 각 도형마다 진한 색조 외곽선 + 셀 셰이딩 2단(밑색/그늘) + 하이라이트.
"""
import colorsys
import math

import numpy as np
from PIL import Image, ImageDraw

SS = 4          # 슈퍼샘플 배율
DENSITY = 1.5   # 에셋 px / 월드 단위


# ---------------------------------------------------------------- 색
def hx(s):
    s = s.lstrip('#')
    return np.array([int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def mix(a, b, t):
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def tone(c, v=1.0, s=1.0, h=0.0):
    """HSV 조정한 색. 외곽선/그늘 색 만들 때 쓴다."""
    r, g, b = [float(x) for x in c]
    H, S, V = colorsys.rgb_to_hsv(r, g, b)
    H = (H + h) % 1.0
    S = min(1.0, S * s)
    V = min(1.0, V * v)
    return np.array(colorsys.hsv_to_rgb(H, S, V), np.float32)


class Mat:
    """재질: hl(하이라이트) / base(밑색) / sh(그늘) / line(외곽선)."""

    def __init__(self, base, sh=None, hl=None, line=None):
        self.base = hx(base) if isinstance(base, str) else base
        self.sh = hx(sh) if isinstance(sh, str) else (sh if sh is not None else tone(self.base, 0.84, 1.18, -0.012))
        self.hl = hx(hl) if isinstance(hl, str) else (hl if hl is not None else mix(self.base, hx('#FFFFFF'), 0.55))
        self.line = hx(line) if isinstance(line, str) else (line if line is not None else tone(self.base, 0.42, 1.35, -0.02))


# ---------------------------------------------------------------- 도형 (월드 좌표 점 배열)
def ellipse(cx, cy, rx, ry, rot=0.0, n=72):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    x, y = rx * np.cos(t), ry * np.sin(t)
    c, s = math.cos(rot), math.sin(rot)
    return np.stack([cx + x * c - y * s, cy + x * s + y * c], 1)


def polar(cx, cy, fn, n=96):
    """fn(theta) -> (rx, ry). theta 0 = 오른쪽, pi/2 = 아래."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rx, ry = fn(t)
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return np.array(pts, np.float32)


def bez(p0, p1, p2, p3, n=18):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.asarray(p, np.float32) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def path(start, segs, n=18):
    """start=(x,y), segs=[(c1,c2,p), ...] 3차 베지어 연결. 닫힌 도형으로 쓴다."""
    pts = [np.asarray([start], np.float32)]
    cur = start
    for c1, c2, p in segs:
        pts.append(bez(cur, c1, c2, p, n)[1:])
        cur = p
    return np.concatenate(pts, 0)


def star(cx, cy, ro, ri, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        r = ro if i % 2 == 0 else ri
        a = rot + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts, np.float32)


def rrect(x0, y0, x1, y1, r, n=8):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts, np.float32)


def xform(pts, dx=0.0, dy=0.0, sx=1.0, sy=1.0, rot=0.0, ox=0.0, oy=0.0):
    """(ox,oy) 기준으로 크기/회전 후 이동."""
    p = np.asarray(pts, np.float32) - (ox, oy)
    p = p * (sx, sy)
    c, s = math.cos(rot), math.sin(rot)
    p = np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1)
    return p + (ox + dx, oy + dy)


# ---------------------------------------------------------------- 캔버스
class Canvas:
    def __init__(self, w, h, ax, ay):
        """w,h = 프레임 크기(에셋 px), ax,ay = 기준점(에셋 px)."""
        self.w, self.h = w, h
        self.W, self.H = w * SS, h * SS
        self.k = DENSITY * SS
        self.ox, self.oy = ax * SS, ay * SS
        self.buf = np.zeros((self.H, self.W, 4), np.float32)
        self.T = [np.eye(3, dtype=np.float32)]

    # 변환 스택 (몸 전체 기울이기, 눌림 등)
    def push(self, dx=0.0, dy=0.0, sx=1.0, sy=1.0, rot=0.0, ox=0.0, oy=0.0):
        c, s = math.cos(rot), math.sin(rot)
        M = (np.array([[1, 0, ox + dx], [0, 1, oy + dy], [0, 0, 1]], np.float32)
             @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)
             @ np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1]], np.float32)
             @ np.array([[1, 0, -ox], [0, 1, -oy], [0, 0, 1]], np.float32))
        self.T.append(self.T[-1] @ M)

    def pop(self):
        self.T.pop()

    def scale_now(self):
        M = self.T[-1]
        return math.sqrt(abs(M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]))

    def to_px(self, pts):
        p = np.asarray(pts, np.float32)
        M = self.T[-1]
        x = M[0, 0] * p[:, 0] + M[0, 1] * p[:, 1] + M[0, 2]
        y = M[1, 0] * p[:, 0] + M[1, 1] * p[:, 1] + M[1, 2]
        return np.stack([self.ox + x * self.k, self.oy + y * self.k], 1)

    # 래스터
    def mask(self, pts):
        im = Image.new('L', (self.W, self.H), 0)
        ImageDraw.Draw(im).polygon([tuple(map(float, q)) for q in self.to_px(pts)], fill=255)
        return np.asarray(im, np.float32) / 255.0

    def stroke_mask(self, pts, width, closed=True):
        """width: 에셋 px 두께. 둥근 이음/끝."""
        px = self.to_px(pts)
        wpx = max(1.0, width * SS)
        im = Image.new('L', (self.W, self.H), 0)
        d = ImageDraw.Draw(im)
        seq = [tuple(map(float, q)) for q in px]
        if closed:
            seq = seq + [seq[0]]
        d.line(seq, fill=255, width=int(round(wpx)), joint='curve')
        r = wpx / 2
        for q in (seq[0], seq[-1]):
            d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=255)
        return np.asarray(im, np.float32) / 255.0

    def paint(self, m, col, a=1.0):
        if m is None:
            return
        al = (m * a)[..., None]
        c = np.concatenate([np.asarray(col, np.float32), [1.0]])
        self.buf = self.buf * (1 - al) + c * al

    # 일러스트 도형: 외곽선 + 밑색 + 그늘 + 하이라이트
    def umask(self, polys):
        m = None
        for p in polys:
            q = self.mask(p)
            m = q if m is None else np.maximum(m, q)
        return m

    def part(self, pts, mat, ol=2.2, shade=(0.0, 0.0), shade_sc=1.0, hl=None, hl_a=0.9,
             clip=None, ret=False, sh2=None):
        """pts: 도형 또는 도형 목록(합집합, 사이 외곽선 없음).
        shade=(dx,dy): 그늘 경계 = 도형을 빛쪽(왼쪽 위)으로 민 사본의 바깥.
        shade_sc: 그 사본의 크기 배율(도형 중심 기준). hl: 하이라이트 도형(들). sh2: 2단 그늘 오프셋."""
        polys = pts if isinstance(pts, list) else [pts]
        m = self.umask(polys)
        if clip is not None:
            m = m * clip
        if ol and ol > 0:
            st = None
            for p in polys:
                q = self.stroke_mask(p, 2 * ol)
                st = q if st is None else np.maximum(st, q)
            o = np.maximum(m, st * (clip if clip is not None else 1))
            self.paint(o, mat.line)
        self.paint(m, mat.base)
        c = np.concatenate([np.asarray(p, np.float32) for p in polys], 0).mean(0)
        if shade is not None and (shade[0] or shade[1] or shade_sc != 1.0):
            p2 = [xform(p, shade[0], shade[1], shade_sc, shade_sc, ox=c[0], oy=c[1]) for p in polys]
            self.paint(m * (1 - self.umask(p2)), mat.sh)
            if sh2 is not None:
                p3 = [xform(p, sh2[0], sh2[1], shade_sc, shade_sc, ox=c[0], oy=c[1]) for p in polys]
                self.paint(m * (1 - self.umask(p3)), tone(mat.sh, 0.86, 1.1), 0.8)
        if hl is not None:
            for h in (hl if isinstance(hl, list) else [hl]):
                self.paint(m * self.mask(h), mat.hl, hl_a)
        return m if ret else None

    def fill(self, pts, col, a=1.0, clip=None):
        m = self.mask(pts)
        if clip is not None:
            m = m * clip
        self.paint(m, col, a)
        return m

    def line(self, pts, col, width=1.6, a=1.0, closed=False, clip=None):
        m = self.stroke_mask(pts, width, closed)
        if clip is not None:
            m = m * clip
        self.paint(m, col, a)

    # 합성
    def blank(self):
        c = Canvas.__new__(Canvas)
        c.__dict__.update(self.__dict__)
        c.buf = np.zeros_like(self.buf)
        c.T = [self.T[-1].copy()]
        return c

    def over(self, other, a=1.0):
        al = other.buf[..., 3:4] * a
        self.buf = self.buf * (1 - al) + other.buf * a

    def tint(self, col, t):
        """불투명 부분의 색을 col 쪽으로 t만큼(피격 번쩍임 등)."""
        a = self.buf[..., 3:4]
        c = np.asarray(col, np.float32)
        self.buf[..., :3] = self.buf[..., :3] * (1 - t) + c * a * t

    def image(self):
        b = self.buf.reshape(self.h, SS, self.w, SS, 4).mean((1, 3))
        a = b[..., 3:4]
        rgb = np.where(a > 1e-6, b[..., :3] / np.maximum(a, 1e-6), 0)
        out = np.concatenate([rgb, a], 2)
        return Image.fromarray(np.clip(np.round(out * 255), 0, 255).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- 공용 부품
INK = hx('#2B1D2E')
WHITE = hx('#FFFFFF')


def eye(c, x, y, rx, ry, mode='open', col=INK, rot=0.0):
    """메이플풍 큰 눈: 세로 타원 + 하이라이트 2개.
    mode: open | hit(>< 꾹) | dead(X) | happy(^)"""
    s = max(rx, ry)
    if mode == 'open':
        c.fill(ellipse(x, y, rx, ry, rot), col)
        # 아래쪽 은은한 반사
        c.fill(ellipse(x, y + ry * 0.45, rx * 0.62, ry * 0.32), mix(col, hx('#8A5CB0'), 0.55), 0.85,
               clip=c.mask(ellipse(x, y, rx, ry, rot)))
        c.fill(ellipse(x + rx * 0.22, y - ry * 0.38, rx * 0.46, ry * 0.36), WHITE)
        c.fill(ellipse(x - rx * 0.32, y + ry * 0.36, rx * 0.22, ry * 0.18), WHITE, 0.95)
    elif mode == 'hit':
        w = s * 0.95
        c.line(np.array([(x - w * 0.7, y - w * 0.6), (x + w * 0.35, y), (x - w * 0.7, y + w * 0.6)]), col, s * 0.75 * DENSITY)
    elif mode == 'hitL':
        w = s * 0.95
        c.line(np.array([(x + w * 0.7, y - w * 0.6), (x - w * 0.35, y), (x + w * 0.7, y + w * 0.6)]), col, s * 0.75 * DENSITY)
    elif mode == 'dead':
        w = s * 0.7
        lw = s * 0.62 * DENSITY
        c.line(np.array([(x - w, y - w), (x + w, y + w)]), col, lw)
        c.line(np.array([(x - w, y + w), (x + w, y - w)]), col, lw)
    elif mode == 'happy':
        w = s * 0.9
        c.line(bez((x - w, y + w * 0.3), (x - w * 0.5, y - w * 0.7), (x + w * 0.5, y - w * 0.7), (x + w, y + w * 0.3)),
               col, s * 0.6 * DENSITY)


def blush(c, x, y, rx, ry, a=0.55):
    c.fill(ellipse(x, y, rx, ry), hx('#FF8FA8'), a)


def puff(c, x, y, r, a=1.0, col='#FFFFFF', line='#C4B8D6'):
    """연기 구름 한 덩이(4개 원 묶음, 외곽선 + 그늘)."""
    blobs = [(x, y, r), (x - r * 0.75, y + r * 0.25, r * 0.7), (x + r * 0.8, y + r * 0.2, r * 0.72),
             (x + r * 0.1, y - r * 0.55, r * 0.68)]
    sub = c.blank()
    m = sum_mask = None
    lc, fc = hx(line), hx(col)
    for bx, by, br in blobs:
        sub.paint(sub.stroke_mask(ellipse(bx, by, br, br, n=40), 2.2 * 1.0) , lc)
    for bx, by, br in blobs:
        sub.fill(ellipse(bx, by, br, br, n=40), fc)
    for bx, by, br in blobs:
        sub.fill(ellipse(bx + br * 0.18, by + br * 0.22, br * 0.82, br * 0.78, n=40), hx('#E6E0F0'), 1.0,
                 clip=sub.mask(ellipse(bx, by, br, br, n=40)) * (1 - sub.mask(ellipse(bx - br * 0.1, by - br * 0.12, br * 0.9, br * 0.86, n=40))))
    c.over(sub, a)


def sparkle(c, x, y, r, a=1.0, col='#FFE45C', line='#E0861E'):
    sub = c.blank()
    sub.part(star(x, y, r, r * 0.45), Mat(col, line=line, sh='#FFC93A'), ol=1.4, shade=(-r * 0.12, -r * 0.12))
    c.over(sub, a)


def twinkle(c, x, y, r, a=1.0, col='#FFFFFF'):
    """십자 반짝임(외곽선 없음)."""
    p = star(x, y, r, r * 0.18, n=4, rot=0)
    c.fill(p, hx(col), a)


def ground_shadow(c, rx, ry=None, a=0.22, y=0.0, x=0.0):
    sub = c.blank()
    ry = ry if ry is not None else rx * 0.22
    for i, f in enumerate((1.0, 0.8, 0.6)):
        sub.fill(ellipse(x, y, rx * f, ry * f), hx('#3A2440'), 0.45)
    c.over(sub, a)
