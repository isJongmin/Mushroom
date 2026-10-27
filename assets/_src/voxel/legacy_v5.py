"""[사이클 7 보관용] 사이클 5~6 복셀 캐릭터 모델 원본. model.py가 머리카락(HAIRS)과 모자(HATS) 형상만
가져다 새 머리 크기(HK배)로 키워 쓴다. 이 파일은 수정하지 않는다.

원래 설명: 버섯마을 복셀 캐릭터 모델 (사이클 5). 단위 = 복셀 1칸 (시트 2.75px, 월드 약 1.83단위).

캐릭터 로컬 좌표: +x = 캐릭터의 왼쪽(정면에서 화면 오른쪽), +y 위, +z 앞, 발바닥 y=0.
뼈: root, torso, head, arm+/arm-, leg+/leg-(허벅지), shin+/shin-(정강이, 무릎 아래).
파츠 함수는 dict 목록(bone, c, h, col, ...)을 돌려주고 assemble()이 포즈를 적용해 Box 목록을 만든다.
"""
import numpy as np
from vox import Box, rot_x, rot_z

# ------------------------------------------------------------------ 치수 (마네킹, 통통한 치비)
HEAD_PIVOT = (0, 22.5, 0)
HEAD_H = (11.0, 10.0, 10.0)      # 머리 22 x 20 x 20, 머리 로컬 y 0..20, 앞면 z=10
SHOULDER = (8.9, 20.4, 0)
HIP = (3.5, 10.0, 0)
KNEE = (0, -5.0, 0)              # 허벅지 뼈 기준 무릎
SOLE = (0, -5.0, 1.0)            # 정강이 뼈 기준 발바닥 중앙

LABELS = {
    'skin': [('light', '밝은 피부'), ('medium', '보통 피부'), ('dark', '진한 피부')],
    'face': [('basic', '기본'), ('smile', '웃음'), ('wink', '윙크'), ('sleepy', '졸린 눈')],
    'hair': [('black-short', '검은 짧은 머리'), ('brown-short', '밤색 짧은 머리'), ('blonde-spiky', '금발 뻗친 머리'),
             ('pink-long', '분홍 긴 머리'), ('sky-bob', '하늘색 단발'), ('tan-ponytail', '갈색 포니테일'),
             ('black-twintail', '검은 양갈래'), ('mint-curly', '민트 곱슬')],
    'top': [('hoodie-black', '검은 후드티'), ('hoodie-white', '흰 후드티'), ('blouse-white', '흰 블라우스'),
            ('overalls-green', '초록 멜빵'), ('tee-stripe-red', '빨간 줄무늬 티'), ('cape-blue', '파란 망토 셔츠')],
    'bottom': [('pants-navy', '남색 바지'), ('pants-black', '검은 바지'), ('skirt-pink', '분홍 치마'),
               ('shorts-brown', '갈색 반바지'), ('jeans-blue', '청바지')],
    'shoes': [('sneakers-white', '흰 운동화'), ('maryjane-red', '빨간 메리제인'), ('boots-brown', '갈색 부츠'),
              ('sneakers-black', '검은 운동화')],
    'hat': [('none', '없음'), ('cap-white', '흰 야구모자'), ('mushroom-red', '빨간 버섯 모자'),
            ('explorer-brown', '갈색 탐험가 모자'), ('beanie-yellow', '노란 비니'), ('ribbon-pink', '분홍 리본')],
}
PRESETS = [
    ('후드 소년', dict(skin='light', hair='black-short', face='basic', top='hoodie-black', bottom='pants-navy', shoes='sneakers-white', hat='none')),
    ('분홍 소녀', dict(skin='light', hair='pink-long', face='basic', top='blouse-white', bottom='skirt-pink', shoes='maryjane-red', hat='none')),
    ('모자 소년', dict(skin='light', hair='brown-short', face='smile', top='hoodie-white', bottom='pants-black', shoes='sneakers-black', hat='cap-white')),
    ('버섯 꼬마', dict(skin='light', hair='blonde-spiky', face='basic', top='overalls-green', bottom='jeans-blue', shoes='boots-brown', hat='mushroom-red')),
    ('하늘 마법사', dict(skin='medium', hair='sky-bob', face='wink', top='cape-blue', bottom='pants-navy', shoes='boots-brown', hat='none')),
    ('탐험가', dict(skin='dark', hair='black-twintail', face='smile', top='tee-stripe-red', bottom='shorts-brown', shoes='sneakers-white', hat='explorer-brown')),
]
CATS = ['skin', 'face', 'hair', 'top', 'bottom', 'shoes', 'hat']

SKINS = {'light': '#FAD3BA', 'medium': '#E2A982', 'dark': '#A3684A'}
SOFT = 0.85      # 몸/옷 베벨 폭 (둥글게)
HAIRB = 0.45     # 머리카락 베벨 (큐브 느낌 유지)


def P(bone, c, h, col, **kw):
    return dict(bone=bone, c=c, h=h, col=col, **kw)


def R(bone, c, h, col, r=0.6, **kw):
    """모서리를 한 칸 깎은 상자 (3개 상자 십자 결합) - 각진 느낌 완화."""
    hx, hy, hz = h
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


# ================================================================== skin (마네킹)
def skin(tone):
    s = SKINS[tone]
    k = dict(noise=0.012)
    out = [P('head', (0, 10, 0), HEAD_H, s, bevel=0.5, **k),
           P('torso', (0, 21.6, 0), (3.6, 1.4, 3.6), s, **k)]
    out += R('torso', (0, 15.8, 0), (7.0, 5.9, 4.2), s, 0.7, **k)
    out += R('torso', (0, 10.0, 0), (6.6, 1.3, 4.0), s, 0.5, **k)
    for sg in (1, -1):
        a, l, sh = 'arm%+d' % sg, 'leg%+d' % sg, 'shin%+d' % sg
        out += R(a, (0, -4.3, 0), (2.4, 4.6, 2.4), s, 0.5, **k)
        out += R(a, (0, -10.7, 0.2), (2.8, 2.5, 2.8), s, 0.8, **k)          # 뭉툭한 손
        out += R(l, (0, -2.5, 0), (3.0, 2.7, 3.0), s, 0.5, **k)
        out += R(sh, (0, -2.4, 0), (2.9, 2.6, 2.9), s, 0.5, **k)
        out += R(sh, (0, -4.3, 1.0), (3.2, 0.8, 4.2), s, 0.5, **k)          # 발
    return out


# ================================================================== face (머리 앞면 데칼)
FZ = 10.0
D = dict(decal=True, bevel=0, noise=0.0)
EYE_X = 5.0
EYE_Y = 7.9


def _eye_open(ex, sg):
    """큰 세로 눈 (5.0 x 7.4칸, 모서리 둥글게), 갈색 그라데이션 홍채, 큰 하이라이트 + 반사점 (발광)."""
    y = EYE_Y
    return [
        P('head', (ex, y, FZ + 0.03), (2.5, 3.2, 0.03), '#24161C', **D),
        P('head', (ex, y, FZ + 0.03), (1.9, 3.7, 0.03), '#24161C', **D),
        P('head', (ex + sg * 2.45, y + 3.0, FZ + 0.03), (0.75, 0.45, 0.03), '#24161C', **D),   # 바깥 속눈썹
        P('head', (ex, y - 1.0, FZ + 0.06), (1.8, 2.3, 0.03), '#4A2A26', **D),               # 홍채
        P('head', (ex, y - 2.3, FZ + 0.08), (1.45, 1.0, 0.03), '#8A5638', **D),              # 아래 호박색
        P('head', (ex, y - 2.95, FZ + 0.10), (0.95, 0.42, 0.03), '#C88E5A', **D),            # 아래 반사
        P('head', (ex - 0.8, y + 1.75, FZ + 0.12), (1.15, 1.2, 0.03), '#FFFFFF', emit=0.9, **D),   # 큰 하이라이트
        P('head', (ex + 1.05, y - 1.5, FZ + 0.12), (0.5, 0.5, 0.03), '#FFFFFF', emit=0.8, **D),     # 작은 반사점
        P('head', (ex - 1.35, y - 0.4, FZ + 0.12), (0.28, 0.28, 0.03), '#FFF4F0', emit=0.6, **D),   # 반짝
    ]


