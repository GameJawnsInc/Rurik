r"""Does a CAST's damage roll a hit location the way a SWING's does? Retail's wire.

    python toolkit/authsrv/spellhitjoin.py            # every live capture
    python toolkit/authsrv/spellhitjoin.py --json
    python toolkit/authsrv/spellhitjoin.py --pairs    # every (caster, skill, target)

WHY THIS EXISTS. `studies/skills/FINDINGS.md` 39.6 left the incoming-Flare
armour term unbuilt because GWW is ambiguous about WHICH armour a spell
scales against: every hit-location sentence it has says "attack" (chest 3/8,
legs 2/8, feet/hands/head 1/8), and the non-attack formula names no
location. It proposed a loopback probe with a lopsided armour set -- which
cannot answer the question, because on loopback OUR server computes the
number (two of our own components agreeing). The instrument is retail's
own casts: one caster, one skill, one target, many hits. A location roll on
a set whose pieces differ shows as a second value bucket; a single rating
shows as one value for as long as the target's armour holds.

THE JOIN. A cast's damage rides the same `0x00A3` property 16/17 a swing
does, in the batch its caster's property-58 (skill_finished) closes; the
SKILL is named by the cast announcement `0x00A0 [60 SKILL_ACTIVATED, caster,
target, skill]`, and the damage lands one activation later (Mind Burn's
1.0 s, Fireball's 1.5 s -- the `age` column reproduces the wiki's
activation times). A DAMAGE-OVER-TIME tick (Fire Storm, once a second, no
58 of its own) can share a batch with a cast from the same caster; a value
in a 58-batch that also occurs as a NO-58 hit from the same cause onto the
same target within 5 s is a tick and is set aside, not counted as the cast.

THE PREDICTIONS, stated before the numbers:

  P1  cast damage is ANNOUNCED: >= 95% of damage in a 58-batch has a
      property-60 from its cause inside 4 s.
  P2  one caster + one skill + one target is ONE VALUE: over every pair with
      >= 3 non-tick hits, the number of distinct fractions is 1 -- for at
      least 10 pairs and 60 hits. A 1-in-8 head roll on ANY armour
      difference leaves a single bucket with probability (7/8)^n; at n = 60
      that is 0.03%. What P2 cannot separate: a roll on a set whose pieces
      are all equal, which is what a PvP set usually is (43.5).
  P3  the CONTROL, so the instrument is known to see variance where it
      exists: swing damage from one cause onto one target with >= 10 hits
      has >= 3 distinct values (a weapon's range).
  P4  the wiki's own second packet: Mind Burn (185) "if you have more Energy
      than target foe, that foe ... take[s] an additional 15..60" -- read
      as TWO identical 16s onto one target in one batch, >= 10 times.

Standard library only; reads the vault through `vaultpath`; refuses a tape
that does not frame whole (`deepwoundjoin.sequence`).
"""
import argparse
import bisect
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import adrenjoin        # noqa: E402
import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import healjoin         # noqa: E402
import livewire         # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_FLOAT_TARGET = 0x00A3   # [prop, target, cause, f32]
OP_SKILL_ACTIVATED = 0x00E3
PROP_MELEE_FINISHED = 1
PROP_SKILL_FINISHED = 58
PROP_ATTACK_SKILL_ACTIVATED = 50
PROP_SKILL_ACTIVATED = 60
PROP_HEALTH_MAX = 42
PROP_DAMAGE = (16, 17)
ANNOUNCE_WINDOW = 4.0      # s; longer than any activation on the wire
TICK_WINDOW = 5.0          # s; a DoT's cadence is 1 s
MIND_BURN = 185


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def events(seq):
    """Every 16/17 in one sequence, classified.

    A row: {"t", "prop", "target", "cause", "value", "kind" (swing / cast /
    both / none -- what the cause finished in the batch), "skill" (the
    cause's latest property-60 skill, None if none inside ANNOUNCE_WINDOW),
    "age" (seconds since that announcement), "maxhp" (the target's last
    property 42, None if never seen), "tick" (a 58-batch value that also
    occurs as a no-58 hit from the same cause onto the same target within
    TICK_WINDOW), "twin" (another identical 16 onto this target from this
    cause in the same batch)}.
    """
    ann = {}
    maxhp = {}
    rows = []
    for batch in healjoin.batches(seq):
        fin = collections.defaultdict(set)
        for _i, t, op, v in batch:
            if op == OP_INT_TARGET and v[1] == PROP_SKILL_ACTIVATED:
                ann[v[2]] = (v[4], t)
            elif op == OP_INT and v[1] == PROP_HEALTH_MAX:
                maxhp[v[2]] = v[3]
            elif op == OP_INT and v[1] in (PROP_MELEE_FINISHED,
                                           PROP_SKILL_FINISHED):
                fin[v[2]].add(v[1])
        seen = collections.Counter()
        for _i, t, op, v in batch:
            if op != OP_FLOAT_TARGET or v[1] not in PROP_DAMAGE:
                continue
            prop, target, cause, value = v[1], v[2], v[3], round(_f32(v[4]), 5)
            kinds = fin.get(cause, set())
            kind = {frozenset(): "none",
                    frozenset({PROP_MELEE_FINISHED}): "swing",
                    frozenset({PROP_SKILL_FINISHED}): "cast"}.get(
                        frozenset(kinds), "both")
            skill, age = None, None
            a = ann.get(cause)
            if a is not None and 0.0 <= t - a[1] <= ANNOUNCE_WINDOW:
                skill, age = a[0], round(t - a[1], 3)
            key = (target, cause, value)
            seen[key] += 1
            rows.append({"t": round(t, 6), "prop": prop, "target": target,
                         "cause": cause, "value": value, "kind": kind,
                         "skill": skill, "age": age,
                         "maxhp": maxhp.get(target), "tick": False,
                         "twin": seen[key] > 1})
    # Ticks: a 58-batch value also seen as a no-58 hit nearby.
    bare = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "none":
            bare[(r["target"], r["cause"], r["value"])].append(r["t"])
    for r in rows:
        if r["kind"] == "cast":
            near = bare.get((r["target"], r["cause"], r["value"]), ())
            r["tick"] = any(abs(t - r["t"]) <= TICK_WINDOW for t in near)
    return rows


