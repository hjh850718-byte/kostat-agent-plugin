---
name: kostat-orchestrator
description: "KOSTAT Orchestrator — 트리거 감지 → 에이전트팀 병렬 소집 → 결과 취합 → EOD 전달. 레벨 7 코어 엔진."
---

# kostat-orchestrator — Level 7 Orchestrator

## 정체성

본 Orchestrator는 KOSTAT 자동화 시스템의 **두뇌** 역할을 한다.
POP3 폴링/사용자 입력/파일 감지 등에서 트리거를 식별하고,
적절한 에이전트팀을 소집하여 병렬 실행한 후 결과를 취합한다.

---

## 트리거 감지 → 핸들러 매핑

### 트리거 테이블

| 트리거 키워드 | 우선순위 | 소집 에이전트팀 | 실행 모드 |
|--------------|---------|----------------|----------|
| PO PDF 수신 | 1 | PO-US + Doc-Translate + Calendar | Fan-out 3way |
| HK PO / Amkor PO 수신 | 1 | HK-PO + Doc-Translate | Fan-out 2way |
| OOR / Open Order | 2 | OOR + Validator | Fan-out 2way |
| Commission / Invoice | 3 | Commission-Gen + Commission-Eval | Gen/Eval Loop |
| 업무끝 / EOD | 4 | EOD-Retro + Memory-Ticket | 순차 |
| /kostat | 5 | Morning-Briefing | 단일 |
| /skill-check | 6 | Skill-Check | 단일 |
| 일반 메일 | 7 | Summary | 단일 |

**우선순위 규칙**: 숫자가 작을수록 높음. 중복 트리거 발생 시 가장 높은 우선순위 처리 후 나머지 대기.

---

## 실행 흐름

```
[트리거 입력]
     │
     ▼
┌─────────┐
│Trigger  │  키워드 매칭 → 우선순위 판단
│Classifier│
└────┬────┘
     │
     ▼
┌─────────┐
│Team     │  해당 에이전트팀 병렬 소집
│Dispatch │
└────┬────┘
     │
     ▼
┌─────────┐
│Monitor  │  각 에이전트 상태 추적
│Status   │
└────┬────┘
     │
     ▼
┌─────────┐
│Result   │  전체 완료 → 취합 → Telegram
│Collect  │
└────┬────┘
     │
     ▼
┌─────────┐
│Forward  │  EOD 에이전트에 세션 결과 전달
│to EOD   │
└─────────┘
```

---

## Agent Teams 구성

### Team A: PO 수신 대응
| 에이전트 | 스킬 | 투입 조건 |
|----------|------|----------|
| PO-US | kostat-po-update (Task 1) | 항상 투입 |
| Doc-Translate | kostat-po-update (Task 2) | 항상 투입 |
| Calendar | kostat-po-update (Task 3) | Calendar API 사용 가능 시 |

### Team B: OOR 대응
| 에이전트 | 스킬 | 투입 조건 |
|----------|------|----------|
| OOR | kostat-oor-weekly (Task 1) | 항상 투입 |
| Validator | kostat-oor-weekly (Task 2) | 항상 투입 |

### Team C: 커미션 대응
| 에이전트 | 스킬 | 투입 조건 |
|----------|------|----------|
| Commission-Gen | kostat-commission-invoice (Phase 1) | 항상 투입 |
| Commission-Eval | kostat-commission-invoice (Phase 2) | Generator 완료 후 |

### Team D: EOD 회고
| 에이전트 | 스킬 | 투입 조건 |
|----------|------|----------|
| EOD-Retro | kostat-eod-retrospective | 업무종료 트리거 |
| Memory-Ticket | kostat-memory-ticket | KPT 생성 후 자동 호출 |

---

## 병렬 실행 명령 포맷

Orchestrator는 각 Task를 아래 포맷으로 호출한다:

```json
{
  "command": "agent_task",
  "task_id": "PO-TASK1-20260608-01",
  "skill": "kostat-po-update",
  "mode": "fanout",
  "task_number": 1,
  "input": {
    "pdf_path": "D:\\jun\\한준희\\미국오더\\PO12345.pdf",
    "po_number": "PO12345",
    "customer": "Skyworks",
    "priority": "normal"
  },
  "dependencies": [],
  "timeout_minutes": 10
}
```

**Task ID 체계**: `{트리거접두사}-TASK{N}-{YYYYMMDD}-{순번}`

| 트리거 | 접두사 |
|--------|--------|
| PO | PO |
| HK PO | HK |
| OOR | OOR |
| Commission | COM |
| EOD | EOD |
| 일반 | GEN |

---

## 모니터링 체계

### 상태 추적
각 Task는 다음 상태를 가짐:

```
pending → running → completed
                 → failed (→ retry → failed_final)
                 → timeout
```

### 제한
- Task 타임아웃: 10분
- 재시도: 1회 (동일 Task 재실행)
- 전체 팀 타임아웃: 15분
- 동시 실행 Task 수: 최대 4개 (리소스 제한)

### 알림
- Task 완료 시: 진행 상태 업데이트
- 전체 완료 시: 취합 결과 1회 발송
- 에러 발생 시: 즉시 알림 + 수동 처리 권장

---

## 에러 처리

| 에러 유형 | 처리 |
|----------|------|
| 단일 Task 실패 | 재시도 1회 → 실패 시 해당 Task 스킵 + 알림 |
| 2개 이상 Task 실패 | 전체 중단 → Telegram 긴급 알림 |
| Validator 에러 발견 | 사용자 확인 요청 (자동 진행 금지) |
| API 키 없음 | 해당 Task 스킵 + 환경설정 안내 |
| 타임아웃 | 강제 종료 → 부분 결과로 처리 |

---

## EOD 연동

세션 종료 시 Orchestrator는 아래 정보를 EOD 에이전트에 전달:

```json
{
  "session_start": "2026-06-08T09:00:00+09:00",
  "session_end": "2026-06-08T18:00:00+09:00",
  "processed_triggers": [
    {"type": "PO", "count": 2, "status": "completed"},
    {"type": "OOR", "count": 1, "status": "completed"}
  ],
  "team_performance": {
    "PO-US": {"tasks": 2, "success": 2, "errors": 0},
    "OOR": {"tasks": 1, "success": 1, "errors": 0},
    "Validator": {"tasks": 1, "success": 1, "errors": 0}
  },
  "total_agent_calls": 7,
  "errors": [],
  "open_loops": [
    "PO#67890 - Calendar 등록 실패 → 수동 처리"
  ]
}
```

---

## 제한사항
- Orchestrator는 **직접 파일을 수정하지 않는다** — 각 에이전트에 위임
- 비밀번호/API 키는 Orchestrator가 보관하지 않음 — `.env` 참조만 전달
- 인간의 판단이 필요한 작업(Gate)은 항상 사용자에게 에스컬레이션
- Orchestrator가 다운되어도 개별 스킬은 standalone 모드로 동작 가능 (fallback)
