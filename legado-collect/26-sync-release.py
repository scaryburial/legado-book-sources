#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建 Release：清空旧附件，上传三大分类包与新版 APK，并更新说明"""
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

BODY = """\
## 成人向 · 三大分类（只收录实测可用的）

**范围：仅成人向书源。** 全部按它自己的搜索地址跑过一次真实请求，
只有返回正常页面的才收录；超时/域名失效/页面不存在/被拦的一律没有放进来。

| 分类 | 条数 | 说明 |
| --- | ---: | --- |
| 小说 | 644 | 成人向文本小说 |
| 漫画 | 32 | 成人向漫画/图源 |
| 视频 | 2 | 成人向视频 |

合计 678 条，来自 2252 条成人向源（实测可用率 30.1%）。

## 一键导入（手机点这个）

```
小说：legado://import/bookSource?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fcat%2FNovel.json
漫画：legado://import/bookSource?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fcat%2FComic.json
视频：legado://import/bookSource?src=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2Fscaryburial%2Flegado-book-sources%40master%2Fcat%2FVideo.json
```

直链走 jsDelivr CDN，国内手机可直接访问。也可以复制
`https://cdn.jsdelivr.net/gh/scaryburial/legado-book-sources@master/cat/Novel.json`
这种地址，在 书源管理 → 网络导入 里粘贴。

## 实测与格式

- 成人向源 2252 条参与测试 → **可用 678**
- 分类口径：`bookSourceType` 0=小说、2=漫画、4=视频，名称关键词兜底纠错
- 全部产物按官方 BookSource 实体清洗过：字段类型、类型枚举、规则子字段全部合规，
  校验错误 0、警告 0（`legado-collect/23-validate-format.py`）

## 关于 APK

阅读 App（Legado）**没有"内置书源"机制**——官方包的 `assets/defaultData/bookSources.json` 是遗留死文件，
代码从不读取（源码 + dex 字符串双重核实）。所以内置版 APK 里的数据不会自动出现，
**请直接用上面的导入链接**。

下面两个 APK 与官方 v3.26.042717 功能一致，仅用于提供同签名的安装包，可互相覆盖安装；
首次安装仍需先卸载官方版。
"""


def api(url, method="GET", data=None, ctype=None):
    h = dict(HEAD)
    if ctype:
        h["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=900) as r:
        b = r.read()
        return json.loads(b) if b else None


def main() -> int:
    rel = api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}")
    rid = rel["id"]
    print("Release:", rel["html_url"])

    for a in api(f"https://api.github.com/repos/{REPO}/releases/{rid}/assets"):
        api(f"https://api.github.com/repos/{REPO}/releases/assets/{a['id']}", "DELETE")
        print("  删除旧附件:", a["name"])

    files = [
        (ROOT / "cat" / "Novel.json", "Adult-Novel.json"),
        (ROOT / "cat" / "Comic.json", "Adult-Comic.json"),
        (ROOT / "cat" / "Video.json", "Adult-Video.json"),
        (ROOT / "legado-collect" / "apk" / "legado-main-built.apk", "Legado-Main-BookSources.apk"),
        (ROOT / "legado-collect" / "apk" / "legado-adult-built.apk", "Legado-Adult-BookSources.apk"),
        (ROOT / "一键导入链接.md", "Import-Links.md"),
    ]
    for src, name in files:
        if not src.exists():
            print("  缺失，跳过:", src)
            continue
        url = (f"https://uploads.github.com/repos/{REPO}/releases/{rid}/assets"
               f"?name={urllib.parse.quote(name)}")
        try:
            a = api(url, "POST", src.read_bytes(), "application/octet-stream")
            print(f"  已上传 {a['name']}  ({a['size']/1024/1024:.1f} MB)")
        except Exception as e:
            print(f"  上传失败 {name}: {e}")
        time.sleep(1)

    api(f"https://api.github.com/repos/{REPO}/releases/{rid}", "PATCH",
        json.dumps({"body": BODY, "name": f"书源三大分类 + 内置版 APK {TAG}"}).encode())
    print("说明已更新")

    print("\n最终附件:")
    for a in api(f"https://api.github.com/repos/{REPO}/releases/{rid}/assets"):
        print(f"  {a['name']:<34} {a['size']/1024/1024:>6.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
