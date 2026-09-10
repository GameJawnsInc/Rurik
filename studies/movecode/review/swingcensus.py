r"""Every player swing in our hand-driven captures: did it land, and if not, what dropped it?

    python studies/movecode/review/swingcensus.py                 # every capture with swings
    python studies/movecode/review/swingcensus.py --cap PATH

WHY THIS EXISTS. RUN-1zCG session 8: the operator reported "some attacks didn't
deal damage even though the full animation played". 7 of 21 swings drew an
`attack_started` and produced no outcome, and 4 of those left NO row anywhere --
`_press_refused` writes nothing once the press it describes has been ANSWERED,
and a swing in flight is by definition one whose press was answered, so every
one of `attack_tick`'s in-flight drops ran through a logger that had already
declined to log (studies/movecode 1z-cr). `_swing_dropped` closes that from
2026-09-09 on; this reads the captures recorded BEFORE it existed, where the
branch has to be inferred by elimination.

THE ELIMINATION, per silent swing:
  * a `cancel:*` drop is visible on the wire -- the connection thread sends a
    labelled `attack_stopped` before asking for the drop;
  * `dead-player` is visible -- the death messages sit in the same second;
  * `target-gone` is visible -- the target's own death/removal;
  * `reach` sends NOTHING, and it is what is left. Its operand is the SERVER's
    believed distance, which the server prints in its own APPROACH / halt /
    FOLLOW labels -- so a silent swing whose window carries a printed distance
    above `attack_reach()` is attributed to `reach`.

WHAT THIS CANNOT DO. The printed distances are sampled at the label instants,
not at the drop tick, so the attribution is by elimination plus a window, not a
direct read. Captures written after `_swing_dropped` carry `swing_verdict` rows
and are read directly instead -- the `source` column says which.

Standard library only. Reads the vault through `vaultpath`.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan"):
    sys.path.insert(0, os.path.join(ROOT, _sub))

import vaultpath      # noqa: E402

REACH = 144.0          # attack_reach() under --attack-approach
WINDOW = 0.95          # s after the start to look for the server's own distance

_START = "player swings at 10"
_APPROACH = re.compile(r"APPROACH: player -> agent \d+ at \([-\d]+,[-\d]+\), "
                       r"([\d.]+) u out")
_HALT = re.compile(r"agent \d+ halts at \([-\d]+,[-\d]+\): arrived [\d.]+ s ago, "
                   r"([\d.]+) u from the player")
_FOLLOW = re.compile(r"FOLLOW(?: re-path)?: agent \d+ -> player at "
                     r"\([-\d]+,[-\d]+\) plane [\d>-]+, ([\d.]+) u out")


def _landed(label):
    return ("weapon hit on agent" in label
            or (label.startswith("damage") and "to agent" in label)
            or label.startswith("CRITICAL"))


def swings(rows):
    """One row per player swing: {t, landed, source, branch, dist}."""
    sent = [r for r in rows if r.get("kind") == "sent"]
    lab = lambda r: r.get("label", "")                      # noqa: E731
    starts = sorted(r["t"] for r in sent if _START in lab(r))
    hits = sorted(r["t"] for r in sent if _landed(lab(r)))
    stops = sorted((r["t"], lab(r)) for r in sent if "attack_stopped" in lab(r))
    deaths = sorted(r["t"] for r in sent
                    if "the player is dead" in lab(r).lower()
                    or "energy regeneration stops" in lab(r))
    verdicts = sorted((r["t"], r) for r in rows
                      if r.get("kind") == "swing_verdict")
    dists = []
    for r in sent:
        for rx in (_APPROACH, _HALT, _FOLLOW):
            m = rx.search(lab(r))
            if m:
                dists.append((r["t"], float(m.group(1))))
                break
    dists.sort()
    out = []
    for st in starts:
        landed = any(0 <= h - st <= 1.6 for h in hits)
        row = {"t": round(st, 2), "landed": landed, "source": None,
               "branch": None, "dist": None}
        if not landed:
            direct = [v for t, v in verdicts if -0.05 <= t - st <= 2.0]
            if direct:
                row["source"] = "swing_verdict"
                row["branch"] = direct[0].get("branch")
                row["dist"] = direct[0].get("dist")
            else:
                row["source"] = "inferred"
                near = [(t, d) for t, d in dists if -0.05 <= t - st <= WINDOW]
                mx = max((d for _t, d in near), default=None)
                if any(-0.1 <= t - st <= 0.9 for t, _l in stops):
                    row["branch"] = "cancel"
                elif any(-0.5 <= d - st <= 1.5 for d in deaths):
                    row["branch"] = "dead-player"
                elif mx is not None and mx > REACH:
                    row["branch"] = "reach"
                    row["dist"] = mx
                else:
                    row["branch"] = "unattributed"
                    row["dist"] = mx
        out.append(row)
    return out


# --------------------------------------------------------------- retail

STARTED, STOPPED, FINISHED = 4, 3, 1     # GV_* on 0x00A0 / 0x009F


def retail():
    """What follows an `attack_started` on ArenaNet's own wire.

    THE SLOT IS MEASURED, NOT ASSUMED: `0x00A0 [prop, attacker, target]` for
    GV_ATTACK_STARTED, against `0x00A3 [prop, target, cause]` for the damage --
    pairing each start to its next damage says attacker-first 876 times and
    target-first 28, so v[2] is the attacker. (Reading it the other way turns
    92.7% into 0.8% and was the first cut of this function.)
    """
    import livewire
    tot = collections.Counter()
    conns = 0
    for capdir, cf in livewire.live_connections():
        try:
            _c, merged, ok = livewire.decode_conn(capdir, cf)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        conns += 1
        ev = collections.defaultdict(list)
        for (t, dr, op, v) in merged:
            if dr != "s2c":
                continue
            if op == 0xA0 and len(v) >= 4 and v[1] == STARTED:
                ev[v[2]].append((t, "start"))
            elif op == 0x9F and len(v) >= 3 and v[1] == FINISHED:
                ev[v[2]].append((t, "finish"))
            elif op == 0x9F and len(v) >= 3 and v[1] == STOPPED:
                ev[v[2]].append((t, "stop"))
            elif op == 0xA3 and len(v) >= 5 and v[1] in (16, 17):
                ev[v[3]].append((t, "damage"))
        for _a, rws in ev.items():
            rws.sort()
            for i, (t, k) in enumerate(rws):
                if k != "start":
                    continue
                tot["started"] += 1
                later = [k2 for t2, k2 in rws[i + 1:] if 0 < t2 - t <= 3.0]
                if "damage" in later:
                    tot["damage"] += 1
                elif "finish" in later:
                    tot["finish_no_damage"] += 1
                elif "stop" in later:
                    tot["stopped"] += 1
                else:
                    tot["silent"] += 1
    return {"connections": conns, **dict(tot)}


def census(paths=None):
    gs = vaultpath.require_dir("captures", "gamesrv",
                               why="swingcensus reads our own captures")
    paths = paths or [os.path.join(gs, f) for f in sorted(os.listdir(gs))
                      if f.endswith(".jsonl")]
    out = {}
    for p in paths:
        try:
            rows = [json.loads(l) for l in open(p, encoding="utf-8")
                    if l.strip()]
        except Exception:                                   # noqa: BLE001
            continue
        sw = swings(rows)
        if sw:
            out[os.path.basename(p)] = sw
    return out


def score(cen):
    tot = [s for sw in cen.values() for s in sw]
    silent = [s for s in tot if not s["landed"]]
    return {
        "captures": len(cen),
        "swings": len(tot),
        "landed": sum(1 for s in tot if s["landed"]),
        "silent": len(silent),
        "by_branch": dict(collections.Counter(s["branch"] for s in silent)),
        "by_source": dict(collections.Counter(s["source"] for s in silent)),
        "reach_dists": sorted(s["dist"] for s in silent
                              if s["branch"] == "reach" and s["dist"]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cap", action="append")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cen = census(args.cap)
    sc = score(cen)
    if args.json:
        print(json.dumps({"score": sc, "captures": cen}, indent=1))
        return
    print(f"{sc['captures']} captures with player swings: {sc['swings']} swings, "
          f"{sc['landed']} landed, {sc['silent']} drew no outcome")
    print(f"  the silent ones by branch: {sc['by_branch']}")
    print(f"  attributed how:            {sc['by_source']}")
    if sc["reach_dists"]:
        print(f"  `reach` drops, server-believed distance (reach {REACH:.0f}): "
              f"{sc['reach_dists']}")
    try:
        r = retail()
        n = r.get("started", 0)
    except Exception as exc:                                # noqa: BLE001
        print("\n(retail half unavailable: %r)" % (exc,))
        n = 0
    if n:
        silent_ours = (sc["by_branch"].get("reach", 0)
                       + sc["by_branch"].get("unattributed", 0))
        cancel_ours = sc["by_branch"].get("cancel", 0)
        sw = sc["swings"]
        print("")
        print("RETAIL, the same lifecycle on ArenaNet's wire "
              "(%d connections, %d attack_started):" % (r["connections"], n))
        print("  -> damage         %6d  %5.1f%%   OURS %5.1f%%"
              % (r.get("damage", 0), 100.0 * r.get("damage", 0) / n,
                 100.0 * sc["landed"] / sw))
        print("  -> attack_stopped %6d  %5.1f%%   OURS %5.1f%%   <-- THE DIVERGENCE"
              % (r.get("stopped", 0), 100.0 * r.get("stopped", 0) / n,
                 100.0 * cancel_ours / sw))
        print("  -> SILENT         %6d  %5.1f%%   OURS %5.1f%%   (at retail's own rate)"
              % (r.get("silent", 0), 100.0 * r.get("silent", 0) / n,
                 100.0 * silent_ours / sw))
    for name, sw in sorted(cen.items()):
        s = [x for x in sw if not x["landed"]]
        if not s:
            continue
        print(f"  {name}: {len(sw)} swings, {len(s)} silent -- "
              + ", ".join(f"t={x['t']} {x['branch']}"
                          + (f" @{x['dist']}u" if x["dist"] else "")
                          for x in s))


if __name__ == "__main__":
    main()
