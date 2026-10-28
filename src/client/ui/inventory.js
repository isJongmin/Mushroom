// (사이클 9) 가방 패널: 방 HUD 가방 버튼으로 연다. 아이템을 누르면 즉시 착용(화면이 프로필 저장 + updateSelf).
// 블록 UI 키트(.bk-panel, .bk-slots, .bk-slot, .bk-btn) 그대로. 모달이 아니다(게임은 계속, Esc로 닫기).
// 아이템 이름은 manifest label(아트 문자열)을 textContent/aria-label로만 넣는다.
import { h, setText } from '../dom.js';
import { parseItem } from '../game/mobs.js';
import { drawItemIcon } from '../game/drops.js';
import { PART_LABELS } from '../constants.js';

const SLOT_PX = 80;

/**
 * @param o.items()        현재 인벤토리 아이템 배열
 * @param o.avatar()       현재 착용 아바타 (7키)
 * @param o.labelOf(part, id)
 * @param o.icons          createItemIcons()
 * @param o.thumbFn(item)  아이콘 대체 썸네일
 * @param o.onEquip(item)
 * @param o.on             리스너 등록 함수 (AbortSignal로 해제)
 */
export function createInventoryPanel(o) {
  const title = h('h2', { class: 'inv-title', id: 'inv-title' }, '가방');
  const count = h('span', { class: 'bk-chip inv-count', testid: 'inventory-count' });
  const closeBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--sm', testid: 'inventory-close', 'aria-label': '가방 닫기' }, '닫기');
  const grid = h('div', { class: 'bk-slots inv-slots', role: 'group', 'aria-labelledby': 'inv-title', testid: 'inventory-grid' });
  const empty = h('p', { class: 'bk-help inv-empty', testid: 'inventory-empty' }, '아직 아이템이 없어요. 몬스터를 잡고 Z로 주워 보세요.');
  const status = h('p', { class: 'bk-help inv-status', 'aria-live': 'polite', testid: 'inventory-status' });
  const el = h('section', { class: 'bk-panel inv-panel', testid: 'inventory-panel', 'aria-labelledby': 'inv-title', hidden: true },
    h('div', { class: 'inv-head' }, title, count, closeBtn), empty, grid, status);
  let slots = [];
  let isOpen = false;

  function paint() {
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const av = o.avatar();
    for (const s of slots) {
      const on = !!(s.it && av && av[s.it.part] === s.it.id);
      s.btn.setAttribute('aria-pressed', String(on));
      const c = s.cv.getContext('2d');
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.clearRect(0, 0, s.cv.width, s.cv.height);
      c.imageSmoothingEnabled = true;
      c.imageSmoothingQuality = 'high';
      drawItemIcon(c, s.item, (SLOT_PX * dpr) / 2, (SLOT_PX * dpr) / 2, SLOT_PX * dpr * 0.8, o.icons, o.thumbFn);
    }
  }

  function build() {
    const items = o.items();
    setText(count, `${items.length}개`);
    empty.hidden = items.length > 0;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    slots = items.map((item) => {
      const it = parseItem(item);
      const name = it ? `${PART_LABELS[it.part] || it.part} · ${o.labelOf(it.part, it.id)}` : item;
      const cv = h('canvas', { 'aria-hidden': 'true' });
      cv.width = SLOT_PX * dpr;
      cv.height = SLOT_PX * dpr;
      const btn = h('button', { type: 'button', class: 'bk-slot', 'aria-pressed': 'false', 'aria-label': `${name} 착용`, title: name, testid: `inv-item-${item}`, 'data-item': item }, cv);
      return { item, it, btn, cv };
    });
    grid.replaceChildren(...slots.map((s) => s.btn));
    paint();
  }

  function open() {
    if (isOpen) return;
    isOpen = true;
    setText(status, '');
    build();
    el.hidden = false;
    (slots[0] ? slots[0].btn : closeBtn).focus({ preventScroll: true });
  }
  function close() {
    if (!isOpen) return;
    isOpen = false;
    el.hidden = true;
    o.onClose?.();
  }

  o.on(closeBtn, 'click', () => close());
  o.on(grid, 'click', (e) => {
    const btn = e.target.closest('.bk-slot');
    if (!btn || !grid.contains(btn)) return;
    const item = btn.dataset.item;
    const it = parseItem(item);
    if (!it) return;
    if (o.onEquip(item)) setText(status, `${PART_LABELS[it.part] || it.part}: ${o.labelOf(it.part, it.id)} 착용`);
    paint();
  });
  o.on(el, 'keydown', (e) => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); }
  });

  return {
    el,
    open,
    close,
    toggle() { if (isOpen) close(); else open(); },
    refresh() { if (isOpen) build(); },
    repaint() { if (isOpen) paint(); },
    get isOpen() { return isOpen; },
  };
}
