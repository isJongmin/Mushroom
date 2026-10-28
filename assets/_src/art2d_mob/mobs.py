"""몬스터 5종 그림 정의. 좌표는 월드 단위, 원점 = 발 바닥 중앙, 오른쪽을 본다.

draw(c, mode, t): mode = move | hit | dead, t = 0..1 위상(move).
"""
import math

import numpy as np

from vec import (Mat, hx, mix, tone, ellipse, polar, path, bez, star, rrect, xform,
                 eye, blush, ground_shadow, INK, WHITE)

TAU = 2 * math.pi


def mouth_smile(c, x, y, w, col, lw=1.3, open_=False, tongue=True):
    if open_:
        p = path((x - w, y), [((x - w * 0.6, y + w * 1.3), (x + w * 0.6, y + w * 1.3), (x + w, y)),
                              ((x + w * 0.3, y + w * 0.2), (x - w * 0.3, y + w * 0.2), (x - w, y))], n=10)
        c.part(p, Mat('#7A2E3A', line=col), ol=0.7, shade=None)
        if tongue:
            m = c.mask(p)
            c.fill(ellipse(x + w * 0.1, y + w * 0.85, w * 0.55, w * 0.38), hx('#FF7E8E'), clip=m)
    else:
        c.line(bez((x - w, y - w * 0.1), (x - w * 0.4, y + w * 0.7), (x + w * 0.4, y + w * 0.7), (x + w, y - w * 0.1), 10),
               col, lw)


# ======================================================================== snail
SNAIL_BODY = Mat('#FFE6A8', sh='#F2BC78', hl='#FFF8E0', line='#9C5A2A')
SNAIL_SHELL = Mat('#5FA8E8', sh='#3C78C4', hl='#BFE4FF', line='#1E3A7A')
SNAIL_BAND = Mat('#9CD2FF', sh='#7AB4EE', line='#1E3A7A')


