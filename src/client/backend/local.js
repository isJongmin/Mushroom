// local 모드 어댑터 — 개발·QA 전용. 실제 서비스에 쓰지 않는다. 외부 네트워크(CDN 포함)에 접근하지 않는다.
//
// 서버(supabase/migrations/20261015000000_rooms.sql)의 RPC 규칙을 같은 의미로 흉내 낸다.
// - 저장: localStorage `mushroom.local.v4.db` 한 키에 { seq, rooms, members, messages, failures, lastChat }.
//   같은 브라우저 프로필의 모든 탭이 공유한다(= 하나의 "서버").
// - 동시 쓰기: navigator.locks.request('mushroom.local.v4.db')로 읽기-수정-쓰기를 탭 사이에서 직렬화한다.
//   Web Locks가 없는 브라우저(Safari 15.4 미만 등)에서는 직렬화하지 않는다 → 두 탭이 같은 순간 쓰면 마지막 쓰기가 이긴다
//   (예: 같은 닉네임 동시 입장이 둘 다 성공할 수 있음). 개발용이라 수용.
// - 비밀번호: PBKDF2-SHA256(무작위 salt 16바이트, 100,000회) 해시만 저장. 평문 저장 안 함.
// - 사용자: backend/identity.js (브라우저 프로필 단위 userId, 테스트 훅 `?as=<이름>`으로 탭별 사용자).
// - 실시간: 방별 BroadcastChannel `mushroom:room:<id>`.
//   Presence: join → 2초마다 heartbeat → 6초 소식 없으면 제거, pagehide 때 leave(= untrack).
//   chat: sendChat이 저장 후 같은 채널로 'chat'을 보낸다(서버 송신 흉내). 보낸 탭도 같은 이벤트를 받고 id로 중복 제거.
//   move: 최대 10회/초.
import { AppError } from '../errors.js';
import { MOVE_INTERVAL_MS, ROOM_CAPACITY } from '../constants.js';
import {
  isValidNickname, cleanRoomName, cleanRoomPassword, cleanChatText, cleanPresenceState, cleanChatMessage, createThrottle,
} from './common.js';
import { localIdentity } from './identity.js';
import { createTrackLimiter, TRACK_GAP_MS } from './room-link.js';
import { cleanMove, isMoveState } from '../game/physics.js';

const DB_KEY = 'mushroom.local.v4.db';
const LOCK_NAME = 'mushroom.local.v4.db';
const BC_PREFIX = 'mushroom:room:';
const PBKDF2_ITER = 100000;
const LATENCY_MS = 60; // 로딩 상태를 눈으로 확인할 수 있게 작은 지연
const PRESENCE_HEARTBEAT_MS = 2000;
const PRESENCE_TIMEOUT_MS = 6000;
const PRUNE_MS = 1000;

// 서버와 같은 시간 상수 (backend handoff 2장)
const ACTIVE_MS = 60 * 1000; // 활성 멤버
const VALID_MS = 10 * 60 * 1000; // 유효 멤버(재접속 비밀번호 생략, 채팅, 채널)
const EXPIRE_MS = 30 * 60 * 1000; // 방 만료
const FAIL_WINDOW_MS = 60 * 1000; // 비밀번호 실패 창
const FAIL_MAX = 5;
const FAIL_KEEP_MS = 10 * 60 * 1000;
const CHAT_GAP_MS = 1000; // 사용자당 모든 방 합산
const MSG_KEEP = 50;
const OWN_MAX = 3;
const LIST_MAX = 100;

const delay = (ms) => new Promise((r) => setTimeout(r, ms));
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

function emptyDb() {
  return { v: 4, seq: 0, rooms: {}, members: {}, messages: {}, failures: [], lastChat: {} };
}

function loadDb() {
  try {
    const raw = localStorage.getItem(DB_KEY);
    if (!raw) return emptyDb();
    const db = JSON.parse(raw);
    if (!db || typeof db !== 'object' || db.v !== 4) return emptyDb();
    const base = emptyDb();
    for (const k of Object.keys(base)) if (!own(db, k) || typeof db[k] !== typeof base[k]) db[k] = base[k];
    if (!Array.isArray(db.failures)) db.failures = [];
    return db;
  } catch {
    return emptyDb();
  }
}

