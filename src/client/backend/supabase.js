// supabase 모드 어댑터 (ARCHITECTURE 결정 3~6, supabase/README.md "프런트용 API 명세").
// supabase-js는 ARCHITECTURE가 고정한 CDN URL에서 "처음 필요할 때" 동적 import 한다.
// local 모드에서는 이 파일 자체가 import되지 않는다(backend/index.js).
// anon(publishable) key만 쓴다. service_role 키는 어떤 경우에도 넣지 않는다.
//
// 오류 매핑:
//   RPC 예외: error.message === '<코드>' (SQLSTATE P0001) → 그 코드
//   join_room 반환 'WRONG_PASSWORD' → WRONG_PASSWORD (예외가 아니라 반환값: 실패 기록 커밋 때문)
//   42501 / PGRST301~303 / HTTP 401 (세션 없음·만료) → 세션 복구(refreshSession → 실패하면 signInAnonymously) 후 1회 재시도, 그래도 실패 → UNKNOWN
//   fetch 실패/오프라인/CDN 로드 실패 → NETWORK
//   그 밖 → UNKNOWN
import { AppError, ERROR_CODES } from '../errors.js';
import { SUPABASE_CDN, HEARTBEAT_MS, MOVE_INTERVAL_MS } from '../constants.js';
import { cleanPresenceState, cleanChatMessage, createThrottle } from './common.js';

const KNOWN = new Set(ERROR_CODES);
const TRACK_IDLE_MS = 600; // 정지 후 Presence 좌표 갱신(track) 지연
const SUBSCRIBE_TIMEOUT_MS = 10000;

function isNetworkError(err) {
  if (!err) return false;
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return true;
  if (err.name === 'AuthRetryableFetchError' || err.name === 'TypeError') return true;
  if (err.status === 0) return true;
  const msg = `${err.message || ''} ${err.details || ''}`;
  return /failed to fetch|fetch failed|networkerror|network request failed|load failed|timed? ?out/i.test(msg);
}

// PostgREST: PGRST301(JWT 해석 실패), PGRST302(인증 없음), PGRST303(JWT 클레임/만료). 42501은 권한 없음.
// postgrest-js 2.45는 HTTP 상태를 error가 아니라 응답(res.status)에 둔다 → status를 따로 받는다.
const AUTH_CODES = new Set(['42501', 'PGRST301', 'PGRST302', 'PGRST303']);
function isAuthError(err, status) {
  return !!err && (AUTH_CODES.has(err.code) || status === 401 || err.status === 401);
}

function mapError(err) {
  if (!err) return new AppError('UNKNOWN');
  if (err instanceof AppError) return err;
  if (isNetworkError(err)) return new AppError('NETWORK', err);
  const m = typeof err.message === 'string' ? err.message.trim() : '';
  if (KNOWN.has(m)) return new AppError(m, err);
  return new AppError('UNKNOWN', err);
}

