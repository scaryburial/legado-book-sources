# 合并 6 组搜索结果 -> 去重 -> 按 star / 更新时间排序，输出候选仓库清单
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'

$all = @{}
$searchFiles = Get-ChildItem -LiteralPath $raw -Filter '*.json' |
    Where-Object { $_.Name -notin @('all-repos.json', 'selected-repos.json', 'json-inventory.json',
                                     'repo-meta.json', 'repo-contribution.json') -and $_.Name -notlike 'alive*' }
foreach ($f in $searchFiles) {
    $doc = Get-Content -Raw -LiteralPath $f.FullName | ConvertFrom-Json
    if (-not $doc.items) { continue }
    foreach ($it in $doc.items) {
        if (-not $all.ContainsKey($it.full_name)) {
            $all[$it.full_name] = [pscustomobject]@{
                repo        = $it.full_name
                stars       = $it.stargazers_count
                forks       = $it.forks_count
                pushed      = ([datetime]$it.pushed_at).ToString('yyyy-MM-dd')
                updated     = ([datetime]$it.updated_at).ToString('yyyy-MM-dd')
                archived    = $it.archived
                lang        = $it.language
                size_kb     = $it.size
                desc        = $it.description
                default_br  = $it.default_branch
                url         = $it.html_url
            }
        }
    }
}

$list = $all.Values | Sort-Object -Property @{e='stars';Descending=$true}, @{e='pushed';Descending=$true}
$list | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $raw 'all-repos.json') -Encoding utf8NoBOM

"候选仓库总数: $($list.Count)"
""
$i = 0
$list | Select-Object -First 60 | ForEach-Object {
    $i++
    $d = ($_.desc -replace '\s+', ' ')
    if ($d.Length -gt 70) { $d = $d.Substring(0, 70) }
    "{0,3} | {1,6}星 | {2} | {3} | {4}" -f $i, $_.stars, $_.pushed, $_.repo, $d
}
