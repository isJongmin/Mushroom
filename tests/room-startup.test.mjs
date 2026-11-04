import {withBody,avatarBody,BODY_PRESETS} from '../src/client/avatar-body.js';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {adventureProgress} from '../src/client/game/adventure-level.js';

const source=readFileSync(new URL('../src/client/screens/room.js',import.meta.url),'utf8');
const start=source.lastIndexOf('  (async () => {');
const bootstrap=source.slice(start,source.indexOf('  })();',start)+7);
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
const tick=()=>new Promise(r=>setImmediate(r));
function fixture(){
 const map=deferred(),player=deferred(),requests=[],calls=[];
 const assets={sanitizeAvatar:a=>a};
 const c=vm.createContext({withBody,adventureProgress,presentedLevel:1,alive:true,assets:null,avatarR:null,villageMap:null,map:null,
  platforms:[],ropes:[],world:null,camRef:0,me:null,raf:null,taxiAvatar:null,
  app:{assets:Promise.resolve(assets),mapAssets:map.promise,profileKey:'qa',userId:'qa'},
  profile:{avatar:{id:'player'},body:BODY_PRESETS[3].values},roomId:'room',myNick:'Qa',NICK_RE:/^Qa$/,
  createAvatarRenderer:()=>({ready:a=>{requests.push(a);return a.id==='player'?player.promise:new Promise(()=>{});}}),
  costumeAvatar:(a,costume)=>({...a,costume}),equippedCostume:()=> 'earned-costume',
  AREA_IDS:['village','quarry','forest','frost'],currentArea:'village',areaCatalog:new Map(),
  areaMap:()=>({groundY:800,spawns:[]}),normalizePlatforms:()=>[],normalizeRopes:()=>[],
  BODY_OPT:{},worldFromMap:m=>m,computeLayout(){},TAXI_DRIVER:{avatar:{id:'taxi'}},
  regionNpcs:new Map(),npcRoster:area=>({quest:{avatar:{id:area+'-quest'}},pet:{avatar:{id:area+'-pet'}}}),
  mentorOf:area=>({avatar:{id:area+'-mentor'}}),funNpcOf:area=>({avatar:{id:area+'-fun'}}),
  syncNpcLook(){},spawnPoint:()=>({x:900,y:800}),
  makePlayer:(uid,nick,avatar)=>({user_id:uid,avatar,costume:'earned-costume'}),createBody:()=>({}),
  progress:null,progressError:'',chatLog:{addSystem(){}},players:new Map(),updateCount(){},
  announceArea:()=>calls.push('announce'),requestAnimationFrame:()=>{calls.push('frame');return 1;},
  frame(){},firstJoin:()=>calls.push('join'),setConnection:s=>calls.push(s)});
 return {c,map,player,requests,calls};
}
const f=fixture(),run=vm.runInContext(bootstrap,f.c);
await tick();
assert.equal(f.requests.length,1,'player download begins before the map finishes');
assert.deepEqual(avatarBody(f.requests[0]),BODY_PRESETS[3].values,'selected proportions are preloaded before entering');
assert.equal(f.requests[0].costume,'earned-costume','equipped costume is preloaded too');
assert.deepEqual(f.calls,[]);
f.map.resolve({});await tick();
assert.deepEqual(f.calls,[],'entry still waits for the player outfit');
f.player.resolve();await run;
assert.deepEqual(f.calls,['announce','frame','join']);
assert.equal(f.requests.length,1,'taxi and all sixteen NPC outfits do not block entry');
assert.equal(f.c.regionNpcs.size,4,'regional appearance data remains available');
const cancelled=fixture(),closed=vm.runInContext(bootstrap,cancelled.c);
await tick();cancelled.c.alive=false;cancelled.map.resolve({});cancelled.player.resolve();await closed;
assert.deepEqual(cancelled.calls,[],'leaving during loading does not start an abandoned room');
console.log('PASS player/map overlap, equipped costume, deferred NPCs and cancelled startup');
