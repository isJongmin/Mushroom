import { abilityDefinition } from './jobs.js';

const TAU=Math.PI*2;
const COLORS={slash:['#9edcff','#fff9df'],cross:['#ff75b8','#fff0ff'],wave:['#ff6830','#fff2a0'],whirlwind:['#ffd35b','#fffbe7'],arrow:['#8be6ac','#eeffdb'],fan:['#54e5cf','#e7fff9'],bomb:['#ff874b','#fff7a0'],rain:['#75bfff','#ecfaff'],orb:['#ad7cff','#fff1ff'],claw:['#f580ff','#fff4ff'],beam:['#51ccff','#edfeff'],storm:['#b79aff','#fffbc4'],star:['#8ae2ff','#eefaff'],triple:['#ff85c7','#ffe7f9'],saw:['#9c7bff','#ecdaff'],clones:['#9c90ff','#e9edff']};
const clamp=(x)=>Math.max(0,Math.min(1,x));
function path(c,points,color,width=3,alpha=1) {
  c.save();c.globalAlpha*=alpha;c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.beginPath();points.forEach(([x,y],i)=>c[i?'lineTo':'moveTo'](x,y));c.stroke();c.restore();
}
function glowPath(c,points,color,core,width=4,alpha=1) {
  path(c,points,color,width*4,alpha*.12);path(c,points,color,width*2,alpha*.4);path(c,points,core,width,alpha);
}
function ring(c,x,y,r,color,width=3,alpha=1,sy=1) {
  c.save();c.globalAlpha*=alpha;c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.ellipse(x,y,Math.max(.1,r),Math.max(.1,r*sy),0,0,TAU);c.stroke();c.restore();
}
function star(c,x,y,r,color,points=4,rotation=0) {
  c.save();c.translate(x,y);c.rotate(rotation);c.fillStyle=color;c.beginPath();
  for(let i=0;i<points*2;i++){const a=i*Math.PI/points,rr=i%2?r*.27:r;c[i?'lineTo':'moveTo'](Math.cos(a)*rr,Math.sin(a)*rr);}c.closePath();c.fill();c.restore();
}
function arrow(c,x,y,length,color,angle=0,width=3) {
  c.save();c.translate(x,y);c.rotate(angle);glowPath(c,[[-length,0],[7,0]],color,'#f6ffec',width);path(c,[[0,-6],[9,0],[0,6]],color,width);path(c,[[-length,0],[-length-6,-5]],color,2);path(c,[[-length,0],[-length-6,5]],color,2);c.restore();
}
function bolt(c,x,y,toX,toY,color,core,seed=0,width=4) {
  const dx=toX-x,dy=toY-y,len=Math.max(1,Math.hypot(dx,dy)),nx=-dy/len,ny=dx/len,pts=[];
  for(let i=0;i<=12;i++){const t=i/12,j=(i===0||i===12)?0:Math.sin(i*7.13+seed)*15;pts.push([x+dx*t+nx*j,y+dy*t+ny*j]);}
  glowPath(c,pts,color,core,width);
}
function slash(c,x,y,r,angle,color,core,t=1) {
  c.save();c.translate(x,y);c.rotate(angle);const sweep=clamp(t*2.8);c.beginPath();c.arc(0,0,r,-1.2,-1.2+sweep*2.2);c.arc(-r*.16,0,r*.65,-1.2+sweep*2.2,-1.2,true);c.closePath();
  const g=c.createLinearGradient(-r,0,r,0);g.addColorStop(0,color+'00');g.addColorStop(.65,color);g.addColorStop(1,core);c.fillStyle=g;c.fill();c.restore();
}
function particles(c,x,y,r,t,color,count=16,seed=0) {
  for(let i=0;i<count;i++){const a=i*2.399+seed,rr=r*(.2+clamp(t))*(.55+(i%5)/10);star(c,x+Math.cos(a)*rr,y+Math.sin(a)*rr,Math.max(.5,4*(1-clamp(t))),i%3?color:'#ffffff',4,a);}
}
function magicCircle(c,x,y,r,color,angle=0) {
  ring(c,x,y,r,color,2,.65,.3);ring(c,x,y,r*.76,color,1,.5,.3);
  for(let i=0;i<8;i++){const a=i*TAU/8+angle;star(c,x+Math.cos(a)*r,y+Math.sin(a)*r*.3,4,color,4,a);}
}
function claw(c,x,y,t,color,core,reverse=false) {
  const progress=clamp(t*4),sgn=reverse?-1:1;
  for(let i=0;i<3;i++) {
    const xx=x-25+i*20;
    glowPath(c,[[xx-26*sgn,y-38],[xx+14*sgn*progress,y-38+55*progress],[xx+23*sgn*progress,y-38+82*progress]],color,core,5-i*.6);
  }
}
function silhouette(c,x,y,alpha,color) {
  c.save();c.globalAlpha*=alpha;c.fillStyle=color;c.beginPath();c.arc(x,y-65,12,0,TAU);c.fill();c.beginPath();c.moveTo(x-10,y-52);c.lineTo(x-18,y-17);c.lineTo(x+22,y-17);c.lineTo(x+10,y-52);c.closePath();c.fill();path(c,[[x-4,y-20],[x-14,y]],color,6);path(c,[[x+8,y-20],[x+20,y]],color,6);path(c,[[x+7,y-47],[x+38,y-42]],color,6);c.restore();
}

