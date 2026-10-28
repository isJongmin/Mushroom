"""아바타 납품 검사 (사이클 9, 2D 메이플풍).

python3 assets/_src/art2d/check.py                 # assets/avatar 검사 + 결정성 재빌드(임시 폴더, 약 2분)
python3 assets/_src/art2d/check.py --fast          # 결정성 재빌드 생략
python3 assets/_src/art2d/check.py --dir <폴더>     # 다른 아바타 폴더 (예: assets/_src/art2d/out/avatar)

검사 항목
 1. manifest 형식: frame 144x192, anchor (72,180), density 1.5, frames 13개 순서, animations(attack [11,12] 포함),
    layerOrder {layer,part,blend}, parts(파츠 키 7개, 사이클 3 id 전부, 드롭 10종 이상 + 메인 고정 10종), presets 6종
 2. manifest.files <-> 디스크 PNG 정확히 일치, 필수 레이어(skin/face/hair_front/top/bottom/shoes/hat)는 모든 id 포함
 3. 시트 크기 1872x192 RGBA
 4. 아이콘 icon/<파츠>/<id>.png 64x64 RGBA, 모든 id(hat none 제외), 네 모서리 투명
 5. 프리셋 + 무작위 조합 합성: 프레임 안(가장자리 1px 여백), 지면 프레임은 발이 기준선(y 180±2),
    jump/fall은 기준선 아래로 넘지 않음, prone은 최하단 기준선 + 키가 side의 35~50%, 정면 머리 맨 위가 월드 85~106
 6. truth/presetN.png = 이 폴더 PNG를 layerOrder로 합성한 결과 (프리멀티 RGB 평균 <= 6.0, 알파 MAE <= 2.0)
 7. 결정적 빌드: 임시 폴더에 다시 빌드한 PNG/manifest 해시가 out/avatar 와 같다 (--fast 면 생략)
"""
import os
import sys
import json
import hashlib
import random
import tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402

NF = len(B.FRAMES)
REQUIRED = {'skin': 'skin', 'face': 'face', 'hair_front': 'hair', 'top': 'top', 'bottom': 'bottom', 'shoes': 'shoes', 'hat': 'hat'}
OLD_IDS = {
    'skin': ['light', 'medium', 'dark'], 'face': ['basic', 'smile', 'wink', 'sleepy'],
    'hair': ['ash-twoblock', 'black-seethrough', 'black-wolfcut', 'pink-bridge-ponytail', 'black-short', 'brown-short',
             'blonde-spiky', 'pink-long', 'sky-bob', 'tan-ponytail', 'black-twintail', 'mint-curly'],
    'top': ['hoodie-lavender', 'cardigan-cream', 'varsity-navy', 'puffer-mint', 'hoodie-black', 'hoodie-white', 'blouse-white',
            'overalls-green', 'tee-stripe-red', 'cape-blue'],
    'bottom': ['denim-wide', 'skirt-check', 'cargo-black', 'cargo-beige', 'pants-navy', 'pants-black', 'skirt-pink',
               'shorts-brown', 'jeans-blue'],
    'shoes': ['chunky-white', 'loafer-socks', 'hightop-black', 'sneakers-white', 'maryjane-red', 'boots-brown', 'sneakers-black'],
    'hat': ['none', 'bucket-white', 'cap-black', 'cap-white', 'mushroom-red', 'explorer-brown', 'beanie-yellow', 'ribbon-pink'],
}
DROP_FIXED = ['hat:snail-shell', 'hat:mushroom-cap', 'hat:golem-helm', 'top:slime-hood', 'top:bat-cape', 'top:golem-armor',
              'bottom:mushroom-shorts', 'bottom:slime-pants', 'shoes:snail-boots', 'shoes:bat-boots']
TOL_MEAN, TOL_ALPHA = 6.0, 2.0
fails = []


