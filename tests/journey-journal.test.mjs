import assert from 'node:assert/strict';
import {starterState,STAGES,applyCommand} from '../src/client/game/progression.js';
import {journeySummary,journalChapters,equipmentUpgrade,journeyActionLabel} from '../src/client/game/journey-journal.js';
import {journeyObjective,journeyTarget} from '../src/client/game/journey.js';
const state=starterState(),before=JSON.stringify(state);
assert.equal(journeySummary(null),null);assert.deepEqual(journalChapters(null),[]);
const summary=journeySummary(state);
assert.equal(summary.contract.reward,'일반 검 + 150 G');assert.equal(summary.contract.current,0);
assert.ok(summary.levelHint.includes('8마리'));assert.equal(summary.goal.action,'mentor');
assert.equal(journeySummary(state,'invalid').area,'village');
for(const area of Object.keys(STAGES))for(const kills of [0,1,19,20,21,199]){
 const s=starterState();s.kills[area]=kills;const result=journeySummary(s,area);
 assert.equal(result.contract.current,kills%20);assert.equal(result.contract.remaining,20-kills%20);
 assert.equal(result.contract.completed,Math.floor(kills/20));assert.ok(result.level.ratio>=0&&result.level.ratio<=1);
}
assert.deepEqual(journalChapters(state).map(c=>c.unlocked),[true,false,false,false]);
const unlocked=starterState();unlocked.traits.events.village.boss=true;unlocked.traits.events.quarry.boss=true;
assert.deepEqual(journalChapters(unlocked).map(c=>c.unlocked),[true,true,true,false]);
assert.ok(journeySummary(unlocked).skillHint.startsWith('모험 레벨 5'),'skill hint follows adventure level rather than weapon grade');
assert.equal(JSON.stringify(state),before,'reading the journal never changes rewards or progression');
assert.equal(equipmentUpgrade(state,{kind:'sword',tier:1}).title,'고급 검 획득');
for(const item of [{kind:'sword',tier:0},{kind:'bow',tier:4},{kind:'gold',amount:20},{kind:'sword',tier:5},{kind:'sword',tier:NaN}])assert.equal(equipmentUpgrade(state,item),null);
// Displayed contract reward is exactly the real transaction reward, not a cosmetic promise.
let working=starterState();for(let n=0;n<20;n++)working=applyCommand(working,{type:'loot',receipt:'journal-'+n,kind:'snail',area:'village',x:0,y:0,gold:0,items:[]},{now:100}).state;
assert.ok(working.pending.some(i=>i.kind==='sword'&&i.tier===0));assert.equal(working.pending.filter(i=>i.kind==='gold').reduce((n,i)=>n+i.amount,0),150);
const event=starterState();event.kills.village=20;event.traits.quests['village:hunt20']='claimed';event.traits.allocated.attack=1;event.traits.quests['village:boss-first']='active';
assert.equal(journeyObjective(event,'village').action,'event');
assert.equal(journeyActionLabel(journeyObjective(event,'village')),'도전 장소로 안내');
assert.equal(journeyTarget(journeyObjective(event,'village'),{}, {maxX:5000,groundY:800,spawn:{x:1600}},event,{x:1600,y:800}).label,'마을 안내 NPC');
event.traits.events.village.boss=true;assert.notEqual(journeyObjective(event,'village').action,'event');
console.log('PASS journal rewards match actual payouts, progression boundaries, class-specific skill hints, safe reading, upgrades and active boss guidance');
