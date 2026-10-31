import {bossImpactAt,bossPatternText} from './garden-boss.js';
export function drawBoss(c,m,x,y,k,now){
 c.save();c.translate(x,y);c.scale(k,k);const bob=Math.sin(now/300)*2;
 c.fillStyle='#1b38254d';c.beginPath();c.ellipse(0,-2,80,18,0,0,Math.PI*2);c.fill();
 const body=c.createLinearGradient(-45,0,45,0);body.addColorStop(0,'#c6bd94');body.addColorStop(.35,'#fff1cb');body.addColorStop(1,'#b5b17d');c.fillStyle=body;c.strokeStyle='#6e6740';c.lineWidth=2;c.beginPath();c.roundRect(-47,-96+bob,94,93,24);c.fill();c.stroke();
 c.fillStyle='#6f9c5b';c.beginPath();c.moveTo(-53,-66);c.lineTo(-67,-12);c.lineTo(-34,-5);c.lineTo(-24,-56);c.closePath();c.fill();
 const cap=c.createRadialGradient(-20,-130,3,0,-95,90);cap.addColorStop(0,'#e6ac71');cap.addColorStop(.65,'#bf714b');cap.addColorStop(1,'#80533d');c.fillStyle=cap;c.beginPath();c.ellipse(0,-95+bob,82,45,0,Math.PI,Math.PI*2);c.fill();c.strokeStyle='#efbf7a';c.lineWidth=5;c.beginPath();c.ellipse(0,-96+bob,80,12,0,0,Math.PI*2);c.stroke();
 c.fillStyle='#fff1c9';for(const [a,b,r] of [[-42,-117,10],[4,-128,13],[45,-114,8]]){c.beginPath();c.ellipse(a,b+bob,r,r*.55,0,0,Math.PI*2);c.fill();}
 c.fillStyle='#e9bd5f';c.beginPath();c.moveTo(-27,-135);c.lineTo(-32,-162);c.lineTo(-13,-153);c.lineTo(0,-173);c.lineTo(14,-153);c.lineTo(32,-162);c.lineTo(27,-135);c.closePath();c.fill();c.strokeStyle='#9a733c';c.lineWidth=2;c.stroke();
 c.fillStyle='#293a2f';for(const a of [-17,17]){c.beginPath();c.ellipse(a,-66+bob,5,8,0,0,Math.PI*2);c.fill();}c.strokeStyle='#7a4c37';c.lineWidth=3;c.beginPath();c.arc(0,-49+bob,10,0,Math.PI);c.stroke();
 c.fillStyle='#759657';c.fillRect(42,-64,8,70);c.fillStyle='#edcf87';c.beginPath();c.arc(46,-74,13,0,Math.PI*2);c.fill();c.restore();
}
export function drawBossTelegraph(c,b,point,camX,camY,k,now){
 if(!b)return;const impact=bossImpactAt(b),age=now-impact;if(b.pattern==='exposed')return;
 if(now<b.at||age>500)return;
 const pulse=.2+.15*Math.sin(now/100);c.save();c.translate((point.x-camX)*k,(point.y-camY)*k);c.scale(k,k);
 c.fillStyle=age>=0?'#f3d790b3':`rgba(221,104,71,${pulse})`;c.strokeStyle='#ffe0a1';c.lineWidth=2;
 if(b.pattern==='spores'){const x=b.targetX-point.x;c.fillRect(x-105,-8,210,14);c.strokeRect(x-105,-8,210,14);if(age>=0){c.fillStyle='#cfb9e9cc';for(let i=0;i<7;i++){c.beginPath();c.arc(x-90+i*30,-70-(i%3)*40,12,0,Math.PI*2);c.fill();}}}
 else if(b.pattern==='stomp'){c.fillRect(-210,-8,420,14);c.strokeRect(-210,-8,420,14);if(age>=0){c.beginPath();c.ellipse(0,-5,210,45,0,Math.PI,2*Math.PI);c.stroke();}}
 else{for(const x of [-590,145]){c.fillRect(x,-8,445,14);c.strokeRect(x,-8,445,14);}c.strokeStyle='#a8dd8e';c.strokeRect(-140,-8,280,14);}
 c.restore();
}
