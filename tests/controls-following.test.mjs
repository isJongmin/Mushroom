import assert from 'node:assert/strict';
import {createMoveInput} from '../src/client/game/input.js';
import {createBody,stepBody} from '../src/client/game/physics.js';
import {createCompanionGroup,COMPANION_MIN_GAP} from '../src/client/game/scene-order.js';
// Repeat down events must not create a second physical edge, even with repeat=false.
for(const [source,group,dir]of [['key:ArrowLeft','left',-1],['key:ArrowRight','right',1],['key:KeyA','left',-1],['key:KeyD','right',1]]){
 const input=createMoveInput(),b=createBody(2000,800,800);assert.equal(input.press(source,dir),true);assert.equal(input.tap(group,0,source),false);
 for(let frame=1;frame<360;frame++){
  const now=frame*1000/60;assert.equal(input.press(source,dir),false);assert.equal(input.tap(group,now,source),false);
  const request=input.takeSuper(now);assert.equal(request,null);const result=stepBody(b,{dir:input.direction(),superKind:request?.kind},1/60,{speed:240,minX:0,maxX:5000,groundY:800,platforms:[]});assert.equal(result.fx,null);
 }
 // Releasing after a long hold is not a quick pair of taps.
 input.release(source);input.press(source,dir);assert.equal(input.tap(group,6100,source),false);assert.equal(input.takeSuper(6100),null);
 input.release(source);input.press(source,dir);assert.equal(input.tap(group,6250,source),true);assert.equal(input.takeSuper(6250).kind,group);assert.equal(input.takeSuper(6250),null);
 assert.equal(input.tap(group,6300,source),false);input.clear();assert.equal(input.direction(),0);assert.equal(input.takeSuper(6300),null);
}
const aliases=createMoveInput();aliases.press('key:KeyA',-1);aliases.tap('left',0,'key:KeyA');aliases.press('key:ArrowLeft',-1);assert.equal(aliases.tap('left',80,'key:ArrowLeft'),false,'a second held alias is not a released double tap');assert.equal(aliases.takeSuper(80),null);
const jump=createMoveInput();jump.pressAction('key:ArrowUp','jump',0);jump.tap('up',0,'key:ArrowUp');for(let t=20;t<=100;t+=20){assert.equal(jump.pressAction('key:ArrowUp','jump',t),false);assert.equal(jump.tap('up',t,'key:ArrowUp'),false);}jump.release('key:ArrowUp');jump.pressAction('key:ArrowUp','jump',150);assert.equal(jump.tap('up',150,'key:ArrowUp'),true);assert.equal(jump.takeSuper(150).kind,'up');
const slow=createMoveInput();slow.press('a',-1);slow.tap('left',0,'a');slow.release('a');slow.press('a',-1);assert.equal(slow.tap('left',301,'a'),false);
const ids=['village:0','quarry:1','frost:4'],pets=createCompanionGroup();let poses;
for(let n=0;n<120;n++)poses=pets.sample({ids,x:1000,y:800,dir:1,moving:true,now:n*16});const moving=poses.map(p=>p.x);assert.ok(moving[0]>moving[1]&&moving[1]>moving[2]);const movingSpan=Math.max(...moving)-Math.min(...moving);assert.ok(movingSpan<64);
for(let n=120;n<360;n++)poses=pets.sample({ids,x:1000,y:800,dir:1,moving:false,now:n*16});const idleSpan=Math.max(...poses.map(p=>p.x))-Math.min(...poses.map(p=>p.x));assert.ok(idleSpan<movingSpan);assert.ok(idleSpan<=37);assert.ok(idleSpan>=2*COMPANION_MIN_GAP-1e-9);
const before=poses.map(p=>p.x);poses=pets.sample({ids,x:1010,y:800,dir:1,moving:true,now:360*16});const delta=poses.map((p,i)=>p.x-before[i]);assert.ok(new Set(delta.map(n=>n.toFixed(3))).size>1,'individual lag is observable');
for(let n=361;n<600;n++)poses=pets.sample({ids,x:1000,y:800,dir:-1,moving:false,target:{x:1020,y:800},now:n*16,minX:20,maxX:5980});const sorted=[...poses].sort((a,b)=>a.x-b.x);assert.ok(sorted[2].x-sorted[0].x<40);for(let i=1;i<3;i++)assert.ok(sorted[i].x-sorted[i-1].x>=18-1e-9);
console.log('PASS physical-edge dash: 6-second repeat holds for arrows/A/D, release-required alias guard, fresh double taps and jump preservation; individually lagged pets, compact idle/loot overlap without total stacking');
