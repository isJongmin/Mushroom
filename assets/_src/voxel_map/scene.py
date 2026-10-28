"""버섯마을 맵 레이어 구성 (복셀 장면). 각 함수는 Box 목록을 돌려준다.

지면 레이어 좌표: 모델 1단위 = 월드 2단위 = 3px. 원점(0,0,0) = 월드 (0, 440) = 캐릭터가 걷는 선(깊이 z=0).
"""
import numpy as np
from vox import Box, hex2lin
import props as P
from props import B, placed
import platforms as PL

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


# 소품 배치 (사이클 8: 발판 구조물 사이에 배치. 모델 x = 월드 x / 2)
def waterfall(x, top, z, w=7.0, seed=0):
    """x 중심, top 에서 지면(0)까지 떨어지는 폭포 + 물보라."""
    rng = np.random.default_rng(seed)
    bx = []
    yy = top
    k = 0
    while yy > 0.5:
        hh = min(6.0, yy)
        ww = w + min(k, 10) * 0.12
        bx.append(B(x + rng.uniform(-0.25, 0.25), yy - hh / 2, z, ww, hh + 0.15, 3.0,
                    ('#A8DEFA', '#C4EAFE', '#B6E4FC')[k % 3], noise=0.05, bevel=0.3, emit=('#DDF4FF', 0.10)))
        # 흰 물줄기 결
        if k % 2 == 0:
            bx.append(B(x + rng.uniform(-w / 3, w / 3), yy - hh / 2, z + 1.6, 1.0, hh * 0.8, 0.4, '#FFFFFF', noise=0,
                        bevel=0.1, emit=('#FFFFFF', 0.15)))
        yy -= hh; k += 1
    # 물보라 큐브
    for j in range(10):
        s_ = rng.uniform(1.6, 3.6)
        bx.append(B(x + rng.uniform(-w, w), rng.uniform(0.5, 4.5), z + rng.uniform(-2, 4), s_, s_, s_, '#FFFFFF',
                    noise=0.02, bevel=0.3))
    return bx


def pond(x0, x1, z0, z1, seed=0):
    rng = np.random.default_rng(seed)
    bx = [B((x0 + x1) / 2, 0.15, (z0 + z1) / 2, x1 - x0, 0.6, z0 - z1, '#6CC4F0', noise=0.03, bevel=0.1,
            emit=('#BFE8FF', 0.08))]
    # 돌 테두리
    x = x0 - 2
    while x < x1 + 2:
        s_ = rng.uniform(2.5, 4.5)
        for zz in (z0 + 1.0, z1 - 1.0):
            bx.append(B(x, s_ * 0.3, zz + rng.uniform(-0.6, 0.6), s_, s_ * 0.7, s_ * 0.8, ('stone1', 'stone2')[int(x) % 2],
                        noise=0.08))
        x += s_ * 0.9
    for k in range(14):       # 반짝임
        bx.append(B(rng.uniform(x0 + 2, x1 - 2), 0.5, rng.uniform(z1 + 2, z0 - 2), rng.uniform(2, 5), 0.2, 0.6,
                    '#FFFFFF', noise=0, bevel=0, emit=('#FFF4D8', 0.7)))
    # 연잎
    for k in range(3):
        bx.append(B(rng.uniform(x0 + 4, x1 - 4), 0.55, rng.uniform(z1 + 3, z0 - 3), 3.2, 0.3, 3.0, 'leaf2', noise=0.03,
                    bevel=0.1))
    return bx


