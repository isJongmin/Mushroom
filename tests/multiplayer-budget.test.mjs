import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {createJobProjectiles} from '../src/client/game/combat.js';
import {createSkillAttacks,buildStrikePlan} from '../src/client/game/attack-patterns.js';
import {createMobView} from '../src/client/game/mobs.js';
import {abilityStats,acceptJobAttack} from '../src/client/game/jobs.js';
import {cleanGameEvent,createEventGate} from '../src/client/backend/common.js';
import {scenePolicy,sceneDpr,createSceneBudget} from '../src/client/game/scene-budget.js';
import {readPanelCollapsed,writePanelCollapsed} from '../src/client/ui/panel-preference.js';

const attack=(job,slot,id='player',seq=1)=>({...abilityStats(job,slot),user_id:id,seq,x:200,y:500,dir:'right'});
// Non-host mobView.list is a Map iterator, not an Array. This used to throw before visuals/cooldown.
{
 const mobs=[{id:'target',x:270,y:500,hp:100,s:'move'}],map=new Map(mobs.map(m=>[m.id,m]));
 const view=createMobView({kinds:new Map(),onDamage(){},onDie(){}});
 for(const job of ['warrior','archer','mage','thief'])for(let slot=0;slot<4;slot++){
   const a=attack(job,slot);assert.deepEqual(buildStrikePlan(a,map.values()),buildStrikePlan(a,mobs));
   const effects=createSkillAttacks();assert.doesNotThrow(()=>effects.add(a,0,false,view.list));
   assert.equal(effects.count,1);
 }
}
// Twenty legitimate thief ultimates launch 180 shots. The former 160 cap silently deleted 20.
const shots=createJobProjectiles();for(let n=0;n<20;n++)shots.add(attack('thief',3,'p'+n),0,true);
assert.equal(shots.count,180);assert.equal(shots.snapshot().shots.filter(s=>s.id.startsWith('p0:')).length,9);
let hits=0;shots.update(.016,2000,()=>{hits++;return {mob:{x:200,y:500}};});assert.equal(hits,180);assert.equal(shots.count,0);

// Legitimate sender cadence survives receipt-time jitter; early casts and repeated bursts still fail.
const timed=(castAt,seq,session='one')=>({...attack('warrior',1,'p',seq),castAt,castSession:session});
const p={x:200,y:500};assert.equal(acceptJobAttack(p,timed(0,1),1000),true);
assert.equal(acceptJobAttack(p,timed(3000,2),3850),true,'150ms variation no longer makes the skill disappear');
assert.equal(acceptJobAttack(p,timed(3100,3),6900),false,'sender cannot shorten the actual cooldown');
assert.equal(acceptJobAttack(p,timed(6000,3),6700),false,'jitter allowance does not accumulate into faster casting');
assert.equal(acceptJobAttack(p,timed(6000,3),7000),true);assert.equal(acceptJobAttack(p,timed(9000,3),10000),false,'sequence replay');
assert.equal(acceptJobAttack(p,timed(0,4,'reload'),10000),true,'new mount resets its relative clock without resetting receipt pacing');
assert.equal(acceptJobAttack(p,timed(3000,5,'another-session'),10100),false,'changing session does not bypass receipt deadline');
const wire=cleanGameEvent('atk',timed(1234,10));assert.equal(wire.castAt,1234);assert.equal(wire.castSession,'one');
assert.equal(cleanGameEvent('atk',{...timed(1234,10),castSession:'<bad>'}).castSession,undefined);
const old={x:200,y:500};assert.ok(acceptJobAttack(old,attack('warrior',1),0));assert.equal(acceptJobAttack(old,{...attack('warrior',1),seq:2},2970),false,'legacy checks stay strict');
// One host can acknowledge all 180 impacts without hitting the former 40 individual packet limit.
{
 const sent=[],timers=new Map(),stats={};let timerId=0;
 const gate=createEventGate((event,payload)=>sent.push([event,payload]),stats,{batchImpacts:true,schedule:fn=>{timers.set(++timerId,fn);return timerId;},cancel:id=>timers.delete(id)});
 for(let n=0;n<180;n++)assert.equal(gate.push('impact',{host:'host',id:'p:'+n,x:n,y:500,job:'thief',skill:3,mapId:'village'}),true);
 assert.equal(sent.length,0);const flush=timers.values().next().value;timers.clear();flush();assert.equal(sent.length,8);
 const impacts=sent.flatMap(([event,p])=>{assert.equal(event,'impact');assert.ok(p.impacts.length<=24);const clean=cleanGameEvent(event,p);assert.ok(clean);return clean.impacts;});
 assert.equal(new Set(impacts.map(i=>i.id)).size,180);assert.equal(stats.evDropped||0,0);
 assert.equal(cleanGameEvent('impact',{host:'host',impacts:[{id:'bad id',x:0,y:0}]}),null);
 assert.equal(cleanGameEvent('impact',{host:'host',impacts:Array(25).fill({id:'p:1',x:0,y:0})}),null);
 gate.push('impact',{host:'host',id:'p:181',x:0,y:500,job:'thief',skill:3});assert.equal(timers.size,1);gate.cancel();assert.equal(timers.size,0);
}

