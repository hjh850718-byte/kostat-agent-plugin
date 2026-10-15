---
name: kostat-commission-invoice
description: "커미션 인보이스 생성 및 검증. 트리거: '커미션', 'commission', 'invoice'. Generator/Evaluator Loop 패턴. 독립 에이전트 교차 검증."
---

# kostat-commission-invoice — Level 6 Generator/Evaluator Loop

## 실행 모드

| 모드 | 동작 |
|------|------|
| **gen-eval-loop** (기본) | Generator ↔ Evaluator 독립 실행 + Loop-until-done |
| **standalone** | 기존 순차 실행 |

---

## Generator/Evaluator Loop 모드

```
[RAW DATA]
    │
    ▼
 ┌──────────┐
 │ Generator│  ← 인보이스 초안 생성
 │ (Phase1) │
 └────┬─────┘
      │ 초안
      ▼
 ┌──────────┐
 │ Evaluator│  ← 요율 역산 + 금액 검증 (독립 컨텍스트)
 │ (Phase2) │
 └────┬─────┘
      │
   ┌──┴──┐
   │Pass?│──No──→ Generator 재생성 (최대 3회)
   └──┬──┘          ↑ 피드백 전달
      │ Yes
      ▼
  최종 저장 + Telegram
```

### 핵심 원칙
- **Generator ≠ Evaluator**: 절대 동일 컨텍스트에서 실행 금지 (자기확증편향 방지)
- Evaluator는 Generator의 결과를 **독립적으로 검증**
- 실패 시 **구체적 피드백**을 Generator에 전달하여 재생성
- Loop 최대 3회 — 초과 시 사용자 에스컬레이션

---

### Phase 1: Generator (인보이스 생성 에이전트)

**입력**:
- RAW DATA: `D:\jun\한준희\` 내 커미션 관련 Excel
- 고객사 시트: US / ATP / MICRON 등

**작업 순서**:
1. RAW DATA 로드 (pandas or openpyxl)
2. 고객사별 데이터 분리 (US, ATP, MICRON 시트)
3. **요율 역산** — 각 고객사별 적용 요율 계산:
   - `rate = commission_amount / sales_amount`
4. **인보이스 초안 생성** — 고객사·기간별로 구분

> 상세 인보이스 포맷·JSON 구조·검증 출력 형식: [references/rate-tables.md](references/rate-tables.md)

---

### Phase 2: Evaluator (검증 에이전트 — 독립 컨텍스트)

**입력**: Generator가 생성한 인보이스 데이터 (JSON)

**검증 항목**:
1. **요율 역산 검증** (`commission / sales_amount * 100 = rate`, 허용 오차 ±0.01%)
2. **합계 금액 검증** (개별 합계 = Total Commission, SUMMARY 시트 교차 검증)
3. **통화 표기 검증** (USD 일관성, 천단위 구분자 일관성)
4. **데이터 무결성 검증** (RAW DATA 행 수 vs 인보이스 반영 건수 일치)

> 상세 검증 출력 JSON 구조: [references/rate-tables.md](references/rate-tables.md)

---

### Loop 제어

```python
MAX_LOOP = 3
loop_count = 0

while loop_count < MAX_LOOP:
    loop_count += 1
    
    # Phase 1: Generate
    invoice = Generator(raw_data, feedback_from_prev)
    
    # Phase 2: Evaluate (독립 컨텍스트!)
    verdict = Evaluator(invoice)
    
    if verdict == "pass":
        save_and_notify()
        break
    else:
        feedback = extract_feedback(verdict)
        if loop_count >= MAX_LOOP:
            escalate_to_user(f"3회 재생성 실패: {feedback}")
            break
        # continue loop with feedback
