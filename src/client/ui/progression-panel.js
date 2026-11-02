import {h} from '../dom.js';
import {openModal} from './modal.js';
import {petSellPrice,petPrice,petBonuses,fusionSummary,GRADES,GRADE_COLORS,WEAPONS,ATTACK,DEFENSE,SELL,ITEM_NAMES,stageOf,itemName,loadout,combatStats,petSpec,PET_RATES,PET_PRICES,PET_ATK,PET_HP,PET_ESSENCE,PET_UPGRADE,PET_SELL,activeWeapon,activeJob,wornItem} from '../game/progression.js';
import {drawItem,drawPet} from '../game/progression-visuals.js';
import {createPetReveal} from './pet-reveal.js';

export function createProgressionPanel({main,store,job,getArea,onChange,onFocus,canDraw=()=>true}) {
 let modal=null,screen='bag',tab='equipment',bulk=false,selected=new Set(),detail=null;
 let filter='all';
 let busy=false,notice='',confirm=null,reveal=null,revealTimer=null,renderAc=null,destroyed=false;
 const body=h('div',{class:'growth-panel'});
 const reduced=()=>globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
 const worn=wornItem;
 const usable=()=>true;
 const badge=(text,tier)=>h('span',{class:'gp-grade',style:{color:GRADE_COLORS[tier]}},text);
 function button(text,fn,{disabled=false,testid,kind='',focus}={}) {
  const b=h('button',{type:'button',class:`gp-button ${kind}`,disabled,testid,'data-focus':focus||testid||text},text);
  b.addEventListener('click',fn,{signal:renderAc.signal});return b;
 }
 function petIcon(id,size=80){const cv=h('canvas',{width:80,height:80,'aria-hidden':true,style:{width:size+'px',height:size+'px'}});drawPet(cv.getContext('2d'),id,40,63,1.4,0);return cv;}
 function itemIcon(i){const cv=h('canvas',{width:72,height:72,'aria-hidden':true});drawItem(cv.getContext('2d'),i.kind,36,42,1.05,GRADE_COLORS[i.tier]);return cv;}
 function resetSelection(){selected.clear();detail=null;confirm=null;}
 function cancelReveal(){clearTimeout(revealTimer);revealTimer=null;}
 function present(){if(modal?.open&&!destroyed)paint();}
 async function run(command){
  if(busy||destroyed)return;busy=true;notice='';paint();
  try {
   const result=await store.run(command);
   if(command.type==='draw'){reveal=createPetReveal(result);confirm=null;}
   else if(command.type==='fuse-all'){resetSelection();notice=`${result.count}회 합성 완료 · 장비 ${result.before}개 → ${result.after}개`;}
   else if(command.type==='fuse'){detail=result.id;confirm=null;notice=`${itemName(result)} 합성 성공`;}
   else if(['sell','sell-many','pet-sell'].includes(command.type)){resetSelection();notice=`${result.toLocaleString()} G를 받았습니다.`;}
   onChange();
  }catch(e){notice=e.message;confirm=null;}
  finally{busy=false;present();if(command.type==='draw'&&modal?.open)body.querySelector('[data-testid="pet-reveal-next"]')?.focus({preventScroll:true});}
 }
 function beginReveal(){
  if(!reveal||!reveal.begin())return;paint();cancelReveal();
  const current=reveal;
  revealTimer=setTimeout(()=>{revealTimer=null;if(destroyed||!modal?.open||reveal!==current)return;current.reveal();paint();body.querySelector('[data-testid="pet-reveal-next"]')?.focus({preventScroll:true});},reduced()?80:850);
 }
 function paint(){
  const focus=body.contains(document.activeElement)?document.activeElement?.getAttribute('data-focus'):null;
  const scroll=modal?.section.scrollTop,gridScroll=body.querySelector('.gp-grid')?.scrollTop||0;
  renderAc?.abort();renderAc=new AbortController();body.replaceChildren();
  const s=store.state,stats=combatStats(loadout(s,job)),area=getArea();
  body.append(h('header',{class:'gp-header'},h('div',{},h('p',{class:'gp-eyebrow'},screen==='shop'?'LULU’S PET ATELIER':'ADVENTURER’S COLLECTION'),h('h2',{id:'growth-title'},screen==='shop'?`${stageOf(area).name} 펫 상점`:'모험가의 가방')),button('닫기',close,{disabled:busy,testid:'growth-close',kind:'gp-quiet'})),
   h('div',{class:'gp-wallet'},h('strong',{},`${s.gold.toLocaleString()} G`),h('span',{},`펫 정수 ${s.essence}`)));
  if(screen==='bag'){
   body.append(h('div',{class:'gp-bag-top'},h('div',{class:'gp-tabs',role:'tablist','aria-label':'가방 종류'},...['equipment','pets'].map(t=>{const b=button(t==='equipment'?`장비 ${s.items.length}`:`펫 ${Object.keys(s.pets).length}`,()=>{tab=t;bulk=false;resetSelection();notice='';paint();},{disabled:busy,focus:'tab-'+t});b.setAttribute('role','tab');b.setAttribute('aria-selected',String(tab===t));b.tabIndex=tab===t?0:-1;
    b.addEventListener('keydown',e=>{if(busy||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();tab=e.key==='Home'?'equipment':e.key==='End'?'pets':tab==='equipment'?'pets':'equipment';bulk=false;resetSelection();notice='';paint();body.querySelector('[data-focus="tab-'+tab+'"]')?.focus();},{signal:renderAc.signal});return b;})),h('p',{class:'gp-stats'},`공격 ${stats.attack} · 방어 ${stats.defense} · HP ${stats.maxHp}`)));
  }
  if(notice)body.append(h('p',{class:'gp-notice',role:'status',testid:'growth-notice'},notice));
  if(screen==='shop')paintShop(s,area);else if(tab==='equipment')paintEquipment(s);else paintPets(s);
  const currentGrid=body.querySelector('.gp-grid');if(currentGrid)currentGrid.scrollTop=gridScroll;
  if(focus){const target=[...body.querySelectorAll('[data-focus]')].find(e=>e.getAttribute('data-focus')===focus&&!e.disabled);target?.focus({preventScroll:true});}
  if(scroll!=null&&modal?.open)modal.section.scrollTop=scroll;
 }
 function paintEquipment(s){
  selected=new Set([...selected].filter(id=>s.items.some(i=>i.id===id)&&!worn(s,id)));
  const items=[...s.items].sort((a,b)=>Number(worn(s,b.id))-Number(worn(s,a.id))||b.tier-a.tier||a.kind.localeCompare(b.kind));
  if(bulk)body.append(h('div',{class:'gp-tools'},h('span',{class:'gp-muted'},bulk?'판매할 장비를 선택하세요. 착용 장비는 보호됩니다.':'무기를 바꾸면 공격과 스킬도 바뀝니다.'),button(bulk?'선택 종료':'선택 판매',()=>{bulk=!bulk;resetSelection();paint();},{disabled:busy,testid:'gear-bulk-toggle'})));
  if(bulk)body.append(h('div',{class:'gp-selection-tools'},button('전체 선택',()=>{selected=new Set(items.filter(i=>!worn(s,i.id)).map(i=>i.id));confirm=null;paint();},{disabled:busy,testid:'gear-select-all'}),button('다른 무기만',()=>{selected=new Set(items.filter(i=>!worn(s,i.id)&&i.kind!=='shield'&&i.kind!==activeWeapon(s)?.kind).map(i=>i.id));confirm=null;paint();},{disabled:busy,testid:'gear-select-other'}),button('선택 해제',()=>{selected.clear();confirm=null;paint();},{disabled:busy||!selected.size})));
  const grid=h('div',{class:'gp-grid',role:'group','aria-label':bulk?'판매할 장비 선택':'보유 장비'});
  const summary=fusionSummary(s.items);
  if(!bulk){
   body.append(h('div',{class:'gp-fusion-toolbar'},h('span',{class:'gp-muted'},`장비 ${s.items.length} / 200`),h('div',{class:'gp-actions'},button('선택 판매',()=>{bulk=true;resetSelection();paint();},{disabled:busy,testid:'gear-bulk-toggle'}),button(`일괄 합성${summary.count?' · '+summary.count+'회':''}`,()=>{confirm={type:'fuse-all'};paint();},{disabled:busy||!summary.count,kind:'gp-primary',testid:'gear-fuse-all'}))));
   if(confirm?.type==='fuse-all')body.append(h('section',{class:'gp-confirm',role:'region','aria-label':'일괄 합성 확인'},h('strong',{},`${summary.count}회 합성 · ${summary.before}개 → ${summary.after}개`),h('p',{},'모든 종류의 같은 등급 장비 2개를 합성합니다. 새로 만든 장비도 연속 합성하며, 착용 장비는 결과 장비로 자동 교체됩니다. 최고 등급은 유지됩니다.'),h('div',{class:'gp-actions'},button('취소',()=>{confirm=null;paint();},{disabled:busy}),button('모두 합성',()=>run({type:'fuse-all'}),{disabled:busy,kind:'gp-primary',testid:'gear-fuse-all-confirm'}))));
  }
  const filters=h('div',{class:'gp-filters','aria-label':'장비 종류'});
  for(const [kind,label]of [['all','전체'],...Object.entries(ITEM_NAMES)]){const b=button(label,()=>{filter=kind;detail=null;paint();},{disabled:busy,focus:'filter-'+kind});b.setAttribute('aria-pressed',String(filter===kind));filters.append(b);}body.append(filters);
  const groups=new Map();
  for(const i of items){const key=i.kind+':'+i.tier;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(i);}
  const visible=(bulk?items:[...groups.values()].map(g=>g[0])).filter(i=>filter==='all'||i.kind===filter);
  for(const i of visible){
   const isWorn=worn(s,i.id),active=bulk?selected.has(i.id):detail===i.id;
   const content=[h('span',{class:'gp-tile-top'},badge(GRADES[i.tier],i.tier),isWorn?h('span',{class:'gp-equipped'},'착용'):null),itemIcon(i),h('strong',{},ITEM_NAMES[i.kind]+(!bulk&&groups.get(i.kind+':'+i.tier).length>1?' ×'+groups.get(i.kind+':'+i.tier).length:'')),h('small',{},i.kind==='shield'?`방어 +${[4,9,16,26,40][i.tier]}`:`공격 ${ATTACK[i.tier]}`)];
   if(bulk){
    const check=h('input',{type:'checkbox',checked:active,disabled:busy||isWorn,'aria-label':`${itemName(i)} 판매 선택`,'data-focus':'gear-'+i.id});
    check.addEventListener('change',()=>{check.checked?selected.add(i.id):selected.delete(i.id);confirm=null;paint();},{signal:renderAc.signal});
    grid.append(h('label',{class:`gp-tile ${active?'is-selected':''} ${isWorn?'is-protected':''}`,style:{'--rarity':GRADE_COLORS[i.tier]}},check,...content));
   }else{
    const tile=button('',()=>{detail=i.id;confirm=null;paint();},{disabled:busy,focus:'gear-'+i.id,kind:`gp-tile ${active?'is-selected':''}`});tile.setAttribute('aria-label',`${itemName(i)} 상세${isWorn?', 착용 중':''}`);tile.setAttribute('aria-pressed',String(active));tile.style.setProperty('--rarity',GRADE_COLORS[i.tier]);tile.append(...content);grid.append(tile);
   }
  }
  if(!visible.length)grid.append(h('p',{class:'gp-empty'},'이 종류의 장비가 없습니다.'));
  body.append(grid);
  if(bulk){
   const total=s.items.filter(i=>selected.has(i.id)).reduce((sum,i)=>sum+SELL[i.tier],0);
   body.append(h('footer',{class:'gp-action-bar'},h('div',{},h('strong',{},`${selected.size}개 선택`),h('span',{class:'gp-muted'},`판매 금액 ${total.toLocaleString()} G`)),confirm?.type==='bulk'?h('div',{class:'gp-actions'},button('취소',()=>{confirm=null;paint();},{disabled:busy}),button(`${selected.size}개 판매 확정`,()=>run({type:'sell-many',ids:[...selected]}),{disabled:busy||!selected.size,kind:'gp-danger',testid:'gear-sell-confirm'})):button('선택 장비 판매',()=>{confirm={type:'bulk'};paint();},{disabled:busy||!selected.size,kind:'gp-primary',testid:'gear-sell-selected'})));
   return;
  }
  const i=s.items.find(i=>i.id===detail);if(!i){if(!bulk)body.append(h('p',{class:'gp-muted gp-hint'},'장비를 누르면 능력치와 착용·합성 메뉴가 열립니다.'));return;}
  const partner=i.tier<4?s.items.find(x=>x.id!==i.id&&x.kind===i.kind&&x.tier===i.tier&&!worn(s,x.id))||s.items.find(x=>x.id!==i.id&&x.kind===i.kind&&x.tier===i.tier):null;
  const current=s.items.find(x=>x.id===(i.kind==='shield'?s.shield:s.activeWeapon));
  const value=i.kind==='shield'?[4,9,16,26,40][i.tier]:ATTACK[i.tier],prior=current?(i.kind==='shield'?[4,9,16,26,40][current.tier]:ATTACK[current.tier]):i.kind==='shield'?0:20;
  const d=h('section',{class:'gp-detail','aria-label':'선택 장비 상세'},h('div',{},h('strong',{},itemName(i)),h('p',{class:'gp-muted'},usable(i)?`현재 장비 대비 ${value-prior>=0?'+':''}${value-prior} · ${i.kind==='shield'?'방어력':'공격력'} ${value}${i.kind==='shield'?'':` / 방어력 +${DEFENSE[i.tier]}`}`:'무기를 착용하면 해당 무기의 공격과 스킬로 바뀝니다.')));
  if(confirm?.type==='fuse')d.append(h('p',{class:'gp-confirm'},`${itemName(i)} 2개를 사용해 ${GRADES[i.tier+1]} ${ITEM_NAMES[i.kind]} 1개로 합성합니다. 성공률 100%. 착용 재료는 결과 장비로 교체됩니다.`),h('div',{class:'gp-actions'},button('취소',()=>{confirm=null;paint();},{disabled:busy}),button('합성 확정',()=>run({type:'fuse',a:i.id,b:confirm.partner}),{disabled:busy,kind:'gp-primary',testid:'growth-fuse'})));
  else d.append(h('div',{},h('div',{class:'gp-actions'},button(worn(s,i.id)?'착용 중':'착용',()=>run({type:'equip',id:i.id}),{disabled:busy||!usable(i)||worn(s,i.id),kind:'gp-primary'}),button(i.tier===4?'최고 등급':'합성',()=>{confirm={type:'fuse',partner:partner.id};paint();},{disabled:busy||!partner,testid:'gear-fuse-start'}),button('1개 판매',()=>{bulk=true;selected=new Set([i.id]);confirm=null;paint();},{disabled:busy||worn(s,i.id)})),!partner&&i.tier<4?h('small',{class:'gp-muted'},'합성에는 같은 종류·등급의 장비가 하나 더 필요해요.'):null));
  body.insertBefore(d,grid);
 }
 function paintPets(s){
  body.append(h('p',{class:'gp-muted'},'펫을 눌러 동행·강화·판매하세요. 한 마리만 동행할 수 있어요.'));
  const grid=h('div',{class:'gp-grid',role:'group','aria-label':'보유 펫'});
  for(const [id,p]of Object.entries(s.pets).sort(([a],[b])=>Number(s.pet===b)-Number(s.pet===a)||petSpec(b).tier-petSpec(a).tier)){
   const pet=petSpec(id),tile=button('',()=>{detail=id;confirm=null;paint();},{disabled:busy,kind:`gp-tile ${detail===id?'is-selected':''}`,focus:'pet-'+id});tile.setAttribute('aria-label',`${pet.name} 상세`);tile.style.setProperty('--rarity',GRADE_COLORS[pet.tier]);tile.append(h('span',{class:'gp-tile-top'},badge(GRADES[pet.tier],pet.tier),s.pet===id?h('span',{class:'gp-equipped'},'동행'):null),petIcon(id,64),h('strong',{},pet.name),h('small',{},`강화 +${p.level}`));grid.append(tile);
  }
  if(!grid.children.length)grid.append(h('p',{class:'gp-empty'},'아직 펫이 없어요. 마을의 펫 조련사 루루를 찾아보세요.'));body.append(grid);
  const p=s.pets[detail],pet=petSpec(detail);if(!p||!pet)return;
  const d=h('section',{class:'gp-detail','aria-label':'선택 펫 상세'},h('strong',{},`${pet.name} +${p.level}`),h('p',{class:'gp-muted'},`공격력 +${(petBonuses(pet.id,p.level).attack*100).toFixed(1)}% · HP +${petBonuses(pet.id,p.level).hp} · 자동 줍기`));
  if(confirm?.type==='pet-sell')d.append(h('p',{class:'gp-confirm'},`판매할 펫: ${pet.name} · ${petSellPrice(pet.id).toLocaleString()} G. 펫은 사라지며 강화에 쓴 정수는 반환되지 않습니다.`),h('div',{class:'gp-actions'},button('취소',()=>{confirm=null;paint();},{disabled:busy}),button('펫 판매 확정',()=>run({type:'pet-sell',id:detail}),{disabled:busy,kind:'gp-danger',testid:'pet-sell-confirm'})));
  else d.append(h('div',{},h('div',{class:'gp-actions'},button(s.pet===detail?'동행 해제':'동행하기',()=>run(s.pet===detail?{type:'pet-off'}:{type:'pet-equip',id:detail}),{disabled:busy,kind:'gp-primary',testid:'pet-equip-toggle'}),button(p.level>=5?'최대 강화':`강화 · 정수 ${PET_UPGRADE[p.level]}`,()=>run({type:'pet-upgrade',id:detail}),{disabled:busy||p.level>=5||s.essence<PET_UPGRADE[p.level]}),button(`판매 · ${petSellPrice(pet.id).toLocaleString()} G`,()=>{confirm={type:'pet-sell'};paint();},{disabled:busy||s.pet===detail,testid:'pet-sell-start'})),s.pet===detail?h('small',{class:'gp-muted'},'판매하려면 먼저 동행을 해제해주세요.'):null));
  body.append(d);
 }
 function paintShop(s,area){
  if(reveal){paintReveal();return;}
  const pity=s.pity[area]||[0,0,0];
  body.append(h('div',{class:'gp-shop-hero'},petIcon(area+':4',108),h('div',{},h('h3',{},'어떤 동료를 만나게 될까요?'),h('p',{class:'gp-muted'},'이 마을의 펫 5종 · 한 장씩 열어보세요.'))),
   h('div',{class:'gp-draw-options'},...[1,5,10].map(count=>button('',()=>{if(!canDraw()){notice='펫 조련사 가까이에서 이용해주세요.';paint();return;}run({type:'draw',area,count});},{disabled:busy||s.gold<petPrice(area,count),testid:`pet-draw-${count}`,kind:count===10?'is-featured':''})).map((b,n)=>{const count=[1,5,10][n];b.append(h('strong',{},`${count}마리 뽑기`),h('span',{},`${petPrice(area,count).toLocaleString()} G`),h('small',{},count===1?'한 장의 설렘':count===5?'5% 할인':'10% 할인'));return b;})),
   h('div',{class:'gp-pity'},h('strong',{},'다음 보장까지'),h('span',{},`희귀 이상 ${20-pity[0]}회 · 영웅 이상 ${80-pity[1]}회 · 전설 ${200-pity[2]}회`)));
  const info=h('details',{class:'gp-odds'},h('summary',{},'등장 펫 · 확률 보기'));
  const list=h('div',{class:'gp-pool'});PET_RATES.forEach((rate,tier)=>list.append(h('div',{},petIcon(area+':'+tier,48),h('strong',{},petSpec(area+':'+tier).name),badge(GRADES[tier],tier),h('span',{},`${(rate*100).toFixed(1)}%`),h('small',{},`공격 +${Math.round(petBonuses(area+':'+tier).attack*100)}% · HP +${petBonuses(area+':'+tier).hp}`))));
  info.append(list,h('p',{class:'gp-muted'},'기본 확률이며 보장 회차에는 상위 등급이 나올 수 있어요. 천장은 마을별로 유지되고 해당 등급 이상 획득 시 초기화됩니다. 중복은 등급별 정수 1/2/5/12/30개로 바뀝니다. 묶음도 한 번씩 같은 규칙을 적용합니다.'));body.append(info);
 }
 function paintReveal(){
  const phase=reveal.phase,current=reveal.current,pet=current?petSpec(current.id):null;
  if(phase==='summary'){
   body.append(h('h3',{class:'gp-result-title'},'새로운 만남의 기록'),h('div',{class:'gp-results',testid:'pet-results'},...reveal.shown.map(r=>{const p=petSpec(r.id);return h('article',{style:{'--rarity':GRADE_COLORS[p.tier]}},petIcon(r.id,64),h('strong',{},p.name),badge(GRADES[p.tier],p.tier),h('small',{},r.duplicate?`중복 · 정수 +${r.essence}`:'새로운 동료'));})),h('p',{class:'gp-muted'},'모든 결과가 저장되었습니다. 첫 펫은 자동으로 동행합니다.'),button('상점으로',()=>{reveal=null;paint();},{kind:'gp-primary',testid:'pet-results-done'}));return;
  }
  const revealed=phase==='revealed'||phase==='complete';
  const card=h('div',{class:`gp-reveal-card ${phase==='charging'?'is-charging':''} ${revealed?'is-revealed':''} ${revealed&&pet.tier>=3?'is-rare':''}`,style:{'--rarity':revealed?GRADE_COLORS[pet.tier]:'#91c6bf'},testid:'pet-reveal-card'});
  if(revealed){card.append(h('div',{class:'gp-reveal-rays','aria-hidden':true}),badge(GRADES[pet.tier],pet.tier),petIcon(current.id,150),h('h3',{},pet.name),h('p',{},current.duplicate?`중복 펫 · 정수 +${current.essence}`:'새로운 동료를 만났어요!'));}
  else card.append(h('span',{class:'gp-card-seal','aria-hidden':true},'?'),h('strong',{},phase==='charging'?'빛 속에서 누군가 다가옵니다…':'작은 카드 속, 새로운 동료'),h('small',{},'MUSHROOM PET COLLECTION'));
  body.append(h('div',{class:'gp-reveal-stage'},h('p',{class:'gp-reveal-progress'},`${revealed?reveal.index+1:reveal.index+2} / ${reveal.total}`),card,h('p',{class:'gp-reveal-announcement',role:'status','aria-live':'polite'},revealed?`${GRADES[pet.tier]} ${pet.name}${current.duplicate?', 중복 정수 '+current.essence+'개':''}`:phase==='charging'?'카드를 공개하고 있어요.':'카드를 열어 동료를 만나보세요.'),
   h('div',{class:'gp-actions'},button(phase==='complete'?'결과 모아보기':phase==='revealed'?'다음 카드':phase==='charging'?'공개 중…':'카드 열기',()=>{if(phase==='complete'){reveal.summary();paint();}else{if(phase==='revealed')reveal.next();beginReveal();}},{disabled:phase==='charging',kind:'gp-primary',testid:'pet-reveal-next'}),button('모두 공개',()=>{cancelReveal();reveal.skip();paint();body.querySelector('[data-testid="pet-results-done"]')?.focus({preventScroll:true});},{kind:'gp-quiet',testid:'pet-reveal-skip'})),h('small',{class:'gp-muted'},'결과는 이미 저장되어 있어요. 닫아도 획득한 펫은 유지됩니다.')));
 }
 function close(){if(busy)return;cancelReveal();renderAc?.abort();modal?.close();modal=null;reveal=null;onFocus();}
 return {
  open(mode='equipment'){if(busy||destroyed)return;cancelReveal();screen=mode==='shop'?'shop':'bag';tab=mode==='pets'?'pets':'equipment';bulk=false;filter='all';resetSelection();notice='';reveal=null;paint();modal=openModal({main,titleId:'growth-title',testid:'growth-panel',children:[body],onCancel:close,canEscape:()=>!busy,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal');},
  refresh(){if(modal?.open&&!busy&&!reveal)paint();},
  destroy(){destroyed=true;cancelReveal();renderAc?.abort();modal?.close({restoreFocus:false});modal=null;},
 };
}