function saveDb(db) {
  try {
    localStorage.setItem(DB_KEY, JSON.stringify(db));
  } catch (e) {
    throw new AppError('UNKNOWN', e); // 저장 공간 가득 참 등
  }
}

/** 읽기-수정-쓰기 트랜잭션. fn이 던지면 쓰지 않는다(롤백). */
async function tx(fn, { write = true } = {}) {
  const run = async () => {
    const db = loadDb();
    const out = await fn(db, Date.now());
    if (write) saveDb(db);
    return out;
  };
  if (typeof navigator !== 'undefined' && navigator.locks && typeof navigator.locks.request === 'function') {
    return navigator.locks.request(LOCK_NAME, run);
  }
  return run(); // 한계: 직렬화 없음 (파일 머리 주석)
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
  if (!globalThis.crypto || !crypto.subtle) throw new AppError('UNKNOWN', 'Web Crypto 사용 불가(보안 컨텍스트 필요)');
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: saltBytes, iterations: PBKDF2_ITER }, key, 256);
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

// --- 규칙 헬퍼 (서버 app_private.* 와 같은 의미) ---------------------------------
function roomMembers(db, roomId) {
  if (!own(db.members, roomId) || typeof db.members[roomId] !== 'object') db.members[roomId] = {};
  return db.members[roomId];
}
function roomAlive(db, room, now) {
  if (now - room.last_active_at <= EXPIRE_MS) return true;
  return Object.values(roomMembers(db, room.id)).some((m) => now - m.last_seen_at <= EXPIRE_MS);
}
function deleteRoom(db, roomId) {
  delete db.rooms[roomId];
  delete db.members[roomId];
  delete db.messages[roomId];
  db.failures = db.failures.filter((f) => f.room_id !== roomId);
}
function isValidMember(db, roomId, uid, now) {
  const m = roomMembers(db, roomId)[uid];
  return !!m && now - m.last_seen_at < VALID_MS;
}
function activeOthers(db, roomId, uid, now) {
  return Object.entries(roomMembers(db, roomId)).filter(([id, m]) => id !== uid && now - m.last_seen_at < ACTIVE_MS);
}
function postToRoom(roomId, msg) {
  try {
    const bc = new BroadcastChannel(BC_PREFIX + roomId);
    bc.postMessage(msg); // 닫기 전에 보낸 메시지는 전달된다
    bc.close();
  } catch { /* BroadcastChannel 없음: 실시간 없이 저장만 */ }
}

