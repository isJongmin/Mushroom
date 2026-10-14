"""Design draft renderer: validates the anatomy/region maps written in style-guide.md.
Not an art deliverable. Produces preview PNGs for the design doc."""
from PIL import Image
import sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

PAL = {
 'ink':'#1A1626','hb1':'#4A4560','hb2':'#2E2A3E',
 'w1':'#E0A868','w2':'#B97A4A','w3':'#8A5232','w4':'#5E3620',
 's1':'#FFE3CC','s2':'#F5C29A','s3':'#D99464',
 'white':'#FFFFFF',
 'y1':'#FFF2A8','y2':'#F7C948','y3':'#F08A2E','y4':'#A84A1E',
 'p1':'#FFC8DC','p2':'#F58AB4','p3':'#B04A78',
 'r1':'#FF8E7A','r2':'#E8483E','r3':'#9E2838',
 'u1':'#9CC8FF','u2':'#4D7CFE','u3':'#2E3E9E','u4':'#232A5E',
 'g1':'#B6E86A','g2':'#6CC443','g3':'#3E8A2E','g4':'#23562A',
 'c1':'#FFF6E4','c2':'#F2DDB8','c3':'#C9A47A',
 'm1':'#BFF0DC','m2':'#7ED6B4','m3':'#3E9A86',
 'k1':'#6EC6F5','k2':'#86D2F8','k3':'#A0DDFA','k4':'#BBE8FC','k5':'#D8F3FE',
 'st1':'#C8C4D0','st2':'#8E88A0',
}
def rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

SKIN = {'skin-light':('s1','s2','w2'), 'skin-tan':('s2','s3','w3'), 'skin-dark':('w2','w3','w4')}
HAIRC = {'black':('hb1','hb2','ink'),'chestnut':('w2','w3','w4'),'blonde':('y1','y2','y4'),
         'pink':('p1','p2','p3'),'mint':('m1','m2','m3')}

W,H = 32,48
# ---------------- body region spans per frame -----------------
# region code -> list of (y, x0, x1)
def torso(dy):
    s=[(25+dy,12,18)]
    for y in range(26+dy,34+dy): s.append((y,11,19))
    return s
def rect(x0,x1,y0,y1): return [(y,x0,x1) for y in range(y0,y1+1)]
def rows(lst): return [(y,a,b) for (y,a,b) in lst]

FR = {}
FWD=[(34,15,17),(35,15,17),(36,16,18),(37,16,18),(38,17,19),(39,17,19),(40,18,20),(41,18,20),(42,19,21)]
FWD_FOOT=[(43,19,21),(44,19,22),(45,19,22)]
BACK=[(34,13,15),(35,13,15),(36,12,14),(37,12,14),(38,11,13),(39,11,13),(40,10,12),(41,10,12),(42,9,11)]
BACK_FOOT=[(43,9,11),(44,9,12),(45,9,12)]
# idle0
FR['idle0'] = dict(dy=0,
 T=torso(0),
 A=rect(10,12,26,28), a=rect(10,12,29,30), H=rect(10,12,31,32),
 B=[(26,20,20),(27,20,21),(28,20,21)], b=rect(20,21,29,30), h=rect(20,21,31,32),
 L=rect(12,14,34,42), M=rect(16,18,34,42),
 F=[(43,12,14),(44,12,15),(45,12,15)], G=[(43,16,18),(44,16,19),(45,16,19)])
FR['idle1'] = dict(dy=1,
 T=torso(1),
 A=rect(10,12,27,29), a=rect(10,12,30,31), H=rect(10,12,32,33),
 B=[(27,20,20),(28,20,21),(29,20,21)], b=rect(20,21,30,31), h=rect(20,21,32,33),
 L=rect(12,14,35,42), M=rect(16,18,35,42),
 F=[(43,12,14),(44,12,15),(45,12,15)], G=[(43,16,18),(44,16,19),(45,16,19)])
