# kostat-agent-plugin — Claude AI 작업 규칙 (v1.3.0)

## 정체성

이 Plugin은 **KOSTAT 해외영업 업무 자동화**를 위한 Claude Code Plugin입니다.
반도체 해외영업(PO 관리, OOR 분석, 커미션 인보이스, EOD 회고 등)을 자동화하는
11개 스킬과 9개 Hook 스크립트를 제공합니다.

- **저자**: 한준희 (hjh850718@gmail.com)
- **버전**: package.json 기준 1.3.0 (plugin.json 기준 1.0.0)
- **Repository**: https://github.com/hjh850718-byte/kostat-agent-plugin
- **라이선스**: MIT

---

## 디렉토리 구조

```
kostat-agent-plugin/
├── .claude-plugin/
│   ├── plugin.json          ← Plugin 메타데이터 (name, version, author, keywords)
│   └── marketplace.json     ← GitHub Marketplace 등록용 메타데이터
├── skills/                  ← KOSTAT 스킬 11개 (각각 SKILL.md 포함)
│   ├── kostat-orchestrator/         ← Level 7: 트리거 감지 → 팀 소집 → 결과 취합
│   ├── kostat-po-update/            ← Level 6: Fan-out 3way (Excel+번역+Calendar)
│   ├── kostat-hk-po-update/         ← Level 6: Fan-out 2way (HK/Amkor PO)
│   ├── kostat-oor-weekly/           ← Level 6: Fan-out 2way (Bring Forward 분석)
│   ├── kostat-commission-invoice/   ← Level 6: Gen/Eval Loop (인보이스 생성+검증)
│   ├── kostat-eod-retrospective/    ← Level 6: Fan-out 2way (KPT 회고)
│   ├── kostat-morning-briefing/     ← Level 1: 일일 브리핑
│   ├── kostat-memory-loader/        ← Level 1: 세션 시작 시 컨텍스트 로드
│   ├── kostat-memory-ticket/        ← Level 1: 학습/결정 사항 기록
│   ├── kostat-skill-check/          ← Level 1: 스킬 라이프사이클 관리
│   └── kostat-tal/                  ← Level 1: 판단 기준 참조 (MFG SITE 매핑 등)
├── hooks/                   ← Hook Python 스크립트 9개 + 설정 참조
│   ├── hooks.json           ← Hook 설정 참조 (실제 등록은 settings.json)
│   ├── kostat-gateguard.py          ← PreToolUse: Excel 수정 전 Human Gate
│   ├── kostat-autobackup.py         ← PreToolUse: 수정 전 자동 백업
│   ├── kostat-observe.py            ← PostToolUse: 변경 관찰 로깅
│   ├── kostat-tracelogger.py        ← PostToolUse: Trace 로그 기록
│   ├── kostat-eod-sessionstart.py   ← SessionStart: 6시 이후 재접속 시 회고 제안
│   ├── kostat-eod-stop.py           ← Stop: 세션 로그 + pending_retro flag
│   ├── kostat-eod-detector.py       ← UserPromptSubmit: EOD 트리거 감지
│   ├── kostat-compact.py            ← PreCompact: 컨텍스트 압축 전 작업
│   └── kostat-workspace-router.py   ← UserPromptSubmit: 워크스페이스 라우팅
├── references/              ← 토큰 최적화용 상세 매핑 참조 파일 4개
│   ├── field-mapping.md     ← PO PDF → Excel 필드 매핑
│   ├── rate-tables.md       ← 커미션 요율 계산 규칙
│   ├── column-map.md        ← OOR 컬럼 매핑 및 검증
│   └── xview-mapping.md     ← HK/Amkor PO 필드 매핑
├── scripts/
│   └── kostat-team.sh       ← tmux 멀티탭 팀 실행 (4개 창: orchestrator, po-agent, oor-agent, validator)
├── docs/                    ← 설계 문서 9개
│   ├── 01. Dynamic Workflow 실전 프롬프트.md
│   ├── 03. kostat-po-update Eval 테스트 케이스.md
│   ├── 04. kostat-eod-retrospective Eval 테스트 케이스.md
│   ├── 05. KOSTAT-AGENT Trace Schema.md
│   ├── 06. KOSTAT Managed Agent Console 설계 v1.0.md
│   ├── 07. KOSTAT Managed Agent 아키텍처 리뷰.md
│   ├── 08. KOSTAT Plugin 패키징 설계.md
│   ├── 09. Make.com + Claude 자동화 구현 가이드.md
│   └── 10. Make.com + Claude KOSTAT 업무 적용 방안.md
├── CLAUDE.md                ← 이 파일 (AI 어시스턴트 작업 규칙)
├── CONNECTORS.md            ← 외부 서비스 연결 현황
├── README.md                ← 설치/사용 가이드
├── package.json             ← 버전 및 의존성 (v1.3.0)
├── LICENSE                  ← MIT
└── .gitignore               ← 표준 무시 패턴
```

