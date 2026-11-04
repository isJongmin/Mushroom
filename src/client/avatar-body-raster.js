import {isDefaultBody,bodyWidth,sourceBodyY,bodyY} from './avatar-body.js';
// Bake each atlas once. Runtime draw remains one drawImage; identity is byte-identical.
export function deformBodySheet(source,body,{frameW,frameH,anchorX,anchorY=180*frameH/192,makeCanvas}){
 if(isDefaultBody(body))return source;
 const frames=Math.floor(source.width/frameW),maxWidth=Math.max(...Object.entries(body).filter(([key])=>key!=='legLength').map(([,n])=>n))/100;
 const left=Math.floor(-anchorX*maxWidth)-2,right=Math.ceil((frameW-anchorX)*maxWidth)+2;
 const top=Math.floor(bodyY(body,0)*frameH/192)-2,bottom=frameH+2;
 const outW=right-left,outH=bottom-top;
 const out=makeCanvas(outW*frames,outH),ctx=out.getContext('2d');
 Object.defineProperty(out,'avatarGeometry',{value:{w:outW,h:outH,ax:-left,ay:anchorY-top,top,left}});
 const src=source.getContext('2d').getImageData(0,0,source.width,source.height),dst=ctx.createImageData(out.width,out.height);
 const w=source.width;
 for(let y=0;y<outH;y++){
  const sy=(sourceBodyY(body,(y+top+.5)*192/frameH)*frameH/192)-.5;
  if(sy<-.5||sy>frameH-.5)continue;
  const scale=bodyWidth(body,(sy+.5)*192/frameH),y0=Math.floor(sy),ty=sy-y0;
  for(let x=0;x<outW;x++){
   const sx=anchorX+(x+left+.5)/scale-.5,x0=Math.floor(sx),tx=sx-x0;
   for(let f=0;f<frames;f++){
    const at=(y*out.width+f*outW+x)*4;let a=0,r=0,g=0,b=0;
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
