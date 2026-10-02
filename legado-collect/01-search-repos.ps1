# 检索 GitHub 上的书源相关仓库，结果落盘到 raw/search-*.json
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
New-Item -ItemType Directory -Force -Path $raw | Out-Null

$headers = @{
    'User-Agent' = 'codex-booksource-research'
    'Accept'     = 'application/vnd.github+json'
}

$queries = @{
    'q-书源'        = '书源'
    'q-legado'      = 'legado'
    'q-阅读书源'    = '阅读 书源 in:name,description,readme'
    'q-booksource'  = 'bookSource in:name,description,readme'
    'q-legado源'    = 'legado 书源 in:name,description,readme'
    'q-阅读3'       = '阅读3.0 书源 in:name,description,readme'
}

foreach ($k in $queries.Keys) {
    $q = [uri]::EscapeDataString($queries[$k])
    $uri = "https://api.github.com/search/repositories?q=$q&sort=stars&order=desc&per_page=100"
    try {
        $resp = Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 40
        $resp | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $raw "$k.json") -Encoding utf8NoBOM
        "[$k] total=$($resp.total_count) got=$($resp.items.Count)"
    } catch {
        "[$k] ERR: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 7
}
