"""버섯마을 2D 맵 벡터 렌더러 (사이클 9).

장면(Scene)은 그리기 명령 목록이다. 기하는 장면을 만들 때 한 번 정하고(난수 포함),
render() 는 레이어를 타일로 나눠 타일마다 같은 명령을 4배 슈퍼샘플 버퍼에 그린 뒤 평균으로 줄인다.
그래서 결과는 타일 크기와 상관없이 같고, 결정적이다.

좌표: 레이어 이미지 px(1x). 다각형은 (N,2) numpy 배열.
명령:
  shape(polys, fill, line, lw)   외곽선(각 다각형 둘레를 폭 2*lw 로 긋기) 후 채움 → 바깥으로 lw px 외곽선
  fill(polys, color, alpha, grad) 채움만 (grad = [(y, '#hex'), ..] 세로 그라데이션)
  stroke(lines, color, w, alpha)  열린 선(둥근 끝)
  clip(polys) / unclip()          이후 명령을 다각형 안으로 제한(중첩 가능, 교집합)
"""
import numpy as np
from PIL import Image, ImageDraw

SS = 4


def hexc(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def mix(a, b, t):
    """두 HEX 색을 t(0=a, 1=b)로 섞은 HEX."""
    ca, cb = hexc(a), hexc(b)
    c = ca * (1 - t) + cb * t
    return '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in c)


def _bbox(polys, pad=0.0):
    xs0 = min(float(p[:, 0].min()) for p in polys)
    ys0 = min(float(p[:, 1].min()) for p in polys)
    xs1 = max(float(p[:, 0].max()) for p in polys)
    ys1 = max(float(p[:, 1].max()) for p in polys)
    return (xs0 - pad, ys0 - pad, xs1 + pad, ys1 + pad)


def _as_polys(p):
    if isinstance(p, np.ndarray):
        return [p]
    return [np.asarray(q, np.float64) for q in p]


class Scene:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ops = []

    def shape(self, polys, fill, line=None, lw=2.5, alpha=1.0):
        polys = _as_polys(polys)
        if line is not None and lw > 0:
            self.ops.append(('strokeclosed', _bbox(polys, lw + 1), polys, hexc(line), lw * 2, alpha))
        self.ops.append(('fill', _bbox(polys, 1), polys, hexc(fill), alpha, None))

    def fill(self, polys, color, alpha=1.0, grad=None, agrad=None):
        """agrad = [(y, alpha), ..] 이면 세로 방향으로 불투명도가 바뀐다(안개, 글로우)."""
        polys = _as_polys(polys)
        if agrad is not None:
            alpha = (np.array([float(y) for y, _ in agrad]), np.array([float(a) for _, a in agrad]) * alpha)
        g = None
        if grad is not None:
            g = ([float(y) for y, _ in grad], np.stack([hexc(c) for _, c in grad]))
        self.ops.append(('fill', _bbox(polys, 1), polys, hexc(color), alpha, g))

    def outline(self, polys, color, lw=2.5, alpha=1.0):
        """닫힌 다각형 둘레만 긋기(중심선 기준 폭 2*lw)."""
        polys = _as_polys(polys)
        self.ops.append(('strokeclosed', _bbox(polys, lw + 1), polys, hexc(color), lw * 2, alpha))

    def stroke(self, lines, color, w=2.5, alpha=1.0):
        lines = _as_polys(lines)
        self.ops.append(('stroke', _bbox(lines, w / 2 + 1), lines, hexc(color), w, alpha))

    def clip(self, polys):
        polys = _as_polys(polys)
        self.ops.append(('clip', _bbox(polys, 1), polys))

    def unclip(self):
        self.ops.append(('unclip', None))

    def extend(self, other):
        self.ops.extend(other.ops)


class _Tile:
    def __init__(self, x0, y0, w, h):
        self.x0, self.y0, self.w, self.h = x0, y0, w, h
        self.W, self.H = w * SS, h * SS
        self.buf = np.zeros((self.H, self.W, 4), np.float32)
        self.clips = []  # (bx0, by0, bool array) 버퍼 좌표

    def _box(self, bb):
        bx0 = int(np.floor((bb[0] - self.x0) * SS))
        by0 = int(np.floor((bb[1] - self.y0) * SS))
        bx1 = int(np.ceil((bb[2] - self.x0) * SS)) + 1
        by1 = int(np.ceil((bb[3] - self.y0) * SS)) + 1
        bx0, by0 = max(bx0, 0), max(by0, 0)
        bx1, by1 = min(bx1, self.W), min(by1, self.H)
        if bx1 <= bx0 or by1 <= by0:
            return None
        return bx0, by0, bx1, by1

    def _pts(self, p, bx0, by0):
        q = (p - (self.x0, self.y0)) * SS - (bx0, by0) - 0.5
        return [tuple(v) for v in q.tolist()]

    def raster(self, kind, bb, polys, width=0.0):
        box = self._box(bb)
        if box is None:
            return None, None
        bx0, by0, bx1, by1 = box
        im = Image.new('L', (bx1 - bx0, by1 - by0), 0)
        d = ImageDraw.Draw(im)
        if kind == 'fill':
            for p in polys:
                if len(p) >= 3:
                    d.polygon(self._pts(p, bx0, by0), fill=255)
        else:
            W = max(1, int(round(width * SS)))
            r = W / 2.0
            for p in polys:
                pts = self._pts(p, bx0, by0)
                if kind == 'strokeclosed':
                    pts = pts + pts[:1]
                if len(pts) >= 2:
                    d.line(pts, fill=255, width=W, joint='curve')
                if kind == 'stroke' or W > 6:
                    ends = (pts[0], pts[-1]) if kind == 'stroke' else ()
                    for (x, y) in ends:
                        d.ellipse((x - r + 0.5, y - r + 0.5, x + r - 0.5, y + r - 0.5), fill=255)
        m = np.asarray(im) > 127
        for (cx0, cy0, cm) in self.clips:
            sub = np.zeros_like(m)
            # 클립 마스크와 교집합
            ox0, oy0 = max(bx0, cx0), max(by0, cy0)
            ox1, oy1 = min(bx1, cx0 + cm.shape[1]), min(by1, cy0 + cm.shape[0])
            if ox1 > ox0 and oy1 > oy0:
                sub[oy0 - by0:oy1 - by0, ox0 - bx0:ox1 - bx0] = cm[oy0 - cy0:oy1 - cy0, ox0 - cx0:ox1 - cx0]
            m &= sub
        return box, m

    def paint(self, box, m, rgb, alpha, grad=None):
        if box is None or not m.any():
            return
        bx0, by0, bx1, by1 = box
        reg = self.buf[by0:by1, bx0:bx1]
        if grad is not None:
            ys = self.y0 + (np.arange(by0, by1) + 0.5) / SS
            col = np.stack([np.interp(ys, grad[0], grad[1][:, i]) for i in range(3)], -1).astype(np.float32)
            col = np.broadcast_to(col[:, None, :], (by1 - by0, bx1 - bx0, 3))
        if isinstance(alpha, tuple):
            ys = self.y0 + (np.arange(by0, by1) + 0.5) / SS
            arow = np.interp(ys, alpha[0], alpha[1]).astype(np.float32)
            a = np.broadcast_to(arow[:, None], m.shape)[m][:, None]
            sel = reg[m]
            c = col[m] if grad is not None else rgb[None, :]
            sel *= (1 - a)
            sel[:, :3] += c * a
            sel[:, 3:4] += a
            reg[m] = sel
            return
        if alpha >= 1.0:
            if grad is None:
                reg[m] = (rgb[0], rgb[1], rgb[2], 1.0)
            else:
                reg[m, :3] = col[m]
                reg[m, 3] = 1.0
        else:
            a = np.float32(alpha)
            sel = reg[m]
            c = col[m] if grad is not None else rgb[None, :]
            sel *= (1 - a)
            sel[:, :3] += c * a
            sel[:, 3] += a
            reg[m] = sel

    def run(self, ops):
        for op in ops:
            k = op[0]
            if k == 'unclip':
                self.clips.pop()
                continue
            bb = op[1]
            if k == 'clip':
                box, m = self.raster('fill', bb, op[2])
                if box is None:
                    self.clips.append((0, 0, np.zeros((1, 1), bool)))
                else:
                    full = np.zeros((box[3] - box[1], box[2] - box[0]), bool)
                    full[:] = m
                    self.clips.append((box[0], box[1], full))
                continue
            if bb[2] < self.x0 or bb[0] > self.x0 + self.w or bb[3] < self.y0 or bb[1] > self.y0 + self.h:
                continue
            if k == 'fill':
                box, m = self.raster('fill', bb, op[2])
                self.paint(box, m, op[3], op[4], op[5])
            else:
                box, m = self.raster(k, bb, op[2], op[4])
                self.paint(box, m, op[3], op[5])

    def result(self):
        b = self.buf.reshape(self.h, SS, self.w, SS, 4).mean(axis=(1, 3))
        return b


def render(scene, tile=512, pad=24, bg=None, region=None, jobs=1):
    """장면을 (H, W, 4) 프리멀티 float32 로 렌더. region=(x0,y0,x1,y1) 이면 그 부분만."""
    rx0, ry0, rx1, ry1 = region or (0, 0, scene.w, scene.h)
    W, H = rx1 - rx0, ry1 - ry0
    out = np.zeros((H, W, 4), np.float32)
    tiles = [(tx, ty) for ty in range(0, H, tile) for tx in range(0, W, tile)]
    args = [(scene.ops, rx0 + tx - pad, ry0 + ty - pad, min(tile, W - tx), min(tile, H - ty), pad, bg) for tx, ty in tiles]
    if jobs > 1:
        import multiprocessing as mp
        global _OPS
        _OPS = scene.ops
        with mp.get_context('fork').Pool(jobs) as pool:
            res = pool.map(_tile_job_fork, [a[1:] for a in args], chunksize=1)
    else:
        res = [_tile_job(*a) for a in args]
    for (tx, ty), r in zip(tiles, res):
        out[ty:ty + r.shape[0], tx:tx + r.shape[1]] = r
    return out


_OPS = None


def _tile_job_fork(a):
    return _tile_job(_OPS, *a)


def _tile_job(ops, x0, y0, tw, th, pad, bg):
    t = _Tile(x0, y0, tw + 2 * pad, th + 2 * pad)
    if bg is not None:
        t.buf[:] = (*hexc(bg), 1.0)
    t.run(ops)
    return t.result()[pad:pad + th, pad:pad + tw]


def to_rgba8(pm):
    a = pm[..., 3:4]
    rgb = np.where(a > 1e-6, pm[..., :3] / np.maximum(a, 1e-6), 0)
    o = np.concatenate([rgb, a], -1)
    return (np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8)
