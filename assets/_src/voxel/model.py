"""버섯마을 복셀 캐릭터 모델 (사이클 7: 트렌디 비율). 단위 = 복셀 1칸 (시트 1.9px, 월드 약 1.27단위).

사이클 7 변경: Canva 시안 4종을 따라 마네킹을 다시 잡았다.
  - 비율: 머리(머리카락 포함)가 키의 약 41%, 다리(가랑이~발바닥) 약 31%. 몸통을 좁히고 다리를 길게.
  - 해상도: 복셀 1칸 2.75px -> 1.9px. 머리 28x25.6x25.6칸(사이클 5 머리의 HK=1.28배).
  - 사이클 5 모자는 legacy_v5.py 형상을 HK배로 키워 새 머리에 씌운다. 머리카락 8종, 옷/신발/얼굴은 새 몸에 맞춰 다시 만들었다.

캐릭터 로컬 좌표: +x = 캐릭터의 왼쪽(정면에서 화면 오른쪽), +y 위, +z 앞, 발바닥 y=0.
뼈: root, torso, head, arm+/arm-, leg+/leg-(허벅지), shin+/shin-(정강이, 무릎 아래).
torso 뼈 상자의 y 는 발바닥 기준 절대 높이(서 있을 때). 머리 로컬 y 0..25.6 (턱 0), 앞면 z=12.8.
파츠 함수는 dict 목록(bone, c, h, col, ...)을 돌려주고 assemble()이 포즈를 적용해 Box 목록을 만든다.
dict 의 rot=(rx, ry, rz) 는 뼈 안에서 상자를 더 돌린다(도, 회전 순서 z @ y @ x).
"""
import numpy as np
from vox import Box, rot_x, rot_y, rot_z
import legacy_v5 as V5

# ------------------------------------------------------------------ 치수 (마네킹)
HK = 1.28                         # 사이클 5 머리 -> 사이클 7 머리 배율
HEAD_PIVOT = (0, 42.0, 0)
HEAD_H = (14.0, 12.8, 12.8)       # 머리 28 x 25.6 x 25.6, 머리 로컬 y 0..25.6
SHOULDER = (9.1, 38.2, 0)
HIP = (3.9, 24.5, 0)
KNEE = (0, -14.0, 0)              # 허벅지 뼈 기준 무릎
LEGX = 3.0                        # 사이클 7: 허벅지를 늘린 만큼 몸통 뼈 전체를 올림 (몸통 로컬 y 는 그대로)
TORSO_SY = 1.17                   # 사이클 7: 몸통 뼈 상자를 엉덩이 높이 기준으로 세로 1.17배 (어깨/목/머리도 같이 올라감)
SOLE = (0, -13.5, 1.0)            # 정강이 뼈 기준 발바닥 중앙
FOOT_DZ = (-3.8, 7.0)             # 발바닥 뒤꿈치/앞코 z (접지 계산)
SKIRT_Y = 25.4                    # 치마 허리 높이 (숙이기 치마 경첩)

LABELS = {
    'skin': [('light', '밝은 피부'), ('medium', '보통 피부'), ('dark', '진한 피부')],
    'face': [('basic', '기본'), ('smile', '웃음'), ('wink', '윙크'), ('sleepy', '졸린 눈')],
    'hair': [('ash-twoblock', '애쉬브라운 투블럭'), ('black-seethrough', '시스루뱅 긴 흑발'),
             ('black-wolfcut', '검은 울프컷'), ('pink-bridge-ponytail', '핑크 브릿지 포니테일'),
             ('black-short', '검은 짧은 머리'), ('brown-short', '밤색 짧은 머리'), ('blonde-spiky', '금발 뻗친 머리'),
             ('pink-long', '분홍 긴 머리'), ('sky-bob', '하늘색 단발'), ('tan-ponytail', '갈색 포니테일'),
             ('black-twintail', '검은 양갈래'), ('mint-curly', '민트 곱슬')],
    'top': [('hoodie-lavender', '라벤더 오버핏 후드'), ('cardigan-cream', '크림 가디건과 숄더백'),
            ('varsity-navy', '네이비 바시티 재킷'), ('puffer-mint', '민트 크롭 패딩과 크로스백'),
            ('hoodie-black', '검은 후드티'), ('hoodie-white', '흰 후드티'), ('blouse-white', '흰 블라우스'),
            ('overalls-green', '초록 멜빵'), ('tee-stripe-red', '빨간 줄무늬 티'), ('cape-blue', '파란 망토 셔츠')],
    'bottom': [('denim-wide', '연청 와이드 데님'), ('skirt-check', '체크 플리츠 스커트'),
               ('cargo-black', '검정 카고 조거'), ('cargo-beige', '베이지 와이드 카고'),
               ('pants-navy', '남색 바지'), ('pants-black', '검은 바지'), ('skirt-pink', '분홍 치마'),
               ('shorts-brown', '갈색 반바지'), ('jeans-blue', '청바지')],
    'shoes': [('chunky-white', '흰 청키 스니커즈'), ('loafer-socks', '로퍼와 니삭스'), ('hightop-black', '검정 하이탑'),
              ('sneakers-white', '흰 운동화'), ('maryjane-red', '빨간 메리제인'), ('boots-brown', '갈색 부츠'),
              ('sneakers-black', '검은 운동화')],
    'hat': [('none', '없음'), ('bucket-white', '흰 버킷햇'), ('cap-black', '검정 무지 캡'),
            ('cap-white', '흰 야구모자'), ('mushroom-red', '빨간 버섯 모자'),
            ('explorer-brown', '갈색 탐험가 모자'), ('beanie-yellow', '노란 비니'), ('ribbon-pink', '분홍 리본')],
}
PRESETS = [
    ('라벤더 후드', dict(skin='light', hair='ash-twoblock', face='basic', top='hoodie-lavender', bottom='denim-wide', shoes='chunky-white', hat='bucket-white')),
    ('가디건 걸', dict(skin='light', hair='black-seethrough', face='basic', top='cardigan-cream', bottom='skirt-check', shoes='loafer-socks', hat='none')),
    ('바시티 캡', dict(skin='light', hair='black-wolfcut', face='basic', top='varsity-navy', bottom='cargo-black', shoes='hightop-black', hat='cap-black')),
    ('민트 패딩', dict(skin='light', hair='pink-bridge-ponytail', face='basic', top='puffer-mint', bottom='cargo-beige', shoes='chunky-white', hat='none')),
    ('분홍 소녀', dict(skin='light', hair='pink-long', face='basic', top='blouse-white', bottom='skirt-pink', shoes='maryjane-red', hat='none')),
    ('버섯 꼬마', dict(skin='light', hair='blonde-spiky', face='basic', top='overalls-green', bottom='jeans-blue', shoes='boots-brown', hat='mushroom-red')),
]
CATS = ['skin', 'face', 'hair', 'top', 'bottom', 'shoes', 'hat']

SKINS = {'light': '#FAD6C0', 'medium': '#E2A982', 'dark': '#A3684A'}
SOFT = 0.8       # 몸/옷 베벨 폭
HAIRB = 0.5      # 머리카락 베벨


def P(bone, c, h, col, **kw):
    return dict(bone=bone, c=c, h=h, col=col, **kw)


def R(bone, c, h, col, r=0.6, **kw):
    """모서리를 한 칸 깎은 상자 (3개 상자 십자 결합) - 각진 느낌 완화."""
    hx, hy, hz = h
    r = min(r, 0.8 * min(h))          # 반폭보다 큰 깎기는 상자를 뒤집으므로 제한
    kw.setdefault('bevel', SOFT)
    return [P(bone, c, (hx, hy - r, hz - r), col, **kw),
            P(bone, c, (hx - r, hy, hz - r), col, **kw),
            P(bone, c, (hx - r, hy - r, hz), col, **kw)]


