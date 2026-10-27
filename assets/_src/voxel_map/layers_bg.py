"""배경 레이어: sky(그라데이션), clouds, far, mid.

밀도 1.5px = 월드 1. 레이어마다 모델 단위 크기(scale px/단위)가 다르다: 멀수록 블록이 작게 보인다.
반복 레이어는 period(px) 주기로 상자를 좌우 복제해 렌더하므로 이음매 없이 이어진다.
"""
import numpy as np
from PIL import Image
from vox import Cfg, Box, rot_y, rot_z, hex2lin, lin2srgb
import props as P
from props import B, BR, placed, octo


# ====================================================================== sky
SKY_STOPS = [(0.00, '#55AAEA'), (0.22, '#74BDEE'), (0.42, '#A6D6F2'), (0.55, '#D2E9F0'), (0.64, '#FBEBD6'),
             (0.74, '#FFDDB6'), (1.00, '#FFCFA0')]


def sky_image(W=16, H=810):
    t = (np.arange(H) + 0.5) / H
    pos = np.array([s[0] for s in SKY_STOPS]); cols = np.array([hex2lin(s[1]) for s in SKY_STOPS])
    lin = np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], -1)
    srgb = lin2srgb(lin)
    # 순서 디더(결정적)로 8비트 띠 방지
    bay = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
    img = np.repeat(srgb[:, None, :], W, 1) * 255
    img += bay[np.arange(H)[:, None] % 4, np.arange(W)[None, :] % 4][..., None] * 0.9
    img = np.clip(np.round(img), 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([img, np.full((H, W), 255, np.uint8)]), 'RGBA')


# ====================================================================== clouds
def cloud(seed, w):
    """큐브 적운: 납작한 바닥 + 2단 퍼프 (가운데가 높은 둥근 실루엣)."""
    rng = np.random.default_rng(seed)
    bx = []
    h0 = max(4, w * 0.11)
    d = w * 0.34
    bx += octo(0, 0, 0, w, h0, d, '#EDF0F8', cut=0.25, noise=0.02)
    n1 = max(3, int(w / 20) + 1)
    for k in range(n1):
        fx = ((k + 0.5) / n1 * 2 - 1) * 0.36 * w + rng.uniform(-0.04, 0.04) * w
        pw = w * rng.uniform(0.26, 0.38) * (1 - 0.35 * abs(fx) / (0.36 * w))
        ph = w * rng.uniform(0.13, 0.2) * (1 - 0.4 * abs(fx) / (0.36 * w))
        bx.append(B(fx, h0 * 0.6 + ph / 2, rng.uniform(-d * 0.12, d * 0.12), pw, ph, min(d * 1.05, pw * 0.9),
                    '#FFFFFF', noise=0.02))
    n2 = max(1, int(w / 34))
    for k in range(n2 + 1):
        fx = rng.uniform(-0.16, 0.16) * w
        pw = w * rng.uniform(0.2, 0.3); ph = w * rng.uniform(0.11, 0.16)
        bx.append(B(fx, h0 * 0.6 + w * 0.15 + ph / 2, rng.uniform(-d * 0.08, d * 0.08), pw, ph, min(d, pw * 0.9),
                    '#FFFFFF', noise=0.02))
    return bx


def clouds_scene(period_u):
    rng = np.random.default_rng(71)
    bx = []
    # (x 비율, y(모델, 위로 +), 너비)
    items = [(0.03, 50, 62), (0.17, 72, 30), (0.30, 42, 92), (0.45, 76, 40), (0.57, 54, 56), (0.68, 74, 26),
             (0.79, 40, 80), (0.92, 68, 36)]
    for i, (fx, y, w) in enumerate(items):
        bx += placed(cloud(100 + i, w), fx * period_u, (y - 38) * 0.8, -20 - i * 6)
    return bx


