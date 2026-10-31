import assert from 'node:assert/strict';
import {bossPose,bossStrikePoint,bossDanger,advanceBoss,cleanBoss,installBoss,BOSS_KIND} from '../src/client/game/garden-boss.js';
import {createGarden,cleanGarden,gardenZones} from '../src/client/game/garden.js';
import {createMobSim,normalizeMobManifest} from '../src/client/game/mobs.js';
import {drawBoss,drawBossTelegraph} from '../src/client/game/boss-visuals.js';
import {drawCostume,costumeAvatar,COSTUMES} from '../src/client/game/reward-costumes.js';
import {drawQuestNpc} from '../src/client/game/quest-npc.js';
import {recordingContext} from './normal-skill-visuals.test.mjs';
import {readFileSync} from 'node:fs';
const point={x:1800,y:800},b={pattern:'stomp',seq:1,at:1000,targetX:1550,max:1400,homeX:1800,originX:1800};
assert.equal(bossPose(b,point,1000).height,0);assert.ok(bossPose(b,point,2100).height>240);assert.ok(bossPose(b,point,2100).x<1800);assert.ok(bossPose(b,point,2800).height<1e-6);assert.equal(bossStrikePoint(b,point).x,1550);
assert.ok(bossDanger(b,{x:1550,y:800},point));assert.equal(bossDanger(b,{x:1800,y:800},point),false);assert.equal(bossDanger(b,{x:1550,y:700},point),false);
const next=advanceBoss(b,5000,1900);assert.equal(next.originX,1550);assert.equal(bossPose(next,point,5000).x,1550);assert.ok(bossPose(next,point,6400).x!==1550);assert.deepEqual(cleanBoss(next),next);
const state=createGarden();state.start('restore',0,['a'],'boss');state.tick(5000,{spawnBoss:()=>true,targetX:1550,bossX:1800});const wire=cleanGarden(state.snapshot());assert.equal(wire.boss.homeX,1800);const clone=createGarden();clone.load(wire);assert.deepEqual(bossPose(clone.snapshot().boss,point,5900),bossPose(wire.boss,point,5900));
const defs=normalizeMobManifest(JSON.parse(readFileSync(new URL('../assets/mob/manifest.json',import.meta.url))));installBoss(defs.kinds);assert.ok(defs.kinds.get('garden-runner').speed>defs.kinds.get('slime').speed);assert.ok(defs.kinds.get('garden-guard').hp>defs.kinds.get('mushroom').hp);
const zones=gardenZones([],{spawn:{x:1540},groundY:800},'village');const sim=createMobSim({kinds:defs.kinds,zones,rnd:()=>.5});assert.ok(sim.spawnBoss(1400,0));const pose=bossPose(b,point,2100);sim.moveBoss(pose.x,800-pose.height,pose.dir);const snap=sim.snapshot();assert.ok(snap[0].y<600);const inherited=createMobSim({kinds:defs.kinds,zones});inherited.load(snap,0);assert.equal(inherited.bossMob().y,snap[0].y);
assert.equal(costumeAvatar({hat:'mage-hat',hair:'x'},'royal-guardian').hat,'none');assert.equal(costumeAvatar({hat:'mage-hat'},'sprout-cape').hat,'mage-hat');
for(const pattern of ['stomp','spores','ring','exposed'])for(const t of [0,500,1100,1800,2200,4000]){
 const rec=recordingContext(),phase={...b,pattern},p=bossPose(phase,point,1000+t);
 drawBoss(rec.context,{s:'move',dir:1},300,400,1.5,1000+t,p);drawBossTelegraph(rec.context,phase,point,1400,300,1.5,1000+t);drawQuestNpc(rec.context,{x:1500,y:800},1400,300,1.5);rec.balanced();
 assert.equal(rec.commands.some(x=>x[0]==='ellipse'||x[0]==='roundRect'||x[0]==='arc'),false,'boss and NPC silhouettes must stay block-based');
}
for(const costume of COSTUMES)for(const left of [true,false])for(const rear of [true,false]){
 const rec=recordingContext();for(const back of [true,false])drawCostume(rec.context,costume.id,200,300,2,{left,rear,back,side:!rear,moving:true,time:240,fit:{headTop:82,headX:2,neck:45,shoulder:13,bodyX:0,hem:18}});rec.balanced();
}
console.log('PASS real boss movement/airborne collision, landing-centered hazards, snapshot inheritance, dynamic enemies, block-only rendering and attached costume directions');
