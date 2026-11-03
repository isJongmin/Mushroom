import assert from 'node:assert/strict';
import {adventureProgress,levelCost,adventureBonuses,cleanAdventureLevel} from '../src/client/game/adventure-level.js';
import {adventureGoal,cooperativeRoster} from '../src/client/game/adventure-goals.js';
import {starterState,cleanState,applyCommand,loadout,cleanLoadout,combatStats} from '../src/client/game/progression.js';
import {cleanGameEvent} from '../src/client/backend/common.js';

let state=starterState();
assert.equal(adventureProgress(state).level,1);
assert.equal(adventureProgress({...state,kills:{village:7}}).current,70);
assert.equal(adventureProgress({...state,kills:{village:8}}).level,2);
assert.equal(adventureProgress({...state,kills:{village:8}}).current,0);
let total=0;
for(let level=1;level<30;level++){
 total+=levelCost(level);
 const p=adventureProgress({kills:{village:Math.ceil(total/10)}});
 assert.equal(p.level,level+1);assert.ok(p.ratio>=0&&p.ratio<=1);
}
assert.equal(adventureProgress({kills:{frost:1e9}}).level,30);
assert.equal(adventureProgress({kills:{village:NaN,quarry:-1,forest:1.5,frost:Infinity}}).total,0);
for(const n of [NaN,Infinity,'30',undefined,1.5])assert.equal(cleanAdventureLevel(n),1);
assert.equal(cleanAdventureLevel(999),30);
assert.equal(adventureBonuses(30).hp,87);
assert.ok(Math.abs(adventureBonuses(30).attack-1.29)<1e-9);
const veteran=starterState();veteran.kills={village:120,quarry:30,forest:5,frost:1};
veteran.gold=1234;veteran.pets={'village:0':{level:3}};
assert.equal(adventureProgress(cleanState(veteran)).total,2600,'existing kills migrate without resetting assets');
assert.equal(cleanState(veteran).gold,1234);assert.equal(cleanState(veteran).pets['village:0'].level,3);
for(let n=0;n<8;n++)state=applyCommand(state,{type:'loot',receipt:'growth-'+n,kind:'snail',area:'village',x:0,y:0,gold:0,items:[]}).state;
assert.equal(adventureProgress(state).level,2);
const duplicate=applyCommand(state,{type:'loot',receipt:'growth-7',kind:'snail',area:'village',x:0,y:0,gold:0,items:[]});
assert.equal(duplicate.result.duplicate,true);assert.equal(adventureProgress(duplicate.state).total,80);
const event=applyCommand(state,{type:'loot',receipt:'event-defense',area:'village',x:0,y:0,gold:0,items:[]}).state;
assert.equal(adventureProgress(event).total,80,'event payout cannot double-count hunting XP');
const base=combatStats(loadout(starterState())),grown=combatStats(loadout(state));
assert.equal(grown.maxHp,base.maxHp+3);assert.ok(grown.multiplier>base.multiplier);
assert.equal(cleanLoadout({adventureLevel:999}).adventureLevel,30);
assert.equal(cleanLoadout({level:5}).adventureLevel,1,'pet level and player level remain separate');
assert.equal(cleanGameEvent('hp',{user_id:'qa',hp:103,max:103,loadout:loadout(state)}).loadout.adventureLevel,2);
assert.equal(cleanLoadout(loadout(state)).adventureLevel,2);
const goal=adventureGoal(state,'village');assert.equal(goal.action,'hunt');assert.ok(goal.title.includes('12'));
const next=starterState();next.highest.warrior=1;assert.equal(adventureGoal(next,'village').action,'taxi');
next.items=Array.from({length:190},(_,n)=>({id:'gear'+n,kind:'sword',tier:0}));assert.equal(adventureGoal(next,'village').action,'bag');
const training=starterState();training.kills.village=20;training.traits.quests['village:hunt20']='active';
assert.equal(adventureGoal(training,'village').action,'mentor');
training.traits.quests['village:hunt20']='claimed';assert.equal(adventureGoal(training,'village').action,'traits');
assert.equal(adventureGoal(null,'village'),null);
const self={user_id:'self',mapId:'village'};
const roster=cooperativeRoster([self,{user_id:'remote',mapId:'frost',nickname:'Other'},
 {user_id:'friend',mapId:'village',nickname:'Friend',hp:200,max:100},
 {user_id:'fallen',mapId:'village',nickname:'Fallen',hp:0,max:100,dead:true}],self);
assert.deepEqual(roster.map(p=>p.id),['fallen','friend']);assert.equal(roster[1].hp,100);
assert.deepEqual(cooperativeRoster([],null),[]);
console.log('PASS level thresholds/cap, legacy evidence, duplicate XP, balanced stats, protocol and actionable goals/co-op roster');
