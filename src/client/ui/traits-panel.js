import {h} from '../dom.js';
import {openModal} from './modal.js';
import {TRAITS,allocatedPoints,earnedPoints,traitGoals,emptyAllocation,SPECIES_NAMES} from '../game/adventure-traits.js';
import {STAGES,loadout,combatStats} from '../game/progression.js';
import {mentorOf} from '../game/training-mentors.js';
import {abilityStats} from '../game/jobs.js';
const TABS=[['allocation','능력 배분'],['goals','수련 퀘스트']];
const LABELS={attack:'공격력',health:'최대 체력',technique:'스킬 재사용'};
function traitIcon(id){
 const cv=h('canvas',{width:40,height:40,'aria-hidden':true}),c=cv.getContext('2d');c.strokeStyle=id==='health'?'#b8656d':id==='attack'?'#bd8543':'#57858a';c.fillStyle=c.strokeStyle;c.lineWidth=2.8;c.lineCap='round';c.lineJoin='round';
 if(id==='attack'){c.beginPath();c.moveTo(12,29);c.lineTo(28,13);c.lineTo(29,8);c.lineTo(24,9);c.lineTo(9,25);c.stroke();c.beginPath();c.moveTo(8,22);c.lineTo(18,32);c.moveTo(10,29);c.lineTo(6,33);c.stroke();}
 else if(id==='health'){c.beginPath();c.moveTo(20,32);c.bezierCurveTo(2,21,5,9,13,10);c.bezierCurveTo(17,10,19,13,20,15);c.bezierCurveTo(23,8,33,8,34,16);c.bezierCurveTo(35,22,27,29,20,32);c.stroke();}
 else{c.beginPath();c.arc(20,21,12,0,Math.PI*2);c.moveTo(20,13);c.lineTo(20,22);c.lineTo(26,25);c.moveTo(16,5);c.lineTo(24,5);c.stroke();}return cv;
}
export function createTraitsPanel({main,store,getArea,getEditReason,onChange,onFocus,onTalk=()=>{},getTalkReason=()=>''}){
 let modal=null,draft=emptyAllocation(),revision=0,busy=false,notice='',area='village',tab='allocation',renderAc=null,destroyed=false;
 const body=h('div',{class:'traits-panel traits-v2'});
 function button(text,fn,{disabled=false,id,label,title}={}){const b=h('button',{type:'button',class:'gp-button',disabled,testid:id,'data-focus':id||text,'aria-label':label,title},text);b.addEventListener('click',fn,{signal:renderAc.signal});return b;}
 const changed=()=>TRAITS.some(t=>draft[t.id]!==store.state.traits.allocated[t.id]);
 function status(){if(!modal?.open)return;const reason=getEditReason(),hint=body.querySelector('[data-testid="traits-lock"]');if(hint)hint.textContent=reason||'무료 변경';const apply=body.querySelector('[data-testid="traits-apply"]');if(apply)apply.disabled=busy||!!reason||!changed();}
 async function save(){
  if(busy||destroyed)return;const reason=getEditReason();if(reason){notice=reason;paint();return;}
  busy=true;notice='';paint();
  try{await store.run({type:'traits-allocate',allocated:{...draft},expectedRevision:revision});if(destroyed)return;notice='적용 완료';onChange();}
  catch(e){notice=e.message;}
  finally{busy=false;draft={...store.state.traits.allocated};revision=store.state.revision;if(modal?.open&&!destroyed)paint();}
 }
 function selectTab(id,focus=false){tab=id;paint();if(modal?.open)modal.section.scrollTop=0;if(focus)body.querySelector(`[data-testid="traits-tab-${id}"]`)?.focus();}
 function paintAllocation(panel,s,earned){
  const used=allocatedPoints(draft),l=loadout(s),before=combatStats(l),after=combatStats({...l,traits:draft});
  panel.append(h('div',{class:'traits-counts',testid:'traits-points',role:'status'},h('span',{},`획득 ${earned}/15`),h('span',{},`배분 ${used}점`)));
  const rows=h('div',{class:'traits-rows'});
  for(const t of TRAITS){
   const value=draft[t.id],negative=t.id==='technique',sign=negative?'−':'+';
   const prior=t.id==='attack'?before.attack:t.id==='health'?before.maxHp:abilityStats(l.job,1,l).cooldown+'초';
   const next=t.id==='attack'?after.attack:t.id==='health'?after.maxHp:abilityStats(l.job,1,{...l,traits:draft}).cooldown+'초';
   const change=button('+',()=>{draft[t.id]++;paint();},{disabled:busy||value>=10||used>=earned,id:'trait-plus-'+t.id,label:LABELS[t.id]+' 1점 추가',title:`1점 ${sign}${t.step}%`});
   rows.append(h('section',{class:'trait-row','aria-label':LABELS[t.id]},h('div',{class:'trait-row-heading'},traitIcon(t.id),h('div',{},h('h3',{},LABELS[t.id]),h('small',{},`1점 ${sign}${t.step}%`)),h('strong',{class:'trait-total'},`${sign}${value*t.step}%`)),h('div',{class:'trait-row-bottom'},h('span',{class:'trait-value'+(prior!==next?' is-changing':''),testid:'trait-value-'+t.id},`${prior} → ${next}`),h('div',{class:'trait-stepper'},button('−',()=>{draft[t.id]--;paint();},{disabled:busy||!value,id:'trait-minus-'+t.id,label:LABELS[t.id]+' 1점 회수'}),h('span',{'aria-live':'polite'},h('b',{},value),h('small',{},'/10')),change))));
  }
  panel.append(rows);
  const detail=h('details',{class:'traits-extra'},h('summary',{},'스킬별 재사용 시간'));
  for(const slot of [1,2,3]){const a=abilityStats(l.job,slot,l),b=abilityStats(l.job,slot,{...l,traits:draft});detail.append(h('p',{},`${slot===3?'궁극기':'스킬 '+slot} · ${a.cooldown}초 → ${b.cooldown}초`));}panel.append(detail);
  const actions=h('div',{class:'traits-footer'},h('div',{class:'traits-footer-buttons'},button('초기화',()=>{draft=emptyAllocation();paint();},{disabled:busy||!used,id:'traits-reset',title:'배분을 0으로 미리 봅니다. 적용하면 저장되며 현재 HP는 회복되지 않아요.'}),button(busy?'저장 중…':'적용',save,{disabled:busy,id:'traits-apply'})),h('p',{class:'traits-lock',testid:'traits-lock',role:'status'},getEditReason()||'무료 변경'));
  panel.append(actions);
 }
 function paintGoals(panel,s,earned){
  const goals=traitGoals(s,STAGES),rows=goals.filter(g=>g.area===area);
  const select=h('select',{'aria-label':'획득 조건 지역',testid:'traits-area',disabled:busy});
  for(const [id,st]of Object.entries(STAGES)){const option=h('option',{value:id},st.name);option.selected=id===area;select.append(option);}
  select.addEventListener('change',()=>{area=select.value;paint();body.querySelector('[data-testid="traits-area"]')?.focus();},{signal:renderAc.signal});
  panel.append(h('div',{class:'traits-goal-top'},select,h('strong',{},`${rows.filter(g=>g.claimed).length} / ${rows.length} 완료`)),h('div',{class:'traits-journey-count'},h('span',{},'전체 포인트'),h('strong',{},`${earned} / 15`)));
  panel.append(h('div',{class:'traits-mentor-link'},h('div',{},h('strong',{},mentorOf(area).name),h('small',{},'미니맵 노란 표식 · 수련 스승')),button('대화하기',()=>onTalk(area),{disabled:busy||area!==getArea()||!!getTalkReason(),id:'traits-talk'})));
  for(const g of rows){
   const row=h('section',{class:'trait-goal'+(g.claimed?' is-complete':''),testid:g.key},h('div',{class:'trait-goal-heading'},h('span',{class:'trait-goal-badge'},g.claimed?'완료':g.ready?'보고':g.status==='active'?'진행':'수락 전'),h('strong',{},g.label),h('span',{class:'trait-goal-count'},`${g.current}/${g.target}`)),h('progress',{max:g.target,value:g.current,'aria-label':g.label}));
   if(g.key.includes('species')){const details=h('details',{},h('summary',{},'몬스터별 보기'));details.append(h('ul',{class:'trait-species'},...Object.keys(STAGES[area].mobs).map(k=>h('li',{},h('span',{},SPECIES_NAMES[k]||k),h('b',{},`${s.traits.species[area][k].length}/${area==='village'?10:20}`)))));row.append(details);}
   else if(g.key.includes('explore')){const details=h('details',{},h('summary',{},'탐험 지점 보기'));details.append(h('ul',{class:'trait-species'},...[['entry','입구'],['upper','위층'],['depth','깊은 곳']].map(([id,name])=>h('li',{},h('span',{},name),h('b',{},s.traits.explored[area].includes(id)?'발견':'미발견')))));row.append(details);}
   panel.append(row);
  }
  panel.append(h('p',{class:'traits-once'},'NPC와 대화 → 수련 수락 → 완료 보고'));
 }
 function paint(){
  const focused=body.contains(document.activeElement)?document.activeElement?.getAttribute('data-focus'):null,scroll=modal?.section.scrollTop;
  renderAc?.abort();renderAc=new AbortController();body.replaceChildren();const s=store.state,earned=earnedPoints(s,STAGES),remaining=earned-allocatedPoints(draft);
  body.append(h('header',{class:'traits-header'},h('h2',{id:'traits-title'},'모험 특성'),h('span',{class:'traits-available',testid:'traits-available'},`남은 ${remaining}점`),button('닫기',close,{disabled:busy,id:'traits-close'})));
  const tabs=h('div',{class:'traits-tabs',role:'tablist','aria-label':'모험 특성 메뉴'});
  for(const [id,label]of TABS){const b=button(label,()=>selectTab(id),{disabled:busy,id:'traits-tab-'+id});b.id='traits-tab-'+id;b.setAttribute('role','tab');b.setAttribute('aria-selected',String(tab===id));b.setAttribute('aria-controls','traits-content-'+id);b.tabIndex=tab===id?0:-1;b.addEventListener('keydown',e=>{if(busy||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();selectTab(e.key==='Home'?'allocation':e.key==='End'?'goals':tab==='allocation'?'goals':'allocation',true);},{signal:renderAc.signal});tabs.append(b);}body.append(tabs);
  if(notice)body.append(h('p',{class:'traits-notice',role:'status'},notice));
  for(const [id]of TABS){const panel=h('section',{id:'traits-content-'+id,role:'tabpanel','aria-labelledby':'traits-tab-'+id,hidden:tab!==id,testid:'traits-content-'+id});if(tab===id){if(id==='allocation')paintAllocation(panel,s,earned);else paintGoals(panel,s,earned);}body.append(panel);}
  if(focused)[...body.querySelectorAll('[data-focus]')].find(b=>b.getAttribute('data-focus')===focused&&!b.disabled)?.focus({preventScroll:true});
  if(scroll!=null&&modal?.open)modal.section.scrollTop=scroll;status();
 }
 function close(){if(busy)return;renderAc?.abort();modal?.close();modal=null;onFocus();}
 return {open(){if(destroyed||busy)return;draft={...store.state.traits.allocated};revision=store.state.revision;area=getArea();tab='allocation';notice='';paint();modal=openModal({main,titleId:'traits-title',testid:'traits-panel',children:[body],onCancel:close,canEscape:()=>!busy,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal','traits-modal');status();},refresh(){if(!modal?.open||busy)return;if(revision!==store.state.revision){notice=changed()?'진행도 갱신 · 저장된 배분을 불러왔어요.':'';draft={...store.state.traits.allocated};revision=store.state.revision;paint();}else status();},destroy(){destroyed=true;renderAc?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
