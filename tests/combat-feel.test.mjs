import assert from 'node:assert/strict';
import {createCombatFeel,FEEL_LIMITS} from '../src/client/game/combat-feel.js';
import {recordingContext} from './normal-skill-visuals.test.mjs';
const f=createCombatFeel();
assert.equal(f.shouldHold(0),false);
f.hit({id:'m',x:30,y:40,now:1000,local:true});
assert.equal(f.shouldHold(1000),false,'impact frame renders before pause');
assert.equal(f.shouldHold(1016),true);assert.equal(f.shouldHold(1043),false);
assert.equal(f.hit({id:'m',x:30,y:40,now:1008,local:true}),false,'same packet/damage batch does not duplicate sparks');
f.hit({id:'m2',x:30,y:40,now:1030,local:true,strong:true});assert.equal(f.holdingUntil,1042,'AOE does not extend stop');
f.hit({id:'m3',x:30,y:40,now:1200,local:true,strong:true});assert.equal(f.holdingUntil,1262);
assert.equal(f.shouldHold(1200),false);assert.equal(f.shouldHold(1216,{reduced:true}),false);assert.equal(f.shouldHold(1230),false,'reduced motion cancels pending stop');
f.hit({id:'other',x:20,y:20,now:1400});assert.equal(f.shouldHold(1410),false,'remote hit does not stop local rendering');
f.hit({id:'self',x:20,y:20,now:1600,local:true,hurt:true});assert.notEqual(f.camera(1630).x,0);assert.deepEqual(f.camera(1630,true),{x:0,y:0});assert.equal(f.pose('self',1660,true).x,0);
assert.equal(f.shouldHold(1600,{blocked:true}),false);assert.equal(f.shouldHold(1620),false,'modal/connection cancels pending stop');
for(let i=0;i<200;i++)f.hit({id:'flood'+i,x:100,y:100,now:2000+i*30,local:true});assert.equal(f.size,FEEL_LIMITS.maxImpacts);
for(const reduced of [false,true])for(const now of [7900,8000,8200,9000]){const rec=recordingContext();f.draw(rec.context,0,0,2,now,reduced);rec.balanced();}
f.clear();assert.equal(f.size,0);assert.equal(f.shouldHold(1),false);assert.deepEqual(f.pose('m',100),{x:0,brightness:1});
console.log('PASS confirmed impact frame, capped 42/62ms visual holds, AOE/replay isolation, bounded sparks, hit reactions, reduced motion and teardown');
