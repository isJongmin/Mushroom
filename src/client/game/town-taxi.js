import {AREA_IDS,AREA_NAMES} from './areas.js';
import {stageUnlocked,stageOf,GRADES} from './progression.js';
export const TAXI_DRIVER=Object.freeze({name:'기사 달콩',avatar:{hair:'espresso-crop',hat:'cap-black',top:'varsity-navy',bottom:'pants-navy',shoes:'hightop-black',skin:'medium',face:'wink'}});
export const TAXI_MARKER_HEIGHT=165;
// A dedicated western stop, clear of the mentor/pet/quest line and entry portal labels.
export const taxiPoint=map=>({x:Math.max(245,Math.min(map.width-140,(map.spawn?.x??900)-800)),y:map.groundY});
export function taxiDestinations(state,job,current){return AREA_IDS.map(id=>({id,name:AREA_NAMES[id],current:id===current,unlocked:!!state&&stageUnlocked(state,job,id),requirement:`${GRADES[stageOf(id).recommended]} 주무기 획득`}));}
export function taxiTravelReason({state,job,current,to,player,map,connected=true,now=0,readyAt=0}){
 if(!connected)return '연결을 기다려주세요.';if(!player||player.dead)return '살아 있는 상태에서 택시를 이용하세요.';
 if(now<readyAt)return '잠시 후 다시 이용하세요.';const p=taxiPoint(map);if(Math.abs(player.x-p.x)>160||Math.abs(player.y-p.y)>85)return '택시 가까이로 이동해주세요.';
 if(!AREA_IDS.includes(to))return '목적지를 선택하세요.';if(to===current)return '현재 있는 마을입니다.';
 if(!state||!stageUnlocked(state,job,to))return `${GRADES[stageOf(to).recommended]} 이상 주무기를 먼저 획득하세요.`;
 return '';
}
// Three-face blocks and bevelled wheels match the village's voxel art.
function block(c,x,y,w,h,d,front,top,side){
 c.fillStyle=front;c.fillRect(x,y,w,h);
 c.fillStyle=top;c.beginPath();c.moveTo(x,y);c.lineTo(x+d,y-d);c.lineTo(x+w+d,y-d);c.lineTo(x+w,y);c.closePath();c.fill();
 c.fillStyle=side;c.beginPath();c.moveTo(x+w,y);c.lineTo(x+w+d,y-d);c.lineTo(x+w+d,y+h-d);c.lineTo(x+w,y+h);c.closePath();c.fill();
}
function wheel(c,x,y){
 c.save();c.translate(x,y);c.fillStyle='#1e293c';c.beginPath();c.moveTo(-14,-9);c.lineTo(-8,-15);c.lineTo(9,-15);c.lineTo(16,-8);c.lineTo(16,9);c.lineTo(9,16);c.lineTo(-8,16);c.lineTo(-14,9);c.closePath();c.fill();
 block(c,-10,-11,20,23,3,'#46566a','#758297','#172536');block(c,-6,-7,12,14,2,'#c7ac75','#f7dfa2','#857047');c.fillStyle='#f7eed5';c.fillRect(-2,-3,5,6);c.restore();
}
export function drawTaxiDriverPortrait(cv,renderer,avatar){
 const c=cv.getContext('2d');c.clearRect(0,0,cv.width,cv.height);
 renderer?.draw(c,avatar,cv.width/2,cv.height-6,1.65,0,false);
}
export function drawTownTaxi(c,map,camX,camY,k,now,reduced=false,{renderer,avatar}={}){
 const p=taxiPoint(map),x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-180*k||x>c.canvas.width+180*k)return;
 c.save();c.translate(x,y);c.scale(k,k);
 const r=(col,x,y,w,h)=>{c.fillStyle=col;c.fillRect(x,y,w,h);};
 // Paving, kerb and a brass taxi-stop pole. No collision or hit areas are added.
 block(c,-100,2,202,7,8,'#536474','#a3b0ad','#334655');
 for(let i=0;i<5;i++)r('#c3b38d',-83+i*38,3,25,2);
 block(c,-101,-139,5,141,3,'#5f6f71','#b7b9a1','#364654');
 block(c,-121,-158,48,23,4,'#254b58','#52818a','#193843');
 c.font='900 10px system-ui';c.textAlign='center';c.fillStyle='#ffe4a6';c.fillText('TAXI',-96,-143);
 // The canopy has a chunky mushroom silhouette, warm cream spots and luggage.
 block(c,-65,-95,126,54,9,'#80573f','#ac8052','#543e36');
 block(c,-67,-90,127,44,8,'#2b4357','#526f7b','#1b3149');
 for(const [wx,ww]of [[-58,41],[-9,33],[31,25]]){
  block(c,wx,-86,ww,33,2,'#81b5c0','#c1e2dc','#507e91');r('#d7f1e3aa',wx+3,-82,5,21);r('#d7f1e380',wx+10,-82,3,13);
 }
 // The real wardrobe avatar also appears in the front window and dialogue portrait.
 if(renderer&&avatar){c.save();c.beginPath();c.rect(28,-88,35,37);c.clip();renderer.draw(c,avatar,45,-38,.55,renderer.frameAt('idle_front',reduced?0:now),false);c.restore();}
 else{r('#d8af83',37,-80,18,22);r('#342f3b',40,-73,3,4);r('#342f3b',49,-73,3,4);r('#ecd39a',33,-85,26,6);r('#394b60',37,-91,18,7);r('#ab755b',42,-62,8,2);}
 // Gold body, passenger door, checker stripe, winged mushroom badge and chrome.
 block(c,-78,-49,154,33,9,'#c78f43','#f2cb72','#896139');
 block(c,-57,-48,76,33,3,'#e4b866','#ffe09a','#ba8541');r('#fff0b0',-51,-43,62,3);r('#8b643e',9,-38,8,3);
 r('#25394b',-75,-22,150,5);for(let i=0;i<12;i++)r(i%2?'#e6c278':'#344556',-70+i*12,-27,10,4);
 block(c,60,-47,25,26,6,'#d6a455','#ffdf91','#91673d');
 block(c,74,-41,11,10,3,'#fff0b1','#fffbe1','#b4b194');r('#fff8df',76,-39,5,5);
 block(c,-84,-39,9,8,3,'#d88263','#f0b18c','#95504b');
 block(c,-85,-19,174,6,5,'#a3b5ba','#e5ece2','#667b8b');
 wheel(c,-46,-8);wheel(c,51,-8);
 // Raised mushroom badge on the door.
 r('#88633f',-31,-41,23,7);r('#f6e4af',-28,-44,17,5);r('#f3db9e',-23,-36,7,6);r('#fff3cb',-25,-43,4,2);
 block(c,-77,-104,154,12,10,'#b76b42','#e8a767','#814c37');
 block(c,-66,-117,132,14,10,'#d88b50','#f5bf77','#9b603c');
 block(c,-45,-126,90,10,10,'#e3a25f','#ffda94','#b07142');
 for(const [sx,sy,w]of [[-54,-112,14],[-23,-120,21],[24,-110,16]])block(c,sx,sy,w,4,3,'#f5e2b2','#fff4d6','#cfb384');
 // A roof rack and travelling trunk make the taxi feel used by actual adventurers.
 block(c,-31,-133,58,4,4,'#7d684d','#d9c391','#514737');
 block(c,-28,-152,29,18,5,'#846045','#b18a5b','#573f37');r('#d8b97a',-23,-151,3,16);r('#d8b97a',-6,-151,3,16);r('#f0d39b',-17,-144,4,5);
 block(c,8,-145,17,11,4,'#688b7c','#a1bfa0','#405c59');
 // A warm steady roof lamp; reduced motion removes the soft exhaust drift.
 block(c,37,-137,25,13,4,'#ead08d','#fff3bf','#a48855');c.fillStyle='#374b55';c.font='800 7px system-ui';c.fillText('택시',50,-127);
 if(!reduced){for(let i=0;i<3;i++){const t=(now/2200+i/3)%1;c.globalAlpha=(1-t)*.22;r('#d9e2d6',-91-t*24,-21-t*18,5+t*5,5+t*5);}c.globalAlpha=1;}
 c.fillStyle='#172c40eb';c.fillRect(-64,18,128,20);c.font='700 10px system-ui';c.fillStyle='#f3d494';c.fillText('달콩의 버섯 택시',0,32);
 c.restore();
}
