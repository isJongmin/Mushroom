"""사이클 9 아바타 빌드 (2D 메이플풍).

python3 assets/_src/art2d/build.py [--jobs N] [--only key:id,...]

출력 (모두 assets/_src/art2d/out/ 아래, assets/avatar 는 install.py 가 옮긴다)
  out/avatar/<layer>/<id>.png    13프레임 시트 1872x192
  out/avatar/icon/<key>/<id>.png 64x64 아이콘 (투명)
  out/avatar/manifest.json
  out/truth/presetN.png          프리셋 합성 정답 (프런트 합성과 같은 규칙)
결정적: 같은 입력이면 같은 바이트.
"""
import os
import sys
import json
import time
import shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(HERE, 'out')

import raster as R  # noqa: E402
from rig import Ctx, FRAMES  # noqa: E402
import parts  # noqa: E402
from compose import LAYER_ORDER, compose  # noqa: E402
import hair, tops, bottoms, shoes, hats, body  # noqa: E402

FW, FH = R.FW, R.FH
NF = len(FRAMES)

LABELS = {
    'skin': [('light', '밝은 피부'), ('medium', '보통 피부'), ('dark', '진한 피부')],
    'face': [('basic', '기본'), ('smile', '웃음'), ('wink', '윙크'), ('sleepy', '졸린 눈')],
    'hair': [('ash-twoblock', '애쉬브라운 투블럭'), ('black-seethrough', '시스루뱅 긴 흑발'), ('black-wolfcut', '검은 울프컷'),
             ('pink-bridge-ponytail', '핑크 브릿지 포니테일'), ('black-short', '검은 짧은 머리'), ('brown-short', '밤색 짧은 머리'),
             ('blonde-spiky', '금발 뻗친 머리'), ('pink-long', '분홍 긴 머리'), ('sky-bob', '하늘색 단발'),
             ('tan-ponytail', '갈색 포니테일'), ('black-twintail', '검은 양갈래'), ('mint-curly', '민트 곱슬')],
    'top': [('hoodie-lavender', '라벤더 오버핏 후드'), ('cardigan-cream', '크림 가디건과 숄더백'), ('varsity-navy', '네이비 바시티 재킷'),
            ('puffer-mint', '민트 크롭 패딩과 크로스백'), ('hoodie-black', '검은 후드티'), ('hoodie-white', '흰 후드티'),
            ('blouse-white', '흰 블라우스'), ('overalls-green', '초록 멜빵'), ('tee-stripe-red', '빨간 줄무늬 티'),
            ('cape-blue', '파란 망토 셔츠'),
            ('slime-hood', '슬라임 젤리 후드', True), ('bat-cape', '박쥐 날개 상의', True), ('golem-armor', '골렘 돌갑옷', True)],
    'bottom': [('denim-wide', '연청 와이드 데님'), ('skirt-check', '체크 플리츠 스커트'), ('cargo-black', '검정 카고 조거'),
               ('cargo-beige', '베이지 와이드 카고'), ('pants-navy', '남색 바지'), ('pants-black', '검은 바지'),
               ('skirt-pink', '분홍 치마'), ('shorts-brown', '갈색 반바지'), ('jeans-blue', '청바지'),
               ('mushroom-shorts', '주황버섯 반바지', True), ('slime-pants', '슬라임 젤리 바지', True)],
    'shoes': [('chunky-white', '흰 청키 스니커즈'), ('loafer-socks', '로퍼와 니삭스'), ('hightop-black', '검정 하이탑'),
              ('sneakers-white', '흰 운동화'), ('maryjane-red', '빨간 메리제인'), ('boots-brown', '갈색 부츠'),
              ('sneakers-black', '검은 운동화'),
              ('snail-boots', '달팽이 부츠', True), ('bat-boots', '박쥐 날개 부츠', True)],
    'hat': [('none', '없음'), ('bucket-white', '흰 버킷햇'), ('cap-black', '검정 무지 캡'), ('cap-white', '흰 야구모자'),
            ('mushroom-red', '빨간 버섯 모자'), ('explorer-brown', '갈색 탐험가 모자'), ('beanie-yellow', '노란 비니'),
            ('ribbon-pink', '분홍 리본'),
            ('snail-shell', '달팽이 껍질 모자', True), ('mushroom-cap', '주황버섯 갓 모자', True), ('golem-helm', '골렘 돌투구', True)],
}
KEYS = ['skin', 'face', 'hair', 'top', 'bottom', 'shoes', 'hat']

