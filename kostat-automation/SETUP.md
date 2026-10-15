# KOSTAT 자동화 최초 설정 가이드

> **목표:** 7월 9일 미국 출장 전까지 4개 루틴 완전 자동화 완료

---

## 사전 조건 확인

```powershell
# 1) Python 설치 확인 (3.9 이상 필요)
python --version

# 2) Claude Code CLI 설치 확인
claude --version

# 3) npm 글로벌 경로 확인
npm root -g
```

모두 정상 출력되어야 합니다.

---

## Step 1 — 파일 배치

자동화 폴더를 작업 디렉토리에 복사합니다.

```
C:\Users\USER\Desktop\77. CLOUDE 정리용\
└── kostat-automation\          ← 이 폴더 전체를 여기에 놓으세요
    ├── runner.py
    ├── .env.example
    ├── scheduler\
    ├── notifier\
    └── gates\
```

---

## Step 2 — 환경변수 설정 (.env)

```powershell
# 작업 폴더로 이동
cd "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation"

# .env 파일 생성
copy .env.example .env
notepad .env
```

`.env` 파일 내용:

```env
# Telegram Bot 설정
TELEGRAM_BOT_TOKEN=<여기에_봇_토큰_입력>
TELEGRAM_CHAT_ID=8761375155

# Claude 작업 디렉토리 (CLAUDE.md가 있는 경로)
CLAUDE_WORK_DIR=C:\Users\USER\Documents\Claude\AGENT
```

### Telegram Bot 토큰 발급 방법

1. Telegram에서 `@BotFather` 검색
2. `/newbot` 명령어 입력
3. 봇 이름 입력 → 토큰 발급
4. 발급된 토큰을 `TELEGRAM_BOT_TOKEN`에 입력

> ⚠️ 기존 `@Junheehanbot`의 토큰이 있다면 그대로 사용하세요.

---

## Step 3 — Telegram 연결 테스트

```powershell
cd "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation"
python notifier\telegram_notify.py "✅ KOSTAT 자동화 연결 테스트"
```

Telegram `@Junheehanbot` 채팅방에 메시지가 오면 성공입니다.

---

## Step 4 — Task Scheduler 등록

PowerShell을 열고 (관리자 권한 불필요):

```powershell
cd "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation"
powershell -ExecutionPolicy Bypass -File .\scheduler\setup_tasks.ps1
```

성공 시 출력:

```
✅ [KOSTAT_MorningBriefing] 등록 완료 — 매일 08:10
✅ [KOSTAT_OOR_WeeklyCheck] 등록 완료 — 매주 월요일 09:00
✅ [KOSTAT_CommissionInvoice] 등록 완료 — 매월 1일 09:00
✅ [KOSTAT_EOD_Retrospective] 등록 완료 — 매일 18:30
```

---

## Step 5 — 수동 테스트 실행

```powershell
# 모닝 브리핑 단독 테스트
python runner.py KOSTAT_MorningBriefing

# EOD 게이트 테스트 (Telegram에서 Y/N 응답 필요)
python runner.py KOSTAT_EOD_Retrospective
```

---

## Step 6 — 절전 설정 (출장 필수)

출장 중 PC가 절전 모드가 되면 Task Scheduler가 실행되지 않습니다.

```powershell
# 절전 해제 (AC 전원 연결 시)
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
```

또는: **제어판 → 전원 옵션 → 고성능 → 절전 안 함** 설정

---

## 등록 확인 (GUI)

1. `Win + R` → `taskschd.msc` 입력
2. 좌측 트리: **작업 스케줄러 라이브러리 → KOSTAT**
3. 4개 태스크 목록 확인
4. 각 태스크 우클릭 → **실행** → 테스트

---

## 로그 확인

```powershell
# 오늘 로그 실시간 확인
Get-Content "C:\Users\USER\Desktop\77. CLOUDE 정리용\logs\$(Get-Date -Format 'yyyy-MM-dd').log" -Wait
```

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| `claude CLI not found` | npm PATH 미등록 | `npm root -g` 확인 후 PATH 추가 |
| Telegram 미수신 | 토큰 오류 | `.env`의 `TELEGRAM_BOT_TOKEN` 재확인 |
| 태스크가 실행 안 됨 | PC 절전 | Step 6 절전 설정 확인 |
| 게이트 응답 안 됨 | Chat ID 불일치 | `.env`의 `TELEGRAM_CHAT_ID` 확인 |
| `returncode=-1` | Claude 타임아웃 | `task_definitions.json`의 `timeout_minutes` 증가 |

---

## 다음 실행 명령어

### 전체 재등록 (설정 변경 후)
```powershell
cd "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation"
powershell -ExecutionPolicy Bypass -File .\scheduler\setup_tasks.ps1
```

### 특정 태스크 즉시 실행
```powershell
python "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\runner.py" KOSTAT_MorningBriefing
python "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\runner.py" KOSTAT_OOR_WeeklyCheck
python "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\runner.py" KOSTAT_CommissionInvoice
python "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\runner.py" KOSTAT_EOD_Retrospective
```

### Task Scheduler에서 수동 즉시 실행
```powershell
Start-ScheduledTask -TaskName "\KOSTAT\KOSTAT_MorningBriefing"
Start-ScheduledTask -TaskName "\KOSTAT\KOSTAT_EOD_Retrospective"
```

### 태스크 일시 중지 / 재개
```powershell
# 출장 전 일시 중지 (선택)
Disable-ScheduledTask -TaskName "\KOSTAT\KOSTAT_EOD_Retrospective"

# 복귀 후 재개
Enable-ScheduledTask -TaskName "\KOSTAT\KOSTAT_EOD_Retrospective"
```

### 전체 삭제 후 재등록
```powershell
# 삭제
Get-ScheduledTask -TaskPath "\KOSTAT\" | Unregister-ScheduledTask -Confirm:$false

# 재등록
powershell -ExecutionPolicy Bypass -File .\scheduler\setup_tasks.ps1
```

### Telegram 연결 테스트
```powershell
python "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\notifier\telegram_notify.py" "테스트"
```

### 로그 확인
```powershell
Get-Content "C:\Users\USER\Desktop\77. CLOUDE 정리용\logs\$(Get-Date -Format 'yyyy-MM-dd').log" -Tail 50
```
