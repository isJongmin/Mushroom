import assert from 'node:assert/strict';
import { JOBS, abilityDefinition, abilityStats, acceptJobAttack, BASIC_INTERVAL_MS } from '../src/client/game/jobs.js';
import { drawSkillIcon, drawProjectileVisual, drawImpactVisual, drawAbilityEffect } from '../src/client/game/skill-visuals.js';
import { NORMAL_VISUAL_LIMITS } from '../src/client/game/normal-skill-visuals.js';
import { buildStrikePlan } from '../src/client/game/attack-patterns.js';

export function recordingContext(){
  const commands=[],stack=[];const target={globalAlpha:1,canvas:{width:1024,height:768}};
  const validate=args=>{for(const a of args)if(typeof a==='number')assert.ok(Number.isFinite(a),'non-finite Canvas argument');};
  const context=new Proxy(target,{
    set(t,key,value){if(key==='globalAlpha')assert.ok(Number.isFinite(value)&&value>=0&&value<=1,'invalid alpha');t[key]=value;return true;},
    get(t,key){if(key in t)return t[key];if(key==='save')return()=>{stack.push({...t});commands.push(['save']);};
      if(key==='restore')return()=>{assert.ok(stack.length,'unbalanced restore');Object.assign(t,stack.pop());commands.push(['restore']);};
      if(String(key).startsWith('create'))return(...args)=>{validate(args);return{addColorStop(offset,color){assert.ok(offset>=0&&offset<=1);assert.equal(typeof color,'string');}};};
      return(...args)=>{validate(args);if(key==='ellipse'||key==='arc')assert.ok(args[2]>=0,'negative radius');commands.push([key,...args]);};}
  });
  return{context,commands,balanced(){assert.equal(stack.length,0);}};
}
for(const j of JOBS)for(let slot=0;slot<3;slot++){
  const def=abilityDefinition(j.id,slot),a={...abilityStats(j.id,slot),user_id:'visual',seq:1,x:0,y:100,dir:'right'};
  const plan=buildStrikePlan(a,[{id:'mob',x:120,y:100,hp:100,s:'move'}]);
  for(const left of [false,true])for(const ms of [0,50,100,150,240,350,550,800,def.duration+300]){
    const rec=recordingContext(),c=rec.context;
    drawSkillIcon(c,j.id,slot,48);
    drawAbilityEffect(c,j.id,slot,250,300,1.5,ms,left,{origin:a,plan});
    if(def.speed)drawProjectileVisual(c,{a,x:170,y:65,dir:left?-1:1,angle:0,at:0},0,0,1.5,ms);
    drawImpactVisual(c,{job:j.id,skill:slot,x:150,y:65,at:0},0,0,1.5,ms);
    rec.balanced();assert.ok(rec.commands.length>10);
  }
}
assert.equal(NORMAL_VISUAL_LIMITS.cinematic,false);assert.ok(NORMAL_VISUAL_LIMITS.maxParticles<=16);
assert.equal(BASIC_INTERVAL_MS,360);
for(const j of JOBS){
 const a={...abilityStats(j.id),x:0,y:100,seq:1},player={x:0,y:100};
 assert.equal(a.cooldown,0);assert.equal(a.animMs,360);
 assert.equal(acceptJobAttack(player,a,0),true);
 assert.equal(acceptJobAttack(player,{...a,seq:2},240),false);
 assert.equal(acceptJobAttack(player,{...a,seq:2},360),true);
 assert.equal(abilityDefinition(j.id,1).cooldown,3);assert.equal(abilityDefinition(j.id,2).cooldown,7);assert.equal(abilityDefinition(j.id,3).cooldown,15);
}
console.log('PASS 12 ordinary visuals across phases/directions: finite geometry, valid alpha, balanced Canvas state, limited particles and 360ms basic cadence');
