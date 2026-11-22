# run-scan.ps1 — 작업 스케줄러가 호출하는 실행기
# 사용: powershell -NoProfile -ExecutionPolicy Bypass -File run-scan.ps1 -Stage naver
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('naver', 'musinsa', 'blog', 'monthly', 'weekly')]
    [string]$Stage
)

$ErrorActionPreference = 'Stop'
$Root = 'C:\workspace\review-trial'
Set-Location $Root

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)

$cfg    = Get-Content "$Root\config.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$prompt = (Get-Content "$Root\prompts\$Stage.txt" -Raw -Encoding UTF8).Trim()
$log    = "$Root\logs\$Stage.log"
$stamp  = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

# 예약 실행 허용 도구: 셸 없음. 파일 읽기/쓰기 + 브라우저 + 노션(있을 때만 동작)
$tools = 'Read,Write,Edit,Glob,mcp__playwright,mcp__notion,mcp__claude_ai_Notion'
if ($Stage -eq 'weekly') { $tools = 'Read,Write,Edit,Glob,mcp__notion,mcp__claude_ai_Notion' }

"===== [$stamp] $Stage 시작 =====" | Out-File $log -Append -Encoding utf8
try {
    & $cfg.claudePath -p $prompt --allowedTools $tools --permission-mode acceptEdits 2>&1 |
        Out-File $log -Append -Encoding utf8
    "===== [$(Get-Date -Format 'HH:mm:ss')] $Stage 종료 (exit $LASTEXITCODE) =====" | Out-File $log -Append -Encoding utf8
} catch {
    "===== [$(Get-Date -Format 'HH:mm:ss')] $Stage 실패: $($_.Exception.Message) =====" | Out-File $log -Append -Encoding utf8
    exit 1
}
