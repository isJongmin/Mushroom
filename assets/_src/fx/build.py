"""사이클 10 fx 빌드.

python3 assets/_src/fx/build.py           # 아이콘 5종, 구슬 시트, 속성 베기 3종 + 몬스터 manifest 갱신
python3 assets/_src/fx/build.py --check   # 기본 팔레트 베기가 assets/fx/slash.png와 같은지 확인

출력: assets/fx/buff/<id>.png, assets/fx/buff_orb.png, assets/fx/slash_{fire,ice,bolt}.png, assets/mob/manifest.json(fx·buffDrop)
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
FX_DIR = os.path.join(ROOT, 'assets', 'fx')
MANIFEST = os.path.join(ROOT, 'assets', 'mob', 'manifest.json')

import fx  # noqa: E402
import spec  # noqa: E402


def patch_manifest():
    """몬스터 manifest: drops 제거, buffDrop(+buffDropCount) 추가, fx 항목 추가. 나머지는 그대로."""
    with open(MANIFEST, encoding='utf-8') as f:
        m = json.load(f)
    for mid, mob in m['mobs'].items():
        mob.pop('drops', None)
        mob['buffDrop'] = spec.BUFF_DROP[mid]
        if mid in spec.BUFF_DROP_COUNT:
            mob['buffDropCount'] = spec.BUFF_DROP_COUNT[mid]
        else:
            mob.pop('buffDropCount', None)
    m.setdefault('fx', {}).update(spec.FX_MANIFEST)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main(argv):
    if '--check' in argv:
        a = np.asarray(fx.slash_sheet('base'), np.int16)
        b = np.asarray(Image.open(os.path.join(FX_DIR, 'slash.png')).convert('RGBA'), np.int16)
        print('slash 재현 최대 차이:', int(np.abs(a - b).max()))
        return
    os.makedirs(os.path.join(FX_DIR, 'buff'), exist_ok=True)
    for bid in spec.ITEMS:
        fx.icon(bid).save(os.path.join(FX_DIR, 'buff', f'{bid}.png'), optimize=True)
    print('icons ok')
    fx.orb_sheet().save(os.path.join(FX_DIR, 'buff_orb.png'), optimize=True)
    print('orb ok')
    for pal in ('fire', 'ice', 'bolt'):
        fx.slash_sheet(pal).save(os.path.join(FX_DIR, f'slash_{pal}.png'), optimize=True)
    print('slash ok')
    patch_manifest()
    print('manifest ok')


if __name__ == '__main__':
    main(sys.argv[1:])