def tint(hexcol, k):
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float)
    c = c * (1 + k) if k < 0 else c + (255 - c) * k * 0.6
    c = np.clip(np.round(c), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


def _rng(seed):
    return np.random.default_rng(seed)


DEC = dict(decal=True, bevel=0, noise=0.0)


def decal(bone, c, h, col, **kw):
    d = dict(DEC); d.update(kw)
    return P(bone, c, h, col, **d)


def scaled(defs, k=HK):
    """사이클 5 머리 로컬 형상을 k배 (위치/크기/베벨). k 는 숫자 또는 (kx, ky, kz)."""
    k = np.broadcast_to(np.asarray(k, float), (3,))
    out = []
    for d in defs:
        e = dict(d)
        e['c'] = tuple(np.asarray(d['c'], float) * k)
        e['h'] = tuple(np.asarray(d['h'], float) * k)
        if 'bevel' in d and d['bevel']:
            e['bevel'] = d['bevel'] * 1.1
        out.append(e)
    return out


# ================================================================== skin (마네킹)
def skin(tone):
    s = SKINS[tone]
    k = dict(noise=0.012)
    out = [P('head', (0, 12.8, 0), HEAD_H, s, bevel=0.6, **k),
           P('torso', (0, 41.0, 0), (2.4, 1.8, 2.4), s, **k)]                  # 목
    out += R('torso', (0, 34.6, 0), (7.0, 5.0, 4.0), s, 0.8, **k)              # 가슴 29.6..39.6
    out += R('torso', (0, 28.0, 0), (6.4, 2.0, 3.7), s, 0.6, **k)              # 허리
    out += R('torso', (0, 24.4, 0), (6.8, 2.4, 3.9), s, 0.6, **k)              # 골반 22..26.8
    for sg in (1, -1):
        a, l, sh = 'arm%+d' % sg, 'leg%+d' % sg, 'shin%+d' % sg
        out += R(a, (0, -3.8, 0), (2.1, 4.2, 2.1), s, 0.5, **k)
        out += R(a, (0, -10.0, 0.1), (1.95, 2.6, 1.95), s, 0.5, **k)
        out += R(a, (0, -14.6, 0.3), (2.25, 2.2, 2.3), s, 0.8, **k)             # 손
        out += R(l, (0, -6.9, 0), (2.9, 7.4, 2.9), s, 0.5, **k)
        out += R(sh, (0, -5.0, 0), (2.5, 5.6, 2.5), s, 0.5, **k)
        out += R(sh, (0, -12.0, 1.3), (2.8, 1.5, 4.2), s, 0.5, **k)            # 발
    return out


# ================================================================== face (머리 앞면 데칼)
FZ = 12.8
D = dict(decal=True, bevel=0, noise=0.0)
EYE_X = 6.5
EYE_Y = 10.2
LASH = '#1E1216'


def _eye_open(ex, sg):
    """큰 세로 눈 (5.8 x 7.6칸), 굵은 위 속눈썹 라인, 갈색 그라데이션 홍채, 큰 하이라이트 + 반사점 (발광)."""
    y, z = EYE_Y, FZ
    dk = '#2A1A1F'
    return [
        P('head', (ex, y - 0.2, z + 0.03), (3.1, 3.4, 0.03), dk, **D),
        P('head', (ex, y - 0.2, z + 0.03), (2.5, 3.9, 0.03), dk, **D),
        P('head', (ex, y + 3.45, z + 0.05), (3.45, 0.6, 0.03), LASH, **D),             # 위 속눈썹 라인
        P('head', (ex + sg * 3.55, y + 3.85, z + 0.05), (0.8, 0.55, 0.03), LASH, **D),  # 바깥 꼬리
        P('head', (ex, y - 1.0, z + 0.06), (2.35, 2.7, 0.03), '#3A2220', **D),          # 홍채
        P('head', (ex, y - 2.5, z + 0.08), (1.7, 1.1, 0.03), '#6B402E', **D),           # 아래 호박색
        P('head', (ex, y - 3.3, z + 0.10), (1.1, 0.45, 0.03), '#A8744E', **D),          # 아래 반사
        P('head', (ex - 0.95, y + 1.5, z + 0.12), (1.25, 1.35, 0.03), '#FFFFFF', emit=0.9, **D),   # 큰 하이라이트
        P('head', (ex + 1.2, y - 1.6, z + 0.12), (0.6, 0.6, 0.03), '#FFFFFF', emit=0.8, **D),      # 작은 반사점
        P('head', (ex - 1.55, y - 0.7, z + 0.12), (0.3, 0.3, 0.03), '#FFF4F0', emit=0.6, **D),     # 반짝
    ]


def _eye_arc(ex):
    """^ 모양 감은 눈 (굵게)."""
    y = EYE_Y - 0.2
    c = '#2A1A20'
    return [P('head', (ex - 2.4, y - 1.1, FZ + 0.03), (0.9, 0.6, 0.03), c, **D),
            P('head', (ex - 1.2, y + 0.0, FZ + 0.03), (0.75, 0.6, 0.03), c, **D),
            P('head', (ex, y + 0.55, FZ + 0.03), (0.9, 0.6, 0.03), c, **D),
            P('head', (ex + 1.2, y + 0.0, FZ + 0.03), (0.75, 0.6, 0.03), c, **D),
            P('head', (ex + 2.4, y - 1.1, FZ + 0.03), (0.9, 0.6, 0.03), c, **D)]


def _blush(big=False):
    w = 2.4 if big else 2.1
    out = []
    for sg in (1, -1):
        out += [P('head', (sg * 8.9, 5.3, FZ + 0.03), (w, 0.95, 0.03), '#F59AA6', emit=0.15, **D),
                P('head', (sg * 8.9, 5.3, FZ + 0.05), (w - 0.9, 0.5, 0.03), '#F8B4BC', emit=0.2, **D)]
    return out


def face(kind):
    out = []
    if kind == 'basic':
        for sg in (1, -1):
            out += _eye_open(sg * EYE_X, sg)
        out += _blush()
        out.append(P('head', (0, 4.0, FZ + 0.03), (0.85, 0.38, 0.03), '#A8475A', **D))
    elif kind == 'smile':
        for sg in (1, -1):
            out += _eye_arc(sg * EYE_X)
        out += _blush(True)
        out += [P('head', (0, 4.1, FZ + 0.03), (1.6, 0.95, 0.03), '#8E3346', **D),
                P('head', (0, 3.6, FZ + 0.06), (1.0, 0.45, 0.03), '#F07A8A', **D)]
    elif kind == 'wink':
        out += _eye_open(EYE_X, 1)
        out += _eye_arc(-EYE_X)
        out += _blush()
        out += [P('head', (0, 4.0, FZ + 0.03), (1.1, 0.38, 0.03), '#A8475A', **D),
                P('head', (1.3, 4.45, FZ + 0.03), (0.4, 0.4, 0.03), '#A8475A', **D),
                P('head', (-1.3, 4.45, FZ + 0.03), (0.4, 0.4, 0.03), '#A8475A', **D)]
    elif kind == 'sleepy':
        for sg in (1, -1):
            ex = sg * EYE_X
            out += [P('head', (ex, 8.0, FZ + 0.03), (2.9, 2.0, 0.03), '#24161C', **D),
                    P('head', (ex, 10.2, FZ + 0.03), (3.3, 0.5, 0.03), LASH, **D),            # 눈꺼풀 선
                    P('head', (ex, 7.4, FZ + 0.06), (2.1, 1.3, 0.03), '#5A3428', **D),
                    P('head', (ex, 6.5, FZ + 0.08), (1.4, 0.45, 0.03), '#A06C48', **D),
                    P('head', (ex - 0.9, 8.6, FZ + 0.12), (0.7, 0.6, 0.03), '#FFFFFF', emit=0.8, **D)]
        out += _blush()
        out.append(P('head', (0, 4.0, FZ + 0.03), (0.65, 0.6, 0.03), '#A8475A', **D))
    return out


# ================================================================== hair (사이클 7 새 머리)
class Hair:
    """새 머리 로컬 좌표 헬퍼 (머리 x +-14, y 0..25.6, z +-12.8). 가는 가닥(1~2칸) 위주."""

    def __init__(self, col, seed, noise=0.06):
        self.col, self.r, self.out = col, _rng(seed), []
        self.kw = dict(noise=noise, bevel=HAIRB)

    def box(self, c, h, k=0.0, col=None, **kw):
        kk = dict(self.kw); kk.update(kw)
        self.out.append(P('head', c, h, tint(col or self.col, k), **kk))

    def chunk(self, c, h, lo=-0.10, hi=0.12, **kw):
        self.box(c, h, self.r.uniform(lo, hi), **kw)

    def u(self, a, b):
        return self.r.uniform(a, b)

    def shell(self, sb=8.0, bb=4.0, sf=4.0, top=27.2):
        """정수리 판 + 뒤판(아래 끝 bb) + 옆판(아래 끝 sb, 앞 끝 z sf) + 앞머리 바탕(y 19.7..26.3)."""
        self.box((0, top, -0.4), (15.6, 1.8, 14.4))
        self.box((0, (bb + 27.6) / 2, -14.3), (15.5, (27.6 - bb) / 2, 1.6))
        for sg in (1, -1):
            self.box((sg * 15.5, (sb + 27.6) / 2, (sf - 15.6) / 2), (1.5, (27.6 - sb) / 2, (sf + 15.6) / 2))
        self.box((0, 23.0, 13.9), (15.0, 3.3, 1.3))

    def crown(self, n=4, y0=29.0, dome=3.0, size=(2.4, 3.4), hy=(1.0, 1.8), spread=10.5, jit=1.2, z0=-0.8):
        """정수리 볼륨 (가운데가 높은 돔). 둥근 바탕 덩어리 + 작은 결 덩어리(대비 작게)."""
        self.box((0, y0 - 0.4 + dome * 0.35, z0), (spread + 1.0, 1.0 + dome * 0.35, spread + 1.0), 0.02)
        self.box((0, y0 - 0.2 + dome * 0.7, z0), (spread * 0.6, 0.8 + dome * 0.3, spread * 0.6), 0.04)
        m = n + 1
        for gx in np.linspace(-spread, spread, m):
            for gz in np.linspace(-spread, spread, m):
                mid = 1.0 - (abs(gx) + abs(gz)) / (2.4 * spread)
                self.chunk((gx + self.u(-jit, jit), y0 + mid * dome + self.u(-0.4, 0.4), z0 + gz + self.u(-jit, jit)),
                           (self.u(*size) * 0.7, self.u(*hy), self.u(*size) * 0.7), -0.05, 0.08)

    def bangs(self, strands, top=24.5, z=14.8, depth=1.3, tip=1.6, k=(-0.06, 0.06)):
        """앞머리 가닥 (x, 아래끝 y, 반폭): 넓은 몸통 + 좁은 끝(계단)."""
        for x, yb, hw in strands:
            self.chunk((x, (yb + tip + top) / 2, z), (hw, (top - yb - tip) / 2, depth), *k)
            self.chunk((x, yb + tip / 2, z - 0.1), (hw * 0.55, tip / 2, depth * 0.9), k[0] - 0.04, k[1] - 0.04)

    def back_strands(self, y_top, yb, x0=-16.0, x1=16.0, w=(1.2, 2.0), z=-15.6, depth=1.3, k=(-0.12, 0.08), **kw):
        """뒤쪽 세로 가닥들 (아래 끝 yb 범위에서 들쭉날쭉)."""
        x = x0
        while x < x1:
            hw = self.u(*w)
            b = self.u(*yb)
            self.chunk((x + hw, (y_top + b) / 2, z + self.u(-0.3, 0.3)), (hw, (y_top - b) / 2, depth), *k, **kw)
            x += 2 * hw * 0.85

    def side_strands(self, sg, y_top, yb, z0, z1, x=17.0, w=(1.1, 1.8), depth=1.4, k=(-0.12, 0.08), **kw):
        """옆쪽 세로 가닥들 (z0..z1)."""
        z = z0
        while z < z1:
            hw = self.u(*w)
            b = self.u(*yb)
            self.chunk((sg * (x + self.u(-0.3, 0.3)), (y_top + b) / 2, min(z + hw, z1 - hw * 0.3)), (depth, (y_top - b) / 2, hw), *k, **kw)
            z += 2 * hw * 0.85

    def cheek_lock(self, sg, yb, z0=4.0, z1=14.6, x=13.7, top=22.0, k=0.02, col=None, hx=2.2):
        """볼을 감싸는 옆머리: 얼굴 가장자리 앞으로 내려와 끝이 안쪽으로 말림."""
        self.box((sg * x, (top + yb) / 2, (z0 + z1) / 2), (hx, (top - yb) / 2, (z1 - z0) / 2), k, col=col)
        self.box((sg * (x - 0.6), yb - 0.7, z1 - 1.4), (hx * 0.75, 0.9, 1.3), k - 0.06, col=col)


def hair_ash_twoblock():
    """시안 1: 애쉬브라운 투블럭. 둥근 버섯 실루엣(윗층이 옆/뒤를 덮음), 계단식 앞머리, 볼 감싸는 옆머리, 어두운 뒷목 언더컷."""
    k = Hair('#7A6862', 101)
    k.shell(sb=9.0, bb=6.0, sf=5.0)
    k.crown(n=4, y0=28.2, dome=1.6, size=(2.6, 3.6), hy=(0.8, 1.2), spread=10.5, jit=1.0)
    for sg in (1, -1):                                                   # 윗층 오버행 (옆)
        k.side_strands(sg, 24.5, (7.4, 10.4), -15.6, 8.0, x=16.9, w=(1.3, 2.0))
    k.back_strands(25.0, (6.4, 9.4), z=-16.4, w=(1.4, 2.2))              # 윗층 오버행 (뒤)
    k.box((0, 26.0, 14.2), (15.4, 1.6, 1.5), 0.06)                        # 앞 정수리 볼륨 (모자 둥근 모서리 밖으로 안 나오게)
    k.box((0, 3.6, -13.4), (11.4, 2.6, 0.9), -0.30)                       # 언더컷 (짧게 친 뒷목)
    k.bangs([(x, yb, 1.45) for x, yb in zip(np.linspace(-13.6, 13.6, 11),
                                            (15.8, 14.4, 13.4, 14.6, 13.6, 14.8, 13.5, 14.6, 13.4, 14.5, 15.9))])
    k.bangs([(-9.0, 17.0, 2.0), (-2.6, 16.6, 2.1), (3.8, 17.2, 2.0), (10.2, 17.6, 1.9)], top=26.2, z=15.8, depth=0.9, tip=1.4)
    for sg in (1, -1):
        k.cheek_lock(sg, 6.2, z0=3.0, z1=14.6)
        k.cheek_lock(sg, 8.0, z0=-6.0, z1=4.0, x=16.4, hx=1.6, k=-0.04)
    return k.out


def hair_black_seethrough():
    """시안 2: 시스루뱅 긴 흑발. 얇은 앞머리 가닥(이마가 비침), 얼굴 옆 직선 커튼, 허리까지 오는 뒷머리, 헤어핀 2개."""
    k = Hair('#27232C', 202, noise=0.05)
    k.shell(sb=-4.0, bb=-18.0, sf=3.5)
    k.crown(n=3, y0=28.8, dome=1.8, size=(3.4, 4.4), hy=(0.9, 1.3), spread=9.5, jit=0.8)
    k.back_strands(25.0, (-25.0, -21.5), z=-16.0, w=(1.5, 2.3), x0=-17.4, x1=17.4)
    for sg in (1, -1):
        k.side_strands(sg, 24.5, (-21.5, -16.5), -15.6, 5.0, x=17.6, w=(1.3, 2.0), depth=1.6)   # 옆 커튼 (어깨 바깥)
        k.box((sg * 13.8, 3.0, 9.4), (2.2, 18.6, 5.2), 0.03)                               # 얼굴 옆 직선 (볼 감쌈)
        k.box((sg * 13.8, -16.2, 9.0), (2.0, 0.9, 3.6), -0.06)
        k.box((sg * 12.4, 13.6, 13.9), (1.2, 4.6, 1.0), 0.02)                              # 긴 옆 앞머리
        k.box((sg * 12.0, 8.6, 13.7), (0.8, 0.9, 0.8), -0.04)
    # 시스루 앞머리: 얇은 가닥 사이로 이마가 보이게
    k.bangs([(x, 14.4 + 0.7 * ((i * 7) % 3) / 2, 0.8) for i, x in enumerate(np.linspace(-10.2, 10.2, 9))],
            top=20.6, z=14.3, depth=0.8, tip=1.4)
    # 헤어핀 2개 (캐릭터 왼쪽, 사선)
    k.out.append(P('head', (9.4, 21.4, 15.45), (2.2, 0.55, 0.3), '#FBF3EA', bevel=0.2, noise=0.0, rot=(0, 0, 24)))
    k.out.append(P('head', (10.2, 19.4, 15.45), (2.2, 0.55, 0.3), '#F6B6CA', bevel=0.2, noise=0.0, rot=(0, 0, 24)))
    return k.out


def hair_black_wolfcut():
    """시안 3: 검은 울프컷. 헝클어진 정수리, 뾰족한 앞머리, 바깥으로 뻗친 층층 옆머리, 길게 내려와 뻗친 뒷목."""
    k = Hair('#1F1C23', 303, noise=0.07)
    k.shell(sb=8.0, bb=3.0, sf=4.5)
    k.crown(n=4, y0=27.8, dome=1.6, size=(2.0, 3.0), hy=(0.8, 1.2), spread=10.5, jit=1.6)
    k.bangs([(x, yb, 1.4) for x, yb in zip(np.linspace(-13.4, 13.4, 10),
                                           (14.4, 12.6, 14.0, 12.4, 13.8, 12.5, 13.9, 12.7, 14.2, 15.0))], tip=2.4)
    for sg in (1, -1):
        for row, y in enumerate((19.5, 14.0, 8.6)):                                           # 층층이 바깥으로 뻗침
            for z in (-13.0, -9.2, -5.4, -1.6, 2.2, 5.6):
                ang = sg * (10 + 7 * row + k.u(-4, 4))
                k.chunk((sg * (16.5 + 0.5 * row), y + k.u(-0.8, 0.8), z + k.u(-0.4, 0.4)), (1.1, 2.6, 1.5), -0.1, 0.08,
                        rot=(0, 0, ang))
        k.cheek_lock(sg, 7.0, z0=4.0, z1=14.4, x=13.8, hx=2.0, k=0.0)
        k.chunk((sg * 15.4, 5.6, 12.6), (1.1, 1.4, 1.2), -0.08, 0.0, rot=(0, 0, sg * 20))
    k.back_strands(21.0, (-2.4, 1.0), z=-16.0, w=(1.2, 1.8))
    for x in np.linspace(-11, 11, 6):                                                          # 뒷목 뻗침
        k.chunk((x, -2.8 + k.u(-0.6, 0.6), -16.6), (1.2, 1.8, 1.2), -0.1, 0.04, rot=(28, 0, np.sign(x) * 14))
    return k.out


def hair_pink_bridge_ponytail():
    """시안 4: 진갈색 + 핑크 브릿지 하이포니테일. 정수리 뒤에서 높이 묶어 위로 솟았다 등 뒤로 떨어지는 꼬리, 얼굴 옆 잔머리."""
    base, pink = '#3F2D29', '#F288B6'
    k = Hair(base, 404, noise=0.05)
    k.shell(sb=10.0, bb=8.0, sf=4.0)
    k.crown(n=3, y0=28.4, dome=1.4, size=(3.4, 4.4), hy=(0.8, 1.2), spread=8.5, jit=0.6)
    k.bangs([(x, yb, 1.4) for x, yb in zip(np.linspace(-12.8, 12.8, 9),
                                           (15.6, 14.4, 15.4, 14.2, 15.2, 14.4, 15.4, 14.6, 15.6))], top=22.0, depth=1.0)
    for sg in (1, -1):
        k.box((sg * 13.5, 11.0, 13.4), (1.5, 10.4, 1.2), 0.02)                                 # 얼굴 옆 잔머리
        k.box((sg * 13.0, 0.2, 13.2), (1.0, 0.9, 1.0), -0.05)
        k.box((sg * 16.0, 13.4, 9.6), (1.2, 7.8, 1.4), 0.0, col=pink)                          # 핑크 브릿지 가닥
        k.box((sg * 15.7, 5.2, 9.6), (0.9, 0.9, 1.1), -0.05, col=pink)
        k.side_strands(sg, 24.0, (9.0, 11.0), -15.0, 6.0, x=16.6, w=(1.4, 2.0), depth=1.1)
    k.out.append(P('head', (0, 28.8, -11.4), (3.0, 2.2, 2.8), pink, bevel=0.6, noise=0.04))  # 곱창 머리끈
    tail = [((0, 32.0, -14.0), (3.6, 2.6, 3.0)), ((0.6, 34.6, -18.8), (4.2, 3.0, 3.4)), ((1.6, 34.2, -24.4), (4.6, 3.5, 3.6)),
            ((3.0, 30.6, -28.2), (4.7, 3.7, 3.4)), ((4.6, 24.2, -29.6), (4.5, 3.8, 3.2)), ((6.0, 17.6, -29.4), (4.0, 3.8, 3.0)),
            ((7.0, 11.0, -28.4), (3.4, 3.6, 2.7)), ((7.6, 4.8, -26.8), (2.7, 3.2, 2.3)), ((8.0, -0.6, -25.0), (1.8, 2.4, 1.8))]
    shade = (0.10, 0.08, 0.05, 0.02, 0.0, -0.03, -0.06, -0.08, -0.1)
    for i, (c, h) in enumerate(tail):
        k.box(c, h, shade[i])
        if 1 <= i <= 7:                                                                       # 핑크 브릿지 결
            for sg in (1, -1):
                k.box((c[0] + sg * (h[0] + 0.1), c[1], c[2] + 0.5 * sg), (0.45, h[1] * 0.85, h[2] * 0.45), 0.0, col=pink)
    return k.out


HAIRS = {'ash-twoblock': hair_ash_twoblock, 'black-seethrough': hair_black_seethrough,
         'black-wolfcut': hair_black_wolfcut, 'pink-bridge-ponytail': hair_pink_bridge_ponytail}

# ------------------------------------------------------------------ 사이클 5 머리 8종 (사이클 7 키트로 다시: id/색/실루엣 의도 유지)
def _fringe(k, xs, ybs, hw=1.45, **kw):
    k.bangs([(x, yb, hw) for x, yb in zip(xs, ybs)], **kw)


def hair_black_short():
    """검은 짧은 머리: 곱슬 덩어리 볼륨, 이마를 덮는 짧은 앞머리, 볼 옆 짧은 옆머리."""
    k = Hair('#30231F', 7, noise=0.07)
    k.shell(sb=10.0, bb=5.0, sf=5.0)
    k.crown(n=4, y0=28.8, dome=2.8, size=(2.6, 3.6), hy=(1.2, 2.0), spread=10.5, jit=1.4)
    for sg in (1, -1):
        for y in (22.0, 17.0, 12.4):                                              # 옆 곱슬 덩어리
            for z in (-12.0, -6.5, -1.0, 4.0):
                k.chunk((sg * (16.6 + k.u(-0.3, 0.5)), y + k.u(-0.8, 0.8), z + k.u(-0.8, 0.8)), (1.6, 2.2, 2.4), -0.1, 0.1)
        k.cheek_lock(sg, 9.6, z0=4.0, z1=14.4, hx=2.0)
    for y in (22.0, 16.6, 11.2, 6.4):                                              # 뒤 곱슬
        for x in np.linspace(-12.5, 12.5, 6):
            k.chunk((x + k.u(-0.8, 0.8), y + k.u(-0.8, 0.8), -16.3 + k.u(-0.3, 0.3)), (2.4, 2.3, 1.4), -0.12, 0.08)
    _fringe(k, np.linspace(-13.4, 13.4, 9), (16.4, 15.4, 16.0, 15.2, 15.8, 15.0, 15.8, 15.2, 16.4), hw=1.7)
    for x in (-9.6, -3.2, 3.2, 9.6):                                               # 앞 곱슬 볼륨
        k.chunk((x + k.u(-0.6, 0.6), 26.6 + k.u(-0.4, 0.6), 15.2 + k.u(0, 0.8)), (2.8, 2.0, 1.8), -0.04, 0.1)
    return k.out


def hair_brown_short():
    """밤색 짧은 머리: 단정한 옆가르마, 한쪽으로 쓸린 앞머리, 정수리 더듬이."""
    k = Hair('#7A4A2E', 21, noise=0.05)
    k.shell(sb=9.0, bb=5.0, sf=5.0)
    k.crown(n=3, y0=28.6, dome=2.0, size=(3.0, 4.0), hy=(1.0, 1.4), spread=9.5, jit=0.8)
    k.box((-2.0, 26.6, 14.6), (13.4, 2.0, 1.6), 0.06)                              # 앞 볼륨 (오른쪽으로 쓸림)
    k.box((5.0, 28.2, 13.6), (8.0, 1.2, 1.6), 0.10)
    _fringe(k, np.linspace(-13.2, 13.4, 9), np.linspace(14.0, 17.6, 9), hw=1.65)
    for sg in (1, -1):
        k.side_strands(sg, 24.0, (8.6, 10.6), -15.4, 6.0, x=16.9, w=(1.6, 2.2))
        k.cheek_lock(sg, 8.6, z0=4.0, z1=14.4, hx=2.0)
    k.back_strands(24.0, (4.6, 6.4), w=(1.8, 2.4))
    k.box((1.4, 31.2, 3.0), (0.9, 1.6, 0.9), 0.05)                                 # 더듬이
    k.box((2.6, 33.0, 3.8), (0.9, 1.0, 0.9), 0.12)
    return k.out


def hair_blonde_spiky():
    """금발 뻗친 머리: 위/옆/뒤로 뻗은 뾰족한 덩어리(2단으로 좁아짐), 아래로 뾰족한 앞머리."""
    k = Hair('#F2C14E', 33, noise=0.06)
    k.shell(sb=10.0, bb=5.0, sf=5.0)
    k.crown(n=3, y0=28.4, dome=1.6, size=(3.0, 3.8), hy=(1.0, 1.4), spread=9.0, jit=0.6)
    # (중심, (rz: + 면 +x 쪽으로 눕힘, rx: + 면 앞으로 눕힘))
    spikes = [((-5.5, 29.6, 5.0), (-25, 10)), ((4.5, 30.0, 5.5), (25, 8)), ((0, 30.4, -3.0), (0, -18)),
              ((-9.0, 29.0, -7.0), (-35, -25)), ((9.0, 29.0, -6.0), (35, -25)),
              ((-15.6, 24.0, 2.0), (-60, 5)), ((15.6, 24.0, 1.0), (60, 5)),
              ((-6.0, 20.0, -15.0), (-15, -70)), ((6.0, 20.0, -15.0), (15, -70)), ((0, 11.0, -15.0), (0, -85)),
              ((-15.0, 15.0, -8.0), (-70, -30)), ((15.0, 15.0, -8.0), (70, -30))]
    for (c, (rz, rx)) in spikes:
        k.box(c, (3.4, 2.6, 3.4), k.u(-0.02, 0.08), rot=(rx, 0, -rz))
        tip = np.array(c, float) + rot_z(-rz) @ rot_x(rx) @ np.array([0, 3.6, 0])
        k.box(tuple(tip), (1.7, 1.8, 1.7), k.u(0.04, 0.14), rot=(rx, 0, -rz))
    for x, yb in zip(np.linspace(-12.6, 12.6, 6), (15.4, 14.2, 15.0, 14.2, 15.0, 15.6)):   # 뾰족 앞머리
        k.box((x, yb + 3.4, 14.8), (2.4, 2.2, 1.3), k.u(-0.04, 0.04))
        k.box((x, yb + 0.8, 14.7), (1.1, 0.8, 1.1), k.u(-0.06, 0.02))
    k.box((0, 25.0, 14.9), (15.0, 1.8, 1.3), 0.04)
    for sg in (1, -1):
        k.cheek_lock(sg, 10.0, z0=5.0, z1=14.4, hx=1.8)
    return k.out


def hair_pink_long():
    """분홍 긴 머리: 일자 앞머리, 볼을 감싸고 가슴까지 오는 앞 가닥, 허리까지 오는 뒷머리(끝 말림)."""
    k = Hair('#F49AC1', 41, noise=0.05)
    k.shell(sb=-4.0, bb=-16.0, sf=3.5)
    k.crown(n=3, y0=28.6, dome=1.6, size=(3.4, 4.2), hy=(0.9, 1.3), spread=9.5, jit=0.6)
    _fringe(k, np.linspace(-12.8, 12.8, 9), [14.6 + (0.5 if i % 2 else 0) for i in range(9)], hw=1.6, tip=1.0)
    k.back_strands(25.0, (-20.0, -17.0), x0=-17.2, x1=17.2, w=(1.6, 2.4))
    for x in (-12.0, -6.0, 0.0, 6.0, 12.0):                                        # 끝 안쪽 말림
        k.box((x, -20.4, -14.6), (3.0, 1.1, 2.0), -0.10)
    for sg in (1, -1):
        k.side_strands(sg, 24.5, (-17.0, -12.0), -15.6, 3.0, x=17.4, w=(1.4, 2.0), depth=1.5)
        k.box((sg * 13.8, 2.0, 10.0), (2.2, 19.0, 4.6), 0.04)                      # 얼굴 옆 앞 가닥 (가슴까지)
        k.box((sg * 13.2, -17.6, 11.6), (1.8, 1.2, 2.6), -0.06)                     # 끝 말림
    return k.out


def hair_sky_bob():
    """하늘색 단발: 턱선 길이, 안으로 말린 둥근 실루엣, 일자 앞머리."""
    k = Hair('#8FCBF0', 55, noise=0.06)
    k.shell(sb=2.0, bb=1.0, sf=5.0)
    k.crown(n=3, y0=28.8, dome=2.0, size=(3.0, 4.0), hy=(1.0, 1.4), spread=9.5, jit=0.8)
    _fringe(k, np.linspace(-12.8, 12.8, 9), [14.8 - 0.5 * np.cos(i * 1.7) for i in range(9)], hw=1.6, tip=1.0)
    for sg in (1, -1):
        k.side_strands(sg, 24.5, (2.6, 4.4), -15.6, 7.0, x=17.6, w=(1.5, 2.1), depth=1.6)
        k.box((sg * 16.4, 1.4, -3.8), (1.8, 1.4, 11.0), -0.08)                       # 아래 안쪽 말림
        k.cheek_lock(sg, 2.6, z0=4.0, z1=14.4, hx=2.2)
    k.back_strands(25.0, (1.8, 3.6), w=(1.6, 2.4), depth=1.5)
    k.box((0, 1.0, -16.0), (15.0, 1.4, 1.6), -0.08)
    k.box((-3.0, 31.0, 1.0), (1.8, 0.9, 1.8), 0.1)
    return k.out


def hair_tan_ponytail():
    """갈색 포니테일: 뒤통수 가운데에서 묶어 아래로 흐르는 꼬리, 빨간 머리끈, 옆 가르마 앞머리."""
    k = Hair('#8C5A3C', 63, noise=0.05)
    k.shell(sb=9.0, bb=6.0, sf=5.0)
    k.crown(n=3, y0=28.4, dome=1.4, size=(3.4, 4.4), hy=(0.8, 1.2), spread=9.0, jit=0.6)
    _fringe(k, np.linspace(-12.8, 12.8, 9), np.linspace(14.2, 16.8, 9)[::-1] + np.array([0, .6, 0, .6, 0, .6, 0, .6, 0]), hw=1.6)
    for sg in (1, -1):
        k.box((sg * 13.6, 11.0, 13.2), (1.4, 9.6, 1.2), 0.02)                      # 얼굴 옆 잔머리
        k.side_strands(sg, 24.0, (9.0, 11.0), -15.4, 6.0, x=16.8, w=(1.5, 2.1), depth=1.1)
    k.out.append(P('head', (0, 19.0, -16.4), (2.4, 2.4, 1.6), '#E8483E', bevel=0.5, noise=0.02))   # 머리끈
    tail = [((0, 19.2, -19.0), (3.4, 3.2, 2.4)), ((0, 13.8, -20.6), (3.9, 3.6, 2.8)), ((0, 7.8, -20.6), (3.6, 3.4, 2.7)),
            ((0, 2.2, -19.8), (3.0, 3.0, 2.4)), ((0.4, -3.0, -18.6), (2.2, 2.6, 2.0)), ((0.8, -7.2, -17.4), (1.3, 1.8, 1.4))]
    for i, (c, h) in enumerate(tail):
        k.box(c, h, (0.08, 0.04, 0.0, -0.04, -0.08, -0.1)[i])
    return k.out


def hair_black_twintail():
    """검은 양갈래: 귀 위에서 묶은 두 꼬리가 바깥으로 뻗었다 어깨 아래로, 빨간 머리끈, 일자 앞머리."""
    k = Hair('#2C2533', 77, noise=0.06)
    k.shell(sb=8.0, bb=4.0, sf=5.0)
    k.crown(n=3, y0=28.4, dome=1.4, size=(3.4, 4.4), hy=(0.8, 1.2), spread=9.0, jit=0.6)
    _fringe(k, np.linspace(-12.8, 12.8, 9), [14.8 + (0.6 if i in (0, 8) else 0) for i in range(9)], hw=1.6, tip=1.0)
    k.back_strands(24.0, (4.0, 6.0), w=(1.8, 2.4))
    for sg in (1, -1):
        k.cheek_lock(sg, 8.0, z0=4.0, z1=14.4, hx=2.0)
        k.out.append(P('head', (sg * 17.6, 19.0, -3.0), (1.4, 2.0, 2.0), '#E8483E', bevel=0.4, noise=0.02))
        tail = [((sg * 20.0, 18.4, -3.2), (2.6, 2.8, 2.6)), ((sg * 21.8, 13.6, -3.2), (3.0, 3.2, 2.8)),
                ((sg * 22.2, 7.8, -3.0), (2.9, 3.0, 2.7)), ((sg * 21.6, 2.4, -2.6), (2.5, 2.8, 2.4)),
                ((sg * 20.4, -2.6, -2.2), (1.9, 2.4, 1.9)), ((sg * 19.0, -6.4, -1.8), (1.2, 1.6, 1.3))]
        for i, (c, h) in enumerate(tail):
            k.box(c, h, (0.10, 0.04, -0.02, -0.06, -0.08, -0.1)[i])
    return k.out


def hair_mint_curly():
    """민트 곱슬: 머리 전체를 덮는 크고 둥근 곱슬 볼륨 (작은 덩어리 많이, 바깥으로 2~4칸)."""
    k = Hair('#7FD6B8', 91, noise=0.08)
    k.shell(sb=5.0, bb=2.0, sf=5.0)
    k.crown(n=4, y0=29.6, dome=3.0, size=(2.6, 3.6), hy=(1.4, 2.2), spread=11.0, jit=1.4)
    for sg in (1, -1):
        for y in (24.0, 19.0, 14.0, 9.0, 4.6):
            for z in (-13.0, -8.0, -3.0, 2.0, 6.4):
                k.chunk((sg * (17.8 + k.u(-0.6, 0.6)), y + k.u(-1.0, 1.0), z + k.u(-1.0, 1.0)), (1.8, 2.3, 2.4), -0.12, 0.1)
        k.cheek_lock(sg, 6.0, z0=4.0, z1=14.4, hx=2.2)
    for y in (24.0, 19.0, 14.0, 9.0, 4.0):
        for x in np.linspace(-14.0, 14.0, 7):
            k.chunk((x + k.u(-1.0, 1.0), y + k.u(-1.0, 1.0), -17.0 + k.u(-0.6, 0.6)), (2.4, 2.4, 1.8), -0.12, 0.1)
    _fringe(k, np.linspace(-13.0, 13.0, 8), (15.6, 14.4, 15.2, 14.2, 15.0, 14.4, 15.4, 16.0), hw=1.9, tip=1.2)
    for x in np.linspace(-11.0, 11.0, 5):
        k.chunk((x + k.u(-0.6, 0.6), 27.0 + k.u(-0.4, 0.6), 15.6 + k.u(0, 0.8)), (2.8, 2.2, 1.9), -0.04, 0.1)
    return k.out


HAIRS.update({'black-short': hair_black_short, 'brown-short': hair_brown_short, 'blonde-spiky': hair_blonde_spiky,
              'pink-long': hair_pink_long, 'sky-bob': hair_sky_bob, 'tan-ponytail': hair_tan_ponytail,
              'black-twintail': hair_black_twintail, 'mint-curly': hair_mint_curly})


# ================================================================== top (옷 공용)
BX, BZ = 8.0, 4.8          # 기본 핏 몸판 반폭/반깊이 (마네킹 가슴 7.0 x 4.0)


def _body(col, hem=None, hx=BX, hz=BZ, y0=21.4):
    """기본 핏 몸판 (y0..40.4)."""
    out = R('torso', (0, 35.0, 0), (hx, 5.4, hz), col, 0.8)
    out += R('torso', (0, (y0 + 30.4) / 2, 0), (hx - 0.2, (30.4 - y0) / 2 + 0.6, hz - 0.15), col, 0.6)
    if hem:
        out += R('torso', (0, y0 + 0.8, 0), (hx + 0.1, 0.9, hz + 0.1), hem, 0.4)
    return out


def _long_sleeves(col, cuff, hx=2.55):
    out = []
    for sg in (1, -1):
        a = 'arm%+d' % sg
        out += R(a, (0, -5.0, 0), (hx, 5.6, hx), col, 0.6)
        out += R(a, (0, -11.4, 0.1), (hx + 0.2, 0.95, hx + 0.2), cuff, 0.4)
    return out


def _over_sleeves(col, cuff, hx=3.1):
    """오버사이즈 소매: 손등 위쪽까지 덮는다 (손 y -12.4..-16.8 중 위 1.7칸)."""
    out = []
    for sg in (1, -1):
        a = 'arm%+d' % sg
        out += R(a, (0, -0.4, 0), (hx + 0.2, 1.6, hx + 0.2), col, 0.8)          # 떨어진 어깨
        out += R(a, (0, -6.0, 0.05), (hx, 6.0, hx), col, 0.7)
        out += R(a, (0, -12.9, 0.2), (hx - 0.15, 1.25, hx - 0.15), cuff, 0.5)
    return out


def _short_sleeves(col, band=None, puff=False):
    out = []
    for sg in (1, -1):
        a = 'arm%+d' % sg
        if puff:
            out += R(a, (0, -1.8, 0), (3.4, 2.8, 3.4), col, 0.9)
        else:
            out += R(a, (0, -2.4, 0), (2.75, 3.0, 2.75), col, 0.6)
        if band:
            hb = 3.0 if puff else 2.85
            out += R(a, (0, -4.4 if puff else -5.2, 0), (hb, 0.5, hb), band, 0.3)
    return out


def _hood(col, z0=-5.6):
    return [P('torso', (0, 41.4, z0), (7.2, 2.6, 2.6), col, bevel=SOFT),
            P('torso', (0, 43.6, z0 - 1.4), (5.8, 1.3, 1.6), tint(col, -0.04), bevel=SOFT),
            P('torso', (0, 38.6, z0 - 2.0), (5.6, 1.8, 1.2), tint(col, -0.07), bevel=SOFT)]


# ------------------------------------------------------------------ 새 상의 (시안)
def top_hoodie_lavender():
    """시안 1: 라벤더 오버사이즈 후드. 박스 핏 몸판, 떨어진 어깨, 손등 덮는 소매, 캥거루 주머니, 흰 끈."""
    col = '#BCA8EC'
    rib = tint(col, -0.08)
    hz = 5.5
    out = R('torso', (0, 33.8, 0), (9.2, 6.8, hz), col, 1.0)                   # 27..40.6
    out += R('torso', (0, 24.4, 0), (9.0, 3.0, hz - 0.15), col, 0.8)          # 21.4..27.4
    out += R('torso', (0, 20.8, 0), (8.7, 1.0, hz - 0.4), rib, 0.4)           # 밑단 시보리
    out += [P('torso', (0, 25.0, hz + 0.05), (5.8, 2.7, 0.35), tint(col, 0.04), bevel=0.4),       # 캥거루 주머니
            decal('torso', (-5.8, 25.0, hz + 0.42), (0.22, 2.5, 0.03), tint(col, -0.18)),
            decal('torso', (5.8, 25.0, hz + 0.42), (0.22, 2.5, 0.03), tint(col, -0.18)),
            decal('torso', (0, 27.75, hz + 0.42), (5.6, 0.14, 0.03), tint(col, -0.1))]
    out += _hood(col, z0=-6.0)
    for sg in (1, -1):
        out += [P('torso', (sg * 5.8, 41.2, -0.4), (2.2, 1.5, 4.9), col, bevel=SOFT),                 # 후드 앞 둘레
                decal('torso', (sg * 1.9, 37.2, hz + 0.03), (0.4, 2.8, 0.03), '#FFFFFF', emit=0.05),   # 끈
                P('torso', (sg * 1.9, 34.2, hz + 0.1), (0.55, 0.7, 0.25), '#F4F1F6', bevel=0.15, noise=0)]
    out += [decal('torso', (-5.4, 36.0, hz + 0.03), (1.2, 1.2, 0.03), '#DCD0F6')]                    # 무지 네모 패치
    return out + _over_sleeves(col, rib, hx=3.4)


def top_cardigan_cream():
    """시안 2: 크림 니트 가디건(열림) + 흰 티(분홍 리본 프린트) + 검정 미니 숄더백."""
    cr = '#EFE2C8'; wt = '#FFFFFF'; bag = '#2A2630'
    hz = 5.0
    out = R('torso', (0, 33.4, 0), (8.4, 7.0, hz), cr, 0.9)                   # 26.4..40.4
    out += R('torso', (0, 24.6, 0), (8.3, 2.6, hz - 0.1), cr, 0.7)
    out += R('torso', (0, 21.6, 0), (8.45, 0.8, hz), tint(cr, -0.07), 0.4)  # 밑단 시보리
    out += [P('torso', (0, 30.6, hz - 0.15), (2.8, 8.8, 0.35), wt, bevel=0.3, noise=0.01),     # 안쪽 흰 티
            P('torso', (0, 40.3, 0), (4.0, 0.5, 4.0), wt, bevel=0.3, noise=0.01)]
    for sg in (1, -1):
        out += [P('torso', (sg * 3.3, 30.6, hz + 0.15), (0.55, 9.0, 0.2), tint(cr, -0.04), bevel=0.15),   # 여밈 단
                decal('torso', (sg * 3.3, 35.0, hz + 0.38), (0.22, 0.22, 0.03), '#C9B48E'),
                decal('torso', (sg * 3.3, 30.4, hz + 0.38), (0.22, 0.22, 0.03), '#C9B48E')]
        for x in (5.2, 7.0):
            out.append(decal('torso', (sg * x, 31.0, hz + 0.03), (0.16, 8.6, 0.03), tint(cr, -0.06)))      # 니트 골
    out += [decal('torso', (-0.8, 36.4, hz + 0.23), (0.65, 0.55, 0.03), '#F48FB1'),                       # 티 리본 프린트
            decal('torso', (0.8, 36.4, hz + 0.23), (0.65, 0.55, 0.03), '#F48FB1'),
            decal('torso', (0, 36.4, hz + 0.26), (0.32, 0.32, 0.03), '#D9628A')]
    # 숄더백 (캐릭터 왼쪽 엉덩이 앞) + 끈
    out += [P('torso', (6.0, 23.2, hz + 0.5), (2.3, 2.1, 1.2), bag, bevel=0.5, noise=0.02),
            P('torso', (6.0, 24.4, hz + 1.72), (2.2, 0.85, 0.05), tint(bag, 0.1), bevel=0.0, noise=0.0),
            decal('torso', (6.0, 23.8, hz + 1.79), (0.55, 0.3, 0.03), '#E3B04B', emit=0.15),
            P('torso', (5.2, 33.2, hz + 0.25), (0.35, 7.6, 0.2), bag, bevel=0.1, noise=0.0),
            P('torso', (5.2, 40.6, 0), (0.35, 0.25, hz + 0.2), bag, bevel=0.1, noise=0.0),
            P('torso', (5.2, 36.0, -hz - 0.25), (0.35, 4.6, 0.2), bag, bevel=0.1, noise=0.0)]
    return out + _over_sleeves(cr, tint(cr, -0.07), hx=2.95)


def top_varsity_navy():
    """시안 3: 네이비 몸판 + 크림 소매 바시티 재킷. 줄무늬 시보리, 스냅 단추, 글자 없는 둥근 패치."""
    nv = '#25304E'; cr = '#ECE1CA'; wt = '#FFFFFF'
    hz = 5.2
    out = R('torso', (0, 33.4, 0), (8.6, 7.0, hz), nv, 0.9)
    out += R('torso', (0, 24.6, 0), (8.5, 2.8, hz - 0.1), nv, 0.7)
    out += R('torso', (0, 21.4, 0), (8.65, 0.95, hz + 0.05), tint(nv, -0.1), 0.4)     # 밑단 시보리
    out += R('torso', (0, 21.6, 0), (8.75, 0.22, hz + 0.15), cr, 0.1)
    out += [P('torso', (0, 33.6, hz - 0.2), (2.3, 6.8, 0.35), wt, bevel=0.3, noise=0.01)]   # 안쪽 흰 티
    out += R('torso', (0, 40.5, -0.4), (5.8, 0.8, 5.0), tint(nv, -0.1), 0.3)          # 깃 시보리
    out += R('torso', (0, 40.6, -0.4), (5.9, 0.2, 5.1), cr, 0.1)
    for sg in (1, -1):
        out.append(P('torso', (sg * 2.85, 31.0, hz + 0.15), (0.55, 9.2, 0.2), tint(nv, 0.05), bevel=0.15))
    for y in (37.0, 33.4, 29.8, 26.2):
        out.append(P('torso', (-2.85, y, hz + 0.38), (0.42, 0.42, 0.1), cr, bevel=0.1, noise=0, emit=0.05))
    # 글자 없는 둥근 패치 (가슴 오른쪽): 크림 원 + 빨간 점
    out += [decal('torso', (-5.6, 35.0, hz + 0.03), (1.6, 1.25, 0.03), cr),
            decal('torso', (-5.6, 35.0, hz + 0.03), (1.25, 1.6, 0.03), cr),
            decal('torso', (-5.6, 35.0, hz + 0.06), (0.7, 0.7, 0.03), '#C9424A')]
    for sg in (1, -1):
        out.append(P('torso', (sg * 5.8, 26.2, hz - 0.05), (1.5, 0.2, 0.15), cr, bevel=0.05, noise=0))   # 주머니 입구 테
    out += _over_sleeves(cr, tint(nv, -0.1), hx=3.0)
    for sg in (1, -1):
        out += R('arm%+d' % sg, (0, -12.5, 0.2), (2.97, 0.22, 2.97), cr, 0.1)               # 소매 시보리 줄
    return out


def top_puffer_mint():
    """시안 4: 민트 크롭 패딩(가로 누빔) + 흰 이너 + 검정 크로스백(사선 끈)."""
    mt = '#A9E3C8'; wt = '#FFFFFF'; bag = '#2A2630'; pink = '#F288B6'
    out = R('torso', (0, 32.2, 0), (7.4, 7.0, 4.5), wt, 0.7)                          # 이너 (25.2..39.2, 크롭 밑으로 살짝)
    out += R('torso', (0, 41.0, -0.3), (6.6, 1.3, 5.2), mt, 0.6)                        # 스탠드 칼라
    for i, y in enumerate((38.4, 34.8, 31.2, 28.2)):                                     # 누빔 띠 (크롭: 아래 26.7)
        hx = 9.2 if i % 2 == 0 else 8.9
        out += R('torso', (0, y, 0), (hx, 1.9 if i < 3 else 1.5, 5.7 if i % 2 == 0 else 5.5), tint(mt, 0.03 * (i % 2)), 1.0)
    for sg in (1, -1):
        out.append(P('torso', (sg * 2.3, 32.6, 5.4), (0.6, 7.2, 0.5), tint(mt, -0.05), bevel=0.3))   # 열린 앞여밈
    out.append(P('torso', (0, 32.6, 4.9), (1.7, 7.0, 0.5), wt, bevel=0.2, noise=0.01))
    # 크로스백: 캐릭터 왼쪽 어깨 -> 오른쪽 엉덩이
    out += [P('torso', (0.4, 32.8, 6.05), (0.42, 10.6, 0.25), bag, bevel=0.1, noise=0.0, rot=(0, 0, -30)),
            P('torso', (5.2, 40.8, 0), (0.42, 0.3, 5.9), bag, bevel=0.1, noise=0.0),
            P('torso', (0.4, 32.8, -6.05), (0.42, 10.6, 0.25), bag, bevel=0.1, noise=0.0, rot=(0, 0, -30)),
            P('torso', (-5.8, 24.2, 5.4), (2.2, 2.4, 1.2), bag, bevel=0.5, noise=0.02),
            P('torso', (-5.8, 25.4, 6.62), (2.1, 1.05, 0.05), pink, bevel=0.0, noise=0.0),
            decal('torso', (-5.8, 24.8, 6.69), (0.45, 0.3, 0.03), '#FFFFFF', emit=0.1)]
    for sg in (1, -1):                                                                     # 부푼 소매 (누빔)
        a = 'arm%+d' % sg
        out += R(a, (0, -0.6, 0), (3.6, 2.2, 3.6), mt, 1.0)
        out += R(a, (0, -4.6, 0.05), (3.35, 2.0, 3.35), tint(mt, 0.03), 1.0)
        out += R(a, (0, -8.6, 0.1), (3.4, 2.1, 3.4), mt, 1.0)
        out += R(a, (0, -11.9, 0.2), (2.7, 1.3, 2.7), tint(mt, -0.1), 0.5)
    return out


# ------------------------------------------------------------------ 사이클 5 상의 (새 몸에 맞춰 다시)
def top_hoodie(col, cord):
    rib = tint(col, -0.08)
    out = _body(col, rib, hx=8.1, hz=4.9)
    out += [P('torso', (0, 25.4, 5.05), (5.2, 2.6, 0.35), col, bevel=0.5)]
    out += _hood(col)
    for sg in (1, -1):
        out += [P('torso', (sg * 5.5, 41.0, -0.6), (1.9, 1.5, 4.6), col, bevel=SOFT),
                decal('torso', (sg * 1.9, 37.0, 4.93), (0.4, 2.8, 0.03), cord),
                P('torso', (sg * 1.9, 34.0, 5.0), (0.55, 0.65, 0.22), tint(cord, -0.15), bevel=0.15, noise=0)]
    return out + _long_sleeves(col, rib)


def top_blouse():
    col = '#FBF7F2'
    hz = 4.7
    out = _body(col, tint(col, -0.05), hx=7.9, hz=hz)
    pink = '#F58AB4'
    for sg in (1, -1):
        out += [P('torso', (sg * 2.7, 40.1, hz - 1.1), (2.8, 0.55, 1.6), col, bevel=0.5),
                decal('torso', (sg * 2.7, 39.6, hz + 0.53), (2.8, 0.2, 0.03), pink),
                P('torso', (sg * 1.9, 39.4, hz + 0.3), (1.15, 0.9, 0.4), pink, bevel=0.35, noise=0.02),
                P('torso', (sg * 0.75, 37.6, hz + 0.25), (0.45, 1.1, 0.25), tint(pink, -0.08), bevel=0.2, noise=0.02)]
    out.append(P('torso', (0, 39.3, hz + 0.45), (0.8, 0.75, 0.4), tint(pink, -0.1), bevel=0.3, noise=0.02))
    for y in (35.4, 31.8, 28.2, 24.6):
        out.append(decal('torso', (0, y, hz + 0.03), (0.42, 0.42, 0.03), '#F7C0D6'))
    out += R('torso', (0, 21.0, 0), (8.5, 0.8, hz + 0.5), tint(col, -0.03), 0.4)
    return out + _short_sleeves(col, pink, puff=True)


def top_overalls():
    tee = '#FFF6E4'; g = '#4FAE4A'
    hz = 4.7
    out = _body(tee, hx=7.9, hz=hz)
    out += R('torso', (0, 23.4, 0), (8.2, 2.2, hz + 0.3), g, 0.5)
    out += [P('torso', (0, 29.6, hz + 0.2), (5.0, 4.6, 0.4), g, bevel=0.5),
            decal('torso', (0, 30.0, hz + 0.63), (2.2, 1.5, 0.03), tint(g, -0.12))]
    for sg in (1, -1):
        out += [P('torso', (sg * 3.6, 37.2, hz + 0.15), (1.0, 3.4, 0.3), g, bevel=0.3),
                P('torso', (sg * 3.6, 40.5, 0), (1.0, 0.3, hz + 0.3), g, bevel=0.2),
                P('torso', (sg * 3.0, 33.0, -hz - 0.2), (1.0, 7.6, 0.3), g, bevel=0.3),
                P('torso', (sg * 3.6, 34.0, hz + 0.55), (0.65, 0.65, 0.2), '#F7C948', bevel=0.2, noise=0, emit=0.1)]
    return out + _short_sleeves(tee, tint(tee, -0.06))


def top_tee_stripe():
    w = '#FBF7F2'; red = '#E8483E'
    hz = 4.7
    out = _body(w, hx=7.9, hz=hz)
    for y in (24.4, 28.6, 32.8, 37.0):
        out += R('torso', (0, y, 0), (8.0, 0.85, hz + 0.1), red, 0.3)
    out += R('torso', (0, 21.6, 0), (8.1, 0.6, hz + 0.2), tint(w, -0.06), 0.3)
    out.append(P('torso', (0, 40.5, 0), (4.0, 0.25, 4.0), red, bevel=0.2))
    return out + _short_sleeves(w, red)


CAPE_CUTS = (38.0, 27.0)
CAPE_Z = -5.6


def top_cape():
    shirt = '#EEF2FA'; blue = '#3E6BD8'
    hz = 4.7
    out = _body(shirt, tint(shirt, -0.06), hx=7.9, hz=hz)
    out += [P('torso', (0, 28.6, CAPE_Z), (8.8, 11.4, 0.6), blue, bevel=0.5, sway='cape'),
            P('torso', (0, 17.6, CAPE_Z - 0.6), (9.4, 1.6, 0.6), tint(blue, -0.06), bevel=0.5, sway='cape'),
            P('torso', (0, 28.6, CAPE_Z + 0.65), (8.3, 10.9, 0.05), '#F7C948', decal=True, bevel=0, noise=0, sway='cape')]
    out += R('torso', (0, 39.6, -0.5), (9.6, 1.2, 5.4), blue, 0.5)
    out += [P('torso', (0, 41.6, -3.0), (6.0, 1.0, 1.9), tint(blue, 0.08), bevel=0.4),
            P('torso', (0, 38.8, 5.55), (1.05, 1.05, 0.3), '#F7C948', bevel=0.3, noise=0, emit=0.15)]
    return out + _long_sleeves(shirt, tint(blue, 0.1))


TOPS = {'hoodie-lavender': top_hoodie_lavender, 'cardigan-cream': top_cardigan_cream,
        'varsity-navy': top_varsity_navy, 'puffer-mint': top_puffer_mint,
        'hoodie-black': lambda: top_hoodie('#3B3644', '#C9C3CF'), 'hoodie-white': lambda: top_hoodie('#F4EDE2', '#B5AA9E'),
        'blouse-white': top_blouse, 'overalls-green': top_overalls, 'tee-stripe-red': top_tee_stripe, 'cape-blue': top_cape}


# ================================================================== bottom
WX, WZ = 7.2, 4.3          # 바지 허리 반폭/반깊이 (골반 6.8 x 3.9)


def _waist(col, hx=WX, hz=WZ):
    return R('torso', (0, 24.6, 0), (hx, 2.4, hz), col, 0.5)


def _pants(col, cuff=None, shorts=False, thigh=3.3, shin=3.0, hem=-10.4):
    out = _waist(col)
    for sg in (1, -1):
        l, sh = 'leg%+d' % sg, 'shin%+d' % sg
        if shorts:
            out += R(l, (0, -4.2, 0), (thigh + 0.3, 4.8, thigh + 0.3), col, 0.5)
            out += R(l, (0, -8.8, 0), (thigh + 0.4, 0.5, thigh + 0.4), tint(col, -0.1), 0.3)
        else:
            out += R(l, (0, -6.7, 0), (thigh, 7.7, thigh), col, 0.5)
            out += R(sh, (0, (1.2 + hem) / 2, 0), (shin, (1.2 - hem) / 2, shin), col, 0.5)
            if cuff:
                out += R(sh, (0, hem + 0.7, 0), (shin + 0.25, 0.8, shin + 0.25), cuff, 0.3)
    return out


def bottom_denim_wide():
    """시안 1: 연청 와이드 데님. 통 넓은 다리, 접어 올린 밑단, 옆 솔기, 라벤더 무지 탭."""
    col = '#A9C3E6'
    out = _waist(col, WX + 0.1, WZ + 0.1)
    out += [decal('torso', (0, 26.6, WZ + 0.13), (WX - 0.2, 0.12, 0.03), tint(col, -0.18)),
            P('torso', (-4.8, 23.0, WZ), (1.3, 0.18, 0.2), tint(col, -0.12), bevel=0.05, noise=0)]
    for sg in (1, -1):
        l, sh = 'leg%+d' % sg, 'shin%+d' % sg
        out += R(l, (0, -6.7, 0), (4.0, 7.8, 4.0), col, 0.6)
        out += R(sh, (0, -3.95, 0.1), (4.4, 5.15, 4.4), col, 0.6)                       # 밑단 -9.1: 신발 윗선(-9.2) 위에서 끝
        out += R(sh, (0, -8.25, 0.1), (4.55, 0.85, 4.55), tint(col, 0.12), 0.4)          # 접은 밑단
        out += [decal(l, (sg * 4.03, -6.7, 0), (0.03, 7.5, 0.12), tint(col, -0.15)),
                decal(sh, (sg * 4.43, -3.9, 0.1), (0.03, 4.9, 0.12), tint(col, -0.15))]
    out += [decal('leg+1', (1.8, -10.0, 4.03), (1.1, 1.1, 0.03), '#BCA8EC')]
    return out


def bottom_skirt_check():
    """시안 2: 체크 플리츠 미니스커트 (그레이지 바탕 + 갈색/크림 격자, 주름 골)."""
    base = '#C4B6A6'; dk = '#5E4C44'; lt = '#F4EEE4'
    out = R('torso', (0, 25.8, 0), (7.3, 1.4, 4.4), tint(base, -0.05), 0.4)              # 허리
    out += R('torso', (0, 22.4, 0), (8.4, 2.4, 5.4), base, 0.6, sway='skirt')
    out += R('torso', (0, 19.2, 0), (9.0, 1.2, 5.9), base, 0.6, sway='skirt')
    sk = dict(sway='skirt')
    for (hz, hx, y, hy) in ((5.4, 8.4, 22.4, 2.4), (5.9, 9.0, 19.2, 1.2)):
        for zs in (1, -1):
            for x in np.linspace(-hx + 1.2, hx - 1.2, 6):
                out.append(decal('torso', (x, y, zs * (hz + 0.03)), (0.24, hy - 0.1, 0.03), dk, **sk))     # 세로 격자
            for yy in (y - hy * 0.4, y + hy * 0.45):
                out.append(decal('torso', (0, yy, zs * (hz + 0.04)), (hx - 0.3, 0.2, 0.03), dk, **sk))
            out.append(decal('torso', (0, y, zs * (hz + 0.05)), (hx - 0.3, 0.14, 0.03), lt, **sk))
        for xs in (1, -1):
            for z in np.linspace(-hz + 1.2, hz - 1.2, 4):
                out.append(decal('torso', (xs * (hx + 0.03), y, z), (0.03, hy - 0.1, 0.14), dk, **sk))
            out.append(decal('torso', (xs * (hx + 0.04), y - hy * 0.4, 0), (0.03, 0.12, hz - 0.3), dk, **sk))
    return out


def bottom_cargo_black():
    """시안 3: 검정 카고 조거. 옆 카고 주머니, 발목 조임 시보리, 은색 체인."""
    col = '#2B2930'
    out = _waist(col)
    for sg in (1, -1):
        l, sh = 'leg%+d' % sg, 'shin%+d' % sg
        out += R(l, (0, -6.7, 0), (3.7, 7.7, 3.7), col, 0.6)
        out += R(sh, (0, -4.0, 0), (3.6, 5.2, 3.6), col, 0.6)
        out += R(sh, (0, -9.4, 0), (3.0, 0.9, 3.0), tint(col, -0.12), 0.4)              # 조임 시보리
        out += [P(l, (sg * 3.8, -9.0, 0.3), (0.45, 2.6, 2.4), tint(col, 0.07), bevel=0.3),  # 카고 주머니
                P(l, (sg * 3.9, -6.5, 0.3), (0.45, 0.5, 2.5), tint(col, 0.1), bevel=0.2)]
    for i, t in enumerate(np.linspace(0, 1, 9)):                                           # 체인 (오른쪽 엉덩이)
        z = 3.4 - 6.8 * t
        y = 24.0 - 2.6 * np.sin(np.pi * t)
        out.append(P('torso', (-7.55, y, z), (0.32, 0.32, 0.42), '#C9CED8', bevel=0.12, noise=0, emit=0.1))
    return out


def bottom_cargo_beige():
    """시안 4: 베이지 와이드 카고. 넓은 통, 옆 카고 주머니, 민트 끈 장식."""
    col = '#E3CDA6'
    out = _waist(col, WX + 0.1, WZ + 0.1)
    for sg in (1, -1):
        l, sh = 'leg%+d' % sg, 'shin%+d' % sg
        out += R(l, (0, -6.7, 0), (4.0, 7.8, 4.0), col, 0.6)
        out += R(sh, (0, -3.95, 0.1), (4.35, 5.15, 4.35), col, 0.6)
        out += R(sh, (0, -8.6, 0.1), (4.4, 0.5, 4.4), tint(col, -0.08), 0.3)
        out += [P(l, (sg * 4.1, -9.4, 0.3), (0.45, 2.8, 2.6), tint(col, -0.04), bevel=0.3),
                P(l, (sg * 4.2, -6.7, 0.3), (0.45, 0.55, 2.7), tint(col, -0.08), bevel=0.2),
                decal(sh, (sg * 4.38, -2.0, 0.1), (0.03, 2.6, 2.4), tint(col, -0.06))]
    out += [P('torso', (-2.9, 21.0, WZ + 0.35), (0.35, 2.4, 0.2), '#8FD3B6', bevel=0.1, noise=0),
            P('torso', (-2.9, 18.4, WZ + 0.4), (0.5, 0.5, 0.3), '#8FD3B6', bevel=0.15, noise=0),
            decal('torso', (0, 26.6, WZ + 0.13), (WX - 0.2, 0.12, 0.03), tint(col, -0.15))]
    return out


def bottom_skirt_pink():
    pink = '#F58AB4'
    out = R('torso', (0, 25.4, 0), (7.3, 1.8, 4.4), pink, 0.5)
    out += R('torso', (0, 21.4, 0), (8.6, 2.6, 5.6), tint(pink, 0.05), 0.6, sway='skirt')
    out += R('torso', (0, 18.8, 0), (8.9, 0.4, 5.9), '#FFF6E4', 0.3, sway='skirt')
    return out


BOTTOMS = {'denim-wide': bottom_denim_wide, 'skirt-check': bottom_skirt_check,
           'cargo-black': bottom_cargo_black, 'cargo-beige': bottom_cargo_beige,
           'pants-navy': lambda: _pants('#2E3E7A'), 'pants-black': lambda: _pants('#2B2733'), 'skirt-pink': bottom_skirt_pink,
           'shorts-brown': lambda: _pants('#8A5232', shorts=True), 'jeans-blue': lambda: _pants('#4D7CC8', cuff='#7FA6E0')}


# ================================================================== shoes (정강이 뼈, 발 y -13.5..-10.5, z -2.9..5.5)
def shoes_chunky_white():
    """흰 청키 스니커즈: 두꺼운 밑창 + 회보라 띠, 둥근 앞코, 발목 칼라, 끈."""
    w = '#FBFAF7'; sole = '#ECE8E4'; acc = '#D6D0E2'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -12.6, 1.7), (4.25, 0.95, 5.7), sole, 0.4)
        out += R(s, (0, -12.15, 1.7), (4.32, 0.18, 5.77), acc, 0.1)
        out += R(s, (0, -10.6, 1.5), (4.0, 1.4, 5.2), w, 1.0)
        out += R(s, (0, -9.4, -1.5), (3.5, 0.6, 3.0), w, 0.4)                      # 발목 칼라
        out += [P(s, (0, -9.5, 2.6), (2.1, 0.5, 2.1), tint(w, -0.03), bevel=0.3),   # 혀
                decal(s, (sg * 4.03, -10.8, 1.0), (0.03, 0.6, 3.0), acc),           # 옆 무지 패널
                decal(s, (-sg * 4.03, -10.8, 1.0), (0.03, 0.6, 3.0), acc)]
        for z in (1.6, 3.0, 4.4):
            out.append(decal(s, (0, -9.17, z), (1.9, 0.03, 0.24), '#CFC9D4'))
    return out


