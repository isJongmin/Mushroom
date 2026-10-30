import assert from 'node:assert/strict';
import { JOBS, normalizeJob, acceptJobAttack, abilityDefinition, abilityStats, BASIC_INTERVAL_MS } from '../src/client/game/jobs.js';
import { attackStats, clampAttack } from '../src/client/game/buffs.js';
import { createJobProjectiles } from '../src/client/game/combat.js';
import { cleanGameEvent, stampGameEvent } from '../src/client/backend/common.js';
import { createMobSim } from '../src/client/game/mobs.js';
assert.equal(normalizeJob('bogus'), 'warrior');
for (const j of JOBS) {
  assert.deepEqual(attackStats({ range:10,power:10,multi:10,speed:10 },j.id), abilityStats(j.id));
  const pl = { x:0, y:100, job:j.id };
  for(let slot=0;slot<4;slot++) {
    const a = abilityStats(j.id,slot), def = abilityDefinition(j.id,slot);
    assert.equal(a.cooldown,[0,3,7,15][slot]);
    const packet = {...a,user_id:'user',mapId:'village',seq:slot*10+1,x:0,y:100,dir:'right'};
    const wire = cleanGameEvent('atk', stampGameEvent('atk',packet,'user'));
    assert.ok(wire); assert.equal(wire.skill,slot); assert.equal(wire.cooldown,a.cooldown);
    assert.deepEqual(clampAttack({...wire,w:99999,dmax:99999}), a);
    const now=slot*20000;
    assert.equal(acceptJobAttack(pl,wire,now),true);
    assert.equal(acceptJobAttack(pl,{...wire,seq:packet.seq+1},now+100),false);
    assert.equal(acceptJobAttack(pl,{...wire,seq:packet.seq+1},now+(slot?def.cooldown*1000:BASIC_INTERVAL_MS)),true);
    assert.equal(acceptJobAttack(pl,{...wire,seq:packet.seq+2},now+100000),true);
    assert.equal(acceptJobAttack(pl,{...wire,seq:packet.seq+3,x:10000},now+200000),false);
    if(def.speed) {
      const shots=createJobProjectiles(); shots.add(packet,0,true); assert.ok(shots.count);
      let hits=0; shots.update(.01,100, p => { hits+=p.damage.hits; return {mob:{x:1}}; });
      for(let time=200;time<=1200;time+=100) shots.update(.01,time,p=>{hits+=p.damage.hits;return{mob:{x:1}};});
      assert.equal(shots.count,0); assert.equal(hits,def.projectileHits ?? a.hits);
    }
  }
  assert.equal(acceptJobAttack({x:0,y:100},{...abilityStats(j.id),seq:1,x:0,y:100,skill:99},0),false);
}
const kinds=new Map([['dummy',{hp:1,speed:0,behavior:'walk',size:{w:30,h:40},buffDrop:1,buffDropCount:2}]]);
const sim=createMobSim({kinds,zones:[{i:0,x1:0,x2:100,y:100,max:1,mobs:['dummy']}],rnd:()=>.1});
sim.fill(0); const hit=sim.hit({x1:0,x2:100,y1:0,y2:110},0,1,[999]);
assert.ok(hit.killed); assert.deepEqual(hit.buffs,['heal']);
console.log('PASS all 12 skills: cooldowns, canonical damage, wire round-trip, replay/origin validation, projectile hit totals; no attack upgrade drops');

for(const job of ['archer','thief']) {
  const a=abilityStats(job,0),def=abilityDefinition(job,0),shots=createJobProjectiles();
  assert.equal(a.hits,2);assert.equal(def.shots,2);assert.equal(a.animMs,360);
  shots.add({...a,user_id:'basic',seq:1,x:0,y:100,dir:'right'},0,true);
  assert.equal(shots.count,2);assert.ok(shots.snapshot().shots.every(p=>p.hits===1));
  assert.equal(clampAttack({...a,hits:1}).hits,2);
  assert.equal(abilityStats(job,1).hits,3);
}
console.log('PASS archer/thief basics launch two one-hit projectiles; damage claims normalize to two hits; 360ms cadence and triple skills remain unchanged');
