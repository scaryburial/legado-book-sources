# 从候选里筛出"书源"相关仓库，按 star 排序输出
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$raw = Join-Path $root 'raw'

$list = Get-Content -Raw -LiteralPath (Join-Path $raw 'all-repos.json') | ConvertFrom-Json

# 命中即算书源仓库
$hit = '书源|書源|legado|Legado|bookSource|booksource|Yuedu|yuedu|阅读3|阅读 3|reading source|阅读APP|阅读app'
# 明显不是（讲编程的书/资源集合）——仅在名字里带 book 但描述无关时排除
$noise = 'open-source book|开源书|开源图书|电子书下载|MyBatis|pytorch|TensorFlow|算法|面试|font|字体'

$sel = $list | Where-Object {
    $text = "$($_.repo) $($_.desc)"
    ($text -match $hit) -and ($_.repo -notmatch '^gedoor/legado$') -and ($text -notmatch $noise)
} | Sort-Object -Property @{e='stars';Descending=$true}

$sel | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $raw 'selected-repos.json') -Encoding utf8NoBOM
"筛选后: $($sel.Count)"
""
$i = 0
$sel | ForEach-Object {
    $i++
    $d = ($_.desc -replace '\s+', ' ')
    if ($d.Length -gt 60) { $d = $d.Substring(0, 60) }
    "{0,3} | {1,5}星 | {2} | {3} | {4}" -f $i, $_.stars, $_.pushed, $_.repo, $d
}
