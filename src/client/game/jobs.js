// Shared job contract. IDs are persisted in profiles and sent with attacks.
export const JOBS = Object.freeze([
  { id: 'warrior', name: '검사', label: '검사', skill: '파워 스트라이크', description: '넓은 검기로 가까운 몬스터를 함께 베어요.', color: '#ffb35c', cooldown: .52, range: 105, min: 15, max: 22, hits: 1, targets: 3, speed: 0 },
  { id: 'archer', name: '궁수', label: '궁수', skill: '더블 샷', description: '멀리 날아가는 화살 두 발로 사냥해요.', color: '#8fe7aa', cooldown: .60, range: 490, min: 7, max: 11, hits: 2, targets: 1, speed: 780 },
  { id: 'mage', name: '마법사', label: '마법사', skill: '매직 버스트', description: '마력탄이 터지며 주변 몬스터를 공격해요.', color: '#bda5ff', cooldown: .72, range: 360, min: 17, max: 25, hits: 1, targets: 4, speed: 520, splash: 92 },
  { id: 'thief', name: '도적', label: '도적', skill: '럭키 세븐', description: '빠르게 회전하는 표창 두 발을 던져요.', color: '#7edfff', cooldown: .38, range: 330, min: 5, max: 8, hits: 2, targets: 1, speed: 920 },
].map(Object.freeze));
export const normalizeJob = (id) => JOBS.some(j => j.id === id) ? id : 'warrior';
export const jobDefinition = (id) => JOBS.find(j => j.id === normalizeJob(id));

/** Replay/cadence/origin validation shared by the host and spectators. */
export function acceptJobAttack(player, attack, now) {
  if (!player || player.dead || !Number.isSafeInteger(attack.seq) || attack.seq <= (player.acceptedAttackSeq || 0)) return false;
  if (Math.abs(attack.x - (player.targetX ?? player.x)) > 230 || Math.abs(attack.y - (player.yTo ?? player.y)) > 210) return false;
  const base = jobDefinition(attack.job).cooldown;
  const claimed = attack.cooldown ?? base;
  // Buff speed has eleven discrete legal values; do not accept arbitrary client timing.
  const legal = Array.from({ length: 11 }, (_, n) => Math.round(Math.max(.1, base * .8 ** n) * 1000) / 1000);
  if (!legal.includes(claimed)) return false;
  const floor = Math.max(.1, base * .8 ** 10);
  const interval = Math.max(floor * 1000, claimed * 1000 - 15);
  if (now - (player.acceptedAttackAt ?? -Infinity) < interval) return false;
  player.acceptedAttackSeq = attack.seq;
  player.acceptedAttackAt = now;
  return true;
}
