import {handAnchor} from './avatar-hand-anchors.js';
import {petSpec,GRADE_COLORS,WEAPONS} from './progression.js';
export const SKILL_KEYS=Object.freeze({KeyK:1,KeyL:2,Semicolon:3,Digit1:1,Digit2:2,Digit3:3});
export const SKILL_LABELS=['','K','L',';'];
// Deterministic species motion; reactions do not change combat or loot rules.
export function petPose(id,now,{moving=false,reaction=null,reduced=false}={}) {
 const p=petSpec(id);if(!p)return {x:0,y:0,angle:0,sx:1,sy:1};
 const seed=p.tier+({village:0,quarry:5,forest:10}[p.area]),t=now/(170+seed*17);
 const fly=['quarry:1','quarry:4','forest:2','forest:4'].includes(id);
 const hop=['village:0','village:1','forest:0','forest:1'].includes(id);
 let x=0,y=fly?-9:0,angle=0,sx=1,sy=1;
 if(!reduced){
  y=fly?-9-Math.sin(t)*4:hop?-Math.abs(Math.sin(t))*(moving?9:3):Math.sin(t*2)*(moving?2:1);
  angle=fly?Math.sin(t)*.08:Math.sin(t)*(moving?.08:.025);
  if(hop){sx=1+Math.cos(t*2)*.045;sy=1-Math.cos(t*2)*.06;}
  if(id==='quarry:0')x=Math.sin(t*2)*(moving?2:1);
  if(id==='quarry:2')x=Math.sin(t)*3;
  if(id==='quarry:3'){y=-Math.abs(Math.sin(t))*(moving?3:1);angle=Math.sin(t)*.04;}
  if(id==='village:2')angle=Math.sin(t*2)*.06;
  if(id==='village:3'||id==='forest:3')y=-Math.abs(Math.sin(t))*(moving?5:1);
  if(id==='village:4')angle=Math.sin(t*.5)*.025;
  if(reaction==='loot'){y-=Math.abs(Math.sin(t*2))*7;sx*=1.06;}
  if(reaction==='hurt'){angle-=.12;sx*=.94;sy*=1.05;}
  if(reaction==='attack')x+=Math.sin(t)*3;
 }
 return {x,y,angle,sx,sy,fly,seed};
}
export function drawEquippedGear(c,job,l,x,y,k,now,{left=false,hidden=false,reduced=false,drawItem,frame=2,hand=null}={}) {
 if(hidden||!l||!drawItem)return;
 const tier=l.tier||0,dir=left?-1:1,anchors=handAnchor(frame);
 const near=hand?.near||{x:anchors.N[0],y:anchors.N[1]},far=hand?.far||{x:anchors.F[0],y:anchors.F[1]};
 const kind=l.weapon||WEAPONS[job]||'sword',scale=kind==='claw'?.62:.73;
 const grip={sword:[-Math.sin(.6)*15,Math.cos(.6)*15],bow:[4,-2],staff:[-Math.sin(.3)*15,Math.cos(.3)*15],claw:[0,8]}[kind];
 c.save();c.translate(x,y);c.scale(dir,1);
 if(tier>=2){c.globalAlpha=.12;c.fillStyle=GRADE_COLORS[tier];c.beginPath();c.ellipse(0,-3*k,(19+tier*2)*k,5*k,0,0,Math.PI*2);c.fill();c.globalAlpha=1;}
 if(l.shield>=0)drawItem(c,'shield',far.x*k,(far.y+3)*k,.48*k,GRADE_COLORS[l.shield],l.shield);
 c.translate(near.x*k,near.y*k);
 drawItem(c,kind,-grip[0]*scale*k,-grip[1]*scale*k,scale*k,GRADE_COLORS[tier],tier);
 if(tier>=3&&!reduced){c.fillStyle=GRADE_COLORS[tier];for(let i=0;i<tier;i++){const t=now/600+i*2;c.globalAlpha=.35+.25*Math.sin(t);c.fillRect(Math.cos(t)*15*k,(-15+Math.sin(t)*20)*k,2*k,2*k);}}
 c.restore();
}
export function drawEquipBurst(c,x,y,k,tier,age,{reduced=false}={}) {
 if(age<0||age>900)return;const t=age/900;c.save();c.globalAlpha=(1-t)*.75;c.strokeStyle=GRADE_COLORS[tier];c.lineWidth=(tier>=3?3:2)*k;
 c.beginPath();c.ellipse(x,y-30*k,(18+(reduced?0:t*45))*k,(25+(reduced?0:t*48))*k,0,0,Math.PI*2);c.stroke();
 if(!reduced){c.fillStyle=GRADE_COLORS[tier];for(let i=0;i<6+tier*3;i++){const a=i*Math.PI*2/(6+tier*3),r=(15+t*65)*k;c.fillRect(x+Math.cos(a)*r,y-30*k+Math.sin(a)*r,3*k,3*k);}}c.restore();
}
