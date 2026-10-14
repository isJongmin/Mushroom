"""미리보기 (스크래치용): chars_6x, outline_compare, walk.gif, scene_2x."""
import os
from PIL import Image

W, H = 48, 64
BG = (0xEA, 0xF6, 0xFF, 255)


def frame(im, i):
    return im.crop((W * i, 0, W * (i + 1), H))


def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def on_bg(im, bg=BG):
    b = Image.new('RGBA', im.size, bg)
    b.alpha_composite(im)
    return b


def grid(rows, k, pad=2):
    """rows: [[img,...],...] (같은 크기) -> 배경 위 격자."""
    nr, nc = len(rows), max(len(r) for r in rows)
    out = Image.new('RGBA', ((W * nc + pad * (nc + 1)) * k, (H * nr + pad * (nr + 1)) * k), BG)
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            out.alpha_composite(up(im, k), ((pad + c * (W + pad)) * k, (pad + r * (H + pad)) * k))
    return out


def make(d, comps, scene_img):
    os.makedirs(d, exist_ok=True)
    cids = sorted({c for c, _ in comps})
    rows = [[frame(comps[(c, False)], i) for i in (0, 1, 6)] for c in cids]
    grid(rows, 6).convert('RGB').save(os.path.join(d, 'chars_6x.png'))
    rows = []
    for c in (cids[0], cids[2]):
        for v in (False, True, 'sil'):
            rows.append([frame(comps[(c, v)], i) for i in (0, 1, 6)])
    grid(rows, 6).convert('RGB').save(os.path.join(d, 'outline_compare.png'))
    frames = []
    for k in range(4):
        frames.append(grid([[frame(comps[(c, False)], 2 + k) for c in cids]], 6).convert('RGB'))
    frames[0].save(os.path.join(d, 'walk.gif'), save_all=True, append_images=frames[1:], duration=150, loop=0)
    # walk 프레임 정지 그림 (Read로 확인용)
    grid([[frame(comps[(c, False)], 2 + k) for k in range(4)] for c in cids], 6).convert('RGB').save(
        os.path.join(d, 'walk_frames_6x.png'))
    up(scene_img, 2).convert('RGB').save(os.path.join(d, 'scene_2x.png'))
