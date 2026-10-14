"""블록 아트 납품 검사 (docs/ARCHITECTURE.md "블록 아트 계약").

  python3 assets/_src/block/check.py

검사 항목
  1. assets/ 아래 납품 파일 목록 = manifest 가 가리키는 파일 + manifest/outline.json (1:1, 남는 파일 없음)
  2. 아바타 PNG 336x64, 맵 PNG 크기/위치 (ground 너비 1200, 아래 끝 270, 반복 레이어 아래 끝이 잔디(218) 뒤)
  3. 모든 PNG 알파 0/255 만
  4. 팔레트 42색 외 색 없음
  5. outline.json: 아바타 PNG 에 쓰인 모든 불투명 색 포함, 키/값 대문자 #RRGGBB, 값도 팔레트 색
  6. manifest 형식(키, 프레임 순서, layerOrder, 기본값, hat none, id 규칙, presets 의 id 유효)
  7. 프레임 여백: 합성 + 외곽선 결과가 프레임 안 (불투명 픽셀 x 1..46, y 1..61), 기준점 아래 2행 여백
  8. 결정적 빌드: 임시 폴더에 두 번 빌드한 결과 md5 동일, 저장소 파일과도 동일
  9. 맵: 잔디 윗면 첫 행 y=218 이 x 0..1199 전부 불투명, 지면선 y=220 행도 불투명
"""
import os
import sys
sys.dont_write_bytecode = True
import re
import json
import glob
import hashlib
import tempfile
import random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))

from PIL import Image  # noqa: E402
from palette import PAL  # noqa: E402

FAIL = []


def ok(cond, msg):
    if not cond:
        FAIL.append(msg)
    return cond


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def tree(root):
    out = {}
    for sub in ('avatar', 'map'):
        for p in sorted(glob.glob(os.path.join(root, 'assets', sub, '**', '*'), recursive=True)):
            if os.path.isfile(p):
                out[os.path.relpath(p, root)] = md5(p)
    return out


