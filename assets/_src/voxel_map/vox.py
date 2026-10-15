"""버섯마을 voxel_map: 맵용 numpy 직교 레이캐스터.

assets/_src/voxel_v1/vox.py(캐릭터 렌더러)를 복사해 맵용으로 확장했다. 조명 방향/색, AO 색, 베벨, 림, 톤맵은
캐릭터와 같게 유지해 스타일을 맞춘다. 확장 내용:
  - 설정(Cfg): 슈퍼샘플/점유 격자 크기/AO 반경/그림자 레이 길이를 레이어마다 바꿀 수 있다
    (모델 단위가 클수록 격자도 키워서 메모리를 아낀다).
  - 점유 격자 범위를 상자들로부터 계산(타일 렌더). 상자 컬링(화면 범위 밖 상자는 건너뜀).
  - 발광(emit): 랜턴 유리, 창문. 조명과 무관하게 더해지고 발광 마스크를 따로 돌려줘 후처리 글로를 만든다.
  - 공기 원근(haze): 깊이에 따라 색을 하늘색으로 섞는다(먼 레이어).
  - 타일 렌더(render_tiled): 넓은 레이어를 세로 띠로 나눠 2코어 병렬 렌더 후 이어 붙인다.
결정적: 난수 없음(좌표 해시만).
"""
import numpy as np
from scipy import ndimage

BEVEL = 0.38      # 베벨 폭 (모델 단위)


class Cfg:
    def __init__(self, ss=3, grid=1.0, ao_radii=(1.2, 2.6, 4.6, 7.5), ao_w=(1.0, 0.8, 0.55, 0.35),
                 ao_gain=2.3, sh_step=1.0, sh_n=70, sh_k=2.2, haze=None, haze_z=(0, 0), haze_amt=0.0, haze_add=0.0,
                 rim=1.0, exposure=1.0, soft=0.11, bounce=1.0, sky=1.0, grade=(1.06, 1.0, 0.91)):
        self.ss, self.grid = ss, grid
        self.ao_radii, self.ao_w, self.ao_gain = ao_radii, ao_w, ao_gain
        self.sh_step, self.sh_n, self.sh_k = sh_step, sh_n, sh_k
        self.haze = None if haze is None else hex2lin(haze)
        self.haze_z, self.haze_amt, self.haze_add = haze_z, haze_amt, haze_add
        self.rim, self.exposure, self.soft = rim, exposure, soft
        self.bounce, self.sky = bounce, sky
        self.grade = np.array(grade, float)


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


I3 = np.eye(3)


class Box:
    __slots__ = ('c', 'h', 'R', 'col', 'bevel', 'decal', 'noise', 'emit', 'tag')

    def __init__(self, c, h, R=None, col='#FF00FF', bevel=BEVEL, decal=False, noise=0.04, emit=None, tag=''):
        self.c = np.asarray(c, float); self.h = np.asarray(h, float)
        self.R = I3 if R is None else np.asarray(R, float)
        self.col = hex2lin(col) if isinstance(col, str) else np.asarray(col, float)
        self.bevel, self.decal, self.noise, self.tag = bevel, decal, noise, tag
        self.emit = None if emit is None else (hex2lin(emit[0]) * emit[1] if isinstance(emit, tuple) else hex2lin(emit))

    def moved(self, d, R=None):
        """평행이동(+선택 회전, 회전은 원점 기준 후 이동)한 복사본."""
        b = Box.__new__(Box)
        for k in Box.__slots__:
            setattr(b, k, getattr(self, k))
        if R is not None:
            b.c = R @ self.c; b.R = R @ self.R
        b.c = b.c + np.asarray(d, float)
        return b


