// 버섯마을 실행 설정
//
// SUPABASE_URL      : Supabase 대시보드 > Project Settings > API 의 Project URL
// SUPABASE_ANON_KEY : 같은 화면의 legacy anon key (JWT, role = "anon").
//
// anon(공개) 키만 넣는다. 데이터는 RLS와 security definer RPC로만 접근되므로 프런트와 저장소에 넣어도 된다.
// service_role(secret) 키는 RLS를 우회하므로 절대 넣지 않는다.
// 개발·QA(외부망이 막힌 환경 포함)는 ?mode=local 또는 #local 로 local 모드를 강제한다 (아래 참고).
//
// 실행 모드 (backend/index.js selectedMode, 페이지 로드당 한 번 결정):
//   - supabase 모드: 두 값이 채워져 있고 local 강제 스위치가 꺼져 있을 때 (기본).
//   - local 모드: 두 값 중 하나라도 비어 있거나, 아래 스위치 중 하나라도 켜져 있을 때.
//     프로필/방/메시지는 localStorage, 실시간은 BroadcastChannel(같은 브라우저 탭끼리).
//     외부 네트워크(Supabase, CDN)에 전혀 접근하지 않는다. 개발·QA·데모용.
//
// local 모드 강제 (배포 사이트에서 데모, 외부망이 막힌 개발 환경, claude.ai 아티팩트 미리보기용):
//   1) URL 쿼리 `?mode=local`        예: index.html?mode=local&as=a
//      → 그 탭의 sessionStorage `mushroom.mode` = 'local'로 저장되어 새로고침해도 유지된다.
//   2) sessionStorage `mushroom.mode` = 'local' 을 직접 넣고 새로고침 (Playwright init script 등)
//   3) URL hash가 정확히 `#local`    예: index.html#local (아티팩트는 쿼리 없이 hash만 전달한다)
//   해제: URL 쿼리 `?mode=supabase` → 그 탭의 sessionStorage 값을 지운다(같은 로드에서 hash가 #local이면 여전히 local).
export const SUPABASE_URL = 'https://crxnvrntkwhdwxzhujva.supabase.co';
export const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNyeG52cm50a3doZHd4emh1anZhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMwNzk0NDQsImV4cCI6MjEwODY1NTQ0NH0.kD3RJNhnUZiv_yv3WLZwsWR-n0qoSGRT-6sCfZzHlyQ';
