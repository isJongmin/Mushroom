# 화면 설계: 로비 (방 목록 + 방 만들기 + 입장)

버전: 4.0 (2026-10-15, 사이클 4 신규).
참조: ARCHITECTURE 결정 3~6, "화면 흐름 (사이클 4)" (정본). 어댑터 `init / listRooms / createRoom / joinRoom`, 오류 코드 `Error.code`. style-guide v4 11장(새 컴포넌트), 구현 CSS `docs/design/ui-kit.css` 14~23절.
시안 (`docs/design/ref/c4/`):
- `lobby-desktop.png` 1280x800 (방 6개: 공개/잠금/가득 참), `lobby-mobile.png` 360x640
- `lobby-loading.png` (첫 로딩 뼈대), `lobby-empty.png` (빈 목록), `lobby-error.png` (모바일, 네트워크 오류), `lobby-notfound.png` (모바일, ROOM_NOT_FOUND 배너)
- `modal-create-desktop.png` (TOO_MANY_ROOMS 배너 + 비밀번호 포커스), `modal-create-mobile.png` (PASSWORD_FORMAT)
- `modal-password-desktop.png`, `modal-password-mobile.png` (WRONG_PASSWORD), `modal-nick-mobile.png` (NICK_TAKEN)

## 1. 목적과 진입

- 프로필이 있는 사용자가 방을 고르거나 만드는 화면. 프로필 화면 "입장하기/저장/취소", 방 "나가기", 방 재입장 실패 후 여기로 온다.
- 진입 시 `init()`(익명 로그인/복구)이 끝나지 않았으면 끝날 때까지 첫 로딩 상태(4.1)로 둔다. 끝나면 즉시 `listRooms()`.
- 떠나는 곳: 방(입장/만들기 성공), 프로필 수정("꾸미기").
- 배경 `.bk-world` 유지(프로필과 같은 배경, 다시 만들지 않음).

## 2. 레이아웃

### 2.1 DOM 골격

```html
<div class="bk-world" aria-hidden="true"> … (style-guide 5.11) </div>
<main class="scr-lobby" id="lobby">
  <header class="lobby-head">
    <div class="lobby-brand">
      <h1 class="bk-logo bk-logo--sm"><span class="bk-ico bk-ico--mush" aria-hidden="true"></span>버섯마을</h1>
      <span class="bk-chip bk-chip--mode">LOCAL MODE</span>            <!-- local 모드만 -->
    </div>
    <div class="bk-me">
      <span class="bk-thumb"><canvas width="40" height="40" aria-hidden="true"></canvas></span>
      <span class="bk-me__name"><span class="bk-me__label">내 캐릭터</span><span class="bk-me__nick">버섯이</span></span>
      <button class="bk-btn bk-btn--sm" type="button">꾸미기</button>
    </div>
  </header>
  <section class="bk-panel lobby-panel" aria-labelledby="lobby-title">
    <div class="lobby-tools">
      <h2 id="lobby-title" tabindex="-1">방 목록</h2>
      <span class="lobby-tools__count">6개</span>
      <button class="bk-btn bk-btn--sm" type="button">새로고침</button>
      <button class="bk-btn bk-btn--primary" type="button">방 만들기</button>
    </div>
    <div class="bk-banner bk-banner--error" role="alert" hidden></div>   <!-- 로비 배너 (6장) -->
    <div class="bk-roomwrap">
      <ul class="bk-roomlist" role="list" aria-labelledby="lobby-title" aria-busy="false"> li.bk-room … </ul>
    </div>
    <p class="lobby-note" hidden>방이 많아 100개까지만 보여요.</p>
  </section>
</main>
<div class="bk-dim" hidden> <section class="bk-panel bk-modal" role="dialog" aria-modal="true"> … </section> </div>
```

방 행 하나:

```html
<li class="bk-room [is-full]" data-room-id="…">
  <span class="bk-room__lock"><span class="bk-ico bk-ico--lock" aria-hidden="true"></span></span>  <!-- 공개 방은 빈 span -->
  <span class="bk-room__main">
    <span class="bk-room__name">수다방</span>
    <span class="bk-room__meta">비밀번호 방 · 8분 전 생성</span>
  </span>
  <span class="bk-chip bk-count [is-full]"><span class="bk-ico bk-ico--user" aria-hidden="true"></span>5/20명</span>
  <button class="bk-btn bk-btn--primary bk-room__go" type="button" aria-label="수다방 입장, 비밀번호 방, 5명 접속 중">입장</button>
</li>
```

