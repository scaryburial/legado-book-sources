import json, zipfile, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile("阅读APP-内置主流书源.apk")
rules = json.loads(z.read("assets/defaultData/replaceRule.json").decode("utf-8"))
for r in rules:
    print(f"  [{r.get('group')}] {r.get('name')}  scope={r.get('scope')} regex={r.get('isRegex')} enabled={r.get('isEnabled')}  pattern={str(r.get('pattern'))[:60]!r} -> {str(r.get('replacement'))[:30]!r}")
