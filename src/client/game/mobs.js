// (사이클 9) 몬스터: manifest 정리, 스폰 구역, 호스트 시뮬레이션, 화면 표시(보간), 그리기. ARCHITECTURE "사이클 9 계약".
//
// - manifest: assets/mob/manifest.json (아트 소유) { density, mobs: { <id>: { name, hp, speed, touchDamage, size{w,h}, anchor{x,y},
//   frame{w,h}, sheet, animations{move,hit,die}, fps, behavior: walk|hop|fly, buffDrop(0~1), buffDropCount? } }, ghost, tombstone, fx }.
//   (사이클 10) 의상 drops는 폐기, 버프 드롭 확률 buffDrop(없으면 계약 기본값: snail 0.35, bat 0.4, mushroom 0.45, slime 0.5, golem 1.0 x2).
//   ghost/tombstone은 문자열 경로 또는 { src|sheet, anchor{x,y}, frame{w,h}, fps } 를 받는다. 없으면 절차적 대체 그림.
//   시트는 가로 한 줄 프레임, 기본 방향은 오른쪽(manifest facing: 'left'면 반대). 파일이 없으면 종류별 절차적 그림.
// - 스폰 구역: 맵 manifest spawns [{ id, platform: <발판 id | "ground">, x1, x2, mobs: [kind..], max }].
// - 호스트만 시뮬레이션(createMobSim)하고 mobs { t, list:[{ id, kind, x, y, dir, hp, s, z }] }를 5회/초 보낸다.
//   z = 스폰 구역 번호(정수, 같은 맵 manifest라 모두 같다): 호스트가 바뀌면 새 호스트가 순찰 범위와 리스폰을 이어 간다.
// - 다른 클라이언트는 createMobView로 받은 기록을 220ms 늦게 재생(두 기록 사이 직선 보간)한다.
import { loadImage, warnOnce } from '../assets.js';
import { BUFF_IDS } from './buffs.js';

const REPO_ROOT = new URL('../../../', import.meta.url);
const SRC_RE = /^assets\/[a-z0-9_\-/]+\.(png|webp)$/i;
const KIND_RE = /^[a-z0-9-]{1,32}$/;
export const MOB_STATES = Object.freeze(['move', 'hit', 'die']);
export const MOB_LIMITS = Object.freeze({ total: 60, perZone: 20, zones: 32 });
export const RESPAWN_MS = 8000;
export const DIE_MS = 650; // 처치 후 목록에 남는 시간 (die 애니메이션)
export const HIT_MS = 300;
const INTERP_MS = 220;
const BUF_MAX = 6;

const fin = (v) => typeof v === 'number' && Number.isFinite(v);
const clampN = (v, lo, hi, d) => (fin(v) ? Math.min(hi, Math.max(lo, v)) : d);

// (사이클 10) 계약 기본 버프 드롭 확률과 개수
const BUFF_DROP_DEFAULT = Object.freeze({ snail: 0.35, bat: 0.4, mushroom: 0.45, slime: 0.5, golem: 1.0 });
const BUFF_COUNT_DEFAULT = Object.freeze({ golem: 2 });

function fxSpec(raw, keys, density) {
  const fx = raw && raw.fx && typeof raw.fx === 'object' ? raw.fx : null;
  if (!fx) return null;
  for (const k of keys) if (fx[k]) return spriteSpec(fx[k], null, density);
  return null;
}
function buffIconSpec(raw, id, density) {
  const fx = raw && raw.fx && typeof raw.fx === 'object' ? raw.fx : null;
  if (!fx) return null;
  const b = fx.buff || fx.buffs || fx.buffIcons;
  if (b && typeof b === 'object' && typeof b.pattern === 'string' && (!Array.isArray(b.ids) || b.ids.includes(id))) {
    return spriteSpec(b.pattern.replace('{id}', id), null, density); // 아트: { pattern: 'assets/fx/buff/{id}.png', ids }
  }
  if (b && typeof b === 'object' && b[id]) return spriteSpec(b[id], null, density);
  if (fx[`buff_${id}`]) return spriteSpec(fx[`buff_${id}`], null, density);
  return null;
}

