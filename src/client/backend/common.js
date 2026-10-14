// 두 어댑터가 공유하는 검증. 서버(DB 제약)와 같은 규칙을 클라이언트에서도 확인한다.
import { ID_RE, PW_MIN, NICK_RE } from '../constants.js';
import { AppError } from '../errors.js';
import { isValidAvatarShape, pickAvatar, normalizeAvatar } from '../avatar-data.js';

export { isValidAvatarShape, pickAvatar };

export function assertCredentials(id, password, { signup }) {
  if (typeof id !== 'string' || !ID_RE.test(id)) throw new AppError(signup ? 'ID_FORMAT' : 'LOGIN_FAILED');
  if (typeof password !== 'string' || password.length === 0) throw new AppError('LOGIN_FAILED');
  if (signup && password.length < PW_MIN) throw new AppError('PW_SHORT');
}

export function isValidNickname(nickname) {
  return typeof nickname === 'string' && NICK_RE.test(nickname);
}

/**
 * DB/localStorage에서 읽은 avatar를 7개 키로 맞춘다 (eyes→face, 옛 id 별칭, 누락 키 기본값).
 * manifest id 검사는 화면 쪽(assets.sanitizeAvatar)이 한다. 저장된 값은 바꾸지 않는다.
 */
export function readAvatar(raw) {
  return normalizeAvatar(raw);
}
