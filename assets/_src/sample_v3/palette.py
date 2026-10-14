"""sample_v3 palette: one char -> one colour. Ramps: hl -> base -> sh -> deep -> line.
Light comes from the upper-left."""

PAL = {
    # hair (charcoal with a little purple)
    'a': '#AC9AA2',  # hair hl2 (shine dash)
    'b': '#78697C',  # hair hl
    'K': '#564B5C',  # hair mid-light (sheen zone)
    'c': '#433A48',  # hair base
    'd': '#302937',  # hair shadow
    'e': '#211B27',  # hair deep / strand line
    'f': '#110D15',  # hair outline (outer silhouette)
    # skin
    'g': '#FFF8F3',  # skin hl
    'h': '#FFEADF',  # skin base
    'i': '#F8D0C0',  # skin shadow
    'j': '#E9A495',  # skin deep (ear inside, chin under)
    'k': '#8C4842',  # skin outline
    'l': '#F7A3A6',  # blush
    'm': '#C9474A',  # mouth dark
    'n': '#F2847E',  # mouth light / tongue
    # eyes
    'o': '#21182B',  # lash / eye line
    'p': '#302660',  # iris dark
    'q': '#5A4CA8',  # iris mid
    'r': '#9C8CE0',  # iris light
    'w': '#FFFFFF',  # white (eye shine, shoe hl)
    # hoodie (black)
    's': '#5A5464',  # hoodie hl
    't': '#3B3644',  # hoodie base
    'u': '#2B2733',  # hoodie shadow
    'v': '#1E1B25',  # hoodie deep / fold
    'x': '#0F0D13',  # hoodie outline
    'y': '#F1EDF4',  # drawstring
    'z': '#A9A2B4',  # drawstring shade / aglet
    'A': '#6E3440',  # hood lining (dark red)
    # denim shorts
    'B': '#93A4D2',  # denim hl
    'C': '#5E6FA3',  # denim base
    'D': '#465385',  # denim shadow
    'E': '#323C66',  # denim deep
    'F': '#1B2142',  # denim outline
    # white sneakers
    'G': '#E7E5EE',  # shoe base
    'H': '#BDB8CC',  # shoe shadow
    'I': '#8D88A1',  # shoe deep / sole side
    'J': '#47425A',  # shoe outline
}

HAIR = dict(hl2='a', hl='b', base='c', sh='d', deep='e', line='f')
SKIN = dict(hl='g', base='h', sh='i', deep='j', line='k')
TOP = dict(hl='s', base='t', sh='u', deep='v', line='x')
TOP_FAR = dict(hl='t', base='u', sh='v', deep='v', line='x')
DENIM = dict(hl='B', base='C', sh='D', deep='E', line='F')
DENIM_FAR = dict(hl='C', base='D', sh='E', deep='E', line='F')
SHOE = dict(hl='w', base='G', sh='H', deep='I', line='J')
SHOE_FAR = dict(hl='G', base='H', sh='I', deep='I', line='J')
SKIN_FAR = dict(hl='h', base='i', sh='j', deep='j', line='k')

assert len(PAL) <= 40, len(PAL)
