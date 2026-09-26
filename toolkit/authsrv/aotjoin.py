r"""Areas over time on retail's wire: every Fire Storm cast, its completion, its ground visual and its ticks.

    python toolkit/authsrv/aotjoin.py              # every live capture: P1-P9, PASS/FAIL per line
    python toolkit/authsrv/aotjoin.py --rows       # plus one block per cast (batches in wire order)
    python toolkit/authsrv/aotjoin.py --json
    python toolkit/authsrv/aotjoin.py --stamp 20260817T231139   # one capture

WHY THIS EXISTS. DESKWORK-D6 step 1 (studies/deskwork/PLAN.md): the record's target byte
16 marks fourteen areas over TIME (a spell with a duration, ticking at a point) and the
server builds none of them. The one with a retail witness is Fire Storm (197): seventeen
casts on `20260817T231139`. Two written sources described that witness and disagreed --
weapons PLAN §40 said ONE ground `0x00A1 350` in the completion batch, D6 said "three
ground-350 0x00A1s" and "words at +3, +4, +5 s". This reader re-derives the shape from
the bytes, before any server line is written (D6: "no server change until the shape is
locked"), and `test_weapons.py` section 29 locks what it prints. It is the committed port
of the DESKWORK-D6 tape lane's scratch join (2026-09-26), including that lane's one fix
(THE COMPLETION below).

METHOD. Captures come from `livewire.live_captures()` -- origin LIVE only (origin.py's
refuse-to-mix rule at the loader), behind `vaultpath.require_dir` so a missing vault
raises instead of scanning nothing. Each game connection is decoded by
`deepwoundjoin.sequence`, which REFUSES a connection that does not frame whole (refusals
are counted and printed). The observer is `spellhitjoin.observer_of` (property 41
cross-checked against the answered c2s presses), computed only on a connection that
carries a cast -- the c2s decode is most of the cost.

THE CLASSIFIER (`classify`, pure, on the client's own skill rows, `agents.WORLD`):
  area over time   target byte 16, type 5 (Spell), no projectile (2077, the table's
                   "none", or 0 / absent), a duration (duration0 or duration15 > 0) and
                   aoe_range > 0.
  area hex         target byte 16, type 4 (Hex), aoe_range > 0.
  other            every other target-16 row (a projectile burst, a single-packet burst).
On the pinned table that is 14 / 7 / 13 (OBSERVED, 2026-09-26). Weapons PLAN §40's
heading says "Fifteen" areas over time and "Ten" single-packet bursts while its own lists
name 14 and 11 -- the counts, not the lists, were wrong.

WIRE SHAPES (decoded values carry the header at v[0]):
  0x00A0 [160, prop, a, b, value]      prop 60: [60, caster, target, skill] (the announce)
  0x009F [159, prop, agent, value]     prop 58: the skill finished; prop 10: skill damage
                                       naming the skill; prop 60 untargeted announce
  0x00A1 [161, (x, y), w, agent, effect, b, b]   an effect at a point (350 = the ground)
  0x00A3 [163, prop, target, cause, f32]         16/17 damage (a negative fraction)
  0x00CF [207, agent, n]               adrenaline gain (adrenjoin.ADRENALINE_GAIN)
  0x00F1 [241, agent, status]          bit 0x10 = dead (agents.py)
  0x0020 create: v[1] agent, v[4] kind, v[5] (x, y), v[12] allegiance token
  0x001E the world simulation tick -- skipped when reading batch order

THE COMPLETION. The first `[58, caster, 0]` at least COMPLETION_MIN (0.5 s) after the
announce whose caster's latest announce is this one. The first cut took the first 58
after the announce and on one cast (54071, announce 638.048) that was a PREVIOUS skill's
58 sharing the announce's batch -- its three 350s then came out "unattributed". The fix
is the lane's; the real completion there is +2.000.

A TICK is a group of the caster's damage words (cause = caster) whose instant sits within
TICK_TOL (0.05 s) of completion + k s, k = 1..12. A tick batch is CLEAN when it carries
no 58, no `[20]` and no `0x00A7` from the caster; a MIXED batch (another announced skill
of the same caster completing in the same instant) keeps only the words whose value is
that (caster, target) pair's clean-tick value, once (a Mind Burn twin is two identical
words, never a tick). CLEAN IS A DEFINITION, so "no 58 on a clean tick" would be true by
construction; P6 below is stated on what the definition does not force.

THE PREDICTIONS, registered before this reader ran (DESKWORK-D6's acceptance, and the
orchestrator's spec §0 from the scratch lane's counts; a reader that disagrees refutes
them, not the tape):

  P1  On `20260817T231139`: exactly 17 Fire Storm announces, 13 + 2 + 1 + 1 over four
      connections (ports 54071, 50527, 50513, 50286), all `0x00A0 [60, caster, target,
      197]`, none by the connection's observer. Scored PER TAPE: a later capture with
      more Fire Storms is confirming evidence and must not redden a corpus total.
  P2  Every cast completes with ONE `[58, caster, 0]` at announce + 2.0 +- 0.05 s (the
      record's activation 2.0), and the completion batch holds no other agent's 58.
  P3  In every completion batch the ground `0x00A1 [P, 0, 0, 350, 0, 0]` is the message
      IMMEDIATELY after the caster's 58 (0x001E skipped), exactly one 350 in the batch.
  P4  The 350 is re-sent at the same point at completion + 3 and + 6 (+- 0.05 s), and
      nowhere else: every 350 at P sits at 0, 3 or 6 s, three per cast.
  P5  Ticks fall at completion + k s for k = 1..10 only (none at k = 0, none at k >= 11),
      phase |offset - k| <= 0.100 s; and no CLEAN group of the caster's words carrying
      a pair's tick value falls OUTSIDE the tick gate or in the completion batch (a
      drifted tick would land there -- the arm that lets the phase half fail although
      the gate is 0.05 s). (First run, 2026-09-26: FAILED on the arm as first coded --
      it counted a wand hit on 54071 at +10.653, an 0x00A4 launch and an 0x00A7 in its
      batch, whose ~17 health equals the pair's -0.0306. The operand was wrong, not the
      tape: a group carrying an 0x00A7, a [20] or the caster's 58 is another action.
      The registered half -- k = 1..10, phase within 0.100 -- held on that run.)
  P6  No tick carries a 58 attributed to Fire Storm itself, and every tick batch that
      carries a `[20]` or an `0x00A7` from the caster also carries that caster's 58 of
      ANOTHER announced skill (the visual is the other skill's, not the tick's).
  P7  0 unattributed 350s: every `0x00A1 ... 350` in the corpus sits at a Fire Storm
      area's point (1 u) inside its lifetime (completion - 0.05 .. + 11 s).
  P8  0 announces (0x00A0 / 0x009F props 60, 50, 48, or the observer's own E2..E5) of
      any OTHER area over time or of any of the seven area hexes, corpus-wide.
  P9  0 monster takers: every agent a tick struck has a create, and none carries a
      monster allegiance token (MONSTER_TOKENS, agents.py's vocabulary) -- the corpus's
      whole scatter witness (there is none; every area on tape is PvP).

ALSO REPORTED, not predicted (spec §0): the `[55, caster, caster, +f]` self health gain
before the 58 (a heal in the caster's build, NOT energy -- property 55 is a health gain,
agents.py); the observer-hit prefix (`0x00CF [obs, 4]` then `0x009F [10, obs, 197]` then
the word); the 350's place in a tick batch (before the words); per-tick foe counts;
constant fraction per (cast, target); dead takers never struck; casters walking or dying
with the area live.

What this reader does NOT settle: who stands inside aoe 156 at each tick (every
non-observer position on these tapes is a lead -- shoutjoin's lead check, median 765 u);
whether the caster's death ends the area (2 casts, both areas already empty: printed,
INCONCLUSIVE); monster scatter (no witness, P9); any other area over time (P8).

Standard library only; reads the vault through `vaultpath`.
"""
import argparse
import bisect
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import agents           # noqa: E402  (the client's skill rows: the classifier's input)
import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402  (sequence: refuses a connection that does not frame whole)
import livewire         # noqa: E402  (live_captures: origin LIVE only)
import spellhitjoin     # noqa: E402  (observer_of / c2s_of)
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_CREATE = 0x0020
OP_SIM_TICK = 0x001E       # the world simulation tick; not part of any batch's order
OP_LEAD = 0x0029
OP_DEST = 0x002A
OP_POSITION = 0x002C
OP_INT = 0x009F
OP_INT_TARGET = 0x00A0
OP_POINT_EFFECT = 0x00A1
OP_FLOAT_TARGET = 0x00A3
OP_A7 = 0x00A7
OP_ADRENALINE = 0x00CF     # adrenjoin.ADRENALINE_GAIN
OP_STATUS = 0x00F1
OWN_OPS = (0x00E2, 0x00E3, 0x00E4, 0x00E5)
PROP_SKILL_DAMAGE = 10
PROP_EFFECT_ON_TARGET = 20
PROP_DAMAGE = (16, 17)
PROP_HEALTH_GAIN = 55
PROP_FINISHED = 58
PROP_ANNOUNCE = 60
ANNOUNCE_PROPS = (60, 50, 48)
DEAD_BIT = 0x10

