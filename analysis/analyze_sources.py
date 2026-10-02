import json, zipfile, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")

for apk in ["阅读APP-内置主流书源.apk", "阅读APP-内置成人向书源.apk"]:
    z = zipfile.ZipFile(apk)
    raw = z.read("assets/defaultData/bookSources.json")
    data = json.loads(raw.decode("utf-8"))
    print(f"===== {apk}")
    print(f"  书源条数: {len(data)}   JSON 字节: {len(raw):,}")
    schemes = collections.Counter()
    hosts = collections.Counter()
    js_sources = 0
    js_blocks = 0
    http_only = 0
    for it in data:
        u = it.get("bookSourceUrl") or ""
        m = re.match(r"([a-zA-Z]+)://([^/]+)", u)
        if m:
            schemes[m.group(1).lower()] += 1
            hosts[m.group(2).lower()] += 1
        blob = json.dumps(it, ensure_ascii=False)
        n = len(re.findall(r"<js>|@js:|java\.", blob))
        if n:
            js_sources += 1
            js_blocks += n
        if (it.get("bookSourceUrl") or "").startswith("http://"):
            http_only += 1
    print(f"  协议分布: {dict(schemes)}")
    print(f"  明文 http:// 书源: {http_only}")
    print(f"  含 JS 规则的书源: {js_sources} (JS 片段 {js_blocks} 处)")
    print("  域名 Top15:")
    for h, c in hosts.most_common(15):
        print(f"    {c:5d}  {h}")
