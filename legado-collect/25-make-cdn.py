#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把三大分类打包成 CDN 用的单文件（每个 < 19MB，jsDelivr 单文件上限 20MB），
并生成一键导入链接。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FINAL = ROOT / "out-final"
CDN = ROOT.parent / "cat"
MAX = 17 * 1024 * 1024

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SLUG = {"小说": "Novel", "漫画": "Comic", "视频": "Video"}
REPO = "scaryburial/legado-book-sources"


def main() -> int:
    CDN.mkdir(exist_ok=True)
    for f in CDN.glob("*.json"):
        try:
            f.unlink()
        except OSError:
            pass

    links = []
    for cat, slug in SLUG.items():
        items = []
        for p in sorted((FINAL / cat).glob("part*.json")):
            items.extend(json.loads(p.read_text(encoding="utf-8")))
        if not items:
            print(f"{cat}: 0 条，跳过")
            continue

        chunks, cur, used = [], [], 0
        for bs in items:
            n = len(json.dumps(bs, ensure_ascii=False).encode("utf-8")) + 40
            if cur and used + n > MAX:
                chunks.append(cur)
                cur, used = [], 0
            cur.append(bs)
            used += n
        if cur:
            chunks.append(cur)

        for i, ch in enumerate(chunks, 1):
            name = f"{slug}.json" if len(chunks) == 1 else f"{slug}-{i}.json"
            (CDN / name).write_text(json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
            mb = (CDN / name).stat().st_size / 1024 / 1024
            raw = (f"https://cdn.jsdelivr.net/gh/{REPO}@master/cat/{name}")
            link = "legado://import/bookSource?src=" + __import__("urllib.parse", fromlist=["quote"]).quote(raw, safe="")
            links.append({"分类": cat, "文件": name, "条数": len(ch), "大小MB": round(mb, 1),
                          "直链": raw, "一键导入": link})
            print(f"{cat}: {name}  {len(ch)} 条  {mb:.1f} MB")

    (CDN / "links.json").write_text(json.dumps(links, ensure_ascii=False, indent=1), encoding="utf-8")
    doc = ["# 三大分类 · 一键导入链接", "",
           "> 只收录实测「可用」的书源。手机装好阅读 App 后点链接即可导入。", "",
           "| 分类 | 条数 | 大小 | 一键导入（手机点这个） | 网络导入直链 |",
           "| --- | ---: | ---: | --- | --- |"]
    for l in links:
        doc.append(f"| {l['分类']} | {l['条数']} | {l['大小MB']} MB | "
                   f"[点我导入]({l['一键导入']}) | `{l['直链']}` |")
    doc += ["", "## 说明", "",
            "- 分类口径：`bookSourceType` 0=小说、2=漫画、4=视频，再按名称关键词兜底纠错。",
            "- 全部经过实测：按书源自身的搜索地址发一次真实请求，只有返回正常页面的才保留。",
            "- 不可用的（超时/域名失效/页面不存在/连接被拦）一律没有收录。", ""]
    (ROOT.parent / "一键导入链接.md").write_text("\n".join(doc), encoding="utf-8")
    print("\n已写出 一键导入链接.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
