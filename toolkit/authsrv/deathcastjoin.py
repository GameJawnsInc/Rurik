"""deathcastjoin.py -- what retail's death batch does with the observer's cast in flight.

    python toolkit/authsrv/deathcastjoin.py          # the census over the live corpus
    python toolkit/authsrv/deathcastjoin.py --rows   # every death with a cast open, its batch

THE QUESTION (CONFPASS-F1, studies/deskwork/CONFIRM-2026-10-08.md §3). On our loopback
runs CT-2 and CT-2x the player pressed Backfire 28 (3.00 s), bled out partway, and the
cast still completed after the death batch -- E5, [58], the hex on the hostile, the
aftercast's E3 -- because `kill_player` closed nothing. What does retail send for a cast
the observer's own death cuts short, and where in the death batch?

THE JOIN, per live connection (livewire.decode_conn; the observer by shoutjoin.observer_of,
property 41 and the answered presses, which must agree): the observer's 0x00F1 status word
gaining the dead bit (16) is a death, losing it a rise. A cast is OPEN at a death when its
0x00E4 [me, skill, copy] has had no 0x00E5 / 0x00E3 / 0x00E2 [me, skill] since, inside
OPEN_S. The death BATCH is the run of s2c messages from the status to the observer's own
flags word 0x0026 [me, ..], inside BATCH_S of the status (retail closes every death tick
with it, 29 of 29 here). Read from the batch: the stop word ([59] / [49] / [45] / [57] on
me), the E2 for the open skill, the morale pair (0x009C [me, ..], 0x00EE), the 0x00D0, the
strips (0x0044 [me, ..]), the 0x002D, and any [8, me, *]. Read after it, to the rise or
AFTER_S: any 0x00E5 / 0x00E3 for the open skill -- the corpse completing.

THE PREDICTIONS, written before the first run (scratch, 2026-10-09):

  P1  no E5 and no E3 for the open skill after the death, ever (the corpse does not
      complete).
  P2  the batch closes it with [59, me, 0] immediately followed by E2 [me, skill, copy]
      -- the hero's shape at 20260914T005758 609.252 (PENDSKILL), and the cancel burst's
      last two messages.
  P3  their SLOT: after the status and after the morale pair when the map charges one,
      ahead of the 0x00D0, every strip and the 0x002D. The weakest of the four.
  P4  no [8, me, *] in the batch: the corpse is held by its cast's own [8, me, 1], and
      the hold flag is transition-only (castmech 3c).

MEASURED 2026-10-09 over the live corpus (39 captures): 29 observer deaths; 6 with the
observer's own cast open (skills 1 x3 and 153 x3, 0.20-1.88 s into the cast). P1 6 of 6,
P2 6 of 6, P3 6 of 6 (the morale pair ahead on the 4 that charged), P4 6 of 6. Also
printed, NOT predicted and not scored: deaths inside the AFTERCAST (E5 out, E3 not) --
one, 20260929T100038 :51090 423.923, skill 1 completing in the death's own instant,
closed by [57, me, 0] + E2 rather than an E3 (CONFPASS-F1b, open, n = 1); and where the
0x00D0 sits against the 0x002D across every death (ahead of it on every death that
carries one -- ours sends it after; open, not this change).

Read-only; standard library only; refuses non-live captures by construction
(livewire.live_connections).
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import shoutjoin  # noqa: E402

STATUS = 0x00F1
FLAGS = 0x0026
MOVE_CANCEL = 0x002D
MORALE = 0x009C
ATTR_UPDATE = 0x00EE          # player-scoped, no agent id: [attr, delta]
ADREN_CLEAR = 0x00D0
STRIP = 0x0044
PINT = 0x009F                 # [prop, agent, value]
E2, E3, E4, E5 = 0x00E2, 0x00E3, 0x00E4, 0x00E5
DEAD_BIT = 16
HOLD = 8                      # agents.GV_DISABLED
STOPS = {59: "skill_stopped", 49: "attack_skill_stopped", 45: "cast_dropped",
         57: "57 (unnamed)"}
OPEN_S = 10.0                 # an E4 older than this with no close is a lost record, not a cast
BATCH_S = 0.03                # one batch: retail's death tick shares one capture stamp
AFTER_S = 30.0                # how far past a death to look for a completion
INTERRUPT_S = 0.05            # an E5 this close behind an E2 is an interrupt's recharge


def _vals(v):
    """A decoded message's fields without the header word livewire leaves at index 0."""
    return list(v)[1:]


