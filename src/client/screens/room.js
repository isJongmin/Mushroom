// 방 화면: 맵 + 캐릭터 + 말풍선 + HUD + 채팅 로그 (docs/design/screens/room.md v4, style-guide 6~8장·11.9)
// 캔버스(배율/카메라/그리기 순서/라벨/말풍선)와 이동·터치·채팅 입력은 v3 game 화면 그대로.
// 바뀐 것: 방 HUD(방 이름 + 자물쇠, 인원 n/20, 나가기), 채팅 로그 패널, 채팅 전송 = sendChat RPC,
//          말풍선/로그 = 서버 chat 이벤트 기반(내 메시지도 RPC 성공 후), 시스템 메시지(Presence join/leave).
// 사용자 문자열은 Canvas fillText / textContent로만 넣는다.
// (사이클 6) 연결: backend/room-link.js 상태기계(join_room 'OK' 뒤 구독, 세대 번호, 지수 백오프, 하트비트, 탭 복귀 점검).
//            Presence track은 입장 1회(어댑터), 위치는 move { x, y, dir, s }로만. 새 멤버가 오면 내 상태를 move로 1회.
//            점프: game/physics.js (중력 2000, 초속 650).
// (사이클 8) 발판(한 방향 통과, 맵 manifest platforms), 엎드리기(prone), ↓+점프 내려가기, 슈퍼 점프(더블탭) + 이펙트(game/fx.js),
//            원격 세로는 받은 y를 그대로 보간(물리 재계산 없음), 세로 카메라, 방 삭제(방장 HUD 버튼, room_closed → 로비 + 배너).
import { h, setText, wait } from '../dom.js';
import {
  WORLD, HEAD, BUBBLE, PAL, MOBILE_MAX_WIDTH, MOBILE_CONTROLS_H, MOBILE_MIN_CANVAS_H, DESKTOP_RESERVED_H, NICK_RE,
  CHAT_MAX, CHAT_COOLDOWN_MS, MOVE_INTERVAL_MS, ROOM_CAPACITY, LEAVE_WAIT_MS, SYS_LEAVE_DELAY_MS, pixelScale,
} from '../constants.js';
import { ROOM_MESSAGES as M, LOBBY_MESSAGES as LM, AppError, toAppError } from '../errors.js';
import { createAvatarRenderer, smooth } from '../avatar.js';
import { drawMap, drawFootShadow, cameraFor, camYTarget, drawPlatformDebug } from '../game/world.js';
import { layoutBubble, drawBubble, drawLabel, bubbleAlpha } from '../game/overlay.js';
import { createMoveInput, KEY_DIR, KEY_ACTION, KEY_TAP } from '../game/input.js';
import { PHYS, createBody, stepBody, surfaceBelow, normState, isFx } from '../game/physics.js';
import { createFx, prefersReducedMotion } from '../game/fx.js';
import { openModal } from '../ui/modal.js';
import { createRoomLink } from '../backend/room-link.js';
import { createChatLog } from '../ui/chatlog.js';
import { clearRoomSession } from '../store.js';
import { cleanChatText } from '../backend/common.js';

