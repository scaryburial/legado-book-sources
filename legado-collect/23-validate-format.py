#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按官方 BookSource 实体校验所有产物 JSON 的格式是否正确。
校验项：JSON 合法性 / 必填字段 / 字段类型 / 类型枚举 / 规则子字段名 / 地址去重
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 官方实体字段（scalar）
SCALAR = {
    "bookSourceUrl": str, "bookSourceName": str, "bookSourceGroup": (str, type(None)),
    "bookSourceType": int, "bookUrlPattern": (str, type(None)), "customOrder": int,
    "enabled": bool, "enabledExplore": bool, "enabledCookieJar": (bool, type(None)),
    "jsLib": (str, type(None)), "concurrentRate": (str, type(None)), "header": (str, type(None)),
    "loginUrl": (str, type(None)), "loginUi": (str, type(None)), "loginCheckJs": (str, type(None)),
    "coverDecodeJs": (str, type(None)), "bookSourceComment": (str, type(None)),
    "variableComment": (str, type(None)), "lastUpdateTime": int, "respondTime": int,
    "weight": int, "exploreUrl": (str, type(None)), "exploreScreen": (str, type(None)),
    "searchUrl": (str, type(None)), "ruleFindUrl": (str, type(None)),
}
RULE_FIELDS = {"ruleSearch": "SearchRule", "ruleExplore": "ExploreRule",
               "ruleBookInfo": "BookInfoRule", "ruleToc": "TocRule",
               "ruleContent": "ContentRule", "ruleReview": "ReviewRule"}
RULE_KEYS = {
    "SearchRule": {"bookList", "name", "author", "kind", "wordCount", "lastChapter",
                   "intro", "coverUrl", "bookUrl", "checkKeyWord"},
    "ExploreRule": {"bookList", "name", "author", "kind", "wordCount", "lastChapter",
                    "intro", "coverUrl", "bookUrl"},
    "BookInfoRule": {"init", "name", "author", "intro", "kind", "lastChapter", "updateTime",
                     "coverUrl", "tocUrl", "wordCount", "canReName", "downloadUrls"},
    "TocRule": {"preUpdateJs", "chapterList", "chapterName", "chapterUrl", "formatJs",
                "isVolume", "isVip", "isPay", "updateTime", "nextTocUrl"},
    "ContentRule": {"content", "subContent", "title", "nextContentUrl", "webJs",
                    "sourceRegex", "replaceRegex", "imageStyle", "imageDecode",
                    "payAction", "callBackJs"},
    "ReviewRule": {"reviewUrl", "avatarRule", "contentRule", "postTimeRule", "nameRule",
                   "totalScoreRule", "scoreRule", "reviewQuoteUrl"},
}


def validate_entries(arr, label, problems, warns):
    if not isinstance(arr, list):
        problems.append(f"{label}: 顶层不是 JSON 数组")
        return Counter()

    urls, stat = Counter(), Counter()
    for i, bs in enumerate(arr):
        tag = f"{label}[{i}]"
        if not isinstance(bs, dict):
            problems.append(f"{tag}: 不是对象")
            continue
        for k, t in SCALAR.items():
            if k in bs and bs[k] is not None and not isinstance(bs[k], t):
                # bool 是 int 的子类，单独排除
                if not (t is int and isinstance(bs[k], bool)):
                    problems.append(f"{tag}: {k} 类型应为 {t}，实际 {type(bs[k]).__name__}")
        if not str(bs.get("bookSourceName") or "").strip():
            problems.append(f"{tag}: bookSourceName 为空")
        u = str(bs.get("bookSourceUrl") or "").strip()
        if not u:
            problems.append(f"{tag}: bookSourceUrl 为空")
        elif not re.match(r"^https?://", u, re.I):
            warns.append(f"{tag}: bookSourceUrl 不是 http(s):// -> {u[:60]}")
        urls[u] += 1
        t = bs.get("bookSourceType", 0)
        if t not in (0, 1, 2, 3, 4):
            problems.append(f"{tag}: bookSourceType={t} 超出 0-4")
        stat[str(t)] += 1
        for f, rule in RULE_FIELDS.items():
            v = bs.get(f)
            if v is None:
                continue
            if not isinstance(v, dict):
                problems.append(f"{tag}: {f} 应为对象，实际 {type(v).__name__}")
                continue
            unknown = set(v) - RULE_KEYS[rule]
            if unknown:
                warns.append(f"{tag}: {f} 含未知子字段 {sorted(unknown)}")
    dup = {u: c for u, c in urls.items() if c > 1}
    if dup:
        problems.append(f"{label}: 有 {len(dup)} 个重复 bookSourceUrl（导入会互相覆盖）")
    return stat


def main() -> int:
    problems, warns = [], []
    files = 0
    total = 0
    type_stat = Counter()

    skip = {"links.json", "stats.json"}
    targets = sorted(ROOT.glob("out*/**/part*.json")) \
        + [p for p in sorted((ROOT.parent / "cat").glob("*.json")) if p.name not in skip] + [
        ROOT.parent / "adult" / "Adult-BookSources-2323.json",
        ROOT.parent / "main" / "Main-BookSources-1944.json",
        ROOT.parent / "main" / "ReplaceRules-23.json",
    ]
    for p in targets:
        if not p.exists():
            continue
        try:
            arr = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"{p.name}: JSON 解析失败 {e}")
            continue
        files += 1
        if p.name.startswith("ReplaceRules"):
            for i, r in enumerate(arr):
                if not isinstance(r, dict) or "pattern" not in r or "name" not in r:
                    problems.append(f"ReplaceRules[{i}]: 缺 pattern/name")
            print(f"[规则] {p.name}: {len(arr)} 条  格式 OK")
            continue
        total += len(arr)
        type_stat.update(validate_entries(arr, f"{p.parent.name}/{p.name}", problems, warns))
        print(f"[书源] {p.relative_to(ROOT.parent)}: {len(arr)} 条")

    # APK 内置数据
    for apk in (ROOT / "apk" / "legado-adult-built.apk", ROOT / "apk" / "legado-main-built.apk"):
        if not apk.exists():
            continue
        with zipfile.ZipFile(apk) as z:
            arr = json.loads(z.read("assets/defaultData/bookSources.json").decode("utf-8"))
            validate_entries(arr, f"{apk.name}:bookSources.json", problems, warns)
            print(f"[APK ] {apk.name}: 内置 {len(arr)} 条")
            rules = json.loads(z.read("assets/defaultData/replaceRule.json").decode("utf-8"))
            print(f"[APK ] {apk.name}: 内置规则 {len(rules)} 条")

    print()
    print(f"校验文件数: {files}   书源条目合计: {total}")
    print(f"类型分布: {dict(type_stat)}")
    print(f"错误: {len(problems)}   警告: {len(warns)}")
    for x in problems[:25]:
        print("  [错误]", x)
    for x in warns[:15]:
        print("  [警告]", x)
    (ROOT / "out-live").mkdir(exist_ok=True)
    (ROOT / "out-live" / "format-report.json").write_text(
        json.dumps({"files": files, "entries": total, "type_dist": dict(type_stat),
                    "errors": problems[:500], "warnings": warns[:500],
                    "error_count": len(problems), "warning_count": len(warns)},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
