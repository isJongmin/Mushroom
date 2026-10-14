"""아바타: 마네킹(공통 몸) 치수, 파츠 정의(레이어별 상자 묶음 + 텍스처), 프리셋, 프레임 포즈.

좌표 (캐릭터 공간, 1 = 1px, 원점 = 두 발 사이 바닥 중앙 = 기준점 (24, 60))
  x: 정면 뷰에서 화면 오른쪽(캐릭터 왼쪽), y: 아래, z: 뒤. 캐릭터는 -z 를 본다.
  상자 (x0, x1, y0, y1, z0, z1) 는 x0 <= x < x1 ... 인 칸을 덮는다 (행 y0 .. y1-1).
  머리   x -10..10  y -39..-19  z -10..10   (정면 20x20, 윗면/옆면 4px)
  몸통   x  -6..6   y -19..-8   z  -4..4
  팔     x -10..-6 / 6..10, y -19..-8, z -3..3   (아래 3행 = 손)
  다리   x  -6..0 / 0..6,   y  -8..0,  z  -3..3   (아래 2행 = 신발 자리)
그룹(포즈 단위): head, torso, armR(캐릭터 오른팔 = 옆모습 카메라 쪽), armL, legR, legL.
텍스처 함수 tex(face, x, y, z, view) -> 재질 이름 | (재질, delta) | 팔레트 토큰 | None(투명)
  face: 'front'(-z면) 'back'(+z) 'top'(-y) 'bottom' 'left'(+x, 캐릭터 왼쪽) 'right'(-x, 캐릭터 오른쪽)
"""
import math
from render import Box

HEAD = (-10, 10, -39, -19, -10, 10)
TORSO = (-6, 6, -19, -8, -4, 4)
ARM_R = (-10, -6, -19, -8, -3, 3)
ARM_L = (6, 10, -19, -8, -3, 3)
LEG_R = (-6, 0, -8, 0, -3, 3)
LEG_L = (0, 6, -8, 0, -3, 3)

LAYER_ORDER = ['hair_back', 'skin', 'face', 'bottom', 'shoes', 'top', 'hair_front', 'hat']


def fl(v):
    return int(math.floor(v + 1e-6))


def nz(seed, *k):
    """좌표 해시 노이즈 0..1 (결정적)."""
    h = seed & 0xffffffff
    for v in k:
        h = (h ^ ((v & 0xffff) * 0x9E3779B1)) & 0xffffffff
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = (h * 0x85EBCA6B + 0x1234567) & 0xffffffff
    h ^= h >> 16
    return (h & 0xffff) / 65536.0


def B(b, layer, group, tex, name=''):
    return Box(*b, layer=layer, group=group, tex=tex, name=name)


def solid(mat):
    return lambda face, x, y, z, view: mat


def grow(b, gx=0, gy0=0, gy1=0, gz=0):
    x0, x1, y0, y1, z0, z1 = b
    return (x0 - gx, x1 + gx, y0 - gy0, y1 + gy1, z0 - gz, z1 + gz)


def face_uv(face, x, y, z):
    """면 위 정수 좌표 (u, v): front/back 은 (x, y), left/right 는 (z, y), top 은 (x, z). back 은 u 를 거울로."""
    ix, iy, iz = fl(x), fl(y), fl(z)
    if face == 'front':
        return ix, iy
    if face == 'back':
        return -ix - 1, iy
    if face in ('left', 'right'):
        return iz, iy
    return ix, iz


# =============================================================== skin
SKINS = [('light', '밝은 피부', 'skin_light'), ('medium', '보통 피부', 'skin_medium'), ('dark', '진한 피부', 'skin_dark')]


def body_boxes(mat='skin_light'):
    t = solid(mat)
    return [B(HEAD, 'skin', 'head', t, 'head'), B(TORSO, 'skin', 'torso', t),
            B(ARM_R, 'skin', 'armR', t), B(ARM_L, 'skin', 'armL', t),
            B(LEG_R, 'skin', 'legR', t), B(LEG_L, 'skin', 'legL', t)]


# =============================================================== face
E0 = -27            # 눈 맨 윗행
EYE_X = (-6, 4)     # 정면 눈 왼쪽 열 (캐릭터 오른눈, 왼눈). 2열 폭, 좌우 대칭(-6,-5 <-> 4,5)
SIDE_EYE = -7       # 옆모습 눈 앞쪽 열(z). 눈은 z -7, -6 (화면 x 6..7)


def eye_open(c, r):
    """2x3 동그란 눈: c=0..1, r=0..2. 왼쪽 위 하이라이트."""
    if not (0 <= c <= 1 and 0 <= r <= 2):
        return None
    return 'white' if (c, r) == (0, 0) else 'ink'


def eye_smile(c, r):
    """^ 눈 (3x2): c=-?: 정면 좌표에서 2열 눈 칸 기준 c=-1..1 사용 안 함 -> 0..2 로 3열."""
    if r == 1 and c == 1:
        return 'ink'
    if r == 2 and c in (0, 2):
        return 'ink'
    return None