def ground_props():
    L = []
    add = lambda boxes, x, z, yaw=0.0, s=1.0, y=0.0: L.extend(placed(boxes, x, y, z, yaw, s))
    pinfo = PLAT_INFO
    # ---- 왼쪽 끝
    add(P.cherry(31, h=34, r=36), 22, -74)
    add(P.petals(30, 70, 30, 30), 30, -40)
    add(P.bush(32, 22, 10), 52, -46)
    add(P.flowers(33, 18, 8, 7), 46, -28)
    add(P.lantern_post(), 50, -22)
    # 선반 아래
    add(P.flowers(35, 40, 10, 12), 96, -36)
    add(P.rocks(36, 3, 5), 120, -40)
    # 빨간 집 주변
    add(P.mushroom_small(34, 'red', 1.0), 150, -14, 10)
    add(P.mushroom_small(37, 'orange', 0.7), 158, -12, -20)
    add(P.lantern_post(), 262, -22)
    add(P.tuft(38), 240, -14)
    # 벚꽃 섬 아래: 울타리 + 벤치 + 떨어진 꽃잎
    add(P.fence(44), 300, -42)
    add(P.bench(), 292, -28, 0)
    add(P.petals(39, 80, 30, 34), 300, -40)
    add(P.flowers(40, 26, 8, 8, ('yellow', 'white', 'pink3')), 322, -22)
    # 우물 + 랜턴
    add(P.well(), 352, -50, -16)
    add(P.lantern_post(), 380, -22)
    # 주황 오두막 주변
    add(P.mushroom_small(42, 'orange', 0.9), 392, -14, -10)
    add(P.mushroom_small(43, 'red', 0.7), 462, -16, 20)
    add(P.flowers(44, 20, 6, 6), 460, -26)
    # 다리 아래
    add(P.signpost(), 512, -30, 8)
    add(P.barrel(), 548, -40, 10)
    add(P.crate(45, 8), 560, -34, -12)
    add(P.crate(46, 6), 556, -34, 20, 1.0, 8.0)
    add(P.bush(47, 20, 9), 530, -52)
    add(P.flowers(48, 30, 8, 9, ('pink3', 'white', '#9CC8FF')), 572, -24)
    # 폭포 연못
    add(pond(662, 728, -26, -66, 49), 0, 0)
    add(P.rocks(50, 3, 6), 640, -34)
    add(P.tuft(51), 650, -20)
    add(P.lantern_post(), 742, -22)
    add(P.cherry(62, h=20, r=22), 700, -88)
    # 파란 집 왼쪽: 벚꽃
    add(P.cherry(52, h=22, r=24), 772, -78)
    add(P.petals(53, 50, 24, 20), 770, -40)
    add(P.flowers(54, 22, 8, 8), 790, -20)
    # 파란 집 주변 / 단구
    add(P.barrel(), 902, -14, 10)
    add(P.flowers(55, 14, 6, 5, ('yellow', 'white')), 914, -14)
    # 오른쪽 끝 마을
    add(P.lantern_post(), 1024, -22)
    add(P.oak(56, h=28, r=27, palette=('leaf2', 'leaf3', 'leaf1', 'leaf4')), 1050, -74)
    add(P.cherry(57, h=24, r=27), 1112, -66)
    add(P.petals(58, 60, 28, 22), 1112, -34)
    add(P.fence(40), 1080, -40)
    add(P.flowers(59, 30, 8, 10), 1080, -26)
    add(P.bench(), 1150, -30, -6)
    add(P.lantern_post(), 1132, -22)
    add(P.oak(60, h=32, r=29), 1192, -70)
    add(P.tuft(61), 1170, -14)
    # 뒤 가장자리 덤불/풀 띠 (잔디 끝선 가림)
    rng = np.random.default_rng(54)
    x = -16
    while x < 1220:
        w = rng.uniform(14, 30); h = rng.uniform(6, 13)
        cols = (('leaf3', 'leaf2', 'leaf4') if rng.random() < 0.7 else ('leaf4', 'leaf5', 'leaf3'))
        L.extend(placed(P.bush(int(rng.integers(0, 1 << 30)), w, h, cols), x, 0, GROUND_BACK + 7 + rng.uniform(-3, 3)))
        x += w * rng.uniform(0.6, 0.9)
    # 흩어진 풀 술 (연못 피함)
    for i in range(46):
        x = rng.uniform(0, 1200); z = rng.uniform(-86, -14)
        if 655 < x < 735 and z < -20:
            continue
        L.extend(placed(P.tuft(int(rng.integers(0, 1 << 30)), int(rng.integers(3, 6)), 5), x, 0, z))
    return L


