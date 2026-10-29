"""Distinct silhouette wardrobe; additive IDs keep existing saves compatible."""
import functools
import numpy as np
from hair10 import HairV


@functools.lru_cache(maxsize=1)
def bald():
    return []


@functools.lru_cache(maxsize=1)
def wolf_cut():
    k = HairV('#463A45', 720, lo=(-25,-12,-25), hi=(25,39,23), n=26)
    k.helmet(top=29.4,hx=15.3,front=13.9,back=-15.9,side=12.7,rear=1.0,py=17,tip=1.0,jit=.6)
    k.face_window(top=23.6,hx=12.6,z0=4)
    for sg in (-1,1):
        for j in range(4):
            k.lock([(sg*12.5,21-j*3,-7),(sg*(16+j*.6),13-j*3,-10),(sg*(17+j*.5),9-j*3,-12)], [2.2,2.3,.35],j%3,sz=.8)
        k.lock([(sg*2,28,11),(sg*7,24,14),(sg*12,18.5,13)], [2.3,2,.4],1,sz=.7)
    return k.boxes(noise=.035)


@functools.lru_cache(maxsize=1)
def mohawk():
    k=HairV('#D85963',721,lo=(-22,-8,-24),hi=(22,42,24),n=24)
    # No helmet: shaved temples expose the skin, with one narrow sagittal crest.
    for i,z in enumerate(np.linspace(-13,12,9)):
        y=27+4*np.sin((i/8)*np.pi)
        k.lock([(0,23,z),(0,y+5,z-1),(0,y+8,z-2)], [3.2,2.2,.45],i%3,sz=.8)
    return k.boxes(noise=.03)


@functools.lru_cache(maxsize=1)
def pompadour():
    k=HairV('#724B32',722,lo=(-24,-8,-25),hi=(24,42,25),n=26)
    k.helmet(top=28,hx=14.8,front=12.9,back=-15.2,side=16,rear=9,py=17,tip=.3,jit=.2)
    k.face_window(top=25,hx=13,z0=3)
    k.neck_cut(y=8)
    for i,x in enumerate(np.linspace(-10,10,7)):
        k.lock([(x,25,7),(x,33.5,15),(x,35.5,9),(x,29,-2)], [2.5,3,2.6,1.5],i%3,sz=.8)
    return k.boxes(noise=.03)


