# 커미션 요율표 및 역산 규칙

> `kostat-commission-invoice` 스킬의 상세 참조 자료

---

## 요율 역산 규칙

기본 공식: `rate = commission_amount / sales_amount × 100`

### 검증 허용 오차
- 요율 역산: ±0.01%
- 합계 금액: 1 USD 미만 오차 허용

---

## 고객사별 시트 매핑

| 시트 | 고객사 | 특징 |
|------|--------|------|
| US | 미국 고객사 통합 | 다수 고객 포함 가능 |
| ATP | ATP 고객 | 별도 요율 적용 |
| MICRON | Micron 고객 | 별도 요율 적용 |

---

## 인보이스 포맷

```markdown
# COMMISSION INVOICE — {고객사}
기간: {YYYY-MM-DD} ~ {YYYY-MM-DD}

| 항목 | 금액 (USD) |
|------|-----------|
| 판매액 | {amount} |
| 요율 | {rate}% |
| 커미션 | {commission} |

SUMMARY
- {고객사}: ${amount}
- 합계: ${total}
```

### 구조화 출력 (Generator → Evaluator 전달용)

```json
{
  "customers": [
    {
      "name": "US",
      "sales_amount": 100000,
      "rate": 3.0,
      "commission": 3000,
      "period_start": "2026-01-01",
      "period_end": "2026-03-31"
    }
  ],
  "total_commission": 9000,
  "generated_at": "2026-06-08T14:00:00+09:00"
}
```

### 검증 출력 (Evaluator → Generator 피드백용)

```json
{
  "verdict": "pass" | "fail",
  "checks": [
    {
      "check": "rate_verification",
      "status": "pass" | "fail",
      "detail": "US 요율 3.0% = 3000/100000*100 ✅"
    },
    {
      "check": "total_verification",
      "status": "pass" | "fail",
      "detail": "합계 9000 = 3000+3000+3000 ✅"
    }
  ],
  "fail_count": 0,
  "feedback": "Generator에 전달할 구체적 수정사항 (실패 시)"
}
```

---

## 저장 경로

- 인보이스: `C:\Users\USER\Desktop\77. CLOUDE 정리용\Commission\Invoice_{고객사}_{YYYYMMDD}.md`

---

## Telegram 알림 포맷

```
💰 커미션 인보이스 생성 완료 (Gen/Eval Loop {N}회)
━━━━━━━━━━━━━━━━━━━━━━━━━
📋 고객사: {US/ATP/MICRON}
💰 총 커미션: ${total:,}
✅ 검증: 통과 (재생성 {N-1}회)

📎 파일: {invoice_path}
```
