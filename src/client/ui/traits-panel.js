import {h} from '../dom.js';
import {openModal} from './modal.js';
import {TRAITS,allocatedPoints,earnedPoints,traitGoals,emptyAllocation} from '../game/adventure-traits.js';
import {STAGES,loadout,combatStats} from '../game/progression.js';
import {abilityStats} from '../game/jobs.js';
const SPECIES_NAMES={'snail':'달팽이','mushroom':'버섯','slime':'슬라임','wild-stump':'숲 그루터기','armored-mushroom':'철갑 버섯','bat':'박쥐','crystal-crab':'수정 게','golem':'골렘','ore-beetle':'광석 딱정벌레','cave-sentinel':'광산 파수꾼','moss-slime':'이끼 슬라임','forest-stump':'숲 그루터기','moss-guardian':'이끼 수호자','thorn-mantis':'가시 사마귀','ancient-treant':'고대 나무정령','frost-slime':'서리 슬라임','ice-crab':'빙정 게','ice-golem':'얼음 골렘','frost-beetle':'서리 딱정벌레','glacier-sentinel':'빙하 파수꾼'};
export function createTraitsPanel({main,store,getArea,getEditReason,onChange,onFocus}){
 let modal=null,draft=emptyAllocation(),revision=0,busy=false,notice='',area='village',renderAc=null,destroyed=false;
 const body=h('div',{class:'traits-panel'});
 function button(text,fn,{disabled=false,id}={}){const b=h('button',{type:'button',class:'gp-button',disabled,testid:id,'data-focus':id||text},text);b.addEventListener('click',fn,{signal:renderAc.signal});return b;}
 const changed=()=>TRAITS.some(t=>draft[t.id]!==store.state.traits.allocated[t.id]);
 function status(){if(!modal?.open)return;const reason=getEditReason();const hint=body.querySelector('[data-testid="traits-lock"]');if(hint)hint.textContent=reason||'무료 변경 가능 · 적용해도 현재 체력은 회복되지 않아요.';const apply=body.querySelector('[data-testid="traits-apply"]');if(apply)apply.disabled=busy||!!reason||!changed();}
 async function save(){
  if(busy||destroyed)return;const reason=getEditReason();if(reason){notice=reason;paint();return;}
  busy=true;notice='';paint();
  try{await store.run({type:'traits-allocate',allocated:{...draft},expectedRevision:revision});if(destroyed)return;notice='특성을 저장했어요.';onChange();}
  catch(e){notice=e.message;}
  finally{busy=false;draft={...store.state.traits.allocated};revision=store.state.revision;if(modal?.open&&!destroyed)paint();}
 }
 function paint(){
  const focused=body.contains(document.activeElement)?document.activeElement?.getAttribute('data-focus'):null,scroll=modal?.section.scrollTop;
  renderAc?.abort();renderAc=new AbortController();body.replaceChildren();const s=store.state,earned=earnedPoints(s,STAGES),used=allocatedPoints(draft),current=loadout(s),before=combatStats(current),after=combatStats({...current,traits:draft});
  body.append(h('header',{class:'gp-header'},h('div',{},h('p',{class:'gp-eyebrow'},'ADVENTURE TRAITS'),h('h2',{id:'traits-title'},'모험 특성')),button('닫기',close,{disabled:busy,id:'traits-close'})),h('div',{class:'traits-points',role:'status',testid:'traits-points'},h('strong',{},`사용 가능 ${earned-used}점`),h('span',{},`획득 ${earned} / 15 · 배분 ${used}점`)));
  if(notice)body.append(h('p',{class:'gp-notice',role:'status'},notice));
  const cards=h('div',{class:'traits-cards'});
  for(const t of TRAITS){const value=draft[t.id];cards.append(h('section',{class:'trait-card','aria-label':t.name},h('h3',{},t.name),h('p',{},t.description),h('strong',{class:'trait-effect'},`${t.id==='technique'?'−':'+'}${value*t.step}%`),h('div',{class:'trait-controls'},button('−',()=>{draft[t.id]--;paint();},{disabled:busy||!value,id:'trait-minus-'+t.id}),h('span',{'aria-live':'polite'},`${value} / 10`),button('+',()=>{draft[t.id]++;paint();},{disabled:busy||value>=10||used>=earned,id:'trait-plus-'+t.id}))));}
  const cooldown=traits=>[1,2,3].map(slot=>abilityStats(current.job,slot,{...current,traits}).cooldown+'초').join(' / ');
  body.append(cards,h('section',{class:'traits-preview',testid:'traits-preview','aria-label':'적용 전후 능력치'},h('p',{},`공격력 ${before.attack} → ${after.attack}`),h('p',{},`최대 체력 ${before.maxHp} → ${after.maxHp}`),h('p',{},`스킬 재사용 ${cooldown(current.traits)} → ${cooldown(draft)}`)),h('p',{class:'gp-muted'},'기본 공격 간격은 그대로예요. 무기를 바꿔도 특성은 유지돼요.'),h('div',{class:'gp-actions'},button('무료 초기화 미리보기',()=>{draft=emptyAllocation();paint();},{disabled:busy||!used,id:'traits-reset'}),button(busy?'저장 중…':'적용',save,{disabled:busy,id:'traits-apply'})),h('p',{class:'traits-lock',testid:'traits-lock',role:'status'},getEditReason()||'무료 변경 가능 · 적용해도 현재 체력은 회복되지 않아요.'));
  const goals=traitGoals(s,STAGES),next=goals.find(g=>!g.done&&g.area===area)||goals.find(g=>!g.done);
  body.append(h('h3',{},'포인트 획득 여정'),h('p',{class:'gp-muted',testid:'traits-next'},next?`다음 목표: ${STAGES[next.area].name} · ${next.label} (${next.current}/${next.target})`:'15포인트를 모두 획득했어요.'));
  body.append(h('div',{class:'traits-regions','aria-label':'지역별 획득 조건'},...Object.entries(STAGES).map(([id,st])=>{const b=button(`${st.name} ${goals.filter(g=>g.area===id&&g.done).length}/${id==='village'?3:4}`,()=>{area=id;paint();},{disabled:busy,id:'traits-region-'+id});b.setAttribute('aria-pressed',String(area===id));return b;})));
  for(const g of goals.filter(g=>g.area===area)){
   const row=h('section',{class:'trait-goal'+(g.done?' is-complete':''),testid:g.key},h('div',{},h('strong',{},g.label),h('span',{},g.done?'완료 · +1점':`${g.current} / ${g.target} · +1점`)),h('progress',{max:g.target,value:g.current,'aria-label':g.label}));
   if(g.key.includes('species'))row.append(h('ul',{class:'trait-species'},...Object.keys(STAGES[area].mobs).map(k=>h('li',{},`${SPECIES_NAMES[k]||k} ${s.traits.species[area][k].length}/${area==='village'?10:20}`))));
   else if(g.key.includes('explore'))row.append(h('p',{},[['entry','입구'],['upper','위층'],['depth','깊은 곳']].map(([id,name])=>`${name} ${s.traits.explored[area].includes(id)?'발견':'미발견'}`).join(' · ')));
   body.append(row);
  }
  body.append(h('p',{class:'gp-muted'},'각 조건은 최초 1회만 지급해요. 처치 참여가 인정되며 반복 사냥 의뢰에는 포인트가 추가되지 않아요.'));
  if(focused)[...body.querySelectorAll('[data-focus]')].find(b=>b.getAttribute('data-focus')===focused&&!b.disabled)?.focus({preventScroll:true});
  if(scroll!=null&&modal?.open)modal.section.scrollTop=scroll;status();
 }
 function close(){if(busy)return;renderAc?.abort();modal?.close();modal=null;onFocus();}
 return {open(){if(destroyed||busy)return;draft={...store.state.traits.allocated};revision=store.state.revision;area=getArea();notice='';paint();modal=openModal({main,titleId:'traits-title',testid:'traits-panel',children:[body],onCancel:close,canEscape:()=>!busy,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal','traits-modal');status();},refresh(){if(!modal?.open||busy)return;if(revision!==store.state.revision){notice=changed()?'진행도가 갱신되어 저장된 배분을 불러왔어요.':'';draft={...store.state.traits.allocated};revision=store.state.revision;paint();}else status();},destroy(){destroyed=true;renderAc?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
