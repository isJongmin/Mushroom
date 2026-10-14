# 진행 상황

## 완료 (사이클 1, 2026-10-14)
- 팀 정의(.claude/agents/), 문서 뼈대, 설계 결정 확정 (ARCHITECTURE.md)
- design: 스타일 가이드, 화면 설계 3종 (docs/design/)
- backend: characters 테이블, RLS, 컬럼 권한, is_nickname_taken RPC (supabase/migrations/). 로컬 PostgreSQL 16에서 49건 검증 통과
- art: 아바타 파츠 16종 + manifest, 맵 배경 (assets/)
- frontend: 로그인/생성/게임 화면, supabase/local 두 모드, Canvas 렌더, 실시간 이동·채팅 (index.html, src/client/)
- qa: E2E 12항목 (tests/e2e_local.py) local 모드 12/12 통과, 정적 점검 이상 없음 (docs/qa/qa-20261014-cycle1.md)

## 사용자 작업 필요
1. Supabase 프로젝트 생성 → supabase/README.md 순서대로 마이그레이션 적용, "Confirm email" 끄기
2. src/client/config.js에 Project URL과 anon key 입력 (service_role key 금지)
3. GitHub Pages 활성화 (Settings > Pages > main 브랜치 / root)

## 미검증
- Supabase 모드 전체 (Auth, RLS 실제 동작, Realtime, 재연결)
- Safari/Firefox, 실제 모바일 터치, 한글 IME 조합 중 Enter

## 알려진 문제 (다음 사이클)
- [중간] config가 비어 있으면 배포 사이트가 조용히 local 모드로 동작 (배지로만 표시). Supabase 연결 후 배포용 local 모드 차단 검토
- [낮음] 모바일에서 닉네임 라벨 하단 약 3px 잘림, 게임 하단 빈 영역, LOCAL MODE 배지가 생성 카드와 겹침
- [낮음] 아바타는 정면 파츠 (3/4뷰는 디자인 좌표 재정의 필요)
- [수용] Broadcast 발신자 위장 가능 (ARCHITECTURE 알려진 한계)

## 다음 작업 후보
1. Supabase 연결 후 QA로 Supabase 모드 검증
2. 모바일 UI 문제 수정
3. 아바타 커스터마이징 확장 (파츠 추가, 3/4뷰)
