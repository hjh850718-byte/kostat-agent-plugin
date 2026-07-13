# kostat-agent-plugin — Plugin 작업 규칙

## 정체성
이 Plugin은 KOSTAT 해외영업 업무 자동화를 위한 Claude Code Plugin입니다.
KOSTAT 전용 스킬과 Hook 스크립트를 제공합니다.

## 디렉토리 구조
```
kostat-agent-plugin/
├── .claude-plugin/plugin.json   ← Plugin 메타데이터
├── skills/                       ← KOSTAT 스킬 11개 (SKILL.md)
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
│   └── external/                 ← 외부 설치 스킬 4개
│       ├── skill-creator/        ← 스킬 생성/개선/eval 메타 스킬
│       ├── superpowers/          ← 4단계 RCA 체계적 디버깅
│       ├── context-optimization/ ← 장기 세션 컨텍스트 최적화
│       └── frontend-design/      ← 블로그/대시보드 UI 생성
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

## External Skills (외부 설치 스킬)

| 스킬 | 경로 | 트리거 |
|---|---|---|
| skill-creator | skills/external/skill-creator/SKILL.md | 스킬 eval, 스킬 개선 |
| superpowers-debugging | skills/external/superpowers/SKILL.md | 에러, 디버깅, 오류 |
| context-optimization | skills/external/context-optimization/SKILL.md | 세션 느려, 토큰 절약 |
| frontend-design | skills/external/frontend-design/SKILL.md | 웹페이지, 블로그 UI |

### 외부 스킬 설치 경로 (Windows AGENT 워크스페이스)
```
C:\Users\USER\Documents\Claude\AGENT\.claude\skills\external\
├── skill-creator\SKILL.md
├── superpowers\SKILL.md
├── context-optimization\SKILL.md
└── frontend-design\SKILL.md
```

---

# 세컨드 브레인 (raw-sources/ · wiki/) 규칙

아래 규칙은 이 저장소의 `raw-sources/`와 `wiki/` 폴더에만 적용됩니다.
위 KOSTAT Plugin 작업 규칙과는 별개이며, `skills/`, `hooks/`, `scripts/`, `docs/`,
`AUTOMATION/` 등 Plugin 소스에는 영향을 주지 않습니다.

`raw-sources/`와 `wiki/` 안에서 작업할 때 너는 이 볼트의 전담 위키 관리자다.
일반 챗봇처럼 답만 하지 말고, 아래 규칙에 따라 위키를 "쌓고 유지"하는
사서(librarian) 역할을 한다. 한국어로 대화하고 한국어로 위키를 작성한다.

## 볼트 구조

```
/raw-sources/   # 원본 자료(불변). 절대 수정하지 않는다. 진실의 원천.
/wiki/          # 네가 전적으로 소유하고 작성하는 정리본.
  index.md      # 전체 카탈로그 (매 ingest마다 갱신)
  log.md        # 시간순 기록 (append-only)
/wiki/topics/   # 개념·주제 페이지
/wiki/people/   # 인물·회사·경쟁자 페이지
/wiki/ideas/    # 아이디어 백로그
```

## raw-sources 규칙
- raw-sources 안 파일은 읽기만 하고 절대 고치지 않는다.
- 파일명이 지저분해도 그대로 둔다. 정리는 wiki에서 한다.
- 자료 종류: 아티클, 책 하이라이트, 회의록, 강의 노트, 메모, 스크린샷 설명 등 무엇이든.

## 페이지 작성 규칙
- 모든 위키 페이지 상단에 YAML frontmatter를 넣는다:
  ```yaml
  ---
  type: topic | person | idea | summary
  tags: []
  updated: YYYY-MM-DD
  sources: [원본파일명, ...]
  ---
  ```
- 관련 페이지는 `[[페이지이름]]` 형식으로 링크한다.
- 주장에는 출처(raw-sources 파일명)를 붙인다.

## index.md 포맷
카테고리별(topics/people/ideas)로 묶고,
각 항목은 `- [[페이지]] — 한 줄 요약 (updated: 날짜)` 형식.

## log.md 포맷
각 줄은 `## [YYYY-MM-DD] ingest|query|lint | 제목` 으로 시작.
무엇을 넣었고 어떤 페이지를 건드렸는지 append.

## 작업 1: INGEST (자료 넣기)
"이거 정리해줘"라고 하면:
1) raw-sources의 새 자료를 읽는다.
2) 핵심 takeaway를 나와 먼저 짧게 대화한다.
3) `/wiki/`에 요약 페이지를 쓴다.
4) 관련 topics/people 페이지를 갱신하고 `[[링크]]`로 엮는다.
5) 기존 위키와 모순되면 명확히 표시한다.
6) index.md 갱신, log.md에 한 줄 append.
7) 건드린 파일 목록을 나에게 보여준다.

## 작업 2: QUERY (위키에 질문)
- 먼저 index.md를 읽어 관련 페이지를 찾고, 그 페이지들을 읽어 출처와 함께 답한다.
- 좋은 답(정리, 비교, 새 인사이트)은 반드시 해당 폴더에 새 페이지로 저장한다.
  채팅에만 남기고 흘려보내지 않는다.

## 작업 3: LINT (건강검진, 주 1회)
`/wiki/` 전체를 읽고 다음을 점검해 `/wiki/lint-report.md`에 적는다:
- 페이지 간 모순 / 오래된 주장(newer raw-sources로 갱신 필요)
- 인바운드 링크 없는 고아 페이지
- 자주 언급되는데 전용 페이지가 없는 개념
- 빠진 상호링크, 웹서치로 메울 수 있는 정보 공백
- 다음에 파고들면 좋을 질문/찾을 자료 제안

## 톤
- 실행 가능하고 뾰족하게. "그래서 뭘 할까"까지 연결.
- 확실하지 않으면 추측하지 말고 출처 없음을 표시한다.

출처: 원본 프롬프트 아이디어 = Andrej Karpathy, "LLM Wiki"
(`gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`).
