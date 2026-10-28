"""레이어별 장면 구성 (사이클 9, 월드 4800x1000, 지면 y=900, 밀도 1.5).

sky     16x1500 세로 그라데이션 (stretchX)
clouds  3600x780  parallax 0.10  y 0     repeatX  뭉게구름
far     3600x900  parallax 0.25  y 340   repeatX  원경 산(눈 덮인 봉우리) + 벚꽃 언덕
mid     4500x660  parallax 0.55  y 480   repeatX  중경 숲 + 작은 버섯 집 (대기색 22% 섞음)
ground  7200x1500 parallax 1.00  y 0              지면, 발판, 마을, 큰 나무, 소품
"""
import numpy as np
from vec import Scene, mix
from geom import (circle, ellipse, catmull, rrect, rect, poly, move, scale, blob, scallop, qbez, bez)
from pal import M, H
import props as P
from platforms import PLATFORMS, WORLD_W, WORLD_H, GROUND_Y, DENSITY

D = DENSITY
GW, GH = int(WORLD_W * D), int(WORLD_H * D)      # 7200 x 1500
GY = GROUND_Y * D                                # 1350

LAYERS = {
    'clouds': dict(parallax=0.10, y=0, w=3600, h=780, repeat=True, haze=0.0),
    'far': dict(parallax=0.25, y=340, w=3600, h=900, repeat=True, haze=0.0),
    'mid': dict(parallax=0.55, y=480, w=4500, h=660, repeat=True, haze=0.28),
    'ground': dict(parallax=1.0, y=0, w=GW, h=GH, repeat=False, haze=0.0),
}

SKY_STOPS = [(0, '#58B4F0'), (420, '#7CCAF6'), (820, '#B4E4FC'), (1150, '#E2F6FF'), (1500, '#FFF4DE')]


def sub(rng):
    return np.random.default_rng(int(rng.integers(1 << 31)))


def wrapped(W, x, span, fn, rng):
    """반복 레이어: 경계를 넘는 물체는 ±W 위치에도 같은 난수로 다시 그린다."""
    seed = int(rng.integers(1 << 31))
    for off in (-W, 0, W):
        if x + off + span < -40 or x + off - span > W + 40:
            continue
        fn(x + off, np.random.default_rng(seed))


def periodic(W, xs, terms, rng):
    """주기 W 인 부드러운 함수 값 (정수 배 주파수 사인 합)."""
    y = np.zeros_like(xs, dtype=np.float64)
    for (k, amp) in terms:
        ph = rng.uniform(0, 2 * np.pi)
        y += amp * np.sin(2 * np.pi * k * xs / W + ph)
    return y


# ---------------------------------------------------------------------------
# 구름

def build_clouds():
    L = LAYERS['clouds']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(901)
    # 큰 뭉게구름 (위쪽) → 작은 구름 (아래, 멀리)
    spec = []
    x = 80.0
    while x < W:
        big = rng.random() < 0.55
        w = rng.uniform(300, 470) if big else rng.uniform(150, 250)
        y = rng.uniform(110, 330) if big else rng.uniform(380, 640)
        spec.append((x, y, w))
        x += w * rng.uniform(0.75, 1.35) + rng.uniform(60, 220)
    # 먼(작은) 구름 먼저
    for (x, y, w) in sorted(spec, key=lambda c: c[2]):
        h = w * rng.uniform(0.32, 0.4)
        tone = P.M['cloud'] if w > 280 else {k: mix(v, '#BFE4FA', 0.25) for k, v in P.M['cloud'].items()}
        wrapped(W, x, w * 0.6, lambda xx, r, y=y, w=w, h=h, tone=tone: P.cloud(s, xx, y, w, h, r, tone, lw=2.2 if w > 280 else 1.8), rng)
    # 납작한 띠 구름
    for i in range(7):
        x = rng.uniform(0, W)
        y = rng.uniform(560, 740)
        w = rng.uniform(160, 300)
        wrapped(W, x, w, lambda xx, r, y=y, w=w: _flat_cloud(s, xx, y, w, r), rng)
    return s


def _flat_cloud(s, x, y, w, rng):
    m = {k: mix(v, '#CDEBFA', 0.35) for k, v in P.M['cloud'].items()}
    polys = [ellipse(x, y, w / 2, 9)] + [ellipse(x + rng.uniform(-w * 0.3, w * 0.3), y - 6, w * rng.uniform(0.15, 0.25), 10) for _ in range(3)]
    s.shape(polys, m['shade'], m['line'], 1.6)
    s.clip(polys)
    for p in polys:
        s.fill(move(p, -3, -3), m['base'])
    s.unclip()


# ---------------------------------------------------------------------------
# 원경