def main():
    pal = {v.upper() for v in PAL.values()}
    am = json.load(open(os.path.join(ROOT, 'assets/avatar/manifest.json'), encoding='utf-8'))
    mm = json.load(open(os.path.join(ROOT, 'assets/map/manifest.json'), encoding='utf-8'))
    outline = json.load(open(os.path.join(ROOT, 'assets/avatar/outline.json'), encoding='utf-8'))

    # 6. manifest 형식
    ok(am['frame'] == {'w': 48, 'h': 64}, 'frame')
    ok(am['anchor'] == {'x': 24, 'y': 60}, 'anchor')
    ok(am['scale'] == 2, 'scale')
    ok(am['frames'] == ['front', 'side_idle', 'side_walk0', 'side_walk1', 'side_walk2', 'side_walk3', 'back'], 'frames')
    ok(am['animations'] == {'idle': {'frames': [1], 'ms': 500}, 'walk': {'frames': [2, 3, 4, 5], 'ms': 150}}, 'animations')
    ok(am['layerOrder'] == ['hair_back', 'skin', 'face', 'bottom', 'shoes', 'top', 'hair_front', 'hat'], 'layerOrder')
    cats = ['skin', 'hair', 'face', 'top', 'bottom', 'shoes', 'hat']
    ok(sorted(am['parts']) == sorted(cats), 'parts keys')
    ok(am['parts']['hat'][0] == {'id': 'none', 'label': '없음'}, 'hat none first')
    idre = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
    for c in cats:
        ids = [p['id'] for p in am['parts'][c]]
        ok(len(ids) == len(set(ids)), 'dup id ' + c)
        for p in am['parts'][c]:
            ok(set(p) == {'id', 'label'} and idre.match(p['id']) and p['label'], 'part entry %s %s' % (c, p))
    ok(len(am['presets']) == 6, 'presets count')
    for pr in am['presets']:
        ok(set(pr['avatar']) == set(cats), 'preset keys %s' % pr['label'])
        for c in cats:
            ok(pr['avatar'][c] in [p['id'] for p in am['parts'][c]], 'preset id %s %s' % (pr['label'], c))

    # 1. 파일 1:1
    expect = {'assets/avatar/manifest.json', 'assets/avatar/outline.json', 'assets/map/manifest.json'}
    for c in cats:
        for p in am['parts'][c]:
            if c == 'hat' and p['id'] == 'none':
                continue
            layers = ['hair_back', 'hair_front'] if c == 'hair' else [c]
            for l in layers:
                expect.add('assets/avatar/%s/%s.png' % (l, p['id']))
    for L in mm['layers']:
        expect.add(L['src'])
    have = set()
    for p in glob.glob(os.path.join(ROOT, 'assets', '**', '*'), recursive=True):
        rel = os.path.relpath(p, ROOT)
        if os.path.isfile(p) and not rel.startswith('assets/_src/'):
            have.add(rel)
    ok(have == expect, 'files 1:1: missing %s extra %s' % (sorted(expect - have), sorted(have - expect)))

    # 2-5. PNG 검사
    used = set()
    npng = 0
    for rel in sorted(expect):
        if not rel.endswith('.png') or not os.path.exists(os.path.join(ROOT, rel)):
            continue
        npng += 1
        im = Image.open(os.path.join(ROOT, rel))
        ok(im.mode == 'RGBA', 'mode ' + rel)
        if rel.startswith('assets/avatar/'):
            ok(im.size == (336, 64), 'size %s %s' % (rel, im.size))
        for cnt, px in im.getcolors(1 << 20):
            if px[3] not in (0, 255):
                ok(False, 'alpha %s %s' % (rel, px))
            elif px[3] == 255:
                h = '#%02X%02X%02X' % px[:3]
                ok(h in pal, 'off-palette %s %s' % (rel, h))
                if rel.startswith('assets/avatar/'):
                    used.add(h)
    for k, v in outline.items():
        ok(re.match(r'^#[0-9A-F]{6}$', k) and re.match(r'^#[0-9A-F]{6}$', v), 'outline hex case %s' % k)
        ok(v in pal, 'outline value off-palette %s' % v)
    ok(used <= set(outline), 'outline missing %s' % sorted(used - set(outline)))

    # 맵 레이어
    ok(mm['scale'] == 2 and mm['groundY'] == 220 and mm['width'] == 1200, 'map header')
    par = [L['parallax'] for L in mm['layers']]
    ok(par == sorted(par) and par[-1] == 1.0, 'parallax order')
    for i, L in enumerate(mm['layers']):
        im = Image.open(os.path.join(ROOT, L['src']))
        w, h = im.size
        ok(L['y'] + h <= 270, 'layer below world %s' % L['src'])
        if i == len(mm['layers']) - 1:
            ok(w == 1200 and not L['repeatX'] and L['parallax'] == 1.0 and L['y'] + h == 270, 'ground layer %s' % L)
            a = im.load()
            for y in (218, 220, 269):
                ok(all(a[x, y - L['y']][3] == 255 for x in range(w)), 'ground row %d not solid' % y)
            ok(any(a[x, 217 - L['y']][3] == 255 for x in range(w)), 'props on ground')
        elif L['src'].endswith(('far.png', 'mid.png')):
            ok(L['y'] + h >= 219, 'repeat layer bottom hidden %s' % L['src'])
            ok(L['repeatX'], 'repeatX ' + L['src'])
        if L['src'].endswith('sky.png'):
            ok(h == 270 and L['y'] == 0, 'sky covers world')

    # 7. 프레임 여백 (모든 프리셋 + 고정 시드 무작위 200 조합)
    import avatar
    sheets = {}
    for c in cats:
        for p in am['parts'][c]:
            if c == 'hat' and p['id'] == 'none':
                continue
            for l in (['hair_back', 'hair_front'] if c == 'hair' else [c]):
                sheets[(l, p['id'])] = Image.open(os.path.join(ROOT, 'assets/avatar/%s/%s.png' % (l, p['id']))).convert('RGBA')
    rng = random.Random(7)
    combos = [pr['avatar'] for pr in am['presets']]
    combos += [{c: rng.choice(am['parts'][c])['id'] for c in cats} for _ in range(200)]
    worst = [99, 99, -1, -1]
    for av in combos:
        comp = avatar.compose(sheets, av)
        for f in range(7):
            bb = comp.crop((48 * f, 0, 48 * f + 48, 64)).getbbox()
            worst = [min(worst[0], bb[0]), min(worst[1], bb[1]), max(worst[2], bb[2]), max(worst[3], bb[3])]
    ok(worst[0] >= 1 and worst[1] >= 1 and worst[2] <= 47 and worst[3] <= 61, 'frame margin %s' % worst)

    # 8. 결정적 빌드
    import build
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        build.build(t1)
        build.build(t2)
        a, b = tree(t1), tree(t2)
        ok(a == b, 'nondeterministic build')
        ok(a == tree(ROOT), 'repo assets differ from fresh build (run build.py)')

    print('PNG %d, outline colors %d (used %d), combos checked %d, opaque bbox union %s' % (
        npng, len(outline), len(used), len(combos), worst))
    if FAIL:
        print('FAIL %d' % len(FAIL))
        for f in FAIL:
            print('  -', f)
        sys.exit(1)
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
