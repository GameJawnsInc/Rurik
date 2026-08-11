"""Locate the wide-string 'authsrv' in Gw.exe and dump the contiguous wide-string
neighbourhood around it. Command-line argument name tables are almost always laid
out contiguously by the compiler, so the neighbours ARE the flag list. Read-only."""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pinned  # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool
# in this directory. This used to be `C:\gw\Gw.exe`, the live install.
PATH, WHY = pinned.find()
print(f"client: {PATH}\n        ({WHY})\n")
blob = open(PATH, "rb").read()

needle = "authsrv".encode("utf-16-le")
idx = blob.find(needle)
print(f"Gw.exe = {len(blob):,} bytes")
print(f"'authsrv' (utf-16le) at file offset 0x{idx:x} ({idx:,})\n")
if idx < 0:
    sys.exit("not found")

# Walk out from the hit collecting every printable UTF-16LE run in a window.
LO, HI = max(0, idx - 6000), min(len(blob), idx + 6000)
window = blob[LO:HI]

runs = []
for m in re.finditer(rb"(?:[\x20-\x7e]\x00){2,}", window):
    s = m.group().decode("utf-16-le")
    runs.append((LO + m.start(), s))

print("=" * 76)
print("CONTIGUOUS WIDE-STRING NEIGHBOURHOOD (+/- 6 KB around 'authsrv')")
print("=" * 76)
for off, s in runs:
    mark = "  <<<< AUTHSRV" if s == "authsrv" else ""
    print(f"0x{off:08x}  {s!r}{mark}")

# Also: every wide string in the whole binary that looks like a bare lowercase
# identifier of the kind used for CLI switches, so we can see the full set.
print()
print("=" * 76)
print("ALL BARE LOWERCASE WIDE IDENTIFIERS IN Gw.exe (candidate switch names)")
print("=" * 76)
cand = {}
for m in re.finditer(rb"(?:[\x20-\x7e]\x00){3,}", blob):
    s = m.group().decode("utf-16-le")
    if re.fullmatch(r"[a-z][a-z0-9_]{2,20}", s):
        cand.setdefault(s, m.start())
for s in sorted(cand):
    print(f"0x{cand[s]:08x}  {s}")
print(f"\n({len(cand)} candidates)")
