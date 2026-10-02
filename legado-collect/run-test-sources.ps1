# 并行跑书源可用性测试：4 个独立进程分片
param(
    [int]$Processes = 4,
    [int]$Workers = 150
)
$ErrorActionPreference = 'Stop'
$wd = 'C:\Users\Administrator\Documents\ChatGPT\插件'
$log = Join-Path $wd 'legado-collect\raw'

$tags = @('A', 'B', 'C', 'D')
for ($i = 0; $i -lt $Processes; $i++) {
    Start-Process -FilePath 'python' `
        -ArgumentList @('.\legado-collect\21-test-sources.py', '--shard', "$i", '--shards', "$Processes",
                        '--workers', "$Workers", '--tag', $tags[$i]) `
        -WorkingDirectory $wd -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $log "test-$($tags[$i]).log") `
        -RedirectStandardError  (Join-Path $log "test-$($tags[$i]).err")
}

Start-Sleep -Seconds 10
"已启动测试进程数: " + (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
