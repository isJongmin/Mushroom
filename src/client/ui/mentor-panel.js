import {h} from '../dom.js';
import {openModal} from './modal.js';
import {traitGoals,SPECIES_NAMES} from '../game/adventure-traits.js';
import {STAGES} from '../game/progression.js';
import {mentorOf} from '../game/training-mentors.js';
const questTitle=g=>g.key.endsWith('hunt20')?'검을 쥐는 마음':g.key.includes('species')?'다섯 적의 가르침':g.key.includes('explore')?'길 위의 수련':g.key.includes('defense')?'지켜내는 힘':'강자의 증명';
export function createMentorPanel({main,store,getArea,getAccessReason,paintPortrait,onChange,onReward,onAllocate,onFocus}){
 let modal=null,area='village',selected=null,screen='list',busy=false,notice='',renderAc=null,destroyed=false,lastRevision=-1;
 const body=h('div',{class:'mentor-dialog'});
 function button(text,fn,id,disabled=false){const b=h('button',{type:'button',class:'gp-button',testid:id,disabled,'data-focus':id},text);b.addEventListener('click',fn,{signal:renderAc.signal});return b;}
 function close(){if(busy)return;renderAc?.abort();modal?.close();modal=null;onFocus();}
 async function run(type){if(busy||!selected)return;const reason=getAccessReason();if(reason){notice=reason;paint();return;}busy=true;notice='';paint();try{const result=await store.run({type,key:selected});if(destroyed)return;if(result?.duplicate){screen='quest';notice='이미 받은 보상입니다.';}else if(type==='trait-quest-claim'){screen='reward';if(result?.point)onReward();}else screen='accepted';onChange();}catch(e){notice=e.message;}finally{busy=false;if(modal?.open&&!destroyed)paint();}}
 function paint(){
  const focus=body.contains(document.activeElement)?document.activeElement?.getAttribute('data-focus'):null;renderAc?.abort();renderAc=new AbortController();body.replaceChildren();const m=mentorOf(area),goals=traitGoals(store.state,STAGES).filter(g=>g.area===area),quest=goals.find(g=>g.key===selected);lastRevision=store.state.revision;
  const portrait=h('canvas',{width:128,height:168,'aria-hidden':true});paintPortrait?.(portrait,area);
  body.append(h('header',{class:'mentor-heading'},h('div',{},h('h2',{id:'mentor-title'},m.name),h('small',{},m.title)),button('닫기',close,'mentor-close',busy)));
  const speech=screen==='reward'?m.complete:screen==='accepted'?m.accept:screen==='quest'&&quest?(quest.ready?'약속한 수련을 마쳤군. 네 안의 힘을 깨워주겠다.':quest.status==='active'?'수련은 계속되고 있다. 준비가 되면 내게 돌아와라.':`${quest.label}를 달성하고 돌아와라. 네 경험을 힘으로 바꾸어 주겠다.`):m.greeting;
  body.append(h('div',{class:'mentor-speech'},portrait,h('p',{},speech)));
  if(notice)body.append(h('p',{class:'traits-notice',role:'status'},notice));
  if(screen==='list'){
   const list=h('div',{class:'mentor-choices','aria-label':'수련 퀘스트'});
   for(const g of goals){const state=g.claimed?'완료':g.ready?'보상 받기':g.status==='active'?'진행 중':'수락 가능';const b=button('',()=>{selected=g.key;screen='quest';paint();},'mentor-quest-'+g.key,busy);b.classList.add('mentor-choice');b.append(h('strong',{},questTitle(g)),h('span',{class:g.ready?'is-ready':''},state));list.append(b);}body.append(list);
   body.append(button('특성 배분',()=>{close();onAllocate();},'mentor-allocate',busy));
  }else if(screen==='reward')body.append(h('div',{class:'mentor-reward',role:'status',testid:'mentor-reward'},h('strong',{},'수련 완료'),h('span',{},'특성 포인트 +1')),h('div',{class:'mentor-actions'},button('다른 수련',()=>{screen='list';paint();},'mentor-back',busy),button('특성 배분',()=>{close();onAllocate();},'mentor-allocate',busy)));
  else if(screen==='accepted')body.append(h('div',{class:'mentor-reward',role:'status'},h('strong',{},'수련을 수락했습니다'),h('span',{},quest?.label)),h('div',{class:'mentor-actions'},button('다른 수련',()=>{screen='list';paint();},'mentor-back',busy),button('알겠습니다',close,'mentor-leave',busy)));
  else if(quest){
   body.append(h('section',{class:'mentor-objective'},h('h3',{},questTitle(quest)),h('p',{},quest.label),h('div',{},h('span',{},`${quest.current} / ${quest.target}`),h('b',{},'보상 · 특성 포인트 1점')),h('progress',{max:quest.target,value:quest.current,'aria-label':quest.label})));
   if(quest.key.includes('species')){const details=h('details',{class:'mentor-targets'},h('summary',{},'대상 몬스터'));details.append(h('ul',{class:'trait-species'},...Object.keys(STAGES[area].mobs).map(k=>h('li',{},h('span',{},SPECIES_NAMES[k]||k),h('b',{},`${store.state.traits.species[area][k].length}/${area==='village'?10:20}`)))));body.append(details);}
   const reason=getAccessReason();body.append(h('div',{class:'mentor-actions'},button('돌아가기',()=>{screen='list';paint();},'mentor-back',busy),quest.claimed?button('완료한 수련',()=>{},'mentor-completed',true):quest.ready?button('보상 받기',()=>run('trait-quest-claim'),'mentor-claim',busy||!!reason):quest.status==='available'?button('수련 시작',()=>run('trait-quest-accept'),'mentor-accept',busy||!!reason):button('계속 수련하기',close,'mentor-leave',busy)));if(reason)body.append(h('p',{class:'traits-lock',role:'status'},reason));
  }
  if(focus&&modal?.open){const target=[...body.querySelectorAll('[data-focus]')].find(b=>b.getAttribute('data-focus')===focus&&!b.disabled)||body.querySelector('[data-testid=mentor-accept]:not(:disabled),[data-testid=mentor-claim]:not(:disabled),[data-testid=mentor-leave]:not(:disabled),[data-testid=mentor-allocate]:not(:disabled)');target?.focus({preventScroll:true});}
 }
 return {open(){if(destroyed||busy)return;area=getArea();screen='list';selected=null;notice='';paint();modal=openModal({main,titleId:'mentor-title',testid:'mentor-panel',children:[body],onCancel:close,canEscape:()=>!busy,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal','mentor-modal');},refresh(){if(modal?.open&&!busy&&store.state.revision!==lastRevision)paint();},destroy(){destroyed=true;renderAc?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
