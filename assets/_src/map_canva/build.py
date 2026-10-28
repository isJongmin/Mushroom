"""버섯마을 사이클 10 맵 빌드: Canva 원본 그림 패널을 이어 붙여 지면 레이어(ground.webp)와 하늘(sky.png), manifest 를 만든다.

python3 assets/_src/map_canva/build.py --out DIR      # DIR 에 sky.png, ground.webp, manifest.json (src 경로는 assets/map/)
python3 assets/_src/map_canva/build.py --install      # assets/map/ 에 쓰고 옛 clouds/far/mid 를 지운다 (메인 지시 후)

처리 순서
1. 패널마다 UPSCALE 배로 키운다(LANCZOS). 지면 행(ground)이 모두 같은 높이가 되게 위아래로 맞춘다. 아래가 모자라면
   흙 단면 아래쪽 행을 거울로 이어 채운다.
2. 이음매: OVERLAP 만큼 겹쳐, 겹친 구간에서 색 차이가 가장 작은 세로 경로(DP)를 찾고 그 경로를 따라 섞는다. 섞는 폭은
   그 행의 차이가 작을수록(하늘, 원경) 넓게, 클수록(소품, 지면) 좁게. 오른쪽 패널 색은 겹친 구간 평균에 맞춰 보정한다.
3. 그림 위에 SKY_PAD_PX 만큼 하늘을 덧붙인다: 그림 맨 윗줄을 가로로 흐리게 한 색에서 위쪽 단색 하늘로 이어지는 그라데이션.
4. 맵 양 끝 EDGE_FADE px: 살짝 흐리고 옅게(대기 원근) 마감한다.
결정적: 난수 없음. 같은 입력이면 같은 바이트.
"""
import os, sys, json, argparse, shutil
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
import panels as PN

U, D = PN.UPSCALE, PN.DENSITY
SKY_PAD_PX = 212                 # 그림 위 하늘 (에셋 px). 중앙 패널 지면 행 790 → 월드 groundY = (212 + 987.5)/1.5 ≈ 800
WEBP_Q = 88


def load_panels():
    out = []
    for p in PN.PANELS:
        if not os.path.exists(p['file']) or p.get('ground') is None:
            continue
        im = Image.open(p['file']).convert('RGB')
        w, h = round(im.width * U), round(im.height * U)
        big = np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32)
        out.append(dict(p, img=big, g=p['ground'] * U, w0=im.width, h0=im.height))
    if not out:
        raise SystemExit('패널 없음')
    return out


def align_vertical(ps):
    G = max(p['g'] for p in ps)
    for p in ps:
        p['dy'] = int(round(G - p['g']))
    H = max(p['img'].shape[0] + p['dy'] for p in ps)
    for p in ps:
        im = p['img']
        top = p['dy']; bot = H - im.shape[0] - top
        if top:
            im = np.concatenate([np.repeat(im[:1], top, 0), im], 0)       # 위: 맨 윗줄 반복 (하늘 덧붙임에서 다시 덮음)
        if bot > 0:
            im = np.concatenate([im, im[-1:-bot - 1:-1]], 0)             # 아래: 흙 단면 거울
        p['img'] = im
    return int(round(G)), H


