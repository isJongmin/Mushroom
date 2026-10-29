import { abilityDefinition } from './jobs.js';
import { drawAbilityEffect } from './skill-visuals.js';

const living = m => m.hp > 0 && m.s !== 'die';
export const isProjectileAbility = (job, slot = 0) => !!abilityDefinition(job, slot)?.speed;

/** Fixed world geometry shared by hit simulation and effects. Never follows the caster after use. */
export function buildStrikePlan(a, mobs = []) {
  const d = a.dir === 'left' ? -1 : 1, def = abilityDefinition(a.job, a.skill ?? 0);
  if (!def || def.speed) return [];
  const frontBox = (w, h = 85) => ({ x1: a.x + (d < 0 ? -w : 0), x2: a.x + (d > 0 ? w : 0), y1: a.y - h, y2: a.y + 6 });
  const nearby = mobs.filter(m => living(m) && (m.x-a.x)*d >= -20 && (m.x-a.x)*d <= a.w && Math.abs(m.y-a.y)<130)
    .sort((m,n)=>Math.abs(m.x-a.x)-Math.abs(n.x-a.x) || String(m.id).localeCompare(String(n.id)));
  const events=[];
  const add=(delay,x,y,box,hits=1,targets=def.targets,targetId=null)=>events.push({delay,x,y,box,damage:{...a,hits},targets,targetId});
  switch(def.pattern) {
    case 'slash': add(0,a.x+d*55,a.y-40,frontBox(a.w),a.hits); break;
    case 'cross': [90,240].forEach(delay=>add(delay,a.x+d*95,a.y-40,frontBox(a.w),1)); break;
    case 'whirlwind': [220,430,640,850].forEach(delay=>add(delay,a.x,a.y-45,{x1:a.x-def.radius,x2:a.x+def.radius,y1:a.y-165,y2:a.y+10})); break;
    case 'claw': {
      const targets=nearby.slice(0,def.targets);
      if(!targets.length) targets.push({x:a.x+d*190,y:a.y,id:null});
      for(const m of targets) [100,270].forEach(delay=>add(delay,m.x,m.y-35,{x1:m.x-48,x2:m.x+48,y1:m.y-105,y2:m.y+8},1,1,m.id));
      break;
    }
    case 'beam': [150,340].forEach(delay=>add(delay,a.x+d*a.w,a.y-38,frontBox(a.w,95),1)); break;
    case 'rain': for(let i=0;i<6;i++) {
      const x=a.x+d*(60+i*88); add(260+i*125,x,a.y-25,{x1:x-46,x2:x+46,y1:a.y-260,y2:a.y+10},1,2);
    } break;
    case 'storm': for(let i=0;i<4;i++) {
      const m=nearby[i], x=m?.x ?? a.x+d*(110+i*155), y=m?.y ?? a.y;
      add(240+i*240,x,y-30,{x1:x-82,x2:x+82,y1:y-280,y2:y+12},1,2);
    } break;
  }
  return events.map((e,i)=>({...e,id:`${a.user_id}:${a.seq}:strike${i}`}));
}

/** Delayed strikes and complete cast effects; no timers survive a room/map teardown. */
export function createSkillAttacks() {
  const casts=[], acknowledgements=new Map();
  return {
    add(a,now,authoritative=false,mobs=[]) {
      const id=`${a.user_id}:${a.seq}`;
      if(casts.some(c=>c.id===id)) return;
      const plan=buildStrikePlan(a,mobs).map(e=>{
        const ack=acknowledgements.get(e.id);
        return {...e,at:now+e.delay,done:false,...(ack?{x:ack.x,y:ack.y}: {})};
      });
      casts.push({id,a:{...a},at:now,authoritative,plan});
      if(casts.length>100) casts.shift();
    },
    update(now,hit) {
      for(const c of casts) for(const e of c.plan) if(!e.done && now>=e.at) {
        e.done=true;
        if(c.authoritative) hit(e,c.a);
      }
      for(let i=casts.length-1;i>=0;i--) if(now-casts[i].at>abilityDefinition(casts[i].a.job,casts[i].a.skill??0).duration+350) casts.splice(i,1);
      for(const [id,ack] of acknowledgements) if(now-ack.at>5000) acknowledgements.delete(id);
    },
    impact(id,x,y,now) {
      if(!id.includes(':strike')) return;
      acknowledgements.set(id,{x,y,at:now});
      while(acknowledgements.size>512) acknowledgements.delete(acknowledgements.keys().next().value);
      for(const c of casts) { const e=c.plan.find(e=>e.id===id); if(e){e.x=x;e.y=y;} }
    },
    draw(ctx,camX,camY,k,now) {
      ctx.save(); ctx.setTransform(1,0,0,1,0,0);
      for(const c of casts) drawAbilityEffect(ctx,c.a.job,c.a.skill??0,(c.a.x-camX)*k,(c.a.y-camY)*k,k,now-c.at,c.a.dir==='left',{plan:c.plan,origin:c.a});
      ctx.restore();
    },
    clear(){casts.length=0;acknowledgements.clear();},
    get count(){return casts.length;},
    snapshot(){return casts.map(c=>({id:c.id,pattern:abilityDefinition(c.a.job,c.a.skill??0).pattern,events:c.plan.map(e=>({id:e.id,done:e.done,box:{...e.box}}))}));},
  };
}
