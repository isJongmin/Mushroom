import assert from 'node:assert/strict';
import {createCanvas} from '@napi-rs/canvas';
import {taxiPoint,taxiTravelReason,taxiDestinations,drawTownTaxi} from '../src/client/game/town-taxi.js';
import {areaMap,landmarkSignPlacements,drawMinimap,MINIMAP_COLORS} from '../src/client/game/areas.js';
import {explorationPoints} from '../src/client/game/adventure-traits.js';
import {starterState} from '../src/client/game/progression.js';
const state=starterState(),map=areaMap('quarry'),player={...taxiPoint(map),dead:false},base={state,job:'warrior',current:'quarry',to:'village',player,map,now:2000};
assert.equal(taxiTravelReason(base),'');assert.ok(taxiTravelReason({...base,to:'forest'}));
state.traits.events.village.boss=true;state.traits.events.quarry.boss=true;state.traits.events.forest.boss=true;const before=JSON.stringify(state);assert.equal(taxiDestinations(state,'mage','quarry').filter(d=>d.unlocked).length,4,'boss milestones unlock travel for all jobs');
assert.equal(taxiTravelReason({...base,to:'frost'}),'');assert.ok(taxiTravelReason({...base,to:'invalid'}));assert.ok(taxiTravelReason({...base,to:'quarry'}));assert.ok(taxiTravelReason({...base,connected:false}));assert.ok(taxiTravelReason({...base,player:{...player,dead:true}}));assert.ok(taxiTravelReason({...base,player:{...player,x:player.x+161}}));assert.ok(taxiTravelReason({...base,player:{...player,y:player.y-86}}));assert.ok(taxiTravelReason({...base,readyAt:3000}));assert.equal(JSON.stringify(state),before,'travel policy never spends currency or rewrites equipment');
for(const area of ['quarry','forest','frost']){
 const m=areaMap(area),flags=explorationPoints(m),original=JSON.stringify(m.districts),signs=landmarkSignPlacements(m);
 for(const s of signs)for(const f of flags)assert.ok(s.lift>=100||Math.abs(s.x-f.x)>=160||Math.abs(m.groundY-f.y)>115,'district signs do not cover exploration pole or label');
 assert.equal(JSON.stringify(m.districts),original);assert.equal(flags.find(f=>f.id==='entry').x,650,'existing exploration triggers remain at saved coordinates');
 assert.equal(signs[0].x,650);assert.ok(signs[0].lift>=120,'entry sign stands on the upper platform, clear of the ground flag and decorative cart');
 const c=createCanvas(900,600).getContext('2d');drawTownTaxi(c,m,0,400,1,0);assert.equal(c.getTransform().a,1);
}
const canvas=createCanvas(204,88),c=canvas.getContext('2d'),m={id:'village',width:1000,height:1000,groundY:800,platforms:[],ropes:[]};
drawMinimap(c,m,[{user_id:'self',mapId:'village',x:100,y:800},{user_id:'friend',mapId:'village',x:800,y:800},{user_id:'elsewhere',mapId:'forest',x:400,y:800}],[],{user_id:'self',mapId:'village',x:100,y:800},null,204,88,[{x:600,y:800},{x:600,y:800}]);
const data=c.getImageData(0,0,204,88).data,counts={};for(let i=0;i<data.length;i+=4){const rgb='#'+[data[i],data[i+1],data[i+2]].map(n=>n.toString(16).padStart(2,'0')).join('');counts[rgb]=(counts[rgb]||0)+1;}
assert.ok(counts[MINIMAP_COLORS.self]>=25);assert.equal(counts[MINIMAP_COLORS.player],16,'only the current-area remote player is shown');assert.ok(counts[MINIMAP_COLORS.npc]>10,'NPCs use a separate color and duplicate positions get separate lanes');assert.notEqual(MINIMAP_COLORS.player,MINIMAP_COLORS.npc);
console.log('PASS free taxi routes, locks/death/range/cooldown guards, job-independent unlocks, unchanged progress, map-filtered user/NPC colors and non-overlapping exploration signs');
