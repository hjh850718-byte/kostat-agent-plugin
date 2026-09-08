---
name: kostat-eod-retrospective
description: "EOD KPT 회고록 자동 생성. 트리거: '업무끝', 'EOD', '회고', 'KPT'. Mode: fanout | standalone."
---

# kostat-eod-retrospective — Level 6 Fan-out

## 실행 모드 선택

| 모드 | 동작 | 사용场景 |
|------|------|----------|
| **fanout** (기본) | 2개 Task 병렬 실행 → Serial 취합 | Orchestrator/자동 트리거 시 |
| **standalone** | 기존 순차 5단계 실행 | 사용자가 직접 호출 시 |

> **모드 판단 규칙**: Orchestrator/자동 트리거(EOD 감지) → fanout.
> 사용자가 직접 "/kostat-eod-retrospective" 호출 시 → standalone.

---

## Fan-out 모드 (병렬 2way + Serial 취합)

```
[종료 트리거]
       │
       ▼
  세션 히스토리 수집 (공통 입력)
       │
  ┌────┴────┐
  ▼         ▼
Task1       Task2
KPT 구조화  Lessons Learned
(Keep/      수집
Problem/    (비효율/반복
Try 생성)    패턴)
  │         │
  └────┬────┘
       ▼
  Serial: 내일 First Action 생성
  (Task1 + Task2 결과 기반)
       │
       ▼
  저장 + Memory Ticket 발행
```

### 진입 조건
- 사용자 종료 발화 감지 ("업무끝", "퇴근", "오늘 끝" 등)
- EOD 트리거 (오후 5시 이후 묵시적 종료 감지)
- Orchestrator로부터 세션 종료 신호 수신

---

### 공통 입력 — 세션 히스토리 수집

Task1/Task2 모두 공유하는 입력 데이터를 먼저 수집:

**수집 항목**:
| 항목 | 출처 |
|------|------|
| 오늘 완료 업무 목록 | 대화 내역, 처리 로그 |
| 처리된 PO/OOR/커미션 건수 | logs/ 디렉토리 |
| 발생한 이슈/에러 | 대화 내역 |
| 주요 결정사항 | 대화 내역 |
| 오늘의 AI 작업 로그 | session trace |
| 직전 KPT 파일 | `*KPT*.md` 최신 파일 |

**출력**: 구조화된 세션 히스토리 데이터 (두 Task에 동일 전달)

---

### Task 1 — KPT 구조화 (KPT 에이전트)

**담당**: 세션 히스토리 기반 Keep/Problem/Try 생성

**작업 순서**:
1. 세션 히스토리 분석 — 완료 업무, 이슈, 결정사항 추출
2. Keep 항목 도출 — 오늘 잘한 것, 유지할 습관 (최소 2~3개)
3. Problem 항목 도출 — 발생한 문제, 비효율, 개선 필요 사항 (최소 2~3개)
4. Try 항목 도출 — 구체적인 개선 액션 (추상적 표현 금지)

**출력**:
```json
{
  "keep": ["PO 3건 실수 없이 처리", "OOR 검증 리포트 자동화 완료"],
  "problem": ["Calendar API 인증 오류로 납기등록 스킵", "오후에 집중력 저하"],
  "try": ["Calendar API 키 사전 검증 스크립트 작성", "오전에 고난도 업무 배치"]
}
```

---

### Task 2 — Lessons Learned 수집 (Lessons 에이전트)

**담당**: 오늘 AI 작업 비효율 추출 및 반복 패턴 감지

**작업 순서**:
1. 세션 히스토리에서 AI 작업 비효율 추출 (아래 유형 기준)
2. 각 비효율을 [유형/상황/원인/개선방향] 구조화
3. 반복 패턴 감지 — 이번 주 동일 유형 3회 이상 발생 시 플래그
4. CLAUDE.md 업데이트 후보 식별

**비효율 유형 기준**:

| 유형 | 설명 |
|------|------|
| 불필요한 반복 | 같은 파일을 3번 이상 읽음 |
| 잘못된 추측 | 확인 없이 기본값 입력했다가 수정 |
| Gate 누락 | 승인 없이 파일 저장 |
| 도구 오선택 | grep 대신 파일 전체 읽기로 탐색 |
| 컨텍스트 낭비 | 불필요한 파일 대량 로드 |
| 규칙 미준수 | Human Gate 2단계 건너뜀 |

**출력**:
```json
{
  "lessons": [
    {"type": "불필요한 반복", "situation": "같은 OOR 파일을 3회 읽음", "cause": "분석 중간 결과 저장 안 함", "direction": "중간 결과 캐싱 로직 추가"}
  ],
  "patterns": ["이번 주 'Gate 누락' 3회 반복 — 주의 필요"],
  "claude_md_candidates": ["Human Gate 2단계 규칙 강화 — 항상 변경안 제시 후 승인"]
}
```

---

### Serial Step — 내일 First Action 생성 (취합)

**담당**: Task1 KPT + Task2 Lessons → 종합하여 우선순위 액션 도출

**작업 순서**:
1. Task1 결과(KPT) 로드
2. Task2 결과(Lessons) 로드
3. 두 결과를 종합하여 내일 우선순위 액션 3~5개 생성
4. 🔴/🟠/🟡 긴급도 표시

**출력 형식**:
```markdown
## 내일 First Action
- 🔴 [PO 미처리건] — 긴급: 3건 대기 중
- 🟠 [Calendar API] — 수동 재설정 필요
- 🟡 [Lessons 반영] — CLAUDE.md Gate 규칙 문구 강화
```

---

### 최종 저장

