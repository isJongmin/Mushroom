// supabase 모드 어댑터.
// supabase-js는 ARCHITECTURE.md가 고정한 CDN URL에서 "처음 필요할 때" 동적 import 한다.
// local 모드에서는 이 파일 자체가 import되지 않는다(backend/index.js 참고).
//
// 오류 매핑은 docs/handoff/backend-20261014-schema.md, supabase/README.md 그대로:
//   Auth:  user_already_exists → ID_TAKEN, invalid_credentials → LOGIN_FAILED, weak_password → PW_SHORT,
//          over_request_rate_limit(429) → SERVER, email_not_confirmed → SERVER(대시보드 설정 문제)
//   insert: 23505 + characters_nickname_lower_key → NICK_TAKEN
//           23505 + characters_pkey               → CHAR_EXISTS (재조회 후 맵으로)
//           23514 + characters_nickname_format    → NICK_FORMAT
//           23514 + characters_avatar_shape       → AVATAR_FORMAT (avatar는 항상 정확히 7개 키로 보낸다)
//           23502                                 → SERVER (필수 값 누락)
//           42501                                 → AUTH_REQUIRED (다시 로그인)
//   fetch 실패/오프라인 → NETWORK
import { AppError } from '../errors.js';
import { SUPABASE_CDN, CHANNEL_NAME, CHAT_MAX } from '../constants.js';
import { assertCredentials, isValidAvatarShape, isValidNickname, pickAvatar, readAvatar } from './common.js';

const emailOf = (id) => `${id}@mushroom.local`;
const TRACK_IDLE_MS = 600; // 정지 후 Presence 좌표 갱신(track) 지연
const JOIN_TIMEOUT_MS = 10000;

function isNetworkError(err) {
  if (!err) return false;
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return true;
  if (err.name === 'AuthRetryableFetchError') return true;
  if (err.status === 0) return true;
  const msg = String(err.message || err);
  return !err.code && /fetch|network|load failed|timed? ?out/i.test(msg);
}

function mapAuthError(err, { signup }) {
  if (!err) return new AppError('SERVER');
  if (isNetworkError(err)) return new AppError('NETWORK', err);
  const code = err.code || '';
  if (code === 'user_already_exists' || /already registered/i.test(err.message || '')) {
    return new AppError(signup ? 'ID_TAKEN' : 'LOGIN_FAILED', err);
  }
  if (code === 'invalid_credentials' || /invalid login credentials/i.test(err.message || '')) return new AppError('LOGIN_FAILED', err);
  if (code === 'weak_password') return new AppError(signup ? 'PW_SHORT' : 'LOGIN_FAILED', err);
  if (code === 'over_request_rate_limit' || err.status === 429) return new AppError('SERVER', err);
  if (code === 'email_not_confirmed') return new AppError('SERVER', err);
  return new AppError('SERVER', err);
}

function mapDbError(err) {
  if (!err) return new AppError('SERVER');
  if (isNetworkError(err)) return new AppError('NETWORK', err);
  const msg = String(err.message || '') + ' ' + String(err.details || '');
  switch (err.code) {
    case '23505':
      if (msg.includes('characters_nickname_lower_key')) return new AppError('NICK_TAKEN', err);
      if (msg.includes('characters_pkey')) return new AppError('CHAR_EXISTS', err);
      return new AppError('SERVER', err);
    case '23514':
      if (msg.includes('characters_nickname_format')) return new AppError('NICK_FORMAT', err);
      if (msg.includes('characters_avatar_shape')) return new AppError('AVATAR_FORMAT', err);
      return new AppError('SERVER', err);
    case '23502':
      return new AppError('SERVER', err);
    case '42501':
    case 'PGRST301': // JWT 만료 등
      return new AppError('AUTH_REQUIRED', err);
    default:
      return new AppError('SERVER', err);
  }
}

