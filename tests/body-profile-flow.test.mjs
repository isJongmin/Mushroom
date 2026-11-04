// Full profile screen event flow in a DOM fixture + native Canvas, not browser layout QA.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createCanvas,loadImage} from '@napi-rs/canvas';
import {installDomFixture} from './helpers/dom-fixture.mjs';
import {normalizeAvatar} from '../src/client/avatar-data.js';
import {BODY_PRESETS,DEFAULT_BODY} from '../src/client/avatar-body.js';
import {readProfile} from '../src/client/store.js';
import {mount} from '../src/client/screens/profile.js';
const dom=installDomFixture({createCanvas}),memory=new Map(),frames=new Map();let frameId=0;
globalThis.window=new EventTarget();window.devicePixelRatio=1;
globalThis.getComputedStyle=()=>({getPropertyValue:()=> '3'});
globalThis.localStorage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,v)};
globalThis.requestAnimationFrame=fn=>{frames.set(++frameId,fn);return frameId;};globalThis.cancelAnimationFrame=id=>frames.delete(id);
globalThis.OffscreenCanvas=class {constructor(w,h){return createCanvas(w,h)}};
const m=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url))),images=new Map();
const assets={...m,frameCount:m.frames.length,frameNames:m.frames,source:'manifest',frameIndex:Object.fromEntries(m.frames.map((n,i)=>[n,i])),defaultAvatar:normalizeAvatar(m.presets[0].avatar),
 sanitizeAvatar:normalizeAvatar,labelOf:(part,id)=>m.parts[part].find(p=>p.id===id)?.label||id,
 hasLayer:(layer,id)=>m.files[layer]?.includes(id),getLayer:(layer,id)=>{const key=layer+'/'+id;if(!images.has(key))images.set(key,loadImage(new URL('../assets/avatar/'+key+'.png',import.meta.url).pathname));return images.get(key);}};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const root=document.createElement('div'),nav=[],app={mode:'local',profileKey:'qa',profile:null,providers:{},assets:Promise.resolve(assets),go:(...args)=>nav.push(args),placeModeBadge(){}};
const screen=mount(root,app);await tick();
assert(app.providers.profile().ready);
assert.equal(dom.find(root,'studio-body-tab').getAttribute('aria-selected'),'true');
dom.find(root,'body-preset-ranger').dispatchEvent(new Event('click'));
const waist=dom.find(root,'body-waist');waist.value='95';waist.dispatchEvent(new Event('input'));
// Save before the 100ms preview timer: persisted state must still be the latest slider value.
const nick=dom.find(root,'nickname-input');nick.value='새모험가';nick.dispatchEvent(new Event('input'));
dom.find(root,'studio-wardrobe-tab').dispatchEvent(new Event('click'));assert.equal(dom.find(root,'studio-wardrobe-tab').getAttribute('aria-selected'),'true');
dom.find(root,'preset-1').dispatchEvent(new Event('click'));assert.equal(app.providers.profile().body.waist,95,'wardrobe presets preserve proportions');
dom.find(root,'create-submit').dispatchEvent(new Event('click'));
assert.equal(nav.at(-1)[0],'lobby');assert.equal(app.profile.body.waist,95);assert.equal(app.profile.body.legLength,155);assert.deepEqual(readProfile('qa').body,app.profile.body);assert.equal(Object.keys(app.profile.avatar).length,7);
screen.unmount();assert.equal(frames.size,0);
// Reopen, adjust, cancel: no saved data changes, and cleanup cancels pending repaint.
const original=structuredClone(app.profile),editRoot=document.createElement('div'),edit=mount(editRoot,app,{mode:'edit'});await tick();
assert.equal(dom.find(editRoot,'body-waist').value,'95');
dom.find(editRoot,'body-preset-guardian').dispatchEvent(new Event('click'));assert.equal(app.providers.profile().body.shoulders,155);
dom.find(editRoot,'profile-cancel').dispatchEvent(new Event('click'));assert.deepEqual(app.profile,original);assert.deepEqual(readProfile('qa').body,original.body);
edit.unmount();assert.equal(frames.size,0);
// Reopen + reset: body-only reset must not alter selected clothing.
const resetRoot=document.createElement('div'),reset=mount(resetRoot,app,{mode:'edit'});await tick();
const before=app.providers.profile().avatar;dom.find(resetRoot,'body-reset').dispatchEvent(new Event('click'));assert.deepEqual(app.providers.profile().body,DEFAULT_BODY);assert.deepEqual(app.providers.profile().avatar,before);
reset.unmount();await tick();assert.equal(frames.size,0);
console.log('PASS full profile mount: tabs, presets, immediate save before preview debounce, reentry, cancel, independent reset and cleanup');
