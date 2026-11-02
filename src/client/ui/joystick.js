// A captured pointer can leave the pad without interrupting movement; the other thumb is independent.
export function stickVector(dx,dy,radius=48,dead=11){const length=Math.hypot(dx,dy),scale=length>radius?radius/length:1,x=dx*scale,y=dy*scale;if(length<dead)return {x,y,dir:0,up:false,down:false};return {x,y,dir:Math.abs(x)>dead?Math.sign(x):0,up:y<-radius*.4&&Math.abs(y)>Math.abs(x)*.85,down:y>radius*.5&&Math.abs(y)>Math.abs(x)*.85};}
export function bindJoystick(el,knob,{input,on,enabled=()=>true}){
 let pointer=null,lastDir=0;
 function reset(){input.release('stick:horizontal');input.release('stick:up');input.release('stick:down');pointer=null;lastDir=0;knob.style.transform='';el.classList.remove('is-active');}
 function move(e){const r=el.getBoundingClientRect(),v=stickVector(e.clientX-r.left-r.width/2,e.clientY-r.top-r.height/2,Math.min(48,r.width*.36));if(v.dir!==lastDir){input.release('stick:horizontal');if(v.dir)input.press('stick:horizontal',v.dir);lastDir=v.dir;}
  for(const [id,held,action]of [['stick:up',v.up,'climb-up'],['stick:down',v.down,'prone']]){if(held)input.pressAction(id,action,performance.now());else input.release(id);}knob.style.transform=`translate(${v.x}px,${v.y}px)`;
 }
 on(el,'pointerdown',e=>{if(pointer!==null||!enabled())return;e.preventDefault();pointer=e.pointerId;el.setPointerCapture(pointer);el.classList.add('is-active');move(e);});
 on(el,'pointermove',e=>{if(e.pointerId===pointer){if(!enabled()){reset();return;}move(e);}});
 for(const name of ['pointerup','pointercancel','lostpointercapture'])on(el,name,e=>{if(e.pointerId===pointer)reset();});on(el,'contextmenu',e=>e.preventDefault());return {reset};
}
