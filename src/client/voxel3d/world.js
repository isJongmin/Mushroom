import {box,localBox} from './engine.js';
export const AREAS={village:{title:'버섯마을',subtitle:'햇살이 머무는 첫 번째 마을',grass:'#79a45a',earth:'#846547',leaf:'#456f49',sky:'#b6d7cf',mob:'#cc7758'},quarry:{title:'광산마을',subtitle:'수정의 빛을 따라',grass:'#81918c',earth:'#667077',leaf:'#597178',sky:'#a8bdc9',mob:'#8293ae'},forest:{title:'이끼마을',subtitle:'깊은 숲의 오래된 숨결',grass:'#537e64',earth:'#52644e',leaf:'#335d50',sky:'#a2bfb2',mob:'#83a875'}};
export function ground(x,z){const d=Math.max(Math.abs(x),Math.abs(z));return d<17?0:d<22?1:2+Math.floor((Math.sin(x*.25)+Math.cos(z*.27)+2)*.7);}
export function makeWorld(area='village'){
 const theme=AREAS[area],blocks=[],obstacles=[];
 // Greedy terrain meshing combines adjacent solid blocks into rectangular surfaces.
 // Collision still samples the original unit grid; only the drawn geometry is merged.
 const cells=new Map(),used=new Set();
 for(let x=-28;x<=28;x++)for(let z=-28;z<=28;z++){
  const y=ground(x,z),path=(Math.abs(x)<1.7||Math.abs(z-3)<1.7||Math.abs(x-8)<1.2&&z<-4)&&Math.abs(x)<17&&Math.abs(z)<17;
  cells.set(x+','+z,{y,color:path?'#c4b58b':theme.grass});
 }
 for(let z=-28;z<=28;z++)for(let x=-28;x<=28;x++){
  const key=x+','+z;if(used.has(key))continue;const tile=cells.get(key),same=(xx,zz)=>{const k=xx+','+zz,t=cells.get(k);return t&&!used.has(k)&&t.y===tile.y&&t.color===tile.color;};let width=1,height=1;
  while(x+width<=28&&same(x+width,z))width++;
  outer:while(z+height<=28){for(let dx=0;dx<width;dx++)if(!same(x+dx,z+height))break outer;height++;}
  for(let dz=0;dz<height;dz++)for(let dx=0;dx<width;dx++)used.add((x+dx)+','+(z+dz));
  box(blocks,x+(width-1)/2,tile.y-1.15,z+(height-1)/2,width,2.3,height,tile.color);
 }

 function tree(x,z,scale=1){const y=ground(x,z);box(blocks,x,y+1.5*scale,z,.7*scale,3*scale,.7*scale,'#79604b');for(let j=0;j<3;j++)box(blocks,x,y+(3.3+j*.65)*scale,z,(3.5-j*.75)*scale,1*scale,(3.5-j*.75)*scale,j===2?'#76985c':theme.leaf);obstacles.push({x,z,w:.75,d:.75});}
 for(let n=0;n<48;n++){const a=n*2.399,r=19+(n%6)*1.5;tree(Math.cos(a)*r,Math.sin(a)*r,.8+n%3*.18);}
 for(const [x,z]of [[-10,7],[12,8],[-13,-8],[13,-9]]){tree(x,z,1.15);}
 function cottage(x,z,roof){const y=ground(x,z);box(blocks,x,y+1.7,z,4.3,3.4,3.8,'#ddd0a4');box(blocks,x,y+.3,z,4.6,.6,4.1,'#8e8270');for(let i=0;i<4;i++)box(blocks,x,y+3.6+i*.43,z,5.5-i*.9,.5,4.7,roof);for(const dx of [-1.9,1.9])box(blocks,x+dx,y+1.8,z+1.94,.22,3.2,.16,'#79654e');box(blocks,x,y+1,z+1.96,.9,2,.12,'#735743');for(const dx of [-1.3,1.3]){box(blocks,x+dx,y+1.9,z+1.98,.8,.9,.12,'#7baba1');box(blocks,x+dx,y+1.9,z+2.06,.08,.95,.06,'#e7dcb5');}box(blocks,x+1.4,y+4.6,z-1,.6,1.7,.65,'#8e8070');obstacles.push({x,z,w:4.5,d:4});}
 cottage(-7,0,'#a7644f');cottage(7,7,'#597e73');cottage(-9,-10,'#92724f');
 // Landmark mushrooms and flower patches, made from the same unit cubes.
 for(let n=0;n<38;n++){const x=Math.sin(n*12.3)*15,z=Math.cos(n*4.8)*15;if(Math.abs(x)<2||Math.abs(z-3)<2)continue;const y=ground(x,z);if(n%3===0){box(blocks,x,y+.45,z,.35,.9,.35,'#e6d7b1');box(blocks,x,y+.95,z,1.3,.35,1.15,'#ba7357');box(blocks,x-.3,y+1.15,z,.23,.1,.23,'#f1dfb9');}else{box(blocks,x,y+.2,z,.1,.4,.1,'#527955');box(blocks,x,y+.45,z,.3,.22,.3,n%2?'#e5b06d':'#dcc6a0');}}
 for(const [x,z]of [[-2,6],[2,-5],[4,3],[-13,3]]){box(blocks,x,1.5,z,.18,3,.18,'#675e4d');box(blocks,x,3,z,.7,.7,.7,'#efd797');box(blocks,x,3.45,z,.9,.14,.9,'#5e6957');}
 // A well, market canopy and crates give the village a recognisable centre.
 for(const [x,z]of [[3,-1],[4,-1],[5,-1],[3,-3],[4,-3],[5,-3],[3,-2],[5,-2]])box(blocks,x,.4,z,1,.8,1,'#9ba49a');box(blocks,4,.1,-2,1,.1,1,'#669f9e');
 for(const dx of [-1.6,1.6])box(blocks,5+dx,1.4,-7,.15,2.8,.15,'#8d7455');box(blocks,5,2.8,-7,4,.2,2.3,'#e5c388');box(blocks,5,.65,-7,3.7,1.3,1,'#8b7655');obstacles.push({x:5,z:-7,w:3.7,d:1.2});
 for(let n=0;n<4;n++)box(blocks,-11+n*.8,.45,1,.75,.9,.75,n%2?'#9d825a':'#b29b6b');
 return {blocks,obstacles,theme};
}
export function blocked(x,z,obstacles,r=.32){return Math.abs(x)>27||Math.abs(z)>27||obstacles.some(o=>Math.abs(x-o.x)<o.w/2+r&&Math.abs(z-o.z)<o.d/2+r);}
export function character(list,p,{weapon='sword',tier=0,attack=0,moving=false,time=0,npc=false}={}){
 const root={...p},swing=moving?Math.sin(time*11)*.22:0,col=npc?'#d2a56b':'#567c73',skin='#e1bc99';
 const b=(x,y,z,sx,sy,sz,c,a=0)=>localBox(list,root,x,y,z,sx,sy,sz,c,a);
 b(0,.85,0,.62,.65,.38,col);b(0,1.45,0,.62,.62,.57,skin);b(0,1.77,-.03,.68,.2,.63,npc?'#b78755':'#584a40');b(0,1.55,-.27,.65,.36,.16,'#584a40');for(const d of [-1,1]){b(d*.17,.38,swing*d,.23,.65,.26,'#47586b');b(d*.17,.08,.06+swing*d,.28,.17,.39,'#d0c8af');b(d*.14,1.47,.292,.07,.09,.035,'#303e3d');b(d*.42,.92,0,.2,.55,.24,col);b(d*.42,.62,.03,.2,.2,.24,skin);}
 b(0,1.28,.3,.11,.08,.05,'#ba8b70');b(0,1.05,.21,.12,.1,.04,'#ccb787');
 if(npc){b(0,1.92,0,.88,.14,.75,'#bea071');b(0,2.05,0,.55,.25,.54,'#c6af83');return;}
 const grade=['#bacad0','#78bb91','#81b9d8','#bb9bd7','#e9c775'][tier],hand={x:p.x+Math.cos(p.yaw)*.44,y:p.y+.66,z:p.z-Math.sin(p.yaw)*.44,yaw:p.yaw+(attack?-.85+attack*2.4:.1)};
 const w=(x,y,z,sx,sy,sz,c)=>localBox(list,hand,x,y,z,sx,sy,sz,c);
 if(weapon==='sword'){w(0,.1,.17,.13,.13,.37,'#8b6b48');w(0,.13,.38,.48,.15,.12,'#ddbe74');w(0,.13,.94,.16,.12,1.04,grade);w(-.055,.14,.94,.035,.14,1.04,'#e7ece0');}
 if(weapon==='bow'){for(let n=-2;n<=2;n++)w(n*.07,n*.2,.3-Math.abs(n)*.08,.13,.23,.13,grade);w(-.2,0,.16,.045,.93,.045,'#ede2bb');}
 if(weapon==='staff'){w(0,.3,.15,.13,1.6,.13,'#8d725d');w(0,1.2,.15,.4,.4,.4,grade);w(0,1.48,.15,.18,.18,.18,'#e9e4c7');}
 if(weapon==='claw'){w(0,0,.1,.28,.23,.32,'#8d7595');for(let i=-1;i<=1;i++)w(i*.12,.02,.39,.07,.1,.38,grade);}
 if(tier>=2)w(0,.28,.4,.19,.19,.19,grade);
}
export function mushroom(list,m,time=0){const k=m.boss?2.4:1,hop=m.moving?Math.abs(Math.sin(time*6+m.seed))*.12:Math.sin(time*2+m.seed)*.025,y=m.y+hop;const r={x:m.x,y,z:m.z,yaw:m.yaw||0};const b=(x,yy,z,sx,sy,sz,c)=>localBox(list,r,x*k,yy*k,z*k,sx*k,sy*k,sz*k,c);
 b(0,.42,0,.7,.8,.65,m.hit>0?'#f2d6b3':'#dfd0a5');b(0,.96,0,1.45,.36,1.25,m.hit>0?'#edc299':m.color);b(0,1.23,-.04,1.05,.25,.9,m.color);for(const [x,z]of [[-.4,.3],[.32,.35],[.1,-.3]])b(x,1.16,z,.23,.12,.23,'#f0e0b6');for(const d of [-1,1]){b(d*.16,.55,.335,.09,.12,.04,'#3a4438');b(d*.28,.12,.06,.3,.22,.4,'#a1835f');}if(m.boss){b(0,1.47,0,.75,.16,.7,'#dfbc65');for(const d of [-1,0,1])b(d*.29,1.65,0,.15,.3,.2,'#efd493');}}
