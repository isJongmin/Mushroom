"""Additive fine-pixel wardrobe. Existing IDs and geometry remain unchanged.

Palette remaps target only the named textile/hair material; shirts, leather,
metal, embroidery and other accents keep their original material colors.
"""
import numpy as np
from hair10 import HairV, HatV, tint, hair_sky_bob


def recolor(defs, old, new, shifts):
    palette = {tint(old, k): tint(new, k) for k in shifts}
    palette[old] = new
    return [dict(d, col=palette.get(d['col'], d['col'])) for d in defs]


def hair_espresso_crop():
    """Close-cut nape and temples, raised brushed crop with visible forehead."""
    k = HairV('#44302A', 515, n=28)
    k.helmet(top=29.6, hx=15.3, front=13.6, back=-15.4,
             side=13.0, rear=7.5, py=17.0, tip=0.6, jit=0.3)
    k.face_window(top=24.0, hx=13.4, z0=4.0, r=2.0)
    k.neck_cut(y=5.8, hx=12.0)
    # Independent swept locks stay above the brow instead of a bowl fringe.
    for i, x in enumerate(np.linspace(-10.5, 10.5, 8)):
        k.lock([(x, 26.0, 9.0), (x + 1.2, 28.3 + 0.5 * np.cos(i), 11.6),
                (x + 2.2, 24.4 + 0.4 * np.sin(i), 13.3)], [2.0, 1.9, 0.65], i % 3, sz=0.7)
    return k.boxes(noise=0.035)


def hair_copper_spacebuns():
    """Two coiled buns above the ears, parted crown and short face tendrils."""
    k = HairV('#B66D46', 616, lo=(-27, -8, -25), hi=(27, 42, 22), n=26,
              accents=('#E8C68A',))
    k.helmet(top=31.0, hx=16.0, front=14.3, back=-16.5,
             side=10.5, rear=7.0, py=17.0, tip=0.8, jit=0.4)
    k.face_window(top=22.8, hx=12.6, z0=3.5)
    k.neck_cut(y=4.8)
    for sg in (1, -1):
        k.lock([(sg * 11.0, 25.8, -3.0), (sg * 18.5, 29.0, -3.4)], [3.0, 3.2], 0)
        k.blob((sg * 17.3, 28.0, -3.0), (2.3, 2.3, 2.6), 5)
        k.blob((sg * 20.3, 30.0, -3.4), (5.8, 6.4, 6.0), 0)
        # Coiled rings have independent SDF geometry and contrasting strands.
        th = np.linspace(0, 2 * np.pi, 18)
        pts = [(sg * (20.3 + 4.4 * np.sin(t)), 30.0 + 4.9 * np.cos(t), -0.3) for t in th]
        k.lock(pts, [0.75] * len(pts), 1, sz=0.85)
        k.lock([(sg * 12.4, 24.2, 12.6), (sg * 13.1, 16.0, 13.5),
                (sg * 12.4, 10.2, 12.8)], [1.5, 1.0, 0.35], 2, sz=0.7)
    # Slightly parted short fringe leaves an open center forehead.
    for sg in (1, -1):
        k.lock([(sg * 1.2, 27.8, 12.0), (sg * 5.5, 25.0, 14.0),
                (sg * 10.5, 21.6, 14.0)], [2.0, 1.8, 0.65], 1, sz=0.7)
    return k.boxes(noise=0.04)


def hair_silver_bob():
    return recolor(hair_sky_bob(), '#8FCBF0', '#B9BEC9', (0.08, -0.07, -0.16, -0.35))


def hat_beanie_sage():
    # A slightly roomier knit crown contains raised crop locks in front view.
    k = HatV('#8FA18A', accents=('#FFF6E4',))
    g = k.g
    k.crown((0, 26.8, -0.8), (19.4, 10.0, 20.0), 8.0, p=3.0)
    rib = np.floor((np.arctan2(g.X, g.Z + 0.8) / (2 * np.pi) + 0.5) * 36) % 2 == 0
    k.lab = np.where((k.d <= 0) & rib, 2, k.lab)
    k.band(19.6, 2.2, 19.4, 20.0, 2.4, zc=-0.8, lab=np.where(rib, 3, 2), out=1.03)
    k.blob((0, 37.2, -0.8), (3.2, 2.8, 3.2), 5)
    return k.boxes()


def install(model):
    model.HAIRS.update({'espresso-crop': hair_espresso_crop,
                        'copper-spacebuns': hair_copper_spacebuns, 'silver-bob': hair_silver_bob})
    model.HATS['beanie-sage'] = hat_beanie_sage
    model.TOPS['varsity-burgundy'] = lambda: recolor(model.top_varsity_navy(), '#25304E', '#873E4B', (-0.1, 0.05))
    model.TOPS['cardigan-sage'] = lambda: recolor(model.top_cardigan_cream(), '#DCC6A0', '#8FA18A', (-0.07, -0.04, -0.06))
    model.BOTTOMS['widepants-cream'] = lambda: recolor(model.bottom_denim_wide(), '#A9C3E6', '#E9DEC7', (-0.18, -0.12, 0.12, -0.15))
