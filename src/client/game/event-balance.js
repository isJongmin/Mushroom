import {JOBS,abilityStats,abilityDefinition,BASIC_INTERVAL_MS} from './jobs.js';
// Sustained single-target ceiling: assumes every projectile connects and no movement.
export function jobCeiling(job){const avg=a=>(a.dmin+a.dmax)/2*a.hits;let busy=0,skills=0;for(let i=1;i<4;i++){const a=abilityStats(job,i);busy+=a.animMs/(a.cooldown*1000);skills+=avg(a)/a.cooldown;}return avg(abilityStats(job,0))/(BASIC_INTERVAL_MS/1000)*Math.max(0,1-busy)+skills;}
const raw=JOBS.map(j=>jobCeiling(j.id));const target=[...raw].sort((a,b)=>a-b).slice(1,3).reduce((a,b)=>a+b)/2;
export const EVENT_FACTORS=Object.freeze(Object.fromEntries(JOBS.map((j,i)=>[j.id,Math.round(Math.max(.85,Math.min(1.45,target/raw[i]))*100)/100])));
export const eventDamage=(job,amount,exposed=false)=>Math.max(1,Math.round(amount*(EVENT_FACTORS[job]??1)*(exposed?1.5:1)));
