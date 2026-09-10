r"""How far does a server's own copy of the PLAYER sit from the player's own report?

    python studies/movecode/review/operandcensus.py            # retail and ours
    python studies/movecode/review/operandcensus.py --json

WHY THIS EXISTS. Two of our modules read `state["pos"]` -- the position MODEL --
as "where the player is": `_npc_follow_tick`'s chase target (§1z-cp.3) and
`attack_tick`'s reach gate (§1z-cx.4). §1z-cp.3 measured that model running
**259 u** from the drawn body at the corner, and §1z-cx found four swings
silently whiffed because of it. The obvious repair -- "read the last report
instead" -- is a GUESS until somebody asks what ArenaNet's server does, and the
corpus can answer directly.

THE OPERAND IS ON THE WIRE. Retail's `0x002A` follow carries a POINT as well as
a target agent, and that point is ArenaNet's own copy of the target at the send
(NPCTRACK F16, `chasercensus.py`'s docstring). The player's own position is the
c2s `0x003D` report. So `|follow point - report|` IS retail's model-vs-report
error, measured on ArenaNet's server, and our FOLLOW label carries the same two
numbers for ours.

THE PREDICTIONS, stated before the numbers:

  P1  retail's copy is NOT the report verbatim: p50 > 1 u. (If retail simply
      echoed the last report, "read the report" would be the whole answer and
      this census would say so.)
  P2  retail's copy is BOUNDED: its p99 sits well under the ~766 u lead retail
      grants a walking player. A server that integrated its own grant would run
      out toward the lead's end; one that tracks the body cannot.
  P3  the error is LAG, not extrapolation: projected on the player's own
      heading, retail's copy sits BEHIND the report more often than ahead.
  P4  ours has the same p50 and a heavier TAIL -- the defect is the tail, not
      the existence of a model. §1z-cp.3's own figures (p50 14.0, p90 72.5,
      max 259.2) predict this before the run.

WHAT THIS CANNOT DO. Retail's report cadence and ours differ, and a copy
sampled only when a chase is live is not a uniform sample of the session. Both
sides are measured the same way, at follow instants only, so the comparison is
like-for-like even where neither is a session average.

Standard library only. Reads the vault through `livewire` / `vaultpath`.
"""
import argparse
import bisect
import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                            # noqa: E402

C2S_HEADING = 61           # 0x003D  [op, point, heading...]
S2C_FOLLOW = 42            # 0x002A  [op, agent, point, w, w, target]
S2C_LEG = 41               # 0x0029  [op, agent, point, w, w]
ANSWER_WINDOW = 0.3

_FOLLOW_LBL = re.compile(r"FOLLOW(?: re-path)?: agent \d+ -> player at "
                         r"\(([-\d.]+),([-\d.]+)\)")
_REPORT_LBL = re.compile(r"KBD LEAD \([-\d.]+,[-\d.]+\) from "
                         r"\(([-\d.]+),([-\d.]+)\)")


def q(v, f):
    v = sorted(v)
    return v[min(int(f * len(v)), len(v) - 1)] if v else float("nan")


def _stats(v):
    v = [x for x in v if x is not None]
    if not v:
        return {}
    return {"n": len(v), "p50": round(q(v, .50), 1), "p90": round(q(v, .90), 1),
            "p99": round(q(v, .99), 1), "max": round(max(v), 1)}


# ----------------------------------------------------------------- retail

def player_of(merged):
    """The agent whose 0x0029 grants answer the c2s heading reports."""
    c61 = [(t, v) for (t, dr, op, v) in merged
           if dr == "c2s" and op == C2S_HEADING and len(v) >= 2]
    s29 = [(t, v) for (t, dr, op, v) in merged
           if dr == "s2c" and op == S2C_LEG and len(v) >= 3]
    if len(c61) < 5 or not s29:
        return None, c61
    cnt = collections.Counter()
    st = [t for t, _ in s29]
    for t, _ in c61:
        i = bisect.bisect_left(st, t)
        for j in range(i, min(i + 4, len(s29))):
            if s29[j][0] - t <= ANSWER_WINDOW:
                cnt[s29[j][1][1]] += 1
    return (cnt.most_common(1)[0][0] if cnt else None), c61


def retail():
    """|follow point - player report| at every retail follow naming the player."""
    import livewire
    err, ahead, rows, ages, conns = [], [], [], [], 0
    for capdir, conn_file in livewire.live_connections():
        try:
            _conn, merged, ok = livewire.decode_conn(capdir, conn_file)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        pid, c61 = player_of(merged)
        if pid is None or len(c61) < 5:
            continue
        conns += 1
        rts = [t for t, _ in c61]
        for (t, dr, op, v) in merged:
            if dr != "s2c" or op != S2C_FOLLOW or len(v) < 6:
                continue
            if v[5] != pid or v[1] == pid:
                continue
            i = bisect.bisect_right(rts, t) - 1
            if i < 0:
                continue
            rep = tuple(c61[i][1][1])
            age = t - c61[i][0]
            pt = tuple(v[2])
            e = math.hypot(pt[0] - rep[0], pt[1] - rep[1])
            err.append(e)
            ages.append((age, e))
            # Direction: project on the player's own travel since the previous
            # report. Positive = the copy is AHEAD of the report along it.
            if i >= 1:
                prev = tuple(c61[i - 1][1][1])
                hx, hy = rep[0] - prev[0], rep[1] - prev[1]
                n = math.hypot(hx, hy)
                if n > 1.0:
                    proj = ((pt[0] - rep[0]) * hx + (pt[1] - rep[1]) * hy) / n
                    ahead.append(proj)
            rows.append({"t": round(t, 3), "err": round(e, 1),
                         "age": round(age, 3),
                         "capture": os.path.basename(capdir)})
    return {"connections": conns, "err": err, "ahead": ahead, "rows": rows,
            "ages": ages}


