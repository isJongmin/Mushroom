"""옷 공용 도우미: 몸판, 소매, 바짓가랑이, 주름선."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, through, quad, bez, rot, shade, light, deep, line_of, rgb, mix, sub, \
    resample
from body import arm_line, leg_line, arm_layer, leg_layer


def cxo(ctx):
    """몸통 로컬 앞중심 x."""
    return 2.5 if ctx.q else 0.0


def body_poly(ctx, hem=3.5, flare=1.0, top=-25.5, sh=13.5, neck='crew', loose=0.0, waist=0.0):
    """몸판 외곽(몸통 로컬). neck: crew | v | high | none."""
    f = flare
    l = loose
    if ctx.q:
        nk = {'crew': [(6.5, top - 1.5), (2.5, top + 1.2), (-2.5, top - 1.5)],
              'v': [(6.5, top - 1.5), (3.5, top + 7.0, 'c'), (-2.0, top - 1.5)],
              'high': [(6.0, top - 3.5), (2.0, top - 2.0), (-3.0, top - 3.5)],
              'none': [(2.0, top)]}[neck]
        pts = [(-9.0 - l, top), (-11.0 - l, top + 4.5), (-10.6 - l + waist, -12), (-11.0 - l, -2),
               (-11.3 * f - l, hem, 'c'), (11.8 * f + l, hem, 'c'), (11.6 + l, -2), (10.8 + l - waist, -12),
               (12.2 + l, top + 4.5), (10.0 + l, top)] + nk
    else:
        nk = {'crew': [(4.6, top - 1.6), (0, top + 1.4), (-4.6, top - 1.6)],
              'v': [(4.6, top - 1.6), (0, top + 7.5, 'c'), (-4.6, top - 1.6)],
              'high': [(4.6, top - 3.6), (0, top - 2.2), (-4.6, top - 3.6)],
              'none': [(0, top)]}[neck]
        if ctx.back:
            nk = [(4.6, top - 1.8), (0, top - 1.0), (-4.6, top - 1.8)]
        pts = [(-11.0 - l, top), (-sh - l, top + 4.5), (-12.0 - l + waist, -12), (-12.4 - l, -2),
               (-12.6 * f - l, hem, 'c'), (12.6 * f + l, hem, 'c'), (12.4 + l, -2), (12.0 + l - waist, -12),
               (sh + l, top + 4.5), (11.0 + l, top)] + nk
    return cr(pts, 6)


def hem_band(ctx, y0, y1, flare=1.0, loose=0.0):
    l = loose
    if ctx.q:
        xl, xr = -11.3 * flare - l, 11.8 * flare + l
    else:
        xl, xr = -12.6 * flare - l, 12.6 * flare + l
    return cr([(xl + 0.3, y0, 'c'), (xr - 0.3, y0, 'c'), (xr, y1, 'c'), (xl, y1, 'c')], 3)


def sleeve_line(ctx, k, t1=1.0, ext=2.2):
    c = arm_line(ctx, k, 24)
    d = c[1] - c[0]
    d = d / max(1e-6, np.linalg.norm(d))
    c = np.concatenate([[c[0] - d * ext], c], 0)
    return resample(sub(c, 0, t1 * (1 - 0.0), 24), 24)


def sleeve(ctx, k, col, w0=7.6, w1=6.6, t1=0.95, cuff=None, cuff_w=None, cuff_len=0.16, puff=0.0, folds=True,
           shapes_extra=(), layer=None, lw=None, sh=None):
    """소매 하나. t1 = 팔 길이 비율(1 = 손목). cuff = 소맷부리 색."""
    lay = layer or arm_layer(ctx, k, 'top')
    c = sleeve_line(ctx, k, t1)
    if puff:
        wf = lambda t: (w0 + (w1 - w0) * t) + puff * math.sin(min(1, t / 0.9) * math.pi) * 1.0
    else:
        wf = [(0, w0), (1, w1)]
    poly = ribbon(c, wf)
    shapes = list(shapes_extra)
    if folds and t1 > 0.6:
        a = ctx.arms[k]
        el = a['el']
        # 팔꿈치 안쪽 주름 2줄
        dd = c[-1] - c[0]
        nrm = np.array([-dd[1], dd[0]]) / max(1e-6, np.linalg.norm(dd))
        for j, (o, L) in enumerate(((0.0, 2.6), (1.8, 2.0))):
            p = el + nrm * (w0 * 0.12) + (c[-1] - c[0]) / max(1e-6, np.linalg.norm(dd)) * (o - 0.6)
            q = p + nrm * L
            shapes.append((taper(quad(p, (p + q) / 2 + (c[-1] - c[0]) / np.linalg.norm(dd) * 0.6, q, 8), 0.9, 0.3, 0.5),
                           deep(col, 0.8), 0.8))
    ctx.fig(lay, ctx.root_inv(poly) if False else poly, col, shapes=shapes, **({} if sh is None else {'sh': sh}))
    if cuff:
        cw = cuff_w or (w1 + 0.6)
        cc = sub(c, max(0, 1 - cuff_len), 1.0, 8)
        cp = ribbon(cc, cw, cap0=False)
        ribs = []
        dd = cc[-1] - cc[0]
        nrm = np.array([-dd[1], dd[0]]) / max(1e-6, np.linalg.norm(dd))
        for t in np.linspace(0.2, 0.8, 4):
            p = cc[0] + dd * 0.1 + nrm * (t - 0.5) * cw
            ribs.append((taper(np.array([p, p + dd * 0.8]), 0.55, 0.2, 0.2), shade(cuff), 0.8))
        ctx.fig(lay, cp, cuff, shapes=ribs)
    return c


def pant_leg(ctx, k, col, w0=10.0, wk=9.0, w1=9.0, t1=1.0, ext=6.0, hem_drop=1.2, layer=None, shapes_extra=(),
             cuff=None, cuff_len=0.12, folds=True, flare_hem=0.0):
    lay = layer or leg_layer(ctx, k, 'bottom')
    c = leg_line(ctx, k, 26)
    d0 = c[1] - c[0]
    d0 = d0 / np.linalg.norm(d0)
    up = ctx.Tt.lin(np.array([0, -1.0]))
    c = np.concatenate([[c[0] + up * ext], c], 0)
    c = resample(c, 26)
    if t1 >= 1.0:
        d1 = c[-1] - c[-2]
        d1 = d1 / np.linalg.norm(d1)
        c = np.concatenate([c, [c[-1] + d1 * hem_drop]], 0)
        c = resample(c, 26)
    else:
        c = resample(sub(c, 0, t1, 26), 26)
    wf = [(0, w0), (0.5, wk), (1, w1)]
    poly = ribbon(c, wf, cap1=False)
    if flare_hem:
        pass
    shapes = list(shapes_extra)
    if folds and t1 > 0.7:
        kn = ctx.legs[k]['knee']
        dd = c[-1] - c[0]
        dd = dd / np.linalg.norm(dd)
        nrm = np.array([-dd[1], dd[0]])
        for o, L, s in ((-1.0, 3.2, -1), (1.4, 2.4, 1), (6.5, 3.0, -1)):
            p = kn + dd * o + nrm * s * wk * 0.15
            q = p + nrm * s * L + dd * 0.8
            shapes.append((taper(quad(p, (p + q) / 2 - dd * 0.6, q, 8), 0.9, 0.3, 0.5), deep(col, 0.7), 0.75))
    ctx.fig(lay, poly, col, shapes=shapes)
    if cuff:
        cc = sub(c, 1 - cuff_len, 1.0, 8)
        ctx.fig(lay, ribbon(cc, w1 + 0.8, cap0=False, cap1=False), cuff,
                shapes=[(taper(sub(cc, 0.45, 0.55, 4), 0.1, 0, 0), cuff)])
    return c


def fold(c, w=0.9):
    return taper(np.asarray(c, float), w, 0.3, 0.45)


def T(ctx, pts):
    return ctx.Tt(np.asarray(pts, float))
