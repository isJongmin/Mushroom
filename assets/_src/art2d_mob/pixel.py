"""Deterministic fine-pixel finish for the editable monster drawings.

One shared palette per animation prevents frame-to-frame palette flicker.
The grid is frame-local, so adjacent frames never bleed into one another.
Frame dimensions, anchors, hitboxes and gameplay metadata stay unchanged.
"""
import numpy as np
from PIL import Image

CELL = 2  # Asset pixels; 1.33 world units at the existing density of 1.5.
COLORS = 64


def pixel_frames(frames):
    small = []
    for frame in frames:
        w, h = frame.size
        if w % CELL or h % CELL:
            raise ValueError('Monster frames must be divisible by the pixel grid')
        im = frame.convert('RGBA').resize((w // CELL, h // CELL), Image.Resampling.BOX)
        a = np.array(im)
        # Restrained warm light, while keeping the blue shell and mint slime distinct.
        rgb = a[..., :3].astype(float)
        lum = rgb @ np.array([0.299, 0.587, 0.114])
        rgb = lum[..., None] + (rgb - lum[..., None]) * 0.88
        rgb = rgb * np.array([1.01, 0.98, 0.94]) + np.array([2, 2, 3])
        a[..., :3] = np.clip(np.round(rgb), 0, 255).astype('uint8')
        # Keep hit/death fades and soft ground shadows; only remove near-invisible fringe.
        a[..., 3] = np.where(a[..., 3] < 24, 0,
                            np.clip(np.round(a[..., 3] / 17) * 17, 0, 255)).astype('uint8')
        small.append(Image.fromarray(a))
    # Build palette from visible samples only: transparent black must not consume a color.
    samples = np.concatenate([np.array(im)[np.array(im)[..., 3] > 64, :3] for im in small])
    if not len(samples):
        return [Image.new('RGBA', f.size) for f in frames]
    palette = Image.fromarray(samples.reshape(1, -1, 3)).quantize(
        colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    result = []
    for original, im in zip(frames, small):
        rgb = im.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE).convert('RGBA')
        rgb.putalpha(im.getchannel('A'))
        out = rgb.resize(original.size, Image.Resampling.NEAREST)
        a = np.array(out)
        a[a[..., 3] == 0] = 0
        result.append(Image.fromarray(a))
    return result
