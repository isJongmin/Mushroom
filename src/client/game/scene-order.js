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
