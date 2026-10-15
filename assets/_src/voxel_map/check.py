"""버섯마을 복셀 맵 검사: manifest-파일 일치, 크기, 용량, (선택) 결정성.

python3 assets/_src/voxel_map/check.py            # 정적 검사
python3 assets/_src/voxel_map/check.py --determinism   # 같은 레이어를 두 번 렌더해 바이트 비교 (clouds, sky + 지면 타일 1개)
"""
import os, sys, json, hashlib, argparse
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MAP = os.path.join(ROOT, 'assets', 'map')
LIMIT = 6 * 1024 * 1024

errors = []


def err(m):
    errors.append(m); print('FAIL', m)


def static():
    man = json.load(open(os.path.join(MAP, 'manifest.json'), encoding='utf-8'))
    D = man.get('density')
    if D != 1.5: err('density %r != 1.5' % D)
    if man.get('groundY') != 440: err('groundY != 440')
    if man.get('width') != 2400: err('width != 2400')
    files = set(os.listdir(MAP)) - {'manifest.json'}
    used = set()
    total = os.path.getsize(os.path.join(MAP, 'manifest.json'))
    ground = None
    for l in man['layers']:
        src = l['src']
        if not src.startswith('assets/map/'): err('src 경로 %s' % src)
        fn = src[len('assets/map/'):]
        used.add(fn)
        p = os.path.join(MAP, fn)
        if not os.path.exists(p):
            err('없는 파일 %s' % fn); continue
        if os.path.splitext(fn)[1] not in ('.png', '.webp'): err('형식 %s' % fn)
        im = Image.open(p)
        sz = os.path.getsize(p); total += sz
        for k in ('parallax', 'y', 'repeatX'):
            if k not in l: err('%s: %s 없음' % (fn, k))
        if not 0 <= l['parallax'] <= 1: err('%s parallax 범위' % fn)
        if 'w' in l and abs(l['w'] - im.width / D) > 0.01: err('%s w 불일치' % fn)
        if 'h' in l and abs(l['h'] - im.height / D) > 0.01: err('%s h 불일치' % fn)
        if im.mode != 'RGBA': err('%s RGBA 아님 (%s)' % (fn, im.mode))
        bottom = l['y'] + im.height / D
        if bottom > 540 + 0.01: err('%s 아래가 월드 540 밖 (%.1f)' % (fn, bottom))
        if l['parallax'] == 1 and not l['repeatX']:
            ground = (l, im)
        print('%-14s %5dx%-4d  y=%-4s 월드 %.0fx%.0f  parallax=%-5s repeatX=%-5s stretchX=%-5s %7.1f KB' % (
            fn, im.width, im.height, l['y'], im.width / D, im.height / D, l['parallax'], l['repeatX'],
            l.get('stretchX', False), sz / 1024))
    if files - used: err('manifest에 없는 파일: %s' % sorted(files - used))
    if ground is None:
        err('지면 레이어(parallax 1, repeatX false) 없음')
    else:
        l, im = ground
        if im.width != 3600: err('지면 너비 %d != 3600' % im.width)
        if man['layers'][-1] is not l: err('지면 레이어가 마지막이 아님')
        # 지면선: 걷는 선(y=440)에서 잔디 윗면이 불투명해야 한다
        a = np.asarray(im)[..., 3]
        row = int(round((440 - l['y']) * D))
        if a[row].min() < 255: err('지면선 행이 완전 불투명하지 않음')
        if a[-1].min() < 255: err('지면 맨 아래 행 투명')
    # 반복 레이어 이음매: 좌우 끝 열 차이
    for l in man['layers']:
        if l['repeatX']:
            a = np.asarray(Image.open(os.path.join(ROOT, l['src'])).convert('RGBA')).astype(float)
            a[..., :3] *= a[..., 3:4] / 255.0      # 프리멀티플라이 (투명 픽셀의 RGB 는 의미 없음)
            d = np.abs(a[:, 0] - a[:, -1]).mean()
            adj = np.abs(np.diff(a, axis=1)).mean((0, 2))      # 이웃 열 쌍마다 평균 차
            p99 = float(np.percentile(adj, 99))
            print('  이음매 %-12s 끝-처음 열 차 %.2f (이웃 열 차 99%%: %.2f)' % (os.path.basename(l['src']), d, p99))
            if d > p99 * 1.5 + 1: err('%s 반복 이음매가 튐 %.1f' % (l['src'], d))
    print('합계 %.1f KB (한도 %d KB)' % (total / 1024, LIMIT // 1024))
    if total > LIMIT: err('용량 초과')


def determinism():
    import build
    from vox import render_tiled
    h = []
    for rep in range(2):
        s = build.spec('clouds')
        boxes = build.wrap_boxes(s['boxes'], s['period'] / s['scale'])
        rgba, em, ec = render_tiled(boxes, 0.0, build.PITCH, s['scale'], s['cfg'], W=600, H=s['H'], anchor=s['anchor'],
                                    tile=300)
        g = build.spec('ground')
        rg, _, _ = render_tiled(g['boxes'], 0.0, build.PITCH, g['scale'], g['cfg'], W=200, H=g['H'], anchor=g['anchor'],
                                tile=200)
        sky = np.asarray(build.spec('sky')['image'])
        h.append(hashlib.md5(rgba.tobytes() + rg.tobytes() + sky.tobytes()).hexdigest())
    print('결정성 md5', h)
    if h[0] != h[1]: err('결정성 실패')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--determinism', action='store_true')
    a = ap.parse_args()
    static()
    if a.determinism:
        determinism()
    print('OK' if not errors else '%d 문제' % len(errors))
    sys.exit(1 if errors else 0)
