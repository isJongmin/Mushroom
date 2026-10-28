"""파츠 등록부: 파츠 키 -> id -> 그리기 함수."""
import body, hair
DEFAULT = {'skin': 'light', 'face': 'basic', 'hair': 'black-short', 'top': None, 'bottom': None, 'shoes': None, 'hat': 'none'}
def draw_part(ctx, key, pid):
    if pid is None or pid == 'none':
        return
    if key == 'skin': body.skin(ctx, pid)
    elif key == 'face': body.face(ctx, pid)
    elif key == 'hair': hair.hair(ctx, pid)
    else:
        mod = REG.get(key)
        if mod and pid in mod: mod[pid](ctx)
import tops, bottoms, shoes, hats
REG = {'top': tops.TOPS, 'bottom': bottoms.BOTTOMS, 'shoes': shoes.SHOES, 'hat': hats.HATS}
def draw_all(ctx, av):
    for k in ('skin', 'face', 'hair', 'top', 'bottom', 'shoes', 'hat'):
        draw_part(ctx, k, av.get(k, DEFAULT[k]))
