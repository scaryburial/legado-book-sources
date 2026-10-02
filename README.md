# Legado（阅读）书源整理

## 直接下载

| 文件 | 说明 |
| --- | --- |
| [阅读APP-内置成人向书源.apk](./阅读APP-内置成人向书源.apk) | **已编译好的阅读 App**，内置成人向书源 2323 条 + 净化规则 23 条 |
| [成人向书源-全量2323条.json](./成人向书源-全量2323条.json) | 单独的书源包，可手动导入任意版本阅读 App |
| [成人向书源整理.md](./成人向书源整理.md) | 成人向那套的分类说明 |
| [书源整理.md](./书源整理.md) | 主流书源那套的分类说明 |

## 这个 APK 是什么

- 基于官方 `io.legado.app.release` v3.26.042717 重打包，**只改了内置数据**，没动任何代码
- 内置 `assets/defaultData/bookSources.json`（2323 条成人向书源）
- 内置 `assets/defaultData/replaceRule.json`（23 条净化规则）
- 首次启动、数据库为空时会自动导入内置书源

### 安装注意

**签名与官方版不同，必须先卸载官方版**（会清空书架与阅读进度，建议先导出备份）。

## 书源成果目录

| 目录 | 内容 |
| --- | --- |
| `legado-collect/out/` | 主流书源 19301 条，按形态 / 题材 / 质量分好类 |
| `legado-collect/out-adult/` | 成人向书源 2323 条，单独一套分类 |
| `legado-collect/apk/` | APK 构建脚本、keystore 与构建说明 |

详细统计见 `legado-collect/out/stats.json` 与 `legado-collect/out-adult/stats.json`。

## 自行重建

```powershell
python .\legado-collect\merge.py                      # 采集结果 -> 去重分类
pwsh -File .\legado-collect\apk\build.ps1            # 重打包 + 签名 APK
```