# ====================================================================== far
def far_scene(period_u):
    """모델 1단위 = 월드 1. 원점 y = 월드 430."""
    rng = np.random.default_rng(81)
    bx = []
    TAU = 2 * np.pi
    # 먼 산맥: 봉우리마다 위로 좁아지는 층 (주기 안에서 감싸기)
    peaks = [(0.03, 130, 190), (0.12, 90, 130), (0.21, 120, 230), (0.33, 100, 160), (0.45, 80, 120), (0.55, 110, 210),
             (0.70, 95, 150), (0.80, 125, 240), (0.92, 90, 140)]
    PAST = [('#9E9CCB', '#B5ADD8', '#CDBFE2'), ('#A9A2D2', '#C2B2DC', '#D9C6E6'), ('#98A6CF', '#B0B8DE', '#CBCDE8')]
    for i, (fx, W_, H_) in enumerate(peaks):
        cx = fx * period_u
        z = -250 - (i % 3) * 18
        n = int(H_ * 0.85 // 8)
        pal = PAST[i % 3]
        for k in range(n):
            t = k / n
            w = W_ * 1.6 * (1 - t) ** 1.05 + 5
            off = (rng.uniform(-0.08, 0.08) * W_) * t
            col = '#F6F2FA' if t > 0.8 else (pal[2] if t > 0.55 else (pal[1] if t > 0.25 else pal[0]))
            bx.append(B(cx + off, k * 8 + 4, z, w, 8.4, 34, col, noise=0.03))
            if t > 0.5 and t < 0.8 and rng.random() < 0.5:     # 눈 줄무늬
                bx.append(B(cx + off + rng.uniform(-w / 4, w / 4), k * 8 + 4, z + 17.3, w * 0.3, 8.4, 0.6, '#F6F2FA',
                            noise=0.02, bevel=0.1))
    # 가까운 언덕 (초록)
    def h_near(x):
        f = x / period_u * TAU
        return 52 + 22 * np.sin(f * 4 + 2.0) + 14 * np.sin(f * 9 + 0.7)
    x = 0.0
    while x < period_u:
        w = float(rng.integers(10, 18))
        h = h_near(x + w / 2)
        bx.append(B(x + w / 2, h / 2, -150, w + 0.4, h, 40, '#7FBF8E', noise=0.04))
        bx.append(B(x + w / 2, h + 1.2, -150, w + 0.4, 2.4, 40, '#9BD39A', noise=0.04))
        # 작은 나무 점
        if rng.random() < 0.55:
            s = rng.uniform(5, 9)
            bx.append(B(x + rng.uniform(0, w), h + s / 2 + 1, -140, s, s, s,
                        '#E8A6C4' if rng.random() < 0.3 else '#5FA872', noise=0.05))
        x += w
    # 호수 (아래 띠)
    bx.append(B(period_u / 2, -3, -60, period_u * 1.2, 6, 120, '#7CC4EC', noise=0.02, bevel=0))
    for k in range(60):
        gx = rng.uniform(0, period_u); gz = rng.uniform(-110, 0)
        bx.append(B(gx, 0.15, gz, rng.uniform(4, 12), 0.3, 0.8, '#FFFFFF', noise=0, bevel=0, emit=('#FFF4D8', 0.6)))
    # 성 (언덕 위)
    cx = period_u * 0.62
    base = 92.0
    for k, (w, col) in enumerate(((150, '#8E9AB0'), (124, '#97A2B8'), (104, '#8E9AB0'), (92, '#A0AABF'), (86, '#97A2B8'))):
        bx.append(B(cx + (k % 2) * 3, k * 18.4 + 9.2, -122, w, 18.4, 40, col, noise=0.04))
    bx.append(B(cx, base - 1, -122, 92, 2, 40, '#8FCF7A', noise=0.04))
    def tower(x, z, w, h, roof='#E58AB0'):
        out = [B(x, base + h / 2, z, w, h, w, '#EEE6EE', noise=0.04)]
        out.append(B(x, base + h + 1, z, w + 2, 2, w + 2, '#C3C6D6', noise=0.03))
        r = w + 2; y = base + h + 2
        while r > 1.5:
            out.append(B(x, y + 2, z, r, 4, r, roof, noise=0.03))
            y += 4; r -= 2.3
        out.append(B(x + w * 0.2, base + h * 0.7, z + w / 2 + 0.2, 2, 3, 0.4, '#FFE7A0', bevel=0, emit=('#FFC060', 0.4)))
        return out
    bx.append(B(cx, base + 14, -120, 70, 28, 22, '#E4DCE8', noise=0.04))
    for k in range(9):
        bx.append(B(cx - 32 + k * 8, base + 30, -110, 4, 4, 2, '#E4DCE8'))
    bx += tower(cx - 38, -112, 14, 52)
    bx += tower(cx + 38, -112, 14, 48, '#7FA0E0')
    bx += tower(cx - 10, -126, 18, 84)
    bx += tower(cx + 14, -128, 12, 66, '#7FA0E0')
    bx += tower(cx - 56, -116, 10, 34, '#7FA0E0')
    bx += tower(cx + 54, -116, 10, 30)
    return bx


# ====================================================================== mid
def cabin(seed=0, roof='#C0503A', w=30, h=18, d=22):
    bx = [B(0, h / 2, 0, w, h, d, '#E0A868', noise=0.08)]
    for k in range(4):
        bx.append(B(0, 2 + k * 4.4, d / 2 + 0.2, w - 1, 0.6, 0.6, '#B97A4A', bevel=0.1, noise=0))
    for sgn in (-1, 1):
        bx.append(BR(sgn * w * 0.27, h + 5.5, 0, w * 0.62, 2.6, d + 4, roof, rot_z(-sgn * 34), noise=0.05))
    bx.append(B(0, h + 11, 0, 3, 2.6, d + 4.5, '#7E2C24', noise=0.05))
    bx.append(B(0, h / 2 + 4.5, d / 2, w * 0.48 * 0 + 6, 0.1, 0.1, '#E0A868'))
    bx.append(B(w / 2 - 5, 7.5, d / 2 + 0.6, 5, 5, 1, '#FFE7A0', emit=('#FFB848', 0.6), noise=0.05))
    bx.append(B(-w / 2 + 6, 6, d / 2 + 0.6, 5.5, 11, 1, '#8A5232', noise=0.08))
    bx.append(B(w / 2 - 7, h + 9, -4, 4, 8, 4, '#8E88A0', noise=0.08))
    return bx


def mid_scene(period_u):
    """모델 1단위 = 월드 1.5. 원점 y = 월드 430."""
    rng = np.random.default_rng(91)
    TAU = 2 * np.pi
    bx = []

    def hill(x):
        f = x / period_u * TAU
        return 30 + 16 * np.sin(f * 3 + 0.3) + 9 * np.sin(f * 7 + 1.9)
    # 언덕: 계단 기둥 (앞뒤 2줄)
    x = 0.0
    tops = []
    while x < period_u:
        w = float(rng.integers(8, 15))
        h = round(hill(x + w / 2) / 4) * 4
        bx.append(B(x + w / 2, h / 2 - 10, -70, w + 0.3, h + 20, 40, '#6DB85A', noise=0.05))
        bx.append(B(x + w / 2, h - 1.5, -70, w + 0.3, 3, 40, '#88CC63', noise=0.05))
        tops.append((x, w, h))
        x += w
    hz = lambda xx: next((h for (x0, w, h) in tops if x0 <= (xx % period_u) < x0 + w), 30)
    # 집 3채 (언덕 위)
    for i, (fx, cap) in enumerate(((0.15, 'red'), (0.52, 'blue'), (0.80, 'orange'))):
        cx = fx * period_u
        bx += placed(P.mushroom_house(cap, 44, seed=200 + i, chimney=True), cx, hz(cx), -72, [18, -14, 10][i], 0.42)
    for i, (fx, cap) in enumerate(((0.33, 'orange'), (0.67, 'red'), (0.95, 'blue'))):
        cx = fx * period_u
        bx += placed(P.mushroom_house(cap, 40, seed=210 + i, chimney=False), cx, hz(cx), -80, [-12, 16, 8][i], 0.3)
    # 숲 줄: 뒤 (언덕 위) 둥근 나무 + 소나무
    x = 0.0
    while x < period_u:
        cx = x + rng.uniform(0, 6)
        if any(abs(cx - f * period_u) < 26 for f in (0.15, 0.52, 0.80, 0.33, 0.67, 0.95)):
            x += 10; continue
        r = rng.uniform(0.6, 0.9)
        kind = rng.random()
        z = -86 + rng.uniform(-6, 6)
        if kind < 0.45:
            bx += placed(P.oak(int(rng.integers(0, 1 << 30)), h=18, r=20, palette=('leaf3', 'leaf4', 'leaf2', 'leaf5')),
                         cx, hz(cx) - 2, z, 0, r)
        elif kind < 0.72:
            bx += placed(P.pine(int(rng.integers(0, 1 << 30)), h=58, r=14), cx, hz(cx) - 2, z, 0, r)
        else:
            bx += placed(P.cherry(int(rng.integers(0, 1 << 30)), h=20, r=24), cx, hz(cx) - 2, z, 0, r)
        x += rng.uniform(18, 30) * r
    # 앞줄: 낮은 언덕 둔덕 + 덤불/작은 나무 (지면 레이어 뒤 가장자리 아래를 채운다)
    x = 0.0
    while x < period_u:
        w = float(rng.integers(10, 20))
        h = 10 + rng.uniform(0, 6)
        bx.append(B(x + w / 2, h / 2 - 12, -20, w + 0.3, h + 24, 30, '#5FAE52', noise=0.05))
        if rng.random() < 0.45:
            r = rng.uniform(0.45, 0.65)
            if rng.random() < 0.75:
                bx += placed(P.oak(int(rng.integers(0, 1 << 30)), h=16, r=20), x + w / 2, h - 12, -16, 0, r)
            else:
                bx += placed(P.cherry(int(rng.integers(0, 1 << 30)), h=18, r=24), x + w / 2, h - 12, -16, 0, r)
        x += w
    return bx


# ====================================================================== spec
def spec(name, L, D):
    if name == 'sky':
        return dict(image=sky_image(16, int(540 * D)))
    if name == 'clouds':
        period_px = 2700
        sc = 3.0
        H = 330
        cfg = Cfg(ss=3, grid=1.0, sh_step=1.3, sh_n=40, haze='#D6ECFA', haze_amt=0.10, bounce=0.6, sky=1.6, rim=0.6)
        return dict(boxes=clouds_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, 320.0),
                    cfg=cfg, period=period_px, glow=None, tile=300)
    if name == 'far':
        period_px = 3000
        sc = 1.5
        H = int((440 - L['y']) * D) + 0
        ay = (430 - L['y']) * D
        cfg = Cfg(ss=3, grid=1.0, sh_step=1.5, sh_n=60, haze='#C6DAE8', haze_amt=0.22, haze_add=0.34, haze_z=(-20, -240), bounce=1.2,
                  rim=0.5)
        return dict(boxes=far_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, ay), cfg=cfg,
                    period=period_px, glow=(3.0, 0.8, 0, 0), tile=300)
    if name == 'mid':
        period_px = 3000
        sc = 2.25
        H = int((440 - L['y']) * D)
        ay = (430 - L['y']) * D
        cfg = Cfg(ss=3, grid=1.0, sh_step=1.3, sh_n=70, haze='#CFE2EA', haze_amt=0.27, bounce=1.6, rim=0.8)
        return dict(boxes=mid_scene(period_px / sc), scale=sc, W=period_px, H=H, anchor=(0.0, ay), cfg=cfg,
                    period=period_px, glow=(4.0, 1.0, 12.0, 0.3), tile=250)
    raise KeyError(name)
