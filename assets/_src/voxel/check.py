"""아바타 납품 검사 (복셀 아트 계약).

python3 assets/_src/voxel/check.py              # 전체 (결정적 빌드 검사 포함: 임시 폴더에 다시 빌드해 해시 비교)
python3 assets/_src/voxel/check.py --only hair:espresso-crop  # 전체 계약 + 선택 파츠 증분 결정성 재렌더
python3 assets/_src/voxel/check.py --fast       # 결정성 재빌드 생략
python3 assets/_src/voxel/check.py --av DIR --src-out DIR   # (사이클 10) 설치 전 다른 폴더의 빌드 결과 검사

검사 항목
 1. manifest 형식 (frame/anchor/density/frames/animations/layerOrder{layer,part,blend}/parts/presets)
    (사이클 7) 파츠 개수 hair 15 / top 12 / bottom 10 / shoes 7 / hat 9(none 포함), 사이클 5 id 전부 유지
 2. manifest <-> 파일 일치: 모든 PNG가 layerOrder 의 레이어 + 해당 part 의 id 이고, 필수 레이어 파일이 있다
    + manifest.files: 모든 레이어 키, 정렬된 id, 실제 파일과 정확히 일치, 필수 레이어는 모든 id(hat 은 none 제외) 포함
 3. 시트 크기 = (144*13) x 192 RGBA
 4. 기준점이 프레임 안
 5. 프리셋 12종 합성(+파츠 전 변형 무작위 조합) 결과가 프레임 안 (가장자리 1px 여백), 발이 기준점 근처
    (사이클 6) jump/fall: 발이 기준선 위로 떠도 되지만 기준선 아래로 넘지 않고, 몸 중심 높이가 side 와 비슷
    (사이클 8) prone: 몸 최하단이 기준선, 키(기준선~위끝)가 side 의 35~45% (모자 포함 조합은 50% 이하), 몸 가로 중심이 기준점 x 근처
    (사이클 8) layerOrder: shoes_under 가 bottom 바로 앞
    (사이클 10) 13프레임 1872x192, 11 attack0 / 12 attack1, animations attack [11,12] 120ms, 공격 프레임도 발이 기준선
 6. 레이어 합성 vs 전체 렌더 차이 <= 허용치 (build_report.json, truth/)
 7. 결정적 빌드: 다시 빌드한 결과의 파일 해시가 같다
"""
import os
import sys
import json
import hashlib
import tempfile
import shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402

