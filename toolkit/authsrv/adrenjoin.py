r"""The adrenaline census, stratified by whether the player's bar can hold any.

    python toolkit/authsrv/adrenjoin.py              # the split, and the join
    python toolkit/authsrv/adrenjoin.py --rows       # every damage row, sorted
    python toolkit/authsrv/adrenjoin.py --json       # for another tool

WHAT IT IS FOR, AND THE TRAP IT EXISTS TO STOP. `pools.damage_units` grants one
adrenaline unit per 1% of maximum health lost, rounded to nearest, and the
rounding was measured on 2026-08-21 by joining GAIN -> DAMAGE: 32 sub-25
`0x00CF`s, 31 joinable, round fits 31 of 31. That population is SELECTED ON THE
OUTCOME -- every row in it is a damage event that DID produce a gain -- so it
cannot contain the band where the rule stops granting, and the docstring said
so: "which side of it retail lands on is UNVERIFIED".

The obvious repair is to run the join the other way, DAMAGE -> GAIN, over every
`0x00A3` naming the observer as target. Run naively that produces a confident
and completely wrong answer: 32 damage events granting nothing, the largest of
them **7.5% of maximum health**, which read at face value would put retail's
cutoff an order of magnitude above the wiki's and refute round() outright.

It is an artifact of a variable nobody had stratified on. Every one of those 32
rows is in a connection whose player carries NO ADRENALINE SKILL ON THE BAR, and
in those connections retail's server sends no `0x00CF` AT ALL -- not for damage
taken, and not for the 45 weapon hits and 13 completed melee attacks those same
connections contain. Split on the bar and the corpus is two clean populations
(see `studies/skills/FINDINGS.md` 34):

    ARMED bars  36 connections   918 gains,  27 clears, 40 spends
    DARK  bars  22 connections     0 gains,   0 clears,  0 spends

That accounts for the whole family census exactly, which is this scanner's own
consistency check -- `test_adrenwire`'s CENSUS is 918/27/0/40 and the ARMED
column reproduces it from a completely different query.

WHAT IT DOES NOT SETTLE, and this is the point of running it: the gate's
variable is CONFOUNDED. Every DARK connection is also a non-Warrior character,
so "the bar carries an adrenal skill" and "the profession uses adrenaline" fit
the same 58 connections and this corpus cannot separate them. Both are recorded
as candidates; neither is implemented in the sender.

READ-ONLY. It opens `vault/captures/live/` and writes nothing anywhere.
Standard library only, like everything else on this path.
"""
import argparse
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "schema"))

import content      # noqa: E402
import tape         # noqa: E402
import vaultpath    # noqa: E402
from codec import Codec  # noqa: E402

PROP_INT = 0x009F           # [prop, agent, value]
PROP_FLOAT_SELF = 0x00A2    # [prop, agent, f32]           -- no source field
PROP_FLOAT_TARGET = 0x00A3  # [prop, target, source, f32]
SKILLBAR_UPDATE = 0x00DA    # [agent, skills[8], ...]
ADRENALINE_GAIN = 0x00CF
ADRENALINE_CLEAR = 0x00D0
ADRENALINE_SPEND = 0x00D2

PROP_MAX_ENERGY = 41        # SELF-SCOPED -- see whose_agent below
PROP_MAX_HEALTH = 42        # re-sent on change -- see whose_max_health below
PROP_MELEE_FINISHED = 1
DAMAGE_PROPS = (16, 17)     # both carry a negative fraction of max health
STRIKE_UNITS = 25

# DAMAGE ARRIVES ON BOTH FLOAT CHANNELS, and the sourceless one is easy to miss
# because it is rare: 0x00A3 carries 63 damage events at the observer and 0x00A2
# carries ONE. That one is a 6.25% hit granting 6 units, and a scan that reads
# only 0x00A3 reports it as a gain with no damage anywhere near it. The first
# pass of this scanner did exactly that, printed the orphan, and moved on; a
# blind replication run the same hour chased it instead and found the channel.
# Hence: an unexplained row is a lead, and the ledger closing at 918 of 918 is
# what says none is left.
DAMAGE_OPS = (PROP_FLOAT_SELF, PROP_FLOAT_TARGET)


def f32(dw):
    """Four bytes read as a float, because reading them as an int never errors.

    Same trap `moralescan.s32` documents from the signed side: property 16's
    payload is IEEE-754 and 3,172,012,305 is a perfectly plausible-looking
    integer for -0.0354.
    """
    return struct.unpack("<f", struct.pack("<I", int(dw) & 0xFFFFFFFF))[0]


# PRINT NINE DECIMALS, AND THAT IS NOT FUSSINESS. The single most interesting
# damage event in the corpus is 0xBC23D70A = -0.009999999776482582, which four
# decimals render as "1.0000%" -- and 1.0% is exactly where the two surviving
# rules AGREE. Read from the bytes it is 0.999999978%, just below, where they
# do NOT. Three independent readers (this scanner and two replication agents)
# printed it rounded and all three read past it. studies/skills 34.D.
PCT_FMT = "%12.9f"


