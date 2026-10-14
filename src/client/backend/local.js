// local 모드 어댑터 — 개발·QA 전용. 실제 서비스에 쓰지 않는다.
//
// - 계정/캐릭터: localStorage (같은 브라우저 프로필의 모든 탭이 공유)
//   비밀번호는 평문으로 저장하지 않는다. Web Crypto PBKDF2-SHA256(무작위 salt, 100,000회)로 해시만 저장한다.
//   그래도 브라우저 저장소는 보안 저장소가 아니다. 개발용이다.
// - 세션: sessionStorage (탭마다 따로, 새로고침해도 유지). 한 브라우저에서 탭마다 다른 계정으로 테스트할 수 있다.
// - 실시간: BroadcastChannel('mushroom:map:village')로 같은 브라우저의 탭끼리 Presence/move/chat을 흉내 낸다.
//   Presence: join → 2초마다 heartbeat → 6초 동안 소식이 없으면 제거. 탭 종료(pagehide) 시 leave 송신.
import { AppError } from '../errors.js';
import { NICK_RE, CHAT_MAX } from '../constants.js';
import { assertCredentials, isValidAvatarShape, isValidNickname, pickAvatar } from './common.js';

const LS_ACCOUNTS = 'mushroom.local.accounts.v1';
const LS_CHARACTERS = 'mushroom.local.characters.v1';
const SS_SESSION = 'mushroom.local.session.v1';
const BC_NAME = 'mushroom:map:village';
const PBKDF2_ITER = 100000;
const LATENCY_MS = 80; // 스피너 등 비동기 상태를 눈으로 확인할 수 있게 작은 지연을 둔다
const HEARTBEAT_MS = 2000;
const PRESENCE_TIMEOUT_MS = 6000;
const PRUNE_MS = 1000;

const delay = (ms) => new Promise((r) => setTimeout(r, ms));