def shoes_loafer_socks():
    """로퍼 + 흰 니삭스 (무릎 아래까지)."""
    sock = '#F8F6F3'; blk = '#1F1B1E'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -5.6, 0), (2.7, 5.0, 2.7), sock, 0.4)
        out += R(s, (0, -1.0, 0), (2.82, 0.6, 2.82), tint(sock, -0.04), 0.3)
        out += R(s, (0, -13.05, 1.4), (3.2, 0.45, 4.6), '#3A3034', 0.2)
        out += R(s, (0, -11.6, 1.3), (3.02, 1.1, 4.4), blk, 0.9, noise=0.01)
        out += [P(s, (0, -10.55, 2.9), (3.08, 0.32, 1.0), tint(blk, 0.08), bevel=0.2, noise=0),      # 페니 스트랩
                P(s, (0, -10.2, 2.9), (1.0, 0.08, 0.34), '#E3B04B', bevel=0.05, noise=0, emit=0.2)]
    return out


def shoes_hightop_black():
    """검정 하이탑: 흰 밑창/앞코, 발목 위까지 올라오는 검정 갑피, 흰 끈, 옆 무지 띠."""
    blk = '#211E24'; w = '#F6F3EE'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -12.95, 1.5), (3.75, 0.6, 5.1), w, 0.3)
        out += R(s, (0, -10.9, 1.2), (3.55, 1.6, 4.7), blk, 0.9)
        out += R(s, (0, -8.2, -0.1), (3.15, 1.7, 3.2), blk, 0.6)                    # 발목 위
        out += R(s, (0, -11.3, 4.4), (3.5, 1.0, 1.6), w, 0.6)                       # 흰 앞코
        out += R(s, (0, -6.6, -0.1), (3.2, 0.3, 3.3), w, 0.2)                       # 윗단 테
        out += [decal(s, (sg * 3.58, -11.2, 0.4), (0.03, 0.55, 3.0), w),
                decal(s, (-sg * 3.58, -11.2, 0.4), (0.03, 0.55, 3.0), w),
                decal(s, (sg * 3.18, -8.0, -1.6), (0.03, 0.9, 0.9), '#5A5560')]
        for y in (-9.4, -8.4, -7.4):
            out.append(decal(s, (0, y, 3.13), (1.4, 0.2, 0.03), w))
    return out


