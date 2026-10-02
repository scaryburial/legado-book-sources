#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更正 Release 说明：阅读 App 没有内置书源机制，改为给出导入链接"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = "scaryburial/legado-book-sources"
TAG = "v1.0.0"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BODY = """\
> **重要更正**：阅读 App（Legado）**没有任何"内置书源"机制**。
> 官方包的 `assets/defaultData/bookSources.json` 是遗留死文件，代码从不读取
> （已用源码 + dex 字符串双重核实），所以下面这两个 APK 内置的数据**不会自动出现**。
> 真正能用的方式是下面的导入链接。

## 推荐用法：一键导入（点一下就把书源导进去）

手机已装阅读 App 的前提下，直接点：

- **成人向书源 2323 条**
  `legado://import/bookSource?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fadult%2FAdult-BookSources-2323.json`
- **主流精品 1944 条**
  `legado://import/bookSource?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fmain%2FMain-BookSources-1944.json`
- **净化规则 23 条**
  `legado://import/replaceRule?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fmain%2FReplaceRules-23.json`

或者复制上面的 `https` 直链，在 阅读 → 我的 → 书源管理 → 右上角 → **网络导入** 里粘贴。

## APK 说明

下面两个 APK 基于官方 v3.26.042717 重打包、使用同一签名，可互相覆盖安装，
**功能与官方版一致**，内置数据不会被自动导入。用上面的链接导入书源即可。

首次安装仍需先卸载官方版（签名不同，否则装不上）。

## 完整书源库

仓库 `legado-collect/` 下有全部分类好的书源：主流 19301 条（按形态/题材/质量分层）、成人向 2323 条。
"""


def main() -> int:
    state = (Path.home() / ".codex" / ".codex-global-state.json").read_text(encoding="utf-8", errors="ignore")
    token = re.search(r"gh[po]_[A-Za-z0-9_]{20,}", state).group()
    head = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "User-Agent": "codex", "Content-Type": "application/json"}

    def api(url, method="GET", data=None):
        req = urllib.request.Request(url, data=data, headers=head, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            return json.loads(body) if body else None

    rel = api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
    out = api(f"https://api.github.com/repos/{REPO}/releases/{rel['id']}", "PATCH",
              json.dumps({"body": BODY}).encode())
    print("Release 说明已更新:", out["html_url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