export function createSupabaseBackend(url, anonKey) {
  let clientPromise = null;
  let userId = null;
  let authSub = null;
  const conns = new Set();

  function client() {
    if (!clientPromise) {
      clientPromise = import(SUPABASE_CDN)
        .then((mod) => mod.createClient(url, anonKey, {
          auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
        }))
        .catch((e) => {
          clientPromise = null; // 다음 시도에서 다시 로드
          throw new AppError('NETWORK', e);
        });
    }
    return clientPromise;
  }

  /** 세션 확보: 있으면 복구, 없으면 익명 로그인. */
  async function ensureSession() {
    const sb = await client();
    let session = null;
    try {
      const { data, error } = await sb.auth.getSession();
      if (error) throw error;
      session = data && data.session;
      if (!session) {
        const r = await sb.auth.signInAnonymously();
        if (r.error) throw r.error;
        session = r.data && r.data.session;
      }
    } catch (e) {
      throw mapError(e);
    }
    if (!session || !session.user) throw new AppError('UNKNOWN', 'no session');
    userId = session.user.id;
    if (!authSub) {
      // 토큰 갱신 시 Realtime에도 새 JWT 전달 (비공개 채널 권한은 JWT 갱신 때 다시 검사된다)
      const { data } = sb.auth.onAuthStateChange((event, s) => {
        if ((event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN') && s && s.access_token) {
          try { sb.realtime.setAuth(s.access_token); } catch { /* 무시 */ }
        }
      });
      authSub = data && data.subscription;
    }
    return session;
  }

  /**
   * 서버가 토큰을 거부했을 때: getSession은 로컬 만료 시각만 보므로 같은 토큰을 돌려줄 수 있다.
   * refreshSession으로 강제 갱신하고, 실패하면(사용자 삭제 등) 새 익명 계정으로 로그인한다.
   */
  async function recoverSession() {
    const sb = await client();
    let session = null;
    try {
      const r = await sb.auth.refreshSession();
      session = !r.error && r.data && r.data.session;
      if (!session) {
        const a = await sb.auth.signInAnonymously();
        if (a.error) throw a.error;
        session = a.data && a.data.session;
      }
    } catch (e) {
      throw mapError(e);
    }
    if (!session || !session.user) throw new AppError('UNKNOWN', 'no session');
    userId = session.user.id;
    try { sb.realtime.setAuth(session.access_token); } catch { /* 무시 */ }
    return session;
  }

  async function rpc(name, args, retried = false) {
    const sb = await client();
    let res;
    try {
      res = await sb.rpc(name, args);
    } catch (e) {
      throw mapError(e);
    }
    if (res.error) {
      if (!retried && isAuthError(res.error, res.status)) {
        await recoverSession();
        return rpc(name, args, true);
      }
      throw mapError(res.error);
    }
    return res.data;
  }

  const requireInit = () => {
    if (!userId) throw new AppError('NOT_MEMBER');
  };

  async function connect(roomId, handlers, self) {
    const sb = await client();
    const session = await ensureSession();
    // 비공개 채널: 구독 전에 JWT를 Realtime에 전달 (join_room 성공 후에 호출된다)
    try { sb.realtime.setAuth(session.access_token); } catch { /* 무시 */ }

    const me = userId;
    const myState = { nickname: self.nickname, avatar: self.avatar, x: self.x, y: self.y, user_id: me };
    const seenChat = new Set();
    let closed = false;
    let synced = false;
    let subscribed = false;
    let trackTimer = 0;
    let heartbeatTimer = 0;

    const call = (n, ...a) => {
      if (closed) return;
      try { handlers[n]?.(...a); } catch (e) { console.error(e); } // eslint-disable-line no-console
    };
    const deliver = (raw) => {
      const m = cleanChatMessage(raw);
      if (!m || seenChat.has(m.id)) return;
      seenChat.add(m.id);
      if (seenChat.size > 500) seenChat.delete(seenChat.values().next().value);
      call('onChat', m);
    };

    const ch = sb.channel(`room:${roomId}`, {
      config: { private: true, presence: { key: me }, broadcast: { self: false } },
    });

    ch.on('presence', { event: 'sync' }, () => {
      if (closed) return;
      synced = true;
      const list = [];
      const state = ch.presenceState();
      for (const metas of Object.values(state)) {
        if (!Array.isArray(metas) || !metas.length) continue;
        const st = cleanPresenceState(metas[metas.length - 1]);
        if (st) list.push(st);
      }
      call('onSync', list);
    });
    // join/leave: 첫 sync 전(이미 있던 사람)은 무시. currentPresences가 있으면 track 갱신이지 새 입장/퇴장이 아니다.
    ch.on('presence', { event: 'join' }, ({ key, currentPresences, newPresences }) => {
      if (!synced || key === me || (currentPresences && currentPresences.length)) return;
      const st = cleanPresenceState(newPresences && newPresences[newPresences.length - 1]);
      if (st) call('onJoin', st);
    });
    ch.on('presence', { event: 'leave' }, ({ key, currentPresences, leftPresences }) => {
      if (!synced || key === me || (currentPresences && currentPresences.length)) return;
      const st = cleanPresenceState(leftPresences && leftPresences[leftPresences.length - 1]);
      if (st) call('onLeave', st);
    });
    ch.on('broadcast', { event: 'move' }, (msg) => {
      const p = msg && msg.payload;
      if (p && typeof p === 'object' && p.user_id !== me) call('onMove', p);
    });
    // chat은 서버(send_message → realtime.send)만 보낸다. 형식이 맞지 않으면 버린다.
    // 같은 방 멤버의 위조 송신은 수신 측에서 구분할 수 없다(알려진 한계 1). 신뢰 기록은 recent_messages.
    ch.on('broadcast', { event: 'chat' }, (msg) => deliver(msg && msg.payload));

    const mover = createThrottle(MOVE_INTERVAL_MS, (p) => {
      ch.send({ type: 'broadcast', event: 'move', payload: p }).catch(() => {});
    });
    const scheduleTrack = () => {
      clearTimeout(trackTimer);
      trackTimer = setTimeout(() => { if (!closed) ch.track({ ...myState }).catch(() => {}); }, TRACK_IDLE_MS);
    };

    // 탭 닫기: leave_room은 보장할 수 없으므로 Presence만 내린다. 멤버 행은 활성 60초 규칙에 맡긴다.
    const onPageHide = () => { try { ch.untrack(); } catch { /* 무시 */ } };
    window.addEventListener('pagehide', onPageHide);

    const leave = async () => {
      if (closed) return;
      closed = true;
      mover.cancel();
      clearTimeout(trackTimer);
      clearInterval(heartbeatTimer);
      window.removeEventListener('pagehide', onPageHide);
      conns.delete(conn);
      try { await ch.untrack(); } catch { /* 무시 */ }
      try { await sb.removeChannel(ch); } catch { /* 무시 */ }
    };

    const conn = {
      roomId,
      deliver,
      async sendMove({ x, y, dir }) {
        if (closed) throw new AppError('NETWORK');
        myState.x = x;
        myState.y = y;
        mover.push({ user_id: me, x, y, dir: dir === 'left' ? 'left' : 'right' });
        scheduleTrack(); // 정지 후 좌표를 Presence에도 반영 (새로 들어오는 사람용)
      },
      async updateSelf(partial) {
        if (closed) throw new AppError('NETWORK');
        for (const k of ['nickname', 'avatar', 'x', 'y']) if (partial && Object.prototype.hasOwnProperty.call(partial, k)) myState[k] = partial[k];
        const r = await ch.track({ ...myState });
        if (r !== 'ok') throw new AppError('NETWORK', r);
      },
      leave,
    };

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (!subscribed) { leave(); reject(new AppError('NETWORK', 'subscribe timeout')); }
      }, SUBSCRIBE_TIMEOUT_MS);
      ch.subscribe(async (status, err) => {
        if (closed) return;
        if (status === 'SUBSCRIBED') {
          try {
            const r = await ch.track({ ...myState });
            if (r !== 'ok') throw new Error(String(r));
          } catch (e) {
            if (!subscribed) { clearTimeout(timeout); leave(); reject(new AppError('NETWORK', e)); }
            return;
          }
          if (!subscribed) { subscribed = true; clearTimeout(timeout); resolve(); }
          call('onStatus', 'connected');
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          // 비멤버 구독은 CHANNEL_ERROR(정책 거부). 첫 구독 실패는 화면이 재시도/치명 처리.
          if (!subscribed) { clearTimeout(timeout); leave(); reject(new AppError('NETWORK', err || status)); }
          else call('onStatus', 'disconnected');
        }
      });
    });

    // 하트비트 20초 (ARCHITECTURE 결정 4). NOT_MEMBER면 화면에 알린다. 네트워크 오류는 채널 상태가 알린다.
    heartbeatTimer = setInterval(() => {
      rpc('heartbeat', { p_room_id: roomId }).catch((e) => {
        if (e && e.code === 'NOT_MEMBER') call('onStatus', 'not_member');
      });
    }, HEARTBEAT_MS);

    conns.add(conn);
    return conn;
  }

  return {
    mode: 'supabase',

    async init() {
      await ensureSession();
      return { userId };
    },

    async listRooms() {
      requireInit();
      const rows = await rpc('list_rooms', {});
      return (Array.isArray(rows) ? rows : []).map((r) => ({
        id: r.id, name: r.name, locked: !!r.locked, members: Number(r.members) || 0, createdAt: r.created_at,
      }));
    },

    async createRoom({ name, password, nickname }) {
      requireInit();
      const id = await rpc('create_room', { p_name: name, p_password: password || null, p_nickname: nickname });
      if (typeof id !== 'string') throw new AppError('UNKNOWN', 'no room id');
      return { roomId: id };
    },

    async joinRoom({ roomId, password, nickname }) {
      requireInit();
      const r = await rpc('join_room', { p_room_id: roomId, p_password: password || null, p_nickname: nickname });
      if (r === 'WRONG_PASSWORD') throw new AppError('WRONG_PASSWORD');
      if (r !== 'OK') throw new AppError('UNKNOWN', r);
    },

    async leaveRoom(roomId) {
      requireInit();
      await rpc('leave_room', { p_room_id: roomId });
    },

    async heartbeat(roomId) {
      requireInit();
      await rpc('heartbeat', { p_room_id: roomId });
    },

    async recentMessages(roomId) {
      requireInit();
      const rows = await rpc('recent_messages', { p_room_id: roomId });
      return (Array.isArray(rows) ? rows : []).map(cleanChatMessage).filter(Boolean);
    },

    async sendChat(roomId, text) {
      requireInit();
      const msg = cleanChatMessage(await rpc('send_message', { p_room_id: roomId, p_text: text }));
      if (!msg) throw new AppError('UNKNOWN', 'bad message');
      // 반환값도 실시간 chat과 같은 경로로 (id 중복 제거). realtime.send가 실패해도 내 로그에는 남는다.
      for (const c of conns) if (c.roomId === roomId) c.deliver(msg);
      return msg;
    },

    async connectRoom(roomId, handlers, self) {
      requireInit();
      const c = await connect(roomId, handlers, self);
      return { sendMove: c.sendMove, updateSelf: c.updateSelf, leave: c.leave };
    },
  };
}
