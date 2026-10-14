# backend → main: characters 스키마 / RLS / Realtime 명세 (2026-10-14)

## 변경 파일
- `supabase/migrations/20261014000000_characters.sql` — 신규. characters 테이블, 제약, RLS, 컬럼 권한, `is_nickname_taken` RPC
- `supabase/migrations/20261014000100_realtime.sql` — 신규. 주석만(no-op). Realtime에서 하지 않는 것 + 후속 과제(private channel, realtime.messages RLS 초안)
- `supabase/README.md` — 신규. 적용 순서(SQL Editor / CLI), 대시보드 설정, 키 취급, 프런트 API 명세, 알려진 한계
- 그 밖의 파일은 수정하지 않음. 커밋하지 않음.

## 사용자(메인 경유) 작업 필요
1. Supabase 프로젝트 생성 후 `20261014000000_characters.sql`을 SQL Editor에서 실행(또는 `supabase db push`).
2. Authentication > Providers > Email: **Confirm email 끄기**. Rate limit 확인(QA 대량 가입 시 429 가능).
3. Project URL과 anon key를 프런트 `src/client/config.js`에 입력. **service_role key는 절대 넣지 않음.**

## 테이블 요약 `public.characters`
| 컬럼 | 타입 | 제약 |
|---|---|---|
| user_id | uuid | PK `characters_pkey` (계정당 1개), → auth.users(id) on delete cascade |
| nickname | text | not null, check `characters_nickname_format` `^[가-힣A-Za-z0-9]{2,12}$`, unique index `characters_nickname_lower_key` on lower(nickname) |
| avatar | jsonb | not null, check `characters_avatar_shape`: object, 키 skin/hair/eyes/top/bottom 정확히 5개, 각 값 string `^[a-z0-9-]{1,32}$` |
| created_at | timestamptz | not null default now() |

권한/RLS:
- anon: 테이블, RPC 모두 권한 없음(Supabase 기본 grant를 revoke).
- authenticated: select(모든 행, 4개 컬럼) / insert(본인 user_id만; 컬럼 user_id, nickname, avatar) / update(본인 행만; **avatar 컬럼만**) / delete 없음.
- 닉네임 변경 불가는 **컬럼 권한**으로 강제(트리거 아님). 파싱 단계에서 42501로 거부되므로 트리거 누락·버그 위험이 없고 user_id/created_at 변경도 함께 막힌다. 관리자(service_role)는 변경 가능.
- RPC `public.is_nickname_taken(p_nickname text) returns boolean`: security definer, `search_path = ''`, lower 비교, authenticated만 execute.

## 프런트용 API 요약 (상세: supabase/README.md)
- 가입/로그인: `auth.signUp` / `auth.signInWithPassword`, email = `${id}@mushroom.local`
- 내 캐릭터: `from('characters').select('user_id,nickname,avatar').eq('user_id', uid).maybeSingle()` → null이면 생성 화면
- 생성: `from('characters').insert({ user_id: uid, nickname, avatar })` — created_at 보내지 말 것, upsert 쓰지 말 것
- 닉네임 확인: `rpc('is_nickname_taken', { p_nickname })` → boolean (UX용, 최종 판정은 insert 결과)
- Realtime `map:village`: Presence(key=user_id, `{user_id,nickname,avatar,x,y}`), Broadcast `move` `{user_id,x,y,dir}` ≤10회/초, `chat` `{user_id,text}` ≤80자·비저장. public channel, Postgres Changes 미사용. Presence에 없는 user_id 메시지는 버림.

## 에러 코드 처리 (insert)
| error.code | error.message에 포함 | 의미 |
|---|---|---|
| 23505 | `characters_nickname_lower_key` | 닉네임 중복(대소문자 무시). 동시 생성 race에서 진 쪽도 이것 |
| 23505 | `characters_pkey` | 이미 캐릭터 있음 → 재조회 후 맵으로 |
| 23514 | `characters_nickname_format` / `characters_avatar_shape` | 형식 위반 |
| 23502 | — | nickname/avatar 누락 |
| 42501 | `row-level security` 또는 `permission denied` | 다른 user_id, 미로그인, 허용되지 않은 컬럼(created_at, nickname update 등) |

