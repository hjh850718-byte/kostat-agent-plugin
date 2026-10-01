---
name: kostat-morning-briefing
description: "/kostat 명령어 실행 시 아침 브리핑 출력. PM Soul Loop 기반 오늘 우선순위 정렬 + Drift 감지."
---

# kostat-morning-briefing

## 트리거
- 사용자가 `/kostat` 입력 시 **확인 없이 즉시 실행**
- 새 세션 시작 후 첫 메시지로 "출근", "아침", "오늘" 등 발화에도 실행 가능
- `"/classify"` 또는 "gmail 분류해줘" 입력 시 **Gmail 분류만 단독 실행**
- Task Scheduler: `claude --print "/classify"` 형태로 스케줄 등록 가능

## 작업 흐름

### Step 1: 컨텍스트 로드
1. **KOSTAT_MEMORY.md** 읽기 — `C:\Users\USER\Desktop\77. CLOUDE 정리용\KOSTAT_MEMORY.md`
2. **Open Loops 확인** — 이월된 미완료 항목 (없으면 건너뜀)
3. **오늘 날짜/요일 확인**
4. **Drift 감지** — 아래 기준으로 감지 실행:
   - KOSTAT_MEMORY.md의 마지막 업데이트가 3일 이상 전이면서 PO/OOR 작업 기록 없음 → Drift
   - 직전 EOD KPT 파일(`KPT_YYYY-MM-DD.md`)에서 Keep 항목이 AI/자동화만 있음 → Drift

### Step 1.5: Gmail 분류 (선택)

**실행 조건:** `/kostat` 브리핑(Step 4로 포함) 또는 `/classify` 단독 실행 시에만 동작.
CLAUDE.md 라우팅맵에 의한 일반 PO/OOR 처리 요청 시에는 건너뜀.

#### MCP 설정 확인
`%APPDATA%\Claude\claude_desktop_config.json`에 Gmail MCP 서버 등록 필요.
등록 누락 시 해당 섹션을 "MCP 미연결"로 표시하고 건너뜀.

#### 1. 메일 수집
Gmail MCP로 받은편지함 **미라벨 메일 최근 20개** fetch.
이미 라벨이 붙어 있는 메일은 건너뜀.

#### 2. 분류 기준 적용

우선순위 순서대로 평가하며, **첫 번째 매칭 라벨만 적용**.
복수 조건 해당 시 우선순위 높은 것을 우선함.

| 우선순위 | 조건 | 적용 라벨 | 추가 액션 |
|----------|------|-----------|-----------|
| 1 🔴 긴급 | Subject·본문에 `PO` `Purchase Order` `발주서` | `KOSTAT/PO-오더` | — |
| 2 🔴 긴급 | Subject·본문에 `urgent` `ASAP` `긴급` `즉시` | `KOSTAT/긴급` | — |
| 3 🔴 긴급 | Subject·본문에 `claim` `complaint` `issue` `defect` | `KOSTAT/긴급` | — |
| 4 🔵 고객사 | From: `@skyworks.com` | `고객사/Skyworks` | — |
| 5 🔵 고객사 | From: `@micron.com` | `고객사/Micron` | — |
| 6 🔵 고객사 | From: `@qorvo.com` | `고객사/Qorvo` | — |
| 7 🔵 고객사 | From: `xview` `hk` 관련 도메인 | `고객사/Xview-HK` | — |
| 8 🔵 고객사 | From: `@infineon.com` | `고객사/IFX` | — |
| 9 🔵 고객사 | From: `@amkor.com` | `고객사/Amkor` | — |
| 10 🔵 고객사 | From: `@intel.com` | `고객사/Intel` | — |
| 11 🟡 업무 | Subject: `OOR` `Open Order` | `KOSTAT/OOR` | — |
| 12 🟡 업무 | Subject: `invoice` `commission` `커미션` | `KOSTAT/커미션` | — |
| 13 🟡 업무 | Subject: `quote` `pricing` `견적` | `KOSTAT/견적` | — |
| 14 🟡 업무 | Subject: `shipment` `출하` `tracking` | `KOSTAT/출하` | — |
| 15 🟡 업무 | Subject: `quality` `QC` `REACH` `RoHS` `품질` | `KOSTAT/품질-컴플라이언스` | — |
| 16 🏢 사내 | From: `@kostat.com` | `사내` | — |
| 17 🗑️ 광고 | Gmail Promotions 카테고리 / From: `noreply@` `no-reply@` `marketing@` / Subject: `할인` `특가` `newsletter` `unsubscribe` `수신거부` | `_광고-삭제예정` | 받은편지함 제거 |
| 18 📥 기타 | 위 조건 미해당 전부 | `_미분류-확인필요` | — |

