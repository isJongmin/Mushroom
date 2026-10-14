# 테스트

## E2E (local 모드)

```sh
# 저장소 루트에서
python3 tests/e2e_local.py          # 전체 실행 (약 1분)
python3 tests/e2e_local.py -v       # 실패 항목의 traceback 포함
python3 tests/e2e_local.py --shots /경로/폴더   # 화면 스크린샷만 저장
```

- 요구: Python Playwright와 Chromium이 설치되어 있어야 한다. 테스트는 설치를 하지 않는다.
- 저장소 루트를 `python3 -m http.server`로 빈 포트에 띄우고, 종료 시 반드시 멈춘다.
- 외부 네트워크(Supabase, CDN)에 접속하지 않는다. local 모드(BroadcastChannel, localStorage)로 동작한다.
- 각 실행은 고유한 아이디/닉네임을 쓴다(`q` + hex 10자, `Qa` + hex 6자).
- 결과는 항목별 `PASS` / `FAIL` / `UNVERIFIED`로 출력한다. 종료 코드는 FAIL이 있으면 1.
- 셀렉터: `data-testid`, 상태: `window.__mushroom.getState()` (docs/handoff/frontend-20261014-client.md 5장).

### 항목

| 번호 | 내용 |
|---|---|
| 1 | 회원가입 -> 캐릭터 생성 -> 게임 진입, 새로고침 세션 복구 |
| 2 | 아이디 형식 오류, 비밀번호 8자 미만, 중복 아이디, 틀린 비밀번호 문구 |
| 3 | 닉네임 중복(대소문자 무시), 형식 위반 거부 (UI와 어댑터 직접 호출) |
| 4 | 계정당 캐릭터 1개 (재로그인 시 생성 화면 미경유, 어댑터 CHAR_EXISTS) |
| 5 | 두 탭 동시 접속: 서로의 존재, 이동 반영, 채팅 양방향 |
| 6 | XSS: 닉네임 생성 시도와 채팅의 `<img onerror>` (window.__xss, img 요소, DOM 문자열) |
| 7 | 채팅 80자 제한, 1초 쿨다운 |
| 8 | 탭 닫기 -> 다른 탭에서 제거 (6초 이내) |
| 9 | 로그아웃 -> 로그인 화면, 다른 탭에서 제거 |
| 10 | 전체 실행 중 콘솔/페이지 에러 0건 |
| 11 | 360x640 모바일: 가로 스크롤 없음, 터치 버튼 이동 (CDP 터치) |
| 12 | 로그인/로그아웃 3회 후 BroadcastChannel, setInterval, rAF, 화면 DOM 잔여 0 |

### 한계

- local 모드 테스트다. Supabase 모드(RLS, Auth, Realtime 실서버)는 검증하지 않는다.
- 항목 12는 리스너 개수와 JS 힙을 측정하지 않는다 (DevTools 필요).
- Chromium만 사용한다.
