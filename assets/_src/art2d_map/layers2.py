"""v2 감성 일러스트 레이어 (사이클 9 재작업). 파일명, 크기, parallax 는 v1(layers.py)과 같다.

톤: 채도 낮은 세이지/올리브/크림/웜그레이/테라코타/더스티 블루. 원경일수록 옅고(대기원근), 능선 사이에 안개.
하늘: 피치 → 더스티 블루. 구름: 외곽선 없는 볼륨. 마을: 나무와 흰 벽의 카페, 베이커리, 작은 상점.
"""
import numpy as np
from vec import Scene, mix
from geom import circle, ellipse, catmull, rrect, rect, poly, move, scale, blob, qbez
from pal2 import M, tone
import props2 as P
from layers import LAYERS as _L1, wrapped, periodic, _periodic_at, sub, hash_id
from platforms import PLATFORMS, WORLD_W, WORLD_H, GROUND_Y, DENSITY

D = DENSITY
GW, GH = int(WORLD_W * D), int(WORLD_H * D)
GY = GROUND_Y * D

LAYERS = {k: dict(v, haze=0.0) for k, v in _L1.items()}

# 위(더스티 블루) → 아래(피치)
SKY_STOPS = [(0, '#7FA4C6'), (320, '#A5C0D6'), (580, '#D8D6D2'), (780, '#F0D8C2'), (1100, '#F4D6BE'), (1500, '#F5DEC9')]


# ---------------------------------------------------------------------------
# 능선 실루엣

def forest_profile(W, xs, base, terms, rng, spacing=None, rmin=10, rmax=24, conifer=0.3, tall=1.0):
    y = base + periodic(W, xs, terms, rng)
    if spacing:
        bump = np.zeros_like(xs)
        c = rng.uniform(0, spacing)
        while c < W:
            d = ((xs - c + W / 2) % W) - W / 2
            if rng.random() < conifer:
                H = rng.uniform(rmax * 1.4, rmax * 2.4) * tall
                b = np.maximum(0, H - np.abs(d) * H / (H * 0.38))
            else:
                r = rng.uniform(rmin, rmax)
                b = np.sqrt(np.maximum(0, r * r - d * d)) * 1.15 * tall
            bump = np.maximum(bump, b)
            c += spacing * rng.uniform(0.55, 1.1)
        y = y - bump
    return y


def ridge(s, W, Hh, xs, ys, top, bot, mist=None, line=None, lw=1.2, rim=None):
    body = np.concatenate([np.stack([xs, ys], -1), [[xs[-1], Hh + 30], [xs[0], Hh + 30]]])
    ymin, ymax = float(ys.min()), float(ys.max())
    if line:
        s.outline(body, line, lw)
    s.fill(body, top, grad=[(ymin, top), (ymax + 60, mix(top, bot, 0.5)), (Hh, bot)])
    if rim:
        s.clip(body)
        s.stroke(np.stack([xs, ys + 2.5], -1), rim, 2.4, alpha=0.55)
        s.unclip()
    if mist:
        col, a = mist
        s.fill(rect(xs[0], ymin, xs[-1], Hh + 30), col, agrad=[(ymin + (ymax - ymin) * 0.4, 0.0), (ymax + 40, a * 0.6), (ymax + 140, a)])


# ---------------------------------------------------------------------------
# 구름

def build_clouds():
    L = LAYERS['clouds']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(1901)
    # 햇빛 글로우 (반복 레이어라 두 군데)
    for gx in (W * 0.22, W * 0.72):
        wrapped(W, gx, 420, lambda xx, r: P.sun_glow(s, xx, 330, 420, '#FFF2DE', 0.55), rng)
    # 수평선 근처 엷은 띠 구름
    for _ in range(12):
        x, y, w = rng.uniform(0, W), rng.uniform(560, 740), rng.uniform(220, 480)
        wrapped(W, x, w, lambda xx, r, y=y, w=w: _streak(s, xx, y, w, r), rng)
    # 볼륨 구름: 먼(작고 옅은) → 가까운(큰)
    spec = []
    x = 60.0
    while x < W:
        big = rng.random() < 0.5
        w = rng.uniform(460, 760) if big else rng.uniform(200, 340)
        y = rng.uniform(130, 330) if big else rng.uniform(380, 560)
        spec.append((x, y, w, big))
        x += w * rng.uniform(0.7, 1.2) + rng.uniform(80, 260)
    for (x, y, w, big) in sorted(spec, key=lambda c: c[2]):
        h = w * rng.uniform(0.3, 0.38)
        far = 0.0 if big else 0.35
        wrapped(W, x, w * 0.6, lambda xx, r, y=y, w=w, h=h, far=far: P.soft_cloud(s, xx, y, w, h, r, far=far), rng)
    return s


