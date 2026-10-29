// CANVAS_MODULE=/absolute/path/to/@napi-rs/canvas/index.js node tests/avatar-hat.test.mjs
import assert from 'node:assert/strict';
import { createAvatarRenderer } from '../src/client/avatar.js';
const {createCanvas} = await import(process.env.CANVAS_MODULE || '@napi-rs/canvas');
globalThis.OffscreenCanvas=class {constructor(w,h){return createCanvas(w,h)}};
const sheet=(color,paint)=>{const cv=createCanvas(20,10),c=cv.getContext('2d');c.fillStyle=color;paint(c);Object.defineProperty(cv,'naturalWidth',{value:20});return cv;};
const hair=sheet('#ff0000',c=>c.fillRect(0,0,20,10));
const skin=sheet('#0000ff',c=>{c.fillRect(3,3,4,7);c.fillRect(13,3,4,7)});
const hat=sheet('#00ff00',c=>{c.fillRect(3,4,4,1);c.fillRect(13,6,4,1)});
const assets={frame:{w:10,h:10},anchor:{x:5,y:10},density:1,frameCount:2,animations:{idle:{frames:[0],ms:100}},frameIndex:{front:0},frameNames:[],source:'manifest',
 layerOrder:[{layer:'skin',part:'skin',blend:'source-over'},{layer:'hair',part:'hair',blend:'source-over'},{layer:'hat',part:'hat',blend:'source-over'}],
 hasLayer:(layer,id)=>id!=='none',getLayer:async(layer)=>({hair,skin,hat})[layer]};
const renderer=createAvatarRenderer(assets);
for(const hatId of ['cap-black','none','ribbon-pink']) {
 const avatar={skin:'skin',hair:'hair',hat:hatId};await renderer.ready(avatar);
 for(const frame of [0,1]) {
  const cv=createCanvas(10,10),c=cv.getContext('2d');assert(renderer.draw(c,avatar,5,10,1,frame,false));
  const pixel=(x,y)=>Array.from(c.getImageData(x,y,1,1).data);
  assert.deepEqual(pixel(1,8),[255,0,0,255]); // loose hair retained
  if(hatId==='cap-black') {assert.ok(pixel(1,0)[3]<32);const brim=pixel(4,frame?6:4);assert.ok(brim[1]>200 && brim[0]<60 && brim[3]===255);}
  else assert.deepEqual(pixel(1,0),[255,0,0,255]); // none/ribbon retains crown
 }
}
console.log('PASS hat clipping follows each frame; lower hair and ribbon hairstyles retained');
