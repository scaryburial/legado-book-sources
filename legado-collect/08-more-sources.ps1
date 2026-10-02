# 补下载：修正分支的重试 + MyData 仓库里的书源文件（按需下载，不整包拉取）
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
$tb = Join-Path $raw 'tarballs'
$repos = Join-Path $raw 'repos'
$h = @{ 'User-Agent' = 'codex-research'; 'Accept' = 'application/vnd.github+json' }

# ---------- 0. 清掉 ZGQ 的无效空分片 ----------
Get-ChildItem -LiteralPath (Join-Path $raw 'zgq') -Filter 'bookSource_*.json' |
    Where-Object { $_.Length -lt 2048 } | Remove-Item -Force

# ---------- 1. 重试 tarball ----------
foreach ($t in @(
        @{ r = 'e101406/booksources'; br = 'master' }
        @{ r = 'oli-fa/YueDuBackup'; br = 'master' }
    )) {
    $safe = ($t.r -replace '/', '__') + '__' + $t.br
    $tgz = Join-Path $tb "$safe.tgz"
    $dest = Join-Path $repos $safe
    try {
        Invoke-WebRequest -Uri "https://codeload.github.com/$($t.r)/tar.gz/refs/heads/$($t.br)" -OutFile $tgz -TimeoutSec 300 -UseBasicParsing
    } catch { "FAIL $($t.r): $($_.Exception.Message)"; continue }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    & tar.exe -xzf $tgz -C $dest --strip-components=1 2>$null
    $jsonCount = (Get-ChildItem -LiteralPath $dest -Recurse -File -Include *.json -ErrorAction SilentlyContinue).Count
    "OK $($t.r)@$($t.br)  {0:N1} MB  json={1}" -f ((Get-Item -LiteralPath $tgz).Length / 1MB), $jsonCount
}

# ---------- 2. xdd666t/MyData: 只取 noval 目录下的书源 ----------
$tree = Invoke-RestMethod -Uri 'https://api.github.com/repos/xdd666t/MyData/git/trees/master?recursive=1' -Headers $h -TimeoutSec 60
$cand = $tree.tree | Where-Object { $_.type -eq 'blob' -and $_.size -gt 2000 -and $_.size -lt 30MB -and $_.path -match '(?i)(noval|novel|书源|shuyuan)' -and $_.path -match '\.(json|txt|json5)?$' }
"MyData 候选文件: $($cand.Count)"
$dest = Join-Path $repos 'xdd666t__MyData'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($c in $cand) {
    $out = Join-Path $dest ($c.path -replace '/', '__')
    try {
        Invoke-WebRequest -Uri "https://raw.githubusercontent.com/xdd666t/MyData/master/$($c.path)" -OutFile $out -TimeoutSec 120 -UseBasicParsing
        "  OK {0,10:N0} B  {1}" -f (Get-Item -LiteralPath $out).Length, $c.path
    } catch { "  FAIL $($c.path)" }
}
