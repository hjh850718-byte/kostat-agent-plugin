---
name: kostat-katok-search
description: "고객사 카카오톡 대화 로컬 검색 연동 (katok CLI, Apple Silicon macOS 전용, 현재 설계 단계). 트리거: '카톡 검색', 'katok 검색', '카카오톡 대화 찾아줘'."
---

# kostat-katok-search

## 개요
고객사 담당자와 나눈 카카오톡 대화를 Mac 로컬에서 검색·조회하기 위한 스킬입니다.
실행 표면으로 [NomaDamas/katok](https://github.com/NomaDamas/katok) CLI를 사용하며, 카카오톡
대화 내용을 별도 서버로 올리지 않고 개인 Mac 안에서만 아카이브·인덱스를 만들어 검색합니다.

**현재 단계: 설계/문서화만 완료.** 실행 환경(Apple Silicon Mac + macOS 카카오톡 앱)이
아직 준비되지 않았으므로, 아래 사전 확인 절차는 항상 "미충족"으로 판단하고 종료합니다.
환경이 준비되면 이 문서의 "사전 확인 통과 시 명령 흐름"부터 실제 동작을 시작합니다.

## 사전 확인 (Loop보다 먼저, 매번 실행)
1. **플랫폼 확인** — 현재 세션이 Apple Silicon macOS에서 실행 중인지 확인. Windows·Linux·Intel
   Mac이면 즉시 아래 "미충족 시 안내"를 출력하고 종료한다.
2. **katok 설치 확인** — `katok doctor --json` 실행 가능 여부 확인. 명령을 찾을 수 없으면 설치
   안내(`brew install katok` 또는 `cargo install katok`) 후 종료한다.
3. **권한 확인** — `katok doctor --json`(macOS 권한 프롬프트 없는 기본 모드)의 `freshness`만
   확인한다. Full Disk Access가 안 되어 있으면 `katok permissions macos` 안내로 종료한다.

### 미충족 시 안내 (현재 기본 상태)
```
🔒 katok 연동은 Apple Silicon Mac + macOS 카카오톡 앱 환경에서만 동작합니다.
현재 세션 환경에서는 실행할 수 없어 검색을 생략합니다.
Mac에서 사용하려면: brew install katok (또는 cargo install katok) 후
katok doctor --json 으로 상태를 확인하세요.
```

## 사전 확인 통과 시 명령 흐름
사전 확인을 모두 통과했을 때만 진행한다 (katok 저장소 `skills/katok/SKILL.md` 기준 순서).

```bash
katok doctor --json                           # freshness 확인, 권한 프롬프트 없음
katok sync --source macos --json              # freshness.recommendation.sync_before_search == true 일 때만
katok index --json                            # freshness.recommendation.index_before_semantic_search == true 일 때만
katok search keyword "<정확한 단어>" --json
katok search bm25 "<여러 단어 질의>" --json
katok search semantic "<의미 기반 질의>" --json
katok chunk get <chunk-id> --json             # 사용자가 특정 결과를 명시적으로 열어달라고 할 때만
```

## Privacy Rules
katok 저장소의 `AGENTS.md`, `skills/katok/SKILL.md`를 그대로 준수한다.

- 카카오톡 DB·SQLCipher·인증 캐시 등 내부 구조를 직접 다루지 않는다 — CLI 명령으로만 접근한다.
- 검색 결과는 기본적으로 snippet과 chunk id만 보여준다. 원문 전체는 사용자가 특정 chunk id를
  지정하거나 결과를 열어달라고 명시적으로 요청했을 때만 `katok chunk get`으로 조회한다.
- 실제 대화에서 확인한 내용(인용문, 방 이름, 상대방 이름 등)은 이 스킬 파일·커밋 메시지·문서·
  테스트 어디에도 기록하지 않는다. 세션 내 답변에만 사용한다.
- 합성 테스트가 필요하면 `tests/fixtures/kakao/replies.jsonl` 같은 fixture만 사용하고
  `--data-dir <tmp>`로 반드시 격리한다. 실제 아카이브에는 절대 기록하지 않는다.
- `katok send`(메시지 전송)는 **이번 통합 범위에서 제외**한다. 전송이 필요하면 katok 저장소의
  `skills/katok-send/SKILL.md` 절차(dry-run → 명시적 확인 → 1회 실행)를 사용자가 별도로 따르도록
  안내만 하고, 이 스킬에서 자동으로 호출하지 않는다.

## 검증 체크리스트 (Loop 방식)
- [ ] 플랫폼(Apple Silicon macOS) 확인 완료
- [ ] katok 설치 및 `doctor --json` 정상 응답 확인
- [ ] freshness 기준 sync/index 필요 여부 판단 완료
- [ ] 검색 결과를 snippet 수준으로만 요약했는지 확인 (전체 원문 무단 노출 금지)
- [ ] 실제 대화 내용이 스킬 산출물(커밋, 문서, 로그)에 남지 않았는지 확인

## 검증 루프 절차
1. **체크리스트 1회 실행** — 위 항목 순차 점검
2. **실패 항목 발견 시** → 원인 재확인 → 재시도 → 다시 1단계로 (Loop)
3. **전체 통과 시** → 결과 요약 출력

### Loop 규칙
- 실패가 0이 될 때까지 반복 (최대 3회)
- 3회 초과 실패 → 사용자에게 상황 보고 후 에스컬레이션 (권한·설치 문제는 자동 해결 불가)

## 참고
- 원본 CLI/스킬: https://github.com/NomaDamas/katok
  (`skills/katok/SKILL.md`, `skills/katok-send/SKILL.md`, `AGENTS.md`)
- 지원 환경: Apple Silicon Mac, macOS 카카오톡 앱, 터미널 전체 디스크 접근 권한
  (Intel Mac·Windows 미지원 — EmbeddingGemma 로컬 임베딩 경로가 ONNX Runtime prebuilt를
  `x86_64-apple-darwin`용으로 제공하지 않기 때문)
- 기존 `kostat-morning-briefing`의 "KakaoTalk (MCP)"는 **발송(PlayMCP)** 용도이고,
  이 스킬(katok)은 **로컬 검색·조회 전용**입니다. 서로 다른 연동이므로 혼동하지 않는다.
- Mac 환경이 아직 없다면 `kostat-kakao-export-search`(Windows 카카오톡 PC 클라이언트의
  "대화 내보내기" txt 파일 로컬 검색, 별도 CLI 설치 불필요)를 대신 사용할 수 있다.
  자동 동기화·semantic 검색은 없지만 지금 바로 Windows에서 쓸 수 있다.
