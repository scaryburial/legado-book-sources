# Legado（阅读）书源整理

## 直接下载

**推荐走 [Releases](https://github.com/scaryburial/legado-book-sources/releases/latest) 下载**，那里是打好包的成品。

| 文件 | 说明 |
| --- | --- |
| [阅读APP-内置主流书源.apk](./阅读APP-内置主流书源.apk) | **主流书源版**：内置精品书源 1944 条 + 净化规则 23 条，适合直接发出去用 |
| [阅读APP-内置成人向书源.apk](./阅读APP-内置成人向书源.apk) | **成人向版**：内置成人向书源 2323 条 + 净化规则 23 条 |
| [成人向书源-全量2323条.json](./成人向书源-全量2323条.json) | 单独的书源包，可手动导入任意版本阅读 App |
| [成人向书源整理.md](./成人向书源整理.md) | 成人向那套的分类说明 |
| [书源整理.md](./书源整理.md) | 主流书源那套的分类说明 |

两个 APK 用的是同一个签名（`legado-collect/apk/legado-built.keystore`），
所以**可以先装一个、再直接覆盖安装另一个**，不用卸载。

## 两个内置版有什么区别

| | 主流版 | 成人向版 |
| --- | --- | --- |
| 内置书源 | 1944 条（精品库里按规则完整度 + 更新时间排序取前段） | 2323 条（成人向全量） |
| 体积 | 17.8 MB | 17.1 MB |
| 内置数据 | 18.0 MB | 13.8 MB |
| 适合 | 分享给任何人 | 自己用 |

主流版没有把 19301 条全塞进去——90 MB 的内置 JSON 首次启动必然 OOM（阅读堆上限 256 MB，
社区实测 21 MB 是安全线），所以按质量排序取了前 18 MB。**完整 19301 条在 `legado-collect/out/`**，
需要的话按目录手动导入即可。

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
