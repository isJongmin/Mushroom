import {cleanState,applyCommand} from './game/progression.js';
// IndexedDB read/write transactions serialize tabs and commit items + currency together.
// localStorage is only a UI snapshot/migration source when IndexedDB is available.
export function createProgressionStore(key,{job='warrior',storage=globalThis.localStorage,locks=null,indexedDB=globalThis.indexedDB,onChange=()=>{},guardCommand=()=>{}}={}) {
 const storageKey=key+':equipment-v1';let state,dbPromise;
 function read(){let raw;try{const text=storage.getItem(storageKey);raw=text?JSON.parse(text):null;}catch{if(indexedDB)return cleanState(null,job);throw new Error('성장 데이터를 읽을 수 없습니다. 브라우저 저장 설정을 확인해주세요.');}return cleanState(raw,job);}
 state=read();
 function db(){if(!dbPromise)dbPromise=new Promise((resolve,reject)=>{const r=indexedDB.open('mushroom-progression-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('states');r.onsuccess=()=>{r.result.onversionchange=()=>{r.result.close();dbPromise=null;};resolve(r.result);};r.onerror=()=>{dbPromise=null;reject(new Error('성장 저장소를 열 수 없습니다.'));};r.onblocked=()=>{reject(new Error('다른 게임 탭을 닫고 다시 시도해주세요.'));};});return dbPromise;}
 async function transact(command){const database=await db();return new Promise((resolve,reject)=>{
  const tx=database.transaction('states','readwrite'),records=tx.objectStore('states'),request=records.get(storageKey);let next,error;
  request.onsuccess=()=>{try{const current=cleanState(request.result??read(),job);guardCommand(command,current);next=applyCommand(current,command,{job});records.put(next.state,storageKey);}catch(e){error=e;tx.abort();}};
  tx.oncomplete=()=>{state=next.state;try{storage.setItem(storageKey,JSON.stringify(state));}catch{/* IndexedDB is the authoritative saved state. */}onChange(state);resolve(next.result);};
  tx.onabort=()=>reject(error||new Error('저장에 실패해 변경하지 못했습니다.'));tx.onerror=()=>{};
 });}
 return {get state(){return state;},key:storageKey,async run(command){
  if(indexedDB)return transact(command);
  // Dependency-injected fallback for deterministic transaction tests / secure legacy hosts.
  if(!locks?.request)throw new Error('이 브라우저에서 안전한 성장 저장소를 사용할 수 없습니다.');
  return locks.request(storageKey,async()=>{const current=read();guardCommand(command,current);const next=applyCommand(current,command,{job});try{storage.setItem(storageKey,JSON.stringify(next.state));}catch{throw new Error('저장 공간이 부족해 변경하지 못했습니다.');}state=next.state;onChange(state);return next.result;});
 },reload(){state=read();onChange(state);return state;},close(){dbPromise?.then(database=>database.close()).catch(()=>{});}};
}
