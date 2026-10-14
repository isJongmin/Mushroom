"""Design draft: UI skin sprites from ASCII + login / game mobile mock."""
import sys, os
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from draft import PAL, rgb, compose
from map_draft import render_view, font

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

def from_ascii(rows, key):
    h = len(rows); w = len(rows[0])
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        assert len(r) == w, (y, r, len(r), w)
        for x, ch in enumerate(r):
            if ch != '.': im.putpixel((x, y), rgb(PAL[key[ch]]) + (255,))
    return im

# ---- panel 24x24, slice 8 ----
PANEL = [
 "..######################..",
]
def panel_rows():
    # build by rule: ring index i = min distance to edge
    W = H = 24
    rows = []
    for y in range(H):
        r = ''
        for x in range(W):
            # rounded corners: cut 2px stair
            cx = min(x, W - 1 - x); cy = min(y, H - 1 - y)
            if (cx == 0 and cy <= 1) or (cy == 0 and cx <= 1): r += '.'; continue
            if cx == 1 and cy == 1: r += 'D'; continue
            i = min(cx, cy)
            top_or_left = (y <= x and y < H - 1 - x) or (x < y and x < H - 1 - y)  # nearest edge is top or left
            nearest = min((y, 'T'), (H - 1 - y, 'B'), (x, 'L'), (W - 1 - x, 'R'))[1]
            if i == 0: ch = 'D'                       # outer line w4
            elif i == 1: ch = 'h' if nearest in 'TL' else 'm'   # w1 highlight / w3 shade
            elif i in (2, 3): ch = 'w'               # wood w2
            elif i == 4: ch = 'm'                    # w3
            elif i == 5: ch = 'D'                    # inner line w4
            elif i == 6: ch = 'c' if nearest in 'TL' else 'f'   # cream shadow c2 on top/left
            else: ch = 'f'                           # cream c1
            r += ch
        rows.append(r)
    # rivets
    rows = [list(r) for r in rows]
    for (x, y) in [(3, 3), (20, 3), (3, 20), (20, 20)]:
        rows[y][x] = 'y'
    return [''.join(r) for r in rows]
PANEL_KEY = {'D': 'w4', 'h': 'w1', 'm': 'w3', 'w': 'w2', 'c': 'c2', 'f': 'c1', 'y': 'y2'}

def button_rows(state, kind='primary'):
    W, H = 24, 24
    if kind == 'primary':
        line, hl, body, low, lip = 'w4', 'y1', 'y2', 'y3', 'y4'
        if state == 'hover': hl, body, low = 'white', 'y1', 'y2'
    else:
        line, hl, body, low, lip = 'w3', 'white', 'c1', 'c2', 'c3'
        if state == 'hover': body, low = 'white', 'c1'
    if state == 'disabled': line, hl, body, low, lip = 'c3', 'c1', 'c2', 'c2', 'c3'
    rows = []
    for y in range(H):
        r = []
        for x in range(W):
            cx = min(x, W - 1 - x)
            if (cx == 0 and (y == 0 or y >= H - 3)): r.append(None); continue
            if state == 'pressed':
                # no lip: content shifted down 2 -> rows 0..1 transparent
                if y < 2: r.append(None); continue
                yy = y - 2
                if cx == 0 and yy == 0: r.append(None); continue
                if yy == 0 or y == H - 1 or cx == 0: r.append(line); continue
                if yy == 1: r.append(lip); continue  # inner top shadow
                if y >= H - 3: r.append(low); continue
                r.append(body); continue
            if y == 0 or cx == 0 or y == H - 1: r.append(line); continue
            if y == 1: r.append(hl); continue
            if y >= H - 3: r.append(lip); continue      # 2px lip rows 21..22
            if y >= H - 6: r.append(low); continue
            r.append(body)
        rows.append(r)
    return rows

def rows_to_img(rows):
    H = len(rows); W = len(rows[0])
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for y in range(H):
        for x in range(W):
            if rows[y][x]: im.putpixel((x, y), rgb(PAL[rows[y][x]]) + (255,))
    return im

def nine(img, sl, w, h, P):
    """9-slice draw img (slice sl) to target size w x h (css px) at pixel scale P."""
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    iw, ih = img.size
    s = sl
    big = lambda box, tw, th: img.crop(box).resize((max(1, tw), max(1, th)), Image.NEAREST)
    S = s * P
    xs = [(0, s, 0, S), (s, iw - s, S, w - S), (iw - s, iw, w - S, w)]
    ys = [(0, s, 0, S), (s, ih - s, S, h - S), (ih - s, ih, h - S, h)]
    for (sx0, sx1, dx0, dx1) in xs:
        for (sy0, sy1, dy0, dy1) in ys:
            if dx1 > dx0 and dy1 > dy0:
                out.alpha_composite(big((sx0, sy0, sx1, sy1), dx1 - dx0, dy1 - dy0), (dx0, dy0))
    return out

def text(d, xy, s, f, fill, shadow=None):
    if shadow: d.text((xy[0] + 1, xy[1] + 1), s, font=f, fill=shadow)
    d.text(xy, s, font=f, fill=fill)