/** Sixteen different pictograms, rendered with the same shapes used by their attacks. */
export function drawSkillIcon(c,job,slot,size=40) {
  const p=abilityDefinition(job,slot)?.pattern;if(!p)return;
  const [color,core]=COLORS[p];c.save();c.translate(size/2,size/2);c.scale(size/48,size/48);c.lineCap='round';
  switch(p){
    case 'slash': slash(c,-3,3,23,-.2,color,core,.6);break;
    case 'cross':glowPath(c,[[-15,-16],[16,17]],color,core,5);glowPath(c,[[15,-16],[-16,17]],color,core,5);break;
    case 'wave':for(let i=0;i<3;i++){c.fillStyle=i%2?core:color;c.beginPath();c.moveTo(-20+i*12,18);c.quadraticCurveTo(-14+i*12,-25,-3+i*12,-15);c.quadraticCurveTo(-10+i*12,5,1+i*12,18);c.fill();}break;
    case 'whirlwind': for(let i=0;i<3;i++){c.save();c.rotate(i*TAU/3);slash(c,0,0,20,0,color,core,.5);c.restore();}break;
    case 'arrow':arrow(c,3,0,25,color,-.5);break;
    case 'fan':for(let i=-1;i<=1;i++)arrow(c,7,i*8,24,color,i*.4,2);break;
    case 'bomb':star(c,7,-5,19,color,8);star(c,7,-5,10,core,6);arrow(c,2,8,22,'#ffce91',-.4,2);break;
    case 'rain':for(let i=0;i<3;i++)arrow(c,-12+i*12,13-i*3,25,color,Math.PI/2,2);break;
    case 'orb':ring(c,0,0,17,color,5);ring(c,0,0,9,core,3);star(c,-13,-14,6,core);break;
    case 'claw':claw(c,-1,-1,.35,color,core);break;
    case 'beam':bolt(c,-20,7,20,-7,color,core,1,4);break;
    case 'storm':for(let i=0;i<3;i++)bolt(c,-12+i*12,-20,-14+i*12,20,color,core,i,2);break;
    case 'star':star(c,0,0,22,color,4,.2);star(c,0,0,8,core,4,.2);break;
    case 'triple':for(let i=0;i<3;i++)star(c,-14+i*14,12-i*12,11,i%2?core:color,4,.3);break;
    case 'saw':star(c,0,0,23,color,12);ring(c,0,0,11,core,4);break;
    case 'clones':for(let i=0;i<3;i++)silhouette(c,-15+i*14,18, .45+i*.25,color);break;
  }
  c.restore();
}

/** Traveling effects. The collision engine uses the same x/y and trajectory as this drawing. */
export function drawProjectileVisual(c,p,camX,camY,k,now) {
  const def=abilityDefinition(p.a.job,p.a.skill??0),pattern=def.pattern,[color,core]=COLORS[pattern];
  const t=(now-p.at)/1000;
  c.save();c.translate((p.x-camX)*k,(p.y-camY)*k);c.scale(p.dir*k,k);c.rotate(p.angle||0);
  if(['arrow','fan','bomb'].includes(pattern)) {
    if(pattern==='bomb'){particles(c,-5,0,20,(t*4)%1,color,8);star(c,7,0,12,color,6,t*4);}
    arrow(c,0,0,pattern==='bomb'?42:30,color,0,pattern==='bomb'?5:3);
  } else if(pattern==='orb') {
    const g=c.createRadialGradient(0,0,2,0,0,28);g.addColorStop(0,'#ffffff');g.addColorStop(.22,core);g.addColorStop(.48,color);g.addColorStop(1,color+'00');c.fillStyle=g;c.fillRect(-28,-28,56,56);
    for(let i=0;i<3;i++){ring(c,-i*11,0,12-i*2,color,2,.6-i*.15);}
    ring(c,0,0,18,color,2);star(c,0,0,8,core,4,t*4);
  } else if(pattern==='wave') {
    const g=c.createLinearGradient(-85,0,15,0);g.addColorStop(0,'#ff360000');g.addColorStop(.7,'#ff6424');g.addColorStop(1,'#fff8b5');c.fillStyle=g;
    c.beginPath();c.moveTo(-90,23);c.quadraticCurveTo(-48,2,-28,-43);c.quadraticCurveTo(-9,-8,4,-62);c.quadraticCurveTo(33,-12,8,24);c.closePath();c.fill();
    slash(c,-9,-7,48,.1,color,core,.6);particles(c,-32,-5,40,(t*3)%1,'#ffd076',10);
  } else {
    const big=pattern==='saw',r=big?43:14;
    for(let i=1;i<5;i++){c.save();c.globalAlpha=.32/i;star(c,-i*10,Math.sin(i+t*8)*3,r*(1-i*.12),color,big?12:4,t*18);c.restore();}
    if(big){ring(c,0,0,48,color,2,.65);ring(c,0,0,35,core,3,.8);}
    star(c,0,0,r,color,big?12:4,t*(big?12:25));star(c,0,0,r*.45,core,big?6:4,-t*15);ring(c,0,0,big?13:3,'#34214f',big?6:2);
  }
  c.restore();
}

