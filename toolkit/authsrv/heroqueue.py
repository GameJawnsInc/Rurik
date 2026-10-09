r"""When does a HERO's 0x00E4 open -- at its cast's start, or at its pick? Retail's wire, and ours.

    python toolkit/authsrv/heroqueue.py                       # every live capture
    python toolkit/authsrv/heroqueue.py --rows                # + every hero E4, classed
    python toolkit/authsrv/heroqueue.py --ours <authsrv-*-c1.jsonl>   # + one of OUR captures
    python toolkit/authsrv/heroqueue.py --json

WHY THIS EXISTS (studies/skills 65.8's E4 decision, 65.9). PENDSKILL ships a hero's
0x00E4 [hero, skill, 0] -- the client's pending record for a cast in flight (0x008148F0
adds it for any agent but the observer) -- at the cast's START, beside its [60] / [50].
SKILLS-AC8 saw retail's Koss open it 0.75 s earlier, at the previous spell's [58], 4 of 4,
and 65.7 saw 322's E4 lead its [50] by 0.39-8.48 s. This reads every non-observer E4 on
the corpus (heroes only: a henchman sends none, 0 of 532 casts) against that agent's next
START and asks what the gap is.

THE INSTRUMENT. Per live connection (deepwoundjoin.sequence, framed whole; the observer by
spellhitjoin.observer_of), every 0x00E4 [agent, skill, copy] of an agent other than the
observer, with:
  * its START -- that agent's next 0x009F / 0x00A0 property 60 (a cast), 50 (an attack
    skill) or 48 (an instant), within MAX_S, and the skill it names;
  * its CLOSE -- that agent's next 0x00E3 / 0x00E2 for the skill;
  * what came before it: the agent's last close / start / swing ([58] [46] [59] [49] [45]
    [60] [50] [48] [4]) and how long before;
  * what came between it and the start: the agent's 0x002A / 0x0029 (a walk), its [4]
    swing starts, and its [62] debit.
A row is classed by the first rule it meets:
  with-start   the start is within SAME_S of the E4;
  dropped      no start; the record closes by E2 with a [45, agent, 0] in its instant;
  aftercast    the agent's last action before the E4 is a [58] less than AFTER_LO
               before it -- a pick made inside that spell's aftercast;
  walk         the agent walks between the E4 and its start;
  swing        the start is a [50] and the agent's last action before the E4 is a swing
               start [4] -- an attack skill queued behind its own swing;
  other        none of the above.

THE PREDICTIONS. Written AFTER a scratch census of the same 69 rows on 2026-10-09 (the
hq_census of the HERO QUEUE session) -- so this is a re-derivation with a reader of its
own, NOT a blind test, and labelled so. What it pins is what that census read:
  Q1  every E4 whose agent was idle at it rides its start: with-start, lead 0.000, and
      none of those leads above SAME_S.
  Q2  AFTERCAST: every pick made inside a spell's aftercast starts 0.70-0.80 s after
      that [58], in the agent's own E3 batch (4 rows, Koss on 20261008T132845, each
      picked AT the [58]: 0.000 x3, 0.020).
  Q3  SWING: an attack skill picked behind its swing starts at that swing's start +
      SWING_LO..SWING_HI (0.85-0.95 s; the sword, 1.33 s), and its E4 comes after the
      swing's hit, never before (10 rows; an 11th, 382 at 435.199, waits the previous
      attack skill's own close instead and is classed other).
  Q4  WALK: the walk-in rows lead by > 1 s (8 rows: 322 x7, 382 x1).
  Q5  the [62] debit rides the START, never an E4 that leads it (every paid row).
  Q6  the one drop is E4, [45], E2 in one instant (392.729, 385).
  Q7  OURS (`--ours`): before the HERO QUEUE every hero E4 rides its start -- 0 rows
      in the aftercast or swing classes on a capture that has picks held by either.

AS RUN, 2026-10-09 (two hero connections, Koss on both: 20260914T005758 :56011, 50 E4s;
20261008T132845 :51409, 19): with-start 45 (17 spells, 24 instants, 4 attack skills; max
lead 0.000) -- Q1 HOLDS; aftercast 4 at 0.729 / 0.747 / 0.748 / 0.751 -- Q2 HOLDS; swing
10 at the swing's start + 0.880-0.909, every E4 after the hit -- Q3 HOLDS; walk 8 at
1.858-8.479 -- Q4 HOLDS; the [62] at the start 47 of 47 -- Q5 HOLDS; the drop 1 (392.729,
385; its fight target 44 dies on the wire 0.039 s later) -- Q6 HOLDS; other 1 (above).

Read-only; standard library only; refuses nothing it cannot frame (deepwoundjoin does).
"""
import argparse
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

