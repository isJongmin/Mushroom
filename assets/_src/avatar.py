"""아바타 파츠 시트 생성 (style-guide v2.0 5장).

모든 파츠는 32x48 프레임 6장(idle0 idle1 walk0 walk1 walk2 walk3)을 공유한다.
몸 영역은 프레임별 스팬(FR)으로 정의하고, 보이는 영역 지도는 data/regions.txt
(style-guide 5.3.1 원문)와 일치하는지 빌드할 때 검사한다.
"""
import os
from PIL import Image
from palette import RAMP, rgba

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')

W, H = 32, 48
ORDER = ['idle0', 'idle1', 'walk0', 'walk1', 'walk2', 'walk3']
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ------------------------------------------------------------------ 영역 스팬
def rect(x0, x1, y0, y1):
    return [(y, x0, x1) for y in range(y0, y1 + 1)]


def torso(dy):
    return [(25 + dy, 12, 18)] + [(y, 11, 19) for y in range(26 + dy, 34 + dy)]


FWD = [(34, 15, 17), (35, 15, 17), (36, 16, 18), (37, 16, 18), (38, 17, 19),
       (39, 17, 19), (40, 18, 20), (41, 18, 20), (42, 19, 21)]
FWD_FOOT = [(43, 19, 21), (44, 19, 22), (45, 19, 22)]
BACK = [(34, 13, 15), (35, 13, 15), (36, 12, 14), (37, 12, 14), (38, 11, 13),
        (39, 11, 13), (40, 10, 12), (41, 10, 12), (42, 9, 11)]
BACK_FOOT = [(43, 9, 11), (44, 9, 12), (45, 9, 12)]

FR = {
    'idle0': dict(dy=0, T=torso(0),
                  A=rect(10, 12, 26, 28), a=rect(10, 12, 29, 30), H=rect(10, 12, 31, 32),
                  B=[(26, 20, 20), (27, 20, 21), (28, 20, 21)], b=rect(20, 21, 29, 30), h=rect(20, 21, 31, 32),
                  L=rect(12, 14, 34, 42), M=rect(16, 18, 34, 42),
                  F=[(43, 12, 14), (44, 12, 15), (45, 12, 15)], G=[(43, 16, 18), (44, 16, 19), (45, 16, 19)]),
    'idle1': dict(dy=1, T=torso(1),
                  A=rect(10, 12, 27, 29), a=rect(10, 12, 30, 31), H=rect(10, 12, 32, 33),
                  B=[(27, 20, 20), (28, 20, 21), (29, 20, 21)], b=rect(20, 21, 30, 31), h=rect(20, 21, 32, 33),
                  L=rect(12, 14, 35, 42), M=rect(16, 18, 35, 42),
                  F=[(43, 12, 14), (44, 12, 15), (45, 12, 15)], G=[(43, 16, 18), (44, 16, 19), (45, 16, 19)]),
    'walk0': dict(dy=0, T=torso(0),
                  A=[(26, 10, 12), (27, 9, 11), (28, 9, 11)], a=[(29, 8, 10), (30, 8, 10)], H=[(31, 7, 9), (32, 7, 9)],
                  B=[(26, 20, 20), (27, 20, 21), (28, 20, 22)], b=[(29, 21, 22), (30, 21, 23)], h=[(31, 21, 23), (32, 22, 23)],
                  L=FWD, F=FWD_FOOT, M=BACK, G=BACK_FOOT),
    'walk1': dict(dy=-1, T=torso(-1),
                  A=rect(10, 12, 25, 27), a=rect(10, 12, 28, 29), H=rect(10, 12, 30, 31),
                  B=[(25, 20, 20), (26, 20, 21), (27, 20, 21)], b=rect(20, 21, 28, 29), h=rect(20, 21, 30, 31),
                  L=rect(13, 15, 33, 42), F=[(43, 13, 15), (44, 13, 16), (45, 13, 16)],
                  M=rect(15, 17, 33, 40), G=[(41, 15, 17), (42, 15, 18), (43, 15, 18)]),
    'walk2': dict(dy=0, T=torso(0),
                  A=[(26, 11, 13), (27, 12, 14), (28, 13, 15)], a=[(29, 13, 15), (30, 14, 16)], H=[(31, 14, 16), (32, 15, 17)],
                  B=[(27, 10, 10), (28, 10, 10)], b=[(29, 10, 10)], h=[(30, 9, 10), (31, 9, 10)],
                  L=BACK, F=BACK_FOOT, M=FWD, G=FWD_FOOT),
    'walk3': dict(dy=-1, T=torso(-1),
                  A=rect(10, 12, 25, 27), a=rect(10, 12, 28, 29), H=rect(10, 12, 30, 31),
                  B=[(25, 20, 20), (26, 20, 21), (27, 20, 21)], b=rect(20, 21, 28, 29), h=rect(20, 21, 30, 31),
                  M=rect(15, 17, 33, 42), G=[(43, 15, 17), (44, 15, 18), (45, 15, 18)],
                  L=rect(12, 14, 33, 38) + [(39, 13, 15), (40, 13, 15)], F=[(41, 13, 15), (42, 13, 16), (43, 13, 16)]),
}
DRAW = ['B', 'b', 'h', 'M', 'G', 'T', 'L', 'F', 'A', 'a', 'H']        # 뒤 -> 앞
GROUP = {'B': 'farA', 'b': 'farA', 'h': 'farA', 'M': 'farL', 'G': 'farL', 'T': 'T',
         'L': 'nearL', 'F': 'nearL', 'A': 'nearA', 'a': 'nearA', 'H': 'nearA'}