def _eye_arc(ex):
    """^ 모양 감은 눈."""
    y = EYE_Y - 0.4
    c = '#2A1A20'
    return [P('head', (ex - 1.9, y - 0.9, FZ + 0.03), (0.75, 0.5, 0.03), c, **D),
            P('head', (ex - 0.95, y + 0.0, FZ + 0.03), (0.6, 0.5, 0.03), c, **D),
            P('head', (ex, y + 0.45, FZ + 0.03), (0.75, 0.5, 0.03), c, **D),
            P('head', (ex + 0.95, y + 0.0, FZ + 0.03), (0.6, 0.5, 0.03), c, **D),
            P('head', (ex + 1.9, y - 0.9, FZ + 0.03), (0.75, 0.5, 0.03), c, **D)]


def _blush(big=False):
    w = 2.1 if big else 1.8
    return [P('head', (sg * 7.9, 3.5, FZ + 0.03), (w, 0.85, 0.03), '#F4949F', emit=0.15, **D) for sg in (1, -1)]


def face(kind):
    out = []
    if kind == 'basic':
        for sg in (1, -1):
            out += _eye_open(sg * EYE_X, sg)
        out += _blush()
        out.append(P('head', (0, 2.2, FZ + 0.03), (0.8, 0.4, 0.03), '#A8475A', **D))
    elif kind == 'smile':
        for sg in (1, -1):
            out += _eye_arc(sg * EYE_X)
        out += _blush(True)
        out += [P('head', (0, 2.3, FZ + 0.03), (1.4, 0.85, 0.03), '#8E3346', **D),
                P('head', (0, 1.85, FZ + 0.06), (0.9, 0.4, 0.03), '#F07A8A', **D)]
    elif kind == 'wink':
        out += _eye_open(EYE_X, 1)
        out += _eye_arc(-EYE_X)
        out += _blush()
        out += [P('head', (0, 2.2, FZ + 0.03), (1.0, 0.35, 0.03), '#A8475A', **D),
                P('head', (1.15, 2.6, FZ + 0.03), (0.35, 0.35, 0.03), '#A8475A', **D),
                P('head', (-1.15, 2.6, FZ + 0.03), (0.35, 0.35, 0.03), '#A8475A', **D)]
    elif kind == 'sleepy':
        for sg in (1, -1):
            ex = sg * EYE_X
            out += [P('head', (ex, 6.1, FZ + 0.03), (2.5, 1.7, 0.03), '#24161C', **D),
                    P('head', (ex, 7.9, FZ + 0.03), (2.8, 0.38, 0.03), '#24161C', **D),          # 눈꺼풀 선
                    P('head', (ex, 5.6, FZ + 0.06), (1.8, 1.1, 0.03), '#5A3428', **D),
                    P('head', (ex, 4.9, FZ + 0.08), (1.2, 0.4, 0.03), '#A06C48', **D),
                    P('head', (ex - 0.8, 6.6, FZ + 0.12), (0.6, 0.5, 0.03), '#FFFFFF', emit=0.8, **D)]
        out += _blush()
        out.append(P('head', (0, 2.2, FZ + 0.03), (0.55, 0.5, 0.03), '#A8475A', **D))
    return out


# ================================================================== hair
class HairKit:
    """머리 로컬 좌표 헬퍼. 껍데기(정수리/뒤/옆/앞머리 바탕) + 덩어리."""

    def __init__(self, col, seed, noise=0.07):
        self.col, self.r, self.out = col, _rng(seed), []
        self.kw = dict(noise=noise, bevel=HAIRB)

    def box(self, c, h, k=0.0, **kw):
        kk = dict(self.kw); kk.update(kw)
        self.out.append(P('head', c, h, tint(self.col, k), **kk))

    def chunk(self, c, h, lo=-0.10, hi=0.14, **kw):
        self.box(c, h, self.r.uniform(lo, hi), **kw)

    def u(self, a, b):
        return self.r.uniform(a, b)

    def shell(self, side_bottom=8.0, back_bottom=3.0, side_front=3.0, top=20.7):
        self.box((0, top, -0.5), (11.8, 1.7, 11.0))
        yb = back_bottom
        self.box((0, (yb + 21) / 2, -10.95), (11.7, (21 - yb) / 2, 1.25))
        zf = side_front
        for sg in (1, -1):
            self.box((sg * 11.85, (side_bottom + 21) / 2, (zf - 10.8) / 2), (1.25, (21 - side_bottom) / 2, (zf + 10.8) / 2))
        self.box((0, 17.6, 10.85), (11.7, 2.6, 1.2))     # 앞머리 바탕 (y 15..20.2)

    def bangs(self, strands, z=11.2, top=16.6, depth=1.25):
        for x, yb, hw in strands:
            self.chunk((x, (yb + top) / 2, z), (hw, (top - yb) / 2, depth), -0.08, 0.06)

    def shingles(self, rows, face, lo=-0.12, hi=0.10, size=(1.8, 3.2), hy=(1.6, 2.5), back=None):
        """face: 'back' or ('side', sg). rows: [(y, ext)]."""
        for row, (y, ext) in enumerate(rows):
            if face == 'back':
                xs = np.cumsum(self.r.uniform(3.6, 6.2, 6)) - 12.5 - self.u(0, 2)
                for x in xs[xs < 10.6]:
                    self.chunk((x, y + self.u(-1.0, 1.0), -(ext + self.u(-0.4, 0.4))),
                               (self.u(*size), self.u(*hy), self.u(1.0, 1.6)), lo - row * 0.03, hi,
                               **({'back': True} if back is not None and y < back else {}))
            else:
                sg = face[1]
                zs = np.cumsum(self.r.uniform(3.8, 5.6, 4)) - 11.5 - self.u(0, 1)
                for z in zs[zs < 1.4]:
                    hz = min(self.u(*size), 2.8 - z)          # 앞끝 z <= 2.8 : 뺨/눈을 가리지 않게
                    self.chunk((sg * (ext + self.u(-0.4, 0.4)), y + self.u(-1.0, 0.9), z),
                               (self.u(1.1, 1.6), self.u(*hy), hz), lo - row * 0.03, hi,
                               **({'back': True} if back is not None and y < back else {}))

    def top_chunks(self, n=4, y0=22.3, dome=1.6, size=(1.9, 3.3), hy=(1.2, 2.0), spread=8.4, jit=1.3):
        for gx in np.linspace(-spread, spread, n):
            for gz in np.linspace(-spread, spread, n):
                mid = 1.0 - (abs(gx) + abs(gz)) / 20
                self.chunk((gx + self.u(-jit, jit), y0 + mid * dome + self.u(-0.5, 0.8), gz + self.u(-jit, jit)),
                           (self.u(*size), self.u(*hy), self.u(*size)))


