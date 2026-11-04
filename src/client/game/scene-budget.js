// Presentation policy only. Simulation, damage, networking and own skills never skip work.
export function scenePolicy(players=1,slow=false){
 const crowded=players>=8||slow;
 return {crowded,maxPixels:crowded?1600000:3200000,maxDpr:crowded?1.5:2,remotePets:crowded?1:3};
}
export function sceneDpr(width,height,deviceDpr,policy){
 return Math.max(.5,Math.min(deviceDpr||1,policy.maxDpr,Math.sqrt(policy.maxPixels/Math.max(1,width*height))));
}
export function createSceneBudget(){
 let average=16,slow=false,lastChange=-Infinity;
 return {sample(ms,players,now){
   if(Number.isFinite(ms)&&ms>0&&ms<1000)average=average*.94+ms*.06;
   if(now-lastChange>5000){if(!slow&&average>28){slow=true;lastChange=now;}else if(slow&&average<19){slow=false;lastChange=now;}}
   return scenePolicy(players,slow);
 },get averageMs(){return average;}};
}

const COLORS={warrior:'#ffd28b',archer:'#a7f3be',mage:'#d5c3ff',thief:'#9eeaff'};
// Low-cost but visible remote spell silhouettes; no particles/gradients or screen-wide filters.
export function drawCrowdCast(c,a,elapsed,x,y,k,definition){
 if(elapsed<0||elapsed>definition.duration||definition.speed&&!definition.finisher)return;
 const ultimate=a.skill===3,t=elapsed/definition.duration,reach=Math.min(a.w,ultimate?350:180);
 c.save();c.translate(x,y);c.scale((a.dir==='left'?-1:1)*k,k);c.strokeStyle=COLORS[a.job]||'#fff4d3';c.lineWidth=ultimate?5:3;c.globalAlpha*=.85;
 c.beginPath();
 if(a.job==='mage'){c.moveTo(20,-40);c.lineTo(reach*.45,-95);c.lineTo(reach*.6,-25);c.lineTo(reach,-70);}
 else if(a.job==='archer'){c.moveTo(20,-35);c.lineTo(reach,-35);c.moveTo(reach-18,-47);c.lineTo(reach,-35);c.lineTo(reach-18,-23);}
 else if(a.job==='thief'){c.moveTo(20,-30);c.lineTo(reach,-95);c.moveTo(20,-95);c.lineTo(reach,-30);}
 else c.ellipse(reach*.45,-40,Math.max(15,reach*.5),ultimate?80:45,-.35,-1.3+t*.4,1.3+t*.4);
 c.stroke();c.restore();
}
export function drawCrowdProjectile(c,p,camX,camY,k){
 c.save();c.translate((p.x-camX)*k,(p.y-camY)*k);c.scale(p.dir*k,k);c.rotate(p.angle||0);c.fillStyle=COLORS[p.job.id]||'#fff4d3';
 c.fillRect(-12,-3,24,6);c.fillStyle='#fffdf0';c.fillRect(-2,-2,5,4);c.restore();
}