def install(m):
    P,R=m.P,m.R
    def tunic(col,sleeves=True):
        out=R('torso',(0,32,0),(8.7,9.2,5.4),col,.7)
        if sleeves: out+=m._over_sleeves(col,m.tint(col,-.15),hx=2.8)
        return out
    def belt(col='#654431'):
        return R('torso',(0,24.2,.1),(9.2,1.2,5.8),col,.3)+[P('torso',(0,24.2,6),(1.3,1.1,.5),'#EBC779',bevel=.2)]
    def warrior():
        out=tunic('#566879')+belt()
        out+=R('torso',(0,33.5,5),(7.8,6.5,1.2),'#AEBFC8',.5)
        for sg in (-1,1):
            out+=R('arm%+d'%sg,(0,-1.4,0),(4.8,3,4.6),'#B7C7CE',.7)
            out+=R('arm%+d'%sg,(0,-10.3,0),(3.25,2.2,3.25),'#95A7B5',.4)
        out += [P('torso',(0,33.5,6.3),(.55,5.6,.35),'#EAC67A',bevel=.15),P('torso',(-9,23,-5),(1,8,1.1),'#7B4B34',rot=(0,0,-20)),P('torso',(-11.8,31,-5),(3,.6,1.2),'#D5B966',rot=(0,0,-20))]
        return out
    def archer():
        out=tunic('#688353')+belt()
        out+=R('torso',(-3,30,-7),(8,10,1.4),'#345D42',.6)
        out+=[P('torso',(5,32,-9),(3,7,2.5),'#96643F',rot=(0,0,-12)),P('torso',(-3,33,5.8),(.9,9,.5),'#BD9257',rot=(0,0,30))]
        for x in (3,5,7):
            out+=[P('torso',(x,40,-9),(.3,5,.3),'#DEC89D'),P('torso',(x,44,-9),(1,1.8,.5),'#EDE9CB',rot=(0,0,15))]
        # Curved longbow at the flank; a fine pale string closes its silhouette.
        for y,x in ((22,12),(27,14),(32,15),(37,14),(42,12)):
            out+=R('torso',(x,y,0),(.65,3,.65),'#AC7547',.2)
        out += [P('torso',(12,32,0),(.15,10,.15),'#E8D7AD')]
        return out
    def mage():
        out=tunic('#65518F')+belt('#C5A255')
        for sg in (-1,1):
            out+=R('torso',(sg*5,20,.1),(5.3,5,5.8),'#65518F',.5)
            out+=R('arm%+d'%sg,(0,-10,0),(4.4,4,4.1),'#7863A7',.5)
            out+=[P('torso',(sg*8,21,6),(.5,5,.4),'#E1C47C')]
        # Handheld staff follows the arm in walk and attack poses.
        out += [P('arm-1',(-5,-5,4),(.65,16,.65),'#8D643E',rot=(0,0,12)),P('arm-1',(-8.5,12,4),(2,2.8,2),'#76D5DE',rot=(0,0,35),emit=.1)]
        return out
    def thief():
        out=tunic('#353C4D')+belt('#77533D')
        for sg in (-1,1):
            out+=R('torso',(sg*5,22,-1),(3.7,4,5),'#454D61',.5)
            out+=[P('torso',(sg*3.5,33,5.8),(1,8,.5),'#8A6950',rot=(0,0,sg*20))]
        out += [P('arm+1',(0,-17,4),(.65,4,.35),'#CBD6DF'),P('arm+1',(0,-13,4),(2,.5,.7),'#B8A174'),P('arm+1',(0,-11.5,4),(.7,1.3,.7),'#77533D')]
        return out
    def trousers(col,armor=False):
        out=m._waist(col,m.WX,m.WZ)
        for sg in (-1,1):
            out+=R('leg%+d'%sg,(0,-6.7,0),(3.1,7.6,3.2),col,.5)
            out+=R('shin%+d'%sg,(0,-4,0),(3,5,3),col,.4)
            if armor: out+=R('shin%+d'%sg,(0,-2,3),(3.4,3.4,1.2),'#ABBDC7',.4)
        return out
    def boots(col,metal=False):
        out=[]
        for sg in (-1,1):
            bone='shin%+d'%sg
            out+=R(bone,(0,-12.6,1.5),(3.6,.8,5),'#39323A',.3)
            out+=R(bone,(0,-10.5,1.6),(3.4,1.8,4.6),col,.6)
            out+=R(bone,(0,-6,0),(3.3,4.1,3.4),col,.5)
            out+=[P(bone,(sg*3.4,-5,1),(.5,.7,1),'#CDB57B')]
        return out
    def mage_hat():
        out=[]
        for y,hx,hz in ((27,19,19),(30,14,14),(34,11,11),(38,8,8),(42,5,5),(45,2.5,2.5)):
            out+=R('head',((y-30)*.18,y,-1),(hx,2,hz),'#65518F',.5)
        out += [P('head',(0,30,13),(2,1,.7),'#E5C979')]
        return out
    def circlet():
        return [P('head',(0,22,13.6),(12,1.2,.7),'#D8B969',bevel=.3),P('head',(0,23.5,14),(1.5,2.1,.8),'#71BDCC',rot=(0,0,45))]
    def ranger_cap():
        out=R('head',(0,27,-2),(16,4,16),'#476D43',1)
        out+=R('head',(-12,29,-2),(9,2,8),'#476D43',.5)
        out += [P('head',(-16,32,-2),(.6,6,1),'#EDD6A0',rot=(0,0,-30))]
        return out
    def hood():
        out=R('head',(0,28,-3),(17,4,17),'#353C4D',1)
        for sg in (-1,1): out+=R('head',(sg*15,15,-3),(3,12,16),'#353C4D',.6)
        out+=R('head',(0,14,-17),(14,11,2),'#353C4D',.6)
        return out
    additions={'hair':[('bald','대머리'),('wolf-cut','레이어드 울프컷'),('mohawk','모호크'),('pompadour','포마드 퐁파두르')],
      'top':[('warrior-armor','전사 갑옷과 검'),('archer-ranger','궁수 망토와 활·화살통'),('mage-robe','마법사 로브와 지팡이'),('thief-jacket','도적 재킷과 단검')],
      'bottom':[('warrior-greaves','전사 판금 바지'),('ranger-trousers','궁수 바지'),('mage-trousers','마법사 바지'),('thief-trousers','도적 바지')],
      'shoes':[('warrior-sabatons','전사 철부츠'),('ranger-boots','궁수 장화'),('mage-boots','마법사 부츠'),('thief-boots','도적 부츠')],
      'hat':[('warrior-circlet','전사 서클릿'),('ranger-cap','궁수 깃털모자'),('mage-hat','마법사 고깔모자'),('thief-hood','도적 두건')]}
    for cat,entries in additions.items(): m.LABELS[cat]+=entries
    m.HAIRS.update({'bald':bald,'wolf-cut':wolf_cut,'mohawk':mohawk,'pompadour':pompadour})
    m.TOPS.update({'warrior-armor':warrior,'archer-ranger':archer,'mage-robe':mage,'thief-jacket':thief})
    m.BOTTOMS.update({'warrior-greaves':lambda:trousers('#566879',True),'ranger-trousers':lambda:trousers('#6B6946'),'mage-trousers':lambda:trousers('#514369'),'thief-trousers':lambda:trousers('#303748')})
    m.SHOES.update({'warrior-sabatons':lambda:boots('#A5B5C2',True),'ranger-boots':lambda:boots('#78563B'),'mage-boots':lambda:boots('#59416E'),'thief-boots':lambda:boots('#3F3A48')})
    m.HATS.update({'warrior-circlet':circlet,'ranger-cap':ranger_cap,'mage-hat':mage_hat,'thief-hood':hood})
    for label,hair,top,bottom,shoes,hat in [('전사','mohawk','warrior-armor','warrior-greaves','warrior-sabatons','warrior-circlet'),('궁수','wolf-cut','archer-ranger','ranger-trousers','ranger-boots','ranger-cap'),('마법사','bald','mage-robe','mage-trousers','mage-boots','mage-hat'),('도적','pompadour','thief-jacket','thief-trousers','thief-boots','thief-hood')]:
        m.PRESETS.append((label,dict(skin='medium',face='basic',hair=hair,top=top,bottom=bottom,shoes=shoes,hat=hat)))
