import { ultimatePresentation, drawUltimateBackdrop } from './ultimate-visuals.js';
import { abilityDefinition } from './jobs.js';
import { drawAbilityEffect } from './skill-visuals.js';

const living = m => m.hp > 0 && m.s !== 'die';
export const isProjectileAbility = (job, slot = 0) => !!abilityDefinition(job, slot)?.speed;

/** Fixed world geometry shared by hit simulation and effects. Never follows the caster after use. */
export function buildStrikePlan(a, mobs = []) {
  const d = a.dir === 'left' ? -1 : 1, def = abilityDefinition(a.job, a.skill ?? 0);
  if (!def || (def.speed && !def.finisher)) return [];
  const frontBox = (w, h = 85) => ({ x1: a.x + (d < 0 ? -w : 0), x2: a.x + (d > 0 ? w : 0), y1: a.y - h, y2: a.y + 6 });
  const nearby = mobs.filter(m => living(m) && (m.x-a.x)*d >= -20 && (m.x-a.x)*d <= a.w && Math.abs(m.y-a.y)<130)
    .sort((m,n)=>Math.abs(m.x-a.x)-Math.abs(n.x-a.x) || String(m.id).localeCompare(String(n.id)));
  const events=[];
  const add=(delay,x,y,box,hits=1,targets=def.targets,targetId=null)=>events.push({delay,x,y,box,damage:{...a,hits},targets,targetId});
  switch(def.pattern) {
    case 'slash': add(0,a.x+d*55,a.y-40,frontBox(a.w),a.hits); break;
    case 'cross': [90,240].forEach(delay=>add(delay,a.x+d*95,a.y-40,frontBox(a.w),1)); break;
    case 'whirlwind':
      [600,850,1100].forEach(delay=>add(delay,a.x,a.y-45,{x1:a.x-def.radius,x2:a.x+def.radius,y1:a.y-180,y2:a.y+10}));
      add(1500,a.x,a.y-50,{x1:a.x-def.radius,x2:a.x+def.radius,y1:a.y-420,y2:a.y+12},3,8);events.at(-1).phase='final';
      add(1800,a.x,a.y-20,{x1:a.x-def.radius,x2:a.x+def.radius,y1:a.y-110,y2:a.y+12},1,8);break;
    case 'claw': {
      const targets=nearby.slice(0,def.targets);
      if(!targets.length) targets.push({x:a.x+d*190,y:a.y,id:null});
      for(const m of targets) [100,270].forEach(delay=>add(delay,m.x,m.y-35,{x1:m.x-48,x2:m.x+48,y1:m.y-105,y2:m.y+8},1,1,m.id));
      break;
    }
    case 'beam': [150,340].forEach(delay=>add(delay,a.x+d*a.w,a.y-38,frontBox(a.w,95),1)); break;
    case 'rain': for(let i=0;i<6;i++) {
      const x=a.x+d*(60+i*88); add(700+i*130,x,a.y-25,{x1:x-46,x2:x+46,y1:a.y-260,y2:a.y+10},1,2);
    }
      add(1740,a.x+d*320,a.y-40,frontBox(a.w,380),3,8);events.at(-1).phase='final';
      break;
    case 'storm': for(let i=0;i<4;i++) {
      const m=nearby[i], x=m?.x ?? a.x+d*(110+i*155), y=m?.y ?? a.y;
      add(650+i*210,x,y-30,{x1:x-82,x2:x+82,y1:y-280,y2:y+12},1,2);
    }
      add(1740,a.x+d*340,a.y-40,frontBox(a.w,450),3,8);events.at(-1).phase='final';
      break;
    case 'clones':
      add(1660,a.x+d*330,a.y-40,frontBox(a.w,220),4,8);events.at(-1).phase='final';break;
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
      if(casts.length>100){const ordinary=casts.findIndex(c=>(c.a.skill??0)!==3);casts.splice(ordinary<0?0:ordinary,1);}
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
      for(const c of casts) {
        const sx=(c.a.x-camX)*k,sy=(c.a.y-camY)*k;
        const reach=Math.max(c.a.w,abilityDefinition(c.a.job,c.a.skill??0).radius||0)*k;
        if(ctx.canvas&&(sx+reach< -100||sx-reach>ctx.canvas.width+100||sy+100<0||sy-750*k>ctx.canvas.height+100))continue;
        drawAbilityEffect(ctx,c.a.job,c.a.skill??0,sx,sy,k,now-c.at,c.a.dir==='left',{plan:c.plan,origin:c.a});
      }
      ctx.restore();
    },
    presentation(now,userId,reduced=false) {
      const c=casts.findLast(c=>(c.a.skill??0)===3&&c.a.user_id===userId);
      if(!c)return {x:0,y:0};
      return ultimatePresentation(now-c.at,abilityDefinition(c.a.job,3).impactAt,reduced);
    },
    drawBackdrop(ctx,width,height,now,userId,reduced=false,dpr=1) {
      const c=casts.findLast(c=>(c.a.skill??0)===3&&c.a.user_id===userId);
      if(c)drawUltimateBackdrop(ctx,width,height,c.a.job,now-c.at,abilityDefinition(c.a.job,3),reduced,dpr);
    },
    clear(){casts.length=0;acknowledgements.clear();},
    get count(){return casts.length;},
    snapshot(){return casts.map(c=>({id:c.id,pattern:abilityDefinition(c.a.job,c.a.skill??0).pattern,events:c.plan.map(e=>({id:e.id,done:e.done,box:{...e.box}}))}));},
  };
}
