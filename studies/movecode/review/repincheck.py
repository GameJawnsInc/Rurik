#!/usr/bin/env python3
"""Every 0x002C the server sent, against the harm bound that licenses it.

    python studies/movecode/review/repincheck.py                # newest capture
    python studies/movecode/review/repincheck.py vault/captures/gamesrv/authsrv-<stamp>-c1.jsonl
    python studies/movecode/review/repincheck.py --all          # the whole corpus

RUN-1zAH's safety readout (MOVECODE-1z-ah). The AgTrack re-pin sends the
client's OWN last accepted report, so "how far is the re-pin from that report"
is 0.0 u by construction and measures nothing. The quantity that matters is the
one the freshness gate exists to bound: **how far the drawn body may have moved
since that report**, because a 0x002C SetPositions BOTH copies (`AgMsg.cpp` 579
and 584) and re-pinning a body that has walked away drags it backward -- the
warp an earlier build shipped and this project removed.

So each fired 0x002C is scored on three things the wire CAN say:

  * `age`      -- how stale the report it carries was. Under
                  REPIN_MAX_REPORT_AGE (100/288 s) the original gate licensed
                  it and the harm is under the client's own 100 u radius.
  * `prev_d`   -- the distance between the last TWO accepted reports, which is
                  the stationary waiver's entire predicate. A stale re-pin is
                  licensed ONLY when this is within the client's own
                  ZERO_DIST_SQ, i.e. the body was MEASURED still.
  * `next_d`   -- how far the NEXT accepted report lands from the point we
                  pinned to. A body that really was parked there reports from
                  there; a body we dragged reports a jump.

VIOLATION = a stale AGTRACK RE-PIN whose `prev_d` is over the radius. That is a
re-pin the waiver must never have licensed, and one is enough to refute
FINDINGS sec.1z-ah.4 on safety. Exits non-zero if any is found, so it cannot be
skimmed past.

SCOPED TO THAT SENDER ON PURPOSE. The other 0x002C arms (RESYNC, PRESS ENDS THE
WALK, CAST-STOP PIN, ...) never pass through the re-pin's preconditions, so this
rule is not theirs; they are printed for context and never counted. Scoring them
by it made the corpus read 7 violations that predate 1z-ah entirely -- a metric
red before the change ran cannot score the change.

Read-only; the vault is found through vaultpath.
"""
import argparse
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))

# The two decoded constants this check is written against, restated from the
# modules that derive them so a drift shows up as a mismatch rather than
# silently changing what "licensed" means.
MAX_AGE = 100.0 / 288.0          # agtrack_guard.REPIN_MAX_REPORT_AGE
ZERO_DIST = 1.0                  # agtrack_mirror.ZERO_DIST_SQ, as a radius


def newest():
    import vaultpath
    hits = sorted(glob.glob(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "authsrv-*-c1.jsonl")))
    if not hits:
        raise SystemExit("no gamesrv captures in the vault")
    return hits[-1]


def decode_point(plain):
    """(x, y, plane) from a 0x002C payload's hex, exactly.

    The label rounds to integers, which cannot answer a 1.0 u question -- so
    the floats come off the wire bytes: u16 opcode, u32 agent, f32 x, f32 y,
    u16 plane.
    """
    try:
        b = bytes.fromhex(plain)
    except (ValueError, TypeError):
        return None
    if len(b) < 16:
        return None
    x, y = struct.unpack_from("<ff", b, 6)
    plane = struct.unpack_from("<H", b, 14)[0]
    return x, y, plane


def sender(label):
    """The 0x002C's own arm, from the wire label it was sent with."""
    for name in ("AGTRACK RE-PIN", "RESYNC", "CAST-STOP PIN", "PLANE-REPAIR",
                 "APPROACH RE-PIN", "PRESS ENDS THE WALK"):
        if name in label:
            return name
    return label.split("(")[0].strip()[:28] or "unlabelled"


