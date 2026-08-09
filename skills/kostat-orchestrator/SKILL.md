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

### Task 상태 이벤트 스키마 (v2 — 설계안)

`task-status.json`은 기존 필드(`skill`/`file`/`status`/`timestamp`)에 더해
아래 필드를 선택적으로 기록할 수 있다. 상세 스키마, 필드 정의, 하위 호환 규칙은
[`docs/11. PraisonAI 참고 Orchestrator 신뢰성 설계.md`](../../docs/11.%20PraisonAI%20참고%20Orchestrator%20신뢰성%20설계.md) 참고.

| 필드 | 값 | 설명 |
|------|-----|------|
| `task_id` | `{접두사}-TASK{N}-{YYYYMMDD}-{순번}` | 아래 Task ID 체계와 동일 |
| `event_type` | `START`\|`RUNNING`\|`RETRY`\|`ERROR`\|`COMPLETE` | 상태 전이 이벤트명 |
| `error_category` | `config`\|`dependency`\|`tool`\|`model`\|`infra`\|`null` | 아래 에러 처리 §5분류 참고 |
| `retry_count` / `max_retries` | 정수 | `max_retries`는 항상 1 |
| `next_retry_at` | ISO8601 \| `null` | 아래 Backoff 정책으로 계산된 재시도 시각 |

> Hook(`kostat-handoff-writer.py` 등) 코드가 이 v2 스키마를 실제로 기록하도록 갱신하는 작업은
> 별도 범위다 — 이 SKILL.md는 Orchestrator(Claude)가 판단·기록할 때 따르는 설계 기준만 정의한다.

### 제한
- Task 타임아웃: 10분
- 재시도: 최대 1회, 에러 카테고리별 Backoff 적용 (아래 표 참고)
- 전체 팀 타임아웃: 15분
- 동시 실행 Task 수: 최대 4개 (리소스 제한)

### 알림
- Task 완료 시: 진행 상태 업데이트
- 전체 완료 시: 취합 결과 1회 발송
- 에러 발생 시: 즉시 알림 + 수동 처리 권장

---

## 에러 처리

### 5분류 체계 (PraisonAI 참고)

단일/다중 Task 실패 여부만 보던 기존 처리를 실패 **원인 카테고리**로 재구성한다.
카테고리는 `task-status.json`의 `error_category` 필드 값과 1:1 대응한다.

| 카테고리 | KOSTAT 시나리오 예시 | 재시도 | Backoff | 기본 대응 |
|----------|----------------------|--------|---------|----------|
| `config` | `.env` 값 누락, 파일 경로 오탈자 | 안 함 | — | 즉시 중단 + 설정 안내 |
| `dependency` | API 키 없음 (Calendar/Telegram/Notion) | 안 함 | — | 해당 Task 스킵 + 경고, 나머지 진행 |
| `tool` | Excel 파싱 실패, PDF 추출 실패, Validator 불일치 | 1회 | 30초 | Backoff 후 재시도 → 실패 시 스킵 + 알림 |
| `model` | Claude API 타임아웃/rate limit | 1회 | 30초 | Backoff 후 재시도 → 반복 실패 시 수동 처리 전환 |
| `infra` | POP3 연결 끊김, 동시 실행 4개 초과 정체, 디스크 부족 | 1회 | 120초 (서킷브레이커) | 신규 Task 일시 보류 + 마지막 체크포인트에서 재개 |

`next_retry_at = 실패시각 + Backoff초` 로 계산하며, Orchestrator는 이 시각이 지난 Task만
재시도 대상으로 취합한다.

### 팀 단위 규칙 (기존 유지)

| 상황 | 처리 |
|------|------|
| 2개 이상 Task 실패 | 전체 중단 → Telegram 긴급 알림 |
| Validator 에러 발견 | 카테고리와 무관하게 사용자 확인 요청 (자동 진행 금지) |
| 타임아웃 | 강제 종료 → 부분 결과로 처리 (`infra` 카테고리로 기록) |

### Replay(재실행)

`failed_final` Task를 재실행할 때는 `task_id`에 `-REPLAY{n}` 접미사를 붙여 새 Task로 등록한다
(예: `PO-TASK1-20260809-01-REPLAY1`). Fan-out 팀에서 이미 `completed`인 형제 Task는 재실행하지
않고 실패한 Task만 다시 소집한다. 상세는 `docs/11` §5 참고.

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

## .ai-bridge/ 상태 공유 구조

### 디렉토리 레이아웃

```
{KOSTAT_AI_BRIDGE_DIR}/          (기본: ~/Documents/Claude/AGENT/.ai-bridge)
├── current-plan.md              ← Orchestrator가 작성하는 현재 실행 계획
├── decisions.md                 ← Human Gate 승인/거부 이력
├── task-status.json             ← 에이전트별 실행 상태 (kostat-handoff-writer 갱신)
├── session-context.md           ← 세션 시작 컨텍스트 (kostat-ai-bridge 초기화)
└── agent-handoffs/              ← 에이전트 간 핸드오프 파일
    ├── kostat-po-update-{date}.md
    ├── kostat-oor-weekly-{date}.md
    ├── kostat-commission-invoice-{date}.md
    └── kostat-eod-retrospective-{date}.md
```