# walk0: near leg forward(right), far leg back(left); near arm back, far arm forward
FR['walk0'] = dict(dy=0,
 T=torso(0),
 A=[(26,10,12),(27,9,11),(28,9,11)], a=[(29,8,10),(30,8,10)], H=[(31,7,9),(32,7,9)],
 B=[(26,20,20),(27,20,21),(28,20,22)], b=[(29,21,22),(30,21,23)], h=[(31,21,23),(32,22,23)],
 L=FWD, F=FWD_FOOT, M=BACK, G=BACK_FOOT)
# walk1: passing, body up 1. near leg supports, far leg lifted
FR['walk1'] = dict(dy=-1,
 T=torso(-1),
 A=rect(10,12,25,27), a=rect(10,12,28,29), H=rect(10,12,30,31),
 B=[(25,20,20),(26,20,21),(27,20,21)], b=rect(20,21,28,29), h=rect(20,21,30,31),
 L=rect(13,15,33,42), F=[(43,13,15),(44,13,16),(45,13,16)],
 M=rect(15,17,33,40), G=[(41,15,17),(42,15,18),(43,15,18)])
# walk2: near leg back(left), far leg forward(right); near arm forward, far arm back
FR['walk2'] = dict(dy=0,
 T=torso(0),
 A=[(26,11,13),(27,12,14),(28,13,15)], a=[(29,13,15),(30,14,16)], H=[(31,14,16),(32,15,17)],
 B=[(27,10,10),(28,10,10)], b=[(29,10,10)], h=[(30,9,10),(31,9,10)],
 L=BACK, F=BACK_FOOT, M=FWD, G=FWD_FOOT)
# walk3: passing, body up 1. far leg supports, near leg lifted
FR['walk3'] = dict(dy=-1,
 T=torso(-1),
 A=rect(10,12,25,27), a=rect(10,12,28,29), H=rect(10,12,30,31),
 B=[(25,20,20),(26,20,21),(27,20,21)], b=rect(20,21,28,29), h=rect(20,21,30,31),
 M=rect(15,17,33,42), G=[(43,15,17),(44,15,18),(45,15,18)],
 L=rect(12,14,33,38)+[(39,13,15),(40,13,15)], F=[(41,13,15),(42,13,16),(43,13,16)])
ORDER = ['idle0','idle1','walk0','walk1','walk2','walk3']
DRAW = ['B','b','h','M','G','T','L','F','A','a','H']   # back -> front
GROUP = {'B':'farA','b':'farA','h':'farA','M':'farL','G':'farL','T':'T','L':'nearL','F':'nearL','A':'nearA','a':'nearA','H':'nearA'}

def region_map(f):
    fr=FR[f]; m=[['.']*W for _ in range(H)]
    for code in DRAW:
        for (y,a,b) in fr.get(code,[]):
            for x in range(a,b+1): m[y][x]=code
    return m

# ---------------- head -----------------
HEAD = [(8,11,20),(9,9,22),(10,8,23)]+[(y,7,24) for y in range(11,21)]+[(21,8,24),(22,9,23),(23,10,22),(24,12,21)]

def put(img,x,y,c):
    if 0<=x<W and 0<=y<H and c: img.putpixel((x,y),rgb(PAL[c])+(255,))

def outline_mask(mask_set):
    out=set()
    for (x,y) in mask_set:
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            if (x+dx,y+dy) not in mask_set: out.add((x,y)); break
    return out

def skin_layer(f, skin):
    base,shade,line = SKIN[skin]
    fr=FR[f]; dy=fr['dy']; img=Image.new('RGBA',(W,H),(0,0,0,0))
    m=region_map(f)
    # body: outline per pixel vs empty or vs a group drawn earlier
    rank={g:i for i,g in enumerate(['farA','farL','T','nearL','nearA'])}
    for y in range(H):
        for x in range(W):
            c=m[y][x]
            if c=='.': continue
            g=GROUP[c]; edge=False
            for ddx,ddy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+ddx,y+ddy
                n = m[ny][nx] if 0<=nx<W and 0<=ny<H else '.'
                if n=='.' or (GROUP[n]!=g and rank[GROUP[n]]<rank[g]): edge=True
            if edge: col=line
            else: col = shade if g in ('farA','farL') else base
            put(img,x,y,col)
    # head
    hs={(x,y+dy) for (y,a,b) in HEAD for x in range(a,b+1)}
    ol=outline_mask(hs)
    for (x,y) in hs:
        put(img,x,y, line if (x,y) in ol else base)
    # back-side shade (column x=8) rows 12..21 and ear
    for y in range(12,21): put(img,8,y+dy,shade)
    for (x,y) in [(9,21),(10,22),(11,22),(11,23)]: put(img,x,y+dy,shade)
    for (x,y) in [(10,16),(11,16),(10,17),(10,18),(11,18)]: put(img,x,y+dy,shade)
    put(img,11,17+dy,line)   # inner ear
    put(img,18,22+dy,line); put(img,19,22+dy,line)  # mouth
    return img

