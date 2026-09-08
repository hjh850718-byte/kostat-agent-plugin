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
