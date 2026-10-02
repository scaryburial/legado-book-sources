import re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
lines = open("analysis/AndroidManifest.xmltree.txt", encoding="utf-8").read().splitlines()
comp_stack = []
cur = None
components = []
for i, ln in enumerate(lines):
    s = ln.strip()
    m = re.match(r"E: (activity|service|receiver|provider|activity-alias)(?: \(line=\d+\))?$", s)
    if m:
        cur = {"type": m.group(1), "name": None, "exported": None, "perm": None, "actions": [], "schemes": [], "authorities": None, "grant": None}
        components.append(cur); continue
    if cur is None:
        continue
    if re.match(r"E: (intent-filter|meta-data|data|category|grant-uri-permission)", s):
        if s.startswith("E: intent-filter") or s.startswith("E: meta-data"):
            if s.startswith("E: meta-data") and not s.startswith("E: meta-data "):
                pass
        continue
    m = re.search(r'android:name\(0x01010003\)="([^"]+)"', s)
    if m:
        v = m.group(1)
        if cur["name"] is None and not v.startswith("android.") and not v.startswith("com."):
            cur["name"] = v
        elif v.startswith("android.intent.action.") or v.startswith("android.intent.category."):
            cur["actions"].append(v)
        elif cur["perm"] is None:
            cur["perm"] = v
        continue
    m = re.search(r'android:exported\(0x01010010\)=(true|false)', s)
    if m: cur["exported"] = m.group(1); continue
    m = re.search(r'android:permission\(0x01010006\)="([^"]+)"', s)
    if m: cur["perm"] = m.group(1); continue
    m = re.search(r'android:authorities\(0x01010018\)="([^"]+)"', s)
    if m: cur["authorities"] = m.group(1); continue
    m = re.search(r'android:scheme\(0x01010027\)="([^"]+)"', s)
    if m and m.group(1) not in ("*",): cur["schemes"].append(m.group(1)); continue

print("导出组件（exported=true）:")
for c in components:
    if c["exported"] == "true":
        print(f"  [{c['type']}] {c['name']}  perm={c['perm']}  filters={sorted(set(c['actions']))[:4]} schemes={sorted(set(c['schemes']))} auth={c['authorities']}")
print()
print("全部组件数:", len(components), collections.Counter(c["type"] for c in components))
print()
print("Service 列表:")
for c in components:
    if c["type"] in ("service","receiver","provider"):
        print(f"  [{c['type']}] exported={c['exported']} {c['name']} perm={c['perm']}")
