"""Contract, frame bounds, geometry, animation and deterministic render checks."""
import hashlib
import json
import subprocess
from pathlib import Path
from multiprocessing import Pool
from PIL import Image
import numpy as np
from build import ROOT, OUT, render_frame
from model import NAMES, MOVE, assemble


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest=json.loads((ROOT/'assets/mob/manifest.json').read_text())
    original=json.loads(subprocess.check_output(['git','show','HEAD:assets/mob/manifest.json'],cwd=ROOT))
    # Only explicitly owned art metadata may differ from the committed contract.
    for key,value in original.items():
        if key not in ('revision','mobs'):
            assert manifest[key]==value, f'changed non-mob metadata {key}'
    assert set(manifest['mobs'])==set(original['mobs'])
    checks=[]
    for k in NAMES:
        spec=manifest['mobs'][k];before=original['mobs'][k]
        for key,value in before.items():
            if key!='pixelArt':assert spec[key]==value, f'changed gameplay/frame contract {k}:{key}'
        assert spec['pixelArt'] is False
        w,h=spec['frame']['w'],spec['frame']['h']
        image=Image.open(ROOT/spec['sheet']).convert('RGBA')
        assert image.size==(w*spec['frames'],h)
        anim=spec['animations']
        assert [len(anim[a]) for a in ('move','hit','die')]==[MOVE[k],1,4]
        assert sorted(sum(anim.values(),[]))==list(range(spec['frames']))
        hashes=[]
        for f in range(spec['frames']):
            frame=image.crop((f*w,0,(f+1)*w,h));bbox=frame.getbbox()
            assert bbox and bbox[0]>0 and bbox[1]>0 and bbox[2]<w and bbox[3]<h, (k,f,bbox)
            assert np.asarray(frame)[...,3].max()==255
            hashes.append(sha(frame.tobytes()))
            boxes=assemble(k,f)
            assert len(boxes)>=20 and all(np.all(b.h>0) for b in boxes)
        assert len(set(hashes))==len(hashes), f'duplicate animation frame: {k}'
        checks.append(dict(kind=k,size=image.size,frames=spec['frames'],frameHashes=hashes,
                           sheetSha256=sha((ROOT/spec['sheet']).read_bytes())))
    # Every representative 3-D frame must render byte-identically from the sources.
    with Pool(4) as pool:
        for k,f,arr,_,_ in pool.map(render_frame,[(k,0,manifest['mobs'][k]) for k in NAMES]):
            spec=manifest['mobs'][k];w,h=spec['frame']['w'],spec['frame']['h']
            actual=np.asarray(Image.open(ROOT/spec['sheet']).convert('RGBA').crop((0,0,w,h)))
            assert np.array_equal(arr,actual),f'non-deterministic frame {k}:{f}'
    for name in ('ghost.png','tombstone.png','drop_bag.png'):
        relative=f'assets/mob/{name}'
        assert subprocess.check_output(['git','show',f'HEAD:{relative}'],cwd=ROOT)==(ROOT/relative).read_bytes(),relative
    fx_changes=subprocess.check_output(['git','diff','--name-only','HEAD','--','assets/fx'],cwd=ROOT).decode().strip()
    assert not fx_changes, f'changed unowned effects: {fx_changes}'
    result=dict(result='PASS',geometricFrames=sum(c['frames'] for c in checks),
                allAnimationFramesDistinct=True,allFramesUnclipped=True,
                originalGameplayAndFramesPreserved=True,representativeRerenderByteIdentical=5,
                extraMobPngsUnchanged=3,fxUnchanged=True,sheets=checks)
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='sheets'},indent=2))


if __name__=='__main__':main()
