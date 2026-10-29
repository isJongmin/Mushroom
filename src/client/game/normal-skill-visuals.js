import { abilityDefinition } from './jobs.js';

// Compact, weapon-led art direction. Ordinary attacks never request cinematic overlays.
const TAU = Math.PI * 2;
const clamp = x => Math.max(0, Math.min(1, x));
const ease = x => 1 - (1 - clamp(x)) ** 3;
const INK = {
  slash: ['#72cce9', '#effbff', '#27485f'],
  cross: ['#ee729f', '#fff0ed', '#66304c'],
  wave: ['#f58a48', '#fff2c4', '#793a35'],
  arrow: ['#7fd2ac', '#f1fce1', '#29524c'],
  fan: ['#53d8cb', '#e6fff2', '#2c6474'],
  bomb: ['#eeb566', '#fff4ce', '#765050'],
  orb: ['#b598f4', '#f8edff', '#51417e'],
  claw: ['#e58bdb', '#fff0ff', '#6c3e84'],
  beam: ['#69d5ec', '#eefeff', '#3f73a5'],
  star: ['#96d1df', '#f0faff', '#37546b'],
  triple: ['#b492ef', '#f3e9ff', '#5d4681'],
  saw: ['#9d9feb', '#edf0ff', '#424b81'],
};
export const NORMAL_VISUAL_LIMITS = Object.freeze({ maxParticles: 16, maxAmbientRadius: 80, cinematic: false });

