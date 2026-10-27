"""버섯마을 맵 소품 복셀 모델. 단위 = 모델 단위(지면 레이어에서 1단위 = 월드 2 = 3px).
원점 = 소품 바닥 중앙(지면 y=0). x 오른쪽, y 위, z 카메라 쪽.
모든 무작위는 seed 고정 default_rng.
"""
import numpy as np
from vox import Box, rot_y, rot_z, rot_x

# ---------------------------------------------------------------- 색 (스타일 가이드 팔레트 기반 + 중간 톤)
C = dict(
    cream='#FFF3DE', cream2='#F2DDB8', cream3='#E4C8A0',
    red='#E8483E', red_hi='#FF6E5C', orange='#F5902E', orange_hi='#FFB050', blue='#4D7CFE', blue_hi='#79A6FF',
    white='#FFFFFF', wood1='#E0A868', wood2='#B97A4A', wood3='#8A5232', wood4='#5E3620',
    stone1='#C8C4D0', stone2='#A8A2B8', stone3='#8E88A0', stone4='#6E6882',
    leaf1='#B6E86A', leaf2='#7FD04A', leaf3='#5BB33C', leaf4='#3E8A2E', leaf5='#2F6E2A',
    pink1='#FFD6E4', pink2='#FFB3CD', pink3='#F58AB4', pink4='#E06A9C',
    glass='#FFE7A0', glow='#FFC864', water='#5FB7F0', yellow='#F7C948', ink='#2E2A3E',
)


def B(cx, cy, cz, w, h, d, col, **kw):
    """중심 (cx, cy, cz), 크기 (w, h, d)."""
    return Box((cx, cy, cz), (w / 2, h / 2, d / 2), None, C.get(col, col), **kw)


def BR(cx, cy, cz, w, h, d, col, R, **kw):
    return Box((cx, cy, cz), (w / 2, h / 2, d / 2), R, C.get(col, col), **kw)


def octo(cx, y0, cz, w, h, d, col, cut=0.18, **kw):
    """모서리를 깎은 팔각 기둥 (상자 2개 교차)."""
    cw, cd = w * cut, d * cut
    return [B(cx, y0 + h / 2, cz, w, h, d - 2 * cd, col, **kw),
            B(cx, y0 + h / 2, cz, w - 2 * cw, h, d, col, **kw)]


def _scale_keep(boxes, s):
    out = []
    for b in boxes:
        nb = b.moved((0, 0, 0))
        nb.c = b.c * s; nb.h = b.h * s
        out.append(nb)
    return out


def placed(boxes, x=0.0, y=0.0, z=0.0, yaw=0.0, s=1.0):
    if s != 1.0:
        boxes = _scale_keep(boxes, s)
    R = rot_y(yaw)
    return [b.moved((x, y, z), R) for b in boxes]