### Orchestrator 읽기/쓰기 규칙

| 파일 | 읽기 | 쓰기 | 시점 |
|------|------|------|------|
| `current-plan.md` | 모든 에이전트 | Orchestrator | 트리거 감지 즉시 |
| `decisions.md` | 모든 에이전트 | Orchestrator | Human Gate 결정 시 |
| `task-status.json` | Orchestrator | kostat-handoff-writer hook | Write 작업 완료 시 자동 |
| `session-context.md` | Orchestrator, EOD 스킬 | kostat-ai-bridge hook | 세션 시작/종료 자동 |
| `agent-handoffs/*.md` | 다음 에이전트 | kostat-handoff-writer hook | Write 작업 완료 시 자동 |

### current-plan.md 작성 예시

트리거 감지 후 Orchestrator는 아래 형식으로 `current-plan.md`를 업데이트한다:

```markdown
# 현재 오케스트레이터 계획

**세션**: abc12345
**날짜**: 2026-06-25

## 실행 대기 중인 트리거
- PO PDF 수신: PO12345.pdf (우선순위 1)

## 진행 중인 에이전트 팀
- [진행중] PO-US (kostat-po-update Task 1) — 시작: 14:30
- [대기] Doc-Translate (kostat-po-update Task 2) — PO-US 완료 후 시작

## 완료된 작업
- [완료 14:15] OOR 분석 → kostat-oor-weekly-2026-06-25.md
```

---

## Handoff 모드 (ORCHESTRATOR_ENGINE=handoff)

### 동작 방식

```
[트리거 감지]
      │
      ▼
┌─────────────┐
│ Orchestrator │  current-plan.md 작성 (계획 전용)
│  (Claude)    │  직접 에이전트 호출 ✗
└──────┬──────┘
       │  .ai-bridge/current-plan.md 파일 생성
       ▼
┌─────────────┐
│ orchestrator │  current-plan.md 읽기
│  _bridge.py  │  → 각 에이전트 subprocess 실행
│  (Python)    │  → task-status.json 갱신
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ agent-handoffs/ │  각 에이전트 완료 시 핸드오프 파일 생성
│  (hook 자동)    │  → EOD 스킬이 오늘 핸드오프 모아 회고 작성
└─────────────┘
```

### .env 전환 설정

```dotenv
# AUTOMATION/.env
ORCHESTRATOR_ENGINE=handoff    # direct | claude | handoff
KOSTAT_AI_BRIDGE_DIR=C:\Users\USER\Documents\Claude\AGENT\.ai-bridge
KOSTAT_HANDOFF=on              # handoff-writer hook 활성화
```

### orchestrator_bridge.py 연동 코드

`AUTOMATION/orchestrator_bridge.py`에 아래 핸들러를 추가한다:

```python
import json
from pathlib import Path
import os

AI_BRIDGE_DIR = Path(os.environ.get(
    "KOSTAT_AI_BRIDGE_DIR",
    Path.home() / "Documents" / "Claude" / "AGENT" / ".ai-bridge"
))

def run_handoff_mode(classification_result):
    """
    ORCHESTRATOR_ENGINE=handoff 모드:
    current-plan.md 를 polling하여 Claude가 작성한 계획을 읽고
    각 에이전트 subprocess를 실행한다.
    """
    plan_file = AI_BRIDGE_DIR / "current-plan.md"
    status_file = AI_BRIDGE_DIR / "task-status.json"

    # 계획 파일 대기 (Claude가 작성할 때까지 최대 60초)
    import time
    deadline = time.time() + 60
    while time.time() < deadline:
        if plan_file.exists():
            content = plan_file.read_text(encoding="utf-8")
            if "## 진행 중인 에이전트 팀" in content and "없음" not in content:
                break
        time.sleep(2)
    else:
        raise TimeoutError("current-plan.md 작성 타임아웃")

    # task-status.json 에 시작 기록
    status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
    status["handoff_started"] = time.strftime("%Y-%m-%d %H:%M:%S")
    status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    # 기존 direct 실행과 동일한 로직으로 에이전트 호출
    return run_direct_mode(classification_result)
```

### 세 가지 엔진 모드 비교

| 모드 | Claude 역할 | Python 역할 | 용도 |
|------|------------|-------------|------|
| `direct` | 없음 | handlers.py 직접 실행 | 완전 자동화 |
| `claude` | subprocess 실행 | 트리거 전달 | Fan-out 모드 |
| `handoff` | current-plan.md 작성 | 계획 읽고 실행 | 계획/실행 분리 |

---

## 제한사항
- Orchestrator는 **직접 파일을 수정하지 않는다** — 각 에이전트에 위임
- `current-plan.md`는 Orchestrator만 쓰고, 각 에이전트는 읽기만 한다
- 비밀번호/API 키는 Orchestrator가 보관하지 않음 — `.env` 참조만 전달
- 인간의 판단이 필요한 작업(Gate)은 항상 사용자에게 에스컬레이션
- Orchestrator가 다운되어도 개별 스킬은 standalone 모드로 동작 가능 (fallback)
- Handoff 모드에서 `current-plan.md` 미작성 시 60초 후 타임아웃 → `direct` 모드로 fallback
