// All actors share a foot-plane. Elevated platforms stay behind lower actors;
// on the same plane, props/NPCs precede mobs, players and companions.
const rank={npc:0,mob:1,player:2,pet:3};
export function sortSceneActors(actors){return [...actors].sort((a,b)=>a.y-b.y||(rank[a.kind]??0)-(rank[b.kind]??0)||String(a.id).localeCompare(String(b.id)));}
export function createCompanionFollower(){
 let pose=null;
 return {reset(){pose=null;},sample({id,mapId,x,y,dir=1,target=null,now=0,distance=48,response=12}){
  if(!id||!Number.isFinite(x)||!Number.isFinite(y)){pose=null;return null;}
  const tx=target?.x??x-dir*distance,ty=target?.y??y;
  if(!pose||pose.id!==id||pose.mapId!==mapId||!Number.isFinite(pose.x)||!Number.isFinite(pose.y)||Math.abs(pose.x-tx)>400||Math.abs(pose.y-ty)>240)pose={id,mapId,x:tx,y:ty,now};
  else{const dt=Math.max(0,Math.min(.1,(now-pose.now)/1000)),f=1-Math.exp(-response*dt);pose.x+=(tx-pose.x)*f;pose.y+=(ty-pose.y)*f;pose.now=now;}
  return {...pose};
 }};
}

// Individual follow distances/lag let pets bunch up naturally. Only prevent
// total stacking; 18px center spacing intentionally allows slight sprite overlap.
export const COMPANION_MIN_GAP=18;
export const COMPANION_FOLLOW_DISTANCES=Object.freeze({idle:[30,48,66],moving:[38,66,94]});
export function createCompanionGroup(){
 const followers=new Map();
 return {reset(){followers.clear();},sample({ids=[],mapId,x,y,dir=1,moving=false,target=null,now=0,minX=-Infinity,maxX=Infinity}){
  const pets=[...new Set(ids.filter(id=>typeof id==='string'&&id))].slice(0,3);
  for(const id of followers.keys())if(!pets.includes(id))followers.delete(id);
  if(!Number.isFinite(x)||!Number.isFinite(y)){followers.clear();return [];}
  const poses=pets.map((id,slot)=>{
   let follower=followers.get(id);if(!follower){follower=createCompanionFollower();followers.set(id,follower);}
   const destination=target?{x:target.x-dir*slot*COMPANION_MIN_GAP,y:target.y}:null;
   return {...follower.sample({id,mapId,x,y,dir,target:destination,now,distance:COMPANION_FOLLOW_DISTANCES[moving?'moving':'idle'][slot],response:[11,8.5,6.5][slot]}),slot};
  });
  const sorted=[...poses].sort((a,b)=>a.x-b.x||a.slot-b.slot);
  for(let i=0;i<sorted.length;i++){sorted[i].x=Math.max(minX+i*COMPANION_MIN_GAP,Math.min(maxX-(sorted.length-1-i)*COMPANION_MIN_GAP,sorted[i].x));if(i)sorted[i].x=Math.max(sorted[i].x,sorted[i-1].x+COMPANION_MIN_GAP);}
  return poses;
 }};
}
