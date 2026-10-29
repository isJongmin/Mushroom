import { normalizeMapId } from './areas.js';
// 캐릭터 물리 (ARCHITECTURE 복셀 아트 계약 사이클 6 조작 + 사이클 8 계약). 월드 단위, 순수 함수 — Node 단위 시험 가능.
//   중력 2000/s², 점프 초속 650 → 최고 높이 105.6, 체공 0.65초. 공중 좌우 이동 허용.
//   (사이클 8) 발판: 맵 manifest platforms [{ id, x1, x2, y }] (y = 윗면 = 서는 높이). 한 방향 통과 —
//     위에서 떨어지며 윗면을 지나는 순간(이전 발 y <= 발판 y < 현재 발 y, x가 [x1, x2] 안)에만 착지. 아래에서 오르면 통과.
//     발판 끝을 지나 걸어 나가면 떨어진다. 지면(y=440, x 전체)은 암묵적 바닥.
//   엎드리기(prone): 지면/발판에서 ↓를 누르는 동안. 엎드린 동안 좌우 이동·점프 불가. 공중에서 누르면 착지 후 엎드린다.
//   ↓ + 점프: 발판 위면 그 발판을 0.25초 무시하고 떨어진다. 지면에서는 아무것도 하지 않는다(점프도 안 함).
//   슈퍼 점프: 같은 방향키(←, →, ↑) 300ms 안 두 번(input.js). ←/→ 대시 = 수평 1100 x 0.22초(그 동안 중력 절반) + 위로 350,
//     ↑ = 위로 950(최고 약 225). 쿨다운 0.8초. 공중에서는 1회(착지하면 다시 충전).
//     지면/발판에서 쓰거나, 더블탭의 첫 누름으로 막 뛰어오른 경우(↑↑)는 공중 충전을 쓰지 않는다.
// 상태 s: 'idle' | 'walk' | 'jump'(vy<0) | 'fall'(vy>=0, 공중) | 'prone'. 수신은 옛 'crouch'도 'prone'으로 받는다.

export const PHYS = Object.freeze({
  gravity: 2000,
  jumpV: 650,
  groundY: 440,
  jumpBufferMs: 150,
  dashVX: 1100,
  dashTime: 0.22,
  dashUpV: 350,
  dashGravity: 0.5, // 대시 중 중력 배율
  superUpV: 950,
  superCooldown: 0.8,
  dropIgnore: 0.25,
  doubleTapMs: 300,
  ceilY: 0, // 발이 이보다 위로는 못 간다 (맵 위 끝)
});
// (사이클 9) 'attack'(공격 중), 'ghost'(사망 후 유령)를 더한다.
// (사이클 10) 'climb'(로프에 매달림)
export const MOVE_STATES = Object.freeze(['idle', 'walk', 'jump', 'fall', 'prone', 'attack', 'ghost', 'climb']);
// (사이클 10) 로프 (ARCHITECTURE 사이클 10 "로프"): 가로 ±12 안에서 ↑로 잡음(위끝 발판에서는 ↓로 잡고 내려감).
// 매달린 동안 중력 없음, ↑/↓ 초속 160, ←/→ 무시. 점프(새로 누름) + ←/→ = 옆으로 뛰어내림(위로 650 x 0.6).
// 위끝에 닿으면 그 높이 발판에 올라섬, 아래끝에 닿으면 바로 아래 면(24 이내)에 내려서거나 떨어짐. 놓은 뒤 0.3초는 다시 잡지 않음.
export const ROPE = Object.freeze({ grab: 12, speed: 160, jumpOffV: 650 * 0.6, topSnap: 16, bottomSnap: 24, regrab: 0.3, below: 20 });
export const KNOCK = Object.freeze({ vx: 300, vy: 250, t: 0.3 }); // (사이클 9) 넉백
export const MAX_WORLD_Y = 5000; // 수신 y 상한 (화면이 맵 groundY로 다시 자른다)
const STATE_SET = new Set(MOVE_STATES);
export const isMoveState = (s) => typeof s === 'string' && STATE_SET.has(s);
/** 수신 상태 정리: 옛 'crouch' → 'prone', 목록 밖 → null */
export const normState = (s) => (s === 'crouch' ? 'prone' : isMoveState(s) ? s : null);
export const FX_KINDS = Object.freeze(['dash-left', 'dash-right', 'dash-up']);
const FX_SET = new Set(FX_KINDS);
export const isFx = (v) => typeof v === 'string' && FX_SET.has(v);