def seam_blend(A, B, ov):
    """A 오른쪽 ov 열과 B 왼쪽 ov 열이 겹친다. 반환: 이어 붙인 이미지."""
    H = A.shape[0]
    a = A[:, -ov:]; b = B[:, :ov].copy()
    # 색 보정: 겹친 구간 위쪽 절반 평균 비율로 B 전체를 맞추되, 이음매에서 멀어질수록 원래 색으로
    gain = (a[:H // 2].reshape(-1, 3).mean(0) + 1) / (b[:H // 2].reshape(-1, 3).mean(0) + 1)
    gain = np.clip(gain, 0.9, 1.1)
    ramp = np.clip(1 - np.arange(B.shape[1]) / 600.0, 0, 1)[None, :, None]
    B = B * (1 + (gain[None, None, :] - 1) * ramp)
    b = B[:, :ov]
    diff = ndimage.gaussian_filter(np.abs(a - b).mean(2), 2.0)
    # DP 세로 경로 (가운데 쪽 약한 선호)
    cost = diff + 0.15 * np.abs(np.arange(ov) - ov / 2)[None, :] / ov * diff.mean()
    acc = cost.copy(); back = np.zeros((H, ov), np.int16)
    for y in range(1, H):
        prev = acc[y - 1]
        l = np.concatenate([[np.inf], prev[:-1]]); r = np.concatenate([prev[1:], [np.inf]])
        st = np.stack([l, prev, r]); k = st.argmin(0)
        acc[y] = cost[y] + st[k, np.arange(ov)]
        back[y] = np.arange(ov) + k - 1
    s = np.zeros(H, int); s[-1] = int(acc[-1].argmin())
    for y in range(H - 1, 0, -1):
        s[y - 1] = back[y, s[y]]
    s = ndimage.gaussian_filter1d(s.astype(float), 3.0)
    rowd = ndimage.gaussian_filter1d(diff[np.arange(H), np.clip(s.astype(int), 0, ov - 1)], 6.0)
    fw = np.interp(rowd, [4, 30], [ov * 0.45, 6])       # 차이 작으면 넓게
    xs = np.arange(ov)[None, :]
    t = np.clip((xs - s[:, None]) / (2 * fw[:, None]) + 0.5, 0, 1)
    t = t * t * (3 - 2 * t)
    mid = a * (1 - t[..., None]) + b * t[..., None]
    return np.concatenate([A[:, :-ov], mid, B[:, ov:]], 1)


def compose(ps):
    Gpx, H = align_vertical(ps)
    ov = int(round(PN.OVERLAP * U))
    img = ps[0]['img']; ps[0]['x0'] = 0
    for p in ps[1:]:
        p['x0'] = img.shape[1] - ov
        img = seam_blend(img, p['img'], ov)
    return img, Gpx


def add_sky(img):
    H, W, _ = img.shape
    pad = SKY_PAD_PX
    row = img[:6].mean(0)                                    # 그림 맨 윗줄 색
    near = ndimage.gaussian_filter1d(row, 40, axis=0)
    far_ = ndimage.gaussian_filter1d(row, 600, axis=0, mode='nearest')
    top = np.array([150, 178, 200], np.float32)               # 하늘 맨 위 (더스티 블루)
    top = 0.5 * top + 0.5 * far_.mean(0) * np.array([0.92, 0.98, 1.04])
    t = ((np.arange(pad) + 0.5) / pad)[:, None, None]        # 0 = 맨 위, 1 = 그림 바로 위
    base = top[None, None, :] * (1 - t) + far_[None] * t
    s = np.clip((t - 0.78) / 0.22, 0, 1); s = s * s * (3 - 2 * s)
    pad_img = base * (1 - s) + near[None] * s
    # 그림 윗부분 몇 줄도 덧붙인 하늘과 섞어 이음매를 없앤다
    k = 24
    w = ((np.arange(k) + 0.5) / k)[:, None, None]
    img = img.copy()
    img[:k] = near[None] * (1 - w) + img[:k] * w
    out = np.concatenate([pad_img, img], 0)
    # 8비트 띠 방지 디더 (결정적)
    bay = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5
    yy, xx = np.mgrid[0:pad, 0:W]
    out[:pad] += bay[yy % 4, xx % 4][..., None] * 0.9
    return out, top


def edge_fade(img):
    n = PN.EDGE_FADE
    if n <= 0:
        return img
    blur = ndimage.gaussian_filter(img[:, :n * 2], (1.5, 1.5, 0))
    blurR = ndimage.gaussian_filter(img[:, -n * 2:], (1.5, 1.5, 0))
    haze = np.array([214, 206, 196], np.float32)
    x = (np.arange(n) + 0.5) / n
    f = (1 - x) ** 2                                          # 끝에서 1 → 안쪽 0
    img = img.copy()
    L = img[:, :n] * (1 - 0.35 * f[None, :, None]) + (0.6 * blur[:, :n] + 0.4 * haze) * 0.35 * f[None, :, None]
    R = img[:, -n:] * (1 - 0.35 * f[::-1][None, :, None]) + (0.6 * blurR[:, -n:] + 0.4 * haze) * 0.35 * f[::-1][None, :, None]
    img[:, :n] = L; img[:, -n:] = R
    return img


def geometry(ps, Gpx):
    """월드 단위 platforms / spawns / spawn / 크기."""
    pf, sp = [], []
    spawn = None
    for p in ps:
        tx = lambda x, p=p: (p['x0'] + x * U) / D
        ty = lambda y, p=p: (SKY_PAD_PX + p['dy'] + y * U) / D
        for (pid, x1, x2, y) in p['platforms']:
            pf.append(dict(id=pid, x1=int(round(tx(x1))), x2=int(round(tx(x2))), y=int(round(ty(y)))))
        for (sid, plat, x1, x2, mobs, mx) in p['spawns']:
            sp.append(dict(id=sid, platform=plat, x1=int(round(tx(x1))), x2=int(round(tx(x2))), mobs=list(mobs), max=mx))
        if p.get('spawn_x') is not None and spawn is None:
            spawn = dict(x=int(round(tx(p['spawn_x']))), y=None)
    groundY = int(round((SKY_PAD_PX + Gpx) / D))
    if spawn is None:
        spawn = dict(x=None, y=None)
    spawn['y'] = groundY
    return pf, sp, spawn, groundY


def build(out_dir, src_prefix='assets/map/'):
    ps = load_panels()
    img, Gpx = compose(ps)
    img = edge_fade(img)
    full, top = add_sky(img)
    H, W, _ = full.shape
    rgb = np.clip(np.round(full), 0, 255).astype(np.uint8)
    os.makedirs(out_dir, exist_ok=True)
    g = Image.fromarray(rgb, 'RGB')
    g.save(os.path.join(out_dir, 'ground.webp'), format='WEBP', quality=WEBP_Q, method=6)
    # 하늘: 덧붙인 하늘 맨 위 색 → 그림 평균 하늘 (카메라가 월드 위로 넘칠 때만 보인다, stretchX)
    col = full[:, :, :].mean(1)
    sky = np.repeat(col[:, None, :], 16, 1)
    Image.fromarray(np.clip(np.round(sky), 0, 255).astype(np.uint8), 'RGB').convert('RGBA').save(
        os.path.join(out_dir, 'sky.png'), optimize=True)
    pf, sp, spawn, groundY = geometry(ps, Gpx)
    man = dict(
        density=D, width=round(W / D, 3), height=round(H / D, 3), groundY=groundY, spawn=spawn,
        layers=[
            dict(name='sky', src=src_prefix + 'sky.png', parallax=0.0, y=0, w=round(16 / D, 3), h=round(H / D, 3),
                 repeatX=False, stretchX=True),
            dict(name='ground', src=src_prefix + 'ground.webp', parallax=1.0, y=0, w=round(W / D, 3),
                 h=round(H / D, 3), repeatX=False),
        ],
        platforms=pf, spawns=sp,
        source=dict(panels=[p['name'] for p in ps], upscale=U, skyPadPx=SKY_PAD_PX, overlapPx=PN.OVERLAP),
    )
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write('\n')
    tot = sum(os.path.getsize(os.path.join(out_dir, f)) for f in ('ground.webp', 'sky.png', 'manifest.json'))
    print('panels %s  ground %dx%d px  world %.1f x %.1f  groundY %d  platforms %d  spawns %d  total %.2f MB' % (
        [p['name'] for p in ps], W, H, W / D, H / D, groundY, len(pf), len(sp), tot / 1048576))
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--install', action='store_true')
    a = ap.parse_args()
    if a.install:
        out = os.path.join(ROOT, 'assets', 'map')
        build(out)
        for f in ('clouds.webp', 'far.webp', 'mid.webp'):
            if os.path.exists(os.path.join(out, f)):
                os.remove(os.path.join(out, f))
    elif a.out:
        build(a.out)
    else:
        ap.error('--out DIR 또는 --install')


if __name__ == '__main__':
    main()