def _sneaker(up, sole, lace):
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -13.05, 1.3), (3.3, 0.5, 4.6), sole, 0.3)
        out += R(s, (0, -11.6, 1.2), (3.1, 1.3, 4.35), up, 0.8)
        out += [decal(s, (0, -10.27, 2.2), (1.6, 0.03, 1.6), lace),
                decal(s, (0, -11.8, 5.58), (2.2, 0.8, 0.03), tint(up, -0.05))]
    return out


def shoes_maryjane():
    red = '#E8483E'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -9.6, 0), (2.7, 1.4, 2.7), '#FFFFFF', 0.4)
        out += R(s, (0, -13.05, 1.3), (3.2, 0.45, 4.5), '#9E2838', 0.3)
        out += R(s, (0, -11.8, 1.4), (3.0, 1.0, 4.25), red, 0.8)
        out.append(P(s, (0, -10.75, 1.8), (3.1, 0.3, 0.6), red, bevel=0.2))
        out.append(decal(s, (sg * 3.13, -10.8, 1.8), (0.03, 0.35, 0.35), '#F7C948'))
    return out


def shoes_boots():
    br = '#8A5232'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -13.0, 1.3), (3.4, 0.55, 4.7), '#4A2A1A', 0.3)
        out += R(s, (0, -10.2, 0.6), (3.2, 2.6, 3.9), br, 0.7)
        out += R(s, (0, -11.2, 2.9), (3.15, 1.6, 2.8), br, 0.7)
        out += R(s, (0, -7.4, 0), (3.45, 0.8, 3.45), tint(br, 0.12), 0.4)
    return out


