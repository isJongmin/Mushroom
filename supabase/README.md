# 버섯마을 Supabase 백엔드

정본 설계는 `docs/ARCHITECTURE.md`의 "확정된 결정"과 "인터페이스 계약"이다. 이 문서는 그 내용을 Supabase에 적용하는 방법과 프런트가 쓸 API를 정리한다.

## 마이그레이션 목록

| 파일 | 내용 |
|---|---|
| `migrations/20261014000000_characters.sql` | `public.characters` 테이블, 제약, RLS, 컬럼 권한, `is_nickname_taken` RPC |
| `migrations/20261014000100_realtime.sql` | 주석만 있음(no-op). Realtime에서 하지 않는 것과 후속 과제 기록 |

규칙: 이미 적용된 마이그레이션은 수정하지 않는다. 변경은 항상 새 타임스탬프 파일로 추가한다.

## 적용 순서

### A. 대시보드 SQL Editor 사용

1. Supabase 대시보드 > 프로젝트 > **SQL Editor** > New query.
2. `migrations/20261014000000_characters.sql` 전체를 붙여넣고 **Run**. 오류 없이 끝나야 한다.
3. `migrations/20261014000100_realtime.sql`은 주석뿐이라 실행하지 않아도 된다(실행해도 변화 없음).
4. 확인: **Table Editor**에 `characters`가 보이고 "RLS enabled" 표시가 있어야 한다. **Database > Functions**에 `is_nickname_taken`이 있어야 한다.

같은 파일을 두 번 실행하면 `relation "characters" already exists` 오류가 난다. 이것은 정상이며 이미 적용되었다는 뜻이다.

### B. supabase CLI 사용

```sh
# 저장소 루트에서 (최초 1회)
supabase init                                    # supabase/config.toml 생성. 기존 migrations/는 그대로 둔다
supabase login
supabase link --project-ref <프로젝트 ref>      # Project Settings > General 의 Reference ID

# 적용 (supabase/migrations/ 의 미적용 파일을 타임스탬프 순서로 실행)
supabase db push

# 확인
supabase migration list
```

`supabase init`이 만드는 `supabase/config.toml`(로컬 개발용 설정, 비밀 없음)의 커밋 여부는 메인이 결정한다.

## 대시보드에서 사용자가 할 설정

1. **Authentication > Providers(또는 Sign In / Providers) > Email**
   - Email provider: **Enabled**
   - **Confirm email: 끄기**. `<아이디>@mushroom.local`은 실제로 받을 수 없는 주소라서, 켜 두면 가입 후 로그인할 수 없다.
   - 비밀번호 최소 길이는 8 이상으로 설정 권장(프런트 규칙과 일치).
2. **Authentication > Rate Limits**
   - 가입/로그인 요청 제한 값을 확인한다. 같은 IP에서 QA가 짧은 시간에 여러 계정을 만들면 `429` / `over_request_rate_limit`이 날 수 있다. 테스트 중이면 일시적으로 올린다.
   - 이메일 발송 제한은 Confirm email을 끄면 가입에 영향이 없다.
3. **Realtime**: 이 단계에서는 별도 설정 없음(public channel 사용). Realtime Settings에서 "Allow public access"가 켜져 있어야 한다(기본값).

## 프런트가 쓸 값

| 값 | 위치 | 프런트에 넣어도 되나 |
|---|---|---|
| Project URL (`https://<ref>.supabase.co`) | Project Settings > API (또는 Data API) | 예 → `SUPABASE_URL` |
| anon / publishable key | Project Settings > API Keys | 예 → `SUPABASE_ANON_KEY` (RLS로 보호됨) |
| **service_role / secret key** | Project Settings > API Keys | **절대 안 됨.** 프런트 코드, `src/client/config.js`, 저장소, 이슈, 채팅 어디에도 넣지 않는다. RLS를 우회한다. |

## 프런트용 API 명세

supabase-js 2.45.4 (`https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm`) 기준.

### 1. 회원가입 / 로그인

```js
const email = `${id}@mushroom.local`;   // id: ^[a-z0-9_]{4,16}$ (프런트에서 검사)

// 가입 (Confirm email OFF이면 data.session이 바로 생김)
const { data, error } = await supabase.auth.signUp({ email, password });

// 로그인
const { data, error } = await supabase.auth.signInWithPassword({ email, password });

// 로그아웃 / 세션
await supabase.auth.signOut();
const { data: { session } } = await supabase.auth.getSession();
const uid = session?.user.id;
```

