import assert from 'node:assert/strict';
import { JOBS, abilityDefinition, abilityStats } from '../src/client/game/jobs.js';
import { buildStrikePlan, createSkillAttacks, isProjectileAbility } from '../src/client/game/attack-patterns.js';
import { createJobProjectiles, projectileCollision } from '../src/client/game/combat.js';
import { cleanGameEvent, stampGameEvent } from '../src/client/backend/common.js';
const attack=(job,skill=0,dir='right')=>({...abilityStats(job,skill),user_id:'caster',seq:100+skill,x:0,y:100,dir});
const mobs=[{id:'front',x:150,y:100,hp:100,s:'move'},{id:'back',x:-100,y:100,hp:100,s:'move'},{id:'far',x:450,y:100,hp:100,s:'move'}];
for(const job of JOBS) {
  assert.equal(new Set([0,1,2,3].map(slot=>abilityDefinition(job.id,slot).pattern)).size,4);
  for(let slot=0;slot<4;slot++) {
    const a=attack(job.id,slot),plan=buildStrikePlan(a,mobs),def=abilityDefinition(job.id,slot);
    assert.equal(isProjectileAbility(job.id,slot),!!def.speed);
    if(def.speed){assert.equal(plan.length,0);continue;}
    assert.ok(plan.length);
    for(const e of plan){assert.ok(e.box.x1<e.box.x2);assert.ok(e.box.y1<e.box.y2);assert.ok(e.delay>=0);assert.ok(e.damage.hits>=1);}
    const host=createSkillAttacks(),replica=createSkillAttacks();let hits=0;
    host.add(a,0,true,mobs);host.add(a,0,true,mobs);replica.add(a,0,false,mobs);
    assert.equal(host.count,1);
    for(let t=0;t<2000;t+=10){host.update(t,()=>hits++);replica.update(t,()=>assert.fail('replicas must not damage'));}
    assert.equal(hits,plan.length); assert.equal(host.count,0);
    host.add(a,3000,true,mobs);host.clear();host.update(9000,()=>assert.fail('cleared attacks must not hit'));
  }
}
// Claws materialize on selected enemies rather than traveling through intervening space.
const claws=buildStrikePlan(attack('mage',1),mobs);
assert.equal(claws.length,2);assert.ok(claws.every(e=>e.targetId==='front'&&e.x===150));
// Beam is a long, directional, repeated hitbox; whirlwind also hits behind the caster.
const beam=buildStrikePlan(attack('mage',2),mobs);assert.equal(beam.length,2);assert.equal(beam[0].box.x2,560);assert.equal(beam[0].box.x1,0);
const left=buildStrikePlan(attack('mage',2,'left'),mobs);assert.equal(left[0].box.x1,-560);assert.equal(left[0].box.x2,0);
const spin=buildStrikePlan(attack('warrior',3),mobs);assert.ok(spin[0].box.x1< -100&&spin[0].box.x2>150);
const rain=buildStrikePlan(attack('archer',3),mobs);assert.equal(new Set(rain.map(e=>e.x)).size,6);assert.ok(rain.every((e,i)=>!i||e.delay>rain[i-1].delay));
const storm=buildStrikePlan(attack('mage',3),mobs);assert.equal(storm.length,4);assert.equal(storm[0].x,150);assert.ok(storm[0].box.y1< -100);
// Fan arrows follow three actual trajectories; clones launch nine stars from three origins.
const fan=createJobProjectiles();fan.add(attack('archer',1),0);fan.update(.1,100,undefined,()=>null);
assert.equal(new Set(fan.snapshot().shots.map(p=>p.y)).size,3);
const clones=createJobProjectiles();clones.add(attack('thief',3),0);const cloneShots=clones.snapshot().shots;
assert.equal(cloneShots.length,9);assert.equal(new Set(cloneShots.map(p=>p.y)).size,3);assert.ok(Math.max(...cloneShots.map(p=>p.at))>400);
// Broad-phase overlap alone must not hit the empty corner of a diagonal sweep.
const p={x:0,y:0,nextX:100,nextY:100,dir:1,radius:2};
const box={x1:-2,x2:102,y1:-2,y2:102};
const target={id:'corner',hp:100,s:'move',x:80,y:20};
assert.equal(projectileCollision(p,box,[target],m=>({x1:m.x-5,x2:m.x+5,y1:m.y-5,y2:m.y+5})),null);
// Confirmed bursts carry skill identity even if acknowledgement precedes the attack.
const wire=cleanGameEvent('impact',stampGameEvent('impact',{id:'caster:102:0',x:50,y:60,job:'archer',skill:2},'host'));
assert.equal(wire.skill,2);assert.equal(cleanGameEvent('impact',{...wire,skill:99}),null);
const early=createJobProjectiles();early.impact(wire.id,wire.x,wire.y,0,wire.job,wire.skill);early.add(attack('archer',2),10);assert.equal(early.count,0);assert.equal(early.snapshot().bursts[0].skill,2);
console.log('PASS 16 distinct patterns: timed host-only damage, target claws, piercing beam, radial strikes, rain/storm lanes, fan trajectories, clone origins, exact swept collision, cancellation and impact identity');
