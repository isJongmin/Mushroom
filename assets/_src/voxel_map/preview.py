"""미리보기: map_full.png(전체 합성 축소), view_desktop.png(1280x540 P=2 화면 3곳), with_char.png(캐릭터 샘플).

python3 assets/_src/voxel_map/preview.py OUTDIR [CHAR_DIR]
CHAR_DIR: 96x128 프레임 8개짜리 캐릭터 시트 PNG 폴더 (기준점 (48,120), 1px = 월드 1단위).
"""
import os, sys, json
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def load():
    man = json.load(open(os.path.join(ROOT, 'assets', 'map', 'manifest.json')))
    D = man['density']
    layers = []
    for l in man['layers']:
        im = Image.open(os.path.join(ROOT, l['src'])).convert('RGBA')
        layers.append((l, im))
    return man, layers


def world_scaled(im, k):
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def compose(man, layers, camx, vw, vh=540, k=1.0, parallax=True):
    """월드 단위 화면(vw x vh)을 배율 k(화면 px / 월드 단위)로 합성."""
    D = man['density']
    out = Image.new('RGBA', (round(vw * k), round(vh * k)), (0, 0, 0, 255))
    for l, im in layers:
        s = k / D
        if l.get('stretchX'):
            sim = im.resize((out.width, round(im.height * s)), Image.BILINEAR)
            out.alpha_composite(sim, (0, round(l['y'] * k)))
            continue
        sim = world_scaled(im, s)
        par = l['parallax'] if parallax else 1.0
        ox = -int(camx * par) * k
        y = round(l['y'] * k)
        if l['repeatX']:
            w = sim.width
            x = int(ox % w) - w
            while x < out.width:
                c, px = (sim.crop((-x, 0, w, sim.height)), 0) if x < 0 else (sim, x)
                c = c.crop((0, 0, min(c.width, out.width - px), c.height))
                if c.width > 0:
                    out.alpha_composite(c, (px, y))
                x += w
        else:
            x = int(ox)
            if x < 0:
                c = sim.crop((-x, 0, sim.width, sim.height)); x = 0
            else:
                c = sim
            c = c.crop((0, 0, min(c.width, out.width - x), c.height))
            if c.width > 0:
                out.alpha_composite(c, (x, y))
    return out


def chars(char_dir):
    if not char_dir or not os.path.isdir(char_dir):
        return []
    out = []
    for f in sorted(os.listdir(char_dir)):
        if f.endswith('.png'):
            out.append(Image.open(os.path.join(char_dir, f)).convert('RGBA'))
    return out


def put_char(img, sheet, frame, wx, k, flip=False):
    fr = sheet.crop((96 * frame, 0, 96 * frame + 96, 128))
    if flip:
        fr = fr.transpose(Image.FLIP_LEFT_RIGHT)
    fr = fr.resize((round(96 * k), round(128 * k)), Image.LANCZOS)
    # 발 그림자
    sh = Image.new('RGBA', (round(30 * k), round(6 * k)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(40, 30, 50, 70))
    img.alpha_composite(sh, (round((wx - 15) * k), round((440 - 3) * k)))
    img.alpha_composite(fr, (round((wx - 48) * k), round((440 - 120) * k)))


def main(outdir, char_dir=None):
    os.makedirs(outdir, exist_ok=True)
    man, layers = load()
    full = compose(man, layers, 0, man['width'], k=0.5, parallax=False)
    full.convert('RGB').save(os.path.join(outdir, 'map_full.png'))
    cams = (0, 560, 1120)
    views = [compose(man, layers, c, 1280, k=1.0) for c in cams]
    vd = Image.new('RGBA', (1280, 540 * 3 + 16), (20, 18, 30, 255))
    for i, v in enumerate(views):
        vd.alpha_composite(v, (0, i * 548))
    vd.convert('RGB').save(os.path.join(outdir, 'view_desktop.png'))
    sheets = chars(char_dir)
    if sheets:
        wc = Image.new('RGBA', (1280, 540 * 2 + 8), (20, 18, 30, 255))
        for i, cam in enumerate((560, 0)):
            v = compose(man, layers, cam, 1280, k=1.0)
            xs = (180, 420, 640, 860, 1080, 300, 980) if i == 0 else (90, 330, 560, 760, 1010, 1180)
            for j, x in enumerate(xs):
                s = sheets[j % len(sheets)]
                put_char(v, s, (0, 2, 3, 2, 0, 5, 2)[j % 7], x, 1.0, flip=(j % 3 == 1))
            wc.alpha_composite(v, (0, i * 548))
        wc.convert('RGB').save(os.path.join(outdir, 'with_char.png'))
        # P=3 (1.5배) 확대 크롭: 에셋 1:1
        v3 = compose(man, layers, 560, 853, k=1.5)
        for j, x in enumerate((150, 330, 520, 700)):
            put_char(v3, sheets[j % len(sheets)], (0, 2, 4, 0)[j], x, 1.5, flip=(j == 1))
        v3.convert('RGB').save(os.path.join(outdir, 'with_char_p3.png'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
