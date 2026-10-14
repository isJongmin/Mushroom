"""sample_v3: hoodie boy, 80x96 frames, foot anchor (40, 92).

Layers (composite order): hair_back, body, bottom, shoes, top, eyes, hair_front
Frames: front, side_idle, side_walk0..3, back

Run:  python3 build.py   ->  out/<frame>_<layer>.png, out/<frame>.png, out/sheet.png
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import (W, H, XX, YY, new, ell, poly, lines, rect, at, shift, edge,
                 dilate, put, sphere_light, band_shade, stamp, flip, offset,
                 over, to_img, to_txt)
from palette import (HAIR, SKIN, SKIN_FAR, TOP, TOP_FAR, DENIM, DENIM_FAR,
                     SHOE, SHOE_FAR)
import grids as G

ORDER = ['hair_back', 'body', 'bottom', 'shoes', 'top', 'eyes', 'hair_front']
FRAMES = ['front', 'side_idle', 'side_walk0', 'side_walk1', 'side_walk2',
          'side_walk3', 'back']
ANCHOR = (40, 92)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')


def mx(pts):
    """mirror points around the frame centre line (x=39.5)."""
    return [(79 - x, y) for x, y in pts]


# =================================================================== HAIR
def lumpy(cx, cy, rx, ry, bumps):
    """ellipse + small round lobes on its rim -> soft, clumpy silhouette.
    bumps: (angle_deg, radius) ; 0 = right, 90 = down (screen)."""
    m = ell(cx, cy, rx, ry)
    for a, r in bumps:
        t = np.radians(a)
        bx = cx + np.cos(t) * (rx - r * 0.6)
        by = cy + np.sin(t) * (ry - r * 0.6)
        m |= ell(bx, by, r, r)
    return m


def paint_hair(sil, cut, sph, strands, ring, ring2_xmax, wisps=()):
    """Render a full hair mass as one char layer.
    sil     : silhouette mask
    cut     : mask removed from silhouette (face window)
    sph     : (cx, cy, rx, ry) ellipsoid used for global light
    strands : polylines -> clump separators (deep line, shadow on its left)
    ring    : (cx, cy, rx, ry, xmax) highlight band ("angel ring") arc
    """
    m = sil & ~cut
    L = new()
    I = sphere_light(*sph)
    L[m] = 'c'
    L[m & (I < 0.12)] = 'd'
    L[m & (I < -0.18)] = 'e'
    # underside of every tip/lock is in shadow
    L[m & ~at(m, 0, 2) & (L == 'c')] = 'd'
    # clump separators
    sep = np.zeros_like(m)
    for pts in strands:
        sep |= lines(pts)
    sep &= m
    left = shift(sep, -1, 0) & m & ~sep
    L[left & (L == 'c')] = 'd'
    # highlight band: two staggered rows of short dashes (strand sheen)
    rcx, rcy, rrx, rry, xmax = ring
    r = np.sqrt(((XX + .5 - rcx) / rrx) ** 2 + ((YY + .5 - rcy) / rry) ** 2)
    band = m & (r >= 1.0) & (r < 1.0 + 2.6 / rry) & (YY < rcy) & (XX <= xmax)
    band &= ~sep & ~left & ~edge(m)
    zone = m & (r >= 0.80) & (r < 1.0 + 6.5 / rry) & (YY < rcy) & (I > 0.05) & ~edge(m)
    L[zone & (L == 'c')] = 'K'
    row = (YY % 2)
    dash = ((XX + 3 * row) % 6) < 4
    L[band & dash] = 'b'
    core = band & dash & (r < 1.0 + 1.3 / rry) & (XX <= ring2_xmax) & (((XX + 3 * row) % 6) >= 1) & (((XX + 3 * row) % 6) <= 2)
    L[core] = 'a'
    # lit edge of each clump just below the band
    streak = shift(sep, 1, 0) & m & ~sep & (r >= 1.0 + 2.6 / rry) & (r < 1.0 + 7.5 / rry) & (I > 0.25)
    L[streak] = 'b'
    L[sep & (r >= 1.0 + 2.6 / rry)] = 'e'
    L[sep & (r < 1.0 + 2.6 / rry) & np.isin(L, ['c', 'K', 'd'])] = 'd'
    L[edge(m)] = 'f'
    for pts in wisps:
        L[lines(pts) & ~m] = 'f'
    return L, m


def split(L, front_mask):
    hb, hf = new(), new()
    fm = front_mask & (L != '.')
    bm = ~front_mask & (L != '.')
    hf[fm] = L[fm]
    hb[bm] = L[bm]
    return hb, hf


def ahoge(L, pts):
    s = lines(pts)
    L[s] = 'f'


def face_shade(L, f, cheek):
    L[f] = 'h'
    L[f & ~at(f, 2, 0)] = 'i'          # far (right) side
    L[f & ~at(f, 0, 2)] = 'i'          # under the jaw
    L[f & (YY <= 36)] = 'i'            # forehead under the fringe
    L[f & ~at(f, 0, 1) & ~at(f, 2, 0)] = 'j'
    cx, cy = cheek
    L[f & ell(cx, cy, 2.5, 1.6)] = 'g'
    L[edge(f)] = 'k'


# =================================================================== FRONT
FACE_F = ell(39.5, 40, 20.5, 13.2) | ell(39.5, 46, 15.5, 9.6)


def hair_front_view():
    sil = lumpy(39.5, 29.5, 27.5, 22.5, [(-160, 4), (-128, 4), (-62, 4),
                                  (-30, 4), (0, 4), (180, 4)])
    for t in ([(12, 36), (12, 45), (15, 51), (17, 46), (20, 50), (22, 40)],
              [(67, 36), (67, 45), (64, 51), (62, 46), (59, 50), (57, 40)],
              [(11, 31), (9, 35), (12, 37)], [(68, 31), (70, 35), (67, 37)]):
        sil |= poly(t)
    win = poly([(21, 70), (21, 48), (22, 42), (23, 37), (25, 33), (27, 37),
                (29, 32), (31, 38), (34, 32), (36, 35), (38, 30), (41, 30),
                (43, 35), (45, 32), (48, 38), (50, 32), (52, 37), (54, 33),
                (56, 37), (57, 42), (58, 48), (58, 70)])
    cut = (win & FACE_F) | rect(20, 50, 59, 95)
    strands = [
        [(33, 15), (31, 24), (29, 31)],
        [(37, 14), (35, 24), (34, 31)],
        [(40, 16), (39, 24), (39, 29)],
        [(44, 15), (45, 25), (45, 31)],
        [(48, 15), (50, 25), (50, 31)],
        [(52, 17), (54, 25), (54, 32)],
        [(27, 15), (21, 23), (18, 33), (17, 44)],
        [(53, 15), (60, 23), (62, 33), (63, 44)],
        [(20, 20), (14, 29), (13, 37)],
        [(59, 19), (65, 28), (66, 36)],
        [(37, 9), (34, 12)], [(45, 9), (49, 12)],
    ]
    wisps = [[(57, 12), (61, 9), (64, 9)], [(66, 22), (70, 20), (72, 21)],
             [(13, 22), (9, 20)]]
    L, m = paint_hair(sil, cut, (36, 24, 31, 26), strands,
                      (40, 34, 24, 17, 54), 36, wisps)
    ahoge(L, [(40, 8), (39, 5), (41, 3), (44, 3), (46, 5)])
    front = dilate(FACE_F, 1) & (YY > 24)
    return split(L, front)


def body_front():
    L = new()
    # neck
    neck = rect(35, 50, 44, 57)
    band_shade(L, neck, SKIN_FAR, sh=None)
    # ears (behind face edge)
    stamp(L, G.EAR_FRONT, 15, 40)
    stamp(L, G.EAR_FRONT, 60, 40, mirror=True)
    # face
    face_shade(L, FACE_F, (25, 43))
    # blush
    stamp(L, G.BLUSH, 24, 47)
    stamp(L, G.BLUSH, 52, 47)
    # hands
    stamp(L, G.HAND_FRONT, 18, 70)
    stamp(L, G.HAND_FRONT, 56, 70, mirror=True)
    # legs
    for x0 in (30, 42):
        band_shade(L, rect(x0, 76, x0 + 7, 87), SKIN, sh=(2, 0))
    return L


def eyes_front():
    L = new()
    stamp(L, G.EYE_FRONT_L, 25, 37)
    stamp(L, G.EYE_FRONT_R, 47, 37)
    stamp(L, G.MOUTH_FRONT, 39, 50)
    return L


def top_front():
    L = new()
    torso = poly([(29, 53), (50, 53), (54, 57), (55, 75), (24, 75), (25, 57)])
    torso &= ~FACE_F
    band_shade(L, torso, TOP, sh=(3, 1), hl=(2, 2))
    # hem rib
    hem = torso & (YY >= 72)
    L[hem] = 'u'
    L[hem & (YY == 72)] = 'v'
    L[hem & (YY > 72) & (XX % 2 == 0)] = 'v'
    L[edge(torso) & hem] = 'x'
    L[edge(torso)] = 'x'
    # kangaroo pocket
    pk = poly([(31, 72), (33, 65), (46, 65), (48, 72)])
    L[pk & ~edge(pk)] = 'u'
    L[edge(pk) & (YY < 72)] = 'v'
    L[rect(33, 64, 46, 64)] = 's'
    # side folds
    for pts in ([(27, 61), (28, 66)], [(52, 61), (51, 66)], [(29, 69), (30, 71)]):
        L[lines(pts) & torso & ~edge(torso)] = 'v'
    # hood collar bunched around the neck
    for e in (ell(30.5, 55, 7.5, 3.6), ell(48.5, 55, 7.5, 3.6)):
        c = e & ~FACE_F
        band_shade(L, c, TOP, sh=(1, 2), hl=(1, 1))
    lining = poly([(35, 53), (44, 53), (41, 58), (38, 58)]) & ~FACE_F
    L[lining] = 'A'
    L[edge(lining) & (YY >= 57)] = 'x'
    # drawstrings
    for pts in ([(36, 57), (35, 66)], [(43, 57), (44, 66)]):
        s = lines(pts)
        L[s] = 'y'
        L[shift(s, 1, 0) & ~s & torso] = 'v'
    L[rect(35, 66, 35, 67)] = 'z'
    L[rect(44, 66, 44, 67)] = 'z'
    # sleeves
    sl = poly([(25, 56), (22, 58), (19, 64), (18, 71), (26, 71), (27, 63)])
    band_shade(L, sl, TOP, sh=(2, 1), hl=(1, 1))
    sr = poly(mx([(25, 56), (22, 58), (19, 64), (18, 71), (26, 71), (27, 63)]))
    band_shade(L, sr, TOP, sh=(2, 1), hl=(1, 1))
    for s in (sl, sr):
        cuff = s & (YY >= 69)
        L[cuff & ~edge(s)] = 'u'
        L[cuff & (YY == 69) & ~edge(s)] = 'v'
        L[lines([(20, 63), (23, 65)]) & s & ~edge(s)] = 'v'
        L[lines([(59, 63), (56, 65)]) & s & ~edge(s)] = 'v'
    return L


def bottom_front():
    L = new()
    sh = poly([(26, 73), (53, 73), (55, 84), (42, 84), (40, 79), (39, 79),
               (37, 84), (24, 84)])
    band_shade(L, sh, DENIM, sh=(2, 1), hl=(1, 1))
    cuff = sh & (YY >= 82)
    L[cuff & ~edge(sh)] = 'C'
    L[sh & (YY == 81) & ~edge(sh)] = 'E'
    L[lines([(39, 75), (39, 78)])] = 'E'
    for pts in ([(28, 79), (30, 79)], [(46, 78), (48, 78)], [(31, 80), (32, 80)]):
        L[lines(pts) & sh] = 'B'
    return L


def shoe_shape(x0):
    return (ell(x0 + 6.5, 90.5, 7, 6) | rect(x0, 90, x0 + 13, 92)) & (YY <= 92) & (YY >= 85)


def shoes_front():
    L = new()
    for x0, flipx in ((24, False), (42, True)):
        s = shoe_shape(x0)
        band_shade(L, s, SHOE, sh=(2, 1), hl=(1, 1))
        L[s & (YY >= 90) & ~edge(s)] = 'H'
        L[s & (YY == 91) & ~edge(s)] = 'I'
        L[s & (YY == 86) & (XX > x0 + 3) & (XX < x0 + 10)] = 'I'
        for xx in (x0 + 4, x0 + 6, x0 + 8):
            L[87, xx] = 'H'
    return L


# =================================================================== SIDE
FACE_S = ell(46.5, 42, 15.5, 13.6) | ell(54, 46, 7, 8)
FACE_S_VIS = FACE_S & (XX >= 41)


def hair_side_view():
    sil = lumpy(35.5, 28, 28, 21, [(-165, 4), (-130, 4), (-100, 3), (-65, 4),
                                  (-30, 4), (150, 4), (178, 4)])
    for t in ([(12, 34), (12, 45), (16, 52), (21, 50), (24, 54), (29, 50),
               (33, 54), (37, 48), (38, 36)],
              [(60, 22), (65, 25), (61, 28)],
              [(61, 29), (66, 33), (61, 35)],
              [(9, 28), (6, 33), (10, 35)]):
        sil |= poly(t)
    win = poly([(38, 70), (38, 48), (42, 47), (43, 41), (45, 35), (47, 38),
                (49, 32), (52, 37), (54, 32), (57, 37), (59, 33), (62, 36),
                (64, 35), (72, 35), (72, 70)])
    cut = (win & FACE_S) | rect(38, 55, 79, 95) | rect(0, 60, 79, 95)
    strands = [
        [(40, 14), (46, 20), (49, 26), (49, 32)],
        [(44, 14), (50, 19), (53, 25), (54, 32)],
        [(48, 14), (55, 18), (58, 25), (59, 33)],
        [(36, 15), (40, 22), (42, 30), (43, 40)],
        [(31, 16), (32, 26), (36, 36), (37, 46)],
        [(27, 16), (22, 24), (21, 34), (23, 44), (25, 51)],
        [(24, 15), (16, 21), (13, 30), (14, 40), (17, 49)],
        [(29, 20), (27, 32), (29, 42), (31, 50)],
        [(36, 9), (33, 12)], [(42, 9), (47, 11)],
    ]
    wisps = [[(53, 11), (57, 8), (60, 8)], [(9, 22), (5, 20)]]
    L, m = paint_hair(sil, cut, (31, 23, 31, 27), strands,
                      (34, 34, 25, 17, 50), 30, wisps)
    ahoge(L, [(37, 8), (36, 5), (38, 3), (41, 3), (43, 5)])
    front = dilate(FACE_S, 1) & (XX >= 41) & (YY > 24)
    return split(L, front)


def body_side_head():
    L = new()
    neck = rect(40, 50, 48, 58)
    band_shade(L, neck, SKIN_FAR, sh=None)
    face_shade(L, FACE_S_VIS, (57, 44))
    stamp(L, G.EAR_SIDE, 35, 39)
    stamp(L, G.BLUSH_SIDE, 53, 47)
    return L


def eyes_side():
    L = new()
    stamp(L, G.EYE_SIDE, 53, 37)
    stamp(L, G.MOUTH_SIDE, 56, 50)
    return L


def arm_side(L, ax, ramp, hand_ramp_far=False):
    """sleeve from shoulder (41,56) to hand at (41+ax, 71)."""
    hx = 41 + ax
    sl = poly([(37, 56), (44, 56), (45 + ax // 2, 63), (hx + 4, 70),
               (hx - 3, 71), (37 + ax // 3, 63)])
    band_shade(L, sl, ramp, sh=(2, 1), hl=(1, 1))
    L[sl & ~at(sl, -2, 0) & ~edge(sl) & (YY < 68)] = ramp['hl']   # rim light
    cuff = sl & (YY >= 68)
    L[cuff & ~edge(sl)] = ramp['sh']
    L[cuff & (YY == 68) & ~edge(sl)] = ramp['deep']
    L[lines([(39 + ax // 3, 62), (42 + ax // 2, 63)]) & sl & ~edge(sl)] = ramp['deep']
    return sl, hx


def top_side(near_ax, far_ax):
    L = new()
    # far arm (behind the torso)
    arm_side(L, far_ax + 3, TOP_FAR)
    # hood hanging on the back
    hood = poly([(27, 52), (38, 51), (40, 56), (37, 63), (29, 64), (25, 59)])
    torso = poly([(32, 53), (48, 53), (52, 57), (53, 75), (28, 75), (28, 58)])
    torso &= ~FACE_S
    band_shade(L, torso, TOP, sh=(3, 1), hl=(2, 2))
    hem = torso & (YY >= 72)
    L[hem] = 'u'
    L[hem & (YY == 72)] = 'v'
    L[hem & (YY > 72) & (XX % 2 == 0)] = 'v'
    L[edge(torso)] = 'x'
    pk = poly([(42, 72), (44, 65), (52, 65), (52, 72)]) & torso
    L[edge(pk) & (YY < 72) & ~edge(torso)] = 'v'
    # drawstring at the front
    s = lines([(47, 57), (48, 66)])
    L[s] = 'y'
    L[rect(48, 66, 48, 67)] = 'z'
    band_shade(L, hood & ~FACE_S, TOP, sh=(2, 2), hl=(1, 1))
    L[lines([(29, 56), (35, 55), (37, 58)]) & hood & ~edge(hood)] = 'v'
    collar = poly([(38, 54), (48, 53), (47, 57), (40, 58)]) & ~FACE_S
    L[collar & ~edge(collar)] = 'A'
    L[edge(collar) & (YY >= 56)] = 'x'
    near_sl, hx = arm_side(L, near_ax, TOP)
    return L, hx, torso


def leg_side(Lb, Ls, Lk, hx, fx, lift, near):
    """hip x hx, foot x fx (shoe heel side), lift = px off the ground."""
    dn = DENIM if near else DENIM_FAR
    sk = SKIN if near else SKIN_FAR
    so = SHOE if near else SHOE_FAR
    g = 92 - lift
    sx = hx + (fx - hx) * 0.55
    tube = poly([(hx - 7, 74), (hx + 7, 74), (sx + 6, 84), (sx - 6, 84)])
    band_shade(Lb, tube, dn, sh=(2, 1), hl=(1, 1))
    Lb[tube & (YY == 81) & ~edge(tube)] = dn['deep']
    shin = poly([(sx - 3, 83), (sx + 2, 83), (fx + 2, g - 5), (fx - 3, g - 5)])
    band_shade(Lk, shin, sk, sh=(2, 0))
    shoe = poly([(fx - 4, g - 7), (fx + 3, g - 7), (fx + 7, g - 4),
                 (fx + 9, g - 2), (fx + 9, g), (fx - 6, g), (fx - 6, g - 4)])
    band_shade(Ls, shoe, so, sh=(1, 2), hl=(1, 1))
    Ls[shoe & (YY == g - 1) & ~edge(shoe)] = so['deep']
    Ls[shoe & (YY == g - 2) & ~edge(shoe)] = so['sh']
    Ls[shoe & (YY == g - 6) & (XX < fx + 2) & ~edge(shoe)] = so['deep']
    for xx in (fx + 1, fx + 3):
        Ls[g - 5, int(xx)] = so['sh']


# =================================================================== BACK
def hair_back_view():
    sil = lumpy(39.5, 28.5, 28.5, 21, [(-160, 4), (-128, 4), (-100, 3), (-62, 4),
                                      (-30, 4), (0, 4), (180, 4)])
    for t in ([(14, 36), (15, 46), (18, 50), (21, 48), (24, 53), (28, 51),
               (31, 55), (34, 52), (36, 54), (39, 51), (43, 56), (46, 52),
               (50, 54), (53, 50), (57, 53), (59, 49), (62, 50), (65, 45), (66, 36)],
              [(11, 31), (9, 35), (12, 37)], [(68, 31), (70, 35), (67, 37)]):
        sil |= poly(t)
    cut = np.zeros((H, W), bool)
    strands = [
        [(40, 16), (36, 26), (33, 38), (33, 47), (33, 54)],
        [(43, 17), (44, 30), (43, 42), (43, 55)],
        [(46, 16), (50, 28), (52, 40), (51, 50)],
        [(38, 15), (30, 22), (25, 34), (25, 47)],
        [(48, 15), (57, 22), (60, 32), (58, 46)],
        [(36, 14), (24, 18), (17, 27), (16, 38)],
        [(50, 14), (61, 18), (66, 27), (65, 36)],
        [(29, 34), (29, 50)], [(38, 36), (37, 55)], [(48, 36), (47, 54)],
        [(55, 34), (55, 50)], [(20, 36), (20, 47)],
    ]
    wisps = [[(57, 12), (61, 9), (64, 9)], [(13, 22), (9, 20)]]
    L, m = paint_hair(sil, cut, (35, 24, 31, 28), strands,
                      (40, 30, 24, 16, 52), 34, wisps)
    # crown whorl
    L[lines([(40, 13), (42, 12), (45, 13), (45, 15), (43, 16)])] = 'e'
    ahoge(L, [(41, 8), (40, 5), (42, 3), (45, 3), (47, 5)])
    return new(), L


def body_back():
    L = new()
    stamp(L, G.EAR_FRONT, 14, 38)
    stamp(L, G.EAR_FRONT, 61, 38, mirror=True)
    stamp(L, G.HAND_FRONT, 18, 70)
    stamp(L, G.HAND_FRONT, 56, 70, mirror=True)
    for x0 in (30, 42):
        band_shade(L, rect(x0, 76, x0 + 7, 87), SKIN, sh=(2, 0))
    return L


def top_back():
    L = new()
    torso = poly([(29, 53), (50, 53), (54, 57), (55, 75), (24, 75), (25, 57)])
    band_shade(L, torso, TOP, sh=(3, 1), hl=(2, 2))
    hem = torso & (YY >= 72)
    L[hem] = 'u'
    L[hem & (YY == 72)] = 'v'
    L[hem & (YY > 72) & (XX % 2 == 0)] = 'v'
    L[edge(torso)] = 'x'
    hood = poly([(27, 51), (52, 51), (54, 57), (48, 65), (40, 67), (31, 65), (25, 57)])
    band_shade(L, hood, TOP, sh=(2, 2), hl=(1, 1))
    L[lines([(40, 55), (40, 66)]) & hood] = 'v'
    L[lines([(29, 59), (33, 63)]) & hood] = 'v'
    L[lines([(50, 59), (47, 63)]) & hood] = 'u'
    sl = poly([(25, 56), (22, 58), (19, 64), (18, 71), (26, 71), (27, 63)])
    sr = poly(mx([(25, 56), (22, 58), (19, 64), (18, 71), (26, 71), (27, 63)]))
    for s in (sl, sr):
        band_shade(L, s, TOP, sh=(2, 1), hl=(1, 1))
        cuff = s & (YY >= 69)
        L[cuff & ~edge(s)] = 'u'
        L[cuff & (YY == 69) & ~edge(s)] = 'v'
    return L


def bottom_back():
    L = new()
    sh = poly([(26, 73), (53, 73), (55, 84), (42, 84), (40, 79), (39, 79),
               (37, 84), (24, 84)])
    band_shade(L, sh, DENIM, sh=(2, 1), hl=(1, 1))
    L[sh & (YY >= 82) & ~edge(sh)] = 'C'
    L[sh & (YY == 81) & ~edge(sh)] = 'E'
    L[lines([(39, 75), (39, 79)])] = 'E'
    for x0 in (29, 43):
        p = rect(x0, 76, x0 + 6, 79)
        L[edge(p)] = 'E'
    return L


def shoes_back():
    L = new()
    for x0 in (24, 42):
        s = poly([(x0 + 1, 85), (x0 + 11, 85), (x0 + 12, 87), (x0 + 12, 92),
                  (x0 + 1, 92), (x0 + 1, 87)])
        band_shade(L, s, SHOE, sh=(2, 1), hl=(1, 1))
        L[s & (YY >= 89) & ~edge(s)] = 'I'
        L[s & (YY == 89) & ~edge(s)] = 'H'
        L[s & (YY == 86) & (XX > x0 + 3) & (XX < x0 + 9)] = 'I'
    return L


# =================================================================== BUILD
def build():
    frames = {}
    hb, hf = hair_front_view()
    frames['front'] = dict(hair_back=hb, body=body_front(), bottom=bottom_front(),
                           shoes=shoes_front(), top=top_front(), eyes=eyes_front(),
                           hair_front=hf)
    # ---- side
    shb, shf = hair_side_view()
    head = body_side_head()
    eyes = eyes_side()
    # (near foot x, far foot x, near lift, far lift, bob, near arm, far arm)
    poses = {
        'side_idle': (42, 37, 0, 0, 0, 0, 0),
        'side_walk0': (48, 31, 0, 0, 1, -5, 4),
        'side_walk1': (41, 38, 0, 2, 0, -1, 1),
        'side_walk2': (32, 47, 0, 0, 1, 5, -4),
        'side_walk3': (38, 41, 2, 0, 0, 1, -1),
    }
    for name, (nf, ff, nl, fl, bob, na, fa) in poses.items():
        top, hx, torso = top_side(na, fa)
        body = head.copy()
        far_hand = new()
        stamp(far_hand, G.HAND_SIDE, 41 + fa + 3 - 2, 70)
        body = over(far_hand, body)
        # the top layer leaves holes where the hands must show through
        top[(far_hand != '.') & ~torso] = '.'
        body_up = offset(body, 0, bob)
        top_up = offset(top, 0, bob)
        # near hand drawn on top layer region? keep in body: under the sleeve
        hand = new()
        stamp(hand, G.HAND_SIDE, hx - 2, 70)
        top[hand != '.'] = '.'
        top_up = offset(top, 0, bob)
        Lb, Ls, Lk = new(), new(), new()
        leg_side(Lb, Ls, Lk, 38, ff, fl, near=False)
        Lb2, Ls2, Lk2 = new(), new(), new()
        leg_side(Lb2, Ls2, Lk2, 43, nf, nl, near=True)
        # shorts seat
        seat = poly([(29, 73), (52, 73), (52, 77), (29, 77)])
        Ls_ = new()
        band_shade(Ls_, seat, DENIM, sh=(2, 1), hl=(1, 1))
        bottom = over(offset(Lb, 0, 0), offset(Lb2, 0, 0))
        bottom = over(bottom, offset(Ls_, 0, bob))
        body_full = over(Lk, Lk2, body_up, offset(hand, 0, bob))
        frames[name] = dict(hair_back=offset(shb, 0, bob), body=body_full,
                            bottom=bottom, shoes=over(Ls, Ls2), top=top_up,
                            eyes=offset(eyes, 0, bob), hair_front=offset(shf, 0, bob))
    # ---- back
    bhb, bhf = hair_back_view()
    frames['back'] = dict(hair_back=bhb, body=body_back(), bottom=bottom_back(),
                          shoes=shoes_back(), top=top_back(), eyes=new(),
                          hair_front=bhf)
    return frames


def save(frames):
    os.makedirs(OUT, exist_ok=True)
    from PIL import Image
    sheet = Image.new('RGBA', (W * len(FRAMES), H), (0, 0, 0, 0))
    layer_sheets = {k: Image.new('RGBA', (W * len(FRAMES), H), (0, 0, 0, 0)) for k in ORDER}
    for i, fn in enumerate(FRAMES):
        fr = frames[fn]
        comp = over(*[fr[k] for k in ORDER])
        to_img(comp).save(os.path.join(OUT, f'{fn}.png'))
        sheet.paste(to_img(comp), (i * W, 0))
        for k in ORDER:
            layer_sheets[k].paste(to_img(fr[k]), (i * W, 0))
    sheet.save(os.path.join(OUT, 'sheet.png'))
    for k, im in layer_sheets.items():
        im.save(os.path.join(OUT, f'layer_{k}.png'))
    # text dump of composites for diffing
    with open(os.path.join(OUT, 'sheet.txt'), 'w') as f:
        for fn in FRAMES:
            f.write(f'# {fn}\n')
            f.write(to_txt(over(*[frames[fn][k] for k in ORDER])))


if __name__ == '__main__':
    fr = build()
    save(fr)
    print('ok')
