#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书源真实可用性测试：直接按 searchUrl 请求一次搜索页，判断这个源还能不能用。

- 不走系统代理（显式关闭 ProxyHandler）
- 只测 小说(0) / 漫画(2) / 视频(4) 三类
- 结果写 out-live/test-<tag>.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
ADULT = ROOT / "out-adult"
LIVE = ROOT / "out-live"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UA = ("Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 明确不走代理
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),          # 空 = 禁用代理
    urllib.request.HTTPSHandler(context=CTX),
)

KEYWORD = {"0": "剑来", "2": "火影", "4": "斗破"}
TARGET_TYPES = ("0", "2", "4")


def norm_url(u: str) -> str:
    u = (u or "").strip()
    u = re.sub(r"[#\s].*$", "", u)
    if not u:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.\-]*://", u, re.I):
        u = "http://" + u
    u = u.replace("[", "").replace("]", "")
    return u


def build_test_url(bs: dict) -> tuple[str, str]:
    """返回 (测试地址, 测试方式)。优先测真实搜索。"""
    raw_type = str(bs.get("bookSourceType", 0))
    keyword = KEYWORD.get(raw_type, "剑来")
    base = norm_url(bs.get("bookSourceUrl"))
    search = str(bs.get("searchUrl") or "").strip()

    if search and "<js>" not in search.lower() and "@js:" not in search.lower():
        # 去掉 Legado 的 ",{...}" 请求配置尾巴
        tpl = re.split(r",\s*\{", search, maxsplit=1)[0].strip()
        if tpl and not re.search(r"\{\{(?!key|page)[^}]*\}\}", tpl):
            tpl = tpl.replace("{{page}}", "1")
            tpl = tpl.replace("{{key}}", urllib.parse.quote(keyword))
            if tpl.startswith("//"):
                return "https:" + tpl, "search"
            if tpl.startswith("/"):
                m = re.match(r"^(https?://[^/]+)", base)
                if m:
                    return m.group(1) + tpl, "search"
                return base, "base"
            if re.match(r"^https?://", tpl):
                return tpl, "search"
            if base:
                return base.rstrip("/") + "/" + tpl.lstrip("/"), "search"
    return base, "base"


def probe(bs: dict):
    try:
        url, how = build_test_url(bs)
        if not url:
            return {"status": "无地址", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
        # 域名必须是纯 ASCII，否则 urllib 会直接抛 ValueError
        m = re.match(r"^(https?://)([^/]+)(.*)$", url, re.I)
        if not m or not re.match(r"^[A-Za-z0-9.\-:_\[\]]+$", m.group(2)):
            return {"status": "无效地址", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
        keyword = KEYWORD.get(str(bs.get("bookSourceType", 0)), "剑来")
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with OPENER.open(req, timeout=12) as r:
            code = r.getcode()
            body = r.read(400_000)
            final = r.geturl()
        txt = ""
        for enc in ("utf-8", "gbk", "gb18030"):
            try:
                txt = body.decode(enc)
                break
            except Exception:
                continue
        if not txt:
            txt = body.decode("utf-8", "ignore")
        kw_hit = "命中" if keyword in txt else ""
        if code == 200 and len(body) >= 2000:
            status = "可用"
        elif code == 200:
            status = "可疑"
        else:
            status = "异常状态"
        return {"status": status, "code": code, "len": len(body), "kw": kw_hit,
                "how": how, "final": final[:120]}
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 405, 406, 429):
            return {"status": "拦截", "code": e.code, "len": 0, "kw": "", "how": how, "final": ""}
        if e.code in (404, 410):
            return {"status": "失效", "code": e.code, "len": 0, "kw": "", "how": how, "final": ""}
        return {"status": "异常状态", "code": e.code, "len": 0, "kw": "", "how": how, "final": ""}
    except urllib.error.URLError as e:
        r = str(getattr(e, "reason", e)).lower()
        if "timed out" in r or isinstance(getattr(e, "reason", None), socket.timeout):
            return {"status": "超时", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
        if "getaddrinfo" in r or "name or service" in r:
            return {"status": "域名失效", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
        return {"status": "连不上", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
    except socket.timeout:
        return {"status": "超时", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}
    except Exception:
        return {"status": "其它错误", "code": 0, "len": 0, "kw": "", "how": how, "final": ""}


def load_all() -> list[dict]:
    items, seen = [], set()
    for d in (OUT / "00-全量去重", ADULT / "00-全量去重"):
        for p in sorted(d.glob("part*.json")):
            for bs in json.loads(p.read_text(encoding="utf-8")):
                t = str(bs.get("bookSourceType", 0))
                if t not in TARGET_TYPES:
                    continue
                u = str(bs.get("bookSourceUrl") or "").strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                bs["_adult"] = "1" if "out-adult" in str(p) else ""
                items.append(bs)
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=3)
    ap.add_argument("--workers", type=int, default=160)
    ap.add_argument("--tag", default="A")
    args = ap.parse_args()

    LIVE.mkdir(parents=True, exist_ok=True)
    items = load_all()
    todo = [x for i, x in enumerate(items) if i % args.shards == args.shard]
    print(f"分片 {args.tag}: 待测 {len(todo)} / 全部 {len(items)}", flush=True)

    t0 = time.time()
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (bs, r) in enumerate(zip(todo, pool.map(probe, todo)), 1):
            rows.append({
                "名称": str(bs.get("bookSourceName") or "").strip(),
                "地址": str(bs.get("bookSourceUrl") or "").strip(),
                "类型": str(bs.get("bookSourceType", 0)),
                "成人向": bs.get("_adult", ""),
                "状态": r["status"], "HTTP": r["code"], "长度": r["len"],
                "命中关键词": r["kw"], "测法": r["how"], "最终地址": r["final"],
            })
            if i % 1000 == 0:
                print(f"  {i}/{len(todo)}  {time.time()-t0:.0f}s", flush=True)

    path = LIVE / f"test-{args.tag}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {}
    for r in rows:
        summary[r["状态"]] = summary.get(r["状态"], 0) + 1
    payload = {"tag": args.tag, "checked": len(rows), "summary": summary,
               "seconds": round(time.time() - t0, 1)}
    (LIVE / f"test-{args.tag}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
