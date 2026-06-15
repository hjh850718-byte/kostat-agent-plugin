## AUTOMATION 연동 (Level 7 Python 시스템)
```
AUTOMATION/
├── kostat_poller.py         ← POP3 폴링 + ThreadPoolExecutor 병렬 처리
├── trigger_classifier.py    ← 메일/파일/입력 → ClassificationResult 분류
├── orchestrator_bridge.py   ← ClassificationResult → Skill/direct 실행
├── pop3_watcher.py          ← 기존 (호환성 유지)
├── router.py                ← 기존 (호환성 유지)
├── handlers.py              ← 기존 (호환성 유지)
├── telegram_client.py       ← Telegram 발송
├── claude_client.py         ← Claude API 호출
├── processed_ids.json       ← 중복 방지 캐시
└── task_logs/               ← Task 실행 로그
```

## Orchestrator 연동 규칙
- `ORCHESTRATOR_ENGINE=direct`: handlers.py 직접 호출 (기존)
- `ORCHESTRATOR_ENGINE=claude`: Claude Code subprocess 실행 (fanout 모드)
- `.env`에서 ENGINE 전환 가능
- Task 타임아웃: 10분 / 재시도: 1회 / 동시 실행: 최대 4개
