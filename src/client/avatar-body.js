// Version 1 appearance-only proportions. Physics never reads these values.
// The existing atlas has merged limbs: horizontal bands also affect sleeves/hands.
export const BODY_FIELDS=Object.freeze([
 {key:'head',label:'머리 크기',min:10,max:200,low:'작게',high:'크게',group:'전체 비율'},
 {key:'legLength',label:'다리 길이',min:10,max:200,low:'짧게',high:'길게',group:'전체 비율'},
 {key:'shoulders',label:'어깨·팔 너비',min:10,max:200,low:'좁게',high:'넓게',group:'상체'},
 {key:'chest',label:'가슴 너비',min:10,max:200,low:'가늘게',high:'두껍게',group:'상체'},
 {key:'waist',label:'허리 너비',min:10,max:200,low:'가늘게',high:'두껍게',group:'상체'},
 {key:'hips',label:'골반 너비',min:10,max:200,low:'좁게',high:'넓게',group:'하체'},
 {key:'thighs',label:'허벅지 너비',min:10,max:200,low:'가늘게',high:'두껍게',group:'하체'},
 {key:'calves',label:'종아리 너비',min:10,max:200,low:'가늘게',high:'두껍게',group:'하체'},
 {key:'feet',label:'발 너비',min:10,max:200,low:'작게',high:'크게',group:'하체'},
].map(Object.freeze));
export const DEFAULT_BODY=Object.freeze(Object.fromEntries(BODY_FIELDS.map(f=>[f.key,100])));
export function normalizeBody(raw){
 const src=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{};
 return Object.fromEntries(BODY_FIELDS.map(f=>[f.key,typeof src[f.key]==='number'&&Number.isFinite(src[f.key])?Math.round(Math.max(f.min,Math.min(f.max,src[f.key]))):100]));
}
export const bodyKey=raw=>{const body=normalizeBody(raw);return BODY_FIELDS.map(f=>body[f.key]).join('.');};
export const BODY_PRESETS=Object.freeze([
 {id:'balanced',name:'균형',caption:'익숙하고 편안한 비율',values:{}},
 {id:'storybook',name:'동화',caption:'큰 머리와 짧은 다리',values:{head:150,legLength:65,shoulders:80,chest:85,feet:125}},
 {id:'ranger',name:'날렵',caption:'긴 다리와 가벼운 실루엣',values:{head:80,legLength:155,shoulders:75,chest:75,waist:65,hips:80,thighs:70,calves:65,feet:90}},
 {id:'guardian',name:'든든',caption:'넓은 상체와 단단한 하체',values:{head:90,shoulders:155,chest:165,waist:115,hips:125,thighs:145,calves:130,feet:120}},
].map(p=>Object.freeze({...p,values:Object.freeze(normalizeBody(p.values))})));
// Symbol metadata survives costume spreads but stays out of the 7-part JSON contract.
const BODY=Symbol('avatar-body');
export function withBody(avatar,raw){const body=Object.freeze(normalizeBody(raw));return {...avatar,[BODY]:Object.freeze({body,key:BODY_FIELDS.map(f=>body[f.key]).join('.')})};}
export const avatarBody=avatar=>avatar?.[BODY]?.body||DEFAULT_BODY;
const DEFAULT_KEY=BODY_FIELDS.map(()=>100).join('.');
export const avatarBodyKey=avatar=>avatar?.[BODY]?.key||DEFAULT_KEY;
export const isDefaultBody=raw=>BODY_FIELDS.every(f=>raw[f.key]===100);

const smooth=t=>t*t*(3-2*t);
// Atlas-space coordinates normalized to the shipped 144 x 192 atlas.
export function bodyWidth(body,y){
 const stops=[[98,'head'],[108,'shoulders'],[122,'chest'],[135,'waist'],[146,'hips'],[157,'thighs'],[169,'calves'],[180,'feet']];
 if(y<=stops[0][0])return body.head/100;
 for(let i=1;i<stops.length;i++){const [at,key]=stops[i], [prev,old]=stops[i-1];if(y<=at){const t=smooth((y-prev)/(at-prev));return (body[old]+(body[key]-body[old])*t)/100;}}
 return body.feet/100;
}
function linearBodyY(body,y){
 const leg=body.legLength/100,head=body.head/100;
 if(y>=176)return y;
 if(y>=142)return 176+(y-176)*leg;
 const hip=176-34*leg;
 if(y>=110)return hip+(y-142);
 return hip-32+(y-110)*head;
}
// Continuous first derivative at neck/hip; do not stretch the lower face into a taper.
const transition=(start,span,t,a,b)=>start+span*(a*t+(b-a)*t*t/2);
const untransition=(value,start,span,a,b)=>{const d=(value-start)/span;return 2*d/(a+Math.sqrt(Math.max(0,a*a+2*(b-a)*d)));};
export function bodyY(body,y){
 if(y>=104&&y<=116)return transition(linearBodyY(body,104),12,(y-104)/12,body.head/100,1);
 if(y>=136&&y<=148)return transition(linearBodyY(body,136),12,(y-136)/12,1,body.legLength/100);
 return linearBodyY(body,y);
}
export function sourceBodyY(body,y){
 const leg=body.legLength/100,head=body.head/100,hip=176-34*leg,neck=hip-32;
 for(const [start,a,b]of [[104,head,1],[136,1,leg]]){const low=linearBodyY(body,start),high=linearBodyY(body,start+12);if(y>=low&&y<=high)return start+12*untransition(y,low,12,a,b);}
 if(y>=176)return y;
 if(y>=hip)return 176+(y-176)/leg;
 if(y>=neck)return 142+(y-hip);
 return 110+(y-neck)/head;
}
export function bodyPoint(body,point,{frameH=192,anchorX=72,anchorY=180,density=1.5}={}){
 const sy=anchorY+point.y*density,y192=sy*192/frameH;
 return {x:point.x*bodyWidth(body,y192),y:(bodyY(body,y192)*frameH/192-anchorY)/density};
}
