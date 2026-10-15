"""버섯마을 맵 레이어 구성 (복셀 장면). 각 함수는 Box 목록을 돌려준다.

지면 레이어 좌표: 모델 1단위 = 월드 2단위 = 3px. 원점(0,0,0) = 월드 (0, 440) = 캐릭터가 걷는 선(깊이 z=0).
"""
import numpy as np
from vox import Box, hex2lin
import props as P
from props import B, placed

# ====================================================================== ground
GROUND_FRONT = 12.0      # 잔디 윗면 앞 가장자리 z
GROUND_BACK = -104.0     # 잔디 윗면 뒤 가장자리 z

GRASS = ('#7FD04A', '#86D650', '#78C846', '#8FDB58', '#74C244')
DIRT = ('#7E4A2C', '#714126', '#87522F', '#784530')
STONE = ('#8A849A', '#7C7690', '#948EA6', '#857F95')


def _row_blocks(rng, x0, x1, wmin, wmax):
    xs = [x0]
    while xs[-1] < x1:
        xs.append(xs[-1] + float(rng.integers(wmin, wmax + 1)))
    return list(zip(xs[:-1], xs[1:]))


def ground_base(seed=11, x0=-24, x1=1224):
    rng = np.random.default_rng(seed)
    bx = []
    # 윗면 줄 (앞 → 뒤)
    z = GROUND_FRONT
    rows = []
    while z > GROUND_BACK:
        dz = 8.0
        rows.append((z - dz, z))
        z -= dz
    for ri, (za, zb) in enumerate(rows):
        for (xa, xb) in _row_blocks(rng, x0 - rng.integers(0, 8), x1, 8, 18):
            col = GRASS[int(rng.integers(0, len(GRASS)))]
            # 저주파 얼룩: 진한 잔디 패치와 햇빛 받은 밝은 패치
            xm, zm = (xa + xb) / 2, (za + zb) / 2
            f = np.sin(xm * 0.031 + zm * 0.05) + 0.7 * np.sin(xm * 0.083 - zm * 0.11 + 1.7)
            if f > 1.05:
                col = ('#68B83E', '#62B03C')[int(rng.integers(0, 2))]
            elif f < -1.2:
                col = ('#98DE60', '#A0E266')[int(rng.integers(0, 2))]
            hgt = 4.0
            bx.append(Box(((xa + xb) / 2, -hgt / 2, (za + zb) / 2), ((xb - xa) / 2, hgt / 2, (zb - za) / 2), None, col,
                          noise=0.05))
    # 앞 단면: 흙/돌 블록 (벽돌 엇갈림)
    za, zb = rows[0]
    y = -4.0
    k = 0
    while y > -64:
        h = 8.0
        for (xa, xb) in _row_blocks(rng, x0 - rng.integers(0, 10), x1, 8, 16):
            depth = k
            p_stone = (0.0, 0.03, 0.10, 0.22, 0.4, 0.55, 0.6, 0.6)[min(depth, 7)]
            pal = STONE if rng.random() < p_stone else DIRT
            col = hex2lin(pal[int(rng.integers(0, len(pal)))]) * (1 - 0.07 * k)
            bx.append(Box(((xa + xb) / 2, y - h / 2, (za + zb) / 2), ((xb - xa) / 2, h / 2, (zb - za) / 2), None, col,
                          noise=0.07))
        y -= h; k += 1
    # 잔디가 흙 앞으로 조금 늘어진 술 (앞면 윗단)
    x = x0
    while x < x1:
        x += float(rng.integers(6, 16))
        w = float(rng.integers(2, 5)); hh = float(rng.uniform(1.5, 3.2))
        bx.append(B(x, -4 - hh / 2 + 0.3, GROUND_FRONT + 0.4, w, hh, 1.0, GRASS[int(rng.integers(0, 3))], noise=0.04,
                    bevel=0.25))
    # 흙 속 작은 돌/뿌리 박힌 점
    for i in range(70):
        x = rng.uniform(x0, x1); yy = rng.uniform(-44, -14)
        s = rng.uniform(1.6, 3.2)
        bx.append(B(x, yy, GROUND_FRONT + 0.25, s, s * rng.uniform(0.6, 1.0), 0.8,
                    STONE[int(rng.integers(0, 4))] if rng.random() < 0.7 else '#5E3620', noise=0.05, bevel=0.2))
    return bx


