// Cosmetic scenery only: no collisions, rewards or per-frame allocations outside visible props.
export const REGION_CHARACTER = Object.freeze({
 village:{name:'포포',role:'길 잃은 버섯 배달부',color:'#df8b67',accent:'#f1c86e',tag:'버섯 우편국'},
 quarry:{name:'딱콩',role:'수정에 진심인 두더지',color:'#a896bd',accent:'#8fe1e4',tag:'딱콩의 야간 작업장'},
 forest:{name:'루미',role:'졸음 많은 새싹 정령',color:'#96c9a3',accent:'#e2eaa0',tag:'낮잠 정령의 쉼터'},
 frost:{name:'보송',role:'추위를 타는 눈요정',color:'#d3e8ec',accent:'#eaa483',tag:'따뜻한 눈송이 쉼터'},
});
export function drawMascot(c,area,x,y,k=1,now=0,{reduced=false}={}) {
 const s=REGION_CHARACTER[area]||REGION_CHARACTER.village,t=reduced?0:now/1000,bob=Math.sin(t*2.5)*2;
 c.save();c.translate(x,y);c.scale(k,k);
 const r=(color,x,y,w,h)=>{c.fillStyle=color;c.fillRect(x,y,w,h);};
 c.fillStyle='#11263535';c.beginPath();c.ellipse(0,1,26,5,0,0,Math.PI*2);c.fill();c.translate(0,bob);
 r('#26384a',-21,-44,42,42);r(s.color,-18,-43,36,38);r('#ffffff38',-15,-40,11,8);
 r(s.color,-15,-7,10,9);r(s.color,6,-7,10,9);r('#26384a',-28,-27,8,16);r(s.color,-27,-28,8,13);r(s.color,20,-28+Math.sin(t*3)*2,8,13);
 if(area==='village'){r('#784b46',-33,-49,66,13);r(s.color,-28,-63,56,19);r('#fce9bc',-20,-58,10,7);r('#fce9bc',7,-54,12,8);r('#bb714e',-26,-13,14,21);r('#f3d590',-24,-12,10,3);}
 if(area==='quarry'){r('#b98549',-25,-49,50,9);r('#e2b76b',-19,-59,38,14);r('#384459',-9,-53,18,12);r(s.accent,-5,-51,10,7);r('#6b607b',-25,-23,50,5);r('#b7e7ed',-13,-26,10,9);r('#b7e7ed',4,-26,10,9);}
 if(area==='forest'){r('#527e59',-3,-57,6,16);r('#a9d38c',0,-66,23,12);r('#d8e7a4',-18,-61,18,9);r('#667c53',-22,-11,44,6);r('#e1eaa5',-5,-14,10,10);}
 if(area==='frost'){r(s.color,-16,-54,10,15);r(s.color,7,-57,10,18);r(s.accent,-23,-13,46,9);r(s.accent,12,-5,8,20);r('#ffe1b4',11,8,10,4);}
 const blink=!reduced&&now%4100>3920;
 r('#243248',-10,-31,5,blink?2:7);r('#243248',6,-31,5,blink?2:7);
 if(!blink){r('#fff9e3',-9,-31,2,2);r('#fff9e3',7,-31,2,2);}
 r('#e2a39b',-15,-21,6,3);r('#e2a39b',11,-21,6,3);r('#425265',-3,-20,7,2);r('#425265',0,-18,3,2);
 c.restore();
}
export function drawAdventureScenery(c,map,camX,camY,k,now,{reduced=false}={}) {
 const area=REGION_CHARACTER[map.id]?map.id:'village',s=REGION_CHARACTER[area],ground=map.groundY;
 c.save();c.translate(-camX*k,-camY*k);c.scale(k,k);
 const r=(color,x,y,w,h)=>{c.fillStyle=color;c.fillRect(x,y,w,h);};
 const base=(map.spawn?.x??900)-330;
 // A landmark behind each mascot gives the entry a recognisable silhouette.
 if(base+130>camX&&base-130<camX+c.canvas.width/k){
   const x=base-85,y=ground;
   if(area==='village'){
     r('#59484a',x-15,y-62,33,62);r('#b56050',x-25,y-92,53,59);r('#eaa777',x-21,y-88,45,49);r('#6a4644',x-16,y-77,35,6);r('#f7dfb3',x-9,y-62,21,16);r('#bd785b',x-5,y-58,13,2);r('#d6a167',x+24,y-91,5,24);r('#b45148',x+28,y-91,17,10);
   }else if(area==='quarry'){
     r('#343c52',x-24,y-65,70,54);r('#657285',x-20,y-61,62,39);r('#cfac63',x-20,y-61,62,7);r('#2c3146',x-23,y-13,18,14);r('#2c3146',x+25,y-13,18,14);r('#9cd5dc',x-7,y-53,13,21);r('#9cd5dc',x+15,y-46,12,14);r('#e9e6b5',x-3,y-54,3,15);
   }else if(area==='forest'){
     r('#50644a',x-26,y-126,65,125);r('#7e8960',x-20,y-119,53,115);r('#465c49',x-17,y-76,15,3);r('#465c49',x+13,y-76,15,3);r('#475e47',x+2,y-59,11,9);r('#a3aa77',x-24,y-59,15,5);r('#a3aa77',x+23,y-59,15,5);
     for(let i=0;i<3;i++){r('#49765c',x-46+i*8,y-153-i*15,100-i*12,30);r('#7ba46e',x-41+i*8,y-154-i*15,76-i*12,7);}
   }else{
     r('#86a6ba',x-38,y-72,83,70);r('#d0e7e9',x-33,y-80,73,71);r('#e2f1ef',x-21,y-128,50,57);r('#303e59',x-9,y-108,5,7);r('#303e59',x+14,y-108,5,7);r('#e2a06b',x+1,y-99,16,5);r('#9b6e77',x-24,y-130,55,7);r('#56627c',x-16,y-154,39,25);r('#dfa28d',x-27,y-82,62,12);r('#dfa28d',x+17,y-70,12,35);r('#f2d1a4',x+17,y-42,12,5);
   }
 }
 const first=180+Math.max(0,Math.floor((camX-280)/600))*600;
 for(let x=first;x<Math.min(map.width-120,camX+c.canvas.width/k+100);x+=600){
   const phase=reduced?0:Math.sin(now/650+x)*3;
   if(area==='village'){
     r('#735845',x,ground-124,7,124);r('#eac580',x-6,ground-127,19,5);
     c.fillStyle=x%1200<600?'#d87d64':'#6faaa2';c.beginPath();c.moveTo(x+7,ground-121);c.lineTo(x+65,ground-115+phase);c.lineTo(x+52,ground-92+phase);c.lineTo(x+7,ground-94);c.fill();r('#f6e6b4',x+22,ground-113,9,12);
   }else if(area==='quarry'){
     r('#30364f',x-23,ground-6,56,7);for(let i=0;i<3;i++){r('#526b91',x+i*14-18,ground-35-i*12,11,33+i*12);r(s.accent,x+i*14-15,ground-34-i*12,3,25+i*12);}r('#d6eeee',x+10,ground-61+phase,3,3);
   }else if(area==='forest'){
     r('#6b6950',x,ground-96,6,96);r('#7c8260',x+4,ground-96,30,4);r('#526f5b',x+23,ground-93,2,19);r('#d5e4a0',x+14,ground-75+phase,22,20);r('#f7efb8',x+19,ground-72+phase,7,11);
   }else{
     r('#7197b3',x,ground-113,6,113);r('#c7ecf1',x-8,ground-116,53,5);r('#abc8d7',x+30,ground-110,2,20);r('#e0f6f4',x+23,ground-90+phase,18,21);r('#89bcd1',x+27,ground-86+phase,5,10);r('#e7c587',x+29,ground-64+phase,5,5);
   }
 }
 c.restore();
}
// Mascots are sorted with actors by foot height. Their labels describe scenery, not quests.
export function drawRegionMascot(c,map,camX,camY,k,now,options={}) {
 const area=REGION_CHARACTER[map.id]?map.id:'village',s=REGION_CHARACTER[area],x=(map.spawn?.x??900)-330,y=map.groundY;
 if((x-camX)*k<-120*k||(x-camX)*k>c.canvas.width+120*k)return;
 drawMascot(c,area,(x-camX)*k,(y-camY)*k,k,now,options);
 c.save();c.translate((x-camX)*k,(y-camY)*k);c.scale(k,k);c.font='700 10px system-ui';c.textAlign='center';c.fillStyle='#15283ae8';c.fillRect(-66,10,132,20);c.fillStyle='#f4ddb0';c.fillText(`${s.name} · ${s.tag}`,0,24);c.restore();
}
export function drawAdventureCharm(c,x,y,k,{fit,left=false,hidden=false,job='warrior',now=0,moving=false,reduced=false}={}) {
 if(hidden||!fit)return;
 const colors={warrior:'#df8b67',archer:'#88bd94',mage:'#ae9dd5',thief:'#82b8cb'},color=colors[job]||colors.warrior;
 c.save();c.translate(x,y);c.scale(left?-k:k,k);const neck=fit.neck,body=fit.bodyX||0,wave=moving&&!reduced?Math.sin(now/95)*2:0;
 c.fillStyle='#3d3949';c.fillRect(body-12,-neck+1,24,6);c.fillStyle=color;c.fillRect(body-11,-neck,22,4);c.fillRect(body-15,-neck+3,6,12+wave);c.fillStyle='#f1d69b';c.fillRect(body-14,-neck+12+wave,5,3);c.restore();
}
