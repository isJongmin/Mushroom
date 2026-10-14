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
3. (사이클 4, 2026-10-15) 로그인 없음. 앱 시작 시 Supabase 익명 로그인(`auth.signInAnonymously()`)으로 보이지 않는 계정(uid)을 만든다. 세션은 supabase-js 기본 저장소(localStorage)에 유지.
   - 사용자 작업: 대시보드 Authentication > Sign In / Providers 에서 "Allow anonymous sign-ins" 켜기.
   - 프로필(닉네임 + 아바타 7키)은 서버에 저장하지 않고 localStorage `mushroom:profile` = `{ nickname, avatar }`에만 둔다. 브라우저 데이터를 지우면 사라진다(수용).
   - 닉네임 규칙: `^[가-힣A-Za-z0-9]{2,12}$`. 중복은 같은 방의 활성 멤버 사이에서만 금지(대소문자 무시, 서버 RPC가 강제).
4. 채팅방 (사이클 4 정책, 사용자 확정)
   - 방 비밀번호는 선택(4~32자). 있으면 잠금 방. 서버에서 bcrypt 해시(pgcrypto)로만 저장·검증. 해시 컬럼은 클라이언트가 읽을 수 없다.
   - 방 이름 1~24자(앞뒤 공백 제거, 제어문자 금지). 방당 최대 20명. 1인당 동시에 소유한 살아 있는 방 최대 3개.
   - 활성 멤버 = `last_seen_at`이 60초 이내. 클라이언트는 방 안에서 20초마다 하트비트.
   - 활성 멤버가 0명인 상태로 30분이 지난 방은 만료(목록에서 제외, 서버가 기회가 될 때 삭제).
   - 채팅은 방마다 최근 50개만 서버에 저장. 해당 방 멤버만 읽을 수 있다. 입장 시 최근 50개를 불러와 채팅 로그에 표시.
   - 방 목록은 로비에서 5초 간격 폴링(`list_rooms`): 이름, 잠금 여부, 활성 인원, 생성 시각. 인원 많은 순 → 최근 활동 순.
5. 실시간 (사이클 4): 방마다 **비공개 채널** `room:<room_id>` (`{ config: { private: true } }`, Realtime Authorization).
   - `realtime.messages` RLS: 해당 방 `room_members`에 본인 행이 있는 authenticated만 broadcast/presence 읽기·쓰기 허용. 공개 채널 `map:village`는 폐기.
   - Presence: key = user_id, 상태 = `{ user_id, nickname, avatar, x, y }`.
   - Broadcast `move` (클라이언트 송신): `{ user_id, x, y, dir }`, 최대 10회/초, `dir`은 `'left' | 'right'`.
   - Broadcast `chat` (**서버 송신만**): 클라이언트는 `send_message` RPC를 호출하고, DB가 저장 후 같은 채널로 `{ id, user_id, nickname, text, created_at }`를 보낸다(발신자·닉네임은 서버가 멤버 행에서 채움 → 채팅 위장 불가). 클라이언트가 직접 보낸 `chat` 이벤트는 무시한다.
