import assert from 'node:assert/strict';
import {readAdventurer,recommendedRoom,roomMatches} from '../src/client/game/portal-model.js';
import {starterState} from '../src/client/game/progression.js';
import {mount} from '../src/client/screens/home.js';

const save=starterState();save.kills.village=8;save.gold=230;save.highest.warrior=2;save.pets={'village:0':{level:1}};
const summary=readAdventurer('qa',{storage:{getItem:k=>{assert.equal(k,'qa:equipment-v1');return JSON.stringify(save);}}});
assert.equal(summary.level,2);assert.equal(summary.gold,230);assert.equal(summary.regions,3);assert.equal(summary.petCount,1);
assert.equal(readAdventurer('qa',{storage:{getItem(){throw Error('blocked');}}}).level,1);
assert.equal(readAdventurer('qa',{storage:{getItem:()=>'{bad'}}).gold,0);
const rooms=[{id:'full',name:'꽉찬 방',members:20},{id:'private',name:'비밀 방',locked:true,members:5},{id:'busy',name:'Forest',members:8},{id:'mine',name:'내 모험',members:1,mine:true}];
const before=JSON.stringify(rooms);assert.equal(recommendedRoom(rooms).id,'mine');assert.equal(recommendedRoom(rooms.slice(0,3)).id,'busy');assert.equal(recommendedRoom(rooms.slice(0,2)),null);assert.equal(JSON.stringify(rooms),before);
assert.equal(roomMatches(rooms[2],' forest '),true);assert.equal(roomMatches(rooms[3],'모험'),true);assert.equal(roomMatches(rooms[2],'마을'),false);assert.equal(roomMatches(rooms[0],'  '),true);
// Exercise the real home UI and its navigation/cleanup with a minimal DOM.
class Element extends EventTarget{constructor(tag){super();this.tagName=tag;this.children=[];this.attrs={};this.style={};}setAttribute(k,v){this.attrs[k]=v;}appendChild(c){this.children.push(c);return c;}append(...cs){cs.forEach(c=>this.appendChild(c));}scrollIntoView(){}}
const oldDoc=globalThis.document,oldNode=globalThis.Node;
globalThis.Node=Element;globalThis.document={createElement:t=>new Element(t),createTextNode:t=>Object.assign(new Element('#text'),{textContent:t})};
const find=(el,id)=>el.attrs['data-testid']===id?el:el.children.map(c=>find(c,id)).find(Boolean);
try{
 for(const profile of [null,{nickname:'모험가',avatar:{}}]){
  const root=new Element('root'),calls=[],app={profile,profileKey:'qa',go:(...args)=>calls.push(args)};
  const view=mount(root,app);find(root,'home-start').dispatchEvent(new Event('click'));
  assert.equal(calls[0][0],profile?'lobby':'profile');
  find(root,'home-studio').dispatchEvent(new Event('click'));assert.equal(calls[1][0],'profile');assert.equal(calls[1][1].mode,profile?'edit':'first');
  view.unmount();find(root,'home-start').dispatchEvent(new Event('click'));assert.equal(calls.length,2,'old title screen cannot navigate after being removed');
 }
}finally{globalThis.document=oldDoc;globalThis.Node=oldNode;}
console.log('PASS saved adventurer summary, safe storage fallback, room search/recommendation and first/returning home navigation cleanup');
