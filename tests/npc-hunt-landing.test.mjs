import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {NPC_ROSTER} from '../src/client/game/npc-roster.js';
import {createHuntChain} from '../src/client/game/hunt-chain.js';
import {createMoveInput} from '../src/client/game/input.js';
import {createBody,stepBody,PHYS} from '../src/client/game/physics.js';
import {starterState,applyCommand,STAGES,cleanState} from '../src/client/game/progression.js';
import {cleanGameEvent} from '../src/client/backend/common.js';
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url)));
const names=new Set(),looks=new Set();for(const cast of Object.values(NPC_ROSTER))for(const npc of Object.values(cast)){assert.ok(!names.has(npc.name));names.add(npc.name);for(const [part,id]of Object.entries(npc.avatar))assert.ok(manifest.parts[part].some(p=>p.id===id),part+':'+id);looks.add(JSON.stringify(npc.avatar));}assert.equal(looks.size,8);
// The actual runtime used raw map order: a lower platform precedes the upper floor.
// Reproduce two real input taps, including held jump after the second tap.
for(const dt of [1/120,1/60,1/30,.05]){
 const raw=[{id:'low',x1:0,x2:300,y:650},{id:'high',x1:0,x2:300,y:495}],input=createMoveInput(),b=createBody(150,800,800),opt={platforms:raw,groundY:800,speed:240,minX:0,maxX:1000};let tapped=false,landed=false;
 input.pressAction('touch:jump','jump',0);input.tap('up',0);
 for(let frame=0;frame<200;frame++){
  const now=frame*dt*1000;if(!tapped&&now>=120){input.release('touch:jump');input.pressAction('touch:jump','jump',now);input.tap('up',now);tapped=true;}
  const sup=input.takeSuper(now),r=stepBody(b,{dir:0,jump:input.wantsJump(now,PHYS.jumpBufferMs),superKind:sup?.kind,superAge:sup?.age},dt,opt);
  if(r.jumped)input.consumeJump();if(r.landed&&b.on){input.suppressJumpHold();if(b.on.id==='high')landed=true;}
  if(landed&&frame*dt>2)break;
 }
 assert.ok(landed,'raw-order upper floor at dt='+dt);assert.equal(b.on?.id,'high');assert.equal(b.grounded,true,'held jump must not launch again');
}
// Pick the highest crossed surface even if several floors are passed in one frame.
const falling=createBody(150,400,800);falling.vy=1500;stepBody(falling,{dir:0},.2,{platforms:[{id:'lower',x1:0,x2:300,y:700},{id:'upper',x1:0,x2:300,y:500}],speed:240,minX:0,maxX:1000,groundY:800});assert.equal(falling.on.id,'upper');
const chain=createHuntChain();for(let n=1;n<=40;n++){const c=chain.record('a',n*1000);assert.equal(c.count,n);assert.ok(c.bonus<=30);}assert.equal(chain.record('b',40000).count,1);assert.equal(chain.record('a',61001).count,1);chain.clear();assert.equal(chain.record('a',62000).count,1);
for(const [area,st]of Object.entries(STAGES)){
 let s=starterState();s.kills[area]=19;s.items[0].kind='bow';s.activeWeapon=s.items[0].id;
 const packet={type:'loot',receipt:'milestone-'+area,area,x:100,y:800,items:[],gold:10};const r=applyCommand(s,packet);assert.equal(r.result.contract,true);s=r.state;assert.equal(s.kills[area],20);assert.equal(s.pending.filter(d=>d.kind==='bow').length,1);assert.equal(s.pending.find(d=>d.kind==='bow').tier,st.order);assert.equal(s.pending.filter(d=>d.kind==='gold').reduce((a,d)=>a+d.amount,0),10+150*3**(st.order-1));assert.deepEqual(applyCommand(s,packet).state.pending,s.pending);assert.equal(cleanState(s).kills[area],20);
 const event=applyCommand(s,{...packet,receipt:'event-test-'+area});assert.equal(event.state.kills[area],20);assert.equal(event.result,null);
 const full=starterState();full.kills[area]=19;full.pending=Array.from({length:200},(_,n)=>({id:'full'+n,area,kind:'gold',amount:1,x:0,y:800}));assert.throws(()=>applyCommand(full,packet));assert.equal(full.kills[area],19);
}
const net={host:'host',owner:'owner',receipt:'one',area:'village',x:100,y:800,gold:10,items:[],combo:30};assert.equal(cleanGameEvent('loot',net).combo,30);for(const combo of [0,-1,1000,1.5])assert.equal(cleanGameEvent('loot',{...net,combo}),null);
console.log('PASS eight distinct valid NPCs, real double-tap raw-order landing/hold, combo isolation/expiry/cap and atomic persistent contract rewards');
