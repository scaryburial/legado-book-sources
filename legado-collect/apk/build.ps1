# 内置成人向书源 + 净化规则，重打包并签名
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$bt   = 'C:\Users\Administrator\AppData\Local\Android\Sdk\build-tools\35.0.1'
$ks   = Join-Path $here 'legado-built.keystore'
$out  = Join-Path $here 'legado-adult-built.apk'

# ---------- 1. 重打包 ----------
python (Join-Path $here 'repack.py')

# ---------- 2. 对齐（resources.arsc 必须 4 字节对齐） ----------
$aligned = Join-Path $here 'aligned.apk'
& "$bt\zipalign.exe" -f -p 4 (Join-Path $here 'unsigned.apk') $aligned
"zipalign 完成"

# ---------- 3. 生成签名密钥（仅首次） ----------
if (-not (Test-Path -LiteralPath $ks)) {
    & keytool -genkeypair -v -keystore $ks -alias legado `
        -keyalg RSA -keysize 2048 -validity 10950 `
        -storepass legado123 -keypass legado123 `
        -dname "CN=Legado Built, OU=Personal, O=Personal, L=CN, S=CN, C=CN"
    "已生成 keystore: $ks"
}

# ---------- 4. 签名（v1+v2+v3） ----------
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Force }
& "$bt\apksigner.bat" sign `
    --ks $ks --ks-key-alias legado `
    --ks-pass pass:legado123 --key-pass pass:legado123 `
    --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true `
    --out $out $aligned
"签名完成: $out"

# ---------- 5. 校验 ----------
& "$bt\apksigner.bat" verify --verbose --print-certs $out
""
"产物: {0}  ({1:N1} MB)" -f $out, ((Get-Item -LiteralPath $out).Length / 1MB)
Get-ChildItem -LiteralPath $here -Filter '*.apk' | Select-Object Name, Length | Format-Table -AutoSize