# ---------------------------------------------------------------- 버섯 집
def mushroom_house(cap='red', H=56, seed=1, chimney=True, windows=('L', 'R', 'S'), slabs=None, top_cut=0.24,
                   info=None, sw=48.0):
    """slabs: 갓 슬랩 (w, h, d) 목록(아래→위). 마지막 슬랩 윗면은 발판으로 쓸 수 있다(top_cut 으로 모서리 덜 깎기).
    info(dict)를 주면 cap_top(갓 윗면 높이), top_w, top_d, top_cut 을 채운다."""
    rng = np.random.default_rng(seed)
    capc = {'red': ('red', 'red_hi'), 'orange': ('orange', 'orange_hi'), 'blue': ('blue', 'blue_hi')}[cap]
    bx = []
    SW, SD, CUT = sw, sw * 0.875, 0.2       # 기둥 너비/깊이/모서리 깎기
    # 기초 돌 띠
    bx += octo(0, 0, 0, SW + 4, 4, SD + 4, 'stone2', cut=CUT, noise=0.08)
    # 기둥 (아래가 살짝 넓은 2단)
    bx += octo(0, 3.5, 0, SW, H * 0.5, SD, 'cream', cut=CUT, noise=0.03)
    bx += octo(0, 3.5 + H * 0.5, 0, SW - 3, H * 0.5 - 3.5, SD - 3, 'cream', cut=CUT, noise=0.03)
    # 갓 아래 주름(그늘 띠)
    bx += octo(0, H - 3.0, 0, 84, 3.2, 72, 'cream2', cut=0.24, noise=0.03)
    # 갓 슬랩 (아래 → 위): 넓게 퍼진 둥근 돔
    plat = slabs is not None
    if slabs is None:
        slabs = [(96, 5, 82), (100, 7, 86), (94, 8, 80), (84, 8, 72), (68, 8, 58), (48, 6, 41), (26, 4, 22)]
    y = H
    tops = []
    for i, (w, h, d) in enumerate(slabs):
        last = i == len(slabs) - 1
        col = capc[1] if (i >= 5 and not plat) else capc[0]
        if plat and last:
            col = {'red': '#F45A48', 'orange': '#FFA23C', 'blue': '#5A88FF'}[cap]
        elif plat and i == len(slabs) - 2:
            col = {'red': '#EE5244', 'orange': '#FA9834', 'blue': '#5282FE'}[cap]
        bx += octo(0, y, 0, w, h, d, col, cut=top_cut if (plat and last) else 0.24, noise=0.035,
                   tag='top' if (plat and last) else '')
        tops.append((y, w, h, d))
        y += h
    cap_top = y
    if plat:      # 윗면 뒤쪽 절반에 흰 점 (발판 서는 선 뒤)
        w, d = slabs[-1][0], slabs[-1][2]
        for k in range(4):
            sz = rng.uniform(4.5, 7)
            bx.append(B(-w * 0.36 + k * w * 0.24 + rng.uniform(-3, 3), y + 0.12, -d * 0.18 - rng.uniform(0, d * 0.18),
                        sz, 0.8, sz * 0.85, 'white', noise=0.02, bevel=0.3, tag='top'))
    if info is not None:
        info.update(cap_top=cap_top, top_w=slabs[-1][0], top_d=slabs[-1][2], top_cut=top_cut)
    # 흰 점 (앞면/옆면 + 윗면)
    spots = []
    for (yy, w, h, d) in tops[1:min(5, len(tops) - (1 if plat else 0))]:
        n = 4 if w > 90 else 3 if w > 60 else 2
        for k in range(n):
            for tries in range(20):
                sx = rng.uniform(-w * 0.26 - 2, w * 0.26 + 2)
                ok = all(abs(sx - p[0]) > 12 or abs(yy - p[1]) > 6 for p in spots)
                if ok:
                    break
            spots.append((sx, yy))
            sz = rng.uniform(4.5, 7)
            # 앞면 점 (얇게 붙임)
            bx.append(B(sx, yy + h / 2, d / 2 + 0.25, sz, min(h - 1.5, sz * 0.8), 1.2, 'white', noise=0.02, bevel=0.3))
    for (yy, w, h, d) in (tops[2:-1] if plat else tops[2:6]):
        for k in range(2):
            sx = rng.uniform(-w / 2 + 6, w / 2 - 6); sz = rng.uniform(4, 6.5)
            sz_ = rng.uniform(-d / 2 + 5, d / 2 - 8)
            bx.append(B(sx, yy + h + 0.15, sz_, sz, 1.0, sz * 0.9, 'white', noise=0.02, bevel=0.3))
    # 옆면(오른쪽 x+) 점
    for (yy, w, h, d) in tops[1:4]:
        zz = rng.uniform(-d * 0.26, d * 0.26)
        sz = rng.uniform(4.5, 6.5)
        bx.append(B(w / 2 + 0.25, yy + h / 2, zz, 1.2, min(h - 1.5, sz * 0.8), sz, 'white', noise=0.02, bevel=0.3))
    zf = SD / 2   # 기둥 앞면
    zs = SD * (1 - 2 * CUT) / 2    # 깎인 어깨 앞면 z
    # 문 (아치)
    dw, dh = 15, 27
    bx.append(B(0, 4 + dh / 2 - 0.5, zf + 0.2, dw + 3, dh + 1, 1.6, 'wood4', noise=0.05))        # 문틀
    bx.append(B(0, 4 + dh / 2 + 1.2, zf + 0.2, dw - 3, 2, 1.6, 'wood4', noise=0.05))
    bx.append(B(0, 4 + dh / 2 - 1, zf + 0.7, dw, dh - 2, 1.4, 'wood2', noise=0.09))           # 문판
    bx.append(B(0, 4 + dh - 2.2, zf + 0.7, dw - 4, 2.4, 1.4, 'wood2', noise=0.09))
    for px_ in (-3.2, 0.0, 3.2):
        bx.append(B(px_, 4 + dh / 2 - 1, zf + 1.45, 0.5, dh - 4, 0.3, 'wood3', bevel=0.1, noise=0.0))
    bx.append(B(3.8, 4 + dh / 2 - 2, zf + 1.6, 1.6, 1.6, 1.0, 'yellow', noise=0.0, bevel=0.2))   # 손잡이
    # 작은 차양 위 문
    bx.append(B(0, 4 + dh + 1.6, zf + 2.2, dw + 5, 1.8, 4.2, 'wood3', noise=0.06))
    # 창문
    def window(cx, cy, cz, face='z', s=1.0):
        out = []
        fw = 10 * s
        if face == 'z':
            out.append(B(cx, cy, cz + 0.3, fw + 2.4, fw + 2.4, 1.4, 'wood3', noise=0.05))
            out.append(B(cx, cy, cz + 0.7, fw - 0.4, fw - 0.4, 1.0, 'glass', noise=0.06, emit=('#FFB848', 0.55)))
            out.append(B(cx, cy, cz + 1.25, 1.0, fw - 0.4, 0.3, 'wood4', bevel=0.12, noise=0))
            out.append(B(cx, cy, cz + 1.25, fw - 0.4, 1.0, 0.3, 'wood4', bevel=0.12, noise=0))
            out.append(B(cx, cy - fw / 2 - 2.0, cz + 1.6, fw + 4, 1.6, 3.0, 'wood2', noise=0.05))   # 창턱
            # 창턱 꽃
            for k, col in enumerate(('pink3', 'yellow', 'red_hi')):
                out.append(B(cx - 3.5 + k * 3.5, cy - fw / 2 - 0.2, cz + 2.2, 2.2, 2.2, 2.2, col, noise=0.05, bevel=0.3))
        else:
            out.append(B(cx + 0.3, cy, cz, 1.4, fw + 2.4, fw + 2.4, 'wood3', noise=0.05))
            out.append(B(cx + 0.7, cy, cz, 1.0, fw - 0.4, fw - 0.4, 'glass', noise=0.06, emit=('#FFB848', 0.55)))
            out.append(B(cx + 1.25, cy, cz, 0.3, fw - 0.4, 1.0, 'wood4', bevel=0.12, noise=0))
            out.append(B(cx + 1.25, cy, cz, 0.3, 1.0, fw - 0.4, 'wood4', bevel=0.12, noise=0))
            out.append(B(cx + 1.6, cy - fw / 2 - 2.0, cz, 3.0, 1.6, fw + 4, 'wood2', noise=0.05))
        return out
    wy = 4 + dh * 0.62
    xs_ = SW / 2 - SW * CUT / 2     # 어깨 면 가운데 x
    if 'L' in windows:
        bx += window(-xs_, wy, zs - 0.25, 'z', 0.78)
    if 'R' in windows:
        bx += window(xs_, wy, zs - 0.25, 'z', 0.78)
    if 'S' in windows:
        bx += window(SW / 2 - 0.25, wy, -2, 'x', 0.95)
    # 갓 아래 작은 창 (다락)
    bx += window(0, H - 11, zf - 1.5 - 0.25, 'z', 0.6)
    # 굴뚝
    if chimney:
        cx_, cz_ = 22, -12
        y0 = tops[3][0]
        hh = cap_top - y0 + 8
        bx.append(B(cx_, y0 + hh / 2, cz_, 7, hh, 7, 'stone2', noise=0.1))
        bx.append(B(cx_, y0 + hh - 3, cz_, 7.2, 1.2, 7.2, 'stone3', noise=0.06, bevel=0.2))
        bx.append(B(cx_, y0 + hh + 0.8, cz_, 9, 2, 9, 'stone4', noise=0.08))
    # 디딤돌
    bx.append(B(-1, 0.6, zf + 6, 10, 1.2, 6, 'stone1', noise=0.08))
    bx.append(B(2, 0.5, zf + 12, 8, 1.0, 5, 'stone1', noise=0.08))
    return bx


