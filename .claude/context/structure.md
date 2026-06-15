## 디렉토리 구조
```
kostat-agent-plugin/
├── .claude-plugin/plugin.json
├── skills/                        ← KOSTAT 스킬 11개
│   ├── kostat-orchestrator/       ← Level 7 Orchestrator
│   ├── kostat-po-update/          ← Level 6 Fan-out 3way
│   ├── kostat-hk-po-update/       ← Level 6 Fan-out 2way
│   ├── kostat-oor-weekly/         ← Level 6 Fan-out 2way
│   ├── kostat-commission-invoice/ ← Level 6 Gen/Eval Loop
│   ├── kostat-eod-retrospective/  ← Level 6 Fan-out 2way
│   ├── kostat-morning-briefing/
│   ├── kostat-memory-ticket/
│   ├── kostat-skill-check/
│   ├── kostat-memory-loader/
│   └── kostat-tal/
├── scripts/kostat-team.sh         ← tmux 멀티탭 팀 실행
├── hooks/                         ← Hook Python 스크립트 9개 + hooks.json
├── docs/
├── CLAUDE.md
├── package.json
└── README.md
```
