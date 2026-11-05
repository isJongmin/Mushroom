import {adventureProgress,AREA_XP} from './adventure-level.js';
import {traitGoals,earnedPoints,allocatedPoints} from './adventure-traits.js';
import {STAGES,GRADES,stageOf,stageUnlocked,activeWeapon,tierOK,ITEM_NAMES} from './progression.js';
import {huntContract} from './hunt-chain.js';
import {chapterOf,journeyObjective} from './journey.js';

export function journeySummary(state,area='village') {
  if(!state)return null;
  const id=Object.hasOwn(STAGES,area)?area:'village',stage=stageOf(id);
  const kills=state.kills[id]||0,current=kills%20,weapon=activeWeapon(state),next=Object.keys(STAGES).find(a=>STAGES[a].order===stage.order+1);
  const contract=huntContract(id,stage.order,20,weapon?.kind||'sword');
  const level=adventureProgress(state),goals=traitGoals(state,STAGES).filter(g=>g.area===id);
  return {area:id,kills,chapter:chapterOf(id),goal:journeyObjective(state,id),level,
    contract:{current,target:20,remaining:20-current,completed:Math.floor(kills/20),reward:`${GRADES[contract.item.tier]} ${ITEM_NAMES[contract.item.kind]} + ${contract.gold.toLocaleString()} G`},
    levelHint:level.capped?'최고 레벨 달성':`Lv.${level.level+1}까지 약 ${Math.ceil((level.needed-level.current)/AREA_XP[id])}마리 · 공격력 +1% · 최대 HP +3`,
    skillHint:level.level<5?'모험 레벨 5에 두 번째 스킬 해금':level.level<12?'모험 레벨 12에 궁극기 해금':'모든 스킬 단계 해금',
    freePoints:earnedPoints(state,STAGES)-allocatedPoints(state.traits.allocated),
    goals,next:next?{id:next,name:STAGES[next].name,unlocked:stageUnlocked(state,null,next),requirement:`${STAGES[id].name} 보스 첫 처치`}:null};
}

export function journalChapters(state){
  if(!state)return [];
  return Object.keys(STAGES).map(area=>{
    const summary=journeySummary(state,area);
    return {...summary,name:STAGES[area].name,unlocked:stageUnlocked(state,null,area),claimed:summary.goals.filter(g=>g.claimed).length};
  });
}

export const journeyActionLabel=goal=>({mentor:'스승에게 길 안내',traits:'특성 확인',bag:'가방 정리',taxi:'택시로 길 안내',event:'도전 장소로 안내',explore:'탐험 길 안내',hunt:'사냥터 길 안내'}[goal?.action]||'여정 확인');

// Show an upgrade only when the actual collected item improves the active weapon of the same kind.
export function equipmentUpgrade(state,item){
  const current=activeWeapon(state);
  if(!current||!item||item.kind!==current.kind||!tierOK(item.tier)||item.tier<=current.tier)return null;
  return {title:`${GRADES[item.tier]} ${ITEM_NAMES[item.kind]} 획득`,detail:`${GRADES[current.tier]} → ${GRADES[item.tier]} · 가방에서 비교하고 장착하세요`};
}
