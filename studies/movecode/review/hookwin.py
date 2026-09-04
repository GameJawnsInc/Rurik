#!/usr/bin/env python3
"""Dump a movehook capture around one client destination (MOVECODE-1z-be).

    python studies/movecode/review/hookwin.py <movehook.bin> --anchor 10358,8287
    python studies/movecode/review/hookwin.py <movehook.bin> --anchor 10358,8287 --before 4700 --after 700 --skip inputeval

WHY. leadtap.py answers "what did the pathfinder say around a GRANT"; this answers
"what did every tapped site do around one CLIENT-ISSUED destination" -- the record
stream itself, in order, with the return address rebased to the pinned image so a
reader can name the caller (0x00600333 is the arrival tick's halt, 0x0060189E the
avoidance solver's, 0x00602B79 the position installer's, ...). 1z-be was read off
exactly this print: the same S press ends in `chcli_advance` in one run and in
`resume_arm` returning to ChCliBase case 4 (0x0081B53C) in the other.

The anchor is the `agapi_setdest` record whose pt_a is within 0.6 u of --anchor;
times are milliseconds relative to it (GetTickCount granularity, ~16 ms). The
return address is rebased with the capture's own module base against
readhook.static_base(), never with a hard-coded delta. Stdlib only, read-only.
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan", "movehook"))


def _f(dw):
    return struct.unpack("<f", struct.pack("<I", dw))[0]


def pt(v):
    if not v or v[0] == 0:
        return "-"
    return "(%.2f,%.2f)" % (_f(v[0]), _f(v[1]))


def find_anchor(cap, names, x, y, tol=0.6):
    sd = names.index("agapi_setdest")
    for r in cap.recs:
        if r["site"] == sd and r.get("have_pts"):
            a = r["pt_a"]
            if abs(_f(a[0]) - x) < tol and abs(_f(a[1]) - y) < tol:
                return r
    return None


def fmt(r, names, delta, t0):
    n = names[r["site"]] if r["site"] < len(names) else "site%d" % r["site"]
    fl = r.get("flags", 0)
    bits = ("W" if fl & (1 << 18) else ".") + ("I" if fl & (1 << 17) else ".") + ("S" if fl & (1 << 19) else ".")
    line = "%+6d %-14s ret %08X w%s id %-3s fl %s stop %-6s pt %s tgt %s" % (
        r["tick"] - t0, n, r["retaddr"] - delta, r.get("world", "?"), r.get("id"), bits,
        r.get("stop"), pt(r.get("point")), pt(r.get("target")))
    if r.get("have_pts"):
        line += " A %s" % pt(r.get("pt_a"))
    v = r.get("vel")
    if v and (v[0] or v[1]):
        line += " v(%.0f,%.0f)" % (_f(v[0]), _f(v[1]))
    if n == "mapfindpath":
        line += " out %s/%s" % (r.get("have_out"), r.get("out_count"))
    if r.get("have_gate"):
        line += " gate %x/%x" % (r.get("gate_flags"), r.get("gate_status"))
    if r.get("have_src"):
        line += " src id %s w%s pt %s" % (r.get("src_id"), r.get("src_world"), pt(r.get("src_point")))
    line += " args %x %x %x" % (r["arg1"], r["arg2"], r["arg3"])
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bin")
    ap.add_argument("--anchor", required=True, help="X,Y of the client-issued destination (agapi_setdest pt_a)")
    ap.add_argument("--before", type=int, default=250, help="ms before the anchor")
    ap.add_argument("--after", type=int, default=700, help="ms after the anchor")
    ap.add_argument("--skip", default="", help="comma-separated site names to omit (e.g. inputeval)")
    ap.add_argument("--only", default="", help="comma-separated site names to keep")
    a = ap.parse_args()
    import readhook
    cap = readhook.Capture(a.bin)
    names = readhook.site_names(cap)
    delta = cap.base - readhook.static_base()
    x, y = (float(s) for s in a.anchor.split(","))
    anchor = find_anchor(cap, names, x, y)
    if anchor is None:
        print("no agapi_setdest record within 0.6 u of (%g, %g)" % (x, y))
        return 1
    skip = set(s for s in a.skip.split(",") if s)
    only = set(s for s in a.only.split(",") if s)
    t0 = anchor["tick"]
    ca, cb, _ = cap.sidecar()
    print("%s: v%d, %d records (%d partial), base %08X (delta %+X), control A %s B %s" % (
        os.path.basename(a.bin), cap.version, cap.stored, cap.partial, cap.base, delta,
        "FIRED" if ca else ca, "FIRED" if cb else cb))
    print("anchor: agapi_setdest -> (%g, %g) at tick %d (seq %d)" % (x, y, t0, anchor["seq"]))
    n = 0
    for r in cap.recs:
        dt = r["tick"] - t0
        if dt < -a.before or dt > a.after:
            continue
        nm = names[r["site"]] if r["site"] < len(names) else "site%d" % r["site"]
        if nm in skip or (only and nm not in only):
            continue
        print(fmt(r, names, delta, t0))
        n += 1
    print("%d records" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