def ok(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond:
        fails.append(msg)


def diff_stats(a, b):
    a = a.astype(float); b = b.astype(float)
    pa = a[..., :3] * a[..., 3:4] / 255
    pb = b[..., :3] * b[..., 3:4] / 255
    d = np.abs(pa - pb).mean(-1)
    w = np.maximum(a[..., 3], b[..., 3]) / 255
    return float((d * w).sum() / max(w.sum(), 1)), float(np.abs(a[..., 3] - b[..., 3]).mean())


def frame_stats(sheet, i):
    a = np.asarray(sheet)[:, 144 * i:144 * (i + 1), 3]
    ys, xs = np.where(a > 24)
    return ys.min(), ys.max(), xs.min(), xs.max(), (xs * a[ys, xs]).sum() / a[ys, xs].sum()


def main(av_dir, fast):
    av_dir = os.path.abspath(av_dir)
    print('검사 대상:', av_dir)
    m = json.load(open(os.path.join(av_dir, 'manifest.json'), encoding='utf-8'))
    # 1
    print('1. manifest')
    ok(m.get('frame') == {'w': 144, 'h': 192} and m.get('anchor') == {'x': 72, 'y': 180} and m.get('density') == 1.5,
       'frame/anchor/density')
    ok(m.get('frames') == B.FRAMES, 'frames 13개 순서 %s' % m.get('frames'))
    an = m.get('animations', {})
    ok(an.get('attack', {}).get('frames') == [11, 12] and an.get('prone', {}).get('frames') == [10]
       and an.get('walk', {}).get('frames') == [3, 4, 5, 6], 'animations attack/prone/walk')
    lo = m.get('layerOrder', [])
    ok(all(set(e) == {'layer', 'part', 'blend'} and e['part'] in OLD_IDS and e['blend'] in ('source-over', 'source-atop')
           for e in lo) and len({e['layer'] for e in lo}) == len(lo), 'layerOrder 형식 (%d 레이어)' % len(lo))
    ok(all(e['blend'] == 'source-atop' for e in lo if e['layer'].startswith('shade_')), 'shade_* 는 source-atop')
    P = m.get('parts', {})
    ok(sorted(P) == sorted(OLD_IDS), '파츠 키 7개')
    for k, ids in OLD_IDS.items():
        have = [p['id'] for p in P.get(k, [])]
        ok(all(i in have for i in ids) and have[:len(ids)] == ids, '%s 기존 id %d개 유지(순서 포함)' % (k, len(ids)))
    drops = ['%s:%s' % (k, p['id']) for k in P for p in P[k] if p.get('drop')]
    ok(len(drops) >= 10 and all(d in drops for d in DROP_FIXED), '드롭 파츠 %d종 (고정 10종 포함)' % len(drops))
    ok(len(m.get('presets', [])) == 6 and all(set(p['avatar']) == set(OLD_IDS) for p in m['presets']), '프리셋 6종')
    # 2
    print('2. files <-> 디스크')
    files = m.get('files', {})
    disk = {}
    for l in os.listdir(av_dir):
        p = os.path.join(av_dir, l)
        if os.path.isdir(p) and l != 'icon':
            disk[l] = sorted(f[:-4] for f in os.listdir(p) if f.endswith('.png'))
    ok({k: sorted(v) for k, v in files.items()} == {k: v for k, v in disk.items() if v}, 'manifest.files == 디스크 PNG')
    ok(all(v == sorted(v) for v in files.values()), 'files id 정렬')
    lay_part = {e['layer']: e['part'] for e in lo}
    ok(all(l in lay_part for l in files), 'files 레이어가 모두 layerOrder 에 있음')
    ok(all(i in [p['id'] for p in P[lay_part[l]]] for l in files for i in files[l]), 'files id 가 해당 파츠 id')
    for l, k in REQUIRED.items():
        need = [p['id'] for p in P[k] if p['id'] != 'none']
        ok(sorted(files.get(l, [])) == sorted(need), '필수 레이어 %s: %s 전 id(%d)' % (l, k, len(need)))
    # 3
    print('3. 시트 크기')
    bad = []
    for l, ids in files.items():
        for i in ids:
            im = Image.open(os.path.join(av_dir, l, i + '.png'))
            if im.size != (144 * NF, 192) or im.mode != 'RGBA':
                bad.append('%s/%s %s %s' % (l, i, im.size, im.mode))
    ok(not bad, '모든 시트 %dx192 RGBA %s' % (144 * NF, bad[:3]))
    # 4
    print('4. 아이콘')
    bad = []
    n = 0
    for k in P:
        for p in P[k]:
            if p['id'] == 'none':
                continue
            f = os.path.join(av_dir, 'icon', k, p['id'] + '.png')
            n += 1
            if not os.path.exists(f):
                bad.append(f); continue
            im = Image.open(f)
            a = np.asarray(im.convert('RGBA'))[..., 3]
            if im.size != (64, 64) or im.mode != 'RGBA' or a[[0, 0, -1, -1], [0, -1, 0, -1]].max() > 0 or a.max() < 200:
                bad.append(f)
    ok(not bad, '아이콘 %d개 64x64 투명 %s' % (n, bad[:3]))
    # 5
    print('5. 합성 프레임 검사')
    rng = random.Random(9)
    combos = [p['avatar'] for p in m['presets']]
    for _ in range(30):
        combos.append({k: rng.choice([p['id'] for p in P[k]]) for k in P})
    hat_combo = [any(c['hat'] != 'none' for _ in [0]) for c in combos]
    probs = []
    ratios = []
    tops = []
    for ci, av in enumerate(combos):
        sh = B.compose_sheet(av_dir, av, files)
        st = {f: frame_stats(sh, i) for i, f in enumerate(B.FRAMES)}
        for f, (y0, y1, x0, x1, cx) in st.items():
            if y0 < 1 or x0 < 1 or x1 > 142 or y1 > 190:
                probs.append('%d %s 프레임 밖 %s' % (ci, f, (y0, y1, x0, x1)))
            if f in ('front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back', 'attack0', 'attack1'):
                if not (178 <= y1 <= 183):
                    probs.append('%d %s 발 y=%d' % (ci, f, y1))
            if f in ('jump', 'fall') and y1 > 183:
                probs.append('%d %s 기준선 아래 y=%d' % (ci, f, y1))
        y0, y1, x0, x1, cx = st['prone']
        hs = 180 - st['side'][0]
        r = (180 - y0) / hs
        ratios.append(r)
        if not (178 <= y1 <= 183) or not (0.35 <= r <= (0.52 if av['hat'] != 'none' else 0.48)) or abs(cx - 72) > 14:
            probs.append('%d prone 최하단 %d 비율 %.2f 중심 %.1f %s' % (ci, y1, r, cx, av))
        ht = (180 - st['front'][0]) / 1.5
        tops.append(ht)
        if not (85 <= ht <= 106):
            probs.append('%d 정면 머리 맨 위 월드 %.1f %s' % (ci, ht, av['hat']))
    ok(not probs, '프리셋 6 + 무작위 30 조합 %s' % probs[:6])
    print('       prone 비율 %.2f~%.2f, 정면 머리 맨 위(월드) %.1f~%.1f' % (min(ratios), max(ratios), min(tops), max(tops)))
    # 6
    print('6. truth')
    for i, p in enumerate(m['presets']):
        tp = os.path.join(B.OUT, 'truth', 'preset%d.png' % (i + 1))
        if not os.path.exists(tp):
            ok(False, 'truth preset%d 없음' % (i + 1)); continue
        a = np.asarray(B.compose_sheet(av_dir, p['avatar'], files))
        b = np.asarray(Image.open(tp).convert('RGBA'))
        if a.shape != b.shape:
            ok(False, 'preset%d 크기 %s / %s' % (i + 1, a.shape, b.shape)); continue
        mean, amae = diff_stats(a, b)
        ok(mean <= TOL_MEAN and amae <= TOL_ALPHA, 'preset%d 합성 vs truth: 평균 %.3f 알파 %.3f' % (i + 1, mean, amae))
    # 7
    if fast:
        print('7. 결정성: --fast 생략')
    else:
        print('7. 결정성 재빌드 (임시 폴더)')
        with tempfile.TemporaryDirectory() as td:
            B.build(2, None, log=lambda *a: None, out=td)
            ref = os.path.join(B.OUT, 'avatar')

            def hashes(d):
                h = {}
                for root, _, fs in os.walk(d):
                    for f in fs:
                        p = os.path.join(root, f)
                        h[os.path.relpath(p, d)] = hashlib.md5(open(p, 'rb').read()).hexdigest()
                return h
            ha, hb = hashes(ref), hashes(os.path.join(td, 'avatar'))
            diff = [k for k in set(ha) | set(hb) if ha.get(k) != hb.get(k)]
            ok(not diff, '재빌드 해시 일치 (%d 파일) %s' % (len(ha), diff[:3]))
            hc = hashes(av_dir)
            diff2 = [k for k in set(ha) | set(hc) if ha.get(k) != hc.get(k)]
            ok(not diff2, '설치본(%s) == out/avatar %s' % (av_dir, diff2[:3]))
    print('결과:', '통과' if not fails else '실패 %d건' % len(fails))
    return 0 if not fails else 1


if __name__ == '__main__':
    a = sys.argv[1:]
    d = a[a.index('--dir') + 1] if '--dir' in a else os.path.join(B.ROOT, 'assets', 'avatar')
    sys.exit(main(d, '--fast' in a))