def eye_closed(c, r):
    """감은 눈 (윙크): 아래로 둥근 선 3열."""
    if r == 1 and c in (0, 2):
        return 'ink'
    if r == 2 and c == 1:
        return 'ink'
    return None


def eye_sleepy(c, r):
    """졸린 눈: 눈꺼풀 3열 + 아래 반쪽 눈동자 2열."""
    if r == 1 and 0 <= c <= 2:
        return 'ink'
    if r == 2 and c in (1, 2):
        return 'ink'
    return None


FACES = {
    # id: (label, 오른눈(화면 왼쪽), 왼눈, 입 모양, 옆모습 눈)
    'basic':  ('기본', eye_open, eye_open, 'dot', eye_open),
    'smile':  ('웃음', eye_smile, eye_smile, 'smile', eye_smile),
    'wink':   ('윙크', eye_closed, eye_open, 'smile', eye_closed),
    'sleepy': ('졸린 눈', eye_sleepy, eye_sleepy, 'small', eye_sleepy),
}


def face_boxes(fid):
    label, eR, eL, mouth, eS = FACES[fid]
    wide = lambda f: f in (eye_smile, eye_closed, eye_sleepy)

    def eye_px(f, ix, iy, right):
        r = iy - E0
        if wide(f):        # 3열: 오른눈 -7..-5, 왼눈 4..6 (좌우 거울)
            c = ix + 7 if right else 6 - ix
            return f(c, r) if 0 <= c <= 2 else None
        c = ix + 6 if right else ix - 4   # 2열: 하이라이트는 두 눈 모두 왼쪽 위
        return f(c, r) if 0 <= c <= 1 else None

    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'front' and view == 'front':
            if E0 <= iy <= E0 + 2:
                c = eye_px(eR, ix, iy, True) if ix < 0 else eye_px(eL, ix, iy, False)
                if c:
                    return c
            if iy == E0 + 3 and ix in (-8, -7, 6, 7):
                return 'p2'
            if mouth == 'dot' and iy == E0 + 4 and ix in (-1, 0):
                return 'w4'
            if mouth == 'smile' and ((iy == E0 + 4 and ix in (-2, 1)) or (iy == E0 + 5 and ix in (-1, 0))):
                return 'w4'
            if mouth == 'small' and iy == E0 + 5 and ix in (-1, 0):
                return 'w4'
            return None
        if face == 'right' and view == 'side':
            # 옆모습: z=-10 이 화면 오른쪽 끝(앞). 화면 열 = -z. 눈은 화면 x 6..7 (z -7, -6)
            sc = -iz            # 화면 기준 열 (클수록 앞)
            r = iy - E0
            if wide(eS):
                c = 7 - sc       # 3열: 화면 5..7 -> c 2..0
                if 0 <= c <= 2 and 0 <= r <= 2:
                    col = eS(2 - c, r)
                    if col:
                        return col
            else:
                c = sc - 6       # 화면 6 -> c0 (하이라이트), 7 -> c1
                if 0 <= c <= 1 and 0 <= r <= 2:
                    return eye_open(c, r)
            if iy == E0 + 3 and sc in (4, 5):
                return 'p2'
            if iy == E0 + (5 if mouth == 'small' else 4) and sc == 9:
                return 'w4'
            return None
        return None
    return [B(HEAD, 'face', 'head', t, 'face')]


# =============================================================== hair
SHELL_Y0 = -40


def hair_tex(mat, front_end=None, side_end=None, back_end=None, strand=4, sseed=0):
    """머리 껍데기 텍스처.
    front_end(ix) / side_end(iz) / back_end(u): 그 행부터 아래는 투명(얼굴 창, 목덜미).
    결: 각 면의 끝단 1행은 strand 열마다 한 톤 어둡게(끝 갈라짐), 윗면은 깨끗하게."""
    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'top':
            return mat
        if face == 'front':
            end = front_end(ix) if front_end else 99
        elif face in ('left', 'right'):
            end = side_end(iz) if side_end else 99
        elif face == 'back':
            end = back_end(-ix - 1) if back_end else 99
        else:
            return mat
        if iy >= end:
            return None
        u = ix if face in ('front', 'back') else iz
        if iy == end - 1 and (u + sseed) % strand == 0:
            return (mat, 1)
        return mat
    return t


def lst(values, lo):
    """정수 인덱스 -> 값 (리스트 시작 인덱스 lo, 범위 밖은 끝 값)."""
    def f(i):
        k = i - lo
        return values[max(0, min(len(values) - 1, k))]
    return f


def shell(mat, front, side, back, nape=-20, sseed=0, name='shell'):
    """front: x -11..10 (22) 앞머리 끝 행, side: z -11..10 (22) 옆머리 끝 행, back: 열 22개 뒷머리 끝 행."""
    return B((-11, 11, SHELL_Y0, nape, -11, 11), 'hair', 'head',
             hair_tex(mat, lst(front, -11), lst(side, -11), lst(back, -11), sseed=sseed), name)