# ---------------------------------------------------------------- 나무
def oak(seed=3, h=26, r=28, palette=('leaf2', 'leaf3', 'leaf1', 'leaf4')):
    rng = np.random.default_rng(seed)
    bx = []
    bx.append(B(0, h / 2, 0, 7, h, 7, 'wood3', noise=0.12))
    bx.append(B(0, 1.5, 0, 11, 3, 9, 'wood3', noise=0.12))                # 뿌리
    bx.append(B(-4.5, 1, 1, 4, 2, 4, 'wood3', noise=0.12))
    bx.append(B(0, h * 0.7, 0, 3.5, 3.5, 3.5, 'wood4'))
    bx.append(BR(5, h * 0.78, 0, 10, 3.2, 3.2, 'wood3', rot_z(35), noise=0.1))
    bx.append(BR(-5, h * 0.85, 0, 9, 3.0, 3.0, 'wood3', rot_z(-40), noise=0.1))
    cy = h + r * 0.55
    # 큰 덩어리 몇 개 + 작은 큐브
    blobs = []
    for k in range(24):
        th = rng.uniform(0, 2 * np.pi); ph = rng.uniform(-0.45, 1.0)
        rr = r * rng.uniform(0.35, 0.85)
        x = np.cos(th) * np.cos(ph) * rr * 1.15
        z = np.sin(th) * np.cos(ph) * rr * 0.75
        y = cy + np.sin(ph) * rr * 0.8
        s = rng.uniform(0.38, 0.62) * r
        blobs.append((x, y, z, s))
    blobs.append((0, cy, 0, r * 1.05))
    for i, (x, y, z, s) in enumerate(blobs):
        col = palette[0] if y > cy + 2 else palette[1]
        if rng.random() < 0.25:
            col = palette[2] if y > cy else palette[1]
        sy = s * rng.uniform(0.8, 1.0)
        bx.append(B(x, y, z, s, sy, s * rng.uniform(0.85, 1.0), col, noise=0.07))
    # 작은 잎 큐브 (가장자리 결)
    for k in range(10):
        th = rng.uniform(0, 2 * np.pi)
        x = np.cos(th) * r * 0.95; y = cy + np.sin(th) * r * 0.6
        s = rng.uniform(3.5, 5.5)
        bx.append(B(x, y, rng.uniform(-r * 0.3, r * 0.5), s, s, s, palette[0] if y > cy else palette[1], noise=0.06))
    return bx


