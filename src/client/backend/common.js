// 두 어댑터가 공유하는 검증. 서버(DB 제약)와 같은 규칙을 클라이언트에서도 확인한다.
import { ID_RE, PW_MIN, NICK_RE, PART_KEYS, PART_ID_RE } from '../constants.js';
import { AppError } from '../errors.js';

export function assertCredentials(id, password, { signup }) {
  if (typeof id !== 'string' || !ID_RE.test(id)) throw new AppError(signup ? 'ID_FORMAT' : 'LOGIN_FAILED');
  if (typeof password !== 'string' || password.length === 0) throw new AppError('LOGIN_FAILED');
  if (signup && password.length < PW_MIN) throw new AppError('PW_SHORT');
}

/** characters_avatar_shape 와 같은 규칙: 정확히 5개 키, 각 값 ^[a-z0-9-]{1,32}$ */
export function isValidAvatarShape(avatar) {
  if (!avatar || typeof avatar !== 'object' || Array.isArray(avatar)) return false;
  const keys = Object.keys(avatar);
  if (keys.length !== PART_KEYS.length) return false;
  return PART_KEYS.every((k) => typeof avatar[k] === 'string' && PART_ID_RE.test(avatar[k]));
}

export function isValidNickname(nickname) {
  return typeof nickname === 'string' && NICK_RE.test(nickname);
}

export function pickAvatar(avatar) {
  const out = {};
  for (const k of PART_KEYS) out[k] = avatar[k];
  return out;
}
