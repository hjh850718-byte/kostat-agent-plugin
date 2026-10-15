---
name: kostat-po-update
description: "PO PDF → Excel 입력. 트리거: 'PO 업데이트', 'PO 입력', PO 번호. Mode: fanout | standalone."
---

# kostat-po-update — Level 6 Fan-out

## 실행 모드 선택

본 스킬은 2가지 모드로 동작한다.

| 모드 | 동작 | 사용场景 |
|------|------|----------|
| **fanout** (기본) | 3개 Task 병렬 실행 → 결과 취합 | POP3/OOrchestrator에서 호출 시 |
| **standalone** | 기존 순차 7단계 실행 | 사용자가 직접 요청 시 |

> **모드 판단 규칙**: Orchestrator/다른 스킬에서 호출 시 → fanout.
> 사용자가 직접 "/kostat-po-update" 호출 시 → standalone (사용자 확인 질문).

---

## Fan-out 모드 (병렬 3way)

```
[PO PDF 수신]
       │
  ┌────┼────┐
  ▼    ▼    ▼
Task1 Task2 Task3
Excel  한글  Calendar
입력   요약  납기등록
  │    │    │
  └────┼────┘
       ▼
  취합 + Telegram 알림
```

### 진입 조건
- PO PDF 파일 존재 (`D:\jun\한준희\미국오더\*.pdf`)
- 또는 이메일 첨부로 PO PDF 수신

---

### Task 1 — Excel 업데이트 (PO-US 에이전트)

**담당**: 기존 순차 로직 그대로 실행

**작업 순서**:
1. **PO PDF 읽기** — PDF에서 PO#, Cust PN, Need By Date, Ship To, Remarks, TEMP 등 추출
2. **Kostat PN 확인** — 기존 행에서 동일한 Cust PN 검색 → MFG SITE 참조 (신규 PN이면 'KR' 기본값)
3. **PO# 중복 체크** — 중복 시 사용자 확인 후 진행 (자동 덮어쓰기 금지)
4. **Excel 신규 행 추가** — 가장 최근 날짜 다음 행에 삽입, 녹색 하이라이트
5. **Remarks 형식 검증** (`"Cust PN: | Need By: | $"` 패턴 강제)
6. **TEMP 처리** — 빈 값이면 빈칸 유지 + 알림

**출력**: `{po_number, customer, qty, ship_date, kostat_pn, status: "ok" | "dup" | "error"}`

> 상세 대상 파일 경로·필드 매핑·MFG SITE 규칙: [references/field-mapping.md](references/field-mapping.md)

---

### Task 2 — PO 한국어 요약 (Doc-Translate 에이전트)

**담당**: PO PDF의 영문 내용을 한국어로 요약

**입력**: 동일 PO PDF

**출력 형식**: PO 요약 마크다운 (고객사·P/N·수량·납기·Ship To·주요 포인트)

**저장**: po-summaries 디렉토리에 `{PO#}_summary.md`

---

### Task 3 — Calendar 납기 등록 (Calendar 에이전트)

**담당**: PO 납기일을 Google Calendar에 등록

**입력**: PO PDF에서 추출한 납기 관련 정보

**우선순위 색상 판단**:
- Need By Date 기준 오늘 + 14일 이내 → 🔴 긴급
- Need By Date 기준 오늘 + 60일 이내 → 🟡 일반
- 그 외 → 🟢 여유

**플랫폼 연동**: Google Calendar API (`.env` 또는 `settings.json`에서 키 로드)

**출력**: `{event_id, event_url, calendar_name, status: "created" | "skipped" | "error"}`

> 상세 일정 포맷·필드 매핑: [references/field-mapping.md](references/field-mapping.md)

---

### Synchronization Barrier (취합)

3개 Task 모두 완료 후 취합 → **Telegram** 발송

**에러 발생 시**:
- 1개 Task 실패 → 나머지 완료 + 실패 Task 재시도 1회
- 재시도 실패 → Telegram 에러 알림 + 수동 처리 권장
- 2개 이상 실패 → Orchestrator에 에러 보고 → 전체 중단

> 상세 Telegram 포맷: [references/field-mapping.md](references/field-mapping.md)

---

## Standalone 모드 (기존 순차)

사용자 직접 요청 시 기존 7단계 순차 실행:

