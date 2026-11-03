export const SPECIES_NAMES={'snail':'달팽이','mushroom':'버섯','slime':'슬라임','wild-stump':'숲 그루터기','armored-mushroom':'철갑 버섯','bat':'박쥐','crystal-crab':'수정 게','golem':'골렘','ore-beetle':'광석 딱정벌레','cave-sentinel':'광산 파수꾼','moss-slime':'이끼 슬라임','forest-stump':'숲 그루터기','moss-guardian':'이끼 수호자','thorn-mantis':'가시 사마귀','ancient-treant':'고대 나무정령','frost-slime':'서리 슬라임','ice-crab':'빙정 게','ice-golem':'얼음 골렘','frost-beetle':'서리 딱정벌레','glacier-sentinel':'빙하 파수꾼'};
// Persist evidence, derive awards; an arbitrary earned/completed number is never accepted.
export const TRAITS = Object.freeze([
 {id:'attack',name:'전투 숙련',step:5,unit:'공격력',description:'펫 적용 후 공격력에 포인트당 +5%'},
 {id:'health',name:'강인한 신체',step:5,unit:'최대 체력',description:'펫 적용 후 최대 체력에 포인트당 +5%'},
 {id:'technique',name:'기술 연마',step:2,unit:'스킬 쿨타임',description:'공격 스킬과 궁극기 쿨타임에 포인트당 −2%'},
]);
export const TRAIT_LIMIT=10, POINT_LIMIT=15;
export const emptyAllocation=()=>({attack:0,health:0,technique:0});
export const allocatedPoints=a=>TRAITS.reduce((n,t)=>n+(a?.[t.id]||0),0);
export function allocationOK(a,earned=POINT_LIMIT){return !!a&&typeof a==='object'&&Object.keys(a).length===3&&TRAITS.every(t=>Object.hasOwn(a,t.id)&&Number.isInteger(a[t.id])&&a[t.id]>=0&&a[t.id]<=TRAIT_LIMIT)&&allocatedPoints(a)<=earned;}
export function cleanAllocation(a,earned=POINT_LIMIT){return allocationOK(a,earned)?{attack:a.attack,health:a.health,technique:a.technique}:emptyAllocation();}
export function explorationPoints(map){
 if(!map||map.id==='village')return [];
 const upper=(map.platforms||[]).find(p=>p.id===(map.id==='forest'?'ancient-bough':'mine-lift'));
 return [{id:'entry',name:'입구',x:650,y:map.groundY},...(upper?[{id:'upper',name:'위층',x:(upper.x1+upper.x2)/2,y:upper.y}]:[]),{id:'depth',name:'깊은 곳',x:map.width-550,y:map.groundY}];
}
export function traitGoals(s,stages){
 return Object.entries(stages).flatMap(([area,stage])=>{
  const t=s.traits,threshold=area==='village'?10:20,species=Object.keys(stage.mobs),done=t?.events?.[area]||{};
  const row=(suffix,label,current,target,detail='')=>{const key=area+':'+suffix,status=t?.quests?.[key]||'available',done=current>=target;return {key,area,label,current:Math.min(target,current),target,done,detail,status,claimed:status==='claimed',ready:status==='active'&&done};};
  return [area==='village'?row('hunt20','첫 사냥 의뢰',s.kills?.village||0,20):row('explore3','탐험 지점 3곳',t?.explored?.[area]?.length||0,3,'입구 · 위층 · 깊은 곳'),
   row('species'+threshold,`몬스터 5종 각각 ${threshold}마리`,species.reduce((n,k)=>n+Math.min(threshold,t?.species?.[area]?.[k]?.length||0),0),species.length*threshold,species.map(k=>`${k} ${t?.species?.[area]?.[k]?.length||0}/${threshold}`).join(' · ')),
   ...(area==='village'?[]:[row('defense-first','방어 첫 성공',done.defense?1:0,1)]),row('boss-first','보스 첫 처치',done.boss?1:0,1)];
 });
}
export const earnedPoints=(s,stages)=>traitGoals(s,stages).filter(g=>g.done&&(s.traits?.questVersion!==1||g.claimed)).length;
export function cleanTraits(raw,kills,stages){
 const t={questVersion:1,legacyRewardsMigrated:raw?.legacyRewardsMigrated===true,quests:{},allocated:emptyAllocation(),species:{},explored:{},events:{}};
 for(const [area,stage]of Object.entries(stages)){
  t.species[area]={};const threshold=area==='village'?10:20;
  for(const kind of Object.keys(stage.mobs))t.species[area][kind]=[...new Set((Array.isArray(raw?.species?.[area]?.[kind])?raw.species[area][kind]:[]).filter(r=>typeof r==='string'&&r.length>0&&r.length<=150))].slice(0,threshold);
  t.explored[area]=area==='village'?[]:[...new Set((Array.isArray(raw?.explored?.[area])?raw.explored[area]:[]).filter(id=>['entry','upper','depth'].includes(id)))];
  t.events[area]={boss:raw?.events?.[area]?.boss===true,defense:area!=='village'&&raw?.events?.[area]?.defense===true};
 }
 for(const g of traitGoals({kills,traits:t},stages)){const state=raw?.quests?.[g.key];if(raw?.questVersion!==1&&g.done)t.quests[g.key]='claimed';else if(state==='active'||state==='claimed'&&g.done)t.quests[g.key]=state;}
 t.allocated=cleanAllocation(raw?.allocated,earnedPoints({kills,traits:t},stages));return t;
}
export function traitEditReason({connected,alive,near,now,lastAttack=-Infinity,lastHit=-Infinity}){
 if(!connected)return '연결된 상태에서 변경할 수 있어요.';
 if(!alive)return '생존 중에 변경할 수 있어요.';
 if(!near)return '수련 스승 가까이에서 변경할 수 있어요.';
 if(now-Math.max(lastAttack,lastHit)<5000)return '공격·피격 후 5초가 지나야 변경할 수 있어요.';
 return '';
}
export function drawExplorationPoints(ctx,map,camX,camY,k,visited=[]){
 ctx.save();for(const p of explorationPoints(map)){
  const x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-100||x>ctx.canvas.width+100)continue;
  const done=visited.includes(p.id);ctx.fillStyle=done?'#789f86':'#f1d176';ctx.fillRect(x-2*k,y-62*k,4*k,62*k);ctx.fillRect(x+2*k,y-62*k,22*k,14*k);
  ctx.font=`600 ${11*k}px system-ui`;ctx.textAlign='center';ctx.strokeStyle='#243c37';ctx.lineWidth=3*k;ctx.fillStyle=done?'#d7e7d9':'#fff1bf';const label=`${p.name} · ${done?'발견':'탐험'}`;ctx.strokeText(label,x,y-74*k);ctx.fillText(label,x,y-74*k);
 }ctx.restore();
}
