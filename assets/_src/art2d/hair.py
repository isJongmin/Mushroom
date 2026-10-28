"""머리카락 12종 (사이클 9 v2: 레이어드 컷, 가닥 잎 모양 겹치기).

머리 로컬 좌표(원점 = 턱 밑 가운데, 머리 x ±28.5, y -54.5..0, 눈 y≈-22, 이마선 y≈-42).
구성: 바탕 덩어리(cap) + 정수리에서 뻗는 가닥(leaf)들을 겹쳐 그린다. 가닥마다 얇은 색선과 그늘이 있어 결이 보인다.
"""
import math
import numpy as np
from raster import cr, ellipse, ribbon, taper, quad, bez, rot, shade, light, deep, line_of, rgb, mix, sub, resample


def arc(cx, cy, rx, ry, a0, a1, n=12):
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


class HairStyle:
    def __init__(self, col, hl=None, ln=None, dk=None):
        self.col = col
        self.sh = shade(col, 0.9)
        self.dk = dk or deep(col, 0.9)
        self.hl = hl or light(col, 0.7)
        self.ln = ln or line_of(col)

    def F(self, ctx, layer, poly, shapes=(), col=None, **kw):
        H = ctx.Th
        sh = [(H(s[0]),) + tuple(s[1:]) for s in shapes if s is not None]
        c = col or self.col
        ctx.fig(layer, H(poly), c, sh=kw.pop('sh', self.sh if col is None else shade(c, 0.9)),
                line=kw.pop('line', self.ln if col is None else line_of(c)), shapes=sh, sd=kw.pop('sd', (1.4, 1.7)), **kw)


def sheen(cx, cy, rx, ry, a0, a1, segs=3, w=2.2, gap=0.3):
    out = []
    span = (a1 - a0) / segs
    for i in range(segs):
        s0 = a0 + span * i + span * gap * 0.5
        s1 = a0 + span * (i + 1) - span * gap * 0.5
        out.append(taper(np.array(arc(cx, cy, rx, ry, s0, s1, 10)), w, a=0.45, b=0.45))
    return out


def leaf(S, ctx, layer, root, tip, w, bend=0.0, a=0.45, b=0.5, sheen_on=True, col=None):
    root = np.asarray(root, float); tip = np.asarray(tip, float)
    d = tip - root
    L = np.linalg.norm(d)
    n = np.array([-d[1], d[0]]) / max(L, 1e-6)
    c = quad(root, (root + tip) / 2 + n * bend, tip, 18)
    shapes = []
    if sheen_on:
        shapes.append((taper(sub(c, 0.25, 0.55, 8) - n * w * 0.12, w * 0.22, 0.4, 0.4), S.hl if col is None else light(col, 0.7), 0.55))
    S.F(ctx, layer, taper(c, w, a=a, b=b, wmin=0.3), shapes=shapes, col=col)
    return c


def shade_bangs(ctx, tips, dy=2.4, w=9.0):
    """앞머리가 이마에 드리우는 그늘 (shade_hair, source-atop)."""
    H = ctx.Th
    for (r, t, ww) in tips:
        c = quad(np.asarray(r) + (0.6, dy), (np.asarray(r) + np.asarray(t)) / 2 + (0.6, dy), np.asarray(t) + (0.6, dy), 10)
        ctx.paint('shade_hair', H(taper(c, ww * 0.9, 0.5, 0.4)), '#B07468', alpha=0.22)