function polygon(c, points, fill, stroke = null, width = 1) {
  c.beginPath(); points.forEach(([x,y],i) => c[i ? 'lineTo' : 'moveTo'](x,y)); c.closePath();
  c.fillStyle=fill; c.fill();
  if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}
}
function line(c, points, color, width=2, alpha=1) {
  c.save(); c.globalAlpha *= clamp(alpha); c.strokeStyle=color; c.lineWidth=Math.max(.1,width);c.lineCap='round';c.lineJoin='round';
  c.beginPath();points.forEach(([x,y],i)=>c[i?'lineTo':'moveTo'](x,y));c.stroke();c.restore();
}
function trace(c,points,color,core,width=2,alpha=1) {
  line(c,points,color,width*4,alpha*.1);line(c,points,color,width*1.8,alpha*.4);line(c,points,core,width,alpha);
}
function ring(c,x,y,r,color,width=1.5,alpha=1,sy=1,start=0,end=TAU) {
  c.save();c.globalAlpha*=clamp(alpha);c.strokeStyle=color;c.lineWidth=width;
  c.beginPath();c.ellipse(x,y,Math.max(.1,r),Math.max(.1,r*sy),0,start,end);c.stroke();c.restore();
}
function bloom(c,x,y,r,color,alpha=.5) {
  r=Math.min(r,NORMAL_VISUAL_LIMITS.maxAmbientRadius);
  if(r<=0)return;
  c.save();c.globalAlpha*=clamp(alpha);const g=c.createRadialGradient(x,y,0,x,y,r);
  g.addColorStop(0,color+'80');g.addColorStop(.4,color+'28');g.addColorStop(1,color+'00');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);c.restore();
}
function diamond(c,x,y,r,color,rotation=0) {
  c.save();c.translate(x,y);c.rotate(rotation);polygon(c,[[0,-r],[r*.42,0],[0,r],[-r*.42,0]],color);c.restore();
}
function sparks(c,x,y,r,t,color,count=10,seed=0) {
  const life=clamp(t),fade=1-life;c.save();c.globalAlpha*=fade;
  for(let i=0;i<Math.min(count,NORMAL_VISUAL_LIMITS.maxParticles);i++){
    const angle=i*2.399+seed,rr=r*(.15+ease(life))*(.5+i%4*.12);
    c.save();c.translate(x+Math.cos(angle)*rr,y+Math.sin(angle)*rr*.65);c.rotate(angle);
    polygon(c,[[-1,-(4+i%4)*fade],[1,0],[0,3*fade],[-1,0]],i%3?color:'#fff7ed');c.restore();
  }
  c.restore();
}
function lens(c,x,y,r,color,core,rotation=0,alpha=1) {
  c.save();c.globalAlpha*=clamp(alpha);
  ring(c,x,y,r,color,1.5,.8,1,rotation,rotation+Math.PI*1.45);
  ring(c,x,y,r*.72,core,1,.5,1,-rotation,-rotation+Math.PI*1.2);
  for(let i=0;i<4;i++){const a=i*TAU/4+rotation;diamond(c,x+Math.cos(a)*r,y+Math.sin(a)*r,3,color,a);}
  c.restore();
}
function metalGradient(c,x1,y1,x2,y2,color,core,dark) {
  const g=c.createLinearGradient(x1,y1,x2,y2);g.addColorStop(0,dark);g.addColorStop(.35,color);g.addColorStop(.49,core);g.addColorStop(.56,'#ffffff');g.addColorStop(.72,color);g.addColorStop(1,dark);return g;
}
function dagger(c,x,y,length,rotation,color,core,dark) {
  c.save();c.translate(x,y);c.rotate(rotation);
  polygon(c,[[0,-length],[-5,-length*.75],[-4,-9],[0,-4],[4,-9],[5,-length*.75]],metalGradient(c,-5,0,5,0,color,core,dark),core,.7);
  polygon(c,[[-10,-10],[-8,-14],[0,-11],[8,-14],[10,-10],[0,-6]],'#bca47f','#ede0ba',.8);
  line(c,[[0,-5],[0,8]],dark,4);line(c,[[0,-4],[0,6]],'#bda27d',1.4);c.restore();
}
function ribbon(c,x,y,r,rotation,color,core,progress=1,alpha=1) {
  c.save();c.translate(x,y);c.rotate(rotation);c.globalAlpha*=clamp(alpha);
  const p=ease(progress),tip=r*(.2+p*.8),g=c.createLinearGradient(-r*.6,-r,tip,r*.2);
  g.addColorStop(0,color+'00');g.addColorStop(.55,color+'99');g.addColorStop(.9,color);g.addColorStop(1,core);
  c.fillStyle=g;c.beginPath();c.moveTo(-r*.55,-r*.7);
  c.bezierCurveTo(r*.05,-r*1.05,tip*.95,-r*.85,tip,-r*.05);
  c.bezierCurveTo(tip*.6,-r*.59,-r*.05,-r*.62,-r*.55,-r*.7);c.closePath();c.fill();
  c.strokeStyle=core;c.lineWidth=1.7;c.beginPath();c.moveTo(-r*.35,-r*.73);c.bezierCurveTo(r*.2,-r*.87,tip*.87,-r*.65,tip,-r*.05);c.stroke();
  c.restore();
}
function featherArrow(c,color,core,dark,length=38,powered=false) {
  const g=metalGradient(c,-length,0,10,0,color,core,dark);
  polygon(c,[[-length,-1.5],[2,-1.5],[8,0],[2,1.5],[-length,1.5]],g);
  polygon(c,[[15,0],[-2,-6],[2,0],[-2,6]],g,core,.8);
  line(c,[[2,0],[13,0]],core,1);
  for(const side of [-1,1]){
    polygon(c,[[-length,0],[-length-9,side*8],[-length+4,side*5],[-length+11,0]],color,dark,.7);
    line(c,[[-length+2,side*2],[-length-5,side*6]],core,.7,.75);
  }
  if(powered){lens(c,1,0,12,color,core,.3,.8);diamond(c,8,0,4,core,Math.PI/2);}
}
function shuriken(c,color,core,dark,r=16,rotation=0,saw=false) {
  c.save();c.rotate(rotation);const points=saw?7:4;
  for(let i=0;i<points;i++){
    c.save();c.rotate(i*TAU/points);
    polygon(c,[[3,-3],[r*.3,-r],[r*.56,-r*.44],[r*.24,-r*.11],[r*.15,3]],metalGradient(c,0,-r,r*.5,0,color,core,dark),core,.65);
    line(c,[[r*.32,-r*.85],[r*.24,-r*.2]],core,.8,.8);c.restore();
  }
  ring(c,0,0,r*.32,dark,r*.16,1);ring(c,0,0,r*.19,color,1.2);
  if(saw){ring(c,0,0,r*.74,color,1,.45);ring(c,0,0,r*1.05,color,1.4,.8,1,.3,2.3);}
  c.restore();
}
function energyOrb(c,color,core,dark,t=0,size=18) {
  bloom(c,0,0,size*2,color,.6);
  const g=c.createRadialGradient(-size*.25,-size*.3,1,0,0,size);
  g.addColorStop(0,'#ffffff');g.addColorStop(.15,core);g.addColorStop(.45,color);g.addColorStop(1,dark);
  c.fillStyle=g;c.beginPath();c.arc(0,0,size*.63,0,TAU);c.fill();
  for(let i=0;i<3;i++){c.save();c.rotate(t+i*Math.PI/3);ring(c,0,0,size*(.95+i*.13),i===1?core:color,1.3,.7,.4);c.restore();}
  diamond(c,Math.cos(t*2)*size,Math.sin(t*2)*size*.5,3.5,core,t);
}
function flameCrest(c,color,core,dark,t=0) {
  const g=c.createLinearGradient(-85,0,22,-20);g.addColorStop(0,color+'00');g.addColorStop(.45,dark+'99');g.addColorStop(.8,color);g.addColorStop(1,core);
  for(let i=2;i>=0;i--){c.save();c.translate(-i*10,-i*4);c.globalAlpha*=1-i*.22;c.fillStyle=g;c.beginPath();c.moveTo(-95,19);c.bezierCurveTo(-45,7,-48,-32,-19,-49);c.quadraticCurveTo(-25,-15,3,-66);c.bezierCurveTo(31,-34,28,-2,9,19);c.quadraticCurveTo(-23,28,-95,19);c.fill();c.restore();}
  ribbon(c,-4,11,64,.2,color,core,.9,.9);
  polygon(c,[[4,-49],[14,-30],[10,-1],[-3,13],[4,-12]],core);
  line(c,[[-64,12],[-27,7],[4,-18]],'#ffcf83',1.3,.8);
  for(let i=0;i<7;i++){const xx=-20-i*12,yy=-13+Math.sin(t*12+i)*17;c.save();c.globalAlpha=.7-i*.08;diamond(c,xx,yy,3+i%3,color,-.4);c.restore();}
}

