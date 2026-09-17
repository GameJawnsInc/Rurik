"""chainjoin.py -- the Assassin's attack chain on retail's wire.

    python toolkit/authsrv/chainjoin.py                       # the whole live corpus
    python toolkit/authsrv/chainjoin.py --capture 20260917T160915

THE QUESTIONS (studies/daggers/FINDINGS.md, DAGGERS-Q1..Q5), each joined on one
clock per connection (livewire.decode_conn), the observer found by the
self-scoped property 41 (adrenjoin's rule):

  chain    every s2c 0x005C [observer, target, state]; for each 0, the seconds
           since the state was SET and since the observer's last chain-skill
           0x00E5 -- the two readings of "15 s" that a re-lead separates.
  relead   a lead's 0x00E5 landing on a target ALREADY at state 1: is a second
           0x005C sent?
  dual     per 0x00E5 of a `combo = 3` skill: the observer's damage words in
           the next 0.75 s, the gap between them, the fail words (property 38,
           reason 2), the [47, observer, 0] marker, and the property-55 words
           the observer deals to OTHER agents (an attack skill's adjacent
           damage).
  cold     per 0x00E5 of a chain skill answered by a fail word: is the same
           instant's second 0x00E5 a zero recharge?
  double   per PLAIN swing ([4, observer, T, 0] with no property-50 inside a
           second): damage words before the next start; for a pair, the gap,
           the [2, observer, 0] marker, and which word the close (1) rides.
  crit     per property-17 word of the observer's: a 0x00A3 [52, self, self,
           f] and a 0x00A0 [54, self, self, n] in the same instant, in order.

Which skills are chain skills is the CLIENT's own field: `combo` on the skills
rows (skilltable.py --emit-content, DAGGERS-B1). Without those rows this tool
refuses rather than guessing a list.

Read-only; standard library only; refuses non-live captures by construction
(livewire.live_connections).
"""
import argparse
import collections
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402

COMBO, E5 = 0x005C, 0x00E5
PINT, PINT_T, PFLOAT_T = 0x009F, 0x00A0, 0x00A3
SAME = 0.02             # s: "the same instant" on one connection's clock
SECOND_WINDOW = 0.75    # s: a second strike is ~0.5 s behind the first


def _f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def chain_skills():
    """{skill id: combo} off the content rows; raises when they carry none."""
    import agents
    out = {}
    for key, row in agents.WORLD.rows("skills").items():
        if int(row.get("combo", 0)):
            out[int(key)] = int(row["combo"])
    if not out:
        raise SystemExit("chainjoin: the skills rows carry no `combo` -- "
                         "re-run skilltable.py --emit-content (DAGGERS-B1)")
    return out


def observer_of(merged):
    for _t, d, op, v in merged:
        if d == "s2c" and op == PINT and len(v) > 2 and v[1] == 41:
            return v[2]
    return None


def census(capture=None, skills=None):
    skills = skills or chain_skills()
    out = collections.defaultdict(list)
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        if capture and stamp != capture:
            continue
        try:
            _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        except Exception:                                       # noqa: BLE001
            continue
        me = observer_of(merged)
        if me is None:
            continue
        s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
        if not any(op == COMBO for _t, op, _v in s2c):
            continue
        _one(stamp, me, s2c, skills, out)
    return out


