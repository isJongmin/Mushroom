"""버섯마을 복셀 맵 검사: manifest-파일 일치, 크기, 용량, 발판(사이클 8), (선택) 결정성.

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


JUMP = 105        # 일반 점프 최고 높이 (ARCHITECTURE 사이클 6)
SUPER = 225       # 슈퍼 점프 최고 높이 (사이클 8)


def platforms_check(render_mask=True):
    """manifest platforms: 형식/범위/층 간격 + 그림 윗면 일치(샘플)."""
    man = json.load(open(os.path.join(MAP, 'manifest.json'), encoding='utf-8'))
    pl = man.get('platforms')
    if not isinstance(pl, list) or not pl:
        err('platforms 없음'); return
    import platforms as PLM
    src = [dict(id=p['id'], x1=p['x1'], x2=p['x2'], y=p['y']) for p in PLM.PLATFORMS]
    if pl != src: err('manifest platforms 가 platforms.py 정본과 다름')
    ids = set()
    for p in pl:
        if set(p) != {'id', 'x1', 'x2', 'y'}: err('%s 키 %s' % (p.get('id'), sorted(p)))
        if p['id'] in ids: err('id 중복 %s' % p['id'])
        ids.add(p['id'])
        if not (0 <= p['x1'] < p['x2'] <= man['width']): err('%s x 범위' % p['id'])
        if not (60 <= p['y'] < man['groundY']): err('%s y 범위 %s' % (p['id'], p['y']))
        if p['x2'] - p['x1'] < 80: err('%s 너비 %d < 80' % (p['id'], p['x2'] - p['x1']))
    normal = [p for p in pl if not p['id'].startswith('secret')]
    secret = [p for p in pl if p['id'].startswith('secret')]
    tiers = sorted({p['y'] for p in normal}, reverse=True)
    levels = [man['groundY']] + tiers
    gaps = [levels[i] - levels[i + 1] for i in range(len(levels) - 1)]
    print('발판 %d개 (일반 %d, 비밀 %d), 층 y %s, 간격 %s' % (len(pl), len(normal), len(secret), tiers, gaps))
    if len(tiers) < 3: err('일반 발판 층 < 3')
    if any(not 85 <= g <= 95 for g in gaps): err('층 간격이 85~95 밖: %s' % gaps)
    if min(tiers) > 170: err('가장 높은 일반 층 y > 170')
    if not 6 <= len(pl) <= 10: err('발판 수 %d (6~10)' % len(pl))
    # 일반 발판: 바로 아래 층(지면 포함)에서 일반 점프로 닿는지 (가로 거리 <= 70)
    def hgap(a, b):
        return max(0, max(a['x1'], b['x1']) - min(a['x2'], b['x2']))
    for p in normal:
        below = [q for q in normal if 0 < q['y'] - p['y'] <= JUMP - 10]
        if p['y'] + JUMP - 10 >= man['groundY']:
            continue
        if not any(hgap(p, q) <= 70 for q in below): err('%s: 아래 층에서 일반 점프로 닿지 않음' % p['id'])
    # 비밀 발판: 일반 점프로는 못 닿고 슈퍼 점프로는 닿아야 한다
    for p in secret:
        easy = [q for q in normal if 0 < q['y'] - p['y'] <= JUMP and hgap(p, q) <= 110]
        if easy: err('%s: 일반 점프로 닿음 (%s)' % (p['id'], [q['id'] for q in easy]))
        sup = [q for q in normal if 0 < q['y'] - p['y'] <= SUPER - 15 and hgap(p, q) <= 30]
        if not sup: err('%s: 슈퍼 점프로 닿는 발판 없음' % p['id'])
    # 그림 검사 1: ground.webp 의 서는 선 행이 발판 구간에서 불투명
    g = next(l for l in man['layers'] if l['parallax'] == 1 and not l['repeatX'])
    D = man['density']
    a = np.asarray(Image.open(os.path.join(ROOT, g['src'])).convert('RGBA'))[..., 3]
    for p in pl:
        row = int(round((p['y'] - g['y']) * D))
        c0, c1 = int(np.ceil(p['x1'] * D)) + 2, int(np.floor(p['x2'] * D)) - 2
        op = (a[row, c0:c1] >= 250).mean()
        if op < 0.99: err('%s: 서는 선 행 불투명 %.0f%%' % (p['id'], op * 100))
    if not render_mask:
        return
    # 그림 검사 2: 렌더 마스크 — 서는 선 행에서 '위를 향한 발판 윗면'이 보이고, 좌우 끝이 x1, x2 와 맞는지
    import build, scene
    from vox import top_mask
    boxes = scene.ground()
    s = build.spec('ground')
    for p in pl:
        x0 = int(p['x1'] * D) - 30
        W = int((p['x2'] - p['x1']) * D) + 60
        Hs = int(80 * D)
        y0 = (p['y'] - 40) * D          # 띠 윗변 (px, 지면 레이어 기준)
        anchor = (s['anchor'][0], s['anchor'][1] - (y0 - g['y'] * D))
        m = top_mask(boxes, 0.0, build.PITCH, s['scale'], W=W, H=Hs, anchor=anchor, ss=2, x0=x0)
        rr = int(round(40 * D))
        cols = np.nonzero(m[rr - 1:rr + 2].max(0) > 0.5)[0]
        if len(cols) == 0:
            err('%s: 서는 선에 윗면 없음' % p['id']); continue
        inner = m[rr, int(30 + 3 * D):int(W - 30 - 3 * D)]
        cov = (inner > 0.5).mean()
        L = (x0 + cols.min()) / D; R = (x0 + cols.max() + 1) / D
        band = np.nonzero((m[:, int(30 + 3 * D):int(W - 30 - 3 * D)] > 0.5).mean(1) > 0.3)[0]
        top_rows = ((band.min() / D + p['y'] - 40), (band.max() + 1) / D + p['y'] - 40) if len(band) else (0, 0)
        print('  %-13s y=%-3d 윗면 %4.0f%%  끝 %.1f~%.1f (정본 %d~%d)  윗면 띠 y %.1f~%.1f' % (
            p['id'], p['y'], cov * 100, L, R, p['x1'], p['x2'], top_rows[0], top_rows[1]))
        if cov < 0.95: err('%s: 서는 선 윗면 덮임 %.0f%%' % (p['id'], cov * 100))
        if abs(L - p['x1']) > 1.5 or abs(R - p['x2']) > 1.5: err('%s: 그림 끝 %.1f~%.1f' % (p['id'], L, R))
        if not (top_rows[0] <= p['y'] - 1 and top_rows[1] >= p['y'] + 0.5):
            err('%s: 윗면 띠가 서는 선을 감싸지 않음' % p['id'])


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
    ap.add_argument('--fast', action='store_true', help='발판 렌더 마스크 검사 생략')
    a = ap.parse_args()
    static()
    platforms_check(not a.fast)
    if a.determinism:
        determinism()
    print('OK' if not errors else '%d 문제' % len(errors))
    sys.exit(1 if errors else 0)
