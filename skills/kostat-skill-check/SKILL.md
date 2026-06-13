---
name: kostat-skill-check
description: "/skill-check 명령어로 스킬 상태 점검. Skill Lifecycle (candidate→trial→promoted→deprecated) 관리."
---

# kostat-skill-check

## 트리거
- 사용자가 `/skill-check` 입력 시 즉시 실행
- EOD 회고 시 Phase 3에서 자동 호출 가능

## 작업 흐름

### Step 1: 스킬 인벤토리 스캔
`kostat-agent-plugin/skills/` 디렉토리를 스캔하여 모든 SKILL.md 수집

### Step 2: 상태 평가

각 스킬을 아래 **Lifecycle** 기준으로 평가:

```
candidate  → 아이디어만 있는 상태 (SKILL.md 없음)
trial      → SKILL.md 작성, 1회 이상 사용
promoted   → 3회 이상 사용 + 오류 없음 + EOD 회고에서 효과 확인
deprecated → 3회 이상 실패 or 더 나은 스킬로 대체
```

### Step 3: 상태 리포트 출력

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 KOSTAT 스킬 상태 점검 — 2026-06-08
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Promoted (안정 운영)
| 스킬 | 사용 횟수 | 마지막 실행 | 비고 |
|------|----------|------------|------|
| kostat-po-update | N회 | - | 양호 |
| ... | | | |

🧪 Trial (실험 중)
| 스킬 | 사용 횟수 | 상태 |
|------|----------|------|
| ... | | |

💡 Candidate (아이디어)
| 스킬 | 설명 |
|------|------|
| ... | |

⚠️ Deprecated (폐기)
| 스킬 | 폐기 사유 | 대체 스킬 |
|------|----------|-----------|

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 종합
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 전체 스킬: N개
- Promoted: N개 — 안정적 운영 중
- Trial: N개 — 모니터링 필요
- Candidate: N개 — 개발 검토
- Deprecated: N개

💡 제안: [Trial 스킬 중 promoted 조건 충족한 항목 있으면 제안]
```

### Step 4: 승격/강등 제안

아래 기준으로 자동 제안:

| 상태 변화 | 조건 |
|----------|------|
| trial → promoted | 3회 이상 사용 + 최근 3회 오류 없음 |
| candidate → trial | SKILL.md 존재 + 1회 사용됨 |
| promoted → deprecated | 최근 5회 중 3회 실패 |
| trial → deprecated | 30일 이상 미사용 |

## 데이터 소스

| 정보 | 출처 |
|------|------|
| 스킬 목록 | `skills/*/SKILL.md` 존재 여부 |
| 사용 횟수 | `logs/` 디렉토리 로그 분석 (추정) |
| 오류 여부 | 로그 내 에러 패턴 검색 |
| 마지막 실행 | 로그 파일 수정 시간 기반 |

## 검증 체크리스트
- [ ] 모든 skills/ 디렉토리 스캔 완료
- [ ] lifecycle 기준 정확히 적용
- [ ] 승격/강등 제안 근거 명시
- [ ] 사용자 액션 필요 항목 확인 표시
