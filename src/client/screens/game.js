// 인게임 화면 (docs/design/screens/game.md, style-guide 4~7장)
import { h, setText, wait } from '../dom.js';
import {
  WORLD, ART, BUBBLE, PAL, MOBILE_MAX_WIDTH, MOBILE_CONTROLS_H, DESKTOP_RESERVED_H, NICK_RE,
  CHAT_MAX, CHAT_COOLDOWN_MS, MOVE_INTERVAL_MS, RECONNECT_DELAYS_MS, pixelScale,
} from '../constants.js';
import { GAME_MESSAGES as M } from '../errors.js';
import { createAvatarRenderer, makeCanvas, idleOffset } from '../avatar.js';
import { drawMap, drawFootShadow, cameraFor } from '../game/world.js';
import { layoutBubble, drawBubble, drawLabel, bubbleAlpha } from '../game/overlay.js';
import { createMoveInput, KEY_DIR } from '../game/input.js';

const JOIN_TIMEOUT_MS = 12000;
const REMOTE_SNAP_DIST = 400; // 이보다 멀면 순간 이동
const REMOTE_CATCHUP = 32; // 뒤처진 거리(월드 단위)마다 속도를 1배씩 더한다
const WALK_HOLD_MS = 150; // 원격 아바타: 마지막으로 움직인 뒤 이 시간 안이면 walk (패킷 간격 100ms 흡수)
const toArt = (wx) => Math.round(wx / 2);

const clampX = (x) => Math.min(WORLD.maxX, Math.max(WORLD.minX, x));
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
// 제어 문자(줄바꿈 포함)는 공백으로
const cleanText = (s) => s.replace(/[\u0000-\u001F\u007F\u2028\u2029]/g, ' ').trim();

