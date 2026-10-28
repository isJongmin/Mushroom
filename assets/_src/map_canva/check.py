"""사이클 10 맵 검사 (Canva 그림 맵).

python3 assets/_src/map_canva/check.py [MAPDIR] [--determinism]
  MAPDIR 기본 assets/map. 검사: manifest 형식/파일/크기, 용량 3MB, 지면선 행과 서는 선 행 불투명,
  발판 범위/너비, 잔디 섬 윗면이 서는 선과 맞는지(그림 대조), 점프 도달성(일반 105, 슈퍼 225), 스폰 규칙, 결정성.
"""
import os, sys, json, argparse, hashlib, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)

JUMP, SUPER = 105.6, 225.6     # physics.js JUMP_APEX, SUPER_APEX (월드)
MARGIN = 6                     # 발이 올라서려면 최고점이 윗면보다 이만큼 높아야 한다
HGAP = 70                      # 점프로 건너는 가로 거리 상한 (사이클 8 검사와 같음)
LIMIT = 3 * 1024 * 1024
MOBS = ('snail', 'mushroom', 'slime', 'bat', 'golem')
errors = []


def err(m):
    errors.append(m); print('FAIL', m)


def check(mapdir):
    man = json.load(open(os.path.join(mapdir, 'manifest.json'), encoding='utf-8'))
    D = man['density']
    if D != 1.5: err('density')
    W, H, GY = man['width'], man['height'], man['groundY']
    tot = os.path.getsize(os.path.join(mapdir, 'manifest.json'))
    ground = None
    for l in man['layers']:
        fn = os.path.join(mapdir, os.path.basename(l['src']))
        if not l['src'].startswith('assets/map/'): err('src ' + l['src'])
        if not os.path.exists(fn): err('없음 ' + fn); continue
        tot += os.path.getsize(fn)
        im = Image.open(fn)
        if abs(l['w'] - im.width / D) > 0.01 or abs(l['h'] - im.height / D) > 0.01: err('w/h 불일치 ' + fn)
        if l['parallax'] == 1 and not l['repeatX']:
            ground = (l, np.asarray(im.convert('RGBA')))
    print('world %.1f x %.1f groundY %d, layers %s, %.2f MB' % (W, H, GY, [l['name'] for l in man['layers']], tot / 1048576))
    if tot > LIMIT: err('용량 %.2f MB > 3MB' % (tot / 1048576))
    if ground is None:
        err('지면 레이어 없음'); return man
    l, g = ground
    if abs(l['w'] - W) > 0.01 or abs(l['h'] - H) > 0.01: err('지면 레이어가 월드 크기와 다름')
    if g[..., 3].min() < 255: err('지면 레이어에 투명 픽셀 (하늘 포함 불투명이어야 함)')
    # 발판
    pl = man['platforms']
    ids = set()
    for p in pl:
        if set(p) != {'id', 'x1', 'x2', 'y'}: err('키 %s' % p)
        if p['id'] in ids: err('id 중복 ' + p['id'])
        ids.add(p['id'])
        if not (0 <= p['x1'] < p['x2'] <= W): err('%s x 범위' % p['id'])
        if not (0 < p['y'] < GY): err('%s y 범위' % p['id'])
        if p['x2'] - p['x1'] < 80: err('%s 너비 %d < 80' % (p['id'], p['x2'] - p['x1']))
    # 그림 대조: 잔디 섬과 지면 — 서는 선 y 위 2~8px(에셋) 안에 잔디 윗면 윗끝이 있어야 한다
    rgb = g[..., :3].astype(float)
    Rr, Gg, Bb = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    grass = (Gg > Rr * 0.85) & (Rr > Bb * 1.45) & (Gg > Bb * 1.5) & (Gg > 95)
    for p in pl + [dict(id='ground', x1=10, x2=W - 10, y=GY)]:
        if '-isle-' not in p['id'] and p['id'] != 'ground':
            continue
        c0, c1 = int(p['x1'] * D) + 8, int(p['x2'] * D) - 8
        Y = p['y'] * D
        rows = np.arange(int(Y) - 30, int(Y) + 30)
        fr = grass[rows, c0:c1].mean(1)
        on = rows[fr > (0.9 if p['id'] != 'ground' else 0.6)]
        top = on.min() if len(on) else -999
        d = Y - top
        ok = (2 <= d <= 9) if p['id'] != 'ground' else (-4 <= d <= 14)
        print('  %-16s y=%-4d 윗면 윗끝까지 %+.1f px' % (p['id'], p['y'], d))
        if not ok: err('%s 서는 선과 잔디 윗면 어긋남 (%.1f px)' % (p['id'], d))
    # 도달성
    nodes = [dict(id='ground', x1=0, x2=W, y=GY)] + pl

    def hgap(a, b):
        return max(0, max(a['x1'], b['x1']) - min(a['x2'], b['x2']))

    def reach(limit):
        seen = {'ground'}; frontier = ['ground']
        byid = {n['id']: n for n in nodes}
        while frontier:
            a = byid[frontier.pop()]
            for b in nodes:
                if b['id'] in seen: continue
                dy = a['y'] - b['y']
                if (0 < dy <= limit - MARGIN or dy <= 0) and hgap(a, b) <= HGAP:
                    seen.add(b['id']); frontier.append(b['id'])
        return seen
    rn, rs = reach(JUMP), reach(SUPER)
    super_only = [p['id'] for p in pl if p['id'] not in rn and p['id'] in rs]
    never = [p['id'] for p in pl if p['id'] not in rs]
    print('도달: 일반 점프만 %d/%d, 슈퍼 점프 포함 %d/%d' % (len(rn) - 1, len(pl), len(rs) - 1, len(pl)))
    # 0-1 BFS: 발판마다 필요한 최소 슈퍼 점프 횟수
    import collections
    byid = {n['id']: n for n in nodes}
    cost = {'ground': 0}; dq = collections.deque(['ground'])
    while dq:
        a = byid[dq.popleft()]
        for b in nodes:
            dy = a['y'] - b['y']
            if hgap(a, b) > HGAP: continue
            if dy <= 0 or dy <= JUMP - MARGIN: c = 0
            elif dy <= SUPER - MARGIN: c = 1
            else: continue
            if cost[a['id']] + c < cost.get(b['id'], 99):
                cost[b['id']] = cost[a['id']] + c
                (dq.appendleft if c == 0 else dq.append)(b['id'])
    print('  최소 슈퍼 점프 수: %s' % ', '.join('%s=%d' % (p['id'], cost.get(p['id'], -1)) for p in pl))
    if never: err('닿지 않는 발판: %s' % never)
    # 스폰
    plat = {p['id']: p for p in pl}
    for s in man['spawns']:
        if any(m not in MOBS for m in s['mobs']): err('mob id ' + s['id'])
        if s['platform'] == 'ground':
            lo, hi = 0, W
        elif s['platform'] in plat:
            lo, hi = plat[s['platform']]['x1'], plat[s['platform']]['x2']
        else:
            err('spawn platform ' + s['id']); continue
        if not (lo <= s['x1'] < s['x2'] <= hi): err('spawn 범위 ' + s['id'])
        if s['max'] < 1: err('max ' + s['id'])
    sp = man['spawn']
    if not (0 <= sp['x'] <= W and sp['y'] == GY): err('spawn')
    print('spawns %d, spawn %s' % (len(man['spawns']), sp))
    return man


def determinism():
    import build
    h = []
    for _ in range(2):
        d = tempfile.mkdtemp()
        build.build(d)
        h.append(''.join(hashlib.md5(open(os.path.join(d, f), 'rb').read()).hexdigest()
                         for f in ('ground.webp', 'sky.png', 'manifest.json')))
    print('결정성', 'OK' if h[0] == h[1] else 'FAIL')
    if h[0] != h[1]: err('결정성')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mapdir', nargs='?', default=os.path.join(ROOT, 'assets', 'map'))
    ap.add_argument('--determinism', action='store_true')
    a = ap.parse_args()
    check(a.mapdir)
    if a.determinism:
        determinism()
    print('OK' if not errors else '%d 문제' % len(errors))
    sys.exit(1 if errors else 0)
