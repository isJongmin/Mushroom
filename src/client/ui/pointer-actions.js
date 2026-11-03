// Every combat control owns its pointer. A second thumb never releases the movement thumb.
export function bindPointerAction(el,{on,activate,release=()=>{},enabled=()=>!el.disabled,hold=false}){
 let pointer=null;
 function reset(){const id=pointer;pointer=null;if(id!==null){release();el.classList.remove('is-pressed');try{if(el.hasPointerCapture?.(id))el.releasePointerCapture(id);}catch{}}}
 on(el,'pointerdown',e=>{if(pointer!==null||!enabled()||(e.button!==undefined&&e.button!==0))return;e.preventDefault();pointer=e.pointerId;try{el.setPointerCapture?.(pointer);}catch{}el.classList.add('is-pressed');activate(e);});
 for(const name of ['pointerup','pointercancel','lostpointercapture'])on(el,name,e=>{if(e.pointerId===pointer)reset();});
 on(el,'click',e=>{if(!hold&&e.detail===0&&!e.pointerType&&enabled())activate(e);});
 on(el,'contextmenu',e=>e.preventDefault());
 return {reset};
}