---

## 스킬 아키텍처

### 레벨 체계

| 레벨 | 설명 | 해당 스킬 |
|------|------|----------|
| Level 7 | Orchestrator — 전체 시스템 두뇌 | kostat-orchestrator |
| Level 6 | 복합 실행 — Fan-out 병렬 or Gen/Eval Loop | po-update, hk-po-update, oor-weekly, commission-invoice, eod-retrospective |
| Level 1 | 단일 실행 — 참조/관리/브리핑 | morning-briefing, memory-loader, memory-ticket, skill-check, tal |

### 실행 모드

| 모드 | 설명 | 해당 스킬 |
|------|------|----------|
| Fan-out 3way | 3개 Task 병렬 실행 후 동기화 | kostat-po-update |
| Fan-out 2way | 2개 Task 병렬 실행 후 동기화 | kostat-hk-po-update, kostat-oor-weekly, kostat-eod-retrospective |
| Gen/Eval Loop | Generator → Evaluator 검증 루프 (최대 3회) | kostat-commission-invoice |
| Standalone | 단일 실행 | 나머지 모든 스킬 |

### 트리거 우선순위 (Orchestrator 기준)

| 우선순위 | 트리거 키워드 | 소집 팀 | 실행 모드 |
|---------|--------------|--------|----------|
| 1 | PO PDF 수신 | PO-US + Doc-Translate + Calendar | Fan-out 3way |
| 1 | HK PO / Amkor PO 수신 | HK-PO + Doc-Translate | Fan-out 2way |
| 2 | OOR / Open Order / Bring Forward | OOR + Validator | Fan-out 2way |
| 3 | commission / invoice | Commission-Gen + Commission-Eval | Gen/Eval Loop |
| 4 | 업무끝 / EOD / 회고 / KPT | EOD-Retro + Memory-Ticket | 순차 |
| 5 | /kostat / 출근 | Morning-Briefing | 단일 |
| 6 | /skill-check | Skill-Check | 단일 |
| 7 | 일반 메일 | Summary | 단일 |

### Orchestrator Task ID 체계

형식: `{접두사}-TASK{N}-{YYYYMMDD}-{순번}`

| 트리거 | 접두사 |
|--------|--------|
| PO | PO |
| HK PO | HK |
| OOR | OOR |
| Commission | COM |
| EOD | EOD |
| 일반 | GEN |

---

## Hook 시스템

### Hook 등록 방법

`hooks/hooks.json`은 **참조 파일**이며, 실제 Hook 등록은 `settings.json`에서 이루어집니다.

```json
{
  "PreToolUse": {
    "Write|Edit": ["kostat-gateguard.py (5s)", "kostat-autobackup.py (5s)"]
  },
  "PostToolUse": {
    "Write|Edit": ["kostat-observe.py (10s)", "kostat-tracelogger.py (5s)"]
  },
  "SessionStart": ["kostat-eod-sessionstart.py (5s)"],
  "Stop": ["kostat-eod-stop.py (5s)"]
}
```

`kostat-eod-detector.py`와 `kostat-workspace-router.py`는 `UserPromptSubmit` Hook으로 별도 등록합니다.

### 각 Hook 역할

| Hook | 라이프사이클 | 역할 |
|------|------------|------|
| kostat-gateguard.py | PreToolUse (Write/Edit) | Excel 수정 전 Human Gate 승인 확인 (세션 기반 상태 추적) |
| kostat-autobackup.py | PreToolUse (Write/Edit) | 파일 수정 전 자동 백업 |
| kostat-observe.py | PostToolUse (Write/Edit) | 변경 사항 관찰 로깅 |
| kostat-tracelogger.py | PostToolUse (Write/Edit) | Trace 로그 기록 |
| kostat-eod-sessionstart.py | SessionStart | 오후 6시 이후 재접속 감지 → 회고 제안 |
| kostat-eod-stop.py | Stop | 세션 종료 로그 (`session-log.txt`) + `pending_retro` flag 설정 |
| kostat-eod-detector.py | UserPromptSubmit | EOD 트리거 감지 → `eod_detected.flag` 파일 생성 |
| kostat-workspace-router.py | UserPromptSubmit | 키워드 매칭 → 워크스페이스 라우팅 + 관련 스킬 추천 |
| kostat-compact.py | PreCompact | 컨텍스트 압축 전 작업 |