방 이름과 닉네임은 사용자 입력이므로 `textContent`로만 넣는다(HTML 삽입 금지).

### 2.2 데스크톱 (720px 이상, 기준 1280x800)

`.scr-lobby`: 높이 `100dvh`, 세로 flex, 가운데 정렬, 패딩 위 24 / 좌우 16 / 아래 56(잔디 띠가 조금 보이게), 줄 간격 16. 페이지 자체는 스크롤하지 않고 목록만 스크롤한다.

| 요소 | 규격 |
|---|---|
| 머리줄 `.lobby-head` | 가로 720, 양끝 정렬. 왼쪽: 작은 로고(24px/32, 버섯 아이콘 32x28, 간격 8) + 12px + 모드 칩. 오른쪽: `.bk-me` |
| 내 프로필 `.bk-me` | 크림 판자(칩 색 + 아래 두께 2px `c3` + 2px `w4`). 패딩 4 8 4 4. 썸네일 칸 44x44(`k3` 바탕 오목 베벨, 안 40x40) → 8 → 이름 묶음("내 캐릭터" 12px `w3` / 닉네임 16px 700 `ink`, 최대 168px 말줄임) → 16 → "꾸미기" `.bk-btn--sm` |
| 패널 `.lobby-panel` | `.bk-panel` 가로 720, 남은 높이 전부(1280x800에서 박스 약 640). 안쪽 세로 flex 간격 12 |
| 도구줄 `.lobby-tools` | 제목 "방 목록" 20px 700 → 12 → 개수 "N개" 14px `w3`(나머지 폭) → "새로고침" `.bk-btn--sm` → 12 → "방 만들기" `.bk-btn--primary` (높이 44) |
| 목록 틀 `.bk-roomwrap` | 오목 칸(바탕 `c2`, 베벨 위/왼 4 `w2`, 아래/오른 4 `white`), `overflow-y: auto`, 남은 높이 전부. 안쪽 패딩 8 10 12 8(행 테두리/두께가 잘리지 않게). 스크롤바: 폭 10, 엄지 `w3` 사각, 트랙 `c2` |
| 행 `.bk-room` | 박스 최소 높이 64, 패딩 8 12, 4열 그리드 `16px 1fr auto auto` 간격 12: 자물쇠 / 이름+메타 / 인원 배지 / 입장 버튼(최소 88). 행 사이 12(보이는 틈 6). 1280x800에서 약 7행이 보인다 |

### 2.3 모바일 (720px 미만, 기준 360x640)

`.scr-lobby` 패딩 16 18 16, 간격 12.

| 순서 | 요소 | 규격 |
|---|---|---|
| 1 | 로고 줄 | 로고 20px/28(아이콘 32x28) 왼쪽, 모드 칩 오른쪽 끝 |
| 2 | `.bk-me` | 가로 100%(324). 썸네일 44 + 이름 묶음(나머지 폭, 말줄임) + "꾸미기" |
| 3 | 패널 | 남은 높이(360x640에서 박스 약 480). 패딩 16 |
| 3a | 도구줄 | 제목 16px → 개수 → "새로고침"(sm) → "방 만들기"(primary). 290px 안에 한 줄(측정 약 262) |
| 3b | 목록 | 행 2줄 배치 `grid-template-areas: "lock name go" / "lock count go"`, 열 `14px 1fr auto` 간격 8. 이름 16px 한 줄 말줄임, 그 아래 인원 배지(높이 24, 12px). 메타 줄 숨김. 입장 버튼 최소 72 x 44. 360x640에서 약 4.5행 보임 |

가로 스크롤 금지(측정 `scrollWidth` 360).

## 3. 방 목록 동작

### 3.1 데이터와 표시

