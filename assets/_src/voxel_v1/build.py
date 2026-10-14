"""voxel_v1 빌드: 전체 렌더(정답) + 레이어별 렌더 + 그림자(shade) 레이어 + 합성 검증.

python3 assets/_src/voxel_v1/build.py [--preview DIR] [--quick]
출력: assets/_src/voxel_v1/out/
  full/<combo>.png              조합 전체를 한 번에 렌더한 정답 시트 (8프레임 768x128)
  layers/<layer>/<id>.png       레이어 시트 (같은 프레임 규격)
  layers/shade_<cat>/<id>.png   그 파츠가 마네킹에 드리우는 그림자 (RGB=그림자색, A=어두워짐 정도)
  manifest.json, timing.json
"""
import os
import sys
import json
import time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import assemble, CATS  # noqa: E402
from vox import render  # noqa: E402

W, H = 96, 128
ANCHOR = (48, 120)
SCALE = 2.1
PITCH = 15
FRAMES = ['front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back']
YAW = {'front': 25, 'front_b': 25, 'side': 62, 'back': 160}
LAYER_ORDER = ['hair_back', 'skin', 'face', 'bottom', 'shoes', 'shade_top', 'top', 'shade_hair', 'hair_front']
SHADE_CATS = ['hair', 'top']
SHADE_RGB = (34, 26, 48)

BASE = dict(skin='light', face='basic', hair='black-curly', top='hoodie-white', bottom='pants-black', shoes='sneakers-white')
COMBOS = {
    'A_curly_hoodie': BASE,
    'B_curly_tee': dict(BASE, top='tee-yellow'),
    'C_wavy_hoodie': dict(BASE, hair='brown-wavy'),
    'D_wavy_tee': dict(BASE, hair='brown-wavy', top='tee-yellow'),
}
OUT = os.path.join(HERE, 'out')


def yaw_of(fr):
    return YAW.get(fr, YAW['side'])


def frame_boxes(outfit, fr):
    return assemble(outfit, fr, back_view=(fr == 'back'))


def render_full(outfit, fr):
    b = frame_boxes(outfit, fr)
    return render(b, yaw_of(fr), PITCH, SCALE, W=W, H=H, anchor=ANCHOR)['rgba']


def render_layers(cat, pid, fr):
    """파츠 하나를 마네킹(skin)과 함께 렌더. 반환 {layer: rgba}."""
    out = {}
    if cat == 'skin':
        b = frame_boxes({'skin': pid}, fr)
        out['skin'] = render(b, yaw_of(fr), PITCH, SCALE, W=W, H=H, anchor=ANCHOR)['rgba']
        return out
    b = frame_boxes({'skin': BASE['skin'], cat: pid}, fr)
    man = [i for i, x in enumerate(b) if x.tag == 'skin']
    layers = sorted({x.layer for x in b if x.tag == cat})
    for L in layers:
        vis = [i for i, x in enumerate(b) if x.layer == L]
        out[L] = render(b, yaw_of(fr), PITCH, SCALE, vis=vis, mask=man, W=W, H=H, anchor=ANCHOR)['rgba']
    if cat in SHADE_CATS:
        out['shade_' + cat] = render_shade(b, man, fr)
    return out


def render_shade(b, man, fr):
    """마네킹 표면 조도: 파츠 있음/없음 비율 -> 어두워짐 알파."""
    r1 = render(b, yaw_of(fr), PITCH, SCALE, vis=man, occ=None, W=W, H=H, anchor=ANCHOR)
    r0 = render(b, yaw_of(fr), PITCH, SCALE, vis=man, occ=man, W=W, H=H, anchor=ANCHOR)
    k = np.where(r1['hit'], 1 - r1['irr'] / np.maximum(r0['irr'], 1e-6), 0)
    k = np.clip(k, 0, 1) * 0.9
    from vox import SS
    a = k.reshape(H, SS, W, SS).mean((1, 3))
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = SHADE_RGB
    rgba[..., 3] = np.round(a * 255)
    return rgba


# ------------------------------------------------------------------ 합성 (프런트가 할 일과 같은 규칙)
def over(dst, src):
    sa = src[..., 3:4] / 255.0
    da = dst[..., 3:4] / 255.0
    oa = sa + da * (1 - sa)
    oc = np.where(oa > 0, (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-9), 0)
    return np.dstack([oc, oa * 255])