def _streak(s, x, y, w, rng):
    for i in range(3):
        s.fill(ellipse(x + rng.uniform(-w * 0.2, w * 0.2), y + i * 5, w * rng.uniform(0.3, 0.5), rng.uniform(3, 6)), '#F3E6DA', alpha=0.35)


# ---------------------------------------------------------------------------
# 원경: 겹친 능선 (멀수록 옅게)

def build_far():
    L = LAYERS['far']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(1902)
    xs = np.arange(-40, W + 41, 4.0)
    haze = '#E6DCD0'
    bands = [
        # base, terms, spacing, rmin, rmax, conifer, top, bot, mist alpha, rim
        (250, [(3, 70), (7, 38), (13, 14), (29, 5)], None, 0, 0, 0, '#A9B9CC', '#D2CFD0', 0.45, '#EADFD2'),
        (380, [(4, 52), (9, 26), (19, 9)], 26, 6, 12, 0.5, '#97ABBA', '#C9CAC4', 0.45, '#E2D8C8'),
        (500, [(5, 40), (11, 20), (23, 6)], 22, 8, 16, 0.35, '#8AA19E', '#C2C4B6', 0.4, '#D9D6BE'),
        (640, [(6, 26), (14, 12)], 18, 9, 18, 0.3, '#7F9886', '#B3B8A0', 0.4, '#D2D2B0'),
    ]
    for (base, terms, sp, rmin, rmax, con, top, bot, ma, rim) in bands:
        ys = forest_profile(W, xs, base, terms, sub(rng), sp, rmin, rmax, con)
        ridge(s, W, Hh, xs, ys, top, bot, mist=(haze, ma), rim=rim)
    return s


# ---------------------------------------------------------------------------
# 중경: 숲 실루엣 + 먼 마을 지붕 + 안개

def build_mid():
    L = LAYERS['mid']
    W, Hh = L['w'], L['h']
    s = Scene(W, Hh)
    rng = np.random.default_rng(1903)
    xs = np.arange(-40, W + 41, 3.0)
    haze = '#E6DCCE'
    # 띠 1 (먼 숲)
    ys1 = forest_profile(W, xs, 250, [(4, 34), (9, 16)], sub(rng), 26, 14, 30, 0.35)
    ridge(s, W, Hh, xs, ys1, '#7E9F8C', '#AAB89E', mist=(haze, 0.3), rim='#DCDDB6')
    terms2 = [(5, 22), (12, 10)]
    # 띠 2 (가까운 숲, 질감)
    ys2 = forest_profile(W, xs, 360, terms2, np.random.default_rng(19032), 30, 18, 36, 0.25)
    ridge(s, W, Hh, xs, ys2, '#668A62', '#8EA47E', rim='#CFD69E')
    s.clip(np.concatenate([np.stack([xs, ys2], -1), [[xs[-1], Hh], [xs[0], Hh]]]))
    for _ in range(int(W / 5)):
        x = rng.uniform(0, W)
        y = float(np.interp(x, xs, ys2)) + rng.uniform(4, 60)
        s.fill(ellipse(x, y, rng.uniform(3, 7), rng.uniform(2, 4), 8), ['#86A07C', '#5F7A5A', '#A4B68A'][int(rng.integers(3))], alpha=0.7)
    s.unclip()
    s.fill(rect(-40, float(ys2.min()), W + 40, Hh + 30), haze, agrad=[(float(ys2.max()) - 20, 0.0), (float(ys2.max()) + 90, 0.24), (Hh, 0.3)])
    # 띠 3 (초원 언덕, 바닥까지 불투명)
    ys3 = 520 + periodic(W, xs, [(6, 18), (13, 7)], np.random.default_rng(19033))
    ridge(s, W, Hh, xs, ys3, '#90A46C', '#7D9060', line='#66784F', lw=1.0, rim='#C8D296')
    # 언덕 위 작은 나무와 덤불
    x = 0.0
    while x < W:
        size = rng.uniform(40, 70)
        kind = 'leaf' if rng.random() < 0.75 else 'rose'
        def dt(xx, r, size=size, kind=kind):
            gy = 520 + _periodic_at(W, xx % W, [(6, 18), (13, 7)], np.random.default_rng(19033)) + 8
            P.tree(s, xx, gy, size, r, kind, lw=1.1, haze=0.32)
        wrapped(W, x, size, dt, rng)
        x += rng.uniform(140, 320)
    return s