RANK = {g: i for i, g in enumerate(['farA', 'farL', 'T', 'nearL', 'nearA'])}


def span_pts(spans):
    return {(x, y) for (y, a, b) in spans for x in range(a, b + 1)}


def full(f, code):
    """가려진 부분까지 포함한 영역 전체 (예: walk1 뒷다리)."""
    return span_pts(FR[f].get(code, []))


_VIS = {}


def vis(f):
    """보이는 영역 지도: {(x,y): code} (가장 앞에 그린 영역)."""
    if f not in _VIS:
        m = {}
        for code in DRAW:
            for p in full(f, code):
                m[p] = code
        _VIS[f] = m
    return _VIS[f]


def vis_pts(f, codes):
    return {p for p, c in vis(f).items() if c in codes}


def check_regions():
    txt = open(os.path.join(DATA, 'regions.txt'), encoding='utf-8').read().split('\n')
    cur = None
    spec = {}
    for line in txt:
        if line.startswith('#') or not line.strip():
            continue
        if line.startswith('['):
            cur = line.strip('[]')
            spec[cur] = {}
            continue
        y = int(line[:2])
        for i, ch in enumerate(line[3:27]):
            if ch != '.':
                spec[cur][(4 + i, y)] = ch
    for f in ORDER:
        assert vis(f) == spec[f], f'region map mismatch in {f}'


# ------------------------------------------------------------------ 공통 도구
class Layer:
    def __init__(self):
        self.px = {}

    def put(self, x, y, tok):
        if 0 <= x < W and 0 <= y < H and tok:
            self.px[(x, y)] = tok

    def image(self):
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for (x, y), t in self.px.items():
            im.putpixel((x, y), rgba(t))
        return im


def edge_set(pts):
    return {(x, y) for (x, y) in pts if any((x + dx, y + dy) not in pts for dx, dy in N4)}


def paint_groups(L, groups):
    """groups: [(pts, ramp)] 뒤 -> 앞. 5.4.1 규칙 2: 이웃이 비었거나 더 뒤 그룹이면 외곽선.
    반환: {p: 'line'|'base'} 역할 지도 (후처리 음영에 사용)."""
    owner = {}
    for i, (pts, _) in enumerate(groups):
        for p in pts:
            owner[p] = i
    role = {}
    for i, (pts, ramp) in enumerate(groups):
        hl, base, shade, line = RAMP[ramp]
        for p in pts:
            if owner[p] != i:
                continue
            x, y = p
            edge = any((x + dx, y + dy) not in owner or owner[(x + dx, y + dy)] < i for dx, dy in N4)
            L.put(x, y, line if edge else base)
            role[p] = 'line' if edge else 'base'
    return role


