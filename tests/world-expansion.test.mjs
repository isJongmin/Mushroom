import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {areaMap,AREA_IDS,drawBiomeMap} from '../src/client/game/areas.js';
import {STAGES,petPrice,petBonuses,petSpec,cleanState,starterState,stageKinds} from '../src/client/game/progression.js';
import {rollMonsterLoot} from '../src/client/game/monster-rewards.js';
import {createBody,stepBody,normalizePlatforms,normalizeRopes,PHYS,surfaceBelow} from '../src/client/game/physics.js';
import {camYTarget} from '../src/client/game/world.js';
import {gardenZones,createGarden} from '../src/client/game/garden.js';
import {normalizeMobManifest,normalizeZones,createMobSim} from '../src/client/game/mobs.js';
import {installBoss} from '../src/client/game/garden-boss.js';
import {regionOf} from '../src/client/game/regions.js';
const base=normalizeMobManifest(JSON.parse(readFileSync(new URL('../assets/mob/manifest.json',import.meta.url)))).kinds;installBoss(base);
let hp=0,power=0,price=0;
for(const area of AREA_IDS){
 const st=STAGES[area];assert.ok(Object.values(st.mobs)[0][0]>hp);hp=Object.values(st.mobs)[0][0];assert.ok(petBonuses(area+':2').attack>power);power=petBonuses(area+':2').attack;assert.ok(petPrice(area,1)>price);price=petPrice(area,1);
 assert.ok(petSpec(area+':4'));const old=starterState();old.pets['village:3']={level:2};old.pet='village:3';assert.equal(cleanState(old).pet,'village:3');
 const kinds=stageKinds(base,area),map=areaMap(area,{width:3840,groundY:800,platforms:[],ropes:[],spawns:[]}),platforms=normalizePlatforms(map.platforms,{width:map.width,groundY:800}),ropes=normalizeRopes(map.ropes,{width:map.width,groundY:800});
 const zones=gardenZones(normalizeZones(map.spawns,platforms,{width:map.width,groundY:800},kinds),{...map,minX:20,maxX:map.width-20},area);
 assert.ok(zones.some(z=>z.boss));assert.ok(zones.filter(z=>z.event).length===2);
 const sim=createMobSim({kinds,zones,rnd:()=>.5,players:()=>[]});const event=createGarden();event.start('test-'+area,0,['player'],'boss');event.tick(5000,{players:1,difficulty:regionOf(area).scale,spawnBoss:max=>sim.spawnBoss(max,5000),bossX:map.spawn?.x??0});assert.equal(event.snapshot().boss.max,Math.min(50000,1400*regionOf(area).scale));assert.equal(sim.bossMob().hp,event.snapshot().boss.max);
 const elite=Object.keys(st.mobs).at(-1);for(const n of [0,.2,.5,.999]){const loot=rollMonsterLoot(area,elite,()=>n);assert.equal(loot.items.length,1);assert.ok(loot.items[0].tier>=Math.min(4,st.order));}
 const boss=rollMonsterLoot(area,'garden-king',()=>.9);assert.equal(boss.items.length,5);assert.ok(boss.gold<=20000);assert.ok(boss.items.slice(0,2).every(i=>i.tier>=Math.max(2,st.order)));
 if(area!=='village')for(const p of platforms.filter(p=>!p.id.includes('-step-'))){const body=createBody(p.x1+20,800,800);const opt={speed:240,minX:0,maxX:map.width,groundY:800,platforms,ropes:[]};for(let frame=0;frame<600&&(!body.grounded||body.y!==p.y);frame++){const jump=frame%65===0;stepBody(body,{dir:0,jump:false,superKind:jump?'up':null},1/60,opt);}assert.equal(body.y,p.y,'stepping ledges reach '+p.id);}
}
// Large frames and exact landing boundaries cannot tunnel through a platform.
for(const dt of [1/120,1/30,.1]){const p={id:'upper',x1:20,x2:300,y:530},b=createBody(100,800,800);const opt={speed:240,minX:0,maxX:1000,groundY:800,platforms:[p]};stepBody(b,{dir:0,superKind:'up'},dt,opt);for(let t=0;t<2;t+=dt)stepBody(b,{dir:0},dt,opt);assert.equal(b.y,530);assert.equal(b.on.id,'upper');}
assert.ok(PHYS.superUpV**2/(2*PHYS.gravity)>270);
assert.equal(surfaceBelow([{x1:0,x2:100,y:500}],150,499,800),800,'spilled loot falls to ground outside ledge');
const oldFoot=800-camYTarget(800,500,0,1000),newFoot=800-camYTarget(800,500,0,836,.88);assert.ok(newFoot>oldFoot+60);
// Model the prior frame's DPR transform; biome rendering must leave identity for drops/portals.
let transform=3,stack=[];const ctx=new Proxy({canvas:{width:390,height:820},setTransform(a){transform=a},save(){stack.push(transform)},restore(){transform=stack.pop()},createLinearGradient(){return {addColorStop(){}}}}, {get(o,k){return k in o?o[k]:()=>{};},set(o,k,v){o[k]=v;return true;}});
drawBiomeMap(ctx,areaMap('quarry',{}),0,250,3,1170,2460);assert.equal(transform,1);
console.log('PASS four-region progression, pets/prices, elite guarantees, regional boss spawn/HP, stepping/super jumps and high-DPR drop transform');
