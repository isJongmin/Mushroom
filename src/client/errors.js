// 어댑터는 항상 AppError(code)를 던진다. 화면은 code를 화면별 문구로 바꾼다.
// 문구는 docs/design/screens/*.md의 "오류 문구" 표를 그대로 쓴다.

export class AppError extends Error {
  constructor(code, detail) {
    super(code);
    this.name = 'AppError';
    this.code = code;
    this.detail = detail;
  }
}

export const LOGIN_MESSAGES = Object.freeze({
  ID_FORMAT: '아이디는 영문 소문자, 숫자, 밑줄(_)을 사용해 4~16자로 입력하세요.',
  PW_SHORT: '비밀번호는 8자 이상 입력하세요.',
  PW_MISMATCH: '비밀번호가 일치하지 않습니다.',
  ID_TAKEN: '이미 사용 중인 아이디입니다.',
  LOGIN_FAILED: '아이디 또는 비밀번호가 올바르지 않습니다.',
  NETWORK: '연결에 문제가 있습니다. 인터넷 연결을 확인한 뒤 다시 시도하세요.',
  SERVER: '문제가 발생했습니다. 잠시 후 다시 시도하세요.',
});

export const CREATE_MESSAGES = Object.freeze({
  HELP: '2~12자, 한글, 영문, 숫자만 사용할 수 있습니다.',
  UNCHECKED: '중복 확인이 필요합니다.',
  NICK_FORMAT: '2~12자의 한글, 영문, 숫자만 사용할 수 있습니다.',
  CHECKING: '확인 중...',
  AVAILABLE: '사용할 수 있는 닉네임입니다.',
  NICK_TAKEN: '이미 사용 중인 닉네임입니다.',
  NICK_CHECK_FAILED: '닉네임 확인에 실패했습니다. 다시 시도하세요.',
  NETWORK: '캐릭터를 만들지 못했습니다. 연결을 확인한 뒤 다시 시도하세요.',
  SERVER: '캐릭터를 만들지 못했습니다. 잠시 후 다시 시도하세요.',
});

export const GAME_MESSAGES = Object.freeze({
  JOINING: '마을에 들어가는 중...',
  DISCONNECTED: '연결이 끊어졌습니다. 다시 연결하는 중...',
  RECONNECT_FAILED: '연결하지 못했습니다.',
  FATAL: '마을에 들어갈 수 없습니다. 다시 시도하세요.',
  COOLDOWN: '1초 뒤에 다시 보낼 수 있습니다.',
  SEND_FAILED: '메시지를 보내지 못했습니다.',
});

export function toAppError(err, fallback = 'SERVER') {
  if (err instanceof AppError) return err;
  return new AppError(fallback, err);
}

/** 오류 코드 → 지정한 문구 표의 문구. 표에 없으면 SERVER 문구. */
export function messageFor(table, err) {
  const code = err && err.code;
  return (code && table[code]) || table.SERVER;
}
