import {petSellPrice} from '../src/client/game/progression.js';
import assert from 'node:assert/strict';
import {starterState,applyCommand,PET_SELL} from '../src/client/game/progression.js';
import {createPetReveal} from '../src/client/ui/pet-reveal.js';
import {createProgressionStore} from '../src/client/progression-store.js';
let s=starterState();s.items.push({id:'bow',kind:'bow',tier:2},{id:'staff',kind:'staff',tier:1},{id:'legend',kind:'claw',tier:4});
const original=structuredClone(s);
for(const ids of [[],['bow','bow'],['bow','missing'],['bow','starter-warrior']]){assert.throws(()=>applyCommand(s,{type:'sell-many',ids}));assert.deepEqual(s,original);}
const sold=applyCommand(s,{type:'sell-many',ids:['bow','staff','legend']});assert.equal(sold.result,950);assert.equal(sold.state.gold,950);assert.deepEqual(sold.state.items.map(i=>i.id),['starter-warrior']);assert.throws(()=>applyCommand(sold.state,{type:'sell-many',ids:['bow','staff']}));
for(let tier=0;tier<5;tier++){
 const state=starterState();const id='forest:'+tier;state.pets[id]={level:5};state.pet=id;state.essence=50;
 assert.throws(()=>applyCommand(state,{type:'pet-sell',id}),/동행/);
 const off=applyCommand(state,{type:'pet-off'}).state;const sale=applyCommand(off,{type:'pet-sell',id});
 assert.equal(sale.result,petSellPrice(id));assert.equal(sale.state.gold,petSellPrice(id));assert.equal(sale.state.essence,50);assert.equal(sale.state.pets[id],undefined);assert.equal(sale.state.pet,null);assert.throws(()=>applyCommand(sale.state,{type:'pet-sell',id}));
}
const results=[{id:'village:0',duplicate:false},{id:'village:4',duplicate:false},{id:'village:0',duplicate:true,essence:1}];
const r=createPetReveal(results);assert.equal(r.current,null);assert.equal(r.phase,'sealed');assert.equal(r.begin(),true);assert.equal(r.begin(),false);assert.equal(r.current,null);assert.equal(r.reveal(),true);assert.equal(r.reveal(),false);assert.equal(r.current,results[0]);assert.equal(r.shown.length,1);assert.equal(r.next(),true);assert.equal(r.next(),false);r.begin();r.reveal();assert.equal(r.current,results[1]);r.next();r.begin();r.reveal();assert.equal(r.phase,'complete');assert.equal(r.next(),false);r.summary();assert.equal(r.phase,'summary');assert.deepEqual(r.shown,results);
const skip=createPetReveal(results);skip.begin();skip.skip();assert.equal(skip.reveal(),false);assert.deepEqual(skip.shown,results);
const one=createPetReveal([results[0]]);one.begin();one.reveal();assert.equal(one.phase,'complete');
// Conflicting bulk sales and pet sales serialize against current state, not a stale selection.
const data=new Map();const st=starterState();st.items.push({id:'a',kind:'bow',tier:0},{id:'b',kind:'bow',tier:0},{id:'c',kind:'bow',tier:0});st.pets['village:2']={level:0};data.set('ux:equipment-v1',JSON.stringify(st));
const storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};let chain=Promise.resolve();const locks={request:(_,fn)=>{const p=chain.then(fn);chain=p.catch(()=>{});return p;}};
const a=createProgressionStore('ux',{storage,locks}),b=createProgressionStore('ux',{storage,locks});
const sales=await Promise.allSettled([a.run({type:'sell-many',ids:['a','b']}),b.run({type:'sell-many',ids:['b','c']})]);assert.equal(sales.filter(s=>s.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).gold,30);assert.equal(JSON.parse(data.get(a.key)).items.length,2);
const pets=await Promise.allSettled([a.run({type:'pet-sell',id:'village:2'}),b.run({type:'pet-sell',id:'village:2'})]);assert.equal(pets.filter(s=>s.status==='fulfilled').length,1);assert.equal(JSON.parse(data.get(a.key)).gold,210);
console.log('PASS atomic multi-sale, equipped protection, stale selection rollback, pet sale/refund rules, concurrent sales and single-card reveal/skip without rerolls');