### Step 1~6: 순차 처리
1. PO PDF 읽기 → 필드 추출
2. Kostat PN 확인 (기존 행 참조 → MFG SITE)
3. PO# 중복 체크 (중복 시 사용자 확인)
4. Excel 신규 행 추가 (녹색 하이라이트)
5. Remarks 형식 검증 (`"Cust PN: | Need By: | $"` 패턴)
6. TEMP 처리

### Step 7: 저장 승인 Gate (Human-in-the-loop — 1회만)

---

## 검증 루프 절차

1. 체크리스트 실행 → 실패 항목 발견 시 원인 분석 → 수정 → 재검증 (최대 3회)
2. **Fan-out 모드**: 3개 Task는 서로 독립적 — 컨텍스트 공유 금지
3. 3회 초과 실패 → 사용자에게 상황 보고 후 에스컬레이션

> 상세 검증 체크리스트·주의사항: [references/field-mapping.md](references/field-mapping.md)

## Evidence 적용
공통 정의·보고 형식·쓰기 게이트: [references/output-contract.md](../../references/output-contract.md)

### 필드별 라벨 기준

| 필드 | ✅ 확인됨 | 🧮 계산됨 | ❓ 추정 | ⛔ 미확인 |
|------|----------|----------|--------|----------|
| PO#, Cust PN, Qty, Need By, Ship To | PDF에서 추출 (페이지 명시) | — | — | 추출 실패/판독 불가 |
| Kostat PN | 기존 행에서 동일 Cust PN 검색됨 (시트/행 명시) | — | 신규 PN | 복수 행이 서로 다른 값 |
| MFG SITE | 기존 행 참조됨 | — | 신규 PN → 'KR' 기본값 | — |
| TEMP | PDF에 값 있음 | — | — | 비어 있음 (빈칸 유지 + 알림) |
| Remarks | — | `"Cust PN: \| Need By: \| $"` 패턴 조합 (입력이 모두 확인됨일 때) | 입력 중 추정 포함 | 입력 중 미확인 포함 |
| 캘린더 우선순위 🔴🟡🟢 | — | Need By − 오늘 (≤14일 🔴, ≤60일 🟡) | — | Need By 미확인 |
| 한국어 요약 | 원문 수치·고유명사 인용 | — | 해석·"주요 포인트" 문장 (요약에 ❓ 표기) | — |

### Task별 동작
- **Task 1 (Excel)**: 식별 필드(PO#, 고객사, Qty, Need By) 중 `추정/미확인`이 있으면 쓰지 않고 `status: "needs_review"`. 그 외 `추정`(MFG SITE 기본값 등)은 fanout에서는 쓰지 않고 보류, standalone에서는 Step 7 저장 승인 Gate의 변경 계획 표에 ❓로 표시. PO# 중복은 기존 규칙대로 사용자 확인 (자동 덮어쓰기 금지).
- **Task 2 (요약)**: 요약 본문의 모든 수치는 ✅ 원문 인용이어야 한다. 해석 문장은 "(추정)"을 붙인다.
- **Task 3 (Calendar)**: Need By가 ✅일 때만 일정 생성. ⛔이면 `status: "skipped"` + 사유.
- **취합**: 세 Task 출력의 라벨을 합산해 Telegram 첫 줄 `✅ n · 🧮 n · ❓ n · ⛔ n`로 보고하고 ❓/⛔만 펼친다. 같은 PO#의 필드가 Task 간 서로 다르면(예: Task1 Qty ≠ Task2 요약 Qty) 두 값 모두 ❓로 내리고 사용자 확인.

### Task 출력 JSON 확장
```json
{"po_number": "...", "status": "ok|dup|needs_review|error",
 "fields": {"qty": {"value": 5000, "label": "확인됨", "source": "PO.pdf p1 line 1"}},
 "counts": {"확인됨": 12, "계산됨": 2, "추정": 1, "미확인": 1}}
```

### 검증 체크리스트 추가
- [ ] 출력 필드 100%에 라벨 존재
- [ ] MFG SITE 'KR' 기본값이 ❓로 표기됨 (✅로 오표기 금지)
- [ ] 빈 TEMP가 빈칸으로 유지되고 ⛔로 보고됨
- [ ] Task 간 동일 필드 값 일치 (불일치 시 ❓)