def lockbox(b, mat, tip=2, cut=1, name='lock', layer='hair', group='head', strand=0, slen=5):
    """머리 다발 상자. 끝 tip 행은 양옆 cut 칸씩 깎아 계단 끝단, 정면 가운데 결 1열."""
    x0, x1, y0, y1, z0, z1 = b

    def t(face, x, y, z, view):
        ix, iy, iz = fl(x), fl(y), fl(z)
        if face == 'top':
            return mat
        if face in ('front', 'back'):
            lo, hi = x0, x1 - 1
            u = ix
        elif face in ('left', 'right'):
            lo, hi = z0, z1 - 1
            u = iz
        else:
            return mat
        k = (y1 - 1) - iy            # 끝에서 몇 번째 행 (0 = 맨 끝)
        if k < tip:
            c = cut * (tip - k)
            if u < lo + c or u > hi - c:
                return None
        if k == 0:
            return (mat, 1)
        if strand and k < slen and (u - lo) % strand == strand - 1 and lo + 1 < u < hi - 1:
            return (mat, 1)                # 결 (끝단 쪽 세로 갈라짐)
        return mat
    return B(b, layer, group, t, name)


def side_profile(window_end, back_start, fringe, low, mid=None):
    """옆면 끝 행 목록 (z -11..10). z < back_start: fringe(얼굴 창 위), 이후 low(뒷머리 길이).
    window 와 뒷머리 경계에 1계단(mid)."""
    out = []
    for iz in range(-11, 11):
        if iz == -11:
            out.append(window_end)
        elif iz < back_start:
            out.append(fringe)
        elif iz == back_start and mid is not None:
            out.append(mid)
        else:
            out.append(low)
    return out


def hair_black_short():
    m = 'hair_black'
    front = [-26, -32, -33, -33, -32, -33, -34, -33, -32, -33, -33, -33, -33, -32, -33, -34, -33, -32, -33, -33, -32, -26]
    side = side_profile(-26, 3, -32, -22, mid=-27)
    back = [-21, -22, -21, -21, -22, -21, -21, -22, -21, -21, -22, -22, -21, -21, -22, -21, -21, -22, -21, -21, -22, -21]
    return [shell(m, front, side, back, nape=-20),
            B((-2, 1, -43, -40, -1, 2), 'hair', 'head', solid(m), 'tuft'),
            B((0, 1, -45, -43, -1, 2), 'hair', 'head', solid(m), 'tuft2')]


def hair_brown_short():
    m = 'hair_brown'
    # 옆가르마: 화면 왼쪽은 짧고 오른쪽으로 흘러내림
    front = [-26, -34, -34, -34, -33, -33, -33, -32, -32, -32, -31, -31, -31, -30, -30, -31, -32, -32, -33, -33, -33, -26]
    side = side_profile(-26, 3, -32, -22, mid=-27)
    back = [-21, -21, -22, -22, -21, -21, -21, -22, -22, -21, -21, -21, -22, -22, -21, -21, -21, -22, -22, -21, -21, -21]
    return [shell(m, front, side, back, nape=-20, sseed=1),
            B((-9, -3, -41, -40, -9, -1), 'hair', 'head', solid(m), 'part')]


def hair_blonde_spiky():
    m = 'hair_blonde'
    front = [-28, -32, -34, -32, -31, -33, -35, -33, -31, -32, -34, -34, -32, -31, -33, -35, -33, -31, -32, -34, -32, -28]
    side = side_profile(-28, 3, -32, -23, mid=-28)
    back = [-23, -22, -21, -22, -23, -22, -21, -22, -23, -22, -21, -21, -22, -23, -22, -21, -22, -23, -22, -21, -22, -23]
    spikes = [
        # 윗면 삐침 (밑동 4x4 + 끝 2x2 계단)
        (-9, -6, -43, -40, -6, -3), (-2, 1, -45, -40, -3, 0), (5, 8, -43, -40, -5, -2),
        # 옆으로 뻗은 삐침 (정면 실루엣)
        (-13, -11, -39, -35, 3, 7), (-14, -13, -38, -36, 4, 6),
        (11, 13, -39, -35, 3, 7), (13, 14, -38, -36, 4, 6),
        # 뒤로 뻗은 삐침 (옆모습 실루엣, 계단)
        (-6, 6, -40, -36, 11, 14), (-4, 4, -39, -37, 14, 16),
        (-6, 6, -33, -29, 11, 13), (-4, 4, -32, -30, 13, 15),
    ]
    out = [shell(m, front, side, back, nape=-21, sseed=2)]
    for i, b in enumerate(spikes):
        bx = B(b, 'hair', 'head', solid(m), 'spike%d' % i)
        bx.noao = True
        out.append(bx)
    return out


