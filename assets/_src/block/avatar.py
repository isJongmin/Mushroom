"""아바타 레이어 시트 + manifest.json + outline.json 생성.

레이어 독립성: 각 파츠는 혼자 렌더한 뒤, 공통 몸(skin)이 더 앞에 있는 픽셀만 지운다.
다른 옷/머리 파츠에는 의존하지 않으므로 어떤 조합도 layerOrder 대로 쌓으면 맞물린다.
머리카락은 '옷 입은 몸'(몸통/팔/다리를 1px 부풀린 가상 몸)보다 뒤에 있는 픽셀을 hair_back 으로,
나머지를 hair_front 로 자동 분리한다.
"""
import os
import json
from PIL import Image

from palette import PAL, LINE, HEX2TOK
from render import render, to_image
from parts import parts_table, PRESETS, FRAMES, LAYER_ORDER, body_boxes, mannequin_clothed

W, H = 48, 64
AX, AY = 24, 60


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


_BODY = {}
_MAN = {}


def body_ref(fi):
    if fi not in _BODY:
        fname, view, pose = FRAMES[fi]
        _BODY[fi] = render(body_boxes(), view, pose, W, H, AX, AY, ao=False)
        _MAN[fi] = render(mannequin_clothed(), view, pose, W, H, AX, AY, ao=False)
    return _BODY[fi], _MAN[fi]


def render_part(cat, boxes_fn):
    """-> {layer: [cols per frame]}"""
    boxes = boxes_fn()
    res = {}
    for fi, (fname, view, pose) in enumerate(FRAMES):
        body, man = body_ref(fi)
        buf = render(boxes, view, pose, W, H, AX, AY)
        if cat == 'skin':
            res.setdefault('skin', []).append(buf.col)
        elif cat == 'hair':
            back, front = split(buf, lambda x, y: man.z[y][x] < buf.z[y][x] - 0.01)
            cut_by_body(front, body)
            cut_by_body(back, body)
            res.setdefault('hair_back', []).append(back.col)
            res.setdefault('hair_front', []).append(front.col)
        else:
            if cat != 'face':
                cut_by_body(buf, body)
            res.setdefault(cat, []).append(buf.col)
    return res


def sheet(frames):
    im = Image.new('RGBA', (W * len(frames), H), (0, 0, 0, 0))
    for i, cols in enumerate(frames):
        im.paste(to_image(cols, Image), (W * i, 0))
    return im


def build(root):
    """root = 저장소 루트. assets/avatar/** 를 새로 쓴다. -> (manifest, {(layer,id): Image})"""
    out = os.path.join(root, 'assets', 'avatar')
    table = parts_table()
    sheets = {}
    for cat, items in table.items():
        for pid, label, fn in items:
            if fn is None:
                continue
            for layer, frames in render_part(cat, fn).items():
                sheets[(layer, pid)] = sheet(frames)
    for (layer, pid), im in sheets.items():
        d = os.path.join(out, layer)
        os.makedirs(d, exist_ok=True)
        im.save(os.path.join(d, pid + '.png'), optimize=False)

    manifest = {
        'frame': {'w': W, 'h': H},
        'anchor': {'x': AX, 'y': AY},
        'scale': 2,
        'frames': [f[0] for f in FRAMES],
        'animations': {'idle': {'frames': [1], 'ms': 500}, 'walk': {'frames': [2, 3, 4, 5], 'ms': 150}},
        'layerOrder': LAYER_ORDER,
        'parts': {cat: [{'id': pid, 'label': label} for pid, label, fn in items]
                  for cat, items in (('skin', table['skin']), ('hair', table['hair']), ('face', table['face']),
                                     ('top', table['top']), ('bottom', table['bottom']), ('shoes', table['shoes']),
                                     ('hat', table['hat']))},
        'presets': [{'label': lb, 'avatar': av} for lb, av in PRESETS],
    }
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')

    # outline.json: 아바타 PNG 에 실제로 쓰인 모든 불투명 색 -> line 색
    used = set()
    for im in sheets.values():
        for (cnt, px) in im.getcolors(1 << 16):
            if px[3] == 255:
                used.add('#%02X%02X%02X' % px[:3])
    outline = {h: PAL[LINE[HEX2TOK[h]]] for h in sorted(used)}
    with open(os.path.join(out, 'outline.json'), 'w', encoding='utf-8') as f:
        json.dump(outline, f, indent=2)
        f.write('\n')
    return manifest, sheets, outline


# ------------------------------------------------------------------ 프런트와 같은 합성/외곽선 (미리보기, 검증용)
def compose(sheets, avatar):
    im = Image.new('RGBA', (W * len(FRAMES), H), (0, 0, 0, 0))
    for layer in LAYER_ORDER:
        key = 'hair' if layer in ('hair_back', 'hair_front') else layer
        pid = avatar.get(key)
        if pid is None or pid == 'none':
            continue
        im.alpha_composite(sheets[(layer, pid)])
    return im


def silhouette(im, outline):
    """계약의 외곽선 규칙: 투명 픽셀 중 4방향(아래, 왼쪽, 오른쪽, 위 순) 이웃이 불투명이면 그 색의 line 색.
    프레임 경계 안에서만 이웃을 본다."""
    src = im.load()
    out = im.copy()
    dst = out.load()
    nf = im.width // W
    for f in range(nf):
        for y in range(H):
            for x in range(W):
                X = f * W + x
                if src[X, y][3]:
                    continue
                for dx, dy in ((0, 1), (-1, 0), (1, 0), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and src[f * W + nx, ny][3]:
                        p = src[f * W + nx, ny]
                        h = outline.get('#%02X%02X%02X' % p[:3])
                        if h:
                            dst[X, y] = (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)
                        else:
                            dst[X, y] = (int(p[0] * 0.45), int(p[1] * 0.45), int(p[2] * 0.45), 255)
                        break
    return out
