import assert from 'node:assert/strict';
import {starterState,cleanState,applyCommand,activeJob,loadout,stageUnlocked,combatStats,skillUnlocked} from '../src/client/game/progression.js';
import {acceptJobAttack,abilityStats} from '../src/client/game/jobs.js';
import {createCompanionFollower,sortSceneActors} from '../src/client/game/scene-order.js';
import {handAnchor} from '../src/client/game/avatar-hand-anchors.js';
import {createMoveInput} from '../src/client/game/input.js';
let legacy=starterState('mage');delete legacy.activeWeapon;legacy.pets={'village:4':{level:2}};legacy.pet='village:4';legacy.gold=1234;legacy.highest.mage=3;
let s=cleanState(legacy,'mage');assert.equal(activeJob(s),'mage');assert.equal(s.pet,'village:4');assert.equal(s.gold,1234);
s.items.push({id:'bow',kind:'bow',tier:1},{id:'claw',kind:'claw',tier:2},{id:'sword',kind:'sword',tier:0},{id:'shield',kind:'shield',tier:2});s=cleanState(s);
for(const [id,job]of [['bow','archer'],['claw','thief'],['sword','warrior'],['starter-mage','mage']]){
 s=applyCommand(s,{type:'equip',id}).state;assert.equal(activeJob(s),job);assert.equal(loadout(s).job,job);assert.equal(s.pet,'village:4');assert.equal(stageUnlocked(s,job,'forest'),true);
}
s=applyCommand(s,{type:'equip',id:'shield'}).state;assert.equal(activeJob(s),'mage');assert.equal(loadout(s).shield,2);assert.ok(combatStats(loadout(s)).defense>=16);
assert.throws(()=>applyCommand(s,{type:'sell',id:s.activeWeapon}),/착용/);
s=applyCommand(s,{type:'sell',id:'sword'}).state;assert.equal(s.equipped.warrior,undefined);
const player={x:0,y:100,job:'mage'};
const mage={...abilityStats('mage',3),loadout:{weapon:'staff',tier:2,highest:2},seq:1,x:0,y:100};assert.equal(acceptJobAttack(player,mage,1000),true);
const bow={...abilityStats('archer',3),loadout:{weapon:'bow',tier:2,highest:2},seq:2,x:0,y:100};assert.equal(acceptJobAttack(player,bow,1100),false);assert.equal(acceptJobAttack(player,bow,16000),true);
assert.equal(acceptJobAttack({x:0,y:100},{...mage,loadout:{weapon:'bow',tier:2,highest:2}},0),false);
const follower=createCompanionFollower();let pose=follower.sample({id:s.pet,mapId:'village',x:1647,y:800,now:0});assert.equal(pose.id,'village:4');
for(const area of ['quarry','forest','village']){pose=follower.sample({id:s.pet,mapId:area,x:230,y:800,now:1000});assert.equal(pose.id,'village:4');assert.equal(pose.mapId,area);assert.ok(Number.isFinite(pose.x)&&Number.isFinite(pose.y));assert.ok(Math.abs(pose.x-230)<100);}
follower.reset();assert.equal(follower.sample({id:s.pet,mapId:'quarry',x:230,y:800,now:2000}).id,s.pet);assert.equal(follower.sample({id:null,x:230,y:800}),null);
const actors=[{id:'pet',kind:'pet',y:800},{id:'me',kind:'player',y:800},{id:'npc',kind:'npc',y:800},{id:'high',kind:'mob',y:500},{id:'mob',kind:'mob',y:800}];assert.deepEqual(sortSceneActors(actors).map(a=>a.id),['high','npc','mob','me','pet']);assert.deepEqual(actors.map(a=>a.id),['pet','me','npc','high','mob']);
const hands=new Set();for(let f=0;f<13;f++){const h=handAnchor(f);for(const p of [h.N,h.F])assert.ok(p.every(Number.isFinite));hands.add(JSON.stringify(h.N));}assert.ok(hands.size>10);assert.ok(handAnchor(2).N[0]<0);assert.ok(handAnchor(12).N[0]>10);
const input=createMoveInput();input.press('left-thumb',-1);input.pressAction('right-thumb','attack',0);assert.equal(input.direction(),-1);assert.equal(input.wantsAttack(10),true);input.release('right-thumb');assert.equal(input.direction(),-1);input.release('left-thumb');assert.equal(input.direction(),0);
console.log('PASS legacy equipment/pets preserved, weapon-driven skills and shared cooldown, universal shield, global stage milestones, cross-map companion and actor order, 13 rig hand anchors and independent thumbs');
