"""block_v1 빌드: 파츠 레이어 시트 + 캐릭터 합성본 + 타일/장면.

python3 build.py            -> out/ 생성
python3 build.py PREVIEW_DIR -> out/ 생성 + 미리보기(6배, gif, 장면 2배)
결정적: 난수 없음(좌표 해시 노이즈). 같은 코드면 같은 PNG.
"""
import os
import sys
import json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import render, outline_inner, to_image   # noqa: E402
from chars import PARTS, CHARS, FRAMES, LAYER_ORDER, mannequin_clothed  # noqa: E402

W, H = 48, 64
AX, AY = 24, 60
OUT = os.path.join(HERE, 'out')


def cut_by_body(buf, body):
    for y in range(buf.H):
        for x in range(buf.W):
            if buf.col[y][x] is not None and body.z[y][x] < buf.z[y][x] - 0.01:
                buf.col[y][x] = None
                buf.mat[y][x] = None


def split(buf, mask_fn):
    a, b = buf.copy_empty(), buf.copy_empty()
    for y in range(buf.H):
        for x in range(buf.W):
            if buf.col[y][x] is None:
                continue
            t = a if mask_fn(x, y) else b
            t.col[y][x], t.mat[y][x], t.z[y][x] = buf.col[y][x], buf.mat[y][x], buf.z[y][x]
    return a, b


def render_part_frames(layer, pid):
    """-> {out_layer: [Buf per frame]}"""
    boxes = PARTS[layer][pid]()
    res = {}
    for fname, view, pose in FRAMES:
        body = render(PARTS['body']['skin_light'](), view, pose, W, H, AX, AY)
        buf = render(boxes, view, pose, W, H, AX, AY)
        if layer == 'body':
            res.setdefault('body', []).append(buf)
            continue
        if layer == 'hair':
            man = render(mannequin_clothed(), view, pose, W, H, AX, AY)
            back, front = split(buf, lambda x, y: man.z[y][x] < buf.z[y][x] - 0.01)
            cut_by_body(front, body)
            cut_by_body(back, body)
            res.setdefault('hair_back', []).append(back)
            res.setdefault('hair_front', []).append(front)
            continue
        if layer != 'face':
            cut_by_body(buf, body)
        res.setdefault(layer, []).append(buf)
    return res


def silhouette(col, mat):
    from palette import MATS
    out = [r[:] for r in col]
    for y in range(H):
        for x in range(W):
            if col[y][x] is not None:
                continue
            best = None
            for ddx, ddy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
                nx, ny = x + ddx, y + ddy
                if 0 <= nx < W and 0 <= ny < H and col[ny][nx] is not None:
                    m = mat[ny][nx]
                    best = MATS[m].line if m else 'ink'
                    break
            if best:
                out[y][x] = best
    return out


def sheet(bufs, outline=False):
    im = Image.new('RGBA', (W * len(bufs), H), (0, 0, 0, 0))
    for i, b in enumerate(bufs):
        cols = outline_inner(b) if outline else b.col
        im.paste(to_image(cols, Image), (W * i, 0))
    return im


def build_avatar():
    cache = {}
    for layer, items in PARTS.items():
        for pid in items:
            for ol, bufs in render_part_frames(layer, pid).items():
                cache[(ol, pid)] = bufs
    for (ol, pid), bufs in cache.items():
        for outline, sub in ((False, 'avatar'), (True, 'avatar_outline')):
            d = os.path.join(OUT, sub, ol)
            os.makedirs(d, exist_ok=True)
            # 외곽선은 face 레이어에 적용하지 않음
            sheet(bufs, outline and ol != 'face').save(os.path.join(d, pid + '.png'))
    comps = {}
    for cid, combo in CHARS:
        for outline, sub in ((False, 'avatar'), (True, 'avatar_outline')):
            im = Image.new('RGBA', (W * len(FRAMES), H), (0, 0, 0, 0))
            for ol in LAYER_ORDER:
                key = 'hair' if ol in ('hair_back', 'hair_front') else ol
                if key not in combo:
                    continue
                p = os.path.join(OUT, sub, ol, combo[key] + '.png')
                im.alpha_composite(Image.open(p))
            d = os.path.join(OUT, sub, '_composite')
            os.makedirs(d, exist_ok=True)
            im.save(os.path.join(d, cid + '.png'))
            comps[(cid, outline)] = im
        # C안: 합성본 바깥 실루엣 1px 외곽선 (인접 픽셀 재질의 line 색)
        frames = []
        for fi in range(len(FRAMES)):
            col = [[None] * W for _ in range(H)]
            mat = [[None] * W for _ in range(H)]
            for ol in LAYER_ORDER:
                key = 'hair' if ol in ('hair_back', 'hair_front') else ol
                if key not in combo:
                    continue
                b = cache[(ol, combo[key])][fi]
                for y in range(H):
                    for x in range(W):
                        if b.col[y][x] is not None:
                            col[y][x], mat[y][x] = b.col[y][x], b.mat[y][x]
            frames.append(silhouette(col, mat))
        im = Image.new('RGBA', (W * len(FRAMES), H), (0, 0, 0, 0))
        for i, c in enumerate(frames):
            im.paste(to_image(c, Image), (W * i, 0))
        d = os.path.join(OUT, 'avatar_silhouette', '_composite')
        os.makedirs(d, exist_ok=True)
        im.save(os.path.join(d, cid + '.png'))
        comps[(cid, 'sil')] = im
    manifest = {
        'frame': {'w': W, 'h': H}, 'anchor': {'x': AX, 'y': AY}, 'scale': 2,
        'frames': [f[0] for f in FRAMES],
        'animations': {'front': {'frames': [0]}, 'side_idle': {'frames': [1]},
                       'walk': {'frames': [2, 3, 4, 5], 'ms': 150}, 'back': {'frames': [6]}},
        'layerOrder': LAYER_ORDER,
        'parts': {ol: sorted({pid for (o, pid) in cache if o == ol}) for ol in LAYER_ORDER},
        'hairSplit': 'hair id 하나가 hair_back/hair_front 두 시트를 가진다',
        'characters': {cid: combo for cid, combo in CHARS},
    }
    with open(os.path.join(OUT, 'avatar_manifest.json'), 'w') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return comps


if __name__ == '__main__':
    comps = build_avatar()
    import scene
    scene_img = scene.build(OUT, comps)
    if len(sys.argv) > 1:
        import preview
        preview.make(sys.argv[1], comps, scene_img)
