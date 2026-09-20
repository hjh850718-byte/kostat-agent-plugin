---
name: kostat-oor-weekly
description: "OOR Bring Forward 분석. 트리거: 'OOR', 'Open Order', 'Bring Forward'. Mode: fanout | standalone. ultracode Fan-out 권장."
---

# kostat-oor-weekly — Level 6 Fan-out

## 실행 모드 선택

| 모드 | 동작 | 사용场景 |
|------|------|----------|
| **fanout** (기본) | Task 1/2 병렬 실행 → 취합 | Orchestrator 호출 시 |
| **standalone** | 기존 순차 실행 | 사용자 직접 요청 시 |

---

## Fan-out 모드 (병렬 2way)

```
[OOR xlsx 수신]
       │
  ┌────┴────┐
  ▼         ▼
Task1       Task2
BF 추출 +   PO# 불일치
Excel       검증 리포트
업데이트     생성
  │         │
  └────┬────┘
       ▼
  취합 + Telegram 알림
```

### 진입 조건
- OOR xlsx 파일 수신 (이메일 첨부)
- 또는 사용자가 OOR 분석 요청

---

### Task 1 — Bring Forward 항목 추출 + Excel 업데이트 (OOR 에이전트)

**대상 파일**: OOR xlsx (이메일 첨부 또는 지정 경로)

**작업 순서**:
1. **OOR xlsx 읽기** — pandas/openpyxl로 데이터 로드
2. **항목 분류** — Bring Forward 항목을 아래 기준으로 3그룹 분류:

| 그룹 | 기준 | 색상 |
|------|------|------|
| 🔴 긴급 | 납기 2주 이내 + Status 미매칭 | 빨강 |
| 🟡 일반 | 납기 2주~2개월 or Bring Forward 있음 | 노랑 |
| ⚪ 보류 | 납기 여유 or 추후 검토 필요 | 초록 |

3. **Excel 업데이트**: 각 행에 그룹별 컬러코딩 + Bring Forward 사유 요약 컬럼 추가
4. **저장**: 원본 백업 후 결과 저장

> 상세 컬럼 매핑(F/AS/H/AU)·컬러코딩 규칙·검증 리포트 포맷: [references/column-map.md](references/column-map.md)

---

### Task 2 — PO# 불일치 검증 리포트 (Validator 에이전트)

**담당**: OOR 데이터 vs 실제 PO 파일 간 교차 검증 리포트 생성

**작업 순서**:
1. **OOR 데이터 로드** — 동일 xlsx 읽기
2. **PO# 불일치 검증** — F열(PO#) vs AS열(PO#) 비교
3. **납기 지연 검증** — H열(Ship Date) vs AU열(Req Date) 비교
4. **항목별 심각도 판단**: Critical(PO# 불일치) / Warning(납기 7일 초과) / Info(납기 7일 이내)
5. **리포트 생성**

> 상세 컬럼 매핑·심각도 기준·리포트 포맷·Telegram 알림: [references/column-map.md](references/column-map.md)

---

### Synchronization Barrier (취합)

두 Task 완료 후 결과 병합 → 최종 Telegram 발송

**에러 처리**:
- 1개 Task 실패 → 완료된 쪽 저장 + 실패 쪽 재시도 1회
- 재시도 실패 → 수동 처리 권장 메시지 + 실패 내역 포함하여 발송

> 상세 Telegram 포맷: [references/column-map.md](references/column-map.md)

---

## Standalone 모드 (기존 순차)

1. **항목 분류** — Bring Forward 항목을 [긴급/일반/보류] 3그룹 분류
2. **그룹별 검증** — PO#, 납기, Status 교차 검증
3. **불일치 항목 플래그** — PO# 불일치, 납기 초과 등 별도 표시
4. **취합 및 저장** — 컬러코딩 완료된 xlsx 출력

---

## 검증 루프 절차

1. 체크리스트 실행 → 실패 항목 발견 시 원인 분석 → 수정 → 재검증 (최대 3회)
2. 재검증 시 이전과 다른 각도에서 검증 (동일 실수 반복 방지)
3. 3회 초과 실패 → 사용자에게 상황 보고 후 에스컬레이션

> 상세 검증 체크리스트: [references/column-map.md](references/column-map.md)