| 항목 | 출처 | 표시 |
|---|---|---|
| 이름 | `name` | 16px 700 `ink`, 한 줄 말줄임. 전체 이름은 `title` 속성과 입장 버튼 `aria-label`에 |
| 잠금 | `locked` | 자물쇠 도트 아이콘 14x16(`.bk-ico--lock`) + 메타 줄 "비밀번호 방". 공개 방은 아이콘 없음 + "공개 방" |
| 생성 시각 | `createdAt` | 메타 줄 " · 방금 생성"(1분 미만) / "N분 전 생성"(60분 미만) / "N시간 전 생성"(24시간 미만) / "N일 전 생성". 데스크톱만 |
| 인원 | `members` (활성 멤버 수) | 인원 배지 `.bk-count`: 사람 도트 아이콘 + "N/20명" (숫자 고정폭). `aria-label` "접속 인원 N명, 최대 20명" |
| 가득 참 | `members >= 20` | 행 `.is-full`(바탕 `c2`, 테두리 `w3`, 이름 `w4`), 배지 `.is-full`(바탕 `p1`, 글자/테두리 `r3`), 버튼 비활성 + 글자 "가득 참". 색 외에 버튼 글자로 구분 |
| 순서 | 서버 순서 그대로(인원 많은 순 → 최근 활동 순) | 클라이언트가 다시 정렬하지 않는다 |
| 개수 | 목록 길이 | 도구줄 "N개". 100개면 목록 아래 `.lobby-note` "방이 많아 100개까지만 보여요." |

### 3.2 갱신 (5초 폴링 + 수동)

- 자동: 응답을 받은 뒤 5초 후 다음 요청(`setTimeout` 사슬, 요청이 겹치지 않음). `document.visibilityState === "hidden"`이면 멈추고, 다시 보이면 즉시 1회 요청 후 사슬 재개. 로비를 떠나면(방 입장, 꾸미기) 멈춘다.
- 수동 "새로고침": 누르면 즉시 요청하고 자동 사슬을 그 응답 기준으로 다시 잡는다. 요청 중에는 버튼 비활성 + 로딩 점 + "새로고침"(최소 400ms 유지, 깜빡임 방지). 연타 무시.
- 모달이 열려 있어도 폴링은 계속한다(목록은 딤 아래에서 갱신). 입장/만들기 요청이 진행 중이면 그 동안만 멈춘다.
- 갱신 반영(키 = 방 id로 같은 DOM 행을 재사용): 스크롤 위치 유지, 포커스 유지. 포커스가 있던 행의 방이 사라지면 포커스를 제목 `#lobby-title`로 옮긴다. 갱신 표시 애니메이션 없음(5초마다 깜빡이면 산만함).
- 스크린 리더: 자동 갱신은 읽지 않는다. 수동 새로고침이 끝나면 숨김 상태 영역(`role="status"`)에 "방 목록을 새로 고쳤어요. N개" 1회.

## 4. 상태

### 4.1 상태 표

| 상태 | 조건 | 목록 영역 | 도구줄 |
|---|---|---|---|
| 첫 로딩 | `init()` 또는 첫 `listRooms()` 대기 | 뼈대 행 3개(`.bk-room.is-skel`, `c2` 막대: 이름 55% x 16, 메타 30% x 10, 배지 76 x 28, 버튼 88 x 44), `aria-busy="true"`, 숨김 상태 문구 "방 목록을 불러오는 중이에요" | 개수 자리에 로딩 점. 새로고침/방 만들기 비활성 |
| 정상 | 목록 1개 이상 | 행 목록 | 모두 활성 |
| 빈 목록 | 목록 0개 | `.bk-empty`: 버섯 아이콘(2배) → "아직 방이 없어요." 16px `ink` → "첫 방을 만들어 보세요." 14px `w4` → "방 만들기" primary 버튼(도구줄 버튼과 같은 동작) | "0개" |
| 첫 로딩 실패 | `init()` 또는 첫 `listRooms()`가 `NETWORK`/`UNKNOWN` | `.bk-empty.bk-empty--error` (`role="alert"`): "방 목록을 불러오지 못했어요." 16px `r3` → "인터넷 연결을 확인한 뒤 다시 시도해 주세요." → "다시 시도" primary | 개수 비움. 방 만들기 비활성(init 실패 시), 새로고침 활성 |
| 갱신 실패 | 정상 표시 중 폴링/수동 요청 실패 | 기존 목록 유지 | 로비 배너(6장) "연결이 불안정해요. 목록이 최신이 아닐 수 있어요." 다음 성공 때 자동으로 지움. 폴링은 계속 |
| 입장 중 | 공개 방 입장 버튼 누름 | 그 행 버튼: 비활성 + 로딩 점 + "입장 중". 다른 행 입장 버튼, 방 만들기, 새로고침, 꾸미기 비활성 | - |

