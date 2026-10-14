// 캐릭터 생성 화면 (docs/design/screens/character-create.md v3.0, style-guide v3 5.12~5.14)
// - 카테고리 탭 7개 + 아이템 슬롯 그리드(썸네일) + 프리셋 + 회전 미리보기(앞/옆/뒤 + 걷기) + 닉네임.
// - 탭/슬롯/프리셋은 assets/avatar/manifest.json 의 parts/presets 로만 만든다(하드코딩 없음).
// - 저장 값은 항상 정확히 7개 키 (skin, hair, face, top, bottom, shoes, hat).
import { h, setText } from '../dom.js';
import { PAL, NICK_RE, NICK_DEBOUNCE_MS, PART_KEYS, CATEGORY_ORDER, PART_LABELS, HAT_NONE } from '../constants.js';
import { CREATE_MESSAGES as M, toAppError } from '../errors.js';
import { createAvatarRenderer, makeCanvas } from '../avatar.js';
import { drawFootShadow } from '../game/world.js';
import { pickAvatar } from '../avatar-data.js';

const MANIFEST_MSG = '파츠 정보를 불러오지 못했습니다. 새로고침해 주세요.';

// 미리보기 무대 (style-guide 5.14): 아트 56x72, 프레임 왼쪽 위 (4,4) → 기준점 (28,64), 잔디 윗면 첫 행 62
const STAGE = Object.freeze({ w: 56, h: 72, ax: 28, ay: 64, grassTop: 62 });
const SKY_BANDS = [[PAL.k3, 0, 24], [PAL.k4, 24, 44], [PAL.k5, 44, 62]];

// 슬롯 썸네일 (style-guide 5.12 표): 합성할 파츠와 자르기 왼쪽 위 (40x40 영역)
const THUMB = Object.freeze({
  skin: { parts: ['skin', 'face'], x: 4, y: 10 },
  face: { parts: ['skin', 'face'], x: 4, y: 10 },
  hair: { parts: ['skin', 'face', 'hair'], x: 4, y: 10 },
  hat: { parts: ['skin', 'face', 'hair', 'hat'], x: 4, y: 6 },
  top: { parts: ['skin', 'face', 'top'], x: 4, y: 24 },
  bottom: { parts: ['skin', 'face', 'bottom'], x: 4, y: 24 },
  shoes: { parts: ['skin', 'face', 'shoes'], x: 4, y: 24 },
});
const THUMB_SIZE = 40;
const PRESET_CROP = Object.freeze({ x: 4, y: 6 });
const VIEWS = Object.freeze([['front', '앞'], ['side', '옆'], ['back', '뒤']]);