export function drawImpactVisual(c,b,camX,camY,k,now) {
  const def=abilityDefinition(b.job,b.skill??0),[color,core]=COLORS[def.pattern],t=clamp((now-b.at)/600);
  if(t>=1)return;
  c.save();c.translate((b.x-camX)*k,(b.y-camY)*k);c.scale(k,k);c.globalAlpha=1-t;
  const r=(def.splash||25)*(.22+t);
  if(def.pattern==='bomb'||def.pattern==='wave') {
    const g=c.createRadialGradient(0,0,0,0,0,r);g.addColorStop(0,'#fffbd7');g.addColorStop(.35,'#ffca5a');g.addColorStop(.7,'#ff5c2d99');g.addColorStop(1,'#ff462000');c.fillStyle=g;c.fillRect(-r,-r,r*2,r*2);star(c,0,0,r*.75,'#ffb657',9,t);ring(c,0,0,r,'#ffeec1',4);
  } else if(def.pattern==='saw') {
    for(let i=0;i<3;i++)slash(c,0,0,r*.8,i*TAU/3,color,core,t+.25);
  } else {ring(c,0,0,r,color,4);ring(c,0,0,r*.65,core,2);star(c,0,0,18*(1-t),core,6,t);}
  particles(c,0,0,r,t,color,def.splash?24:10,b.x);
  c.restore();
}