# ------------------------------------------------------------------ skin
HEAD = [(8, 11, 20), (9, 9, 22), (10, 8, 23)] + [(y, 7, 24) for y in range(11, 21)] + \
       [(21, 8, 24), (22, 9, 23), (23, 10, 22), (24, 12, 21)]
SKIN_IDS = ['skin-light', 'skin-tan', 'skin-dark']


def skin_layer(f, sid):
    _, base, shade, line = RAMP[sid]
    dy = FR[f]['dy']
    L = Layer()
    m = vis(f)
    for (x, y), c in m.items():
        g = GROUP[c]
        edge = False
        for dx, ddy in N4:
            n = m.get((x + dx, y + ddy))
            if n is None or (GROUP[n] != g and RANK[GROUP[n]] < RANK[g]):
                edge = True
        L.put(x, y, line if edge else (shade if g in ('farA', 'farL') else base))
    hs = {(x, y + dy) for (y, a, b) in HEAD for x in range(a, b + 1)}
    ol = edge_set(hs)
    for p in hs:
        L.put(p[0], p[1], line if p in ol else base)
    for y in range(12, 21):
        L.put(8, y + dy, shade)
    for (x, y) in [(9, 21), (10, 22), (11, 22), (11, 23), (10, 16), (11, 16), (10, 17), (10, 18), (11, 18)]:
        L.put(x, y + dy, shade)
    L.put(11, 17 + dy, line)                      # 귀 안쪽
    L.put(18, 22 + dy, line)
    L.put(19, 22 + dy, line)                      # 입
    return L


def check_skin_grid():
    rows = [l for l in open(os.path.join(DATA, 'skin_grid.txt'), encoding='utf-8').read().split('\n')
            if l and not l.startswith('#')]
    key = {'O': 'w2', 's': 's1', 'd': 's2'}
    want = {}
    for line in rows:
        y = int(line[:2])
        for i, ch in enumerate(line[3:27]):
            if ch != '.':
                want[(4 + i, y)] = key[ch]
    got = skin_layer('idle0', 'skin-light').px
    assert got == want, 'skin grid (5.5.1) mismatch: ' + str(sorted(set(got.items()) ^ set(want.items()))[:10])


# ------------------------------------------------------------------ eyes
EYES = {
    'eyes-dot': (['.WW', '.KK', '.KN', '.KK', '.UU'], ['WW.', 'KK.', 'KN.', 'KK.', 'UU.']),
    'eyes-happy': (['.WW', '...', '.K.', 'K.K', '...'], ['WW.', '...', '.K.', 'K.K', '...']),
    'eyes-sleepy': (['...', '.WW', '...', 'KKK', '.UU'], ['...', 'WW.', '...', 'KKK', 'UU.']),
    'eyes-sparkle': (['.WW', '.KK', '.KN', '.NK', '.UU'], ['WWW', 'KKK', 'KNK', 'KKN', 'UUU']),
}
EYE_IDS = ['eyes-dot', 'eyes-happy', 'eyes-sleepy', 'eyes-sparkle']
BLUSH = [(13, 21), (21, 21), (22, 21)]
EYE_BOX = {(x, y) for x in list(range(13, 16)) + list(range(19, 22)) for y in range(15, 20)}


def eyes_layer(f, eid):
    dy = FR[f]['dy']
    L = Layer()
    cmap = {'K': 'ink', 'N': 'white', 'U': 'u2', 'W': 'w4'}
    for rows, x0 in zip(EYES[eid], (13, 19)):
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != '.':
                    L.put(x0 + c, 15 + r + dy, cmap[ch])
    bl = BLUSH + ([(12, 21)] if eid == 'eyes-happy' else [])
    for (x, y) in bl:
        L.put(x, y + dy, 'p2')
    return L