def _range(s, W, Hh, base_y, peaks, m, snow, rng, lw=2.2):
    """주기적인 산맥. 봉우리마다 따로 그린다(높은 봉우리가 뒤). peaks = [(x, top_y, half_width)]."""
    pk = []
    for (px_, py_, hw) in peaks:
        for off in (-W, 0, W):
            if px_ + off + hw * 1.1 < -40 or px_ + off - hw * 1.1 > W + 40:
                continue
            pk.append((px_ + off, py_, hw, int(rng.integers(1 << 30))))
    for (px_, py_, hw, seed) in sorted(pk, key=lambda q: q[1]):
        r = np.random.default_rng(seed)
        hh = base_y - py_
        xs = np.linspace(px_ - hw * 1.05, px_ + hw * 1.05, 70)
        d = np.abs(xs - px_) / hw
        ys = py_ + hh * np.clip(d, 0, 1.05) ** 1.15 * (1 - 0.12 * np.sin(d * 7.0 + r.uniform(0, 3)) * d)
        ys += r.uniform(-2, 2, len(xs)) * d
        body = np.concatenate([np.stack([xs, ys], -1), [[px_ + hw * 1.05, Hh + 20], [px_ - hw * 1.05, Hh + 20]]])
        s.shape(body, m['base'], m['line'], lw)
        s.clip(body)
        ridge = catmull([(px_, py_), (px_ + hw * 0.12, py_ + hh * 0.3), (px_ + hw * 0.04, py_ + hh * 0.6), (px_ + hw * 0.18, base_y + 10)], False, 8)
        sh = np.concatenate([ridge, [[px_ + hw * 1.3, base_y + 10], [px_ + hw * 1.3, py_ - 10], [px_, py_ - 10]]])
        s.fill(sh, m['shade'])
        # 왼쪽 면 계곡 결
        s.stroke(catmull([(px_ - hw * 0.35, py_ + hh * 0.35), (px_ - hw * 0.3, py_ + hh * 0.6), (px_ - hw * 0.42, py_ + hh * 0.85)], False, 8),
                 m['shade'], 2.0, alpha=0.8)
        s.stroke(ridge, m['deep'], 1.4, alpha=0.5)
        if snow and hh > 200:
            cap_h = hh * 0.28
            n = 9
            zx = np.linspace(px_ - hw * 0.5, px_ + hw * 0.5, n)
            zy = py_ + cap_h * (0.55 + 0.45 * np.abs(np.linspace(-1, 1, n))) + r.uniform(-8, 10, n)
            cap = np.concatenate([[[px_ - hw * 0.7, py_ - 30], [px_ + hw * 0.7, py_ - 30]], np.stack([zx, zy], -1)[::-1]])
            s.clip(cap)
            s.fill(cap, '#FFFFFF')
            s.fill(np.concatenate([ridge, [[px_ + hw, base_y], [px_ + hw, py_ - 30], [px_, py_ - 30]]]), '#D6DEF8')
            s.unclip()
            s.stroke(np.stack([zx, zy], -1), m['line'], 1.4, alpha=0.45)
        s.unclip()


def build_far():
    L = LAYERS['far']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(902)
    # 뒷 산맥
    m1 = dict(base='#BFC6F2', shade='#A3AAE2', deep='#8F96D2', line='#7C82C0', hi='#D8DCFA')
    peaks = []
    x = 0.0
    while x < W - 120:
        hw = rng.uniform(170, 300)
        peaks.append((x + hw * 0.5, rng.uniform(40, 200), hw))
        x += hw * rng.uniform(0.85, 1.25)
    _range(s, W, Hh, 520, peaks, m1, True, rng)
    # 앞 산맥 (푸른 녹색)
    m2 = dict(base='#A6D4E6', shade='#8ABCD8', deep='#76A6C8', line='#5E8CB4', hi='#C8E8F2')
    peaks2 = []
    x = 60.0
    while x < W - 100:
        hw = rng.uniform(150, 240)
        peaks2.append((x + hw * 0.5, rng.uniform(300, 420), hw))
        x += hw * rng.uniform(1.0, 1.6)
    _range(s, W, Hh, 640, peaks2, m2, False, rng)
    # 폭포 두 줄기 (앞 산맥 사이)
    for fx in (W * 0.27, W * 0.71):
        _falls(s, fx, 470, 680, rng)
    # 벚꽃 언덕
    xs = np.arange(-60, W + 61, 6.0)
    hy = 640 + periodic(W, xs, [(5, 26), (11, 12), (19, 5)], rng)
    hill = np.concatenate([np.stack([xs, hy], -1), [[W + 60, Hh + 20], [-60, Hh + 20]]])
    mh = dict(base='#A8DDB0', shade='#8CC89C', deep='#76B48A', line='#5E9A78', hi='#C8EEC8')
    s.shape(hill, mh['base'], mh['line'], 2.0)
    s.clip(hill)
    s.fill(np.concatenate([np.stack([xs, hy + 26], -1), [[W + 60, Hh + 20], [-60, Hh + 20]]]), mh['shade'])
    s.unclip()
    # 언덕 위 나무(벚꽃, 초록), 작은 침엽수
    x = 10.0
    while x < W:
        k = rng.random()
        yb = 640 + 4
        if k < 0.45:
            kind = 'cherry'
        elif k < 0.8:
            kind = 'leaf'
        else:
            kind = 'pine'
        size = rng.uniform(26, 44)
        def draw(xx, r, size=size, kind=kind):
            hyy = 640 + _periodic_at(W, xx % W, [(5, 26), (11, 12), (19, 5)], np.random.default_rng(902 + 1000)) + 6
            if kind == 'pine':
                P.pine(s, xx, hyy, size * 1.6, r, {kk: mix(v, '#CDEBFA', 0.35) for kk, v in M['leaf2'].items()}, lw=1.6)
            else:
                _round_tree_far(s, xx, hyy, size, r, kind)
        wrapped(W, x, 60, draw, rng)
        x += rng.uniform(26, 70)
    # 아래쪽 언덕 띠 2
    hy2 = 760 + periodic(W, xs, [(7, 18), (13, 8)], rng)
    hill2 = np.concatenate([np.stack([xs, hy2], -1), [[W + 60, Hh + 20], [-60, Hh + 20]]])
    mh2 = dict(base='#9AD69C', shade='#7EC488', deep='#68AE78', line='#4E8E66', hi='#BDEBB4')
    s.shape(hill2, mh2['base'], mh2['line'], 2.0)
    s.clip(hill2)
    s.fill(np.concatenate([np.stack([xs, hy2 + 22], -1), [[W + 60, Hh + 20], [-60, Hh + 20]]]), mh2['shade'])
    s.unclip()
    return s