def hair_black_short():
    """참고 소년: 검은 곱슬 덩어리, 이마를 덮는 2겹 앞머리, 옆은 뺨을 가리지 않게 뒤로."""
    k = HairKit('#30231F', 7)
    k.shell(side_bottom=9.5, back_bottom=2.5, side_front=2.5)
    k.top_chunks()
    for x in (-8.6, -4.3, 0.0, 4.3, 8.6):
        k.chunk((x + k.u(-0.5, 0.5), 20.0 + k.u(-0.3, 0.8), 11.2 + k.u(0.2, 1.0)), (k.u(2.2, 2.7), k.u(1.6, 2.1), k.u(1.3, 1.8)))
    k.bangs([(-9.6, 13.4, 2.0), (-5.6, 12.5, 1.9), (-1.8, 13.0, 1.9), (2.0, 12.4, 1.9), (5.8, 13.0, 1.9), (9.6, 13.6, 2.0)])
    k.bangs([(-7.6, 14.2, 1.9), (-3.7, 13.9, 1.8), (0.1, 14.4, 1.8), (3.9, 14.0, 1.8), (7.7, 14.5, 1.8)], z=12.0, top=17.8, depth=0.9)
    for sg in (1, -1):
        k.shingles([(18.2, 13.5), (14.0, 13.1), (10.4, 12.7)], ('side', sg))
        k.chunk((sg * 12.9, 16.6, 1.0), (1.3, 2.2, 1.6))
        k.chunk((sg * 11.6, 10.6, 1.0), (1.0, 1.8, 1.5))          # 짧은 구레나룻 (귀 앞, 뺨은 열어 둠)
    k.shingles([(18.6, 13.3), (14.4, 13.0), (10.4, 12.7), (6.4, 12.3)], 'back')
    for c, h in [((-12.8, 21.6, 0.0), (1.8, 1.6, 2.0)), ((13.2, 20.8, -3.0), (1.9, 1.5, 2.1)),
                 ((-3.0, 25.4, -2.5), (1.6, 1.3, 1.8)), ((4.8, 25.0, 1.5), (1.5, 1.2, 1.6)),
                 ((9.6, 23.6, 7.0), (1.6, 1.4, 1.6)), ((-9.8, 23.4, -8.0), (1.7, 1.4, 1.7)),
                 ((0.5, 22.8, -13.2), (1.8, 1.6, 1.3)), ((-13.4, 13.5, -6.0), (1.3, 1.6, 1.8))]:
        k.chunk(c, h)
    return k.out


def hair_brown_short():
    """밤색 짧은 머리: 단정한 큰 판, 옆 가르마로 쓸린 앞머리, 정수리 더듬이."""
    k = HairKit('#7A4A2E', 21, noise=0.05)
    k.shell(side_bottom=9.5, back_bottom=3.5, side_front=2.5)
    k.top_chunks(n=3, y0=22.0, dome=1.0, size=(3.0, 4.0), hy=(1.0, 1.5), spread=7.5, jit=0.8)
    # 앞쪽 볼륨 (오른쪽으로 쓸림)
    k.box((-2.0, 20.6, 11.3), (9.8, 1.8, 1.5), 0.06)
    k.box((4.0, 21.8, 11.0), (6.0, 1.2, 1.4), 0.10)
    k.bangs([(-9.6, 12.6, 2.0), (-5.6, 13.0, 2.0), (-1.6, 13.6, 2.0), (2.4, 14.2, 2.0), (6.4, 14.8, 2.0), (10.0, 15.2, 1.6)])
    k.bangs([(-7.8, 13.4, 1.6), (-3.8, 14.0, 1.5)], z=12.0, top=18.0, depth=0.9)
    for sg in (1, -1):
        k.shingles([(17.6, 13.2), (13.2, 12.8)], ('side', sg), size=(2.6, 3.4), hy=(2.0, 2.6))
    k.shingles([(18.0, 12.9), (13.2, 12.6), (8.4, 12.2)], 'back', size=(2.6, 3.6), hy=(2.0, 2.6))
    k.box((1.0, 24.4, 2.5), (0.8, 1.3, 0.8), 0.05)
    k.box((2.1, 25.8, 3.2), (0.8, 0.9, 0.8), 0.12)
    return k.out


def hair_blonde_spiky():
    """금발 뻗친 머리: 불꽃처럼 위/옆/뒤로 뻗은 굵은 덩어리(3단으로 좁아짐), 아래로 뾰족한 앞머리."""
    k = HairKit('#F2C14E', 33, noise=0.06)
    k.shell(side_bottom=10.0, back_bottom=4.0, side_front=2.5)
    k.top_chunks(n=3, y0=22.0, dome=0.8, size=(3.0, 3.8), hy=(1.0, 1.4), spread=7.0, jit=0.6)
    spikes = [((-4.5, 23.0, 3.5), (-0.3, 1, 0.6)), ((3.5, 23.4, 4.0), (0.3, 1, 0.5)), ((0, 23.6, -2.0), (0, 1, -0.2)),
              ((-7.0, 23.0, -5.0), (-0.6, 0.9, -0.5)), ((7.0, 23.0, -4.5), (0.6, 0.9, -0.5)),
              ((-10.5, 20.0, 1.5), (-1, 0.6, 0.2)), ((10.5, 20.0, 1.0), (1, 0.6, 0.2)),
              ((-5.0, 16.0, -11.0), (-0.3, 0.2, -1)), ((5.0, 16.0, -11.0), (0.3, 0.2, -1)),
              ((0.0, 10.0, -11.0), (0, -0.3, -1)), ((-11.0, 14.0, -5.5), (-1, 0.1, -0.4)), ((11.0, 14.0, -5.5), (1, 0.1, -0.4))]
    for base, d in spikes:
        d = np.array(d, float); d /= np.linalg.norm(d)
        sizes = (3.2, 2.1)
        c = np.array(base, float)
        for i, s in enumerate(sizes):
            if i:
                c = c + d * (sizes[i - 1] * 0.9 + s * 0.6)
            k.box(tuple(c), (s, s * 0.85, s), k.u(-0.04, 0.10) + i * 0.06)
    # 아래로 뾰족한 앞머리 (넓은 위 + 좁은 끝)
    for x, yb in [(-9.0, 13.2), (-4.6, 12.6), (0.0, 13.0), (4.6, 12.5), (9.0, 13.4)]:
        k.box((x, yb + 2.2, 11.4), (2.3, 1.6, 1.3), k.u(-0.05, 0.05))
        k.box((x, yb + 0.5, 11.4), (1.1, 0.6, 1.1), k.u(-0.05, 0.05))
    k.box((0, 20.6, 11.6), (11.0, 1.4, 1.2), 0.04)
    return k.out