#### 3. 결과 저장
분류 결과를 아래 경로에 자동 저장:
```
C:\Users\USER\Desktop\77. CLOUDE 정리용\브리핑로그\Gmail분류_YYYYMMDD.txt
```
폴더가 없으면 자동 생성.

#### 4. 광고 삭제 처리
- `_광고-삭제예정` 건수를 브리핑에 표시
- **대화형 모드에서만 사용자 확인 후** 삭제 실행
- 자동 실행(Task Scheduler) 모드에서는 삭제 없이 카운트만 기록

---

### Step 2: 브리핑 출력

아래 템플릿을 **빈칸 채워서** 출력:

```markdown
🌅 KOSTAT 해외영업부 — 2026.06.08 (월) 아침 브리핑

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 이월된 Open Loops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [미완료 항목 1]
2. [미완료 항목 2]
   ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 오늘 반드시 (긴급/마감 오늘)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [고객 응대, PO 처리, 긴급 OOR 등]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 오늘 중 (이번주 마감)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. [인보이스, 출장 준비, 보고서 등]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 여유 있으면 (다음주 이후)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. [신규 개발, 블로그, 자동화 등]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 Gmail 분류 결과  [N건 처리]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 🔴 긴급        : N건
- 🔵 고객사      : N건  (Skyworks N / Micron N / Qorvo N / 기타 N)
- 🟡 업무        : N건  (OOR N / 커미션 N / 견적 N / 출하 N / 품질 N)
- 🏢 사내        : N건
- 🗑️ 광고-삭제예정 : N건  → 삭제할까요? [Y/N]
- 📥 미분류      : N건
[MCP 미연결 시: "📬 Gmail 분류: MCP 미연결 (claude_desktop_config.json에 Gmail MCP 등록 필요)"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 PM Soul 상태
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[정상 / ⚠️ DRIFT 감지 시 경고 메시지]
```

### Step 3: Acceptance Criteria 제안

브리핑 마지막에 오늘 세션의 목표를 1~3개 제안:

```
🎯 오늘의 Acceptance Criteria (제안)
세션 종료 시 아래가 완료되면 성공:
1. [추정 우선순위 기반 1]
2. [추정 우선순위 기반 2]
3. [추정 우선순위 기반 3]

수정이 필요하면 알려주세요.
```

---

### Step 4: `/classify` 단독 실행

**"/classify"** 또는 **"gmail 분류해줘"** 입력 시 아래만 실행하고 종료:

1. **Step 1.5** (Gmail 분류) 전체 수행
2. 결과를 브리핑로그에 저장
3. 분류 결과 요약만 출력 (전체 브리핑 생략)
4. 광고 삭제는 확인 후 진행

출력 형식:
```
📬 Gmail 분류 완료 — YYYY-MM-DD (N건 처리)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 🔴 긴급        : N건 상세
- 🔵 고객사      : N건  (Skyworks N / Micron N / ...)
- 🟡 업무        : N건  (OOR N / 커미션 N / ...)
- 🏢 사내        : N건
- 🗑️ 광고-삭제예정 : N건  → 삭제할까요? [Y/N]
- 📥 미분류      : N건  → 확인 필요 목록

저장: C:\Users\USER\Desktop\77. CLOUDE 정리용\브리핑로그\Gmail분류_YYYYMMDD.txt
```

## 컨텍스트 소스

| 정보 | 출처 |
|------|------|
| Open Loops | KOSTAT_MEMORY.md 내 Open Loops 섹션 |
| 고객사 상태 | KOSTAT_MEMORY.md 내 고객사 현황 |
| 스킬 상태 | kostat-agent-plugin의 skills/ 디렉토리 스캔 |
| 직전 KPT | `*KPT*.md` 최신 파일 |
| Gmail 분류 | Gmail MCP (Step 1.5) |
| Gmail 분류 결과 저장 | `C:\Users\USER\Desktop\77. CLOUDE 정리용\브리핑로그\Gmail분류_YYYYMMDD.txt` |
| Drift 근거 | 마지막 PO/OOR 처리 기록, KPT Keep 내용 분석 |

## 주의사항
- 브리핑은 **항상 최신 KOSTAT_MEMORY.md 기준**으로 생성
- 추정 우선순위는 "제안"임을 명시, 사용자 수정 가능하게 할 것
- Drift 감지 시 경고는 **부드럽게** — 개발 작업 자체를 비난하는 느낌 금지
- Open Loops가 없으면 "📌 이월된 Open Loops 없음" 출력
