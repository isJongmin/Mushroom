import {h} from '../dom.js';
import {openModal} from './modal.js';
import {GRADES,GRADE_COLORS,WEAPONS,ATTACK,DEFENSE,SELL,STAGES,stageOf,itemName,loadout,combatStats,petSpec,PET_RATES,PET_PRICES,PET_ATK,PET_HP,PET_ESSENCE,PET_UPGRADE,skillUnlocked} from '../game/progression.js';
import {drawItem,drawPet} from '../game/progression-visuals.js';
export function createProgressionPanel({main,store,job,getArea,onChange,onFocus,canDraw=()=>true}) {
 let modal=null,shopAvailable=false,tab='equipment',selected=[],busy=false,notice='',results=[],confirmSale=null,renderAc=null;
 const body=h('div',{class:'growth-panel'});
 const btn=(text,fn,disabled=false,testid)=>{const e=h('button',{type:'button',class:'bk-btn bk-btn--sm',disabled,testid},text);e.addEventListener('click',fn,{signal:renderAc.signal});return e;};
 const badge=(text,color)=>h('span',{class:'growth-badge',style:{color}},text);
 function icon(kind,tier){const cv=h('canvas',{width:72,height:72,'aria-hidden':true});drawItem(cv.getContext('2d'),kind,36,42,1.05,GRADE_COLORS[tier]);return cv;}
 function petIcon(id){const cv=h('canvas',{width:80,height:80,'aria-hidden':true});drawPet(cv.getContext('2d'),id,40,63,1.4,0);return cv;}
 async function run(command){if(busy)return;busy=true;notice='';paint();try{const r=await store.run(command);if(command.type==='draw')results=r;else if(command.type==='fuse'){selected=[];notice=`${itemName(r)} 합성 성공!`;}else if(command.type==='sell')notice=`${r}골드를 받았습니다.`;onChange();}catch(e){notice=e.message;}finally{busy=false;confirmSale=null;if(modal?.open)paint();}}
 function paint(){
 renderAc?.abort();renderAc=new AbortController();const s=store.state,l=loadout(s,job),stats=combatStats(l),area=getArea();body.replaceChildren();
 body.append(h('div',{class:'growth-heading'},h('div',{},h('p',{class:'growth-eyebrow'},'MUSHROOM · ADVENTURE'),h('h2',{id:'growth-title'},tab==='shop'?`${stageOf(area).name} 펫 상점`:'모험가의 가방')),btn('닫기',close,busy,'growth-close')),
 h('div',{class:'growth-wallet'},badge(`${s.gold.toLocaleString()} G`,'#e9be68'),badge(`펫 정수 ${s.essence}`,'#a9cdec'),h('span',{},`장비 ${s.items.length}/200`)),
 h('div',{class:'growth-stats'},h('strong',{},`장비 공격력 ${stats.attack}`),h('span',{},`방어력 ${stats.defense}`),h('span',{},`최대 HP ${stats.maxHp}`)),
 h('p',{class:'growth-muted'},'이 브라우저에 자동 저장됩니다. 계정 간 거래·현금 구매는 없습니다.'),
 h('nav',{class:'growth-tabs','aria-label':'성장 메뉴'},...['equipment','pets','stages',...(shopAvailable?['shop']:[])].map(t=>btn(({equipment:'장비 · 합성',pets:'보유 펫',stages:'마을 안내',shop:'지역 뽑기'})[t],()=>{tab=t;selected=[];results=[];notice='';paint();},busy||tab===t))));
 if(notice)body.append(h('p',{class:'growth-notice',role:'status',testid:'growth-notice'},notice));
 if(tab==='equipment'){
 body.append(h('p',{class:'growth-muted'},'같은 종류·등급 2개를 선택해 확정 합성합니다. 착용 장비를 합성하면 결과 장비로 자동 교체됩니다. 방패는 검사 전용입니다.'));
 const a=s.items.find(i=>i.id===selected[0]),b=s.items.find(i=>i.id===selected[1]);const valid=a&&b&&a.kind===b.kind&&a.tier===b.tier&&a.tier<4;
 body.append(h('div',{class:'growth-fusion'},h('span',{},valid?`${itemName(a)} + ${itemName(b)} → ${GRADES[a.tier+1]} · ${a.kind==='shield'?'방어력 '+[4,9,16,26,40][a.tier+1]:'공격력 '+ATTACK[a.tier+1]} · 성공률 100%`:`합성 재료 ${selected.length}/2 선택`),btn('합성하기',()=>run({type:'fuse',a:a.id,b:b.id}),busy||!valid,'growth-fuse'),btn('선택 해제',()=>{selected=[];paint();},busy||!selected.length)));
 const grid=h('div',{class:'growth-grid'});
 for(const i of [...s.items].sort((a,b)=>b.tier-a.tier||a.kind.localeCompare(b.kind))){
 const equipped=Object.values(s.equipped).includes(i.id)||s.shield===i.id,usable=i.kind===WEAPONS[job]||i.kind==='shield'&&job==='warrior';
 const checkbox=h('input',{type:'checkbox',checked:selected.includes(i.id),disabled:busy||i.tier===4,'aria-label':`${itemName(i)} 합성 재료 선택`});checkbox.addEventListener('change',()=>{if(checkbox.checked){if(selected.length<2)selected.push(i.id);}else selected=selected.filter(x=>x!==i.id);paint();},{signal:renderAc.signal});
 const isShield=i.kind==='shield';const current=s.items.find(x=>x.id===(isShield?s.shield:s.equipped[job]));const value=isShield?[4,9,16,26,40][i.tier]:ATTACK[i.tier],prior=current?(isShield?[4,9,16,26,40][current.tier]:ATTACK[current.tier]):isShield?0:20;
 const card=h('article',{class:'growth-card'+(selected.includes(i.id)?' is-selected':''),style:{'--rarity':GRADE_COLORS[i.tier]}},h('div',{class:'growth-card-top'},badge(GRADES[i.tier],GRADE_COLORS[i.tier]),checkbox),icon(i.kind,i.tier),h('strong',{},itemName(i)),h('small',{},isShield?`방어력 +${value}`:`공격력 ${value} · 방어력 +${DEFENSE[i.tier]}`),h('small',{class:'growth-muted'},usable?`현재 장비 대비 ${value-prior>=0?'+':''}${value-prior}`:'다른 직업 장비 · 판매 가능'),h('div',{class:'growth-actions'},btn(equipped?'착용 중':'착용',()=>run({type:'equip',id:i.id}),busy||!usable||equipped),btn(confirmSale===i.id?'판매 확정':`${SELL[i.tier]} G 판매`,()=>{if(confirmSale===i.id)run({type:'sell',id:i.id});else{confirmSale=i.id;paint();}},busy||equipped)));
 grid.append(card);
 }body.append(grid);
 }else if(tab==='pets'){
 body.append(h('p',{class:'growth-muted'},'1마리 장착 · 모든 펫 자동 줍기 240 · 중복 펫은 정수로 변환 · 강화당 기본 능력치 10% 증가 (최대 +5)'),btn('펫 장착 해제',()=>run({type:'pet-off'}),busy||!s.pet));
 const grid=h('div',{class:'growth-grid'});for(const [id,p] of Object.entries(s.pets)){
 const pet=petSpec(id);grid.append(h('article',{class:'growth-card',style:{'--rarity':GRADE_COLORS[pet.tier]}},badge(GRADES[pet.tier],GRADE_COLORS[pet.tier]),petIcon(id),h('strong',{},`${pet.name} +${p.level}`),h('small',{},`공격력 +${(PET_ATK[pet.tier]*(1+p.level*.1)*100).toFixed(1)}% · HP +${Math.round(PET_HP[pet.tier]*(1+p.level*.1))}`),h('div',{class:'growth-actions'},btn(s.pet===id?'동행 중':'장착',()=>run({type:'pet-equip',id}),busy||s.pet===id),btn(p.level>=5?'최대 강화':`강화 · 정수 ${PET_UPGRADE[p.level]}`,()=>run({type:'pet-upgrade',id}),busy||p.level>=5||s.essence<PET_UPGRADE[p.level]))));
 }if(!grid.children.length)grid.append(h('p',{},'마을의 펫 조련사 루루에게 첫 동료를 뽑아보세요.'));body.append(grid);
 }else if(tab==='shop'){
 const pity=s.pity[area]||[0,0,0];
 body.append(h('p',{class:'growth-muted'},'골드는 장비 판매로 얻습니다. 묶음 뽑기도 1회씩 같은 확률·천장 규칙을 적용합니다.'),h('div',{class:'growth-pity'},`희귀 이상 ${20-pity[0]}회 이내 · 영웅 이상 ${80-pity[1]}회 이내 · 전설 ${200-pity[2]}회 이내 보장`),h('p',{class:'growth-muted'},'천장은 마을별로 유지됩니다. 해당 등급 이상 획득 시 해당 천장만 초기화됩니다. 보장 회차에는 아래 기본 확률보다 높은 등급이 나올 수 있습니다.'),h('div',{class:'growth-draw-actions'},...[1,5,10].map(count=>btn(`${count}마리 · ${PET_PRICES[count].toLocaleString()} G`,()=>{if(!canDraw()){notice='이 마을의 펫 NPC 가까이에서 이용해주세요.';paint();return;}run({type:'draw',area,count});},busy||s.gold<PET_PRICES[count],`pet-draw-${count}`))));
 if(results.length)body.append(h('div',{class:'growth-results',role:'status',testid:'pet-results'},...results.map(r=>{const p=petSpec(r.id);return h('div',{class:'growth-result',style:{'--rarity':GRADE_COLORS[p.tier]}},petIcon(r.id),h('strong',{},p.name),badge(GRADES[p.tier],GRADE_COLORS[p.tier]),h('small',{},r.duplicate?`중복 · 정수 +${r.essence}`:'새로운 동료'));})));
 const grid=h('div',{class:'growth-grid'});PET_RATES.forEach((rate,t)=>{const id=area+':'+t;grid.append(h('article',{class:'growth-card',style:{'--rarity':GRADE_COLORS[t]}},petIcon(id),h('strong',{},petSpec(id).name),badge(`${GRADES[t]} · ${(rate*100).toFixed(1)}%`,GRADE_COLORS[t]),h('small',{},`공격력 +${Math.round(PET_ATK[t]*100)}% · HP +${PET_HP[t]}`),h('small',{class:'growth-muted'},`중복 시 정수 ${PET_ESSENCE[t]}`)));});body.append(grid);
 }else{
 for(const [id,st] of Object.entries(STAGES).sort((a,b)=>a[1].order-b[1].order))body.append(h('article',{class:'growth-stage-card'},h('h3',{},`${st.order}차 · ${st.name}`),h('p',{},`진입: ${GRADES[st.recommended]} 주무기 획득 · 처치 ${s.kills[id]||0}마리`),h('p',{},Object.entries(st.mobs).map(([kind,[hp,damage]])=>`${({'snail':'달팽이','mushroom':'버섯','slime':'슬라임','bat':'박쥐','crystal-crab':'수정게','golem':'골렘','moss-slime':'이끼 슬라임','forest-stump':'숲 그루터기','moss-guardian':'이끼 수호자'})[kind]} HP ${hp} / 접촉 ${damage}`).join(' · ')),h('small',{class:'growth-muted'},`주무기 드롭 65% · 방패 별도 10% · 등급: ${st.drop.map((r,t)=>r?GRADES[t]+' '+Math.round(r*100)+'%':null).filter(Boolean).join(' / ')}`)));
 body.append(h('p',{class:'growth-muted'},`스킬: 공격 스킬은 처음부터 · 고급 주무기 획득 시 보조 스킬 · 희귀 주무기 획득 시 궁극기. 현재 ${[1,2,3].filter(slot=>skillUnlocked(l,slot)).length}/3 해금. 한 번 해금하면 유지됩니다.`));
 }
 }
 function close(){if(busy)return;renderAc?.abort();modal?.close();modal=null;onFocus();}
 return {open(mode='equipment'){shopAvailable=mode==='shop';tab=mode;selected=[];results=[];notice='';paint();modal=openModal({main,titleId:'growth-title',testid:'growth-panel',children:[body],onCancel:close,canEscape:()=>!busy,fallbackFocus:()=>main.querySelector('canvas')});modal.section.classList.add('growth-modal');},refresh(){if(modal?.open&&!busy)paint();},destroy(){renderAc?.abort();modal?.close({restoreFocus:false});modal=null;}};
}
