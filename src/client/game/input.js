// 이동 입력 상태. 키보드와 터치 버튼을 "누른 순서"로 관리한다.
// 규칙(screens/game.md 3.1, 5.1): 나중에 누른 방향 우선, 한쪽을 떼면 남은 쪽으로 계속 이동.
// (사이클 6) 동작 입력: 점프(누른 순간 기억 + 누르고 있음), 숙이기(누르고 있음). 출처(sourceId)별로 관리해
// 키보드와 터치를 섞어도 한쪽을 뗄 때 다른 쪽이 남는다.

export function createMoveInput() {
  const held = new Map(); // sourceId -> { dir, order }
  const acts = new Map(); // sourceId -> 'jump' | 'crouch'
  let seq = 0;
  let jumpAt = -Infinity; // 마지막 점프 누름 시각 (performance.now 기준)
  const holding = (action) => {
    for (const a of acts.values()) if (a === action) return true;
    return false;
  };
  return {
    press(sourceId, dir) {
      if (held.has(sourceId)) return; // 키 반복 무시
      held.set(sourceId, { dir, order: ++seq });
    },
    /** 점프/숙이기 누름. now = performance.now() */
    pressAction(sourceId, action, now) {
      if (acts.has(sourceId)) return; // 키 반복 무시
      acts.set(sourceId, action);
      if (action === 'jump') jumpAt = now;
    },
    release(sourceId) {
      held.delete(sourceId);
      acts.delete(sourceId);
    },
    clear() {
      held.clear();
      acts.clear();
      jumpAt = -Infinity;
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
    /** 점프를 실행했으면 누름 기억을 지운다 (누르고 있으면 착지 후 다시 뛴다) */
    consumeJump() {
      jumpAt = -Infinity;
    },
    crouching() {
      return holding('crouch');
    },
  };
}

export const KEY_DIR = Object.freeze({
  ArrowLeft: -1,
  KeyA: -1,
  ArrowRight: 1,
  KeyD: 1,
});

/** (사이클 6) 점프 = ↑ / W / Space, 숙이기 = ↓ / S */
export const KEY_ACTION = Object.freeze({
  ArrowUp: 'jump',
  KeyW: 'jump',
  Space: 'jump',
  ArrowDown: 'crouch',
  KeyS: 'crouch',
});
