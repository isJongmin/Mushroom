# design -> main / frontend / art: 사이클 4 채팅방 화면 (프로필 → 로비 → 방)

날짜: 2026-10-15 / 담당: 디자인
상태: 완료. 기준 = ARCHITECTURE 결정 3~6, "화면 흐름 (사이클 4)". 블록 UI(v3)는 그대로 두고 확장했다.

## 1. 문서

| 파일 | 상태 | 내용 |
|---|---|---|
| `docs/design/screens/profile.md` | 신규 | 닉네임(형식만 실시간 검사) + 캐릭터 꾸미기(v3 탭/슬롯/프리셋/회전 미리보기 그대로). 최초 "입장하기" / 수정 "취소"+"저장". 서버 통신 없음, localStorage `mushroom:profile` |
| `docs/design/screens/lobby.md` | 신규 | 머리줄(로고, 모드 칩, 내 캐릭터 카드 + 꾸미기), 방 목록(행, 자물쇠, n/20, 가득 참), 5초 폴링 + 새로고침, 빈/로딩/오류 상태, 방 만들기·비밀번호·닉네임 겹침 모달, 오류 문구 전체 |
| `docs/design/screens/room.md` | 신규 (`game.md` 개정) | HUD(방 이름 + 자물쇠, n/20명, 나가기), 채팅 로그 패널, 전송 오류, 상태/배너, 모바일 2줄 HUD |
| `docs/design/screens/login.md` | 폐기 표시 | 내용은 기록으로 유지(비밀번호 필드/보기 토글 규격은 모달이 재사용) |
| `docs/design/screens/character-create.md` | 폐기 표시 | 3장(미리보기), 5장(파츠 선택)은 profile.md가 참조하므로 유효 |
| `docs/design/screens/game.md` | 폐기 표시 | 입력/터치/키보드/아바타/재연결 절은 room.md가 참조하므로 유효 |
| `docs/design/style-guide.md` | v4.0 | 11장(v4 컴포넌트 규격, 문구 톤, 반투명 예외) + 12장 변경 이력. 4.1/5.6/8.3/9장 문구 갱신 |
| `docs/design/ui-kit.css` | v4 | 14~23절 추가 (기존 1~13절은 변경 없음, 헤더 주석만) |
| `docs/design/ref/c4/*.png` | 신규 19장 | 시안 (7장) |

## 2. 핵심 결정

1. **채팅 로그 위치 = 캔버스 왼쪽 위, HUD 첫 줄 아래** (left 12, top 56), **가로 320, 세로 `clamp(120px, 캔버스H - 328px, 240px)`** → 1280x800(캔버스 540)에서 320 x 212. 세로 공식은 4줄 말풍선 위 끝(캔버스 아래에서 262px)보다 위에서 끝나게 해서, 데스크톱에서는 아바타/라벨/말풍선을 절대 가리지 않는다. 아래쪽은 아바타가 모이는 곳이라 피했다.
2. **모바일 로그 = 접힘 기본**, HUD 2줄째 "채팅 기록" 토글(+읽지 않은 수 배지)로 펼침. 펼치면 캔버스 위 오버레이 (8, 46) ~ 오른쪽 8, 세로 `clamp(96px, 캔버스H - 226px, 320px)` → 360x640에서 344 x 282. 내 캐릭터 머리는 가리지 않음(말풍선은 가릴 수 있음 — 같은 내용이 로그에 있음). 채팅 입력은 기존 위치.
3. **나가기 = 확인 창 없음.** 잃는 데이터가 없고(기록 50개 서버 보관, 빈 방 30분 유지) 버튼이 작고 단축키가 없다. 잠금 방 재입장 시 비밀번호 재입력은 수용.
4. **모달**: 딤 클릭으로 닫지 않음(입력 보호), Esc = 취소, focus trap + 뒤 `main`에 `inert`, 닫으면 연 버튼으로 포커스 복귀(사라졌으면 "방 목록" 제목). 처리 중엔 Esc 무시. 애니메이션 없음. 모바일은 위 64px부터(키보드 대비).
5. **ROOM_FULL / ROOM_NOT_FOUND는 모달을 닫고 로비 배너 + 즉시 목록 갱신.** WRONG_PASSWORD는 필드 오류(입력 비움), RATE_LIMITED는 배너 + 주 버튼 10초 비활성 카운트다운.
6. **NICK_TAKEN**: 비밀번호 모달 → 닉네임 모달로 교체. 제안값 = 프로필 닉네임 + "2"(12자 넘으면 앞 11자 + "2"), 전체 선택. 입력한 비밀번호는 메모리에 보관해 재시도에 사용(재입력 없음). 프로필은 그대로, 방 닉네임은 sessionStorage `mushroom:room.nickname`에만.
7. **반투명 예외 2곳**: `--dim` ink 72%, `--log-bg` hb2 88%. 로그 글자 대비는 white 배경 위 합성색 `#474455` 기준 전부 4.5:1 이상(최저 `st1` 5.5). 0.88 아래로 낮추지 말 것.
8. **문구 톤 해요체**로 통일(새 화면 + 프로필 닉네임 문구).
9. 자물쇠는 CSS box-shadow 도트(`.bk-ico--lock` 14x16, 노란 블록 몸통 + `hb2` 고리 + `ink` 열쇠 구멍). 이모지/글리프 금지.

