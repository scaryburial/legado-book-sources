# 临时 HTTP 下载服务：默认 10 分钟后自动关闭
param(
    [int]$Minutes = 10,
    [int]$Port = 8000
)
$ErrorActionPreference = 'Stop'

$share = Join-Path $PSScriptRoot 'share'
New-Item -ItemType Directory -Force -Path $share | Out-Null

# 准备要分享的文件
$apk = 'C:\Users\Administrator\Downloads\io.legado.app.release-built.apk'
$json = 'C:\Users\Administrator\Downloads\成人向书源-全量2323条.json'
Copy-Item -LiteralPath $apk -Destination (Join-Path $share 'legado-adult-built.apk') -Force
Copy-Item -LiteralPath $json -Destination (Join-Path $share '成人向书源-全量2323条.json') -Force
Copy-Item -LiteralPath 'C:\Users\Administrator\Documents\ChatGPT\插件\成人向书源整理.md' -Destination $share -Force
Copy-Item -LiteralPath 'C:\Users\Administrator\Documents\ChatGPT\插件\书源整理.md' -Destination $share -Force

$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress

$proc = Start-Process -FilePath 'python' `
    -ArgumentList @('-m', 'http.server', "$Port", '--bind', '0.0.0.0', '--directory', $share) `
    -WindowStyle Hidden -PassThru

"下载服务已启动，PID=$($proc.Id)"
"地址： http://$ip`:$Port/"
""
Get-ChildItem -LiteralPath $share | ForEach-Object {
    "  http://$ip`:$Port/$([uri]::EscapeDataString($_.Name))"
}
""
"$Minutes 分钟后自动关闭..."
Start-Sleep -Seconds ($Minutes * 60)
if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
"已关闭下载服务。"
