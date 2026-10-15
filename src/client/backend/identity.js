// local 모드 사용자 식별 (개발·QA 전용).
//
// 기본: 브라우저 프로필 단위 userId (localStorage `mushroom.local.v4.uid`) — 같은 브라우저의 모든 탭이 같은 사람.
// 테스트 훅: 탭마다 다른 사람을 흉내 내려면
//   1) URL에 `?as=<이름>` (영문/숫자/_/-, 1~32자)  예: index.html?as=a
//   2) 또는 sessionStorage `mushroom.local.as` = '<이름>' 을 넣고 새로고침
// URL 값은 그 탭의 sessionStorage에도 저장되어 새로고침 후에도 유지된다.
// `as`가 있으면 userId = `as-<이름 소문자>`, 프로필 키도 `mushroom:profile:as:<이름 소문자>`로 분리된다
// (같은 브라우저 컨텍스트의 두 탭이 서로 다른 닉네임/아바타를 갖게). supabase 모드에서는 쓰지 않는다.

const UID_KEY = 'mushroom.local.v4.uid';
const SS_AS = 'mushroom.local.as';
const AS_RE = /^[A-Za-z0-9_-]{1,32}$/;

let cached = null;

function randomId() {
  if (globalThis.crypto && crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hx = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${hx.slice(0, 8)}-${hx.slice(8, 12)}-${hx.slice(12, 16)}-${hx.slice(16, 20)}-${hx.slice(20)}`;
}

/** @returns {{ userId: string, as: string|null }} */
export function localIdentity() {
  if (cached) return cached;
  let as = null;
  try {
    const p = new URLSearchParams(location.search).get('as');
    if (p && AS_RE.test(p)) {
      as = p.toLowerCase();
      try { sessionStorage.setItem(SS_AS, as); } catch { /* 저장 불가: 이 로드에서만 */ }
    }
  } catch { /* location 접근 불가 */ }
  if (!as) {
    try {
      const s = sessionStorage.getItem(SS_AS);
      if (s && AS_RE.test(s)) as = s.toLowerCase();
    } catch { /* 무시 */ }
  }
  if (as) {
    cached = { userId: `as-${as}`, as };
    return cached;
  }
  let id = null;
  try { id = localStorage.getItem(UID_KEY); } catch { /* 무시 */ }
  if (!id || id.length > 64) {
    id = randomId();
    try { localStorage.setItem(UID_KEY, id); } catch { /* 저장 불가: 이 탭에서만 유효 */ }
  }
  cached = { userId: id, as: null };
  return cached;
}
