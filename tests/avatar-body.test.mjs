import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createCanvas,loadImage} from '@napi-rs/canvas';
import {BODY_FIELDS,BODY_PRESETS,DEFAULT_BODY,normalizeBody,bodyKey,withBody,avatarBody,bodyPoint,bodyY,sourceBodyY} from '../src/client/avatar-body.js';
import {deformBodySheet} from '../src/client/avatar-body-raster.js';
import {createAvatarRenderer} from '../src/client/avatar.js';
import {normalizeAvatar,pickAvatar} from '../src/client/avatar-data.js';
import {readProfile,writeProfile} from '../src/client/store.js';
import {cleanPresenceState} from '../src/client/backend/common.js';
import {handAnchor} from '../src/client/game/avatar-hand-anchors.js';
import {createBodyEditor} from '../src/client/ui/body-editor.js';
import {installDomFixture} from './helpers/dom-fixture.mjs';

globalThis.OffscreenCanvas=class {constructor(w,h){return createCanvas(w,h)}};
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url)));
const images=new Map();
const assets={...manifest,frameCount:manifest.frames.length,frameNames:manifest.frames,source:'manifest',frameIndex:Object.fromEntries(manifest.frames.map((n,i)=>[n,i])),
 hasLayer:(layer,id)=>manifest.files[layer]?.includes(id),getLayer:(layer,id)=>{const key=layer+'/'+id;if(!images.has(key))images.set(key,loadImage(new URL('../assets/avatar/'+key+'.png',import.meta.url).pathname));return images.get(key);}};
