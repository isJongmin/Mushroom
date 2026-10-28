"""머리카락 12종. 머리 로컬 좌표(원점 = 턱 밑 가운데, 머리 x ±30, y -54.5..0)."""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, quad, bez, rot, shade, light, deep, line_of, rgb, mix, sub, resample

# --------------------------------------------------------------- 보조
def arc(cx, cy, rx, ry, a0, a1, n=12):
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


def wavy_arc(cx, cy, rx, ry, a0, a1, bumps, amp, n_per=3, spike=False, seed=0):
    """둥근 덩어리(곱슬) 또는 가시(spike) 외곽."""
    rs = np.random.RandomState(seed)
    pts = []
    tot = bumps * n_per
    for i in range(tot + 1):
        t = i / tot
        a = math.radians(a0 + (a1 - a0) * t)
        ph = (i % n_per) / n_per
        if spike:
            k = amp * (1.0 + 0.25 * rs.uniform(-1, 1)) if ph == 0 and 0 < i < tot else 0.0
            p = (cx + (rx + k) * math.cos(a), cy + (ry + k) * math.sin(a))
            pts.append(p + (('c',) if ph == 0 and 0 < i < tot else ()))
        else:
            k = amp * math.sin(ph * math.pi) * (1.0 + 0.2 * rs.uniform(-1, 1))
            p = (cx + (rx + k) * math.cos(a), cy + (ry + k) * math.sin(a))
            pts.append(p + (('c',) if ph == 0 else ()))
    return pts


def bang_run(xs, tip_y, val_y, curl=0.0):
    """오른쪽 -> 왼쪽 앞머리. xs: 끝 x 목록(오른->왼). tip_y/val_y: 함수(x) 또는 수."""
    ty = tip_y if callable(tip_y) else (lambda x, v=tip_y: v)
    vy = val_y if callable(val_y) else (lambda x, v=val_y: v)
    out = []
    for i, x in enumerate(xs):
        sg = 1 if x > 3 else (-1 if x < -3 else 0)
        out.append((x + curl + sg * 1.6, ty(x), 'c'))
        if i + 1 < len(xs):
            xm = (x + xs[i + 1]) / 2
            out.append((xm - curl * 0.3, vy(xm)))
    return out


def strands_from(pts, crown, frac=0.45, w=1.2):
    """골(valley) -> 정수리 방향 결 선."""
    out = []
    crown = np.asarray(crown, float)
    for p in pts:
        p = np.asarray(p[:2], float)
        q = p + (crown - p) * frac
        m = (p + q) / 2 + np.array([(p[0] - crown[0]) * 0.08, 0])
        out.append(taper(quad(p, m, q, 10), w, a=0.15, b=0.6))
    return out


class HairStyle:
    def __init__(self, col, hl=None, ln=None, dk=None):
        self.col = col
        self.sh = shade(col)
        self.dk = dk or deep(col, 1.1)
        self.hl = hl or light(col, 1.0)
        self.ln = ln or line_of(col)

    # 레이어 편의
    def F(self, ctx, layer, poly, shapes=(), col=None, **kw):
        H = ctx.Th
        sh = [(H(s[0]),) + tuple(s[1:]) for s in shapes if s is not None]
        ctx.fig(layer, H(poly), col or self.col, sh=kw.pop('sh', self.sh), line=kw.pop('line', self.ln),
                shapes=sh, sd=kw.pop('sd', (1.6, 1.9)), **kw)


def angel_ring(cx, cy, rx, ry, a0, a1, segs=3, w=2.6, gap=0.25):
    out = []
    span = (a1 - a0) / segs
    for i in range(segs):
        s0 = a0 + span * i + span * gap * 0.5
        s1 = a0 + span * (i + 1) - span * gap * 0.5
        c = np.array(arc(cx, cy, rx, ry, s0, s1, 10))
        out.append(taper(c, w, a=0.45, b=0.45))
    return out


def shade_bangs(ctx, poly, dy=2.6):
    H = ctx.Th
    p = np.asarray([q[:2] for q in poly], float) + (0.6, dy)
    ctx.paint('shade_hair', H(p), '#B65A4E', alpha=0.30)


