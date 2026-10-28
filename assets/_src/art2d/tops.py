"""상의 10종 + 드롭 3종. 몸통 로컬 좌표(원점 엉덩이 가운데, 어깨 y≈-23, 목 y≈-27)."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, through, quad, bez, rot, shade, light, deep, line_of, rgb, mix, sub
from cloth import body_poly, hem_band, sleeve, cxo, fold, T
from body import arm_layer, arm_line, hand_pos


def _ribs(ctx, x0, x1, y0, y1, n, col, w=0.55):
    out = []
    for x in np.linspace(x0, x1, n):
        out.append((T(ctx, taper(np.array([(x, y0), (x, y1)]), w, 0.15, 0.15)), shade(col), 0.85))
    return out


def body_folds(ctx, col, hem, strength=1.0):
    """옆구리/밑단 주름."""
    c = cxo(ctx)
    k = deep(col, 0.8)
    out = []
    for p, q, m in (((-10, -18), (-6, -14), (-8, -15)), ((11, -18), (7, -14.5), (9, -15.5)),
                    ((-8, hem - 3.5), (-5, hem - 9), (-6.0, hem - 6)), ((7, hem - 3.5), (4.5, hem - 8), (5.2, hem - 6)),
                    ((c - 1.0, hem - 3.5), (c - 0.5, hem - 7.5), (c - 1.2, hem - 5.5))):
        if ctx.q:
            p = (p[0] * 0.92 + 1, p[1]); q = (q[0] * 0.92 + 1, q[1]); m = (m[0] * 0.92 + 1, m[1])
        out.append((T(ctx, fold(quad(p, m, q, 8), 0.95)), k, 0.7 * strength))
    return out


def both_sleeves(ctx, col, **kw):
    for k in ('F', 'N'):
        sleeve(ctx, k, col, **kw)


# ------------------------------------------------------------------ 후드티
def hood_shape(ctx, col, layer='top'):
    if ctx.front:
        pts = [(-13, -23), (-12, -30), (-6, -33.5), (6, -33.5), (12, -30), (13, -23), (7, -25.5), (0, -24.5),
               (-7, -25.5)]
        inner = cr([(-8, -27), (0, -29.5), (8, -27), (0, -25.5)], 6)
        ctx.fig(layer, T(ctx, cr(pts, 6)), col, shapes=[(T(ctx, inner), shade(col, 1.6), 0.9)])
    elif ctx.q:
        pts = [(-13.5, -21), (-15.0, -28), (-10, -33.5), (-2, -33), (4, -28), (-1, -24), (-7, -22.5)]
        ctx.fig(layer, T(ctx, cr(pts, 6)), col,
                shapes=[(T(ctx, fold(quad((-12, -24), (-11, -29), (-6, -31), 8), 1.0)), deep(col), 0.7)])
    else:
        pts = [(-11, -28), (-5, -30), (5, -30), (11, -28), (11, -20), (7, -12.5), (0, -10), (-7, -12.5), (-11, -20)]
        ctx.fig(layer, T(ctx, cr(pts, 6)), col,
                shapes=[(T(ctx, fold(quad((0, -28), (0.6, -20), (0, -12), 8), 1.0)), deep(col), 0.8),
                        (T(ctx, fold(quad((-8, -25), (-6, -18), (-2, -13), 8), 0.9)), deep(col, 0.8), 0.6),
                        (T(ctx, fold(quad((8, -25), (6, -18), (2, -13), 8), 0.9)), deep(col, 0.8), 0.6)])


def hoodie(ctx, col, cord='#FFFFFF', patch=None, hem=5.5, sleeve_col=None):
    c = cxo(ctx)
    if not ctx.back:
        hood_shape(ctx, col)
    poly = body_poly(ctx, hem=hem, loose=1.2, flare=1.03)
    ctx.fig('top', T(ctx, poly), col, shapes=body_folds(ctx, col, hem - 2.5))
    ctx.fig('top', T(ctx, hem_band(ctx, hem - 3.2, hem, 1.03, 1.2)), col,
            shapes=_ribs(ctx, -13, 13, hem - 2.8, hem - 0.4, 14, col))
    if ctx.back:
        hood_shape(ctx, col)
    else:
        # 캥거루 주머니
        px = c + (1.5 if ctx.q else 0)
        pk = cr([(px - 7.5, -10.5), (px + 7.5, -10.5), (px + 9.5, hem - 3.4, 'c'), (px - 9.5, hem - 3.4, 'c')], 5)
        ctx.fig('top', T(ctx, pk), col, lw=1.6,
                shapes=[(T(ctx, cr([(px - 9.5, hem - 3.4), (px - 7.5, -10.5), (px - 5.8, -7), (px - 6.8, hem - 3.6)], 4)),
                         shade(col), 0.9),
                        (T(ctx, cr([(px + 9.5, hem - 3.4), (px + 7.5, -10.5), (px + 5.8, -7), (px + 6.8, hem - 3.6)], 4)),
                         shade(col), 0.9)])
        # 끈
        for sx in (-1, 1):
            x = c + sx * 2.4 + (0.8 if ctx.q and sx > 0 else 0)
            s = quad((x, -25.5), (x + sx * 0.4, -21), (x + sx * 0.2 + ctx.sway * 0.4, -16.5), 8)
            ctx.fig('top', T(ctx, ribbon(s, 1.0)), cord, lw=1.2)
            e = s[-1]
            ctx.fig('top', T(ctx, ellipse(e[0], e[1] + 0.8, 0.9, 1.4, 12)), mix(cord, '#B0A8B8', 0.3), lw=1.1)
        if patch:
            patch(ctx)
    for k in ('F', 'N'):
        sleeve(ctx, k, sleeve_col or col, w0=9.2, w1=8.2, t1=0.93, cuff=sleeve_col or col, cuff_len=0.18)


def patch_smile(ctx):
    c = cxo(ctx)
    x, y = c - 6.5, -19
    if ctx.q:
        x = c - 3.5
    sq = cr([(x - 2.2, y - 2.2, 'c'), (x + 2.2, y - 2.2, 'c'), (x + 2.2, y + 2.2, 'c'), (x - 2.2, y + 2.2, 'c')], 3)
    ctx.fig('top', T(ctx, sq), '#E4DAFB', lw=1.2, line='#7B66B8',
            shapes=[(T(ctx, ellipse(x - 0.9, y - 0.5, 0.35, 0.5, 8)), '#7B66B8'),
                    (T(ctx, ellipse(x + 0.9, y - 0.5, 0.35, 0.5, 8)), '#7B66B8'),
                    (T(ctx, taper(quad((x - 1.1, y + 0.7), (x, y + 1.6), (x + 1.1, y + 0.7), 6), 0.45, 0.2, 0.2)),
                     '#7B66B8')])


def t_hoodie_lavender(ctx):
    hoodie(ctx, '#C3AEF0', '#FFFFFF', patch=patch_smile, hem=6.0)


def t_hoodie_black(ctx):
    hoodie(ctx, '#45404F', '#D8D2DE', hem=5.0)


def t_hoodie_white(ctx):
    hoodie(ctx, '#F7F2EA', '#B8AFA4', hem=5.0)


# ------------------------------------------------------------------ 가디건 + 숄더백
def t_cardigan_cream(ctx):
    cr_ = '#F1E3C6'
    tee = '#FFFFFF'
    c = cxo(ctx)
    hem = 3.0
    if ctx.back:
        ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, loose=0.6)), cr_,
                shapes=_ribs(ctx, -11, 11, -24, hem - 3, 9, cr_, 0.4) + body_folds(ctx, cr_, hem))
        ctx.fig('top', T(ctx, hem_band(ctx, hem - 3, hem, 1, 0.6)), cr_, shapes=_ribs(ctx, -12, 12, hem - 2.6, hem - 0.4, 14, cr_))
    else:
        # 안쪽 흰 티
        ctx.fig('top', T(ctx, body_poly(ctx, hem=hem - 1.0, neck='crew')), tee)
        # 리본 프린트
        bx, by = c, -18
        for sx in (-1, 1):
            ctx.fig('top', T(ctx, cr([(bx, by), (bx + sx * 2.6, by - 1.6), (bx + sx * 2.8, by + 1.4)], 5)), '#F59AC0',
                    lw=0.9, line='#C24E80')
        ctx.fig('top', T(ctx, ellipse(bx, by, 0.9, 0.9, 10)), '#E0628E', lw=0.8, line='#A83A66')
        # 가디건 앞판 두 쪽 (가운데가 열림)
        gap = 3.6
        for sx in (-1, 1):
            if ctx.q:
                x_in = c + sx * (gap if sx > 0 else gap + 0.5)
            else:
                x_in = c + sx * gap
            x_sh = (-9.0 if sx < 0 else 10.0) if ctx.q else sx * 11.0
            x_out = (-11.3 - 0.6 if sx < 0 else 11.8 + 0.6) if ctx.q else sx * 13.2
            pts = [(x_sh, -25.5), (c + sx * 4.6, -27.0), (x_in + sx * 0.2, -14, 'c'), (x_in, hem, 'c'),
                   (x_out, hem, 'c'), (x_out + sx * 0.2, -2), (x_out - sx * 0.4, -12), (x_out + sx * 0.6, -21)]
            if sx > 0:
                pts = pts[::-1]
            ribs = _ribs(ctx, min(x_in, x_out) + 1.5, max(x_in, x_out) - 1.5, -22, hem - 3, 3, cr_, 0.45)
            ctx.fig('top', T(ctx, cr(pts, 6)), cr_, shapes=ribs + body_folds(ctx, cr_, hem, 0.6))
            # 단추 3개
            for y in (-17, -11, -5):
                bxp = x_in + sx * 1.6
                ctx.fig('top', T(ctx, ellipse(bxp, y, 0.95, 0.95, 10)), '#D9B97E', lw=0.9, line='#8E6A30')
            ctx.fig('top', T(ctx, cr([(x_in, hem - 3, 'c'), (x_out, hem - 3, 'c'), (x_out, hem, 'c'), (x_in, hem, 'c')], 2)),
                    cr_, lw=1.4, shapes=_ribs(ctx, min(x_in, x_out) + 0.6, max(x_in, x_out) - 0.6, hem - 2.6, hem - 0.4,
                                              5, cr_))
    for k in ('F', 'N'):
        sleeve(ctx, k, cr_, w0=8.2, w1=7.4, t1=0.94, cuff=cr_, cuff_len=0.2)
    shoulder_bag(ctx, '#2C2834', strap_from='N')


def shoulder_bag(ctx, col, strap_from='N'):
    """한쪽 어깨에 멘 작은 가방 (금색 잠금)."""
    gold = '#E3B04B'
    if ctx.front:
        s0, b = (8.5, -25.5), (13.5, -2.5)
        lay = 'top_near'
    elif ctx.back:
        s0, b = (-8.5, -25.5), (-13.5, -2.5)
        lay = 'top_near'
    else:
        s0, b = (-6.5, -25.5), (-10.5, -1.5)
        lay = 'top'
    strap = quad(s0, ((s0[0] + b[0]) / 2 + 1.0, (s0[1] + b[1]) / 2), (b[0], b[1] - 4), 10)
    ctx.fig(lay, T(ctx, ribbon(strap, 1.3)), col, lw=1.2)
    bw, bh = 5.0, 4.4
    x, y = b[0] + ctx.sway * 0.4, b[1]
    bag = cr([(x - bw, y - bh + 0.6), (x - bw + 0.8, y - bh, 'c'), (x + bw - 0.8, y - bh, 'c'), (x + bw, y - bh + 0.6),
              (x + bw, y + bh - 1.4), (x + bw - 1.4, y + bh, 'c'), (x - bw + 1.4, y + bh, 'c'), (x - bw, y + bh - 1.4)], 3)
    flap = cr([(x - bw, y - bh + 0.4), (x + bw, y - bh + 0.4), (x + bw - 0.4, y + 0.5), (x, y + 1.6), (x - bw + 0.4, y + 0.5)], 4)
    if ctx.back:
        ctx.fig(lay, T(ctx, bag), col)
        return
    ctx.fig(lay, T(ctx, bag), col, shapes=[(T(ctx, flap), light(col, 0.35))])
    ctx.fig(lay, T(ctx, flap), light(col, 0.25), lw=1.2, shd=False,
            shapes=[(T(ctx, taper(np.array([(x - bw + 1, y - bh + 1.2), (x + bw - 1, y - bh + 1.2)]), 0.5, 0.1, 0.1)),
                     light(col, 0.7), 0.6)])
    ctx.fig(lay, T(ctx, cr([(x - 1.4, y + 0.6, 'c'), (x + 1.4, y + 0.6, 'c'), (x + 1.4, y + 2.0, 'c'),
                            (x - 1.4, y + 2.0, 'c')], 2)), gold, lw=0.9, line='#8E6A30')


# ------------------------------------------------------------------ 바시티 재킷
def letter_R(ctx, x, y, s, col):
    st = [((x - s * 0.5, y + s), (x - s * 0.5, y - s)), ]
    bowl = quad((x - s * 0.5, y - s), (x + s * 1.2, y - s * 0.55), (x - s * 0.5, y + s * 0.05), 10)
    leg = np.array([(x - s * 0.2, y), (x + s * 0.7, y + s)])
    return [taper(np.array(st[0]), s * 0.55, 0.05, 0.05), taper(bowl, s * 0.5, 0.05, 0.05), taper(leg, s * 0.5, 0.05, 0.05)]


def t_varsity_navy(ctx):
    nv, crm, wt = '#2B3A62', '#EEE2C8', '#FFFFFF'
    c = cxo(ctx)
    hem = 4.0
    stripe = lambda y0, y1, xl, xr: [(T(ctx, cr([(xl, y, 'c'), (xr, y, 'c'), (xr, y + 0.7, 'c'), (xl, y + 0.7, 'c')], 2)),
                                      crm, 1.0) for y in (y0 + (y1 - y0) * 0.3, y0 + (y1 - y0) * 0.62)]
    if ctx.back:
        ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, loose=1.0)), nv, shapes=body_folds(ctx, nv, hem))
        # 등판 아치 글자 자리
        ctx.fig('top', T(ctx, taper(quad((-8, -17), (0, -21.5), (8, -17), 12), 3.0, 0.1, 0.1)), crm, lw=1.2)
    else:
        ctx.fig('top', T(ctx, body_poly(ctx, hem=hem - 1, neck='crew')), wt,
                shapes=[(T(ctx, fold(quad((c - 1, -12), (c, -8), (c - 0.6, -3), 6))), '#D8D4E4', 0.8)])
        # 은 목걸이
        ctx.fig('top', T(ctx, taper(quad((c - 3.4, -25.4), (c + 0.2, -19.6), (c + 3.6, -25.4), 14), 0.8, 0.05, 0.05)),
                '#D9DCE6', lw=0.6, line='#7A8098')
        gap = 3.4
        for sx in (-1, 1):
            x_in = c + sx * gap
            x_sh = (-9.0 if sx < 0 else 10.0) if ctx.q else sx * 11.0
            x_out = (-12.3 if sx < 0 else 12.8) if ctx.q else sx * 13.8
            pts = [(x_sh, -25.5), (c + sx * 4.4, -26.6), (x_in + sx * 0.2, -14, 'c'), (x_in, hem, 'c'),
                   (x_out, hem, 'c'), (x_out + sx * 0.2, -2), (x_out - sx * 0.4, -12), (x_out + sx * 0.6, -21)]
            if sx > 0:
                pts = pts[::-1]
            sh = body_folds(ctx, nv, hem, 0.5)
            # 스냅 단추
            for y in (-19, -13, -7):
                sh.append((T(ctx, ellipse(x_in + sx * 1.5, y, 0.75, 0.75, 10)), '#F4F0E6'))
            # 주머니 (가죽 테)
            sh.append((T(ctx, taper(np.array([(x_in + sx * 3.2, -8), (x_in + sx * 4.6, -2.5)]), 1.2, 0.05, 0.05)), crm))
            ctx.fig('top', T(ctx, cr(pts, 6)), nv, shapes=sh)
            # 앞섶 크림 테
            ctx.fig('top', T(ctx, ribbon(quad((c + sx * 4.4, -26.4), (x_in + sx * 0.5, -18), (x_in, hem - 3), 10), 1.4,
                                         cap0=False, cap1=False)), crm, lw=1.0)
            ctx.fig('top', T(ctx, cr([(x_in, hem - 3, 'c'), (x_out, hem - 3, 'c'), (x_out, hem, 'c'), (x_in, hem, 'c')], 2)), nv,
                    lw=1.4, shapes=stripe(hem - 3, hem, min(x_in, x_out), max(x_in, x_out)))
        # R 패치 (가슴 왼쪽 = 화면 오른쪽)
        px = c + (6.6 if not ctx.q else 6.8)
        ctx.fig('top', T(ctx, letter_R(ctx, px, -17.5, 2.2, crm)[0]), crm, lw=0.9, line='#8E7E60')
        for g in letter_R(ctx, px, -17.5, 2.2, crm)[1:]:
            ctx.fig('top', T(ctx, g), crm, lw=0.9, line='#8E7E60')
    if ctx.back:
        ctx.fig('top', T(ctx, hem_band(ctx, hem - 3, hem, 1, 1.0)), nv,
                shapes=stripe(hem - 3, hem, -14, 14))
    # 칼라 (줄무늬 립)
    if ctx.front or ctx.back:
        col = cr([(-11, -24.5), (-5, -27.8), (5, -27.8), (11, -24.5), (5, -25.6), (0, -25.0), (-5, -25.6)], 5)
    else:
        col = cr([(-9.5, -24.5), (-3.5, -28.4), (6.5, -27.6), (8.5, -24.8), (3.5, -25.6), (-3.5, -25.8)], 5)
    ctx.fig('top', T(ctx, col), nv, lw=1.4)
    for k in ('F', 'N'):
        sh_ = []
        sleeve(ctx, k, crm, w0=8.8, w1=7.8, t1=0.93, cuff=nv, cuff_len=0.18)
        # 소매 패치
        cl = arm_line(ctx, k, 20)
        if not (ctx.q and k == 'F'):
            p = cl[6]
            ctx.fig(arm_layer(ctx, k, 'top'), ctx.root_unit(ellipse(p[0], p[1], 1.5, 1.5, 12)) if False else
                    ellipse(p[0], p[1], 1.5, 1.5, 12), '#C9424A', lw=0.9)


# ------------------------------------------------------------------ 민트 크롭 패딩 + 크로스백
def puffy(pts_func, amp):
    return pts_func


def t_puffer_mint(ctx):
    mt, wt, pink, blk = '#AEE6CC', '#FFFFFF', '#F48CBB', '#2C2834'
    c = cxo(ctx)
    hem = -3.5
    # 안쪽 흰 크롭 탑 (패딩 아래로 보임)
    ctx.fig('top', T(ctx, body_poly(ctx, hem=0.5, neck='crew')), wt,
            shapes=[(T(ctx, fold(quad((c - 4, -2), (c - 1, -1), (c + 2, -2.5), 6))), '#D8D4E4', 0.8)])
    poly = body_poly(ctx, hem=hem, loose=2.0, flare=1.08, neck='high', top=-25.0)
    quilt = []
    xl, xr = -16, 16
    for y in (-19.5, -14.5, -9.5):
        quilt.append((T(ctx, taper(quad((xl, y + 0.6), (c, y - 0.8), (xr, y + 0.6), 14), 1.0, 0.05, 0.05)),
                      shade(mt, 1.3), 0.95))
        quilt.append((T(ctx, taper(quad((xl, y - 1.6), (c, y - 3.0), (xr, y - 1.6), 14), 1.6, 0.25, 0.25)), light(mt), 0.8))
    if not ctx.back:
        # 지퍼
        quilt.append((T(ctx, taper(np.array([(c + 0.4, -26), (c + 0.4, hem)]), 0.8, 0.02, 0.02)), shade(mt, 1.6), 1))
    ctx.fig('top', T(ctx, poly), mt, shapes=quilt, sd=(1.4, 1.8))
    # 높은 칼라
    if not ctx.back:
        coll = cr([(c - 7, -24), (c - 7.5, -29.5), (c, -30.5), (c + 7.5, -29.5), (c + 7, -24), (c, -25)], 5)
        ctx.fig('top', T(ctx, coll), mt, shapes=[(T(ctx, ellipse(c, -27.0, 4.5, 1.6, 12)), shade(mt, 1.4), 0.8)])
        # 왼쪽 가슴 작은 로고 태그
        ctx.fig('top', T(ctx, cr([(c + 5, -18.2, 'c'), (c + 7.5, -18.2, 'c'), (c + 7.5, -16.6, 'c'), (c + 5, -16.6, 'c')], 2)),
                pink, lw=0.8)
    for k in ('F', 'N'):
        cl = sleeve(ctx, k, mt, w0=10.0, w1=9.0, t1=0.92, puff=1.2, folds=False, cuff=mt, cuff_len=0.14)
        # 소매 퀼팅 고리
        lay = arm_layer(ctx, k, 'top')
        for t in (0.3, 0.55, 0.78):
            p = sub(cl, t - 0.02, t + 0.02, 3)
            d = p[-1] - p[0]
            d = d / max(1e-6, np.linalg.norm(d))
            nrm = np.array([-d[1], d[0]])
            m = p[1]
            ctx.paint(lay, taper(quad(m - nrm * 4.4, m + d * 0.8, m + nrm * 4.4, 8), 0.9, 0.1, 0.1), shade(mt, 1.3), 0.9)
    # 크로스백: 오른어깨 -> 왼허리
    if ctx.front:
        a, b, lay = (8.5, -25.0), (-10.5, -3.5), 'top'
    elif ctx.back:
        a, b, lay = (-8.5, -25.0), (10.5, -3.5), 'top'
    else:
        a, b, lay = (7.5, -25.0), (-9.0, -3.5), 'top'
    ctx.fig(lay, T(ctx, ribbon(quad(a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 1.5), b, 12), 1.3)), blk, lw=1.1)
    if not ctx.back:
        x, y = b[0] + ctx.sway * 0.3, b[1] + 2.5
        bag = cr([(x - 3.6, y - 3.4, 'c'), (x + 3.6, y - 3.4, 'c'), (x + 3.6, y + 3.0), (x + 2.6, y + 3.8, 'c'),
                  (x - 2.6, y + 3.8, 'c'), (x - 3.6, y + 3.0)], 3)
        ctx.fig(lay, T(ctx, bag), blk,
                shapes=[(T(ctx, cr([(x - 3.6, y - 3.4), (x + 3.6, y - 3.4), (x + 3.6, y - 0.6), (x - 3.6, y - 0.6)], 2)),
                         light(blk, 0.3))])
        ctx.fig(lay, T(ctx, cr([(x - 1.2, y + 0.6, 'c'), (x + 1.2, y + 0.6, 'c'), (x + 1.2, y + 2.2, 'c'),
                                (x - 1.2, y + 2.2, 'c')], 2)), pink, lw=0.8)


# ------------------------------------------------------------------ 블라우스
def t_blouse_white(ctx):
    wt, pink = '#FBF7F2', '#F58AB4'
    c = cxo(ctx)
    hem = -2.0
    sh = body_folds(ctx, wt, hem)
    if not ctx.back:
        sh.append((T(ctx, taper(np.array([(c, -24), (c, hem)]), 1.6, 0.02, 0.02)), shade(wt, 0.6), 1.0))
        for y in (-19, -13, -7):
            sh.append((T(ctx, ellipse(c, y, 0.7, 0.7, 10)), '#F7C0D6'))
    ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, flare=1.02, loose=0.3)), wt, shapes=sh)
    # 프릴 밑단
    xs = np.linspace(-12.6, 12.6, 9) if not ctx.q else np.linspace(-11.3, 11.8, 9)
    fr = [(xs[0], hem - 1.5, 'c')]
    for i in range(len(xs) - 1):
        fr.append(((xs[i] + xs[i + 1]) / 2, hem + 1.4))
        fr.append((xs[i + 1], hem + 0.2, 'c'))
    fr += [(xs[-1], hem - 1.5, 'c')]
    ctx.fig('top', T(ctx, cr(fr, 4)), wt, lw=1.5)
    # 둥근 칼라 + 리본
    if not ctx.back:
        for sx in (-1, 1):
            cpts = [(c, -25.0), (c + sx * 5.5, -27.0), (c + sx * 7.5, -24.5), (c + sx * 5.0, -21.8), (c + sx * 1.2, -22.5)]
            ctx.fig('top', T(ctx, cr(cpts, 5)), wt, lw=1.5)
        bx, by = c, -22.2
        for sx in (-1, 1):
            ctx.fig('top', T(ctx, cr([(bx, by), (bx + sx * 3.6, by - 2.2), (bx + sx * 4.0, by + 1.8)], 5)), pink,
                    shapes=[(T(ctx, fold(quad((bx + sx * 0.8, by), (bx + sx * 2.0, by - 0.6), (bx + sx * 3.2, by - 0.4), 6), 0.6)),
                             shade(pink), 0.8)])
            ctx.fig('top', T(ctx, taper(quad((bx, by + 0.4), (bx + sx * 1.6, by + 3.0), (bx + sx * 1.0 + ctx.sway * 0.5, by + 5.6), 8),
                                        1.6, 0.05, 0.3)), pink)
        ctx.fig('top', T(ctx, ellipse(bx, by, 1.2, 1.1, 10)), shade(pink), lw=1.0)
    else:
        ctx.fig('top', T(ctx, cr([(-7, -25), (0, -27.5), (7, -25), (5, -22), (0, -21.5), (-5, -22)], 5)), wt, lw=1.5)
    for k in ('F', 'N'):
        sleeve(ctx, k, wt, w0=9.6, w1=7.2, t1=0.48, puff=2.2, folds=False, cuff=wt, cuff_w=6.6, cuff_len=0.22)


# ------------------------------------------------------------------ 초록 멜빵
def t_overalls_green(ctx):
    tee, g, yl = '#FFF6E4', '#55B24E', '#F7C948'
    c = cxo(ctx)
    ctx.fig('top', T(ctx, body_poly(ctx, hem=-1.0)), tee, shapes=body_folds(ctx, tee, -1.0, 0.6))
    for k in ('F', 'N'):
        sleeve(ctx, k, tee, w0=8.4, w1=7.4, t1=0.46, folds=False, cuff=tee, cuff_len=0.2)
    # 허리 밴드 + 가슴판
    wb = cr([(-12.8, -6.5, 'c'), (12.8, -6.5, 'c'), (13.0, 0.5, 'c'), (-13.0, 0.5, 'c')], 3) if not ctx.q else \
        cr([(-11.6, -6.5, 'c'), (12.0, -6.5, 'c'), (12.2, 0.5, 'c'), (-11.8, 0.5, 'c')], 3)
    if not ctx.back:
        bib = cr([(c - 7.0, -19.5, 'c'), (c + 7.0, -19.5, 'c'), (c + 7.5, -5, 'c'), (c - 7.5, -5, 'c')], 3)
        ctx.fig('top', T(ctx, bib), g,
                shapes=[(T(ctx, cr([(c - 3.5, -16, 'c'), (c + 3.5, -16, 'c'), (c + 3.5, -10.5), (c, -9.5), (c - 3.5, -10.5)], 3)),
                         shade(g), 0.8),
                        (T(ctx, taper(quad((c - 6, -18.5), (c, -18.8), (c + 6, -18.5), 8), 0.5, 0.05, 0.05)), light(g), 0.9)])
        ctx.fig('top', T(ctx, wb), g)
        for sx in (-1, 1):
            x = c + sx * 5.0
            st = quad((x, -19), (x + sx * 1.2, -23.5), (x + sx * 2.5 - (2 if ctx.q else 0), -26.5), 8)
            ctx.fig('top', T(ctx, ribbon(st, 2.6, cap0=False)), g)
            ctx.fig('top', T(ctx, ellipse(x, -18.0, 1.3, 1.3, 12)), yl, lw=1.0, line='#9A6A10')
    else:
        ctx.fig('top', T(ctx, wb), g)
        for sx in (-1, 1):
            st = np.array([(sx * 6.5, -26.5), (-sx * 4.0, -6.0)])
            ctx.fig('top', T(ctx, ribbon(st, 2.6, cap0=False, cap1=False)), g)


# ------------------------------------------------------------------ 빨간 줄무늬 티
def t_tee_stripe_red(ctx):
    w, red = '#FBF7F2', '#E8483E'
    hem = 2.5
    stripes = []
    for y in np.arange(-22, hem, 4.0):
        stripes.append((T(ctx, cr([(-16, y, 'c'), (16, y, 'c'), (16, y + 1.9, 'c'), (-16, y + 1.9, 'c')], 2)), red, 1.0))
    ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, loose=0.4)), w, shapes=stripes + body_folds(ctx, w, hem))
    if not ctx.back:
        c = cxo(ctx)
        ctx.fig('top', T(ctx, taper(quad((c - 5, -26), (c, -22.6), (c + 5, -26), 10), 1.4, 0.1, 0.1)), red, lw=1.0)
    for k in ('F', 'N'):
        cl = arm_line(ctx, k, 20)
        sl = []
        for t in (0.12, 0.30):
            p = sub(cl, t, t + 0.08, 4)
            sl.append((ribbon(p, 9.0, cap0=False, cap1=False), red, 1.0))
        sleeve(ctx, k, w, w0=8.4, w1=7.4, t1=0.46, folds=False, cuff=red, cuff_len=0.15, shapes_extra=sl)


# ------------------------------------------------------------------ 파란 망토 셔츠
def t_cape_blue(ctx):
    shirt, blue, yl = '#EEF2FA', '#3E6BD8', '#F7C948'
    c = cxo(ctx)
    hem = 2.0
    sw = ctx.sway

    def cape(layer):
        if ctx.front:
            pts = [(-11, -26), (11, -26), (15 - sw, -10), (17.5 - sw * 2, 9, 'c'), (8 - sw * 2, 7.0), (0 - sw * 2, 9.5),
                   (-8 - sw * 2, 7), (-17.5 - sw * 2, 9, 'c'), (-15 - sw, -10)]
        elif ctx.back:
            pts = [(-11, -27), (11, -27), (14 - sw, -10), (16 - sw * 2, 9, 'c'), (8 - sw * 2, 7.0), (0 - sw * 2, 9.5),
                   (-8 - sw * 2, 7), (-16 - sw * 2, 9, 'c'), (-14 - sw, -10)]
        else:
            pts = [(-6, -27), (4, -27), (-2 - sw, -10), (-6 - sw * 3, 8, 'c'), (-12 - sw * 3, 6), (-18 - sw * 4, 7.5, 'c'),
                   (-16 - sw * 2, -10), (-11, -22)]
        folds = [(T(ctx, fold(quad((x * 0.4, -20), (x * 0.8, -8), (x - sw * 2, 6), 10), 1.1)), deep(blue), 0.8)
                 for x in ((-7, 0, 7) if not ctx.q else (-9, -14))]
        lining = []
        if not ctx.back:
            lining = [(T(ctx, ribbon(quad(pts[2][:2], pts[3][:2], pts[4][:2], 8), 2.2)), yl, 1.0)]
        ctx.fig(layer, T(ctx, cr(pts, 6)), blue, shapes=folds + lining)
    if not ctx.back:
        cape('top_back')
    sh = body_folds(ctx, shirt, hem)
    if not ctx.back:
        sh.append((T(ctx, taper(np.array([(c, -24), (c, hem)]), 1.4, 0.02, 0.02)), shade(shirt, 0.6), 1.0))
        for y in (-18, -12, -6):
            sh.append((T(ctx, ellipse(c, y, 0.7, 0.7, 10)), '#9AA8C8'))
        # 허리 벨트
        sh.append((T(ctx, cr([(-15, -5, 'c'), (15, -5, 'c'), (15, -2.2, 'c'), (-15, -2.2, 'c')], 2)), '#8A5A3A', 1.0))
        sh.append((T(ctx, cr([(c - 1.6, -5.4, 'c'), (c + 1.6, -5.4, 'c'), (c + 1.6, -1.8, 'c'), (c - 1.6, -1.8, 'c')], 2)), yl, 1.0))
    ctx.fig('top', T(ctx, body_poly(ctx, hem=hem)), shirt, shapes=sh)
    for k in ('F', 'N'):
        sleeve(ctx, k, shirt, w0=8.0, w1=7.0, t1=0.94, cuff=shirt, cuff_len=0.16)
    if ctx.back:
        cape('top_near')
    else:
        # 망토 어깨 덮개 + 금 브로치
        if ctx.front:
            mant = cr([(-13.5, -21), (-10, -27.5), (0, -28.5), (10, -27.5), (13.5, -21), (7, -23.5), (0, -23), (-7, -23.5)], 6)
            cx = 0
        else:
            mant = cr([(-11.5, -20), (-8, -28), (2, -28.5), (9, -27), (8, -23), (1, -23.5), (-5, -23)], 6)
            cx = c + 1.5
        ctx.fig('top', T(ctx, mant), blue, shapes=[(T(ctx, fold(quad((-6, -25), (0, -24.4), (6, -25), 8), 0.8)), deep(blue), 0.6)])
        ctx.fig('top', T(ctx, ellipse(cx, -24.5, 1.9, 1.9, 14)), yl, line='#9A6A10',
                shapes=[(T(ctx, ellipse(cx - 0.5, -25.0, 0.6, 0.6, 8)), '#FFFBE0')])


# ------------------------------------------------------------------ 드롭: 슬라임 젤리 후드
SLIME = '#86DC6C'


def slime_face(ctx, x, y, s, layer, lay_fn=None):
    for sx in (-1, 1):
        ex = x + sx * 2.2 * s
        ctx.fig(layer, T(ctx, ellipse(ex, y, 0.95 * s, 1.35 * s, 12)), '#1E3A20', lw=0.6, line='#1E3A20', shd=False,
                shapes=[(T(ctx, ellipse(ex - 0.3 * s, y - 0.5 * s, 0.4 * s, 0.45 * s, 8)), '#FFFFFF')])
    ctx.fig(layer, T(ctx, taper(quad((x - 1.4 * s, y + 1.6 * s), (x, y + 2.8 * s), (x + 1.4 * s, y + 1.6 * s), 8), 0.7 * s, 0.1, 0.1)),
            '#1E3A20', noline=True, shd=False)


def t_slime_hood(ctx):
    g = SLIME
    c = cxo(ctx)
    hem = 5.0
    gl = light(g, 1.0)
    # 젤리 후드 (뒤로 넘긴 큰 방울)
    if ctx.front:
        hp = [(-14.5, -22), (-15.5, -30), (-8, -35.5), (8, -35.5), (15.5, -30), (14.5, -22), (6, -25.5), (-6, -25.5)]
    elif ctx.q:
        hp = [(-15, -19), (-18, -28), (-12, -35.5), (-2, -35), (4, -28), (-2, -23), (-8, -21)]
    else:
        hp = [(-12, -30), (-6, -32), (6, -32), (12, -30), (13, -20), (7, -11), (0, -9), (-7, -11), (-13, -20)]
    hshapes = [(T(ctx, taper(quad(hp[1][:2], ((hp[1][0] + hp[2][0]) / 2, hp[2][1]), hp[2][:2], 8), 1.6, 0.3, 0.3)), gl, 0.9)]
    hood_lay = 'top' if ctx.back else 'top'
    if not ctx.back:
        ctx.fig(hood_lay, T(ctx, cr(hp, 6)), g, shapes=hshapes)
        if ctx.q:
            slime_face(ctx, -9.5, -29.5, 1.1, hood_lay)
    # 몸판 + 흘러내린 방울 밑단
    poly = body_poly(ctx, hem=hem - 2, loose=1.0, flare=1.05)
    sh = body_folds(ctx, g, hem - 2, 0.6)
    sh += [(T(ctx, taper(quad((-9, -21), (-10.5, -14), (-9, -6), 10), 2.2, 0.3, 0.3)), gl, 0.8),
           (T(ctx, ellipse(-6.5, -21.5, 1.4, 1.0, 10)), '#FFFFFF', 0.9)]
    for bx, by, r in ((4, -12, 1.2), (-3, -5, 0.9), (8, -3, 0.7)):
        sh.append((T(ctx, ellipse(c + bx, by, r, r, 10)), light(g, 0.6), 0.9))
        sh.append((T(ctx, ellipse(c + bx - r * 0.3, by - r * 0.3, r * 0.35, r * 0.35, 8)), '#FFFFFF', 0.9))
    ctx.fig('top', T(ctx, poly), g, shapes=sh, alpha=0.97)
    # 방울 밑단
    xs = np.linspace(-12.8, 12.8, 6) if not ctx.q else np.linspace(-11.8, 12.3, 6)
    for i, x in enumerate(xs):
        L = 3.0 + (i % 3) * 1.4
        d = cr([(x - 2.4, hem - 3.5), (x + 2.4, hem - 3.5), (x + 1.6, hem - 1 + L * 0.4), (x, hem - 1 + L),
                (x - 1.6, hem - 1 + L * 0.4)], 5)
        ctx.fig('top', T(ctx, d), g, shapes=[(T(ctx, ellipse(x - 0.5, hem - 1 + L * 0.5, 0.45, 0.8, 8)), '#FFFFFF', 0.8)])
    if ctx.back:
        ctx.fig('top', T(ctx, cr(hp, 6)), g, shapes=hshapes)
        slime_face(ctx, 0, -22, 1.4, 'top')
    elif ctx.front:
        slime_face(ctx, c, -9.5, 1.4, 'top')
    else:
        slime_face(ctx, c + 2.5, -9.5, 1.3, 'top')
    for k in ('F', 'N'):
        sleeve(ctx, k, g, w0=9.4, w1=8.4, t1=0.9, puff=0.6, folds=False,
               shapes_extra=[(taper(sub(arm_line(ctx, k, 16), 0.1, 0.5) + (-1.2, -0.6), 1.4, 0.3, 0.3), gl, 0.8)])
        # 소매 끝 방울
        cl = arm_line(ctx, k, 20)
        p = sub(cl, 0.86, 0.9, 2)[1]
        ctx.fig(arm_layer(ctx, k, 'top'), ellipse(p[0] + 0.5, p[1] + 2.4, 1.4, 2.0, 12), g)


# ------------------------------------------------------------------ 드롭: 박쥐 날개 상의
BAT = '#4C3B6E'
BAT_W = '#6A4E94'


def bat_wing(ctx, side, layer, span=26.0, flap=0.0):
    """side: -1 왼쪽 / +1 오른쪽 (몸통 로컬). 손가락 뼈 + 물결 아래 가장자리."""
    root = np.array([side * 4.0, -21.0]) if not ctx.q else np.array([-6.0, -21.0])
    up = -8 - flap * 6
    tips = [(side * span, up - 6), (side * (span - 3), up + 8), (side * (span - 9), up + 16), (side * 9, -3)]
    pts = [tuple(root + (0, -2))] + [(side * span * 0.55, up - 9)] + [tips[0] + ('c',)]
    for i in range(1, len(tips)):
        a = np.array(tips[i - 1][:2]); b = np.array(tips[i][:2])
        m = (a + b) / 2 + np.array([-side * 2.0, -3.0])
        pts += [tuple(m), tuple(b) + ('c',)]
    pts += [tuple(root + (side * 2, 4))]
    bones = [(T(ctx, fold(np.array([root, t[:2]]), 0.9)), '#2E2244', 0.9) for t in tips[:3]]
    memb = [(T(ctx, cr([tuple(root), tips[0][:2], tips[1][:2]], 3)), BAT_W, 0.55)]
    ctx.fig(layer, T(ctx, cr(pts, 5)), '#3A2C58', shapes=memb + bones, sd=(1.2, 1.6))


def t_bat_cape(ctx):
    vest, red = BAT, '#E2465A'
    c = cxo(ctx)
    hem = 3.5
    flap = ctx.lift if ctx.lift else (0.3 * math.sin(ctx.sway * 2))
    if ctx.front:
        for s in (-1, 1):
            bat_wing(ctx, s, 'top_back', flap=flap)
    elif ctx.q:
        # 옆에서는 두 날개가 등 뒤(왼쪽)로 겹쳐 보인다
        bat_wing(ctx, -1, 'top_back', span=24, flap=flap + 0.4)
        bat_wing(ctx, -1, 'top_back', span=20, flap=flap - 0.3)
    sh = body_folds(ctx, vest, hem)
    if not ctx.back:
        # V 앞섶 + 지그재그 밑단 무늬
        sh.append((T(ctx, cr([(c - 3.5, -25.5), (c + 3.5, -25.5), (c, -16, 'c')], 3)), '#2E2244', 1.0))
        sh.append((T(ctx, taper(np.array([(c, -16), (c, hem)]), 0.9, 0.05, 0.05)), '#2E2244', 0.9))
    ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, loose=0.6)), vest, shapes=sh)
    # 박쥐 모양 밑단
    xs = np.linspace(-13.2, 13.2, 7) if not ctx.q else np.linspace(-12.0, 12.4, 7)
    hp = [(xs[0], hem - 2.5, 'c')]
    for i in range(len(xs) - 1):
        hp += [((xs[i] + xs[i + 1]) / 2, hem - 0.8), (xs[i + 1], hem + 1.6, 'c')]
    hp += [(xs[-1], hem - 2.5, 'c')]
    ctx.fig('top', T(ctx, cr(hp, 4)), '#3A2C58', lw=1.4)
    # 높은 박쥐 칼라 + 빨간 보석
    if not ctx.back:
        for sx in (-1, 1):
            cp = [(c + sx * 1.0, -25.0), (c + sx * 6.5, -31.5, 'c'), (c + sx * 7.5, -27.5), (c + sx * 9.5, -26.5, 'c'),
                  (c + sx * 7.0, -23.5)]
            ctx.fig('top', T(ctx, cr(cp, 4)), '#3A2C58', lw=1.4, shapes=[(T(ctx, ellipse(c + sx * 5, -27, 1.4, 2.0, 8)), BAT_W, 0.8)])
        ctx.fig('top', T(ctx, rot(cr([(0, -2.0, 'c'), (1.6, 0, 'c'), (0, 2.0, 'c'), (-1.6, 0, 'c')], 3), 0) + (c, -24.6)), red,
                line='#7A1A2A', lw=1.0, shapes=[(T(ctx, ellipse(c - 0.5, -25.3, 0.5, 0.5, 8)), '#FFD0D8')])
    else:
        for s in (-1, 1):
            bat_wing(ctx, s, 'top_near', flap=flap)
    for k in ('F', 'N'):
        sleeve(ctx, k, vest, w0=8.0, w1=7.0, t1=0.94, cuff='#3A2C58', cuff_len=0.2)


# ------------------------------------------------------------------ 드롭: 골렘 돌갑옷
STONE = '#B2A89A'
MOSS = '#7FBF4A'


def crack(p):
    return fold(np.asarray(p, float), 0.8)


def t_golem_armor(ctx):
    st, dk = STONE, '#6E6458'
    c = cxo(ctx)
    hem = 3.0
    under = '#6A4A36'
    ctx.fig('top', T(ctx, body_poly(ctx, hem=hem, loose=0.4)), under)
    # 가슴판 (돌 판 3장)
    if not ctx.back:
        plates = [
            [(c - 11.5, -24.5), (c - 1.0, -26.0), (c - 0.6, -13.5), (c - 12.0, -12.5)],
            [(c + 1.0, -26.0), (c + 12.0, -24.5), (c + 12.5, -12.5), (c + 0.6, -13.5)],
            [(c - 12.5, -11.5), (c + 12.8, -11.5), (c + 13.0, hem), (c - 13.0, hem)],
        ]
    else:
        plates = [[(-11.5, -25), (11.5, -25), (12.5, -12.5), (-12.5, -12.5)],
                  [(-12.8, -11.5), (12.8, -11.5), (13.0, hem), (-13.0, hem)]]
    cracks = [crack([(-6, -22), (-4.5, -19), (-6.5, -16.5)]), crack([(7, -20), (5, -17.5)]), crack([(-2, -8), (1, -5), (0, -2)])]
    for i, p in enumerate(plates):
        pc = [(x, y, 'c') for x, y in p]
        sh = [(T(ctx, cracks[i % len(cracks)]), dk, 0.9),
              (T(ctx, taper(np.array([p[0], p[1]]) + (0, 1.2), 1.4, 0.15, 0.15)), light(st, 0.8), 0.9)]
        ctx.fig('top', T(ctx, cr(pc, 3)), st, shapes=sh)
    # 이끼
    for x, y, r in ((-9, -24.5, 3.2), (9, -24.5, 2.8), (c + 7, hem - 1, 2.4)):
        m = cr([(x - r, y + 0.6), (x - r * 0.5, y - 0.9), (x, y - 0.3), (x + r * 0.5, y - 1.1), (x + r, y + 0.4),
                (x + r * 0.4, y + 1.6), (x - r * 0.4, y + 1.4)], 4)
        ctx.fig('top', T(ctx, m), MOSS, lw=1.2)
    # 돌 벨트 + 룬 보석
    if not ctx.back:
        ctx.fig('top', T(ctx, ellipse(c, -6.0, 2.2, 2.2, 6)), '#6BD4E8', line='#2A6C82',
                shapes=[(T(ctx, ellipse(c - 0.6, -6.6, 0.7, 0.7, 6)), '#E8FCFF')])
    for k in ('F', 'N'):
        cl = sleeve(ctx, k, under, w0=7.8, w1=7.0, t1=0.94, folds=True)
        lay = arm_layer(ctx, k, 'top')
        # 팔뚝 돌 보호대
        fc = sub(arm_line(ctx, k, 20), 0.62, 0.95, 8)
        ctx.fig(lay, ribbon(fc, 8.4, cap0=False, cap1=False), st,
                shapes=[(taper(sub(fc, 0.2, 0.8, 4) + (0.6, 0.2), 0.8, 0.2, 0.2), dk, 0.8)])
        # 어깨 바위
        s = ctx.arms[k]['sh']
        a = rot(cr([(-6.5, 1.5), (-5.5, -3.5), (-1, -5.5), (4.5, -4.5), (6.5, 0.5), (4, 3.5), (-3, 3.8)], 5), ctx.torso_a) + s
        ctx.fig(lay, a, st, shapes=[(rot(cr([(-4.5, -2.8), (0, -4.6), (3.5, -3.5), (0.5, -2.2)], 4), ctx.torso_a) + s, MOSS, 1.0),
                                    (rot(crack([(1, -1), (2.5, 1.5), (1.6, 3)]), ctx.torso_a) + s, dk, 0.9)])


TOPS = {
    'hoodie-lavender': t_hoodie_lavender, 'cardigan-cream': t_cardigan_cream, 'varsity-navy': t_varsity_navy,
    'puffer-mint': t_puffer_mint, 'hoodie-black': t_hoodie_black, 'hoodie-white': t_hoodie_white,
    'blouse-white': t_blouse_white, 'overalls-green': t_overalls_green, 'tee-stripe-red': t_tee_stripe_red,
    'cape-blue': t_cape_blue,
    'slime-hood': t_slime_hood, 'bat-cape': t_bat_cape, 'golem-armor': t_golem_armor,
}
