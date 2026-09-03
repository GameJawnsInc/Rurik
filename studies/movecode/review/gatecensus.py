#!/usr/bin/env python3
"""The gates' row census for one gamesrv capture (RUN-1zAB's readout).

    python studies/movecode/review/gatecensus.py                 # newest capture
    python studies/movecode/review/gatecensus.py vault/captures/gamesrv/authsrv-<stamp>-c1.jsonl

Counts, from the server's own rows, everything a `--kbd-lead` run must report
beside its separation number: the heading arm's verdicts (fired / refused, the
lead's source and clip reason -- `fence-shut` is the 1z-aa gate degrading a
lead), the held re-aims (1z-y), the lead kills (1z-y), the fence tracker's
re-arms (1z-aa), the AgTrack guard's rows (1z-s), every 0x002C by sender, and
the wire labels. A ZERO in any row is zero exposure for that gate, not a pass.
Read-only; the vault is found through vaultpath.
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))


def newest():
    import vaultpath
    hits = sorted(glob.glob(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "authsrv-*-c1.jsonl")))
    if not hits:
        raise SystemExit("no gamesrv captures in the vault")
    return hits[-1]


def census(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    C = collections.OrderedDict((k, collections.Counter()) for k in (
        "heading arm (arm, fired, reason, lead_src, lead_clip_why)",
        "held re-aims (kind, act/reason)", "lead kills (act, why, matured)",
        "fence tracker (act, by)", "agtrack guard (kind, code, why)",
        "0x002C by sender", "wire labels"))
    span = (rows[0]["t"], rows[-1]["t"]) if rows else (0, 0)
    for r in rows:
        k = str(r.get("kind", ""))
        if k == "grant_verdict" and r.get("arm") == "zero-lead":
            C["heading arm (arm, fired, reason, lead_src, lead_clip_why)"][
                (r.get("arm"), r.get("fired"), r.get("reason"),
                 r.get("lead_src"), r.get("lead_clip_why"))] += 1
        elif k == "heading_hold":
            C["held re-aims (kind, act/reason)"][(k, r.get("act") or r.get("reason"))] += 1
        elif k == "kbd_leg":
            C["lead kills (act, why, matured)"][
                (r.get("act"), r.get("why") or r.get("by"), r.get("matured"))] += 1
        elif k == "fence":
            C["fence tracker (act, by)"][(r.get("act"), r.get("by"))] += 1
        elif k.startswith("agtrack"):
            C["agtrack guard (kind, code, why)"][(k, r.get("code"), r.get("why"))] += 1
        elif k == "sent" and r.get("opcode") == 0x2C:
            C["0x002C by sender"][str(r.get("label", ""))[:28].split(" 0x002C")[0]] += 1
        if k == "sent" and r.get("opcode") in (0x29, 0x2B):
            lab = str(r.get("label", ""))
            for tag in ("KBD LEAD", "KBD SPEED-TRUTH", "KBD STOP-ECHO", "ZERO LEAD",
                        "AGENT_MOVE_TO_POINT", "router"):
                if tag in lab:
                    C["wire labels"][tag] += 1
                    break
    return span, C


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else newest()
    span, C = census(path)
    print(f"{os.path.basename(path)}  span {span[1] - span[0]:.0f} s")
    for name, ctr in C.items():
        print(f"  {name}")
        if not ctr:
            print("      (none -- zero exposure)")
        for key, n in ctr.most_common():
            print(f"      {n:4d}  {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
