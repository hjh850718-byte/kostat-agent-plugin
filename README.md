# KOSTAT Agent Plugin

KOSTAT 해외영업 업무 자동화를 위한 Claude Code Plugin입니다.
PO PDF → Excel 입력, OOR Bring Forward 분석, 커미션 인보이스 생성, EOD KPT 회고, 아침 브리핑 등 11개 스킬을 제공합니다.

---

## 설치 방법

### 방법 1: GitHub Marketplace (권장)

```bash
# 마켓플레이스 추가
/plugin marketplace add https://github.com/hjh850718-byte/kostat-agent-plugin

# 플러그인 설치
/plugin install kostat-agent@kostat-agent
```

### 방법 2: 로컬 디렉토리

```bash
# Plugin 디렉토리 생성
mkdir -p ~/.claude/plugins/kostat-agent

# Plugin 파일 복사
cp -r kostat-agent-plugin/* ~/.claude/plugins/kostat-agent/

# settings.json에 활성화
# "enabledPlugins": { "kostat-agent@local": true }
```

---

## 포함된 스킬

| 스킬 | 설명 | 트리거 | 레벨 |
|------|------|--------|------|
| kostat-orchestrator | 트리거 감지 → 에이전트팀 병렬 소집 → 결과 취합 | 자동 (Orchestrator) | L7 |
| kostat-po-update | PO PDF → Excel 입력 (3way Fan-out) | 'PO 업데이트', 'PO 입력', PO 번호 | L6 |
| kostat-hk-po-update | HK(Amkor) PO PDF → Excel 입력 (2way Fan-out) | 'HK PO', 'Amkor PO' | L6 |
| kostat-oor-weekly | OOR Bring Forward 분석 (2way Fan-out) | 'OOR', 'Open Order', 'Bring Forward' | L6 |
| kostat-commission-invoice | 커미션 인보이스 생성 및 검증 (Gen/Eval Loop) | '커미션', 'commission', 'invoice' | L6 |
| kostat-eod-retrospective | EOD KPT 회고록 자동 생성 (2way Fan-out) | '업무끝', 'EOD', '회고', 'KPT' | L6 |
| kostat-morning-briefing | `/kostat` 아침 브리핑 + Gmail 분류 | '/kostat', '출근', '아침' | L1 |
| kostat-memory-loader | KOSTAT 컨텍스트 로드 | '컨텍스트 로드', '메모리 로드' (자동) | L1 |
| kostat-memory-ticket | Memory Ticket 발행 (학습/판단 기준 기록) | '/memory-ticket' | L1 |
| kostat-skill-check | 스킬 상태 점검 (Lifecycle 관리) | '/skill-check' | L1 |
| kostat-tal | KOSTAT 판단 기준 로드 | '판단 기준', 'tal', '가이드라인' | L1 |

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

플러그인과 함께 7개의 Hook 스크립트가 제공됩니다:

| 스크립트 | Hook 포인트 | 기능 |
|----------|------------|------|
| kostat-eod-detector.py | SessionStart | EOD 재접속 감지 (6시 이후 회고 제안) |
| kostat-eod-stop.py | Stop | 세션 종료 시 EOD 로깅 + pending_retro flag |
| kostat-gateguard.py | PreToolUse (Write\|Edit) | Human Gate 승인 확인 |
| kostat-autobackup.py | PreToolUse (Write\|Edit) | 수정 전 자동 백업 |
| kostat-observe.py | PostToolUse (Write\|Edit) | 변경 사항 관찰 로깅 |
| kostat-tracelogger.py | PostToolUse (Write\|Edit) | Trace Log 기록 |
| kostat-compact.py | PreCompact | 컨텍스트 압축 전 작업 |

---

## 프로젝트 구조

```
kostat-agent-plugin/
├── .claude-plugin/
│   ├── marketplace.json    ← 마켓플레이스 카탈로그
│   └── plugin.json         ← 플러그인 메타데이터
├── skills/                 ← KOSTAT 스킬 11개 (SKILL.md)
│   ├── kostat-orchestrator/
│   ├── kostat-po-update/
│   ├── kostat-hk-po-update/
│   ├── kostat-oor-weekly/
│   ├── kostat-commission-invoice/
│   ├── kostat-eod-retrospective/
│   ├── kostat-morning-briefing/
│   ├── kostat-memory-loader/
│   ├── kostat-memory-ticket/
│   ├── kostat-skill-check/
│   └── kostat-tal/
├── references/             ← 상세 매핑/규칙 (토큰 절감용 분리)
│   ├── rate-tables.md
│   ├── column-map.md
│   ├── field-mapping.md
│   └── xview-mapping.md
├── hooks/                  ← Hook Python 스크립트
│   ├── hooks.json
│   └── *.py
├── scripts/                ← 실행 스크립트
│   └── kostat-team.sh
├── docs/                   ← 참고 자료 (설계 문서 등)
├── CONNECTORS.md           ← 외부 서비스 연결 현황
├── LICENSE                 ← MIT License
├── CLAUDE.md               ← Plugin 작업 규칙
├── package.json
└── README.md
```

---

## 버전

현재 버전: 1.0.0

## 라이선스

MIT License — 자유로운 사용, 수정, 배포가 가능합니다.
단, 외부 공개 시 고객사 정보 등 민감 데이터가 포함되지 않도록 주의하세요.