# --------------------------------------------------------------- 기본 짧은 머리 생성기
def base_short(ctx, S, *, front_xs, front_tip, q_xs, q_tip, val=-41.0, lockF=(-12, 3.5), lockQ=-13,
               nape=-6.0, ear=True, vol=(33.5, 31.0, -29.5), crown_spike=None, curly=None, back_tips=None,
               ring=True, qside=None, extra_front=None, extra_q=None, strand_w=1.15):
    """front_xs: 정면 앞머리 끝 x (오른->왼), front_tip: 끝 y 함수. lockF=(옆머리 끝 y, 두께)."""
    rx, ry, cy = vol
    hv = ctx.view

    def dome(a0, a1, n=16):
        if curly:
            return wavy_arc(0, cy, rx, ry, a0, a1, curly[0], curly[1], seed=curly[2] if len(curly) > 2 else 1)
        if crown_spike:
            return wavy_arc(0, cy, rx, ry, a0, a1, crown_spike[0], crown_spike[1], spike=True,
                            seed=crown_spike[2] if len(crown_spike) > 2 else 1)
        return arc(0, cy, rx, ry, a0, a1, n)

    valf = (lambda x: val + (x / 30.0) ** 2 * 7.0)
    if hv == 'front':
        ly, lt = lockF
        pts = [(-29.5, ly, 'c')] + [(-33.5, ly - 9)] + dome(168, 372) + [(33.5, ly - 9), (29.5, ly, 'c'),
                                                                          (27.5 - lt * 0.3, ly - 7), (25.5, -27),
                                                                          (24.0, -35)]
        bx = bang_run(front_xs, front_tip, valf)
        pts += bx + [(-24.0, -35), (-25.5, -27), (-27.5 + lt * 0.3, ly - 7)]
        if extra_front:
            pts = extra_front(pts)
        vals = [p for p in bx if len(p) == 2]
        sh = strands_from(vals, (0, -60), 0.42, strand_w)
        sh += [taper(quad((-30, ly - 2), (-30.5, -24), (-27, -36), 10), strand_w, 0.2, 0.5),
               taper(quad((30, ly - 2), (30.5, -24), (27, -36), 10), strand_w, 0.2, 0.5)]
        rings = angel_ring(0, cy - 2, rx - 6.5, ry - 8, 205, 335, 3) if ring else []
        S.F(ctx, 'hair_front', cr(pts, 6), shapes=[(s, S.dk, 0.85) for s in sh] + [(r, S.hl, 0.95) for r in rings])
        shade_bangs(ctx, cr(pts, 6))
    elif hv == 'q':
        pts = []
        # 뒤통수 쪽 (왼쪽)
        if ear:
            pts += [(-27.5, nape, 'c'), (-23.5, nape - 5), (-23.0, -17), (-23.5, -26), (-19.5, -30.5),
                    (-13.5, -30), (-11.5, -21.5, 'c'), (-9.5, -31.5)]
        else:
            pts += [(-27.5, nape, 'c'), (-22.5, nape - 3), (-16.5, -12), (-13, -24), (-10.5, -33.5)]
        if qside:
            pts = qside(pts)
        bx = bang_run(q_xs, q_tip, lambda x: valf(x - 6.0))
        rly = lockQ
        tail = [(25.5, -30), (27.0, rly - 6), (29.0, rly, 'c'), (31.5, rly - 9)]
        front = pts + bx[::-1] + tail
        if not curly and not crown_spike:
            front = [front[0]] + front[1:] + dome(8, -197 + 360 - 360, 16)[::-1] if False else front
        domep = dome(-12 + 360, 166, 18) if not (curly or crown_spike) else dome(348, 166)
        # dome: 오른쪽(348도) -> 위 -> 왼쪽(166도) 반시계로 가야 하므로 각도 감소
        poly = front + domep + [(-33.0, nape - 10)]
        # 순서 보정: front 는 왼쪽 아래 -> 앞머리(왼->오) -> 오른쪽 옆머리
        if extra_q:
            poly = extra_q(poly)
        vals = [p for p in bx if len(p) == 2]
        sh = strands_from(vals, (-6, -60), 0.42, strand_w)
        sh += [taper(quad((-27, nape - 2), (-31, -22), (-27, -40), 12), strand_w, 0.2, 0.5),
               taper(quad((-20, -14), (-22, -30), (-18, -44), 12), strand_w, 0.2, 0.6),
               taper(quad((29.5, rly - 2), (30, -26), (26, -38), 10), strand_w, 0.2, 0.5)]
        rings = angel_ring(-3, cy - 2, rx - 6.5, ry - 8, 200, 330, 3) if ring else []
        S.F(ctx, 'hair_front', cr(poly, 6), shapes=[(s, S.dk, 0.85) for s in sh] + [(r, S.hl, 0.95) for r in rings])
        shade_bangs(ctx, cr(poly, 6))
    else:  # back
        tips = back_tips or [-26, -17, -8, 1, 10, 19, 27]
        bot = []
        for i, x in enumerate(tips[::-1]):
            bot.append((x, nape + 1.0 + (1.5 if i % 2 else 0), 'c'))
            if i + 1 < len(tips):
                xm = (x + tips[::-1][i + 1]) / 2
                bot.append((xm, nape - 4))
        pts = dome(150, 390) + [(31.5, nape - 6)] + bot + [(-31.5, nape - 6)]
        sh = [taper(quad((x, nape - 2), (x * 1.08, -26), (x * 0.4, -52), 12), strand_w, 0.15, 0.5) for x in tips[1:-1]]
        rings = angel_ring(0, cy - 2, rx - 5, ry - 7, 210, 330, 3) if ring else []
        S.F(ctx, 'hair_front', cr(pts, 6), shapes=[(s, S.dk, 0.85) for s in sh] + [(r, S.hl, 0.95) for r in rings])


