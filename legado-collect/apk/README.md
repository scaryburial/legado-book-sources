# 内置书源版 APK 构建说明

## 产物

| 文件 | 说明 |
| --- | --- |
| `legado-adult-built.apk` | 已签名成品（也复制到了 `C:\Users\Administrator\Downloads\io.legado.app.release-built.apk`） |
| `legado-built.keystore` | 自签名密钥，口令 `legado123`，别名 `legado`。**后续升级必须用同一个 keystore**，否则装不上 |
| `repack.py` | 替换 `assets/defaultData/` 下的书源与规则后重新打包 |
| `build.ps1` | 全流程：重打包 → zipalign → 生成密钥 → apksigner 签名 → 校验 |

## 内置了什么

- `assets/defaultData/bookSources.json`：成人向书源全量 **2323 条**（13.8 MB）
- `assets/defaultData/replaceRule.json`：净化规则 **23 条**（新增文件）

其余资产（`rssSources.json`、`dictRules.json`、`txtTocRule.json`、`httpTTS.json`、
`themeConfig.json` 等）保持官方原样未动。

## 基线

- 原始 APK：`C:\Users\Administrator\Downloads\io.legado.app.release.apk`
- 包名 `io.legado.app.release`，versionName `3.26.042717`，versionCode `16558`，targetSdk 36
- 签名：v1 + v2 + v3 全部通过；`zipalign -c 4` 校验通过；`resources.arsc` 保持未压缩

## 安装注意

签名与官方版不同，**必须先卸载官方版**（会清空书架、书源、阅读进度）。
建议先在官方版里导出备份，再卸载、安装本包、导入备份。

## 重建

```powershell
pwsh -File .\legado-collect\apk\build.ps1
```

书源内容来自 `legado-collect/out-adult/00-全量去重/`，要换内容改 `repack.py` 顶部的路径即可。