# ---------------- eyes -----------------
# 2-char codes. boxes: back eye x13..15, front eye x19..21, rows 15..19 (+dy)
EYES = {
 'eyes-dot': {   # rows 15..19, cols relative to box x0
   'back': ['.WW','.KK','.KN','.KK','.UU'],
   'front':['WW.','KK.','KN.','KK.','UU.']},
 'eyes-happy': {
   'back': ['.WW','...','.K.','K.K','...'],
   'front':['WW.','...','.K.','K.K','...']},
 'eyes-sleepy': {
   'back': ['...','.WW','...','KKK','.UU'],
   'front':['...','WW.','...','KKK','UU.']},
 'eyes-sparkle': {
   'back': ['.WW','.KK','.KN','.NK','.UU'],
   'front':['WWW','KKK','KNK','KKN','UUU']},
}
def eyes_layer(f, eid, skin):
    dy=FR[f]['dy']; img=Image.new('RGBA',(W,H),(0,0,0,0))
    cmap={'K':'ink','N':'white','U':'u2','W':'w4'}
    for side,x0 in (('back',13),('front',19)):
        for r,row in enumerate(EYES[eid][side]):
            for c,ch in enumerate(row):
                if ch!='.': put(img,x0+c,15+r+dy,cmap[ch])
    # blush
    bl = [(13,21),(21,21),(22,21)] if eid!='eyes-happy' else [(12,21),(13,21),(21,21),(22,21)]
    for (x,y) in bl: put(img,x,y+dy,'p2')
    return img