/** 최고 높이 (월드) */
export const JUMP_APEX = (PHYS.jumpV * PHYS.jumpV) / (2 * PHYS.gravity);
export const SUPER_APEX = (PHYS.superUpV * PHYS.superUpV) / (2 * PHYS.gravity);

/**
 * manifest platforms 정리: [{ id, x1, x2, y }] (x1 < x2, 0 < y < 지면). 형식이 틀린 항목은 버린다. 최대 64개.
 * 반환은 y 오름차순(높은 발판 먼저) 고정 배열. 없거나 깨졌으면 [] (지면만).
 */
export function normalizePlatforms(raw, { width = 2400, groundY = PHYS.groundY } = {}) {
  if (!Array.isArray(raw)) return Object.freeze([]);
  const out = [];
  const fin = (v) => typeof v === 'number' && Number.isFinite(v);
  for (const p of raw.slice(0, 64)) {
    if (!p || typeof p !== 'object' || !fin(p.x1) || !fin(p.x2) || !fin(p.y)) continue;
    const x1 = Math.max(0, Math.min(p.x1, p.x2));
    const x2 = Math.min(width, Math.max(p.x1, p.x2));
    if (x2 - x1 < 1 || p.y <= 0 || p.y >= groundY) continue;
    const id = typeof p.id === 'string' && p.id.length <= 32 ? p.id : `p${out.length}`;
    out.push(Object.freeze({ id, x1, x2, y: p.y }));
  }
  out.sort((a, b) => a.y - b.y);
  return Object.freeze(out);
}

/** (x, y)에서 아래로 처음 만나는 면의 y (발판 윗면 또는 지면). 그림자 위치용. */
export function surfaceBelow(platforms, x, y, groundY = PHYS.groundY) {
  let best = groundY;
  for (const p of platforms) {
    if (p.y >= y - 0.5 && p.y < best && x >= p.x1 && x <= p.x2) best = p.y;
  }
  return best;
}

/** (사이클 10) manifest ropes 정리: [{ id, x, y1, y2 }] (y1 위끝 < y2 아래끝, 0~groundY). 최대 32개 */
export function normalizeRopes(raw, { width = 2400, groundY = PHYS.groundY } = {}) {
  if (!Array.isArray(raw)) return Object.freeze([]);
  const out = [];
  const fin = (v) => typeof v === 'number' && Number.isFinite(v);
  for (const r of raw.slice(0, 32)) {
    if (!r || typeof r !== 'object' || !fin(r.x) || !fin(r.y1) || !fin(r.y2)) continue;
    const y1 = Math.max(0, Math.min(r.y1, r.y2));
    const y2 = Math.min(groundY, Math.max(r.y1, r.y2));
    if (y2 - y1 < 8 || r.x < 0 || r.x > width) continue;
    out.push(Object.freeze({ id: typeof r.id === 'string' && r.id.length <= 32 ? r.id : `r${out.length}`, x: r.x, y1, y2 }));
  }
  return Object.freeze(out);
}