# 소품 배치: (함수, x, z, yaw, 인자)
def ground_props():
    L = []
    add = lambda boxes, x, z, yaw=0.0, s=1.0: L.extend(placed(boxes, x, 0, z, yaw, s))
    # 왼쪽 끝 숲
    add(P.oak(31, h=30, r=30), 22, -70, 0)
    add(P.bush(32, 22, 10), 64, -46)
    add(P.flowers(33, 20, 8, 7), 60, -30)
    # 빨간 버섯 집
    add(P.mushroom_house('red', 42, seed=1), 150, -66, 18, 1.2)
    add(P.mushroom_small(34, 'red', 1.0), 112, -30, 10)
    add(P.lantern_post(), 230, -24)
    add(P.flowers(35, 40, 10, 12), 268, -26)
    add(P.fence(46), 270, -38)
    add(P.tuft(36), 236, -14)
    # 벚꽃 + 꽃잎
    add(P.cherry(37), 336, -64)
    add(P.petals(38, 70, 30, 26), 336, -32)
    add(P.lantern_post(), 384, -24)
    # 우물 + 벤치
    add(P.well(), 432, -46, -16)
    add(P.rocks(39, 3, 6), 466, -34)
    add(P.bench(), 500, -32, 0)
    add(P.tuft(40), 520, -12)
    # 주황 버섯 집 (중앙)
    add(P.mushroom_house('orange', 38, seed=2), 594, -66, -14, 1.1)
    add(P.flowers(41, 26, 8, 8, ('yellow', 'white', 'orange')), 548, -28)
    add(P.signpost(), 664, -28, 8)
    add(P.mushroom_small(42, 'orange', 0.9), 690, -26, -10)
    add(P.mushroom_small(43, 'red', 0.7), 698, -20, 20)
    add(P.lantern_post(), 724, -24)
    # 오른쪽 숲 조금
    add(P.oak(44, h=28, r=27, palette=('leaf2', 'leaf3', 'leaf1', 'leaf4')), 770, -72)
    add(P.bush(45, 24, 11), 802, -44)
    add(P.rocks(46, 2, 7), 826, -30)
    add(P.fence(40), 860, -38)
    add(P.flowers(47, 30, 8, 9, ('pink3', 'white', '#9CC8FF')), 860, -26)
    # 파란 버섯 집
    add(P.mushroom_house('blue', 46, seed=3), 952, -66, 20, 1.28)
    add(P.barrel(), 1034, -36, 10)
    add(P.crate(48, 8), 1046, -30, -12)
    add(P.lantern_post(), 1068, -24)
    add(P.cherry(49, h=24, r=27), 1104, -66)
    add(P.petals(50, 60, 28, 20), 1104, -34)
    add(P.oak(51, h=32, r=29), 1186, -70)
    add(P.flowers(52, 30, 8, 10), 1160, -28)
    add(P.tuft(53), 1140, -14)
    # 뒤 가장자리 덤불/풀 띠 (잔디 끝선 가림)
    rng = np.random.default_rng(54)
    x = -16
    while x < 1220:
        w = rng.uniform(14, 30); h = rng.uniform(6, 13)
        cols = (('leaf3', 'leaf2', 'leaf4') if rng.random() < 0.7 else ('leaf4', 'leaf5', 'leaf3'))
        L.extend(placed(P.bush(int(rng.integers(0, 1 << 30)), w, h, cols), x, 0, GROUND_BACK + 7 + rng.uniform(-3, 3)))
        x += w * rng.uniform(0.6, 0.9)
    # 흩어진 풀 술
    for i in range(46):
        x = rng.uniform(0, 1200); z = rng.uniform(-86, -14)
        L.extend(placed(P.tuft(int(rng.integers(0, 1 << 30)), int(rng.integers(3, 6)), 5), x, 0, z))
    return L


def ground():
    return ground_base() + ground_props()