function resolveSrc(src) {
  if (typeof src !== 'string' || !SRC_RE.test(src) || src.includes('..')) return null;
  return new URL(src, REPO_ROOT);
}

function spriteSpec(raw, defaultSrc, density) {
  let src = null;
  let o = {};
  if (typeof raw === 'string') src = raw;
  else if (raw && typeof raw === 'object') { o = raw; src = typeof raw.src === 'string' ? raw.src : raw.sheet; }
  else if (raw === undefined) src = defaultSrc;
  const url = resolveSrc(src);
  if (!url) return null;
  return {
    url,
    frameW: clampN(o.frame && o.frame.w, 1, 2048, 0) || 0,
    frameH: clampN(o.frame && o.frame.h, 1, 2048, 0) || 0,
    anchorX: fin(o.anchor && o.anchor.x) ? o.anchor.x : null,
    anchorY: fin(o.anchor && o.anchor.y) ? o.anchor.y : null,
    fps: clampN(o.fps, 1, 30, 6),
    density: clampN(o.density, 0.25, 8, density),
    order: Array.isArray(o.order) ? o.order.filter((v) => typeof v === 'string').slice(0, 16) : null, // 구슬 시트 프레임 순서
  };
}

const DEFAULT_SIZE = { snail: [40, 30], mushroom: [44, 44], slime: [46, 38], bat: [46, 30], golem: [84, 96] };

/** manifest 정리. 형식이 아니면 null */
export function normalizeMobManifest(raw) {
  if (!raw || typeof raw !== 'object' || !raw.mobs || typeof raw.mobs !== 'object') return null;
  const density = clampN(raw.density, 0.25, 8, 1.5);
  const kinds = new Map();
  for (const [id, m] of Object.entries(raw.mobs).slice(0, 32)) {
    if (!KIND_RE.test(id) || !m || typeof m !== 'object') continue;
    const ds = DEFAULT_SIZE[id] || [44, 40];
    const behavior = m.behavior === 'hop' || m.behavior === 'fly' ? m.behavior : 'walk';
    const anims = {};
    for (const a of MOB_STATES) {
      const list = m.animations && Array.isArray(m.animations[a]) ? m.animations[a].filter((f) => Number.isInteger(f) && f >= 0 && f < 64) : [];
      anims[a] = list.slice(0, 16);
    }
    const buffDrop = clampN(m.buffDrop, 0, 1, BUFF_DROP_DEFAULT[id] ?? 0.35);
    const buffDropCount = Math.round(clampN(m.buffDropCount, 1, 4, BUFF_COUNT_DEFAULT[id] ?? 1));
    const frame = { w: clampN(m.frame && m.frame.w, 1, 1024, 0), h: clampN(m.frame && m.frame.h, 1, 1024, 0) };
    kinds.set(id, Object.freeze({
      id,
      name: typeof m.name === 'string' ? m.name.slice(0, 20) : id,
      hp: Math.round(clampN(m.hp, 1, 100000, 30)),
      speed: clampN(m.speed, 0, 400, 50),
      touchDamage: Math.round(clampN(m.touchDamage, 0, 100, 5)),
      size: { w: clampN(m.size && m.size.w, 8, 400, ds[0]), h: clampN(m.size && m.size.h, 8, 400, ds[1]) },
      anchor: { x: fin(m.anchor && m.anchor.x) ? m.anchor.x : null, y: fin(m.anchor && m.anchor.y) ? m.anchor.y : null },
      frame,
      sheet: resolveSrc(m.sheet),
      animations: anims,
      fps: clampN(m.fps, 1, 30, 8),
      behavior,
      facingLeft: m.facing === 'left',
      buffDrop,
      buffDropCount,
    }));
  }
  return {
    density,
    kinds,
    ghost: spriteSpec(raw.ghost, 'assets/mob/ghost.png', density),
    tombstone: spriteSpec(raw.tombstone, 'assets/mob/tombstone.png', density),
    // 아트 확장 키: 슬래시(fx.slash), 드롭 받침(dropBag). 없으면 절차적 그림
    slash: raw.fx && raw.fx.slash ? spriteSpec(raw.fx.slash, null, density) : null,
    // (사이클 10) 속성 베기 3종, 버프 구슬(가로 5프레임 range,multi,element,power,speed), 버프 아이콘 5종.
    // manifest fx에 적힌 것만 받는다(없는 파일을 짐작해 요청하지 않음 → 404 없음). 없으면 절차적 그림.
    slashEl: [null, fxSpec(raw, ['slash_fire', 'slashFire'], density), fxSpec(raw, ['slash_ice', 'slashIce'], density), fxSpec(raw, ['slash_bolt', 'slashBolt'], density)],
    buffOrb: fxSpec(raw, ['buff_orb', 'buffOrb'], density),
    buffIcons: Object.fromEntries(BUFF_IDS.map((id) => [id, buffIconSpec(raw, id, density)])),
    dropBag: raw.dropBag ? spriteSpec(raw.dropBag, null, density) : null,
  };
}

