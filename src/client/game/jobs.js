// Shared job contract. IDs are persisted in profiles and sent with attacks.
export const JOBS = Object.freeze([
  { id: 'warrior', name: '검사', label: '검사', skill: '검 베기', description: '넓은 검기로 가까운 몬스터를 함께 베어요.', color: '#ffb35c', cooldown: .52, range: 105, min: 15, max: 22, hits: 1, targets: 3, speed: 0 },
  { id: 'archer', name: '궁수', label: '궁수', skill: '더블 샷', description: '멀리 날아가는 화살 두 발로 사냥해요.', color: '#8fe7aa', cooldown: .60, range: 490, min: 7, max: 11, hits: 2, targets: 1, speed: 780 },
  { id: 'mage', name: '마법사', label: '마법사', skill: '에너지 볼', description: '에너지 볼·매직 클로·썬더 빔·광역 낙뢰를 사용해요.', color: '#bda5ff', cooldown: .72, range: 360, min: 17, max: 25, hits: 1, targets: 4, speed: 520, splash: 92 },
  { id: 'thief', name: '도적', label: '도적', skill: '표창 던지기', description: '빠르게 회전하는 표창 두 발을 던져요.', color: '#7edfff', cooldown: .38, range: 330, min: 5, max: 8, hits: 2, targets: 1, speed: 920 },
].map(Object.freeze));
export const normalizeJob = (id) => JOBS.some(j => j.id === id) ? id : 'warrior';
export const jobDefinition = (id) => JOBS.find(j => j.id === normalizeJob(id));

// Skills are fixed contracts: the host derives damage rather than trusting client bonuses.
const SKILLS = {
  warrior: [['크로스 슬래시', 1.7, 155, 2, 3, 0], ['플레임 웨이브', 2.5, 460, 2, 5, 1], ['블레이드 템페스트', 4, 230, 4, 8, 3]],
  archer: [['스프레드 샷', 1.3, 540, 3, 1, 0], ['폭발 화살', 2.5, 590, 2, 4, 1], ['애로우 레인', 3.5, 600, 6, 6, 0]],
  mage: [['매직 클로', 1.5, 420, 2, 2, 0], ['썬더 빔', 2.2, 560, 2, 6, 3], ['썬더 스톰', 3.2, 680, 4, 8, 3]],
  thief: [['트리플 스로우', 1.5, 420, 3, 1, 0], ['섀도 스핀', 2.2, 510, 4, 3, 2], ['섀도 클론', 3.2, 660, 9, 6, 3]],
};
// Every slot owns an attack shape, trajectory and visual language (not a recolor).
const PATTERNS = {
  warrior: [
    { pattern: 'slash', description: '전방의 적을 짧게 베어요.', duration: 300, name: '검 베기' },
    { pattern: 'cross', description: '서로 교차하는 검격으로 두 번 베어요.', duration: 600 },
    { pattern: 'wave', description: '지면을 따라 불꽃 검기를 날려 폭발시켜요.', duration: 900, speed: 650, shots: 1, splash: 85 },
    { pattern: 'whirlwind', description: '주변을 회전 검기로 네 번 휩쓸어요.', duration: 1250, radius: 230 },
  ],
  archer: [
    { pattern: 'arrow', description: '전방에 화살 두 발을 연속으로 쏴요.', duration: 300, name: '더블 샷', speed: 850, shots: 2 },
    { pattern: 'fan', description: '세 방향으로 화살을 동시에 펼쳐 쏴요.', duration: 550, speed: 900, shots: 3, spread: .17 },
    { pattern: 'bomb', description: '명중한 위치에서 넓게 폭발하는 화살을 쏴요.', duration: 800, speed: 650, shots: 1, splash: 145 },
    { pattern: 'rain', description: '전방 여섯 구역에 화살비를 차례로 내려요.', duration: 1400 },
  ],
  mage: [
    { pattern: 'orb', description: '빛나는 에너지 볼을 전방으로 날려요.', duration: 400, name: '에너지 볼', speed: 520, shots: 1 },
    { pattern: 'claw', description: '가까운 적 위치에 마력 발톱을 두 번 새겨요.', duration: 750 },
    { pattern: 'beam', description: '긴 번개 광선으로 전방의 여러 적을 관통해요.', duration: 850 },
    { pattern: 'storm', description: '적이 있는 구역에 거대한 낙뢰를 차례로 내려요.', duration: 1500 },
  ],
  thief: [
    { pattern: 'star', description: '표창 두 개를 빠르게 던져요.', duration: 350, name: '표창 던지기', speed: 920, shots: 2 },
    { pattern: 'triple', description: '빠른 세 번의 투척으로 적을 집중 공격해요.', duration: 650, speed: 1100, shots: 3 },
    { pattern: 'saw', description: '거대한 회전 표창을 날려 주변을 갈라요.', duration: 900, speed: 480, shots: 1, splash: 105 },
    { pattern: 'clones', description: '세 분신이 서로 다른 위치에서 아홉 표창을 던져요.', duration: 1350, speed: 1000, shots: 9 },
  ],
};
export const BASIC_INTERVAL_MS = 240; // animation cadence; basic attack has no skill cooldown
export function abilityDefinition(jobId, slot = 0) {
  const j = jobDefinition(jobId);
  if (!Number.isInteger(slot) || slot < 0 || slot > 3) return null;
  if (!slot) return { slot, cooldown: 0, multiplier: 1, range: j.range, hits: j.hits, targets: j.id === 'mage' ? 1 : j.targets, el: 0, splash: 0, ...PATTERNS[j.id][0] };
  const [name, multiplier, range, hits, targets, el] = SKILLS[j.id][slot - 1];
  return { slot, name, multiplier, range, hits, targets, el, cooldown: [0, 3, 7, 15][slot], splash: 0, ...PATTERNS[j.id][slot] };
}
export function abilityStats(jobId, slot = 0) {
  const j = jobDefinition(jobId), a = abilityDefinition(j.id, slot);
  if (!a) return null;
  return { job: j.id, skill: slot, cooldown: a.cooldown, w: a.range, hits: a.hits,
    dmin: Math.round(j.min * a.multiplier), dmax: Math.round(j.max * a.multiplier), el: a.el, animMs: slot ? Math.min(500, a.duration * .5) : BASIC_INTERVAL_MS };
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