def cherry(seed=5, h=26, r=30):
    rng = np.random.default_rng(seed)
    bx = []
    bx.append(B(0, h / 2, 0, 6.5, h, 6.5, 'wood4', noise=0.12))
    bx.append(B(0, 1.5, 0, 10, 3, 8, 'wood4', noise=0.12))
    bx.append(BR(-6, h * 0.82, 0, 14, 3.2, 3.2, 'wood4', rot_z(-28), noise=0.1))
    bx.append(BR(7, h * 0.9, 1, 16, 3.0, 3.0, 'wood4', rot_z(32), noise=0.1))
    bx.append(BR(1, h + 4, -1, 3, 10, 3, 'wood4', rot_z(8), noise=0.1))
    cy = h + r * 0.42
    # 둥근 몸통: 층층 돔
    for (fw, fh, fd, dy, col) in ((2.0, 0.42, 1.25, -0.15, 'pink3'), (1.8, 0.4, 1.15, 0.22, 'pink2'),
                                  (1.35, 0.32, 0.9, 0.55, 'pink2'), (0.8, 0.22, 0.6, 0.8, 'pink1')):
        bx += octo(0, cy + dy * r - fh * r / 2, 0, fw * r, fh * r, fd * r, col, cut=0.22, noise=0.05)
    # 표면 꽃송이
    for k in range(30):
        th = rng.uniform(0, 2 * np.pi); ph = rng.uniform(-0.5, 1.1)
        x = np.cos(th) * np.cos(ph) * r * 1.0
        z = np.sin(th) * np.cos(ph) * r * 0.62
        y = cy + np.sin(ph) * r * 0.52
        s_ = rng.uniform(0.22, 0.36) * r
        col = 'pink3' if y < cy - r * 0.1 else ('pink1' if y > cy + r * 0.25 else 'pink2')
        if rng.random() < 0.18:
            col = 'pink1' if col != 'pink1' else 'white'
        bx.append(B(x, y, z, s_, s_ * rng.uniform(0.7, 0.95), s_, col, noise=0.06))
    # 떨어지는 꽃잎 몇 개
    for k in range(7):
        x = rng.uniform(-r * 1.2, r * 1.2); y = rng.uniform(h * 0.2, h * 0.9)
        bx.append(BR(x, y, rng.uniform(0, 8), 1.6, 0.6, 1.6, 'pink1', rot_z(rng.uniform(-40, 40)), bevel=0.15, noise=0))
    return bx


