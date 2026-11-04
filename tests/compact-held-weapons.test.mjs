import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {drawItem} from '../src/client/game/progression-visuals.js';
import {drawEquippedGear} from '../src/client/game/appearance-motion.js';
import {GRADE_COLORS} from '../src/client/game/progression.js';
const measure=draw=>{const cv=createCanvas(180,180),c=cv.getContext('2d');draw(c);const d=c.getImageData(0,0,180,180).data;let pixels=0,x1=180,x2=0,y1=180,y2=0;for(let y=0;y<180;y++)for(let x=0;x<180;x++)if(d[(y*180+x)*4+3]>8){pixels++;x1=Math.min(x1,x);x2=Math.max(x2,x);y1=Math.min(y1,y);y2=Math.max(y2,y);}return {pixels,width:x2-x1+1,height:y2-y1+1};};
for(const kind of ['sword','staff','bow','claw','shield'])for(let tier=0;tier<5;tier++){
 const icon=measure(c=>drawItem(c,kind,90,90,1,GRADE_COLORS[tier],tier));
 const held=measure(c=>drawItem(c,kind,90,90,1,GRADE_COLORS[tier],tier,{held:true}));
 assert(held.width<icon.width*.8,`${kind}/${tier} held silhouette stays slender despite longer reach`);
}
for(const kind of ['sword','staff'])for(const left of [false,true]){
 const b=measure(c=>drawEquippedGear(c,'warrior',{weapon:kind,tier:4,shield:-1},90,130,1,0,{left,frame:2,reduced:true,drawItem}));
 assert(b.width>b.height,kind+' rests nearly horizontal instead of covering the face');
}
const big=measure(c=>drawEquippedGear(c,'warrior',{weapon:'sword',tier:0,shield:-1},90,130,1,0,{drawItem,bodyScale:1}));
const small=measure(c=>drawEquippedGear(c,'warrior',{weapon:'sword',tier:0,shield:-1},90,130,1,0,{drawItem,bodyScale:.1}));assert(small.pixels<big.pixels*.3);
for(const [kind,minLength]of [['sword',65],['staff',68],['bow',53],['claw',32]]){const b=measure(c=>drawItem(c,kind,90,90,1,GRADE_COLORS[0],0,{held:true}));assert(b.height>=minLength,kind+' has restored length without enlarging the grip');}
console.log('PASS 25 slender held weapon/grade silhouettes, restored blade/shaft length, horizontal sword/staff rest and scaled small-body gear');
