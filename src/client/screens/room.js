// 방 화면: 맵 + 캐릭터 + 말풍선 + HUD + 채팅 로그 (docs/design/screens/room.md v4, style-guide 6~8장·11.9)
// 캔버스(배율/카메라/그리기 순서/라벨/말풍선)와 이동·터치·채팅 입력은 v3 game 화면 그대로.
// 바뀐 것: 방 HUD(방 이름 + 자물쇠, 인원 n/20, 나가기), 채팅 로그 패널, 채팅 전송 = sendChat RPC,
//          말풍선/로그 = 서버 chat 이벤트 기반(내 메시지도 RPC 성공 후), 시스템 메시지(Presence join/leave).
// 사용자 문자열은 Canvas fillText / textContent로만 넣는다.
import { h, setText, wait } from '../dom.js';
import {
  WORLD, HEAD, BUBBLE, PAL, MOBILE_MAX_WIDTH, MOBILE_CONTROLS_H, MOBILE_MIN_CANVAS_H, DESKTOP_RESERVED_H, NICK_RE,
  CHAT_MAX, CHAT_COOLDOWN_MS, MOVE_INTERVAL_MS, RECONNECT_DELAYS_MS, ROOM_CAPACITY, LEAVE_WAIT_MS, SYS_LEAVE_DELAY_MS, pixelScale,
} from '../constants.js';
import { ROOM_MESSAGES as M, toAppError } from '../errors.js';
import { createAvatarRenderer, smooth } from '../avatar.js';
import { drawMap, drawFootShadow, cameraFor } from '../game/world.js';
import { layoutBubble, drawBubble, drawLabel, bubbleAlpha } from '../game/overlay.js';
import { createMoveInput, KEY_DIR } from '../game/input.js';
import { createChatLog } from '../ui/chatlog.js';
import { clearRoomSession } from '../store.js';
import { cleanChatText } from '../backend/common.js';

const CONNECT_TIMEOUT_MS = 12000;
const REMOTE_SNAP_DIST = 400; // 이보다 멀면 순간 이동
const REMOTE_CATCHUP = 32; // 뒤처진 거리(월드 단위)마다 속도를 1배씩 더한다
const WALK_HOLD_MS = 200; // 원격 아바타: 마지막으로 움직인 뒤 200ms 안이면 walk (패킷 간격 100ms 흡수)
const TRACK_IDLE_MS = 600; // 정지 후 Presence 좌표 갱신
const DESKTOP_MAX_VIEW_W = 1280; // 데스크톱 시야 가로 최대 (월드): P=2 → 1280px, P=3 → 1920px

const clampX = (x) => Math.min(WORLD.maxX, Math.max(WORLD.minX, x));
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
// 입력 단계: 제어 문자(줄바꿈 포함)는 공백으로 (서버는 제어문자를 거부한다)
const cleanInput = (s) => s.replace(/[\u0000-\u001F\u007F-\u009F\u2028\u2029]/g, ' ');

