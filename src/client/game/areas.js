// 세 맵은 같은 방의 채팅을 공유하며 사냥/위치/호스트는 mapId로 분리한다.
export const AREA_IDS = Object.freeze(['forest', 'village', 'quarry']);
export const normalizeMapId = (id) => AREA_IDS.includes(id) ? id : 'village';
export const AREA_NAMES = Object.freeze({ village: '버섯마을', forest: '바람결 이끼숲', quarry: '별빛 수정 채석장' });
export function areaMap(id, village) {
  id = normalizeMapId(id);
  if (id === 'village') return { ...village, id, name: AREA_NAMES[id] };
  const platforms = [
    {id:'west-bough',x1:470,x2:1040,y:650}, {id:'high-bough',x1:1280,x2:1800,y:490},
    {id:'east-bough',x1:2050,x2:2500,y:640}, {id:'summit',x1:2740,x2:3140,y:450},
  ];
  const ropes = [{id:'west-rope',x:760,y1:650,y2:800},{id:'high-rope',x:1510,y1:490,y2:800},
    {id:'east-rope',x:2250,y1:640,y2:800},{id:'summit-rope',x:2920,y1:450,y2:800}];
  const monsters = id === 'forest' ? ['forest-stump','mushroom','slime'] : ['crystal-crab','golem','bat'];
  return {id,name:AREA_NAMES[id],layers:[],width:3500,height:900,groundY:800,spawn:{x:240,y:800},platforms,ropes,
    spawns:[{id:'west-ground',platform:'ground',x1:420,x2:1450,mobs:monsters,max:4},
      {id:'east-ground',platform:'ground',x1:1850,x2:3050,mobs:monsters,max:4},
      ...platforms.map((p,i)=>({id:p.id+'-mobs',platform:p.id,x1:p.x1+35,x2:p.x2-35,mobs:[monsters[i%monsters.length]],max:2}))]};
}
export function areaPortals(map) {
  const i=AREA_IDS.indexOf(normalizeMapId(map.id));
  return [{id:'left',x:100,y:map.groundY,to:AREA_IDS[(i+2)%3],entry:'right'},
    {id:'right',x:map.width-100,y:map.groundY,to:AREA_IDS[(i+1)%3],entry:'left'}];
}
export function nearbyPortal(map,player) {
  if (!player || player.dead) return null;
  return areaPortals(map).find(p=>Math.abs(p.x-player.x)<64 && Math.abs(p.y-player.y)<28) || null;
}
export function sameArea(a,b) { return normalizeMapId(a?.mapId)===normalizeMapId(b?.mapId); }
const palettes = {
 forest:{sky:'#c5e4d9',haze:'#eef1c9',far:'#96b9a1',mount:'#6f997e',bark:'#6b5841',leaf:'#477c58',light:'#77a96b',soil:'#6b5d46',edge:'#a6ca7d'},
 quarry:{sky:'#253354',haze:'#7283a3',far:'#465879',mount:'#344763',bark:'#474d69',leaf:'#727eab',light:'#9aa9d1',soil:'#44445d',edge:'#a0c7d2'},
};
export function drawBiomeMap(ctx,map,camX,camY,k,W,H) {
  const p=palettes[map.id]||palettes.forest;
  ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.imageSmoothingEnabled=false;
  const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,p.sky);g.addColorStop(1,p.haze);ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
  const noise=(x,n)=>{const v=Math.sin(x*12.9898+n*78.233)*43758.5453;return v-Math.floor(v);};
  const poly=(color,points)=>{ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>ctx[i?'lineTo':'moveTo'](Math.round((x-camX)*k),Math.round((y-camY)*k)));ctx.closePath();ctx.fill();};
  const rect=(color,x,y,w,h)=>{ctx.fillStyle=color;ctx.fillRect(Math.round((x-camX)*k),Math.round((y-camY)*k),Math.ceil(w*k),Math.ceil(h*k));};
  for(let layer=0;layer<2;layer++) {
    const par=layer ? .35 : .18,step=layer?190:260;
    for(let x=Math.floor(camX*par/step)*step-step;x<camX*par+W/k+step;x+=step) {
      const top=240+layer*130+Math.sin(x*.009)*65;
      rect(layer?p.mount:p.far,x+camX*(1-par),top,step+1,800-top);
      rect(layer?p.mount:p.far,x+40+camX*(1-par),top-55,step-80,60);
    }
  }
  // 완만한 땅 위에 큼직한 블록 수관/수정 기둥. 화면에 필요한 것만 그린다.
  const step=map.id==='forest'?235:185;
  for(let x=Math.floor((camX-180)/step)*step;x<camX+W/k+step;x+=step) {
    const h=220+(Math.sin(x*.021)+1)*65;
    if(map.id==='forest') {
      rect(p.bark,x+75,800-h,30,h);rect('#89724e',x+75,800-h,8,h);
      for(let y=800-h+12;y<790;y+=30) {rect('#564d38',x+92,y,11,3);rect('#a28a56',x+77,y+7,5,10);}
      for(let row=0;row<4;row++) {
        const w=135+row*24,l=x+90-w/2,y=800-h-72+row*26;
        rect(row%2?p.leaf:p.light,l,y,w,35);
        poly('#91b879',[[l,y],[l+10,y-8],[l+w+10,y-8],[l+w,y]]);
        poly('#386b4d',[[l+w,y],[l+w+10,y-8],[l+w+10,y+25],[l+w,y+35]]);
        for(let n=0;n<11;n++) {const xx=l+noise(x+row,n)*w,yy=y+6+noise(x-row,n+4)*21;rect(n%3?'#5e8e5c':'#9dbb76',Math.round(xx/4)*4,Math.round(yy/4)*4,8,4);}
      }
      rect(p.edge,x+20,800-h-62,70,5);
    } else {
      const y=800-h;
      poly('#394a68',[[x+34,800],[x+34,y+24],[x+60,y],[x+95,y+24],[x+95,800]]);
      poly('#617fa0',[[x+34,800],[x+34,y+24],[x+60,y],[x+60,800]]);
      poly('#93bed0',[[x+60,y],[x+95,y+24],[x+75,y+17],[x+60,y+40]]);
      for(let n=0;n<7;n++)rect('#738eae',x+38+noise(x,n)*35,y+50+noise(x,n+2)*(h-65),6,3);
      poly('#b0e9ed',[[x+56,y+60],[x+50,y+3],[x+65,y-35],[x+78,y+4],[x+68,y+62]]);
      poly('#6ca4c6',[[x+65,y-35],[x+78,y+4],[x+68,y+62],[x+65,y+8]]);
      rect('#e1fcf2',x+57,y-7,4,18);
    }
  }
  rect(p.soil,0,800,map.width,200);rect(p.leaf,0,800,map.width,14);rect(p.edge,0,800,map.width,5);
  for(let x=Math.floor(camX/38)*38;x<camX+W/k+38;x+=38) {
    rect(p.bark,x,827+(Math.sin(x)*.5+.5)*22,15,6);
    rect(p.light,x+12,801,12,4);
  }
  // 지면의 작은 식물과 광물도 동일한 월드 좌표에서 재현된다.
  for(let x=Math.floor(camX/78)*78;x<camX+W/k+78;x+=78) {
    if(map.id==='forest'){
      rect('#3c7150',x+10,790,4,10);rect('#83ae6a',x+5,787,7,4);rect('#bbcc81',x+13,784,4,8);
      if(noise(x,2)>.55){rect('#e9d9ac',x+40,790,5,10);rect('#b98960',x+30,786,25,5);rect('#d3ae76',x+34,781,17,6);rect('#f4dfaa',x+38,783,4,3);}
    }else{
      poly('#86c4d6',[[x+20,800],[x+15,785],[x+22,774],[x+30,786],[x+28,800]]);
      poly('#4f89a9',[[x+22,774],[x+30,786],[x+28,800],[x+22,792]]);
      rect('#bde8ed',x+20,781,3,8);
    }
  }
  for(const plat of map.platforms) {
    rect(p.soil,plat.x1,plat.y,plat.x2-plat.x1,24);rect(p.leaf,plat.x1,plat.y,plat.x2-plat.x1,10);rect(p.edge,plat.x1,plat.y,plat.x2-plat.x1,4);
    poly(map.id==='forest'?'#49724c':'#4d6079',[[plat.x1,plat.y+24],[plat.x2,plat.y+24],[plat.x2-10,plat.y+31],[plat.x1+10,plat.y+31]]);
    for(let x=plat.x1+10;x<plat.x2;x+=55)rect(p.bark,x,plat.y+14,22,7);
  }
  for(const rope of map.ropes) {
    rect('#66513c',rope.x-2,rope.y1,4,rope.y2-rope.y1);rect('#cfb57b',rope.x-1,rope.y1,2,rope.y2-rope.y1);
    for(let y=rope.y1;y<rope.y2;y+=12)rect('#e7d19c',rope.x-3,y,6,2);
  }
  ctx.restore();
}
export function drawPortals(ctx,map,camX,camY,k,now) {
  ctx.save();ctx.setTransform(1,0,0,1,0,0);
  for(const portal of areaPortals(map)) {
    const x=(portal.x-camX)*k,y=(portal.y-camY)*k;
    ctx.fillStyle='#5c666c';ctx.fillRect(x-39*k,y-7*k,78*k,9*k);
    ctx.fillStyle='#bde8e5';ctx.fillRect(x-33*k,y-10*k,66*k,4*k);
    const glow=ctx.createRadialGradient(x,y-44*k,4*k,x,y-44*k,45*k);
    glow.addColorStop(0,'rgba(201,255,242,.65)');glow.addColorStop(1,'rgba(88,207,229,0)');ctx.fillStyle=glow;ctx.fillRect(x-45*k,y-93*k,90*k,92*k);
    for(let n=0;n<20;n++) {
      const a=n*Math.PI/10,sz=(n%3?5:7)*k;ctx.fillStyle=n%3?'#8ce6ed':'#eefcda';
      ctx.fillRect(x+Math.cos(a)*26*k-sz/2,y-44*k+Math.sin(a)*37*k-sz/2,sz,sz);
    }
    for(let n=0;n<5;n++){const t=(now/1500+n/5)%1;ctx.fillStyle=`rgba(214,255,245,${1-t})`;ctx.fillRect(x+Math.sin(n*4+t*7)*18*k,y-(10+t*75)*k,3*k,3*k);}
    ctx.font=`bold ${Math.max(10,11*k)}px system-ui`;ctx.textAlign='center';ctx.lineWidth=3*k;ctx.strokeStyle='#263f43';ctx.fillStyle='#f1fff5';
    ctx.strokeText(AREA_NAMES[portal.to],x,y-100*k);ctx.fillText(AREA_NAMES[portal.to],x,y-100*k);
  }
  ctx.restore();
}
export function minimapPoint(map,x,y,width=204,height=88) {
  return {x:8+Math.max(0,Math.min(map.width,x))/map.width*(width-16),y:8+Math.max(0,Math.min(map.height,y))/map.height*(height-16)};
}
export function drawMinimap(ctx,map,players,mobs,me,view,width=204,height=88) {
  ctx.clearRect(0,0,width,height);ctx.fillStyle='#253c3e';ctx.fillRect(0,0,width,height);
  const point=(x,y)=>minimapPoint(map,x,y,width,height);
  const line=(x1,y1,x2,y2,color)=>{const a=point(x1,y1),b=point(x2,y2);ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();};
  line(0,map.groundY,map.width,map.groundY,'#92b892');
  for(const p of map.platforms||[])line(p.x1,p.y,p.x2,p.y,'#a7c7a1');
  for(const r of map.ropes||[])line(r.x,r.y1,r.x,r.y2,'#a69476');
  if(view){const a=point(view.x,view.y),b=point(view.x+view.w,view.y+view.h);ctx.strokeStyle='#687f7e';ctx.lineWidth=1;ctx.strokeRect(a.x,a.y,b.x-a.x,b.y-a.y);}
  const dot=(x,y,color,size)=>{const a=point(x,y);ctx.fillStyle=color;ctx.fillRect(Math.round(a.x-size/2),Math.round(a.y-size/2),size,size);};
  for(const p of areaPortals(map))dot(p.x,p.y-30,'#8cdeec',5);
  for(const m of mobs)if(m.s!=='die'&&m.hp>0)dot(m.x,m.y-12,'#ed9291',2);
  for(const p of players)if(p.user_id!==me?.user_id&&sameArea(p,me))dot(p.x,p.y-24,'#eee9cf',3);
  if(me)dot(me.x,me.y-24,'#ffe578',5);
}
