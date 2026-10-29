// 이동 입력 상태. 키보드와 터치 버튼을 "누른 순서"로 관리한다.
// 규칙(screens/game.md 3.1, 5.1): 나중에 누른 방향 우선, 한쪽을 떼면 남은 쪽으로 계속 이동.
// (사이클 6) 동작 입력: 점프(누른 순간 기억 + 누르고 있음), 엎드리기(누르고 있음). 출처(sourceId)별로 관리해
// 키보드와 터치를 섞어도 한쪽을 뗄 때 다른 쪽이 남는다.
// (사이클 8) 더블탭: 같은 묶음(왼쪽 = ←/A/터치 왼쪽, 오른쪽 = →/D/터치 오른쪽, 위 = ↑/W/터치 점프)을
// doubleTapMs(300) 안에 두 번 누르면 슈퍼 점프 요청 1건. 다른 묶음을 누르면 진행 중인 더블탭은 끊긴다. Space는 제외.

export function createMoveInput({ doubleTapMs = 300 } = {}) {
  const held = new Map(); // sourceId -> { dir, order }
  const acts = new Map(); // sourceId -> 'jump' | 'prone'
  let seq = 0;
  let jumpAt = -Infinity; // 마지막 점프 누름 시각 (performance.now 기준)
  let attackAt = -Infinity; // (사이클 9) 마지막 공격 누름 시각
  let lastTap = null; // { group, at }
  let superReq = null; // { kind, firstAt, at }
  let jumpHoldOff = false; // (사이클 10) 로프 위끝에 올라선 뒤: 다시 누를 때까지 누르고 있는 점프를 무시
  const holding = (action) => {
    if (action === 'jump' && jumpHoldOff) return false;
    for (const a of acts.values()) if (a === action) return true;
    return false;
  };
  return {
    press(sourceId, dir) {
      if (held.has(sourceId)) return; // 키 반복 무시
      held.set(sourceId, { dir, order: ++seq });
    },
    /** 점프/엎드리기 누름. now = performance.now() */
    pressAction(sourceId, action, now) {
      if (acts.has(sourceId)) return; // 키 반복 무시
      acts.set(sourceId, action);
      if (action === 'jump') { jumpAt = now; jumpHoldOff = false; }
      else if (action === 'attack') attackAt = now;
    },
    /** 더블탭 묶음 누름 ('left' | 'right' | 'up'). 키 반복은 부르는 쪽이 거른다. */
    tap(group, now) {
      if (lastTap && lastTap.group === group && now - lastTap.at <= doubleTapMs) {
        superReq = { kind: group, firstAt: lastTap.at, at: now };
        lastTap = null;
        return true;
      }
      lastTap = { group, at: now };
      return false;
    },
    /** 이번 프레임 슈퍼 점프 요청 { kind, age(초: 첫 누름부터) } 또는 null. 꺼내면 지운다(쿨다운에 막혀도 쌓지 않음). */
    takeSuper(now) {
      const r = superReq;
      superReq = null;
      if (!r || now - r.at > 150) return null;
      return { kind: r.kind, age: Math.max(0, (now - r.firstAt) / 1000) };
    },
    release(sourceId) {
      held.delete(sourceId);
      acts.delete(sourceId);
    },
    clear() {
      held.clear();
      acts.clear();
      jumpAt = -Infinity;
      jumpHoldOff = false;
      attackAt = -Infinity;
      lastTap = null;
      superReq = null;
    },
    /** -1(왼쪽), 0(정지), 1(오른쪽) */
    direction() {
      let best = null;
      for (const v of held.values()) if (!best || v.order > best.order) best = v;
      return best ? best.dir : 0;
    },
    /** 이번 프레임 점프 요청: 최근 bufferMs 안에 눌렀거나 누르고 있음 */
    wantsJump(now, bufferMs) {
      return now - jumpAt <= bufferMs || holding('jump');
    },
    /** 점프 입력을 썼으면 누름 기억을 지운다 (누르고 있으면 착지 후 다시 뛴다) */
    consumeJump() {
      jumpAt = -Infinity;
    },
    proning() {
      return holding('prone');
    },
    /** (사이클 10) 로프 오르기: ↑/W/터치 점프를 누르고 있음 (Space 제외) */
    upHeld() {
      for (const [id, a] of acts) if (a === 'jump' && id !== 'key:Space') return true;
      return false;
    },
    /** (사이클 10) 점프를 방금(bufferMs 안) 새로 눌렀음 — 로프에서 뛰어내리기 */
    jumpTapped(now, bufferMs) {
      return now - jumpAt <= bufferMs;
    },
    /** (사이클 10) 누르고 있는 점프를 다음 누름까지 무시 (로프 위끝에서 올라선 직후 바로 뛰지 않게) */
    suppressJumpHold() {
      jumpHoldOff = true;
      jumpAt = -Infinity;
    },
    /** (사이클 9) 공격: 최근 bufferMs 안에 눌렀거나 누르고 있음(누르고 있으면 쿨다운마다 계속 공격) */
    wantsAttack(now, bufferMs = 150) {
      return now - attackAt <= bufferMs || holding('attack');
    },
    consumeAttack() { attackAt = -Infinity; },

  };
}

export const KEY_DIR = Object.freeze({
  ArrowLeft: -1,
  KeyA: -1,
  ArrowRight: 1,
  KeyD: 1,
});

/** 점프 = ↑ / W / Space, 엎드리기 = ↓ / S */
export const KEY_ACTION = Object.freeze({
  ArrowUp: 'jump',
  KeyW: 'jump',
  Space: 'jump',
  ArrowDown: 'prone',
  KeyS: 'prone',
});

/** (사이클 8) 슈퍼 점프 더블탭 묶음 */
export const KEY_TAP = Object.freeze({
  ArrowLeft: 'left',
  KeyA: 'left',
  ArrowRight: 'right',
  KeyD: 'right',
  ArrowUp: 'up',
  KeyW: 'up',
});

/** 기본 공격 = Ctrl / J / X. 스킬 = 1 / 2 / 3 (room). */
export const KEY_ATTACK = Object.freeze({ ControlLeft: true, ControlRight: true, KeyJ: true, KeyX: true });