def _periodic_at(W, x, terms, rng):
    v = periodic(W, np.array([x], np.float64), terms, rng)
    return float(v[0])


def _round_tree_far(s, x, gy, size, rng, kind):
    m = {k: mix(v, '#CDEBFA', 0.3) for k, v in M[kind].items()}
    mt = {k: mix(v, '#CDEBFA', 0.3) for k, v in M['trunk'].items()}
    s.shape(rect(x - size * 0.07, gy - size * 0.7, x + size * 0.07, gy + 2), mt['base'], mt['line'], 1.5)
    cl = [(x + rng.uniform(-0.3, 0.3) * size, gy - size * rng.uniform(0.85, 1.15), size * rng.uniform(0.32, 0.42)) for _ in range(4)]
    cl.append((x, gy - size * 0.95, size * 0.45))
    polys = [circle(a, b, c) for a, b, c in cl]
    s.shape(polys, m['shade'], m['line'], 1.6)
    s.clip(polys)
    for (a, b, c) in cl:
        s.fill(circle(a - c * 0.12, b - c * 0.16, c * 0.84), m['base'])
    s.unclip()


def _falls(s, x, y0, y1, rng):
    w = 22
    p = poly([(x - w / 2, y0), (x + w / 2, y0), (x + w / 2 + 4, y1), (x - w / 2 - 4, y1)])
    s.shape(p, '#C8EEFF', '#6EA8D8', 1.6)
    s.clip(p)
    for i in range(4):
        xx = x - w / 2 + 3 + i * 5.5
        s.stroke(poly([(xx, y0), (xx + 1, y1)]), '#FFFFFF', 1.6, alpha=0.8)
    s.unclip()
    for i in range(5):
        s.shape(circle(x + rng.uniform(-18, 18), y1 + rng.uniform(-6, 4), rng.uniform(7, 12)), '#FFFFFF', '#A8D2F0', 1.4)


# ---------------------------------------------------------------------------
# 중경

def rng_h(r):
    return r.uniform(70, 95)


