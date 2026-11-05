import assert from 'node:assert/strict';
import {touchLayout,combatReserve} from '../src/client/ui/game-layout.js';
for(const [w,h,coarse,expected]of [[390,844,false,true],[844,390,true,true],[1000,550,false,false],[1180,820,true,true],[1280,800,false,false],[1366,768,true,false]])assert.equal(touchLayout(w,h,coarse),expected);
for(const [w,h]of [[320,640],[390,844],[844,390],[1024,500]]){const reserve=combatReserve(w,h);assert.ok(reserve>=100&&reserve<=170);assert.ok(h-reserve>=180);assert.equal(combatReserve(w,h,true),64);}
console.log('PASS portrait/landscape/tablet layout selection, visible combat space and keyboard chat reserve');
