#!/usr/bin/env python3
"""Which creature definitions on the live tapes are MELEE subjects for a notice-radius
plan, and on which map? (monsterai §9 Q7; §13's plan picked its zone with this.)

    python studies/monsterai/review/meleecensus.py

WHY IT EXISTS. §12.5 is the lesson that made a census necessary: a CASTER opens on the
player with a spell from its cast range and never walks, so its notice instant cannot be
separated from that range -- the level-6 Elementalist of the Jarin run gave two
reconstructed points and no clean one. A creature that charges and swings shows its notice
as the instant it moves, so the only good subjects for Q7 are melee, and which definitions
those are is a fact the tapes already hold.

WHAT IT READS, and the boundary it sits on. The `0x0056` definition record, whose layout is
`npcdefs.py`'s and whose profession and level bytes N10 reads: everything here is a number
MEASURED off ArenaNet's own bytes -- a definition index, a profession byte, a level byte, a
map id -- which is the permitted side of the provenance gate (`PLAN.md` §7 Q3, measurement
not expression). No name is read, resolved or printed.

THE PROFESSION BYTE IS THE PROXY, AND IT IS A PROXY. Profession 1 (Warrior) is taken as
"melee"; the run's own approach is what confirms a subject charges. The proxy is checked
against what the tapes showed: def 1397 (profession 1) charged on three approaches (N7),
and every creature that opened with a spell instead -- 4440, 1432 -- carries profession 6.
It is not checked the other way: a profession-1 definition may still be passive (def 4431
is, §12.6), which costs a row rather than corrupting one.

ONLY MONSTER TOKENS. A definition is listed only if some agent created with it in that
connection carried a monster token (`mon1`/`mons`) and kind 9, so gadgets, NPCs and the
Isle's `att2` training dummies do not enter the table.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "studies/npctrack/review"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire                                                # noqa: E402
import noticeradius as nr                                      # noqa: E402

S2C_MAP = 0x0199
MELEE_PROFESSION = 1
PROF = {1: "War", 2: "Ran", 3: "Mo", 4: "Nec", 5: "Mes", 6: "Ele",
        7: "Ass", 8: "Rit", 9: "Par", 10: "Der"}


def census(root=None):
    """map id -> {(definition, profession, level): {capture stamps}}."""
    bymap = collections.defaultdict(lambda: collections.defaultdict(set))
    for capdir, gf in livewire.live_connections(root):
        stamp = os.path.basename(capdir)
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        if not ok or not merged:
            continue
        maps = [v[2] for (t, dr, op, v) in merged
                if dr == "s2c" and op == S2C_MAP and len(v) >= 3]
        mid = maps[-1] if maps else None
        creates = nr.creates_of(merged)
        # A definition counts only where a kind-9 monster token was created with it.
        mon_defs = {c[4] for cs in creates.values() for c in cs
                    if c[2] == nr.KIND_NPC and c[3] in nr.MONSTER_TOKENS}
        for (t, dr, op, v) in merged:
            if dr == "s2c" and op == nr.S2C_DEFINITION and len(v) >= 9:
                dfn = v[1] & nr.DEFINITION_MASK
                if dfn in mon_defs:
                    bymap[mid][(dfn, v[7], v[8])].add(stamp)
    return bymap


def main(argv):
    bymap = census()
    if not bymap:
        print("no live captures decoded -- nothing to census")
        return 2
    melee = 0
    for mid in sorted(bymap, key=lambda m: (m is None, m)):
        rows = bymap[mid]
        n = sum(1 for (_d, prof, _l) in rows if prof == MELEE_PROFESSION)
        melee += n
        print(f"map {mid}: {len(rows)} monster definitions, {n} melee (profession "
              f"{MELEE_PROFESSION})")
        for (dfn, prof, lvl), stamps in sorted(
                rows.items(), key=lambda kv: (kv[0][1] != MELEE_PROFESSION,
                                              kv[0][2], kv[0][0])):
            mark = "  <- melee" if prof == MELEE_PROFESSION else ""
            print(f"   def {dfn:5d}  {PROF.get(prof, prof):3}  lvl {lvl:2d}  "
                  f"tapes {len(stamps)}  newest {sorted(stamps)[-1]}{mark}")
    # No section signs in printed output: this prints to a cp1252 console, the same
    # reason `noticeradius.fourcc` is ascii-safe.
    print(f"\n{melee} melee definition(s) across {len(bymap)} map(s). A melee subject is "
          f"the only clean one for the notice radius (sec.12.5): a caster's opener cannot "
          f"be told from its cast range.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
