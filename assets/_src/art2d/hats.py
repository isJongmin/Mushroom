"""모자 7종 + 드롭 3종. 머리 로컬 좌표 (머리카락 정수리 y≈-62)."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, quad, bez, rot, shade, light, deep, line_of, mix, sub


def H(ctx, p):
    return ctx.Th(np.asarray(p, float))


def F(ctx, layer, poly, col, shapes=(), **kw):
    ctx.fig(layer, H(ctx, poly), col, shapes=[(H(ctx, s[0]),) + tuple(s[1:]) for s in shapes], **kw)


def brim_shadow(ctx, poly, dy=3.2, alpha=0.30):
    p = np.asarray([q[:2] for q in poly], float) + (0.5, dy)
    ctx.paint('shade_hat', H(ctx, p), '#5A3040', alpha)


def hx(ctx):
    return 3.0 if ctx.q else 0.0


def fold(c, w=0.9):
    return taper(np.asarray(c, float), w, 0.3, 0.45)


# ------------------------------------------------------------------ 버킷햇
def h_bucket_white(ctx):
    col = '#FAF7F2'
    x = hx(ctx)
    crown = cr([(x - 27, -44), (x - 26, -57), (x - 16, -67), (x, -69), (x + 16, -67), (x + 26, -57), (x + 27, -44)], 6)
    brim = cr([(x - 38, -36.5), (x - 31, -46), (x, -48.5), (x + 31, -46), (x + 38, -36.5), (x + 30, -33.5), (x, -35.5),
               (x - 30, -33.5)], 6)
    F(ctx, 'hat', crown, col, sd=(1.4, 1.8),
      shapes=[(fold(quad((x - 18, -49), (x - 15, -58), (x - 9, -64), 8), 1.0), shade(col, 1.0), 0.7),
              (fold(quad((x + 18, -49), (x + 16, -58), (x + 10, -64), 8), 1.0), shade(col, 1.0), 0.7),
              (taper(quad((x - 14, -63), (x - 4, -67.2), (x + 6, -65.5), 10), 2.2, 0.3, 0.3), '#FFFFFF', 0.9),
              (cr([(x - 27, -49, 'c'), (x + 27, -49, 'c'), (x + 27, -45.5, 'c'), (x - 27, -45.5, 'c')], 2), '#EDE6F8', 1.0)])
    stitches = [(taper(quad((x - 33, -38.6), (x, -42.8 + i * 2.2), (x + 33, -38.6), 16), 0.45, 0.05, 0.05), shade(col, 0.8), 0.9)
                for i in range(2)]
    F(ctx, 'hat', brim, col, shapes=stitches, sd=(1.0, 1.6))
    brim_shadow(ctx, brim)
    if not ctx.back:
        px, py = x + (14 if ctx.front else 13), -57
        sq = cr([(px - 3, py - 3, 'c'), (px + 3, py - 3, 'c'), (px + 3, py + 3, 'c'), (px - 3, py + 3, 'c')], 2)
        F(ctx, 'hat', sq, '#C3AEF0', lw=1.2, line='#6A55A8',
          shapes=[(ellipse(px - 1.2, py - 0.6, 0.5, 0.7, 8), '#6A55A8'), (ellipse(px + 1.2, py - 0.6, 0.5, 0.7, 8), '#6A55A8'),
                  (taper(quad((px - 1.4, py + 1.0), (px, py + 2.2), (px + 1.4, py + 1.0), 6), 0.6, 0.2, 0.2), '#6A55A8')])


# ------------------------------------------------------------------ 캡
def cap(ctx, col, logo, logo_line, bill=None):
    bill = bill or col
    x = hx(ctx) * 0.3
    crown = cr([(x - 31, -40, 'c'), (x - 30, -54), (x - 18, -66), (x, -69), (x + 18, -66), (x + 30, -54), (x + 31, -40, 'c')], 6)
    seams = [(fold(quad((x - 1, -68), (x - 9, -56), (x - 13, -41), 10), 0.8), deep(col, 0.8), 0.7),
             (fold(quad((x + 1, -68), (x + 9, -56), (x + 13, -41), 10), 0.8), deep(col, 0.8), 0.7),
             (taper(quad((x - 18, -61), (x - 8, -66.6), (x + 4, -66.0), 10), 2.2, 0.3, 0.3), light(col, 0.6), 0.9)]
    if ctx.q:
        # 챙이 오른쪽(앞)으로
        b = cr([(x + 2, -41.5), (x + 22, -45), (x + 41, -40.5), (x + 43, -37.5), (x + 30, -36.4), (x + 6, -38)], 6)
        F(ctx, 'hat', crown, col, shapes=seams, sd=(1.4, 1.8))
        F(ctx, 'hat', b, bill, shapes=[(taper(quad((x + 8, -40), (x + 26, -42.5), (x + 40, -39.5), 10), 0.6, 0.1, 0.1), light(bill, 0.4), 0.8)],
          sd=(0.8, 1.6))
        brim_shadow(ctx, b, dy=3.6, alpha=0.32)
        lx, ly = x + 14, -54
    elif ctx.front:
        F(ctx, 'hat', crown, col, shapes=seams, sd=(1.4, 1.8))
        b = cr([(x - 27, -41.5), (x - 14, -45.5), (x, -46.5), (x + 14, -45.5), (x + 27, -41.5), (x + 19, -36.0), (x, -34.6),
                (x - 19, -36.0)], 6)
        F(ctx, 'hat', b, bill, shapes=[(cr([(x - 26, -41), (x, -45.6), (x + 26, -41), (x + 18, -39.5), (x, -40.5), (x - 18, -39.5)], 5),
                                         light(bill, 0.25), 1.0)], sd=(0.8, 1.6))
        brim_shadow(ctx, b, dy=3.0, alpha=0.32)
        lx, ly = x, -55
    else:
        F(ctx, 'hat', crown, col, shapes=seams, sd=(1.4, 1.8))
        # 뒤 조절끈 구멍
        F(ctx, 'hat', cr([(x - 6, -40, 'c'), (x - 6, -45), (x, -48), (x + 6, -45), (x + 6, -40, 'c')], 5), deep(col, 1.4), lw=1.2)
        F(ctx, 'hat', cr([(x - 7, -41.5, 'c'), (x + 7, -41.5, 'c'), (x + 7, -39.6, 'c'), (x - 7, -39.6, 'c')], 2), col, lw=1.2)
        lx = None
    F(ctx, 'hat', ellipse(x, -68.6, 2.6, 1.4, 12), col, lw=1.2)
    if lx is not None:
        logo(ctx, lx, ly, logo_line)


def logo_mush(fill):
    def f(ctx, x, y, ln):
        capp = cr([(x - 5.5, y + 0.5, 'c'), (x - 4.5, y - 3.0), (x, y - 5.0), (x + 4.5, y - 3.0), (x + 5.5, y + 0.5, 'c')], 6)
        F(ctx, 'hat', capp, fill, lw=1.1, line=ln, shd=False,
          shapes=[(ellipse(x - 2, y - 2.4, 1.0, 0.8, 8), ln, 0.9), (ellipse(x + 2.2, y - 1.6, 0.8, 0.7, 8), ln, 0.9)])
        F(ctx, 'hat', cr([(x - 1.8, y + 0.5, 'c'), (x + 1.8, y + 0.5, 'c'), (x + 1.5, y + 4.0, 'c'), (x - 1.5, y + 4.0, 'c')], 2), fill,
          lw=1.1, line=ln, shd=False)
    return f


def h_cap_black(ctx):
    cap(ctx, '#2E2B36', logo_mush('#F1E3C6'), '#8E7E60')


def h_cap_white(ctx):
    cap(ctx, '#FAF7F2', logo_mush('#3E6BD8'), '#22346E', bill='#F0ECE6')


# ------------------------------------------------------------------ 버섯 모자 (빨강) / 드롭 주황버섯
def mushroom(ctx, col, spot, under='#FFF1DC', tall=0.0, spots=None, eyes=False):
    x = hx(ctx) * 0.4
    capp = cr([(x - 42, -36), (x - 38, -50), (x - 24, -66 - tall * 0.6), (x, -72 - tall), (x + 24, -66 - tall * 0.6),
               (x + 38, -50), (x + 42, -36), (x + 30, -32.5), (x, -34), (x - 30, -32.5)], 7)
    gills = cr([(x - 38, -36.5), (x, -39.5), (x + 38, -36.5), (x + 30, -32.8), (x, -34.2), (x - 30, -32.8)], 6)
    sp = spots or [(-22, -56, 5.5, 4.4), (4, -63, 6.4, 4.8), (25, -52, 4.6, 3.6), (-33, -42, 3.2, 2.6), (14, -44, 3.6, 2.8),
                   (-9, -47, 3.0, 2.4), (34, -40, 2.4, 2.0)]
    shapes = [(ellipse(x + a, b, c, d, 18), spot, 1.0) for a, b, c, d in sp]
    shapes.append((taper(quad((x - 26, -60), (x - 10, -69 - tall), (x + 8, -68.5 - tall), 10), 3.2, 0.3, 0.3), light(col, 0.7), 0.8))
    if not ctx.back:
        shapes.append((gills, under, 1.0))
        for gx in np.linspace(-30, 30, 9):
            shapes.append((taper(np.array([(x + gx * 0.92, -35.0), (x + gx, -37.0)]), 0.6, 0.1, 0.1), shade(under, 1.2), 0.8))
    F(ctx, 'hat', capp, col, shapes=shapes, sd=(1.6, 2.2))
    brim_shadow(ctx, capp[np.asarray(capp)[:, 1] > -40] if False else capp, dy=3.0, alpha=0.22)
    if eyes and ctx.front:
        for sx in (-1, 1):
            F(ctx, 'hat', ellipse(x + sx * 8, -52, 1.6, 2.4, 12), '#3A1E10', lw=0.6, shd=False,
              shapes=[(ellipse(x + sx * 8 - 0.5, -53, 0.6, 0.7, 8), '#FFFFFF')])


def h_mushroom_red(ctx):
    mushroom(ctx, '#E8483E', '#FFFFFF')


def h_mushroom_cap(ctx):
    """드롭: 주황버섯 갓 (더 둥글고 높다, 크림 반점 + 작은 눈)."""
    mushroom(ctx, '#F59A3C', '#FFE7B8', tall=4.0,
             spots=[(-20, -60, 4.2, 3.4), (8, -68, 4.6, 3.6), (26, -55, 3.6, 3.0), (-34, -45, 2.8, 2.4), (30, -42, 2.4, 2.0)],
             eyes=True)


# ------------------------------------------------------------------ 탐험가 모자
def h_explorer_brown(ctx):
    col = '#B07A4A'
    band = '#5A3A26'
    x = hx(ctx)
    crown = cr([(x - 25, -45, 'c'), (x - 24, -58), (x - 14, -67), (x, -68.5), (x + 14, -67), (x + 24, -58), (x + 25, -45, 'c')], 6)
    brim = cr([(x - 42, -40.5), (x - 33, -46.5), (x, -48.0), (x + 33, -46.5), (x + 42, -40.5), (x + 32, -38), (x, -39.6),
               (x - 32, -38)], 6)
    F(ctx, 'hat', crown, col, sd=(1.4, 1.8),
      shapes=[(fold(quad((x, -67), (x + 0.6, -60), (x, -54), 8), 1.2), deep(col), 0.8),
              (taper(quad((x - 14, -62), (x - 6, -66.6), (x + 4, -66), 10), 2.2, 0.3, 0.3), light(col, 0.6), 0.85),
              (cr([(x - 26, -51, 'c'), (x + 26, -51, 'c'), (x + 26, -46.5, 'c'), (x - 26, -46.5, 'c')], 2), band, 1.0)])
    F(ctx, 'hat', brim, col, sd=(1.0, 1.6),
      shapes=[(taper(quad((x - 36, -41.8), (x, -45.2), (x + 36, -41.8), 16), 0.5, 0.05, 0.05), deep(col, 0.8), 0.8)])
    brim_shadow(ctx, brim)
    if not ctx.back:
        # 깃털
        fx = x + (17 if not ctx.q else 15)
        fe = quad((fx, -50), (fx + 4, -58), (fx + 1, -66), 10)
        F(ctx, 'hat', taper(fe, 4.2, 0.1, 0.5, 0.6), '#E8483E', shapes=[(taper(fe, 0.6, 0.1, 0.1), '#9E2838', 0.9)])


# ------------------------------------------------------------------ 비니
def h_beanie_yellow(ctx):
    col = '#F7C948'
    x = hx(ctx) * 0.4
    dome = cr([(x - 32, -45, 'c'), (x - 30, -58), (x - 18, -69), (x, -72), (x + 18, -69), (x + 30, -58), (x + 32, -45, 'c')], 6)
    ribs = [(fold(quad((x + gx * 0.4, -70), (x + gx * 0.92, -60), (x + gx, -48), 8), 0.8), shade(col, 1.0), 0.75)
            for gx in np.linspace(-26, 26, 9)]
    ribs.append((taper(quad((x - 18, -64), (x - 8, -69.6), (x + 4, -69), 10), 2.4, 0.3, 0.3), light(col, 0.7), 0.85))
    F(ctx, 'hat', dome, col, shapes=ribs, sd=(1.4, 1.8))
    cuff = cr([(x - 34, -50, 'c'), (x, -52.5), (x + 34, -50, 'c'), (x + 34.5, -41.5, 'c'), (x, -39.5), (x - 34.5, -41.5, 'c')], 6)
    cr_ribs = [(fold(np.array([(x + gx, -50.5), (x + gx, -41)]), 0.9), shade(col, 1.1), 0.85) for gx in np.linspace(-31, 31, 17)]
    F(ctx, 'hat', cuff, col, shapes=cr_ribs, sd=(1.0, 1.6))
    brim_shadow(ctx, cuff, dy=2.6, alpha=0.25)
    if not ctx.back:
        F(ctx, 'hat', cr([(x + 10, -48.5, 'c'), (x + 17, -48.5, 'c'), (x + 17, -44, 'c'), (x + 10, -44, 'c')], 2), '#FFFFFF', lw=1.0,
          line='#B8902A')
    # 방울
    pp = []
    for i in range(16):
        a = math.radians(i * 22.5)
        r = 6.0 + (0.9 if i % 2 else 0)
        pp.append((x + math.cos(a) * r, -74 + math.sin(a) * r))
    F(ctx, 'hat', cr(pp, 3), '#FFF4D8', sd=(1.0, 1.2),
      shapes=[(ellipse(x - 2, -76, 2.2, 1.6, 10), '#FFFFFF', 0.9)])


# ------------------------------------------------------------------ 리본
def h_ribbon_pink(ctx):
    col = '#F58AB4'
    x = hx(ctx)
    bx, by = (x + 17, -60) if not ctx.back else (x - 17, -60)
    sgn = 1
    # 꼬리 (머리 뒤)
    for sx in (-1, 1):
        t = quad((bx, by), (bx + sx * 3.5 - ctx.sway, by + 9), (bx + sx * 5 - ctx.sway * 1.5, by + 17), 10)
        ctx.fig('hat_back' if not ctx.back else 'hat', H(ctx, taper(t, 4.0, 0.0, 0.15, 2.8)), col)
    for sx in (-1, 1):
        loop = cr([(bx, by), (bx + sx * 6, by - 7.5), (bx + sx * 11.5, by - 6.5), (bx + sx * 12, by + 1), (bx + sx * 6.5, by + 4.5)], 6)
        F(ctx, 'hat', loop, col, shapes=[(fold(quad((bx + sx * 2, by - 1), (bx + sx * 6, by - 3.4), (bx + sx * 9.5, by - 2.4), 8), 1.0),
                                           shade(col, 1.2), 0.85),
                                          (taper(quad((bx + sx * 4, by - 6), (bx + sx * 8, by - 7), (bx + sx * 10.5, by - 4.6), 8), 1.4, 0.3, 0.3),
                                           light(col, 0.7), 0.9)])
    F(ctx, 'hat', ellipse(bx, by, 3.2, 3.6, 14), shade(col, 0.8), shapes=[(ellipse(bx - 0.8, by - 1, 1.0, 1.0, 8), light(col), 0.9)])


# ------------------------------------------------------------------ 드롭: 달팽이 껍질
def h_snail_shell(ctx):
    col = '#5AA6EC'
    x = hx(ctx) * 0.5
    cx, cy = (x - 2, -58) if not ctx.q else (x - 6, -58)
    shell = cr([(cx - 30, -42, 'c'), (cx - 31, -55), (cx - 22, -71), (cx - 4, -77), (cx + 14, -74), (cx + 27, -63), (cx + 32, -48),
                (cx + 31, -42, 'c')], 7)
    sp = []
    for i in range(52):
        a = math.radians(-90 + i * 20)
        r = 19 * (1 - i / 56)
        sp.append((cx + 2 + math.cos(a) * r * 1.15, cy + math.sin(a) * r))
    spiral = taper(np.array(sp), 3.0, 0.05, 0.3, 0.5)
    shapes = [(spiral, deep(col, 1.0), 0.95),
              (taper(np.array(sp[:24]) + (-0.8, -1.2), 1.6, 0.2, 0.4), light(col, 0.9), 0.9),
              (taper(quad((cx - 22, -62), (cx - 12, -73), (cx + 2, -74.5), 10), 3.0, 0.3, 0.3), light(col, 1.0), 0.8)]
    F(ctx, 'hat', shell, col, shapes=shapes, sd=(1.8, 2.2))
    # 입구 테두리 (아래)
    lip = cr([(cx - 31, -45, 'c'), (cx, -48.5), (cx + 32, -45, 'c'), (cx + 32, -40.5, 'c'), (cx, -42.5), (cx - 31, -40.5, 'c')], 6)
    F(ctx, 'hat', lip, '#F2E2C2', shapes=[(fold(np.array([(cx - 28, -43), (cx + 28, -43)]), 0.5), '#C9A47A', 0.8)])
    brim_shadow(ctx, lip, dy=2.6, alpha=0.25)


# ------------------------------------------------------------------ 드롭: 골렘 투구
def h_golem_helm(ctx):
    st = '#B2A89A'
    moss = '#7FBF4A'
    x = hx(ctx) * 0.5
    helm = cr([(x - 33, -36, 'c'), (x - 34, -52), (x - 24, -68, 'c'), (x - 8, -73, 'c'), (x + 10, -73, 'c'), (x + 25, -67, 'c'),
               (x + 34, -52), (x + 33, -36, 'c'), (x + 25, -36, 'c'), (x + 24, -44), (x + 10, -46.5), (x - 10, -46.5), (x - 24, -44),
               (x - 25, -36, 'c')], 4)
    if ctx.back:
        helm = cr([(x - 33, -36, 'c'), (x - 34, -52), (x - 24, -68, 'c'), (x - 8, -73, 'c'), (x + 10, -73, 'c'), (x + 25, -67, 'c'),
                   (x + 34, -52), (x + 33, -36, 'c')], 4)
    shapes = [(fold(quad((x - 16, -66), (x - 12, -60), (x - 15, -54), 8), 1.0), '#6E6458', 0.9),
              (fold(quad((x + 18, -58), (x + 14, -54), (x + 16, -50), 8), 0.9), '#6E6458', 0.9),
              (fold(np.array([(x - 30, -52), (x + 30, -52)]), 0.8), '#7E7468', 0.6),
              (taper(quad((x - 22, -63), (x - 8, -71), (x + 8, -71), 10), 2.6, 0.3, 0.3), light(st, 0.7), 0.85)]
    F(ctx, 'hat', helm, st, shapes=shapes, sd=(1.6, 2.0))
    brim_shadow(ctx, helm, dy=2.6, alpha=0.22)
    # 이끼 + 새싹
    mp = cr([(x - 18, -69), (x - 10, -75), (x - 2, -73), (x + 6, -76), (x + 16, -71), (x + 12, -68.5), (x, -70), (x - 12, -67.5)], 5)
    F(ctx, 'hat', mp, moss, lw=1.6)
    st_ = quad((x + 2, -74), (x + 2.6, -79), (x + 1.2, -83), 8)
    F(ctx, 'hat', ribbon(st_, 1.4), '#5FA03A', lw=1.0)
    for sx in (-1, 1):
        leaf = cr([(x + 1.2, -83), (x + 1.2 + sx * 4, -87.5), (x + 1.2 + sx * 9, -86), (x + 1.2 + sx * 5, -82.5)], 5)
        F(ctx, 'hat', leaf, '#8ED45A', shapes=[(fold(np.array([(x + 1.2, -83), (x + 1.2 + sx * 7.5, -86)]), 0.5), '#5FA03A', 0.9)])
    # 이마 룬 보석
    if ctx.front:
        F(ctx, 'hat', cr([(x, -51, 'c'), (x + 3, -48, 'c'), (x, -45, 'c'), (x - 3, -48, 'c')], 3), '#6BD4E8', line='#2A6C82',
          shapes=[(ellipse(x - 0.8, -49, 0.8, 0.8, 8), '#E8FCFF')])


HATS = {
    'bucket-white': h_bucket_white, 'cap-black': h_cap_black, 'cap-white': h_cap_white,
    'mushroom-red': h_mushroom_red, 'explorer-brown': h_explorer_brown, 'beanie-yellow': h_beanie_yellow,
    'ribbon-pink': h_ribbon_pink,
    'snail-shell': h_snail_shell, 'mushroom-cap': h_mushroom_cap, 'golem-helm': h_golem_helm,
}
