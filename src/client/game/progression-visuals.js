import {npcRoster} from './npc-roster.js';
import {petPose} from './appearance-motion.js';
import {petSpec,GRADE_COLORS} from './progression.js';
// Small shaded blocks match the existing voxel avatars, without external assets.
export function drawItem(c,kind,x,y,k=1,color='#a7d2eb',tier=Math.max(0,GRADE_COLORS.indexOf(color)),{held=false}={}) {
 c.save();c.translate(x,y);c.scale(k,k);c.lineJoin='miter';
 const r=(col,x,y,w,h)=>{c.fillStyle=col;c.fillRect(x,y,w,h);};
 if(!held)r('#18283788',-15,13,30,4);
 if(kind==='sword'){if(!held)c.rotate(.6);r('#39506c',-4,-23,8,32);r('#e8f8ff',-3,-23,3,30);r(color,0,-22,3,29);r('#e6ba66',-10,5,20,5);r('#70543f',-3,10,6,11);}
 if(kind==='bow'){r('#d3a56f',-9,-21,5,38);r('#916745',-4,-16,6,30);r('#d3a56f',2,-11,5,20);r('#f3e4bc',-11,-21,2,38);r(color,4,-6,4,9);}
 if(kind==='staff'){if(!held)c.rotate(.3);r('#8c6b85',-3,-13,6,36);r('#e4bd72',-6,-19,12,9);r(color,-8,-29,16,15);r('#effaff',-5,-26,5,7);}
 if(kind==='claw'){r('#6d678a',-13,-3,25,15);for(let n=0;n<3;n++){r(color,-10+n*8,-23,5,23);r('#eefaff',-10+n*8,-23,2,15);}r('#d8ac69',-14,8,28,5);}
 if(kind==='shield'){r('#48647e',-16,-23,32,31);r(color,-12,-20,24,29);r(color,-8,9,16,7);r('#ebf5ff',-10,-18,4,24);r('#d6b06e',-3,-20,6,31);r('#d6b06e',-12,-7,24,5);}
 // Grade silhouettes: forged guard → crystal wings → orbit crown.
 if(tier>=1){r('#e4c17b',-7,-8,14,3);r('#f4e5b2',-2,-12,4,8);}
 if(tier>=2){for(const d of [-1,1]){r(color,d<0?-17:10,-14,7,13);r('#ebf9ff',d<0?-16:11,-14,2,8);}}
 if(tier>=3){for(const d of [-1,1]){r(color,d<0?-23:17,-19,6,10);r(color,d<0?-19:13,-24,6,8);}r('#fff2c9',-3,-31,6,7);}
 if(tier===4){r('#f3d782',-11,-36,22,3);for(let n=0;n<3;n++)r('#ffeab1',-11+n*9,-41,4,6);r('#fff9dc',-20,-30,3,3);r('#fff9dc',18,-32,3,3);}
 c.restore();
}
export function drawPet(c,id,x,y,k=1,now=0,level=0,motion={}) {
 const p=petSpec(id);if(!p)return;const pose=petPose(id,now,motion);c.save();c.translate(x+pose.x*k,y+pose.y*k);c.rotate(pose.angle);c.scale((motion.left?-1:1)*k*pose.sx,k*pose.sy);
 const r=(col,x,y,w,h)=>{c.fillStyle=col;c.fillRect(x,y,w,h);};
 const color=p.area==='frost'?['#a9daee','#d7eff7','#8bc5ee','#b2c9f1','#d1edff'][p.tier]:p.area==='village'?['#d58f64','#82cd9c','#ba8c62','#93b9e7','#f0cb66'][p.tier]:p.area==='quarry'?['#a2a9b7','#a88bd6','#78c7e8','#b797e6','#f0d390'][p.tier]:['#8fbc72','#b5d69a','#b4e2b0','#a2c1a3','#d2e9a3'][p.tier];
 r('#132c3f33',-15,1,30,4);
 if(p.tier>=3){c.globalAlpha=.5+(motion.reduced?0:Math.sin(now/350)*.2);for(let i=0;i<6;i++){const a=(motion.reduced?0:now/1100)+i*Math.PI/3;r(GRADE_COLORS[p.tier],Math.cos(a)*23-1,-17+Math.sin(a)*23,3,3);}c.globalAlpha=1;}
 r('#324c55',-14,-28,28,26);r(color,-12,-27,24,24);r('#ffffff44',-10,-25,9,5);r('#29445055',8,-24,4,21);r(color,-10,-3,7,6);r(color,5,-3,7,6);
 if(p.area==='village'&&[0,4].includes(p.tier)){r('#986444',-19,-31,38,13);r(color,-16,-36,32,13);r('#f7ecc6',-10,-33,6,4);r('#f7ecc6',7,-29,5,4);}
 else if(p.area==='quarry'){for(let i=0;i<3;i++){r('#426579',-12+i*9,-33-i%2*5,7,10);r(color,-11+i*9,-34-i%2*5,4,9);}if(p.tier===1){r(color,-27,-22,14,10);r(color,13,-22,14,10);}}
 else {r(color,-12,-37,7,12);r(color,6,-39,7,14);if(p.area==='forest'){r('#507d55',-5,-34,4,9);r('#d2e9a3',-3,-38,10,6);}}
 // Species silhouettes: tails, ears, claws, wings and crowns stay readable at game scale.
 if(p.area==='village'){
   if(p.tier===1){r('#78b98d',-12,-35,6,11);r('#bce9a6',-6,-39,12,6);}
   if(p.tier===2){r('#916447',-23,-22,9,25);r('#d2ae77',-26,-25,7,23);r('#f1d7a1',-3,-23,5,15);r('#916447',-13,-34,7,10);r('#916447',6,-34,7,10);}
   if(p.tier===3){for(const d of [-1,1]){r('#d7c89b',d<0?-12:8,-43,4,20);r('#d7c89b',d<0?-19:10,-42,11,4);r('#d7c89b',d<0?-19:17,-48,3,10);}r('#e4f3f4',-8,-24,5,4);}
   if(p.tier===4){r('#9c722d',-12,-40,24,6);for(let n=0;n<3;n++)r('#ffeb9f',-12+n*10,-47,4,10);r('#d78462',-2,-40,5,5);}
 }else if(p.area==='quarry'){
   if(p.tier===0){r('#d6c1b3',-6,-12,13,8);r('#685c6d',-2,-10,5,3);r('#dbd6bf',-18,-4,7,5);r('#dbd6bf',12,-4,7,5);}
   if(p.tier===1){r('#765c9e',-29,-26,16,6);r('#765c9e',13,-26,16,6);r('#bca4df',-25,-20,11,6);r('#bca4df',14,-20,11,6);r('#765c9e',-21,-14,7,5);r('#765c9e',14,-14,7,5);}
   if(p.tier===2){r('#77b9cb',-22,-20,10,6);r('#77b9cb',13,-20,10,6);r('#b9e7e7',-24,-29,5,10);r('#b9e7e7',20,-29,5,10);for(let n=0;n<3;n++){r('#4d849b',-19,-6+n*4,7,2);r('#4d849b',13,-6+n*4,7,2);}}
   if(p.tier===3){r('#8976ba',-21,-25,8,23);r('#8976ba',14,-25,8,23);r('#d0bff3',-3,-25,7,7);}
   if(p.tier===4){r('#bca36d',-30,-27,17,7);r('#bca36d',13,-27,17,7);r('#f3df9c',-26,-22,13,7);r('#f3df9c',13,-22,13,7);r('#bca36d',14,-4,15,5);r('#f3df9c',25,-9,6,9);}
 }else{
   if(p.tier===1){r('#e6edd5',-10,-45,4,14);r('#e6edd5',7,-47,4,16);}
   if(p.tier===2){r('#e8f8ba',-25,-24,12,15);r('#e8f8ba',14,-24,12,15);r('#f7ffe0',-19,-21,5,7);r('#f7ffe0',16,-21,5,7);}
   if(p.tier===3){r('#9d9272',-15,-42,4,16);r('#9d9272',11,-42,4,16);r('#9d9272',-21,-42,9,4);r('#9d9272',13,-42,9,4);}
   if(p.tier===4){r('#659363',-22,-38,44,13);r('#b2d190',-17,-46,34,13);r('#dceab0',-9,-51,18,7);r('#f6f5ce',-2,-43,5,5);}
 }
 if(pose.fly&&!motion.reduced){const flap=Math.sin(now/90+pose.seed)*5;r(color,-28,-21+flap,14,4);r(color,14,-21+flap,14,4);}
 if(motion.reaction==='loot'){r('#f4d37c',18,-40,3,9);r('#f4d37c',15,-37,9,3);}
 if(motion.reaction==='hurt'){r('#c894a5',18,-34,4,7);r('#c894a5',18,-24,4,3);}
 r('#233744',-7,-18,4,5);r('#233744',5,-18,4,5);r('#fff',-6,-18,2,2);r('#fff',6,-18,2,2);r('#e5a5a5',-10,-10,4,2);r('#e5a5a5',8,-10,4,2);r('#52635a',-1,-10,4,2);
 if(level){r('#f9df89',-2,-30,4,4);}c.restore();
}
export function drawEquipmentDrop(c,d,camX,camY,k,now,age=Infinity) {
 const hop=Number.isFinite(age)?Math.sin(Math.min(1,Math.max(0,age/650))*Math.PI)*28:0;
 if(d.kind==='gold'){const x=(d.x-camX)*k,y=(d.y-camY-12-hop+Math.sin(now/240+d.x)*3)*k;c.save();c.fillStyle='#80502b';c.fillRect(x-9*k,y-8*k,18*k,13*k);c.fillStyle='#e9ba54';c.fillRect(x-8*k,y-10*k,16*k,12*k);c.fillStyle='#fff0a2';c.fillRect(x-5*k,y-8*k,4*k,7*k);c.fillStyle='#b8833e';c.fillRect(x+3*k,y-7*k,2*k,6*k);c.restore();return;}
 const x=(d.x-camX)*k,y=(d.y-camY-15-hop+Math.sin(now/300+d.x)*3)*k,color=GRADE_COLORS[d.tier];
 c.save();c.fillStyle=color+'28';c.fillRect(x-20*k,y-30*k,40*k,49*k);c.fillStyle=color;c.fillRect(x-18*k,y+17*k,36*k,2*k);drawItem(c,d.kind,x,y,.65*k,color);c.restore();
}
export const petNpcPoint = world => ({x:Math.min(world.maxX-90,(world.spawn?.x??300)+125),y:world.groundY});
export function drawPetMerchant(c,p,camX,camY,k,renderer,avatar,area,now) {
 const x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-150*k||x>c.canvas.width+150*k)return;
 c.save();c.fillStyle='#39505b44';c.fillRect(x-38*k,y-2*k,76*k,6*k);
 renderer?.draw(c,avatar,x,y,k,renderer.frameAt('idle_front',now),true);
 c.fillStyle=area==='quarry'?'#766491':area==='forest'?'#60866d':'#ad795a';c.fillRect(x+25*k,y-31*k,53*k,32*k);c.fillStyle='#ead5a3';c.fillRect(x+22*k,y-35*k,59*k,6*k);
 drawPet(c,area+':0',x+50*k,y-33*k,k*.65,now);
 c.font=`600 ${10*k}px system-ui`;c.textAlign='center';c.fillStyle='#203e39';c.fillRect(x-57*k,y+7*k,114*k,18*k);c.fillStyle='#f7ebc7';c.fillText(npcRoster(area).pet.name,x,y+20*k);c.restore();
}
