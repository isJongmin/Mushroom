# 아키텍처

## 디렉터리 구조
```
index.html       진입점 (GitHub Pages 루트에서 서빙) (frontend)
src/client/      프런트엔드 ES 모듈 (frontend)
supabase/        migrations/*.sql, 정책 (backend)
assets/          블록 아트 PNG + _src 생성 스크립트 (art)
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
- 아바타 데이터(`characters.avatar`, jsonb, 사이클 3부터): `{ "skin", "hair", "face", "top", "bottom", "shoes", "hat" }` 7개 키, 값은 파츠 id 문자열. `hat`은 `"none"` 허용. (사이클 1~2의 `eyes` 키는 `face`로 대체. backend 마이그레이션으로 변환)
- 표시 시 manifest에 없는 id는 해당 파츠의 기본값(첫 항목)으로 그린다.

### 블록 아트 계약 (2026-10-14 사이클 3 — 마인크래프트풍 블록 스타일, 이전 픽셀아트 계약 폐기)
- 스타일: 모든 사물을 상자로 보고 윗면(밝게)/정면(기본)/옆면(어둡게) 3면 톤으로 그리는 블록 픽셀아트. 사선 투영(위·오른쪽에서 본 3/4). 안티에일리어싱 없음.
- 렌더: `imageSmoothingEnabled = false`, CSS `image-rendering: pixelated`. 아트 1px = 월드 2단위. 표시 배율은 정수만(기본 2, 1600x900 이상 화면 3).
- 월드: 2400x540 월드 단위 = 아트 1200x270. 지면선 아트 y=220 (월드 440). 잔디 타일 윗면 첫 행 = 218.
- 아바타 프레임: 48x64. 기준점 (24, 60) = 두 발 사이 바닥 중앙. 지면선 y에 서면 프레임 왼쪽 위 = (x-24, y-60).
- 시트: 가로 한 줄 7프레임 336x64, 순서 `front, side_idle, side_walk0, side_walk1, side_walk2, side_walk3, back` (프레임 i의 x = 48i).
  - 인게임: side_idle / side_walk(150ms/프레임). 기본 오른쪽, 왼쪽은 x=24 기준 좌우 반전.
  - front/back: 캐릭터 생성 미리보기 회전용.
- 레이어(합성 순서): `hair_back → skin → face → bottom → shoes → top → hair_front → hat`.
  - 파일: `assets/avatar/<layer>/<id>.png`. hair id 하나가 `hair_back/<id>.png`와 `hair_front/<id>.png` 두 파일을 가진다(뒷부분이 없으면 hair_back 파일은 완전 투명 시트). `hat/none`은 파일 없음.
- 외곽선: 레이어 PNG는 외곽선 없이 납품. 프런트가 합성 후 바깥 실루엣 1px 외곽선을 그린다: 투명 픽셀 중 4방향(아래, 왼쪽, 오른쪽, 위 순) 이웃에 불투명 픽셀이 있으면 그 이웃 색을 `assets/avatar/outline.json`(`{ "#RRGGBB": "#RRGGBB" }`, 팔레트 색 → line 색)로 매핑한 색으로 칠한다. 매핑에 없으면 RGB 각 성분 x0.45. 결과는 외형 조합당 1회 계산해 캐시. 프레임 경계 안에서 처리(기준점 여백 확보됨).
- 매니페스트 `assets/avatar/manifest.json`:
  `{ "frame":{"w":48,"h":64}, "anchor":{"x":24,"y":60}, "scale":2, "frames":["front","side_idle","side_walk0","side_walk1","side_walk2","side_walk3","back"], "animations":{"idle":{"frames":[1],"ms":500},"walk":{"frames":[2,3,4,5],"ms":150}}, "layerOrder":["hair_back","skin","face","bottom","shoes","top","hair_front","hat"], "parts":{ "skin":[..], "hair":[..], "face":[..], "top":[..], "bottom":[..], "shoes":[..], "hat":[{"id":"none","label":"없음"}, ..] }, "presets":[ {"label":"..","avatar":{..}} ] }` — 각 part 배열 항목은 `{"id","label"}`, 첫 항목이 기본값. hair 파츠는 hair_back/hair_front 레이어로, 나머지는 같은 이름 레이어로 그린다.
- 맵: `assets/map/manifest.json` — `{ "scale":2, "groundY":220, "width":1200, "layers":[ {"src":"assets/map/<file>.png","parallax":0.0~1.0,"y":<아트 px>,"repeatX":true|false} ] }`. 배열 앞쪽이 뒤에 그려진다. parallax 1.0 = 월드와 같이 움직임. 마지막 지면 레이어(parallax 1.0)는 너비 1200.
- 원본: `assets/_src/block/` Python(Pillow) 스크립트. `python3 assets/_src/block/build.py`로 assets/avatar, assets/map 전체 재생성(결정적 출력).
- UI: 블록 스타일을 CSS로 구현(계단형 픽셀 테두리, 3면 톤 버튼). PNG UI 스킨은 쓰지 않는다. 정본은 docs/design/style-guide.md.
- 텍스트(닉네임, 말풍선, UI)는 시스템 폰트로 화면 해상도에서 선명하게.

## 데이터 모델 (backend가 확정)
- characters: user_id (PK, auth.users 참조), nickname (unique), avatar (jsonb), created_at

## 알려진 한계 (MVP에서 수용)
- Broadcast 메시지에는 인증된 발신자 정보가 붙지 않는다. 악의적 클라이언트가 다른 user_id로 move/chat을 보낼 수 있다. 수신 측은 Presence에 없는 user_id 메시지를 버리는 것으로 완화하고, 근본 대응(서버 경유 또는 Realtime Authorization)은 후속 과제로 둔다.
- 위치는 서버가 검증하지 않는다 (몬스터 사냥 단계 전에 재설계).
