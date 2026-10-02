# 等待 N 分钟后把仓库转回私有（后台常驻）
param(
    [int]$Minutes = 10,
    [string]$Repo = 'scaryburial/legado-book-sources',
    [string]$Log = ''
)
$toggle = Join-Path $PSScriptRoot 'toggle-repo-visibility.ps1'

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    if ($Log) { Add-Content -LiteralPath $Log -Value $line -Encoding utf8 }
}

Write-Log "定时器启动，将在 $Minutes 分钟后把 $Repo 转回私有"
Start-Sleep -Seconds ($Minutes * 60)
try {
    $out = & $toggle -Repo $Repo -Private $true 2>&1
    Write-Log ("执行结果: " + ($out -join ' '))
} catch {
    Write-Log ("失败: " + $_.Exception.Message)
}
