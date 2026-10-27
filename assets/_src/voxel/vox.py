"""버섯마을 voxel (사이클 5 정본, 사이클 7: 복셀 1칸 1.9px 모델에 맞춰 격자 범위/AO 반경/그림자 거리 확대): numpy 직교 레이캐스터.

모델 = 방향 있는 상자(Box) 목록. 한 상자 = 한 '큐브 덩어리'(베벨/이음새 단위).
  - 1차 가시성: 해석적 ray-box(slab) 교차, 4x4 슈퍼샘플.
  - 조명(뷰 공간): 따뜻한 키라이트(+부드러운 그림자), 하늘 필, 지면 반사, 정면 필, 백라이트.
  - AO/그림자: 포즈마다 0.5단위 점유 격자를 만들어 반구 샘플 / 레이 마칭 (상자 이음새가 자연히 어두워진다).
  - 베벨: 상자 가장자리 폭 BEVEL 안에서 법선을 바깥으로 기울여 모서리가 빛을 받는다.
  - 림: 깊이 버퍼 기준 화면 공간 오른쪽-위 가장자리 발광.
결정적: 난수 없음(좌표 해시만).
"""
import numpy as np
from scipy import ndimage

SS = 4            # 슈퍼샘플 배율
GRID = 0.5        # 점유 격자 셀 크기 (모델 단위)
BEVEL = 0.38      # 베벨 폭 (모델 단위)


# ---------------------------------------------------------------- 색/행렬 유틸
def hex2lin(h):
    c = np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def rot_x(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def norm(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


class Box:
    __slots__ = ('c', 'h', 'R', 'col', 'layer', 'bevel', 'decal', 'noise', 'tag', 'emit')

    def __init__(self, c, h, R, col, layer, bevel=BEVEL, decal=False, noise=0.04, tag='', emit=0.0):
        self.c = np.asarray(c, float); self.h = np.asarray(h, float); self.R = np.asarray(R, float)
        self.col = hex2lin(col) if isinstance(col, str) else np.asarray(col, float)
        self.layer, self.bevel, self.decal, self.noise, self.tag, self.emit = layer, bevel, decal, noise, tag, emit


# ---------------------------------------------------------------- 조명 (뷰 공간: x 오른쪽, y 위, z 카메라 쪽)
KEY_DIR = norm([-0.42, 0.72, 0.56])
KEY_COL = np.array([1.00, 0.87, 0.70]) * 1.9
SKY_COL = np.array([0.52, 0.57, 0.74]) * 0.70
GND_COL = np.array([0.40, 0.30, 0.24]) * 0.45
FILL_DIR = norm([0.45, 0.10, 0.90])
FILL_COL = np.array([0.62, 0.66, 0.80]) * 0.40
BACK_DIR = norm([0.80, 0.35, -0.50])
BACK_COL = np.array([1.00, 0.78, 0.58]) * 0.85
RIM_COL = np.array([1.00, 0.82, 0.62]) * 0.95
EXPOSURE = 1.05

# 반구 AO 방향: 26 이웃 방향
_D = np.array([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)], float)
AO_DIRS = _D / np.linalg.norm(_D, axis=1)[:, None]
AO_RADII = (1.0, 2.2, 3.9, 6.0)      # 사이클 7: 모델 단위가 작아져 1.3배
AO_W = (1.0, 0.8, 0.55, 0.35)

# 슈퍼샘플 지터 (그림자 소프트니스): 4x4 서브픽셀마다 키라이트 방향을 원뿔 안에서 흔든다
_jt = []
for k in range(16):
    r = 0.11 * np.sqrt((k + 0.5) / 16)
    a = k * 2.399963
    _jt.append((r * np.cos(a), r * np.sin(a)))
JITTER = np.array(_jt)


def view_matrix(yaw, pitch):
    return rot_x(pitch) @ rot_y(yaw)


def _hash3(a, b, c):
    h = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (c.astype(np.int64) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h >> 7) & 0xFFFF) / 65535.0


