$ErrorActionPreference = 'Stop'
$dir = 'C:\Users\Administrator\Documents\ChatGPT\插件'

# ---------- 1. 清理书源：只保留规则完整的 ----------
$all = Get-Content -Raw -LiteralPath "$dir\成人向书源.json" | ConvertFrom-Json
"原始条数: $($all.Count)"

$clean = $all | Where-Object {
    $_.searchUrl -and $_.ruleSearch -and $_.ruleToc.chapterList -and $_.ruleContent.content
}
"精简后:   $($clean.Count)"

$clean = $clean | Sort-Object -Property bookSourceUrl -Unique
"去重后:   $($clean.Count)"

$clean | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$dir\成人向书源_精简.json" -Encoding utf8NoBOM
"写出精简书源: {0} KB" -f [math]::Round((Get-Item "$dir\成人向书源_精简.json").Length / 1KB, 1)

# ---------- 2. 生成净化规则 ----------
$defs = @(
    @{ g = '1-广告推广'; n = '含网址的整行'; p = '(?im)^\s*[^\r\n]{0,30}(?:https?://|www\.[\w.-]+|m\.[\w.-]+)[^\r\n]*$'; r = '' }
    @{ g = '1-广告推广'; n = '"记住本站/最新网址"行'; p = '(?im)^.*(?:请记住|记住本站|记住本书|收藏本站|本站(?:地址|域名|网址|永久)|最新(?:网址|地址|域名)|永久(?:域名|网址)|备用网址).*$'; r = '' }
    @{ g = '1-广告推广'; n = '手机/PC 阅读引导行'; p = '(?im)^.*(?:手机(?:用户)?(?:请)?(?:浏览|阅读|访问)|电脑(?:用户)?(?:请|端)|扫描?二维码|扫码|关注(?:微信)?公众号|加入?书友群|下载APP|APP阅读).*$'; r = '' }
    @{ g = '1-广告推广'; n = '站点名+免费更新的水印行'; p = '(?im)^\s*[^\r\n]{0,12}(?:笔趣阁|笔趣|书吧|小说网|书网|阅读网|文学网|文学城|书院|书屋)[^\r\n]{0,24}(?:更新|提供|阅读|首发|整理|免费|无弹窗)[^\r\n]*$'; r = '' }
    @{ g = '1-广告推广'; n = '纯广告词行'; p = '(?im)^\s*(?:广告|推广|赞助|AD|【广告】|\[广告\]|【推广】)[^\r\n]*$'; r = '' }
    @{ g = '1-广告推广'; n = '"本章未完/下一页"行'; p = '(?im)^\s*(?:本章未完[，,]?)?\s*(?:请)?(?:点击|轻触|戳|按)?\s*(?:下一页继续阅读|下一页|下一頁|下页|继续阅读|翻页)[^\r\n]*$'; r = '' }
    @{ g = '1-广告推广'; n = '纯导航词行（上一章/目录/下一章）'; p = '(?im)^\s*(?:上一[章页]|下一[章页]|返回目录|返回顶部|加入书签|投推荐票|打赏|(?:章节)?目录)\s*(?:[|｜·、，,/\s]+(?:上一[章页]|下一[章页]|返回目录|返回顶部|加入书签|投推荐票|打赏|(?:章节)?目录)\s*)*$'; r = '' }
    @{ g = '1-广告推广'; n = '求收藏/求票/作者求支持行'; p = '(?im)^.*(?:求(?:收藏|推荐|月票|订阅|打分|评价|点赞)|投(?:推荐票|月票)|各位书友|感谢(?:大家)?的?支持|喜欢本书|请收藏|别忘了|多谢支持).*$'; r = '' }
    @{ g = '1-广告推广'; n = '成人站点水印行'; p = '(?im)^\s*[^\r\n]{0,15}(?:海棠|PO18|废文|废文网|書耽|书耽|长佩|腐文|腐小说)[^\r\n]{0,25}(?:文学城|书屋|小说网|阅读|免费|更新|首发|提供|文化).*$'; r = '' }

    @{ g = '2-章节冗余'; n = '第X页 / X/Y页'; p = '(?im)^\s*(?:第\s*[0-9一二三四五六七八九十]+\s*[页頁]|[0-9]+\s*/\s*[0-9]+\s*[页頁]?)\s*$'; r = '' }
    @{ g = '2-章节冗余'; n = '（本章完）/（全文完）'; p = '(?im)^\s*[（(【\[]\s*(?:本章完|全文完)\s*[）)】\]]\s*$'; r = '' }
    @{ g = '2-章节冗余'; n = '章节标题前的"正文"前缀'; p = '(?m)^\s*正文\s+(?=第)'; r = '' }
    @{ g = '2-章节冗余'; n = 'VIP 标记'; p = '(?i)(?:【VIP】|\[VIP\]|（VIP）|\(VIP\)|畅读VIP|VIP章节)'; r = '' }
    @{ g = '2-章节冗余'; n = '「最新章节」提示行'; p = '(?im)^.*(?:最新章节|无弹窗|全文字更新?|请记住本书首发域名|首发域名).*$'; r = '' }

    @{ g = '3-排版整理'; n = '行首缩进'; p = '(?m)^[ \t　]+'; r = '' }
    @{ g = '3-排版整理'; n = '行尾空白'; p = '(?m)[ \t　]+$'; r = '' }
    @{ g = '3-排版整理'; n = '正文首部空白'; p = '^\s+'; r = '' }
    @{ g = '3-排版整理'; n = '正文尾部空白'; p = '\s+$'; r = '' }
    @{ g = '3-排版整理'; n = '全角空格'; p = '　'; r = ' ' }
    @{ g = '3-排版整理'; n = 'HTML 实体'; p = '&nbsp;'; r = ' ' }
    @{ g = '3-排版整理'; n = '残留 HTML 标签'; p = '</?(?:br|p|div|span|font|a)\b[^>]*>'; r = '' }
    @{ g = '3-排版整理'; n = '连续空行压缩'; p = '(?:\r?\n){3,}'; r = "`n`n" }
    @{ g = '3-排版整理'; n = '连点省略号'; p = '\.{3,}|。{3,}'; r = '……' }
)