def build_mid():
    L = LAYERS['mid']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(903)
    xs = np.arange(-80, W + 81, 5.0)
    terms_back = [(4, 30), (9, 16), (17, 6)]
    rb = np.random.default_rng(9031)
    hb = 360 + periodic(W, xs, terms_back, rb)

    def hb_at(x):
        return 360 + _periodic_at(W, x % W, terms_back, np.random.default_rng(9031))

    # 뒷줄 나무 (언덕 뒤)
    x = 0.0
    while x < W:
        kind = ['leaf', 'leaf2', 'cherry', 'leaf', 'cherry'][int(rng.integers(5))]
        size = rng.uniform(70, 110)
        wrapped(W, x, size, lambda xx, r, size=size, kind=kind: P.tree(s, xx, hb_at(xx) + 30, size, r, kind, lw=2.2), rng)
        x += rng.uniform(55, 120)
    # 언덕 1
    hill = np.concatenate([np.stack([xs, hb], -1), [[W + 80, Hh + 20], [-80, Hh + 20]]])
    mg = M['grass']
    s.shape(hill, mg['base'], mg['line'], 2.4)
    s.clip(hill)
    s.fill(np.concatenate([np.stack([xs, hb + 12], -1), [[W + 80, Hh + 20], [-80, Hh + 20]]]), mg['shade'])
    s.fill(np.concatenate([np.stack([xs, hb - 2], -1), np.stack([xs, hb + 5], -1)[::-1]]), mg['hi'])
    s.unclip()
    # 언덕 위 작은 버섯 집과 울타리
    caps = ['cap_red', 'cap_orange', 'cap_blue', 'cap_yellow', 'cap_purple', 'cap_pink']
    hx = [260, 980, 1700, 2350, 3050, 3800]
    for i, x in enumerate(hx):
        w = rng.uniform(110, 150)
        cap = caps[i % len(caps)]

        def dh(xx, r, w=w, cap=cap):
            gy = hb_at(xx) + 8
            P.mushroom_house(s, xx, gy, w, w * 1.3, cap, r, lw=2.2, windows=1 + int(r.random() < 0.5), detail=0.5)
            P.fence(s, xx + w * 0.45, xx + w * 0.45 + 70, gy + 2, h=24, lw=1.8)
        wrapped(W, x, 120, dh, rng)
    # 앞 언덕
    terms_f = [(6, 20), (13, 9)]
    hf = 470 + periodic(W, xs, terms_f, np.random.default_rng(9032))

    def hf_at(x):
        return 470 + _periodic_at(W, x % W, terms_f, np.random.default_rng(9032))
    x = 30.0
    while x < W:
        kind = ['leaf2', 'leaf', 'cherry'][int(rng.integers(3))]
        size = rng.uniform(90, 140)
        wrapped(W, x, size, lambda xx, r, size=size, kind=kind: P.tree(s, xx, hf_at(xx) + 30, size, r, kind, lw=2.4), rng)
        x += rng.uniform(160, 340)
    hill2 = np.concatenate([np.stack([xs, hf], -1), [[W + 80, Hh + 20], [-80, Hh + 20]]])
    s.shape(hill2, mg['shade'], mg['line'], 2.4)
    s.clip(hill2)
    s.fill(np.concatenate([np.stack([xs, hf - 2], -1), np.stack([xs, hf + 5], -1)[::-1]]), mg['base'])
    s.unclip()
    # 앞 언덕 덤불
    x = 0.0
    while x < W:
        w = rng.uniform(70, 140)
        wrapped(W, x, w, lambda xx, r, w=w: P.bush(s, xx, hf_at(xx) + 16, w, w * 0.42, r, M['leaf2'], lw=2.2,
                                                  flowers=['cap_pink', 'cap_yellow'] if r.random() < 0.4 else None), rng)
        x += rng.uniform(90, 200)
    # 바닥 띠 (지면 레이어가 덮는 곳) + 산울타리
    s.fill(rect(-80, 590, W + 80, Hh + 20), M['leaf2']['deep'])
    x = 0.0
    while x < W:
        ww = rng.uniform(90, 160)
        wrapped(W, x, ww, lambda xx, r, ww=ww: P.bush(s, xx, 640, ww, rng_h(r), r, M['leaf2'], lw=2.2), rng)
        x += ww * 0.62
    return s


# ---------------------------------------------------------------------------
# 발판

def plank_boards(s, x0, x1, Y, rng, th=15, m=None):
    m = m or M['wood']
    xs = [x0]
    while xs[-1] < x1 - 1e-6:
        bw = rng.uniform(26, 42)
        nx = min(x1, xs[-1] + bw)
        if x1 - nx < 14:
            nx = x1
        xs.append(nx)
    boards = []
    for a, b in zip(xs[:-1], xs[1:]):
        bb = th + rng.uniform(-1.5, 1.5)
        boards.append((a, b, bb))
    # 외곽선(전체), 판자별 채움
    allp = [poly([(a, Y), (b, Y), (b, Y + bb), (a, Y + bb)]) for a, b, bb in boards]
    s.shape(allp, m['shade'], m['line'], P.LW)
    for (a, b, bb) in boards:
        tone = m['base'] if rng.random() < 0.7 else mix(m['base'], m['shade'], 0.35)
        s.fill(rect(a + 0.8, Y, b - 0.8, Y + bb - 3.5), tone)
        s.fill(rect(a + 0.8, Y, b - 0.8, Y + 3), m['hi'])
        s.stroke(poly([(b, Y + 1), (b, Y + bb)]), m['line'], 1.6)
        # 못
        for nx in (a + 5, b - 5):
            s.fill(circle(nx, Y + bb * 0.55, 1.5, 8), m['deep'])
        if rng.random() < 0.5:
            yy = Y + rng.uniform(5, bb - 4)
            s.stroke(poly([(a + 6, yy), (a + (b - a) * rng.uniform(0.4, 0.8), yy)]), m['shade'], 1.0)
    return boards


