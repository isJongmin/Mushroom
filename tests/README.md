# 테스트

## E2E (local 모드, 사이클 3 계약)

```sh
# 저장소 루트에서. 항목 17/18의 사본은 QA_SCRATCH 아래에 만든다 (없으면 시스템 임시 폴더)
QA_SCRATCH=/경로/스크래치 python3 -B tests/e2e_local.py     # 전체 실행
python3 -B tests/e2e_local.py -v                          # 실패 항목의 traceback 포함
python3 -B tests/e2e_local.py --shots /경로/폴더           # 화면 스크린샷만 저장 (데스크톱/모바일 6장 + 게임)
```

- 요구: Python Playwright와 Chromium이 설치되어 있어야 한다. 테스트는 설치를 하지 않는다. Pillow, numpy는 항목 13, 17, 18에 필요하다.
- 저장소 루트를 `python3 -m http.server`로 빈 포트에 띄우고, 종료 시 반드시 멈춘다.
- 외부 네트워크(Supabase, CDN)에 접속하지 않는다. local 모드(BroadcastChannel, localStorage)로 동작한다.
- 저장소 원본 `assets/`는 건드리지 않는다. build.py와 check.py는 사본에서만 실행한다.
- 결과는 항목별 `PASS` / `FAIL` / `UNVERIFIED`로 출력한다. 종료 코드는 FAIL이 있으면 1.
- 셀렉터: `data-testid`, 상태: `window.__mushroom.getState()` (docs/handoff/frontend-20261014-block.md 4장).

### 항목

| 번호 | 내용 |
|---|---|
| 1 | 가입 -> 머리 탭 슬롯 선택 -> 게임 진입, 7키 저장, 새로고침 복구 |
| 2 | 아이디 형식 오류, 비밀번호 8자 미만, 중복 아이디, 틀린 비밀번호 문구 |
| 3 | 닉네임 중복(대소문자 무시), 형식 위반 거부 (UI와 어댑터 직접 호출) |
| 4 | 계정당 캐릭터 1개 (재로그인 시 생성 화면 미경유, 어댑터 CHAR_EXISTS) |
| 5 | 두 탭 동시 접속: 서로의 존재, 이동 반영, 채팅 양방향 |
| 6 | XSS: 닉네임 생성 시도와 채팅의 `<img onerror>` |
| 7 | 채팅 80자 제한, 1초 쿨다운 |
| 8 | 탭 닫기 -> 다른 탭에서 제거 (6초 이내) |
| 9 | 로그아웃 -> 로그인 화면, 다른 탭에서 제거 |
| 10 | 전체 실행 중 콘솔/페이지 에러 0건 |
| 11 | 360x640 모바일: 가로 스크롤 없음, 캔버스 360x508, 터치 버튼 이동 |
| 12 | 로그인/로그아웃 3회 후 BroadcastChannel, setInterval, rAF, 화면 DOM 잔여 0 |
| 13 | 픽셀 선명도: 1280x800 / 1920x1080 / 360x640에서 아트 블록 정사각, 색 전환 격자 정렬 (HUD와 라벨 마스크) |
| 14 | 애니메이션: 이동 중 walk(frame 2..5), 정지 후 idle(frame 1), 왼쪽 dir=left (로컬과 원격) |
| 15 | 에셋 로드: 실패 0, manifest 200, 아바타 레이어 43, 맵 5, PNG 48 |
| 16 | 레이아웃: 가로 스크롤 없음, LOCAL MODE 비겹침, 닉네임 라벨 캔버스 안, 모바일 하단 여백 |
| 17 | 에셋 빌드 재현성: 사본에서 build.py -> assets/avatar, assets/map 바이트 동일 (2회 결정성) |
| 18 | `assets/_src/block/check.py` 통과 (사본에서 실행) |
| 19 | 생성 화면: 탭 7개, 슬롯 선택 반영, 프리셋 6종, 앞/옆/뒤, 걷기, 탭/슬롯 키보드 |
| 20 | 저장 avatar 정확히 7키, getState와 localStorage 원본이 선택값과 일치 |
| 21 | 호환: 사이클 1 저장값(5키, eyes, 옛 id) 정규화, 저장값 유지, Presence 옛 형식/깨진 값 정규화 |

### 한계

- local 모드 테스트다. Supabase 모드(RLS, Auth, Realtime 실서버)는 검증하지 않는다.
- 항목 12는 리스너 개수와 JS 힙을 측정하지 않는다 (DevTools 필요).
- 항목 13은 말풍선 픽셀 정렬을 검사하지 않는다 (2px 격자 UI). 말풍선은 스크린샷으로 확인한다.
- Chromium만 사용한다.
