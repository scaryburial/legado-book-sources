# 第二批：其它含书源数据的仓库
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
$tb = Join-Path $raw 'tarballs'
$repos = Join-Path $raw 'repos'
New-Item -ItemType Directory -Force -Path $tb, $repos | Out-Null

$targets = @(
    @{ r = 'oevery/Source';                     br = 'master' }
    @{ r = 'CandyMuj/ResourceInterface';        br = 'main' }
    @{ r = 'DowneyRem/PixivSource';             br = 'main' }
    @{ r = 'leetomlee123/book';                 br = 'main' }
    @{ r = 'ssnangua/ColorTxt';                 br = 'main' }
    @{ r = 'CCSSNE/legadoC';                    br = 'main' }
    @{ r = 'Jingshiro/legado';                  br = 'main' }
    @{ r = 'Zzzia/EasyBook';                    br = 'master' }
    @{ r = 'LegadoTeam/legado-rule';            br = 'main' }
)

foreach ($t in $targets) {
    $safe = ($t.r -replace '/', '__') + '__' + $t.br
    $tgz = Join-Path $tb "$safe.tgz"
    $dest = Join-Path $repos $safe
    if (-not ((Test-Path -LiteralPath $tgz) -and (Get-Item -LiteralPath $tgz).Length -gt 1024)) {
        try {
            Invoke-WebRequest -Uri "https://codeload.github.com/$($t.r)/tar.gz/refs/heads/$($t.br)" `
                -OutFile $tgz -TimeoutSec 300 -UseBasicParsing
        } catch {
            "FAIL $($t.r)@$($t.br): $($_.Exception.Message)"
            continue
        }
    }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    & tar.exe -xzf $tgz -C $dest --strip-components=1 2>$null
    $jsonCount = (Get-ChildItem -LiteralPath $dest -Recurse -File -Include *.json -ErrorAction SilentlyContinue).Count
    "OK {0,-34} {1,7:N1} MB  json={2}" -f $t.r, ((Get-Item -LiteralPath $tgz).Length / 1MB), $jsonCount
}
