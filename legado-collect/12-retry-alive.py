#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对上一轮"超时/连接失败/其它错误"的源做复检：更长超时 + 重试。
结果写 可达性_R<n>.csv，11-finalize.py 会以后写入的结果覆盖旧结果。
"""
from __future__ import annotations

import argparse
import csv
import json
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
ALIVE = OUT / "alive"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

UA = ("Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RETRY_STATUS = {"超时", "连接失败", "其它错误", "异常状态"}


def probe(url: str, timeout: int, retries: int):
    u = (url or "").strip()
    if not u:
        return ("无效地址", 0)
    if not u.lower().startswith(("http://", "https://")):
        u = "http://" + u
    u = u.replace("[", "").replace("]", "")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(u, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
                resp.read(512)
                return ("可达", resp.getcode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403, 405, 406, 429):
                return ("有响应(拦截)", e.code)
            if e.code in (404, 410):
                return ("页面不存在", e.code)
            last = ("异常状态", e.code)
        except urllib.error.URLError as e:
            r = str(getattr(e, "reason", e)).lower()
            if "timed out" in r or isinstance(getattr(e, "reason", None), socket.timeout):
                last = ("超时", 0)
            else:
                last = ("连接失败", 0)
        except socket.timeout:
            last = ("超时", 0)
        except Exception:
            last = ("其它错误", 0)
        time.sleep(0.4)
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--workers", type=int, default=160)
    ap.add_argument("--tag", default="R1")
    args = ap.parse_args()

    seen = set()
    todo = []
    for f in sorted(ALIVE.glob("可达性_*.csv")):
        if f.stem.endswith(args.tag):
            continue
        with f.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                u = row["地址"].strip()
                if u in seen:
                    continue
                seen.add(u)
                if row["状态"] in RETRY_STATUS:
                    todo.append({"name": row["书源名"], "url": u,
                                 "group": row.get("分组", ""), "type": row.get("类型", "")})
    todo = [t for i, t in enumerate(todo) if i % args.shards == args.shard]
    print(f"复检分片 {args.shard}/{args.shards}  待复检 {len(todo)} 条", flush=True)

    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (it, (st, code)) in enumerate(
                zip(todo, pool.map(lambda x: probe(x["url"], args.timeout, args.retries), todo)), 1):
            it["status"] = st
            it["code"] = code
            results.append(it)
            if i % 500 == 0:
                print(f"  {i}/{len(todo)}  {time.time()-t0:.0f}s", flush=True)

    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    ALIVE.mkdir(parents=True, exist_ok=True)
    suffix = args.tag if args.shards == 1 else f"{args.tag}s{args.shard}"
    with (ALIVE / f"可达性_{suffix}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["书源名", "分组", "状态", "HTTP", "地址"])
        for r in results:
            w.writerow([r["name"], r["group"], r["status"], r["code"] or "", r["url"]])

    payload = {"tag": suffix, "checked": len(results), "summary": summary,
               "seconds": round(time.time() - t0, 1)}
    (ALIVE / f"可达性_{suffix}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