def _far_house(s, x, gy, w, rng):
    wall = mix(M['plaster']['shade'], '#B8BDB4', 0.4)
    roof = mix(M['terracotta']['base'], '#9AA59A', 0.45)
    h = w * 0.6
    s.fill(rect(x - w / 2, gy - h, x + w / 2, gy + 20), wall)
    s.fill(rect(x + w * 0.2, gy - h, x + w / 2, gy + 20), mix(wall, '#7F9277', 0.25))
    rp = catmull([(x - w * 0.62, gy - h + 4), (x - w * 0.3, gy - h - w * 0.32), (x, gy - h - w * 0.4), (x + w * 0.3, gy - h - w * 0.32), (x + w * 0.62, gy - h + 4)], False, 8)
    s.fill(np.concatenate([rp, [[x, gy - h + 8]]]), roof)
    for wx in (x - w * 0.2, x + w * 0.15):
        s.fill(rect(wx - 3, gy - h * 0.6, wx + 3, gy - h * 0.6 + 7), '#F3DDB4')


# ---------------------------------------------------------------------------
# 발판

def stone_ledge(s, x0, x1, Y, rng, deep=None, sky=False):
    """이끼 낀 돌 턱: 불규칙한 돌 블록 몸통 + 이끼/잔디 덮개(윗면 Y)."""
    w = x1 - x0
    Dd = deep or float(np.clip(40 + w * 0.03, 44, 54))
    st = M['stone']
    if sky:
        pts = [(x0 - 2, Y + 4), (x0 + 6, Y + Dd * 0.45), (x0 + w * 0.3, Y + Dd * 0.9), (x0 + w * 0.5, Y + Dd * 1.3),
               (x0 + w * 0.7, Y + Dd * 0.85), (x1 - 6, Y + Dd * 0.4), (x1 + 2, Y + 4)]
        body = catmull(pts, False, 10)
    else:
        bx = np.linspace(x1 - 10, x0 + 10, max(5, int(w / 18)))
        by = Y + Dd + rng.uniform(-6, 3, len(bx))
        pts = [(x0 - 2, Y + 4), (x0 - 1, Y + Dd * 0.6)] + list(zip(bx[::-1], by[::-1])) + [(x1 + 1, Y + Dd * 0.6), (x1 + 2, Y + 4)]
        body = catmull(pts, False, 4)
    s.shape(body, st['shade'], st['line'], P.LW)
    s.clip(body)
    s.fill(move(body, -4, -Dd * 0.16), st['base'])
    # 돌 블록
    yy = Y + 10
    row = 0
    while yy < Y + Dd * 1.3:
        rh = rng.uniform(12, 17)
        x = x0 - 10 + (row % 2) * rng.uniform(8, 16)
        while x < x1 + 10:
            bw = rng.uniform(22, 40)
            blk = rrect(x + 1.2, yy + 1.2, x + bw - 1.2, yy + rh - 1.2, 4)
            s.outline(blk, st['deep'], 0.8, alpha=0.8)
            s.fill(rrect(x + 3, yy + 2.5, x + bw * 0.6, yy + 4.5, 1), st['hi'], alpha=0.55)
            if rng.random() < 0.25:
                s.fill(rrect(x + 2, yy + 2, x + bw - 2, yy + rh - 2, 4), st['deep'], alpha=0.18)
            x += bw
        yy += rh
        row += 1
    # 바닥 그늘
    s.fill(move(body, 0, Dd * 0.75), st['deep'], alpha=0.35)
    s.unclip()
    if sky:
        # 작은 수정 (더스티 블루)
        for (cx, h_) in ((x0 + w * 0.44, 20), (x0 + w * 0.56, 14)):
            cy = Y + Dd * 0.8
            s.shape(poly([(cx - 5, cy), (cx, cy + h_), (cx + 5, cy)]), M['dustyblue']['hi'], M['dustyblue']['line'], 1.0)
    moss_cap(s, x0, x1, Y, rng)
    for _ in range(int(rng.integers(1, 3))):
        vx = rng.uniform(x0 + 20, x1 - 20)
        P.vine(s, vx, Y + 12, rng.uniform(26, 56), rng)
    P.blade_row(s, x0 + 2, x1 - 2, Y + 1, rng, hmin=3, hmax=8, density=0.35)