# --------------------------------------------------------------- 기본 생성기
def hair_base(ctx, S, *, vol=(33.5, 32.0, -30.0), side=-16.0, nape=-8.0, ear=True, bangs=(), sidelocks=True,
              side_w=8.5, back_tips=9, back_len=None, crown=(0, -60.0), tufts=(), hairline=-43.5, lock_bend=2.0,
              q_shift=6.0, flat_back=False):
    """bangs: [(tip_x, tip_y, w, bend)] 정면 기준. side: 얼굴 옆 머리 끝 y. nape: 뒷머리 끝 y."""
    rx, ry, cy = vol
    hv = ctx.view
    back_len = nape if back_len is None else back_len
    if ctx.prone:  # 엎드리면 턱이 바닥: 턱 아래로 내려가는 머리는 자른다
        side, nape, back_len = min(side, -4.0), min(nape, -4.0), min(back_len, -4.0)
    sw = ctx.sway
    dx = -3 if hv == 'q' else 0
    for (r, t, w, bend) in tufts:  # 바탕 뒤에 먼저: 끝만 실루엣 밖으로 삐친다
        leaf(S, ctx, 'hair_front', (r[0] + dx, r[1]), (t[0] + dx, t[1]), w, bend=bend, a=0.3, b=0.5)
    if hv == 'front':
        cap = arc(0, cy, rx, ry, 158, 382, 20)
        cap = cap + [(rx * 0.93, side - 2), (rx * 0.86, side, 'c'), (26.5, side - 3), (27.5, -26), (24.5, -38),
                     (13, hairline - 1), (0, hairline - 1.5), (-13, hairline - 1), (-24.5, -38), (-27.5, -26),
                     (-26.5, side - 3), (-rx * 0.86, side, 'c'), (-rx * 0.93, side - 2)]
        S.F(ctx, 'hair_front', cr(cap, 6), shapes=[(s, S.hl, 0.45) for s in sheen(0, cy - 1, rx - 6, ry - 7, 212, 328, 3)])
        if sidelocks:
            for sx in (-1, 1):
                leaf(S, ctx, 'hair_front', (sx * 20, -50), (sx * (rx * 0.84) - sw * 0.5, side + 0.5), side_w, bend=-sx * 2.5,
                     a=0.35, b=0.35)
        sb = []
        order = sorted(bangs, key=lambda t: -abs(t[0]))
        for (tx, ty, w, bend) in order:
            root = (crown[0] + tx * 0.28, crown[1] + 4)
            leaf(S, ctx, 'hair_front', root, (tx, ty), w, bend=bend if bend else (lock_bend if tx < 0 else -lock_bend))
            sb.append((root, (tx, ty), w))
        shade_bangs(ctx, sb)
    elif hv == 'q':
        cx0 = -4.0
        cap = arc(cx0, cy, rx, ry, 150, 372, 20)
        cap = cap + [(rx * 0.95 + cx0 + 2, side - 2), (29.0, side, 'c'), (27.0, side - 4), (27.0, -30), (19, hairline),
                     (6, hairline - 1.5), (-6, hairline + 1)]
        if ear:
            cap += [(-9.5, -33), (-10.0, -25, 'c'), (-12.5, -31.5), (-19, -32.5), (-22.5, -27), (-22.8, -16), (-24, nape + 3),
                    (-27, nape, 'c')]
        else:
            cap += [(-11, -34), (-13, -22), (-15.5, side + 2), (-17, side, 'c'), (-24, side - 2), (-28, nape, 'c')]
        cap += [(-33.5, nape - 6)]
        S.F(ctx, 'hair_front', cr(cap, 6), shapes=[(s, S.hl, 0.45) for s in sheen(cx0, cy - 1, rx - 6, ry - 7, 205, 322, 3)])
        # 뒤통수 결 (가닥 2~3개)
        for (r, t, w, bend) in (((-14, -58), (-30, nape + 1), 11, 3), ((-6, -60), (-22, nape - 2), 10, 2)):
            leaf(S, ctx, 'hair_front', r, (t[0] + sw * 0.6, t[1]), w, bend=bend, a=0.4, b=0.4)
        if sidelocks:
            leaf(S, ctx, 'hair_front', (21, -50), (29.5 - sw * 0.5, side + 0.5), side_w * 0.85, bend=-2.0, a=0.35, b=0.35)
        sb = []
        tr = [(tx * 0.82 + q_shift, ty, w, bend) for (tx, ty, w, bend) in bangs]
        tr = [t for t in tr if t[0] > -11]
        for (tx, ty, w, bend) in sorted(tr, key=lambda t: -abs(t[0] - 8)):
            root = (cx0 + tx * 0.3, crown[1] + 4)
            leaf(S, ctx, 'hair_front', root, (tx, ty), w, bend=bend if bend else (lock_bend if tx < 8 else -lock_bend))
            sb.append((root, (tx, ty), w))
        shade_bangs(ctx, sb)
    else:  # back
        cap = arc(0, cy, rx, ry, 148, 392, 22)
        cap = cap + [(rx * 0.9, back_len - 4), (rx * 0.8, back_len, 'c')]
        xs = np.linspace(rx * 0.8, -rx * 0.8, back_tips)
        for i in range(1, len(xs) - 1):
            cap.append((xs[i], back_len + (0 if i % 2 else 1.6) - (abs(xs[i]) / rx) * 2))
        cap += [(-rx * 0.8, back_len, 'c'), (-rx * 0.9, back_len - 4)]
        S.F(ctx, 'hair_front', cr(cap, 6), shapes=[(s, S.hl, 0.45) for s in sheen(0, cy - 1, rx - 5, ry - 6, 215, 325, 3)])
        for x in np.linspace(-rx * 0.62, rx * 0.62, max(3, back_tips - 4)):
            leaf(S, ctx, 'hair_front', (x * 0.25, -58), (x - sw * 0.4, back_len - 1.0), 11, bend=x * 0.08, a=0.45, b=0.4)


