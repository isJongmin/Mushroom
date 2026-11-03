import {h} from '../dom.js';
import {openModal} from './modal.js';
import {taxiDestinations,TAXI_DRIVER} from '../game/town-taxi.js';
export function createTaxiPanel({main,getState,getJob,getArea,getReason,onTravel,onFocus,paintPortrait}){
 let modal=null,ac=null,destroyed=false;
 function close(){ac?.abort();modal?.close();modal=null;onFocus();}
 return {open(){if(destroyed)return;ac?.abort();ac=new AbortController();const body=h('div',{class:'taxi-dialog'}),notice=h('p',{role:'status',class:'taxi-notice',hidden:true});
 const button=(label,fn,attrs={})=>{const b=h('button',{type:'button',class:'gp-button',...attrs},label);b.addEventListener('click',fn,{signal:ac.signal});return b;};
 body.append(h('header',{class:'mentor-heading'},h('div',{},h('h2',{id:'taxi-title'},'마을 택시'),h('small',{},'기사 달콩 · 무료 운행')),button('닫기',close,{testid:'taxi-close'})));
 const portrait=h('canvas',{width:128,height:160,'aria-hidden':'true'});paintPortrait?.(portrait);
 body.append(h('div',{class:'taxi-greeting'},portrait,h('div',{},h('strong',{},TAXI_DRIVER.name),h('p',{},'어디로 가드릴까요~?'),h('small',{},'편히 타세요. 목적지만 골라주시면 됩니다.'))));
 const list=h('div',{class:'taxi-destinations','aria-label':'목적지 선택'});
 for(const d of taxiDestinations(getState(),getJob(),getArea())){const b=button('',()=>{const reason=getReason(d.id);if(reason){notice.textContent=reason;notice.hidden=false;return;}if(onTravel(d.id))close();},{class:'gp-button taxi-destination',testid:'taxi-to-'+d.id,disabled:d.current||!d.unlocked});b.append(h('strong',{},d.name),h('span',{},d.current?'현재 위치':d.unlocked?'이동 →':d.requirement));list.append(b);}
 body.append(list,notice);modal=openModal({main,titleId:'taxi-title',testid:'taxi-panel',children:[body],onCancel:close,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal','mentor-modal','taxi-modal');},close,destroy(){destroyed=true;ac?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
