import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { loadAvatarAssets } from '../src/client/assets.js';
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url)));
const previous=globalThis.fetch;
try{
 globalThis.fetch=async()=>({ok:true,json:async()=>manifest});
 const a=await loadAvatarAssets();
 assert.equal(a.presets.length,16);
 assert.deepEqual(a.presets.slice(-4).map(p=>p.label),manifest.presets.slice(-4).map(p=>p.label));
 for(const id of ['bald','wolf-cut','mohawk','pompadour'])assert.ok(a.parts.hair.some(p=>p.id===id));
 for(const p of a.presets.slice(-4))assert.deepEqual(a.sanitizeAvatar(p.avatar),p.avatar);
 assert.equal(a.imageCount,0,'new outfits remain lazy-loaded');
}finally{globalThis.fetch=previous;}
console.log('PASS all16 outfit presets reach actual asset loader and new styles remain lazy');