/** 몸 상태 초기값 */
export function createBody(x, y = PHYS.groundY, groundY = PHYS.groundY) {
  return {
    x, y, vy: 0, grounded: y >= groundY,
    kbT: 0, kbDir: 0, // (사이클 9) 넉백 남은 시간, 방향
    rope: null, climbV: 0, ropeOffT: 0, toppedOut: false, // (사이클 10) 매달린 로프, 오르내림 방향(-1/0/1), 다시 잡기 금지 남은 시간 on: null, prone: false, s: 'idle',
    t: 0, // 몸 시계 (초)
    airT: 0, // 마지막으로 땅/발판을 떠난 뒤 지난 시간
    airCharge: true, // 공중 슈퍼 점프 1회
    cool: 0, // 슈퍼 점프 쿨다운 남은 시간
    dashT: 0, dashDir: 0, // 대시 남은 시간, 방향
    ignore: null, ignoreUntil: 0, // 내려가기로 무시 중인 발판 id
  };
}

function land(b, y, plat, prone) {
  b.y = y;
  b.vy = 0;
  b.grounded = true;
  b.on = plat;
  b.airT = 0;
  b.airCharge = true;
  b.dashT = 0;
  b.kbT = 0;
  b.prone = !!prone; // 착지 순간 ↓를 누르고 있으면 바로 엎드림
}

function leaveGround(b) {
  b.grounded = false;
  b.on = null;
  b.prone = false;
  b.airT = 0;
}

/** 이번 구간에서 위에서 아래로 윗면을 지난 발판 중 가장 먼저(가장 높은) 것. 없으면 null */
function crossed(platforms, b, yTop, yEnd) {
  for (const p of platforms) { // y 오름차순 → 처음 맞는 것이 가장 높다
    if (p.y < yTop - 1e-9) continue;
    if (p.y >= yEnd) break;
    if (b.x < p.x1 || b.x > p.x2) continue;
    if (b.ignore === p.id && b.t < b.ignoreUntil) continue;
    return p;
  }
  return null;
}

/**
 * 한 프레임 진행. 등가속 운동을 구간별로 정확히 적분하므로 dt가 달라도 같은 궤적이다(대시 끝 경계에서 나눈다).
 * @param b 몸 (제자리 수정)
 * @param inp { dir: -1|0|1, jump: boolean, prone: boolean(누르는 중), superKind?: 'left'|'right'|'up'|null, superAge?: 초(더블탭 첫 누름부터) }
 * @param opt { speed, minX, maxX, platforms }
 * @returns { jumped(점프 입력을 썼음: 점프, 내려가기, 지면 ↓+점프 무동작 포함), dropped, landed, fx: 'dash-left'|'dash-right'|'dash-up'|null }
 */
