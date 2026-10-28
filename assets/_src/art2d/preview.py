"""미리보기 시트 (납품 PNG를 프런트와 같은 규칙으로 합성).

python3 assets/_src/art2d/preview.py [아바타 폴더 (기본 out/avatar)] [출력 폴더 (기본 out/preview)]
"""
import os
import sys
import json
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import compose_sheet, PRESETS, OUT, KEYS  # noqa: E402
from rig import FRAMES  # noqa: E402

FW, FH = 144, 192
DROP_SETS = [
    ('달팽이 세트', dict(skin='light', face='smile', hair='sky-bob', hat='snail-shell', top='slime-hood', bottom='slime-pants', shoes='snail-boots')),
    ('주황버섯 세트', dict(skin='medium', face='basic', hair='brown-short', hat='mushroom-cap', top='golem-armor', bottom='mushroom-shorts', shoes='bat-boots')),
    ('박쥐 세트', dict(skin='dark', face='wink', hair='black-twintail', hat='golem-helm', top='bat-cape', bottom='pants-black', shoes='bat-boots')),
    ('섞어 입기', dict(skin='light', face='sleepy', hair='mint-curly', hat='none', top='bat-cape', bottom='mushroom-shorts', shoes='snail-boots')),
]


def grid(av_dir, files, rows, frames, z=2, crop=(0, 16, 144, 190), label=True):
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]
    W = Image.new('RGBA', (cw * len(frames), ch * len(rows)), (255, 255, 255, 255))
    for r, av in enumerate(rows):
        sh = compose_sheet(av_dir, av, files)
        for i, f in enumerate(frames):
            fi = FRAMES.index(f)
            im = sh.crop((FW * fi + crop[0], crop[1], FW * fi + crop[2], crop[3]))
            bg = Image.new('RGBA', im.size, (206, 228, 246, 255) if (r + i) % 2 == 0 else (220, 238, 250, 255))
            d = ImageDraw.Draw(bg)
            gy = 180 - crop[1]
            d.rectangle((0, gy, cw, ch), fill=(178, 214, 140, 255))
            bg.alpha_composite(im)
            W.paste(bg, (cw * i, ch * r))
    return W.resize((W.width * z, W.height * z), Image.LANCZOS)


def icons(av_dir, m, z=2):
    items = [(k, p['id'], p.get('drop')) for k in KEYS for p in m['parts'][k] if p['id'] != 'none']
    n = 13
    rows = (len(items) + n - 1) // n
    W = Image.new('RGBA', (n * 68, rows * 68), (255, 255, 255, 255))
    for i, (k, pid, drop) in enumerate(items):
        x, y = (i % n) * 68, (i // n) * 68
        bg = Image.new('RGBA', (68, 68), (255, 236, 200, 255) if drop else (232, 240, 248, 255))
        ic = Image.open(os.path.join(av_dir, 'icon', k, pid + '.png'))
        bg.alpha_composite(ic, (2, 2))
        W.paste(bg, (x, y))
    return W.resize((W.width * z, W.height * z), Image.LANCZOS)


def main(av_dir=None, out=None):
    av_dir = av_dir or os.path.join(OUT, 'avatar')
    out = out or os.path.join(OUT, 'preview')
    os.makedirs(out, exist_ok=True)
    m = json.load(open(os.path.join(av_dir, 'manifest.json'), encoding='utf-8'))
    files = m['files']
    pres = [av for lb, av in PRESETS]
    grid(av_dir, files, pres, ['front', 'front_b', 'side', 'back', 'walk0', 'walk1', 'walk2', 'walk3'], z=2).save(os.path.join(out, 'presets_a.png'))
    grid(av_dir, files, pres, ['jump', 'fall', 'prone', 'attack0', 'attack1'], z=2, crop=(0, 16, 144, 190)).save(os.path.join(out, 'presets_b.png'))
    grid(av_dir, files, [av for lb, av in DROP_SETS], ['front', 'side', 'back', 'walk0', 'jump', 'prone', 'attack1'], z=2).save(os.path.join(out, 'drops.png'))
    grid(av_dir, files, pres[:4], ['front', 'side'], z=4, crop=(16, 20, 128, 186)).save(os.path.join(out, 'closeup.png'))
    icons(av_dir, m).save(os.path.join(out, 'icons.png'))
    print('preview ->', out)


if __name__ == '__main__':
    main(*(sys.argv[1:3]))