export function drawNormalIcon(c,job,slot,size=40) {
  const def=abilityDefinition(job,slot);if(!def||slot===3)return;
  const p=def.pattern,[color,core,dark]=INK[p];
  c.save();c.translate(size/2,size/2);c.scale(size/48,size/48);
  bloom(c,0,0,25,color,.35);ring(c,0,0,22,color,1,.2,1,-.4,1.5);
  switch(p){
    case 'slash':dagger(c,-7,15,35,.6,color,core,dark);ribbon(c,-8,12,27,.1,color,core,1,.8);break;
    case 'cross':dagger(c,-11,15,35,.63,color,core,dark);dagger(c,11,15,35,-.63,color,core,dark);break;
    case 'wave':c.scale(.3,.3);flameCrest(c,color,core,dark);break;
    case 'arrow':c.rotate(-.65);featherArrow(c,color,core,dark,24);break;
    case 'fan':for(let i=-1;i<=1;i++){c.save();c.translate(7,i*7);c.rotate(i*.35);featherArrow(c,color,core,dark,22);c.restore();}break;
    case 'bomb':c.rotate(-.55);featherArrow(c,color,core,dark,25,true);lens(c,4,0,19,color,core,.3);break;
    case 'orb':energyOrb(c,color,core,dark,.2,17);break;
    case 'claw':for(let i=0;i<3;i++)ribbon(c,-9+i*8,17,30,-.5,color,core,1);break;
    case 'beam':lens(c,-12,0,10,color,core,.2);trace(c,[[-12,0],[20,0]],color,core,4);line(c,[[-8,-6],[17,-6]],color,1,.6);line(c,[[-8,6],[17,6]],color,1,.6);break;
    case 'star':shuriken(c,color,core,dark,23,.3);break;
    case 'triple':for(let i=0;i<3;i++){c.save();c.translate(-13+i*13,11-i*11);shuriken(c,color,core,dark,11,.2+i*.3);c.restore();}break;
    case 'saw':shuriken(c,color,core,dark,22,.2,true);break;
  }
  c.restore();
}

