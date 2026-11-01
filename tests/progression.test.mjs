import assert from 'node:assert/strict';
import {starterState,applyCommand,cleanState,STAGES,GRADES,ATTACK,DEFENSE,SELL,WEAPONS,loadout,combatStats,skillUnlocked,stageUnlocked,rollEquipment,weighted,PET_RATES,PET_PRICES,petSpec,stageKinds} from '../src/client/game/progression.js';
import {createProgressionStore} from '../src/client/progression-store.js';
import {cleanGameEvent} from '../src/client/backend/common.js';
import {abilityStats,acceptJobAttack} from '../src/client/game/jobs.js';
import {normalizeMobManifest,normalizeZones,createMobSim,createMobView} from '../src/client/game/mobs.js';
import {areaMap,areaPortals,AREA_IDS} from '../src/client/game/areas.js';
import {readFile} from 'node:fs/promises';
let serial=0;const opts={id:()=>`item-${++serial}`,rnd:()=>0,job:'warrior'};
const doCmd=(s,c,o={})=>applyCommand(s,c,{...opts,...o});
let s=starterState();assert.equal(skillUnlocked(loadout(s,'warrior'),1),true);assert.equal(skillUnlocked(loadout(s,'warrior'),2),false);assert.equal(stageUnlocked(s,'warrior','quarry'),false);
const receipt={type:'loot',receipt:'kill',area:'village',x:900,y:800,items:[{kind:'sword',tier:0},{kind:'bow',tier:2}]};
s=doCmd(s,receipt).state;assert.equal(s.pending.length,2);assert.equal(s.kills.village,1);s=doCmd(s,receipt).state;assert.equal(s.pending.length,2);assert.equal(s.kills.village,1);
s=doCmd(s,{type:'collect',id:'kill:0'}).state;s=doCmd(s,{type:'collect',id:'kill:1'}).state;
const swapped=doCmd(s,{type:'equip',id:'kill:1'}).state;assert.equal(loadout(swapped).job,'archer');assert.equal(loadout(swapped).weapon,'bow');assert.throws(()=>doCmd(s,{type:'sell',id:'starter-warrior'}),/착용/);
const original=structuredClone(s);assert.throws(()=>doCmd(s,{type:'fuse',a:'kill:0',b:'kill:0'}));assert.deepEqual(s,original);
let fused=doCmd(s,{type:'fuse',a:'starter-warrior',b:'kill:0'});s=fused.state;assert.equal(s.items.length,2);assert.equal(s.equipped.warrior,fused.result.id);assert.equal(combatStats(loadout(s,'warrior')).attack,32);assert.equal(skillUnlocked(loadout(s,'warrior'),2),true);assert.equal(stageUnlocked(s,'warrior','quarry'),true);
s=doCmd(s,{type:'sell',id:'kill:1'}).state;assert.equal(s.gold,SELL[2]);assert.throws(()=>doCmd(s,{type:'sell',id:'kill:1'}));
s.items.push({id:'rare',kind:'sword',tier:2});s=cleanState(s);assert.equal(skillUnlocked(loadout(s,'warrior'),3),true);s=doCmd(s,{type:'sell',id:'rare'}).state;assert.equal(skillUnlocked(loadout(s,'warrior'),3),true);
for(const [area,st]of Object.entries(STAGES)){assert.ok(Math.abs(st.drop.reduce((a,b)=>a+b,0)-1)<1e-10);assert.equal(st.drop.length,GRADES.length);}
assert.ok(Math.abs(PET_RATES.reduce((a,b)=>a+b,0)-1)<1e-10);assert.equal(PET_PRICES[10],1800);
for(const area of Object.keys(STAGES)) {
 let p=starterState();p.gold=100000;p.highest.warrior=4;p.pity[area]=[19,79,199];
 p=doCmd(p,{type:'draw',area,count:1}).state;assert.ok(p.pets[area+':4']);assert.deepEqual(p.pity[area],[0,0,0]);
 p.pity[area]=[0,79,0];const epic=doCmd(p,{type:'draw',area,count:1});assert.ok(epic.state.pets[area+':3']);assert.equal(epic.result[0].id,area+':3');
 p.pity[area]=[19,0,0];const rare=doCmd(p,{type:'draw',area,count:1});assert.equal(rare.result[0].id,area+':2');
 p.pity[area]=[0,0,0];p=doCmd(p,{type:'draw',area,count:10}).state;assert.equal(p.pets[area+':0'].level,0);assert.equal(p.essence,9);assert.equal(p.gold,98000);
 p.pet=area+':4';const stats=combatStats(loadout(p,'warrior'));assert.equal(stats.attack,23);assert.equal(stats.maxHp,160);assert.equal(stats.pickup,240);
 p.essence=100;p=doCmd(p,{type:'pet-upgrade',id:area+':4'}).state;assert.equal(p.essence,95);assert.equal(p.pets[area+':4'].level,1);
}
let batch=starterState();batch.gold=5000;batch.pity.village=[15,0,0];const batched=doCmd(batch,{type:'draw',area:'village',count:10});let singles=structuredClone(batch);for(let n=0;n<10;n++)singles=doCmd(singles,{type:'draw',area:'village',count:1}).state;assert.deepEqual(batched.state.pity,singles.pity);assert.deepEqual(batched.state.pets,singles.pets);assert.equal(batched.state.gold-singles.gold,200);
assert.throws(()=>doCmd(starterState(),{type:'draw',area:'village',count:1}),/골드/);assert.throws(()=>doCmd(starterState(),{type:'draw',area:'quarry',count:1}),/해금/);
assert.equal(petSpec('__proto__:0'),null);assert.equal(petSpec('village:0:extra'),null);assert.equal(cleanGameEvent('loot',{host:'h',owner:'o',receipt:'r',area:'__proto__',x:1,y:2,items:[]}),null);
assert.equal(cleanGameEvent('loot',{host:'h',owner:'o',receipt:'r',area:'forest',x:1,y:2,items:[{kind:'sword',tier:99}]}),null);
for(const j of Object.keys(WEAPONS))for(let tier=0;tier<5;tier++)for(let slot=0;slot<4;slot++){
 const a=abilityStats(j,slot,{tier,highest:tier,pet:null});assert.ok(a.dmin>=1&&a.dmax<=1000);assert.equal(a.hits,abilityStats(j,slot).hits);if(tier)assert.ok(a.dmin>abilityStats(j,slot).dmin);
}
assert.equal(acceptJobAttack({x:0,y:0},{...abilityStats('mage',3),loadout:{tier:0,highest:0},seq:1,x:0,y:0},0),false);
// Actual stages feed simulation, contact damage and HP rendering with the same specs.
const defs=normalizeMobManifest(JSON.parse(await readFile(new URL('../assets/mob/manifest.json',import.meta.url))));
const base=stageKinds(stageKinds(defs.kinds,'forest'),'quarry');
for(const area of AREA_IDS){const map=areaMap(area,{width:3500,height:900,groundY:800,spawn:{x:250,y:800},platforms:[],spawns:[{id:'test',mobs:['golem'],max:2,x1:500,x2:1000}]});
 const kinds=stageKinds(base,area),world={groundY:800,minX:20,maxX:3480};const zones=normalizeZones(map.spawns,map.platforms||[],world,kinds);const sim=createMobSim({kinds,zones,rnd:()=>.5});sim.fill(0);assert.ok(sim.snapshot().length>0);
 const view=createMobView({kinds});view.apply(sim.snapshot(),0,true);for(const v of view.list){assert.equal(v.hp,STAGES[area].mobs[v.kind][0]);assert.equal(v.spec.touchDamage,STAGES[area].mobs[v.kind][1]);}
 const portals=areaPortals(map);assert.equal(portals.length,area==='quarry'?2:1);assert.ok(portals.every(p=>Math.abs(AREA_IDS.indexOf(p.to)-AREA_IDS.indexOf(area))===1));
}
// Lock serialization: two tabs cannot spend the same gold or sell/fuse the same items.
const data=new Map(),storage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};let queue=Promise.resolve();const locks={request:(key,fn)=>{const p=queue.then(fn);queue=p.catch(()=>{});return p;}};
const funded=starterState();funded.gold=200;data.set('test:equipment-v1',JSON.stringify(funded));
const a=createProgressionStore('test',{storage,locks}),b=createProgressionStore('test',{storage,locks});const draws=await Promise.allSettled([a.run({type:'draw',area:'village',count:1}),b.run({type:'draw',area:'village',count:1})]);assert.equal(draws.filter(r=>r.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).gold,0);
const saleState=starterState();saleState.items.push({id:'sale-once',kind:'bow',tier:1});data.set(a.key,JSON.stringify(saleState));
const sales=await Promise.allSettled([a.run({type:'sell',id:'sale-once'}),b.run({type:'sell',id:'sale-once'})]);assert.equal(sales.filter(r=>r.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).gold,40);
const fusionState=starterState();fusionState.items.push({id:'fuse-once',kind:'sword',tier:0});data.set(a.key,JSON.stringify(fusionState));
const fusions=await Promise.allSettled([a.run({type:'fuse',a:'starter-warrior',b:'fuse-once'}),b.run({type:'fuse',a:'starter-warrior',b:'fuse-once'})]);assert.equal(fusions.filter(r=>r.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).items.length,1);
const failStore=createProgressionStore('test',{storage:{getItem:k=>data.get(k),setItem:()=>{throw Error('quota');}},locks});const before=structuredClone(failStore.state);await assert.rejects(()=>failStore.run({type:'ensure'}),/저장/);assert.deepEqual(failStore.state,before);
await assert.rejects(()=>createProgressionStore('test',{storage,locks:null}).run({type:'ensure'}),/저장소/);
console.log('PASS progression: stages/simulation, weapon-driven equipment, fusion/equip preservation, sales, permanent skill milestones, per-biome gacha pity/batches, pet stats, protocol rejection, concurrent spend and storage rollback');