/** assets/mob/manifest.json 받기. 없거나 깨지면 null (몬스터 없이, 유령·비석은 대체 그림) */
export async function loadMobManifest() {
  try {
    const res = await fetch(new URL('assets/mob/manifest.json', REPO_ROOT).href, { cache: 'no-cache' });
    if (!res.ok) { warnOnce('mob:manifest', 'assets/mob/manifest.json이 없습니다 (몬스터 없이, 유령/비석은 대체 그림)'); return null; }
    const m = normalizeMobManifest(await res.json());
    if (!m) warnOnce('mob:manifest-bad', 'assets/mob/manifest.json 형식이 계약과 다릅니다 (몬스터 없이 동작)');
    return m;
  } catch {
    return null;
  }
}

/** 단일 스프라이트(유령, 비석) 받기 → { img, anchorX, anchorY, density, frameW, frameH, fps } | null */
export async function loadSprite(spec) {
  if (!spec) return null;
  const img = await loadImage(spec.url);
  if (!img) return null;
  const fw = spec.frameW || img.naturalWidth;
  const fh = spec.frameH || img.naturalHeight;
  return {
    img, density: spec.density, fps: spec.fps, frameW: fw, frameH: fh,
    anchorX: spec.anchorX ?? fw / 2, anchorY: spec.anchorY ?? fh, order: spec.order || null,
  };
}

/**
 * 스폰 구역 정리. platforms = 정리된 발판, world = { groundY, minX, maxX }. 종류가 manifest에 없는 몬스터는 뺀다.
 * @returns [{ i, id, y, x1, x2, mobs:[kind], max }]
 */
export function normalizeZones(raw, platforms, world, kinds) {
  if (!Array.isArray(raw) || !kinds || !kinds.size) return [];
  const out = [];
  for (const z of raw.slice(0, MOB_LIMITS.zones)) {
    if (!z || typeof z !== 'object') continue;
    let y;
    let lo;
    let hi;
    if (z.platform === 'ground' || z.platform == null) { y = world.groundY; lo = world.minX; hi = world.maxX; } else {
      const p = platforms.find((q) => q.id === z.platform);
      if (!p) continue;
      y = p.y; lo = p.x1 + 8; hi = p.x2 - 8;
    }
    const x1 = Math.max(lo, Math.min(fin(z.x1) ? z.x1 : lo, fin(z.x2) ? z.x2 : hi));
    const x2 = Math.min(hi, Math.max(fin(z.x1) ? z.x1 : lo, fin(z.x2) ? z.x2 : hi));
    if (x2 - x1 < 4) continue;
    const mobs = Array.isArray(z.mobs) ? z.mobs.filter((k) => typeof k === 'string' && kinds.has(k)) : [];
    if (!mobs.length) continue;
    out.push(Object.freeze({
      i: out.length, id: typeof z.id === 'string' ? z.id.slice(0, 32) : `z${out.length}`, y, x1, x2,
      mobs: Object.freeze(mobs), max: Math.round(clampN(z.max, 1, MOB_LIMITS.perZone, 3)),
    }));
  }
  return out;
}

const rid = () => Math.random().toString(36).slice(2, 7);

/**
 * 호스트 시뮬레이션.
 * @param o.kinds  Map kind → spec
 * @param o.zones  normalizeZones 결과
 * @param o.rnd    난수 (시험용)
 */
