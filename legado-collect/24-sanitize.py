#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把所有产物里的书源清洗成官方 BookSource 实体的规范格式：
- 只保留官方字段（丢掉其它 App/分支的私有字段，比如 ttsDice）
- bookSourceType 归一成 0/1/2/3/4 整数
- lastUpdateTime / respondTime / customOrder / weight 归一成整数
- 布尔字段归一成 true/false
- 规则字段必须是对象，是数组/字符串的一律置空（否则 Gson 解析会整包失败）
- 规则子字段只保留官方定义的键
- bookSourceUrl 不是 http(s) 网址的条目直接丢弃
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

STR_FIELDS = ["bookSourceUrl", "bookSourceName", "bookSourceGroup", "bookUrlPattern",
              "jsLib", "concurrentRate", "header", "loginUrl", "loginUi", "loginCheckJs",
              "coverDecodeJs", "bookSourceComment", "variableComment", "exploreUrl",
              "exploreScreen", "searchUrl"]
INT_FIELDS = ["bookSourceType", "customOrder", "lastUpdateTime", "respondTime", "weight"]
BOOL_FIELDS = ["enabled", "enabledExplore", "enabledCookieJar", "eventListener", "customButton"]
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
RULES = {"ruleSearch": "SearchRule", "ruleExplore": "ExploreRule",
         "ruleBookInfo": "BookInfoRule", "ruleToc": "TocRule",
         "ruleContent": "ContentRule", "ruleReview": "ReviewRule"}

TYPE_MAP = {"": 0, "TEXT": 0, "text": 0, "小说": 0, "文本": 0,
            "AUDIO": 1, "audio": 1, "音频": 1, "有声": 1,
            "IMAGE": 2, "image": 2, "漫画": 2, "图片": 2, "图源": 2,
            "FILE": 3, "file": 3, "文件": 3,
            "VIDEO": 4, "video": 4, "视频": 4}


def to_int(v, default=0):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        try:
            return int(v)
        except Exception:
            return default
    s = str(v or "").strip()
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else default


def to_bool(v, default=True):
    if isinstance(v, bool):
        return v
    s = str(v or "").strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return default


def clean_entry(bs: dict, stats: Counter):
    out = {}
    for f in STR_FIELDS:
        v = bs.get(f)
        if v is None:
            continue
        s = v if isinstance(v, str) else str(v)
        out[f] = s.strip() if f in ("bookSourceUrl", "bookSourceName") else s

    for f in INT_FIELDS:
        if f in bs:
            out[f] = to_int(bs.get(f))
        elif f in ("bookSourceType", "customOrder", "lastUpdateTime"):
            out[f] = 0
        elif f == "respondTime":
            out[f] = 180000
        elif f == "weight":
            out[f] = 0

    # 类型归一
    raw_type = bs.get("bookSourceType", 0)
    if isinstance(raw_type, str) and raw_type.strip() in TYPE_MAP:
        out["bookSourceType"] = TYPE_MAP[raw_type.strip()]
    else:
        out["bookSourceType"] = to_int(raw_type)
    if out["bookSourceType"] not in (0, 1, 2, 3, 4):
        out["bookSourceType"] = 0
        stats["type_fixed"] += 1

    for f in BOOL_FIELDS:
        if f in bs:
            out[f] = to_bool(bs.get(f))
        elif f in ("enabled", "enabledExplore"):
            out[f] = True

    for f, rule in RULES.items():
        v = bs.get(f)
        if v is None:
            continue
        if not isinstance(v, dict):
            stats[f"drop_{f}"] += 1
            continue
        keep = {}
        for k, val in v.items():
            if k not in RULE_KEYS[rule]:
                stats["drop_unknown_key"] += 1
                continue
            if val is None:
                continue
            keep[k] = val if isinstance(val, str) else str(val)
        if keep:
            out[f] = keep

    extra = set(bs) - set(out)
    stats["drop_other_fields"] += len(extra)
    return out


def write_json(path: Path, data, retries: int = 8):
    """先写临时文件再原子替换，避开 Windows 偶发的文件占用/Invalid argument"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=1)
    last = None
    for i in range(retries):
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
            return
        except OSError as e:
            last = e
            time.sleep(0.6 * (i + 1))
    raise last


def process(path: Path, stats: Counter):
    if not path.exists():
        return 0
    arr = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(arr, list):
        return 0
    cleaned, seen, dropped = [], set(), 0
    for bs in arr:
        if not isinstance(bs, dict):
            dropped += 1
            continue
        url = str(bs.get("bookSourceUrl") or "").strip()
        name = str(bs.get("bookSourceName") or "").strip()
        if not re.match(r"^https?://[^\s/]+\.", url, re.I) or not name:
            dropped += 1
            continue
        if url in seen:
            dropped += 1
            stats["dup_url"] += 1
            continue
        seen.add(url)
        cleaned.append(clean_entry(bs, stats))
    stats["dropped_entries"] += dropped
    write_json(path, cleaned)
    return len(cleaned)


def main() -> int:
    stats = Counter()
    total = 0
    files = 0
    targets = sorted(ROOT.glob("out*/**/part*.json")) + [
        ROOT.parent / "adult" / "Adult-BookSources-2323.json",
        ROOT.parent / "main" / "Main-BookSources-1944.json",
    ]
    for p in targets:
        n = process(p, stats)
        if n:
            files += 1
            total += n

    # ---- 跨分片去重：同一个目录下的所有 part*.json 视为一个导入包，网址必须唯一 ----
    for d in {p.parent for p in targets}:
        parts = sorted(d.glob("part*.json"))
        if len(parts) < 2:
            continue
        seen, kept = set(), []
        for p in parts:
            arr = json.loads(p.read_text(encoding="utf-8"))
            for bs in arr:
                u = str(bs.get("bookSourceUrl") or "").strip()
                if u in seen:
                    stats[f"cross_dup"] += 1
                    continue
                seen.add(u)
                kept.append(bs)
        total -= stats["cross_dup"]
        chunk = max(1, (len(kept) + len(parts) - 1) // len(parts))
        # 就地重写：多余的分片写成空数组，避免 unlink 被占用报错
        for i, p in enumerate(parts):
            seg = kept[i * chunk:(i + 1) * chunk]
            write_json(p, seg)
    print(f"清洗文件: {files}   保留条目: {total}")
    print(f"丢弃：非网址/空名条目 {stats['dropped_entries']}，同文件重复 {stats['dup_url']}，"
          f"跨分片重复 {stats['cross_dup']}")
    print(f"修正：类型越界 {stats['type_fixed']}，规则字段置空 "
          f"{stats['drop_ruleExplore'] + stats['drop_ruleSearch'] + stats['drop_ruleBookInfo'] + stats['drop_ruleToc'] + stats['drop_ruleContent'] + stats['drop_ruleReview']}，"
          f"未知子字段 {stats['drop_unknown_key']}，其它来源字段 {stats['drop_other_fields']}")
    (ROOT / "out-live").mkdir(exist_ok=True)
    (ROOT / "out-live" / "sanitize-report.json").write_text(
        json.dumps({"files": files, "entries": total, **stats}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