def long_back(ctx, S, length=26.0, width=33.0, tips=7, layer=None, flare=1.0, wave=0.0, inward=0.0):
    """긴 머리 뒷덩어리. 정면/옆: hair_back, 뒤: hair_front(앞에서 덮음)."""
    hv = ctx.view
    sway = ctx.sway * 2.2
    lay = layer or ('hair_front' if hv == 'back' else 'hair_back')
    if ctx.prone:
        length = min(length, 6.0)
    if hv == 'q':
        x0, x1 = -33.0 - flare * 2, 20.0
    else:
        x0, x1 = -width - flare * 2, width + flare * 2
    xs = np.linspace(x1, x0, tips)
    bot = []
    for i, x in enumerate(xs):
        t = abs(x) / max(abs(x0), abs(x1))
        y = length - (2.5 if i % 2 else 0) - t * 3 - (inward * 6 * (1 - t))
        bot.append((x - sway * (1 + y / 30), y, 'c'))
        if i + 1 < len(xs):
            xm = (x + xs[i + 1]) / 2
            bot.append((xm - sway, y - 5 - wave))
    top = arc(0 if hv != 'q' else -3, -30, 34.5, 31.5, 180, 360, 12)
    pts = [(x1 + 1.5, -20)] + bot + [(x0 - 0.5, -20)] + top
    sh = []
    for x in np.linspace(x0 + 6, x1 - 6, max(2, tips - 2)):
        sh.append(taper(quad((x - sway, length - 4), (x * 1.05, length * 0.3), (x * 0.9, -26), 12), 1.2, 0.15, 0.5))
    rings = []
    if hv == 'back':
        rings = angel_ring(0, -32, 28, 25, 215, 325, 3)
    S.F(ctx, lay, cr(pts, 6), shapes=[(s, S.dk, 0.8) for s in sh] + [(r, S.hl, 0.9) for r in rings])