def snail(c, mode='move', t=0.0):
    st = math.sin(TAU * t)              # 몸 늘었다 줄었다
    cs = math.cos(TAU * t)
    lean = 0.0
    head_dx, head_dy, ant = 1.6 * st, 0.0, 0.18 * cs
    shell_dx, shell_dy, shell_rot = 0.4 * st, -0.5 * max(0, cs), 0.03 * st
    front = 15.5 + 2.2 * st
    rear = -23.5 + 1.0 * st
    emode = 'open'
    if mode == 'hit':
        head_dx, head_dy, ant = -4.0, 2.0, -0.5
        shell_rot, shell_dx, shell_dy = -0.12, -1.0, -1.5
        front, rear = 12.0, -22.0
        emode = 'hit'
    elif mode == 'dead':
        head_dx, head_dy, ant = 0.5, 5.0, -1.1
        shell_rot, shell_dx, shell_dy = -0.25, -1.5, 0.5
        front, rear = 16.5, -24.0
        emode = 'dead'

    ground_shadow(c, 23, 3.0, a=0.22)
    # 몸통(발) + 머리를 하나의 실루엣으로
    hx_, hy_ = 13.5 + head_dx, -12.5 + head_dy
    foot = path((rear, -1.0), [((rear + 12, 0.5), (front - 12, 0.5), (front, 0.0)),
                               ((front + 4, -0.4), (front + 3.5, -7.5), (hx_ - 1, -8.5 + head_dy * 0.5)),
                               ((4, -8.0), (-10, -6.0), (rear, -1.0))])
    head = ellipse(hx_, hy_, 7.6, 9.2, rot=0.12 if mode != 'dead' else 0.5)
    # 더듬이(머리 뒤)
    for i, (bx, ang0) in enumerate(((-2.2, -1.95), (2.6, -1.35))):
        a = ang0 + ant * (1 if i else 0.7)
        L = 8.0 if mode != 'dead' else 6.5
        x0, y0 = hx_ + bx, hy_ - 6.5
        x1, y1 = x0 + L * math.cos(a), y0 + L * math.sin(a)
        mx_, my_ = (x0 + x1) / 2 + 1.2, (y0 + y1) / 2
        c.line(bez((x0, y0), (mx_, my_), (mx_, my_), (x1, y1), 10), SNAIL_BODY.line, 3.6)
        c.line(bez((x0, y0), (mx_, my_), (mx_, my_), (x1, y1), 10), SNAIL_BODY.sh, 1.6)
        c.part(ellipse(x1, y1, 2.0, 2.0, n=24), SNAIL_BODY, ol=1.2, shade=(-0.5, -0.5), hl=ellipse(x1 - 0.5, y1 - 0.6, 0.8, 0.7))
    c.part([foot, head], SNAIL_BODY, ol=2.0, shade=(-1.2, -2.2), shade_sc=1.0,
           hl=[ellipse(hx_ - 2.5, hy_ - 4.5, 2.6, 1.8, rot=-0.5)], hl_a=0.95)
    # 발 밑 주름
    for xx in (-16, -9, -2):
        c.line(np.array([(xx + 0.6 * st, -0.6), (xx + 1.6 + 0.6 * st, -2.8)]), SNAIL_BODY.sh, 1.1)

    # 껍데기
    c.push(dx=shell_dx, dy=shell_dy, rot=shell_rot, ox=-5, oy=-3)
    sx_, sy_, r = -5.0, -14.0, 12.6
    shell = polar(sx_, sy_, lambda th: (r * (1.0 + 0.04 * math.cos(th)), r * 0.98))
    m = c.part(shell, SNAIL_SHELL, ol=2.1, shade=(-2.0, -2.6), shade_sc=0.98, sh2=(-0.6, -0.8), ret=True)
    # 나선 무늬(밝은 띠 + 진한 선)
    sp = []
    for i in range(80):
        u = i / 79
        a = -0.6 + u * 2.25 * TAU
        rr = 1.0 + u * 9.8
        sp.append((sx_ + 1.0 + rr * math.cos(a), sy_ + 0.6 + rr * math.sin(a)))
    sp = np.array(sp[::-1])
    c.line(sp, SNAIL_BAND.base, 3.6, clip=m)
    c.line(sp, SNAIL_SHELL.line, 1.3, clip=m)
    c.fill(ellipse(sx_ - 5.0, sy_ - 6.5, 3.2, 1.9, rot=-0.6), SNAIL_SHELL.hl, 0.95, clip=m)
    c.fill(ellipse(sx_ - 8.5, sy_ - 2.5, 1.0, 1.0), WHITE, 0.9, clip=m)
    c.pop()

    # 얼굴
    ex, ey = hx_ + 2.2, hy_ - 0.6
    if emode == 'open':
        eye(c, ex - 2.6, ey, 1.75, 2.6)
        eye(c, ex + 2.4, ey, 1.55, 2.5)
    else:
        eye(c, ex - 2.6, ey, 1.9, 1.9, emode)
        eye(c, ex + 2.5, ey, 1.8, 1.8, 'hitL' if emode == 'hit' else emode)
    blush(c, ex - 3.4, ey + 3.4, 1.7, 1.0)
    blush(c, ex + 4.2, ey + 3.4, 1.2, 0.9)
    if mode == 'hit':
        mouth_smile(c, ex + 0.2, ey + 4.6, 1.2, SNAIL_BODY.line, open_=True, tongue=False)
    elif mode == 'dead':
        c.line(bez((ex - 1.4, ey + 4.8), (ex - 0.5, ey + 4.0), (ex + 0.5, ey + 5.6), (ex + 1.4, ey + 4.8), 8), SNAIL_BODY.line, 1.1)
    else:
        mouth_smile(c, ex + 0.1, ey + 3.9, 1.1, SNAIL_BODY.line, lw=1.1)


# ======================================================================== mushroom (주황버섯)
MUSH_CAP = Mat('#FF9638', sh='#E8641E', hl='#FFD49A', line='#8C3410')
MUSH_SPOT = Mat('#FFF0D2', sh='#F6D2A4', line='#C26A2A')
MUSH_STEM = Mat('#FFF2DC', sh='#EECB9C', hl='#FFFFFF', line='#94603A')
MUSH_GILL = hx('#E2B07A')

HOP6 = [  # (y, sx, sy, cap_rot)  땅 짓눌림 -> 도약 -> 정점 -> 낙하 -> 착지 -> 회복
    (0.0, 1.14, 0.84, 0.00),
    (-7.0, 0.92, 1.12, -0.03),
    (-15.0, 0.98, 1.04, -0.05),
    (-10.0, 0.95, 1.08, 0.03),
    (0.0, 1.16, 0.82, 0.04),
    (0.0, 1.02, 0.98, 0.0),
]


def _hop(t):
    i = int(round(t * 6)) % 6
    return HOP6[i]