def petals(seed, w=40, d=16, n=14):
    rng = np.random.default_rng(seed)
    return [B(rng.uniform(-w / 2, w / 2), 0.2, rng.uniform(-d / 2, d / 2), rng.uniform(1.2, 2.0), 0.4,
              rng.uniform(1.2, 2.0), 'pink1' if rng.random() < 0.6 else 'pink2', bevel=0.1, noise=0) for _ in range(n)]


def pine(seed=4, h=60, r=15):
    rng = np.random.default_rng(seed)
    bx = [B(0, 5, 0, 5, 10, 5, 'wood3', noise=0.1)]
    tiers = 5
    for i in range(tiers):
        t = i / (tiers - 1)
        w = r * 2 * (1 - 0.72 * t)
        y = 7 + t * (h - 16)
        bx.append(B(rng.uniform(-0.6, 0.6), y + 5, 0, w, 10, w * 0.8, 'leaf4' if i % 2 == 0 else 'leaf5', noise=0.08))
    bx.append(B(0, h - 2, 0, 4, 6, 4, 'leaf4'))
    return bx


# ---------------------------------------------------------------- 소품
def lantern_post(seed=0, h=46):
    bx = []
    bx.append(B(0, 2, 0, 8, 4, 8, 'stone2', noise=0.1))
    bx.append(B(0, 4.6, 0, 6, 1.4, 6, 'stone1', noise=0.08))
    bx.append(B(0, h / 2 + 2, 0, 4.2, h - 2, 4.2, 'wood4', noise=0.1))
    bx.append(B(0, h + 1.0, 0, 6, 1.6, 6, 'wood4', noise=0.06))
    ly = h + 2
    # 랜턴 몸체: 모서리 기둥 + 유리
    for sx in (-3.3, 3.3):
        for sz in (-3.3, 3.3):
            bx.append(B(sx, ly + 5, sz, 1.3, 10, 1.3, 'ink', bevel=0.2, noise=0.03))
    bx.append(B(0, ly + 5, 0, 6.2, 9.4, 6.2, 'glass', noise=0.05, emit=('#FFB850', 1.5)))
    bx.append(B(0, ly + 0.5, 0, 8.4, 1.2, 8.4, 'ink', noise=0.04))
    bx.append(B(0, ly + 10.4, 0, 9.6, 1.6, 9.6, 'wood4', noise=0.05))
    bx.append(B(0, ly + 12.0, 0, 6.6, 1.8, 6.6, 'wood4', noise=0.05))
    bx.append(B(0, ly + 13.4, 0, 3.0, 1.4, 3.0, 'wood4', noise=0.05))
    bx.append(B(0, ly + 14.6, 0, 1.4, 1.4, 1.4, 'yellow', noise=0.0, bevel=0.2))
    return bx


