# 并行跑三段"超时/失败"复检
$ErrorActionPreference = 'Stop'
$wd = 'C:\Users\Administrator\Documents\ChatGPT\插件'
$log = Join-Path $wd 'legado-collect\raw'

foreach ($i in 0, 1, 2) {
    Start-Process -FilePath 'python' `
        -ArgumentList @('.\legado-collect\12-retry-alive.py', '--shard', "$i", '--shards', '3',
                        '--timeout', '20', '--retries', '2', '--workers', '160', '--tag', 'R1') `
        -WorkingDirectory $wd -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $log "retry-$i.log") `
        -RedirectStandardError  (Join-Path $log "retry-$i.err")
}

Start-Sleep -Seconds 10
"已启动 python 进程数: " + (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