"다시 시도"는 `init()`이 실패했으면 `init()`부터, 아니면 `listRooms()`만 다시 한다.

## 5. 모달 공통 (`.bk-dim > .bk-panel.bk-modal`)

### 5.1 모양

| 항목 | 값 |
|---|---|
| 딤 `.bk-dim` | `position: fixed; inset: 0; z-index: 50`, 바탕 `--dim` (ink 72%, v4 반투명 예외). 데스크톱: 모달을 가로세로 가운데. 모바일: 위 64px부터(키보드가 올라와도 입력이 가려지지 않게), 좌우 18 |
| 모달 박스 | `.bk-panel.bk-modal`, 가로 400(모바일 `100vw - 36` = 324), 패딩 16 |
| 머리 | 제목 `<h2>` 20px 700, 아래 12 |
| 방 줄 `.bk-modal__room` (비밀번호 모달) | 오목 띠(바탕 `c2`, 위/왼 2px `c3`), 패딩 8 12: 자물쇠 아이콘 + 8 + 방 이름 14px 700 `ink` 말줄임. 아래 16 |
| 설명 `.bk-modal__desc` | 14px/20 700 `w4`, 아래 16 |
| 모달 배너 | `.bk-banner--error` (`role="alert"`), 제목 아래, 아래 16 |
| 필드 | style-guide 5.4. 필드 사이 16 |
| 바닥 버튼 `.bk-modal__foot` | 위 24. 데스크톱: 오른쪽 정렬 [취소 secondary][주 버튼 primary], 각 최소 104, 간격 12. 모바일: 2칸 그리드(각 약 140) |
| 열림/닫힘 | 애니메이션 없음 |

### 5.2 동작과 접근성 (모든 모달 공통, 필수)

- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` = 제목 id, `aria-describedby` = 설명/방 줄 id(있으면).
- 열 때: 모달 뒤 `main#lobby`에 `inert` 속성(지원 안 되는 브라우저는 `aria-hidden="true"` + 아래 focus trap으로 대체), `body.has-modal`(스크롤 잠금). 첫 입력 필드에 포커스(필드가 없으면 주 버튼).
- **Focus trap**: Tab/Shift+Tab이 모달 안의 포커스 가능한 요소(입력, 보기 토글, 취소, 주 버튼)만 순환한다. 마지막에서 Tab → 첫 요소, 첫 요소에서 Shift+Tab → 마지막. 모달 밖 클릭으로 포커스가 나가지 않는다.
- 닫을 때: `inert` 해제, 포커스를 모달을 연 버튼으로 되돌린다. 그 버튼이 사라졌으면(목록 갱신으로 행 삭제) 제목 `#lobby-title`로.
- Esc = "취소". 단 요청 처리 중이거나 IME 조합 중이면 무시.
- 딤 클릭: 닫지 않는다(입력한 방 이름/비밀번호를 실수로 잃지 않게). 닫기는 "취소"와 Esc만.
- Enter: 주 버튼이 활성이면 제출(`<form>` submit). IME 조합 중 Enter는 무시.
- 처리 중: 주 버튼 비활성 + 로딩 점 + 진행 문구("만드는 중", "입장 중"), 입력/취소/보기 모두 비활성, Esc 무시.
- 오류 문구는 필드 오류면 그 필드 `.bk-help--error`(`aria-describedby`로 연결, `aria-invalid="true"`) + 그 필드로 포커스. 필드와 무관한 오류는 모달 배너(`role="alert"`).
- 한 번에 모달 1개만. 비밀번호 모달 → 닉네임 모달 전환은 첫 모달을 닫고(포커스 복귀 없이) 바로 다음 모달을 연다.

## 6. 로비 배너

- 위치: 도구줄 아래, 목록 위(`.lobby-panel > .bk-banner`). 정보는 `.bk-banner`, 오류는 `.bk-banner--error`, `role="alert"`(정보는 `role="status"`).
- 한 번에 하나. 새 배너가 이전 배너를 바꾼다. 다음 사용자 동작(입장/만들기/새로고침 누름) 때 지우거나, 갱신 실패 배너는 다음 성공 때 지운다. 그 밖에는 8초 뒤 사라진다.

## 7. 방 만들기 모달

