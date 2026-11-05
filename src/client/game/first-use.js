export const FIRST_USE_GUIDES=Object.freeze({
 controls:{title:'두 손으로 함께 조작',text:'왼손으로 이동하면서 오른손으로 공격·스킬을 누르세요. 방향키는 두 번 연타하면 대시합니다.'},
 skills:{title:'스킬 사용',text:'아이콘을 누르면 즉시 발동합니다. 숫자는 남은 재사용 시간이며, 두 번째 스킬은 레벨 5, 궁극기는 레벨 12에 열립니다.'},
 bag:{title:'가방',text:'장비나 펫을 누르면 착용·합성·판매 메뉴가 나옵니다. 펫은 최대 3마리까지 함께 다닙니다.'},
 traits:{title:'모험 특성',text:'지역의 수련 스승에게 퀘스트를 받고 완료 보고하세요. 얻은 포인트로 공격력·체력·재사용 시간을 강화합니다.'},
 npc:{title:'가까이에서 대화',text:'가까이 다가가 대화 버튼이나 E키를 누르세요. 마스코트와 재미 NPC는 비용·능력치 변동 없이 수다를 즐길 수 있습니다.'},
 map:{title:'미니맵',text:'노랑은 나, 파랑은 다른 유저, 초록은 NPC입니다. ＋와 −로 펼치거나 접으세요.'},
 drops:{title:'바닥 아이템',text:'가까이 가면 자동으로 줍습니다. 떨어진 아이템과 골드는 3분 뒤 사라지며, 가방에 넣은 아이템은 유지됩니다.'},
 taxi:{title:'마을 택시',text:'해금한 마을을 골라 무료로 이동하세요. 잠긴 지역은 필요한 등급의 주무기를 획득하면 열립니다.'},
 boss:{title:'보스 도전',text:'등장 후 바닥의 공격 표식을 피하세요. 약점 노출 때가 공격 기회입니다. 전투 중에도 이동과 스킬을 함께 사용할 수 있습니다.'},
});
export function createFirstUseHints(key,options={}){
 let storage=options.storage;try{storage??=globalThis.localStorage;}catch{}
 const storageKey=key+':first-use:v1';let seen=new Set(),queue=[],active=null;
 try{const raw=JSON.parse(storage?.getItem(storageKey)||'[]');if(Array.isArray(raw))seen=new Set(raw.filter(id=>Object.hasOwn(FIRST_USE_GUIDES,id)));}catch{}
 function persist(){try{storage?.setItem(storageKey,JSON.stringify([...seen]));}catch{}}
 return {request(id,now,force=false){if(!Object.hasOwn(FIRST_USE_GUIDES,id)||(!force&&seen.has(id))||active?.id===id||queue.includes(id))return false;if(force)active=null;queue.push(id);return true;},
 update(now,blocked=false){if(active&&now>=active.until)active=null;if(blocked)return null;
  if(!active&&queue.length){const id=queue.shift();active={id,...FIRST_USE_GUIDES[id],until:now+7000};seen.add(id);persist();}return active;
 },dismiss(){active=null;},clear(){queue=[];active=null;},hasSeen:id=>seen.has(id)};
}
