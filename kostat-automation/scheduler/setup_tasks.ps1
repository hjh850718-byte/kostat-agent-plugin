# ============================================================
# KOSTAT 자동화 — Windows Task Scheduler 등록 스크립트
# 작성자: 한준희 과장 / KOSTAT 해외영업부
# 실행: 관리자 권한 불필요 (현재 사용자 계정으로 등록)
# 실행법: PowerShell에서 .\setup_tasks.ps1
# ============================================================

$ErrorActionPreference = "Stop"

# ── 경로 설정 (환경에 맞게 수정하세요) ──────────────────────────────────────
$RunnerPath  = "C:\Users\USER\Desktop\77. CLOUDE 정리용\kostat-automation\runner.py"
$PythonExe   = "python"   # PATH에 python이 있으면 OK, 없으면 전체 경로 입력
$TaskFolder  = "\KOSTAT"  # 작업 스케줄러 폴더 이름

# ── 공통 실행 액션 생성 함수 ────────────────────────────────────────────────
function New-ClaudeAction($TaskName) {
    $Action = New-ScheduledTaskAction `
        -Execute  $PythonExe `
        -Argument "`"$RunnerPath`" $TaskName" `
        -WorkingDirectory (Split-Path $RunnerPath)
    return $Action
}

# ── 공통 설정 ────────────────────────────────────────────────────────────────
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit   (New-TimeSpan -Minutes 30) `
    -RestartCount         2 `
    -RestartInterval      (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable   `
    -RunOnlyIfNetworkAvailable

# ── 작업 폴더 생성 ───────────────────────────────────────────────────────────
$Scheduler = New-Object -ComObject Schedule.Service
$Scheduler.Connect()
$Root = $Scheduler.GetFolder("\")
try {
    $Root.GetFolder($TaskFolder) | Out-Null
    Write-Host "✅ 작업 폴더 '$TaskFolder' 이미 존재합니다." -ForegroundColor Yellow
} catch {
    $Root.CreateFolder($TaskFolder) | Out-Null
    Write-Host "✅ 작업 폴더 '$TaskFolder' 생성 완료." -ForegroundColor Green
}

# ════════════════════════════════════════════════════════════
# 태스크 1: 매일 08:10 — 모닝 브리핑
# ════════════════════════════════════════════════════════════
$Task1Name    = "KOSTAT_MorningBriefing"
$Task1Trigger = New-ScheduledTaskTrigger -Daily -At "08:10"
$Task1Action  = New-ClaudeAction $Task1Name

Register-ScheduledTask `
    -TaskName   "$TaskFolder\$Task1Name" `
    -Action     $Task1Action `
    -Trigger    $Task1Trigger `
    -Settings   $Settings `
    -Description "KOSTAT 매일 오전 8:10 모닝 브리핑 자동 실행" `
    -RunLevel   Limited `
    -Force | Out-Null

Write-Host "✅ [$Task1Name] 등록 완료 — 매일 08:10" -ForegroundColor Green

# ════════════════════════════════════════════════════════════
# 태스크 2: 매주 월요일 09:00 — OOR 체크 리마인드
# ════════════════════════════════════════════════════════════
$Task2Name    = "KOSTAT_OOR_WeeklyCheck"
$Task2Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "09:00"
$Task2Action  = New-ClaudeAction $Task2Name

Register-ScheduledTask `
    -TaskName   "$TaskFolder\$Task2Name" `
    -Action     $Task2Action `
    -Trigger    $Task2Trigger `
    -Settings   $Settings `
    -Description "KOSTAT 매주 월요일 9:00 OOR 수신 여부 확인" `
    -RunLevel   Limited `
    -Force | Out-Null

Write-Host "✅ [$Task2Name] 등록 완료 — 매주 월요일 09:00" -ForegroundColor Green

# ════════════════════════════════════════════════════════════
# 태스크 3: 매월 1일 09:00 — 커미션 인보이스 리마인드
# ════════════════════════════════════════════════════════════
$Task3Name    = "KOSTAT_CommissionInvoice"
# 매월 반복 트리거는 PowerShell 기본 cmdlet 미지원 → XML로 직접 등록
$Task3XML = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>KOSTAT 매월 1일 9:00 커미션 인보이스 생성 리마인드</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-07-01T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByMonth>
        <DaysOfMonth>
          <Day>1</Day>
        </DaysOfMonth>
        <Months>
          <January/>
          <February/>
          <March/>
          <April/>
          <May/>
          <June/>
          <July/>
          <August/>
          <September/>
          <October/>
          <November/>
          <December/>
        </Months>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>$PythonExe</Command>
      <Arguments>"$RunnerPath" $Task3Name</Arguments>
      <WorkingDirectory>$(Split-Path $RunnerPath)</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
  </Settings>
</Task>
"@

$TempXml = [System.IO.Path]::GetTempFileName() + ".xml"
[System.IO.File]::WriteAllText($TempXml, $Task3XML, [System.Text.Encoding]::Unicode)
schtasks /Create /XML $TempXml /TN "$TaskFolder\$Task3Name" /F 2>&1 | Out-Null
Remove-Item $TempXml -ErrorAction SilentlyContinue

Write-Host "✅ [$Task3Name] 등록 완료 — 매월 1일 09:00" -ForegroundColor Green

# ════════════════════════════════════════════════════════════
# 태스크 4: 매일 18:30 — EOD 회고 초안
# ════════════════════════════════════════════════════════════
$Task4Name    = "KOSTAT_EOD_Retrospective"
$Task4Trigger = New-ScheduledTaskTrigger -Daily -At "18:30"
$Task4Action  = New-ClaudeAction $Task4Name

Register-ScheduledTask `
    -TaskName   "$TaskFolder\$Task4Name" `
    -Action     $Task4Action `
    -Trigger    $Task4Trigger `
    -Settings   $Settings `
    -Description "KOSTAT 매일 오후 6:30 EOD 회고 초안 생성 (Notion 저장 전 승인 필요)" `
    -RunLevel   Limited `
    -Force | Out-Null

Write-Host "✅ [$Task4Name] 등록 완료 — 매일 18:30" -ForegroundColor Green

# ════════════════════════════════════════════════════════════
# 등록 결과 요약 출력
# ════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  KOSTAT 자동화 태스크 등록 완료!" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "등록된 태스크 목록:" -ForegroundColor White

Get-ScheduledTask -TaskPath "$TaskFolder\" | ForEach-Object {
    $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath
    Write-Host "  ✔ $($_.TaskName)" -ForegroundColor Green
    Write-Host "    마지막 실행: $($info.LastRunTime)  결과: $($info.LastTaskResult)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📁 로그 위치: C:\Users\USER\Desktop\77. CLOUDE 정리용\logs\" -ForegroundColor Yellow
Write-Host "📋 작업 스케줄러에서 확인: taskschd.msc → 작업 스케줄러 라이브러리 → KOSTAT" -ForegroundColor Yellow
Write-Host ""

# ── 즉시 테스트 실행 여부 확인 ──────────────────────────────────────────────
$runNow = Read-Host "지금 모닝 브리핑 태스크를 테스트 실행하시겠습니까? (Y/N)"
if ($runNow -eq "Y" -or $runNow -eq "y") {
    Write-Host "▶ KOSTAT_MorningBriefing 테스트 실행 중..." -ForegroundColor Cyan
    Start-ScheduledTask -TaskName "$TaskFolder\KOSTAT_MorningBriefing"
    Start-Sleep -Seconds 3
    $status = (Get-ScheduledTaskInfo -TaskName "KOSTAT_MorningBriefing" -TaskPath "$TaskFolder\").LastTaskResult
    Write-Host "   결과 코드: $status (0 = 성공)" -ForegroundColor $(if ($status -eq 0) { "Green" } else { "Red" })
}
