export const COSTUMES=Object.freeze([
 {id:'sprout-cape',name:'새싹 정찰대',need:'버섯밭 방어 1회 성공',unlocked:r=>r.clears>=1,color:'#7aaa61',trim:'#d6e9a4'},
 {id:'bloom-cape',name:'꽃잎 기사단',need:'버섯밭 방어 3회 성공',unlocked:r=>r.clears>=3,color:'#b56d91',trim:'#f4cfcd'},
 {id:'royal-guardian',name:'버섯 왕관과 망토',need:'버섯왕 처치 1회 성공 · 기존 모자 대신 착용',unlocked:r=>r.bossClears>=1,color:'#476d86',trim:'#e8bf63'}
]);
export const cleanCostume=id=>COSTUMES.some(c=>c.id===id)?id:null;
export const costumeAvatar=(avatar,id)=>id==='royal-guardian'?{...avatar,hat:'none'}:avatar;
function mushroom(c,x,y,s){
 c.fillStyle='#d9b769';c.fillRect(x-1.5*s,y-5*s,3*s,5*s);
 c.fillStyle='#945536';c.fillRect(x-5*s,y-8*s,10*s,3*s);c.fillStyle='#cc8654';c.fillRect(x-4*s,y-11*s,8*s,3*s);c.fillStyle='#f3c57d';c.fillRect(x-2*s,y-12*s,4*s,2*s);
 c.fillStyle='#ffedbe';c.fillRect(x-2*s,y-9*s,2*s,2*s);c.fillRect(x+2*s,y-7*s,2*s,1*s);
}
export function drawCostume(c,id,x,y,k,{back=false,rear=false,prone=false,left=false,side=false,fit={},time=0,moving=false}={}){
 const s=COSTUMES.find(s=>s.id===id);if(!s||prone)return;
 const {headTop=86,headX=0,neck=46,shoulder=13,bodyX=0,hem=18}=fit;
 c.save();c.translate(x,y);c.scale(left?-k:k,k);
 const sway=moving?Math.sin(time/140)*2:0,half=side?shoulder*.65:shoulder;
 const capeX=bodyX+(side&&!rear?-shoulder*.65:0);
 // Cape is a back garment. The front pass adds no collar, bib or shoulder pads.
 if(back||rear){
   c.fillStyle=s.color;c.beginPath();c.moveTo(capeX-half,-neck);c.lineTo(capeX+half,-neck);c.lineTo(capeX+half+3+sway,-hem);c.lineTo(capeX+sway,-hem+3);c.lineTo(capeX-half-3+sway,-hem);c.closePath();c.fill();
   c.fillStyle='#172f3424';c.beginPath();c.moveTo(capeX+half-3,-neck);c.lineTo(capeX+half+3+sway,-hem);c.lineTo(capeX+half-2+sway,-hem);c.lineTo(capeX+half-7,-neck);c.closePath();c.fill();
   c.strokeStyle=s.trim;c.lineWidth=1;c.beginPath();c.moveTo(capeX-half-2+sway,-hem-1);c.lineTo(capeX+sway,-hem+2);c.lineTo(capeX+half+2+sway,-hem-1);c.stroke();
   if(rear){c.strokeStyle=s.trim;c.beginPath();c.moveTo(capeX,-neck+10);c.lineTo(capeX,-hem-7);c.moveTo(capeX-4,-neck+16);c.lineTo(capeX+4,-neck+21);c.stroke();}
 }
 if(!back){
   if(id==='royal-guardian'){
     const y0=-headTop+8,hw=side?10:15;
     c.fillStyle='#9b743c';c.fillRect(headX-hw,y0,hw*2,3);c.fillStyle='#dfb864';c.fillRect(headX-hw,y0-1,hw*2,2);
     for(const dx of[-hw+3,0,hw-3])mushroom(c,headX+dx,y0,dx===0?.9:.65);
   }
 }
 c.restore();
}
