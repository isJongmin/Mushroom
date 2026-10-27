// 실행 모드를 정하고 어댑터를 고른다. local 모드에서는 supabase.js(와 CDN)를 절대 로드하지 않는다.
//
// 모드 결정 (config.js 주석 참고):
//   1) config.js의 URL 또는 anon key가 비어 있으면 local
//   2) local 강제 스위치 중 하나라도 켜져 있으면 local
//        - URL 쿼리 mode=local (그 탭의 sessionStorage `mushroom.mode` = 'local' 저장 → 새로고침 유지)
//        - sessionStorage `mushroom.mode` === 'local'
//        - URL hash가 정확히 '#local'
//      URL 쿼리 mode=supabase 는 sessionStorage 값을 지워 강제를 해제한다.
//   3) 그 밖에는 supabase
// 결과는 페이지 로드당 한 번만 계산한다(화면 전환이나 hash 변경으로 모드가 바뀌지 않게).
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '../config.js';

const SS_MODE = 'mushroom.mode';
let cachedMode = null;

function localForced() {
  let q = null;
  let hash = '';
  try {
    q = new URLSearchParams(location.search).get('mode');
    hash = location.hash || '';
  } catch { /* location 접근 불가 */ }

  if (q === 'local') {
    try { sessionStorage.setItem(SS_MODE, 'local'); } catch { /* 저장 불가: 이 로드에서만 */ }
    return true;
  }
  if (q === 'supabase') {
    try { sessionStorage.removeItem(SS_MODE); } catch { /* 무시 */ }
  } else {
    try {
      if (sessionStorage.getItem(SS_MODE) === 'local') return true;
    } catch { /* sessionStorage 차단 */ }
  }
  return hash === '#local';
}

export function selectedMode() {
  if (cachedMode) return cachedMode;
  const url = typeof SUPABASE_URL === 'string' ? SUPABASE_URL.trim() : '';
  const key = typeof SUPABASE_ANON_KEY === 'string' ? SUPABASE_ANON_KEY.trim() : '';
  cachedMode = !url || !key || localForced() ? 'local' : 'supabase';
  return cachedMode;
}

export async function createBackend() {
  if (selectedMode() === 'supabase') {
    const { createSupabaseBackend } = await import('./supabase.js');
    return createSupabaseBackend(SUPABASE_URL.trim(), SUPABASE_ANON_KEY.trim());
  }
  const { createLocalBackend } = await import('./local.js');
  return createLocalBackend();
}
