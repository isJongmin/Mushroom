"""voxel_map 공용: 정본 표 로드, 팔레트, 상자 헬퍼, 복셀 볼륨 → 상자 변환.

정본(발판, 스폰, 월드 크기)은 assets/_src/art2d_map/platforms.py 이다. 여기서 경로로 불러와 그대로 쓴다
(좌표를 바꾸지 않는다). 모듈 이름이 겹치지 않게 'canon' 으로 로드한다.
"""
import os
import importlib.util
import numpy as np
from vox import Box, rot_y, rot_z, rot_x, hex2lin

HERE = os.path.dirname(os.path.abspath(__file__))
_CANON_PATH = os.path.abspath(os.path.join(HERE, '..', 'art2d_map', 'platforms.py'))
_spec = importlib.util.spec_from_file_location('canon_platforms', _CANON_PATH)
canon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(canon)

WORLD_W, WORLD_H, GROUND_Y, DENSITY = canon.WORLD_W, canon.WORLD_H, canon.GROUND_Y, canon.DENSITY
PLATFORMS, SPAWNS, SPAWN = canon.PLATFORMS, canon.SPAWNS, canon.SPAWN

# ---------------------------------------------------------------- 팔레트 (새 시안: 따뜻한 오후, 피치~더스티 블루)
C = dict(
    cream='#FBF1DE', cream2='#EFDDBF', cream3='#DCC4A0', plaster='#F6E9D3', plaster2='#EAD8BC',
    stone1='#D9D0C4', stone2='#BDB2A6', stone3='#9C9187', stone4='#7A7068',
    wood1='#D9A46A', wood2='#B8804E', wood3='#8C5A36', wood4='#623E24', wood5='#4A2D1A',
    terra='#C8693F', terra2='#B45A34', terra3='#D9805A', terra4='#9E4A2A', pot='#C9724A', pot2='#A85A38',
    moss='#7E9A48', moss2='#6E8A3E', moss3='#93AE58', moss4='#5D7834',
    leaf1='#A8D26A', leaf2='#86BC52', leaf3='#6AA444', leaf4='#4E8638', leaf5='#3A6A2E',
    pine1='#5E8E5A', pine2='#4C7A4C', pine3='#3D6642', pine4='#6E9E64',
    pink1='#FFE0E6', pink2='#FBC4CF', pink3='#F2A2B4', pink4='#E2849C', pink5='#C96A86',
    red='#D9534A', red2='#B8403A', green_aw='#6FA46A', peach='#F7C9A0',
    iron='#3E3A42', iron2='#56505A', glass='#FFE7A8', bulb='#FFE2A0',
    bread='#D58E48', bread2='#B8702E', bread3='#E9B06A', crust='#9E5A26',
    white='#FFFFFF', yellow='#F5C94A', lilac='#B9A2E0', sky='#9CC8FF', ink='#2E2A3E',
    dirt1='#7A4E32', dirt2='#6C432B', dirt3='#855838', dirt4='#5E3A26', dirt5='#4E3020',
    grass1='#8DC456', grass2='#98CC5E', grass3='#82B84E', grass4='#A2D466', grass5='#78AE48',
)


def col(c):
    return C.get(c, c)


def B(cx, cy, cz, w, h, d, c, **kw):
    """중심 (cx, cy, cz), 크기 (w, h, d)."""
    kw.setdefault('bevel', min(0.38, 0.22 * min(w, h, d) + 0.05))
    return Box((cx, cy, cz), (w / 2, h / 2, d / 2), None, col(c), **kw)


def BR(cx, cy, cz, w, h, d, c, R, **kw):
    kw.setdefault('bevel', min(0.38, 0.22 * min(w, h, d) + 0.05))
    return Box((cx, cy, cz), (w / 2, h / 2, d / 2), R, col(c), **kw)


def _scale_keep(boxes, s):
    out = []
    for b in boxes:
        nb = b.moved((0, 0, 0))
        nb.c = b.c * s; nb.h = b.h * s
        out.append(nb)
    return out


def placed(boxes, x=0.0, y=0.0, z=0.0, yaw=0.0, s=1.0):
    if s != 1.0:
        boxes = _scale_keep(boxes, s)
    R = rot_y(yaw)
    return [b.moved((x, y, z), R) for b in boxes]


def pick(rng, pal):
    return pal[int(rng.integers(0, len(pal)))]


def hash01(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return ((h >> 8) & 0xFFFF) / 65535.0


def strip(rng, x1, x2, wmin, wmax):
    """x1~x2 를 정확히 덮는 블록 구간들."""
    xs = [x1]
    while xs[-1] < x2 - 1e-6:
        xs.append(min(x2, xs[-1] + float(rng.uniform(wmin, wmax))))
    if len(xs) > 2 and xs[-1] - xs[-2] < wmin * 0.5:
        xs.pop(-2)
    return list(zip(xs[:-1], xs[1:]))


# ---------------------------------------------------------------- 복셀 볼륨 → 상자
def vol_boxes(idx, pal, origin, cell, noise=0.04, bevel=None, emit=None, tag=''):
    """idx: (nx, ny, nz) int 배열 (0 = 빈칸, k = pal[k-1]). x 방향 같은 색 연속 칸을 상자 하나로 합친다.
    origin: idx[0,0,0] 칸의 최소 모서리(모델 좌표). cell: 칸 크기. emit: {k: (색, 세기)}."""
    nx, ny, nz = idx.shape
    bv = cell * 0.3 if bevel is None else bevel
    pcol = [hex2lin(col(p)) for p in pal]
    out = []
    ox, oy, oz = origin
    for j in range(ny):
        for k in range(nz):
            row = idx[:, j, k]
            if not row.any():
                continue
            ch = np.nonzero(np.diff(np.concatenate([[0], row, [0]])))[0]
            # 연속 구간 경계
            for a, b in zip(ch[:-1], ch[1:]):
                v = row[a]
                if v == 0:
                    continue
                cx = ox + (a + b) / 2 * cell
                out.append(Box((cx, oy + (j + 0.5) * cell, oz + (k + 0.5) * cell),
                               ((b - a) * cell / 2, cell / 2, cell / 2), None, pcol[v - 1], bevel=bv, noise=noise,
                               emit=None if not emit or v not in emit else emit[v], tag=tag))
    return out


def ellipsoid_grid(rx, ry, rz, cell, fn=None):
    """중심 원점 타원체를 칸 격자로. 반환 (mask, coords(X,Y,Z 칸 중심), origin)."""
    nx, ny, nz = [int(np.ceil(r / cell)) * 2 for r in (rx, ry, rz)]
    xs = (np.arange(nx) + 0.5) * cell - nx * cell / 2
    ys = (np.arange(ny) + 0.5) * cell - ny * cell / 2
    zs = (np.arange(nz) + 0.5) * cell - nz * cell / 2
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    m = (X / rx) ** 2 + (Y / ry) ** 2 + (Z / rz) ** 2 <= 1.0
    return m, (X, Y, Z), (-nx * cell / 2, -ny * cell / 2, -nz * cell / 2)


def cell_hash(X, Y, Z, seed=0, s=1.0):
    a = np.floor(X / s).astype(np.int64); b = np.floor(Y / s).astype(np.int64); c = np.floor(Z / s).astype(np.int64)
    h = (a * 73856093) ^ (b * 19349663) ^ (c * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h >> 7) & 0xFFFF) / 65535.0
