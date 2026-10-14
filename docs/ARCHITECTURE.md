# 아키텍처

## 디렉터리 구조
```
index.html       진입점 (GitHub Pages 루트에서 서빙) (frontend)
src/client/      프런트엔드 ES 모듈 (frontend)
supabase/        migrations/*.sql, 정책 (backend)
assets/          SVG 에셋 (art)
tests/           테스트 (qa)
docs/            문서
  design/        스타일 가이드, 화면 설계 (design)
  qa/            QA 결과 (qa)
  handoff/       역할 간 요청/결과 메모
```

## 확정된 결정 (2026-10-14)
1. 호스팅: GitHub Pages, 빌드 도구 없음. 브라우저 네이티브 ES 모듈만 사용.
2. 프런트: 바닐라 JS + Canvas 2D. 외부 라이브러리는 supabase-js 하나만, 버전 고정 CDN(`https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/+esm`)으로 로드.
3. 인증: Supabase Auth(email/password). 사용자가 입력한 아이디를 `<아이디>@mushroom.local`로 매핑한다.
   - 아이디 규칙: `^[a-z0-9_]{4,16}$`, 비밀번호 8자 이상.
   - Supabase 대시보드에서 "Confirm email"을 꺼야 한다(사용자 작업). 비밀번호 재설정 메일은 동작하지 않는다.
4. 실시간: Supabase Realtime 채널 `map:village`.
   - Presence: 접속자 목록. key = user_id, 상태 = `{ user_id, nickname, avatar, x, y }`.
   - Broadcast `move`: `{ user_id, x, y, dir }` — 송신 최대 10회/초로 제한.
   - Broadcast `chat`: `{ user_id, text }` — text 최대 80자, 저장하지 않음.
5. 실행 모드 두 가지 (src/client/config.js로 전환):
   - supabase 모드: `SUPABASE_URL`, `SUPABASE_ANON_KEY`가 채워진 경우.
   - local 모드: 값이 비어 있으면 자동 전환. 인증과 캐릭터는 localStorage, 실시간은 BroadcastChannel로 같은 브라우저의 탭끼리 동작. 개발·QA용.
   - 두 모드는 같은 인터페이스(`backend` 어댑터)를 구현한다: `signUp, signIn, signOut, getSession, getMyCharacter, createCharacter, isNicknameTaken, joinMap(handlers, self) → { sendMove, sendChat, leave }`.
   - move의 `dir` 값은 `'left' | 'right'`.

## 인터페이스 계약
- 아바타 데이터(`characters.avatar`, jsonb): `{ "skin": "<id>", "hair": "<id>", "eyes": "<id>", "top": "<id>", "bottom": "<id>" }`
- 에셋 경로: `assets/avatar/<part>/<id>.svg`. part 목록과 id 목록, 캔버스 크기, 기준점은 docs/design/style-guide.md가 정본이다.
- 맵 배경: `assets/map/background.svg`, viewBox `0 0 2400 540`로 월드 전체를 덮는다.
- 에셋 목록 매니페스트: `assets/avatar/manifest.json` — `{ "canvas": {"w":..,"h":..}, "anchor": {"x":..,"y":..}, "parts": { "<part>": [ {"id":"..","label":".."} ] }, "layerOrder": [..] }` (art 작성)

## 데이터 모델 (backend가 확정)
- characters: user_id (PK, auth.users 참조), nickname (unique), avatar (jsonb), created_at

## 알려진 한계 (MVP에서 수용)
- Broadcast 메시지에는 인증된 발신자 정보가 붙지 않는다. 악의적 클라이언트가 다른 user_id로 move/chat을 보낼 수 있다. 수신 측은 Presence에 없는 user_id 메시지를 버리는 것으로 완화하고, 근본 대응(서버 경유 또는 Realtime Authorization)은 후속 과제로 둔다.
- 위치는 서버가 검증하지 않는다 (몬스터 사냥 단계 전에 재설계).
