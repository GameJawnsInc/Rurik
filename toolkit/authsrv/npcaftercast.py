r"""Does a body wait out its spell's AFTERCAST before its next action? Retail's wire, and ours.

    python toolkit/authsrv/npcaftercast.py                     # every live capture
    python toolkit/authsrv/npcaftercast.py --ours <authsrv-*-c1.jsonl>   # + one of OUR captures
    python toolkit/authsrv/npcaftercast.py --json

WHY THIS EXISTS (DESKWORK-D5, "NPC aftercast proper"; studies/skills 65, SKILLS-AC).
`authsrv.py` (642d8957) cleared a body's `casting` at the landing and the very next tick
could cast or swing again: the ENEMY_SKILL_BAR comment said "aftercast is wirable from
the same read and is not wired". The player's aftercast IS modelled (E3 = E5 + the table's
+0x40, castmech 3; OBSERVED on the observer's own E5 -> E3). This asks the question
for EVERY OTHER agent: after a spell's completion, how soon does the same body start
anything else?

THE INSTRUMENT. Per (connection, agent INCARNATION) other than the connection's own
player (`spellhitjoin.observer_of`; split at each `0x0020` create, rechargeprobe's
rule, so a recycled id cannot manufacture a short gap): every completion
`0x009F [58, agent, 0]` whose most recent START was a spell's announcement --
`0x00A0 [60, agent, target, skill]`, or the un-targeted `0x009F [60, agent, skill]`
(CASTAI-R2's shape) -- with no other close between them; the GAP from that [58] to
the same incarnation's NEXT START: `0x00A0` property 60 (a cast), 50 (an attack
skill) or 4 (a swing), or the un-targeted `0x009F [60]` / `[50]`. The completed
skill's AFTERCAST is read off the table on the connection's OWN build (the client's
VERSION frame names it; the vault's exe of that build supplies the row through
`clientscan/skilltable.py`'s +0x40, as `rechargeprobe` reads activation and recharge).
An instant skill's `0x009F [48, agent, skill]` is not a START (it carries no [60]); it
is read separately, as the first [48] between the [58] and the next start.

A body that acts the moment it may shows the aftercast as the group's FLOOR -- the
same reading rechargeprobe makes of a recharge, one level down.

THE PREDICTIONS, stated before the numbers (the triage's survey of 2026-10-07 gave
the expectations; this re-derives them):

  P1  THE FLOOR: for completed spells whose table aftercast is 0.75 s, NO next start
      comes sooner than FLOOR_S (0.70 s: 0.75 less the corpus's 50 ms batch
      shoulder) on the retail corpus. Survey: n = 872, min 0.704, 0 below.
  P2  THE MASS: at least MASS_SHARE (30 %) of those gaps fall in [0.70, 0.80) --
      bodies with something ready act AT the aftercast's end, so a floor that held
      only because the AI is slow would not pile up there. Survey: 355 of 872 (41 %).
  P3  THE CONTROL: the completed spells whose table aftercast is 0 have at least
      CONTROL_SHARE (25 %) of their gaps under 0.70 s -- so the floor is the
      TABLE's and not a general minimum time between a body's actions. Survey: one
      skill (2, Resurrection Signet), 28 of 56. One skill is a weak control; the
      known-bad arm below is the stronger one.
  P4  OURS FAILS: `--ours` on authsrv-20260928T002701-c1 (a recorder capture of OUR
      server before NPC_AFTERCAST: the Hatcher chains 253 -> 289) scores P1 FALSE
      -- min ~0.025 s, inside one 0.05 s tick. A real capture as the known-bad arm,
      not an invented fixture.
  P5  THE HERO'S E3 RIDES ITS E5: for every non-observer agent's `0x00E5 [agent,
      skill, ...]` followed by its `0x00E3 [agent, skill]`, E3 - E5 is 0.000 s --
      a body's E3 is NOT the aftercast's end (the player's is). Survey: 322 11/11,
      346 17/17, 348 7/7 on 20260914T005758 (346 and 348 are instant / attack: only
      a SPELL row with a table aftercast > 0 can tell the two readings apart, and
      the scored set is those). [Corrected 2026-10-07, the registered text left as
      written: 346 is a stance and 348 a shout, both instants; the attack is 322.]

  P6  AN INSTANT IN THE WINDOW (registered in the implementer's notes before the run,
      not in the survey): no instant skill's [48] falls inside a 0.75 aftercast either
      -- the WIKI ("Aftercast delay") says the caster "cannot ... activate other skills".

AS RUN, 2026-10-07 (127 connections on FOUR builds -- 38797 x 12, 38833 x 37, 38849 x 12,
38888 x 66, each scored on its own build's table; the vault holds six exe tables, 38519
and 38974 with no live connection; :65009 set aside by name):
  P1 HOLDS -- n = 1,477, min 0.704, p5 0.741, p10 0.748, median 1.135, 0 below 0.70;
     by the next start: a cast 1,108 (min 0.704), a swing 352 (0.704), an attack skill 17
     (0.735). THE SURVEY'S n = 872 IS REPRODUCED EXACTLY by reading only `0x00A0` starts and
     walking back across closes; the un-targeted `0x009F [60]` is a start too (a self cast,
     CASTAI-R2's and castethogram L1's shape: 417 of 417 self-kind casts ride it), and 127 of
     the survey's 872 rows were a [58] closing such a cast, scored against the targeted cast
     before it. Every one of the four (targeted / un-targeted) x (next) classes floors at
     0.704 or above.
  P2 HOLDS -- 527 of 1,477 = 35.7 % (the survey's 41 % is its 355 of 872).
  P3 HOLDS -- 49 of 95 under 0.70 over FIVE aftercast-0 skills (2; the Ranger preparations
     432 / 433 / 435, activation 2.0, which re-start at 0.000 several times; 769), not the
     survey's one. By skill (under 0.70 / n): the signet 2 32 / 42, 433 15 / 40, 435 2 / 3,
     432 0 / 4, and the one SPELL, 769 (type 5), 0 / 6 with min 1.75 -- so P3 shows the
     floor is not a general pause after every action, and does NOT separate "the column
     decides" from "spells pause" for an aftercast-0 spell (WIKI there, castmech 9).
  P4 HOLDS -- ours FAILS P1: n = 13, min 0.025, 2 below 0.70.
  P5 UNDECIDABLE -- 0 scoreable rows. The survey's 322 / 346 / 348 are an attack (type 14),
     a stance (3) and a shout (15), every one table aftercast 0 on all six tables, so their
     0.000 cannot tell "the E3 rides the E5" from "the E3 waits the aftercast"; no
     non-observer agent completes an aftercast > 0 skill with an E5 / E3 on any tape.
  P6 REFUTED -- of the 7 instants between a 0.75 completion and the next start, 2 sit
     STRICTLY inside the window: 0.499 and 0.501 (stance 11, agent 4, 20260928T103123
     :58544). A third, at 0.000 (:50061), is in the [58]'s own batch, and batch order is
     not evidence -- on the same connection at t = 160.980 the [48] precedes the [58] --
     so it is printed apart ("co-batched") and scores nothing (corrected after review the
     same day; it had been counted, "3 of 7"). n = 2, one stance, one body: OBSERVED and
     CONTESTED with the wiki's wording; shouts and type 16 are not witnessed.

What this cannot separate: an aftercast from the AI's own wait (the floor bounds
both -- which is why P2 and P3 exist); the 0.75 class from any other non-zero value
(the table holds 0.25, 1.0, 1.5 and others on playable rows; none is on tape, printed
not scored); a STOPPED cast's aftercast ([59] and an interrupt are not completions,
and are not read here).

A GAPPED CONNECTION is set aside BY NAME (`deepwoundjoin.whole_s2c`, capgaps): the
corpus's one is 20260928T103123 :65009. Any other refusal RAISES.

Standard library only; the vault through `vaultpath`; tapes framed whole
(`deepwoundjoin.sequence`); the tables out of the owner's own exes
(`rechargeprobe._exe_tables`). The pure functions (`actions_of`, `completion_rows`,
`score`, `hero_e3`) take a decoded message list and are tested without a vault.
"""
import argparse
import collections
import contextlib
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
CLIENTSCAN = os.path.join(PARENT, "clientscan")
if CLIENTSCAN not in sys.path:
    sys.path.insert(0, CLIENTSCAN)

