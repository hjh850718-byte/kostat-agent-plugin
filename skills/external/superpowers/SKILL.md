---
name: superpowers-debugging
description: 4단계 RCA 기반 체계적 디버깅. "디버깅", "에러 원인", "MCP 오류", "OAuth 문제", "cron 실패", "안 돼" 등 디버깅 요청 시 사용. 15~30분 내 근본 원인 해결 목표.
---

# Superpowers: Systematic Debugging (KOSTAT 커스텀)

## 목적
KOSTAT-AGENT 운영 중 발생하는 오류를 체계적으로 추적·해결.
추측성 시도(try-and-error) 대신 4단계 RCA(Root Cause Analysis) 실행.

## 4단계 디버깅 프로세스

### Phase 1 — 증상 수집
- 정확한 에러 메시지, 스택 트레이스 확인
- 언제부터, 어떤 조건에서 발생했는지 파악
- 최근 변경사항(코드, 설정, 환경) 목록화

### Phase 2 — 가설 수립 (3개 이상)
- 각 가설을 "만약 X라면 Y가 관찰될 것" 형태로 작성
- 가능성 순위 매기기 (HIGH/MED/LOW)
- KOSTAT 주요 가설 패턴:
  * Gmail MCP: OAuth scope 문제 → read-only vs write 권한 확인
  * cron 실패: 경로 문제 or 환경변수 누락
  * Excel 오류: 시트명 불일치 or 컬럼 인덱스 오프셋
  * Telegram bot: Chat ID 오류 or 네트워크 타임아웃

### Phase 3 — 격리 실험
- 가설 검증을 위한 최소 재현 코드 작성
- 경계 조건에 로깅 추가
- 하나씩 격리하여 원인 확정

### Phase 4 — 근본 해결
- 임시 패치가 아닌 근본 원인 수정
- 동일 오류 재발 방지 코드 추가
- 수정 내용 CLAUDE.md 또는 해당 SKILL.md에 반영

## KOSTAT 주요 장애 유형 & 빠른 참조

| 장애 유형 | 1차 확인 | 해결 방향 |
|---|---|---|
| Gmail MCP 쓰기 실패 | OAuth scope 확인 | 재연결, write scope 추가 |
| cron 모닝브리핑 미실행 | Task Scheduler 로그 | 경로/권한/환경변수 점검 |
| Excel 컬럼 오프셋 | col 인덱스 출력 | SKILL.md 컬럼 매핑 수정 |
| Notion MCP 저장 실패 | 페이지 ID 유효성 | 페이지 ID 재확인 |
| PlayMCP KakaoTalk 실패 | Chat ID 8761375215 | 봇 연결 상태 확인 |

## 출력 형식
- 가설 목록 → 실험 결과 → 확정 원인 → 수정 코드 순서로 제시
- 수정 후 검증 방법도 함께 제시

## 트리거 키워드
"에러", "오류", "안 돼", "실패", "디버깅", "왜 안 되지", "MCP 문제", "cron 실패", "OAuth 오류"
