# login.ps1 — 자동화 전용 Edge 프로필에 사이트별로 한 번 직접 로그인한다.
# 비밀번호는 사람이 직접 입력. 스크립트는 창만 연다. 다 끝나면 Edge 창을 모두 닫을 것.
$ProfileDir = 'C:\workspace\review-trial\browser-profile'
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$urls = @(
    'https://nid.naver.com/nidlogin.login',
    'https://www.musinsa.com/auth/login'
)

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }

Start-Process $edge -ArgumentList (@("--user-data-dir=$ProfileDir") + $urls)
Write-Host ''
Write-Host '1) 열린 Edge 창에서 네이버(무신사 계정이 있으면 무신사도) 로그인'
Write-Host '   - 네이버는 [로그인 상태 유지] 체크'
Write-Host '2) 레뷰/강남맛집/서울오빠 계정이 있으면 같은 창에서 로그인'
Write-Host '3) 끝나면 Edge 창을 전부 닫고 Enter (창이 열려 있으면 자동화가 프로필을 못 씀)'
Read-Host | Out-Null