# ---------------------------------------------------------------- 조명 (뷰 공간: x 오른쪽, y 위, z 카메라 쪽) — 캐릭터와 동일
KEY_DIR = norm([-0.42, 0.72, 0.56])
KEY_COL = np.array([1.00, 0.87, 0.70]) * 1.9
SKY_COL = np.array([0.52, 0.57, 0.74]) * 0.62
GND_COL = np.array([0.40, 0.30, 0.24]) * 0.45
FILL_DIR = norm([0.45, 0.10, 0.90])
FILL_COL = np.array([0.55, 0.64, 0.86]) * 0.30
BACK_DIR = norm([0.80, 0.35, -0.50])
BACK_COL = np.array([1.00, 0.78, 0.58]) * 0.85
RIM_COL = np.array([1.00, 0.82, 0.62]) * 0.95

_D = np.array([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if (x, y, z) != (0, 0, 0)], float)
AO_DIRS = _D / np.linalg.norm(_D, axis=1)[:, None]


def jitter(ss, r0):
    n = ss * ss
    out = []
    for k in range(n):
        r = r0 * np.sqrt((k + 0.5) / n)
        a = k * 2.399963
        out.append((r * np.cos(a), r * np.sin(a)))
    return np.array(out)


def view_matrix(yaw, pitch):
    return rot_x(pitch) @ rot_y(yaw)


def _hash3(a, b, c):
    h = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (c.astype(np.int64) * 83492791)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h >> 7) & 0xFFFF) / 65535.0


def box_view_ext(b, V):
    Mv, cv = V @ b.R, V @ b.c
    return cv, np.abs(Mv) @ b.h