export function drawNormalProjectile(c,p,camX,camY,k,now) {
  const def=abilityDefinition(p.a.job,p.a.skill??0),pattern=def.pattern,[color,core,dark]=INK[pattern],t=(now-p.at)/1000;
  c.save();c.translate((p.x-camX)*k,(p.y-camY)*k);c.scale(p.dir*k,k);c.rotate(p.angle||0);
  // Directional ribbons are tighter than the spell body, keeping targets readable.
  if(['arrow','fan','bomb'].includes(pattern)){
    const length=pattern==='bomb'?45:34;
    trace(c,[[-90,-3],[-44,0],[1,0]],color,core,pattern==='bomb'?2:1,.4);
    if(pattern==='fan'){line(c,[[-55,-8],[-9,-5]],color,1,.5);line(c,[[-55,8],[-9,5]],color,1,.5);}
    featherArrow(c,color,core,dark,length,pattern==='bomb');
    if(pattern==='bomb'){lens(c,0,0,19,color,core,t*4,.8);for(let i=0;i<5;i++)diamond(c,-25-i*10,Math.sin(t*13+i)*9,2.5,color,.5);}
  }else if(pattern==='orb'){
    for(let i=3;i>0;i--){c.save();c.globalAlpha=.1/i;c.translate(-i*13,Math.sin(t*8+i)*2);energyOrb(c,color,core,dark,t,14-i);c.restore();}
    energyOrb(c,color,core,dark,t*2,18);
  }else if(pattern==='wave')flameCrest(c,color,core,dark,t);
  else{
    const big=pattern==='saw',r=big?43:16;
    for(let i=3;i>0;i--){c.save();c.translate(-i*(big?19:11),0);c.globalAlpha=(big?.12:.18)/i;shuriken(c,color,core,dark,r*(1-i*.08),t*15-i*.3,big);c.restore();}
    if(big)bloom(c,0,0,65,color,.3);
    shuriken(c,color,core,dark,r,t*(big?12:23),big);
    if(big)for(let i=0;i<3;i++){const a=t*5+i*TAU/3;line(c,[[Math.cos(a)*49,Math.sin(a)*49],[Math.cos(a+.35)*49,Math.sin(a+.35)*49]],core,1,.7);}
  }
  c.restore();
}

export function drawNormalImpact(c,b,camX,camY,k,now) {
  const def=abilityDefinition(b.job,b.skill??0),[color,core,dark]=INK[def.pattern],t=clamp((now-b.at)/600);
  if(t>=1)return;
  c.save();c.translate((b.x-camX)*k,(b.y-camY)*k);c.scale(k,k);c.globalAlpha=1-t;
  const extent=def.splash||28;
  if(def.pattern==='bomb'||def.pattern==='wave'){
    bloom(c,0,0,extent*.85,color,.7*(1-t));
    for(let i=0;i<6;i++){const a=i*TAU/6+t*.2;c.save();c.rotate(a);polygon(c,[[12,0],[extent*.6*ease(t+.1),-8*(1-t)],[extent*ease(t),0],[extent*.6*ease(t+.1),6*(1-t)]],i%2?color:core);c.restore();}
    ring(c,0,0,extent*ease(t),color,2,1-t,.75);ring(c,0,0,extent*.7*ease(t+.1),core,1.2,.7*(1-t),.75);
    for(let i=0;i<3;i++)ribbon(c,0,0,extent*.55,i*TAU/3,color,core,t+.2,.5);
  }else if(def.pattern==='saw'){
    for(let i=0;i<3;i++)ribbon(c,-6,10,65,i*TAU/3,color,core,t+.15,1-t);
    ring(c,0,0,55*ease(t),color,1.5,.5);
  }else if(def.pattern==='orb'){
    lens(c,0,0,28*ease(t+.12),color,core,t*.7,1-t);bloom(c,0,0,38,color,.5);
    for(let i=0;i<5;i++){const a=i*TAU/5;diamond(c,Math.cos(a)*36*ease(t),Math.sin(a)*30*ease(t),6*(1-t),core,a);}
  }else{
    trace(c,[[-22*(1-t),-16*(1-t)],[18*(1-t),13*(1-t)]],color,core,2.5);
    trace(c,[[12*(1-t),-19*(1-t)],[-13*(1-t),18*(1-t)]],color,core,1.5);
    ring(c,0,0,23*ease(t),color,1,.5);
  }
  sparks(c,0,0,extent*.75,t,color,def.splash?16:8,b.x*.01);
  c.restore();
}

