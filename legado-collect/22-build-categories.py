#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按测试结果生成最终三大分类：小说 / 漫画 / 视频
- 只收测试状态为「可用」的源
- 分类依据 bookSourceType：0=小说 2=漫画 4=视频
- 输出到 out-final/{小说,漫画,视频}/partNN.json（每条都是清洗后的规范格式）
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "out-live"
FINAL = ROOT / "out-final"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CATS = {"0": "小说", "2": "漫画", "4": "视频"}
CHUNK = 500

# 名字/分组里的兜底关键词（有些源类型标错）
VIDEO_RE = re.compile(r"视频|影视|电影|短剧|剧场|影院|TV|tvbox")
COMIC_RE = re.compile(r"漫画|漫畫|图源|manhua|manga|comic|动漫|anime|dmzj", re.I)


def category_of(bs: dict) -> str:
    t = str(bs.get("bookSourceType", 0))
    blob = f"{bs.get('bookSourceName') or ''} {bs.get('bookSourceGroup') or ''}"
    if t == "4" or VIDEO_RE.search(blob):
        return "视频"
    if t == "2" or COMIC_RE.search(blob):
        return "漫画"
    return "小说"


def quality(bs: dict) -> int:
    s = 0
    if str(bs.get("searchUrl") or "").strip():
        s += 2
    rt = bs.get("ruleToc") if isinstance(bs.get("ruleToc"), dict) else {}
    if str(rt.get("chapterList") or "").strip():
        s += 2
    rc = bs.get("ruleContent") if isinstance(bs.get("ruleContent"), dict) else {}
    if str(rc.get("content") or "").strip():
        s += 2
    rs = bs.get("ruleSearch") if isinstance(bs.get("ruleSearch"), dict) else {}
    if any(str(v).strip() for v in rs.values() if v):
        s += 1
    if str(bs.get("exploreUrl") or "").strip():
        s += 1
    return s


def load_sources(scope: str) -> dict:
    """当前（已清洗）的全部书源，按地址索引"""
    pool = {}
    dirs = [ROOT / "out-adult" / "00-全量去重"]
    if scope == "all":
        dirs.insert(0, ROOT / "out" / "00-全量去重")
    for d in dirs:
        for p in sorted(d.glob("part*.json")):
            for bs in json.loads(p.read_text(encoding="utf-8")):
                pool[str(bs.get("bookSourceUrl"))] = bs
    return pool


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("adult", "all"), default="adult",
                    help="adult=只要成人向（默认），all=全部")
    args = ap.parse_args()

    pool = load_sources(args.scope)
    print(f"书源池（scope={args.scope}）: {len(pool)}")

    rows = []
    for f in sorted(LIVE.glob("test-*.csv")):
        if f.stem.endswith("smoke"):
            continue
        with f.open("r", encoding="utf-8-sig", newline="") as fh:
            rows.extend(list(csv.DictReader(fh)))
    print(f"测试记录: {len(rows)}")

    stat = Counter()
    final = {c: [] for c in CATS.values()}
    seen = set()
    for r in rows:
        st = r.get("状态", "")
        stat[st] += 1
        if st != "可用":
            continue
        url = r.get("地址", "").strip()
        if not url or url in seen:
            continue
        if args.scope == "adult" and r.get("成人向", "") != "1":
            continue
        bs = pool.get(url)
        if not bs:
            continue
        seen.add(url)
        final[category_of(bs)].append(bs)

    if FINAL.exists():
        for f in sorted(FINAL.rglob("*"), reverse=True):
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass
            elif f.is_dir():
                try:
                    f.rmdir()
                except OSError:
                    pass
    manifest = []
    for cat, items in final.items():
        items.sort(key=lambda b: (-quality(b), str(b.get("bookSourceName") or "")))
        d = FINAL / cat
        d.mkdir(parents=True, exist_ok=True)
        n = 0
        for i in range(0, len(items), CHUNK):
            n += 1
            (d / f"part{n:02d}.json").write_text(
                json.dumps(items[i:i + CHUNK], ensure_ascii=False, indent=1), encoding="utf-8")
        manifest.append({"分类": cat, "条数": len(items), "分片": n})
        print(f"  {cat}: {len(items)} 条 / {n} 个分片")

    (FINAL / "stats.json").write_text(json.dumps(
        {"测试记录": len(rows), "状态分布": dict(stat.most_common()),
         "分类": manifest,
         "范围": "成人向" if args.scope == "adult" else "全部",
         "说明": "只收录实测「可用」的书源；分类口径 bookSourceType 0=小说 2=漫画 4=视频"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(dict(stat.most_common()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