## 3. 새 컴포넌트 / 클래스 (`ui-kit.css` 14~23절)

| 컴포넌트 | 클래스 | 비고 |
|---|---|---|
| 토큰 | `--dim`, `--log-bg`, `--row-h 64`, `--thumb 40`, `--log-w 320` | |
| 아이콘 | `.bk-ico--lock`(14x16), `.bk-ico--user`(10x12, currentColor), `.bk-ico--down`(14x8) + `.bk-ico--up` | `aria-hidden` |
| 작은 로고 | `.bk-logo.bk-logo--sm` | 24px(모바일 20) |
| 아주 작은 버튼 | `.bk-btn--xs` | 박스 24, 터치 확장 44 |
| 숫자 배지 | `.bk-badge` | `hidden`으로 숨김, "99+" |
| 인원 배지 | `.bk-chip.bk-count` (+ `.is-full`) | "N/20명" |
| 내 캐릭터 카드 | `.bk-me`, `.bk-thumb`, `.bk-me__name/__label/__nick` | |
| 방 목록 | `.bk-roomwrap`(스크롤 틀) > `ul.bk-roomlist[role=list]` > `li.bk-room`(+`.is-full`, `.is-skel`), `.bk-room__lock/__main/__name/__meta/__go`, `.bk-skel(--name/--meta/--count/--btn)` | |
| 빈/오류 상태 | `.bk-empty`(+`--error`), `.bk-empty__art/__title/__text` | |
| 모달 | `.bk-dim`(+`[hidden]`) > `.bk-panel.bk-modal`, `.bk-modal__head/__room/__desc/__foot`, `body.has-modal` | |
| 배너 숨김 | `.bk-banner[hidden]` | `display:block` 덮어쓰기 수정 |
| 채팅 로그 | `.bk-log`(+`.is-collapsed`), `.bk-log__head/__title/__list/__state/__new`, `.bk-msg`(+`--self`, `--sys`, `.is-error`, `.is-history`), `.bk-msg__nick/__time` | |
| 배치 | `.card-head .card-title`, `.cta-pair`, `.scr-lobby`, `.lobby-head/-brand/-panel/-tools/-tools__count/-note`, `.hud-room`, `.room-log`, `.hud-row2`, `.room-log-toggle`, `.game-stage.log-open` | |

## 4. 문구 전체