def mushroom(c, mode='move', t=0.0):
    y, sx, sy, crot = _hop(t)
    emode = 'open'
    tilt = 0.0
    if mode == 'hit':
        y, sx, sy, crot, tilt = 0.0, 0.96, 1.02, -0.18, -0.16
        emode = 'hit'
    elif mode == 'dead':
        y, sx, sy, crot, tilt = 0.0, 1.12, 0.84, 0.32, 0.10
        emode = 'dead'
    ground_shadow(c, 18 * (1 - abs(y) / 40), 3.2 * (1 - abs(y) / 40), a=0.24)
    c.push(dy=y, sx=sx, sy=sy, rot=tilt, ox=0, oy=0)
    # 기둥(얼굴)
    stem = path((0, 0.0), [((9, 0.0), (13.5, -2.0), (13.0, -10.0)),
                           ((12.6, -17.0), (10.0, -24.0), (8.5, -26.0)),
                           ((3, -27.0), (-3, -27.0), (-8.5, -26.0)),
                           ((-10.0, -24.0), (-12.6, -17.0), (-13.0, -10.0)),
                           ((-13.5, -2.0), (-9, 0.0), (0, 0.0))])
    m = c.part(stem, MUSH_STEM, ol=2.0, shade=(-2.0, -1.6), shade_sc=0.97, ret=True,
               hl=[ellipse(-7.0, -14.0, 2.0, 4.5, rot=0.15)], hl_a=0.7)
    # 갓 아래 그늘 띠
    c.fill(ellipse(0, -24.5, 15, 5.0), MUSH_GILL, 0.55, clip=m)
    # 얼굴
    ex, ey = 3.4, -12.5
    if emode == 'open':
        eye(c, ex, ey, 2.5, 3.5)
        eye(c, ex + 6.4, ey, 2.2, 3.4)
        # 귀여운 눈썹(살짝 심통)
        c.line(np.array([(ex - 2.4, ey - 5.6), (ex + 1.8, ey - 4.8)]), MUSH_STEM.line, 1.4)
        c.line(np.array([(ex + 4.8, ey - 4.8), (ex + 8.4, ey - 5.6)]), MUSH_STEM.line, 1.4)
        mouth_smile(c, ex + 3.3, ey + 5.2, 1.6, MUSH_STEM.line, open_=int(round(t * 6)) % 6 in (1, 2))
    else:
        eye(c, ex, ey, 2.4, 2.4, emode)
        eye(c, ex + 6.4, ey, 2.2, 2.2, 'hitL' if emode == 'hit' else emode)
        if mode == 'hit':
            mouth_smile(c, ex + 3.3, ey + 5.0, 1.7, MUSH_STEM.line, open_=True, tongue=False)
        else:
            c.line(bez((ex + 1.3, ey + 5.6), (ex + 2.6, ey + 4.4), (ex + 4.0, ey + 6.6), (ex + 5.3, ey + 5.4), 8), MUSH_STEM.line, 1.2)
    blush(c, ex - 2.2, ey + 4.0, 2.2, 1.2)
    blush(c, ex + 9.0, ey + 4.0, 1.6, 1.1)

    # 갓
    c.push(rot=crot, ox=0, oy=-24)
    cap = path((-25.5, -22.0), [((-26.5, -34.0), (-15.0, -47.5), (1.0, -47.5)),
                                ((17.0, -47.5), (27.5, -35.0), (26.0, -22.0)),
                                ((22.0, -18.0), (14.0, -21.2), (0.0, -21.2)),
                                ((-14.0, -21.2), (-22.0, -18.0), (-25.5, -22.0))])
    cm = c.part(cap, MUSH_CAP, ol=2.2, shade=(-2.6, -3.0), shade_sc=0.98, sh2=(-0.8, -1.0), ret=True,
                hl=[ellipse(-11, -40.5, 6.0, 2.6, rot=-0.45)], hl_a=0.95)
    # 무늬 점(갓 곡면 따라)
    for (px_, py_, r_, rot_) in ((-14.0, -31.0, 4.4, -0.3), (2.0, -38.5, 5.4, 0.0), (15.5, -30.0, 3.8, 0.35),
                                 (-3.0, -27.5, 2.6, 0.0), (21.0, -24.5, 2.0, 0.5)):
        sp = ellipse(px_, py_, r_, r_ * 0.78, rot_, n=40)
        c.part(sp, MUSH_SPOT, ol=0.0, shade=(-0.7, -0.9), clip=cm)
    c.fill(ellipse(-15.5, -42.0, 1.3, 1.0), WHITE, 0.95, clip=cm)
    c.pop()
    c.pop()


# ======================================================================== slime
SLIME = Mat('#86DC5C', sh='#50B44A', hl='#E4FFC8', line='#22703A')
SLIME_IN = hx('#B4F08A')

