#!/usr/bin/env python3
"""How far does the SERVER'S OWN model of the player walk on one heading? (MOVECODE-1z-cc)

    python studies/movecode/review/modelleg.py            # the corpus census
    python studies/movecode/review/modelleg.py --check    # the same, with sec.1z-cc's
                                                          # figures as pass/fail bars
    python studies/movecode/review/modelleg.py <gamesrv.jsonl> ...   # named captures

THE QUANTITY, and it never touches the wire. On a `0x003D` the server sets
`state["dest"] = clip_to_walkable(state["pos"] + vec2)` and the world tick walks
`state["pos"]` there at 288 u/s, clamping on arrival. The client reports again only
when its own chord trigger fires (~515 u) or the key is released -- so when the body
is BLOCKED and stops, no report comes, and the model walks the whole leg alone.
Every follow order, every leash test and every range check then reads that position.

WHAT IT MEASURES, off the capture and our own navmesh -- no replay, no simulator:

  (a) THE TWO CLIPPERS ON ONE RAY. For each `0x003D` that armed a keyboard lead, the
      model leg's endpoint under `pm.clip` WITHOUT the plane term (what shipped until
      2026-09-06) and WITH it, against the reach of the lead grant the same report
      produced -- which `a2_clip_lead` has clipped WITH the plane term since 1z-ap.
      The two are the same ray from the same origin at the same instant, so a
      disagreement is ours, not the mesh's.

  (b) THE COST, OBSERVED. At every `0x0047` stop report the capture records the drift
      between the client's own point and `state["pos"]`. Where that drift EQUALS the
      plane-blind model reach the body stood still through the entire leg and the
      number is the model's walk, verbatim -- no inference.

THE FIGURES sec.1z-cc quotes, and `--check` re-asserts them as floors and ceilings.

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

# The bars sec.1z-cc registered, off the 2026-09-06 census. They are FLOORS on the
# defect's exposure and CEILINGS on what the fix leaves, so the corpus growing can
# only move them the safe way -- [[corpus-counts-redden]]: never pin an exact value
# on a corpus that gains captures.
FLOOR_PAIRS = 700           # report -> lead pairs scored
FLOOR_CLIPPED = 400         # of which the mesh cut the lead short
FLOOR_BLIND_OVER = 25       # blind model leg ends past its own grant, on those
CEIL_AWARE_OVER = 8         # the plane term must leave far fewer
CEIL_AWARE_OVER_MAX = 5.0   # and none of them big
FLOOR_STILL = 25            # stop reports where the body never moved at all
FLOOR_STILL_P50 = 300.0     # their drift today, median
CEIL_FIXED_P50 = 250.0      # what the plane term must leave of it

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


def score(path, pm, step):
    """(pairs, stops) for one capture. Pure over the file and the mesh."""
    rows = _rows(path)
    pairs, stops = [], []
    # TWO consumers, ONE tracker -- and they must not eat each other's report. The
    # first draft cleared the pending heading on the lead arm, so every 0x0047 that
    # followed one found nothing and (b) scored 7 stop reports out of 193. The lead
    # arm and the stop report are different questions about the SAME 0x003D.
    pending, verdict = None, None
    for r in rows:
        kind = r.get("kind")
        if kind == "decoded" and r.get("opcode") == 61:
            v = r.get("values") or []
            if len(v) < 5:
                continue
            rx, ry = float(v[1][0]), float(v[1][1])
            if not pm.walkable(rx, ry):
                # The model's own suspension: standing off the mesh disables the
                # clip entirely, so there is no leg to score and counting one would
                # invent a comparison neither clipper made.
                pending, verdict = None, None
                continue
            raw = (rx + float(v[3][0]), ry + float(v[3][1]))
            plane = pm.plane_at(rx, ry, prefer=v[2])
            blind = pm.clip(rx, ry, raw[0], raw[1], step=step)
            aware = (blind if plane is None
                     else pm.clip(rx, ry, raw[0], raw[1], step=step, plane=plane))
            pending = {"x": rx, "y": ry, "t": r.get("t"),
                       "blind": math.hypot(blind[0] - rx, blind[1] - ry),
                       "aware": math.hypot(aware[0] - rx, aware[1] - ry)}
            verdict = None
        elif kind == "grant_verdict":
            verdict = r
        elif kind == "kbd_leg" and r.get("act") == "arm" and pending is not None:
            dest = r.get("dest") or [pending["x"], pending["y"]]
            pairs.append({
                "t": r.get("t"), "blind": pending["blind"],
                "aware": pending["aware"],
                "lead": math.hypot(float(dest[0]) - pending["x"],
                                   float(dest[1]) - pending["y"]),
                "clipped": bool((verdict or {}).get("lead_clipped")),
                "why": (verdict or {}).get("lead_clip_why")})
        elif (kind == "position_report" and r.get("source") == "0x0047"
              and pending is not None):
            stops.append({"t": r.get("t"), "drift": float(r.get("drift") or 0.0),
                          "blind": pending["blind"], "aware": pending["aware"],
                          "silence": (r.get("t") or 0.0) - (pending["t"] or 0.0)})
            pending, verdict = None, None
    return pairs, stops


def q(vals, p):
    if not vals:
        return float("nan")
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p * len(vals)))]


def main(argv):
    check = "--check" in argv
    named = [a for a in argv if not a.startswith("-")]
    import authsrv
    step = authsrv.COLLISION_STEP
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
    pairs, stops, used, refused = [], [], 0, []
    for path in files:
        rows_head = _rows(path)
        if not any(r.get("kind") == "kbd_leg" for r in rows_head):
            continue
        pm, why = _mesh_for(rows_head, cache)
        if pm is None:
            refused.append((os.path.basename(path), why))
            continue
        p, s = score(path, pm, step)
        pairs.extend(p)
        stops.extend(s)
        used += 1
    for name, why in refused:
        print(f"  [SKIP] {name}: {why}")
    print(f"\n{used} captures with keyboard-lead rows; {len(pairs)} report->lead "
          f"pairs, {len(stops)} stop reports  (clip step {step})")
    if not pairs:
        print("  [SKIP] nothing to score")
        return 0 if not check else 1

    clipped = [x for x in pairs if x["clipped"]]
    clear = [x for x in pairs if not x["clipped"]]
    print("\n(a) THE TWO CLIPPERS ON ONE RAY -- the model leg's end against the "
          "grant's own reach")
    for tag, rows in (("lead CLIPPED", clipped), ("lead CLEAR  ", clear)):
        if not rows:
            print(f"  {tag}: none")
            continue
        gb = [x["blind"] - x["lead"] for x in rows]
        ga = [x["aware"] - x["lead"] for x in rows]
        print(f"  {tag} ({len(rows):3d}):  plane-BLIND past the grant "
              f"{sum(1 for g in gb if g > 1.0):3d}, max {max(gb):6.1f} u   |   "
              f"plane-AWARE {sum(1 for g in ga if g > 1.0):3d}, max {max(ga):6.1f} u")
    print("  (a CLEAR lead is 520 u by derivation against the client's ~768 u vec2 "
          "-- that 248 u is the margin over its own report trigger, 1z-ab.4)")

    still = [x for x in stops if abs(x["drift"] - x["blind"]) < 1.0]
    print("\n(b) THE COST, OBSERVED at the 0x0047 -- the subset where the body "
          "never moved at all")
    print(f"  {len(still)} of {len(stops)} stop reports: the recorded drift IS the "
          f"plane-blind model reach, to within 1 u")
    if still:
        print(f"    drift today            p50 {q([x['drift'] for x in still], .5):6.1f}"
              f"  p90 {q([x['drift'] for x in still], .9):6.1f}"
              f"  max {max(x['drift'] for x in still):6.1f} u")
        print(f"    the plane term leaves  p50 {q([x['aware'] for x in still], .5):6.1f}"
              f"  p90 {q([x['aware'] for x in still], .9):6.1f}"
              f"  max {max(x['aware'] for x in still):6.1f} u")
        cut = sum(x["blind"] - x["aware"] for x in still)
        untouched = [x for x in still
                     if x["blind"] - x["aware"] <= 1.0 and x["drift"] > 100.0]
        print(f"    {cut:.0f} u removed in total; {len(untouched)} of {len(still)} "
              f"are UNTOUCHED and still over 100 u -- our mesh reads those rays "
              f"clear the whole way, which is the mesh-AGREEMENT residual (1o) "
              f"and not something this closes")
        print("\n  the six biggest:")
        for x in sorted(still, key=lambda v: -v["drift"])[:6]:
            print(f"    t={x['t']:7.2f}  drift {x['drift']:6.1f} u after "
                  f"{x['silence']:4.2f} s of silence   blind {x['blind']:6.1f} -> "
                  f"plane {x['aware']:6.1f}")

    if not check:
        return 0
    fails = []

    def bar(ok, label, got):
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}  {got}")
        if not ok:
            fails.append(label)

    print("\n--check, against sec.1z-cc's registered figures")
    bar(len(pairs) >= FLOOR_PAIRS, f"at least {FLOOR_PAIRS} report->lead pairs",
        len(pairs))
    bar(len(clipped) >= FLOOR_CLIPPED, f"at least {FLOOR_CLIPPED} clipped leads",
        len(clipped))
    over_b = [x["blind"] - x["lead"] for x in clipped]
    over_a = [x["aware"] - x["lead"] for x in clipped]
    nb = sum(1 for g in over_b if g > 1.0)
    na = sum(1 for g in over_a if g > 1.0)
    bar(nb >= FLOOR_BLIND_OVER,
        f"the blind model leg out-walks its own grant at least {FLOOR_BLIND_OVER} "
        f"times (the defect is EXPOSED -- a census that finds none is measuring "
        f"the wrong thing)", nb)
    bar(na <= CEIL_AWARE_OVER and (not over_a or max(over_a) <= CEIL_AWARE_OVER_MAX),
        f"the plane term leaves at most {CEIL_AWARE_OVER}, none over "
        f"{CEIL_AWARE_OVER_MAX} u", f"{na}, max {max(over_a) if over_a else 0:.1f}")
    bar(len(still) >= FLOOR_STILL,
        f"at least {FLOOR_STILL} stop reports where the body never moved",
        len(still))
    if still:
        p50 = q([x["drift"] for x in still], .5)
        f50 = q([x["aware"] for x in still], .5)
        bar(p50 >= FLOOR_STILL_P50,
            f"their drift today is at least {FLOOR_STILL_P50} u at p50", f"{p50:.1f}")
        bar(f50 <= CEIL_FIXED_P50,
            f"and the plane term brings it under {CEIL_FIXED_P50} u", f"{f50:.1f}")
    print(f"\n{'ALL BARS MET' if not fails else str(len(fails)) + ' BAR(S) MISSED'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