# ------------------------------------------------------------------ hair
def load_hair(name):
    pts = {}
    for line in open(os.path.join(DATA, f'hair_{name}.txt'), encoding='utf-8').read().split('\n'):
        if not line or line.startswith('#'):
            continue
        y = int(line[:2])
        for i, ch in enumerate(line[3:29]):
            if ch != '.':
                pts[(3 + i, y)] = ch
    return pts


HAIR_SHAPES = {n: load_hair(n) for n in ('round', 'spiky', 'long')}
# 품질 보강: 모양 안쪽에만 넣는 음영(s)과 추가 하이라이트(h). 실루엣/좌표는 그대로.
HAIR_EXTRA = {
    'round': {'h': [(7, 9), (7, 10), (6, 11), (19, 8), (20, 8), (21, 9)],
              's': [(7, 17), (7, 18), (9, 13), (10, 13), (22, 11), (23, 11), (24, 12)]},
    'spiky': {'h': [(10, 5), (11, 5), (16, 5), (17, 4), (6, 8), (7, 8), (21, 7), (22, 8)],
              's': [(8, 13), (9, 13), (7, 15), (21, 12), (22, 12), (23, 11), (16, 13)]},
    'long': {'h': [(6, 9), (6, 10), (5, 11), (19, 8), (20, 8), (21, 9), (5, 19), (5, 20)],
             's': [(7, 24), (7, 25), (7, 26), (7, 27), (9, 13), (10, 13), (22, 11), (23, 11), (24, 12)]},
}
HAIR_IDS = [('hair-round-black', 'round', 'black'), ('hair-round-chestnut', 'round', 'chestnut'),
            ('hair-spiky-black', 'spiky', 'black'), ('hair-spiky-chestnut', 'spiky', 'chestnut'),
            ('hair-spiky-mint', 'spiky', 'mint'), ('hair-long-pink', 'long', 'pink'),
            ('hair-long-blonde', 'long', 'blonde')]


def hair_layer(f, shape, color):
    dy = FR[f]['dy']
    hl, base, shade, line = RAMP[color]
    pts = {(x, y + dy): ch for (x, y), ch in HAIR_SHAPES[shape].items()}
    ex = HAIR_EXTRA[shape]
    for (x, y) in ex['h']:
        if pts.get((x, y + dy)) == 'b':
            pts[(x, y + dy)] = 'h'
    for (x, y) in ex['s']:
        if pts.get((x, y + dy)) == 'b':
            pts[(x, y + dy)] = 's'
    m = vis(f)
    for (x, y) in list(pts):
        if (x, y - dy) in EYE_BOX:                          # 5.4 눈 상자 금지
            del pts[(x, y)]
        elif y >= 25 + dy and m.get((x, y)) in ('A', 'a', 'H'):   # 앞팔 위로 오는 머리 삭제
            del pts[(x, y)]
    ol = edge_set(set(pts))
    L = Layer()
    for (x, y), ch in pts.items():
        if ch == 'O' or (x, y) in ol:
            t = line
        else:
            t = {'h': hl, 's': shade, 'b': base}[ch]
        L.put(x, y, t)
    return L


# ------------------------------------------------------------------ top
TOP_IDS = ['top-tee-red', 'top-hoodie-blue', 'top-overalls-blue', 'top-cape-mushroom']


