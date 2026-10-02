# 扫描 raw/repos 下所有文件，识别出"书源 JSON 数组"（含无扩展名文件）
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'
$repos = Join-Path $raw 'repos'

$hits = New-Object System.Collections.Generic.List[object]

foreach ($repoDir in Get-ChildItem -LiteralPath $repos -Directory) {
    $repoName = $repoDir.Name -replace '__', '/'
    foreach ($f in Get-ChildItem -LiteralPath $repoDir.FullName -Recurse -File -Force -ErrorAction SilentlyContinue) {
        if ($f.Length -gt 80MB -or $f.Length -lt 16) { continue }
        if ($f.Extension -match '^\.(png|jpg|jpeg|gif|webp|ico|svg|zip|gz|tgz|apk|so|dll|exe|woff2?|ttf|eot|mp3|mp4|epub|pdf|jar|bin|pxm|bak)$') { continue }

        $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
        $text = $null
        # 去 BOM
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
        } else {
            $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        }
        $t = $text.TrimStart([char]0xFEFF, ' ', "`t", "`r", "`n")
        if (-not ($t.StartsWith('[') -or $t.StartsWith('{'))) { continue }
        if ($t -notmatch 'bookSourceUrl') { continue }

        $count = 0
        $ok = $false
        try {
            $doc = $t | ConvertFrom-Json -Depth 40
            if ($doc -is [System.Array]) {
                $count = @($doc | Where-Object { $_.PSObject.Properties.Name -contains 'bookSourceUrl' }).Count
                $ok = $true
            } elseif ($doc.PSObject.Properties.Name -contains 'bookSourceUrl') {
                $count = 1; $ok = $true
            }
        } catch { }

        $rel = $f.FullName.Substring($repoDir.FullName.Length + 1)
        $hits.Add([pscustomobject]@{
            repo   = $repoName
            path   = $rel
            bytes  = $f.Length
            parsed = $ok
            count  = $count
            mtime  = $f.LastWriteTime.ToString('yyyy-MM-dd')
        })
    }
}

$hits | Sort-Object -Property @{e='parsed';Descending=$true}, @{e='count';Descending=$true} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $raw 'json-inventory.json') -Encoding utf8NoBOM

"疑似书源文件: $($hits.Count)   (可解析: $(@($hits | Where-Object parsed).Count))"
"可解析书源条目合计: $(($hits | Where-Object parsed | Measure-Object -Property count -Sum).Sum)"
""
$hits | Where-Object parsed | Sort-Object -Property count -Descending | Select-Object -First 40 |
    ForEach-Object { "{0,7} 条 | {1,9:N0} B | {2} :: {3}" -f $_.count, $_.bytes, $_.repo, $_.path }
