// 버섯마을 실행 설정
//
// SUPABASE_URL      : Supabase 대시보드 > Project Settings > API 의 Project URL (https://<ref>.supabase.co)
// SUPABASE_ANON_KEY : 같은 화면의 anon(publishable) key. RLS로 보호되므로 프런트에 넣어도 된다.
//
// 두 값이 모두 채워져 있으면 supabase 모드, 하나라도 비어 있으면 local 모드로 동작한다.
//   - local 모드: 인증/캐릭터는 브라우저 localStorage, 실시간은 BroadcastChannel(같은 브라우저 탭끼리).
//     개발·QA 전용이다. 외부 네트워크(CDN 포함)에 전혀 접근하지 않는다.
//
// 주의: service_role(secret) 키는 RLS를 우회한다. 어떤 경우에도 이 파일이나 저장소에 넣지 않는다.
export const SUPABASE_URL = '';
export const SUPABASE_ANON_KEY = '';
