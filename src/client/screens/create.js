// 캐릭터 생성 화면 (docs/design/screens/character-create.md)
import { h, setText } from '../dom.js';
import { COLORS, NICK_RE, NICK_DEBOUNCE_MS, PART_KEYS, PART_LABELS, PART_ARIA, MOBILE_MAX_WIDTH } from '../constants.js';
import { CREATE_MESSAGES as M, toAppError } from '../errors.js';
import { createAvatarRenderer } from '../avatar.js';

const ROW_ORDER = ['skin', 'hair', 'eyes', 'top', 'bottom'];

export function mount(root, app) {
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;
  let assets = null;
  let renderer = null;
  let avatar = null;
  let creating = false;
  let debounceTimer = 0;
  let checkSeq = 0;
  let pendingCheck = null; // Promise of current check
  let composing = false;
  // nick: { value, status: 'empty'|'format'|'unchecked'|'checking'|'available'|'taken'|'failed' }
  const nick = { value: '', status: 'empty', checkedValue: null };

  // --- 요소 ---------------------------------------------------------------
  const logoutBtn = h('button', { type: 'button', class: 'link-btn', testid: 'logout' }, '로그아웃');
  const banner = h('div', { class: 'banner banner-error', role: 'alert', testid: 'error-message', hidden: true });
  const previewCanvas = h('canvas', { class: 'preview-canvas', 'aria-hidden': 'true' });
  const preview = h('div', { class: 'preview', 'aria-hidden': 'true', testid: 'avatar-preview' }, previewCanvas);

  const nickInput = h('input', {
    id: 'nickname', class: 'input', type: 'text', testid: 'nickname-input', maxlength: '12', autocomplete: 'off',
    spellcheck: 'false', 'aria-describedby': 'nickname-status',
  });
  const statusIcon = h('span', { class: 'status-icon', 'aria-hidden': 'true' });
  const statusText = h('span', {});
  const status = h('p', { id: 'nickname-status', class: 'nick-status', testid: 'nickname-status', 'aria-live': 'polite' }, statusIcon, statusText);

  const submitLabel = h('span', {}, '캐릭터 만들기');
  const spinner = h('span', { class: 'spinner', 'aria-hidden': 'true', hidden: true });
  const submit = h('button', { type: 'button', class: 'btn btn-primary create-submit', testid: 'create-submit', disabled: true }, spinner, submitLabel);
  const live = h('div', { class: 'sr-only', 'aria-live': 'polite' });

  const rows = {};
  const rowEls = ROW_ORDER.map((part) => {
    const labelId = `part-label-${part}`;
    const prev = h('button', { type: 'button', class: 'icon-btn', testid: `part-prev-${part}`, 'aria-label': `이전 ${PART_ARIA[part]}` }, '◀');
    const next = h('button', { type: 'button', class: 'icon-btn', testid: `part-next-${part}`, 'aria-label': `다음 ${PART_ARIA[part]}` }, '▶');
    const value = h('span', { class: 'part-value-text', testid: `part-value-${part}` });
    const index = h('span', { class: 'part-index' });
    const row = h('div', { class: 'part-row', role: 'group', 'aria-labelledby': labelId, testid: `part-row-${part}` },
      h('span', { class: 'part-label', id: labelId }, PART_LABELS[part]),
      prev,
      h('div', { class: 'part-value' }, value, index),
      next);
    rows[part] = { prev, next, value, index, row };
    return row;
  });

  const card = h('main', { class: 'card create-card' },
    h('div', { class: 'create-header' }, h('h1', { class: 'title' }, '캐릭터 만들기'), logoutBtn),
    banner,
    h('div', { class: 'create-grid' },
      h('div', { class: 'area-preview' }, preview),
      h('div', { class: 'area-nick field' },
        h('label', { for: 'nickname', class: 'label' }, '닉네임'),
        nickInput,
        status),
      h('div', { class: 'area-parts' }, rowEls),
      h('div', { class: 'area-submit' }, submit)),
    live);
  root.append(card);

  // --- 미리보기 -------------------------------------------------------------
  function drawPreview() {
    if (!renderer || !avatar) return;
    const rect = preview.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width));
    const hh = Math.max(1, Math.round(rect.height));
    const dpr = window.devicePixelRatio || 1;
    if (previewCanvas.width !== Math.round(w * dpr) || previewCanvas.height !== Math.round(hh * dpr)) {
      previewCanvas.width = Math.round(w * dpr);
      previewCanvas.height = Math.round(hh * dpr);
    }
    const c = previewCanvas.getContext('2d');
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, hh);
    const g = c.createLinearGradient(0, 0, 0, hh);
    g.addColorStop(0, COLORS.skyTop);
    g.addColorStop(1, COLORS.skyBottom);
    c.fillStyle = g;
    c.fillRect(0, 0, w, hh);
    c.fillStyle = COLORS.grass;
    c.fillRect(0, hh - 40, w, 40);
    c.fillStyle = COLORS.grassLight;
    c.fillRect(0, hh - 40, w, 1);
    const mobile = (document.documentElement.clientWidth || window.innerWidth) < MOBILE_MAX_WIDTH;
    const scale = mobile ? 2.5 : 3;
    const footY = hh - (mobile ? 20 : 24);
    renderer.draw(c, avatar, w / 2, footY, scale, dpr, false);
  }

  function renderRows() {
    for (const part of ROW_ORDER) {
      const list = assets.parts[part];
      const i = Math.max(0, list.findIndex((o) => o.id === avatar[part]));
      setText(rows[part].value, list[i].label);
      rows[part].value.title = list[i].label;
      setText(rows[part].index, `${i + 1} / ${list.length}`);
    }
  }

  function step(part, delta) {
    if (creating || !assets) return;
    const list = assets.parts[part];
    let i = list.findIndex((o) => o.id === avatar[part]);
    i = (i + delta + list.length) % list.length; // 순환
    avatar = { ...avatar, [part]: list[i].id };
    renderRows();
    drawPreview();
    setText(live, `${PART_LABELS[part]}: ${list[i].label}`);
  }

  // --- 닉네임 상태 -----------------------------------------------------------
  const STATUS = {
    empty: { cls: 'muted', text: M.HELP },
    format: { cls: 'error', text: M.NICK_FORMAT },
    unchecked: { cls: 'muted', text: M.UNCHECKED },
    checking: { cls: 'muted', text: M.CHECKING, spin: true },
    available: { cls: 'success', text: M.AVAILABLE, icon: '✓' },
    taken: { cls: 'error', text: M.NICK_TAKEN },
    failed: { cls: 'error', text: M.NICK_CHECK_FAILED },
  };

  function setStatus(s) {
    nick.status = s;
    const d = STATUS[s];
    status.className = `nick-status ${d.cls}`;
    status.dataset.state = s;
    setText(statusText, d.text);
    statusIcon.className = d.spin ? 'status-icon spinner spinner-sm' : 'status-icon';
    setText(statusIcon, d.icon || '');
    statusIcon.hidden = !d.spin && !d.icon;
    const invalid = s === 'format' || s === 'taken';
    nickInput.classList.toggle('is-invalid', invalid);
    nickInput.classList.toggle('is-valid', s === 'available');
    if (invalid) nickInput.setAttribute('aria-invalid', 'true');
    else nickInput.removeAttribute('aria-invalid');
    updateSubmit();
  }

  function updateSubmit() {
    submit.disabled = creating || !assets || !['unchecked', 'checking', 'available'].includes(nick.status);
  }

  function evaluate() {
    const v = nickInput.value.trim();
    nick.value = v;
    clearTimeout(debounceTimer);
    checkSeq++; // 진행 중인 확인 결과는 버린다(이전 결과를 재사용하지 않음)
    pendingCheck = null;
    if (!v) return setStatus('empty');
    if (!NICK_RE.test(v)) return setStatus(composing ? 'unchecked' : 'format');
    setStatus('unchecked');
    debounceTimer = setTimeout(() => { if (!composing) runCheck(); }, NICK_DEBOUNCE_MS);
  }

  function runCheck() {
    const v = nick.value;
    if (!NICK_RE.test(v)) return Promise.resolve();
    const seq = ++checkSeq;
    clearTimeout(debounceTimer);
    setStatus('checking');
    const p = (async () => {
      try {
        const taken = await app.backend.isNicknameTaken(v);
        if (!alive || seq !== checkSeq) return;
        nick.checkedValue = v;
        setStatus(taken ? 'taken' : 'available');
      } catch (err) {
        if (!alive || seq !== checkSeq) return;
        if (toAppError(err).code === 'AUTH_REQUIRED') { app.forceLogout('SERVER'); return; }
        setStatus('failed');
      }
    })();
    pendingCheck = p;
    return p;
  }

  // --- 생성 -----------------------------------------------------------------
  function setCreating(b) {
    creating = b;
    nickInput.disabled = b;
    logoutBtn.disabled = b;
    for (const part of ROW_ORDER) { rows[part].prev.disabled = b; rows[part].next.disabled = b; }
    spinner.hidden = !b;
    setText(submitLabel, b ? '만드는 중...' : '캐릭터 만들기');
    updateSubmit();
  }

  async function doCreate() {
    if (creating || submit.disabled) return;
    banner.hidden = true;
    if (nick.status === 'checking' && pendingCheck) await pendingCheck;
    if (!alive) return;
    if (nick.status === 'unchecked') await runCheck();
    if (!alive || nick.status !== 'available') return;
    setCreating(true);
    try {
      const ch = await app.backend.createCharacter(nick.value, { ...avatar });
      if (!alive) return;
      app.character = ch;
      submit.disabled = true;
      await app.go('game');
    } catch (err) {
      if (!alive) return;
      const e = toAppError(err);
      setCreating(false);
      switch (e.code) {
        case 'NICK_TAKEN':
          setStatus('taken');
          break;
        case 'NICK_FORMAT':
          setStatus('format');
          break;
        case 'CHAR_EXISTS':
          try {
            const ch = await app.backend.getMyCharacter();
            if (!alive) return;
            if (ch) { app.character = ch; await app.go('game'); return; }
          } catch { /* 아래 배너 */ }
          showBanner('SERVER');
          break;
        case 'AUTH_REQUIRED':
          app.forceLogout('SERVER');
          break;
        case 'NETWORK':
          showBanner('NETWORK');
          break;
        default:
          showBanner('SERVER');
      }
    }
  }

  function showBanner(code) {
    setText(banner, M[code] || M.SERVER);
    banner.hidden = false;
  }

  // --- 이벤트 -------------------------------------------------------------
  on(nickInput, 'compositionstart', () => { composing = true; });
  on(nickInput, 'compositionend', () => { composing = false; evaluate(); });
  on(nickInput, 'input', () => evaluate());
  on(nickInput, 'blur', () => {
    if (nick.status === 'unchecked' || nick.status === 'failed' || (nick.status === 'format' && NICK_RE.test(nickInput.value.trim()))) {
      composing = false;
      if (nick.value !== nickInput.value.trim()) evaluate();
      if (NICK_RE.test(nick.value)) runCheck();
    }
  });
  on(nickInput, 'keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.isComposing || e.keyCode === 229) return;
      doCreate();
    }
  });
  for (const part of ROW_ORDER) {
    on(rows[part].prev, 'click', () => step(part, -1));
    on(rows[part].next, 'click', () => step(part, 1));
    on(rows[part].row, 'keydown', (e) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); step(part, -1); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); step(part, 1); }
    });
  }
  on(submit, 'click', () => doCreate());
  on(logoutBtn, 'click', () => { if (!creating) app.forceLogout(); });
  const ro = new ResizeObserver(() => drawPreview());
  ro.observe(preview);

  setStatus('empty');
  for (const part of ROW_ORDER) { rows[part].prev.disabled = true; rows[part].next.disabled = true; }

  app.assets.then((a) => {
    if (!alive) return;
    assets = a;
    renderer = createAvatarRenderer(a);
    avatar = { ...a.defaultAvatar };
    for (const part of PART_KEYS) { rows[part].prev.disabled = false; rows[part].next.disabled = false; }
    renderRows();
    drawPreview();
    updateSubmit();
  }, () => {
    if (alive) showBanner('SERVER');
  });
  nickInput.focus();

  return {
    unmount() {
      alive = false;
      clearTimeout(debounceTimer);
      ro.disconnect();
      ac.abort();
      renderer?.clear();
    },
  };
}