def tail(ctx, S, root, d, length, w0, w1, layer, tie=None, curl=0.0, tipn=3, streak=None):
    """포니테일/양갈래 꼬리. root=머리 로컬 시작점, d=방향 각(도, 0=아래)."""
    root = np.asarray(root, float)
    a = math.radians(d)
    dv = np.array([math.sin(a), math.cos(a)])
    nv = np.array([dv[1], -dv[0]])
    sw = ctx.sway * 3.0
    p1 = root + dv * length * 0.45 + nv * (curl * 0.5) + np.array([-sw * 0.4, 0])
    p2 = root + dv * length + nv * curl + np.array([-sw, 0])
    c = quad(root, p1, p2, 18)
    w = lambda t: (w0 + (w1 - w0) * t) * (math.sin(min(1, (1 - t) / 0.35) * math.pi / 2) if t > 0.65 else 1) \
        * (0.75 + 0.25 * math.sin(min(1, t / 0.15) * math.pi / 2))
    poly = ribbon(c, w, cap0=True, cap1=False)
    # 끝을 여러 갈래로
    sh = [taper(sub(c, 0.1, 0.95, 12) + nv * k, 1.1, 0.2, 0.3) for k in (-w0 * 0.22, w0 * 0.18)]
    hl = [taper(sub(c, 0.12, 0.45, 10) + nv * (-w0 * 0.12), 2.0, 0.4, 0.4)]
    shapes = [(s, S.dk, 0.8) for s in sh] + [(h, S.hl, 0.9) for h in hl]
    if streak:
        shapes.append((taper(sub(c, 0.05, 0.98, 14) + nv * (w0 * 0.12), w0 * 0.26, 0.1, 0.25), streak, 1.0))
    for kk, (ang, lf, wf) in enumerate(((-14, 0.82, 0.55), (12, 0.9, 0.5))):
        a2 = math.radians(d + ang)
        dv2 = np.array([math.sin(a2), math.cos(a2)])
        q1 = root + dv2 * length * 0.45 * lf + nv * (curl * 0.4) + np.array([-sw * 0.4, 0])
        q2 = root + dv2 * length * lf + nv * curl * 0.8 + np.array([-sw, 0])
        c2 = quad(root, q1, q2, 14)
        S.F(ctx, layer, ribbon(c2, lambda t: w(t) * wf * 1.6 if t > 0.3 else w(t) * 0.5, cap0=True, cap1=False),
            shapes=[(taper(sub(c2, 0.3, 0.9, 8), 0.9, 0.2, 0.3), S.dk, 0.7)])
    S.F(ctx, layer, poly, shapes=shapes)
    if tie:
        tp = root + dv * 2.6
        S.F(ctx, layer, rot(ellipse(0, 0, w0 * 0.42, 2.6, 18), math.degrees(-a)) + tp, col=tie, sh=shade(tie),
            line=line_of(tie))


# --------------------------------------------------------------- 스타일 12종
def h_ash_twoblock(ctx):
    S = HairStyle('#8A7670', hl='#C9B8B0')
    base_short(ctx, S, front_xs=[24, 15, 5, -5, -15, -24],
               front_tip=lambda x: -31.0 + abs(x) * 0.12 - (2 if abs(x) < 6 else 0),
               q_xs=[29, 21, 12, 3, -6], q_tip=lambda x: -31 + (x - 8) ** 2 * 0.006,
               lockF=(-14, 4), lockQ=-17, nape=-10, vol=(35.5, 34.5, -28.5), curly=(9, 1.8, 5))


def h_black_seethrough(ctx):
    S = HairStyle('#2F2B38', hl='#7A7392', ln='#120F18')
    long_back(ctx, S, length=34, width=33, tips=9)
    if ctx.view == 'back':
        base_short(ctx, S, front_xs=[], front_tip=0, q_xs=[], q_tip=0, nape=30, back_tips=[-30, -20, -10, 0, 10, 20, 30])
        return
    # 시스루뱅: 가는 앞머리 사이로 이마가 보인다
    base_short(ctx, S, front_xs=[25, 19, 12, 5, -2, -9, -16, -21, -25],
               front_tip=lambda x: -28.5 + abs(x) * 0.1, val=-42.5,
               q_xs=[29, 24, 18, 12, 6, 0, -5, -10], q_tip=lambda x: -28.5,
               lockF=(4, 5), lockQ=2, nape=4, ear=False, vol=(35, 33.5, -29.0))
    # 앞 옆머리 긴 가닥 (얼굴 옆으로)
    H = ctx.Th
    for sx, side in ((-1, 'L'), (1, 'R')):
        if ctx.q and sx < 0:
            continue
        x = 29.5 * sx if not ctx.q else 30.0
        c = quad((x - sx * 2, -26), (x + sx * 1.0, -6), (x - sx * 1.5 - ctx.sway, 16), 14)
        S.F(ctx, 'hair_front', taper(c, 7.0, a=0.0, b=0.35, wmin=0.5),
            shapes=[(taper(sub(c, 0.1, 0.9) + (sx * 0.5, 0), 1.0, 0.2, 0.4), S.dk, 0.8)])
    # 머리핀 2개 (오른쪽 앞머리)
    if ctx.front:
        pins = [(15.5, -43.5, 26), (17.5, -39.0, 26)]
    else:
        pins = [(19.0, -43.0, 22), (21.5, -38.5, 22)]
    for (x, y, a), c in zip(pins, ('#FFF6EE', '#F8A8C8')):
        S.F(ctx, 'hair_front', rot(cr([(-4.5, -1.1, 'c'), (4.5, -1.1, 'c'), (4.5, 1.1, 'c'), (-4.5, 1.1, 'c')], 3), a) + (x, y),
            col=c, sh=shade(c), line=line_of(c), lw=1.5)