def deaths(merged, me):
    """Every death of `me` on one connection: dicts with the batch and the casts in flight."""
    s2c = [(t, op, _vals(v)) for t, d, op, v in merged if d == "s2c"]
    open_e4, aftercast, last_e2 = {}, {}, {}
    out, dead = [], False
    for k, (t, op, v) in enumerate(s2c):
        if not v:
            continue
        if op == E4 and v[0] == me and len(v) > 2:
            open_e4[v[1]] = (t, v[2])
        elif op == E5 and v[0] == me and len(v) > 1:
            open_e4.pop(v[1], None)
            if t - last_e2.get(v[1], -1e9) > INTERRUPT_S:
                aftercast[v[1]] = t
        elif op in (E2, E3) and v[0] == me and len(v) > 1:
            open_e4.pop(v[1], None)
            aftercast.pop(v[1], None)
            if op == E2:
                last_e2[v[1]] = t
        if op != STATUS or v[0] != me or len(v) < 2:
            continue
        if not v[1] & DEAD_BIT:
            dead = False
            continue
        if dead:
            continue                                  # the strips re-send the word as 16
        dead = True
        batch = []
        for t2, op2, v2 in s2c[k:]:
            if t2 - t > BATCH_S:
                break
            batch.append((op2, v2))
            if op2 == FLAGS and v2 and v2[0] == me:
                break
        rise = next((t2 for t2, op2, v2 in s2c[k + 1:]
                     if op2 == STATUS and v2 and v2[0] == me and len(v2) > 1
                     and not v2[1] & DEAD_BIT), t + AFTER_S)
        later = [(op2, v2) for t2, op2, v2 in s2c[k + len(batch):]
                 if t2 <= min(rise, t + AFTER_S) and op2 in (E3, E5) and v2 and v2[0] == me]
        out.append({
            "t": t, "word": v[1], "batch": batch, "later": later,
            "open": {s: (round(t - x[0], 3), x[1]) for s, x in open_e4.items()
                     if t - x[0] <= OPEN_S},
            "aftercast": {s: round(t - x, 3) for s, x in aftercast.items() if t - x <= OPEN_S},
        })
    return out


def _idx(batch, pred):
    return [i for i, (op, v) in enumerate(batch) if pred(op, v)]


def score_death(row, me):
    """The four predictions on one death with a cast open: {P1..P4: bool, ...}."""
    b = row["batch"]
    res = {}
    for skill, (_age, copy) in row["open"].items():
        stop = _idx(b, lambda op, v: op == PINT and len(v) > 2 and v[1] == me and v[2] == 0
                    and v[0] in STOPS)
        e2 = _idx(b, lambda op, v, s=skill: op == E2 and len(v) > 1 and v[0] == me and v[1] == s)
        morale = _idx(b, lambda op, v: (op == MORALE and v[0] == me) or op == ATTR_UPDATE)
        later_ops = {op for op, v in row["later"] if len(v) > 1 and v[1] == skill}
        after = (_idx(b, lambda op, v: op == ADREN_CLEAR and v[0] == me)
                 + _idx(b, lambda op, v: op == STRIP and v[0] == me)
                 + _idx(b, lambda op, v: op == MOVE_CANCEL and v[0] == me))
        res[skill] = {
            "P1": not later_ops,
            "P2": (len(stop) == 1 and b[stop[0]][1][0] == 59 and len(e2) == 1
                   and e2[0] == stop[0] + 1 and b[e2[0]][1][2] == copy),
            "P3": bool(stop) and all(i < stop[0] for i in morale)
                  and all(i > (e2 or stop)[0] for i in after),
            "P4": not _idx(b, lambda op, v: op == PINT and len(v) > 1 and v[0] == HOLD
                           and v[1] == me),
            "morale": bool(morale),
            "stop": [b[i][1][0] for i in stop],
        }
    return res


def census():
    """(totals Counter, rows) over every live connection; rows are deaths with a cast open
    or an aftercast open."""
    tot, rows = collections.Counter(), []
    for capdir, gf in livewire.live_connections():
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        me, _press, _why = shoutjoin.observer_of(merged)
        if me is None:
            continue
        for row in deaths(merged, me):
            tot["deaths"] += 1
            d_at = _idx(row["batch"], lambda op, v: op == ADREN_CLEAR and v[0] == me)
            c_at = _idx(row["batch"], lambda op, v: op == MOVE_CANCEL and v[0] == me)
            if d_at and c_at:
                tot["0x00D0 ahead of 0x002D" if d_at[0] < c_at[0] else "0x00D0 behind 0x002D"] += 1
            row.update(capture=os.path.basename(capdir), conn=conn or gf, me=me, ok=ok)
            if row["open"]:
                tot["open"] += 1
                row["score"] = score_death(row, me)
                for res in row["score"].values():
                    for p in ("P1", "P2", "P3", "P4"):
                        tot[p] += bool(res[p])
                    tot["charged"] += res["morale"]
            if row["aftercast"]:
                tot["aftercast"] += 1
            if row["open"] or row["aftercast"]:
                rows.append(row)
    return tot, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="every death with a cast open, its batch")
    a = ap.parse_args()
    tot, rows = census()
    n = tot["open"]
    print(f"observer deaths: {tot['deaths']}; with the observer's own cast open: {n}")
    for p, what in (("P1", "no E5 / E3 for the cut skill afterwards"),
                    ("P2", "[59, me, 0] then E2 [me, skill, copy], adjacent"),
                    ("P3", "after the status + morale pair, ahead of 0x00D0 / strips / 0x002D"),
                    ("P4", "no [8, me, *] in the batch")):
        print(f"  {p} {what}: {tot[p]} of {n}")
    print(f"  (of those, the map charged morale on {tot['charged']})")
    print(f"deaths inside the aftercast (E5 out, E3 not): {tot['aftercast']} -- not scored")
    print(f"0x00D0 against 0x002D: ahead {tot['0x00D0 ahead of 0x002D']}, "
          f"behind {tot['0x00D0 behind 0x002D']}")
    for row in rows:
        tag = (f"{row['capture']} {row['conn']} me={row['me']} t={row['t']:.3f} "
               f"open={row['open']} aftercast={row['aftercast']}")
        print(("\n" if a.rows else "") + tag + (f"  {row.get('score')}" if a.rows else ""))
        if a.rows:
            for op, v in row["batch"]:
                print(f"    0x{op:04X} {v}")
            for op, v in row["later"]:
                print(f"    later 0x{op:04X} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
