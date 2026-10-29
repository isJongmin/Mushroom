// Ultimate choreography: anticipation -> release -> decisive impact -> lingering embers.
// All noise is deterministic; no timers, random allocations per particle, or bitmap assets.
const TAU = Math.PI * 2;
const clamp = v => Math.max(0, Math.min(1, v));
const ease = t => 1 - (1 - clamp(t)) ** 3;
const PALETTES = {
  warrior: ['#ffba4b', '#fff6d1', '#ad401c'],
  archer: ['#ff9d4a', '#fff7ca', '#e45555'],
  mage: ['#9179ff', '#e9fcff', '#42b6ff'],
  thief: ['#dc518b', '#ffe5f3', '#7963ee'],
};

function poly(c, points, fill, stroke = null, width = 1) {
  c.beginPath(); points.forEach(([x,y],i) => c[i ? 'lineTo' : 'moveTo'](x,y)); c.closePath();
  c.fillStyle = fill; c.fill();
  if (stroke) { c.strokeStyle = stroke; c.lineWidth = width; c.stroke(); }
}
function line(c, points, color, width = 2, alpha = 1) {
  c.save(); c.globalAlpha *= alpha; c.lineCap = 'round'; c.lineJoin = 'round';
  c.strokeStyle = color; c.lineWidth = width; c.beginPath();
  points.forEach(([x,y],i) => c[i ? 'lineTo' : 'moveTo'](x,y)); c.stroke(); c.restore();
}
function energy(c, points, color, core, width = 5, alpha = 1) {
  line(c, points, color, width * 6, alpha * .07);
  line(c, points, color, width * 3, alpha * .22);
  line(c, points, color, width * 1.6, alpha * .65);
  line(c, points, core, width, alpha);
}
function halo(c, x, y, radius, color, alpha = 1) {
  if (radius <= 0 || alpha <= 0) return;
  c.save(); c.globalAlpha *= alpha;
  const g = c.createRadialGradient(x,y,0,x,y,radius);
  g.addColorStop(0, color + 'b0'); g.addColorStop(.25, color + '55'); g.addColorStop(1, color + '00');
  c.fillStyle = g; c.fillRect(x-radius,y-radius,radius*2,radius*2); c.restore();
}
function ring(c,x,y,r,color,width=2,alpha=1,sy=1,start=0,end=TAU) {
  c.save(); c.globalAlpha *= clamp(alpha); c.strokeStyle=color; c.lineWidth=width;
  c.beginPath(); c.ellipse(x,y,Math.max(.1,r),Math.max(.1,r*sy),0,start,end); c.stroke(); c.restore();
}
function gleam(c,x,y,r,color,angle=0) {
  c.save(); c.translate(x,y); c.rotate(angle);
  poly(c,[[0,-r],[r*.12,-r*.12],[r,0],[r*.12,r*.12],[0,r],[-r*.12,r*.12],[-r,0],[-r*.12,-r*.12]],color);
  c.restore();
}
function shards(c,x,y,r,t,color,count=32,seed=0) {
  const fade=1-clamp(t);
  c.save(); c.globalAlpha *= fade;
  for(let i=0;i<count;i++) {
    const a=i*2.399+seed, travel=r*(.15+ease(t))*(.45+(i%7)/10);
    const xx=x+Math.cos(a)*travel, yy=y+Math.sin(a)*travel*.65+t*t*22;
    c.save(); c.translate(xx,yy); c.rotate(a+t*2);
    poly(c,[[-2,-(7+i%6)*fade],[2,-2],[1,7*fade],[-2,2]],i%4?color:'#fffaf1');
    c.restore();
  }
  c.restore();
}
function lightning(c,x,y,toX,toY,color,core,seed,width=5) {
  const dx=toX-x,dy=toY-y,dist=Math.max(1,Math.hypot(dx,dy)),points=[];
  for(let n=0;n<=18;n++) {
    const t=n/18, off=n===0||n===18?0:Math.sin(n*11.7+seed)*18;
    points.push([x+dx*t-dy/dist*off,y+dy*t+dx/dist*off]);
  }
  energy(c,points,color,core,width);
  for(let n=4;n<16;n+=5){const p=points[n];line(c,[p,[p[0]+Math.sin(n+seed)*55,p[1]+45],[p[0]+Math.sin(n+seed)*80,p[1]+60]],color,width*.45,.65);}
}
function sigil(c,x,y,r,color,core,rotation=0,alpha=1,sy=1) {
  c.save(); c.translate(x,y); c.scale(1,sy); c.globalAlpha *= clamp(alpha);
  ring(c,0,0,r,color,2); ring(c,0,0,r*.94,core,1,.65); ring(c,0,0,r*.74,color,1,.6);
  for(let i=0;i<3;i++) {
    const a=rotation+i*TAU/3, pts=[];
    for(let n=0;n<3;n++){const angle=a+n*TAU/3;pts.push([Math.cos(angle)*r*.74,Math.sin(angle)*r*.74]);}
    line(c,[...pts,pts[0]],color,1.4,.7);
  }
  for(let i=0;i<18;i++){
    const a=i*TAU/18-rotation*.5,xx=Math.cos(a)*r*.84,yy=Math.sin(a)*r*.84;
    c.save();c.translate(xx,yy);c.rotate(a+Math.PI/2);
    line(c,[[-3,-5],[3,-5],[0,0],[3,5],[-3,5]],i%3?color:core,1.3);
    c.restore();
  }
  c.restore();
}
function blade(c,x,y,size,angle,alpha=1) {
  c.save();c.translate(x,y);c.rotate(angle);c.globalAlpha *= clamp(alpha);
  halo(c,0,-size*.38,size*.7,'#ffd17e',.45);
  const g=c.createLinearGradient(-size*.1,0,size*.1,0);
  g.addColorStop(0,'#bc6e35');g.addColorStop(.3,'#ffe296');g.addColorStop(.5,'#ffffff');g.addColorStop(.7,'#ffecb6');g.addColorStop(1,'#b67b3c');
  poly(c,[[0,0],[-size*.065,-size*.2],[-size*.055,-size*.82],[0,-size],[size*.055,-size*.82],[size*.065,-size*.2]],g,'#fff1c0',1.5);
  line(c,[[0,-size*.12],[0,-size*.9]],'#ffffff',2,.9);
  poly(c,[[-size*.18,-size*.2],[-size*.14,-size*.27],[-size*.05,-size*.23],[0,-size*.28],[size*.05,-size*.23],[size*.14,-size*.27],[size*.18,-size*.2],[0,-size*.16]],'#da9b41','#fff0b2',2);
  poly(c,[[-size*.016,-size*.17],[-size*.025,-size*.03],[0,size*.01],[size*.025,-size*.03],[size*.016,-size*.17]],'#68402b','#e8b15b');
  poly(c,[[0,-size*.245],[-size*.026,-size*.21],[0,-size*.18],[size*.026,-size*.21]],'#9bdfff','#faffff',1);
  c.restore();
}
function phoenix(c,x,y,size,time,alpha=1) {
  c.save();c.translate(x,y);c.scale(size,size);c.globalAlpha *= clamp(alpha);
  halo(c,0,0,130,'#ff9a38',.6);
  // Layered, curved feathers create a recognizable bird silhouette, not an enlarged arrow.
  for(const side of [-1,1]) for(let i=11;i>=0;i--) {
    const spread=(i+1)/12, flap=Math.sin(time*2)*7;
    const gradient=c.createLinearGradient(0,0,side*130,-80);
    gradient.addColorStop(0,'#fff9cd');gradient.addColorStop(.4,'#ffb34c');gradient.addColorStop(1,i%2?'#f55650':'#ff7950');c.fillStyle=gradient;
    c.beginPath();c.moveTo(side*8,5);
    c.bezierCurveTo(side*45,-20,side*(95+spread*45),-110+flap+spread*18,side*(35+spread*112),-8-spread*67+flap);
    c.bezierCurveTo(side*(90+spread*22),20-spread*35,side*37,17,side*8,18);c.fill();
    line(c,[[side*18,9],[side*(48+spread*60),-10-spread*40+flap]],'#fff2b0',1,.55);
  }
  for(let i=-2;i<=2;i++) {
    c.fillStyle=i%2?'#ff8644':'#ffc85b';c.beginPath();c.moveTo(i*3,14);c.bezierCurveTo(i*9,50,i*20+Math.sin(time*2+i)*18,80,i*19,133-Math.abs(i)*15);c.quadraticCurveTo(i*4,68,i*3+5,15);c.fill();
  }
  poly(c,[[0,-39],[-13,-6],[-7,24],[0,37],[8,24],[13,-6]],'#fff3c0','#ffca6f',1);
  poly(c,[[0,-46],[-7,-33],[0,-36],[15,-30],[6,-24],[5,-35]],'#fff8d9');
  poly(c,[[0,-39],[-12,-52],[-6,-34],[-20,-43],[-7,-26]],'#ff8c4d');
  gleam(c,4,-34,2.5,'#6d3045');c.restore();
}
function phantom(c,x,y,angle,alpha=1) {
  c.save();c.translate(x,y);c.rotate(angle);c.globalAlpha *= clamp(alpha);
  halo(c,0,-42,65,'#9272ec',.35);
  const g=c.createLinearGradient(-20,-100,20,0);g.addColorStop(0,'#27213e');g.addColorStop(.5,'#61467d');g.addColorStop(1,'#221f3b');
  poly(c,[[0,-104],[-20,-80],[-13,-60],[-31,-15],[-16,-23],[-23,-2],[0,-12],[23,-2],[16,-23],[31,-15],[13,-60],[20,-80]],g,'#bb8bd9',1.3);
  poly(c,[[-12,-80],[12,-80],[8,-65],[-8,-65]],'#17172d');
  line(c,[[-9,-76],[-3,-75]],'#ffb6d9',2.5);line(c,[[3,-75],[9,-76]],'#ffb6d9',2.5);
  line(c,[[-5,-12],[-16,10]],'#392a56',7);line(c,[[5,-12],[17,10]],'#392a56',7);
  energy(c,[[14,-50],[55,-84]],'#d28adf','#fff4f9',2.5);
  c.fillStyle='#c27aca';c.beginPath();c.moveTo(-15,-65);c.bezierCurveTo(-45,-75,-42,-40,-80,-48);c.quadraticCurveTo(-43,-31,-15,-56);c.fill();
  c.restore();
}