def long_back(ctx, S, length=26.0, width=33.0, wave=0.0, inward=0.0, layer=None, locks=5):
    """긴 머리 뒷덩어리. 정면/옆: hair_back, 뒤: hair_front."""
    hv = ctx.view
    sw = ctx.sway * 2.0
    lay = layer or ('hair_front' if hv == 'back' else 'hair_back')
    if ctx.prone:
        length = min(length, -5.0)
    if hv == 'q':
        x0, x1 = -width - 2, 18.0
    else:
        x0, x1 = -width, width
    n = 7
    xs = np.linspace(x1, x0, n)
    bot = []
    for i, x in enumerate(xs):
        t = abs(x) / max(abs(x0), abs(x1))
        y = length - t * 3.0 - inward * 5 * (1 - t) - (1.5 if i % 2 else 0)
        bot.append((x - sw * (1 + y / 40) + (wave * (1 if i % 2 else -1)), y))
    top = arc(0 if hv != 'q' else -4, -30, width + 1.5, 31.5, 182, 358, 12)
    pts = [(x1 + 1.0, -18)] + bot + [(x0 - 0.5, -18)] + top
    S.F(ctx, lay, cr(pts, 6))
    for x in np.linspace(x0 + 7, x1 - 7, locks):
        c0 = (x * 0.7, -30)
        c1 = (x - sw * (1 + length / 40), length - 2)
        leaf(S, ctx, lay, c0, c1, 12, bend=wave * 1.5 + x * 0.04, a=0.5, b=0.35)


def tail(ctx, S, root, d, length, w0, w1, layer, tie=None, curl=0.0, streak=None):
    """포니테일/양갈래 꼬리 (가닥 3개 묶음)."""
    if ctx.prone:  # 엎드리면 등 쪽(왼쪽)으로 눕힌다
        d, length, curl = -84.0, length * 0.85, abs(curl)
    root = np.asarray(root, float)
    a = math.radians(d)
    dv = np.array([math.sin(a), math.cos(a)])
    nv = np.array([dv[1], -dv[0]])
    sw = ctx.sway * 3.0
    for k, (ang, lf, wf, cf) in enumerate(((-12, 0.86, 0.65, 0.6), (14, 0.92, 0.6, 1.2), (0, 1.0, 1.0, 1.0))):
        a2 = math.radians(d + ang)
        dv2 = np.array([math.sin(a2), math.cos(a2)])
        tip = root + dv2 * length * lf + nv * curl * cf + np.array([-sw, 0])
        mid = root + dv2 * length * 0.5 * lf + nv * curl * 0.9 + np.array([-sw * 0.4, 0])
        c = quad(root, mid, tip, 18)
        wfn = lambda t, w0=w0 * wf, w1=w1 * wf: (w0 + (w1 - w0) * t) * (math.sin(min(1, (1 - t) / 0.45) * math.pi / 2)) \
            * (0.7 + 0.3 * math.sin(min(1, t / 0.2) * math.pi / 2))
        shapes = [(taper(sub(c, 0.15, 0.5, 8) - nv * w0 * 0.12, w0 * 0.2, 0.4, 0.4), S.hl, 0.5)]
        if streak and k == 2:
            shapes.append((taper(sub(c, 0.05, 0.95, 14) + nv * (w0 * 0.12), w0 * 0.3, 0.1, 0.3), streak, 0.95))
        S.F(ctx, layer, ribbon(c, wfn, cap0=True, cap1=False), shapes=shapes)
    if tie:
        tp = root + dv * 2.4
        S.F(ctx, layer, rot(ellipse(0, 0, w0 * 0.42, 2.4, 18), math.degrees(-a)) + tp, col=tie)


