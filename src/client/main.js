// 앱 진입점: 어댑터 선택, 익명 로그인(init), 화면 전환(profile → lobby → room), 테스트 훅(window.__mushroom).
// 화면 흐름 정본: ARCHITECTURE "화면 흐름 (사이클 4)".
import { createBackend, selectedMode } from './backend/index.js';
import { localIdentity } from './backend/identity.js';
import { loadAvatarAssets, loadMapAssets } from './assets.js';
import { h, setText } from './dom.js';
import { BOOT_TIMEOUT_MS } from './constants.js';
import { AppError, GLOBAL_MESSAGE, toAppError } from './errors.js';
import { profileKey, readProfile, readRoomSession, clearRoomSession } from './store.js';
import { closeAnyModal } from './ui/modal.js';
import * as profileScreen from './screens/profile.js';
import * as lobbyScreen from './screens/lobby.js';
import * as roomScreen from './screens/room.js';

const SCREENS = { profile: profileScreen, lobby: lobbyScreen, room: roomScreen };

const root = document.getElementById('app');
const mode = selectedMode();

// LOCAL MODE 칩 (style-guide 5.6 .bk-chip--mode): 각 화면이 자기 슬롯에 넣는다 (app.placeModeBadge).
const modeBadge = h('span', { class: 'bk-chip bk-chip--mode', testid: 'mode-badge', 'aria-label': '실행 모드' }, mode === 'local' ? 'LOCAL MODE' : 'SUPABASE MODE');
if (mode !== 'local') modeBadge.hidden = true;

