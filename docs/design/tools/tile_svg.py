"""맵 지면 PNG에서 16x16 타일을 잘라 ui-kit.css 의 --tile-grass, --tile-dirt 값(SVG 데이터 URI) 출력.

사용: python3 docs/design/tools/tile_svg.py [assets/map/ground.png]
출력 두 줄을 docs/design/ui-kit.css 1.6절의 같은 변수 자리에 붙여 넣는다.
자르는 위치 (ground.png 이미지 좌표, 소품/돌 없는 곳):
  잔디: x 32-47, 행 158-173  (아트 y 218 = 잔디 윗면 첫 행, 매니페스트 ground y 60)
  흙:   x 112-127, 행 174-189
아트가 ground.png 를 바꾸면 다시 실행하고, 잘린 곳에 소품/돌이 걸리지 않았는지 확인한다.
가로로 같은 색이 이어지는 픽셀을 rect 하나로 묶는다. 투명 픽셀은 건너뛴다.
"""
import sys
from PIL import Image

CROPS = {'--tile-grass': (32, 158, 48, 174), '--tile-dirt': (112, 174, 128, 190)}


def svg_uri(im):
    w, h = im.size
    px = im.load()
    rects = []
    for y in range(h):
        x = 0
        while x < w:
            c = px[x, y]
            x2 = x
            while x2 < w and px[x2, y] == c:
                x2 += 1
            if c[3]:
                rects.append("<rect x='%d' y='%d' width='%d' height='1' fill='%%23%02X%02X%02X'/>" % (x, y, x2 - x, c[0], c[1], c[2]))
            x = x2
    return ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' "
            "shape-rendering='crispEdges'>%s</svg>" % (w, h, ''.join(rects)))


if __name__ == '__main__':
    src = Image.open(sys.argv[1] if len(sys.argv) > 1 else 'assets/map/ground.png').convert('RGBA')
    for name, box in CROPS.items():
        print('  %s: url("%s");' % (name, svg_uri(src.crop(box))))
