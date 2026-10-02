#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 entry 对比基线官方 APK 与重打包 APK，输出差异清单与统计。"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def digest(zf: zipfile.ZipFile, name: str) -> str:
    return hashlib.sha256(zf.read(name)).hexdigest()


def describe(path: Path) -> dict:
    zf = zipfile.ZipFile(path)
    out = {}
    for info in zf.infolist():
        if info.is_dir():
            continue
        out[info.filename] = {
            "size": info.file_size,
            "csize": info.compress_size,
            "method": info.compress_type,
            "sha256": digest(zf, info.filename),
        }
    zf.close()
    return out


def main() -> int:
    base = describe(Path(sys.argv[1]))
    print(f"基线: {sys.argv[1]}  条目 {len(base)}")
    for target in sys.argv[2:]:
        tgt = describe(Path(target))
        names_b = set(base)
        names_t = set(tgt)
        same = [n for n in names_b & names_t if base[n]["sha256"] == tgt[n]["sha256"]]
        diff = [
            n
            for n in names_b & names_t
            if base[n]["sha256"] != tgt[n]["sha256"]
            and not n.startswith("META-INF/")
        ]
        sigdiff = [
            n
            for n in names_b & names_t
            if base[n]["sha256"] != tgt[n]["sha256"] and n.startswith("META-INF/")
        ]
        added = sorted(names_t - names_b)
        removed = sorted(names_b - names_t)
        print(f"\n===== {target}")
        print(f"  条目 {len(tgt)} | 内容一致 {len(same)} | 内容变化(非签名) {len(diff)} | 签名区变化 {len(sigdiff)}")
        print(f"  新增 {len(added)} | 删除 {len(removed)}")
        for n in diff:
            print(f"    [改] {n}  {base[n]['size']:,} -> {tgt[n]['size']:,}")
        for n in added:
            print(f"    [增] {n}  {tgt[n]['size']:,} 方法 {tgt[n]['method']}")
        for n in removed:
            print(f"    [删] {n}  {base[n]['size']:,}")
        # 分类汇总
        groups = {}
        for n in diff + added + removed:
            key = n.split("/")[0]
            groups[key] = groups.get(key, 0) + 1
        print(f"  受影响顶层目录: {json.dumps(groups, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