def atop(dst, src):
    """source-atop: 기존 알파 유지, 색만 src 알파로 섞음 (그림자 레이어)."""
    sa = src[..., 3:4] / 255.0
    oc = dst[..., :3] * (1 - sa) + src[..., :3] * sa
    return np.dstack([oc, dst[..., 3:4]])


def composite(sheets, outfit):
    acc = np.zeros((H, sheets_width(sheets), 4))
    for L in LAYER_ORDER:
        cat = 'hair' if L.startswith('hair') else L.replace('shade_', '')
        pid = outfit.get(cat)
        key = (L, pid)
        if key not in sheets:
            continue
        s = sheets[key].astype(float)
        acc = atop(acc, s) if L.startswith('shade_') else over(acc, s)
    return np.clip(np.round(acc), 0, 255).astype(np.uint8)


def sheets_width(sheets):
    return next(iter(sheets.values())).shape[1]


def hstack(frames):
    return np.concatenate(frames, axis=1)


def save(arr, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr, 'RGBA').save(path, optimize=True)


def main():
    args = sys.argv[1:]
    preview = args[args.index('--preview') + 1] if '--preview' in args else None
    quick = '--quick' in args
    timing = {}
    combos = {'A_curly_hoodie': COMBOS['A_curly_hoodie']} if quick else COMBOS

    # 1) 정답(전체 렌더)
    full = {}
    for name, outfit in combos.items():
        fr_imgs = []
        for fr in FRAMES:
            t = time.time()
            fr_imgs.append(render_full(outfit, fr))
            timing.setdefault('full_frame_s', []).append(time.time() - t)
        full[name] = hstack(fr_imgs)
        save(full[name], os.path.join(OUT, 'full', name + '.png'))

    # 2) 레이어
    sheets = {}
    need = {}
    for outfit in combos.values():
        for cat in CATS:
            need.setdefault(cat, set()).add(outfit[cat])
    for cat in CATS:
        for pid in sorted(need[cat]):
            res_all = []
            for fr in FRAMES:
                t = time.time()
                res_all.append(render_layers(cat, pid, fr))
                timing.setdefault('layer_part_frame_s', []).append(time.time() - t)
            names = set().union(*res_all)
            if cat == 'hair':
                names |= {'hair_back', 'hair_front'}
            empty = np.zeros((H, W, 4), np.uint8)
            for L in names:
                sheets[(L, pid)] = hstack([r.get(L, empty) for r in res_all])
    for (L, pid), arr in sheets.items():
        save(arr, os.path.join(OUT, 'layers', L, pid + '.png'))

    # 3) 합성 검증
    report = {}
    comp = {}
    for name, outfit in combos.items():
        c = composite(sheets, outfit)
        comp[name] = c
        f = full[name].astype(float); g = c.astype(float)
        a = np.maximum(f[..., 3], g[..., 3]) / 255
        diff = np.abs(f[..., :3] * f[..., 3:4] / 255 - g[..., :3] * g[..., 3:4] / 255).mean(-1)
        report[name] = dict(mean_abs_rgb=float((diff * a).sum() / max(a.sum(), 1)),
                            p95=float(np.percentile(diff[a > 0.05], 95)),
                            alpha_mae=float(np.abs(f[..., 3] - g[..., 3]).mean()))
        save(c, os.path.join(OUT, 'composite', name + '.png'))
    tm = {k: dict(mean=round(float(np.mean(v)), 3), n=len(v)) for k, v in timing.items()}
    with open(os.path.join(OUT, 'timing.json'), 'w') as fh:
        json.dump(dict(timing=tm, layer_vs_full=report), fh, indent=2)
    write_manifest(sheets)
    print(json.dumps(dict(timing=tm, layer_vs_full=report), indent=1))
    if preview:
        import preview as pv
        pv.make_all(preview, full, comp, sheets, FRAMES)


def write_manifest(sheets):
    m = dict(frame=dict(w=W, h=H), anchor=dict(x=ANCHOR[0], y=ANCHOR[1]), displayScale=1,
             frames=FRAMES, yawDeg={fr: yaw_of(fr) for fr in FRAMES}, pitchDeg=PITCH, unitPx=SCALE,
             animations=dict(idle=dict(frames=[0, 1], ms=600), walk=dict(frames=[3, 4, 5, 6], ms=150)),
             layerOrder=LAYER_ORDER,
             blend={L: ('source-atop' if L.startswith('shade_') else 'source-over') for L in LAYER_ORDER},
             parts={}, sample=True)
    for (L, pid) in sorted(sheets):
        m['parts'].setdefault(L, []).append(pid)
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


if __name__ == '__main__':
    main()
