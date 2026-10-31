import { gardenPoint, gardenActive } from './garden.js';
export function drawGarden(ctx,world,state,camX,camY,k,now) {
  const p=gardenPoint(world),x=(p.x-camX)*k,y=(p.y-camY)*k;
  if(x < -180*k || x>ctx.canvas.width+180*k)return;
  ctx.save();ctx.translate(x,y);ctx.scale(k,k);
  const active=gardenActive(state);
  ctx.fillStyle=active?'#89d77a35':'#f6e4ac40';ctx.beginPath();ctx.ellipse(0,-3,110,20,0,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle=state?.hp===0?'#986755':'#9bc381';ctx.lineWidth=2;ctx.setLineDash([5,6]);ctx.beginPath();ctx.ellipse(0,-3,108,20,0,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);
  for(let i=0;i<5;i++) {
    const px=(i-2)*32,py=-5+(i%2)*7;
    ctx.fillStyle='#eddec1';ctx.fillRect(px-4,py-22,8,20);
    ctx.fillStyle=state?.hp===0?'#99866a':i%2?'#e7ae58':'#de8765';ctx.beginPath();ctx.ellipse(px,py-23,15,11,0,Math.PI,Math.PI*2);ctx.fill();
    ctx.fillStyle='#fff2d7';ctx.beginPath();ctx.arc(px-5,py-27,2.5,0,Math.PI*2);ctx.arc(px+5,py-29,2,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#628549';ctx.beginPath();ctx.ellipse(px+7,py-4,8,3,-.6,0,Math.PI*2);ctx.fill();
  }
  ctx.fillStyle='#fff8e4';ctx.strokeStyle='#6d8d50';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(-61,-81,122,24,6);ctx.fill();ctx.stroke();
  ctx.fillStyle='#47633d';ctx.font='700 10px system-ui';ctx.textAlign='center';ctx.fillText('함께 지키는 버섯밭',0,-65);
  if(active){ctx.fillStyle='#37513a';ctx.fillRect(-45,-51,90,5);ctx.fillStyle=state.hp>40?'#a2d579':'#f0a16d';ctx.fillRect(-45,-51,90*state.hp/100,5);}
  ctx.restore();
}
export function drawGardenTitle(ctx,text,x,y) {
  ctx.save();ctx.font='700 10px system-ui';ctx.textAlign='center';const w=ctx.measureText(text).width+20;
  ctx.fillStyle='#e6f3d8';ctx.strokeStyle='#82a66e';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(x-w/2,y,w,17,7);ctx.fill();ctx.stroke();ctx.fillStyle='#486b39';ctx.fillText(text,x,y+12);ctx.restore();
}
export function drawGardenInvader(ctx,m,camX,camY,k) {
  const x=(m.x-camX)*k,y=(m.y-camY)*k;
  ctx.save();ctx.strokeStyle=m.kind==='garden-runner'?'#ed8b69':m.kind==='garden-guard'?'#9dc9d1':'#e7b85d';ctx.lineWidth=2*k;ctx.beginPath();ctx.ellipse(x,y-2*k,24*k,6*k,0,0,Math.PI*2);ctx.stroke();
  ctx.fillStyle='#ffde8a';ctx.beginPath();ctx.moveTo(x-5*k,y-(m.spec.size.h+15)*k);ctx.lineTo(x+5*k,y-(m.spec.size.h+15)*k);ctx.lineTo(x,y-(m.spec.size.h+7)*k);ctx.closePath();ctx.fill();if(m.kind==='garden-runner'||m.kind==='garden-guard'){ctx.font=`700 ${9*k}px system-ui`;ctx.textAlign='center';ctx.fillStyle=m.kind==='garden-runner'?'#f6b097':'#c1e0e7';ctx.fillText(m.kind==='garden-runner'?'급습':'강화',x,y-(m.spec.size.h+22)*k);}ctx.restore();
}
