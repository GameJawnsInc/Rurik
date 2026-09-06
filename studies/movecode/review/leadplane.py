#!/usr/bin/env python3
"""Is a keyboard lead ever GRANTED off the mover's own plane? (MOVECODE-1z-cd)

    python studies/movecode/review/leadplane.py            # the corpus census
    python studies/movecode/review/leadplane.py --check    # with sec.1z-cd's bars
    python studies/movecode/review/leadplane.py <gamesrv.jsonl> ...   # named captures

THE QUESTION, and it is somebody's proposed fix. NPCTRACK's wall case reads: the
player stands against the staircase side, presses a key, the server grants a
`0x0029` lead toward the stair tread, and the client -- whose own navmesh has no
path from the ground to the tread through the wall -- refuses the whole leg and
stands still for five seconds. The proposed repair was to make the lead REFUSE or
SHORTEN a point whose plane differs from the mover's when no same-plane route
exists.

WHAT THIS MEASURES, off the capture and our own navmesh -- no replay, no simulator:
for every `0x003D` report that armed a keyboard lead, the plane of the point the
server ACTUALLY GRANTED (the `kbd_leg` arm row's own dest, which is what went on
the wire) against the plane of the report it was anchored at. A grant on a
different plane is the proposed fix's precondition. Counting them is therefore
counting how often that fix could ever fire.

THE SEGMENTATION, and it is what makes the answer readable. The gamesrv jsonl
carries no argv (REALFIX-Q8), so the arm has to be inferred from the rows. The
word `plane-seam` is computed ONLY inside `a2_clip_lead`'s `if clipped and plane
is not None`, so a capture containing one had `A2_LEAD_PLANE_CLIP` ON. That is a
SUFFICIENT condition and not a necessary one -- a run with the term on that never
aimed at a seam shows none -- so the two segments are "term provably ON" and
"unknown", never "term provably OFF". `A2_LEAD_PLANE_CLIP` and the word both
shipped in 42f6009 on 2026-09-04, and the corpus splits on that commit to the
capture.

THE POSITIVE CONTROL IS THE POINT. A census that reports zero because it cannot
see the thing is worth nothing, so the same detector is run over the captures
recorded BEFORE the term shipped, where the defect is known to exist. It must
find them. Only then does the zero on the other side mean anything.

Read-only. Stdlib only. Needs the vault (the captures are the owner's own) and the
navmesh for the captured map; both refuse loudly rather than printing a flattering
zero.
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in ("toolkit", os.path.join("toolkit", "authsrv"),
           os.path.join("toolkit", "mapdata")):
    sys.path.insert(0, os.path.join(ROOT, _p))

import vaultpath                                            # noqa: E402

# The bars sec.1z-cd registered off the 2026-09-06 census. FLOORS on what must be
# found and CEILINGS on what must not exist, so a growing corpus can only move
# them the safe way -- [[corpus-counts-redden]]: never pin an exact value on a
# corpus that gains captures. The ON segment gains a capture every run; the
# pre-term segment is historical and fixed.
FLOOR_PAIRS = 950         # report -> grant pairs scored in total
FLOOR_MOVING = 450        # of them, NON-TRIVIAL: the grant is not the report itself
FLOOR_ON_MOVING = 190     # of THOSE, under a plane clip that is actually in force
CEIL_ON_CROSS = 0         # and NONE of those may be granted off the mover's plane
FLOOR_OFF_CROSS = 40      # the positive control: the detector must still find the
                          # defect on the arms where the clip is NOT in force, or
                          # its zero above is indistinguishable from a broken census
FLOOR_OFF_MOVING = 240    # scored on that side, so the control is not one capture


def _rows(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _mesh_for(rows, cache):
    """The navmesh for the map this capture was recorded on, or None with a reason."""
    import authsrv
    mid = None
    for r in rows:
        if r.get("kind") == "version":
            mid = r.get("map_id")
            break
    if mid is None:
        return None, "no version row -- the capture does not name its map"
    if mid in cache:
        return cache[mid], None
    cfg = authsrv.MAP_STATIC_CONFIG.get(mid)
    if cfg is None:
        cache[mid] = None
        return None, f"map {mid} has no static config"
    pm = authsrv.load_pathmap(cfg[0])
    cache[mid] = pm
    return pm, None if pm is not None else f"no navmesh for map {mid}"


def arm_of(rows):
    """(segment, flags) -- which lead-clip arm this capture was recorded on.

    Read off the capture's own `flags` row, never inferred. "in force" is
    PLANE_CLIP and not SEAM_CLIP, because `a2_clip_lead`'s `elif
    A2_LEAD_SEAM_CLIP` branch takes the seam walk INSTEAD of the plane clip
    (authsrv.py, the `elif ... hasattr(pm, "seam_clip")` arm) -- so a run with
    both flags true is not running the term under test.
    """
    for r in rows:
        if r.get("kind") != "flags":
            continue
        if "A2_LEAD_PLANE_CLIP" not in r:
            return "pre-flags", None
        f = (bool(r.get("A2_LEAD_PLANE_CLIP")),
             bool(r.get("A2_LEAD_ORIGIN_SEAM")),
             bool(r.get("A2_LEAD_SEAM_CLIP")))
        return ("on" if (f[0] and not f[2]) else "off"), f
    return "pre-flags", None


def score(rows, pm):
    """(segment, pairs) for one capture. Pure over the rows and the mesh."""
    seg, _flags = arm_of(rows)
    pairs = []
    pending, verdict = None, None
    for r in rows:
        kind = r.get("kind")
        if kind == "decoded" and r.get("opcode") == 61:
            v = r.get("values") or []
            if len(v) < 5:
                continue
            # The report's own plane WORD is the `prefer`, exactly as
            # `a2_clip_lead` passes `state["plane"]` -- a different preference
            # would be scoring a different function.
            pending = {"x": float(v[1][0]), "y": float(v[1][1]), "word": v[2]}
            verdict = None
        elif kind == "grant_verdict":
            verdict = r
        elif kind == "kbd_leg" and r.get("act") == "arm" and pending is not None:
            dest = r.get("dest")
            if dest is not None:
                rx, ry = pending["x"], pending["y"]
                gx, gy = float(dest[0]), float(dest[1])
                op = pm.plane_at(rx, ry, prefer=pending["word"])
                gp = pm.plane_at(gx, gy, prefer=op)
                pairs.append({
                    "t": r.get("t"), "rx": rx, "ry": ry, "gx": gx, "gy": gy,
                    "op": op, "gp": gp,
                    "why": (verdict or {}).get("lead_clip_why"),
                    "leg_plane": r.get("plane"),
                    "reach": math.hypot(gx - rx, gy - ry),
                    # A zero-lead grants the report back to the client, so its
                    # destination IS the origin and cross-plane is impossible by
                    # construction. Counting it as a scored trial halves the rate.
                    "moving": math.hypot(gx - rx, gy - ry) > 1e-9,
                    # BOTH planes must be nameable for the comparison to mean
                    # anything: an unnameable plane is the mesh saying nothing,
                    # which is not the same claim as "a different plane".
                    "cross": (op is not None and gp is not None and op != gp)})
            pending = None
    return seg, pairs


def main(argv):
    check = "--check" in argv
    named = [a for a in argv if not a.startswith("-")]
    if named:
        files = named
    else:
        try:
            base = vaultpath.require_dir("captures", "gamesrv")
        except Exception as exc:                              # noqa: BLE001
            print(f"[SKIP] no vault: {exc}")
            return 0 if not check else 1
        files = sorted(glob.glob(os.path.join(base, "*.jsonl")))
    cache = {}
    seg_pairs = {"on": [], "off": [], "pre-flags": []}
    percap, refused, used = [], [], 0
    for path in files:
        rows = _rows(path)
        if not any(r.get("kind") == "kbd_leg" for r in rows):
            continue
        pm, why = _mesh_for(rows, cache)
        if pm is None:
            refused.append((os.path.basename(path), why))
            continue
        seg, pairs = score(rows, pm)
        _s, flags = arm_of(rows)
        seg_pairs[seg].extend(pairs)
        used += 1
        mv = [p for p in pairs if p["moving"]]
        percap.append((os.path.basename(path), seg, flags, len(pairs), len(mv),
                       sum(1 for p in mv if p["cross"])))
    for name, why in refused:
        print(f"  [SKIP] {name}: {why}")

    allp = [p for seg in seg_pairs.values() for p in seg]
    if not allp:
        print("  [SKIP] nothing to score")
        return 0 if not check else 1
    moving = [p for p in allp if p["moving"]]
    print(f"\n{used} captures with keyboard-lead rows; {len(allp)} report->grant "
          f"pairs, of which {len(moving)} are NON-TRIVIAL (the grant is not the "
          f"report itself)")

    print("\nper capture   (arm read from the capture's own `flags` row)")
    print(f"  {'capture':<36} {'arm':<10} {'flags':<18} {'pairs':>6} {'moving':>7} {'cross':>6}")
    for name, seg, flags, n, nm, c in percap:
        fs = ("-" if flags is None
              else f"clip={int(flags[0])} seam={int(flags[2])} org={int(flags[1])}")
        flag = "  <-- CROSS-PLANE IN FORCE" if (c and seg == "on") else ""
        print(f"  {name[:36]:<36} {seg:<10} {fs:<18} {n:6d} {nm:7d} {c:6d}{flag}")

    print("\n=== THE PROPOSED FIX'S PRECONDITION: a grant off the mover's plane ===")
    print("  (zero-distance leads excluded: their destination IS the report, so")
    print("   cross-plane is impossible by construction and counting them halves")
    print("   the rate -- the subcount shape this repo keeps being bitten by)")
    rows_on = [p for p in seg_pairs["on"] if p["moving"]]
    rows_off = [p for p in seg_pairs["off"] if p["moving"]]
    rows_pre = [p for p in seg_pairs["pre-flags"] if p["moving"]]
    for label, rs in (("plane clip IN FORCE   ", rows_on),
                      ("clip reverted/bypassed", rows_off),
                      ("older than the flags  ", rows_pre)):
        cross = [p for p in rs if p["cross"]]
        pc = (100.0 * len(cross) / len(rs)) if rs else 0.0
        print(f"  {label} {len(rs):5d} moving grants   {len(cross):4d} cross-plane"
              f"  ({pc:.1f}%)")
    onx = [p for p in rows_on if p["cross"]]
    if onx:
        print("\n  the ones under the shipped arm -- the fix's whole scope:")
        for p in onx[:20]:
            print(f"    t={p['t']:7.2f} ({p['rx']:.1f},{p['ry']:.1f}) plane {p['op']}"
                  f" -> ({p['gx']:.1f},{p['gy']:.1f}) plane {p['gp']}"
                  f"  reach {p['reach']:6.1f}  why={p['why']}")
    else:
        print("\n  ZERO with the clip in force. The precondition is never true, so a")
        print("  guard on it could not fire once -- and the control below is what")
        print("  makes that zero mean something.")

    print("\n=== THE POSITIVE CONTROL: the same detector where the clip is NOT in force ===")
    ctrl = rows_off + rows_pre
    cx = [p for p in ctrl if p["cross"]]
    print(f"  {len(cx)} cross-plane grants of {len(ctrl)} moving, on the reverted, "
          f"seam-bypassed and pre-2026-09-04 arms")
    bywhy = {}
    for p in cx:
        bywhy[p["why"]] = bywhy.get(p["why"], 0) + 1
    for w, n in sorted(bywhy.items(), key=lambda kv: -kv[1]):
        print(f"    why={str(w):<12} {n}")
    for p in cx[:8]:
        print(f"    t={p['t']:7.2f} ({p['rx']:.1f},{p['ry']:.1f}) plane {p['op']}"
              f" -> ({p['gx']:.1f},{p['gy']:.1f}) plane {p['gp']}"
              f"  reach {p['reach']:6.1f}  why={p['why']}")

    print("\n=== the door each moving grant went out of, clip in force ===")
    bywhy = {}
    for p in rows_on:
        d = bywhy.setdefault(p["why"], {"n": 0, "cross": 0})
        d["n"] += 1
        d["cross"] += 1 if p["cross"] else 0
    for w, d in sorted(bywhy.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {str(w):<20} n={d['n']:5d}   cross-plane={d['cross']}")

    if not check:
        return 0
    fails = []

    def bar(ok, label, got):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}  {got}")
        if not ok:
            fails.append(label)

    print("\n--check, against sec.1z-cd's registered figures")
    bar(len(allp) >= FLOOR_PAIRS, f"at least {FLOOR_PAIRS} report->grant pairs",
        len(allp))
    bar(len(moving) >= FLOOR_MOVING,
        f"at least {FLOOR_MOVING} of them non-trivial", len(moving))
    bar(len(rows_on) >= FLOOR_ON_MOVING,
        f"at least {FLOOR_ON_MOVING} moving grants with the clip IN FORCE",
        len(rows_on))
    bar(len(onx) <= CEIL_ON_CROSS,
        f"at most {CEIL_ON_CROSS} of those granted off the mover's plane (the "
        f"claim sec.1z-cd rests on; NON-zero here means the refutation has "
        f"expired and the guard is back on the table)", len(onx))
    bar(len(ctrl) >= FLOOR_OFF_MOVING,
        f"at least {FLOOR_OFF_MOVING} moving grants on the control side",
        len(ctrl))
    bar(len(cx) >= FLOOR_OFF_CROSS,
        f"the POSITIVE CONTROL: the same detector still finds at least "
        f"{FLOOR_OFF_CROSS} cross-plane grants where the clip is not in force "
        f"(a census that finds none here is measuring nothing, and the zero "
        f"above would be worthless)", len(cx))
    print(f"\n{'ALL BARS MET' if not fails else str(len(fails)) + ' BAR(S) MISSED'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
