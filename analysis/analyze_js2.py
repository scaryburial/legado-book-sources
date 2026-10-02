import json, zipfile, re, sys, collections, ipaddress
sys.stdout.reconfigure(encoding="utf-8")

def is_private(host):
    h = host.split(":")[0]
    if h in ("localhost",) or h.endswith(".local"): return True
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False

for apk in ["阅读APP-内置主流书源.apk", "阅读APP-内置成人向书源.apk"]:
    z = zipfile.ZipFile(apk)
    data = json.loads(z.read("assets/defaultData/bookSources.json").decode("utf-8"))
    print(f"===== {apk}  ({len(data)} 条)")
    priv, browser, ajax_ext, webbrowse = [], 0, 0, 0
    port_hits = []
    kw_hits = collections.defaultdict(list)
    for it in data:
        u = it.get("bookSourceUrl") or ""
        m = re.match(r"[a-zA-Z]+://([^/#]+)", u)
        if m and is_private(m.group(1)):
            priv.append((it.get("bookSourceName"), u))
        if m and re.search(r":\d{2,5}$", m.group(1)) and not m.group(1).endswith((":443",)):
            port_hits.append((it.get("bookSourceName"), u))
        blob = json.dumps(it, ensure_ascii=False)
        if "startBrowserAwait" in blob or "startBrowser(" in blob: browser += 1
        if "java.ajax" in blob: ajax_ext += 1
        for kw in ["deviceId", "IMEI", "imei", "android_id", "getMacAddress", "SubscriberId", "Runtime.", "exec("]:
            if kw in blob and len(kw_hits[kw]) < 3:
                i = blob.find(kw)
                kw_hits[kw].append((it.get("bookSourceName"), blob[max(0,i-90):i+90]))
    print(f"  真实内网/回环 URL: {len(priv)} {priv[:5]}")
    print(f"  非 443 自定义端口 URL: {len(port_hits)} {port_hits[:8]}")
    print(f"  含 java.ajax（脚本发网络请求）: {ajax_ext}")
    print(f"  含 startBrowserAwait/startBrowser（拉起浏览器）: {browser}")
    for kw, items in kw_hits.items():
        print(f"  --- 关键词 {kw!r} 示例 ---")
        for n, s in items:
            print(f"    [{n}] ...{s.replace(chr(10),' ')}...")
    print()
