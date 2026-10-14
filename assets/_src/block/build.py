"""버섯마을 블록 아트 빌드 (사이클 3 정본).

  python3 assets/_src/block/build.py                 assets/avatar/**, assets/map/** 전체 재생성
  python3 assets/_src/block/build.py --preview DIR   + 미리보기 PNG/GIF 를 DIR 에 (저장소 밖 권장)

결정적 출력: 난수 대신 좌표 해시 노이즈, 고정 순서. 같은 코드면 같은 PNG (check.py 가 md5 로 확인).
출력 폴더(assets/avatar, assets/map)는 빌드 때 비우고 다시 만든다.
"""
import os
import sys
sys.dont_write_bytecode = True
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))

import avatar   # noqa: E402
import mapgen   # noqa: E402


def build(root=ROOT):
    for sub in ('avatar', 'map'):
        d = os.path.join(root, 'assets', sub)
        if os.path.isdir(d):
            shutil.rmtree(d)
    manifest, sheets, outline = avatar.build(root)
    mman, mimgs = mapgen.build(root)
    return manifest, sheets, outline, mman, mimgs


def world_preview(sheets, outline, mimgs):
    from parts import PRESETS
    world = mapgen.compose_world(mimgs)
    xs = (120, 300, 470, 640, 860, 1060)
    frames = (1, 2, 0, 4, 1, 6)
    for (lb, av), x, fi in zip(PRESETS, xs, frames):
        comp = avatar.silhouette(avatar.compose(sheets, av), outline)
        fr = comp.crop((avatar.W * fi, 0, avatar.W * (fi + 1), avatar.H))
        world.alpha_composite(fr, (x - avatar.AX, mapgen.GROUND_Y - avatar.AY))
    return world


if __name__ == '__main__':
    manifest, sheets, outline, mman, mimgs = build()
    print('avatar sheets:', len(sheets), ' outline colors:', len(outline), ' map layers:', len(mman['layers']))
    if '--preview' in sys.argv:
        import preview
        d = sys.argv[sys.argv.index('--preview') + 1]
        preview.make(d, sheets, outline, world_preview(sheets, outline, mimgs))
        print('preview ->', d)
