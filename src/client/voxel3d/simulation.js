import {clamp} from './engine.js';
import {ground,blocked} from './world.js';
export function moveBody(p,dx,dz,dt,obstacles){const steps=Math.max(1,Math.ceil(Math.hypot(dx,dz)*dt/.18));for(let n=0;n<steps;n++){const x=clamp(p.x+dx*dt/steps,-26.8,26.8);if(!blocked(x,p.z,obstacles)&&ground(x,p.z)<=p.y+.65)p.x=x;const z=clamp(p.z+dz*dt/steps,-26.8,26.8);if(!blocked(p.x,z,obstacles)&&ground(p.x,z)<=p.y+.65)p.z=z;}}
export function inStrike(p,m,range,cone=-1){const dx=m.x-p.x,dz=m.z-p.z,d=Math.hypot(dx,dz);return d<=range+(m.boss?.8:.3)&&(d<.3||((dx*Math.sin(p.yaw)+dz*Math.cos(p.yaw))/d)>=cone);}
export function nearestTarget(p,mobs,range=10){let chosen=null,best=range;for(const m of mobs){const d=Math.hypot(m.x-p.x,m.z-p.z);if(m.hp>0&&d<best){chosen=m;best=d;}}return chosen;}
export function safeSpawn(mobs,p,obstacles,seed=0){for(let n=0;n<80;n++){const a=(n+seed)*2.399,r=6+(n%8)*1.1,x=Math.cos(a)*r,z=Math.sin(a)*r;if(Math.hypot(x-p.x,z-p.z)>4&&!blocked(x,z,obstacles,.8)&&!mobs.some(m=>m.hp>0&&Math.hypot(m.x-x,m.z-z)<1.5))return {x,z,y:ground(x,z)};}return null;}