AREA_TARGET_BYTE = 16
TYPE_SPELL = 5
TYPE_HEX = 4
NO_PROJECTILE = 2077       # skilltable.NO_PROJECTILE: the table's "none"
FIRE_STORM = 197
GROUND = 350               # the ground effect the wire draws (the record's impact_visual is 351)
ACTIVATION = 2.0           # s; the record's activation for 197
BATCH = 0.05               # s; one batch's shoulder
COMPLETION_MIN = 0.5       # s; a 58 closer to the announce belongs to a previous skill
COMPLETION_TOL = 0.05      # s; P2
TICK_TOL = 0.05            # s; a caster word group this close to completion + k is a tick
PHASE_LIMIT = 0.100        # s; P5 (D6: "a phase drift over 100 ms refutes")
VISUAL_AT = (0.0, 3.0, 6.0)   # s after the completion; P4
VISUAL_TOL = 0.05
AREA_LIFE = 11.0           # s after the completion a 350 at the point may sit (P7)
WINDOW = 12.5              # s after the completion scanned for the area's words
POINT_EPS = 1.0            # u; the same ground point
KMAX = 12                  # the gate looks for ticks up to k = 12, so k = 11 / 12 can FAIL P5

# P1's prior, per tape (the scratch lane's counts, D6's acceptance (a)).
EXPECT_CAPTURE = "20260817T231139"
EXPECT_PER_PORT = {"54071": 13, "50527": 2, "50513": 1, "50286": 1}
EXPECT_TICKS_K = tuple(range(1, 11))   # duration 10 at a 1 s period

# agents.py's MEASURED token vocabulary (2026-08-17): the hostile creatures' tokens.
# 'mon1', 'mons', 'anim', 'band', and 'ani' + 0x8F (definition 3973).
MONSTER_TOKENS = (0x6D6F6E31, 0x6D6F6E73, 0x616E696D, 0x62616E64, 0x616E698F)


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def _xy(v):
    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) and len(v) >= 2 else None


