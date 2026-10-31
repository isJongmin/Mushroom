import { GARDEN_TITLE } from './game/garden.js';
const empty=()=>({unlocked:false,equipped:false,clears:0,bestHp:0,seen:[]});
const key=p=>`${p}:garden-rewards`;
export function readRewards(profileKey) {
  try { const s=JSON.parse(localStorage.getItem(key(profileKey)));if(!s || typeof s!=='object')return empty();return {unlocked:s.unlocked===true,equipped:s.unlocked===true&&s.equipped===true,clears:Number.isInteger(s.clears)?Math.max(0,Math.min(1e6,s.clears)):0,bestHp:Number.isInteger(s.bestHp)?Math.max(0,Math.min(100,s.bestHp)):0,seen:Array.isArray(s.seen)?s.seen.filter(x=>typeof x==='string').slice(-64):[]};}catch{return empty();}
}
export function saveRewards(profileKey,rewards){try{localStorage.setItem(key(profileKey),JSON.stringify(rewards));return true;}catch{return false;}}
export function grantGarden(profileKey,id,hp) {
  const r=readRewards(profileKey);if(r.seen.includes(id))return {rewards:r,fresh:false,saved:true};
  r.unlocked=true;r.clears++;r.bestHp=Math.max(r.bestHp,hp);r.seen.push(id);r.seen=r.seen.slice(-64);
  return {rewards:r,fresh:true,saved:saveRewards(profileKey,r)};
}
export const equippedTitle = profileKey => readRewards(profileKey).equipped ? GARDEN_TITLE : null;
