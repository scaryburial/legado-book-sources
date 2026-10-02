#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对去重后的书源做一次轻量可达性抽检。
只做一次 GET（读取少量字节就断开），不解析页面内容，目的是粗筛"域名还在不在"。
注意：403/429 只代表"服务器在但对脚本不友好"，不等于书源失效。
"""
from __future__ import annotations

import csv
import argparse
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UA = ("Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def norm(u: str) -> str:
    u = (u or "").strip()
    u = re.sub(r"[#\s].*$", "", u)
    if not u:
        return ""
    if not re.match(r"^[a-z][a-z0-9+.\-]*://", u, re.I):
        u = "http://" + u
    # 去掉会让 urllib 直接抛 ValueError 的非法字符
    u = u.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
    u = re.sub(r"[^\x21-\x7e\u0080-\uffff]", "", u)
    return u


def probe(url: str):
    try:
        u = norm(url)
        if not u:
            return ("无效地址", 0)
        req = urllib.request.Request(u, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Range": "bytes=0-2048",
        })
        with urllib.request.urlopen(req, timeout=8, context=CTX) as resp:
            resp.read(512)
            code = resp.getcode()
            return ("可达", code)
    except urllib.error.HTTPError as e:
        code = e.code
        if code in (401, 402, 403, 405, 406, 429):
            return ("有响应(拦截)", code)
        if code in (404, 410):
            return ("页面不存在", code)
        return ("异常状态", code)
    except urllib.error.URLError as e:
        r = str(e.reason)
        if isinstance(e.reason, socket.timeout) or "timed out" in r.lower():
            return ("超时", 0)
        if "Name or service not known" in r or "getaddrinfo" in r or "nodename" in r.lower():
            return ("域名解析失败", 0)
        return ("连接失败", 0)
    except socket.timeout:
        return ("超时", 0)
    except Exception:
        return ("其它错误", 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="pfrom", type=int, default=1, help="起始分片号（含）")
    ap.add_argument("--to", dest="pto", type=int, default=999, help="结束分片号（含）")
    ap.add_argument("--tag", default="all", help="输出文件后缀，用于分片并行")
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--base", default="", help="要检测的分片目录（默认 out/00-全量去重）")
    args = ap.parse_args()

    base = Path(args.base) if args.base else (OUT / "00-全量去重")
    alive_dir = base.parent / "alive"
    items = []
    seen = set()
    parts = sorted(base.glob("part*.json"))
    parts = [p for p in parts if args.pfrom <= int(re.search(r"(\d+)", p.stem).group(1)) <= args.pto]
    print(f"分片: {[p.stem for p in parts]}", flush=True)
    for part in parts:
        for bs in json.loads(part.read_text(encoding="utf-8")):
            u = str(bs.get("bookSourceUrl") or "").strip()
            if not u or u in seen:
                continue
            seen.add(u)
            items.append({
                "name": str(bs.get("bookSourceName") or "").strip(),
                "url": u,
                "group": str(bs.get("bookSourceGroup") or "").strip(),
                "type": bs.get("bookSourceType", 0),
            })

    print(f"待检测: {len(items)}", flush=True)
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (it, (status, code)) in enumerate(zip(items, pool.map(lambda x: probe(x["url"]), items)), 1):
            it["status"] = status
            it["code"] = code
            results.append(it)
            if i % 2000 == 0:
                print(f"  {i}/{len(items)}  {time.time()-t0:.0f}s", flush=True)

    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    alive_dir.mkdir(parents=True, exist_ok=True)
    with (alive_dir / f"可达性_{args.tag}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["书源名", "分组", "状态", "HTTP", "地址"])
        for r in sorted(results, key=lambda x: (x["status"], x["name"])):
            w.writerow([r["name"], r["group"], r["status"], r["code"] or "", r["url"]])

    live = sum(v for k, v in summary.items() if k in ("可达", "有响应(拦截)"))
    payload = {
        "tag": args.tag,
        "checked": len(results),
        "live_or_reachable": live,
        "live_rate": round(live / max(1, len(results)) * 100, 1),
        "summary": dict(sorted(summary.items(), key=lambda kv: -kv[1])),
        "note": "403/429 等归入'有响应(拦截)'，只说明服务器在，不能判定书源可用。",
        "seconds": round(time.time() - t0, 1),
    }
    (alive_dir / f"可达性_{args.tag}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