def h_black_wolfcut(ctx):
    S = HairStyle('#2A2733', hl='#6E6A86', ln='#110E16')
    # 뒷목 울프 꼬리
    if ctx.view != 'back':
        if ctx.q:
            for x, l in ((-20, 9), (-14, 7)):
                tail(ctx, S, (x, -6), 8 + ctx.sway * 2, l, 7.0, 4.5, 'hair_back')
        else:
            for x in (-22, -12, 12, 22):
                tail(ctx, S, (x, -10), -x * 0.4, 13, 7.0, 4.0, 'hair_back')
    base_short(ctx, S, front_xs=[26, 17, 8, -1, -10, -19, -26],
               front_tip=lambda x: -30 + (2.5 if int(x) % 2 else 0) + abs(x) * 0.05, val=-42,
               q_xs=[30, 22, 13, 4, -5], q_tip=lambda x: -30.5 + (2.5 if int(x) % 2 else 0),
               lockF=(-8, 4.5), lockQ=-10, nape=-1, ear=False, vol=(35.5, 34.0, -29.0), crown_spike=(7, 3.6, 3),
               back_tips=[-29, -21, -13, -5, 3, 11, 19, 27])
    # 은 귀걸이(정면에서 왼쪽 귀 아래)
    if ctx.front:
        S.F(ctx, 'hair_front', ellipse(-29.5, -15.5, 1.5, 1.5, 12), col='#E8ECF4', sh='#9AA4BC', line='#5B6278', lw=1.2)


def h_pink_bridge_ponytail(ctx):
    S = HairStyle('#4A3530', hl='#9C7A6E', ln='#22140F')
    pink = '#F48CBB'
    if ctx.view == 'front':
        tail(ctx, S, (22, -50), -22 + ctx.sway * 4, 40, 14, 6, 'hair_back', curl=-6, streak=pink)
    elif ctx.q:
        tail(ctx, S, (-26, -50), -22 + ctx.sway * 10, 44, 15, 8, 'hair_back', curl=8, streak=pink)
    base_short(ctx, S, front_xs=[24, 14, 4, -6, -16, -24],
               front_tip=lambda x: -30 + abs(x) * 0.08, q_xs=[29, 20, 11, 2, -6], q_tip=lambda x: -30,
               lockF=(-2, 4.0), lockQ=-4, nape=-14, vol=(34.5, 33.5, -29.0))
    H = ctx.Th
    # 분홍 브릿지 가닥 (앞 옆머리: 머리색 가닥 안에 분홍 줄)
    sides = [1] if ctx.q else [-1, 1]
    for sx in sides:
        x = 27.5 * sx if not ctx.q else 28.5
        c = quad((x - sx * 4, -40), (x + sx * 1.5, -22), (x - sx * 0.5, -4), 14)
        S.F(ctx, 'hair_front', taper(c, 6.0, a=0.05, b=0.3, wmin=0.6),
            shapes=[(taper(sub(c, 0.08, 0.92) + (-sx * 0.6, 0), 2.6, 0.2, 0.3), pink, 1.0),
                    (taper(sub(c, 0.1, 0.5) + (-sx * 1.0, 0), 0.9, 0.3, 0.3), light(pink), 0.9)])
    if ctx.view == 'back':
        tail(ctx, S, (0, -52), 0 + ctx.sway * 5, 44, 15, 7, 'hair_front', tie='#F48CBB', streak=pink)
    elif ctx.q:
        S.F(ctx, 'hair_front', rot(ellipse(0, 0, 3.0, 4.6, 16), 30) + (-27.5, -48), col=pink, sh=shade(pink),
            line=line_of(pink))


def h_black_short(ctx):
    S = HairStyle('#3A2C28', hl='#86706A', ln='#1A100D')
    base_short(ctx, S, front_xs=[25, 16, 7, -2, -11, -19, -25],
               front_tip=lambda x: -32.5 + (1.5 if int(x) % 2 else 0), val=-44,
               q_xs=[29, 21, 13, 4, -5], q_tip=lambda x: -33,
               lockF=(-18, 3.5), lockQ=-20, nape=-12, vol=(34.5, 33.5, -29.0))