def hair_pink_long():
    """분홍 긴 머리: 일자 앞머리, 얼굴 옆으로 내려오는 앞 가닥, 허리까지 오는 뒷머리(층층)."""
    k = HairKit('#F49AC1', 41, noise=0.05)
    k.shell(side_bottom=-2.0, back_bottom=-12.0, side_front=1.5)
    k.top_chunks(n=3, y0=21.9, dome=0.8, size=(3.2, 4.0), hy=(1.0, 1.4), spread=7.5, jit=0.6)
    k.bangs([(x, 12.7 + (0.4 if i % 2 else 0), 2.05) for i, x in enumerate(np.linspace(-9.7, 9.7, 6))])
    for sg in (1, -1):
        # 얼굴 옆 앞 가닥 (어깨 앞으로) - 뺨 앞을 가리지 않게 머리 옆선 바깥
        k.box((sg * 12.2, 5.0, 3.8), (1.3, 9.5, 1.9), 0.04)
        k.box((sg * 12.0, -5.6, 4.2), (1.2, 1.3, 1.6), -0.04)            # 끝 안쪽으로 말림
        k.box((sg * 10.9, -7.0, 4.2), (1.0, 0.8, 1.4), -0.08)
        k.shingles([(16.0, 13.2), (10.0, 13.0), (4.0, 12.8), (-2.0, 12.7)], ('side', sg), size=(2.4, 3.4), hy=(2.4, 3.0), back=2.0)
    k.shingles([(16.0, 12.6), (10.0, 12.5), (4.0, 12.4), (-2.0, 12.3), (-8.0, 12.2), (-12.6, 11.8)], 'back',
               size=(2.4, 3.6), hy=(2.4, 3.0), back=2.0)
    # 끝 말림
    for x in (-7.5, -2.5, 2.5, 7.5):
        k.box((x, -13.6, -10.6), (2.2, 0.9, 1.6), -0.08, back=True)
    return k.out


def hair_sky_bob():
    """하늘색 단발: 턱선 길이, 끝이 안으로 말린 둥근 실루엣, 일자 앞머리, 층층 결."""
    k = HairKit('#8FCBF0', 55, noise=0.06)
    k.shell(side_bottom=1.5, back_bottom=1.0, side_front=2.5)
    k.top_chunks(n=3, y0=21.8, dome=1.2, size=(2.6, 3.6), hy=(1.0, 1.6), spread=7.5, jit=0.9)
    k.bangs([(x, 12.9 - 0.4 * np.cos(i * 1.7), 2.05) for i, x in enumerate(np.linspace(-9.7, 9.7, 6))])
    for sg in (1, -1):
        k.shingles([(17.0, 13.2), (11.4, 13.0), (5.8, 12.8)], ('side', sg), size=(2.6, 3.6), hy=(2.4, 3.0))
        k.box((sg * 12.4, 1.4, -3.5), (1.5, 1.3, 7.0), -0.08)            # 아래 안쪽 말림
        k.box((sg * 12.6, 7.0, 1.6), (1.1, 5.0, 1.2), 0.04)               # 귀 앞 옆선 (뺨은 열어 둠)
        k.box((sg * 12.2, 2.0, 1.6), (1.0, 0.9, 1.1), -0.06)
    k.shingles([(17.2, 12.9), (11.6, 12.7), (6.0, 12.5)], 'back', size=(2.6, 3.6), hy=(2.4, 3.0))
    k.box((0, 1.5, -12.0), (10.8, 1.3, 1.3), -0.08)
    k.box((-3.0, 24.0, 1.0), (1.8, 0.9, 1.8), 0.1)
    return k.out


def hair_tan_ponytail():
    """갈색 포니테일: 높이 묶은 꼬리(뒤로 갔다 아래로), 빨간 머리끈, 옆 가르마 앞머리."""
    k = HairKit('#8C5A3C', 63, noise=0.05)
    k.shell(side_bottom=8.5, back_bottom=4.0, side_front=2.5)
    k.top_chunks(n=3, y0=21.6, dome=0.8, size=(3.0, 4.0), hy=(0.9, 1.3), spread=7.5, jit=0.6)
    k.bangs([(-9.6, 12.8, 2.0), (-5.6, 13.0, 2.0), (-1.6, 13.4, 2.0), (2.4, 13.9, 2.0), (6.4, 14.4, 2.0), (10.0, 13.2, 1.6)])
    for sg in (1, -1):
        k.box((sg * 12.3, 12.0, 2.2), (1.0, 3.6, 1.2), -0.04)              # 옆 잔머리
    k.out.append(P('head', (0, 17.4, -12.4), (1.8, 1.8, 1.3), '#E8483E', bevel=0.4, noise=0.02))   # 머리끈
    tail = [((0, 17.6, -14.6), (2.5, 2.5, 1.6)), ((0, 14.0, -15.8), (3.0, 2.8, 2.0)), ((0, 9.8, -16.0), (2.8, 2.6, 2.0)),
            ((0, 5.8, -15.4), (2.3, 2.2, 1.8)), ((0, 2.6, -14.4), (1.7, 1.6, 1.5)), ((0.6, 0.4, -13.2), (1.1, 1.0, 1.1))]
    for i, (c, h) in enumerate(tail):
        k.box(c, h, (0.08, 0.04, -0.02, -0.06, -0.08, -0.1)[i])
    return k.out


def hair_black_twintail():
    """검은 양갈래: 옆에서 묶은 두 꼬리가 어깨 높이까지, 빨간 머리끈."""
    k = HairKit('#2C2533', 77, noise=0.06)
    k.shell(side_bottom=9.0, back_bottom=3.0, side_front=2.5)
    k.top_chunks(n=3, y0=21.6, dome=0.8, size=(3.0, 4.0), hy=(0.9, 1.3), spread=7.5, jit=0.6)
    k.bangs([(x, 12.8 + (0.5 if i in (0, 5) else 0), 2.05) for i, x in enumerate(np.linspace(-9.7, 9.7, 6))])
    k.shingles([(17.0, 12.6), (11.0, 12.4), (5.6, 12.2)], 'back', size=(2.6, 3.6), hy=(2.2, 2.8))
    for sg in (1, -1):
        k.out.append(P('head', (sg * 13.4, 15.0, -2.5), (1.2, 1.5, 1.5), '#E8483E', bevel=0.4, noise=0.02))
        tail = [((sg * 15.3, 13.6, -2.8), (2.2, 2.4, 2.2)), ((sg * 16.4, 9.6, -2.8), (2.6, 2.8, 2.4)),
                ((sg * 16.6, 5.0, -2.5), (2.4, 2.4, 2.2)), ((sg * 16.0, 1.2, -2.0), (2.0, 2.0, 1.9)),
                ((sg * 14.8, -1.8, -1.6), (1.5, 1.3, 1.5))]
        for i, (c, h) in enumerate(tail):
            k.box(c, h, (0.10, 0.04, -0.02, -0.06, -0.08)[i])
    return k.out


def hair_mint_curly():
    """민트 곱슬: 크고 둥근 곱슬 볼륨 (덩어리 많이, 바깥으로 2~4칸)."""
    k = HairKit('#7FD6B8', 91, noise=0.08)
    k.shell(side_bottom=6.0, back_bottom=1.0, side_front=2.5, top=21.2)
    k.top_chunks(n=4, y0=23.0, dome=2.2, size=(2.2, 3.4), hy=(1.6, 2.4), spread=9.0, jit=1.2)
    k.top_chunks(n=3, y0=25.2, dome=1.4, size=(2.0, 3.0), hy=(1.3, 2.0), spread=6.0, jit=1.2)
    for x in (-8.8, -4.4, 0.0, 4.4, 8.8):
        k.chunk((x + k.u(-0.5, 0.5), 20.4 + k.u(-0.3, 1.0), 11.6 + k.u(0.2, 1.0)), (k.u(2.3, 2.9), k.u(1.8, 2.4), k.u(1.4, 1.9)))
    k.bangs([(-9.6, 13.6, 2.1), (-5.2, 12.8, 2.1), (-0.6, 13.3, 2.1), (4.0, 12.6, 2.1), (8.6, 13.4, 2.1)])
    for sg in (1, -1):
        k.shingles([(19.0, 14.4), (14.6, 14.2), (10.0, 13.8), (6.0, 13.2)], ('side', sg), size=(2.2, 3.2), hy=(2.0, 2.6))
    k.shingles([(19.0, 14.2), (14.6, 14.0), (10.0, 13.7), (5.6, 13.2), (1.8, 12.6)], 'back', size=(2.2, 3.2), hy=(2.0, 2.6))
    return k.out


