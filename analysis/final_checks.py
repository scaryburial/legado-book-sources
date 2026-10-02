import json, zipfile, sys
sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile("阅读APP-内置主流书源.apk")
data = json.loads(z.read("assets/defaultData/bookSources.json").decode("utf-8"))
for it in data:
    if it.get("bookSourceType") == 1000:
        print("异常 type=1000:", it.get("bookSourceName"), it.get("bookSourceUrl"))
d = open("analysis/classes.dex","rb").read()
for kw in [b"defaultData", b"bookSources.json", b"replaceRule.json", b"firebase", b"crashlytics"]:
    print(kw.decode(), "->", d.count(kw))
