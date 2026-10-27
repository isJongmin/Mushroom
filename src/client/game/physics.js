// 점프·숙이기 물리 (ARCHITECTURE 복셀 아트 계약 (사이클 6) 조작). 월드 단위, 순수 함수 — Node 단위 시험 가능.
//   중력 2000/s², 점프 초속 650 → 최고 높이 650² / (2 x 2000) = 105.6, 체공 0.65초. 공중 좌우 이동 허용.
//   숙이기: 지면에서 ↓/S를 누르는 동안. 숙인 동안 이동·점프 불가. 공중에서 누르면 착지 후 숙인다.
//   점프 입력: 누른 순간을 150ms 기억(착지 직전 입력도 받음), 누르고 있으면 착지할 때마다 다시 뛴다.
// 상태 s: 'idle' | 'walk' | 'jump'(vy<0) | 'fall'(vy>=0, 공중) | 'crouch'

export const PHYS = Object.freeze({
  gravity: 2000,
  jumpV: 650,
  groundY: 440,
  jumpBufferMs: 150,
});
export const MOVE_STATES = Object.freeze(['idle', 'walk', 'jump', 'fall', 'crouch']);
const STATE_SET = new Set(MOVE_STATES);
export const isMoveState = (s) => typeof s === 'string' && STATE_SET.has(s);

/** 최고 높이 (월드) */
export const JUMP_APEX = (PHYS.jumpV * PHYS.jumpV) / (2 * PHYS.gravity);

/** 몸 상태 초기값 */
export function createBody(x, y = PHYS.groundY) {
  return { x, y, vy: 0, grounded: y >= PHYS.groundY, crouch: false, s: 'idle' };
}

/**
 * 한 프레임 진행. 등가속 운동을 정확히 적분하므로 dt가 달라도 같은 궤적이다.
 * @param b 몸 { x, y, vy, grounded, crouch, s } (제자리 수정)
 * @param inp { dir: -1|0|1, jump: boolean(이번 프레임 점프 요청: 버퍼 또는 누름 유지), crouch: boolean(누르는 중) }
 * @param dt 초
 * @param opt { speed, minX, maxX }
 * @returns { jumped: boolean, landed: boolean }
 */
export function stepBody(b, inp, dt, opt) {
  const g = PHYS.gravity;
  let jumped = false;
  let landed = false;
  if (b.grounded) {
    b.crouch = !!inp.crouch;
    if (!b.crouch && inp.jump) {
      b.vy = -PHYS.jumpV;
      b.grounded = false;
      jumped = true;
    }
  }
  // 좌우: 숙인 동안 불가, 공중에서는 허용
  const dir = b.crouch ? 0 : (inp.dir | 0);
  if (dir !== 0) b.x = Math.min(opt.maxX, Math.max(opt.minX, b.x + dir * opt.speed * dt));
  if (!b.grounded) {
    b.y += b.vy * dt + 0.5 * g * dt * dt;
    b.vy += g * dt;
    if (b.y >= PHYS.groundY && b.vy >= 0) { // 상승 중(dt = 0인 점프 첫 프레임 포함)에는 착지가 아니다
      b.y = PHYS.groundY;
      b.vy = 0;
      b.grounded = true;
      landed = true;
      b.crouch = !!inp.crouch; // 착지 순간 누르고 있으면 바로 숙임
    }
  }
  b.s = stateOf(b, dir);
  return { jumped, landed };
}

export function stateOf(b, dir) {
  if (!b.grounded) return b.vy < 0 ? 'jump' : 'fall';
  if (b.crouch) return 'crouch';
  return dir !== 0 ? 'walk' : 'idle';
}

/**
 * 원격 캐릭터: 받은 (y, s)에서 세로 속도를 되살린다. 점프는 항상 지면에서 초속 650으로 시작하므로
 * 에너지 보존으로 |vy| = sqrt(650² - 2g(440 - y)). 방향은 s(jump = 위, fall = 아래).
 */
export function velocityAt(y, s) {
  const h = Math.max(0, PHYS.groundY - y);
  const v = Math.sqrt(Math.max(0, PHYS.jumpV * PHYS.jumpV - 2 * PHYS.gravity * h));
  return s === 'jump' ? -v : v;
}

/** 원격 시뮬레이션 한 프레임: { y, vy, air } (제자리 수정) */
export function stepRemoteAir(r, dt) {
  if (!r.air) return;
  r.y += r.vy * dt + 0.5 * PHYS.gravity * dt * dt;
  r.vy += PHYS.gravity * dt;
  if (r.y >= PHYS.groundY && r.vy >= 0) { r.y = PHYS.groundY; r.vy = 0; r.air = false; }
}

/** move payload 정리 (수신 측). 깨진 값이면 null. y는 [지면 - 200, 지면]로 자른다. s가 없으면 null(추정은 화면이). */
export function cleanMove(p) {
  if (!p || typeof p !== 'object') return null;
  if (typeof p.user_id !== 'string' || !p.user_id || p.user_id.length > 64) return null;
  if (typeof p.x !== 'number' || !Number.isFinite(p.x)) return null;
  const y = typeof p.y === 'number' && Number.isFinite(p.y)
    ? Math.min(PHYS.groundY, Math.max(PHYS.groundY - 200, p.y)) : PHYS.groundY;
  const dir = p.dir === 'left' || p.dir === -1 ? 'left' : (p.dir === 'right' || p.dir === 1 ? 'right' : null);
  return { user_id: p.user_id, x: p.x, y, dir, s: isMoveState(p.s) ? p.s : null };
}