OP_CREATE = 0x0020          # [agent, ...]
OP_INT = 0x009F             # [prop, agent, value]
OP_INT_TARGET = 0x00A0      # [prop, agent, target, value]
OP_E5 = 0x00E5              # [agent, skill, ...]  a body's / the player's landing
OP_E3 = 0x00E3              # [agent, skill, ...]  its release
PROP_ATTACK_STARTED = 4
PROP_ATTACK_SKILL_FINISHED = 46
PROP_INSTANT = 48
PROP_ATTACK_SKILL_STOPPED = 49
PROP_ATTACK_SKILL_ACTIVATED = 50
PROP_SKILL_FINISHED = 58
PROP_SKILL_STOPPED = 59
PROP_SKILL_ACTIVATED = 60
START_PROPS = (PROP_SKILL_ACTIVATED, PROP_ATTACK_SKILL_ACTIVATED, PROP_ATTACK_STARTED)
CLOSE_PROPS = (PROP_SKILL_FINISHED, PROP_ATTACK_SKILL_FINISHED, PROP_SKILL_STOPPED,
               PROP_ATTACK_SKILL_STOPPED)

AFTERCAST = 0.75            # the class P1/P2 score (1,475 of 1,641 playable 38888 rows)
FLOOR_S = 0.70              # AFTERCAST less the corpus's 50 ms batch shoulder
MASS_LO, MASS_HI = 0.70, 0.80
MASS_SHARE = 0.30
CONTROL_SHARE = 0.25
INSTANT_TYPES = (3, 15, 16)     # authsrv.INSTANT_TYPE_CODES: Stance, Shout, type 16
ATTACK_TYPE = 14                # authsrv.ATTACK_TYPE_CODE
NEXT_KIND = {"S60": "cast", "S50": "attack skill", "S4": "swing"}