export function createMobSim(o) {
  const { kinds, zones } = o;
  const rnd = o.rnd || Math.random;
  const mobs = new Map(); // id -> sim mob
  const pending = zones.map(() => []); // 구역별 리스폰 예정 시각(ms)
  let seq = 0;
  const stats = { spawned: 0, killed: 0 };

  function spawn(z, now, near) {
    const kind = z.mobs[Math.floor(rnd() * z.mobs.length)];
    const spec = kinds.get(kind);
    const x = near != null ? near : z.x1 + rnd() * (z.x2 - z.x1);
    const m = {
      id: `${rid()}${(seq++).toString(36)}`, kind, z: z.i, x, y: z.y, base: z.y, dir: rnd() < 0.5 ? -1 : 1,
      hp: spec.hp, max: spec.hp, s: 'move', vy: 0, air: false, hitT: 0, dieT: 0, turnT: 2 + rnd() * 4, hopT: 0.4 + rnd(), pauseT: 0,
      phase: rnd() * Math.PI * 2,
    };
    if (spec.behavior === 'fly') m.y = z.y - 64;
    mobs.set(m.id, m);
    stats.spawned++;
    return m;
  }

  function aliveIn(zi) {
    let n = 0;
    for (const m of mobs.values()) if (m.z === zi) n++;
    return n;
  }

  /** 처음 시작(받은 상태 없음): 모든 구역을 채운다 */
  function fill(now) {
    for (const z of zones) while (aliveIn(z.i) + pending[z.i].length < z.max && aliveIn(z.i) < z.max) {
      if (mobs.size >= MOB_LIMITS.total) return;
      spawn(z, now);
    }
  }

  /** 호스트 인계: 마지막으로 받은(보이는) 상태에서 이어 간다. 모자란 수는 리스폰 예정으로 */
  function load(list, now) {
    mobs.clear();
    for (const p of pending) p.length = 0;
    for (const v of list) {
      const z = zones[v.z];
      const spec = kinds.get(v.kind);
      if (!z || !spec || mobs.size >= MOB_LIMITS.total) continue;
      if (v.s === 'die' || v.hp <= 0) { pending[z.i].push(now + RESPAWN_MS); continue; }
      mobs.set(v.id, {
        id: v.id, kind: v.kind, z: z.i, x: Math.min(z.x2, Math.max(z.x1, v.x)), y: spec.behavior === 'fly' ? v.y : z.y, base: z.y,
        dir: v.dir < 0 ? -1 : 1, hp: Math.min(spec.hp, v.hp), max: spec.hp, s: 'move', vy: 0, air: false, hitT: 0, dieT: 0,
        turnT: 2 + rnd() * 4, hopT: 0.4 + rnd(), pauseT: 0, phase: rnd() * Math.PI * 2,
      });
    }
    for (const z of zones) {
      const missing = z.max - aliveIn(z.i) - pending[z.i].length;
      for (let i = 0; i < missing; i++) pending[z.i].push(now + RESPAWN_MS);
    }
  }

  function step(dt, now) {
    for (const m of [...mobs.values()]) {
      const z = zones[m.z];
      const spec = kinds.get(m.kind);
      if (!z || !spec) { mobs.delete(m.id); continue; }
      if (m.s === 'die') {
        m.dieT -= dt;
        if (m.dieT <= 0) { mobs.delete(m.id); pending[z.i].push(now + RESPAWN_MS); }
        continue;
      }
      if (m.hitT > 0) { m.hitT -= dt; m.s = m.hitT > 0 ? 'hit' : 'move'; }
      const moving = m.hitT <= 0;
      m.phase += dt;
      if (spec.behavior === 'fly') {
        if (moving) m.x += m.dir * spec.speed * dt;
        m.y = z.y - 64 + Math.sin(m.phase * 2.2) * 16;
      } else if (moving) { // walk, hop (hop의 뜀 높이는 시트 프레임에 들어 있다: 아트 manifest note. y는 바닥 그대로)
        if (m.pauseT > 0) m.pauseT -= dt;
        else m.x += m.dir * spec.speed * dt;
      }
      // 순찰 범위 끝에서 방향 반전, 가끔 돌아서거나 쉰다
      if (m.x <= z.x1) { m.x = z.x1; m.dir = 1; }
      if (m.x >= z.x2) { m.x = z.x2; m.dir = -1; }
      m.turnT -= dt;
      if (m.turnT <= 0) {
        m.turnT = 2 + rnd() * 4;
        const r = rnd();
        if (r < 0.35) m.dir = -m.dir;
        else if (r < 0.55 && spec.behavior === 'walk') m.pauseT = 0.6 + rnd() * 1.2;
      }
    }
    // 리스폰
    for (const z of zones) {
      const p = pending[z.i];
      for (let i = p.length - 1; i >= 0; i--) {
        if (now >= p[i]) {
          p.splice(i, 1);
          if (aliveIn(z.i) < z.max && mobs.size < MOB_LIMITS.total) spawn(z, now);
        }
      }
    }
  }

  /**
   * 공격 판정 상자에 맞은 몬스터 하나(공격자에 가장 가까운 것)에 타별 피해를 차례로. 처치되면 남은 타는 버리고 버프 드롭을 굴린다.
   * @param dmgs 타별 피해 [n..] (multi 버프면 여러 개)
   * @returns null | { mob, dmgs(실제로 들어간 타), killed, buffs(드롭할 버프 id 목록) }
   */
  function hit(box, ax, dir, dmgs) {
    let best = null;
    let bestD = Infinity;
    for (const m of mobs.values()) {
      if (m.s === 'die') continue;
      const spec = kinds.get(m.kind);
      const b = { x1: m.x - spec.size.w / 2, x2: m.x + spec.size.w / 2, y1: m.y - spec.size.h, y2: m.y };
      if (!(box.x1 < b.x2 && box.x2 > b.x1 && box.y1 < b.y2 && box.y2 > b.y1)) continue;
      const d = Math.abs(m.x - ax);
      if (d < bestD) { bestD = d; best = m; }
    }
    if (!best) return null;
    const spec = kinds.get(best.kind);
    const applied = [];
    for (const d of dmgs) {
      if (best.hp <= 0) break;
      best.hp = Math.max(0, best.hp - d);
      applied.push(d);
    }
    (best.dm || (best.dm = [])).push(...applied); // 다음 mobs 송신에 타별 피해를 싣는다 (비호스트 피해 숫자)
    best.dir = dir < 0 ? 1 : -1; // 공격자 쪽을 본다
    const z = zones[best.z];
    best.x = Math.min(z.x2, Math.max(z.x1, best.x + (dir < 0 ? -14 : 14)));
    const buffs = [];
    if (best.hp <= 0) {
      best.s = 'die';
      best.dieT = DIE_MS / 1000;
      stats.killed++;
      if (rnd() < spec.buffDrop) for (let i = 0; i < spec.buffDropCount; i++) buffs.push(BUFF_IDS[Math.floor(rnd() * BUFF_IDS.length)]);
    } else {
      best.s = 'hit';
      best.hitT = HIT_MS / 1000;
    }
    return { mob: best, dmgs: applied, killed: best.hp <= 0, buffs };
  }

  /** 송신용 목록 (숫자 반올림). withDamage = 마지막 송신 뒤 들어간 타별 피해 dm을 싣고 비운다 */
  function snapshot(withDamage = false) {
    const list = [];
    for (const m of mobs.values()) {
      const o = { id: m.id, kind: m.kind, x: Math.round(m.x), y: Math.round(m.y), dir: m.dir, hp: Math.round(m.hp), s: m.s, z: m.z };
      if (withDamage && m.dm && m.dm.length) { o.dm = m.dm.slice(-8); m.dm.length = 0; }
      list.push(o);
    }
    return list;
  }

  return {
    fill, load, step, hit, snapshot,
    get size() { return mobs.size; },
    get stats() { return { ...stats, pending: pending.reduce((n, p) => n + p.length, 0) }; },
    clear() { mobs.clear(); for (const p of pending) p.length = 0; },
  };
}

