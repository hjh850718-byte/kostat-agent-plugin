# PO PDF → Excel 필드 매핑

> `kostat-po-update` 스킬의 상세 참조 자료

---

## 대상 파일 경로

| 항목 | 경로 |
|------|------|
| PO PDF | `D:\jun\한준희\미국오더\*.pdf` |
| Excel 대상 | `C:\Users\USER\Desktop\77. CLOUDE 정리용\PO 업데이트 리스트\미국오더_20260410-_클로드_정리_updated.xlsx` |
| 대상 시트 | `미국오더-클로드정리` |
| PO 요약 저장 | `C:\Users\USER\Desktop\77. CLOUDE 정리용\po-summaries\{PO#}_summary.md` |

---

## PO PDF → Excel 컬럼 매핑

| PDF 필드 | Excel 컬럼 | 비고 |
|----------|-----------|------|
| PO# | PO# | 중복 체크 대상 |
| Cust PN | Cust PN | Kostat PN 매핑의 키 |
| Need By Date | Need By Date | 납기일 |
| Ship To | Ship To | 전체 주소 + Ship To Code |
| Remarks | Remarks | `"Cust PN: \| Need By: \| $"` 패턴 강제 |
| TEMP | TEMP | 빈 값이면 빈칸 유지 |

---

## MFG SITE 매핑 규칙

| 조건 | 기본값 |
|------|--------|
| 기존 Kostat PN 존재 | 이전 행 MFG SITE 값 따름 |
| 신규 Kostat PN | 'KR' 기본값 |

---

## Remarks 형식

강제 패턴: `"Cust PN: | Need By: | $"` — 각 필드를 파이프(`|`)로 구분

---

## 중복 PO# 처리 규칙

1. 기존 Excel에서 동일 PO# 검색
2. 중복 발견 시 **자동 덮어쓰기 금지** — 사용자 확인 필수
3. 사용자 승인 시에만 진행

---

## Calendar 일정 포맷

| 항목 | 값 |
|------|------|
| 제목 | `[KOSTAT] {Customer} PO#{PO#} 납기` |
| 날짜 | Need By Date (또는 Ship Date) |
| 설명 | `고객사: {Customer}\nPO#: {PO#}\n수량: {Qty}\nKostat PN: {Kostat PN}\nShip To: {Ship To}` |

### 우선순위 색상

| 조건 | 색상 |
|------|------|
| Need By Date 기준 오늘 + 14일 이내 | 🔴 긴급 |
| Need By Date 기준 오늘 + 60일 이내 | 🟡 일반 |
| 그 외 | 🟢 여유 |

---

## Telegram 알림 포맷

```
✅ PO#{po_number} 처리 완료 (Fan-out)

📊 Excel 업데이트: ✅완료 / ⚠️중복
📝 한글 요약:    ✅완료
📅 납기 등록:    ✅완료 / ⏭️스킵

📄 요약: {customer} | {kostat_pn} | {qty}개 | 납기 {ship_date}
```