OP_INT = 0x009F             # [prop, agent, value]
OP_INT_TARGET = 0x00A0      # [prop, agent, target, value]
OP_FLOAT = 0x00A2           # [prop, agent, f32]
OP_E2, OP_E3, OP_E4 = 0x00E2, 0x00E3, 0x00E4
OP_WALK, OP_LEAD = 0x002A, 0x0029
P_SWING, P_DROPPED, P_ATK_STOP, P_ATK_START = 4, 45, 49, 50
P_ATK_FIN, P_INSTANT, P_FIN, P_STOP, P_CAST = 46, 48, 58, 59, 60
P_HIT, P_SPENT = 1, 62
STARTS = (P_CAST, P_ATK_START, P_INSTANT)
BEFORE = (P_FIN, P_ATK_FIN, P_STOP, P_ATK_STOP, P_DROPPED, P_CAST, P_ATK_START, P_INSTANT,
          P_SWING)
SAME_S = 0.05               # one batch, the corpus's shoulder (npcaftercast FLOOR_S's)
MAX_S = 30.0
SWING_LO, SWING_HI = 0.85, 0.95
AFTER_LO, AFTER_HI = 0.70, 0.80


# ---- the pure half: a decoded message list in, rows out ----------------------------

def _names(op, v, agent):
    """Does message (op, v) -- v with the opcode at [0] -- concern `agent` as its actor?"""
    if op in (OP_INT, OP_INT_TARGET, OP_FLOAT):
        return len(v) > 2 and v[2] == agent
    return len(v) > 1 and v[1] == agent


def rows_of(seq, player):
    """[row] for every non-observer 0x00E4 in `seq` ([(index, t, op, values)], values
    carrying the opcode at [0], as deepwoundjoin.sequence returns)."""
    out = []
    for k, (_i, t, op, v) in enumerate(seq):
        if op != OP_E4 or len(v) < 3 or v[1] == player:
            continue
        ag, sk = v[1], v[2]
        row = {"t": round(t, 3), "agent": ag, "skill": sk, "prev": None, "start": None,
               "close": None, "walks": 0, "swings": 0, "spend": None, "hit": None,
               "dropped_word": False}
        for _j, t2, op2, v2 in reversed(seq[:k]):
            if op2 in (OP_INT, OP_INT_TARGET) and len(v2) > 2 and v2[2] == ag \
                    and v2[1] in BEFORE:
                row["prev"] = (round(t - t2, 3), v2[1])
                break
        if row["prev"] and row["prev"][1] == P_SWING:
            # the swing's hit: the agent's [1] (its swing landing) after that swing start
            sw = t - row["prev"][0]
            for _j, t2, op2, v2 in seq[:k + 1]:
                if t2 >= sw and op2 == OP_INT and len(v2) > 2 and v2[1] == P_HIT \
                        and v2[2] == ag:
                    row["hit"] = round(t2 - sw, 3)
                    break
        for _j, t2, op2, v2 in seq[k + 1:]:
            if t2 - t > MAX_S:
                break
            if abs(t2 - t) <= 1e-9 and op2 == OP_INT and v2[1:3] == [P_DROPPED, ag]:
                row["dropped_word"] = True
            if row["start"] is None:
                if op2 in (OP_INT, OP_INT_TARGET) and len(v2) > 2 and v2[2] == ag:
                    if v2[1] in STARTS:
                        row["start"] = (round(t2 - t, 3), v2[1], v2[-1])
                    elif v2[1] == P_SWING:
                        row["swings"] += 1
                if op2 in (OP_WALK, OP_LEAD) and len(v2) > 1 and v2[1] == ag:
                    row["walks"] += 1
            if row["spend"] is None and op2 == OP_FLOAT and len(v2) > 2 \
                    and v2[1] == P_SPENT and v2[2] == ag:
                row["spend"] = round(t2 - t, 3)
            if op2 in (OP_E3, OP_E2) and len(v2) > 2 and v2[1] == ag and v2[2] == sk:
                row["close"] = (round(t2 - t, 3), "E3" if op2 == OP_E3 else "E2")
                break
        row["cls"] = classify(row)
        out.append(row)
    return out


def classify(r):
    st, prev = r["start"], r["prev"]
    if st is not None and st[0] <= SAME_S:
        return "with-start"
    if st is None:
        return ("dropped" if r["close"] and r["close"][1] == "E2" and r["close"][0] <= SAME_S
                and r["dropped_word"] else "other")
    if prev and prev[1] == P_FIN and prev[0] < AFTER_LO:
        return "aftercast"
    if r["walks"]:
        return "walk"
    if st[1] == P_ATK_START and prev and prev[1] == P_SWING:
        return "swing"
    return "other"


