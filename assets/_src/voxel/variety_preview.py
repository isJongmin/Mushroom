"""Reproducible layer-composited contact sheets for the additive wardrobe."""
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import build as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'variety')
NAMES = ['Lavender hoodie', 'Cream cardigan', 'Navy varsity', 'Mint puffer', 'Pink blouse', 'Mushroom explorer',
         'Burgundy crop', 'Copper garden', 'Silver street', 'Mint day', 'Sage stroll', 'Twin ribbon']
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def gallery(sheets, indices, path):
    rows = (len(indices) + 5) // 6
    im = Image.new('RGBA', (6 * 288, rows * 440), '#F4EDE0')
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 18)
    small = ImageFont.truetype(FONT, 13)
    for cell, i in enumerate(indices):
        av = B.PRESETS[i][1]
        raw = B.composite(sheets, av)
        x, y = cell % 6 * 288, cell // 6 * 440
        sprite = Image.fromarray(raw[:, :144]).resize((288, 384), Image.Resampling.NEAREST)
        im.alpha_composite(sprite, (x, y))
        d.text((x + 12, y + 394), '%02d  %s' % (i + 1, NAMES[i]), font=font, fill='#493B35')
        d.text((x + 12, y + 420), '%s / %s' % (av['skin'], av['face']), font=small, fill='#786C5F')
    im.convert('RGB').save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    sheets = B.load_sheets(os.path.join(B.ROOT, 'assets', 'avatar'))
    gallery(sheets, list(range(6, 12)), os.path.join(OUT, 'additional6-front.png'))
    gallery(sheets, list(range(12)), os.path.join(OUT, 'all12-front.png'))
    im = Image.new('RGBA', (1872, 6 * 216), '#F4EDE0')
    d = ImageDraw.Draw(im)
    for i, (_, av) in enumerate(B.PRESETS[6:]):
        im.alpha_composite(Image.fromarray(B.composite(sheets, av)), (0, i * 216))
        d.text((12, i * 216 + 196), '%02d %s' % (i + 7, NAMES[i + 6]), fill='#493B35')
    im.convert('RGB').save(os.path.join(OUT, 'additional6-all13poses.png'))
    print(OUT)


if __name__ == '__main__':
    main()
