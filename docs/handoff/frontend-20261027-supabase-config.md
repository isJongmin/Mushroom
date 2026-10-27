# frontend 2026-10-27: 실제 Supabase 연결 설정 + local 모드 강제 스위치

## 변경한 파일
| 파일 | 내용 |
|---|---|
| `src/client/config.js` | 실제 프로젝트 URL과 legacy anon 키(JWT payload `role: "anon"` 확인)를 채움. 주석: anon(공개) 키만, service_role 금지, 개발·QA는 `?mode=local` / `#local`로 local 강제, 해제 방법. 키·URL은 이 파일에만 있다. |
| `src/client/backend/index.js` | `selectedMode()`에 local 강제 스위치 추가. 페이지 로드당 1회 계산 후 캐시(hash 변경·화면 전환으로 모드가 바뀌지 않음). |
| `src/client/backend/supabase.js` | 코드 리뷰 수정 2건 (아래). |

## 모드 결정 규칙 (`backend/index.js`)
1. config의 URL 또는 anon 키가 비어 있으면 local.
2. 아래 중 하나라도 해당하면 local.
   - URL 쿼리 `mode=local` → 그 탭 sessionStorage `mushroom.mode` = `'local'` 저장(새로고침 유지).
   - sessionStorage `mushroom.mode` === `'local'`.
   - `location.hash`가 정확히 `#local` (`#localx`, `#local&x` 등은 해당 없음).
3. URL 쿼리 `mode=supabase` → sessionStorage 값 삭제(강제 해제). 같은 로드에 hash `#local`이 있으면 여전히 local.
4. 그 밖에는 supabase.
- 모드 배지: 기존 동작 그대로. local은 `LOCAL MODE` 칩 표시, supabase는 칩 텍스트 `SUPABASE MODE`이지만 기존 설계대로 숨김(`hidden`)이며 화면 슬롯에도 붙지 않는다. supabase 모드 표시가 필요하면 디자인 결정 필요(아래 요청).
- local 모드에서는 supabase.js와 CDN을 import하지 않는다(외부 요청 0건 확인).

## supabase 모드 코드 리뷰 (실서버 미연결, 코드 + 마이그레이션 대조)
| 항목 | 결과 |
|---|---|
| supabase-js 2.45.4 고정 CDN, `auth.signInAnonymously()` | OK. `getSession` → 없으면 익명 로그인. `persistSession`, `autoRefreshToken` 켜짐. |
| private 채널 구독 전 `realtime.setAuth` | OK. `connect()`에서 `sb.channel(...)` 생성 전에 `setAuth(access_token)`. 토큰 갱신(`TOKEN_REFRESHED`/`SIGNED_IN`) 때도 재설정. 채널 `config.private: true`. |
| RPC 이름·인자 | OK. `list_rooms()`, `create_room(p_name,p_password,p_nickname)` → uuid, `join_room(p_room_id,p_password,p_nickname)` → `'OK'`/`'WRONG_PASSWORD'`(반환값 → `WRONG_PASSWORD` 오류, 그 밖 값은 UNKNOWN), `leave_room(p_room_id)`, `heartbeat(p_room_id)`, `recent_messages(p_room_id)`, `send_message(p_room_id,p_text)` → jsonb. 마이그레이션 `20261015000000_rooms.sql` 시그니처·grant와 일치. |
| `error.message` 코드 매핑 | OK. `raise exception using message='<코드>'` → `error.message`가 ERROR_CODES에 있으면 그 코드, 네트워크(`Failed to fetch` 등, CDN 로드 실패) → NETWORK, 그 밖 UNKNOWN. |
| **수정 1** 인증 오류 감지 | postgrest-js 2.45는 HTTP 401을 `error`가 아니라 응답 `res.status`에 둔다. 기존 `err.status === 401` 검사는 항상 거짓이었다 → `isAuthError(res.error, res.status)`로 변경, 코드도 `PGRST301/302/303`, `42501`로 확장(PGRST303 = JWT 만료/클레임 실패). |
| **수정 2** 세션 복구 | 기존 재시도는 `ensureSession()`(= `getSession`)을 불렀는데, 서버가 거부한 토큰이 로컬 기준으로 유효하면 같은 토큰으로 재시도해 실패했다 → `recoverSession()`: `refreshSession()` 강제 갱신, 실패하면 `signInAnonymously()`(새 uid), `userId`와 `realtime.setAuth` 갱신 후 1회 재시도. |

