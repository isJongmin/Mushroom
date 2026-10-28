"""피부(몸, 머리, 팔다리)와 얼굴."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, through, quad, bez, rot, shade, light, rgb, mix, sub

SKINS = {'light': '#FDDDC8', 'medium': '#EBB48E', 'dark': '#A86C4E'}
SKIN_SH = {'light': '#F3B9A6', 'medium': '#D68E70', 'dark': '#86503A'}
SKIN_LN = {'light': '#B9705E', 'medium': '#9A5440', 'dark': '#55301F'}


# ------------------------------------------------------------------ 공용 형태
def head_poly(view):
    if view == 'q':
        pts = [(2, -54.5), (18, -52.5), (27.5, -45), (30, -32), (29.2, -19), (25, -8.5), (16.5, -1.5), (5, 0.6),
               (-7, -1.5), (-18.5, -7.5), (-27, -18.5), (-30, -32), (-27.5, -45), (-15, -52.5)]
    else:
        pts = [(0, -54.5), (17, -52.5), (27, -45.5), (30, -33), (29.3, -20), (24.5, -9), (14.5, -2), (0, 0.6),
               (-14.5, -2), (-24.5, -9), (-29.3, -20), (-30, -33), (-27, -45.5), (-17, -52.5)]
    return cr(pts, 8)


def torso_poly(view):
    if view == 'q':
        pts = [(-8.5, -25), (-10.2, -20), (-9.4, -11), (-9.8, -3), (-7.0, 2.2), (1, 3.4), (8.0, 1.8), (10.0, -3),
               (9.4, -11), (10.6, -19.5), (9, -25), (0.5, -26.5)]
    else:
        pts = [(-10.5, -25.5), (-12.2, -20.5), (-10.6, -11), (-11.2, -3), (-7.5, 2.5), (0, 3.6), (7.5, 2.5), (11.2, -3),
               (10.6, -11), (12.2, -20.5), (10.5, -25.5), (0, -26.8)]
    return cr(pts, 7)


def arm_line(ctx, k, n=22):
    a = ctx.arms[k]
    return through(a['sh'], a['el'], a['wr'], n)


def leg_line(ctx, k, n=22):
    g = ctx.legs[k]
    return through(g['hip'], g['knee'], g['ank'], n)


def arm_layer(ctx, k, base):
    """base: 'skin' | 'top'. q 보기 먼 팔은 *_far, 나머지는 *_near."""
    if ctx.q and k == 'F':
        return base + '_far'
    return base + '_near'


def leg_layer(ctx, k, base):
    """base: 'skin' | 'bottom' | 'shoes'."""
    if ctx.q and k == 'F':
        return base + '_far'
    return base


def hand_pos(ctx, k):
    a = ctx.arms[k]
    return a['wr'] + a['d2'] * 1.6


def draw_hand(ctx, k, col, sh, ln, layer):
    a = ctx.arms[k]
    c = hand_pos(ctx, k)
    d = a['d2']
    ang = math.degrees(math.atan2(d[1], d[0])) - 90
    pts = rot(ellipse(0, 0, 3.7, 4.0, 28), ang) + c
    # 엄지: 진행 방향(앞) 쪽 작은 혹
    fw = np.array([1.0, 0.0]) if ctx.q else np.array([-1.0 if k == 'N' else 1.0, 0.0])
    if ctx.back:
        fw = -fw
    th = c + fw * 3.0 + d * -0.6
    ctx.fig(layer, ellipse(th[0], th[1], 1.7, 1.9, 16), col, sh=sh, line=ln, lw=1.6)
    ctx.fig(layer, pts, col, sh=sh, line=ln)


# ------------------------------------------------------------------ 피부
def skin(ctx, tone):
    col, sh, ln = SKINS[tone], SKIN_SH[tone], SKIN_LN[tone]
    v = ctx.view
    # 다리
    for k in ('F', 'N'):
        c = leg_line(ctx, k)
        ctx.fig(leg_layer(ctx, k, 'skin'), ribbon(c, [(0, 8.4), (0.5, 7.0), (1, 5.6)]), col, sh=sh, line=ln)
    # 몸통 + 목
    T = ctx.Tt
    nx = 1.5 if ctx.q else 0.0
    neck = cr([(nx - 3.6, -31), (nx + 3.6, -31), (nx + 3.8, -23, 'c'), (nx - 3.8, -23, 'c')], 4)
    ctx.fig('skin', T(neck), col, sh=sh, line=ln)
    ctx.fig('skin', T(torso_poly(v)), col, sh=sh, line=ln,
            shapes=[(T(ellipse(nx, -22, 5, 2.4, 20)), sh, 0.8)])
    # 팔
    for k in ('F', 'N'):
        lay = arm_layer(ctx, k, 'skin')
        c = arm_line(ctx, k)
        ctx.fig(lay, ribbon(c, [(0, 5.8), (1, 4.6)]), col, sh=sh, line=ln)
        draw_hand(ctx, k, col, sh, ln, lay)
    # 머리
    H = ctx.Th
    if not ctx.q:
        for sg in (-1, 1):
            ex = sg * 29.0
            ear = ellipse(ex, -23, 4.2, 5.6, 24)
            ctx.fig('head', H(ear), col, sh=sh, line=ln,
                    shapes=[(H(ellipse(ex + sg * 0.6, -23, 2.0, 3.4, 18)), sh, 0.9)])
    hp = head_poly(v)
    cheek = []
    if not ctx.back:
        # 얼굴 아래 그늘(목에 닿는 턱선 쪽) + 볼 아래 살짝
        fx = 5.0 if ctx.q else 0.0
        cheek = [(H(ellipse(fx, 4.0, 22, 7.5, 30)), sh, 0.55)]
    ctx.fig('head', H(hp), col, sh=sh, line=ln, sd=(1.3, 1.5), shapes=cheek)
    if ctx.q:
        ex, ey = -19.0, -21.0
        ctx.fig('head', H(cr([(ex - 3.2, ey - 4.5), (ex + 0.6, ey - 6.2), (ex + 3.4, ey - 2.5), (ex + 2.6, ey + 3.5),
                              (ex - 0.2, ey + 6.0), (ex - 3.6, ey + 3)], 6)), col, sh=sh, line=ln,
                shapes=[(H(cr([(ex - 1.3, ey - 3.0), (ex + 1.4, ey - 3.6), (ex + 1.8, ey + 1.6), (ex - 0.4, ey + 3.4),
                                (ex - 1.8, ey + 0.4)], 5)), sh, 0.95)])


# ------------------------------------------------------------------ 얼굴
LASH = '#2A1820'
IRIS = '#5A3326'
IRIS_LO = '#B8784A'
PUPIL = '#24121A'
MOUTH = '#B5485E'
BLUSH = '#FF9AAE'


def eye_shape(cx, cy, w, h):
    return cr([(cx - w * 0.50, cy - h * 0.05), (cx - w * 0.40, cy - h * 0.40), (cx - w * 0.05, cy - h * 0.52),
               (cx + w * 0.38, cy - h * 0.43), (cx + w * 0.50, cy - h * 0.08), (cx + w * 0.42, cy + h * 0.34),
               (cx, cy + h * 0.50), (cx - w * 0.42, cy + h * 0.34)], 7)


def eye_open(ctx, cx, cy, w, h, outer, look=0.0, half=0.0):
    """outer: 바깥 눈꼬리 방향(-1 왼쪽, +1 오른쪽). half: 졸린 눈 (윗 눈꺼풀 내림 0..1)."""
    H = ctx.Th
    sc = eye_shape(cx, cy, w, h)
    if half > 0:
        lid = cy - h * 0.5 + h * half
        sc = np.array([(x, max(y, lid + (abs(x - cx) / w) * 1.2)) for x, y in sc])
    ix = cx + look
    iris = ellipse(ix, cy + h * 0.04, w * 0.40, h * 0.46, 30)
    lo = ellipse(ix, cy + h * 0.30, w * 0.34, h * 0.20, 24)
    pup = ellipse(ix, cy + h * 0.02, w * 0.20, h * 0.25, 20)
    top_dark = ellipse(ix, cy - h * 0.30, w * 0.44, h * 0.22, 20)
    hl1 = rot(ellipse(0, 0, w * 0.17, h * 0.15, 20), -20) + (ix - outer * w * 0.14, cy - h * 0.16)
    hl2 = ellipse(ix + outer * w * 0.16, cy + h * 0.24, w * 0.08, h * 0.07, 14)
    hl3 = ellipse(ix - outer * w * 0.18, cy + h * 0.20, w * 0.05, h * 0.045, 12)
    shapes = [(H(iris), IRIS), (H(lo), IRIS_LO, 0.85), (H(top_dark), PUPIL, 0.7), (H(pup), PUPIL),
              (H(ellipse(cx, cy - h * 0.40, w * 0.55, h * 0.16, 20)), '#C9B8D8', 0.55),
              (H(hl1), '#FFFFFF'), (H(hl2), '#FFFFFF', 0.95), (H(hl3), '#FFFFFF', 0.7)]
    ctx.fig('face', H(sc), '#FFFFFF', shd=False, noline=True, shapes=shapes)
    # 윗 속눈썹 (두꺼운 선, 바깥 꼬리 튕김)
    top = sc[[i for i in range(len(sc)) if sc[i][1] <= cy + h * 0.02]]
    top = top[np.argsort(top[:, 0])]
    if outer < 0:
        top = top[::-1]
    # top: 안쪽 -> 바깥쪽
    tip = top[-1] + np.array([outer * w * 0.22, -h * 0.10])
    lash = np.concatenate([top, [tip]], 0)
    lash = cr([tuple(p) for p in lash[::max(1, len(lash) // 7)]] + [tuple(tip)], 5, closed=False)
    ctx.fig('face', H(taper(lash, 2.3 if half == 0 else 1.9, a=0.18, b=0.10, wmin=0.4)), LASH, noline=True, shd=False)
    # 아래 속눈썹 (짧게)
    lo_l = np.array([(cx + outer * w * 0.40, cy + h * 0.22), (cx + outer * w * 0.28, cy + h * 0.40),
                     (cx + outer * w * 0.10, cy + h * 0.48)])
    ctx.fig('face', H(taper(quad(*lo_l, n=10), 0.9, a=0.3, b=0.4)), LASH, noline=True, shd=False, alpha=0.8)


def eye_closed(ctx, cx, cy, w, h, happy=True):
    H = ctx.Th
    if happy:
        c = quad((cx - w * 0.48, cy + h * 0.12), (cx, cy - h * 0.55), (cx + w * 0.48, cy + h * 0.12), 16)
    else:
        c = quad((cx - w * 0.48, cy + h * 0.0), (cx, cy + h * 0.30), (cx + w * 0.48, cy + h * 0.0), 16)
    ctx.fig('face', H(taper(c, 2.2, a=0.2, b=0.2, wmin=0.5)), LASH, noline=True, shd=False)


def wink_eye(ctx, cx, cy, w, h, outer):
    H = ctx.Th
    # '>' 모양 (바깥 쪽이 뾰족)
    a = (cx - outer * w * 0.45, cy - h * 0.30)
    b = (cx + outer * w * 0.40, cy + h * 0.02)
    c = (cx - outer * w * 0.45, cy + h * 0.30)
    l1 = quad(a, (cx, cy - h * 0.05), b, 10)
    l2 = quad(b, (cx, cy + h * 0.05), c, 10)
    ctx.fig('face', H(taper(np.concatenate([l1, l2[1:]]), 2.1, a=0.15, b=0.15, wmin=0.6)), LASH, noline=True,
            shd=False)


def face(ctx, kind):
    if ctx.back:
        return
    H = ctx.Th
    q = ctx.q
    if q:
        E = [(-3.0, -20.5, 12.0, 15.2, -1), (16.6, -20.5, 9.6, 14.6, 1)]
        fx = 6.5
        bl = [(-13.0, -11.5, 5.4), (22.5, -11.5, 4.2)]
    else:
        E = [(-12.8, -20.5, 12.2, 15.2, -1), (12.8, -20.5, 12.2, 15.2, 1)]
        fx = 0.0
        bl = [(-19.5, -11.5, 5.4), (19.5, -11.5, 5.4)]
    look = 1.1 if q else 0.0
    # 볼터치 + 빗금
    for bx, by, r in bl:
        ctx.paint('face', H(ellipse(bx, by, r, r * 0.55, 26)), BLUSH, alpha=0.55 if kind != 'smile' else 0.7)
        for j in (-1, 0, 1):
            x = bx + j * r * 0.42
            ctx.paint('face', H(taper(np.array([(x + 0.9, by - 1.3), (x - 0.9, by + 1.3)]), 0.7, 0.3, 0.3)),
                      '#F06D8A', alpha=0.75)
    # 눈썹 (앞머리가 가리면 안 보인다)
    for cx, cy, w, h, outer in E:
        bc = quad((cx - w * 0.42, cy - h * 0.86), (cx, cy - h * 1.02), (cx + w * 0.42, cy - h * 0.86), 10)
        ctx.paint('face', H(taper(bc, 1.3, 0.3, 0.3)), '#6B4034', alpha=0.85)
    if kind == 'basic':
        for cx, cy, w, h, outer in E:
            eye_open(ctx, cx, cy, w, h, outer, look)
        m = quad((fx - 2.2, -8.9), (fx, -7.4), (fx + 2.2, -8.9), 10)
        ctx.fig('face', H(taper(m, 1.15, 0.25, 0.25, 0.4)), MOUTH, noline=True, shd=False)
    elif kind == 'smile':
        for cx, cy, w, h, outer in E:
            eye_closed(ctx, cx, cy, w, h, happy=True)
        mo = cr([(fx - 3.6, -10.0, 'c'), (fx + 3.6, -10.0, 'c'), (fx + 2.6, -7.2), (fx, -5.6), (fx - 2.6, -7.2)], 6)
        tongue = ellipse(fx + 0.3, -6.6, 2.3, 1.4, 18)
        ctx.fig('face', H(mo), '#8E2E44', lw=1.3, shd=False, line='#6E1F33', shapes=[(H(tongue), '#F27A8E')])
    elif kind == 'wink':
        cx, cy, w, h, outer = E[0]
        eye_open(ctx, cx, cy, w, h, outer, look)
        cx, cy, w, h, outer = E[1]
        wink_eye(ctx, cx, cy, w, h, outer)
        mo = cr([(fx - 2.6, -9.6, 'c'), (fx + 2.6, -9.6, 'c'), (fx + 1.8, -7.4), (fx, -6.6), (fx - 1.8, -7.4)], 6)
        ctx.fig('face', H(mo), '#8E2E44', lw=1.2, shd=False, line='#6E1F33',
                shapes=[(H(ellipse(fx + 0.2, -7.0, 1.6, 1.0, 14)), '#F27A8E')])
        # 반짝 별
        sx, sy = (E[1][0] + 7.5, E[1][1] - 8.5)
        star = [(sx + math.cos(math.radians(a)) * (2.6 if i % 2 == 0 else 0.9),
                 sy + math.sin(math.radians(a)) * (2.6 if i % 2 == 0 else 0.9)) for i, a in enumerate(range(-90, 270, 45))]
        ctx.fig('face', H(np.array(star)), '#FFE36A', lw=0.9, line='#E0A020', shd=False)
    elif kind == 'sleepy':
        for cx, cy, w, h, outer in E:
            eye_open(ctx, cx, cy + 1.0, w, h * 0.92, outer, look * 0.5, half=0.42)
        mo = ellipse(fx, -8.3, 1.5, 1.2, 16)
        ctx.fig('face', H(mo), '#9A3A50', lw=1.0, shd=False, line='#6E1F33')
