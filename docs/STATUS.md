# 진행 상황

## 최신 아트 (2026-10-29, 사용자 승인 완료)

- 작업 브랜치: `art/fine-pixel-preview`. 사용자 승인으로 캐릭터 다양화·3D 블록 몬스터 변경을 `main`에 반영한다.
- 캐릭터: 기존 코디 6개와 파츠 보존. 새 헤어 3종, 상의 2종, 하의 1종, 모자 1종과 추천 코디 6개 추가(총12개). 피부3종/표정4종을 조합한다.
- 프로필: 기본6개 + native details로 추가6개 펼치기. 추가 썸네일은 펼칠 때 합성한다.
- 몬스터: 과거 2D 필터 결과를 대신해 5종을 독립적인 3D 블록 모델로 제작. 현재 원본은 `assets/_src/voxel_mob/`, 49개 이동/피격/사망 프레임. 전투수치와 기존 frame/anchor 계약 유지.
- 최신 실제 스프라이트 시안: `assets/_src/voxel-variety-review/`. 이전 승인 전 시안은 `assets/_src/fine-pixel-review/`에 보존. 상세 검증·재생성 방법은 `docs/handoff/art-20261029-avatar-variety.md`, `art-20261029-voxel-mobs.md` 참고.
- 브라우저 E2E는 실행환경에 Chromium이 없고 설치 다운로드가 실패하여 미실행. 에셋·기하·정규화·소스 검증과 E2E 명세 업데이트는 별도로 수행한다.

## 이전 상태 (사이클 4, 2026-10-15): 로그인 없는 채팅방 구조
- 흐름: 프로필(닉네임 + 꾸미기) → 로비(방 목록/만들기) → 방(맵 + 말풍선 + 채팅 로그)
- backend: 마이그레이션 20261015000000_rooms.sql — rooms/room_members/room_messages, RPC 7종(security definer), 비밀번호 bcrypt, 비공개 채널 RLS(realtime.messages), 채팅은 서버가 realtime.send로 송신. 로컬 PostgreSQL 16 스텁 환경에서 163건 + 동시성 7건 통과. 사이클 1~3의 characters 테이블 제거
- design: 프로필/로비/방 화면 설계, ui-kit 14~23절(모달, 방 목록, 자물쇠, 채팅 로그), 시안 docs/design/ref/c4/
- frontend: 로그인 제거, 익명 로그인, 로비/모달/채팅 로그, local 모드에 서버 규칙 재현, 끊김 시 자동 재입장(끊김마다 1회, 10초 간격)
- qa: E2E 31항목 local 모드 28 통과 / 0 실패 / 3 미검증 (docs/qa/qa-20261015-cycle4.md)

## 사이클 5 (2026-10-15): 3D 복셀 조명 렌더 아트
- art: 캐릭터를 3D 복셀 모델 + 조명(키라이트, AO, 소프트 섀도, 베벨, 림)으로 렌더. 같은 7개 파츠 키·id·프리셋 유지(저장된 프로필 호환). 144x192 프레임, 8프레임(앞 숨쉬기 2, 옆, 걷기 4, 뒤), 13레이어(그림자 레이어 source-atop), manifest `files`로 레이어 존재 목록 제공. 소스 assets/_src/voxel/
- map: 같은 렌더러로 버섯마을 낮 맵 5레이어(sky, clouds, far, mid, ground) WebP 무손실 1.5MB. 소스 assets/_src/voxel_map/
- frontend: 레이어 blend 합성(아트 기준 구현과 평균 오차 0.04/255 이내), 스무딩 렌더, 월드 단위 좌표, 지연 로드, files 없을 때 필수 레이어만 요청
- qa: E2E 36항목 31 통과 / 0 실패 / 5 미검증, 전체 결정성 재빌드 통과, 콜드 입장 첫 프레임 약 0.6초·전송 1.9MB (docs/qa/qa-20261015-cycle5.md)
- 낮음: 모바일 채팅 로그 펼침 시 말풍선 가림, 데스크톱 채팅 로그가 왼쪽 건물·캐릭터 일부 가림, 말풍선이 가로등과 겹치는 경우, ui-kit.css의 canvas pixelated 규칙(프런트 style.css에서 덮어씀) 정리 필요

## 사용자 작업 필요
1. Supabase 프로젝트 생성 → supabase/README.md 순서대로 마이그레이션 4개 적용
2. Authentication에서 "Allow anonymous sign-ins" 켜기, Realtime 설정에서 "Allow public access" 끄기(권장)
3. src/client/config.js에 Project URL과 anon key 입력 (service_role key 금지)
4. setup/agent-team 브랜치를 main에 병합 후 GitHub Pages 활성화

## 미검증
- Supabase 실환경 전체: 익명 로그인, RPC, 비공개 채널 권한, realtime.send가 비공개 채널로 실제 전달되는지(안 되면 README의 대안 적용 필요)
- 모달 접근성 일부(IME 중 Esc, 구형 Safari inert), 리스너/힙 정밀 측정
- Safari/Firefox, 실기기

## 알려진 문제 / 한계
- [중간] 같은 방 멤버는 move/presence와 가짜 chat 이벤트를 보낼 수 있음(받는 쪽에서 서버 송신과 구분 불가). 저장되는 기록은 서버가 쓴 것만
- [중간] 익명 계정 무제한 생성 → 방 3개/비밀번호 시도 제한 우회 가능. 사용자 늘면 CAPTCHA
- [낮음] 브라우저 데이터 삭제 시 프로필 소실
- [낮음] 디자인 문서 정리: 모바일 채팅 로그 위치(room.md 4.2, ui-kit 23절)를 구현 값으로 갱신, 내 말풍선 표시 시점(RPC 성공 후)과 탭 닫기 시 처리(untrack만) 반영
- [낮음] 측면 얼굴/긴 머리 뒷모습/걷기 다리 구분 (아트)

## 다음 작업 후보
1. Supabase 연결 후 실환경 검증
2. chat 위조 차단 강화(realtime.messages insert 정책에서 chat 이벤트 금지 가능 여부 확인)
3. 방별 맵 테마, 이모트, 아트 다듬기
