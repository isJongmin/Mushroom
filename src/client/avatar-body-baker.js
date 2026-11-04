import {deformBodySheet} from './avatar-body-raster.js';

// One worker and one active transfer per renderer. Obsolete slider jobs are skipped.
export function createBodyBaker({workerFactory,makeCanvas}={}){
 let worker=null,failed=false,closed=false,seq=0,active=null;const queue=[];
 const supported=workerFactory||typeof Worker!=='undefined'&&typeof OffscreenCanvas!=='undefined';
 function fallback(item){try{item.resolve(item.valid()?deformBodySheet(item.source,item.body,{...item.options,makeCanvas}):null);}catch{item.resolve(null);}}
 function stopWorker(){worker?.terminate();worker=null;}
 function fail(){failed=true;stopWorker();const item=active;active=null;if(item)fallback(item);pump();}
 function pump(){
  if(closed||active)return;
  let item;while((item=queue.shift())&&!item.valid())item.resolve(null);if(!item)return;
  if(!supported||failed){fallback(item);pump();return;}
  try{
   if(!worker){
    const url=new URL('./avatar-body-worker.js',import.meta.url);url.search=new URL(import.meta.url).search;
    worker=workerFactory?workerFactory(url):new Worker(url,{type:'module'});
    worker.onerror=fail;
    worker.onmessage=({data})=>{
     if(closed||!active||data.id!==active.id)return;
     if(data.error){fail();return;}
     const current=active;active=null;
     if(!current.valid())current.resolve(null);
     else try{
      const cv=makeCanvas(data.width,data.height),ctx=cv.getContext('2d'),pixels=ctx.createImageData(data.width,data.height);pixels.data.set(new Uint8ClampedArray(data.buffer));ctx.putImageData(pixels,0,0);
      if(data.geometry)Object.defineProperty(cv,'avatarGeometry',{value:data.geometry});current.resolve(cv);
     }catch{current.resolve(null);}
     pump();
    };
   }
   const pixels=item.source.getContext('2d').getImageData(0,0,item.source.width,item.source.height);
   active=item;worker.postMessage({id:item.id,width:item.source.width,height:item.source.height,buffer:pixels.data.buffer,body:item.body,options:item.options},[pixels.data.buffer]);
  }catch{if(!active)active=item;fail();}
 }
 return {bake(source,body,options,valid=()=>true){if(closed)return Promise.resolve(null);return new Promise(resolve=>{queue.push({id:++seq,source,body,options,valid,resolve});pump();});},dispose(){closed=true;stopWorker();active?.resolve(null);active=null;for(const item of queue)item.resolve(null);queue.length=0;}};
}