def top_layer(f, tid):
    dy = FR[f]['dy']
    L = Layer()
    tor = {p for p in vis_pts(f, 'T') if p[1] <= 32 + dy}
    A, a, B, b = vis_pts(f, 'A'), vis_pts(f, 'a'), vis_pts(f, 'B'), vis_pts(f, 'b')

    def shoulder(tok):
        for x in range(13, 18):
            if (x, 26 + dy) in tor:
                L.put(x, 26 + dy, tok)

    def on_torso(x, y, tok):
        if (x, y) in tor:
            L.put(x, y, tok)

    def sleeve_hl(pts, role, tok):
        # 앞소매 안쪽 맨 위 왼쪽 픽셀에 하이라이트 (빛은 왼쪽 위)
        inner = sorted((p for p in pts if role.get(p) == 'base'), key=lambda p: (p[1], p[0]))
        if inner:
            L.put(inner[0][0], inner[0][1], tok)

    if tid == 'top-tee-red':
        role = paint_groups(L, [(B, 'red'), (tor, 'red'), (A, 'red')])
        shoulder('r1')
        sleeve_hl(A, role, 'r1')
    elif tid == 'top-hoodie-blue':
        role = paint_groups(L, [(B | b, 'blue'), (tor, 'blue'), (A | a, 'blue')])
        shoulder('u1')
        sleeve_hl(A | a, role, 'u1')
        for (x, y, k) in [(11, 25, 'u3'), (12, 25, 'u1'), (13, 25, 'u1'), (14, 25, 'u3')]:
            L.put(x, y + dy, k)
        for x in range(14, 19):
            on_torso(x, 30 + dy, 'u3')
        on_torso(17, 26 + dy, 'white')
        on_torso(17, 27 + dy, 'white')
    elif tid == 'top-overalls-blue':
        role = paint_groups(L, [(B, 'cream'), (tor, 'cream'), (A, 'cream')])
        shoulder('white')
        sleeve_hl(A, role, 'white')
        for y in range(29, 32):
            for x in range(13, 19):
                on_torso(x, y + dy, 'u2')
        for x in range(13, 19):
            on_torso(x, 32 + dy, 'u3')
        for y in range(25, 29):
            on_torso(14, y + dy, 'u3')
            on_torso(18, y + dy, 'u3')
        on_torso(14, 29 + dy, 'y2')
        on_torso(18, 29 + dy, 'y2')
        for x in (15, 16, 17):                       # 가슴판 윗단 하이라이트 (품질 보강)
            on_torso(x, 29 + dy, 'u1')
    elif tid == 'top-cape-mushroom':
        role = paint_groups(L, [(B | b, 'cream'), (tor, 'cream'), (A | a, 'cream')])
        sleeve_hl(A | a, role, 'white')
        m = vis(f)
        cape = set()
        for (y, x0, x1) in [(25, 10, 20), (26, 9, 21), (27, 8, 22), (28, 8, 22), (29, 8, 22)]:
            for x in range(x0, x1 + 1):
                if y == 29 and x % 2:
                    continue
                if m.get((x, y + dy)) in ('a', 'H', 'h', 'b'):
                    continue
                cape.add((x, y + dy))
        ol = edge_set(cape)
        # 물결 끝단: y28 위 픽셀은 아래가 비어도(홀수 x 골) 외곽선으로 두지 않는다 -> 끝단이 r2/r3 물결로 보임
        for (x, y) in list(ol):
            if y == 28 + dy and (x - 1, y) in cape and (x + 1, y) in cape and (x, y - 1) in cape:
                ol.discard((x, y))
        for p in cape:
            L.put(p[0], p[1], 'r3' if p in ol else 'r2')
        for x in range(12, 17):                      # 망토 어깨 하이라이트 (품질 보강)
            if (x, 26 + dy) in cape and (x, 26 + dy) not in ol:
                L.put(x, 26 + dy, 'r1')
        for (x, y) in [(9, 28), (11, 26), (13, 28), (15, 25), (17, 27), (19, 26), (21, 28)]:
            p = (x, y + dy)
            if p in cape and p not in ol:
                L.put(x, y + dy, 'c1')
        L.put(15, 30 + dy, 'y2')
    return L


# ------------------------------------------------------------------ bottom
BOTTOM_IDS = ['bottom-shorts-navy', 'bottom-jeans-blue', 'bottom-skirt-pink', 'bottom-pumpkin-green']


def leg_rows(f, code, n):
    sp = FR[f][code]
    ys = sorted({y for (y, a, b) in sp})[:n]
    return {(x, y) for (y, a, b) in sp if y in ys for x in range(a, b + 1)}


