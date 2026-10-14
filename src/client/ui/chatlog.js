// 채팅 로그 패널 (room.md 3.2, 4.2, 5장 / style-guide 11.9 / ui-kit 22절)
// 모든 사용자 글자(닉네임, 채팅)는 textContent로만 넣는다.
import { h, setText } from '../dom.js';
import { LOG_DOM_MAX, SS_LOG_OPEN } from '../constants.js';
import { ROOM_MESSAGES as M } from '../errors.js';

const BOTTOM_SLACK = 24;
let seq = 0;

function pad2(n) { return String(n).padStart(2, '0'); }
export function formatTime(iso, now = new Date()) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const hm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  const sameDay = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  return sameDay ? hm : `${d.getMonth() + 1}월 ${d.getDate()}일 ${hm}`;
}
const badgeText = (n) => (n > 99 ? '99+' : String(n));

function readLogOpen() {
  try { return sessionStorage.getItem(SS_LOG_OPEN) !== '0'; } catch { return true; }
}
function writeLogOpen(open) {
  try { sessionStorage.setItem(SS_LOG_OPEN, open ? '1' : '0'); } catch { /* 무시 */ }
}

/**
 * @param {{ myId: string, onLayout?: () => void }} o  onLayout: 펼침/접힘이 바뀔 때 (배너 위치용 .log-open 갱신)
 */
