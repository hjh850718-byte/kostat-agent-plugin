# OOR 컬럼 매핑 및 규칙

> `kostat-oor-weekly` 스킬의 상세 참조 자료

---

## 컬럼 매핑

| 열 | 내용 | 검증 대상 |
|----|------|-----------|
| F열 | PO# | 불일치 검증 (vs AS열) |
| AS열 (또는 44열) | PO# (참조) | 불일치 검증 (vs F열) |
| H열 | Ship Date | 납기 지연 검증 (vs AU열) |
| AU열 | Req Date | 납기 지연 검증 (vs H열) |

---

## Bring Forward 분류 기준

| 그룹 | 기준 | 색상 |
|------|------|------|
| 🔴 긴급 | 납기 2주 이내 + Status 미매칭 | 빨강 |
| 🟡 일반 | 납기 2주~2개월 or Bring Forward 있음 | 노랑 |
| ⚪ 보류 | 납기 여유 or 추후 검토 필요 | 초록 |

---

## 심각도 판단 기준

| 심각도 | 조건 | 색상 |
|--------|------|------|
| 🔴 Critical | PO# 불일치 (데이터 무결성 위반) | 빨강 |
| 🟠 Warning | 납기 지연 7일 초과 | 주황 |
| 🟡 Info | 납기 지연 7일 이내 | 노랑 |

---

## 검증 리포트 포맷

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 OOR 검증 리포트 — {날짜}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 검증 대상: 총 {N}건

🔴 Critical — PO# 불일치 ({N}건)
| 행 | F열(PO#) | AS열(PO#) |
|----|----------|-----------|
| {row} | {f_val} | {as_val} |

🟠 Warning — 납기 7일 초과 ({N}건)
| 행 | H열(Ship Date) | AU열(Req Date) | 지연일수 |
|----|---------------|---------------|----------|
| {row} | {h_val} | {au_val} | {days} |

🟡 Info — 납기 7일 이내 ({N}건)

📋 요약
- 검증 완료: {N}건
- 정상: {N}건 ({(N/total*100):.0f}%)
- 이상: {N}건 ({(N/total*100):.0f}%)
  - PO# 불일치: {N}건
  - 납기 지연: {N}건
```

---

## 컬러코딩 적용 규칙

1. 각 행을 분류 기준에 따라 그룹화
2. 해당 행 전체에 그룹별 색상 적용 (openpyxl PatternFill)
3. Bring Forward 사유 요약 컬럼 추가 (신규 컬럼 또는 기존 빈 컬럼 사용)
4. 이상 항목에 Excel Comment 포함

---

## 파일 저장 규칙

- 원본 백업: `*_backup_YYYYMMDD_HHMMSS.xlsx`
- 결과 저장: `OOR_processed_YYYYMMDD_HHMMSS.xlsx`
- 검증 리포트: `OOR_validation_report_YYYYMMDD.md`

---

## Telegram 알림 포맷

```
📊 OOR 분석 완료 (Fan-out)
━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Excel 업데이트: ✅완료
   - 총 {N}건 | 🔴{urgent} 🟡{normal} ⚪{hold}
🔍 검증 리포트:   ✅완료
   - PO# 불일치: {critical}건
   - 납기 지연:   {warning+info}건

📎 리포트: {report_path}
📎 Excel: {excel_path}
```
