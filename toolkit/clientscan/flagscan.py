"""Scan the Guild Wars binaries for command-line flag strings, in both ASCII
and UTF-16LE, and report where each one lives. Read-only."""
import os, re, sys

GW = r"C:\gw"
TARGETS = [
    "authsrv", "bpserver", "portal", "email", "password", "character",
    "dsound", "windowed", "fullscreen", "noshader", "perf", "log",
    "diag", "image", "repair", "nopatchui", "mute", "dx9", "dx11",
    "loginsrv", "gamesrv", "authserver", "srv", "127.0.0.1", "localhost",
    "ncsoft", "plaync", "guildwars", "arena.net", "arenanet",
]

# Anything that looks like it could be a CLI switch the client parses.
FLAGISH = re.compile(rb"[\x20-\x7e]{3,40}")


def read(path):
    with open(path, "rb") as f:
        return f.read()


def find(blob, needle):
    hits = {}
    a = needle.encode("ascii")
    w = needle.encode("utf-16-le")
    hits["ascii"] = blob.count(a)
    hits["utf16"] = blob.count(w)
    return hits


def ascii_strings(blob, minlen=4):
    return set(m.group().decode("ascii", "replace")
               for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, blob))


def utf16_strings(blob, minlen=4):
    out = set()
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minlen, blob):
        out.add(m.group().decode("utf-16-le", "replace"))
    return out


bins = [f for f in os.listdir(GW)
        if f.lower().endswith((".exe", ".dll")) and
        os.path.getsize(os.path.join(GW, f)) < 400 * 1024 * 1024]

print("=" * 78)
print("TARGETED FLAG SCAN")
print("=" * 78)
for name in sorted(bins):
    path = os.path.join(GW, name)
    blob = read(path)
    found = []
    for t in TARGETS:
        h = find(blob, t)
        if h["ascii"] or h["utf16"]:
            found.append(f"{t}(a={h['ascii']},w={h['utf16']})")
    print(f"\n-- {name}  [{len(blob):,} bytes]")
    print("   " + (", ".join(found) if found else "(no target strings)"))

print()
print("=" * 78)
print("DASH-PREFIXED TOKENS (candidate command-line switches)")
print("=" * 78)
for name in sorted(bins):
    path = os.path.join(GW, name)
    blob = read(path)
    strs = ascii_strings(blob, 3) | utf16_strings(blob, 3)
    dashed = sorted(s for s in strs
                    if re.fullmatch(r"-{1,2}[A-Za-z][A-Za-z0-9_]{1,24}", s.strip()))
    if dashed:
        print(f"\n-- {name}")
        for d in dashed:
            print(f"   {d}")

print()
print("=" * 78)
print("HOSTNAME / URL-LOOKING STRINGS")
print("=" * 78)
host_re = re.compile(
    r"^(?:https?://)?[A-Za-z0-9][A-Za-z0-9\-.]{2,60}\."
    r"(?:com|net|org|io|gg|co|kr|eu)(?:[/:][\x21-\x7e]{0,60})?$")
for name in sorted(bins):
    path = os.path.join(GW, name)
    blob = read(path)
    strs = ascii_strings(blob, 6) | utf16_strings(blob, 6)
    hosts = sorted(set(s.strip() for s in strs if host_re.match(s.strip())))
    if hosts:
        print(f"\n-- {name}")
        for h in hosts[:60]:
            print(f"   {h}")
        if len(hosts) > 60:
            print(f"   ... +{len(hosts) - 60} more")