def whose_max_health(msgs, me, before):
    """The observer's maximum health IN FORCE at stream index `before`.

    NOT the last one in the connection, and not any one of them. Property 42 is
    re-sent when it changes -- a death penalty moves it, and so does a gear
    change -- so a connection can carry 120 for its whole fight and 102 three
    thousand messages later. Two replication agents both took a set of the
    values and both assigned the WRONG maximum to two connections; the skeptic
    pass caught it from the bytes. Immaterial to the rule as it happens (those
    rows are excluded anyway, and all four ARMED connections carry only 480),
    material as a method: a denominator read non-temporally is a denominator
    that can be silently wrong.

    The leading 1 is skipped: property 42 arrives as the PAIR (1, real_max) for
    every own agent in the corpus, which `pools.py`'s header records as
    unexplained and which nothing here depends on.
    """
    seen = [int(v[3]) for i, (_t, op, v) in enumerate(msgs)
            if op == PROP_INT and len(v) > 3 and int(v[1]) == PROP_MAX_HEALTH
            and int(v[2]) == me and i < before and int(v[3]) > 1]
    return seen[-1] if seen else None


def whose_agent(msgs):
    """The observing player's agent id, or None. NO FALLBACK.

    Property 41 on the int channel is self-scoped. This is `moralescan.py`'s
    corrected rule and it is corrected for a measured reason: identifying the
    observer by the first `0x0059` was WRONG ON 20 OF 44 CONNECTIONS
    (studies/skills 26.13), because the server broadcasts one of those per
    player in the instance.

    AND DO NOT BE TEMPTED TO USE "the agent named by a 0x00CF" HERE. It is
    right on every connection that has one, and it would silently delete the
    entire DARK population from the denominator -- the connections with no
    gains are exactly the ones this scanner exists to count. That is the
    outcome-selection defect one level down, and it would have hidden the
    finding rather than producing a wrong number, which is worse.
    """
    seen = {int(v[2]) for _t, op, v in msgs
            if op == PROP_INT and len(v) > 2 and int(v[1]) == PROP_MAX_ENERGY}
    return seen.pop() if len(seen) == 1 else None


def adrenal_costs():
    """skill id -> raw adrenaline cost, from our own extracted table."""
    return {int(k): int(r.get("adrenaline_units") or 0)
            for k, r in content.load().rows("skills").items()}


def scan(costs=None):
    """Walk the live corpus once. Returns (stats, rows, skipped)."""
    costs = adrenal_costs() if costs is None else costs
    live = vaultpath.require_dir("captures", "live",
                                 why="the adrenaline census")
    codec = Codec()
    stats = {"armed": collections.Counter(), "dark": collections.Counter()}
    rows, skipped, captures = [], [], 0

    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        captures += 1
        for chan in tape.channel_files(cap):
            conn = chan["connection"]
            try:
                _info, events = tape.load_tape(cap, conn)
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            me = whose_agent(msgs)
            if me is None:
                skipped.append({"capture": stamp, "connection": conn})
                continue

            bars = [tuple(int(x) for x in v[2]) for _t, op, v in msgs
                    if op == SKILLBAR_UPDATE and len(v) > 2 and int(v[1]) == me]
            on_bar = {s for bar in bars for s in bar if s}
            adrenal = sorted(s for s in on_bar if costs.get(s, 0) > 0)
            arm = "armed" if adrenal else "dark"
            s = stats[arm]
            s["connections"] += 1
            s["messages"] += len(msgs)

            for _t, op, v in msgs:
                if op == ADRENALINE_GAIN and int(v[1]) == me:
                    s["gain"] += 1
                    s["strike" if int(v[2]) == STRIKE_UNITS else "sub"] += 1
                elif op == ADRENALINE_CLEAR and int(v[1]) == me:
                    s["clear"] += 1
                elif op == ADRENALINE_SPEND and int(v[1]) == me:
                    s["spend"] += 1
                elif op in DAMAGE_OPS and int(v[1]) in DAMAGE_PROPS:
                    if int(v[2]) == me:
                        s["damage_taken"] += 1
                    # only 0x00A3 names a source, so only it can say who landed
                    if op == PROP_FLOAT_TARGET and int(v[3]) == me:
                        s["hits_landed"] += 1
                elif (op == PROP_INT and len(v) > 2
                        and int(v[1]) == PROP_MELEE_FINISHED and int(v[2]) == me):
                    s["melee_finished"] += 1

            # THE JOIN IS BY BATCH, and a batch is an identical timestamp. The
            # gain and its damage ride one batch -- gain FIRST, 601 of 663
            # by the following message (test_adrenwire 7).
            batches = collections.defaultdict(list)
            for i, (t, op, v) in enumerate(msgs):
                batches[t].append((i, op, v))
            for t, items in batches.items():
                dmg = [(i, int(v[1]),
                        int(v[3]) if op == PROP_FLOAT_TARGET else None,
                        f32(v[4] if op == PROP_FLOAT_TARGET else v[3]))
                       for i, op, v in items
                       if op in DAMAGE_OPS and int(v[1]) in DAMAGE_PROPS
                       and int(v[2]) == me]
                sub = [(i, int(v[2])) for i, op, v in items
                       if op == ADRENALINE_GAIN and int(v[1]) == me
                       and int(v[2]) != STRIKE_UNITS]
                if not dmg:
                    continue
                # A BATCH WITH n DAMAGE AND n IDENTICAL GAINS ATTRIBUTES BY
                # SYMMETRY, and refusing to is over-caution that costs rows.
                # The two batches this covers each carry two 6.0417% hits and
                # two 6-unit gains: every assignment gives the same pair, so
                # there is nothing to get wrong. Anything else -- unequal
                # counts, unequal values -- stays ambiguous and is REPORTED,
                # never attributed to whichever damage sorted first.
                symmetric = (len(dmg) == len(sub) and len(sub) > 0
                             and len({u for _i, u in sub}) == 1
                             and len({round(d[3], 9) for d in dmg}) == 1)
                clean = len(dmg) == 1 or symmetric
                for di, prop, src, val in dmg:
                    rows.append({
                        "capture": stamp, "connection": conn, "arm": arm,
                        "index": di, "t": t, "prop": prop, "source": src,
                        "max_health": whose_max_health(msgs, me, di),
                        "value": val, "pct": abs(val) * 100.0,
                        "units": (sub[0][1] if sub and clean else None),
                        "ambiguous": not clean,
                        "adrenal_on_bar": adrenal,
                    })
    return {"captures": captures, "arms": stats}, rows, skipped


