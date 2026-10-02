# 并行跑三段可达性检测（每段独立进程，各 160 线程）
$ErrorActionPreference = 'Stop'
$wd = 'C:\Users\Administrator\Documents\ChatGPT\插件'
$log = Join-Path $wd 'legado-collect\raw'

Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

$shards = @(
    @{ tag = 'A'; from = 1;  to = 7  },
    @{ tag = 'B'; from = 8;  to = 14 },
    @{ tag = 'C'; from = 15; to = 20 }
)

foreach ($s in $shards) {
    Start-Process -FilePath 'python' `
        -ArgumentList @('.\legado-collect\check-alive.py', '--from', "$($s.from)", '--to', "$($s.to)",
                        '--tag', $s.tag, '--workers', '160') `
        -WorkingDirectory $wd -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $log "alive-$($s.tag).log") `
        -RedirectStandardError  (Join-Path $log "alive-$($s.tag).err")
}

Start-Sleep -Seconds 10
"已启动 python 进程数: " + (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
