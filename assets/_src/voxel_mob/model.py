"""Seven original, deterministic solid-box creatures. Coordinates are real 3-D geometry.

All model features, including eyes, shell spiral, cap spots and core, are boxes;
there is no painted silhouette, vector source, pixelation or image tracing.
The shared avatar raycaster supplies face lighting, occlusion and fine cube grain.
"""
import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'voxel'))
from vox import Box, rot_z

NAMES = ('snail', 'mushroom', 'slime', 'bat', 'golem', 'forest-stump', 'crystal-crab')
MOVE = dict(snail=4, mushroom=6, slime=6, bat=4, golem=4, **{'forest-stump':4, 'crystal-crab':4})
I = np.eye(3)


class Sculpt:
    def __init__(self):
        self.boxes = []

    def b(self, c, size, col, tag='', *, bevel=.26, cube=.7, emit=0, angle=0):
        self.boxes.append(Box(c, np.array(size) / 2, rot_z(angle), col, 'mob',
                              bevel=bevel, noise=.025, cube=cube, tag=tag, emit=emit,
                              org=c))

    def eye(self, x, y, z, *, dark='#25251f', bright='#fff4ce', size=3):
        self.b((x, y, z), (size, size*1.35, 1.7), dark, 'eye', bevel=.1, cube=0)
        self.b((x+.5, y+.9, z+1), (.95, 1.05, .6), bright, 'glint', bevel=0, cube=0, emit=.3)


def snail(s, phase):
    """Low jade foot, terraced amber shell with a raised rectangular spiral."""
    stretch = math.sin(phase) * 1.2
    s.b((-1, 7, 0), (65+stretch, 8, 24), '#779b69', 'foot')
    s.b((-4, 12, -1), (53, 7, 22), '#a7bb7e', 'back')
    s.b((-29, 7, 0), (13, 5, 18), '#8caf76', 'tail')
    for x in (-25, -15, -5, 5, 15, 25):
        s.b((x, 7, 12.1), (6, 3.3, 1.6), '#b4c889', 'foot-ridge', bevel=.12)
    # Three interlocking layers form genuinely stepped shell corners.
    s.b((-12, 28, -1), (38, 25, 25), '#a55e36', 'shell')
    s.b((-12, 29, -1), (30, 37, 25), '#bd7e48', 'shell')
    s.b((-12, 29, -1), (22, 41, 19), '#d99b57', 'shell')
    s.b((-12, 30, 12), (29, 30, 3), '#e4b574', 'shell-face')
    # Raised square spiral, intentionally open on the lower right.
    for c, size in [((-12,44,15),(25,3,3)),((-24,32,15),(3,26,3)),
                    ((-13,20,15),(24,3,3)),((-2,29,15),(3,18,3)),
                    ((-10,37,15),(17,3,3)),((-17,31,15),(3,13,3)),
                    ((-11,26,15),(13,3,3)),((-6,30,15),(3,8,3))]:
        s.b(c, size, '#925331', 'spiral', bevel=.13, cube=.3)
    nod = math.cos(phase) * .8
    s.b((25, 17+nod, 0), (19, 17, 20), '#a5bf82', 'head')
    s.b((34, 15+nod, 5), (7, 10, 14), '#bbcf92', 'muzzle')
    for x,z in ((24,3),(32,10)):
        s.b((x, 29+nod, z), (3.6, 14, 3.6), '#9bb779', 'stalk')
        s.b((x, 36+nod, z), (7, 6.8, 6), '#c0ce93', 'eyecube')
        s.eye(x+1, 36+nod, z+3.3, size=2.8)
    s.b((34, 15+nod, 12.4), (3, 1.5, 1), '#687d55', 'smile', cube=0)


def mushroom(s, phase):
    """Asymmetric terracotta block cap, buttery gills, short cream stem."""
    swing = math.sin(phase) * 3.2
    s.b((-9-swing, 6, 1), (18, 10, 23), '#ad794b', 'left-foot')
    s.b((13+swing, 6, 4), (18, 10, 23), '#c38a53', 'right-foot')
    s.b((3, 23, 0), (31, 33, 26), '#f5dcaa', 'stem')
    s.b((1, 38, 0), (25, 16, 23), '#e8c690', 'stem-neck')
    s.b((-1, 47, -1), (76, 8, 43), '#ba794e', 'gills')
    s.b((-4, 53, -2), (82, 11, 46), '#c26a41', 'cap-rim')
    s.b((-5, 63, -3), (70, 13, 43), '#ca7448', 'cap-middle')
    s.b((-9, 73, -4), (52, 10, 35), '#da8858', 'cap-top')
    s.b((-14, 80, -4), (28, 5, 24), '#e49d6c', 'cap-crown')
    # Side cutout gives a distinct, lopsided cap silhouette.
    s.b((32, 51, -1), (13, 6, 34), '#ad5839', 'rim-step')
    for c, size in [((-25,70,19),(12,8,3)),((1,63,21),(10,10,3)),
                    ((21,55,22),(8,6,3)),((-9,78,12),(10,3,10)),
                    ((-28,64,-7),(10,3,12)),((10,72,-3),(9,3,12))]:
        s.b(c, size, '#f6d5a2', 'cap-inlay', bevel=.16, cube=.25)
    for x in (-28,-18,-8,2,12,22):
        s.b((x,46,21), (2.5,3.6,1.5), '#e9be88', 'gill', bevel=.1)
    s.eye(3, 28, 13.8, size=3.3)
    s.eye(15, 28, 13.8, size=3.3)
    s.b((10,21,14), (4,1.5,1.5), '#a96c50', 'smile', cube=0)
    s.b((-3,24,13.9), (4,2,1), '#e6b49a', 'cheek', cube=0)
    s.b((21,24,13.9), (4,2,1), '#e6b49a', 'cheek', cube=0)


