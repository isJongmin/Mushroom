# QA 2026-10-27: 실제 Supabase 설정 + local 모드 강제 스위치 (테스트 보정)

- 대상 handoff: `docs/handoff/frontend-20261027-supabase-config.md` (QA 확인 항목 1~3)
- 대상 코드: `src/client/config.js`(실키, anon JWT), `src/client/backend/index.js`(모드 스위치) — 소스 수정 없음
- 수정한 파일 (tests/만): `tests/e2e_local.py`, `tests/README.md`, 결과 `docs/qa/qa-20261027-supabase-config.md`
- 실행: `QA_SCRATCH=<스크래치> python3 -B tests/e2e_local.py` (전체 39개 항목, 약 6분), 로그는 스크래치에 보관
- 환경: 이 컨테이너는 supabase.co와 CDN(cdn.jsdelivr.net)에 접근 불가. 외부망 스모크는 하지 않았다.

## 요약

| 구분 | 개수 |
|---|---|
| PASS | 33 |
| FAIL | 1 (37번: SUPABASE MODE 배지 검사, 스펙 불일치) |
| UNVERIFIED | 5 (12, 20, 24, 25, 30) |

- 기존 실패 원인(config 실키로 페이지가 supabase 모드로 열림)은 해소됐다. 항목 1~11, 13~19, 21~23, 26~28, 32~36이 모두 PASS다. 29번(콘솔 에러 0건)과 31번(정적 점검)도 PASS다.
- 요청한 것 중 남은 실패는 한 가지다. 쿼리 없이 열었을 때 SUPABASE MODE 배지가 보인다는 사양이 현재 코드와 맞지 않는다 (아래 "스펙 불일치").

## 결과표

| 번호 | 항목 | 결과 | 재현 절차 / 근거 |
|---|---|---|---|
| 1~11 | 사이클 4 흐름(프로필, 방, 중복, 정원, 채팅, 재입장, 만료) | PASS | `python3 -B tests/e2e_local.py --only 1,...` 또는 전체 실행. 모든 페이지는 `LocalBrowser`가 붙인 local 강제 init script로 열린다. |
| 12 | 모달 접근성 | UNVERIFIED | IME 조합 중 Esc, Safari 15.4 미만 inert 대체 경로는 Chromium에서 재현 불가 (기존과 같음). |
| 13~19 | 모바일 레이아웃, 폴링, 두 탭, 끊김 재접속, 탭 닫기, XSS, 채팅 제한 | PASS | 전체 실행. 16번 재접속은 멤버 행 삭제로 NOT_MEMBER 경로를 확인했다. |
| 20 | 리소스 누수 | UNVERIFIED | 리스너 개수와 JS 힙은 DevTools 없이 측정하지 않는다 (기존과 같음). |
| 21~23 | 레이아웃, 스무딩 렌더, 에셋 로드 | PASS | 전체 실행. |
| 24, 25 | 복셀 아바타/맵 결정성 재빌드 | UNVERIFIED | `QA_FULL_BUILD=1 python3 -B tests/e2e_local.py --only 24,25` (약 15~20분)를 한 번 따로 돌려야 한다. 이번에는 생략. |
| 26~28 | 꾸미기 화면, 저장 정규화, 애니메이션 | PASS | 전체 실행. |
| 29 | 콘솔/페이지 에러 0건 | PASS | 전체 실행. 37번의 CDN 리소스 오류는 별도 수집이라 여기에 들어가지 않는다. |
| 30 | 정적 점검: 마이그레이션 | UNVERIFIED | 파일 검사는 통과했지만 "배포 설정(익명 로그인, public access)"과 "실제 Supabase 적용(RLS 우회 시도)" 두 검사는 외부망이 필요해 미검증으로 남긴다. |
| 31 | 정적 점검: 클라이언트 (비밀 값, config JWT) | PASS | 아래 "항목 31 판정 기준" 참조. 실제 config.js JWT 1개, role=anon. 위반 0건. |
| 32~36 | 아바타 대체, 발 위치, 프리셋, 라벨, 로딩 성능 | PASS | 전체 실행. handoff가 말한 35번 재확인 항목도 PASS. |
| 37 | supabase 모드 기본 진입 (쿼리·hash 없음) | FAIL (스펙 불일치) | 아래 "37번 재현 절차" 참조. 나머지 검사 (mode=supabase, 오류 화면, 다시 시도, 다시 시도 클릭 후 유지, pageerror 0, CDN 차단 기록)는 통과. |
| 38 | `#local`, `?mode=local` 진입 = LOCAL MODE, 외부 요청 0건, pageerror 0 | PASS | 두 진입 모두 mode=local, LOCAL MODE 배지, 외부 요청 0건, pageerror 0. |
| 39 | 모드 스위치 규칙 (10개 검사) | PASS | `?mode=local` 저장과 새로고침 유지, `?mode=supabase` 해제(sessionStorage 삭제), `#localx`와 `#local&x`는 supabase, `?mode=supabase#local`은 local, 수동 sessionStorage는 local. |

