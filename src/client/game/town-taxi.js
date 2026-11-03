import {AREA_IDS,AREA_NAMES} from './areas.js';
import {stageUnlocked,stageOf,GRADES} from './progression.js';
export const taxiPoint=map=>({x:Math.max(100,Math.min(map.width-100,(map.spawn?.x??900)+235)),y:map.groundY});
export function taxiDestinations(state,job,current){return AREA_IDS.map(id=>({id,name:AREA_NAMES[id],current:id===current,unlocked:!!state&&stageUnlocked(state,job,id),requirement:`${GRADES[stageOf(id).recommended]} 주무기 획득`}));}
export function taxiTravelReason({state,job,current,to,player,map,connected=true,now=0,readyAt=0}){
 if(!connected)return '연결을 기다려주세요.';if(!player||player.dead)return '살아 있는 상태에서 택시를 이용하세요.';
 if(now<readyAt)return '잠시 후 다시 이용하세요.';const p=taxiPoint(map);if(Math.abs(player.x-p.x)>160||Math.abs(player.y-p.y)>85)return '택시 가까이로 이동해주세요.';
 if(!AREA_IDS.includes(to))return '목적지를 선택하세요.';if(to===current)return '현재 있는 마을입니다.';
 if(!state||!stageUnlocked(state,job,to))return `${GRADES[stageOf(to).recommended]} 이상 주무기를 먼저 획득하세요.`;
 return '';
}
export function drawTownTaxi(c,map,camX,camY,k,now,reduced=false){
 const p=taxiPoint(map),x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-100*k||x>c.canvas.width+100*k)return;
 c.save();c.translate(x,y);c.scale(k,k);const r=(color,x,y,w,h)=>{c.fillStyle=color;c.fillRect(x,y,w,h);};
 r('#15273844',-43,0,86,5);r('#29364b',-36,-12,17,14);r('#29364b',20,-12,17,14);r('#bbd5d4',-32,-8,8,6);r('#bbd5d4',24,-8,8,6);
 r('#b48043',-46,-33,92,23);r('#e6b965',-43,-36,86,23);r('#f9d984',-33,-61,63,28);r('#324a62',-28,-57,52,22);r('#a4d9df',-24,-55,20,18);r('#7eb6c9',9,-55,13,18);
 r('#d8a87d',-18,-51,13,13);r('#343e54',-17,-48,2,3);r('#343e54',-8,-48,2,3);r('#f4d88f',-21,-55,20,5);r('#ad784b',-18,-59,13,6);
 r('#fff3ba',-43,-30,9,8);r('#e98c71',35,-30,8,8);r('#273d50',-39,-17,78,4);r('#efd58b',-14,-75,28,12);r('#24374c',-9,-72,18,5);
 c.font='800 10px system-ui';c.textAlign='center';c.fillStyle='#172d40ed';c.fillRect(-43,10,86,19);c.fillStyle='#f6d28b';c.fillText('마을 택시',0,23);c.restore();
}