Task1 + Task2 + Serial 결과를 병합하여 `KPT_YYYY-MM-DD.md` 파일로 저장:

- **저장 경로**: `C:\Users\USER\Desktop\77. CLOUDE 정리용\KPT\KPT_YYYY-MM-DD.md`
- **날짜 포맷**: `2026.06.02 (화 저녁)` — 요일 정확성
- Memory Ticket 자동 발행 (Lessons에서 CLAUDE.md 업데이트 후보 발견 시)

---

## Standalone 모드 (기존 순차)

사용자 직접 요청 시 기존 5단계 순차 실행:

1. **세션 분석** — 오늘 대화에서 완료 업무/이슈/결정사항 추출
2. **KPT 구조화**
   - **Keep**: 오늘 잘한 것, 유지할 습관
   - **Problem**: 발생한 문제, 비효율, 개선 필요 사항
   - **Try**: 구체적인 개선 액션 (추상적 표현 금지)
3. **Lessons Learned — AI 작업 비효율 기록**
4. **내일 First Action** — 3~5개 액션, 🔴/🟠/🟡 긴급도 표시
5. **저장** — `KPT_YYYY-MM-DD.md` 형식, Notion 업무일지 하위에도 생성

## Lessons Learned 섹션 작성 기준

오늘 AI(Claude)가 작업 중 겪은 비효율·실수·반복 패턴을 기록합니다.
이 섹션은 에이전트 개선과 CLAUDE.md 업데이트의 입력 데이터가 됩니다.

### 기록해야 할 항목

| 유형 | 예시 |
|------|------|
| 불필요한 반복 | 같은 파일을 3번 이상 읽음 |
| 잘못된 추측 | MFG SITE를 확인 없이 'KR'로 입력했다가 수정 |
| Gate 누락 | 확인 없이 파일을 먼저 저장한 경우 |
| 도구 오선택 | grep 대신 파일 전체 읽기로 탐색 |
| 컨텍스트 낭비 | 불필요한 파일 대량 로드 |
| 규칙 미준수 | Human Gate 2단계 건너뜀 |

### 출력 형식

```markdown
## Lessons Learned — AI 작업 비효율 (2026-06-06)

| # | 유형 | 상황 | 원인 | 개선 방향 |
|---|------|------|------|-----------|
| 1 | [유형] | [무슨 일이 있었는가] | [왜 발생했는가] | [다음엔 어떻게] |

**반복 패턴 주의**: [이번 달 3회 이상 반복된 비효율 있으면 강조]
**CLAUDE.md 업데이트 후보**: [규칙으로 명문화할 사항]
```

비효율이 없었던 날에도 "오늘 비효율 없음 — 정상 작동" 한 줄 기록.

## KPT 전체 템플릿

```markdown
# KPT 회고 — {날짜}

## Keep
- 

## Problem
- 

## Try
- 

## Lessons Learned — AI 작업 비효율

| # | 유형 | 상황 | 원인 | 개선 방향 |
|---|------|------|------|-----------|
| 1 | | | | |

## 내일 First Action
- 🔴 
- 🟠 
- 🟡 
```

## 검증 체크리스트 (Fan-out 모드)

- [ ] 공통 입력: 세션 히스토리 수집 완료
- [ ] Task 1 (KPT): Keep/Problem/Try 각 섹션 최소 2~3개 항목 충족
- [ ] Task 1 (KPT): 추상적 표현 없이 구체적 업무 내용만 반영
- [ ] Task 2 (Lessons): Lessons Learned 섹션 기록 완료 (비효율 없어도 1줄)
- [ ] Task 2 (Lessons): 반복 패턴 감지 완료 (3회 이상 발생 시)
- [ ] Task 2 (Lessons): CLAUDE.md 업데이트 후보 식별 완료
- [ ] Serial Step: 내일 First Action 3~5개 구체화 완료
- [ ] Serial Step: 🔴/🟠/🟡 긴급도 표시 정확
- [ ] 최종 저장 경로 정확: `KPT\KPT_YYYY-MM-DD.md`
- [ ] Memory Ticket 연동 완료 (CLAUDE.md 업데이트 후보 있을 경우)

## 검증 체크리스트 (Standalone 모드)
- [ ] Keep/Problem/Try 각 섹션 최소 2~3개 항목 충족
- [ ] Lessons Learned 섹션 기록 완료 (비효율 없어도 1줄)
- [ ] 내일 First Action 3~5개 구체화 완료 (추상적 표현 금지)
- [ ] 저장 경로 정확: `C:\Users\USER\Desktop\77. CLOUDE 정리용\KPT\KPT_YYYY-MM-DD.md`
- [ ] 날짜 포맷 일치 (`2026.06.02 (화 저녁)`)

## 검증 루프 절차
1. **체크리스트 1회 실행** — 위 항목 순차 점검
2. **실패 항목 발견 시** → 해당 섹션 보완 → 다시 1단계로 (Loop)
3. **전체 통과 시** → 최종 저장

### Loop 규칙
- 실패가 0이 될 때까지 반복 (최대 3회)
- 추상적 표현("개선 노력")은 구체적 액션("10시 이전에 메일 확인")으로 대체
- 3회 초과 실패 → 사용자에게 미달 항목 보고 후 저장 진행

## 작성 규칙
- 날짜 포맷: `2026.06.02 (화 저녁)` — 요일 정확성
- K/P/T 각 섹션에 최소 2~3개 항목
- 추상적 원칙 나열 금지, 실제 업무 내용만 반영
- 내일 First Action은 실행 가능한 수준으로 구체화
- Lessons Learned는 사실 기반으로 기록 (주관적 판단 최소화)
