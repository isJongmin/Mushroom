import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createCanvas,Image} from '@napi-rs/canvas';
import {expandWardrobe,WARDROBE_VARIANTS} from '../src/client/wardrobe-catalog.js';
import {loadAvatarAssets} from '../src/client/assets.js';
import {createAvatarRenderer} from '../src/client/avatar.js';
import {cleanSkinColor,withSkinColor,avatarSkinColor,recolorAvatarSheet} from '../src/client/avatar-palette.js';
import {readProfile,writeProfile} from '../src/client/store.js';
import {cleanPresenceState} from '../src/client/backend/common.js';
const raw=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url))),before=JSON.stringify(raw),expanded=expandWardrobe(raw);
for(const bad of [null,{}, {parts:{skin:3},files:{},layerOrder:[]},{parts:{},files:{skin:null},layerOrder:[]},{parts:{},files:{},layerOrder:[null]}])assert.doesNotThrow(()=>expandWardrobe(bad));
assert.equal(JSON.stringify(raw),before,'catalog does not mutate the source manifest');
assert.deepEqual(Object.fromEntries(['skin','face','hair','top','bottom'].map(p=>[p,expanded.manifest.parts[p].length])),{skin:10,face:19,hair:35,top:32,bottom:24});
for(const v of expanded.variants.values()){assert(/^[a-z0-9-]{1,32}$/.test(v.id));assert(raw.parts[v.part].some(p=>p.id===v.source));for(const layer of raw.layerOrder.filter(l=>l.part===v.part)){if(expanded.manifest.files[layer.layer].includes(v.id))assert(raw.files[layer.layer].includes(v.source));}}
assert.equal(cleanSkinColor('#AbC123'),'#abc123');for(const bad of ['red','#abc','url(x)','<script>',{},123,null])assert.equal(cleanSkinColor(bad),null);
const memory=new Map();globalThis.localStorage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v)};
memory.set('old',JSON.stringify({nickname:'오래된캐릭터',avatar:raw.presets[0].avatar,body:{head:200,legs:10}}));assert(!('body'in readProfile('old')));assert.equal(readProfile('old').skinColor,null);
assert(writeProfile('new',{nickname:'피부색검증',avatar:raw.presets[0].avatar,skinColor:'#C58A61',body:{head:200}}));assert.equal(readProfile('new').skinColor,'#c58a61');assert(!('body'in JSON.parse(memory.get('new'))));
const peer=cleanPresenceState({user_id:'peer',avatar:raw.presets[0].avatar,skinColor:'#C58A61',body:{head:200}});assert.equal(peer.skinColor,'#c58a61');assert(!('body'in peer));
globalThis.fetch=async()=>({ok:true,json:async()=>raw});const requests=[];const setSrc=Object.getOwnPropertyDescriptor(Image.prototype,'src').set;
globalThis.Image=function(){const image=new Image();Object.defineProperty(image,'src',{set(value){requests.push(new URL(value).pathname);setSrc.call(image,readFileSync(new URL(value).pathname));}});return image;};
globalThis.OffscreenCanvas=class{constructor(w,h){return createCanvas(w,h)}};
const assets=await loadAvatarAssets();assert.equal(assets.source,'manifest');assert.equal(assets.parts.hair.length,35);
let changed=0;
for(const v of WARDROBE_VARIANTS){
 const layer=v.part==='hair'?'hair_front':v.part;assert(assets.hasLayer(layer,v.id));
 const image=await assets.getLayer(layer,v.id),original=await assets.getLayer(layer,v.source);assert(image,'variant image '+v.id);assert.equal(image.naturalWidth,original.naturalWidth);assert.equal(image.naturalHeight,192);
 const a=createCanvas(image.naturalWidth,192),b=createCanvas(original.naturalWidth,192);a.getContext('2d').drawImage(image,0,0);b.getContext('2d').drawImage(original,0,0);const ad=a.getContext('2d').getImageData(0,0,a.width,192).data,bd=b.getContext('2d').getImageData(0,0,b.width,192).data;
 let different=false;for(let i=0;i<ad.length;i+=4){assert.equal(ad[i+3],bd[i+3],'alpha/silhouette preserved for '+v.id);if(ad[i]!==bd[i]||ad[i+1]!==bd[i+1]||ad[i+2]!==bd[i+2])different=true;}
 assert(different,'new colorway must visibly change pixels: '+v.id);changed++;
}
assert(requests.every(path=>existsSync(path)),'virtual choices only request shipped source PNGs');
const renderer=createAvatarRenderer(assets),base=assets.sanitizeAvatar(raw.presets[0].avatar),normal=withSkinColor(base,null),custom=withSkinColor(base,'#9c6848');assert.equal(Object.keys(custom).length,7);assert.equal(avatarSkinColor({...custom,hat:'none'}),'#9c6848');
await renderer.ready(normal);await renderer.ready(custom);
function pixels(av){const c=createCanvas(144,192),ctx=c.getContext('2d');renderer.draw(ctx,av,72,180,1.5,0,false);return ctx.getImageData(0,0,144,192).data;}
assert.notDeepEqual(pixels(normal),pixels(custom));assert.deepEqual(pixels(normal),pixels({...normal,body:{head:200}}),'legacy body fields never deform the character');
for(let frame=0;frame<13;frame++){const c=createCanvas(144,192);assert(renderer.draw(c.getContext('2d'),custom,72,180,1.5,frame,true));}
renderer.clear();console.log('PASS '+changed+' real-asset colorways with preserved silhouettes; source-only PNG requests; custom skin persistence/Presence and all 13 poses; legacy body ignored');
