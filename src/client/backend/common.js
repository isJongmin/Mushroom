import { cleanGarden, GARDEN_TITLE } from '../game/garden.js';
import { normalizeMapId } from '../game/areas.js';
import { normalizeJob } from '../game/jobs.js';
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
    mapId: normalizeMapId(s.mapId),
    nickname: typeof s.nickname === 'string' ? s.nickname.slice(0, 32) : '',
    title: s.title === GARDEN_TITLE ? GARDEN_TITLE : null,
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
 * (사이클 8) push(v, true) = 급송(fx 이펙트 1회): 간격을 기다리지 않고 바로 보낸다(대기 중인 값은 이것으로 대체).
 *   남용 방지: 급송은 urgentWindowMs(2초) 안에 urgentMax(4)회까지. 넘으면 보통 규칙으로 보낸다.
 */
export function createThrottle(intervalMs, send, { urgentMax = 4, urgentWindowMs = 2000 } = {}) {
  let last = -Infinity;
  let pending = null;
  let timer = 0;
  const urgentAt = [];
  const flush = () => {
    timer = 0;
    const v = pending;
    pending = null;
    if (v) { last = performance.now(); send(v); }
  };
  return {
    push(v, urgent = false) {
      const now = performance.now();
      if (urgent) {
        while (urgentAt.length && now - urgentAt[0] > urgentWindowMs) urgentAt.shift();
        if (urgentAt.length < urgentMax) {
          urgentAt.push(now);
          clearTimeout(timer);
          timer = 0;
          pending = null;
          last = now;
          send(v);
          return;
        }
      }
      const wait = intervalMs - (now - last);
      if (wait <= 0 && !timer) { last = now; send(v); return; }
      pending = v;
      if (!timer) timer = setTimeout(flush, Math.max(0, wait));
    },
    cancel() { clearTimeout(timer); timer = 0; pending = null; },
  };
}

// ---------------------------------------------------------------------------
// (사이클 9) 게임 broadcast 이벤트: atk, hp, mobs, drop, pick, picked (ARCHITECTURE "사이클 9 계약").
// 두 어댑터가 같은 규칙으로 보내고(send) 받는다(onEvent). 형식이 틀리면 버린다.
// 보낸 사람 표시: atk/hp/pick의 user_id와 mobs/drop/picked의 host는 어댑터가 자기 uid로 덮어쓴다(위장은 알려진 한계).
export const GAME_EVENTS = Object.freeze(['atk', 'hp', 'mobs', 'drop', 'pick', 'picked', 'impact', 'garden-start']);
const GAME_EVENT_SET = new Set(GAME_EVENTS);
export const isGameEvent = (e) => typeof e === 'string' && GAME_EVENT_SET.has(e);
const UID_OK = (v) => typeof v === 'string' && v.length > 0 && v.length <= 64;
const SID_RE = /^[a-z0-9]{1,16}$/i;
const KIND_RE = /^[a-z0-9-]{1,32}$/;
const BUFF_SET = new Set(['heal']); // (사이클 10) game/buffs.js DROP_KINDS (버프 5종 + heal)
const DM_OK = (v) => Array.isArray(v) && v.length > 0 && v.length <= 12 && v.every((n) => Number.isInteger(n) && n >= 0 && n <= 1000);
const MOB_S = new Set(['move', 'hit', 'die']);
const numIn = (v, lo, hi) => isNum(v) && v >= lo && v <= hi;
const COORD = 1e5;
const MOBS_MAX = 80;

/** 보낸 쪽 표시를 붙인다 (어댑터 송신 직전) */
export function stampGameEvent(event, payload, uid) {
  const p = { ...payload };
  if (event === 'atk' || event === 'hp' || event === 'pick' || event === 'garden-start') p.user_id = uid;
  else p.host = uid;
  return p;
}