function clawStrike(c,x,y,t,color,core,reverse=false) {
  c.save();c.translate(x,y);c.scale(reverse?-1:1,1);
  for(let i=0;i<3;i++){
    const xx=-26+i*20,progress=ease(t*3),g=c.createLinearGradient(xx,-48,xx+38,45);
    g.addColorStop(0,color+'00');g.addColorStop(.4,color+'88');g.addColorStop(.85,color);g.addColorStop(1,core);
    c.fillStyle=g;c.beginPath();c.moveTo(xx-18,-45);c.bezierCurveTo(xx+26,-32,xx+34,10,xx+42*progress,42*progress);c.bezierCurveTo(xx+12,0,xx+12,-23,xx-18,-45);c.fill();
    c.strokeStyle=core;c.lineWidth=1.6;c.beginPath();c.moveTo(xx-10,-41);c.bezierCurveTo(xx+21,-25,xx+27,7,xx+42*progress,42*progress);c.stroke();
  }
  c.restore();
}
function beam(c,w,ms,color,core) {
  const charge=clamp(ms/150),fade=1-clamp((ms-540)/300);
  c.save();c.globalAlpha*=fade;
  bloom(c,24,-38,48,color,.4);lens(c,24,-38,24,color,core,ms*.002);lens(c,43,-38,18,color,core,-ms*.003,.6);
  if(ms<150){diamond(c,24,-38,12*charge,core,ms*.002);c.restore();return;}
  const grow=ease((ms-120)/80),length=w*grow;
  const g=c.createLinearGradient(0,-62,0,-14);g.addColorStop(0,color+'00');g.addColorStop(.32,color+'44');g.addColorStop(.5,core+'cc');g.addColorStop(.68,color+'44');g.addColorStop(1,color+'00');c.fillStyle=g;c.fillRect(30,-62,length-20,48);
  trace(c,[[30,-38],[length,-38]],color,core,3.5);
  for(let i=0;i<2;i++){
    const points=[];for(let n=0;n<=26;n++){const xx=30+n/26*(length-30),envelope=Math.sin(n/26*Math.PI);points.push([xx,-38+Math.sin(n*.7-ms*.018+i*Math.PI)*11*envelope]);}
    line(c,points,color,1.8,.8);
  }
  for(let i=0;i<5;i++){const xx=65+(i/5+.02*Math.sin(ms*.006))*Math.max(0,length-80);diamond(c,xx,-38,4,color,Math.PI/2);}
  polygon(c,[[length+11,-38],[length-8,-47],[length-2,-38],[length-8,-29]],core);
  lens(c,length,-38,17,color,core,-ms*.001,.65);
  c.restore();
}

