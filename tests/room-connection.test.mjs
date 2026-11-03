import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Execute the real callback with its dependencies, so an unresolved name cannot
// silently strand initial entry before setConnection('connected').
const source=readFileSync(new URL('../src/client/screens/room.js',import.meta.url),'utf8');
const callback=source.slice(source.indexOf('  function onLinkState('),source.indexOf('  async function loadHistory('));
const calls=[];
const context=vm.createContext({alive:true,connection:'joining',connectedAt:0,
  performance:{now:()=>1234},canvas:{focus:()=>calls.push('focus')},
  setConnection:state=>{context.connection=state;calls.push(state);},
  loadHistory:merge=>calls.push(['history',merge]),
  reconnected:()=>calls.push('reconnected')});
vm.runInContext(callback,context);
context.onLinkState('connected',{first:true});
assert.equal(context.connection,'connected');
assert.equal(context.connectedAt,1234);
assert.deepEqual(calls,['connected','focus']);
calls.length=0;
context.onLinkState('connected',{first:false,after:'rejoining'});
assert.deepEqual(calls,[['history',true]]);
calls.length=0;context.connection='disconnected';
context.onLinkState('connected',{first:false});
assert.deepEqual(calls,['reconnected']);
calls.length=0;context.alive=false;
context.onLinkState('connected',{first:true});
assert.deepEqual(calls,[]);
console.log('PASS initial connected callback, quiet rejoin, reconnect and disposed screen');