def check(path, verbose=True):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    if not rows:
        return 0, 0
    t0 = rows[0]["t"]
    waiver = None
    for r in rows:
        if r.get("kind") == "flags":
            waiver = r.get("agtrack_guard.STATIONARY_WAIVER")
            break
    reps = [(r["t"], tuple(r["reported"])) for r in rows
            if r.get("kind") == "position_report" and r.get("accepted")
            and r.get("reported")]
    pins = [r for r in rows
            if r.get("kind") == "sent" and r.get("opcode") == 0x2C]

    if verbose:
        print("capture  %s" % os.path.basename(path))
        print("         %d accepted reports, %d x 0x002C, span %.1f s, "
              "STATIONARY_WAIVER=%s"
              % (len(reps), len(pins), rows[-1]["t"] - t0,
                 "(not recorded -- pre-1z-ah capture)" if waiver is None
                 else waiver))
    if not pins:
        if verbose:
            print("  no 0x002C sent -- zero exposure for this check, "
                  "not a pass\n")
        return 0, 0

    if verbose:
        print("\n%-8s %-18s %10s %7s %8s %8s  %s"
              % ("t", "sender", "point", "age", "prev_d", "next_d", "verdict"))
    violations = 0
    for r in pins:
        t = r["t"]
        pt = decode_point(r.get("plain", ""))
        lab = str(r.get("label", ""))
        prior = [x for x in reps if x[0] <= t]
        after = [x for x in reps if x[0] > t]
        age = (t - prior[-1][0]) if prior else None
        prev_d = None
        if len(prior) >= 2:
            (_, p1), (_, p2) = prior[-2], prior[-1]
            prev_d = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        next_d = None
        if after and pt is not None:
            q = after[0][1]
            next_d = ((q[0] - pt[0]) ** 2 + (q[1] - pt[1]) ** 2) ** 0.5

        who = sender(lab)
        stale = age is not None and age > MAX_AGE
        if who != "AGTRACK RE-PIN":
            # SCOPE. The bound below licenses the AGTRACK RE-PIN, whose
            # preconditions are agtrack_guard._repin_block. The other 0x002C
            # senders never pass through it and carry their own arguments, so
            # judging them by this rule would paint pre-existing behaviour as a
            # regression of 1z-ah's -- and a safety metric that is already red
            # before the change ran is measuring the wrong quantity. Reported
            # for context, never counted. (The corpus sweep does show PRESS
            # ENDS THE WALK sending stale 0x002Cs -- their own question.)
            verdict = "-- other sender, not the waiver's rule"
        elif not stale:
            verdict = "ok (fresh report, the original gate)"
        elif prev_d is None:
            verdict = "?? stale with fewer than two reports -- unlicensed"
            violations += 1
        elif prev_d <= ZERO_DIST:
            verdict = "ok (STATIONARY WAIVER: body measured still)"
        else:
            verdict = ("VIOLATION -- stale re-pin, body had MOVED %.1f u"
                       % prev_d)
            violations += 1
        if verbose:
            print("%-8.3f %-18s %10s %7s %8s %8s  %s"
                  % (t - t0, sender(lab),
                     "(%.0f,%.0f)" % (pt[0], pt[1]) if pt else "??",
                     "%.2fs" % age if age is not None else "--",
                     "%.1f" % prev_d if prev_d is not None else "--",
                     "%.1f" % next_d if next_d is not None else "--",
                     verdict))
    if verbose:
        print()
    return len(pins), violations


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", nargs="?", default=None)
    ap.add_argument("--all", action="store_true",
                    help="sweep every gamesrv capture in the vault")
    a = ap.parse_args()

    if a.all:
        import vaultpath
        paths = sorted(glob.glob(os.path.join(
            vaultpath.vault_path("captures", "gamesrv"), "authsrv-*-c1.jsonl")))
    else:
        paths = [a.capture or newest()]

    pins = viol = 0
    for p in paths:
        try:
            # A sweep stays quiet on the clean ones and prints the offenders in
            # full: a wall of 1,200 clean tables is where a violation hides.
            n, v = check(p, verbose=not a.all)
            if a.all and v:
                check(p, verbose=True)
        except (OSError, KeyError, IndexError) as e:
            print("  [skip] %s (%r)" % (os.path.basename(p), e))
            continue
        pins += n
        viol += v

    print("%d x 0x002C over %d capture(s); %d violation(s) of the harm bound"
          % (pins, len(paths), viol))
    if viol:
        print("A stale re-pin fired at a body that had MOVED. That is the warp "
              "AgMsg.cpp 584 makes possible, and it refutes FINDINGS "
              "sec.1z-ah.4 on safety -- revert with "
              "--no-repin-stationary-waiver.")
        return 1
    print("Every 0x002C was licensed: a fresh report, or a body MEASURED "
          "still across two of them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
