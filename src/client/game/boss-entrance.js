import {regionOf} from './regions.js';
export const BOSS_ENTRANCES=Object.freeze({
 village:{color:'#e8b46e',subtitle:'작은 왕관, 커다란 심술',line:'내 버섯밭에서 소란을 피운 게 너희냐!',style:'spores'},
 quarry:{color:'#9cdde4',subtitle:'깊은 갱도가 깨어난다',line:'수정의 잠을 깨운 대가를 치러라.',style:'crystal'},
 forest:{color:'#b8d68e',subtitle:'천 년의 뿌리가 움직인다',line:'숲의 평온을… 돌려놓아라.',style:'roots'},
 frost:{color:'#c2ebfa',subtitle:'얼어붙은 왕좌의 주인',line:'이 겨울의 끝까지 버텨보아라.',style:'frost'},
});
export const ENTRANCE_DURATION=4200;
export function createBossEntrance(){
 const seen=new Set();let active=null;
 return {observe(state,area,wallNow){
  if(active&&(state?.id!==active.id||state?.phase!=='ready'||wallNow-active.at>=ENTRANCE_DURATION))active=null;
  if(state?.phase!=='ready'||state.mode!=='boss'||seen.has(state.id))return active;
  seen.add(state.id);while(seen.size>32)seen.delete(seen.values().next().value);
  const age=wallNow-state.started;
  if(age<0||age>=ENTRANCE_DURATION)return null;
  active={id:state.id,at:state.started,area,name:regionOf(area).boss,...(BOSS_ENTRANCES[area]||BOSS_ENTRANCES.village)};return active;
 },clear(){active=null;seen.clear();},get active(){return active;}};
}
export function drawBossEntrance(c,entry,point,camX,camY,k,wallNow,reduced=false){
 if(!entry)return;const age=wallNow-entry.at;if(age<0||age>=ENTRANCE_DURATION)return;
 const t=age/ENTRANCE_DURATION,fade=Math.min(1,age/300,(ENTRANCE_DURATION-age)/350);
 c.save();c.translate((point.x-camX)*k,(point.y-camY)*k);c.scale(k,k);c.globalAlpha=Math.max(0,fade)*.8;
 c.strokeStyle=entry.color;c.fillStyle=entry.color;c.lineWidth=2;
 if(entry.style==='spores'){
  for(let i=0;i<9;i++){const x=(i-4)*30,y=reduced?-35:-20-((t*100+i*17)%95);c.fillRect(x-6,y,12,5);c.fillRect(x-3,y-4,6,4);c.fillRect(x-2,y+5,4,6);}
 }else if(entry.style==='crystal'){
  for(let i=0;i<7;i++){const x=(i-3)*34,h=reduced?50:25+Math.sin(Math.PI*t)*70+i%3*12;c.beginPath();c.moveTo(x-10,0);c.lineTo(x-12,-h*.6);c.lineTo(x,-h);c.lineTo(x+12,-h*.6);c.lineTo(x+9,0);c.closePath();c.stroke();}
 }else if(entry.style==='roots'){
  for(const d of [-1,1])for(let i=0;i<3;i++){const h=reduced?65:35+Math.sin(t*Math.PI)*65;c.beginPath();c.moveTo(d*(35+i*30),0);c.bezierCurveTo(d*10,-h*.5,d*(100+i*22),-h*.8,d*(50+i*32),-h);c.stroke();c.fillRect(d*(50+i*32)-4,-h-3,8,5);}
 }else{
  for(let i=0;i<8;i++){const a=i*Math.PI/4+(reduced?0:t*.5),r=65+(reduced?0:Math.sin(t*Math.PI)*25),x=Math.cos(a)*r,y=-60+Math.sin(a)*45;c.beginPath();c.moveTo(x-6,y);c.lineTo(x+6,y);c.moveTo(x,y-6);c.lineTo(x,y+6);c.moveTo(x-4,y-4);c.lineTo(x+4,y+4);c.stroke();}
 }
 c.beginPath();c.ellipse(0,-2,145,14,0,0,Math.PI*2);c.stroke();c.restore();
}