SHOES = {'chunky-white': shoes_chunky_white, 'loafer-socks': shoes_loafer_socks, 'hightop-black': shoes_hightop_black,
         'sneakers-white': lambda: _sneaker('#F6F3EE', '#B9B2BE', '#9C93A3'), 'maryjane-red': shoes_maryjane,
         'boots-brown': shoes_boots, 'sneakers-black': lambda: _sneaker('#34303C', '#F2EEE8', '#BDB6C6')}


# ================================================================== hat (머리 로컬)
def hat_bucket_white():
    """시안 1: 흰 버킷햇. 둥글게 줄어드는 크라운, 아래로 기운 챙, 라벤더 무지 패치."""
    w = '#F8F6F2'
    out = R('head', (0, 25.0, -0.4), (18.8, 5.6, 18.2), w, 2.0, bevel=1.6)     # 크라운 19.4..30.6 (모서리 둥글게)
    out += R('head', (0, 31.2, -0.4), (15.6, 1.1, 15.0), tint(w, 0.03), 1.0, bevel=1.2)
    out += R('head', (0, 20.4, -0.4), (18.85, 0.75, 18.25), tint(w, -0.06), 0.6, bevel=0.4)  # 띠
    out += R('head', (0, 19.6, -0.4), (19.8, 0.7, 19.2), w, 0.5)                # 챙 뿌리
    br = tint(w, -0.02)
    out += [P('head', (0, 18.6, 21.0), (20.4, 0.6, 2.6), br, bevel=0.5, rot=(20, 0, 0)),          # 앞 챙 (짧게: 눈을 가리지 않게)
            P('head', (0, 17.9, -22.2), (20.6, 0.6, 3.4), br, bevel=0.5, rot=(-32, 0, 0)),
            P('head', (21.0, 17.9, -0.4), (3.4, 0.6, 21.6), br, bevel=0.5, rot=(0, 0, -32)),
            P('head', (-21.0, 17.9, -0.4), (3.4, 0.6, 21.6), br, bevel=0.5, rot=(0, 0, 32))]
    out += [decal('head', (-7.4, 25.4, 17.83), (2.0, 2.0, 0.03), '#BCA8EC'),
            decal('head', (-7.4, 25.4, 17.86), (1.25, 1.25, 0.03), '#D4C6F4')]
    return out