/** Independent cast lifetimes keep ultimates visible when the next basic attack starts. */
export function drawAbilityEffect(c,job,slot,x,y,scale,elapsed,left=false,options={}) {
  const def=abilityDefinition(job,slot);if(!def||elapsed<0||elapsed>def.duration+300)return;
  const [color,core]=COLORS[def.pattern],t=elapsed/def.duration,d=left?-1:1;
  c.save();c.translate(x,y);c.scale(d*scale,scale);c.lineCap='round';
  // No global screen flash: bright halos stay within the spell's world footprint.
  const origin=options.origin;
  let plan=options.plan;
  if(!plan){
    const count=def.pattern==='rain'?6:def.pattern==='storm'?4:def.pattern==='claw'?2:1;
    plan=Array.from({length:count},(_,i)=>({x:origin?origin.x+d*(90+i*75):90+i*75,y:origin?origin.y-35:-35,delay:def.pattern==='rain'?260+i*125:def.pattern==='storm'?240+i*240:i*170}));
  }
  const point=e=>origin?[(e.x-origin.x)*d,e.y-origin.y]:[e.x,e.y];
  const castAlpha=1-clamp(elapsed/350);
  if(castAlpha>0){magicCircle(c,0,-3,slot?38:20,color,t);star(c,18,-38,(slot?14:8)*castAlpha,core,6,t*3);}
  switch(def.pattern){
    case 'slash':c.globalAlpha=1-clamp(t);slash(c,12,-40,65,-.25,color,core,t);break;
    case 'cross':
      for(let i=0;i<2;i++){const st=(elapsed-[70,220][i])/350;if(st>=0&&st<1){c.globalAlpha=1-st;slash(c,55,-42,90,i?2.6:-.5,color,core,st+.1);glowPath(c,i?[[10,-100],[130,15]]:[[10,15],[130,-100]],color,core,4*(1-st));}}
      break;
    case 'whirlwind':{
      c.globalAlpha=1-clamp((t-.72)/.4);magicCircle(c,0,-2,def.radius*clamp(t*4),color,t*4);
      for(let i=0;i<3;i++){const pts=[];for(let n=0;n<=20;n++){const a=i*TAU/3+t*11+n*.13,r=def.radius*(.3+n*.035);pts.push([Math.cos(a)*r,-50+Math.sin(a)*r*.62]);}glowPath(c,pts,color,core,5,.85);const [sx,sy]=pts[20];star(c,sx,sy,16,core,4,t*11);}
      for(let i=0;i<2;i++)ring(c,0,-48,def.radius*((t*3+i*.5)%1),color,2,.4,.6);
      particles(c,0,-55,def.radius,t*.75,color,28);break;
    }
    case 'claw':
      for(const [i,e] of plan.entries()){const st=(elapsed-e.delay)/330;if(st<0||st>1)continue;const [xx,yy]=point(e);c.globalAlpha=1-st;claw(c,xx,yy,st+.05,color,core,i%2===1);particles(c,xx,yy,48,st,color,10,i);}
      break;
    case 'beam':{
      const charge=clamp(elapsed/150),fade=1-clamp((elapsed-540)/300);if(elapsed<150){ring(c,28,-40,28*charge,color,4);ring(c,28,-40,35*(1-charge),core,2);}
      else {c.globalAlpha=fade;const w=options.origin?.w||def.range;const pulse=1+Math.sin(elapsed*.07)*.12;const grad=c.createLinearGradient(0,-77,0,-3);grad.addColorStop(0,color+'00');grad.addColorStop(.35,color+'88');grad.addColorStop(.5,core);grad.addColorStop(.65,color+'88');grad.addColorStop(1,color+'00');c.fillStyle=grad;c.fillRect(20,-77,w,74);for(let i=0;i<3;i++)bolt(c,20,-40+(i-1)*9,w,-40+(i-1)*9,color,core,Math.floor(elapsed/60)+i,3*pulse);ring(c,w,-40,25,color,4);particles(c,w,-40,35,(elapsed%150)/150,color,12);}
      break;
    }
    case 'rain':{
      c.globalAlpha=.65*(1-clamp((elapsed-1100)/350));magicCircle(c,def.range*.48,-245,def.range*.48,color,t);
      for(const [i,e]of plan.entries()){const st=(elapsed-(e.delay-220))/400;if(st<0||st>1.5)continue;const [xx,yy]=point(e);c.globalAlpha=1-clamp((st-.6)/.9);const yyFall=yy-260+clamp(st)*260;for(let j=-1;j<=1;j++)arrow(c,xx+j*17,yyFall-18*Math.abs(j),52,color,Math.PI/2,3);if(st>=.55){ring(c,xx,yy+25,45*clamp(st),core,3,1-clamp(st),.3);particles(c,xx,yy,50,st-.5,color,10,i);}}
      break;
    }
    case 'storm':
      for(const [i,e]of plan.entries()){const st=(elapsed-(e.delay-180))/560;if(st<0||st>1.4)continue;const [xx,yy]=point(e);c.globalAlpha=1-clamp((st-.8)/.6);magicCircle(c,xx,yy+30,65,color,t);if(st<.32){ring(c,xx,yy-220,25+st*30,color,4);continue;}bolt(c,xx-7,yy-280,xx,yy+22,color,core,i+Math.floor(elapsed/65),8);bolt(c,xx+35,yy-170,xx,yy+22,'#fff485',core,i,3);ring(c,xx,yy+22,70*clamp(st),color,4,1,.25);particles(c,xx,yy,75,st-.3,color,20,i);}
      break;
    case 'clones':
      for(let i=0;i<3;i++){const st=(elapsed-i*180)/800;if(st<0||st>1.4)continue;silhouette(c,-38+i*43,-12-i*18,(1-clamp(st))*.8,color);ring(c,-28+i*43,-55-i*18,22*(1-clamp(st)),core,2,.5);}
      break;
    case 'fan':c.globalAlpha=1-clamp(t);for(let i=-1;i<=1;i++)arrow(c,25+t*55,-38+i*20,22,color,i*.17,2);break;
    case 'triple':c.globalAlpha=1-clamp(t);for(let i=0;i<3;i++)star(c,30+i*12,-35-i*9,10,color,4,t*10+i);break;
    case 'saw':c.globalAlpha=1-clamp(elapsed/300);ring(c,25,-38,40*clamp(t*4),color,4);break;
    case 'bomb':c.globalAlpha=castAlpha;star(c,25,-35,24,color,8,t);break;
    case 'wave':c.globalAlpha=castAlpha;particles(c,30,-10,55,t,color,18);break;
    case 'orb':c.globalAlpha=castAlpha;ring(c,20,-38,18,color,3);break;
    case 'star':c.globalAlpha=castAlpha;slash(c,15,-35,23,-.4,color,core,t+.3);break;
    case 'arrow':c.globalAlpha=castAlpha;path(c,[[0,-57],[18,-40],[0,-20]],color,3);break;
  }
  c.restore();
}