HAIRS = {'black-short': hair_black_short, 'brown-short': hair_brown_short, 'blonde-spiky': hair_blonde_spiky,
         'pink-long': hair_pink_long, 'sky-bob': hair_sky_bob, 'tan-ponytail': hair_tan_ponytail,
         'black-twintail': hair_black_twintail, 'mint-curly': hair_mint_curly}


# ================================================================== top
def _body(col, hem=None, hx=7.6, hz=4.75):
    out = R('torso', (0, 16.0, 0), (hx, 5.8, hz), col, 0.8)
    if hem:
        out += R('torso', (0, 10.5, 0), (hx + 0.2, 0.9, hz + 0.2), hem, 0.5)
    return out


def _long_sleeves(col, cuff):
    out = []
    for sg in (1, -1):
        a = 'arm%+d' % sg
        out += R(a, (0, -3.9, 0), (2.85, 5.1, 2.85), col, 0.6)
        out += R(a, (0, -8.6, 0), (3.15, 1.0, 3.15), cuff, 0.4)
    return out


def _short_sleeves(col, band=None, puff=False):
    out = []
    for sg in (1, -1):
        a = 'arm%+d' % sg
        if puff:
            out += R(a, (0, -1.6, 0), (3.5, 2.5, 3.5), col, 0.9)
        else:
            out += R(a, (0, -2.0, 0), (2.95, 3.0, 2.95), col, 0.6)
        if band:
            out += R(a, (0, -4.1 if puff else -4.7, 0), (3.05 if not puff else 3.1, 0.5, 3.05 if not puff else 3.1), band, 0.3)
    return out


def top_hoodie(col, cord):
    rib = tint(col, -0.08)
    out = _body(col, rib)
    out += [P('torso', (0, 13.6, 4.9), (4.7, 2.3, 0.35), col, bevel=0.5),                 # 캥거루 주머니
            P('torso', (0, 22.5, -6.6), (7.0, 3.3, 3.1), col, bevel=SOFT),               # 후드 덩어리
            P('torso', (0, 24.9, -8.8), (5.8, 1.6, 1.4), tint(col, -0.04), bevel=SOFT),
            P('torso', (0, 19.7, -9.3), (5.2, 1.5, 1.0), tint(col, -0.07), bevel=SOFT)]
    for sg in (1, -1):
        out += [P('torso', (sg * 5.7, 22.4, -0.9), (1.7, 1.8, 4.0), col, bevel=SOFT),
                P('torso', (sg * 1.8, 18.6, 4.8), (0.5, 2.4, 0.12), cord, decal=True, bevel=0, noise=0),
                P('torso', (sg * 1.8, 15.8, 4.85), (0.65, 0.65, 0.22), tint(cord, -0.15), bevel=0.15, noise=0)]
    return out + _long_sleeves(col, rib)


def top_blouse():
    col = '#FBF7F2'
    out = _body(col, tint(col, -0.05), hx=7.5, hz=4.65)
    pink = '#F58AB4'
    for sg in (1, -1):
        out += [P('torso', (sg * 2.6, 21.7, 3.4), (2.7, 0.55, 1.7), col, bevel=0.5),               # 둥근 칼라
                P('torso', (sg * 2.6, 21.2, 5.05), (2.7, 0.2, 0.1), pink, decal=True, bevel=0, noise=0),
                P('torso', (sg * 1.9, 21.0, 4.95), (1.2, 0.9, 0.4), pink, bevel=0.35, noise=0.02),       # 리본 고리
                P('torso', (sg * 0.7, 19.2, 4.9), (0.45, 1.1, 0.25), tint(pink, -0.08), bevel=0.2, noise=0.02)]
    out.append(P('torso', (0, 20.9, 5.1), (0.8, 0.75, 0.4), tint(pink, -0.1), bevel=0.3, noise=0.02))
    for y in (17.4, 15.0, 12.6):
        out.append(P('torso', (0, y, 4.7), (0.42, 0.42, 0.1), '#F7C0D6', decal=True, bevel=0, noise=0))
    out += R('torso', (0, 10.0, 0), (8.1, 0.8, 5.2), tint(col, -0.03), 0.4)                       # 프릴 밑단
    return out + _short_sleeves(col, pink, puff=True)


def top_overalls():
    tee = '#FFF6E4'; g = '#4FAE4A'
    out = _body(tee, hx=7.5, hz=4.65)
    out += R('torso', (0, 11.0, 0), (7.8, 1.5, 4.95), g, 0.5)                                     # 허리
    out += [P('torso', (0, 14.6, 4.85), (4.8, 4.2, 0.4), g, bevel=0.5),                          # 가슴판
            P('torso', (0, 15.0, 5.27), (2.2, 1.5, 0.04), tint(g, -0.12), decal=True, bevel=0, noise=0)]
    for sg in (1, -1):
        out += [P('torso', (sg * 3.4, 20.0, 4.8), (0.95, 2.0, 0.3), g, bevel=0.3),
                P('torso', (sg * 3.4, 21.95, 0), (0.95, 0.3, 4.95), g, bevel=0.2),
                P('torso', (sg * 2.6, 16.2, -4.85), (0.95, 5.6, 0.3), g, bevel=0.3),
                P('torso', (sg * 3.4, 18.4, 5.25), (0.65, 0.65, 0.2), '#F7C948', bevel=0.2, noise=0, emit=0.1)]
    return out + _short_sleeves(tee, tint(tee, -0.06))


def top_tee_stripe():
    w = '#FBF7F2'; red = '#E8483E'
    out = _body(w, hx=7.5, hz=4.65)
    for y in (12.0, 15.2, 18.4):
        out += R('torso', (0, y, 0), (7.6, 0.8, 4.75), red, 0.3)
    out += R('torso', (0, 10.5, 0), (7.7, 0.6, 4.85), tint(w, -0.06), 0.3)
    out.append(P('torso', (0, 21.85, 0), (4.0, 0.25, 4.0), red, bevel=0.2))
    return out + _short_sleeves(w, red)


def top_cape():
    shirt = '#EEF2FA'; blue = '#3E6BD8'
    out = _body(shirt, tint(shirt, -0.06), hx=7.5, hz=4.65)
    out += [P('torso', (0, 13.5, -5.7), (8.3, 8.5, 0.6), blue, bevel=0.5, sway='cape'),            # 망토 등판
            P('torso', (0, 6.4, -6.3), (8.9, 1.6, 0.6), tint(blue, -0.06), bevel=0.5, sway='cape'),  # 아래 퍼짐
            P('torso', (0, 13.5, -5.05), (7.8, 8.0, 0.05), '#F7C948', decal=True, bevel=0, noise=0, sway='cape')]  # 안감(가장자리만 보임)
    out += R('torso', (0, 21.3, -0.6), (8.9, 1.1, 5.4), blue, 0.5)                              # 어깨 망토(케이프렛)
    out += [P('torso', (0, 22.9, -3.0), (6.0, 1.0, 2.0), tint(blue, 0.08), bevel=0.4),            # 세운 깃
            P('torso', (0, 20.6, 5.55), (1.05, 1.05, 0.3), '#F7C948', bevel=0.3, noise=0, emit=0.15)]  # 금색 브로치
    return out + _long_sleeves(shirt, tint(blue, 0.1))