시안: `modal-create-desktop.png`, `modal-create-mobile.png`.

| 요소 | 규격 |
|---|---|
| 제목 | "방 만들기" |
| 방 이름 | 라벨 "방 이름". `.bk-input--with-end`, `maxlength="24"`, `autocomplete="off"`, 카운터 "N/24"(앞뒤 공백 제거 후 글자 수, 입력 시작 후 표시). 도움말 "1~24자" |
| 비밀번호 | 라벨 "비밀번호 (선택)". `type="password"`, `maxlength="32"`, `autocomplete="new-password"`, 플레이스홀더 "4~32자". 오른쪽 안 "보기"/"숨기기" 토글 `.bk-link[aria-pressed]` (`aria-controls` = 입력, 누르면 `type` 전환, 포커스 유지) |
| 비밀번호 도움말 (실시간) | 비어 있음: "비워 두면 누구나 들어올 수 있는 공개 방이 돼요." (`w3`) / 4~32자: 자물쇠 아이콘 + "비밀번호를 아는 사람만 들어올 수 있어요." (`w3`) / 1~3자: 오류(아래) |
| 버튼 | "취소" / "만들기"(primary). "만들기" 활성 조건: 방 이름 형식 맞음 + 비밀번호가 비었거나 4~32자 |

검사 (클라이언트, 서버가 최종):
- 방 이름: 앞뒤 공백 제거 후 1~24자, 제어문자(U+0000–U+001F, U+007F–U+009F) 없음. 빈 값은 오류를 띄우지 않고 버튼만 비활성. 제어문자(붙여넣기)는 즉시 오류.
- 비밀번호: 앞뒤 공백을 제거하지 않는다(입력 그대로 전송). 길이만 검사. 1~3자 오류는 blur 또는 "만들기" 누름 때부터 표시, 이후 실시간.

제출: `createRoom({ name: trim(name), password: pw || null, nickname: profile.nickname })` → 성공하면 서버가 만든 사람을 자동 입장시킨다 → sessionStorage `mushroom:room` 저장 → 방 화면. 만든 사람에게는 비밀번호를 다시 묻지 않는다.

| 코드 | 표시 위치 | 문구 | 후속 |
|---|---|---|---|
| `ROOM_NAME_FORMAT` | 방 이름 필드 오류 | 방 이름은 1~24자로 정해 주세요. 줄바꿈 같은 특수 문자는 쓸 수 없어요. | 방 이름 필드로 포커스 |
| `PASSWORD_FORMAT` | 비밀번호 필드 오류 | 비밀번호는 4~32자로 정해 주세요. | 비밀번호 필드로 포커스 |
| `TOO_MANY_ROOMS` | 모달 배너 | 방은 동시에 3개까지 만들 수 있어요. 내가 만든 방이 비고 30분이 지나면 사라져요. | 입력 유지, "만들기" 다시 활성 |
| `RATE_LIMITED` | 모달 배너 | 잠시 후 다시 시도해 주세요. | "만들기" 10초 비활성(글자 "10초 뒤 다시" → 1초마다 줄어듦) |
| `NETWORK` | 모달 배너 | 방을 만들지 못했어요. 연결을 확인하고 다시 시도해 주세요. | 입력 유지 |
| `UNKNOWN` (그 밖) | 모달 배너 | 문제가 생겼어요. 잠시 후 다시 시도해 주세요. | 입력 유지 |

## 8. 입장

### 8.1 공개 방

"입장" → `joinRoom({ roomId, password: null, nickname: profile.nickname })`. 처리 중 4.1 "입장 중". 성공 → sessionStorage `mushroom:room` = `{ roomId, nickname }`(실제 쓴 닉네임) → 방 화면(배경 제거, 페이드 200ms).

### 8.2 잠금 방 → 비밀번호 모달

시안: `modal-password-desktop.png`, `modal-password-mobile.png`.

| 요소 | 규격 |
|---|---|
| 제목 | "비밀번호 입력" |
| 방 줄 | 자물쇠 + 방 이름(말줄임) |
| 필드 | 라벨 "비밀번호". `type="password"`, `maxlength="32"`, `autocomplete="off"`, 보기 토글. 도움말 없음(오류 자리 16px 확보) |
| 버튼 | "취소" / "입장"(primary). "입장" 활성 조건: 1자 이상 (형식 검사는 서버. 4자 미만이어도 보낸다 → 서버 `WRONG_PASSWORD`) |

