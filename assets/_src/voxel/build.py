"""버섯마을 아바타 빌드 (복셀 아트 계약, 사이클 5 + 사이클 6 jump/fall 프레임 + 사이클 7 트렌디 비율 + 사이클 8 prone(엎드리기)/둥근 머리/shoes_under, 복셀 1칸 1.82px).

python3 assets/_src/voxel/build.py                     # assets/avatar/** 전체 재생성 + 검증용 정답 렌더
python3 assets/_src/voxel/build.py --preview DIR       # + 미리보기 (presets, parts_*, walk.gif, compare, ingame_scale)
python3 assets/_src/voxel/build.py --out DIR --src-out DIR   # 다른 폴더로 (check.py 결정성 검사용)
python3 assets/_src/voxel/build.py --manifest-only     # PNG는 건드리지 않고 manifest.json만 다시 씀 (files 는 디스크의 PNG 기준)
옵션: --jobs N (기본 2), --no-truth (정답 렌더 생략)

레이어 분리 규칙
  - 파츠 하나는 '마네킹(skin) + 그 파츠'만 놓고 렌더하고, 마네킹이 앞을 가리는 서브픽셀은 지운다(깊이 마스크).
  - AO/그림자는 '마네킹 + 그 파츠' 기준으로 굽는다. 다른 파츠에 드리우는 그림자는 shade_<part> 레이어로 따로 굽는다
    (마네킹 표면 조도의 '파츠 있음/없음' 비율, 모자는 머리카락 껍데기 근사 면 기준).
  - hair/top/hat 은 근사 프록시(옷 입은 몸 / 바지·신발 / 머리카락 껍데기)보다 뒤에 있는 서브픽셀을 *_back 레이어로 보낸다.
    프레임마다 자동이라 뒷머리, 양갈래, 망토, 모자 챙이 뷰에 따라 앞/뒤 레이어를 오간다.
"""
import os
import sys
import json
import time
import shutil
import hashlib
import numpy as np
from multiprocessing import Pool
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
from model import assemble, proxy_boxes, LABELS, PRESETS, CATS, PARTS  # noqa: E402
from vox import render, downsample, SS, UNIT  # noqa: E402

W, H = 144, 192
ANCHOR = (72, 180)
DENSITY = 1.5
SCALE = 1.82 / UNIT     # 시트 px / 복셀 1칸 (사이클 7: 2.75 -> 1.82, 사이클 10: 0.91)
PITCH = 15
FRAMES = ['front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back', 'jump', 'fall', 'prone', 'attack0', 'attack1']
YAW = {'front': -25, 'front_b': -25, 'back': 160}   # 사이클 7: 정면은 시안처럼 캐릭터 왼쪽에서 (25 -> -25)
SIDE_YAW = 62
LAYER_ORDER = [
    ('hair_back', 'hair', 'source-over'),
    ('top_back', 'top', 'source-over'),
    ('skin', 'skin', 'source-over'),
    ('face', 'face', 'source-over'),
    ('shoes_under', 'shoes', 'source-over'),      # 사이클 8: 양말/하이탑 발목 (하의 아래). 메인 승인 2026-10-28
    ('bottom', 'bottom', 'source-over'),
    ('shoes', 'shoes', 'source-over'),
    ('shade_top', 'top', 'source-atop'),
    ('top', 'top', 'source-over'),
    ('shade_hair', 'hair', 'source-atop'),
    ('hat_back', 'hat', 'source-over'),
    ('hair_front', 'hair', 'source-over'),
    ('shade_hat', 'hat', 'source-atop'),
    ('hat', 'hat', 'source-over'),
]
SPLIT = {'hair': ('body', 'hair_back', 'hair_front'), 'top': ('legs', 'top_back', 'top'), 'hat': ('hairshell', 'hat_back', 'hat')}
SHADE = {'hair': 'man', 'top': 'man', 'hat': 'man+shell'}
SHADE_RGB = (34, 26, 48)
SHADE_GAIN = {'hair': 0.65, 'top': 0.6, 'hat': 0.7}   # 사이클 7: 파츠별 (겹치는 그림자가 곱해져 과하게 어두워지는 것 보정, 0.9 -> 파츠별)
TOL_MEAN = 6.0          # 레이어 합성 vs 전체 렌더 허용치 (프리멀티 RGB 평균 절대차, /255)
TOL_ALPHA = 2.0

IRR0 = {}               # (frame, recv) -> (irr, hit) : 2단계 풀이 fork 로 물려받음


PITCH_OF = {'prone': 8}  # 사이클 8: 엎드리기는 카메라를 낮춰 정수리 윗면이 덜 보이게 (키 비율), model.FIT_VIEW 와 같아야 함


def yaw_of(fr):
    return YAW.get(fr, SIDE_YAW)


def R(boxes, fr, **kw):
    return render(boxes, yaw_of(fr), PITCH_OF.get(fr, PITCH), SCALE, W=W, H=H, anchor=ANCHOR, **kw)


