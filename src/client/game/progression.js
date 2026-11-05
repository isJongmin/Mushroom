import {cleanTraits,cleanAllocation,allocationOK,earnedPoints,traitGoals} from './adventure-traits.js';
import {huntContract} from './hunt-chain.js';
import {regionOf} from './regions.js';
import {adventureProgress,adventureBonuses,cleanAdventureLevel} from './adventure-level.js';
// One balance contract for loot, equipment, stages and pets. No real-money purchases.
export const GROUND_DROP_TTL_MS=3*60*1000;
export const groundDropAlive=(drop,now=Date.now())=>!drop.expiresAt||drop.expiresAt>now;
export const GRADES = Object.freeze(['일반','고급','희귀','영웅','전설']);
export const GRADE_COLORS = ['#9aaeb6','#65c795','#73b6ff','#bc92ff','#f4ce70'];
export const WEAPONS = Object.freeze({warrior:'sword',archer:'bow',mage:'staff',thief:'claw'});
export const weaponJob=kind=>Object.keys(WEAPONS).find(j=>WEAPONS[j]===kind)||'warrior';
export const activeWeapon=s=>s.items.find(i=>i.id===s.activeWeapon&&i.kind!=='shield')||null;
export const activeJob=s=>weaponJob(activeWeapon(s)?.kind);
export const wornItem=(s,id)=>s.activeWeapon===id||s.shield===id;
export const ITEM_NAMES = {sword:'검',bow:'활',staff:'스태프',claw:'아대',shield:'방패'};
export const ATTACK = [20,32,51,82,131];
export const DEFENSE = [0,3,7,13,22];
export const SELL = [15,40,110,300,800];
export const STAGES = Object.freeze({
 village:{order:1,name:'버섯마을',recommended:0,drop:[.80,.18,.02,0,0],mobs:{snail:[40,5],mushroom:[65,8],slime:[90,10],'wild-stump':[120,12],'armored-mushroom':[180,16]},petNames:['아기버섯','새싹슬라임','도토리다람쥐','달빛사슴','황금버섯왕']},
 quarry:{order:2,name:'광산마을',recommended:1,drop:[.10,.70,.18,.02,0],mobs:{bat:[240,24],'crystal-crab':[360,30],golem:[520,38],'ore-beetle':[720,44],'cave-sentinel':[1000,52]},petNames:['광석두더지','꼬마박쥐','수정게','자수정골렘','별빛드래곤']},
 forest:{order:3,name:'이끼마을',recommended:2,drop:[0,.10,.70,.18,.02],mobs:{'moss-slime':[1100,48],'forest-stump':[1500,57],'moss-guardian':[2100,68],'thorn-mantis':[2800,79],'ancient-treant':[3800,92]},petNames:['이끼방울','잎새토끼','반딧불정령','고대숲사슴','세계수정령']},
 frost:{order:4,name:'서리마을',recommended:3,drop:[0,0,.1,.7,.2],mobs:{'frost-slime':[4200,88],'ice-crab':[5400,103],'ice-golem':[7000,119],'frost-beetle':[9000,135],'glacier-sentinel':[12000,155]},petNames:['눈송이방울','설원토끼','빙정여우','오로라사슴','빙하드래곤']},
});
export const MAX_EQUIPPED_PETS=3;
// Keep the first-pet alias for legacy saves/clients; all new writes keep both fields aligned.
export function equippedPetIds(s){
 const owned=id=>petSpec(id)&&Object.hasOwn(s.pets||{},id);
 let ids=Array.isArray(s.equippedPets)?s.equippedPets:[];
 if(owned(s.pet)&&s.pet!==ids[0])ids=[s.pet];
 return [...new Set(ids.filter(owned))].slice(0,MAX_EQUIPPED_PETS);
}
function setEquippedPets(s,ids){s.equippedPets=[...ids];s.pet=s.equippedPets[0]||null;}
export const PET_RATES = [.65,.25,.08,.018,.002];
export const PET_PRICES = {1:200,5:950,10:1800};
export const PET_ATK = [.02,.04,.07,.10,.15];
export const PET_HP = [5,10,20,35,60];
export const PET_ESSENCE = [1,2,5,12,30];
export const PET_SELL = [20,60,180,600,2000];
export const PET_UPGRADE = [5,10,20,35,55];
export const petSellPrice=id=>{const p=petSpec(id);return p?PET_SELL[p.tier]*regionOf(p.area).petPrice:0;};
export const petPrice=(area,count)=>PET_PRICES[count]*regionOf(area).petPrice;
export function petBonuses(id,level=0){const p=petSpec(id);if(!p)return {attack:0,hp:0};const scale=regionOf(p.area).petPower*(1+level*.1);return {attack:PET_ATK[p.tier]*scale,hp:Math.round(PET_HP[p.tier]*scale)};}
export const stageOf = id => Object.hasOwn(STAGES,id)?STAGES[id]:STAGES.village;
export const tierOK = n => Number.isInteger(n)&&n>=0&&n<5;
export const itemOK = i => !!i&&typeof i.id==='string'&&i.id.length>0&&i.id.length<=160&&Object.hasOwn(ITEM_NAMES,i.kind)&&tierOK(i.tier);
export function petSpec(id) {
 if(typeof id!=='string'||!/^[a-z]+:[0-4]$/.test(id))return null;
 const [area,t]=id.split(':');const tier=Number(t);
 return Object.hasOwn(STAGES,area)&&String(tier)===t&&tierOK(tier)?{id,area,tier,name:STAGES[area].petNames[tier]}:null;
}
export const itemName = i => i.kind==='gold'?`${i.amount.toLocaleString()} G`:`${GRADES[i.tier]} ${ITEM_NAMES[i.kind]}`;
export const dropOK=d=>itemOK(d)||!!d&&d.kind==='gold'&&typeof d.id==='string'&&d.id.length>0&&d.id.length<=160&&Number.isSafeInteger(d.amount)&&d.amount>0&&d.amount<=20000;
export function weighted(rates,rnd=Math.random){let n=rnd();for(let i=0;i<rates.length;i++){n-=rates[i];if(n<0)return i;}return rates.length-1;}
export function rollEquipment(area,rnd=Math.random){
 const out=[];if(rnd()<.65)out.push({kind:['sword','bow','staff','claw'][Math.min(3,Math.floor(rnd()*4))],tier:weighted(stageOf(area).drop,rnd)});
 if(rnd()<.10)out.push({kind:'shield',tier:weighted(stageOf(area).drop,rnd)});
 return out;
}
export function starterState(job='warrior') {return {version:1,progressionVersion:2,revision:0,gold:0,items:[{id:'starter-'+job,kind:WEAPONS[job]||'sword',tier:0}],activeWeapon:'starter-'+job,equipped:{[job]:'starter-'+job},shield:null,highest:{[job]:0},pets:{},equippedPets:[],pet:null,essence:0,pity:{},pending:[],seen:[],kills:{village:0,quarry:0,forest:0,frost:0},traits:cleanTraits(null,{},STAGES)};}
export function cleanState(raw,job='warrior') {
 if(!raw||raw.version!==1)return starterState(job);
 const s=starterState(job),nat=(n,max=1e9)=>Number.isSafeInteger(n)?Math.max(0,Math.min(max,n)):0;
 s.revision=nat(raw.revision);s.gold=nat(raw.gold);s.essence=nat(raw.essence);
 const ids=new Set();s.items=(Array.isArray(raw.items)?raw.items:[]).filter(i=>itemOK(i)&&!ids.has(i.id)&&ids.add(i.id)).slice(0,200).map(i=>({id:i.id,kind:i.kind,tier:i.tier}));
 s.equipped={};s.highest={};for(const j of Object.keys(WEAPONS)){
 const item=s.items.find(i=>i.id===raw.equipped?.[j]&&i.kind===WEAPONS[j]);if(item)s.equipped[j]=item.id;
 s.highest[j]=Math.max(tierOK(raw.highest?.[j])?raw.highest[j]:0,...s.items.filter(i=>i.kind===WEAPONS[j]).map(i=>i.tier));
 }
 s.activeWeapon=s.items.find(i=>i.id===(raw.activeWeapon||s.equipped[job])&&i.kind!=='shield')?.id||s.items.find(i=>i.kind!=='shield')?.id||null;
 s.shield=s.items.some(i=>i.id===raw.shield&&i.kind==='shield')?raw.shield:null;
 for(const [id,p] of Object.entries(raw.pets||{}).slice(0,20))if(petSpec(id))s.pets[id]={level:nat(p?.level,5)};
 setEquippedPets(s,equippedPetIds({...raw,pets:s.pets}));
 for(const area of Object.keys(STAGES)) {const p=raw.pity?.[area];s.pity[area]=[nat(p?.[0],19),nat(p?.[1],79),nat(p?.[2],199)];s.kills[area]=nat(raw.kills?.[area]);}
 s.seen=Array.isArray(raw.seen)?raw.seen.filter(i=>typeof i==='string'&&i.length<=160).slice(-10000):[];
 s.traits=cleanTraits(raw.traits,s.kills,STAGES);
 if(raw.progressionVersion!==2){
  const legacyTier=Math.max(0,...Object.values(s.highest));
  if(legacyTier>=1)s.traits.events.village.boss=true;
  if(legacyTier>=2)s.traits.events.quarry.boss=true;
  if(legacyTier>=3)s.traits.events.forest.boss=true;
 }
 s.pending=(Array.isArray(raw.pending)?raw.pending:[]).filter(d=>dropOK(d)&&Object.hasOwn(STAGES,d.area)&&Number.isFinite(d.x)&&Number.isFinite(d.y)&&Math.abs(d.x)<1e5&&Math.abs(d.y)<1e5).slice(0,200).map(d=>({...d,expiresAt:Number.isSafeInteger(d.expiresAt)&&d.expiresAt>0?d.expiresAt:0}));return s;
}
export function loadout(s) {
 const weapon=activeWeapon(s),job=weaponJob(weapon?.kind);
 const shield=s.items.find(i=>i.id===s.shield&&i.kind==='shield');
 const companions=equippedPetIds(s).map(id=>({id,level:s.pets[id].level}));
 return {adventureLevel:adventureProgress(s).level,companions,traits:{...s.traits.allocated},weapon:weapon?.kind||'sword',job,tier:weapon?.tier??0,highest:s.highest[job]??0,shield:shield?.tier??-1,pet:companions[0]?.id||null,level:companions[0]?.level||0};
}
export function cleanLoadout(l) {
 const weapon=Object.values(WEAPONS).includes(l?.weapon)?l.weapon:null;
 const source=Array.isArray(l?.companions)?l.companions:[{id:l?.pet,level:l?.level}],seen=new Set(),companions=[];
 for(const p of source.slice(0,20))if(petSpec(p?.id)&&!seen.has(p.id)){seen.add(p.id);companions.push({id:p.id,level:Number.isInteger(p.level)?Math.max(0,Math.min(5,p.level)):0});if(companions.length===MAX_EQUIPPED_PETS)break;}
 return {adventureLevel:cleanAdventureLevel(l?.adventureLevel),companions,traits:cleanAllocation(l?.traits),...(weapon?{weapon,job:weaponJob(weapon)}:{}),tier:tierOK(l?.tier)?l.tier:0,highest:Math.max(tierOK(l?.tier)?l.tier:0,tierOK(l?.highest)?l.highest:0),shield:tierOK(l?.shield)?l.shield:-1,pet:companions[0]?.id||null,level:companions[0]?.level||0};
}
export function combatStats(raw) {
 const l=cleanLoadout(raw),traits=l.traits,bonuses=l.companions.map(p=>petBonuses(p.id,p.level)),bonus=bonuses.reduce((n,p)=>n+p.attack,0),hp=bonuses.reduce((n,p)=>n+p.hp,0);
 const growth=adventureBonuses(l.adventureLevel);
 return {attack:Math.round(ATTACK[l.tier]*(1+bonus)*(1+.05*traits.attack)*growth.attack),multiplier:ATTACK[l.tier]/20*(1+bonus)*(1+.05*traits.attack)*growth.attack,defense:DEFENSE[l.tier]+(l.shield<0?0:[4,9,16,26,40][l.shield]),cooldownMultiplier:1-.02*traits.technique,maxHp:Math.round((100+hp+growth.hp)*(1+.05*traits.health)),pickup:l.companions.length?240:26};
}
export const skillUnlocked = (l,slot) => {
 const level=cleanLoadout(l).adventureLevel;
 return slot<=1 || slot===2&&level>=5 || slot===3&&level>=12;
};
export const stageUnlocked = (s,job,area) => {
 const order=stageOf(area).order;if(order<=1)return true;
 const previous=Object.keys(STAGES).find(id=>STAGES[id].order===order-1);
 return !!previous&&s?.traits?.events?.[previous]?.boss===true;
};
// Include newly forged items until no pair remains; max grade is never consumed.
export function fusionSummary(items) {
 const counts=new Map();let count=0;
 for(const i of items){const key=i.kind+':'+i.tier;counts.set(key,(counts.get(key)||0)+1);}
 for(const kind of Object.keys(ITEM_NAMES))for(let tier=0;tier<4;tier++){
  const key=kind+':'+tier,pairs=Math.floor((counts.get(key)||0)/2);count+=pairs;
  counts.set(key,(counts.get(key)||0)%2);const next=kind+':'+(tier+1);counts.set(next,(counts.get(next)||0)+pairs);
 }
 return {count,before:items.length,after:items.length-count};
}
export function applyCommand(original,command,{job='warrior',rnd=Math.random,now=Date.now(),id=()=>globalThis.crypto.randomUUID?.()||Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('')}={}) {
 const s=cleanState(original,job),c=command;let result=null;
 const fail=m=>{throw new Error(m);};
 if(c.type==='expire-drops'){const before=s.pending.length;s.pending=s.pending.filter(d=>groundDropAlive(d,now));result={expired:before-s.pending.length};}
 else if(c.type==='ensure') {s.pending=s.pending.filter(d=>groundDropAlive(d,now)).map(d=>d.expiresAt?d:{...d,expiresAt:now+GROUND_DROP_TTL_MS});if(!s.traits.legacyRewardsMigrated){if(c.legacyVillageBoss===true){s.traits.events.village.boss=true;s.traits.quests['village:boss-first']='claimed';}s.traits.legacyRewardsMigrated=true;}if(!activeWeapon(s)){const i={id:id(),kind:WEAPONS[job],tier:0};s.items.push(i);s.equipped[job]=i.id;s.activeWeapon=i.id;}}
 else if(c.type==='trait-quest-accept'||c.type==='trait-quest-claim') {
  const goal=traitGoals(s,STAGES).find(g=>g.key===c.key);if(!goal)fail('존재하지 않는 수련입니다.');
  if(c.type==='trait-quest-accept'){if(goal.claimed)return {state:s,result:{duplicate:true,key:c.key}};if(goal.status==='available')s.traits.quests[c.key]='active';result={accepted:true,key:c.key};}
  else{if(goal.claimed)return {state:s,result:{duplicate:true,key:c.key}};if(!goal.ready)fail('수련을 수락하고 목표를 완료한 뒤 다시 찾아오세요.');s.traits.quests[c.key]='claimed';result={point:1,key:c.key};}
 }
 else if(c.type==='traits-allocate') {
  if(c.expectedRevision!==s.revision)fail('다른 탭에서 진행도가 바뀌었어요. 다시 확인해주세요.');
  if(!allocationOK(c.allocated,earnedPoints(s,STAGES)))fail('특성은 각 0~10 정수, 합계는 획득 포인트 이하여야 합니다.');
  s.traits.allocated=cleanAllocation(c.allocated,earnedPoints(s,STAGES));
 }
 else if(c.type==='trait-explore') {
  if(!Object.hasOwn(STAGES,c.area)||c.area==='village'||!['entry','upper','depth'].includes(c.point))fail('잘못된 탐험 지점입니다.');
  if(!s.traits.explored[c.area].includes(c.point))s.traits.explored[c.area].push(c.point);
 }
 else if(c.type==='trait-event') {
  if(!Object.hasOwn(STAGES,c.area)||!['boss','defense'].includes(c.mode)||(c.area==='village'&&c.mode==='defense'))fail('잘못된 모험 기록입니다.');
  s.traits.events[c.area][c.mode]=true;
 }
 else if(c.type==='loot') {
  if(typeof c.receipt!=='string'||c.receipt.length>150||!Object.hasOwn(STAGES,c.area))fail('잘못된 드롭 정보입니다.');
  if(s.seen.includes(c.receipt))return {state:s,result:{duplicate:true}};
  if(!Array.isArray(c.items)||c.items.length>8||c.items.some(i=>!itemOK({...i,id:'check'})))fail('잘못된 장비입니다.');
  let gold=c.gold??0;if(!Number.isSafeInteger(gold)||gold<0||gold>20000)fail('잘못된 골드 보상입니다.');
  if(c.kind!=null&&!Object.hasOwn(STAGES[c.area].mobs,c.kind)&&!['garden-king','garden-runner','garden-guard'].includes(c.kind))fail('잘못된 몬스터입니다.');
  const counts=!c.receipt.startsWith('event-')&&(!c.kind||Object.hasOwn(STAGES[c.area].mobs,c.kind)),kills=s.kills[c.area]+(counts?1:0),contract=counts?huntContract(c.area,stageOf(c.area).order,kills,activeWeapon(s)?.kind||'sword'):null,items=[...c.items];
  if(contract){gold+=contract.gold;items.push(contract.item);result={contract:true};}
  const createdAt=Number.isSafeInteger(c.createdAt)&&c.createdAt>0?Math.min(c.createdAt,now):now,expiresAt=createdAt+GROUND_DROP_TTL_MS,expired=expiresAt<=now;
  s.pending=s.pending.filter(d=>groundDropAlive(d,now));
  const piles=gold?Math.min(8,Math.max(1,Math.ceil(gold/120))):0;
  if(!expired&&s.pending.length+items.length+piles>200)fail('바닥 장비가 너무 많습니다. 먼저 장비를 주워주세요.');
  if(!Number.isFinite(c.x)||!Number.isFinite(c.y)||Math.abs(c.x)>1e5||Math.abs(c.y)>1e5)fail('잘못된 드롭 위치입니다.');
  if(counts&&c.kind){const records=s.traits.species[c.area][c.kind],max=c.area==='village'?10:20;if(records.length<max&&!records.includes(c.receipt))records.push(c.receipt);}
  s.seen.push(c.receipt);s.seen=s.seen.slice(-10000);s.kills[c.area]=kills;
  if(!expired)items.forEach((i,n)=>s.pending.push({expiresAt,id:c.receipt+':'+n,kind:i.kind,tier:i.tier,area:c.area,x:c.x+(n-(items.length-1)/2)*38,y:c.y}));
  for(let n=0;!expired&&n<piles;n++)s.pending.push({expiresAt,id:c.receipt+':gold:'+n,kind:'gold',amount:Math.floor(gold/piles)+(n<gold%piles?1:0),area:c.area,x:c.x+(n-(piles-1)/2)*32,y:c.y});
 }
 else if(c.type==='collect') {
  const d=s.pending.find(i=>i.id===c.id);if(!d)fail('이미 주웠거나 사라진 아이템입니다.');if(!groundDropAlive(d,now))fail('시간이 지나 사라진 아이템입니다.');if(d.kind!=='gold'&&s.items.length>=200)fail('가방이 가득 찼습니다. 장비를 판매하거나 합성해주세요.');
  s.pending=s.pending.filter(i=>i.id!==d.id);if(d.kind==='gold')s.gold=Math.min(1e9,s.gold+d.amount);else s.items.push({id:d.id,kind:d.kind,tier:d.tier});
  const j=Object.keys(WEAPONS).find(j=>WEAPONS[j]===d.kind);if(j)s.highest[j]=Math.max(s.highest[j]||0,d.tier);result=d;
 }
 else if(c.type==='equip') {const i=s.items.find(i=>i.id===c.id);if(!i)fail('장비가 없습니다.');if(i.kind==='shield')s.shield=i.id;else{s.activeWeapon=i.id;s.equipped[weaponJob(i.kind)]=i.id;}}
 else if(c.type==='unequip-shield')s.shield=null;
 else if(c.type==='sell-many') {
 if(!Array.isArray(c.ids)||!c.ids.length||c.ids.length>200||new Set(c.ids).size!==c.ids.length)fail('판매할 장비를 선택해주세요.');
 const equipped=new Set([s.activeWeapon,s.shield]);
 const items=c.ids.map(id=>s.items.find(i=>i.id===id));
 if(items.some(i=>!i))fail('일부 장비가 이미 판매되었거나 없습니다.');
 if(items.some(i=>equipped.has(i.id)))fail('착용 중인 장비는 판매할 수 없습니다.');
 const ids=new Set(c.ids);result=items.reduce((sum,i)=>sum+SELL[i.tier],0);
 s.items=s.items.filter(i=>!ids.has(i.id));s.gold=Math.min(1e9,s.gold+result);
 }
 else if(c.type==='pet-sell') {
 const p=petSpec(c.id);if(!p||!s.pets[c.id])fail('이미 판매된 펫입니다.');
 if(s.equippedPets.includes(c.id))fail('동행을 해제한 뒤 판매해주세요.');
 result=PET_SELL[p.tier]*regionOf(p.area).petPrice;delete s.pets[c.id];s.gold=Math.min(1e9,s.gold+result);
 }
 else if(c.type==='sell') {
 const i=s.items.find(i=>i.id===c.id);if(!i)fail('이미 판매된 장비입니다.');if(wornItem(s,i.id))fail('착용 중인 장비는 판매할 수 없습니다.');
 s.items=s.items.filter(x=>x.id!==i.id);s.gold=Math.min(1e9,s.gold+SELL[i.tier]);result=SELL[i.tier];
 }
 else if(c.type==='fuse-all') {
 const summary=fusionSummary(s.items);if(!summary.count)fail('합성 가능한 장비가 없습니다.');
 // One store transaction commits the entire chain, including equipped replacements.
 for(const kind of Object.keys(ITEM_NAMES))for(let tier=0;tier<4;tier++){
  let pair;
  while((pair=s.items.filter(i=>i.kind===kind&&i.tier===tier)).length>=2){
   pair.sort((a,b)=>Number(wornItem(s,b.id))-Number(wornItem(s,a.id)));
   const next=applyCommand(s,{type:'fuse',a:pair[0].id,b:pair[1].id},{job,rnd,id,now});Object.assign(s,next.state);
  }
 }
 result=summary;
 }
 else if(c.type==='fuse') {
 const a=s.items.find(i=>i.id===c.a),b=s.items.find(i=>i.id===c.b);if(!a||!b||a.id===b.id||a.kind!==b.kind||a.tier!==b.tier||a.tier>=4)fail('같은 종류·등급의 장비 2개가 필요합니다.');
 const next={id:id(),kind:a.kind,tier:a.tier+1};s.items=s.items.filter(i=>i.id!==a.id&&i.id!==b.id);s.items.push(next);
 for(const j of Object.keys(WEAPONS)) {if([a.id,b.id].includes(s.equipped[j]))s.equipped[j]=next.id;if(WEAPONS[j]===a.kind)s.highest[j]=Math.max(s.highest[j]||0,next.tier);}
 if([a.id,b.id].includes(s.activeWeapon))s.activeWeapon=next.id;
 if([a.id,b.id].includes(s.shield))s.shield=next.id;result=next;
 }
 else if(c.type==='draw') {
 if(!Object.hasOwn(STAGES,c.area)||![1,5,10].includes(c.count))fail('잘못된 뽑기입니다.');if(!stageUnlocked(s,job,c.area))fail('먼저 해당 마을을 해금해주세요.');
 const price=petPrice(c.area,c.count);if(s.gold<price)fail('골드가 부족합니다.');s.gold-=price;result=[];
 for(let n=0;n<c.count;n++) {
 const pity=s.pity[c.area]||[0,0,0];let tier=weighted(PET_RATES,rnd);
 if(pity[2]>=199)tier=4;else if(pity[1]>=79)tier=Math.max(3,tier);else if(pity[0]>=19)tier=Math.max(2,tier);
 s.pity[c.area]=[tier>=2?0:pity[0]+1,tier>=3?0:pity[1]+1,tier>=4?0:pity[2]+1];
 const pid=c.area+':'+tier,duplicate=!!s.pets[pid];if(duplicate)s.essence+=PET_ESSENCE[tier];else s.pets[pid]={level:0};
 result.push({id:pid,duplicate,essence:duplicate?PET_ESSENCE[tier]:0});if(!s.equippedPets.length)setEquippedPets(s,[pid]);
 }
 }
 else if(c.type==='pet-equip') {
  if(!Object.hasOwn(s.pets,c.id))fail('보유하지 않은 펫입니다.');
  if(!s.equippedPets.includes(c.id)){if(s.equippedPets.length>=MAX_EQUIPPED_PETS)fail('최대 3마리까지 동행할 수 있어요. 먼저 다른 펫의 동행을 해제해주세요.');setEquippedPets(s,[...s.equippedPets,c.id]);}
 }
 else if(c.type==='pet-off') {
  if(c.id!=null&&!s.equippedPets.includes(c.id))fail('동행 중인 펫이 아닙니다.');
  setEquippedPets(s,c.id?s.equippedPets.filter(id=>id!==c.id):[]);
 }
 else if(c.type==='pet-upgrade') {const p=s.pets[c.id];if(!p||p.level>=5)fail('더 강화할 수 없습니다.');const cost=PET_UPGRADE[p.level];if(s.essence<cost)fail('펫 정수가 부족합니다.');s.essence-=cost;p.level++;}
 else fail('알 수 없는 동작입니다.');
 for(const [j,id] of Object.entries(s.equipped))if(!s.items.some(i=>i.id===id))delete s.equipped[j];
 s.revision++;return {state:s,result};
}
export function stageKinds(base,area){
 const kinds=new Map(base);const boss=base.get('garden-king');if(boss)kinds.set('garden-king',{...boss,name:regionOf(area).boss,touchDamage:Math.round(boss.touchDamage*Math.sqrt(regionOf(area).scale))});for(const id of ['garden-runner','garden-guard']){const spec=base.get(id);if(spec)kinds.set(id,{...spec,hp:Math.round(spec.hp*regionOf(area).scale),touchDamage:Math.round(spec.touchDamage*regionOf(area).scale)});}const extra={'frost-slime':['slime','서리 슬라임',54,48],'ice-crab':['crystal-crab','빙정 게',66,54],'ice-golem':['golem','얼음 골렘',82,94],'frost-beetle':['crystal-crab','서리 딱정벌레',72,62],'glacier-sentinel':['golem','빙하 파수꾼',94,112],'wild-stump':['golem','숲 그루터기',58,66],'armored-mushroom':['mushroom','철갑 버섯',68,70],'ore-beetle':['crystal-crab','광석 딱정벌레',68,52],'cave-sentinel':['golem','광산 파수꾼',84,98],'thorn-mantis':['golem','가시 사마귀',66,83],'ancient-treant':['golem','고대 나무정령',94,112]};for(const [kind,[hp,touchDamage]] of Object.entries(stageOf(area).mobs)) {
 const source=base.get(extra[kind]?.[0]||kind)||base.get(kind==='moss-slime'?'slime':'golem');if(source)kinds.set(kind,{...source,id:kind,hp,touchDamage,name:({'moss-slime':'이끼 슬라임','moss-guardian':'이끼 수호자'})[kind]||source.name,biome:area,...(extra[kind]?{sheet:null,name:extra[kind][1],size:{w:extra[kind][2],h:extra[kind][3]},rewardRank:kind.includes('sentinel')||kind.includes('ancient')||kind.includes('armored')?3:2}:{}),...(kind.startsWith('moss-')?{sheet:null}: {})});
 }return kinds;
}