export function mount(root, app) {
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;
  let assets = null;
  let renderer = null;
  let avatar = null;
  let ready = false;
  let creating = false;
  let debounceTimer = 0;
  let checkSeq = 0;
  let pendingCheck = null;
  let composing = false;
  let activeTab = 'hair'; // 첫 진입 = 머리 (5.1)
  let view = 'front'; // front | side | back
  let walking = false;
  let walkStart = 0;
  let raf = 0;
  const nick = { value: '', status: 'empty', checkedValue: null };

  // --- 요소 ---------------------------------------------------------------
  const logoutBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--sm', testid: 'logout' }, '로그아웃');
  const banner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'error-message', hidden: true });

  // 미리보기
  const stageCanvas = h('canvas', { width: String(STAGE.w), height: String(STAGE.h), 'aria-hidden': 'true' });
  const stageDots = h('span', { class: 'bk-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const previewEl = h('div', { class: 'bk-preview', testid: 'avatar-preview' },
    h('div', { class: 'bk-well' }, h('div', { class: 'bk-preview__stage' }, stageCanvas, stageDots)));
  const viewBtns = {};
  for (const [key, label] of VIEWS) {
    viewBtns[key] = h('button', {
      type: 'button', class: 'bk-btn', role: 'radio', 'aria-checked': String(key === view), testid: `view-${key}`,
      tabindex: key === view ? '0' : '-1', 'aria-label': `미리보기 ${label}모습`,
    }, label);
  }
  const viewGroup = h('div', { class: 'bk-tabs', role: 'radiogroup', 'aria-label': '미리보기 방향' }, VIEWS.map(([k]) => viewBtns[k]));
  const walkBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--latch', testid: 'preview-walk', 'aria-pressed': 'false' },
    h('span', { class: 'bk-ico bk-ico--arrow', 'aria-hidden': 'true' }), '걷기');
  const prevArea = h('div', { class: 'create-prev create-left' }, previewEl, h('div', { class: 'bk-preview__ctrl' }, viewGroup, walkBtn));

  // 프리셋, 탭, 슬롯
  const presetGrid = h('div', { class: 'bk-presets', role: 'group', 'aria-label': '추천 조합' });
  const tabBtns = {};
  for (const part of CATEGORY_ORDER) {
    tabBtns[part] = h('button', {
      type: 'button', class: 'bk-btn', role: 'tab', id: `tab-${part}`, testid: `tab-${part}`,
      'aria-selected': String(part === activeTab), 'aria-controls': 'slot-grid', tabindex: part === activeTab ? '0' : '-1', disabled: true,
    }, PART_LABELS[part]);
  }
  const tabList = h('div', { class: 'bk-tabs bk-tabs--cat', role: 'tablist', 'aria-label': '꾸미기 항목' }, CATEGORY_ORDER.map((p) => tabBtns[p]));
  const slotGrid = h('div', { class: 'bk-slots', role: 'radiogroup', id: 'slot-grid', testid: 'slot-grid', 'aria-labelledby': `tab-${activeTab}` });
  const currentLine = h('p', { class: 'bk-help', testid: 'current-part', 'aria-live': 'polite' });
  const partsBanner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'manifest-error', hidden: true }, MANIFEST_MSG);
  const partsBody = h('div', {},
    h('h2', { class: 'section-title' }, '추천 조합'), presetGrid,
    h('h2', { class: 'section-title' }, '꾸미기'), tabList, slotGrid, currentLine);
  const partsArea = h('div', { class: 'create-parts' }, partsBanner, partsBody);

  // 닉네임
  const nickInput = h('input', {
    id: 'nickname', class: 'bk-input', type: 'text', testid: 'nickname-input', maxlength: '12', autocomplete: 'off',
    spellcheck: 'false', 'aria-describedby': 'nickname-status',
  });
  const statusIcon = h('span', { class: 'status-icon', 'aria-hidden': 'true', hidden: true });
  const statusText = h('span', {});
  const status = h('p', { id: 'nickname-status', class: 'bk-help nick-status', testid: 'nickname-status', 'aria-live': 'polite' }, statusIcon, statusText);
  const nickArea = h('div', { class: 'create-nick bk-field' },
    h('label', { for: 'nickname', class: 'bk-label-text' }, '닉네임'),
    h('div', { class: 'bk-input-wrap' }, nickInput),
    status);

  const submitLabel = h('span', {}, '캐릭터 만들기');
  const spinner = h('span', { class: 'bk-dots', 'aria-hidden': 'true', hidden: true }, h('i'), h('i'), h('i'));
  const submit = h('button', { type: 'button', class: 'bk-btn bk-btn--primary bk-btn--block', testid: 'create-submit', disabled: true }, spinner, submitLabel);
  const ctaArea = h('div', { class: 'create-cta' }, submit);

  const modeSlot = h('span', { class: 'mode-slot' });
  const modeRow = app.mode === 'local'
    ? h('div', { class: 'card-foot' }, modeSlot, h('span', {}, '이 브라우저에만 저장됩니다'))
    : null;
  const card = h('section', { class: 'bk-panel card-create' },
    h('div', { class: 'card-head' }, h('h1', {}, '캐릭터 만들기'), logoutBtn),
    banner,
    h('div', { class: 'create-grid' }, prevArea, partsArea, nickArea, ctaArea),
    modeRow);
  root.append(h('main', { class: 'scr-auth' }, card));
  if (modeRow) app.placeModeBadge(modeSlot);

  // --- 미리보기 그리기 ---------------------------------------------------------
  const art = makeCanvas(STAGE.w, STAGE.h);
  const actx = art.getContext('2d');
  let map = null;
  let pv = 4;
  let dpr = 1;

  function sizeStage() {
    const v = parseInt(getComputedStyle(previewEl).getPropertyValue('--pv'), 10);
    pv = Number.isInteger(v) && v > 0 ? v : 4;
    dpr = Math.max(1, Math.min(3, Math.round(window.devicePixelRatio || 1)));
    const w = STAGE.w * pv * dpr;
    const hgt = STAGE.h * pv * dpr;
    if (stageCanvas.width !== w || stageCanvas.height !== hgt) { stageCanvas.width = w; stageCanvas.height = hgt; }
  }

  function drawStageBg() {
    const c = actx;
    for (const [col, y0, y1] of SKY_BANDS) { c.fillStyle = col; c.fillRect(0, y0, STAGE.w, y1 - y0); }
    if (map && map.groundImg) {
      // 지면 레이어의 잔디 윗면 첫 행(아트 y 218 → 레이어 이미지 y 218 - layer.y)부터 10행을 무대 y 62에 깐다
      const sy = 218 - map.groundLayerY;
      c.drawImage(map.groundImg, 0, sy, STAGE.w, STAGE.h - STAGE.grassTop, 0, STAGE.grassTop, STAGE.w, STAGE.h - STAGE.grassTop);
    } else {
      c.fillStyle = PAL.g1; c.fillRect(0, 62, STAGE.w, 2);
      c.fillStyle = PAL.g2; c.fillRect(0, 64, STAGE.w, 2);
      c.fillStyle = PAL.w3; c.fillRect(0, 66, STAGE.w, 6);
    }
  }

  function previewFrame(now) {
    if (walking) return renderer.frameAt('walk', now - walkStart);
    return renderer.frameIndex[view];
  }

  function drawPreview(now = performance.now()) {
    actx.imageSmoothingEnabled = false;
    drawStageBg();
    if (renderer && avatar) {
      drawFootShadow(actx, STAGE.ax, STAGE.ay);
      renderer.draw(actx, avatar, STAGE.ax, STAGE.ay, previewFrame(now), false);
    }
    const c = stageCanvas.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.imageSmoothingEnabled = false;
    c.drawImage(art, 0, 0, STAGE.w, STAGE.h, 0, 0, stageCanvas.width, stageCanvas.height);
  }

  function loop(now) {
    raf = 0;
    if (!alive || !walking) return;
    drawPreview(now);
    raf = requestAnimationFrame(loop);
  }
  function stopLoop() { if (raf) cancelAnimationFrame(raf); raf = 0; }

  function setView(next) {
    view = next;
    for (const [k] of VIEWS) {
      viewBtns[k].setAttribute('aria-checked', String(k === view));
      viewBtns[k].tabIndex = k === view ? 0 : -1;
    }
  }
  function setWalking(on) {
    walking = on;
    walkBtn.setAttribute('aria-pressed', String(on));
    stopLoop();
    if (on) {
      setView('side');
      walkStart = performance.now();
      raf = requestAnimationFrame(loop);
    }
    drawPreview();
  }

  // --- 썸네일 -----------------------------------------------------------------
  function thumbCanvas(sizeCss) {
    const cv = h('canvas', { 'aria-hidden': 'true' });
    cv.width = sizeCss * dpr;
    cv.height = sizeCss * dpr;
    return cv;
  }
  function paintThumb(cv, src, sx, sy) {
    const c = cv.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.imageSmoothingEnabled = false;
    c.clearRect(0, 0, cv.width, cv.height);
    c.drawImage(src, sx, sy, THUMB_SIZE, THUMB_SIZE, 0, 0, cv.width, cv.height);
  }

  // --- 슬롯 그리드 --------------------------------------------------------------
  let slots = []; // [{ id, btn, canvas }]

  function buildSlots() {
    const part = activeTab;
    slotGrid.setAttribute('aria-labelledby', `tab-${part}`);
    slots = assets.parts[part].map((item) => {
      const isNone = part === 'hat' && item.id === HAT_NONE;
      const canvas = isNone ? null : thumbCanvas(THUMB_SIZE * 2);
      const btn = h('button', {
        type: 'button', class: 'bk-slot', role: 'radio', 'aria-checked': 'false', 'aria-label': item.label,
        testid: `slot-${part}-${item.id}`, 'data-id': item.id, tabindex: '-1', disabled: creating,
      }, isNone ? h('span', { class: 'bk-slot__none', 'aria-hidden': 'true' }) : canvas);
      return { id: item.id, btn, canvas };
    });
    slotGrid.replaceChildren(...slots.map((s) => s.btn));
    paintSlots();
  }

  function paintSlots() {
    const part = activeTab;
    const spec = THUMB[part];
    for (const s of slots) {
      const sel = avatar[part] === s.id;
      s.btn.setAttribute('aria-checked', String(sel));
      s.btn.tabIndex = sel ? 0 : -1;
      if (s.canvas) paintThumb(s.canvas, renderer.thumb({ ...avatar, [part]: s.id }, spec.parts), spec.x, spec.y);
    }
  }

  function buildPresets() {
    presetGrid.replaceChildren();
    assets.presets.forEach((p, i) => {
      const cv = thumbCanvas(THUMB_SIZE);
      paintThumb(cv, renderer.thumb(p.avatar, PART_KEYS), PRESET_CROP.x, PRESET_CROP.y);
      const btn = h('button', { type: 'button', class: 'bk-btn', testid: `preset-${i}`, 'data-label': p.label, disabled: creating }, cv, h('span', {}, p.label));
      on(btn, 'click', () => applyPreset(i));
      presetGrid.appendChild(btn);
    });
  }

  function announce(text) { setText(currentLine, text); }
  function announcePart(part) { announce(`${PART_LABELS[part]}: ${assets.labelOf(part, avatar[part])}`); }

  function selectPart(part, id) {
    if (creating || !ready || avatar[part] === id) return;
    avatar = { ...avatar, [part]: id };
    paintSlots();
    drawPreview();
    announcePart(part);
  }

  function applyPreset(i) {
    if (creating || !ready) return;
    const p = assets.presets[i];
    if (!p) return;
    avatar = assets.sanitizeAvatar(p.avatar); // manifest에 없는 id는 기본값
    paintSlots();
    drawPreview();
    announce(`추천 조합 적용: ${p.label}`);
  }

  function setTab(part, focus) {
    if (!ready || part === activeTab) { if (focus) tabBtns[part].focus(); return; }
    activeTab = part;
    for (const p of CATEGORY_ORDER) {
      tabBtns[p].setAttribute('aria-selected', String(p === part));
      tabBtns[p].tabIndex = p === part ? 0 : -1;
    }
    buildSlots();
    announcePart(part);
    if (focus) tabBtns[part].focus();
  }

  function gridColumns() {
    if (slots.length < 2) return 1;
    const top = slots[0].btn.offsetTop;
    let n = 0;
    for (const s of slots) { if (s.btn.offsetTop !== top) break; n++; }
    return Math.max(1, n);
  }

  // --- 닉네임 상태 (v1과 같음) ----------------------------------------------------
  const STATUS = {
    empty: { cls: '', text: M.HELP },
    format: { cls: 'bk-help--error', text: M.NICK_FORMAT },
    unchecked: { cls: '', text: M.UNCHECKED },
    checking: { cls: '', text: M.CHECKING, spin: true },
    available: { cls: 'bk-help--ok', text: M.AVAILABLE, check: true },
    taken: { cls: 'bk-help--error', text: M.NICK_TAKEN },
    failed: { cls: 'bk-help--error', text: M.NICK_CHECK_FAILED },
  };

  function setStatus(s) {
    nick.status = s;
    const d = STATUS[s];
    status.className = `bk-help nick-status ${d.cls}`.trim();
    status.dataset.state = s;
    setText(statusText, d.text);
    statusIcon.replaceChildren();
    if (d.spin) {
      statusIcon.className = 'status-icon bk-dots';
      statusIcon.append(h('i'), h('i'), h('i'));
    } else if (d.check) {
      statusIcon.className = 'status-icon bk-ico bk-ico--check';
    } else statusIcon.className = 'status-icon';
    statusIcon.hidden = !d.spin && !d.check;
    if (s === 'format' || s === 'taken') nickInput.setAttribute('aria-invalid', 'true');
    else nickInput.removeAttribute('aria-invalid');
    updateSubmit();
  }

  function updateSubmit() {
    submit.disabled = creating || !ready || !['unchecked', 'checking', 'available'].includes(nick.status);
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
    walkBtn.disabled = b;
    for (const [k] of VIEWS) viewBtns[k].disabled = b;
    for (const p of CATEGORY_ORDER) tabBtns[p].disabled = b || !ready;
    for (const s of slots) s.btn.disabled = b;
    for (const btn of presetGrid.querySelectorAll('button')) btn.disabled = b;
    spinner.hidden = !b;
    setText(submitLabel, b ? '만드는 중' : '캐릭터 만들기');
    updateSubmit();
  }

  async function doCreate() {
    if (creating || submit.disabled) return;
    banner.hidden = true;
    if (nick.status === 'checking' && pendingCheck) await pendingCheck;
    if (!alive) return;
    if (nick.status === 'unchecked') await runCheck();
    if (!alive || nick.status !== 'available' || !ready) return;
    setCreating(true);
    try {
      const ch = await app.backend.createCharacter(nick.value, pickAvatar(avatar)); // 정확히 7개 키
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

  function showManifestError() {
    partsBanner.hidden = false;
    partsBody.hidden = true;
    ready = false;
    updateSubmit();
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
  on(submit, 'click', () => doCreate());
  on(logoutBtn, 'click', () => { if (!creating) app.forceLogout(); });

  // 방향/걷기 (3.2): 앞/뒤를 누르면 걷기를 끈다. 걷기를 켜면 옆으로.
  for (const [k] of VIEWS) {
    on(viewBtns[k], 'click', () => {
      if (creating) return;
      if (walking && k !== 'side') { walking = false; walkBtn.setAttribute('aria-pressed', 'false'); stopLoop(); }
      setView(k);
      drawPreview();
    });
  }
  on(viewGroup, 'keydown', (e) => {
    const keys = VIEWS.map(([k]) => k);
    const i = keys.indexOf(view);
    let n = -1;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') n = (i + keys.length - 1) % keys.length;
    else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') n = (i + 1) % keys.length;
    if (n < 0) return;
    e.preventDefault();
    viewBtns[keys[n]].click();
    viewBtns[keys[n]].focus();
  });
  on(walkBtn, 'click', () => { if (!creating) setWalking(!walking); });

  // 카테고리 탭 (roving tabindex, 좌/우, Home/End)
  for (const p of CATEGORY_ORDER) on(tabBtns[p], 'click', () => { if (!creating) setTab(p, false); });
  on(tabList, 'keydown', (e) => {
    const i = CATEGORY_ORDER.indexOf(activeTab);
    let n = -1;
    if (e.key === 'ArrowLeft') n = (i + CATEGORY_ORDER.length - 1) % CATEGORY_ORDER.length;
    else if (e.key === 'ArrowRight') n = (i + 1) % CATEGORY_ORDER.length;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = CATEGORY_ORDER.length - 1;
    if (n < 0 || creating) return;
    e.preventDefault();
    setTab(CATEGORY_ORDER[n], true);
  });

  // 슬롯 (radio 동작: 클릭/Enter/Space 선택, 방향키 이동 + 선택)
  on(slotGrid, 'click', (e) => {
    const btn = e.target.closest('.bk-slot');
    if (!btn || !slotGrid.contains(btn) || btn.disabled) return;
    selectPart(activeTab, btn.dataset.id);
  });
  on(slotGrid, 'keydown', (e) => {
    if (creating || !slots.length) return;
    const i = Math.max(0, slots.findIndex((s) => s.id === avatar[activeTab]));
    const cols = gridColumns();
    let n = -1;
    if (e.key === 'ArrowLeft') n = i - 1;
    else if (e.key === 'ArrowRight') n = i + 1;
    else if (e.key === 'ArrowUp') n = i - cols;
    else if (e.key === 'ArrowDown') n = i + cols;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = slots.length - 1;
    else return;
    e.preventDefault();
    n = Math.max(0, Math.min(slots.length - 1, n));
    selectPart(activeTab, slots[n].id);
    slots[n].btn.focus();
  });

  let resizeTimer = 0;
  on(window, 'resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (alive) { sizeStage(); drawPreview(); } }, 100);
  });

  // --- 테스트 훅 ---------------------------------------------------------------
  app.createStateProvider = () => ({
    ready,
    avatar: avatar ? pickAvatar(avatar) : null,
    tab: activeTab,
    view,
    walking,
    frame: renderer && avatar ? previewFrame(performance.now()) : null,
    slots: slots.length,
    presets: assets ? assets.presets.length : 0,
  });

  // --- 시작 -----------------------------------------------------------------
  setStatus('empty');
  sizeStage();
  drawPreview();
  Promise.all([app.assets, app.mapAssets.catch(() => null)]).then(([a, m]) => {
    if (!alive) return;
    assets = a;
    map = m;
    stageDots.hidden = true;
    if (!a || a.source !== 'manifest') { showManifestError(); return; }
    renderer = createAvatarRenderer(a);
    avatar = { ...a.defaultAvatar }; // 7개 키 모두 manifest 각 파츠 첫 항목 (5.4)
    ready = true;
    for (const p of CATEGORY_ORDER) tabBtns[p].disabled = false;
    buildPresets();
    buildSlots();
    announcePart(activeTab);
    drawPreview();
    updateSubmit();
  }, () => {
    if (!alive) return;
    stageDots.hidden = true;
    showManifestError();
  });
  nickInput.focus({ preventScroll: true });

  return {
    unmount() {
      alive = false;
      clearTimeout(debounceTimer);
      clearTimeout(resizeTimer);
      stopLoop();
      ac.abort();
      if (app.createStateProvider) app.createStateProvider = null;
      renderer?.clear();
    },
  };
}
