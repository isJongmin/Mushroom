"""(사이클 10) 부호 거리 함수(SDF) 형상을 반 칸(사이클 8 단위 0.5 = 렌더 복셀 1칸) 격자로 복셀화해 상자 정의로 바꾼다.

둥근 머리카락 볼륨, 모자 크라운처럼 상자 조합으로 둥글게 만들기 어려운 형상에 쓴다.
  - 형상 = SDF(numpy 배열 연산). 음수 = 안쪽. 합집합 min, 차집합 max(a, -b), 부드러운 합 smin.
  - 색 = 복셀마다 색 번호 (같은 색끼리만 상자로 합친다).
  - 합치기: y 방향 구간 -> 같은 구간을 x 로 -> z 로 (탐욕적). 결과 상자는 베벨 0 (합친 경계가 줄로 보이지 않게).
결정적: 난수 없음. 같은 입력이면 같은 상자 목록.
"""
import numpy as np

STEP = 0.5          # 사이클 8 단위 (= 렌더 복셀 1칸)


class Grid3:
    def __init__(self, lo, hi, step=STEP):
        self.step = step
        self.lo = np.floor(np.asarray(lo, float) / step) * step
        n = np.ceil((np.asarray(hi, float) - self.lo) / step).astype(int)
        self.n = n
        ax = [self.lo[k] + (np.arange(n[k]) + 0.5) * step for k in range(3)]
        self.ax = ax
        self.X, self.Y, self.Z = np.meshgrid(*ax, indexing='ij')


# ------------------------------------------------------------------ 기본 형상 (g = Grid3)
def ellipsoid(g, c, r):
    """근사 SDF (r 단위로 정규화한 길이 x 최소 반경)."""
    c = np.asarray(c, float); r = np.asarray(r, float)
    q = np.sqrt(((g.X - c[0]) / r[0]) ** 2 + ((g.Y - c[1]) / r[1]) ** 2 + ((g.Z - c[2]) / r[2]) ** 2)
    return (q - 1) * r.min()


def rbox(g, c, h, r=1.0):
    """둥근 상자 (반폭 h, 모서리 반경 r)."""
    c = np.asarray(c, float); h = np.asarray(h, float) - r
    qx = np.abs(g.X - c[0]) - h[0]; qy = np.abs(g.Y - c[1]) - h[1]; qz = np.abs(g.Z - c[2]) - h[2]
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r


def capsule(g, a, b, ra, rb=None, sz=1.0):
    """두 점 a, b 를 잇는 굵기가 ra -> rb 로 변하는 캡슐. sz: z 방향 납작함 (0.5 = 앞뒤로 절반 두께)."""
    rb = ra if rb is None else rb
    a = np.asarray(a, float); b = np.asarray(b, float)
    ba = b - a
    px, py, pz = g.X - a[0], g.Y - a[1], (g.Z - a[2])
    t = np.clip((px * ba[0] + py * ba[1] + pz * ba[2]) / (ba @ ba), 0, 1)
    dx, dy, dz = px - t * ba[0], py - t * ba[1], (pz - t * ba[2]) / sz
    return np.sqrt(dx * dx + dy * dy + dz * dz) - (ra + (rb - ra) * t)


def tube(g, pts, radii, sz=1.0):
    """점 목록을 잇는 캡슐 사슬 (꼬리, 가닥)."""
    d = None
    for i in range(len(pts) - 1):
        e = capsule(g, pts[i], pts[i + 1], radii[i], radii[i + 1], sz)
        d = e if d is None else np.minimum(d, e)
    return d


def smin(a, b, k=1.5):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def union(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.minimum(out, d)
    return out


def sub(a, b):
    return np.maximum(a, -b)


def inter(a, b):
    return np.maximum(a, b)


# ------------------------------------------------------------------ 복셀 -> 상자
def merge_boxes(lab, g, cols, bone, **kw):
    """lab: (nx, ny, nz) 정수 (-1 = 빈칸). cols: 번호 -> (hex, dict 추가 키). 반환: 상자 정의 dict 목록."""
    nx, ny, nz = lab.shape
    s = g.step
    # 1) y 구간
    segs = {}                                  # (x, z) -> [(y0, y1, lab)]
    for x in range(nx):
        col = lab[x]                           # (ny, nz)
        for z in range(nz):
            v = col[:, z]
            if (v < 0).all():
                continue
            ch = np.flatnonzero(np.diff(np.concatenate(([-2], v, [-2]))) != 0)
            for i in range(len(ch) - 1):
                y0, y1 = ch[i], ch[i + 1]
                if v[y0] >= 0:
                    segs.setdefault(z, {}).setdefault((y0, y1, int(v[y0])), []).append(x)
    # 2) x 로 합치기 (z 마다 같은 (y0, y1, lab) 의 연속 x)
    rows = {}                                  # (x0, x1, y0, y1, lab) -> [z]
    for z in sorted(segs):
        for key, xs in segs[z].items():
            xs = sorted(xs)
            st = xs[0]; pv = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == pv + 1:
                    pv = x; continue
                rows.setdefault((st, pv + 1) + key, []).append(z)
                if x is not None:
                    st = pv = x
    # 3) z 로 합치기
    out = []
    for key in sorted(rows):
        x0, x1, y0, y1, k = key
        zs = sorted(rows[key])
        st = pv = zs[0]
        for z in zs[1:] + [None]:
            if z is not None and z == pv + 1:
                pv = z; continue
            z0, z1 = st, pv + 1
            c = (g.lo[0] + (x0 + x1) * s / 2, g.lo[1] + (y0 + y1) * s / 2, g.lo[2] + (z0 + z1) * s / 2)
            h = ((x1 - x0) * s / 2, (y1 - y0) * s / 2, (z1 - z0) * s / 2)
            hexcol, extra = cols[k]
            d = dict(bone=bone, c=c, h=h, col=hexcol, bevel=0.0, hard=True)
            d.update(kw); d.update(extra)
            out.append(d)
            if z is not None:
                st = pv = z
    return out


def surface_only(lab, keep=1):
    """안쪽(6 이웃이 모두 채워진 칸에서 keep 칸 더 들어간) 복셀은 같은 번호 하나로 묶어 상자 수를 줄인다."""
    occ = lab >= 0
    inner = occ.copy()
    for _ in range(keep + 1):
        e = inner.copy()
        e[1:] &= inner[:-1]; e[:-1] &= inner[1:]
        e[:, 1:] &= inner[:, :-1]; e[:, :-1] &= inner[:, 1:]
        e[:, :, 1:] &= inner[:, :, :-1]; e[:, :, :-1] &= inner[:, :, 1:]
        inner = e
    return inner


def build(g, d, labels, base, cols, bone='head', **kw):
    """d <= 0 인 칸을 labels(같은 모양 정수 배열) 색으로 채워 상자 정의로. 안쪽 칸은 base 번호로 묶는다."""
    lab = np.where(d <= 0, labels, -1).astype(np.int32)
    inner = surface_only(lab, keep=1)
    lab[inner] = base
    return merge_boxes(lab, g, cols, bone, **kw)
