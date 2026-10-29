# 테스트

## E2E (local 모드, 사이클 5 계약: 로그인 없음, 프로필 -> 로비 -> 방, 복셀 아트)

```sh
# 저장소 루트에서. 항목 24의 사본은 QA_SCRATCH 아래에 만든다 (없으면 시스템 임시 폴더)
QA_SCRATCH=/경로/스크래치 python3 -B tests/e2e_local.py          # 전체 실행 (약 6~8분)
QA_SCRATCH=/경로/스크래치 QA_FULL_BUILD=1 python3 -B tests/e2e_local.py --only 24,25   # 전체 결정성 재빌드 (약 15분, 한 번만)
python3 -B tests/e2e_local.py -v                                 # 실패 항목의 traceback 포함
python3 -B tests/e2e_local.py --only 1,8,16                      # 번호만 실행
python3 -B tests/e2e_local.py --shots /경로/폴더                  # 로비/방 스크린샷 + 꾸미기 (데스크톱 1280x800, 모바일 360x640)
```

- 요구: Python Playwright와 Chromium이 설치되어 있어야 한다. 테스트는 설치를 하지 않는다. numpy, Pillow는 항목 22, 33, 34에 필요하다.
- 저장소 루트를 `python3 -m http.server`로 빈 포트에 띄우고, 종료 시 반드시 멈춘다.
- 기본은 local 모드다. `LocalBrowser`가 모든 컨텍스트에 sessionStorage `mushroom.mode` = `'local'`을 미리 넣으므로 `?as=`, goto, 새로고침, 새 탭이 모두 local로 열린다. 외부 네트워크는 항목 37에서만 건드린다(Supabase, CDN이 차단됐는지 확인). 항목 38, 39의 supabase 측 검사는 `force_local=False`로 연 컨텍스트에서 한다.
- 실행 모드 규칙은 `src/client/backend/index.js`를 따른다: `?mode=local`(그 탭 sessionStorage 저장), sessionStorage `mushroom.mode`='local', hash가 정확히 `#local`이면 local. `?mode=supabase`는 저장을 지워 해제한다. 설정 값이 비어 있으면 local이다.
- 저장소 원본 `assets/`는 건드리지 않는다. build.py와 check.py는 사본에서만 실행한다.
- 결과는 항목별 `PASS` / `FAIL` / `UNVERIFIED`. 검사 줄마다 `OK` / `NG` / `UNV`를 찍는다. FAIL이 있으면 종료 코드 1.
- 셀렉터: `data-testid`, 상태: `window.__mushroom.getState()` (docs/handoff/frontend-20261015-rooms.md 4장).
- 사용자 구분: URL `?as=<이름>` (탭마다 다른 사용자). 같은 browser context 안의 페이지들은 같은 localStorage DB와 BroadcastChannel을 쓴다.

### 시간과 정원 조작 (실제 대기 대신 쓰는 방법, 각 항목에 명시)

| 대상 | 방법 |
|---|---|
| 방 만료 30분 | 항목 11: `mushroom.local.v4.db`의 `last_active_at`/`last_seen_at`을 31분 전으로 (`db_mut`, 같은 잠금 사용) |
| 비밀번호 1분 실패 창 | 항목 5: 실패 기록 `at`을 61초 전으로 |
| 같은 사용자 1초 채팅 제한 | 항목 9: 51개 전송 전에 `lastChat[uid]`를 0으로 (서버 규칙의 나머지는 그대로) |
| 20명 정원 | 항목 7: 활성 가짜 멤버 18명 주입 (방장 1 + 18 + 테스트 탭 B = 20). 가짜는 Presence가 없고 `last_seen`을 40초 뒤로 두어 테스트 동안 활성 유지 |
| 멤버 행 강제 삭제 (연결 끊김) | 항목 16: 서버가 멤버를 잃은 상황을 만든다 -> 하트비트 NOT_MEMBER 경로 |

## 항목 (39개)

