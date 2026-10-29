"""Render review boards from the exact runtime assets, never concept placeholders.

Run: python assets/_src/review_fine_pixel.py
Optional comparison: --before-ref <commit SHA>
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'assets/_src/voxel'))
import build as avatar_build

OUT = ROOT / 'assets/_src/voxel-variety-review'
BG = '#f4f0e7'
INK = '#292a37'
MUTED = '#747779'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
LABELS = ['Lavender club', 'Cream cardigan', 'Midnight varsity',
          'Mint puffer', 'Rose ribbon', 'Mushroom scout',
          'Burgundy crop', 'Copper garden', 'Silver street',
          'Mint day', 'Sage stroll', 'Twin ribbon']


def text(im, xy, value, size=20, fill=INK, bold=False):
    ImageDraw.Draw(im).text(xy, value, font=ImageFont.truetype(BOLD if bold else FONT, size), fill=fill)


def composite(root=ROOT, ref=None):
    def read(path):
        if ref:
            return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)
        return (root / path).read_bytes()
    manifest = json.loads(read('assets/avatar/manifest.json'))
    sheets = {}
    for e in manifest['layerOrder']:
        for pid in manifest['files'][e['layer']]:
            key = (e['layer'], pid)
            sheets[key] = np.array(Image.open(io.BytesIO(read(f'assets/avatar/{key[0]}/{pid}.png'))).convert('RGBA'))
    # Use each version's own layer ordering rather than assuming a historical layout.
    result = []
    for p in manifest['presets']:
        acc = None
        for e in manifest['layerOrder']:
            a = sheets.get((e['layer'], p['avatar'].get(e['part'])))
            if a is None:
                continue
            if acc is None:
                acc = np.zeros_like(a, dtype=float)
            acc = avatar_build.atop(acc, a) if e['blend'] == 'source-atop' else avatar_build.over(acc, a)
        result.append(Image.fromarray(np.clip(np.round(acc), 0, 255).astype('uint8')))
    return manifest, result


def frame(sheet, m, name):
    w, h = m['frame']['w'], m['frame']['h']
    i = m['frames'].index(name)
    return sheet.crop((i*w, 0, (i+1)*w, h))


def sprite(im, image, foot, anchor, scale):
    size = (round(image.width*scale), round(image.height*scale))
    image = image.resize(size, Image.Resampling.NEAREST)
    im.alpha_composite(image, (round(foot[0]-anchor[0]*scale), round(foot[1]-anchor[1]*scale)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before-ref')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    m, characters = composite()
    anchor = (m['anchor']['x'], m['anchor']['y'])
    rows = (len(characters) + 5) // 6
    board = Image.new('RGBA', (1800, 720 + (rows - 1) * 520), BG)
    text(board, (48, 30), 'MUSHROOM / FINE PIXEL', 18, MUTED, True)
    text(board, (48, 64), 'More hair, more color, more character.', 32, bold=True)
    text(board, (48, 112), f'Actual layered game assets / {len(characters)} outfits / original customization retained', 18, MUTED)
    for i, c in enumerate(characters):
        x = 24+(i%6)*296
        y = (i//6)*520
        ImageDraw.Draw(board).rounded_rectangle((x, y+165, x+280, y+672), 18, fill='#ebe8df')
        sprite(board, frame(c,m,'front'), (x+110, y+540), anchor, 2.25)
        sprite(board, frame(c,m,'side'), (x+233, y+540), anchor, 1.0)
        label = LABELS[i] if i < len(LABELS) else m['presets'][i]['label']
        text(board,(x+18,y+574),f'{i+1:02d} / {label}',17,bold=True)
        text(board,(x+18,y+608),'Front + side / runtime sprites',14,MUTED)
    board.convert('RGB').save(OUT/'characters.png')

    mobs = json.loads((ROOT/'assets/mob/manifest.json').read_text())
    mobboard=Image.new('RGBA',(1600,660),BG)
    text(mobboard,(48,30),'MUSHROOM / CREATURE COLLECTION',18,MUTED,True)
    text(mobboard,(48,65),'Built in blocks, from the ground up.',30,bold=True)
    text(mobboard,(48,115),'Original 3D voxel models / warm three-face lighting / move, hit and defeat animations',17,MUTED)
    for i,(mid,s) in enumerate(mobs['mobs'].items()):
        x=28+i*314
        ImageDraw.Draw(mobboard).rounded_rectangle((x,170,x+290,600),18,fill='#e7e6db')
        w,h=s['frame']['w'],s['frame']['h']
        img=Image.open(ROOT/s['sheet']).crop((0,0,w,h))
        scale=min(2.8,260/w,300/h)
        sprite(mobboard,img,(x+145,493),(s['anchor']['x'],s['anchor']['y']),scale)
        text(mobboard,(x+20,525),mid.upper(),18,bold=True)
        text(mobboard,(x+20,558),f"{s['frames']} frames / move + hit + defeat",13,MUTED)
    mobboard.convert('RGB').save(OUT/'monsters.png')

    # Scene uses map world geometry: exactly the same world-to-sheet density as runtime.
    mp=json.loads((ROOT/'assets/map/manifest.json').read_text())
    ground=Image.open(ROOT/'assets/map/ground.webp').convert('RGBA')
    scene=Image.new('RGBA',(1600,850),BG)
    text(scene,(48,25),'MUSHROOM / IN-WORLD ART PREVIEW',18,MUTED,True)
    text(scene,(48,60),'Same village. A fresher cast.',32,bold=True)
    k=1.12  # CSS-like preview pixels per world unit.
    camx=1000
    camy=mp['groundY']-515/k
    box=(round(camx*mp['density']),round(camy*mp['density']),
         round((camx+1600/k)*mp['density']),round((camy+600/k)*mp['density']))
    crop=ground.crop(box).resize((1600,600),Image.Resampling.LANCZOS)
    scene.alpha_composite(crop,(0,145))
    gy=round(145+(mp['groundY']-camy)*k)
    for i,c in enumerate(characters[-6:]):
        x=145+i*260
        ImageDraw.Draw(scene).ellipse((x-22,gy-4,x+22,gy+5),fill=(41,34,25,80))
        sprite(scene,frame(c,m,'side' if i%2 else 'front'),(x,gy),anchor,k/m['density'])
    for i,(mid,s) in enumerate(mobs['mobs'].items()):
        w,h=s['frame']['w'],s['frame']['h']
        img=Image.open(ROOT/s['sheet']).crop((0,0,w,h))
        sprite(scene,img,(275+i*260,gy-(90 if mid=='bat' else 0)),(s['anchor']['x'],s['anchor']['y']),k/mobs['density'])
    text(scene,(48,780),'Rendered from the replacement sprite sheets on the existing map.',20,bold=True)
    text(scene,(48,813),'Art composition preview - not a browser screenshot.',15,MUTED)
    scene.convert('RGB').save(OUT/'village.png')

    animation=[]
    for name in ['front','front_b','side','walk0','walk1','walk2','walk3','back','jump','fall','prone','attack0','attack1']:
        im=Image.new('RGBA',(1440,420+(rows-1)*360),BG)
        text(im,(32,20),'MUSHROOM / MOTION CHECK',17,MUTED,True)
        text(im,(32,52),name.upper(),24,bold=True)
        for i,c in enumerate(characters):
            sprite(im,frame(c,m,name),(120+(i%6)*240,385+(i//6)*360),anchor,1.5)
        animation.append(im.convert('RGB'))
    palette=animation[0].quantize(colors=128)
    animation=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in animation]
    animation[0].save(OUT/'motion.gif',save_all=True,append_images=animation[1:],duration=[500,500,300,150,150,150,150,300,300,300,500,180,180],loop=0,disposal=2)

    if args.before_ref:
        oldm,old=composite(ref=args.before_ref)
        compare=Image.new('RGBA',(1800,900),BG)
        for row,(mm,chars,title) in enumerate([(oldm,old[:6],'PREVIOUS / six outfits'),(m,characters[-6:],'ADDED / six more personalities')]):
            y=row*450
            text(compare,(40,y+20),title,25,bold=True)
            aa=(mm['anchor']['x'],mm['anchor']['y'])
            for i,c in enumerate(chars):
                sprite(compare,frame(c,mm,'front'),(150+i*300,y+425),aa,1.9)
        compare.convert('RGB').save(OUT/'before-after.png')

        old_mobs = json.loads(subprocess.check_output(
            ['git','show',f'{args.before_ref}:assets/mob/manifest.json'],cwd=ROOT))
        comparison = Image.new('RGBA',(1600,950),BG)
        for row,(mm,title) in enumerate([(old_mobs,'PREVIOUS / 2D pixel finish'),(mobs,'NEW / original 3D block models')]):
            y=row*475
            text(comparison,(40,y+20),title,26,bold=True)
            for i,(mid,s) in enumerate(mm['mobs'].items()):
                if row:
                    img=Image.open(ROOT/s['sheet'])
                else:
                    img=Image.open(io.BytesIO(subprocess.check_output(
                        ['git','show',f"{args.before_ref}:{s['sheet']}"],cwd=ROOT)))
                w,h=s['frame']['w'],s['frame']['h']
                scale=min(2.6,260/w,330/h)
                sprite(comparison,img.crop((0,0,w,h)),(160+i*320,y+410),
                       (s['anchor']['x'],s['anchor']['y']),scale)
                text(comparison,(55+i*320,y+435),mid.upper(),18,bold=True)
        comparison.convert('RGB').save(OUT/'monsters-before-after.png')

    monster_motion=[]
    for pose in ['move','hit','die']:
        count=max(len(s['animations'][pose]) for s in mobs['mobs'].values())
        for fi in range(count):
            im=Image.new('RGBA',(1500,420),BG)
            text(im,(35,20),f'MUSHROOM / VOXEL CREATURES / {pose.upper()}',23,bold=True)
            for i,(mid,s) in enumerate(mobs['mobs'].items()):
                w,h=s['frame']['w'],s['frame']['h']
                indices=s['animations'][pose]
                f=indices[min(fi,len(indices)-1)]
                img=Image.open(ROOT/s['sheet']).crop((f*w,0,(f+1)*w,h))
                sprite(im,img,(150+i*300,365),(s['anchor']['x'],s['anchor']['y']),min(2.4,245/w,270/h))
            monster_motion.append(im.convert('RGB'))
    palette=monster_motion[0].quantize(colors=192)
    monster_motion=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in monster_motion]
    monster_motion[0].save(OUT/'monster-motion.gif',save_all=True,append_images=monster_motion[1:],duration=180,loop=0,disposal=2)
    print('Review boards:',OUT)


if __name__=='__main__':
    main()
