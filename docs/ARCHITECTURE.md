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
- 아바타 데이터(`characters.avatar`, jsonb): `{ "skin": "<id>", "hair": "<id>", "eyes": "<id>", "top": "<id>", "bottom": "<id>" }` (DB 스키마 변경 없음)

### 픽셀아트 계약 (2026-10-14 사이클 2, SVG 벡터 방식 폐기)
- 스타일: 메이플스토리풍 픽셀아트. 안티에일리어싱 없음. 렌더 시 `imageSmoothingEnabled = false`, CSS `image-rendering: pixelated`.
- 배율: 아트 1px = 월드 2단위 (데스크톱 2배 표시). 월드 좌표계 2400x540, 지면 y=440은 유지. 아트 좌표로는 1200x270.
- 아바타 프레임: 32x48 px. 기준점(발 중앙) (16, 46). 기본 방향은 오른쪽, 왼쪽은 x=16 기준 좌우 반전.
- 프레임 순서(가로 한 줄 시트, 6프레임, 192x48): `idle0, idle1, walk0, walk1, walk2, walk3`.
  - idle: 프레임당 500ms. walk: 프레임당 120ms.
  - 모든 파츠가 같은 프레임 순서와 프레임별 움직임(몸 상하 흔들림, 팔·다리 위치)을 공유해야 레이어가 맞는다. 프레임별 몸통 오프셋 표는 style-guide에 정의한다.
- 아바타 파츠 시트: `assets/avatar/<part>/<id>.png` (part = skin, bottom, top, eyes, hair).
- 매니페스트 `assets/avatar/manifest.json`:
  `{ "frame": {"w":32,"h":48}, "anchor": {"x":16,"y":46}, "scale": 2, "layerOrder": ["skin","bottom","top","eyes","hair"], "animations": { "idle": {"frames":[0,1], "ms":500}, "walk": {"frames":[2,3,4,5], "ms":120} }, "parts": { "<part>": [ {"id":"..","label":".."} ] } }` — 각 part 배열의 첫 항목이 기본값.
- 맵: `assets/map/manifest.json`이 레이어를 정의한다.
  `{ "scale": 2, "layers": [ {"src":"assets/map/<file>.png", "parallax": 0.0~1.0, "y": <아트 px>, "repeatX": true|false } ] }` — 앞에 올수록 뒤에 그린다. parallax 1.0은 월드와 같이 움직임.
- UI 스킨: `assets/ui/` 9-slice PNG. 버튼 등 상태가 있는 요소는 상태별 개별 파일(CSS border-image 사용을 위해). 파일 목록과 slice 값은 style-guide와 `assets/ui/manifest.json`.
- 표시 배율 P는 정수만: 기본 2, 1600x900 이상 화면 3. 시야는 화면 크기에 따라 가변, 카메라는 화면 아래 끝 고정(style-guide 정본). 월드 밖 상단은 하늘색으로 채운다.
- 사이클 1 아바타 id 호환: 목록에 없는 id는 style-guide의 매핑 또는 기본값으로 그린다. DB 저장값은 바꾸지 않는다.
- 원본: `assets/_src/` 에 Python(Pillow) 생성 스크립트와 픽셀 데이터. `python3 assets/_src/build.py`로 모든 PNG 재생성.
- 텍스트(닉네임, 말풍선, UI)는 화면 해상도에서 시스템 폰트로 선명하게 그린다. 픽셀 한글 폰트(Galmuri, OFL)는 후속 과제(개발 환경에서 다운로드 불가).

## 데이터 모델 (backend가 확정)
- characters: user_id (PK, auth.users 참조), nickname (unique), avatar (jsonb), created_at

## 알려진 한계 (MVP에서 수용)
- Broadcast 메시지에는 인증된 발신자 정보가 붙지 않는다. 악의적 클라이언트가 다른 user_id로 move/chat을 보낼 수 있다. 수신 측은 Presence에 없는 user_id 메시지를 버리는 것으로 완화하고, 근본 대응(서버 경유 또는 Realtime Authorization)은 후속 과제로 둔다.
- 위치는 서버가 검증하지 않는다 (몬스터 사냥 단계 전에 재설계).