제출: `joinRoom({ roomId, password, nickname: profile.nickname })`.

### 8.3 입장 오류 (공개 방 / 비밀번호 모달 / 닉네임 모달 공통)

| 코드 | 공개 방에서 | 모달에서 | 문구 |
|---|---|---|---|
| `WRONG_PASSWORD` | - | 비밀번호 필드 오류. 입력을 비우고 포커스, `aria-invalid` | 비밀번호가 맞지 않아요. 다시 입력해 주세요. |
| `RATE_LIMITED` | 로비 배너 | 모달 배너. "입장" 10초 비활성(카운트다운 "10초 뒤 다시"), 입력 유지 | 잠시 후 다시 시도해 주세요. |
| `ROOM_FULL` | 로비 배너 + 즉시 목록 갱신 | 모달 닫기 → 로비 배너 + 즉시 갱신 | 방이 가득 찼어요. 다른 방을 골라 주세요. |
| `ROOM_NOT_FOUND` | 로비 배너 + 즉시 목록 갱신 | 모달 닫기 → 로비 배너 + 즉시 갱신 | 방이 사라졌어요. 목록을 새로 고쳤어요. |
| `NICK_TAKEN` | 닉네임 모달 열기 (8.4) | 비밀번호 모달 닫고 닉네임 모달 열기. 입력한 비밀번호는 메모리에 보관해 재시도에 쓴다 | (8.4) |
| `NICK_FORMAT` | 닉네임 모달 열기(저장된 닉네임이 형식에 안 맞는 경우) | 닉네임 필드 오류 | 2~12자의 한글, 영문, 숫자만 쓸 수 있어요. |
| `NETWORK` | 로비 배너 | 모달 배너, 입력 유지 | 연결이 불안정해요. 다시 시도해 주세요. |
| `UNKNOWN` | 로비 배너 | 모달 배너 | 문제가 생겼어요. 잠시 후 다시 시도해 주세요. |

### 8.4 닉네임 겹침 모달 (`NICK_TAKEN`)

시안: `modal-nick-mobile.png`.

| 요소 | 규격 |
|---|---|
| 제목 | "닉네임이 겹쳐요" |
| 설명 | "이 방에 같은 닉네임이 있어요. 이 방에서만 쓸 닉네임을 정해 주세요. 프로필 닉네임은 그대로예요." |
| 필드 | 라벨 "이 방에서 쓸 닉네임". 프로필 닉네임 필드와 같은 규격(`maxlength="12"`, 카운터 "N/12", 정규식, 실시간 검사·상태 문구는 `profile.md` 5장) |
| 초기값 | 제안: 프로필 닉네임 + "2" (12자를 넘으면 앞 11자 + "2"). 열 때 전체 선택(바로 덮어쓸 수 있게) |
| 버튼 | "취소" / "입장"(primary). 활성 조건: 형식 맞음 |

- 제출: `joinRoom({ roomId, password: 보관한 비밀번호 또는 null, nickname: 새 값 })`. 프로필(localStorage)은 바꾸지 않는다. 쓴 닉네임은 sessionStorage `mushroom:room.nickname`에만 남는다(새로고침 재입장용).
- 다시 `NICK_TAKEN`: 필드 오류 "이 닉네임도 이 방에 있어요. 다른 닉네임을 써 주세요." + 전체 선택.
- 그 밖의 오류는 8.3 "모달에서" 열을 따른다. 잠금 방에서 `WRONG_PASSWORD`가 오면(그 사이 비밀번호가 바뀐 경우는 없지만 방어적으로) 닉네임 모달을 닫고 비밀번호 모달을 오류 상태로 다시 연다.
- 취소: 보관한 비밀번호를 지우고 로비로.

## 9. 오류 문구 전체 (로비)

