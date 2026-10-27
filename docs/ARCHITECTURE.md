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
   - Broadcast `move` (클라이언트 송신): `{ user_id, x, y, dir, s }`, 최대 10회/초, `dir`은 `'left' | 'right'`, `s`(사이클 6)는 `'idle' | 'walk' | 'jump' | 'fall' | 'crouch'`. `y`는 발 위치(월드, 지면 440, 점프 중 작아짐). `s`가 없으면 `idle/walk`로 추정.
   - (사이클 6) Presence `track()`은 입장 시와 닉네임/아바타 변경 시에만 호출한다(위치 갱신에 쓰지 않음 — Supabase Presence 전송 한도 초과로 채널이 끊긴 원인). Presence 상태의 x/y는 입장 시점 값일 뿐이며, 새 멤버가 들어오면(presence join) 기존 멤버가 자기 현재 상태를 `move`로 1회 보낸다. track 호출은 최소 2초 간격.
   - (사이클 6) 채널 구독은 반드시 `join_room` 성공(`'OK'`) 후. 채널 오류/종료 시 지수 백오프(1, 2, 4, 8, 16, 최대 30초)로 `join_room` → 재구독. 탭이 다시 보이면 즉시 상태 점검.
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
     `connectRoom(roomId, handlers, self, { signal }) → { sendMove, updateSelf, healthy, close, leave(= close) }` (handlers: onSync, onJoin, onLeave, onPeerJoin(user_id), onMove, onChat, onDrop(status)). (사이클 6) 하트비트·재시도·재입장은 어댑터가 아니라 `src/client/backend/room-link.js` 상태기계가 담당. 계측 `backend.stats = { track, moveSent, subscribe, removeChannel, joinRoom, leaveRoom, drops }`.
   - 예외: `join_room`은 비밀번호 불일치를 예외가 아니라 반환값 `'WRONG_PASSWORD'`로 돌려준다(예외는 실패 기록까지 롤백해 시도 제한이 무력화되므로). 성공은 `'OK'`. 어댑터가 `WRONG_PASSWORD` 오류로 변환한다.
   - 서버 세부 규칙(backend 확정): 멤버 행은 마지막 활동 후 10분간 유효 → 그 안의 재입장은 비밀번호 생략, `leave_room` 후나 10분 후에는 다시 필요. 60초 넘게 비활성인 사람의 닉네임은 새 입장자가 쓸 수 있다. 방 이름·채팅에 줄바꿈/제어문자 금지. 채팅 1초 제한은 모든 방 합산. local 모드도 같은 규칙.
   - 재입장용으로 sessionStorage `mushroom:room` = `{ roomId, nickname }` (이 방에서 쓴 닉네임 포함).
   - 오류는 `Error.code`로 구분: `ROOM_NOT_FOUND, WRONG_PASSWORD, ROOM_FULL, NICK_TAKEN, NICK_FORMAT, ROOM_NAME_FORMAT, PASSWORD_FORMAT, TOO_MANY_ROOMS, RATE_LIMITED, NOT_MEMBER, TEXT_FORMAT, NETWORK, UNKNOWN`. supabase 모드는 RPC가 `raise exception using message = '<코드>'`로 던지고 어댑터가 매핑한다.

## 인터페이스 계약
- 아바타 데이터(`characters.avatar`, jsonb, 사이클 3부터): `{ "skin", "hair", "face", "top", "bottom", "shoes", "hat" }` 7개 키, 값은 파츠 id 문자열. `hat`은 `"none"` 허용. (사이클 1~2의 `eyes` 키는 `face`로 대체. backend 마이그레이션으로 변환)
- 표시 시 manifest에 없는 id는 해당 파츠의 기본값(첫 항목)으로 그린다.

