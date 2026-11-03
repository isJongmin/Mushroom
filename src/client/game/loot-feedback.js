// Bounded presentation state; collecting remains a single store transaction.
export function createLootFeedback(){
 let entries=[],serial=0;
 return {push(item,now){
  entries=entries.filter(e=>now<e.until);
  if(item.kind==='gold'){
   const last=entries.find(e=>e.kind==='gold'&&now-e.at<900);
   if(last){last.amount+=item.amount;last.at=now;last.until=now+2600;return;}
  }
  entries.push({...item,key:++serial,at:now,until:now+3200});
  if(entries.length>3)entries.shift();
 },sample(now){entries=entries.filter(e=>now<e.until);return entries;},clear(){entries=[];}};
}