# WHOSE CONNECTION IT IS (2026-09-23). This used to be "the agent of the FIRST
# 0x00E3", and on the one tape with a hero (20260914T005758, conn 56011) that
# ack is the HERO's: agent 30 (a kind-9 create) holds 48 of the 54 -- 346, 322,
# 382, 348, 385, one 2 -- and the player, agent 29 (the kind-5 create, whose acks
# answer all 18 c2s presses: 392, 394, 433, 446, 455), holds 6. On 69 more connections the
# player never cast, so there was no 0x00E3 and the old rule named NOBODY while
# property 41 named the observer. Every consumer's "own" split was scored on that
# (studies/skills 43.8). The observer is now `adrenjoin.whose_agent` -- property
# 41, self-scoped, with the JARIN kind-5 tie-break -- cross-checked against the
# agent whose 0x00E3 / 0x00E2 answers the connection's own c2s presses; the two
# disagreeing is REFUSED (no player named), never settled by picking one.
# `shoutjoin.observer_of` (branch desk-d5c) is the same rule on a merged stream.
OP_SKILL_RELEASED = 0x00E2
OP_CMSG_PRESS = (0x0027, 0x0046)   # c2s: attack-skill and cast presses
PRESS_ANSWER_S = 0.3       # s; the observer's E3 / E2 answering its own press


def c2s_of(cap_dir, conn_file):
    """[(t, opcode)] of the client's own requests, on the capture clock, or []."""
    _conn, events, err = livewire.build_events(cap_dir, conn_file, "c2s")
    if err is not None or not events:
        return []
    msgs, _receipt = tape.decode_all(events, livewire._get_codec(),
                                     channel="GAME_CMSG", mask=livewire.CMSG_MASK,
                                     strict=False)
    return [(t, op) for t, op, _v in msgs]


def observer_of(seq, c2s=()):
    """(player, press_agent, why): the connection's own agent by two rules.

    Property 41 (`adrenjoin.whose_agent`, NO fallback) and the landslide vote of
    the agent whose `0x00E3` / `0x00E2` is the next answer inside PRESS_ANSWER_S
    after each c2s press in `c2s` ([(t, opcode)] on `seq`'s clock, `c2s_of`).
    Both, when both answer, must agree; `why` is None when a player is named and
    says which case it is when not ("no observer: ..." -- neither rule answers;
    "observer rules disagree: ..." -- the REFUSAL). A press answered later than
    the window casts no vote (a walk into range first); it does not refute.
    """
    s2c = [(t, op, v) for _i, t, op, v in seq]
    by_41 = adrenjoin.whose_agent(s2c)
    answers = [(t, int(v[1])) for t, op, v in s2c
               if op in (OP_SKILL_ACTIVATED, OP_SKILL_RELEASED) and len(v) > 1]
    times = [t for t, _a in answers]
    votes = collections.Counter()
    for t, op in c2s:
        if op not in OP_CMSG_PRESS:
            continue
        i = bisect.bisect_left(times, t)
        if i < len(answers) and answers[i][0] - t <= PRESS_ANSWER_S:
            votes[answers[i][1]] += 1
    by_press = votes.most_common(1)[0][0] if votes else None
    if by_41 is None and by_press is None:
        return None, None, "no observer: no property 41 and no answered press"
    if by_41 is not None and by_press is not None and by_41 != by_press:
        return None, by_press, (f"observer rules disagree: property 41 says {by_41}, "
                                f"the answered presses say {by_press} ({dict(votes)})")
    return (by_41 if by_41 is not None else by_press), by_press, None


