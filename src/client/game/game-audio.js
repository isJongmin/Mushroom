// Small optional synthesized cues; no audio download or autoplay on entry.
export function createGameAudio({storage,Audio=globalThis.AudioContext||globalThis.webkitAudioContext,clock=()=>performance.now()}={}){
 let enabled=false,context=null,disposed=false,lastAt=-Infinity;
 const voices=new Set();try{storage??=globalThis.localStorage;enabled=storage?.getItem('mushroom:sound')==='on';}catch{}
 function unlock(){if(!enabled||disposed||!Audio)return;try{context??=new Audio();context.resume()?.catch(()=>{});}catch{}}
 function play(kind){
  if(!enabled||!context||context.state!=='running'||disposed||clock()-lastAt<70||voices.size>=8)return false;
  lastAt=clock();const notes={swing:[180,100],skill:[320,480],loot:[660,880],rare:[523,659,784],level:[523,659,784,1047]};
  const list=notes[kind]||notes.loot;
  if(voices.size+list.length>8)return false;
  list.forEach((freq,i)=>{const o=context.createOscillator(),g=context.createGain(),at=context.currentTime+i*.065;
   o.type=kind==='swing'?'triangle':'sine';o.frequency.setValueAtTime(freq,at);if(kind==='swing')o.frequency.exponentialRampToValueAtTime(freq*.55,at+.09);
   g.gain.setValueAtTime(0,at);g.gain.linearRampToValueAtTime(.035,at+.008);g.gain.exponentialRampToValueAtTime(.0001,at+.18);
   o.connect(g);g.connect(context.destination);voices.add(o);o.onended=()=>{o.disconnect();g.disconnect();voices.delete(o);};o.start(at);o.stop(at+.2);
  });return true;
 }
 return {get enabled(){return enabled;},toggle(){enabled=!enabled;try{storage?.setItem('mushroom:sound',enabled?'on':'off');}catch{}if(enabled)unlock();else if(context)context.suspend()?.catch(()=>{});return enabled;},unlock,play,
  close(){disposed=true;for(const o of voices){try{o.stop();}catch{}}voices.clear();context?.close()?.catch(()=>{});context=null;}};
}