def lashing(s, x, y0, y1, m=None):
    m = m or M['rope']
    p = rrect(x - 4.5, y0, x + 4.5, y1, 2)
    s.shape(p, m['base'], m['line'], 1.8)
    s.clip(p)
    yy = y0 + 2
    while yy < y1:
        s.stroke(poly([(x - 6, yy + 3), (x + 6, yy - 1)]), m['shade'], 1.3)
        yy += 4
    s.fill(rect(x + 1.5, y0, x + 5, y1), m['shade'], alpha=0.6)
    s.unclip()


def plat_plank(s, x0, x1, Y, rng):
    w = x1 - x0
    wd = M['darkwood']
    # 받침 통나무
    log = rrect(x0 + 10, Y + 12, x1 - 10, Y + 26, 7)
    P.toon(s, [log], wd, P.LW, shift=(0, -0.25), shrink=1.0)
    for ex in (x0 + 14, x1 - 14):
        s.shape(ellipse(ex, Y + 19, 5.5, 7.5), M['wood']['hi'], wd['line'], 1.6)
        s.outline(ellipse(ex, Y + 19, 2.4, 3.4), M['wood']['shade'], 0.6)
    plank_boards(s, x0, x1, Y, rng)
    n = max(2, int(w / 120) + 1)
    lx = np.linspace(x0 + 16, x1 - 16, n)
    for i, x in enumerate(lx):
        lashing(s, x, Y + 1, Y + 28)
        if rng.random() < 0.6:
            P.rope_coil_hang(s, x + 2, Y + 28, rng.uniform(14, 30), rng)
    # 덩굴
    for _ in range(int(rng.integers(1, 3))):
        vx = rng.uniform(x0 + 30, x1 - 30)
        P.vine(s, vx, Y + 20, rng.uniform(30, 60), rng)


def plat_grass(s, x0, x1, Y, rng, deep=None, sky=False):
    w = x1 - x0
    Dd = deep or float(np.clip(40 + w * 0.03, 44, 54))
    if sky:
        pts = [(x0 - 3, Y + 6), (x0 + 6, Y + Dd * 0.45), (x0 + w * 0.3, Y + Dd * 0.85), (x0 + w * 0.5, Y + Dd * 1.25),
               (x0 + w * 0.68, Y + Dd * 0.8), (x1 - 6, Y + Dd * 0.4), (x1 + 3, Y + 6)]
        body = catmull(pts, False, 10)
    else:
        bx = np.linspace(x1 - 14, x0 + 14, max(4, int(w / 22)))
        by = Y + Dd + rng.uniform(-4, 3, len(bx))
        pts = [(x0 - 3, Y + 6), (x0 + 1, Y + Dd * 0.7)] + list(zip(bx[::-1], by[::-1])) + [(x1 - 1, Y + Dd * 0.7), (x1 + 3, Y + 6)]
        body = catmull(pts, False, 8)
    P.dirt_body(s, body, M['dirt'], rng, Y + 8, strata=True, stones=max(1, int(w / 60)))
    # 아래 가장자리 그늘
    if sky:
        for (cx, h_) in ((x0 + w * 0.42, 22), (x0 + w * 0.56, 16)):
            cy = Y + Dd * 0.75
            s.shape(poly([(cx - 6, cy), (cx, cy + h_), (cx + 6, cy)]), '#C8B4FF', '#6A4AB0', 1.6)
            s.fill(poly([(cx - 3, cy + 1), (cx, cy + h_ * 0.8), (cx, cy + 1)]), '#EEE6FF')
    P.grass_cap(s, x0, x1, Y, 17, rng, drip=8)
    # 덩굴
    for _ in range(int(rng.integers(1, 3)) if w > 160 else 1):
        vx = rng.uniform(x0 + 20, x1 - 20)
        P.vine(s, vx, Y + 20, rng.uniform(30, 60) + Dd * 0.5, rng)
    P.grass_top_blades(s, x0 + 4, x1 - 4, Y, rng, every=34, hmax=8)