def h_brown_short(ctx):
    S = HairStyle('#8A5636', hl='#D49A6A', ln='#3E2010')
    # 옆가르마: 왼쪽으로 쓸어 넘긴 앞머리 (끝이 왼쪽으로 휨)
    base_short(ctx, S, front_xs=[26, 16, 6, -4, -14, -23],
               front_tip=lambda x: -32 - x * 0.12, val=-43,
               q_xs=[30, 21, 12, 3, -6], q_tip=lambda x: -32 - (x - 10) * 0.1,
               lockF=(-17, 3.5), lockQ=-18, nape=-11, vol=(35.0, 34.0, -29.0), curly=(7, 1.4, 9))


def h_blonde_spiky(ctx):
    S = HairStyle('#F5C64E', hl='#FFF1B0', ln='#9A5A12', dk='#D8902A')
    base_short(ctx, S, front_xs=[27, 17, 7, -3, -13, -22, -28],
               front_tip=lambda x: -29 + (2.5 if int(x) % 3 == 0 else 0), val=-42,
               q_xs=[31, 22, 13, 4, -5], q_tip=lambda x: -29.5,
               lockF=(-12, 5), lockQ=-15, nape=-6, vol=(35.0, 33.5, -29.0), crown_spike=(7, 7.5, 7),
               back_tips=[-29, -19, -9, 1, 11, 21, 29])


def h_pink_long(ctx):
    S = HairStyle('#F7A0C6', hl='#FFE0EE', ln='#A8406E')
    long_back(ctx, S, length=36, width=34, tips=9, wave=2.5, flare=2.0)
    if ctx.view == 'back':
        base_short(ctx, S, front_xs=[], front_tip=0, q_xs=[], q_tip=0, nape=34, curly=(10, 1.6, 4),
                   back_tips=[-32, -22, -11, 0, 11, 22, 32])
        return
    base_short(ctx, S, front_xs=[25, 15, 5, -5, -15, -24],
               front_tip=lambda x: -30.5 + abs(x) * 0.06, val=-43,
               q_xs=[29, 20, 11, 2, -7], q_tip=lambda x: -30.5,
               lockF=(8, 6), lockQ=6, nape=8, ear=False, vol=(35.5, 34.0, -29.0), curly=(10, 1.6, 4))
    # 옆 웨이브 가닥
    for sx in ([1] if ctx.q else [-1, 1]):
        x = 30.0 * sx
        c = bez((x - sx * 3, -30), (x + sx * 4, -14), (x - sx * 4, 2), (x + sx * 1 - ctx.sway, 20), 16)
        S.F(ctx, 'hair_front', taper(c, 8.0, a=0.0, b=0.3, wmin=0.6),
            shapes=[(taper(sub(c, 0.15, 0.85) + (sx * 0.8, 0), 1.0, 0.2, 0.4), S.dk, 0.8),
                    (taper(sub(c, 0.1, 0.4) + (-sx * 1.2, 0), 2.0, 0.3, 0.3), S.hl, 0.85)])


def h_sky_bob(ctx):
    S = HairStyle('#94CFF2', hl='#E2F4FF', ln='#2E6E9E')
    long_back(ctx, S, length=0.0, width=33.5, tips=7, inward=0.6)
    if ctx.view == 'back':
        base_short(ctx, S, front_xs=[], front_tip=0, q_xs=[], q_tip=0, nape=2, back_tips=[-32, -21, -10, 0, 10, 21, 32])
        return
    base_short(ctx, S, front_xs=[25, 16, 7, -2, -11, -19, -25],
               front_tip=lambda x: -32.0, val=-44,
               q_xs=[29, 21, 13, 4, -5], q_tip=lambda x: -32.5,
               lockF=(-1, 7), lockQ=-2, nape=0, ear=False, vol=(36.0, 34.5, -29.0))