function warrior(c,ms,def) {
  const fade=1-clamp((ms-2250)/550),charge=ease(ms/480),r=def.radius;
  c.globalAlpha *= fade;
  halo(c,0,-100,250,'#ffc459',.25*charge);
  sigil(c,0,-4,r*charge,'#ffc56a','#fff1ba',ms*.0005,.9,.28);
  if(ms<1500){
    for(let i=0;i<6;i++){
      const a=i*TAU/6+ms*.002,rr=115+45*charge;
      const xx=Math.cos(a)*rr,yy=-180+Math.sin(a)*rr*.45;
      blade(c,xx,yy,120+25*charge,a*.2,Math.min(1,charge*1.5));
      const trail=[];for(let n=0;n<14;n++){const q=a-n*.055;trail.push([Math.cos(q)*rr,-180+Math.sin(q)*rr*.45]);}energy(c,trail,'#ffbb51','#fff5d6',2,.45);
    }
  }
  // Whirlwind cadence precedes the main sword, matching the three actual damage pulses.
  for(const delay of [600,850,1100]){
    const t=(ms-delay)/420;if(t<0||t>1)continue;
    for(let i=0;i<3;i++){const pts=[];for(let n=0;n<=30;n++){const a=i*TAU/3+t*5+n*.11,rr=r*(.3+n*.023);pts.push([Math.cos(a)*rr,-50+Math.sin(a)*rr*.45]);}energy(c,pts,'#ffb53f','#fffbdc',5,(1-t)*.8);}
  }
  if(ms>1050&&ms<2100){const fall=ease((ms-1050)/450);blade(c,0,-420-450*(1-fall),420,Math.PI,1-clamp((ms-1750)/350));}
  if(ms>=1500){
    const t=(ms-1500)/1050;
    halo(c,0,-20,280*(1+t),'#ffd06a',(1-clamp(t))*.85);
    for(let i=0;i<3;i++)ring(c,0,-5,Math.min(r,45+ease(t+i*.08)*r),'#ffda8f',5-i,1-clamp(t+i*.13),.28);
    for(let i=0;i<12;i++){const a=i*TAU/12,rr=ease(t)*r;energy(c,[[Math.cos(a)*25,-5+Math.sin(a)*8],[Math.cos(a)*rr,-5+Math.sin(a)*rr*.26]],'#eaa352','#fff0ad',2,(1-clamp(t))*.7);}
    shards(c,0,-55,r,t,'#ffd88b',44);
  }
}
function archer(c,ms,def,plan,point) {
  const fade=1-clamp((ms-2300)/500),center=320;
  c.globalAlpha *= fade;
  sigil(c,center,-365,210*ease(ms/500),'#ffb25e','#fff0b7',-ms*.0004,.8,.45);
  for(let i=0;i<12;i++){
    const a=i*TAU/12+ms*.0004;gleam(c,center+Math.cos(a)*220,-365+Math.sin(a)*95,4+2*Math.sin(ms*.003+i),'#ffedb9',a);
  }
  const flight=clamp((ms-450)/1290);
  if(ms>300&&ms<2040)phoenix(c,center,-340+flight*280,1.3+flight*.25,ms*.002,Math.min(1,(ms-300)/300)*(1-clamp((ms-1740)/300)));
  for(const [i,e] of plan.filter(e=>e.phase!=='final').entries()){
    const t=(ms-(e.delay-350))/460;if(t<0||t>1.5)continue;const [x,y]=point(e);
    for(let n=-1;n<=1;n++){
      const xx=x+n*19,yy=y-380+clamp(t)*390;
      energy(c,[[xx-14,yy-100],[xx,yy]],'#ffb668','#fff8d2',3.5,1-clamp((t-1)*2));
      poly(c,[[xx,yy+12],[xx-7,yy-3],[xx,yy],[xx+7,yy-3]],'#fff3c8');
    }
    if(t>.65){ring(c,x,y+20,75*ease(t-.65),'#ffd083',3,1-clamp(t-.65),.3);shards(c,x,y,80,t-.65,'#ffd8a1',12,i);}
  }
  if(ms>=1740){
    const t=(ms-1740)/1000;halo(c,center,-65,330,'#ff8d4c',1-clamp(t));
    for(const side of [-1,1]){const pts=[];for(let n=0;n<=30;n++){const x=center+side*n*11,y=-35-Math.sin(n/30*Math.PI)*110*(1-t);pts.push([x,y]);}energy(c,pts,'#ff9259','#fff5bb',16*(1-clamp(t)),.8);}
    for(let i=0;i<3;i++)ring(c,center,-8,(80+ease(t)*280)*(1-i*.17),'#ffcf7b',4,1-clamp(t+i*.12),.3);
    shards(c,center,-70,330,t,'#ffd99c',48);
    for(let i=0;i<8;i++){const a=i*TAU/8;gleam(c,center+Math.cos(a)*ease(t)*290,-80+Math.sin(a)*ease(t)*170,18*(1-clamp(t)),'#fff5c6',a);}
  }
}
function mage(c,ms,def,plan,point) {
  const fade=1-clamp((ms-2450)/450),center=340;
  c.globalAlpha *= fade;
  sigil(c,center,-300,190*ease(ms/550),'#a992ff','#dcf7ff',ms*.00035,.9);
  sigil(c,center,-4,300*ease(ms/550),'#8b8ef9','#b5edff',-ms*.0005,.75,.24);
  halo(c,center,-285,200,'#7873e8',.4);
  for(let i=0;i<8;i++){
    const a=i*TAU/8+ms*.00045,xx=center+Math.cos(a)*235,yy=-300+Math.sin(a)*110;
    poly(c,[[xx,yy-13],[xx-7,yy],[xx,yy+13],[xx+7,yy]],'#a2c9ff','#e2f4ff',1);
    if(ms<1740)line(c,[[xx,yy],[center+Math.cos(a)*170,-300+Math.sin(a)*170]],'#987be9',1,.5);
  }
  for(const [i,e]of plan.filter(e=>e.phase!=='final').entries()){
    const t=(ms-(e.delay-150))/500;if(t<0||t>1.5)continue;const [x,y]=point(e);
    ring(c,x,y+26,72,'#b9a9ff',2,.7,.22);
    if(t>.3){lightning(c,x,y-440,x,y+22,'#9c8cff','#f6feff',i+Math.floor(ms/95),9);halo(c,x,y-10,120,'#a0a7ff',1-clamp(t));shards(c,x,y,90,t*.6,'#bce7ff',18,i);}
  }
  if(ms>=1350&&ms<1850){const charge=ease((ms-1350)/390);halo(c,center,-280,130*charge,'#cee8ff',.75);ring(c,center,-280,80*(1-charge)+12,'#e9f8ff',5);gleam(c,center,-280,50*charge,'#faffff',ms*.001);}
  if(ms>=1740){
    const t=(ms-1740)/1100,w=80*(1-clamp(t)) + 15;
    const g=c.createLinearGradient(center-w,0,center+w,0);g.addColorStop(0,'#8d86ff00');g.addColorStop(.25,'#8584ff99');g.addColorStop(.43,'#c5eaff');g.addColorStop(.5,'#ffffff');g.addColorStop(.57,'#c5eaff');g.addColorStop(.75,'#8584ff99');g.addColorStop(1,'#8d86ff00');
    c.fillStyle=g;c.fillRect(center-w,-560,w*2,590);
    for(let i=-1;i<=1;i++)lightning(c,center+i*30,-560,center+i*24,0,'#8d9eff','#fbffff',i+Math.floor(ms/90),6-i);
    for(let i=0;i<5;i++){const a=i*TAU/5;lightning(c,center,-25,center+Math.cos(a)*260,-25+Math.sin(a)*80,'#9ca2ff','#dff9ff',i,2);}
    for(let i=0;i<3;i++)ring(c,center,-4,(80+ease(t)*260)*(1-i*.18),'#c1e8ff',5-i,1-clamp(t+i*.1),.25);
    halo(c,center,-30,330,'#aaaaff',.65*(1-clamp(t)));shards(c,center,-100,330,t,'#c0d9ff',48);
  }
}
function thief(c,ms,def) {
  const fade=1-clamp((ms-2300)/500),center=310;
  c.globalAlpha *= fade;
  halo(c,center,-240,230,'#914caa',.35);
  ring(c,center,-270,98,'#db75aa',3,.7);ring(c,center,-270,112,'#8774c6',1,.6);
  // Crescent moon uses a closed shape; it does not erase the map beneath it.
  c.fillStyle='#d86d9f';c.beginPath();c.arc(center,-270,91,-1.2,1.2);c.bezierCurveTo(center+82,-235,center+82,-305,center+33,-355);c.closePath();c.fill();
  for(let i=0;i<5;i++){
    const angle=i*TAU/5+ms*.0003,xx=center+Math.cos(angle)*200,yy=-100+Math.sin(angle)*75;
    sigil(c,xx,yy+9,36,'#9d70db','#e5b3e3',ms*.001,.55,.35);
    if(ms<1700)phantom(c,xx,yy,Math.sin(angle)*.08,clamp((ms-i*65)/240)*(1-clamp((ms-1350)/400)));
    if(ms>450&&ms<1250){const p=(ms-450+i*70)%350/350;energy(c,[[xx,yy-65],[xx+(center-xx)*p,yy-65+(-50-yy)*p]],'#c77ac5','#ffe7fc',2,1-p);}
  }
  if(ms>1250&&ms<1700){sigil(c,center,-110,140,'#c274bc','#f3c3e8',ms*.002,.7);ring(c,center,-110,130*(1-clamp((ms-1250)/410)),'#f5d0eb',4);}
  if(ms>=1660){
    const t=(ms-1660)/1050,progress=ease(t*3),alpha=1-clamp(t);
    c.save();c.globalAlpha *= alpha;
    for(let i=0;i<3;i++){
      const xx=80+i*80;const points=[[xx,-210-i*20],[xx+progress*470,-15+i*20]];
      energy(c,points,i%2?'#8d76dd':'#f080bd','#fff3fd',i===1?15:6,.85);
    }
    const length=620*progress,g=c.createLinearGradient(10,-200,length,20);g.addColorStop(0,'#db5eac00');g.addColorStop(.45,'#8c5dd4aa');g.addColorStop(.85,'#f89bd7');g.addColorStop(1,'#fff4ff');
    c.fillStyle=g;c.beginPath();c.moveTo(20,-190);c.bezierCurveTo(230,-240,length,-120,length+25,20);c.bezierCurveTo(length-100,-65,210,-95,20,-190);c.fill();
    shards(c,center,-90,330,t,'#e79bdd',42);gleam(c,center,-70,110*(1-t),'#fff0fa',Math.PI/4);
    ring(c,center,-5,270*ease(t),'#ae83e4',4,alpha,.3);c.restore();
  }
}