def _int(x, default=0):
    try:
        return int(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def _token(tok):
    try:
        return int(tok).to_bytes(4, "big").decode("latin1")
    except (TypeError, ValueError, OverflowError):
        return repr(tok)


def classify(rows):
    """(aot, ahex, other): three {skill_id: row} dicts over the target-16 rows.

    aot   = type 5, no projectile, a duration, aoe_range > 0 (an area over time);
    ahex  = type 4, aoe_range > 0 (an area hex);
    other = every other target-16 row. Pure: `rows` is {id: row}, ids int or str."""
    aot, ahex, other = {}, {}, {}
    for key, r in rows.items():
        if _int(r.get("target"), -1) != AREA_TARGET_BYTE:
            continue
        sid = int(key)
        tc = _int(r.get("type_code"), -1)
        proj = _int(r.get("projectile"), NO_PROJECTILE)
        dur = _int(r.get("duration0")) > 0 or _int(r.get("duration15")) > 0
        try:
            radius = float(r.get("aoe_range") or 0.0)
        except (TypeError, ValueError):
            radius = 0.0
        if tc == TYPE_SPELL and proj in (0, NO_PROJECTILE) and dur and radius > 0.0:
            aot[sid] = r
        elif tc == TYPE_HEX and radius > 0.0:
            ahex[sid] = r
        else:
            other[sid] = r
    return aot, ahex, other


def skills_table():
    """{skill_id: row} from the client's own skill rows (agents.WORLD)."""
    return {int(k): r for k, r in agents.WORLD.rows("skills").items()}


def _fmt(op, v):
    if op == OP_FLOAT_TARGET and len(v) > 4:
        return f"0x{op:04X} {[v[1], v[2], v[3], round(_f32(v[4]), 4)]}"
    if op == OP_POINT_EFFECT and len(v) > 6 and _xy(v[1]):
        p = _xy(v[1])
        return f"0x{op:04X} [({p[0]:.1f},{p[1]:.1f}), {v[2]}, {v[3]}, {v[4]}, {v[5]}, {v[6]}]"
    s = repr(list(v[1:]))
    return f"0x{op:04X} {s if len(s) < 90 else s[:87] + '...'}"


def rows_of(seq, skill=FIRE_STORM, ground=GROUND):
    """Per-cast rows for every announce of `skill` in one connection's `seq`
    ([(index, t, op, values)], deepwoundjoin.sequence)."""
    times = [t for _i, t, _op, _v in seq]
    creates = {}
    announces = collections.defaultdict(list)     # caster -> [(t, skill, target, form)]
    deaths = collections.defaultdict(list)        # agent -> [(t, dead)]
    moves = collections.defaultdict(list)         # agent -> [(t, xy, op)]
    last_status = {}
    for _i, t, op, v in seq:
        if op == OP_CREATE and len(v) > 12:
            creates[int(v[1])] = (int(v[4]), int(v[12]))
            if _xy(v[5]):
                moves[int(v[1])].append((t, _xy(v[5]), op))
        elif op == OP_INT_TARGET and len(v) > 4 and v[1] == PROP_ANNOUNCE:
            announces[v[2]].append((t, v[4], v[3], "0x00A0"))
        elif op == OP_INT and len(v) > 3 and v[1] == PROP_ANNOUNCE:
            announces[v[2]].append((t, v[3], None, "0x009F"))
        elif op == OP_STATUS and len(v) > 2:
            dead = bool(int(v[2]) & DEAD_BIT)
            if last_status.get(v[1]) != dead:
                deaths[v[1]].append((t, dead))
                last_status[v[1]] = dead
        elif op in (OP_LEAD, OP_DEST, OP_POSITION) and len(v) > 2 and _xy(v[2]):
            moves[int(v[1])].append((t, _xy(v[2]), op))

    def span(a, b):
        return seq[bisect.bisect_left(times, a):bisect.bisect_right(times, b)]

    def batch_of(tc):
        return span(tc - BATCH, tc + BATCH)

    def announce_before(caster, t):
        best = None
        for a in announces.get(caster, ()):
            if a[0] <= t:
                best = a
        return best

    rows = []
    for caster, lst in announces.items():
        for (ta, sk, target, form) in lst:
            if sk != skill:
                continue
            row = {"caster": caster, "target": target, "announce_t": ta,
                   "announce_form": form, "caster_create": creates.get(caster),
                   "target_create": creates.get(target)}
            tc, stop = None, None
            for _i, t, op, v in span(ta, ta + 4.0):
                if op == OP_INT and len(v) > 3 and v[2] == caster and v[1] in (58, 59, 45, 35):
                    if t < ta + COMPLETION_MIN:   # a previous skill's end in the announce batch
                        continue
                    a = announce_before(caster, t)
                    if a is None or a[0] != ta:
                        continue
                    if v[1] == PROP_FINISHED:
                        tc = t
                        break
                    stop = stop or (t, v[1])
            row["completion_t"] = tc
            row["completion_dt"] = None if tc is None else round(tc - ta, 3)
            row["stopped"] = stop
            if tc is None:
                rows.append(row)
                continue
            b = batch_of(tc)
            row["batch"] = [(round(t - tc, 3), _fmt(op, v)) for _i, t, op, v in b]
            ops = [(op, v) for _i, _t, op, v in b if op != OP_SIM_TICK]
            j58 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_INT and v[1] == PROP_FINISHED and v[2] == caster), None)
            row["a1_right_after_58"] = (j58 is not None and j58 + 1 < len(ops)
                                        and ops[j58 + 1][0] == OP_POINT_EFFECT
                                        and ops[j58 + 1][1][4] == ground)
            j55 = next((n for n, (op, v) in enumerate(ops)
                        if op == OP_FLOAT_TARGET and v[1] == PROP_HEALTH_GAIN
                        and v[2] == caster), None)
            row["own55_right_before_58"] = j55 is not None and j58 is not None and j55 + 1 == j58
            row["batch_58s"] = sorted({v[2] for _i, _t, op, v in b
                                       if op == OP_INT and v[1] == PROP_FINISHED})
            row["batch_55"] = [(v[2], v[3], round(_f32(v[4]), 4)) for _i, _t, op, v in b
                               if op == OP_FLOAT_TARGET and v[1] == PROP_HEALTH_GAIN]
            row["completion_words"] = [(v[2], round(_f32(v[4]), 4)) for _i, _t, op, v in b
                                       if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE
                                       and v[3] == caster]
            g = [v for _i, _t, op, v in b if op == OP_POINT_EFFECT and v[4] == ground]
            row["completion_350s"] = len(g)
            P = _xy(g[0][1]) if g else None
            row["point"] = P
            row["completion_350_fields"] = [list(v[2:]) for v in g]
            prev = [(t, p_, o) for t, p_, o in moves.get(target, ()) if t <= tc]
            row["target_last_sample"] = ((round(tc - prev[-1][0], 3), f"0x{prev[-1][2]:04X}",
                                          prev[-1][1]) if prev else None)
            row["target_sample_dist"] = (round(math.dist(P, prev[-1][1]), 1)
                                         if P and prev else None)
            a1 = []
            for _i, t, op, v in span(tc - BATCH, tc + WINDOW):
                if op == OP_POINT_EFFECT and P and _xy(v[1]) \
                        and math.dist(_xy(v[1]), P) <= POINT_EPS:
                    a1.append((round(t - tc, 3), v[4], v[2], v[3]))
            row["a1_at_point"] = a1
            row["visual_offsets"] = [x[0] for x in a1 if x[1] == ground]
            # the caster's damage words, in batches, from 0.3 s after the completion
            groups = []
            for _i, t, op, v in span(tc + 0.3, tc + WINDOW):
                if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[3] == caster:
                    w = (v[2], v[1], round(_f32(v[4]), 4))
                    if groups and t - groups[-1]["t"] <= BATCH:
                        groups[-1]["words"].append(w)
                    else:
                        groups.append({"t": t, "words": [w]})
            ticks, other = [], []
            for gr in groups:
                off = gr["t"] - tc
                k = round(off)
                bb = [(t, op, v) for _i, t, op, v in batch_of(gr["t"]) if op != OP_SIM_TICK]
                own58 = [(round(t - tc, 3), (announce_before(caster, t) or (None, None))[1])
                         for t, op, v in bb if op == OP_INT and v[1] == PROP_FINISHED
                         and v[2] == caster]
                a7 = any(op == OP_A7 and len(v) > 1 and v[1] == caster for _t, op, v in bb)
                fx20 = [(v[2], v[4]) for _t, op, v in bb
                        if op == OP_INT_TARGET and v[1] == PROP_EFFECT_ON_TARGET and v[3] == caster]
                ent = {"off": round(off, 3), "k": k, "t": gr["t"], "words": gr["words"],
                       "own58": own58, "a7": a7, "fx20": fx20,
                       "a1": [(v[4], v[3]) for _t, op, v in bb if op == OP_POINT_EFFECT],
                       "skill_damage_10": [(v[2], v[3]) for _t, op, v in bb
                                           if op == OP_INT and v[1] == PROP_SKILL_DAMAGE],
                       "cf": [tuple(v[1:]) for _t, op, v in bb if op == OP_ADRENALINE],
                       "order": [(op, v) for _t, op, v in bb]}
                if 1 <= k <= KMAX and abs(off - k) <= TICK_TOL:
                    ent["clean"] = not a7 and not fx20 and not own58
                    ticks.append(ent)
                else:
                    other.append(ent)
            row["ticks"], row["other_words"] = ticks, other
            row["caster_deaths"] = [(round(t - tc, 3), d) for t, d in deaths.get(caster, ())
                                    if -2 <= t - tc <= WINDOW]
            first_lead = next((t for t, _p, op in moves.get(caster, ())
                               if t > tc and op == OP_LEAD), None)
            row["caster_first_lead_after"] = None if first_lead is None else round(first_lead - tc, 3)
            row["_deaths"] = deaths
            row["_creates"] = creates
            rows.append(row)
    _split_mixed(rows, skill)
    for r in rows:
        d = r.pop("_deaths", {})
        c = r.pop("_creates", {})
        takers = {w[0] for x in r.get("ticks", ()) for w in x["fs_words"]}
        r["taker_creates"] = {tg: c.get(tg) for tg in sorted(takers)}
        r["taker_deaths"] = {tg: [(round(t - r["completion_t"], 3), dd) for t, dd in d.get(tg, ())
                                  if 0 <= t - r["completion_t"] <= WINDOW]
                             for tg in sorted(takers)
                             if any(0 <= t - r["completion_t"] <= WINDOW for t, _dd in d.get(tg, ()))}
        # a REVIVAL is a dead -> alive transition (the first 0x00F1 an agent gets is
        # recorded whatever it says, so an alive first word is not a revival)
        rev = {}
        for tg in sorted(takers):
            tr = d.get(tg, ())
            rev[tg] = [round(tr[n][0] - r["completion_t"], 3) for n in range(1, len(tr))
                       if tr[n - 1][1] and not tr[n][1]
                       and 0 <= tr[n][0] - r["completion_t"] <= WINDOW]
        r["taker_revivals"] = {tg: v for tg, v in rev.items() if v}
        r["revived_struck"] = sorted(
            tg for tg, v in r["taker_revivals"].items()
            if any(w[0] == tg and x["off"] > v[0] for x in r["ticks"] for w in x["fs_words"]))
        r["struck_while_dead"] = sum(
            1 for x in r.get("ticks", ()) for w in x["fs_words"]
            if _dead_at(d.get(w[0], ()), x["t"]))
    return rows