주요 Auth 오류 (`error.code`, supabase-js 2.45 기준):
- `user_already_exists` — 아이디 중복 (가입 시)
- `invalid_credentials` — 아이디/비밀번호 불일치 (로그인 시)
- `weak_password` — 비밀번호 정책 위반
- `over_request_rate_limit` (HTTP 429) — 요청 과다
- `email_not_confirmed` — Confirm email이 켜져 있음(대시보드 설정 확인)

### 2. 내 캐릭터 조회

```js
const { data, error } = await supabase
  .from('characters')
  .select('user_id,nickname,avatar')
  .eq('user_id', uid)
  .maybeSingle();
// data === null → 캐릭터 없음 → 캐릭터 생성 화면
```

### 3. 캐릭터 생성

```js
const { error } = await supabase
  .from('characters')
  .insert({ user_id: uid, nickname, avatar });   // created_at은 보내지 말 것(권한 없음)
```

- `avatar`: `{ skin, hair, eyes, top, bottom }` 5개 키만. 값은 `^[a-z0-9-]{1,32}$`. 그 외 키가 있으면 거부.
- `nickname`: `^[가-힣A-Za-z0-9]{2,12}$`. 대소문자 무시 중복 불가(`Mushroom`과 `mushroom`은 같은 닉네임).
- `upsert`는 쓰지 말 것(닉네임 update 권한이 없어 실패한다).

오류 처리 (`error.code`는 Postgres SQLSTATE 문자열, `error.message`에 제약 이름 포함):

| code | 의미 | 구분 방법 | 사용자 메시지 예 |
|---|---|---|---|
| `23505` | unique 위반 | `error.message`에 `characters_nickname_lower_key` 포함 → **닉네임 중복** | "이미 사용 중인 닉네임입니다" |
| `23505` | unique 위반 | `error.message`에 `characters_pkey` 포함 → **이미 캐릭터가 있음** | 내 캐릭터 다시 조회 후 맵으로 |
| `23514` | check 위반 | `characters_nickname_format` → 닉네임 형식, `characters_avatar_shape` → 아바타 형식 | 형식 안내 |
| `23502` | not null 위반 | nickname/avatar 누락 | 입력 확인 |
| `42501` | 권한/RLS 거부 | 다른 user_id로 insert, 미로그인, created_at 지정 등 | 다시 로그인 |

```js
if (error?.code === '23505') {
  if (error.message.includes('characters_nickname_lower_key')) { /* 닉네임 중복 */ }
  else if (error.message.includes('characters_pkey'))         { /* 캐릭터 이미 존재 */ }
}
```

동시 생성 race: 두 사용자가 같은 닉네임으로 동시에 생성하면 unique 인덱스가 한 명만 통과시키고 다른 쪽은 `23505`(`characters_nickname_lower_key`)를 받는다. 사전 확인(RPC)이 `false`였어도 insert에서 `23505`가 날 수 있으므로 **insert 오류 처리가 최종 판정**이다.

### 4. 닉네임 중복 확인 (UX용 사전 확인)

```js
const { data: taken, error } = await supabase.rpc('is_nickname_taken', { p_nickname: nickname });
// taken: true | false  (대소문자 무시)
```

로그인(authenticated) 상태에서만 호출 가능. 미로그인(anon)이면 `42501`.

### 5. 아바타 변경 (현재 UI 범위 밖, 허용만 되어 있음)

```js
await supabase.from('characters').update({ avatar }).eq('user_id', uid);
```

`nickname`, `user_id`, `created_at`을 update에 포함하면 `42501`로 전체 요청이 거부된다. 다른 사람 행을 대상으로 하면 오류 없이 0행이 변경된다(RLS). 변경 여부를 확인하려면 `.select()`를 붙여 반환 행 수를 본다.

### 6. 다른 플레이어 정보

로그인 사용자는 `characters`의 모든 행(`user_id, nickname, avatar, created_at`)을 조회할 수 있다. 다만 맵 표시에는 Presence 상태를 사용한다(아래).

### 7. Realtime 채널 `map:village`

ARCHITECTURE.md "확정된 결정 4"를 그대로 옮긴 것이다.

- 채널: `supabase.channel('map:village', { config: { presence: { key: uid } } })` — public channel (`private` 지정 안 함). DB 변경 구독(Postgres Changes)은 사용하지 않는다.
- **Presence** — 접속자 목록
  - key = `user_id`
  - 상태 = `{ user_id, nickname, avatar, x, y }`
  - 입장 시 `channel.track(state)`, 퇴장 시 `channel.untrack()` / `removeChannel`.
