# 下载精选仓库 tarball 并解压到 raw/repos/<owner>__<repo>/
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
$tb = Join-Path $raw 'tarballs'
$repos = Join-Path $raw 'repos'
New-Item -ItemType Directory -Force -Path $tb, $repos | Out-Null

$all = Get-Content -Raw -LiteralPath (Join-Path $raw 'all-repos.json') | ConvertFrom-Json

$want = @(
    'XIU2/Yuedu'
    'aoaostar/legado'
    'ZGQ-inc/source'
    'liufuyou/read'
    'jiwangyihao/source-j-legado'
    'ZWolken/Light-Novel-Yuedu-Source'
    'Luoyacheng/yuedu'
    'Wenmoux/sources'
    'aikankankanhhh998/shuxiangzhijiayuan'
    'entr0pia/MyLegadoSource'
    'sjshb57/legado-57'
    'MajoSissi/legado-source'
    'booksources/booksources.github.io'
    'yolo52/Yuedu'
    'cyao2q/yuedu'
    'kooofu/yueduyuan'
    'Clean-Reader/CleanReader.Sources'
    'daiaji/LegadoSource'
    'someok/booksources'
    'Orokapei/BookSource'
    'Eliauk365/yuedu'
    'fmpfmp/YueDuBackup'
    'pindaCrazy/BookSourceForReader3.0'
    'chillingfir/BookSourceForLegado'
    'LM-Firefly/booksource'
    'deepink-app/booksource'
    'zmn001125/booksources'
    'zimkyes/legado_source'
    'speauty/legado.sources'
    'hxwxww/BookSources'
    'KotaHv/legadoBookSource'
    'TinhoXu/BookSource'
    'Dancying/Legado-Adaptation-Plan'
    'gs1147/fanqie-booksource'
    'rektpartyaftermath/Legado-booksource-collection'
)

foreach ($w in $want) {
    $meta = $all | Where-Object { $_.repo -eq $w } | Select-Object -First 1
    if (-not $meta) { "SKIP $w (无元数据)"; continue }
    $br = if ($meta.default_br) { $meta.default_br } else { 'main' }
    $safe = ($w -replace '/', '__')
    $tgz = Join-Path $tb "$safe.tgz"
    $dest = Join-Path $repos $safe
    $url = "https://codeload.github.com/$w/tar.gz/refs/heads/$br"

    if (-not (Test-Path -LiteralPath $tgz) -or (Get-Item -LiteralPath $tgz).Length -lt 1024) {
        try {
            Invoke-WebRequest -Uri $url -OutFile $tgz -TimeoutSec 180 -UseBasicParsing
        } catch {
            "FAIL $w 下载失败: $($_.Exception.Message)"
            continue
        }
    }
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    & tar.exe -xzf $tgz -C $dest --strip-components=1 2>$null

    $jsonCount = (Get-ChildItem -LiteralPath $dest -Recurse -File -Include *.json -ErrorAction SilentlyContinue).Count
    "OK {0,-55} {1,7:N1} MB  json={2}" -f $w, ((Get-Item -LiteralPath $tgz).Length / 1MB), $jsonCount
}