const toast = h('div', { class: 'global-toast bk-banner bk-banner--error', role: 'alert', testid: 'global-error', hidden: true });
document.body.appendChild(toast);
let toastTimer = 0;
function showToast(text) {
  setText(toast, text);
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

function withTimeout(promise, ms) {
  let t;
  return Promise.race([
    Promise.resolve(promise).finally(() => clearTimeout(t)),
    new Promise((_, reject) => { t = setTimeout(() => reject(new AppError('NETWORK', 'timeout')), ms); }),
  ]);
}

const app = {
  mode,
  backend: null,
  assets: null, // Promise: 아바타 (loadAvatarAssets)
  mapAssets: null, // Promise: 맵 레이어 (loadMapAssets)
  modeBadge,
  /** local 모드 테스트 훅 ?as=<이름> (backend/identity.js). supabase 모드는 null */
  as: mode === 'local' ? localIdentity().as : null,
  profileKey: null, // 아래에서 as에 따라 정함
  /** { nickname, avatar } | null — localStorage `mushroom:profile` */
  profile: null,
  /** 프로필 저장 실패(STORAGE) → 로비 정보 배너 1회 */
  storageFailed: false,
  userId: null,
  screen: 'boot',
  /** 화면이 등록하는 테스트 훅 상태 공급자 */
  providers: { profile: null, lobby: null, room: null },
  placeModeBadge(slot) {
    if (slot && modeBadge.parentNode !== slot) slot.appendChild(modeBadge);
  },
  go: null,
  ensureInit: null,
};
app.profileKey = profileKey(app.as);

// 익명 로그인(init)은 한 번만 진행하고, 실패하면 다음 호출에서 다시 시도한다 (로비 "다시 시도").
let initPromise = null;
app.ensureInit = function ensureInit() {
  if (!initPromise) {
    initPromise = (async () => {
      if (!app.backend) app.backend = await createBackend();
      const r = await withTimeout(app.backend.init(), BOOT_TIMEOUT_MS);
      app.userId = r.userId;
      return r;
    })().catch((e) => {
      initPromise = null;
      throw toAppError(e, 'NETWORK');
    });
  }
  return initPromise;
};

let current = null; // { name, el, unmount }
let navChain = Promise.resolve();

app.go = function go(name, opts = {}) {
  navChain = navChain.then(async () => {
    closeAnyModal();
    if (current) {
      const prev = current;
      current = null;
      try { await prev.unmount?.(); } catch { /* 정리 실패는 무시 */ }
      prev.el.remove();
    }
    modeBadge.remove();
    syncBackground(name);
    const el = h('div', { class: `screen screen-${name}`, 'data-screen': name });
    root.appendChild(el);
    app.screen = name;
    document.body.dataset.screen = name;
    window.scrollTo(0, 0);
    const inst = await SCREENS[name].mount(el, app, opts);
    current = { name, el, unmount: inst && inst.unmount };
  }).catch((e) => {
    console.error(e); // eslint-disable-line no-console
    showToast(GLOBAL_MESSAGE);
  });
  return navChain;
};

// 프로필/로비 공통 배경 .bk-world (style-guide 5.11): CSS만으로 그린다. 두 화면 사이에서는 유지, 방에 들어가면 제거.
const CLOUDS = [[4, 76, false], [24, 36, true], [40, 132, false]]; // [left %, top px, 큰 구름] — 같은 배치 2벌 (200% 묶음)
let bg = null;
function createWorldBackground() {
  const clouds = h('div', { class: 'bk-clouds' });
  for (const off of [0, 50]) {
    for (const [left, top, big] of CLOUDS) {
      clouds.appendChild(h('div', { class: big ? 'bk-cloud bk-cloud--b' : 'bk-cloud', style: { left: `${left + off}%`, top: `${top}px` } }));
    }
  }
  const el = h('div', { class: 'bk-world', 'aria-hidden': 'true', testid: 'world-bg' },
    clouds, h('div', { class: 'bk-world__hills' }), h('div', { class: 'bk-world__ground' }));
  document.body.prepend(el);
  return el;
}
function syncBackground(name) {
  const want = name === 'profile' || name === 'lobby' || name === 'boot';
  if (want && !bg) bg = createWorldBackground();
  else if (!want && bg) { bg.remove(); bg = null; }
}

function renderBoot() {
  syncBackground('boot');
  const el = h('div', { class: 'screen screen-boot', 'data-screen': 'boot' },
    h('main', { class: 'scr-auth' },
      h('div', { class: 'bk-panel boot-panel', role: 'status', 'aria-label': '불러오는 중' },
        h('span', { class: 'bk-dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i')))));
  root.appendChild(el);
  current = { name: 'boot', el, unmount: null };
  document.body.dataset.screen = 'boot';
}

async function boot() {
  renderBoot();
  app.assets = loadAvatarAssets();
  app.assets.catch(() => {});
  app.mapAssets = loadMapAssets();
  app.mapAssets.catch(() => {});
  app.profile = readProfile(app.profileKey);
  // 익명 로그인은 화면과 별개로 바로 시작한다 (프로필 화면은 기다리지 않고, 로비가 기다린다)
  app.ensureInit().catch(() => {});

  if (!app.profile) { app.go('profile', { mode: 'first' }); return; }

  // 새로고침 재입장 (room.md 1.1): 비밀번호 없이 멤버 행으로 확인. 실패하면 로비 + 배너.
  const rs = readRoomSession();
  if (rs) {
    try {
      await app.ensureInit();
      await withTimeout(app.backend.joinRoom({ roomId: rs.roomId, password: null, nickname: rs.nickname }), BOOT_TIMEOUT_MS);
      let info = null;
      try { info = (await withTimeout(app.backend.listRooms(), BOOT_TIMEOUT_MS)).find((r) => r.id === rs.roomId) || null; } catch { /* 이름 없이 진행 */ }
      app.go('room', { roomId: rs.roomId, name: info ? info.name : '', locked: info ? !!info.locked : false, nickname: rs.nickname });
    } catch {
      clearRoomSession();
      app.go('lobby', { banner: 'REJOIN_FAILED' });
    }
    return;
  }
  app.go('lobby');
}

// ---------------------------------------------------------------------------
// 처리되지 않은 비동기 오류는 콘솔 대신 사용자 문구로 알린다.
window.addEventListener('unhandledrejection', (e) => {
  e.preventDefault();
  showToast(GLOBAL_MESSAGE);
});

// ---------------------------------------------------------------------------
// QA 테스트 훅 (읽기 전용). docs/handoff/frontend-20261015-rooms.md "테스트 훅"
function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const v of Object.values(o)) deepFreeze(v);
  }
  return o;
}

function getState() {
  const r = app.providers.room ? app.providers.room() : null;
  const l = app.providers.lobby ? app.providers.lobby() : null;
  const p = app.providers.profile ? app.providers.profile() : null;
  const snapshot = {
    screen: app.screen,
    mode: app.mode,
    userId: app.userId,
    as: app.as,
    profile: app.profile ? { nickname: app.profile.nickname, avatar: { ...app.profile.avatar } } : null,
    // 프로필 화면(꾸미기) 상태: 현재 고른 아바타 7키, 미리보기, 닉네임 상태
    create: p,
    // 로비
    lobby: l ? l.lobby : null,
    rooms: l ? l.rooms : [],
    // 방
    room: r ? r.room : null,
    chatLog: r ? r.chatLog : [],
    log: r ? r.log : null,
    connection: r ? r.connection : null,
    assets: r ? r.assets : null,
    me: r ? r.me : null,
    players: r ? r.players : [],
  };
  return deepFreeze(JSON.parse(JSON.stringify(snapshot)));
}

Object.defineProperty(window, '__mushroom', {
  value: Object.freeze({ getState }),
  writable: false,
  configurable: false,
  enumerable: false,
});

boot();
