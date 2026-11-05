import {earnedPoints,allocatedPoints,traitGoals} from './adventure-traits.js';
import {STAGES,GRADES,stageOf,stageUnlocked} from './progression.js';
import {mentorOf} from './training-mentors.js';

// 지금 가장 도움이 되는 행동 하나만 제안한다. 로그인 직후 모달을 띄우지는 않는다.
export function adventureGoal(state,area){
 if(!state)return null;
 if(state.items.length>=190)return {action:'bag',title:'가방 정리',detail:`장비 ${state.items.length}/200 · 합성 또는 판매`};
 const free=earnedPoints(state,STAGES)-allocatedPoints(state.traits.allocated);
 if(free>0)return {action:'traits',title:`특성 포인트 ${free}개`,detail:'특성을 배분해 능력치를 높여보세요'};
 const goals=traitGoals(state,STAGES).filter(g=>g.area===area),ready=goals.find(g=>g.ready);
 if(ready)return {action:'mentor',title:'수련 보상 받기',detail:`${mentorOf(area).name} · ${ready.label}`};
 const next=Object.keys(STAGES).find(a=>stageOf(a).order===stageOf(area).order+1);
 if(next&&stageUnlocked(state,null,next))return {action:'taxi',title:`다음 지역 · ${STAGES[next].name}`,detail:'택시로 이동 · 더 좋은 사냥 보상'};
 const active=goals.find(g=>g.status==='active'&&!g.done);
 const left=20-(state.kills[area]||0)%20,tier=Math.min(4,stageOf(area).order);
 return {action:'hunt',title:`사냥 순환 · ${left}마리 남음`,detail:`${GRADES[tier]} 주무기 보장${active?' · 수련 '+active.current+'/'+active.target:''}`};
}

export function cooperativeRoster(players,self){
 if(!self)return [];
 return [...players].filter(p=>p.user_id!==self.user_id&&(p.mapId||'village')===(self.mapId||'village'))
 .sort((a,b)=>Number(b.dead)-Number(a.dead)||a.nickname.localeCompare(b.nickname)).slice(0,19)
 .map(p=>({id:p.user_id,name:p.nickname,dead:!!p.dead,hp:Math.max(0,Math.min(p.max||100,p.hp||0)),max:p.max||100}));
}
