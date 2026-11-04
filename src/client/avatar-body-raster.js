import {isDefaultBody,bodyWidth,sourceBodyY} from './avatar-body.js';
// Bake each atlas once. Runtime draw remains one drawImage; identity is byte-identical.
export function deformBodySheet(source,body,{frameW,frameH,anchorX,makeCanvas}){
 if(isDefaultBody(body))return source;
 const out=makeCanvas(source.width,source.height),ctx=out.getContext('2d');
 const src=source.getContext('2d').getImageData(0,0,source.width,source.height),dst=ctx.createImageData(source.width,source.height);
 const frames=Math.floor(source.width/frameW),w=source.width;
 for(let y=0;y<frameH;y++){
  const sy=(sourceBodyY(body,(y+.5)*192/frameH)*frameH/192)-.5;
  if(sy<-.5||sy>frameH-.5)continue;
  const scale=bodyWidth(body,(sy+.5)*192/frameH),y0=Math.floor(sy),ty=sy-y0;
  for(let x=0;x<frameW;x++){
   const sx=anchorX+(x+.5-anchorX)/scale-.5,x0=Math.floor(sx),tx=sx-x0;
   for(let f=0;f<frames;f++){
    const at=(y*w+f*frameW+x)*4;let a=0,r=0,g=0,b=0;
    for(let j=0;j<2;j++)for(let i=0;i<2;i++){
     const px=x0+i,py=y0+j;if(px<0||px>=frameW||py<0||py>=frameH)continue;
     const q=(py*w+f*frameW+px)*4,weight=(i?tx:1-tx)*(j?ty:1-ty),alpha=src.data[q+3]*weight;
     a+=alpha;r+=src.data[q]*alpha;g+=src.data[q+1]*alpha;b+=src.data[q+2]*alpha;
    }
    if(a>0){dst.data[at]=r/a;dst.data[at+1]=g/a;dst.data[at+2]=b/a;dst.data[at+3]=a;}
   }
  }
 }
 ctx.putImageData(dst,0,0);return out;
}
