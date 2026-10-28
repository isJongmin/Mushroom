"""사이클 9 맵 검사.

python3 assets/_src/art2d_map/check.py [--determinism]
1. manifest 형식, 정본 표(platforms.py)와 일치, 월드 크기/지면/부활 지점
2. 발판 규칙: 범위, 너비, 층 간격(85~95), 일반 발판은 아래 층(또는 지면)에서 일반 점프(105)로 닿음(가로 70 이내),
   슈퍼 전용 발판은 일반 점프로 닿지 않고 슈퍼 점프(225)로 닿음, 층 수 4~5(+슈퍼 1~2)
3. 그림 대조: 발판만 그린 장면을 렌더해 윗면 첫 불투명 행이 y*1.5 와 ±1.5px 안(열의 85% 이상),
   좌우 끝이 x1/x2 와 ±10px 안, ground.webp 의 y*1.5+2 행이 95% 이상 불투명, 지면선 행(1352) 전 구간 불투명
4. 스폰: 몬스터 id, 발판 id, 구간이 발판 안, 개수 8~12, 마을 중앙(x 1600~3200)에 없음, 지면에 golem/snail,
   낮은 층(810/720)에 mushroom/slime, bat 는 540 이하 높은 층
5. 용량 10MB 이하, --determinism 이면 빌드 2회 md5 비교
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MAP = os.path.join(ROOT, 'assets', 'map')
STYLE = 'v1'

from platforms import PLATFORMS, SPAWNS, SPAWN, WORLD_W, WORLD_H, GROUND_Y, DENSITY, MOB_IDS  # noqa: E402

errors = []


def err(msg):
    errors.append(msg)
    print('FAIL', msg)


def check_manifest():
    m = json.load(open(os.path.join(MAP, 'manifest.json')))
    if (m.get('width'), m.get('height'), m.get('groundY'), m.get('density')) != (WORLD_W, WORLD_H, GROUND_Y, DENSITY):
        err('manifest world/groundY/density')
    if m.get('spawn') != SPAWN:
        err('manifest spawn')
    want = [dict(id=p['id'], x1=p['x1'], x2=p['x2'], y=p['y']) for p in PLATFORMS]
    if m.get('platforms') != want:
        err('manifest platforms != PLATFORMS')
    if len(m.get('spawns', [])) != len(SPAWNS):
        err('manifest spawns')
    for l in m['layers']:
        if not os.path.exists(os.path.join(MAP, os.path.basename(l['src']))):
            err('missing ' + l['src'])
    g = [l for l in m['layers'] if l['parallax'] == 1.0 and not l.get('repeatX') and not l.get('stretchX')]
    if len(g) != 1 or abs(g[0]['w'] - WORLD_W) > 0.01 or g[0]['y'] != 0:
        err('ground layer width/y')
    return m


def check_platforms():
    ids = set()
    normal = [p for p in PLATFORMS if not p.get('secret')]
    secret = [p for p in PLATFORMS if p.get('secret')]
    for p in PLATFORMS:
        if p['id'] in ids:
            err('dup id ' + p['id'])
        ids.add(p['id'])
        if not (0 <= p['x1'] < p['x2'] <= WORLD_W) or p['x2'] - p['x1'] < 80:
            err('range ' + p['id'])
    tiers = sorted({p['y'] for p in normal}, reverse=True)
    gaps = np.diff([GROUND_Y] + tiers)
    if not all(-95 <= g <= -85 for g in gaps):
        err(f'tier gaps {gaps}')
    if not (4 <= len(tiers) <= 5):
        err(f'tier count {len(tiers)}')
    if not (1 <= len(secret) <= 2):
        err('secret count')

    def reach(p, jump, pool):
        out = []
        for q in pool + [dict(id='ground', x1=0, x2=WORLD_W, y=GROUND_Y)]:
            if q is p:
                continue
            dy = q['y'] - p['y']
            dx = max(0, max(p['x1'], q['x1']) - min(p['x2'], q['x2']))
            if 0 < dy <= jump and dx <= 70:
                out.append(q['id'])
        return out
    for p in normal:
        if not reach(p, 105, normal):
            err('unreachable ' + p['id'])
    for p in secret:
        if reach(p, 105, normal):
            err('secret reachable by normal jump ' + p['id'])
        if not reach(p, 225, normal):
            err('secret unreachable ' + p['id'])
    print(f'platforms: {len(PLATFORMS)} (normal {len(normal)}, super {len(secret)}), tiers {tiers}')


def check_art():
    import importlib
    L = importlib.import_module('layers2' if STYLE == 'v2' else 'layers')
    from vec import Scene, render
    g = np.asarray(Image.open(os.path.join(MAP, 'ground.webp')).convert('RGBA'))
    if g.shape[:2] != (int(WORLD_H * DENSITY), int(WORLD_W * DENSITY)):
        err('ground size')
    gy = int(GROUND_Y * DENSITY)
    if (g[gy + 2, :, 3] < 250).mean() > 0.0:
        err('ground line not opaque')
    worst = []
    for p in PLATFORMS:
        s = Scene(L.GW, L.GH)
        L.draw_platforms(s, None, only={p['id']})
        Y = p['y'] * DENSITY
        # 서는 선 위로 3px 넘게 솟는 명령(풀잎, 난간, 기둥 머리, 금빛 버섯 같은 장식)은 빼고 몸체만 대조한다
        s.ops = [op for op in s.ops if op[0] == 'unclip' or op[1][1] >= Y - 3]
        depth = 0
        kept = []
        for op in s.ops:  # 짝이 맞지 않는 unclip 제거
            if op[0] == 'clip':
                depth += 1
            elif op[0] == 'unclip':
                if depth == 0:
                    continue
                depth -= 1
            kept.append(op)
        s.ops = kept
        x0, x1 = p['x1'] * DENSITY, p['x2'] * DENSITY
        reg = (int(x0) - 40, int(Y) - 40, int(x1) + 40, int(Y) + 30)
        a = render(s, region=reg, tile=256)[..., 3]
        cols = np.arange(int(x0) + 3, int(x1) - 3) - reg[0]
        tops = []
        for c in cols:
            col = a[:, c]
            idx = np.nonzero(col > 0.5)[0]
            # 서는 선 근처에서 연속으로 불투명한 덩어리의 윗끝 (풀잎 장식은 무시: 위 12px 안의 고립 픽셀)
            near = idx[(idx >= 40 - 14) & (idx <= 40 + 6)]
            tops.append(near.min() + reg[1] if len(near) else 1e9)
        tops = np.array(tops)
        okf = (np.abs(tops - Y) <= 1.5).mean()
        rowf = (a[int(round(Y)) + 2 - reg[1], cols] > 0.9).mean()
        # 좌우 끝: 서는 선 +2 행에서 불투명 구간
        row = a[int(round(Y)) + 2 - reg[1]]
        on = np.nonzero(row > 0.5)[0]
        le, re = on.min() + reg[0], on.max() + reg[0]
        endok = abs(le - x0) <= 10 and abs(re - x1) <= 10
        fin = (g[int(round(Y)) + 2, int(x0) + 3:int(x1) - 3, 3] > 230).mean()
        worst.append((okf, p['id']))
        if okf < 0.85 or rowf < 0.95 or not endok or fin < 0.95:
            err(f"art {p['id']}: top-match {okf:.2f} row {rowf:.2f} ends {le - x0:+.1f}/{re - x1:+.1f} final {fin:.2f}")
    worst.sort()
    print('art: worst top-match', ', '.join(f'{i}={v:.2f}' for v, i in worst[:4]))


def check_spawns():
    plat = {p['id']: p for p in PLATFORMS}
    if not (8 <= len(SPAWNS) <= 12):
        err('spawn count')
    for s in SPAWNS:
        for mob in s['mobs']:
            if mob not in MOB_IDS:
                err('mob id ' + mob)
        if s['platform'] == 'ground':
            y, lo, hi = GROUND_Y, 0, WORLD_W
            if not set(s['mobs']) <= {'golem', 'snail'}:
                err('ground mobs ' + s['id'])
        else:
            if s['platform'] not in plat:
                err('spawn platform ' + s['id'])
                continue
            q = plat[s['platform']]
            y, lo, hi = q['y'], q['x1'], q['x2']
            if 'bat' in s['mobs'] and y > 540:
                err('bat too low ' + s['id'])
            if set(s['mobs']) & {'mushroom', 'slime'} and y < 720:
                err('mushroom/slime too high ' + s['id'])
        if not (lo <= s['x1'] < s['x2'] <= hi):
            err('spawn range ' + s['id'])
        if s['x2'] > 1600 and s['x1'] < 3200:
            err('spawn in town ' + s['id'])
        if s['max'] < 1:
            err('max ' + s['id'])
    print(f'spawns: {len(SPAWNS)} ok')


def check_size():
    tot = sum(os.path.getsize(os.path.join(MAP, f)) for f in os.listdir(MAP))
    print(f'size: {tot / 1024 / 1024:.2f} MB')
    if tot > 10 * 1024 * 1024:
        err('size > 10MB')


def md5s():
    return {f: hashlib.md5(open(os.path.join(MAP, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(MAP))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--determinism', action='store_true')
    ap.add_argument('--style', default='v1', choices=['v1', 'v2'])
    ap.add_argument('--map', default=None, help='검사할 맵 폴더 (기본 assets/map)')
    a = ap.parse_args()
    global MAP, STYLE
    STYLE = a.style
    if a.map:
        MAP = os.path.abspath(a.map)
    check_manifest()
    check_platforms()
    check_spawns()
    check_art()
    check_size()
    if a.determinism:
        h1 = md5s()
        subprocess.run([sys.executable, os.path.join(HERE, 'build.py'), '--style', STYLE, '--out', MAP], check=True, stdout=subprocess.DEVNULL)
        h2 = md5s()
        if h1 != h2:
            err('not deterministic: ' + str([f for f in h1 if h1[f] != h2.get(f)]))
        else:
            print('determinism: md5 identical')
    print('OK' if not errors else f'{len(errors)} errors')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
