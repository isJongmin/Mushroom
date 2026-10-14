"""voxel_v1 캐릭터 모델: 마네킹(뼈대) + 교체 파츠. 단위 = 복셀 1칸 (최종 약 2.1px).

캐릭터 로컬 좌표: +x = 캐릭터의 왼쪽(정면에서 화면 오른쪽), +y 위, +z 앞(바라보는 방향), 발바닥 y=0.
뼈(bone): root, torso, head, arm+/arm-, leg+/leg- (부호 = x 쪽).
파츠 함수는 (bone, center, half, color, ...) 목록을 돌려주고, assemble()이 포즈를 적용해 Box 목록을 만든다.
"""
import numpy as np
from vox import Box, rot_x, rot_z, rot_y, BEVEL

# ------------------------------------------------------------------ 치수 (마네킹)
HEAD_PIVOT = (0, 22.0, 0)
HEAD_H = (11.0, 10.0, 10.0)      # 머리 22 x 20 x 20
SHOULDER = (8.7, 20.6, 0)
HIP = (3.3, 9.5, 0)

SKINS = {'light': '#FAD3BA', 'tan': '#E9B48C'}


def P(bone, c, h, col, **kw):
    return dict(bone=bone, c=c, h=h, col=col, **kw)


# ------------------------------------------------------------------ skin (= 마네킹, 다른 레이어의 깊이 마스크)
def skin(tone='light'):
    s = SKINS[tone]
    out = [
        P('head', (0, 10, 0), HEAD_H, s, noise=0.015),
        P('torso', (0, 21.3, 0), (3.6, 1.6, 3.6), s, noise=0.015),          # 목
        P('torso', (0, 15.6, 0), (6.8, 5.9, 3.8), s, noise=0.015),          # 몸통
        P('torso', (0, 9.3, 0), (6.2, 1.2, 3.6), s, noise=0.015),           # 골반
    ]
    for sg in (1, -1):
        out += [P('arm%+d' % sg, (0, -4.6, 0), (2.15, 4.9, 2.15), s, noise=0.015),
                P('arm%+d' % sg, (0, -11.1, 0), (2.35, 2.1, 2.35), s, noise=0.015),   # 손 (뭉툭)
                P('leg%+d' % sg, (0, -4.6, 0), (2.8, 4.75, 2.8), s, noise=0.015)]
    return out


# ------------------------------------------------------------------ face (머리 앞면 데칼, 머리 로컬)
def face(kind='basic'):
    z = 10.0
    D = dict(decal=True, bevel=0, noise=0.0)
    out = []
    for sg in (1, -1):
        ex = sg * 4.9
        out += [
            P('head', (ex, 7.9, z + 0.04), (2.3, 3.5, 0.04), '#22171C', **D),           # 눈 (진갈색-검정)
            P('head', (ex, 6.0, z + 0.08), (1.55, 1.6, 0.04), '#4E3029', **D),           # 아래 홍채 (갈색)
            P('head', (ex, 5.2, z + 0.10), (1.0, 0.75, 0.04), '#7E5140', **D),           # 홍채 반사
            P('head', (ex - sg * 0.6, 9.7, z + 0.12), (1.0, 1.05, 0.04), '#FFFFFF', **D),    # 큰 하이라이트
            P('head', (ex + sg * 1.0, 5.0, z + 0.12), (0.5, 0.5, 0.04), '#FFF4EA', **D),     # 작은 반사점
            P('head', (sg * 7.8, 3.7, z + 0.04), (1.8, 0.8, 0.04), '#F4999F', **D),      # 볼터치
        ]
    out.append(P('head', (0, 2.6, z + 0.04), (0.85, 0.42, 0.04), '#A8475A', **D))         # 입
    return out


# ------------------------------------------------------------------ hair
def _rng(seed):
    return np.random.default_rng(seed)


