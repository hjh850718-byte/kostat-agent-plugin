# Aside 실행용 프롬프트 (복붙)

```txt
[역할]
너는 내 Windows 11 PC에서 작업하는 에이전트다. 아래 순서대로 끝까지 진행하고, 마지막에 결과를 표로만 보고해라.

[목표]
체험단 스캔 자동화(review-trial-hunter)를 PC에 설치하고 검증한다.
설치 패키지는 GitHub 저장소 hjh850718-byte/kostat-agent-plugin 의 브랜치 claude/notion-page-link-upj9pt,
폴더 결과물/20261122_체험단자동화/ 에 있다.

[절대 규칙]
1. 공개 댓글 등록, 체험단 신청 제출, 결제, 비밀번호 입력은 하지 않는다.
2. 로그인 화면, 캡차, 본인인증이 나오면 멈추고 나에게 알린다. 우회하지 않는다.
3. 비밀번호, 쿠키, 토큰을 파일이나 로그에 남기지 않는다.
4. 관리자 권한을 요구하는 명령은 실행하지 말고 나에게 알린다.
5. 오류가 나면 추측해서 고치지 말고, 오류 메시지 원문과 원인 추정을 분리해서 보고한다. 같은 오류가 2번 나면 멈춘다.

[1단계: 패키지 받기]
PowerShell에서:
  cd $env:USERPROFILE\Desktop
  git clone -b claude/notion-page-link-upj9pt --depth 1 https://github.com/hjh850718-byte/kostat-agent-plugin.git review-trial-src
- git이 없거나 인증 실패 시: 나에게 알리고, 내가 GitHub에서 ZIP으로 받아 바탕화면에 풀어 줄 때까지 기다린다.
- 받은 뒤 review-trial-src\결과물\20261122_체험단자동화 에 install.ps1, run-scan.ps1, login.ps1, SKILL.md, prompts 폴더가 있는지 확인한다.

[2단계: 사전 확인]
  where.exe claude
  where.exe npx
  claude --version
- claude 가 없으면 멈추고 알린다.
- npx 가 없으면 Node.js LTS 설치가 필요하다고 알리고 멈춘다(설치는 내가 한다).

[3단계: 설치]
  cd $env:USERPROFILE\Desktop\review-trial-src\결과물\20261122_체험단자동화
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -EnableMusinsa
- 무신사 계정은 있음(확정). 블로그 체험단(레뷰/강남맛집/서울오빠)은 내가 계정이 있다고 확정해 줄 때만 -EnableBlog 를 붙인다.
- 출력된 설치 결과 표를 그대로 보관한다.

[4단계: 로그인 (사람이 할 일)]
  powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\review-trial\login.ps1
- Edge 창이 열리면 "네이버·무신사 로그인(네이버는 로그인 상태 유지 체크) 후 Edge 창을 모두 닫고 알려달라"고 나에게 요청하고 기다린다.
- 직접 아이디·비밀번호를 입력하지 않는다.

[5단계: 검증]
  Get-ScheduledTask ReviewTrialHunter_* | Get-ScheduledTaskInfo | Select TaskName, NextRunTime, LastTaskResult
  Get-Content C:\workspace\review-trial\.mcp.json
  cd C:\workspace\review-trial; claude mcp list
- 각 작업이 "로그온했을 때만 실행"(LogonType Interactive)인지 확인:
  Get-ScheduledTask ReviewTrialHunter_* | Select TaskName, @{n='Logon';e={$_.Principal.LogonType}}

[6단계: 네이버 스캔 1회]
  schtasks /Run /TN ReviewTrialHunter_Daily
- 최대 20분 기다리며 1분 간격으로 확인:
  Get-Content C:\workspace\review-trial\logs\naver.log -Tail 20 -Encoding UTF8
- "종료 (exit 0)" 가 보이면 C:\workspace\review-trial\logs\scan 의 최신 결과 파일 내용을 보고에 붙인다.
- 로그에 로그인 화면/캡차가 언급되면 4단계로 돌아가라고 나에게 알린다.

[보고 형식]
| 단계 | 결과(성공/실패/대기) | 근거(명령 출력 한 줄) | 다음 조치 |
- 그 아래에 install.ps1 결과 표 원문
- 그 아래에 네이버 스캔 결과 파일 원문(있으면)
- 확인된 사실과 추정은 분리해서 적는다.
```