# ---------------- hair -----------------
# masks: absolute coords (idle0), rows from y=HY0. '.' empty, 'b' base, 'h' highlight, 'O' forced line
HY0=1
HAIR = {}
HAIR['round'] = [
# x: 0123456789012345678901234567890 1
  "................................", #1
  "................................", #2
  "................................", #3
  "...........bbbbbbbbb............", #4
  ".........bbbbbbbbbbbbb..........", #5
  ".......bbbbbbhhhhhbbbbbb........", #6
  "......bbbbbbhhhhhhhbbbbbb.......", #7
  ".....bbbbbbbbbbbbbbbbbbbbb......", #8
  ".....bbbbbbbbbbbbbbbbbbbbb......", #9
  ".....bbbbbbbbbbbbbbbbbbbbb......", #10
  ".....bbbbbbbbbbbbbbbbbbbbb......", #11
  ".....bbbbbbbbbbOObbbbObbbbb.....", #12
  ".....bbbbbbbbbbbbbbbbbbbbbb.....", #13
  ".....bbbbbbbbb.bbbbbbbb.bbb.....", #14
  ".....bbbbbbb.........b...bb.....", #15
  ".....bbbbbbb.............bb.....", #16
  ".....bbbbbbb.............bb.....", #17
  ".....bbbbbbb.............b......", #18
  ".....bbbbbb.....................", #19
  ".....bbbbbb.....................", #20
  "......bbbbb.....................", #21
  ".......bbb......................", #22
]
HAIR['spiky'] = [
  "................................", #1
  "..........b......b..............", #2
  "..........bb....bbb....b........", #3
  "..........bbb..bbbbb..bb........", #4
  ".........bbbbbbbbbbbbbbb........", #5
  "......bbbbbbbhhhhhbbbbbbb.......", #6
  ".....bbbbbbbhhhhhhhbbbbbbbb.....", #7
  "....bbbbbbbbbbbbbbbbbbbbbbbbb...", #8
  ".....bbbbbbbbbbbbbbbbbbbbbbb....", #9
  ".....bbbbbbbbbbbbbbbbbbbbbbbbb..", #10
  "....bbbbbbbbbbbbbbbbbbbbbbbb....", #11
  ".....bbbbbbbbbbbbbbbbbbbbbbbb...", #12
  "......bbbbbbbbbbbbbbbbbbbbbb....", #13
  ".....bbbbbbb.bbb.bbbb.bbbbb.....", #14
  "......bbbbb...b...b.....bb......", #15
  "......bbbb..............b.......", #16
  ".......bbb......................", #17
]
HAIR['long'] = [
  "................................", #1
  "................................", #2
  "................................", #3
  "...........bbbbbbbbb............", #4
  ".........bbbbbbbbbbbbb..........", #5
  ".......bbbbbbhhhhhbbbbbb........", #6
  "......bbbbbbhhhhhhhbbbbbb.......", #7
  ".....bbbbbbbbbbbbbbbbbbbbb......", #8
  ".....bbbbbbbbbbbbbbbbbbbbb......", #9
  "....bbbbbbbbbbbbbbbbbbbbbbb.....", #10
  "....bbbbbbbbbbbbbbbbbbbbbbb.....", #11
  "....bbbbbbbbbbbbbbbbbbbbbbbb....", #12
  "....bbbbbbbbbbbbbbbbbbbbbbbb....", #13
  "....bbbbbbbbbb.bbbbbbbbb.bbb....", #14
  "....bbbbbbbb.........b...bbb....", #15
  "....bbbbbbbb.............bbb....", #16
  "....bbbbbbbb.............bbb....", #17
  "....bbbbbbb..............bbb....", #18
  "....bbbbbbb..............bbb....", #19
  "....bbbbbbb..............bbb....", #20
  "....bbbbbbb...............bb....", #21
  "....bbbbbbb.....................", #22
  "....bbbbbbb.....................", #23
  "....bbbbbbb.....................", #24
  "....bbbbbbb.....................", #25
  "....bbbbbb......................", #26
  "....bbbbbb......................", #27
  ".....bbbbb......................", #28
  ".....bb.bb......................", #29
]
def hair_layer(f, shape, color):
    fr=FR[f]; dy=fr['dy']; img=Image.new('RGBA',(W,H),(0,0,0,0))
    hl,base,line=HAIRC[color]
    pts={}
    for r,row in enumerate(HAIR[shape]):
        for x,ch in enumerate(row):
            if ch!='.': pts[(x,HY0+r+dy)]=ch
    # remove near-arm overlap below chin
    m=region_map(f)
    for (x,y) in list(pts):
        if y>=25+dy and 0<=y<H and m[y][x] in ('A','a','H'): del pts[(x,y)]
    ol=outline_mask(set(pts))
    for (x,y),ch in pts.items():
        col = line if ((x,y) in ol or ch=='O') else (hl if ch=='h' else base)
        put(img,x,y,col)
    return img

# ---------------- clothes -----------------
def regpix(f, codes, rowfilter=None):
    m=region_map(f); out=set()
    for y in range(H):
        for x in range(W):
            if m[y][x] in codes and (rowfilter is None or rowfilter(x,y,m[y][x])): out.add((x,y))
    return out

def leg_rows(f, code, n):
    """first n rows of a leg region"""
    sp=FR[f][code]; ys=sorted({y for (y,a,b) in sp})[:n]
    return {(x,y) for (y,a,b) in sp if y in ys for x in range(a,b+1)}

def paint(img, pts, ramp, shade_pts=(), hl_pts=()):
    hl,base,line=ramp
    ol=outline_mask(pts)
    for p in pts:
        c = line if p in ol else (line if p in shade_pts else (hl if p in hl_pts else base))
        put(img,p[0],p[1],c)

