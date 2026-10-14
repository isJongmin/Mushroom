"""UI 스킨 19개 (style-guide v2.0 7장). 정본 ASCII 격자(data/ui_*.txt)와 버튼 틀 규칙(7.3)으로 만든다."""
import os
from PIL import Image
from palette import rgba

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def grid(name):
    rows = [l for l in open(os.path.join(DATA, name), encoding='utf-8').read().split('\n') if l]
    w = len(rows[0])
    assert all(len(r) == w for r in rows), name
    return rows


def img(rows, key):
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != '.':
                im.putpixel((x, y), rgba(key[ch]))
    return im


def button_rows(pressed=False):
    W = 24
    edge = '.' + 'L' * 22 + '.'
    def row(ch): return 'L' + ch * 22 + 'L'
    if not pressed:
        return [edge, row('H')] + [row('B')] * 16 + [row('D')] * 3 + [row('P')] * 2 + [edge]
    return ['.' * W] * 2 + [edge, row('P')] + [row('B')] * 17 + [row('D')] * 2 + [edge]


BUTTONS = {  # file: (pressed, L, H, B, D, P)  style-guide 7.3 표
    'button-primary-normal': (False, 'w4', 'y1', 'y2', 'y3', 'y4'),
    'button-primary-hover': (False, 'w4', 'white', 'y1', 'y2', 'y4'),
    'button-primary-pressed': (True, 'w4', None, 'y2', 'y3', 'y4'),
    'button-primary-disabled': (False, 'c3', 'c1', 'c2', 'c2', 'c3'),
    'button-secondary-normal': (False, 'w3', 'white', 'c1', 'c2', 'c3'),
    'button-secondary-hover': (False, 'w3', 'white', 'white', 'c1', 'c3'),
    'button-secondary-pressed': (True, 'w3', None, 'c1', 'c2', 'c3'),
}


def skins():
    out = {}
    out['panel'] = img(grid('ui_panel.txt'), {'D': 'w4', 'h': 'w1', 'w': 'w2', 'm': 'w3', 'c': 'c2', 'f': 'c1', 'y': 'y2'})
    for name, (pr, L, H, B, D, P) in BUTTONS.items():
        key = {'L': L, 'B': B, 'D': D, 'P': P}
        if H:
            key['H'] = H
        out[name] = img(button_rows(pr), key)
    n, f = grid('ui_input_normal.txt'), grid('ui_input_focus.txt')
    out['input-normal'] = img(n, {'O': 'w3', 's': 'c3', 'W': 'white'})
    out['input-focus'] = img(f, {'O': 'u3', 'u': 'u1', 'W': 'white'})
    out['input-error'] = img(f, {'O': 'r3', 'u': 'r1', 'W': 'white'})
    out['input-disabled'] = img(n, {'O': 'c3', 's': 'c2', 'W': 'c2'})
    out['chip'] = img(grid('ui_chip.txt'), {'O': 'w3', 'H': 'white', 'B': 'c1', 'S': 'c2'})
    bk = {'O': 'hb2', 'W': 'white', 'c': 'c2'}
    out['bubble'] = img(grid('ui_bubble.txt'), bk)
    out['bubble-tail'] = img(grid('ui_bubble_tail.txt'), bk)
    lab = grid('ui_label.txt')
    out['label-other'] = img(lab, {'O': 'ink', 'H': 'hb1', 'B': 'hb2'})
    out['label-self'] = img(lab, {'O': 'y4', 'H': 'y2', 'B': 'y3'})
    out['icon-mushroom'] = img(grid('ui_icon_mushroom.txt'), {'O': 'r3', 'R': 'r2', 'W': 'c1', 'S': 'w3', 'C': 'c1'})
    out['icon-arrow'] = img(grid('ui_icon_arrow.txt'), {'X': 'w4'})
    return out


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for name, im in skins().items():
        p = os.path.join(out_dir, name + '.png')
        im.save(p, optimize=True)
        files.append(p)
    return files


def manifest():
    u = lambda n: f'assets/ui/{n}.png'
    return {
        'scale': 2,
        'nine': {
            'panel': {'src': u('panel'), 'slice': [8, 8, 8, 8]},
            'button-primary': {'states': {s: u('button-primary-' + s) for s in ('normal', 'hover', 'pressed', 'disabled')},
                               'slice': [8, 8, 8, 8], 'pressedShift': 2},
            'button-secondary': {'states': {'normal': u('button-secondary-normal'), 'hover': u('button-secondary-hover'),
                                            'pressed': u('button-secondary-pressed'), 'disabled': u('button-primary-disabled')},
                                 'slice': [8, 8, 8, 8], 'pressedShift': 2},
            'input': {'states': {s: u('input-' + s) for s in ('normal', 'focus', 'error', 'disabled')}, 'slice': [4, 4, 4, 4]},
            'chip': {'src': u('chip'), 'slice': [3, 3, 3, 3]},
            'bubble': {'src': u('bubble'), 'slice': [4, 4, 4, 4]},
            'label-other': {'src': u('label-other'), 'slice': [3, 3, 3, 3]},
            'label-self': {'src': u('label-self'), 'slice': [3, 3, 3, 3]},
        },
        'sprites': {'bubble-tail': u('bubble-tail'), 'icon-mushroom': u('icon-mushroom'), 'icon-arrow': u('icon-arrow')},
    }
