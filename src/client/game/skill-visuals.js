import { jobDefinition, abilityDefinition } from './jobs.js';

/** Shared weapon silhouettes for hotbar icons, world effects and wardrobe previews. */
export function drawSkillIcon(c, job, slot, size = 40) {
  c.save(); c.translate(size / 2, size / 2); c.scale(size / 48, size / 48);
  c.strokeStyle = jobDefinition(job).color; c.fillStyle = '#fff6d1'; c.lineWidth = 3; c.lineCap = 'round';
  const line = (x,y,a,b) => { c.beginPath(); c.moveTo(x,y); c.lineTo(a,b); c.stroke(); };
  if (slot === 3) { c.beginPath(); c.arc(0,0,20,0,Math.PI*2); c.stroke(); }
  if (job === 'warrior') {
    c.beginPath(); c.moveTo(-12,15); c.lineTo(14,-17); c.lineTo(18,-18); c.lineTo(17,-11); c.lineTo(-8,18); c.closePath(); c.fill(); c.stroke(); line(-15,7,-4,18);
  } else if (job === 'archer') {
    c.beginPath(); c.arc(-9,0,18,-1.2,1.2); c.stroke(); line(-2,-17,-2,17); line(-16,0,20,0); line(20,0,12,-6); line(20,0,12,6);
  } else if (job === 'mage') {
    line(-12,18,7,-9); c.beginPath(); for(let i=0;i<8;i++){const a=i*Math.PI/4,r=i%2?6:13;c[i?'lineTo':'moveTo'](7+Math.cos(a)*r,-9+Math.sin(a)*r);} c.closePath(); c.fill(); c.stroke();
  } else {
    c.beginPath(); for(let i=0;i<8;i++){const a=i*Math.PI/4,r=i%2?6:20;c[i?'lineTo':'moveTo'](Math.cos(a)*r,Math.sin(a)*r);} c.closePath(); c.fill(); c.stroke();
  }
  for(let i=0;i<slot;i++) { c.fillStyle=jobDefinition(job).color; c.fillRect(-17+i*7,20,4,4); }
  c.restore();
}

export function drawAbilityEffect(c, job, slot, x, y, scale, elapsed, left = false) {
  if (elapsed < 0 || elapsed > 650) return;
  const a = abilityDefinition(job, slot), t = elapsed / 650;
  c.save(); c.translate(x,y); c.scale((left?-1:1)*scale,scale);
  c.globalAlpha = (1-t) * .9; c.strokeStyle = jobDefinition(job).color; c.fillStyle = c.strokeStyle;
  c.lineWidth = slot === 3 ? 5 : 3;
  const radius = 28 + slot*14 + t*35;
  c.beginPath();
  if(job==='warrior') c.arc(15,-40,radius,-1.6,1.1);
  else if(job==='mage') c.arc(35,-40,radius,0,Math.PI*2);
  else { for(let i=0;i<=slot;i++){ c.moveTo(12,-25-i*14); c.lineTo(30+t*(60+slot*15),-25-i*14); } }
  c.stroke();
  if(slot) for(let i=0;i<slot*5;i++){const angle=i*2.4+t*2; c.fillRect(30+Math.cos(angle)*radius,-40+Math.sin(angle)*radius,4,4);}
  // Weapon follows the hand during the basic attack animation.
  c.save(); c.translate(12,-35); c.rotate(-.7+t*1.5); drawSkillIcon(c,job,0,28); c.restore();
  c.restore();
}