# ------------------------------------------------------------------- ours

def ours():
    """The same quantity from our own gamesrv captures, from the server's own rows.

    `position_report` carries `reported` (the client's own report), `ours`
    (the position MODEL) and `drift` (their distance) -- the row §1z-cp.3's
    figures come from. `npc_order.frame` is the point a follow actually aimed
    at. So the follow-instant error is |frame - last reported|, measured the
    same way retail's is, and `drift` is the same number sampled at every
    report instead.
    """
    gs = vaultpath.require_dir("captures", "gamesrv",
                               why="operandcensus reads our own captures")
    drift, foll, rows, ages, caps = [], [], [], [], 0
    for name in sorted(os.listdir(gs)):
        if not name.endswith(".jsonl"):
            continue
        try:
            rec = [json.loads(l) for l in
                   open(os.path.join(gs, name), encoding="utf-8") if l.strip()]
        except Exception:                                   # noqa: BLE001
            continue
        reps, seen = [], False
        for r in rec:
            k = r.get("kind")
            if k == "position_report":
                if r.get("accepted") and r.get("reported"):
                    reps.append((r["t"], tuple(r["reported"])))
                if r.get("drift") is not None:
                    drift.append(float(r["drift"]))
                    seen = True
            elif k == "npc_order" and r.get("frame") and reps:
                fr = tuple(r["frame"])
                rt, rep = reps[-1]
                e = math.hypot(fr[0] - rep[0], fr[1] - rep[1])
                foll.append(e)
                ages.append((r["t"] - rt, e))
                rows.append({"t": round(r["t"], 2), "err": round(e, 1),
                             "age": round(r["t"] - rt, 3), "capture": name})
        if seen:
            caps += 1
    return {"captures": caps, "drift": drift, "err": foll, "rows": rows,
            "ages": ages}


def score():
    r, o = retail(), ours()
    ah = r["ahead"]
    def by_age(pairs, lo, hi):
        return _stats([e for a, e in pairs if lo <= a < hi])
    BANDS = ((0.0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 1e9))
    return {
        "retail_by_age": {f"{lo}-{hi}": by_age(r["ages"], lo, hi)
                          for lo, hi in BANDS},
        "ours_by_age": {f"{lo}-{hi}": by_age(o["ages"], lo, hi)
                        for lo, hi in BANDS},
        "ours_drift_all_reports": _stats(o["drift"]),
        "retail": {"connections": r["connections"], "err": _stats(r["err"]),
                   "ahead_of_report": _stats([a for a in ah if a > 0]),
                   "behind_report": _stats([-a for a in ah if a < 0]),
                   "n_behind": sum(1 for a in ah if a < 0),
                   "n_ahead": sum(1 for a in ah if a > 0)},
        "ours": {"captures": o["captures"], "err": _stats(o["err"])},
        "ours_worst": sorted(o["rows"], key=lambda x: -x["err"])[:8],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sc = score()
    if args.json:
        print(json.dumps(sc, indent=1))
        return
    r, o = sc["retail"], sc["ours"]
    print("RETAIL -- ArenaNet's own copy of the player vs the player's own report,")
    print(f"         at every 0x002A naming the player ({r['connections']} connections)")
    print(f"  |copy - report|        {r['err']}")
    print(f"  P3 direction: BEHIND the report {r['n_behind']}, ahead {r['n_ahead']}")
    print(f"     behind by            {r['behind_report']}")
    print(f"     ahead by             {r['ahead_of_report']}")
    print()
    print(f"OURS -- state['pos'] (the model) vs the report the lead was baked from")
    print(f"         ({o['captures']} captures)")
    print(f"  |model - report|       {o['err']}")
    print("  worst:", ", ".join(f"{x['capture'][8:21]} t={x['t']} {x['err']}u"
                                for x in sc["ours_worst"][:5]))
    print(f"  drift at EVERY accepted report (§1z-cp.3's own number): "
          f"{sc['ours_drift_all_reports']}")
    print()
    print("AGE-CONTROLLED -- |copy - report| by how STALE the report was, the")
    print("confound that makes an uncontrolled comparison meaningless:")
    print(f"  {'band (s)':>10}  {'RETAIL':>34}  {'OURS':>34}")
    for k in sc["retail_by_age"]:
        print(f"  {k:>10}  {str(sc['retail_by_age'][k]):>34}  "
              f"{str(sc['ours_by_age'][k]):>34}")


if __name__ == "__main__":
    main()
