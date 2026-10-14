# 아키텍처

## 디렉터리 구조 (계획)
```
src/client/      프런트엔드 (frontend)
supabase/        마이그레이션, Edge Function, 정책 (backend)
assets/          SVG 에셋 (art)
tests/           테스트 (qa)
docs/            문서
  design/        스타일 가이드, 화면 설계 (design)
  qa/            QA 결과 (qa)
  handoff/       역할 간 요청/결과 메모
```

## 확정된 결정
- 호스팅은 GitHub Pages, 백엔드는 Supabase.
- 계정당 캐릭터 1개, 닉네임 중복 불가는 DB 제약(unique)으로 강제한다.

## 미결 사항 (사용자 결정 필요)
1. 인증 방식
   - 권장: Supabase Auth 사용. 사용자는 아이디/비밀번호로 로그인하되, 아이디는 내부적으로 `<아이디>@mushroom.local` 형태의 이메일로 매핑한다. 해싱과 세션을 Supabase가 처리한다.
   - 대안: 테이블에 직접 자격증명을 저장하는 완전 자체 인증. GitHub Pages는 정적 호스팅이라 서버 비밀을 둘 곳이 없고, 해싱/검증을 Edge Function으로 직접 구현해야 해서 비용과 위험이 크다.
   - 참고: 이메일 인증을 끄고 `.local` 도메인을 쓰면 비밀번호 재설정 메일이 동작하지 않는다.
2. 프런트 기술: 바닐라 JS + Canvas, Phaser, 또는 PixiJS. 빌드 도구 사용 여부.
3. 실시간 방식: Supabase Realtime(Broadcast/Presence) 사용 여부. 이동/채팅은 DB 쓰기 없이 Broadcast로 처리하는 것을 기본안으로 한다.

## 데이터 모델 (초안, backend가 확정)
- characters: user_id (unique, auth.users 참조), nickname (unique), avatar (jsonb), created_at
