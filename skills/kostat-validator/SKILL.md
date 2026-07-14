---
name: kostat-validator
description: "PO/OOR/Commission 처리 결과 교차 검증 게이트. 트리거: '검증', 'Validator', 'PO# 불일치 확인', '중복 체크', '컬럼 매핑 검증'. Mode: gate (타 스킬 호출) | standalone. Quality→Verdict→Answerability 3단 판정."
---

# kostat-validator — Level 6 Quality Gate

## 정체성

Validator는 특정 트리거로 단독 기동하는 에이전트가 아니라, **PO-US(kostat-po-update) / PO-HK(kostat-hk-po-update) / OOR(kostat-oor-weekly) / Commission(kostat-commission-invoice) 각 스킬이 처리를 마친 직후 호출되는 공용 검증 게이트**다. "맞다/틀리다" 판정에서 그치지 않고, **Quality(증거 생성) → Verdict(판정) → Answerability(설명 책임)** 3단계를 항상 거쳐 상사 보고에 바로 쓸 수 있는 근거를 남긴다.

> 설계 근거: KOSTAT-AGENT v2 Validator 설계문서(2026-07-14, 한준희) 권고안 — **옵션 A**(Quality-Verdict-Answerability) + **옵션 C**(Append-only 로그 + Compaction) 우선 적용. **옵션 B**(coordinator/contract 표준화, PO-US/PO-HK/OOR 검증 로직 통합)는 China 출장(8/3~9) 이후 신규 고객사(Luxshare/NXP/Zhenghao) 온보딩 시점에 단계적으로 착수 예정 — 이번 구현에서는 그 전환이 쉽도록 입력 스키마만 범용화해둔다. **각 스킬 자체의 검증 로직(예: kostat-oor-weekly Task 2의 PO# 불일치 검증)은 그대로 유지**하며, Validator는 그 결과 위에 판정·로그·근거 요약 레이어를 얹는다.

---

## 실행 모드 선택

| 모드 | 동작 | 사용 시점 |
|------|------|----------|
| **gate** (기본) | 호출한 스킬의 처리 결과를 입력받아 Quality→Verdict→Answerability 실행 | PO-US/PO-HK/OOR/Commission 처리 완료 직후 (자동 호출) |
| **standalone** | 사용자가 지정한 파일/데이터를 직접 검증 | 사용자가 "이 파일 검증해줘" 등 직접 요청 시 |

## 트리거

- 타 스킬(kostat-po-update, kostat-hk-po-update, kostat-oor-weekly, kostat-commission-invoice) 처리 완료 후 자동 호출 (gate 모드)
- 사용자 발화: "검증", "Validator", "PO# 불일치 확인", "중복 체크", "컬럼 매핑 검증" (standalone 모드)
- Orchestrator가 Team 소집 시 각 팀의 마지막 단계로 포함 (아래 [연동 지점](#연동-지점-호출-시점) 참고)

---

## 입력 스키마 (범용 — Extension 영역 분리)

옵션 B(coordinator/contract) 전환에 대비해 base 필드는 최대한 범용화하고, 고객사·스킬별 특수 필드는 `extension`에 담는다. base 필드는 설계문서가 제시한 표준 계약 후보(PO DATE / 출하일 / customer / PO# / Q'ty / Status)와 동일하게 맞춘다.

```json
{
  "source_skill": "kostat-po-update",
  "task_id": "PO-TASK1-20260714-01",
  "record_type": "po_line",
  "base": {
    "po_number": "6000046947",
    "customer": "Skyworks",
    "po_date": "2026-07-10",
    "ship_date": "2026-08-01",
    "qty": 1000,
    "status": "open"
  },
  "extension": {
    "mfg_site": "KR",
    "ks_pn": null,
    "commission_rate": null
  },
  "evidence_source": {
    "file_path": "D:\\jun\\한준희\\미국오더\\...xlsx",
    "row_range": "2415-2420"
  }
}
```

| 필드 | 규칙 |
|------|------|
| `source_skill` | 호출한 스킬 이름 (`kostat-po-update` \| `kostat-hk-po-update` \| `kostat-oor-weekly` \| `kostat-commission-invoice`) |
| `record_type` | `po_line` \| `oor_line` \| `commission_line` |
| `base` | 모든 스킬 공통 필드 — 향후 옵션 B 표준 계약과 1:1 대응 |
| `extension` | 스킬/고객사 전용 필드 (HK의 `ks_pn`, PO-US의 `mfg_site`, Commission의 `commission_rate` 등). 해당 없으면 `null` |
| `evidence_source` | 원본 파일 경로 + 행 범위 — Answerability 근거 추적용 |

---

## Quality 단계 — 증거 생성

| 검증 항목 | 대상 | 방법 | 실패 시 기록 |
|-----------|------|------|-------------|
| PO# 매칭 | `base.po_number` vs 원본 PO 파일/타 시트 | 정규화(trim, 대소문자) 후 정확 일치 | mismatch 목록 (기대값/실제값) |
| 중복 탐지 | `base.po_number` + `base.qty` 조합 | 대상 시트 내 동일 조합 재검색 | 중복 행 번호 |
| 컬럼 매핑 검증 | `extension` 필드 ↔ 원본 컬럼 위치 | 스킬별 필드 매핑 규칙 대조 (field-mapping/xview-mapping/column-map 기준) | 매핑 오류 컬럼명 |
| (Commission 전용) 요율 역산 | `extension.commission_rate` | `rate = commission / sales_amount`, 허용 오차 ±0.01% | 오차 초과 항목 |

각 검증 항목의 결과는 구조화된 로그 엔트리로 남긴다:

```json
{"check": "po_number_match", "result": "pass", "detail": ""}
{"check": "duplicate_detect", "result": "fail", "detail": "PO#6000046950 qty=900 — 2415행과 2420행 중복"}
```

---

## Verdict 단계 — 판정 (자동 승인 임계치)

| 조건 | Verdict | 처리 |
|------|---------|------|
| Quality 불일치 **0건** | ✅ **승인 (approved)** | 자동 진행, Telegram에 결과만 포함 |
| 불일치 **1건 이상**, Critical 없음 (Warning/Info만) | 🟡 **보류 (hold)** | 사람 확인 필요 — 자동 진행 금지, 원본 스킬은 저장 진행하되 "확인 필요" 플래그 동반 |
| **Critical 불일치 1건 이상** (PO# 불일치, 요율 오차 허용치 초과 등) | 🔴 **반려 (rejected)** | 원본 스킬의 저장 단계 중단 → 근거와 함께 사용자에게 즉시 보고 |

- Critical / Warning / Info 심각도 구분은 kostat-oor-weekly의 기존 기준(Critical=PO# 불일치, Warning=납기 7일 초과, Info=납기 7일 이내)을 그대로 재사용한다.
- 임계치는 "불일치 0건 = 승인"으로 고정 — 중간 관리자 승인 병목을 막기 위해 보류 조건을 더 엄격하게 낮추지 않는다.

---

## Answerability 단계 — 근거 3줄 요약

Verdict마다 아래 템플릿으로 요약을 자동 생성한다. 이 3줄은 배경→현황→옵션→권고안 보고 형식의 **"현황"** 섹션에 그대로 붙여넣을 수 있는 형태여야 한다.

```markdown
**근거 요약 ({source_skill} / {검증 대상} / {날짜})**
1. [Quality] 검증 {N}건 중 {통과}건 통과, {불일치}건 발견 ({불일치 항목명})
2. [Verdict] {승인|보류|반려} — 사유: {핵심 사유 1줄}
3. [Action] {자동 진행 / 사용자 확인 필요 항목 / 반려 재처리 방법}
```

예시:
```markdown
**근거 요약 (kostat-po-update / PO#6000046950 / 2026-07-14)**
1. [Quality] 검증 3건 중 2건 통과, 1건 불일치 (Qty: 원본 1000 vs Excel 900)
2. [Verdict] 보류 — 사유: Qty 불일치 (Critical 아님, Warning)
3. [Action] 사용자 확인 후 저장 진행 — Excel 900 유지 여부 확인 필요
```

---

## Append-only 로그 + Compaction 연동 (옵션 C)

### 저장 위치
- Raw log(append-only): `{KOSTAT_AI_BRIDGE_DIR}\validator-log\validator-YYYY-MM-DD.jsonl` (기본: `C:\Users\USER\Documents\Claude\AGENT\.ai-bridge\validator-log\`)
- 한 줄 = 검증 1건 (Quality 로그 + Verdict + Answerability 3줄 요약을 하나의 JSON 레코드로 append)
- **덮어쓰기 금지** — 항상 append. 같은 날 여러 건이면 계속 누적.

```json
{"timestamp": "2026-07-14T14:32:00+09:00", "source_skill": "kostat-po-update", "task_id": "PO-TASK1-20260714-01", "quality": [{"check": "po_number_match", "result": "pass"}, {"check": "duplicate_detect", "result": "fail", "detail": "..."}], "verdict": "hold", "answerability": "**근거 요약 (...)**\n1. ...\n2. ...\n3. ..."}
```

### Compaction (kostat-eod-retrospective 연동)

하루 끝에 **kostat-eod-retrospective**가 공통 입력 수집 단계에서 당일 `validator-YYYY-MM-DD.jsonl` 전체를 읽어 압축한다.

**압축 규칙**:
1. Verdict별 건수만 집계 (승인/보류/반려)
2. **승인 건**은 건수만 남기고 상세 Quality 로그는 버림 (원본에만 존재)
3. **보류·반려 건**은 Answerability 3줄 요약을 **원문 그대로 보존** — 근거 유실 금지 (요약의 요약을 만들지 않는다)
4. 압축본만 다음 세션 컨텍스트(`.ai-bridge/session-context.md`)에 포함

**압축본 예시**:
```markdown
## Validator 요약 (2026-07-14)
- 승인 12건 / 보류 2건 / 반려 0건
- 보류 상세:
  1. PO#6000046950 (kostat-po-update) — Qty 불일치(1000→900) → 사용자 확인 대기
  2. OOR 2026W28 (kostat-oor-weekly) — PO# AS열 공백 → 확인 필요
```

**아카이브**: 압축 완료 후 원본 `validator-YYYY-MM-DD.jsonl`은 Obsidian Vault KPT 회고 폴더에 그대로 이동/복사한다: `{OBSIDIAN_VAULT}\KPT\validator-archive\validator-YYYY-MM-DD.jsonl`. 세션 컨텍스트에는 압축본만 남기고 원본 jsonl은 로드하지 않는다 (124K 토큰 목표 기여, kostat-memory-loader의 "불필요한 파일 대량 로드 방지" 원칙과 동일).

> EOD 스킬 쪽 구현 상세는 [kostat-eod-retrospective/SKILL.md](../kostat-eod-retrospective/SKILL.md)의 "Validator 로그 Compaction" 절 참고.

---

## 연동 지점 (호출 시점)

| 호출 스킬 | 호출 시점 | `source_skill` 값 | 비고 |
|-----------|----------|-------------------|------|
| kostat-po-update | Task 1(Excel 입력) 완료 직후, Synchronization Barrier 전 | `kostat-po-update` | Task 1 출력(`{po_number, customer, qty, ship_date, kostat_pn, status}`)을 base/extension으로 매핑해 전달 |
| kostat-hk-po-update | Task 1(Excel 입력) 완료 직후 | `kostat-hk-po-update` | `ks_pn` 등 HK 전용 필드는 extension에 포함 |
| kostat-oor-weekly | Task 1(BF 추출+Excel 업데이트) 완료 직후 | `kostat-oor-weekly` | Task 2(PO# 불일치 검증 리포트)는 그대로 유지 — 그 리포트 결과를 Validator 입력의 Quality 근거 중 하나로 함께 전달 (로직 대체 아님, 판정·로그 레이어 추가) |
| kostat-commission-invoice | Phase 2(Evaluator) 완료 후, 최종 저장 전 | `kostat-commission-invoice` | Evaluator의 pass/fail을 Validator의 Verdict 게이트로 재사용 — Verdict=반려 시 Generator 재생성 루프로 피드백 |

Verdict=반려 시 원본 스킬의 저장 단계를 중단하고 Answerability 요약과 함께 사용자에게 즉시 보고한다. Verdict=보류 시에는 저장은 진행하되 Telegram/보고에 "확인 필요" 플래그를 동반한다.

---

## Standalone 모드

사용자가 직접 "이 파일 검증해줘" 요청 시:

1. 대상 파일/데이터 확인 (경로를 모르면 사용자에게 질의)
2. Quality 체크 항목 확인 — 기본값은 PO#매칭 + 중복탐지 + 컬럼매핑 전체
3. Verdict 판정 + Answerability 3줄 요약 출력
4. gate 모드와 동일하게 append-only 로그에 기록 (standalone도 로그 대상에서 예외 없음)

---

## 검증 체크리스트

- [ ] Quality: 검증 항목별 결과가 구조화 로그(JSON)로 생성됨
- [ ] Verdict: 승인/보류/반려 3단계 중 하나로 명확히 판정됨
- [ ] Verdict 임계치 규칙 적용됨 (불일치 0건→승인, Critical 1건 이상→반려, 그 외→보류)
- [ ] Answerability: 근거 3줄 요약이 "현황" 섹션에 바로 삽입 가능한 형태로 생성됨
- [ ] Append-only 로그 기록 완료 (`validator-YYYY-MM-DD.jsonl`, 덮어쓰기 없음)
- [ ] `source_skill`/`extension` 필드 누락 없이 기록됨 (향후 옵션 B 전환 대비)

## 검증 루프 절차

1. 체크리스트 실행 → 실패 항목 발견 시 원인 분석 → 수정 → 재검증 (최대 3회)
2. 재검증 시 이전과 다른 각도에서 검증 (동일 실수 반복 방지)
3. 3회 초과 실패 → **Verdict=보류로 강제 전환** + 사용자 에스컬레이션 (반려로 자동 전환 금지 — 최종 판단은 사람이 내린다)

---

## 주의사항

- Validator는 원본 데이터(Excel/PDF)를 직접 수정하지 않는다 — 판정과 로그만 남기고 수정은 호출한 스킬에 위임한다
- Verdict=반려는 사용자 확인 없이 자동 재시도하지 않는다 (Commission Gen/Eval Loop의 3회 자동 재생성과 다름 — Validator의 반려는 사람 개입 지점)
- Quality 원본 로그(raw jsonl)는 세션 컨텍스트에 전체 로드하지 않는다 — Compaction된 요약만 로드한다
- 옵션 B(coordinator/contract) 착수 전까지 각 스킬의 자체 검증 로직(PO# 불일치 리포트 등)은 폐지하지 않는다 — Validator는 그 위에 얹는 판정/로그 레이어다