def logo(d, cx, y, f):
    s = '버섯마을'
    w = d.textlength(s, font=f)
    x = cx - w / 2
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2), (0, 4), (2, 4), (-2, 4)]:
        d.text((x + dx, y + dy), s, font=f, fill=PAL['w4'])
    d.text((x, y), s, font=f, fill=PAL['c1'])

def login_mock(vw, vh, P, path):
    viewW, viewH = vw // P, vh // P
    camY = 250 - viewH
    art = Image.new('RGBA', (viewW, viewH), rgb(PAL['k1']) + (255,))
    v = render_view(300, viewW, max(viewH, 270), 0)
    art.alpha_composite(v.crop((0, max(0, camY), viewW, max(0, camY) + viewH)), (0, max(0, -camY)))
    scr = art.resize((vw, vh), Image.NEAREST)
    d = ImageDraw.Draw(scr)
    mobile = vw < 720
    cw = vw - 32 if mobile else 360
    ch = 452
    x0 = (vw - cw) // 2
    y0 = 96 if mobile else (vh - ch) // 2 + 30
    f28 = font(28); f14 = font(14); f16 = font(16); f12 = font(12)
    logo(d, vw // 2, y0 - 60, f28)
    panel = from_ascii(panel_rows(), PANEL_KEY)
    scr.alpha_composite(nine(panel, 8, cw, ch, 2), (x0, y0))
    ix0 = x0 + 16 + 8; iw = cw - 48
    yy = y0 + 16 + 8
    text(d, (vw // 2 - d.textlength('친구들과 함께 노는 작은 마을', font=f14) / 2, yy), '친구들과 함께 노는 작은 마을', f14, PAL['w4'])
    yy += 32
    # tabs: two secondary buttons, active = primary
    bp = rows_to_img(button_rows('normal'))
    bs = rows_to_img(button_rows('normal', 'secondary'))
    tw = (iw - 8) // 2
    scr.alpha_composite(nine(bp, 8, tw, 40, 2), (ix0, yy))
    scr.alpha_composite(nine(bs, 8, tw, 40, 2), (ix0 + tw + 8, yy))
    text(d, (ix0 + tw / 2 - 20, yy + 9), '로그인', f16, PAL['ink'])
    text(d, (ix0 + tw + 8 + tw / 2 - 26, yy + 9), '회원가입', f16, PAL['w3'])
    yy += 56
    inp = from_ascii([
        "..wwwwwwww..",
        ".wccccccccw.",
        "wcWWWWWWWWcw",
        "wcWWWWWWWWcw",
        "wWWWWWWWWWWw",
        "wWWWWWWWWWWw",
        "wWWWWWWWWWWw",
        "wWWWWWWWWWWw",
        "wWWWWWWWWWWw",
        "wWWWWWWWWWWw",
        ".wWWWWWWWWw.",
        "..wwwwwwww..",
    ], {'w': 'w3', 'c': 'c3', 'W': 'white'})
    for label, help_ in [('아이디', '영문 소문자, 숫자, 밑줄 4~16자'), ('비밀번호', '8자 이상')]:
        text(d, (ix0, yy), label, f14, PAL['ink'])
        yy += 22
        scr.alpha_composite(nine(inp, 4, iw, 44, 2), (ix0, yy))
        yy += 48
        text(d, (ix0, yy), help_, f12, PAL['w3'])
        yy += 28
    yy += 4
    scr.alpha_composite(nine(bp, 8, iw, 48, 2), (ix0, yy))
    t = '로그인'
    text(d, (ix0 + iw / 2 - d.textlength(t, font=f16) / 2, yy + 11), t, f16, PAL['ink'])
    yy += 60
    # local mode footer inside panel
    t = 'LOCAL MODE · 이 브라우저에만 저장됩니다'
    text(d, (ix0 + iw / 2 - d.textlength(t, font=f12) / 2, yy), t, f12, PAL['w3'])
    scr.save(path)

if __name__ == '__main__':
    from_ascii(panel_rows(), PANEL_KEY).resize((24 * 8, 24 * 8), Image.NEAREST).save(os.path.join(OUT, 'panel-8x.png'))
    strip = Image.new('RGBA', (24 * 8 * 4 + 30, 24 * 8 * 2 + 10), (200, 200, 200, 255))
    for i, st in enumerate(['normal', 'hover', 'pressed', 'disabled']):
        strip.alpha_composite(rows_to_img(button_rows(st)).resize((192, 192), Image.NEAREST), (i * 200, 0))
        strip.alpha_composite(rows_to_img(button_rows(st, 'secondary')).resize((192, 192), Image.NEAREST), (i * 200, 200))
    strip.save(os.path.join(OUT, 'buttons-8x.png'))
    login_mock(960, 600, 2, os.path.join(OUT, 'login-desktop.png'))
    login_mock(360, 640, 2, os.path.join(OUT, 'login-mobile.png'))
    for r in panel_rows(): print(r)
    print('ok')
