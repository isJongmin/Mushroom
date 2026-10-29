import assert from 'node:assert/strict';
import { createJobProjectiles, projectileCollision } from '../src/client/game/combat.js';
import { createMobSim, RESPAWN_MS } from '../src/client/game/mobs.js';
import { attackStats } from '../src/client/game/buffs.js';

const boxFor = m => ({x1:m.x-15,x2:m.x+15,y1:m.y-40,y2:m.y});
for (const dir of [-1, 1]) {
  const targets = [120,60].map((x,i)=>({id:String(i),x:dir*x,y:100,hp:100,s:'move'}));
  const p={x:0,y:70,dir};
  const box={x1:dir>0?-8:-208,x2:dir>0?208:8,y1:59,y2:81};
  assert.equal(projectileCollision(p,box,targets,boxFor).mob.id,'1');
  assert.equal(projectileCollision(p,box,targets,boxFor).impactX, dir*37);
  assert.equal(projectileCollision(p,{...box,y1:110,y2:130},targets,boxFor),null);
  assert.equal(projectileCollision(p,box,targets.map(m=>({...m,s:'die'})),boxFor),null);
}
for (const job of ['archer','mage','thief']) for (const authoritative of [false,true]) {
  const shots=createJobProjectiles();
  shots.add({...attackStats({},job),x:0,y:100,dir:'right'},0,authoritative);
  let damage=0, visual=0;
  const target={x:60,y:100,hp:100,s:'move'};
  const collide=(p,box)=>projectileCollision(p,box,[target],boxFor);
  shots.update(.2,200,(p,b)=>{damage++; return collide(p,b);},(p,b)=>{visual++; return collide(p,b);});
  assert.equal(shots.count,0);
  assert.equal(damage>0,authoritative);
  assert.equal(visual>0,!authoritative);
  // Every peer draws an impact at the first contact, before the target center.
  const bursts=shots.snapshot().bursts;
  assert.ok(bursts.length>0);
  assert.ok(bursts.every(b=>b.x===37));
}
const kinds=new Map([['dummy',{hp:100,speed:0,behavior:'walk',size:{w:30,h:40},buffDrop:0}]]);
const zones=[{i:0,x1:0,x2:100,y:100,max:3,mobs:['dummy']}];
let players=[{x:50,y:100,dead:false}];
const sim=createMobSim({kinds,zones,rnd:()=>.5,getPlayers:()=>players});
sim.fill(0);
assert.equal(sim.size,0); assert.equal(sim.stats.pending,3);
sim.step(0,1000); assert.equal(sim.size,0); assert.equal(sim.stats.pending,3);
players=[]; sim.step(0,1999); assert.equal(sim.size,0);
sim.step(0,2000); assert.equal(sim.size,3); assert.equal(sim.stats.pending,0);
// Actual death/respawn also defers while the zone is occupied.
for (let i=0;i<3;i++) sim.hit({x1:-100,x2:200,y1:0,y2:110},0,1,[1000]);
sim.step(1,3000); assert.equal(sim.size,0); assert.equal(sim.stats.pending,3);
players=[{x:50,y:100}]; sim.step(0,3000+RESPAWN_MS); assert.equal(sim.size,0);
players=[{x:50,y:100,dead:true}]; sim.step(0,4000+RESPAWN_MS); assert.equal(sim.size,3);
// Players on a separated platform do not block and handoff loading remains bounded.
players=[{x:50,y:200}]; sim.clear(); sim.fill(0); assert.equal(sim.size,3);
const loaded=sim.snapshot(); players=[{x:50,y:100}]; sim.load(loaded,0);
assert.equal(sim.size,0); assert.equal(sim.stats.pending,3);
players=[]; sim.step(0,1000); assert.equal(sim.size,3);
const wide=createMobSim({kinds,zones:[{...zones[0],x2:1000,max:1}],rnd:()=>.5,getPlayers:()=>[{x:500,y:100}]});
wide.fill(0); assert.ok(Math.abs(wide.snapshot()[0].x-500)>=90);
console.log('Swept host/spectator projectiles, impact effects and safe deferred mob spawning pass');

// Authoritative impacts survive a death snapshot arriving before the visual shot.
const ackShots=createJobProjectiles();
const ackAttack={...attackStats({},'mage'),user_id:'player-1',seq:42,x:0,y:100,dir:'right'};
ackShots.add(ackAttack,0);
ackShots.update(.01,10,()=>assert.fail('replicas cannot damage'),()=>null);
assert.equal(ackShots.count,1);
assert.equal(ackShots.impact('player-1:42:0',37,70,20,'mage'),true);
assert.equal(ackShots.count,0);
assert.equal(ackShots.impact('player-1:42:0',37,70,21,'mage'),false);
assert.equal(ackShots.snapshot().bursts.length,1); // Duplicate acknowledgements produce one burst.
ackShots.clear();
ackShots.impact('player-1:42:0',37,70,0,'mage');
ackShots.add(ackAttack,20); assert.equal(ackShots.count,0); // Ack before attack.
ackShots.clear(); ackShots.add(ackAttack,0);
ackShots.update(.2,200,undefined,()=>({mob:{x:60},impactX:37}));
assert.equal(ackShots.impact('player-1:42:0',37,70,210,'mage'),false); // Local prediction already burst.
const {cleanGameEvent,stampGameEvent,createEventGate,isGameEvent}=await import('../src/client/backend/common.js');
assert.equal(isGameEvent('impact'),true);
const impact={id:'player-1:42:0',x:37,y:70,job:'mage',mapId:'forest'};
const packet=cleanGameEvent('impact',stampGameEvent('impact',impact,'host-1'));
assert.equal(packet.host,'host-1'); assert.equal(packet.id,impact.id); assert.equal(packet.job,'mage');
assert.equal(cleanGameEvent('impact',{...packet,id:'bad id'}),null);
assert.equal(cleanGameEvent('impact',{...packet,x:Infinity}),null);
assert.equal(cleanGameEvent('impact',{...packet,id:'x'.repeat(111)}),null);
assert.equal(cleanGameEvent('impact',{...packet,host:''}),null);
const gateStats={}; let sent=0;
const gate=createEventGate(()=>sent++,gateStats);
for(let i=0;i<40;i++) assert.equal(gate.push('impact',packet),true);
assert.equal(gate.push('impact',packet),false); assert.equal(sent,40); assert.equal(gateStats.evDropped,1);
gate.cancel();
console.log('Authoritative impact ids, reordered acknowledgements, deduplicated bursts and bounded packet rate pass');
