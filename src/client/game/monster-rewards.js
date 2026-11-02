import {stageOf} from './progression.js';
import {regionOf} from './regions.js';
// Difficulty tiers are fixed by species, never by how long a player takes to kill it.
export const MONSTER_RANK={snail:0,mushroom:1,slime:2,'wild-stump':2.35,'armored-mushroom':3,bat:0,'crystal-crab':1,golem:2,'ore-beetle':2.4,'cave-sentinel':3,'moss-slime':0,'forest-stump':1,'moss-guardian':2,'thorn-mantis':2.4,'ancient-treant':3,'frost-slime':0,'ice-crab':1,'ice-golem':2,'frost-beetle':2.4,'glacier-sentinel':3,'garden-runner':2,'garden-guard':3,'garden-king':4};
export const REWARD_RULES=[{gold:[4,7],equipment:.4,promote:0},{gold:[9,14],equipment:.65,promote:.2},{gold:[17,25],equipment:.85,promote:.45},{gold:[30,45],equipment:1,promote:.7}];
export function rewardProfile(area,kind){const stage=stageOf(area).order-1,rank=MONSTER_RANK[kind]??1;if(rank===4)return {rank,stage,gold:[650,950].map(n=>n*regionOf(area).scale),count:5,rates:[0,.15,.7,.15,0]};const lo=REWARD_RULES[Math.floor(rank)],hi=REWARD_RULES[Math.min(3,Math.floor(rank)+1)],t=rank-Math.floor(rank),mix=(a,b)=>a+(b-a)*t;return {rank,stage,equipment:mix(lo.equipment,hi.equipment),promote:mix(lo.promote,hi.promote),gold:lo.gold.map((n,i)=>Math.round(mix(n,hi.gold[i])*3**stage))};}
export function rollMonsterLoot(area,kind,rnd=Math.random){
 const p=rewardProfile(area,kind),items=[],gold=p.gold[0]+Math.floor(rnd()*(p.gold[1]-p.gold[0]+1)),types=['sword','bow','staff','claw','shield'];
 const choose=weights=>{let n=rnd();for(let i=0;i<weights.length;i++){n-=weights[i];if(n<0)return i;}return weights.length-1;};
 if(p.rank===4){for(let n=0;n<p.count;n++)items.push({kind:types[Math.min(4,Math.floor(rnd()*5))],tier:Math.min(4,n<2?Math.max(2,p.stage+1):Math.max(p.stage,choose(p.rates)))});}
 else if(rnd()<p.equipment){let tier=p.stage+choose([.8,.18,.02]);if(rnd()<p.promote)tier++;items.push({kind:types[Math.min(4,Math.floor(rnd()*5))],tier:Math.min(4,Math.max(p.stage+(p.rank>=3?1:0),tier))});}
 return {gold,items};
}