| 번호 | 내용 |
|---|---|
| 1 | 첫 방문 -> 프로필(닉네임 형식 검사, 저장) -> 로비. 재방문은 로비부터 |
| 2 | 프로필 수정: 꾸미기 -> 저장 반영, Esc 취소는 미반영 |
| 3 | 공개 방 생성 -> 다른 사용자 로비에 5초 안에 표시, 인원 1/20, 입장 |
| 4 | 방 이름/비밀번호 형식 오류 문구, 서버 ROOM_NAME_FORMAT/PASSWORD_FORMAT, 방 3개 초과 TOO_MANY_ROOMS |
| 5 | 잠금 방: 자물쇠, WRONG_PASSWORD, 맞는 비번 입장, 6번째 RATE_LIMITED, 1분 뒤 복구 |
| 6 | 같은 방 닉네임 중복(대소문자 무시) -> NICK_TAKEN 모달 -> 다른 닉네임 입장. 다른 방은 허용 |
| 7 | 20명 제한: 21번째 ROOM_FULL (UI 배너 + 어댑터) |
| 8 | 방 안: 서로 보임, 이동, 말풍선, 양쪽 로그 1번씩, 입/퇴장 시스템 메시지, 인원 |
| 9 | 기록: 51개 보낸 뒤 새 입장자는 최근 50개, 오래된 순 (로그 DOM 기준) |
| 10 | 새로고침 -> 비밀번호 없이 재입장. 나가기 -> 로비, 잠금 방 재입장은 비밀번호 필요 |
| 11 | 만료: 활성 0명 30분 경과 방은 목록에서 사라짐, 29분은 유지 |
| 12 | 모달 접근성: focus trap, Esc 취소, 포커스 복귀, inert, 딤 클릭 무시 |
| 13 | 모바일 360x640: 로비/방/모달 가로 스크롤과 겹침, 로그 접힘 기본, 안 읽은 수, 펼침 크기 |
| 14 | 로비 폴링: 5초 갱신, 탭 숨김 중 정지, 다시 보이면 즉시 1회 + 재개 |
| 15 | 필수: 같은 계정 두 탭 -> 한 사람으로 집계, 중복 줄 없음, 한쪽 나가기 영향 |
| 16 | 필수: 연결 끊김 후 재접속 (멤버 행 삭제 -> 자동 재입장), 잠금 방은 로비로 |
| 17 | 탭 닫기 -> 상대 화면 제거(Presence), 퇴장 메시지 1번, 로비 인원은 활성 60초 규칙 |
| 18 | XSS: 닉네임 거부, 방 이름/채팅의 `<img onerror>` 문자열 표시 |
| 19 | 채팅 80자 제한, 1초 쿨다운, 서버 TEXT_FORMAT/RATE_LIMITED |
| 20 | 방 입퇴장 3회 후 BroadcastChannel/setInterval/rAF/.screen 잔여 0 (로비 기준값과 비교) |
| 21 | 레이아웃: 프로필/로비/방 가로 스크롤, 모드 칩 비겹침, 360 터치 이동 |
| 22 | 스무딩 렌더 품질: imageSmoothingEnabled 켬(high), 캐릭터 영역 비어 있지 않음, 고유 색 100 이상, 경계 블렌딩 0.25 이상 (계단 아님) |
| 23 | 에셋 로드: 4xx/5xx 0, 요청 실패 0, outline.json 요청 0, 요청 PNG는 manifest files 안, 조합 필요 레이어 전부 200, 맵 5 레이어 |
| 24 | 복셀 아바타 검사 (사본): `voxel/check.py --fast`, files 합 = PNG 65장, 원본 assets 불변. `QA_FULL_BUILD=1`이면 무옵션 재빌드까지 |
| 25 | 복셀 맵 검사 (사본): `voxel_map/check.py` 통과. `QA_FULL_BUILD=1`이면 맵 build 후 원본과 바이트 비교 + `--determinism` |
| 26 | 꾸미기 화면: 탭 7, 슬롯 반영, 프리셋 6, 앞(0/1 숨쉬기)/옆(2)/뒤(7), 걷기(3..6), 키보드 |
| 27 | 아바타 저장 7키, 기본값, 사이클 1 형식 정규화(저장값 유지), Presence 옛/깨진 값 |
| 28 | 애니메이션: walk 3..6, 인게임 idle 2, 왼쪽 dir (로컬과 원격) |
| 29 | 콘솔/페이지 에러 0 (전체 수집) |
| 30 | 정적 점검: 마이그레이션 (테이블 권한, RLS, password_hash 노출, RPC definer/search_path/anon, realtime 정책) |
| 31 | 정적 점검: 클라이언트 (innerHTML/eval, 비밀 값, private 채널, chat 송신, 프로필 저장 내용, config.js JWT role) |
| 32 | (a) manifest files 대체: files 키 없음/객체 아님/키 누락 -> 필수 레이어만 요청, 404 0, 캐릭터 정상, 경고 1회 (라우트 가로채기) |
| 33 | (b) 발 위치: me.y = 440, 장치 기준점 = 지면선, 발 아래 1~8단위 잔디, 잔디 앞 가장자리 8단위 이후, 22~26단위 흙 (화면 픽셀) |
| 34 | (c) 프리셋 6종: 프런트 합성 시트 vs `assets/_src/voxel/out/truth/presetN.png` (art check.py 허용치: 평균 6.0, 알파 MAE 2.0) |
| 35 | (d) 라벨/말풍선: 라벨 위 = 발바닥 선 +6, 꼬리 간격 = 4u+4 (머리 맨 위 기준), 라벨/말풍선 겹침 0, 캔버스 안 (P2/P3/모바일) |
| 36 | (e) 로딩 성능: 콜드 열기 -> 첫 캐릭터 프레임, 입장 클릭 -> 첫 프레임, 전송 바이트, 웜 재입장. 실패 기준 15s 초과 / 10MB 초과 |
| 37 | supabase 모드 기본 진입(쿼리·hash 없음): SUPABASE MODE 배지, CDN/supabase.co 차단 확인 -> 로비 오류 화면 + 다시 시도, pageerror 0 (콘솔 리소스 오류는 29번에서 제외) |
| 38 | `#local`과 `?mode=local` 진입 = LOCAL MODE 배지, 외부 요청 0건, pageerror 0 |
| 39 | 모드 스위치: `?mode=local` 저장/유지/`?mode=supabase` 해제, `#localx`·`#local&x` 비해당, `?mode=supabase#local`은 local, 수동 sessionStorage |

