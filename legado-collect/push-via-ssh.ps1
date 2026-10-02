# 生成专用部署密钥 -> 挂到目标仓库 -> 走 SSH(22) 推送
param(
    [string]$Repo = 'scaryburial/legado-book-sources',
    [string]$KeyPath = "$env:USERPROFILE\.ssh\legado-sources-deploy"
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$token = (Get-Content -Raw -LiteralPath (Join-Path $root '.token.tmp')).Trim()

# ---------- 1. 生成部署密钥 ----------
if (-not (Test-Path -LiteralPath $KeyPath)) {
    & ssh-keygen -t ed25519 -N '""' -C 'legado-sources-deploy' -f $KeyPath
    "已生成密钥: $KeyPath"
} else {
    "复用已有密钥: $KeyPath"
}
$pub = (Get-Content -Raw -LiteralPath "$KeyPath.pub").Trim()

# ---------- 2. 挂到仓库（读写部署密钥） ----------
$headers = @{
    Authorization = "Bearer $token"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'codex'
}
$body = @{
    title     = 'legado-sources-deploy'
    key       = $pub
    read_only = $false
} | ConvertTo-Json

try {
    $k = Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$Repo/keys" `
        -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 60
    "已添加部署密钥 id=$($k.id)  read_only=$($k.read_only)"
} catch {
    "添加密钥返回: $($_.Exception.Message)"
}

# ---------- 3. 测试 SSH 认证 ----------
$env:GIT_SSH_COMMAND = "ssh -i `"$KeyPath`" -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
ssh -i $KeyPath -o StrictHostKeyChecking=accept-new -o BatchMode=yes -T git@github.com 2>&1 | Select-Object -First 3

# ---------- 4. 推送 ----------
Push-Location $root
try {
    git remote remove origin 2>$null
    git remote add origin "git@github.com:$Repo.git"
    "开始推送（SSH，约 130 MB）..."
    git push -u origin master --force
    "push exit=$LASTEXITCODE"
    git remote -v
} finally {
    Pop-Location
}
