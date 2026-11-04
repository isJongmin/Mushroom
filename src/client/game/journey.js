import {adventureGoal} from './adventure-goals.js';
import {mentorPoint} from './training-mentors.js';
import {taxiPoint} from './town-taxi.js';
import {explorationPoints} from './adventure-traits.js';
import {questNpcPoint} from './quest-npc.js';
export const CHAPTERS=Object.freeze({
 village:{number:'01',title:'작은 마을의 큰 소동',line:'평온한 버섯마을에도, 누군가의 첫 용기가 필요하다.'},
 quarry:{number:'02',title:'땅속에서 들려오는 노래',line:'불 꺼진 갱도 아래, 수정은 아직 빛나고 있다.'},
 forest:{number:'03',title:'숲이 기억하는 이름',line:'길을 잃어도 괜찮다. 오래된 나무가 너를 기억하니까.'},
 frost:{number:'04',title:'서리 너머의 약속',line:'가장 추운 곳에, 끝내 지키고 싶은 온기가 있다.'},
});
export const chapterOf=area=>CHAPTERS[area]||CHAPTERS.village;
export function journeyObjective(state,area){
 const base=adventureGoal(state,area);if(!base)return null;
 if(['bag','traits','mentor'].includes(base.action))return base;
 const first=area+':'+(area==='village'?'hunt20':'explore3');
 if(!state.traits.quests[first])return {action:'mentor',title:area==='village'?'첫걸음, 스승의 부탁':'이곳의 스승을 찾아서',detail:'수련을 수락하고 여정을 시작하세요'};
 if(area!=='village'&&state.traits.quests[first]==='active')return {action:'explore',title:'지도에 없는 세 갈래 길',detail:`탐험 지점 ${state.traits.explored[area].length} / 3`};
 if(base.action==='hunt'&&state.traits.quests[area+':boss-first']==='active'&&!state.traits.events[area].boss)return {action:'event',title:'이 마을을 지켜낼 시간',detail:'안내 NPC에게 보스 도전을 선택하세요 · 첫 처치 수련'};
 if(base.action==='hunt'&&area!=='village'&&state.traits.quests[area+':defense-first']==='active'&&!state.traits.events[area].defense)return {action:'event',title:'함께 지켜내는 작은 약속',detail:'안내 NPC에게 방어 이벤트를 선택하세요'};
 return {...base,title:base.action==='hunt'?(area==='village'?'마을 밖으로, 첫 출정':'다음 여정을 위한 준비'):base.title,detail:base.action==='hunt'?base.title+' · '+base.detail:base.detail};
}
export function journeyTarget(goal,map,world,state,player){
 if(!goal||!player)return null;
 if(['mentor','traits'].includes(goal.action))return {...mentorPoint(world),label:'수련 스승'};
 if(goal.action==='taxi')return {...taxiPoint(map),label:'마을 택시'};
 if(goal.action==='event')return {...questNpcPoint(world),label:'마을 안내 NPC'};
 if(goal.action==='explore'){
  const p=explorationPoints(map).find(p=>!state.traits.explored[map.id].includes(p.id));return p?{...p,label:p.name}:null;
 }
 if(goal.action==='hunt'){
  const zones=(map.spawns||[]).filter(z=>z.platform==='ground'&&!z.event&&Number.isFinite(z.x1)&&Number.isFinite(z.x2));
  const z=zones.sort((a,b)=>Math.abs((a.x1+a.x2)/2-player.x)-Math.abs((b.x1+b.x2)/2-player.x))[0];
  return z?{x:(z.x1+z.x2)/2,y:map.groundY,label:'사냥터'}:null;
 }
 return null;
}
export function journeyDirection(target,player){
 if(!target||!player)return '';
 if(Math.abs(target.x-player.x)<100&&Math.abs(target.y-player.y)<100)return '목표에 도착했습니다';
 if(Math.abs(target.x-player.x)<130&&target.y<player.y-100)return '위층으로 올라가세요';
 return target.x<player.x?'왼쪽 길을 따라가세요':'오른쪽 길을 따라가세요';
}
export function drawJourneyBeacon(c,target,player,camX,camY,k,now,reduced=false){
 if(!target||!player)return;
 const rawX=(target.x-camX)*k,rawY=(target.y-camY-135)*k;
 const x=Math.max(28*k,Math.min(c.canvas.width-28*k,rawX));
 const y=Math.max(120*k,Math.min(c.canvas.height-125*k,rawY));
 const off=Math.abs(x-rawX)>1,bob=reduced?0:Math.sin(now/360)*3*k;
 c.save();c.translate(x,y+bob);c.fillStyle='#102d32e8';c.strokeStyle='#eddb9c';c.lineWidth=1.3*k;
 c.beginPath();c.moveTo(0,-13*k);c.lineTo(13*k,0);c.lineTo(0,13*k);c.lineTo(-13*k,0);c.closePath();c.fill();c.stroke();
 c.fillStyle='#f4e5b5';c.font=`700 ${12*k}px system-ui`;c.textAlign='center';c.fillText(off?(rawX<x?'‹':'›'):'◇',0,4*k);
 c.font=`600 ${10*k}px system-ui`;const label=target.label,w=c.measureText(label).width+16*k;
 c.fillStyle='#122b31e8';c.fillRect(-w/2,20*k,w,19*k);c.fillStyle='#f4e5b5';c.fillText(label,0,33*k);c.restore();
}