### 4.1 프로필
| 코드/상태 | 문구 |
|---|---|
| 안내 | 2~12자, 한글·영문·숫자만 쓸 수 있어요. |
| 형식 맞음 | 쓸 수 있는 형식이에요. |
| `NICK_FORMAT` | 2~12자의 한글, 영문, 숫자만 쓸 수 있어요. |
| `MANIFEST` | 파츠 정보를 불러오지 못했어요. 새로고침해 주세요. |
| `STORAGE` (로비 정보 배너) | 프로필을 이 브라우저에 저장하지 못했어요. 새로고침하면 다시 만들어야 해요. |
| 상시 안내 | 프로필은 이 브라우저에만 저장돼요 |

### 4.2 로비
| 코드/상태 | 문구 |
|---|---|
| 빈 목록 | 아직 방이 없어요. / 첫 방을 만들어 보세요. |
| 첫 로딩 (숨김 상태) | 방 목록을 불러오는 중이에요 |
| 수동 새로고침 완료 (숨김 상태) | 방 목록을 새로 고쳤어요. N개 |
| 100개 | 방이 많아 100개까지만 보여요. |
| 방 만들기 비밀번호 도움말 | (빈 값) 비워 두면 누구나 들어올 수 있는 공개 방이 돼요. / (4~32자) 비밀번호를 아는 사람만 들어올 수 있어요. |
| `ROOM_NAME_FORMAT` | 방 이름은 1~24자로 정해 주세요. 줄바꿈 같은 특수 문자는 쓸 수 없어요. |
| `PASSWORD_FORMAT` | 비밀번호는 4~32자로 정해 주세요. |
| `TOO_MANY_ROOMS` | 방은 동시에 3개까지 만들 수 있어요. 내가 만든 방이 비고 30분이 지나면 사라져요. |
| `WRONG_PASSWORD` | 비밀번호가 맞지 않아요. 다시 입력해 주세요. |
| `RATE_LIMITED` | 잠시 후 다시 시도해 주세요. (주 버튼 "N초 뒤 다시" 10초) |
| `ROOM_FULL` | 방이 가득 찼어요. 다른 방을 골라 주세요. |
| `ROOM_NOT_FOUND` | 방이 사라졌어요. 목록을 새로 고쳤어요. |
| `NICK_TAKEN` | 모달 제목 "닉네임이 겹쳐요" / 설명 "이 방에 같은 닉네임이 있어요. 이 방에서만 쓸 닉네임을 정해 주세요. 프로필 닉네임은 그대로예요." / 재실패 "이 닉네임도 이 방에 있어요. 다른 닉네임을 써 주세요." |
| `NICK_FORMAT` | 2~12자의 한글, 영문, 숫자만 쓸 수 있어요. |
| `NETWORK` 입장 | 연결이 불안정해요. 다시 시도해 주세요. |
| `NETWORK` 만들기 | 방을 만들지 못했어요. 연결을 확인하고 다시 시도해 주세요. |
| `NETWORK` 첫 로딩 | 방 목록을 불러오지 못했어요. / 인터넷 연결을 확인한 뒤 다시 시도해 주세요. (버튼 "다시 시도") |
| `NETWORK` 갱신 | 연결이 불안정해요. 목록이 최신이 아닐 수 있어요. |
| `UNKNOWN` | 문제가 생겼어요. 잠시 후 다시 시도해 주세요. |
| 재입장 실패 | 방에 다시 들어가지 못했어요. 목록에서 다시 골라 주세요. |