### 복셀 아트 계약 (2026-10-15 사이클 5 — 3D 복셀 모델 조명 렌더, 블록 아트 계약 대체)
- 방식: 캐릭터와 맵 모두 코드로 정의한 3D 복셀(상자) 모델을 오프라인 레이트레이서(numpy)로 조명 렌더(키라이트 + 필 + AO + 소프트 섀도 + 베벨 하이라이트 + 림)해 PNG/WebP로 굽는다. 원본: `assets/_src/voxel/`(공용 렌더러 + 캐릭터), `assets/_src/voxel_map/`(맵). 결정적 출력.
- 좌표: 월드 2400x540 월드 단위(기존과 같음), 지면선 월드 y=440. **에셋 밀도 1.5px = 월드 1단위**(화면 P=3에서 1:1, P=2에서는 2/3로 축소 표시).
- 렌더: 캔버스 `imageSmoothingEnabled = true`, `imageSmoothingQuality = 'high'`. 반투명 가장자리(알파) 허용. 1px 외곽선 없음. 표시 배율 P(화면 px / 월드 단위 = P/2)는 기존 규칙(기본 2, 1600x900 이상 3) 유지.
- 아바타 프레임: 월드 96x128 단위 = 시트 프레임 **144x192 px**, 기준점 **(72, 180) px** = 발 중앙 바닥(월드 (48,120)). 캐릭터 키(머리카락 포함)는 월드 약 90~100단위.
- 시트: 가로 8프레임 1152x192, 순서 `front, front_b, side, walk0, walk1, walk2, walk3, back` (프레임 i의 x = 144i). 오른쪽을 보는 것이 기본, 왼쪽은 프레임 좌우 반전(기준점 x 유지).
  - 애니메이션: `idle_front` = [0,1] 600ms(숨쉬기), `idle` = [2](인게임 정지), `walk` = [3,4,5,6] 150ms.
  - (사이클 6) 프레임 추가: 8 = `jump`(상승, 무릎 당기고 팔 위로), 9 = `fall`(하강, 다리 펴고 팔 벌림), 10 = `crouch`(숙이기, 정지). 시트 11프레임 1584x192. manifest `frames`/`animations`에 `jump` [8], `fall` [9], `crouch` [10] 추가. 기준점(72,180)은 모든 프레임 동일(점프 높이는 프런트가 y로 표현, 프레임은 포즈만). 프런트는 manifest에 해당 애니메이션이 없으면 idle 프레임으로 대체.
  - (사이클 6) 조작: 점프 = ↑ / W / Space(채팅 입력 중 아님), 숙이기 = ↓ / S 누르는 동안(지면에서만, 숙인 동안 이동 불가). 물리(월드 단위): 중력 2000/s², 점프 초속 650(최고 높이 약 105), 공중 좌우 이동 허용, 착지 시 y=440. 모바일 터치: 점프·숙이기 버튼 추가.
- 파츠 id: 사이클 3과 **같은 7개 파츠 키와 같은 id 집합**(skin 3, face 4, hair 8, top 6, bottom 5, shoes 4, hat 5+none)과 같은 프리셋 6종을 유지한다. 저장된 프로필이 그대로 동작해야 한다.
- 레이어: `assets/avatar/manifest.json`의 `layerOrder`가 정본. 각 항목 `{ "layer": "<폴더>", "part": "<파츠 키>", "blend": "source-over" | "source-atop" }`. 프런트는 순서대로 `assets/avatar/<layer>/<id>.png`(id = 프로필의 해당 파츠 값)를 해당 blend로 합성한다. 파일이 없으면 건너뛴다(예: hat none, 그림자 없는 파츠). 그림자 레이어(`shade_*`)는 `source-atop`.
- 매니페스트: `{ "frame":{"w":144,"h":192}, "anchor":{"x":72,"y":180}, "density":1.5, "frames":[..8개], "animations":{..}, "layerOrder":[..], "parts":{..}, "presets":[..] }`.
- 맵: `assets/map/manifest.json` — `{ "density":1.5, "groundY":440, "width":2400, "layers":[ {"src":"assets/map/<file>","parallax":0~1,"y":<월드 단위>,"repeatX":bool,"stretchX":bool} ] }`. src는 .png 또는 .webp. 앞쪽 항목이 뒤에 그려진다. parallax 1.0 지면 레이어는 월드 너비 2400(=3600px). y와 크기는 월드 단위로 환산(px / 1.5). 맵 전체 용량 목표 6MB 이하.
- UI: 블록 스타일 CSS(ui-kit) 유지.
- 이전 블록 아트 계약(48x64, 2D 면 명암)은 폐기. 소스는 git 이력에 있다.

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
