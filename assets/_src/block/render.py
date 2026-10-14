"""블록(상자) 렌더러: 3D 상자 -> 사선 투영(oblique) 2D 픽셀.

좌표계 (캐릭터 공간)
  x: 화면 오른쪽(정면 뷰 기준, = 캐릭터의 왼손 쪽), y: 아래, z: 뒤(카메라에서 멀어짐). 캐릭터는 -z를 바라본다.
  단위 1 = 정면에서 1px. 원점 = 두 발 사이 바닥 중앙 = 기준점(anchor).
투영: sx = X + A*Z, sy = Y - A*Z  (A = 0.2 -> 깊이 20인 머리는 윗면/옆면이 4px)
  뒤로 갈수록 오른쪽 위로 밀린다 = 약간 위, 오른쪽에서 본 3/4 시점. 보이는 면: 정면, 윗면, 오른쪽 옆면.
면 톤: 윗면 = 재질 top(밝게), 정면 = front, 오른쪽 = side(어둡게). 그라데이션 없음.
각 면은 픽셀 중심을 역사상(inverse mapping)해서 칠하므로 구멍/겹침 없이 결정적이다. z-buffer로 가림 처리.
"""
import math
from palette import PAL, MATS, DARKER

A = 0.2
CAM = (A, -A, -1.0)   # 카메라를 향하는 방향 (면 법선과 내적 > 0 이면 보임)

VIEWS = ('front', 'side', 'back')
# 옆모습에서 카메라 반대쪽(캐릭터 왼쪽) 팔다리는 한 톤 어둡게 그린다 -> 걷기에서 두 다리/두 팔이 구분된다.
FAR_GROUPS = {'side': ('legL', 'armL')}


def view_xform(view, p):
    x, y, z = p
    if view == 'front':
        return (x, y, z)
    if view == 'back':
        return (-x, y, -z)
    if view == 'side':          # 캐릭터가 화면 오른쪽(+X)을 본다. 캐릭터 오른쪽(-x)이 카메라 쪽
        return (-z, y, x)
    raise ValueError(view)


class Box:
    """x0..x1, y0..y1, z0..z1 (캐릭터 공간), layer, group(포즈 단위), tex(face, x, y, z, view)."""
    def __init__(self, x0, x1, y0, y1, z0, z1, layer, group, tex, name=''):
        self.b = (x0, x1, y0, y1, z0, z1)
        self.layer, self.group, self.tex, self.name = layer, group, tex, name
        self.noao = False   # True: 이 상자는 이웃에 깊이 경계 그늘을 만들지 않는다 (작은 삐침 등)

    def faces(self):
        x0, x1, y0, y1, z0, z1 = self.b
        # (이름, 원점, e1, e2)
        return [
            ('front',  (x0, y0, z0), (x1 - x0, 0, 0), (0, y1 - y0, 0)),
            ('back',   (x0, y0, z1), (x1 - x0, 0, 0), (0, y1 - y0, 0)),
            ('top',    (x0, y0, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0)),
            ('bottom', (x0, y1, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0)),
            ('left',   (x1, y0, z0), (0, 0, z1 - z0), (0, y1 - y0, 0)),   # +x = 캐릭터 왼쪽
            ('right',  (x0, y0, z0), (0, 0, z1 - z0), (0, y1 - y0, 0)),   # -x = 캐릭터 오른쪽
        ]

    def center(self):
        x0, x1, y0, y1, z0, z1 = self.b
        return ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def make_pose_fn(pose, group):
    """pose[group] = dict(d=(dx,dy,dz), shear=s, pivot=py): z += s*(y-py) (앞뒤 스윙), 그 뒤 평행이동."""
    g = pose.get(group, {}) if pose else {}
    gb = pose.get('_all', {}) if pose else {}
    dx, dy, dz = g.get('d', (0, 0, 0))
    bx, by, bz = gb.get('d', (0, 0, 0))
    s = g.get('shear', 0.0)
    py = g.get('pivot', 0.0)

    def f(p):
        x, y, z = p
        z = z + s * (y - py)
        return (x + dx + bx, y + dy + by, z + dz + bz)
    return f


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def proj(p):
    return (p[0] + A * p[2], p[1] - A * p[2])


def resolve(t, tone, dark=0):
    """텍스처 결과 -> (색 토큰, 재질 이름, delta). dark: 추가로 어둡게 할 단계(먼 쪽 팔다리)."""
    if t is None:
        return None
    if isinstance(t, str):
        if t in MATS:
            return MATS[t].color(tone, dark), t, dark
        for _ in range(dark):
            t = DARKER[t]
        return t, None, 0
    mat, delta = t
    if mat is None:
        return resolve(delta, tone, dark)
    return MATS[mat].color(tone, delta + dark), mat, delta + dark


class Buf:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.col = [[None] * W for _ in range(H)]
        self.mat = [[None] * W for _ in range(H)]
        self.z = [[math.inf] * W for _ in range(H)]
        self.tone = [[None] * W for _ in range(H)]
        self.delta = [[0] * W for _ in range(H)]
        self.bid = [[-1] * W for _ in range(H)]

    def copy_empty(self):
        return Buf(self.W, self.H)