def hat_cap_black():
    """시안 3: 검정 무지 캡 (글자/로고 없음, 단추와 작은 크림 패치만). 둥근 크라운 + 긴 챙."""
    b = '#34303D'
    out = R('head', (0, 24.4, -0.6), (17.6, 5.2, 17.0), b, 3.0, bevel=1.6)     # 19.2..29.6 (둥근 돔)
    out += R('head', (0, 30.2, -0.8), (13.6, 1.2, 13.0), tint(b, 0.04), 1.0, bevel=1.0)
    out += [P('head', (0, 31.6, -0.8), (1.3, 0.4, 1.3), tint(b, 0.1), bevel=0.3),
            P('head', (0, 20.2, 21.4), (13.6, 0.6, 5.6), b, bevel=0.6, rot=(8, 0, 0)),          # 챙
            P('head', (0, 19.7, 21.2), (13.2, 0.1, 5.2), '#3C3743', bevel=0.0, rot=(8, 0, 0)),
            decal('head', (0, 23.0, 16.23), (0.16, 3.2, 0.03), tint(b, -0.4)),
            decal('head', (0, 21.2, -17.43), (4.0, 1.0, 0.03), tint(b, 0.12)),
            decal('head', (-6.4, 23.0, 16.23), (1.3, 1.0, 0.03), '#EDE3CF'),
            decal('head', (-6.4, 23.0, 16.23), (1.0, 1.3, 0.03), '#EDE3CF')]
    return out


