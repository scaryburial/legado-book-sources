#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把三分片可达性检测结果合并回来：
  1. index.csv 增加"可达性"列
  2. 新增 50-实测可达 目录：规则完整 + 非站群模板 + 实测有响应
  3. 更新 stats.json / analysis.json 里的可达性统计
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
ALIVE = OUT / "alive"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TYPE_NAMES = {0: "文本小说", 1: "有声听书", 2: "漫画图源", 3: "文件网盘", 4: "视频影视"}
OK = {"可达", "有响应(拦截)"}


def load_status() -> dict:
    status = {}
    for f in sorted(ALIVE.glob("可达性_*.csv")):
        with f.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                # 复检结果文件名排序在后，直接覆盖首轮结果
                status[row["地址"].strip()] = (row["状态"], row["HTTP"])
    return status


def main() -> int:
    status = load_status()
    parts = sorted((OUT / "00-全量去重").glob("part*.json"))
    items = []
    for p in parts:
        items.extend(json.loads(p.read_text(encoding="utf-8")))

    # ---- 1. index.csv 补列 ----
    idx = OUT / "index.csv"
    rows = []
    with idx.open("r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        header = header + ["可达性"]
        for r in rd:
            st = status.get(r[-1].strip(), ("未检测", ""))
            rows.append(r + [st[0]])
    with idx.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)

    # ---- 2. 实测可达包 ----
    def is_ok(it):
        st = status.get(str(it.get("bookSourceUrl") or "").strip(), ("未检测", ""))[0]
        return st in OK

    def quality(it):
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

    live = [it for it in items if is_ok(it) and quality(it) >= 6]
    live.sort(key=lambda it: (-quality(it), str(it.get("bookSourceName") or "")))

    d = OUT / "50-实测可达"
    if d.exists():
        for f in d.glob("*"):
            f.unlink()
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(live), 500):
        n += 1
        (d / f"part{n:02d}.json").write_text(
            json.dumps(live[i:i + 500], ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 3. 更新统计 ----
    summary = Counter(st for st, _ in status.values())
    stats = json.loads((OUT / "stats.json").read_text(encoding="utf-8"))
    stats["alive"] = {
        "checked": len(status),
        "summary": dict(sorted(summary.items(), key=lambda kv: -kv[1])),
        "live_or_reachable": sum(v for k, v in summary.items() if k in OK),
        "live_rate": round(sum(v for k, v in summary.items() if k in OK) / max(1, len(status)) * 100, 1),
        "by_type_live": dict(Counter(
            TYPE_NAMES.get(it.get("bookSourceType", 0), str(it.get("bookSourceType")))
            for it in live)),
    }
    stats["manifest"].append({
        "dir": "50-实测可达",
        "desc": "规则完整（≥6 分）且本次实测域名有响应的源，按 500 条分片",
        "count": len(live),
        "parts": n,
    })
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats["alive"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