TOPS = {'hoodie-black': lambda: top_hoodie('#3B3644', '#C9C3CF'), 'hoodie-white': lambda: top_hoodie('#F4EDE2', '#B5AA9E'),
        'blouse-white': top_blouse, 'overalls-green': top_overalls, 'tee-stripe-red': top_tee_stripe, 'cape-blue': top_cape}


# ================================================================== bottom
def _pants(col, cuff=None, shorts=False):
    out = R('torso', (0, 10.3, 0), (7.3, 1.7, 4.45), col, 0.5)
    for sg in (1, -1):
        l, sh = 'leg%+d' % sg, 'shin%+d' % sg
        if shorts:
            out += R(l, (0, -2.1, 0), (3.55, 2.5, 3.55), col, 0.5)
            out += R(l, (0, -4.2, 0), (3.65, 0.5, 3.65), tint(col, -0.1), 0.3)
        else:
            out += R(l, (0, -2.5, 0), (3.35, 2.9, 3.35), col, 0.5)
            out += R(sh, (0, -1.6, 0), (3.25, 2.3, 3.25), col, 0.5)
            if cuff:
                out += R(sh, (0, -3.2, 0), (3.45, 0.75, 3.45), cuff, 0.3)
    return out


def bottom_skirt():
    pink = '#F58AB4'
    out = R('torso', (0, 10.4, 0), (7.6, 1.5, 4.8), pink, 0.5)
    out += R('torso', (0, 8.0, 0), (8.7, 1.4, 5.7), tint(pink, 0.05), 0.6, sway='skirt')
    out += R('torso', (0, 6.3, 0), (9.0, 0.4, 6.0), '#FFF6E4', 0.3, sway='skirt')
    return out


BOTTOMS = {'pants-navy': lambda: _pants('#2E3E7A'), 'pants-black': lambda: _pants('#2B2733'), 'skirt-pink': bottom_skirt,
           'shorts-brown': lambda: _pants('#8A5232', shorts=True), 'jeans-blue': lambda: _pants('#4D7CC8', cuff='#7FA6E0')}


# ================================================================== shoes (정강이 뼈)
def _sneaker(up, sole, lace):
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -4.45, 1.0), (3.85, 0.55, 4.85), sole, 0.3)
        out += R(s, (0, -3.0, 0.9), (3.55, 1.45, 4.55), up, 0.7)
        out += [P(s, (0, -1.53, 1.9), (1.8, 0.05, 1.7), lace, decal=True, bevel=0, noise=0),
                P(s, (0, -3.2, 5.47), (2.6, 0.9, 0.05), tint(up, -0.05), decal=True, bevel=0, noise=0)]
    return out


def shoes_maryjane():
    red = '#E8483E'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -2.2, 0), (3.15, 1.2, 3.15), '#FFFFFF', 0.4)                 # 흰 양말
        out += R(s, (0, -4.5, 1.0), (3.75, 0.5, 4.75), '#9E2838', 0.3)
        out += R(s, (0, -3.4, 1.1), (3.5, 1.0, 4.5), red, 0.8)
        out.append(P(s, (0, -2.35, 1.5), (3.6, 0.3, 0.6), red, bevel=0.2))             # 끈
        out.append(P(s, (sg * 3.6, -2.4, 1.5), (0.1, 0.35, 0.35), '#F7C948', decal=True, bevel=0, noise=0))
    return out


def shoes_boots():
    br = '#8A5232'
    out = []
    for sg in (1, -1):
        s = 'shin%+d' % sg
        out += R(s, (0, -4.45, 1.0), (3.9, 0.55, 4.85), '#4A2A1A', 0.3)
        out += R(s, (0, -2.3, 0.5), (3.6, 2.3, 4.3), br, 0.7)
        out += R(s, (0, -2.6, 2.6), (3.55, 1.5, 2.6), br, 0.7)
        out += R(s, (0, 0.2, 0), (3.85, 0.8, 3.85), tint(br, 0.12), 0.4)              # 접힌 윗단
    return out


SHOES = {'sneakers-white': lambda: _sneaker('#F6F3EE', '#B9B2BE', '#9C93A3'), 'maryjane-red': shoes_maryjane,
         'boots-brown': shoes_boots, 'sneakers-black': lambda: _sneaker('#34303C', '#F2EEE8', '#BDB6C6')}


# ================================================================== hat (머리 로컬)
def hat_cap():
    w = '#F6F3EE'
    out = R('head', (0, 21.4, -0.3), (13.5, 2.6, 13.4), w, 0.9)
    out += R('head', (0, 24.9, -0.6), (12.0, 1.4, 11.8), tint(w, 0.02), 0.8)
    out += R('head', (0, 26.6, -0.8), (9.0, 0.8, 8.8), tint(w, 0.04), 0.6)
    out += [P('head', (0, 27.65, -0.8), (1.0, 0.45, 1.0), '#E8483E', bevel=0.3, noise=0),
            P('head', (0, 19.4, 15.8), (10.6, 0.55, 3.6), w, bevel=0.6),
            P('head', (0, 18.8, 15.5), (10.2, 0.08, 3.2), '#C9C3CF', bevel=0),
            P('head', (0, 22.0, 13.15), (2.2, 1.4, 0.05), '#E8483E', decal=True, bevel=0, noise=0),
            P('head', (0, 22.4, 13.2), (1.3, 0.5, 0.05), '#FFFFFF', decal=True, bevel=0, noise=0),
            P('head', (0, 20.6, -13.75), (3.0, 1.0, 0.05), '#C9C3CF', decal=True, bevel=0, noise=0)]
    return out


def hat_mushroom():
    red = '#E8483E'; dot = '#FFF6E4'
    out = [P('head', (0, 20.4, 0), (14.6, 0.5, 14.6), '#F2DDB8', bevel=0.4)]
    out += R('head', (0, 23.0, 0), (15.8, 2.2, 15.8), red, 1.0)
    out += R('head', (0, 26.6, 0), (13.4, 1.8, 13.4), red, 0.9)
    out += R('head', (0, 29.4, 0), (10.2, 1.4, 10.2), red, 0.8)
    out += R('head', (0, 31.3, 0), (6.0, 0.8, 6.0), tint(red, 0.05), 0.5)
    D2 = dict(decal=True, bevel=0, noise=0, emit=0.1)
    for (x, y, z, hx, hy, hz) in [(0, 32.12, 0, 2.2, 0.03, 2.2), (-7, 30.82, 4, 1.8, 0.03, 1.8), (6, 30.82, -5, 1.6, 0.03, 1.6),
                                   (7.5, 28.42, 7, 1.4, 0.03, 1.4), (-9, 28.42, -7, 1.6, 0.03, 1.6),
                                   (-6, 23.0, 15.82, 2.0, 1.4, 0.03), (6, 22.6, 15.82, 1.4, 1.0, 0.03), (0, 26.8, 13.42, 1.8, 1.0, 0.03),
                                   (15.82, 23.0, 2, 0.03, 1.4, 2.2), (-15.82, 23.0, -4, 0.03, 1.3, 1.8), (0, 23.0, -15.82, 2.0, 1.3, 0.03)]:
        out.append(P('head', (x, y, z), (hx, hy, hz), dot, **D2))
    return out


