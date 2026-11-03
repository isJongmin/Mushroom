export function traitAuraStyle(allocation){
 const a=allocation||{},points=['attack','health','technique'].reduce((n,k)=>n+(Number.isInteger(a[k])&&a[k]>=0&&a[k]<=10?a[k]:0),0),kind=['attack','health','technique'].sort((x,y)=>(a[y]||0)-(a[x]||0))[0];
 return {points,color:({attack:'#f3ce81',health:'#a8df9b',technique:'#9bdce9'})[kind]};
}
export function drawTraitAura(c,x,y,k,allocation,now,{burstAge=Infinity,reduced=false,front=false}={}){
 const {points,color}=traitAuraStyle(allocation),burst=Number.isFinite(burstAge)&&burstAge>=0&&burstAge<1600,fade=burst?1-burstAge/1600:0;if(!points&&!burst)return;
 c.save();c.translate(x,y-37*k);c.scale(k,k);const pulse=reduced?0:Math.sin(now/520)*2;
 if(!front){const alpha=.12+Math.min(15,points)*.004+fade*.2,g=c.createRadialGradient(0,0,6,0,0,58);g.addColorStop(0,color);g.addColorStop(1,color+'00');c.globalAlpha=alpha;c.fillStyle=g;c.fillRect(-60,-66,120,125);c.globalAlpha=.42+fade*.4;c.strokeStyle=color;c.lineWidth=burst?2:1;c.beginPath();c.ellipse(0,0,22+pulse+fade*10,43+fade*8,0,0,Math.PI*2);c.stroke();}
 else{c.strokeStyle=color;c.globalAlpha=.35+fade*.5;c.lineWidth=1.2;c.beginPath();c.ellipse(0,35,27+fade*12,7,0,0,Math.PI*2);c.stroke();if(!reduced)for(let i=0;i<(burst?10:4);i++){const a=now/1100+i*2.4,r=24+fade*13;c.fillStyle=color;c.fillRect(Math.cos(a)*r-1,Math.sin(a)*36-1,2,3);}}
 c.restore();
}