def fence(length=40, seed=0, h=15):
    bx = []
    n = int(length // 10) + 1
    for i in range(n):
        x = -length / 2 + i * length / (n - 1)
        bx.append(B(x, h / 2, 0, 3, h, 3, 'wood2', noise=0.1))
        bx.append(B(x, h + 0.6, 0, 3.6, 1.2, 3.6, 'wood3', noise=0.06))
    for yy in (h * 0.38, h * 0.78):
        bx.append(B(0, yy, 1.8, length + 2, 2.2, 1.2, 'wood1', noise=0.08))
    return bx


def well(seed=0):
    bx = []
    o, t, hh = 26, 4.5, 12
    for (cx, cz, w, d) in ((0, o / 2 - t / 2, o, t), (0, -o / 2 + t / 2, o, t), (-o / 2 + t / 2, 0, t, o - 2 * t),
                           (o / 2 - t / 2, 0, t, o - 2 * t)):
        # 돌 벽: 두 단으로 나눠 이음새
        bx.append(B(cx, hh * 0.25, cz, w, hh * 0.5, d, 'stone2', noise=0.12))
        bx.append(B(cx, hh * 0.75, cz, w, hh * 0.5, d, 'stone1', noise=0.12))
    bx.append(B(0, hh * 0.8, 0, o - 2 * t, 1, o - 2 * t, '#3C6FA8', noise=0.04, bevel=0.1))
    bx.append(B(0, hh + 0.7, 0, o + 1.5, 1.4, o + 1.5, 'stone3', noise=0.08))
    # 기둥 + 지붕
    for sx in (-o / 2 + 2, o / 2 - 2):
        bx.append(B(sx, hh + 12, 0, 2.6, 24, 2.6, 'wood3', noise=0.1))
    bx.append(B(0, hh + 17, 0, o - 2, 1.8, 1.8, 'wood4', noise=0.06))          # 도르래 축
    bx.append(B(0, hh + 12.5, 0, 0.6, 9, 0.6, 'cream3', bevel=0.1, noise=0))   # 밧줄
    bx.append(B(0, hh + 6.5, 0, 4.6, 4.2, 4.6, 'wood2', noise=0.08))            # 두레박
    bx.append(B(0, hh + 8.8, 0, 5.0, 0.8, 5.0, 'wood3', noise=0.05))
    for sgn in (-1, 1):
        bx.append(BR(sgn * 7.5, hh + 26.5, 0, 18, 2.4, 22, 'red', rot_z(-sgn * 30), noise=0.05))
    bx.append(B(0, hh + 31, 0, 3, 2.4, 22.5, 'r3' if False else '#9E2838', noise=0.05))
    return bx


def signpost(seed=0):
    bx = []
    bx.append(B(0, 14, 0, 3, 28, 3, 'wood3', noise=0.1))
    bx.append(B(0, 22, 1.8, 26, 11, 1.8, 'wood1', noise=0.1))
    bx.append(B(0, 22, 1.5, 27.5, 12.5, 1.2, 'wood3', noise=0.06))
    # 버섯 아이콘 + 화살표 (판 앞면 데칼)
    bx.append(B(-6.5, 23.4, 2.95, 9, 3.2, 0.5, 'red', bevel=0.15, noise=0.0))
    bx.append(B(-6.5, 25.4, 2.95, 5.4, 1.4, 0.5, 'red', bevel=0.15, noise=0.0))
    bx.append(B(-8.3, 23.6, 3.25, 1.4, 1.2, 0.3, 'white', bevel=0.1, noise=0.0))
    bx.append(B(-4.7, 24.3, 3.25, 1.2, 1.1, 0.3, 'white', bevel=0.1, noise=0.0))
    bx.append(B(-6.5, 20.0, 2.95, 3.4, 3.6, 0.5, 'cream', bevel=0.15, noise=0.0))
    bx.append(B(5.0, 22, 2.95, 7, 1.8, 0.5, 'wood4', bevel=0.15, noise=0.0))
    bx.append(BR(7.6, 23.1, 2.95, 3.4, 1.6, 0.5, 'wood4', rot_z(-40), bevel=0.15, noise=0.0))
    bx.append(BR(7.6, 20.9, 2.95, 3.4, 1.6, 0.5, 'wood4', rot_z(40), bevel=0.15, noise=0.0))
    return bx


def bench(seed=0):
    bx = []
    for sx in (-11, 11):
        bx.append(B(sx, 3.5, 1.5, 2.4, 7, 2.4, 'wood3', noise=0.08))
        bx.append(B(sx, 7, -3.0, 2.4, 14, 2.4, 'wood3', noise=0.08))
    bx.append(B(0, 7.6, 0, 30, 1.6, 4.0, 'wood1', noise=0.1))
    bx.append(B(0, 7.6, -4.2, 30, 1.6, 3.6, 'wood2', noise=0.1))
    bx.append(B(0, 11.8, -4.0, 30, 2.4, 1.4, 'wood1', noise=0.1))
    bx.append(B(0, 15.0, -4.0, 30, 2.4, 1.4, 'wood1', noise=0.1))
    return bx


def bush(seed=0, w=16, h=9, cols=('leaf3', 'leaf2', 'leaf4')):
    rng = np.random.default_rng(seed)
    bx = []
    n = max(3, int(w / 4))
    for k in range(n):
        x = rng.uniform(-w / 2, w / 2) * 0.8
        s = rng.uniform(0.45, 0.75) * h * 1.2
        y = s * 0.45 + rng.uniform(0, h * 0.25)
        bx.append(B(x, y, rng.uniform(-3, 3), s, s * 0.9, s * 0.9, cols[int(rng.integers(0, len(cols)))], noise=0.08))
    return bx


def flowers(seed=0, w=24, d=10, n=10, cols=('red_hi', 'yellow', 'pink3', 'white', '#9CC8FF')):
    rng = np.random.default_rng(seed)
    bx = []
    for k in range(n):
        x = rng.uniform(-w / 2, w / 2); z = rng.uniform(-d / 2, d / 2)
        hh = rng.uniform(2.5, 4.5)
        bx.append(B(x, hh / 2, z, 0.9, hh, 0.9, 'leaf4', bevel=0.1, noise=0))
        bx.append(B(x + 1, 1.0, z, 1.6, 0.8, 1.2, 'leaf3', bevel=0.1, noise=0))
        c = cols[int(rng.integers(0, len(cols)))]
        bx.append(B(x, hh + 0.9, z, 2.4, 2.0, 2.4, c, bevel=0.35, noise=0.04))
        bx.append(B(x, hh + 1.95, z + 0.2, 0.9, 0.3, 0.9, 'yellow' if c != 'yellow' else 'orange', bevel=0.1, noise=0))
    return bx


def tuft(seed=0, n=5, w=6):
    rng = np.random.default_rng(seed)
    bx = []
    for k in range(n):
        hh = rng.uniform(2, 4.2)
        bx.append(B(rng.uniform(-w / 2, w / 2), hh / 2, rng.uniform(-1.5, 1.5), 1.1, hh, 1.1,
                    ('leaf3', 'leaf2', 'leaf4')[int(rng.integers(0, 3))], bevel=0.15, noise=0.03))
    return bx


def rocks(seed=0, n=3, s=6):
    rng = np.random.default_rng(seed)
    bx = []
    x = -s * n * 0.4
    for k in range(n):
        w = rng.uniform(0.6, 1.0) * s; h = w * rng.uniform(0.6, 0.9)
        bx.append(BR(x, h / 2 - 0.3, rng.uniform(-2, 2), w, h, w * 0.9, ('stone1', 'stone2')[k % 2],
                     rot_y(rng.uniform(-25, 25)), noise=0.1))
        x += w * 0.85
    return bx


def mushroom_small(seed=0, col='red', s=1.0):
    bx = [B(0, 2.5 * s, 0, 2.6 * s, 5 * s, 2.6 * s, 'cream', noise=0.03),
          B(0, 5.6 * s, 0, 7 * s, 2.4 * s, 7 * s, col, noise=0.04),
          B(0, 7.2 * s, 0, 4.4 * s, 1.4 * s, 4.4 * s, col, noise=0.04),
          B(-1.4 * s, 5.8 * s, 3.55 * s, 1.4 * s, 1.2 * s, 0.4, 'white', bevel=0.1, noise=0),
          B(1.8 * s, 6.0 * s, 3.55 * s, 1.0 * s, 1.0 * s, 0.4, 'white', bevel=0.1, noise=0)]
    return bx


def barrel(seed=0):
    bx = octo(0, 0, 0, 9, 11, 9, 'wood2', cut=0.22, noise=0.1)
    bx += octo(0, 2, 0, 9.6, 1.2, 9.6, 'stone4', cut=0.22, noise=0.04)
    bx += octo(0, 8, 0, 9.6, 1.2, 9.6, 'stone4', cut=0.22, noise=0.04)
    return bx


def crate(seed=0, s=8):
    return [B(0, s / 2, 0, s, s, s, 'wood1', noise=0.12), B(0, s / 2, s / 2 + 0.1, s - 2, 0.8, 0.4, 'wood3', bevel=0.1)]
