"""검증용 확대 미리보기 (빌드 산출물이 아님). 사용: python3 assets/_src/preview.py <출력 폴더>
생성된 PNG(assets/)만 읽어서 합성한다 = 프런트가 보게 될 결과와 같다."""
import os, sys, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import rgba

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
A = os.path.join(ROOT, 'assets')
W, H = 32, 48

COMBOS = [
    dict(skin='skin-light', hair='hair-round-black', eyes='eyes-dot', top='top-tee-red', bottom='bottom-shorts-navy'),
    dict(skin='skin-tan', hair='hair-spiky-chestnut', eyes='eyes-happy', top='top-hoodie-blue', bottom='bottom-jeans-blue'),
    dict(skin='skin-dark', hair='hair-long-pink', eyes='eyes-sparkle', top='top-overalls-blue', bottom='bottom-skirt-pink'),
    dict(skin='skin-light', hair='hair-spiky-mint', eyes='eyes-sleepy', top='top-cape-mushroom', bottom='bottom-pumpkin-green'),
    dict(skin='skin-tan', hair='hair-long-blonde', eyes='eyes-dot', top='top-tee-red', bottom='bottom-skirt-pink'),
    dict(skin='skin-dark', hair='hair-round-chestnut', eyes='eyes-happy', top='top-hoodie-blue', bottom='bottom-shorts-navy'),
]
ORDER = ['skin', 'bottom', 'top', 'eyes', 'hair']


def sheet(av):
    s = Image.new('RGBA', (W * 6, H), (0, 0, 0, 0))
    for part in ORDER:
        s.alpha_composite(Image.open(os.path.join(A, 'avatar', part, av[part] + '.png')).convert('RGBA'))
    return s


def frame(av, i, flip=False):
    f = sheet(av).crop((i * W, 0, i * W + W, H))
    return f.transpose(Image.FLIP_LEFT_RIGHT) if flip else f


def avatars(out, Z=8, flip=False):
    pad = 4
    big = Image.new('RGBA', ((W * Z + pad * Z) * 6, (H * Z + pad * Z) * len(COMBOS)), rgba('k4'))
    d = ImageDraw.Draw(big)
    for r, av in enumerate(COMBOS):
        for i in range(6):
            fr = frame(av, i, flip)
            ox, oy = i * (W + pad) * Z + pad * Z // 2, r * (H + pad) * Z + pad * Z // 2
            # 발 그림자 (style-guide 4.5)
            for (x0, x1, y) in ((10, 21, 46), (11, 20, 47)):
                d.rectangle([ox + x0 * Z, oy + y * Z, ox + (x1 + 1) * Z - 1, oy + (y + 1) * Z - 1], fill=rgba('g3'))
            big.alpha_composite(fr.resize((W * Z, H * Z), Image.NEAREST), (ox, oy))
            # 기준점 (16,46)
            d.line([ox + 16 * Z, oy + 44 * Z, ox + 16 * Z, oy + 48 * Z - 1], fill=(255, 0, 160, 255))
    big.save(os.path.join(out, 'avatars-flip-8x.png' if flip else 'avatars-8x.png'))


def all_parts(out, Z=4):
    """22개 파츠 시트를 단독으로 나열 (각 시트 192x48)."""
    man = json.load(open(os.path.join(A, 'avatar', 'manifest.json'), encoding='utf-8'))
    rows = [(p, it['id']) for p in ORDER for it in man['parts'][p]]
    big = Image.new('RGBA', (192 * Z + 8, (48 * Z + 4) * len(rows)), rgba('k5'))
    for i, (p, pid) in enumerate(rows):
        im = Image.open(os.path.join(A, 'avatar', p, pid + '.png')).convert('RGBA')
        big.alpha_composite(im.resize((192 * Z, 48 * Z), Image.NEAREST), (4, i * (48 * Z + 4)))
    big.save(os.path.join(out, 'parts-all-4x.png'))