def _dead_at(transitions, t):
    """The agent's dead flag just before `t` from its 0x00F1 transitions."""
    dead = False
    for tt, dd in transitions:
        if tt < t - BATCH:
            dead = dd
    return dead


def _split_mixed(rows, skill):
    """Keep, in a MIXED tick batch, only the words whose value is that pair's
    clean-tick value, once; a batch left with none is not a tick."""
    ref = collections.defaultdict(set)
    for r in rows:
        for x in r.get("ticks", ()):
            if x["clean"]:
                for tg, _p, val in x["words"]:
                    ref[(r["caster"], tg)].add(val)
    for r in rows:
        if r.get("completion_t") is None:
            continue
        kept = []
        for x in r["ticks"]:
            if x["clean"]:
                x["fs_words"], x["non_fs_words"] = list(x["words"]), []
            else:
                cnt = collections.Counter((tg, val) for tg, _p, val in x["words"])
                fs, non = [], []
                for tg, pp, val in x["words"]:
                    if val in ref.get((r["caster"], tg), ()) and cnt[(tg, val)] == 1:
                        fs.append((tg, pp, val))
                    else:
                        non.append((tg, pp, val))
                x["fs_words"], x["non_fs_words"] = fs, non
            if x["fs_words"]:
                kept.append(x)
            else:
                r["other_words"].append(x)
        r["ticks"] = kept
        r["tick_ks"] = [x["k"] for x in kept]
        r["phase"] = [round(x["off"] - x["k"], 3) for x in kept]
        r["mixed_ticks"] = [x["k"] for x in kept if not x["clean"]]
        r["targets_per_tick"] = [len({w[0] for w in x["fs_words"]}) for x in kept]
        r["tick_58_of_skill"] = [x["k"] for x in kept if any(s == skill for _o, s in x["own58"])]
        # a tick value landing OUTSIDE the gate: a word by the caster, not in a tick,
        # whose value is that pair's tick value (the arm that lets P5's phase fail)
        # Only a CLEAN group can be a drifted tick: one carrying an 0x00A7 (an attack's
        # landing), a [20] or the caster's 58 is another action's word. (First run,
        # 2026-09-26: without that the arm counted a wand hit -- 0x00A4 launch, 0x00A7,
        # [16, 9, 14, -0.0306] at +10.653 on 54071 -- whose ~17 health equals the pair's
        # tick value.)
        stray = []
        for x in r["other_words"]:
            if x["a7"] or x["fx20"] or x["own58"]:
                continue
            for tg, _p, val in x["words"]:
                if val in ref.get((r["caster"], tg), ()):
                    stray.append((x["off"], tg, val))
        r["stray_tick_values"] = stray
        # and a tick AT the completion (k = 0) would be a word there with a tick value
        r["completion_tick_values"] = [(tg, val) for tg, val in r["completion_words"]
                                       if val in ref.get((r["caster"], tg), ())]


