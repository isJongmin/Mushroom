"""피부(몸, 머리, 팔다리)와 얼굴. 사이클 9 v2: 4.3등신, 정제된 얼굴, 얇은 색선."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, through, quad, bez, rot, shade, light, rgb, mix, sub

SKINS = {'light': '#F8E1D2', 'medium': '#E3B696', 'dark': '#9E6E52'}
SKIN_SH = {'light': '#EEC6B4', 'medium': '#CF9A7C', 'dark': '#865840'}
SKIN_LN = {'light': '#C99582', 'medium': '#A87258', 'dark': '#5E3A28'}


# ------------------------------------------------------------------ 공용 형태
def head_poly(view):
    """머리 로컬 (원점 턱 밑, 높이 54.5). 갸름한 달걀형 + 턱선."""
    if view == 'q':
        pts = [(1, -54.5), (17, -52.5), (26.5, -44.5), (29, -32), (28, -20), (24.5, -10.5), (17, -3.5), (8.5, 0.4),
               (2, 0.4), (-8, -3), (-18, -9.5), (-25.5, -20), (-28.5, -32), (-26.5, -45), (-15, -52.5)]
    else:
        pts = [(0, -54.5), (16.5, -52.5), (26, -45), (28.5, -33), (27.6, -21), (23.5, -11), (15, -3.5), (6, 0.2),
               (0, 0.6), (-6, 0.2), (-15, -3.5), (-23.5, -11), (-27.6, -21), (-28.5, -33), (-26, -45), (-16.5, -52.5)]
    return cr(pts, 8)


def torso_poly(view):
    """몸통 로컬 (높이 25 기준, rig 가 TSX/TSY 로 늘린다). 어깨-허리-골반."""
    if view == 'q':
        pts = [(-7.5, -24.5), (-9.6, -21), (-8.8, -15), (-7.4, -9), (-8.6, -2.5), (-7.2, 2.0), (1, 3.0), (7.5, 1.8),
               (9.0, -2.5), (7.8, -9), (8.8, -15), (10.2, -20.5), (8.5, -24.5), (0.5, -25.6)]
    else:
        pts = [(-9.0, -24.8), (-11.2, -21), (-10.0, -15), (-8.2, -9), (-9.8, -2.5), (-7.6, 2.4), (0, 3.4), (7.6, 2.4),
               (9.8, -2.5), (8.2, -9), (10.0, -15), (11.2, -21), (9.0, -24.8), (0, -25.8)]
    return cr(pts, 7)


def arm_line(ctx, k, n=22):
    a = ctx.arms[k]
    return through(a['sh'], a['el'], a['wr'], n)


def leg_line(ctx, k, n=22):
    g = ctx.legs[k]
    return through(g['hip'], g['knee'], g['ank'], n)


def arm_layer(ctx, k, base):
    """base: 'skin' | 'top'. q 보기 먼 팔(그리고 머리 위로 든 가까운 팔)은 *_far, 나머지는 *_near."""
    if ctx.q and (k == 'F' or (ctx.arms[k]['a'] > 110 and not ctx.prone)):
        return base + '_far'
    return base + '_near'


def leg_layer(ctx, k, base):
    """base: 'skin' | 'bottom' | 'shoes'."""
    if ctx.q and k == 'F':
        return base + '_far'
    return base


ARM_W = [(0, 6.6), (0.45, 5.4), (1, 4.3)]
LEG_W = [(0, 12.0), (0.48, 7.8), (0.66, 8.2), (1, 5.2)]


def hand_pos(ctx, k):
    a = ctx.arms[k]
    return a['wr'] + a['d2'] * 2.6


def draw_hand(ctx, k, col, sh, ln, layer):
    a = ctx.arms[k]
    c = hand_pos(ctx, k)
    d = a['d2']
    ang = math.degrees(math.atan2(d[1], d[0])) - 90
    pts = rot(cr([(-2.4, -2.6), (2.4, -2.6), (2.9, 1.0), (1.6, 3.9), (-1.0, 4.0), (-2.7, 1.2)], 6), ang) + c
    fw = np.array([1.0, 0.0]) if ctx.q else np.array([-1.0 if k == 'N' else 1.0, 0.0])
    if ctx.back:
        fw = -fw
    th = c + fw * 2.3 - d * 0.6
    ctx.fig(layer, rot(ellipse(0, 0, 1.1, 2.0, 14), ang) + th, col, sh=sh, line=ln, lw=0.9)
    ctx.fig(layer, pts, col, sh=sh, line=ln, lw=1.0)


# ------------------------------------------------------------------ 피부
def skin(ctx, tone):
    col, sh, ln = SKINS[tone], SKIN_SH[tone], SKIN_LN[tone]
    v = ctx.view
    for k in ('F', 'N'):
        c = leg_line(ctx, k, 26)
        ctx.fig(leg_layer(ctx, k, 'skin'), ribbon(c, LEG_W), col, sh=sh, line=ln)
    T = ctx.Tt
    nx = 1.5 if ctx.q else 0.0
    neck = cr([(nx - 3.0, -33.5), (nx + 3.0, -33.5), (nx + 3.4, -23, 'c'), (nx - 3.4, -23, 'c')], 4)
    ctx.fig('skin', T(neck), col, sh=sh, line=ln, shapes=[(T(ellipse(nx + 1.0, -29, 2.4, 3.6, 16)), sh, 0.8)])
    ctx.fig('skin', T(torso_poly(v)), col, sh=sh, line=ln,
            shapes=[(T(ellipse(nx, -22.6, 4.4, 1.4, 20)), sh, 0.7)])
    for k in ('F', 'N'):
        lay = arm_layer(ctx, k, 'skin')
        c = arm_line(ctx, k, 24)
        ctx.fig(lay, ribbon(c, ARM_W), col, sh=sh, line=ln)
        draw_hand(ctx, k, col, sh, ln, lay)
    H = ctx.Th
    if not ctx.q:
        for sg in (-1, 1):
            ex = sg * 27.8
            ear = ellipse(ex, -24, 3.6, 6.0, 24)
            ctx.fig('head', H(ear), col, sh=sh, line=ln, shapes=[(H(ellipse(ex + sg * 0.6, -24, 1.6, 3.6, 18)), sh, 0.9)])
    cheek = []
    if not ctx.back:
        fx = 5.0 if ctx.q else 0.0
        cheek = [(H(ellipse(fx, 3.0, 20, 6.5, 30)), sh, 0.5)]
    ctx.fig('head', H(head_poly(v)), col, sh=sh, line=ln, sd=(0.9, 1.0), shapes=cheek)
    if ctx.q:
        ex, ey = -16.5, -23.0
        ctx.fig('head', H(cr([(ex - 2.6, ey - 5.5), (ex + 0.6, ey - 7.0), (ex + 2.8, ey - 3.0), (ex + 2.2, ey + 3.5),
                              (ex - 0.2, ey + 6.4), (ex - 3.0, ey + 3)], 6)), col, sh=sh, line=ln,
                shapes=[(H(cr([(ex - 1.0, ey - 3.6), (ex + 1.2, ey - 4.0), (ex + 1.5, ey + 1.6), (ex - 0.3, ey + 3.4),
                                (ex - 1.5, ey + 0.4)], 5)), sh, 0.95)])


# ------------------------------------------------------------------ 얼굴 (가는 아몬드 눈, 하이라이트 1개)
LASH = '#3A2A2C'
IRIS = '#5B4034'
IRIS_LO = '#9A7458'
PUPIL = '#2C1E1E'
MOUTH = '#B9706F'
BLUSH = '#F2A6A6'
BROW = '#6E5448'


def almond(cx, cy, w, h, outer, lift=0.0):
    """아몬드 눈 외곽: 위는 둥근 활, 아래는 완만. outer = 눈꼬리 방향. lift = 눈꼬리 올림."""
    o = outer
    return cr([(cx - o * w * 0.50, cy + h * 0.10, 'c'), (cx - o * w * 0.30, cy - h * 0.42), (cx + o * w * 0.08, cy - h * 0.55),
               (cx + o * w * 0.40, cy - h * 0.30 - lift), (cx + o * w * 0.52, cy - h * 0.08 - lift, 'c'),
               (cx + o * w * 0.30, cy + h * 0.38), (cx - o * w * 0.10, cy + h * 0.46), (cx - o * w * 0.38, cy + h * 0.34)], 7)


def eye_open(ctx, cx, cy, w, h, outer, look=0.0, half=0.0):
    H = ctx.Th
    sc = almond(cx, cy, w, h, outer, lift=h * 0.12)
    if half > 0:
        lid = cy - h * 0.5 + h * half
        sc = np.array([(x, max(y, lid)) for x, y in sc])
    ix = cx + look + outer * w * 0.02
    iris = ellipse(ix, cy + h * 0.06, w * 0.27, h * 0.56, 26)
    lo = ellipse(ix, cy + h * 0.30, w * 0.20, h * 0.20, 18)
    pup = ellipse(ix, cy + h * 0.04, w * 0.12, h * 0.30, 16)
    hl = ellipse(ix - outer * w * 0.09, cy - h * 0.16, w * 0.075, h * 0.15, 14)
    shapes = [(H(iris), IRIS), (H(lo), IRIS_LO, 0.75), (H(pup), PUPIL),
              (H(ellipse(cx, cy - h * 0.44, w * 0.6, h * 0.22, 20)), '#C8B8C0', 0.5), (H(hl), '#FFFFFF')]
    ctx.fig('face', H(sc), '#FBF8F6', shd=False, noline=True, shapes=shapes)
    top = sc[[i for i in range(len(sc)) if sc[i][1] <= cy + h * 0.12]]
    top = top[np.argsort(top[:, 0])]
    if outer < 0:
        top = top[::-1]
    tip = top[-1] + np.array([outer * w * 0.12, -h * 0.10])
    lash = np.concatenate([top, [tip]], 0)
    lash = cr([tuple(p) for p in lash[::max(1, len(lash) // 7)]] + [tuple(tip)], 5, closed=False)
    ctx.fig('face', H(taper(lash, 2.4, a=0.25, b=0.12, wmin=0.5)), LASH, noline=True, shd=False)
    # 쌍꺼풀 선 (가늘게)
    dl = quad((cx - outer * w * 0.18, cy - h * 0.78), (cx + outer * w * 0.12, cy - h * 0.98), (cx + outer * w * 0.48, cy - h * 0.66), 10)
    ctx.paint('face', H(taper(dl, 0.9, 0.3, 0.3)), '#B58A7E', alpha=0.7)
    lo_l = quad((cx - outer * w * 0.20, cy + h * 0.50), (cx + outer * w * 0.12, cy + h * 0.52), (cx + outer * w * 0.36, cy + h * 0.38), 10)
    ctx.paint('face', H(taper(lo_l, 0.8, 0.3, 0.3)), '#8A6A60', alpha=0.55)


def eye_closed(ctx, cx, cy, w, h, happy=True, outer=1):
    H = ctx.Th
    if happy:
        c = quad((cx - w * 0.48, cy + h * 0.15), (cx, cy - h * 0.55), (cx + w * 0.48, cy + h * 0.15), 16)
    else:
        c = quad((cx - w * 0.5, cy), (cx, cy + h * 0.45), (cx + w * 0.5, cy - h * 0.05 * outer), 16)
    ctx.fig('face', H(taper(c, 2.0, a=0.25, b=0.2, wmin=0.4)), LASH, noline=True, shd=False)


def face(ctx, kind):
    if ctx.back:
        return
    H = ctx.Th
    q = ctx.q
    W, Hh = 13.0, 6.6
    if q:
        E = [(-3.5, -22.0, W * 1.02, Hh, -1), (16.0, -22.0, W * 0.80, Hh * 0.96, 1)]
        fx = 7.0
        bl = [(-11.5, -12.5, 6.0), (21.0, -12.5, 4.4)]
        nose = taper(quad((fx + 2.6, -18.0), (fx + 3.6, -15.0), (fx + 2.2, -13.6), 8), 1.3, 0.3, 0.3)
    else:
        E = [(-12.4, -22.0, W, Hh, -1), (12.4, -22.0, W, Hh, 1)]
        fx = 0.0
        bl = [(-17.5, -12.5, 6.0), (17.5, -12.5, 6.0)]
        nose = taper(quad((0.2, -16.0), (1.0, -14.6), (-0.4, -13.6), 8), 1.2, 0.3, 0.3)
    look = 0.8 if q else 0.0
    for bx, by, r in bl:
        ctx.paint('face', H(ellipse(bx, by, r, r * 0.5, 26)), BLUSH, alpha=0.26 if kind != 'smile' else 0.34)
    for cx, cy, w, h, outer in E:
        bc = quad((cx - outer * w * 0.40, cy - h * 1.75), (cx + outer * w * 0.05, cy - h * 2.15), (cx + outer * w * 0.48, cy - h * 1.85), 10)
        ctx.paint('face', H(taper(bc, 1.5, 0.3, 0.35)), BROW, alpha=0.9)
    ctx.paint('face', H(nose), '#C08A78', alpha=0.85)
    if kind == 'basic':
        for cx, cy, w, h, outer in E:
            eye_open(ctx, cx, cy, w, h, outer, look)
        m = quad((fx - 2.6, -8.0), (fx + 0.2, -6.9), (fx + 2.6, -8.2), 10)
        ctx.paint('face', H(taper(m, 1.4, 0.3, 0.3)), MOUTH, alpha=0.95)
    elif kind == 'smile':
        for cx, cy, w, h, outer in E:
            eye_closed(ctx, cx, cy, w, h, happy=True)
        mo = cr([(fx - 3.4, -9.0, 'c'), (fx + 3.4, -9.0, 'c'), (fx + 2.2, -6.4), (fx, -5.6), (fx - 2.2, -6.4)], 6)
        ctx.fig('face', H(mo), '#A4505A', lw=0.8, shd=False, line='#8A3E48',
                shapes=[(H(cr([(fx - 3.0, -9.0), (fx + 3.0, -9.0), (fx + 2.6, -8.1), (fx - 2.6, -8.1)], 3)), '#FFFFFF', 0.95),
                        (H(ellipse(fx + 0.3, -6.2, 1.8, 0.9, 14)), '#E58A90')])
    elif kind == 'wink':
        cx, cy, w, h, outer = E[0]
        eye_open(ctx, cx, cy, w, h, outer, look)
        cx, cy, w, h, outer = E[1]
        eye_closed(ctx, cx, cy, w, h, happy=False, outer=outer)
        m = quad((fx - 2.8, -8.4), (fx, -6.4), (fx + 2.8, -8.6), 10)
        ctx.paint('face', H(taper(m, 1.5, 0.3, 0.3)), MOUTH, alpha=0.95)
    elif kind == 'sleepy':
        for cx, cy, w, h, outer in E:
            eye_open(ctx, cx, cy + 0.8, w, h * 0.95, outer, look * 0.5, half=0.45)
        ctx.paint('face', H(ellipse(fx, -7.8, 1.4, 1.0, 16)), '#A85A64', alpha=0.9)