| 코드 | 문구 |
|---|---|
| `ROOM_NAME_FORMAT` | 방 이름은 1~24자로 정해 주세요. 줄바꿈 같은 특수 문자는 쓸 수 없어요. |
| `PASSWORD_FORMAT` | 비밀번호는 4~32자로 정해 주세요. |
| `TOO_MANY_ROOMS` | 방은 동시에 3개까지 만들 수 있어요. 내가 만든 방이 비고 30분이 지나면 사라져요. |
| `WRONG_PASSWORD` | 비밀번호가 맞지 않아요. 다시 입력해 주세요. |
| `RATE_LIMITED` | 잠시 후 다시 시도해 주세요. |
| `ROOM_FULL` | 방이 가득 찼어요. 다른 방을 골라 주세요. |
| `ROOM_NOT_FOUND` | 방이 사라졌어요. 목록을 새로 고쳤어요. |
| `NICK_TAKEN` | (모달 제목) 닉네임이 겹쳐요 / (재시도 실패) 이 닉네임도 이 방에 있어요. 다른 닉네임을 써 주세요. |
| `NICK_FORMAT` | 2~12자의 한글, 영문, 숫자만 쓸 수 있어요. |
| `NETWORK` (입장) | 연결이 불안정해요. 다시 시도해 주세요. |
| `NETWORK` (만들기) | 방을 만들지 못했어요. 연결을 확인하고 다시 시도해 주세요. |
| `NETWORK` (첫 로딩) | 방 목록을 불러오지 못했어요. / 인터넷 연결을 확인한 뒤 다시 시도해 주세요. |
| `NETWORK` (갱신) | 연결이 불안정해요. 목록이 최신이 아닐 수 있어요. |
| `UNKNOWN` | 문제가 생겼어요. 잠시 후 다시 시도해 주세요. |
| (재입장 실패, `room.md` 1장) | 방에 다시 들어가지 못했어요. 목록에서 다시 골라 주세요. |
| `STORAGE` (정보) | 프로필을 이 브라우저에 저장하지 못했어요. 새로고침하면 다시 만들어야 해요. |

## 10. 접근성

- 랜드마크: `main#lobby`, 패널 `section[aria-labelledby]`. 목록 `ul` + `li`(기본 list 역할 유지, CSS `list-style: none`이 Safari에서 역할을 지우므로 `role="list"`를 명시).
- 입장 버튼 `aria-label`: "<방 이름> 입장, <공개 방|비밀번호 방>, N명 접속 중" / 가득 참: "<방 이름>, 가득 참" (`disabled`).
- 자물쇠/사람 아이콘은 `aria-hidden`. 정보는 메타 줄과 `aria-label`로 전달(모바일은 메타 줄이 숨겨지므로 `aria-label` 필수).
- 대비(WCAG AA 4.5:1): 행 이름 `ink`/`c1` 16.5, 메타 `w3`/`c1` 5.9, 가득 참 이름 `w4`/`c2` 7.8, "가득 참" 버튼 글자 `w3`/`c2` 4.7, 가득 참 배지 `r3`/`p1` 5.2, 개수 `w3`/`c1` 5.9. 비텍스트 대비(3:1): 행 테두리 `w4`/`c2` 7.8.
- Tab 순서: 꾸미기 → 새로고침 → 방 만들기 → (배너 안 버튼 없음) → 각 행 입장 버튼(위에서 아래). 목록 스크롤 틀은 `tabindex` 없음(버튼 포커스로 자동 스크롤).
- 터치 목표: 입장 44 높이, 꾸미기/새로고침 32 + 투명 확장 44.
- 모달: 5.2절.

## 11. 360 x 640 체크 항목 (QA)

- [ ] 가로 스크롤 없음. 로고 줄, 내 프로필 줄, 도구줄이 각각 한 줄.
- [ ] 페이지는 스크롤되지 않고 목록만 스크롤된다. 마지막 행의 아래 두께(4px)가 잘리지 않는다.
- [ ] 24자 방 이름이 말줄임되고 입장 버튼과 겹치지 않는다.
- [ ] 가득 찬 방은 배지가 분홍, 버튼이 "가득 참" 비활성.
- [ ] 5초마다 갱신돼도 스크롤 위치와 포커스가 유지된다. 탭을 숨기면 요청이 멈춘다.
- [ ] 방 만들기 모달이 위 64px에서 시작하고, 키보드가 올라와도 비밀번호 입력과 버튼이 보인다(실기기).
- [ ] 모달이 열린 동안 Tab이 모달 밖으로 나가지 않는다. Esc로 닫히면 포커스가 연 버튼으로 돌아간다.
- [ ] 잠금 방 + 닉네임 겹침: 비밀번호 입력 → 닉네임 모달 → 새 닉네임으로 비밀번호 재입력 없이 입장된다.
