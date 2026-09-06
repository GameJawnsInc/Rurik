#!/usr/bin/env python3
"""How long does the CLIENT's own AgTrack fence actually stay shut after our 0x002C, and how long does OUR latch think it does? (MOVECODE-1z-bw)

    python studies/movecode/review/fencelatency.py            # the whole corpus
    python studies/movecode/review/fencelatency.py <tape.jsonl>

THE QUESTION. `authsrv.KBD_LEAD_FENCE_GATE` degrades a keyboard or D1 lead to the
zero-lead point while `state["fence_shut_at"] is not None` (authsrv.py:5789
`_fence_gate_lead`).  That latch is stamped at EVERY player 0x002C (:4705) and cleared
in exactly ONE place (:19202-19208): a keyboard WALK-START, i.e. a moving 0x003D
arriving while `kbd_moving_at` was clear -- which requires a preceding 0x0047 to have
cleared it.  **So a player who walks without stopping can hold the latch set
indefinitely, and every lead in that stretch ships as a zero-length grant.**

On RUN-1zBW that cost 54.72 s of a 190 s session (28.7%), in three windows, the longest
45.25 s, degrading 72 of 163 fired grants (44.2%).

WHETHER THAT IS RIGHT depends on a fact about the CLIENT, not about us: how long the
client's own fence (`clientControlled`, the dword its dispatcher tests at 0x00606002
before it will run the three-gate snap test) really stays shut.  agenttap has recorded
that dword since MOVECODE-1z-an, so the corpus can answer it.  This file asks:

  1. of the 0x002C we sent, how many SHUT the client's fence at all;
  2. when one did, how long until the client read OPEN again;
  3. how that compares with how long OUR latch stayed set.

WHY IT IS NOT ENOUGH TO READ ONE RUN.  RUN-1zBW has five pins, three of which shut the
fence -- n=3 is not a constant, it is an anecdote, and this repo has shipped a borrowed
constant as a placeholder before.  Every tape carrying the fence column is scored here
so the number has a denominator.

INSTRUMENT LIMITS, STATED.  The tape polls at ~11-30 Hz, so a shut window shorter than a
sample gap is invisible and every duration here is quantised to that gap -- these are
LOWER bounds on "how fast it reopens" and the sample count is printed per pin.  The tape
and the capture are joined on wall-unix (the tape's head t0 plus the sample's t against
the capture rows' wall_unix); a run whose streams do not overlap is skipped and counted,
never silently dropped.

Read-only.  Needs the vault.  Stdlib only.
"""
import glob
import json
import os
import statistics
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for sub in (("toolkit",), ("toolkit", "clientscan"), ("toolkit", "authsrv")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
from vaultpath import require_dir  # noqa: E402

VAULT = require_dir()
SHUT_WINDOW = 3.0      # s after a pin within which a shut is attributed to it


def load_tape(path):
    head, samples = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("kind") == "head":
                head = r
            elif r.get("kind") == "sample":
                samples.append(r)
    return head, samples


def fence_series(head, samples):
    """[(wall_unix, fence_raw)] for agent 1, or [] if the column is absent."""
    out = []
    t0 = (head or {}).get("t0")
    if t0 is None:
        return out
    for s in samples:
        f = ((s.get("agents") or {}).get("1") or {}).get("fence") or {}
        raw = f.get("fence_raw")
        if raw is None:
            continue
        out.append((t0 + s["t"], raw))
    return out


def pins_and_rearms(cap):
    """([wall_unix of every player 0x002C], [(wall_unix, shut_for) of every fence rearm])."""
    pins, rearms = [], []
    with open(cap, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            w = r.get("wall_unix")
            if not isinstance(w, (int, float)):
                continue
            if r.get("kind") == "sent" and "0x002C" in str(r.get("label", "")):
                pins.append(w)
            elif r.get("kind") == "fence" and r.get("act") == "rearm":
                rearms.append((w, r.get("shut_for")))
    return sorted(pins), sorted(rearms)


def pair_capture(fs):
    """The gamesrv capture whose wall span overlaps this tape's, or None."""
    lo, hi = fs[0][0], fs[-1][0]
    best, best_ov = None, 0.0
    for c in glob.glob(os.path.join(VAULT, "captures", "gamesrv", "*-c1.jsonl")):
        try:
            ts = []
            with open(c, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        w = json.loads(line).get("wall_unix")
                    except Exception:
                        continue
                    if isinstance(w, (int, float)):
                        ts.append(w)
                        if len(ts) > 4000:
                            break
            if not ts:
                continue
            ov = min(hi, max(ts)) - max(lo, min(ts))
            if ov > best_ov:
                best, best_ov = c, ov
        except Exception:
            continue
    return best if best_ov > 0 else None


def score(tape):
    head, samples = load_tape(tape)
    fs = fence_series(head, samples)
    if not fs:
        return None
    cap = pair_capture(fs)
    if cap is None:
        return {"tape": tape, "skip": "no overlapping gamesrv capture"}
    pins, rearms = pins_and_rearms(cap)
    if not pins:
        return {"tape": tape, "cap": cap, "skip": "no 0x002C", "n_open": sum(1 for _t, v in fs if v == 1),
                "n_shut": sum(1 for _t, v in fs if v == 0)}
    rows = []
    for p in pins:
        after = [(t, v) for t, v in fs if t >= p]
        # a shut ATTRIBUTED to this pin: the first shut within SHUT_WINDOW,
        # and not one that a LATER pin could own
        nxt = min([q for q in pins if q > p] or [float("inf")])
        shut_t = next((t for t, v in after if v == 0 and t - p <= SHUT_WINDOW and t < nxt), None)
        if shut_t is None:
            rows.append({"pin": p, "shut": False})
            continue
        reopen = next((t for t, v in fs if t > shut_t and v == 1), None)
        n_in = sum(1 for t, v in fs if shut_t <= t <= (reopen if reopen else fs[-1][0]))
        rows.append({"pin": p, "shut": True, "shut_at": shut_t,
                     "reopen": reopen, "dur": (reopen - shut_t) if reopen else None,
                     "samples": n_in})
    return {"tape": tape, "cap": cap, "rows": rows, "rearms": rearms,
            "n_open": sum(1 for _t, v in fs if v == 1),
            "n_shut": sum(1 for _t, v in fs if v == 0), "n": len(fs)}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    # BOTH naming conventions.  The first draft of this file globbed only
    # "agenttap-*.jsonl" and therefore EXCLUDED RUN-1zBW's own tape, which is named
    # "1zbw-agenttap.jsonl" -- the corpus number was computed without the run that
    # motivated it.  A fixture that silently matches the wrong set is the same defect
    # as one that resolves to nothing.
    taps = args or sorted(set(
        glob.glob(os.path.join(VAULT, "research", "**", "agenttap-*.jsonl"), recursive=True)
        + glob.glob(os.path.join(VAULT, "research", "**", "*-agenttap*.jsonl"), recursive=True)))
    print("scanning %d tape(s) for the client fence column ..." % len(taps))
    durs, n_pins, n_shut_pins, skipped, scored = [], 0, 0, 0, 0
    open_s = shut_s = 0
    for t in taps:
        r = score(t)
        if r is None:
            continue
        if r.get("skip"):
            skipped += 1
            continue
        scored += 1
        open_s += r["n_open"]
        shut_s += r["n_shut"]
        for row in r["rows"]:
            n_pins += 1
            if row["shut"]:
                n_shut_pins += 1
                if row["dur"] is not None:
                    durs.append(row["dur"])
        print("\n%s" % os.path.basename(t))
        print("   capture %s   fence samples: open %d / shut %d"
              % (os.path.basename(r["cap"]), r["n_open"], r["n_shut"]))
        for row in r["rows"]:
            if not row["shut"]:
                print("   pin -> the client's fence NEVER read shut within %.1f s" % SHUT_WINDOW)
            else:
                print("   pin -> shut, reopened after %s (%d samples inside)"
                      % (("%.3f s" % row["dur"]) if row["dur"] is not None else "never (tape ended)",
                         row["samples"]))
        for w, sf in r["rearms"]:
            print("   our latch rearmed, logged shut_for=%s" % sf)

    print("\n" + "=" * 78)
    print("CORPUS: %d tape(s) scored, %d skipped (no capture / no 0x002C)" % (scored, skipped))
    if not n_pins:
        # A NULL HERE IS NOT A PASS: with no pin the corpus has run no trials of the
        # question and the constant below must not be quoted.
        print("NO 0x002C in any scored tape -- ZERO TRIALS. No constant is derivable; "
              "nothing here may be quoted as one.")
        return 3
    print("client fence samples: open %d / shut %d (%.1f%% open)"
          % (open_s, shut_s, 100.0 * open_s / max(open_s + shut_s, 1)))
    print("our 0x002C: %d sent, %d actually shut the client's fence (%.0f%%)"
          % (n_pins, n_shut_pins, 100.0 * n_shut_pins / n_pins))
    if durs:
        durs.sort()
        print("client SHUT DURATION over %d measured shuts: min %.3f  p50 %.3f  p90 %.3f  max %.3f s"
              % (len(durs), durs[0], statistics.median(durs),
                 durs[min(int(0.9 * len(durs)), len(durs) - 1)], durs[-1]))
        print("\nOUR LATCH, by contrast, is cleared ONLY by a keyboard walk-start")
        print("(authsrv.py:19202-19208), which needs a 0x0047 first -- so it is UNBOUNDED")
        print("above.  On RUN-1zBW it held 45.25 s against a client maximum of %.3f s." % durs[-1])
    else:
        print("no measurable shut duration (every shut ran to the end of its tape)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
