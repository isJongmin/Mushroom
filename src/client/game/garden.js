import {cleanBoss,advanceBoss,bossMaxHp} from './garden-boss.js';
// Host-owned, serializable cooperative encounter. No timers or browser dependencies.
export const GARDEN_TITLE = 'sprout-guardian';
export const GARDEN_LABEL = '새싹 수호자';
export const gardenPoint = world => ({ x: world.spawn?.x ?? world.width / 2, y: world.groundY });
export function gardenZones(zones, world, area) {
  if (area !== 'village') return zones;
  const p = gardenPoint(world);
  return [...zones, { i: zones.length, id: 'garden-event', event: true, x1: p.x - 680, x2: p.x + 680, y: p.y, max: 12, mobs: ['mushroom', 'slime'] },{i:zones.length+1,id:'garden-boss',event:true,boss:true,x1:p.x-420,x2:p.x+940,y:p.y,max:1,mobs:['garden-king']}];
}
const states = new Set(['ready','wave','rest','success','failed','boss']);
const int = (x,a,b) => Number.isInteger(x) && x>=a && x<=b;
export function cleanGarden(s) {
  if (!s || typeof s.id!=='string' || !/^[a-z0-9-]{1,64}$/i.test(s.id) || !states.has(s.phase)) return null;
  if (!int(s.rev,0,1e9) || !int(s.wave,0,3) || !int(s.hp,0,100) || !int(s.kills,0,100) || !int(s.spawned,0,100)) return null;
  if (!int(s.started,0,9e15) || !int(s.deadline,0,9e15) || !int(s.ended,0,9e15)) return null;
  if(s.phase==='success'&&(s.wave!==3||s.hp===0) || s.phase==='ready'&&s.wave!==0 || s.phase==='wave'&&s.wave===0 || s.phase==='rest'&&(s.wave<1||s.wave>2))return null;
  if (!Array.isArray(s.members) || s.members.length>20) return null;
  const members=[];
  for (const m of s.members) {
    if (!m || typeof m.uid!=='string' || !m.uid || m.uid.length>64 || members.some(x=>x.uid===m.uid) || !int(m.damage,0,1e7) || !int(m.kills,0,100)) return null;
    members.push({uid:m.uid,damage:m.damage,kills:m.kills,bossDamage:int(m.bossDamage,0,1e7)?m.bossDamage:0,job:['warrior','archer','mage','thief'].includes(m.job)?m.job:'warrior'});
  }
  const boss=s.boss?cleanBoss(s.boss):null;if(s.phase==='boss'&&!boss)return null;
  return {mode:s.mode==='boss'?'boss':'defense',boss,id:s.id,rev:s.rev,phase:s.phase,wave:s.wave,hp:s.hp,kills:s.kills,spawned:s.spawned,started:s.started,deadline:s.deadline,ended:s.ended,members};
}
export const gardenActive = s => !!s && ['ready','wave','rest','boss'].includes(s.phase);
export const gardenEligible = (s,uid) => s?.phase==='success' && s.members.some(m=>m.uid===uid && m.damage>0);
export function createGarden() {
  let state=null;
  const copy=()=>state?structuredClone(state):null;
  function start(id,now,uids,mode='defense') {
    if (gardenActive(state) || state && now-state.ended<5000) return false;
    state={mode:mode==='boss'?'boss':'defense',boss:null,id,rev:1,phase:'ready',wave:0,hp:100,kills:0,spawned:0,started:now,deadline:now+5000,ended:0,members:[...new Set(uids)].slice(0,20).map(uid=>({uid,damage:0,kills:0,bossDamage:0,job:'warrior'}))};
    return true;
  }
  function record(uid,damage,killed,job='warrior',boss=false) {
    if (!['wave','boss'].includes(state?.phase)||typeof uid!=='string'||!uid||uid.length>64) return;
    let m=state.members.find(m=>m.uid===uid);
    if(!m && state.members.length<20){m={uid,damage:0,kills:0,bossDamage:0,job:'warrior'};state.members.push(m);}
    if(!m)return;
    m.job=job;if(boss)m.bossDamage=Math.min(1e7,m.bossDamage+Math.round(damage));
    m.damage=Math.min(1e7,m.damage+Math.max(0,Math.round(damage)));
    if(killed){m.kills++;state.kills++;} state.rev++;
  }
  function tick(now,{alive=0,breaches=0,players=1,spawn=()=>0,spawnBoss=()=>false,bossAlive=true,targetX=0,clear=()=>{}}={}) {
    if(!gardenActive(state))return;
    const finish=phase=>{state.phase=phase;state.ended=now;state.deadline=now+5000;state.rev++;clear();};
    if(breaches){state.hp=Math.max(0,state.hp-breaches*20);state.rev++;}
    if(state.hp===0 || players===0){finish('failed');return;}
    if(state.phase==='boss'){
      if(!bossAlive){state.wave=3;finish('success');return;}
      if(now>=state.deadline){finish('failed');return;}
      const next=advanceBoss(state.boss,now,targetX);if(next!==state.boss){state.boss=next;state.rev++;}return;
    }
    if(state.phase==='ready'&&state.mode==='boss'&&now>=state.deadline){
      const max=bossMaxHp(players);if(!spawnBoss(max)){state.deadline=now+1000;return;}
      state.phase='boss';state.wave=1;state.boss={pattern:'stomp',seq:1,at:now,targetX,max};state.deadline=now+150000;state.rev++;return;
    }
    if(state.phase==='wave') {
      if(alive===0){if(state.wave===3)finish('success');else {state.phase='rest';state.deadline=now+4000;state.rev++;}}
      else if(now>=state.deadline)finish('failed');
    } else if(now>=state.deadline) {
      const count=Math.min(12,3+state.wave+Math.min(4,Math.max(0,players-1))*2);
      const n=spawn(count,state.wave+1);
      // Crowded spawn positions retry without silently completing a wave.
      if(n===0){state.deadline=now+1000;return;}
      state.wave++;state.spawned+=n;state.phase='wave';state.deadline=now+40000;state.rev++;
    }
  }
  return {start,record,tick,snapshot:copy,load(s){state=cleanGarden(s);},accept(s){const next=cleanGarden(s);if(!next)return false;if(state && (next.started<state.started || next.id===state.id&&next.rev<state.rev))return false;state=next;return true;},clear(){state=null;}};
}