## QA 확인 항목
정상 경로
1. 가입 → 즉시 세션 발급(Confirm email OFF) → 캐릭터 없음(null) → 생성 → 재로그인 시 같은 캐릭터 조회.
2. 한글/영문/숫자 혼합 닉네임 2자, 12자 생성 성공.
3. `is_nickname_taken`: 기존 닉네임의 대소문자 변형도 true.

제약
4. 같은 닉네임 대소문자만 다르게 → 23505 `characters_nickname_lower_key`.
5. 이미 캐릭터 있는 계정으로 두 번째 생성 → 23505 `characters_pkey`.
6. 닉네임 1자, 13자, 공백, `_`, 특수문자, 자모 단독(ㄱㄴ), 이모지 → 23514.
7. avatar: 키 누락, 추가 키, 값 숫자/null/대문자/빈 문자열/33자, 배열·문자열 등 비객체 → 23514.
8. 두 브라우저에서 같은 닉네임 동시 생성 → 정확히 한 명만 성공, 다른 쪽 23505.

권한 우회 시도
9. 로그인 상태에서 `insert({ user_id: <다른 사람 uid>, ... })` → 42501.
10. `update({ nickname: 'X' }).eq('user_id', uid)` (본인) → 42501.
11. `update({ user_id: ... })`, `update({ created_at: ... })` → 42501.
12. `update({ avatar }).eq('user_id', <다른 사람 uid>)` → 오류 없이 0행, 상대 행 불변(`.select()` 결과 빈 배열).
13. `delete().eq('user_id', uid)` → 42501, 행 유지.
14. `insert({ ..., created_at: '2000-01-01' })` → 42501.
15. `upsert(...)` → 실패(42501).
16. 로그아웃(anon key만) 상태에서 `from('characters').select()` → 42501(permission denied), `rpc('is_nickname_taken')` → 42501.
17. REST 직접 호출(curl, anon key + 다른 사용자 JWT 없이)로 위 9~16 재현.
18. Realtime(알려진 한계 확인용): 다른 user_id로 move/chat broadcast 송신 시 수신 측이 Presence에 없는 id는 무시하는지. Presence에 있는 다른 사람 id로 위조하면 통과됨(현재 한계, 결함으로 보고하지 말고 한계로 기록).
19. chat 81자 이상 송신 시 수신 측 처리(자르기/버림)는 프런트 영역.

## 검증 결과
환경: npm 레지스트리가 조직 egress 정책으로 차단(403)되어 PGlite는 설치 불가. 대신 컨테이너에 있는 **PostgreSQL 16.15**로 일회용 클러스터를 띄워 검증. Supabase 환경 스텁: 역할 anon/authenticated/service_role, `auth` 스키마, `auth.users`, `auth.uid()`(request.jwt.claims의 sub), Supabase의 public 스키마 default privileges(anon/authenticated에 전체 grant) 재현. 검증 스크립트는 저장소 밖 스크래치 디렉터리에 둠.

- 두 마이그레이션 모두 `ON_ERROR_STOP`으로 오류 없이 적용: **통과**
- 자동 테스트 49건: **49 통과 / 0 실패**
  - 정상 insert(영문, 한글), 같은 user_id 두 번째 insert 23505 pkey, 대소문자 다른 닉네임 23505 lower_key
  - 닉네임 형식 위반 6종 23514, avatar 형식 위반 10종 23514, null 23502
  - 다른 user_id insert RLS 42501, sub 없는 insert 42501, created_at insert 42501
  - 본인 avatar update 성공, nickname/user_id update 42501, 타인 행 update 0행·불변, delete 42501
  - anon select/insert/RPC 42501
  - RPC 대소문자 무시 동작, security definer, search_path='', PUBLIC execute 없음
  - auth.users 삭제 시 cascade
- 동시 생성 race(두 세션, 같은 닉네임 대소문자 다름): 후행 세션이 선행 커밋까지 대기 후 23505 `characters_nickname_lower_key`: **통과**
- 검증 중 발견·수정한 결함: avatar check에서 키가 없으면 `jsonb_typeof()`가 NULL → CHECK가 통과하던 문제. `coalesce(..., false)` + `?&` 키 존재 검사로 수정 후 재검증 통과.
- **미검증**: 실제 Supabase(PG 15/17, 실제 auth.uid(), PostgREST 경유 오류 형식 `error.code`/`error.message`), Realtime 동작, Auth 설정. 실제 프로젝트 생성 후 QA 항목 9~17을 supabase-js/REST로 재확인 필요.
