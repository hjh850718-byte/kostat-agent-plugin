# KOSTAT Agent Plugin

KOSTAT 해외영업 업무 자동화를 위한 Claude Code Plugin **모음**입니다.
PO PDF → Excel 입력, OOR Bring Forward 분석, 커미션 인보이스 생성, EOD KPT 회고, 아침 브리핑 등
11개 스킬을 제공하며, 업무 성격별로 나뉜 **5개 플러그인**으로 구성되어 있어 필요한 것만 골라 설치할 수 있습니다.

---

## 왜 플러그인이 5개인가

폴더마다 하는 일이 다르면(PO 입력만 하는 폴더, OOR만 처리하는 폴더 등), 그 폴더에 필요 없는 스킬·hook까지
항상 함께 로드되는 것은 낭비이고 방해가 됩니다. 그래서 하나의 거대한 플러그인 대신 업무 단위로 쪼갰습니다.

| 플러그인 | 역할 | 필수 여부 |
|----------|------|-----------|
| **kostat-core** | Orchestrator, 메모리 로더, Human Gate 승인, 자동 백업, Trace 로깅, 작업공간 라우팅 | ✅ 항상 필수 |
| **kostat-po** | 미국/홍콩 PO(Purchase Order) 자동 업데이트 | PO 작업 폴더에만 |
| **kostat-oor** | 주간 OOR(Open Order Report) Bring Forward 분석 | OOR 작업 폴더에만 |
| **kostat-commission** | 월간 커미션 인보이스 생성 및 검증 | 커미션 작업 폴더에만 |
| **kostat-eod** | 모닝 브리핑 + EOD KPT 회고 | 하루 시작/종료 루틴이 필요한 폴더에만 |

`kostat-po`, `kostat-oor`, `kostat-commission`, `kostat-eod`는 모두 `kostat-core`가 제공하는
Human Gate·자동 백업·Trace 로깅 인프라에 의존하므로, **kostat-core와 함께 설치**해야 합니다.

---

## 설치 방법

### 방법 1: GitHub Marketplace (권장)

```bash
# 마켓플레이스 추가
/plugin marketplace add https://github.com/hjh850718-byte/kostat-agent-plugin

# 필수: 공통 인프라
/plugin install kostat-core@kostat-agent

# 필요한 업무 플러그인만 선택 설치
/plugin install kostat-po@kostat-agent
/plugin install kostat-oor@kostat-agent
/plugin install kostat-commission@kostat-agent
/plugin install kostat-eod@kostat-agent
```

모든 업무를 한 폴더에서 처리한다면 5개 모두 설치하면 됩니다.
업무별로 폴더를 나눠 쓴다면, 그 폴더가 실제로 하는 일에 맞는 플러그인만 설치하세요
(예: PO 전용 폴더 → `kostat-core` + `kostat-po`).

### 방법 2: 로컬 디렉토리

```bash
# 원하는 플러그인만 각각 복사 (예: core + po)
mkdir -p ~/.claude/plugins/kostat-core ~/.claude/plugins/kostat-po
cp -r kostat-agent-plugin/plugins/kostat-core/* ~/.claude/plugins/kostat-core/
cp -r kostat-agent-plugin/plugins/kostat-po/* ~/.claude/plugins/kostat-po/

# settings.json에 활성화
# "enabledPlugins": { "kostat-core@local": true, "kostat-po@local": true }
```

---

## 포함된 스킬 (플러그인별)

### kostat-core
| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-orchestrator | 트리거 감지 → 에이전트팀 병렬 소집 → 결과 취합 | 자동 (Orchestrator) | L7 |
| kostat-memory-loader | KOSTAT 컨텍스트 로드 | '컨텍스트 로드', '메모리 로드' (자동) | L1 |
| kostat-memory-ticket | Memory Ticket 발행 (학습/판단 기준 기록) | '/memory-ticket' | L1 |
| kostat-skill-check | 스킬 상태 점검 (Lifecycle 관리) | '/skill-check' | L1 |
| kostat-tal | KOSTAT 판단 기준 로드 | '판단 기준', 'tal', '가이드라인' | L1 |

### kostat-po
| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-po-update | PO PDF → Excel 입력 (3way Fan-out) | 'PO 업데이트', 'PO 입력', PO 번호 | L6 |
| kostat-hk-po-update | HK(Xview Asia) PO PDF → Excel 입력 (2way Fan-out) | 'HK PO', 'XVIEW PO' | L6 |

