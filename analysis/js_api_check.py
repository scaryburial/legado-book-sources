import sys, re
sys.stdout.reconfigure(encoding="utf-8")
d = open("analysis/classes.dex","rb").read()
for kw in [b"readFile", b"writeFile", b"getFile", b"delFile", b"unzipFile", b"getTxtFromFile", b"ajaxTest", b"getFromCache", b"sdkInt", b"getCookie", b"deleteCookie", b"setVariable", b"getVariable", b"longToast", b"toast", b"androidId", b"deviceInfo", b"getWifiName"]:
    print(f"  {kw.decode():<16} {d.count(kw)}")
i = d.find(b"androidId")
print("\nandroidId 上下文:")
for m in re.finditer(rb"androidId", d):
    seg = d[max(0,m.start()-70):m.start()+70]
    txt = "".join(chr(c) if 32 <= c < 127 else "·" for c in seg)
    print("   ", txt)
