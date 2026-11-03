import {cleanState,STAGES,stageUnlocked} from './progression.js';
import {adventureProgress} from './adventure-level.js';
import {ROOM_CAPACITY} from '../constants.js';
export function readAdventurer(key,{storage}={}){
 let raw=null;try{storage??=globalThis.localStorage;raw=JSON.parse(storage.getItem(key+':equipment-v1')||'null');}catch{}
 const state=cleanState(raw);
 return {state,level:adventureProgress(state).level,gold:state.gold,petCount:Object.keys(state.pets).length,
  regions:Object.keys(STAGES).filter(area=>stageUnlocked(state,null,area)).length};
}
export const roomMatches=(room,query)=>!query.trim()||room.name.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
export function recommendedRoom(rooms){return rooms.filter(r=>!r.locked&&r.members<ROOM_CAPACITY).sort((a,b)=>Number(!!b.mine)-Number(!!a.mine)||b.members-a.members||a.name.localeCompare(b.name))[0]||null;}
