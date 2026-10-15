// 이동 입력 상태. 키보드와 터치 버튼을 "누른 순서"로 관리한다.
// 규칙(screens/game.md 3.1, 5.1): 나중에 누른 방향 우선, 한쪽을 떼면 남은 쪽으로 계속 이동.

export function createMoveInput() {
  const held = new Map(); // sourceId -> { dir, order }
  let seq = 0;
  return {
    press(sourceId, dir) {
      if (held.has(sourceId)) return; // 키 반복 무시
      held.set(sourceId, { dir, order: ++seq });
    },
    release(sourceId) {
      held.delete(sourceId);
    },
    clear() {
      held.clear();
    },
    /** -1(왼쪽), 0(정지), 1(오른쪽) */
    direction() {
      let best = null;
      for (const v of held.values()) if (!best || v.order > best.order) best = v;
      return best ? best.dir : 0;
    },
  };
}

export const KEY_DIR = Object.freeze({
  ArrowLeft: -1,
  KeyA: -1,
  ArrowRight: 1,
  KeyD: 1,
});