/** 수신 payload 정리. 깨진 값이면 null */
function cleanGameEventPayload(event, p) {
  if (!isGameEvent(event) || !p || typeof p !== 'object') return null;
  switch (event) {
    case 'garden-start':
      return UID_OK(p.user_id) ? { user_id:p.user_id } : null;
    case 'atk':
      if (!UID_OK(p.user_id) || !numIn(p.x, -COORD, COORD) || !numIn(p.y, -COORD, COORD)) return null;
      // (사이클 10) 강화 값 w, hits, dmin, dmax, el은 숫자만 넘기고 상한 자르기는 화면(buffs.clampAttack)이 한다
      return {
        job: normalizeJob(p.job), skill: p.skill == null ? 0 : Number.isInteger(p.skill) && p.skill >= 0 && p.skill <= 3 ? p.skill : -1, cooldown: numIn(p.cooldown, 0, 15) ? p.cooldown : null,
        user_id: p.user_id, x: p.x, y: p.y, dir: p.dir === 'left' ? 'left' : 'right', seq: Number.isInteger(p.seq) ? p.seq : 0,
        w: isNum(p.w) ? p.w : null, hits: isNum(p.hits) ? p.hits : null, dmin: isNum(p.dmin) ? p.dmin : null, dmax: isNum(p.dmax) ? p.dmax : null, el: isNum(p.el) ? p.el : null,
      };
    case 'impact':
      if (!UID_OK(p.host) || typeof p.id !== 'string' || !/^[a-zA-Z0-9:_-]{1,110}$/.test(p.id)) return null;
      if (!numIn(p.x, -COORD, COORD) || !numIn(p.y, -COORD, COORD)) return null;
      if (p.skill != null && (!Number.isInteger(p.skill) || p.skill < 0 || p.skill > 3)) return null;
      return { host: p.host, id: p.id, x: p.x, y: p.y, job: normalizeJob(p.job), skill: p.skill ?? 0 };
    case 'hp':
      if (!UID_OK(p.user_id) || !numIn(p.hp, 0, 100000) || !numIn(p.max, 1, 100000)) return null;
      // dm = (사이클 10 확장) 이번에 받은 타별 피해 (피해 숫자용)
      return { user_id: p.user_id, hp: Math.min(p.hp, p.max), max: p.max, dead: p.dead === true, by: UID_OK(p.by) ? p.by : null, dm: DM_OK(p.dm) ? p.dm : null };
    case 'mobs': {
      if (!UID_OK(p.host) || !Array.isArray(p.list) || p.list.length > MOBS_MAX) return null;
      const list = [];
      for (const m of p.list) {
        if (!m || typeof m !== 'object' || typeof m.id !== 'string' || !SID_RE.test(m.id) || typeof m.kind !== 'string' || !KIND_RE.test(m.kind)) continue;
        if (!numIn(m.x, -COORD, COORD) || !numIn(m.y, -COORD, COORD) || !numIn(m.hp, 0, 1e6)) continue;
        const o = { id: m.id, kind: m.kind, x: m.x, y: m.y, dir: m.dir < 0 ? -1 : 1, hp: m.hp, s: MOB_S.has(m.s) ? m.s : 'move', z: Number.isInteger(m.z) && m.z >= 0 && m.z < 64 ? m.z : -1 };
        if (DM_OK(m.dm)) o.dm = m.dm;
        list.push(o);
      }
      return { host: p.host, t: isNum(p.t) ? p.t : 0, list, garden: cleanGarden(p.garden) };
    }
    case 'drop':
      if (!UID_OK(p.host) || typeof p.id !== 'string' || !SID_RE.test(p.id) || !BUFF_SET.has(p.buff)) return null;
      if (!numIn(p.x, -COORD, COORD) || !numIn(p.y, -COORD, COORD)) return null;
      return { host: p.host, id: p.id, buff: p.buff, x: p.x, y: p.y, ttl: numIn(p.ttl, 1, 30000) ? p.ttl : null };
    case 'pick':
      if (!UID_OK(p.user_id) || typeof p.drop_id !== 'string' || !SID_RE.test(p.drop_id)) return null;
      return { user_id: p.user_id, drop_id: p.drop_id };
    case 'picked':
      if (!UID_OK(p.host) || !UID_OK(p.user_id) || typeof p.drop_id !== 'string' || !SID_RE.test(p.drop_id) || !BUFF_SET.has(p.buff)) return null;
      return { host: p.host, drop_id: p.drop_id, user_id: p.user_id, buff: p.buff };
    default:
      return null;
  }
}

/** Every game packet belongs to one area; old clients belong to the village. */
export function cleanGameEvent(event, p) {
  const payload = cleanGameEventPayload(event, p);
  return payload ? { ...payload, mapId: normalizeMapId(p.mapId) } : null;
}

/**
 * 게임 이벤트 송신 제한 (Supabase broadcast 한도 보호).
 *   mobs: 최소 180ms 간격, 마지막 값만 보낸다(throttle).  그 밖: 이벤트마다 1초에 최대 12건, 넘으면 버린다(stats.evDropped).
 * send(event, payload) 를 그대로 부르거나 미룬다. cancel()로 대기 중인 송신을 버린다.
 */
export function createEventGate(send, stats) {
  const mobs = createThrottle(180, (p) => send('mobs', p), { urgentMax: 0 });
  const recent = new Map(); // event -> [시각]
  return {
    push(event, payload) {
      if (event === 'mobs') { mobs.push(payload); return true; }
      const now = performance.now();
      let r = recent.get(event);
      if (!r) { r = []; recent.set(event, r); }
      while (r.length && now - r[0] >= 1000) r.shift();
      // Two shots per fast attack, with room for delivery bunching; all event rates remain bounded.
      if (r.length >= (event === 'atk' ? 10 : event === 'impact' ? 40 : 12)) { if (stats) stats.evDropped = (stats.evDropped || 0) + 1; return false; }
      r.push(now);
      send(event, payload);
      return true;
    },
    cancel() { mobs.cancel(); recent.clear(); },
  };
}
