"""(사이클 10) 머리카락 12종 + 모자 7종: SDF 형상을 반 칸 격자로 복셀화 (sdf.py).

좌표 = 머리 로컬 (사이클 8 단위): 머리 x +-14, y 0..25.6 (턱 0, 정수리 25.6), z +-12.8 (앞면 z 12.8, 둥근 모서리 반경 6).
머리카락 볼륨은 시안처럼 머리보다 크고 둥글다 (정수리 y 약 33, 옆 x +-17.5, 뒤 z -17.6).
가닥: 정수리 축(x=0, z=ZC) 둘레 각도로 가닥 번호를 매겨 가닥마다 색을 조금 바꾸고, 가닥 경계는 반 칸 파내 결을 만든다.
끝: 가닥마다 길이를 흔들고 가닥 가운데로 뾰족하게 (층진 끝).
"""
import functools
import numpy as np
import sdf
from sdf import Grid3, ellipsoid, rbox, capsule, tube, smin

ZC = -1.5                # 정수리 축 z
FACE_TOP = 17.4          # 얼굴 창(머리카락을 파내는 곳) 위끝 y
GROOVE = 0.7             # 가닥 경계 파냄 깊이


def tint(hexcol, k):
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float)
    c = c * (1 + k) if k < 0 else c + (255 - c) * k * 0.6
    c = np.clip(np.round(c), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


def _hash(i, s=0):
    i = (np.asarray(i, np.int64) * 2654435761 + s * 97531) & 0xFFFFFFFF
    i = (i ^ (i >> 15)) * 2246822519 & 0xFFFFFFFF
    return ((i ^ (i >> 13)) & 0xFFFF) / 65535.0


def _front_z(x, y):
    from model import head_front_z
    z = head_front_z(x, y)
    return 7.0 if z is None else z


class HairV:
    """머리카락 볼륨 키트. 라벨: 0 바탕, 1 밝은 가닥, 2 어두운 가닥, 3 결(홈), 4 아주 어두움(언더컷/안쪽), 5.. 강조색."""

    def __init__(self, col, seed=1, lo=(-24, -8, -25), hi=(24, 40, 22), n=24, accents=()):
        self.col, self.seed, self.n = col, seed, n
        self.g = g = Grid3(lo, hi)
        self.d = np.full(g.X.shape, 1e3)
        self.lab = np.zeros(g.X.shape, np.int32)
        th = np.arctan2(g.X, g.Z - ZC)
        u = (th / (2 * np.pi) + 0.5) * n                       # 가닥 좌표 (뒤 가운데 = 0 / n)
        self.sid = np.floor(u).astype(int) % n
        self.f = u - np.floor(u)                               # 가닥 안 위치 0..1
        hs = _hash(self.sid, seed)
        self.strand_lab = np.where(hs < 0.3, 1, np.where(hs > 0.75, 2, 0))
        self.cols = {0: col, 1: tint(col, 0.08), 2: tint(col, -0.07), 3: tint(col, -0.16), 4: tint(col, -0.35)}
        for i, c in enumerate(accents):
            self.cols[5 + i] = c

    # ---------------------------------------------------------------- 기본 연산
    def add(self, d, lab=None, k=0.0):
        """합집합. lab: None = 가닥 무늬, 정수, 또는 배열. k > 0 이면 부드러운 합."""
        inside = d <= 0
        self.d = smin(self.d, d, k) if k > 0 else np.minimum(self.d, d)
        if lab is None:
            lab = self.strand_lab
        self.lab = np.where(inside, lab, self.lab)

    def cut(self, d):
        self.d = np.maximum(self.d, -d)

    def keep(self, d):
        self.d = np.maximum(self.d, d)

    # ---------------------------------------------------------------- 볼륨
    def shell(self, d, bottom, tip=1.6, jit=0.9, groove=True, lab=None):
        """d: 볼륨 SDF. bottom: y 아래끝 (배열 가능). 가닥마다 길이 흔들고 가운데로 뾰족하게,
        가닥 단면을 둥글게(경계 쪽을 파냄: 결)."""
        g = self.g
        hs = _hash(self.sid, self.seed + 7)
        yb = bottom + (hs - 0.5) * 2 * jit - tip * (1 - np.abs(2 * self.f - 1))
        d = np.maximum(d, yb - g.Y)
        if groove:
            w = 1 - np.clip((g.Y - 27.0) / 5.0, 0, 1) * 0.7          # 정수리 쪽은 결을 약하게
            d = d + GROOVE * w * (1 - np.sin(np.pi * self.f)) ** 2
        inside = d <= 0
        self.d = np.minimum(self.d, d)
        L = self.strand_lab if lab is None else lab
        if groove:
            L = np.where(np.abs(self.f - 0.5) > 0.42, 3, L)
        self.lab = np.where(inside, L, self.lab)

    def helmet(self, top=33.2, hx=17.4, front=15.4, back=-17.6, side=8.0, rear=4.0, zs=4.0, zb=-6.0, r=10.0,
               puff=0.0, py=16.0, p=2.4, **kw):
        """둥근 바가지 볼륨 (위: 초타원체, 관자놀이 py 아래: 같은 단면 기둥). side: 얼굴 옆(z > zs) 아래끝,
        rear: 뒤(z < zb) 아래끝 (그 사이 선형). puff: 관자놀이 높이 가로 볼륨."""
        g = self.g
        hz = (front - back) / 2
        zc = (front + back) / 2
        d = sdf.dome(g, (0, py, zc), hx + puff, top - py, hz + puff * 0.5, p)
        t = np.clip((g.Z - zb) / max(zs - zb, 1e-3), 0, 1)
        self.shell(d, rear + (side - rear) * t, **kw)

    def curtain(self, x0, x1, y0, y1, z0, z1, r=3.0, **kw):
        """늘어진 머리 판 (긴 머리 뒤판, 옆 커튼). y0 = 아래끝 (가닥 끝 처리)."""
        g = self.g
        d = rbox(g, ((x0 + x1) / 2, (y0 + y1) / 2 - 3, (z0 + z1) / 2), ((x1 - x0) / 2, (y1 - y0) / 2 + 3, (z1 - z0) / 2), r)
        self.shell(d, y0, **kw)

    def face_window(self, top=FACE_TOP, hx=13.0, z0=3.5, r=2.5):
        """얼굴 앞을 파낸다 (|x| < hx, y < top, z > z0)."""
        g = self.g
        self.cut(rbox(g, (0, top - 20, z0 + 12), (hx, 20, 12), r))

    def neck_cut(self, y=1.5, hx=10.5, z1=-6.0):
        """목/어깨 자리 (턱 아래, 몸 앞쪽) 파내기."""
        self.cut(rbox(self.g, (0, y - 20, z1 + 15), (hx, 20, 15), 2.0))

    # ---------------------------------------------------------------- 앞머리
    def bangs(self, strands, top=26.0, ra=2.3, rb=0.5, sz=0.5, dz=1.0, labs=(0, 1, 0, 2)):
        """strands: [(x 위, x 끝, 끝 y), ...] 납작한 뾰족 캡슐 가닥. 머리 앞면을 따라 dz 만큼 띄운다."""
        for i, (xa, xb, yb) in enumerate(strands):
            za = _front_z(xa, min(top, 22.0)) + dz + 0.6
            zb_ = _front_z(xb, max(yb, 4.0)) + dz
            d = capsule(self.g, (xa, top, za), (xb, yb, zb_), ra, rb, sz)
            self.add(d, labs[i % len(labs)])

    def lock(self, pts, radii, lab=0, sz=1.0, k=0.0):
        self.add(tube(self.g, pts, radii, sz), lab, k)

    def blob(self, c, r, lab=0, k=0.0):
        self.add(ellipsoid(self.g, c, r), lab, k)

    # ---------------------------------------------------------------- 결과
    def boxes(self, noise=0.05):
        cols = {k: (v, dict(noise=noise)) for k, v in self.cols.items()}
        return sdf.build(self.g, self.d, self.lab, 0, cols, bone='head')


def _even(n, x0, x1):
    return np.linspace(x0, x1, n)


def _fringe(k, n=9, x0=-12.8, x1=12.8, yb=14.6, amp=1.2, lean=0.0, ra=2.3, **kw):
    """일자에 가까운 앞머리: n 가닥, 끝 높이 들쭉날쭉."""
    xs = _even(n, x0, x1)
    hs = _hash(np.arange(n), k.seed + 3)
    k.bangs([(x, x + lean + (h - 0.5) * 0.8, yb + (h - 0.5) * 2 * amp) for x, h in zip(xs, hs)], ra=ra, **kw)


# ================================================================== 머리카락 12종
def hair_ash_twoblock():
    """애쉬브라운 투블럭: 둥근 버섯 실루엣, 층진 앞머리, 볼 감싸는 옆머리, 짧게 친 뒷목."""
    k = HairV('#7A6862', 101)
    k.helmet(side=7.0, rear=5.0, puff=1.0, py=17.0)
    k.face_window()
    k.neck_cut()
    _fringe(k, 10, -13.2, 13.2, 14.2, amp=1.4, lean=0.6)
    k.add(rbox(k.g, (0, 3.6, -14.6), (11.0, 3.0, 1.6), 1.2), 4)                # 언더컷
    return k.boxes()


def hair_black_seethrough():
    """시스루뱅 긴 흑발: 얇은 앞머리 가닥(이마 비침), 얼굴 옆 직선 커튼, 허리까지 뒷머리, 헤어핀 2개."""
    k = HairV('#27232C', 202, lo=(-24, -30, -25), accents=('#FBF3EA', '#F6B6CA'))
    k.helmet(side=-2.0, rear=-2.0, puff=0.6, py=14.0, tip=2.0)
    k.curtain(-17.4, 17.4, -24.0, 8.0, -17.4, -6.8, r=4.0, tip=2.4, jit=1.0)          # 뒷머리 (허리)
    for sg in (1, -1):
        k.curtain(sg * 12.6 - 2.6, sg * 12.6 + 2.6, -16.0, 14.0, 2.0, 13.8, r=2.4, tip=2.4, jit=1.0)   # 얼굴 옆 직선
    k.face_window(hx=12.4)
    k.neck_cut(hx=10.0)
    xs = _even(9, -10.0, 10.0)
    k.bangs([(x, x * 1.04, 14.0 + 0.7 * ((i * 7) % 3) / 2) for i, x in enumerate(xs)], top=22.0, ra=1.1, rb=0.4, sz=0.6)
    for i, (y, lab) in enumerate(((21.0, 5), (19.2, 6))):                          # 헤어핀 (사선)
        k.lock([(7.6, y - 0.8, 15.0), (11.4, y + 1.0, 14.0)], [0.6, 0.6], lab)
    return k.boxes()


def hair_black_wolfcut():
    """검은 울프컷: 헝클어진 정수리, 뾰족한 앞머리, 바깥으로 뻗친 층층 옆머리, 길게 뻗친 뒷목."""
    k = HairV('#1F1C23', 303, n=28)
    k.helmet(side=7.5, rear=1.0, puff=1.2, py=15.0, tip=3.4, jit=2.2)
    for sg in (1, -1):                                                           # 바깥으로 뻗친 끝
        for i, (y, z) in enumerate(((9.0, -10.0), (8.0, -3.0), (10.0, 3.5), (2.0, -13.0))):
            k.lock([(sg * 15.8, y + 4.5, z), (sg * 18.6, y - 1.2, z + 0.5)], [2.0, 0.5], 2 if i % 2 else 0)
    for x in (-8.0, -3.0, 2.0, 7.0):                                             # 뒷목 뻗침
        k.lock([(x, 4.0, -15.6), (x * 1.15, -2.6, -17.0)], [2.0, 0.5], 0)
    for x, z in ((-3.0, 4.0), (2.5, 2.0), (0.0, -5.0)):                           # 정수리 헝클
        k.lock([(x, 31.5, z), (x * 1.5 + 1.0, 34.2, z - 2.0)], [2.0, 0.5], 1)
    k.face_window()
    k.neck_cut()
    xs = _even(10, -13.2, 13.2)
    hs = _hash(np.arange(10), 9)
    k.bangs([(x, x + (h - 0.5) * 2.0, 13.0 + (i % 2) * 1.6 + h) for i, (x, h) in enumerate(zip(xs, hs))], rb=0.35)
    return k.boxes()


def hair_pink_bridge_ponytail():
    """진갈색 + 핑크 브릿지 하이포니테일: 정수리 뒤에서 높이 묶어 위로 솟았다 등 뒤로 떨어지는 꼬리, 곱창 머리끈, 얼굴 옆 잔머리."""
    base, pink = '#4A332C', '#F288B6'
    k = HairV(base, 404, lo=(-24, -8, -36), hi=(24, 42, 22), accents=(pink, tint(pink, -0.12)))
    k.helmet(top=32.2, hx=16.8, back=-16.8, side=10.0, rear=8.0, r=9.0, tip=1.6, jit=0.8)
    for sg in (1, -1):
        k.lock([(sg * 13.6, 21.0, 12.4), (sg * 14.2, 10.0, 12.6), (sg * 13.4, 2.0, 11.6)], [1.5, 1.2, 0.4], 1, sz=0.8)   # 잔머리
        k.lock([(sg * 16.2, 22.0, 8.0), (sg * 16.6, 12.0, 8.6), (sg * 16.0, 5.0, 8.0)], [1.4, 1.2, 0.5], 5)            # 핑크 브릿지
    pts = [(0, 30.0, -12.5), (0.5, 33.6, -17.6), (1.5, 33.0, -22.6), (3.0, 28.6, -26.0), (4.6, 22.0, -27.0),
           (6.0, 15.0, -26.4), (7.0, 8.5, -25.0), (7.6, 2.5, -23.4), (8.0, -2.5, -21.6)]
    rad = [4.2, 5.0, 5.4, 5.3, 5.0, 4.5, 3.8, 2.6, 0.7]
    k.lock(pts, rad, 0, k=1.0)
    for sg in (1, -1):                                                           # 꼬리 핑크 결
        k.lock([(p[0] + sg * r * 0.72, p[1], p[2] + 0.4) for p, r in zip(pts[1:8], rad[1:8])],
               [0.9] * 7, 5)
    k.blob((0, 29.6, -11.6), (3.4, 2.4, 3.0), 6)                                   # 곱창 머리끈
    k.face_window()
    k.neck_cut()
    _fringe(k, 9, -12.6, 12.6, 15.0, amp=0.8, top=23.0)
    return k.boxes()


def hair_black_short():
    """검은 짧은 머리: 곱슬 덩어리 볼륨, 이마를 덮는 짧은 앞머리, 볼 옆 짧은 옆머리."""
    k = HairV('#30231F', 7, n=26)
    k.helmet(side=9.5, rear=5.0, puff=1.0, tip=1.6, jit=1.2)
    for i, (x, y, z) in enumerate(((-12, 28, 4), (-4, 32, 6), (5, 31.5, 5), (12, 27, 2), (-15, 20, -6), (15, 20, -7),
                                   (-8, 30, -10), (8, 30, -11), (0, 24, -16), (-12, 14, -12), (12, 14, -13))):
        k.blob((x, y, z), (4.0, 3.4, 4.0), 1 if i % 3 == 0 else 0, k=1.2)
    k.face_window()
    k.neck_cut()
    _fringe(k, 9, -13.2, 13.2, 15.4, amp=0.8, ra=2.5)
    return k.boxes()


def hair_brown_short():
    """밤색 짧은 머리: 옆가르마, 한쪽으로 쓸린 앞머리, 정수리 더듬이."""
    k = HairV('#7A4A2E', 21)
    k.helmet(side=8.6, rear=5.0, puff=0.8, tip=2.0)
    k.face_window()
    k.neck_cut()
    xs = _even(9, -13.2, 13.4)
    k.bangs([(x, x - 2.2, 13.6 + 0.45 * i) for i, x in enumerate(xs)], top=27.0)
    k.lock([(1.6, 32.0, 3.0), (2.4, 35.2, 4.0), (4.0, 36.0, 6.2)], [1.0, 0.9, 0.4], 1)   # 더듬이
    return k.boxes()


def hair_blonde_spiky():
    """금발 뻗친 머리: 위/옆/뒤로 뻗은 뾰족한 덩어리, 아래로 뾰족한 앞머리."""
    k = HairV('#F2C14E', 33, n=24)
    k.helmet(top=31.6, hx=16.6, side=10.0, rear=5.0, tip=3.0, jit=1.4)
    spikes = [((-5, 30, 5), (-8, 35.5, 7)), ((4.5, 30.5, 5), (8, 35.5, 7.5)), ((0, 31, -3), (1, 36.5, -6)),
              ((-9, 29, -7), (-13, 33, -11)), ((9, 29, -6), (13.5, 33, -10)), ((-15, 23, 2), (-20.5, 25, 3)),
              ((15, 23, 1), (20.5, 25, 2)), ((-6, 20, -15), (-8, 19, -20.5)), ((6, 20, -15), (8, 19, -20.5)),
              ((0, 12, -15), (0, 8, -19.5)), ((-14, 14, -9), (-19.5, 11, -12)), ((14, 14, -9), (19.5, 11, -12))]
    for i, (a, b) in enumerate(spikes):
        k.lock([a, b], [3.6, 0.6], 1 if i % 2 else 0, k=1.0)
    k.face_window()
    k.neck_cut()
    xs = _even(6, -12.4, 12.4)
    k.bangs([(x, x * 0.9, 14.6 + (i % 2) * 1.0) for i, x in enumerate(xs)], ra=3.0, rb=0.35)
    return k.boxes()


def hair_pink_long():
    """분홍 긴 머리: 일자 앞머리, 볼을 감싸고 가슴까지 오는 앞 가닥, 허리까지 오는 뒷머리(끝 안쪽 말림)."""
    k = HairV('#F49AC1', 41, lo=(-24, -28, -25))
    k.helmet(side=-2.0, rear=-2.0, puff=1.0, py=14.0, tip=2.0)
    k.curtain(-17.6, 17.6, -20.0, 8.0, -17.6, -6.8, r=4.0, tip=2.0, jit=0.8)
    for sg in (1, -1):
        k.curtain(sg * 13.2 - 2.4, sg * 13.2 + 2.4, -17.0, 14.0, 4.0, 14.0, r=2.4, tip=1.4, jit=0.6)    # 앞 가닥 (가슴까지)
        k.lock([(sg * 12.6, -15.0, 11.5), (sg * 11.2, -17.4, 12.6)], [2.2, 1.4], 2)                     # 끝 말림
    k.lock([(-14.0, -19.0, -13.4), (14.0, -19.0, -13.4)], [2.0, 2.0], 2)                                   # 뒤 끝 말림
    k.face_window(hx=12.6)
    k.neck_cut()
    _fringe(k, 9, -12.4, 12.4, 14.6, amp=0.5, ra=2.2, rb=0.8)
    return k.boxes()


def hair_sky_bob():
    """하늘색 단발: 턱선 길이, 안으로 말린 둥근 실루엣, 일자 앞머리."""
    k = HairV('#8FCBF0', 55)
    k.helmet(side=2.0, rear=1.0, puff=1.6, py=12.0, tip=1.2, jit=0.5)
    k.add(rbox(k.g, (0, 2.0, -3.0), (17.6, 1.8, 15.0), 1.8), 2, k=1.0)            # 아래 안쪽 말림
    k.face_window(hx=12.8)
    k.neck_cut(y=1.0, hx=11.0)
    _fringe(k, 9, -12.6, 12.6, 14.8, amp=0.4, ra=2.2, rb=0.9)
    return k.boxes()


def hair_tan_ponytail():
    """갈색 포니테일: 뒤통수 가운데에서 묶어 아래로 흐르는 꼬리, 빨간 머리끈, 옆 가르마 앞머리."""
    k = HairV('#8C5A3C', 63, lo=(-24, -14, -26), accents=('#E8483E',))
    k.helmet(top=32.4, hx=16.8, back=-16.8, side=10.0, rear=8.0, r=9.0, tip=1.6, jit=0.6)
    for sg in (1, -1):
        k.lock([(sg * 13.8, 20.0, 12.6), (sg * 14.0, 8.0, 12.4), (sg * 13.2, 2.0, 11.4)], [1.4, 1.1, 0.4], 1, sz=0.8)
    k.lock([(0, 19.0, -19.0), (0, 13.0, -21.4), (0, 6.0, -21.0), (0.4, -1.0, -19.6), (0.8, -7.4, -17.8)],
           [3.2, 3.9, 3.6, 2.6, 0.6], 0, k=1.0)
    k.blob((0, 19.6, -17.0), (2.6, 2.6, 1.8), 5)
    k.face_window()
    k.neck_cut()
    xs = _even(9, -12.8, 12.8)
    k.bangs([(x, x + 1.2, 16.6 - 0.3 * i + (i % 2) * 0.6) for i, x in enumerate(xs)], top=24.0)
    return k.boxes()


def hair_black_twintail():
    """검은 양갈래: 귀 위에서 묶은 두 꼬리가 바깥으로 뻗었다 어깨 아래로, 빨간 머리끈, 일자 앞머리."""
    k = HairV('#2C2533', 77, lo=(-27, -12, -25), hi=(27, 40, 22), accents=('#E8483E',))
    k.helmet(top=32.6, hx=16.8, side=8.0, rear=4.0, tip=1.6, jit=0.6)
    for sg in (1, -1):
        k.blob((sg * 17.4, 19.0, -3.0), (1.6, 2.2, 2.2), 5)
        k.lock([(sg * 19.4, 19.0, -3.2), (sg * 22.0, 14.0, -3.2), (sg * 22.4, 7.0, -3.0), (sg * 21.4, 1.0, -2.6),
                (sg * 19.4, -5.0, -2.0), (sg * 18.6, -8.0, -1.8)], [2.6, 3.2, 3.1, 2.7, 1.6, 0.5], 0, k=0.8)
    k.face_window()
    k.neck_cut()
    _fringe(k, 9, -12.8, 12.8, 14.8, amp=0.5, ra=2.2, rb=0.8)
    return k.boxes()


def hair_mint_curly():
    """민트 곱슬: 머리 전체를 덮는 크고 둥근 곱슬 볼륨 (작은 공 덩어리 많이)."""
    k = HairV('#7FD6B8', 91)
    k.helmet(top=31.8, hx=16.6, side=6.0, rear=2.0, tip=0.8, jit=0.4, groove=False)
    rng = np.random.default_rng(91)
    for i in range(70):
        th = rng.uniform(-np.pi * 0.62, np.pi * 0.62) + np.pi        # 뒤/옆/위 (얼굴 앞 제외)
        ph = rng.uniform(-0.25, 1.15)
        rr = 17.0
        x = rr * np.sin(th) * np.cos(ph * 0.9)
        z = ZC + rr * np.cos(th) * np.cos(ph * 0.9)
        y = 15.0 + 14.0 * np.sin(ph)
        if y > 30.0:
            continue
        k.blob((x, y, z), (2.8, 2.6, 2.8), (0, 1, 2)[i % 3])
    for x in _even(6, -12.0, 12.0):                                              # 앞 곱슬 볼륨
        k.blob((x, 27.0, 13.4), (3.0, 2.5, 2.4), 1)
    k.face_window()
    k.neck_cut()
    _fringe(k, 8, -12.8, 12.8, 15.4, amp=0.8, ra=2.4, rb=1.0)
    return k.boxes()


HAIRS = {'ash-twoblock': hair_ash_twoblock, 'black-seethrough': hair_black_seethrough,
         'black-wolfcut': hair_black_wolfcut, 'pink-bridge-ponytail': hair_pink_bridge_ponytail,
         'black-short': hair_black_short, 'brown-short': hair_brown_short, 'blonde-spiky': hair_blonde_spiky,
         'pink-long': hair_pink_long, 'sky-bob': hair_sky_bob, 'tan-ponytail': hair_tan_ponytail,
         'black-twintail': hair_black_twintail, 'mint-curly': hair_mint_curly}


# ================================================================== 모자 7종
class HatV(HairV):
    def __init__(self, col, lo=(-26, 12, -26), hi=(26, 42, 30), accents=()):
        g = Grid3(lo, hi)
        self.g, self.col, self.seed, self.n = g, col, 0, 1
        self.d = np.full(g.X.shape, 1e3)
        self.lab = np.zeros(g.X.shape, np.int32)
        self.cols = {0: col, 1: tint(col, 0.06), 2: tint(col, -0.08), 3: tint(col, -0.18), 4: tint(col, -0.3)}
        for i, c in enumerate(accents):
            self.cols[5 + i] = c

    def boxes(self, noise=0.03):
        return super().boxes(noise)

    def crown(self, c, h, r, lab=0):
        self.add(rbox(self.g, c, h, r), lab)

    def brim(self, y, rin, rout, droop, th=0.7, zc=-0.6, lab=0, front=None):
        """챙: 반지름 rin..rout, 바깥으로 갈수록 droop 만큼 내려감 (얇은 원뿔 판)."""
        g = self.g
        rad = np.sqrt(g.X ** 2 + (g.Z - zc) ** 2)
        t = np.clip((rad - rin) / (rout - rin), 0, 1)
        yy = y - droop * t ** 1.3
        d = np.maximum(np.abs(g.Y - yy) - th, np.maximum(rad - rout, rin - 1.5 - rad))
        self.add(d, lab)


def _surface_mask(k, d, center, r):
    """d 표면 근처, center 에서 r 안쪽 (점 무늬)."""
    g = k.g
    return (np.sqrt((g.X - center[0]) ** 2 + (g.Y - center[1]) ** 2 + (g.Z - center[2]) ** 2) < r)


def hat_bucket_white():
    """흰 버킷햇: 둥근 크라운, 아래로 기운 챙, 띠, 라벤더 하트 자수."""
    k = HatV('#F8F6F2', accents=('#BCA8EC', '#D4C6F4'))
    k.crown((0, 27.8, -0.6), (18.6, 7.6, 18.4), 7.0)
    k.add(rbox(k.g, (0, 21.0, -0.6), (18.9, 1.0, 18.7), 2.0), 2)                     # 띠
    k.brim(20.4, 16.0, 23.8, 4.0, th=0.8, zc=-0.6, lab=1)
    cx, cy, cz = -7.0, 26.0, 18.2                                                  # 하트 (앞 왼쪽)
    g = k.g
    hx, hy = (g.X - cx) / 1.9, (g.Y - cy) / 1.9
    heart = (hx ** 2 + (hy - np.sqrt(np.abs(hx)) * 0.9) ** 2 < 1.0) & (g.Z > cz - 1.6)
    k.lab = np.where(heart & (k.d <= 0), 5, k.lab)
    return k.boxes()


def hat_cap_black():
    """검정 캡: 둥근 크라운, 긴 챙, 단추, 앞 크림 자수 (글자 없는 둥근 마크)."""
    k = HatV('#34303D', accents=('#EDE3CF',))
    k.crown((0, 27.0, -0.8), (18.8, 8.4, 18.6), 8.5)
    g = k.g
    bill = np.maximum(np.abs(g.Y - (20.4 - 0.18 * np.clip(g.Z - 14, 0, None))) - 0.7,
                      ellipsoid(g, (0, 20.4, 18.0), (14.5, 30.0, 10.0)))
    bill = np.maximum(bill, 12.0 - g.Z)
    k.add(bill, 2)
    k.blob((0, 35.4, -0.8), (1.4, 0.8, 1.4), 1)                                     # 단추
    seam = (np.abs(g.X) < 0.3) & (g.Z > 0)
    k.lab = np.where(seam & (k.d <= 0) & (g.Y > 22), 3, k.lab)
    mark = (np.sqrt((g.X + 6.0) ** 2 + (g.Y - 26.0) ** 2) < 1.8) & (g.Z > 10)
    k.lab = np.where(mark & (k.d <= 0), 5, k.lab)
    return k.boxes()


def hat_cap_white():
    """흰 야구모자: 둥근 크라운, 챙, 빨간 단추와 빨간 둥근 앞 마크."""
    k = HatV('#F6F3EE', accents=('#E8483E', '#FFFFFF'))
    k.crown((0, 27.2, -0.6), (18.6, 8.2, 18.4), 8.5)
    g = k.g
    bill = np.maximum(np.abs(g.Y - (20.6 - 0.15 * np.clip(g.Z - 14, 0, None))) - 0.7,
                      ellipsoid(g, (0, 20.6, 18.0), (14.0, 30.0, 9.5)))
    bill = np.maximum(bill, 12.0 - g.Z)
    k.add(bill, 2)
    k.blob((0, 35.2, -0.6), (1.4, 0.8, 1.4), 5)
    mark = (((g.X - 0.0) / 2.8) ** 2 + ((g.Y - 26.4) / 2.0) ** 2 < 1) & (g.Z > 10)
    k.lab = np.where(mark & (k.d <= 0), 5, k.lab)
    return k.boxes()


def hat_mushroom_red():
    """빨간 버섯 모자: 둥근 갓 (크림 점무늬), 갓 아래 크림 주름 테."""
    k = HatV('#E8483E', lo=(-27, 12, -27), hi=(27, 44, 27), accents=('#FFF6E4', '#F2DDB8'))
    g = k.g
    cap = ellipsoid(g, (0, 22.0, -0.6), (22.0, 15.0, 21.6))
    cap = np.maximum(cap, 19.6 - g.Y)
    k.add(cap, 0)
    k.add(rbox(g, (0, 19.8, -0.6), (18.6, 0.9, 18.4), 0.8), 6)                      # 갓 아래 주름 테
    dots = [(0, 1, 0.1, 4.2), (-0.55, 0.62, 0.55, 3.2), (0.6, 0.6, -0.55, 3.0), (0.75, 0.45, 0.48, 2.8),
            (-0.72, 0.48, -0.5, 3.0), (-0.95, 0.15, 0.25, 2.6), (0.95, 0.18, -0.1, 2.6), (0.1, 0.35, 0.94, 3.0),
            (-0.2, 0.38, -0.92, 2.8), (0.45, 0.85, 0.3, 2.2)]
    for dx, dy, dz, r in dots:
        v = np.array([dx, dy, dz]); v = v / np.linalg.norm(v)
        p = (v[0] * 22.0, 22.0 + v[1] * 15.0, -0.6 + v[2] * 21.6)
        m = _surface_mask(k, cap, p, r)
        k.lab = np.where(m & (k.d <= 0), 5, k.lab)
    return k.boxes()


def hat_explorer_brown():
    """갈색 탐험가 모자: 둥근 크라운 + 가운데 홈, 짙은 띠, 넓은 챙."""
    tan = '#C9A47A'
    k = HatV(tan, accents=('#5E3620',))
    k.crown((0, 27.4, -0.6), (17.8, 7.2, 17.6), 6.0)
    g = k.g
    k.cut(ellipsoid(g, (0, 35.6, -0.6), (3.0, 2.0, 12.0)))                          # 크라운 홈
    k.add(rbox(g, (0, 22.0, -0.6), (18.1, 1.4, 17.9), 1.2), 5)                       # 띠
    k.brim(20.6, 16.0, 24.4, 2.0, th=0.75, zc=-0.6, lab=2)
    return k.boxes()


def hat_beanie_yellow():
    """노란 비니: 둥근 니트 몸통(세로 골), 접은 단, 크림 방울."""
    y = '#F7C948'
    k = HatV(y, accents=('#FFF6E4',))
    g = k.g
    k.crown((0, 26.0, -0.8), (18.4, 9.0, 18.2), 8.0)
    rib = (np.floor((np.arctan2(g.X, g.Z + 0.8) / (2 * np.pi) + 0.5) * 36) % 2 == 0)
    k.lab = np.where((k.d <= 0) & rib, 2, k.lab)
    k.add(rbox(g, (0, 19.6, -0.8), (18.9, 2.2, 18.7), 1.8), np.where(rib, 3, 2))       # 접은 단
    k.blob((0, 36.0, -0.8), (3.2, 2.8, 3.2), 5)
    return k.boxes()


def hat_ribbon_pink():
    """분홍 리본: 머리 옆 위에 큰 리본 (양 날개 + 매듭 + 늘어진 끈)."""
    p = '#F58AB4'
    k = HatV(p, lo=(-6, 14, -6), hi=(24, 38, 22))
    c = np.array([9.0, 29.0, 7.5])
    k.blob(tuple(c), (1.8, 1.8, 1.6), 2)
    for sg in (1, -1):
        k.lock([tuple(c + [sg * 1.0, 0.2, 0]), tuple(c + [sg * 4.6, 2.0, -0.6])], [1.5, 3.0], 0, sz=0.55, k=0.6)
        k.lock([tuple(c + [sg * 0.8, -0.8, 0.4]), tuple(c + [sg * 2.6, -5.2, 0.8])], [1.1, 0.8], 1, sz=0.5)
    return k.boxes()


HATS = {'bucket-white': hat_bucket_white, 'cap-black': hat_cap_black, 'cap-white': hat_cap_white,
        'mushroom-red': hat_mushroom_red, 'explorer-brown': hat_explorer_brown, 'beanie-yellow': hat_beanie_yellow,
        'ribbon-pink': hat_ribbon_pink}


def cached(fn):
    @functools.lru_cache(maxsize=None)
    def _c():
        return tuple(fn())

    return lambda: [dict(d) for d in _c()]


HAIRS = {k: cached(v) for k, v in HAIRS.items()}
HATS = {k: cached(v) for k, v in HATS.items()}
