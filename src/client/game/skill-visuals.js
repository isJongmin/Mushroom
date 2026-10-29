import { abilityDefinition } from './jobs.js';
import { drawUltimate, drawUltimateIcon } from './ultimate-visuals.js';
import { drawNormalIcon, drawNormalProjectile, drawNormalImpact, drawNormalCast } from './normal-skill-visuals.js';

const TAU=Math.PI*2;
const clamp=x=>Math.max(0,Math.min(1,x));
// Existing ultimate projectiles and impacts retain their established appearance.
const CLONE_COLORS=['#9c90ff','#e9edff'];
function ring(c,x,y,r,color,width=3,alpha=1,sy=1) {
  c.save();c.globalAlpha*=alpha;c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.ellipse(x,y,Math.max(.1,r),Math.max(.1,r*sy),0,0,TAU);c.stroke();c.restore();
}
function star(c,x,y,r,color,points=4,rotation=0) {
  c.save();c.translate(x,y);c.rotate(rotation);c.fillStyle=color;c.beginPath();
  for(let i=0;i<points*2;i++){const a=i*Math.PI/points,rr=i%2?r*.27:r;c[i?'lineTo':'moveTo'](Math.cos(a)*rr,Math.sin(a)*rr);}c.closePath();c.fill();c.restore();
}
function particles(c,x,y,r,t,color,count=16,seed=0) {
  for(let i=0;i<count;i++){const a=i*2.399+seed,rr=r*(.2+clamp(t))*(.55+(i%5)/10);star(c,x+Math.cos(a)*rr,y+Math.sin(a)*rr,Math.max(.5,4*(1-clamp(t))),i%3?color:'#ffffff',4,a);}
}
export function drawSkillIcon(c,job,slot,size=40) {
  if(!abilityDefinition(job,slot))return;
  if(slot!==3)return drawNormalIcon(c,job,slot,size);
  c.save();c.translate(size/2,size/2);c.scale(size/48,size/48);c.lineCap='round';
  drawUltimateIcon(c,job);c.restore();
}
export function drawProjectileVisual(c,p,camX,camY,k,now) {
  if((p.a.skill??0)!==3)return drawNormalProjectile(c,p,camX,camY,k,now);
  const [color,core]=CLONE_COLORS,t=(now-p.at)/1000,r=14;
  c.save();c.translate((p.x-camX)*k,(p.y-camY)*k);c.scale(p.dir*k,k);c.rotate(p.angle||0);
  const glow=c.createRadialGradient(0,0,0,0,0,35);glow.addColorStop(0,'#ffe8ff99');glow.addColorStop(1,'#b87bff00');c.fillStyle=glow;c.fillRect(-35,-35,70,70);
  for(let i=1;i<5;i++){c.save();c.globalAlpha=.32/i;star(c,-i*10,Math.sin(i+t*8)*3,r*(1-i*.12),color,4,t*18);c.restore();}
  star(c,0,0,r,color,4,t*25);star(c,0,0,r*.45,core,4,-t*15);ring(c,0,0,3,'#34214f',2);
  c.restore();
}
export function drawImpactVisual(c,b,camX,camY,k,now) {
  if((b.skill??0)!==3)return drawNormalImpact(c,b,camX,camY,k,now);
  const [color,core]=CLONE_COLORS,t=clamp((now-b.at)/600);
  if(t>=1)return;
  c.save();c.translate((b.x-camX)*k,(b.y-camY)*k);c.scale(k,k);c.globalAlpha=1-t;
  const r=25*(.22+t);ring(c,0,0,r,color,4);ring(c,0,0,r*.65,core,2);star(c,0,0,18*(1-t),core,6,t);
  particles(c,0,0,r,t,color,10,b.x);c.restore();
}
export function drawAbilityEffect(c,job,slot,x,y,k,elapsed,left=false,options={}) {
  const def=abilityDefinition(job,slot);
  if(!def||elapsed<0||elapsed>def.duration+300)return;
  if(slot!==3)return drawNormalCast(c,job,slot,x,y,k,elapsed,left,options);
  c.save();c.translate(x,y);c.scale((left?-1:1)*k,k);c.lineCap='round';
  drawUltimate(c,job,elapsed,def,{...options,left});c.restore();
}