export function mount(root, app) {
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;

  const character = app.character;
  let assets = null;
  let avatarR = null;
  let map = null; // loadMapAssets() 결과
  let ui = null; // loadUiAssets() 결과
  let link = null; // { sendMove, sendChat, leave }
  let joinGen = 0;
  let connection = 'joining'; // joining | connected | disconnected | failed | fatal
  let reconnecting = false;
  let raf = 0;
  let lastFrame = 0;
  const input = createMoveInput();
  const timers = new Set();
  const later = (fn, ms) => { const t = setTimeout(() => { timers.delete(t); fn(); }, ms); timers.add(t); return t; };
  const cancel = (t) => { clearTimeout(t); timers.delete(t); };

  /** user_id -> player */
  const players = new Map();
  let me = null;

  // 레이아웃 (style-guide 4.2): P = 정수 픽셀 배율, view = 아트 px 시야
  let layout = { mobile: false, cssW: 2, cssH: 2, viewW: 1, viewH: 1, P: 2, dpr: 1 };
  let off = makeCanvas(1, 1); // 아트 해상도 오프스크린
  let offCtx = off.getContext('2d');

  // 네트워크 송신 상태
  let lastMoveSentAt = 0;
  let sentX = null;
  let sentDir = null;
  let lastChatAt = -Infinity;

  // --- DOM ----------------------------------------------------------------
  const countText = h('span', { testid: 'player-count' }, '접속 중 1명');
  const countDot = h('span', { class: 'count-dot', title: '연결 끊김', hidden: true });
  const countBadge = h('div', { class: 'chip count-badge', 'aria-live': 'off' },
    h('span', { class: 'chip-icon', 'aria-hidden': 'true' }), countText, countDot);
  const modeSlot = h('span', { class: 'mode-slot' });
  const hint = h('div', { class: 'chip hud-hint' }, '← → 또는 A D 이동 · Enter 채팅 · Esc 입력 해제');
  const logoutBtn = h('button', { type: 'button', class: 'btn btn-secondary btn-sm hud-logout', testid: 'logout' }, '로그아웃');
  const hud = h('div', { class: 'hud' },
    h('div', { class: 'hud-left' }, countBadge, modeSlot),
    h('div', { class: 'hud-right' }, hint, logoutBtn));

  const bannerText = h('span', {});
  const bannerBtn = h('button', { type: 'button', class: 'btn btn-primary btn-sm', testid: 'reconnect-button', hidden: true });
  const banner = h('div', { class: 'game-banner', testid: 'game-banner', role: 'status', hidden: true }, bannerText, bannerBtn);

  const canvas = h('canvas', {
    class: 'game-canvas', testid: 'game-canvas', tabindex: '0',
    'aria-label': '버섯마을 맵. 좌우 방향키로 이동, Enter로 채팅',
  });
  const loadingDots = h('span', { class: 'dots dots-light canvas-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const canvasWrap = h('div', { class: 'canvas-wrap' }, canvas, hud, banner, loadingDots);

  const arrowL = h('span', { class: 'arrow arrow-left', 'aria-hidden': 'true' }, '◀');
  const arrowR = h('span', { class: 'arrow', 'aria-hidden': 'true' }, '▶');
  const leftBtn = h('button', { type: 'button', class: 'btn btn-secondary touch-btn', testid: 'move-left', 'aria-label': '왼쪽으로 이동' }, arrowL, '왼쪽');
  const rightBtn = h('button', { type: 'button', class: 'btn btn-secondary touch-btn', testid: 'move-right', 'aria-label': '오른쪽으로 이동' }, '오른쪽', arrowR);
  const touchRow = h('div', { class: 'touch-row' }, leftBtn, rightBtn);

  const chatInput = h('input', {
    type: 'text', class: 'input chat-input', testid: 'chat-input', maxlength: String(CHAT_MAX), placeholder: '메시지를 입력하세요',
    autocomplete: 'off', 'aria-label': '채팅 메시지',
  });
  const counter = h('span', { class: 'chat-counter', testid: 'chat-counter', hidden: true, 'aria-hidden': 'true' });
  const sendBtn = h('button', { type: 'button', class: 'btn btn-primary chat-send', testid: 'chat-send', disabled: true }, '보내기');
  const chatHint = h('div', { class: 'chip chat-hint', testid: 'chat-hint', hidden: true }, M.COOLDOWN);
  const chatError = h('div', { class: 'err-banner chat-error', testid: 'chat-error', role: 'alert', hidden: true });
  const chatBar = h('div', { class: 'chat-bar' }, h('div', { class: 'chat-field' }, chatInput, counter), sendBtn);
  const chatRow = h('div', { class: 'chat-row' }, chatHint, chatError, chatBar);

  const col = h('div', { class: 'game-col' }, canvasWrap, touchRow, chatRow);
  root.append(col);
  app.placeModeBadge(modeSlot);

  // --- 레이아웃 -----------------------------------------------------------
  function computeLayout() {
    // innerWidth는 모바일에서 내용이 넘치면 커진다. 레이아웃 뷰포트(clientWidth)를 기준으로 한다.
    const vw = document.documentElement.clientWidth || window.innerWidth;
    const vv = window.visualViewport;
    const vh = Math.floor(vv && vv.height ? Math.min(vv.height, window.innerHeight || vv.height) : window.innerHeight);
    const mobile = vw < MOBILE_MAX_WIDTH;
    let P;
    let cssW;
    let cssH;
    if (mobile) {
      P = 2;
      cssW = Math.floor(vw / P) * P;
      cssH = Math.floor((vh - MOBILE_CONTROLS_H) / P) * P;
    } else {
      P = pixelScale(vw, vh);
      cssW = Math.min(Math.floor(vw / P) * P, 640 * P); // 1280 (P=2), 1920 (P=3)
      cssH = Math.min(ART.height * P, Math.floor((vh - DESKTOP_RESERVED_H) / P) * P);
    }
    let viewW = Math.max(1, cssW / P);
    let viewH = cssH / P;
    if (viewH < ART.minViewH) { viewH = ART.minViewH; cssH = viewH * P; }
    viewW = Math.max(1, Math.floor(viewW));
    cssW = viewW * P;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    layout = { mobile, cssW, cssH, viewW, viewH, P, dpr };
    root.dataset.layout = mobile ? 'mobile' : 'desktop';
    root.style.setProperty('--canvas-w', `${cssW}px`);
    canvasWrap.style.width = `${cssW}px`;
    canvasWrap.style.height = `${cssH}px`;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    if (off.width !== viewW || off.height !== viewH) {
      off = makeCanvas(viewW, viewH);
      offCtx = off.getContext('2d');
    }
    offCtx.imageSmoothingEnabled = false;
    hint.classList.toggle('narrow', cssW < 900);
    // 데스크톱 바깥 배경 경계: 캔버스 아래 끝 (하늘 / 흙)
    if (!mobile) {
      const r = canvasWrap.getBoundingClientRect();
      const top = root.getBoundingClientRect().top;
      root.style.setProperty('--ground-y', `${Math.round(r.bottom - top)}px`);
    } else root.style.removeProperty('--ground-y');
    if (connection === 'joining' || connection === 'fatal') paintLetterbox();
    else render(performance.now());
  }

  function paintLetterbox() {
    const c = canvas.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.fillStyle = PAL.ink;
    c.fillRect(0, 0, canvas.width, canvas.height);
  }

  // --- 상태/배너 -----------------------------------------------------------
  let bannerHideTimer = 0;
  function setBanner(kind, text, button) {
    cancel(bannerHideTimer);
    banner.classList.remove('fade-out');
    if (!kind) { banner.hidden = true; return; }
    banner.hidden = false;
    banner.className = `game-banner ${kind}`;
    banner.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    setText(bannerText, text);
    if (button) { setText(bannerBtn, button); bannerBtn.hidden = false; }
    else bannerBtn.hidden = true;
  }

  function setConnection(next) {
    const prev = connection;
    connection = next;
    root.dataset.connection = next;
    const hudVisible = next !== 'joining' && next !== 'fatal';
    hud.hidden = !hudVisible && next !== 'fatal';
    countBadge.hidden = !hudVisible;
    hint.hidden = !hudVisible;
    modeSlot.hidden = !hudVisible;
    chatRow.classList.toggle('is-hidden', !hudVisible);
    touchRow.classList.toggle('is-hidden', !hudVisible);
    loadingDots.hidden = next !== 'joining';
    countDot.hidden = !(next === 'disconnected' || next === 'failed');
    const interactive = next === 'connected' || next === 'disconnected';
    chatInput.disabled = next !== 'connected';
    leftBtn.disabled = !interactive;
    rightBtn.disabled = !interactive;
    updateSendBtn();
    if (next !== 'connected') input.clear();

    switch (next) {
      case 'joining':
        setBanner('info', M.JOINING);
        paintLetterbox();
        break;
      case 'connected':
        if (prev === 'disconnected' || prev === 'failed') {
          banner.classList.add('fade-out');
          bannerHideTimer = later(() => setBanner(null), 500);
        } else setBanner(null);
        break;
      case 'disconnected':
        setBanner('error', M.DISCONNECTED);
        break;
      case 'failed':
        setBanner('error', M.RECONNECT_FAILED, '다시 연결');
        break;
      case 'fatal':
        setBanner('error', M.FATAL, '다시 시도');
        paintLetterbox();
        break;
      default:
        break;
    }
  }

  function updateCount() {
    const n = players.size;
    setText(countText, n >= 1000 ? '접속 중 999명+' : `접속 중 ${n}명`);
  }

  // --- 플레이어 -------------------------------------------------------------
  function makePlayer(uid, nickname, avatar, x, isSelf) {
    return {
      user_id: uid, nickname, avatar, x, targetX: x, y: WORLD.groundY, dir: 1,
      moving: false, lastMoveAt: 0, lastMovedAt: -Infinity, anim: 'idle', animSince: performance.now(),
      idleOffset: idleOffset(uid), bubble: null, lastChat: null, isSelf,
    };
  }

  function setBubble(p, text) {
    p.lastChat = text;
    p.bubble = { text, at: performance.now(), layout: layoutBubble(canvas.getContext('2d'), text) };
  }

  const handlersFor = (gen) => ({
    onPresence(list) {
      if (!alive || gen !== joinGen || !Array.isArray(list)) return;
      const seen = new Set([me.user_id]);
      for (const s of list) {
        if (!s || typeof s !== 'object' || typeof s.user_id !== 'string' || !s.user_id || s.user_id.length > 64) continue;
        if (s.user_id === me.user_id) continue;
        seen.add(s.user_id);
        const nickname = typeof s.nickname === 'string' && NICK_RE.test(s.nickname) ? s.nickname : '???';
        const avatar = assets.sanitizeAvatar(s.avatar);
        const existing = players.get(s.user_id);
        if (existing) {
          existing.nickname = nickname;
          existing.avatar = avatar;
        } else {
          const x = isNum(s.x) ? clampX(s.x) : WORLD.minX;
          players.set(s.user_id, makePlayer(s.user_id, nickname, avatar, x, false));
        }
      }
      for (const uid of [...players.keys()]) if (!seen.has(uid)) players.delete(uid);
      updateCount();
    },
    onMove(p) {
      if (!alive || gen !== joinGen || !p || typeof p !== 'object') return;
      const pl = typeof p.user_id === 'string' ? players.get(p.user_id) : null;
      if (!pl || pl.isSelf || !isNum(p.x)) return; // Presence에 없는 user_id는 버린다
      pl.targetX = clampX(p.x);
      if (p.dir === 'left' || p.dir === -1) pl.dir = -1;
      else if (p.dir === 'right' || p.dir === 1) pl.dir = 1;
      pl.lastMoveAt = performance.now();
    },
    onChat(p) {
      if (!alive || gen !== joinGen || !p || typeof p !== 'object') return;
      const pl = typeof p.user_id === 'string' ? players.get(p.user_id) : null;
      if (!pl || pl.isSelf || typeof p.text !== 'string') return;
      if (p.text.length > CHAT_MAX) return; // 길이 제한 재검증: 초과 메시지는 버린다
      const text = cleanText(p.text);
      if (!text) return;
      setBubble(pl, text);
    },
    onStatus(st) {
      if (!alive || gen !== joinGen) return;
      if (st === 'connected') {
        if (connection === 'disconnected' || connection === 'failed') setConnection('connected');
      } else if (st === 'disconnected') {
        reconnect();
      }
    },
  });

  async function join() {
    const gen = ++joinGen;
    const self = { user_id: me.user_id, nickname: me.nickname, avatar: me.avatar, x: Math.round(me.x), y: me.y };
    let timeoutId = 0;
    const joined = await Promise.race([
      app.backend.joinMap(handlersFor(gen), self),
      new Promise((_, reject) => { timeoutId = later(() => reject(new Error('join timeout')), JOIN_TIMEOUT_MS); }),
    ]).finally(() => cancel(timeoutId));
    if (!alive || gen !== joinGen) {
      try { await joined.leave(); } catch { /* 무시 */ }
      throw new Error('stale');
    }
    link = joined;
    sentX = Math.round(me.x);
    sentDir = me.dir;
  }

  async function leaveMap() {
    const m = link;
    link = null;
    joinGen++;
    if (m) {
      try { await m.leave(); } catch { /* 무시 */ }
    }
  }

  async function reconnect() {
    if (reconnecting || !alive) return;
    reconnecting = true;
    setConnection('disconnected');
    for (const d of RECONNECT_DELAYS_MS) {
      await wait(d, ac.signal);
      if (!alive) return;
      if (connection === 'connected') { reconnecting = false; return; } // 어댑터가 스스로 복구함
      try {
        await leaveMap();
        await join();
        if (!alive) return;
        setConnection('connected');
        reconnecting = false;
        return;
      } catch {
        /* 다음 시도 */
      }
    }
    if (!alive) return;
    reconnecting = false;
    setConnection('failed');
  }

  async function firstJoin() {
    setConnection('joining');
    try {
      await join();
      if (!alive) return;
      setConnection('connected');
      canvas.focus({ preventScroll: true });
    } catch (err) {
      if (!alive) return;
      if (err && err.code === 'AUTH_REQUIRED') { app.forceLogout('SERVER'); return; }
      setConnection('fatal');
    }
  }

  // --- 업데이트/렌더 ---------------------------------------------------------
  function update(dt, now) {
    if (connection === 'connected' && me) {
      const dir = input.direction();
      if (dir !== 0) {
        me.x = clampX(me.x + dir * WORLD.speed * dt);
        me.dir = dir;
        me.moving = true;
      } else {
        me.moving = false;
      }
      // move 송신: 최대 10회/초, 위치(또는 방향)가 바뀌었을 때만. 정지 후 마지막 좌표도 이 규칙으로 1회 나간다.
      const rx = Math.round(me.x);
      if (link && now - lastMoveSentAt >= MOVE_INTERVAL_MS && (rx !== sentX || me.dir !== sentDir)) {
        lastMoveSentAt = now;
        sentX = rx;
        sentDir = me.dir;
        link.sendMove({ x: rx, y: WORLD.groundY, dir: me.dir < 0 ? 'left' : 'right' }).catch(() => {});
      }
    } else if (me) {
      me.moving = false;
    }
    for (const p of players.values()) {
      if (p.isSelf) continue;
      // 원격 보간: 등속(160/초) 추적 + 뒤처진 만큼 가속, 너무 멀면 순간 이동
      const diff = p.targetX - p.x;
      const dist = Math.abs(diff);
      if (dist > REMOTE_SNAP_DIST) {
        p.x = p.targetX;
      } else if (dist > 0) {
        const v = WORLD.speed * (1 + Math.max(0, dist - 16) / REMOTE_CATCHUP);
        const step = Math.min(dist, v * dt);
        p.x += Math.sign(diff) * step;
        if (step > 0.01) p.lastMovedAt = now;
      }
      // style-guide 5.11: 마지막 move 이후 위치가 바뀌고 있으면 walk
      p.moving = now - p.lastMovedAt < WALK_HOLD_MS;
      if (p.bubble && now - p.bubble.at >= BUBBLE.showMs) p.bubble = null;
    }
    if (me && me.bubble && now - me.bubble.at >= BUBBLE.showMs) me.bubble = null;
    for (const p of players.values()) {
      const next = p.moving ? 'walk' : 'idle';
      if (next !== p.anim) { p.anim = next; p.animSince = now; } // 상태가 바뀌면 첫 프레임부터
    }
  }

  function frameOf(p, now) {
    const t = now - p.animSince;
    return p.anim === 'walk' ? avatarR.frameAt('walk', t) : avatarR.frameAt('idle', t + p.idleOffset);
  }

  // style-guide 4.4 파이프라인: 아트 해상도 오프스크린 → 정수 배율 확대(스무딩 끔) → 화면 해상도 글자
  function render(now) {
    if (!me || !avatarR) return;
    if (connection === 'joining' || connection === 'fatal') { paintLetterbox(); return; }
    const { cssW, viewW, viewH, P, dpr } = layout;
    const { camX, camY } = cameraFor(toArt(me.x), viewW, viewH);
    const c = offCtx;
    c.imageSmoothingEnabled = false;
    drawMap(c, map, camX, camY, viewW, viewH);

    const groundY = ART.groundY - camY;
    const order = [];
    for (const p of players.values()) if (!p.isSelf) order.push(p);
    order.sort((a, b) => a.x - b.x);
    order.push(me); // 내 캐릭터는 마지막
    const visible = [];
    for (const p of order) {
      const ax = toArt(p.x) - camX;
      if (ax < -avatarR.frameW || ax > viewW + avatarR.frameW) continue;
      visible.push([p, ax]);
    }
    for (const [, ax] of visible) drawFootShadow(c, ax, groundY);
    for (const [p, ax] of visible) avatarR.draw(c, p.avatar, ax, groundY, frameOf(p, now), p.dir < 0);

    const ctx = canvas.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(off, 0, 0, viewW, viewH, 0, 0, canvas.width, canvas.height);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const footY = groundY * P;
    for (const [p, ax] of visible) drawLabel(ctx, ui, p.nickname, ax * P, footY, p.isSelf, cssW);
    const headY = (ART.headLineY - camY) * P;
    for (const [p, ax] of visible) {
      if (!p.bubble) continue;
      drawBubble(ctx, ui, p.bubble.layout, ax * P, headY, cssW, bubbleAlpha(now - p.bubble.at));
    }
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(Math.max((now - (lastFrame || now)) / 1000, 0), WORLD.maxDt);
    lastFrame = now;
    update(dt, now);
    render(now);
  }

  // --- 채팅 -----------------------------------------------------------------
  let hintTimer = 0;
  let errorTimer = 0;
  let cooldownTimer = 0;

  function updateCounter() {
    const n = chatInput.value.length;
    counter.hidden = n === 0;
    setText(counter, `${n}/${CHAT_MAX}`);
    updateSendBtn();
  }

  function inCooldown() {
    return performance.now() - lastChatAt < CHAT_COOLDOWN_MS;
  }

  function updateSendBtn() {
    sendBtn.disabled = connection !== 'connected' || !chatInput.value.trim() || inCooldown();
  }

  function showHint() {
    chatHint.hidden = false;
    cancel(hintTimer);
    hintTimer = later(() => { chatHint.hidden = true; }, 800);
  }

  function showSendError() {
    setText(chatError, M.SEND_FAILED);
    chatError.hidden = false;
    cancel(errorTimer);
    errorTimer = later(() => { chatError.hidden = true; }, 2000);
  }

  function trySend() {
    if (connection !== 'connected' || !link) return;
    const raw = chatInput.value;
    const text = cleanText(raw).slice(0, CHAT_MAX);
    if (!text) return;
    if (inCooldown()) { showHint(); return; }
    lastChatAt = performance.now();
    setBubble(me, text); // 서버 왕복 없이 즉시
    chatInput.value = '';
    updateCounter();
    cancel(cooldownTimer);
    cooldownTimer = later(updateSendBtn, CHAT_COOLDOWN_MS + 10);
    const m = link;
    m.sendChat(text).catch(() => {
      if (!alive) return;
      if (!chatInput.value) { chatInput.value = raw; updateCounter(); }
      showSendError();
    });
  }

  // --- 입력 이벤트 -----------------------------------------------------------
  const isTypingTarget = (el) => !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
  const isGameFocus = () => {
    const ae = document.activeElement;
    return !ae || ae === document.body || ae === document.documentElement || ae === canvas;
  };

  on(window, 'keydown', (e) => {
    if (!alive) return;
    const typing = document.activeElement === chatInput;
    if (e.key === 'Enter') {
      if (typing) {
        if (e.isComposing || e.keyCode === 229) return; // 한글 조합 중
        e.preventDefault();
        trySend();
      } else if (isGameFocus() && connection === 'connected') {
        e.preventDefault();
        chatInput.focus();
      }
      return;
    }
    if (e.key === 'Escape') {
      if (typing) {
        e.preventDefault();
        chatInput.blur();
        canvas.focus({ preventScroll: true });
      }
      return;
    }
    const dir = KEY_DIR[e.code];
    if (dir && !isTypingTarget(document.activeElement)) {
      e.preventDefault();
      if (!e.repeat && connection === 'connected') input.press(`key:${e.code}`, dir);
    }
  });
  on(window, 'keyup', (e) => { input.release(`key:${e.code}`); });
  on(window, 'blur', () => input.clear());
  on(document, 'visibilitychange', () => { if (document.visibilityState !== 'visible') input.clear(); });
  on(chatInput, 'focus', () => input.clear());
  on(chatInput, 'input', updateCounter);
  on(sendBtn, 'click', () => { trySend(); });
  on(canvas, 'pointerdown', () => canvas.focus({ preventScroll: true }));
  // 포커스 테두리는 Tab 키로 캔버스에 들어왔을 때만 (자동/마우스 포커스는 표시 안 함)
  let tabNav = false;
  on(window, 'keydown', (e) => { tabNav = e.key === 'Tab'; }, { capture: true });
  on(window, 'pointerdown', () => { tabNav = false; canvas.classList.remove('kbd-focus'); }, { capture: true });
  on(canvas, 'focus', () => canvas.classList.toggle('kbd-focus', tabNav));
  on(canvas, 'blur', () => canvas.classList.remove('kbd-focus'));

  for (const [btn, dir, id] of [[leftBtn, -1, 'touch:left'], [rightBtn, 1, 'touch:right']]) {
    const release = () => { input.release(id); btn.classList.remove('pressed'); };
    on(btn, 'pointerdown', (e) => {
      e.preventDefault();
      if (connection !== 'connected') return;
      input.press(id, dir);
      btn.classList.add('pressed');
    });
    on(btn, 'pointerup', release);
    on(btn, 'pointercancel', release);
    on(btn, 'pointerleave', release);
    on(btn, 'contextmenu', (e) => e.preventDefault());
  }

  on(bannerBtn, 'click', async () => {
    bannerBtn.disabled = true;
    if (connection === 'fatal') {
      await firstJoin();
    } else if (connection === 'failed') {
      setConnection('disconnected');
      try {
        await leaveMap();
        await join();
        if (alive) setConnection('connected');
      } catch {
        if (alive) setConnection('failed');
      }
    }
    bannerBtn.disabled = false;
  });

  let loggingOut = false;
  on(logoutBtn, 'click', async () => {
    if (loggingOut) return;
    loggingOut = true;
    logoutBtn.disabled = true;
    await cleanup();
    await app.forceLogout();
  });

  let resizeQueued = false;
  const onResize = () => {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => { resizeQueued = false; if (alive) computeLayout(); });
  };
  on(window, 'resize', onResize);
  if (window.visualViewport) on(window.visualViewport, 'resize', onResize);

  // --- 테스트 훅 상태 공급 -----------------------------------------------------
  const snap = (p) => ({ user_id: p.user_id, nickname: p.nickname, x: Math.round(p.x * 10) / 10, y: p.y, lastChat: p.lastChat, anim: p.anim });
  app.gameStateProvider = () => ({
    connection,
    assets: assets ? {
      source: assets.source, images: assets.imageCount, background: !!(map && map.layerCount),
      mapLayers: map ? map.layerCount : 0, ui: ui ? ui.source : null,
    } : null,
    me: me ? { ...snap(me), avatar: { ...me.avatar }, dir: me.dir < 0 ? 'left' : 'right' } : null,
    players: [...players.values()].map(snap),
  });

  // --- 정리 -----------------------------------------------------------------
  let cleaned = null;
  function cleanup() {
    if (cleaned) return cleaned;
    alive = false;
    cancelAnimationFrame(raf);
    raf = 0;
    ac.abort();
    for (const t of timers) clearTimeout(t);
    timers.clear();
    input.clear();
    if (app.gameStateProvider) app.gameStateProvider = null;
    avatarR?.clear();
    cleaned = (async () => {
      const m = link;
      link = null;
      joinGen++;
      if (m) { try { await m.leave(); } catch { /* 무시 */ } }
    })();
    return cleaned;
  }

  // --- 시작 -----------------------------------------------------------------
  setConnection('joining');
  computeLayout();

  (async () => {
    try {
      assets = await app.assets;
    } catch {
      if (alive) setConnection('fatal');
      return;
    }
    if (!alive) return;
    if (!character) { app.forceLogout(); return; }
    [map, ui] = await Promise.all([app.mapAssets.catch(() => null), app.uiAssets.catch(() => null)]);
    if (!alive) return;
    avatarR = createAvatarRenderer(assets);
    const startX = clampX(300 + Math.floor(Math.random() * 600));
    me = makePlayer(character.user_id, character.nickname, assets.sanitizeAvatar(character.avatar), startX, true);
    players.set(me.user_id, me);
    updateCount();
    raf = requestAnimationFrame(frame);
    await firstJoin();
  })();

  return {
    unmount() {
      return cleanup();
    },
  };
}