export function drawUltimate(c,job,ms,def,options={}) {
  const origin=options.origin,d=options.left?-1:1;
  const point=e=>origin?[(e.x-origin.x)*d,e.y-origin.y]:[e.x,e.y];
  let plan=options.plan;
  if(!plan){const count=job==='archer'?6:4;plan=Array.from({length:count},(_,i)=>({x:origin?origin.x+d*(100+i*90):100+i*90,y:origin?origin.y-30:-30,delay:(job==='archer'?700:650)+i*(job==='archer'?130:210)}));}
  c.save();c.lineCap='round';c.lineJoin='round';
  if(job==='warrior')warrior(c,ms,def);
  else if(job==='archer')archer(c,ms,def,plan,point);
  else if(job==='mage')mage(c,ms,def,plan,point);
  else thief(c,ms,def);
  c.restore();
}

export function ultimatePresentation(elapsed,impactAt,reduced=false) {
  const t=(elapsed-impactAt)/450;
  const strength=t>=0&&t<1?(1-t)**2:0;
  return {x:reduced?0:Math.sin(elapsed*.047)*6*strength,y:reduced?0:Math.sin(elapsed*.073)*3.5*strength};
}

export function drawUltimateBackdrop(c,width,height,job,elapsed,def,reduced=false,dpr=1) {
  if(elapsed<0||elapsed>def.duration)return;
  const [color,core]=PALETTES[job];
  const alpha=Math.min(ease(elapsed/250),1-clamp((elapsed-def.duration+400)/400));
  c.save();c.setTransform(1,0,0,1,0,0);
  const g=c.createRadialGradient(width*.5,height*.55,height*.15,width*.5,height*.5,Math.max(width,height)*.75);
  g.addColorStop(0,'#10112600');g.addColorStop(1,'#111026');c.globalAlpha=.38*alpha;c.fillStyle=g;c.fillRect(0,0,width,height);
  // One fade-in and fade-out, rather than repeated full-screen flashes.
  const titleFade=Math.min(ease(elapsed/200),1-clamp((elapsed-950)/350));
  if(titleFade>0){
    const s=Math.max(.7,Math.min(1.25,width/dpr/1100))*dpr,cx=width/2,yy=90*s;
    c.globalAlpha=titleFade;c.translate(reduced?cx:cx+(1-ease(elapsed/300))*-35,yy);
    const band=c.createLinearGradient(-260*s,0,260*s,0);band.addColorStop(0,color+'00');band.addColorStop(.5,color+'44');band.addColorStop(1,color+'00');c.fillStyle=band;c.fillRect(-260*s,-31*s,520*s,66*s);
    line(c,[[-240*s,-32*s],[240*s,-32*s]],color,1.5,.7);line(c,[[-180*s,35*s],[180*s,35*s]],color,1,.6);
    c.textAlign='center';c.font=`700 ${10*s}px system-ui`;c.fillStyle=color;c.fillText('U L T I M A T E',0,-13*s);
    c.font=`900 ${25*s}px system-ui`;c.lineWidth=4;c.strokeStyle='#171324';c.strokeText(def.name,0,17*s);c.fillStyle=core;c.fillText(def.name,0,17*s);
  }
  c.restore();
}

export function drawUltimateIcon(c,job) {
  const [color,core]=PALETTES[job];
  halo(c,0,0,26,color,.7);ring(c,0,0,22,color,1,.7);
  if(job==='warrior')blade(c,0,21,42,0);
  else if(job==='archer')phoenix(c,0,-2,.135,0);
  else if(job==='mage'){sigil(c,0,0,20,color,core,.25);lightning(c,-3,-19,3,19,color,core,1,2.5);gleam(c,0,0,9,core);}
  else {ring(c,0,-1,16,color,3);poly(c,[[2,-19],[-6,-3],[16,17],[8,0]],core);energy(c,[[-17,13],[17,-13]],color,core,2);}
}
