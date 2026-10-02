#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产出写报告要用的统计数据：分组分布、站点 Top、仓库贡献（带 star）。"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TYPE_NAMES = {0: "文本小说", 1: "有声听书", 2: "漫画图源", 3: "文件网盘", 4: "视频影视"}


def main() -> int:
    meta = {}
    p = RAW / "all-repos.json"
    if p.exists():
        for r in json.loads(p.read_text(encoding="utf-8")):
            meta[r["repo"]] = r

    items = []
    for part in sorted((OUT / "00-全量去重").glob("part*.json")):
        items.extend(json.loads(part.read_text(encoding="utf-8")))

    groups = Counter()
    for it in items:
        g = str(it.get("bookSourceGroup") or "").strip()
        for piece in re.split(r"[,，;；/|｜\s]+", g):
            piece = piece.strip()
            if piece and len(piece) <= 20:
                groups[piece] += 1

    hosts = Counter(str(it.get("bookSourceUrl") or "").split("#")[0].split("//")[-1].split("/")[0].lower()
                    for it in items)

    repo_counts = Counter()
    for it in items:
        for s in json.loads("[]") if False else []:
            pass
    for part in sorted((OUT / "00-全量去重").glob("part*.json")):
        pass

    contrib = json.loads((OUT / "repo-contribution.json").read_text(encoding="utf-8"))

    dead_ish = [it for it in items if not str(it.get("searchUrl") or "").strip()]
    no_content = [it for it in items
                  if not str(((it.get("ruleContent") or {}) if isinstance(it.get("ruleContent"), dict) else {}).get("content") or "").strip()]

    out = {
        "count": len(items),
        "top_groups": groups.most_common(40),
        "top_hosts": hosts.most_common(30),
        "repo_contrib": [
            {
                "repo": r,
                "raw_entries": n,
                "stars": (meta.get(r) or {}).get("stars", ""),
                "pushed": (meta.get(r) or {}).get("pushed", ""),
                "url": (meta.get(r) or {}).get("url", ""),
            }
            for r, n in sorted(contrib.items(), key=lambda kv: -kv[1])
        ],
        "no_search_url": len(dead_ish),
        "no_content_rule": len(no_content),
        "type_dist": dict(Counter(TYPE_NAMES.get(it.get("bookSourceType", 0), it.get("bookSourceType")) for it in items)),
    }
    (OUT / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("top_groups", "top_hosts", "repo_contrib")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