def slime(s, phase):
    """Mint cuboid jelly with glassy solid insets and a three-step crown."""
    s.b((0, 8, 0), (63, 11, 38), '#65ad96', 'base')
    s.b((0, 25, -1), (58, 33, 37), '#8ad3b8', 'jelly')
    s.b((-2, 43, -2), (47, 10, 31), '#a0e1c7', 'top')
    s.b((-9, 50, -3), (19, 7, 20), '#bbeed6', 'crown-left')
    s.b((7, 54, -3), (12, 13, 18), '#b7efd6', 'crown-high')
    s.b((20, 48, -3), (10, 7, 16), '#9fddbf', 'crown-right')
    for x in (-23,-10,3,16,27):
        s.b((x,5,11), (9,6,14), '#7cc4a9', 'toe')
    # Highlights are dimensional inlaid cubes, not transparent alpha or paint.
    s.b((-18,34,18.4), (7,12,1.4), '#cef2d9', 'reflection', cube=.15)
    s.b((-21,42,18.4), (3.5,4,1.5), '#e4f7df', 'reflection', cube=0)
    s.b((15,13,18.6), (8,4,1.5), '#b7e4ba', 'jelly-inset', cube=.2)
    s.b((-13,13,18.7), (4,4,1.6), '#9cdbb5', 'bubble')
    s.eye(4, 29, 18.8, dark='#285b53', size=3.4)
    s.eye(17, 29, 18.8, dark='#285b53', size=3.4)
    s.b((12,21,19), (5,1.5,1.8), '#498772', 'smile', cube=0)
    s.b((25,24,18.7), (4,2,1.3), '#b5d6ac', 'cheek')


def bat(s, phase):
    """Plum block wings: overlapping cuboid fingers, never flat triangles."""
    flap = math.sin(phase)
    s.b((2,42,0), (25,29,22), '#66516b', 'body')
    s.b((5,61,1), (29,25,25), '#79607e', 'head')
    s.b((5,36,11.7), (15,15,2.5), '#ac8790', 'belly')
    s.b((-5,77,0), (9,15,12), '#735572', 'ear-left')
    s.b((15,79,0), (9,17,12), '#8b6784', 'ear-right')
    s.b((-5,78,6.2), (4,8,1.2), '#c29498', 'inner-ear')
    s.b((15,80,6.2), (4,9,1.2), '#ca9b99', 'inner-ear')
    for side in (-1,1):
        # Stair-shaped membranes remain thick in Z and have real top/side faces.
        for step, (width, height, y) in enumerate(((17,29,48),(16,22,51),(12,14,55))):
            x = side * (20+step*13)
            yy = y + flap * (step+1)*4
            s.b((x,yy,-3-step), (width,height,8), '#765477' if side<0 else '#8b6386', 'wing', angle=side*flap*7)
            s.b((x,yy+height/2,-3-step), (width+1,3,9), '#a57a9d', 'wing-finger', bevel=.15, angle=side*flap*7)
        s.b((side*15,35,-2), (9,11,9), '#5f4565', 'wing-knuckle')
    s.b((-4,23,4), (5,10,6), '#a38780', 'foot-left')
    s.b((10,23,4), (5,10,6), '#b69987', 'foot-right')
    for x in (2,15):
        s.b((x,63,14.1), (6,7,2), '#edb75b', 'amber-eye', cube=.15, emit=.1)
        s.b((x+1,63,15.3), (2,4,1), '#332c32', 'pupil', cube=0)
        s.b((x-.8,64.4,15.8), (1.3,1.4,.6), '#fff2ba', 'glint', cube=0, emit=.2)
    s.b((12,55,14.1), (8,5,4), '#ad7b8c', 'muzzle')
    s.b((8,52,15.5), (2,3,2), '#f1d8b6', 'fang')
    s.b((16,52,15.5), (2,3,2), '#f1d8b6', 'fang')