assert.deepEqual(normalizeBody(null),DEFAULT_BODY);assert.deepEqual(normalizeBody([]),DEFAULT_BODY);
for(const field of BODY_FIELDS){
 for(const bad of [NaN,Infinity,-Infinity,'110',{},null])assert.equal(normalizeBody({[field.key]:bad})[field.key],100);
 assert.equal(normalizeBody({[field.key]:-1e9})[field.key],field.min);
 assert.equal(normalizeBody({[field.key]:1e9})[field.key],field.max);
}
const avatar=normalizeAvatar(manifest.presets[0].avatar);
for(const preset of BODY_PRESETS){
 const av=withBody(avatar,preset.values);
 assert.equal(Object.keys(av).length,7);assert.deepEqual(pickAvatar(av),avatar);assert.deepEqual(JSON.parse(JSON.stringify(av)),avatar);
 assert.deepEqual(avatarBody({...av,hat:'none'}),preset.values);
 for(let y=0;y<=192;y+=.5)assert.ok(Math.abs(sourceBodyY(preset.values,bodyY(preset.values,y))-y)<1e-8);
}
const memory=new Map();globalThis.localStorage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v)};
for(const preset of BODY_PRESETS){
 assert(writeProfile('profile',{nickname:'체형검증',avatar,body:preset.values}));
 assert.deepEqual(readProfile('profile').body,preset.values);
 const peer=cleanPresenceState({user_id:'peer',nickname:'친구',avatar,body:JSON.parse(JSON.stringify(preset.values))});assert.deepEqual(peer.body,preset.values);
}
memory.set('legacy',JSON.stringify({nickname:'옛모험가',avatar}));assert.deepEqual(readProfile('legacy').body,DEFAULT_BODY);
assert.equal(cleanPresenceState({user_id:'peer',body:{head:1e9}}).body.head,110);
// Native raster: identity is exact; distant frames never bleed into one another.
const synthetic=createCanvas(288,192),sc=synthetic.getContext('2d');sc.fillStyle='red';sc.fillRect(0,0,144,192);sc.fillStyle='blue';sc.fillRect(144,0,144,192);
assert.equal(deformBodySheet(synthetic,DEFAULT_BODY,{frameW:144,frameH:192,anchorX:72,makeCanvas:createCanvas}),synthetic);
const warped=deformBodySheet(synthetic,BODY_PRESETS[3].values,{frameW:144,frameH:192,anchorX:72,makeCanvas:createCanvas});
const wd=warped.getContext('2d').getImageData(0,0,288,192).data;
for(let y=0;y<192;y++)for(let x=0;x<288;x++){const i=(y*288+x)*4;if(wd[i+3])assert.equal(wd[i+(x<144?2:0)],0);}
const renderer=createAvatarRenderer(assets),frames=[];
for(const preset of BODY_PRESETS){
 const av=withBody(avatar,preset.values);await renderer.ready(av);
 const cv=createCanvas(144,192),ctx=cv.getContext('2d');
 for(let f=0;f<13;f++){
  ctx.clearRect(0,0,144,192);assert(renderer.draw(ctx,av,72,180,1.5,f,false));
  const data=ctx.getImageData(0,0,144,192).data;assert(data.some((v,i)=>i%4===3&&v>0));
  const hand=handAnchor(f),expected=bodyPoint(preset.values,{x:hand.N[0],y:hand.N[1]});assert.deepEqual(renderer.handFit(av,f).near,expected);
  renderer.drawGrip(ctx,av,72,180,1.5,f,false);renderer.costumeFit(av,f);renderer.headTopFrame(av,f);
 }
 ctx.clearRect(0,0,144,192);renderer.draw(ctx,av,72,180,1.5,0,false);frames.push(Buffer.from(ctx.getImageData(0,0,144,192).data));
 assert(renderer.headTop(av)>0);renderer.drawClimb(ctx,av,72,180,1.5,100,true);
}
assert.notDeepEqual(frames[0],frames[1]);assert.notDeepEqual(frames[0],frames[2]);assert.notDeepEqual(frames[2],frames[3]);
const canvas=createCanvas(1440,192),context=canvas.getContext('2d');let calls=0;
const proxy=new Proxy(context,{get(target,key){const v=Reflect.get(target,key,target);return typeof v==='function'?((...args)=>{if(key==='drawImage')calls++;return v.apply(target,args);}):v;},set(target,key,val){target[key]=val;return true;}});
const prepared=renderer.stats.composites;
for(let i=0;i<20;i++)renderer.draw(proxy,withBody(avatar,BODY_PRESETS[i%4].values),36+i*65,180,1,i%13,false);
assert.equal(calls,20);assert.equal(renderer.stats.composites,prepared);
// Real editor handlers: presets, slider, release, reset, disabling and disposal.
const dom=installDomFixture({createCanvas}),ac=new AbortController(),changes=[];
const editor=createBodyEditor({on:(el,type,fn)=>el.addEventListener(type,fn,{signal:ac.signal}),initial:DEFAULT_BODY,onChange:(value,options)=>changes.push({value,options})});
assert(dom.find(editor.el,'body-head').disabled);editor.setEnabled(true);
dom.find(editor.el,'body-preset-guardian').dispatchEvent(new Event('click'));
assert.equal(editor.getValue().shoulders,112);assert.equal(dom.find(editor.el,'body-preset-guardian').getAttribute('aria-pressed'),'true');
const slider=dom.find(editor.el,'body-waist');slider.value='91';slider.dispatchEvent(new Event('input'));assert.equal(editor.getValue().waist,91);assert.equal(dom.find(editor.el,'body-waist-value').textContent,'91%');assert.equal(dom.find(editor.el,'body-selection').textContent,'직접 조정');assert.equal(changes.at(-1).options.commit,false);
slider.dispatchEvent(new Event('change'));assert.equal(changes.at(-1).options.commit,true);
dom.find(editor.el,'body-reset').dispatchEvent(new Event('click'));assert.deepEqual(editor.getValue(),DEFAULT_BODY);
editor.setValue(BODY_PRESETS[1].values);assert.equal(dom.find(editor.el,'body-head').value,'110');
editor.setEnabled(false);assert(dom.find(editor.el,'body-head').disabled);
const before=changes.length;ac.abort();slider.dispatchEvent(new Event('input'));assert.equal(changes.length,before);
assert.equal(dom.all(editor.el).filter(n=>n.tagName==='INPUT').length,9);
renderer.clear();assert.equal(renderer.cacheSize,0);
console.log('PASS body bounds/migration/Presence; four actual-asset silhouettes across 13 frames; transformed hand anchors; 20 cached actors = 20 draws; editor preset/slider/reset/disposal');