def hair_pink_long():
    m = 'hair_pink'
    front = [-17, -31, -32, -32, -33, -33, -32, -32, -31, -32, -33, -33, -32, -31, -32, -32, -33, -33, -32, -32, -31, -17]
    side = side_profile(-17, 2, -32, -14)
    back = [-14] * 22
    out = [shell(m, front, side, back, nape=-13, sseed=1, name='shell')]
    # 얼굴 옆 다발 (정면에서 얼굴 양옆, 어깨 앞으로 내려옴)
    out += [lockbox((-13, -10, -33, -14, -2, 3), m, tip=2, strand=3, name='lockR'),
            lockbox((10, 13, -33, -14, -2, 3), m, tip=2, strand=3, name='lockL')]
    # 뒷머리: 뒤통수부터 내려오는 다발 5개. 길이/깊이를 엇갈려 층과 결을 만든다(깊이 경계 그늘이 결 선이 됨)
    xs = [-12, -7, -2, 2, 7, 12]
    ends = [-10, -6, -4, -5, -9]
    zs = [(9, 12), (9, 13), (9, 14), (9, 13), (9, 12)]
    tops = [-37, -39, -38, -39, -37]
    for i in range(5):
        out.append(lockbox((xs[i], xs[i + 1], tops[i], ends[i], zs[i][0], zs[i][1]), m, tip=2, strand=3, slen=6, name='back%d' % i))
    # 아래층: 어깨 아래에서 한 겹 더 바깥으로 (볼륨)
    out.append(lockbox((-11, -4, -22, -7, 12, 14), m, tip=2, name='under0'))
    out.append(lockbox((3, 10, -22, -8, 12, 14), m, tip=2, name='under1'))
    return out


def hair_sky_bob():
    m = 'hair_sky'
    front = [-21, -21] + [-32] * 18 + [-21, -21]
    side = side_profile(-21, 1, -32, -21)
    back = [-21] * 22
    out = [shell(m, front, side, back, nape=-19, sseed=3)]
    # 옆: 얼굴 창 뒤로 다발 3개 (앞쪽이 길고 뒤로 갈수록 짧아지는 단발 라인, 바깥/안쪽 엇갈림)
    for sgn, nm in ((-1, 'R'), (1, 'L')):
        for i, (z0, z1, x_out, end) in enumerate(((1, 5, 13, -18), (5, 9, 12, -19), (9, 13, 13, -20))):
            xa, xb = (-x_out, -11) if sgn < 0 else (11, x_out)
            out.append(lockbox((xa, xb, -35, end, z0, z1), m, tip=2, cut=1, name='bob%s%d' % (nm, i)))
    # 뒤: 다발 4개, 깊이/길이 엇갈림
    xs = [-12, -6, 0, 6, 12]
    for i in range(4):
        z1 = 13 if i % 2 == 0 else 14
        out.append(lockbox((xs[i], xs[i + 1], -37, -20 + (i % 2), 11, z1), m, tip=2, cut=1, strand=3, name='bobB%d' % i))
    return out


def hair_tan_ponytail():
    m = 'hair_tan'
    front = [-26, -33, -33, -32, -32, -31, -31, -32, -33, -34, -34, -34, -34, -33, -33, -32, -32, -31, -31, -32, -32, -26]
    side = side_profile(-26, 3, -32, -24, mid=-27)
    back = [-22] * 22
    out = [shell(m, front, side, back, nape=-21, sseed=1)]
    out += [B((-3, 3, -34, -29, 11, 13), 'hair', 'head', solid('cloth_red'), 'tie'),
            lockbox((-3, 3, -35, -22, 13, 18), m, tip=0, name='tail1'),
            lockbox((-2, 3, -22, -14, 14, 18), m, tip=3, cut=1, strand=3, name='tail2')]
    return out


def hair_black_twintail():
    m = 'hair_black'
    front = [-26, -31, -32, -33, -33, -32, -31, -32, -33, -33, -32, -32, -33, -33, -32, -31, -32, -33, -33, -32, -31, -26]
    side = side_profile(-26, 3, -32, -22, mid=-27)
    back = [-21] * 22
    out = [shell(m, front, side, back, nape=-20, sseed=2)]
    for sgn, nm in ((-1, 'R'), (1, 'L')):
        def X(a, b):
            return (a, b) if sgn < 0 else (-b, -a)
        x0, x1 = X(-14, -11)
        out.append(B((x0, x1, -35, -31, 2, 7), 'hair', 'head', solid('cloth_pink'), 'tie' + nm))
        x0, x1 = X(-15, -11)
        out.append(lockbox((x0, x1, -31, -21, 2, 7), m, tip=0, name='tw1' + nm))
        x0, x1 = X(-14, -11)
        out.append(lockbox((x0, x1, -21, -13, 3, 7), m, tip=3, cut=1, name='tw2' + nm))
    return out