export function mount(root, app, opts = {}) {
  const ac = new AbortController();
  const on = (el, type, fn, o) => el.addEventListener(type, fn, { signal: ac.signal, ...o });
  let alive = true;

  const roomId = opts.roomId;
  const roomName = typeof opts.name === 'string' && opts.name ? opts.name : '방';
  const locked = !!opts.locked;
  const myNick = opts.nickname;
  const profile = app.profile;

  let assets = null;
  let avatarR = null;
  let map = null; // loadMapAssets() 결과
  let link = null; // { sendMove, updateSelf, leave }
  let joinGen = 0;
  let connection = 'joining'; // joining | connected | disconnected | failed | lost | fatal
  let reconnecting = false;
  let raf = 0;
  let lastFrame = 0;
  const input = createMoveInput();
  const timers = new Set();
  const later = (fn, ms) => { const t = setTimeout(() => { timers.delete(t); fn(); }, ms); timers.add(t); return t; };
  const cancel = (t) => { if (t) { clearTimeout(t); timers.delete(t); } };

  /** user_id -> player */
  const players = new Map();
  let me = null;

  // 레이아웃 (style-guide 6.1): P = 표시 배율 (CSS px / 월드 = P/2), view = 월드 단위 시야, k = 장치 px / 월드
  let layout = { mobile: false, cssW: 2, cssH: 2, viewW: 1, viewH: 1, P: 2, dpr: 1, k: 1 };

  // 네트워크 송신 상태
  let lastMoveSentAt = 0;
  let sentX = null;
  let sentDir = null;
  let lastChatAt = -Infinity;
  let trackTimer = 0;

  // --- DOM (room.md 2~4장, ui-kit 22~23절) ------------------------------------------
  const roomChip = h('span', { class: 'bk-chip hud-room', testid: 'room-title', title: roomName },
    locked ? h('span', { class: 'bk-ico bk-ico--lock', 'aria-hidden': 'true' }) : null,
    locked ? h('span', { class: 'bk-sr' }, '비밀번호 방') : null,
    h('span', { testid: 'room-title-text' }, roomName));
  const countText = h('span', { testid: 'player-count' }, `1/${ROOM_CAPACITY}명`);
  const countDot = h('span', { class: 'bk-dot-off', title: '연결 끊김', hidden: true });
  const countChip = h('span', { class: 'bk-chip bk-count', testid: 'room-count-chip', 'aria-live': 'off' },
    h('span', { class: 'bk-ico bk-ico--user', 'aria-hidden': 'true' }), countText, countDot);
  const modeSlot = h('span', { class: 'mode-slot' });
  const hint = h('div', { class: 'bk-chip bk-chip--hint hint-desktop' }, M.HINT);
  const leaveDots = h('span', { class: 'bk-dots', 'aria-hidden': 'true', hidden: true }, h('i'), h('i'), h('i'));
  const leaveIcon = h('span', { class: 'bk-ico bk-ico--arrow bk-ico--left', 'aria-hidden': 'true' });
  const leaveText = h('span', {}, '나가기');
  const leaveBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--sm', testid: 'room-leave' }, leaveIcon, leaveDots, leaveText);
  const hudL = h('div', { class: 'hud-l' }, roomChip, countChip, modeSlot);
  const hud = h('div', { class: 'hud' }, hudL, h('div', { class: 'hud-r' }, hint, leaveBtn));
  const modeSlot2 = h('span', { class: 'mode-slot' });

  const bannerText = h('span', {});
  const bannerBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--primary bk-btn--sm', testid: 'reconnect-button', hidden: true });
  const banner = h('div', { class: 'hud-banner bk-banner', testid: 'game-banner', role: 'status', hidden: true }, bannerText, bannerBtn);

  const canvas = h('canvas', {
    class: 'game-canvas', testid: 'game-canvas', tabindex: '0',
    'aria-label': `${roomName} 맵. 좌우 방향키로 이동, Enter로 채팅`,
  });
  const loadingDots = h('span', { class: 'bk-dots canvas-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'));
  const stage = h('div', { class: 'game-stage' }, canvas, hud, banner, loadingDots);

  const chatLog = createChatLog({
    onLayout: () => stage.classList.toggle('log-open', chatLog ? chatLog.desktopExpanded() : false),
  });
  const row2 = h('div', { class: 'hud-row2' }, chatLog.toggle, modeSlot2);
  // Tab 순서: 캔버스 → 나가기 → (모바일) 채팅 기록 토글 → 로그 → 채팅 입력 (9장)
  stage.append(row2, chatLog.el);
  stage.classList.toggle('log-open', chatLog.desktopExpanded());

  const leftBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--touch', testid: 'move-left', 'aria-label': '왼쪽으로 이동' },
    h('span', { class: 'bk-ico bk-ico--arrow bk-ico--left', 'aria-hidden': 'true' }), '왼쪽');
  const rightBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--touch', testid: 'move-right', 'aria-label': '오른쪽으로 이동' },
    '오른쪽', h('span', { class: 'bk-ico bk-ico--arrow', 'aria-hidden': 'true' }));
  const touchRow = h('div', { class: 'touch-row' }, leftBtn, rightBtn);

  const chatInput = h('input', {
    type: 'text', class: 'bk-input bk-input--with-end', testid: 'chat-input', maxlength: String(CHAT_MAX), placeholder: '메시지를 입력하세요',
    autocomplete: 'off', 'aria-label': '채팅 메시지', enterkeyhint: 'send',
  });
  const counter = h('span', { class: 'bk-counter', testid: 'chat-counter', hidden: true, 'aria-hidden': 'true' });
  const sendBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--primary chat-send', testid: 'chat-send', disabled: true }, '보내기');
  const chatHint = h('div', { class: 'bk-chip bk-chip--hint chat-float', testid: 'chat-hint', hidden: true }, M.COOLDOWN);
  const chatError = h('div', { class: 'bk-banner bk-banner--error chat-float', testid: 'chat-error', role: 'alert', hidden: true });
  const chatRow = h('div', { class: 'chat-row' }, chatHint, chatError,
    h('div', { class: 'bk-input-wrap' }, chatInput, h('span', { class: 'bk-input-end' }, counter)),
    sendBtn);

  const col = h('main', { class: 'scr-game scr-room' }, stage, touchRow, chatRow);
  root.append(col);

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
    // CSS 크기는 P의 배수(기존 규칙 유지), 시야(월드) = CSS / (P/2)
    if (mobile) {
      P = 2;
      cssW = Math.floor(vw / P) * P;
      cssH = Math.max(MOBILE_MIN_CANVAS_H, Math.floor((vh - MOBILE_CONTROLS_H) / P) * P);
    } else {
      P = pixelScale(vw, vh);
      cssW = Math.min(Math.floor(vw / P) * P, (DESKTOP_MAX_VIEW_W * P) / 2); // 1280 (P=2), 1920 (P=3)
      cssH = Math.min((WORLD.height * P) / 2, Math.floor((vh - DESKTOP_RESERVED_H) / P) * P);
    }
    cssW = Math.max(P, cssW);
    let viewH = (cssH * 2) / P;
    if (viewH < WORLD.minViewH) { viewH = WORLD.minViewH; cssH = (viewH * P) / 2; }
    const viewW = (cssW * 2) / P;
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const k = (P / 2) * dpr;
    const modeChanged = layout.mobile !== mobile || !root.dataset.layout;
    layout = { mobile, cssW, cssH, viewW, viewH, P, dpr, k };
    root.dataset.layout = mobile ? 'mobile' : 'desktop';
    root.style.setProperty('--canvas-w', `${cssW}px`);
    // .game-stage는 캔버스와 같은 CSS 크기 (로그 패널 clamp의 % 기준, design handoff 5-11)
    stage.style.width = `${cssW}px`;
    stage.style.height = `${cssH}px`;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    hint.classList.toggle('narrow', cssW < 900); // 캔버스 가로 900px 미만이면 조작 힌트 숨김
    if (modeChanged) {
      chatLog.setMobile(mobile);
      // LOCAL MODE 칩: 데스크톱은 HUD 첫 줄, 모바일은 2줄째 (room.md 3.1, 4.1)
      app.placeModeBadge(mobile ? modeSlot2 : modeSlot);
    }
    if (connection === 'joining' || connection === 'fatal') paintLetterbox();
    else render(performance.now());
  }

  function paintLetterbox() {
    const c = canvas.getContext('2d');
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.fillStyle = PAL.ink;
    c.fillRect(0, 0, canvas.width, canvas.height);
  }

  // --- 상태/배너 (7장) ----------------------------------------------------------
  let bannerHideTimer = 0;
  let bannerAction = null;
  function setBanner(kind, text, button, action) {
    cancel(bannerHideTimer);
    banner.classList.remove('fade-out');
    bannerAction = action || null;
    if (!kind) { banner.hidden = true; return; }
    banner.hidden = false;
    banner.className = kind === 'error' ? 'hud-banner bk-banner bk-banner--error' : 'hud-banner bk-banner';
    banner.setAttribute('role', kind === 'error' && button ? 'alert' : 'status');
    setText(bannerText, text);
    if (button) { setText(bannerBtn, button); bannerBtn.hidden = false; bannerBtn.disabled = false; } else bannerBtn.hidden = true;
  }

  function setConnection(next) {
    const prev = connection;
    connection = next;
    root.dataset.connection = next;
    const full = next === 'connected' || next === 'disconnected' || next === 'failed';
    // 들어가는 중: 방 이름 + 나가기만 / 방 연결 끊김·치명적 오류: 나가기만
    roomChip.hidden = next === 'lost' || next === 'fatal';
    countChip.hidden = !full;
    hint.hidden = !full;
    modeSlot.hidden = !full;
    row2.hidden = !full;
    chatLog.el.classList.toggle('is-hidden-fatal', next === 'fatal');
    chatRow.classList.toggle('is-hidden', !full);
    touchRow.classList.toggle('is-hidden', !full);
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
        setBanner('error', M.RECONNECT_FAILED, '다시 연결', 'reconnect');
        break;
      case 'lost':
        setBanner('error', M.NOT_MEMBER, '로비로', 'lobby');
        break;
      case 'fatal':
        setBanner('error', M.FATAL, '다시 시도', 'retry');
        paintLetterbox();
        break;
      default:
        break;
    }
  }

  function updateCount() {
    const n = Math.min(players.size, 999);
    setText(countText, `${n}/${ROOM_CAPACITY}명`);
    countChip.classList.toggle('is-full', n >= ROOM_CAPACITY);
    countChip.setAttribute('aria-label', `접속 인원 ${n}명, 최대 ${ROOM_CAPACITY}명`);
  }

  // --- 플레이어 -------------------------------------------------------------
  function makePlayer(uid, nickname, avatar, x, isSelf) {
    return {
      user_id: uid, nickname, avatar, x, targetX: x, y: WORLD.groundY, dir: 1,
      moving: false, lastMoveAt: 0, lastMovedAt: -Infinity, anim: 'idle', animSince: performance.now(),
      bubble: null, lastChat: null, isSelf,
    };
  }

  function setBubble(p, text) {
    p.lastChat = text;
    p.bubble = { text, at: performance.now(), layout: layoutBubble(canvas.getContext('2d'), text) };
  }

  const nickOf = (s) => (s && typeof s.nickname === 'string' && NICK_RE.test(s.nickname) ? s.nickname : '???');

  // 입장/퇴장 시스템 메시지 (5.3-6): 퇴장은 3초 미뤘다가 그 사이 재입장하면 둘 다 버린다
  const pendingLeaves = new Map(); // user_id -> timer
  function sysJoin(st) {
    const t = pendingLeaves.get(st.user_id);
    if (t) { cancel(t); pendingLeaves.delete(st.user_id); return; }
    chatLog.addSystem(M.JOINED(nickOf(st)));
  }
  function sysLeave(st) {
    if (pendingLeaves.has(st.user_id)) return;
    const nick = nickOf(st);
    pendingLeaves.set(st.user_id, later(() => {
      pendingLeaves.delete(st.user_id);
      if (alive) chatLog.addSystem(M.LEFT(nick));
    }, SYS_LEAVE_DELAY_MS));
  }

  const handlersFor = (gen) => {
    const live = () => alive && gen === joinGen && me;
    return {
      onSync(list) {
        if (!live() || !Array.isArray(list)) return;
        const seen = new Set([me.user_id]);
        for (const s of list) {
          if (!s || typeof s.user_id !== 'string' || !s.user_id || s.user_id.length > 64 || s.user_id === me.user_id) continue;
          seen.add(s.user_id);
          const nickname = nickOf(s);
          const avatar = assets.sanitizeAvatar(s.avatar); // 7개 키 정규화 (옛 5키/eyes/없는 id → 기본값)
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
      onJoin(st) { if (live() && st && st.user_id !== me.user_id) sysJoin(st); },
      onLeave(st) { if (live() && st && st.user_id !== me.user_id) sysLeave(st); },
      onMove(p) {
        if (!live() || !p || typeof p !== 'object') return;
        const pl = typeof p.user_id === 'string' ? players.get(p.user_id) : null;
        if (!pl || pl.isSelf || !isNum(p.x)) return; // Presence에 없는 user_id는 버린다
        pl.targetX = clampX(p.x);
        if (p.dir === 'left' || p.dir === -1) pl.dir = -1;
        else if (p.dir === 'right' || p.dir === 1) pl.dir = 1;
        pl.lastMoveAt = performance.now();
      },
      /** 서버 chat (어댑터가 id로 중복 제거, sendChat 반환값도 이 경로). 로그 + 말풍선 */
      onChat(msg) {
        if (!live() || !msg) return;
        const self = msg.user_id === me.user_id;
        if (!chatLog.addChat(msg, self)) return; // 기록과 겹친 id
        const pl = players.get(msg.user_id);
        if (pl) setBubble(pl, msg.text);
      },
      onStatus(st) {
        if (!live()) return;
        if (st === 'connected') {
          if (connection === 'disconnected' || connection === 'failed') reconnected();
        } else if (st === 'disconnected') {
          reconnect();
        } else if (st === 'not_member') {
          memberLost();
        }
      },
    };
  };

  async function connect() {
    const gen = ++joinGen;
    const self = { nickname: me.nickname, avatar: me.avatar, x: Math.round(me.x), y: me.y };
    let timeoutId = 0;
    const joined = await Promise.race([
      app.backend.connectRoom(roomId, handlersFor(gen), self),
      new Promise((_, reject) => { timeoutId = later(() => reject(toAppError(null, 'NETWORK')), CONNECT_TIMEOUT_MS); }),
    ]).finally(() => cancel(timeoutId));
    if (!alive || gen !== joinGen) {
      try { await joined.leave(); } catch { /* 무시 */ }
      throw new Error('stale');
    }
    link = joined;
    sentX = Math.round(me.x);
    sentDir = me.dir;
  }

  async function disconnect() {
    const m = link;
    link = null;
    joinGen++;
    cancel(trackTimer);
    if (m) {
      try { await m.leave(); } catch { /* 무시 */ }
    }
  }

  async function loadHistory(merge) {
    if (!merge) chatLog.setLoading(true);
    try {
      const msgs = await app.backend.recentMessages(roomId);
      if (!alive) return;
      if (merge) chatLog.merge(msgs, me.user_id);
      else {
        chatLog.loadHistory(msgs, me.user_id);
        chatLog.addSystem(M.JOINED(me.nickname)); // 기록 → 구분 줄 → 내 입장 (5.3-1, 2)
      }
    } catch {
      if (!alive) return;
      if (!merge) {
        chatLog.historyFailed();
        chatLog.addSystem(M.JOINED(me.nickname));
      }
    }
  }

  function reconnected() {
    setConnection('connected');
    chatLog.addSystem(M.LOG_RECONNECTED);
    loadHistory(true); // 빠진 메시지를 id 순서대로 끼워 넣는다
  }

  async function reconnect() {
    if (reconnecting || !alive || connection === 'lost') return;
    reconnecting = true;
    if (connection !== 'disconnected') chatLog.addSystem(M.LOG_DISCONNECTED, 'error');
    setConnection('disconnected');
    for (const d of RECONNECT_DELAYS_MS) {
      await wait(d, ac.signal);
      if (!alive || connection === 'lost') { reconnecting = false; return; }
      if (connection === 'connected') { reconnecting = false; return; } // 어댑터가 스스로 복구함
      try {
        await disconnect();
        await connect();
        if (!alive) return;
        reconnecting = false;
        reconnected();
        return;
      } catch (err) {
        if (!alive) return;
        if (toAppError(err).code === 'NOT_MEMBER') { reconnecting = false; memberLost(); return; }
      }
    }
    if (!alive) return;
    reconnecting = false;
    setConnection('failed');
  }

  // 방 연결 끊김 (NOT_MEMBER: 하트비트 만료, 닉네임 양보 등): 같은 닉네임으로 자동 재입장 (보관한 비밀번호 없음)
  // 메인 결정 (2026-10-15, QA D-1): "자동 재입장 1회"는 세션당이 아니라 끊김이 생길 때마다 1회.
  // - 끊김 하나에 재입장 시도는 1번. 그 시도가 실패하면 "방과 연결이 끊어졌어요" 배너(lost).
  // - 재입장 성공(정상 연결 복구) 시 다음 끊김에서 다시 1회 시도할 수 있다.
  // - 무한 루프 방지: 직전 시도 시작 후 REJOIN_MIN_GAP_MS(10초)가 지나기 전 새 끊김은 남은 시간만큼 기다렸다가 시도한다.
  //   시도 중/대기 중에 들어온 추가 NOT_MEMBER 신호(하트비트, 전송 실패 등)는 같은 끊김으로 보고 무시한다.
  const REJOIN_MIN_GAP_MS = 10000;
  let rejoinBusy = false; // 시도 중 또는 대기 중
  let lastRejoinAt = -Infinity;
  let rejoinWait = 0;
  function memberLost() {
    if (!alive || connection === 'lost' || rejoinBusy) return;
    rejoinBusy = true;
    const gap = REJOIN_MIN_GAP_MS - (performance.now() - lastRejoinAt);
    if (gap > 0) rejoinWait = later(() => { rejoinWait = 0; tryRejoin(); }, gap);
    else tryRejoin();
  }
  async function tryRejoin() {
    if (!alive) return;
    lastRejoinAt = performance.now();
    try {
      await app.backend.joinRoom({ roomId, password: null, nickname: myNick });
      if (!alive) return;
      await disconnect();
      await connect();
      if (!alive) return;
      if (connection !== 'connected') reconnected();
      rejoinBusy = false; // 복구됨 → 다음 끊김에서 다시 1회 시도
    } catch {
      if (!alive) return;
      await disconnect();
      rejoinBusy = false;
      setConnection('lost'); // 이 끊김의 재시도 실패 → 배너 "로비로"
    }
  }

  async function firstJoin() {
    setConnection('joining');
    loadHistory(false); // 캔버스를 막지 않음 (1.1)
    try {
      await connect();
      if (!alive) return;
      setConnection('connected');
      canvas.focus({ preventScroll: true });
    } catch (err) {
      if (!alive) return;
      if (toAppError(err).code === 'NOT_MEMBER') { memberLost(); return; }
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
        const l = link;
        l.sendMove({ x: rx, y: WORLD.groundY, dir: me.dir < 0 ? 'left' : 'right' }).catch(() => {});
        cancel(trackTimer);
        trackTimer = later(() => { if (link === l) l.updateSelf({ x: Math.round(me.x), y: me.y }).catch(() => {}); }, TRACK_IDLE_MS);
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
    return avatarR.frameAt(p.anim === 'walk' ? 'walk' : 'idle', now - p.animSince);
  }

  // 그리기 파이프라인 (복셀 계약, 사이클 5): 메인 캔버스 백킹(CSS x dpr)에 바로, 고품질 스무딩.
  //   맵 레이어 → 발 그림자 → 아바타 (장치 px, k = P/2 x dpr) → 라벨/말풍선 (CSS px, setTransform(dpr))
  function render(now) {
    if (!me || !avatarR) return;
    if (connection === 'joining' || connection === 'fatal') { paintLetterbox(); return; }
    const { cssW, viewW, viewH, P, dpr, k } = layout;
    const { camX, camY } = cameraFor(me.x, viewW, viewH, k);
    const ctx = canvas.getContext('2d');
    drawMap(ctx, map, camX, camY, k, canvas.width, canvas.height);

    const gy = WORLD.groundY - camY; // 지면선 (시야 기준 월드)
    const order = [];
    for (const p of players.values()) if (!p.isSelf) order.push(p);
    order.sort((a, b) => a.x - b.x);
    order.push(me); // 내 캐릭터는 마지막
    const visible = [];
    const margin = avatarR.worldW;
    for (const p of order) {
      const sx = p.x - camX;
      if (sx < -margin || sx > viewW + margin) continue;
      visible.push([p, sx]);
    }
    const fyD = Math.round(gy * k);
    for (const [, sx] of visible) drawFootShadow(ctx, sx * k, fyD, k);
    smooth(ctx);
    for (const [p, sx] of visible) avatarR.draw(ctx, p.avatar, Math.round(sx * k), fyD, k, frameOf(p, now), p.dir < 0);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const u = P / 2; // CSS px / 월드
    const fy = fyD / dpr; // 발바닥 선 (CSS px)
    for (const [p, sx] of visible) drawLabel(ctx, p.nickname, sx * u, fy, p.isSelf, cssW);
    // 말풍선: 먼저 받은 것부터 그려 최신이 위 (style-guide 6.3-6). 꼬리 끝 = 머리(모자) 맨 위 + HEAD.gap
    const talking = visible.filter(([p]) => p.bubble).sort((a, b) => a[0].bubble.at - b[0].bubble.at);
    for (const [p, sx] of talking) {
      const head = (avatarR.headTop(p.avatar) + HEAD.gap) * u;
      drawBubble(ctx, p.bubble.layout, sx * u, fy, head, cssW, bubbleAlpha(now - p.bubble.at));
    }
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(Math.max((now - (lastFrame || now)) / 1000, 0), WORLD.maxDt);
    lastFrame = now;
    update(dt, now);
    render(now);
  }

  // --- 채팅 (6장) -------------------------------------------------------------
  let hintTimer = 0;
  let errorTimer = 0;
  let cooldownTimer = 0;
  let sending = false;

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
  function showHint(text = M.COOLDOWN) {
    setText(chatHint, text);
    chatHint.hidden = false;
    cancel(hintTimer);
    hintTimer = later(() => { chatHint.hidden = true; }, text === M.COOLDOWN ? 800 : 2000);
  }
  function showSendError(text) {
    setText(chatError, text);
    chatError.hidden = false;
    cancel(errorTimer);
    errorTimer = later(() => { chatError.hidden = true; }, 2000);
  }

  function trySend() {
    if (connection !== 'connected' || !link) return;
    const raw = chatInput.value;
    const text = cleanChatText(cleanInput(raw));
    if (!text) { if (raw.trim()) showSendError(M.TEXT_FORMAT); return; }
    if (inCooldown() || sending) { showHint(); return; }
    lastChatAt = performance.now();
    sending = true;
    chatInput.value = '';
    updateCounter();
    cancel(cooldownTimer);
    cooldownTimer = later(updateSendBtn, CHAT_COOLDOWN_MS + 10);
    // 서버 저장 성공 → 어댑터가 onChat으로 전달 (로그 + 말풍선). 실패하면 입력 복구 + 오류.
    app.backend.sendChat(roomId, text).then(() => {
      sending = false;
    }, (err) => {
      sending = false;
      if (!alive) return;
      if (!chatInput.value) { chatInput.value = raw; updateCounter(); }
      const code = toAppError(err).code;
      if (code === 'RATE_LIMITED') showHint(M.SEND_RATE_LIMITED);
      else if (code === 'TEXT_FORMAT') showSendError(M.TEXT_FORMAT);
      else if (code === 'NOT_MEMBER') memberLost();
      else showSendError(M.SEND_FAILED);
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
    // 로그 목록에 포커스가 있으면 방향키는 목록 스크롤에 양보한다
    if (dir && !isTypingTarget(document.activeElement) && !chatLog.el.contains(document.activeElement)) {
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
    const release = () => { input.release(id); btn.classList.remove('is-pressed'); };
    on(btn, 'pointerdown', (e) => {
      e.preventDefault();
      if (connection !== 'connected') return;
      input.press(id, dir);
      btn.classList.add('is-pressed');
    });
    on(btn, 'pointerup', release);
    on(btn, 'pointercancel', release);
    on(btn, 'pointerleave', release);
    on(btn, 'contextmenu', (e) => e.preventDefault());
  }

  on(bannerBtn, 'click', async () => {
    const action = bannerAction;
    bannerBtn.disabled = true;
    if (action === 'lobby') { goLobby(); return; }
    if (action === 'retry') {
      await disconnect();
      await firstJoin();
    } else if (action === 'reconnect') {
      setConnection('disconnected');
      try {
        await disconnect();
        await connect();
        if (alive) reconnected();
      } catch (err) {
        if (!alive) return;
        if (toAppError(err).code === 'NOT_MEMBER') memberLost();
        else setConnection('failed');
      }
    }
    if (alive) bannerBtn.disabled = false;
  });

  // --- 나가기 (1.2): 확인 창 없음. leave_room 최대 1.5초 기다리고 실패해도 로비로 ------------
  let leaving = false;
  async function goLobby() {
    if (leaving) return;
    leaving = true;
    leaveBtn.disabled = true;
    leaveIcon.hidden = true;
    leaveDots.hidden = false;
    setText(leaveText, M.LEAVING);
    const ch = disconnect();
    const rpc = app.backend.leaveRoom(roomId).catch(() => {});
    await Promise.race([Promise.all([ch, rpc]), wait(LEAVE_WAIT_MS)]);
    clearRoomSession();
    app.go('lobby');
  }
  on(leaveBtn, 'click', () => goLobby());

  let resizeQueued = false;
  const onResize = () => {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(() => { resizeQueued = false; if (alive) computeLayout(); });
  };
  on(window, 'resize', onResize);
  if (window.visualViewport) on(window.visualViewport, 'resize', onResize);

  // --- 테스트 훅 상태 공급 -----------------------------------------------------
  const snap = (p) => ({
    user_id: p.user_id, nickname: p.nickname, avatar: { ...p.avatar }, x: Math.round(p.x * 10) / 10, y: p.y,
    dir: p.dir < 0 ? 'left' : 'right', lastChat: p.lastChat, bubble: p.bubble ? p.bubble.text : null, anim: p.anim,
    frame: avatarR ? frameOf(p, performance.now()) : null,
  });
  app.providers.room = () => ({
    room: { id: roomId, name: roomName, locked, members: players.size, nickname: myNick },
    chatLog: chatLog.snapshot(50),
    log: chatLog.ui(),
    connection,
    assets: assets ? {
      source: assets.source, images: assets.imageCount, imageTotal: assets.imageTotal, background: !!(map && map.layerCount),
      mapLayers: map ? map.layerCount : 0, sheets: avatarR ? avatarR.cacheSize : 0,
      composite: avatarR ? { count: avatarR.stats.composites, avgMs: avatarR.stats.composites ? Math.round((avatarR.stats.totalMs / avatarR.stats.composites) * 10) / 10 : 0, maxMs: Math.round(avatarR.stats.maxMs * 10) / 10 } : null,
      layout: { P: layout.P, cssW: layout.cssW, cssH: layout.cssH, viewW: layout.viewW, viewH: layout.viewH, k: layout.k },
    } : null,
    me: me ? snap(me) : null,
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
    pendingLeaves.clear();
    input.clear();
    if (app.providers.room) app.providers.room = null;
    avatarR?.clear();
    chatLog.destroy();
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
    if (!profile || !roomId || !NICK_RE.test(myNick || '')) { clearRoomSession(); app.go('lobby'); return; }
    map = await app.mapAssets.catch(() => null);
    if (!alive) return;
    avatarR = createAvatarRenderer(assets);
    const startX = clampX(300 + Math.floor(Math.random() * 600));
    me = makePlayer(app.userId || 'me', myNick, assets.sanitizeAvatar(profile.avatar), startX, true);
    await avatarR.ready(me.avatar); // 내 조합의 레이어만 받고 합성 (다른 사람 조합은 그릴 때 지연 로드)
    if (!alive) return;
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
