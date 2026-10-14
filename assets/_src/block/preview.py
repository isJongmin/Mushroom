"""미리보기 이미지 (검수용, 저장소 밖 폴더에 쓴다).

parts_4x.png       파츠 카테고리별 전체 목록 (front + side_idle), 기준 몸 위에 얹어서
presets_6x.png     프리셋 6종 x 7프레임, 외곽선 적용
walk.gif           프리셋 6종 걷기 (150ms)
walk_frames_6x.png 걷기 4프레임 정지 그림
random_combos.png  무작위 조합 12개 (고정 시드) 외곽선 적용, front/side_idle/side_walk0/back
world_2x.png       맵 전체 레이어 합성 (parallax 무시) + 캐릭터 6명
"""
import os
import random
from PIL import Image, ImageDraw

from avatar import W, H, AX, AY, compose, silhouette
from parts import parts_table, PRESETS

BG = (0xEA, 0xF6, 0xFF, 255)
BG2 = (0xD8, 0xF3, 0xFE, 255)


def frame(im, i):
    return im.crop((W * i, 0, W * (i + 1), H))


def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def grid(rows, k, pad=2, labels=None):
    nr, nc = len(rows), max(len(r) for r in rows)
    out = Image.new('RGBA', ((W * nc + pad * (nc + 1)) * k, (H * nr + pad * (nr + 1)) * k), BG)
    d = ImageDraw.Draw(out)
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            x, y = (pad + c * (W + pad)) * k, (pad + r * (H + pad)) * k
            d.rectangle([x, y, x + W * k - 1, y + H * k - 1], fill=BG2 if (r + c) % 2 else BG)
            # 기준점 표시 (지면선)
            d.line([x, y + AY * k, x + W * k - 1, y + AY * k], fill=(0xBB, 0xE8, 0xFC, 255))
            out.alpha_composite(up(im, k), (x, y))
    return out


BASE = {'skin': 'light', 'hair': 'black-short', 'face': 'basic', 'top': 'hoodie-white',
        'bottom': 'pants-navy', 'shoes': 'sneakers-white', 'hat': 'none'}
BASE_NAKED = {'skin': 'light', 'face': 'basic'}


def make(d, sheets, outline, world=None):
    os.makedirs(d, exist_ok=True)
    table = parts_table()

    # parts_4x: 카테고리마다 한 줄. 각 파츠를 기준 몸에 얹은 front + side_idle (외곽선 적용)
    rows = []
    for cat in ('skin', 'face', 'hair', 'hat', 'top', 'bottom', 'shoes'):
        row = []
        for pid, label, fn in table[cat]:
            av = dict(BASE)
            if cat in ('top', 'bottom', 'shoes', 'hair', 'hat'):
                av[cat] = pid
            else:
                av[cat] = pid
            if cat == 'hair':
                av['top'] = 'hoodie-white'
            comp = silhouette(compose(sheets, av), outline)
            row += [frame(comp, 0), frame(comp, 1)]
        rows.append(row)
    grid(rows, 4).convert('RGB').save(os.path.join(d, 'parts_4x.png'))

    # back 뷰 목록도 (머리/모자/상의 뒷모습)
    rows = []
    for cat in ('hair', 'hat', 'top'):
        row = []
        for pid, label, fn in table[cat]:
            av = dict(BASE)
            av[cat] = pid
            comp = silhouette(compose(sheets, av), outline)
            row += [frame(comp, 6)]
        rows.append(row)
    grid(rows, 4).convert('RGB').save(os.path.join(d, 'parts_back_4x.png'))

    comps = [silhouette(compose(sheets, av), outline) for lb, av in PRESETS]
    grid([[frame(c, i) for i in range(7)] for c in comps], 6).convert('RGB').save(
        os.path.join(d, 'presets_6x.png'))

    frames = [grid([[frame(c, 2 + k) for c in comps]], 5).convert('RGB') for k in range(4)]
    frames[0].save(os.path.join(d, 'walk.gif'), save_all=True, append_images=frames[1:], duration=150, loop=0)
    grid([[frame(c, 2 + k) for k in range(4)] for c in comps], 6).convert('RGB').save(
        os.path.join(d, 'walk_frames_6x.png'))

    rng = random.Random(20261014)
    rows = []
    combos = []
    for i in range(12):
        av = {cat: rng.choice(table[cat])[0] for cat in ('skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat')}
        combos.append(av)
        c = silhouette(compose(sheets, av), outline)
        rows.append([frame(c, j) for j in (0, 1, 2, 6)])
    # 2열로 배치 (6줄 x 8칸)
    rows2 = [rows[r] + rows[r + 6] for r in range(6)]
    grid(rows2, 4).convert('RGB').save(os.path.join(d, 'random_combos.png'))

    if world is not None:
        up(world, 2).convert('RGB').save(os.path.join(d, 'world_2x.png'))
    return comps, combos