export function stepBody(b, inp, dt, opt) {
  const g = PHYS.gravity;
  const groundY = typeof opt.groundY === 'number' ? opt.groundY : PHYS.groundY;
  const plats = opt.platforms || [];
  const clampX = (x) => Math.min(opt.maxX, Math.max(opt.minX, x));
  const out = { jumped: false, dropped: false, landed: false, fx: null };
  b.t += dt;
  if (b.cool > 0) b.cool = Math.max(0, b.cool - dt);
  if (b.ignore && b.t >= b.ignoreUntil) b.ignore = null;
  if (b.ropeOffT > 0) b.ropeOffT = Math.max(0, b.ropeOffT - dt);

  // 0) (사이클 10) 로프
  const ropes = opt.ropes || [];
  if (!b.rope && ropes.length && b.ropeOffT <= 0 && b.dashT <= 0 && b.kbT <= 0) {
    for (const r of ropes) {
      if (Math.abs(b.x - r.x) > ROPE.grab) continue;
      // ↑: 로프 구간(아래끝 아래 20까지, 위끝 위는 제외)에서 잡음. ↓: 위끝 높이 발판에 서 있으면 잡고 내려감
      const upGrab = inp.up && b.y > r.y1 + 1 && b.y <= r.y2 + ROPE.below;
      const downGrab = inp.down && b.grounded && Math.abs(b.y - r.y1) <= ROPE.topSnap;
      if (!upGrab && !downGrab) continue;
      b.rope = r;
      b.grounded = false;
      b.on = null;
      b.prone = false;
      b.vy = 0;
      b.x = r.x;
      b.y = downGrab ? r.y1 + 2 : Math.min(b.y, r.y2);
      out.grabbed = true;
      out.jumped = !!inp.jump; // 잡는 데 쓴 ↑(점프 입력)는 소비
      break;
    }
  }
  if (b.rope) {
    const r = b.rope;
    const dir = inp.dir | 0;
    if (inp.jumpTap && dir !== 0) { // 옆으로 뛰어내림
      b.rope = null;
      b.climbV = 0;
      b.ropeOffT = ROPE.regrab;
      b.vy = -ROPE.jumpOffV;
      b.airT = 0;
      b.x = clampX(b.x + dir * 2);
      out.jumped = true;
      out.unclimbed = 'jump';
    } else {
      if (inp.jump) out.jumped = true; // 매달린 동안 점프 입력은 소비만
      const v = (inp.up ? -1 : 0) + (inp.down ? 1 : 0);
      b.climbV = v;
      b.y += v * ROPE.speed * dt;
      b.x = r.x;
      if (b.y <= r.y1) { // 위끝: 그 높이 발판에 올라선다 (없으면 위끝에 매달린 채)
        const p = plats.find((q) => Math.abs(q.y - r.y1) <= ROPE.topSnap && r.x >= q.x1 && r.x <= q.x2);
        if (p) { b.rope = null; b.climbV = 0; b.ropeOffT = ROPE.regrab; land(b, p.y, p, false); out.landed = true; out.unclimbed = 'top'; } else b.y = r.y1;
      } else if (b.y >= r.y2) { // 아래끝: 바로 아래 면에 내려서거나 놓고 떨어진다
        const below = surfaceBelow(plats, r.x, r.y2, groundY);
        b.rope = null;
        b.climbV = 0;
        b.ropeOffT = ROPE.regrab;
        out.unclimbed = 'bottom';
        if (below - r.y2 <= ROPE.bottomSnap) {
          land(b, below, below === groundY ? null : plats.find((q) => q.y === below && r.x >= q.x1 && r.x <= q.x2) || null, false);
          out.landed = true;
        } else { b.y = r.y2; b.grounded = false; b.vy = 0; b.airT = 0; }
      }
      if (b.rope) { b.s = 'climb'; return out; }
      b.s = stateOf(b, 0);
      return out;
    }
  }

  // 1) 땅 위 동작: 엎드리기, 점프, 내려가기
  if (b.grounded) {
    b.prone = !!inp.prone;
    if (inp.jump) {
      out.jumped = true;
      if (b.prone) {
        if (b.on) { // ↓ + 점프 = 이 발판을 0.25초 무시하고 떨어진다
          b.ignore = b.on.id;
          b.ignoreUntil = b.t + PHYS.dropIgnore;
          leaveGround(b);
          b.vy = 0;
          out.dropped = true;
        } // 지면: 아무것도 하지 않는다
      } else {
        leaveGround(b);
        b.vy = -PHYS.jumpV;
      }
    }
  }

  // 2) 슈퍼 점프
  const sk = inp.superKind;
  if (sk && !b.prone && b.cool <= 0) {
    const age = typeof inp.superAge === 'number' ? inp.superAge : 0;
    const fromGround = b.grounded || b.airT <= age + 0.05; // ↑↑: 첫 누름으로 막 뜬 경우는 땅에서 쓴 것으로
    if (fromGround || b.airCharge) {
      if (!fromGround) b.airCharge = false;
      if (b.grounded) leaveGround(b);
      if (sk === 'up') {
        b.vy = -PHYS.superUpV;
        b.dashT = 0;
      } else {
        b.dashDir = sk === 'left' ? -1 : 1;
        b.dashT = PHYS.dashTime;
        b.vy = -PHYS.dashUpV;
      }
      b.cool = PHYS.superCooldown;
      out.fx = `dash-${sk}`;
    }
  }

  // 3) 이동
  const walkDir = b.prone ? 0 : (inp.dir | 0);
  if (b.grounded) {
    if (walkDir !== 0) b.x = clampX(b.x + walkDir * opt.speed * dt);
    if (b.on && (b.x < b.on.x1 || b.x > b.on.x2)) { // 발판 끝을 지나 걸어 나감 → 떨어진다
      leaveGround(b);
      b.vy = 0;
    }
  } else {
    let rem = dt;
    let guard = 0;
    while (rem > 1e-9 && guard++ < 4) {
      const dashing = b.dashT > 0;
      const h = dashing ? Math.min(rem, b.dashT) : rem;
      const gg = dashing ? g * PHYS.dashGravity : g;
      const vx = dashing ? b.dashDir * PHYS.dashVX : (b.kbT > 0 ? b.kbDir * KNOCK.vx : walkDir * opt.speed);
      if (vx !== 0) b.x = clampX(b.x + vx * h);
      const y0 = b.y;
      const v0 = b.vy;
      b.y = y0 + v0 * h + 0.5 * gg * h * h;
      b.vy = v0 + gg * h;
      b.airT += h;
      if (dashing) { b.dashT -= h; if (b.dashT < 1e-9) b.dashT = 0; }
      if (b.kbT > 0) b.kbT = Math.max(0, b.kbT - h);
      rem -= h;
      if (b.y < PHYS.ceilY) { b.y = PHYS.ceilY; if (b.vy < 0) b.vy = 0; }
      if (b.vy >= 0) { // 내려오는 중: 이 구간의 가장 높은 점(꼭대기를 지났으면 꼭대기)부터 끝까지 지난 윗면
        const yTop = v0 < 0 ? y0 - (v0 * v0) / (2 * gg) : y0;
        const p = crossed(plats, b, Math.max(PHYS.ceilY, yTop), b.y);
        if (p) { land(b, p.y, p, inp.prone); out.landed = true; break; }
        if (b.y >= groundY) { land(b, groundY, null, inp.prone); out.landed = true; break; }
      }
    }
  }
  b.s = stateOf(b, walkDir);
  return out;
}

