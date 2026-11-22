# install.ps1 — review-trial-hunter 원샷 설치 (Windows 11, 관리자 권한 불필요)
# 사용 (이 폴더에서):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1                  # 1단계(네이버)만
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -EnableMusinsa   # + 무신사
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -EnableMusinsa -EnableBlog -RunTest
param(
    [switch]$EnableMusinsa,   # 무신사 계정 있을 때
    [switch]$EnableBlog,      # 레뷰/강남맛집/서울오빠 중 하나라도 계정 있을 때
    [switch]$RunTest,         # 설치 후 네이버 스캔 1회 바로 실행
    [switch]$UpdateSkill      # 이미 설치된 SKILL.md 를 새 버전으로 덮어쓰기(기존은 .prev 로 보관)
)

$ErrorActionPreference = 'Stop'
$Src  = $PSScriptRoot
$Root = 'C:\workspace\review-trial'
$utf8 = [Text.UTF8Encoding]::new($false)
$report = [System.Collections.Generic.List[object]]::new()
function Add-Result($item, $ok, $note) {
    $report.Add([pscustomobject]@{ 항목 = $item; 결과 = $(if ($ok) { '성공' } else { '실패' }); 비고 = $note })
}
function Write-Json($path, $obj) {
    [IO.File]::WriteAllText($path, ($obj | ConvertTo-Json -Depth 6), $utf8)
}

# ---------- 1. 폴더 + 파일 복사 ----------
$dirs = @($Root, "$Root\logs", "$Root\logs\scan", "$Root\logs\screens", "$Root\prompts",
          "$Root\browser-profile", "$Root\.claude\skills\review-trial-hunter")
$dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }

$skillDst = "$Root\.claude\skills\review-trial-hunter\SKILL.md"
if (-not (Test-Path $skillDst)) {
    Copy-Item "$Src\SKILL.md" $skillDst
} elseif ($UpdateSkill) {
    Copy-Item $skillDst "$skillDst.prev" -Force   # 계정/사이즈 메모 보관
    Copy-Item "$Src\SKILL.md" $skillDst -Force
}   # 그 외: 기존 SKILL.md(계정·사이즈 메모 포함) 유지
Copy-Item "$Src\run-scan.ps1"   "$Root\run-scan.ps1" -Force
Copy-Item "$Src\login.ps1"      "$Root\login.ps1" -Force
Copy-Item "$Src\prompts\*.txt"  "$Root\prompts\" -Force
Add-Result '스킬·스크립트 복사' $true $skillDst

if (-not (Test-Path "$Root\state.json")) {
    Write-Json "$Root\state.json" ([ordered]@{
        reported     = @()
        applications = @()
        sites        = [ordered]@{ revu = 'https://www.revu.net'; gangnam = 'https://xn--939au0g4vj8sq.net'; seoulobba = 'https://www.seoulouba.co.kr' }
    })
}
Add-Result 'state.json' $true '기존 파일 있으면 유지'

# ---------- 2. claude 경로 + 플래그 확인 ----------
$claude = $null
try { $claude = (Get-Command claude -ErrorAction Stop).Source } catch {}
if (-not $claude) {
    Add-Result 'claude 경로' $false 'where claude 실패 — Claude Code 설치/PATH 확인'
    $report | Format-Table -AutoSize; exit 1
}
Write-Json "$Root\config.json" ([ordered]@{ claudePath = $claude })
Add-Result 'claude 경로' $true $claude

$help = (& $claude --help 2>&1) -join "`n"
$missing = @('-p', '--allowedTools', '--permission-mode') | Where-Object { $help -notmatch [regex]::Escape($_) }
Add-Result 'CLI 플래그' ($missing.Count -eq 0) $(if ($missing) { "없음: $($missing -join ', ')" } else { '-p / --allowedTools / --permission-mode 확인' })

# ---------- 3. Playwright MCP (프로젝트 범위, Edge + 로그인 유지 프로필) ----------
$npx = $null
try { $npx = (Get-Command npx -ErrorAction Stop).Source } catch {}
Add-Result 'Node.js(npx)' ([bool]$npx) $(if ($npx) { $npx } else { 'https://nodejs.org 에서 LTS 설치 후 재실행' })

