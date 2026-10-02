# 追加检索：topic + in:name，覆盖更多书源合集仓库
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'

$headers = @{ 'User-Agent' = 'codex-booksource-research'; 'Accept' = 'application/vnd.github+json' }
$queries = @{
    't-legado'      = 'topic:legado'
    't-booksource'  = 'topic:booksource'
    't-yuedu'       = 'topic:yuedu'
    't-阅读'        = 'topic:阅读'
    'n-shuyuan'     = 'shuyuan in:name'
    'n-书源'        = '书源 in:name'
    'd-书源合集'    = '书源 合集 in:description,readme'
    'd-源仓库'      = '源仓库 书源'
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
