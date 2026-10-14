# 진행 상황

## 현재 상태 (사이클 4, 2026-10-15): 로그인 없는 채팅방 구조
- 흐름: 프로필(닉네임 + 꾸미기) → 로비(방 목록/만들기) → 방(맵 + 말풍선 + 채팅 로그)
- backend: 마이그레이션 20261015000000_rooms.sql — rooms/room_members/room_messages, RPC 7종(security definer), 비밀번호 bcrypt, 비공개 채널 RLS(realtime.messages), 채팅은 서버가 realtime.send로 송신. 로컬 PostgreSQL 16 스텁 환경에서 163건 + 동시성 7건 통과. 사이클 1~3의 characters 테이블 제거
- design: 프로필/로비/방 화면 설계, ui-kit 14~23절(모달, 방 목록, 자물쇠, 채팅 로그), 시안 docs/design/ref/c4/
- frontend: 로그인 제거, 익명 로그인, 로비/모달/채팅 로그, local 모드에 서버 규칙 재현, 끊김 시 자동 재입장(끊김마다 1회, 10초 간격)
- qa: E2E 31항목 local 모드 28 통과 / 0 실패 / 3 미검증 (docs/qa/qa-20261015-cycle4.md)
- 아트(블록 스타일)는 사이클 3 그대로

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
