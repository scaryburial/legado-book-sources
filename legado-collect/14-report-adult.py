#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1) 把可达性检测结果并回 out-adult/index.csv，并生成 out-adult/50-实测可达
2) 生成《成人向书源整理.md》
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADULT = ROOT / "out-adult"
ALIVE = ADULT / "alive"
TOP = ROOT.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OK = {"可达", "有响应(拦截)"}
TYPE_NAMES = {0: "文本小说", 1: "有声听书", 2: "漫画图源", 3: "文件网盘", 4: "视频影视"}


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def quality(it: dict) -> int:
    s = 0
    if str(it.get("searchUrl") or "").strip():
        s += 2
    rt = it.get("ruleToc") if isinstance(it.get("ruleToc"), dict) else {}
    if str(rt.get("chapterList") or "").strip():
        s += 2
    rc = it.get("ruleContent") if isinstance(it.get("ruleContent"), dict) else {}
    if str(rc.get("content") or "").strip():
        s += 2
    rs = it.get("ruleSearch") if isinstance(it.get("ruleSearch"), dict) else {}
    if any(str(v).strip() for v in rs.values() if v):
        s += 1
    if str(it.get("exploreUrl") or "").strip():
        s += 1
    return s


def main() -> int:
    stats = json.loads((ADULT / "stats.json").read_text(encoding="utf-8"))

    # ---- 可达性 ----
    status = {}
    for f in sorted(ALIVE.glob("可达性_*.csv")):
        with f.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                status[row["地址"].strip()] = row["状态"]

    parts = sorted((ADULT / "00-全量去重").glob("part*.json"))
    items = []
    for p in parts:
        items.extend(json.loads(p.read_text(encoding="utf-8")))

    live = [it for it in items if status.get(str(it.get("bookSourceUrl") or "").strip()) in OK and quality(it) >= 6]
    live.sort(key=lambda it: (-quality(it), str(it.get("bookSourceName") or "")))
    d = ADULT / "50-实测可达"
    if d.exists():
        for f in d.glob("*"):
            f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(live), 500):
        n += 1
        (d / f"part{n:02d}.json").write_text(
            json.dumps(live[i:i + 500], ensure_ascii=False, indent=1), encoding="utf-8")

    if status:
        with (ADULT / "index.csv").open("r", encoding="utf-8-sig", newline="") as fh:
            rd = csv.reader(fh)
            header = next(rd) + ["可达性"]
            rows = [r + [status.get(r[-1].strip(), "未检测")] for r in rd]
        with (ADULT / "index.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)

        summary = Counter(status.values())
        live_n = sum(v for k, v in summary.items() if k in OK)
        stats["alive"] = {
            "checked": len(status),
            "summary": dict(sorted(summary.items(), key=lambda kv: -kv[1])),
            "live_or_reachable": live_n,
            "live_rate": round(live_n / max(1, len(status)) * 100, 1),
        }
        stats["manifest"].append({"dir": "50-实测可达",
                                  "desc": "规则完整且本次探测有响应", "count": len(live), "parts": n})
        stats["live_count"] = len(live)
        (ADULT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    m_rows = "\n".join(
        f"| `out-adult/{m['dir']}/` | {fmt(m['count'])} | {m['parts']} | {m['desc']} |"
        for m in stats["manifest"])
    sub_rows = "\n".join(f"| {k} | {fmt(v)} |" for k, v in stats["by_sub"].items())

    a = stats.get("alive", {})
    alive_rows = "\n".join(
        f"| {k} | {fmt(v)} | {v / max(1, a.get('checked', 1)) * 100:.1f}% |"
        for k, v in a.get("summary", {}).items())

    doc = f"""# 成人向书源整理（参考用）

> 整理时间：**{stats['date']}** ｜ 与主流那套完全分开存放
> 去重后 **{fmt(stats['count'])}** 条，同站合并后 **{fmt(stats['merged'])}** 条
> 产物目录：`legado-collect/out-adult/`

---

## 一、这是什么

主流程在合并时会给每条书源打标签，凡是命中成人向关键词
（小黄、成人、18禁、🔞、海棠、PO18、耽美、禁漫、r18、欲、刘备、福利、写真……）
的条目，**不进 `out/` 那套目录**，而是走这个独立的 `out-adult/` 目录树单独分类。

主流程判定数量：**{fmt(stats['count'])} 条**。

---

## 二、目录结构

| 目录 | 条数 | 分片数 | 说明 |
| --- | ---: | ---: | --- |
{m_rows}

配套文件：

| 文件 | 说明 |
| --- | --- |
| `out-adult/index.csv` | 明细表（名称/站点/细分/标签/规则完整度/最后更新/来源仓库/可达性） |
| `out-adult/stats.json` | 统计数字 |
| `out-adult/alive/` | 可达性检测原始结果 |

---

## 三、细分口径

先按内容形态切开，形态不明确的落进"成人小说文本"：

| 细分 | 条数 |
| --- | ---: |
{sub_rows}

判定优先级：漫画/图源 → 有声 → 视频 → 文件网盘 → 同人耽美（名称/分组含耽美、腐、BL、百合、同人、乙女）→ 轻小说二次元 → 其余为文本小说。

---

## 四、质量与可达性

- 规则完整（搜索 + 目录 + 正文都齐）且社区未标失效：**{fmt(stats['rule_complete'])} 条**
- 被原合集标注"搜索失效/发现失效"：**{fmt(stats['flagged_broken'])} 条**（在 `60-社区标记失效/`）
- 本次实测域名有响应：**{fmt(a.get('live_or_reachable', 0))} 条，占 {a.get('live_rate', 0)}%**
  （共探测 {fmt(a.get('checked', 0))} 条）

| 状态 | 条数 | 占比 |
| --- | ---: | ---: |
{alive_rows}

`50-实测可达/` 是"规则完整 + 本次探测有响应"的交集（{fmt(stats.get('live_count', 0))} 条），要省事就从这里挑。

---

## 五、导入方法

和主流那套一样：

1. 把 `part01.json` 之类传到手机 → 阅读 App → 我的 → 书源管理 → 右上角 → **本地导入**；
2. 一次别导太多，`01-同站合并/`（{fmt(stats['merged'])} 条）体积最小，适合直接上手机。

---

## 六、注意事项

1. **识别是关键词规则，不是人工审核**。会有两头错：叫"欲书阁"的未必真是成人站，
   不叫这些名字的成人站也可能漏在外面（主流那套里）。当参考用，别当权威分类。
2. 这类站点是**引流、马甲包、扣费、弹窗**的重灾区，比例明显高于主流的笔趣阁类站群。
   本次只做了域名可达性探测，**没有做内容审核，也不保证站点内容合法或安全**。
3. 书源规则跑的是 JS，等于别人的脚本在你 App 里执行。需要登录的源尤其别填常用密码。
4. 我不对这部分内容做筛选、推荐或内容转存，只做链接元数据的去重与归类。
5. 内容版权归原站与原作者，请自行确认使用场景的合法性。

---

## 七、复现

```powershell
cd C:\\Users\\Administrator\\Documents\\ChatGPT\\插件
python .\\legado-collect\\merge.py            # 会同时生成 out/ 和 out-adult/
pwsh -File .\\legado-collect\\run-alive-adult.ps1
python .\\legado-collect\\14-report-adult.py
```

分类规则在 `legado-collect/merge.py` 的 `ADULT_WORDS` 常量里，要调松紧直接改正则。
"""

    (TOP / "成人向书源整理.md").write_text(doc, encoding="utf-8")
    print(f"已生成 {TOP / '成人向书源整理.md'}   ({len(doc):,} 字符)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