SLIME6 = [  # (y, sx, sy, tip_lean)
    (0.0, 1.20, 0.80, 0.10),
    (-6.0, 0.88, 1.16, -0.18),
    (-13.0, 0.97, 1.05, -0.05),
    (-8.0, 0.93, 1.10, 0.12),
    (0.0, 1.24, 0.76, 0.22),
    (0.0, 1.06, 0.94, -0.06),
]


def slime(c, mode='move', t=0.0):
    i = int(round(t * 6)) % 6
    y, sx, sy, lean = SLIME6[i]
    emode = 'open'
    tilt = 0.0
    if mode == 'hit':
        y, sx, sy, lean, tilt = 0.0, 0.9, 1.06, -0.45, -0.12
        emode = 'hit'
    elif mode == 'dead':
        y, sx, sy, lean, tilt = 0.0, 1.32, 0.66, 0.6, 0.0
        emode = 'dead'
    ground_shadow(c, 21 * (1 - abs(y) / 40), 3.4 * (1 - abs(y) / 40), a=0.24)
    sub = c.blank()
    sub.push(dy=y, sx=sx, sy=sy, rot=tilt, ox=0, oy=0)

    def bfn(th):
        s = math.sin(th)
        rx = 21.5 * (1 + 0.04 * math.cos(2 * th))
        ry = 15.0 if s < 0 else 15.0 * (1 - 0.25 * s ** 4)
        return rx, ry
    blob = polar(0, -14.2, bfn)
    blob[:, 1] = np.minimum(blob[:, 1], -0.2)
    # 물방울 꼭지(살짝 휘어짐)
    L = lean
    tip = path((-8.5, -26.0), [((-6.0, -31.0), (-1.0 + L * 6, -33.5), (2.0 + L * 9, -38.5)),
                               ((3.5 + L * 10, -40.5), (6.0 + L * 9, -38.0), (5.0 + L * 7, -35.0)),
                               ((4.2 + L * 5, -31.5), (7.0, -29.0), (9.5, -26.0))], n=14)
    m = sub.part([blob, tip], SLIME, ol=2.2, shade=(-2.6, -3.2), shade_sc=0.97, ret=True, sh2=(-0.8, -1.0))
    # 젤리 속 밝은 부분 + 기포
    sub.fill(ellipse(-3, -9.0, 14.0, 6.5), SLIME_IN, 0.55, clip=m)
    for (bx, by, br) in ((-12.0, -10.0, 1.9), (-8.6, -6.0, 1.1), (13.5, -6.5, 1.3)):
        sub.line(ellipse(bx, by, br, br, n=24), mix(SLIME.hl, WHITE, 0.4), 0.9, closed=True, clip=m)
    sub.fill(ellipse(-11.5, -21.5, 4.6, 2.4, rot=-0.55), SLIME.hl, 0.95, clip=m)
    sub.fill(ellipse(1.2 + L * 7, -34.5, 1.0, 1.8, rot=0.4), SLIME.hl, 0.9, clip=m)
    sub.fill(ellipse(-15.5, -16.5, 1.1, 1.1), WHITE, 0.95, clip=m)
    # 얼굴
    ex, ey = 3.8, -14.5
    if emode == 'open':
        eye(sub, ex, ey, 2.7, 3.8, col=hx('#1C2A22'))
        eye(sub, ex + 7.4, ey, 2.4, 3.7, col=hx('#1C2A22'))
        mouth_smile(sub, ex + 3.7, ey + 5.6, 1.9, SLIME.line, open_=True)
    else:
        eye(sub, ex, ey, 2.6, 2.6, emode, col=hx('#1C2A22'))
        eye(sub, ex + 7.4, ey, 2.4, 2.4, 'hitL' if emode == 'hit' else emode, col=hx('#1C2A22'))
        if mode == 'hit':
            mouth_smile(sub, ex + 3.7, ey + 5.6, 1.8, SLIME.line, open_=True, tongue=False)
        else:
            sub.line(bez((ex + 1.5, ey + 6.0), (ex + 3.0, ey + 4.8), (ex + 4.5, ey + 7.0), (ex + 6.0, ey + 5.8), 8), SLIME.line, 1.2)
    blush(sub, ex - 2.6, ey + 4.6, 2.3, 1.2, a=0.5)
    blush(sub, ex + 10.6, ey + 4.6, 1.7, 1.1, a=0.5)
    sub.pop()
    c.over(sub, 0.96)   # 살짝 비치는 젤리


# ======================================================================== bat
BAT = Mat('#9A78D6', sh='#6E4EB0', hl='#D2C0F6', line='#33205E')
BAT_WING = Mat('#6C4CA6', sh='#4E3488', hl='#9C82D4', line='#2A1850')
BAT_INNER = hx('#F2B8D8')
BAT_BELLY = Mat('#E4D6FA', sh='#C7B4EE', line='#33205E')