/** (사이클 9) 넉백: dir 방향으로 수평 300(0.3초), 위로 250. 땅/발판에서 떠오른다. 대시는 끝난다. */
export function knockBody(b, dir) {
  if (b.grounded) leaveGround(b);
  b.vy = -KNOCK.vy;
  b.kbDir = dir < 0 ? -1 : 1;
  b.kbT = KNOCK.t;
  b.dashT = 0;
}

export function stateOf(b, dir) {
  if (b.rope) return 'climb';
  if (!b.grounded) return b.vy < 0 ? 'jump' : 'fall';
  if (b.prone) return 'prone';
  return dir !== 0 ? 'walk' : 'idle';
}

/** move payload 정리 (수신 측). 깨진 값이면 null. y는 [맵 위 끝, 지면]으로 자른다. s가 없으면 null(추정은 화면이). */
export function cleanMove(p) {
  if (!p || typeof p !== 'object') return null;
  if (typeof p.user_id !== 'string' || !p.user_id || p.user_id.length > 64) return null;
  if (typeof p.x !== 'number' || !Number.isFinite(p.x)) return null;
  const y = typeof p.y === 'number' && Number.isFinite(p.y)
    ? Math.min(MAX_WORLD_Y, Math.max(PHYS.ceilY, p.y)) : null;
  const dir = p.dir === 'left' || p.dir === -1 ? 'left' : (p.dir === 'right' || p.dir === 1 ? 'right' : null);
  const out = { user_id: p.user_id, mapId: normalizeMapId(p.mapId), x: p.x, y, dir, s: normState(p.s) };
  if (isFx(p.fx)) out.fx = p.fx;
  return out;
}