def hat_explorer():
    tan = '#C9A47A'
    out = [P('head', (0, 21.0, 0), (15.8, 0.55, 15.8), tint(tan, -0.04), bevel=0.6)]
    out += R('head', (0, 24.6, -0.2), (13.6, 3.2, 13.6), tan, 1.0)
    out += [P('head', (0, 27.9, -0.2), (11.2, 0.3, 11.2), tint(tan, -0.08), bevel=0.3),
            P('head', (0, 22.4, -0.2), (13.75, 0.75, 13.75), '#5E3620', bevel=0.3)]
    return out


def hat_beanie():
    y = '#F7C948'
    out = R('head', (0, 21.4, -0.4), (13.5, 4.2, 13.4), y, 1.2)
    out += R('head', (0, 26.0, -0.6), (11.6, 1.0, 11.4), tint(y, 0.04), 0.9)                 # 둥근 윗단
    out += R('head', (0, 17.6, -0.4), (13.8, 1.4, 13.7), tint(y, -0.1), 0.5)
    out += R('head', (0, 28.6, -0.6), (2.6, 2.0, 2.6), '#FFF6E4', 0.9)                      # 방울
    for x in np.linspace(-11.5, 11.5, 9):
        out.append(P('head', (x, 17.6, 13.33), (0.28, 1.2, 0.03), tint(y, -0.2), decal=True, bevel=0, noise=0))
    for x in np.linspace(-9, 9, 5):
        out.append(P('head', (x, 22.0, 13.03), (0.22, 2.8, 0.03), tint(y, -0.07), decal=True, bevel=0, noise=0))
    return out


def hat_ribbon():
    p = '#F58AB4'
    c = np.array([6.5, 24.6, 6.0])
    out = [P('head', tuple(c), (1.9, 1.8, 1.6), tint(p, -0.08), bevel=0.5),
           P('head', tuple(c + [-4.3, 1.0, -0.2]), (3.2, 2.7, 1.4), p, bevel=0.8),
           P('head', tuple(c + [4.3, 1.0, -0.2]), (3.2, 2.7, 1.4), p, bevel=0.8),
           P('head', tuple(c + [-4.3, 1.0, 1.23]), (1.4, 1.1, 0.03), tint(p, -0.2), decal=True, bevel=0, noise=0),
           P('head', tuple(c + [4.3, 1.0, 1.23]), (1.4, 1.1, 0.03), tint(p, -0.2), decal=True, bevel=0, noise=0),
           P('head', tuple(c + [-2.0, -3.2, 0.2]), (1.1, 2.2, 0.8), p, bevel=0.4),
           P('head', tuple(c + [2.2, -3.5, 0.2]), (1.1, 2.4, 0.8), p, bevel=0.4)]
    return out


def hat_ribbon():
    p = '#F58AB4'
    c = np.array([7.2, 24.2, 4.5])
    out = [P('head', tuple(c), (1.4, 1.4, 1.2), tint(p, -0.08), bevel=0.4),
           P('head', tuple(c + [-3.2, 0.8, 0]), (2.4, 2.0, 1.0), p, bevel=0.6),
           P('head', tuple(c + [3.2, 0.8, 0]), (2.4, 2.0, 1.0), p, bevel=0.6),
           P('head', tuple(c + [-3.2, 0.8, 1.02]), (1.0, 0.8, 0.03), tint(p, -0.18), decal=True, bevel=0, noise=0),
           P('head', tuple(c + [3.2, 0.8, 1.02]), (1.0, 0.8, 0.03), tint(p, -0.18), decal=True, bevel=0, noise=0),
           P('head', tuple(c + [-1.4, -2.4, 0.3]), (0.8, 1.6, 0.6), p, bevel=0.3),
           P('head', tuple(c + [1.6, -2.6, 0.3]), (0.8, 1.8, 0.6), p, bevel=0.3)]
    return out


HATS = {'cap-white': hat_cap, 'mushroom-red': hat_mushroom, 'explorer-brown': hat_explorer,
        'beanie-yellow': hat_beanie, 'ribbon-pink': hat_ribbon}

PARTS = {
    'skin': {k: (lambda k=k: skin(k)) for k in SKINS},
    'face': {k: (lambda k=k: face(k)) for k in ('basic', 'smile', 'wink', 'sleepy')},
    'hair': HAIRS, 'top': TOPS, 'bottom': BOTTOMS, 'shoes': SHOES, 'hat': HATS,
}


# ================================================================== 프록시 (레이어 분리, 그림자 받는 면)
def proxy_body():
    """옷 입은 몸 근사 (머리 제외): hair/hat 뒤쪽 판정용. 망토 두께까지 뒤로 넓힘."""
    out = [P('torso', (0, 15.6, -0.9), (8.2, 6.8, 5.9), '#000000'),
           P('torso', (0, 8.0, -0.9), (9.0, 2.6, 5.9), '#000000')]
    for sg in (1, -1):
        out += [P('arm%+d' % sg, (0, -6.0, 0.1), (3.4, 7.6, 3.4), '#000000'),
                P('leg%+d' % sg, (0, -2.5, 0), (3.8, 3.0, 3.8), '#000000'),
                P('shin%+d' % sg, (0, -2.4, 0.6), (4.0, 2.8, 4.6), '#000000')]
    return out


def proxy_legs():
    """바지/신발 근사: top(망토) 뒤쪽 판정용."""
    out = [P('torso', (0, 10.0, 0), (7.3, 1.6, 4.5), '#000000')]
    for sg in (1, -1):
        out += [P('leg%+d' % sg, (0, -2.5, 0), (3.6, 3.0, 3.6), '#000000'),
                P('shin%+d' % sg, (0, -2.4, 0.6), (3.9, 2.8, 4.6), '#000000')]
    return out


def proxy_hairshell():
    """머리카락 껍데기 근사: 모자 뒤쪽 판정 + 모자 그림자 받는 면."""
    return [P('head', (0, 11.0, -0.6), (13.4, 12.0, 12.6), '#000000')]


PROXIES = {'body': proxy_body, 'legs': proxy_legs, 'hairshell': proxy_hairshell}


# ================================================================== 포즈
# 사이클 6 포즈 (jump / fall / crouch). 기존 8프레임은 아래 기본값에서 사이클 5와 같은 경로를 탄다(출력 동일).
#   pivot 'hip'  : 몸 기울기(lean)를 엉덩이 높이 기준으로 (기본: 발바닥 높이 기준, 사이클 5 그대로)
#   sink         : 몸통(+머리, 팔)을 엉덩이 관절보다 아래로 내림 (숙이기에서 키 줄이기)
#   ground       : None = 자동 접지(낮은 발바닥을 y=0), 숫자 = 고정 높이(점프/하강: 몸 중심 유지, 발은 떠 있음)
#   feet_z       : 숫자면 두 발바닥 중심 z 평균이 이 값이 되게 몸 전체를 앞뒤로 옮김 (숙이기: 발이 기준점 위)
#   legsplay     : 다리를 옆으로 벌림(도, +바깥). asplay: 팔별 벌림(도) - 없으면 splay
#   hang         : 머리카락 늘어짐(월드 기준 각도, 0 = 중력 방향으로 곧게, + = 뒤/위로 날림).
#                  머리 로컬 y < HANG_CUTS[0] 부분을 잘라 2마디로 나눠 돌린다(축은 상자 z). 숫자면 두 마디에 고르게,
#                  (w1, w2) 튜플이면 마디별 월드 각도 (숙이기: 끝마디가 바닥에 닿아 뒤로 눕는다).
#   cape         : 망토 등판(sway='cape' 상자) 월드 기준 각도. 어깨 뒤 축 + 2마디.
#   squash       : (sy, sxz) 몸통 뼈 상자를 엉덩이 높이 기준으로 세로 sy, 가로/깊이 sxz 배 (숙이기: 웅크려 눌림)
#   skirt_lift   : 치마 단(sway='skirt')을 수평으로 되돌리고 위로 올림 (숙이기: 치마가 지면을 뚫지 않게)
HANG_CUTS = (6.0, -3.0)
CAPE_CUTS = (21.0, 12.0)
CAPE_Z = -5.7
NEW_FRAMES = ('jump', 'fall', 'crouch')


