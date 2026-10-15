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

## Evidence 적용
공통 정의·보고 형식·쓰기 게이트: [references/output-contract.md](../../references/output-contract.md)

### 필드별 라벨 기준

| 필드 | ✅ 확인됨 | 🧮 계산됨 | ❓ 추정 | ⛔ 미확인 |
|------|----------|----------|--------|----------|
| F열 PO#, AS열 PO#, H열 Ship Date, AU열 Req Date, Status | 셀 값 존재 (시트/행/열 명시) | — | — | 셀이 비어 있거나 날짜 파싱 실패 |
| 그룹 🔴🟡⚪ | — | 납기 − **기준일** (리포트에 기준일 명시), Status 매칭 여부 | — | 납기 ⛔ → 그룹 미정 (별도 "판정 불가" 목록) |
| PO# 불일치 (Critical) | — | F ≠ AS (양쪽 ✅, 정규화 규칙 명시: 공백·대소문자·선행 0) | — | 한쪽이 ⛔ → "비교 불가" |
| 납기 지연 (Warning/Info) | — | AU − H 일수 (양쪽 ✅) | — | 한쪽 ⛔ → "비교 불가" |
| Bring Forward 사유 요약 컬럼 | 원본 Remarks/Status 인용 | — | 요약·해석 문장 (컬럼에 ❓ 표기) | — |

### 동작
- **비교 불가는 불일치가 아니다.** Critical/Warning 건수에 포함하지 않고 별도 "비교 불가(미확인)" 건수로 보고한다 (빈 AS열을 빨간 PO#로 칠하지 않음).
- 그룹 컬러코딩·불일치 표시는 🧮 규칙 결과이므로 리포트 상단에 `기준일`, `정규화 규칙`, `임계값(14일/60일/7일)`을 한 번 명시한다.
- Task 1(컬러코딩)과 Task 2(검증 리포트)가 같은 행에 다른 결론을 내면(예: Task1 🟡, Task2 Critical) 취합 시 해당 행을 ❓로 표시하고 두 근거를 함께 보고.
- 원본 xlsx 백업 후 저장(기존 규칙). 사유 요약 컬럼 외 원본 값은 변경하지 않는다.

### 보고 예시
```
📋 OOR 주간 — 행 184 · ✅ 920 · 🧮 368 · ❓ 6 · ⛔ 11
🔴 긴급 9 · 🟡 일반 41 · ⚪ 보류 128 · 판정불가 6
Critical(PO# 불일치) 4 · Warning 12 · 비교 불가 11  (기준일 2026-10-15)
```

### 검증 체크리스트 추가
- [ ] 비교 불가 행이 Critical/Warning에 집계되지 않음
- [ ] 리포트에 기준일·정규화 규칙·임계값 명시
- [ ] 원본 값 셀 변경 0건 (추가 컬럼·컬러 제외)
