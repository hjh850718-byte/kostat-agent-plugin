---
name: kostat-local-llm
description: "Unsloth Desktop을 로컬 LLM 서브에이전트로 연동. 트리거: '로컬 LLM 연동', 'Unsloth 연결', '오프라인 모드', '서브에이전트로 로컬 모델', '민감 데이터 로컬 처리'."
---

# kostat-local-llm (Unsloth Desktop 연동)

## 개요
Unsloth Desktop(로컬 LLM 실행/파인튜닝 도구)을 KOSTAT 업무의 **서브에이전트**로 연동한다.
`unsloth start claude --as-subagent` 명령으로 메인 Claude는 그대로 유지한 채,
로컬 모델을 반복적/대량/민감 데이터 작업의 1차 처리기로 활용한다.

> 참고: Unsloth Desktop은 Mac/Win/Linux/WSL을 지원하며 NVIDIA/AMD/Mac GPU에서 동작한다.
> 코어는 Apache 2.0, Studio UI 등 일부는 AGPL-3.0 듀얼 라이선스.

## 왜 필요한가
- **민감 데이터 보호**: PO 원본, 커미션 RAW DATA 등 고객사 정보를 외부 API로 보내지 않고 로컬에서 1차 처리 가능 (텔레메트리 없이 완전 오프라인 실행 지원)
- **반복 작업 오프로드**: 대량 PO/OOR 행 단위 파싱, 포맷 정규화 등 단순 반복 작업을 로컬 모델에 위임해 메인 세션의 토큰/시간 절약
- **네트워크 단절 대응**: 사내망/보안 환경에서 클라우드 접근이 제한될 때도 업무 연속성 확보

## 사전 조건
- Unsloth Desktop 설치 완료 (Mac/Win/Linux/WSL)
- 로컬 GPU 또는 CPU 추론 환경 준비 (GGUF/MLX/safetensors 중 환경에 맞는 포맷 모델 다운로드)
- `unsloth start claude --as-subagent` 실행 시 MCP 연결 및 Bash/Python 샌드박스 권한 확인

## 연동 절차

### Step 1: Unsloth Desktop 실행 및 서브에이전트 등록
```bash
unsloth start claude --as-subagent
```
- 기존 메인 Claude(클라우드) 세션은 유지되며, 로컬 모델이 서브에이전트로 추가됨
- `--secure` 옵션 사용 시 Cloudflare HTTPS 터널로 외부 기기(휴대폰 등)에서도 접속 가능 — **민감 데이터 작업 시에는 사용하지 않음**

### Step 2: 위임 대상 작업 판단
아래 기준으로 로컬 서브에이전트에게 위임할지 메인 Claude가 직접 처리할지 결정한다.

| 위임 적합 (로컬 서브에이전트) | 직접 처리 (메인 Claude) |
|------|------|
| 대량 PO/OOR 행 단위 1차 파싱·정규화 | 최종 Excel 반영, 수식/서식 처리 |
| 반복 포맷 변환 (날짜 표준화, 컬럼 정리 등) | 고객사별 판단 기준(kostat-tal) 적용 |
| 오프라인/네트워크 단절 시 임시 처리 | Human Gate 승인이 필요한 변경 |
| 민감도 낮은 초안 요약 | 최종 커미션 인보이스 검증 |

### Step 3: 결과 검증 (Human Gate 원칙 유지)
- 로컬 모델 출력은 **초안(draft)**으로만 취급
- 메인 Claude가 kostat-tal의 판단 기준 및 기존 검증 체크리스트로 재검토 후 최종 반영
- 로컬 모델 정확도는 클라우드 모델 대비 낮을 수 있으므로, PO 금액·수량·납기일 등 핵심 필드는 반드시 원본 PDF와 재대조

## 활용 시나리오 예시
1. **대량 OOR 1차 정리**: 수백 행의 OOR 데이터에서 PO#/수량/납기일 추출을 로컬 모델에 위임 → 메인 Claude가 kostat-oor-weekly 규칙으로 최종 검증
2. **네트워크 불안정 환경**: 출장/외부 미팅 중 PO PDF 1차 요약을 오프라인 로컬 모델로 처리 → 사무실 복귀 후 메인 Claude로 정식 반영
3. **자동 재시도(self-healing)**: 로컬 모델의 도구 호출 실패 시 Unsloth의 self-healing 기능이 자동 감지/수정/재시도하여 정확도 향상

## 주의사항
- 로컬 모델의 출력을 그대로 Excel/인보이스에 반영 금지 — 반드시 메인 Claude 검증 단계를 거칠 것
- `--secure` 터널 사용 시 고객사 민감 정보가 포함된 세션은 노출 위험이 있으므로 사용 금지
- KOSTAT 관련 스킬(PO 업데이트, 커미션 인보이스 등)의 최종 승인/기록은 기존 Human Gate·백업 Hook(kostat-gateguard.py, kostat-autobackup.py) 절차를 그대로 따름

## 검증 체크리스트
- [ ] 로컬 서브에이전트 출력이 초안임을 인지하고 있는가
- [ ] 핵심 필드(금액/수량/납기일/PO#)를 원본과 재대조했는가
- [ ] 민감 데이터 작업 시 `--secure` 터널을 사용하지 않았는가
- [ ] 최종 반영 전 kostat-tal 판단 기준을 적용했는가
