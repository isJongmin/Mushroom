import { GARDEN_TITLE } from './game/garden.js';
import {cleanCostume,COSTUMES} from './game/reward-costumes.js';
const empty=()=>({bossClears:0,costume:null,unlocked:false,equipped:false,clears:0,bestHp:0,seen:[]});
const key=p=>`${p}:garden-rewards`;
export function readRewards(profileKey) {
  try { const s=JSON.parse(localStorage.getItem(key(profileKey)));if(!s || typeof s!=='object')return empty();return {bossClears:Number.isInteger(s.bossClears)?Math.max(0,Math.min(1e6,s.bossClears)):0,costume:cleanCostume(s.costume),unlocked:s.unlocked===true,equipped:s.unlocked===true&&s.equipped===true,clears:Number.isInteger(s.clears)?Math.max(0,Math.min(1e6,s.clears)):0,bestHp:Number.isInteger(s.bestHp)?Math.max(0,Math.min(100,s.bestHp)):0,seen:Array.isArray(s.seen)?s.seen.filter(x=>typeof x==='string').slice(-64):[]};}catch{return empty();}
}
export function saveRewards(profileKey,rewards){try{localStorage.setItem(key(profileKey),JSON.stringify(rewards));return true;}catch{return false;}}
export function grantGarden(profileKey,id,hp,mode='defense') {
  const r=readRewards(profileKey);if(r.seen.includes(id))return {rewards:r,fresh:false,saved:true};
  r.unlocked=true;if(mode==='boss')r.bossClears++;else r.clears++;r.bestHp=Math.max(r.bestHp,hp);r.seen.push(id);r.seen=r.seen.slice(-64);
  return {rewards:r,fresh:true,saved:saveRewards(profileKey,r)};
}
export const equippedCostume=key=>{const r=readRewards(key);return COSTUMES.some(c=>c.id===r.costume&&c.unlocked(r))?r.costume:null;};
export const equippedTitle = profileKey => readRewards(profileKey).equipped ? GARDEN_TITLE : null;