def hair_mint_curly():
    m = 'hair_mint'
    front = [-25, -32, -33, -34, -33, -32, -33, -34, -33, -32, -33, -33, -32, -33, -34, -33, -32, -33, -34, -33, -32, -25]
    side = side_profile(-25, 3, -31, -21, mid=-26)
    back = [-21] * 22
    out = [shell(m, front, side, back, nape=-20, sseed=0)]
    bumps = [(-13, -7, -42, -36, -12, -6), (-6, 0, -43, -38, -12, -6), (1, 7, -42, -37, -12, -6), (7, 13, -41, -35, -12, -6),
             (-8, -1, -43, -40, -2, 5), (1, 8, -43, -40, 2, 9),
             (-13, -11, -38, -32, -4, 3), (-13, -11, -31, -24, 4, 10), (11, 13, -39, -33, -4, 2), (11, 13, -32, -25, 3, 9),
             (-12, -5, -35, -28, 10, 13), (-4, 4, -31, -22, 10, 13), (5, 12, -36, -29, 10, 13), (-11, -4, -26, -19, 9, 12),
             (4, 11, -27, -20, 9, 12)]
    for i, b in enumerate(bumps):
        out.append(B(b, 'hair', 'head', solid(m), 'bump%d' % i))
    return out


HAIRS = [
    ('black-short', '검은 짧은 머리', hair_black_short),
    ('brown-short', '밤색 짧은 머리', hair_brown_short),
    ('blonde-spiky', '금발 뻗친 머리', hair_blonde_spiky),
    ('pink-long', '분홍 긴 머리', hair_pink_long),
    ('sky-bob', '하늘색 단발', hair_sky_bob),
    ('tan-ponytail', '갈색 포니테일', hair_tan_ponytail),
    ('black-twintail', '검은 양갈래', hair_black_twintail),
    ('mint-curly', '민트 곱슬', hair_mint_curly),
]


