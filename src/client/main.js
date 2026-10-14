// 앱 진입점: 어댑터 선택, 세션 복구, 화면 전환, 테스트 훅(window.__mushroom).
import { createBackend, selectedMode } from './backend/index.js';
import { loadAvatarAssets, loadMapAssets, loadUiAssets } from './assets.js';
import { createBackgroundMap } from './bgmap.js';
import { h, setText } from './dom.js';
import { BOOT_TIMEOUT_MS } from './constants.js';
import { AppError, LOGIN_MESSAGES } from './errors.js';
import * as loginScreen from './screens/login.js';
import * as createScreen from './screens/create.js';
import * as gameScreen from './screens/game.js';

const SCREENS = { login: loginScreen, create: createScreen, game: gameScreen };

const root = document.getElementById('app');
const mode = selectedMode();

// LOCAL MODE 칩 (style-guide 7.9): position: fixed 금지. 각 화면이 자기 슬롯에 넣는다 (app.placeModeBadge).
// supabase 모드에서는 표시하지 않는다.
const modeBadge = h('span', { class: 'mode-chip', testid: 'mode-badge', 'aria-label': '실행 모드' }, mode === 'local' ? 'LOCAL MODE' : 'SUPABASE MODE');
if (mode !== 'local') modeBadge.hidden = true;

const toast = h('div', { class: 'global-toast err-banner', role: 'alert', testid: 'global-error', hidden: true });
document.body.appendChild(toast);
let toastTimer = 0;
function showToast(text) {
  setText(toast, text);
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

const app = {
  mode,
  backend: null,
  assets: null, // Promise: 아바타 (loadAvatarAssets)
  mapAssets: null, // Promise: 맵 레이어 (loadMapAssets)
  uiAssets: null, // Promise: UI 스킨 (loadUiAssets) — Canvas 라벨/말풍선용
  modeBadge,
  /** 화면이 LOCAL MODE 칩을 넣을 자리를 지정한다 (local 모드만 보임). */
  placeModeBadge(slot) {
    if (slot && modeBadge.parentNode !== slot) slot.appendChild(modeBadge);
  },
  screen: 'boot',
  session: null,
  character: null,
  /** game 화면이 등록하는 상태 공급자 (테스트 훅용) */
  gameStateProvider: null,
  go: null,
  /** 로그인/가입 직후: 캐릭터 유무로 분기. 실패하면 AppError를 던진다. */
  async routeAfterAuth(session) {
    app.session = session;
    const ch = await app.backend.getMyCharacter();
    app.character = ch;
    return app.go(ch ? 'game' : 'create');
  },
  /** 세션이 무효가 되었을 때(42501 등) 로그인 화면으로 */
  async forceLogout(bannerCode) {
    try { await app.backend.signOut(); } catch { /* 무시 */ }
    app.session = null;
    app.character = null;
    return app.go('login', { banner: bannerCode });
  },
};

let current = null; // { name, el, unmount }
let navChain = Promise.resolve();

app.go = function go(name, opts = {}) {
  navChain = navChain.then(async () => {
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
    const inst = await SCREENS[name].mount(el, app, opts);
    current = { name, el, unmount: inst && inst.unmount };
  }).catch(() => {
    showToast(LOGIN_MESSAGES.SERVER);
  });
  return navChain;
};

// 로그인/생성 화면 공통 배경. 두 화면 사이에서는 유지하고(카메라 위치 이어짐), 게임에 들어가면 제거한다.
let bg = null;
function syncBackground(name) {
  const want = name === 'login' || name === 'create';
  if (want && !bg && app.mapAssets) bg = createBackgroundMap(app.mapAssets);
  else if (!want && bg) { bg.destroy(); bg = null; }
}

function renderBoot() {
  const el = h('div', { class: 'screen screen-boot', 'data-screen': 'boot' },
    h('div', { class: 'px-panel boot-panel', role: 'status', 'aria-label': '불러오는 중' },
      h('span', { class: 'dots', 'aria-hidden': 'true' }, h('i'), h('i'), h('i'))));
  root.appendChild(el);
  current = { name: 'boot', el, unmount: null };
  document.body.dataset.screen = 'boot';
}

function withTimeout(promise, ms) {
  let t;
  return Promise.race([
    promise.finally(() => clearTimeout(t)),
    new Promise((_, reject) => { t = setTimeout(() => reject(new AppError('NETWORK', 'timeout')), ms); }),
  ]);
}

async function boot() {
  renderBoot();
  app.assets = loadAvatarAssets();
  app.assets.catch(() => {});
  app.mapAssets = loadMapAssets();
  app.mapAssets.catch(() => {});
  app.uiAssets = loadUiAssets();
  app.uiAssets.catch(() => {});
  // 스킨이 없는 화면이 잠깐 보이지 않도록 UI 스킨을 조금 기다린다 (최대 1.5초, 실패해도 진행)
  const uiWait = Promise.race([app.uiAssets.catch(() => null), new Promise((r) => setTimeout(r, 1500))]);

  try {
    app.backend = await createBackend();
  } catch {
    await uiWait;
    app.go('login', { banner: 'SERVER' });
    return;
  }
  let target;
  try {
    target = await withTimeout((async () => {
      const session = await app.backend.getSession();
      if (!session) return { name: 'login' };
      app.session = session;
      try {
        const ch = await app.backend.getMyCharacter();
        app.character = ch;
        return { name: ch ? 'game' : 'create' };
      } catch (e) {
        if (e && e.code === 'AUTH_REQUIRED') {
          try { await app.backend.signOut(); } catch { /* 무시 */ }
          app.session = null;
          return { name: 'login' };
        }
        throw e;
      }
    })(), BOOT_TIMEOUT_MS);
  } catch (e) {
    target = { name: 'login', opts: { banner: e && e.code === 'NETWORK' ? 'NETWORK' : 'SERVER' } };
  }
  await uiWait;
  app.go(target.name, target.opts);
}

// ---------------------------------------------------------------------------
// 처리되지 않은 비동기 오류는 콘솔 대신 사용자 문구로 알린다.
window.addEventListener('unhandledrejection', (e) => {
  e.preventDefault();
  showToast(LOGIN_MESSAGES.SERVER);
});

// ---------------------------------------------------------------------------
// QA 테스트 훅 (읽기 전용)
function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const v of Object.values(o)) deepFreeze(v);
  }
  return o;
}

function getState() {
  const g = app.gameStateProvider ? app.gameStateProvider() : null;
  const ch = app.character;
  const snapshot = {
    screen: app.screen,
    mode: app.mode,
    connection: g ? g.connection : null,
    assets: g ? g.assets : null,
    me: g ? g.me : ch ? { user_id: ch.user_id, nickname: ch.nickname, avatar: { ...ch.avatar }, x: null, y: null, lastChat: null } : null,
    players: g ? g.players : [],
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