# ------------------------------------------------------------------ 작업 (워커에서 실행)
def receivers(fr, recv):
    b = assemble({'skin': 'light'}, fr)
    if recv == 'man+shell':
        b = b + proxy_boxes('hairshell', fr)
    return b


def t_irr0(args):
    fr, recv = args
    b = receivers(fr, recv)
    r = R(b, fr)
    return (fr, recv), (r['irr'], r['hit'])


def t_layer(args):
    cat, pid, fr = args
    t = time.time()
    out = {}
    if cat == 'skin':
        r = R(assemble({'skin': pid}, fr), fr)
        out['skin'] = downsample(r['img'], r['a'])
        return args, out, time.time() - t
    b = assemble({'skin': 'light', cat: pid}, fr)
    man = [i for i, x in enumerate(b) if x.tag == 'skin']
    vis = [i for i, x in enumerate(b) if x.tag == cat]
    r = R(b, fr, vis=vis, mask=man)
    if cat in SPLIT:
        kind, Lb, Lf = SPLIT[cat]
        rp = R(proxy_boxes(kind, fr), fr, lighting=False)
        back = (r['a'] > 0) & (rp['zbuf'] < r['zbuf'] - 0.05)
        out[Lb] = downsample(r['img'], r['a'] * back)
        out[Lf] = downsample(r['img'], r['a'] * ~back)
    elif cat == 'shoes':
        # 사이클 8: under 표시 상자(양말 등)가 보이는 서브픽셀은 shoes_under 로 (하의 아래에 합성)
        und = np.array([b[i].layer.endswith('_under') for i in range(len(b))] + [False])
        under = (r['a'] > 0) & und[r['idb']]
        if under.any():
            out['shoes_under'] = downsample(r['img'], r['a'] * under)
        out['shoes'] = downsample(r['img'], r['a'] * ~under)
    else:
        out[cat] = downsample(r['img'], r['a'])
    if cat in SHADE:
        recv = SHADE[cat]
        rb = receivers(fr, recv)
        allb = rb + [b[i] for i in vis]
        r1 = R(allb, fr, vis=range(len(rb)))
        irr0, hit0 = IRR0[(fr, recv)]
        k = np.where(r1['hit'] & hit0, 1 - r1['irr'] / np.maximum(irr0, 1e-6), 0)
        k = np.clip(k, 0, 1) * SHADE_GAIN[cat]
        a = k.reshape(H, SS, W, SS).mean((1, 3))
        sh = np.zeros((H, W, 4), np.uint8)
        sh[..., :3] = SHADE_RGB
        sh[..., 3] = np.round(a * 255)
        sh[sh[..., 3] == 0] = 0
        out['shade_' + cat] = sh
    return args, out, time.time() - t


def t_full(args):
    outfit, fr = args
    t = time.time()
    r = R(assemble(outfit, fr), fr)
    return args, downsample(r['img'], r['a']), time.time() - t


# ------------------------------------------------------------------ 합성 (프런트 규칙과 같음)
def over(dst, src):
    sa = src[..., 3:4] / 255.0
    da = dst[..., 3:4] / 255.0
    oa = sa + da * (1 - sa)
    oc = np.where(oa > 0, (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-9), 0)
    return np.dstack([oc, oa * 255])


def atop(dst, src):
    sa = src[..., 3:4] / 255.0
    return np.dstack([dst[..., :3] * (1 - sa) + src[..., :3] * sa, dst[..., 3:4]])


def composite(sheets, outfit):
    """sheets: {(layer, id): (H, W*n, 4) uint8}."""
    acc = None
    for layer, part, blend in LAYER_ORDER:
        key = (layer, outfit.get(part))
        if key not in sheets:
            continue
        s = sheets[key].astype(float)
        if acc is None:
            acc = np.zeros_like(s)
        acc = atop(acc, s) if blend == 'source-atop' else over(acc, s)
    return np.clip(np.round(acc), 0, 255).astype(np.uint8)


def load_sheets(avatar_dir):
    sheets = {}
    for layer, part, _ in LAYER_ORDER:
        d = os.path.join(avatar_dir, layer)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.png'):
                sheets[(layer, f[:-4])] = np.array(Image.open(os.path.join(d, f)).convert('RGBA'))
    return sheets


def diff_stats(a, b):
    a = a.astype(float); b = b.astype(float)
    pa = a[..., :3] * a[..., 3:4] / 255; pb = b[..., :3] * b[..., 3:4] / 255
    d = np.abs(pa - pb).mean(-1)
    w = np.maximum(a[..., 3], b[..., 3]) / 255
    return dict(mean_abs_rgb=round(float((d * w).sum() / max(w.sum(), 1)), 3),
                p95=round(float(np.percentile(d[w > 0.05], 95)), 2),
                alpha_mae=round(float(np.abs(a[..., 3] - b[..., 3]).mean()), 3))


def save_png(arr, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr, 'RGBA').save(path, optimize=True)