### 항목 31 비밀 값 판정 (config.js와 저장소 전체)

- config.js의 JWT: 디코드한 payload `role`이 `anon`이어야 한다. 그 밖의 role, 디코드 실패는 실패.
- config.js 밖의 어떤 텍스트 파일(docs 포함)에도 JWT(`eyJ...`)가 있으면 실패. `tests/`는 검사 대상이 아니다(규칙 문자열을 담고 있다).
- `sb_secret_`, `sk_live`, `sk_test` 문자열: docs를 제외한 모든 텍스트 파일에서 0건.
- `service_role`: 코드 파일(js, html, css, json, sql, py)의 비주석 줄에서만 0건. 주석(`//`, `/*`, `*`, `--`, `#`로 시작하는 줄)과 문서 산문의 언급은 허용한다. 주석 줄에 금지 문자열이 있어도 실패하지 않는다.
- 판정 로직을 바꾼 뒤에는 사본(스크래치)에 `service_role` JWT, `sb_secret_`, 주석 밖 `service_role`을 넣어 실패하는지 확인한다.

### 항목 37 판정 (차단 환경 전제)

- 외부 요청(`cdn.jsdelivr.net`, `supabase.co`)이 실패 기록되지 않으면 차단 확인이 안 된 것이므로, 오류 화면 검사는 UNVERIFIED(None)로 남긴다.
- SUPABASE MODE 배지: 현재 화면 코드(`profile.js`, `lobby.js`)는 `app.mode === 'local'`일 때만 배지를 붙인다. supabase 모드에서는 배지가 DOM에 없다. 항목 37은 요청 사양("쿼리 없이 열면 SUPABASE MODE 배지가 보인다")대로 검사하므로 이 부분이 FAIL로 나온다. 설계 결정이 나올 때까지 이 FAIL은 스펙 불일치로 본다.

