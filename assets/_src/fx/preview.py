"""미리보기: python3 assets/_src/fx/preview.py OUT_DIR
icons.png(1x/3x, 밝은/어두운 배경), orbs.png, slashes.png (밝은/어두운 배경, 3x)."""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FX = os.path.join(ROOT, 'assets', 'fx')
import spec  # noqa: E402

LIGHT, DARK = (236, 224, 206, 255), (44, 48, 68, 255)


def on(bg, im, scale):
    w, h = im.size
    b = Image.new('RGBA', (w, h), bg)
    b.alpha_composite(im)
    return b.resize((w * scale, h * scale), Image.NEAREST) if scale != 1 else b


def row(ims, pad=8, bg=(128, 128, 128, 255)):
    W = sum(i.width for i in ims) + pad * (len(ims) + 1)
    H = max(i.height for i in ims) + pad * 2
    out = Image.new('RGBA', (W, H), bg)
    x = pad
    for i in ims:
        out.paste(i, (x, pad))
        x += i.width + pad
    return out


def col(rows, bg=(128, 128, 128, 255)):
    W = max(r.width for r in rows)
    out = Image.new('RGBA', (W, sum(r.height for r in rows)), bg)
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    return out


def main(out):
    os.makedirs(out, exist_ok=True)
    icons = [Image.open(os.path.join(FX, 'buff', f'{b}.png')).convert('RGBA') for b in spec.ITEMS]
    small = [i.resize((36, 36), Image.LANCZOS) for i in icons]
    col([row([on(LIGHT, i, 1) for i in icons] + [on(LIGHT, s, 1) for s in small]),
         row([on(DARK, i, 1) for i in icons] + [on(DARK, s, 1) for s in small]),
         row([on(LIGHT, i, 3) for i in icons[:3]]), row([on(LIGHT, i, 3) for i in icons[3:]]),
         row([on(DARK, i, 3) for i in icons[:3]]), row([on(DARK, i, 3) for i in icons[3:]])]).save(
        os.path.join(out, 'icons.png'))
    orb = Image.open(os.path.join(FX, 'buff_orb.png')).convert('RGBA')
    col([row([on(LIGHT, orb, 1), on(DARK, orb, 1)]), row([on(LIGHT, orb, 3)]), row([on(DARK, orb, 3)])]).save(
        os.path.join(out, 'orbs.png'))
    for bgn, bg in (('light', LIGHT), ('dark', DARK)):
        rows = [row([on(bg, Image.open(os.path.join(FX, f)).convert('RGBA'), 2)])
                for f in ('slash.png', 'slash_fire.png', 'slash_ice.png', 'slash_bolt.png')]
        col(rows).save(os.path.join(out, f'slashes_{bgn}.png'))


if __name__ == '__main__':
    main(sys.argv[1])