def unattributed(seq, rows, ground=GROUND):
    """Every 0x00A1 `ground` in the connection outside every area (point + life)."""
    areas = [(r["completion_t"], r["point"]) for r in rows if r.get("point")]
    out = []
    for _i, t, op, v in seq:
        if op == OP_POINT_EFFECT and len(v) > 4 and v[4] == ground:
            p = _xy(v[1])
            if not any(tc - BATCH <= t <= tc + AREA_LIFE and p and math.dist(p, P) <= POINT_EPS
                       for tc, P in areas):
                out.append((round(t, 3), p, list(v[2:])))
    return out


def sweep(seq, t16):
    """{(skill, form): n} for every announce / own activation of a target-16 skill."""
    hits = collections.Counter()
    for _i, _t, op, v in seq:
        sk = form = None
        if op == OP_INT_TARGET and len(v) > 4 and v[1] in ANNOUNCE_PROPS:
            sk, form = v[4], f"0x00A0[{v[1]}]"
        elif op == OP_INT and len(v) > 3 and v[1] in ANNOUNCE_PROPS:
            sk, form = v[3], f"0x009F[{v[1]}]"
        elif op in OWN_OPS and len(v) > 2:
            sk, form = v[2], f"0x{op:04X}"
        if sk is not None and sk in t16:
            hits[(int(sk), form)] += 1
    return hits


def census(stamps=None, codec=None):
    """Every live capture (or those named), every game connection that frames whole."""
    codec = codec or bufflog.Codec()
    root = vaultpath.require_dir("captures", "live", why="aotjoin reads live captures")
    aot, ahex, other = classify(skills_table())
    t16 = set(aot) | set(ahex) | set(other)
    out = {"casts": [], "unattributed": [], "refused": [], "connections": 0, "captures": 0,
           "sweep": collections.Counter(), "sweep_where": collections.defaultdict(set),
           "aot": sorted(aot), "ahex": sorted(ahex), "other": sorted(other),
           "stamps": stamps}
    for capdir, _who in livewire.live_captures(root):
        stamp = os.path.basename(capdir)
        if stamps and stamp not in stamps:
            continue
        out["captures"] += 1
        for ch in tape.channel_files(capdir):
            try:
                seq = deepwoundjoin.sequence(capdir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError) as exc:
                out["refused"].append((stamp, ch["connection"], str(exc)[:100]))
                continue
            out["connections"] += 1
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            rows = rows_of(seq)
            observer = None
            if rows:
                c2s = spellhitjoin.c2s_of(capdir, ch["file"])
                observer, _press, _why = spellhitjoin.observer_of(seq, c2s)
            for r in rows:
                r.update(capture=stamp, port=port, observer=observer)
            out["casts"].extend(rows)
            for u in unattributed(seq, rows):
                out["unattributed"].append((stamp, port) + u)
            for k, n in sweep(seq, t16).items():
                out["sweep"][k] += n
                out["sweep_where"][k].add(f"{stamp}/{port}")
    return out


