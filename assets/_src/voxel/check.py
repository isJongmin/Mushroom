"""아바타 납품 검사 (복셀 아트 계약).

python3 assets/_src/voxel/check.py              # 전체 (결정적 빌드 검사 포함: 임시 폴더에 다시 빌드해 해시 비교)
python3 assets/_src/voxel/check.py --fast       # 결정성 재빌드 생략

검사 항목
 1. manifest 형식 (frame/anchor/density/frames/animations/layerOrder{layer,part,blend}/parts/presets)
 2. manifest <-> 파일 일치: 모든 PNG가 layerOrder 의 레이어 + 해당 part 의 id 이고, 필수 레이어 파일이 있다
    + manifest.files: 모든 레이어 키, 정렬된 id, 실제 파일과 정확히 일치, 필수 레이어는 모든 id(hat 은 none 제외) 포함
 3. 시트 크기 = (144*8) x 192 RGBA
 4. 기준점이 프레임 안
 5. 프리셋 6종 합성(+파츠 전 변형 무작위 조합) 결과가 프레임 안 (가장자리 1px 여백), 발이 기준점 근처
 6. 레이어 합성 vs 전체 렌더 차이 <= 허용치 (build_report.json, truth/)
 7. 결정적 빌드: 다시 빌드한 결과의 파일 해시가 같다
"""
import os
import sys
import json
import hashlib
import tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402

AV = os.path.join(B.ROOT, 'assets', 'avatar')
REQUIRED = {'skin': 'skin', 'face': 'face', 'hair_front': 'hair', 'top': 'top', 'bottom': 'bottom', 'shoes': 'shoes', 'hat': 'hat'}
fails = []


