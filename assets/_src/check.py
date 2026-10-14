"""에셋 검사: manifest <-> 파일 일치, 크기, 알파 0/255, 팔레트 밖 색 0, aliases 대상 존재,
반복 레이어 이음매, 맵 레이어 아래 끝 규칙. 사용: python3 assets/_src/check.py"""
import os, sys, json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from palette import PAL_RGB  # noqa: E402

ASSETS = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.dirname(ASSETS)

UI_SIZES = {
    'panel.png': (24, 24), 'button-primary-normal.png': (24, 24), 'button-primary-hover.png': (24, 24),
    'button-primary-pressed.png': (24, 24), 'button-primary-disabled.png': (24, 24),
    'button-secondary-normal.png': (24, 24), 'button-secondary-hover.png': (24, 24),
    'button-secondary-pressed.png': (24, 24), 'input-normal.png': (12, 12), 'input-focus.png': (12, 12),
    'input-error.png': (12, 12), 'input-disabled.png': (12, 12), 'chip.png': (8, 8), 'bubble.png': (12, 12),
    'bubble-tail.png': (8, 4), 'label-other.png': (8, 8), 'label-self.png': (8, 8),
    'icon-mushroom.png': (9, 8), 'icon-arrow.png': (4, 7),
}
MAP_SPEC = {  # file: (w, h, y, parallax, repeatX)  style-guide 6.1
    'sky.png': (16, 270, 0, 0.0, True), 'clouds.png': (480, 70, 18, 0.25, True),
    'mountains.png': (640, 110, 110, 0.2, True), 'hills.png': (640, 80, 142, 0.3, True),
    'trees.png': (640, 120, 104, 0.5, True), 'village.png': (1200, 160, 60, 1.0, False),
    'ground.png': (1200, 54, 216, 1.0, False),
}


class Report:
    def __init__(self):
        self.errors, self.notes = [], []

    def err(self, m):
        self.errors.append(m)

    def ok(self, m):
        self.notes.append(m)


def pixel_check(R, path):
    im = Image.open(path)
    if im.mode != 'RGBA':
        R.err(f'{path}: mode {im.mode} (RGBA 필요)')
        im = im.convert('RGBA')
    bad_a = bad_c = 0
    for (r, g, b, a) in im.getdata():
        if a not in (0, 255):
            bad_a += 1
        elif a == 255 and (r, g, b) not in PAL_RGB:
            bad_c += 1
    if bad_a:
        R.err(f'{path}: 반투명 픽셀 {bad_a}개')
    if bad_c:
        R.err(f'{path}: 팔레트 밖 색 {bad_c}개')
    return im


def check_avatar(R):
    man = json.load(open(os.path.join(ASSETS, 'avatar', 'manifest.json'), encoding='utf-8'))
    for k in ('frame', 'anchor', 'scale', 'layerOrder', 'animations', 'parts'):
        if k not in man:
            R.err(f'avatar manifest: {k} 없음')
    if man['frame'] != {'w': 32, 'h': 48} or man['anchor'] != {'x': 16, 'y': 46} or man['scale'] != 2:
        R.err('avatar manifest: frame/anchor/scale 값이 계약과 다름')
    if man['layerOrder'] != ['skin', 'bottom', 'top', 'eyes', 'hair']:
        R.err('avatar manifest: layerOrder')
    if man['animations'] != {'idle': {'frames': [0, 1], 'ms': 500}, 'walk': {'frames': [2, 3, 4, 5], 'ms': 120}}:
        R.err('avatar manifest: animations')
    listed = set()
    count = {p: len(v) for p, v in man['parts'].items()}
    if count != {'skin': 3, 'hair': 7, 'eyes': 4, 'top': 4, 'bottom': 4}:
        R.err(f'avatar parts 개수 {count}')
    ids = {p: {it['id'] for it in v} for p, v in man['parts'].items()}
    for part, items in man['parts'].items():
        for it in items:
            path = os.path.join(ASSETS, 'avatar', part, it['id'] + '.png')
            listed.add(os.path.normpath(path))
            if not os.path.exists(path):
                R.err(f'없음: {path}')
                continue
            im = pixel_check(R, path)
            if im.size != (192, 48):
                R.err(f'{path}: 크기 {im.size}')
            a = im.getchannel('A')
            if a.crop((0, 46, 192, 48)).getbbox():
                R.err(f'{path}: 행 46-47 불투명')
            for i in range(6):
                if not a.crop((i * 32, 0, i * 32 + 32, 48)).getbbox():
                    R.err(f'{path}: 프레임 {i} 비어 있음')
    for old, new in man.get('aliases', {}).items():
        part = new.split('-')[0]
        if new not in ids.get(part, set()):
            R.err(f'alias {old} -> {new}: 대상 없음')
        if old in ids.get(part, set()):
            R.err(f'alias {old}: 이미 목록에 있는 id')
    for d, _, fs in os.walk(os.path.join(ASSETS, 'avatar')):
        for f in fs:
            p = os.path.normpath(os.path.join(d, f))
            if f.endswith('.png') and p not in listed:
                R.err(f'manifest에 없는 파일: {p}')
            if f.endswith('.svg'):
                R.err(f'폐기된 SVG 남아 있음: {p}')
    R.ok(f'avatar: {len(listed)} sheets')


