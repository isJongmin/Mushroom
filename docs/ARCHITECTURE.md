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

### 사이클 8 계약 (2026-10-28)
- **엎드리기**: 프레임 10을 `crouch`(쪼그려 앉기)에서 `prone`(배를 바닥에 대고 완전히 엎드림, 메이플 스타일)으로 교체한다. manifest animations 키는 `prone` [10]으로 바꾸고, 프런트는 `crouch`가 있으면 같은 의미로 받아 준다(호환). 엎드린 모습은 가로로 길고 낮다(키의 약 35~45%). 기준점(72,180)은 유지하고, 몸은 진행 방향(오른쪽)으로 눕는다. 상태값 `s`는 `'prone'`(구 `'crouch'`도 수신 허용).
- **발판(플랫폼)**: 맵 manifest에 `platforms: [{ "id", "x1", "x2", "y" }]`(월드 단위, y = 발판 윗면 = 서는 높이)를 추가한다. 지면(y=440, x 0~2400)은 암묵적 바닥이다. 발판은 **한 방향 통과**다. 아래에서 뛰어오르면 통과하고, 위에서 떨어질 때만 착지한다. 층 간격은 일반 점프(약 105)로 오를 수 있게 **세로 85~95**로 하고, 가장 높은 층은 y 170 이상으로 한다(슈퍼 점프 전용 층은 더 높아도 된다). 발판 그림은 아트가 맵 레이어(ground 또는 mid 중 parallax 1.0 레이어)에 정확히 같은 좌표로 그리고, `platforms` 목록의 정본도 아트가 소유한다.
- **아래 + 점프 = 뛰어내리기**: 발판 위에서 ↓를 누른 채 점프하면, 그 발판을 0.25초 무시하고 아래로 떨어진다. 지면 위에서는 아무 일도 일어나지 않는다(점프도 하지 않는다).
- **슈퍼 점프**: 같은 방향키(←, →, ↑ / A, D, W)를 300ms 안에 두 번 누르면 발동한다. ←/→는 그 방향으로 대시(수평 초속 1100, 0.22초 동안 중력 절반, 동시에 위로 초속 350), ↑는 높이 뛰기(초속 950, 최고 약 225)다. 지면, 발판, 공중(공중에서는 1회, 착지하면 다시 충전) 어디서든 쓸 수 있다. 쿨다운은 0.8초다. 이펙트는 프런트가 절차적으로 그린다(잔상 3~4개 + 시작 지점 큐브 파티클 버스트 + 바람 줄기). move payload에 `fx: 'dash-left'|'dash-right'|'dash-up'`을 1회 실어 보내 원격 화면에서도 이펙트가 재생된다.
- **신발 아래 레이어(사이클 8)**: layerOrder에서 `bottom` 바로 앞에 `{layer:'shoes_under', part:'shoes', blend:'source-over'}`를 추가한다. 긴 바지 정강이 안쪽과 뒤에 오는 신발 부분(양말, 하이탑 발목)이 이 레이어로 가서, 긴 바지에는 가려지고 치마나 반바지에서는 보인다.
- **방 삭제**: 방장(created_by)만 `delete_room(p_room_id)` RPC로 방을 삭제할 수 있다. 삭제 직전에 서버가 비공개 채널 `room:<id>`로 broadcast `room_closed` `{ room_id, by_nickname }`을 보낸다. 받은 클라이언트(방장 포함)는 채널을 닫고 로비로 이동하며 "방장이 방을 삭제했어요" 배너를 띄운다. 채널을 놓친 클라이언트는 다음 heartbeat/join이 `ROOM_NOT_FOUND`/`NOT_MEMBER`를 받아 같은 처리를 한다. `list_rooms`는 `mine boolean`(내가 만든 방) 컬럼을 추가로 반환한다. 오류 코드 `NOT_OWNER`를 추가한다. UI는 방 HUD에 방장에게만 "방 삭제" 버튼을, 로비 목록의 내 방에도 삭제 버튼을 둔다. 둘 다 확인 모달을 거친다(브라우저 confirm 금지).
- 파츠 id: 사이클 3과 **같은 7개 파츠 키와 같은 id 집합**(skin 3, face 4, hair 8, top 6, bottom 5, shoes 4, hat 5+none)과 같은 프리셋 6종을 유지한다. 저장된 프로필이 그대로 동작해야 한다.
- 레이어: `assets/avatar/manifest.json`의 `layerOrder`가 정본. 각 항목 `{ "layer": "<폴더>", "part": "<파츠 키>", "blend": "source-over" | "source-atop" }`. 프런트는 순서대로 `assets/avatar/<layer>/<id>.png`(id = 프로필의 해당 파츠 값)를 해당 blend로 합성한다. 파일이 없으면 건너뛴다(예: hat none, 그림자 없는 파츠). 그림자 레이어(`shade_*`)는 `source-atop`.
- 매니페스트: `{ "frame":{"w":144,"h":192}, "anchor":{"x":72,"y":180}, "density":1.5, "frames":[..8개], "animations":{..}, "layerOrder":[..], "parts":{..}, "presets":[..] }`.
- 맵: `assets/map/manifest.json` — `{ "density":1.5, "groundY":440, "width":2400, "layers":[ {"src":"assets/map/<file>","parallax":0~1,"y":<월드 단위>,"repeatX":bool,"stretchX":bool} ] }`. src는 .png 또는 .webp. 앞쪽 항목이 뒤에 그려진다. parallax 1.0 지면 레이어는 월드 너비 2400(=3600px). y와 크기는 월드 단위로 환산(px / 1.5). 맵 전체 용량 목표 6MB 이하.
- UI: 블록 스타일 CSS(ui-kit) 유지.
- 이전 블록 아트 계약(48x64, 2D 면 명암)은 폐기. 소스는 git 이력에 있다.

