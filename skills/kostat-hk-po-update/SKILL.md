---
name: kostat-hk-po-update
description: "HK(Amkor) PO PDF → Excel 입력. 트리거: 'HK PO', 'Amkor PO'. Mode: fanout | standalone."
---

# kostat-hk-po-update — Level 6 Fan-out

## 실행 모드 선택

| 모드 | 동작 | 사용场景 |
|------|------|----------|
| **fanout** (기본) | 2개 Task 병렬 실행 → 결과 취합 | Orchestrator/POP3에서 호출 시 |
| **standalone** | 기존 순차 5단계 실행 | 사용자가 직접 요청 시 |

> **모드 판단 규칙**: Orchestrator/다른 스킬에서 호출 시 → fanout.
> 사용자가 직접 "/kostat-hk-po-update" 호출 시 → standalone.

---

## Fan-out 모드 (병렬 2way)

```
[HK PO PDF 수신]
       │
  ┌────┴────┐
  ▼         ▼
Task1       Task2
Excel       한국어
입력        요약
  │         │
  └────┬────┘
       ▼
  취합 + Telegram 알림
```

### 진입 조건
- Amkor PO PDF 파일 존재 (PO-XXXX 형식)
- 또는 이메일 첨부로 HK PO PDF 수신

---

### Task 1 — Excel 업데이트 (HK-PO 에이전트)

**담당**: 기존 순차 로직 그대로 실행

**작업 순서**:
1. **HK PO PDF 읽기** — PO#, 품목, 수량, 단가, 납기 추출
2. **Excel 시트 매핑** — HK 전용 시트에 맞게 컬럼 매핑
3. **기존 데이터 확인** — 동일 PO# 존재 여부 체크 (중복 시 사용자 확인)
4. **신규 행 추가** — 적절한 위치에 삽입, 녹색 하이라이트
5. **저장** — 파일명에 날짜 포함 + 백업 생성

**출력**: `{po_number, customer, qty, status: "ok" | "dup" | "error"}`

> 상세 대상 파일 경로·필드 매핑·Invoice#/PO# 구분: [references/xview-mapping.md](references/xview-mapping.md)

---

### Task 2 — HK PO 한국어 요약 (Doc-Translate 에이전트)

**담당**: HK PO PDF의 영문 내용을 한국어로 요약

**입력**: 동일 HK PO PDF

**출력 형식**: PO 요약 마크다운 (고객사·P/N·수량·납기·Invoice#·주요 포인트)

**저장**: po-summaries 디렉토리에 `HK_{PO#}_summary.md`

---

### Synchronization Barrier (취합)

2개 Task 모두 완료 후 취합 → **Telegram** 발송

**에러 발생 시**:
- 1개 Task 실패 → 나머지 완료 + 실패 Task 재시도 1회
- 재시도 실패 → Telegram 에러 알림 + 수동 처리 권장
- 2개 모두 실패 → 전체 중단 → 긴급 알림

> 상세 Telegram 포맷: [references/xview-mapping.md](references/xview-mapping.md)

---

## Standalone 모드 (기존 순차)

1. **HK PO PDF 읽기** — PO#, 품목, 수량, 단가, 납기 추출
2. **Excel 시트 매핑** — HK 전용 시트 컬럼 매핑
3. **기존 데이터 확인** — 동일 PO# 존재 여부 체크
4. **신규 행 추가**
5. **저장** — 파일명에 날짜 포함

---

## 검증 루프 절차

1. 체크리스트 실행 → 실패 항목 발견 시 해당 Task만 재실행 → 재검증 (최대 3회)
2. Task별 독립 재시도 (한 Task 실패가 다른 Task에 영향 주지 않음)
3. **Fan-out 모드**: 2개 Task는 서로 독립적 — 컨텍스트 공유 금지
4. 3회 초과 실패 → 해당 Task 스킵 + 에러 알림

> 상세 검증 체크리스트·주의사항: [references/xview-mapping.md](references/xview-mapping.md)