## 검증 (python3 -m http.server + Playwright Chromium, 이 컨테이너는 supabase.co·CDN 차단)
| 경우 | 결과 |
|---|---|
| (a) 쿼리 없이 열기 (프로필 저장 상태) | `getState().mode === 'supabase'`, CDN 요청 시도 후 로비에 "방 목록을 불러오지 못했어요." 오류 화면, pageerror 0. |
| (b) `?mode=local` | LOCAL MODE 칩, 외부 요청 0, pageerror 0, sessionStorage 저장 → 쿼리 없이 새로고침해도 local 유지. |
| (b) `?mode=supabase` | sessionStorage 삭제, supabase 모드로 열림. |
| (b) `#local` | LOCAL MODE, 외부 요청 0, pageerror 0. `#localx`는 supabase. |
| (b) init script로 sessionStorage `mushroom.mode='local'` | LOCAL MODE, 외부 요청 0. |
| 참고: config를 비운 상태로 기존 e2e 실행 | PASS 30 / FAIL 1(35번, 모바일 B 라벨/말풍선 기록 없음 — 모드 스위치와 무관해 보임, 재실행 확인 필요) / UNVERIFIED 5 |

## (c) tests/e2e_local.py: 현재(config 채움) 깨지는 항목 — 테스트 파일은 수정하지 않음
결과: PASS 2 / FAIL 31 / UNVERIFIED 3.

| 항목 | 원인 | 필요한 수정 (QA) |
|---|---|---|
| 1~23, 27, 28, 32, 33, 35, 36 | 페이지가 supabase 모드로 열려 CDN 차단 → 로비 "목록 준비 안 됨 (현재 error)", 1번은 locator 타임아웃 | 모든 `page.goto` URL에 `mode=local` 추가(예: `f"{BASE}?mode=local&as={name}"`), 또는 각 context에 `ctx.add_init_script("sessionStorage.setItem('mushroom.mode','local')")`. init script 방식이 새 탭·새로고침·직접 goto 모두 덮어 빠짐이 적다. |
| 29 콘솔 에러 0건 | 위와 같은 원인으로 `net::ERR_TUNNEL_CONNECTION_FAILED` 수집 | 위 수정으로 해소 |
| 31 정적 점검: 클라이언트 | (1) "비밀 값 0건"이 `eyJ...` JWT 패턴으로 config.js의 anon 키를 잡음, (2) "config.js 키 비어 있음" 검사 | (1) JWT 패턴 검사에서 config.js의 `SUPABASE_ANON_KEY`는 제외하고, 대신 그 JWT payload를 base64 디코드해 `role == "anon"`인지 검사. (2) "키 비어 있음"을 "저장소 전체에 `service_role` 값/키 없음 + config.js의 키는 anon 역할 JWT만"으로 교체. |
| 12, 20 (이전 UNVERIFIED) | 모드 문제로 FAIL로 바뀜 | 위 수정 후 원래 상태로 복귀 예상 |
| 26, 34 PASS | 프로필 화면/정적 비교라 영향 없음 | - |
| 추가 권장 | 모드 스위치 회귀 | `?mode=local`/`#local`/sessionStorage/`?mode=supabase` 해제/`#localx` 비해당 케이스, local 모드 외부 요청 0건 검사 추가 |

## 다른 팀 요청
- 백엔드(사용자 대시보드 작업 포함): `20261015000000_rooms.sql` 적용 여부 확인, Authentication에서 "Allow anonymous sign-ins" 켜기, Realtime 설정에서 private 채널만 허용(Realtime Authorization) 확인. 실서버 연결 스모크 테스트는 외부망이 되는 환경에서 필요(이 컨테이너 불가).
- 디자인: supabase 모드에서 모드 칩을 숨기는 현재 동작 유지 여부 확인(메인 지시는 "기존 배지 그대로"로 이해해 변경하지 않음).
- 메인: 키를 저장소에 둘지 방침이 작업 중 두 번 바뀌었다(커밋 → 금지 → 승인). 최종 지시대로 config.js에 채워 두었으니 사용자 승인 여부만 확정해 주세요. 되돌리려면 config.js 마지막 두 줄을 `''`로 바꾸면 된다(나머지 코드는 그대로 동작).

## QA 확인 항목
1. 위 (c) 수정 적용 후 e2e 전체 통과(35번 재확인).
2. 모드 스위치 5케이스와 local 모드 외부 요청 0건.
3. 저장소에 service_role 키 없음, config.js 키는 anon 역할 JWT.
4. 외부망 환경에서 쿼리 없이 열었을 때 익명 로그인 → 로비 → 방 생성/입장/채팅 스모크(가능할 때).