def golem(s, phase):
    """Mossy sandstone guardian, separated arms and a recessed turquoise core."""
    stride = math.sin(phase)*5
    for side in (-1,1):
        x = side*24
        lift = max(0,side*stride)
        s.b((x,12+lift,side*stride), (32,20,34), '#a89776', 'foot')
        s.b((x,33+lift,side*stride), (23,25,25), '#b4a17b', 'shin')
        s.b((x,51+lift,0), (25,11,27), '#8d8668', 'knee')
        s.b((x,66,0), (28,22,27), '#b7a47c', 'thigh')
    s.b((0,78,0), (70,19,33), '#b5a180', 'hip')
    s.b((0,103,-1), (74,37,37), '#bba681', 'torso')
    s.b((0,124,-2), (64,10,35), '#d0b991', 'collar')
    # Surface stones frame a recessed, luminous mineral cube.
    s.b((-19,106,19), (27,26,5), '#d4be94', 'chest-left')
    s.b((22,106,19), (22,26,5), '#c8ad80', 'chest-right')
    s.b((4,123,19), (23,7,5), '#e0c79b', 'core-lintel')
    s.b((4,90,19), (23,7,5), '#a38a64', 'core-sill')
    s.b((4,106,19), (17,24,4), '#427d72', 'core-recess')
    s.b((4,107,21), (11,16,6), '#69c5b2', 'core', emit=.32, cube=.4)
    s.b((2,112,24.2), (4,5,1), '#caf0c6', 'core-glint', cube=0, emit=.4)
    for side in (-1,1):
        swing=side*stride
        s.b((side*49,120,-1), (23,26,30), '#c7b28b', 'shoulder')
        s.b((side*55,99+swing,1), (20,24,24), '#b8a481', 'upper-arm')
        s.b((side*57,80+swing,2), (13,12,17), '#746e57', 'joint')
        s.b((side*59,64+swing,4), (25,25,28), '#c3ad84', 'forearm')
        s.b((side*59,48+swing,7), (26,11,27), '#a89472', 'knuckles')
        for finger in (-1,1):
            s.b((side*59+finger*6,43+swing,14), (8,9,12), '#b5a17c', 'finger')
    s.b((4,137,0), (28,14,25), '#8d8465', 'neck')
    s.b((4,155,0), (53,34,34), '#c8b58e', 'head')
    s.b((1,174,-2), (43,8,29), '#d6c49b', 'head-step')
    s.b((8,144,18), (35,9,7), '#ae9773', 'jaw')
    for x in (-3,18):
        s.b((x,157,18), (13,8,4), '#6c6c54', 'eye-socket')
        s.b((x+1,157,20.5), (7,4,2), '#a7dfb6', 'eye', emit=.2, cube=.2)
    s.b((9,146,22), (10,2,2), '#7e7056', 'mouth', cube=0)
    # Actual moss blocks cling to head, shoulder and forearm, breaking the outline.
    for c, size, col in [((-13,180,-1),(23,6,22),'#799a60'),
                          ((-21,174,9),(8,7,14),'#83a36a'),
                          ((-49,137,0),(24,7,25),'#71905b'),
                          ((-57,122,15),(10,16,3),'#6d8757'),
                          ((57,79,3),(20,6,21),'#8b9d61'),
                          ((-27,24,15),(11,5,6),'#83965f')]:
        s.b(c,size,col,'moss', bevel=.2)
    for c in ((-12,183,2),(-47,143,-2)):
        s.b(c,(3,6,4),'#9fb777','moss-sprout')


def forest_stump(s, phase):
    """Walking hollow hardwood trunk with stepped living moss and root limbs."""
    stride=math.sin(phase)*4
    for side in (-1,1):
        s.b((side*17,7+max(0,side*stride),side*stride),(22,12,27),'#695039','root-foot')
        s.b((side*31,32-side*stride,0),(13,26,15),'#79563a','branch-arm',angle=side*12)
        s.b((side*35,21-side*stride,4),(17,12,19),'#9c7248','root-hand')
    s.b((0,35,0),(48,48,33),'#885d3b','trunk')
    s.b((-2,60,-1),(52,10,36),'#bd965d','cut-rim')
    s.b((-2,66,-1),(39,4,27),'#ddbd80','cut-wood')
    s.b((-2,68,-1),(25,2,16),'#ad814e','growth-ring')
    s.b((-2,69,-1),(14,2,8),'#e1c88f','wood-heart')
    for x in (-20,-9,5,19):
        s.b((x,36,17),(4,37-(x%3)*4,3),'#60442e','bark-groove')
        s.b((x+3,40,18),(3,24,3),'#b28651','bark-ridge')
    for x in (-11,10):
        s.b((x,44,19),(10,9,4),'#3a3925','eye-hollow')
        s.b((x+1,45,21.4),(5,4,2),'#c1ee75','living-eye',emit=.5,cube=.2)
    s.b((2,28,19),(15,4,3),'#423c29','mouth')
    for c,sz in [((-17,70,-4),(24,9,30)),((3,74,-7),(23,9,24)),((18,67,-3),(13,10,24)),((-22,58,12),(9,18,9)),((-34,40,0),(17,6,18))]:
        s.b(c,sz,'#63884b','moss')
    for c in [(-18,78,-3),(3,83,-7),(13,78,-6)]:
        s.b(c,(8,7,8),'#94b966','leaf-bud')
    s.b((18,78,-3),(5,17,5),'#705238','twig',angle=-25)
    s.b((22,84,-3),(13,5,9),'#89ae5c','leaf')


