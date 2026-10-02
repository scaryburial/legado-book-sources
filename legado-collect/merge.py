#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 raw/ 下各仓库收集到的 Legado 书源合并、去重、分类。

去重规则（"以最新的为准"）：
  1. 归一化 bookSourceUrl（去空白、统一小写、去掉 # 之后的变体标记、去尾部 /）
  2. 同一站点 + 同一 bookSourceType 视为一组，只保留"最优"的一条
  3. 最优 = lastUpdateTime 最新 > 规则最完整 > 来源仓库更新更近
"""
from __future__ import annotations

import hashlib
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "out"
ADULT_OUT = ROOT / "out-adult"

try:  # Windows 控制台默认 GBK，强制 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ---------------------------------------------------------------- 关键词表

ADULT_WORDS = re.compile(
    r"小黄|成人|18禁|18\+|🔞|🙈|色情|情色|肉文|撸|工口|里番|H漫|H文|H书|"
    r"海棠|PO18|po18|废文|書耽|书耽|长佩|腐文|耽美|BL小说|御宅屋|欲望社|"
    r"hlib|禁漫|禁漫天堂|jmcomic|nhentai|r18|R18|色色|福利姬|私房|写真|"
    r"成人向|情欲|欲|淫|艳情|桃色|虎穴|尻|榨精|肉便器|群交|乱伦|绿母|刘备|福利|"
    r"uaa\d*\.|yuwangshe|haitang|powenwu|huanxiwu|52blxs|yuzhaiwu|po18m",
    re.IGNORECASE,
)

# 仅用于识别"文件路径"里的成人分区标记（R18/ 目录、nsfw 命名等）
ADULT_PATH = re.compile(r"(^|/)(r18|nsfw|adult|18x)(/|\.|_|-|$)", re.IGNORECASE)

TYPE_TEXT, TYPE_AUDIO, TYPE_IMAGE, TYPE_FILE, TYPE_VIDEO = 0, 1, 2, 3, 4

TYPE_NAMES = {0: "文本小说", 1: "有声听书", 2: "漫画图源", 3: "文件网盘", 4: "视频影视"}

THEME_RULES = [
    ("正版出版", re.compile(
        r"起点|番茄小说|七猫|QQ阅读|微信读书|掌阅|晋江|纵横|飞卢|刺猬猫|SF轻小说|"
        r"咪咕|豆瓣|得到|知乎|多看|当当|京东读书|kindle|Amazon|GooglePlay图书|"
        r"BOOK|bookwalker|阅文|塔读|17K|17k|磨铁|博集|中信|出版", re.IGNORECASE)),
    ("轻小说二次元", re.compile(
        r"轻小说|輕小說|轻之国度|LK|wenku8|哔哩轻小说|哔哩|esj|真白萌|轻国|"
        r"二次元|动漫之家|kakuyomu|syosetu|narou|novel18", re.IGNORECASE)),
    ("学术文献", re.compile(
        r"学术|论文|期刊|知网|万方|维普|library|libgen|zlib|z-library|annas-archive|"
        r"PLOS|PubMed|arxiv|Sci-?Hub|读秀|超星|文献", re.IGNORECASE)),
    ("订阅RSS", re.compile(r"订阅|RSS|rss|feed|Feed|播客|Podcast|公众号", re.IGNORECASE)),
    ("女频言情", re.compile(
        r"女频|言情|现言|古言|浪漫|甜宠|宫斗|穿越女|青梅|晋江|腐|耽美|百合|"
        r"关耳|女生", re.IGNORECASE)),
    ("男频网文", re.compile(
        r"男频|玄幻|修真|仙侠|武侠|都市|神豪|战神|系统流|赘婿|兵王|无限流|"
        r"网游|末世|异能", re.IGNORECASE)),
    ("动漫图片", re.compile(r"图源|漫画|漫畫|写真|壁纸|插画|pixiv|Pixiv|manga|comic", re.IGNORECASE)),
    ("听书有声", re.compile(r"听书|有声|音频|广播|电台|TTS|tts|朗读|相声|评书", re.IGNORECASE)),
]

LOGIN_WORDS = re.compile(r"登录|登陆|验证|cookie|Cookie|账号|账户|扫码|人机|滑动验证|需要注册")

BROKEN_WORDS = re.compile(r"失\s*-?\s*效|无效|已挂|挂了|不能用|待修|❌|✖|⛔")

GOOD_WORDS = re.compile(r"优质|精选|精品|已检验|已验证|推荐|好用|稳定|常用|💯")

UNSTABLE_WORDS = re.compile(
    r"笔趣阁|笔趣|笔趣|书吧|小说网|文学网|书网|阅读网|书院|书屋|顶点|无弹窗|"
    r"免费小说|全本|TXT|txt下载")


# ---------------------------------------------------------------- 工具函数

def norm_url(u: str, keep_variant: bool = True) -> str:
    """
    归一化书源地址。
    keep_variant=True  保留 # 之后的变体标记（同站不同规则要分开）
    keep_variant=False 丢掉变体标记（用于"同站合并"）
    """
    if not u:
        return ""
    s = str(u).replace("\u3000", " ").strip().lower()
    s = re.sub(r"\s+", "", s)
    # 兼容 "ohttps://" 这类手抖前缀
    m = re.search(r"[a-z][a-z0-9+.\-]*://", s)
    if m and m.start() > 0:
        s = s[m.start():]
    base, sep, frag = s.partition("#")
    base = base.rstrip("/")
    if keep_variant and sep and frag.strip():
        return f"{base}#{frag}"
    return base


def base_key(u: str) -> str:
    """同站合并用的键：去协议、去 www、去变体。"""
    s = norm_url(u, keep_variant=False)
    s = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.rstrip("/")


LEGACY_KEYS = re.compile(r"^(ruleSearchUrl|ruleSearchList|ruleSearchName|ruleSearchAuthor|"
                         r"ruleBookName|ruleBookAuthor|ruleBookContent|ruleChapterList|"
                         r"ruleChapterName|ruleChapterUrl|ruleFindUrl)$")


def is_legacy(bs: dict) -> bool:
    """阅读 2.x 老格式：没有 searchUrl/ruleToc，只有 ruleXxx 扁平字段。"""
    if str(bs.get("searchUrl") or "").strip():
        return False
    rt = bs.get("ruleToc")
    if isinstance(rt, dict) and str(rt.get("chapterList") or "").strip():
        return False
    return any(LEGACY_KEYS.match(k) for k in bs.keys())


def host_of(u: str) -> str:
    if not u:
        return ""
    s = str(u).strip()
    if "://" not in s:
        s = "http://" + s
    try:
        h = urlsplit(s).hostname or ""
    except Exception:
        h = ""
    return h.lower().lstrip(".")


def rule_score(bs: dict) -> int:
    """规则完整度打分：能不能搜、能不能取目录、能不能取正文。"""
    score = 0
    if (bs.get("searchUrl") or "").strip():
        score += 2
    rs = bs.get("ruleSearch") or {}
    if isinstance(rs, dict) and any(str(v).strip() for v in rs.values() if v):
        score += 1
    rt = bs.get("ruleToc") or {}
    if isinstance(rt, dict) and str(rt.get("chapterList") or "").strip():
        score += 2
    rc = bs.get("ruleContent") or {}
    if isinstance(rc, dict) and str(rc.get("content") or "").strip():
        score += 2
    rbi = bs.get("ruleBookInfo") or {}
    if isinstance(rbi, dict) and any(str(v).strip() for v in rbi.values() if v):
        score += 1
    if (bs.get("exploreUrl") or "").strip():
        score += 1
    return score


def ts_of(bs: dict) -> int:
    """lastUpdateTime，毫秒或秒都兼容。"""
    try:
        t = int(bs.get("lastUpdateTime") or 0)
    except Exception:
        return 0
    if t and t < 10_000_000_000:      # 秒
        t *= 1000
    if t < 1_000_000_000_000:         # 明显不是有效毫秒时间
        return 0
    return t


def type_of(bs: dict) -> int:
    """bookSourceType 有时会被写成 '漫画' 之类的文字。"""
    v = bs.get("bookSourceType")
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v or "").strip()
    if s.isdigit():
        return int(s)
    table = {"文本": 0, "小说": 0, "音频": 1, "有声": 1, "听书": 1,
             "图片": 2, "漫画": 2, "图源": 2, "文件": 3, "视频": 4}
    return table.get(s, 0)


def parse_json_lenient(text: str):
    """容忍 BOM / 尾逗号 / 前后杂字符。"""
    t = text.lstrip("\ufeff \t\r\n")
    try:
        return json.loads(t)
    except Exception:
        pass
    # 去掉尾逗号
    try:
        return json.loads(re.sub(r",\s*([\]}])", r"\1", t))
    except Exception:
        pass
    # 只截取最外层的 [ ... ]
    i, j = t.find("["), t.rfind("]")
    if 0 <= i < j:
        frag = t[i:j + 1]
        try:
            return json.loads(frag)
        except Exception:
            try:
                return json.loads(re.sub(r",\s*([\]}])", r"\1", frag))
            except Exception:
                return None
    return None


def iter_candidate_files():
    """遍历 raw 下所有可能是书源的文件。"""
    skip_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".zip",
                ".gz", ".tgz", ".apk", ".so", ".dll", ".exe", ".woff", ".woff2",
                ".ttf", ".eot", ".mp3", ".mp4", ".epub", ".pdf", ".jar", ".class",
                ".dex", ".bak", ".png", ".xml", ".md", ".html", ".css", ".js"}
    for p in RAW.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in skip_ext:
            continue
        sz = p.stat().st_size
        if sz < 32 or sz > 120 * 1024 * 1024:
            continue
        yield p


def load_repo_dates() -> dict:
    """仓库最近推送时间，用作 lastUpdateTime 缺失时的兜底。"""
    dates = {}
    meta = RAW / "all-repos.json"
    if meta.exists():
        try:
            for r in json.loads(meta.read_text(encoding="utf-8")):
                dates[r["repo"]] = r.get("pushed") or ""
        except Exception:
            pass
    return dates


def repo_label(path: Path) -> tuple[str, str]:
    """从文件路径推断来源仓库与站内路径。"""
    rel = path.relative_to(RAW).as_posix()
    parts = rel.split("/")
    if parts[0] == "repos" and len(parts) > 2:
        return parts[1].replace("__", "/"), "/".join(parts[2:])
    if parts[0] == "zgq":
        return "ZGQ-inc/source_repo", "/".join(parts[1:])
    return "local", rel


# ---------------------------------------------------------------- 主流程

def main() -> int:
    repo_dates = load_repo_dates()
    files = list(iter_candidate_files())
    print(f"待扫描文件: {len(files)}", flush=True)

    entries = []          # {"bs":..., "repo":..., "path":..., "repo_date":...}
    seen_file_hash = set()
    scanned = 0
    for p in files:
        try:
            raw_bytes = p.read_bytes()
        except Exception:
            continue
        h = hashlib.md5(raw_bytes, usedforsecurity=False).hexdigest()
        if h in seen_file_hash:      # 同一份文件被多个仓库重复收录
            continue
        if b"bookSourceUrl" not in raw_bytes[:4_000_000] and b"bookSourceUrl" not in raw_bytes[-4_000_000:]:
            continue
        seen_file_hash.add(h)
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("utf-8", "ignore")
            except Exception:
                continue
        doc = parse_json_lenient(text)
        if doc is None:
            continue
        if isinstance(doc, dict):
            doc = [doc]
        if not isinstance(doc, list):
            continue
        repo, inner = repo_label(p)
        repo_date = repo_dates.get(repo) or datetime.fromtimestamp(
            p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
        got = 0
        for bs in doc:
            if not isinstance(bs, dict) or not bs.get("bookSourceUrl") or not bs.get("bookSourceName"):
                continue
            entries.append({"bs": bs, "repo": repo, "path": inner, "repo_date": repo_date})
            got += 1
        if got:
            scanned += 1
            print(f"  {got:6d} 条 <- {repo} :: {inner}", flush=True)

    print(f"命中的书源文件: {scanned}，原始条目合计: {len(entries)}", flush=True)

    # ---------------- 去重（两级） ----------------
    def rank(e):
        bs = e["bs"]
        return (
            ts_of(bs),
            rule_score(bs),
            len(json.dumps(bs, ensure_ascii=False)),
            e["repo_date"],
        )

    def collapse(items, keyfn):
        """同一键只留最优的一条，并记录它被哪几个仓库收录过。"""
        groups: dict = defaultdict(list)
        for e in items:
            groups[keyfn(e)].append(e)
        out = []
        for key, group in groups.items():
            group.sort(key=rank, reverse=True)
            best = group[0]
            best["sources"] = sorted({i["repo"] for i in group})
            best["dupes"] = len(group) - 1
            best["variants"] = len({str(i["bs"].get("bookSourceUrl") or "") for i in group})
            out.append(best)
        return out

    # 一级：完整地址（含变体）+ 类型，保持同站不同源的差异
    exact = collapse(entries, lambda e: (norm_url(e["bs"].get("bookSourceUrl")), type_of(e["bs"])))
    # 二级：同站合并，交给想要"越小越好"的用户
    merged = collapse(entries, lambda e: (base_key(e["bs"].get("bookSourceUrl")), type_of(e["bs"])))

    stats = {"raw": len(entries), "exact_groups": len(exact), "base_groups": len(merged),
             "dropped_exact": len(entries) - len(exact),
             "dropped_base": len(entries) - len(merged)}
    deduped = exact
    print(f"按完整地址去重: {len(exact)}（合并掉 {stats['dropped_exact']}）", flush=True)
    print(f"按同站合并后  : {len(merged)}（合并掉 {stats['dropped_base']}）", flush=True)

    # ---------------- 分类 ----------------
    def classify(e):
        bs = e["bs"]
        name = str(bs.get("bookSourceName") or "")
        group = str(bs.get("bookSourceGroup") or "")
        comment = str(bs.get("bookSourceComment") or "")
        url = str(bs.get("bookSourceUrl") or "")
        blob = f"{name} {group} {comment} {url}"      # 只用书源自身字段判定题材
        pathblob = str(e["path"])                     # 文件路径只用来识别成人分区

        bstype = type_of(bs)
        tags = []
        if ADULT_WORDS.search(blob) or ADULT_PATH.search(pathblob):
            tags.append("成人向")
        if bstype == TYPE_IMAGE or re.search(r"漫画|漫畫|图源|manga|comic", blob, re.I):
            tags.append("漫画图源")
        if bstype == TYPE_AUDIO or re.search(r"听书|有声|音频|广播|电台|TTS|朗读|评书", blob, re.I):
            tags.append("有声听书")
        if bstype == TYPE_VIDEO or re.search(r"视频|影视|电影", blob, re.I):
            tags.append("视频影视")
        if bstype == TYPE_FILE or re.search(r"网盘|下载站|文件源|drive\.|pan\.", blob, re.I):
            tags.append("文件网盘")
        if is_legacy(bs):
            tags.append("旧版格式")
        if UNSTABLE_WORDS.search(blob):
            tags.append("站群模板")
        if BROKEN_WORDS.search(f"{name} {group}"):
            tags.append("社区标记失效")
        elif GOOD_WORDS.search(f"{name} {group}"):
            tags.append("社区推荐")
        for tname, rx in THEME_RULES:
            if rx.search(blob):
                tags.append(tname)
        if not any(t in tags for t in ("漫画图源", "有声听书", "视频影视", "文件网盘")):
            tags.append("文本小说")
        return tags

    def annotate(e):
        e["tags"] = classify(e)
        bs = e["bs"]
        e["name"] = str(bs.get("bookSourceName") or "").strip()
        e["url"] = str(bs.get("bookSourceUrl") or "").strip()
        e["host"] = host_of(e["url"])
        e["type"] = type_of(bs)
        e["quality"] = rule_score(bs)
        e["ts"] = ts_of(bs)
        e["updated"] = (
            datetime.fromtimestamp(e["ts"] / 1000, timezone.utc).strftime("%Y-%m-%d")
            if e["ts"] else ""
        )
        e["adult"] = "成人向" in e["tags"]
        e["legacy"] = "旧版格式" in e["tags"]
        e["needs_login"] = bool(LOGIN_WORDS.search(str(bs.get("bookSourceComment") or "")))
        e["unstable"] = bool(UNSTABLE_WORDS.search(e["name"]))
        return e

    deduped = [annotate(e) for e in deduped]
    merged = [annotate(e) for e in merged]

    mainstream = [e for e in deduped if not e["adult"]]
    stats["adult"] = len(deduped) - len(mainstream)
    print(f"其中成人向被隔离: {stats['adult']}，主流集合: {len(mainstream)}", flush=True)

    for e in deduped + merged:
        e["broken"] = "社区标记失效" in e["tags"]
    stats["flagged_broken"] = sum(1 for e in mainstream if e["broken"])
    print(f"社区自标失效: {stats['flagged_broken']}", flush=True)

    # ---------------- 输出 ----------------
    keep = OUT / "alive"          # 可达性检测结果目录要保留
    if OUT.exists():
        for f in sorted(OUT.rglob("*"), reverse=True):
            if keep in f.parents or f == keep:
                continue
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                try:
                    f.rmdir()
                except OSError:
                    pass
    OUT.mkdir(parents=True, exist_ok=True)

    def dump(path: Path, items, key="bs"):
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [dict(i[key]) for i in items]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return len(payload)

    def dump_chunked(dirname: str, items, chunk=1000, prefix="part", base: Path = OUT):
        items = sorted(items, key=lambda e: (-e["quality"], -e["ts"], e["name"]))
        n = 0
        for i in range(0, len(items), chunk):
            part = items[i:i + chunk]
            n += 1
            dump(base / dirname / f"{prefix}{n:02d}.json", part)
        return n

    manifest = []

    # 现代格式（阅读 3.0 可直接用）与旧格式（2.x 遗留）分开
    modern = [e for e in mainstream if not e["legacy"]]
    legacy = [e for e in mainstream if e["legacy"]]
    merged_main = [e for e in merged if not e["adult"]]
    merged_modern = [e for e in merged_main if not e["legacy"]]

    # 1) 全量（按完整地址去重后的主流集合）
    parts = dump_chunked("00-全量去重", modern)
    manifest.append({"dir": "00-全量去重", "desc": "主流书源全量，按完整地址去重（同站不同源保留），分片导入",
                     "count": len(modern), "parts": parts})

    # 1b) 同站合并版（更小，适合手机）
    parts = dump_chunked("01-同站合并", merged_modern)
    manifest.append({"dir": "01-同站合并", "desc": "同一站点只留最优的一条，体积最小，适合手机导入",
                     "count": len(merged_modern), "parts": parts})

    # 2) 按内容形态
    for t in ["文本小说", "有声听书", "漫画图源", "视频影视", "文件网盘"]:
        items = [e for e in modern if t in e["tags"]]
        if not items:
            continue
        parts = dump_chunked(f"10-形态/{t}", items)
        manifest.append({"dir": f"10-形态/{t}", "desc": f"内容形态：{t}", "count": len(items), "parts": parts})

    # 3) 按题材/来源
    for tname, _ in THEME_RULES:
        items = [e for e in modern if tname in e["tags"]]
        if not items:
            continue
        parts = dump_chunked(f"20-题材/{tname}", items, chunk=500)
        manifest.append({"dir": f"20-题材/{tname}", "desc": f"题材/来源：{tname}", "count": len(items), "parts": parts})

    # 4) 精品：规则完整度高（能搜能看）且不是站群模板、不被社区标记失效
    jingpin = [e for e in modern if e["quality"] >= 6 and not e["unstable"] and not e["broken"]]
    parts = dump_chunked("30-精品", jingpin, chunk=500)
    manifest.append({"dir": "30-精品", "desc": "精品：搜索/目录/正文规则齐全，且非笔趣阁类站群模板", "count": len(jingpin), "parts": parts})

    # 5) 可探索源（有分类页，适合找书）
    explore = [e for e in modern if str((e["bs"].get("exploreUrl") or "")).strip() and not e["broken"]]
    parts = dump_chunked("31-可发现", explore, chunk=500)
    manifest.append({"dir": "31-可发现", "desc": "带分类/榜单页，适合逛书城式找书", "count": len(explore), "parts": parts})

    # 5b) 入门精选：规则满分 + 有分类页 + 非站群 + 更新较新，取前 300
    recent_cut = f"{int(TODAY[:4]) - 2}{TODAY[4:]}"
    starter = [e for e in modern if e["quality"] >= 8 and not e["unstable"] and not e["broken"]
               and str((e["bs"].get("exploreUrl") or "")).strip()
               and (e["updated"] or "") >= recent_cut]
    starter = sorted(starter, key=lambda e: (-e["quality"], -(e["ts"] or 0), e["name"]))[:300]
    if starter:
        parts = dump_chunked("32-入门精选", starter, chunk=300)
        manifest.append({"dir": "32-入门精选", "desc": "入门精选：规则齐全 + 有分类页 + 非站群模板 + 近两年有更新，限 300 条",
                         "count": len(starter), "parts": parts})

    # 6) 旧版格式（阅读 2.x 遗留，导入后需自行升级/校验）
    if legacy:
        parts = dump_chunked("40-旧版格式", legacy, chunk=1000)
        manifest.append({"dir": "40-旧版格式", "desc": "阅读 2.x 老格式源，多为 2019 年前后的失效站点，单独存放备查",
                         "count": len(legacy), "parts": parts})

    # 7) 社区自标失效（合集维护者已经标注搜索/发现失效）
    flagged = [e for e in modern if e["broken"]]
    if flagged:
        parts = dump_chunked("60-社区标记失效", flagged, chunk=1000)
        manifest.append({"dir": "60-社区标记失效", "desc": "原合集分组里已被标注「搜索失效/发现失效」的源，留档别直接导",
                         "count": len(flagged), "parts": parts})

    # ---------------- 成人向：单独一套目录树（out-adult/） ----------------
    stats["isolated_adult"] = len(deduped) - len(mainstream)

    adult_exact = [e for e in deduped if e["adult"]]
    adult_merged = [e for e in merged if e["adult"]]

    # 成人向内部再分一层：先按形态，再按题材
    ADULT_SUB = [
        ("成人漫画图源", lambda e: "漫画图源" in e["tags"] or "动漫图片" in e["tags"]),
        ("成人有声听书", lambda e: "有声听书" in e["tags"]),
        ("成人视频影视", lambda e: "视频影视" in e["tags"]),
        ("成人文件网盘", lambda e: "文件网盘" in e["tags"]),
        ("成人同人耽美", lambda e: re.search(r"耽美|腐|BL|百合|同人|乙女|原耽", f"{e['name']} {e['bs'].get('bookSourceGroup') or ''}", re.I) is not None),
        ("成人轻小说二次元", lambda e: "轻小说二次元" in e["tags"]),
    ]
    for e in adult_exact:
        e["adult_sub"] = next((n for n, fn in ADULT_SUB if fn(e)), "成人小说文本")

    if ADULT_OUT.exists():
        for f in sorted(ADULT_OUT.rglob("*"), reverse=True):
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                try:
                    f.rmdir()
                except OSError:
                    pass
    ADULT_OUT.mkdir(parents=True, exist_ok=True)

    adult_manifest = []
    parts = dump_chunked("00-全量去重", adult_exact, chunk=500, base=ADULT_OUT)
    adult_manifest.append({"dir": "00-全量去重", "desc": "成人向全量（按完整地址去重，同站不同源保留）",
                           "count": len(adult_exact), "parts": parts})

    parts = dump_chunked("01-同站合并", adult_merged, chunk=500, base=ADULT_OUT)
    adult_manifest.append({"dir": "01-同站合并", "desc": "成人向同站合并版，手机导入用这个",
                           "count": len(adult_merged), "parts": parts})

    for sub, fn in ADULT_SUB:
        items = [e for e in adult_exact if e["adult_sub"] == sub]
        if not items:
            continue
        parts = dump_chunked(f"10-分类/{sub}", items, chunk=500, base=ADULT_OUT)
        adult_manifest.append({"dir": f"10-分类/{sub}", "desc": sub,
                               "count": len(items), "parts": parts})

    items = [e for e in adult_exact if e["adult_sub"] == "成人小说文本"]
    if items:
        parts = dump_chunked("10-分类/成人小说文本", items, chunk=500, base=ADULT_OUT)
        adult_manifest.append({"dir": "10-分类/成人小说文本", "desc": "成人向文本小说（默认类）",
                               "count": len(items), "parts": parts})

    # 成人向里规则最完整的一批
    adult_good = [e for e in adult_exact if e["quality"] >= 6 and not e["broken"]]
    parts = dump_chunked("30-规则完整", adult_good, chunk=500, base=ADULT_OUT)
    adult_manifest.append({"dir": "30-规则完整", "desc": "成人向里搜索/目录/正文规则齐全且未被标记失效的",
                           "count": len(adult_good), "parts": parts})

    adult_broken = [e for e in adult_exact if e["broken"]]
    if adult_broken:
        parts = dump_chunked("60-社区标记失效", adult_broken, chunk=500, base=ADULT_OUT)
        adult_manifest.append({"dir": "60-社区标记失效", "desc": "原合集已标注搜索/发现失效",
                               "count": len(adult_broken), "parts": parts})

    with (ADULT_OUT / "index.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["书源名", "站点", "细分", "标签", "规则完整度", "最后更新",
                    "重复份数", "来源仓库", "需登录", "地址"])
        for e in sorted(adult_exact, key=lambda x: (x["adult_sub"], -x["quality"], -x["ts"])):
            w.writerow([
                e["name"], e["host"], e["adult_sub"], "/".join(t for t in e["tags"] if t != "成人向"),
                e["quality"], e["updated"] or "未知", e["dupes"] + 1, "|".join(e["sources"]),
                "是" if e["needs_login"] else "", e["url"],
            ])

    adult_stats = {
        "date": TODAY,
        "count": len(adult_exact),
        "merged": len(adult_merged),
        "by_sub": dict(sorted(
            {s: sum(1 for e in adult_exact if e["adult_sub"] == s) for s, _ in ADULT_SUB + [("成人小说文本", None)]}.items(),
            key=lambda kv: -kv[1])),
        "by_type": dict(sorted(Counter(TYPE_NAMES.get(e["type"], str(e["type"])) for e in adult_exact).items(),
                               key=lambda kv: -kv[1])),
        "quality_dist": {f"{q}分": sum(1 for e in adult_exact if e["quality"] == q) for q in range(9, -1, -1)},
        "flagged_broken": len(adult_broken),
        "rule_complete": len(adult_good),
        "manifest": adult_manifest,
    }
    (ADULT_OUT / "stats.json").write_text(json.dumps(adult_stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"成人向单独导出: {len(adult_exact)} 条 -> out-adult/", flush=True)

    # ---------------- 索引 CSV ----------------
    idx = OUT / "index.csv"
    with idx.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["书名源名", "站点", "类型", "标签", "规则完整度", "最后更新",
                    "重复份数", "来源仓库", "需登录", "站群模板", "地址"])
        for e in sorted(mainstream, key=lambda x: (-x["quality"], -x["ts"])):
            w.writerow([
                e["name"], e["host"], TYPE_NAMES.get(e["type"], e["type"]),
                "/".join(e["tags"]), e["quality"], e["updated"] or "未知",
                e["dupes"] + 1, "|".join(e["sources"]),
                "是" if e["needs_login"] else "", "是" if e["unstable"] else "", e["url"],
            ])

    # ---------------- 统计 ----------------
    def count_by(fn):
        d = defaultdict(int)
        for e in mainstream:
            d[fn(e)] += 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    stats.update({
        "date": TODAY,
        "mainstream": len(mainstream),
        "modern": len(modern),
        "legacy": len(legacy),
        "merged_main": len(merged_modern),
        "by_type": count_by(lambda e: TYPE_NAMES.get(e["type"], str(e["type"]))),
        "by_tag": count_by(lambda e: "/".join(e["tags"])),
        "by_repo_hit": count_by(lambda e: e["sources"][0] if len(e["sources"]) == 1 else "多来源重合"),
        "quality_dist": count_by(lambda e: f"{e['quality']}分"),
        "with_explore": sum(1 for e in mainstream if str((e["bs"].get("exploreUrl") or "")).strip()),
        "needs_login": sum(1 for e in mainstream if e["needs_login"]),
        "updated_known": sum(1 for e in mainstream if e["updated"]),
        "updated_recent_1y": sum(
            1 for e in mainstream
            if e["updated"] and e["updated"] >= f"{int(TODAY[:4]) - 1}{TODAY[4:]}"),
        "manifest": manifest,
        "source_files": scanned,
        "source_repos": len({e["repo"] for e in entries}),
    })
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------- 逐仓库贡献 ----------------
    contrib = defaultdict(int)
    for e in entries:
        contrib[e["repo"]] += 1
    (OUT / "repo-contribution.json").write_text(
        json.dumps(dict(sorted(contrib.items(), key=lambda kv: -kv[1])), ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(json.dumps({k: v for k, v in stats.items() if k != "manifest"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