def _observer_prefix(x, obs, skill):
    """For a tick striking the observer: 0x00CF [obs, ...] then [10, obs, skill]
    then the word, in wire order (the tick's own batch)."""
    order = x["order"]
    i_cf = next((n for n, (op, v) in enumerate(order)
                 if op == OP_ADRENALINE and len(v) > 1 and v[1] == obs), None)
    i_10 = next((n for n, (op, v) in enumerate(order)
                 if op == OP_INT and v[1] == PROP_SKILL_DAMAGE and v[2] == obs
                 and v[3] == skill), None)
    i_w = next((n for n, (op, v) in enumerate(order)
                if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE and v[2] == obs), None)
    cf_n = order[i_cf][1][2] if i_cf is not None and len(order[i_cf][1]) > 2 else None
    ok = None not in (i_cf, i_10, i_w) and i_cf < i_10 < i_w
    return ok, cf_n


def _visual_before_words(x, P):
    """For a tick batch carrying the re-sent 350 at P: is it before the tick's first word?"""
    order = x["order"]
    i_a1 = next((n for n, (op, v) in enumerate(order)
                 if op == OP_POINT_EFFECT and v[4] == GROUND and _xy(v[1])
                 and math.dist(_xy(v[1]), P) <= POINT_EPS), None)
    if i_a1 is None:
        return None
    i_w = next((n for n, (op, v) in enumerate(order)
                if op == OP_FLOAT_TARGET and v[1] in PROP_DAMAGE), None)
    return i_w is None or i_a1 < i_w