def crystal_crab(s, phase):
    """Six stone legs, separated pincers, and a tiered mineral carapace."""
    for side in (-1,1):
        for j in range(3):
            step=math.sin(phase+j*math.pi*.7)*3
            x=side*(28+j*5)
            s.b((x,14+step,-14+j*13),(24,9,9),'#677583','leg-upper',angle=side*(15+j*8))
            s.b((x+side*10,7+max(0,step),-14+j*13),(10,12,11),'#87929a','leg-tip')
        s.b((side*30,25,21),(16,12,18),'#718796','claw-arm',angle=-side*15)
        s.b((side*38,31+side*math.sin(phase)*2,31),(23,17,18),'#89a0af','pincer')
        s.b((side*44,41,32),(9,12,17),'#a6bfcd','claw-upper',angle=-side*15)
        s.b((side*31,39,33),(8,8,16),'#718b9e','claw-lower')
    s.b((0,24,-1),(56,25,37),'#576d84','stone-body')
    s.b((-2,37,-4),(53,13,35),'#5479a5','shell')
    s.b((-3,46,-5),(41,9,29),'#698fc2','shell-tier')
    for c,sz,col in [((-18,53,-5),(12,21,13),'#78b6df'),((-2,60,-7),(13,31,14),'#9bd6ed'),((14,51,-5),(12,18,12),'#719dd5'),((-4,48,11),(10,15,10),'#96c9e8')]:
        s.b(c,sz,col,'crystal',bevel=.4,cube=.45)
        s.b((c[0]-2,c[1]+sz[1]*.2,c[2]+sz[2]/2+.6),(3,sz[1]*.5,1.5),'#d3eff7','crystal-glint',emit=.15,cube=0)
    for x in (-10,11):
        s.b((x,38,20),(5,16,6),'#718a9e','eye-stalk')
        s.b((x,46,21),(10,8,8),'#344958','eye-socket')
        s.b((x+1,46,25.5),(5,4,2),'#e5bf75','eye',emit=.3,cube=0)
    s.b((1,23,20),(15,4,3),'#344a5d','mouth')


BUILDERS = dict(snail=snail, mushroom=mushroom, slime=slime, bat=bat, golem=golem, **{'forest-stump':forest_stump, 'crystal-crab':crystal_crab})


def assemble(kind, frame=0):
    s=Sculpt()
    n=MOVE[kind]
    phase=frame/n*math.tau if frame<n else 0
    BUILDERS[kind](s,phase)
    hop=0
    sx=sy=1
    if kind in ('mushroom','slime') and frame<n:
        hop=math.sin(frame/n*math.pi)**2 * (20 if kind=='mushroom' else 24)
        squash=math.cos(phase)*(.065 if kind=='mushroom' else .11)
        sx=1+squash
        sy=1-squash
    if kind=='bat' and frame<n:
        hop=math.cos(phase)*1.8
    if kind=='golem' and frame<n:
        hop=(1-math.cos(phase))*.8
    if frame==n:  # the existing one-frame hit contract
        sx,sy=1.08,.86
    death=max(0,frame-n)
    if kind in ('forest-stump','crystal-crab'):
        if frame in (n,n+1):
            sx,sy=(1.08,.86) if frame==n else (.94,1.02)
        death=max(0,frame-n-1)
    if death:
        t=death/4
        sx,sy=1,max(.14,1-t*.85)
        hop=0
    for i,b in enumerate(s.boxes):
        b.c*=np.array([sx,sy,1])
        b.h*=np.array([sx,sy,1])
        b.c[1]+=hop
        if kind=='slime' and frame<n:
            b.c[0]+=b.c[1]*.025*math.sin(phase)
        if death:
            t=death/4
            # Independent blocks break apart, settle, then fade via the runtime.
            b.c[0]+=math.copysign(t*(2+i%4)*.9,b.c[0] or 1)
            b.c[1]+= (i%3)*t*2
            b.c[2]+=(i%5-2)*t*1.8
        b.org=b.c.copy()
    return s.boxes
