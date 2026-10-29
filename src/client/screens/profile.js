// 프로필 화면: 닉네임 + 캐릭터 꾸미기 (docs/design/screens/profile.md v4, character-create.md v3 3·5장, style-guide 5.12~5.14)
// - 서버와 통신하지 않는다. 저장 = localStorage `mushroom:profile` = { nickname, avatar(7키) } (ARCHITECTURE 결정 3).
// - 모드: first(최초, "입장하기") / edit(로비 "꾸미기"에서, "취소" + "저장").
// - 카테고리 탭 7개 + 아이템 슬롯 그리드(썸네일) + 프리셋 + 회전 미리보기(앞/옆/뒤 + 걷기)는 v3 그대로.
// - 탭/슬롯/프리셋은 assets/avatar/manifest.json 의 parts/presets 로만 만든다(하드코딩 없음).
import { h, setText } from '../dom.js';
import { NICK_RE, NICK_MAX, PART_KEYS, CATEGORY_ORDER, PART_LABELS, HAT_NONE } from '../constants.js';
import { PROFILE_MESSAGES as M } from '../errors.js';
import { createAvatarRenderer, smooth } from '../avatar.js';
import { drawFootShadow, drawMap } from '../game/world.js';
import { pickAvatar } from '../avatar-data.js';
import { writeProfile } from '../store.js';
import { trimWs, charLength } from '../backend/common.js';

// 미리보기 무대 (사이클 5, 월드 단위): 112x144 = CSS 56x72 x --pv (데스크톱 4 → 224x288, 모바일 3 → 168x216).
// 기준점 (56,128). 배경 = 맵 전체를 카메라 (mapX, mapY)로 그린 작은 장면 (지면선 440 → 무대 128). mapX는 소품이 적은 잔디 구간.
const STAGE = Object.freeze({ w: 112, h: 144, ax: 56, ay: 128, mapX: 1460, mapY: 440 - 128 });

// 슬롯/프리셋 썸네일 자르기 (시트 px, front 프레임 144x192 안의 정사각형): 얼굴/머리(모자 포함) 또는 몸.
const HEAD_CROP = Object.freeze({ x: 16, y: 26, size: 112 });
const TOP_CROP = Object.freeze({ x: 22, y: 92, size: 100 }); // 어깨~무릎
const BOTTOM_CROP = Object.freeze({ x: 27, y: 104, size: 90 }); // 허리~발
const SHOES_CROP = Object.freeze({ x: 32, y: 112, size: 80 }); // 무릎~발끝 (측면 발끝 y 186까지)
const THUMB = Object.freeze({
  skin: { parts: ['skin', 'face'], crop: HEAD_CROP },
  face: { parts: ['skin', 'face'], crop: HEAD_CROP },
  hair: { parts: ['skin', 'face', 'hair'], crop: HEAD_CROP },
  hat: { parts: ['skin', 'face', 'hair', 'hat'], crop: HEAD_CROP },
  top: { parts: ['skin', 'face', 'top'], crop: TOP_CROP },
  bottom: { parts: ['skin', 'face', 'bottom'], crop: BOTTOM_CROP },
  shoes: { parts: ['skin', 'face', 'shoes'], crop: SHOES_CROP },
});
const THUMB_SIZE = 40;
const PRESET_CROP = HEAD_CROP;
const VIEWS = Object.freeze([['front', '앞'], ['side', '옆'], ['back', '뒤']]);