def plat_bridge(s, x0, x1, Y, rng):
    wd = M['darkwood']
    rp = M['rope']
    sag = 18
    ph = 46
    posts = (x0 + 7, x1 - 7)
    rail_y = Y - ph + 8
    xs = np.linspace(posts[0], posts[1], 60)
    t = (xs - posts[0]) / (posts[1] - posts[0])
    rail = np.stack([xs, rail_y + sag * 4 * t * (1 - t)], -1)
    # 뒤 난간 (흐리게)
    P.rope(s, move(rail, 0, -4), {k: mix(v, '#B4E4FC', 0.35) for k, v in rp.items()}, 3.0, twist=False)
    # 기둥
    for px_ in posts:
        p = rrect(px_ - 6, Y - ph, px_ + 6, Y + 34, 3)
        P.toon(s, [p], wd, P.LW, shift=(-0.25, 0), shrink=1.0)
        s.shape(circle(px_, Y - ph - 2, 7.5), wd['base'], wd['line'], 2.0)
        s.fill(circle(px_ - 2, Y - ph - 4, 2.6), wd['hi'])
    # 아래 밧줄
    P.rope(s, poly([(posts[0], Y + 11), (posts[1], Y + 11)]), rp, 3.4)
    # 판자 (사이에 틈)
    x = x0
    while x < x1 - 1e-6:
        bw = min(x1 - x, rng.uniform(17, 21))
        if x1 - (x + bw) < 8:
            bw = x1 - x
        b = rrect(x + 0.5, Y, x + bw - 0.5, Y + 10, 1.5)
        s.shape(b, M['wood']['shade'], M['wood']['line'], 1.8)
        s.fill(rect(x + 1.5, Y, x + bw - 1.5, Y + 6.5), M['wood']['base'] if rng.random() < 0.75 else M['wood']['hi'])
        s.fill(rect(x + 1.5, Y, x + bw - 1.5, Y + 2.2), M['wood']['hi'])
        x += bw
    # 앞 난간 + 걸이 줄
    for xx in np.arange(posts[0] + 26, posts[1] - 10, 30):
        tt = (xx - posts[0]) / (posts[1] - posts[0])
        ry = rail_y + sag * 4 * tt * (1 - tt)
        s.stroke(poly([(xx, ry), (xx, Y + 1)]), rp['line'], 3.2)
        s.stroke(poly([(xx, ry), (xx, Y + 1)]), rp['base'], 1.4)
    P.rope(s, rail, rp, 3.6)
    for px_ in posts:
        lashing(s, px_, rail_y - 6, rail_y + 6)
    # 깃발 장식
    for i, xx in enumerate(np.linspace(posts[0] + 40, posts[1] - 40, max(2, int((x1 - x0) / 90)))):
        tt = (xx - posts[0]) / (posts[1] - posts[0])
        ry = rail_y + sag * 4 * tt * (1 - tt) + 2
        cm = M[['cap_red', 'cap_yellow', 'cap_blue', 'cap_pink'][i % 4]]
        s.shape(poly([(xx - 7, ry), (xx + 7, ry), (xx, ry + 14)]), cm['base'], cm['line'], 1.4)


def plat_deck(s, x0, x1, Y, rng):
    wd = M['darkwood']
    w = x1 - x0
    n = 2 if w < 230 else 3
    px_ = np.linspace(x0 + 14, x1 - 14, n)
    # 기둥 + 짧은 무릎 버팀대
    for i, x in enumerate(px_):
        for sgn in (-1, 1):
            if (i == 0 and sgn < 0) or (i == len(px_) - 1 and sgn > 0):
                continue
            p0, p1 = (x, Y + 50), (x + sgn * 34, Y + 16)
            s.stroke(poly([p0, p1]), wd['line'], 8.0)
            s.stroke(poly([p0, p1]), wd['shade'], 3.8)
    for x in px_:
        p = rect(x - 6, Y + 6, x + 6, GY + 2)
        P.toon(s, [p], wd, P.LW, shift=(-0.3, 0), shrink=1.0)
        for yy in np.arange(Y + 60, GY - 20, 70):
            s.stroke(poly([(x - 5, yy), (x + 5, yy + 3)]), wd['deep'], 1.4)
        lashing(s, x, GY - 70, GY - 52)
    # 들보
    beam = rrect(x0 + 4, Y + 10, x1 - 4, Y + 22, 3)
    P.toon(s, [beam], wd, P.LW, shift=(0, -0.3), shrink=1.0)
    plank_boards(s, x0, x1, Y, rng)
    # 화분 매달기 / 랜턴
    lx = x0 + w * rng.uniform(0.35, 0.65)
    s.stroke(poly([(lx, Y + 22), (lx, Y + 38)]), M['metal']['line'], 2)
    s.fill(circle(lx, Y + 48, 16), '#FFF3B0', alpha=0.25)
    s.shape(rrect(lx - 7, Y + 38, lx + 7, Y + 56, 3), M['window']['base'], M['metal']['line'], 2.0)
    s.fill(rect(lx - 4, Y + 41, lx - 1, Y + 53), M['window']['hi'])


def plat_sky(s, x0, x1, Y, rng):
    plat_grass(s, x0, x1, Y, rng, deep=56, sky=True)
    # 금빛 버섯 (끝 쪽, 작은 장식)
    gx = x1 - 16
    s.fill(circle(gx, Y - 10, 18), '#FFF3B0', alpha=0.35)
    P.small_shroom(s, gx, Y + 2, 9, 'cap_yellow', rng)
    for (sx, sy) in ((gx - 16, Y - 22), (gx + 10, Y - 26)):
        s.fill(poly([(sx, sy - 5), (sx + 1.4, sy - 1.4), (sx + 5, sy), (sx + 1.4, sy + 1.4), (sx, sy + 5), (sx - 1.4, sy + 1.4), (sx - 5, sy), (sx - 1.4, sy - 1.4)]), '#FFFBE0')


PLAT_FN = dict(grass=plat_grass, plank=plat_plank, bridge=plat_bridge, deck=plat_deck, sky=plat_sky)