function readJSON(storage, key, fallback) {
  try {
    const raw = storage.getItem(key);
    if (!raw) return fallback;
    const v = JSON.parse(raw);
    return v && typeof v === 'object' ? v : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(storage, key, value) {
  try {
    storage.setItem(key, JSON.stringify(value));
  } catch (e) {
    throw new AppError('SERVER', e);
  }
}

function b64(bytes) {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function unb64(str) {
  const s = atob(str);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

async function hashPassword(password, saltBytes) {
  if (!globalThis.crypto || !crypto.subtle) throw new AppError('SERVER', 'Web Crypto 사용 불가(보안 컨텍스트 필요)');
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt: saltBytes, iterations: PBKDF2_ITER },
    key,
    256,
  );
  return b64(new Uint8Array(bits));
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hx = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${hx.slice(0, 8)}-${hx.slice(8, 12)}-${hx.slice(12, 16)}-${hx.slice(16, 20)}-${hx.slice(20)}`;
}

function currentSession() {
  const s = readJSON(sessionStorage, SS_SESSION, null);
  if (!s || typeof s.user_id !== 'string' || typeof s.login_id !== 'string') return null;
  const acc = readJSON(localStorage, LS_ACCOUNTS, {})[s.login_id];
  if (!acc || acc.user_id !== s.user_id) return null; // 계정이 지워졌으면 세션 무효
  return { user_id: s.user_id, login_id: s.login_id };
}

function requireSession() {
  const s = currentSession();
  if (!s) throw new AppError('AUTH_REQUIRED');
  return s;
}

function setSession(account, loginId) {
  writeJSON(sessionStorage, SS_SESSION, { user_id: account.user_id, login_id: loginId });
  return { user_id: account.user_id, login_id: loginId };
}

// ---------------------------------------------------------------------------
// 실시간 (BroadcastChannel)

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

function cleanPresenceState(s) {
  if (!s || typeof s !== 'object') return null;
  if (typeof s.user_id !== 'string' || s.user_id.length > 64) return null;
  if (!isNum(s.x) || !isNum(s.y)) return null;
  return {
    user_id: s.user_id,
    nickname: typeof s.nickname === 'string' ? s.nickname.slice(0, 32) : '',
    avatar: s.avatar && typeof s.avatar === 'object' ? s.avatar : null,
    x: s.x,
    y: s.y,
  };
}

let activeMap = null;

function joinMapLocal(handlers, self) {
  const myState = { ...self };
  const members = new Map(); // user_id -> { state, lastSeen }
  let closed = false;
  const bc = new BroadcastChannel(BC_NAME);

  const emitPresence = () => {
    if (closed) return;
    const list = [{ ...myState }];
    for (const m of members.values()) list.push({ ...m.state });
    handlers.onPresence?.(list);
  };

  const post = (msg) => {
    if (closed) return;
    try {
      bc.postMessage(msg);
    } catch {
      /* 닫힌 채널 등: 무시 */
    }
  };

  const upsertMember = (state) => {
    const prev = members.get(state.user_id);
    members.set(state.user_id, { state, lastSeen: Date.now() });
    return !prev || prev.state.nickname !== state.nickname || JSON.stringify(prev.state.avatar) !== JSON.stringify(state.avatar);
  };

  bc.onmessage = (ev) => {
    const msg = ev.data;
    if (closed || !msg || typeof msg !== 'object') return;
    switch (msg.type) {
      case 'presence-join':
      case 'presence-heartbeat': {
        const st = cleanPresenceState(msg.state);
        if (!st || st.user_id === myState.user_id) return;
        const changed = upsertMember(st);
        if (msg.type === 'presence-join') {
          // 새로 들어온 사람이 나를 바로 알 수 있게 즉시 heartbeat
          post({ type: 'presence-heartbeat', state: { ...myState } });
          emitPresence();
        } else if (changed) emitPresence();
        break;
      }
      case 'presence-leave': {
        const uid = msg.user_id;
        if (typeof uid === 'string' && members.delete(uid)) emitPresence();
        break;
      }
      case 'broadcast': {
        const p = msg.payload;
        if (!p || typeof p !== 'object') return;
        // Presence에 있는 상대만 heartbeat로 간주하지 않는다(heartbeat은 presence 메시지로만 갱신)
        if (msg.event === 'move') {
          const m = members.get(p.user_id);
          if (m && isNum(p.x) && isNum(p.y)) { m.state.x = p.x; m.state.y = p.y; }
          handlers.onMove?.(p);
        } else if (msg.event === 'chat') {
          handlers.onChat?.(p);
        }
        break;
      }
      default:
        break;
    }
  };

  const heartbeat = setInterval(() => post({ type: 'presence-heartbeat', state: { ...myState } }), HEARTBEAT_MS);
  const prune = setInterval(() => {
    const now = Date.now();
    let removed = false;
    for (const [uid, m] of members) {
      if (now - m.lastSeen > PRESENCE_TIMEOUT_MS) { members.delete(uid); removed = true; }
    }
    if (removed) emitPresence();
  }, PRUNE_MS);

  const onPageHide = () => post({ type: 'presence-leave', user_id: myState.user_id });
  // 숨김 탭은 타이머가 느려진다. 다시 보이면 바로 heartbeat을 보내 상대 목록에서 빠지지 않게 한다.
  const onVisible = () => { if (document.visibilityState === 'visible') post({ type: 'presence-heartbeat', state: { ...myState } }); };
  window.addEventListener('pagehide', onPageHide);
  document.addEventListener('visibilitychange', onVisible);

  const leave = async () => {
    if (closed) return;
    post({ type: 'presence-leave', user_id: myState.user_id });
    closed = true;
    clearInterval(heartbeat);
    clearInterval(prune);
    window.removeEventListener('pagehide', onPageHide);
    document.removeEventListener('visibilitychange', onVisible);
    bc.onmessage = null;
    bc.close();
    members.clear();
    if (activeMap === api) activeMap = null;
  };

  const api = {
    async sendMove({ x, y, dir }) {
      if (closed) throw new AppError('NETWORK');
      myState.x = x;
      myState.y = y;
      post({ type: 'broadcast', event: 'move', payload: { user_id: myState.user_id, x, y, dir } });
    },
    async sendChat(text) {
      if (closed) throw new AppError('NETWORK');
      const t = String(text).slice(0, CHAT_MAX);
      post({ type: 'broadcast', event: 'chat', payload: { user_id: myState.user_id, text: t } });
    },
    leave,
  };

  post({ type: 'presence-join', state: { ...myState } });
  activeMap = api;
  // 연결 상태: BroadcastChannel은 끊기지 않으므로 바로 connected
  queueMicrotask(() => { emitPresence(); handlers.onStatus?.('connected'); });
  return api;
}

// ---------------------------------------------------------------------------

export function createLocalBackend() {
  return {
    mode: 'local',

    async signUp(id, password) {
      assertCredentials(id, password, { signup: true });
      await delay(LATENCY_MS);
      const accounts = readJSON(localStorage, LS_ACCOUNTS, {});
      if (Object.prototype.hasOwnProperty.call(accounts, id)) throw new AppError('ID_TAKEN');
      const salt = crypto.getRandomValues(new Uint8Array(16));
      const hash = await hashPassword(password, salt);
      const account = { user_id: uuid(), salt: b64(salt), hash, iter: PBKDF2_ITER, created_at: new Date().toISOString() };
      accounts[id] = account;
      writeJSON(localStorage, LS_ACCOUNTS, accounts);
      return setSession(account, id);
    },

    async signIn(id, password) {
      assertCredentials(id, password, { signup: false });
      await delay(LATENCY_MS);
      const accounts = readJSON(localStorage, LS_ACCOUNTS, {});
      const acc = Object.prototype.hasOwnProperty.call(accounts, id) ? accounts[id] : null;
      // 계정이 없어도 해시를 계산해 응답 시간 차이를 줄인다
      const salt = acc ? unb64(acc.salt) : new Uint8Array(16);
      const hash = await hashPassword(password, salt);
      if (!acc || !safeEqual(hash, acc.hash)) throw new AppError('LOGIN_FAILED');
      return setSession(acc, id);
    },

    async signOut() {
      if (activeMap) await activeMap.leave();
      try { sessionStorage.removeItem(SS_SESSION); } catch { /* 무시 */ }
    },

    async getSession() {
      return currentSession();
    },

    async getMyCharacter() {
      const s = requireSession();
      await delay(LATENCY_MS / 2);
      const ch = readJSON(localStorage, LS_CHARACTERS, {})[s.user_id];
      return ch ? { user_id: ch.user_id, nickname: ch.nickname, avatar: { ...ch.avatar } } : null;
    },

    async isNicknameTaken(nickname) {
      requireSession();
      await delay(LATENCY_MS);
      const lower = String(nickname).toLowerCase();
      const chars = readJSON(localStorage, LS_CHARACTERS, {});
      return Object.values(chars).some((c) => c && typeof c.nickname === 'string' && c.nickname.toLowerCase() === lower);
    },

    async createCharacter(nickname, avatar) {
      const s = requireSession();
      await delay(LATENCY_MS);
      if (!isValidNickname(nickname) || !NICK_RE.test(nickname)) throw new AppError('NICK_FORMAT');
      if (!isValidAvatarShape(avatar)) throw new AppError('AVATAR_FORMAT');
      const chars = readJSON(localStorage, LS_CHARACTERS, {});
      if (chars[s.user_id]) throw new AppError('CHAR_EXISTS'); // characters_pkey
      const lower = nickname.toLowerCase();
      if (Object.values(chars).some((c) => c && String(c.nickname).toLowerCase() === lower)) {
        throw new AppError('NICK_TAKEN'); // characters_nickname_lower_key
      }
      const row = { user_id: s.user_id, nickname, avatar: pickAvatar(avatar), created_at: new Date().toISOString() };
      chars[s.user_id] = row;
      writeJSON(localStorage, LS_CHARACTERS, chars);
      return { user_id: row.user_id, nickname: row.nickname, avatar: { ...row.avatar } };
    },

    /**
     * @param handlers { onPresence(list), onMove(payload), onChat(payload), onStatus(status) }
     * @param self { user_id, nickname, avatar, x, y }  Presence에 올릴 내 상태
     * @returns Promise<{ sendMove({x,y,dir}), sendChat(text), leave() }>
     */
    async joinMap(handlers, self) {
      if (typeof BroadcastChannel === 'undefined') throw new AppError('NETWORK', 'BroadcastChannel 미지원');
      const s = requireSession();
      if (activeMap) await activeMap.leave();
      return joinMapLocal(handlers, { ...self, user_id: s.user_id });
    },

    async leaveMap() {
      if (activeMap) await activeMap.leave();
    },
  };
}