def paint_groups(img, groups, ramp_for):
    """groups: list of (pts, ramp, far) in back->front order. outline vs empty or earlier-group."""
    owner={}
    for i,(pts,ramp,far) in enumerate(groups):
        for p in pts: owner[p]=i
    for i,(pts,ramp,far) in enumerate(groups):
        hl,base,line=ramp
        for p in pts:
            if owner[p]!=i: continue
            x,y=p; edge=False
            for dx,dyy in ((1,0),(-1,0),(0,1),(0,-1)):
                q=(x+dx,y+dyy)
                if q not in owner or owner[q]<i: edge=True
            put(img,x,y, line if edge else (line if far=='dark' else base))

R = {'red':('r1','r2','r3'),'blue':('u1','u2','u3'),'navy':('u3','u4','ink'),'pink':('p1','p2','p3'),
     'green':('g1','g2','g3'),'cream':('white','c1','c3'),'brown':('w2','w3','w4'),'shoe':('w2','w3','w4'),'redshoe':('r1','r2','r3')}

def shoulder_hl(img,f,k):
    dy=FR[f]['dy']
    for x in range(13,18): put(img,x,26+dy,k)

def top_layer(f, tid):
    fr=FR[f]; dy=fr['dy']; img=Image.new('RGBA',(W,H),(0,0,0,0))
    torso=regpix(f,('T',)); torso={p for p in torso if p[1]<=32+dy}
    near_up=regpix(f,('A',)); near_lo=regpix(f,('a',))
    far_up=regpix(f,('B',)); far_lo=regpix(f,('b',))
    if tid=='top-tee-red':
        g=[(far_up,R['red'],'far'),(torso,R['red'],None),(near_up,R['red'],None)]
        paint_groups(img,g,None)
        shoulder_hl(img,f,'r1')
    elif tid=='top-hoodie-blue':
        g=[(far_up|far_lo,R['blue'],'far'),(torso,R['blue'],None),(near_up|near_lo,R['blue'],None)]
        paint_groups(img,g,None)
        shoulder_hl(img,f,'u1')
        # hood fold on back of neck
        for (x,y,k) in [(11,25,'u3'),(12,25,'u1'),(13,25,'u1'),(14,25,'u3')]:
            put(img,x,y+dy,k)
        # pocket line + drawstrings
        for x in range(14,19): put(img,x,30+dy,'u3')
        put(img,17,26+dy,'white'); put(img,17,27+dy,'white')
    elif tid=='top-overalls':
        g=[(far_up,R['cream'],'far'),(torso,R['cream'],None),(near_up,R['cream'],None)]
        paint_groups(img,g,None)
        # bib + straps (blue)
        for y in range(29,33):
            for x in range(13,19): put(img,x,y+dy,'u2')
        for x in range(13,19): put(img,x,32+dy,'u3')
        for y in range(25,29): put(img,14,y+dy,'u3'); put(img,18,y+dy,'u3')
        put(img,14,29+dy,'y2'); put(img,18,29+dy,'y2')
    elif tid=='top-mushroom-cape':
        g=[(far_up|far_lo,R['cream'],'far'),(torso,R['cream'],None),(near_up|near_lo,R['cream'],None)]
        paint_groups(img,g,None)
        m=region_map(f)
        cape=set()
        for (y,a,b) in [(25,10,20),(26,9,21),(27,8,22),(28,8,22),(29,8,21)]:
            for x in range(a,b+1):
                yy=y+dy
                if m[yy][x] in ('a','H','h','b') : continue
                cape.add((x,yy))
        # scallop: drop every other pixel on bottom row
        for x in range(8,23):
            if x%2==1: cape.discard((x,29+dy))
        paint(img,cape,R['red'])
        for (x,y) in [(11,26),(15,25),(19,26),(13,28),(17,27),(21,28),(9,28)]:
            if (x,y+dy) in cape: put(img,x,y+dy,'c1')
        # toggle button
        put(img,15,30+dy,'y2')
    return img

