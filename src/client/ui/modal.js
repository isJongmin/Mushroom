// 모달 공통 동작 (lobby.md 5.2, style-guide 11.8)
// - .bk-dim > section.bk-panel.bk-modal[role=dialog][aria-modal=true]
// - 뒤 main에 inert (미지원 브라우저는 aria-hidden + 아래 focus trap으로 대체), body.has-modal
// - Focus trap: Tab/Shift+Tab 순환 직접 구현, 모달 밖으로 포커스가 나가면 되돌린다
// - Esc = 취소 (canEscape()가 false면 무시: 처리 중, IME 조합 중), 딤 클릭은 닫지 않는다
// - 닫으면 연 버튼으로 포커스 복귀 (사라졌으면 fallback)
// - 한 번에 1개. 새 모달을 열면 이전 모달은 포커스 복귀 없이 닫힌다.
import { h } from '../dom.js';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const HAS_INERT = typeof HTMLElement !== 'undefined' && 'inert' in HTMLElement.prototype;

let current = null;

/**
 * @param {object} o
 * @param {HTMLElement} o.main  모달 뒤 영역 (inert 대상)
 * @param {string} o.titleId   aria-labelledby
 * @param {string} [o.descId]  aria-describedby
 * @param {string} [o.testid]
 * @param {Node[]} o.children  모달 내용
 * @param {() => HTMLElement|null} [o.initialFocus]
 * @param {() => void} o.onCancel  Esc
 * @param {() => boolean} [o.canEscape]
 * @param {HTMLElement|null} [o.returnTo]  닫을 때 포커스를 돌려줄 요소
 * @param {() => HTMLElement|null} [o.fallbackFocus]
 */
export function openModal(o) {
  if (current) current.close({ restoreFocus: false });
  const ac = new AbortController();
  const on = (el, type, fn, opt) => el.addEventListener(type, fn, { signal: ac.signal, ...opt });

  const section = h('section', {
    class: 'bk-panel bk-modal', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': o.titleId,
    'aria-describedby': o.descId || null, testid: o.testid || 'modal',
  }, o.children);
  const dim = h('div', { class: 'bk-dim', testid: 'modal-dim' }, section);
  document.body.appendChild(dim);
  document.body.classList.add('has-modal');
  const main = o.main;
  if (main) {
    if (HAS_INERT) main.inert = true;
    else main.setAttribute('aria-hidden', 'true');
  }

  const focusables = () => [...section.querySelectorAll(FOCUSABLE)].filter((el) => !el.hidden && el.offsetParent !== null);
  const focusFirst = () => {
    const el = (o.initialFocus && o.initialFocus()) || focusables()[0] || section;
    if (el === section) section.tabIndex = -1;
    el.focus({ preventScroll: true });
  };

  on(document, 'keydown', (e) => {
    if (e.key === 'Escape') {
      if (e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      if (!o.canEscape || o.canEscape()) o.onCancel();
      return;
    }
    if (e.key !== 'Tab') return;
    const list = focusables();
    if (!list.length) { e.preventDefault(); return; }
    const first = list[0];
    const last = list[list.length - 1];
    const ae = document.activeElement;
    if (e.shiftKey && (ae === first || !section.contains(ae))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && (ae === last || !section.contains(ae))) { e.preventDefault(); first.focus(); }
  }, { capture: true });
  // 모달 밖으로 포커스가 나가면 되돌린다 (inert 미지원 대비)
  on(document, 'focusin', (e) => { if (!section.contains(e.target)) focusFirst(); });

  let closed = false;
  const api = {
    section,
    close({ restoreFocus = true } = {}) {
      if (closed) return;
      closed = true;
      ac.abort();
      dim.remove();
      if (current === api) current = null;
      if (!current) {
        document.body.classList.remove('has-modal');
        if (main) {
          if (HAS_INERT) main.inert = false;
          else main.removeAttribute('aria-hidden');
        }
      }
      if (restoreFocus) {
        const target = o.returnTo && o.returnTo.isConnected && !o.returnTo.disabled ? o.returnTo : (o.fallbackFocus && o.fallbackFocus());
        if (target) target.focus({ preventScroll: true });
      }
    },
    get open() { return !closed; },
  };
  current = api;
  focusFirst();
  return api;
}

/** 화면 정리용: 열려 있는 모달을 포커스 복귀 없이 닫는다. */
export function closeAnyModal() {
  if (current) current.close({ restoreFocus: false });
}