# ---------------------------------------------------------------- 점유 격자
class Grid:
    def __init__(self, boxes, V, lo, hi, cell):
        self.lo = np.array(lo, float); self.cell = cell
        n = np.maximum(np.ceil((np.array(hi, float) - self.lo) / cell).astype(int), 1)
        occ = np.zeros(n, np.float32)
        for b in boxes:
            if b.decal:
                continue
            Mv, cv = V @ b.R, V @ b.c
            ext = np.abs(Mv) @ b.h
            i0 = np.clip(np.floor((cv - ext - self.lo) / cell).astype(int), 0, n)
            i1 = np.clip(np.ceil((cv + ext - self.lo) / cell).astype(int) + 1, 0, n)
            if np.any(i1 <= i0):
                continue
            sl = occ[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
            if np.allclose(np.abs(Mv), np.eye(3)) or np.allclose(Mv, np.eye(3)):
                # 축 정렬 상자: 셀 중심 범위로 바로 채움
                ax = [self.lo[k] + (np.arange(i0[k], i1[k]) + 0.5) * cell for k in range(3)]
                m = [np.abs(ax[k] - cv[k]) <= ext[k] + 1e-6 for k in range(3)]
                sl[np.ix_(m[0], m[1], m[2])] = 1.0
                continue
            ax = [self.lo[k] + (np.arange(i0[k], i1[k]) + 0.5) * cell for k in range(3)]
            X, Y, Z = np.meshgrid(*ax, indexing='ij')
            P = np.stack([X - cv[0], Y - cv[1], Z - cv[2]], -1) @ Mv
            inside = np.all(np.abs(P) <= b.h + 1e-6, axis=-1)
            sl[inside] = 1.0
        self.occ = ndimage.gaussian_filter(occ, 0.55)

    def sample(self, P):
        idx = ((P - self.lo) / self.cell - 0.5).T
        return ndimage.map_coordinates(self.occ, idx, order=1, mode='constant', cval=0.0)


# ---------------------------------------------------------------- 렌더
def render(boxes, yaw, pitch, scale, cfg, *, W, H, anchor, occ_boxes=None, grid_box=None):
    """boxes: 보이는 상자. occ_boxes: 그림자/AO 차폐 상자(None=boxes).
    scale: 모델 단위당 px. anchor: 뷰 원점이 놓이는 px.
    반환: dict(rgba=(H,W,4) uint8, emit=(H,W) float 발광 커버리지, emitcol=(H,W,3) 선형)."""
    SS = cfg.ss
    occ_boxes = boxes if occ_boxes is None else occ_boxes
    V = view_matrix(yaw, pitch)
    Wb, Hb, S = W * SS, H * SS, scale * SS
    axp, ayp = anchor[0] * SS, anchor[1] * SS
    Z0 = 2000.0
    zbuf = np.full((Hb, Wb), np.inf)
    idb = np.full((Hb, Wb), -1, np.int32)

    cache = {}
    for i, b in enumerate(boxes):
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
        cache[i] = (Mv, cv)

    cover = idb >= 0
    ys, xs = np.nonzero(cover)
    N = len(ys)
    res = dict(rgba=np.zeros((H, W, 4), np.uint8), emit=np.zeros((H, W)), emitcol=np.zeros((H, W, 3)))
    if N == 0:
        return res
    P = np.zeros((N, 3)); ng = np.zeros((N, 3)); nbv = np.zeros((N, 3)); alb = np.zeros((N, 3))
    emi = np.zeros((N, 3)); isem = np.zeros(N)
    ids = idb[ys, xs]
    t = zbuf[ys, xs]
    P[:, 0] = ((xs + 0.5) - axp) / S
    P[:, 1] = (ayp - (ys + 0.5)) / S
    P[:, 2] = Z0 - t
    for i in np.unique(ids):
        sel = ids == i
        b = boxes[i]
        Mv, cv = cache[i]
        pl = (P[sel] - cv) @ Mv
        rel = np.abs(pl) / b.h
        axis = np.argmax(rel, -1)
        sgn = np.sign(pl[np.arange(len(pl)), axis])
        nl = np.zeros_like(pl); nl[np.arange(len(pl)), axis] = sgn
        ng[sel] = nl @ Mv.T
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
        if b.emit is not None:
            emi[sel] = b.emit[None, :] * (1 + 0.25 * (hsh[:, None] - 0.5))
            isem[sel] = 1.0

    # --- 격자 범위: 보이는 점 주변 + 차폐 상자
    if grid_box is None:
        lo = P.min(0) - 10; hi = P.max(0) + 10
    else:
        lo, hi = grid_box
    grid = Grid(occ_boxes, V, lo, hi, cfg.grid)

    # --- AO
    base = P + ng * 0.3 * cfg.grid / 0.5
    acc = np.zeros(N); norm_w = np.zeros(N)
    for r, wr in zip(cfg.ao_radii, cfg.ao_w):
        for dvec in AO_DIRS:
            wgt = np.clip(ng @ dvec, 0, 1) * wr
            m = wgt > 0
            if not np.any(m):
                continue
            o = np.zeros(N)
            o[m] = grid.sample(base[m] + dvec[None, :] * r)
            acc += wgt * o
            norm_w += wgt
    ao = 1 - np.clip(acc / np.maximum(norm_w, 1e-6) * cfg.ao_gain, 0, 0.88)
    ao = ao ** 1.15

    # --- 키라이트 그림자
    JT = jitter(SS, cfg.soft)
    jid = (ys % SS) * SS + (xs % SS)
    jt = JT[jid]
    up = norm(np.cross(KEY_DIR, [0, 0, 1])); vv = np.cross(KEY_DIR, up)
    Ld = KEY_DIR[None, :] + jt[:, :1] * up[None, :] + jt[:, 1:] * vv[None, :]
    Ld /= np.linalg.norm(Ld, axis=1, keepdims=True)
    lit = (nbv @ KEY_DIR) > -0.2
    shadow = np.ones(N)
    if np.any(lit):
        pos = P[lit] + ng[lit] * 1.1 * cfg.grid + Ld[lit] * 0.6 * cfg.grid
        L = Ld[lit]
        tau = np.zeros(len(pos))
        for _ in range(cfg.sh_n):
            pos = pos + L * cfg.sh_step
            tau += grid.sample(pos) * cfg.sh_step
        shadow[lit] = np.exp(-tau * cfg.sh_k / cfg.grid * 0.5)

    ao3 = ao[:, None] ** np.array([[0.85, 1.0, 1.2]])
    nd = lambda dv: np.clip(nbv @ dv, 0, 1)
    irr = (KEY_COL[None] * (nd(KEY_DIR) * shadow)[:, None]
           + cfg.sky * SKY_COL[None] * (0.55 + 0.45 * nbv[:, 1])[:, None] * ao3
           + cfg.bounce * GND_COL[None] * (0.5 - 0.5 * nbv[:, 1])[:, None] * ao3
           + FILL_COL[None] * nd(FILL_DIR)[:, None] * ao3
           + BACK_COL[None] * nd(BACK_DIR)[:, None] * (0.35 + 0.65 * ao3))

    # --- 화면 공간 림
    rim = np.zeros(N)
    zc = zbuf[ys, xs]
    for k in range(1, 7):
        dx, dy = int(round(k * 0.85 * SS / 4)), -int(round(k * 0.55 * SS / 4))
        if dx == 0 and dy == 0:
            continue
        xx = np.clip(xs + dx, 0, Wb - 1); yy = np.clip(ys + dy, 0, Hb - 1)
        z2 = zbuf[yy, xx]
        open_ = (~cover[yy, xx]) | (z2 > zc + 2.5)
        rim += open_ * (1.0 - (k - 1) / 7)
    rim = np.clip(rim / 2.4, 0, 1) * (0.4 + 0.6 * np.clip(nbv @ norm([0.6, 0.6, 0.3]) + 0.4, 0, 1)) * cfg.rim

    col = alb * irr + RIM_COL[None] * (rim * (0.35 + 0.9 * alb.mean(1)))[:, None]
    col = col * (1 - isem[:, None] * 0.6) + emi
    col = tonemap(col * cfg.exposure * cfg.grade[None])
    if cfg.haze is not None and cfg.haze_amt > 0:
        z0, z1 = cfg.haze_z
        # P[:,2] 는 뷰 공간 z (카메라 쪽 +). haze_amt = 기본량, haze_z = (z0, z1) 구간에서 haze_add 만큼 더한다.
        f = np.full(N, cfg.haze_amt)
        if z0 != z1:
            f = f + cfg.haze_add * np.clip((z0 - P[:, 2]) / (z0 - z1), 0, 1)
        col = col * (1 - f[:, None]) + cfg.haze[None] * f[:, None]
    srgb = lin2srgb(col)

    img = np.zeros((Hb, Wb, 3)); a = np.zeros((Hb, Wb))
    img[ys, xs] = srgb; a[ys, xs] = 1
    res['rgba'] = downsample(img, a, SS)
    em = np.zeros((Hb, Wb)); em[ys, xs] = isem
    ec = np.zeros((Hb, Wb, 3)); ec[ys, xs] = emi
    res['emit'] = em.reshape(H, SS, W, SS).mean((1, 3))
    res['emitcol'] = ec.reshape(H, SS, W, SS, 3).mean((1, 3))
    return res


def tonemap(c):
    k = 0.78
    return np.where(c < k, c, k + (1 - k) * (1 - np.exp(-(c - k) / (1 - k))))


def downsample(img, a, SS):
    Hb, Wb = a.shape
    H, W = Hb // SS, Wb // SS
    pm = (img * a[..., None]).reshape(H, SS, W, SS, 3).mean((1, 3))
    al = a.reshape(H, SS, W, SS).mean((1, 3))
    rgb = np.where(al[..., None] > 0, pm / np.maximum(al[..., None], 1e-9), 0)
    return np.dstack([np.round(rgb * 255), np.round(al * 255)]).astype(np.uint8)


# ---------------------------------------------------------------- 타일 렌더
def _tile_job(args):
    boxes, yaw, pitch, scale, cfg, X0, X1, H, anchor, pad, margin_l, margin_r = args
    V = view_matrix(yaw, pitch)
    # 화면 x(px) → 뷰 x(모델 단위)
    vx0 = (X0 - pad - anchor[0]) / scale
    vx1 = (X1 + pad - anchor[0]) / scale
    vis, occ = [], []
    ylo, yhi, zlo, zhi = np.inf, -np.inf, np.inf, -np.inf
    for b in boxes:
        cv, ext = box_view_ext(b, V)
        if cv[0] + ext[0] >= vx0 - margin_l and cv[0] - ext[0] <= vx1 + margin_r:
            occ.append(b)
            ylo = min(ylo, cv[1] - ext[1]); yhi = max(yhi, cv[1] + ext[1])
            zlo = min(zlo, cv[2] - ext[2]); zhi = max(zhi, cv[2] + ext[2])
            if cv[0] + ext[0] >= vx0 and cv[0] - ext[0] <= vx1:
                vis.append(b)
    W = X1 - X0 + 2 * pad
    if not vis:
        return np.zeros((H, X1 - X0, 4), np.uint8), np.zeros((H, X1 - X0)), np.zeros((H, X1 - X0, 3))
    # 화면 위아래로 보이는 범위만 격자에 (아래로 깊은 지면 상자는 잘라도 된다)
    vy_lo = (anchor[1] - H) / scale - 4
    vy_hi = anchor[1] / scale + 4
    lo = (vx0 - margin_l - 2, max(ylo, vy_lo - 12) - 2, zlo - 2)
    hi = (vx1 + margin_r + 2, min(yhi, vy_hi + 60) + 2, zhi + 2)
    r = render(vis, yaw, pitch, scale, cfg, W=W, H=H, anchor=(anchor[0] - X0 + pad, anchor[1]),
               occ_boxes=occ, grid_box=(lo, hi))
    sl = slice(pad, pad + X1 - X0)
    return r['rgba'][:, sl], r['emit'][:, sl], r['emitcol'][:, sl]


def render_tiled(boxes, yaw, pitch, scale, cfg, *, W, H, anchor, tile=200, pad=8, margin_l=None, margin_r=12,
                 pool=None):
    if margin_l is None:
        margin_l = cfg.sh_n * cfg.sh_step * 0.45 + 10
    jobs = []
    for X0 in range(0, W, tile):
        X1 = min(W, X0 + tile)
        jobs.append((boxes, yaw, pitch, scale, cfg, X0, X1, H, anchor, pad, margin_l, margin_r))
    outs = pool.map(_tile_job, jobs) if pool is not None else [_tile_job(j) for j in jobs]
    rgba = np.concatenate([o[0] for o in outs], 1)
    em = np.concatenate([o[1] for o in outs], 1)
    ec = np.concatenate([o[2] for o in outs], 1)
    return rgba, em, ec


def add_glow(rgba, em, ec, sigma=6.0, strength=0.9, sigma2=None, strength2=0.0):
    """발광 마스크로 글로(빛 번짐)를 만들어 RGBA에 더한다(투명 영역에도 반투명 빛)."""
    a = rgba[..., 3:4] / 255.0
    rgb = lin_from_u8(rgba[..., :3]) * a      # premultiplied linear
    col = np.where(em[..., None] > 1e-6, ec / np.maximum(em[..., None], 1e-6), 0)
    g = np.zeros(em.shape + (3,))
    ga = np.zeros(em.shape)
    for s, k in ((sigma, strength), (sigma2, strength2)):
        if not s or k <= 0:
            continue
        for c in range(3):
            g[..., c] += ndimage.gaussian_filter(ec[..., c], s) * k
        ga += ndimage.gaussian_filter(em, s) * k
    ga = np.clip(ga, 0, 1)
    out_a = a[..., 0] + ga * (1 - a[..., 0]) * 0.85
    prem = rgb + g * 0.55
    rgbn = np.where(out_a[..., None] > 1e-6, prem / np.maximum(out_a[..., None], 1e-6), 0)
    srgb = lin2srgb(rgbn)
    return np.dstack([np.round(srgb * 255), np.round(np.clip(out_a, 0, 1) * 255)]).astype(np.uint8)


def lin_from_u8(u):
    c = u / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