# ---------------------------------------------------------------- 점유 격자
class Grid:
    def __init__(self, boxes, V, lo=(-36, -16, -36), hi=(36, 98, 36)):
        self.lo = np.array(lo, float)
        n = np.ceil((np.array(hi) - self.lo) / GRID).astype(int)
        occ = np.zeros(n, np.float32)
        for b in boxes:
            if b.decal:
                continue
            Mv, cv = V @ b.R, V @ b.c
            ext = np.abs(Mv) @ b.h
            i0 = np.clip(np.floor((cv - ext - self.lo) / GRID).astype(int), 0, n)
            i1 = np.clip(np.ceil((cv + ext - self.lo) / GRID).astype(int) + 1, 0, n)
            if np.any(i1 <= i0):
                continue
            ax = [self.lo[k] + (np.arange(i0[k], i1[k]) + 0.5) * GRID for k in range(3)]
            X, Y, Z = np.meshgrid(*ax, indexing='ij')
            P = np.stack([X - cv[0], Y - cv[1], Z - cv[2]], -1) @ Mv
            inside = np.all(np.abs(P) <= b.h + 1e-6, axis=-1)
            sl = occ[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
            sl[inside] = 1.0
        self.raw = occ
        self.occ = ndimage.gaussian_filter(occ, 0.55)
        nz = np.argwhere(occ > 0)
        if len(nz):
            self.blo = self.lo + (nz.min(0) - 2) * GRID
            self.bhi = self.lo + (nz.max(0) + 3) * GRID
        else:
            self.blo = self.bhi = self.lo

    def sample(self, P):
        idx = ((P - self.lo) / GRID - 0.5).T
        return ndimage.map_coordinates(self.occ, idx, order=1, mode='constant', cval=0.0)


# ---------------------------------------------------------------- 렌더
def render(boxes, yaw, pitch, scale, *, vis=None, mask=(), occ=None, W=144, H=192, anchor=(72, 180),
           lighting=True):
    """boxes: Box 목록. vis: 보이는 상자 인덱스(None=전체). mask: 깊이로만 가리는 상자(투명 처리).
    occ: 그림자/AO 차폐에 쓰는 상자 인덱스(None=전체).
    반환: dict(rgba=(H,W,4) uint8, irr=SS해상도 조도 휘도, hit=SS해상도 가시 마스크, ...)."""
    nb = len(boxes)
    vis = set(range(nb)) if vis is None else set(vis)
    mask = set(mask) - vis
    occ = list(range(nb)) if occ is None else list(occ)
    V = view_matrix(yaw, pitch)
    Wb, Hb, S = W * SS, H * SS, scale * SS
    axp, ayp = anchor[0] * SS, anchor[1] * SS
    Z0 = 200.0
    zbuf = np.full((Hb, Wb), np.inf)
    idb = np.full((Hb, Wb), -1, np.int32)

    cache = {}
    for i in sorted(vis | mask):
        b = boxes[i]
        Mv, cv = V @ b.R, V @ b.c
        ext = np.abs(Mv) @ b.h
        x0 = int(max(0, np.floor((cv[0] - ext[0]) * S + axp)))
        x1 = int(min(Wb, np.ceil((cv[0] + ext[0]) * S + axp) + 1))
        y0 = int(max(0, np.floor(ayp - (cv[1] + ext[1]) * S)))
        y1 = int(min(Hb, np.ceil(ayp - (cv[1] - ext[1]) * S) + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        vx = ((np.arange(x0, x1) + 0.5) - axp) / S
        vy = (ayp - (np.arange(y0, y1) + 0.5)) / S
        VX, VY = np.meshgrid(vx, vy)
        R = np.stack([VX - cv[0], VY - cv[1], np.full_like(VX, Z0 - cv[2])], -1)
        o = R @ Mv
        d = -Mv[2, :]
        inv = np.where(np.abs(d) > 1e-9, 1.0 / np.where(np.abs(d) > 1e-9, d, 1), 1e12)
        t1 = (-b.h - o) * inv
        t2 = (b.h - o) * inv
        tn = np.minimum(t1, t2); tf = np.maximum(t1, t2)
        tN = tn.max(-1); tF = tf.min(-1)
        hit = (tN <= tF) & (tF > 0)
        zs = zbuf[y0:y1, x0:x1]
        win = hit & (tN < zs)
        zs[win] = tN[win]
        idb[y0:y1, x0:x1][win] = i
        cache[i] = (x0, y0, x1, y1, Mv, cv)

    cover = idb >= 0
    vismask = cover & np.isin(idb, list(vis))
    out = dict(cover=cover, hit=vismask, zbuf=zbuf, idb=idb)
    ys, xs = np.nonzero(vismask)
    N = len(ys)
    P = np.zeros((N, 3)); ng = np.zeros((N, 3)); nbv = np.zeros((N, 3)); alb = np.zeros((N, 3)); emi = np.zeros(N)
    ids = idb[ys, xs]
    t = zbuf[ys, xs]
    P[:, 0] = ((xs + 0.5) - axp) / S
    P[:, 1] = (ayp - (ys + 0.5)) / S
    P[:, 2] = Z0 - t
    for i in np.unique(ids):
        sel = ids == i
        b = boxes[i]
        x0, y0, x1, y1, Mv, cv = cache[i]
        pl = (P[sel] - cv) @ Mv                 # 로컬 좌표
        d = -Mv[2, :]
        rel = np.abs(pl) / b.h
        axis = np.argmax(rel, -1)              # 들어온 면
        sgn = np.sign(pl[np.arange(len(pl)), axis])
        nl = np.zeros_like(pl); nl[np.arange(len(pl)), axis] = sgn
        ng[sel] = nl @ Mv.T
        # 베벨: 면의 접선 축마다 가장자리 거리
        nt = nl.copy()
        cellid = []
        for k in range(3):
            dk = b.h[k] - np.abs(pl[:, k])
            onT = axis != k
            if b.bevel > 0:
                w = np.clip(1 - dk / b.bevel, 0, 1) * onT
                nt[:, k] += np.sign(pl[:, k]) * w * 0.95
            cellid.append(np.floor(pl[:, k] + b.h[k] + 1e-4 - (axis == k) * 0.5))
        nt /= np.linalg.norm(nt, axis=1, keepdims=True)
        nbv[sel] = nt @ Mv.T
        hsh = _hash3(cellid[0] + i * 31, cellid[1] + axis * 7, cellid[2])
        alb[sel] = b.col[None, :] * (1 + b.noise * (hsh[:, None] - 0.5) * 2)
        emi[sel] = b.emit
    out['P'], out['ys'], out['xs'] = P, ys, xs
    if not lighting:
        return out

    grid = Grid([boxes[i] for i in occ], V)
    # --- AO (기하 법선 기준 반구)
    base = P + ng * 0.3
    acc = np.zeros(N); wsum = 0.0
    for r, wr in zip(AO_RADII, AO_W):
        for dvec in AO_DIRS:
            cosw = ng @ dvec
            sel = np.nonzero(cosw > 0.05)[0]
            if len(sel) == 0:
                continue
            o = grid.sample(base[sel] + dvec[None, :] * r)
            acc[sel] += cosw[sel] * wr * o
        wsum += wr
    norm_w = np.zeros(N)
    for r, wr in zip(AO_RADII, AO_W):
        cw = ng @ AO_DIRS.T
        norm_w += wr * np.where(cw > 0.05, cw, 0).sum(1)
    ao = 1 - np.clip(acc / np.maximum(norm_w, 1e-6) * 2.3, 0, 0.88)
    ao = ao ** 1.15

    # --- 키라이트 그림자 (서브픽셀 지터 원뿔 + 점유 밀도 투과율)
    jid = (ys % SS) * SS + (xs % SS)
    jt = JITTER[jid]
    up = norm(np.cross(KEY_DIR, [0, 0, 1])); vv = np.cross(KEY_DIR, up)
    Ld = KEY_DIR[None, :] + jt[:, :1] * up[None, :] + jt[:, 1:] * vv[None, :]
    Ld /= np.linalg.norm(Ld, axis=1, keepdims=True)
    pos = P + ng * 0.55 + Ld * 0.3
    tau = np.zeros(N)
    step = 0.6
    act = np.arange(N)
    for _ in range(230):
        pos[act] += Ld[act] * step
        p = pos[act]
        ok = np.all((p > grid.blo) & (p < grid.bhi), axis=1)
        act = act[ok]
        if len(act) == 0:
            break
        tau[act] += grid.sample(pos[act]) * step
    shadow = np.exp(-tau * 2.2)

    ao = ao[:, None] ** np.array([[0.85, 1.0, 1.2]])   # 따뜻한 틈 그림자
    nd = lambda dv: np.clip(nbv @ dv, 0, 1)
    irr = (KEY_COL[None] * (nd(KEY_DIR) * shadow)[:, None]
           + SKY_COL[None] * (0.55 + 0.45 * nbv[:, 1])[:, None] * ao
           + GND_COL[None] * (0.5 - 0.5 * nbv[:, 1])[:, None] * ao
           + FILL_COL[None] * nd(FILL_DIR)[:, None] * ao
           + BACK_COL[None] * nd(BACK_DIR)[:, None] * (0.35 + 0.65 * ao))

    # --- 화면 공간 림: 오른쪽-위 방향으로 비었거나 훨씬 깊은 곳이 있으면 가장자리
    rim = np.zeros(N)
    zc = zbuf[ys, xs]
    for k in range(1, 7):
        dx, dy = int(round(k * 0.85)), -int(round(k * 0.55))
        xx = np.clip(xs + dx, 0, Wb - 1); yy = np.clip(ys + dy, 0, Hb - 1)
        z2 = zbuf[yy, xx]
        open_ = (~cover[yy, xx]) | (z2 > zc + 2.5)
        rim += open_ * (1.0 - (k - 1) / 7)
    rim = np.clip(rim / 2.4, 0, 1) * (0.4 + 0.6 * np.clip(nbv @ norm([0.6, 0.6, 0.3]) + 0.4, 0, 1))

    col = alb * irr * (1 - emi[:, None]) + alb * (1.5 * emi[:, None]) + RIM_COL[None] * (rim * (0.35 + 0.9 * alb.mean(1)))[:, None]
    col = tonemap(col * EXPOSURE)
    srgb = lin2srgb(col)

    img = np.zeros((Hb, Wb, 3), np.float32); a = np.zeros((Hb, Wb), np.float32)
    img[ys, xs] = srgb; a[ys, xs] = 1
    lum = np.zeros((Hb, Wb), np.float32); lum[ys, xs] = irr @ np.array([0.3, 0.59, 0.11])
    out.update(irr=lum, img=img, a=a)
    return out


def tonemap(c):
    k = 0.78
    return np.where(c < k, c, k + (1 - k) * (1 - np.exp(-(c - k) / (1 - k))))


def downsample(img, a):
    """SS 해상도 색(sRGB 0..1)과 커버리지 -> (H,W,4) uint8 (프리멀티 평균 후 언프리멀티)."""
    Hb, Wb = a.shape
    H, W = Hb // SS, Wb // SS
    pm = (img * a[..., None]).reshape(H, SS, W, SS, 3).mean((1, 3))
    al = a.reshape(H, SS, W, SS).mean((1, 3))
    rgb = np.where(al[..., None] > 0, pm / np.maximum(al[..., None], 1e-9), 0)
    return np.dstack([np.round(rgb * 255), np.round(al * 255)]).astype(np.uint8)
