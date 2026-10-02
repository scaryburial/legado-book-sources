# 补充下载：ZGQ 托管书源、shidahuilang、以及其它批量合集
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
$tb = Join-Path $raw 'tarballs'
$repos = Join-Path $raw 'repos'
$zgq = Join-Path $raw 'zgq'
New-Item -ItemType Directory -Force -Path $tb, $repos, $zgq | Out-Null

function Get-File($url, $out) {
    if ((Test-Path -LiteralPath $out) -and (Get-Item -LiteralPath $out).Length -gt 1024) { return $true }
    try { Invoke-WebRequest -Uri $url -OutFile $out -TimeoutSec 180 -UseBasicParsing; return $true }
    catch { return $false }
}

# ---------- A. ZGQ 托管的书源分片 ----------
for ($i = 1; $i -le 30; $i++) {
    $out = Join-Path $zgq "bookSource_$i.json"
    $ok = Get-File "https://source-repo.zgqinc.gq/legado3/bookSource/bookSource_$i.json" $out
    if (-not $ok) { "ZGQ 分片到 $($i-1) 结束"; break }
    "ZGQ 分片 $i : {0:N1} MB" -f ((Get-Item -LiteralPath $out).Length / 1MB)
}

# ---------- B. 其它仓库 tarball ----------
$targets = @(
    @{ r = 'shidahuilang/shuyuan'; br = 'main' }
    @{ r = 'shidahuilang/shuyuan'; br = 'shuyuan' }
    @{ r = 'e101406/booksources'; br = 'main' }
    @{ r = 'cloudmantou/cloudBookSource'; br = 'main' }
    @{ r = 'oli-fa/YueDuBackup'; br = 'main' }
    @{ r = 'Cyril0563/FREE_COMIC-BOOK'; br = 'main' }
)
foreach ($t in $targets) {
    $safe = ($t.r -replace '/', '__') + '__' + $t.br
    $tgz = Join-Path $tb "$safe.tgz"
    $dest = Join-Path $repos $safe
    $url = "https://codeload.github.com/$($t.r)/tar.gz/refs/heads/$($t.br)"
    if (-not (Get-File $url $tgz)) { "FAIL $($t.r)@$($t.br)"; continue }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    & tar.exe -xzf $tgz -C $dest --strip-components=1 2>$null
    $jsonCount = (Get-ChildItem -LiteralPath $dest -Recurse -File -Include *.json -ErrorAction SilentlyContinue).Count
    "OK {0}@{1,-8} {2,7:N1} MB  json={3}" -f $t.r, $t.br, ((Get-Item -LiteralPath $tgz).Length / 1MB), $jsonCount
}