### 사이클 10 계약 (2026-10-28) — 고해상도 복셀 복귀, 공격 강화 버프

사용자 결정: 2D 메이플풍(치비, v2 모두)은 폐기하고 **복셀로 돌아간다. 블록을 더 잘게** 나눠 Canva 새 시안(캐릭터 MAHZSj_bNq4, 배경 MAHZSrXs_ZA, 썸네일 scratchpad/canva2/)에 가깝게 만든다. 몬스터 드롭은 **의상이 아니라 공격 강화 버프**다. 사이클 9 계약 중 아래가 바뀐다. 나머지(PvP, 몬스터 호스트 권위, 사망·유령·비석, HP 바, 월드 4800x1000, platforms/spawns)는 그대로다.

- **캐릭터(복셀, `assets/_src/voxel/`)**: 시트 계약 그대로(프레임 144x192, 기준점 (72,180), 밀도 1.5, 13프레임 1872x192, 11=attack0, 12=attack1, animations attack [11,12] 120ms, 10=prone). 파츠 키 7개, 기존 id 전부, 프리셋 6종 유지. **복셀 단위 크기를 사이클 8의 1/2**로 줄여(모델 해상도 2배) 실루엣을 둥글게 하고 디테일(눈 하이라이트, 끈, 주름, 포켓, 로고)을 늘린다. 조명은 시안처럼 부드러운 AO와 따뜻한 키라이트. **드롭 전용 파츠는 만들지 않는다**(사이클 9 드롭 의상 폐기).
- **배경(복셀, `assets/_src/voxel_map/` 복구)**: 월드 4800x1000, groundY 900, platforms 30개와 spawns 11개 좌표(`assets/_src/art2d_map/platforms.py` 정본) 그대로. 레이어 파일명과 패럴랙스(sky, clouds 0.10, far 0.25, mid 0.55, ground 1.0) 그대로. 톤은 새 시안: 피치~더스티 블루 하늘, 볼륨 구름, 대기원근 능선과 침엽수 숲, 돔 지붕 카페·베이커리(줄무늬 차양, 화분, 스트링 라이트, 파라솔, 벤치), 벚나무, 잔디 섬 발판(아래 흙 단면), 나무 데크. 복셀은 사이클 8 맵보다 잘게.
- **버프 드롭(의상 드롭 대체)**: 버프 종류 id 5개 고정
  - `range` 사거리: 판정 가로 +35/스택 (기본 70)
  - `multi` 공격 횟수: 타수 +1/스택 (기본 1). 한 번의 atk에 여러 타. 피해 숫자는 타마다 80ms 간격으로 띄운다
  - `element` 속성: 피해 +20%/스택, 베기 이펙트에 속성색(1스택 불 주황, 2스택 얼음 하늘, 3스택 번개 노랑)
  - `power` 공격력: 피해 +4/스택 (기본 8~14)
  - `speed` 공격 속도: 쿨다운 x0.8/스택 (기본 0.45초, 최소 0.25초)
  - 지속 60초. 같은 버프를 다시 주우면 스택 +1(최대 3)이고 시간은 60초로 갱신. 사망하면 모두 사라진다. HUD 좌상단에 아이콘 + 스택 수 + 남은 시간 원형 게이지.
  - 드롭 확률: 몬스터 manifest `buffDrop`(0~1, 버프 종류는 균등 무작위). snail 0.35, bat 0.4, mushroom 0.45, slime 0.5, golem 1.0(2개). 호스트가 `drop { id, buff, x, y }`를 보낸다. 줍기는 **닿으면 자동**(Z도 동작) → `pick { drop_id, user_id }` → 호스트 `picked { drop_id, user_id, buff }`. 드롭 30초 뒤 사라짐.
  - `atk` payload 확장: `{ user_id, x, y, dir, seq, w, hits, dmin, dmax, el }`(공격자가 자기 버프로 계산). 받는 쪽(PvP 피격자, 몬스터 호스트)은 상한으로 자른다: w≤175, hits≤4, dmax≤60, el 0~3. 없으면 기본값.