### 4.3 방
| 코드/상태 | 문구 |
|---|---|
| 들어가는 중 | 방에 들어가는 중... |
| 로그 로딩 | 대화를 불러오는 중이에요 |
| 기록 구분 | 이전 대화 N개 |
| 기록 실패 | 이전 대화를 불러오지 못했어요. |
| 입장/퇴장 | OO님이 들어왔어요 / OO님이 나갔어요 |
| 연결 (로그) | 연결이 끊어졌어요 / 다시 연결됐어요 |
| 새 메시지 버튼 | 새 메시지 N개 |
| 연결 끊김 배너 | 연결이 끊어졌어요. 다시 연결하는 중... |
| 재연결 실패 | 연결하지 못했어요. [다시 연결] |
| `NOT_MEMBER` (자동 재입장 실패) | 방과 연결이 끊어졌어요. 로비에서 다시 들어와 주세요. [로비로] |
| 치명적 오류 | 방에 들어갈 수 없어요. 다시 시도해 주세요. [다시 시도] |
| 전송 `NETWORK` / `UNKNOWN` | 메시지를 보내지 못했어요. |
| 전송 `RATE_LIMITED` | 잠시 후 다시 보내 주세요. |
| 전송 `TEXT_FORMAT` | 메시지는 1~80자로 보내 주세요. |
| 나가기 처리 중 | 나가는 중 |
| 캔버스 aria-label | <방 이름> 맵. 좌우 방향키로 이동, Enter로 채팅 |

v3 게임 화면의 쿨다운 힌트("1초 뒤에 다시 보낼 수 있습니다.")와 조작 힌트 칩 문구는 그대로 둔다(문구 톤 변경은 다음 정리 때).

## 5. 프런트 구현 포인트

1. `ui-kit.css`를 다시 복사(`src/client/ui-kit.css`). 1~13절 값은 바뀌지 않았다. 프런트 전용 규칙은 별도 파일.
2. **스크롤 틀 안의 블록 테두리**: `.bk-roomwrap`, `.bk-log__list`는 `overflow-y: auto`라 바깥 그림자가 잘린다 → 안쪽 패딩(목록 8 10 12 8)을 줄이지 말 것. 행 사이 `gap 12`도 유지.
3. **로비 페이지는 스크롤하지 않는다**: `.scr-lobby` 높이 `100dvh` + 패널 `flex: 1; min-height: 0` + 목록만 스크롤.
4. **목록 갱신은 방 id 키로 DOM 재사용**(스크롤/포커스 유지). 응답 후 5초 `setTimeout` 사슬, 숨김 탭 정지, 진입/요청 중 정지. 사라진 행에 포커스가 있었으면 `#lobby-title`(tabindex -1)로.
5. **사용자 입력(방 이름, 닉네임, 채팅)은 `textContent`만.**
6. **모달 focus trap**: `inert`(뒤 `main`) + Tab 순환 직접 구현(구형 Safari 대비). 하나만 열림. Esc/IME 조합 예외. 비밀번호 → 닉네임 모달 전환 시 포커스 복귀 생략.
7. **방 만들기 검사**: 이름 trim 후 1~24자 + 제어문자 금지, 비밀번호는 trim 하지 않음(길이만). 비밀번호 모달은 1자 이상이면 전송(서버가 판정).
8. **채팅 로그**: 기록 50개 → "이전 대화 N개" 구분 줄 → 내 입장 메시지. 실시간 `chat`은 `id`로 중복 제거, 내 메시지도 서버 `chat` 도착 때 로그에 넣음(말풍선은 즉시). Presence 첫 sync는 시스템 메시지 없음, 퇴장 메시지 3초 지연 후 재입장 시 둘 다 버림. 재연결 후 `recentMessages` 다시 불러와 끼워 넣기. DOM 200개 상한.
9. **자동 스크롤**: 바닥 24px 이내면 붙임, 아니면 위치 유지 + "새 메시지 N개"(시스템 제외). 내가 보낸 메시지는 항상 바닥으로. 접힘 중 읽지 않은 수 배지(99+).
10. **로그 접힘 상태**: 데스크톱 sessionStorage `mushroom:logOpen`, 모바일은 매번 접힘. 접힘 중 목록은 `display:none`/`hidden`(aria-live 끄기 위해).
11. **로그 크기**는 CSS(`.room-log`의 `clamp`, `%`는 `.game-stage` 높이 기준)로 자동 계산된다. `.game-stage`는 캔버스와 같은 CSS 크기여야 한다.
12. **배너 겹침**: 데스크톱 캔버스 720~1039 + 로그 펼침이면 `.game-stage`에 `log-open` 클래스를 붙인다(배너가 로그 오른쪽으로 이동). 모바일 배너 top 92.
13. **sessionStorage `mushroom:room` = `{ roomId, nickname }`** — 실제 입장에 쓴 닉네임 저장. 나가기 버튼에서만 삭제(새로고침/pagehide는 유지).
14. **나가기**: 확인 없음, 최대 1.5초 대기 후 실패해도 로비로. 로비는 즉시 갱신.
15. **프로필 저장 실패**(`STORAGE`)는 막지 말고 메모리로 진행 + 로비 정보 배너 1회.
16. 내 캐릭터 미니 썸네일 = 프로필 아바타 합성 front 프레임 (4,6)~(44,46) 1배(프리셋 썸네일과 같은 함수).
17. 오류 코드 → 문구 매핑은 4장 표를 한 모듈(`errors.js`)에 모아 둘 것을 권장(화면별 맥락 구분: NETWORK 4종).