# ---- the pure half: a decoded message list in, rows out ----------------------------

def actions_of(seq, player):
    """{(agent, incarnation): [(t, tag, skill), ...]} in WIRE ORDER for every agent
    other than `player`. Tags: "S60" / "S50" / "S4" a start, "F58" / "F46" / "F59" /
    "F49" a close, "I48" an instant skill. `seq` is [(index, t, op, values)] with
    values carrying the opcode at [0], as `deepwoundjoin.sequence` returns."""
    inc = collections.Counter()
    ev = collections.defaultdict(list)
    for _i, t, op, v in seq:
        if op == OP_CREATE and len(v) > 1:
            inc[v[1]] += 1
            continue
        if op == OP_INT_TARGET and len(v) >= 5 and v[1] in START_PROPS:
            a = v[2]
            if a == player:
                continue
            ev[(a, inc[a])].append(
                (t, "S%d" % v[1], v[4] if v[1] != PROP_ATTACK_STARTED else None))
        elif op == OP_INT and len(v) >= 4:
            prop, a = v[1], v[2]
            if a == player:
                continue
            if prop in (PROP_SKILL_ACTIVATED, PROP_ATTACK_SKILL_ACTIVATED):
                # the un-targeted announce (CASTAI-R2: a byte-3 non-heal on the caster)
                ev[(a, inc[a])].append((t, "S%d" % prop, v[3]))
            elif prop in CLOSE_PROPS:
                ev[(a, inc[a])].append((t, "F%d" % prop, None))
            elif prop == PROP_INSTANT:
                ev[(a, inc[a])].append((t, "I48", v[3]))
    return dict(ev)


def completion_rows(actions):
    """One row per completed SPELL: a "F58" whose most recent start was an "S60" with
    no other close between them, and a next start after it. Row keys: agent, inc,
    skill, t (the 58), gap (to the next start), next (its tag), next_skill,
    instant_gap (the 58 to the first "I48" before that start, or None)."""
    rows = []
    for (agent, inc), lst in actions.items():
        for i, (t, tag, _sk) in enumerate(lst):
            if tag != "F58":
                continue
            start = None
            for j in range(i - 1, -1, -1):
                tj = lst[j][1]
                if tj.startswith("F"):
                    break               # another close sits between: not this cast's
                if tj.startswith("S"):
                    start = lst[j]
                    break
            if start is None or start[1] != "S60":
                continue
            nxt, inst = None, None
            for j in range(i + 1, len(lst)):
                tj = lst[j][1]
                if tj == "I48" and inst is None:
                    inst = lst[j][0]
                if tj.startswith("S"):
                    nxt = lst[j]
                    break
            if nxt is None:
                continue
            rows.append({"agent": agent, "inc": inc, "skill": start[2], "t": round(t, 3),
                         "gap": round(nxt[0] - t, 3), "next": nxt[1],
                         "next_skill": nxt[2],
                         "instant_gap": (round(inst - t, 3) if inst is not None else None)})
    return rows


