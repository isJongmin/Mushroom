import assert from 'node:assert/strict';
import { readProfile, writeProfile } from '../src/client/store.js';
import { JOBS } from '../src/client/game/jobs.js';
import { createMobSim, RESPAWN_MS } from '../src/client/game/mobs.js';
const memory = new Map();
globalThis.localStorage = {getItem:k=>memory.get(k) ?? null, setItem:(k,v)=>memory.set(k,v)};
memory.set('legacy', JSON.stringify({nickname:'테스터',avatar:{}}));
assert.equal(readProfile('legacy').job,'warrior');
for(const job of JOBS) {
 assert.equal(writeProfile('new',{nickname:'테스터',avatar:{},job:job.id}),true);
 assert.equal(readProfile('new').job,job.id);
 assert.equal(Object.keys(readProfile('new').avatar).length,7);
}
assert.equal(writeProfile('bad',{nickname:'테스터',avatar:{},job:'<script>'}),true);
assert.equal(readProfile('bad').job,'warrior');
assert.equal(RESPAWN_MS,10000);
const kinds = new Map([['dummy',{hp:10,speed:0,behavior:'walk',size:{w:30,h:40},buffDrop:0}]]);
const sim=createMobSim({kinds,zones:[{i:0,x1:0,x2:100,y:100,max:1,mobs:['dummy']}],rnd:()=>.5});
sim.fill(0);
assert.equal(sim.snapshot().length,1);
assert.equal(sim.hit({x1:0,x2:100,y1:40,y2:110},0,1,[100]).killed,true);
sim.step(.7,700); assert.equal(sim.snapshot().length,0);
sim.step(0,10699); assert.equal(sim.snapshot().length,0);
sim.step(0,10700); assert.equal(sim.snapshot().length,1);
console.log('PASS profile job persistence, legacy/default sanitization and ten-second monster respawn');
