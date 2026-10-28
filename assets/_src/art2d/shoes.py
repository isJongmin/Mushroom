"""신발 7종 + 드롭 2종. 발 로컬 좌표: 원점 = 발목, +x = 발끝, 땅 y = +4.6."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, quad, bez, rot, shade, light, deep, line_of, mix, sub, Xf
from body import leg_line, leg_layer
from cloth import fold
from rig import ANK, SHOE_K

G = ANK


def foot_xf(ctx, k):
    g = ctx.legs[k]
    if ctx.q:
        sa = g['sa']
        k_ = 0.35 if ctx.p['ground'] else 1.0
        r = -sa * k_ + g['f']
        return Xf.T(*g['ank']) @ Xf.R(r) @ Xf.T(0, G) @ Xf.S(SHOE_K) @ Xf.T(0, -G)
    return Xf.T(*g['ank']) @ Xf.T(0, G) @ Xf.S(SHOE_K) @ Xf.T(0, -G)


def socks(ctx, col, t0=0.35, band=None, w=6.6, frill=None):
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 20)
        cc = sub(c, t0, 1.0, 12)
        lay = leg_layer(ctx, k, 'shoes')
        ribs = []
        d = cc[-1] - cc[0]
        d = d / np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        ctx.fig(lay, ribbon(cc, w, cap0=False), col,
                shapes=[(taper(sub(cc, 0.1, 0.9, 6) + n * 1.2, 0.6, 0.2, 0.2), shade(col, 0.6), 0.6)])
        if band:
            bc = sub(cc, 0.0, 0.16, 5)
            ctx.fig(lay, ribbon(bc, w + 0.5, cap0=False, cap1=False), band,
                    shapes=[(taper(np.array([bc[0] + n * x, bc[-1] + n * x]), 0.45, 0.1, 0.1), shade(band), 0.8)
                            for x in (-2, -0.7, 0.7, 2)])
        if frill:
            p = cc[int(len(cc) * 0.55)]
            pts = []
            for i in range(9):
                a = -90 + i * 22.5
                rr = 4.4 if i % 2 == 0 else 3.4
                pts.append((p[0] + n[0] * (i - 4) * 1.2 + d[0] * (1.8 if i % 2 == 0 else 0.4),
                            p[1] + n[1] * (i - 4) * 1.2 + d[1] * (1.8 if i % 2 == 0 else 0.4)))
            fr = ribbon(np.array([p - n * w * 0.62, p + n * w * 0.62]), 3.0, cap0=True, cap1=True)
            ctx.fig(lay, fr, frill, lw=1.2, shapes=[(taper(np.array([p - n * w * 0.5 + d * 0.8, p + n * w * 0.5 + d * 0.8]), 0.5, 0.1, 0.1),
                                                    shade(frill), 0.8)])


def sneaker(ctx, up, sole='#F6F3EE', accent=None, st=1.9, high=0.0, lace='#F6F3EE', toe=None, heel=None,
            extra=None):
    for k in ('F', 'N'):
        X = foot_xf(ctx, k)
        lay = leg_layer(ctx, k, 'shoes')
        stp = G - st
        if ctx.q:
            top = -3.6 - high
            upper = cr([(-4.6, top), (-1.0, top - 0.6), (2.6, -3.4), (6.4, -1.4), (9.3, 0.4), (10.5, stp - 0.6),
                        (10.3, stp + 0.4, 'c'), (-5.4, stp + 0.4, 'c'), (-5.8, stp - 1.8), (-5.5, -1.0)], 6)
            sh = []
            if toe:
                sh.append((cr([(6.4, -1.0), (9.4, 0.5), (10.6, stp), (6.0, stp + 0.5), (5.6, 0.5)], 4), toe, 1.0))
            if accent:
                sh.append((taper(quad((-4.6, stp - 0.6), (1.5, stp - 0.4), (6.5, stp - 3.6), 10), 2.2, 0.15, 0.6), accent, 1.0))
            if heel:
                sh.append((cr([(-5.9, top + 0.4), (-3.4, top - 0.2), (-3.0, stp + 0.4), (-5.9, stp + 0.4)], 3), heel, 1.0))
            sh.append((taper(quad((-5.0, top + 1.6), (-1.5, top + 1.2), (2.0, -2.4), 6), 0.8, 0.2, 0.2), light(up, 0.6), 0.7))
            ctx.fig(lay, X(upper), up, shapes=[(X(s[0]),) + tuple(s[1:]) for s in sh], sd=(0.9, 1.1))
            # 끈
            for i, t in enumerate(np.linspace(0.15, 0.85, 3)):
                p = np.array([0.6, -4.0]) + np.array([5.6, 2.4]) * t
                ctx.fig(lay, X(taper(np.array([p + (-1.0, -0.8), p + (1.0, 0.9)]), 1.1, 0.1, 0.1)), lace, lw=0.8)
            if high:
                ctx.fig(lay, X(cr([(-5.0, top - 0.4, 'c'), (0.8, top - 1.0, 'c'), (1.0, top + 1.6, 'c'), (-5.2, top + 2.0, 'c')], 2)),
                        light(up, 0.15) if up != '#F6F3EE' else '#F2F0F6', lw=1.2)
            sl = cr([(-6.0, stp, 'c'), (11.0, stp, 'c'), (11.0, G - 0.8), (10.2, G, 'c'), (-5.6, G, 'c'), (-6.1, G - 0.7)], 4)
            ctx.fig(lay, X(sl), sole, shapes=[(X(taper(np.array([(-5.2, stp + st * 0.55), (10.4, stp + st * 0.55)]), 0.5, 0.05, 0.05)),
                                               shade(sole, 1.0), 0.9)], sd=(0.6, 0.8))
            if extra:
                extra(ctx, X, lay, 'q')
        else:
            back = ctx.back
            top = -3.8 - high
            upper = cr([(-5.0, top), (0, top - 0.5), (5.0, top), (5.9, -0.2), (6.2, stp + 0.4, 'c'), (-6.2, stp + 0.4, 'c'),
                        (-5.9, -0.2)], 6)
            sh = [(ellipse(0, stp - 2.0, 4.6, 2.6, 18), light(up, 0.35), 0.8)] if not back else []
            if toe and not back:
                sh.append((ellipse(0, stp - 0.5, 5.2, 2.4, 18), toe, 1.0))
            if heel and back:
                sh.append((cr([(-2.2, top), (2.2, top), (2.4, stp + 0.4), (-2.4, stp + 0.4)], 3), heel, 1.0))
            if accent:
                sh.append((taper(quad((-5.6, stp - 0.8), (-5.0, stp - 2.6), (-3.6, stp - 4.0), 6), 1.6, 0.2, 0.4), accent, 1.0))
                sh.append((taper(quad((5.6, stp - 0.8), (5.0, stp - 2.6), (3.6, stp - 4.0), 6), 1.6, 0.2, 0.4), accent, 1.0))
            ctx.fig(lay, X(upper), up, shapes=[(X(s[0]),) + tuple(s[1:]) for s in sh], sd=(0.9, 1.1))
            if not back:
                tongue = cr([(-2.4, top - 0.4), (2.4, top - 0.4), (2.0, -0.6), (-2.0, -0.6)], 3)
                ctx.fig(lay, X(tongue), light(up, 0.15) if up != '#F6F3EE' else '#F0EEF4', lw=1.0,
                        shapes=[(X(taper(np.array([(-2.0, y), (2.0, y)]), 0.9, 0.1, 0.1)), lace, 1.0) for y in (top + 1.2, top + 2.6)])
            if high:
                ctx.fig(lay, X(cr([(-5.4, top - 0.6, 'c'), (5.4, top - 0.6, 'c'), (5.4, top + 1.6, 'c'), (-5.4, top + 1.6, 'c')], 2)),
                        light(up, 0.15) if up != '#F6F3EE' else '#F2F0F6', lw=1.2)
            sl = cr([(-6.6, stp, 'c'), (6.6, stp, 'c'), (6.5, G - 0.5), (5.8, G, 'c'), (-5.8, G, 'c'), (-6.5, G - 0.5)], 3)
            ctx.fig(lay, X(sl), sole, sd=(0.6, 0.8))
            if extra:
                extra(ctx, X, lay, 'back' if back else 'front')


def s_chunky_white(ctx):
    sneaker(ctx, '#F6F3EE', sole='#F4F0EA', accent='#B9AED8', st=3.0, lace='#E8E4F0', heel='#D6CFE8')


def s_sneakers_white(ctx):
    sneaker(ctx, '#F6F3EE', sole='#ECE6DE', accent='#9DB6D3', st=1.8, lace='#E8E4F0')


def s_sneakers_black(ctx):
    sneaker(ctx, '#3A393E', sole='#F6F3EE', accent='#F6F3EE', st=1.8, lace='#F6F3EE')


def s_hightop_black(ctx):
    socks(ctx, '#F6F3EE', t0=0.72, w=6.6)
    sneaker(ctx, '#323036', sole='#F6F3EE', accent='#F6F3EE', st=2.0, high=4.5, lace='#F6F3EE', toe='#F6F3EE')


def loafer(ctx, col, bit='#C9A060', strap=False, heel_h=1.4):
    for k in ('F', 'N'):
        X = foot_xf(ctx, k)
        lay = leg_layer(ctx, k, 'shoes')
        stp = G - heel_h
        if ctx.q:
            up = cr([(-4.6, -1.6), (0.6, -1.4), (4.0, -1.8), (7.6, -0.6), (9.8, 1.0), (10.0, stp, 'c'), (-5.6, stp, 'c'),
                     (-5.8, 0.4)], 6)
            sh = [(taper(quad((-4.0, -1.0), (1.0, -0.4), (5.0, -1.0), 6), 1.0, 0.2, 0.2), light(col, 0.5), 0.8)]
            ctx.fig(lay, X(up), col, shapes=[(X(s[0]),) + tuple(s[1:]) for s in sh], sd=(0.9, 1.1))
            if strap:
                ctx.fig(lay, X(cr([(-0.4, -1.6, 'c'), (1.6, -1.6, 'c'), (1.8, stp - 0.4, 'c'), (-0.2, stp - 0.4, 'c')], 2)), col, lw=1.2)
                ctx.fig(lay, X(ellipse(0.8, 0.6, 0.8, 0.8, 8)), '#E8DCB8', lw=0.8)
            elif bit:
                ctx.fig(lay, X(cr([(3.2, -2.2, 'c'), (6.0, -1.2, 'c'), (5.8, -0.2, 'c'), (3.0, -1.2, 'c')], 2)), bit, lw=0.8,
                        line='#8E6A30')
            sole = cr([(-5.8, stp, 'c'), (10.4, stp, 'c'), (10.2, G, 'c'), (2.0, G, 'c'), (1.6, stp + 0.6), (-1.6, stp + 0.6),
                       (-1.8, G, 'c'), (-5.6, G, 'c')], 3)
            ctx.fig(lay, X(sole), '#4A3A34', lw=1.2, sd=(0.5, 0.6))
        else:
            up = cr([(-5.0, -1.6), (0, -2.2), (5.0, -1.6), (5.8, 0.6), (6.0, stp, 'c'), (-6.0, stp, 'c'), (-5.8, 0.6)], 6)
            sh = [(ellipse(0, stp - 1.8, 4.2, 1.8, 16), light(col, 0.4), 0.8)] if not ctx.back else []
            ctx.fig(lay, X(up), col, shapes=[(X(s[0]),) + tuple(s[1:]) for s in sh], sd=(0.9, 1.1))
            if strap and not ctx.back:
                ctx.fig(lay, X(cr([(-5.6, -0.4, 'c'), (5.6, -0.4, 'c'), (5.6, 1.0, 'c'), (-5.6, 1.0, 'c')], 2)), col, lw=1.1)
                ctx.fig(lay, X(ellipse(3.6, 0.3, 0.8, 0.8, 8)), '#E8DCB8', lw=0.8)
            elif bit and not ctx.back:
                ctx.fig(lay, X(cr([(-2.6, -1.2, 'c'), (2.6, -1.2, 'c'), (2.6, 0.0, 'c'), (-2.6, 0.0, 'c')], 2)), bit, lw=0.8,
                        line='#8E6A30')
            ctx.fig(lay, X(cr([(-6.2, stp, 'c'), (6.2, stp, 'c'), (6.0, G, 'c'), (-6.0, G, 'c')], 2)), '#4A3A34', lw=1.2)


def s_loafer_socks(ctx):
    socks(ctx, '#F6F3EE', t0=0.18, band='#F6F3EE', w=7.0)
    loafer(ctx, '#3A3035')


def s_maryjane_red(ctx):
    socks(ctx, '#F6F3EE', t0=0.78, w=6.4, frill='#F6F3EE')
    loafer(ctx, '#B85A4E', bit=None, strap=True)


def boot(ctx, col, h=9.5, cuff=None, lace=None, extra=None, pointy=0.0):
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 20)
        X = foot_xf(ctx, k)
        lay = leg_layer(ctx, k, 'shoes')
        # 정강이 통
        t0 = 1.0 - h / 15.0
        cc = sub(c, t0, 1.0, 10)
        shaft = ribbon(cc, [(0, 8.4), (1, 7.6)], cap0=False)
        d = cc[-1] - cc[0]
        d = d / np.linalg.norm(d)
        n = np.array([-d[1], d[0]])
        ctx.fig(lay, shaft, col, shapes=[(taper(sub(cc, 0.2, 0.9, 5) - n * 1.5, 1.0, 0.2, 0.3), light(col, 0.5), 0.8)])
        if ctx.q:
            up = cr([(-4.8, -3.0), (2.4, -3.2), (6.8, -1.2), (9.6 + pointy, 0.6 - pointy * 0.4), (10.2 + pointy, 2.6),
                     (10.0 + pointy, 3.0, 'c'), (-5.6, 3.0, 'c'), (-5.8, -0.4)], 6)
            ctx.fig(lay, X(up), col, shapes=[(X(taper(quad((-3, -2.0), (2, -2.0), (6, -0.6), 6), 1.0, 0.2, 0.3)), light(col, 0.5), 0.8)],
                    sd=(0.9, 1.1))
            ctx.fig(lay, X(cr([(-6.0, 2.8, 'c'), (10.6 + pointy, 2.8, 'c'), (10.4 + pointy, G, 'c'), (-5.8, G, 'c')], 2)),
                    deep(col, 1.3), lw=1.2, sd=(0.5, 0.6))
        else:
            up = cr([(-5.2, -3.0), (5.2, -3.0), (6.0, 0.4), (6.2, 3.0, 'c'), (-6.2, 3.0, 'c'), (-6.0, 0.4)], 6)
            ctx.fig(lay, X(up), col, shapes=[(X(ellipse(0, 0.6, 4.0, 1.8, 14)), light(col, 0.4), 0.7)] if not ctx.back else [],
                    sd=(0.9, 1.1))
            ctx.fig(lay, X(cr([(-6.6, 2.8, 'c'), (6.6, 2.8, 'c'), (6.4, G, 'c'), (-6.4, G, 'c')], 2)), deep(col, 1.3), lw=1.2)
        if lace and not ctx.back:
            for t in (0.3, 0.55, 0.8):
                p = sub(cc, t, t + 0.01, 2)[0] + n * (1.0 if ctx.q else 0)
                ctx.fig(lay, taper(np.array([p - n * 1.6 - d * 0.6, p + n * 1.6 + d * 0.6]), 0.9, 0.1, 0.1), lace, lw=0.7)
        if cuff:
            bc = sub(cc, 0.0, 0.2, 5)
            ctx.fig(lay, ribbon(bc, 9.4, cap0=False, cap1=False), cuff,
                    shapes=[(taper(np.array([bc[0] + n * x, bc[-1] + n * x]), 0.5, 0.1, 0.1), shade(cuff), 0.7)
                            for x in (-2.5, -0.8, 0.8, 2.5)])
        if extra:
            extra(ctx, X, lay, cc, n, d)


def s_boots_brown(ctx):
    boot(ctx, '#8E6A4E', h=9.0, cuff='#ECE0CC', lace='#D9C29A')


# ------------------------------------------------------------------ 드롭
def s_snail_boots(ctx):
    """파란 달팽이 부츠: 발목에 소용돌이 껍질, 발끝에 눈 더듬이."""
    shell, body_c = '#8FAFCB', '#C5D6AE'

    def ex(ctx, X, lay, cc, n, d):
        p = cc[int(len(cc) * 0.45)]
        side = 1.0 if ctx.q else 0.0
        cp = p - n * (1.0 + side)
        sp = []
        for i in range(30):
            a = math.radians(i * 22)
            r = 3.6 * (1 - i / 34)
            sp.append(cp + np.array([math.cos(a), math.sin(a)]) * r)
        ctx.fig(lay, ellipse(cp[0], cp[1], 4.0, 3.8, 24), shell,
                shapes=[(taper(np.array(sp), 0.9, 0.05, 0.4), deep(shell), 0.9),
                        (ellipse(cp[0] - 1.4, cp[1] - 1.6, 1.1, 0.8, 10), light(shell, 1.0), 0.9)])
        if ctx.q:
            for dx, L in ((6.0, 5.0), (8.0, 4.4)):
                a = X(np.array([[dx, -0.8]]))[0]
                b = X(np.array([[dx + 1.2, -0.8 - L]]))[0]
                ctx.fig(lay, ribbon(np.array([a, b]), 0.9), body_c, lw=0.8)
                ctx.fig(lay, ellipse(b[0], b[1], 1.0, 1.0, 10), body_c, lw=0.8,
                        shapes=[(ellipse(b[0] + 0.2, b[1], 0.45, 0.5, 8), '#1E2A20')])
    boot(ctx, body_c, h=7.5, extra=ex)


def s_bat_boots(ctx):
    col = '#4E485C'

    def ex(ctx, X, lay, cc, n, d):
        p = cc[2]
        for s in ((-1, 1) if not ctx.q else (-1,)):
            base = p + n * s * 3.6
            tip = base + n * s * 6.0 - d * 3.0
            mid = base + n * s * 3.4 + d * 1.2
            wing = cr([tuple(base - d * 1.4), tuple(tip) + ('c',), tuple(base + n * s * 4.6 + d * 0.8), tuple(mid) + ('c',),
                       tuple(base + n * s * 1.6 + d * 2.4), tuple(base + d * 1.6)], 3)
            ctx.fig(lay, wing, '#3A3546', lw=1.1, shapes=[(fold(np.array([base, tip]), 0.6), '#857C98', 0.9)])
        ctx.fig(lay, ellipse(p[0] + d[0] * 2, p[1] + d[1] * 2, 1.2, 1.2, 10), '#B85A5A', lw=0.8, line='#7A3A3A')
    boot(ctx, col, h=8.5, extra=ex, pointy=2.0)


SHOES = {
    'chunky-white': s_chunky_white, 'loafer-socks': s_loafer_socks, 'hightop-black': s_hightop_black,
    'sneakers-white': s_sneakers_white, 'maryjane-red': s_maryjane_red, 'boots-brown': s_boots_brown,
    'sneakers-black': s_sneakers_black,
    'snail-boots': s_snail_boots, 'bat-boots': s_bat_boots,
}
