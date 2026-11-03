import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url)));

import {createBossEntrance,drawBossEntrance,BOSS_ENTRANCES,ENTRANCE_DURATION} from '../src/client/game/boss-entrance.js';
import {FUN_NPCS,nearbyPlayful,playfulPoint,playfulChoices,playfulReply,rpsResult,drawFunNpc,drawPlayfulReaction} from '../src/client/game/playful-npcs.js';
import {recordingContext} from './normal-skill-visuals.test.mjs';
for(const npc of Object.values(FUN_NPCS))for(const [part,id]of Object.entries(npc.avatar))assert.ok(manifest.parts[part].some(p=>p.id===id),part+':'+id);
const state={id:'run1',phase:'ready',mode:'boss',started:1000},e=createBossEntrance();
assert.equal(e.observe({...state,mode:'defense'},'village',1200),null);
for(const area of Object.keys(BOSS_ENTRANCES)){
 e.clear();const active=e.observe(state,area,1200);assert.equal(active.area,area);assert.equal(e.observe({...state,rev:2},area,1300),active);
 for(const reduced of [false,true])for(const now of [1000,1400,3100,5199,5200]){const rec=recordingContext();drawBossEntrance(rec.context,active,{x:900,y:800},300,200,1.5,now,reduced);rec.balanced();}
 assert.equal(e.observe({...state,phase:'boss'},area,6000),null);
 assert.equal(e.observe(state,area,1400),null,'old ready snapshot never replays entrance');
 const late=createBossEntrance();assert.equal(late.observe(state,area,1000+ENTRANCE_DURATION),null,'late join skips expired entrance');
 assert.ok(new Set(Object.values(FUN_NPCS).map(n=>n.avatar.hat)).size>=3);
 const map={id:area,groundY:800,spawn:{x:900}};
 for(const kind of ['mascot','fun']){
  const point=playfulPoint(map,kind);assert.equal(nearbyPlayful(map,{...point,dead:false}).kind,kind);
  assert.equal(nearbyPlayful(map,{...point,y:point.y-100,dead:false}),null);
  assert.equal(nearbyPlayful(map,{...point,dead:true}),null);
  for(const choice of playfulChoices(area,kind))assert.ok(playfulReply(area,kind,choice,0,()=>0).text.length>10);
  assert.equal(playfulReply(area,kind,'invalid'),null);
 }
 const rec=recordingContext();drawFunNpc(rec.context,map,0,0,1,100,{renderer:{draw(){},frameAt:()=>0},avatar:{}});drawPlayfulReaction(rec.context,map,'mascot',0,0,1,300,{text:'!',until:1800});rec.balanced();
}
let wins=0,losses=0,draws=0;for(const a of ['가위','바위','보'])for(const b of ['가위','바위','보']){const r=rpsResult(a,b);if(r==='win')wins++;else if(r==='lose')losses++;else draws++;}assert.deepEqual([wins,losses,draws],[3,3,3]);assert.equal(rpsResult('invalid','가위'),null);
const before=JSON.stringify(FUN_NPCS);for(let i=0;i<30;i++)playfulReply('quarry','fun','바위',i,()=>.5);assert.equal(JSON.stringify(FUN_NPCS),before,'flavor games do not mutate roster or progression');
console.log('PASS four boss entrances, fresh/late/deduplicated snapshots, finite effects, nearby/E interaction bounds, all 9 RPS outcomes and harmless flavor choices');
