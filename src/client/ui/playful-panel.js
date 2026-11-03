import {h} from '../dom.js';
import {openModal} from './modal.js';
import {playfulIdentity,playfulChoices,playfulReply} from '../game/playful-npcs.js';
export function createPlayfulPanel({main,getAccessReason,paintPortrait,onReaction,onFocus}){
 let modal=null,ac=null,area='village',kind='mascot',turn=0,line='',destroyed=false;
 const body=h('div',{class:'playful-dialog'});
 function close(){ac?.abort();modal?.close();modal=null;onFocus();}
 function paint(){
  ac?.abort();ac=new AbortController();const s=playfulIdentity(area,kind),portrait=h('canvas',{width:128,height:168,'aria-hidden':'true'});paintPortrait(portrait,area,kind);body.replaceChildren();
  const button=(text,fn,id)=>{const b=h('button',{type:'button',class:'gp-button',testid:id},text);b.addEventListener('click',fn,{signal:ac.signal});return b;};
  const speech=h('p',{role:'status','aria-live':'polite'},line||s.greeting);
  body.append(h('header',{class:'mentor-heading'},h('div',{},h('h2',{id:'playful-title'},s.name),h('small',{},s.role)),button('닫기',close,'playful-close')),h('div',{class:'mentor-speech'},portrait,speech));
  const choices=h('div',{class:'playful-choices'});
  for(const choice of playfulChoices(area,kind))choices.append(button(choice,()=>{const reason=getAccessReason(area,kind);if(reason){speech.textContent=reason;return;}const result=playfulReply(area,kind,choice,turn++);speech.textContent=result.text;line=result.text;onReaction(area,kind,result.emote);},'playful-choice-'+choice));
  body.append(choices);
 }
 return {open(nextArea,nextKind){if(destroyed)return;area=nextArea;kind=nextKind;turn=0;line='';paint();modal=openModal({main,titleId:'playful-title',testid:'playful-panel',children:[body],onCancel:close,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal','mentor-modal','playful-modal');},close,destroy(){destroyed=true;ac?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