def h_tan_ponytail(ctx):
    S = HairStyle('#9C6440', hl='#D9A57A', ln='#4A2410')
    tie = '#E8483E'
    if ctx.view == 'front':
        tail(ctx, S, (17, -22), -30 + ctx.sway * 4, 30, 12, 6, 'hair_back', curl=-3)
    elif ctx.q:
        tail(ctx, S, (-25, -24), -12 + ctx.sway * 8, 32, 13, 7, 'hair_back', curl=4)
    base_short(ctx, S, front_xs=[24, 14, 4, -6, -16, -24],
               front_tip=lambda x: -31 + abs(x) * 0.06, q_xs=[29, 20, 11, 2, -6], q_tip=lambda x: -31,
               lockF=(-12, 4), lockQ=-14, nape=-16, vol=(34.0, 33.0, -29.0))
    if ctx.view == 'back':
        tail(ctx, S, (0, -24), ctx.sway * 5, 30, 12, 6, 'hair_front', tie=tie)
    elif ctx.q:
        S.F(ctx, 'hair_front', rot(ellipse(0, 0, 2.8, 4.2, 16), 15) + (-28.0, -23), col=tie, sh=shade(tie),
            line=line_of(tie))


def h_black_twintail(ctx):
    S = HairStyle('#352D3E', hl='#7C7090', ln='#160F1C')
    tie = '#E8483E'
    if ctx.view == 'front':
        for sx in (-1, 1):
            tail(ctx, S, (sx * 30, -38), sx * 16 + ctx.sway * 4, 40, 13, 7, 'hair_back', curl=sx * 4)
    elif ctx.q:
        tail(ctx, S, (27, -40), 14 + ctx.sway * 6, 38, 12, 6, 'hair_back', curl=-3)
    base_short(ctx, S, front_xs=[24, 15, 5, -5, -15, -24],
               front_tip=lambda x: -32 + abs(x) * 0.05, q_xs=[29, 20, 11, 2, -6], q_tip=lambda x: -32,
               lockF=(-14, 4), lockQ=-15, nape=-14, vol=(34.0, 33.0, -29.0))
    if ctx.view == 'front':
        for sx in (-1, 1):
            S.F(ctx, 'hair_front', rot(ellipse(0, 0, 3.0, 4.4, 16), sx * 20) + (sx * 30, -38), col=tie, sh=shade(tie),
                line=line_of(tie))
    elif ctx.q:
        tail(ctx, S, (-24, -40), -14 + ctx.sway * 8, 40, 13, 6, 'hair_front', curl=4, tie=tie)
    else:
        for sx in (-1, 1):
            tail(ctx, S, (sx * 28, -38), sx * 18 + ctx.sway * 4, 40, 13, 6, 'hair_front', curl=sx * 4, tie=tie)


def h_mint_curly(ctx):
    S = HairStyle('#86DABD', hl='#DDF8EE', ln='#2E7E68')
    # 뒤로 풍성한 곱슬 볼륨
    if ctx.view != 'back':
        H = ctx.Th
        pts = wavy_arc(0 if ctx.front else -4, -29, 36, 27, 140, 400, 11, 2.6, seed=11)
        S.F(ctx, 'hair_back', cr(pts, 5), shapes=[(c, S.dk, 0.7) for c in
                                                     [taper(quad((x, -4), (x * 1.1, -14), (x, -24), 8), 1.1, 0.3, 0.3)
                                                      for x in (-30, -20, 20, 30)]])
    base_short(ctx, S, front_xs=[26, 17, 8, -1, -10, -19, -26],
               front_tip=lambda x: -31.5 + (2 if int(x) % 2 else 0), val=-43,
               q_xs=[30, 21, 12, 3, -6], q_tip=lambda x: -31.5,
               lockF=(-6, 5), lockQ=-8, nape=-4, ear=False, vol=(36.5, 35.0, -28.5), curly=(12, 2.6, 13),
               back_tips=[-31, -22, -13, -4, 5, 14, 23, 31])


HAIRS = {
    'ash-twoblock': h_ash_twoblock, 'black-seethrough': h_black_seethrough, 'black-wolfcut': h_black_wolfcut,
    'pink-bridge-ponytail': h_pink_bridge_ponytail, 'black-short': h_black_short, 'brown-short': h_brown_short,
    'blonde-spiky': h_blonde_spiky, 'pink-long': h_pink_long, 'sky-bob': h_sky_bob, 'tan-ponytail': h_tan_ponytail,
    'black-twintail': h_black_twintail, 'mint-curly': h_mint_curly,
}


def hair(ctx, hid):
    HAIRS[hid](ctx)
