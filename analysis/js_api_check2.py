import sys, re
sys.stdout.reconfigure(encoding="utf-8")
d = open("analysis/classes.dex","rb").read()
for pat in [b"androidId\x00", b"androidID\x00", b"getAndroidId\x00", b"deviceId\x00", b"androidId()"]:
    print(pat, d.count(pat))
# 找出所有以 androidId 结尾、前一个字节为长度前缀的 dex string（粗略）
for m in re.finditer(rb"androidId\x00", d):
    print("  命中偏移", m.start())