def layer_files(avatar_dir):
    """레이어별 실제 PNG id 목록 (정렬). layerOrder 의 모든 레이어 키를 넣고, 파일이 없으면 빈 배열."""
    out = {}
    for layer, _, _ in LAYER_ORDER:
        d = os.path.join(avatar_dir, layer)
        out[layer] = sorted(f[:-4] for f in os.listdir(d) if f.endswith('.png')) if os.path.isdir(d) else []
    return out


def manifest(files):
    return {
        'frame': {'w': W, 'h': H},
        'anchor': {'x': ANCHOR[0], 'y': ANCHOR[1]},
        'density': DENSITY,
        'frames': FRAMES,
        'animations': {'idle_front': {'frames': [0, 1], 'ms': 600}, 'idle': {'frames': [2], 'ms': 600},
                       'walk': {'frames': [3, 4, 5, 6], 'ms': 150},
                       'jump': {'frames': [8], 'ms': 200}, 'fall': {'frames': [9], 'ms': 200},
                       'prone': {'frames': [10], 'ms': 200},
                       'attack': {'frames': [11, 12], 'ms': 120}},
        'layerOrder': [{'layer': l, 'part': p, 'blend': b} for l, p, b in LAYER_ORDER],
        'parts': {k: [{'id': i, 'label': lab} for i, lab in LABELS[k]] for k in CATS},
        'presets': [{'label': lab, 'avatar': av} for lab, av in PRESETS],
        'files': files,
    }


def write_manifest(out_dir):
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest(layer_files(out_dir)), fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def build(out_dir, src_out, jobs=2, truth=True, log=print):
    t0 = time.time()
    timing = {}
    tasks_irr = [(fr, recv) for fr in FRAMES for recv in ('man', 'man+shell')]
    with Pool(jobs) as p:
        for k, v in p.imap(t_irr0, tasks_irr):
            IRR0[k] = v
    timing['irr0_s'] = round(time.time() - t0, 1)
    tasks = [(cat, pid, fr) for cat in CATS for pid, _ in LABELS[cat] if pid != 'none' for fr in FRAMES]
    per = {}
    lt = []
    t1 = time.time()
    with Pool(jobs) as p:
        for (cat, pid, fr), res, dt in p.imap(t_layer, tasks, chunksize=1):
            per.setdefault((cat, pid), {})[fr] = res
            lt.append(dt)
    timing['layers_s'] = round(time.time() - t1, 1)
    timing['layer_task_mean_s'] = round(float(np.mean(lt)), 2)
    timing['layer_tasks'] = len(lt)

    sheets = {}
    empty = np.zeros((H, W, 4), np.uint8)
    for (cat, pid), frs in per.items():
        names = set().union(*[set(v) for v in frs.values()])
        for L in sorted(names):
            arr = np.concatenate([frs[fr].get(L, empty) for fr in FRAMES], axis=1)
            if arr[..., 3].any():
                sheets[(L, pid)] = arr
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    for (L, pid), arr in sorted(sheets.items()):
        save_png(arr, os.path.join(out_dir, L, pid + '.png'))
    write_manifest(out_dir)

    report = {}
    if truth:
        t2 = time.time()
        ft = [(av, fr) for _, av in PRESETS for fr in FRAMES]
        full = {}
        with Pool(jobs) as p:
            for (av, fr), im, dt in p.imap(t_full, ft, chunksize=1):
                full.setdefault(json.dumps(av, sort_keys=True), {})[fr] = im
        timing['truth_s'] = round(time.time() - t2, 1)
        os.makedirs(os.path.join(src_out, 'truth'), exist_ok=True)
        for i, (lab, av) in enumerate(PRESETS):
            tr = np.concatenate([full[json.dumps(av, sort_keys=True)][fr] for fr in FRAMES], axis=1)
            save_png(tr, os.path.join(src_out, 'truth', 'preset%d.png' % (i + 1)))
            report['preset%d' % (i + 1)] = diff_stats(composite(sheets, av), tr)
    timing['total_s'] = round(time.time() - t0, 1)
    timing['jobs'] = jobs
    os.makedirs(src_out, exist_ok=True)
    with open(os.path.join(src_out, 'build_report.json'), 'w') as fh:
        json.dump({'timing': timing, 'layer_vs_full': report}, fh, indent=2)
    log(json.dumps({'timing': timing, 'layer_vs_full': report}, indent=1))
    return sheets


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    out_dir = opt('--out', os.path.join(ROOT, 'assets', 'avatar'))
    src_out = opt('--src-out', os.path.join(HERE, 'out'))
    jobs = int(opt('--jobs', 2))
    if '--manifest-only' in a:
        write_manifest(out_dir)
        print('manifest.json 갱신:', os.path.join(out_dir, 'manifest.json'))
        return
    sheets = build(out_dir, src_out, jobs, truth='--no-truth' not in a)
    pv = opt('--preview')
    if pv:
        import preview
        preview.make_all(pv, sheets, jobs)


if __name__ == '__main__':
    main()
