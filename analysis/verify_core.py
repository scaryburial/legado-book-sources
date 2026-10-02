import hashlib, zipfile, sys
sys.stdout.reconfigure(encoding="utf-8")
base = zipfile.ZipFile(r"C:\Users\Administrator\Downloads\io.legado.app.release.apk")
def h(z,n): return hashlib.sha256(z.read(n)).hexdigest()
check = ["AndroidManifest.xml","resources.arsc","classes.dex","classes2.dex","classes3.dex","classes4.dex",
         "lib/arm64-v8a/libc++_shared.so","lib/arm64-v8a/librhino.so"]
for apk in ["阅读APP-内置主流书源.apk","阅读APP-内置成人向书源.apk"]:
    t = zipfile.ZipFile(apk)
    print(f"===== {apk}")
    names = set(base.namelist())
    for n in sorted(x for x in t.namelist() if x.startswith("lib/")):
        same = n in names and h(base,n)==h(t,n)
        print(f"  lib {n:<45} 与官方一致={same}")
    for n in sorted(x for x in t.namelist() if x.startswith("classes") and x.endswith(".dex")):
        same = n in names and h(base,n)==h(t,n)
        print(f"  dex {n:<45} 与官方一致={same}  sha256={h(t,n)[:16]}...")
    for n in ["AndroidManifest.xml","resources.arsc"]:
        print(f"  res {n:<45} 与官方一致={h(base,n)==h(t,n)}")
    print(f"  assets/defaultData 条目:")
    for n in sorted(x for x in t.namelist() if x.startswith("assets/defaultData/")):
        same = n in names and h(base,n)==h(t,n)
        print(f"    {n:<50} 与官方一致={same}  大小={t.getinfo(n).file_size:,}")
