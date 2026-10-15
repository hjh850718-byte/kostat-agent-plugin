# KOSTAT 해외영업 업무 자동화 시스템

**담당자:** 한준희 과장 | **버전:** 1.0.0 | **최종 수정:** 2026-06-14

> Windows Task Scheduler + Python으로 KOSTAT-AGENT 루틴을 완전 자동화합니다.
> 외부 발송(이메일, 카카오톡)은 반드시 사람이 Telegram 승인 후 실행됩니다.

---

## 디렉토리 구조

```
kostat-automation/
├── runner.py                        ← 메인 실행 래퍼 (Task Scheduler가 호출)
├── .env                             ← 환경변수 (Telegram 토큰 등 — Git 미포함)
├── .env.example                     ← 환경변수 템플릿
├── scheduler/
│   ├── setup_tasks.ps1              ← Windows Task Scheduler 일괄 등록
│   └── task_definitions.json        ← 루틴 정의 (일정 + 프롬프트 + 게이트 설정)
├── notifier/
│   └── telegram_notify.py           ← Telegram Bot API 알림 모듈
├── gates/
│   └── approval_gate.py             ← 검수 게이트 (Y/N 승인 로직)
├── README.md                        ← 이 파일
└── SETUP.md                         ← 최초 설정 가이드
```

---

## 자동화 루틴 요약

| 루틴 | 스케줄 | 검수 게이트 | 설명 |
|------|--------|------------|------|
| `KOSTAT_MorningBriefing` | 매일 08:10 | 없음 | `/morning` 실행 → Telegram |
| `KOSTAT_OOR_WeeklyCheck` | 매주 월 09:00 | 없음 | OOR 수신 여부 확인 → Telegram |
| `KOSTAT_CommissionInvoice` | 매월 1일 09:00 | 없음 | 커미션 인보이스 리마인드 → Telegram |
| `KOSTAT_EOD_Retrospective` | 매일 18:30 | 쓰기 승인 | KPT 초안 → Notion 저장 |

---

## 게이트 정책

| 작업 유형 | 게이트 | 동작 |
|----------|--------|------|
| 읽기 전용 (조회, 분석, 브리핑) | 없음 | 자동 실행 |
| 쓰기 (파일 생성, Notion 저장) | Telegram Y/N | 60초 미응답 시 기본값(Y) 자동 처리 |
| 외부 발송 (이메일, 카카오톡) | Telegram Y/N 필수 | 미응답 시 자동 차단(N) |

---

## 실행 흐름

```
Task Scheduler
     │
     ▼
runner.py <task_name>
     │
     ├─ task_definitions.json 로드
     │
     ├─ [approval_gate = true] ──▶ approval_gate.py
     │                                    │
     │                                    ├─ Telegram 승인 요청 발송
     │                                    └─ getUpdates 폴링 (Y/N)
     │
     ├─ claude --dangerously-skip-permissions -p "<prompt>"
     │     └─ 실패 시 최대 3회 재시도 (2s → 4s → 8s)
     │
     └─ Telegram 결과 알림 + 로그 기록
              C:\Users\USER\Desktop\77. CLOUDE 정리용\logs\YYYY-MM-DD.log
```

---

## 빠른 시작

```powershell
# 1. .env 파일 생성
copy .env.example .env
notepad .env   # TELEGRAM_BOT_TOKEN 입력

# 2. Task Scheduler 등록
powershell -ExecutionPolicy Bypass -File .\scheduler\setup_tasks.ps1

# 3. 연결 테스트
python notifier\telegram_notify.py "테스트 메시지"
```

자세한 설정은 **SETUP.md** 참조.

---

## 로그 위치

- 실행 로그: `C:\Users\USER\Desktop\77. CLOUDE 정리용\logs\YYYY-MM-DD.log`
- Task Scheduler 이벤트: 작업 스케줄러 → KOSTAT 폴더 → 기록 탭

---

## 7월 9일 미국 출장 전 체크리스트

- [ ] `.env` 파일에 `TELEGRAM_BOT_TOKEN` 설정 완료
- [ ] `setup_tasks.ps1` 실행 후 4개 태스크 등록 확인
- [ ] 모닝 브리핑 수동 테스트 1회 성공
- [ ] EOD 게이트 Telegram 응답 테스트 (Y/N 응답 확인)
- [ ] 출장 중 PC 절전 해제 설정 (제어판 → 전원 옵션 → 절전 안 함)
- [ ] 로그 파일 정기 정리 스크립트 설정 (선택)