## 항목 31 판정 기준 (이번에 바꾼 내용)

- config.js의 JWT: 디코드한 payload `role`이 `anon`이어야 한다. 다른 role이나 디코드 실패는 실패.
- config.js 밖의 텍스트 파일(docs 포함)에 JWT가 있으면 실패. `tests/`는 검사 대상이 아니다.
- `sb_secret_`, `sk_live`, `sk_test`: docs를 제외한 모든 텍스트 파일에서 0건.
- `service_role`: 코드 파일(js, html, css, json, sql, py)의 비주석 줄에서만 0건. 주석과 문서 산문의 언급은 허용. config.js에 있는 기존 주석 "service_role(secret) 키는 ... 넣지 않는다"는 주석이라 실패로 잡지 않는다. 주석까지 막으면 이 안내 문구를 지워야 하므로 허용으로 정했다.
- 기존 "config.js 키 비어 있음" 검사는 제거했다. 설정을 비우면 local 모드로 돌아가는 것이 의도된 동작이기 때문이다.

이 판정 로직은 스크래치 사본에서 음성 시험으로 확인했다. 사본에 `service_role` JWT를 config.js에 넣고, anon JWT를 `src/client/extra.js`와 `docs/neg-jwt.md`에 넣고, `sb_secret_`을 `src/client/main2.js`에 넣고, 코드 줄에 `service_role`을 넣었더니 모두 실패로 잡혔다(상세 문구에 각각 표시). 원본 저장소는 건드리지 않았다.

## 37번 재현 절차 (FAIL, 스펙 불일치)

1. 로컬 정적 서버를 저장소 루트에 띄운다 (`python3 -m http.server`).
2. 새 브라우저 컨텍스트(강제 스위치 없음)에서 쿼리와 hash 없이 `http://127.0.0.1:<port>/`를 연다.
3. 결과: `window.__mushroom.getState().mode === 'supabase'`는 맞다. 그러나 `[data-testid="mode-badge"]` 요소가 DOM에 없다.
4. 원인: `src/client/screens/profile.js:126`과 `src/client/screens/lobby.js:83`이 `if (app.mode === 'local') app.placeModeBadge(...)`로만 배지를 붙인다. `src/client/main.js:22`는 supabase 모드에서 배지를 `hidden`으로 만든다. 두 곳 모두 배지를 supabase 모드에서 숨긴다.
5. 프로필 저장 후 로비로 가도 같은 결과다. 로비 오류 화면, 다시 시도 버튼, pageerror 0은 모두 정상이다.

판단: `docs/handoff/frontend-20261027-supabase-config.md`는 "supabase 모드 칩은 기존 설계대로 숨김. 표시가 필요하면 디자인 결정"이라고 적고 디자인 확인을 요청했다. 요청 사양은 "쿼리 없이 열면 SUPABASE MODE 배지가 보인다"이다. 두 문서가 충돌하므로 **설계 결정이 필요하다**. 소스는 고치지 않았다. 결정 전까지 37번의 배지 검사는 FAIL로 둔다.
- 배지를 보이게 하기로 하면: 프로필/로비/방에서 supabase 모드일 때도 배지를 붙이도록 `profile.js`, `lobby.js`, `room.js`, `main.js`를 고친다. 그 뒤 37번은 그대로 PASS가 된다.
- 숨기기로 하면: 37번의 배지 검사 두 줄을 "supabase 모드에서 배지 없음"으로 바꾼다. 테스트를 고쳐야 할 일이다.

## 37번의 전제 (차단 환경)

- 외부 요청(`cdn.jsdelivr.net`, `supabase.co`)이 실패로 기록되어야 오류 화면 검사를 한다. 이번 실행은 차단되어 해당 검사가 실행됐다.
- 외부망이 열린 환경에서는 오류 화면 검사가 UNVERIFIED로 남는다. 그 환경의 실서버 스모크는 별도 작업이다 (handoff QA 항목 4).

## 기준선 (수정 전)

- 수정 전 테스트를 실키 config로 돌리면 supabase 모드로 열려 항목 1~16이 "로비 목록 준비 안 됨 (현재 error)"로 실패했다. handoff의 (c) 표와 일치한다. 기준선 실행은 16번째 항목에서 중단했다(전체 실행이 아니므로 기준선 수치로 쓰지 않는다).

## 남은 일

- 항목 24, 25의 결정성 재빌드를 `QA_FULL_BUILD=1`로 한 번 돌린다.
- 외부망이 되는 환경에서 실서버 스모크 (익명 로그인, 방 생성/입장/채팅)를 한다. 이 컨테이너에서는 불가능하다.
- 37번 배지 결정 (위 "판단" 참조).
- 백엔드 확인 항목(`20261015000000_rooms.sql` 적용, anonymous sign-ins 켜기, Realtime private 채널)은 이 결과에 포함되지 않는다.