# --------------------------------------------------------------- 스타일 12종
def h_ash_twoblock(ctx):
    """애쉬브라운 투블럭: 정수리 볼륨 + 눈썹을 덮는 가닥 앞머리, 옆은 짧게."""
    S = HairStyle('#8E807A', hl='#C4B8B2')
    hair_base(ctx, S, vol=(34.5, 34.5, -29.0), side=-24, nape=-12, ear=True,
              bangs=[(-20, -31, 12, 0), (-10, -28.5, 13, 0), (0, -29, 13, 0), (10, -28, 13, 0), (20, -31, 12, 0)],
              side_w=7.0, lock_bend=3.0)


def h_black_seethrough(ctx):
    """시스루뱅 긴 흑발: 가는 앞머리 사이로 이마가 비치고, 얼굴 옆 가닥이 길다."""
    S = HairStyle('#36323A', hl='#76707E', ln='#1E1B22')
    long_back(ctx, S, length=40, width=33, wave=0.6)
    hair_base(ctx, S, vol=(33.5, 32.5, -29.5), side=10, nape=36, back_len=38, ear=False,
              bangs=[(-15, -29.5, 6.5, 0), (-7, -28, 6.0, 0), (1, -28.5, 6.0, 0), (9, -28, 6.0, 0), (16, -29.5, 6.5, 0)],
              side_w=9.0, lock_bend=1.0)
    if ctx.view != 'back':
        pins = [(16.5, -44.0, 24), (18.5, -39.5, 24)] if ctx.front else [(20.0, -43.5, 20), (22.0, -39.0, 20)]
        for (x, y, a), c in zip(pins, ('#F4EEE6', '#E2B8C2')):
            S.F(ctx, 'hair_front', rot(cr([(-4.6, -1.1, 'c'), (4.6, -1.1, 'c'), (4.6, 1.1, 'c'), (-4.6, 1.1, 'c')], 3), a) + (x, y),
                col=c, lw=0.8)


def h_black_wolfcut(ctx):
    """검은 울프컷: 결이 삐친 레이어, 목덜미까지 내려오는 뒷머리, 커튼 앞머리."""
    S = HairStyle('#323036', hl='#6C6872', ln='#1C1A1E')
    if ctx.view != 'back':
        if ctx.q:
            for x, l, d in ((-22, 14, 14), (-15, 12, 6)):
                tail(ctx, S, (x, -8), d + ctx.sway * 3, l, 8.0, 5.0, 'hair_back')
        else:
            for x in (-24, -14, 14, 24):
                tail(ctx, S, (x, -12), -x * 0.5, 14, 7.0, 4.5, 'hair_back')
    tufts = [((-26, -40), (-35, -14), 7, 3), ((26, -40), (35, -14), 7, -3), ((-20, -50), (-34, -30), 7, 3), ((20, -50), (34, -30), 7, -3)]
    hair_base(ctx, S, vol=(35.0, 34.0, -29.0), side=-10, nape=-2, back_len=2, ear=False,
              bangs=[(-22, -27, 9, 3), (-12, -30, 11, 3), (-3, -33, 9, 2), (4, -33, 9, -2), (13, -30, 11, -3), (22, -27, 9, -3)],
              side_w=9.0, tufts=tufts, back_tips=11)
    if ctx.front:
        S.F(ctx, 'hair_front', ellipse(-28.0, -15.0, 1.3, 1.3, 12), col='#E4E6EC', lw=0.7)


def h_pink_bridge_ponytail(ctx):
    """핑크 브릿지 포니테일: 높은 포니테일, 얼굴 옆 잔머리에 분홍 브릿지."""
    S = HairStyle('#4E3D37', hl='#8E766C', ln='#2A1D18')
    pink = '#E3A0B8'
    if ctx.view == 'front':
        tail(ctx, S, (20, -52), -24 + ctx.sway * 4, 44, 14, 6, 'hair_back', curl=-6, streak=pink)
    elif ctx.q:
        tail(ctx, S, (-25, -52), -26 + ctx.sway * 10, 46, 15, 7, 'hair_back', curl=8, streak=pink)
    hair_base(ctx, S, vol=(33.0, 32.5, -29.5), side=-8, nape=-16, ear=True,
              bangs=[(-18, -31, 11, 0), (-7, -33.5, 12, 0), (5, -33, 12, 0), (17, -31, 11, 0)], side_w=6.5)
    sides = [1] if ctx.q else [-1, 1]
    for sx in sides:
        x = 25.5 * sx if not ctx.q else 27.0
        leaf(S, ctx, 'hair_front', (x - sx * 5, -46), (x + sx * 0.5 - ctx.sway * 0.5, -6), 3.6, bend=-sx * 1.5, col=pink, a=0.3, b=0.4)
    if ctx.view == 'back':
        tail(ctx, S, (0, -54), ctx.sway * 5, 44, 14, 6, 'hair_front', tie=pink, streak=pink)
    elif ctx.q:
        S.F(ctx, 'hair_front', rot(ellipse(0, 0, 2.8, 4.4, 16), 30) + (-26.5, -50), col=pink, lw=0.8)