/**
 * 화면 표시용 몬스터 목록 (호스트와 비호스트 공통).
 * apply(list, now, direct): direct = 호스트(시뮬레이션 값을 그대로), 아니면 받은 기록을 220ms 늦게 보간.
 * hp가 줄면 onDamage(view, amount), 처치되면(s die로 바뀜) onDie(view).
 */
export function createMobView({ kinds, onDamage, onDie }) {
  const map = new Map();
  function apply(list, now, direct) {
    const seen = new Set();
    for (const m of list) {
      const spec = kinds.get(m.kind);
      if (!spec) continue;
      seen.add(m.id);
      let v = map.get(m.id);
      if (!v) {
        v = { id: m.id, kind: m.kind, spec, x: m.x, y: m.y, dir: m.dir, hp: m.hp, max: spec.hp, s: m.s, z: m.z, buf: [], animAt: now, hpUntil: 0, hitAt: 0, goneAt: 0 };
        map.set(m.id, v);
      }
      v.goneAt = 0;
      if (m.hp < v.hp) {
        // (사이클 10) 호스트(direct)는 hit 결과로 직접 숫자를 띄운다. 비호스트는 dm(타별 피해)이 있으면 그것, 없으면 차이
        if (!direct) onDamage?.(v, Array.isArray(m.dm) && m.dm.length ? m.dm : [v.hp - m.hp]);
        v.hpUntil = now + 3000; v.hitAt = now;
      }
      v.hp = m.hp;
      v.z = m.z;
      if (m.s !== v.s) { v.s = m.s; v.animAt = now; if (m.s === 'die') { v.hpUntil = now + 600; onDie?.(v); } }
      v.dir = m.dir;
      if (direct) { v.x = m.x; v.y = m.y; v.buf.length = 0; } else {
        const last = v.buf[v.buf.length - 1];
        if (!last || now - last.t > INTERP_MS * 4 || Math.hypot(m.x - v.x, m.y - v.y) > 400) {
          v.buf.length = 0;
          v.buf.push({ t: now - INTERP_MS, x: m.x, y: m.y });
        }
        v.buf.push({ t: now, x: m.x, y: m.y });
        if (v.buf.length > BUF_MAX) v.buf.splice(0, v.buf.length - BUF_MAX);
      }
    }
    for (const [id, v] of map) {
      if (seen.has(id)) continue;
      if (v.s === 'die') { if (!v.goneAt) v.goneAt = now; } else map.delete(id);
    }
  }
  function update(now) {
    for (const [id, v] of map) {
      if (v.goneAt && now - v.goneAt > DIE_MS) { map.delete(id); continue; }
      if (v.buf.length) {
        const t = now - INTERP_MS;
        const b = v.buf;
        if (t <= b[0].t) { v.x = b[0].x; v.y = b[0].y; } else {
          let done = false;
          for (let i = 1; i < b.length; i++) {
            if (t <= b[i].t) {
              const a = b[i - 1];
              const r = (t - a.t) / Math.max(1, b[i].t - a.t);
              v.x = a.x + (b[i].x - a.x) * r;
              v.y = a.y + (b[i].y - a.y) * r;
              done = true;
              break;
            }
          }
          if (!done) { v.x = b[b.length - 1].x; v.y = b[b.length - 1].y; }
        }
      }
    }
  }
  /** 인계용: 가장 최근 받은 값 기준 목록 */
  function latest() {
    return [...map.values()].map((v) => {
      const l = v.buf[v.buf.length - 1];
      return { id: v.id, kind: v.kind, x: l ? l.x : v.x, y: l ? l.y : v.y, dir: v.dir, hp: v.hp, s: v.s, z: v.z };
    });
  }
  return {
    apply, update, latest,
    get list() { return map.values(); },
    get size() { return map.size; },
    box(v) { return { x1: v.x - v.spec.size.w / 2, x2: v.x + v.spec.size.w / 2, y1: v.y - v.spec.size.h, y2: v.y }; },
    clear() { map.clear(); },
  };
}