const crowd=scenePolicy(20);assert.equal(crowd.remotePets,1);assert.equal(scenePolicy(1).remotePets,3);
for(const count of [1,8,20]){const policy=scenePolicy(count),dpr=sceneDpr(1280,850,3,policy);assert.ok(1280*850*dpr*dpr<=policy.maxPixels+1);}
const budget=createSceneBudget();for(let i=0;i<100;i++)budget.sample(40,1,i*40);assert.equal(budget.sample(40,1,5000).crowded,true);

// Compare actual native-canvas draw work. Rendering quality must never change simulation plans.
const casts=createSkillAttacks(),jobs=['warrior','archer','mage','thief'];
for(let n=0;n<20;n++)casts.add(attack(jobs[n%4],3,n===0?'local':'p'+n),0,true);
const before=JSON.stringify(casts.snapshot());
function draw(compact){const cv=createCanvas(1280,720),raw=cv.getContext('2d');let calls=0;
 const ctx=new Proxy(raw,{get(t,key){const v=t[key];return typeof v==='function'?(...args)=>{calls++;return v.apply(t,args);}:v;},set(t,key,value){t[key]=value;return true;}});
 const started=performance.now();casts.draw(ctx,0,0,1,1000,{compact,localUserId:'local'});return {calls,ms:performance.now()-started};}
const full=draw(false),compact=draw(true);assert.ok(compact.calls<full.calls*.4,`${compact.calls}/${full.calls} drawing calls`);
assert.equal(JSON.stringify(casts.snapshot()),before,'compact mode never removes strikes or changes damage timing');
const own=createSkillAttacks();own.add(attack('mage',3,'local'),0,true);
function ownImage(compact){const cv=createCanvas(1000,720);own.draw(cv.getContext('2d'),0,0,1,1000,{compact,localUserId:'local'});return cv.toBuffer('image/png');}
assert.deepEqual(ownImage(false),ownImage(true),'own skill effect stays pixel-identical');
const storage=new Map(),adapter={getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)};
assert.equal(readPanelCollapsed(adapter,'panel',true),true);writePanelCollapsed(adapter,'panel',false);assert.equal(readPanelCollapsed(adapter,'panel',true),false);
assert.equal(readPanelCollapsed({getItem(){throw Error();}},'panel',true),true);writePanelCollapsed({setItem(){throw Error();}},'panel',false);
console.log('PASS 20-user/180-shot retention, jitter/clock/replay safeguards, pixel budget, own-skill preservation, unchanged strike plans and persistent panel collapse');
console.log(JSON.stringify({scene:'20 concurrent ultimates; native canvas renderer only',full,compact}));
