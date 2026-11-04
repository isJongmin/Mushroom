// Bounded FIFO: typing never waits for RPC latency; only confirmed rate rejects retry automatically.
export function createChatOutbox({send, gapMs=1050, max=8, onPending=()=>{}, onState=()=>{}, onSent=()=>{}, onFailed=()=>{}, now=()=>performance.now(), schedule=setTimeout, cancel=clearTimeout}) {
  const entries=new Map(), queue=[];
  let seq=0, current=null, timer=null, readyAt=0, online=false, paused=false, closed=false;
  const snapshot=()=>({count:entries.size, queued:queue.length, sending:!!current, paused, full:entries.size>=max});
  const changed=()=>{if(!closed)onState(snapshot());};
  function arm(){
    if(closed||!online||paused||current||timer!==null||!queue.length)return;
    const delay=Math.max(0,readyAt-now());
    if(delay){timer=schedule(()=>{timer=null;arm();},delay);return;}
    current=queue.shift();const item=current;
    item.status='sending';onPending(item);changed();
    Promise.resolve().then(()=>{if(!closed)return send(item.text);}).then(msg=>{
      if(closed)return;
      if(!item.ack){item.ack=msg;onSent(item,msg);}
      finish(item);
    },err=>{
      if(closed)return;
      if(item.ack){finish(item);return;}
      current=null;readyAt=now()+gapMs;
      if(err?.code==='RATE_LIMITED'&&item.attempts++<2){item.status='queued';queue.unshift(item);onPending(item);changed();arm();return;}
      item.status='failed';item.uncertain=!['RATE_LIMITED','TEXT_FORMAT','NOT_MEMBER'].includes(err?.code);
      paused=true;onFailed(item,err);changed();
    });
  }
  function finish(item){entries.delete(item.id);current=null;readyAt=now()+gapMs;changed();arm();}
  return {
    snapshot,
    enqueue(text){
      if(closed||entries.size>=max)return null;
      const item={id:`pending-chat-${++seq}`,text,status:'queued',attempts:0,ack:null};
      entries.set(item.id,item);queue.push(item);onPending(item);changed();arm();return item;
    },
    // Realtime can beat the RPC response. Confirm only the active matching send.
    accept(msg){if(closed||!current||current.text!==msg.text||current.ack)return false;current.ack=msg;onSent(current,msg);return true;},
    setOnline(value){online=!!value;arm();changed();},
    retry(id){const item=entries.get(id);if(closed||item?.status!=='failed')return false;item.status='queued';item.attempts=0;paused=false;queue.unshift(item);onPending(item);changed();arm();return true;},
    discard(id){const item=entries.get(id);if(item?.status!=='failed')return false;entries.delete(id);paused=false;changed();arm();return true;},
    destroy(){closed=true;if(timer!==null)cancel(timer);timer=null;queue.length=0;entries.clear();},
  };
}
