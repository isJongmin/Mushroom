import {h} from '../dom.js';
import {createFirstUseHints} from '../game/first-use.js';
export function createFirstUseHintView({key,on}){
 const hints=createFirstUseHints(key),title=h('strong'),text=h('span'),close=h('button',{type:'button','aria-label':'안내 닫기',testid:'first-use-close'},'×');
 const el=h('aside',{class:'first-use-hint',hidden:true,role:'status','aria-live':'polite',testid:'first-use-hint'},h('div',{},title,text),close);let current='',home=null;
 on(close,'click',()=>{hints.dismiss();el.hidden=true;});
 return {el,request:(id,now=performance.now(),force=false)=>hints.request(id,now,force),update(now,blocked=false){home??=el.parentElement;const dialog=document.querySelector('.bk-modal[aria-modal=true]');if(dialog&&el.parentElement!==dialog)dialog.prepend(el);else if(!dialog&&home&&el.parentElement!==home)home.append(el);el.classList.toggle('is-in-dialog',!!dialog);const item=hints.update(now,blocked);el.hidden=!item;if(item&&current!==item.id){current=item.id;title.textContent=item.title;text.textContent=item.text;}},clear(){hints.clear();el.hidden=true;}};
}