def check_map(R):
    man = json.load(open(os.path.join(ASSETS, 'map', 'manifest.json'), encoding='utf-8'))
    if man.get('scale') != 2:
        R.err('map manifest scale')
    names = [os.path.basename(L['src']) for L in man['layers']]
    if names != list(MAP_SPEC):
        R.err(f'map 레이어 순서 {names}')
    for L in man['layers']:
        fn = os.path.basename(L['src'])
        path = os.path.join(ROOT, L['src'])
        if not os.path.exists(path):
            R.err(f'없음: {path}')
            continue
        w, h, y, par, rep = MAP_SPEC[fn]
        if (L['y'], L['parallax'], L['repeatX']) != (y, par, rep):
            R.err(f'{fn}: y/parallax/repeatX 값')
        im = pixel_check(R, path)
        if im.size != (w, h):
            R.err(f'{fn}: 크기 {im.size} != {(w, h)}')
        if rep:   # 이음매: 첫 열과 마지막 열의 불투명 행 차이가 작아야 한다
            a = im.getchannel('A')
            diff = sum(1 for yy in range(h) if (a.getpixel((0, yy)) > 0) != (a.getpixel((w - 1, yy)) > 0))
            if diff > 3:
                R.err(f'{fn}: 좌우 끝 이음매 차이 {diff}행')
        if fn == 'sky.png':
            if im.getchannel('A').getextrema() != (255, 255):
                R.err('sky.png: 투명 픽셀')
        if fn == 'village.png':
            bb = im.getchannel('A').getbbox()
            if bb[3] != 160:
                R.err(f'village.png: 마지막 불투명 행 {bb[3] - 1} != 159')
        if fn == 'ground.png':
            row4 = {im.getpixel((x, 4)) for x in range(im.width)}
            if len(row4) != 1:
                R.err('ground.png: 잔디 윗면(행 4)이 한 색이 아님')
    for d, _, fs in os.walk(os.path.join(ASSETS, 'map')):
        for f in fs:
            if f.endswith('.svg'):
                R.err(f'폐기된 SVG 남아 있음: {os.path.join(d, f)}')
            if f.endswith('.png') and f not in MAP_SPEC:
                R.err(f'manifest에 없는 맵 파일: {f}')
    R.ok(f'map: {len(man["layers"])} layers')


def check_ui(R):
    man = json.load(open(os.path.join(ASSETS, 'ui', 'manifest.json'), encoding='utf-8'))
    refs = set()
    for name, n in man['nine'].items():
        srcs = [n['src']] if 'src' in n else list(n['states'].values())
        for s in srcs:
            refs.add(s)
        sl = n['slice']
        for s in srcs:
            p = os.path.join(ROOT, s)
            if not os.path.exists(p):
                R.err(f'없음: {s}')
                continue
            im = Image.open(p).convert('RGBA')
            t, r, b, l = sl
            if t + b >= im.height or l + r >= im.width:
                R.err(f'{s}: slice {sl}가 크기 {im.size}보다 큼')
                continue
            # 9-slice 가운데 단색 (늘려도 깨지지 않음)
            mid = im.crop((l, t, im.width - r, im.height - b))
            if len(set(mid.getdata())) != 1:
                R.err(f'{s}: 가운데 영역이 단색이 아님')
            # 가장자리 띠가 늘림 방향으로 균일한지 (위/아래 띠는 가로로, 좌/우 띠는 세로로)
            for box in ((l, 0, im.width - r, t), (l, im.height - b, im.width - r, im.height)):
                band = im.crop(box)
                for yy in range(band.height):
                    if len({band.getpixel((xx, yy)) for xx in range(band.width)}) != 1:
                        R.err(f'{s}: 위/아래 띠 행 {yy}가 가로로 균일하지 않음')
                        break
            for box in ((0, t, l, im.height - b), (im.width - r, t, im.width, im.height - b)):
                band = im.crop(box)
                for xx in range(band.width):
                    if len({band.getpixel((xx, yy)) for yy in range(band.height)}) != 1:
                        R.err(f'{s}: 좌/우 띠 열 {xx}가 세로로 균일하지 않음')
                        break
    for s in man['sprites'].values():
        refs.add(s)
    files = {f for f in os.listdir(os.path.join(ASSETS, 'ui')) if f.endswith('.png')}
    if files != set(UI_SIZES):
        R.err(f'ui 파일 목록 차이: 더 있음 {files - set(UI_SIZES)}, 없음 {set(UI_SIZES) - files}')
    if {os.path.basename(r) for r in refs} != set(UI_SIZES):
        R.err(f'ui manifest 참조 차이: {set(UI_SIZES) ^ {os.path.basename(r) for r in refs}}')
    for f in sorted(files):
        im = pixel_check(R, os.path.join(ASSETS, 'ui', f))
        if f in UI_SIZES and im.size != UI_SIZES[f]:
            R.err(f'{f}: 크기 {im.size} != {UI_SIZES[f]}')
    R.ok(f'ui: {len(files)} files')


def run(verbose=True):
    R = Report()
    for fn in (check_avatar, check_map, check_ui):
        try:
            fn(R)
        except FileNotFoundError as e:
            R.err(f'{fn.__name__}: {e}')
    if verbose:
        for n in R.notes:
            print('  ok   ', n)
        for e in R.errors:
            print('  FAIL ', e)
    return not R.errors


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