def score(c):
    """The numbers P1-P9 are judged on."""
    casts = c["casts"]
    done = [r for r in casts if r.get("completion_t") is not None]
    ticks = [(r, x) for r in done for x in r["ticks"]]
    # P1, per tape
    wit = [r for r in casts if r["capture"] == EXPECT_CAPTURE]
    per_port = dict(collections.Counter(r["port"] for r in wit))
    per_capture = dict(collections.Counter(r["capture"] for r in casts))
    p1 = (per_port == EXPECT_PER_PORT
          and all(r["announce_form"] == "0x00A0" for r in wit)
          and not any(r["caster"] == r["observer"] for r in wit))
    # P2
    dts = [r["completion_dt"] for r in done]
    p2 = (bool(casts) and len(done) == len(casts)
          and all(abs(dt - ACTIVATION) <= COMPLETION_TOL for dt in dts)
          and all(r["batch_58s"] == [r["caster"]] for r in done))
    # P3
    after58 = sum(1 for r in done if r["a1_right_after_58"])
    one350 = sum(1 for r in done if r["completion_350s"] == 1)
    fields_ok = all(f == [0, 0, GROUND, 0, 0] for r in done for f in r["completion_350_fields"])
    p3 = bool(done) and after58 == len(done) and one350 == len(done) and fields_ok
    # P4
    def on_schedule(off):
        return any(abs(off - s) <= VISUAL_TOL for s in VISUAL_AT)
    per_cast_350 = collections.Counter(len(r["visual_offsets"]) for r in done)
    off_schedule = [(r["capture"], r["port"], r["announce_t"], o) for r in done
                    for o in r["visual_offsets"] if not on_schedule(o)]
    p4 = (bool(done) and not off_schedule
          and all(sorted(min(VISUAL_AT, key=lambda s: abs(s - o)) for o in r["visual_offsets"])
                  == list(VISUAL_AT) for r in done))
    # P5
    ks = collections.Counter(x["k"] for _r, x in ticks)
    phases = [x["off"] - x["k"] for _r, x in ticks]
    completion_words = sum(len(r["completion_words"]) for r in done)
    at_completion = [(r["capture"], r["port"], r["announce_t"]) + w for r in done
                     for w in r["completion_tick_values"]]
    stray = [(r["capture"], r["port"], r["announce_t"]) + s for r in done
             for s in r["stray_tick_values"]]
    p5 = (bool(ticks) and set(ks) <= set(EXPECT_TICKS_K)
          and all(abs(p) <= PHASE_LIMIT for p in phases) and not stray
          and not at_completion)
    # P6
    fs58 = sum(len(r["tick_58_of_skill"]) for r in done)
    vis_ticks = [x for _r, x in ticks if x["fx20"] or x["a7"]]
    unexplained = [x for x in vis_ticks
                   if not any(s is not None and s != FIRE_STORM for _o, s in x["own58"])]
    p6 = bool(ticks) and fs58 == 0 and not unexplained
    # P7
    n350 = sum(len(r["visual_offsets"]) for r in done)
    p7 = n350 > 0 and not c["unattributed"]
    # P8
    other_aot = {k: n for k, n in c["sweep"].items() if k[0] in c["aot"] and k[0] != FIRE_STORM}
    ahex = {k: n for k, n in c["sweep"].items() if k[0] in c["ahex"]}
    fs_seen = sum(n for k, n in c["sweep"].items() if k[0] == FIRE_STORM)
    p8 = fs_seen > 0 and not other_aot and not ahex and len(c["aot"]) >= 14
    # P9
    takers = {}
    for r in done:
        for tg, cr in r["taker_creates"].items():
            takers[(r["capture"], r["port"], tg)] = cr
    no_create = [k for k, cr in takers.items() if cr is None]
    monsters = [k for k, cr in takers.items() if cr is not None and cr[1] in MONSTER_TOKENS]
    token_census = dict(collections.Counter(_token(cr[1]) if cr else None
                                            for cr in takers.values()))
    p9 = bool(takers) and not no_create and not monsters
    # also reported
    obs_hits = [(r, x) for r, x in ticks if r["observer"] is not None
                and any(w[0] == r["observer"] for w in x["fs_words"])]
    prefix = [_observer_prefix(x, r["observer"], FIRE_STORM) for r, x in obs_hits]
    vis_in_tick = [_visual_before_words(x, r["point"]) for r, x in ticks]
    vis_in_tick = [v for v in vis_in_tick if v is not None]
    const, varied = 0, []
    for r in done:
        vals = collections.defaultdict(set)
        for x in r["ticks"]:
            for tg, _p, val in x["fs_words"]:
                vals[tg].add(val)
        for tg, vs in vals.items():
            if len(vs) == 1:
                const += 1
            else:
                varied.append((r["port"], r["announce_t"], tg, sorted(vs)))
    return {
        "captures": c["captures"], "connections": c["connections"],
        "refused": len(c["refused"]),
        "aot": c["aot"], "ahex": c["ahex"], "other": c["other"],
        "casts": len(casts), "completed": len(done),
        "per_capture": per_capture, "witness_per_port": per_port,
        "announce_forms": dict(collections.Counter(r["announce_form"] for r in casts)),
        "by_observer": sum(1 for r in casts if r["caster"] == r["observer"]),
        "p1": p1,
        "completion_dt": (min(dts), max(dts)) if dts else None,
        "single_58": sum(1 for r in done if r["batch_58s"] == [r["caster"]]),
        "p2": p2,
        "a1_right_after_58": after58, "one_350_in_batch": one350, "fields_ok": fields_ok,
        "p3": p3,
        "per_cast_350": dict(per_cast_350), "n350": n350,
        "visual_offsets": sorted(o for r in done for o in r["visual_offsets"]),
        "off_schedule_350": off_schedule,
        "p4": p4,
        "tick_instants": len(ticks), "k_hist": dict(sorted(ks.items())),
        "phase": (round(min(phases), 3), round(max(phases), 3)) if phases else None,
        "completion_words": completion_words, "stray_tick_values": stray,
        "tick_at_completion": at_completion,
        "p5": p5,
        "mixed_ticks": sum(len(r["mixed_ticks"]) for r in done),
        "fs58_on_tick": fs58, "ticks_with_20_or_a7": len(vis_ticks),
        "unexplained_20_or_a7": len(unexplained),
        "clean_ticks": sum(1 for _r, x in ticks if x["clean"]),
        "p6": p6,
        "unattributed": len(c["unattributed"]),
        "p7": p7,
        "sweep": {f"{k[0]} {k[1]}": n for k, n in sorted(c["sweep"].items())},
        "other_aot": {f"{k[0]} {k[1]}": n for k, n in other_aot.items()},
        "ahex_seen": {f"{k[0]} {k[1]}": n for k, n in ahex.items()},
        "fs_seen": fs_seen,
        "p8": p8,
        "takers": len(takers), "takers_no_create": len(no_create),
        "monster_takers": len(monsters), "taker_tokens": token_census,
        "p9": p9,
        "targets_per_tick": dict(sorted(collections.Counter(
            n for r in done for n in r["targets_per_tick"]).items())),
        "own55": sum(1 for r in done if r["batch_55"]),
        "own55_before_58": sum(1 for r in done if r["own55_right_before_58"]),
        "own55_values": dict(collections.Counter(v for r in done for _a, _b, v in r["batch_55"])),
        "observer_hit_ticks": len(obs_hits),
        "observer_prefix_ok": sum(1 for ok, _n in prefix if ok),
        "observer_prefix_cf": dict(collections.Counter(n for _ok, n in prefix)),
        "visual_in_tick": len(vis_in_tick),
        "visual_before_words": sum(1 for v in vis_in_tick if v),
        "pairs_constant": const, "pairs_varied": varied,
        "struck_while_dead": sum(r["struck_while_dead"] for r in done),
        "revived_struck": [(r["port"], r["announce_t"], tg, r["taker_revivals"][tg])
                           for r in done for tg in r["revived_struck"]],
        "ticks_after_caster_walks": sum(
            1 for r in done if r["caster_first_lead_after"] is not None
            and any(x["off"] > r["caster_first_lead_after"] for x in r["ticks"])),
        "caster_deaths": [(r["port"], r["announce_t"], r["caster_deaths"], r["tick_ks"],
                           [o for o in r["visual_offsets"]
                            if any(dd and o > t for t, dd in r["caster_deaths"])])
                          for r in done if any(dd for _t, dd in r["caster_deaths"])],
    }


def _say(text):
    """print(), but a console that cannot encode a character never kills the run
    (checks._say's rule: a decoded string field can carry any character)."""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        print(text.encode(enc, "backslashreplace").decode(enc, "replace"))


def _verdict(ok):
    return "PASS" if ok else "FAIL"


