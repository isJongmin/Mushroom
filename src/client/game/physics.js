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
export const MOVE_STATES = Object.freeze(['idle', 'walk', 'jump', 'fall', 'prone']);
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
export function normalizePlatforms(raw, { width = 2400 } = {}) {
  if (!Array.isArray(raw)) return Object.freeze([]);
  const out = [];
  const fin = (v) => typeof v === 'number' && Number.isFinite(v);
  for (const p of raw.slice(0, 64)) {
    if (!p || typeof p !== 'object' || !fin(p.x1) || !fin(p.x2) || !fin(p.y)) continue;
    const x1 = Math.max(0, Math.min(p.x1, p.x2));
    const x2 = Math.min(width, Math.max(p.x1, p.x2));
    if (x2 - x1 < 1 || p.y <= 0 || p.y >= PHYS.groundY) continue;
    const id = typeof p.id === 'string' && p.id.length <= 32 ? p.id : `p${out.length}`;
    out.push(Object.freeze({ id, x1, x2, y: p.y }));
  }
  out.sort((a, b) => a.y - b.y);
  return Object.freeze(out);
}

/** (x, y)에서 아래로 처음 만나는 면의 y (발판 윗면 또는 지면). 그림자 위치용. */
export function surfaceBelow(platforms, x, y) {
  let best = PHYS.groundY;
  for (const p of platforms) {
    if (p.y >= y - 0.5 && p.y < best && x >= p.x1 && x <= p.x2) best = p.y;
  }
  return best;
}

/** 몸 상태 초기값 */
export function createBody(x, y = PHYS.groundY) {
  return {
    x, y, vy: 0, grounded: y >= PHYS.groundY, on: null, prone: false, s: 'idle',
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
  const plats = opt.platforms || [];
  const clampX = (x) => Math.min(opt.maxX, Math.max(opt.minX, x));
  const out = { jumped: false, dropped: false, landed: false, fx: null };
  b.t += dt;
  if (b.cool > 0) b.cool = Math.max(0, b.cool - dt);
  if (b.ignore && b.t >= b.ignoreUntil) b.ignore = null;

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
      const vx = dashing ? b.dashDir * PHYS.dashVX : walkDir * opt.speed;
      if (vx !== 0) b.x = clampX(b.x + vx * h);
      const y0 = b.y;
      const v0 = b.vy;
      b.y = y0 + v0 * h + 0.5 * gg * h * h;
      b.vy = v0 + gg * h;
      b.airT += h;
      if (dashing) { b.dashT -= h; if (b.dashT < 1e-9) b.dashT = 0; }
      rem -= h;
      if (b.y < PHYS.ceilY) { b.y = PHYS.ceilY; if (b.vy < 0) b.vy = 0; }
      if (b.vy >= 0) { // 내려오는 중: 이 구간의 가장 높은 점(꼭대기를 지났으면 꼭대기)부터 끝까지 지난 윗면
        const yTop = v0 < 0 ? y0 - (v0 * v0) / (2 * gg) : y0;
        const p = crossed(plats, b, Math.max(PHYS.ceilY, yTop), b.y);
        if (p) { land(b, p.y, p, inp.prone); out.landed = true; break; }
        if (b.y >= PHYS.groundY) { land(b, PHYS.groundY, null, inp.prone); out.landed = true; break; }
      }
    }
  }
  b.s = stateOf(b, walkDir);
  return out;
}

export function stateOf(b, dir) {
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
    ? Math.min(PHYS.groundY, Math.max(PHYS.ceilY, p.y)) : PHYS.groundY;
  const dir = p.dir === 'left' || p.dir === -1 ? 'left' : (p.dir === 'right' || p.dir === 1 ? 'right' : null);
  const out = { user_id: p.user_id, x: p.x, y, dir, s: normState(p.s) };
  if (isFx(p.fx)) out.fx = p.fx;
  return out;
}
