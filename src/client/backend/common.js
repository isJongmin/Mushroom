// 두 어댑터와 화면이 공유하는 형식 검사. 서버(supabase/migrations/20261015000000_rooms.sql)와 같은 규칙.
import { NICK_RE, ROOM_NAME_MAX, ROOM_PW_MIN, ROOM_PW_MAX, CHAT_MAX } from '../constants.js';
import { AppError } from '../errors.js';
import { normalizeAvatar } from '../avatar-data.js';

// 서버 app_private.trim_ws: 앞뒤 공백(일반 공백, 탭, 개행, NBSP, 전각 공백 U+3000, BOM) 제거. JS \s가 모두 포함한다.
const TRIM_RE = /^[\s\u00A0\u3000\uFEFF]+|[\s\u00A0\u3000\uFEFF]+$/g;
// 서버 [[:cntrl:]] (유니코드 Cc: U+0000–U+001F, U+007F–U+009F). 줄바꿈 포함.
const CNTRL_RE = /[\u0000-\u001F\u007F-\u009F]/;

export function trimWs(s) {
  return typeof s === 'string' ? s.replace(TRIM_RE, '') : '';
}
export function hasControl(s) {
  return CNTRL_RE.test(s);
}
/** 코드 포인트 수 (PostgreSQL char_length와 같음) */
export function charLength(s) {
  let n = 0;
  for (const _ of s) n++; // eslint-disable-line no-unused-vars
  return n;
}

export function isValidNickname(nickname) {
  return typeof nickname === 'string' && NICK_RE.test(nickname);
}

/** 방 이름: trim 후 1~24자, 제어문자 금지. 반환: 정리한 이름 또는 null */
export function cleanRoomName(name) {
  if (typeof name !== 'string') return null;
  const v = trimWs(name);
  const n = charLength(v);
  if (n < 1 || n > ROOM_NAME_MAX || hasControl(v)) return null;
  return v;
}

/** 비밀번호: null/'' = 공개, 그 외 4~32자 (trim 하지 않음). 반환: '' (공개) | 비밀번호 | null(형식 오류) */
export function cleanRoomPassword(pw) {
  if (pw == null || pw === '') return '';
  if (typeof pw !== 'string') return null;
  const n = charLength(pw);
  return n >= ROOM_PW_MIN && n <= ROOM_PW_MAX ? pw : null;
}

/** 채팅: trim 후 1~80자, 제어문자 금지. 반환: 정리한 글 또는 null */
export function cleanChatText(text) {
  if (typeof text !== 'string') return null;
  const v = trimWs(text);
  const n = charLength(v);
  if (n < 1 || n > CHAT_MAX || hasControl(v)) return null;
  return v;
}

export function assertNickname(nickname) {
  if (!isValidNickname(nickname)) throw new AppError('NICK_FORMAT');
}

/** 저장소/Presence에서 읽은 avatar를 7개 키로 맞춘다 (manifest id 검사는 화면 쪽 assets.sanitizeAvatar). */
export function readAvatar(raw) {
  return normalizeAvatar(raw);
}

const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

/** Presence 상태 { user_id, nickname, avatar, x, y } 정리. 깨진 값이면 null */
export function cleanPresenceState(s) {
  if (!s || typeof s !== 'object') return null;
  if (typeof s.user_id !== 'string' || !s.user_id || s.user_id.length > 64) return null;
  return {
    user_id: s.user_id,
    nickname: typeof s.nickname === 'string' ? s.nickname.slice(0, 32) : '',
    avatar: s.avatar && typeof s.avatar === 'object' ? s.avatar : null,
    x: isNum(s.x) ? s.x : null,
    y: isNum(s.y) ? s.y : null,
  };
}

/** 서버 chat 페이로드 { id, user_id, nickname, text, created_at } 정리. 깨진 값이면 null */
export function cleanChatMessage(m) {
  if (!m || typeof m !== 'object') return null;
  const id = typeof m.id === 'string' && /^\d{1,18}$/.test(m.id) ? Number(m.id) : m.id;
  if (!Number.isSafeInteger(id) || id <= 0) return null;
  if (typeof m.user_id !== 'string' || !m.user_id || m.user_id.length > 64) return null;
  if (typeof m.text !== 'string' || charLength(m.text) > CHAT_MAX || hasControl(m.text)) return null;
  const nickname = typeof m.nickname === 'string' && NICK_RE.test(m.nickname) ? m.nickname : '???';
  const t = typeof m.created_at === 'string' ? Date.parse(m.created_at) : NaN;
  return {
    id,
    user_id: m.user_id,
    nickname,
    text: m.text,
    created_at: Number.isFinite(t) ? new Date(t).toISOString() : new Date().toISOString(),
  };
}

/**
 * 같은 throttle 규칙(최대 10회/초, 마지막 값은 반드시 보냄)을 두 어댑터가 쓴다.
 * send(v)를 즉시 또는 남은 간격 뒤에 호출한다. cancel()로 대기 중인 송신을 버린다.
 */
export function createThrottle(intervalMs, send) {
  let last = -Infinity;
  let pending = null;
  let timer = 0;
  const flush = () => {
    timer = 0;
    const v = pending;
    pending = null;
    if (v) { last = performance.now(); send(v); }
  };
  return {
    push(v) {
      const wait = intervalMs - (performance.now() - last);
      if (wait <= 0 && !timer) { last = performance.now(); send(v); return; }
      pending = v;
      if (!timer) timer = setTimeout(flush, Math.max(0, wait));
    },
    cancel() { clearTimeout(timer); timer = 0; pending = null; },
  };
}
