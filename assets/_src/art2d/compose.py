"""레이어 순서와 합성 (미리보기/검사용). 프런트의 합성 규칙과 같다."""
import numpy as np
from PIL import Image

LAYER_ORDER = [
    ('hair_back', 'hair', 'source-over'),
    ('hat_back', 'hat', 'source-over'),
    ('top_back', 'top', 'source-over'),
    ('skin_far', 'skin', 'source-over'),
    ('shoes_far', 'shoes', 'source-over'),
    ('bottom_far', 'bottom', 'source-over'),
    ('top_far', 'top', 'source-over'),
    ('skin', 'skin', 'source-over'),
    ('shoes', 'shoes', 'source-over'),
    ('bottom', 'bottom', 'source-over'),
    ('top', 'top', 'source-over'),
    ('head', 'skin', 'source-over'),
    ('face', 'face', 'source-over'),
    ('shade_hair', 'hair', 'source-atop'),
    ('hair_front', 'hair', 'source-over'),
    ('shade_hat', 'hat', 'source-atop'),
    ('skin_near', 'skin', 'source-over'),
    ('top_near', 'top', 'source-over'),
    ('hat', 'hat', 'source-over'),
]


def _f(im):
    return np.asarray(im.convert('RGBA'), np.float32) / 255.0


def over(dst, src, atop=False):
    sa = src[..., 3:4]
    da = dst[..., 3:4]
    if atop:
        oc = src[..., :3] * sa + dst[..., :3] * (1 - sa)
        return np.concatenate([oc, da], -1)
    oa = sa + da * (1 - sa)
    oc = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    return np.concatenate([oc, oa], -1)


def compose(get):
    """get(layer, part) -> PIL RGBA 또는 None."""
    out = None
    for layer, part, blend in LAYER_ORDER:
        im = get(layer, part)
        if im is None:
            continue
        a = _f(im)
        if out is None:
            out = np.zeros_like(a)
        out = over(out, a, blend == 'source-atop')
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')