def h_black_short(ctx):
    """검은 짧은 머리: 한쪽으로 쓸어내린 쉼표 앞머리."""
    S = HairStyle('#3D322E', hl='#7A6A64', ln='#221A17')
    hair_base(ctx, S, vol=(33.5, 33.0, -29.5), side=-22, nape=-14, ear=True,
              bangs=[(-22, -33, 10, 3), (-13, -31, 12, 4), (-3, -30.5, 13, 4), (7, -31.5, 12, 4), (17, -34, 11, 3)],
              side_w=6.5)


def h_brown_short(ctx):
    """밤색 짧은 머리: 가르마를 탄 부드러운 레이어."""
    S = HairStyle('#80604A', hl='#B8967E', ln='#4A3426')
    hair_base(ctx, S, vol=(34.0, 33.5, -29.5), side=-20, nape=-12, ear=True,
              bangs=[(-21, -32, 11, 3), (-11, -30, 12, 3), (-1, -33, 11, 3), (12, -35, 12, -4), (22, -32, 10, -3)],
              side_w=7.0)


def h_blonde_spiky(ctx):
    """금발 뻗친 머리: 텍스처 펌 느낌으로 위로 뻗은 결."""
    S = HairStyle('#E2C384', hl='#F6E6BE', ln='#9A7638', dk='#C29C58')
    tufts = [((-14, -44), (-30, -60), 10, -2), ((-4, -46), (-12, -68), 10, -2), ((6, -46), (8, -69), 10, 2),
             ((14, -44), (26, -64), 10, 2), ((20, -40), (35, -50), 9, 2), ((-20, -40), (-36, -48), 9, -2)]
    hair_base(ctx, S, vol=(33.5, 33.0, -29.5), side=-18, nape=-10, ear=True,
              bangs=[(-20, -34, 10, 2), (-9, -32, 11, 2), (2, -35, 10, 2), (13, -33, 11, -2), (22, -35, 9, -2)],
              side_w=6.5, tufts=tufts)


def h_pink_long(ctx):
    """분홍 긴 웨이브."""
    S = HairStyle('#E2B0BF', hl='#F6DCE4', ln='#A06A7C')
    long_back(ctx, S, length=42, width=35, wave=2.2)
    hair_base(ctx, S, vol=(34.5, 33.5, -29.0), side=12, nape=38, back_len=40, ear=False,
              bangs=[(-17, -31, 12, 0), (-6, -29.5, 12, 0), (6, -29.5, 12, 0), (17, -31, 12, 0)], side_w=10.0)
    if ctx.view != 'back':
        for sx in ([] if (ctx.q or ctx.prone) else [-1, 1]):
            x = 31.0 * sx
            c = bez((x - sx * 4, -30), (x + sx * 4, -14), (x - sx * 4, 2), (x + sx * 1.5 - ctx.sway, 20), 16)
            S.F(ctx, 'hair_front', taper(c, 8.5, a=0.1, b=0.3, wmin=0.6),
                shapes=[(taper(sub(c, 0.1, 0.4) + (-sx * 1.2, 0), 1.8, 0.3, 0.3), S.hl, 0.6)])


def h_sky_bob(ctx):
    """하늘색 단발: 턱선 길이, 끝이 안으로 말린다."""
    S = HairStyle('#A8C4D8', hl='#DCEAF3', ln='#5E7E96')
    long_back(ctx, S, length=0.0, width=34.5, inward=0.6, locks=4)
    hair_base(ctx, S, vol=(35.0, 33.5, -29.0), side=-1, nape=1, back_len=2, ear=False,
              bangs=[(-18, -33, 11, 0), (-8, -31, 11, 0), (2, -31.5, 11, 0), (12, -31, 11, 0), (21, -33, 10, 0)],
              side_w=10.0)


