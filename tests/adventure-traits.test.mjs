import assert from 'node:assert/strict';
import {starterState,cleanState,applyCommand,STAGES,loadout,combatStats,cleanLoadout} from '../src/client/game/progression.js';
import {earnedPoints,traitGoals,allocationOK,explorationPoints,traitEditReason} from '../src/client/game/adventure-traits.js';
import {abilityStats,acceptJobAttack,BASIC_INTERVAL_MS} from '../src/client/game/jobs.js';
import {cleanGameEvent} from '../src/client/backend/common.js';
import {createProgressionStore} from '../src/client/progression-store.js';
import {areaMap} from '../src/client/game/areas.js';
const run=(s,c)=>applyCommand(s,c,{id:()=>crypto.randomUUID()}).state;
const allocate=(s,a)=>run(s,{type:'traits-allocate',expectedRevision:s.revision,allocated:a});
const zero={attack:0,health:0,technique:0};
let s=starterState();delete s.traits;s.gold=12345;s.highest.warrior=4;s.pets={'frost:4':{level:5}};s.pet='frost:4';s.kills.village=20;
const old=structuredClone(s);s=cleanState(s);assert.equal(earnedPoints(s,STAGES),1);assert.deepEqual(s.pets,old.pets);assert.equal(s.gold,12345);assert.equal(s.highest.warrior,4);assert.ok(Object.values(s.traits.species).every(a=>Object.values(a).every(r=>r.length===0)));
s=run(s,{type:'ensure',legacyVillageBoss:true});assert.equal(earnedPoints(s,STAGES),2);s=run(s,{type:'ensure',legacyVillageBoss:true});assert.equal(earnedPoints(s,STAGES),2);
for(const goal of traitGoals(s,STAGES))s=run(s,{type:'trait-quest-accept',key:goal.key});
let serial=0;
for(const [area,st]of Object.entries(STAGES)){
 const threshold=area==='village'?10:20;
 for(const kind of Object.keys(st.mobs))for(let n=0;n<threshold;n++){
  const packet={type:'loot',receipt:`kill-${++serial}`,area,kind,x:100,y:800,items:[],gold:0};
  s=run(s,packet);const once=structuredClone(s);s=run(s,packet);assert.deepEqual(s.traits,once.traits);assert.equal(s.kills[area],once.kills[area]);s.pending=[];
 }
 if(area!=='village'){
  const map=areaMap(area,{}),points=explorationPoints(map);assert.deepEqual(points.map(p=>p.id),['entry','upper','depth']);
  assert.ok(points.every(p=>p.x>0&&p.x<map.width));const upper=points[1];assert.ok(map.platforms.some(p=>upper.x>=p.x1&&upper.x<=p.x2&&upper.y===p.y));
  for(const point of points){s=run(s,{type:'trait-explore',area,point:point.id});s=run(s,{type:'trait-explore',area,point:point.id});}assert.equal(s.traits.explored[area].length,3);
  s=run(s,{type:'trait-event',area,mode:'defense'});s=run(s,{type:'trait-event',area,mode:'defense'});
 }
 s=run(s,{type:'trait-event',area,mode:'boss'});s=run(s,{type:'trait-event',area,mode:'boss'});
}
for(const goal of traitGoals(s,STAGES).filter(g=>g.ready))s=run(s,{type:'trait-quest-claim',key:goal.key});
assert.equal(earnedPoints(s,STAGES),15);assert.equal(traitGoals(s,STAGES).filter(g=>g.done).length,15);assert.equal(new Set(traitGoals(s,STAGES).map(g=>g.key)).size,15);
const full=structuredClone(s);
for(const bad of [{attack:-1,health:0,technique:0},{attack:1.5,health:0,technique:0},{attack:11,health:0,technique:0},{attack:10,health:10,technique:0},{attack:NaN,health:0,technique:0},{attack:1,health:0,technique:0,other:1},null])assert.throws(()=>allocate(s,bad));
assert.equal(allocationOK({attack:10,health:5,technique:0}),true);assert.throws(()=>allocate(starterState(),{attack:1,health:0,technique:0}));assert.throws(()=>run(s,{type:'trait-explore',area:'quarry',point:'wrong'}));assert.throws(()=>run(s,{type:'trait-event',area:'__proto__',mode:'boss'}));
s.items[0].tier=4;s=allocate(s,{attack:10,health:5,technique:0});const stats=combatStats(loadout(s));assert.equal(stats.attack,594);assert.equal(stats.multiplier,131/20*3.025*1.5);assert.equal(stats.maxHp,1138);s=allocate(s,{attack:0,health:10,technique:5});assert.equal(combatStats(loadout(s)).maxHp,1365);s=allocate(s,{attack:5,health:0,technique:10});
const wire=loadout(s);assert.deepEqual(cleanLoadout(wire).traits,s.traits.allocated);assert.deepEqual(cleanLoadout({traits:{attack:10,health:10,technique:10}}).traits,zero);
for(const job of ['warrior','archer','mage','thief'])for(let slot=0;slot<4;slot++){
 const l={...wire,weapon:{warrior:'sword',archer:'bow',mage:'staff',thief:'claw'}[job]},a=abilityStats(job,slot,l),packet=cleanGameEvent('atk',{...a,user_id:'guest',loadout:l,seq:1,x:0,y:800,dir:'right',mapId:'frost'});assert.deepEqual(packet.loadout.traits,l.traits);
 assert.equal(a.cooldown,[0,2.4,5.6,12][slot]);const p={x:0,y:800};assert.ok(acceptJobAttack(p,packet,0));const interval=slot?a.cooldown*1000:BASIC_INTERVAL_MS;assert.equal(acceptJobAttack(p,{...packet,seq:2},interval-30),false);assert.ok(acceptJobAttack(p,{...packet,seq:2},interval));assert.equal(acceptJobAttack(p,{...packet,seq:3},interval*2-30),false);
 const base=abilityStats(job,slot,{...l,traits:zero});assert.equal(a.animMs,base.animMs);assert.equal(a.w,base.w);assert.equal(a.hits,base.hits);
}
assert.equal(BASIC_INTERVAL_MS,360);
const lootWire=cleanGameEvent('loot',{host:'h',owner:'guest',receipt:'sample',area:'frost',kind:'ice-golem',x:0,y:800,items:[],gold:1});assert.equal(lootWire.kind,'ice-golem');assert.equal(cleanGameEvent('loot',{...lootWire,kind:'snail'}),null);
const hpWire=cleanGameEvent('hp',{user_id:'guest',loadout:wire,hp:300,max:combatStats(wire).maxHp});assert.deepEqual(hpWire.loadout.traits,wire.traits);
// Evidence survives removal from the bounded generic loot receipt cache.
let replay=starterState();const packet={type:'loot',receipt:'ancient-receipt',area:'village',kind:'snail',x:0,y:800,items:[]};replay=run(replay,packet);replay.seen=[];replay=run(replay,packet);assert.equal(replay.traits.species.village.snail.length,1);
// Event mobs never increase species/contract progress.
let event=starterState();event=run(event,{...packet,receipt:'boss-loot',kind:'garden-king'});assert.equal(event.kills.village,0);assert.equal(earnedPoints(event,STAGES),0);
const ready={connected:true,alive:true,near:true,now:6000,lastAttack:1000,lastHit:0};assert.equal(traitEditReason(ready),'');for(const v of [{connected:false},{alive:false},{near:false},{lastAttack:1001},{lastHit:1001}])assert.notEqual(traitEditReason({...ready,...v}),'');
const data=new Map(),storage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};let queue=Promise.resolve();const locks={request:(key,fn)=>{const result=queue.then(fn);queue=result.catch(()=>{});return result;}};
data.set('traits:equipment-v1',JSON.stringify(full));const a=createProgressionStore('traits',{storage,locks}),b=createProgressionStore('traits',{storage,locks});
const commands=await Promise.allSettled([a.run({type:'traits-allocate',allocated:{attack:10,health:5,technique:0},expectedRevision:full.revision}),b.run({type:'traits-allocate',allocated:{attack:0,health:5,technique:10},expectedRevision:full.revision})]);assert.equal(commands.filter(r=>r.status==='fulfilled').length,1);assert.equal(earnedPoints(JSON.parse(data.get(a.key)),STAGES),15);
let blocked=false;const guard=createProgressionStore('traits',{storage,locks,guardCommand:c=>{if(c.type==='traits-allocate'&&blocked)throw new Error('combat');}});blocked=true;await assert.rejects(()=>guard.run({type:'traits-allocate',allocated:zero,expectedRevision:a.state.revision}),/combat/);
const fail=createProgressionStore('traits',{storage:{getItem:k=>data.get(k),setItem:()=>{throw Error('quota');}},locks});const before=structuredClone(fail.state);await assert.rejects(()=>fail.run({type:'traits-allocate',allocated:zero,expectedRevision:before.revision}),/저장/);assert.deepEqual(fail.state,before);
const refreshed=createProgressionStore('traits',{storage,locks});assert.deepEqual(refreshed.state.traits.allocated,a.state.traits.allocated);
const highDamage=abilityStats('warrior',3,{tier:4,highest:4,pet:'frost:4',level:5,traits:{attack:10,health:0,technique:5}}).dmax;assert.ok(highDamage>1000);assert.deepEqual(cleanGameEvent('mobs',{host:'h',t:0,list:[{id:'mob1',kind:'garden-king',x:0,y:800,hp:1000,dm:[highDamage]}]}).list[0].dm,[highDamage]);

// Redistribution during an existing cooldown preserves the cast-time deadline on the host.
const caster={x:0,y:800},slow={tier:4,highest:4,traits:zero},fast={...slow,traits:{attack:0,health:0,technique:10}};
assert.ok(acceptJobAttack(caster,{...abilityStats('mage',3,slow),seq:1,x:0,y:800,loadout:slow},0));
assert.equal(acceptJobAttack(caster,{...abilityStats('mage',3,fast),seq:2,x:0,y:800,loadout:fast},12000),false);
assert.ok(acceptJobAttack(caster,{...abilityStats('mage',3,fast),seq:2,x:0,y:800,loadout:fast},15000));
console.log('PASS adventure traits: 15 evidence-backed first awards, duplicate/replay protection, old save preservation, strict allocation and stale revision, 594 ATK/1365 HP, all-job cooldown/host/wire parity, fixed animations/basic speed, exploration, transaction rollback and concurrent tabs');
