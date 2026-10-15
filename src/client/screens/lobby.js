// 로비: 방 목록 + 방 만들기 + 입장 (docs/design/screens/lobby.md v4, style-guide 11장, ui-kit 14~23절)
// - 방 목록: listRooms 5초 폴링(응답 후 setTimeout 사슬, 숨김 탭/입장·만들기 요청 중 정지) + 수동 새로고침
// - 행은 방 id 키로 DOM 재사용(스크롤/포커스 유지). 사용자 문자열(방 이름, 닉네임)은 textContent로만.
// - 모달: 방 만들기 / 비밀번호 / 닉네임 겹침 (ui/modal.js: focus trap, Esc 취소, 딤 클릭 무시, 포커스 복귀)
import { h, setText } from '../dom.js';
import {
  NICK_RE, NICK_MAX, ROOM_NAME_MAX, ROOM_PW_MIN, ROOM_PW_MAX, ROOM_CAPACITY, PART_KEYS, LOBBY_POLL_MS, RATE_LOCK_MS,
} from '../constants.js';
import { LOBBY_MESSAGES as M, PROFILE_MESSAGES as PM, toAppError } from '../errors.js';
import { createAvatarRenderer, smooth } from '../avatar.js';
import { openModal } from '../ui/modal.js';
import { writeRoomSession } from '../store.js';
import { trimWs, charLength, hasControl, cleanRoomName } from '../backend/common.js';

const THUMB_CROP = Object.freeze({ x: 16, y: 26, size: 112, css: 40 }); // 사이클 5: front 프레임(시트 px) 얼굴/머리(모자 포함) 정사각형 → CSS 40px
const LIST_LIMIT = 100;
const REFRESH_MIN_MS = 400;
const BANNER_MS = 8000;