def platform_props():
    """발판 위/주변 장식 (발판 뒤쪽, 서는 선 뒤)."""
    L = []
    add = lambda boxes, x, y, z, yaw=0.0, s=1.0: L.extend(placed(boxes, x, y, z, yaw, s))
    I = PLAT_INFO
    byid = {p['id']: p for p in PL.PLATFORMS}
    # 빨간 갓 윗면 뒤: 작은 버섯 + 꽃
    h = I['red-cap']
    add(P.mushroom_small(70, 'red', 0.9), 222, h['Yt'], h['z0'] - 16, 15)
    add(P.flowers(71, 12, 4, 4, ('yellow', 'white')), 172, h['Yt'], h['z0'] - 14)
    # 벚꽃 섬: 벚나무 + 꽃
    i = I['isle-cherry']
    add(P.cherry(72, h=22, r=25), i['cx'] + 8, i['Yt'], i['zb'] + 9)
    add(P.flowers(73, 20, 4, 6, ('pink3', 'white', 'pink2')), i['cx'] - 22, i['Yt'], i['zb'] + 6)
    add(PL.sparkles(74, 60, 30, 0) + P.petals(75, 60, 8, 14), i['cx'], i['Yt'], i['zb'] + 10)
    # 주황 오두막 윗면 뒤
    h = I['orange-cap']
    add(P.flowers(76, 16, 3, 5, ('white', 'yellow')), 440, h['Yt'], h['z0'] - 16)
    # 폭포 섬: 작은 버섯 집 + 소나무 + 폭포
    i = I['isle-falls']
    add(P.mushroom_house('red', 40, seed=77, chimney=True), i['cx'] - 12, i['Yt'], i['zb'] + 9, 14, 0.3)
    add(P.pine(78, h=36, r=9), i['cx'] + 22, i['Yt'], i['zb'] + 6)
    add(P.flowers(79, 14, 3, 5), i['cx'] + 6, i['Yt'], i['zb'] + 5)
    L.extend(waterfall(byid['isle-falls']['x2'] / 2 - 6.5, i['Yt'] - 5.0, -30.0, 10.0, 80))
    # 파란 갓 윗면 뒤
    h = I['blue-cap']
    add(P.mushroom_small(81, 'blue', 0.8), 878, h['Yt'], h['z0'] - 17, -10)
    add(P.flowers(82, 12, 4, 4, ('white', '#9CC8FF', 'yellow')), 840, h['Yt'], h['z0'] - 15)
    # 단구 윗면: 랜턴 + 꽃
    c = I['cliff-right']
    add(P.lantern_post(), 1000, c['Yt'], c['zb'] + 8)
    add(P.flowers(83, 30, 6, 10), 960, c['Yt'], c['zb'] + 8)
    add(P.bush(84, 16, 8), 932, c['Yt'], c['zb'] + 6)
    # 비밀 발판: 금빛 버섯 / 보물 상자
    i = I['secret-sky']
    add(PL.golden_mushroom(1.2), i['cx'] + 4, i['Yt'], i['zb'] + 7, -10)
    add(P.flowers(85, 16, 3, 5, ('yellow', 'white', 'pink3')), i['cx'] - 10, i['Yt'], i['zb'] + 5)
    add(PL.sparkles(86, 40, 26, 9), i['cx'], i['Yt'], i['zb'] + 9)
    i = I['secret-chest']
    add(PL.chest(), i['cx'] + 3, i['Yt'], i['zb'] + 8, -12)
    add(P.flowers(87, 14, 3, 5, ('pink3', 'white', 'yellow')), i['cx'] - 13, i['Yt'], i['zb'] + 5)
    add(PL.sparkles(88, 36, 24, 8), i['cx'], i['Yt'], i['zb'] + 9)
    return L


PLAT_BOXES, PLAT_INFO = PL.build_all()


def ground():
    return ground_base() + PLAT_BOXES + platform_props() + ground_props()