## 6. 아트에게

새 아트 요청 없음. 자물쇠/사람/화살표 아이콘은 CSS 도트로 끝냈다(팔레트 42색 안: `hb2`, `y1`~`y4`, `ink`). 팔레트 변경 없음.

## 7. 시안

저장소 `docs/design/ref/c4/` (19장, 1280x800 / 360x640, dpr 1):
`lobby-desktop`, `lobby-mobile`, `lobby-loading`, `lobby-empty`, `lobby-error`(모바일), `lobby-notfound`(모바일), `modal-create-desktop`, `modal-create-mobile`, `modal-password-desktop`, `modal-password-mobile`, `modal-nick-mobile`, `room-desktop`, `room-desktop-collapsed`, `room-mobile`, `room-mobile-log`, `profile-first-desktop`(전체 길이), `profile-desktop`(수정), `profile-mobile`, `profile-mobile-full`.

시안 HTML(참고용, 저장소 밖, 사라질 수 있음): `/tmp/claude-0/-home-claude-mushroom/32cd137b-a08b-5b56-b439-13acd387c199/scratchpad/c4design/{lobby,room,profile}.html` (`lobby.html#create|create2|password|nick|empty|loading|error|notfound`, `room.html#open|collapsed`, `profile.html#first`), 캡처 `shoot.py`, 장면 합성 `gen.py`. `docs/design/ui-kit.css`를 절대 경로로 링크한다.

다듬은 회차: (1) 첫 렌더에서 `.bk-banner`의 `display:block`이 `hidden`을 덮어 배너가 항상 보임 → `[hidden]` 규칙 추가, 작은 로고 버섯이 1배라 약해 보임 → 2배. (2) 모달 설명/빈 상태 글자가 한글 음절 중간에서 끊김 → `word-break: keep-all`. 비밀번호 플레이스홀더가 도움말과 중복 → "4~32자". (3) 프로필 수정 카드의 `<h2>` 제목 크기 누락 → `.card-title`. 모든 캡처 `scrollWidth` = 뷰포트 폭(가로 스크롤 없음) 확인.

## 8. 메인에게 (확인/결정 필요)

- ARCHITECTURE 변경 요청 없음. 다만 아래 두 가지는 프런트/백엔드 계약에 영향:
  - sessionStorage `mushroom:room`에 `nickname`을 함께 저장하는 것(디자인 제안). 재입장 RPC가 멤버 행 닉네임을 쓰면 불필요.
  - `RATE_LIMITED` 후 클라이언트 10초 잠금은 디자인 임의 값. 서버 제한 창이 정해지면 맞출 것.
- `NOT_MEMBER` 시 자동 재입장 1회는 잠금 방이면 비밀번호 없이 실패할 수 있다(멤버 행이 지워진 경우). 그때는 "로비로" 배너로 끝난다 — 수용 여부 확인.
- QA 요청: 모달 focus trap/`inert`(Safari 15.4 미만 대체 경로), 반투명 로그 위 글자 가독성(밝은 구름/버섯집 위), 360px 로비/모달 키보드 상태(실기기).
