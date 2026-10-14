"""마네킹(공통 몸) + 파츠(레이어별 상자 묶음) + 캐릭터 4종 조합 + 프레임 포즈.

치수 (캐릭터 공간, 1 = 1px, 원점 = 발 중앙 바닥)
  머리   x -10..10  y -39..-19  z -10..10   (정면 20x20, 윗면/옆면 4px)
  몸통   x  -6..6   y -19..-8   z  -4..4
  팔     x -10..-6 / 6..10, y -19..-8, z -3..3  (아래 3줄이 손)
  다리   x  -6..0 / 0..6,   y  -8..0,  z  -4..4  (아래 2줄은 신발 자리)
"""
import math
from render import Box

HEAD = (-10, 10, -39, -19, -10, 10)
TORSO = (-6, 6, -19, -8, -4, 4)
ARM_R = (-10, -6, -19, -8, -3, 3)   # 캐릭터 오른팔 (화면 왼쪽, 옆모습에서 카메라 쪽)
ARM_L = (6, 10, -19, -8, -3, 3)
LEG_R = (-6, 0, -8, 0, -4, 4)
LEG_L = (0, 6, -8, 0, -4, 4)

LAYER_ORDER = ['hair_back', 'body', 'face', 'bottom', 'shoes', 'top', 'hair_front', 'hat']


def fl(v):
    return int(math.floor(v + 1e-6))


def nz(seed, *k):
    h = seed & 0xffffffff
    for v in k:
        h = (h ^ ((v & 0xffff) * 0x9E3779B1)) & 0xffffffff
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = (h * 0x85EBCA6B + 0x1234567) & 0xffffffff
    h ^= h >> 16
    return (h & 0xffff) / 65536.0


def solid(mat, noise=0.0, seed=1, dark_only=False):
    def t(face, x, y, z, view):
        if noise:
            r = nz(seed, fl(x), fl(y), fl(z), hash(face) & 0xff if False else len(face))
            if r < noise:
                return (mat, 1)
            if r > 1 - noise and not dark_only:
                return (mat, -1)
        return (mat, 0)
    return t


def B(b, layer, group, tex, name=''):
    return Box(*b, layer=layer, group=group, tex=tex, name=name)


def grow(b, gx=0, gy0=0, gy1=0, gz=0):
    x0, x1, y0, y1, z0, z1 = b
    return (x0 - gx, x1 + gx, y0 - gy0, y1 + gy1, z0 - gz, z1 + gz)


# ---------------------------------------------------------------- body / face
def body_part():
    t = solid('skin')
    return [B(HEAD, 'body', 'head', t, 'head'), B(TORSO, 'body', 'torso', t),
            B(ARM_R, 'body', 'armR', t), B(ARM_L, 'body', 'armL', t),
            B(LEG_R, 'body', 'legR', t), B(LEG_L, 'body', 'legL', t)]


def face_part(eye_row=-27):
    """눈 2x3 (하이라이트 1px), 볼터치 2px, 작은 입. 정면 뷰는 front 면, 옆 뷰는 오른쪽 면 앞쪽."""
    e0 = eye_row

    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'front' and view == 'front':
            for ex in (-6, 4):
                if ex <= ix <= ex + 1 and e0 <= iy <= e0 + 2:
                    if ix == ex and iy == e0:
                        return 'white'
                    return 'ink'
            if iy == e0 + 3 and ix in (-8, -7, 6, 7):
                return 'p2'
            if iy == e0 + 4 and ix in (-1, 0):
                return 'w4'
            return None
        if face == 'right' and view == 'side':
            # 옆모습: 앞쪽 가장자리(z=-10)가 화면 오른쪽
            if iz in (-9, -8) and e0 <= iy <= e0 + 2:
                if iz == -8 and iy == e0:
                    return 'white'
                return 'ink'
            if iy == e0 + 3 and iz in (-7, -6):
                return 'p2'
            if iy == e0 + 4 and iz == -10:
                return 'w4'
            return None
        return None
    return [B(HEAD, 'face', 'head', t, 'face')]


