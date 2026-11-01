import assert from 'node:assert/strict';
import {petPose,SKILL_KEYS,drawEquippedGear,drawEquipBurst} from '../src/client/game/appearance-motion.js';
import {drawItem,drawPet} from '../src/client/game/progression-visuals.js';
import {GRADE_COLORS} from '../src/client/game/progression.js';
import {recordingContext} from './normal-skill-visuals.test.mjs';
assert.deepEqual([SKILL_KEYS.KeyK,SKILL_KEYS.KeyL,SKILL_KEYS.Semicolon],[1,2,3]);
assert.deepEqual([SKILL_KEYS.Digit1,SKILL_KEYS.Digit2,SKILL_KEYS.Digit3],[1,2,3]);
assert.equal(SKILL_KEYS.KeyJ,undefined);assert.equal(SKILL_KEYS.KeyW,undefined);
const signatures=new Set();
for(const area of ['village','quarry','forest'])for(let tier=0;tier<5;tier++){
 const id=area+':'+tier;signatures.add(JSON.stringify([petPose(id,173),petPose(id,411,{moving:true})].map(({x,y,angle,sx,sy})=>({x,y,angle,sx,sy}))));
 for(const reduced of [false,true])for(const reaction of [null,'loot','hurt','attack'])for(const now of [0,113,850]){
  const pose=petPose(id,now,{moving:true,reaction,reduced});for(const key of ['x','y','angle','sx','sy'])assert.ok(Number.isFinite(pose[key]));
  const rec=recordingContext();drawPet(rec.context,id,100,120,2,now,2,{moving:true,reaction,reduced,left:true});rec.balanced();
 }
 assert.deepEqual(petPose(id,0,{reduced:true}),petPose(id,1000,{reduced:true}));
 assert.notDeepEqual(petPose(id,300),petPose(id,300,{reaction:'loot'}));
}
assert.equal(signatures.size,15);
for(const kind of ['sword','bow','staff','claw','shield']){const shapes=new Set();for(let tier=0;tier<5;tier++){const rec=recordingContext();drawItem(rec.context,kind,40,50,1.2,GRADE_COLORS[tier],tier);rec.balanced();shapes.add(JSON.stringify(rec.commands));}assert.equal(shapes.size,5,'each grade changes geometry, not just fill color');}
let calls=[];const draw=(...args)=>calls.push(args);
drawEquippedGear(recordingContext().context,'warrior',{tier:4,shield:2},0,100,1,400,{drawItem:draw});assert.equal(calls.length,2);assert.equal(calls[0][1],'shield');assert.equal(calls[1][1],'sword');
calls=[];drawEquippedGear(recordingContext().context,'mage',{tier:4},0,100,1,400,{hidden:true,drawItem:draw});assert.equal(calls.length,0);
for(let tier=0;tier<5;tier++)for(const age of [-1,0,450,900,901])drawEquipBurst(recordingContext().context,20,30,2,tier,age);
console.log('PASS 15 pet motion signatures, loot/hurt/attack reactions, reduced motion, grade gear/shield rendering, climbing suppression and K/L/semicolon bindings');
// Every pose and facing keeps exactly the selected physical weapon and its grade.
for(const weapon of ['sword','bow','staff','claw'])for(let tier=0;tier<5;tier++)for(let frame=0;frame<13;frame++)for(const left of [false,true]){
 const rec=recordingContext(),items=[];
 drawEquippedGear(rec.context,'warrior',{weapon,tier,shield:-1},120,200,1.7,400,{frame,left,reduced:true,drawItem:(...args)=>items.push(args)});
 assert.equal(items.length,1);assert.equal(items[0][1],weapon);assert.equal(items[0][5],GRADE_COLORS[tier]);assert.equal(items[0][6],tier);assert.deepEqual(items[0][7],{held:true});rec.balanced();
 const held=recordingContext();drawItem(held.context,weapon,0,0,1,GRADE_COLORS[tier],tier,{held:true});held.balanced();
 assert.equal(held.commands.some(([op])=>op==='rotate'),false,'held geometry leaves orientation to the palm pivot');
 assert.equal(held.commands.some(cmd=>JSON.stringify(cmd)===JSON.stringify(['fillRect',-15,13,30,4])),false,'inventory shadow must not float beside the hand');
}
console.log('PASS 520 weapon/grade/pose/facing combinations preserve one selected weapon with palm-local geometry');
