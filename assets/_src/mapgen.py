"""맵 레이어 7장 생성 (style-guide v2.0 6장). 아트 좌표 1200 x 270, 지면 y 220.
반복 레이어(하늘, 구름, 산, 언덕, 나무)는 가로로 이음매 없이 이어진다 (주기 함수 + 좌표 wrap)."""
import os, math, random
from PIL import Image
from palette import RAMP, rgba

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Canvas:
    def __init__(self, w, h, wrap=False):
        self.w, self.h, self.wrap = w, h, wrap
        self.px = {}

    def put(self, x, y, t):
        if self.wrap:
            x %= self.w
        if 0 <= x < self.w and 0 <= y < self.h and t:
            self.px[(x, y)] = t

    def get(self, x, y):
        if self.wrap:
            x %= self.w
        return self.px.get((x, y))

    def hline(self, x0, x1, y, t):
        for x in range(x0, x1 + 1):
            self.put(x, y, t)

    def image(self):
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        for (x, y), t in self.px.items():
            im.putpixel((x, y), rgba(t))
        return im


def disc(cx, cy, r):
    return {(cx + x, cy + y) for y in range(-r, r + 1) for x in range(-r, r + 1) if x * x + y * y <= r * r + r * 0.6}


def edges(pts):
    return {(x, y) for (x, y) in pts if any((x + dx, y + dy) not in pts for dx, dy in N4)}


# ------------------------------------------------------------------ 1 하늘
SKY_BANDS = [('k1', 0, 59), ('k2', 60, 104), ('k3', 105, 139), ('k4', 140, 169), ('k5', 170, 269)]


def sky():
    c = Canvas(16, 270)
    for t, a, b in SKY_BANDS:
        for y in range(a, b + 1):
            c.hline(0, 15, y, t)
    return c


