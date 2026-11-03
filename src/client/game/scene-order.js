// All actors share a foot-plane. Elevated platforms stay behind lower actors;
// on the same plane, props/NPCs precede mobs, players and companions.
const rank={npc:0,mob:1,player:2,pet:3};
export function sortSceneActors(actors){return [...actors].sort((a,b)=>a.y-b.y||(rank[a.kind]??0)-(rank[b.kind]??0)||String(a.id).localeCompare(String(b.id)));}
export function createCompanionFollower(){
 let pose=null;
 return {reset(){pose=null;},sample({id,mapId,x,y,dir=1,target=null,now=0}){
  if(!id||!Number.isFinite(x)||!Number.isFinite(y)){pose=null;return null;}
  const tx=target?.x??x-dir*48,ty=target?.y??y;
  if(!pose||pose.id!==id||pose.mapId!==mapId||!Number.isFinite(pose.x)||!Number.isFinite(pose.y)||Math.abs(pose.x-tx)>400||Math.abs(pose.y-ty)>240)pose={id,mapId,x:tx,y:ty,now};
  else{const dt=Math.max(0,Math.min(.1,(now-pose.now)/1000)),f=1-Math.exp(-12*dt);pose.x+=(tx-pose.x)*f;pose.y+=(ty-pose.y)*f;pose.now=now;}
  return {...pose};
 }};
}

// A shared smooth center and fixed world-order slots never cross on turns or
// converge on the same loot. 64 world pixels clear even the widest .8-scale pet.
export const COMPANION_GAP=64;
export function createCompanionGroup(){
 const follower=createCompanionFollower();
 return {reset(){follower.reset();},sample({ids=[],mapId,x,y,dir=1,target=null,now=0,minX=-Infinity,maxX=Infinity}){
  const pets=[...new Set(ids.filter(id=>typeof id==='string'&&id))].slice(0,3);
  if(!pets.length){follower.reset();return [];}
  const half=(pets.length-1)*COMPANION_GAP/2;
  const anchor=follower.sample({id:pets.join('|'),mapId,x,y,dir,now,target:{x:target?.x??x-dir*(48+half),y:target?.y??y}});
  if(!anchor)return [];
  const center=Math.max(minX+half,Math.min(maxX-half,anchor.x));
  return pets.map((id,slot)=>({...anchor,id,slot,x:center+(slot-(pets.length-1)/2)*COMPANION_GAP}));
 }};
}