### 사이클 5 판정 기준 (복셀 아트, 항목 22/33/34/35/36)

- 22 스무딩: 캐릭터 프레임 그리기 호출마다 `imageSmoothingEnabled`가 true여야 한다. 캐릭터 마스크(그리기 전후 차이 픽셀)의 경계 픽셀 중 내부 팔레트에 없는 색 비율(블렌딩)이 0.25 이상이어야 한다. 음성 대조군(합성 상자에 NEAREST 2/3 축소)은 블렌딩 0.0, 고유 색 6개로 실패, BICUBIC/LANCZOS는 0.8 이상으로 통과한다.
- 33 발 위치: 지면선은 장치 y = round((440 - camY) x k). 기준점 장치 y(프레임 dy + 180 x k/1.5)와 같아야 한다(허용 1px). 잔디 앞 가장자리(녹색 비율 0.5 미만 첫 행)는 발 아래 8단위 이후여야 한다. 실측은 14단위(문서 6단위와 다름, art-20261015-voxel-map 4장과 frontend 2장의 446 기준과 어긋남 → 보고서 참고).
- 34 프리셋: art `check.py`와 같은 식(`diff_stats`)으로 평균 6.0 이하, 알파 MAE 2.0 이하.
- 35 라벨/말풍선: 라벨 위 = 발바닥 선 + 6(허용 1.5), 꼬리 간격 = HEAD.gap x u + tipGap(허용 1.5), 라벨/말풍선끼리 겹침 0. 머리 맨 위는 장면 안 페이지 안에서 `avatar.js` headTop을 같은 식으로 계산한다.
- 36 로딩: 콜드 열기 -> 첫 캐릭터 프레임 15초 이하, 콜드 자산 전송 10MB 이하가 실패 기준. 콜드 = 새 페이지 + CDP `Network.setCacheDisabled`(같은 컨텍스트의 localStorage는 유지).

### 한계

- local 모드 테스트다. Supabase 모드(실 익명 로그인, 실 Realtime 채널 구독 거부, RLS 우회 시도, `realtime.send`의 RLS 통과)는 검증하지 않는다 (항목 30이 UNVERIFIED로 남긴다). 항목 37은 supabase 모드의 진입과 차단 시 동작만 본다. 외부망이 열린 환경에서 실서버로 방 생성/입장/채팅을 확인하는 스모크는 별도 작업이다.
- 실제 네트워크 단절은 재현하지 않는다. local에는 끊김 경로가 없어서 항목 16은 멤버 행 삭제로 NOT_MEMBER 경로만 본다.
- 항목 12: IME 조합 중 Esc, Safari 15.4 미만 inert 대체 경로는 UNVERIFIED. 항목 20: 리스너 개수와 JS 힙은 DevTools 없이 측정하지 않는다 (UNVERIFIED).
- Chromium만 사용한다. dpr 3, 실기기 소프트 키보드, Safari/Firefox는 미검증.

## 협동 사냥·직업 회귀 검사

Node.js 22 이상에서 저장소 루트 기준:

```sh
node tests/jobs.test.mjs
node tests/profile-jobs.test.mjs
# Canvas 합성 검사: @napi-rs/canvas 설치 경로를 지정 (기존 게임 런타임 의존성 추가 없음)
CANVAS_MODULE=/absolute/path/to/@napi-rs/canvas/index.js node tests/avatar-hat.test.mjs
```

브라우저 E2E를 대신하는 검사는 아니며, 충돌·전송 형식·프로필 호환·재생성 타이밍과 Canvas 합성 회귀를 검사한다.

## 연결 맵·외형 확장 검사

```sh
node tests/projectiles-respawn.test.mjs
node tests/map-protocol.test.mjs
node tests/areas.test.mjs
node tests/wardrobe-loader.test.mjs
python tests/avatar-wardrobe.test.py
```

발사체 소멸/확정 이벤트 순서, 안전 리스폰 재시도, 맵별 패킷 형식, 포탈 왕복/밧줄 도달, 미니맵 좌표와16개 코디 로더를 검사한다.
