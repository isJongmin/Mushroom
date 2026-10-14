"""Hand-drawn char grids (palette chars, '.' = leave, '_' = clear).
Coordinates of where each grid is stamped live in build.py."""

# ---- eyes: light from upper-left, so both shines sit upper-left.
EYE_FRONT_L = """
o.......
.oooooo.
ooppppoo
.opwwppo
.opwwpqo
.oppqqqo
.oqqrrqo
.oqrrwqo
..qqqq..
"""

EYE_FRONT_R = """
.......o
.oooooo.
ooppppoo
opwwppo.
opwwpqo.
oppqqqo.
oqqrrqo.
oqrrwqo.
.qqqq...
"""

# side view, facing right: lash flick points back (left)
EYE_SIDE = """
oo....
.oooo.
oopppo
.pwwpo
.pwwqo
.ppqqo
.qrrqo
.qrwq.
..qq..
"""

MOUTH_FRONT = """
mmm
.n.
"""

MOUTH_SIDE = """
mm
"""

BLUSH = """
.ll.
llll
"""

BLUSH_SIDE = """
lll
.l.
"""

# ---- small body parts
# front ear (left side of picture); mirrored for the right one
EAR_FRONT = """
.kkk.
kiihk
kjihk
kjhhk
kjihk
.kjhk
..kk.
"""

# side ear (facing right)
EAR_SIDE = """
.kkkk.
kihhik
kijjhk
kijihk
kihjik
.kiihk
..kkk.
"""

# hands: front mitten (left side), mirrored for right
HAND_FRONT = """
.kkkk.
khhhik
khghik
khhhik
kihiik
.kkkk.
"""

HAND_SIDE = """
.kkkk
khhik
kghik
khhik
.kkk.
"""

# ---- round 2: bigger eyes (8 x 10), thick 2-row upper lash
EYE_FRONT_L = """
oo......
.oooooo.
oooooooo
oopppppo
.opwwppo
.opwwpqo
.oppqqqo
.oqqrrqo
.oqrrwqo
..qqqq..
"""

EYE_FRONT_R = """
......oo
.oooooo.
oooooooo
opppppoo
opwwppo.
opwwpqo.
oppqqqo.
oqqrrqo.
oqrrwqo.
.qqqq...
"""

EYE_SIDE = """
oo....
.oooo.
oooooo
oppppo
.pwwpo
.pwwqo
.ppqqo
.qrrqo
.qrwq.
..qq..
"""
