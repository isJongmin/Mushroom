// 어댑터는 항상 AppError(code)를 던진다. 화면은 code를 화면별(맥락별) 문구로 바꾼다.
// 문구 정본: docs/handoff/design-20261015-rooms.md 4장, screens/{profile,lobby,room}.md 오류 문구 표.
//
// 오류 코드 (ARCHITECTURE 결정 6):
//   ROOM_NOT_FOUND, WRONG_PASSWORD, ROOM_FULL, NICK_TAKEN, NICK_FORMAT, ROOM_NAME_FORMAT, PASSWORD_FORMAT,
//   TOO_MANY_ROOMS, RATE_LIMITED, NOT_MEMBER, TEXT_FORMAT, NETWORK, UNKNOWN
// 클라이언트 전용: MANIFEST(파츠 매니페스트 실패), STORAGE(프로필 저장 실패)

export const ERROR_CODES = Object.freeze([
  'ROOM_NOT_FOUND', 'WRONG_PASSWORD', 'ROOM_FULL', 'NICK_TAKEN', 'NICK_FORMAT', 'ROOM_NAME_FORMAT', 'PASSWORD_FORMAT',
  'TOO_MANY_ROOMS', 'RATE_LIMITED', 'NOT_MEMBER', 'TEXT_FORMAT', 'NETWORK', 'UNKNOWN',
]);
const KNOWN = new Set(ERROR_CODES);

export class AppError extends Error {
  constructor(code, detail) {
    super(code);
    this.name = 'AppError';
    this.code = KNOWN.has(code) ? code : 'UNKNOWN';
    this.detail = detail;
  }
}

export function toAppError(err, fallback = 'UNKNOWN') {
  if (err instanceof AppError) return err;
  if (err && typeof err.code === 'string' && KNOWN.has(err.code)) return new AppError(err.code, err);
  return new AppError(fallback, err);
}

const UNKNOWN_MSG = '문제가 생겼어요. 잠시 후 다시 시도해 주세요.';
const NICK_FORMAT_MSG = '2~12자의 한글, 영문, 숫자만 쓸 수 있어요.';

// profile.md 5~7장
export const PROFILE_MESSAGES = Object.freeze({
  HELP: '2~12자, 한글·영문·숫자만 쓸 수 있어요.',
  OK: '쓸 수 있는 형식이에요.',
  NICK_FORMAT: NICK_FORMAT_MSG,
  MANIFEST: '파츠 정보를 불러오지 못했어요. 새로고침해 주세요.',
  STORAGE: '프로필을 이 브라우저에 저장하지 못했어요. 새로고침하면 다시 만들어야 해요.',
  NOTE: '프로필은 이 브라우저에만 저장돼요',
});

// lobby.md 9장. NETWORK는 맥락마다 다르다 (입장 / 만들기 / 첫 로딩 / 갱신).
export const LOBBY_MESSAGES = Object.freeze({
  ROOM_NAME_FORMAT: '방 이름은 1~24자로 정해 주세요. 줄바꿈 같은 특수 문자는 쓸 수 없어요.',
  PASSWORD_FORMAT: '비밀번호는 4~32자로 정해 주세요.',
  TOO_MANY_ROOMS: '방은 동시에 3개까지 만들 수 있어요. 내가 만든 방이 비고 30분이 지나면 사라져요.',
  WRONG_PASSWORD: '비밀번호가 맞지 않아요. 다시 입력해 주세요.',
  RATE_LIMITED: '잠시 후 다시 시도해 주세요.',
  ROOM_FULL: '방이 가득 찼어요. 다른 방을 골라 주세요.',
  ROOM_NOT_FOUND: '방이 사라졌어요. 목록을 새로 고쳤어요.',
  NICK_TAKEN_TITLE: '닉네임이 겹쳐요',
  NICK_TAKEN_DESC: '이 방에 같은 닉네임이 있어요. 이 방에서만 쓸 닉네임을 정해 주세요. 프로필 닉네임은 그대로예요.',
  NICK_TAKEN_AGAIN: '이 닉네임도 이 방에 있어요. 다른 닉네임을 써 주세요.',
  NICK_FORMAT: NICK_FORMAT_MSG,
  NETWORK_JOIN: '연결이 불안정해요. 다시 시도해 주세요.',
  NETWORK_CREATE: '방을 만들지 못했어요. 연결을 확인하고 다시 시도해 주세요.',
  NETWORK_FIRST_TITLE: '방 목록을 불러오지 못했어요.',
  NETWORK_FIRST_TEXT: '인터넷 연결을 확인한 뒤 다시 시도해 주세요.',
  NETWORK_POLL: '연결이 불안정해요. 목록이 최신이 아닐 수 있어요.',
  UNKNOWN: UNKNOWN_MSG,
  REJOIN_FAILED: '방에 다시 들어가지 못했어요. 목록에서 다시 골라 주세요.',
  STORAGE: PROFILE_MESSAGES.STORAGE,
  EMPTY_TITLE: '아직 방이 없어요.',
  EMPTY_TEXT: '첫 방을 만들어 보세요.',
  LOADING: '방 목록을 불러오는 중이에요',
  LIMIT_NOTE: '방이 많아 100개까지만 보여요.',
  PW_HELP_EMPTY: '비워 두면 누구나 들어올 수 있는 공개 방이 돼요.',
  PW_HELP_SET: '비밀번호를 아는 사람만 들어올 수 있어요.',
});

// room.md 4.3 문구 표, 6~7장
export const ROOM_MESSAGES = Object.freeze({
  JOINING: '방에 들어가는 중...',
  LOG_LOADING: '대화를 불러오는 중이에요',
  HISTORY: (n) => `이전 대화 ${n}개`,
  HISTORY_FAILED: '이전 대화를 불러오지 못했어요.',
  JOINED: (nick) => `${nick}님이 들어왔어요`,
  LEFT: (nick) => `${nick}님이 나갔어요`,
  LOG_DISCONNECTED: '연결이 끊어졌어요',
  LOG_RECONNECTED: '다시 연결됐어요',
  NEW_MESSAGES: (n) => `새 메시지 ${n}개`,
  DISCONNECTED: '연결이 끊어졌어요. 다시 연결하는 중...',
  RECONNECT_FAILED: '연결하지 못했어요.',
  NOT_MEMBER: '방과 연결이 끊어졌어요. 로비에서 다시 들어와 주세요.',
  FATAL: '방에 들어갈 수 없어요. 다시 시도해 주세요.',
  SEND_FAILED: '메시지를 보내지 못했어요.',
  SEND_RATE_LIMITED: '잠시 후 다시 보내 주세요.',
  TEXT_FORMAT: '메시지는 1~80자로 보내 주세요.',
  LEAVING: '나가는 중',
  // v3 문구 그대로 유지 (design handoff 4.3 마지막 줄)
  COOLDOWN: '1초 뒤에 다시 보낼 수 있습니다.',
  HINT: '← → 또는 A D 이동 · Enter 채팅 · Esc 입력 해제',
});

/** 처리되지 않은 오류 토스트 */
export const GLOBAL_MESSAGE = UNKNOWN_MSG;