def hair_curly(col='#30231F', seed=7):
    """검은 곱슬: 큰 판(슬랩) 덩어리를 기와처럼 층층이 겹친 껍데기 + 바깥으로 삐친 큐브."""
    H = dict(noise=0.07)
    r = _rng(seed)
    out = [
        P('head', (0, 20.6, -0.6), (11.7, 1.6, 10.9), col, **H),       # 정수리 바탕
        P('head', (0, 11.6, -10.9), (11.6, 9.4, 1.2), col, **H),       # 뒤통수 바탕
    ]
    for sg in (1, -1):
        out += [P('head', (sg * 11.8, 14.6, -2.4), (1.2, 6.4, 8.8), col, **H),      # 옆 바탕
                P('head', (sg * 11.7, 8.9, 5.4), (1.05, 2.5, 2.0), col, **H)]       # 구레나룻
    out.append(P('head', (0, 17.4, 10.85), (11.7, 2.6, 1.2), col, **H))         # 앞머리 바탕

    def chunk(c, h, k=None):
        k = r.uniform(-0.10, 0.16) if k is None else k
        out.append(P('head', c, h, _tint(col, k), **H))

    # 정수리: 4x4 큰 덩어리, 가운데일수록 높게
    for ix, gx in enumerate(np.linspace(-8.4, 8.4, 4)):
        for iz, gz in enumerate(np.linspace(-8.2, 8.2, 4)):
            mid = 1.0 - (abs(gx) + abs(gz)) / 20
            chunk((gx + r.uniform(-1.3, 1.3), 22.3 + mid * 1.6 + r.uniform(-0.6, 0.9), gz + r.uniform(-1.3, 1.3)),
                  (r.uniform(1.9, 3.4), r.uniform(1.2, 2.1), r.uniform(1.9, 3.4)))
    # 앞머리 위 (이마 위로 볼록) - 앞으로 2칸 튀어나온 층
    for x in (-8.6, -4.3, 0.0, 4.3, 8.6):
        chunk((x + r.uniform(-0.5, 0.5), 20.0 + r.uniform(-0.3, 0.8), 11.2 + r.uniform(0.2, 1.0)),
              (r.uniform(2.2, 2.7), r.uniform(1.6, 2.1), r.uniform(1.3, 1.8)))
    # 앞머리 가닥: 굵은 세로 판 2겹 (뒤 겹이 더 길고 어둡다), 들쭉날쭉한 끝
    for x, yb in [(-9.6, 12.4), (-5.6, 11.4), (-1.8, 12.2), (2.0, 11.2), (5.8, 12.1), (9.6, 12.8)]:
        top = 16.6
        chunk((x, (yb + top) / 2, 11.2), (2.0, (top - yb) / 2, 1.25), r.uniform(-0.08, 0.04))
    for x, yb in [(-7.6, 13.6), (-3.7, 13.3), (0.1, 13.8), (3.9, 13.4), (7.7, 13.9)]:
        top = 17.8
        chunk((x, (yb + top) / 2, 12.0), (1.9, (top - yb) / 2, 0.9), r.uniform(0.0, 0.12))
    # 옆: 위->아래 3단 기와, 크기/위치 불규칙, 아래로 갈수록 좁고 어둡게, 바깥으로 1~2칸
    for sg in (1, -1):
        for row, (y, ext) in enumerate([(18.2, 13.5), (14.0, 13.1), (9.8, 12.8)]):
            zs = [-8.0, -3.2, 2.2] if row < 2 else [-6.0, 0.4]
            for z in zs:
                hz = r.uniform(1.6, 3.2)
                chunk((sg * (ext + r.uniform(-0.5, 0.5)), y + r.uniform(-1.2, 1.0), z + r.uniform(-1.4, 1.4)),
                      (r.uniform(1.1, 1.7), r.uniform(1.5, 2.6), hz), r.uniform(-0.12 - row * 0.03, 0.10))
        chunk((sg * 13.0, 15.5, 6.8), (1.4, 2.6, 1.8))                       # 관자 앞 삐침
    # 뒤: 4단 기와 (엇갈림 폭/높이 불규칙)
    for row, (y, ext) in enumerate([(18.6, 13.3), (14.4, 13.0), (10.4, 12.7), (6.6, 12.3)]):
        xs = np.cumsum(r.uniform(3.6, 6.4, 6)) - 12.5 - r.uniform(0, 2)
        for x in xs[xs < 10.5]:
            chunk((x, y + r.uniform(-1.1, 1.1), -(ext + r.uniform(-0.5, 0.4))),
                  (r.uniform(1.8, 3.2), r.uniform(1.6, 2.6), r.uniform(1.0, 1.6)), r.uniform(-0.12 - row * 0.03, 0.10))
    # 바깥으로 크게 삐친 큐브 (실루엣 들쭉날쭉)
    for c, h in [((-12.8, 21.6, 2.0), (1.8, 1.6, 2.0)), ((13.2, 20.8, -3.0), (1.9, 1.5, 2.1)),
                 ((-3.0, 25.4, -2.5), (1.6, 1.3, 1.8)), ((4.8, 25.0, 1.5), (1.5, 1.2, 1.6)),
                 ((9.6, 23.6, 7.6), (1.6, 1.4, 1.6)), ((-9.8, 23.4, -8.0), (1.7, 1.4, 1.7)),
                 ((0.5, 22.8, -13.2), (1.8, 1.6, 1.3)), ((-13.4, 13.5, -6.0), (1.3, 1.6, 1.8))]:
        chunk(c, h)
    return out


