import {AREA_IDS,AREA_NAMES} from './areas.js';
import {stageUnlocked,stageOf,GRADES} from './progression.js';
export const TAXI_DRIVER=Object.freeze({name:'기사 달콩',avatar:{hair:'espresso-crop',hat:'cap-black',top:'varsity-navy',bottom:'pants-navy',shoes:'hightop-black',skin:'medium',face:'wink'}});
export const TAXI_MARKER_HEIGHT=108;
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
// A compact yellow sedan, drawn with the same crisp edges as the world art.
export function drawTaxiDriverPortrait(cv,renderer,avatar){
 const c=cv.getContext('2d');c.clearRect(0,0,cv.width,cv.height);
 renderer?.draw(c,avatar,cv.width/2,cv.height-6,1.65,0,false);
}
export function drawTownTaxi(c,map,camX,camY,k,now,reduced=false,{renderer,avatar}={}){
 const p=taxiPoint(map),x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-110*k||x>c.canvas.width+110*k)return;
 c.save();c.translate(x,y);c.scale(k,k);
 const r=(col,x,y,w,h)=>{c.fillStyle=col;c.fillRect(x,y,w,h);};
 const shape=(col,points)=>{c.fillStyle=col;c.beginPath();c.moveTo(...points[0]);for(const pt of points.slice(1))c.lineTo(...pt);c.closePath();c.fill();};
 // Four-door silhouette: low boot, sloped windows and a short bonnet.
 r('#17273840',-76,-1,154,5);
 shape('#805b27',[[-75,-34],[-44,-39],[-26,-68],[26,-68],[48,-40],[76,-35],[81,-26],[81,-9],[-78,-9],[-80,-25]]);
 shape('#f3c33e',[[-76,-32],[-41,-37],[-24,-65],[24,-65],[46,-37],[74,-32],[78,-24],[78,-13],[-76,-13]]);
 shape('#9ccbd3',[[-35,-39],[-21,-60],[-4,-60],[-4,-39]]);
 shape('#9ccbd3',[[2,-60],[21,-60],[38,-39],[2,-39]]);
 shape('#dcebef',[[-32,-40],[-20,-58],[-16,-58],[-28,-40]]);
 // The small driver stays inside the front window.
 if(renderer&&avatar){c.save();c.beginPath();c.rect(3,-60,33,21);c.clip();renderer.draw(c,avatar,18,-25,.36,renderer.frameAt('idle_front',reduced?0:now),false);c.restore();}
 else{r('#d8af83',13,-55,10,12);r('#344454',11,-58,14,4);r('#344454',20,-51,2,2);}
 r('#ffe179',-70,-33,138,3);
 // Standard black checker strip and simple door handles.
 r('#f8d65c',-64,-28,126,8);
 for(let i=0;i<21;i++)r('#29333c',-64+i*6,-28+(i%2)*4,6,4);
 r('#b38a30',-2,-37,1,24);r('#37414a',-13,-35,8,2);r('#37414a',28,-35,8,2);
 r('#fff0bd',69,-30,8,7);r('#dc7762',-77,-29,6,7);
 r('#d5dce0',-79,-15,13,5);r('#d5dce0',68,-15,13,5);
 r('#8d6d2e',-62,-13,126,3);
 // Plain black tyres with small silver hubs.
 for(const wx of [-48,49]){shape('#202c39',[[wx-11,-19],[wx+11,-19],[wx+15,-14],[wx+15,-3],[wx+10,2],[wx-10,2],[wx-15,-3],[wx-15,-14]]);r('#8f9ca7',wx-7,-15,14,13);r('#d5dde0',wx-3,-12,6,7);}
 // The familiar roof sign is the only roof decoration.
 r('#805b27',-18,-79,37,13);r('#fff1bc',-16,-78,33,10);
 c.textAlign='center';c.font='900 8px system-ui';c.fillStyle='#29333c';c.fillText('TAXI',0,-70);
 if(!reduced){for(let i=0;i<2;i++){const t=(now/2200+i/2)%1;c.globalAlpha=(1-t)*.14;r('#d9e2d6',-84-t*15,-13-t*8,3+t*3,3+t*3);}c.globalAlpha=1;}
 c.restore();
}
