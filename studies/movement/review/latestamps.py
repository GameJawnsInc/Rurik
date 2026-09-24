r"""Late capture stamps on OUR tapes: how many of our speed-arm hard rows are one late stamp?

    python studies/movement/review/latestamps.py            # the census
    python studies/movement/review/latestamps.py --rows     # + every row the census names

THE QUESTION (DESKWORK-Q3, the movement FINDINGS entry of 2026-09-17). Retail's one firing of
the 400 u/s speed arm is a capture stamp 18 ms late (`movesync.late_stamp`, analysis only).
That entry left the other direction open: "A hard-jump count on a boosted or short-cadence
capture of OURS may include late stamps. Not measured; `late_stamp` is the tool that would."
This is that measurement, over every recorder capture in `vault/captures/gamesrv/` that
`origin.origin_of` calls OURS.

PREDICTION, stated before the run (2026-09-24): ZERO late stamps within the 67 ms bound among
our speed-arm hard rows, over a population of roughly 270-290 rows in roughly 70 captures (the
DESKWORK survey's single-witness scratch count was 0 of 274 in 71, studies/deskwork/PLAN.md
section 4). Most rows should be refused because the PAIR still reads over the arm -- a real
displacement adds distance, a late stamp only moves time. A late stamp found on our tapes would
mean some hard-jump counts quoted from `movesync` include an artifact, and the rows would be
listed.

THE CAVEAT THAT BOUNDS THE ANSWER. Our recorder stamps a c2s report when OUR server receives
it, on one process clock; retail's capture stamps it when the sniffer sees the packet. A late
stamp is a delay between the client's report and the stamp, so on our tapes it is a delay
inside the loopback socket and our own receive loop -- the artifact may be structurally rarer
here, and a zero is a statement about our tapes, not about the predicate.

HOW EACH ROW IS CLASSIFIED. `why_not` below walks `movesync.late_stamp`'s own refusals in its
own order and names the first that fires; a row it accepts must be a row `late_stamp` accepts,
and the census REFUSES TO PRINT if the two disagree on any row (the classifier is a mirror of
the committed predicate, never a second opinion). POSITIVE CONTROL FIRST: the same classifier
must name retail's own late stamp (20260916T213125, t = 197.760) through `cmsgstream`, or the
census stops -- a zero from a classifier that cannot see the one known stamp measures nothing.

Server hard sets: a row spanning a `0x002C` we SENT to the player (agent 1, the agent our
`0x0029` grants name) is marked as `movesync.mark_server_sets` does, so `late_stamp` refuses it
the way it refuses retail's JARIN shrine.

READ-ONLY. Standard library only.
"""
import argparse
import collections
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/schema"):
    _p = os.path.join(ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import movesync  # noqa: E402
import origin  # noqa: E402
import vaultpath  # noqa: E402

OP_UPDATE_POSITION = movesync.OP_UPDATE_POSITION     # s2c 0x002C
KNOWN_LATE = ("20260916T213125", 197.760)            # retail's one, FINDINGS 2026-09-17


def speed_arm(r):
    return (r.get("server_set") is None and r["dt"] >= movesync.HARD_JUMP_MIN_DT
            and r["speed"] > movesync.HARD_JUMP_SPEED)


def why_not(rows, k):
    """(reason, detail) -- the FIRST of `late_stamp`'s refusals that fires on row k, in its
    order; ("late-stamp", info) when none does. Mirrors movesync.late_stamp line for line."""
    if k < 1 or k >= len(rows):
        return "no-predecessor", None
    fast, slow = rows[k], rows[k - 1]
    for r in (fast, slow):
        if r["dt"] < movesync.HARD_JUMP_MIN_DT:
            return "neighbour-below-dt-floor", None
        if r.get("server_set") is not None:
            return "spans-a-server-set", None
    if not fast["speed"] > movesync.HARD_JUMP_SPEED:
        return "not-on-the-speed-arm", None
    pair_speed = (fast["dist"] + slow["dist"]) / (fast["dt"] + slow["dt"])
    if pair_speed >= movesync.HARD_JUMP_SPEED or pair_speed <= 0:
        return "pair-still-over-the-arm", pair_speed
    delta = fast["dist"] / pair_speed - fast["dt"]
    around = [rows[j]["speed"] for j in (k - 2, k + 1)
              if 0 <= j < len(rows)
              and rows[j]["dt"] >= movesync.HARD_JUMP_MIN_DT
              and rows[j].get("server_set") is None]
    if not 0.0 < delta <= movesync.LATE_STAMP_MAX:
        # Past the bound, the rest of the predicate is still asked (it does not change the
        # verdict): a row whose flanks AGREE with the pair is the stamp SHAPE with a delay
        # the 67 ms bound refuses -- the residue worth naming, apart from a pair that merely
        # averages under the arm across a stop.
        shaped = bool(around) and all(abs(pair_speed - v) <= movesync.LATE_STAMP_TOL
                                      for v in around)
        return "delta-outside-the-bound", {"delta": delta, "shaped": shaped}
    if not around:
        return "no-flank", None
    if any(abs(pair_speed - v) > movesync.LATE_STAMP_TOL for v in around):
        return "flanks-disagree", (pair_speed, around, delta)
    return "late-stamp", {"delta": delta, "pair_speed": pair_speed, "around": around}


def sent_sets(path, agent=movesync.PLAYER_AGENT):
    """[(t, [x, y])] of every 0x002C we sent to `agent`, from the logged wire bytes (the same
    offsets `movesync.load_grants` reads 0x0029's agent and point at)."""
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "sent" or r.get("opcode") != OP_UPDATE_POSITION:
            continue
        b = bytes.fromhex(r.get("plain") or "")
        if len(b) < 14:
            continue
        aid, = struct.unpack_from("<I", b, 2)
        if aid == agent:
            x, y = struct.unpack_from("<ff", b, 6)
            out.append((r["t"], [x, y]))
    return out


def positive_control():
    """The classifier on retail's own corpus: it must name KNOWN_LATE. Returns the row's info."""
    import cmsgstream
    st, t_known = KNOWN_LATE
    msgs = cmsgstream.timed(st, "c2s", "game")
    s2c = cmsgstream.timed(st, "s2c", "game")
    sets = movesync.hard_sets(s2c, movesync.named_players(s2c))
    byconn = collections.defaultdict(list)
    for t, conn, op, vals in msgs:
        if op in (movesync.OP_SET_HEADING, movesync.OP_CANCEL_REPORT) and len(vals) > 1:
            p = vals[1]
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                byconn[conn].append((t, [float(p[0]), float(p[1])]))
    for conn, reps in byconn.items():
        reps.sort(key=lambda z: z[0])
        rows = movesync.steps(reps)
        movesync.mark_server_sets(rows, sets.get(conn, []))
        for k, r in enumerate(rows):
            if speed_arm(r) and abs(r["t"] - t_known) < 0.01:
                reason, info = why_not(rows, k)
                if reason == "late-stamp" and movesync.late_stamp(rows, k):
                    return info
    return None


def census(paths):
    """Every OURS capture's speed-arm rows, each classified. Returns (stats, rows, mismatches)."""
    stats = collections.Counter()
    out, mismatches = [], []
    for path in paths:
        org, _why = origin.origin_of(path)
        stats["origin:" + org] += 1
        if org != origin.OURS:
            continue
        reps, _walls, _src = movesync.load_wire_reports(path)
        rows = movesync.steps(reps)
        movesync.mark_server_sets(rows, sent_sets(path))
        stats["captures_ours"] += 1
        stats["intervals"] += len(rows)
        hit = False
        for k, r in enumerate(rows):
            if r.get("server_set") is not None:
                stats["rows_spanning_a_server_set"] += 1
            if not speed_arm(r):
                continue
            hit = True
            reason, info = why_not(rows, k)
            committed = movesync.late_stamp(rows, k)
            if (reason == "late-stamp") != (committed is not None):
                mismatches.append((os.path.basename(path), r["t"], reason))
            out.append((os.path.basename(path), r, reason, info))
        stats["captures_with_a_speed_arm_row"] += hit
    return stats, out, mismatches


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="print every classified row")
    a = ap.parse_args(argv)

    ctrl = positive_control()
    if not ctrl:
        print(f"POSITIVE CONTROL FAILED: the classifier does not name retail's late stamp "
              f"{KNOWN_LATE[0]} t={KNOWN_LATE[1]} -- a zero below would measure nothing.")
        return 2
    print(f"positive control: retail {KNOWN_LATE[0]} t={KNOWN_LATE[1]} named, stamp "
          f"{ctrl['delta'] * 1000:.1f} ms late, pair {ctrl['pair_speed']:.2f} u/s")

    root = vaultpath.require_dir("captures", "gamesrv")
    paths = sorted(glob.glob(os.path.join(root, "*.jsonl")))
    stats, rows, mismatches = census(paths)
    if mismatches:
        print(f"REFUSED: the classifier disagrees with movesync.late_stamp on "
              f"{len(mismatches)} row(s): {mismatches[:5]}")
        return 2
    reasons = collections.Counter(reason for _p, _r, reason, _i in rows)
    print(f"{len(paths)} recorder captures in captures/gamesrv; by origin "
          + ", ".join(f"{k[7:]} {v}" for k, v in sorted(stats.items())
                      if k.startswith("origin:")))
    print(f"{stats['captures_ours']} OURS, {stats['intervals']:,} intervals, "
          f"{stats['rows_spanning_a_server_set']} spanning a 0x002C we sent the player")
    print(f"{len(rows)} speed-arm hard rows (> {movesync.HARD_JUMP_SPEED:.0f} u/s at dt >= "
          f"{movesync.HARD_JUMP_MIN_DT} s, no server set) in "
          f"{stats['captures_with_a_speed_arm_row']} captures")
    for reason, n in reasons.most_common():
        print(f"  {n:5d}  {reason}")
    late = [x for x in rows if x[2] == "late-stamp"]
    beyond = [i for _p, _r, reason, i in rows if reason == "delta-outside-the-bound"]
    shaped = sorted(i["delta"] for i in beyond if i["shaped"])
    print(f"LATE STAMPS within {movesync.LATE_STAMP_MAX * 1000:.0f} ms: {len(late)}")
    if beyond:
        print(f"of the {len(beyond)} pairs under the arm with delta outside (0, "
              f"{movesync.LATE_STAMP_MAX * 1000:.0f}] ms, {len(shaped)} have flanks that AGREE "
              f"with the pair (the stamp SHAPE, delay past the bound)"
              + (f": delta {shaped[0] * 1000:.0f}-{shaped[-1] * 1000:.0f} ms" if shaped else ""))
    if a.rows or late:
        for p, r, reason, info in rows:
            if a.rows or reason == "late-stamp":
                print(f"  {p} t={r['t']:.3f} {r['dist']:.1f} u / {r['dt']:.3f} s = "
                      f"{r['speed']:.1f} u/s  {reason}  {info if info is not None else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
