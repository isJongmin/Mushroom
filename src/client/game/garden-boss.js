export const bossPoint=world=>({x:(world.spawn?.x??world.width/2)+260,y:world.groundY});
export const BOSS_KIND='garden-king';
export const bossMaxHp=n=>Math.round(1400*(1+.65*(Math.max(1,Math.min(20,n))-1)));
export function cleanBoss(b){
 if(!b||!['stomp','spores','ring','exposed'].includes(b.pattern)||!Number.isInteger(b.seq)||b.seq<0||b.seq>10000||!Number.isInteger(b.at)||b.at<0||!Number.isFinite(b.targetX)||Math.abs(b.targetX)>1e5||!Number.isInteger(b.max)||b.max<1||b.max>50000)return null;
 return {pattern:b.pattern,seq:b.seq,at:b.at,targetX:b.targetX,max:b.max};
}
export const bossImpactAt=b=>b.at+(['stomp','ring'].includes(b.pattern)?1800:2200);
export const bossPhaseDuration=b=>b.pattern==='exposed'?6000:4000;
export function advanceBoss(b,now,targetX){
 if(now<b.at+bossPhaseDuration(b))return b;
 const order=['stomp','spores','ring','exposed'],i=(order.indexOf(b.pattern)+1)%4;
 return {...b,pattern:order[i],seq:b.seq+1,at:now,targetX};
}
export function bossDanger(b,p,point){
 if(!b||p.dead||b.pattern==='exposed')return false;
 const d=Math.abs(p.x-point.x),height=point.y-p.y;
 if(b.pattern==='stomp')return d<210&&height<85;
 if(b.pattern==='spores')return Math.abs(p.x-b.targetX)<105&&height<350;
 return d>145&&d<590&&height<110;
}
export const bossPatternText={stomp:'지면 충격파 · 점프로 피하세요',spores:'포자 낙하 · 표시된 위치에서 벗어나세요',ring:'포자 고리 · 보스 가까이가 안전해요',exposed:'약점 노출 · 공격할 기회!'};
export function bossSpec(base){return {...base,name:'버섯왕 모스',hp:50000,speed:0,touchDamage:0,size:{w:144,h:142},behavior:'walk'};}

export function installBoss(kinds){const base=kinds.get('golem')||kinds.get('mushroom');if(base)kinds.set(BOSS_KIND,bossSpec(base));}
