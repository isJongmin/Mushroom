const bodyUrl=new URL('./avatar-body.js',import.meta.url);bodyUrl.search=new URL(import.meta.url).search;
const {isDefaultBody,bodyWidth,sourceBodyY,bodyY}=await import(bodyUrl.href);

// Source coordinates use pixel centres. Area coverage for shrinking prevents aliasing;
// Catmull-Rom reconstruction for enlargement preserves detail better than bilinear.
export function bodySampleWeights(center,scale,limit){
 const result=[];
 if(scale<1-1e-6){
  const radius=.5/scale,lo=center-radius,hi=center+radius;
  for(let i=Math.floor(lo+.5);i<=Math.floor(hi+.5);i++){
   const weight=Math.max(0,Math.min(hi,i+.5)-Math.max(lo,i-.5))*scale;
   if(weight>0&&i>=0&&i<limit)result.push([i,weight]);
  }
 }else{
  for(let i=Math.floor(center)-1;i<=Math.floor(center)+2;i++){
   const t=Math.abs(center-i),weight=t<1?(1.5*t-2.5)*t*t+1:t<2?((-.5*t+2.5)*t-4)*t+2:0;
   if(weight&&i>=0&&i<limit)result.push([i,weight]);
  }
 }
 return result;
}

// Bake once per body/outfit. Two separable passes keep filtering out of the game loop.
export function deformBodySheet(source,body,{frameW,frameH,anchorX,anchorY=180*frameH/192,makeCanvas}){
 if(isDefaultBody(body))return source;
 const frames=Math.floor(source.width/frameW),maxWidth=Math.max(...Object.entries(body).filter(([key])=>key!=='legLength').map(([,n])=>n))/100;
 const left=Math.floor(-anchorX*maxWidth)-2,right=Math.ceil((frameW-anchorX)*maxWidth)+2;
 const top=Math.floor(bodyY(body,0)*frameH/192)-2,bottom=frameH+2,outW=right-left,outH=bottom-top;
 const out=makeCanvas(outW*frames,outH),ctx=out.getContext('2d');
 Object.defineProperty(out,'avatarGeometry',{value:{w:outW,h:outH,ax:-left,ay:anchorY-top,top,left}});
 const src=source.getContext('2d').getImageData(0,0,source.width,source.height),dst=ctx.createImageData(out.width,out.height);
 const width=out.width,horizontal=new Float32Array(width*frameH*4),kernelCache=new Map();
 for(let y=0;y<frameH;y++){
  const scale=bodyWidth(body,(y+.5)*192/frameH);
  let kernels=kernelCache.get(scale);
  if(!kernels){kernels=Array.from({length:outW},(_,x)=>bodySampleWeights(anchorX+(x+left+.5)/scale-.5,scale,frameW).flat());kernelCache.set(scale,kernels);}
  for(let f=0;f<frames;f++){
   const sourceRow=(y*source.width+f*frameW)*4,targetRow=(y*width+f*outW)*4;
   for(let x=0;x<outW;x++){
    const weights=kernels[x];if(!weights.length)continue;
    let a=0,r=0,g=0,b=0;
    for(let n=0;n<weights.length;n+=2){const i=sourceRow+weights[n]*4,alpha=src.data[i+3]*weights[n+1];a+=alpha;r+=src.data[i]*alpha;g+=src.data[i+1]*alpha;b+=src.data[i+2]*alpha;}
    const i=targetRow+x*4,alpha=Math.max(0,Math.min(255,a));horizontal[i+3]=alpha;
    if(alpha>0){horizontal[i]=Math.max(0,Math.min(alpha*255,r));horizontal[i+1]=Math.max(0,Math.min(alpha*255,g));horizontal[i+2]=Math.max(0,Math.min(alpha*255,b));}
   }
  }
 }
 for(let y=0;y<outH;y++){
  const y0=sourceBodyY(body,(y+top)*192/frameH)*frameH/192,y1=sourceBodyY(body,(y+top+1)*192/frameH)*frameH/192;
  const center=sourceBodyY(body,(y+top+.5)*192/frameH)*frameH/192-.5;
  const weights=bodySampleWeights(center,1/Math.max(1e-6,y1-y0),frameH).flat();if(!weights.length)continue;
  for(let n=0;n<weights.length;n+=2)weights[n]*=width*4;
  const targetRow=y*width*4;
  for(let x=0;x<width*4;x+=4){
   let a=0,r=0,g=0,b=0;
   for(let n=0;n<weights.length;n+=2){const i=weights[n]+x,w=weights[n+1];a+=horizontal[i+3]*w;r+=horizontal[i]*w;g+=horizontal[i+1]*w;b+=horizontal[i+2]*w;}
   if(a>0){const i=targetRow+x;dst.data[i]=r/a;dst.data[i+1]=g/a;dst.data[i+2]=b/a;dst.data[i+3]=Math.min(255,a);}
  }
 }
 ctx.putImageData(dst,0,0);return out;
}