- **에셋**: `assets/fx/buff/<id>.png` 아이콘 64x64(5종), 드롭 구슬 `assets/fx/buff_orb.png`(종류별 색, 가로 5프레임 시트 각 48x48, 순서 range,multi,element,power,speed), 베기 이펙트 속성색 3종 `assets/fx/slash_fire.png`, `slash_ice.png`, `slash_bolt.png`(slash.png와 같은 규격). 없으면 프런트는 절차적 대체 그림.
- **폐기**: 인벤토리(가방 버튼, `mushroom:inventory`), 프로필 자물쇠, manifest `drop` 파츠, 몬스터 manifest `drops`. localStorage 기존 키는 무시만 한다.

### 사이클 9 계약 (2026-10-28) — 2D 메이플풍 전환, PvP, 몬스터, 드롭 의상
메인 결정(사용자 지시 기반, 사용자 확인 없이 진행):
- **아트 방식 전환**: 복셀 레이트레이서를 버리고 **2D 벡터 일러스트**(메이플스토리풍)로 캐릭터와 배경을 모두 다시 만든다. 코드로 정의한 벡터 도형(베지어 패스)을 고품질 안티앨리어싱으로 래스터화한다(4배 슈퍼샘플 후 축소). 스타일: 2.5등신 치비, 머리가 키의 약 45%, 큰 눈(하이라이트 2개), 어두운 색조 외곽선(검정이 아니라 각 색의 진한 톤, 에셋 px 기준 약 2.5px), 셀 셰이딩 2단 + 하이라이트 1단. 원본 `assets/_src/art2d/`(캐릭터), `assets/_src/art2d_map/`(배경), `assets/_src/art2d_mob/`(몬스터, 비석, 유령, 아이템 아이콘). 복셀 원본은 git 이력에 남기고 폴더는 삭제해도 된다.
- **유지하는 계약**: 파츠 키 7개, 기존 id 집합, 프리셋 6종, manifest 형식, layerOrder 방식(`{layer,part,blend}`), 프레임 144x192, 기준점 (72,180), 밀도 1.5. 저장된 프로필은 그대로 동작해야 한다.
- **시트 확장**: 프레임 11 = `attack0`(무기 뒤로 젖힘), 12 = `attack1`(앞으로 휘두름). 시트 13프레임 1872x192. manifest animations에 `attack` [11,12] 120ms 추가. 무기는 캐릭터 레이어가 아니다. 휘두르는 궤적(호 모양 슬래시)은 프런트 fx가 그린다.
- **월드 확대**: 월드 4800 x 1000, 지면 y=900(맵 manifest `width` 4800, `height` 1000, `groundY` 900). 카메라는 가로·세로 모두 플레이어를 따라간다. 발판은 4~5층, 층 간격 85~95, 슈퍼 점프 전용 층 허용. 맵 용량 목표 10MB 이하. 몬스터 스폰 구역은 맵 manifest의 `spawns: [{ "id", "platform": <platform id | "ground">, "x1", "x2", "mobs": ["<mob id>", ..], "max": n }]`(아트 소유).
- **전투 권위 (서버 DB 변경 없음, 방 채널 broadcast만 사용)**
  - 공격: Ctrl / J / X(모바일은 공격 버튼). 쿨다운 0.45초. 공격자가 broadcast `atk { user_id, x, y, dir, seq }`를 보낸다. 판정 상자는 공격자 기준 앞쪽 가로 70, 세로 70(발 위치 기준 y-75~y-5).
  - **PvP는 피격자 권위**: 각 클라이언트가 받은 `atk`를 자기 위치로 판정한다. 맞았으면 피해 8~14(무작위) 적용, 넉백(공격 방향으로 수평 300, 위로 250), 무적 0.6초. 그다음 broadcast `hp { user_id, hp, max, dead, by }`를 보낸다. 최대 HP 100.
  - **몬스터는 호스트 권위**: 호스트 = 현재 Presence에 있는 멤버 중 user_id가 사전순 가장 작은 사람. 호스트가 몬스터 AI와 스폰을 시뮬레이션하고 `mobs { t, list:[{ id, kind, x, y, dir, hp, s }] }`를 5회/초 보낸다. 다른 클라이언트는 이를 보간해 그린다. 호스트가 받은 `atk`가 몬스터에 맞으면 피해를 적용하고, 처치되면 `drop { id, item, x, y }`를 보낸다. 호스트가 바뀌면 새 호스트는 마지막으로 받은 `mobs` 상태에서 이어서 시뮬레이션한다.
  - 몬스터 접촉 피해: 각 클라이언트가 자기 캐릭터와 몬스터의 겹침을 판정해 스스로 피해를 적용한다(PvP와 같은 무적과 넉백 규칙).
  - 줍기: 드롭 위에서 Z(모바일은 줍기 버튼)를 누르면 `pick { drop_id, user_id }`를 보낸다. 호스트가 처음 요청한 한 명에게 `picked { drop_id, user_id, item }`을 보낸다. 받은 본인은 인벤토리에 추가한다. 드롭은 60초 뒤 사라진다.
