---
name: kostat-memory-ticket
description: "/memory-ticket 명령어로 새 Memory Ticket 발행. 학습/판단 기준 업데이트를 구조화하여 기록."
---

# kostat-memory-ticket

## 트리거
- 사용자가 `/memory-ticket` 입력
- EOD 회고 시 Phase 3에서 자동 호출
- Worker가 새로운 판단 기준이나 학습 발견 시 제안

## Memory Ticket 포맷

모든 Memory Ticket은 아래 JSON 구조를 **정확히** 사용:

```json
{
  "id": "MT-YYYYMMDD-N",
  "timestamp": "2026-06-08T09:00:00+09:00",
  "sourceAgent": "[호출한 스킬명 또는 Worker]",
  "scope": "skill | customer | decision | project | process",
  "trustLabel": "proposed | confirmed | validated",
  "summary": "한 줄 요약 (50자 이내)",
  "evidence": "근거 — 파일명, 대화 맥락, 판단 기준 (200자 이내)",
  "action": "propose_update | flag_review | promote_skill | deprecate | archive",
  "status": "pending | approved | rejected | applied"
}
```

### 필드 설명

| 필드 | 규칙 |
|------|------|
| `id` | `MT-YYYYMMDD-N` — N은 당일 순번 (01부터) |
| `timestamp` | ISO 8601 +09:00 (한국 시간) |
| `sourceAgent` | 호출한 스킬명 (kostat-po-update, eod-retrospective 등) |
| `scope` | 영향 범위 — 하나만 선택 |
| `trustLabel` | 신뢰도 — `proposed`(제안), `confirmed`(확인됨), `validated`(검증됨) |
| `summary` | 50자 이내 핵심 요약 |
| `evidence` | 판단 근거 (파일명, 고객명, 실제 사례) |
| `action` | 취해야 할 조치 |
| `status` | 처리 상태 — 생성 시 항상 `pending` |

### scope 종류

| scope | 발행 조건 |
|-------|----------|
| `skill` | 스킬 효과/오류/개선 필요 |
| `customer` | 고객사 요청/응대/이슈 변경 |
| `decision` | 판단 기준/의사결정 변경 |
| `project` | 프로젝트 진행/범위 변경 |
| `process` | 업무 프로세스 개선 |

## 발행 조건 (이 중 하나라도 해당되면 발행)

1. **스킬 효과 발견** — 특정 스킬이 예상보다 효과적/비효과적이었음
2. **고객사 변경** — 고객 담당자 변경, 요구사항 변경, 이슈 발생
3. **판단 기준 업데이트 필요** — 기존 규칙이 실제와 다른 경우
4. **반복 패턴 발견** — 3회 이상 동일한 실수/비효율 발생
5. **의사결정 기록 필요** — 중요한 결정을 내렸으나 문서화되지 않음

## 저장 위치

- **파일 저장**: `C:\Users\USER\Desktop\77. CLOUDE 정리용\memory-tickets\MT-YYYY-MM-DD-N.json`
- **인덱스**: 같은 디렉토리의 `INDEX.md`에 요약 추가
- EOD 회고와 연동: KPT 파일 하단에 오늘 발행된 Ticket ID 목록 추가

## Memory Ticket INDEX.md 포맷

```markdown
# Memory Ticket Index

| ID | 날짜 | scope | 요약 | 상태 |
|----|------|-------|------|------|
| MT-20260608-01 | 2026-06-08 | customer | Skyworks 담당자 변경 | pending |
```

## 절대 저장 금지 (검증 필터)
- API 키, 비밀번호, 인증 토큰
- 고객 단가, 내부 원가, 수익률
- 미확인 추정값 ("아마도~", "~인 것 같음")
- 원문 트랜스크립트 전체
- 개인정보 (고객 연락처, 생년월일 등)

## 검증 체크리스트
- [ ] JSON 형식 정확 (trailing comma 없음)
- [ ] id 중복 체크 완료
- [ ] scope 필드 유효 (6개 중 하나)
- [ ] trustLabel 필드 유효 (3개 중 하나)
- [ ] summary 50자 이내
- [ ] evidence에 구체적 근거 포함됨
- [ ] 저장 금지 목록 포함 여부 검사 완료
- [ ] 저장 경로 정확
