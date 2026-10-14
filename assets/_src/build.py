"""버섯마을 픽셀아트 에셋 빌드. 사용: python3 assets/_src/build.py [avatar|map|ui ...]
인자를 생략하면 전부 다시 만든다. 결정적이다 (난수는 고정 시드, 같은 입력 -> 같은 PNG).
마지막에 check.py 검사를 실행한다."""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ASSETS = os.path.abspath(os.path.join(HERE, '..'))


def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main(targets):
    n = 0
    if 'avatar' in targets:
        import avatar
        files = avatar.build(os.path.join(ASSETS, 'avatar'))
        write_json(os.path.join(ASSETS, 'avatar', 'manifest.json'), avatar.manifest())
        n += len(files)
        print(f'avatar: {len(files)} sheets')
    if 'map' in targets:
        import mapgen
        files = mapgen.build(os.path.join(ASSETS, 'map'))
        write_json(os.path.join(ASSETS, 'map', 'manifest.json'), mapgen.manifest())
        n += len(files)
        print(f'map: {len(files)} layers')
    if 'ui' in targets:
        import ui
        files = ui.build(os.path.join(ASSETS, 'ui'))
        write_json(os.path.join(ASSETS, 'ui', 'manifest.json'), ui.manifest())
        n += len(files)
        print(f'ui: {len(files)} skins')
    import check
    ok = check.run()
    print(f'built {n} png, check {"OK" if ok else "FAILED"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:] or ['avatar', 'map', 'ui']))