def moss_cap(s, x0, x1, Y, rng, thick=11):
    m = M['moss']
    g = M['grass']
    xs = np.arange(x0, x1 + 3, 3.0)
    xs[-1] = x1
    bot = Y + thick + 3 * np.sin(xs / 9.0 + rng.uniform(0, 6)) + rng.uniform(-1.5, 3.5, len(xs))
    # 늘어진 이끼 가닥
    for i in range(0, len(xs), 4):
        if rng.random() < 0.35:
            bot[i] += rng.uniform(5, 13)
    e = 4.0
    right = catmull([(x1, Y), (x1 + e * 0.8, Y + 2), (x1 + e, Y + thick * 0.7)], False, 4)
    left = catmull([(x0 - e, Y + thick * 0.7), (x0 - e * 0.8, Y + 2), (x0, Y)], False, 4)
    p = np.concatenate([[[x0, Y], [x1, Y]], right[1:], np.stack([xs, bot], -1)[::-1], left[:-1]])
    s.shape(p, m['shade'], m['line'], P.LW)
    s.clip(p)
    s.fill(move(p, 0, -4), g['base'])
    s.fill(rect(x0 - 8, Y - 2, x1 + 8, Y + 3), g['hi'])
    P.dabs(s, x0, Y + 3, x1, Y + thick + 4, int((x1 - x0) / 6), rng, [g['hi'], m['base'], g['shade']], 1.2, 2.6)
    s.unclip()


def plank_boards(s, x0, x1, Y, rng, th=14, m=None):
    m = m or M['wood']
    xs = [x0]
    while xs[-1] < x1 - 1e-6:
        nx = min(x1, xs[-1] + rng.uniform(26, 42))
        if x1 - nx < 14:
            nx = x1
        xs.append(nx)
    allp = [rect(a, Y, b, Y + th) for a, b in zip(xs[:-1], xs[1:])]
    s.shape(allp, m['shade'], m['line'], P.LW)
    for a, b in zip(xs[:-1], xs[1:]):
        tone_ = mix(m['base'], m['shade'], rng.uniform(0, 0.35))
        s.fill(rect(a + 0.8, Y, b - 0.8, Y + th - 3.5), tone_)
        s.fill(rect(a + 0.8, Y, b - 0.8, Y + 2.6), m['hi'])
        s.stroke(poly([(b, Y + 1), (b, Y + th)]), m['line'], 1.2)
        for _ in range(2):
            yy = Y + rng.uniform(5, th - 4)
            xa = a + rng.uniform(3, (b - a) * 0.4)
            s.stroke(poly([(xa, yy), (xa + rng.uniform(6, (b - a) * 0.6), yy + rng.uniform(-0.6, 0.6))]), m['deep'], 0.8, alpha=0.6)
        if rng.random() < 0.25:
            P.dabs(s, a + 2, Y + 1, b - 2, Y + 5, 3, rng, [M['moss']['base']], 1.5, 3)


def lashing(s, x, y0, y1):
    m = M['wood']
    p = rrect(x - 4, y0, x + 4, y1, 2)
    s.shape(p, M['cream']['shade'], M['cream']['line'], 1.1)
    s.clip(p)
    yy = y0 + 2
    while yy < y1:
        s.stroke(poly([(x - 5, yy + 3), (x + 5, yy - 1)]), M['cream']['deep'], 1.0)
        yy += 3.5
    s.unclip()


