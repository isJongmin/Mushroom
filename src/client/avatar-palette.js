// Appearance colors only. Proportions and the seven-part avatar contract stay fixed.
export const cleanSkinColor=value=>typeof value==='string'&&/^#[0-9a-f]{6}$/i.test(value)?value.toLowerCase():null;
const SKIN=Symbol('skin-color');
export const withSkinColor=(avatar,color)=>({...avatar,[SKIN]:cleanSkinColor(color)});
export const avatarSkinColor=avatar=>avatar?.[SKIN]||null;
export const SKIN_SWATCHES=Object.freeze([
 ['light','밝은 피부','#fad6c0'],['medium','보통 피부','#e2a982'],['dark','진한 피부','#a3684a'],
 ['porcelain','포슬린','#f3dfd1'],['rose-beige','로즈 베이지','#e5b8a4'],['golden','골든 베이지','#d8aa78'],['olive','올리브','#b49a76'],['bronze','브론즈','#a87953'],['cocoa','코코아','#79513c'],['ebony','에보니','#4d352b'],
].map(([id,label,color])=>Object.freeze({id,label,color})));
const rgb=hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);
function hsl(r,g,b){const hi=Math.max(r,g,b),lo=Math.min(r,g,b),d=hi-lo,l=(hi+lo)/2;let h=0;if(d){h=hi===r?(g-b)/d+(g<b?6:0):hi===g?(b-r)/d+2:(r-g)/d+4;h/=6;}return [h,d?d/(1-Math.abs(2*l-1)):0,l];}
const clamp=v=>Math.max(0,Math.min(1,v));
function channels(h,s,l){h=(h%1+1)%1;const c=(1-Math.abs(2*l-1))*s,x=c*(1-Math.abs((h*6)%2-1)),m=l-c/2;const k=Math.floor(h*6);return [[c,x,0],[x,c,0],[0,c,x],[0,x,c],[x,0,c],[c,0,x]][k].map(v=>(v+m)*255);}
const hueDistance=(a,b)=>Math.min(Math.abs(a-b),1-Math.abs(a-b));
export function recolorAvatarSheet(image,{color,reference='#fad6c0',mode='material'},makeCanvas){
 const w=image.naturalWidth||image.width,h=image.naturalHeight||image.height,cv=makeCanvas(w,h),ctx=cv.getContext('2d');ctx.drawImage(image,0,0);
 const pixels=ctx.getImageData(0,0,w,h),d=pixels.data,target=hsl(...rgb(color)),base=hsl(...rgb(reference));
 for(let i=0;i<d.length;i+=4){if(!d[i+3])continue;const [hue,sat,light]=hsl(d[i]/255,d[i+1]/255,d[i+2]/255);
  let use=mode==='skin'||(mode==='eyes'?hue<.15&&sat>.18&&light>.1&&light<.58:mode==='hair'?(light<.3||hueDistance(hue,base[0])<.12&&sat>.08&&light<.91):base[2]<.25?light<.45:hueDistance(hue,base[0])<.2&&sat>.1&&light<.94&&(base[2]<.6||light>.38));
  if(!use)continue;
  const L=mode==='skin'?clamp(target[2]*light/Math.max(.1,base[2])+Math.max(0,light-base[2])*.2):clamp(target[2]+(light-base[2])*.85);
  const out=channels(target[0],clamp(target[1]*(.82+.18*sat/Math.max(.1,base[1]))),L);d[i]=out[0];d[i+1]=out[1];d[i+2]=out[2];
 }
 ctx.putImageData(pixels,0,0);Object.defineProperties(cv,{naturalWidth:{value:w},naturalHeight:{value:h}});return cv;
}
