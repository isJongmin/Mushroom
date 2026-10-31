import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createAvatarRenderer} from '../src/client/avatar.js';
import {drawCostume} from '../src/client/game/reward-costumes.js';
import {NPC_AVATAR,drawQuestNpc} from '../src/client/game/quest-npc.js';
import {recordingContext} from './normal-skill-visuals.test.mjs';
// A cape cannot paint an extra collar/bib on the front. Rear cloth still paints.
for(const id of ['sprout-cape','bloom-cape'])for(const side of [false,true])for(const left of [false,true]){
 const rec=recordingContext();drawCostume(rec.context,id,100,200,2,{side,left});rec.balanced();
 assert.equal(rec.commands.filter(c=>['fill','fillRect','stroke'].includes(c[0])).length,0,'front torso must remain uncovered');
 const rear=recordingContext();drawCostume(rear.context,id,100,200,2,{rear:true,side:false});rear.balanced();assert.ok(rear.commands.some(c=>c[0]==='fill'));
}
// Rope rendering must not paint skin/sleeves over the back-of-head/neck.
const oldCanvas=globalThis.OffscreenCanvas;
class CanvasStub{constructor(w,h){this.width=w;this.height=h;this.rec=recordingContext();}getContext(){return this.rec.context;}}
globalThis.OffscreenCanvas=CanvasStub;
try{
 const assets={source:'manifest',frame:{w:144,h:192},anchor:{x:72,y:180},density:1.5,frameCount:13,frameIndex:{back:7},animations:{idle:{frames:[2],ms:600}},layerOrder:[{part:'skin',layer:'skin',blend:'source-over'}],hasLayer:()=>true,getLayer:async()=>({naturalWidth:144*13})};
 const r=createAvatarRenderer(assets);await r.ready(NPC_AVATAR);
 for(const moving of [true,false])for(const now of [0,110,220,440]){
  const rec=recordingContext();assert.ok(r.drawClimb(rec.context,NPC_AVATAR,100,200,2,now,moving));rec.balanced();
  assert.ok(rec.commands.some(c=>c[0]==='drawImage'));assert.equal(rec.commands.some(c=>c[0]==='fillRect'||c[0]==='fill'),false);
 }
 r.clear();
}finally{if(oldCanvas===undefined)delete globalThis.OffscreenCanvas;else globalThis.OffscreenCanvas=oldCanvas;}
const manifest=JSON.parse(readFileSync(new URL('../assets/avatar/manifest.json',import.meta.url)));
for(const [part,id]of Object.entries(NPC_AVATAR))assert.ok(manifest.parts[part].some(p=>p.id===id),`NPC ${part} uses a real avatar asset`);
let count=0;const rec=recordingContext();drawQuestNpc(rec.context,{x:100,y:200},0,0,2,{avatar:NPC_AVATAR,now:650,renderer:{frameAt:(anim,time)=>{assert.equal(anim,'idle_front');assert.equal(time,650);return 1;},draw:(c,av,x,y,k,frame,left)=>{count++;assert.deepEqual(av,NPC_AVATAR);assert.equal(frame,1);assert.equal(left,false);}}});rec.balanced();assert.equal(count,1);
console.log('PASS invisible rope hands, rear-only cape cloth, shared detailed NPC assets and breathing renderer');