- **사망과 유령**: HP가 0이 되면 `dead`가 된다. 캐릭터는 유령 스프라이트(`assets/mob/ghost.png`, 반투명, 위아래로 둥실)로 바뀌고, 그 자리에 비석(`assets/mob/tombstone.png`)이 위에서 떨어져 꽂힌다(낙하와 먼지 연출). 유령은 이동과 채팅은 할 수 있지만 공격, 피격, 줍기는 할 수 없다. 5초 뒤 "마을에서 부활" 버튼이 나오고, 누르면 스폰 지점에서 HP가 가득 찬 채 부활한다. 부활 직후 2초간 무적이다. 비석은 부활하면 사라진다. 상태값 `s`에 `'attack' | 'ghost'`를 추가한다. 재입장한 사람은 현재 상태를 `hp`로 1회 알린다(입장 시 move와 같은 규칙).
- **HP 바**: 모든 캐릭터 머리 위(닉네임 위)에 가로 40, 세로 5의 빨간 바를 그린다(배경은 어두운 회색, 테두리 1). 몬스터도 맞은 뒤 3초 동안 같은 바를 표시한다. 피해 숫자는 메이플처럼 위로 떠오르며 사라진다.
- **몬스터 종류**(`assets/mob/manifest.json`, 아트 소유, 형식 `{ "density":1.5, "mobs": { "<id>": { "name", "hp", "speed", "touchDamage", "size":{"w","h"}, "anchor":{"x","y"}, "frame":{"w","h"}, "sheet":"assets/mob/<id>.png", "animations":{"move":[..],"hit":[..],"die":[..]}, "fps", "behavior":"walk|hop|fly", "drops":[{"item","p"}] } } }`)
  - `snail` 달팽이(HP 25, 느림), `mushroom` 주황버섯(HP 45, 통통 뛰며 이동), `slime` 슬라임(HP 60, 뛰기), `bat` 박쥐(HP 35, 공중 비행), `golem` 돌골렘(HP 220, 큼, 느림, 접촉 피해 큼). 최소 5종.
- **드롭 의상**: 몬스터가 의상 아이템을 떨어뜨린다. 기존 파츠는 그대로 모두에게 열려 있고, **드롭 전용 파츠**를 추가한다(파츠 manifest 항목에 `"drop": true`). 최소 hat 3, top 3, bottom 2, shoes 2 등 10종 이상(예: 달팽이 껍질 모자, 버섯 갓 모자, 슬라임 젤리 후드, 골렘 갑옷 상의, 박쥐 날개 망토 상의). 아이템 id = `"<파츠 키>:<파츠 id>"`. 아이콘 `assets/avatar/icon/<파츠 키>/<id>.png`(64x64, 투명 배경)는 캐릭터 아트가 만든다. 드롭 확률은 몬스터 manifest의 `drops`.
- **인벤토리**: localStorage `mushroom:inventory` = `{ items: ["hat:snail-shell", ..] }`(프로필과 같은 방식, 서버 저장 없음). 방 HUD에 가방 버튼이 있어 패널에서 아이템을 누르면 즉시 착용한다(프로필 저장 + updateSelf). 프로필 화면은 드롭 전용 파츠를 인벤토리에 없으면 자물쇠로 표시한다.
- **알려진 한계(수용)**: 피격자 권위라 자기 HP를 조작하는 클라이언트는 무적이 될 수 있다. 호스트는 몬스터와 드롭을 조작할 수 있다. 인벤토리는 로컬이라 조작할 수 있다. 의상은 외형뿐이라 수용한다.

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