export function createSupabaseBackend(url, anonKey) {
  let clientPromise = null;
  let activeMap = null;

  function client() {
    if (!clientPromise) {
      clientPromise = import(SUPABASE_CDN)
        .then((mod) => mod.createClient(url, anonKey, { auth: { persistSession: true, autoRefreshToken: true } }))
        .catch((e) => {
          clientPromise = null; // 다음 시도에서 다시 로드
          throw new AppError('NETWORK', e);
        });
    }
    return clientPromise;
  }

  async function uid() {
    const sb = await client();
    const { data, error } = await sb.auth.getSession();
    if (error) throw mapAuthError(error, { signup: false });
    const id = data && data.session && data.session.user && data.session.user.id;
    if (!id) throw new AppError('AUTH_REQUIRED');
    return id;
  }

  async function joinMapSupabase(handlers, self) {
    const sb = await client();
    const myState = { ...self };
    let closed = false;
    let joined = false;
    let trackTimer = 0;

    const ch = sb.channel(CHANNEL_NAME, { config: { presence: { key: myState.user_id }, broadcast: { self: false } } });

    ch.on('presence', { event: 'sync' }, () => {
      if (closed) return;
      const state = ch.presenceState();
      const list = [];
      for (const metas of Object.values(state)) {
        if (Array.isArray(metas) && metas.length) list.push(metas[metas.length - 1]);
      }
      handlers.onPresence?.(list);
    })
      .on('broadcast', { event: 'move' }, (msg) => { if (!closed) handlers.onMove?.(msg && msg.payload); })
      .on('broadcast', { event: 'chat' }, (msg) => { if (!closed) handlers.onChat?.(msg && msg.payload); });

    const onPageHide = () => { try { sb.removeChannel(ch); } catch { /* 무시 */ } };
    window.addEventListener('pagehide', onPageHide);

    const leave = async () => {
      if (closed) return;
      closed = true;
      clearTimeout(trackTimer);
      window.removeEventListener('pagehide', onPageHide);
      try { await ch.untrack(); } catch { /* 무시 */ }
      try { await sb.removeChannel(ch); } catch { /* 무시 */ }
      if (activeMap === api) activeMap = null;
    };

    const api = {
      async sendMove({ x, y, dir }) {
        if (closed) throw new AppError('NETWORK');
        myState.x = x;
        myState.y = y;
        const r = await ch.send({ type: 'broadcast', event: 'move', payload: { user_id: myState.user_id, x, y, dir } });
        // 정지 후 Presence 좌표도 갱신해서 새로 들어오는 사람이 올바른 위치를 보게 한다
        clearTimeout(trackTimer);
        trackTimer = setTimeout(() => { if (!closed) ch.track({ ...myState }).catch(() => {}); }, TRACK_IDLE_MS);
        if (r !== 'ok') throw new AppError('NETWORK', r);
      },
      async sendChat(text) {
        if (closed) throw new AppError('NETWORK');
        const r = await ch.send({ type: 'broadcast', event: 'chat', payload: { user_id: myState.user_id, text: String(text).slice(0, CHAT_MAX) } });
        if (r !== 'ok') throw new AppError('NETWORK', r);
      },
      leave,
    };

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => { if (!joined) { leave(); reject(new AppError('NETWORK', 'join timeout')); } }, JOIN_TIMEOUT_MS);
      ch.subscribe(async (status, err) => {
        if (closed) return;
        if (status === 'SUBSCRIBED') {
          try {
            await ch.track({ ...myState });
          } catch (e) {
            if (!joined) { clearTimeout(timeout); leave(); reject(new AppError('NETWORK', e)); }
            return;
          }
          if (!joined) { joined = true; clearTimeout(timeout); resolve(); }
          handlers.onStatus?.('connected');
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          if (!joined) { clearTimeout(timeout); leave(); reject(new AppError('NETWORK', err || status)); }
          else handlers.onStatus?.('disconnected');
        }
      });
    });

    activeMap = api;
    return api;
  }

  return {
    mode: 'supabase',

    async signUp(id, password) {
      assertCredentials(id, password, { signup: true });
      const sb = await client();
      let res;
      try {
        res = await sb.auth.signUp({ email: emailOf(id), password });
      } catch (e) {
        throw mapAuthError(e, { signup: true });
      }
      if (res.error) throw mapAuthError(res.error, { signup: true });
      // Confirm email이 켜져 있으면 session이 없다 → 대시보드 설정 문제(SERVER로 안내)
      // 이미 있는 이메일에 대해 일부 설정은 오류 대신 identities가 빈 user를 돌려준다
      const user = res.data && res.data.user;
      if (user && Array.isArray(user.identities) && user.identities.length === 0) throw new AppError('ID_TAKEN');
      if (!res.data || !res.data.session) throw new AppError('SERVER', 'no session (Confirm email ON?)');
      return { user_id: res.data.session.user.id, login_id: id };
    },

    async signIn(id, password) {
      assertCredentials(id, password, { signup: false });
      const sb = await client();
      let res;
      try {
        res = await sb.auth.signInWithPassword({ email: emailOf(id), password });
      } catch (e) {
        throw mapAuthError(e, { signup: false });
      }
      if (res.error) throw mapAuthError(res.error, { signup: false });
      return { user_id: res.data.session.user.id, login_id: id };
    },

    async signOut() {
      if (activeMap) await activeMap.leave();
      if (!clientPromise) return;
      try {
        const sb = await client();
        await sb.auth.signOut();
      } catch {
        // 네트워크 오류여도 로컬 세션은 supabase-js가 지운다. 화면은 로그인으로 보낸다.
      }
    },

    async getSession() {
      const sb = await client();
      const { data, error } = await sb.auth.getSession();
      if (error) throw mapAuthError(error, { signup: false });
      const s = data && data.session;
      if (!s || !s.user) return null;
      const email = s.user.email || '';
      return { user_id: s.user.id, login_id: email.replace(/@mushroom\.local$/, '') };
    },

    async getMyCharacter() {
      const id = await uid();
      const sb = await client();
      let res;
      try {
        res = await sb.from('characters').select('user_id,nickname,avatar').eq('user_id', id).maybeSingle();
      } catch (e) {
        throw mapDbError(e);
      }
      if (res.error) throw mapDbError(res.error);
      // 마이그레이션 전/후 어느 형식이든 7개 키(eyes→face, 옛 id 별칭, 누락 키 기본값)로 읽는다
      return res.data ? { user_id: res.data.user_id, nickname: res.data.nickname, avatar: readAvatar(res.data.avatar) } : null;
    },

    async isNicknameTaken(nickname) {
      const sb = await client();
      let res;
      try {
        res = await sb.rpc('is_nickname_taken', { p_nickname: nickname });
      } catch (e) {
        throw mapDbError(e);
      }
      if (res.error) throw mapDbError(res.error);
      return res.data === true;
    },

    async createCharacter(nickname, avatar) {
      if (!isValidNickname(nickname)) throw new AppError('NICK_FORMAT');
      if (!isValidAvatarShape(avatar)) throw new AppError('AVATAR_FORMAT');
      const id = await uid();
      const sb = await client();
      const row = { user_id: id, nickname, avatar: pickAvatar(avatar) };
      let res;
      try {
        res = await sb.from('characters').insert(row); // upsert 금지, created_at 보내지 않음
      } catch (e) {
        throw mapDbError(e);
      }
      if (res.error) throw mapDbError(res.error);
      return { user_id: id, nickname, avatar: row.avatar };
    },

    async joinMap(handlers, self) {
      const id = await uid();
      if (activeMap) await activeMap.leave();
      return joinMapSupabase(handlers, { ...self, user_id: id });
    },

    async leaveMap() {
      if (activeMap) await activeMap.leave();
    },
  };
}