const REMOTE_SNAP_DIST = 400; // 이보다 멀면 순간 이동
const REMOTE_CATCHUP = 32; // 뒤처진 거리(월드 단위)마다 속도를 1배씩 더한다
const WALK_HOLD_MS = 200; // 원격 아바타: 마지막으로 움직인 뒤 200ms 안이면 walk (패킷 간격 100ms 흡수)
const Y_INTERP_DELAY_MS = 120; // 원격 세로 보간: 받은 (도착 시각, y) 기록을 120ms 늦게 재생하며 두 기록 사이를 직선 보간
const Y_BUF_MAX = 8;
const Y_SNAP_DIST = 320; // 원격 세로 차이가 이보다 크면 순간 이동
const DASH_CHASE_MS = 350; // 원격 대시 fx를 받은 뒤 이 시간 동안 x 추적 속도 하한을 대시 속도로
const CAM_SMOOTH_S = 0.12; // 세로 카메라 따라가기 시간 상수
const CAM_HEAD = 110; // 세로 카메라: 공중에서 머리(발 위 110)가 시야 위 8% 안으로 들어오면 따라 올라간다
const RECONNECT_BUTTON_MIN_MS = 4000; // 백오프 대기가 이보다 길면 배너에 "지금 연결" 버튼
const CLEANUP_WAIT_MS = 2000; // 화면 정리 때 채널 정리를 기다리는 최대 시간
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
  const isOwner = opts.owner === true; // (사이클 8) 방장: 로비 mine / createRoom 결과 / 새로고침 때 list_rooms mine 또는 sessionStorage
  let platforms = Object.freeze([]); // 맵 manifest platforms (없으면 지면만)
  let debugPlatforms = false;
  try { debugPlatforms = sessionStorage.getItem('mushroom.debug.platforms') === '1'; } catch { /* 무시 */ }
  const fx = createFx({ reduced: prefersReducedMotion() });
  let camY = null; // 세로 카메라 (월드). null = 아직 없음
  let camRef = WORLD.groundY; // 세로 카메라 기준 발 높이
  let pendingFx = null; // 다음 move에 1회 실을 fx
  let closingRoom = false; // room_closed 처리 중 (한 번만)
  let deletingSelf = false; // 내가 삭제를 요청했음 → 배너 문구 구분

  let assets = null;
  let avatarR = null;
  let map = null; // loadMapAssets() 결과
  let link = null; // 열린 채널 { sendMove, updateSelf, healthy, close }
  let rl = null; // room-link 상태기계
  let openSeq = 0; // 채널 구독마다 증가: 지난 채널의 늦은 이벤트를 버린다
  let connection = 'joining'; // joining | connected | disconnected | lost | fatal  ('failed'는 사이클 6부터 쓰지 않음)
  let raf = 0;
  let lastFrame = 0;
  const input = createMoveInput();
  const timers = new Set();
  const later = (fn, ms) => { const t = setTimeout(() => { timers.delete(t); fn(); }, ms); timers.add(t); return t; };
  const cancel = (t) => { if (t) { clearTimeout(t); timers.delete(t); } };

  /** user_id -> player */
  const players = new Map();
  // Presence sync보다 먼저 도착한 move (네트워크 순서가 바뀐 경우): 그 사람이 목록에 생길 때 적용한다. 최대 40명분.
  const earlyMoves = new Map();
  let me = null;

  // 레이아웃 (style-guide 6.1): P = 표시 배율 (CSS px / 월드 = P/2), view = 월드 단위 시야, k = 장치 px / 월드
  let layout = { mobile: false, cssW: 2, cssH: 2, viewW: 1, viewH: 1, P: 2, dpr: 1, k: 1 };

  // 네트워크 송신 상태
  let lastMoveSentAt = -Infinity;
  let sentKey = ''; // 마지막으로 보낸 'x|y|dir|s'
  let announce = false; // 다음 송신 기회에 바뀐 것이 없어도 현재 상태를 1회 보낸다 (새 멤버 입장, 재연결)
  let lastChatAt = -Infinity;
  const stats = { superJumps: 0, fxSent: 0 }; // (사이클 8) 계측

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
  // (사이클 8) 방장에게만 보이는 방 삭제 버튼 (확인 모달을 거친다)
  const deleteBtn = isOwner ? h('button', { type: 'button', class: 'bk-btn bk-btn--sm bk-btn--danger', testid: 'room-delete' }, M.DELETE) : null;
  const hudL = h('div', { class: 'hud-l' }, roomChip, countChip, modeSlot);
  const hud = h('div', { class: 'hud' }, hudL, h('div', { class: 'hud-r' }, hint, deleteBtn, leaveBtn));
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
  // testid 'crouch'는 QA 호환으로 유지 (문구는 사이클 8 엎드리기)
  const crouchBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--touch', testid: 'crouch', 'aria-label': '엎드리기 (누르는 동안, 점프와 함께 누르면 발판에서 내려가기)' },
    h('span', { class: 'bk-ico bk-ico--down', 'aria-hidden': 'true' }), '엎드리기');
  const jumpBtn = h('button', { type: 'button', class: 'bk-btn bk-btn--touch', testid: 'jump', 'aria-label': '점프 (두 번 누르면 슈퍼 점프)' },
    h('span', { class: 'bk-ico bk-ico--down bk-ico--up', 'aria-hidden': 'true' }), '점프');
  // 왼손: 좌우 이동(두 번 누르면 대시), 오른손: 엎드리기·점프(두 번 누르면 높이 뛰기) (360x640에서 한 줄 64px 안, 버튼 높이 56)
  const touchRow = h('div', { class: 'touch-row touch-row--4' },
    h('div', { class: 'touch-group' }, leftBtn, rightBtn),
    h('div', { class: 'touch-group' }, crouchBtn, jumpBtn));

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
    if (deleteBtn) deleteBtn.hidden = !(next === 'connected' || next === 'disconnected');
    modeSlot.hidden = !full;
    row2.hidden = !full;
    chatLog.el.classList.toggle('is-hidden-fatal', next === 'fatal');
    chatRow.classList.toggle('is-hidden', !full);
    touchRow.classList.toggle('is-hidden', !full);
    loadingDots.hidden = next !== 'joining';
    countDot.hidden = !(next === 'disconnected' || next === 'failed');
    const interactive = next === 'connected' || next === 'disconnected';
    chatInput.disabled = next !== 'connected';
    for (const b of [leftBtn, rightBtn, crouchBtn, jumpBtn]) b.disabled = !interactive;
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
      s: 'idle', // 이동 상태 idle | walk | jump | fall | prone (원격은 받은 값, 없으면 null → 추정)
      body: isSelf ? createBody(x) : null, // 내 캐릭터 물리
      // 원격 세로: 받은 y 기록 [{ t(도착 performance.now), y }] → Y_INTERP_DELAY_MS 늦게 직선 보간 (물리 재계산 없음)
      yBuf: [], yTo: WORLD.groundY,
      fastUntil: 0, // 원격 대시: x 추적 속도 하한을 높이는 시각
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

  /** 원격 move 적용: x 목표, 방향, 세로(받은 y로 보간, 물리 재계산 없음), s, fx(이펙트 1회) */
  function applyMove(pl, p, now = performance.now()) {
    pl.targetX = clampX(p.x);
    if (p.dir === 'left' || p.dir === -1) pl.dir = -1;
    else if (p.dir === 'right' || p.dir === 1) pl.dir = 1;
    const y = isNum(p.y) ? Math.min(WORLD.groundY, Math.max(PHYS.ceilY, p.y)) : WORLD.groundY;
    const buf = pl.yBuf;
    // 오래 소식이 없었으면(정지 후 다시 움직임) 지금 보이는 높이를 기점으로 다시 시작한다
    const last = buf[buf.length - 1];
    if (!last || now - last.t > Y_INTERP_DELAY_MS * 3 || Math.abs(y - pl.y) > Y_SNAP_DIST) {
      buf.length = 0;
      buf.push({ t: now - Y_INTERP_DELAY_MS, y: Math.abs(y - pl.y) > Y_SNAP_DIST ? y : pl.y });
    }
    buf.push({ t: now, y });
    if (buf.length > Y_BUF_MAX) buf.splice(0, buf.length - Y_BUF_MAX);
    pl.yTo = y;
    pl.s = normState(p.s);
    pl.lastMoveAt = now;
    if (isFx(p.fx)) playFx(pl, p.fx, pl.x, pl.y, now);
  }

  /** 슈퍼 점프 이펙트 재생 (내 캐릭터: 시작 지점, 원격: 지금 보이는 위치) */
  function playFx(pl, kind, x, y, now) {
    if (!avatarR) return;
    fx.spawn(kind, x, y, avatarR.tintOf(pl.avatar), pl);
    if (!pl.isSelf && kind !== 'dash-up') pl.fastUntil = now + DASH_CHASE_MS;
  }

  // 채널 하나(구독 1회)의 이벤트 처리기. token이 최신 구독이 아니면 버린다(지난 채널의 늦은 이벤트).
  const handlersFor = (token) => {
    const live = () => alive && token === openSeq && me;
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
            // Presence x는 입장 시점 값. 그 사람이 내 입장(presence join)을 보고 move로 현재 위치를 1회 보내 준다.
            const x = isNum(s.x) ? clampX(s.x) : WORLD.minX;
            const pl = makePlayer(s.user_id, nickname, avatar, x, false);
            players.set(s.user_id, pl);
            const early = earlyMoves.get(s.user_id);
            if (early) { applyMove(pl, { ...early, fx: null }); pl.x = pl.targetX; pl.y = pl.yTo; pl.yBuf.length = 0; } // 늦은 fx는 재생하지 않는다
          }
        }
        earlyMoves.clear();
        for (const uid of [...players.keys()]) if (!seen.has(uid)) { fx.forget(players.get(uid)); players.delete(uid); }
        updateCount();
      },
      onJoin(st) { if (live() && st && st.user_id !== me.user_id) sysJoin(st); },
      onLeave(st) { if (live() && st && st.user_id !== me.user_id) sysLeave(st); },
      // 다른 사람이 (다시) 들어왔다: 내 현재 상태(x, y, dir, s)를 move로 1회 보낸다. 여러 명이면 한 번으로 합쳐진다.
      onPeerJoin() { if (live()) announce = true; },
      onMove(p) {
        if (!live() || !p || typeof p !== 'object' || typeof p.user_id !== 'string' || !isNum(p.x)) return;
        const pl = players.get(p.user_id);
        if (!pl) { // Presence에 아직 없는 user_id: 다음 sync까지 마지막 값만 보관 (sync에 없으면 버려진다)
          if (earlyMoves.size < 40 || earlyMoves.has(p.user_id)) earlyMoves.set(p.user_id, p);
          return;
        }
        if (!pl.isSelf) applyMove(pl, p);
      },
      /** (사이클 8) 방 삭제 broadcast: 방장 본인 포함. 채널 정리 → 로비 + 배너 */
      onClosed() { if (live()) roomClosed(deletingSelf); },
      /** 서버 chat (어댑터가 id로 중복 제거, sendChat 반환값도 이 경로). 로그 + 말풍선 */
      onChat(msg) {
        if (!live() || !msg) return;
        const self = msg.user_id === me.user_id;
        if (!chatLog.addChat(msg, self)) return; // 기록과 겹친 id
        const pl = players.get(msg.user_id);
        if (pl) setBubble(pl, msg.text);
      },
    };
  };

  /** 상태기계: 첫 입장은 로비/새로고침이 이미 join_room 'OK'를 받은 뒤라 구독부터, 그 뒤 모든 시도는 join → 구독. */
  function createLink() {
    return createRoomLink({
      join: () => app.backend.joinRoom({ roomId, password: null, nickname: myNick }),
      open: (sink, signal) => {
        const token = ++openSeq;
        const self = { nickname: me.nickname, avatar: me.avatar, x: Math.round(me.x), y: Math.round(me.y) };
        return app.backend.connectRoom(roomId, { ...handlersFor(token), onDrop: sink.onDrop }, self, { signal });
      },
      heartbeat: async () => {
        try {
          await app.backend.heartbeat(roomId);
        } catch (e) {
          const code = toAppError(e).code;
          // (사이클 8) room_closed를 놓친 경우: 방이 목록에 없으면 삭제된 것 → 재입장 시도 없이 로비 + 배너.
          // 방이 있으면(10분 비활성 등) 사이클 6 규칙대로 조용히 재입장한다.
          if (code === 'NOT_MEMBER' || code === 'ROOM_NOT_FOUND') {
            if (await roomGone()) { roomClosed(false); throw new AppError('UNKNOWN', 'room closed'); }
            throw new AppError('NOT_MEMBER', e);
          }
          throw e;
        }
      },
      onOpen: (conn) => {
        link = conn;
        announce = true; // 이미 있던 사람들의 화면에 내 현재 상태를 알린다
      },
      onState: onLinkState,
    });
  }

  function onLinkState(state, info) {
    if (!alive) return;
    switch (state) {
      case 'connecting': // 첫 연결(재시도 포함): 들어가는 중 화면 유지
        if (connection !== 'joining') setConnection('joining');
        break;
      case 'connected':
        if (info.first) {
          setConnection('connected');
          canvas.focus({ preventScroll: true });
        } else if (info.after === 'rejoining' && connection === 'connected') {
          loadHistory(true); // 조용한 재입장(NOT_MEMBER): 배너 없이 빠진 메시지만 채운다
        } else {
          reconnected();
        }
        break;
      case 'rejoining': // NOT_MEMBER → 자동 재입장(배너 없음)
        link = null;
        break;
      case 'reconnecting':
        link = null;
        if (connection !== 'disconnected') {
          chatLog.addSystem(M.LOG_DISCONNECTED, 'error');
          setConnection('disconnected');
        }
        // 대기가 길면 바로 시도할 수 있는 버튼 (자동 재시도는 계속된다)
        if (info.delay >= RECONNECT_BUTTON_MIN_MS) setBanner('error', M.DISCONNECTED, M.RECONNECT_NOW, 'reconnect');
        else setBanner('error', M.DISCONNECTED);
        break;
      case 'failed': // 첫 연결 3번 실패
        link = null;
        setConnection('fatal');
        break;
      case 'lost': // 되돌릴 수 없음 (방 없음, 정원, 닉네임, 잠금 방 비밀번호 필요 등)
        link = null;
        if (info.code === 'ROOM_NOT_FOUND') { roomClosed(false); break; } // (사이클 8) 재입장이 방 없음 → 삭제된 방
        setConnection('lost');
        break;
      default:
        break;
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

  function firstJoin() {
    setConnection('joining');
    loadHistory(false); // 캔버스를 막지 않음 (1.1)
    rl = createLink();
    rl.start({ joined: true });
  }

  // --- 업데이트/렌더 ---------------------------------------------------------
  const BODY_OPT = { speed: WORLD.speed, minX: WORLD.minX, maxX: WORLD.maxX, platforms };
  const NO_INPUT = { dir: 0, jump: false, prone: false, superKind: null };

  function update(dt, now) {
    if (me) {
      // 내 캐릭터: 연결 중일 때만 입력을 받는다. 연결이 끊겨도 공중이면 중력으로 착지까지 진행한다.
      let inp = NO_INPUT;
      if (connection === 'connected') {
        const sup = input.takeSuper(now);
        inp = {
          dir: input.direction(), prone: input.proning(), jump: input.wantsJump(now, PHYS.jumpBufferMs),
          superKind: sup ? sup.kind : null, superAge: sup ? sup.age : 0,
        };
      }
      const b = me.body;
      const x0 = b.x;
      const y0 = b.y;
      const r = stepBody(b, inp, dt, BODY_OPT);
      if (r.jumped) input.consumeJump();
      if (r.fx) {
        if (r.fx === 'dash-left') me.dir = -1;
        else if (r.fx === 'dash-right') me.dir = 1;
        playFx(me, r.fx, x0, y0, now);
        pendingFx = r.fx;
        stats.superJumps++;
      }
      if (inp.dir !== 0 && !b.prone && b.dashT <= 0) me.dir = inp.dir;
      me.x = b.x;
      me.y = b.y;
      me.s = b.s;
      me.moving = b.s === 'walk';
      // move 송신: 최대 10회/초. 위치·방향·상태 중 하나라도 바뀌었을 때만(점프 중에는 y가 계속 바뀐다).
      // 정지·착지 후 마지막 상태도 이 규칙으로 1회 나간다. announce = 바뀐 것이 없어도 1회.
      // (사이클 8) fx가 있으면 간격을 기다리지 않고 바로 1회 (어댑터도 급송, 2초에 4회 상한)
      if (link && connection === 'connected' && (pendingFx || now - lastMoveSentAt >= MOVE_INTERVAL_MS)) {
        const rx = Math.round(me.x);
        const ry = Math.round(me.y);
        const dir = me.dir < 0 ? 'left' : 'right';
        const key = `${rx}|${ry}|${dir}|${me.s}`;
        if (key !== sentKey || announce || pendingFx) {
          lastMoveSentAt = now;
          sentKey = key;
          announce = false;
          const payload = { x: rx, y: ry, dir, s: me.s };
          if (pendingFx) { payload.fx = pendingFx; stats.fxSent++; }
          pendingFx = null;
          link.sendMove(payload).catch(() => {});
        }
      } else if (connection !== 'connected') pendingFx = null;
      updateCamera(dt);
    }
    for (const p of players.values()) {
      if (p.isSelf) continue;
      // 원격 보간: 등속(160/초) 추적 + 뒤처진 만큼 가속, 너무 멀면 순간 이동. 대시 직후에는 대시 속도 이상.
      const diff = p.targetX - p.x;
      const dist = Math.abs(diff);
      if (dist > REMOTE_SNAP_DIST) {
        p.x = p.targetX;
      } else if (dist > 0) {
        let v = WORLD.speed * (1 + Math.max(0, dist - 16) / REMOTE_CATCHUP);
        if (now < p.fastUntil) v = Math.max(v, PHYS.dashVX);
        const step = Math.min(dist, v * dt);
        p.x += Math.sign(diff) * step;
        if (step > 0.01) p.lastMovedAt = now;
      }
      p.moving = now - p.lastMovedAt < WALK_HOLD_MS;
      // 세로: 받은 y 기록을 120ms 늦게 재생 (두 기록 사이 직선 보간, 물리 재계산 없음). 모든 기록 값을 정확히 지나간다.
      p.y = sampleY(p.yBuf, now - Y_INTERP_DELAY_MS, p.yTo);
      if (p.bubble && now - p.bubble.at >= BUBBLE.showMs) p.bubble = null;
    }
    if (me && me.bubble && now - me.bubble.at >= BUBBLE.showMs) me.bubble = null;
    for (const p of players.values()) {
      const next = animOf(p);
      if (next !== p.anim) { p.anim = next; p.animSince = now; } // 상태가 바뀌면 첫 프레임부터
    }
    fx.update(dt, (p) => frameOf(p, now));
  }

  function sampleY(buf, t, fallback) {
    if (!buf.length) return fallback;
    if (t <= buf[0].t) return buf[0].y;
    for (let i = 1; i < buf.length; i++) {
      const b = buf[i];
      if (t <= b.t) {
        const a = buf[i - 1];
        return a.y + (b.y - a.y) * ((t - a.t) / Math.max(1, b.t - a.t));
      }
    }
    return buf[buf.length - 1].y;
  }

  /**
   * 세로 카메라: 땅/발판에 서 있으면 그 높이, 떨어지면 따라 내려가고, 위로는 머리가 시야 위 8% 안으로 들어올 때만 따라 올라간다
   * (일반 점프로 화면이 흔들리지 않게). 목표는 camYTarget(지면 근처는 지금 구도, 맵 위 끝 0 밖은 안 보임), 0.12초로 부드럽게.
   */
  function updateCamera(dt) {
    const { viewH } = layout;
    const b = me.body;
    if (b.grounded) camRef = b.y;
    else if (b.y > camRef) camRef = b.y;
    else if (camY !== null && b.y - CAM_HEAD < camY + viewH * 0.08) camRef = Math.min(camRef, b.y - CAM_HEAD + viewH * (0.66 - 0.08));
    const target = camYTarget(camRef, viewH, 0);
    if (camY === null || !Number.isFinite(camY)) camY = target;
    else camY += (target - camY) * (1 - Math.exp(-dt / CAM_SMOOTH_S));
    if (Math.abs(target - camY) < 0.05) camY = target;
  }

  /** 애니메이션 이름: idle | walk | jump | fall | prone (manifest에 없으면 prone → crouch → idle, 그 밖은 idle) */
  function animOf(p) {
    if (p.isSelf) return p.s === 'walk' || p.s === 'jump' || p.s === 'fall' || p.s === 'prone' ? p.s : 'idle';
    if (p.s === 'jump' || p.s === 'fall' || p.s === 'prone') return p.s;
    return p.moving ? 'walk' : 'idle'; // s가 없거나 idle/walk: 실제 움직임으로 (멈췄는데 걷는 모습 방지)
  }

  function frameOf(p, now) {
    return avatarR.frameAt(p.anim, now - p.animSince);
  }

  // 그리기 파이프라인 (복셀 계약, 사이클 5): 메인 캔버스 백킹(CSS x dpr)에 바로, 고품질 스무딩.
  //   맵 레이어 → 발 그림자(아래 면: 발판 또는 지면, 높이에 따라 작고 흐리게) → 잔상·바람 줄기 → 아바타(발 = y)
  //   → 큐브 파티클 → 라벨/말풍선(캐릭터를 따라감, CSS px)
  function render(now) {
    if (!me || !avatarR) return;
    if (connection === 'joining' || connection === 'fatal') { paintLetterbox(); return; }
    const { cssW, viewW, viewH, P, dpr, k } = layout;
    if (camY === null) camY = camYTarget(camRef, viewH, 0);
    const cam = cameraFor(me.x, viewW, viewH, k, camY);
    const { camX } = cam;
    const cy = cam.camY;
    const ctx = canvas.getContext('2d');
    drawMap(ctx, map, camX, cy, k, canvas.width, canvas.height);
    if (debugPlatforms && platforms.length) drawPlatformDebug(ctx, platforms, camX, cy, k);

    const order = [];
    for (const p of players.values()) if (!p.isSelf) order.push(p);
    order.sort((a, b) => a.x - b.x);
    order.push(me); // 내 캐릭터는 마지막
    const visible = [];
    const margin = avatarR.worldW;
    for (const p of order) {
      const sx = p.x - camX;
      if (sx < -margin || sx > viewW + margin) continue;
      visible.push([p, sx, Math.round((p.y - cy) * k)]); // [플레이어, 시야 x(월드), 발 y(장치 px)]
    }
    for (const [p, sx] of visible) {
      const sy = surfaceBelow(platforms, p.x, p.y);
      drawFootShadow(ctx, sx * k, Math.round((sy - cy) * k), k, sy - p.y);
    }
    fx.drawBack(ctx, camX, cy, k, (c, p, xD, yD, frame, left, alpha) => {
      c.globalAlpha = alpha;
      avatarR.draw(c, p.avatar, xD, yD, k, frame, left);
      c.globalAlpha = 1;
    });
    smooth(ctx);
    for (const [p, sx, pyD] of visible) avatarR.draw(ctx, p.avatar, Math.round(sx * k), pyD, k, frameOf(p, now), p.dir < 0);
    fx.drawFront(ctx, camX, cy, k);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const u = P / 2; // CSS px / 월드
    for (const [p, sx, pyD] of visible) drawLabel(ctx, p.nickname, sx * u, pyD / dpr, p.isSelf, cssW);
    // 말풍선: 먼저 받은 것부터 그려 최신이 위 (style-guide 6.3-6). 꼬리 끝 = 머리(모자) 맨 위 + HEAD.gap
    // (사이클 8) 엎드리면 그 프레임의 알파 bbox 맨 위(낮아진 키)를 쓴다
    const talking = visible.filter(([p]) => p.bubble).sort((a, b) => a[0].bubble.at - b[0].bubble.at);
    for (const [p, sx, pyD] of talking) {
      const top = p.anim === 'prone' ? avatarR.headTopFrame(p.avatar, frameOf(p, now)) : avatarR.headTop(p.avatar);
      drawBubble(ctx, p.bubble.layout, sx * u, pyD / dpr, (top + HEAD.gap) * u, cssW, bubbleAlpha(now - p.bubble.at));
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
      else if (code === 'NOT_MEMBER') rl?.notMember('send');
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
    const ae = document.activeElement;
    // 채팅 입력 중이면 이동 키를 모두 무시하고, 로그 목록에 포커스가 있으면 방향키는 목록 스크롤에 양보한다
    if (isTypingTarget(ae) || chatLog.el.contains(ae)) return;
    if (document.body.classList.contains('has-modal')) return; // 확인 모달이 열려 있으면 게임 입력 없음
    if (e.ctrlKey || e.metaKey || e.altKey) return; // 브라우저 단축키 (Ctrl+S 등)
    const now = performance.now();
    const tapGroup = KEY_TAP[e.code];
    const dir = KEY_DIR[e.code];
    if (dir) {
      e.preventDefault();
      if (!e.repeat && connection === 'connected') { input.press(`key:${e.code}`, dir); input.tap(tapGroup, now); }
      return;
    }
    const act = KEY_ACTION[e.code];
    if (act) {
      // Space는 포커스된 버튼(나가기, 채팅 기록 등)을 누르는 기본 동작에 양보한다 (키보드 접근성)
      if (e.code === 'Space' && ae && ae !== canvas && /^(BUTTON|A|SELECT|SUMMARY)$/.test(ae.tagName)) return;
      e.preventDefault(); // Space·↑·↓ 페이지 스크롤 방지
      if (!e.repeat && connection === 'connected') {
        input.pressAction(`key:${e.code}`, act, now);
        if (tapGroup) input.tap(tapGroup, now);
      }
    }
  });
  on(window, 'keyup', (e) => { input.release(`key:${e.code}`); });
  on(window, 'blur', () => input.clear());
  // 탭 복귀(모바일 백그라운드 포함): 즉시 하트비트 + 채널 상태 점검, 백오프 대기 중이면 바로 시도
  on(document, 'visibilitychange', () => {
    if (document.visibilityState !== 'visible') { input.clear(); return; }
    lastFrame = 0; // 숨김 동안의 큰 dt를 버린다
    rl?.check();
  });
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

  // (사이클 8) 터치 더블탭: 왼쪽/오른쪽 = 대시, 점프 = 높이 뛰기 (키보드와 같은 300ms 판정). 엎드리기 + 점프 = 내려가기.
  const touchButtons = [
    [leftBtn, -1, 'touch:left', 'left'], [rightBtn, 1, 'touch:right', 'right'],
    [crouchBtn, 'prone', 'touch:prone', null], [jumpBtn, 'jump', 'touch:jump', 'up'],
  ];
  for (const [btn, what, id, group] of touchButtons) {
    const release = () => { input.release(id); btn.classList.remove('is-pressed'); };
    on(btn, 'pointerdown', (e) => {
      e.preventDefault();
      if (connection !== 'connected') return;
      const now = performance.now();
      if (typeof what === 'number') input.press(id, what);
      else input.pressAction(id, what, now);
      if (group) input.tap(group, now);
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
      if (rl && rl.state === 'failed') { setConnection('joining'); rl.retry(); }
      else if (!rl) { app.go('room', opts); return; } // 에셋 로드 실패 등: 화면을 다시 연다
    } else if (action === 'reconnect') {
      setBanner('error', M.DISCONNECTED);
      rl?.reconnectNow();
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
    // 채널을 removeChannel로 완전히 정리(진행 중 join/구독 포함)한 뒤 leave_room. 다음 입장은 어댑터가 이 leave를 기다린다.
    const closing = rl ? rl.close() : Promise.resolve();
    const rpc = closing.then(() => app.backend.leaveRoom(roomId)).catch(() => {});
    await Promise.race([rpc, wait(LEAVE_WAIT_MS)]);
    clearRoomSession();
    app.go('lobby');
  }
  on(leaveBtn, 'click', () => goLobby());

  // --- 방 삭제 (사이클 8): 방장만. 확인 모달 → delete_room → room_closed(본인 포함) → 로비 + 배너 -------------
  let delModal = null;
  function openDeleteModal() {
    if (!isOwner || delModal || closingRoom || leaving) return;
    input.clear();
    const titleId = `del-title-${roomId}`;
    const descId = `del-desc-${roomId}`;
    const err = h('div', { class: 'bk-banner bk-banner--error', role: 'alert', testid: 'modal-banner', hidden: true });
    const cancelBtn = h('button', { class: 'bk-btn', type: 'button', testid: 'modal-cancel' }, '취소');
    const okDots = h('span', { class: 'bk-dots', 'aria-hidden': 'true', hidden: true }, h('i'), h('i'), h('i'));
    const okText = h('span', {}, LM.DELETE_CONFIRM);
    const okBtn = h('button', { class: 'bk-btn bk-btn--danger', type: 'button', testid: 'delete-confirm' }, okDots, okText);
    let busy = false;
    const close = (restore = true) => {
      if (!delModal) return;
      const m = delModal;
      delModal = null;
      m.close({ restoreFocus: restore });
    };
    const api = openModal({
      main: col, titleId, descId, testid: 'modal-delete-room',
      children: [
        h('div', { class: 'bk-modal__head' }, h('h2', { id: titleId }, LM.DELETE_TITLE)),
        h('p', { class: 'bk-modal__room' }, h('b', { testid: 'modal-room-name' }, roomName)),
        h('p', { class: 'bk-modal__desc', id: descId }, LM.DELETE_DESC),
        err,
        h('div', { class: 'bk-modal__foot' }, cancelBtn, okBtn),
      ],
      initialFocus: () => cancelBtn,
      returnTo: deleteBtn,
      fallbackFocus: () => canvas,
      onCancel: () => close(),
      canEscape: () => !busy,
    });
    delModal = api;
    on(cancelBtn, 'click', () => { if (!busy) close(); });
    on(okBtn, 'click', async () => {
      if (busy) return;
      busy = true;
      err.hidden = true;
      okBtn.disabled = true;
      cancelBtn.disabled = true;
      okDots.hidden = false;
      setText(okText, LM.DELETING);
      deletingSelf = true;
      try {
        await app.backend.deleteRoom(roomId);
        if (alive) roomClosed(true); // room_closed broadcast가 먼저 와도 같은 처리(한 번만)
      } catch (e) {
        const code = toAppError(e).code;
        if (!alive || closingRoom) return;
        if (code === 'ROOM_NOT_FOUND') { roomClosed(true); return; } // 이미 없음
        deletingSelf = false;
        busy = false;
        okBtn.disabled = false;
        cancelBtn.disabled = false;
        okDots.hidden = true;
        setText(okText, LM.DELETE_CONFIRM);
        setText(err, code === 'NOT_OWNER' ? LM.DELETE_NOT_OWNER : LM.DELETE_FAILED);
        err.hidden = false;
      }
    });
  }
  if (deleteBtn) on(deleteBtn, 'click', () => openDeleteModal());

  /** 방 삭제됨 (room_closed 수신, 내 삭제 성공, 또는 하트비트/재입장이 방 없음): 채널 정리 → 로비 + 배너. 자동 재입장 없음. */
  async function roomClosed(byMe) {
    if (closingRoom || !alive) return;
    closingRoom = true;
    input.clear();
    if (delModal) { const m = delModal; delModal = null; m.close({ restoreFocus: false }); }
    clearRoomSession();
    const closing = rl ? rl.close() : Promise.resolve();
    await Promise.race([closing.catch(() => {}), wait(CLEANUP_WAIT_MS)]);
    app.go('lobby', { banner: byMe ? 'ROOM_DELETED' : 'ROOM_CLOSED' });
  }

  /** 방이 목록에 없는지 (list_rooms). 확인 실패는 false(있다고 보고 기존 재입장 규칙에 맡긴다). */
  async function roomGone() {
    try {
      const list = await app.backend.listRooms();
      return Array.isArray(list) && !list.some((r) => r && r.id === roomId);
    } catch {
      return false;
    }
  }

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
    user_id: p.user_id, nickname: p.nickname, avatar: { ...p.avatar }, x: Math.round(p.x * 10) / 10, y: Math.round(p.y * 10) / 10,
    dir: p.dir < 0 ? 'left' : 'right', lastChat: p.lastChat, bubble: p.bubble ? p.bubble.text : null, anim: p.anim,
    frame: avatarR ? frameOf(p, performance.now()) : null,
    s: p.s, // 나: 물리 상태, 원격: 마지막으로 받은 s (없으면 null, 옛 crouch는 prone)
    ...(p.isSelf && p.body ? {
      grounded: p.body.grounded, on: p.body.on ? p.body.on.id : null, airCharge: p.body.airCharge,
      cool: Math.round(p.body.cool * 1000) / 1000, dashing: p.body.dashT > 0,
    } : {}),
  });
  const netSnap = () => {
    const a = app.backend && app.backend.stats ? app.backend.stats : null;
    return {
      adapter: a ? { ...a } : null, // track, moveSent, subscribe, removeChannel, joinRoom, leaveRoom, drops
      link: rl ? { state: rl.state, gen: rl.gen, ...rl.stats, events: rl.events.slice(-30) } : null,
    };
  };
  app.providers.room = () => ({
    room: { id: roomId, name: roomName, locked, members: players.size, nickname: myNick, owner: isOwner },
    world: { platforms: platforms.map((p) => ({ ...p })), camY: camY === null ? null : Math.round(camY * 10) / 10 },
    fx: { ...fx.counts, ...stats },
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
    net: netSnap(),
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
    earlyMoves.clear();
    input.clear();
    if (app.providers.room) app.providers.room = null;
    avatarR?.clear();
    fx.clear();
    if (delModal) { const m = delModal; delModal = null; m.close({ restoreFocus: false }); }
    chatLog.destroy();
    link = null;
    // 채널 removeChannel까지 기다리되 화면 전환을 오래 막지 않는다. 그 뒤의 순서는 어댑터가 보장한다(chanIdle, leaveInFlight).
    const closing = rl ? rl.close().catch(() => {}) : Promise.resolve();
    cleaned = Promise.race([closing, new Promise((r) => setTimeout(r, CLEANUP_WAIT_MS))]);
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
    platforms = map && Array.isArray(map.platforms) ? map.platforms : Object.freeze([]);
    BODY_OPT.platforms = platforms;
    avatarR = createAvatarRenderer(assets);
    const startX = clampX(300 + Math.floor(Math.random() * 600));
    me = makePlayer(app.userId || 'me', myNick, assets.sanitizeAvatar(profile.avatar), startX, true);
    await avatarR.ready(me.avatar); // 내 조합의 레이어만 받고 합성 (다른 사람 조합은 그릴 때 지연 로드)
    if (!alive) return;
    players.set(me.user_id, me);
    updateCount();
    raf = requestAnimationFrame(frame);
    firstJoin();
  })();

  return {
    unmount() {
      return cleanup();
    },
  };
}