export function drawNormalCast(c,job,slot,x,y,k,elapsed,left=false,options={}) {
  const def=abilityDefinition(job,slot);if(!def||slot===3||elapsed<0||elapsed>def.duration+300)return;
  const p=def.pattern,[color,core,dark]=INK[p],t=elapsed/def.duration,dir=left?-1:1;
  c.save();c.translate(x,y);c.scale(dir*k,k);
  const castFade=1-clamp(elapsed/(slot?300:180));
  if(slot&&castFade>0){bloom(c,20,-38,slot===2?65:40,color,.3*castFade);lens(c,20,-38,slot===2?29:20,color,core,elapsed*.002,castFade);}
  switch(p){
    case 'slash':{
      c.globalAlpha=1-clamp(t);ribbon(c,8,-6,85,-.6,color,core,t*2);
      if(t<.65)dagger(c,13,-32,45,-.8+ease(t*2)*1.7,color,core,dark);
      break;
    }
    case 'cross':
      for(let i=0;i<2;i++){
        const st=(elapsed-[90,240][i])/330;if(st<0||st>1)continue;
        c.save();c.globalAlpha=1-st;
        c.save();if(i){c.translate(0,-80);c.scale(1,-1);}
        ribbon(c,55,-10,110,-.6,color,core,st*3+.2);
        ribbon(c,48,-7,104,-.6,color,core,st*3+.2,.18);c.restore();
        const cut=i?[[42,10],[148,-92]]:[[35,-92],[148,12]];
        trace(c,cut,color,core,2.3,Math.max(.15,1-st));
        if(st<.5)diamond(c,92,-40,11*(1-st),core,Math.PI/4);
        sparks(c,92,-40,48,st,color,9,i);c.restore();
      }
      break;
    case 'claw':{
      const origin=options.origin,plan=options.plan||[0,1].map(i=>({x:origin?origin.x+dir*150:150,y:origin?origin.y-35:-35,delay:100+i*170}));
      for(const [i,e]of plan.entries()){
        const st=(elapsed-e.delay)/350;if(st<0||st>1)continue;
        const xx=origin?(e.x-origin.x)*dir:e.x,yy=origin?e.y-origin.y:e.y;
        c.save();c.globalAlpha=1-st;lens(c,xx,yy,44,color,core,i*.4,.25*(1-st));clawStrike(c,xx,yy,st+.05,color,core,i%2===1);sparks(c,xx+8,yy,48,st,color,10,i);c.restore();
      }
      break;
    }
    case 'beam':beam(c,options.origin?.w||def.range,elapsed,color,core);break;
    case 'arrow':
    case 'fan':{
      c.save();c.globalAlpha=castFade;
      c.strokeStyle=color;c.lineWidth=2.3;c.beginPath();c.moveTo(2,-65);c.quadraticCurveTo(28,-39,2,-13);c.stroke();line(c,[[2,-65],[13,-38],[2,-13]],core,1.1);
      if(p==='fan')for(let i=-1;i<=1;i++)line(c,[[18,-38],[52,-38+i*16]],color,1,.5);
      c.restore();break;
    }
    case 'orb':
      c.save();c.globalAlpha=castFade;c.translate(22,-38);energyOrb(c,color,core,dark,elapsed*.006,14);c.restore();break;
    case 'wave':
      c.save();c.globalAlpha=castFade;ribbon(c,18,-5,82,-.3,color,core,t*3+.2);sparks(c,28,-8,48,clamp(t*2),color,10);c.restore();break;
    case 'bomb':
      c.save();c.globalAlpha=castFade;lens(c,26,-36,26,color,core,-elapsed*.003);diamond(c,26,-36,10,core,Math.PI/2);c.restore();break;
    case 'star':
    case 'triple':
    case 'saw':{
      c.save();c.globalAlpha=castFade;
      if(p==='triple')for(let i=0;i<3;i++){c.save();c.translate(20+i*10,-30-i*9);shuriken(c,color,core,dark,10,elapsed*.02+i);c.restore();}
      else {c.translate(22,-35);ribbon(c,-5,12,p==='saw'?46:26,-.4,color,core,t*3+.3,.6);shuriken(c,color,core,dark,p==='saw'?25:13,elapsed*.02,p==='saw');}
      c.restore();break;
    }
  }
  c.restore();
}
