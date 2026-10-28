"""out/avatar -> assets/avatar 설치 (메인 허락 후에만 실행).

python3 assets/_src/art2d/install.py               # 설치 + check.py --fast
python3 assets/_src/art2d/install.py --dry-run     # 무엇을 지우고 복사하는지만 출력
python3 assets/_src/art2d/install.py --remove-voxel  # 설치 후 assets/_src/voxel/ 폴더도 삭제 (복셀 원본은 git 이력)

assets/avatar 안의 옛 복셀 파일(레이어 폴더 전부, manifest.json)을 지우고 out/avatar 를 그대로 복사한다.
"""
import os
import sys
import json
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(HERE, 'out', 'avatar')
DST = os.path.join(ROOT, 'assets', 'avatar')
VOXEL = os.path.join(ROOT, 'assets', '_src', 'voxel')


def main(argv):
    dry = '--dry-run' in argv
    m = json.load(open(os.path.join(SRC, 'manifest.json'), encoding='utf-8'))
    assert len(m['frames']) == 13 and m['frame'] == {'w': 144, 'h': 192}, 'out/avatar manifest 이상'
    old = sorted(os.listdir(DST)) if os.path.isdir(DST) else []
    print('지울 것 (assets/avatar):', old)
    print('복사할 것 (out/avatar):', sorted(os.listdir(SRC)))
    if dry:
        return 0
    for n in old:
        p = os.path.join(DST, n)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copytree(SRC, DST, dirs_exist_ok=True)
    if '--remove-voxel' in argv and os.path.isdir(VOXEL):
        shutil.rmtree(VOXEL)
        print('assets/_src/voxel 삭제')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), '--fast'])
    return r.returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
