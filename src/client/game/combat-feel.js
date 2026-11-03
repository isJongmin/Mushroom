// Presentation-only hitstop. Gameplay clocks, input and host simulation never pause.
export const FEEL_LIMITS=Object.freeze({stop:42,strongStop:62,interval:180,maxImpacts:24,life:260});
export function createCombatFeel(){
 let impacts=[],reactions=new Map(),stopUntil=0,lastStop=-Infinity,paintImpact=false,hurtAt=-Infinity;
 function confirm(now,strong=false){if(now-lastStop<FEEL_LIMITS.interval)return;lastStop=now;stopUntil=now+(strong?FEEL_LIMITS.strongStop:FEEL_LIMITS.stop);paintImpact=true;}
 return {
  confirm,
  hit({id,x,y,dir=1,now,local=false,strong=false,hurt=false}){
   if(![x,y,now].every(Number.isFinite))return false;
   const previous=reactions.get(id);if(previous&&now-previous.at<28)return false;
   const r={id,x,y,dir:dir<0?-1:1,at:now,strong,hurt};reactions.delete(id);reactions.set(id,r);
   while(reactions.size>64)reactions.delete(reactions.keys().next().value);
   impacts.push(r);if(impacts.length>FEEL_LIMITS.maxImpacts)impacts.shift();
   if(local)confirm(now,strong||hurt);if(hurt)hurtAt=now;return true;
  },
  shouldHold(now,{reduced=false,blocked=false}={}){
   if(reduced||blocked){paintImpact=false;stopUntil=0;return false;}
   if(paintImpact){paintImpact=false;return false;} // Paint the confirmed impact before holding it.
   return now<stopUntil;
  },
  pose(id,now,reduced=false){const r=reactions.get(id),age=r?now-r.at:Infinity;if(age<0||age>180)return {x:0,brightness:1};const t=age/180;return {x:reduced?0:r.dir*(r.strong?7:4)*Math.sin(t*Math.PI)*(1-t),brightness:age<85?1.5:1};},
  camera(now,reduced=false){const age=now-hurtAt;if(reduced||age<0||age>200)return {x:0,y:0};const a=(1-age/200)*2;return {x:Math.sin(age*.11)*a,y:Math.cos(age*.09)*a*.5};},
  draw(c,camX,camY,k,now,reduced=false){
   impacts=impacts.filter(r=>now-r.at<FEEL_LIMITS.life);
   for(const r of impacts){const age=now-r.at;if(age<0)continue;const t=age/FEEL_LIMITS.life,x=(r.x-camX)*k,y=(r.y-camY)*k;if(x<-70*k||x>c.canvas.width+70*k||y<-70*k||y>c.canvas.height+70*k)continue;
    c.save();c.translate(x,y);c.scale(k,k);c.globalAlpha=(1-t)*.95;c.strokeStyle=r.hurt?'#ffb39b':'#fff0bb';c.lineWidth=r.strong?3:2;
    const radius=reduced?13:8+t*(r.strong?36:24);
    c.beginPath();for(let i=0;i<6;i++){const a=i*Math.PI/3+.3;c.moveTo(Math.cos(a)*radius*.4,Math.sin(a)*radius*.4);c.lineTo(Math.cos(a)*radius,Math.sin(a)*radius);}c.stroke();
    if(!reduced){c.fillStyle=r.hurt?'#e99882':'#f5cb7b';for(let i=0;i<7;i++){const a=i*2.399,dist=7+t*38,xx=Math.cos(a)*dist+r.dir*t*14,yy=Math.sin(a)*dist+t*t*24;c.fillRect(xx,yy,i%2?3:4,i%2?3:4);}}
    c.restore();
   }
   const age=now-hurtAt;if(age>=0&&age<320){c.save();c.setTransform(1,0,0,1,0,0);c.strokeStyle=`rgba(221,105,83,${(1-age/320)*.5})`;c.lineWidth=reduced?3:8;c.strokeRect(2,2,c.canvas.width-4,c.canvas.height-4);c.restore();}
   for(const [id,r]of reactions)if(now-r.at>500)reactions.delete(id);
  },
  clear(){impacts=[];reactions.clear();stopUntil=0;lastStop=-Infinity;paintImpact=false;hurtAt=-Infinity;},
  get size(){return impacts.length;},get holdingUntil(){return stopUntil;}
 };
}
