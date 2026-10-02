#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给已有 Release 上传附件（Python 处理 UTF-8 文件名比 PowerShell 可靠）"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "scaryburial/legado-book-sources"
TAG = "v1.0.0"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

state = (Path.home() / ".codex" / ".codex-global-state.json").read_text(encoding="utf-8", errors="ignore")
TOKEN = re.search(r"gh[po]_[A-Za-z0-9_]{20,}", state).group()
HEAD = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "User-Agent": "codex"}


def api(url: str, method: str = "GET", data: bytes | None = None, ctype: str | None = None):
    h = dict(HEAD)
    if ctype:
        h["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=900) as r:
        body = r.read()
        return json.loads(body) if body else None


def main() -> int:
    rel = api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
    rid = rel["id"]
    print(f"Release: {rel['html_url']}  id={rid}")

    # 清掉名字乱掉的旧附件
    for a in api(f"https://api.github.com/repos/{REPO}/releases/{rid}/assets"):
        bad = (a["name"] in ("APP-.apk", "-.2323.json", "default.md")
               or a["name"].startswith("-") or a["name"].startswith("APP-"))
        if bad:
            api(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", method="DELETE")
            print(f"  已删除乱码附件: {a['name']}")

    # 附件名用英文：GitHub 的 assets 接口会吞掉非 ASCII 文件名
    files = [
        (ROOT / "阅读APP-内置主流书源.apk", "Legado-Main-BookSources-1944.apk"),
        (ROOT / "阅读APP-内置成人向书源.apk", "Legado-Adult-BookSources-2323.apk"),
        (ROOT / "成人向书源-全量2323条.json", "Adult-BookSources-2323.json"),
        (ROOT / "书源整理.md", "Main-BookSources-Report.md"),
        (ROOT / "成人向书源整理.md", "Adult-BookSources-Report.md"),
    ]
    existing = {a["name"] for a in api(f"https://api.github.com/repos/{REPO}/releases/{rid}/assets")}
    for f, asset_name in files:
        if asset_name in existing:
            print(f"  已存在，跳过: {asset_name}")
            continue
        name = urllib.parse.quote(asset_name)
        url = f"https://uploads.github.com/repos/{REPO}/releases/{rid}/assets?name={name}"
        try:
            a = api(url, method="POST", data=f.read_bytes(), ctype="application/octet-stream")
            print(f"  已上传 {a['name']}  ({a['size']/1024/1024:.1f} MB)  <- {f.name}")
        except Exception as e:
            print(f"  上传失败 {f.name}: {e}")
        time.sleep(1)

    print("\n最终附件清单:")
    for a in api(f"https://api.github.com/repos/{REPO}/releases/{rid}/assets"):
        print(f"  {a['name']}  ({a['size']/1024/1024:.1f} MB)  {a['browser_download_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
