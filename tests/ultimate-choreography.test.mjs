import assert from 'node:assert/strict';
import { JOBS, abilityDefinition, abilityStats } from '../src/client/game/jobs.js';
import { buildStrikePlan, createSkillAttacks } from '../src/client/game/attack-patterns.js';
import { ultimatePresentation } from '../src/client/game/ultimate-visuals.js';
for(const j of JOBS){
  const def=abilityDefinition(j.id,3),a={...abilityStats(j.id,3),x:0,y:200,dir:'right',user_id:'caster',seq:1};
  const events=buildStrikePlan(a,[]),final=events.find(e=>e.phase==='final');
  assert.ok(def.duration>=2700&&def.duration<=3000);
  assert.equal(def.cooldown,15);
  assert.ok(final&&final.delay===def.impactAt&&final.damage.hits>=3);
  assert.ok(final.box.x2-final.box.x1>=600);
  assert.ok(events.every(e=>e.delay>=450));
  assert.equal(events.reduce((s,e)=>s+e.damage.hits,0)+(def.projectileHits||0),a.hits);
  const fx=createSkillAttacks();fx.add(a,0,true);let hits=0;
  fx.update(449,()=>hits++);assert.equal(hits,0);
  fx.update(def.impactAt,(e)=>{if(e.phase==='final')assert.ok(e.damage.hits>=3);hits++;});assert.ok(hits>0);
  assert.deepEqual(fx.presentation(def.impactAt+60,'other'),{x:0,y:0});
  assert.deepEqual(fx.presentation(def.impactAt+60,'caster',true),{x:0,y:0});
  fx.clear();assert.deepEqual(fx.presentation(def.impactAt+60,'caster'),{x:0,y:0});
  assert.deepEqual(ultimatePresentation(0,def.impactAt),{x:0,y:0});
  for(let t=0;t<4000;t+=10){const p=ultimatePresentation(t,def.impactAt);assert.ok(Math.abs(p.x)<=6&&Math.abs(p.y)<=3.5);assert.deepEqual(ultimatePresentation(t,def.impactAt,true),{x:0,y:0});}
}
console.log('PASS ultimate anticipation, decisive multi-hit finishers, damage totals, bounded camera impulse, reduced motion and teardown');
const busy=createSkillAttacks();
busy.add({...abilityStats('mage',3),user_id:'caster',seq:1,x:0,y:200,dir:'right'},0,false);
for(let seq=2;seq<160;seq++)busy.add({...abilityStats('warrior',0),user_id:'other',seq,x:0,y:200,dir:'right'},1,false);
assert.equal(busy.count,100);assert.ok(busy.snapshot().some(c=>c.id==='caster:1'));
console.log('PASS ordinary attack traffic cannot evict a playing ultimate; cast memory remains bounded');