def walk_gif(out, Z=6):
    frames = []
    seq = [2, 3, 4, 5] * 3 + [0, 0, 0, 0, 1, 1, 1, 1]
    for i in seq:
        im = Image.new('RGBA', (W * Z * len(COMBOS), H * Z), rgba('k5'))
        for c, av in enumerate(COMBOS):
            im.alpha_composite(frame(av, i).resize((W * Z, H * Z), Image.NEAREST), (c * W * Z, 0))
        frames.append(im.convert('RGB').quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
    ms = [120 if i >= 2 else 500 // 4 * 1 for i in seq]
    frames[0].save(os.path.join(out, 'walk.gif'), save_all=True, append_images=frames[1:], duration=ms, loop=0)
    # 프레임 스트립: walk0..3 반복 + 위치 이동(초당 80px, 120ms -> 약 10px)
    strip = Image.new('RGBA', ((W + 10 * 8) * 1 + 10 * 8 + W, H), rgba('k5'))
    Z2 = 6
    strip = Image.new('RGBA', ((34 * 8 + 6) * Z2, (H + 2) * Z2 * 2), rgba('k5'))
    for r, av in enumerate(COMBOS[:2]):
        for k in range(8):
            fr = frame(av, 2 + k % 4)
            strip.alpha_composite(fr.resize((W * Z2, H * Z2), Image.NEAREST), ((4 + k * 34) * Z2, r * (H + 2) * Z2))
    strip.save(os.path.join(out, 'walk-strip-6x.png'))


def map_layers():
    return json.load(open(os.path.join(A, 'map', 'manifest.json'), encoding='utf-8'))


def render_world(camX=0, vw=1200, vh=270, camY=0):
    man = map_layers()
    view = Image.new('RGBA', (vw, vh), rgba('k1'))
    for L in man['layers']:
        im = Image.open(os.path.join(ROOT, L['src'])).convert('RGBA')
        ox = -int(camX * L['parallax'] // 1)
        y = L['y'] - camY
        if L['repeatX']:
            x = ox % im.width - im.width
            while x < vw:
                view.alpha_composite(im, (x, y)) if y >= 0 else view.paste(im, (x, y), im)
                x += im.width
        else:
            view.alpha_composite(im, (ox, y)) if ox >= 0 else view.paste(im, (ox, y), im)
    return view


def world(out):
    v = render_world()
    spots = [(130 + 60, 0, 0, False), (400, 1, 2, False), (560, 2, 4, True), (700, 3, 0, True), (960, 4, 3, False), (1120, 5, 1, True)]
    for (x, c, fi, flip) in spots:
        for (x0, x1, y) in ((x - 6, x + 5, 220), (x - 5, x + 4, 221)):
            for xx in range(x0, x1 + 1):
                v.putpixel((xx, y), rgba('g3'))
        v.alpha_composite(frame(COMBOS[c], fi, flip), (x - 16, 220 - 46))
    v.resize((2400, 540), Image.NEAREST).save(os.path.join(out, 'world-2x.png'))
    # 부분 확대 (마을 x 60-460)
    v.crop((60, 90, 520, 270)).resize((460 * 4, 180 * 4), Image.NEAREST).save(os.path.join(out, 'world-crop-4x.png'))
    v.crop((560, 90, 1200, 270)).resize((640 * 3, 180 * 3), Image.NEAREST).save(os.path.join(out, 'world-crop2-3x.png'))
    # 이음매 확인: 반복 레이어를 두 장 이어 붙이고 경계 부분 확대
    man = map_layers()
    seams = []
    for L in man['layers']:
        if not L['repeatX']:
            continue
        im = Image.open(os.path.join(ROOT, L['src'])).convert('RGBA')
        two = Image.new('RGBA', (im.width * 2, im.height), rgba('k3'))
        two.alpha_composite(im, (0, 0)); two.alpha_composite(im, (im.width, 0))
        cx = im.width
        seams.append(two.crop((max(0, cx - 60), 0, cx + 60, im.height)))
    hh = sum(s.height for s in seams) + 4 * len(seams)
    sheet_ = Image.new('RGBA', (120, hh), (255, 0, 160, 255))
    y = 0
    for s in seams:
        sheet_.alpha_composite(s, ((120 - s.width) // 2, y)); y += s.height + 4
    sheet_.resize((120 * 4, hh * 4), Image.NEAREST).save(os.path.join(out, 'seams-4x.png'))


def nine(img, sl, w, h):
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    iw, ih = img.size
    t, r, b, l = sl
    xs = [(0, l, 0, l), (l, iw - r, l, w - r), (iw - r, iw, w - r, w)]
    ys = [(0, t, 0, t), (t, ih - b, t, h - b), (ih - b, ih, h - b, h)]
    for (sx0, sx1, dx0, dx1) in xs:
        for (sy0, sy1, dy0, dy1) in ys:
            if dx1 > dx0 and dy1 > dy0 and sx1 > sx0 and sy1 > sy0:
                out.alpha_composite(img.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.NEAREST), (dx0, dy0))
    return out


def ui(out, Z=8):
    man = json.load(open(os.path.join(A, 'ui', 'manifest.json'), encoding='utf-8'))
    files = sorted(f for f in os.listdir(os.path.join(A, 'ui')) if f.endswith('.png'))
    cols = 5
    cell = 26 * Z
    big = Image.new('RGBA', (cols * (cell + 16), ((len(files) + cols - 1) // cols) * (cell + 16) + 2 * 0), (190, 190, 200, 255))
    for i, fn in enumerate(files):
        im = Image.open(os.path.join(A, 'ui', fn)).convert('RGBA')
        big.alpha_composite(im.resize((im.width * Z, im.height * Z), Image.NEAREST),
                            ((i % cols) * (cell + 16) + 8, (i // cols) * (cell + 16) + 8))
    big.save(os.path.join(out, 'ui-8x.png'))
    # 9-slice 늘림 확인 (아트 px 기준으로 합성 후 2배 = U)
    canvas = Image.new('RGBA', (260, 180), rgba('k3'))
    nn = man['nine']
    def ld(p): return Image.open(os.path.join(ROOT, p)).convert('RGBA')
    canvas.alpha_composite(nine(ld(nn['panel']['src']), nn['panel']['slice'], 120, 140), (4, 4))
    y = 4
    for st in ('normal', 'hover', 'pressed', 'disabled'):
        canvas.alpha_composite(nine(ld(nn['button-primary']['states'][st]), nn['button-primary']['slice'], 60, 24), (130, y))
        canvas.alpha_composite(nine(ld(nn['button-secondary']['states'][st]), nn['button-secondary']['slice'], 60, 24), (194, y))
        y += 28
    canvas.alpha_composite(nine(ld(nn['input']['states']['normal']), [4, 4, 4, 4], 100, 22), (14, 20))
    canvas.alpha_composite(nine(ld(nn['input']['states']['focus']), [4, 4, 4, 4], 100, 22), (14, 46))
    canvas.alpha_composite(nine(ld(nn['input']['states']['error']), [4, 4, 4, 4], 100, 22), (14, 72))
    canvas.alpha_composite(nine(ld(nn['input']['states']['disabled']), [4, 4, 4, 4], 100, 22), (14, 98))
    canvas.alpha_composite(nine(ld(nn['chip']['src']), [3, 3, 3, 3], 40, 14), (130, 120))
    canvas.alpha_composite(ld(man['sprites']['icon-mushroom']), (133, 123))
    canvas.alpha_composite(nine(ld(nn['label-other']['src']), [3, 3, 3, 3], 30, 10), (176, 118))
    canvas.alpha_composite(nine(ld(nn['label-self']['src']), [3, 3, 3, 3], 30, 10), (210, 118))
    canvas.alpha_composite(nine(ld(nn['bubble']['src']), [4, 4, 4, 4], 50, 16), (190, 150))
    canvas.alpha_composite(ld(man['sprites']['bubble-tail']), (211, 165))
    canvas.alpha_composite(ld(man['sprites']['icon-arrow']), (150, 150))
    canvas.resize((260 * 4, 180 * 4), Image.NEAREST).save(os.path.join(out, 'ui-nine-4x.png'))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    what = sys.argv[2:] or ['avatar', 'map', 'ui']
    if 'avatar' in what:
        avatars(out); avatars(out, flip=True); all_parts(out); walk_gif(out)
    if 'map' in what:
        world(out)
    if 'ui' in what:
        ui(out)
    print('preview ->', out)
