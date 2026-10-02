# 创建仓库并推送（用完把 remote 还原成不带 token 的地址）
param(
    [string]$RepoName = 'legado-book-sources',
    [switch]$Public
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$token = (Get-Content -Raw -LiteralPath (Join-Path $root '.token.tmp')).Trim()

$headers = @{
    Authorization          = "Bearer $token"
    Accept                 = 'application/vnd.github+json'
    'User-Agent'           = 'codex'
}

$body = @{
    name        = $RepoName
    description = 'Legado（阅读）书源整理：多仓库采集、去重、分类与可达性实测，含内置书源版 APK'
    private     = -not $Public
    has_issues  = $true
} | ConvertTo-Json

try {
    $repo = Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' `
        -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 60
    "已创建仓库: $($repo.full_name)  private=$($repo.private)"
} catch {
    if ($_.Exception.Message -match '422') {
        "仓库已存在，直接推送"
        $repo = Invoke-RestMethod -Uri "https://api.github.com/repos/scaryburial/$RepoName" -Headers $headers -TimeoutSec 60
    } else { throw }
}

$clean = "https://github.com/$($repo.full_name).git"
$withToken = "https://$token@github.com/$($repo.full_name).git"

Push-Location $root
try {
    git remote remove origin 2>$null
    git remote add origin $withToken
    "开始推送（仓库约 130 MB，可能要几分钟）..."
    git push -u origin master --force
    "push exit=$LASTEXITCODE"
    git remote set-url origin $clean
    "remote 已还原: $(git remote get-url origin)"
} finally {
    Pop-Location
}

""
"仓库地址: $($repo.html_url)"
