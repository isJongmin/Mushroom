# 진행 상황

## 현재 상태 (사이클 3, 2026-10-14): 마인크래프트풍 블록 스타일로 전면 재제작 완료
- art: 블록 아바타 파츠 43장(피부 3, 얼굴 4, 머리 8, 모자 5+없음, 상의 6, 하의 5, 신발 4), 프리셋 6종, 7프레임 시트(앞/옆/걷기 4/뒤), 블록 맵 5레이어 패럴랙스. 소스 assets/_src/block/ (결정적 빌드)
- design: 블록 UI 키트(docs/design/ui-kit.css), 스타일 가이드 v3, 화면 설계 v3
- backend: 아바타 7키(skin, hair, face, top, bottom, shoes, hat) 마이그레이션 20261014000200_avatar_v3.sql (기존 행 자동 변환)
- frontend: 레이어 합성 + 바깥 외곽선 렌더러, 걷기 애니메이션, 탭/슬롯/프리셋/회전 미리보기 생성 화면, 블록 UI, 구 형식 데이터 호환
- qa: E2E 21항목 local 모드 21/21 통과 (docs/qa/qa-20261014-cycle3.md)

## 이전 사이클
- 사이클 1: SVG 아트, 기본 클라이언트, 스키마/RLS (폐기된 아트는 git 이력에 있음)
- 사이클 2: 48px 픽셀아트 (사용자 평가로 폐기)

## 사용자 작업 필요
1. Supabase 프로젝트 생성 → supabase/README.md 순서대로 마이그레이션 3개 적용, "Confirm email" 끄기
2. src/client/config.js에 Project URL과 anon key 입력 (service_role key 금지)
3. setup/agent-team 브랜치를 main에 병합 후 GitHub Pages 활성화 (Settings > Pages > main / root)

## 미검증
- Supabase 모드 전체 (Auth, RLS 실제 동작, Realtime, 재연결)
- Safari/Firefox, 실기기 터치와 소프트 키보드, 한글 IME

## 알려진 문제
- [중간] config가 비어 있으면 배포 사이트가 local 모드로 동작 (다른 사용자와 맵 공유 안 됨)
- [낮음] 측면 얼굴이 작고, 긴 머리 뒷모습이 판처럼 보이며, 걷기 시 두 다리 구분이 약함
- [낮음] 표정 변화(말할 때 등)와 idle 숨쉬기 없음
- [낮음] 랜덤 스폰 위치로 캐릭터가 겹칠 수 있음
- [수용] Broadcast 발신자 위장 가능 (ARCHITECTURE 알려진 한계)

## 다음 작업 후보
1. Supabase 연결 후 Supabase 모드 검증
2. 측면/걷기 다듬기, 표정, idle 애니메이션
3. 전직·몬스터 사냥 설계 (위치 서버 검증 재설계 포함)
