#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在不动其它任何条目的前提下，替换 APK 里的内置书源/规则，然后重新打包。
保留每个 entry 原有的压缩方式与 extra 字段；resources.arsc 保持 stored，
后续由 zipalign 负责 4 字节对齐。
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent            # legado-collect/
SRC_APK = Path(r"C:/Users/Administrator/Downloads/io.legado.app.release.apk")
OUT_APK = HERE / "unsigned.apk"

ADULT_DIR = ROOT / "out-adult" / "00-全量去重"
REPLACE_RULE = ROOT.parent / "净化规则.json"


def load_adult_sources():
    items = []
    for p in sorted(ADULT_DIR.glob("part*.json")):
        items.extend(json.loads(p.read_text(encoding="utf-8")))
    # 去掉自定义排序字段里可能存在的负数顺序，按名称重排，保证导入后顺序稳定
    for i, it in enumerate(items):
        it["customOrder"] = i
    return items


def main() -> int:
    sources = load_adult_sources()
    payload = json.dumps(sources, ensure_ascii=False, indent=1).encode("utf-8")
    print(f"内置书源: {len(sources)} 条, {len(payload):,} 字节")

    rules = json.loads(REPLACE_RULE.read_text(encoding="utf-8"))
    rule_bytes = json.dumps(rules, ensure_ascii=False, indent=1).encode("utf-8")
    print(f"内置净化规则: {len(rules)} 条, {len(rule_bytes):,} 字节")

    replace = {
        "assets/defaultData/bookSources.json": payload,
        "assets/defaultData/replaceRule.json": rule_bytes,
    }

    src = zipfile.ZipFile(SRC_APK)
    with zipfile.ZipFile(OUT_APK, "w", allowZip64=True) as dst:
        for info in src.infolist():
            data = replace.pop(info.filename, None)
            if data is None:
                data = src.read(info.filename)
            new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new.compress_type = info.compress_type
            new.external_attr = info.external_attr
            new.internal_attr = info.internal_attr
            new.create_system = info.create_system
            new.comment = info.comment
            new.extra = info.extra
            # 目录条目
            if info.is_dir():
                dst.writestr(new, b"")
                continue
            dst.writestr(new, data)
        # 原来没有的条目（如 replaceRule.json）补进去
        for name, data in replace.items():
            new = zipfile.ZipInfo(name)
            new.compress_type = zipfile.ZIP_DEFLATED
            new.external_attr = 0o644 << 16
            dst.writestr(new, data)

    src.close()
    print(f"已生成 {OUT_APK}  ({OUT_APK.stat().st_size/1024/1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