// ---------------------------------------------------------------------------
// 그리기

/** 종류별 시트 지연 로드 */
export function createMobSprites(kinds) {
  const sheets = new Map(); // kind -> { state: 'loading'|'ready'|'none', img }
  return {
    get(kind) {
      const spec = kinds.get(kind);
      if (!spec || !spec.sheet) return null;
      let e = sheets.get(kind);
      if (!e) {
        e = { state: 'loading', img: null };
        sheets.set(kind, e);
        loadImage(spec.sheet).then((img) => { e.img = img; e.state = img ? 'ready' : 'none'; if (!img) warnOnce(`mob:${kind}`, `몬스터 시트를 불러오지 못했습니다: ${kind} (대체 그림)`); });
      }
      return e.img;
    },
    clear() { sheets.clear(); },
  };
}

/** 몬스터 하나. 장치 px 컨텍스트(단위행렬). x, y = 장치 px 발 위치 */
export function drawMob(ctx, v, img, x, y, k, now, density, alpha = 1) {
  const spec = v.spec;
  const anim = spec.animations[v.s] && spec.animations[v.s].length ? spec.animations[v.s] : spec.animations.move;
  const t = (now - v.animAt) / 1000;
  const left = spec.facingLeft ? v.dir > 0 : v.dir < 0;
  ctx.save();
  ctx.globalAlpha = alpha * (v.s === 'die' ? Math.max(0, 1 - t / (DIE_MS / 1000)) : 1);
  if (img && anim.length) {
    const fw = spec.frame.w || img.naturalHeight;
    const fh = spec.frame.h || img.naturalHeight;
    let i = Math.floor(t * spec.fps);
    i = v.s === 'die' ? Math.min(anim.length - 1, i) : i % anim.length;
    const f = anim[i];
    const s = k / density;
    const axp = spec.anchor.x ?? fw / 2;
    const ayp = spec.anchor.y ?? fh;
    ctx.setTransform(left ? -1 : 1, 0, 0, 1, x, y);
    ctx.drawImage(img, f * fw, 0, fw, fh, -axp * s, -ayp * s, fw * s, fh * s);
  } else {
    ctx.setTransform(left ? -1 : 1, 0, 0, 1, x, y);
    drawMobFallback(ctx, v.kind, spec, k, t, v.s);
  }
  if (v.s === 'hit' && now - v.hitAt < 120) { // 맞은 순간 하얗게 번쩍
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(-spec.size.w / 2 * k, -spec.size.h * k, spec.size.w * k, spec.size.h * k);
  }
  ctx.restore();
}

