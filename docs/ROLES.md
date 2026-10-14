# 역할 분장

| 역할 | 모델 | 정의 파일 | 쓰기 범위 |
|---|---|---|---|
| 메인 | 세션 모델 | - | docs/PROJECT.md, ARCHITECTURE.md, ROLES.md, STATUS.md |
| 프런트 | opus | .claude/agents/frontend.md | src/client/ |
| 백엔드 | opus | .claude/agents/backend.md | supabase/ |
| 아트 | haiku | .claude/agents/art.md | assets/ |
| 디자인 | haiku | .claude/agents/design.md | docs/design/ |
| QA | haiku | .claude/agents/qa.md | tests/, docs/qa/ |

## 운영 규칙
- 허브 구조: 모든 요청과 결과는 메인을 거친다. 팀끼리 직접 지시하지 않는다.
- 각 팀은 작업 후 docs/handoff/<역할>-YYYYMMDD-주제.md에 결과를 남긴다.
- 쓰기 범위 밖의 변경이 필요하면 직접 고치지 않고 handoff로 요청한다.
- 프런트/백엔드 결과물은 QA 검증을 거친 뒤 메인이 사용자에게 보고한다.
- 병렬 작업 시 프런트와 백엔드는 별도 worktree에서 진행한다.