def h_tan_ponytail(ctx):
    """갈색 로우 포니테일: 가운데 가르마."""
    S = HairStyle('#946C50', hl='#C4A086', ln='#583E2C')
    tie = '#C8735E'
    if ctx.view == 'front':
        tail(ctx, S, (17, -22), -26 + ctx.sway * 4, 32, 12, 6, 'hair_back', curl=-3)
    elif ctx.q:
        tail(ctx, S, (-25, -24), -12 + ctx.sway * 8, 34, 13, 7, 'hair_back', curl=4)
    hair_base(ctx, S, vol=(33.0, 32.5, -29.5), side=-10, nape=-16, ear=True,
              bangs=[(-22, -31, 11, 4), (-10, -35.5, 12, 4), (10, -35.5, 12, -4), (22, -31, 11, -4)], side_w=7.0)
    if ctx.view == 'back':
        tail(ctx, S, (0, -24), ctx.sway * 5, 32, 12, 6, 'hair_front', tie=tie)
    elif ctx.q:
        S.F(ctx, 'hair_front', rot(ellipse(0, 0, 2.6, 4.0, 16), 15) + (-26.5, -23), col=tie, lw=0.8)


def h_black_twintail(ctx):
    """검은 양갈래 (낮게 묶은 투 테일)."""
    S = HairStyle('#38323C', hl='#6E6676', ln='#1E1A22')
    tie = '#C8735E'
    if ctx.view == 'front':
        for sx in (-1, 1):
            tail(ctx, S, (sx * 28, -26), sx * 14 + ctx.sway * 4, 40, 12, 6, 'hair_back', curl=sx * 4)
    elif ctx.q:
        tail(ctx, S, (25, -28), 12 + ctx.sway * 6, 38, 11, 6, 'hair_back', curl=-3)
    hair_base(ctx, S, vol=(33.0, 32.5, -29.5), side=-12, nape=-14, ear=False,
              bangs=[(-19, -31, 11, 0), (-8, -29.5, 12, 0), (4, -29.5, 12, 0), (15, -31, 11, 0)], side_w=7.0)
    if ctx.view == 'front':
        for sx in (-1, 1):
            S.F(ctx, 'hair_front', rot(ellipse(0, 0, 2.6, 4.0, 16), sx * 20) + (sx * 29.5, -26), col=tie, lw=0.8)
    elif ctx.q:
        tail(ctx, S, (-22, -28), -12 + ctx.sway * 8, 40, 12, 6, 'hair_front', curl=4, tie=tie)
    else:
        for sx in (-1, 1):
            tail(ctx, S, (sx * 27, -26), sx * 16 + ctx.sway * 4, 40, 12, 6, 'hair_front', curl=sx * 4, tie=tie)


def h_mint_curly(ctx):
    """민트 곱슬 (볼륨 펌): 실루엣 둘레가 둥근 컬로 부풀어 있다."""
    S = HairStyle('#A2CDBB', hl='#D8EEE4', ln='#5C8C7A')
    cx = 0 if not ctx.q else -4
    rx, ry, cy = 34.0, 33.5, -29.0
    lay = 'hair_back' if not ctx.back else 'hair_front'
    rs = np.random.RandomState(12)
    angs = list(range(152, 392, 27))
    for a in angs:
        r = 6.0 + rs.uniform(0, 2.2)
        a = a + rs.uniform(-6, 6)
        x = cx + (rx - 2.5) * math.cos(math.radians(a)); y = cy + (ry - 2.5) * math.sin(math.radians(a))
        if y > -6:
            continue
        S.F(ctx, lay, ellipse(x, y, r, r * 0.92, 20),
            shapes=[(taper(np.array(arc(x, y, r * 0.55, r * 0.5, 200, 330, 8)), 1.4, 0.3, 0.3), S.hl, 0.55)])
    hair_base(ctx, S, vol=(rx, ry, cy), side=-8, nape=-4, back_len=-2, ear=False,
              bangs=[(-20, -31, 12, 5), (-9, -29, 12, 6), (3, -29.5, 12, 6), (15, -31, 12, 5)], side_w=10.0)


HAIRS = {
    'ash-twoblock': h_ash_twoblock, 'black-seethrough': h_black_seethrough, 'black-wolfcut': h_black_wolfcut,
    'pink-bridge-ponytail': h_pink_bridge_ponytail, 'black-short': h_black_short, 'brown-short': h_brown_short,
    'blonde-spiky': h_blonde_spiky, 'pink-long': h_pink_long, 'sky-bob': h_sky_bob, 'tan-ponytail': h_tan_ponytail,
    'black-twintail': h_black_twintail, 'mint-curly': h_mint_curly,
}


def hair(ctx, hid):
    HAIRS[hid](ctx)