def bottom_layer(f, bid):
    fr=FR[f]; dy=fr['dy']; img=Image.new('RGBA',(W,H),(0,0,0,0))
    hips={p for p in regpix(f,('T',)) if p[1]>=31+dy}
    shoe = R['redshoe'] if bid=='bottom-skirt-pink' else R['shoe']
    if bid=='bottom-shorts-navy':
        g=[(leg_rows(f,'M',4),R['navy'],'far'),(hips,R['navy'],None),(leg_rows(f,'L',4),R['navy'],None)]
    elif bid=='bottom-jeans-blue':
        g=[(leg_rows(f,'M',20),R['blue'],'far'),(hips,R['blue'],None),(leg_rows(f,'L',20),R['blue'],None)]
    elif bid=='bottom-pumpkin-green':
        lm=leg_rows(f,'M',3); ll=leg_rows(f,'L',3)
        lm|={(x-1,y) for (x,y) in lm}|{(x+1,y) for (x,y) in lm}
        ll|={(x-1,y) for (x,y) in ll}|{(x+1,y) for (x,y) in ll}
        g=[(lm,R['green'],'far'),(hips,R['green'],None),(ll,R['green'],None)]
    elif bid=='bottom-skirt-pink':
        sk=set()
        for (y,a,b) in [(31,11,19),(32,11,19),(33,10,20),(34,10,20),(35,9,21),(36,9,21)]:
            for x in range(a,b+1): sk.add((x,y+dy))
        g=[(sk,R['pink'],None)]
    paint_groups(img,g,None)
    # shoes
    sg=[(regpix(f,('G',)),shoe,None),(regpix(f,('F',)),shoe,None)]
    paint_groups(img,sg,None)
    # pleats for skirt
    if bid=='bottom-skirt-pink':
        for (x,y) in [(12,35),(15,35),(18,35),(12,34),(15,34),(18,34)]: put(img,x,y+dy,'p3')
    return img

def compose(f, av):
    img=Image.new('RGBA',(W,H),(0,0,0,0))
    img.alpha_composite(skin_layer(f,av['skin']))
    img.alpha_composite(bottom_layer(f,av['bottom']))
    img.alpha_composite(top_layer(f,av['top']))
    img.alpha_composite(eyes_layer(f,av['eyes'],av['skin']))
    shape,color=av['hair']
    img.alpha_composite(hair_layer(f,shape,color))
    return img

def sheet(av):
    s=Image.new('RGBA',(W*6,H),(0,0,0,0))
    for i,f in enumerate(ORDER): s.alpha_composite(compose(f,av),(i*W,0))
    return s

if __name__=='__main__':
    combos=[
     dict(skin='skin-light',hair=('round','black'),eyes='eyes-dot',top='top-tee-red',bottom='bottom-shorts-navy'),
     dict(skin='skin-tan',hair=('spiky','chestnut'),eyes='eyes-happy',top='top-hoodie-blue',bottom='bottom-jeans-blue'),
     dict(skin='skin-dark',hair=('long','pink'),eyes='eyes-sparkle',top='top-overalls',bottom='bottom-skirt-pink'),
     dict(skin='skin-light',hair=('spiky','mint'),eyes='eyes-sleepy',top='top-mushroom-cape',bottom='bottom-pumpkin-green'),
     dict(skin='skin-tan',hair=('long','blonde'),eyes='eyes-dot',top='top-tee-red',bottom='bottom-skirt-pink'),
    ]
    Z=6
    big=Image.new('RGBA',(W*6*Z+20, (H*Z+10)*len(combos)),rgb(PAL['k4'])+(255,))
    for r,av in enumerate(combos):
        s=sheet(av).resize((W*6*Z,H*Z),Image.NEAREST)
        # anchor marks
        big.alpha_composite(s,(10,r*(H*Z+10)+5))
    big.save(os.path.join(OUT,'avatar-draft.png'))
    # region maps ascii
    with open(os.path.join(OUT,'regions.txt'),'w') as fh:
        for f in ORDER:
            m=region_map(f)
            fh.write(f'### {f} (dy={FR[f]["dy"]})\n')
            for y in range(23,46):
                fh.write(f'{y:2d} '+''.join(m[y][6:26])+'\n')
    print('ok')
