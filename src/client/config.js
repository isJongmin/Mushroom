// 버섯마을 실행 설정
//
// SUPABASE_URL      : Supabase 대시보드 > Project Settings > API 의 Project URL
// SUPABASE_ANON_KEY : 같은 화면의 legacy anon key (JWT, role = "anon"). service_role 키는 절대 쓰지 않는다.
//
// 저장소에는 두 값을 빈 문자열로 둔다. 배포 시 GitHub Actions가 저장소 Secrets(SUPABASE_URL, SUPABASE_ANON_KEY)로
// 아래 두 줄을 치환한다. 로컬에서 값을 넣었다면 커밋하지 말 것.
// 치환은 정규식으로 `export const SUPABASE_URL = '';` 줄과 `export const SUPABASE_ANON_KEY = '';` 줄을 바꾸므로
// 이 두 줄의 형식(작은따옴표, 공백, 세미콜론, 한 줄)을 그대로 유지한다.
//
// 주의: service_role(secret) 키는 RLS를 우회한다. 어떤 경우에도 이 파일이나 저장소에 넣지 않는다.
//
// 실행 모드 (backend/index.js selectedMode, 페이지 로드당 한 번 결정):
//   - supabase 모드: 두 값이 채워져 있고 local 강제 스위치가 꺼져 있을 때 (배포 사이트 기본).
//   - local 모드: 두 값 중 하나라도 비어 있거나(저장소 상태), 아래 스위치 중 하나라도 켜져 있을 때.
//     프로필/방/메시지는 localStorage, 실시간은 BroadcastChannel(같은 브라우저 탭끼리).
//     외부 네트워크(Supabase, CDN)에 전혀 접근하지 않는다. 개발·QA·데모용.
//
// local 모드 강제 (배포 사이트에서 데모, 외부망이 막힌 개발 환경, claude.ai 아티팩트 미리보기용):
//   1) URL 쿼리 `?mode=local`        예: index.html?mode=local&as=a
//      → 그 탭의 sessionStorage `mushroom.mode` = 'local'로 저장되어 새로고침해도 유지된다.
//   2) sessionStorage `mushroom.mode` = 'local' 을 직접 넣고 새로고침 (Playwright init script 등)
//   3) URL hash가 정확히 `#local`    예: index.html#local (아티팩트는 쿼리 없이 hash만 전달한다)
//   해제: URL 쿼리 `?mode=supabase` → 그 탭의 sessionStorage 값을 지운다(같은 로드에서 hash가 #local이면 여전히 local).
export const SUPABASE_URL = '';
export const SUPABASE_ANON_KEY = '';