BAT4 = [  # (wing angle, body y, wing fold)
    (0.95, -1.5, 0.95),
    (0.25, 0.0, 1.0),
    (-0.55, 1.5, 0.85),
    (0.25, 0.0, 1.0),
]


def _wing(side, ang, fold, cy):
    """side=+1 오른쪽, -1 왼쪽. 어깨 기준 회전. 아래 가장자리는 부채꼴 3개."""
    sh = (7.5, cy - 2.0)
    pts = [(0, 0), (6, -6), (15, -9), (25, -8)]             # 윗변(뼈대)
    tipx, tipy = 26.5, -6.0
    edge = [(tipx, tipy)]
    # 부채꼴 아래 가장자리: 끝 -> 몸쪽
    nodes = [(26.5, -6.0), (19.0, 3.0), (11.0, 6.5), (3.0, 7.0)]
    for (x0, y0), (x1, y1) in zip(nodes[:-1], nodes[1:]):
        mx_, my_ = (x0 + x1) / 2, (y0 + y1) / 2
        nx_, ny_ = -(y1 - y0), (x1 - x0)
        n = math.hypot(nx_, ny_)
        k = -2.8  # 안쪽으로 오목
        cxp, cyp = mx_ + nx_ / n * k, my_ + ny_ / n * k
        for i in range(1, 9):
            u = i / 8
            edge.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cxp + u * u * x1,
                         (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cyp + u * u * y1))
    top = bez((0, 0), (5, -9), (17, -12.5), (tipx, tipy), 16)
    poly = np.concatenate([top, np.array(edge[1:])], 0)
    poly[:, 0] *= fold
    c_, s_ = math.cos(-ang), math.sin(-ang)
    x, y = poly[:, 0], poly[:, 1]
    rx, ry = x * c_ - y * s_, x * s_ + y * c_
    ry = ry * (0.75 + 0.25 * math.cos(ang))
    out = np.stack([sh[0] * side + rx * side, sh[1] + ry], 1)
    bones = []
    for (bx, by) in ((19.0, 3.0), (11.0, 6.5)):
        bx *= fold
        bxr, byr = bx * c_ - by * s_, (bx * s_ + by * c_) * (0.75 + 0.25 * math.cos(ang))
        bones.append(np.array([(sh[0] * side, sh[1]), (sh[0] * side + bxr * 0.8 * side, sh[1] + byr * 0.8)]))
    return out, bones