# =============================================================== hats
def hat_cap_white():
    w = 'cloth_white'

    def crown(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front' and -2 <= ix <= 1 and -40 <= iy <= -39:
            return 'cloth_red'
        if iy == -36 and face != 'top':
            return (w, 1)
        return w
    return [B((-12, 12, -42, -35, -12, 12), 'hat', 'head', crown, 'crown'),
            B((-1, 1, -43, -42, -1, 1), 'hat', 'head', solid('cloth_red'), 'button'),
            B((-11, 11, -36, -34, -19, -12), 'hat', 'head', solid(w), 'brim')]


def dotted(mat, dots):
    """dots: {face_kind: [(u0, v0, w, h)]}  face_kind in front/side/top (back 은 front 거울, left/right 은 side)."""
    def inr(lst_, a, b):
        return any(x0 <= a < x0 + ww and y0 <= b < y0 + hh for x0, y0, ww, hh in lst_)

    def t(face, x, y, z, view):
        u, v = face_uv(face, x, y, z)
        kind = {'front': 'front', 'back': 'front', 'left': 'side', 'right': 'side', 'top': 'top'}.get(face)
        if face == 'right':
            u = -u - 1
        if kind and inr(dots.get(kind, []), u, v):
            return 'dot'
        return mat
    return t


def hat_mushroom_red():
    low = dotted('cap_red', {'front': [(-12, -41, 3, 3), (-1, -40, 4, 3), (8, -42, 3, 3)],
                             'side': [(-9, -41, 3, 3), (3, -40, 4, 3)],
                             'top': [(-13, -10, 3, 3), (9, -12, 3, 4), (10, 8, 3, 3)]})
    up = dotted('cap_red', {'front': [(-6, -48, 3, 3), (4, -47, 3, 2)],
                            'side': [(-5, -48, 3, 3)],
                            'top': [(-8, -6, 4, 4), (2, 2, 4, 5), (-4, 6, 3, 3)]})
    return [B((-14, 14, -43, -37, -14, 14), 'hat', 'head', low, 'cap_low'),
            B((-10, 10, -50, -43, -10, 10), 'hat', 'head', up, 'cap_up'),
            B((-12, 12, -37, -35, -12, 12), 'hat', 'head', solid('stem'), 'gill')]


def hat_explorer_brown():
    m = 'cloth_brown'

    def crown(face, x, y, z, view):
        iy = fl(y)
        if face != 'top' and -39 <= iy <= -38:
            return 'cloth_dark'
        return m

    def top(face, x, y, z, view):
        if face == 'top':
            u, v = face_uv(face, x, y, z)
            if -1 <= u <= 0:
                return (m, 1)          # 가운데 접힌 자국
        return m
    return [B((-16, 16, -37, -35, -16, 16), 'hat', 'head', solid(m), 'brim'),
            B((-11, 11, -45, -37, -11, 11), 'hat', 'head', crown, 'crown'),
            B((-9, 9, -46, -45, -9, 9), 'hat', 'head', top, 'top')]


def hat_beanie_yellow():
    m = 'cloth_yellow'

    def knit(face, x, y, z, view):
        if face == 'top':
            return m
        u, v = face_uv(face, x, y, z)
        return (m, 1) if u % 3 == 0 else m

    def cuff(face, x, y, z, view):
        if face == 'top':
            return m
        u, v = face_uv(face, x, y, z)
        return (m, 1) if u % 2 == 0 and fl(y) == -33 else m
    return [B((-12, 12, -43, -36, -12, 12), 'hat', 'head', knit, 'crown'),
            B((-10, 10, -45, -43, -10, 10), 'hat', 'head', knit, 'crown2'),
            B((-13, 13, -37, -32, -13, 13), 'hat', 'head', cuff, 'cuff'),
            B((-3, 3, -50, -45, -3, 3), 'hat', 'head', solid('cloth_cream'), 'pom')]


def hat_ribbon_pink():
    m = 'cloth_pink'
    cx = 4

    def wing(face, x, y, z, view):
        return m

    def knot(face, x, y, z, view):
        return (m, 1)
    return [B((cx - 2, cx + 2, -44, -40, -5, 0), 'hat', 'head', knot, 'knot'),
            B((cx - 5, cx - 2, -44, -40, -4, 0), 'hat', 'head', wing, 'wR1'),
            B((cx - 9, cx - 5, -46, -39, -4, 0), 'hat', 'head', wing, 'wR2'),
            B((cx + 2, cx + 5, -44, -40, -4, 0), 'hat', 'head', wing, 'wL1'),
            B((cx + 5, cx + 9, -46, -39, -4, 0), 'hat', 'head', wing, 'wL2')]


HATS = [
    ('none', '없음', None),
    ('cap-white', '흰 야구모자', hat_cap_white),
    ('mushroom-red', '빨간 버섯 모자', hat_mushroom_red),
    ('explorer-brown', '갈색 탐험가 모자', hat_explorer_brown),
    ('beanie-yellow', '노란 비니', hat_beanie_yellow),
    ('ribbon-pink', '분홍 리본', hat_ribbon_pink),
]


# =============================================================== tops
SLEEVE_END = -11     # 긴 소매 아래 끝(행 -12 까지), 손 = 행 -11..-9


def sleeves(tex, end=SLEEVE_END, puff=0):
    return [B((-10 - puff, -6, -19, end, -3 - puff, 3 + puff), 'top', 'armR', tex, 'sleeveR'),
            B((6, 10 + puff, -19, end, -3 - puff, 3 + puff), 'top', 'armL', tex, 'sleeveL')]


def top_hoodie(mat, string):
    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            if ix in (-3, 2) and -18 <= iy <= -15:
                return string
            if -4 <= ix <= 3 and iy == -12:
                return (mat, 1)            # 주머니 윗선
        if face != 'top' and iy == -9:
            return (mat, 1)                # 밑단 립
        return mat

    def sleeve(face, x, y, z, view):
        return (mat, 1) if fl(y) == SLEEVE_END - 1 and face != 'top' else mat

    def hood(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'back' and ix in (-1, 0) and iy < -14:
            return (mat, 1)
        if face == 'top':
            return (mat, 2)                # 후드 안쪽 그늘
        return mat
    return [B(TORSO, 'top', 'torso', body, 'torso')] + sleeves(sleeve) + \
        [B((-5, 5, -21, -13, 4, 7), 'top', 'torso', hood, 'hood')]


def top_blouse_white():
    w, p = 'cloth_white', 'cloth_pink'
    bow = {(-3, -17): p, (-2, -17): p, (1, -17): p, (2, -17): p, (-3, -16): p, (2, -16): p,
           (-1, -17): (p, 1), (0, -17): (p, 1), (-1, -16): (p, 1), (0, -16): (p, 1),
           (-2, -16): p, (1, -16): p, (-2, -15): p, (1, -15): p, (-2, -14): p, (1, -14): p}

    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front' and (ix, iy) in bow:
            return bow[(ix, iy)]
        if face == 'front' and iy == -19 and ix in (-5, -4, 3, 4):
            return (w, 1)                  # 칼라
        if iy == -9 and face != 'top':
            return p                       # 분홍 밑단
        return w

    def sleeve(face, x, y, z, view):
        return p if fl(y) == -15 and face != 'top' else w
    return [B(TORSO, 'top', 'torso', body, 'torso')] + sleeves(sleeve, end=-14, puff=1)


def top_overalls_green():
    tee, g = 'cloth_cream', 'cloth_green'
    strap_x = (-5, -4, 3, 4)

    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face == 'front':
            if iy == -15 and ix in (-4, 3):
                return 'gold'
            if -4 <= ix <= 3 and iy >= -15:
                if -2 <= ix <= 1 and iy in (-13, -12) and (iy == -13 or ix in (-2, 1)):
                    return (g, 1)          # 가슴 주머니
                return g
            if ix in strap_x and iy < -15:
                return g
            if iy >= -11:
                return g
            return tee
        if face == 'back':
            u, v = face_uv(face, x, y, z)
            if u in strap_x or iy >= -12:
                return g
            return tee
        if face == 'top':
            return g if ix in strap_x else tee
        if face in ('left', 'right'):
            return g if iy >= -11 else tee
        return tee

    def sleeve(face, x, y, z, view):
        return (tee, 1) if fl(y) == -16 and face != 'top' else tee
    return [B(TORSO, 'top', 'torso', body, 'torso')] + sleeves(sleeve, end=-15)


def top_tee_stripe_red():
    r, s = 'cloth_red', 'cloth_cream'

    def body(face, x, y, z, view):
        iy = fl(y)
        if face == 'top':
            return r
        if iy in (-17, -14, -11):
            return s
        return r

    def sleeve(face, x, y, z, view):
        iy = fl(y)
        if face != 'top' and iy == -17:
            return s
        return r
    return [B(TORSO, 'top', 'torso', body, 'torso')] + sleeves(sleeve, end=-15)


def top_cape_blue():
    b, d = 'cloth_blue', 'cloth_deep'

    def body(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if face != 'top' and iy == -10:
            return 'gold'                  # 허리띠
        if face == 'front' and iy in (-18, -17) and ix in (-5, 4):
            return 'gold'                  # 망토 고리
        if face == 'front' and ix in (-1, 0) and -16 <= iy <= -11:
            return (b, -1)                 # 앞섶
        return b

    def sleeve(face, x, y, z, view):
        return 'gold' if fl(y) == SLEEVE_END - 1 and face != 'top' else b

    def cape(face, x, y, z, view):
        u, v = face_uv(face, x, y, z)
        iy = fl(y)
        if face == 'back' and u % 4 == 1 and iy > -15:
            return (d, 1)                  # 주름
        return d

    def collar(face, x, y, z, view):
        return d
    return [B(TORSO, 'top', 'torso', body, 'torso')] + sleeves(sleeve) + \
        [B((-7, 7, -19, -9, 4, 7), 'top', 'torso', cape, 'cape1'),
         lockbox((-8, 8, -9, -3, 4, 8), d, tip=1, cut=1, name='cape2', layer='top', group='torso'),
         B((-7, 7, -21, -18, 3, 5), 'top', 'torso', collar, 'collar')]


TOPS = [
    ('hoodie-black', '검은 후드티', lambda: top_hoodie('cloth_black', 'white')),
    ('hoodie-white', '흰 후드티', lambda: top_hoodie('cloth_white', 'cloth_red')),
    ('blouse-white', '흰 블라우스', top_blouse_white),
    ('overalls-green', '초록 멜빵', top_overalls_green),
    ('tee-stripe-red', '빨간 줄무늬 티', top_tee_stripe_red),
    ('cape-blue', '파란 망토 셔츠', top_cape_blue),
]


# =============================================================== bottoms
def legs(tex, y0=-8, y1=-2):
    return [B((-6, 0, y0, y1, -3, 3), 'bottom', 'legR', tex, 'legR'),
            B((0, 6, y0, y1, -3, 3), 'bottom', 'legL', tex, 'legL')]


def pant_tex(mat, cuff=None, seam=True):
    def t(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if cuff is not None and iy == cuff and face != 'top':
            return (mat, -1)
        if seam and face == 'front' and ix == -1 and iy >= -6:
            return (mat, 1)                # 다리 사이 그늘
        return mat
    return t


def bottom_skirt_pink():
    m = 'cloth_pink'

    def low(face, x, y, z, view):
        u, v = face_uv(face, x, y, z)
        if face != 'top' and u % 3 == 0:
            return (m, 1)                  # 주름
        return m
    return [B((-7, 7, -10, -7, -5, 5), 'bottom', 'torso', solid(m), 'skirt_up'),
            B((-8, 8, -7, -4, -6, 6), 'bottom', 'torso', low, 'skirt_low')]


def bottom_jeans():
    m = 'cloth_jean'

    def t(face, x, y, z, view):
        ix, iy = fl(x), fl(y)
        if iy == -3 and face != 'top':
            return (m, -1)                 # 접어 올린 밑단
        if face == 'front' and ix == -1 and iy >= -6:
            return (m, 1)
        if face == 'front' and ix in (-4, 3) and -8 <= iy <= -7:
            return (m, 1)                  # 주머니
        return m
    return legs(t)


BOTTOMS = [
    ('pants-navy', '남색 바지', lambda: legs(pant_tex('cloth_navy'))),
    ('pants-black', '검은 바지', lambda: legs(pant_tex('cloth_dark'))),
    ('skirt-pink', '분홍 치마', bottom_skirt_pink),
    ('shorts-brown', '갈색 반바지', lambda: legs(pant_tex('cloth_tan', cuff=-5, seam=False), y1=-4)),
    ('jeans-blue', '청바지', bottom_jeans),
]


# =============================================================== shoes
def shoe_boxes(tex, h=2):
    return [B((-7, 0, -h, 0, -4, 3), 'shoes', 'legR', tex, 'shoeR'),
            B((0, 7, -h, 0, -4, 3), 'shoes', 'legL', tex, 'shoeL')]


def shoe_tex(mat, sole, strap=None, cuff=None):
    def t(face, x, y, z, view):
        iy = fl(y)
        if iy == -1 and face != 'top':
            return sole
        if strap and face == 'top':
            u, v = face_uv(face, x, y, z)
            if v == -1:
                return strap               # 메리제인 끈 (발등)
        if cuff is not None and iy == cuff and face != 'top':
            return (mat, -1)
        return mat
    return t


SHOES = [
    ('sneakers-white', '흰 운동화', lambda: shoe_boxes(shoe_tex('shoe_white', 'c3'))),
    ('maryjane-red', '빨간 메리제인', lambda: shoe_boxes(shoe_tex('shoe_red', 'r3', strap='r3'))),
    ('boots-brown', '갈색 부츠', lambda: shoe_boxes(shoe_tex('shoe_brown', 'w4', cuff=-4), h=4)),
    ('sneakers-black', '검은 운동화', lambda: shoe_boxes(shoe_tex('shoe_black', 'white'))),
]


# =============================================================== registry
def parts_table():
    """{category: [(id, label, boxes_fn)]}  manifest parts 순서 = 이 순서 (첫 항목이 기본값)."""
    return {
        'skin': [(i, l, (lambda m=m: body_boxes(m))) for i, l, m in SKINS],
        'hair': HAIRS,
        'face': [(i, FACES[i][0], (lambda i=i: face_boxes(i))) for i in FACES],
        'top': TOPS,
        'bottom': BOTTOMS,
        'shoes': SHOES,
        'hat': HATS,
    }


PRESETS = [
    ('후드 소년', {'skin': 'light', 'hair': 'black-short', 'face': 'basic', 'top': 'hoodie-black',
               'bottom': 'pants-navy', 'shoes': 'sneakers-white', 'hat': 'none'}),
    ('분홍 소녀', {'skin': 'light', 'hair': 'pink-long', 'face': 'basic', 'top': 'blouse-white',
               'bottom': 'skirt-pink', 'shoes': 'maryjane-red', 'hat': 'none'}),
    ('모자 소년', {'skin': 'light', 'hair': 'brown-short', 'face': 'smile', 'top': 'hoodie-white',
               'bottom': 'pants-black', 'shoes': 'sneakers-black', 'hat': 'cap-white'}),
    ('버섯 꼬마', {'skin': 'light', 'hair': 'blonde-spiky', 'face': 'basic', 'top': 'overalls-green',
               'bottom': 'jeans-blue', 'shoes': 'boots-brown', 'hat': 'mushroom-red'}),
    ('하늘 마법사', {'skin': 'medium', 'hair': 'sky-bob', 'face': 'wink', 'top': 'cape-blue',
                'bottom': 'pants-navy', 'shoes': 'boots-brown', 'hat': 'none'}),
    ('탐험가', {'skin': 'dark', 'hair': 'black-twintail', 'face': 'smile', 'top': 'tee-stripe-red',
             'bottom': 'shorts-brown', 'shoes': 'sneakers-white', 'hat': 'explorer-brown'}),
]


# =============================================================== frames
LEG_PIV, ARM_PIV = -8, -18
LEG_SW, ARM_SW = 5.5, 5.0        # 발끝/손끝 스윙 폭(px)


def walk_pose(k):
    """k=0: 오른다리(카메라 쪽) 앞 + 왼다리 뒤, 몸 1px 아래 / 1: 교차(왼발 2px 들고 앞으로) / 2: 반대 / 3: 교차(오른발)."""
    sl, sa = LEG_SW / 8, ARM_SW / 10
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
        lift, stand = ('legL', 'legR') if k == 1 else ('legR', 'legL')
        p[lift] = {'shear': -0.25, 'pivot': LEG_PIV, 'd': (0, -2, 0)}
        p[stand] = {'shear': 0.12, 'pivot': LEG_PIV}
        arm_f, arm_b = ('armR', 'armL') if k == 1 else ('armL', 'armR')
        p[arm_f] = {'shear': -0.12, 'pivot': ARM_PIV}
        p[arm_b] = {'shear': 0.12, 'pivot': ARM_PIV}
    return p


FRAMES = [('front', 'front', None), ('side_idle', 'side', None)] + \
         [('side_walk%d' % k, 'side', walk_pose(k)) for k in range(4)] + [('back', 'back', None)]


def mannequin_clothed():
    """머리카락 앞/뒤 분리용: 몸통·팔·다리를 1px 부풀린 가상 몸 (머리 제외)."""
    t = solid('skin_light')
    out = []
    for b, g in ((TORSO, 'torso'), (ARM_R, 'armR'), (ARM_L, 'armL'), (LEG_R, 'legR'), (LEG_L, 'legL')):
        out.append(B(grow(b, 1, 1, 0, 1), 'm', g, t))
    return out