Write-Json "$Root\.mcp.json" ([ordered]@{
    mcpServers = [ordered]@{
        playwright = [ordered]@{
            command = 'cmd'
            args    = @('/c', 'npx', '-y', '@playwright/mcp@latest',
                        '--browser', 'msedge',
                        '--user-data-dir', "$Root\browser-profile")
        }
    }
})
Write-Json "$Root\.claude\settings.local.json" ([ordered]@{
    enableAllProjectMcpServers = $true
    enabledMcpjsonServers      = @('playwright')
})

Push-Location $Root
$mcpList = (& $claude mcp list 2>&1) -join "`n"
Pop-Location
Add-Result 'Playwright MCP' ($mcpList -match 'playwright') $(if ($mcpList -match 'playwright.*(Connected|✓)') { '연결됨' } else { 'claude mcp list 결과 확인 필요' })
$hasNotion = $mcpList -match '(?i)notion'
Add-Result '노션 MCP' $hasNotion $(if ($hasNotion) { '연결됨 — 협업 허브 기록 가능' } else { '미연결 — 결과는 logs\scan 에만 저장' })

# ---------- 4. 작업 스케줄러 (로그온했을 때만 실행 / 20분 제한) ----------
$ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
                -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

function New-Action($stage) {
    New-ScheduledTaskAction -Execute $ps -WorkingDirectory $Root `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Root\run-scan.ps1`" -Stage $stage"
}
function Register-Hunter($name, $stage, $trigger) {
    try {
        Register-ScheduledTask -TaskName $name -Action (New-Action $stage) -Trigger $trigger `
            -Principal $principal -Settings $settings -Force | Out-Null
        Add-Result "예약 $name" $true ((Get-ScheduledTask -TaskName $name | Get-ScheduledTaskInfo).NextRunTime)
    } catch { Add-Result "예약 $name" $false $_.Exception.Message }
}

Register-Hunter 'ReviewTrialHunter_Daily'  'naver'  (New-ScheduledTaskTrigger -Daily -At 09:00)
Register-Hunter 'ReviewTrialHunter_Weekly' 'weekly' (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 21:00)

if ($EnableMusinsa) {
    Register-Hunter 'ReviewTrialHunter_MWF' 'musinsa' (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Wednesday, Friday -At 09:10)
} else { Unregister-ScheduledTask -TaskName 'ReviewTrialHunter_MWF' -Confirm:$false -ErrorAction SilentlyContinue }

if ($EnableBlog) {
    Register-Hunter 'ReviewTrialHunter_TT' 'blog' (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday, Thursday -At 09:20)
} else { Unregister-ScheduledTask -TaskName 'ReviewTrialHunter_TT' -Confirm:$false -ErrorAction SilentlyContinue }

# 월간 트리거는 New-ScheduledTaskTrigger 가 지원하지 않아 schtasks 로 만든 뒤 설정만 덮어씀
$tr = "`"$ps`" -NoProfile -ExecutionPolicy Bypass -File `"$Root\run-scan.ps1`" -Stage monthly"
schtasks /Create /TN 'ReviewTrialHunter_Monthly' /TR $tr /SC MONTHLY /D 1 /ST 09:30 /IT /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -eq 0) {
    Set-ScheduledTask -TaskName 'ReviewTrialHunter_Monthly' -Settings $settings | Out-Null
    Add-Result '예약 ReviewTrialHunter_Monthly' $true ((Get-ScheduledTask -TaskName 'ReviewTrialHunter_Monthly' | Get-ScheduledTaskInfo).NextRunTime)
} else { Add-Result '예약 ReviewTrialHunter_Monthly' $false "schtasks exit $LASTEXITCODE" }

# ---------- 5. (선택) 테스트 실행 ----------
if ($RunTest) {
    & $ps -NoProfile -ExecutionPolicy Bypass -File "$Root\run-scan.ps1" -Stage naver
    $tail = Get-Content "$Root\logs\naver.log" -Tail 1 -Encoding UTF8
    Add-Result '네이버 스캔 1회' ($tail -match 'exit 0') $tail
}

# ---------- 보고 ----------
Write-Host ''
Write-Host '===== review-trial-hunter 설치 결과 ====='
$report | Format-Table -AutoSize -Wrap
Write-Host '다음: (1) login.ps1 로 사이트 로그인  (2) SKILL.md 1.1/1.2 계정·사이즈 채우기  (3) -RunTest 로 재실행 또는 schtasks /Run /TN ReviewTrialHunter_Daily'
