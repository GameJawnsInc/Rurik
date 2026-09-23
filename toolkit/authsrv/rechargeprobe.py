r"""Does a body's recharge run from the START of its cast or from its COMPLETION? Retail's wire.

    python toolkit/authsrv/rechargeprobe.py            # every live capture
    python toolkit/authsrv/rechargeprobe.py --json
    python toolkit/authsrv/rechargeprobe.py --gaps     # every gap, per (caster, skill)
    python toolkit/authsrv/rechargeprobe.py --no-split # the known-bad arm: recycled ids pooled

WHY THIS EXISTS. `authsrv.py`'s hostile and party cast sites arm `skill_ready[slot] =
now + recharge` at the cast's START and say so: "a RECONSTRUCTION from the table's
semantics, not an observation: no NPC in the corpus casts twice, so there is no recharge
cycle anywhere to tell start-triggered from finish-triggered" (monsterai FINDINGS 3.6
item 3, isle PLAN's aftercast line). That negative was written over a corpus of two
captures. The corpus is now 36, and other agents cast the same skill many times.

THE INSTRUMENT. Every `0x00A0 [60, caster, target, skill]` announcement (a cast's start,
int-with-target -- the shape every other agent's cast takes, monsterai 3.6 item 2) by an
agent other than the connection's own player, grouped per (connection, caster
INCARNATION, skill); the GAPS between consecutive announcements of one group. The table
gives activation and recharge for that skill ON THE CONNECTION'S OWN BUILD (the client's
VERSION frame names it; the vault's exe of that build supplies the row through
`clientscan/skilltable.py` -- over the 3,443 ids the 38797 and 38888 tables share, 49
recharges and 11 activations differ, so the pinned bulk table is not enough in general.
None of the seven discriminating skills below moves on any of the five vault builds, so
here the per-build read is hygiene, not a result; the first cut wrote "47", uncounted --
fix pass, D5B-R9). A body that re-casts the moment it may shows the anchor as the group's
MINIMUM gap:

    recharge from the START       ->  min gap ~ recharge
    recharge from the COMPLETION  ->  min gap ~ recharge + activation

THE SPLIT, and why it is not optional. An agent id is RECYCLED: a body dies, its id is
removed (`0x0021 [id]`) and a new body arrives under it (`0x0020 [id, ...]`) -- on
`20260917T224104` conn 62557 sixteen ids are created two to four times each. Two casts
of one skill by two BODIES under one id read as one body's short cycle, so every
(connection, agent) key is split at each `0x0020` for that id and a gap never crosses a
create. `--no-split` pools them (the known-bad arm), and P3 requires the two arms to
DIFFER on this corpus -- a split that changes nothing has not been shown to work.

THE PREDICTIONS, stated before the numbers (the survey's: DESKWORK-D5 step 4):

  P1  THE FLOOR: at least 4 skills (distinct ids) each with >= 5 gaps after the split,
      on a build whose table is in the vault. Below it the anchor stays RECONSTRUCTION
      and nothing ships.
  P2  THE ANCHOR: for every skill at the floor whose activation exceeds the tolerance
      (so the two anchors are separable), the minimum gap sits within TOL of
      recharge + activation and NOT within TOL of recharge alone. The survey: 8 of 9
      skills on recharge + activation (186 8.51, 179 8.00, 230 6.00, 222 5.99).
      AS WRITTEN, FAILED (fix pass 2026-09-23, D5B-R4 / ENG-6 -- the first cut scored
      a "majority" rule that no prediction named and did not say so): of the 11 skills
      at the floor, 229 sits at recharge start-to-start and at recharge - activation
      completion-to-next (START-like), and 160 / 197 / 220 / 1097 sit ABOVE both
      anchors -- the AI's own wait, which the minimum cannot see past. RE-STATED, not
      fitted: over the DISCRIMINATING skills (at the floor, separable, on one anchor
      or the other), completion is the anchor when it is the clear majority (at least
      FLOOR_SKILLS of them and more than twice the start-anchored). Both verdicts
      are printed; `p2_as_written` is the registered one. Four of the six
      completion-anchored skills (179, 185, 186, 286) come from ONE capture
      (20260817T231139); 222 and 230 from two others each.
  P3  THE SPLIT WORKS: with recycled ids pooled, at least one gap is SHORTER than the
      skill's recharge; with the split, none is (a sub-recharge gap after the split
      would refute the table, the split or the announcement's meaning, and is named).
      The survey's suspect: skill 229's 5.25 against 7.0.
      AS WRITTEN, FAILED (fix pass, D5B-R3 / ENG-2 -- the first cut's log said "the
      split works"): the split half FAILS -- 229's two sub-recharge gaps survive the
      split -- and the pooled half holds only TRIVIALLY, on those same two: both arms
      give {229: [4.497, 3.251]}, so the arms do NOT DIFFER on sub-recharge gaps,
      which is what P3 required; they differ by six pairs (160: 56 -> 60, 222: 10 ->
      12) and no minimum moves. Both 229 casters were created ONCE (agent 85 on
      20260917T090355, agent 117 on 20260917T224104), so the survey's recycled-id
      explanation of 229 is REFUTED: its short gaps are real, on singly-created
      bodies (the named divergence). On THIS corpus the split is not load-bearing;
      that it works at all is shown on a SYNTHETIC re-created id in test_recharge
      (one id, a cast, a remove, a re-create, the same skill 1 s later: pooled reads a
      sub-recharge pair, split reads none), the route's acceptance (c).
      `p3_as_written` is printed per arm: FALSE on the split arm, TRUE (trivially) on
      the pooled one -- the same set on both is the failure.
  P4  THE BUILD: every connection's build is read from the client's own VERSION frame;
      a connection whose build has no exe in the vault is EXCLUDED and counted, never
      scored against another build's table.

What this cannot separate: the AI's own wait from the recharge (the minimum bounds
both, which is why it is the minimum that is read); a skill whose activation is 0 (an
attack skill: the two anchors coincide); an aftercast longer than the recharge.

Standard library only; reads the vault through `vaultpath`; refuses a tape that does not
frame whole (`deepwoundjoin.sequence`); the tables are read out of the owner's own exes.
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
CLIENTSCAN = os.path.join(PARENT, "clientscan")
if CLIENTSCAN not in sys.path:
    sys.path.insert(0, CLIENTSCAN)

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import spellhitjoin     # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_CREATE = 0x0020         # [agent, ...]
OP_REMOVE = 0x0021         # [agent]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
PROP_SKILL_ACTIVATED = 60
TOL = 0.35                 # s; a tick plus the corpus's batch shoulder, well under any
                           # activation that separates the two anchors (0.75 s and up)
FLOOR_SKILLS = 4
FLOOR_GAPS = 5


OP_INT = 0x009F            # [prop, agent, value]
PROP_ATTACK_SKILL_FINISHED = 46
PROP_SKILL_FINISHED = 58
PROP_SKILL_STOPPED = 59


def gaps_of(seq, player, split=True):
    """{(caster, skill): [pair, ...]} for one framed sequence, casters other than
    `player`. A PAIR is two consecutive announcements of one skill by one caster
    incarnation: {"gap": B - A (start to start), "done": B - the caster's first
    [58, caster, 0] after A (completion to the next start), or None when no 58
    came before B -- that first cast was cancelled or interrupted ([59] counted
    in "stopped"), so the pair is NOT A CYCLE and is set aside. Whether such a
    cast started a recharge is UNVERIFIED (fix pass, D5B-R11): all 11 uncompleted
    pairs' next-cast gaps are 7.00 s or more, which cannot separate "no recharge
    started" from "started"; the player's interrupted cast DOES recharge
    (castmech 4), a body's is on no tape}.

    With `split`, the caster key is (agent, incarnation) where the incarnation
    counts the agent's 0x0020 creates so far; a pair never crosses one.
    Returns (pairs, n_creates_recycled, n_announcements)."""
    incarnation = collections.Counter()
    last = {}                # (caster_key, skill) -> [t_announce, t_finished | None, stopped]
    newest = {}              # caster_key -> the (caster_key, skill) it announced last
    pairs = collections.defaultdict(list)
    recycled = 0
    n_ann = 0
    for _i, t, op, v in seq:
        if op == OP_CREATE and len(v) > 1:
            incarnation[v[1]] += 1
            if incarnation[v[1]] > 1:
                recycled += 1
            continue
        if op == OP_INT and len(v) > 3 and v[1] in (PROP_SKILL_FINISHED,
                                                    PROP_ATTACK_SKILL_FINISHED,
                                                    PROP_SKILL_STOPPED):
            # A completion or a stop belongs to the caster's MOST RECENT
            # announcement (one caster casts one thing at a time); an older
            # record left open stays open -- that cast ended with no 58.
            ck = (v[2], incarnation[v[2]] if split else 0)
            key = newest.get(ck)
            if key is not None and last[key][1] is None and not last[key][2]:
                if v[1] == PROP_SKILL_STOPPED:
                    last[key][2] = True
                else:
                    last[key][1] = t
            continue
        if op != OP_INT_TARGET or len(v) < 5 or v[1] != PROP_SKILL_ACTIVATED:
            continue
        caster, skill = v[2], v[4]
        if caster == player:
            continue
        n_ann += 1
        ck = (caster, incarnation[caster] if split else 0)
        key = (ck, skill)
        prev = last.get(key)
        if prev is not None:
            t0, t58, stopped = prev
            pairs[(caster, skill)].append({
                "gap": round(t - t0, 3),
                "done": (round(t - t58, 3) if t58 is not None else None),
                "stopped": stopped, "t": round(t0, 3)})
        last[key] = [t, None, False]
        newest[ck] = key
    return dict(pairs), recycled, n_ann


# ---- the table on the connection's own build ------------------------------------

_TABLES = {}       # build -> {skill: (activation, recharge)} | None


def _exe_tables():
    """{build: exe_path} for every pristine Gw.exe under vault/client, by hash."""
    out = {}
    try:
        import skilltable       # noqa: E402  (clientscan, stdlib-only)
    except ImportError:
        return out
    root = vaultpath.vault_path("client")
    try:
        dirs = sorted(os.listdir(root))
    except OSError:
        return out
    for d in dirs:
        exe = os.path.join(root, d, "Gw.exe")
        if not os.path.exists(exe):
            continue
        with open(exe, "rb") as f:
            data = f.read()
        b = skilltable.build_of(data)
        if b is not None:
            out[b] = exe
    return out


def table_for(build, exe_by_build):
    """{skill: (activation, recharge)} read out of the exe of `build`, or None."""
    if build in _TABLES:
        return _TABLES[build]
    exe = exe_by_build.get(build)
    if exe is None:
        _TABLES[build] = None
        return None
    import skilltable       # noqa: E402
    with open(exe, "rb") as f:
        data = f.read()
    base, count, _score = skilltable.locate_table(data)
    rows = {}
    for sid in range(count):
        r = skilltable.parse_record(data, base, sid)
        rows[sid] = (float(r["activation"]), float(r["recharge"]))
    _TABLES[build] = rows
    return rows


def census(codec=None, split=True):
    """Every live capture, every game connection that frames whole; the build per
    connection from the VERSION frame; gaps per (capture, conn, caster, skill)."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="rechargeprobe reads live captures")
    exe_by_build = _exe_tables()
    rows = []
    excluded = []
    builds = collections.Counter()
    recycled_total = 0
    n_ann_total = 0
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
                build = tape.client_version(cap_dir, ch["connection"])["build"]
            except (bufflog.BuffLogError, tape.TapeError) as exc:
                excluded.append((stamp, ch["connection"], "unframed", str(exc)[:60]))
                continue
            builds[build] += 1
            table = table_for(build, exe_by_build)
            # "Other agents" needs the observer: property 41, cross-checked against
            # the answered presses (spellhitjoin.observer_of). The first-0x00E3 rule
            # took the JARIN HERO for the player (20260914T005758 conn 56011) and so
            # left the hero's one announcement out: 346 -> 347, no pair moves
            # (skills 43.8). Where the two rules DISAGREE the connection is excluded
            # -- its other agents are undefined. Where neither answers (the corpus's
            # one: 20260807T133758 conn 54560, 88 messages, no announcement) nothing
            # is excluded, as before.
            player, _press, why = spellhitjoin.observer_of(
                seq, spellhitjoin.c2s_of(cap_dir, ch["file"]))
            if why is not None and why.startswith("observer rules disagree"):
                excluded.append((stamp, ch["connection"], "observer-refused", why[:60]))
                continue
            gaps, recycled, n_ann = gaps_of(seq, player, split=split)
            recycled_total += recycled
            n_ann_total += n_ann
            if table is None:
                excluded.append((stamp, ch["connection"], "no-table-for-build", build))
                continue
            for (caster, skill), ps in gaps.items():
                act, rec = table.get(skill, (None, None))
                rows.append({"capture": stamp, "connection": ch["connection"],
                             "port": ch["connection"].split("->")[0].rsplit(":", 1)[-1],
                             "build": build, "caster": caster, "skill": skill,
                             "pairs": ps,
                             "gaps": [p["gap"] for p in ps if p["done"] is not None],
                             "done": [p["done"] for p in ps if p["done"] is not None],
                             "uncompleted": [p["gap"] for p in ps if p["done"] is None],
                             "activation": act, "recharge": rec})
    return {"rows": rows, "excluded": excluded, "builds": dict(builds),
            "exe_builds": sorted(exe_by_build), "recycled_creates": recycled_total,
            "announcements": n_ann_total, "split": split}


def per_skill(rows):
    """{skill: {"n" (completed pairs), "min" (start-to-start), "min_done"
    (completion-to-next-start), "median", "uncompleted" (pairs whose first cast
    never completed), "activation", "recharge", "builds", "groups"}} pooled over
    every (connection, caster) group; a skill whose activation or recharge
    differs across the builds present is kept per build as "skill@build"."""
    g = collections.defaultdict(lambda: {"gaps": [], "done": [], "unc": []})
    meta = {}
    for r in rows:
        key = r["skill"]
        if r["activation"] is None:
            continue
        prev = meta.get(key)
        if prev is not None and prev[:2] != (r["activation"], r["recharge"]):
            key = f"{r['skill']}@{r['build']}"
        meta.setdefault(key, (r["activation"], r["recharge"], set()))[2].add(r["build"])
        g[key]["gaps"].extend(r["gaps"])
        g[key]["done"].extend(r["done"])
        g[key]["unc"].extend(r["uncompleted"])
    out = {}
    for key, d in g.items():
        act, rec, bs = meta[key]
        gs = d["gaps"]
        out[key] = {"n": len(gs), "min": min(gs) if gs else None,
                    "min_done": min(d["done"]) if d["done"] else None,
                    "median": statistics.median(gs) if gs else None,
                    "uncompleted": d["unc"],
                    "activation": act, "recharge": rec, "builds": sorted(bs),
                    "groups": sum(1 for r in rows if (r["skill"] == key
                                                     or f"{r['skill']}@{r['build']}" == key))}
    return out


def _near(x, y):
    return x is not None and abs(x - y) <= TOL


def score(c):
    """The numbers P1-P4 are judged on, on the census given (split or pooled).

    Two readings per skill, both over COMPLETED pairs: the start-to-start
    minimum against recharge + activation (completion-anchored) or recharge
    (start-anchored); the completion-to-next-start minimum against recharge
    (completion-anchored) or recharge - activation (start-anchored). A skill
    whose minimum sits above both is the AI's own wait ("neither")."""
    ps = per_skill(c["rows"])
    at_floor = {k: v for k, v in ps.items() if v["n"] >= FLOOR_GAPS}
    separable = {k: v for k, v in at_floor.items() if v["activation"] > TOL}
    on_completion = {k: v for k, v in separable.items()
                     if _near(v["min"], v["recharge"] + v["activation"])
                     and _near(v["min_done"], v["recharge"])}
    on_start = {k: v for k, v in separable.items()
                if _near(v["min"], v["recharge"])
                and _near(v["min_done"], v["recharge"] - v["activation"])}
    neither = {k: v for k, v in separable.items()
               if k not in on_completion and k not in on_start}
    # A completed pair whose completion-to-next gap is SHORTER than the recharge
    # refutes completion-anchoring outright (the skill re-cast while recharging).
    sub_recharge = {}
    for r in c["rows"]:
        if r["recharge"] is None:
            continue
        short = [d for d in r["done"] if d < r["recharge"] - TOL]
        if short:
            sub_recharge.setdefault(r["skill"], []).extend(short)
    return {
        "split": c["split"],
        "connections_by_build": c["builds"],
        "tables_in_vault": c["exe_builds"],
        "excluded": len(c["excluded"]),
        "excluded_no_table": sum(1 for e in c["excluded"] if e[2] == "no-table-for-build"),
        "announcements": c["announcements"],
        "recycled_creates": c["recycled_creates"],
        "skills": len(ps),
        "pairs": sum(v["n"] for v in ps.values()),
        "uncompleted_pairs": sum(len(v["uncompleted"]) for v in ps.values()),
        "skills_at_floor": sorted(at_floor),
        "p1": len(at_floor) >= FLOOR_SKILLS,
        "separable": sorted(separable),
        "on_completion": {k: (v["min"], v["min_done"], v["recharge"], v["activation"], v["n"])
                          for k, v in on_completion.items()},
        "on_start": {k: (v["min"], v["min_done"], v["recharge"], v["activation"], v["n"])
                     for k, v in on_start.items()},
        "neither": {k: (v["min"], v["min_done"], v["recharge"], v["activation"], v["n"])
                    for k, v in neither.items()},
        # P2 AS REGISTERED: every separable skill at the floor on completion and
        # none on start or above both. FALSE on this corpus (229 start-like, four
        # AI-wait-bound) -- printed beside the re-statement, never in its place.
        "p2_as_written": bool(separable) and len(on_completion) == len(separable),
        # THE RE-STATEMENT (docstring P2): the discriminating skills (separable,
        # at the floor, not AI-wait-bound) split into completion-anchored and
        # start-anchored. COMPLETION is the anchor when it is the clear majority.
        "discriminating": sorted(set(on_completion) | set(on_start)),
        "p2_completion_majority": (len(on_completion) >= FLOOR_SKILLS
                                   and len(on_completion) > 2 * len(on_start)),
        "sub_recharge": sub_recharge,
        # P3 AS REGISTERED, per arm: the split arm shows NO sub-recharge gap; the
        # pooled arm shows SOME. FALSE on both arms of this corpus (229's two).
        "p3_as_written": (not sub_recharge) if c["split"] else bool(sub_recharge),
        "per_skill": ps,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gaps", action="store_true", help="print every group's gaps")
    ap.add_argument("--no-split", action="store_true",
                    help="pool recycled agent ids (the known-bad arm)")
    args = ap.parse_args()
    c = census(split=not args.no_split)
    sc = score(c)
    if args.json:
        print(json.dumps({"score": sc, "rows": c["rows"], "excluded": c["excluded"]},
                         indent=1, default=str))
        return
    print(f"connections by build {sc['connections_by_build']}; tables in the vault "
          f"{sc['tables_in_vault']}; excluded {sc['excluded']} (no table for the build: "
          f"{sc['excluded_no_table']}); other agents' announcements {sc['announcements']}; "
          f"recycled creates {sc['recycled_creates']}; split={'ON' if sc['split'] else 'OFF'}")
    print(f"pairs {sc['pairs']} completed (the first cast carried its 58/46), "
          f"{sc['uncompleted_pairs']} whose first cast never completed (set aside: no "
          f"recharge started)")
    print(f"P1 floor (>= {FLOOR_SKILLS} skills with >= {FLOOR_GAPS} completed pairs): "
          f"{len(sc['skills_at_floor'])} of {sc['skills']} skills -> "
          f"{'HOLDS' if sc['p1'] else 'FAILS'} {sc['skills_at_floor']}")
    print(f"P2 anchor over the separable ones {sc['separable']} as (min start-to-start, min "
          f"completion-to-next, recharge, activation, n):")
    print(f"   COMPLETION-anchored {sc['on_completion']}")
    print(f"   START-anchored {sc['on_start']}")
    print(f"   neither (the AI's wait above both) {sc['neither']}")
    print(f"   P2 AS WRITTEN (every separable skill at the floor completion-anchored): "
          f"{'HOLDS' if sc['p2_as_written'] else 'FAILS'} ({len(sc['on_completion'])} of "
          f"{len(sc['separable'])})")
    print(f"   -> RE-STATED: COMPLETION is the majority anchor of the discriminating skills "
          f"{sc['discriminating']}: {'HOLDS' if sc['p2_completion_majority'] else 'FAILS'} "
          f"({len(sc['on_completion'])} completion vs {len(sc['on_start'])} start)")
    print(f"P3 completion-to-next gaps SHORTER than the recharge: {sc['sub_recharge'] or 'none'}"
          + ("  (split ON: predicted none)" if sc["split"] else "  (split OFF: predicted some)")
          + f" -> P3 AS WRITTEN {'HOLDS' if sc['p3_as_written'] else 'FAILS'} on this arm")
    print("per skill (over completed pairs; table activation + recharge on the builds):")
    for k, v in sorted(sc["per_skill"].items(), key=lambda kv: -kv[1]["n"]):
        if v["n"] == 0:
            print(f"   skill {str(k):>10s}  n=  0  ({len(v['uncompleted'])} uncompleted)")
            continue
        print(f"   skill {str(k):>10s}  n={v['n']:3d}  min {v['min']:6.2f}  min-done "
              f"{v['min_done']:6.2f}  med {v['median']:6.2f}   act {v['activation']:.2f} + rec "
              f"{v['recharge']:.0f} = {v['activation'] + v['recharge']:.2f}   builds "
              f"{v['builds']}  groups {v['groups']}  uncompleted {len(v['uncompleted'])}")
    if args.gaps:
        for r in sorted(c["rows"], key=lambda r: (r["skill"], r["capture"], r["caster"])):
            print(f"   {r['capture']} {r['port']} b{r['build']} caster {r['caster']:4d} skill "
                  f"{r['skill']:4d}: "
                  + " ".join((f"{p['gap']:.2f}/{p['done']:.2f}" if p["done"] is not None
                              else f"{p['gap']:.2f}/{'STOP' if p['stopped'] else 'none'}")
                             for p in r["pairs"]))
    if c["excluded"]:
        print("excluded connections:")
        for e in c["excluded"]:
            print(f"   {e}")


if __name__ == "__main__":
    main()
