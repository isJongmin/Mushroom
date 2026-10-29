"""Run: python tests/avatar-wardrobe.test.py (Pillow, NumPy)."""
import itertools
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/_src/voxel'))
import model

NEW = {
    'hair': ['bald', 'wolf-cut', 'mohawk', 'pompadour'],
    'top': ['warrior-armor', 'archer-ranger', 'mage-robe', 'thief-jacket'],
    'bottom': ['warrior-greaves', 'ranger-trousers', 'mage-trousers', 'thief-trousers'],
    'shoes': ['warrior-sabatons', 'ranger-boots', 'mage-boots', 'thief-boots'],
    'hat': ['warrior-circlet', 'ranger-cap', 'mage-hat', 'thief-hood'],
}

class Wardrobe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'assets/avatar/manifest.json').read_text())

    def test_contract_and_complete_assets(self):
        m = self.manifest
        self.assertEqual(list(m['parts']), model.CATS)
        for cat, ids in NEW.items():
            catalog = {p['id'] for p in m['parts'][cat]}
            for pid in ids:
                self.assertIn(pid, catalog)
                layers = [x['layer'] for x in m['layerOrder'] if x['part'] == cat]
                found = [layer for layer in layers if pid in m['files'][layer]]
                self.assertTrue(found, f'missing {cat}:{pid}')
                for layer in found:
                    with Image.open(ROOT/'assets/avatar'/layer/(pid+'.png')) as im:
                        self.assertEqual(im.size, (m['frame']['w']*len(m['frames']), m['frame']['h']))
                        a=np.asarray(im.convert('RGBA'))[...,3]
                        if pid=='bald': self.assertFalse(a.any())
                        else:
                            # Every pose has room at the sheet edge for weapons/hair.
                            for n in range(len(m['frames'])):
                                f=a[:,n*m['frame']['w']:(n+1)*m['frame']['w']]
                                self.assertFalse(f[0].any() or f[-1].any() or f[:,0].any() or f[:,-1].any(),f'{layer}/{pid} frame{n} clips')

    def test_hair_geometry_silhouettes(self):
        self.assertEqual(model.HAIRS['bald'](),[])
        masks=[]
        for pid in NEW['hair'][1:]:
            defs=model.HAIRS[pid]()
            self.assertTrue(defs)
            # Occupancy signatures ignore material: recoloring cannot pass this check.
            masks.append({tuple(np.round(d['c'],2))+tuple(np.round(d['h'],2)) for d in defs})
        for a,b in itertools.combinations(masks,2):
            self.assertLess(len(a&b)/len(a|b),.7)

    def test_job_presets_and_items(self):
        for _,outfit in model.PRESETS[-4:]:
            self.assertEqual(set(outfit),set(model.CATS))
            for cat,pid in outfit.items():
                self.assertIn(pid,dict(model.LABELS[cat]))
            defs=model.TOPS[outfit['top']]()
            self.assertTrue(any(d['bone'].startswith('arm') for d in defs))
        mage=model.TOPS['mage-robe']()
        self.assertTrue(any(d['bone']=='arm-1' and d['h'][1]>=16 for d in mage))
        thief=model.TOPS['thief-jacket']()
        self.assertTrue(any(d['bone']=='arm+1' and d['col']=='#CBD6DF' for d in thief))

if __name__=='__main__': unittest.main()
