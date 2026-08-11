"""Mine the Guild Wars binaries for protocol-shaped symbol strings.

Near the argument table we already saw 'GcAuthCmdSendFriendUpdate' and "'Auth" —
which means the client carries human-readable names for its own protocol
commands. If that generalises, the binary is self-documenting about a large part
of the message namespace, and that is worth far more than a hex dump.

Read-only. Reports NAMES and COUNTS only; copies no code and no asset bytes.
"""
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pinned  # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool
# in this directory; the login DLL is taken from the same snapshot rather
# than from a second hardcoded path, so both files are always the same build.
EXE, WHY = pinned.find()
FILES = [EXE, os.path.join(os.path.dirname(EXE), "GwLoginClient.dll")]
print(f"client: {EXE}\n        ({WHY})\n")

# Patterns for things that look like engine/protocol identifiers.
PATTERNS = {
    "GcCmd (game client command)": re.compile(r"^Gc[A-Z][A-Za-z0-9_]{3,60}$"),
    "GsCmd (game server command)": re.compile(r"^Gs[A-Z][A-Za-z0-9_]{3,60}$"),
    "Cmd* / *Cmd*":                re.compile(r"^[A-Za-z][A-Za-z0-9_]*Cmd[A-Za-z0-9_]*$"),
    "Msg* / *Msg*":                re.compile(r"^[A-Za-z][A-Za-z0-9_]*Msg[A-Za-z0-9_]*$"),
    "Packet*":                     re.compile(r"^[A-Za-z0-9_]*[Pp]acket[A-Za-z0-9_]*$"),
    "*Srv* / *Server*":            re.compile(r"^[A-Za-z][A-Za-z0-9_]*(Srv|Server)[A-Za-z0-9_]*$"),
    "Auth*":                       re.compile(r"^[A-Za-z0-9_]*Auth[A-Za-z0-9_]*$"),
    "*Stream* / *Session*":        re.compile(r"^[A-Za-z][A-Za-z0-9_]*(Stream|Session)[A-Za-z0-9_]*$"),
}


def strings(blob, minlen=5):
    out = set()
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, blob):
        out.add(m.group().decode("ascii", "replace"))
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minlen, blob):
        out.add(m.group().decode("utf-16-le", "replace"))
    return out


for path in FILES:
    blob = open(path, "rb").read()
    strs = strings(blob)
    # split on whitespace/punctuation so identifiers embedded in format strings surface too
    toks = set()
    for s in strs:
        toks.add(s)
        for t in re.split(r"[^A-Za-z0-9_]+", s):
            if len(t) >= 5:
                toks.add(t)

    print("=" * 78)
    print(f"{path}   [{len(blob):,} bytes, {len(strs):,} raw strings, {len(toks):,} tokens]")
    print("=" * 78)
    for label, pat in PATTERNS.items():
        hits = sorted(t for t in toks if pat.match(t))
        print(f"\n--- {label}: {len(hits)} ---")
        for h in hits[:120]:
            print(f"    {h}")
        if len(hits) > 120:
            print(f"    ... +{len(hits) - 120} more")
    print()
