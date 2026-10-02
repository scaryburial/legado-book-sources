import json, zipfile, re, sys, collections, re as _re
sys.stdout.reconfigure(encoding="utf-8")

classes = collections.Counter()
hosts_lo = collections.Counter()
suspicious = []
for apk in ["阅读APP-内置主流书源.apk", "阅读APP-内置成人向书源.apk"]:
    z = zipfile.ZipFile(apk)
    data = json.loads(z.read("assets/defaultData/bookSources.json").decode("utf-8"))
    rules = json.loads(z.read("assets/defaultData/replaceRule.json").decode("utf-8"))
    print(f"===== {apk}")
    print(f"  净化规则: {len(rules)} 条; 字段示例: {list(rules[0].keys())}")
    local_hits = []
    js_api = collections.Counter()
    for it in data:
        url = (it.get("bookSourceUrl") or "")
        if _re.search(r"127\.0\.0\.1|localhost|0\.0\.0\.0|10\.|192\.168\.|:1[0-9]{3}/", url):
            local_hits.append(url)
        blob = json.dumps(it, ensure_ascii=False)
        for c in _re.findall(r"java\.[a-zA-Z_.]+", blob):
            classes[c] += 1
        for a in _re.findall(r"(?:source\.|java\.|)(?:getString|put|setVariable|getVariable|ajax|connect|toast|log|base64|md5|aes|des|digest)\b", blob):
            js_api[a] += 1
        # 规则里出现权限/隐私相关字符串
        for kw in ["deviceId", "IMEI", "getImei", "getMacAddress", "android_id", "SubscriberId", "Runtime", "exec("]:
            if kw in blob:
                suspicious.append((it.get("bookSourceName"), kw, url))
    print(f"  内网/回环节点书源: {len(local_hits)}")
    for h in local_hits[:10]: print(f"    {h}")
    print(f"  java.* 类引用 Top10: {classes.most_common(10)}")
    print(f"  高权限/隐私关键词命中: {len(suspicious)}")
    for s in suspicious[:10]: print(f"    {s}")
    print(f"  JS 常用 API: {js_api.most_common(12)}")
    print()