const dots = () => h('span', { class: 'bk-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));

function agoText(iso, now = Date.now()) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return '';
  const min = Math.floor(Math.max(0, now - t) / 60000);
  if (min < 1) return '방금 생성';
  if (min < 60) return `${min}분 전 생성`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전 생성`;
  return `${Math.floor(hr / 24)}일 전 생성`;
}

/** NICK_TAKEN 제안값: 프로필 닉네임 + "2" (12자를 넘으면 앞 11자 + "2") */
function suggestNick(nick) {
  const chars = [...nick];
  return (chars.length >= NICK_MAX ? chars.slice(0, NICK_MAX - 1).join('') : nick) + '2';
}

let fieldSeq = 0;

export function mount(root, app, opts = {}) {
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;
  const timers = new Set();
  const later = (fn, ms) => { const t = setTimeout(() => { timers.delete(t); if (alive) fn(); }, ms); timers.add(t); return t; };
  const cancel = (t) => { if (t) { clearTimeout(t); timers.delete(t); } };
  const profile = app.profile;

  // --- 머리줄 -----------------------------------------------------------------
  const dpr = Math.max(1, Math.min(3, Math.round(window.devicePixelRatio || 1)));
  const thumb = h('canvas', { width: String(THUMB_CROP.css * dpr), height: String(THUMB_CROP.css * dpr), 'aria-hidden': 'true', testid: 'me-thumb' });
  const meNick = h('span', { class: 'bk-me__nick', testid: 'me-nickname' }, profile.nickname);
  meNick.title = profile.nickname;
  const editBtn = h('button', { class: 'bk-btn bk-btn--sm', type: 'button', testid: 'profile-edit' }, '꾸미기');
  const modeSlot = h('span', { class: 'mode-slot' });
  const header = h('header', { class: 'lobby-head' },
    h('div', { class: 'lobby-brand' },
      h('h1', { class: 'bk-logo bk-logo--sm' }, h('span', { class: 'bk-ico bk-ico--mush', 'aria-hidden': 'true' }), '버섯마을'),
      modeSlot),
    h('div', { class: 'bk-me', testid: 'me-card' },
      h('span', { class: 'bk-thumb' }, thumb),
      h('span', { class: 'bk-me__name' }, h('span', { class: 'bk-me__label' }, '내 캐릭터'), meNick),
      editBtn));

  // --- 패널 -------------------------------------------------------------------
  const title = h('h2', { id: 'lobby-title', tabindex: '-1' }, '방 목록');
  const countEl = h('span', { class: 'lobby-tools__count', testid: 'room-count' });
  const refreshDots = dots();
  refreshDots.hidden = true;
  const refreshBtn = h('button', { class: 'bk-btn bk-btn--sm', type: 'button', testid: 'room-refresh', disabled: true }, refreshDots, '새로고침');
  const createBtn = h('button', { class: 'bk-btn bk-btn--primary', type: 'button', testid: 'room-create', disabled: true }, '방 만들기');
  const banner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'lobby-banner', hidden: true });
  const list = h('ul', { class: 'bk-roomlist', role: 'list', 'aria-labelledby': 'lobby-title', 'aria-busy': 'true', testid: 'room-list' });
  const wrap = h('div', { class: 'bk-roomwrap', testid: 'room-wrap' }, list);
  const note = h('p', { class: 'lobby-note', testid: 'room-limit-note', hidden: true }, M.LIMIT_NOTE);
  const srStatus = h('div', { class: 'bk-sr', role: 'status', testid: 'lobby-status' });
  const panel = h('section', { class: 'bk-panel lobby-panel', 'aria-labelledby': 'lobby-title' },
    h('div', { class: 'lobby-tools' }, title, countEl, refreshBtn, createBtn),
    banner, wrap, note, srStatus);
  const main = h('main', { class: 'scr-lobby', id: 'lobby' }, header, panel);
  root.append(main);
  if (app.mode === 'local') app.placeModeBadge(modeSlot);

  // --- 상태 -------------------------------------------------------------------
  let phase = 'loading'; // loading | ready | error
  let rooms = [];
  let busy = null; // null | { kind: 'join'|'create'|'refresh', roomId? }
  let bannerInfo = null; // { kind, text, sticky }
  let pollFailed = false;
  let modal = null; // { kind, api }
  const rows = new Map(); // room id -> row

  // --- 배너 (6장) -------------------------------------------------------------
  let bannerTimer = 0;
  function showBanner(kind, text, { sticky = false } = {}) {
    cancel(bannerTimer);
    bannerInfo = { kind, text, sticky };
    banner.className = kind === 'error' ? 'bk-banner bk-banner--error' : 'bk-banner';
    banner.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    setText(banner, text);
    banner.hidden = false;
    if (!sticky) bannerTimer = later(clearBanner, BANNER_MS);
  }
  function clearBanner() {
    cancel(bannerTimer);
    bannerInfo = null;
    pollFailed = false;
    banner.hidden = true;
  }

  // --- 목록 렌더 ----------------------------------------------------------------
  function setCount(content) {
    countEl.replaceChildren();
    if (content instanceof Node) countEl.append(content);
    else setText(countEl, content);
  }

  function makeRow(room) {
    const lock = h('span', { class: 'bk-room__lock' });
    const name = h('span', { class: 'bk-room__name', testid: 'room-name' });
    const meta = h('span', { class: 'bk-room__meta', testid: 'room-meta' });
    const countText = h('span', {});
    const count = h('span', { class: 'bk-chip bk-count', testid: 'room-members' }, h('span', { class: 'bk-ico bk-ico--user', 'aria-hidden': 'true' }), countText);
    const goDots = dots();
    goDots.hidden = true;
    const goText = h('span', {});
    const go = h('button', { class: 'bk-btn bk-btn--primary bk-room__go', type: 'button', testid: 'room-enter' }, goDots, goText);
    const li = h('li', { class: 'bk-room', testid: 'room-row', 'data-room-id': room.id },
      lock, h('span', { class: 'bk-room__main' }, name, meta), count, go);
    const row = { li, lock, name, meta, count, countText, go, goDots, goText, room };
    on(go, 'click', () => onEnter(row.room, go));
    return row;
  }

  function updateRow(row, room) {
    row.room = room;
    const full = room.members >= ROOM_CAPACITY;
    const kind = room.locked ? '비밀번호 방' : '공개 방';
    row.li.classList.toggle('is-full', full);
    row.li.dataset.locked = String(room.locked);
    if (room.locked && !row.lock.firstChild) row.lock.append(h('span', { class: 'bk-ico bk-ico--lock', 'aria-hidden': 'true' }));
    else if (!room.locked && row.lock.firstChild) row.lock.replaceChildren();
    setText(row.name, room.name);
    row.name.title = room.name;
    setText(row.meta, `${kind} · ${agoText(room.createdAt)}`);
    setText(row.countText, `${room.members}/${ROOM_CAPACITY}명`);
    row.count.classList.toggle('is-full', full);
    row.count.setAttribute('aria-label', `접속 인원 ${room.members}명, 최대 ${ROOM_CAPACITY}명`);
    const joiningThis = busy && busy.kind === 'join' && busy.roomId === room.id && !modal;
    row.go.classList.toggle('bk-btn--primary', !full);
    row.goDots.hidden = !joiningThis;
    setText(row.goText, full ? '가득 참' : joiningThis ? '입장 중' : '입장');
    row.go.disabled = full || !!busy;
    row.go.setAttribute('aria-label', full ? `${room.name}, 가득 참` : `${room.name} 입장, ${kind}, ${room.members}명 접속 중`);
  }

  function renderSkeleton() {
    list.setAttribute('aria-busy', 'true');
    const skel = () => h('li', { class: 'bk-room is-skel', 'aria-hidden': 'true' },
      h('span', {}), h('span', { class: 'bk-room__main' }, h('span', { class: 'bk-skel bk-skel--name' }), h('span', { class: 'bk-skel bk-skel--meta' })),
      h('span', { class: 'bk-skel bk-skel--count' }), h('span', { class: 'bk-skel bk-skel--btn' }));
    list.replaceChildren(skel(), skel(), skel());
    wrap.replaceChildren(list);
    setCount(dots());
    setText(srStatus, M.LOADING);
  }

  function renderError() {
    const retry = h('button', { class: 'bk-btn bk-btn--primary', type: 'button', testid: 'room-retry' }, '다시 시도');
    on(retry, 'click', () => { clearBanner(); phase = 'loading'; renderSkeleton(); updateTools(); fetchRooms('first'); });
    wrap.replaceChildren(h('div', { class: 'bk-empty bk-empty--error', role: 'alert', testid: 'room-error' },
      h('p', { class: 'bk-empty__title' }, M.NETWORK_FIRST_TITLE),
      h('p', { class: 'bk-empty__text' }, M.NETWORK_FIRST_TEXT),
      retry));
    rows.clear();
    list.replaceChildren();
    setCount('');
  }

  let emptyEl = null;
  function renderRooms() {
    list.setAttribute('aria-busy', 'false');
    setCount(`${rooms.length}개`);
    note.hidden = rooms.length < LIST_LIMIT;
    const ae = document.activeElement;
    const focusInList = ae && list.contains(ae);
    const scrollTop = wrap.scrollTop;

    if (!rooms.length) {
      for (const r of rows.values()) r.li.remove();
      rows.clear();
      if (!emptyEl) {
        const b = h('button', { class: 'bk-btn bk-btn--primary', type: 'button', testid: 'empty-create' }, '방 만들기');
        on(b, 'click', () => openCreate(b));
        emptyEl = h('div', { class: 'bk-empty', testid: 'room-empty' },
          h('span', { class: 'bk-empty__art' }, h('span', { class: 'bk-ico bk-ico--mush', 'aria-hidden': 'true' })),
          h('p', { class: 'bk-empty__title' }, M.EMPTY_TITLE),
          h('p', { class: 'bk-empty__text' }, M.EMPTY_TEXT), b);
        emptyEl._btn = b; // eslint-disable-line no-underscore-dangle
      }
      emptyEl._btn.disabled = !!busy; // eslint-disable-line no-underscore-dangle
      wrap.replaceChildren(emptyEl);
      if (focusInList) title.focus({ preventScroll: true });
      return;
    }
    if (wrap.firstChild !== list || wrap.childNodes.length !== 1) wrap.replaceChildren(list);
    if (list.querySelector('.is-skel')) list.replaceChildren();

    const ids = new Set(rooms.map((r) => r.id));
    let lostFocus = false;
    for (const [id, r] of rows) {
      if (!ids.has(id)) {
        if (r.li.contains(document.activeElement)) lostFocus = true;
        r.li.remove();
        rows.delete(id);
      }
    }
    rooms.forEach((room, i) => {
      let row = rows.get(room.id);
      if (!row) { row = makeRow(room); rows.set(room.id, row); }
      updateRow(row, room);
      if (list.children[i] !== row.li) list.insertBefore(row.li, list.children[i] || null);
    });
    // 순서 변경으로 포커스가 빠졌으면 같은 요소로 되돌린다
    if (focusInList && ae.isConnected && document.activeElement !== ae && !ae.disabled) ae.focus({ preventScroll: true });
    if (lostFocus) title.focus({ preventScroll: true });
    wrap.scrollTop = scrollTop;
  }

  function updateTools() {
    const ready = phase === 'ready';
    const refreshing = busy && busy.kind === 'refresh';
    refreshBtn.disabled = phase === 'loading' || !!busy;
    refreshDots.hidden = !refreshing;
    createBtn.disabled = !ready || !!busy;
    editBtn.disabled = !!busy && busy.kind !== 'refresh';
    for (const row of rows.values()) updateRow(row, row.room);
    if (emptyEl) emptyEl._btn.disabled = !ready || !!busy; // eslint-disable-line no-underscore-dangle
  }

  function setBusy(b) {
    busy = b;
    updateTools();
    if (b && b.kind !== 'refresh') cancel(pollTimer); // 입장/만들기 요청 중에는 폴링을 멈춘다
    else if (!b) schedulePoll();
  }

  // --- 목록 갱신 (3.2) ----------------------------------------------------------
  let pollTimer = 0;
  let fetching = null;
  function schedulePoll() {
    cancel(pollTimer);
    pollTimer = 0;
    if (!alive || phase !== 'ready' || document.visibilityState === 'hidden' || (busy && busy.kind !== 'refresh') || fetching) return;
    pollTimer = later(() => fetchRooms('poll'), LOBBY_POLL_MS);
  }

  /** kind: first | poll | manual | after(오류 뒤 즉시 갱신) */
  function fetchRooms(kind) {
    if (fetching) return kind === 'after' ? fetching.then(() => fetchRooms('poll')) : fetching;
    cancel(pollTimer);
    pollTimer = 0;
    fetching = (async () => {
      try {
        await app.ensureInit();
        const next = await app.backend.listRooms();
        if (!alive) return;
        rooms = Array.isArray(next) ? next.slice(0, LIST_LIMIT) : [];
        phase = 'ready';
        if (pollFailed) clearBanner(); // 갱신 실패 배너는 다음 성공 때 지운다
        renderRooms();
      } catch (err) {
        if (!alive) return;
        if (phase !== 'ready') {
          phase = 'error';
          renderError();
        } else if (kind === 'poll' || kind === 'manual' || kind === 'after') {
          showBanner('error', M.NETWORK_POLL, { sticky: true });
          pollFailed = true; // 다음 성공 때 자동으로 지운다
        }
        void err;
      } finally {
        fetching = null;
        if (alive) { updateTools(); schedulePoll(); }
      }
    })();
    return fetching;
  }

  on(document, 'visibilitychange', () => {
    if (document.visibilityState === 'hidden') { cancel(pollTimer); pollTimer = 0; return; }
    if (phase === 'ready' && !(busy && busy.kind !== 'refresh')) fetchRooms('poll'); // 다시 보이면 즉시 1회 후 사슬 재개
  });

  on(refreshBtn, 'click', async () => {
    if (busy) return; // 연타 무시
    clearBanner();
    setBusy({ kind: 'refresh' });
    const started = performance.now();
    await fetchRooms('manual');
    const rest = REFRESH_MIN_MS - (performance.now() - started);
    if (rest > 0) await new Promise((r) => later(r, rest));
    if (!alive) return;
    setBusy(null);
    if (phase === 'ready' && !pollFailed) setText(srStatus, `방 목록을 새로 고쳤어요. ${rooms.length}개`);
  });

  // --- 입장 (8장) --------------------------------------------------------------
  function enterRoom(room, nickname) {
    writeRoomSession(room.id, nickname);
    alive = false; // 이후 늦게 도착한 응답은 무시
    app.go('room', { roomId: room.id, name: room.name, locked: !!room.locked, nickname });
  }

  /** 모달/행 공통 오류 처리 중 로비 쪽으로 넘기는 것 */
  function lobbyFailure(code) {
    if (code === 'ROOM_FULL' || code === 'ROOM_NOT_FOUND') {
      showBanner('error', M[code]);
      fetchRooms('after');
      return true;
    }
    return false;
  }

  function onEnter(room, btn) {
    if (busy) return;
    clearBanner();
    if (room.locked) { openPassword(room, btn); return; }
    joinPublic(room, btn);
  }

  async function joinPublic(room, btn) {
    setBusy({ kind: 'join', roomId: room.id });
    try {
      await app.backend.joinRoom({ roomId: room.id, password: null, nickname: profile.nickname });
      if (!alive) return;
      enterRoom(room, profile.nickname);
      return;
    } catch (err) {
      if (!alive) return;
      setBusy(null);
      const code = toAppError(err).code;
      if (lobbyFailure(code)) return;
      if (code === 'NICK_TAKEN' || code === 'NICK_FORMAT') { openNick(room, null, btn, code); return; }
      if (code === 'WRONG_PASSWORD') { openPassword(room, btn); return; }
      if (code === 'RATE_LIMITED') { showBanner('error', M.RATE_LIMITED); return; }
      showBanner('error', code === 'NETWORK' ? M.NETWORK_JOIN : M.UNKNOWN);
    }
  }

  // --- 모달 공통 부품 -------------------------------------------------------------
  function field({ label, input, end, help }) {
    const id = `f${++fieldSeq}`;
    input.id = id;
    if (help) { help.id = `${id}-help`; input.setAttribute('aria-describedby', help.id); }
    return h('div', { class: 'bk-field' },
      h('label', { class: 'bk-label-text', for: id }, label),
      h('div', { class: 'bk-input-wrap' }, input, end ? h('span', { class: 'bk-input-end' }, end) : null),
      help);
  }
  function pwToggle(input) {
    const t = h('button', { class: 'bk-link', type: 'button', 'aria-pressed': 'false', 'aria-controls': '', testid: 'pw-toggle' }, '보기');
    on(t, 'click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      t.setAttribute('aria-pressed', String(show));
      setText(t, show ? '숨기기' : '보기');
    });
    queueMicrotask(() => t.setAttribute('aria-controls', input.id));
    return t;
  }
  function setHelp(help, input, kind, text, icon) {
    help.className = kind === 'error' ? 'bk-help bk-help--error' : kind === 'ok' ? 'bk-help bk-help--ok' : 'bk-help';
    help.replaceChildren();
    if (icon) help.append(h('span', { class: `bk-ico ${icon}`, 'aria-hidden': 'true' }), ' ');
    help.append(text);
    if (kind === 'error') input.setAttribute('aria-invalid', 'true');
    else input.removeAttribute('aria-invalid');
  }
  function modalBanner() {
    return h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'modal-banner', hidden: true });
  }
  function primaryBtn(label, testid) {
    const d = dots();
    d.hidden = true;
    const t = h('span', {}, label);
    const b = h('button', { class: 'bk-btn bk-btn--primary', type: 'submit', testid, disabled: true }, d, t);
    return { b, d, t, label };
  }
  /** RATE_LIMITED: 주 버튼 10초 비활성 + "N초 뒤 다시" 카운트다운 */
  function rateLock(pb, ctx) {
    let left = Math.round(RATE_LOCK_MS / 1000);
    ctx.lockedUntil = performance.now() + RATE_LOCK_MS;
    const tick = () => {
      if (!ctx.open) return;
      if (left <= 0) { ctx.lockedUntil = 0; setText(pb.t, pb.label); ctx.refresh(); return; }
      setText(pb.t, `${left}초 뒤 다시`);
      pb.b.disabled = true;
      left--;
      ctx.timer = later(tick, 1000);
    };
    tick();
  }
  const isLocked = (ctx) => ctx.lockedUntil && performance.now() < ctx.lockedUntil;

  function startModal(kind, children, { titleId, descId, initialFocus, returnTo, onCancel, ctx, testid }) {
    const api = openModal({
      main, titleId, descId, children, testid, initialFocus, returnTo,
      fallbackFocus: () => title,
      onCancel,
      canEscape: () => !ctx.busy,
    });
    ctx.open = true;
    modal = { kind, api, ctx };
    return api;
  }
  function endModal(ctx, restoreFocus = true) {
    if (!modal || modal.ctx !== ctx) return;
    ctx.open = false;
    cancel(ctx.timer);
    const m = modal;
    modal = null;
    m.api.close({ restoreFocus });
  }
  function setModalBusy(ctx, pb, busyLabel, inputs, cancelBtn, b) {
    ctx.busy = b;
    for (const i of inputs) i.disabled = b;
    cancelBtn.disabled = b;
    pb.d.hidden = !b;
    setText(pb.t, b ? busyLabel : pb.label);
    if (b) pb.b.disabled = true;
    setBusy(b ? { kind: ctx.busyKind, roomId: ctx.roomId } : null);
    if (!b) ctx.refresh();
  }

  // --- 방 만들기 모달 (7장) -------------------------------------------------------
  function openCreate(returnTo) {
    if (busy) return;
    clearBanner();
    const ctx = { busy: false, busyKind: 'create', open: false, timer: 0, lockedUntil: 0, refresh: () => {} };
    const titleId = `m-title-${++fieldSeq}`;
    const mBanner = modalBanner();
    const nameInput = h('input', { class: 'bk-input bk-input--with-end', type: 'text', maxlength: String(ROOM_NAME_MAX), autocomplete: 'off', testid: 'create-name' });
    const nameCounter = h('span', { class: 'bk-counter', 'aria-hidden': 'true', hidden: true, testid: 'create-name-counter' });
    const nameHelp = h('p', { class: 'bk-help', testid: 'create-name-help' }, '1~24자');
    const pwInput = h('input', { class: 'bk-input bk-input--with-end', type: 'password', maxlength: String(ROOM_PW_MAX), autocomplete: 'new-password', placeholder: '4~32자', testid: 'create-password' });
    const pwHelp = h('p', { class: 'bk-help', testid: 'create-password-help' });
    const toggle = pwToggle(pwInput);
    const cancelBtn = h('button', { class: 'bk-btn', type: 'button', testid: 'modal-cancel' }, '취소');
    const pb = primaryBtn('만들기', 'create-submit-room');
    const form = h('form', { novalidate: true },
      h('div', { class: 'bk-modal__head' }, h('h2', { id: titleId }, '방 만들기')),
      mBanner,
      field({ label: '방 이름', input: nameInput, end: nameCounter, help: nameHelp }),
      field({ label: '비밀번호 (선택)', input: pwInput, end: toggle, help: pwHelp }),
      h('div', { class: 'bk-modal__foot' }, cancelBtn, pb.b));

    let nameTouched = false;
    let nameErrorFromServer = false;
    let pwShowError = false;
    let pwErrorFromServer = false;
    let composing = false;
    const nameState = () => {
      const v = trimWs(nameInput.value);
      if (!v) return 'empty';
      return hasControl(nameInput.value) || charLength(v) > ROOM_NAME_MAX ? 'error' : 'ok';
    };
    const pwState = () => {
      const n = charLength(pwInput.value);
      if (n === 0) return 'empty';
      return n >= ROOM_PW_MIN && n <= ROOM_PW_MAX ? 'ok' : 'error';
    };
    ctx.refresh = () => {
      const ns = nameState();
      const n = charLength(trimWs(nameInput.value));
      nameCounter.hidden = !nameTouched;
      setText(nameCounter, `${n}/${ROOM_NAME_MAX}`);
      if (nameErrorFromServer || ns === 'error') setHelp(nameHelp, nameInput, 'error', M.ROOM_NAME_FORMAT);
      else setHelp(nameHelp, nameInput, 'help', '1~24자');
      const ps = pwState();
      if (ps === 'error' && (pwShowError || pwErrorFromServer)) setHelp(pwHelp, pwInput, 'error', M.PASSWORD_FORMAT);
      else if (ps === 'ok') setHelp(pwHelp, pwInput, 'help', M.PW_HELP_SET, 'bk-ico--lock');
      else if (pwErrorFromServer) setHelp(pwHelp, pwInput, 'error', M.PASSWORD_FORMAT);
      else setHelp(pwHelp, pwInput, 'help', M.PW_HELP_EMPTY);
      if (!ctx.busy && !isLocked(ctx)) pb.b.disabled = !(ns === 'ok' && !nameErrorFromServer && ps !== 'error');
    };
    on(nameInput, 'compositionstart', () => { composing = true; });
    on(nameInput, 'compositionend', () => { composing = false; ctx.refresh(); });
    on(nameInput, 'input', () => { nameTouched = true; nameErrorFromServer = false; if (!composing) ctx.refresh(); else { nameCounter.hidden = false; setText(nameCounter, `${charLength(trimWs(nameInput.value))}/${ROOM_NAME_MAX}`); } });
    on(pwInput, 'input', () => { pwErrorFromServer = false; ctx.refresh(); });
    on(pwInput, 'blur', () => { if (pwState() === 'error') { pwShowError = true; ctx.refresh(); } });
    const close = (restore = true) => endModal(ctx, restore);
    on(cancelBtn, 'click', () => close());
    on(form, 'submit', async (e) => {
      e.preventDefault();
      if (ctx.busy || isLocked(ctx) || composing) return;
      if (pwState() === 'error') { pwShowError = true; ctx.refresh(); pwInput.focus(); return; }
      const name = cleanRoomName(nameInput.value);
      if (name === null) { ctx.refresh(); nameInput.focus(); return; }
      mBanner.hidden = true;
      const pw = pwInput.value;
      setModalBusy(ctx, pb, '만드는 중', [nameInput, pwInput, toggle], cancelBtn, true);
      try {
        const { roomId } = await app.backend.createRoom({ name, password: pw || null, nickname: profile.nickname });
        if (!ctx.open) return;
        close(false);
        enterRoom({ id: roomId, name, locked: !!pw }, profile.nickname);
      } catch (err) {
        if (!ctx.open) return;
        const code = toAppError(err).code;
        setModalBusy(ctx, pb, '만드는 중', [nameInput, pwInput, toggle], cancelBtn, false);
        if (code === 'ROOM_NAME_FORMAT') { nameErrorFromServer = true; ctx.refresh(); nameInput.focus(); return; }
        if (code === 'PASSWORD_FORMAT') { pwErrorFromServer = true; ctx.refresh(); pwInput.focus(); return; }
        const text = code === 'TOO_MANY_ROOMS' ? M.TOO_MANY_ROOMS
          : code === 'RATE_LIMITED' ? M.RATE_LIMITED
            : code === 'NETWORK' ? M.NETWORK_CREATE
              : code === 'NICK_FORMAT' ? M.NICK_FORMAT : M.UNKNOWN;
        setText(mBanner, text);
        mBanner.hidden = false;
        if (code === 'RATE_LIMITED') rateLock(pb, ctx);
      }
    });
    on(form, 'keydown', (e) => { if (e.key === 'Enter' && (e.isComposing || e.keyCode === 229)) e.preventDefault(); });
    startModal('create', [form], { titleId, ctx, returnTo, onCancel: () => close(), initialFocus: () => nameInput, testid: 'modal-create' });
    ctx.refresh();
  }

  // --- 비밀번호 모달 (8.2) --------------------------------------------------------
  function openPassword(room, returnTo, { error = null } = {}) {
    const ctx = { busy: false, busyKind: 'join', roomId: room.id, open: false, timer: 0, lockedUntil: 0, refresh: () => {} };
    const titleId = `m-title-${++fieldSeq}`;
    const roomLineId = `m-room-${fieldSeq}`;
    const mBanner = modalBanner();
    const pwInput = h('input', { class: 'bk-input bk-input--with-end', type: 'password', maxlength: String(ROOM_PW_MAX), autocomplete: 'off', testid: 'join-password' });
    const pwHelp = h('p', { class: 'bk-help pw-help-slot', testid: 'join-password-help' });
    const toggle = pwToggle(pwInput);
    const cancelBtn = h('button', { class: 'bk-btn', type: 'button', testid: 'modal-cancel' }, '취소');
    const pb = primaryBtn('입장', 'join-submit');
    const form = h('form', { novalidate: true },
      h('div', { class: 'bk-modal__head' }, h('h2', { id: titleId }, '비밀번호 입력')),
      h('p', { class: 'bk-modal__room', id: roomLineId }, h('span', { class: 'bk-ico bk-ico--lock', 'aria-hidden': 'true' }), h('b', { testid: 'modal-room-name' }, room.name)),
      mBanner,
      field({ label: '비밀번호', input: pwInput, end: toggle, help: pwHelp }),
      h('div', { class: 'bk-modal__foot' }, cancelBtn, pb.b));
    let wrong = error === 'WRONG_PASSWORD';
    ctx.refresh = () => {
      if (wrong) setHelp(pwHelp, pwInput, 'error', M.WRONG_PASSWORD);
      else setHelp(pwHelp, pwInput, 'help', '');
      if (!ctx.busy && !isLocked(ctx)) pb.b.disabled = pwInput.value.length < 1; // 형식 검사는 서버
    };
    on(pwInput, 'input', () => ctx.refresh());
    const close = (restore = true) => endModal(ctx, restore);
    on(cancelBtn, 'click', () => close());
    on(form, 'submit', async (e) => {
      e.preventDefault();
      if (ctx.busy || isLocked(ctx) || !pwInput.value) return;
      mBanner.hidden = true;
      const pw = pwInput.value;
      setModalBusy(ctx, pb, '입장 중', [pwInput, toggle], cancelBtn, true);
      try {
        await app.backend.joinRoom({ roomId: room.id, password: pw, nickname: profile.nickname });
        if (!ctx.open) return;
        close(false);
        enterRoom(room, profile.nickname);
      } catch (err) {
        if (!ctx.open) return;
        const code = toAppError(err).code;
        setModalBusy(ctx, pb, '입장 중', [pwInput, toggle], cancelBtn, false);
        if (code === 'WRONG_PASSWORD') {
          wrong = true;
          pwInput.value = '';
          ctx.refresh();
          pwInput.focus();
          return;
        }
        if (code === 'ROOM_FULL' || code === 'ROOM_NOT_FOUND') { close(); lobbyFailure(code); return; }
        if (code === 'NICK_TAKEN' || code === 'NICK_FORMAT') { close(false); openNick(room, pw, returnTo, code); return; }
        setText(mBanner, code === 'RATE_LIMITED' ? M.RATE_LIMITED : code === 'NETWORK' ? M.NETWORK_JOIN : M.UNKNOWN);
        mBanner.hidden = false;
        if (code === 'RATE_LIMITED') rateLock(pb, ctx);
      }
    });
    startModal('password', [form], { titleId, descId: roomLineId, ctx, returnTo, onCancel: () => close(), initialFocus: () => pwInput, testid: 'modal-password' });
    ctx.refresh();
  }

  // --- 닉네임 겹침 모달 (8.4) -----------------------------------------------------
  function openNick(room, password, returnTo, code = 'NICK_TAKEN') {
    let storedPw = password; // 입력한 비밀번호는 메모리에만 보관해 재시도에 쓴다
    const ctx = { busy: false, busyKind: 'join', roomId: room.id, open: false, timer: 0, lockedUntil: 0, refresh: () => {} };
    const titleId = `m-title-${++fieldSeq}`;
    const descId = `m-desc-${fieldSeq}`;
    const mBanner = modalBanner();
    const nickInput = h('input', {
      class: 'bk-input bk-input--with-end', type: 'text', maxlength: String(NICK_MAX), autocomplete: 'off', autocapitalize: 'off',
      spellcheck: 'false', enterkeyhint: 'done', testid: 'room-nick-input',
    });
    nickInput.value = suggestNick(profile.nickname);
    const counter = h('span', { class: 'bk-counter', 'aria-hidden': 'true' });
    const help = h('p', { class: 'bk-help nick-status', testid: 'room-nick-status', 'aria-live': 'polite' });
    const cancelBtn = h('button', { class: 'bk-btn', type: 'button', testid: 'modal-cancel' }, '취소');
    const pb = primaryBtn('입장', 'room-nick-submit');
    const form = h('form', { novalidate: true },
      h('div', { class: 'bk-modal__head' }, h('h2', { id: titleId }, M.NICK_TAKEN_TITLE)),
      h('p', { class: 'bk-modal__desc', id: descId }, M.NICK_TAKEN_DESC),
      mBanner,
      field({ label: '이 방에서 쓸 닉네임', input: nickInput, end: counter, help }),
      h('div', { class: 'bk-modal__foot' }, cancelBtn, pb.b));
    let taken = false;
    let formatShown = code === 'NICK_FORMAT';
    let composing = false;
    ctx.refresh = () => {
      const v = trimWs(nickInput.value);
      setText(counter, `${charLength(nickInput.value)}/${NICK_MAX}`);
      counter.hidden = !nickInput.value;
      const ok = NICK_RE.test(v);
      if (taken) setHelp(help, nickInput, 'error', M.NICK_TAKEN_AGAIN);
      else if (ok) setHelp(help, nickInput, 'ok', PM.OK, 'bk-ico--check');
      else if (formatShown || charLength(v) >= 2) { formatShown = true; setHelp(help, nickInput, 'error', M.NICK_FORMAT); }
      else setHelp(help, nickInput, 'help', PM.HELP);
      help.dataset.state = taken ? 'taken' : ok ? 'ok' : formatShown ? 'format' : 'empty';
      if (!ctx.busy && !isLocked(ctx)) pb.b.disabled = !ok || taken;
    };
    on(nickInput, 'compositionstart', () => { composing = true; });
    on(nickInput, 'compositionend', () => { composing = false; taken = false; ctx.refresh(); });
    on(nickInput, 'input', () => { if (composing) return; taken = false; ctx.refresh(); });
    on(nickInput, 'blur', () => { if (trimWs(nickInput.value) && !NICK_RE.test(trimWs(nickInput.value))) { formatShown = true; ctx.refresh(); } });
    const close = (restore = true) => { storedPw = null; endModal(ctx, restore); };
    on(cancelBtn, 'click', () => close());
    on(form, 'submit', async (e) => {
      e.preventDefault();
      const nickname = trimWs(nickInput.value);
      if (ctx.busy || isLocked(ctx) || composing || !NICK_RE.test(nickname) || taken) return;
      mBanner.hidden = true;
      setModalBusy(ctx, pb, '입장 중', [nickInput], cancelBtn, true);
      try {
        await app.backend.joinRoom({ roomId: room.id, password: storedPw || null, nickname });
        if (!ctx.open) return;
        close(false);
        enterRoom(room, nickname); // 프로필은 그대로, 방 닉네임은 sessionStorage에만
      } catch (err) {
        if (!ctx.open) return;
        const c = toAppError(err).code;
        setModalBusy(ctx, pb, '입장 중', [nickInput], cancelBtn, false);
        if (c === 'NICK_TAKEN') { taken = true; ctx.refresh(); nickInput.focus(); nickInput.select(); return; }
        if (c === 'NICK_FORMAT') { formatShown = true; ctx.refresh(); nickInput.focus(); return; }
        if (c === 'WRONG_PASSWORD') { close(false); openPassword(room, returnTo, { error: 'WRONG_PASSWORD' }); return; }
        if (c === 'ROOM_FULL' || c === 'ROOM_NOT_FOUND') { close(); lobbyFailure(c); return; }
        setText(mBanner, c === 'RATE_LIMITED' ? M.RATE_LIMITED : c === 'NETWORK' ? M.NETWORK_JOIN : M.UNKNOWN);
        mBanner.hidden = false;
        if (c === 'RATE_LIMITED') rateLock(pb, ctx);
      }
    });
    startModal('nick', [form], {
      titleId, descId, ctx, returnTo, onCancel: () => close(), testid: 'modal-nick',
      initialFocus: () => { queueMicrotask(() => nickInput.select()); return nickInput; },
    });
    ctx.refresh();
  }

  // --- 머리줄 동작 ----------------------------------------------------------------
  on(editBtn, 'click', () => { if (!busy) { alive = false; app.go('profile', { mode: 'edit' }); } });
  on(createBtn, 'click', () => openCreate(createBtn));

  // 내 캐릭터 미니 썸네일 (style-guide 11.6)
  let renderer = null;
  app.assets.then((assets) => {
    if (!alive || !assets || assets.source !== 'manifest') return;
    const av = assets.sanitizeAvatar(profile.avatar);
    const paint = () => {
      const src = renderer && renderer.thumb(av, PART_KEYS); // 합성 중이면 null → onUpdate에서 다시
      if (!src) return;
      const c = thumb.getContext('2d');
      smooth(c);
      c.clearRect(0, 0, thumb.width, thumb.height);
      c.drawImage(src, THUMB_CROP.x, THUMB_CROP.y, THUMB_CROP.size, THUMB_CROP.size, 0, 0, thumb.width, thumb.height);
    };
    renderer = createAvatarRenderer(assets, { onUpdate: () => { if (alive) paint(); } });
    paint();
  }, () => {});

  // --- 테스트 훅 ------------------------------------------------------------------
  app.providers.lobby = () => ({
    lobby: {
      state: phase,
      busy: busy ? busy.kind : null,
      banner: bannerInfo ? { kind: bannerInfo.kind, text: bannerInfo.text } : null,
      modal: modal ? modal.kind : null,
      count: rooms.length,
    },
    rooms: rooms.map((r) => ({ id: r.id, name: r.name, locked: !!r.locked, members: r.members, createdAt: r.createdAt })),
  });

  // --- 시작 -----------------------------------------------------------------------
  renderSkeleton();
  updateTools();
  if (opts.banner === 'REJOIN_FAILED') showBanner('error', M.REJOIN_FAILED);
  else if (app.storageFailed) { app.storageFailed = false; showBanner('info', M.STORAGE); }
  fetchRooms('first');
  if (opts.focus === 'edit') editBtn.focus({ preventScroll: true });
  else title.focus({ preventScroll: true });

  return {
    unmount() {
      alive = false;
      if (modal) { modal.ctx.open = false; modal.api.close({ restoreFocus: false }); modal = null; }
      ac.abort();
      for (const t of timers) clearTimeout(t);
      timers.clear();
      renderer?.clear();
      if (app.providers.lobby) app.providers.lobby = null;
    },
  };
}
