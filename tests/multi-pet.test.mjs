import assert from 'node:assert/strict';
import {starterState,cleanState,applyCommand,loadout,cleanLoadout,combatStats,equippedPetIds,petBonuses,MAX_EQUIPPED_PETS} from '../src/client/game/progression.js';
import {createCompanionGroup,COMPANION_MIN_GAP} from '../src/client/game/scene-order.js';
import {cleanGameEvent} from '../src/client/backend/common.js';
import {abilityStats,acceptJobAttack} from '../src/client/game/jobs.js';
import {createProgressionStore} from '../src/client/progression-store.js';
const ids=['frost:4','frost:3','frost:2','forest:4'];
let s=starterState();s.pets=Object.fromEntries(ids.map(id=>[id,{level:5}]));s.gold=1234;s.essence=234;s.items[0].tier=4;s.highest.warrior=4;
const old=structuredClone(s);delete old.equippedPets;old.pet=ids[0];const migrated=cleanState(old);assert.deepEqual(migrated.equippedPets,[ids[0]]);assert.equal(migrated.gold,old.gold);assert.deepEqual(migrated.pets,old.pets);assert.deepEqual(loadout(migrated).companions,[{id:ids[0],level:5}]);
for(const id of ids.slice(0,3))s=applyCommand(s,{type:'pet-equip',id}).state;
assert.equal(MAX_EQUIPPED_PETS,3);assert.deepEqual(equippedPetIds(s),ids.slice(0,3));assert.deepEqual(equippedPetIds(applyCommand(s,{type:'pet-equip',id:ids[1]}).state),ids.slice(0,3));assert.throws(()=>applyCommand(s,{type:'pet-equip',id:ids[3]}),/3마리/);assert.throws(()=>applyCommand(s,{type:'pet-equip',id:'__proto__'}),/보유/);
for(const id of ids.slice(0,3))assert.throws(()=>applyCommand(s,{type:'pet-sell',id}),/동행/);
const off=applyCommand(s,{type:'pet-off',id:ids[0]}).state;assert.deepEqual(off.equippedPets,ids.slice(1,3));assert.equal(off.pet,ids[1]);const sold=applyCommand(off,{type:'pet-sell',id:ids[0]}).state;assert.equal(sold.pets[ids[0]],undefined);assert.deepEqual(sold.equippedPets,ids.slice(1,3));assert.deepEqual(applyCommand(s,{type:'pet-off'}).state.equippedPets,[]);
const l=loadout(s),bonuses=ids.slice(0,3).map(id=>petBonuses(id,5)),atk=bonuses.reduce((n,b)=>n+b.attack,0),hp=bonuses.reduce((n,b)=>n+b.hp,0);assert.equal(combatStats(l).attack,Math.round(131*(1+atk)));assert.equal(combatStats(l).maxHp,100+hp);assert.equal(combatStats({...l,traits:{attack:10,health:5,technique:0}}).attack,Math.round(131*(1+atk)*1.5));assert.equal(combatStats({...l,traits:{attack:5,health:10,technique:0}}).maxHp,Math.round((100+hp)*1.5));
assert.deepEqual(cleanLoadout(l).companions,l.companions);assert.deepEqual(cleanLoadout({pet:'frost:4',level:5}).companions,[{id:'frost:4',level:5}]);assert.deepEqual(cleanLoadout({companions:[],pet:'frost:4'}).companions,[]);
const forged=cleanLoadout({companions:[{id:ids[0],level:99},{id:ids[0],level:4},{id:'__proto__:0',level:5},...ids.slice(1).map(id=>({id,level:5}))]});assert.equal(forged.companions.length,3);assert.equal(forged.companions[0].level,5);assert.equal(new Set(forged.companions.map(p=>p.id)).size,3);
for(const job of ['warrior','archer','mage','thief'])for(let slot=0;slot<4;slot++){
 const wire=cleanGameEvent('atk',{...abilityStats(job,slot,l),user_id:'u',loadout:{...l,weapon:{warrior:'sword',archer:'bow',mage:'staff',thief:'claw'}[job]},seq:1,x:0,y:800});assert.deepEqual(wire.loadout.companions,l.companions);assert.ok(acceptJobAttack({x:0,y:800},wire,0));assert.equal(wire.dmax,abilityStats(job,slot,wire.loadout).dmax);
}
assert.deepEqual(cleanGameEvent('hp',{user_id:'u',hp:100,max:combatStats(l).maxHp,loadout:l}).loadout.companions,l.companions);
// Sample actual follower poses across turns, loot convergence, jumps, edges, and map changes.
const group=createCompanionGroup();
for(let n=0;n<800;n++){
 const dir=n%80<40?1:-1,x=n%160<80?22:5978,y=n%60<30?800:345;
 const poses=group.sample({ids:ids.slice(0,3),mapId:n<400?'village':'frost',x,y,dir,target:n%30<15?{x,y}:null,now:n*16,minX:20,maxX:5980});assert.equal(poses.length,3);
 for(const p of poses){assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y));assert.ok(p.x>=20&&p.x<=5980);}
 for(let i=0;i<poses.length;i++)for(let j=i+1;j<poses.length;j++)assert.ok(Math.hypot(poses[i].x-poses[j].x,poses[i].y-poses[j].y)>=COMPANION_MIN_GAP-1e-9);
}
assert.equal(group.sample({ids:[],x:0,y:800}).length,0);assert.equal(group.sample({ids:[ids[0],ids[0],ids[1]],x:0,y:800,now:0}).length,2);group.reset();assert.equal(group.sample({ids:[ids[0]],x:NaN,y:800}).length,0);
// Two tabs competing for the final slot cannot equip a fourth pet.
const data=new Map(),storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};let queue=Promise.resolve();const locks={request:(_,fn)=>{const r=queue.then(fn);queue=r.catch(()=>{});return r;}};const two=applyCommand(s,{type:'pet-off',id:ids[2]}).state;data.set('pets:equipment-v1',JSON.stringify(two));const a=createProgressionStore('pets',{storage,locks}),b=createProgressionStore('pets',{storage,locks});const race=await Promise.allSettled([a.run({type:'pet-equip',id:ids[2]}),b.run({type:'pet-equip',id:ids[3]})]);assert.equal(race.filter(r=>r.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).equippedPets.length,3);
const reload=createProgressionStore('pets',{storage,locks});assert.equal(reload.state.equippedPets.length,3);const before=structuredClone(reload.state);const failing=createProgressionStore('pets',{storage:{getItem:k=>data.get(k),setItem:()=>{throw Error('quota');}},locks});await assert.rejects(()=>failing.run({type:'pet-off',id:ids[0]}),/저장/);assert.deepEqual(failing.state,before);
console.log('PASS 3 pets: legacy migration, distinct-slot cap, idempotent equip, individual detach/sale protection, additive bonuses then traits, wire/host parity, 800-frame anti-stacking across turns/loot/jumps/maps/edges, concurrent final slot and rollback');