PRESETS = [
    ('라벤더 후드', dict(skin='light', hair='ash-twoblock', face='basic', top='hoodie-lavender', bottom='denim-wide', shoes='chunky-white', hat='bucket-white')),
    ('가디건 걸', dict(skin='light', hair='black-seethrough', face='basic', top='cardigan-cream', bottom='skirt-check', shoes='loafer-socks', hat='none')),
    ('바시티 캡', dict(skin='light', hair='black-wolfcut', face='basic', top='varsity-navy', bottom='cargo-black', shoes='hightop-black', hat='cap-black')),
    ('민트 패딩', dict(skin='light', hair='pink-bridge-ponytail', face='basic', top='puffer-mint', bottom='cargo-beige', shoes='chunky-white', hat='none')),
    ('분홍 소녀', dict(skin='light', hair='pink-long', face='basic', top='blouse-white', bottom='skirt-pink', shoes='maryjane-red', hat='none')),
    ('버섯 꼬마', dict(skin='light', hair='blonde-spiky', face='basic', top='overalls-green', bottom='jeans-blue', shoes='boots-brown', hat='mushroom-red')),
]

ANIMATIONS = {
    'idle_front': {'frames': [0, 1], 'ms': 600},
    'idle': {'frames': [2], 'ms': 600},
    'walk': {'frames': [3, 4, 5, 6], 'ms': 150},
    'jump': {'frames': [8], 'ms': 200},
    'fall': {'frames': [9], 'ms': 200},
    'prone': {'frames': [10], 'ms': 200},
    'attack': {'frames': [11, 12], 'ms': 120},
}


def all_items():
    out = []
    for k in KEYS:
        for e in LABELS[k]:
            if e[0] != 'none':
                out.append((k, e[0]))
    return out


# ------------------------------------------------------------------ 렌더
def render_item(key, pid):
    """파츠 하나 -> {layer: [Layer x 13]}"""
    res = {}
    for i, f in enumerate(FRAMES):
        ctx = Ctx(f)
        parts.draw_part(ctx, key, pid)
        for name, L in ctx.layers.items():
            if not L.used:
                continue
            res.setdefault(name, [None] * NF)[i] = L
    return res


def sheet_of(frames):
    S = Image.new('RGBA', (FW * NF, FH), (0, 0, 0, 0))
    for i, L in enumerate(frames):
        if L is not None:
            S.paste(L.image(), (FW * i, 0))
    return S