// ---------------------------------------------------------------------------
// 실시간 연결 (방 하나) — supabase.js connect()와 같은 의미:
//   track(= Presence 상태 올리기)은 입장 1회 + updateSelf(닉네임/아바타 변경)만, 최소 2초 간격(stats.track로 계측).
//   presence-heartbeat(2초)는 BroadcastChannel에 서버가 없어서 쓰는 생존 신호이고 Supabase track에 해당하지 않는다
//   (내용은 마지막으로 track한 상태 그대로, 위치 갱신 아님).
//   위치는 move로만. 다른 탭의 presence-join을 받으면 onPeerJoin(화면이 자기 현재 상태를 move로 1회 보냄).
//   QA 훅: 같은 방 채널로 { type: 'debug-drop', user_id, fail } 를 보내면 그 사용자의 연결이 서버에 끊긴 것처럼
//   닫히고 onDrop('CHANNEL_ERROR')가 불린다. fail = 다음 구독 시도 n번을 NETWORK로 실패시킨다(백오프 확인용).
function createConnection(roomId, uid, handlers, self, backend, onClose) {
  const myState = { ...self, user_id: uid };
  const members = new Map(); // user_id -> { state, lastSeen }
  const seenChat = new Set();
  let closed = false;
  const bc = new BroadcastChannel(BC_PREFIX + roomId);
  const stats = backend.stats;

  const post = (msg) => {
    if (closed) return;
    try { bc.postMessage(msg); } catch { /* 닫힌 채널 */ }
  };
  const call = (name, ...args) => {
    if (closed) return;
    try { handlers[name]?.(...args); } catch (e) { console.error(e); } // eslint-disable-line no-console
  };
  const list = () => [{ ...myState }, ...[...members.values()].map((m) => ({ ...m.state }))];
  const emitSync = () => call('onSync', list());

  /** @returns 'new' | 'changed' | 'same' (위치는 비교하지 않는다: Presence는 입장 시점 값) */
  const upsert = (st) => {
    const prev = members.get(st.user_id);
    members.set(st.user_id, { state: st, lastSeen: Date.now() });
    if (!prev) return 'new';
    const p = prev.state;
    return p.nickname !== st.nickname || JSON.stringify(p.avatar) !== JSON.stringify(st.avatar) ? 'changed' : 'same';
  };

  const deliver = (raw) => {
    const m = cleanChatMessage(raw);
    if (!m || seenChat.has(m.id)) return;
    seenChat.add(m.id);
    if (seenChat.size > 500) seenChat.delete(seenChat.values().next().value);
    call('onChat', m);
  };

  bc.onmessage = (ev) => {
    const msg = ev.data;
    if (closed || !msg || typeof msg !== 'object') return;
    switch (msg.type) {
      case 'presence-join':
      case 'presence-here':
      case 'presence-heartbeat': {
        const st = cleanPresenceState(msg.state);
        if (!st || st.user_id === uid) return;
        const r = upsert(st);
        if (msg.type === 'presence-join') {
          post({ type: 'presence-here', state: { ...myState } });
          call('onPeerJoin', st.user_id);
        }
        // presence-here = 내가 들어오기 전부터 있던 사람(첫 sync에 해당) → 입장 이벤트 없음
        if (r === 'new' && msg.type !== 'presence-here') call('onJoin', { ...st });
        if (r !== 'same') emitSync();
        break;
      }
      case 'presence-leave': {
        const m = typeof msg.user_id === 'string' ? members.get(msg.user_id) : null;
        if (m) {
          members.delete(msg.user_id);
          call('onLeave', { ...m.state });
          emitSync();
        }
        break;
      }
      case 'move': {
        const p = cleanMove(msg.payload);
        if (!p || p.user_id === uid) return;
        call('onMove', p);
        break;
      }
      case 'chat': // 서버(sendChat) 송신 흉내. 아무 탭이나 같은 형식으로 보낼 수 있다는 점은 실제 서버와 같은 한계.
        deliver(msg.payload);
        break;
      case 'debug-drop': // QA 훅: 서버가 이 사용자의 채널을 끊은 상황
        if (msg.user_id === uid) {
          backend.failNext = Math.max(0, Math.min(10, Number(msg.fail) || 0));
          stats.drops++;
          api.close();
          handlers.onDrop?.('CHANNEL_ERROR');
        }
        break;
      default:
        break;
    }
  };

  const presenceTimer = setInterval(() => post({ type: 'presence-heartbeat', state: { ...myState } }), PRESENCE_HEARTBEAT_MS);
  const pruneTimer = setInterval(() => {
    const now = Date.now();
    let removed = false;
    for (const [id, m] of members) {
      if (now - m.lastSeen > PRESENCE_TIMEOUT_MS) {
        members.delete(id);
        call('onLeave', { ...m.state });
        removed = true;
      }
    }
    if (removed) emitSync();
  }, PRUNE_MS);

  // 탭 닫기: leave_room은 보장할 수 없으므로 Presence만 내린다(untrack). 멤버 행은 활성 60초 규칙에 맡긴다.
  const onPageHide = () => post({ type: 'presence-leave', user_id: uid });
  const onPageShow = (e) => { if (e.persisted) post({ type: 'presence-join', state: { ...myState } }); };
  // 숨김 탭은 타이머가 느려진다. 다시 보이면 바로 생존 신호.
  const onVisible = () => { if (document.visibilityState === 'visible') post({ type: 'presence-heartbeat', state: { ...myState } }); };
  window.addEventListener('pagehide', onPageHide);
  window.addEventListener('pageshow', onPageShow);
  document.addEventListener('visibilitychange', onVisible);

  const mover = createThrottle(MOVE_INTERVAL_MS, (p) => { stats.moveSent++; post({ type: 'move', payload: p }); });
  const track = (type) => backend.trackLimiter.run(() => {
    if (closed) return 'closed';
    stats.track++;
    post({ type, state: { ...myState } });
    return 'ok';
  });

  const api = {
    roomId,
    deliver,
    sendMove({ x, y, dir, s }) {
      if (closed) return Promise.reject(new AppError('NETWORK'));
      mover.push({ user_id: uid, x, y, dir: dir === 'left' ? 'left' : 'right', s: isMoveState(s) ? s : 'idle' });
      return Promise.resolve();
    },
    /** 닉네임/아바타가 바뀌었을 때만 (최소 2초 간격) */
    async updateSelf(partial) {
      if (closed) throw new AppError('NETWORK');
      for (const k of ['nickname', 'avatar']) if (partial && own(partial, k)) myState[k] = partial[k];
      await track('presence-heartbeat');
    },
    healthy() {
      return !closed;
    },
    async close() {
      if (closed) return;
      post({ type: 'presence-leave', user_id: uid });
      closed = true;
      stats.removeChannel++;
      mover.cancel();
      clearInterval(presenceTimer);
      clearInterval(pruneTimer);
      window.removeEventListener('pagehide', onPageHide);
      window.removeEventListener('pageshow', onPageShow);
      document.removeEventListener('visibilitychange', onVisible);
      bc.onmessage = null;
      bc.close();
      members.clear();
      onClose(api);
    },
  };
  api.leave = api.close;

  stats.subscribe++;
  // 첫 track = presence-join (입장 1회). BroadcastChannel은 끊기지 않으므로 바로 구독 완료.
  // 첫 sync = 나 혼자(이미 있던 사람은 presence-here로 조용히 추가).
  const ready = track('presence-join').then(() => { emitSync(); return api; });
  return { api, ready };
}

