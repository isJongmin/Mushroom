// Shared job contract. IDs are persisted in profiles and sent with attacks.
export const JOBS = Object.freeze([
  { id: 'warrior', name: '검사', label: '검사', skill: '파워 스트라이크', description: '넓은 검기로 가까운 몬스터를 함께 베어요.', color: '#ffb35c', cooldown: .52, range: 105, min: 15, max: 22, hits: 1, targets: 3, speed: 0 },
  { id: 'archer', name: '궁수', label: '궁수', skill: '더블 샷', description: '멀리 날아가는 화살 두 발로 사냥해요.', color: '#8fe7aa', cooldown: .60, range: 490, min: 7, max: 11, hits: 2, targets: 1, speed: 780 },
  { id: 'mage', name: '마법사', label: '마법사', skill: '매직 버스트', description: '마력탄이 터지며 주변 몬스터를 공격해요.', color: '#bda5ff', cooldown: .72, range: 360, min: 17, max: 25, hits: 1, targets: 4, speed: 520, splash: 92 },
  { id: 'thief', name: '도적', label: '도적', skill: '럭키 세븐', description: '빠르게 회전하는 표창 두 발을 던져요.', color: '#7edfff', cooldown: .38, range: 330, min: 5, max: 8, hits: 2, targets: 1, speed: 920 },
].map(Object.freeze));
export const normalizeJob = (id) => JOBS.some(j => j.id === id) ? id : 'warrior';
export const jobDefinition = (id) => JOBS.find(j => j.id === normalizeJob(id));

// Skills are fixed contracts: the host derives damage rather than trusting client bonuses.
const SKILLS = {
  warrior: [['파워 스트라이크', 1.7, 150, 1, 3, 1], ['플레임 슬래시', 2.5, 220, 2, 5, 1], ['드래곤 블레이드', 4, 330, 4, 8, 3]],
  archer: [['트리플 샷', 1.3, 540, 3, 1, 0], ['폭발 화살', 2.5, 590, 2, 4, 1], ['피닉스 애로우', 3.5, 720, 6, 6, 1]],
  mage: [['파이어 볼', 1.5, 420, 1, 4, 1], ['프로스트 노바', 2.2, 480, 2, 6, 2], ['썬더 스톰', 3.2, 680, 4, 8, 3]],
  thief: [['트리플 스로우', 1.5, 420, 3, 1, 0], ['섀도 스핀', 2.2, 510, 4, 3, 2], ['팬텀 스타', 3.2, 660, 8, 6, 3]],
};
export const BASIC_INTERVAL_MS = 240; // animation cadence; basic attack has no skill cooldown
export function abilityDefinition(jobId, slot = 0) {
  const j = jobDefinition(jobId);
  if (!Number.isInteger(slot) || slot < 0 || slot > 3) return null;
  if (!slot) return { slot, name: '기본공격', cooldown: 0, multiplier: 1, range: j.range, hits: j.hits, targets: j.targets, el: 0, splash: j.splash || 0 };
  const [name, multiplier, range, hits, targets, el] = SKILLS[j.id][slot - 1];
  return { slot, name, multiplier, range, hits, targets, el, cooldown: [0, 3, 7, 15][slot], splash: j.speed && targets > 1 ? 80 + slot * 35 : 0 };
}
export function abilityStats(jobId, slot = 0) {
  const j = jobDefinition(jobId), a = abilityDefinition(j.id, slot);
  if (!a) return null;
  return { job: j.id, skill: slot, cooldown: a.cooldown, w: a.range, hits: a.hits,
    dmin: Math.round(j.min * a.multiplier), dmax: Math.round(j.max * a.multiplier), el: a.el, animMs: BASIC_INTERVAL_MS };
}
export function acceptJobAttack(player, attack, now) {
  if (!player || player.dead || !Number.isSafeInteger(attack.seq) || attack.seq <= (player.acceptedAttackSeq || 0)) return false;
  if (player.job && normalizeJob(player.job) !== attack.job) return false;
  if (Math.abs(attack.x - (player.targetX ?? player.x)) > 230 || Math.abs(attack.y - (player.yTo ?? player.y)) > 210) return false;
  const slot = attack.skill ?? 0, a = abilityDefinition(attack.job, slot);
  if (!a || attack.cooldown !== a.cooldown) return false;
  const times = player.acceptedSkills || {};
  if (now - (times[slot] ?? -Infinity) < (slot ? a.cooldown * 1000 : BASIC_INTERVAL_MS) - 15) return false;
  player.acceptedAttackSeq = attack.seq;
  player.acceptedAttackAt = now;
  player.acceptedSkills = { ...times, [slot]: now };
  return true;
}
