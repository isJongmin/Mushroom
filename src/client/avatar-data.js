// 아바타 데이터 정규화 (ARCHITECTURE "인터페이스 계약", 사이클 3: 7개 키).
// DOM/Canvas에 의존하지 않는 순수 함수만 둔다. 백엔드 어댑터와 화면이 같이 쓴다.
//
// 규칙 (normalizeAvatar):
//  1. 입력이 일반 객체가 아니면 빈 객체로 본다.
//  2. 키 이름 변환: face가 없으면 옛 키 eyes 값을 face로 쓴다 (사이클 1~2).
//  3. 값이 문자열이 아니거나 ^[a-z0-9-]{1,32}$ 가 아니면 버린다.
//  4. 옛 id 별칭: LEGACY_ALIASES(art 매핑표) → manifest aliases(있으면) 순서로 바꾼다.
//  5. ids(파츠별 manifest id 집합)가 주어지면 거기에 없는 id는 그 파츠 기본값(manifest 첫 항목).
//     ids가 없으면(매니페스트 전) 형식만 맞으면 그대로 둔다.
//  6. 누락 키는 기본값. 결과는 항상 정확히 7개 키 (PART_KEYS 순서), 추가 키는 버린다.
import { PART_KEYS, PART_ID_RE, DEFAULT_AVATAR, LEGACY_ALIASES } from './constants.js';

const isPlainObject = (v) => !!v && typeof v === 'object' && !Array.isArray(v);
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

/**
 * @param raw      저장/수신된 avatar (어떤 형태든)
 * @param opts.ids       { part: Set<id> } manifest에 있는 id (없으면 형식 검사만)
 * @param opts.defaults  { part: id } 기본값 (없으면 DEFAULT_AVATAR)
 * @param opts.aliases   { part: { oldId: newId } } manifest aliases (선택)
 * @returns 정확히 7개 키를 가진 새 객체
 */
export function normalizeAvatar(raw, opts = {}) {
  const src = isPlainObject(raw) ? raw : {};
  const defaults = opts.defaults || DEFAULT_AVATAR;
  const out = {};
  for (const part of PART_KEYS) {
    let v = own(src, part) ? src[part] : undefined;
    if (part === 'face' && (typeof v !== 'string' || !v) && own(src, 'eyes')) v = src.eyes;
    if (typeof v !== 'string' || !PART_ID_RE.test(v)) v = null;
    if (v !== null) {
      const ids = opts.ids && opts.ids[part];
      const legacy = LEGACY_ALIASES[part];
      const extra = opts.aliases && opts.aliases[part];
      if (!(ids && ids.has(v))) {
        if (legacy && own(legacy, v)) v = legacy[v];
        else if (extra && own(extra, v)) v = extra[v];
      }
      if (ids && !ids.has(v)) v = null;
    }
    out[part] = v !== null ? v : defaults[part];
  }
  return out;
}

/** 저장 형식 검사 (characters_avatar_shape 와 같은 규칙): 정확히 7개 키, 각 값 ^[a-z0-9-]{1,32}$ */
export function isValidAvatarShape(avatar) {
  if (!isPlainObject(avatar)) return false;
  const keys = Object.keys(avatar);
  if (keys.length !== PART_KEYS.length) return false;
  return PART_KEYS.every((k) => own(avatar, k) && typeof avatar[k] === 'string' && PART_ID_RE.test(avatar[k]));
}

/** 저장용: PART_KEYS 순서의 정확히 7개 키 복사본 */
export function pickAvatar(avatar) {
  const out = {};
  for (const k of PART_KEYS) out[k] = avatar[k];
  return out;
}