HATS = {'bucket-white': hat_bucket_white, 'cap-black': hat_cap_black}
HAT_K = (1.38, 1.31, 1.38)         # 사이클 5 모자: 머리 배율(HK)보다 가로/깊이를 조금 더 키워 새 머리카락 볼륨을 덮는다
for _tid, _fn in V5.HATS.items():
    HATS[_tid] = (lambda f=_fn: scaled(f(), HAT_K))

PARTS = {
    'skin': {k: (lambda k=k: skin(k)) for k in SKINS},
    'face': {k: (lambda k=k: face(k)) for k in ('basic', 'smile', 'wink', 'sleepy')},
    'hair': HAIRS, 'top': TOPS, 'bottom': BOTTOMS, 'shoes': SHOES, 'hat': HATS,
}


# ================================================================== 프록시 (레이어 분리, 그림자 받는 면)
def proxy_body():
    """옷 입은 몸 근사 (머리 제외): hair/hat 뒤쪽 판정용. 망토/가방 두께까지 뒤로 넓힘."""
    out = [P('torso', (0, 31.4, -0.8), (9.6, 10.0, 6.6), '#000000'),
           P('torso', (0, 19.8, -0.8), (9.4, 2.6, 6.6), '#000000')]
    for sg in (1, -1):
        out += [P('arm%+d' % sg, (0, -7.6, 0.1), (3.8, 9.4, 3.8), '#000000'),
                P('leg%+d' % sg, (0, -6.7, 0), (4.5, 7.9, 4.5), '#000000'),
                P('shin%+d' % sg, (0, -6.6, 1.2), (4.7, 7.4, 5.6), '#000000')]
    return out


def proxy_legs():
    """바지/신발 근사: top(망토) 뒤쪽 판정용."""
    out = [P('torso', (0, 23.0, 0), (7.3, 1.8, 4.35), '#000000')]          # 바지 허리 안쪽 (밖으로 나온 상의 밑단은 앞 레이어로)
    for sg in (1, -1):
        out += [P('leg%+d' % sg, (0, -6.7, 0), (4.4, 7.9, 4.4), '#000000'),
                P('shin%+d' % sg, (0, -6.6, 1.2), (4.6, 7.4, 5.6), '#000000')]
    return out


def proxy_hairshell():
    """머리카락 껍데기 근사: 모자 뒤쪽 판정 + 모자 그림자 받는 면."""
    return [P('head', (0, 14.0, -1.0), (16.8, 15.0, 13.8), '#000000')]      # 앞면 z 12.8 = 얼굴 면, 모든 모자 크라운보다 안쪽


PROXIES = {'body': proxy_body, 'legs': proxy_legs, 'hairshell': proxy_hairshell}


# ================================================================== 포즈
# 사이클 6 포즈 매개변수 (사이클 7에서 새 비율에 맞춰 값만 조정):
#   pivot 'hip'  : 몸 기울기(lean)를 엉덩이 높이 기준으로 (기본: 발바닥 높이 기준)
#   sink         : 몸통(+머리, 팔)을 엉덩이 관절보다 아래로 내림 (숙이기에서 키 줄이기)
#   ground       : None = 자동 접지(낮은 발바닥을 y=0), 숫자 = 고정 높이(점프/하강: 몸 중심 유지, 발은 떠 있음)
#   feet_z       : 숫자면 두 발바닥 중심 z 평균이 이 값이 되게 몸 전체를 앞뒤로 옮김 (숙이기: 발이 기준점 위)
#   legsplay     : 다리를 옆으로 벌림(도, +바깥). asplay: 팔별 벌림(도) - 없으면 splay
#   hang         : 머리카락 늘어짐(월드 기준 각도, 0 = 중력 방향으로 곧게, + = 뒤/위로 날림).
#                  머리 로컬 y < HANG_CUTS[0] 부분을 잘라 2마디로 나눠 돌린다. 숫자면 두 마디에 고르게,
#                  (w1, w2) 튜플이면 마디별 월드 각도 (숙이기: 끝마디가 바닥에 닿아 뒤로 눕는다).
#   cape         : 망토 등판(sway='cape' 상자) 월드 기준 각도. 어깨 뒤 축 + 2마디.
#   squash       : (sy, sxz) 몸통 뼈 상자를 엉덩이 높이 기준으로 세로 sy, 가로/깊이 sxz 배
#   skirt_lift   : 치마 단(sway='skirt')을 수평으로 되돌리고 위로 올림 (숙이기: 치마가 지면을 뚫지 않게)
HANG_CUTS = (7.7, -3.8)
NEW_FRAMES = ('jump', 'fall', 'crouch')