- **Broadcast `move`** — `{ user_id, x, y, dir }`
  - 송신 최대 10회/초 (프런트에서 throttle).
- **Broadcast `chat`** — `{ user_id, text }`
  - `text` 최대 80자 (송신 전 자르기, 수신 측도 80자 초과 시 자르거나 버림).
  - 저장하지 않는다.
- 수신 측 규칙: **Presence에 없는 `user_id`의 move/chat은 버린다**(발신자 위조 완화).

```js
const ch = supabase.channel('map:village', { config: { presence: { key: uid } } });
ch.on('presence', { event: 'sync' }, () => { const state = ch.presenceState(); /* ... */ })
  .on('broadcast', { event: 'move' }, ({ payload }) => { /* {user_id,x,y,dir} */ })
  .on('broadcast', { event: 'chat' }, ({ payload }) => { /* {user_id,text} */ })
  .subscribe(async (status) => {
    if (status === 'SUBSCRIBED') await ch.track({ user_id: uid, nickname, avatar, x, y });
  });
ch.send({ type: 'broadcast', event: 'move', payload: { user_id: uid, x, y, dir } });
```

## 테이블 요약

`public.characters`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| `user_id` | uuid | PK(`characters_pkey`), `auth.users(id)` 참조, on delete cascade |
| `nickname` | text | not null, check `characters_nickname_format`, unique index `characters_nickname_lower_key` on `lower(nickname)` |
| `avatar` | jsonb | not null, check `characters_avatar_shape` |
| `created_at` | timestamptz | not null default now() |

권한 (anon은 테이블/RPC 권한 없음):

| 역할 | select | insert | update | delete | RPC |
|---|---|---|---|---|---|
| anon | X | X | X | X | X |
| authenticated | 모든 행 (RLS `using true`) | 본인 user_id만, 컬럼 user_id/nickname/avatar | 본인 행만, **avatar 컬럼만** | X | `is_nickname_taken` |

닉네임 변경 불가는 트리거가 아니라 **컬럼 권한**(`grant update (avatar)`)으로 강제한다. 이유는 마이그레이션 주석 참고(파싱 단계에서 거부되어 트리거 버그·누락 위험이 없고 user_id/created_at 변경도 함께 막힘). service_role/postgres는 제한을 받지 않으므로 관리자 변경은 가능하다.

## 알려진 한계

1. **Broadcast 발신자 위조**: public channel이고 payload의 `user_id`는 클라이언트가 넣는다. 악의적 클라이언트는 다른 사용자인 척 move/chat을 보낼 수 있고, Presence key도 임의로 지정할 수 있다. anon key만 있으면 로그인 없이도 채널 접속이 가능하다. 완화책은 "Presence에 없는 user_id 무시"뿐이다. 후속 과제: private channel + `realtime.messages` RLS(채널 접근 제한), 근본적으로는 서버 경유 송신. 초안은 `migrations/20261014000100_realtime.sql` 주석 참고.
2. **Presence 상태의 nickname/avatar 위조**: Presence 상태는 DB 값과 대조되지 않는다. 필요하면 수신 측이 `characters`를 조회해 user_id 기준으로 덮어쓴다.
3. **위치/이동 속도 검증 없음**: 서버가 x, y, dir을 검증하지 않는다.
4. **채팅 필터링/저장 없음**: 80자 제한은 클라이언트 규칙일 뿐이며 서버가 강제하지 않는다. 욕설 필터, 신고, 기록 없음.
5. **닉네임/아이디 존재 여부 노출**: 로그인 사용자는 `is_nickname_taken`과 `characters` 조회로 닉네임 존재 여부를 알 수 있다(의도된 동작). Auth의 `user_already_exists`로 아이디 존재 여부도 알 수 있다.
6. **비밀번호 재설정 불가**: `@mushroom.local` 메일은 수신 불가. 분실 시 관리자가 대시보드에서 처리.
7. **닉네임 변경 불가**: 사용자 경로로는 불가. 관리자만 SQL로 변경 가능.
8. **아바타 파트 id의 존재 여부는 DB가 검증하지 않는다**: 형식(`^[a-z0-9-]{1,32}$`)만 검사한다. 매니페스트에 없는 id는 프런트가 기본값으로 대체해 그린다. 파트 종류(키)가 늘어나면 새 마이그레이션으로 `characters_avatar_shape`를 교체해야 한다.
9. **한글 닉네임 범위**: 완성형 `가-힣`만 허용. 자모 단독(ㄱ, ㅏ), 공백, 밑줄, 이모지는 거부된다. 대소문자 무시는 영문에만 의미가 있다.