def plat_plank(s, x0, x1, Y, rng):
    wd = M['darkwood']
    log = rrect(x0 + 10, Y + 11, x1 - 10, Y + 24, 6)
    P.toon(s, [log], wd, P.LW, shift=(0, -0.25), shrink=1.0)
    for ex in (x0 + 14, x1 - 14):
        s.shape(ellipse(ex, Y + 17.5, 5, 6.5), M['wood']['hi'], wd['line'], 1.1)
        s.outline(ellipse(ex, Y + 17.5, 2.2, 3), M['wood']['shade'], 0.5)
    plank_boards(s, x0, x1, Y, rng)
    n = max(2, int((x1 - x0) / 120) + 1)
    for x in np.linspace(x0 + 16, x1 - 16, n):
        lashing(s, x, Y + 1, Y + 26)
    P.hanging_moss(s, x0 + 20, x1 - 20, Y + 22, rng, maxlen=14)
    for _ in range(int(rng.integers(1, 3))):
        P.vine(s, rng.uniform(x0 + 30, x1 - 30), Y + 20, rng.uniform(30, 60), rng)


def plat_bridge(s, x0, x1, Y, rng):
    wd = M['darkwood']
    rp = M['cream']
    sag, ph = 16, 44
    posts = (x0 + 7, x1 - 7)
    rail_y = Y - ph + 8
    xs = np.linspace(posts[0], posts[1], 60)
    t = (xs - posts[0]) / (posts[1] - posts[0])
    rail = np.stack([xs, rail_y + sag * 4 * t * (1 - t)], -1)
    s.stroke(move(rail, 0, -4), mix(rp['shade'], '#B8C0C4', 0.4), 2.2)
    for px_ in posts:
        P.toon(s, [rrect(px_ - 5, Y - ph, px_ + 5, Y + 32, 2)], wd, P.LW, shift=(-0.25, 0), shrink=1.0)
        s.shape(circle(px_, Y - ph - 1, 6.5), wd['base'], wd['line'], 1.2)
    P.rope(s, poly([(posts[0], Y + 10), (posts[1], Y + 10)]), rp, 2.6)
    x = x0
    while x < x1 - 1e-6:
        bw = min(x1 - x, rng.uniform(17, 21))
        if x1 - (x + bw) < 8:
            bw = x1 - x
        s.shape(rect(x + 0.6, Y, x + bw - 0.6, Y + 10), M['wood']['shade'], M['wood']['line'], 1.2)
        s.fill(rect(x + 1.4, Y, x + bw - 1.4, Y + 6.5), mix(M['wood']['base'], M['wood']['hi'], rng.uniform(0, 0.4)))
        s.fill(rect(x + 1.4, Y, x + bw - 1.4, Y + 2), M['wood']['hi'])
        x += bw
    for xx in np.arange(posts[0] + 26, posts[1] - 10, 30):
        tt = (xx - posts[0]) / (posts[1] - posts[0])
        ry = rail_y + sag * 4 * tt * (1 - tt)
        s.stroke(poly([(xx, ry), (xx, Y + 1)]), rp['line'], 2.4)
        s.stroke(poly([(xx, ry), (xx, Y + 1)]), rp['base'], 1.0)
    P.rope(s, rail, rp, 2.8)
    # 천 깃발 (세이지, 테라코타, 크림)
    for i, xx in enumerate(np.linspace(posts[0] + 30, posts[1] - 30, max(3, int((x1 - x0) / 60)))):
        tt = (xx - posts[0]) / (posts[1] - posts[0])
        ry = rail_y + sag * 4 * tt * (1 - tt) + 2
        cm = M[['sage', 'terracotta', 'cream', 'dustyblue'][i % 4]]
        s.shape(poly([(xx - 6, ry), (xx + 6, ry), (xx, ry + 12)]), cm['base'], cm['line'], 0.9)


