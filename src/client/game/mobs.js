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


const REPO_ROOT = new URL('../../../', import.meta.url);
const SRC_RE = /^assets\/[a-z0-9_\-/]+\.(png|webp)$/i;
const KIND_RE = /^[a-z0-9-]{1,32}$/;
export const MOB_STATES = Object.freeze(['move', 'hit', 'die']);
export const MOB_ACTIONS = Object.freeze(['idle','windup','charge','guard','burst']);
export const MOB_LIMITS = Object.freeze({ total: 60, perZone: 20, zones: 32 });
export const RESPAWN_MS = 10000; // 협동 사냥: 재생성 간격 +25% (빈도 약 20% 감소)
export const DIE_MS = 650; // 처치 후 목록에 남는 시간 (die 애니메이션)
export const HIT_MS = 300;
const INTERP_MS = 220;
const BUF_MAX = 6;
const ROLE_BY_KIND=Object.freeze({
 'ore-beetle':'charger','wild-stump':'charger',
 'armored-mushroom':'guard','cave-sentinel':'guard',
 slime:'burst','moss-slime':'burst','frost-slime':'burst',
});
export const monsterRole=kind=>ROLE_BY_KIND[kind]||'contact';
export function monsterDangerBox(v,box){
 if(v?.a!=='burst')return box;
 return {x1:v.x-92,x2:v.x+92,y1:v.y-110,y2:v.y+18};
}
export const monsterTouchDamage=v=>Math.max(0,Math.round((v?.spec?.touchDamage||0)*(v?.a==='charge'?1.5:v?.a==='burst'?1.7:1)));

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
  const revision = typeof raw.revision === 'string' ? raw.revision.slice(0, 64) : '';
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
    const sheet = resolveSrc(m.sheet);
    if (sheet && revision) sheet.searchParams.set('v', revision);
    kinds.set(id, Object.freeze({
      id,
      name: typeof m.name === 'string' ? m.name.slice(0, 20) : id,
      hp: Math.round(clampN(m.hp, 1, 100000, 30)),
      speed: clampN(m.speed, 0, 400, 50),
      touchDamage: Math.round(clampN(m.touchDamage, 0, 100, 5)),
      size: { w: clampN(m.size && m.size.w, 8, 400, ds[0]), h: clampN(m.size && m.size.h, 8, 400, ds[1]) },
      anchor: { x: fin(m.anchor && m.anchor.x) ? m.anchor.x : null, y: fin(m.anchor && m.anchor.y) ? m.anchor.y : null },
      frame,
      sheet,
      animations: anims,
      fps: clampN(m.fps, 1, 30, 8),
      behavior,
      facingLeft: m.facing === 'left',
      pixelArt: m.pixelArt === true,
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
    buffIcons: Object.fromEntries(['range', 'multi', 'element', 'power', 'speed'].map((id) => [id, buffIconSpec(raw, id, density)])),
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

  // Subtract unsafe horizontal intervals; selecting within the remaining space
  // is bounded even when a narrow platform is completely occupied.
  function safePosition(z, spec, preferred = null) {
    const y = z.y - (spec.behavior === 'fly' ? 64 : 0);
    let spans = [[z.x1, z.x2]];
    for (const player of o.getPlayers?.() || []) {
      if (player.dead || !Number.isFinite(player.x) || !Number.isFinite(player.y)) continue;
      if (y <= player.y - 72 || y - spec.size.h >= player.y) continue;
      const gap = Math.max(90, spec.size.w / 2 + 18);
      const lo = player.x - gap, hi = player.x + gap;
      spans = spans.flatMap(([a, b]) => hi <= a || lo >= b ? [[a, b]]
        : [...(lo > a ? [[a, lo]] : []), ...(hi < b ? [[hi, b]] : [])]);
    }
    if (!spans.length) return null;
    if (preferred != null && spans.some(([a, b]) => preferred >= a && preferred <= b)) return preferred;
    const total = spans.reduce((sum, [a, b]) => sum + b - a, 0);
    let offset = rnd() * total;
    for (const [a, b] of spans) { if (offset <= b - a) return a + offset; offset -= b - a; }
    return spans.at(-1)[1];
  }

  function spawn(z, now, near) {
    const choices=z.mobs.filter(kind=>kinds.has(kind));if(!choices.length)return null;
    const kind = choices[Math.floor(rnd() * choices.length)];
    const spec = kinds.get(kind);
    const x = safePosition(z, spec, near);
    if (x == null) return null;
    const m = {
      id: `${rid()}${(seq++).toString(36)}`, kind, z: z.i, x, y: z.y, base: z.y, dir: rnd() < 0.5 ? -1 : 1,
      hp: spec.hp, max: spec.hp, s: 'move', vy: 0, air: false, hitT: 0, dieT: 0, turnT: 2 + rnd() * 4, hopT: 0.4 + rnd(), pauseT: 0,
      phase: rnd() * Math.PI * 2, action:'idle', roleT:0, roleCd:1+rnd()*2,
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
    for (const z of zones.filter(z => !z.event)) while (aliveIn(z.i) + pending[z.i].length < z.max && aliveIn(z.i) < z.max) {
      if (mobs.size >= MOB_LIMITS.total) return;
      if (!spawn(z, now)) pending[z.i].push(now + 1000);
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
      if (aliveIn(z.i) + pending[z.i].length >= z.max) continue;
      if (v.s === 'die' || v.hp <= 0) { if (!z.event) pending[z.i].push(now + RESPAWN_MS); continue; }
      const x = z.event ? Math.min(z.x2, Math.max(z.x1, v.x)) : safePosition(z, spec, Math.min(z.x2, Math.max(z.x1, v.x)));
      if (x == null) { pending[z.i].push(now + 1000); continue; }
      mobs.set(v.id, {
        id: v.id, kind: v.kind, z: z.i, x, y: z.boss || spec.behavior === 'fly' ? v.y : z.y, base: z.y,
        dir: v.dir < 0 ? -1 : 1, hp: Math.min(spec.hp, v.hp), max: z.boss ? (v.max||spec.hp) : spec.hp, s: 'move', vy: 0, air: false, hitT: 0, dieT: 0,
        turnT: 2 + rnd() * 4, hopT: 0.4 + rnd(), pauseT: 0, phase: rnd() * Math.PI * 2,
        action:MOB_ACTIONS.includes(v.a)?v.a:'idle',roleT:Number.isFinite(v.r)?Math.max(0,Math.min(3,v.r/1000)):0,roleCd:1+rnd()*2,
      });
    }
    for (const z of zones.filter(z => !z.event)) {
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
        if (m.dieT <= 0) { mobs.delete(m.id); if (!z.event) pending[z.i].push(now + RESPAWN_MS); }
        continue;
      }
      if (m.hitT > 0) { m.hitT -= dt; m.s = m.hitT > 0 ? 'hit' : 'move'; }
      if (z.event && !z.boss) { m.dir = m.x < (z.x1+z.x2)/2 ? 1 : -1; m.pauseT=0; }
      const role=monsterRole(m.kind),players=[...(o.getPlayers?.()||[])].filter(p=>!p.dead&&Number.isFinite(p.x)&&Number.isFinite(p.y));
      const target=players.sort((a,b)=>Math.abs(a.x-m.x)-Math.abs(b.x-m.x))[0],dx=target?target.x-m.x:Infinity,dy=target?Math.abs(target.y-m.y):Infinity;
      m.roleCd=Math.max(0,m.roleCd-dt);m.roleT=Math.max(0,m.roleT-dt);
      if(m.action==='windup'&&m.roleT<=0){m.action=role==='charger'?'charge':'burst';m.roleT=role==='charger' ? .55 : .28;}
      else if(['charge','burst'].includes(m.action)&&m.roleT<=0){m.action='idle';m.roleCd=role==='charger'?2.4:3.2;}
      else if(role==='charger'&&m.action==='idle'&&m.roleCd<=0&&Math.abs(dx)<420&&dy<150){m.action='windup';m.roleT=.65;m.dir=dx<0?-1:1;}
      else if(role==='burst'&&m.action==='idle'&&m.roleCd<=0&&Math.abs(dx)<145&&dy<130){m.action='windup';m.roleT=.75;m.dir=dx<0?-1:1;}
      else if(role==='guard'&&m.action==='idle'&&Math.abs(dx)<220&&dy<150){m.action='guard';m.roleT=.7;m.dir=dx<0?-1:1;}
      else if(m.action==='guard'&&(m.roleT<=0||Math.abs(dx)>=260||dy>=170)){m.action='idle';m.roleCd=.5;}
      const moving = m.hitT <= 0 && !z.boss&&!['windup','guard','burst'].includes(m.action);
      m.phase += dt;
      if(m.action==='charge')m.x+=m.dir*Math.max(360,spec.speed*4)*dt;
      else if (spec.behavior === 'fly') {
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
      if (!z.event && m.turnT <= 0) {
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
          if (aliveIn(z.i) >= z.max) { p.splice(i, 1); continue; }
          if (mobs.size < MOB_LIMITS.total && spawn(z, now)) p.splice(i, 1);
          else p[i] = now + 1000;
        }
      }
    }
  }

  /**
   * 공격 판정 상자에 맞은 몬스터 하나(공격자에 가장 가까운 것)에 타별 피해를 차례로. 처치되면 남은 타는 버리고 버프 드롭을 굴린다.
   * @param dmgs 타별 피해 [n..] (multi 버프면 여러 개)
   * @returns null | { mob, dmgs(실제로 들어간 타), killed, buffs(드롭할 버프 id 목록) }
   */
  function hit(box, ax, dir, dmgs, excluded = new Set(), modify = (_,d)=>d) {
    let best = null;
    let bestD = Infinity;
    for (const m of mobs.values()) {
      if (m.s === 'die' || excluded.has(m.id)) continue;
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
      let value=modify(best,d);const attackerSide=ax<best.x?-1:1;if(best.action==='guard'&&attackerSide===best.dir)value=Math.max(1,Math.round(value*.3));
      const actual=Math.min(best.hp,value);best.hp-=actual;
      applied.push(actual);
    }
    (best.dm || (best.dm = [])).push(...applied); // 다음 mobs 송신에 타별 피해를 싣는다 (비호스트 피해 숫자)
    best.dir = dir < 0 ? 1 : -1; // 공격자 쪽을 본다
    const z = zones[best.z];
    best.x = Math.min(z.x2, Math.max(z.x1, best.x + (z.boss?0:(dir < 0 ? -14 : 14))));
    const buffs = [];
    if (best.hp <= 0) {
      best.s = 'die';
      best.dieT = DIE_MS / 1000;
      stats.killed++;
      // 드롭 하나마다 25% heal, 나머지 버프 5종 균등 (사이클 10 변경)
      if (rnd() < .25) buffs.push('heal'); // only automatic health recovery; no attack upgrades
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
      const o = { id: m.id, kind: m.kind, x: Math.round(m.x), y: Math.round(m.y), dir: m.dir, hp: Math.round(m.hp), s: m.s, z: m.z,...(m.action!=='idle'?{a:m.action,r:Math.round(m.roleT*1000)}:{}), ...(zones[m.z]?.boss?{max:m.max}:{}) };
      if (withDamage && m.dm && m.dm.length) { o.dm = m.dm.slice(-12); m.dm.length = 0; }
      list.push(o);
    }
    return list;
  }

  return {
    fill, load, step, hit, snapshot,
    spawnGarden(count, now, wave=1) {
      const z=zones.find(z=>z.event&&!z.boss);if(!z)return 0;
      let n=0;const free=Math.max(0,12-this.gardenMobs().length);for(let i=0;i<Math.min(count,free) && mobs.size<MOB_LIMITS.total;i++) {
        const side=i%2 ? 1 : -1, center=(z.x1+z.x2)/2;
        const lane={...z,mobs:!z.mobs.includes('mushroom')?z.mobs:wave>=2?(i%3===0?['garden-runner','slime']:i%3===1?['garden-guard','mushroom']:z.mobs):z.mobs.filter(k=>k!=='garden-guard'),x1:center+side*540-85,x2:center+side*540+85};
        if(spawn(lane,now))n++;
      }return n;
    },
    spawnBoss(max,now){const z=zones.find(z=>z.boss);if(!z)return false;const m=spawn(z,now,(z.x1+z.x2)/2);if(!m)return false;if(m.x!==(z.x1+z.x2)/2){mobs.delete(m.id);return false;}m.hp=m.max=max;return true;},
    moveBoss(x,y,dir=1){const m=[...mobs.values()].find(m=>zones[m.z]?.boss&&m.s!=='die');if(m){const z=zones[m.z];m.x=Math.min(z.x2,Math.max(z.x1,x));m.y=y;m.dir=dir;}},
    bossMob(){return [...mobs.values()].find(m=>zones[m.z]?.boss&&m.s!=='die');},
    gardenMobs() { return [...mobs.values()].filter(m=>zones[m.z]?.event && !zones[m.z]?.boss && m.s!=='die'); },
    removeGarden(ids=null) { const selected=ids && new Set(ids);for(const [id,m] of mobs)if(zones[m.z]?.event && (!selected || selected.has(id)))mobs.delete(id); },
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
        v = { id: m.id, kind: m.kind, spec, x: m.x, y: m.y, dir: m.dir, hp: m.hp, max: m.max||spec.hp, s: m.s, a:MOB_ACTIONS.includes(m.a)?m.a:'idle',r:m.r||0,z: m.z, buf: [], animAt: now, hpUntil: 0, hitAt: 0, goneAt: 0 };
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
      v.a=MOB_ACTIONS.includes(m.a)?m.a:'idle';v.r=Number.isFinite(m.r)?m.r:0;
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
      return { id: v.id, kind: v.kind, x: l ? l.x : v.x, y: l ? l.y : v.y, dir: v.dir, hp: v.hp, s: v.s, z: v.z,...(v.a!=='idle'?{a:v.a,r:v.r}:{}), ...(v.kind==='garden-king'?{max:v.max}:{}) };
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
    // Pixel sheets keep their small clusters crisp at every display scale.
    // save/restore confines this to the monster; avatar and map retain their own filtering.
    if (spec.pixelArt) ctx.imageSmoothingEnabled = false;
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
  if(v.a==='windup'){
    const pulse=.55+.35*Math.sin(now/70);ctx.globalAlpha=pulse;ctx.strokeStyle='#ffd36b';ctx.lineWidth=Math.max(2,3*k);ctx.beginPath();ctx.arc(0,-spec.size.h*k*.55,(spec.size.w*.65+8)*k,0,Math.PI*2);ctx.stroke();
  }else if(v.a==='charge'){
    ctx.globalAlpha=.65;ctx.fillStyle='#f28b5b';ctx.fillRect(-spec.size.w*k*.95,-spec.size.h*k*.48,spec.size.w*k*.65,7*k);
  }else if(v.a==='guard'){
    ctx.globalAlpha=.72;ctx.strokeStyle='#9ee8ef';ctx.lineWidth=Math.max(2,4*k);ctx.beginPath();ctx.arc(spec.size.w*k*.42,-spec.size.h*k*.48,spec.size.h*k*.38,-Math.PI/2,Math.PI/2);ctx.stroke();
  }else if(v.a==='burst'){
    const pulse=.45+.3*Math.sin(now/45);ctx.globalAlpha=pulse;ctx.strokeStyle='#ff705c';ctx.lineWidth=Math.max(3,6*k);ctx.beginPath();ctx.arc(0,-spec.size.h*k*.35,92*k,0,Math.PI*2);ctx.stroke();
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
  if(spec.biome==='frost'){kind=({'frost-slime':'moss-slime','ice-crab':'ore-beetle','ice-golem':'cave-sentinel','frost-beetle':'ore-beetle','glacier-sentinel':'cave-sentinel'})[kind]||kind;}
  const w = spec.size.w;
  const h = spec.size.h;
  const lw = Math.max(1, 2 * u);
  const sq = s === 'hit' ? 0.12 : Math.sin(t * 8) * 0.04;
  if (spec.behavior === 'hop' && s === 'move') ctx.translate(0, -Math.abs(Math.sin(t * 5)) * 14 * u); // 대체 그림만 통통
  ctx.scale(1 + sq, 1 - sq);
  if(['wild-stump','armored-mushroom','ore-beetle','cave-sentinel','thorn-mantis','ancient-treant'].includes(kind)){
   const r=(color,x,y,ww,hh)=>{ctx.fillStyle=color;ctx.fillRect(x*u,y*u,ww*u,hh*u);},wood=kind.includes('stump')||kind.includes('treant'),stone=kind==='cave-sentinel',beetle=kind==='ore-beetle',mantis=kind==='thorn-mantis';
   const stride=s==='move'?Math.sin(t*(beetle?18:9)):Math.sin(t*2)*.18,pulse=.5+Math.sin(t*(stone?3:2))*.5;
   const icy=spec.biome==='frost';
   const base=icy?'#83b7d0':wood?'#876148':stone?'#747d9c':beetle?'#568fa0':mantis?'#759957':'#a87755',light=icy?'#e1faff':wood?'#b38d63':stone?'#a4b1cb':beetle?'#a0d7de':mantis?'#aacc77':'#d9b06b';
   r('#2d4144',-w*.43,-h*.82,w*.86,h*.77);r(base,-w*.4,-h*.84,w*.8,h*.77);r(light,-w*.36,-h*.8,w*.17,h*.65);r('#243b4533',w*.22,-h*.7,w*.17,h*.57);
   for(const d of [-1,1]){const lift=Math.max(0,stride*d)*(beetle?3:6);r(base,d<0?-w*.43:w*.18,-h*.12-lift,w*.25,h*.12);r('#384749',d<0?-w*.43:w*.18,-h*.04-lift,w*.27,h*.06);}
   if(wood){for(let n=0;n<4;n++)r('#553f32',-w*.25+n*w*.17,-h*.64+(n%2)*8,3,h*.45);r('#d0b287',-w*.38,-h*.85,w*.76,8);for(const d of [-1,1])r(base,d<0?-w*.58:w*.39,-h*.62,w*.2,h*.3);if(kind==='ancient-treant'){r('#497354',-w*.55+Math.sin(t*1.7)*2,-h,w*1.1,h*.22);r('#85a975',-w*.4+Math.sin(t*1.7)*3,-h*1.05,w*.8,h*.11);r('#c8cf8c',-7,-h*.68,14,17);}}
   else if(stone){r('#525f7b',-w*.58,-h*.7,w*.22,h*.4);r('#525f7b',w*.36,-h*.7,w*.22,h*.4);r('#c2a7dd',-8,-h*.65,16,19);r('#e2daee',-3,-h*.6,6,9);ctx.save();ctx.globalAlpha=.15+pulse*.3;r('#d0b1ef',-13,-h*.67,26,26);ctx.restore();for(let n=0;n<3;n++)r('#b0bdd3',-w*.3+n*w*.25,-h-6,12,16);}
   else if(beetle){for(const d of [-1,1])for(let n=0;n<3;n++)r('#385d72',d<0?-w*.61:w*.38,-h*.45+n*8+Math.sin(t*18+n*2+d)*3,w*.23,4);r('#a6d7df',-w*.27,-h*.9,w*.54,8);r('#36576e',-2,-h*.8,4,h*.5);for(const d of [-1,1])r(light,d*14-3,-h-8,6,16);}
   else if(mantis){for(const d of [-1,1]){r('#577a46',d<0?-w*.65:w*.4,-h*.68+stride*d*5,w*.23,h*.38);r('#d8dfad',d<0?-w*.65:w*.5,-h*.42+stride*d*5,w*.13,h*.28);r('#5c7847',d*13-2,-h-12,4,17);}r(light,-w*.3,-h,w*.6,h*.22);}
   else{r('#6b6b60',-w*.5,-h*.91,w,h*.3);r('#b7b4a0',-w*.49,-h*.94,w*.98,7);for(let n=0;n<3;n++)r('#e5c67b',-w*.32+n*w*.3,-h*.88,7,7);r('#8d7759',-w*.32,-h*.6,w*.64,4);}
   r('#20343a',-12,-h*.48,6,7);r('#20343a',6,-h*.48,6,7);r('#e8f0c4',-11,-h*.48,2,3);r('#e8f0c4',7,-h*.48,2,3);return;
  }
  if(kind==='moss-slime'||kind==='moss-guardian') {
    const r=(color,x,y,ww,hh)=>{ctx.fillStyle=color;ctx.fillRect(x*u,y*u,ww*u,hh*u);};
    r('#2c4d43',-w/2,-h+5,w,h-5);r(spec.biome==='frost'?'#98cbdc':'#699768',-w/2+3,-h+2,w-6,h-5);r(spec.biome==='frost'?'#ddf7ff':'#a5bf7c',-w/2+3,-h+2,w-6,7);r(spec.biome==='frost'?'#6493b8':'#416c58',w/2-9,-h+9,6,h-14);
    for(let n=0;n<5;n++)r(n%2?'#90b66b':'#456c50',-w/2+6+n*(w-14)/5,-h+14+(n%3)*9,7,5);
    r('#1d3637',-10,-h*.55,5,7);r('#1d3637',5,-h*.55,5,7);r('#d6f5b4',-9,-h*.55,2,3);r('#d6f5b4',6,-h*.55,2,3);
    if(kind==='moss-guardian'){r('#52735e',-w/2-8,-h*.68,10,h*.4);r('#52735e',w/2-2,-h*.68,10,h*.4);r('#c4db83',-6,-h-10,12,12);r('#e9f3b4',-3,-h-7,5,6);}
    else{r(spec.biome==='frost'?'#7baed1':'#5a925f',-5,-h-9,4,10);r(spec.biome==='frost'?'#e2faff':'#b9cf79',-1,-h-10,10,5);}return;
  }
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
