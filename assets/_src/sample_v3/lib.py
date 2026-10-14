"""sample_v3 pixel helpers: char-grid layers, masks, shading, outline.

A layer is a numpy array (H x W) of single chars. '.' = transparent.
Each char maps to one palette colour (palette.py). Everything is
deterministic: same input -> same PNG.
"""
import numpy as np
from PIL import Image, ImageDraw

from palette import PAL

W, H = 80, 96
YY, XX = np.mgrid[0:H, 0:W]


def new():
    return np.full((H, W), '.', dtype='<U1')


# ---------------------------------------------------------------- masks
def ell(cx, cy, rx, ry):
    return ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2 <= 1.0


def poly(pts):
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=1, outline=1)
    return np.array(im, bool)


def lines(pts, width=1):
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).line([tuple(p) for p in pts], fill=1, width=width)
    return np.array(im, bool)


def rect(x0, y0, x1, y1):
    return (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)


def at(m, dx, dy):
    """mask value at (x+dx, y+dy); outside canvas = False."""
    p = np.pad(m, ((abs(dy), abs(dy)), (abs(dx), abs(dx))))
    return p[abs(dy) + dy:abs(dy) + dy + H, abs(dx) + dx:abs(dx) + dx + W]


def shift(m, dx, dy):
    """move mask content by (dx, dy)."""
    return at(m, -dx, -dy)


def edge(m):
    return m & ~(at(m, 1, 0) & at(m, -1, 0) & at(m, 0, 1) & at(m, 0, -1))


def dilate(m, n=1):
    for _ in range(n):
        m = m | at(m, 1, 0) | at(m, -1, 0) | at(m, 0, 1) | at(m, 0, -1)
    return m


# ---------------------------------------------------------------- painting
def put(L, mask, ch):
    L[mask] = ch


def sphere_light(cx, cy, rx, ry, light=(-0.55, -0.65, 0.52)):
    """Lambert term of an ellipsoid; light from upper-left."""
    nx = (XX + 0.5 - cx) / rx
    ny = (YY + 0.5 - cy) / ry
    r2 = np.clip(nx * nx + ny * ny, 0, 1)
    nz = np.sqrt(1 - r2)
    lx, ly, lz = light
    ln = (lx * lx + ly * ly + lz * lz) ** 0.5
    return (nx * lx + ny * ly + nz * lz) / ln


def band_shade(L, mask, ramp, sh=(2, 2), deep=None, hl=None, outline=True):
    """Flat shading by inset bands.
    ramp: dict hl/base/sh/deep/line chars.
    sh  : pixels whose (x+dx, y+dy) leaves the mask become shadow.
    deep: same for deep shadow (narrower offset).
    hl  : pixels whose (x-dx, y-dy) leaves the mask become highlight.
    """
    L[mask] = ramp['base']
    if hl:
        L[mask & ~at(mask, -hl[0], -hl[1])] = ramp['hl']
    if sh:
        L[mask & ~at(mask, sh[0], sh[1])] = ramp['sh']
    if deep:
        L[mask & ~at(mask, deep[0], deep[1])] = ramp['deep']
    if outline:
        L[edge(mask)] = ramp['line']


def stamp(L, grid, x, y, mirror=False):
    """paste a char grid; '.' leaves pixel untouched, '_' clears it."""
    rows = [r for r in grid.strip('\n').split('\n')]
    for j, row in enumerate(rows):
        if mirror:
            row = row[::-1]
        for i, ch in enumerate(row):
            if ch == '.':
                continue
            yy, xx = y + j, x + i
            if 0 <= yy < H and 0 <= xx < W:
                L[yy, xx] = '.' if ch == '_' else ch


def flip(L):
    return L[:, ::-1].copy()


def offset(L, dx, dy):
    out = new()
    for y in range(H):
        for x in range(W):
            sx, sy = x - dx, y - dy
            if 0 <= sx < W and 0 <= sy < H:
                out[y, x] = L[sy, sx]
    return out


def over(*layers):
    out = new()
    for L in layers:
        m = L != '.'
        out[m] = L[m]
    return out


def to_img(L):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    px = im.load()
    for y in range(H):
        for x in range(W):
            c = L[y, x]
            if c != '.':
                h = PAL[c]
                px[x, y] = (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)
    return im


def to_txt(L):
    return '\n'.join(''.join(r) for r in L) + '\n'
