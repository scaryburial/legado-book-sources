# 切换仓库可见性：-Private $true 转私有，-Private $false 转公开
param(
    [string]$Repo = 'scaryburial/legado-book-sources',
    [Parameter(Mandatory = $true)][bool]$Private
)
$ErrorActionPreference = 'Stop'
$statePath = Join-Path $env:USERPROFILE '.codex\.codex-global-state.json'
$raw = Get-Content -Raw -LiteralPath $statePath
$token = [regex]::Match($raw, 'gh[po]_[A-Za-z0-9_]{20,}').Value
if (-not $token) { throw '未能从状态文件中取出 token' }

$headers = @{
    Authorization = "Bearer $token"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'codex'
}
$body = @{ private = $Private } | ConvertTo-Json
$r = Invoke-RestMethod -Method Patch -Uri "https://api.github.com/repos/$Repo" `
    -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 60

"[{0}] {1} -> private={2}" -f (Get-Date -Format 'HH:mm:ss'), $r.full_name, $r.private