### kostat-oor
| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-oor-weekly | OOR Bring Forward 분석 (2way Fan-out) | 'OOR', 'Open Order', 'Bring Forward' | L6 |

### kostat-commission
| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-commission-invoice | 커미션 인보이스 생성 및 검증 (Gen/Eval Loop) | '커미션', 'commission', 'invoice' | L6 |

### kostat-eod
| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-eod-retrospective | EOD KPT 회고록 자동 생성 (2way Fan-out) | '업무끝', 'EOD', '회고', 'KPT' | L6 |
| kostat-morning-briefing | `/kostat` 아침 브리핑 + Gmail 분류 | '/kostat', '출근', '아침' | L1 |

---

## 커넥터

| 서비스 | 용도 | 필수 |
|--------|------|------|
| Gmail (MCP) | 이메일 분류, PO/OOR 메일 감지 | 권장 |
| Google Calendar (MCP) | PO 납기일 등록 | 선택 |
| Telegram Bot | 작업 완료 알림 | 권장 |
| Notion (MCP) | KPT 저장, Memory Ticket 보관 | 선택 |
| KakaoTalk (MCP) | 알림 수신 | 선택 |

> 상세: [CONNECTORS.md](CONNECTORS.md)

---

## Hook 스크립트

### kostat-core (8개 — 모든 업무 공통)
| 스크립트 | Hook 포인트 | 기능 |
|----------|------------|------|
| kostat-workspace-router.py | UserPromptSubmit | 프롬프트 분석 → 작업공간·Skill 라우팅 안내 |
| kostat-gateguard.py | PreToolUse (Write\|Edit) | Human Gate 승인 확인 |
| kostat-autobackup.py | PreToolUse (Write\|Edit) | 수정 전 자동 백업 |
| kostat-observe.py | PostToolUse (Write\|Edit) | 변경 사항 관찰 로깅 |
| kostat-tracelogger.py | PostToolUse (Write\|Edit) | Trace Log 기록 |
| kostat-handoff-writer.py | PostToolUse (Write\|Edit) | 에이전트 핸드오프 파일 기록 |
| kostat-ai-bridge.py | SessionStart / Stop | `.ai-bridge/` 세션 컨텍스트 초기화·종료 기록 |
| kostat-compact.py | PreCompact | 컨텍스트 압축 전 상태 기록 |

### kostat-eod (3개 — 하루 시작/종료 전용)
| 스크립트 | Hook 포인트 | 기능 |
|----------|------------|------|
| kostat-eod-detector.py | UserPromptSubmit | 업무종료 키워드 실시간 감지 → flag 기록 |
| kostat-eod-sessionstart.py | SessionStart | EOD 재접속 감지 (6시 이후 회고 제안) |
| kostat-eod-stop.py | Stop | 세션 종료 시 EOD 로깅 + pending_retro flag |

---

## 프로젝트 구조

```
kostat-agent-plugin/
├── .claude-plugin/
│   └── marketplace.json    ← 마켓플레이스 카탈로그 (5개 플러그인 등록)
├── plugins/
│   ├── kostat-core/
│   │   ├── .claude-plugin/plugin.json
│   │   ├── skills/          ← orchestrator, memory-loader, memory-ticket, skill-check, tal
│   │   └── hooks/           ← hooks.json + *.py (8개)
│   ├── kostat-po/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/          ← kostat-po-update, kostat-hk-po-update (+ references/)
│   ├── kostat-oor/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/kostat-oor-weekly (+ references/)
│   ├── kostat-commission/
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/kostat-commission-invoice (+ references/)
│   └── kostat-eod/
│       ├── .claude-plugin/plugin.json
│       ├── skills/          ← kostat-eod-retrospective, kostat-morning-briefing
│       └── hooks/           ← hooks.json + *.py (3개)
├── scripts/                 ← 실행 스크립트
│   └── kostat-team.sh
├── docs/                    ← 참고 자료 (설계 문서 등)
├── CONNECTORS.md            ← 외부 서비스 연결 현황
├── LICENSE                  ← MIT License
├── CLAUDE.md                ← Plugin 작업 규칙
├── package.json
└── README.md
```

---

## 버전

현재 버전: 2.0.0 (단일 플러그인 → 5개 플러그인 마켓플레이스 구조로 개편)

## 라이선스

MIT License — 자유로운 사용, 수정, 배포가 가능합니다.
단, 외부 공개 시 고객사 정보 등 민감 데이터가 포함되지 않도록 주의하세요.