def player_of(seq, c2s=()):
    """The connection's own agent, or None when `observer_of` names nobody."""
    return observer_of(seq, c2s)[0]


def census(codec=None, unnamed=None):
    """Every live capture, every game connection that frames whole. A
    connection whose player `observer_of` cannot name keeps its rows (player
    None) and, when `unnamed` is a list, is appended to it as (capture,
    connection, why)."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="spellhitjoin reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            player, _press, why = observer_of(seq, c2s_of(cap_dir, ch["file"]))
            if player is None and unnamed is not None:
                unnamed.append((stamp, ch["connection"], why))
            for row in events(seq):
                row.update(capture=stamp, connection=ch["connection"],
                           player=player)
                out.append(row)
    return out


def pairs(rows, kind="cast", min_hits=3):
    """{(capture, connection, cause, skill, target): [values]} for one kind,
    ticks set aside, pairs under `min_hits` dropped."""
    g = collections.defaultdict(list)
    for r in rows:
        if r["kind"] != kind or r["tick"]:
            continue
        g[(r["capture"], r["connection"], r["cause"], r["skill"],
           r["target"])].append(r["value"])
    return {k: v for k, v in g.items() if len(v) >= min_hits}


AGE_BAND = 0.25            # s; a projectile's flight is steady per (caster, skill)
INTEGER_EPS = 0.06         # points; the word is whole points of SOME maximum


def location_buckets(rows, min_hits=5):
    """PROJECTILE spell hits (no 58 in the batch -- the cast closed before the
    orb landed), per (capture, connection, cause, skill, target), as a Counter
    of WHOLE POINTS. SKILLS-LR (RUN-SKILLS-RB2, 2026-09-17): this is where a
    location roll shows, as two buckets 2^(dAR/40) apart.

    Two filters, both measured on the RB2 tape. AGE: the caster's wand hits
    share the announcement window, and a projectile's flight time is steady
    (Lightning Orb 2.38-2.50 s, Javelin 1.57-1.77 s), so rows more than
    AGE_BAND off the group's median age are another source. MAXIMUM: a killing
    blow's batch carries the death penalty's new prop 42 AHEAD of the damage
    word, so `maxhp` is one death stale there; the word is whole points of
    SOME maximum this target held (F46), and the first that makes it whole
    is taken, the current one tried first."""
    g = collections.defaultdict(list)
    for r in rows:
        if r["kind"] == "none" and r["skill"] is not None \
                and r["age"] is not None and r["maxhp"] is not None:
            g[(r["capture"], r["connection"], r["cause"], r["skill"],
               r["target"])].append(r)
    held = collections.defaultdict(set)      # every maximum a target held
    for r in rows:
        if r["maxhp"] is not None:
            held[(r["capture"], r["connection"], r["target"])].add(r["maxhp"])
    out = {}
    for k, rs in g.items():
        ages = sorted(r["age"] for r in rs)
        med = ages[len(ages) // 2]
        maxima = sorted(held[(k[0], k[1], k[4])], reverse=True)
        pts = collections.Counter()
        for r in rs:
            if abs(r["age"] - med) > AGE_BAND:
                continue
            for m in [r["maxhp"]] + [x for x in maxima if x != r["maxhp"]]:
                p = -r["value"] * m
                if abs(p - round(p)) <= INTEGER_EPS:
                    pts[int(round(p))] += 1
                    break
        if sum(pts.values()) >= min_hits:
            out[k] = dict(sorted(pts.items()))
    return out


def score(rows):
    """The numbers P1-P4 are judged on."""
    cast = [r for r in rows if r["kind"] == "cast"]
    announced = [r for r in cast if r["skill"] is not None]
    cp = pairs(rows, "cast", 3)
    named = {k: v for k, v in cp.items() if k[3] is not None}
    multi = {k: sorted(set(v)) for k, v in named.items() if len(set(v)) > 1}
    # A multi-valued pair whose fraction moved WITH its target's maximum --
    # one value per maximum, several across them -- is a DEATH-PENALTY SPLIT,
    # not a second bucket: the word is points / max and a penalty moves the
    # max (studies/slice F46). Named by signature (SLICE-F47 2026-09-16)
    # so the next hero tape does not redden P2 on confirming evidence. A pair
    # with a hit whose maximum was never seen does not qualify.
    by_max = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in rows:
        if r["kind"] == "cast" and not r["tick"] and r["skill"] is not None:
            by_max[(r["capture"], r["connection"], r["cause"], r["skill"],
                    r["target"])][r["maxhp"]].add(r["value"])
    penalty_split = {k: {m: sorted(vs) for m, vs in by_max[k].items()}
                     for k in multi
                     if len(by_max[k]) > 1 and None not in by_max[k]
                     and all(len(vs) == 1 for vs in by_max[k].values())}
    # Two hits, two values: below P2's floor, and named rather than dropped.
    # The corpus's one such pair is a MIXED batch -- Fireball's projectile
    # and Incendiary Bonds' hex-end payoff from the same caster landing on
    # one target 43 ms apart (studies/skills 43.5) -- not a second bucket.
    two = {k: sorted(set(v)) for k, v in pairs(rows, "cast", 2).items()
           if len(v) == 2 and len(set(v)) == 2 and k[3] is not None}
    sp = pairs(rows, "swing", 10)
    swing_distinct = {k: len(set(v)) for k, v in sp.items()}
    twins = [r for r in cast if r["twin"] and r["skill"] == MIND_BURN
             and not r["tick"]]
    onto_player = {k: v for k, v in named.items()
                   if any(r["target"] == r["player"] and r["capture"] == k[0]
                          and r["connection"] == k[1] and r["cause"] == k[2]
                          for r in rows if r["kind"] == "cast")
                   and k[4] == next((r["player"] for r in rows
                                     if r["capture"] == k[0]
                                     and r["connection"] == k[1]), None)}
    return {
        "n_cast": len(cast),
        "announced": len(announced),
        "ticks_set_aside": sum(1 for r in cast if r["tick"]),
        "pairs": len(named),
        "pair_hits": sum(len(v) for v in named.values()),
        "multi_valued": {" ".join(map(str, k[2:])): v for k, v in multi.items()},
        "penalty_split": {" ".join(map(str, k[2:])): v
                          for k, v in penalty_split.items()},
        "two_hit_two_valued": {" ".join(map(str, k[2:])): v
                               for k, v in two.items()},
        "skills": sorted({k[3] for k in named}),
        "swing_pairs": len(sp),
        "swing_pairs_3plus": sum(1 for n in swing_distinct.values() if n >= 3),
        "swing_min_distinct": min(swing_distinct.values()) if sp else None,
        "mind_burn_twins": len(twins),
        "onto_player": {" ".join(map(str, k[2:])): (len(v), sorted(set(v)))
                        for k, v in onto_player.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pairs", action="store_true",
                    help="print every (caster, skill, target) pair's values")
    args = ap.parse_args()
    unnamed = []
    rows = census(unnamed=unnamed)
    sc = score(rows)
    if args.json:
        print(json.dumps({"score": sc, "rows": rows, "unnamed": unnamed}, indent=1))
        return
    refused = [u for u in unnamed if u[2].startswith("observer rules disagree")]
    print(f"connections whose player is named by nobody: {len(unnamed) - len(refused)}; "
          f"REFUSED (property 41 and the answered presses disagree): {len(refused)}")
    for stamp, conn, why in refused:
        print(f"   {stamp} {conn}: {why}")
    print(f"cast damage events {sc['n_cast']}: announced by a property-60 "
          f"inside {ANNOUNCE_WINDOW:.0f} s {sc['announced']} (P1); DoT ticks "
          f"set aside {sc['ticks_set_aside']}")
    print(f"P2 (caster, skill, target) pairs with >= 3 hits: {sc['pairs']} "
          f"over {sc['pair_hits']} hits, skills {sc['skills']}; "
          f"multi-valued pairs: {len(sc['multi_valued'])} "
          f"{sc['multi_valued'] or ''}; two-hit two-valued pairs (below the "
          f"floor, named): {sc['two_hit_two_valued']}")
    print(f"   of the multi-valued, split by a death penalty (one value per "
          f"maximum): {sc['penalty_split'] or 'none'}")
    print(f"   onto the connection's own player: {sc['onto_player']}")
    print(f"P3 control: swing pairs with >= 10 hits {sc['swing_pairs']}, of "
          f"which >= 3 distinct values {sc['swing_pairs_3plus']} (min "
          f"distinct {sc['swing_min_distinct']})")
    print(f"P4 Mind Burn's second packet as a twin 16 in one batch: "
          f"{sc['mind_burn_twins']}")
    if args.pairs:
        for k, v in sorted(pairs(rows, "cast", 2).items(),
                           key=lambda kv: (kv[0][0], kv[0][1], kv[0][2],
                                           str(kv[0][3]), kv[0][4])):
            c = collections.Counter(v)
            print(f"   {k[0]} {k[1][11:16]} cause {k[2]:3d} skill "
                  f"{str(k[3]):>4s} -> {k[4]:3d} n={len(v):3d} :: "
                  + " ".join(f"{val:.4f}x{n}" for val, n in sorted(c.items())))


if __name__ == "__main__":
    main()
