// Levels are derived from saved hunting evidence, including existing saves.
// No separately writable XP balance or second reward transaction is needed.
export const MAX_ADVENTURE_LEVEL=30;
export const AREA_XP=Object.freeze({village:10,quarry:30,forest:70,frost:150});
export const cleanAdventureLevel=n=>Number.isInteger(n)?Math.max(1,Math.min(MAX_ADVENTURE_LEVEL,n)):1;
export const levelCost=level=>80+40*(level-1)+15*(level-1)**2;
export function adventureProgress(state){
 let total=0;
 for(const [area,xp]of Object.entries(AREA_XP)){
  const kills=state?.kills?.[area];
  if(Number.isSafeInteger(kills)&&kills>0)total+=Math.min(1e9,kills)*xp;
 }
 let level=1,current=total;
 while(level<MAX_ADVENTURE_LEVEL&&current>=levelCost(level)){current-=levelCost(level);level++;}
 const capped=level===MAX_ADVENTURE_LEVEL,needed=capped?0:levelCost(level);
 return {level,total,current:capped?0:current,needed,capped,ratio:capped?1:current/needed};
}
export const adventureBonuses=level=>({attack:1+.01*(cleanAdventureLevel(level)-1),hp:3*(cleanAdventureLevel(level)-1)});
