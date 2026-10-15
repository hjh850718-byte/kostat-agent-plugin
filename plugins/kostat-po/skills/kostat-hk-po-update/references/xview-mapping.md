# HK(Amkor) PO 필드 매핑

> `kostat-hk-po-update` 스킬의 상세 참조 자료

---

## 대상 파일 경로

| 항목 | 경로 |
|------|------|
| PO PDF | `D:\jun\한준희\invoice\*.pdf` (PO-XXXX 형식) |
| PO 요약 저장 | `C:\Users\USER\Desktop\77. CLOUDE 정리용\po-summaries\HK_{PO#}_summary.md` |

---

## PDF → Excel 필드 매핑

| PDF 필드 | Excel 컬럼 | 비고 |
|----------|-----------|------|
| PO# | PO# | PO-XXXX 형식, 중복 체크 대상 |
| 품목 | 품목 | Amkor 제품명 |
| 수량 | 수량 | |
| 단가 | 단가 | 통화 확인 필요 |
| 납기 | Need By Date | |
| Invoice# | Invoice# | PO#와 별도 관리 |

---

## Invoice# vs PO# 구분 규칙

- **PO#**: 발주 번호 (PO-XXXX 형식)
- **Invoice#**: 송장 번호 (별도 번호 체계)
- 두 번호를 혼동하지 않고 각각 해당 필드에 입력
- Invoice#는 PO Excel에 별도 컬럼으로 관리

---

## Telegram 알림 포맷

```
✅ HK PO#{po_number} 처리 완료 (Fan-out)

📊 Excel 업데이트: ✅완료 / ⚠️중복
📝 한글 요약:    ✅완료

📄 요약: {customer} | {kostat_pn} | {qty}개 | 납기 {ship_date}
```