6. 실행 모드 두 가지 (src/client/config.js로 전환):
   - supabase 모드: `SUPABASE_URL`, `SUPABASE_ANON_KEY`가 채워진 경우.
   - local 모드: 값이 비어 있으면 자동 전환. 방/멤버/메시지는 localStorage, 실시간은 방별 BroadcastChannel(`mushroom:room:<id>`)로 같은 브라우저 탭끼리 동작. 방 비밀번호는 PBKDF2 해시. 서버 규칙(인원, 닉네임 중복, 만료, 50개, 오류 코드)을 같은 의미로 흉내 낸다. 개발·QA용.
   - 어댑터 인터페이스(두 모드 동일):
     `init() → { userId }` (익명 로그인/복구),
     `listRooms() → [{ id, name, locked, members, createdAt }]`,
     `createRoom({ name, password, nickname }) → { roomId }` (만든 사람은 자동 입장),
     `joinRoom({ roomId, password, nickname })`,
     `leaveRoom(roomId)`, `heartbeat(roomId)`,
     `recentMessages(roomId) → [{ id, user_id, nickname, text, created_at }]` (오래된 것부터),
     `sendChat(roomId, text)`,
     `connectRoom(roomId, handlers, self) → { sendMove, updateSelf, leave }` (handlers: onSync, onJoin, onLeave, onMove, onChat, onStatus).
   - 예외: `join_room`은 비밀번호 불일치를 예외가 아니라 반환값 `'WRONG_PASSWORD'`로 돌려준다(예외는 실패 기록까지 롤백해 시도 제한이 무력화되므로). 성공은 `'OK'`. 어댑터가 `WRONG_PASSWORD` 오류로 변환한다.
   - 서버 세부 규칙(backend 확정): 멤버 행은 마지막 활동 후 10분간 유효 → 그 안의 재입장은 비밀번호 생략, `leave_room` 후나 10분 후에는 다시 필요. 60초 넘게 비활성인 사람의 닉네임은 새 입장자가 쓸 수 있다. 방 이름·채팅에 줄바꿈/제어문자 금지. 채팅 1초 제한은 모든 방 합산. local 모드도 같은 규칙.
   - 재입장용으로 sessionStorage `mushroom:room` = `{ roomId, nickname }` (이 방에서 쓴 닉네임 포함).
   - 오류는 `Error.code`로 구분: `ROOM_NOT_FOUND, WRONG_PASSWORD, ROOM_FULL, NICK_TAKEN, NICK_FORMAT, ROOM_NAME_FORMAT, PASSWORD_FORMAT, TOO_MANY_ROOMS, RATE_LIMITED, NOT_MEMBER, TEXT_FORMAT, NETWORK, UNKNOWN`. supabase 모드는 RPC가 `raise exception using message = '<코드>'`로 던지고 어댑터가 매핑한다.

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

## 화면 흐름 (사이클 4)
`프로필(닉네임 + 캐릭터 꾸미기)` → `로비(방 목록, 방 만들기, 프로필 수정)` → `방(맵 + 캐릭터 + 말풍선 + 채팅 로그 패널, 방 나가기)`.
- 처음 방문: 프로필 화면부터. 프로필이 저장돼 있으면 로비부터.
- 잠금 방 선택 시 비밀번호 입력 창. 공개 방은 바로 입장.
- 입장 실패 처리: WRONG_PASSWORD(다시 입력), ROOM_FULL, ROOM_NOT_FOUND(목록 갱신), NICK_TAKEN(이 방에서만 쓸 닉네임 변경 후 재시도, 프로필은 그대로).
- 새로고침 시 방 안에 있었으면(sessionStorage `mushroom:room`) 같은 방 재입장 시도(비밀번호 재입력 없이 멤버 행으로 확인), 실패하면 로비.

## 데이터 모델 (사이클 4, backend가 확정)
- rooms: id uuid PK, name, password_hash(null = 공개, 클라이언트 읽기 불가), locked(생성 컬럼), created_by uuid, created_at, last_active_at
- room_members: (room_id, user_id) PK, nickname, joined_at, last_seen_at
- room_messages: id bigint PK, room_id, user_id, nickname, text(1~80자), created_at — 방당 최근 50개 유지
- 모든 쓰기는 security definer RPC로만: `create_room, join_room, leave_room, heartbeat, list_rooms, recent_messages, send_message`. 테이블 직접 insert/update/delete 권한 없음.
- 사이클 1~3의 characters 테이블과 is_nickname_taken은 새 마이그레이션에서 제거(배포 전이라 데이터 없음).

## 알려진 한계 (MVP에서 수용)
- 같은 방 멤버끼리는 move broadcast와 presence 상태(닉네임, 아바타)를 위장할 수 있다. 채팅은 서버 송신이라 위장 불가. 방 밖 사용자는 채널 접근 불가.
- 익명 계정은 무제한 생성 가능 → 1인당 방 3개 제한과 비밀번호 시도 제한은 계정을 바꾸면 우회된다. 사용자가 늘면 CAPTCHA(Supabase Auth 지원) 추가.
- 멤버 행이 지워져도 이미 연결된 채널은 다음 재연결 때 권한이 재검사된다(즉시 강퇴 아님).
- 위치는 서버가 검증하지 않는다.