---

## AUTOMATION 연동 (Level 7 Python 시스템)

`AUTOMATION/` 디렉토리는 이 플러그인 레포지토리 외부에 위치합니다.

```
AUTOMATION/
├── kostat_poller.py          ← POP3 폴링 + ThreadPoolExecutor 병렬 처리
├── trigger_classifier.py     ← 메일/파일/입력 → 트리거 분류 (ClassificationResult)
├── orchestrator_bridge.py    ← ClassificationResult → Skill/direct 실행
├── pop3_watcher.py           ← 기존 (호환성 유지)
├── router.py                 ← 기존 (호환성 유지)
├── handlers.py               ← 기존 (호환성 유지)
├── telegram_client.py        ← Telegram 발송
├── claude_client.py          ← Claude API 호출
├── processed_ids.json        ← 중복 방지 캐시
└── task_logs/                ← Task 실행 로그
```

### Orchestrator 엔진 전환

`.env`에서 설정:
- `ORCHESTRATOR_ENGINE=direct` — handlers.py 직접 호출 (기존 방식)
- `ORCHESTRATOR_ENGINE=claude` — Claude Code subprocess 실행 (fanout 모드)

### 실행 제한

| 항목 | 값 |
|------|-----|
| Task 타임아웃 | 10분 |
| 전체 팀 타임아웃 | 15분 |
| Task 재시도 | 1회 |
| 최대 동시 실행 Task | 4개 |

---

## References 파일 (토큰 최적화)

`references/` 디렉토리의 파일들은 SKILL.md 내 상세 매핑을 분리하여 토큰을 절약합니다. 스킬에서 필요할 때만 참조합니다.

