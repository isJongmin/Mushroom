// One balance contract for loot, equipment, stages and pets. No real-money purchases.
export const GRADES = Object.freeze(['일반','고급','희귀','영웅','전설']);
export const GRADE_COLORS = ['#9aaeb6','#65c795','#73b6ff','#bc92ff','#f4ce70'];
export const WEAPONS = Object.freeze({warrior:'sword',archer:'bow',mage:'staff',thief:'claw'});
export const ITEM_NAMES = {sword:'검',bow:'활',staff:'스태프',claw:'아대',shield:'방패'};
export const ATTACK = [20,32,51,82,131];
export const DEFENSE = [0,3,7,13,22];
export const SELL = [15,40,110,300,800];
export const STAGES = Object.freeze({
 village:{order:1,name:'버섯마을',recommended:0,drop:[.80,.18,.02,0,0],mobs:{snail:[40,5],mushroom:[65,8],slime:[90,10]},petNames:['아기버섯','새싹슬라임','도토리다람쥐','달빛사슴','황금버섯왕']},
 quarry:{order:2,name:'광산마을',recommended:1,drop:[.10,.70,.18,.02,0],mobs:{bat:[150,15],'crystal-crab':[220,19],golem:[300,24]},petNames:['광석두더지','꼬마박쥐','수정게','자수정골렘','별빛드래곤']},
 forest:{order:3,name:'이끼마을',recommended:2,drop:[0,.10,.70,.18,.02],mobs:{'moss-slime':[420,28],'forest-stump':[560,33],'moss-guardian':[720,39]},petNames:['이끼방울','잎새토끼','반딧불정령','고대숲사슴','세계수정령']},
});
export const PET_RATES = [.65,.25,.08,.018,.002];
export const PET_PRICES = {1:200,5:950,10:1800};
export const PET_ATK = [.02,.04,.07,.10,.15];
export const PET_HP = [5,10,20,35,60];
export const PET_ESSENCE = [1,2,5,12,30];
export const PET_SELL = [20,60,180,600,2000];
export const PET_UPGRADE = [5,10,20,35,55];
export const stageOf = id => Object.hasOwn(STAGES,id)?STAGES[id]:STAGES.village;
export const tierOK = n => Number.isInteger(n)&&n>=0&&n<5;
export const itemOK = i => !!i&&typeof i.id==='string'&&i.id.length>0&&i.id.length<=160&&Object.hasOwn(ITEM_NAMES,i.kind)&&tierOK(i.tier);
export function petSpec(id) {
 if(typeof id!=='string'||!/^(village|quarry|forest):[0-4]$/.test(id))return null;
 const [area,t]=id.split(':');const tier=Number(t);
 return Object.hasOwn(STAGES,area)&&String(tier)===t&&tierOK(tier)?{id,area,tier,name:STAGES[area].petNames[tier]}:null;
}
export const itemName = i => `${GRADES[i.tier]} ${ITEM_NAMES[i.kind]}`;
export function weighted(rates,rnd=Math.random){let n=rnd();for(let i=0;i<rates.length;i++){n-=rates[i];if(n<0)return i;}return rates.length-1;}
export function rollEquipment(area,rnd=Math.random){
 const out=[];if(rnd()<.65)out.push({kind:['sword','bow','staff','claw'][Math.min(3,Math.floor(rnd()*4))],tier:weighted(stageOf(area).drop,rnd)});
 if(rnd()<.10)out.push({kind:'shield',tier:weighted(stageOf(area).drop,rnd)});
 return out;
}
export function starterState(job='warrior') {return {version:1,revision:0,gold:0,items:[{id:'starter-'+job,kind:WEAPONS[job]||'sword',tier:0}],equipped:{[job]:'starter-'+job},shield:null,highest:{[job]:0},pets:{},pet:null,essence:0,pity:{},pending:[],seen:[],kills:{village:0,quarry:0,forest:0}};}
export function cleanState(raw,job='warrior') {
 if(!raw||raw.version!==1)return starterState(job);
 const s=starterState(job),nat=(n,max=1e9)=>Number.isSafeInteger(n)?Math.max(0,Math.min(max,n)):0;
 s.revision=nat(raw.revision);s.gold=nat(raw.gold);s.essence=nat(raw.essence);
 const ids=new Set();s.items=(Array.isArray(raw.items)?raw.items:[]).filter(i=>itemOK(i)&&!ids.has(i.id)&&ids.add(i.id)).slice(0,200).map(i=>({id:i.id,kind:i.kind,tier:i.tier}));
 s.equipped={};s.highest={};for(const j of Object.keys(WEAPONS)){
 const item=s.items.find(i=>i.id===raw.equipped?.[j]&&i.kind===WEAPONS[j]);if(item)s.equipped[j]=item.id;
 s.highest[j]=Math.max(tierOK(raw.highest?.[j])?raw.highest[j]:0,...s.items.filter(i=>i.kind===WEAPONS[j]).map(i=>i.tier));
 }
 s.shield=s.items.some(i=>i.id===raw.shield&&i.kind==='shield')?raw.shield:null;
 for(const [id,p] of Object.entries(raw.pets||{}).slice(0,15))if(petSpec(id))s.pets[id]={level:nat(p?.level,5)};
 s.pet=s.pets[raw.pet]?raw.pet:null;
 for(const area of Object.keys(STAGES)) {const p=raw.pity?.[area];s.pity[area]=[nat(p?.[0],19),nat(p?.[1],79),nat(p?.[2],199)];s.kills[area]=nat(raw.kills?.[area]);}
 s.seen=Array.isArray(raw.seen)?raw.seen.filter(i=>typeof i==='string'&&i.length<=160).slice(-10000):[];
 s.pending=(Array.isArray(raw.pending)?raw.pending:[]).filter(d=>itemOK(d)&&Object.hasOwn(STAGES,d.area)&&Number.isFinite(d.x)&&Number.isFinite(d.y)&&Math.abs(d.x)<1e5&&Math.abs(d.y)<1e5).slice(0,200).map(d=>({...d}));return s;
}
export function loadout(s,job) {
 const weapon=s.items.find(i=>i.id===s.equipped[job]&&i.kind===WEAPONS[job]);
 const shield=job==='warrior'?s.items.find(i=>i.id===s.shield&&i.kind==='shield'):null;
 return {tier:weapon?.tier??0,highest:s.highest[job]??0,shield:shield?.tier??-1,pet:s.pet,level:s.pets[s.pet]?.level??0};
}
export function cleanLoadout(l) {const p=petSpec(l?.pet);return {tier:tierOK(l?.tier)?l.tier:0,highest:Math.max(tierOK(l?.tier)?l.tier:0,tierOK(l?.highest)?l.highest:0),shield:tierOK(l?.shield)?l.shield:-1,pet:p?.id??null,level:Number.isInteger(l?.level)?Math.max(0,Math.min(5,l.level)):0};}
export function combatStats(raw) {
 const l=cleanLoadout(raw),pet=petSpec(l.pet),bonus=pet?PET_ATK[pet.tier]*(1+l.level*.1):0;
 return {attack:Math.round(ATTACK[l.tier]*(1+bonus)),multiplier:ATTACK[l.tier]/20*(1+bonus),defense:DEFENSE[l.tier]+(l.shield<0?0:[4,9,16,26,40][l.shield]),maxHp:100+(pet?Math.round(PET_HP[pet.tier]*(1+l.level*.1)):0),pickup:pet?240:26};
}
export const skillUnlocked = (l,slot) => slot<=1 || cleanLoadout(l).highest>=slot-1;
export const stageUnlocked = (s,job,area) => (s.highest[job]??0)>=stageOf(area).recommended;
export function applyCommand(original,command,{job='warrior',rnd=Math.random,id=()=>globalThis.crypto.randomUUID?.()||Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('')}={}) {
 const s=cleanState(original,job),c=command;let result=null;
 const fail=m=>{throw new Error(m);};
 if(c.type==='ensure') {if(!s.items.some(i=>i.kind===WEAPONS[job])){const i={id:id(),kind:WEAPONS[job],tier:0};s.items.push(i);s.equipped[job]=i.id;}}
 else if(c.type==='loot') {
  if(typeof c.receipt!=='string'||c.receipt.length>150||!Object.hasOwn(STAGES,c.area))fail('잘못된 드롭 정보입니다.');
  if(s.seen.includes(c.receipt))return {state:s,result:{duplicate:true}};
  if(!Array.isArray(c.items)||c.items.length>2||c.items.some(i=>!itemOK({...i,id:'check'})))fail('잘못된 장비입니다.');
  if(s.pending.length+c.items.length>200)fail('바닥 장비가 너무 많습니다. 먼저 장비를 주워주세요.');
  if(!Number.isFinite(c.x)||!Number.isFinite(c.y)||Math.abs(c.x)>1e5||Math.abs(c.y)>1e5)fail('잘못된 드롭 위치입니다.');
  s.seen.push(c.receipt);s.seen=s.seen.slice(-10000);s.kills[c.area]++;
  c.items.forEach((i,n)=>s.pending.push({id:c.receipt+':'+n,kind:i.kind,tier:i.tier,area:c.area,x:c.x+n*24,y:c.y}));
 }
 else if(c.type==='collect') {
  const d=s.pending.find(i=>i.id===c.id);if(!d)fail('이미 주운 장비입니다.');if(s.items.length>=200)fail('가방이 가득 찼습니다. 장비를 판매하거나 합성해주세요.');
  s.pending=s.pending.filter(i=>i.id!==d.id);s.items.push({id:d.id,kind:d.kind,tier:d.tier});
  const j=Object.keys(WEAPONS).find(j=>WEAPONS[j]===d.kind);if(j)s.highest[j]=Math.max(s.highest[j]||0,d.tier);result=d;
 }
 else if(c.type==='equip') {const i=s.items.find(i=>i.id===c.id);if(!i)fail('장비가 없습니다.');if(i.kind==='shield'&&job==='warrior')s.shield=i.id;else if(i.kind===WEAPONS[job])s.equipped[job]=i.id;else fail('현재 직업이 사용할 수 없는 장비입니다.');}
 else if(c.type==='unequip-shield')s.shield=null;
 else if(c.type==='sell-many') {
 if(!Array.isArray(c.ids)||!c.ids.length||c.ids.length>200||new Set(c.ids).size!==c.ids.length)fail('판매할 장비를 선택해주세요.');
 const equipped=new Set([...Object.values(s.equipped),s.shield]);
 const items=c.ids.map(id=>s.items.find(i=>i.id===id));
 if(items.some(i=>!i))fail('일부 장비가 이미 판매되었거나 없습니다.');
 if(items.some(i=>equipped.has(i.id)))fail('착용 중인 장비는 판매할 수 없습니다.');
 const ids=new Set(c.ids);result=items.reduce((sum,i)=>sum+SELL[i.tier],0);
 s.items=s.items.filter(i=>!ids.has(i.id));s.gold=Math.min(1e9,s.gold+result);
 }
 else if(c.type==='pet-sell') {
 const p=petSpec(c.id);if(!p||!s.pets[c.id])fail('이미 판매된 펫입니다.');
 if(s.pet===c.id)fail('동행을 해제한 뒤 판매해주세요.');
 result=PET_SELL[p.tier];delete s.pets[c.id];s.gold=Math.min(1e9,s.gold+result);
 }
 else if(c.type==='sell') {
 const i=s.items.find(i=>i.id===c.id);if(!i)fail('이미 판매된 장비입니다.');if(Object.values(s.equipped).includes(i.id)||s.shield===i.id)fail('착용 중인 장비는 판매할 수 없습니다.');
 s.items=s.items.filter(x=>x.id!==i.id);s.gold=Math.min(1e9,s.gold+SELL[i.tier]);result=SELL[i.tier];
 }
 else if(c.type==='fuse') {
 const a=s.items.find(i=>i.id===c.a),b=s.items.find(i=>i.id===c.b);if(!a||!b||a.id===b.id||a.kind!==b.kind||a.tier!==b.tier||a.tier>=4)fail('같은 종류·등급의 장비 2개가 필요합니다.');
 const next={id:id(),kind:a.kind,tier:a.tier+1};s.items=s.items.filter(i=>i.id!==a.id&&i.id!==b.id);s.items.push(next);
 for(const j of Object.keys(WEAPONS)) {if([a.id,b.id].includes(s.equipped[j]))s.equipped[j]=next.id;if(WEAPONS[j]===a.kind)s.highest[j]=Math.max(s.highest[j]||0,next.tier);}
 if([a.id,b.id].includes(s.shield))s.shield=next.id;result=next;
 }
 else if(c.type==='draw') {
 if(!Object.hasOwn(STAGES,c.area)||![1,5,10].includes(c.count))fail('잘못된 뽑기입니다.');if(!stageUnlocked(s,job,c.area))fail('먼저 해당 마을을 해금해주세요.');
 const price=PET_PRICES[c.count];if(s.gold<price)fail('골드가 부족합니다.');s.gold-=price;result=[];
 for(let n=0;n<c.count;n++) {
 const pity=s.pity[c.area]||[0,0,0];let tier=weighted(PET_RATES,rnd);
 if(pity[2]>=199)tier=4;else if(pity[1]>=79)tier=Math.max(3,tier);else if(pity[0]>=19)tier=Math.max(2,tier);
 s.pity[c.area]=[tier>=2?0:pity[0]+1,tier>=3?0:pity[1]+1,tier>=4?0:pity[2]+1];
 const pid=c.area+':'+tier,duplicate=!!s.pets[pid];if(duplicate)s.essence+=PET_ESSENCE[tier];else s.pets[pid]={level:0};
 result.push({id:pid,duplicate,essence:duplicate?PET_ESSENCE[tier]:0});if(!s.pet)s.pet=pid;
 }
 }
 else if(c.type==='pet-equip') {if(!s.pets[c.id])fail('보유하지 않은 펫입니다.');s.pet=c.id;}
 else if(c.type==='pet-off')s.pet=null;
 else if(c.type==='pet-upgrade') {const p=s.pets[c.id];if(!p||p.level>=5)fail('더 강화할 수 없습니다.');const cost=PET_UPGRADE[p.level];if(s.essence<cost)fail('펫 정수가 부족합니다.');s.essence-=cost;p.level++;}
 else fail('알 수 없는 동작입니다.');
 s.revision++;return {state:s,result};
}
export function stageKinds(base,area){
 const kinds=new Map(base);for(const [kind,[hp,touchDamage]] of Object.entries(stageOf(area).mobs)) {
 const source=base.get(kind)||base.get(kind==='moss-slime'?'slime':'golem');if(source)kinds.set(kind,{...source,id:kind,hp,touchDamage,name:({'moss-slime':'이끼 슬라임','moss-guardian':'이끼 수호자'})[kind]||source.name,biome:area,...(kind.startsWith('moss-')?{sheet:null}: {})});
 }return kinds;
}