def pose_frame(name):
    """각도 + = 앞으로. shin 은 무릎 굽힘(- = 발이 뒤로)."""
    p = dict(breathe=0.0, arm={1: 0.0, -1: 0.0}, leg={1: 0.0, -1: 0.0}, shin={1: 0.0, -1: 0.0},
             splay=5.0, head=0.0, lean=0.0,
             pivot=None, sink=0.0, ground=None, feet_z=None, legsplay=None, asplay=None, hang=None, cape=None,
             skirt_lift=None, squash=None, hang_cuts=None)
    if name == 'front_b':
        p['breathe'] = -0.45
    walk = {'walk0': ((30, -8), (-24, -32), 40, -1.5), 'walk1': ((-4, -2), (16, -48), 14, 0.0),
            'walk2': ((-24, -32), (30, -8), -40, -1.5), 'walk3': ((16, -48), (-4, -2), -14, 0.0)}
    if name in walk:
        (t1, s1), (t2, s2), arm, head = walk[name]
        p['leg'] = {1: t1, -1: t2}
        p['shin'] = {1: s1, -1: s2}
        p['arm'] = {1: -arm, -1: arm}
        p['splay'] = 3.0
        p['head'] = head
        p['lean'] = 3.0
    POSES6 = {
        # 상승: 무릎 당김(허벅지 앞 약 60, 무릎 약 70), 팔 앞으로 들어 올림, 살짝 웅크림. 몸 중심은 서 있을 때 높이.
        'jump': dict(leg={1: 62.0, -1: 56.0}, shin={1: -72.0, -1: -68.0}, arm={1: 64.0, -1: 72.0},
                     asplay={1: 16.0, -1: 16.0}, lean=8.0, head=-5.0, pivot='hip', ground=0.6,
                     hang=0.0, cape=10.0),
        # 하강: 다리 아래로 펴고 벌림, 팔 옆으로 벌림, 머리카락/망토 위로 날림.
        'fall': dict(leg={1: 10.0, -1: -12.0}, shin={1: -14.0, -1: -8.0}, legsplay=7.0, arm={1: 40.0, -1: -35.0},
                     asplay={1: 70.0, -1: 70.0}, lean=-4.0, head=3.0, pivot='hip', ground=0.6,
                     hang=24.0, cape=40.0),
        # 숙이기: 허벅지 수평 위로(100), 정강이 수직(발 평평), 몸통을 내리고 눌러(squash) 앞으로 숙임, 머리는 앞을 봄.
        'crouch': dict(leg={1: 100.0, -1: 100.0}, shin={1: -100.0, -1: -100.0}, arm={1: 88.0, -1: 82.0},
                       splay=6.0, lean=16.0, head=-16.0, pivot='hip', sink=1.0, feet_z=1.0, squash=(0.55, 1.1),
                       hang=(2.0, 75.0), hang_cuts=(6.0, -9.5), cape=40.0, skirt_lift=3.0),
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
        hip = np.array([sg * HIP[0], HIP[1], 0])
        knee = hip + Rt @ np.array(KNEE)
        for dz in (-3.8, 5.8):
            low.append((knee + Rs @ (np.array(SOLE) + [0, 0, dz - 1.0]))[1])
        soles.append(knee + Rs @ np.array(SOLE))
    b = -min(low) if pose.get('ground') is None else float(pose['ground'])
    dz = 0.0 if pose.get('feet_z') is None else float(pose['feet_z']) - float(np.mean([s[2] for s in soles]))
    xf['root'] = (I, np.array([0, b, dz]))
    if pose.get('pivot') == 'hip':
        hy = np.array([0, HIP[1], 0.0])
        xf['torso'] = (Rl, np.array([0, b + br * 0.5 - pose['sink'], dz]) + hy - Rl @ hy)
    else:
        xf['torso'] = (Rl, np.array([0, b + br * 0.5, 0.0]))
    tor_R, tor_t = xf['torso']
    sq = (lambda v: squash_pt(v, pose['squash'])) if pose.get('squash') else (lambda v: v)
    xf['head'] = (Rl @ rot_x(pose['head']), tor_t + Rl @ sq(np.array(HEAD_PIVOT) + [0, br * 0.5, 0]))
    for sg in (1, -1):
        spl = pose['asplay'][sg] if pose.get('asplay') else pose['splay']
        Ra = Rl @ rot_z(sg * spl) @ rot_x(-pose['arm'][sg])
        xf['arm%+d' % sg] = (Ra, tor_t + Rl @ sq(np.array([sg * SHOULDER[0], SHOULDER[1] + br * 0.1, 0])))
        Rt, Rs = legs[sg]
        hip = np.array([sg * HIP[0], HIP[1] + b, dz])
        xf['leg%+d' % sg] = (Rt, hip)
        xf['shin%+d' % sg] = (Rs, hip + Rt @ np.array(KNEE))
    return xf


def squash_pt(v, sq):
    sy, sxz = sq
    v = np.asarray(v, float)
    return np.array([v[0] * sxz, HIP[1] + (v[1] - HIP[1]) * sy, v[2] * sxz])


def squash_defs(defs, pose):
    """몸통 뼈 상자를 squash (위치와 크기). 해당 없으면 defs 그대로."""
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
    마디 축은 (y=cut, z=zpiv 또는 상자 중심 z) 를 지나는 x축. 아래 조각은 위로 0.6 겹치고 가로/깊이 0.05씩 키워 이음새를 덮는다."""
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
        cuts = tuple(_sq_y(c, pose) for c in CAPE_CUTS)
        zp = CAPE_Z * (pose['squash'][1] if pose.get('squash') else 1)
        return _chain(defs, lambda d: d.get('sway') == 'cape', 'torso', cuts, (a / 2, a / 2), xf, 'cape', zpiv=zp)
    if cat == 'bottom' and pose.get('skirt_lift') is not None and any(d.get('sway') == 'skirt' for d in defs):
        if 'skirt' not in xf:
            R, t = _hinge(xf, 'torso', (0, _sq_y(10.4, pose), 0), -pose['lean'])
            xf['skirt'] = (R, t + np.array([0, pose['skirt_lift'], 0.0]))
        return [dict(d, bone='skirt') if d.get('sway') == 'skirt' else d for d in defs]
    return defs


def make_boxes(defs, xf, layer, tag, back_view=False):
    out = []
    for d in defs:
        R, t = xf[d['bone']]
        kw = {k: d[k] for k in ('bevel', 'decal', 'noise', 'emit') if k in d}
        out.append(Box(_xf_point(R, t, d['c']), d['h'], R, d['col'], layer, tag=tag, **kw))
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