def raster_box(box, view, pose, buf, ax, ay, bid=0, eps=1e-7):
    pf = make_pose_fn(pose, box.group)
    dark = 1 if box.group in FAR_GROUPS.get(view, ()) else 0
    T = lambda p: view_xform(view, pf(p))
    cc = T(box.center())
    for fname, o, e1, e2 in box.faces():
        if (e1 == (0, 0, 0)) or (e2 == (0, 0, 0)):
            continue
        O = T(o)
        P1 = T((o[0] + e1[0], o[1] + e1[1], o[2] + e1[2]))
        P2 = T((o[0] + e2[0], o[1] + e2[1], o[2] + e2[2]))
        E1, E2 = sub(P1, O), sub(P2, O)
        n = cross(E1, E2)
        fc = (O[0] + (E1[0] + E2[0]) / 2, O[1] + (E1[1] + E2[1]) / 2, O[2] + (E1[2] + E2[2]) / 2)
        if dot(n, sub(fc, cc)) < 0:
            n = (-n[0], -n[1], -n[2])
        if dot(n, CAM) <= 1e-9:
            continue
        # 면 톤: 뷰 공간 법선의 주축
        an = (abs(n[0]) * 1.0, abs(n[1]) * 1.0, abs(n[2]) * 1.0)
        if an[2] >= an[0] and an[2] >= an[1]:
            tone = 'front'
        elif an[1] >= an[0]:
            tone = 'top'
        else:
            tone = 'side'
        s0 = proj(O)
        a_ = (E1[0] + A * E1[2], E1[1] - A * E1[2])
        b_ = (E2[0] + A * E2[2], E2[1] - A * E2[2])
        det = a_[0] * b_[1] - a_[1] * b_[0]
        if abs(det) < 1e-9:
            continue
        xs = [s0[0], s0[0] + a_[0], s0[0] + b_[0], s0[0] + a_[0] + b_[0]]
        ys = [s0[1], s0[1] + a_[1], s0[1] + b_[1], s0[1] + a_[1] + b_[1]]
        px0, px1 = int(math.floor(min(xs))) - 1, int(math.ceil(max(xs))) + 1
        py0, py1 = int(math.floor(min(ys))) - 1, int(math.ceil(max(ys))) + 1
        for py in range(py0, py1):
            Y = py + ay
            if Y < 0 or Y >= buf.H:
                continue
            for px in range(px0, px1):
                X = px + ax
                if X < 0 or X >= buf.W:
                    continue
                dx = px + 0.5 - s0[0]
                dy = py + 0.5 - s0[1]
                u = (dx * b_[1] - dy * b_[0]) / det
                v = (a_[0] * dy - a_[1] * dx) / det
                if u < -eps or u >= 1 - eps or v < -eps or v >= 1 - eps:
                    continue
                u = min(max(u, 0.0), 0.999999)
                v = min(max(v, 0.0), 0.999999)
                depth = O[2] + u * E1[2] + v * E2[2]
                if depth >= buf.z[Y][X] - 1e-6:
                    continue
                cp = (o[0] + u * e1[0] + v * e2[0], o[1] + u * e1[1] + v * e2[1], o[2] + u * e1[2] + v * e2[2])
                r = resolve(box.tex(fname, cp[0], cp[1], cp[2], view), tone, dark)
                if r is None:
                    continue
                buf.col[Y][X], buf.mat[Y][X], buf.delta[Y][X] = r
                buf.tone[Y][X] = tone
                buf.z[Y][X] = depth
                buf.bid[Y][X] = bid


def render(boxes, view, pose, W, H, ax, ay, ao=True):
    buf = Buf(W, H)
    for i, b in enumerate(boxes):
        raster_box(b, view, pose, buf, ax, ay, bid=i)
    if ao:
        depth_edges(buf, boxes)
    return buf


def depth_edges(buf, boxes=None, thr=0.9):
    """같은 레이어 안에서 다른 상자가 더 가까이 붙어 있으면(깊이 차 > thr) 먼 쪽 픽셀을 한 톤 어둡게.
    팔/몸통, 머리/목, 다리 사이처럼 같은 색 상자가 겹쳐도 블록 경계가 읽히게 한다."""
    H, W = buf.H, buf.W
    mark = []
    for y in range(H):
        for x in range(W):
            if buf.mat[y][x] is None:
                continue
            z = buf.z[y][x]
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + ddx, y + ddy
                if 0 <= nx < W and 0 <= ny < H and buf.col[ny][nx] is not None \
                        and buf.bid[ny][nx] != buf.bid[y][x] and buf.z[ny][nx] < z - thr \
                        and not (boxes and boxes[buf.bid[ny][nx]].noao):
                    mark.append((x, y))
                    break
    for x, y in mark:
        buf.delta[y][x] += 1
        buf.col[y][x] = MATS[buf.mat[y][x]].color(buf.tone[y][x], buf.delta[y][x])


def to_image(cols, Image):
    H, W = len(cols), len(cols[0])
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = im.load()
    for y in range(H):
        for x in range(W):
            c = cols[y][x]
            if c is not None:
                h = PAL[c]
                px[x, y] = (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)
    return im