def _one(stamp, me, s2c, skills, out):
    words = [(t, v[1], v[2], _f32(v[4])) for t, op, v in s2c
             if op == PFLOAT_T and v[1] in (16, 17) and v[3] == me]
    fails = [(t, v[2]) for t, op, v in s2c
             if op == PINT_T and v[1] == 38 and v[3] == me and v[4] == 2]
    e5s = [(t, v[2], v[4]) for t, op, v in s2c if op == E5 and v[1] == me]
    marks = {p: [t for t, op, v in s2c if op == PINT and v[1] == p and v[2] == me]
             for p in (1, 2, 47)}
    near = lambda ts, t: any(abs(x - t) < SAME for x in ts)

    # ---- chain: every 0x005C, and the two clocks behind each 0 ------------
    state, set_at = {}, {}
    # A chain HIT: the landed skill's own 0x00E5 instant when a damage word
    # rides it; a dual's second strike (its [47] marker) as well; and for a
    # chain SPELL, whose projectiles land after the cast ends, every word of
    # the observer's in the following second (858 throws three, and each one
    # restarts the clock -- which is the August tape's "15.66 s").
    hits = []
    for t, sid, rech in e5s:
        if sid not in skills or not rech or near([f[0] for f in fails], t):
            continue
        if near([w[0] for w in words], t):
            hits.append(t)
            if skills[sid] == 3:
                hits += [x for x in marks[47] if 0 < x - t < SECOND_WINDOW]
        else:
            hits += [w[0] for w in words if 0 < w[0] - t < 1.0]
    hits.sort()
    for t, op, v in s2c:
        if op != COMBO or v[1] != me:
            continue
        tgt, st = v[2], v[3]
        row = {"stamp": stamp, "t": t, "target": tgt, "state": st}
        if st == 0 and tgt in set_at:
            row["since_set"] = t - set_at[tgt]
            last = [h for h in hits if h < t]
            row["since_hit"] = t - last[-1] if last else None
        out["chain"].append(row)
        if st:
            set_at[tgt] = t
        state[tgt] = st
    # ---- relead: a lead landing on a target already showing 1 -------------
    shown = {}
    events = sorted([(t, 0, ("c", v[2], v[3])) for t, op, v in s2c
                     if op == COMBO and v[1] == me]
                    + [(t, 1, ("e5", sid, rech)) for t, sid, rech in e5s])
    for t, _k, ev in events:
        if ev[0] == "c":
            shown[ev[1]] = (ev[2], t)
        elif skills.get(ev[1]) == 1 and ev[2] and not near([f[0] for f in fails], t):
            tgt = next((w[2] for w in words if abs(w[0] - t) < SAME), None)
            if tgt is not None and shown.get(tgt, (0, 0))[0] == 1 \
                    and t - shown[tgt][1] > SAME:
                out["relead"].append({
                    "stamp": stamp, "t": t, "target": tgt,
                    "resent": any(op == COMBO and abs(x - t) < SAME
                                  for x, op, _v in s2c)})
    # ---- dual, cold ---------------------------------------------------------
    for t, sid, rech in e5s:
        if sid not in skills or not rech:
            continue
        failed = [f for f in fails
                  if -SAME < f[0] - t < (SECOND_WINDOW if skills[sid] == 3 else SAME)]
        zeroed = any(abs(x - t) < SAME and s == sid and r == 0 for x, s, r in e5s)
        if failed:
            out["cold"].append({"stamp": stamp, "t": t, "skill": sid,
                                "fails": len(failed), "zeroed": zeroed,
                                "gap": (failed[1][0] - failed[0][0]
                                        if len(failed) > 1 else None)})
        if skills[sid] != 3:
            continue
        ws = [w for w in words if -SAME < w[0] - t < SECOND_WINDOW]
        adj = [(x, v[2], _f32(v[4])) for x, op, v in s2c
               if op == PFLOAT_T and v[1] == 55 and v[3] == me and v[2] != me
               and -SAME < x - t < SECOND_WINDOW]
        m47 = [x for x in marks[47] if -SAME < x - t < SECOND_WINDOW]
        combo = [x for x, op, v in s2c if op == COMBO and v[1] == me and v[3] == 3
                 and -SAME < x - t < SECOND_WINDOW]
        out["dual"].append({
            "stamp": stamp, "t": t, "skill": sid, "words": len(ws),
            "gap": ws[1][0] - ws[0][0] if len(ws) > 1 else None,
            "props": tuple(w[1] for w in ws), "fails": len(failed),
            "marker47": len(m47),
            "state3_with_second": bool(combo and len(ws) > 1
                                       and abs(combo[0] - ws[1][0]) < SAME),
            "adjacent": len(adj), "adjacent_values": sorted({round(a[2], 4) for a in adj}),
            "adjacent_targets": sorted({a[1] for a in adj})})
    # ---- double: plain swings ----------------------------------------------
    starts = [t for t, op, v in s2c if op == PINT_T and v[1] == 4 and v[2] == me]
    acts = [t for t, op, v in s2c if op == PINT_T and v[1] == 50 and v[2] == me]
    for i, t in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else t + 5.0
        if any(abs(a - t) < 1.0 or t < a < nxt for a in acts):
            continue
        ws = [w for w in words if t < w[0] < min(nxt, t + 1.3)]
        row = {"stamp": stamp, "t": t, "words": len(ws), "next": nxt - t}
        if len(ws) == 2:
            row.update(gap=ws[1][0] - ws[0][0], props=(ws[0][1], ws[1][1]),
                       marker2=near(marks[2], ws[1][0]),
                       close_on_first=near(marks[1], ws[0][0]),
                       close_on_second=near(marks[1], ws[1][0]))
        out["double"].append(row)
    # ---- crit ---------------------------------------------------------------
    for i, (t, op, v) in enumerate(s2c):
        if not (op == PFLOAT_T and v[1] == 17 and v[3] == me):
            continue
        batch = [(j, o, vv) for j, (x, o, vv) in enumerate(s2c) if abs(x - t) < SAME]
        i52 = next((j for j, o, vv in batch if o == PFLOAT_T and vv[1] == 52
                    and vv[2] == me and vv[3] == me), None)
        i54 = next((j for j, o, vv in batch if o == PINT_T and vv[1] == 54
                    and vv[2] == me and vv[3] == me), None)
        out["crit"].append({
            "stamp": stamp, "t": t,
            "gain": _f32(s2c[i52][2][4]) if i52 is not None else None,
            "callout": s2c[i54][2][4] if i54 is not None else None,
            "ordered": i52 is not None and i54 is not None and i52 < i54 < i})


