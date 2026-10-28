// (사이클 10) 공격 강화 버프. ARCHITECTURE "사이클 10 계약". DOM 없이 동작(Node 단위 시험 가능), 그리기 함수는 canvas만 받는다.
//   range   사거리: 판정 가로 +35/스택 (기본 70)
//   multi   공격 횟수: 타수 +1/스택 (기본 1)
//   element 속성: 피해 +20%/스택, 베기 색 (1 불 주황, 2 얼음 하늘, 3 번개 노랑)
//   power   공격력: 피해 +4/스택 (기본 8~14)
//   speed   공격 속도: 쿨다운 x0.8/스택 (기본 0.45초, 최소 0.25초). attack 애니메이션 ms도 같은 비율
//   지속 60초, 다시 주우면 스택 +1(최대 3)·시간 60초 갱신, 사망하면 모두 사라짐.
// atk payload { w, hits, dmin, dmax, el }은 공격자가 자기 버프로 계산하고, 받는 쪽은 clampAttack으로 상한을 자른다.

export const BUFF_IDS = Object.freeze(['range', 'multi', 'element', 'power', 'speed']);
const BUFF_SET = new Set(BUFF_IDS);
export const isBuff = (v) => typeof v === 'string' && BUFF_SET.has(v);
export const BUFF = Object.freeze({
  durationMs: 60000,
  maxStacks: 3,
  baseW: 70,
  wPerStack: 35,
  baseHits: 1,
  dmgMin: 8,
  dmgMax: 14,
  powerPerStack: 4,
  elementPerStack: 0.2,
  cooldown: 0.45,
  cooldownMul: 0.8,
  cooldownMin: 0.25,
  animMs: 240,
  hitGapMs: 80, // multi: 피해 숫자 간격
});
// 받는 쪽 상한 (계약)
export const ATK_CAP = Object.freeze({ w: 175, hits: 4, dmax: 60, el: 3 });
export const BUFF_LABEL = Object.freeze({ range: '사거리', multi: '연속 공격', element: '속성', power: '공격력', speed: '공격 속도' });
export const BUFF_COLOR = Object.freeze({
  range: ['#9CC8FF', '#4D7CFE', '#232A5E'],
  multi: ['#FFC8DC', '#F58AB4', '#6A2348'],
  element: ['#FFE0A0', '#F08A2E', '#6A2A0E'],
  power: ['#FF8E7A', '#E8483E', '#5E1420'],
  speed: ['#BFF0DC', '#3E9A86', '#163A30'],
});
// 속성 스택별 베기 색 [안쪽, 바깥, 테두리] — 0 = 기본(흰·하늘)
export const ELEMENT_TINT = Object.freeze([
  null,
  { name: 'fire', inner: '255, 226, 140', outer: '255, 138, 46', line: '168, 52, 20' },
  { name: 'ice', inner: '224, 248, 255', outer: '120, 200, 255', line: '46, 96, 190' },
  { name: 'bolt', inner: '255, 255, 200', outer: '255, 222, 60', line: '160, 120, 10' },
]);

const clampN = (v, lo, hi, d) => (typeof v === 'number' && Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : d);

/** 버프 스택 → 공격 값 { w, hits, dmin, dmax, el, cooldown(초), animMs } */
export function attackStats(st = {}) {
  const s = (id) => Math.max(0, Math.min(BUFF.maxStacks, st[id] | 0));
  const cooldown = Math.max(BUFF.cooldownMin, BUFF.cooldown * BUFF.cooldownMul ** s('speed'));
  return {
    w: BUFF.baseW + BUFF.wPerStack * s('range'),
    hits: BUFF.baseHits + s('multi'),
    dmin: BUFF.dmgMin + BUFF.powerPerStack * s('power'),
    dmax: BUFF.dmgMax + BUFF.powerPerStack * s('power'),
    el: s('element'),
    cooldown,
    animMs: Math.round(BUFF.animMs * (cooldown / BUFF.cooldown)),
  };
}

/** 받은 atk의 강화 값 정리 (상한으로 자르고, 없으면 기본값) */
export function clampAttack(p) {
  const w = clampN(p && p.w, 1, ATK_CAP.w, BUFF.baseW);
  const hits = Math.round(clampN(p && p.hits, 1, ATK_CAP.hits, BUFF.baseHits));
  const dmax = Math.round(clampN(p && p.dmax, 0, ATK_CAP.dmax, BUFF.dmgMax));
  const dmin = Math.round(clampN(p && p.dmin, 0, dmax, Math.min(BUFF.dmgMin, dmax)));
  const el = Math.round(clampN(p && p.el, 0, ATK_CAP.el, 0));
  return { w, hits, dmin, dmax, el };
}