def ok(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond:
        fails.append(msg)


def hashes(d):
    out = {}
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            out[os.path.relpath(p, d)] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    return out


def main():
    fast = '--fast' in sys.argv
    m = json.load(open(os.path.join(AV, 'manifest.json'), encoding='utf-8'))
    print('[1] manifest')
    ok(m.get('frame') == {'w': 144, 'h': 192}, 'frame 144x192')
    ok(m.get('anchor') == {'x': 72, 'y': 180}, 'anchor (72,180)')
    ok(m.get('density') == 1.5, 'density 1.5')
    ok(m.get('frames') == B.FRAMES, 'frames 8개 순서')
    an = m.get('animations', {})
    ok(an.get('idle_front', {}).get('frames') == [0, 1] and an.get('idle', {}).get('frames') == [2]
       and an.get('walk', {}).get('frames') == [3, 4, 5, 6], 'animations idle_front/idle/walk')
    lo = m.get('layerOrder', [])
    ok(all(set(e) == {'layer', 'part', 'blend'} and e['blend'] in ('source-over', 'source-atop') for e in lo), 'layerOrder {layer,part,blend}')
    ok(all(e['blend'] == ('source-atop' if e['layer'].startswith('shade_') else 'source-over') for e in lo), 'shade_* = source-atop')
    counts = {k: len(v) for k, v in m['parts'].items()}
    ok(counts == {'skin': 3, 'face': 4, 'hair': 8, 'top': 6, 'bottom': 5, 'shoes': 4, 'hat': 6}, 'parts 개수 %s' % counts)
    ok(m['parts']['hat'][0]['id'] == 'none', 'hat 첫 항목 none')
    ok(len(m.get('presets', [])) == 6, 'presets 6종')
    ids = {k: {p['id'] for p in v} for k, v in m['parts'].items()}
    ok(all(all(pr['avatar'][k] in ids[k] for k in ids) for pr in m['presets']), 'presets 의 id 가 parts 에 있음')

    print('[2] manifest <-> 파일')
    layer_part = {e['layer']: e['part'] for e in lo}
    files = []
    stray = []
    for root, _, fs in os.walk(AV):
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), AV)
            if rel == 'manifest.json':
                continue
            parts = rel.split(os.sep)
            if len(parts) != 2 or not f.endswith('.png') or parts[0] not in layer_part or f[:-4] not in ids[layer_part[parts[0]]]:
                stray.append(rel)
            else:
                files.append((parts[0], f[:-4]))
    ok(not stray, '알 수 없는 파일 없음 %s' % stray[:5])
    missing = [(L, i) for L, part in REQUIRED.items() for i in ids[part] if i != 'none' and (L, i) not in files]
    ok(not missing, '필수 레이어 파일 존재 (없음: %s)' % missing[:5])
    ok(not any(L == 'hat' and i == 'none' for L, i in files), 'hat/none 파일 없음')
    mf = m.get('files')
    ok(isinstance(mf, dict) and list(mf) == [e['layer'] for e in lo], 'files 키 = layerOrder 레이어 전부 (같은 순서)')
    mf = mf if isinstance(mf, dict) else {}
    ok(all(isinstance(v, list) and v == sorted(set(v)) for v in mf.values()), 'files id 정렬, 중복 없음')
    real = {L: sorted(i for L2, i in files if L2 == L) for L in layer_part}
    fdiff = {L: (sorted(set(mf.get(L, [])) - set(real[L])), sorted(set(real[L]) - set(mf.get(L, []))))
             for L in layer_part if mf.get(L, []) != real[L]}
    ok(not fdiff, 'files 목록 = 실제 파일 (레이어: [목록에만], [파일에만]) %s' % fdiff)
    fmiss = [(L, i) for L, part in REQUIRED.items() for i in ids[part] if i != 'none' and i not in mf.get(L, [])]
    ok(not fmiss, 'files 필수 레이어가 모든 id 포함 (hat 은 none 제외) %s' % fmiss[:5])
    print('    files:', {L: len(v) for L, v in mf.items()})

    print('[3] 시트 크기')
    bad = []
    sheets = {}
    for L, i in files:
        im = Image.open(os.path.join(AV, L, i + '.png'))
        if im.size != (144 * 8, 192) or im.mode != 'RGBA':
            bad.append((L, i, im.size, im.mode))
        sheets[(L, i)] = np.array(im.convert('RGBA'))
    ok(not bad, '%d장 모두 1152x192 RGBA %s' % (len(files), bad[:3]))

    print('[4] 기준점')
    ok(0 <= m['anchor']['x'] < 144 and 0 <= m['anchor']['y'] < 192, '기준점 프레임 안')

    print('[5] 합성 범위')
    rng = np.random.default_rng(1)
    combos = [pr['avatar'] for pr in m['presets']]
    for _ in range(40):
        combos.append({k: sorted(ids[k])[rng.integers(len(ids[k]))] for k in ids})
    worst = [999, 999, 0, 0]
    foot_err = 0
    for av in combos:
        c = B.composite(sheets, av)
        for f in range(8):
            a = c[:, f * 144:(f + 1) * 144, 3]
            ys, xs = np.nonzero(a > 8)
            worst = [min(worst[0], xs.min()), min(worst[1], ys.min()), max(worst[2], xs.max()), max(worst[3], ys.max())]
            if f in (2, 3, 4, 5, 6):
                foot_err = max(foot_err, abs(int(ys.max()) - 180))
    ok(worst[0] >= 1 and worst[1] >= 1 and worst[2] <= 142 and worst[3] <= 190, '불투명(a>8) 범위 x %d..%d, y %d..%d (프리셋 6 + 무작위 40)' % (worst[0], worst[2], worst[1], worst[3]))
    ok(foot_err <= 10, '측면 발 끝이 기준선 y=180 근처 (최대 차 %dpx)' % foot_err)

    print('[6] 레이어 합성 vs 전체 렌더')
    rep = json.load(open(os.path.join(HERE, 'out', 'build_report.json')))['layer_vs_full']
    for i, (lab, av) in enumerate(B.PRESETS):
        tp = os.path.join(HERE, 'out', 'truth', 'preset%d.png' % (i + 1))
        tr = np.array(Image.open(tp).convert('RGBA'))
        st = B.diff_stats(B.composite(sheets, av), tr)
        ok(st['mean_abs_rgb'] <= B.TOL_MEAN and st['alpha_mae'] <= B.TOL_ALPHA,
           'preset%d %s: 평균 %.2f (<=%.1f), p95 %.1f, 알파 %.2f (<=%.1f)' % (i + 1, lab, st['mean_abs_rgb'], B.TOL_MEAN, st['p95'], st['alpha_mae'], B.TOL_ALPHA))
    print('    build_report:', json.dumps(rep, ensure_ascii=False)[:200])

    if not fast:
        print('[7] 결정적 빌드 (임시 폴더에 다시 빌드)')
        with tempfile.TemporaryDirectory() as td:
            B.build(os.path.join(td, 'avatar'), os.path.join(td, 'src'), jobs=2, truth=False, log=lambda *_: None)
            h1, h2 = hashes(AV), hashes(os.path.join(td, 'avatar'))
            diff = sorted(k for k in set(h1) | set(h2) if h1.get(k) != h2.get(k))
            ok(not diff, '%d개 파일 해시 동일 %s' % (len(h1), diff[:5]))

    print('\n결과:', '통과' if not fails else '실패 %d건' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