def bat(c, mode='move', t=0.0):
    i = int(round(t * 4)) % 4
    ang, by, fold = BAT4[i]
    emode = 'open'
    tilt = 0.0
    if mode == 'hit':
        ang, by, fold, tilt = 0.6, -1.0, 0.8, -0.2
        emode = 'hit'
    elif mode == 'dead':
        ang, by, fold, tilt = -0.9, 2.0, 0.7, 0.35
        emode = 'dead'
    cy = -13.0 + by
    c.push(rot=tilt, ox=0, oy=cy)
    # 날개(뒤쪽 = 왼쪽 먼저, 살짝 어둡게)
    for side in (-1, 1):
        w, bones = _wing(side, ang, fold * (0.9 if side < 0 else 1.0), cy)
        mat = BAT_WING if side > 0 else Mat(tone(BAT_WING.base, 0.88), sh=tone(BAT_WING.sh, 0.88), hl=BAT_WING.hl, line=BAT_WING.line)
        m = c.part(w, mat, ol=1.9, shade=(0, -2.2 if ang >= 0 else 2.2), shade_sc=0.96, ret=True)
        for b in bones:
            c.line(b, mat.line, 1.1, clip=m)
    # 귀
    for ex_, lean in ((-5.5, -0.25), (5.0, 0.15)):
        ear = path((ex_ - 4.2, cy - 6.0), [((ex_ - 4.0 + lean * 4, cy - 12.0), (ex_ - 1.0 + lean * 6, cy - 16.5), (ex_ + lean * 8, cy - 19.0)),
                                           ((ex_ + 2.0 + lean * 6, cy - 15.0), (ex_ + 4.5, cy - 11.0), (ex_ + 4.0, cy - 6.0))], n=12)
        em = c.part(ear, BAT, ol=1.9, shade=(-0.8, -0.8), ret=True)
        c.fill(xform(ear, sx=0.5, sy=0.6, ox=ex_ + lean * 2, oy=cy - 7.5), BAT_INNER, 0.9, clip=em)
    # 몸
    body = polar(0.5, cy, lambda th: (12.0, 11.0 * (1 + 0.04 * math.sin(th))))
    bm = c.part(body, BAT, ol=2.0, shade=(-2.0, -2.4), shade_sc=0.97, ret=True,
                hl=[ellipse(-5.5, cy - 6.5, 3.4, 2.0, rot=-0.5)])
    c.part(ellipse(2.0, cy + 6.0, 6.5, 4.5), BAT_BELLY, ol=0, shade=(-0.8, -1.0), clip=bm)
    # 발톱
    for fx_ in (-3.0, 3.5):
        c.part(ellipse(fx_, cy + 11.2, 1.8, 1.4), Mat('#5C3E86', line='#2A1850'), ol=1.0, shade=None)
    # 얼굴
    ex, ey = 3.0, cy - 1.5
    if emode == 'open':
        eye(c, ex, ey, 2.4, 3.2)
        eye(c, ex + 6.2, ey, 2.1, 3.1)
        c.line(np.array([(ex + 1.4, ey + 4.4), (ex + 3.1, ey + 5.6), (ex + 4.8, ey + 4.4)]), BAT.line, 1.1)
        # 송곳니
        for fx_ in (ex + 4.0,):
            c.part(np.array([(fx_ - 0.9, ey + 4.9), (fx_ + 0.9, ey + 4.4), (fx_ + 0.2, ey + 6.9)]), Mat('#FFFFFF', line='#33205E'), ol=0.5, shade=None)
    else:
        eye(c, ex, ey, 2.3, 2.3, emode)
        eye(c, ex + 6.2, ey, 2.1, 2.1, 'hitL' if emode == 'hit' else emode)
        if mode == 'hit':
            mouth_smile(c, ex + 3.1, ey + 4.8, 1.4, BAT.line, open_=True, tongue=False)
        else:
            c.line(bez((ex + 1.2, ey + 5.0), (ex + 2.4, ey + 4.0), (ex + 3.8, ey + 6.0), (ex + 5.0, ey + 5.0), 8), BAT.line, 1.1)
    blush(c, ex - 2.4, ey + 3.6, 2.0, 1.1, a=0.5)
    blush(c, ex + 8.6, ey + 3.6, 1.5, 1.0, a=0.5)
    c.pop()


# ======================================================================== golem
STONE = Mat('#BDB6CC', sh='#8E86A4', hl='#E8E4F2', line='#433C58')
STONE_D = Mat('#A69EB8', sh='#7C7494', hl='#D2CCE0', line='#3A3450')
MOSS = Mat('#8CCB5A', sh='#5E9E3E', hl='#CBF08C', line='#2E5A26')
CRACK = hx('#6A6282')
RUNE = hx('#7FE7FF')


def _rock(cx, cy, rx, ry, seed, lump=0.06, n=60):
    """조금 울퉁불퉁한 둥근 바위(결정적 위상)."""
    return polar(cx, cy, lambda th: (rx * (1 + lump * math.sin(3 * th + seed) + lump * 0.6 * math.sin(5 * th + seed * 2.1)),
                                     ry * (1 + lump * math.sin(3 * th + seed) + lump * 0.6 * math.sin(5 * th + seed * 2.1))), n)


def _moss(c, pts_base, clip):
    pass