export function mount(root, app, opts = {}) {
  const editMode = opts.mode === 'edit' && !!app.profile;
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;
  let assets = null;
  let renderer = null;
  let avatar = null;
  let ready = false;
  const creating = false; // 처리 중 상태 없음 (동기 저장, profile.md 6장)
  let composing = false;
  let errorShown = false; // 한 번 오류를 보인 뒤에는 매 입력마다 즉시 갱신 (5.2)
  let activeTab = 'hair'; // 첫 진입 = 머리 (5.1)
  let view = 'front'; // front | side | back
  let walking = false;
  let walkStart = 0;
  let raf = 0;
  let cancelRepaint = () => {};
  const nick = { value: '', status: 'empty' };

  // --- 요소 ---------------------------------------------------------------

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
  const extraPresetGrid = h('div', { class: 'bk-presets', role: 'group', 'aria-label': '추가 추천 조합' });
  const morePresetLabel = h('span');
  const presetMore = h('details', { class: 'preset-more', testid: 'more-presets', hidden: true },
    h('summary', { class: 'bk-btn' }, morePresetLabel,
      h('span', { class: 'preset-more__expand' }, '펼치기'),
      h('span', { class: 'preset-more__collapse' }, '접기')),
    extraPresetGrid);
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
  const partsBanner = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'manifest-error', hidden: true }, M.MANIFEST);
  const partsBody = h('div', {},
    h('h2', { class: 'section-title' }, '추천 조합'), presetGrid, presetMore,
    h('h2', { class: 'section-title' }, '꾸미기'), tabList, slotGrid, currentLine);
  const partsArea = h('div', { class: 'create-parts' }, partsBanner, partsBody);

  // 닉네임 (5장)
  const nickInput = h('input', {
    id: 'nickname', class: 'bk-input bk-input--with-end', type: 'text', testid: 'nickname-input', maxlength: String(NICK_MAX),
    autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false', enterkeyhint: 'done', 'aria-describedby': 'nickname-status',
  });
  const nickCounter = h('span', { class: 'bk-counter', testid: 'nickname-counter', 'aria-hidden': 'true', hidden: true });
  const statusIcon = h('span', { class: 'status-icon', 'aria-hidden': 'true', hidden: true });
  const statusText = h('span', {});
  const status = h('p', { id: 'nickname-status', class: 'bk-help nick-status', testid: 'nickname-status', 'aria-live': 'polite' }, statusIcon, statusText);
  const nickArea = h('div', { class: 'create-nick bk-field' },
    h('label', { for: 'nickname', class: 'bk-label-text' }, '닉네임'),
    h('div', { class: 'bk-input-wrap' }, nickInput, h('span', { class: 'bk-input-end' }, nickCounter)),
    status);

  // 버튼 (6장): 비활성은 aria-disabled (눌렀을 때 형식 오류를 보여 주기 위해 클릭은 받는다)
  const submit = h('button', {
    type: 'button', class: editMode ? 'bk-btn bk-btn--primary' : 'bk-btn bk-btn--primary bk-btn--block', testid: 'create-submit', 'aria-disabled': 'true',
  }, editMode ? '저장' : '입장하기');
  const cancelBtn = editMode ? h('button', { type: 'button', class: 'bk-btn', testid: 'profile-cancel' }, '취소') : null;
  const ctaArea = h('div', { class: 'create-cta' }, editMode ? h('div', { class: 'cta-pair' }, cancelBtn, submit) : submit);

  const modeSlot = h('span', { class: 'mode-slot' });
  const footRow = h('div', { class: 'card-foot', testid: 'profile-note' }, app.mode === 'local' ? modeSlot : null, h('span', {}, M.NOTE));
  const title = h('h2', { class: 'card-title', tabindex: '-1', testid: 'profile-title' }, editMode ? '프로필 수정' : '프로필 만들기');
  const card = h('section', { class: 'bk-panel card-create', 'aria-labelledby': 'profile-title', testid: 'profile-card' },
    h('div', { class: 'card-head' }, title),
    h('div', { class: 'create-grid' }, prevArea, partsArea, nickArea, ctaArea),
    footRow);
  title.id = 'profile-title';
  const logo = editMode ? null
    : h('h1', { class: 'bk-logo bk-logo--sm' }, h('span', { class: 'bk-ico bk-ico--mush', 'aria-hidden': 'true' }), '버섯마을');
  root.append(h('main', { class: 'scr-auth', 'data-mode': editMode ? 'edit' : 'first' }, logo, card));
  if (app.mode === 'local') app.placeModeBadge(modeSlot);

  // --- 미리보기 그리기 ---------------------------------------------------------
  // 무대 캔버스 백킹(CSS x dpr)에 바로 그린다. k = 장치 px / 월드 = pv/2 x dpr. 스무딩 켬.
  let map = null;
  let pv = 4;
  let dpr = 1;
  let k = 2;
  let lastDrawn = ''; // 마지막으로 그린 (조합, 프레임) — 같은 그림이면 다시 그리지 않는다
  let shownOnce = false;

  function sizeStage() {
    const v = parseInt(getComputedStyle(previewEl).getPropertyValue('--pv'), 10);
    pv = Number.isInteger(v) && v > 0 ? v : 4;
    dpr = Math.max(1, Math.min(3, Math.round(window.devicePixelRatio || 1)));
    k = (pv / 2) * dpr;
    const w = Math.round(STAGE.w * k);
    const hgt = Math.round(STAGE.h * k);
    if (stageCanvas.width !== w || stageCanvas.height !== hgt) { stageCanvas.width = w; stageCanvas.height = hgt; }
    lastDrawn = '';
  }

  // 배경 = 방과 같은 맵 그리기(drawMap)를 카메라 (mapX, mapY)로 (패럴랙스 레이어 포함 작은 장면)
  function drawStageBg(c) {
    // (사이클 9) 맵 지면이 바뀌어도(큰 맵 groundY 900) 지면선이 무대 기준점에 오게
    const gy = map && typeof map.groundY === 'number' ? map.groundY : 440;
    drawMap(c, map, STAGE.mapX, gy - STAGE.ay, k, stageCanvas.width, stageCanvas.height);
  }

  function previewFrame(now) {
    if (walking) return renderer.frameAt('walk', now - walkStart);
    if (view === 'front') return renderer.frameAt('idle_front', now - walkStart); // 앞 = 숨쉬기 0,1
    return renderer.frameIndex[view];
  }

  function drawPreview(now = performance.now(), force = true) {
    const fr = renderer && avatar ? previewFrame(now) : -1;
    const ok = !!(renderer && avatar && renderer.isReady(avatar));
    const key = `${ok ? PART_KEYS.map((p) => avatar[p]).join('|') : '-'}#${fr}`;
    if (!force && key === lastDrawn) return;
    lastDrawn = key;
    const c = stageCanvas.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    smooth(c);
    drawStageBg(c);
    if (renderer && avatar) {
      const fx = STAGE.ax * k;
      const fy = STAGE.ay * k;
      if (ok) drawFootShadow(c, fx, fy, k);
      renderer.draw(c, avatar, fx, fy, k, fr, false);
    }
    if (ok && !shownOnce) { shownOnce = true; stageDots.hidden = true; }
  }

  // 앞(숨쉬기)과 걷기는 애니메이션: 프레임이 바뀔 때만 다시 그린다
  function loop(now) {
    raf = 0;
    if (!alive || !(walking || view === 'front')) return;
    drawPreview(now, false);
    raf = requestAnimationFrame(loop);
  }
  function stopLoop() { if (raf) cancelAnimationFrame(raf); raf = 0; }
  function startLoop() { if (!raf && alive && ready && (walking || view === 'front')) raf = requestAnimationFrame(loop); }

  function setView(next) {
    view = next;
    for (const [v] of VIEWS) {
      viewBtns[v].setAttribute('aria-checked', String(v === view));
      viewBtns[v].tabIndex = v === view ? 0 : -1;
    }
  }
  function setWalking(on) {
    walking = on;
    walkBtn.setAttribute('aria-pressed', String(on));
    stopLoop();
    walkStart = performance.now();
    if (on) setView('side');
    startLoop();
    drawPreview();
  }

  // --- 썸네일 -----------------------------------------------------------------
  function thumbCanvas(sizeCss) {
    const cv = h('canvas', { 'aria-hidden': 'true' });
    cv.width = sizeCss * dpr;
    cv.height = sizeCss * dpr;
    return cv;
  }
  /** src가 null이면(합성 중) 비워 두고, 합성이 끝나면 renderer onUpdate로 다시 칠한다. */
  function paintThumb(cv, src, crop) {
    const c = cv.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    smooth(c);
    c.clearRect(0, 0, cv.width, cv.height);
    if (src) c.drawImage(src, crop.x, crop.y, crop.size, crop.size, 0, 0, cv.width, cv.height);
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
      if (s.canvas) paintThumb(s.canvas, renderer.thumb({ ...avatar, [part]: s.id }, spec.parts), spec.crop);
    }
  }

  let presetCanvases = [];
  function paintPresets() {
    presetCanvases.forEach((cv, i) => {
      if (i < 6 || presetMore.open) paintThumb(cv, renderer.thumb(assets.presets[i].avatar, PART_KEYS), PRESET_CROP);
    });
  }
  on(presetMore, 'toggle', () => { if (ready && presetMore.open) paintPresets(); });
  function buildPresets() {
    presetGrid.replaceChildren();
    extraPresetGrid.replaceChildren();
    presetMore.hidden = assets.presets.length <= 6;
    setText(morePresetLabel, `다른 코디 ${Math.max(0, assets.presets.length - 6)}개`);
    presetCanvases = [];
    assets.presets.forEach((p, i) => {
      const cv = thumbCanvas(THUMB_SIZE);
      presetCanvases.push(cv);
      if (i < 6 || presetMore.open) paintThumb(cv, renderer.thumb(p.avatar, PART_KEYS), PRESET_CROP);
      const btn = h('button', { type: 'button', class: 'bk-btn', testid: `preset-${i}`, 'data-label': p.label, disabled: creating }, cv, h('span', {}, p.label));
      on(btn, 'click', () => applyPreset(i));
      (i < 6 ? presetGrid : extraPresetGrid).appendChild(btn);
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

  // --- 닉네임 상태 (5.2) -------------------------------------------------------
  // empty: 안내 / ok: 형식 맞음 / format: 형식 오류
  const STATUS = {
    empty: { cls: '', text: M.HELP },
    ok: { cls: 'bk-help--ok', text: M.OK, check: true },
    format: { cls: 'bk-help--error', text: M.NICK_FORMAT },
  };

  function setStatus(s) {
    nick.status = s;
    const d = STATUS[s];
    status.className = `bk-help nick-status ${d.cls}`.trim();
    status.dataset.state = s;
    setText(statusText, d.text);
    statusIcon.className = d.check ? 'status-icon bk-ico bk-ico--check' : 'status-icon';
    statusIcon.hidden = !d.check;
    if (s === 'format') nickInput.setAttribute('aria-invalid', 'true');
    else nickInput.removeAttribute('aria-invalid');
    updateSubmit();
  }

  function canSubmit() {
    return ready && nick.status === 'ok';
  }
  function updateSubmit() {
    submit.setAttribute('aria-disabled', String(!canSubmit()));
  }

  function updateCounter() {
    const n = charLength(nickInput.value);
    nickCounter.hidden = n === 0;
    setText(nickCounter, `${n}/${NICK_MAX}`);
  }

  /**
   * trigger: 'input' | 'blur' | 'submit'
   * 처음 입력하는 동안 1자일 때는 안내 상태. 오류는 (a) 2자 이상 불일치 (b) blur 때 불일치(빈 값 제외) (c) 버튼 누름 때 불일치.
   * 한 번 오류를 보인 뒤에는 매 입력마다 즉시 갱신.
   */
  function evaluate(trigger = 'input') {
    updateCounter();
    if (composing) return; // 조합 중에는 직전 상태 유지
    const v = trimWs(nickInput.value);
    nick.value = v;
    if (NICK_RE.test(v)) { setStatus('ok'); return; }
    const show = errorShown || trigger === 'submit' || (v && (trigger === 'blur' || charLength(v) >= 2));
    if (show) {
      errorShown = true;
      setStatus('format');
    } else setStatus('empty');
  }

  // --- 저장 -----------------------------------------------------------------
  let done = false;
  function doSave() {
    if (done) return;
    composing = false;
    evaluate('submit');
    if (!canSubmit()) {
      if (nick.status === 'format') nickInput.focus();
      return;
    }
    done = true;
    const profile = { nickname: nick.value, avatar: pickAvatar(avatar) }; // 정확히 7개 키
    app.profile = profile;
    if (!writeProfile(app.profileKey, profile)) app.storageFailed = true; // 막지 않고 메모리로 진행 (6.1)
    app.go('lobby');
  }
  function doCancel() {
    if (done || !editMode) return;
    done = true;
    app.go('lobby', { focus: 'edit' });
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
  on(nickInput, 'input', (e) => { if (!e.isComposing) composing = false; evaluate(); });
  on(nickInput, 'blur', () => { composing = false; evaluate('blur'); });
  on(nickInput, 'keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.isComposing || e.keyCode === 229) return;
      doSave();
    }
  });
  on(submit, 'click', () => doSave());
  if (cancelBtn) on(cancelBtn, 'click', () => doCancel());
  // Esc: 수정 모드에서 "취소"와 같다 (IME 조합 중이면 무시)
  on(window, 'keydown', (e) => {
    if (e.key !== 'Escape' || !editMode || e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    doCancel();
  });

  // 방향/걷기 (3.2): 앞/뒤를 누르면 걷기를 끈다. 걷기를 켜면 옆으로.
  for (const [k] of VIEWS) {
    on(viewBtns[k], 'click', () => {
      if (creating) return;
      if (walking && k !== 'side') { walking = false; walkBtn.setAttribute('aria-pressed', 'false'); }
      stopLoop();
      if (view !== k) walkStart = performance.now();
      setView(k);
      startLoop();
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
    resizeTimer = setTimeout(() => {
      if (!alive) return;
      sizeStage();
      drawPreview();
    }, 100);
  });

  // --- 테스트 훅 ---------------------------------------------------------------
  app.providers.profile = () => ({
    mode: editMode ? 'edit' : 'first',
    ready,
    avatar: avatar ? pickAvatar(avatar) : null,
    nickname: nickInput.value,
    nicknameStatus: nick.status,
    tab: activeTab,
    view,
    walking,
    frame: renderer && avatar ? previewFrame(performance.now()) : null,
    slots: slots.length,
    presets: assets ? assets.presets.length : 0,
  });

  // --- 시작 -----------------------------------------------------------------
  if (editMode) nickInput.value = app.profile.nickname;
  setStatus('empty');
  evaluate('input');
  sizeStage();
  drawPreview();
  Promise.all([app.assets, app.mapAssets.catch(() => null)]).then(([a, m]) => {
    if (!alive) return;
    assets = a;
    map = m;
    if (!a || a.source !== 'manifest') { stageDots.hidden = true; showManifestError(); return; }
    // 레이어는 그릴 조합이 생길 때 받는다. 합성이 끝날 때마다 다음 프레임에 미리보기/썸네일을 다시 칠한다.
    let repaintRaf = 0;
    renderer = createAvatarRenderer(a, {
      onUpdate() {
        if (repaintRaf || !alive) return;
        repaintRaf = requestAnimationFrame(() => {
          repaintRaf = 0;
          if (!alive || !ready) return;
          drawPreview();
          paintSlots();
          paintPresets();
        });
      },
    });
    cancelRepaint = () => { if (repaintRaf) cancelAnimationFrame(repaintRaf); repaintRaf = 0; };
    // 최초: manifest 각 파츠 첫 항목 / 수정: 저장 값 (manifest에 없는 id는 기본값, 저장하면 그 값으로 고쳐 저장)
    avatar = editMode ? a.sanitizeAvatar(app.profile.avatar) : { ...a.defaultAvatar };
    ready = true;
    for (const p of CATEGORY_ORDER) tabBtns[p].disabled = false;
    buildPresets();
    buildSlots();
    announcePart(activeTab);
    drawPreview();
    startLoop();
    updateSubmit();
  }, () => {
    if (!alive) return;
    stageDots.hidden = true;
    showManifestError();
  });
  // 진입 포커스 = 제목 (모바일에서 키보드가 바로 올라와 미리보기를 가리지 않게, 8장)
  title.focus({ preventScroll: true });

  return {
    unmount() {
      alive = false;
      clearTimeout(resizeTimer);
      stopLoop();
      cancelRepaint();
      ac.abort();
      if (app.providers.profile) app.providers.profile = null;
      renderer?.clear();
    },
  };
}