# ---------------------------------------------------------------- hair
def hair_short(mat, bangs, seed=7, side_window_z=1, nape=-20, side_low=-26, tuft=False):
    """머리 큐브를 감싸는 껍데기. bangs: 열 x(-10..9)별 앞머리 끝 행(이 행부터 얼굴)."""
    shell = (-11, 11, -40, nape, -11, 11)

    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        n = nz(seed, ix, iy, iz, len(face))
        if face == 'top':
            base = (mat, -1) if n < 0.06 else (mat, 0)
        else:
            base = (mat, 1) if n < 0.04 else (mat, 0)
        if face == 'top' or face == 'back':
            return base
        if face == 'front':
            if -10 <= ix <= 9:
                return base if iy < bangs[ix + 10] else None
            return base if iy < side_low else None          # 옆머리 (얼굴 바깥 1열)
        if face in ('left', 'right'):
            if iz < side_window_z and iy >= bangs[0] - 1:
                return None if iz > -11 or iy >= side_low else base
            return base
        return None
    out = [B(shell, 'hair', 'head', t, 'shell')]
    if tuft:
        out.append(B((-2, 1, -43, -40, -2, 1), 'hair', 'head', solid(mat), 'tuft'))
    return out


def hair_long_pink():
    mat = 'hair_pink'
    bangs = [-31, -31, -32, -32, -32, -33, -33, -32, -32, -31, -31, -32, -32, -33, -33, -32, -32, -32, -31, -31]
    parts = hair_short(mat, bangs, seed=21, side_window_z=1, nape=-19, side_low=-30)

    def lock(face, x, y, z, view):            # 얼굴 옆으로 내려오는 옆머리, 끝은 계단
        ix, iy, iz = fl(x), fl(y), fl(z)
        end = -17 if ix in (-12, 11) else -18
        if iy >= end:
            return None
        n = nz(33, ix, iy, iz)
        return (mat, 1) if n < 0.08 else (mat, 0)

    def back_up(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'back' and ix in (-1, 0) and iy < -16:
            return (mat, 1)                       # 가르마 결
        n = nz(35, ix, iy, fl(z), len(face))
        return (mat, 1) if n < 0.04 else (mat, 0)

    def back(face, x, y, z, view):            # 등 뒤로 길게 내려오는 블록
        ix, iy = fl(x), fl(y)
        k = ix if face in ('front', 'back') else fl(z)
        end = (-8, -7, -6, -7)[(k // 2) % 4]           # 2열 단위 계단 끝
        if iy >= end:
            return None
        n = nz(34, ix, iy, fl(z), len(face))
        return (mat, 1) if n < 0.04 else (mat, 0)
    parts += [
        B((-12, -10, -33, -16, 1, 5), 'hair', 'head', lock, 'lockR'),
        B((10, 12, -33, -16, 1, 5), 'hair', 'head', lock, 'lockL'),
        B((-10, 10, -22, -12, 5, 10), 'hair', 'head', back_up, 'long_up'),
        B((-9, 9, -12, -5, 5, 9), 'hair', 'head', back, 'long_low'),
    ]

    # 리본 (빨강) 머리 오른쪽 위
    def bow(face, x, y, z, view):
        ix = fl(x)
        return ('cloth_red', 1) if ix in (6, 7) and face == 'front' else ('cloth_red', 0)
    parts.append(B((3, 10, -43, -39, -6, -2), 'hair', 'head', bow, 'bow'))
    return parts


# ---------------------------------------------------------------- hats
def cap_white():
    def crown(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front' and -2 <= ix <= 1 and -40 <= iy <= -39:
            return 'cloth_red'
        if iy == -36 and face != 'top':
            return ('cloth_white', 1)            # 챙 위 띠
        return 'cloth_white'

    def brim(face, x, y, z, view):
        return 'cloth_white'
    return [B((-12, 12, -42, -35, -12, 12), 'hat', 'head', crown, 'crown'),
            B((-1, 1, -43, -42, -1, 1), 'hat', 'head', solid('cloth_red'), 'button'),
            B((-11, 11, -36, -34, -19, -12), 'hat', 'head', brim, 'brim')]


def mushroom_hat():
    dots = {
        # (면, 기준 셀들) 흰 점: 정면 아래층 / 위층 / 윗면 / 옆면
        'low_front': [(-12, -41, 3, 3), (-1, -40, 4, 3), (8, -42, 3, 3)],
        'low_side': [(-9, -41, 3, 3), (3, -40, 4, 3)],
        'up_front': [(-6, -48, 3, 3), (4, -47, 3, 2)],
        'up_side': [(-5, -48, 3, 3)],
        'up_top': [(-8, -6, 4, 4), (2, 2, 4, 5), (-4, 6, 3, 3)],
        'low_top': [(-13, -10, 3, 3), (9, -12, 3, 4), (10, 8, 3, 3)],
    }

    def inr(lst, a, b):
        return any(x0 <= a < x0 + w and y0 <= b < y0 + h for x0, y0, w, h in lst)

    def low(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face in ('front', 'back') and inr(dots['low_front'], ix if face == 'front' else -ix - 1, iy):
            return 'dot'
        if face in ('left', 'right') and inr(dots['low_side'], iz if face == 'left' else -iz - 1, iy):
            return 'dot'
        if face == 'top' and inr(dots['low_top'], ix, iz):
            return 'dot'
        if iy == -37 and face != 'top':
            return ('cap_red', 1)
        return 'cap_red'

    def up(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face in ('front', 'back') and inr(dots['up_front'], ix if face == 'front' else -ix - 1, iy):
            return 'dot'
        if face in ('left', 'right') and inr(dots['up_side'], iz if face == 'left' else -iz - 1, iy):
            return 'dot'
        if face == 'top' and inr(dots['up_top'], ix, iz):
            return 'dot'
        return 'cap_red'
    return [B((-14, 14, -43, -36, -14, 14), 'hat', 'head', low, 'cap_low'),
            B((-10, 10, -50, -43, -10, 10), 'hat', 'head', up, 'cap_up'),
            B((-12, 12, -36, -35, -12, 12), 'hat', 'head', solid('stem'), 'gill')]


# ---------------------------------------------------------------- tops
def hoodie(mat, string, seed=3):
    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            if ix in (-3, 2) and -18 <= iy <= -15:
                return string
            if iy == -9:
                return (mat, 1)                # 밑단 립
        if face in ('left', 'right', 'back') and iy == -9:
            return (mat, 1)
        return (mat, 0)

    def sleeve(face, x, y, z, view):
        if fl(y) == -12:
            return (mat, 1)                    # 소매 끝
        return (mat, 0)

    def hood(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'back' and ix in (-1, 0) and iy < -14:
            return (mat, 1)                    # 후드 솔기
        if face == 'top':
            return (mat, 2)                    # 후드 안쪽 그늘
        return (mat, 0)
    return [B(TORSO, 'top', 'torso', body, 'torso'),
            B((-10, -6, -19, -11, -3, 3), 'top', 'armR', sleeve),
            B((6, 10, -19, -11, -3, 3), 'top', 'armL', sleeve),
            B((-5, 5, -21, -13, 4, 8), 'top', 'torso', hood, 'hood')]


def blouse_white():
    mat = 'cloth_white'

    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            # 리본
            if iy == -17 and ix in (-3, -2, 1, 2):
                return 'cloth_pink'
            if iy == -16 and ix in (-3, 2):
                return 'cloth_pink'
            if iy in (-17, -16) and ix in (-1, 0):
                return ('cloth_pink', 1) if iy == -17 else None if False else ('cloth_pink', 1)
            if iy == -16 and ix in (-2, 1):
                return 'cloth_pink'
            if iy in (-15, -14) and ix in (-2, 1):
                return 'cloth_pink'
        if iy == -9:
            return 'cloth_pink'                # 분홍 밑단
        return mat

    def sleeve(face, x, y, z, view):
        return 'cloth_pink' if fl(y) == -15 else mat
    return [B(TORSO, 'top', 'torso', body, 'torso'),
            B((-11, -6, -19, -14, -4, 4), 'top', 'armR', sleeve),   # 퍼프 소매 (1px 부풀림)
            B((6, 11, -19, -14, -4, 4), 'top', 'armL', sleeve)]


def overalls_top():
    tee, g = 'cloth_cream', 'cloth_green'
    strap_x = (-5, -4, 3, 4)

    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        iz = fl(z)
        if face == 'front':
            if iy == -15 and ix in (-4, 3):
                return 'gold'                  # 단추
            if -4 <= ix <= 3 and iy >= -15:
                if -2 <= ix <= 1 and iy in (-13, -12) and (iy == -13 or ix in (-2, 1)):
                    return (g, 1)              # 가슴 주머니
                return g
            if ix in strap_x and iy < -15:
                return g
            if iy >= -10:
                return g
            return tee
        if face == 'back':
            if ix in strap_x or iy >= -11:
                return g
            return tee
        if face == 'top':
            return g if ix in strap_x else tee
        if face in ('left', 'right'):
            return g if iy >= -10 else tee
        return tee

    def sleeve(face, x, y, z, view):
        return (tee, 1) if fl(y) == -16 else tee
    return [B(TORSO, 'top', 'torso', body, 'torso'),
            B((-10, -6, -19, -15, -3, 3), 'top', 'armR', sleeve),
            B((6, 10, -19, -15, -3, 3), 'top', 'armL', sleeve)]


# ---------------------------------------------------------------- bottoms
def pants(mat, cuff=False, seed=5):
    def leg(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if cuff and iy == -3:
            return (mat, -1)
        if face == 'front' and ix in (-1,) and iy >= -6:
            return (mat, 1)                    # 다리 사이 그늘
        n = nz(seed, ix, iy, fl(z), len(face))
        return (mat, 1) if n < 0.04 else (mat, 0)
    return [B((-6, 0, -8, -2, -4, 4), 'bottom', 'legR', leg),
            B((0, 6, -8, -2, -4, 4), 'bottom', 'legL', leg)]


def skirt_pink():
    mat = 'cloth_pink'

    def up(face, x, y, z, view):
        return mat

    def low(face, x, y, z, view):
        ix, iz = fl(x), fl(z)
        k = ix if face in ('front', 'back') else iz
        if k % 3 == 0:
            return (mat, 1)                    # 주름
        return mat
    return [B((-7, 7, -10, -7, -5, 5), 'bottom', 'torso', up, 'skirt_up'),
            B((-8, 8, -7, -4, -6, 6), 'bottom', 'torso', low, 'skirt_low')]


# ---------------------------------------------------------------- shoes
def shoes(mat, sole, h=2):
    def t(face, x, y, z, view):
        iy = fl(y)
        if iy == -1 and face != 'top':
            return sole
        return mat
    return [B((-6, 0, -h, 0, -5, 4), 'shoes', 'legR', t),
            B((0, 6, -h, 0, -5, 4), 'shoes', 'legL', t)]


# ---------------------------------------------------------------- characters
BLACK_BANGS = [-31, -32, -32, -33, -33, -32, -32, -33, -33, -33, -33, -32, -32, -33, -33, -32, -32, -31, -31, -30]
BROWN_BANGS = [-32, -33, -33, -33, -32, -33, -33, -33, -33, -33, -33, -33, -33, -33, -32, -33, -33, -33, -33, -32]
BLONDE_BANGS = [-32, -32, -33, -33, -32, -32, -33, -33, -33, -32, -32, -33, -33, -33, -32, -32, -33, -33, -32, -32]

PARTS = {
    'body':   {'skin_light': body_part},
    'face':   {'basic': face_part},
    'hair':   {'black_short': lambda: hair_short('hair_black', BLACK_BANGS, seed=11, tuft=True),
               'pink_long': hair_long_pink,
               'brown_short': lambda: hair_short('hair_brown', BROWN_BANGS, seed=12),
               'blonde_short': lambda: hair_short('hair_blonde', BLONDE_BANGS, seed=13)},
    'hat':    {'cap_white': cap_white, 'mushroom_red': mushroom_hat},
    'top':    {'hoodie_black': lambda: hoodie('cloth_black', 'white'),
               'blouse_white': blouse_white,
               'hoodie_white': lambda: hoodie('cloth_white', 'cloth_red', seed=4),
               'overalls_green': overalls_top},
    'bottom': {'pants_navy': lambda: pants('cloth_navy'),
               'skirt_pink': skirt_pink,
               'pants_black': lambda: pants('cloth_dark', seed=6),
               'overalls_green': lambda: pants('cloth_green', cuff=True, seed=8)},
    'shoes':  {'sneakers_white': lambda: shoes('shoe_white', 'c3'),
               'maryjane_red': lambda: shoes('shoe_red', 'r3'),
               'sneakers_red': lambda: shoes('shoe_red', 'white'),
               'boots_brown': lambda: shoes('shoe_brown', 'w4', h=3)},
}

CHARS = [
    ('c1_hoodie', {'body': 'skin_light', 'face': 'basic', 'hair': 'black_short', 'top': 'hoodie_black',
                   'bottom': 'pants_navy', 'shoes': 'sneakers_white'}),
    ('c2_pink', {'body': 'skin_light', 'face': 'basic', 'hair': 'pink_long', 'top': 'blouse_white',
                 'bottom': 'skirt_pink', 'shoes': 'maryjane_red'}),
    ('c3_cap', {'body': 'skin_light', 'face': 'basic', 'hair': 'brown_short', 'hat': 'cap_white',
                'top': 'hoodie_white', 'bottom': 'pants_black', 'shoes': 'sneakers_red'}),
    ('c4_mushroom', {'body': 'skin_light', 'face': 'basic', 'hair': 'blonde_short', 'hat': 'mushroom_red',
                     'top': 'overalls_green', 'bottom': 'overalls_green', 'shoes': 'boots_brown'}),
]

# ---------------------------------------------------------------- frames
LEG_PIV, ARM_PIV = -8, -18
UPPER = ('head', 'torso', 'armR', 'armL')


def walk_pose(k):
    """k=0: 오른다리(카메라 쪽) 앞, 왼다리 뒤, 몸 1px 아래 / 1: 교차(왼발 들림) / 2: 반대 / 3: 교차(오른발 들림)."""
    sl, sa = 4 / 8, 3 / 10
    p = {}
    if k in (0, 2):
        s = -1 if k == 0 else 1
        p['legR'] = {'shear': s * sl, 'pivot': LEG_PIV}
        p['legL'] = {'shear': -s * sl, 'pivot': LEG_PIV}
        p['armR'] = {'shear': -s * sa, 'pivot': ARM_PIV, 'd': (0, 1, 0)}
        p['armL'] = {'shear': s * sa, 'pivot': ARM_PIV, 'd': (0, 1, 0)}
        p['head'] = {'d': (0, 1, 0)}
        p['torso'] = {'d': (0, 1, 0)}
    else:
        lift = 'legL' if k == 1 else 'legR'
        p[lift] = {'shear': 1 / 8, 'pivot': LEG_PIV, 'd': (0, -1, 0)}
    return p


FRAMES = [('front', 'front', None), ('side_idle', 'side', None)] + \
         [('side_walk%d' % k, 'side', walk_pose(k)) for k in range(4)] + [('back', 'back', None)]


def mannequin_clothed():
    """머리카락 앞/뒤 분리용: 몸통·팔·다리를 1px 부풀린 가상 몸 (머리 제외)."""
    t = lambda *a: 'skin'
    out = []
    for b, g in ((TORSO, 'torso'), (ARM_R, 'armR'), (ARM_L, 'armL'), (LEG_R, 'legR'), (LEG_L, 'legL')):
        out.append(B(grow(b, 1, 1, 0, 1), 'm', g, t))
    return out
