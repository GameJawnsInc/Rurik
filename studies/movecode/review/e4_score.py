#!/usr/bin/env python3
"""DEATHWALK-E4's scorer: does a follow inside its stop disc still re-path, and does a swing still
open in the same call as a re-path? (DEATHWALK-D1, FINDINGS 1z-ds.51.)

    python studies/movecode/review/e4_score.py STAMP [STAMP ...]    # gamesrv capture stamps (all -cN)
    python studies/movecode/review/e4_score.py --selftest           # synthetic + TRAILPIN's real tapes

THE FIX BEING SCORED. `STOP_DISC_ENDS_FOLLOW` (ON; `--repath-inside-stop` reverts): a re-path that
falls due while the body is already inside its stop disc is NOT sent; the arrival branch closes the
follow instead. Before it, that re-path went out with run ~0, its zero leg replaced a live latch,
and 1z-ds.36's re-read let the swing open in the same call -- 47 of 49 same-tick swings.

TWO MEASURES PER TAPE, both off our own rows:
  INSIDE-STOP RE-PATHS -- `approach` rows with `repath` true and `dist_frame` <= `stop`. This is the
    fix's OPERAND: the fixed arm must send none; the known-bad arm sends them whenever a re-path falls
    due inside the disc. It is the exposure measure too -- the known-bad arm's count is how often the
    situation arose on that plan.
  SAME-TICK SWINGS -- a player start (sent 0x00A0 [4, 1, T]) within 25 ms after an `APPROACH` 0x002A,
    classed by the approach row it belongs to:
      C1  a re-path with dist_frame <= stop      (the class the fix closes)
      C2  a re-path with dist_frame >  stop      (the sub-tick re-path; NOT covered, a leftover)
      C3  a new follow (repath false)            (the zero-run new follow after a re-pin; leftover)

THE ARM IS READ OFF THE TAPE: flags STOP_DISC_ENDS_FOLLOW true = "fixed", false = "known-bad",
absent = a build before D1 ("pre-D1", the known-bad behaviour).

E4's REGISTERED PREDICTION (RUN-DEATHWALK H5, sharpened at launch): the fixed arm sends 0 inside-stop
re-paths and has 0 C1; the known-bad arm reproduces both (C1 1-6 a launch, TRAILPIN's rate). C2 / C3
are counted, not held to 0. FLOOR: the known-bad arm's inside-stop re-paths, pooled, >= 5 -- below
that the comparison is UNEXPOSED, because a fixed arm's 0 means nothing on a plan that never made the
situation.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import vaultpath  # noqa: E402

OP_DEST, OP_INT_TARGET = 0x2A, 0xA0
SAME_TICK = 0.025
FLOOR = 5
# TRAILPIN's launches (pt_build.TP_RUNS): pre-D1 tapes with published counts -- T 7, N 10 same-tick
# re-path swings (tp_controls.py, 1z-ds.48), all C1 by DEATHWALK-D1's census (1z-ds.51).
TRAILPIN = {"T": ["20261004T194444", "20261004T200131", "20261004T201815", "20261004T203454"],
            "N": ["20261004T195308", "20261004T200955", "20261004T202637", "20261004T204312"]}


def load(path):
    """(flags, approach rows, follow sends, player starts) from one gamesrv capture."""
    flags, aps, follows, starts = {}, [], [], []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("{"):
                continue
            if ('"kind": "flags"' not in line and '"kind": "approach"' not in line
                    and '"kind": "sent"' not in line):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            k = r.get("kind")
            if k == "flags":
                flags = r
            elif (k == "approach" and r.get("act") in ("send", "re-path")
                  and r.get("leg") != "pickup"):          # a new follow is "send", a re-path "re-path"
                aps.append(r)
            elif k == "sent" and r.get("opcode") == OP_DEST and str(r.get("label", "")).startswith("APPROACH"):
                follows.append(r)
            elif (k == "sent" and r.get("opcode") == OP_INT_TARGET
                  and "attack_started: player" in str(r.get("label", ""))):
                starts.append(r["t"])
    return flags, aps, follows, starts


def arm_of(flags):
    if "STOP_DISC_ENDS_FOLLOW" not in flags:
        return "pre-D1"
    return "fixed" if flags["STOP_DISC_ENDS_FOLLOW"] else "known-bad"


def score_rows(aps, follows, starts):
    """{repaths, inside_stop, C1, C2, C3, examples}"""
    out = {"repaths": 0, "inside_stop": 0, "C1": 0, "C2": 0, "C3": 0, "ex": []}
    for a in aps:
        if a.get("repath"):
            out["repaths"] += 1
            if float(a["dist_frame"]) <= float(a["stop"]):
                out["inside_stop"] += 1
    for fsend in follows:
        t = fsend["t"]
        if not any(0.0 <= s - t < SAME_TICK for s in starts):
            continue
        row = max((a for a in aps if a["t"] <= t + 1e-6), key=lambda a: a["t"], default=None)
        if row is None:
            continue
        if not row.get("repath"):
            cls = "C3"
        elif float(row["dist_frame"]) <= float(row["stop"]):
            cls = "C1"
        else:
            cls = "C2"
        out[cls] += 1
        out["ex"].append((cls, round(t, 3), round(float(row["run"]), 1), round(float(row["dist_frame"]), 1)))
    return out


def tapes_for(arg):
    if os.path.isfile(arg):
        return [arg]
    return sorted(glob.glob(vaultpath.vault_path("captures", "gamesrv", f"authsrv-{arg}-c*.jsonl")))


def score(stamps, quiet=False):
    """{arm: [per-tape dict]}"""
    by = {}
    for a in stamps:
        for p in tapes_for(a):
            flags, aps, follows, starts = load(p)
            if not aps and not starts:
                continue
            r = score_rows(aps, follows, starts)
            r["tape"], r["arm"] = os.path.basename(p), arm_of(flags)
            by.setdefault(r["arm"], []).append(r)
            if not quiet:
                print(f"  {r['tape']} [{r['arm']}] re-paths {r['repaths']}, inside-stop {r['inside_stop']}; "
                      f"same-tick C1 {r['C1']} C2 {r['C2']} C3 {r['C3']}" + (f"  {r['ex']}" if r["ex"] else ""))
    return by


def summary(by):
    lines = []
    for arm, rs in sorted(by.items()):
        tot = {k: sum(r[k] for r in rs) for k in ("repaths", "inside_stop", "C1", "C2", "C3")}
        lines.append(f"[{arm}] {len(rs)} tape(s): re-paths {tot['repaths']}, inside-stop {tot['inside_stop']}; "
                     f"same-tick C1 {tot['C1']}, C2 {tot['C2']}, C3 {tot['C3']}")
    kb = [r for arm in ("known-bad", "pre-D1") for r in by.get(arm, [])]
    exposure = sum(r["inside_stop"] for r in kb)
    lines.append(f"exposure (known-bad inside-stop re-paths, pooled): {exposure} "
                 f"{'(>= floor ' + str(FLOOR) + ')' if exposure >= FLOOR else '-- UNEXPOSED, floor ' + str(FLOOR)}")
    return "\n".join(lines)


def selftest():
    bad = 0

    def ck(ok, what, detail=""):
        nonlocal bad
        print(f"  [{'PASS' if ok else 'FAIL'}] {what}" + (f"  {detail}" if detail else ""))
        bad += 0 if ok else 1

    print("== 1. synthetic rows: each class, and the operand ==")
    aps = [{"t": 1.0, "repath": False, "run": 300.0, "dist_frame": 380.0, "stop": 80.0},
           {"t": 1.5, "repath": True, "run": 0.0, "dist_frame": 70.0, "stop": 80.0},
           {"t": 3.0, "repath": True, "run": 0.4, "dist_frame": 80.4, "stop": 80.0},
           {"t": 5.0, "repath": False, "run": 0.0, "dist_frame": 65.9, "stop": 80.0},
           {"t": 7.0, "repath": True, "run": 50.0, "dist_frame": 130.0, "stop": 80.0}]
    follows = [{"t": a["t"]} for a in aps]
    starts = [1.5002, 3.0043, 5.0003, 7.2]
    r = score_rows(aps, follows, starts)
    ck(r["repaths"] == 3 and r["inside_stop"] == 1,
       "3 re-paths, ONE inside its stop (70 <= 80; 80.4 is outside)", str(r))
    ck((r["C1"], r["C2"], r["C3"]) == (1, 1, 1),
       "same-tick swings classed C1 (re-path inside the stop), C2 (re-path at 80.4), C3 (new follow); "
       "the 7.2 start, 200 ms after its re-path, is not same-tick", str(r["ex"]))
    ck(arm_of({"STOP_DISC_ENDS_FOLLOW": True}) == "fixed"
       and arm_of({"STOP_DISC_ENDS_FOLLOW": False}) == "known-bad" and arm_of({}) == "pre-D1",
       "the arm off the flags row: fixed / known-bad / pre-D1")

    print("== 2. TRAILPIN's real tapes (pre-D1): the published counts, off real bytes ==")
    paths = {arm: [p for s in ss for p in tapes_for(s)] for arm, ss in TRAILPIN.items()}
    if not all(paths.values()):
        print("  [SKIP] TRAILPIN's tapes are not in this vault (bare machine)")
    else:
        got = {}
        for arm, ps in paths.items():
            tot = {"C1": 0, "C2": 0, "C3": 0, "inside_stop": 0, "arms": set()}
            for p in ps:
                flags, aps2, fol2, st2 = load(p)
                rr = score_rows(aps2, fol2, st2)
                for k in ("C1", "C2", "C3", "inside_stop"):
                    tot[k] += rr[k]
                tot["arms"].add(arm_of(flags))
            got[arm] = tot
        ck(got["T"]["C1"] + got["T"]["C2"] == 7 and got["N"]["C1"] + got["N"]["C2"] == 10,
           "same-tick re-path swings T 7 / N 10, as tp_controls.py published (1z-ds.48)",
           f"T {got['T']['C1']}+{got['T']['C2']}, N {got['N']['C1']}+{got['N']['C2']}")
        ck(got["T"]["C2"] == 0 and got["N"]["C2"] == 0,
           "and every one of them C1, as DEATHWALK-D1's census found (1z-ds.51)")
        ck(got["T"]["arms"] == {"pre-D1"} and got["N"]["arms"] == {"pre-D1"},
           "the arm read off those tapes is pre-D1", str({a: g["arms"] for a, g in got.items()}))
        ck(got["T"]["inside_stop"] + got["N"]["inside_stop"] >= got["T"]["C1"] + got["N"]["C1"],
           "inside-stop re-paths are at least as many as the C1 swings they make (every C1 is one)",
           f"inside-stop T {got['T']['inside_stop']}, N {got['N']['inside_stop']}")
    print("SELFTEST", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return selftest()
    by = score(argv)
    if not by:
        print("no tapes for", argv)
        return 2
    print(summary(by))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
