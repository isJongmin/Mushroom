"""하의 9종 + 드롭 2종."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, quad, bez, rot, shade, light, deep, line_of, mix, sub
from cloth import pant_leg, cxo, fold, T
from body import leg_line, leg_layer


def waist(ctx, col, y0=-7.0, y1=4.5, belt=None, loops=True, band=True):
    if ctx.q:
        pts = [(-11.2, y0, 'c'), (11.8, y0, 'c'), (12.0, -1), (9.5, y1 - 0.5), (1, y1), (-8.5, y1 - 1), (-11.6, -1)]
    else:
        pts = [(-12.4, y0, 'c'), (12.4, y0, 'c'), (12.7, -1), (9, y1 - 0.8), (0, y1), (-9, y1 - 0.8), (-12.7, -1)]
    sh = []
    c = cxo(ctx)
    if band:
        bc = belt or shade(col, 0.5)
        sh.append((T(ctx, cr([(-14, y0, 'c'), (14, y0, 'c'), (14, y0 + 2.2, 'c'), (-14, y0 + 2.2, 'c')], 2)), bc, 1.0))
        if loops:
            for x in ((-7, 0, 7) if not ctx.q else (-6, 1, 8)):
                sh.append((T(ctx, cr([(x - 0.5, y0 - 0.2, 'c'), (x + 0.5, y0 - 0.2, 'c'), (x + 0.5, y0 + 2.6, 'c'),
                                      (x - 0.5, y0 + 2.6, 'c')], 2)), deep(col, 0.6), 0.9))
    if not ctx.back:
        sh.append((T(ctx, fold(quad((c, y0 + 2.4), (c + 0.3, y0 + 6), (c - 0.5, y1 - 0.5), 8), 0.8)), deep(col, 0.7), 0.8))
    ctx.fig('bottom', T(ctx, cr(pts, 5)), col, shapes=sh)


def legs(ctx, col, **kw):
    out = {}
    for k in ('F', 'N'):
        out[k] = pant_leg(ctx, k, col, **kw)
    return out


def side_pocket(ctx, k, col, t=0.42, w=6.0, h=6.5, flap=True):
    """허벅지 카고 주머니 (다리 중심선을 따라)."""
    c = leg_line(ctx, k, 20)
    p = sub(c, t - 0.12, t + 0.18, 8)
    d = p[-1] - p[0]
    L = np.linalg.norm(d)
    d = d / max(1e-6, L)
    n = np.array([-d[1], d[0]])
    sgn = 1 if ctx.q else (-1 if k == 'N' else 1)
    o = n * sgn * 1.6
    a0 = p[0] + o - n * w / 2; a1 = p[0] + o + n * w / 2
    b0 = p[-1] + o - n * w / 2; b1 = p[-1] + o + n * w / 2
    lay = leg_layer(ctx, k, 'bottom')
    body = cr([tuple(a0) + ('c',), tuple(a1) + ('c',), tuple(b1 + d * 0.6), tuple((b0 + b1) / 2 + d * 1.2), tuple(b0 + d * 0.6)], 4)
    ctx.fig(lay, body, col, lw=1.5)
    if flap:
        f = cr([tuple(a0 - d * 0.4) + ('c',), tuple(a1 - d * 0.4) + ('c',), tuple(a1 + d * 2.2) + ('c',), tuple(a0 + d * 2.2) + ('c',)], 2)
        ctx.fig(lay, f, col, lw=1.4, shapes=[(ellipse(*((a0 + a1) / 2 + d * 1.2), 0.6, 0.6, 8), light(col, 0.6))])


# ------------------------------------------------------------------
def b_denim_wide(ctx):
    col = '#A8C4E8'
    cuff = '#C8DCF4'
    waist(ctx, col)
    for k in ('F', 'N'):
        c = pant_leg(ctx, k, col, w0=11.5, wk=11.6, w1=12.8, cuff=cuff, cuff_len=0.12,
                     shapes_extra=[])
        # 바깥 솔기
    # 무지 네모 패치 (허벅지)
    k = 'N'
    c = leg_line(ctx, k, 20)
    p = c[7] + (np.array([-2.0, 0]) if not ctx.q else np.array([0.5, 0]))
    sq = cr([(p[0] - 2.2, p[1] - 2.2, 'c'), (p[0] + 2.2, p[1] - 2.2, 'c'), (p[0] + 2.2, p[1] + 2.2, 'c'),
             (p[0] - 2.2, p[1] + 2.2, 'c')], 2)
    if not ctx.back:
        ctx.fig(leg_layer(ctx, k, 'bottom'), sq, '#C3AEF0', lw=1.1, line='#6A55A8',
                shapes=[(ellipse(p[0] - 0.9, p[1] - 0.4, 0.35, 0.5, 8), '#6A55A8'),
                        (ellipse(p[0] + 0.9, p[1] - 0.4, 0.35, 0.5, 8), '#6A55A8'),
                        (taper(quad((p[0] - 1.1, p[1] + 0.8), (p[0], p[1] + 1.6), (p[0] + 1.1, p[1] + 0.8), 6), 0.4, 0.2, 0.2), '#6A55A8')])


def b_cargo_black(ctx):
    col = '#3A3742'
    waist(ctx, col)
    for k in ('F', 'N'):
        pant_leg(ctx, k, col, w0=11.0, wk=10.6, w1=8.6, cuff=col, cuff_len=0.1)
    for k in ('F', 'N'):
        if ctx.q and k == 'F':
            continue
        side_pocket(ctx, k, col)
    # 은 체인
    if not ctx.back:
        c = cxo(ctx)
        x0, x1 = (c + 5, c + 11.5) if not ctx.q else (c + 3, c + 10.5)
        ch = quad((x0, -4.5), ((x0 + x1) / 2, 3.5 + ctx.sway * 0.5), (x1, -3.5), 14)
        for i in range(0, 14, 2):
            p = ch[i]
            ctx.fig('bottom', T(ctx, ellipse(p[0], p[1], 0.9, 0.6, 8)), '#DDE0EA', lw=0.7, line='#6E7488', shd=False)


def b_cargo_beige(ctx):
    col = '#E6D4B2'
    waist(ctx, col)
    for k in ('F', 'N'):
        pant_leg(ctx, k, col, w0=11.8, wk=11.8, w1=12.4, cuff=col, cuff_len=0.08)
    for k in ('F', 'N'):
        if ctx.q and k == 'F':
            continue
        side_pocket(ctx, k, col, t=0.55, w=6.4, h=7)
    # 민트 키링 스트랩
    if not ctx.back:
        c = cxo(ctx)
        x = c - 7 if not ctx.q else c - 4
        s = quad((x, -5), (x - 0.5 + ctx.sway * 0.3, -1), (x + 0.2 + ctx.sway * 0.6, 3.5), 8)
        ctx.fig('bottom', T(ctx, ribbon(s, 1.3)), '#7ED6B4', lw=0.9)


def b_pants(col, crease=True):
    def f(ctx):
        waist(ctx, col)
        for k in ('F', 'N'):
            sh = []
            if crease:
                c = leg_line(ctx, k, 16)
                sh.append((taper(sub(c, 0.15, 0.95, 10), 0.8, 0.1, 0.1), light(col, 0.35), 0.8))
            pant_leg(ctx, k, col, w0=10.4, wk=9.6, w1=9.4, shapes_extra=sh)
    return f


def b_jeans_blue(ctx):
    col = '#4F7CC6'
    stitch = '#E9A64A'
    waist(ctx, col, belt='#3E68AE')
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 16)
        sh = [(taper(sub(c, 0.05, 0.95, 10) + (1.8, 0), 0.45, 0.1, 0.1), stitch, 0.8)]
        pant_leg(ctx, k, col, w0=10.4, wk=9.8, w1=10.0, shapes_extra=sh, cuff='#6E96D8', cuff_len=0.09)
    if not ctx.back:
        c = cxo(ctx)
        for sx in (-1, 1):
            ctx.paint('bottom', T(ctx, taper(quad((c + sx * 5, -4.8), (c + sx * 8.5, -4.0), (c + sx * 10.5, -1), 8), 0.5, 0.1, 0.1)),
                      stitch, 0.9)


def b_shorts_brown(ctx):
    col = '#9C6C46'
    waist(ctx, col)
    for k in ('F', 'N'):
        pant_leg(ctx, k, col, w0=11.2, wk=11.0, w1=11.4, t1=0.5, cuff=light(col, 0.3), cuff_len=0.2, folds=False)


def skirt(ctx, col, y0=-7.0, hem=12.0, flare=17.0, pleats=8, pattern=None, frill=None, band=None):
    sw = ctx.sway * 1.2
    if ctx.q:
        xl0, xr0 = -11.0, 12.0
        xl1, xr1 = -flare + 1.5, flare + 0.5
    else:
        xl0, xr0 = -12.4, 12.4
        xl1, xr1 = -flare, flare
    xs = np.linspace(xr1, xl1, pleats + 1)
    hemp = []
    for i, x in enumerate(xs):
        y = hem + 0.6 * math.sin((x - xl1) / (xr1 - xl1) * math.pi)
        hemp.append((x - sw, y + (1.0 if i % 2 else 0.0), 'c'))
    pts = [(xl0, y0, 'c'), (xr0, y0, 'c')] + hemp
    sh = []
    for i, x in enumerate(xs[1:-1]):
        xt = xl0 + (xr0 - xl0) * (1 - (i + 1) / pleats)
        sh.append((T(ctx, fold(quad((xt, y0 + 2.5), ((xt + x) / 2, (y0 + hem) / 2), (x - sw, hem + 0.4), 8), 1.0)),
                   shade(col, 1.2), 0.85))
        if i % 2 == 0:
            sh.append((T(ctx, cr([(xt, y0 + 2.5), (x - sw, hem + 0.8), (xs[i + 2] - sw if i + 2 < len(xs) else x - sw, hem + 0.8),
                                  (xt - (xr0 - xl0) / pleats, y0 + 2.5)], 3)), shade(col, 0.6), 0.55))
    if pattern:
        sh = pattern(ctx, xl1, xr1, y0, hem) + sh
    if band:
        sh.append((T(ctx, cr([(-15, y0, 'c'), (15, y0, 'c'), (15, y0 + 2.4, 'c'), (-15, y0 + 2.4, 'c')], 2)), band, 1.0))
    ctx.fig('bottom', T(ctx, cr(pts, 5)), col, shapes=sh, sd=(1.2, 1.6))
    if frill:
        fx = np.linspace(xl1 - 0.5, xr1 + 0.5, pleats * 2 + 1)
        fp = [(fx[0] - sw, hem - 0.5, 'c')]
        for i in range(len(fx) - 1):
            fp += [((fx[i] + fx[i + 1]) / 2 - sw, hem + 3.2), (fx[i + 1] - sw, hem + 1.8, 'c')]
        fp += [(fx[-1] - sw, hem - 0.5, 'c')]
        ctx.fig('bottom', T(ctx, cr(fp, 4)), frill, lw=1.3)


def check_pattern(dark, light_):
    def f(ctx, xl, xr, y0, hem):
        out = []
        for x in np.arange(xl - 4, xr + 4, 4.2):
            out.append((T(ctx, cr([(x, y0, 'c'), (x + 1.4, y0, 'c'), (x + 2.0, hem + 2, 'c'), (x + 0.6, hem + 2, 'c')], 2)), dark, 0.45))
        for y in np.arange(y0 + 3, hem + 2, 4.0):
            out.append((T(ctx, cr([(xl - 4, y, 'c'), (xr + 4, y, 'c'), (xr + 4, y + 1.3, 'c'), (xl - 4, y + 1.3, 'c')], 2)), dark, 0.45))
            out.append((T(ctx, cr([(xl - 4, y + 2.1, 'c'), (xr + 4, y + 2.1, 'c'), (xr + 4, y + 2.5, 'c'), (xl - 4, y + 2.5, 'c')], 2)), light_, 0.8))
        return out
    return f


def b_skirt_check(ctx):
    skirt(ctx, '#B8A898', hem=10.0, flare=16.0, pleats=9, pattern=check_pattern('#6E5E52', '#E4D8C8'), band='#8E7E70')


def b_skirt_pink(ctx):
    skirt(ctx, '#F7A6C8', hem=11.0, flare=17.0, pleats=7, frill='#FFF0F6', band='#E886B0')
    if not ctx.back:
        c = cxo(ctx)
        x, y = c + (6 if not ctx.front else 7), -5.8
        for sx in (-1, 1):
            ctx.fig('bottom', T(ctx, cr([(x, y), (x + sx * 2.6, y - 1.6), (x + sx * 2.8, y + 1.4)], 5)), '#FFFFFF', lw=1.0,
                    line='#C06890')
        ctx.fig('bottom', T(ctx, ellipse(x, y, 0.8, 0.8, 8)), '#FFE0EC', lw=0.8, line='#C06890')


# ------------------------------------------------------------------ 드롭
def b_mushroom_shorts(ctx):
    col = '#F2903A'
    spot = '#FFF1D6'
    waist(ctx, '#8A5A3A', loops=False, band=False)
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 16)
        spots = []
        for t, o, r in ((0.12, -1.8, 1.6), (0.3, 2.2, 1.2), (0.42, -1.0, 0.9)):
            p = sub(c, t, t + 0.01, 2)[0] + (o, 0)
            spots.append((ellipse(p[0], p[1], r, r * 0.85, 12), spot, 1.0))
        pant_leg(ctx, k, col, w0=12.2, wk=12.4, w1=13.2, t1=0.52, folds=False, shapes_extra=spots, ext=4)
        # 버섯 갓 아래 주름 밑단
        cc = sub(c, 0.46, 0.53, 6)
        ctx.fig(leg_layer(ctx, k, 'bottom'), ribbon(cc, 12.6, cap0=False, cap1=False), spot,
                shapes=[(taper(sub(cc, 0.0, 1.0, 4) + (x, 0), 0.5, 0.1, 0.1), '#D8B88A', 0.9) for x in (-3, -1, 1, 3)])
    # 갈색 허리 + 작은 버섯 단추
    c = cxo(ctx)
    ctx.fig('bottom', T(ctx, cr([(-13, -7, 'c'), (13, -7, 'c'), (13, -3.5, 'c'), (-13, -3.5, 'c')], 2)), '#8A5A3A')
    if not ctx.back:
        ctx.fig('bottom', T(ctx, cr([(c - 2.4, -5.2), (c - 1.6, -7.4), (c + 1.6, -7.4), (c + 2.4, -5.2)], 4)), '#E8483E', lw=0.9,
                shapes=[(T(ctx, ellipse(c - 0.6, -6.5, 0.5, 0.4, 6)), '#FFFFFF')])
        ctx.fig('bottom', T(ctx, cr([(c - 1.0, -5.2, 'c'), (c + 1.0, -5.2, 'c'), (c + 0.8, -3.6, 'c'), (c - 0.8, -3.6, 'c')], 2)),
                '#FFF1D6', lw=0.8)


def b_slime_pants(ctx):
    g = '#86DC6C'
    gl = light(g, 1.0)
    waist(ctx, g, loops=False, belt=shade(g, 0.6))
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 16)
        sh = [(taper(sub(c, 0.08, 0.6, 10) + (-1.8, 0), 1.6, 0.3, 0.3), gl, 0.85)]
        for t, r in ((0.3, 0.8), (0.7, 0.6)):
            p = sub(c, t, t + 0.01, 2)[0] + (1.5, 0)
            sh.append((ellipse(p[0], p[1], r, r, 8), '#FFFFFF', 0.85))
        cc = pant_leg(ctx, k, g, w0=11.0, wk=10.4, w1=10.4, shapes_extra=sh, folds=False)
        # 방울 밑단
        e = cc[-1]
        d = cc[-1] - cc[-3]
        d = d / np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        for o, L in ((-3.4, 2.6), (0.2, 3.6), (3.6, 2.2)):
            p = e + n * o - d * 1.0
            drip = cr([tuple(p - n * 1.6), tuple(p + n * 1.6), tuple(p + d * L * 0.6 + n * 1.0), tuple(p + d * L),
                       tuple(p + d * L * 0.6 - n * 1.0)], 4)
            ctx.fig(leg_layer(ctx, k, 'bottom'), drip, g, lw=1.4)


BOTTOMS = {
    'denim-wide': b_denim_wide, 'skirt-check': b_skirt_check, 'cargo-black': b_cargo_black,
    'cargo-beige': b_cargo_beige, 'pants-navy': b_pants('#36437E'), 'pants-black': b_pants('#2F2C36'),
    'skirt-pink': b_skirt_pink, 'shorts-brown': b_shorts_brown, 'jeans-blue': b_jeans_blue,
    'mushroom-shorts': b_mushroom_shorts, 'slime-pants': b_slime_pants,
}
