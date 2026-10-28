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
    col = '#F2EFE8'
    x = hx(ctx)
    crown = cr([(x - 27, -44), (x - 26, -57), (x - 16, -67), (x, -69), (x + 16, -67), (x + 26, -57), (x + 27, -44)], 6)
    brim = cr([(x - 38, -36.5), (x - 31, -46), (x, -48.5), (x + 31, -46), (x + 38, -36.5), (x + 30, -33.5), (x, -35.5),
               (x - 30, -33.5)], 6)
    F(ctx, 'hat', crown, col, sd=(1.4, 1.8),
      shapes=[(fold(quad((x - 18, -49), (x - 15, -58), (x - 9, -64), 8), 1.0), shade(col, 1.0), 0.7),
              (fold(quad((x + 18, -49), (x + 16, -58), (x + 10, -64), 8), 1.0), shade(col, 1.0), 0.7),
              (taper(quad((x - 14, -63), (x - 4, -67.2), (x + 6, -65.5), 10), 2.2, 0.3, 0.3), '#FFFFFF', 0.9),
              (cr([(x - 27, -49, 'c'), (x + 27, -49, 'c'), (x + 27, -45.5, 'c'), (x - 27, -45.5, 'c')], 2), '#E6E0EE', 1.0)])
    stitches = [(taper(quad((x - 33, -38.6), (x, -42.8 + i * 2.2), (x + 33, -38.6), 16), 0.45, 0.05, 0.05), shade(col, 0.8), 0.9)
                for i in range(2)]
    F(ctx, 'hat', brim, col, shapes=stitches, sd=(1.0, 1.6))
    brim_shadow(ctx, brim)
    if not ctx.back:
        px, py = x + (14 if ctx.front else 13), -57
        sq = cr([(px - 3, py - 3, 'c'), (px + 3, py - 3, 'c'), (px + 3, py + 3, 'c'), (px - 3, py + 3, 'c')], 2)
        F(ctx, 'hat', sq, '#B9AED8', lw=1.2, line='#6E6490',
          shapes=[(ellipse(px - 1.2, py - 0.6, 0.5, 0.7, 8), '#6E6490'), (ellipse(px + 1.2, py - 0.6, 0.5, 0.7, 8), '#6E6490'),
                  (taper(quad((px - 1.4, py + 1.0), (px, py + 2.2), (px + 1.4, py + 1.0), 6), 0.6, 0.2, 0.2), '#6E6490')])


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
    cap(ctx, '#323036', logo_mush('#E9DCC3'), '#8A7A62')


def h_cap_white(ctx):
    cap(ctx, '#F2EFE8', logo_mush('#6E8DB5'), '#3E5270', bill='#E8E4DC')


# ------------------------------------------------------------------ 버섯 모자 (빨강) / 드롭 주황버섯
def mushroom(ctx, col, spot, under='#F2E6D4', tall=0.0, spots=None, eyes=False):
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
            F(ctx, 'hat', ellipse(x + sx * 8, -52, 1.6, 2.4, 12), '#4A3A30', lw=0.6, shd=False,
              shapes=[(ellipse(x + sx * 8 - 0.5, -53, 0.6, 0.7, 8), '#FFFFFF')])


def h_mushroom_red(ctx):
    mushroom(ctx, '#C9573F', '#FFFFFF')


def h_mushroom_cap(ctx):
    """드롭: 주황버섯 갓 모자 -> 크림 물방울 무늬의 주황 베레모 + 작은 꼭지."""
    col, spot = '#D98A4A', '#F2DDB8'
    x = hx(ctx) * 0.5
    ber = cr([(x - 35, -40), (x - 36, -50), (x - 24, -63), (x - 4, -68), (x + 18, -66), (x + 33, -57), (x + 37, -46),
              (x + 31, -40), (x + 12, -43.5), (x - 14, -43.5)], 7)
    sp = [(-24, -55, 3.4), (-8, -61, 3.8), (10, -61, 3.4), (25, -53, 3.0), (-30, -45, 2.4), (-14, -49, 2.6), (4, -50, 2.8),
          (20, -46, 2.4), (33, -47, 1.8)]
    shapes = [(ellipse(x + a, b_, r, r * 0.8, 16), spot, 1.0) for a, b_, r in sp]
    shapes.append((taper(quad((x - 26, -58), (x - 10, -66), (x + 8, -65.5), 10), 2.6, 0.3, 0.3), light(col, 0.6), 0.6))
    F(ctx, 'hat', ber, col, shapes=shapes, sd=(1.4, 1.8))
    band = cr([(x - 31, -41.5, 'c'), (x, -45.0), (x + 31, -41.5, 'c'), (x + 31, -38.0, 'c'), (x, -41.0), (x - 31, -38.0, 'c')], 6)
    F(ctx, 'hat', band, deep(col, 0.6))
    brim_shadow(ctx, band, dy=2.4, alpha=0.22)
    F(ctx, 'hat', cr([(x + 1, -67), (x + 1.5, -71.5), (x + 4, -72.5), (x + 4.6, -68)], 4), '#F2E6D4', lw=0.8)


# ------------------------------------------------------------------ 탐험가 모자
def h_explorer_brown(ctx):
    col = '#A8835E'
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
        F(ctx, 'hat', taper(fe, 4.2, 0.1, 0.5, 0.6), '#C9573F', shapes=[(taper(fe, 0.6, 0.1, 0.1), '#8E3E30', 0.9)])


# ------------------------------------------------------------------ 비니
def h_beanie_yellow(ctx):
    col = '#D9B05A'
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
          line='#9A7A3A')
    # 방울
    pp = []
    for i in range(16):
        a = math.radians(i * 22.5)
        r = 6.0 + (0.9 if i % 2 else 0)
        pp.append((x + math.cos(a) * r * 0.9, -72 + math.sin(a) * r * 0.85))
    F(ctx, 'hat', cr(pp, 3), '#F4EBD6', sd=(1.0, 1.2),
      shapes=[(ellipse(x - 2, -74, 2.0, 1.4, 10), '#FFFFFF', 0.6)])