export function createChatLog(o) {
  const ac = new AbortController();
  const on = (el, type, fn) => el.addEventListener(type, fn, { signal: ac.signal });
  const n = ++seq;
  const titleId = `log-title-${n}`;
  const listId = `log-list-${n}`;
  const panelId = `log-panel-${n}`;

  const headBadge = h('span', { class: 'bk-badge', testid: 'log-unread', hidden: true });
  const headBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--xs', testid: 'log-fold', 'aria-controls': listId, 'aria-expanded': 'true' }, '접기');
  const list = h('ol', {
    class: 'bk-log__list', id: listId, role: 'log', 'aria-live': 'polite', 'aria-relevant': 'additions',
    'aria-labelledby': titleId, tabindex: '0', testid: 'chat-log',
  });
  const stateDots = h('span', { class: 'bk-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const stateRow = h('div', { class: 'bk-log__state', testid: 'log-loading', hidden: true }, stateDots, M.LOG_LOADING);
  const newLabel = h('span', {});
  const newBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--xs bk-btn--primary bk-log__new', testid: 'log-new', hidden: true },
    newLabel, h('span', { class: 'bk-ico bk-ico--down', 'aria-hidden': 'true' }));
  const el = h('section', { class: 'bk-log room-log', id: panelId, 'aria-labelledby': titleId, testid: 'log-panel' },
    h('div', { class: 'bk-log__head' }, h('h2', { class: 'bk-log__title', id: titleId }, '채팅 기록'), headBadge, headBtn),
    stateRow, list, newBtn);

  // 모바일 HUD 2줄째 토글
  const toggleBadge = h('span', { class: 'bk-badge', testid: 'log-toggle-unread', hidden: true });
  const toggle = h('button', {
    type: 'button', class: 'bk-btn bk-btn--sm room-log-toggle', testid: 'log-toggle', 'aria-expanded': 'false', 'aria-controls': panelId,
  }, '채팅 기록', toggleBadge);

  let mobile = false;
  let desktopOpen = readLogOpen();
  let mobileOpen = false;
  let unread = 0; // 접힘/숨김 중 도착한 일반/내 메시지
  let newCount = 0; // 위로 스크롤한 채 도착한 일반/내 메시지
  const seenIds = new Set();
  let historyLoaded = false;

  const visible = () => (mobile ? mobileOpen : desktopOpen);
  const atBottom = () => list.scrollHeight - list.scrollTop - list.clientHeight <= BOTTOM_SLACK;
  const toBottom = () => { list.scrollTop = list.scrollHeight; };

  function renderBadges() {
    const t = badgeText(unread);
    setText(headBadge, t);
    setText(toggleBadge, t);
    headBadge.setAttribute('aria-label', M.NEW_MESSAGES(unread));
    toggleBadge.setAttribute('aria-label', M.NEW_MESSAGES(unread));
    headBadge.hidden = mobile || desktopOpen || unread === 0;
    toggleBadge.hidden = !mobile || mobileOpen || unread === 0;
  }
  function renderNew() {
    newBtn.hidden = newCount === 0 || !visible();
    setText(newLabel, M.NEW_MESSAGES(newCount > 99 ? '99+' : newCount));
  }

  function applyMode() {
    if (mobile) {
      el.classList.remove('is-collapsed');
      el.hidden = !mobileOpen;
      list.hidden = !mobileOpen;
      setText(headBtn, '닫기');
      headBtn.setAttribute('aria-expanded', String(mobileOpen));
      toggle.setAttribute('aria-expanded', String(mobileOpen));
    } else {
      el.hidden = false;
      list.hidden = false; // 접힘은 CSS(.is-collapsed → display:none)로 숨긴다
      el.classList.toggle('is-collapsed', !desktopOpen);
      setText(headBtn, desktopOpen ? '접기' : '펼치기');
      headBtn.setAttribute('aria-expanded', String(desktopOpen));
    }
    renderBadges();
    renderNew();
    o.onLayout?.();
  }

  function expanded() {
    unread = 0;
    newCount = 0;
    applyMode();
    toBottom();
  }

  on(headBtn, 'click', () => {
    if (mobile) {
      mobileOpen = false;
      applyMode();
      toggle.focus({ preventScroll: true });
    } else {
      desktopOpen = !desktopOpen;
      writeLogOpen(desktopOpen);
      if (desktopOpen) expanded(); else applyMode();
    }
  });
  on(toggle, 'click', () => {
    mobileOpen = !mobileOpen;
    if (mobileOpen) { expanded(); headBtn.focus({ preventScroll: true }); } else applyMode();
  });
  on(newBtn, 'click', () => { newCount = 0; renderNew(); toBottom(); });
  on(list, 'scroll', () => { if (newCount && atBottom()) { newCount = 0; renderNew(); } });

  function trim() {
    while (list.children.length > LOG_DOM_MAX) list.firstElementChild.remove();
  }

  /** 새 항목을 맨 아래에 붙인다. countable = 일반/내 메시지(시스템 제외), force = 위치와 상관없이 맨 아래로 */
  function append(item, { countable, force }) {
    const vis = visible();
    const wasBottom = vis && atBottom();
    list.appendChild(item);
    trim();
    if (!vis) {
      if (countable) { unread++; renderBadges(); }
      return;
    }
    if (force || wasBottom) toBottom();
    else if (countable) { newCount++; renderNew(); }
  }

  function chatItem(msg, self) {
    const li = h('li', { class: self ? 'bk-msg bk-msg--self' : 'bk-msg', testid: 'log-item', 'data-id': String(msg.id), 'data-kind': self ? 'self' : 'chat' },
      self ? h('span', { class: 'bk-sr' }, '나: ') : null,
      h('b', { class: 'bk-msg__nick' }, msg.nickname),
      msg.text,
      h('time', { class: 'bk-msg__time', datetime: msg.created_at }, formatTime(msg.created_at)));
    li._msg = msg; // eslint-disable-line no-underscore-dangle
    return li;
  }
  function sysItem(text, variant) {
    const cls = variant === 'error' ? 'bk-msg bk-msg--sys is-error' : variant === 'history' ? 'bk-msg bk-msg--sys is-history' : 'bk-msg bk-msg--sys';
    return h('li', { class: cls, testid: 'log-item', 'data-kind': variant === 'history' ? 'history' : 'sys' }, text);
  }

  const api = {
    el,
    toggle,
    setMobile(m) {
      if (m === mobile && el.dataset.mode) return;
      mobile = m;
      el.dataset.mode = m ? 'mobile' : 'desktop';
      if (m) mobileOpen = false; // 모바일은 매번 접힌 상태로 시작 (room.md 5.5)
      else desktopOpen = readLogOpen();
      applyMode();
      if (visible()) toBottom();
    },
    /** 데스크톱에서 로그가 펼쳐져 있는가 (.game-stage.log-open 용) */
    desktopExpanded() { return !mobile && desktopOpen; },
    setLoading(b) {
      stateRow.hidden = !b;
      list.setAttribute('aria-busy', String(!!b));
    },
    /** 입장 시 기록 (오래된 것부터). 맨 위에 "이전 대화 N개" + 기록. 이미 있는 id는 건너뛴다. */
    loadHistory(msgs, myId) {
      historyLoaded = true;
      list.setAttribute('aria-busy', 'true');
      stateRow.hidden = true;
      const items = [];
      for (const m of msgs) {
        if (seenIds.has(m.id)) continue;
        seenIds.add(m.id);
        items.push(chatItem(m, m.user_id === myId));
      }
      // 실시간으로 먼저 도착해 이미 있는 id는 빼고 센다 (구분 줄 아래 실제로 들어간 기록 수)
      if (items.length) items.unshift(sysItem(M.HISTORY(items.length), 'history'));
      list.prepend(...items);
      trim();
      list.setAttribute('aria-busy', 'false');
      toBottom(); // 기록을 처음 불러온 직후에는 맨 아래로 (5.4)
    },
    historyFailed() {
      historyLoaded = true;
      stateRow.hidden = true;
      list.setAttribute('aria-busy', 'false');
      list.prepend(sysItem(M.HISTORY_FAILED, 'error'));
    },
    get historyLoaded() { return historyLoaded; },
    /** 재연결 후 다시 불러온 기록: 빠진 메시지를 id 순서대로 끼워 넣는다. */
    merge(msgs, myId) {
      for (const m of msgs) {
        if (seenIds.has(m.id)) continue;
        seenIds.add(m.id);
        const item = chatItem(m, m.user_id === myId);
        const after = [...list.children].find((li) => li._msg && li._msg.id > m.id); // eslint-disable-line no-underscore-dangle
        if (after) list.insertBefore(item, after);
        else append(item, { countable: true, force: false });
      }
      trim();
    },
    /** 실시간 chat (서버 송신). 이미 있는 id면 false. */
    addChat(msg, self) {
      if (seenIds.has(msg.id)) return false;
      seenIds.add(msg.id);
      if (seenIds.size > 2000) seenIds.delete(seenIds.values().next().value);
      append(chatItem(msg, self), { countable: true, force: self });
      return true;
    },
    addSystem(text, variant = 'normal') {
      append(sysItem(text, variant), { countable: false, force: false });
    },
    /** 테스트 훅: 최근 n개 */
    snapshot(limit = 50) {
      const out = [];
      for (const li of [...list.children].slice(-limit)) {
        const m = li._msg; // eslint-disable-line no-underscore-dangle
        if (m) out.push({ id: m.id, user_id: m.user_id, nickname: m.nickname, text: m.text, system: false, self: li.dataset.kind === 'self' });
        else out.push({ id: null, user_id: null, nickname: null, text: li.textContent, system: true, kind: li.dataset.kind, error: li.classList.contains('is-error') });
      }
      return out;
    },
    ui() {
      return { mobile, open: visible(), unread, newMessages: newCount, items: list.children.length };
    },
    destroy() {
      ac.abort();
      el.remove();
      toggle.remove();
    },
  };
  return api;
}