def draw_platforms(s, rng, only=None):
    # 높은 층부터 (낮은 층이 앞)
    for p in sorted(PLATFORMS, key=lambda q: q['y']):
        if only and p['id'] not in only:
            continue
        r = np.random.default_rng(abs(hash_id(p['id'])))
        # 외곽선(LW) 윗끝이 서는 선과 같도록 채움 윗면을 LW 만큼 내린다
        PLAT_FN[p['kind']](s, p['x1'] * D, p['x2'] * D, p['y'] * D + P.LW, r)


def hash_id(s_):
    h = 2166136261
    for ch in s_.encode():
        h = ((h ^ ch) * 16777619) & 0xFFFFFFFF
    return h


# ---------------------------------------------------------------------------
# 지면

def ground_terrain(s, rng):
    W = GW
    dm = M['dirt']
    top = GY + 10
    body = rect(-20, top, W + 20, GH + 20)
    s.fill(body, dm['base'], grad=[(top, dm['base']), (GH, dm['shade'])])
    s.clip(body)
    # 지층 띠
    xs = np.arange(-20, W + 21, 8.0)
    for i, yy in enumerate((GY + 62, GY + 104, GY + 140)):
        wv = yy + 5 * np.sin(xs / 140 + i * 1.7) + 3 * np.sin(xs / 47 + i)
        band = np.concatenate([np.stack([xs, wv], -1), np.stack([xs, wv + 60], -1)[::-1]])
        s.fill(band, [dm['shade'], dm['deep'], dm['deep']][i], alpha=0.35 + 0.15 * i)
        s.stroke(np.stack([xs, wv], -1), dm['line'], 1.8, alpha=0.5)
    # 흙 점
    for _ in range(int(W / 9)):
        x, y = rng.uniform(0, W), rng.uniform(top + 6, GH)
        s.fill(ellipse(x, y, rng.uniform(1.6, 3.4), rng.uniform(1.0, 2.0), 8), dm['deep'], alpha=0.55)
        if rng.random() < 0.3:
            s.fill(ellipse(x - 2, y - 2, 1.5, 1, 6), dm['hi'], alpha=0.6)
    # 묻힌 돌
    x = rng.uniform(20, 80)
    while x < W:
        y = rng.uniform(GY + 48, GH - 6)
        P.pebble_in(s, x, y, rng.uniform(7, 16), rng, M['stone'], lw=2.2)
        if rng.random() < 0.4:
            P.pebble_in(s, x + rng.uniform(14, 24), y + rng.uniform(-4, 6), rng.uniform(4, 8), rng, M['stone'], lw=1.8)
        x += rng.uniform(70, 170)
    # 잔디 아래 그늘 띠
    s.fill(np.concatenate([np.stack([xs, GY + 30 + 4 * np.sin(xs / 37)], -1), np.stack([xs, GY + 46 + 3 * np.sin(xs / 23)], -1)[::-1]]),
           dm['shade'], alpha=0.8)
    # 뿌리
    for _ in range(int(W / 260)):
        rx = rng.uniform(0, W)
        ln = catmull([(rx, GY + 24), (rx + rng.uniform(-8, 8), GY + 38), (rx + rng.uniform(-16, 16), GY + rng.uniform(50, 66))], False, 8)
        s.stroke(ln, dm['deep'], 4.0)
        s.stroke(ln, dm['hi'], 1.4, alpha=0.6)
    s.unclip()
    P.grass_cap(s, -10, W + 10, GY + P.LW, 26, rng, round_ends=False, drip=11)


def giant_tree(s, x, cy, rx, rng):
    """엘리니아풍 거대 나무: 굵은 줄기가 지면에서 수관까지, 수관에서 덩굴이 늘어진다."""
    mt = M['trunk']
    tw = rx * 0.28
    P.trunk(s, x, GY + 4, cy + rx * 0.2, tw, rng, mt, lean=rng.uniform(-10, 10), branches=True)
    # 뿌리 둔덕
    for sgn in (-1, 1):
        root = catmull([(x + sgn * tw * 0.3, GY - 60), (x + sgn * tw * 1.1, GY - 14), (x + sgn * tw * 1.8, GY + 4), (x + sgn * tw * 0.4, GY + 6)], True, 8)
        P.toon(s, [root], mt, P.LW, shift=(-0.1, -0.1), shrink=0.9)
    # 수관: 넓게 퍼진 두 겹(뒤는 짙게)
    back = {k: mix(v, '#1B4E2E', 0.18) for k, v in M['leaf2'].items()}
    P.canopy(s, x + rx * 0.15, cy - rx * 0.12, rx * 1.05, rx * 0.5, rng, back, k=10, tufts=False)
    cl = P.canopy(s, x - rx * 0.05, cy + rx * 0.05, rx * 1.2, rx * 0.6, rng, M['leaf2'], k=16)
    for _ in range(6):
        vx = x + rng.uniform(-rx * 0.8, rx * 0.8)
        vy = cy + rx * 0.62 * 0.55 * np.sqrt(max(0.0, 1 - ((vx - x) / (rx * 0.95)) ** 2)) + 10
        P.vine(s, vx, vy, rng.uniform(50, 120), rng, M['leaf2'])