# ------------------------------------------------------------------ 2 구름
def cloud(c, cx, base, w):
    """원 5개를 합친 뭉게구름, 아랫면 평평. 몸통 white, 아래 2줄 k5, 맨 아랫줄 k4."""
    r = max(5, w // 5)
    lobes = [(-w // 2 + r, int(r * 0.9)), (-w // 5, int(r * 1.3)), (w // 8, int(r * 1.55)),
             (w // 3, int(r * 1.15)), (w // 2 - r, int(r * 0.85))]
    pts = set()
    for ox, rr in lobes:
        for p in disc(cx + ox, base - rr // 3, rr):
            if p[1] <= base:
                pts.add(p)
    for x in range(cx - w // 2 + r // 2, cx + w // 2 - r // 2 + 1):     # 평평한 아랫면 채움
        for y in range(base - r // 2, base + 1):
            pts.add((x, y))
    bottom = max(y for _, y in pts)
    for (x, y) in pts:
        t = 'white'
        if y == bottom:
            t = 'k4'
        elif y >= bottom - 2:
            t = 'k5'
        c.put(x, y, t)
    # 구름 아랫부분 덩어리 사이 골 (k5 한두 점) - 입체감
    for ox, rr in lobes[1:-1]:
        x = cx + ox + rr // 2
        for y in (bottom - 3,):
            if c.get(x, y) == 'white':
                c.put(x, y, 'k5')


def clouds():
    c = Canvas(480, 70, wrap=True)
    for cx, base, w in [(66, 40, 48), (205, 26, 32), (330, 56, 60), (440, 33, 28)]:
        cloud(c, cx, base, w)
    return c


# ------------------------------------------------------------------ 3, 4 산과 언덕
def ridge(width, height, base, peaks, fill, top):
    c = Canvas(width, height, wrap=True)
    hs = []
    for x in range(width):
        h = base
        for (cx, amp, wid) in peaks:
            for off in (-width, 0, width):
                d = (x - cx - off) / wid
                h = max(h, base + amp * math.exp(-d * d))
        hs.append(int(round(h)))
    tops = [height - h for h in hs]
    for x in range(width):
        for y in range(tops[x], height):
            c.put(x, y, fill)
        nb = max(tops[(x - 1) % width], tops[(x + 1) % width])
        for y in range(tops[x], max(tops[x], nb - 1) + 1):        # 이어진 능선 1px
            c.put(x, y, top)
    return c


def mountains():
    return ridge(640, 110, 20, [(60, 62, 48), (200, 44, 58), (335, 84, 52), (470, 40, 50), (580, 60, 44)], 'm1', 'white')


def hills():
    return ridge(640, 80, 18, [(100, 30, 70), (280, 20, 56), (430, 30, 66), (590, 16, 46)], 'm2', 'm1')


# ------------------------------------------------------------------ 5 중경 나무
def leaf_ball(c, cx, cy, r, tick_seed=0):
    """잎: 원 3개(가운데 r, 좌우 0.7r을 r/3 아래로). 뒤 원 -> 앞 원 순서로 칠하고
    앞 원이 뒤 원과 닿는 곳은 g4 선(잎 덩어리 구분). 각 원 안에서 왼쪽 위 g2, 끝 g1."""
    circles = [(cx - r // 2 - 2, cy + r // 3, int(r * 0.7)), (cx + r // 2 + 2, cy + r // 3, int(r * 0.7)), (cx, cy, r)]
    owner = {}
    for i, (x0, y0, rr) in enumerate(circles):
        for p in disc(x0, y0, rr):
            owner[p] = i
    union = set(owner)
    for p, i in owner.items():
        x, y = p
        x0, y0, rr = circles[i]
        edge = any((x + dx, y + dy) not in union for dx, dy in N4)
        seam = any(owner.get((x + dx, y + dy), i) < i for dx, dy in N4) and (y > y0 - rr // 3)
        d = ((x - x0) + (y - y0)) / rr
        if edge or seam:
            t = 'g4'
        elif d < -1.05:
            t = 'g1'
        elif d < -0.45:
            t = 'g2'
        else:
            t = 'g3'
            if (x * 7 + y * 13 + tick_seed) % 29 == 0:      # 잎 결 (g2 점)
                t = 'g2'
        c.put(x, y, t)
    return union


def trunk(c, cx, base_y, h):
    for y in range(base_y - h, base_y + 1):
        c.hline(cx - 2, cx + 2, y, 'w3')
        c.put(cx - 2, y, 'w4')
        c.put(cx + 2, y, 'w4')
        c.put(cx - 1, y, 'w2')
    c.put(cx - 3, base_y, 'w4')                     # 뿌리 퍼짐
    c.put(cx + 3, base_y, 'w4')


def tree(c, cx, base_y, r, seed=0):
    trunk(c, cx, base_y, r)
    leaf_ball(c, cx, base_y - r - r // 2, r, seed)


def trees():
    c = Canvas(640, 120, wrap=True)
    for i, (cx, r) in enumerate([(40, 16), (130, 22), (175, 14), (300, 20), (420, 17), (520, 24), (600, 15)]):
        tree(c, cx, 112, r, i)
    # 덤불 띠: 높이 6-11 물결, g3 채움, 윗줄 g4 (주기 640의 정수배 -> 이음매 없음)
    hs = []
    for x in range(640):
        h = 8.5 + 1.6 * math.sin(2 * math.pi * x * 23 / 640) + 1.2 * math.sin(2 * math.pi * x * 61 / 640 + 1.0)
        hs.append(max(6, min(11, int(round(h)))))
    for x in range(640):
        top = 120 - hs[x]
        for y in range(top, 120):
            c.put(x, y, 'g3')
        nb = max(120 - hs[(x - 1) % 640], 120 - hs[(x + 1) % 640])
        for y in range(top, max(top, nb - 1) + 1):
            c.put(x, y, 'g4')
        if top + 2 < 120 and (x * 5) % 11 == 0:
            c.put(x, top + 2, 'g2')
    return c


# ------------------------------------------------------------------ 6 마을
B = 159          # 마을 레이어 마지막 불투명 행 (= 아트 y 219)


def house(c, cx, cap, cw, ch, sw, sh):
    hl, base, _, line = RAMP['cap-' + cap]
    a, b = cw / 2, ch
    top = B + 1 - sh                 # 기둥 윗선
    cb = top + 4                     # 갓 아랫선
    cc = cx - 0.5                    # 짝수 폭 대칭 중심
    x0, x1 = cx - sw // 2, cx + sw // 2 - 1
    # --- 굴뚝 + 연기 (갓 뒤)
    chx = cx + int(a * 0.45)
    cht = cb - ch + 2
    for y in range(cht, cht + 16):
        c.hline(chx, chx + 7, y, 'st1')
        c.put(chx + 5, y, 'st2')
        c.put(chx + 6, y, 'st2')
        c.put(chx, y, 'hb1')
        c.put(chx + 7, y, 'hb1')
    for y in range(cht + 4, cht + 16, 4):            # 벽돌 줄
        c.hline(chx + 1, chx + 4, y, 'st2')
    c.hline(chx - 1, chx + 8, cht, 'hb1')
    c.hline(chx - 1, chx + 8, cht + 1, 'st2')
    c.put(chx - 1, cht + 1, 'hb1')
    c.put(chx + 8, cht + 1, 'hb1')
    c.hline(chx, chx + 4, cht + 1, 'st1')
    for (sx, sy, rr) in [(chx + 4, cht - 5, 3), (chx + 8, cht - 12, 4)]:
        pts = disc(sx, sy, rr)
        mb = max(y for _, y in pts)
        for (x, y) in pts:
            c.put(x, y, 'c2' if y == mb else 'c1')
    # --- 기둥 (종 모양)
    for y in range(top, B + 1):
        t = (y - top) / (sh - 1)
        f = int(3 * t * t + 1e-9)
        l, r = x0 - f, x1 + f
        c.hline(l, r, y, 'c1')
        c.put(l + 1, y, 'c2')
        c.put(l + 2, y, 'c2')
        c.put(l + 5, y, 'white')
        c.put(l + 6, y, 'white')
        c.put(r - 2, y, 'c2')
        c.put(r - 1, y, 'c3')
        c.put(l, y, 'w3')
        c.put(r, y, 'w3')
    c.hline(x0 - 3, x1 + 3, B, 'w3')
    # --- 문 (아치 14 x 22, 아래 끝 행 157)
    dl, dw, dh = cx - 12, 14, 22
    db = B - 2
    door = set()
    for r_ in range(dh):
        y = db - dh + 1 + r_
        inset = [3, 1, 1][r_] if r_ < 3 else 0
        for x in range(dl + inset, dl + dw - inset):
            door.add((x, y))
    de = edges(door)
    for (x, y) in door:
        c.put(x, y, 'w4' if (x, y) in de else 'w2')
    for y in range(db - dh + 4, db):
        c.put(dl + 5, y, 'w3')
        c.put(dl + 9, y, 'w3')
    for (x, y) in door:                               # 아치 안쪽 윗줄 하이라이트
        if (x, y) not in de and (x, y - 1) in de and y < db - dh + 5:
            c.put(x, y, 'w1')
    c.put(dl + 10, db - 9, 'y2')
    c.put(dl + 11, db - 9, 'y4')
    c.hline(dl - 1, dl + dw, B - 1, 'st1')
    c.hline(dl - 1, dl + dw, B, 'st2')
    c.put(dl - 1, B - 1, 'st2')
    c.put(dl + dw, B - 1, 'st2')
    # --- 둥근 창 10 x 10 (중심 = 기둥 중심 +10, 기둥 위 +12)
    wx, wy = cx + 5, top + 7
    spans = [(3, 6), (1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (3, 6)]
    win = {(wx + x, wy + r_) for r_, (p, q) in enumerate(spans) for x in range(p, q + 1)}
    we = edges(win)
    for (x, y) in win:
        c.put(x, y, 'w3' if (x, y) in we else 'y1')
    for r_ in range(1, 9):
        c.put(wx + 5, wy + r_, 'w3')
    c.hline(wx + 1, wx + 8, wy + 5, 'w3')
    c.put(wx + 2, wy + 2, 'y2')
    c.put(wx + 7, wy + 7, 'y2')
    c.hline(wx + 2, wx + 7, wy + 10, 'c2')            # 창턱 그림자
    # --- 갓
    capp = set()
    for y in range(cb - b, cb + 1):
        dy = (cb - y) / b
        half = a * math.sqrt(max(0.0, 1 - dy * dy))
        for x in range(int(cc - a) - 1, int(cc + a) + 2):
            if abs(x - cc) <= half:
                capp.add((x, y))
    for x in range(int(cc - a) - 1, int(cc + a) + 2):
        d = abs(x - cc)
        if d <= a:
            if d > a * 0.55:
                capp.add((x, cb + 1))
            if d > a * 0.8:
                capp.add((x, cb + 2))
    ce = edges(capp)
    colbot = {}
    for (x, y) in capp:
        colbot[x] = max(colbot.get(x, -1), y)
    linep = set(ce) | {(x, y) for (x, y) in capp if y >= colbot[x] - 2}
    for p in capp:
        c.put(p[0], p[1], line if p in linep else base)
    coltop = {}
    for (x, y) in capp:
        coltop[x] = min(coltop.get(x, 999), y)
    for x in range(math.ceil(cc - a * 0.55), int(cc - a * 0.1) + 1):
        for k in (2, 3):
            p = (x, coltop[x] + k)
            if p in capp and p not in linep and all((x + s, p[1]) in capp for s in (-3, 3)):
                c.put(x, p[1], hl)
    # 하이라이트 옆 작은 반짝 (갓 꼭대기 오른쪽 1점)
    sx = int(cc + a * 0.05)
    c.put(sx, coltop[sx] + 2, hl)
    for (ox, oy, rr) in [(-0.55, 0.35, 4), (-0.15, 0.7, 3), (0.25, 0.4, 5), (0.62, 0.25, 3), (-0.35, 0.12, 2), (0.05, 0.15, 3)]:
        dcx, dcy = int(round(cc + ox * a)), int(round(cb - oy * b))
        for (x, y) in disc(dcx, dcy, rr):
            if (x, y) in capp and (x, y) not in linep:
                c.put(x, y, 'c2' if y > dcy else 'c1')
    # --- 주름 (갓 바로 아래 1줄)
    for x in range(x0, x1 + 1):
        if (x, cb + 1) not in capp:
            c.put(x, cb + 1, 'c3')


def fence(c, x0, n):
    xe = x0 + (n - 1) * 6 + 2
    for ry in (B - 9, B - 4):
        c.hline(x0, xe, ry, 'w3')
        c.hline(x0, xe, ry + 1, 'w4')
    for i in range(n):
        x = x0 + i * 6
        for y in range(B - 11, B + 1):
            c.put(x, y, 'w4')
            c.put(x + 1, y, 'w2')
            c.put(x + 2, y, 'w4')
        c.put(x + 1, B - 12, 'w4')
        c.put(x + 1, B - 11, 'w1')
        c.put(x + 1, B - 10, 'w1')


def sign(c, cx):
    for y in range(B - 21, B + 1):
        c.put(cx - 1, y, 'w4')
        c.put(cx, y, 'w3')
        c.put(cx + 1, y, 'w4')
    bx, by = cx - 14, B - 29
    for y in range(by, by + 14):
        c.hline(bx, bx + 28, y, 'w2')
    c.hline(bx, bx + 28, by, 'w4')
    c.hline(bx, bx + 28, by + 13, 'w4')
    for y in range(by, by + 14):
        c.put(bx, y, 'w4')
        c.put(bx + 28, y, 'w4')
    c.hline(bx + 1, bx + 27, by + 1, 'w1')
    c.hline(bx + 1, bx + 27, by + 12, 'w3')
    for y in range(by + 2, by + 12):
        c.put(bx + 1, y, 'w1')
        c.put(bx + 27, y, 'w3')
    for (x, y) in [(bx, by), (bx + 28, by), (bx, by + 13), (bx + 28, by + 13)]:
        c.px.pop((x, y), None)
    for (x, y) in [(bx + 3, by + 3), (bx + 25, by + 3), (bx + 3, by + 10), (bx + 25, by + 10)]:
        c.put(x, y, 'w4')                                       # 못
    for (r_, a_, b_) in [(3, 12, 16), (4, 11, 17), (5, 10, 18), (6, 10, 18)]:
        c.hline(bx + a_, bx + b_, by + r_, 'r2')
    c.put(bx + 12, by + 4, 'c1')
    c.put(bx + 16, by + 5, 'c1')
    for r_ in (7, 8, 9):
        c.hline(bx + 13, bx + 15, by + r_, 'c1')


FLOWERS = [20, 26, 250, 258, 300, 380, 386, 560, 640, 700, 706, 940, 990, 1150, 1156]


def flowers(c):
    for i, x in enumerate(FLOWERS):
        k = ['r2', 'y2', 'p2', 'white'][i % 4]
        c.put(x, B, 'g3')
        c.put(x, B - 1, 'g3')
        c.put(x, B - 4, k)
        c.put(x - 1, B - 3, k)
        c.put(x + 1, B - 3, k)
        c.put(x, B - 3, 'y4' if k == 'y2' else 'y2')
        c.put(x + 1, B - 1, 'g2')                   # 잎 한 장


def bush(c, cx, w, h, seed):
    pts = set()
    n = max(2, w // 9)
    for i in range(n):
        ox = int(-w / 2 + (i + 0.5) * w / n)
        rr = int(h * (0.75 if i % 2 else 0.95))
        for (x, y) in disc(cx + ox, B - rr + 2, rr):
            if y <= B:
                pts.add((x, y))
    e = edges(pts)
    for (x, y) in pts:
        if (x, y) in e:
            t = 'g4'
        else:
            d = (x - cx) / w + (y - (B - h)) / h
            t = 'g2' if d < 0.15 else 'g3'
            if d < -0.25:
                t = 'g1'
        c.put(x, y, t)


def village():
    c = Canvas(1200, 160)
    # 근경 나무와 덤불 (집 뒤) - 빈 구간에만
    tree(c, 335, B, 15, 3)
    tree(c, 975, B, 13, 5)
    bush(c, 680, 26, 9, 1)
    bush(c, 1118, 24, 8, 2)
    bush(c, 170, 22, 8, 3)
    house(c, 130, 'red', 80, 40, 44, 44)
    house(c, 440, 'orange', 66, 33, 36, 36)
    house(c, 790, 'blue', 76, 38, 42, 42)
    house(c, 1060, 'red', 58, 29, 32, 32)
    fence(c, 200, 8)
    fence(c, 520, 6)
    fence(c, 880, 9)
    sign(c, 600)
    flowers(c)
    return c


# ------------------------------------------------------------------ 7 지면
def ground():
    c = Canvas(1200, 54)
    for ti in range(75):
        tx = ti * 16
        rng = random.Random(7000 + ti % 5)          # 타일 5종 반복 (결정적)
        # 풀잎 (행 0-3): 3px 잎 2개 (끝 g1/g2), 1px 잎 3개 g2
        xs = rng.sample(range(16), 5)
        for j, dx in enumerate(xs):
            if j < 2:
                c.put(tx + dx, 3, 'g2')
                c.put(tx + dx, 2, 'g2')
                c.put(tx + dx, 1, 'g1' if j == 0 else 'g2')
            else:
                c.put(tx + dx, 3, 'g2')
        for dx in range(16):
            x = tx + dx
            c.put(x, 4, 'g1')
            for y in range(5, 10):
                c.put(x, y, 'g2')
            c.put(x, 10, 'g3')
            if (x // 3) % 2 == 0:
                c.put(x, 11, 'g3')
                c.put(x, 12, 'g4')
                d0 = 13
            else:
                c.put(x, 11, 'g4')
                d0 = 12
            for y in range(d0, 54):
                c.put(x, y, 'w3')
        for (dx, y) in rng.sample([(2, 6), (6, 7), (10, 6), (13, 8), (4, 8), (8, 5)], 3):   # 잔디 결
            c.put(tx + dx, y, 'g3')
        c.put(tx + rng.randrange(16), 5, 'g1')
        # 흙 (행 13-19 잔디 타일 아래 + dirt 20-35)
        for (dx, y) in [(5, 16), (12, 18)]:
            c.put(tx + dx, y, 'w4')
        for (dx, y) in [(3, 24), (11, 29), (6, 33), (13, 22)]:
            c.put(tx + dx, y, 'w4')
            c.put(tx + dx + 1, y, 'w4')
        for (dx, y) in [(8, 26), (2, 30)]:
            c.put(tx + dx, y, 'w2')
        # dirt-stone (36-51): 같은 반점 + 돌 (타일마다 위치 번갈아)
        for (dx, y) in [(3, 40), (11, 45), (6, 49), (13, 38)]:
            c.put(tx + dx, y, 'w4')
            c.put(tx + dx + 1, y, 'w4')
        for (dx, y) in [(8, 42), (2, 46)]:
            c.put(tx + dx, y, 'w2')
        srng = random.Random(9100 + ti)               # 돌 위치: 왼쪽 위 / 오른쪽 아래 번갈아, 칸 안에서 흔들기
        if ti % 2 == 0:
            sx, sy = tx + srng.randint(1, 4), 37 + srng.randint(0, 3)
        else:
            sx, sy = tx + srng.randint(7, 10), 42 + srng.randint(0, 4)
        if ti % 7 == 3:                               # 가끔 작은 조약돌만
            c.put(sx + 2, sy + 1, 'st2'); c.put(sx + 2, sy + 2, 'hb1'); c.put(sx + 3, sy + 1, 'st1')
            continue
        stone = [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3)]
        for (ox, oy) in stone:
            c.put(sx + ox, sy + oy, 'st2')
        for (ox, oy) in [(1, 0), (0, 1), (1, 1)]:
            c.put(sx + ox, sy + oy, 'st1')
        for (ox, oy) in [(1, 4), (2, 4), (3, 4)]:
            c.put(sx + ox, sy + oy, 'hb1')
    return c


LAYERS = [  # (file, fn, parallax, y, repeatX)
    ('sky', sky, 0.0, 0, True),
    ('clouds', clouds, 0.25, 18, True),
    ('mountains', mountains, 0.2, 110, True),
    ('hills', hills, 0.3, 142, True),
    ('trees', trees, 0.5, 104, True),
    ('village', village, 1.0, 60, False),
    ('ground', ground, 1.0, 216, False),
]


def build(out):
    os.makedirs(out, exist_ok=True)
    files = []
    for name, fn, *_ in LAYERS:
        p = os.path.join(out, name + '.png')
        fn().image().save(p, optimize=True)
        files.append(p)
    return files


def manifest():
    return {'scale': 2, 'layers': [{'src': f'assets/map/{n}.png', 'parallax': par, 'y': y, 'repeatX': rep}
                                   for (n, _, par, y, rep) in LAYERS]}