function ell(ctx, x, y, rx, ry, fill, stroke, lw) {
  ctx.beginPath();
  ctx.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
}
function eyes(ctx, x, y, u, gap = 7) {
  ell(ctx, x, y, 2.4 * u, 3.6 * u, '#1A1626');
  ell(ctx, x + gap * u, y, 2.4 * u, 3.6 * u, '#1A1626');
  ell(ctx, x + 0.8 * u, y - 1.4 * u, 0.9 * u, 0.9 * u, '#fff');
  ell(ctx, x + gap * u + 0.8 * u, y - 1.4 * u, 0.9 * u, 0.9 * u, '#fff');
}

/** 시트가 없을 때의 종류별 절차적 그림 (오른쪽을 본다, 원점 = 발 중앙) */
export function drawMobFallback(ctx, kind, spec, u, t, s) {
  const w = spec.size.w;
  const h = spec.size.h;
  const lw = Math.max(1, 2 * u);
  const sq = s === 'hit' ? 0.12 : Math.sin(t * 8) * 0.04;
  if (spec.behavior === 'hop' && s === 'move') ctx.translate(0, -Math.abs(Math.sin(t * 5)) * 14 * u); // 대체 그림만 통통
  ctx.scale(1 + sq, 1 - sq);
  switch (kind) {
    case 'snail': {
      ell(ctx, 4 * u, -6 * u, w * 0.5 * u, 6 * u, '#9CC890', '#3E6A3A', lw);
      ell(ctx, w * 0.36 * u, -14 * u, 6 * u, 9 * u, '#9CC890', '#3E6A3A', lw);
      ell(ctx, -4 * u, -h * 0.55 * u, w * 0.34 * u, h * 0.4 * u, '#E0A868', '#7A4A20', lw);
      ctx.strokeStyle = '#7A4A20'; ctx.lineWidth = lw;
      ctx.beginPath(); ctx.arc(-4 * u, -h * 0.55 * u, 5 * u, 0, Math.PI * 1.6); ctx.stroke();
      eyes(ctx, w * 0.32 * u, -18 * u, u, 5);
      break;
    }
    case 'mushroom': {
      ell(ctx, 0, -h * 0.28 * u, w * 0.3 * u, h * 0.26 * u, '#FFE3CC', '#A86A3A', lw);
      ell(ctx, 0, -h * 0.66 * u, w * 0.5 * u, h * 0.3 * u, '#F08A2E', '#8A3A10', lw);
      ell(ctx, -8 * u, -h * 0.75 * u, 4 * u, 3 * u, '#FFF2A8');
      ell(ctx, 9 * u, -h * 0.7 * u, 3 * u, 2.4 * u, '#FFF2A8');
      eyes(ctx, -1 * u, -h * 0.3 * u, u, 7);
      break;
    }
    case 'slime': {
      ctx.beginPath();
      ctx.moveTo(-w * 0.5 * u, 0);
      ctx.quadraticCurveTo(-w * 0.55 * u, -h * 1.05 * u, 0, -h * u);
      ctx.quadraticCurveTo(w * 0.55 * u, -h * 1.05 * u, w * 0.5 * u, 0);
      ctx.closePath();
      ctx.fillStyle = 'rgba(126, 214, 180, 0.92)'; ctx.fill();
      ctx.lineWidth = lw; ctx.strokeStyle = '#2E7A66'; ctx.stroke();
      ell(ctx, -w * 0.2 * u, -h * 0.7 * u, 5 * u, 3 * u, 'rgba(255,255,255,0.8)');
      eyes(ctx, 0, -h * 0.45 * u, u, 8);
      break;
    }
    case 'bat': {
      const flap = Math.sin(t * 18) * 0.5;
      ctx.fillStyle = '#5A3A7A'; ctx.strokeStyle = '#2A1440'; ctx.lineWidth = lw;
      for (const sx of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(0, -h * 0.55 * u);
        ctx.quadraticCurveTo(sx * w * 0.35 * u, -h * (0.9 + flap) * u, sx * w * 0.5 * u, -h * (0.5 + flap * 0.6) * u);
        ctx.quadraticCurveTo(sx * w * 0.3 * u, -h * 0.4 * u, 0, -h * 0.4 * u);
        ctx.fill(); ctx.stroke();
      }
      ell(ctx, 0, -h * 0.5 * u, 9 * u, 9 * u, '#7A5A9A', '#2A1440', lw);
      eyes(ctx, -2 * u, -h * 0.55 * u, u, 6);
      break;
    }
    case 'golem': {
      const r = (x, y, ww, hh, f) => { ctx.fillStyle = f; ctx.fillRect(x * u, y * u, ww * u, hh * u); ctx.strokeStyle = '#3A3648'; ctx.lineWidth = lw; ctx.strokeRect(x * u, y * u, ww * u, hh * u); };
      r(-w * 0.3, -h * 0.3, w * 0.22, h * 0.3, '#8E88A0');
      r(w * 0.08, -h * 0.3, w * 0.22, h * 0.3, '#8E88A0');
      r(-w * 0.42, -h * 0.78, w * 0.84, h * 0.5, '#A9A4B8');
      r(-w * 0.28, -h, w * 0.56, h * 0.26, '#C8C4D0');
      ell(ctx, -6 * u, -h * 0.87 * u, 3 * u, 3 * u, '#F7C948');
      ell(ctx, 8 * u, -h * 0.87 * u, 3 * u, 3 * u, '#F7C948');
      break;
    }
    default: {
      let hsh = 0;
      for (const c of kind) hsh = (hsh * 31 + c.charCodeAt(0)) & 0xffff;
      ell(ctx, 0, -h * 0.5 * u, w * 0.5 * u, h * 0.5 * u, `hsl(${hsh % 360}, 60%, 62%)`, `hsl(${hsh % 360}, 50%, 30%)`, lw);
      eyes(ctx, -2 * u, -h * 0.55 * u, u, 8);
    }
  }
}
