import assert from 'node:assert/strict';
import {areaMap,drawBiomeMap} from '../src/client/game/areas.js';
import {createCanvas} from '@napi-rs/canvas';
import {drawMascot,drawAdventureScenery,drawRegionMascot,drawAdventureCharm,REGION_CHARACTER} from '../src/client/game/adventure-art.js';
const render=(fn)=>{const canvas=createCanvas(1024,768),c=canvas.getContext('2d');fn(c);assert.deepEqual([c.getTransform().a,c.getTransform().d,c.getTransform().e,c.getTransform().f],[1,1,0,0]);return canvas.toBuffer('image/png');};
const appearances=[],biomes=[];
for(const area of ['quarry','forest','frost']){const map=areaMap(area);biomes.push(render(c=>drawBiomeMap(c,map,250,400,1,1024,768)).toString('base64'));}
assert.equal(new Set(biomes).size,3,'snow peaks and firs differ from mine crystals and forest canopy');
for(const area of Object.keys(REGION_CHARACTER)){
 const map={id:area,width:6000,groundY:650,spawn:{x:900}};
 const mascot=(now,reduced)=>render(c=>drawMascot(c,area,400,500,2,now,{reduced}));
 appearances.push(mascot(0,true).toString('base64'));
 assert.deepEqual(mascot(0,true),mascot(3995,true),'reduced motion freezes all mascot poses');
 assert.notDeepEqual(mascot(0,false),mascot(3980,false),'blink and idle movement render');
 const scene=(camX,now,reduced)=>render(c=>drawAdventureScenery(c,map,camX,0,1,now,{reduced}));
 assert.deepEqual(scene(300,0,true),scene(300,1900,true));
 assert.notDeepEqual(scene(300,0,false),scene(300,1500,false));
 const visible=render(c=>drawRegionMascot(c,map,300,0,1,0));
 const culled=render(c=>drawRegionMascot(c,map,4000,0,1,0));
 assert.notDeepEqual(visible,culled);
 assert.deepEqual(culled,render(()=>{}),'offscreen mascot is culled');
 // Camera culling must never change the world positions of repeated props.
 const a=createCanvas(1024,768),b=createCanvas(1024,768);
 drawAdventureScenery(a.getContext('2d'),map,0,0,1,0,{reduced:true});
 drawAdventureScenery(b.getContext('2d'),map,600,0,1,0,{reduced:true});
 assert.deepEqual(a.getContext('2d').getImageData(600,0,424,768).data,b.getContext('2d').getImageData(0,0,424,768).data,'camera overlap keeps identical world art');
 // World props must have bounded work even in a very wide region.
 render(c=>drawAdventureScenery(c,{...map,width:1e9},500000,0,2,1200));
}
assert.equal(new Set(appearances).size,4,'four distinct silhouettes');
const charm=options=>render(c=>drawAdventureCharm(c,300,500,2,{fit:{neck:46,bodyX:1},...options}));
assert.deepEqual(charm({hidden:true}),render(()=>{}));
assert.deepEqual(charm({moving:true,reduced:true,now:0}),charm({moving:true,reduced:true,now:200}));
assert.notDeepEqual(charm({job:'mage'}),charm({job:'warrior'}));
console.log('PASS regional art: four silhouettes, reduced motion, visible culling, bounded scenery and balanced Canvas transforms');
