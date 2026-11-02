// 세 맵은 같은 방의 채팅을 공유하며 사냥/위치/호스트는 mapId로 분리한다.
export const AREA_IDS = Object.freeze(['village', 'quarry', 'forest', 'frost']);
export const normalizeMapId = (id) => AREA_IDS.includes(id) ? id : 'village';
export const AREA_NAMES = Object.freeze({ village: '버섯마을', forest: '이끼마을', quarry: '광산마을', frost:'서리마을' });
export function areaMap(id, village) {
  id = normalizeMapId(id);
  if(id==='village'){
   const edge=village.width||3840,extra=[{id:'outskirts-step',x1:edge+60,x2:edge+390,y:650},{id:'outskirts-canopy',x1:edge+460,x2:edge+850,y:590},{id:'outskirts-east',x1:edge+920,x2:edge+1200,y:630}];
   return {...village,id,name:AREA_NAMES[id],artWidth:edge,width:edge+1380,platforms:[...(village.platforms||[]),...extra],ropes:[...(village.ropes||[]),...extra.map((p,i)=>({id:p.id+'-rope',x:(p.x1+p.x2)/2,y1:p.y,y2:800}))],
    districts:[{x:1647,name:'버섯마을 광장'},{x:edge+210,name:'그루터기 산책길'},{x:edge+680,name:'철갑버섯 숲'}],
    spawns:[...(village.spawns||[]).slice(0,18).map((z,i)=>({...z,mobs:[['snail','mushroom','slime'][i%3]],max:Math.min(3,z.max||2)})),{id:'outskirts-ground',platform:'ground',x1:edge+60,x2:edge+1250,mobs:['wild-stump','armored-mushroom'],max:4},...extra.map((p,i)=>({id:p.id+'-mobs',platform:p.id,x1:p.x1+30,x2:p.x2-30,mobs:[i===1?'armored-mushroom':'wild-stump'],max:2}))]};
  }
  const forest=id==='forest',width=id==='frost'?6000:forest?5400:4800;
  const platforms=forest?[
   {id:'root-step',x1:420,x2:950,y:665},{id:'west-canopy',x1:1050,x2:1530,y:510},{id:'ancient-bough',x1:1730,x2:2220,y:330},{id:'hollow-root',x1:2400,x2:2850,y:650},{id:'thorn-perch',x1:3050,x2:3540,y:480},{id:'treant-crown',x1:3750,x2:4200,y:305},{id:'east-root',x1:4450,x2:4930,y:635}
  ]:[{id:'entry-rail',x1:440,x2:990,y:655},{id:'crystal-shelf',x1:1130,x2:1610,y:495},{id:'mine-lift',x1:1800,x2:2310,y:345},{id:'lower-rail',x1:2490,x2:2980,y:650},{id:'sentinel-post',x1:3200,x2:3690,y:475},{id:'deep-crystal',x1:3890,x2:4350,y:625}];
  if(id==='frost')platforms.push({id:'glacier-throne',x1:4700,x2:5280,y:480},{id:'snow-east',x1:5430,x2:5790,y:650});
  for(const p of [...platforms]){if(p.y<600)for(let y=650;y>p.y;y-=175)platforms.push({id:p.id+'-step-'+y,x1:p.x1-55,x2:p.x1+115,y});}
  const ropes=platforms.filter(p=>!p.id.includes('-step-')).map(p=>({id:p.id+'-rope',x:(p.x1+p.x2)/2,y1:p.y,y2:800}));
  const monsters=id==='frost'?['frost-slime','ice-crab','ice-golem','frost-beetle','glacier-sentinel']:forest?['moss-slime','forest-stump','moss-guardian','thorn-mantis','ancient-treant']:['bat','crystal-crab','golem','ore-beetle','cave-sentinel'];
  return {id,name:AREA_NAMES[id],layers:[],width,height:1000,groundY:800,spawn:{x:900,y:800},platforms,ropes,
   districts:id==='frost'?[{x:650,name:'눈송이 초입'},{x:2400,name:'얼어붙은 광장'},{x:4700,name:'빙하 군주의 봉인'}]:forest?[{x:650,name:'이끼 뿌리길'},{x:2000,name:'고목의 가지'},{x:4000,name:'고대 정령의 숲'}]:[{x:650,name:'광산 입구'},{x:2100,name:'수정 채굴장'},{x:3700,name:'파수꾼의 갱도'}],
   spawns:[{id:'entry-ground',platform:'ground',x1:1400,x2:2100,mobs:monsters.slice(0,2),max:4},{id:'middle-ground',platform:'ground',x1:2350,x2:3300,mobs:monsters.slice(1,4),max:4},{id:'elite-ground',platform:'ground',x1:3500,x2:width-350,mobs:monsters.slice(3),max:4},...platforms.filter(p=>!p.id.includes('-step-')).map((p,i)=>({id:p.id+'-mobs',platform:p.id,x1:p.x1+35,x2:p.x2-35,mobs:[monsters[Math.min(4,Math.floor(p.x1/width*5))]],max:2}))]};

}
export function areaPortals(map) {
  const i=AREA_IDS.indexOf(normalizeMapId(map.id));
  return [...(i>0?[{id:'left',x:100,y:map.groundY,to:AREA_IDS[i-1],entry:'right'}]:[]),
    ...(i<AREA_IDS.length-1?[{id:'right',x:map.width-100,y:map.groundY,to:AREA_IDS[i+1],entry:'left'}]:[])];
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
  const p=map.id==='frost'?{...palettes.quarry,sky:'#5b819d',haze:'#d8eff5',soil:'#657d93',edge:'#e4fbff',leaf:'#a1cbdc'}:palettes[map.id]||palettes.forest;
  ctx.setTransform(1,0,0,1,0,0);ctx.save();ctx.imageSmoothingEnabled=false;
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
  // Background landmarks stay behind combatants and clear of the rope/portal hit areas.
  for(let x=Math.floor((camX-400)/680)*680;x<camX+W/k+400;x+=680){
    if(map.id==='quarry'){
      rect('#202b43',x+100,615,245,185);
      for(const xx of [x+88,x+333]){rect('#403b40',xx,598,18,202);rect('#89745d',xx+3,604,6,196);for(let y=625;y<790;y+=45)rect('#b29a76',xx+1,y,16,5);}
      rect('#453d43',x+74,589,290,24);rect('#b09a77',x+80,589,278,6);
      poly('#65574b',[[x+107,613],[x+145,650],[x+150,642],[x+120,613]]);
      poly('#65574b',[[x+324,613],[x+285,650],[x+279,642],[x+311,613]]);
      rect('#4e5666',x+126,772,190,6);rect('#b0b4ac',x+126,772,190,2);
      for(let xx=x+130;xx<x+310;xx+=31)rect('#766554',xx,777,15,6);
      const lampX=x+211;
      rect('#cda66c22',lampX-37,620,74,92);rect('#e7ba6822',lampX-24,636,48,58);
      rect('#6d655d',lampX-2,611,4,29);rect('#353b4c',lampX-10,637,20,27);rect('#ffd48a',lampX-6,643,12,14);rect('#fff1c1',lampX-3,643,5,10);
      rect('#343b4d',x+381,757,62,32);rect('#788f9f',x+385,761,54,21);rect('#b0c8cb',x+385,757,54,5);
      for(const xx of [x+393,x+428]){rect('#222e40',xx-6,787,12,12);rect('#9c9988',xx-2,790,4,5);}
      poly('#79c4ca',[[x+396,756],[x+399,739],[x+407,733],[x+417,747],[x+424,738],[x+435,757]]);
    }else{
      // Ruined arch and roots make the deeper woods readable without foreground occlusion.
      for(const xx of [x+130,x+290]){rect('#687b69',xx,684,29,116);rect('#a0ac87',xx,684,8,110);for(let y=708;y<790;y+=28)rect('#4a6256',xx+1,y,27,3);rect('#477b54',xx-5,680,40,9);}
      rect('#607b69',x+126,675,197,18);rect('#b4bf95',x+130,675,189,5);
      rect('#517b55',x+144,693,7,36);rect('#84a66e',x+148,714,10,5);rect('#84a66e',x+143,702,8,4);
      rect('#536c59',x+208,690,31,37);rect('#a8bd88',x+217,699,13,16);rect('#dae1b2',x+222,702,4,10);
      for(let n=0;n<4;n++){const xx=x+390+n*26;rect('#5c503d',xx,790-n*4,38,10+n*4);rect('#927c56',xx,788-n*4,30,4);rect('#6e9b62',xx+4,784-n*4,20,5);}
      rect('#eddbb5',x+423,770,5,20);rect('#aa6570',x+411,763,29,8);rect('#d89898',x+416,758,19,7);rect('#f8e3c4',x+420,760,5,3);
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

export function drawRegionLandmarks(ctx,map,camX,camY,k){
 ctx.save();for(const d of map.districts||[]){const x=(d.x-camX)*k,y=(map.groundY-camY)*k;if(x<-180*k||x>ctx.canvas.width+180*k)continue;ctx.fillStyle='#6d5845';ctx.fillRect(x-3*k,y-62*k,6*k,62*k);ctx.fillStyle='#e3d5b3';ctx.fillRect(x-65*k,y-65*k,130*k,25*k);ctx.fillStyle='#5b6d57';ctx.fillRect(x-65*k,y-65*k,130*k,3*k);ctx.font=`600 ${10*k}px system-ui`;ctx.textAlign='center';ctx.fillStyle='#3a5145';ctx.fillText(d.name,x,y-49*k);}
 ctx.restore();
}
export function drawVillageOutskirts(ctx,map,camX,camY,k,W,H){
 if(map.id!=='village'||!map.artWidth||camX+W/k<map.artWidth)return;ctx.save();ctx.beginPath();ctx.rect(Math.max(0,(map.artWidth-camX)*k),0,W,H);ctx.clip();drawBiomeMap(ctx,{...map,id:'forest',platforms:map.platforms.filter(p=>p.x1>=map.artWidth),ropes:map.ropes.filter(r=>r.x>=map.artWidth)},camX,camY,k,W,H);ctx.restore();
}