def fits(rows):
    """floor / ceil / round, counted over the unambiguous rows that granted."""
    out = collections.Counter()
    for r in rows:
        if r["ambiguous"] or r["units"] is None:
            continue
        pct = r["pct"]
        out["n"] += 1
        for name, val in (("floor", math.floor(pct)),
                          ("ceil", math.ceil(pct)),
                          ("round", int(math.floor(pct + 0.5 + 1e-9)))):
            if val == r["units"]:
                out[name] += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true",
                    help="print every damage-to-self row, sorted by percentage")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    stats, rows, skipped = scan()
    if args.json:
        print(json.dumps({"stats": {k: dict(v) for k, v in stats["arms"].items()},
                          "captures": stats["captures"],
                          "rows": rows, "skipped": skipped}, indent=2))
        return 0

    print(f"captures {stats['captures']}   skipped (no unique self agent) "
          f"{len(skipped)}")
    for s in skipped:
        print(f"   {s['capture']}  {s['connection']}")
    print()
    for arm in ("armed", "dark"):
        d = stats["arms"][arm]
        label = ("ARMED -- at least one adrenal skill on the bar" if arm == "armed"
                 else "DARK  -- no adrenal skill, ever, on the bar")
        print(f"{label}")
        print(f"   {d['connections']:3} connections, {d['messages']:6} messages")
        print(f"   0x00CF gain  {d['gain']:5}  ({d['strike']} at {STRIKE_UNITS}, "
              f"{d['sub']} below)")
        print(f"   0x00D0 clear {d['clear']:5}      0x00D2 spend {d['spend']:5}")
        print(f"   damage taken {d['damage_taken']:5}   hits landed "
              f"{d['hits_landed']:5}   melee finished {d['melee_finished']:5}")
        print()

    for arm in ("armed", "dark"):
        mine = [r for r in rows if r["arm"] == arm and not r["ambiguous"]]
        gained = [r for r in mine if r["units"] is not None]
        none = [r for r in mine if r["units"] is None]
        print(f"{arm.upper():6} damage-to-self, unambiguous batches {len(mine):3}"
              f"   granted {len(gained):3}   granted nothing {len(none):3}")
        if mine:
            print(f"       percentage range "
                  f"{min(r['pct'] for r in mine):.9f} .. "
                  f"{max(r['pct'] for r in mine):.9f}")
            band = [r for r in mine if 0.5 <= r["pct"] < 1.0]
            print(f"       in the band where round and ceil DISAGREE "
                  f"[0.5%, 1.0%): {len(band)} rows"
                  + (f" -- {[round(r['pct'], 9) for r in band]}" if band else ""))
        if gained:
            f = fits(mine)
            print(f"       over {f['n']} joined rows: floor {f['floor']}, "
                  f"ceil {f['ceil']}, round {f['round']}")
            units = collections.Counter(r["units"] for r in gained)
            print(f"       units granted {dict(sorted(units.items()))}")
        print()

    if args.rows:
        print("       pct        units  floor ceil round  maxH  prop  arm   capture")
        print("   " + "-" * 76)
        for r in sorted(rows, key=lambda r: (r["arm"], r["pct"])):
            pct = r["pct"]
            print(f"   {pct:12.9f} {str(r['units']):>6}  "
                  f"{math.floor(pct):5} {math.ceil(pct):4} "
                  f"{int(math.floor(pct + 0.5 + 1e-9)):5}  "
                  f"{str(r['max_health']):>4}  {r['prop']:4}  "
                  f"{r['arm']:5}  {r['capture']}"
                  + ("  AMBIGUOUS" if r["ambiguous"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