```

**Loop 규칙**:
- Evaluator 실패 항목 수가 0이 될 때까지 반복 (최대 3회)
- 재생성 시 **이전 피드백을 Generator에 컨텍스트로 전달**
- 재검증 시 이전과 다른 각도에서 검증 (동일 실수 반복 방지)
- 3회 초과 실패 → 사용자에게 실패 내역 + 현재 초안 제시

---

### Phase 3: 최종 저장

- 인보이스 저장 및 Telegram 알림
- RAW DATA와 함께 PDF 변환 (옵션)

> 상세 저장 경로·Telegram 포맷: [references/rate-tables.md](references/rate-tables.md)

---

## Standalone 모드 (기존 순차)

### Phase 1: 인보이스 생성
1. RAW DATA (US/ATP/MICRON 시트) 읽기
2. 고객사별 요율 역산
3. 인보이스 초안 생성 (고객사·기간별)

### Phase 2: 교차 검증 (독립 에이전트)
- 합계 금액 일치 여부 검증
- 요율 역산 정확도 재계산
- SUMMARY 시트 수치 검증
- 불일치 발견 시 사용자 확인 후 저장

---

## 검증 루프 절차

1. 체크리스트 실행 → 실패 항목 발견 시 원인 분석 → 수정 → 재검증 (최대 3회)
2. Generator와 Evaluator는 **반드시 독립 컨텍스트**에서 실행
3. 3회 초과 실패 → 사용자에게 상황 보고 후 에스컬레이션

> 상세 검증 체크리스트: [references/rate-tables.md](references/rate-tables.md)

## Evidence 적용
공통 정의·보고 형식·쓰기 게이트: [references/output-contract.md](references/output-contract.md)

### 필드별 라벨 기준

| 필드 | ✅ 확인됨 | 🧮 계산됨 | ❓ 추정 | ⛔ 미확인 |
|------|----------|----------|--------|----------|
| RAW DATA 행 (고객사, 기간, 매출액, 커미션액) | 시트/행 명시 | — | — | 셀 비어 있음/숫자 파싱 실패 |
| 목표 커미션 금액 | 사용자 입력 또는 RAW 값 | — | — | 미제공 (요율 역산 불가) |
| 요율 | 요율표(`rate-tables.md`)에 정의 | `commission ÷ sales` 역산 (입력 모두 ✅) | 요율표에 없고 역산 근거도 불충분 | 입력 ⛔ |
| 개별/합계 금액, SUMMARY 수치 | — | 합산·곱셈 (반올림 규칙 명시) | — | 입력 ⛔ |
| 통화·천단위 표기 | 요율표/기존 인보이스 서식 | — | — | — |

### Generator / Evaluator 분담
- **Generator 출력**: 모든 금액·요율 필드를 `{value, label, source|formula}`로 내보낸다. 요율은 반드시 🧮 역산식과 입력(매출액, 커미션액)을 함께 기록.
- **Evaluator는 Generator의 label을 신뢰하지 않는다.** 독립 컨텍스트에서 RAW DATA로 🧮 값을 재계산해 일치(±0.01%, 금액은 센트 단위)를 확인하고, `확인됨`으로 표기된 값이 실제 RAW 셀과 같은지 대조한다. 라벨 위조/오표기는 실패 항목.
- 인보이스 파일에는 ❓/⛔ 값을 쓰지 않는다. 요율이 ❓이면 인보이스 초안 생성을 멈추고 사용자에게 요율 확인을 요청한다 (임의 반올림·요율 보정 금지).
- 루프 재생성 시 이전 피드백에 "어떤 필드의 어떤 라벨이 왜 실패했는지"를 포함.

### Evaluator 출력 JSON 확장
```json
{"verdict": "pass|fail",
 "label_audit": {"unlabeled": 0, "source_mismatch": 0, "recompute_mismatch": 0},
 "failures": [{"field": "ATP.rate", "reason": "재계산 2.48% ≠ 기재 2.50%", "label_claimed": "계산됨"}]}
```

### 검증 체크리스트 추가
- [ ] 요율 전부 🧮(식·입력 기록) 또는 ✅(요율표 출처)
- [ ] 합계 = 개별 합 (재계산 일치), SUMMARY 교차 일치
- [ ] RAW 행 수 = 반영 건수 (누락 행은 ⛔로 보고)
- [ ] ❓/⛔ 값이 인보이스 파일에 0건
- [ ] Evaluator 재계산이 Generator 값과 독립적으로 수행됨
