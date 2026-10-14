// config.js 값으로 어댑터를 고른다. local 모드에서는 supabase.js(와 CDN)를 절대 로드하지 않는다.
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '../config.js';

export function selectedMode() {
  const url = typeof SUPABASE_URL === 'string' ? SUPABASE_URL.trim() : '';
  const key = typeof SUPABASE_ANON_KEY === 'string' ? SUPABASE_ANON_KEY.trim() : '';
  return url && key ? 'supabase' : 'local';
}

export async function createBackend() {
  if (selectedMode() === 'supabase') {
    const { createSupabaseBackend } = await import('./supabase.js');
    return createSupabaseBackend(SUPABASE_URL.trim(), SUPABASE_ANON_KEY.trim());
  }
  const { createLocalBackend } = await import('./local.js');
  return createLocalBackend();
}
