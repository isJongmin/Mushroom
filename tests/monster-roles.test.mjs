import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {createMobSim,createMobView,drawMob,monsterRole,monsterDangerBox,monsterTouchDamage} from '../src/client/game/mobs.js';
import {cleanGameEvent,stampGameEvent} from '../src/client/backend/common.js';

const spec=(id,damage=10)=>({id,name:id,hp:300,speed:50,touchDamage:damage,size:{w:50,h:50},behavior:'walk',animations:{move:[],hit:[],die:[]},fps:8,facingLeft:false,pixelArt:false,buffDrop:0});
const kinds=new Map([
 ['ore-beetle',spec('ore-beetle')],
 ['armored-mushroom',spec('armored-mushroom')],
 ['slime',spec('slime')],
]);
const zones=[
 {i:0,id:'charge',x1:0,x2:200,y:500,max:1,mobs:['ore-beetle']},
 {i:1,id:'guard',x1:500,x2:700,y:500,max:1,mobs:['armored-mushroom']},
 {i:2,id:'burst',x1:1000,x2:1200,y:500,max:1,mobs:['slime']},
];
let players=[];const sim=createMobSim({kinds,zones,rnd:()=>.5,getPlayers:()=>players});sim.fill(0);
const initial=sim.snapshot();assert.equal(initial.length,3);const at=kind=>sim.snapshot().find(m=>m.kind===kind);
players=initial.map(m=>({x:m.x+(m.kind==='ore-beetle'?260:m.kind==='armored-mushroom'?120:100),y:500}));
sim.step(2.1,2100);
assert.equal(at('ore-beetle').a,'windup');assert.equal(at('armored-mushroom').a,'guard');assert.equal(at('slime').a,'windup');
const guard=at('armored-mushroom'),guardResult=sim.hit({x1:guard.x-30,x2:guard.x+30,y1:430,y2:510},guard.x+100,1,[100]);
assert.deepEqual(guardResult.dmgs,[30],'front-facing guard blocks 70% damage');
sim.step(.8,2900);const charger=at('ore-beetle'),burst=at('slime');assert.equal(charger.a,'charge');assert.equal(burst.a,'burst');
assert.equal(monsterRole('ore-beetle'),'charger');assert.equal(monsterRole('armored-mushroom'),'guard');assert.equal(monsterRole('slime'),'burst');
const viewShape={...burst,spec:kinds.get('slime')};assert.equal(monsterTouchDamage(viewShape),17);assert.equal(monsterDangerBox(viewShape,{x1:0,x2:1,y1:0,y2:1}).x2,burst.x+92);

const packet=cleanGameEvent('mobs',stampGameEvent('mobs',{t:2900,list:sim.snapshot()},'host'));
assert.equal(packet.list.find(m=>m.kind==='ore-beetle').a,'charge');assert.equal(packet.list.find(m=>m.kind==='slime').a,'burst');
const view=createMobView({kinds});view.apply(packet.list,3000,true);assert.equal([...view.list].find(m=>m.kind==='slime').a,'burst');assert.equal(view.latest().find(m=>m.kind==='ore-beetle').a,'charge');

for(const v of view.list){const canvas=createCanvas(400,300),ctx=canvas.getContext('2d');drawMob(ctx,v,null,200,250,1,3000,1.5);assert.equal(ctx.getTransform().a,1);assert.equal(ctx.globalAlpha,1);}
console.log('PASS telegraphed charger, frontal guard, burst radius, network handoff and balanced role rendering');
