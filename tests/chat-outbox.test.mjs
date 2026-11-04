import assert from 'node:assert/strict';
import {createChatOutbox} from '../src/client/game/chat-outbox.js';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
function harness(options={}){
 let clock=0,seq=0;const timers=new Map(),requests=[],pending=[],sent=[],failed=[];
 const out=createChatOutbox({now:()=>clock,schedule:(fn,ms)=>{timers.set(++seq,{fn,at:clock+ms});return seq;},cancel:id=>timers.delete(id),
  send:text=>new Promise((resolve,reject)=>requests.push({text,resolve,reject})),onPending:item=>pending.push([item.id,item.status]),
  onSent:(item,msg)=>sent.push([item.id,msg]),onFailed:(item,err)=>failed.push([item.id,err]),...options});
 return {out,timers,requests,pending,sent,failed,async advance(ms){clock+=ms;for(const[id,t]of [...timers])if(t.at<=clock){timers.delete(id);t.fn();}await flush();}};
}

// Slow RPC never blocks accepting the next draft; order and server pacing hold.
{
 const h=harness();h.out.setOnline(true);
 const items=['첫째','둘째','셋째'].map(text=>h.out.enqueue(text));
 assert.equal(h.pending.length,4);assert.equal(h.out.snapshot().count,3);
 await flush();assert.deepEqual(h.requests.map(r=>r.text),['첫째']);
 await h.advance(800);h.requests[0].resolve({id:1,text:'첫째'});await flush();
 await h.advance(1049);assert.equal(h.requests.length,1);await h.advance(1);
 assert.equal(h.requests[1].text,'둘째');h.requests[1].resolve({id:2,text:'둘째'});await flush();await h.advance(1050);
 h.requests[2].resolve({id:3,text:'셋째'});await flush();
 assert.deepEqual(h.sent.map(x=>x[0]),items.map(x=>x.id));assert.equal(h.out.snapshot().count,0);
}
// Realtime may arrive first. Never duplicate it or retry an acknowledged send.
{
 const h=harness();h.out.setOnline(true);h.out.enqueue('같은 글');await flush();
 assert.equal(h.out.accept({id:11,text:'다른 글'}),false);
 assert.equal(h.out.accept({id:12,text:'같은 글'}),true);
 h.requests[0].reject({code:'NETWORK'});await flush();assert.equal(h.sent.length,1);assert.equal(h.failed.length,0);assert.equal(h.out.snapshot().count,0);
}
// Definite rate rejection retries, uncertain failures pause without losing drafts.
{
 const h=harness();h.out.setOnline(true);const first=h.out.enqueue('실패 보존');h.out.enqueue('다음 글');await flush();
 h.requests[0].reject({code:'RATE_LIMITED'});await flush();await h.advance(1050);
 assert.equal(h.requests[1].text,'실패 보존');h.requests[1].reject({code:'NETWORK'});await flush();
 await h.advance(5000);assert.equal(h.requests.length,2);assert.equal(h.out.snapshot().paused,true);assert.equal(h.out.snapshot().count,2);
 assert.equal(h.out.retry(first.id),true);await flush();assert.equal(h.requests[2].text,'실패 보존');
 h.requests[2].resolve({id:21,text:'실패 보존'});await flush();await h.advance(1050);assert.equal(h.requests[3].text,'다음 글');
 h.out.destroy();h.requests[3].resolve({id:22,text:'다음 글'});await flush();assert.equal(h.sent.length,1);assert.equal(h.timers.size,0);
}
// Queue is bounded, disconnected messages wait, and discard resumes the next one.
{
 const h=harness({max:2});const first=h.out.enqueue('1');h.out.enqueue('2');assert.equal(h.out.enqueue('3'),null);await flush();assert.equal(h.requests.length,0);
 h.out.setOnline(true);await flush();h.requests[0].reject({code:'TEXT_FORMAT'});await flush();assert.equal(h.out.discard(first.id),true);
 h.out.setOnline(false);await h.advance(2000);assert.equal(h.requests.length,1);h.out.setOnline(true);await flush();assert.equal(h.requests[1].text,'2');
 h.out.destroy();assert.equal(h.out.accept({text:'2'}),false);
}
// Repeated server rejections stop rather than looping indefinitely.
{
 const h=harness();h.out.setOnline(true);h.out.enqueue('제한');await flush();
 for(let i=0;i<3;i++){h.requests[i].reject({code:'RATE_LIMITED'});await flush();await h.advance(1050);}
 assert.equal(h.requests.length,3);assert.equal(h.failed.length,1);assert.equal(h.out.snapshot().paused,true);h.out.destroy();
}
{
 const h=harness();h.out.setOnline(true);h.out.enqueue('퇴장 직전');h.out.destroy();await flush();assert.equal(h.requests.length,0);
}
// Exercise the actual room key handler: IME confirmation and held Enter cannot send partial/duplicate text.
{
 const source=readFileSync(new URL('../src/client/screens/room.js',import.meta.url),'utf8');
 const start=source.indexOf('  const isTypingTarget ='),end=source.indexOf("  on(window, 'keyup'",start);
 const handlers=[];let sends=0,prevented=0;
 const input={tagName:'INPUT'},context=vm.createContext({window:{},document:{activeElement:input},chatInput:input,
  alive:true,composingChat:false,compositionEndedAt:-Infinity,performance:{now:()=>1000},
  on:(_el,_event,fn)=>handlers.push(fn),trySend:()=>sends++});
 vm.runInContext(source.slice(start,end),context);
 const enter=extra=>handlers[0]({key:'Enter',preventDefault:()=>prevented++,...extra});
 enter({isComposing:true});enter({keyCode:229});enter({repeat:true});
 context.composingChat=true;enter({});context.composingChat=false;
 context.compositionEndedAt=950;enter({});assert.equal(sends,0);
 context.compositionEndedAt=900;enter({});enter({});assert.equal(sends,2);assert.equal(prevented,2);
 const pointer=source.slice(source.indexOf("  on(sendBtn,'pointerdown'"),source.indexOf("  on(sendBtn, 'click'"));
 handlers.length=0;vm.runInContext(pointer,Object.assign(context,{sendBtn:{}}));
 for(const pointerType of ['mouse','touch','pen'])handlers[0]({pointerType,preventDefault:()=>prevented++});
 assert.equal(prevented,5,'all pointer types keep the composer focused before click');
}
console.log('PASS chat FIFO, slow sends, pacing, realtime confirmation, bounded retry, failure preservation, reconnect, cleanup and IME/Enter handling');
