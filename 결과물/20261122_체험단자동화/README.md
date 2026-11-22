# 체험단 자동화 설치 패키지 (review-trial-hunter)

노션 「🧪 체험단 자동화 스킬 & 예약 가이드」의 셋업 프롬프트를 **PowerShell 스크립트로 고정**한 버전.
클로드코드에게 셋업을 맡기는 대신 스크립트가 같은 일을 매번 똑같이 하고, 결과를 표로 보고한다.

## 실행 순서 (PC, PowerShell — 관리자 권한 불필요)

```powershell
# 0) 이 폴더를 PC에 내려받은 위치로 이동 (예: 바탕화면)
cd "$env:USERPROFILE\Desktop\20261122_체험단자동화"

# 1) 설치 + 예약 등록 + 플래그/경로/MCP 검증 (네이버 1단계만)
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -EnableMusinsa -EnableBlog
#    무신사 계정 있으면 -EnableMusinsa, 블로그 체험단 계정 있으면 -EnableBlog 추가

# 2) 자동화 전용 Edge 프로필에 로그인 (비밀번호는 직접 입력)
powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\review-trial\login.ps1

# 3) 계정·사이즈 메모: 아래 파일의 1.1 / 1.2 칸 채우기
notepad C:\workspace\review-trial\.claude\skills\review-trial-hunter\SKILL.md

# 4) 네이버 스캔 1회 수동 실행 → 결과 확인
schtasks /Run /TN ReviewTrialHunter_Daily
Get-Content C:\workspace\review-trial\logs\naver.log -Tail 30 -Encoding UTF8
Get-ChildItem C:\workspace\review-trial\logs\scan
```

## 노션 체크리스트 매핑

| 노션 체크리스트 | 처리 |
|---|---|
| 1번 프롬프트로 스킬·예약 등록 | `install.ps1` |
| `claude --help` 플래그 확인 후 경로 확정 | `install.ps1`이 자동 확인 → `config.json`에 경로 저장 |
| 1단계 네이버 스캔 1회 수동 실행 | 위 4) |
| 무신사·레뷰 계정 확인 | `-EnableMusinsa` / `-EnableBlog` 스위치 + SKILL.md 1.1 |
| 평소 사이즈 메모 | SKILL.md 1.2 |

## 노션 가이드 대비 바꾼 점

| 항목 | 노션 원안 | 이 패키지 | 이유 |
|---|---|---|---|
| Playwright MCP | 설치 단계 없음 | `.mcp.json`(프로젝트 범위)에 자동 등록 | 없으면 스캔이 브라우저를 못 염 |
| 로그인 유지 | "프로필 세션 사용"만 명시 | Edge + 전용 프로필 `browser-profile` + `login.ps1` | 매번 새 프로필이면 네이버가 로그인 화면을 띄움 |
| 실행 파일 | `.bat` | `run-scan.ps1 -Stage …` | bat에 한글 프롬프트 넣으면 인코딩 깨짐 위험 |
| 예약 허용 도구 | `Read,Write,Edit,Bash,playwright` | **Bash 제외** | 무인 실행에서 셸 권한은 불필요한 위험 |
| 로그온 조건 | 수동 확인 지시 | `-LogonType Interactive` 로 강제 | "로그온했을 때만 실행" |
| 20분 타임아웃 | "감시하세요" | 작업 설정 `ExecutionTimeLimit 20분` | 자동 종료 |
| 노션 기록 | 필수 | 연결돼 있으면 기록, 없으면 `logs\scan`에만 | PC 클로드코드에 노션 MCP가 없으면 매번 실패 |
| 블로그 체험단 주소 | 매번 검색 | `state.json`의 `sites`에 사람이 확인한 주소만 | 무인 실행 중 검색 결과로 엉뚱한 사이트 접속 방지 |

## 예약 작업

| 작업 이름 | 주기 | 내용 | 기본 등록 |
|---|---|---|---|
| ReviewTrialHunter_Daily | 매일 09:00 | 네이버 무료체험 + 작성 가능 리뷰 | O |
| ReviewTrialHunter_MWF | 월·수·금 09:10 | 무신사 | `-EnableMusinsa` |
| ReviewTrialHunter_TT | 화·목 09:20 | 배송형 블로그 체험단 | `-EnableBlog` |
| ReviewTrialHunter_Monthly | 매월 1일 09:30 | 한달사용리뷰 포인트 | O |
| ReviewTrialHunter_Weekly | 일 21:00 | 주간 리포트 (브라우저 안 씀) | O |

삭제: `Get-ScheduledTask ReviewTrialHunter_* | Unregister-ScheduledTask -Confirm:$false`

## 검증 상태 (팩트 / 추측 분리)

- **확인됨**: 파일 구성, 스킬 본문(노션 원안 + 계정/사이즈/노션 폴백 보완), 스크립트 로직 수동 리뷰.
- **미검증 (PC에서 처음 돌릴 때 확인 필요)**:
  - PowerShell 문법 실행 검증 — 작성 환경에 PowerShell이 없어 실행 못 해봄. 오류 나면 메시지 그대로 붙여줄 것. (확신도: 중)
  - `claude mcp list`에서 playwright가 바로 Connected로 뜨는지 — 첫 실행은 npx 다운로드로 느릴 수 있음. (확신도: 중)
  - 무신사 로그인 주소 `https://www.musinsa.com/auth/login` — 추정값. 틀리면 무신사 메인에서 로그인 버튼으로. (확신도: 낮)
  - 네이버·무신사 페이지 구조 — 개편되면 스킬이 "구조 변경 의심"으로 멈춤. (확신도: 높음 — 언젠가는 생김)
- **운영 조건**: 예약 시각에 PC가 켜져 있고 로그온 + 화면 잠금 해제 상태여야 함. 꺼져 있으면 `StartWhenAvailable`로 다음 로그온 때 실행.
