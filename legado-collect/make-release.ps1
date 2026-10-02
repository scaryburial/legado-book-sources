# 创建 GitHub Release 并上传附件
param(
    [string]$Repo = 'scaryburial/legado-book-sources',
    [string]$Tag = 'v1.0.0'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$token = [regex]::Match((Get-Content -Raw "$env:USERPROFILE\.codex\.codex-global-state.json"),
                        'gh[po]_[A-Za-z0-9_]{20,}').Value
$headers = @{
    Authorization = "Bearer $token"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'codex'
}

$body = @{
    tag_name   = $Tag
    name       = "内置书源版 APK $Tag"
    body       = @"
基于官方 io.legado.app.release v3.26.042717 重打包，只改内置数据、没动代码。两个包同一签名，可互相覆盖安装。

## 阅读APP-内置主流书源.apk（17.8 MB）
- 内置精品书源 1944 条（按规则完整度 + 更新时间排序取前 18 MB）
- 内置净化规则 23 条
- 适合直接分享使用

## 阅读APP-内置成人向书源.apk（17.1 MB）
- 内置成人向书源 2323 条（全量）
- 内置净化规则 23 条

## 安装注意
签名与官方版不同，**首次安装必须先卸载官方版**（会清空书架和阅读进度，建议先导出备份）。
装好任一版本后，再装另一个可直接覆盖，不用卸载。

首次启动、数据库为空时会自动导入内置书源。

完整书源库（主流 19301 条 / 成人向 2323 条，按形态与题材分类）在仓库的 legado-collect/ 目录下。
"@
    draft      = $false
    prerelease = $false
} | ConvertTo-Json

$rel = Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$Repo/releases" `
    -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 60
"已创建 Release: $($rel.html_url)"

$assets = @(
    (Join-Path $root '阅读APP-内置主流书源.apk'),
    (Join-Path $root '阅读APP-内置成人向书源.apk'),
    (Join-Path $root '成人向书源-全量2323条.json')
)
foreach ($f in $assets) {
    $name = [System.IO.Path]::GetFileName($f)
    $enc = [uri]::EscapeDataString($name)
    $up = "https://uploads.github.com/repos/$Repo/releases/$($rel.id)/assets?name=$enc"
    try {
        $a = Invoke-RestMethod -Method Post -Uri $up -Headers $headers `
            -InFile $f -ContentType 'application/octet-stream' -TimeoutSec 900
        "  已上传 {0}  ({1:N1} MB)" -f $a.name, ($a.size / 1MB)
    } catch {
        "  上传失败 $name : $($_.Exception.Message)"
    }
}
""
"Release 地址: $($rel.html_url)"
