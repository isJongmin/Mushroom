import {JOBS} from '../src/client/game/jobs.js';
import {jobCeiling,EVENT_FACTORS} from '../src/client/game/event-balance.js';
console.log('| 직업 | 보정 전 단일 대상 DPS 상한 | 이벤트 배율 | 보정 후 |');console.log('|---|---:|---:|---:|');
for(const j of JOBS){const raw=jobCeiling(j.id);console.log(`| ${j.name} | ${raw.toFixed(1)} | ${EVENT_FACTORS[j.id].toFixed(2)} | ${(raw*EVENT_FACTORS[j.id]).toFixed(1)} |`);}
console.log('\n모델: 평균 피해, 모든 투사체 명중, 스킬을 쿨타임마다 사용, 스킬 모션만큼 기본공격 시간 차감. 이동·패턴 회피·사거리·광역 다중 적중·실제 DPS는 포함하지 않음.');