def bottom_layer(f, bid):
    dy = FR[f]['dy']
    L = Layer()
    hands = vis_pts(f, 'Hh')
    hips = {p for p in full(f, 'T') if p[1] >= 31 + dy} - hands
    shoe = 'shoe-red' if bid == 'bottom-skirt-pink' else 'shoe-brown'
    extra = []
    if bid == 'bottom-shorts-navy':
        role = paint_groups(L, [(leg_rows(f, 'M', 4), 'navy'), (hips, 'navy'), (leg_rows(f, 'L', 4), 'navy')])
        extra = [(p, 'u3') for p in leg_rows(f, 'L', 2) if role.get(p) == 'base'][:1]
    elif bid == 'bottom-jeans-blue':
        lm, ll = leg_rows(f, 'M', 20), leg_rows(f, 'L', 20)
        role = paint_groups(L, [(lm, 'blue'), (hips, 'blue'), (ll, 'blue')])
        # 무릎 하이라이트 + 밑단 접힘(u1), 먼 다리는 그대로
        lys = sorted({y for (_, y) in ll})
        knee = {lys[len(lys) // 2 - 1], lys[len(lys) // 2]}
        for p in ll:
            if role.get(p) == 'base' and (p[1] in knee or p[1] == lys[-1]):
                extra.append((p, 'u1'))
        mys = sorted({y for (_, y) in lm})
        for p in lm:
            if role.get(p) == 'base' and p[1] in (mys[len(mys) // 2],):
                extra.append((p, 'u3'))
    elif bid == 'bottom-pumpkin-green':
        lm, ll = leg_rows(f, 'M', 3), leg_rows(f, 'L', 3)
        lm = lm | {(x - 1, y) for (x, y) in lm} | {(x + 1, y) for (x, y) in lm}
        ll = ll | {(x - 1, y) for (x, y) in ll} | {(x + 1, y) for (x, y) in ll}
        role = paint_groups(L, [(lm, 'green'), (hips, 'green'), (ll, 'green')])
        # 호박 골: 각 다리 가운데 열 g3, 왼쪽 안쪽 g1
        for pts in (lm, ll):
            for y in {q[1] for q in pts}:
                xs = sorted(x for (x, yy) in pts if yy == y)
                inner = [x for x in xs if role.get((x, y)) == 'base' and L.px.get((x, y)) == 'g2']
                if len(inner) >= 3:
                    extra.append(((inner[0], y), 'g1'))
                    extra.append(((inner[len(inner) // 2], y), 'g3'))
    elif bid == 'bottom-skirt-pink':
        sk = set()
        for (y, x0, x1) in [(31, 11, 19), (32, 11, 19), (33, 10, 20), (34, 10, 20), (35, 9, 21), (36, 9, 21)]:
            for x in range(x0, x1 + 1):
                sk.add((x, y + dy))
        sk -= hands
        role = paint_groups(L, [(sk, 'fpink')])
        for (x, y) in [(12, 34), (15, 34), (18, 34), (12, 35), (15, 35), (18, 35)]:
            extra.append(((x, y + dy), 'p3'))
        for x in (11, 12, 13):                         # 허리 아래 하이라이트 (품질 보강)
            if role.get((x, 33 + dy)) == 'base':
                extra.append(((x, 33 + dy), 'p1'))
    for (p, t) in extra:
        L.put(p[0], p[1], t)
    srole = paint_groups(L, [(full(f, 'G'), shoe), (full(f, 'F'), shoe)])
    hl = RAMP[shoe][0]
    for code in ('G', 'F'):                            # 신발 앞코 하이라이트
        inner = sorted((p for p in full(f, code) if srole.get(p) == 'base'), key=lambda p: (p[1], -p[0]))
        if inner:
            L.put(inner[0][0], inner[0][1], hl)
    return L


# ------------------------------------------------------------------ 조립
def part_frames():
    """{part: [(id, fn(frame)->Layer)]} 매니페스트 순서."""
    return {
        'skin': [(s, (lambda f, s=s: skin_layer(f, s))) for s in SKIN_IDS],
        'hair': [(i, (lambda f, sh=sh, c=c: hair_layer(f, sh, c))) for (i, sh, c) in HAIR_IDS],
        'eyes': [(e, (lambda f, e=e: eyes_layer(f, e))) for e in EYE_IDS],
        'top': [(t, (lambda f, t=t: top_layer(f, t))) for t in TOP_IDS],
        'bottom': [(b, (lambda f, b=b: bottom_layer(f, b))) for b in BOTTOM_IDS],
    }


def check_forbidden(part, pid, f, L):
    dy = FR[f]['dy']
    m = vis(f)
    for (x, y) in L.px:
        assert y <= 45, (pid, f, 'rows 46-47 must be empty')
        c = m.get((x, y))
        if part in ('top', 'bottom'):
            assert c not in ('H', 'h'), (pid, f, 'hand pixel', x, y)
            assert y > 24 + dy, (pid, f, 'head area', x, y)
        if part == 'top' and pid in ('top-tee-red', 'top-overalls-blue'):
            assert c not in ('a', 'b'), (pid, f, 'short sleeve arm', x, y)
        if part == 'hair':
            assert (x, y - dy) not in EYE_BOX, (pid, f, 'eye box', x, y)
            assert not (y >= 25 + dy and c in ('A', 'a', 'H')), (pid, f, 'near arm', x, y)
        if part == 'eyes':
            ok = (x, y - dy) in EYE_BOX or (x, y - dy) in BLUSH + [(12, 21)]
            assert ok, (pid, f, 'eyes outside box', x, y)


def build(out_root):
    check_regions()
    check_skin_grid()
    files = []
    for part, items in part_frames().items():
        d = os.path.join(out_root, part)
        os.makedirs(d, exist_ok=True)
        for pid, fn in items:
            sheet = Image.new('RGBA', (W * 6, H), (0, 0, 0, 0))
            for i, f in enumerate(ORDER):
                L = fn(f)
                check_forbidden(part, pid, f, L)
                sheet.alpha_composite(L.image(), (i * W, 0))
            path = os.path.join(d, pid + '.png')
            sheet.save(path, optimize=True)
            files.append(path)
    return files


LABELS = {
    'skin-light': '밝은 피부', 'skin-tan': '보통 피부', 'skin-dark': '진한 피부',
    'hair-round-black': '단발 · 흑발', 'hair-round-chestnut': '단발 · 밤색',
    'hair-spiky-black': '뾰족 · 흑발', 'hair-spiky-chestnut': '뾰족 · 밤색', 'hair-spiky-mint': '뾰족 · 민트',
    'hair-long-pink': '긴머리 · 분홍', 'hair-long-blonde': '긴머리 · 금발',
    'eyes-dot': '기본 눈', 'eyes-happy': '웃는 눈', 'eyes-sleepy': '졸린 눈', 'eyes-sparkle': '반짝 눈',
    'top-tee-red': '빨간 티셔츠', 'top-hoodie-blue': '파란 후드티', 'top-overalls-blue': '파란 멜빵',
    'top-cape-mushroom': '버섯 망토',
    'bottom-shorts-navy': '네이비 반바지', 'bottom-jeans-blue': '청바지', 'bottom-skirt-pink': '분홍 치마',
    'bottom-pumpkin-green': '초록 호박바지',
}


def manifest():
    parts = {p: [{'id': i, 'label': LABELS[i]} for i, _ in items] for p, items in part_frames().items()}
    return {
        'frame': {'w': W, 'h': H},
        'anchor': {'x': 16, 'y': 46},
        'scale': 2,
        'layerOrder': ['skin', 'bottom', 'top', 'eyes', 'hair'],
        'frameOrder': ORDER,
        'animations': {'idle': {'frames': [0, 1], 'ms': 500}, 'walk': {'frames': [2, 3, 4, 5], 'ms': 120}},
        'parts': parts,
        'aliases': {'eyes-round': 'eyes-sparkle', 'top-vest-green': 'top-overalls-blue'},
    }
