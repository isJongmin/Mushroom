"""Deterministic 3-D monster sheets using the shared avatar voxel raycaster.

OPENBLAS_NUM_THREADS=1 python3 assets/_src/voxel_mob/build.py --static --jobs 4
OPENBLAS_NUM_THREADS=1 python3 assets/_src/voxel_mob/build.py --jobs 4
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import argparse
import json
import time
from multiprocessing import Pool
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from model import assemble, NAMES, MOVE
from vox import render, downsample

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'out'
SCALE=.91
PITCH=12
YAW=18


def render_frame(task):
    kind,frame,spec=task
    started=time.time()
    boxes=assemble(kind,frame)
    r=render(boxes,YAW,PITCH,SCALE,W=spec['frame']['w'],H=spec['frame']['h'],
             anchor=(spec['anchor']['x'],spec['anchor']['y']))
    arr=downsample(r['img'],r['a'])
    # Only the geometric raycaster is involved in sprite generation.
    return kind,frame,arr,len(boxes),round(time.time()-started,2)


def contact(images,path,*,frames=False):
    cols=5 if not frames else 6
    cellw,cellh=(244,245) if not frames else (244,245)
    rows=(len(images)+cols-1)//cols
    board=Image.new('RGB',(cols*cellw,rows*cellh),'#f0e7d4')
    draw=ImageDraw.Draw(board)
    try: font=ImageFont.truetype('DejaVuSans.ttf',15)
    except OSError: font=None
    for i,(label,im) in enumerate(images):
        x=i%cols*cellw;y=i//cols*cellh
        draw.rectangle((x+5,y+5,x+cellw-5,y+cellh-5),fill='#d8dac5')
        # Upscale small sprites enough to inspect true cuboid edges and faces.
        factor=min(2.5,(cellw-20)/im.width,(cellh-40)/im.height)
        im=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.NEAREST)
        board.paste(im,(x+(cellw-im.width)//2,y+25+(cellh-30-im.height)//2),im)
        draw.text((x+13,y+10),label,fill='#494137',font=font)
    board.save(path)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--static',action='store_true');ap.add_argument('--jobs',type=int,default=4)
    ap.add_argument('--only', nargs='+', choices=NAMES)
    args=ap.parse_args()
    names=args.only or NAMES
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'assets/mob/manifest.json').read_text())
    tasks=[(k,f,manifest['mobs'][k]) for k in names for f in ([0] if args.static else range(manifest['mobs'][k]['frames']))]
    images={k:{} for k in names};report=[]
    with Pool(args.jobs) as pool:
        for k,f,arr,count,seconds in pool.imap_unordered(render_frame,tasks):
            im=Image.fromarray(arr)
            images[k][f]=im
            bbox=im.getbbox()
            if not bbox: raise AssertionError(f'empty {k}:{f}')
            if bbox[0]<=0 or bbox[1]<=0 or bbox[2]>=im.width or bbox[3]>=im.height:
                raise AssertionError(f'clipped {k}:{f}: {bbox} in {im.size}')
            report.append(dict(kind=k,frame=f,boxes=count,seconds=seconds,bbox=bbox))
            print(f'{k}:{f} boxes={count} {seconds}s bbox={bbox}',flush=True)
    contact([(k,images[k][0]) for k in names],OUT/('biome-static-contact.png' if args.only else 'static-contact.png'))
    for k in names:
        images[k][0].save(OUT/f'{k}-static.png')
    if not args.static:
        for k in names:
            spec=manifest['mobs'][k];w=spec['frame']['w'];h=spec['frame']['h'];n=spec['frames']
            sheet=Image.new('RGBA',(w*n,h))
            for f in range(n):sheet.paste(images[k][f],(f*w,0))
            sheet.save(ROOT/spec['sheet'],optimize=True)
            frames=[images[k][f] for f in spec['animations']['move']]
            frames[0].save(OUT/f'{k}-move.gif',save_all=True,append_images=frames[1:],duration=round(1000/spec['fps']),loop=0,disposal=2)
        contact([(f'{k} {f}',images[k][f]) for k in names for f in sorted(images[k])],OUT/('biome-all-frames.png' if args.only else 'all-frames.png'),frames=True)
        manifest['revision']='fine-voxel-mobs-20261029-v3'
        manifest['mobArt']={'source':'assets/_src/voxel_mob','renderer':'shared voxel/vox.py analytic cuboid raycaster',
                            'model':'original solid 3D stepped box geometry','voxelSheetPx':1.82,
                            'yaw':YAW,'pitch':PITCH,'direction':'right; runtime mirrors left'}
        for k in names:
            manifest['mobs'][k]['artStyle']='fine-voxel-3d'
            manifest['mobs'][k]['pixelArt']=False  # Shared SS4 output has intentional smooth coverage.
        (ROOT/'assets/mob/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report.sort(key=lambda x:(NAMES.index(x['kind']),x['frame']))
    (OUT/(('biome-' if args.only else '')+('static-report.json' if args.static else 'build-report.json'))).write_text(json.dumps(report,indent=2)+'\n')
    print(f'complete: {len(report)} geometric frames; {OUT}',flush=True)


if __name__=='__main__':main()
