# kostat-agent-plugin — Plugin 작업 규칙

## 정체성
이 저장소는 KOSTAT 해외영업 업무 자동화를 위한 Claude Code Plugin **모음(마켓플레이스)**입니다.
하나의 거대한 플러그인 대신, 업무 성격별로 나뉜 5개의 독립 플러그인을 제공합니다.
사용자는 자신이 일하는 폴더(PO 전용 폴더, OOR 전용 폴더 등)에 필요한 플러그인만 골라 설치할 수 있습니다.
(참고: [요즘IT — 폴더 단위로 설정 쪼개기](https://yozm.wishket.com/magazine/detail/3931/)의 "폴더마다 필요한 것만 켠다" 원칙을 플러그인 단위로 적용한 구조입니다.)

## 왜 5개로 쪼갰나
Claude Code Plugin은 스킬 폴더를 한 단계 이상 중첩할 수 없고(`skills/<name>/SKILL.md` 고정),
hook도 스킬 단위로 켜고 끌 수 없습니다(이벤트 타입 + 도구 매처 정규식이 전부).
그래서 "필요한 것만 로드"를 구현하는 유일한 방법은 **플러그인 자체를 업무 단위로 분리**하는 것입니다.
분리하지 않으면, 예를 들어 PO 작업만 하는 폴더에서도 EOD 회고 hook·모닝 브리핑 스킬까지 항상 함께 로드됩니다.

## 디렉토리 구조
```
kostat-agent-plugin/
├── .claude-plugin/marketplace.json   ← 마켓플레이스 카탈로그 (5개 플러그인 등록)
├── plugins/
│   ├── kostat-core/                  ← 필수. 모든 작업 폴더에 설치
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/                   ← orchestrator, memory-loader, memory-ticket, skill-check, tal
│   │   └── hooks/                    ← gateguard, autobackup, observe, tracelogger,
│   │                                    handoff-writer, ai-bridge, workspace-router, compact (8개)
│   ├── kostat-po/                    ← 미국/홍콩 PO 전담 폴더에만 설치
│   │   └── skills/                   ← kostat-po-update, kostat-hk-po-update
│   ├── kostat-oor/                   ← OOR 전담 폴더에만 설치
│   │   └── skills/kostat-oor-weekly
│   ├── kostat-commission/            ← 커미션 인보이스 전담 폴더에만 설치
│   │   └── skills/kostat-commission-invoice
│   └── kostat-eod/                   ← 하루 시작/종료 루틴이 필요한 폴더에만 설치
│       ├── skills/                   ← kostat-eod-retrospective, kostat-morning-briefing
│       └── hooks/                    ← eod-detector, eod-sessionstart, eod-stop (3개)
├── skills/external/                  ← 플러그인이 아닌 별도 워크스페이스(AGENT)로 수동 동기화되는 외부 스킬 4개
│   ├── skill-creator/, superpowers/, context-optimization/, frontend-design/
│   └── (상세: 아래 "External Skills" 절 참고 — plugins/ 마켓플레이스와 무관)
├── raw-sources/ , wiki/              ← 세컨드 브레인 볼트 (아래 별도 절 참고 — Plugin 소스와 무관)
├── scripts/                          ← 실행 스크립트
│   └── kostat-team.sh                ← tmux 멀티탭 팀 실행
├── docs/                             ← 참고 자료 (설계 문서 등)
├── CLAUDE.md                         ← 이 파일
├── package.json                      ← 저장소(레포) 버전
└── README.md                         ← 설치/사용법
```

각 `plugins/kostat-*/`는 그 자체로 완결된 Claude Code Plugin입니다(`.claude-plugin/plugin.json` 보유).
`kostat-po`, `kostat-oor`, `kostat-commission`, `kostat-eod`는 모두 `kostat-core`가 제공하는
Human Gate·자동 백업·Trace 로깅에 의존하므로, **kostat-core 없이 단독 설치하지 않습니다.**

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
- `plugins/*/skills/`의 SKILL.md를 수정한 후에는 Claude Code 설정에서 해당 플러그인 재설치 필요
  - 재설치 전까지 Claude는 AppData 캐시(구버전)를 사용함
  - 설정 경로: Claude 앱 → Settings → Capabilities → 플러그인 재설치
- `plugins/*/hooks/`의 Python 스크립트는 `Documents/Claude/claude-tray/`와 동기화 유지
- 새 스킬을 추가할 때는 어느 플러그인 소속인지부터 정한다 (공통 인프라 → kostat-core, 특정 업무 전용 → 해당 도메인 플러그인, 애매하면 새 플러그인 신설을 검토)
- 각 `plugins/kostat-*/.claude-plugin/plugin.json`의 `version`과 루트 `package.json`의 `version`은 semantic versioning 준수
- 주요 변경 시 `docs/08. KOSTAT Plugin 패키징 설계.md`도 함께 업데이트

## 소스 vs 설치본 구분
| 위치 | 역할 | 편집 가능 |
|------|------|----------|
| `kostat-agent-plugin/plugins/*/skills/` | 소스 원본 | ✅ 직접 편집 |
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
