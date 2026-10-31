export const COSTUMES=Object.freeze([
 {id:'sprout-cape',name:'새싹 정찰대',need:'버섯밭 방어 1회 성공',unlocked:r=>r.clears>=1,color:'#7aaa61',trim:'#d6e9a4'},
 {id:'bloom-cape',name:'꽃잎 기사단',need:'버섯밭 방어 3회 성공',unlocked:r=>r.clears>=3,color:'#b56d91',trim:'#f4cfcd'},
 {id:'royal-guardian',name:'버섯왕 수호대',need:'버섯왕 처치 1회 성공',unlocked:r=>r.bossClears>=1,color:'#476d86',trim:'#e8bf63'}
]);
export const cleanCostume=id=>COSTUMES.some(c=>c.id===id)?id:null;
export function drawCostume(c,id,x,y,k,{back=false,rear=false,prone=false}={}){
 const s=COSTUMES.find(s=>s.id===id);if(!s||prone)return;
 c.save();c.translate(x,y);c.scale(k,k);
 if(back||rear){c.fillStyle=s.color;c.strokeStyle=s.trim;c.lineWidth=1.5;c.beginPath();c.moveTo(-15,-55);c.quadraticCurveTo(-20,-29,-22,-14);c.quadraticCurveTo(0,-4,22,-14);c.lineTo(15,-55);c.closePath();c.fill();c.stroke();
 c.strokeStyle=s.trim;c.beginPath();c.moveTo(0,-43);c.lineTo(0,-19);c.moveTo(-6,-35);c.lineTo(6,-27);c.stroke();}
 if(!back){c.fillStyle=s.trim;for(const dx of [-14,14]){c.beginPath();c.ellipse(dx,-55,8,4,dx<0?-.35:.35,0,Math.PI*2);c.fill();}c.fillStyle=s.color;c.beginPath();c.arc(0,-54,4,0,Math.PI*2);c.fill();
 if(id==='royal-guardian'){c.fillStyle='#e8bf63';c.strokeStyle='#97713e';c.lineWidth=1;c.beginPath();c.moveTo(-15,-88);c.lineTo(-18,-103);c.lineTo(-7,-97);c.lineTo(0,-109);c.lineTo(8,-97);c.lineTo(18,-103);c.lineTo(15,-88);c.closePath();c.fill();c.stroke();c.fillStyle='#9de1c5';c.beginPath();c.arc(0,-96,3,0,Math.PI*2);c.fill();}}
 c.restore();
}