def plat_deck(s, x0, x1, Y, rng):
    wd = M['darkwood']
    w = x1 - x0
    n = 2 if w < 230 else 3
    px_ = np.linspace(x0 + 14, x1 - 14, n)
    for i, x in enumerate(px_):
        for sgn in (-1, 1):
            if (i == 0 and sgn < 0) or (i == len(px_) - 1 and sgn > 0):
                continue
            s.stroke(poly([(x, Y + 48), (x + sgn * 32, Y + 14)]), wd['line'], 6.5)
            s.stroke(poly([(x, Y + 48), (x + sgn * 32, Y + 14)]), wd['shade'], 3.6)
    for x in px_:
        P.toon(s, [rect(x - 6, Y + 6, x + 6, GY + 2)], wd, P.LW, shift=(-0.3, 0), shrink=1.0)
        s.fill(np.concatenate([P.rough_line(x - 7, x + 7, GY - 26, rng, 3), [[x + 7, GY + 2], [x - 7, GY + 2]]]), M['moss']['shade'], alpha=0.85)
    P.toon(s, [rrect(x0 + 4, Y + 10, x1 - 4, Y + 22, 3)], wd, P.LW, shift=(0, -0.3), shrink=1.0)
    plank_boards(s, x0, x1, Y, rng)
    lx = x0 + w * rng.uniform(0.35, 0.65)
    s.stroke(poly([(lx, Y + 22), (lx, Y + 36)]), M['metal']['line'], 1.4)
    s.fill(circle(lx, Y + 46, 18), '#FFE9C4', alpha=0.22)
    s.shape(rrect(lx - 6, Y + 36, lx + 6, Y + 54, 3), M['glow']['base'], M['metal']['line'], 1.4)
    s.fill(rect(lx - 3.5, Y + 39, lx - 1, Y + 51), M['glow']['hi'])


def plat_sky(s, x0, x1, Y, rng):
    stone_ledge(s, x0, x1, Y, rng, deep=56, sky=True)
    gx = x1 - 16
    s.fill(circle(gx, Y - 12, 20, 32), '#FFE9C4', alpha=0.25)
    P.small_shroom(s, gx, Y + 1, 8, rng, 'cream')
    s.fill(circle(gx, Y - 10, 3, 8), '#FFF6E2', alpha=0.8)


PLAT_FN = dict(grass=lambda s, a, b, y, r: stone_ledge(s, a, b, y, r), plank=plat_plank, bridge=plat_bridge, deck=plat_deck, sky=plat_sky)


def draw_platforms(s, rng, only=None):
    for p in sorted(PLATFORMS, key=lambda q: q['y']):
        if only and p['id'] not in only:
            continue
        r = np.random.default_rng(abs(hash_id('v2' + p['id'])))
        # 외곽선(LW) 윗끝이 서는 선과 같도록 채움 윗면을 LW 만큼 내린다
        PLAT_FN[p['kind']](s, p['x1'] * D, p['x2'] * D, p['y'] * D + P.LW, r)


# ---------------------------------------------------------------------------
# 지면

def ground_terrain(s, rng):
    W = GW
    sm = M['soil']
    top = GY + 8
    body = rect(-20, top, W + 20, GH + 20)
    s.fill(body, sm['base'], grad=[(top, sm['base']), (GY + 70, sm['shade']), (GH, sm['deep'])])
    s.clip(body)
    xs = np.arange(-20, W + 21, 8.0)
    # 잔디 아래 그늘
    s.fill(np.concatenate([np.stack([xs, GY + 22 + 3 * np.sin(xs / 31)], -1), np.stack([xs, GY + 40 + 3 * np.sin(xs / 19)], -1)[::-1]]), sm['deep'], alpha=0.45)
    # 지층 결
    for i, yy in enumerate((GY + 66, GY + 104)):
        wv = yy + 4 * np.sin(xs / 150 + i * 1.7) + 2 * np.sin(xs / 41 + i)
        s.stroke(np.stack([xs, wv], -1), sm['deep'], 1.4, alpha=0.5)
        s.stroke(np.stack([xs, wv + 2], -1), sm['hi'], 1.0, alpha=0.25)
    P.dabs(s, 0, top + 8, W, GH, int(W / 6), rng, [sm['deep'], sm['hi'], sm['shade']], 1.2, 3.0, alpha=0.6)
    # 묻힌 돌
    x = rng.uniform(20, 80)
    while x < W:
        y = rng.uniform(GY + 52, GH - 8)
        r = rng.uniform(7, 15)
        p = blob(x, y, r, r * 0.7, rng, k=7, jit=0.15)
        P.toon(s, [p], M['stone'], 1.2, shift=(-0.07, -0.12), shrink=0.84, hi=[ellipse(x - r * 0.35, y - r * 0.3, r * 0.25, r * 0.12)])
        x += rng.uniform(80, 190)
    # 잔뿌리
    for _ in range(int(W / 200)):
        rx = rng.uniform(0, W)
        ln = catmull([(rx, GY + 22), (rx + rng.uniform(-6, 6), GY + 34), (rx + rng.uniform(-14, 14), GY + rng.uniform(46, 60))], False, 8)
        s.stroke(ln, sm['deep'], 1.6, alpha=0.8)
    s.unclip()
    # 잔디 덮개 (윗선 GY, 외곽선 윗끝이 GY 가 되도록 +LW)
    g = M['grass']
    Y = GY + P.LW
    xs = np.arange(-10, W + 13, 3.0)
    bot = Y + 20 + 3 * np.sin(xs / 11.0) + rng.uniform(-2, 4, len(xs))
    for i in range(0, len(xs), 3):
        if rng.random() < 0.3:
            bot[i] += rng.uniform(5, 12)
    p = np.concatenate([[[-10, Y], [W + 10, Y]], np.stack([xs, bot], -1)[::-1]])
    s.shape(p, g['shade'], g['line'], P.LW)
    s.clip(p)
    s.fill(move(p, 0, -5), g['base'])
    s.fill(rect(-10, Y - 2, W + 10, Y + 3), g['hi'])
    P.dabs(s, 0, Y + 3, W, Y + 22, int(W / 4), rng, [g['hi'], g['shade'], M['moss']['base']], 1.2, 2.8)
    s.unclip()


