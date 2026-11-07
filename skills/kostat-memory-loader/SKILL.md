---
name: kostat-memory-loader
description: "KOSTAT 컨텍스트 로드. 트리거: '컨텍스트 로드', '메모리 로드'. 세션 시작 시 자동."
allowed-tools: Read, Glob, Grep
model: sonnet
---

# kostat-memory-loader

## 로드 대상
1. **KOSTAT_MEMORY.md** — `C:\Users\USER\Desktop\77. CLOUDE 정리용\KOSTAT_MEMORY.md` (사용자 프로필, 파일 경로, 고객사, 루틴)
2. **Plugin CLAUDE.md** — `kostat-agent-plugin\CLAUDE.md` (변경 시 규칙, 디렉토리 구조)

## 실행 조건
- 세션 시작 시 자동 로드
- 사용자가 "컨텍스트 로드해줘" 요청 시
- 새로운 작업공간 전환 시

## 판정 체계 (Verdict)

로드 결과를 세션 시작 시 한 줄로 보고한다.

| 대상 | 상태 값 |
|------|---------|
| KOSTAT_MEMORY.md | `loaded` / **`not_loaded`** (필수 - 실패 시 NOT ASSESSED) |
| Plugin CLAUDE.md | `loaded` / `not_loaded` |

**규칙**:
1. 경로가 없거나 읽기 실패 시 조용히 넘어가지 않고 "컨텍스트 미로드: <파일명> - <사유>"를 출력한다.
2. MEMORY.md 미로드 상태에서는 고객사·경로·루틴을 **기억에서 추정하지 않는다** (사용자에게 경로 확인 요청).
3. 선별 로드한 참고 자료는 목록으로 남겨 무엇을 읽지 않았는지 알 수 있게 한다.

---

## 검증 체크리스트 (Loop 방식)
- [ ] MEMORY.md 로드 완료 (필수)
- [ ] 참고 자료 중 현재 작업에 필요한 것만 선별 로드 (토큰 절약)
- [ ] 불필요한 파일 대량 로드 방지

## 검증 루프 절차
1. **체크리스트 1회 실행** — 위 항목 순차 점검
2. **실패 항목 발견 시** → 재로드/재선별 → 다시 1단계로 (Loop)
3. **전체 통과 시** → 다음 작업 진행

### Loop 규칙
- 실패가 0이 될 때까지 반복 (최대 3회)
- 3회 초과 실패 → 사용자에게 상황 보고

## 주의사항
- 과도한 파일 로딩은 토큰 비용 증가 → 필요한 파일만 선별 로드
- MEMORY.md는 항상 로드 (크기 작음)
- 참고 자료는 사용자 요청에 따라 선택 로드
