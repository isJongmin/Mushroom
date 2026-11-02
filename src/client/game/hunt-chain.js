// Host-owned per-participant chain; loot receipts remain the payout deduplication key.
export const comboBonus=count=>Math.min(30,Math.floor(count/5)*5);
export function createHuntChain({windowMs=20000}={}){
 const chains=new Map();
 return {record(uid,now){const old=chains.get(uid),count=old&&now>=old.at&&now-old.at<=windowMs?Math.min(999,old.count+1):1;chains.set(uid,{count,at:now});return {count,bonus:comboBonus(count)};},clear(){chains.clear();},prune(now){for(const [id,v]of chains)if(now-v.at>windowMs)chains.delete(id);}};
}
export function huntContract(area,stage,kills,weapon='sword'){
 if(kills<=0||kills%20!==0)return null;
 return {gold:150*3**(stage-1),item:{kind:weapon,tier:Math.min(4,stage)}};
}
