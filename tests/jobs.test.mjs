import assert from 'node:assert/strict';
import { JOBS, normalizeJob, acceptJobAttack } from '../src/client/game/jobs.js';
import { attackStats, clampAttack } from '../src/client/game/buffs.js';
import { createJobProjectiles } from '../src/client/game/combat.js';
import { cleanGameEvent } from '../src/client/backend/common.js';
assert.equal(JOBS.length, 4);
assert.equal(normalizeJob('bogus'), 'warrior');
for (const j of JOBS) {
  const a = attackStats({}, j.id);
  assert.equal(a.job, j.id); assert.equal(a.w, j.range); assert.equal(a.hits, j.hits);
  const full = attackStats({range:100,multi:100,power:100,element:100,speed:100},j.id);
  assert.ok(full.cooldown >= .1 && full.dmax <= 170 && full.hits <= 12 && full.w <= 840);
  assert.deepEqual(clampAttack(full), {w:full.w,hits:full.hits,dmin:full.dmin,dmax:full.dmax,el:full.el,job:j.id,cooldown:full.cooldown});
}
const pl = {x:0,y:100};
const a = {seq:1,x:0,y:100,job:'archer',cooldown:.6};
assert.equal(acceptJobAttack(pl,a,1000),true);
assert.equal(acceptJobAttack(pl,a,2000),false);
assert.equal(acceptJobAttack(pl,{...a,seq:2},1100),false);
assert.equal(acceptJobAttack(pl,{...a,seq:2,x:10000},2000),false);
assert.equal(acceptJobAttack(pl,{...a,seq:2},1600),true);
for (const job of ['archer','mage','thief']) {
  const shots = createJobProjectiles(); let collisions=0;
  shots.add({...attackStats({},job),x:0,y:100,dir:'right'},0,true);
  assert.ok(shots.count > 0);
  shots.update(.1,100,(p,box)=> { assert.ok(box.x2 > box.x1); assert.ok(box.x2 < p.a.w); collisions++; return {mob:{x:50}}; });
  assert.ok(collisions > 0); assert.equal(shots.count,0);
}
const evt=cleanGameEvent('atk',{user_id:'a',x:1,y:2,job:'mage',cooldown:.72,seq:1});
assert.equal(evt.job,'mage'); assert.equal(evt.cooldown,.72);
console.log('Jobs: stats, caps, replay/cadence/origin validation, projectile collision, broadcast pass');
const { createMobSim } = await import('../src/client/game/mobs.js');
const kinds = new Map([['dummy',{hp:100,speed:0,behavior:'walk',size:{w:30,h:40},buffDrop:0}]]);
const sim=createMobSim({kinds,zones:[{i:0,x1:0,x2:100,y:100,max:3,mobs:['dummy']}],rnd:()=>.5});
sim.fill(0); const excluded = new Set();
for(let i=0;i<3;i++) { const r=sim.hit({x1:0,x2:100,y1:40,y2:110},0,1,[10],excluded); assert.ok(r); assert.equal(excluded.has(r.mob.id),false); excluded.add(r.mob.id); }
assert.equal(sim.hit({x1:0,x2:100,y1:40,y2:110},0,1,[10],excluded),null);
assert.equal(sim.snapshot().filter(m=>m.hp===90).length,3);
console.log('Cleave/splash excluded-target collision passes');

assert.equal(acceptJobAttack({x:0,y:100},{...a,cooldown:.123},1000),false);
assert.equal(acceptJobAttack({x:0,y:100},{...a,cooldown:.01},1000),false);
const rapid={x:0,y:100};
assert.equal(acceptJobAttack(rapid,{...a,cooldown:.1},1000),true);
assert.equal(acceptJobAttack(rapid,{...a,seq:2,cooldown:.1},1099),false);
assert.equal(acceptJobAttack(rapid,{...a,seq:2,cooldown:.1},1100),true);
const reload={x:0,y:100}; const seed=Date.now()*1000;
assert.equal(acceptJobAttack(reload,{...a,seq:seed},1000),true);
assert.equal(acceptJobAttack(reload,{...a,seq:seed+1000},2000),true);
console.log('Discrete speed tiers, strict maximum rate and reload sequence pass');
