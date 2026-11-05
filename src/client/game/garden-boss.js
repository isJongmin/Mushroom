export const bossPoint=world=>({x:(world.spawn?.x??world.width/2)+260,y:world.groundY});
export const BOSS_KIND='garden-king';
export const bossMaxHp=n=>Math.round(1400*(1+.65*(Math.max(1,Math.min(20,n))-1)));

const PATTERNS={
 village:['stomp','spores','ring','exposed'],
 quarry:['crystal-rise','crystal-beam','crystal-shatter','exposed'],
 forest:['stomp','spores','ring','exposed'],
 frost:['stomp','spores','ring','exposed'],
};
export const bossPatternOrder=area=>PATTERNS[area]||PATTERNS.village;

export function cleanBoss(b){
 const area=['village','quarry','forest','frost'].includes(b?.area)?b.area:'village';
 if(!b||!bossPatternOrder(area).includes(b.pattern)||!Number.isInteger(b.seq)||b.seq<0||b.seq>10000||!Number.isInteger(b.at)||b.at<0||!Number.isFinite(b.targetX)||Math.abs(b.targetX)>1e5||!Number.isInteger(b.max)||b.max<1||b.max>50000)return null;
 for(const key of ['homeX','originX'])if(b[key]!=null&&(!Number.isFinite(b[key])||Math.abs(b[key])>1e5))return null;
 return {...(b.area!=null?{area}:{}),pattern:b.pattern,seq:b.seq,at:b.at,targetX:b.targetX,max:b.max,...(b.homeX!=null?{homeX:b.homeX}:{}),...(b.originX!=null?{originX:b.originX}:{})};
}

export const bossImpactAt=b=>b.at+(['stomp','ring'].includes(b.pattern)?1800:['crystal-rise','crystal-beam','crystal-shatter'].includes(b.pattern)?2000:2200);
export const bossPhaseDuration=b=>b.pattern==='exposed'?6000:4000;
export function advanceBoss(b,now,targetX){
 if(now<b.at+bossPhaseDuration(b))return b;
 const order=bossPatternOrder(b.area),i=(order.indexOf(b.pattern)+1)%order.length;
 const end=bossPose(b,{x:b.homeX??b.originX??targetX,y:0},b.at+bossPhaseDuration(b));
 return {...b,pattern:order[i],seq:b.seq+1,at:now,targetX,originX:end.x};
}

const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const ease=t=>t*t*(3-2*t);
export function bossPose(b,point,now){
 if(!b)return {x:point.x,height:0,squash:1,dir:1,step:0};
 const home=b.homeX??point.x,origin=b.originX??home,age=Math.max(0,now-b.at),target=clamp(b.targetX,home-420,home+420);
 let dest=home,x=origin,height=0,squash=1,step=0;
 if(b.pattern==='stomp'||b.pattern==='crystal-rise'){
   dest=target;const t=clamp((age-500)/1300,0,1);x=origin+(dest-origin)*ease(t);height=(b.pattern==='stomp'?260:110)*Math.sin(Math.PI*t);
   if(age<500)squash=1-.18*Math.sin(age/500*Math.PI/2);
   if(age>=1800&&age<2150)squash=.78+.22*(age-1800)/350;
 }else if(b.pattern==='spores'){
   dest=clamp(target+(target<home?230:-230),home-420,home+420);const t=clamp(age/2800,0,1);x=origin+(dest-origin)*ease(t);step=t<1?Math.sin(age/90):0;height=t<1?Math.abs(Math.sin(age/180))*32:0;
 }else if(['ring','crystal-beam','crystal-shatter'].includes(b.pattern)){
   const t=clamp(age/1600,0,1);x=origin+(home-origin)*ease(t);height=b.pattern==='ring'?65*Math.sin(Math.PI*t):0;step=t<1?Math.sin(age/80):0;
 }
 return {x,height:Math.max(0,height),squash,dir:dest>=origin?1:-1,step};
}

export function bossStrikePoint(b,point){return {x:bossPose(b,point,bossImpactAt(b)).x,y:point.y};}
const nearCrystal=(x,home,radius=78)=>Math.abs(x-(home-190))<radius||Math.abs(x-(home+190))<radius;
export function bossDanger(b,p,point){
 if(!b||p.dead||b.pattern==='exposed')return false;
 const impact=bossStrikePoint(b,point),d=Math.abs(p.x-impact.x),height=point.y-p.y;
 if(height>=350||height<=-70)return false;
 if(b.pattern==='stomp')return d<210&&height<85;
 if(b.pattern==='spores')return Math.abs(p.x-b.targetX)<105;
 if(b.pattern==='ring')return d>145&&d<590&&height<110;
 if(b.pattern==='crystal-rise')return [-220,0,220].some(offset=>Math.abs(p.x-b.targetX-offset)<72)&&height<125;
 const home=b.homeX??point.x;
 if(b.pattern==='crystal-beam')return Math.abs(p.x-home)<620&&!nearCrystal(p.x,home)&&height<140;
 if(b.pattern==='crystal-shatter')return nearCrystal(p.x,home,108)&&height<140;
 return false;
}

export const bossPatternText={
 stomp:'점프 내려찍기 · 착지 표식을 피하거나 점프하세요',
 spores:'포자 낙하 · 표시된 위치에서 벗어나세요',
 ring:'포자 고리 · 보스 가까이가 안전해요',
 'crystal-rise':'수정 융기 · 세 갈래 균열 사이로 피하세요',
 'crystal-beam':'수정 광선 · 솟은 수정 뒤에 숨으세요',
 'crystal-shatter':'수정 파쇄 · 엄폐물에서 떨어지세요',
 exposed:'약점 노출 · 공격할 기회!',
};
export function bossSpec(base){return {...base,name:'버섯왕 모스',hp:50000,speed:0,touchDamage:0,size:{w:144,h:142},behavior:'walk'};}

export function installBoss(kinds){const base=kinds.get('golem')||kinds.get('mushroom');if(base)kinds.set(BOSS_KIND,bossSpec(base));const slime=kinds.get('slime');if(slime)kinds.set('garden-runner',{...slime,name:'급습 슬라임',hp:Math.round(slime.hp*.9),speed:slime.speed*1.65});const mushroom=kinds.get('mushroom');if(mushroom)kinds.set('garden-guard',{...mushroom,name:'단단한 버섯',hp:Math.round(mushroom.hp*1.7),speed:mushroom.speed*.9});}
