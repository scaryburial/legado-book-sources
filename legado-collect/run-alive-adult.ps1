# 并行跑成人向书源的可达性检测（3 段）
$ErrorActionPreference = 'Stop'
$wd = 'C:\Users\Administrator\Documents\ChatGPT\插件'
$log = Join-Path $wd 'legado-collect\raw'
$base = Join-Path $wd 'legado-collect\out-adult\00-全量去重'

$shards = @(
    @{ tag = 'A'; from = 1; to = 2 },
    @{ tag = 'B'; from = 3; to = 4 },
    @{ tag = 'C'; from = 5; to = 5 }
)

foreach ($s in $shards) {
    Start-Process -FilePath 'python' `
        -ArgumentList @('.\legado-collect\check-alive.py', '--from', "$($s.from)", '--to', "$($s.to)",
                        '--tag', $s.tag, '--workers', '160', '--base', $base) `
        -WorkingDirectory $wd -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $log "adult-$($s.tag).log") `
        -RedirectStandardError  (Join-Path $log "adult-$($s.tag).err")
}

Start-Sleep -Seconds 10
"已启动 python 进程数: " + (Get-Process python -ErrorAction SilentlyContinue | Measure-Object).Count