def hair_wavy(col='#6E4430', seed=11):
    """밤색 긴 웨이브: 옆/뒤가 어깨 아래까지(back 플래그), 옆 가르마 앞머리, 정수리 더듬이."""
    H = dict(noise=0.08)
    out = [
        P('head', (0, 20.7, -0.4), (11.8, 1.7, 11.0), col, **H),
        P('head', (0, 10.5, -11.0), (11.8, 10.6, 1.4), col, **H),
    ]
    for sg in (1, -1):
        out += [P('head', (sg * 11.9, 12.0, -2.0), (1.3, 9.0, 9.2), col, **H),
                P('head', (sg * 12.1, 3.2, 3.0), (1.5, 3.4, 4.2), _tint(col, -0.06), **H),   # 옆 웨이브 (턱 아래)
                P('head', (sg * 12.9, 13.0, -4.0), (1.3, 3.0, 3.4), _tint(col, 0.08), **H),
                P('head', (sg * 12.7, 7.0, -1.0), (1.3, 2.6, 3.2), _tint(col, -0.05), **H)]
    # 뒤통수 웨이브 기와 (머리 위쪽은 front, 목 아래로 내려오는 부분은 back)
    r0 = _rng(seed + 1)
    for row, y in enumerate([17.5, 13.0, 8.5, 4.0, -0.5, -4.8]):
        w = 11.6 - max(0, row - 3) * 1.8
        xs = np.cumsum(r0.uniform(4.0, 6.0, 6)) - w - r0.uniform(0, 1.5)
        for x in xs[xs < w - 1.0]:
            out.append(P('head', (x, y + r0.uniform(-0.8, 0.8), -12.2 - (row % 2) * 0.5),
                         (r0.uniform(2.0, 2.9), r0.uniform(2.0, 2.6), 1.3), _tint(col, r0.uniform(-0.12, 0.10)),
                         back=y < 1.5, **H))
    out.append(P('head', (0, 17.3, 10.9), (11.8, 2.9, 1.3), col, **H))
    # 옆 가르마: 오른쪽(화면 왼쪽)으로 쓸린 가닥
    for x, yb, hw in [(-9.6, 12.2, 2.2), (-5.8, 12.6, 2.0), (-2.0, 13.4, 1.9), (1.8, 14.2, 1.9), (5.6, 14.8, 1.9), (9.6, 13.0, 2.1)]:
        out.append(P('head', (x, (yb + 15.6) / 2, 11.1), (hw, (15.6 - yb) / 2, 1.2), col, **H))
    r = _rng(seed)
    for gx in np.linspace(-8.5, 8.5, 4):
        for gz in np.linspace(-8.5, 8, 4):
            out.append(P('head', (gx + r.uniform(-1, 1), 22.0 + r.uniform(0, 1.0), gz + r.uniform(-1, 1)),
                         (r.uniform(2.2, 3.0), r.uniform(1.0, 1.6), r.uniform(2.2, 3.0)), _tint(col, r.uniform(-0.08, 0.1)), **H))
    # 더듬이 (아호게)
    out += [P('head', (1.0, 24.6, 3.0), (0.8, 1.4, 0.8), col, **H),
            P('head', (2.2, 26.0, 3.6), (0.8, 0.9, 0.8), _tint(col, 0.08), **H)]
    return out


