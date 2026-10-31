import {bossImpactAt,bossStrikePoint} from './garden-boss.js';
// Small faceted blocks share the map's stepped silhouettes and three-face shading.
function block(c,x,y,w,h,d,front,top,side){
 c.fillStyle=front;c.fillRect(x,y,w,h);
 c.fillStyle=top;c.beginPath();c.moveTo(x,y);c.lineTo(x+d,y-d);c.lineTo(x+w+d,y-d);c.lineTo(x+w,y);c.closePath();c.fill();
 c.fillStyle=side;c.beginPath();c.moveTo(x+w,y);c.lineTo(x+w+d,y-d);c.lineTo(x+w+d,y+h-d);c.lineTo(x+w,y+h);c.closePath();c.fill();
}
function littleMushroom(c,x,y,s=1){block(c,x-3*s,y-6*s,6*s,6*s,2*s,'#e6d4a0','#fff0be','#b29c6d');block(c,x-8*s,y-11*s,16*s,5*s,2*s,'#b56346','#e6a465','#824c37');block(c,x-5*s,y-14*s,10*s,3*s,2*s,'#c98051','#f3bd7e','#945b3c');c.fillStyle='#f8e5b0';c.fillRect(x-3*s,y-11*s,3*s,2*s);}
export function drawBoss(c,m,x,y,k,now,pose=null){
 const height=pose?.height??0,step=pose?.step??Math.sin(now/120)*.3,squash=pose?.squash??1,dir=pose?.dir??m.dir??1;
 c.save();c.translate(x,y);c.scale(k,k);
 c.fillStyle='#283c3538';c.fillRect(-52,height-3,104,8);c.fillStyle='#26382e28';c.fillRect(-66,height,132,5);
 c.scale(1/squash,squash);
 // Feet and arms visibly stride; cloak sits behind the cream stem body.
 block(c,-45,-61,82,48,7,'#47674a','#6e8e5c','#2e4c38');
 block(c,-34,-16+step*5,25,15,7,'#a69262','#ddcc9b','#776b4c');block(c,12,-16-step*5,25,15,7,'#a69262','#ddcc9b','#776b4c');
 block(c,-39,-91,76,72,10,'#decea0','#f6e9bb','#a99b70');block(c,-33,-85,13,61,2,'#e9d9a9','#f9edc4','#c3b284');
 block(c,-51,-66-step*4,15,32,6,'#cbbb8f','#eee0af','#968660');block(c,40,-66+step*4,15,32,6,'#cbbb8f','#eee0af','#968660');
 // Four terraces instead of an ellipse: broad cap rim, body, upper cap and ridge.
 block(c,-80,-101,157,13,8,'#9c5439','#e5a665','#74432f');
 block(c,-71,-118,139,17,8,'#bd7047','#e9aa6a','#8f5135');
 block(c,-53,-132,102,14,8,'#cc8652','#f0ba79','#9b603c');
 block(c,-26,-141,49,9,8,'#d9995e','#f6ce8a','#a66b41');
 for(const [px,py,w]of [[-54,-112,15],[-8,-126,21],[39,-111,13]])block(c,px,py,w,5,3,'#f2deb0','#fff0c7','#cfb78b');
 // Mushroom circlet: low gold band crowned by tiny stepped mushroom ornaments.
 block(c,-32,-142,62,6,5,'#bc9147','#f5d58b','#8f6c35');
 for(const [px,py,s]of [[-23,-143,.8],[0,-146,1.1],[23,-143,.8]])littleMushroom(c,px,py,s);
 const face=dir<0?-4:4;c.fillStyle='#283e31';c.fillRect(face-20,-72,7,10);c.fillRect(face+13,-72,7,10);c.fillStyle='#fff4d2';c.fillRect(face-19,-71,2,3);c.fillRect(face+14,-71,2,3);
 c.fillStyle='#a9704b';c.fillRect(face-5,-53,12,3);c.fillRect(face-8,-56,3,3);c.fillRect(face+7,-56,3,3);
 block(c,49,-66+step*4,5,62,2,'#806843','#baa46e','#574a35');littleMushroom(c,51,-66+step*4,.9);
 if(m.s==='hit'){c.fillStyle='#fff2c520';c.fillRect(-39,-91,76,72);}
 c.restore();
}
export function drawBossTelegraph(c,b,arena,camX,camY,k,now){
 if(!b||b.pattern==='exposed')return;
 const point=bossStrikePoint(b,arena),age=now-bossImpactAt(b);if(now<b.at||age>550)return;
 c.save();c.translate((point.x-camX)*k,(point.y-camY)*k);c.scale(k,k);
 c.fillStyle=age>=0?'#edc681a3':'#c96a4850';c.strokeStyle='#ffe2a1';c.lineWidth=2;
 if(b.pattern==='spores'){
   const x=b.targetX-point.x;c.fillRect(x-105,-7,210,13);c.strokeRect(x-105,-7,210,13);
   if(age>=0)for(let i=0;i<7;i++)block(c,x-96+i*30,-80-(i%3)*35,12,12,4,'#b294ba','#ead4e9','#7b6389');
 }else if(b.pattern==='stomp'){
   c.fillRect(-210,-7,420,13);c.strokeRect(-210,-7,420,13);
   c.fillStyle='#ffe1a6';c.fillRect(-4,-20,8,18);c.fillRect(-4,-30,8,6);
   if(age>=0)for(let i=0;i<9;i++){const px=-200+i*50;block(c,px,-12-(i%3)*9,14,10,4,'#ae8557','#f4d18b','#795b43');}
 }else{
   for(const x of[-590,145]){c.fillRect(x,-7,445,13);c.strokeRect(x,-7,445,13);}c.strokeStyle='#a8dd8e';c.strokeRect(-140,-7,280,13);
 }
 c.restore();
}