def golem(c, mode='move', t=0.0):
    ph = TAU * (t + 0.125)
    s = math.sin(ph)
    bob = -1.6 * abs(math.cos(ph))   # 발 디딜 때 아래
    legL = (-15.0 + 4.5 * s, -5.5 * max(0, -s))   # (x, lift)
    legR = (14.0 - 4.5 * s, -5.5 * max(0, s))
    armF = 0.16 * s     # 앞팔 흔들림
    armB = -0.16 * s
    emode = 'open'
    tilt = 0.0
    if mode == 'hit':
        bob, legL, legR, armF, armB, tilt = -1.0, (-16.0, 0), (15.0, 0), -0.35, -0.25, -0.09
        emode = 'hit'
    elif mode == 'dead':
        bob, legL, legR, armF, armB, tilt = 6.0, (-17.0, 0), (16.0, 0), 0.55, 0.5, 0.12
        emode = 'dead'
    ground_shadow(c, 46, 6.0, a=0.24)

    def leg(x, lift, mat):
        p = rrect(x - 10.5, -26.0 + lift + bob * 0.3, x + 10.5, 0.0 + lift, 6.0)
        c.part(p, mat, ol=2.3, shade=(-2.2, -2.2), shade_sc=0.97, sh2=(-0.6, -0.6))
        c.line(np.array([(x - 9.0, -6.0 + lift), (x + 9.0, -6.0 + lift)]), mat.sh, 1.2)

    def arm(side, sw, mat, front):
        sx_, sy_ = 33.0 * side, -70.0 + bob
        c.push(rot=sw, ox=sx_, oy=sy_)
        upper = _rock(sx_ + 3 * side, sy_ + 16, 8.0, 13.0, 1.3 + side, 0.05)
        fist = _rock(sx_ + 5 * side, sy_ + 37, 14.0, 12.5, 2.0 + side, 0.07)
        c.part(upper, mat, ol=2.3, shade=(-2.4, -2.0), shade_sc=0.97)
        fm = c.part(fist, mat, ol=2.4, shade=(-3.0, -2.6), shade_sc=0.97, sh2=(-0.8, -0.8), ret=True,
                    hl=[ellipse(sx_ + 6 * side - 7, sy_ + 31, 3.6, 2.0, rot=-0.5)] if front else None, hl_a=0.8)
        # 손가락 홈
        for k in (-4.5, 0.5, 5.5):
            c.line(bez((sx_ + 6 * side + k, sy_ + 44), (sx_ + 6 * side + k + 0.5, sy_ + 47), (sx_ + 6 * side + k + 0.5, sy_ + 49), (sx_ + 6 * side + k, sy_ + 50.5), 8),
                   mat.line, 1.4, clip=fm)
        sh_ = _rock(sx_, sy_, 13.5, 12.0, 0.4 + side, 0.05)
        c.part(sh_, mat, ol=2.3, shade=(-2.4, -2.4), shade_sc=0.97,
               hl=[ellipse(sx_ - 4, sy_ - 6, 4.0, 2.0, rot=-0.4)] if front else None, hl_a=0.85)
        if front:  # 어깨 이끼
            mp = path((sx_ - 12.0, sy_ - 3.0), [((sx_ - 10, sy_ - 13.5), (sx_ + 8, sy_ - 14.5), (sx_ + 12.5, sy_ - 4.0)),
                                                 ((sx_ + 9, sy_ - 1.0), (sx_ + 6, sy_ - 6.0), (sx_ + 3, sy_ - 2.5)),
                                                 ((sx_ + 0, sy_ + 1.0), (sx_ - 4, sy_ - 5.0), (sx_ - 6.5, sy_ - 1.0)),
                                                 ((sx_ - 8.5, sy_ + 2.0), (sx_ - 11.5, sy_ + 0.5), (sx_ - 12.0, sy_ - 3.0))], n=10)
            c.part(mp, MOSS, ol=1.6, shade=(-1.0, -1.4), hl=[ellipse(sx_ - 3, sy_ - 10.5, 3.5, 1.2, rot=-0.1)])
        c.pop()

    c.push(rot=tilt, ox=0, oy=0)
    # 뒷팔(왼쪽, 어둡게)
    arm(-1, armB, STONE_D, False)
    # 다리
    leg(legL[0], legL[1], STONE_D)
    leg(legR[0], legR[1], STONE)
    # 몸통
    torso = _rock(0, -54.0 + bob, 31.0, 30.0, 0.7, 0.04)
    tm = c.part(torso, STONE, ol=2.5, shade=(-4.5, -4.0), shade_sc=0.97, sh2=(-1.4, -1.2), ret=True,
                hl=[ellipse(-14, -72 + bob, 7.5, 3.6, rot=-0.55), ellipse(-21, -62 + bob, 2.0, 1.4)], hl_a=0.9)
    # 금, 룬 무늬
    c.line(np.array([(-18, -44 + bob), (-12, -40 + bob), (-14, -33 + bob), (-8, -29 + bob)]), CRACK, 1.5, clip=tm)
    c.line(np.array([(17, -70 + bob), (12, -64 + bob), (15, -59 + bob)]), CRACK, 1.4, clip=tm)
    rune = path((3.0, -58.0 + bob), [((7.0, -56.0 + bob), (7.0, -50.0 + bob), (3.0, -48.0 + bob)),
                                     ((-1.0, -50.0 + bob), (-1.0, -56.0 + bob), (3.0, -58.0 + bob))], n=12)
    c.line(rune, mix(RUNE, WHITE, 0.0), 3.4, closed=True, clip=tm, a=0.35)
    c.line(rune, RUNE, 1.5, closed=True, clip=tm)
    c.fill(ellipse(3.0, -53.0 + bob, 1.4, 1.4), mix(RUNE, WHITE, 0.6), clip=tm)
    # 머리
    hy = -87.0 + bob
    head = _rock(4.0, hy, 24.0, 19.5, 2.4, 0.035)
    hm = c.part(head, STONE, ol=2.5, shade=(-3.4, -3.2), shade_sc=0.97, sh2=(-1.0, -1.0), ret=True,
                hl=[ellipse(-6, hy - 9.5, 5.5, 2.4, rot=-0.4)])
    # 이끼 모자 + 작은 새싹
    moss = path((-18.5, hy - 7.5), [((-15.0, hy - 21.5), (16.0, hy - 24.0), (26.5, hy - 9.5)),
                                    ((22.0, hy - 6.0), (19.0, hy - 9.5), (16.0, hy - 6.5)),
                                    ((13.0, hy - 4.0), (10.0, hy - 9.0), (6.0, hy - 6.0)),
                                    ((2.0, hy - 3.0), (-1.0, hy - 8.5), (-5.0, hy - 6.0)),
                                    ((-9.0, hy - 3.5), (-14.0, hy - 4.5), (-18.5, hy - 7.5))], n=10)
    c.part(moss, MOSS, ol=1.8, shade=(-1.4, -1.8), hl=[ellipse(-2, hy - 14.5, 6.0, 1.6, rot=-0.08)])
    stem_ = bez((6.0, hy - 19.5), (6.5, hy - 23.0), (5.5, hy - 25.0), (6.5, hy - 27.0), 8)
    c.line(stem_, MOSS.line, 2.6)
    c.line(stem_, MOSS.base, 1.0)
    c.part(path((6.5, hy - 26.5), [((3.0, hy - 30.0), (-1.5, hy - 28.0), (-2.0, hy - 26.0)),
                                    ((1.5, hy - 24.0), (4.5, hy - 25.0), (6.5, hy - 26.5))], n=8), MOSS, ol=1.2, shade=None)
    c.part(path((6.5, hy - 26.5), [((9.0, hy - 31.0), (13.5, hy - 31.0), (14.5, hy - 28.0)),
                                    ((12.0, hy - 25.0), (9.0, hy - 25.0), (6.5, hy - 26.5))], n=8), MOSS, ol=1.2, shade=None)
    # 눈 홈 + 눈
    ex, ey = 8.5, hy + 2.0
    c.fill(ellipse(ex + 3.8, ey + 0.2, 12.0, 6.6), STONE.sh, 0.75, clip=hm)
    if emode == 'open':
        eye(c, ex, ey, 3.3, 4.3)
        eye(c, ex + 8.0, ey, 2.9, 4.2)
        c.line(np.array([(ex - 3.8, ey - 7.2), (ex + 2.4, ey - 6.4)]), STONE.line, 2.0)
        c.line(np.array([(ex + 5.6, ey - 6.4), (ex + 11.0, ey - 7.2)]), STONE.line, 2.0)
        c.line(bez((ex + 1.5, ey + 7.0), (ex + 3.0, ey + 8.2), (ex + 5.0, ey + 8.2), (ex + 6.5, ey + 7.0), 8), STONE.line, 1.4)
    else:
        eye(c, ex, ey, 2.8, 2.8, emode)
        eye(c, ex + 7.0, ey, 2.5, 2.5, 'hitL' if emode == 'hit' else emode)
        if mode == 'hit':
            mouth_smile(c, ex + 3.6, ey + 6.4, 1.8, STONE.line, open_=True, tongue=False)
        else:
            c.line(bez((ex + 1.0, ey + 7.6), (ex + 2.6, ey + 6.4), (ex + 4.4, ey + 8.6), (ex + 6.0, ey + 7.4), 8), STONE.line, 1.3)
    blush(c, ex - 3.0, ey + 5.0, 2.6, 1.3, a=0.45)
    blush(c, ex + 10.4, ey + 5.0, 2.0, 1.2, a=0.45)
    # 앞팔
    arm(1, armF, STONE, True)
    c.pop()


# ======================================================================== 표
MOBS = {
    # frame/anchor: 에셋 px. size: 월드(판정 상자). move 프레임 수.
    'snail': dict(draw=snail, frame=(90, 72), anchor=(45, 66), size=(40, 28), move=4, fps=6),
    'mushroom': dict(draw=mushroom, frame=(108, 126), anchor=(54, 118), size=(46, 46), move=6, fps=10),
    'slime': dict(draw=slime, frame=(108, 114), anchor=(54, 106), size=(44, 38), move=6, fps=10),
    'bat': dict(draw=bat, frame=(120, 102), anchor=(60, 88), size=(46, 34), move=4, fps=10),
    'golem': dict(draw=golem, frame=(216, 198), anchor=(108, 190), size=(84, 110), move=4, fps=5),
}