def print_cast(n, r):
    print(f"\n#{n} {r['capture']} {r['port']} observer={r['observer']} caster={r['caster']} "
          f"-> target={r['target']} announce t={r['announce_t']:.3f} ({r['announce_form']}) "
          f"completion +{r['completion_dt']} stopped={r['stopped']}")
    if r.get("completion_t") is None:
        return
    P = r["point"]
    print(f"   point={tuple(round(c, 1) for c in P) if P else None} 350 at "
          f"{r['visual_offsets']} batch58s={r['batch_58s']} [55]={r['batch_55']} "
          f"target's last sample {r['target_last_sample']} ({r['target_sample_dist']} u off)")
    print(f"   ticks k={r['tick_ks']} foes/tick={r['targets_per_tick']} phase={r['phase']} "
          f"mixed={r['mixed_ticks']} caster walks from +{r['caster_first_lead_after']} "
          f"deaths={r['caster_deaths']} taker deaths={r['taker_deaths']}")
    for x in r["ticks"]:
        print(f"     +{x['off']:.3f} k={x['k']} {'clean' if x['clean'] else 'MIXED'} "
              f"words={x['fs_words']} other={x['non_fs_words']} own58={x['own58']} "
              f"[20]={x['fx20']} a1={x['a1']} [10]={x['skill_damage_10']} cf={x['cf']}")
    print("   completion batch, wire order:")
    for off, s in r["batch"]:
        _say(f"       {off:+.3f} {s}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true", help="one block per cast")
    ap.add_argument("--stamp", action="append", default=None,
                    help="only this capture (repeatable)")
    a = ap.parse_args()
    c = census(stamps=a.stamp)
    s = score(c)
    if a.json:
        for r in c["casts"]:
            for x in r.get("ticks", ()) + r.get("other_words", []):
                x.pop("order", None)
        print(json.dumps({"score": s, "casts": c["casts"], "unattributed": c["unattributed"],
                          "refused": c["refused"]}, indent=1, default=str))
        return 0
    print(f"aotjoin: {s['captures']} live captures, {s['connections']} connections framed "
          f"whole, {s['refused']} refused")
    for r in c["refused"]:
        print(f"   refused {r}")
    print(f"   the record's target-16 rows: {len(s['aot'])} areas over time {s['aot']}; "
          f"{len(s['ahex'])} area hexes {s['ahex']}; {len(s['other'])} other")
    if a.rows:
        for n, r in enumerate(c["casts"], 1):
            print_cast(n, r)
        print()
    print(f"[{_verdict(s['p1'])}] P1 Fire Storm announces on {EXPECT_CAPTURE} per port "
          f"{s['witness_per_port']} (predicted {EXPECT_PER_PORT}); forms {s['announce_forms']}; "
          f"by the observer {s['by_observer']}; corpus per capture {s['per_capture']}")
    print(f"[{_verdict(s['p2'])}] P2 one caster 58 at +{ACTIVATION} +- {COMPLETION_TOL} s: "
          f"completed {s['completed']}/{s['casts']}, dt {s['completion_dt']}, a single 58 "
          f"(the caster's) in the batch {s['single_58']}/{s['completed']}")
    print(f"[{_verdict(s['p3'])}] P3 the 350 immediately after the 58: {s['a1_right_after_58']}/"
          f"{s['completed']}; exactly one 350 in the batch {s['one_350_in_batch']}/"
          f"{s['completed']}; fields [0, 0, 350, 0, 0] {s['fields_ok']}")
    print(f"[{_verdict(s['p4'])}] P4 the 350 at +0/+3/+6 only: per cast {s['per_cast_350']} "
          f"({s['n350']} total); off schedule {s['off_schedule_350']}; offsets "
          f"{s['visual_offsets'][0] if s['visual_offsets'] else None}.."
          f"{s['visual_offsets'][-1] if s['visual_offsets'] else None}")
    print(f"[{_verdict(s['p5'])}] P5 ticks at k=1..10 only, |phase| <= {PHASE_LIMIT}: "
          f"{s['tick_instants']} instants, k {s['k_hist']}, phase {s['phase']}; tick values "
          f"outside the gate {s['stray_tick_values']}; a tick value at the completion "
          f"{s['tick_at_completion']} (caster words in the completion batch "
          f"{s['completion_words']}, none a tick value)")
    print(f"[{_verdict(s['p6'])}] P6 no Fire Storm 58 on a tick ({s['fs58_on_tick']}); ticks "
          f"carrying a [20]/0x00A7 {s['ticks_with_20_or_a7']}, not explained by another "
          f"skill's 58 {s['unexplained_20_or_a7']}; clean {s['clean_ticks']}, mixed "
          f"{s['mixed_ticks']}")
    print(f"[{_verdict(s['p7'])}] P7 unattributed 350s: {s['unattributed']} of "
          f"{s['n350'] + s['unattributed']}")
    for u in c["unattributed"][:20]:
        print(f"   unattributed {u}")
    print(f"[{_verdict(s['p8'])}] P8 other areas over time {s['other_aot']}, area hexes "
          f"{s['ahex_seen']} (both predicted empty); Fire Storm {s['fs_seen']}; every "
          f"target-16 hit {s['sweep']}")
    print(f"[{_verdict(s['p9'])}] P9 monster takers {s['monster_takers']} of {s['takers']} "
          f"struck agents (no create {s['takers_no_create']}); taker tokens {s['taker_tokens']}")
    print(f"   also: foes per tick {s['targets_per_tick']}; [55] self gain before the 58 on "
          f"{s['own55_before_58']}/{s['completed']} ({s['own55_values']}) -- a heal, not energy; "
          f"observer-hit ticks {s['observer_hit_ticks']}, 0x00CF -> [10, obs, 197] -> word in "
          f"order {s['observer_prefix_ok']} (0x00CF n {s['observer_prefix_cf']}); a tick batch "
          f"with the re-sent 350 {s['visual_in_tick']}, the 350 before the words "
          f"{s['visual_before_words']}; (cast, taker) pairs one value {s['pairs_constant']}, "
          f"varied {s['pairs_varied']}; struck while dead {s['struck_while_dead']}; revived "
          f"takers struck again {s['revived_struck']}; casts ticking after the caster walks "
          f"{s['ticks_after_caster_walks']}; caster deaths (port, t, death, ks, 350 after) "
          f"{s['caster_deaths']}")
    ok = all(s[f"p{i}"] for i in range(1, 10))
    print(f"aotjoin: {'ALL NINE PREDICTIONS HOLD' if ok else 'A PREDICTION FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