| 파일 | 용도 |
|------|------|
| `field-mapping.md` | PO PDF → Excel 필드 매핑, MFG SITE 규칙, Remarks 포맷, Telegram 포맷 |
| `rate-tables.md` | 커미션 요율 계산 (`commission / sales × 100`, ±0.01% 허용), 시트 매핑, 인보이스 포맷 |
| `column-map.md` | OOR 컬럼 매핑 (F=PO#, AS=PO#ref, H=Ship Date, AU=Req Date), Bring Forward 카테고리 |
| `xview-mapping.md` | HK/Amkor PO 필드 매핑, Invoice# vs PO# 구분 규칙 |

### 주요 규칙 요약

- **MFG SITE**: 기존 PO → 이전 값 유지; 신규 PO → 기본값 `'KR'`
- **Bring Forward 카테고리**: 🔴 긴급 (2주+ 불일치), 🟡 일반 (2주~2개월), ⚪ 보류 (여유)
- **OOR Severity**: Critical (PO# 불일치), Warning (7일+ 지연), Info (≤7일 지연)
- **커미션 수식**: `rate = commission / sales × 100` (±0.01% 허용 오차)

---

## 로컬 파일 경로 (Windows 운영 환경)

| 경로 | 용도 |
|------|------|
| `D:\jun\한준희\` | PO PDF, OOR Excel, 커미션 데이터 원본 |
| `D:\jun\한준희\미국오더\*.pdf` | 미국 PO PDF |
| `D:\jun\한준희\invoice\*.pdf` | HK/Amkor PO PDF |
| `C:\Users\USER\Desktop\77. CLOUDE 정리용\` | 작업 파일, 인보이스, KPT, 브리핑 로그 |
| `Commission\Invoice_{customer}_{YYYYMMDD}.md` | 인보이스 저장 경로 |

---

## 외부 연동 현황

### MCP 서버

| 서비스 | 용도 | 필수 여부 |
|--------|------|-----------|
| Gmail (`mcp__dafeb557__*`) | 이메일 분류, PO/OOR 메일 감지 | 권장 |
| Google Calendar (`mcp__8e247a8e__*`) | PO 납기일 등록 | 선택 |
| Notion (`mcp__f69fe460__*`) | KPT 저장, Memory Ticket 보관 | 선택 |
| KakaoTalk (`mcp__993e42ce__*`) | 알림 수신 | 선택 |
| Google Drive (`mcp__9fb443f9__*`) | 파일 관리 | 선택 |

> MCP 서버 연결은 `claude_desktop_config.json`에서 별도 설정합니다. 플러그인 설치만으로 자동 연결되지 않습니다.

### 외부 API

| 서비스 | 용도 | 인증 |
|--------|------|------|
| Telegram Bot | 작업 완료/에러 알림 | Bot Token (`.env`) |
| 관세청 수출입무역통계 | HS코드, 환율 조회 | 공개 API |

---

## 변경 시 규칙

### 스킬 수정

1. `skills/{skill-name}/SKILL.md` 직접 편집
2. **Claude Code 설정에서 플러그인 재설치 필요**: 설정 → Capabilities → 플러그인 재설치
   - 재설치 전까지 Claude는 AppData 캐시(구버전)를 사용함

### Hook 수정

- `hooks/` 디렉토리의 Python 스크립트 수정 후 `Documents/Claude/claude-tray/`와 **동기화 유지**
- Hook 추가/제거 시 `settings.json`도 함께 수정
- `hooks.json`은 참조용이므로 실제 동작에 영향 없음

### 버전 관리

- `package.json`의 `version`은 **semantic versioning** 준수
- 주요 변경(스킬 추가/삭제, 아키텍처 변경) 시 `docs/08. KOSTAT Plugin 패키징 설계.md` 업데이트

### 소스 vs 설치본

| 위치 | 역할 | 편집 가능 |
|------|------|----------|
| `kostat-agent-plugin/skills/` | 소스 원본 | ✅ 직접 편집 |
| `AppData\Roaming\Claude\...\skills\` | 설치 캐시 | ❌ 플러그인 재설치로만 갱신 |

---

## Python 호출 규칙

- hooks.json 및 settings.json에서 항상 `python "..."` 형식 사용 (Windows 호환)
- `python3`는 Windows에서 없을 수 있으므로 **사용 금지**
- 스크립트 내 shebang(`#!/usr/bin/env python3`)은 유지 가능 (Windows에서 무시됨)

---

## tmux 팀 실행 (scripts/kostat-team.sh)

4개 창을 병렬로 실행:

| 창 | 에이전트 | 역할 |
|----|---------|------|
| orchestrator | 트리거 감지 & 팀 소집 | 전체 조율 |
| po-agent | PO PDF → Excel 처리 | PO 업데이트 |
| oor-agent | OOR Bring Forward 분석 | OOR 분석 |
| validator | PO# 불일치 & 데이터 무결성 | 검증 |

실행: `claude --dangerously-skip-permissions` 사용

---

## 에러 처리 원칙

| 에러 유형 | 처리 |
|----------|------|
| 단일 Task 실패 | 재시도 1회 → 실패 시 해당 Task 스킵 + Telegram 알림 |
| 2개 이상 Task 실패 | 전체 중단 → 긴급 알림 |
| Validator 에러 감지 | 사용자 확인 요청 (자동 진행 금지) |
| API 키 없음 | 해당 Task 스킵 + 환경설정 안내 |
| 타임아웃 | 강제 종료 → 부분 결과로 처리 |

---

## AI 어시스턴트 작업 지침

### 스킬 수정 시

- 해당 스킬의 `SKILL.md`만 수정
- 트리거 키워드 변경 시 `kostat-orchestrator/SKILL.md`의 트리거 테이블도 함께 확인
- 참조 파일(`references/*.md`)은 SKILL.md와 별도로 관리 — 중복 정의 금지

### Hook 스크립트 수정 시

- `hooks/` 내 Python 파일 수정
- Windows 경로 구분자는 `\\` 또는 `os.path.join()` 사용
- `python "..."` 호출 형식 유지

### 새 스킬 추가 시

1. `skills/{new-skill-name}/SKILL.md` 생성
2. `kostat-orchestrator/SKILL.md` 트리거 테이블 업데이트
3. `package.json` 스킬 목록 및 버전 업데이트
4. `README.md` 스킬 목록 업데이트
5. `plugin.json` 필요 시 업데이트

### 커밋 규칙

- `feat:` — 새 스킬 또는 기능 추가
- `fix:` — 버그 수정
- `chore:` — 설정, 메타데이터, 문서 정리
- `docs:` — 문서만 변경

### 절대 하지 말 것

- Orchestrator는 직접 파일을 수정하지 않음 (각 에이전트에 위임)
- `.env` 파일을 커밋하지 않음 (`.gitignore`로 제외됨)
- `python3` 명령어를 Hook에서 사용하지 않음 (Windows 비호환)
- Human Gate(kostat-gateguard.py)를 우회하지 않음