# ------------------------------------------------------------------ 리본
def h_ribbon_pink(ctx):
    col = '#D99AA5'
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
    """드롭: 달팽이 껍질 모자 -> 소용돌이 패턴 버킷햇 + 꼭대기 더듬이 두 개."""
    col, ink = '#9DB4CB', '#5E7896'
    x = hx(ctx)
    crown = cr([(x - 27, -44), (x - 26, -57), (x - 16, -67), (x, -69), (x + 16, -67), (x + 26, -57), (x + 27, -44)], 6)
    brim = cr([(x - 38, -36.5), (x - 31, -46), (x, -48.5), (x + 31, -46), (x + 38, -36.5), (x + 30, -33.5), (x, -35.5),
               (x - 30, -33.5)], 6)

    def swirl(cx, cy, r, turns=2.2):
        pts = [(cx + math.cos(t) * r * (1 - t / (turns * 2 * math.pi + 1)) * 1.1,
                cy + math.sin(t) * r * (1 - t / (turns * 2 * math.pi + 1)))
               for t in np.linspace(0, turns * 2 * math.pi, 40)]
        return taper(np.array(pts), 1.2, 0.05, 0.3)
    # 더듬이 (모자 뒤)
    for sx in (-1, 1):
        st = quad((x + sx * 6, -66), (x + sx * 9, -71), (x + sx * 13, -73.5), 10)
        F(ctx, 'hat_back', ribbon(st, 1.6), '#C5D6AE', lw=0.8)
        F(ctx, 'hat_back', ellipse(x + sx * 13, -74, 2.0, 2.0, 12), '#C5D6AE', lw=0.8,
          shapes=[(ellipse(x + sx * 13.4, -74.1, 0.8, 0.9, 8), '#3A3436')])
    F(ctx, 'hat', crown, col, sd=(1.4, 1.8),
      shapes=[(swirl(x + a, b_, r), ink, 0.85) for a, b_, r in ((-14, -56, 5.5), (6, -61, 5.0), (18, -51, 4.4), (-2, -50, 3.6))]
      + [(taper(quad((x - 14, -63), (x - 4, -67.2), (x + 6, -65.5), 10), 2.0, 0.3, 0.3), '#FFFFFF', 0.5)])
    F(ctx, 'hat', brim, col, sd=(1.0, 1.6),
      shapes=[(taper(quad((x - 33, -38.6), (x, -42.8 + i * 2.2), (x + 33, -38.6), 16), 0.45, 0.05, 0.05), shade(col, 0.8), 0.9)
              for i in range(2)] + [(swirl(x + a, -39.5, 2.6, 1.6), ink, 0.75) for a in (-26, -12, 4, 20)])
    brim_shadow(ctx, brim)


def h_golem_helm(ctx):
    """드롭: 골렘 돌투구 -> 돌 무늬 꽈배기 니트 비니 + 이끼색 접단 + 새싹 핀."""
    st, moss = '#ABA59C', '#93AE6E'
    x = hx(ctx) * 0.4
    dome = cr([(x - 32, -45, 'c'), (x - 30, -58), (x - 18, -69), (x, -72), (x + 18, -69), (x + 30, -58), (x + 32, -45, 'c')], 6)
    cab = []
    for gx in (-18, -6, 6, 18):
        pts = []
        for i, yy in enumerate(np.linspace(-68, -48, 7)):
            pts.append((x + gx + (1.6 if i % 2 else -1.6), yy))
        cab.append((taper(cr(pts, 4, closed=False), 1.0, 0.1, 0.1), '#7E786E', 0.7))
    cab.append((taper(quad((x - 18, -64), (x - 8, -69.6), (x + 4, -69), 10), 2.2, 0.3, 0.3), light(st, 0.7), 0.55))
    F(ctx, 'hat', dome, st, shapes=cab, sd=(1.4, 1.8))
    cuff = cr([(x - 34, -50, 'c'), (x, -52.5), (x + 34, -50, 'c'), (x + 34.5, -41.5, 'c'), (x, -39.5), (x - 34.5, -41.5, 'c')], 6)
    F(ctx, 'hat', cuff, moss, shapes=[(fold(np.array([(x + gx, -50.5), (x + gx, -41)]), 0.8), shade(moss, 1.1), 0.7)
                                      for gx in np.linspace(-31, 31, 17)], sd=(1.0, 1.6))
    brim_shadow(ctx, cuff, dy=2.6, alpha=0.22)
    if not ctx.back:
        px = x + (16 if ctx.front else 18)
        F(ctx, 'hat', ribbon(quad((px, -46), (px + 0.6, -50), (px - 0.4, -54), 8), 1.2), '#6E8E4E', lw=0.7)
        for sx in (-1, 1):
            F(ctx, 'hat', cr([(px - 0.4, -54), (px - 0.4 + sx * 3.5, -57.5), (px - 0.4 + sx * 7, -56), (px - 0.4 + sx * 3.5, -53.5)], 5),
              '#A8C47E', lw=0.7)


HATS = {
    'bucket-white': h_bucket_white, 'cap-black': h_cap_black, 'cap-white': h_cap_white,
    'mushroom-red': h_mushroom_red, 'explorer-brown': h_explorer_brown, 'beanie-yellow': h_beanie_yellow,
    'ribbon-pink': h_ribbon_pink,
    'snail-shell': h_snail_shell, 'mushroom-cap': h_mushroom_cap, 'golem-helm': h_golem_helm,
}