def giant_tree(s, x, cy, rx, rng):
    mt = M['trunk']
    tw = rx * 0.26
    P.trunk(s, x, GY + 4, cy + rx * 0.2, tw, rng, mt, lean=rng.uniform(-10, 10), branches=2)
    for sgn in (-1, 1):
        root = catmull([(x + sgn * tw * 0.3, GY - 56), (x + sgn * tw * 1.1, GY - 12), (x + sgn * tw * 1.9, GY + 4), (x + sgn * tw * 0.4, GY + 6)], True, 8)
        P.toon(s, [root], mt, P.LW, shift=(-0.1, -0.1), shrink=0.9)
    back = {k: mix(v, '#2E3A28', 0.15) for k, v in M['leaf2'].items()}
    P.leafy_canopy(s, x + rx * 0.15, cy - rx * 0.12, rx * 1.05, rx * 0.5, rng, back, k=10, texture=0.5)
    cl = P.leafy_canopy(s, x - rx * 0.05, cy + rx * 0.05, rx * 1.2, rx * 0.6, rng, M['leaf2'], k=16)
    for (cx_, cy_, r) in cl:
        if cy_ > cy + rx * 0.1 and rng.random() < 0.35:
            P.hanging_moss(s, cx_ - r * 0.3, cx_ + r * 0.3, cy_ + r * 0.75, rng, M['moss'], maxlen=18)
    for _ in range(5):
        vx = x + rng.uniform(-rx * 0.8, rx * 0.8)
        vy = cy + rx * 0.62 * 0.55 * np.sqrt(max(0.0, 1 - ((vx - x) / (rx * 0.95)) ** 2)) + 10
        P.vine(s, vx, vy, rng.uniform(50, 110), rng)


