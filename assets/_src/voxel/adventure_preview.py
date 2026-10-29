"""Review new geometry from installed layers; python adventure_preview.py [directory]."""
import os
import sys
from PIL import Image, ImageDraw
import build as B
from model import PRESETS


def make(out):
    os.makedirs(out,exist_ok=True)
    sheets=B.load_sheets(os.path.join(B.ROOT,'assets/avatar'))
    base=dict(PRESETS[0][1],hat='none',hair='bald')
    # Same outfit, view and lighting make actual hair silhouette differences clear.
    rows=[(pid,dict(base,hair=pid)) for pid in ('bald','wolf-cut','mohawk','pompadour')]
    rows += [(av['top'],av) for _,av in PRESETS[-4:]]
    names=('front','side','back','attack1','prone')
    board=Image.new('RGBA',(B.W*len(names),len(rows)*(B.H+26)), '#ECE8E0')
    draw=ImageDraw.Draw(board)
    for r,(label,av) in enumerate(rows):
        y=r*(B.H+26)
        draw.text((10,y+5),label,fill='#343342')
        full=B.composite(sheets,av)
        for j,name in enumerate(names):
            i=B.FRAMES.index(name)
            board.alpha_composite(Image.fromarray(full[:,i*B.W:(i+1)*B.W]),(j*B.W,y+24))
    path=os.path.join(out,'adventure-review.png')
    board.save(path)
    print(path)

if __name__=='__main__': make(sys.argv[1] if len(sys.argv)>1 else os.path.join(B.HERE,'out'))
