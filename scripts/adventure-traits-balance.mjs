import {JOBS,abilityStats,BASIC_INTERVAL_MS} from '../src/client/game/jobs.js';
// Analytic sustained single-target model, not a measured combat benchmark.
function ceiling(job,traits){const avg=a=>(a.dmin+a.dmax)/2*a.hits,l={tier:4,highest:4,pet:'frost:4',level:5,traits};let busy=0,dps=0;for(let slot=1;slot<4;slot++){const a=abilityStats(job,slot,l);busy+=a.animMs/(a.cooldown*1000);dps+=avg(a)/a.cooldown;}return dps+avg(abilityStats(job,0,l))/(BASIC_INTERVAL_MS/1000)*Math.max(0,1-busy);}
console.log('| 직업 | 특성 없음 DPS | 전투10·기술5 | 전투5·기술10 | 모델상 화력 최대 배분 | 최대 증가율 |');console.log('|---|---:|---:|---:|---|---:|');
for(const job of JOBS){const base=ceiling(job.id,{attack:0,health:0,technique:0});let best={dps:0};for(let attack=0;attack<=10;attack++)for(let technique=0;technique<=10;technique++)if(attack+technique<=15){const dps=ceiling(job.id,{attack,health:0,technique});if(dps>best.dps)best={dps,attack,technique};}
console.log(`| ${job.name} | ${base.toFixed(1)} | ${ceiling(job.id,{attack:10,health:0,technique:5}).toFixed(1)} | ${ceiling(job.id,{attack:5,health:0,technique:10}).toFixed(1)} | 전투 ${best.attack} · 기술 ${best.technique} | +${((best.dps/base-1)*100).toFixed(1)}% |`);}
console.log('\n전설 무기 + 서리 전설 펫 +5, 모든 타격 명중, 스킬을 쿨타임마다 사용, 스킬 모션만큼 기본 공격 시간을 차감한 이론 모델. 이동·회피·투사체 충돌·범위 피해·플레이어 숙련도·실제 처치 시간은 미포함. 생존 가치나 체력 투자 효율을 평가하지 않으며 실측 결과가 아님.');