def pose_frame(name):
    """각도 + = 앞으로. shin 은 무릎 굽힘(- = 발이 뒤로)."""
    p = dict(breathe=0.0, arm={1: 0.0, -1: 0.0}, leg={1: 0.0, -1: 0.0}, shin={1: 0.0, -1: 0.0},
             splay=4.0, head=0.0, lean=0.0,
             pivot=None, sink=0.0, ground=None, feet_z=None, legsplay=None, asplay=None, hang=None, cape=None,
             skirt_lift=None, squash=None, hang_cuts=None)
    if name in ('front', 'front_b', 'back'):
        p['legsplay'] = 3.0                      # 정면/뒤: 살짝 벌린 A 자세 (시안)
        p['splay'] = 6.0
    if name == 'front_b':
        p['breathe'] = -0.6
    walk = {'walk0': ((26, -8), (-22, -30), 34, -1.5), 'walk1': ((-4, -2), (14, -44), 12, 0.0),
            'walk2': ((-22, -30), (26, -8), -34, -1.5), 'walk3': ((14, -44), (-4, -2), -12, 0.0)}
    if name in walk:
        (t1, s1), (t2, s2), arm, head = walk[name]
        p['leg'] = {1: t1, -1: t2}
        p['shin'] = {1: s1, -1: s2}
        p['arm'] = {1: -arm, -1: arm}
        p['splay'] = 3.0
        p['head'] = head
        p['lean'] = 2.5
    POSES6 = {
        'jump': dict(leg={1: 62.0, -1: 54.0}, shin={1: -78.0, -1: -72.0}, arm={1: 58.0, -1: 66.0},
                     asplay={1: 16.0, -1: 16.0}, lean=6.0, head=-5.0, pivot='hip', ground=3.0,
                     hang=0.0, cape=10.0),
        'fall': dict(leg={1: 10.0, -1: -12.0}, shin={1: -16.0, -1: -8.0}, legsplay=6.0, arm={1: 40.0, -1: -35.0},
                     asplay={1: 62.0, -1: 62.0}, lean=-4.0, head=3.0, pivot='hip', ground=1.0,
                     hang=24.0, cape=40.0),
        'crouch': dict(leg={1: 106.0, -1: 102.0}, shin={1: -128.0, -1: -124.0}, arm={1: 72.0, -1: 66.0},
                       splay=8.0, lean=24.0, head=-20.0, pivot='hip', sink=0.5, feet_z=1.0, squash=(0.85, 1.05),
                       hang=(2.0, 75.0), hang_cuts=(7.7, -12.2), cape=40.0, skirt_lift=3.0),
    }
    if name in POSES6:
        p.update(POSES6[name])
    return p


def _xf_point(R, t, v):
    return t + R @ np.asarray(v, float)


def bone_xf(pose):
    br = pose['breathe']
    I = np.eye(3)
    Rl = rot_x(pose['lean'])
    xf = {}
    legs = {}
    for sg in (1, -1):
        Rt = rot_x(-pose['leg'][sg])
        if pose.get('legsplay'):
            Rt = rot_z(sg * pose['legsplay']) @ Rt
        Rs = Rt @ rot_x(-pose['shin'][sg])
        legs[sg] = (Rt, Rs)
    # 땅에 닿게: 두 발바닥 중 낮은 쪽을 y=0 (발 앞뒤 끝도 고려)
    low = []
    soles = []
    for sg in (1, -1):
        Rt, Rs = legs[sg]
        hip = np.array([sg * HIP[0], HIP[1] + LEGX, 0])
        knee = hip + Rt @ np.array(KNEE)
        for dz in FOOT_DZ:
            low.append((knee + Rs @ (np.array(SOLE) + [0, 0, dz - SOLE[2]]))[1])
        soles.append(knee + Rs @ np.array(SOLE))
    b = -min(low) if pose.get('ground') is None else float(pose['ground'])
    dz = 0.0 if pose.get('feet_z') is None else float(pose['feet_z']) - float(np.mean([s[2] for s in soles]))
    xf['root'] = (I, np.array([0, b, dz]))
    if pose.get('pivot') == 'hip':
        hy = np.array([0, HIP[1], 0.0])
        xf['torso'] = (Rl, np.array([0, b + LEGX + br * 0.5 - pose['sink'], dz]) + hy - Rl @ hy)
    else:
        xf['torso'] = (Rl, np.array([0, b + LEGX + br * 0.5, 0.0]))
    tor_R, tor_t = xf['torso']
    sq = (lambda v: squash_pt(v, pose['squash'])) if pose.get('squash') else (lambda v: v)
    xf['head'] = (Rl @ rot_x(pose['head']), tor_t + Rl @ sq(stretch_pt(HEAD_PIVOT) + [0, br * 0.5, 0]))
    for sg in (1, -1):
        spl = pose['asplay'][sg] if pose.get('asplay') else pose['splay']
        Ra = Rl @ rot_z(sg * spl) @ rot_x(-pose['arm'][sg])
        xf['arm%+d' % sg] = (Ra, tor_t + Rl @ sq(stretch_pt((sg * SHOULDER[0], SHOULDER[1], 0)) + [0, br * 0.1, 0]))
        Rt, Rs = legs[sg]
        hip = np.array([sg * HIP[0], HIP[1] + LEGX + b, dz])
        xf['leg%+d' % sg] = (Rt, hip)
        xf['shin%+d' % sg] = (Rs, hip + Rt @ np.array(KNEE))
    return xf


def squash_pt(v, sq):
    sy, sxz = sq
    v = np.asarray(v, float)
    return np.array([v[0] * sxz, HIP[1] + (v[1] - HIP[1]) * sy, v[2] * sxz])


def stretch_pt(v):
    """몸통 로컬 점을 엉덩이 높이 기준으로 세로 TORSO_SY 배 (모든 프레임 공통)."""
    v = np.asarray(v, float)
    return np.array([v[0], HIP[1] + (v[1] - HIP[1]) * TORSO_SY, v[2]])


def _sy(y):
    return HIP[1] + (y - HIP[1]) * TORSO_SY


def stretch_defs(defs):
    out = []
    for d in defs:
        if d['bone'] == 'torso':
            hx, hy, hz = d['h']
            d = dict(d, c=tuple(stretch_pt(d['c'])), h=(hx, hy * TORSO_SY, hz))
        out.append(d)
    return out


def squash_defs(defs, pose):
    """몸통 뼈 상자를 squash (위치와 크기). 해당 없으면 defs 그대로."""
    defs = stretch_defs(defs)
    if not pose.get('squash'):
        return defs
    sy, sxz = pose['squash']
    out = []
    for d in defs:
        if d['bone'] == 'torso':
            hx, hy, hz = d['h']
            d = dict(d, c=tuple(squash_pt(d['c'], pose['squash'])), h=(hx * sxz, hy * sy, hz * sxz))
        out.append(d)
    return out


def _sq_y(y, pose):
    return HIP[1] + (y - HIP[1]) * pose['squash'][0] if pose.get('squash') else y


def _hinge(xf, bone, pivot, ang):
    """bone 로컬의 pivot 을 지나는 x축으로 ang 도 돌린 뼈 (R, t)."""
    R, t = xf[bone]
    Ra = rot_x(ang)
    p = np.asarray(pivot, float)
    return R @ Ra, t + R @ (p - Ra @ p)


def _chain(defs, sel, base, cuts, angs, xf, prefix, zpiv=None):
    """sel(d) 인 상자를 bone 로컬 y 의 cuts(내림차순) 에서 잘라 마디마다 angs 만큼 더 돌린다.
    마디 축은 (y=cut, z=zpiv 또는 상자 중심 z) 를 지나는 x축. 아래 조각은 위로 0.6 겹치고 가로/깊이 0.05씩 키워 이음새를 덮는다.
    rot 이 있는 상자(헤어핀 등)는 자르지 않고 중심이 속한 마디로 통째로 옮긴다."""
    out = []
    for d in defs:
        if d['bone'] != base or not sel(d):
            out.append(d); continue
        (cx, cy, cz), (hx, hy, hz) = d['c'], d['h']
        y0, y1 = cy - hy, cy + hy
        pz = cz if zpiv is None else zpiv
        keys = [base]
        for i, (c, a) in enumerate(zip(cuts, angs)):
            k = '%s%d@%.3f' % (prefix, i + 1, pz)
            if k not in xf:
                xf[k] = _hinge(xf, keys[-1], (0, c, pz), a)
            keys.append(k)
        if d.get('rot'):
            out.append(dict(d, bone=keys[sum(1 for c in cuts if cy < c)]))
            continue
        bnd = [c for c in cuts if y0 < c - 0.8 and y1 > c + 0.3]
        edges = [y1] + bnd + [y0]
        for top, bot in zip(edges[:-1], edges[1:]):
            mid = (top + bot) / 2
            seg = sum(1 for c in cuts if mid < c)
            e = dict(d); e['bone'] = keys[seg]
            if top < y1:
                top = top + 0.6
                e['h'] = (hx + 0.05 * seg, (top - bot) / 2, hz + 0.05 * seg)
            else:
                e['h'] = (hx, (top - bot) / 2, hz)
            e['c'] = (cx, (top + bot) / 2, cz)
            out.append(e)
    return out


def sway_defs(defs, cat, pose, xf):
    """hang/cape/skirt_lift 포즈에서 늘어지는 부분을 새 뼈로 옮긴다 (xf 에 뼈 추가). 해당 없으면 defs 그대로."""
    if cat == 'hair' and pose.get('hang') is not None:
        hd = pose['lean'] + pose['head']
        h = pose['hang']
        w1, w2 = (h if isinstance(h, tuple) else ((hd + h) / 2, h))      # 마디별 월드 각도
        cuts = pose.get('hang_cuts') or HANG_CUTS
        return _chain(defs, lambda d: d['c'][1] - d['h'][1] < cuts[0] - 0.8, 'head', cuts, (w1 - hd, w2 - w1), xf, 'hang')
    defs = squash_defs(defs, pose)
    if cat == 'top' and pose.get('cape') is not None and any(d.get('sway') == 'cape' for d in defs):
        a = pose['cape'] - pose['lean']
        cuts = tuple(_sq_y(_sy(c), pose) for c in CAPE_CUTS)
        zp = CAPE_Z * (pose['squash'][1] if pose.get('squash') else 1)
        return _chain(defs, lambda d: d.get('sway') == 'cape', 'torso', cuts, (a / 2, a / 2), xf, 'cape', zpiv=zp)
    if cat == 'bottom' and pose.get('skirt_lift') is not None and any(d.get('sway') == 'skirt' for d in defs):
        if 'skirt' not in xf:
            R, t = _hinge(xf, 'torso', (0, _sq_y(_sy(SKIRT_Y), pose), 0), -pose['lean'])
            xf['skirt'] = (R, t + np.array([0, pose['skirt_lift'], 0.0]))
        return [dict(d, bone='skirt') if d.get('sway') == 'skirt' else d for d in defs]
    return defs


def _local_rot(r):
    rx, ry, rz = r
    return rot_z(rz) @ rot_y(ry) @ rot_x(rx)


def make_boxes(defs, xf, layer, tag, back_view=False):
    out = []
    for d in defs:
        R, t = xf[d['bone']]
        kw = {k: d[k] for k in ('bevel', 'decal', 'noise', 'emit') if k in d}
        Rb = R @ _local_rot(d['rot']) if d.get('rot') else R
        out.append(Box(_xf_point(R, t, d['c']), d['h'], Rb, d['col'], layer, tag=tag, **kw))
    return out


def assemble(outfit, frame):
    """outfit: {cat: id}. 반환: Box 목록 (tag = 파츠 키)."""
    pose = pose_frame(frame)
    xf = bone_xf(pose)
    boxes = []
    for cat in CATS:
        pid = outfit.get(cat)
        if not pid or pid == 'none':
            continue
        boxes += make_boxes(sway_defs(PARTS[cat][pid](), cat, pose, xf), xf, cat, cat)
    return boxes


def proxy_boxes(kind, frame):
    pose = pose_frame(frame)
    xf = bone_xf(pose)
    return make_boxes(squash_defs(PROXIES[kind](), pose), xf, 'proxy', 'proxy')