/** 한 번의 atk가 주는 타별 피해 목록 (속성 +20%/스택) */
export function rollHits(a, rnd = Math.random) {
  const out = [];
  for (let i = 0; i < a.hits; i++) {
    const base = a.dmin + Math.floor(rnd() * (a.dmax - a.dmin + 1));
    out.push(Math.max(1, Math.round(base * (1 + BUFF.elementPerStack * a.el))));
  }
  return out;
}

/** 내 버프 상태 */
export function createBuffs() {
  const map = new Map(); // id -> { stacks, until }
  return {
    /** 줍기: 스택 +1(최대 3), 시간 60초로 갱신 */
    add(id, now) {
      if (!isBuff(id)) return false;
      const e = map.get(id);
      map.set(id, { stacks: Math.min(BUFF.maxStacks, (e ? e.stacks : 0) + 1), until: now + BUFF.durationMs });
      return true;
    },
    clear() { map.clear(); },
    update(now) { for (const [id, e] of map) if (now >= e.until) map.delete(id); },
    stacks() { const o = {}; for (const [id, e] of map) o[id] = e.stacks; return o; },
    /** HUD/QA용 [{ id, stacks, leftMs, frac }] (BUFF_IDS 순서) */
    list(now) {
      const out = [];
      for (const id of BUFF_IDS) {
        const e = map.get(id);
        if (e) out.push({ id, stacks: e.stacks, leftMs: Math.max(0, Math.round(e.until - now)), frac: Math.max(0, Math.min(1, (e.until - now) / BUFF.durationMs)) });
      }
      return out;
    },
    get size() { return map.size; },
  };
}

/** 버프 상징 그림 (아이콘·구슬 공통). 가운데 (cx, cy), 반지름 r. 사용자 문자열 없음 */
export function drawBuffGlyph(ctx, id, cx, cy, r) {
  const [, , dark] = BUFF_COLOR[id] || BUFF_COLOR.power;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.fillStyle = '#FFFFFF';
  ctx.strokeStyle = dark;
  ctx.lineWidth = Math.max(1, r * 0.14);
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const u = r / 10;
  const poly = (pts) => { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x * u, y * u) : ctx.moveTo(x * u, y * u))); ctx.closePath(); ctx.fill(); ctx.stroke(); };
  switch (id) {
    case 'range': // 양쪽 화살표
      poly([[-7, 0], [-3, -4], [-3, -1.5], [3, -1.5], [3, -4], [7, 0], [3, 4], [3, 1.5], [-3, 1.5], [-3, 4]]);
      break;
    case 'multi': // 베기 세 줄
      for (const o of [-4, 0, 4]) poly([[-5 + o * 0.3, 5 + o * 0.2], [4 + o * 0.3, -5 + o * 0.2], [5.5 + o * 0.3, -4 + o * 0.2], [-3.5 + o * 0.3, 6 + o * 0.2]].map(([x, y]) => [x + o * 0.6, y]));
      break;
    case 'element': // 불꽃
      ctx.beginPath();
      ctx.moveTo(0, -7 * u);
      ctx.bezierCurveTo(5 * u, -2 * u, 6 * u, 3 * u, 0, 7 * u);
      ctx.bezierCurveTo(-6 * u, 3 * u, -4 * u, -1 * u, -1.5 * u, -2.5 * u);
      ctx.bezierCurveTo(-1.5 * u, 0, 0, 1 * u, 0.5 * u, -1 * u);
      ctx.closePath();
      ctx.fill(); ctx.stroke();
      break;
    case 'power': // 위 화살표 + 막대
      poly([[0, -7], [6, -1], [2.5, -1], [2.5, 6], [-2.5, 6], [-2.5, -1], [-6, -1]]);
      break;
    case 'speed': // 번개
      poly([[2, -7], [-4.5, 1], [-0.5, 1], [-2, 7], [4.5, -1.5], [0.5, -1.5]]);
      break;
    default:
      break;
  }
  ctx.restore();
}

/** 절차적 버프 구슬 / 아이콘 바탕 (원 + 광택 + 상징) */
export function drawBuffOrb(ctx, id, cx, cy, r, glow = 0) {
  const [hl, face, dark] = BUFF_COLOR[id] || BUFF_COLOR.power;
  ctx.save();
  if (glow > 0) {
    const g = ctx.createRadialGradient(cx, cy, r * 0.6, cx, cy, r * 1.7);
    g.addColorStop(0, `rgba(255,255,255,${0.5 * glow})`);
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, r * 1.7, 0, Math.PI * 2); ctx.fill();
  }
  const g = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.35, r * 0.1, cx, cy, r);
  g.addColorStop(0, hl);
  g.addColorStop(0.7, face);
  g.addColorStop(1, dark);
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
  ctx.lineWidth = Math.max(1, r * 0.12);
  ctx.strokeStyle = dark;
  ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.beginPath(); ctx.ellipse(cx - r * 0.3, cy - r * 0.45, r * 0.38, r * 0.2, -0.5, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
  drawBuffGlyph(ctx, id, cx, cy, r * 0.62);
}
