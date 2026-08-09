# kostat-agent-plugin — Plugin 작업 규칙

## 정체성
이 Plugin은 KOSTAT 해외영업 업무 자동화를 위한 Claude Code Plugin입니다.
KOSTAT 전용 스킬과 Hook 스크립트를 제공합니다.

## 디렉토리 구조
```
kostat-agent-plugin/
├── .claude-plugin/plugin.json   ← Plugin 메타데이터
├── skills/                       ← KOSTAT 스킬 13개 (SKILL.md)
│   ├── kostat-orchestrator/      ← Level 7 Orchestrator
│   ├── kostat-po-update/         ← Level 6 Fan-out 3way
│   ├── kostat-hk-po-update/      ← Level 6 Fan-out 2way [신규 업그레이드]
│   ├── kostat-oor-weekly/        ← Level 6 Fan-out 2way
│   ├── kostat-commission-invoice/ ← Level 6 Gen/Eval Loop
│   ├── kostat-eod-retrospective/ ← Level 6 Fan-out 2way [신규 업그레이드]
│   ├── kostat-morning-briefing/
│   ├── kostat-memory-ticket/
│   ├── kostat-skill-check/
│   ├── kostat-memory-loader/
│   ├── kostat-tal/
│   ├── kostat-katok-search/      ← katok CLI 연동 (카카오톡 로컬 검색, macOS 전용, 설계 단계)
│   └── kostat-kakao-export-search/ ← 카카오톡 대화 내보내기 txt 로컬 검색 (Windows 가능)
├── scripts/                      ← 실행 스크립트
│   └── kostat-team.sh            ← tmux 멀티탭 팀 실행
├── hooks/                        ← Hook Python 스크립트 9개 + hooks.json
├── docs/                         ← 참고 자료 (설계 문서 등)
├── CLAUDE.md                     ← 이 파일
├── package.json                  ← 버전/의존성
└── README.md                     ← 설치/사용법
```

## AUTOMATION 연동 (Level 7 Python 시스템)
```
AUTOMATION/
├── kostat_poller.py              ← POP3 폴링 + ThreadPoolExecutor 병렬 처리
├── trigger_classifier.py         ← 메일/파일/입력 → 트리거 분류 (ClassificationResult)
├── orchestrator_bridge.py        ← ClassificationResult → Skill/direct 실행
├── pop3_watcher.py               ← 기존 (호환성 유지)
├── router.py                     ← 기존 (호환성 유지)
├── handlers.py                   ← 기존 (호환성 유지)
├── telegram_client.py            ← Telegram 발송
├── claude_client.py              ← Claude API 호출
├── processed_ids.json            ← 중복 방지 캐시
└── task_logs/                    ← Task 실행 로그
```

## 변경 시 규칙
- skills/의 SKILL.md를 수정한 후에는 Claude Code 설정에서 플러그인 재설치 필요
  - 재설치 전까지 Claude는 AppData 캐시(구버전)를 사용함
  - 설정 경로: Claude 앱 → Settings → Capabilities → 플러그인 재설치
- hooks/의 Python 스크립트는 `Documents/Claude/claude-tray/`와 동기화 유지
- package.json의 version은 semantic versioning 준수
- 주요 변경 시 `docs/08. KOSTAT Plugin 패키징 설계.md`도 함께 업데이트

## 소스 vs 설치본 구분
| 위치 | 역할 | 편집 가능 |
|------|------|----------|
| `kostat-agent-plugin/skills/` | 소스 원본 | ✅ 직접 편집 |
| AppData\Roaming\Claude\...\skills\ | 설치 캐시 | ❌ 플러그인 재설치로만 갱신 |

## Python 호출 규칙
- hooks.json에서 항상 `python "..."` 형식 사용 (Windows 호환)
- `python3`는 Windows에서 없을 수 있으므로 사용 금지
- shebang(`#!/usr/bin/env python3`)은 유지 가능 (Windows에서 무시됨)

## Orchestrator 연동 규칙 (Level 7)
- `ORCHESTRATOR_ENGINE=direct`: handlers.py 직접 호출 (기존)
- `ORCHESTRATOR_ENGINE=claude`: Claude Code subprocess 실행 (fanout 모드)
- `.env`에서 ENGINE 전환 가능
- Task 타임아웃: 10분, 재시도: 1회, 동시 실행: 최대 4개

## katok(카카오톡 로컬 검색) 연동 상태
- `kostat-katok-search` 스킬은 [NomaDamas/katok](https://github.com/NomaDamas/katok) CLI를
  실행 표면으로 사용해 고객사 카카오톡 대화를 로컬 검색한다.
- katok은 **Apple Silicon macOS 전용**(EmbeddingGemma 로컬 임베딩이 ONNX Runtime prebuilt를
  `x86_64-apple-darwin`용으로 제공하지 않음)이며, 이 플러그인의 기본 작업 환경(Windows PC)에서는
  실행할 수 없다. 현재는 문서/설계 단계이며, 실제 Mac 환경이 준비되기 전까지 스킬은 항상
  "미충족" 안내만 출력하고 종료하도록 설계돼 있다.
- 기존 `kostat-morning-briefing`의 "KakaoTalk (MCP)"는 PlayMCP를 통한 **발송**용이고, katok은
  **로컬 검색·조회 전용**이다. 서로 다른 연동이므로 문서·코드에서 혼동하지 않는다.
- `katok send`(메시지 전송)는 이 플러그인 통합 범위에서 명시적으로 제외한다.
- Mac 환경이 없는 동안에는 `kostat-kakao-export-search`(Windows 카카오톡 PC 클라이언트의
  "대화 내보내기" txt 로컬 검색, 별도 CLI 불필요)를 대체 수단으로 쓴다. 자동 동기화·semantic
  검색은 없고 사용자가 수동으로 재내보내기를 해야 최신화된다.