def _tint(hexcol, k):
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float)
    c = c * (1 + k) if k < 0 else c + (255 - c) * k * 0.6
    c = np.clip(np.round(c), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


# ------------------------------------------------------------------ top
def top_hoodie(col='#F4EDE2'):
    rib = _tint(col, -0.07)
    cord = '#C9BFB4'
    out = [
        P('torso', (0, 15.7, 0), (7.5, 6.1, 4.5), col),                          # 몸판
        P('torso', (0, 10.0, 0), (7.75, 0.85, 4.72), rib),                         # 밑단 립
        P('torso', (0, 13.3, 4.65), (4.6, 2.3, 0.35), col),                        # 캥거루 주머니
        P('torso', (0, 22.4, -6.4), (6.8, 3.2, 3.1), col),                         # 후드 (목 뒤 덩어리)
        P('torso', (0, 24.8, -8.6), (5.6, 1.6, 1.4), _tint(col, -0.04)),           # 후드 위 접힘
        P('torso', (0, 19.6, -9.0), (5.0, 1.5, 1.0), _tint(col, -0.06)),           # 후드 아래 처짐
    ]
    for sg in (1, -1):
        out += [
            P('torso', (sg * 5.3, 22.2, -0.8), (1.6, 1.7, 3.9), col),              # 후드 옆 (목 감싸기)
            P('torso', (sg * 1.7, 18.4, 4.6), (0.45, 2.3, 0.12), '#B5AA9E', decal=True, bevel=0, noise=0),  # 끈
            P('torso', (sg * 1.7, 15.7, 4.65), (0.6, 0.6, 0.2), '#ADA398', bevel=0.15, noise=0),     # 끈 끝
            P('arm%+d' % sg, (0, -4.0, 0), (2.6, 5.0, 2.6), col),                  # 소매
            P('arm%+d' % sg, (0, -8.8, 0), (2.95, 1.05, 2.95), rib),               # 소매 끝 (살짝 넓게)
        ]
    return out


def top_tee(col='#F7C948'):
    out = [
        P('torso', (0, 15.7, 0), (7.4, 6.1, 4.4), col),
        P('torso', (0, 10.0, 0), (7.6, 0.7, 4.6), _tint(col, -0.08)),
        P('torso', (0, 21.9, 0), (4.0, 0.4, 3.9), _tint(col, -0.12)),           # 목 테두리
    ]
    # 가슴 버섯 엠블럼 (데칼)
    D = dict(decal=True, bevel=0, noise=0)
    out += [P('torso', (0, 17.4, 4.44), (2.2, 1.0, 0.04), '#E8483E', **D),
            P('torso', (0, 16.9, 4.48), (0.5, 0.4, 0.04), '#FFFFFF', **D),
            P('torso', (-1.3, 17.8, 4.48), (0.4, 0.35, 0.04), '#FFFFFF', **D),
            P('torso', (0, 15.6, 4.44), (1.0, 0.85, 0.04), '#FFF6E4', **D)]
    for sg in (1, -1):
        out += [P('arm%+d' % sg, (0, -2.1, 0), (2.6, 2.9, 2.6), col),             # 반팔
                P('arm%+d' % sg, (0, -4.7, 0), (2.75, 0.5, 2.75), _tint(col, -0.08))]
    return out


# ------------------------------------------------------------------ bottom / shoes
def bottom_pants(col='#2B2733'):
    out = [P('torso', (0, 9.6, 0), (6.7, 1.5, 3.95), col)]
    for sg in (1, -1):
        out.append(P('leg%+d' % sg, (0, -3.4, 0), (3.1, 3.5, 3.1), col))
    return out


def shoes_sneakers(col='#F6F3EE'):
    out = []
    for sg in (1, -1):
        L = 'leg%+d' % sg
        out += [P(L, (0, -7.55, 0.9), (3.3, 1.45, 4.1), col),                       # 갑피
                P(L, (0, -9.0, 0.9), (3.5, 0.5, 4.3), '#B9B2BE'),                    # 밑창
                P(L, (0, -6.08, 1.9), (1.7, 0.05, 1.6), '#9C93A3', decal=True, bevel=0, noise=0)]  # 끈 자리
    return out


PARTS = {
    'skin': {'light': lambda: skin('light')},
    'face': {'basic': face},
    'hair': {'black-curly': hair_curly, 'brown-wavy': hair_wavy},
    'top': {'hoodie-white': top_hoodie, 'tee-yellow': top_tee},
    'bottom': {'pants-black': bottom_pants},
    'shoes': {'sneakers-white': shoes_sneakers},
}
CATS = ['skin', 'face', 'hair', 'top', 'bottom', 'shoes']


# ------------------------------------------------------------------ 포즈
def pose_frame(name):
    """프레임별 포즈: bounce(몸 전체 y), arm/leg 앞뒤 각도(+ = 앞으로), head tilt."""
    p = dict(bounce=0.0, breathe=0.0, arm={1: 0.0, -1: 0.0}, leg={1: 0.0, -1: 0.0}, splay=4.0, head=0.0)
    if name == 'front_b':
        p['breathe'] = -0.48
    walk = {'walk0': (26, 0.0), 'walk1': (9, 0.5), 'walk2': (-26, 0.0), 'walk3': (-9, 0.5)}
    if name in walk:
        a, up = walk[name]
        p['leg'] = {1: a, -1: -a}
        p['arm'] = {1: -a * 0.85, -1: a * 0.85}
        p['bounce'] = up
        p['splay'] = 2.0
        p['head'] = -1.5 if up == 0 else 0.0
    return p


def bone_xf(pose):
    """bone -> (R, t) 월드 변환."""
    b = pose['bounce']
    br = pose['breathe']
    I = np.eye(3)
    xf = {'root': (I, np.array([0, b, 0.0]))}
    xf['torso'] = (I, np.array([0, b + br * 0.5, 0.0]))
    Rh = rot_x(pose['head'])
    xf['head'] = (Rh, np.array(HEAD_PIVOT) + [0, b + br, 0])
    for sg in (1, -1):
        Ra = rot_z(sg * pose['splay']) @ rot_x(-pose['arm'][sg])
        xf['arm%+d' % sg] = (Ra, np.array([sg * SHOULDER[0], SHOULDER[1] + b + br * 0.6, 0]))
        Rl = rot_x(-pose['leg'][sg])
        xf['leg%+d' % sg] = (Rl, np.array([sg * HIP[0], HIP[1] + b, 0]))
    return xf


def assemble(outfit, frame, back_view=False):
    """outfit: {cat: id}. 반환: (boxes, layers) — layers[i] = 해당 상자의 납품 레이어 이름."""
    xf = bone_xf(pose_frame(frame))
    boxes = []
    for cat in CATS:
        pid = outfit.get(cat)
        if not pid:
            continue
        for d in PARTS[cat][pid]():
            R, t = xf[d['bone']]
            layer = cat
            if cat == 'hair':
                layer = 'hair_front' if (back_view or not d.get('back')) else 'hair_back'
            kw = {k: d[k] for k in ('bevel', 'decal', 'noise') if k in d}
            boxes.append(Box(t + R @ np.asarray(d['c'], float), d['h'], R, d['col'], layer, tag=cat, **kw))
    return boxes
