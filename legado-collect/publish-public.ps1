# 永久公开：撤掉"到点转私有"的定时器，并把仓库设为公开
$ErrorActionPreference = 'Stop'

# 1. 结束还挂着的 restore-private 定时器
$killed = 0
Get-CimInstance Win32_Process -Filter "Name = 'pwsh.exe'" | ForEach-Object {
    if ($_.CommandLine -and $_.CommandLine -match 'restore-private\.ps1') {
        Stop-Process -Id $_.ProcessId -Force
        $killed++
        "已结束定时器进程 PID=$($_.ProcessId)"
    }
}
if ($killed -eq 0) { "未发现运行中的定时器" }

# 2. 设为公开
& (Join-Path $PSScriptRoot 'toggle-repo-visibility.ps1') -Private $false
