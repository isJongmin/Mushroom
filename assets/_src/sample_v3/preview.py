"""Preview renders for sample_v3 (writes into a scratch dir given as argv[1])."""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
W, H = 80, 96
FRAMES = ['front', 'side_idle', 'side_walk0', 'side_walk1', 'side_walk2',
          'side_walk3', 'back']
PINK = (0xF8, 0xEE, 0xF2, 255)


def up(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def main(dst):
    os.makedirs(dst, exist_ok=True)
    fr = {n: Image.open(os.path.join(OUT, f'{n}.png')).convert('RGBA') for n in FRAMES}

    # sheet_6x
    sheet = Image.open(os.path.join(OUT, 'sheet.png')).convert('RGBA')
    bg = Image.new('RGBA', sheet.size, PINK)
    bg.alpha_composite(sheet)
    up(bg, 6).save(os.path.join(dst, 'sheet_6x.png'))

    # compare: reference (as given, 2x of the source) vs ours at 3x
    ref = Image.open(os.path.join(dst, 'ref_hoodie_boy.png')).convert('RGBA')
    k = 3
    ours = Image.new('RGBA', (W * k * 3, H * k), PINK)
    for i, n in enumerate(['front', 'side_idle', 'back']):
        im = fr[n]
        if n == 'side_idle':
            im = im.transpose(Image.FLIP_LEFT_RIGHT)  # ref side faces left
        ours.alpha_composite(up(im, k), (i * W * k, 0))
    cw = ref.width + ours.width + 20
    ch = max(ref.height, ours.height)
    comp = Image.new('RGBA', (cw, ch), PINK)
    comp.alpha_composite(ref, (0, (ch - ref.height) // 2))
    comp.alpha_composite(ours, (ref.width + 20, (ch - ours.height) // 2))
    comp.save(os.path.join(dst, 'compare.png'))

    # walk.gif
    gif = []
    for n in ['side_walk0', 'side_walk1', 'side_walk2', 'side_walk3']:
        b = Image.new('RGBA', (W, H), PINK)
        b.alpha_composite(fr[n])
        gif.append(up(b, 6).convert('RGB').quantize(colors=64, dither=Image.Dither.NONE))
    gif[0].save(os.path.join(dst, 'walk.gif'), save_all=True, append_images=gif[1:],
                duration=150, loop=0, disposal=2)

    # ingame: world crop at 2x, characters at 2x, feet on the ground line (y=220)
    world = Image.open(os.path.join(REPO, 'docs/design/ref/world-1x.png')).convert('RGBA')
    crop = world.crop((60, 70, 460, 270))  # 400 x 200
    ground = 220 - 70
    for i, n in enumerate(['front', 'side_walk0', 'back']):
        x = 40 + i * 110 if i else 30
        crop.alpha_composite(fr[n], (x + (0 if i == 0 else 0), ground - 92 - 1 + 1))
    up(crop, 2).save(os.path.join(dst, 'ingame.png'))


if __name__ == '__main__':
    main(sys.argv[1])
