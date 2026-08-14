#!/usr/bin/env python3
"""Check the authored skill names -- mostly, the arithmetic that keeps them apart.

    python toolkit/mapdata/test_skillnames.py

"188 names came out and they are all different" is worth almost nothing here, and
saying why is the whole design of this file. `assign()` RAISES on a duplicate, so
a run that reaches the end has already proved uniqueness by construction -- the
headline is the guard's own output, not a measurement of it. `name = "Skill %d" %
sid` would pass it too, for all 188, while meaning nothing.

So what is actually asserted is:

  * that the guard CAN fire (section 3 builds a colliding input and a group one
    past the pool, and requires both to be refused rather than wrapped);
  * that uniqueness is STRUCTURAL, one check per arm of the argument, each with
    the arm broken inline as a live function beside it (section 2);
  * that the names AGREE WITH THE PICTURES -- a skill's noun must come from the
    motif of the glyph `iconset` would actually arm for it (section 5), which is
    the claim `"Skill %d"` fails and no uniqueness check can see;
  * that the two modules' MOTIFS are the same number (section 4), because
    `motif_of` is a bare `%` and a modulo by the wrong constant names every skill
    after the wrong shape while every other check here stays green;
  * that the answer does not depend on dict order (section 2), which passes by
    luck today -- the caller happens to build its mapping in sorted order, and
    CPython dicts happen to preserve it.

Sections 0-4 need no vault, no archive and no client. Section 5 reads the pinned
client and the armed archive and declares a skip without them.
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import glyphs                                                    # noqa: E402
import skillnames as sn                                          # noqa: E402
import vaultpath                                                 # noqa: E402

# MEASURED 2026-08-14: 26 with no vault, 36 with one. The floor is the vault-less
# score, because sections 0-4 carry the whole uniqueness argument and its controls
# and can refute the design on a bare machine; section 5 adds the confirmation
# against the real roster and the armed archive.
#
# THIS COMMENT FIRST SAID "MEASURED ... 30 with no vault, 38 with one" AND BOTH
# NUMBERS WERE GUESSES -- in a file that already cited the two previous times the
# same thing happened. test_glyphs.py guessed 41 on a file that runs 32;
# test_emblem.py guessed 12/18 on 11/17 hours later; this is the third, and it
# wore the word MEASURED. The lesson evidently does not transfer by being written
# down near the mistake, so: run the file, read the banner, paste the number, and
# run it again with RURIK_VAULT pointed at an empty directory for the other one.
LEDGER = checks.Ledger("authored skill names", floor=26)
check = checks.adopt(LEDGER)

PROFESSION = 8


def guarded(fn):
    try:
        fn()
    except Exception as exc:                                     # noqa: BLE001
        check(False, "section %s completed" % fn.__name__,
              "%s: %s" % (type(exc).__name__, exc))


# --------------------------------------------------------------------------
# 0. the vocabulary


def section_vocabulary():
    print("\n== 0. the vocabulary ==")
    bad = sn.vocabulary_check()
    check(not bad, "vocabulary_check finds no problem", bad[:3])
    check(sn.POOL > sn.MEASURED_WORST_GROUP,
          "POOL exceeds the measured worst group -- a margin, not a coincidence",
          "%d > %d" % (sn.POOL, sn.MEASURED_WORST_GROUP))
    nouns = [w for pool in sn.NOUNS for w in pool] + list(sn.UNGLYPHED)
    check(len(set(nouns)) == len(nouns),
          "every noun is distinct across all pools -- the property global "
          "uniqueness reduces to", "%d words, %d distinct"
          % (len(nouns), len(set(nouns))))
    check(len(sn.NOUNS) == sn.MOTIFS and all(len(p) >= sn.POOL for p in sn.NOUNS),
          "every motif carries at least POOL nouns", sn.MOTIFS)
    # A vocabulary check that cannot fail is not a check.
    stash = sn.NOUNS
    try:
        sn.NOUNS = stash[:1] + (stash[0],) + stash[2:]
        check(bool(sn.vocabulary_check()),
              "and it goes RED on a duplicated noun pool -- the control")
    finally:
        sn.NOUNS = stash
    check(not sn.vocabulary_check(), "and green again once restored")


# --------------------------------------------------------------------------
# 1. the three arms of the uniqueness argument


def section_structure():
    print("\n== 1. uniqueness is structural, one check per arm ==")
    # ARM 1: same motif, same attribute, different j -> different NOUN.
    a = sn.name_for(3, 32, 0)
    b = sn.name_for(3, 32, 1)
    check(a.split()[1] != b.split()[1],
          "same motif+attribute, different rank -> different noun", (a, b))
    # ARM 2: same motif, different attribute -> different ADJECTIVE.
    c = sn.name_for(3, 32, 0)
    d = sn.name_for(3, 33, 0)
    check(c.split()[0] != d.split()[0],
          "same motif, different attribute -> different adjective", (c, d))
    check(c.split()[1] == d.split()[1],
          "...and the SAME noun, which is why the adjective has to carry it",
          (c, d))
    # ARM 3: different motif -> different noun pool.
    pools = [set(p) for p in sn.NOUNS]
    overlap = [(i, j) for i in range(len(pools)) for j in range(i + 1, len(pools))
               if pools[i] & pools[j]]
    check(not overlap, "different motif -> disjoint noun pool", overlap[:3])
    # The adjective stride cannot break arm 1, because the noun already differs.
    same = [(m, at) for m in range(sn.MOTIFS) for at in sn.ADJECTIVES
            if sn.name_for(m, at, 0) == sn.name_for(m, at, 1)]
    check(not same, "the adjective stride never collapses two ranks", same[:3])


def section_order():
    print("\n== 2. the answer does not depend on dict order ==")
    mapping = {}
    for i, sid in enumerate(range(100, 160)):
        mapping[sid] = (i % 40, sorted(sn.ADJECTIVES)[i % 6])
    first = sn.assign(mapping)
    shuffled = list(mapping.items())
    random.Random(7).shuffle(shuffled)
    check(list(dict(shuffled)) != list(mapping),
          "the shuffled mapping really is in a different order")
    second = sn.assign(dict(shuffled))
    check(first == second,
          "assign() gives the same answer under a shuffled input -- it sorts, "
          "and a version that walked the dict would pass today by luck",
          "%d names" % len(first))
    # The broken version, live, so this is a difference between two answers.
    def assign_unsorted(skills):
        groups = {}
        for sid in skills:                       # <-- no sorted()
            g, at = skills[sid]
            groups.setdefault((sn.motif_of(g), at), []).append(sid)
        out = {}
        for (m, at), members in groups.items():
            for j, sid in enumerate(members):
                out[sid] = sn.name_for(m, at, j)
        return out
    check(assign_unsorted(mapping) != assign_unsorted(dict(shuffled)),
          "and the unsorted version DOES differ -- the control that makes the "
          "check above mean something")


# --------------------------------------------------------------------------
# 3. the refusals


def section_refusals():
    print("\n== 3. the guard can fire ==")
    try:
        sn.name_for(0, 32, sn.POOL)
        check(False, "a rank at POOL is refused")
    except sn.Collision as exc:
        check("wrapping" in str(exc),
              "a rank at POOL is refused and the message says why", str(exc)[:60])
    # A group one past the pool, through assign(), which is how it would happen.
    big = {1000 + i: (0, 32) for i in range(sn.POOL + 1)}
    try:
        sn.assign(big)
        check(False, "a group of POOL+1 is refused")
    except sn.Collision:
        check(True, "a group of POOL+1 is refused rather than wrapped",
              sn.POOL + 1)
    # ...and one exactly AT the pool is allowed. A guard that refuses everything
    # protects nothing, because the generator then never runs.
    ok = {1000 + i: (0, 32) for i in range(sn.POOL)}
    got = sn.assign(ok)
    check(len(got) == sn.POOL and len(set(got.values())) == sn.POOL,
          "a group of exactly POOL is allowed and distinct -- the positive "
          "control", sn.POOL)
    # A duplicate reaching the end must be caught, not returned. Forcing one is
    # harder than it looks, and the first attempt here FAILED for a reason worth
    # keeping: duplicating pool 1 onto pool 0 is not enough, because the adjective
    # is strided by the motif, so motifs 0 and 1 still differ in their first word.
    # The stride therefore carries a uniqueness guarantee this file does not claim
    # -- and the motifs it does NOT separate are the ones POOL apart, where
    # (j + motif) % len(pool) wraps to the same index. So the sabotage has to be
    # aimed at 0 and POOL, which is also the pair a real vocabulary edit would
    # most easily break.
    check(sn.MOTIFS > sn.POOL,
          "there ARE two motifs POOL apart -- otherwise the collision below is "
          "unreachable and the check that follows would be vacuous",
          (sn.MOTIFS, sn.POOL))
    stash = sn.NOUNS
    try:
        sn.NOUNS = stash[:sn.POOL] + (stash[0],) + stash[sn.POOL + 1:]
        pair = {1: (0, 32), 2: (sn.POOL, 32)}
        check(sn.name_for(0, 32, 0) == sn.name_for(sn.POOL, 32, 0),
              "the sabotaged vocabulary really does produce one name twice",
              sn.name_for(0, 32, 0))
        try:
            sn.assign(pair)
            check(False, "a duplicate name is refused by assign()")
        except sn.Collision as exc:
            check("duplicate" in str(exc),
                  "assign() catches a duplicate the pools let through -- the "
                  "last line of defence, and the only one that sees a bad "
                  "VOCABULARY rather than a bad index", str(exc)[:60])
    finally:
        sn.NOUNS = stash


# --------------------------------------------------------------------------
# 4. the coupling to glyphs.py


def section_coupling():
    print("\n== 4. the modulo is against glyphs.py's own constant ==")
    check(sn.MOTIFS == glyphs.MOTIFS,
          "skillnames.MOTIFS equals glyphs.MOTIFS -- a bare %% by the wrong "
          "constant names every skill after the wrong shape",
          (sn.MOTIFS, glyphs.MOTIFS))
    check(sn.motif_of(None) is None, "motif_of passes None through")
    check(sn.motif_of(glyphs.COUNT - 1) == (glyphs.COUNT - 1) % glyphs.MOTIFS,
          "and agrees with glyphs' own i %% MOTIFS on the last index",
          sn.motif_of(glyphs.COUNT - 1))
    # The names describe glyphs.py's motif ORDER, so pin the order rather than
    # trusting the comments. _MOTIFS is a tuple of functions named _m_<shape>.
    shapes = [f.__name__.replace("_m_", "") for f in glyphs._MOTIFS]
    check(len(shapes) == sn.MOTIFS, "glyphs exposes %d motif functions" % sn.MOTIFS,
          len(shapes))
    # Each motif's FIRST noun should be recognisably its shape. Checked for the
    # ones where the shape word IS the noun; the rest are synonyms by design.
    exact = [(s, sn.NOUNS[i][0]) for i, s in enumerate(shapes)
             if s.capitalize() == sn.NOUNS[i][0]]
    check(len(exact) >= 15,
          "at least 15 of 22 motifs lead with their own shape word, so the "
          "pools are aligned to the ORDER and not merely the right length",
          "%d of %d: %s" % (len(exact), len(shapes), [e[1] for e in exact[:5]]))
    # The control: shift the pools by one and the agreement collapses.
    shifted = [(s, sn.NOUNS[(i + 1) % sn.MOTIFS][0])
               for i, s in enumerate(shapes) if s.capitalize()
               == sn.NOUNS[(i + 1) % sn.MOTIFS][0]]
    check(len(shifted) < len(exact),
          "and a one-motif shift collapses it -- the control", len(shifted))


# --------------------------------------------------------------------------
# 5. the real roster


def section_roster():
    print("\n== 5. the real roster, against the client and the armed archive ==")
    try:
        exe = vaultpath.vault_path("run", "reskin-roster", "Gw.exe")
        dat = vaultpath.vault_path("run", "reskin-roster", "Gw.dat")
    except SystemExit:
        exe = dat = None
    if not (exe and dat and os.path.exists(str(exe)) and os.path.exists(str(dat))):
        LEDGER.skip("section 5: no vault",
                    "the roster, the agreement with the icons, and the "
                    "armable-order reproduction all need the real artifacts")
        return
    import iconset                                               # noqa: E402
    mapping = iconset.skill_glyphs(PROFESSION, str(exe), str(dat))
    named = sn.assign(mapping)
    check(len(named) == 188, "profession 8 names 188 skills", len(named))
    check(len(set(named.values())) == len(named),
          "and all of them are distinct", len(set(named.values())))
    groups = {}
    for g, at in mapping.values():
        groups[(sn.motif_of(g), at)] = groups.get((sn.motif_of(g), at), 0) + 1
    worst = max(groups.values())
    check(worst == sn.MEASURED_WORST_GROUP,
          "the measured worst group is still what the module claims -- if this "
          "reddens, MEASURED_WORST_GROUP is stale and POOL may no longer clear it",
          "%d vs %d" % (worst, sn.MEASURED_WORST_GROUP))
    check(worst <= sn.POOL, "and it fits inside POOL", (worst, sn.POOL))

    # THE AGREEMENT CHECK. Every glyphed skill's noun must come from the motif of
    # the glyph iconset would arm for it. This is what `"Skill %d" % sid` fails.
    wrong = []
    for sid, (g, _at) in mapping.items():
        m = sn.motif_of(g)
        noun = named[sid].split()[-1]
        pool = sn.UNGLYPHED if m is None else sn.NOUNS[m]
        if noun not in pool:
            wrong.append((sid, m, noun))
    check(not wrong,
          "every skill's noun comes from the motif of the icon it draws -- the "
          "claim a uniqueness check cannot see", wrong[:3])
    # ...and the same check against a DIFFERENT motif must fail, or it is vacuous.
    misfit = 0
    for sid, (g, _at) in mapping.items():
        m = sn.motif_of(g)
        if m is None:
            continue
        if named[sid].split()[-1] not in sn.NOUNS[(m + 1) % sn.MOTIFS]:
            misfit += 1
    check(misfit == sum(1 for g, _ in mapping.values() if g is not None),
          "and NO glyphed skill's noun belongs to the neighbouring motif -- the "
          "control that stops the check above passing vacuously", misfit)

    unglyphed = [s for s, (g, _) in mapping.items() if g is None]
    check(len(unglyphed) == 12,
          "12 skills draw a shared icon we did not arm", len(unglyphed))
    check(all(named[s].split()[-1] in sn.UNGLYPHED for s in unglyphed),
          "and every one of them is named from UNGLYPHED, so its name does not "
          "claim to describe a picture of ours")

    # THE EXTRACTION. `skill_glyphs` and `--arm` must walk the same list, or a
    # skill gets a name describing a picture it does not draw. Rebuild the
    # positions the way main() does and require them to agree.
    from gwpe import PE                                          # noqa: E402
    pe = PE(str(exe))
    _mine, _users, _skills, rows, _skipped = iconset.armable(
        pe, str(dat), PROFESSION, False)
    walk = {fid: k for k, (fid, _r, _h) in enumerate(rows)}
    import repoint_skill                                         # noqa: E402
    table, count, _sec = repoint_skill.find_table(pe)
    agree = 0
    for sid, (g, _at) in mapping.items():
        fid = repoint_skill.row_values(pe.data, table, sid)["icon2"]
        if walk.get(fid) == g:
            agree += 1
    check(agree == len(mapping),
          "skill_glyphs agrees with the list --arm enumerates, for every skill",
          "%d of %d" % (agree, len(mapping)))
    _mine2, _u2, _s2, rows2, _sk2 = iconset.armable(pe, str(dat), PROFESSION, True)
    check(len(rows2) > len(rows),
          "--allow-shared really does lengthen that list, so the check above is "
          "not comparing two copies of the same trivial thing",
          "%d vs %d" % (len(rows2), len(rows)))

    payload = 2 * sum(len(v) for v in named.values())
    print("   name payload: %d UTF-16 bytes over %d names (median %d chars)"
          % (payload, len(named),
             sorted(len(v) for v in named.values())[len(named) // 2]))


def main():
    print("=" * 70)
    print("AUTHORED SKILL NAMES -- 188 of them, and the arithmetic that "
          "keeps them apart")
    print("=" * 70)
    for fn in (section_vocabulary, section_structure, section_order,
               section_refusals, section_coupling, section_roster):
        guarded(fn)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
