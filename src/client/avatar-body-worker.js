// Import maps do not apply inside workers; carry the release query through this graph.
const rasterUrl=new URL('./avatar-body-raster.js',import.meta.url);rasterUrl.search=new URL(import.meta.url).search;
const raster=import(rasterUrl.href);
self.onmessage=async({data})=>{
 try{
  const {deformBodySheet}=await raster,{id,buffer,width,height,body,options}=data;
  const source=new OffscreenCanvas(width,height);source.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(buffer),width,height),0,0);
  const out=deformBodySheet(source,body,{...options,makeCanvas:(w,h)=>new OffscreenCanvas(w,h)});
  const pixels=out.getContext('2d').getImageData(0,0,out.width,out.height);
  self.postMessage({id,width:out.width,height:out.height,geometry:out.avatarGeometry,buffer:pixels.data.buffer},[pixels.data.buffer]);
 }catch(error){self.postMessage({id:data.id,error:String(error?.message||error)});}
};