AV = os.path.join(B.ROOT, 'assets', 'avatar')
NF = len(B.FRAMES)
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
    global AV
    fast = '--fast' in sys.argv
    a = sys.argv[1:]
    if '--av' in a:
        AV = os.path.abspath(a[a.index('--av') + 1])
    src = os.path.abspath(a[a.index('--src-out') + 1]) if '--src-out' in a else os.path.join(HERE, 'out')
    m = json.load(open(os.path.join(AV, 'manifest.json'), encoding='utf-8'))
    print('[1] manifest')
    ok(m.get('frame') == {'w': 144, 'h': 192}, 'frame 144x192')
    ok(m.get('anchor') == {'x': 72, 'y': 180}, 'anchor (72,180)')
    ok(m.get('density') == 1.5, 'density 1.5')
    ok(m.get('frames') == B.FRAMES and len(B.FRAMES) == 13 and B.FRAMES[8:] == ['jump', 'fall', 'prone', 'attack0', 'attack1'],
       'frames 13개 순서 (8 jump, 9 fall, 10 prone, 11 attack0, 12 attack1)')
    an = m.get('animations', {})
    ok(an.get('idle_front', {}).get('frames') == [0, 1] and an.get('idle', {}).get('frames') == [2]
       and an.get('walk', {}).get('frames') == [3, 4, 5, 6], 'animations idle_front/idle/walk')
    ok(an.get('jump') == {'frames': [8], 'ms': 200} and an.get('fall') == {'frames': [9], 'ms': 200}
       and an.get('prone') == {'frames': [10], 'ms': 200} and 'crouch' not in an, 'animations jump [8] / fall [9] / prone [10] 200ms (crouch 없음)')
    ok(an.get('attack') == {'frames': [11, 12], 'ms': 120}, 'animations attack [11,12] 120ms (사이클 10)')
    lo = m.get('layerOrder', [])
    ok(all(set(e) == {'layer', 'part', 'blend'} and e['blend'] in ('source-over', 'source-atop') for e in lo), 'layerOrder {layer,part,blend}')
    ok(all(e['blend'] == ('source-atop' if e['layer'].startswith('shade_') else 'source-over') for e in lo), 'shade_* = source-atop')
    lay = [e['layer'] for e in lo]
    ok('shoes_under' in lay and lay.index('shoes_under') + 1 == lay.index('bottom')
       and lo[lay.index('shoes_under')]['part'] == 'shoes', 'shoes_under(part shoes) 가 bottom 바로 앞')
    counts = {k: len(v) for k, v in m['parts'].items()}
    ok(counts == {'skin': 3, 'face': 4, 'hair': 15, 'top': 12, 'bottom': 10, 'shoes': 7, 'hat': 9}, 'parts 개수 %s' % counts)
    V5IDS = {'skin': ['light', 'medium', 'dark'], 'face': ['basic', 'smile', 'wink', 'sleepy'],
             'hair': ['black-short', 'brown-short', 'blonde-spiky', 'pink-long', 'sky-bob', 'tan-ponytail', 'black-twintail', 'mint-curly'],
             'top': ['hoodie-black', 'hoodie-white', 'blouse-white', 'overalls-green', 'tee-stripe-red', 'cape-blue'],
             'bottom': ['pants-navy', 'pants-black', 'skirt-pink', 'shorts-brown', 'jeans-blue'],
             'shoes': ['sneakers-white', 'maryjane-red', 'boots-brown', 'sneakers-black'],
             'hat': ['none', 'cap-white', 'mushroom-red', 'explorer-brown', 'beanie-yellow', 'ribbon-pink']}
    have = {k: {p['id'] for p in v} for k, v in m['parts'].items()}
    lost = {k: [i for i in v if i not in have.get(k, ())] for k, v in V5IDS.items()}
    ok(not any(lost.values()), '사이클 5 id 전부 유지 (저장된 프로필 호환) %s' % {k: v for k, v in lost.items() if v})
    ok(m['parts']['hat'][0]['id'] == 'none', 'hat 첫 항목 none')
    ok(len(m.get('presets', [])) == 12, 'presets 12종 (기존 6 + 신규 6)')
    ok(m.get('revision') == 'fine-pixel-variety-20261029-v2', '새 revision으로 캐시 갱신')
    extra = m.get('presets', [])[6:]
    ok({pr['avatar']['skin'] for pr in extra} == {'light', 'medium', 'dark'}
       and {pr['avatar']['face'] for pr in extra} == {'basic', 'smile', 'wink', 'sleepy'},
       '새 추천: 피부 3톤과 표정 4종 모두 사용')
    ok(m['presets'] == [{'label': lab, 'avatar': av} for lab, av in B.PRESETS], '추천 순서와 모델 원본 일치')
    V10IDS = {'hair': ['ash-twoblock', 'black-seethrough', 'black-wolfcut', 'pink-bridge-ponytail'],
              'top': ['hoodie-lavender', 'cardigan-cream', 'varsity-navy', 'puffer-mint'],
              'bottom': ['denim-wide', 'skirt-check', 'cargo-black', 'cargo-beige'],
              'shoes': ['chunky-white', 'loafer-socks', 'hightop-black'],
              'hat': ['bucket-white', 'cap-black']}
    ok(all(set(v) <= have[k] for k, v in V10IDS.items()), '사이클 10 기존 id도 전부 유지')
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
        if im.size != (144 * NF, 192) or im.mode != 'RGBA':
            bad.append((L, i, im.size, im.mode))
        sheets[(L, i)] = np.array(im.convert('RGBA'))
    ok(not bad and NF == 13, '%d장 모두 %dx192 RGBA (13프레임 1872x192) %s' % (len(files), 144 * NF, bad[:3]))

    print('[4] 기준점')
    ok(0 <= m['anchor']['x'] < 144 and 0 <= m['anchor']['y'] < 192, '기준점 프레임 안')

    print('[5] 합성 범위')
    rng = np.random.default_rng(1)
    combos = [pr['avatar'] for pr in m['presets']]
    for _ in range(40):
        combos.append({k: sorted(ids[k])[rng.integers(len(ids[k]))] for k in ids})
    worst = [999, 999, 0, 0]
    foot_err = 0
    air = {'jump': [999, 0], 'fall': [999, 0]}       # 발 끝(최하단) y 범위
    center = []                                     # |몸 중심 y(jump/fall) - side|
    ratio = [9, 0]                                  # prone 키 / side 키 (모자 없음)
    ratio_hat = [9, 0]                              # 모자 있음
    pcx = []                                        # prone 몸 가로 중심 (알파 가중)
    fi = {n: i for i, n in enumerate(B.FRAMES)}
    for av in combos:
        c = B.composite(sheets, av)
        bb = {}
        for f in range(NF):
            a = c[:, f * 144:(f + 1) * 144, 3]
            ys, xs = np.nonzero(a > 8)
            bb[f] = (ys.min(), ys.max(), float((ys * a[ys, xs]).sum() / a[ys, xs].sum()))
            worst = [min(worst[0], xs.min()), min(worst[1], ys.min()), max(worst[2], xs.max()), max(worst[3], ys.max())]
            if f in (2, 3, 4, 5, 6, fi['prone'], fi['attack0'], fi['attack1']):
                foot_err = max(foot_err, abs(int(ys.max()) - 180))
        for n in ('jump', 'fall'):
            air[n] = [min(air[n][0], bb[fi[n]][1]), max(air[n][1], bb[fi[n]][1])]
            # 몸 중심 = 프레임 전체 불투명 픽셀의 알파 가중 평균 y
            center.append(abs(bb[fi[n]][2] - bb[2][2]))
        r = (180 - bb[fi['prone']][0]) / (180 - bb[2][0])
        if av['hat'] == 'none':
            ratio = [min(ratio[0], r), max(ratio[1], r)]
        else:
            ratio_hat = [min(ratio_hat[0], r), max(ratio_hat[1], r)]
        a = c[:, fi['prone'] * 144:(fi['prone'] + 1) * 144, 3].astype(float)
        pcx.append(float((a.sum(0) * np.arange(144)).sum() / a.sum()))
    ok(worst[0] >= 1 and worst[1] >= 1 and worst[2] <= 142 and worst[3] <= 190, '불투명(a>8) 범위 x %d..%d, y %d..%d (프리셋 12 + 무작위 40, 13프레임)' % (worst[0], worst[2], worst[1], worst[3]))
    ok(foot_err <= 10, '측면/걷기/엎드리기/공격 발 끝이 기준선 y=180 근처 (최대 차 %dpx)' % foot_err)
    ok(all(160 <= air[n][0] and air[n][1] <= 190 for n in air), 'jump/fall 발 끝 y: jump %d..%d, fall %d..%d (기준선 위로 뜰 수 있음, 아래로 190 이하)'
       % (air['jump'][0], air['jump'][1], air['fall'][0], air['fall'][1]))
    ok(max(center) <= 8, 'jump/fall 몸 중심(알파 가중 평균 y)이 side 와 비슷 (최대 차 %.1fpx <= 8)' % max(center))
    ok(0.35 <= ratio[0] and ratio[1] <= 0.45, 'prone 키 / side 키 (모자 없음) = %.2f..%.2f (0.35~0.45)' % tuple(ratio))
    ok(0.35 <= ratio_hat[0] and ratio_hat[1] <= 0.50, 'prone 키 / side 키 (모자 있음) = %.2f..%.2f (0.35~0.50)' % tuple(ratio_hat))
    ok(max(abs(x - 72) for x in pcx) <= 10, 'prone 몸 가로 중심 x = %.1f..%.1f (72 +-10)' % (min(pcx), max(pcx)))

    print('[6] 레이어 합성 vs 전체 렌더')
    rep = json.load(open(os.path.join(src, 'build_report.json')))['layer_vs_full']
    # Existing six are compared against the unchanged fine-pixel reference renders.
    # New presets require their own full renders; no composite is used as its own truth.
    for i, (lab, av) in enumerate(B.PRESETS):
        tp = os.path.join(src, 'truth', 'preset%d.png' % (i + 1))
        tr = np.array(Image.open(tp).convert('RGBA'))
        st = B.diff_stats(B.composite(sheets, av), tr)
        ok(st['mean_abs_rgb'] <= B.TOL_MEAN and st['alpha_mae'] <= B.TOL_ALPHA,
           'preset%d %s: 평균 %.2f (<=%.1f), p95 %.1f, 알파 %.2f (<=%.1f)' % (i + 1, lab, st['mean_abs_rgb'], B.TOL_MEAN, st['p95'], st['alpha_mae'], B.TOL_ALPHA))
    print('    build_report:', json.dumps(rep, ensure_ascii=False)[:200])

    if not fast:
        print('[7] 결정적 빌드 (임시 폴더에 다시 빌드)')
        with tempfile.TemporaryDirectory() as td:
            only = B.parse_only(sys.argv[sys.argv.index('--only') + 1]) if '--only' in sys.argv else None
            if only:
                shutil.copytree(AV, os.path.join(td, 'avatar'))
            B.build(os.path.join(td, 'avatar'), os.path.join(td, 'src'), jobs=3, truth=False, log=lambda *_: None, only=only)
            h1, h2 = hashes(AV), hashes(os.path.join(td, 'avatar'))
            diff = sorted(k for k in set(h1) | set(h2) if h1.get(k) != h2.get(k))
            ok(not diff, '%d개 파일 해시 동일 %s' % (len(h1), diff[:5]))

    print('\n결과:', '통과' if not fails else '실패 %d건' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