def save_png(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


def _job(args):
    key, pid, out_av = args
    res = render_item(key, pid)
    layers = {}
    for name, frames in res.items():
        part = dict((l, p) for l, p, b in LAYER_ORDER).get(name)
        assert part == key, (name, key)
        im = sheet_of(frames)
        if im.getbbox() is None:
            continue
        save_png(im, os.path.join(out_av, name, pid + '.png'))
        layers[name] = True
    icon = make_icon(key, pid, res)
    save_png(icon, os.path.join(out_av, 'icon', key, pid + '.png'))
    return key, pid, sorted(layers)


# ------------------------------------------------------------------ 아이콘
ICON = 64


def _ss_image(L):
    b = L.buf
    a = b[..., 3:4]
    c = np.where(a > 1e-6, b[..., :3] / np.maximum(a, 1e-6), 0)
    return np.concatenate([np.clip(c, 0, 1), np.clip(a, 0, 1)], -1)


def _over(dst, src, atop=False):
    from compose import over
    return over(dst, src, atop)


def make_icon(key, pid, res):
    """아이콘: 정면(신발은 옆) 한 프레임을 슈퍼샘플 해상도에서 합성 -> 잘라서 64x64 안에 맞춤."""
    fi = FRAMES.index('side') if key == 'shoes' else 0
    base = {}
    if key in ('face', 'hair'):
        ctx = Ctx(FRAMES[fi])
        body.skin(ctx, 'light')
        if key == 'hair':
            body.face(ctx, 'basic')
        for n in ('head', 'face'):
            if n in ctx.layers:
                base[n] = ctx.layers[n]
    if key == 'skin':
        ctx = Ctx(FRAMES[fi])
        body.face(ctx, 'basic')
        base['face'] = ctx.layers['face']
    acc = None
    for name, part, blend in LAYER_ORDER:
        L = None
        if name in base:
            L = base[name]
        elif name in res and res[name][fi] is not None:
            L = res[name][fi]
        if L is None:
            continue
        if key in ('face', 'hair', 'skin') and name in ('skin_far', 'skin', 'skin_near', 'top', 'top_near', 'top_far'):
            pass
        im = _ss_image(L)
        acc = im if acc is None else _over(acc, im, blend == 'source-atop')
    img = Image.fromarray((np.clip(acc, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
    # 머리 계열은 머리 부분만 (어깨 위)
    if key in ('skin', 'face', 'hair'):
        a = np.asarray(img)[..., 3]
        ys = np.where(a.max(1) > 10)[0]
        top = ys.min()
        hh = int(80 * R.SS)
        img = img.crop((0, max(0, top - 4), img.width, min(img.height, top + hh)))
    bb = img.getbbox()
    img = img.crop(bb)
    w, h = img.size
    k = (ICON - 6) / max(w, h)
    nw, nh = max(1, round(w * k)), max(1, round(h * k))
    img = img.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', (ICON, ICON), (0, 0, 0, 0))
    out.alpha_composite(img, ((ICON - nw) // 2, (ICON - nh) // 2))
    return out


# ------------------------------------------------------------------ manifest / truth
def manifest(files):
    parts_ = {}
    for k in KEYS:
        lst = []
        for e in LABELS[k]:
            d = {'id': e[0], 'label': e[1]}
            if len(e) > 2 and e[2]:
                d['drop'] = True
            lst.append(d)
        parts_[k] = lst
    return {
        'frame': {'w': FW, 'h': FH},
        'anchor': {'x': R.AX, 'y': R.AY},
        'density': 1.5,
        'frames': FRAMES,
        'animations': ANIMATIONS,
        'layerOrder': [{'layer': l, 'part': p, 'blend': b} for l, p, b in LAYER_ORDER],
        'parts': parts_,
        'presets': [{'label': lb, 'avatar': av} for lb, av in PRESETS],
        'files': {l: sorted(files.get(l, [])) for l, p, b in LAYER_ORDER if files.get(l)},
    }


def compose_sheet(av_dir, av, files=None):
    def get(layer, part):
        pid = av.get(part)
        if pid is None or pid == 'none':
            return None
        p = os.path.join(av_dir, layer, pid + '.png')
        if files is not None and pid not in files.get(layer, []):
            return None
        return Image.open(p) if os.path.exists(p) else None
    return compose(get)


def build(jobs=2, only=None, log=print):
    out_av = os.path.join(OUT, 'avatar')
    t0 = time.time()
    if only is None and os.path.isdir(out_av):
        shutil.rmtree(out_av)
    items = all_items() if only is None else only
    args = [(k, p, out_av) for k, p in items]
    if jobs > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(jobs) as pool:
            results = pool.map(_job, args, chunksize=1)
    else:
        results = [_job(a) for a in args]
    files = {}
    if only is not None and os.path.exists(os.path.join(out_av, 'manifest.json')):
        files = {k: list(v) for k, v in json.load(open(os.path.join(out_av, 'manifest.json')))['files'].items()}
        for k, p, lays in results:
            for l in files:
                if p in files[l] and dict((a, b) for a, b, c in LAYER_ORDER)[l] == k:
                    files[l].remove(p)
    for k, p, lays in results:
        for l in lays:
            files.setdefault(l, []).append(p)
    m = manifest(files)
    with open(os.path.join(out_av, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write('\n')
    td = os.path.join(OUT, 'truth')
    os.makedirs(td, exist_ok=True)
    for i, (lb, av) in enumerate(PRESETS):
        save_png(compose_sheet(out_av, av, m['files']), os.path.join(td, 'preset%d.png' % (i + 1)))
    log('build %d items in %.1fs' % (len(items), time.time() - t0))
    return m


if __name__ == '__main__':
    a = sys.argv[1:]
    jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 2
    only = None
    if '--only' in a:
        only = [tuple(s.split(':')) for s in a[a.index('--only') + 1].split(',')]
    build(jobs, only)