def score(rows):
    """The predictions' arithmetic over classed rows."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["cls"]].append(r)
    ws = by["with-start"]
    ac = by["aftercast"]
    sw = by["swing"]
    wk = by["walk"]
    dr = by["dropped"]
    sw_gap = [round(r["prev"][0] + r["start"][0], 3) for r in sw]
    paid = [r for r in rows if r["spend"] is not None and r["start"] is not None]
    res = {
        "n": len(rows), "classes": {k: len(v) for k, v in sorted(by.items())},
        "q1": bool(ws) and all(r["start"][0] <= SAME_S for r in ws),
        "with_start_max": max((r["start"][0] for r in ws), default=None),
        "aftercast_leads": sorted(r["start"][0] for r in ac),
        "aftercast_gaps": sorted(round(r["prev"][0] + r["start"][0], 3) for r in ac),
        "q2": bool(ac) and all(AFTER_LO <= r["prev"][0] + r["start"][0] < AFTER_HI
                               for r in ac),
        "swing_gaps": sorted(sw_gap),
        "swing_e4_after_hit": sum(1 for r in sw if r["hit"] is not None
                                  and r["prev"][0] >= r["hit"]),
        "q3": bool(sw) and all(SWING_LO <= g <= SWING_HI for g in sw_gap)
        and all(r["hit"] is not None and r["prev"][0] >= r["hit"] for r in sw),
        "walk_leads": sorted(r["start"][0] for r in wk),
        "q4": bool(wk) and all(r["start"][0] > 1.0 for r in wk),
        "spend_at_start": sum(1 for r in paid if abs(r["spend"] - r["start"][0]) <= SAME_S),
        "paid": len(paid),
        "q6": [(r["t"], r["skill"]) for r in dr],
    }
    res["q5"] = res["paid"] > 0 and res["spend_at_start"] == res["paid"]
    res["queued"] = len(ac) + len(sw)
    return res


# ---- the vault half ------------------------------------------------------------------

def census():
    import bufflog          # noqa: E402
    import deepwoundjoin    # noqa: E402
    import spellhitjoin     # noqa: E402
    import vaultpath        # noqa: E402
    codec = bufflog.Codec()
    live = vaultpath.require_dir("captures", "live", why="heroqueue reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        for ch in deepwoundjoin.whole_s2c(cap, []):
            seq = deepwoundjoin.sequence(cap, ch["connection"], codec)
            if not any(op == OP_E4 for _i, _t, op, _v in seq):
                continue
            me, _p, _why = spellhitjoin.observer_of(seq, spellhitjoin.c2s_of(cap, ch["file"]))
            for r in rows_of(seq, me):
                r["capture"] = stamp
                r["connection"] = ch["connection"]
                out.append(r)
    return out


def ours(path):
    """The rows of one of OUR recorder captures (observer agent 1)."""
    import timingjoin       # noqa: E402
    label, s2c, me = timingjoin.load_ours(path)
    return label, rows_of([(i, t, op, v) for i, (t, op, v) in enumerate(s2c)], me)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rows", action="store_true", help="print every hero E4, classed")
    ap.add_argument("--ours", help="one of our recorder captures (authsrv-*-c1.jsonl)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    with contextlib_redirect(args.json):
        rows = census()
    res = {"retail": score(rows)}
    if args.ours:
        label, orows = ours(args.ours)
        res["ours"] = dict(score(orows), label=label)
    if args.json:
        print(json.dumps(res, indent=1, default=str))
        return res
    if args.rows:
        for r in rows:
            print(f"{r['capture']} {r['t']:9.3f} ag {r['agent']} sk {r['skill']:4d} "
                  f"{r['cls']:10s} start {r['start']} prev {r['prev']} hit {r['hit']} "
                  f"walks {r['walks']} spend {r['spend']} close {r['close']}")
    for side in ("retail", "ours"):
        if side not in res:
            continue
        s = res[side]
        print(f"{side.upper()}: {s['n']} hero E4s, classes {s['classes']}")
        print(f"  Q1 with its start: max lead {s['with_start_max']} -> "
              f"{'HOLDS' if s['q1'] else 'FAILS'}")
        print(f"  Q2 aftercast: E4 -> start {s['aftercast_leads']}, [58] -> start "
              f"{s['aftercast_gaps']} -> {'HOLDS' if s['q2'] else 'FAILS'}")
        print(f"  Q3 swing start -> [50] {s['swing_gaps']}, E4 after the hit "
              f"{s['swing_e4_after_hit']} of {s['classes'].get('swing', 0)} -> "
              f"{'HOLDS' if s['q3'] else 'FAILS'}")
        print(f"  Q4 walk leads {s['walk_leads']} -> {'HOLDS' if s['q4'] else 'FAILS'}")
        print(f"  Q5 the [62] at the start {s['spend_at_start']} of {s['paid']} -> "
              f"{'HOLDS' if s['q5'] else 'FAILS'}")
        print(f"  Q6 drops {s['q6']}; queued picks (aftercast + swing) {s['queued']}")
    return res


class contextlib_redirect:
    """stderr for the census's SET ASIDE lines when --json owns stdout (npcaftercast's
    EV-7 rule: --json's stdout is one document)."""

    def __init__(self, on):
        self.on = on

    def __enter__(self):
        if self.on:
            self.saved = sys.stdout
            sys.stdout = sys.stderr
        return self

    def __exit__(self, *exc):
        if self.on:
            sys.stdout = self.saved
        return False


if __name__ == "__main__":
    main()