def build_ground():
    s = Scene(GW, GH)
    rng = np.random.default_rng(1904)
    w = lambda v: v * D

    # 서쪽 들판: 넓은 활엽수, 올리브 나무, 장미빛 꽃나무 조금
    for (x, size, kind) in ((40, 220, 'leaf'), (640, 240, 'leaf'), (1080, 150, 'rose'), (1430, 200, 'leaf'), (300, 130, 'olive'), (860, 120, 'olive'), (1240, 110, 'leaf')):
        P.tree(s, w(x), GY + 4, size, sub(rng), kind)
    # 마을: 카페, 베이커리, 상점, 작은 집
    P.tree(s, w(2330), GY + 4, 140, sub(rng), 'rose')
    P.tree(s, w(2960), GY + 4, 160, sub(rng), 'leaf')
    bl = [(1960, 290, 205, 'terracotta', 'cafe', ('cream', 'terracotta')),
          (2185, 250, 185, 'sage', 'bakery', ('cream', 'sage')),
          (2760, 265, 195, 'dustyblue', 'shop', ('cream', 'dustyblue')),
          (3125, 230, 175, 'olive', 'cafe', ('cream', 'olive'))]
    for (x, ww, hh, roof, kind, awn) in bl:
        P.building(s, w(x), GY + 2, ww, hh, sub(rng), roof=roof, kind=kind, awn=awn)
    # 동쪽 숲: 거대한 나무 + 침엽수
    for (x, cy, rx) in ((3580, 300, 250), (4250, 360, 230), (4700, 300, 210), (3150, 380, 170)):
        giant_tree(s, w(x), w(cy), rx, sub(rng))
    for (x, size, kind) in ((3290, 170, 'leaf2'), (3760, 140, 'rose'), (4150, 180, 'leaf2'), (4520, 150, 'olive')):
        P.tree(s, w(x), GY + 4, size, sub(rng), kind)
    for x in (3420, 3880, 4380):
        P.conifer(s, w(x), GY + 4, 190, sub(rng), M['leaf2'])

    ground_terrain(s, rng)

    rr = sub(rng)
    # 덤불
    for x in (150, 470, 880, 1230, 1460, 3400, 3620, 3980, 4300, 4650):
        P.bush(s, w(x), GY + 3, rr.uniform(70, 120), rr.uniform(32, 44), rr, M['leaf'] if x < 2400 else M['leaf2'],
               flowers=['cream', 'dustyblue', 'rose'] if rr.random() < 0.5 else None)
    # 마을 소품
    lamps = {}
    for x in (1860, 2250, 2620, 3040):
        lamps[x] = P.lamp(s, w(x), GY + 2)
    # 스트링 라이트: 가로등 ↔ 가로등, 가로등 ↔ 처마
    P.string_lights(s, *lamps[2250], *lamps[2620], 34, rr)
    P.string_lights(s, *lamps[1860], w(1960) - 145, GY - 205 - 2, 18, rr)
    P.string_lights(s, *lamps[3040], w(3125) - 115, GY - 175 - 2, 14, rr)
    P.bench(s, w(2340), GY + 2)
    P.bench(s, w(2560), GY + 2)
    for (x, r, pl) in ((1890, 9, 'leaf'), (2045, 8, 'olive'), (2100, 10, 'leaf'), (2470, 12, 'olive'), (2690, 9, 'leaf'), (2850, 8, 'olive'), (3060, 9, 'leaf')):
        P.pot(s, w(x), GY + 2, r, rr, pl)
    P.crate(s, w(2700), GY + 2, 28, 'terracotta', rr)
    P.crate(s, w(2722), GY + 2, 24, 'olive', rr)
    P.barrel(s, w(2125), GY + 2)
    P.fence(s, w(1560), w(1620), GY + 2)
    P.fence(s, w(3190), w(3240), GY + 2)
    # 바위, 작은 버섯, 고사리
    for (x, r) in ((330, 15), (1010, 20), (1380, 12), (3530, 22), (3900, 14), (4420, 19), (4720, 12)):
        P.mossy_rock(s, w(x), GY + 3, r, rr)
    for x in (260, 700, 1180, 3340, 3700, 3720, 4080, 4250, 4600):
        P.small_shroom(s, w(x), GY + 3, rr.uniform(6, 10), rr, ['terracotta', 'cream', 'warmgray'][int(rr.integers(3))])
    for x in (3300, 3480, 3640, 3830, 4000, 4190, 4350, 4560, 4760):
        P.fern(s, w(x), GY + 4, rr.uniform(30, 44), rr)
    # 풀잎 끝선과 들꽃
    P.blade_row(s, 0, GW, GY + 1, rr, hmin=3, hmax=9, density=0.5)
    x = 6.0
    while x < GW - 6:
        k = rr.random()
        if k < 0.5:
            P.tuft(s, x, GY + 3, rr.uniform(10, 17), rr)
        elif k < 0.75:
            col = ['cream', 'dustyblue', 'rose', 'cream'][int(rr.integers(4))]
            for j in range(int(rr.integers(1, 4))):
                P.daisy(s, x + j * 8, GY - rr.uniform(8, 15), rr.uniform(2.6, 3.6), col, stem=True)
        x += rr.uniform(22, 50)

    draw_platforms(s, rng)
    return s