def summary(c):
    """The numbers the study quotes and test_daggers pins, from a census."""
    clears = [r for r in c["chain"] if r["state"] == 0 and r.get("since_hit") is not None]
    duals = [r for r in c["dual"] if not r["fails"]]
    doubles = [r for r in c["double"] if r["words"] == 2]
    plain = [r for r in c["double"] if r["words"] in (1, 2)]
    crits = c["crit"]
    return {
        "chain_messages": len(c["chain"]),
        "states": dict(collections.Counter(r["state"] for r in c["chain"])),
        "clears_15s_after_last_hit": sum(1 for r in clears
                                         if abs(r["since_hit"] - 15.0) < 0.05),
        "clears_since_set": sorted(round(r["since_set"], 3) for r in clears),
        "clears_since_hit": sorted(round(r["since_hit"], 3) for r in clears),
        "releads": len(c["relead"]),
        "releads_resent": sum(1 for r in c["relead"] if r["resent"]),
        "duals_landed": len(duals),
        "duals_two_words": sum(1 for r in duals if r["words"] == 2),
        "dual_gap": ([round(min(r["gap"] for r in duals if r["gap"]), 3),
                      round(max(r["gap"] for r in duals if r["gap"]), 3)]
                     if any(r["gap"] for r in duals) else None),
        "duals_marker47": sum(1 for r in c["dual"] if r["marker47"] == 1),
        "duals_state3_with_second": sum(1 for r in duals if r["state3_with_second"]),
        "duals_adjacent": sum(r["adjacent"] for r in duals),
        "adjacent_values": sorted({v for r in duals for v in r["adjacent_values"]}),
        "cold": len(c["cold"]),
        "cold_zeroed": sum(1 for r in c["cold"] if r["zeroed"]),
        "cold_by_fails": dict(collections.Counter(r["fails"] for r in c["cold"])),
        "plain_swings": len(plain),
        "double_strikes": len(doubles),
        "double_gap": ([round(min(r["gap"] for r in doubles), 3),
                        round(statistics.median(r["gap"] for r in doubles), 3),
                        round(max(r["gap"] for r in doubles), 3)] if doubles else None),
        "double_marker2": sum(1 for r in doubles if r["marker2"]),
        "double_close_on_first": sum(1 for r in doubles if r["close_on_first"]),
        "double_close_on_second": sum(1 for r in doubles if r["close_on_second"]),
        "next_start_after_single": (round(statistics.median(
            r["next"] for r in plain if r["words"] == 1 and r["next"] < 2.0), 3)
            if any(r["words"] == 1 for r in plain) else None),
        "next_start_after_double": (round(statistics.median(
            r["next"] for r in doubles if r["next"] < 2.0), 3) if doubles else None),
        "crits": len(crits),
        "crits_with_gain": sum(1 for r in crits if r["gain"] is not None),
        "crits_ordered": sum(1 for r in crits if r["ordered"]),
        "crit_gains": dict(collections.Counter(
            (round(r["gain"], 4), r["callout"]) for r in crits if r["gain"] is not None)),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--capture", help="one live capture's stamp")
    a = ap.parse_args(argv)
    got = summary(census(a.capture))
    for k, v in got.items():
        print(f"{k:32s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