// ---------------------------------------------------------------------------

export function createLocalBackend() {
  const conns = new Set();
  let uid = null;

  const requireUid = () => {
    if (!uid) throw new AppError('NOT_MEMBER'); // 서버: 세션 없음 = NOT_MEMBER
    return uid;
  };

  const backend = {
    mode: 'local',
    // 계측 (getState().net.adapter): supabase.js와 같은 이름
    stats: { track: 0, moveSent: 0, subscribe: 0, removeChannel: 0, joinRoom: 0, leaveRoom: 0, drops: 0 },
    trackLimiter: createTrackLimiter({ minGapMs: TRACK_GAP_MS }),
    failNext: 0,

    async init() {
      uid = localIdentity().userId;
      await delay(LATENCY_MS);
      return { userId: uid };
    },

    async listRooms() {
      requireUid();
      await delay(LATENCY_MS);
      return tx((db, now) => {
        for (const room of Object.values(db.rooms)) if (!roomAlive(db, room, now)) deleteRoom(db, room.id);
        const rows = Object.values(db.rooms).map((r) => {
          const ms = Object.values(roomMembers(db, r.id));
          const members = ms.filter((m) => now - m.last_seen_at < ACTIVE_MS).length;
          const lastAct = Math.max(r.last_active_at, ...ms.map((m) => m.last_seen_at));
          return { r, members, lastAct };
        });
        rows.sort((a, b) => b.members - a.members || b.lastAct - a.lastAct || b.r.created_at - a.r.created_at);
        return rows.slice(0, LIST_MAX).map(({ r, members }) => ({
          id: r.id, name: r.name, locked: !!r.pw_hash, members, createdAt: new Date(r.created_at).toISOString(),
        }));
      });
    },

    async createRoom({ name, password, nickname }) {
      const me = requireUid();
      await delay(LATENCY_MS);
      const cleanName = cleanRoomName(name);
      if (cleanName === null) throw new AppError('ROOM_NAME_FORMAT');
      const pw = cleanRoomPassword(password);
      if (pw === null) throw new AppError('PASSWORD_FORMAT');
      if (!isValidNickname(nickname)) throw new AppError('NICK_FORMAT');
      let salt = null;
      let hash = null;
      if (pw) {
        const saltBytes = crypto.getRandomValues(new Uint8Array(16));
        hash = await hashPassword(pw, saltBytes);
        salt = b64(saltBytes);
      }
      const roomId = await tx((db, now) => {
        const owned = Object.values(db.rooms).filter((r) => r.created_by === me && roomAlive(db, r, now)).length;
        if (owned >= OWN_MAX) throw new AppError('TOO_MANY_ROOMS');
        const id = uuid();
        db.rooms[id] = { id, name: cleanName, pw_salt: salt, pw_hash: hash, created_by: me, created_at: now, last_active_at: now };
        roomMembers(db, id)[me] = { nickname, joined_at: now, last_seen_at: now };
        return id;
      });
      return { roomId };
    },

    async joinRoom({ roomId, password, nickname }) {
      const me = requireUid();
      backend.stats.joinRoom++;
      await delay(LATENCY_MS);
      if (!isValidNickname(nickname)) throw new AppError('NICK_FORMAT');
      if (typeof roomId !== 'string') throw new AppError('ROOM_NOT_FOUND');
      // 해시 계산(수십 ms)은 잠금 밖에서. 방 비밀번호는 바뀌지 않으므로 salt를 미리 읽어도 된다.
      const pre = loadDb().rooms[roomId];
      let tryHash = null;
      if (pre && pre.pw_hash && typeof password === 'string' && password !== '') {
        tryHash = await hashPassword(password, unb64(pre.pw_salt));
      }
      const result = await tx((db, now) => {
        const room = own(db.rooms, roomId) ? db.rooms[roomId] : null;
        if (!room || !roomAlive(db, room, now)) throw new AppError('ROOM_NOT_FOUND');
        const ms = roomMembers(db, roomId);
        for (const [id, m] of Object.entries(ms)) if (now - m.last_seen_at >= VALID_MS) delete ms[id];
        db.failures = db.failures.filter((f) => now - f.at < FAIL_KEEP_MS);
        const isMember = own(ms, me);
        if (room.pw_hash && !isMember) {
          const fails = db.failures.filter((f) => f.user_id === me && f.room_id === roomId && now - f.at < FAIL_WINDOW_MS).length;
          if (fails >= FAIL_MAX) throw new AppError('RATE_LIMITED');
          if (password == null || password === '') return 'WRONG_PASSWORD'; // 세지 않음 (새로고침 재입장 보호)
          if (!tryHash || !safeEqual(tryHash, room.pw_hash)) {
            db.failures.push({ room_id: roomId, user_id: me, at: now }); // 실패 기록은 커밋한다
            return 'WRONG_PASSWORD';
          }
        }
        if (activeOthers(db, roomId, me, now).length >= ROOM_CAPACITY) throw new AppError('ROOM_FULL');
        const lower = nickname.toLowerCase();
        if (activeOthers(db, roomId, me, now).some(([, m]) => m.nickname.toLowerCase() === lower)) throw new AppError('NICK_TAKEN');
        // 비활성(60초 초과) 멤버의 같은 닉네임은 양보 (그 사람은 heartbeat에서 NOT_MEMBER)
        for (const [id, m] of Object.entries(ms)) if (id !== me && m.nickname.toLowerCase() === lower) delete ms[id];
        ms[me] = { nickname, joined_at: isMember ? ms[me].joined_at : now, last_seen_at: now };
        room.last_active_at = now;
        return 'OK';
      });
      if (result === 'WRONG_PASSWORD') throw new AppError('WRONG_PASSWORD');
    },

    async leaveRoom(roomId) {
      const me = requireUid();
      backend.stats.leaveRoom++;
      await tx((db, now) => {
        const ms = db.members[roomId];
        if (ms && own(ms, me)) {
          delete ms[me];
          if (db.rooms[roomId]) db.rooms[roomId].last_active_at = now;
        }
      });
    },

    async heartbeat(roomId) {
      const me = requireUid();
      await tx((db, now) => {
        if (!own(db.rooms, roomId) || !isValidMember(db, roomId, me, now)) throw new AppError('NOT_MEMBER');
        const m = roomMembers(db, roomId)[me];
        // 60초 넘게 비활성이었다가 돌아왔는데 그 사이 방이 찼으면 부활 금지
        if (now - m.last_seen_at >= ACTIVE_MS && activeOthers(db, roomId, me, now).length >= ROOM_CAPACITY) {
          throw new AppError('NOT_MEMBER');
        }
        m.last_seen_at = now;
      });
    },

    async recentMessages(roomId) {
      const me = requireUid();
      await delay(LATENCY_MS);
      return tx((db, now) => {
        if (!own(db.rooms, roomId) || !isValidMember(db, roomId, me, now)) throw new AppError('NOT_MEMBER');
        const list = Array.isArray(db.messages[roomId]) ? db.messages[roomId] : [];
        return list.slice(-MSG_KEEP).map((m) => ({ ...m }));
      }, { write: false });
    },

    async sendChat(roomId, text) {
      const me = requireUid();
      const msg = await tx((db, now) => {
        if (!own(db.rooms, roomId) || !isValidMember(db, roomId, me, now)) throw new AppError('NOT_MEMBER');
        const t = cleanChatText(text);
        if (t === null) throw new AppError('TEXT_FORMAT');
        const last = Number(db.lastChat[me]) || 0;
        if (now - last < CHAT_GAP_MS) throw new AppError('RATE_LIMITED'); // 모든 방 합산
        db.lastChat[me] = now;
        db.seq = (Number(db.seq) || 0) + 1;
        const m = { id: db.seq, user_id: me, nickname: roomMembers(db, roomId)[me].nickname, text: t, created_at: new Date(now).toISOString() };
        const list = Array.isArray(db.messages[roomId]) ? db.messages[roomId] : [];
        list.push(m);
        db.messages[roomId] = list.slice(-MSG_KEEP);
        return m;
      });
      postToRoom(roomId, { type: 'chat', payload: msg }); // 서버 송신 흉내 (보낸 탭의 연결도 받는다)
      for (const c of conns) if (c.roomId === roomId) c.deliver(msg); // 반환값도 같은 경로 (id 중복 제거)
      return { ...msg };
    },

    /**
     * 채널 1회 구독 (supabase.js connectRoom과 같은 계약). 재시도·하트비트·재입장은 room-link.js가 한다.
     * @param handlers { onSync(list), onJoin(state), onLeave(state), onPeerJoin(user_id), onMove(payload), onChat(msg), onDrop(status) }
     * @param self { nickname, avatar, x, y } Presence에 올릴 내 상태 (user_id는 어댑터가 채운다)
     * @param opts.signal AbortSignal
     */
    async connectRoom(roomId, handlers, self, opts = {}) {
      const me = requireUid();
      const signal = opts.signal;
      if (typeof BroadcastChannel === 'undefined') throw new AppError('NETWORK', 'BroadcastChannel 미지원');
      if (signal && signal.aborted) throw new AppError('NETWORK', 'aborted');
      if (backend.failNext > 0) { // QA 훅 debug-drop의 fail
        backend.failNext--;
        await delay(LATENCY_MS);
        throw new AppError('NETWORK', 'debug fail');
      }
      // 서버: 비공개 채널은 유효 멤버만 구독 가능 (아니면 CHANNEL_ERROR)
      const ok = await tx((db, now) => own(db.rooms, roomId) && isValidMember(db, roomId, me, now), { write: false });
      if (!ok) throw new AppError('NOT_MEMBER');
      if (signal && signal.aborted) throw new AppError('NETWORK', 'aborted');
      const { api: conn, ready } = createConnection(roomId, me, handlers, self, backend, (c) => conns.delete(c));
      conns.add(conn);
      await ready;
      if (signal && signal.aborted) { await conn.close(); throw new AppError('NETWORK', 'aborted'); }
      return { sendMove: conn.sendMove, updateSelf: conn.updateSelf, healthy: conn.healthy, close: conn.close, leave: conn.close };
    },
  };
  return backend;
}
