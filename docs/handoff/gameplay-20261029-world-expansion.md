# 외형·줄타기·사냥·연결 맵 확장

사용자 요청 7개를 완료되는 순서대로 main에 반영한다.

## 외형과 줄타기

- 모자의 전역 최하단 대신 열별 챙 경계와 3px 겹침을 사용해 헤어 틈 제거. 리본/검사 서클릿은 머리를 덮지 않음.
- 대머리, 레이어드 울프컷, 모호크, 포마드 추가. 직업별 상의/하의/신발/모자와 검집·활/화살통·지팡이·단검을 포함하는 20개 신규 파츠, 코디 총16개. 이전 PNG 유지.
- 줄타기는 원본 back 프레임을 바탕으로 올라간 팔/교대 손잡기와 이동 bob 적용. 정지하면 동작도 멈춤.

## 발사체와 리스폰

- 호스트/관전자 모두 진행 방향의 첫 접촉에서 화살·표창·마력탄을 제거하고 충돌 효과 표시.
- 호스트가 impact(id, x, y, job, mapId)를 전송. seq/발사 순서 기반 ID와 bounded cache로 몬스터 사망/패킷 순서 역전에도 발사체가 다시 생기지 않음. 피해는 호스트만 적용.
- 몬스터 생성 시 살아 있는 같은 맵 플레이어와 수평90단위 이상 이격(세로 피격 범위가 겹칠 때). 빈 자리가 없으면 1초 뒤 재시도. 최초 생성과 호스트 인계에도 적용.

## 맵과 미니맵

- forest(바람결 이끼숲) ↔ village(버섯마을) ↔ quarry(별빛 수정 채석장)의 순환 구조. 모든 맵 양끝에 왕복 가능한 포탈.
- 포탈 가까이에서 ↑/W 또는 나타나는 이동 버튼. 1.6초 전환 쿨다운, 진입 후2초 무적.
- 신규 두 맵: 독립 블록 지형/배경, 발판4개와 접근 가능한 밧줄4개, ground2+platform4 스폰 구역. 나무정령/수정게9프레임씩 추가하여 몬스터 총7종.
- 같은 방의 채팅은 공유. Presence/move/game 이벤트에 mapId를 넣어 맵별 플레이어 표시, 호스트 선출, 사냥/드롭을 분리. 구형/잘못된 mapId는 village.
- 맵 이동 시 발사체/드롭/물리/카메라 정리. 최근30초의 맵 스냅샷을 최대3개 보관하여 진입/호스트 변경 시 이전 몬스터 상태를 이어 받음.
- 우상단 접이식 미니맵: 현재 맵 이름, 발판·밧줄·포탈, 시야 범위, 나/동료/몬스터. 10Hz 갱신, 모바일 폭144px.

## 검증

- node tests/jobs.test.mjs
- node tests/projectiles-respawn.test.mjs
- node tests/profile-jobs.test.mjs
- node tests/map-protocol.test.mjs
- node tests/areas.test.mjs
- node tests/wardrobe-loader.test.mjs
- CANVAS_MODULE=<@napi-rs/canvas/index.js> node tests/avatar-hat.test.mjs
- python tests/avatar-wardrobe.test.py
- 모든 클라이언트 JS 문법/모듈 import 및 git diff --check.
- 실제 런타임 Canvas 합성으로 모자/새 직업 의상/줄타기, 신규 맵·몬스터 렌더 시안 확인.

Supabase SDK/DB/auth/RLS를 변경하지 않고 기존 Realtime JSON 사용자 필드만 확장한다. 실제 Supabase 방에서의 다인 접속/망 지연 실험은 별도이며 자동 Node 검사는 전송 정규화와 시뮬레이션 계약을 검사한다.
