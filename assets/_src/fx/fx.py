"""사이클 10 이펙트: 버프 아이콘 5종, 드롭 구슬 시트, 속성 베기 3종.

벡터 래스터라이저는 art2d_mob/vec.py를 그대로 쓴다(4배 슈퍼샘플, 결정적).
아이콘/구슬은 좌표 단위를 에셋 px로 쓴다(c.k = SS). 원점 = 프레임 중심.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'art2d_mob'))

from vec import SS, Canvas, hx, mix, tone, ellipse, path, star, rrect, xform, twinkle, WHITE  # noqa: E402
from extras import _crescent  # noqa: E402

import spec  # noqa: E402

TAU = 2 * math.pi

# 버프 색: base(배지 몸), dark(테두리/글리프 외곽선). 색상환에서 고르게 떨어뜨린다.
BUFF_COL = {
    'range':   dict(base='#3EC27C', light='#A6F0B8', dark='#1C6A48'),
    'multi':   dict(base='#4A84F4', light='#A8CCFF', dark='#22398E'),
    'element': dict(base='#9C66E8', light='#D8BCFF', dark='#4A2A8C'),
    'power':   dict(base='#EE4A48', light='#FFB2A2', dark='#8E1E30'),
    'speed':   dict(base='#FFB01E', light='#FFE89A', dark='#A0500E'),
}
EL_FIRE, EL_WATER, EL_BOLT = '#FF7A26', '#3CB8FF', '#FFD430'


# ---------------------------------------------------------------- 공용
def px_canvas(w, h, cx, cy):
    c = Canvas(w, h, cx, cy)
    c.k = SS * 1.0   # 좌표 = 에셋 px
    return c


def _gauss1d(sig):
    r = max(1, int(math.ceil(sig * 3)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    k = np.exp(-0.5 * (x / sig) ** 2)
    return k / k.sum(), r


def blur(a, sig):
    """2D 분리 가우시안(numpy, 경계 0). a: (H,W) 또는 (H,W,C)."""
    k, r = _gauss1d(sig)
    out = a.astype(np.float32)
    for ax in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[ax] = (r, r)
        p = np.pad(out, pad)
        acc = np.zeros_like(out)
        n = out.shape[ax]
        for i, kv in enumerate(k):
            sl = [slice(None)] * out.ndim
            sl[ax] = slice(i, i + n)
            acc += kv * p[tuple(sl)]
        out = acc
    return out


def glow_mask(c, m, col, sig_px, a=1.0):
    """마스크 m(슈퍼샘플 해상도)을 흐려 col로 칠한다. sig_px = 에셋 px."""
    g = blur(m, sig_px * SS)
    c.paint(np.clip(g, 0, 1), hx(col) if isinstance(col, str) else col, a)


def hexs(v):
    return '#%02X%02X%02X' % tuple(int(round(float(x) * 255)) for x in v)


def grid(c):
    """슈퍼샘플 픽셀 중심의 좌표(에셋 px, 원점 기준)."""
    ys, xs = np.mgrid[0:c.H, 0:c.W].astype(np.float32)
    return (xs + 0.5 - c.ox) / c.k, (ys + 0.5 - c.oy) / c.k


def radial(c, cx, cy, r, cin, cout, clip, gamma=1.0):
    x, y = grid(c)
    t = np.clip(np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r, 0, 1) ** gamma
    col = hx(cin)[None, None, :] * (1 - t[..., None]) + hx(cout)[None, None, :] * t[..., None]
    al = clip[..., None]
    c.buf = c.buf * (1 - al) + np.concatenate([col, np.ones_like(t)[..., None]], 2) * al


def shape(c, polys, fill, ink, ow, sub=None, sub_off=(0.0, 0.0)):
    """외곽선(ink, 두께 ow px) + 채움 + 아래쪽 은은한 그늘(sub 색, 도형을 위로 민 사본의 바깥)."""
    polys = polys if isinstance(polys, list) else [polys]
    st = None
    for p in polys:
        q = c.stroke_mask(p, 2 * ow)
        st = q if st is None else np.maximum(st, q)
    m = c.umask(polys)
    c.paint(np.maximum(st, m), hx(ink) if isinstance(ink, str) else ink)
    c.paint(m, hx(fill) if isinstance(fill, str) else fill)
    if sub is not None:
        m2 = c.umask([xform(p, sub_off[0], sub_off[1]) for p in polys])
        c.paint(m * (1 - m2), hx(sub) if isinstance(sub, str) else sub, 1.0)
    return m


# ---------------------------------------------------------------- 글리프 (중심 0,0, 대략 +-21 px 범위)
def g_range():
    arrow = np.array([(-22, 0), (-11, -11), (-11, -4), (11, -4), (11, -11), (22, 0),
                      (11, 11), (11, 4), (-11, 4), (-11, 11)], np.float32)
    return [('w', arrow)]


def _blade(off):
    """살짝 휜 칼날 자국(대각선, 오른쪽 위가 뾰족)."""
    p = path((-16.0, 14.0), [((-9.0, 0.0), (2.0, -10.0), (17.0, -16.0)),
                             ((7.0, -2.0), (-3.0, 8.0), (-16.0, 14.0))], n=24)
    d = off / math.sqrt(2)
    return xform(p, d, d)


def g_multi():
    return [('w', _blade(-11.0)), ('w', _blade(0.0)), ('w', _blade(11.0))]


def _flame():
    return path((0.0, 9.0), [((-8.5, 9.0), (-10.0, 0.0), (-4.5, -5.0)),
                             ((-3.0, -6.5), (-2.5, -9.0), (0.5, -13.0)),
                             ((6.0, -8.0), (9.5, -3.0), (8.5, 2.0)),
                             ((7.5, 7.0), (4.0, 9.0), (0.0, 9.0))], n=14)


def _flame_in():
    return path((0.5, 8.0), [((-4.0, 8.0), (-4.8, 3.0), (-2.0, 0.0)),
                             ((-0.8, -1.5), (0.0, -3.5), (0.5, -5.5)),
                             ((3.5, -2.0), (5.0, 1.0), (4.6, 3.5)),
                             ((4.0, 6.5), (3.0, 8.0), (0.5, 8.0))], n=12)


def _drop():
    return path((0.0, -11.0), [((3.0, -6.0), (7.5, -1.5), (7.5, 3.0)),
                               ((7.5, 7.5), (4.0, 10.0), (0.0, 10.0)),
                               ((-4.0, 10.0), (-7.5, 7.5), (-7.5, 3.0)),
                               ((-7.5, -1.5), (-3.0, -6.0), (0.0, -11.0))], n=14)


def _bolt(s=1.0):
    p = np.array([(1.5, -12.0), (8.0, -12.0), (3.5, -3.0), (8.5, -3.0), (-3.0, 13.0), (-0.5, 2.0), (-6.0, 2.0)],
                 np.float32)
    return p * s


def g_element():
    return [('c', xform(_flame(), 0.0, -9.5), EL_FIRE, '#FFE27A', _flame_in(), (0.0, -9.5)),
            ('c', xform(_drop(), -10.5, 8.0), EL_WATER, '#D8F4FF', ellipse(-2.6, 3.0, 2.2, 3.2, rot=0.3), (-10.5, 8.0)),
            ('c', xform(_bolt(0.95), 11.0, 7.5), EL_BOLT, '#FFF6C0', None, (11.0, 7.5))]


def g_power():
    dx = -3.0
    blade = np.array([(-6.0, -22.0), (-2.0, -17.0), (-2.0, 5.0), (-10.0, 5.0), (-10.0, -17.0)], np.float32) + (dx, 0)
    guard = rrect(-15.5 + dx, 4.0, -0.5 + dx, 9.5, 2.2)
    grip = rrect(-8.3 + dx, 9.0, -3.7 + dx, 17.0, 1.0)
    pommel = ellipse(-6.0 + dx, 19.0, 3.4, 3.4, n=32)
    arrow = np.array([(14.0, -16.0), (23.0, -5.0), (17.5, -5.0), (17.5, 12.0), (10.5, 12.0), (10.5, -5.0), (5.0, -5.0)],
                     np.float32) + (dx, 0)
    return [('w', [blade, guard, grip, pommel]), ('y', arrow)]


def g_speed():
    bolt = np.array([(0.0, -21.0), (13.0, -21.0), (6.0, -6.0), (15.0, -6.0), (-4.0, 22.0), (1.0, 2.5), (-8.0, 2.5)],
                    np.float32) + (3.0, 0.0)
    def streak(x0, x1, y, h):   # 왼쪽이 가늘어지는 속도선
        return path((x0, y), [((x0 + 4, y - h * 0.5), (x1 - h, y - h), (x1 - h * 0.5, y - h)),
                              ((x1 + h * 0.3, y - h), (x1 + h * 0.3, y + h), (x1 - h * 0.5, y + h)),
                              ((x1 - h, y + h), (x0 + 4, y + h * 0.5), (x0, y))], n=12)
    lines = [streak(-23.0, -6.5, -10.0, 2.8), streak(-26.0, -10.0, 0.0, 2.8), streak(-22.0, -11.5, 10.0, 2.6)]
    return [('w', lines), ('w', bolt)]


GLYPH = {'range': g_range, 'multi': g_multi, 'element': g_element, 'power': g_power, 'speed': g_speed}


def draw_glyph(c, bid, s, ow, shadow=(1.0, 1.6), shadow_a=0.26):
    """글리프를 크기 s로 그린다. 흰 글리프 + 어두운 버프색 외곽선 + 아래 그늘."""
    col = BUFF_COL[bid]
    ink = hx(col['dark'])
    soft = mix(hx(col['light']), WHITE, 0.35)
    items = GLYPH[bid]()
    c.push(sx=s, sy=s)
    # 그림자(전체 한 덩어리)
    if shadow is not None:
        allp = []
        for it in items:
            p = it[1]
            allp += p if isinstance(p, list) else [p]
        sh = c.blank()
        sh.T = [c.T[-1].copy()]
        m = None
        for p in allp:
            q = np.maximum(sh.mask(xform(p, shadow[0] / s, shadow[1] / s)),
                           sh.stroke_mask(xform(p, shadow[0] / s, shadow[1] / s), 2 * ow))
            m = q if m is None else np.maximum(m, q)
        c.paint(m, tone(ink, 0.6), shadow_a)
    for it in items:
        kind, p = it[0], it[1]
        if kind == 'w':
            shape(c, p, WHITE, ink, ow, sub=soft, sub_off=(-0.0, -1.6))
        elif kind == 'y':
            shape(c, p, hx('#FFE45C'), ink, ow, sub=hx('#FFB82E'), sub_off=(0.0, -2.0))
        else:   # 속성 조각: 흰 테 + 고유색 + 안쪽 밝은 조각
            _, poly, fc, inner, ip, off = it
            m = shape(c, poly, fc, WHITE, ow * 0.9)
            c.paint(c.stroke_mask(poly, 2 * ow * 0.9 + 2.2 * s) * (1 - np.maximum(m, c.stroke_mask(poly, 2 * ow * 0.9))),
                    ink, 1.0)
            if ip is not None:
                c.fill(xform(ip, off[0], off[1]), hx(inner))
            elif poly is not None and fc == EL_BOLT:
                c.fill(xform(np.array([(1.8, -10.5), (5.5, -10.5), (2.4, -4.0)], np.float32) * 0.95, off[0], off[1]),
                       hx(inner))
    c.pop()


# ---------------------------------------------------------------- 아이콘 64x64
def icon(bid):
    n = spec.ICON
    c = px_canvas(n, n, n / 2, n / 2)
    col = BUFF_COL[bid]
    R = 29.5
    # 테두리
    c.fill(ellipse(0, 0, R + 1.5, R + 1.5, n=120), hx(col['dark']))
    body = c.mask(ellipse(0, 0, R - 1.0, R - 1.0, n=120))
    radial(c, -8.0, -10.0, R * 1.55, hexs(mix(hx(col['light']), hx(col['base']), 0.3)),
           hexs(tone(hx(col['base']), 0.82, 1.08)), body)
    # 안쪽 밝은 링 + 위쪽 광택
    c.line(ellipse(0, 0, R - 2.6, R - 2.6, n=120), hx(col['light']), 1.4, a=0.55, closed=True)
    c.fill(ellipse(-5.0, -17.0, 16.0, 7.0, rot=-0.15), WHITE, 0.28, clip=body)
    draw_glyph(c, bid, 1.0, 2.3)
    return c.image()


# ---------------------------------------------------------------- 구슬 48x48
def orb(c, bid):
    col = BUFF_COL[bid]
    R = 13.5
    # 바깥 글로우
    g = c.blank()
    glow_mask(g, g.mask(ellipse(0, 0, R + 1.5, R + 1.5, n=96)), col['base'], 3.0, 1.0)
    c.over(g, 1.0)
    g2 = c.blank()
    glow_mask(g2, g2.mask(ellipse(0, 0, R - 2.0, R - 2.0, n=96)), col['light'], 1.8, 1.0)
    c.over(g2, 0.55)
    # 몸
    c.fill(ellipse(0, 0, R + 0.9, R + 0.9, n=96), hx(col['dark']), 0.9)
    body = c.mask(ellipse(0, 0, R, R, n=96))
    radial(c, -3.5, -4.5, R * 1.6, hexs(mix(hx(col['light']), WHITE, 0.25)), hexs(tone(hx(col['base']), 0.78, 1.1)),
           body, gamma=0.9)
    # 아래쪽 반사광(유리)
    c.line(path((-9.0, 6.5), [((-5.0, 11.5), (5.0, 11.5), (9.0, 6.5))], n=20), hx(col['light']), 1.6, a=0.7)
    draw_glyph(c, bid, 0.5, 1.25, shadow=(0.6, 0.9), shadow_a=0.25)
    # 광택
    c.fill(ellipse(-5.0, -7.5, 5.0, 2.8, rot=-0.6), WHITE, 0.75, clip=body)
    c.fill(ellipse(-8.6, -2.2, 1.2, 1.2), WHITE, 0.6, clip=body)
    twinkle(c, 11.5, -11.0, 4.2, 0.95)
    twinkle(c, -12.5, 10.5, 2.6, 0.75)


def orb_sheet():
    from PIL import Image
    n = spec.ORB
    out = Image.new('RGBA', (n * len(spec.BUFFS), n), (0, 0, 0, 0))
    for i, bid in enumerate(spec.BUFFS):
        c = px_canvas(n, n, n / 2, n / 2)
        orb(c, bid)
        out.paste(c.image(), (i * n, 0))
    return out


# ---------------------------------------------------------------- 베기(slash.png와 같은 호, 색만 바꿈)
SLASH_PAL = {
    # 기본(slash.png) — 재현 확인용
    'base': dict(glow='#9EE6FF', body='#DDF8FF', core='#FFFFFF', line='#4AA6E0', speed='#BFF0FF', tw='#FFFFFF',
                 aura=None),
    'fire': dict(glow='#FF8A2E', body='#FFC46E', core='#FFF4D6', line='#D8461A', speed='#FFB060', tw='#FFF0C0',
                 aura='#FF7A1E'),
    'ice': dict(glow='#4CBEFF', body='#A4DEFF', core='#F0FBFF', line='#1F6CC8', speed='#8CD4FF', tw='#E8F8FF',
                aura='#3AAEFF'),
    'bolt': dict(glow='#FFD21E', body='#FFEB70', core='#FFFEF0', line='#C98A00', speed='#FFE266', tw='#FFFBD0',
                 aura='#FFC800'),
}


def slash(c, f, pal):
    P = SLASH_PAL[pal]
    cx, cy, R = 8.0, -42.0, 38.0
    if f == 0:
        a0, a1, th, al = -1.75, -0.15, 9.0, 0.95
    else:
        a0, a1, th, al = -1.35, 1.45, 12.0, 0.9
    sub = c.blank()
    if P['aura']:
        m = sub.mask(_crescent(cx, cy, R + 1.0, th + 3.0, a0, a1))
        glow_mask(sub, m, P['aura'], 3.0, 0.75)
    sub.fill(_crescent(cx, cy, R + 2.5, th + 5.0, a0 - 0.05, a1 + 0.05), hx(P['glow']), 0.35)
    sub.fill(_crescent(cx, cy, R, th, a0, a1), hx(P['body']), 0.95)
    sub.fill(_crescent(cx, cy, R - 1.2, th * 0.5, a0 + 0.12, a1 - 0.04), hx(P['core']), 1.0)
    sub.line(_crescent(cx, cy, R, th, a0, a1), hx(P['line']), 1.2, closed=True, a=0.55)
    for da, dr in ((0.3, 5.0), (0.55, 8.0), (0.8, 5.5)):
        a = a0 + (a1 - a0) * da
        r1 = R + dr
        sub.line(np.array([(cx + r1 * 1.25 * math.cos(a - 0.25), cy + r1 * math.sin(a - 0.25)),
                           (cx + r1 * 1.25 * math.cos(a - 0.05), cy + r1 * math.sin(a - 0.05))]), hx(P['speed']), 1.5, a=0.75)
    c.over(sub, al)
    tx, ty = cx + (R - 3) * 1.25 * math.cos(a1 - 0.08), cy + (R - 3) * math.sin(a1 - 0.08)
    twinkle(c, tx, ty, 5.5 if f == 0 else 4.0, 1.0, P['tw'])


def slash_sheet(pal):
    from PIL import Image
    fw, fh = spec.SLASH['frame']
    ax, ay = spec.SLASH['anchor']
    out = Image.new('RGBA', (fw * 2, fh), (0, 0, 0, 0))
    for i in range(2):
        c = Canvas(fw, fh, ax, ay)
        slash(c, i, pal)
        out.paste(c.image(), (i * fw, 0))
    return out
