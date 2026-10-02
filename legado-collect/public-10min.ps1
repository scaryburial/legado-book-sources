# 先把仓库转公开，再起一个后台进程，N 分钟后自动转回私有
param(
    [int]$Minutes = 10,
    [string]$Repo = 'scaryburial/legado-book-sources'
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$toggle = Join-Path $here 'toggle-repo-visibility.ps1'

# 1. 立即公开
& $toggle -Repo $Repo -Private $false

# 2. 起后台定时器（独立进程，不受当前会话影响）
$waiter = Join-Path $here 'restore-private.ps1'
$log = Join-Path $here 'visibility.log'
Start-Process -FilePath 'pwsh' -WindowStyle Hidden -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $waiter,
    '-Minutes', "$Minutes", '-Repo', $Repo, '-Log', $log
)

"已公开: https://github.com/$Repo"
"将在 $Minutes 分钟后自动转回私有（后台进程已启动，日志: $log）"