def hero_e3(seq, player):
    """[(agent, skill, E3 - E5)] for every non-observer 0x00E5 followed by that
    agent's 0x00E3 for the same skill before its next 0x00E5 of it."""
    open_e5 = {}
    out = []
    for _i, t, op, v in seq:
        if op not in (OP_E5, OP_E3) or len(v) < 3:
            continue
        a, sk = v[1], v[2]
        if a == player:
            continue
        if op == OP_E5:
            open_e5[(a, sk)] = t
        else:
            t5 = open_e5.pop((a, sk), None)
            if t5 is not None:
                out.append((a, sk, round(t - t5, 3)))
    return out


def _share(xs, lo, hi):
    return (sum(1 for x in xs if lo <= x < hi) / len(xs)) if xs else 0.0


def _lookup(table):
    return table if callable(table) else table.get


def score(rows, table=None):
    """P1-P3 and the by-kind split over completion rows; `table` maps skill id ->
    (activation, aftercast, recharge, type_code) or is a callable doing the same
    (None for an unknown id); a row carrying its own "_table" (its connection's
    build) is looked up there. A row whose skill the table lacks is counted in
    "untabled" and scored nowhere."""
    groups = collections.defaultdict(list)
    kinds = collections.defaultdict(list)
    instants = []
    per_skill = collections.defaultdict(list)
    untabled = 0
    for r in rows:
        row = _lookup(r.get("_table") or table)(r["skill"])
        if row is None:
            untabled += 1
            continue
        aft = round(float(row[1]), 4)
        groups[aft].append(r["gap"])
        per_skill[(aft, r["skill"])].append(r["gap"])
        if aft == AFTERCAST:
            kinds[r["next"]].append(r["gap"])
            if r["instant_gap"] is not None:
                instants.append(r["instant_gap"])
    main = sorted(groups.get(AFTERCAST, ()))
    ctrl = sorted(groups.get(0.0, ()))
    below = [g for g in main if g < FLOOR_S]
    return {
        "n": len(main), "min": main[0] if main else None,
        "p5": main[len(main) // 20] if main else None,
        "p10": main[len(main) // 10] if main else None,
        "median": statistics.median(main) if main else None,
        "below": len(below),
        "p1": bool(main) and not below,
        "mass": sum(1 for g in main if MASS_LO <= g < MASS_HI),
        "mass_share": _share(main, MASS_LO, MASS_HI),
        "p2": bool(main) and _share(main, MASS_LO, MASS_HI) >= MASS_SHARE,
        "control_n": len(ctrl), "control_under": sum(1 for g in ctrl if g < FLOOR_S),
        "control_min": ctrl[0] if ctrl else None,
        "control_skills": sorted({sk for (a, sk) in per_skill if a == 0.0}),
        "control_by_skill": {sk: (sum(1 for g in gs if g < FLOOR_S), len(gs), min(gs))
                             for (a, sk), gs in sorted(per_skill.items()) if a == 0.0},
        "p3": bool(ctrl) and _share(ctrl, 0.0, FLOOR_S) >= CONTROL_SHARE,
        "by_next": {NEXT_KIND.get(k, k): (len(v), min(v)) for k, v in sorted(kinds.items())},
        "instants": (len(instants), min(instants) if instants else None),
        "instant_gaps": sorted(instants),
        "other_classes": {a: (len(g), min(g)) for a, g in sorted(groups.items())
                          if a not in (AFTERCAST, 0.0)},
        "untabled": untabled,
    }


def p6_split(instant_gaps):
    """(the gaps STRICTLY inside (0, FLOOR_S), sorted; the count in the [58]'s own
    batch, gap 0.000). P6 scores only the first: batch order is not evidence -- the
    same connection carries [48] before [58] in one batch and after it in another
    (20260928T103123 :50061, t = 160.980 and 173.496)."""
    return (sorted(g for g in instant_gaps if 0.0 < g < FLOOR_S),
            sum(1 for g in instant_gaps if g == 0.0))


def score_e3(e3_rows, table=None):
    """P5 over the SPELL rows (table aftercast > 0, not an instant or attack type):
    every E3 - E5 is 0.000. `e3_rows` are (agent, skill, dt) or (agent, skill, dt,
    table) -- the fourth the row's own build table. Returns (n_scored, n_zero,
    by_skill {skill: (n, [dts])}, all_rows_n)."""
    by = collections.defaultdict(list)
    n = z = 0
    for e in e3_rows:
        _a, sk, dt = e[:3]
        row = _lookup(e[3] if len(e) > 3 else table)(sk)
        by[sk].append(dt)
        if row is None or float(row[1]) <= 0 or int(row[3]) in INSTANT_TYPES \
                or int(row[3]) == ATTACK_TYPE:
            continue
        n += 1
        z += dt == 0.0
    return n, z, {k: (len(v), sorted(set(v))[:6]) for k, v in sorted(by.items())}, len(e3_rows)


# ---- the vault half ------------------------------------------------------------------

_TABLES = {}        # build -> {skill: (activation, aftercast, recharge, type_code)} | None


def table_for(build, exe_by_build):
    """{skill: (activation, aftercast, recharge, type_code)} out of the exe of `build`
    (rechargeprobe.table_for's read with the +0x40 column kept), or None."""
    if build in _TABLES:
        return _TABLES[build]
    exe = exe_by_build.get(build)
    if exe is None:
        _TABLES[build] = None
        return None
    import skilltable       # noqa: E402  (clientscan, stdlib-only)
    with open(exe, "rb") as f:
        data = f.read()
    base, count, _score = skilltable.locate_table(data)
    rows = {}
    for sid in range(count):
        r = skilltable.parse_record(data, base, sid)
        rows[sid] = (float(r["activation"]), float(r["aftercast"]), float(r["recharge"]),
                     int(r["type_code"]))
    _TABLES[build] = rows
    return rows


def census():
    """Every live capture's whole game connections: completion rows and E3 rows per
    connection, each with the connection's build table."""
    import bufflog          # noqa: E402
    import deepwoundjoin    # noqa: E402
    import rechargeprobe    # noqa: E402
    import spellhitjoin     # noqa: E402
    import tape             # noqa: E402
    import vaultpath        # noqa: E402
    codec = bufflog.Codec()
    live = vaultpath.require_dir("captures", "live", why="npcaftercast reads live captures")
    exe_by_build = rechargeprobe._exe_tables()
    out = {"conns": [], "excluded": [], "set_aside": [], "exe_builds": sorted(exe_by_build)}
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        for ch in deepwoundjoin.whole_s2c(cap, out["set_aside"]):
            seq = deepwoundjoin.sequence(cap, ch["connection"], codec)
            build = tape.client_version(cap, ch["connection"])["build"]
            player, _p, why = spellhitjoin.observer_of(
                seq, spellhitjoin.c2s_of(cap, ch["file"]))
            if why is not None and why.startswith("observer rules disagree"):
                out["excluded"].append((stamp, ch["connection"], "observer-refused"))
                continue
            table = table_for(build, exe_by_build)
            if table is None:
                out["excluded"].append((stamp, ch["connection"], "no-table-for-build %s" % build))
                continue
            out["conns"].append({"capture": stamp, "connection": ch["connection"],
                                 "build": build, "player": player,
                                 "rows": completion_rows(actions_of(seq, player)),
                                 "e3": hero_e3(seq, player), "table": table})
    return out


def pooled(conns):
    """Completion rows pooled over connections, each carrying its OWN build's table."""
    return [dict(r, _table=c["table"]) for c in conns for r in c["rows"]]


def ours(path, build, exe_by_build=None):
    """Completion rows of one of OUR recorder captures (observer agent 1,
    `timingjoin.load_ours`), scored on `build`'s table."""
    import rechargeprobe    # noqa: E402
    import timingjoin       # noqa: E402
    exe_by_build = exe_by_build if exe_by_build is not None else rechargeprobe._exe_tables()
    label, s2c, me = timingjoin.load_ours(path)
    seq = [(i, t, op, v) for i, (t, op, v) in enumerate(s2c)]
    table = table_for(build, exe_by_build)
    if table is None:
        raise SystemExit(f"no table for build {build} in the vault "
                         f"(have {sorted(exe_by_build)})")
    return label, completion_rows(actions_of(seq, me)), hero_e3(seq, me), table


def _fmt(sc):
    return (f"n={sc['n']} min={sc['min']} p5={sc['p5']} p10={sc['p10']} "
            f"median={sc['median']} below {FLOOR_S:.2f}: {sc['below']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ours", help="one of our recorder captures (authsrv-*-c1.jsonl)")
    ap.add_argument("--ours-build", type=int, default=None,
                    help="the table build to score --ours on (default: the newest in the vault)")
    ap.add_argument("--json", action="store_true",
                    help="stdout carries ONLY the JSON document; the census's own lines "
                         "(capgaps' SET ASIDE) go to stderr")
    args = ap.parse_args(argv)
    with (contextlib.redirect_stdout(sys.stderr) if args.json
          else contextlib.nullcontext()):
        c = census()
        sc = score(pooled(c["conns"]))
        e3n, e3z, e3by, e3all = score_e3([(a, sk, dt, cc["table"]) for cc in c["conns"]
                                          for a, sk, dt in cc["e3"]])
        p5 = ("UNDECIDABLE" if e3n == 0 else "HOLDS" if e3z == e3n else "FAILS")
        inst_in, inst_co = p6_split(sc["instant_gaps"])
        res = {"retail": sc, "connections": len(c["conns"]), "excluded": c["excluded"],
               "set_aside": c["set_aside"], "tables": c["exe_builds"],
               "builds": dict(sorted(collections.Counter(
                   cc["build"] for cc in c["conns"]).items())),
               "p5": p5, "p6_refuted_by": inst_in, "p6_cobatched": inst_co,
               "e3_scored": e3n, "e3_zero": e3z, "e3_by_skill": e3by, "e3_rows": e3all}
        if args.ours:
            import rechargeprobe    # noqa: E402
            exe_by_build = rechargeprobe._exe_tables()
            build = args.ours_build or max(exe_by_build)
            label, orows, oe3, otab = ours(args.ours, build, exe_by_build)
            res["ours"] = dict(score(orows, otab), label=label, build=build)
            res["ours_e3"] = score_e3(oe3, otab)
    if args.json:
        print(json.dumps(res, indent=1, default=str))
        return res
    print(f"connections {res['connections']} on builds {res['builds']} (each on its own "
          f"build's table; the vault's tables {res['tables']}); excluded "
          f"{len(c['excluded'])} {c['excluded'] or ''}; set aside "
          f"{[(r['capture'], r['connection']) for r in c['set_aside']] or 'none'}")
    print(f"completed spells followed by a start: {sum(len(cc['rows']) for cc in c['conns'])}"
          f" (untabled {sc['untabled']})")
    print(f"P1 FLOOR (aftercast {AFTERCAST}: no next start under {FLOOR_S}): {_fmt(sc)} -> "
          f"{'HOLDS' if sc['p1'] else 'FAILS'}")
    print(f"P2 MASS (>= {MASS_SHARE:.0%} in [{MASS_LO}, {MASS_HI})): {sc['mass']} of {sc['n']}"
          f" = {sc['mass_share']:.1%} -> {'HOLDS' if sc['p2'] else 'FAILS'}")
    print(f"P3 CONTROL (aftercast 0: >= {CONTROL_SHARE:.0%} under {FLOOR_S}): "
          f"{sc['control_under']} of {sc['control_n']} (min {sc['control_min']}; skills "
          f"{sc['control_skills']}) -> {'HOLDS' if sc['p3'] else 'FAILS'}")
    print(f"   the control by skill (under {FLOOR_S}, n, min): {sc['control_by_skill']}")
    print(f"   by next start (n, min): {sc['by_next']}")
    print(f"   an instant [48] between the 58 and the next start (n, min): {sc['instants']}")
    print(f"   other aftercast classes (n, min; printed, not scored): {sc['other_classes']}")
    print(f"P5 E3 RIDES E5 (non-observer spell rows, table aftercast > 0): {e3z} of {e3n} at "
          f"0.000 -> {p5}; every E5/E3 pair by skill (n, dts): {e3by}")
    print(f"P6 NO INSTANT INSIDE THE WINDOW: {len(inst_in)} of {sc['instants'][0]} strictly "
          f"inside (0, {FLOOR_S}) {inst_in}; {inst_co} in the [58]'s own batch (printed, "
          f"not scored) -> {'REFUTED' if inst_in else 'HOLDS'}")
    if args.ours:
        o = res["ours"]
        print(f"OURS {o['label']} on build {o['build']}: P1 {_fmt(o)} -> "
              f"{'HOLDS' if o['p1'] else 'FAILS'}  (P4 registered: FAILS on "
              f"authsrv-20260928T002701-c1)")
        print(f"   by next start (n, min): {o['by_next']}; skills: control "
              f"{o['control_skills']}, other classes {o['other_classes']}")
        print(f"   E3 rows {res['ours_e3']}")
    return res


if __name__ == "__main__":
    main()