def build_ground():
    s = Scene(GW, GH)
    rng = np.random.default_rng(904)
    w = lambda v: v * D  # 월드 → px

    # --- 뒤쪽 큰 소품 (지면선에 선다) ---
    # 서쪽 들판: 큰 둥근 나무
    for (x, size, kind) in ((40, 150, 'leaf'), (600, 170, 'leaf'), (1080, 130, 'cherry'), (1420, 120, 'leaf'), (260, 110, 'cherry')):
        P.tree(s, w(x), GY + 4, size, sub(rng), kind)
    # 마을: 버섯 집들
    houses = [(1960, 300, 400, 'cap_red', 2), (2180, 220, 300, 'cap_orange', 1), (2760, 260, 350, 'cap_blue', 2),
              (3130, 210, 280, 'cap_yellow', 1)]
    P.tree(s, w(2330), GY + 4, 150, sub(rng), 'cherry')
    P.tree(s, w(2960), GY + 4, 165, sub(rng), 'leaf')
    for (x, ww, hh, cap, nw) in houses:
        P.mushroom_house(s, w(x), GY + 2, ww, hh, cap, sub(rng), windows=nw)
    # 동쪽 숲 (엘리니아): 거대한 나무 기둥 + 큰 수관 (발판 뒤)
    for (x, cy, rx) in ((3580, 300, 250), (4250, 360, 230), (4700, 300, 210), (3150, 380, 170)):
        giant_tree(s, w(x), w(cy), rx, sub(rng))
    # 동쪽 숲: 크고 짙은 나무, 벚꽃, 침엽수
    for (x, size, kind) in ((3290, 185, 'leaf2'), (3760, 150, 'cherry'), (4150, 200, 'leaf2'), (4520, 160, 'leaf'), (4780, 170, 'leaf2')):
        P.tree(s, w(x), GY + 4, size, sub(rng), kind)

    # --- 지면 ---
    ground_terrain(s, rng)

    # --- 지면 소품 (앞) ---
    rr = sub(rng)
    # 덤불
    for x in (150, 470, 880, 1230, 1460, 3400, 3620, 3980, 4300, 4650):
        P.bush(s, w(x), GY + 3, rr.uniform(70, 120), rr.uniform(34, 46), rr, M['leaf'] if x < 2400 else M['leaf2'],
               flowers=['cap_pink', 'cap_yellow', 'cap_purple'] if rr.random() < 0.6 else None)
    # 마을 울타리, 가로등, 우물, 표지판, 통, 상자
    P.fence(s, w(1560), w(1620), GY + 2)
    P.fence(s, w(2050), w(2110), GY + 2)
    P.fence(s, w(2830), w(2900), GY + 2)
    P.fence(s, w(3190), w(3240), GY + 2)
    for x in (1860, 2250, 2620, 3040):
        P.lamp(s, w(x), GY + 2)
    P.well(s, w(2510), GY + 2)
    P.signpost(s, w(1590), GY + 2, rr)
    P.signpost(s, w(3215), GY + 2, rr)
    P.barrel(s, w(2125), GY + 2)
    P.barrel(s, w(2142), GY + 2, r=12)
    P.crate(s, w(2680), GY + 2, 30)
    P.crate(s, w(2700), GY + 2, 22)
    P.barrel(s, w(3070), GY + 2)
    # 바위
    for (x, r) in ((330, 16), (1010, 22), (1380, 12), (3530, 24), (3900, 14), (4420, 20), (4720, 13)):
        P.rock(s, w(x), GY + 3, r, rr)
    # 작은 버섯
    for x in (260, 700, 1180, 1540, 3340, 3700, 3720, 4080, 4250, 4600):
        cap = ['cap_orange', 'cap_red', 'cap_purple'][int(rr.integers(3))]
        P.small_shroom(s, w(x), GY + 3, rr.uniform(8, 13), cap, rr)
    # 풀과 꽃 (전 구간)
    x = 6.0
    while x < GW - 6:
        k = rr.random()
        if k < 0.55:
            P.tuft(s, x, GY + 3, rr.uniform(9, 15), rr)
        elif k < 0.85:
            col = ['cap_pink', 'cap_yellow', 'cap_purple', 'cap_red', 'cap_blue'][int(rr.integers(5))]
            for j in range(int(rr.integers(1, 4))):
                P.flower(s, x + j * 9, GY - rr.uniform(9, 16), rr.uniform(3.2, 4.4), col)
        x += rr.uniform(20, 46)

    # --- 발판 (맨 앞) ---
    draw_platforms(s, rng)
    return s
