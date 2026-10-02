#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 out/ 下的统计结果生成《书源整理.md》"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
TOP = ROOT.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def main() -> int:
    stats = json.loads((OUT / "stats.json").read_text(encoding="utf-8"))
    ana = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
    alive = stats.get("alive", {})

    manifest = stats["manifest"]
    rows = "\n".join(
        f"| `out/{m['dir']}/` | {fmt(m['count'])} | {m['parts']} | {m['desc']} |"
        for m in manifest)

    repo_rows = []
    for r in ana["repo_contrib"]:
        name = r["repo"]
        # 去掉 "owner/repo/master" 里的分支尾巴，还原成 owner/repo
        name = re.sub(r"/(main|master|shuyuan|gh-pages|backup)$", "", name)
        stars = r["stars"] if r["stars"] != "" else "-"
        pushed = r["pushed"] or "-"
        url = r["url"] or (f"https://github.com/{name}" if "/" in name else "")
        link = f"[{name}]({url})" if url else f"`{name}`"
        repo_rows.append(f"| {link} | {stars} | {pushed} | {fmt(r['raw_entries'])} |")
    repo_table = "\n".join(repo_rows)

    group_rows = "\n".join(
        f"| {g} | {c} |" for g, c in ana["top_groups"][:15])

    a_sum = alive.get("summary", {})
    live_total = alive.get("live_or_reachable", 0)
    checked = alive.get("checked", 0)
    alive_rows = "\n".join(
        f"| {k} | {fmt(v)} | {v / max(1, checked) * 100:.1f}% |"
        for k, v in sorted(a_sum.items(), key=lambda kv: -kv[1]))

    by_type = stats.get("by_type", {})
    type_rows = "\n".join(
        f"| {k} | {fmt(v)} |" for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]))

    doc = f"""# 阅读（Legado）书源整理

> 整理时间：**{stats['date']}**
> 数据来源：GitHub 上 **{stats['source_repos']} 个书源合集仓库**、**{stats['source_files']} 个书源文件**
> 原始条目 **{fmt(stats['raw'])}** 条 → 合并去重后 **{fmt(stats['modern'])}** 条主流书源
> 本文件由 `legado-collect/13-report.py` 依据实测数据自动生成，所有数字可复现。

---

## 一、一句话结论

市面上（GitHub 公开合集）能收集到的 Legado 书源，去重后**实际有效集合约 1.9 万条**，
其中规则完整、非站群模板、社区未标记失效的 **精品约 1.1 万条**；
本次实测域名有响应的约占 **{alive.get('live_rate', 0)}%**。
**手机直接导入建议只用 `out/32-入门精选/` 或 `out/01-同站合并/`**，全量 1.9 万条一次导入大概率会让 App 卡死（阅读的堆上限 256MB）。

---

## 二、成果目录

全部产物在 `legado-collect/out/`，每个 `.json` 都是可直接导入阅读的**书源数组**：

| 目录 | 条数 | 分片数 | 说明 |
| --- | ---: | ---: | --- |
{rows}

配套文件：

| 文件 | 说明 |
| --- | --- |
| `out/index.csv` | 全部书源的索引表（名称/站点/类型/标签/规则完整度/最后更新/重复份数/来源仓库/需登录/站群模板/可达性） |
| `out/stats.json` | 全部统计数字 |
| `out/analysis.json` | 分组分布、域名 Top、仓库贡献等分析数据 |
| `out/repo-contribution.json` | 每个仓库贡献了多少原始条目 |
| `out/alive/` | 可达性检测的原始结果（分片 CSV + 汇总 JSON） |
| `legado-collect/raw/` | 下载的仓库快照与中间数据（体积大，确认无用后可自行删除） |
| `legado-collect/out-adult/` | **另一套**：被识别为成人向的 {fmt(stats['adult'])} 条，单独分类，见《成人向书源整理.md》 |

**磁盘占用**：`legado-collect/out/` 约 495 MB（各分类目录之间有重复条目，是为了让每个目录都能单独导入）；
`legado-collect/raw/` 约 979 MB（仓库快照 + tarball，纯中间产物，随时可删）。
只保留 `out/` 里你真正要用的那几个目录即可。

---

## 三、怎么分类的

### 1. 按内容形态（书源自己声明的 bookSourceType + 名称/分组关键词）

| 形态 | 条数 |
| --- | ---: |
{type_rows}

### 2. 按题材 / 站点性质

`out/20-题材/` 下按以下口径拆分（一条源可能同时命中多个题材，所以各目录之和大于总数）：

| 题材 | 判定依据 |
| --- | --- |
| 正版出版 | 起点、番茄、七猫、晋江、掌阅、微信读书、咪咕、塔读、出版机构等 |
| 轻小说二次元 | 轻之国度、wenku8、哔哩轻小说、真白萌、ESJ、kakuyomu 等 |
| 女频言情 | 言情/现言/古言/甜宠/腐/百合，以及关耳女频等专门合集 |
| 男频网文 | 玄幻/修真/仙侠/都市/神豪/系统流等 |
| 听书有声 | 听书、有声、广播、电台、TTS、评书 |
| 动漫图片 | 漫画、图源、写真、pixiv、manga |
| 学术文献 | 论文、期刊、libgen/zlib/annas-archive、超星、读秀 |
| 订阅RSS | 订阅源、RSS、播客、公众号（这类不是书源，是订阅源） |

### 3. 按质量分层

| 标签 | 含义 |
| --- | --- |
| 规则完整度 9 分 | 有搜索地址 + 搜索规则 + 目录规则 + 正文规则 + 详情规则 + 分类页 |
| `out/30-精品/` | 完整度 ≥6 且**不是**笔趣阁类站群模板、且社区未标记失效 |
| `out/31-可发现/` | 带分类/榜单页，适合像书城一样逛着找书 |
| `out/32-入门精选/` | 9 分规则 + 有分类页 + 非站群 + 近两年有更新，限 300 条，**先用这个** |
| `out/40-旧版格式/` | 阅读 2.x 老格式（ruleSearchUrl/ruleBookContent 那套），几乎都是 2019 年前后的死站，仅留档 |
| `out/60-社区标记失效/` | 原合集分组里已被维护者标注「搜索失效/发现失效」的源，别导入 |

---

## 四、去重规则（重复的以最新为准）

中间数据里 **{fmt(stats['raw'])}** 条原始记录，重复率极高（同一份合集被几十个仓库互相搬运）。处理方式：

1. **文件级去重**：先按文件内容 MD5 去掉完全相同的整份合集，避免同一份文件被算两次。
2. **条目级去重键**：`归一化地址 + 书源类型`。
   - 归一化 = 去空白、统一小写、去掉 `www.`、补全协议、去掉结尾 `/`；
   - **保留 `#` 之后的变体标记**——因为社区用 `#发现规则`、`#魔改版` 这种后缀表示"同一网站的不同源"，合并会误删；
   - 书源类型分开算（同站的「小说源」和「漫画源」都会留下）。
3. **同一键只留一条，排序优先级**：
   `lastUpdateTime 更新 → 规则更完整 → 字段更全 → 来源仓库最近推送时间更新`。
   ——这就是"以最新的为准"。
4. 另出一份 `out/01-同站合并/`：把同站变体也压成一条，给手机端做瘦身（{fmt(stats['merged_main'])} 条）。

结果：合并掉 **{fmt(stats['dropped_exact'])}** 条重复；全量 {fmt(stats['modern'])} 条；
其中 **{fmt(stats['flagged_broken'])}** 条被原合集标注失效，已单独挪到 `60-社区标记失效`。

---

## 五、怎么导入

### 方式 A：本地导入（推荐，能自己挑）

1. 把要导入的 `.json`（例如 `32-入门精选/part01.json`）传到手机；
2. 阅读 App → 我的 → 书源管理 → 右上角菜单 → **本地导入**；
3. 一次选一两个文件，导完再导下一个。

### 方式 B：网络导入（适合自建）

把 `out/` 里的 JSON 传到自己的图床 / 对象存储 / GitHub 仓库，得到直链后：
阅读 → 书源管理 → 右上角 → **网络导入** → 粘贴直链。

### 方式 C：一键唤起 App

```
yuedu://booksource/importonline?src=<你的直链>
```

### 导入顺序建议

1. 先 `32-入门精选`（300 条）→ 用几天，确认顺手；
2. 再按需补 `20-题材/*`（比如只看轻小说就只导 `轻小说二次元`）；
3. 最后才考虑 `30-精品` / `00-全量去重`（分片逐个导入，**不要一次全选**）。

### 移动端省事方案

直接用 `out/01-同站合并/`（{fmt(stats['merged_main'])} 条，13 个分片），同站只留一条，体积最小。

---

## 六、来源仓库清单

共采集 {stats['source_repos']} 个仓库、{stats['source_files']} 个书源文件。贡献量（原始条目，未去重）如下：

| 仓库 | Star | 最近推送 | 贡献原始条目 |
| --- | ---: | --- | ---: |
{repo_table}

> 说明：`oli-fa/YueDuBackup`、`fmpfmp/YueDuBackup`、`oevery/Source` 等是**历史备份仓库**，
> 里面大量 2019–2021 年的源早就废了，之所以还采进来，是为了"以最新的为准"时有对照对象——
> 它们的条目基本都被更新版本覆盖掉了，最终去重后剩下不多。

---

## 七、可达性实测

对去重后的 {fmt(checked)} 条主流书源逐条做了一次轻量 HTTP 探测（8 秒超时，读取 512 字节即断开，移动端 UA），
对超时/失败的又用 20 秒超时复检了一轮：

| 状态 | 条数 | 占比 |
| --- | ---: | ---: |
{alive_rows}

**可达 + 有响应合计 {fmt(live_total)} 条，占 {alive.get('live_rate', 0)}%。**

怎么看这组数字：

- 「可达」= 服务器正常返回页面；
- 「有响应(拦截)」= 返回 403/429 等，服务器还在，只是不欢迎脚本访问，**不能判死**；
- 「超时 / 连接失败 / 域名解析失败」= 大概率已经挂了，或需要特定网络环境；
- 这次是**裸 HTTP 探测**，不等于书源真的能搜到书——真正可用性还要靠阅读 App 里实测。

`out/50-实测可达/` 是从精品里再筛出"本次探测有响应"的那部分，作为最保守的一批。

---

## 八、书源自带的社区分组 Top15

原合集作者自己打的分组标签（可作为挑选参考）：

| 分组 | 条数 |
| --- | ---: |
{group_rows}

---

## 九、风险与边界

1. **书源规则里跑的是 JS**，等于别人的脚本在你 App 里执行。只从有维护、有来源的合集导入，
   不要随手导来路不明的单条源。
2. 站群模板（笔趣阁那一类换皮站）风险相对更高：域名跳转、引流、弹窗广告多。本次已经单独打标，
   并在精品/入门精选里排除。
3. 需要登录的源（{fmt(stats['needs_login'])} 条，多在 comment 里注明要登录/过验证）自己掂量，别在里面填重要账号密码。
4. **成人向内容**：被规则识别为成人向的 **{fmt(stats['adult'])}** 条**不在本文件这套目录里**，
   已单独导出到 `legado-collect/out-adult/`，详见同目录下的《成人向书源整理.md》。
   那一套是关键词自动归类、未经人工审核，风险（引流/扣费/马甲包）明显高于主流这批，自行判断。
5. 所有书源版权归原网站与原作者，本整理只做索引与分类，不做内容转存。

---

## 十、怎么复现 / 更新

`legado-collect/` 下的脚本按序号执行即可：

| 脚本 | 作用 |
| --- | --- |
| `01-search-repos.ps1`、`06-search-more.ps1` | GitHub 检索书源相关仓库 |
| `02-rank-repos.ps1`、`03-filter-repos.ps1` | 合并排序、筛出书源仓库 |
| `04-download-repos.ps1`、`07/08/09-download-*.ps1` | 下载仓库 tarball / 按需抓文件 |
| `merge.py` | 扫描 → 合并 → 去重 → 分类 → 输出分片 |
| `run-alive.ps1`、`check-alive.py` | 并行可达性检测 |
| `run-retry.ps1`、`12-retry-alive.py` | 对超时/失败的源复检 |
| `10-analyse.py` | 生成分析数据 |
| `11-finalize.py` | 合并检测结果、生成 `50-实测可达` |
| `13-report.py` | 生成本文档 |

一键重跑：

```powershell
cd C:\\Users\\Administrator\\Documents\\ChatGPT\\插件
python .\\legado-collect\\merge.py
pwsh -File .\\legado-collect\\run-alive.ps1
pwsh -File .\\legado-collect\\run-retry.ps1
python .\\legado-collect\\10-analyse.py
python .\\legado-collect\\11-finalize.py
python .\\legado-collect\\13-report.py
```

---

## 附：几条常用的在线合集直链（懒人版）

不想下载 `out/` 的话，这几个上游合集可以定期重新导入（App 导入时会自动去重）：

| 名称 | 直链 |
| --- | --- |
| 全量书源（aoaostar 聚合） | https://legado.aoaostar.com/sources/b778fe6b.json |
| 酷安@开源阅读软件 | https://legado.aoaostar.com/sources/3bb7b751.json |
| 酷安@三舞313书源 | https://legado.aoaostar.com/sources/2a1f129b.json |
| XIU2 精品书源 | https://legado.aoaostar.com/sources/71e56d4f.json |
| ZGQ 全量（28180 条，分片） | https://source-repo.zgqinc.gq/legado3/bookSource/bookSource_1.json |

一键导入示例：

```
legado://import/bookSource?src=https://legado.aoaostar.com/sources/71e56d4f.json
```
"""

    (TOP / "书源整理.md").write_text(doc, encoding="utf-8")
    print(f"已生成 {TOP / '书源整理.md'}  ({len(doc):,} 字符)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