$rules = for ($i = 0; $i -lt $defs.Count; $i++) {
    [ordered]@{
        group       = $defs[$i].g
        id          = 800001 + $i
        isEnabled   = $true
        isRegex     = $true
        name        = $defs[$i].n
        order       = $i + 1
        pattern     = $defs[$i].p
        replacement = $defs[$i].r
        scope       = ''
    }
}

"规则条数: $($rules.Count)"

# ---------- 3. 校验每条正则能否编译 ----------
$bad = 0
foreach ($r in $rules) {
    try { [void][regex]::new($r.pattern) }
    catch { $bad++; "正则报错 -> $($r.name): $($_.Exception.Message)" }
}
"正则校验: $($rules.Count - $bad)/$($rules.Count) 通过"

$rules | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$dir\净化规则.json" -Encoding utf8NoBOM
"写出净化规则: {0} KB" -f [math]::Round((Get-Item "$dir\净化规则.json").Length / 1KB, 1)

# ---------- 4. 拿一段真实样本跑一遍，确认效果 ----------
$sample = @"
天才一秒记住本站地址：www.biquge.com，笔趣阁最快更新！
第3章 初见

　　他抬起头，看见了她。

本章未完，请点击下一页继续阅读
手机用户请浏览 m.biquge.com 阅读，更优质的阅读体验。
请记住本站域名：biquge.com
各位书友要是觉得不错，请收藏本站，投推荐票支持一下。
上一章 目录 下一章
（本章完）
"@

$out = $sample
foreach ($r in $rules) {
    if ($r.isRegex) { $out = [regex]::Replace($out, $r.pattern, $r.replacement) }
    else { $out = $out.Replace($r.pattern, $r.replacement) }
}
""
"---------- 净化前 ----------"
$sample
"---------- 净化后 ----------"
$out
