"""Skill damage: the client's own numbers, at the player's own rank.

Step 8 of studies/combat/PLAN.md. What it replaced was
`ENEMY_SKILL_FRACTION = 0.25` -- a flat quarter of the player's maximum for
every skill on the bar, admitted invention -- with the skill's own scale
endpoints interpolated by the client's own formula.

THE PART THAT MATTERS MOST HERE IS THE PART THAT REFUSES. The client's table
gives a magnitude and does NOT say what it means: `scale0/scale15` is
"+ Damage" on Power Attack and "Healing" on Restore Condition, and `type_code`
does not discriminate (a Spell can heal or harm). Three of the four skills on
our own enemy's bar are not damage. So a decode that read endpoints and dealt
them would have had the enemy "damaging" the player with a heal for 10-70 and
an enchantment for 40-200 -- an invention wearing a measurement's clothes, and
worse than the flat fraction it replaced because it would look principled.

The meaning therefore comes from GWW's own `{{Skill progression}}` variable
names, quoted verbatim into content/world.toml with a citation per skill, and
the server models only the labels it names in SCALE_MEANS_DAMAGE. Section 3 is
the one that would catch a regression there.

Section 5 pins the rounding tie-break, which is UNRESOLVED in the client
(studies/combat 8c: its CRT helper adjusts by +/-1.0, not the textbook +/-0.5,
and half-up vs half-even was not settled). We chose half-up. That choice cannot
currently bite, and this file proves it rather than assuming it: no skill the
server resolves lands on a .5 at any rank 0..15.
"""

import collections
import contextlib
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import checks  # noqa: E402
import effects  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR 25, counted from a green run on 2026-08-15 rather than guessed -- and
# the guard caught the guess: this said 26 first and the run reported
# "ONLY 25 OF A DECLARED FLOOR OF 26 CHECKS RAN". 4 endpoints (S1) + 3 shape
# (S2) + 8 meaning (S3: 3 modelled, 5 refused) + 4 bitfield (S4) + 1 tie-break
# (S5) + 3 rank chain (S6) + 2 wire (S7). Nothing here is conditional: every
# section reads content rows that ship in the repo plus the vault overlay, so
# a short run means a section stopped rather than passed.
# SKILLS-HN +4 (44), SKILLS-FA +13 (57: 7 model + 6 corpus), each from its
# green run. Section 12 needs the live corpus and declares a skip without it.
# THE BARE MACHINE (2026-10-07): the floor is decided on DIRECTORIES -- vault/content
# and vault/captures/live -- never on what loaded, so a vault whose skills.toml did not
# load still owes the full count and goes red. Each number is a green run's banner,
# MEASURED 2026-10-07 in the zealous-cannon tree, never computed:
#   FLOOR_VAULT 136 on the owner's vault, no skips = 2026-09-29's 135 + section 15 (the
#     carried rows against the vault's). The single floor it replaces, 97, was a stale
#     core: everything past it was vault-only and nothing said which.
#   FLOOR_VAULT_NO_CORPUS 94 on a scratch vault holding a copy of the owner's
#     vault/content and no captures/live: 136 less sections 12-13's 42, one declared skip.
#     The corpus is all or nothing on its DIRECTORY -- a missing tape FAILS by name, it
#     never skips -- so its count cannot drift with which tapes exist.
#   FLOOR_BARE 76 with RURIK_VAULT at an empty directory and at a nonexistent path
#     alike: sections 2-4 and 6-11d on the carried rows, five declared skips (1: 4
#     checks, 5: 1, 12-13: 42, 14: 12, 15: 1).
FLOOR_VAULT = 136
FLOOR_VAULT_NO_CORPUS = 94
FLOOR_BARE = 76
HAVE_VAULT_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE_CORPUS = os.path.isdir(vaultpath.vault_path("captures", "live"))
LEDGER = checks.Ledger("skill damage", floor=(
    FLOOR_BARE if not HAVE_VAULT_CONTENT
    else FLOOR_VAULT if HAVE_LIVE_CORPUS else FLOOR_VAULT_NO_CORPUS))
# The floor's history before 2026-10-07, when it was one number, 97: 2026-09-29 CASTAI-Z2 (the z2-sdmg lane) +16, all vault-only (sec.12: the pin exact under the payoff / converted classes with P3's swing pairs, the second Zaishen tape's census exact with the 16 unbacked rows, the Zealot's Fire finding, the classify=False arm, the wire's [10]-naming census; the round-2 review's four: the announce-order arm, the arbitrary-value injection arm, the converted and payoff signatures on synthetic batches through events(); the round-3 review's four: the sibling class pinned with its twelve value singletons, the Fighter's census with its whole-point reading, the sibling-bound arm (ARM 4), the wire-order read's re-keyed rows at the pin; the round-4 review's one: the flagged sibling counted at P2's floor, ARM 4 (iv); sec.12c: G4 exact on the tape with G4r and the whole-corpus signature, the removal-by-time arm): MEASURED, a vault run gives 135 (was 119, 6 red; 126 after round 1; 130 after round 2; 134 after round 3); floor unchanged -- a bare run still dies at section 1; 2026-09-28 the regenerate-from-38888 arc (c38-tab) +2, both vault-only (sec.12c: G3r with the 38797 known-bad arm; hexjoin's per-build table against every vault skills row): MEASURED, a vault run gives 119 on the 38797 vault and on the 38888 one; floor unchanged; 2026-09-28 CASTAI-Z1 (the z1-spell lane) +8, all vault-only (sec.12: the gapped connection set aside by name, the Zaishen tape's five multi-valued Mind Burn pairs exact; sec.12c: the set-aside, the whole corpus's FAILED set with the re-statements, I1 / M1, I2 / I3 / G2, G3 / C2c exact on the Zaishen tape, the confirming arm on the whole corpus): MEASURED, a vault run gives 117 (was 109, 4 red); floor unchanged -- a bare run dies at section 1 on the missing skills row 312 in the castai-z1 base tree exactly as here; 2026-09-27 the D6 review's repair +5 (sec.11c: the death batch order re-pinned, the payoff killing its own wearer (M5), the payoff killing the adjacent foe (M6), a second 179 arming no second payoff (R34-4); sec.11d: the dead target (R34-2); sec.12c rewritten per tape with the confirming-copy arm (EV-3, +1 there and the two exact pins re-scored on the witness)): MEASURED from the green run, 109 checks with the overlay = 104 + 5, floor 92 -> 97; 2026-09-27 SKILLS-HX +18 (sec.11c Incendiary Bonds 9, sec.11d Mind Burn 6, sec.12c the hexjoin lock 3): MEASURED from the green run, 104 checks with the overlay = 86 + 18, floor 74 -> 92; 2026-09-23 SKILLS-OB +6 (sec.11b: whose connection it is, four bare; sec.12: the JARIN player, the pair onto it); 2026-09-23 SKILLS-LT +1 (sec.3: Hamstring inflicts through the bonus slot); 2026-09-17 SKILLS-LR +4 (the location roll: three unit, one corpus); 2026-09-16 RUN-SKILLS-RB +2 (section 13, the converted word); 2026-09-16 SLICE-F47 +1 (the penalty split in whole points); 2026-09-14 HEAL-INT +1, ZEROWORD +1;   # MANTID-S +1: the player-side control beside the foe-side refusal
check = LEDGER.ok

# vault/content/skill_labels.toml's label-tier row count per build its header declares,
# MEASURED from each generated file (skilldesc.py --emit-labels): 38797 the table until
# 2026-09-28, 38888 its regeneration (831's row drops out); 38974 the regeneration of
# 2026-10-01, 55 rows MEASURED from its emit and identical by value to 38888's. Section
# 14 FAILS on any other build rather than passing a table nobody measured.
LABEL_ROWS_BY_BUILD = {38797: 56, 38888: 55, 38974: 55}


def _record(activation, aftercast, recharge, energy, attribute, profession, type_code,
            target, skill_arguments, scale, duration=(0, 0), bonus_scale=(0, 0),
            adrenaline=(0, 0), weapon_req=0, aoe_range=0.0, projectile=2077,
            impact_visual=2077, touch_range=False):
    return {"activation": activation, "aftercast": aftercast, "recharge": recharge,
            "energy": energy, "adrenaline": adrenaline[0],
            "adrenaline_units": adrenaline[1], "attribute": attribute,
            "profession": profession, "type_code": type_code, "target": target,
            "combo": 0, "combo_req": 0, "weapon_req": weapon_req, "aoe_range": aoe_range,
            "skill_arguments": skill_arguments, "duration0": duration[0],
            "duration15": duration[1], "scale0": scale[0], "scale15": scale[1],
            "bonus_scale0": bonus_scale[0], "bonus_scale15": bonus_scale[1],
            "projectile": projectile, "impact_visual": impact_visual,
            "touch_range": touch_range, "half_range": False}


# THE BARE MACHINE (2026-10-07). With RURIK_VAULT at an empty directory or at a
# nonexistent path this file reached no verdict: section 1's first read,
# `skill_scale_value(312, 0)`, raised ContentError (the reader's documented contract
# on a rowless skill -- callers catch it), because the skills table is the vault's and
# the tracked content carries 14 skills rows, none of these. No bare red here was a
# server defect. Two kinds of section, two fixes:
#   * a section whose SUBJECT is the vault -- section 1 (the extractor's endpoints
#     against GWW's), section 5 (every skill in the effect table), sections 12-13 (the
#     live corpus), section 14 (the label tier) and section 15 (RECORD against the
#     vault) -- reads the vault's own tables and declares a skip, decided on the
#     DIRECTORY (vaultpath.require_dir) and never on a missing row or an empty result;
#   * a section whose subject is the SERVER's behaviour on a few skills -- 2-4 and
#     6-11d -- runs on the rows below plus the tracked ones a bare machine has,
#     which together REPLACE the skills table for those sections (`carried`), so a
#     vault run takes exactly the bare path and cannot pass on a row a bare machine
#     lacks.
# The rows are skilltable.py's record as vault/content/skills.toml holds it, build
# 38974 (measured numbers -- CLAUDE.md's gate), copied 2026-10-07; 312 / 317 / 322 /
# 135 equal test_guards' copies of the same build. The ids are the ones these
# sections were MEASURED reading off the vault's table on a vaulted run (a logging
# table under the whole file): the default bar 316-323 (sections 7 / 11, through
# bar_holds_adrenal), Healing Signet 1, Faintheartedness 135, Incendiary Bonds 179,
# Mind Burn 185, Flare 194, Scourge Sacrifice 253 and Holy Strike 312. Section 15 holds
# every one to the vault's loaded row, column for column, both ways. MEASURED with a
# scratch mutant per row (RECORD less that row, the owner's vault): dropping any of 1,
# 179, 185, 194, 253, 312, 317, 319, 320, 322 or 323 reddens the VAULT run (a FAIL or a
# crash on the missing row); dropping 135, 316, 318 or 321 does not. Those four stay on
# purpose: 135 is what makes sections 9 / 10's controls controls (Faintheartedness's
# live bonus slot whose label is no condition -- rowless, both pass vacuously), and
# 316 / 318 / 321 keep the bar the server walks the real one (317 alone is what arms it).
# The attribute tables are NOT carried (test_guards' call, the same day): sections 7
# and 9 reach attribute_state through hit_enemy, which on a bare machine refuses ("no
# attribute cost rows") and its callers catch -- Critical Strikes reads 0, the weapon's
# mastery None -- and no check here reads a value that moves with them: the green bare
# run is what measured that. Section 6's ranks are the player row's (tracked). Nothing
# else a carried section reads differs between a bare load and the vault's, row for
# row (the same logging run), bar the label tier's rows inside the skill_effect scans,
# none of them a skill these sections name.
RECORD_BUILD = 38974
RECORD = {
    "1": _record(2.0, 0.75, 4, 0, 21, 1, 7, 0, 2, (82, 172)),   # Healing Signet, section 8's heal
    "135": _record(1.0, 0.75, 8, 10, 7, 4, 4, 5, 5, (50, 50), duration=(4, 18),
                   bonus_scale=(1, 3)),   # Faintheartedness, sections 9 / 10's hex
    "179": _record(1.0, 0.75, 7, 10, 10, 6, 4, 5, 6, (20, 80), duration=(3, 3),
                   bonus_scale=(1, 3), aoe_range=240.0),   # Incendiary Bonds, section 11c
    "185": _record(1.0, 0.75, 5, 5, 10, 6, 5, 5, 6, (15, 60), bonus_scale=(1, 10),
                   aoe_range=156.0),   # Mind Burn, section 11d
    "194": _record(1.0, 0.75, 0, 5, 10, 6, 5, 5, 2, (20, 65), bonus_scale=(1800, 1800),
                   aoe_range=156.0, projectile=343, impact_visual=344),   # Flare, sections 9 / 11
    "253": _record(1.0, 0.75, 5, 5, 14, 3, 4, 5, 1, (100, 100), duration=(8, 20),
                   aoe_range=156.0, impact_visual=463),   # Scourge Sacrifice, section 4
    "312": _record(0.75, 0.75, 8, 5, 14, 3, 10, 5, 6, (10, 55), bonus_scale=(10, 55),
                   touch_range=True),   # Holy Strike, sections 2 / 3 / 6 / 11
    "316": _record(0.0, 0.0, 10, 5, 21, 1, 15, 0, 7, (10, 60), duration=(10, 20),
                   bonus_scale=(1, 6), aoe_range=1000.0),   # the default bar, slot 1
    "317": _record(0.0, 0.0, 0, 0, 17, 1, 3, 0, 1, (33, 33), duration=(5, 20),
                   adrenaline=(4, 80)),   # Battle Rage, section 4; ARMS the default bar
    "318": _record(0.0, 0.0, 0, 0, 17, 1, 16, 0, 7, (90, 300), duration=(20, 20),
                   bonus_scale=(1, 10), adrenaline=(5, 120), aoe_range=20.0),   # Defy Pain, the bar
    "319": _record(0.0, 0.0, 0, 0, 17, 1, 3, 0, 1, (25, 25), duration=(8, 20),
                   adrenaline=(4, 80)),   # Rush, section 4's disabled set
    "320": _record(0.0, 0.0, 10, 5, 20, 1, 14, 5, 4, (0, 0), bonus_scale=(3, 15),
                   weapon_req=128),   # Hamstring, section 3's bonus-slot Crippled
    "321": _record(0.0, 0.0, 8, 5, 51, 1, 14, 5, 0, (0, 0), weapon_req=185),   # the bar, slot 6
    "322": _record(0.0, 0.0, 3, 5, 17, 1, 14, 5, 2, (10, 40),
                   weapon_req=185),   # Power Attack, sections 3 / 6 / 9
    "323": _record(0.0, 0.0, 7, 5, 21, 1, 14, 5, 2, (10, 40), duration=(2, 2),
                   weapon_req=185),   # Desperation Blow, sections 3 / 6
}


@contextlib.contextmanager
def _tables(**replace):
    """WORLD's tables REPLACED by these for the block, then put back."""
    import agents
    tables = agents.WORLD.tables
    kept = {k: tables[k] for k in replace if k in tables}
    tables.update(replace)
    try:
        yield
    finally:
        for k in replace:
            if k in kept:
                tables[k] = kept[k]
            else:
                del tables[k]


_TRACKED = []


def carried():
    """The skills table as a BARE machine holds it -- the tracked rows alone
    (content/overrides/, `content.load(vault_dir="")`) -- plus RECORD's, for the
    sections that read them. The tracked rows win a shared id, as they win the vault's
    in content.load's merge order. They have to be here: section 10's Sever Artery 382
    is a tracked row, and the first cut, RECORD alone, took it away and reddened 10."""
    if not _TRACKED:
        import agents
        _TRACKED.append(agents.content.load(vault_dir="", extra_dirs=[]).rows("skills"))
    table = {k: dict(v) for k, v in RECORD.items()}
    table.update(_TRACKED[0])
    return _tables(skills=table)


def main():
    with contextlib.ExitStack() as carry:
        _sections(carry)
    section_label_tier()
    section_record_rows()
    return LEDGER.verdict()


def _sections(carry):
    """Sections 1-13. `carry` holds `carried()` around 2-4 and 6-11d and nothing
    around 1, 5 and the corpus, which read the vault's own tables."""
    import agents
    import authsrv

    print("1. the endpoints are the client's, exactly, at rank 0 and rank 15")
    # Both endpoints must reproduce or the interpolation is not the client's.
    # These four pairs are also the ones GWW independently lists, so a match is
    # two witnesses rather than our decoder agreeing with itself.
    # THE BARE MACHINE (2026-10-07): the SUBJECT is the vault's table -- the extractor's
    # numbers -- so this reads the loaded table, never RECORD (a carried row checked
    # against the literal it was copied beside is no witness), and skips on an absent
    # vault/content DIRECTORY. With the directory there and a row absent the check FAILS
    # naming the miss: the reader raises ContentError on a rowless skill, its contract.
    try:
        vaultpath.require_dir("content", why="section 1: the endpoints in the vault's "
                                             "skills table")
    except SystemExit as exc:
        LEDGER.skip("1. the endpoints in the vault's skills table (4 checks)",
                    str(exc).splitlines()[0])
    else:
        for skill_id, lo, hi, name in ((312, 10, 55, "Holy Strike"),
                                       (322, 10, 40, "Power Attack"),
                                       (323, 10, 40, "Desperation Blow"),
                                       (276, 10, 70, "Restore Condition")):
            try:
                got0 = authsrv.skill_scale_value(skill_id, 0)
                got15 = authsrv.skill_scale_value(skill_id, 15)
            except agents.content.ContentError as exc:
                got0 = got15 = f"NO ROW ({str(exc).split('. Known:')[0]})"
            check(got0 == lo and got15 == hi,
                  f"{name} ({skill_id}) scales {lo} -> {hi}",
                  f"rank 0 = {got0}, rank 15 = {got15}")

    # Sections 2-4 are the SERVER's behaviour on a handful of skills: RECORD's rows.
    carry.enter_context(carried())

    print("\n2. the shape between them is the client's formula")
    # value(rank) = max(0, round(lo + (hi-lo)*rank/15.0)), measured at
    # 0x005A8920 with the divisor a literal double 15.0 (studies/combat 8c).
    # Holy Strike's span is 45 over 15, so every rank is an exact integer and
    # the whole ladder is checkable without touching the tie-break.
    ladder = [authsrv.skill_scale_value(312, r) for r in range(16)]
    check(ladder == [10 + 3 * r for r in range(16)],
          "Holy Strike walks 10, 13, 16 ... 55 -- 3 per rank, exactly",
          f"{ladder}")
    # NO UPPER CLAMP: the client's interpolator never compares rank against 15,
    # so ranks above it extrapolate. Measured, and worth pinning because a
    # "sensible" clamp is exactly what someone would add.
    check(authsrv.skill_scale_value(312, 20) == 70,
          "and rank 20 EXTRAPOLATES to 70 rather than saturating at 55",
          "the interpolator has no upper bound on rank -- ranks above 15 are "
          "reachable in retail with runes and headgear")
    check(authsrv.skill_scale_value(312, 0) >= 0,
          "the floor at zero is ArenaNet's own assert, ConstSkill:3769")

    print("\n3. what a scale MEANS is sourced, and non-damage is refused")
    # The three the server models...
    for skill_id, mode, name in ((312, "standalone", "Holy Strike"),
                                 (322, "additive", "Power Attack"),
                                 (323, "additive", "Desperation Blow")):
        got = authsrv.skill_damage(skill_id, 15)
        check(got is not None and got[1] == mode,
              f"{name} is a {mode} damage skill",
              f"{got} -- GWW calls its progression var "
              f"{agents.WORLD.get('skill_effect', str(skill_id))['scale_means']!r}")
    # ...and the ones it must NOT, which is the whole point.
    for skill_id, means, name in ((276, "Healing", "Restore Condition"),
                                  (289, "+ Maximum health", "Vital Blessing"),
                                  (318, "+ Maximum health", "Defy Pain")):
        row = agents.WORLD.get("skill_effect", str(skill_id))
        check(authsrv.skill_damage(skill_id, 15) is None
              and row["scale_means"] == means,
              f"{name} deals NO damage -- its scale is {means!r}",
              "returning None rather than 0, so a caller must decide what an "
              "unmodelled skill means instead of silently dealing nothing")
    # SKILLS-LT (2026-09-23, studies/skills 54.5 / 55): the two `scale_means =
    # "Duration"` labels were INERT -- nothing compares a means against
    # "Duration"; an episode's duration is the skills table's -- and skilldesc
    # refereed Battle Rage's a CONFLICT (its flat 33 is the movement speed).
    # Both rows keep their wiki provenance and carry no label.
    for skill_id, name in ((253, "Scourge Sacrifice"), (317, "Battle Rage")):
        row = agents.WORLD.get("skill_effect", str(skill_id))
        check(authsrv.skill_damage(skill_id, 15) is None
              and "scale_means" not in row and "bonus_scale_means" not in row,
              f"{name} deals NO damage and its row carries no label at all -- "
              f"the inert 'Duration' is gone", dict(row))
    # And Hamstring's label moved to the slot the client numbers: args = 4
    # (bonus only), Crippled 3..15 in the BONUS slot, %str2% in the template.
    # Under "Crippled duration" on `scale_means` the server inflicted nothing.
    row = agents.WORLD.get("skill_effect", "320")
    check(authsrv.skill_damage(320, 15) is None and "scale_means" not in row
          and row.get("bonus_scale_means") == "Crippled"
          and authsrv.skill_condition(320, 0) == (481, 3.0)
          and authsrv.skill_condition(320, 15) == (481, 15.0),
          "Hamstring deals NO damage; its Crippled rides the BONUS slot, 3 s at "
          "rank 0 and 15 s at rank 15 (481 = Crippled)",
          (dict(row), authsrv.skill_condition(320, 0), authsrv.skill_condition(320, 15)))

    print("\n4. a disabled set is refused, not read")
    # Rush's scale slot holds 25 -- the "move 25% faster" in its description --
    # with its scale bit CLEAR. Reading endpoints without honouring
    # skill_arguments invents a progression the game never draws.
    for skill_id, name in ((319, "Rush"), (317, "Battle Rage"),
                           (253, "Scourge Sacrifice")):
        raised = False
        try:
            authsrv.skill_scale_value(skill_id, 10)
        except ValueError:
            raised = True
        check(raised, f"{name}'s scale set is disabled and REFUSES")
    check(agents.WORLD.get("skills", "319")["scale0"] == 25,
          "and Rush's slot really does hold 25 -- a constant, not a floor",
          "which is what makes it the discriminator: a decode ignoring the "
          "bitfield returns a plausible 25 here instead of refusing")

    # Section 5's SUBJECT is every skill the server can resolve -- the vault's whole
    # table, not RECORD's fifteen -- so the vault's own rows are put back for it.
    carry.close()

    print("\n5. the unresolved tie-break cannot bite what we ship")
    # studies/combat 8c left half-up vs half-even open. Prove it is moot for
    # every skill the server can resolve, rather than assuming it.
    # THE BARE MACHINE (2026-10-07): skipped on an absent vault/content DIRECTORY.
    try:
        vaultpath.require_dir("content", why="section 5: every skill in the effect "
                                             "table, against the vault's skills table")
    except SystemExit as exc:
        LEDGER.skip("5. the tie-break over the vault's skills table (1 check)",
                    str(exc).splitlines()[0])
    else:
        ties = []
        for row_id in sorted(agents.WORLD.rows("skill_effect")):
            try:
                lo = int(agents.WORLD.get("skills", str(row_id))["scale0"])
                hi = int(agents.WORLD.get("skills", str(row_id))["scale15"])
            except Exception:                                      # noqa: BLE001
                continue
            for rank in range(16):
                exact = lo + (hi - lo) * rank / 15.0
                if abs(exact - int(exact) - 0.5) < 1e-9:
                    ties.append((row_id, rank, exact))
        check(not ties,
              "no skill in the effect table lands on a .5 at any rank 0..15",
              f"{ties} -- so half-up vs half-even changes nothing we send, and the "
              f"client's +/-1.0 CRT adjustment stays an open question that costs "
              f"us nothing today")

    # Sections 6-11d are the SERVER's behaviour again: RECORD's rows.
    carry.enter_context(carried())

    print("\n6. the player's rank drives the player's damage")
    # THE CHAIN STEP 7 AND STEP 8 EXIST TO JOIN: the skill record names its
    # attribute, the attribute is an s_attrib index, and the rank comes from
    # the same content row 0x003A is built from. Before this, `2 * rank` was 0.
    # SLICE-H7 (2026-09-13): the shipped ranks became a hammer warrior's --
    # Strength 9, Tactics 6 (Hammer Mastery 12). The two locks follow the
    # content row rather than a literal, so the claim they make -- the RANK is
    # what separates two identical tables -- survives the next re-spec too.
    _ranks = {int(a): int(r) for a, r in agents.WORLD.get("player", "attributes")["ranks"]}
    check(authsrv.player_rank_for_skill(322) == _ranks[17]
          and authsrv.player_rank_for_skill(323) == _ranks[21]
          and _ranks[17] != _ranks[21],
          f"Power Attack reads Strength ({_ranks[17]}), Desperation Blow reads "
          f"Tactics ({_ranks[21]})",
          "same scale endpoints, different attributes -- so the ranks are what "
          "separate them")
    pa = authsrv.skill_damage(322, authsrv.player_rank_for_skill(322))
    db = authsrv.skill_damage(323, authsrv.player_rank_for_skill(323))
    _want = lambda r: 10 + round(30 * r / 15)
    check(pa[0] == _want(_ranks[17]) and db[0] == _want(_ranks[21]),
          f"so Power Attack adds {_want(_ranks[17])} and Desperation Blow adds "
          f"{_want(_ranks[21])}",
          f"{pa} vs {db} -- identical 10->40 tables, apart because the ranks "
          f"differ. This is what 'the server models no attribute ranks' cost us")
    check(authsrv.player_rank_for_skill(312) == 0,
          "and a Warrior has rank 0 in Smiting Prayers -- correct, not missing",
          "Holy Strike is a Monk skill; the player has no rank in its attribute")

    print("\n7. the bonus reaches the wire as ONE damage number")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = {"name": "t", "dead": False, "last_hit": 0.0,
             "max_health": 1000.0, "health": 1000.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.hit_enemy(send, state, 10, 0, bonus_damage=34.0)
    dmg = [v for op, v, _l in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
           and v[0] == agents.PROP_DAMAGE]
    check(len(dmg) == 1,
          "a skill's '+ Damage' rides the swing as one message, not two",
          f"{len(dmg)} damage message(s) -- GWW writes Power Attack as "
          f"'+ Damage', a bonus on the attack it rides; two messages would "
          f"draw two numbers on screen for one swing")
    # RED FROM 2026-08-20 UNTIL THIS LINE CHANGED, and the reason is worth more
    # than the check. This used to read `base = 1000.0 * authsrv.HIT_FRACTION`
    # -- a flat 15% of the target's pool, which is what `hit_enemy` dealt when
    # this test was written. The weapon-damage arc replaced that with the
    # HAMMER'S OWN 3-5 range read off the item ArenaNet sends, so `HIT_FRACTION`
    # is now only the fallback for a swing with no weapon, and this check was
    # pinned to a constant the code it tests no longer reads. THE SAME DEFECT
    # WAS FOUND AND FIXED IN `test_guards` THE SAME DAY and this copy of it was
    # missed -- which is the argument for running the whole suite after a change
    # to a shared damage path, not the tests whose names sound related.
    #
    # A RANGE RATHER THAN A NUMBER, because the roll is real: `hit_enemy` draws
    # randint(3, 5) and nothing here seeds it. Asserting the range is what this
    # check is actually for -- that the bonus is added to the swing ONCE and
    # lands in the target's bookkeeping, not that the swing is any particular
    # number, which section 6 already pins from the other side.
    lo, hi = authsrv.PLAYER_SWING_DAMAGE
    dealt = 1000.0 - agent["health"]
    check(lo + 34.0 <= dealt <= hi + 34.0,
          f"and the bookkeeping is one swing ({lo}-{hi}) plus the bonus 34",
          f"health {agent['health']}, so {dealt:.0f} dealt against the "
          f"{lo + 34:.0f}-{hi + 34:.0f} this path can produce. The weapon's "
          f"range is the client's own tooltip number (identifier 584); the "
          f"roll inside it is ours")

    print("\n8. the OTHER two directions a cast can resolve (2026-08-20)")
    # HEALING, which this server had no way to express until the corpus was
    # asked which property carries it. agents.GV_HEALTH_GAIN holds the
    # measurement: on 0x00A3, property 16 is negative 1251 of 1251 and 17 is
    # negative 243 of 243, both self-directed 0 of 1501; property 55 is
    # POSITIVE 502 of 506 and SELF-DIRECTED 454 of 506.
    check(authsrv.skill_heal(1, 1) == 88,
          "Healing Signet heals 88 at Tactics 1, from GWW's `Heal` 82..172",
          f"{authsrv.skill_heal(1, 1)} -- the same interpolation the damage "
          f"side uses, on a label sourced per skill rather than guessed from "
          f"the type")
    check(authsrv.skill_damage(1, 1) is None,
          "and it deals no DAMAGE -- a heal is a direction, not a sign flip",
          "`Heal` is not in SCALE_MEANS_DAMAGE, so the damage path returns "
          "None rather than dealing 88 to the caster")
    check(authsrv.skill_heal(322, 12) is None,
          "CONTROL: Power Attack heals nothing",
          "its label is `+ Damage`; a heal that fired on every skill with a "
          "scale would pass the check above and fail this one")

    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"player_health": 40.0, "player_energy": 50.0, "agents": {}}
    landed = authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                authsrv.PLAYER_AGENT_ID, 88, 0)
    heals = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
             and v[0] == agents.GV_HEALTH_GAIN]
    check(len(heals) == 1 and heals[0][1] == heals[0][2],
          "the heal goes out SELF-DIRECTED, target == cause",
          f"{heals[0][:3] if heals else heals} -- which is the shape 454 of "
          f"retail's 506 property-55 events have, and 0 of its 1501 damage "
          f"events do")
    check(authsrv._f32_of(heals[0][3]) > 0,
          "and POSITIVE, where damage on the same channel is negative",
          f"{authsrv._f32_of(heals[0][3]):+.4f} -- `_damage_fraction` sends "
          f"-frac, which is retail's convention 1251 times over")
    check(landed == 60.0 and state["player_health"] == 100.0,
          "an 88 heal on a 40/100 bar lands 60 -- CLAMPED, not overflowed",
          f"landed {landed}, health {state['player_health']}. The client "
          f"asserts `fraction <= 1.0f` at CharPool.cpp:84 and that assert only "
          f"fires in the POSITIVE direction, so this is the first thing this "
          f"server sends that can actually reach it")
    # HEAL-INT (2026-09-14): a fractional heal goes out and lands as WHOLE
    # points, truncated -- retail's property-55 words are 83 of 85 exact over
    # the taker's maximum, the same shape as its damage. 70.4 (an 88 under a
    # Deep Wound's x0.8) is 70 on the wire (f32(0.70) = 0x3F333333) and 70 in
    # the books; nothing rounds it to 71.
    sent_i = []
    send_i = lambda op, vals, label="", quiet=False: sent_i.append((op, vals, label))
    state_i = {"player_health": 10.0, "player_energy": 50.0, "agents": {}}
    landed_i = authsrv.heal_agent(send_i, state_i, authsrv.PLAYER_AGENT_ID,
                                  authsrv.PLAYER_AGENT_ID, 70.4, 0)
    heals_i = [v for op, v, _l in sent_i
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] == agents.GV_HEALTH_GAIN]
    check(len(heals_i) == 1 and heals_i[0][3] == 0x3F333333
          and landed_i == 70.0 and state_i["player_health"] == 80.0,
          "a 70.4 heal is 70 on the wire (f32(0.70) = 0x3F333333) and 70 in the "
          "books -- whole points, truncated (HEAL-INT)",
          f"wire {[hex(v[3]) for v in heals_i]}, landed {landed_i}, health "
          f"{state_i['player_health']}")
    # SKILLS-HN (studies/skills 42). This check used to pin the OPPOSITE --
    # "a heal on a FULL bar sends nothing at all ... overheal is silent in
    # retail too, no green number appears" -- and both halves were a
    # reconstruction: retail sends property 55 onto full pools (healjoin.py
    # P4, 46 witnesses), and the number is blue, drawn from the 55 alone.
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 50, 0) == 0.0
          and len(sent) == before + 1
          and abs(authsrv._f32_of(sent[-1][1][3]) - 0.5) < 1e-6
          and state["player_health"] == 100.0,
          "a heal on a FULL bar still goes out, carrying the skill's own "
          "amount (0.5 of the pool), lands 0 and moves the book nowhere",
          f"sent {len(sent) - before}, fraction "
          f"{authsrv._f32_of(sent[-1][1][3]) if len(sent) > before else None}, "
          f"health {state['player_health']} -- WIKI (GWW 'Heal'): the blue "
          f"number 'is shown even when no health are actually gained'")
    state["player_health"] = 70.0
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 50, 0) == 30.0
          and abs(authsrv._f32_of(sent[-1][1][3]) - 0.5) < 1e-6
          and state["player_health"] == 100.0,
          "a PARTIAL overheal (50 onto 70/100) sends 0.5 -- the amount, not "
          "the 30 that landed -- and the book clamps at the pool",
          f"fraction {authsrv._f32_of(sent[-1][1][3])}, health "
          f"{state['player_health']} (RECONSTRUCTION for the partial case: "
          f"the corpus cannot see a pool, only that full ones get the amount)")
    state["player_health"] = 40.0
    before = len(sent)
    check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                             authsrv.PLAYER_AGENT_ID, 250, 0) == 60.0
          and abs(authsrv._f32_of(sent[-1][1][3]) - 1.0) < 1e-6,
          "a heal bigger than the whole pool is capped at 1.0 on the wire",
          "`_fraction` refuses above 1.0 (CharPool.cpp:84) and retail's "
          "largest 55 is 0.652, so this branch has no witness either way")
    state["player_health"] = 100.0
    authsrv.OVERHEAL_NUMBER = False
    try:
        before = len(sent)
        check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                 authsrv.PLAYER_AGENT_ID, 50, 0) == 0.0
              and len(sent) == before,
              "--no-overheal-number (the known-bad arm): a full bar sends "
              "nothing, as before 2026-09-09")
        state["player_health"] = 70.0
        check(authsrv.heal_agent(send, state, authsrv.PLAYER_AGENT_ID,
                                 authsrv.PLAYER_AGENT_ID, 50, 0) == 30.0
              and abs(authsrv._f32_of(sent[-1][1][3]) - 0.3) < 1e-6,
              "and the partial case shrinks the wire to what landed (0.3)")
    finally:
        authsrv.OVERHEAL_NUMBER = True
        state["player_health"] = 100.0

    print("\n9. a SPELL does not swing a hammer, and its damage is its own")
    # BOTH HALVES WERE WRONG UNTIL 2026-08-20 and the run is what showed it
    # (`20260820T185518`): casting Faintheartedness produced
    # `attack_started: player swings at 10` and 5 points of hammer damage, and
    # Flare -- whose own 20 fire damage was decoded and sitting right there --
    # dealt the same 5, because cast_tick read only the "additive" mode.
    check(authsrv._is_attack_skill(322) and not authsrv._is_attack_skill(194)
          and not authsrv._is_attack_skill(135),
          "the type column says which skills ride a weapon swing",
          "Power Attack is type 14 and Flare and Faintheartedness are not. "
          "All 199 attacks in the corpus carry target byte 5, which is the "
          "same column agreeing")
    check(authsrv.skill_damage(194, 0) == (20, "standalone"),
          "Flare's own damage is 20 at rank 0, mode `standalone`",
          "GWW var1 `Fire damage` 20..65, client scale 20..65")

    sent = []
    ag = {"name": "t", "dead": False, "last_hit": 0.0, "max_health": 100.0,
          "health": 100.0, "pos": (0.0, 0.0), "armor_rating": 3.0}
    state = {"agents": {10: ag}, "pos": (0.0, 0.0)}
    authsrv.hit_enemy(send, state, 10, 0, exact=20.0, swing=False,
                      label="skill 194")
    check(ag["health"] == 80.0,
          "`exact` deals exactly that much -- no roll, no armour, no critical",
          f"{ag['health']}/100. The weapon path would have rolled 3-5 and "
          f"scaled it; a spell's number is the skill's own")
    starts = [v for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
              and v[0] == agents.GV_ATTACK_STARTED]
    check(not starts and len(sent) == 1,
          "and it sends ONE message -- no attack_started, no melee_finished",
          f"{len(sent)} message(s). Those two name the beginning and end of a "
          f"SWING; a spell never began one")

    print("\n10. and a skill can inflict a CONDITION -- the join isle asked for")
    # studies/isle established that a condition's duration comes from the
    # INFLICTING skill (Burning's own endpoints are 3/3 and retail sends it at
    # 9.0). The other half was which condition and from where, and both are
    # per-skill data we already carry: GWW's variable NAMES it, the client's
    # bonus slot carries the seconds, and the bitfield picked the slot.
    got = authsrv.skill_condition(382, 3)
    check(got == (478, 9.0),
          "Sever Artery inflicts Bleeding (478) for 9 s at Swordsmanship 3",
          f"{got} -- GWW gives ONE variable, `Bleeding` 5..25, and the client "
          f"carries 5..25 in the BONUS slot with skill_arguments = 4. The "
          f"bitfield picked the slot before the wiki was read")
    check(effects.condition_id("Bleeding") == 478
          and effects.condition_id("Health degeneration") is None,
          "the label is the join key, and a non-condition label maps to None",
          "`Health degeneration` is a real progression variable (it is "
          "Faintheartedness's) and it is not a condition. Mapping it to the "
          "nearest one is exactly the guess this refuses")
    check(authsrv.skill_condition(135, 0) is None
          and authsrv.skill_condition(322, 12) is None,
          "CONTROL: a hex with a bonus slot and an attack with none inflict none",
          "Faintheartedness's bonus slot holds `Health degeneration` 0..3 with "
          "its bit SET -- a live slot whose label is not a condition, which is "
          "the case a label-blind reading would get wrong")

    sent = []
    state = {"agents": {10: dict(ag, health=100.0)}, "pos": (0.0, 0.0)}
    ep = authsrv.apply_condition(send, state, 10, 478, 9.0, 3, 0, 382)
    check(ep is not None and sent
          and not [1 for op, _v, _w in sent if op == effects.OP_EFFECT_APPLY]
          and (sent[0][0], sent[0][1]) == (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                                           [agents.PROP_AURA_ON, 10, 23])
          and sent[1][0] == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
          and state.get("effect_list_suppressed") == 1,
          "MANTID: on a FOE no 0x0042 goes out -- the visual [6, 10, 23] and the "
          "status word carry the condition (retail: 0 of 369 effect-list messages "
          "name anyone but the player; [6, T, 23] then 0x00F1 on the Reforged "
          "capture's three bleeding foes, 3 of 3 -- RANGERPRE-S13, test_condwords)",
          f"{[(hex(op), v) for op, v, _w in sent][:3]}")
    sent = []
    state = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0}
    authsrv.player_pools(state)
    ep = authsrv.apply_condition(send, state, authsrv.PLAYER_AGENT_ID, 478,
                                 9.0, 3, 0, 382)
    check(ep is not None and sent
          and sent[0][0] == effects.OP_EFFECT_APPLY
          and sent[0][1][1] == 478,
          "and on the PLAYER it goes out as an ordinary 0x0042 naming the "
          "CONDITION's id",
          f"{sent[0][1] if sent else sent} -- not the inflicting skill's. "
          f"That is what retail carries: the corpus's six condition applies "
          f"name 480 and 481, never the skill that caused them")

    print("\n11. an INCOMING fire spell respects the player's armour: ONE rating, "
          "ELEMENTAL, no location roll (SKILLS-FA)")
    # 39.5 named this the one real gap in the enemy's skill path and 39.6 left
    # it unbuilt because GWW is ambiguous about WHICH rating a spell scales
    # against. studies/skills 43 settled the shape on retail's wire
    # (spellhitjoin.py, section 12 below): one caster + one skill + one
    # target is one value, every pair. The unit checks here are the model;
    # the corpus check is the evidence.
    elem = [authsrv.player_armour_at(k, physical=False)
            for k, _w in authsrv.HIT_LOCATION_ODDS]
    phys = [authsrv.player_armour_at(k, physical=True)
            for k, _w in authsrv.HIT_LOCATION_ODDS]
    check(len(set(elem)) == 1 and elem[0] == 25.0 and len(set(phys)) == 1
          and phys[0] == 45.0,
          "the five pieces read 25 elemental and 45 physical, all alike",
          f"elemental {elem}, physical {phys} -- identifier 572 is the rating "
          f"and 527 the `+20 vs. physical` (content/items.toml). Alike, so a "
          f"single rating and a location roll are byte-identical on the wire "
          f"today; what this section pins is WHICH number reaches a spell")
    check(authsrv.player_spell_armour() == 25.0,
          "and a spell resolves against the ELEMENTAL 25, not the physical 45",
          f"{authsrv.player_spell_armour()} -- the `+20 vs. physical damage` "
          f"is a physical bonus; GWW's own worked example counts the "
          f"Elementalist's `+10 vs. Elemental` for nothing against an attack")
    check(authsrv.spell_armour_for(194) == 25.0
          and authsrv.spell_armour_for(312) is None
          and authsrv.spell_armour_for(322) is None,
          "Flare's `Fire damage` respects it; Holy Strike's `Holy damage` and "
          "Power Attack's `+ Damage` do not",
          f"194 -> {authsrv.spell_armour_for(194)}, 312 -> "
          f"{authsrv.spell_armour_for(312)}, 322 -> "
          f"{authsrv.spell_armour_for(322)}. WIKI (GWW, \"Damage\" sec. "
          f"Properties): holy and untyped skill damage ignore armour, and "
          f"`+<number>` rides an armour-respecting swing -- 39.2's rule, "
          f"keyed on the LABEL and never on \"is it a skill\"")

    # SKILLS-LR (2026-09-17, studies/skills 50): the spell ROLLS A LOCATION.
    # A lopsided set -- chest and legs on, head hands and feet bare, the
    # owner's RB2 body -- through the real `spell_armour_for`, with the roll
    # and the pieces pinned.
    cm = authsrv.combatmath
    saved_lr = (cm.player_armour_at, cm.roll_hit_location,
                authsrv.SPELL_LOCATION_ROLL)
    lopsided = {"warrior_body": 25.0, "warrior_legs": 25.0}
    try:
        cm.player_armour_at = lambda key, physical, *_a, **_k: lopsided.get(key)   # **_k: B4's cracked=
        cm.roll_hit_location = lambda: "warrior_head"
        bare = authsrv.spell_armour_for(194)
        cm.roll_hit_location = lambda: "warrior_body"
        chest = authsrv.spell_armour_for(194)
        authsrv.SPELL_LOCATION_ROLL = False
        cm.roll_hit_location = lambda: "warrior_head"
        legacy = authsrv.spell_armour_for(194)
    finally:
        (cm.player_armour_at, cm.roll_hit_location,
         authsrv.SPELL_LOCATION_ROLL) = saved_lr
    check(bare == 0.0 and chest == 25.0,
          "a spell rolls a hit location: a roll onto a BARE piece resolves "
          "against 0, a roll onto the chest against the chest's rating",
          f"head (bare) -> {bare}, chest -> {chest} -- OBSERVED on retail "
          f"(RUN-SKILLS-RB2): one Lightning Orb, 101 armoured and 286 bare")
    check(abs(authsrv.armour_multiplier(0.0) / authsrv.armour_multiplier(60.0)
              - 2 ** 1.5) < 1e-9,
          "and a bare piece against the 60 baseline is x2^(60/40) = 2.83 -- "
          "the tape's 286 / 101 = 2.832",
          f"{authsrv.armour_multiplier(0.0) / authsrv.armour_multiplier(60.0):.4f}")
    check(legacy == 25.0,
          "`--no-spell-location-roll` restores the chest's rating whatever "
          "the roll (the revert arm, REFUTED as a claim about retail)",
          f"roll=head, flag off -> {legacy}")

    # The cast itself, at rank 0 so Flare's 20 scales to 36.68 and does not
    # kill the 100-pool player (at rank 12 the 56 becomes 102.7, an overkill
    # the wire would carry as 1.0 -- the wiki's "below 60 takes MORE").
    def _cast(skill_id, **flags):
        saved = {k: getattr(authsrv, k) for k in flags}
        saved_rank = authsrv.ENEMY_SKILL_RANK
        out = []
        st = {"agents": {}, "pos": (0.0, 0.0)}
        ag = {"name": "t", "dead": False, "last_hit": 0.0, "max_health": 100.0,
              "health": 100.0, "pos": (0.0, 0.0), "casting": 0,
              "skills": ((skill_id, 1.0, 0.0),), "skill_ready": [0.0]}
        st["agents"][10] = ag
        try:
            for k, v in flags.items():
                setattr(authsrv, k, v)
            authsrv.ENEMY_SKILL_RANK = 0
            _send = lambda op, vals, label="", quiet=False: out.append((op, vals, label))   # noqa: E731
            authsrv.land_skill(_send, st, 10, ag, 0)
            # studies/weapons 37 (2026-09-20): a projectile spell's word rides
            # the flight -- Flare's 343 leaves at the completion and lands a
            # flight later, its terms computed THEN, under the same flags.
            for _shot in st.get("body_projectiles") or ():
                _shot["arrives_at"] -= 30.0
            authsrv.projectile_tick(_send, st, 0)
        finally:
            for k, v in saved.items():
                setattr(authsrv, k, v)
            authsrv.ENEMY_SKILL_RANK = saved_rank
        # The float rides the wire as its f32 bit pattern (v[3] is a dword).
        dmg = [struct.unpack("<f", struct.pack("<I", v[3] & 0xFFFFFFFF))[0]
               for op, v, _l in out
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] == agents.PROP_DAMAGE]
        return st, dmg

    mult = authsrv.armour_multiplier(25.0)          # 2^((60-25)/40) = 1.834
    st, dmg = _cast(194)
    # ZEROWORD (2026-09-14): the same Flare into a rating of 300 -- 2^((60-300)/40)
    # = 1/64, so 20 becomes 0.31 and truncates to nothing -- still sends its
    # damage word, as -0.0, and the pool does not move. Retail's -0.0 words
    # are the witness (F46.7). Not "fully converted": no conversion is open.
    st_z, dmg_z = _cast(194, spell_armour_for=lambda _sid, *_a: 300.0)   # *_a: B4's state
    check(len(dmg_z) == 1 and dmg_z[0] == 0.0 and math.copysign(1.0, dmg_z[0]) < 0
          and st_z["player_health"] == 100.0,
          "Flare grazing to nothing still sends [16, player, caster, -0.0] and "
          "takes nothing off the pool",
          f"damage words {dmg_z}, health {st_z['player_health']}")
    want = math.floor(20.0 * mult)   # DAMAGE-INT: 36.68 goes out as 36 (truncated)
    check(len(dmg) == 1 and abs(dmg[0] + want / 100.0) < 1e-5   # f32 on the wire
          and abs(st["player_health"] - (100.0 - want)) < 1e-6,
          f"Flare's 20 lands as {want} ({20.0 * mult:.2f} truncated to whole "
          f"points, DAMAGE-INT) against AR 25 -- the wiki's own "
          f"multiplier, 2^((60-25)/40) = {mult:.4f}",
          f"sent {dmg}, health {st['player_health']}. Below the 60 baseline "
          f"the player takes MORE than the stated amount, which is what GWW "
          f"says happens to an under-armoured target and what this server "
          f"used to get backwards by dealing the stated 20")
    st, dmg = _cast(194, SPELL_ARMOUR=False)
    check(len(dmg) == 1 and abs(dmg[0] + 0.20) < 1e-6,
          "`--no-spell-armour` restores the stated 20 (the revert arm)",
          f"sent {dmg}")
    st, dmg = _cast(194, ARMOUR_TERM=False)
    check(len(dmg) == 1 and abs(dmg[0] + 0.20) < 1e-6,
          "and so does `--no-armour-term`, the general control",
          f"sent {dmg} -- a session that drops the swing's armour maths "
          f"drops the spell's with it")
    st, dmg = _cast(312)
    check(len(dmg) == 1 and abs(dmg[0] + 0.10) < 1e-6,
          "CONTROL: Holy Strike's 10 at rank 0 is still exactly 10 with the "
          "term ON",
          f"sent {dmg} -- armour-ignoring by type, untouched by this default")

    print("\n11b. whose connection it is: spellhitjoin.observer_of (bare "
          "machine, studies/skills 43.8)")
    # The JARIN hero tape's shape (20260914T005758 conn 56011): the player 29
    # is the kind-5 create, the hero 30 the kind-9 one, both get property 41,
    # and the hero's 0x00E3 comes FIRST. The first-0x00E3 rule named 30; every
    # consumer's "own" split (interruptjoin, missjoin, rechargeprobe, this
    # file's section 12) was scored on it.
    import spellhitjoin
    E3, E2, P9F = 0x00E3, 0x00E2, 0x009F
    jarin = [(0, 1.0, 0x0020, [0x20, 29, 0, 0, 5]),
             (1, 1.1, 0x0020, [0x20, 30, 0, 0, 9]),
             (2, 1.2, P9F, [P9F, 41, 29, 1]), (3, 1.3, P9F, [P9F, 41, 30, 1]),
             (4, 2.0, E3, [E3, 30, 346, 0]),          # the hero's, first
             (5, 3.03, E3, [E3, 29, 392, 0]),         # answers the press at 3.0
             (6, 4.0, E3, [E3, 30, 322, 0]),
             (7, 5.04, E2, [E2, 29, 394, 0])]         # answers the press at 5.0
    presses = [(3.0, 0x0046), (5.0, 0x0027)]
    first_e3 = next(v[1] for _i, _t, op, v in jarin if op == E3)
    got = spellhitjoin.observer_of(jarin, presses)
    check(first_e3 == 30 and got == (29, 29, None),
          "the player of a hero tape is the property-41 agent with the kind-5 "
          "create, and the agent answering the connection's own presses agrees "
          "-- NOT the agent of the first 0x00E3, which is the hero's (the "
          "known-bad arm, run on the same fixture)",
          f"first 0x00E3's agent {first_e3}; observer_of -> {got}")
    solo = [r for r in jarin if not (r[2] == P9F and r[3][2] == 30)]
    swapped = [(i, t, op, [v[0], 30] + v[2:] if op in (E3, E2) and v[1] == 29
                else ([v[0], 29] + v[2:] if op in (E3, E2) else v))
               for i, t, op, v in solo]
    got = spellhitjoin.observer_of(swapped, presses)
    check(got[0] is None and got[1] == 30
          and got[2].startswith("observer rules disagree")
          and "29" in got[2] and "30" in got[2],
          "the two rules DISAGREEING is refused -- no player named, the reason "
          "names both answers -- never settled by picking one",
          f"property 41 on 29 alone, the presses answered by 30: {got}")
    no41 = [r for r in jarin if r[2] != P9F]
    got_press = spellhitjoin.observer_of(no41, presses)
    got_none = spellhitjoin.observer_of(no41, ())
    check(got_press == (29, 29, None) and got_none[0] is None
          and got_none[2].startswith("no observer")
          and spellhitjoin.player_of(jarin) == 29,
          "the fallbacks: no property 41 -> the answered presses name the "
          "player; neither -> None, said so; property 41 alone (no c2s given) "
          "still names the player on a hero tape",
          f"no 41 + presses {got_press}; no 41, no presses {got_none}; "
          f"player_of(jarin) {spellhitjoin.player_of(jarin)}")
    late = [(i, t + (0.7 if op == E3 and v[1] == 29 else 0.0), op, v)
            for i, t, op, v in jarin if not (op == E2)]
    got = spellhitjoin.observer_of(late, presses)
    check(got == (29, None, None),
          f"an answer later than {spellhitjoin.PRESS_ANSWER_S} s casts no vote "
          "(a press that walks into range first); it does not refute property 41",
          f"the E3 0.73 s after its press: {got}")


    print("\n11c. Incendiary Bonds 179: the hex's END EFFECT -- at expiry, at the wearer's "
          "death, negated by a removal (studies/skills 61, hexjoin.py)")
    # The tape (28 completions): the completion lands the hex ALONE; its end strikes
    # every foe within 240 u of the wearer, per foe the word THEN the Burning, then the
    # hex's own end; the target's death fires it early on the foes standing; the
    # target's Remove Hex negates it. Driven here through the real press / E5,
    # effect_tick, a killing hit and a hostile's land_skill, against the vault's records.
    FOE, HERO, PLAYER = 10, 200, authsrv.PLAYER_AGENT_ID
    saved_b3 = (authsrv._is_attack_skill, authsrv.skill_timing, authsrv.skill_cost,
                authsrv.weapon_satisfies, agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
                authsrv.HEX_END_BURST, authsrv.SPELL_ENERGY_BONUS, authsrv.ENERGY_BONUS_PER_FOE,
                authsrv.AREA_DAMAGE, authsrv.skill_condition)
    STATUS, REGEN, WORD, APPLY, REMOVE = 0x00F1, 0x00A2, 0x00A3, 0x0042, 0x0044
    words = lambda batch: [v[:3] for op, v in batch if op == WORD and v[0] in (16, 17)]   # noqa: E731
    fracs = lambda batch: [v[3] for op, v in batch if op == WORD and v[0] in (16, 17)]    # noqa: E731
    fin58 = lambda batch: [v for op, v in batch if op == 0x009F and v[0] == 58]           # noqa: E731
    adds = lambda batch: [tuple(v) for op, v in batch if op == 0x009F and v[0] == agents.PROP_AURA_ON]    # noqa: E731
    removes = lambda batch: [tuple(v) for op, v in batch if op == 0x009F and v[0] == agents.PROP_AURA_OFF]  # noqa: E731
    status = lambda batch: [tuple(v) for op, v in batch if op == STATUS]                  # noqa: E731
    applies = lambda batch: [v for op, v in batch if op == APPLY]                         # noqa: E731
    ops = lambda batch: [op for op, _v in batch]                                          # noqa: E731

    def eps(st):
        return sorted((e["agent"], e["buff"], e["skill"], e["duration"])
                      for e in authsrv.effect_table(st).live.values())

    def expire(st, send):
        for e in authsrv.effect_table(st).live.values():
            e["expires_at"] -= 60.0
        authsrv.effect_tick(send, st, 1)

    def _world():
        entry = {"name": "suit", "dead": False, "died_at": 0.0, "health": 9000.0,
                 "max_health": 9000.0, "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
                 "armor_rating": 60.0, "allegiance": agents.ALLEGIANCE_HOSTILE,
                 "attack_speed": authsrv.ENEMY_ATTACK_SPEED, "effects": 0,
                 "attacks_back": False, "skills": (), "skill_ready": []}
        st = {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 480.0}
        st["agents"][11] = dict(entry, pos=(200.0, 0.0))   # 100 u from the target: inside 156 / 240
        st["agents"][12] = dict(entry, pos=(600.0, 0.0))   # 500 u off: outside both
        return st

    def player_cast(sid, before=None, st=None):
        st, sent = (_world() if st is None else st), []
        st["cast_busy_until"] = 0.0
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.handle_skill_press([0, sid, 0, FOE], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
        sent.clear()
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        if before is not None:
            before(st)
        authsrv.cast_tick(send, st, 1)
        for cast in list(st["pending_casts"]):
            st["pending_casts"].remove(cast)
        return st, sent, send

    def _body_world(sid):
        foe = {"name": "archer", "dead": False, "died_at": 0.0, "health": 200.0,
               "max_health": 200.0, "last_hit": 0.0, "pos": (100.0, 0.0), "plane": 0,
               "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75, "effects": 0,
               "attacks_back": True, "skills": [[sid, 0.0, 20.0]], "skill_ready": [0.0],
               "npc": {"profession": 6, "level": 5}, "casting": 0, "cast_target": PLAYER}
        monk = {"name": "monk", "dead": False, "died_at": 0.0, "health": 100.0,
                "max_health": 100.0, "last_hit": 0.0, "pos": (0.0, 110.0), "plane": 0,
                "allegiance": agents.ALLEGIANCE_PLAYER, "effects": 0, "attack_speed": 1.75,
                "attacks_back": False, "skills": (), "skill_ready": [],
                "npc": {"profession": 3, "level": 5}, "party_slot": 0, "weapon_item": "caster_staff"}
        return {"agents": {FOE: foe, HERO: monk, 300: dict(monk, pos=(0.0, 400.0))},
                "pos": (0.0, 0.0), "player_health": 480.0, "player_dead": False}

    try:
        authsrv._is_attack_skill = lambda sid: False
        authsrv.skill_timing = lambda sid: (1.0, 0.75, 0.0)
        authsrv.skill_cost = lambda sid: (0, 0)
        authsrv.weapon_satisfies = lambda sid: True
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        r179 = agents.WORLD.get("skill_effect", "179")
        # (a) the readers, against the record: 72 at rank 13 is the tape's own payoff word
        # (0.12973 of a 555 pool, spellhitjoin 43.5), 3.0 s its Burning
        check(authsrv.hex_end_damage(179, 0) == (20, "standalone")
              and authsrv.hex_end_damage(179, 13) == (72, "standalone")
              and authsrv.hex_end_damage(185, 0) is None and authsrv.hex_end_damage(99999, 0) is None
              and authsrv.hex_cast_damage(179, 13) is None and authsrv.skill_damage(179, 13) is None
              and authsrv.skill_condition(179, 13) is None
              and authsrv._condition_terms(179, r179, 13) == (480, 3.0)
              and r179.get("on_end") == "burst" and r179.get("end_radius") == 240
              and authsrv.area_hex(179) is None and authsrv.spell_burst(179) is None,
              "the row: on_end = burst, end_radius 240; hex_end_damage reads the scale (20 at rank "
              "0, 72 at the tape caster's 13 -- retail's 0.12973 x 555), nothing hits at cast "
              "(hex_cast_damage / skill_damage None), skill_condition is None (the Burning is the "
              "payoff's: _condition_terms 3.0 s at 13), not an area hex, not a burst",
              (authsrv.hex_end_damage(179, 13), dict(r179)))
        # (b) the E5: the hex ALONE -- and the two visuals (EV-4: the skill_visual row)
        st, sent, send = player_cast(179)
        arm = next(iter(authsrv.effect_table(st).live.values())).get("end_burst")
        vis21 = [v for op, v in sent if op == 0x009F and v[0] == agents.GV_EFFECT_ON_AGENT]
        vis20 = [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
        i58 = next((i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 58), None)
        i21 = next((i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == agents.GV_EFFECT_ON_AGENT), None)
        i20 = next((i for i, (op, v) in enumerate(sent) if op == 0x00A0), None)
        i6 = next((i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 6), None)
        check(fin58(sent) == [[58, PLAYER, 0]] and not words(sent) and not applies(sent)
              and adds(sent) == [(6, FOE, 1), (6, FOE, 12)] and status(sent) == [(FOE, 0x800)]
              and vis21 == [[21, PLAYER, 347]] and vis20 == [[20, FOE, PLAYER, 348]]
              and None not in (i58, i21, i20, i6) and i58 < i21 < i20 < i6
              and eps(st) == [(FOE, 1, 179, 3.0)]
              and arm == {"radius": 240.0, "hostile": False, "caster_row": None}
              and all(st["agents"][a]["health"] == 9000.0 for a in (FOE, 11, 12)),
              "the player's Incendiary Bonds at the E5: [58, me, 0], [21, me, 347], [20, 10, me, "
              "348] (the s_skill +0x78 / +0x7c pair, retail 28/28 -- the review's EV-4: the first "
              "cut had no skill_visual row and sent neither), [6, 10, 1], [6, 10, 12], 0x00F1 "
              "[10, 0x800] -- no word, no Burning, one 3.0 s episode on the target ARMED (240 u, "
              "the player's side), the foes beside it untouched",
              str([(hex(op), v) for op, v in sent]))
        # (c) the expiry: the payoff per foe, THEN the hex's own end
        sent.clear()
        expire(st, send)
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_7 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 7]
        i_f = [i for i, (op, v) in enumerate(sent) if op == STATUS]
        i_r = [i for i, (op, v) in enumerate(sent) if op == REGEN]
        check(words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and len(set(fracs(sent))) == 1
              and status(sent) == [(FOE, 0x802), (11, 0x002), (FOE, 0x002)]
              and [v[:2] for op, v in sent if op == REGEN] == [[44, FOE], [44, 11]]
              and i_w[0] < i_f[0] < i_r[0] < i_w[1] < i_f[1] < i_r[1] < i_7[0] < i_7[1] < i_f[2]
              and removes(sent) == [(7, FOE, 1), (7, FOE, 12)] and REMOVE not in ops(sent)
              and eps(st) == [(FOE, 2, 480, 1.0), (11, 3, 480, 1.0)]
              and st["agents"][FOE]["health"] == 8980.0 and st["agents"][11]["health"] == 8980.0
              and st["agents"][12]["health"] == 9000.0,
              "at +3 s the END EFFECT: per foe within 240 u (the target, the one 100 u beside "
              "it; not the one 500 u off) in id order the word [16, foe, me, 20] then its Burning "
              "(0x00F1 +0x02, [44] -- 1.0 s at rank 0; no 0x0042 on a foe), THEN the hex's own "
              "end [7, 10, 1] [7, 10, 12] 0x00F1 [10, 0x2]; no 0x0044 for a foe; no 58, no [20]",
              str([(hex(op), v) for op, v in sent]))
        # (d) the wearer's DEATH fires it early, once, on the foes still standing
        st, sent, send = player_cast(179)
        st["agents"][FOE]["health"] = 1.0
        sent.clear()
        authsrv.hit_enemy(send, st, FOE, 1, exact=5.0, swing=False, armed=True, label="a killing blow")
        dead_batch = list(sent)
        sent.clear()
        expire(st, send)
        d_ops = [(op, v) for op, v in dead_batch]
        i_kill = next((i for i, (op, v) in enumerate(d_ops) if op == STATUS and v == [FOE, 0x810]), None)
        i_rew = next((i for i, (op, v) in enumerate(d_ops) if op == 0x00EE), None)
        i_pay = next((i for i, (op, v) in enumerate(d_ops) if op == WORD and v[1] == 11), None)
        i_7 = [i for i, (op, v) in enumerate(d_ops) if op == 0x009F and v[0] == 7]
        i_step = next((i for i, (op, v) in enumerate(d_ops) if op == STATUS and v == [FOE, 0x10]), None)
        i_flags = next((i for i, (op, v) in enumerate(d_ops) if op == 0x0026), None)
        i_6 = [i for i, (op, v) in enumerate(d_ops) if op == 0x009F and v[0] == 6]
        check(words(dead_batch) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and adds(dead_batch) == [(6, 11, 25)]
              and removes(dead_batch) == [(7, FOE, 1), (7, FOE, 12)]
              and status(dead_batch) == [(FOE, 0x810), (11, 0x002), (FOE, 0x10)]
              and None not in (i_kill, i_rew, i_pay, i_step, i_flags) and len(i_7) == 2
              and i_kill < i_rew < i_pay < i_6[0] < i_7[0] < i_7[1] < i_step < i_flags
              and st["agents"][FOE]["dead"] and st["agents"][11]["health"] == 8980.0
              and st["agents"][12]["health"] == 9000.0
              and eps(st) == [] and not words(sent) and removes(sent) == [(7, 11, 25)],
              "the target killed at +0 s -- RETAIL'S DEATH BATCH ORDER (631.935 / 642.688, 2/2; "
              "the review's EV-1 / EV-2 / R34-1): the death word FIRST with the hex bit still up "
              "(0x810), the kill reward, THEN the payoff EARLY on the foe beside the corpse (20, "
              "Burning with its [6, 11, 25] -- RANGERPRE-S13; retail :54071 634.746 [6, 9, 25] on "
              "the neighbour, then the corpse's [7]s) and not on the corpse, THEN the corpse's "
              "[7, 10, 1] [7, 10, 12] -- ITS OWN, though the Burning took the corpse's freed buff "
              "id (the (wearer, buff) book; keyed by the buff alone the corpse's REMOVE sent [7, "
              "11, 25] here), the step-down 0x00F1 [10, 0x10], the flags byte LAST; the episode is "
              "gone and the tick that would have expired it fires NOTHING more (end_fired: once "
              "per hex) -- the neighbour's Burning ends on its own with [7, 11, 25]",
              (str([(hex(op), v) for op, v in dead_batch]), eps(st), removes(sent)))
        # (d') the review's M5: the payoff KILLS ITS OWN WEARER at expiry -- once
        st, sent, send = player_cast(179)
        st["agents"][FOE]["health"] = 5.0
        sent.clear()
        expire(st, send)
        check(words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and removes(sent) == [(7, FOE, 1), (7, FOE, 12)] and REMOVE not in ops(sent)
              and st["agents"][FOE]["dead"] and st["agents"][11]["health"] == 8980.0
              and [(e[0], e[2], e[3]) for e in eps(st)] == [(11, 480, 1.0)],
              "the payoff kills its own wearer at expiry: ONE word per foe, ONE [7] pair (the "
              "wearer's strip closed and worded the episode; end_fired keeps the strip from "
              "firing it again -- without the guard foe 11 took a third word), the adjacent "
              "foe's health down once", str([(hex(op), v) for op, v in sent]))
        # (d'') the review's M6: the payoff KILLS THE ADJACENT FOE -- no Burning on its corpse
        st, sent, send = player_cast(179)
        st["agents"][11]["health"] = 5.0
        sent.clear()
        expire(st, send)
        w11 = [v[1] for op, v in sent if op == STATUS and v[0] == 11]
        check(st["agents"][11]["dead"] and [e for e in eps(st) if e[0] == 11] == []
              and w11 and w11[0] & 0x10 and not any(w & 0x02 for w in w11)
              and eps(st) == [(FOE, 2, 480, 1.0)],
              "the payoff kills the adjacent foe: no Burning episode on its corpse and no status "
              "word of its carrying the condition bit after the death word (apply_condition "
              "refuses nothing -- the payoff's own corpse gate is what keeps it off)",
              (eps(st), w11))
        # (d''') the review's R34-4: a SECOND 179 on the same wearer arms no second payoff
        st, sent, send = player_cast(179)
        st, sent2, send = player_cast(179, st=st)
        armed = sorted((e["buff"], bool(e.get("end_burst"))) for e in authsrv.effect_table(st).live.values())
        sent2.clear()
        expire(st, send)
        st_d, sent_d, send_d = player_cast(179)
        st_d, sent_d, send_d = player_cast(179, st=st_d)
        st_d["agents"][FOE]["health"] = 1.0
        sent_d.clear()
        authsrv.hit_enemy(send_d, st_d, FOE, 1, exact=5.0, swing=False, armed=True, label="a killing blow")
        check(armed == [(1, True), (2, False)]
              and words(sent2) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st["agents"][11]["health"] == 8980.0
              and words(sent_d) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st_d["agents"][11]["health"] == 8980.0,
              "two Incendiary Bonds on one wearer: two episodes (retail's overlapping shape) but "
              "the second ARMS NOTHING while the first's end is live -- one payoff at expiry and "
              "one at the wearer's death, each foe struck once (RECONSTRUCTION: the client draws "
              "the first hex; no double 179 is on any tape)", (armed, words(sent2), words(sent_d)))
        # (e) a REMOVAL negates it -- and the known-bad arm shows the dead gate is what negates
        st, sent, send = player_cast(179)
        ep = next(iter(authsrv.effect_table(st).live.values()))
        sent.clear()
        authsrv.strip_effects(send, st, FOE, 1, "a cure")
        negated = (list(sent), eps(st), {a: st["agents"][a]["health"] for a in (FOE, 11)})
        sent.clear()
        authsrv.hex_end_burst(send, st, 1, ep, "a death-blind strip (the known-bad arm)")
        check(removes(negated[0]) == [(7, FOE, 1), (7, FOE, 12)] and not words(negated[0])
              and negated[1] == [] and negated[2] == {FOE: 9000.0, 11: 9000.0}
              and words(sent) == [[16, FOE, PLAYER], [16, 11, PLAYER]]
              and st["agents"][FOE]["health"] == 8980.0,
              "a strip while ALIVE (a cure / Remove Hex): the [7]s and 0x00F1 0, no word on "
              "anybody, no Burning -- NEGATED (retail 4/4); KNOWN-BAD ARM: the same stripped "
              "episode handed to hex_end_burst as a death-blind strip would DETONATES on both "
              "foes -- so the `if dead:` gate in strip_effects is what negates",
              (str([(hex(op), v) for op, v in negated[0]]), str(words(sent))))
        # (f) known-bad: the Burning at the COMPLETION (skill_condition ungated)
        authsrv.skill_condition = lambda sid, r: authsrv._condition_terms(sid, authsrv.skill_effect_row(sid), r)
        try:
            st_b, sent_b, _s = player_cast(179)
        finally:
            authsrv.skill_condition = saved_b3[-1]
        st_g, sent_g, _s = player_cast(179)
        check(eps(st_b) == [(FOE, 1, 179, 3.0), (FOE, 2, 480, 1.0)] and status(sent_b)[-1] == (FOE, 0x802)
              and eps(st_g) == [(FOE, 1, 179, 3.0)],
              "KNOWN-BAD ARM: with skill_condition's on_end gate stubbed out the completion "
              "Burns the target at once (retail: 0 of 28); the gate keeps the Burning for the "
              "payoff", (eps(st_b), eps(st_g)))
        # (g) --no-hex-end-burst
        authsrv.HEX_END_BURST = False
        st_n, sent_n, send_n = player_cast(179)
        sent_n.clear()
        expire(st_n, send_n)
        authsrv.HEX_END_BURST = True
        check(not words(sent_n) and removes(sent_n) == [(7, FOE, 1), (7, FOE, 12)]
              and status(sent_n) == [(FOE, 0)] and eps(st_n) == []
              and all(st_n["agents"][a]["health"] == 9000.0 for a in (FOE, 11)),
              "--no-hex-end-burst: the hex expires with its [7]s and 0x00F1 0 and NOTHING fires "
              "-- this server's bytes until 2026-09-27",
              str([(hex(op), v) for op, v in sent_n]))
        # (h) a hostile's 179 at the player, the hero 110 u above, a party body 400 u off
        st = _body_world(179)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        at_e5 = list(sent)
        sent.clear()
        expire(st, send)
        ar = authsrv.spell_armour_for(179)
        want = authsrv._whole_points(68.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        i10 = next((i for i, (op, v) in enumerate(sent) if op == 0x009F and v[:3] == [10, PLAYER, 179]), None)
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_42 = [i for i, (op, v) in enumerate(sent) if op == APPLY]
        i_44 = [i for i, (op, v) in enumerate(sent) if op == REMOVE]
        i_7 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[0] == 7]
        check(at_e5[0] == (0x009F, [58, FOE, 0])
              and applies(at_e5) == [[PLAYER, 179, 12, 1, authsrv._f32(3.0)]]
              and adds(at_e5) == [(6, PLAYER, 1), (6, PLAYER, 12)] and status(at_e5) == [(PLAYER, 0x800)]
              and not words(at_e5) and st["player_health"] == 480.0 - want
              and words(sent) == [[16, PLAYER, FOE], [16, HERO, FOE]]
              and i10 is not None and i10 + 1 == i_w[0]
              and applies(sent) == [[PLAYER, 480, 12, 2, authsrv._f32(3.0)]]
              and i_w[0] < i_42[0] < i_w[1] < i_44[0] < i_7[0] < i_7[1]
              and removes(sent) == [(7, PLAYER, 1), (7, PLAYER, 12)]
              and eps(st) == [(PLAYER, 2, 480, 3.0), (HERO, 3, 480, 3.0)]
              and st["agents"][HERO]["health"] < 100.0 and st["agents"][300]["health"] == 100.0,
              f"a hostile's Incendiary Bonds at the player: [58, it, 0], the player's 0x0042 [me, "
              f"179, 12, 1, 3.0], [6, me, 1], [6, me, 12], 0x00F1 0x800, NO word; at +3 s: [10, me, "
              f"179] then the player's word ({want} = 68 at rank 12 against the pieces' rating at "
              f"the caster's strike level), its Burning 0x0042 480 3.0 s (rank 12: 2.6 -> 3), then "
              f"the hero's word 110 u off and its Burning, THEN 0x0044 [me, 1], [7, me, 1], [7, me, "
              f"12]; the body 400 u off untouched -- the caster's row snapshotted at the apply",
              (str([(hex(op), v) for op, v in at_e5]), str([(hex(op), v) for op, v in sent])))
        # (i) SOURCE: where the hook sits, and that the flag flips inside main()
        src = open(authsrv.__file__, encoding="utf-8").read()
        i_tick = src.index("\ndef effect_tick(")
        i_fire = src.index('hex_end_burst(send, state, conn_id, ep, "it ran out")', i_tick)
        i_close = src.index('table.close(ep["buff"])', i_tick)
        i_strip = src.index("\ndef strip_effects(")
        i_dead = src.index("    if dead:\n", i_strip)
        i_sfire = src.index("hex_end_burst(send, state, conn_id, ep, why)", i_strip)
        i_srem = src.index("effect_list_send(send, state, GAME_SMSG_EFFECT_REMOVE, [ep[\"agent\"], ep[\"buff\"]],", i_strip)
        i_kill = src.index("\ndef kill_agent(")
        i_kword = src.index("    send(GAME_SMSG_AGENT_UPDATE_STATUS, [target_id, _word],", i_kill)
        i_krew = src.index("    send(GAME_SMSG_AGENT_KILL_REWARD,", i_kill)
        i_kstrip = src.index("    _strip_and_step_down()             # between the reward and the flags", i_kill)
        i_kflags = src.index("    send(GAME_SMSG_AGENT_UPDATE_FLAGS, [target_id, AGENT_FLAGS_KILLED],\n         f\"flags {AGENT_FLAGS_KILLED} on the dying agent", i_kill)
        i_main = src.index("\ndef main():")
        i_flag = src.index("    if a.no_hex_end_burst:", i_main)
        i_flag2 = src.index("    if a.no_spell_energy_bonus:", i_main)
        i_flag3 = src.index("    if a.energy_bonus_target_only:", i_main)
        check(i_tick < i_fire < i_close and i_strip < i_dead < i_sfire < i_srem
              and i_sfire - i_dead < 900
              and i_kill < i_kword < i_krew < i_kstrip < i_kflags
              and src.count("    hex_end_arm(state, ep, caster_id, row, erow)      # studies/skills 61") == 1
              and "HEX_END_BURST = False" in src[i_flag:i_flag + 160]
              and "SPELL_ENERGY_BONUS = False" in src[i_flag2:i_flag2 + 160]
              and "ENERGY_BONUS_PER_FOE = False" in src[i_flag3:i_flag3 + 160]
              and src.count("    if row.get(\"on_end\") or row.get(\"bonus_if\"):") == 1,
              "SOURCE LOCK: effect_tick fires the end effect BEFORE the close (the payoff ahead of "
              "the hex's own end), strip_effects fires it under `if dead:` only and AHEAD of the "
              "removal loop (the payoff, then the [7]s -- retail 2/2), kill_agent sends the death "
              "word, the reward, the strip, the flags in that order, the arm is set once at the "
              "apply, skill_condition gates on_end / bonus_if, main() flips HEX_END_BURST / "
              "SPELL_ENERGY_BONUS / ENERGY_BONUS_PER_FOE under their flags (the review's M10)")

        print("\n11d. Mind Burn 185: the base word on the target and the adjacent foes, the "
              "energy clause's twin and Burning decided PER FOE (studies/skills 61)")
        # 25 completions on the tape: [58] [20, T, c, 331] then per foe the word, and a second
        # identical word + Burning when the clause holds FOR THAT FOE -- 647.300 has the target
        # single and an adjacent foe twin, which one comparison against the target cannot make.
        r185 = agents.WORLD.get("skill_effect", "185")
        check(authsrv.skill_damage(185, 0) == (15, "standalone") and authsrv.skill_damage(185, 13) == (54, "standalone")
              and authsrv.spell_adjacent(185) == 156.0 and authsrv.spell_adjacent(179) is None
              and authsrv.spell_adjacent(194) is None and authsrv.spell_adjacent(99999) is None
              and authsrv.energy_bonus_row(185) and not authsrv.energy_bonus_row(179)
              and authsrv.skill_condition(185, 13) is None
              and authsrv._condition_terms(185, r185, 13) == (480, 9.0)
              and authsrv.spell_burst(185) is None and authsrv.area_over_time(185, 12) is None
              and authsrv.player_rank_for_skill(185) == 0,
              "the row: Fire damage 15..60 (54 at the tape caster's 13), adjacent_damage reaches "
              "156 u (a type-5 spell at a foe; a hex or a projectile spell reach nothing), the "
              "energy clause is the row's, skill_condition is None (the Burning is the twin's: "
              "9.0 s at 13 -- retail's 9.0 on the observer), not a burst, not an area; the "
              "player casts at rank 0", (authsrv.spell_adjacent(185), dict(r185)))

        def energies(mine, foe, other):
            def _set(s):
                authsrv.player_energy(s).current = float(mine)
                authsrv.agent_energy(s["agents"][FOE]).current = float(foe)
                authsrv.agent_energy(s["agents"][11]).current = float(other)
            return _set
        # (b) the player at 15: the target (10) takes the twin + Burning, the adjacent (20) one word
        st, sent, send = player_cast(185, before=energies(15, 10, 20))
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        i_f = [i for i, (op, v) in enumerate(sent) if op == STATUS]
        i_20 = [i for i, (op, v) in enumerate(sent) if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
        check(fin58(sent) == [[58, PLAYER, 0]]
              and words(sent) == [[16, FOE, PLAYER], [16, FOE, PLAYER], [16, 11, PLAYER]]
              and len(set(fracs(sent))) == 1 and status(sent) == [(FOE, 0x002)]
              and i_w[1] < i_f[0] < i_w[2]
              and [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_EFFECT_ON_TARGET]
              == [[20, FOE, PLAYER, 331]] and i_20[0] < i_w[0]
              and eps(st) == [(FOE, 1, 480, 1.0)]
              and st["agents"][FOE]["health"] == 8970.0 and st["agents"][11]["health"] == 8985.0
              and st["agents"][12]["health"] == 9000.0,
              "the player's Mind Burn (energy 15) on the target (10) with a foe 100 u beside it (20): "
              "[58], [20, 10, me, 331] on the TARGET alone (the s_skill +0x7c, retail 25/25 -- the "
              "review's EV-4; the first cut sent none and locked the absence), the target's word "
              "TWICE (identical, 15 at rank 0) then its Burning (0x00F1 +0x02, 1.0 s at rank 0), "
              "then the adjacent foe's ONE word; the foe 500 u off untouched; no [20] per foe",
              str([(hex(op), v) for op, v in sent]))
        # (b') the review's R34-2: a target DEAD at the E5 -- nothing on the foes beside it
        st_x, sent_x, _s = player_cast(185, before=lambda s: (energies(15, 10, 20)(s),
                                                             s["agents"][FOE].update(dead=True, health=0.0)))
        check(not words(sent_x) and eps(st_x) == [] and fin58(sent_x) == [[58, PLAYER, 0]]
              and st_x["agents"][11]["health"] == 9000.0,
              "Mind Burn at a target that died mid-cast: the 58 and NOTHING lands -- not on the "
              "corpse, not on the foe 100 u beside it (a targeted spell fails with its target; "
              "only an area at a LOCATION survives it, WIKI rev 2685457); the first cut struck "
              "the adjacent foe from the corpse", str([(hex(op), v) for op, v in sent_x]))
        # (c) 647.300's shape: the target single, the adjacent foe twin
        st, sent, send = player_cast(185, before=energies(15, 20, 5))
        shape_647 = (words(sent), eps(st))
        # (d) KNOWN-BAD: the wiki's one comparison against the target cannot produce it
        authsrv.ENERGY_BONUS_PER_FOE = False
        st_t, sent_t, _s = player_cast(185, before=energies(15, 20, 5))
        st_t2, sent_t2, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.ENERGY_BONUS_PER_FOE = True
        check(shape_647 == ([[16, FOE, PLAYER], [16, 11, PLAYER], [16, 11, PLAYER]], [(11, 1, 480, 1.0)])
              and words(sent_t) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and eps(st_t) == []
              and words(sent_t2) == [[16, FOE, PLAYER], [16, FOE, PLAYER], [16, 11, PLAYER], [16, 11, PLAYER]]
              and eps(st_t2) == [(FOE, 1, 480, 1.0), (11, 2, 480, 1.0)],
              "647.300's shape (the target at 20, the adjacent at 5, the caster 15): the target "
              "SINGLE and the adjacent foe TWIN + Burning -- PER FOE; KNOWN-BAD ARM "
              "--energy-bonus-target-only (the wiki's wording): the same pools give two singles, "
              "and 15 vs (10, 20) gives two twins -- one comparison can never split them",
              (shape_647, words(sent_t), words(sent_t2)))
        # (e) the reverts
        authsrv.SPELL_ENERGY_BONUS = False
        st_e, sent_e, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.SPELL_ENERGY_BONUS = True
        authsrv.AREA_DAMAGE = False
        st_a, sent_a, _s = player_cast(185, before=energies(15, 10, 20))
        authsrv.AREA_DAMAGE = True
        check(words(sent_e) == [[16, FOE, PLAYER], [16, 11, PLAYER]] and eps(st_e) == []
              and words(sent_a) == [[16, FOE, PLAYER]] and eps(st_a) == []
              and st_a["agents"][11]["health"] == 9000.0,
              "--no-spell-energy-bonus: the base words alone, no Burning, whatever the pools; "
              "--no-area-damage: the target's ONE word (the pre-2026-09-27 shape), the adjacent "
              "foe untouched", (words(sent_e), words(sent_a)))
        # (f) a hostile's Mind Burn at the player (30 vs 20: the twin), the hero (30 vs 30: single)
        st = _body_world(185)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))   # noqa: E731
        authsrv.player_energy(st).current = 20.0
        authsrv.agent_energy(st["agents"][HERO]).current = 30.0
        authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        ar = authsrv.spell_armour_for(185)
        want = authsrv._whole_points(51.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar))
        i10 = [i for i, (op, v) in enumerate(sent) if op == 0x009F and v[:3] == [10, PLAYER, 185]]
        i_w = [i for i, (op, v) in enumerate(sent) if op == WORD]
        check(sent[0] == (0x009F, [58, FOE, 0])
              and words(sent) == [[16, PLAYER, FOE], [16, PLAYER, FOE], [16, HERO, FOE]]
              and fracs(sent)[0] == fracs(sent)[1] and len(i10) == 2
              and i10[0] + 1 == i_w[0] and i10[1] + 1 == i_w[1]
              and applies(sent) == [[PLAYER, 480, 12, 1, authsrv._f32(8.0)]]
              and st["player_health"] == 480.0 - 2 * want
              and st["agents"][HERO]["health"] < 100.0 and st["agents"][300]["health"] == 100.0
              and eps(st) == [(PLAYER, 1, 480, 8.0)] and st["agents"][FOE]["casting"] is None
              and float(authsrv.agent_energy_now(st, FOE)) == 30.0,
              f"a hostile's Mind Burn (its pool is our ENEMY_ENERGY 30) at the player (20) with "
              f"the hero 110 u above (30): [58, it, 0], then [10, me, 185] + the player's word "
              f"TWICE ({want} each, identical -- retail's twin) and its Burning 0x0042 480 8.0 s "
              f"(rank 12: 8.2 -> 8), then the hero's ONE word (30 is not more than 30); the body "
              f"400 u off untouched; every foe's terms computed before the 58",
              str([(hex(op), v) for op, v in sent]))
        # (g) SOURCE: the adjacent arm sits inside the standalone arm, behind the area over time
        i_std = src.index('elif target and found and found[1] == "standalone":')
        i_aotl = src.index("                elif _aot is not None:", i_std)
        i_adjl = src.index("                elif _adj is not None and not target_dead(state, target):", i_std)
        i_std_hit = src.index("_st_res = hit_enemy(send, state, target, conn_id, exact=player_spell_amount(", i_std)
        check(i_std < i_aotl < i_adjl < i_std_hit
              and src.count("                elif _adj is not None and not target_dead(state, target):") == 1
              and src.count("    if _adj_terms is not None:                                # studies/skills 61") == 1
              and src.count("    elif damage is not None and _spell_how is None and _carea is None and _adj is not None:") == 1
              and src.index("    if _adj_terms is not None:") > src.index("    if _burst_terms is not None:                              # studies/weapons 40"),
              "SOURCE LOCK: the player's adjacent arm sits inside the standalone arm behind the "
              "area over time and ahead of the one-target word, gated on a LIVE target (R34-2); "
              "a body's terms arm and its exit "
              "sit beside the burst's (the terms before the 58, the words behind it)")
    finally:
        (authsrv._is_attack_skill, authsrv.skill_timing, authsrv.skill_cost,
         authsrv.weapon_satisfies, agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
         authsrv.HEX_END_BURST, authsrv.SPELL_ENERGY_BONUS, authsrv.ENERGY_BONUS_PER_FOE,
         authsrv.AREA_DAMAGE, authsrv.skill_condition) = saved_b3

    # The corpus reads the vault's own tables (hexjoin's 179 rank against the server's
    # hex_end_damage), never RECORD's: the carried rows go back here.
    carry.close()

    print("\n12. the corpus: one caster, one skill, one target is ONE value "
          "(spellhitjoin)")
    # P1-P4 in spellhitjoin's own words. A location roll on a set whose
    # pieces differ would put a second bucket on some pair; none has one.
    # FLOORS, not exact values -- the live corpus grows.
    # The skip is decided on the capture DIRECTORY, never on a failed read: a crash in a
    # reader is a crash, not a skip (2026-09-28).
    # 2026-10-07: the skip covers 12, 12b, 12c and 13 (42 checks on the owner's vault:
    # 25 + 1 + 14 + 2) and RETURNS TO main(), which still runs 14 and 15 -- until that
    # day it returned the verdict from here and section 14 was never reached or declared.
    try:
        vaultpath.require_dir("captures", "live", why="section 12's corpus")
    except (Exception, SystemExit) as exc:                # noqa: BLE001  (require_dir exits)
        LEDGER.skip("12-13. the corpus: spellhitjoin, location buckets, hexjoin, healjoin "
                    "(42 checks: 12 25, 12b 1, 12c 14, 13 2)",
                    f"no live corpus to read on this machine: {exc!r}")
        return
    unnamed, set_aside, refused_conns, named_census = [], [], [], []
    rows = spellhitjoin.census(unnamed=unnamed, set_aside=set_aside, refused=refused_conns,
                               named=named_census)
    sc = spellhitjoin.score(rows)
    # THE ZAISHEN CAPTURE (2026-09-28, CASTAI-Z1): P2 was scored before it on every capture;
    # it is scored so still on every capture BUT that one, whose multi-valued pairs are
    # asserted exactly beside it (the new facts; spellhitjoin P2 FAILED there).
    ZAISHEN = "20260928T103123"
    # THE SECOND ZAISHEN CAPTURE (2026-09-29, CASTAI-Z2, the Smiting Monks): P2 holds there
    # once the join stops counting two classes of word as the announced skill's -- a PAYOFF
    # riding the batch of the skill that triggered it (Zealot's Fire 271, named by the wire's
    # own [10, obs, 271]) and a CONVERTED +0.0 (Reversal of Fortune) -- spellhitjoin's
    # docstring. The pin (every capture before it) is asserted to the digit below, the
    # tape's own census exact, and the classes are shown load-bearing on a known-bad arm.
    ZAISHEN2 = "20260929T100038"
    sc_rest = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN])
    rows_z = [r for r in rows if r["capture"] == ZAISHEN]
    rows_z2 = [r for r in rows if r["capture"] == ZAISHEN2]
    rows_pin = [r for r in rows if r["capture"] < ZAISHEN2]
    GAPPED = [(ZAISHEN, "10.0.0.210:65009->98.95.137.136:80")]
    check([x[:2] for x in set_aside] == GAPPED and all(x[2] for x in set_aside)
          and refused_conns == [],
          "the one connection the manifests declare gapped (20260928T103123 :65009, CASTAI-Z1's "
          "match 2) is set aside BY NAME and still refused; no other connection fails to frame "
          "(they used to be dropped without a word -- now a new one reddens this)",
          f"set aside {set_aside}; refused {refused_conns}")
    hero_tape = {r["player"] for r in rows if r["capture"] == "20260914T005758"
                 and r["connection"].split("->")[0].endswith(":56011")}
    refused = [u for u in unnamed if u[2].startswith("observer rules disagree")]
    check(hero_tape == {29} and not refused,
          "the census names the JARIN tape's player 29 (the kind-5 create whose "
          "acks answer every press), not the hero 30 whose ack comes first; no "
          "connection in the corpus has its two rules disagreeing",
          f"players on 20260914T005758 conn 56011: {hero_tape}; refused "
          f"{refused}; named by nobody {len(unnamed)} (the corpus's one is a "
          f"stub with no property 41 and no press)")
    check(sc["n_cast"] >= 100 and sc["announced"] >= 0.95 * sc["n_cast"],
          "P1 cast damage is announced by a property-60 from its cause",
          f"{sc['announced']} of {sc['n_cast']} inside 4 s (floor 100, 95%)")
    # JARIN (20260914T005758): the caster 54's skill 222 on the Ranger and on
    # the hero spans TWO death penalties each (the targets' maxima 140 -> 119
    # -> 99 / 101) and the hero's Frenzy doubled its intake -- the join keys
    # on the target, not on the target's current maximum, so those two pairs
    # are several values by construction. Named, not widened: a third pair
    # is a new fact.
    # SLICE-F47 (2026-09-16): the third pair came -- 20260916T150306,
    # caster 48's skill 222 onto 29, maximum 140 -> 119 -- and it is the
    # death-penalty split ALONE: 24 whole points at both maxima, 0.17143 x 3
    # then 0.20168. So that signature is a rule in spellhitjoin.score
    # (`penalty_split`: one value per maximum, several maxima) and the new
    # pair passes by it. JARIN's two do NOT pass it and stay named: the
    # Ranger's holds 23 AND 24 points at the one maximum of 140 (cause
    # unmeasured), the hero's 26 AND 51 at 122 (Frenzy, F44/F45).
    PENALTY_SPLIT = {"54 222 29", "54 222 30"}
    split = sc["penalty_split"]
    split_rest = sc_rest["penalty_split"]
    check(sc_rest["pairs"] >= 10 and sc_rest["pair_hits"] >= 60
          and set(sc_rest["multi_valued"]) - set(split_rest) <= PENALTY_SPLIT,
          "P2 every (caster, skill, target) pair with >= 3 hits is ONE value "
          "per target maximum (a death-penalty split passes by SIGNATURE; the "
          "two JARIN pairs that are several values INSIDE one maximum set "
          "aside by name) -- on every capture but 20260928T103123, whose pairs "
          "are asserted exactly below",
          f"{sc_rest['pairs']} pairs over {sc_rest['pair_hits']} hits, skills "
          f"{sc_rest['skills']}, multi-valued {sc_rest['multi_valued']}, of which split "
          f"by a penalty {split_rest} -- a 1-in-8 head roll on any armour "
          f"difference leaves one bucket with probability (7/8)^n, 0.03% at "
          f"n = 60; DoT ticks set aside {sc_rest['ticks_set_aside']}")
    # CASTAI-Z1 (20260928T103123): the Zaishen Mage's (agent 9's) Mind Burn onto three
    # arena foes is several fractions per (connection, caster, skill, target) -- five pairs
    # over the three undamaged matches. Read in WHOLE POINTS: on :50295 all three are 54
    # points, the fraction moving 0.1125 / 0.13235 / 0.16071 = 54 of 480 / 408 / 336 -- the
    # death-penalty ladder -- but the maximum the join holds for each hit lags (the
    # penalty's prop 42 arrives AFTER the word, or never for 3 and 6), so the SIGNATURE
    # (one value per maximum held) cannot see it; on :50061 agent 6 takes 27 at 480 and a
    # fraction whole only at 408 (never on its wire; it died at 155.672 and was raised at
    # 158.976). ONE pair is a second bucket at one reported maximum: :50061 onto agent 5,
    # 29 points three times and 59 once (144.972), both at 480 -- P2 FAILED there, cause
    # UNMEASURED (59 / 29 = 2^(41/40): a location roll on a 40-armour spread, or a
    # damage-doubling state; agent 5's Frenzy 346 is first announced at 219.979, after it).
    zpairs = {(k[1].split("->")[0].rsplit(":", 1)[-1], k[2], k[3], k[4]): sorted(set(v))
              for k, v in spellhitjoin.pairs(rows_z, "cast", 3).items()
              if k[3] is not None and len(set(v)) > 1}
    zpts = {}
    for key in zpairs:
        pts = collections.Counter()
        for r in rows_z:
            if (r["kind"] == "cast" and not r["tick"] and r["maxhp"] is not None
                    and r["connection"].split("->")[0].endswith(":" + key[0])
                    and (r["cause"], r["skill"], r["target"]) == key[1:]):
                p = -r["value"] * r["maxhp"]
                if abs(p - round(p)) <= spellhitjoin.INTEGER_EPS:
                    pts[(int(round(p)), r["maxhp"])] += 1
        zpts[key] = dict(sorted(pts.items()))
    check(zpairs == {("50061", 9, 185, 5): [-0.12292, -0.07108, -0.06636, -0.06042],
                     ("50061", 9, 185, 6): [-0.06618, -0.05625],
                     ("50295", 9, 185, 3): [-0.13235, -0.1125],
                     ("50295", 9, 185, 5): [-0.16071, -0.13235, -0.1125],
                     ("50295", 9, 185, 6): [-0.13235, -0.1125]}
          and zpts[("50061", 9, 185, 5)] == {(29, 437): 2, (59, 480): 2}
          and zpts[("50295", 9, 185, 5)] == {(54, 336): 2, (54, 480): 2}
          and not any(k in split for k in ("9 185 3", "9 185 5", "9 185 6")),
          "P2 on 20260928T103123 (exact, per tape): FIVE multi-valued pairs, all agent 9's Mind "
          "Burn 185; whole points at the maximum the join holds show 54 at 480 AND at 336 onto "
          ":50295's agent 5 (the penalty ladder, its 408 hit read one death stale) and 29 at 437 "
          "AND 59 at 480 onto :50061's agent 5 -- the second bucket at one maximum that FAILS P2; "
          "the signature recognises none of the five (the arena's maxima reach the wire late or "
          "never) -- a finding, not absorbed",
          f"{zpairs}; whole points (points, maximum): {zpts}")
    points = {k: sorted({round(v * m) for m, vals in b.items() for v in vals})
              for k, b in split.items()}
    check(len(split) >= 1 and all(len(p) == 1 for p in points.values()),
          "and every penalty-split pair is ONE value in WHOLE POINTS across "
          "its maxima -- the fraction moved because the maximum did (F46)",
          f"{points} -- LAKESIDE (20260916T150306): 48's 222 onto 29 is 24 "
          f"points at a maximum of 140 (0.17143, 3 hits) and at 119 (0.20168)")
    two = sc["two_hit_two_valued"]
    check(len(two) <= 1 and all(k.startswith("10 186 12") for k in two),
          "and the pairs BELOW the floor with two values are the one named "
          "mixed batch, Fireball + Incendiary Bonds' payoff onto agent 12",
          f"{two} -- the hex-end payoff lands 3.000 s after a 1 s cast and "
          f"the projectile 0.4 s after its 58, in one batch (43.5). A second "
          f"such pair is a new fact, not noise: read it before raising this")
    check(len(sc["onto_player"]) >= 1
          and all(n >= 3 and (len(vals) == 1 or k in PENALTY_SPLIT
                              or k in split)
                  for k, (n, vals) in sc["onto_player"].items()),
          "and the pairs onto the connection's OWN player are one value too "
          "(the JARIN penalty-split pair set aside by name)",
          f"{sc['onto_player']} -- the player is the one body whose armour "
          f"this server models")
    # 2026-09-23 (skills 43.8): until the observer rule was corrected, the JARIN
    # pair "onto the player" was the HERO's (54 -> 30, Frenzy's 26 and 51 at
    # 122) and LAKESIDE's (48 -> 29) was on no player at all -- its connection
    # has no 0x00E3. Both pass the check above, so it could not see the swap.
    check("54 222 29" in sc["onto_player"] and "54 222 30" not in sc["onto_player"]
          and "48 222 29" in sc["onto_player"],
          "and the JARIN pair onto the connection's own player is the RANGER's "
          "(54 -> 29), not the hero's (54 -> 30); LAKESIDE's 48 -> 29 is the "
          "player's too",
          f"{sorted(sc['onto_player'])}")
    # CASTAI-Z2 (2026-09-29, 20260929T100038). THE PIN FIRST: P2's census on every capture
    # before the tape (Z1 set aside as above) reproduces the 2026-09-28 green run to the
    # digit under the new classes -- 15 pairs over 85 hits, the four multi-valued pairs,
    # the two penalty splits, the one two-hit pair, the four pairs onto the player -- and
    # the classes set aside NOTHING there: the old numbers are unmoved by construction.
    # P3's swing pairs at the pin are pinned too (28): a SWING is never set aside by the
    # classes (`counted`), and a first cut that classified swings moved this number.
    sc_pin = spellhitjoin.score([r for r in rows_pin if r["capture"] != ZAISHEN])
    PIN_MULTI = {"54 222 29": [-0.24242, -0.2, -0.17143, -0.16429],
                 "54 222 30": [-0.41803, -0.29286, -0.21311],
                 "48 222 29": [-0.20168, -0.17143], "117 230 25": [-0.1875, -0.13125]}
    check(sc_pin["pairs"] == 15 and sc_pin["pair_hits"] == 85 and sc_pin["multi_valued"] == PIN_MULTI
          and sc_pin["penalty_split"] == {"48 222 29": {140: [-0.17143], 119: [-0.20168]},
                                          "117 230 25": {480: [-0.13125], 336: [-0.1875]}}
          and sc_pin["two_hit_two_valued"] == {"10 186 12": [-0.17658, -0.12973]}
          and sorted(sc_pin["onto_player"]) == ["10 185 11", "117 230 25", "48 222 29", "54 222 29"]
          and sc_pin["payoff_set_aside"] == 0 and sc_pin["converted_set_aside"] == 0
          and sc_pin["ticks_set_aside"] == 12
          and sc_pin["swing_pairs"] == 28 and sc_pin["swing_pairs_3plus"] == 28,
          "THE PIN (every capture before 20260929T100038, Z1 set aside): P2's census under the "
          "2026-09-29 classes reproduces the 2026-09-28 run to the digit -- 15 pairs over 85 "
          "hits, the four multi-valued pairs, the two penalty splits, the one two-hit pair, the "
          "four pairs onto the player, 12 ticks -- the payoff and converted classes set aside "
          "0 rows there, and P3's 28 swing pairs (all >= 3 values) stand: a swing is never set "
          "aside by the classes",
          str({k: sc_pin[k] for k in ("pairs", "pair_hits", "multi_valued", "penalty_split",
                                      "two_hit_two_valued", "payoff_set_aside",
                                      "converted_set_aside", "ticks_set_aside", "swing_pairs")})
          + f"; P3 on the whole corpus (reported): {sc['swing_pairs_3plus']} of {sc['swing_pairs']}")
    # THE TAPE, exact: every word a monk landed in the COMPLETION batch of its Mend Condition
    # 275 / Reversal of Fortune 307 / Balthazar's Aura 272 / Smite Hex 302 / Resurrection
    # Signet 2 is a PAYOFF -- 218 cast rows, keyed by the join to the cause's latest announce
    # AHEAD of the word in wire order (the skill whose completion it rides; every age
    # reproduces that skill's activation: 275 at 0.73-0.76 s, 307 at 0.21-0.27, 272 at
    # 0.99-1.05, 302 at 1.00-1.02, 2 at 3.00-3.02). The 114 onto the observer are every one
    # named 271 (Zealot's Fire) by the wire's own [10, obs, 271]; 79 are those words'
    # siblings (the same cause, the same batch, onto a foe, the only word from that cause
    # onto that body -- twelve of them value singletons on their connection, flagged and
    # pinned by row below); 25 stand on
    # the ally-cast rule with both its witnesses on the connection; and 16 ally-cast-shaped
    # rows the wire could not back are NOT set aside -- they are counted (`unbacked`, the
    # rule's refusal to guess) and pinned exact below. The takers 7 (the observer) / 9 (the
    # Fighter) / 10 (the Mage) / 8 (the Archer). Nothing keys to Drain Enchantment 68: this
    # lane's first cut read the batch's announces ahead of its words and never the targetless
    # 0x009F form, so 18 rows sat under a stale 68 (spellhitjoin's docstring; the arm below).
    # Ten converted +0.0 words (the Mage's Mind Burn x9 and one Fire Storm tick riding the
    # Mage's Aura of Restoration completion, Reversal of Fortune on the monk). With both set
    # aside the tape's P2 is CLEAN: 14 pairs over 74 hits, all Mind Burn, no multi-valued
    # pair, no two-hit pair -- so P2 is scored on it above with every other capture, and a
    # copy under a FUTURE stamp stays clean too.
    pc = spellhitjoin.payoff_census(rows_z2)
    sc_z2 = spellhitjoin.score(rows_z2)
    conv_z2 = collections.Counter((r["cause"], r["skill"]) for r in rows_z2
                                  if r["kind"] == "cast" and r["converted"] and not r["tick"]
                                  and not r["payoff"])
    zero_noheal = [(r["capture"], r["cause"], r["target"]) for r in rows
                   if r["kind"] == "cast" and r["value"] == 0.0 and math.copysign(1, r["value"]) > 0
                   and not r["converted"] and not r["tick"]]
    _port = lambda r: r["connection"].split("->")[0].rsplit(":", 1)[-1]   # noqa: E731
    unbacked_z2 = [(_port(r), r["t"], r["cause"], r["skill"], r["target"], r["value"], r["form"])
                   for r in rows_z2 if r["kind"] == "cast" and r["ally_cast_unbacked"]]
    Z2_UNBACKED = [("62925", 241.45745, 3, 272, 9, -0.03063, "0x009F"),
                   ("62925", 247.710502, 4, 307, 10, -0.05586, "0x00A0"),
                   ("62925", 251.70685, 3, 307, 10, -0.05586, "0x00A0"),
                   ("62925", 252.208386, 4, 307, 10, -0.05586, "0x00A0"),
                   ("62925", 252.714126, 5, 307, 10, -0.05586, "0x00A0"),
                   ("62925", 253.209879, 6, 307, 10, -0.05586, "0x009F"),
                   ("62925", 254.710386, 5, 275, 10, -0.05586, "0x00A0"),
                   ("62925", 255.21082, 4, 275, 10, -0.05586, "0x00A0"),
                   ("62925", 310.220316, 5, 307, 9, -0.02773, "0x00A0"),
                   ("51090", 393.029476, 10, 180, 6, 0.0, "0x009F"),
                   ("51090", 395.051416, 4, 307, 9, -0.06126, "0x00A0"),
                   ("51090", 404.306472, 5, 307, 10, -0.05586, "0x00A0"),
                   ("51090", 426.191138, 10, 184, 4, -0.03651, "0x009F"),
                   ("51199", 531.416546, 5, 302, 9, -0.03063, "0x00A0"),
                   ("51199", 544.675003, 3, 307, 8, -0.02883, "0x00A0"),
                   ("64557", 644.646415, 4, 272, 9, -0.03063, "0x009F")]
    future = [dict(r, capture="20270101T000000") for r in rows_z2]
    sc_future = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future)
    check(pc == {"rows": 218, "by_announced": {275: 95, 307: 56, 272: 37, 302: 24, 2: 6},
                 "named": {271: 114}, "why": {"named": 114, "sibling": 79, "ally-cast": 25},
                 "targets": {7: 114, 9: 99, 10: 3, 8: 2}, "unbacked": 16, "sibling_unbacked": 12}
          and unbacked_z2 == Z2_UNBACKED
          and sum(1 for r in rows if r["kind"] == "cast" and r["skill"] == 68) == 0
          and sc_z2["payoff_set_aside"] == 218 and sc_z2["converted_set_aside"] == 10
          and conv_z2 == {(10, 185): 9, (10, 180): 1} and zero_noheal == []
          and (sc_z2["pairs"], sc_z2["pair_hits"], sc_z2["skills"]) == (14, 74, [185])
          and sc_z2["multi_valued"] == {} and sc_z2["two_hit_two_valued"] == {}
          and set(sc_future["multi_valued"]) - set(sc_future["penalty_split"]) <= PENALTY_SPLIT
          and sc_future["pairs"] == sc_rest["pairs"] + 14,
          "on 20260929T100038 (exact, per tape): 218 cast words are a PAYOFF riding the "
          "COMPLETION batch of the monk's Mend Condition / Reversal of Fortune / Balthazar's "
          "Aura / Smite Hex / Resurrection Signet -- the join's attribution in wire order, 275 "
          "x95, 307 x56, 272 x37, 302 x24, 2 x6, and NOTHING under Drain Enchantment 68 "
          "corpus-wide -- the 114 onto the observer every one named 271 Zealot's Fire by the "
          "wire's [10, obs, 271], 79 their siblings (twelve of them value singletons, flagged), "
          "25 on the ally-cast rule with both "
          "witnesses, and the 16 ally-cast-shaped rows without them COUNTED, not absorbed; 10 "
          "converted +0.0 words (Mind Burn x9, a Fire Storm tick), each with its heal beside "
          "it, and no cast +0.0 anywhere in the corpus without one; with both set aside the "
          "tape's P2 is CLEAN (14 Mind Burn pairs over 74 hits, no multi-valued pair, no "
          "two-hit pair), and its copy under a future stamp leaves P2 holding",
          str((pc, unbacked_z2, sc_z2["converted_set_aside"], dict(conv_z2), zero_noheal,
               (sc_z2["pairs"], sc_z2["pair_hits"], sc_z2["skills"]), sc_z2["multi_valued"],
               sc_future["multi_valued"])))
    # THE SIBLING CLASS, pinned (the round-3 review). Rule (b) is STRUCTURAL -- the same cause
    # and batch as a wire-named word, onto a FOE of the caster, the only word from that cause
    # onto that body in the batch -- and sets a word aside whatever its amount, so the class's
    # (connection, target, value) multiset is pinned exact per tape, and the twelve siblings
    # whose (target, value) is a singleton on their connection (no named / sibling / ally-cast
    # row repeats it) are flagged `sibling_unbacked` and pinned by row. Read in whole points
    # they are the Fighter's 17 and 15 at a maximum that walks off the wire (the Fighter's
    # check below), and counting them everywhere would put two two-hit pairs on the tape --
    # '5 307 9' (17 at 483 and at 531) and '3 307 8' -- for a reader limitation, not a retail
    # fact, reddening the whole-corpus two-hit check above. So (the round-4 review) a flagged
    # sibling is set aside BELOW P2's floor and COUNTED at it (`spellhitjoin.pairs`): the
    # twelve join no pair of three hits on the tape -- asserted here, so the census check's
    # 14 pairs / 74 hits above are P2's reading with them counted -- while three strays of
    # one cause onto one foe reach P2 (ARM 4 (iv) below). On CAST rows the flag is 0 before
    # the tape; three NONE-kind rows before it carry it (20260817T231139 :54071 x2, Z1 :58544
    # -- inert, a none-kind row is never a cast pair's), reported; corpus-wide the flag is
    # REPORTED.
    sib_z2 = collections.Counter((_port(r), r["target"], r["value"]) for r in rows_z2
                                 if r["kind"] == "cast" and r["why"] == "sibling")
    sib_unb_z2 = [(_port(r), r["t"], r["cause"], r["skill"], r["target"], r["value"], r["form"])
                  for r in rows_z2 if r["kind"] == "cast" and r["sibling_unbacked"]]
    sib_unb_corpus = collections.Counter(r["capture"] for r in rows
                                         if r["kind"] == "cast" and r["sibling_unbacked"])
    sib_unb_noncast = collections.Counter((r["capture"], r["kind"]) for r in rows
                                          if r["kind"] != "cast" and r["sibling_unbacked"])
    sib_grp = collections.Counter((r["connection"], r["cause"], r["skill"], r["target"])
                                  for r in rows_z2 if r["kind"] == "cast"
                                  and spellhitjoin.counted(r, flagged=True))
    sib_reach = sorted({(_port(r), r["cause"], r["skill"], r["target"]) for r in rows_z2
                        if r["kind"] == "cast" and r["sibling_unbacked"]
                        and sib_grp[(r["connection"], r["cause"], r["skill"], r["target"])]
                        >= spellhitjoin.P2_MIN_HITS})
    Z2_SIBLINGS = {("51090", 9, -0.0352): 1, ("51090", 9, -0.03448): 3, ("51090", 9, -0.03386): 1,
                   ("51090", 9, -0.0332): 1, ("51090", 9, -0.03202): 1, ("51090", 9, -0.03063): 10,
                   ("51090", 9, -0.03043): 1, ("51090", 9, -0.0293): 1, ("51199", 8, -0.02523): 1,
                   ("51199", 9, -0.03063): 8, ("51199", 10, -0.05586): 1, ("57580", 9, -0.06211): 3,
                   ("57580", 9, -0.0352): 7, ("57580", 9, -0.03063): 10, ("62925", 8, -0.02883): 1,
                   ("62925", 9, -0.0352): 6, ("62925", 9, -0.03448): 5, ("62925", 9, -0.03142): 1,
                   ("62925", 9, -0.03063): 7, ("62925", 9, -0.03043): 1, ("64557", 9, -0.0352): 1,
                   ("64557", 9, -0.03106): 1, ("64557", 9, -0.03063): 6, ("64557", 9, -0.02703): 1}
    Z2_SIB_UNBACKED = [("62925", 271.957575, 3, 307, 9, -0.03043, "0x00A0"),
                       ("62925", 306.457811, 5, 275, 8, -0.02883, "0x00A0"),
                       ("62925", 306.457811, 5, 275, 9, -0.03142, "0x00A0"),
                       ("51090", 417.558964, 5, 307, 9, -0.0352, "0x00A0"),
                       ("51090", 423.558677, 5, 302, 9, -0.03043, "0x00A0"),
                       ("51090", 435.290545, 3, 307, 9, -0.03386, "0x00A0"),
                       ("51090", 437.558725, 6, 2, 9, -0.0332, "0x00A0"),
                       ("51090", 441.291266, 6, 272, 9, -0.0293, "0x009F"),
                       ("51090", 451.804305, 5, 307, 9, -0.03202, "0x009F"),
                       ("51199", 557.166204, 3, 307, 8, -0.02523, "0x009F"),
                       ("64557", 639.151022, 6, 302, 9, -0.02703, "0x00A0"),
                       ("64557", 667.39617, 6, 272, 9, -0.03106, "0x009F")]
    check(dict(sib_z2) == Z2_SIBLINGS and sum(sib_z2.values()) == 79
          and sib_unb_z2 == Z2_SIB_UNBACKED
          and sum(n for cap, n in sib_unb_corpus.items() if cap < ZAISHEN2) == 0
          and sib_reach == [],
          "the SIBLING class on 20260929T100038 (exact, per tape): its 79 rows' (connection, "
          "target, value) multiset -- 76 onto the Fighter 9, 2 onto the Archer 8, 1 onto the "
          "Mage 10 -- and the twelve whose (target, value) is a singleton on the connection, "
          "flagged `sibling_unbacked` and pinned by row (set aside below P2's floor, counted "
          "at it: on the tape none of the twelve joins a pair of three hits, so the tape's P2 "
          "above reads 14 / 74 with them counted); none on a cast row before the tape",
          f"{dict(sib_z2)}; singletons {sib_unb_z2}; flagged cast rows corpus-wide (reported) "
          f"{dict(sib_unb_corpus)}; flagged non-cast rows (reported, inert) "
          f"{dict(sib_unb_noncast)}; flagged rows in a pair of >= {spellhitjoin.P2_MIN_HITS} "
          f"on the tape {sib_reach}")
    # THE FINDING the classes uncover (exact, per tape): Zealot's Fire onto the observer, read
    # at the first maximum the observer held that makes the word whole (F46, current first), is
    # SEVERAL values -- 22 x62 and 38 x31 with their doubles 44 x4 / 76 x3 and fourteen
    # stragglers -- so P2 re-stated onto the payoff's OWN skill would FAIL here as it did for
    # Z1's Mind Burn; and the Fighter below is several values too (17 / 15 and the doubles 30 /
    # 34 at inferred maxima), so the factor between the two amounts (38 / 22 = 1.73; the
    # Fighter's 30 / 17 = 1.76) is NOT the owner's gear. Every one of the four monks lands both
    # 22 and 38 on the observer -- the amount is not the caster's either. The cause is
    # UNMEASURED (the observer's armour and state are off the wire; 38 / 22 = 2^(31/40) fits
    # neither a bare piece, 2^(40/40), nor Frenzy, 2). A FINDING, not absorbed.
    held = collections.defaultdict(set)
    for r in rows_z2:
        if r["maxhp"] is not None:
            held[(r["connection"], r["target"])].add(r["maxhp"])
    zf_pts, zf_unwhole, zf_by_caster = collections.Counter(), [], collections.defaultdict(set)
    for r in rows_z2:
        if r["kind"] == "cast" and r["payoff"] and r["target"] == r["player"]:
            found = None
            for m in [r["maxhp"]] + sorted((x for x in held[(r["connection"], r["target"])]
                                            if x != r["maxhp"]), reverse=True):
                p = None if m is None else -r["value"] * m
                if p is not None and abs(p - round(p)) <= spellhitjoin.INTEGER_EPS:
                    found = int(round(p))
                    break
            if found is None:
                zf_unwhole.append((r["connection"], r["t"], r["cause"], r["value"]))
            else:
                zf_pts[(r["named"], found)] += 1
                zf_by_caster[r["cause"]].add(found)
    check(dict(zf_pts) == {(271, 20): 3, (271, 22): 62, (271, 34): 2, (271, 35): 2, (271, 38): 31,
                           (271, 39): 2, (271, 40): 1, (271, 44): 4, (271, 67): 3, (271, 69): 1,
                           (271, 76): 3}
          and zf_unwhole == []
          and sorted(zf_by_caster) == [3, 4, 5, 6]
          and all({22, 38} <= pts for pts in zf_by_caster.values()),
          "and the FINDING (exact, per tape): the 114 Zealot's Fire words onto the observer, "
          "whole at a maximum it held, are SEVERAL values -- 22 x62, 38 x31, their doubles 44 x4 "
          "and 76 x3, fourteen stragglers -- P2 re-stated onto the payoff's own skill FAILS on "
          "this tape as on Z1's Mind Burn; every one of the four monks lands both 22 and 38, so "
          "the amount is not the caster's; cause UNMEASURED (the observer's armour and state "
          "are off the wire; 38 / 22 = 2^(31/40) is neither a bare piece nor Frenzy; the "
          "Fighter's check below shows the same two-amount shape on a body the owner did not "
          "control)",
          str((dict(sorted(zf_pts.items())), zf_unwhole,
               {c: sorted(v) for c, v in sorted(zf_by_caster.items())})))
    # THE FIGHTER (the round-3 review: this lane's finding used to say the Fighter takes ONE
    # fraction per stretch; it does not). Its 104 payoff-class words (the (b) siblings, the
    # (c) rows and the (c)-unbacked ones onto agent 9) are pinned exact per connection. Its
    # maximum is never on the wire (no property 42 for a henchman), so the whole-point
    # reading is a RECONSTRUCTION, stated so it can be refuted: under the amounts 15 / 17 and
    # their doubles 30 / 34, every fraction is whole at exactly ONE of seven maxima -- 555,
    # 541, 531, 512, 502, 493, 483 -- and at none of the others: 17 x94, 15 x6, 30 x3 (:57580
    # 151.0-151.7, beside 17 at the same 483 nine times) and 34 x1 (:51090 395.051, beside 17
    # at the same 555 twelve times). The observer's OWN maxima (OBSERVED, property 42, pinned
    # per connection) walk the same way -- 480, then 408 on its death, then up in ~10-point
    # steps (418, 427, 437, 446; 355, 365, 374, 394 after a second death) -- which is what a
    # walking maximum looks like on the one body the wire tells. Two amounts ~1.75 apart on
    # BOTH bodies (30 / 17 = 1.76 beside 38 / 22 = 1.73), with doubles on both.
    fighter = {}
    for r in rows_z2:
        if (r["kind"] == "cast" and not r["tick"] and r["target"] == 9
                and (r["payoff"] or r["ally_cast_unbacked"])):
            fighter.setdefault(_port(r), collections.Counter())[r["value"]] += 1
    fighter = {c: dict(sorted(v.items())) for c, v in sorted(fighter.items())}
    FIGHTER_MAXIMA, FIGHTER_AMOUNTS = (555, 541, 531, 512, 502, 493, 483), (15, 17, 30, 34)
    f_read = {(conn, v): [(p, m) for m in FIGHTER_MAXIMA for p in FIGHTER_AMOUNTS
                          if abs(-v * m - p) <= m * 0.000005 + 1e-9]
              for conn, c in fighter.items() for v in c}
    f_amounts = collections.Counter()
    for (conn, v), hits in f_read.items():
        if len(hits) == 1:
            f_amounts[hits[0][0]] += fighter[conn][v]
    obs_walk = {}
    for r in rows_z2:
        if r["maxhp"] is not None and r["target"] == r["player"]:
            obs_walk.setdefault(_port(r), set()).add(r["maxhp"])
    obs_walk = {c: sorted(v, reverse=True) for c, v in sorted(obs_walk.items())}
    check(fighter == {"51090": {-0.06126: 1, -0.0352: 1, -0.03448: 10, -0.03386: 1, -0.0332: 1,
                                -0.03202: 1, -0.03063: 12, -0.03043: 1, -0.0293: 1},
                      "51199": {-0.03063: 11},
                      "57580": {-0.06211: 3, -0.0352: 9, -0.03063: 11},
                      "62925": {-0.0352: 6, -0.03448: 5, -0.03142: 1, -0.03063: 8, -0.03043: 1,
                                -0.02773: 1},
                      "64557": {-0.0352: 2, -0.03106: 1, -0.03063: 15, -0.02703: 1}}
          and all(len(h) == 1 for h in f_read.values())
          and dict(f_amounts) == {17: 94, 15: 6, 30: 3, 34: 1}
          and obs_walk == {"51090": [480, 427, 418, 408, 394, 374, 365, 355],
                           "51199": [480, 446, 437, 427, 408, 374], "57580": [480, 408],
                           "62925": [480, 418, 408, 403, 394], "64557": [480, 418, 408]},
          "and the FIGHTER (exact, per tape): its 104 Zealot's Fire words are SEVERAL fractions "
          "per connection, pinned; read as whole points (RECONSTRUCTION -- its maximum is never "
          "on the wire) every fraction is 15 / 17 / 30 / 34 at exactly one of seven inferred "
          "maxima (555, 541, 531, 512, 502, 493, 483): 17 x94, 15 x6, 30 x3 beside 17 at the "
          "same 483, 34 x1 beside 17 at the same 555 -- the observer's ~1.7x is not the owner's "
          "gear; the observer's OWN maxima (OBSERVED) walk 480 -> 408 on a death, then up in "
          "~10-point steps, per connection exact",
          str((fighter, {k: v for k, v in f_read.items()}, dict(f_amounts), obs_walk)))
    # KNOWN-BAD ARM (exact, per tape): the reader before the classes -- `classify=False` --
    # counts the same rows as the announced skill's, and on the tape alone P2 shows nine
    # multi-valued pairs beyond the penalty rule (six of them the monks' Zealot's Fire under
    # 275 / 307 onto the Fighter, three the Mage's Mind Burn with its +0.0) and seventeen
    # two-hit pairs beyond the named one; and the converted rule is a SIGNATURE, not "drop
    # every zero": a +0.0 planted WITHOUT its heal stands as a second value. A vault without
    # the tape FAILS here by name (conv_row None) and the run goes on.
    arm = spellhitjoin.score(rows_z2, classify=False)
    arm_multi = sorted(set(arm["multi_valued"]) - set(arm["penalty_split"]))
    conv_row = next((r for r in rows_z2 if r["kind"] == "cast" and r["converted"]
                     and r["skill"] == 185 and not r["payoff"]), None)
    mates = [r for r in rows_z2 if conv_row is not None and r["kind"] == "cast"
             and not r["converted"] and not r["payoff"]
             and (r["connection"], r["cause"], r["skill"], r["target"])
             == (conv_row["connection"], conv_row["cause"], conv_row["skill"], conv_row["target"])]
    planted = spellhitjoin.score([dict(r, capture="SYNTHETIC-INJ") for r in mates[:3]]
                                 + ([dict(conv_row, capture="SYNTHETIC-INJ", converted=False)]
                                    if conv_row is not None else []))
    check(arm_multi == ["10 185 3", "10 185 5", "10 185 6", "3 275 9", "3 307 9", "4 275 9",
                        "5 275 9", "5 307 9", "6 275 9"]
          and sorted(arm["two_hit_two_valued"]) == ["3 272 7", "3 275 7", "3 275 9", "3 307 7",
                                                    "3 307 8", "4 275 9", "4 307 7", "4 307 9",
                                                    "5 275 7", "5 307 7", "5 307 9", "6 272 7",
                                                    "6 272 9", "6 275 7", "6 275 9", "6 307 7",
                                                    "6 307 9"]
          and arm["payoff_set_aside"] == 218 and arm["converted_set_aside"] == 10
          and conv_row is not None and len(mates) >= 3 and len(planted["multi_valued"]) == 1
          and 0.0 in next(iter(planted["multi_valued"].values())),
          "KNOWN-BAD ARM (exact, per tape): `classify=False` -- the reader before 2026-09-29 -- "
          "counts the payoffs and the converted zeros as the announced skill's, and the tape "
          "alone shows nine multi-valued pairs past the penalty rule and seventeen two-hit pairs "
          "past the named one; a +0.0 planted WITHOUT its heal beside it is NOT set aside and "
          "stands as a second value (the class is a signature, not a zero filter); a vault "
          "without the tape fails here by name",
          str((arm_multi, sorted(arm["two_hit_two_valued"]), conv_row is not None,
               planted["multi_valued"])))
    # KNOWN-BAD ARM 2 (the review of this lane's first cut): the announce read AHEAD of the
    # batch's words and blind to the targetless 0x009F form -- `ANNOUNCE_BY_ORDER = False`.
    # On the tape it keys 18 counted rows to Drain Enchantment 68 (a stale targeted announce
    # claiming words that ride a Balthazar's Aura / self-cast completion the reader never
    # saw) and reads 5 cast words at age 0.0 (an announce later in the batch claiming a word
    # ahead of it); read in order, no cast row on the whole corpus keys to 68 and none sits
    # at age 0.0. At the pin the arm and the reader agree on every cast row's skill and age
    # and on P2's whole census; the one number the order moves before the tape is a
    # PROJECTILE hit in 12b's non-witness Fireball group (20260817T231139 :54071, caster 14
    # onto 9: its single 107-point hit now keys to the caster's Aura of Restoration
    # self-announce that followed the launch -- the same "latest announce" rule the reader
    # always had for a projectile in flight, now seeing both forms; the RB2 witness and 12b's
    # floor are untouched), asserted exact so the movement is read, not absorbed.
    spellhitjoin.ANNOUNCE_BY_ORDER = False
    try:
        rows_arm = spellhitjoin.census()
    finally:
        spellhitjoin.ANNOUNCE_BY_ORDER = True
    arm_z2 = [r for r in rows_arm if r["capture"] == ZAISHEN2]
    arm_pin = [r for r in rows_arm if r["capture"] < ZAISHEN2 and r["capture"] != ZAISHEN]
    pin_cast = [(r["capture"], r["connection"], r["t"], r["target"], r["cause"], r["skill"], r["age"])
                for r in rows_pin if r["capture"] != ZAISHEN and r["kind"] == "cast"]
    pin_cast_arm = [(r["capture"], r["connection"], r["t"], r["target"], r["cause"], r["skill"], r["age"])
                    for r in arm_pin if r["kind"] == "cast"]
    lb_pin = spellhitjoin.location_buckets([r for r in rows_pin if r["capture"] != ZAISHEN])
    lb_arm = spellhitjoin.location_buckets(arm_pin)
    lb_moved = {k: (lb_arm.get(k), lb_pin.get(k)) for k in set(lb_arm) | set(lb_pin)
                if lb_arm.get(k) != lb_pin.get(k)}
    lb_moved = {(k[0], k[1].split("->")[0].rsplit(":", 1)[-1]) + k[2:]: v for k, v in lb_moved.items()}
    check(len(rows_arm) == len(rows)
          and spellhitjoin.payoff_census(arm_z2)["by_announced"].get(68) == 18
          and sum(1 for r in arm_z2 if r["kind"] == "cast" and r["skill"] == 68
                  and spellhitjoin.counted(r, False)) == 18
          and sum(1 for r in arm_z2 if r["kind"] == "cast" and r["age"] == 0.0) == 5
          and sum(1 for r in rows_z2 if r["kind"] == "cast" and r["age"] == 0.0) == 0
          and len(pin_cast) >= 100 and pin_cast == pin_cast_arm
          and spellhitjoin.score(arm_pin) == sc_pin
          and lb_moved == {("20260817T231139", "54071", 14, 186, 9): ({39: 1, 53: 7, 107: 1},
                                                                     {39: 1, 53: 7})}
          and spellhitjoin.ANNOUNCE_BY_ORDER,
          "KNOWN-BAD ARM 2 (exact, per tape): the announce read ahead of the batch's words and "
          "blind to the 0x009F form (this lane's first cut) keys 18 counted rows on the tape to "
          "Drain Enchantment 68 and reads 5 cast words at age 0.0; in wire order no cast row "
          "corpus-wide keys to 68 or sits at age 0.0; at the pin every cast row's skill and age "
          "and P2's whole census are identical under both, and the one number the order moves "
          "before the tape is 12b's non-witness Fireball group's single 107-point projectile "
          "hit, asserted exact",
          str((spellhitjoin.payoff_census(arm_z2)["by_announced"],
               sum(1 for r in arm_z2 if r["kind"] == "cast" and r["age"] == 0.0),
               len(pin_cast), pin_cast == pin_cast_arm, lb_moved)))
    # THE SCOPE of the wire-order read before the tape (the round-3 review: 'one number' is
    # not 'one row'). The cast rows are untouched at the pin (asserted above), but 74 NON-cast
    # rows change their skill key -- 69 none-kind (49 from None to a skill under a 0x009F
    # self-announce the first cut never saw, 1 under a 0x00A0, 9 from one skill to another
    # under a 0x009F, 8 under a 0x00A0, 2 to None) and 5 swings from None to a skill under a
    # 0x009F -- on five tapes: 20260817T231139 57 none + 4 swing, 20260819T132414 2,
    # 20260913T210901 7, 20260914T005758 3, 20260914T180058 1 swing; Z1 adds 37 none + 6
    # swing. (Counted per ROW: 20260817T231139 :54071 633.997 is a twin pair -- two identical
    # words onto 12 from 8 -- one key, two rows; by key it is 73 / 68 / 56 / 48.) A none-kind
    # row re-keyed onto a self-announce is a word some 58 ms after an Aura of Restoration that
    # deals no damage -- the 'latest announce' limitation's real extent; pinned exact so the
    # movement is read as rows. (The one asserted number it moves is the location bucket
    # above; P3's whole-corpus count reads 35 of 35, reported at THE PIN.)
    _rk = lambda r: (r["capture"], r["connection"], r["t"], r["prop"], r["target"],   # noqa: E731
                     r["cause"], r["value"])
    arm_skill = {_rk(r): r["skill"] for r in rows_arm}
    rekey, rekey_tape, rekey_z1, rekey_cls = (collections.Counter(), collections.Counter(),
                                              collections.Counter(), collections.Counter())
    for r in rows:
        if r["capture"] >= ZAISHEN2 or _rk(r) not in arm_skill or arm_skill[_rk(r)] == r["skill"]:
            continue
        if r["capture"] == ZAISHEN:
            rekey_z1[r["kind"]] += 1
            continue
        rekey[r["kind"]] += 1
        rekey_tape[(r["capture"], r["kind"])] += 1
        rekey_cls[(r["kind"], "none" if arm_skill[_rk(r)] is None else "skill",
                   "none" if r["skill"] is None else "skill", r["form"])] += 1
    check(dict(rekey) == {"none": 69, "swing": 5}
          and dict(rekey_tape) == {("20260817T231139", "none"): 57, ("20260817T231139", "swing"): 4,
                                   ("20260819T132414", "none"): 2, ("20260913T210901", "none"): 7,
                                   ("20260914T005758", "none"): 3, ("20260914T180058", "swing"): 1}
          and dict(rekey_z1) == {"none": 37, "swing": 6}
          and all(_rk(r) in arm_skill for r in rows),
          "the SCOPE of the wire-order read at the pin (exact, per row): 0 cast rows, 69 "
          "none-kind rows and 5 swings change their skill key before 20260929T100038, on five "
          "tapes as pinned (20260817T231139 57 + 4, 20260819T132414 2, 20260913T210901 7, "
          "20260914T005758 3, 20260914T180058 1); Z1 adds 37 none + 6 swing -- rows keyed onto "
          "a self-announce that deals no damage, the 'latest announce' limitation's real "
          "extent, read as rows",
          f"by kind {dict(rekey)}; by tape {dict(rekey_tape)}; Z1 {dict(rekey_z1)}; by (kind, "
          f"from, to, form) {dict(sorted(rekey_cls.items(), key=str))}")
    # KNOWN-BAD ARM 3 (the ally-cast bound, rule (c)): five copies of an ally-cast payoff
    # row with ARBITRARY values planted under a future stamp beside the tape's copy are NOT
    # absorbed -- `score` classifies afresh, the values have no witness on that connection,
    # the rows are counted and P2 sees a five-valued pair (red-able); the copy alone is
    # clean (asserted above), and the planted rows swell the unbacked count by exactly five.
    c_row = next((r for r in rows_z2 if r["kind"] == "cast" and r["why"] == "ally-cast"), None)
    inj = [dict(c_row, capture="20270101T000000", value=round(-0.01 * (k + 1), 5),
                t=c_row["t"] + 0.001 * k) for k in range(5)] if c_row is not None else []
    sc_inj = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj)
    inj_key = None if c_row is None else f"{c_row['cause']} {c_row['skill']} {c_row['target']}"
    inj_pc = spellhitjoin.payoff_census(spellhitjoin.classify_payoffs(
        [dict(r) for r in future + inj]))
    check(c_row is not None
          and sc_inj["multi_valued"].get(inj_key) == [-0.05, -0.04, -0.03, -0.02, -0.01]
          and inj_key not in sc_future["multi_valued"]
          and sc_inj["payoff_set_aside"] == sc_future["payoff_set_aside"]
          and inj_pc["unbacked"] == 16 + 5 and inj_pc["rows"] == 218,
          "KNOWN-BAD ARM 3: five ally-cast-shaped rows with arbitrary values planted under a "
          "future stamp beside the tape's copy are COUNTED (no witness for the values on that "
          "connection), P2 sees the five-valued pair, the payoff count does not move and the "
          "unbacked count grows by exactly five -- rule (c) cannot absorb a stray value",
          str((inj_key, sc_inj["multi_valued"].get(inj_key), sc_inj["payoff_set_aside"],
               sc_future["payoff_set_aside"], inj_pc["unbacked"])))
    # KNOWN-BAD ARM 4 (the sibling bound, rule (b), the round-3 and round-4 reviews):
    # sibling-shaped rows with ARBITRARY values planted under a future stamp beside the tape's
    # copy. A planted row's `foe` (and with it `ally_cast`) is DERIVED from the tape's own
    # token reading, never hand-set -- `_foe_of`: events() set `foe` on every row between the
    # two bodies (the tokens differ symmetrically), and an ally-cast row of the cause names
    # the ally as its announce's target (the same token); the token computation itself is
    # exercised by the synthetic events() check below (a word onto the caster's ally beside a
    # named word). (i) Five copies of the tape's first sibling (:57580 127.488, cause 4's
    # Smite Hex 302 onto the Fighter 9, the reviewer's injection) in its own batch: six words
    # from that cause onto that body in one batch, so none is a sibling (UNIQUE); the real one
    # is re-read as (c) -- its value is witnessed -- and the five planted are not (no witness
    # for -0.01..-0.05): COUNTED, P2 sees the five-valued pair, the payoff count does not
    # move, the (c)-unbacked count grows by five. (ii) One copy in each of five OTHER sibling
    # batches of the same cause onto the same body: the same, and P2 sees a three-valued pair
    # under 275. (iii) One copy onto the caster's ALLY (a monk the cause announced a cast at)
    # in the first batch, its `foe` the tape's reading (False): not a sibling (FOE), not
    # ally-cast-shaped, counted with no flag. Dropping UNIQUE or FOE from rule (b) goes red
    # here. (iv), the shape (b) DOES read as a sibling, is the next check.
    def _foe_of(cause, target):
        seen = {r["foe"] for r in rows_z2 if {r["cause"], r["target"]} == {cause, target}}
        if len(seen) == 1:
            return seen.pop()
        if any(r["ally_cast"] and r["cause"] == cause and r["ann_target"] == target
               for r in rows_z2):
            return False
        return None
    s_row = min((r for r in rows_z2 if r["kind"] == "cast" and r["why"] == "sibling"),
                key=lambda r: r["t"], default=None)
    inj4 = [dict(s_row, capture="20270101T000000", value=round(-0.01 * (k + 1), 5),
                 t=s_row["t"] + 0.001 * k) for k in range(5)] if s_row is not None else []
    key4 = None if s_row is None else f"{s_row['cause']} {s_row['skill']} {s_row['target']}"
    sc_inj4 = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj4)
    cl4 = spellhitjoin.classify_payoffs([dict(r) for r in future + inj4])
    pl4 = [(r["why"], r["ally_cast_unbacked"], r["sibling_unbacked"]) for r in cl4
           if r["value"] in {x["value"] for x in inj4} and r["t"] in {x["t"] for x in inj4}]
    real4 = [r["why"] for r in cl4 if s_row is not None and r["t"] == s_row["t"]
             and r["value"] == s_row["value"] and r["cause"] == s_row["cause"]
             and r["target"] == s_row["target"]]
    pc4 = spellhitjoin.payoff_census(cl4)
    others = sorted((r for r in rows_z2 if s_row is not None and r["kind"] == "cast"
                     and r["why"] == "sibling" and r["connection"] == s_row["connection"]
                     and r["cause"] == s_row["cause"] and r["target"] == s_row["target"]
                     and r["t"] != s_row["t"]), key=lambda r: r["t"])[:5]
    inj5 = [dict(r, capture="20270101T000000", value=round(-0.011 * (k + 1), 5), t=r["t"] + 0.001)
            for k, r in enumerate(others)]
    sc_inj5 = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj5)
    cl5 = spellhitjoin.classify_payoffs([dict(r) for r in future + inj5])
    pl5 = [(r["why"], r["ally_cast_unbacked"]) for r in cl5
           if r["value"] in {x["value"] for x in inj5} and r["cause"] == (s_row or {}).get("cause")]
    new5 = {k: v for k, v in sc_inj5["multi_valued"].items() if k not in sc_future["multi_valued"]}
    ally = next((r["ann_target"] for r in rows_z2 if s_row is not None and r["kind"] == "cast"
                 and r["cause"] == s_row["cause"] and r["ally_cast"]
                 and r["ann_target"] != r["cause"]), None)
    foe6 = None if s_row is None or ally is None else _foe_of(s_row["cause"], ally)
    inj6 = ([dict(s_row, capture="20270101T000000", target=ally, foe=foe6,
                  ally_cast=s_row["ally_cast"] and bool(foe6), value=-0.02)]
            if s_row is not None and ally is not None else [])
    sc_inj6 = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj6)
    pl6 = [(r["why"], r["payoff"], r["ally_cast_unbacked"], r["sibling_unbacked"])
           for r in spellhitjoin.classify_payoffs([dict(r) for r in future + inj6])
           if inj6 and r["t"] == s_row["t"] and r["target"] == ally and r["value"] == -0.02]
    check(s_row is not None and key4 == "4 302 9"
          and sc_inj4["multi_valued"].get(key4) == [-0.05, -0.04, -0.03, -0.02, -0.01]
          and key4 not in sc_future["multi_valued"]
          and pl4 == [(None, True, False)] * 5 and real4 == ["ally-cast"]
          and sc_inj4["payoff_set_aside"] == sc_future["payoff_set_aside"]
          and pc4["unbacked"] == 16 + 5 and pc4["sibling_unbacked"] == 12
          and len(others) == 5 and pl5 == [(None, True)] * 5
          and new5 == {"4 275 9": [-0.055, -0.033, -0.022]}
          and sc_inj5["payoff_set_aside"] == sc_future["payoff_set_aside"]
          and ally is not None and foe6 is False and pl6 == [(None, False, False, False)]
          and sc_inj6["payoff_set_aside"] == sc_future["payoff_set_aside"],
          "KNOWN-BAD ARM 4: sibling-shaped rows with arbitrary values planted under a future "
          "stamp beside the tape's copy are COUNTED -- five in the first sibling's own batch "
          "(six words from one cause onto one body: none a sibling, the real one re-read as an "
          "ally-cast with its witnessed value, the five unbacked; P2 sees the five-valued pair "
          "'4 302 9', the payoff count unmoved, the unbacked count +5), one in each of five other "
          "sibling batches of the same cause onto the same body (P2 sees the three-valued pair "
          "under 275), and one onto the caster's ALLY, its `foe` the tape's own token reading "
          "(not a sibling, not ally-cast-shaped, no flag) -- rule (b) cannot absorb a second "
          "word onto a body nor a word onto an ally",
          str((key4, sc_inj4["multi_valued"].get(key4), pl4, real4, sc_inj4["payoff_set_aside"],
               sc_future["payoff_set_aside"], pc4["unbacked"], pc4["sibling_unbacked"],
               len(others), pl5, new5, ally, foe6, pl6)))
    # KNOWN-BAD ARM 4 (iv) (the round-4 review): the shape rule (b) DOES read as a sibling --
    # a stray onto a foe the cause never otherwise hits, alone in an (a)-batch, its value a
    # singleton on the connection -- planted THREE times, one per (a)-batch, onto the Archer 8
    # from cause 4 under Mend Condition 275 on :57580 (the tape's three such batches; cause 4
    # lands nothing on 8 anywhere on the tape and the (8, value) pool on :57580 is empty; `foe`
    # is the tape's reading of 8 and 4, True). Rule (b) flags every one `sibling_unbacked`, and
    # P2 -- counting the flagged at its floor -- SEES the three-valued pair '4 275 8' (the
    # Archer's maximum is never on the wire, so no penalty split absorbs it): the whole-corpus
    # P2 check's set would be exactly that pair. The two-hit check does not move, the payoff
    # count grows by three (they ARE set aside there), the flag by three. TWO of the three are
    # the residual: set aside below the floor, reported, no pair. Dropping the flagged rows from
    # `pairs` at P2's floor goes red here.
    f57 = [r for r in rows_z2 if _port(r) == "57580"]
    slots7 = sorted((r for r in f57 if r["kind"] == "cast" and r["why"] == "named"
                     and r["cause"] == 4 and r["skill"] == 275
                     and not any(x["batch"] == r["batch"] and x["cause"] == 4 and x["target"] == 8
                                 for x in f57)), key=lambda r: r["t"])
    foe7 = _foe_of(4, 8)
    inj7 = [dict(r, capture="20270101T000000", target=8, named=None, foe=foe7,
                 ally_cast=r["ally_cast"] and bool(foe7), value=round(-0.07 - 0.01 * k, 5),
                 t=r["t"] + 0.0005) for k, r in enumerate(slots7[:3])]
    key7 = "4 275 8"
    sc_inj7 = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj7)
    sc_inj8 = spellhitjoin.score([r for r in rows if r["capture"] != ZAISHEN] + future + inj7[:2])
    cl7 = spellhitjoin.classify_payoffs([dict(r) for r in future + inj7])
    pl7 = [(r["why"], r["sibling_unbacked"]) for r in cl7
           if r["target"] == 8 and r["value"] in {x["value"] for x in inj7}
           and r["t"] in {x["t"] for x in inj7}]
    pc7 = spellhitjoin.payoff_census(cl7)
    pc8 = spellhitjoin.payoff_census(spellhitjoin.classify_payoffs(
        [dict(r) for r in future + inj7[:2]]))
    p2_set7 = sorted(set(sc_inj7["multi_valued"]) - set(sc_inj7["penalty_split"]) - PENALTY_SPLIT)
    check(len(slots7) == 3 and foe7 is True and len({r["batch"] for r in inj7}) == 3
          and not any(r["cause"] == 4 and r["target"] == 8 for r in rows_z2)
          and pl7 == [("sibling", True)] * 3
          and sc_inj7["multi_valued"].get(key7) == [-0.09, -0.08, -0.07]
          and key7 not in sc_inj7["penalty_split"] and key7 not in sc_future["multi_valued"]
          and p2_set7 == [key7]
          and (sc_inj7["pairs"], sc_inj7["pair_hits"])
          == (sc_future["pairs"] + 1, sc_future["pair_hits"] + 3)
          and sc_inj7["two_hit_two_valued"] == sc_future["two_hit_two_valued"]
          and sc_inj7["payoff_set_aside"] == sc_future["payoff_set_aside"] + 3
          and pc7["sibling_unbacked"] == 12 + 3 and pc7["rows"] == 218 + 3
          and key7 not in sc_inj8["multi_valued"] and key7 not in sc_inj8["two_hit_two_valued"]
          and (sc_inj8["pairs"], sc_inj8["pair_hits"]) == (sc_future["pairs"], sc_future["pair_hits"])
          and pc8["sibling_unbacked"] == 12 + 2,
          "KNOWN-BAD ARM 4 (iv): three sibling-shaped strays with arbitrary values onto a foe the "
          "cause never otherwise hits (the Archer 8 from cause 4 under 275 on :57580), one per "
          "(a)-batch, under a future stamp -- rule (b) reads every one as a sibling and flags it, "
          "and P2 counts the flagged at its floor: the three-valued pair '4 275 8' is SEEN (the "
          "whole-corpus P2 set would be exactly it), the two-hit check unmoved, the payoff count "
          "+3, the flag +3; two of the three are the residual, set aside and reported (+2, no "
          "pair)",
          str((len(slots7), foe7, pl7, sc_inj7["multi_valued"].get(key7), p2_set7,
               (sc_inj7["pairs"] - sc_future["pairs"], sc_inj7["pair_hits"] - sc_future["pair_hits"]),
               sc_inj7["two_hit_two_valued"] == sc_future["two_hit_two_valued"],
               sc_inj7["payoff_set_aside"] - sc_future["payoff_set_aside"], pc7["sibling_unbacked"],
               key7 in sc_inj8["multi_valued"], key7 in sc_inj8["two_hit_two_valued"],
               pc8["sibling_unbacked"])))
    # THE SIGNATURES ON SYNTHETIC BATCHES, through `events` itself (the review: nothing had
    # exercised the heal half of `converted`, nor the foe clause of `ally_cast`). Batches a
    # second apart (healjoin.batches splits at 50 ms); v[0] is the header the reader skips.
    _CR, _INT, _INT_T, _FLT = 0x0020, 0x009F, 0x00A0, 0x00A3
    _bits = lambda f: struct.unpack("<I", struct.pack("<f", f))[0]                  # noqa: E731
    _create = lambda agent, alleg: (_CR, [_CR, agent, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0, alleg])   # noqa: E731

    def _seq(items):
        return [(i, t, op, v) for i, (t, (op, v)) in enumerate(items)]
    C, B, F = 3, 5, 7                    # caster, its ally, a foe
    synth = _seq([
        (0.0, _create(C, 1)), (0.001, _create(B, 1)), (0.002, _create(F, 2)),
        # +0.0 onto the foe, NO heal beside it: not converted
        (10.0, (_INT_T, [_INT_T, 60, C, F, 185])),
        (11.0, (_INT, [_INT, 58, C, 0])), (11.001, (_FLT, [_FLT, 16, F, C, 0x00000000])),
        # +0.0 with a positive 55 onto the same target in the batch: converted
        (20.0, (_INT_T, [_INT_T, 60, C, F, 185])),
        (21.0, (_INT, [_INT, 58, C, 0])), (21.001, (_FLT, [_FLT, 55, F, F, _bits(0.05)])),
        (21.002, (_FLT, [_FLT, 16, F, C, 0x00000000])),
        # -0.0 (the graze) with a heal beside it: not converted
        (30.0, (_INT_T, [_INT_T, 60, C, F, 185])),
        (31.0, (_INT, [_INT, 58, C, 0])), (31.001, (_FLT, [_FLT, 55, F, F, _bits(0.05)])),
        (31.002, (_FLT, [_FLT, 16, F, C, 0x80000000])),
    ])
    s_rows = spellhitjoin.events(synth)
    check([(r["kind"], r["skill"], r["converted"]) for r in s_rows]
          == [("cast", 185, False), ("cast", 185, True), ("cast", 185, False)],
          "the CONVERTED signature through `events` on synthetic batches: a +0.0 cast word is "
          "converted ONLY with a positive property-55 heal onto its target beside it -- without "
          "the heal it is not (a plain zero filter goes red here), and the -0.0 graze beside a "
          "heal is not either",
          str([(r["kind"], r["skill"], r["value"], r["converted"]) for r in s_rows]))
    x, y = _bits(-0.03), _bits(-0.07)
    F2 = 9                               # a second foe
    synth2 = _seq([
        (0.0, _create(C, 1)), (0.001, _create(B, 1)), (0.002, _create(F, 2)),
        (0.003, _create(F2, 2)),
        # 1: an ally-cast whose completion the wire names as another skill's on the foe
        #    (a); the word onto the ALLY beside it is NOT a sibling (the FOE clause of (b),
        #    the round-3 review) -- counted, no flag
        (10.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (10.75, (_INT, [_INT, 10, F, 271])), (10.751, (_FLT, [_FLT, 16, F, C, x])),
        (10.752, (_FLT, [_FLT, 16, B, C, x])), (10.753, (_INT, [_INT, 58, C, 0])),
        # 2: the same value onto the FOE under the same ally-cast, unnamed: (c), backed
        (20.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (20.75, (_FLT, [_FLT, 16, F, C, x])), (20.751, (_INT, [_INT, 58, C, 0])),
        # 3: the same value onto the ALLY: the foe clause refuses (c)
        (30.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (30.75, (_FLT, [_FLT, 16, B, C, x])), (30.751, (_INT, [_INT, 58, C, 0])),
        # 4: an unwitnessed value onto the foe under the ally-cast: unbacked, counted
        (40.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (40.75, (_FLT, [_FLT, 16, F, C, y])), (40.751, (_INT, [_INT, 58, C, 0])),
        # 5: a FOE-targeted cast's own word: never (c)
        (50.0, (_INT_T, [_INT_T, 60, C, F, 186])),
        (51.0, (_FLT, [_FLT, 16, F, C, x])), (51.001, (_INT, [_INT, 58, C, 0])),
        # 6: a self-targeted (0x009F) cast of an UNWITNESSED skill: its word onto the foe
        #    is unbacked and counted -- a PBAoE's damage is not erased
        (60.0, (_INT, [_INT, 60, C, 288])),
        (60.75, (_FLT, [_FLT, 16, F, C, x])), (60.751, (_INT, [_INT, 58, C, 0])),
        # 7: an (a)-batch with TWO words from the cause onto the second foe: neither is a
        #    sibling (the UNIQUE clause of (b)) -- both ally-cast-shaped, unwitnessed, counted
        (70.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (70.75, (_INT, [_INT, 10, F, 271])), (70.751, (_FLT, [_FLT, 16, F, C, x])),
        (70.752, (_FLT, [_FLT, 16, F2, C, x])), (70.753, (_FLT, [_FLT, 16, F2, C, y])),
        (70.754, (_INT, [_INT, 58, C, 0])),
        # 8: an (a)-batch with ONE word onto the second foe, its value a singleton on the
        #    connection: a sibling, flagged `sibling_unbacked`, set aside
        (80.0, (_INT_T, [_INT_T, 60, C, B, 275])),
        (80.75, (_INT, [_INT, 10, F, 271])), (80.751, (_FLT, [_FLT, 16, F, C, x])),
        (80.752, (_FLT, [_FLT, 16, F2, C, _bits(-0.05)])), (80.753, (_INT, [_INT, 58, C, 0])),
    ])
    s2 = [(r["target"], r["skill"], r["form"], r["ally_cast"], r["why"], r["ally_cast_unbacked"],
           r["sibling_unbacked"])
          for r in spellhitjoin.events(synth2)]
    check(s2 == [(F, 275, "0x00A0", True, "named", False, False),
                 (B, 275, "0x00A0", False, None, False, False),
                 (F, 275, "0x00A0", True, "ally-cast", False, False),
                 (B, 275, "0x00A0", False, None, False, False),
                 (F, 275, "0x00A0", True, None, True, False),
                 (F, 186, "0x00A0", False, None, False, False),
                 (F, 288, "0x009F", True, None, True, False),
                 (F, 275, "0x00A0", True, "named", False, False),
                 (F2, 275, "0x00A0", True, None, True, False),
                 (F2, 275, "0x00A0", True, None, True, False),
                 (F, 275, "0x00A0", True, "named", False, False),
                 (F2, 275, "0x00A0", True, "sibling", False, True)],
          "the PAYOFF rule through `events` on synthetic batches: (a) the wire's name, (b) its "
          "sibling onto a FOE and the only word from the cause onto that body (onto the "
          "caster's ALLY it is counted; two words onto one body are both counted -- dropping "
          "either clause goes red here; a lone singleton value is a sibling flagged unbacked), "
          "(c) the ally-cast's word onto a FOE only with both witnesses on the connection -- "
          "onto the caster's ALLY the foe clause refuses it, an unwitnessed value is unbacked "
          "and counted, a foe-targeted cast's own word is never (c), and a self-targeted 0x009F "
          "cast of an unwitnessed skill keeps its word (a PBAoE is not erased)",
          str(s2))
    # THE OTHER CHANNEL (exact per tape, pin-exact before it): the wire names the observer's
    # damage ahead of the word with [10, obs, S], and on this tape the holy words -- Smite
    # Hex 302 x11, Balthazar's Aura 272 x64, Scourge Healing 251 x6 -- ride property 55 with a
    # NEGATIVE fraction, never 16 / 17, while Zealot's Fire's fire damage (271 x115) rides 16.
    # Before the tape the 55 side held four skills (the Blood Magic trio 102 / 133 / 143 --
    # life stealing -- and the PvE skill 2809), and on the whole corpus no skill named by a
    # [10] is on both channels: what ignores armour (holy, life stealing) goes out on 55, what
    # respects it (fire, lightning, a swing) on 16 / 17 -- RECONSTRUCTION; every 55 word here
    # is holy or a life steal, so holy-vs-armour-ignoring is UNDISCRIMINATED on this corpus.
    nw_z2, nw_pin, nw_all = collections.Counter(), collections.Counter(), collections.Counter()
    for stamp, _conn, d in named_census:
        for k, n in d.items():
            nw_all[k] += n
            if stamp == ZAISHEN2:
                nw_z2[k] += n
            elif stamp < ZAISHEN2:
                nw_pin[k] += n
    on55 = {s for (s, p) in nw_all if p == 55}
    on16 = {s for (s, p) in nw_all if p in (16, 17)}
    check(dict(nw_z2) == {(271, 16): 115, (251, 55): 6, (272, 55): 64, (302, 55): 11}
          and {s: n for (s, p), n in nw_pin.items() if p == 55} == {102: 1, 133: 1, 143: 3, 2809: 8}
          and len(on16) >= 10 and len(on55) >= 5 and not (on55 & on16),
          "the wire's own naming, [10, obs, S] ahead of the word: on 20260929T100038 (exact) the "
          "holy words -- Smite Hex 302 x11, Balthazar's Aura 272 x64, Scourge Healing 251 x6 -- "
          "ride property 55 with a NEGATIVE fraction and Zealot's Fire's 271 x115 rides 16; at "
          "the pin the 55 side is exactly {102: 1, 133: 1, 143: 3, 2809: 8}; and corpus-wide no "
          "named skill is on both channels (>= 10 on 16 / 17, >= 5 on 55) -- what ignores armour "
          "goes out as a negative health gain (RECONSTRUCTION; this server sends Holy Strike on 16)",
          str((dict(nw_z2), {s: n for (s, p), n in nw_pin.items() if p == 55}, sorted(on16),
               sorted(on55))))
    check(sc["swing_pairs"] >= 5 and sc["swing_pairs_3plus"] == sc["swing_pairs"],
          "P3 CONTROL: every swing pair with >= 10 hits shows >= 3 values",
          f"{sc['swing_pairs_3plus']} of {sc['swing_pairs']} (min distinct "
          f"{sc['swing_min_distinct']}) -- the instrument sees a weapon's "
          f"range where there is one")
    check(sc["mind_burn_twins"] >= 10,
          "P4 Mind Burn's conditional second packet is a twin 16 in one batch",
          f"{sc['mind_burn_twins']} -- WIKI (GWW, \"Mind Burn\"): an "
          f"additional 15..60 if the caster has more Energy; the wire carries "
          f"it as a second identical packet, not a doubled one")

    print("\n12b. the corpus: a spell's LOCATION ROLL (spellhitjoin."
          "location_buckets, RUN-SKILLS-RB2)")
    # One caster's projectile spell onto one target, in whole points. With
    # five equal pieces it is ONE bucket (P2's world); the RB2 tape took three
    # pieces off and the same Lightning Orb fills TWO, 2^(60/40) apart.
    lb = spellhitjoin.location_buckets(rows)
    witnesses = []
    for k, pts in lb.items():
        vals = sorted(pts)
        for lo in vals:
            for hi in vals:
                if hi > lo and pts[lo] >= 4 and pts[hi] >= 2 \
                        and abs(hi / lo - 2 ** 1.5) / 2 ** 1.5 <= 0.015:
                    witnesses.append((" ".join(map(str, k[:1] + k[2:])),
                                      lo, pts[lo], hi, pts[hi]))
    check(len(witnesses) >= 1,
          "SKILLS-LR a projectile spell from one caster onto one target lands "
          "in TWO whole-point buckets 2^(60/40) apart -- an armoured piece and "
          "a bare one; spells roll a hit location",
          f"{witnesses} of {len(lb)} projectile groups -- 20260917T090355, "
          f"Lightning Orb 229 from the Master of Lightning: 101 and 286. The "
          f"single rating SKILLS-FA shipped (studies/skills 43) is REFUTED; "
          f"43.4's caveat -- equal pieces cannot tell -- was the whole story")


    print("\n12c. the corpus: hexjoin -- Incendiary Bonds' end effect, Mind Burn's per-foe "
          "twin, how a hex lands on any body, the conditions (studies/skills 61)")
    # The committed port of the DESKWORK-D6 tape lane's join, its predictions as the lane
    # REGISTERED them: three FAILED as registered (I4, M2, C2) and the reader prints them so,
    # with the corrected readings beside them. This lock is the reader's own verdict plus the
    # witness tape's exact counts (per tape) and the corpus floors.
    import hexjoin
    hc = hexjoin.census()
    hs = hexjoin.score(hc)
    hv = hexjoin.verdicts(hs)
    # THE REGISTRATION'S CORPUS (2026-09-28, CASTAI-Z1): the lane registered on the captures
    # before 20260928T103123 (the Zaishen Challenge). The reading is scored THERE as
    # registered; the whole corpus records what the Zaishen tape FAILED, the re-statement
    # each verdict rests on, and that tape's own exact witness (hexjoin's docstring).
    hcp = hexjoin.upto(hc, ZAISHEN)
    hsp = hexjoin.score(hcp)
    hvp = hexjoin.verdicts(hsp)
    hsz = hexjoin.score(hexjoin.narrow(hc, ZAISHEN))
    hrv = hexjoin.restated_verdicts(hs)
    check(all(hvp.values()) and hsp["refused"] == 0 and hsp["connections"] >= 96
          and not hsp["i4"] and not hsp["m2"] and not hsp["c2"] and hsp["m3"] is None
          and hsp["i4c"] and hsp["m2c"] and hsp["m3c"] and hsp["c2c"],
          "hexjoin's reading HOLDS: every prediction as registered but I4 / M2 / C2 (FAILED as "
          "registered, printed so), their corrected readings hold, M3 is untestable (no Mind "
          "Burn onto the observer) and its M3c holds, the four post-hoc facts hold; 0 refused "
          "(on the corpus it was registered on: the captures before 20260928T103123)",
          str((hvp, hsp["connections"])))
    check([x[:2] for x in hc["set_aside"]] == GAPPED and not hc["declared_not_refused"]
          and hs["refused"] == 0,
          "and on the whole corpus the one connection the manifests declare gapped "
          "(20260928T103123 :65009) is set aside BY NAME and still refused, none other refused",
          str((hc["set_aside"], hc["declared_not_refused"], hc["refused"])))
    failed_now = {k for k in hexjoin.REGISTERED if hs[k] is False}
    # THE SECOND ZAISHEN CAPTURE (2026-09-29, CASTAI-Z2): G4 joins the FAILED set -- the
    # arena round's end strips the observer's Scourge Healing (hexjoin's docstring) -- with
    # G4r beside it; the pin for it is the corpus before 20260929T100038 (Z1 included).
    hcp2 = hexjoin.upto(hc, ZAISHEN2)
    hsp2 = hexjoin.score(hcp2)
    hsz2 = hexjoin.score(hexjoin.narrow(hc, ZAISHEN2))
    FAILED_SET = (set(hexjoin.FAILED_AS_REGISTERED) | set(hexjoin.FAILED_ON_ZAISHEN)
                  | set(hexjoin.FAILED_ON_ZAISHEN2))
    check(failed_now == FAILED_SET
          and hs["m3"] is None and all(hrv.values())
          and not hs["c2c"] and all(hs[k] for k in hexjoin.CORRECTED if k != "c2c")
          and all(hsp[k] for k in hexjoin.FAILED_ON_ZAISHEN)
          and all(hsp2[k] for k in hexjoin.FAILED_ON_ZAISHEN2)
          and hexjoin.FAILED_ON_ZAISHEN2 == ("g4",),
          "on the WHOLE corpus the Zaishen tape FAILS six registered predictions -- I1, I2, I3, "
          "M1, G2, G3, recorded FAILED as registered beside I4 / M2 / C2 -- and the corrected C2c, "
          "and the SECOND Zaishen tape a seventh, G4 (held on every capture before it); "
          "every one holds RE-STATED (I1r / M1r the [61] seconds, I2r a word riding the "
          "caster's own Fire Storm tick, I3r / G2r no 0x00F1 onto a target already hexed, "
          "since 2026-09-28 G3r effects.interp's rounded scaler on the tape's own build's row, the "
          "build MEASURED, the integerization CORROBORATED once, its rule UNDISCRIMINATED -- "
          "until then this read 'every one but G3' -- and since 2026-09-29 G4r, the round's end "
          "a second strip), and every other corrected reading and post-hoc fact holds",
          str((sorted(failed_now), hrv)))
    z_i = [x[3:] for x in hsz["i_ct_casts"]]
    z_m = [x[3:] for x in hsz["m_ct_casts"]]
    check(hs["i1r"] and hs["m1r"] and hsp["i_ct_casts"] == [] and hsp["m_ct_casts"] == []
          and len(z_i) == 10 and {c for c, _d in z_i} == {0.67}
          and (min(d for _c, d in z_i), max(d for _c, d in z_i)) == (0.651, 0.676)
          and len(z_m) == 7 and {c for c, _d in z_m} == {0.67}
          and (min(d for _c, d in z_m), max(d for _c, d in z_m)) == (0.661, 0.693)
          and {x[:2] for x in hsz["i_ct_casts"] + hsz["m_ct_casts"]}
          == {(ZAISHEN, "50061"), (ZAISHEN, "50295")},
          "I1 / M1 FAILED on 20260928T103123 (exact, per tape): 10 of agent 9's 179s and 7 of its "
          "185s carry a [61] of 0.67 and complete at +0.651..+0.676 / +0.661..+0.693 -- the "
          "re-statement (the [61] seconds when sent, else the activation) holds on every cast; "
          "the registration's corpus has none",
          str((hsz["i_ct_casts"], hsz["m_ct_casts"])))
    # Exact on the Zaishen tape, empty at the registration, and on the whole corpus only the
    # SIGNATURE (I2r holds -- asserted with the restated verdicts above) plus the witness as a
    # subset: a later tape repeating it is confirming evidence (review M1, 2026-09-28).
    check(hsz["i_words_on_target_tick"] == [(ZAISHEN, "50295", 457.84, 1)]
          and hsp["i_words_on_target_tick"] == []
          and set(hsz["i_words_on_target_tick"]) <= set(hs["i_words_on_target_tick"])
          and hs["i2r"]
          and hsz["i_hex_already"] == [(ZAISHEN, "50061", 194.673, 3, 0)]
          and hsz["g2_already_hexed"] == [(ZAISHEN, "50061", 193.924, 44),
                                          (ZAISHEN, "50061", 195.674, 179),
                                          (ZAISHEN, "50061", 201.197, 31),
                                          (ZAISHEN, "58544", 621.587, 36)]
          and hsp["g2_already_hexed"] == [] and hsp["i_hex_already"] == []
          and hsz["h_42_elsewhere"] == 0,
          "I2 / I3 / G2 FAILED on 20260928T103123 (exact, per tape): the one word from a 179's "
          "caster onto its target in the completion batch (:50295 457.840) is its own Fire Storm's "
          "k = 2 tick (none at the registration; on the whole corpus I2r holds and this row is "
          "among the words); a hex landing on the observer ALREADY hexed carries no 0x00F1 -- agent 3's "
          "179 at 194.673 (field3 0: the caster's own Fire Magic) and four applies of 44 / 179 / "
          "31 / 36; the 58 still leads the 0x0042 on every one, and every hex 0x0042 is still on "
          "the observer",
          str((hsz["i_words_on_target_tick"], hsz["i_hex_already"], hsz["g2_already_hexed"])))
    # Exact on the Zaishen tape, none at the registration. On the whole corpus the witness is
    # a SUBSET (a later tape repeating it is confirming evidence -- review item 3, 2026-09-28),
    # and every miss carries the witness's SIGNATURE -- G3 (skill, field3, f32, predicted) and
    # C2c (condition, field3, f32) -- so a miss of a NEW shape reddens here and is seen as a
    # new finding, never absorbed into the recorded failure.
    g3_sig = {x[3:] for x in hsz["g3_miss_rows"]}
    ca_sig, ce_sig = set(hsz["c_cast_applied_off"]), set(hsz["c_environmental_off"])
    _sub = lambda a, b: not (collections.Counter(a) - collections.Counter(b))   # noqa: E731
    # 2026-09-28 (the regenerate-from-38888 arc): hexjoin scores every tape on ITS OWN
    # build's table (build_table: the pristine image the tape's VERSION frame names), so
    # these numbers no longer move with the vault's content overlay. The Zaishen tape is
    # build 38888, where 135 is 4..18 (MEASURED, skilltable on the 38888 image), so G3 AS
    # REGISTERED -- unrounded -- predicts 14.267 there and still misses the wire's 14.0.
    # The 12.533 this check pinned until then was the 38797 row's (3..16), and it is kept,
    # exact, on the known-bad arm below.
    check(hsz["g3_miss_rows"] == [(ZAISHEN, "50061", 164.735, 135, 11, 14.0, 14.267),
                                  (ZAISHEN, "50061", 187.725, 135, 11, 14.0, 14.267)]
          and hsp["g3_misses"] == 0 and hsp["g3_miss_rows"] == []
          and hsz["c_cast_applied_off"] == [("Crippled", 0, 15.0)]
          and hsz["c_environmental_off"] == [("Deep Wound", 20, 20.0), ("Poison", 13, 13.0),
                                             ("Poison", 13, 13.0)]
          and hsp["c_cast_applied_off"] == [] and hsp["c_environmental_off"] == []
          and set(hsz["g3_miss_rows"]) <= set(hs["g3_miss_rows"])
          and _sub(hsz["c_cast_applied_off"], hs["c_cast_applied_off"])
          and _sub(hsz["c_environmental_off"], hs["c_environmental_off"])
          and all(x[3:] in g3_sig for x in hs["g3_miss_rows"])
          and set(hs["c_cast_applied_off"]) <= ca_sig
          and set(hs["c_environmental_off"]) <= ce_sig,
          "G3 AS REGISTERED and C2c FAILED on 20260928T103123 (exact, per tape; none at "
          "the registration): agent 4's 135 lands on the observer twice at field3 11 with 14.0 s "
          "where the tape's own build's row (38888, 4..18) gives interp(4, 18, 11) = 14.267 "
          "unrounded -- the corpus's first hex whose duration varies by "
          "rank (179's 3 / 3 could never fail G3); G3's re-statement G3r is the next check; "
          "C2c has none: a skill-applied Crippled "
          "carries field3 0 (15 s, under [10, obs, 334]), and a Deep Wound at hex 44's end plus "
          "two Poisons on an attack's landing carry field3 == f32 where the classifier calls them "
          "environmental; on the whole corpus these rows are among the misses and every miss "
          "has one of their shapes (a miss of a new shape is a new finding and reddens this)",
          str((hsz["g3_miss_rows"], hsz["c_cast_applied_off"], hsz["c_environmental_off"],
               "whole:", hs["g3_miss_rows"], hs["c_cast_applied_off"], hs["c_environmental_off"])))
    # G3r (hexjoin docstring, 2026-09-28): f32 == effects.interp's ROUNDED two-point scaler
    # (effects.interp, 0x005A8920) on the tape's OWN build's row. The cause the registration
    # left UNMEASURED has two parts of UNEQUAL standing: (a) the BUILD, MEASURED -- on the 38797
    # table (every tape scored on the pin's rows -- what hexjoin read before, when the vault's
    # bulk table was 38797) G3 misses at 12.533 exactly as pinned until today, and G3r misses
    # too, at round(12.533) = 13; on the tape's own 38888 row G3 misses at 14.267 and G3r
    # predicts 14, the wire's 14.0. The endpoints are MEASURED per build (skilltable on each
    # pristine image): 135 is 3..16 on 38797 / 38833 / 38849 and 4..18 on 38888 (CASTAI-ZF7).
    # (b) INTEGERIZATION, CORROBORATED by one witness (two applies, one rank, one tape): the
    # wire's 14.0 against 14.267 unrounded says the duration is an INTEGER; the ROUNDING RULE
    # is UNDISCRIMINATED -- round-half-up, floor and truncation all give 14 -- and G3r's
    # half-up is effects.interp's stated choice, not something this tape measured.
    hc_pin = hexjoin.with_table(hc, 38797)
    hs_pin = hexjoin.score(hc_pin)
    hsz_pin = hexjoin.score(hexjoin.narrow(hc_pin, ZAISHEN))
    faint = [x for x in hsz["g3_rows"] if x[3] == 135]
    faint_pin = [x for x in hsz_pin["g3_rows"] if x[3] == 135]
    check(hs["g3r"] and hsp["g3r"] and hsz["g3r"] and hs["g3r_miss_rows"] == []
          and faint == [(ZAISHEN, "50061", 164.735, 135, 11, 14.0, (4.0, 18.0), 38888, 38888),
                        (ZAISHEN, "50061", 187.725, 135, 11, 14.0, (4.0, 18.0), 38888, 38888)]
          and faint_pin == [(ZAISHEN, "50061", 164.735, 135, 11, 14.0, (3.0, 16.0), 38888, 38797),
                            (ZAISHEN, "50061", 187.725, 135, 11, 14.0, (3.0, 16.0), 38888, 38797)]
          and hsz_pin["g3_miss_rows"] == [(ZAISHEN, "50061", 164.735, 135, 11, 14.0, 12.533),
                                          (ZAISHEN, "50061", 187.725, 135, 11, 14.0, 12.533)]
          and hsz_pin["g3r_miss_rows"] == [(ZAISHEN, "50061", 164.735, 135, 11, 14.0, 13),
                                           (ZAISHEN, "50061", 187.725, 135, 11, 14.0, 13)]
          and not hs_pin["g3r"] and hs_pin["g3r_miss_rows"] == hsz_pin["g3r_miss_rows"]
          and hs_pin["g3_miss_rows"] == hsz_pin["g3_miss_rows"],
          "G3r HOLDS on the whole corpus, the registration's and the Zaishen tape (effects.interp's "
          "rounded scaler on each tape's OWN build's row: 135 at field3 11 on 38888's 4..18 is "
          "round(14.267) = 14, the wire's 14.0) -- the cause of G3's miss in two parts: the 38888 "
          "re-balance MEASURED, and the duration's INTEGERIZATION CORROBORATED by one witness "
          "(two applies, one rank, one tape) with the rounding rule UNDISCRIMINATED (half-up, "
          "floor and truncation all give 14); and the known-bad arm, every tape on the 38797 "
          "table, reproduces the old pin exactly: G3 misses at interp(3, 16, 11) = 12.533 and "
          "G3r misses too, at 13",
          str((faint, hs["g3r_miss_rows"], faint_pin, hsz_pin["g3_miss_rows"],
               hsz_pin["g3r_miss_rows"], hs_pin["g3r_miss_rows"])))
    # G4 on the SECOND Zaishen tape (2026-09-29, CASTAI-Z2; hexjoin's docstring): exact per
    # tape, none at the pin. Seven Scourge Healing 251 (30 s) applies on the observer: one
    # runs out (+30.006), five end on the observer's death, and :51090's at 442.802 ends at
    # +12.250 in the batch that closes the arena round -- 0x0181 with every effect on every
    # body stripped, nobody dead -- which is the ONE row G4 as registered fails on, corpus-
    # wide; G4r (the death OR the round's end strips) holds on the tape, the pin and the
    # whole corpus. The tape's G4 misses are exact ON THE TAPE; on the whole corpus every
    # G4 miss carries the witness's SIGNATURE (end_why "round end", so G4r's misses are [])
    # and their count is reported, not asserted -- a later tape repeating the shape is
    # confirming evidence, a miss of a new shape reddens G4r. The KNOWN-BAD ARM is the
    # reader before today, `removal` by time:
    # at :64557 667.396 a 0x0044 [7, 61] sits in the same batch AHEAD of the 0x0042 that
    # hands buff 61 out again, and the old reader read it as this hex's end -- +0.0, "early",
    # G4r FAILING; by wire order the hex ends at +0.5 on the observer's death. Under the arm
    # every hex apply's row at the pin is byte-identical to the new reader's.
    Z2_G4 = [(ZAISHEN2, "62925", 267.971, 251, 30.006, "scheduled"),
             (ZAISHEN2, "51090", 394.801, 251, 3.249, "death"),
             (ZAISHEN2, "51090", 419.558, 251, 4.365, "death"),
             (ZAISHEN2, "51090", 442.802, 251, 12.25, "round end"),
             (ZAISHEN2, "57580", 140.238, 251, 4.251, "death"),
             (ZAISHEN2, "64557", 641.396, 251, 0.249, "death"),
             (ZAISHEN2, "64557", 667.396, 251, 0.5, "death")]
    check(hsz2["g4_rows"] == Z2_G4 and hsz2["g4_off"] == [Z2_G4[3]] and hsz2["g4r_off"] == []
          and not hsz2["g4"] and hsz2["g4r"]
          and hsp2["g4"] and hsp2["g4r"] and hsp2["g4_off"] == [] and hsp2["g4r_off"] == []
          and hs["g4r"] and [x for x in hs["g4_off"] if x[0] == ZAISHEN2] == [Z2_G4[3]]
          and len(hs["g4_off"]) >= 1 and all(x[5] == "round end" for x in hs["g4_off"])
          and hs["g4r_off"] == [] and not hs["g4"]
          and hsz2["h_42_per_skill"] == {251: 7} and hsz2["h_42_elsewhere"] == 0,
          "G4 FAILED on 20260929T100038 (exact, per tape; none at the pin): the seven Scourge "
          "Healing 251 applies on the observer end scheduled (+30.006), on the observer's death "
          "(+3.249 / +4.365 / +4.251 / +0.249 / +0.5) and ONCE at the ROUND'S END (:51090 442.802, "
          "+12.250, the 0x0181 batch, nobody dead) -- the tape's one G4 miss; on the whole corpus "
          "every G4 miss is a round's end (the signature; the count reported) and G4r (the death "
          "OR the round's end strips) holds on the tape, the pin and the whole corpus",
          str((hsz2["g4_rows"], hsz2["g4_off"], "whole corpus G4 misses:", len(hs["g4_off"]),
               hs["g4_off"], hs["g4r_off"])))
    hexjoin.REMOVAL_BY_ORDER = False
    try:
        hsz2_arm = hexjoin.score(hexjoin.narrow(hc, ZAISHEN2))
        hsp2_arm = hexjoin.score(hcp2)
    finally:
        hexjoin.REMOVAL_BY_ORDER = True
    _g4_arm7 = hsz2_arm["g4_rows"][6] if len(hsz2_arm["g4_rows"]) > 6 else None   # a vault without the tape
    check(hsz2_arm["g4_rows"][:6] == Z2_G4[:6]
          and _g4_arm7 == (ZAISHEN2, "64557", 667.396, 251, 0.0, "early")
          and hsz2_arm["g4r_off"] == [(ZAISHEN2, "64557", 667.396, 251, 0.0, "early")]
          and not hsz2_arm["g4r"]
          and hsp2_arm["g4_rows"] == hsp2["g4_rows"] and hsp2_arm["h_residuals"] == hsp2["h_residuals"]
          and hsp2_arm["g4r"] and hexjoin.REMOVAL_BY_ORDER,
          "KNOWN-BAD ARM: `removal` by TIME (the reader before 2026-09-29) reads the 0x0044 "
          "[7, 61] that sits AHEAD of the 0x0042 re-issuing buff 61 at :64557 667.396 as that "
          "hex's own end -- +0.0, 'early', G4r FAILING on it -- where wire order reads the "
          "observer's death at +0.5; at the pin the arm's hex rows and residuals are byte-"
          "identical to the new reader's, so no earlier number moved (a vault without the tape "
          "fails here by name)",
          str((_g4_arm7, hsz2_arm["g4r_off"], hsp2_arm["g4_rows"] == hsp2["g4_rows"])))
    # The per-build table IS the extractor's: every vault skills row, against the table
    # hexjoin reads for the build that row RECORDS (its provenance.build -- 38797 on today's
    # vault bar the repo's row-level 38888 overrides, 38888 after the regeneration), on the
    # four columns the reader consumes. A drift between build_table and --emit-content (a
    # different corpus rule, a column read at another offset) reddens here.
    _cols = ("activation", "type_code", "duration0", "duration15")
    _bad, _n, _vb = [], 0, collections.Counter()
    for _k, _r in agents.WORLD.rows("skills").items():
        _b = int(_r.provenance.get("build", 0))
        _vb[_b] += 1
        try:
            _own = hexjoin.build_table(_b)[0].get(int(_k))
        except LookupError as exc:
            _bad.append((_k, _b, str(exc)[:60]))
            continue
        if _own is None:
            _bad.append((_k, _b, "not in that build's player corpus"))
            continue
        _n += 1
        _d = [c for c in _cols if c in _r and float(_r[c]) != float(_own[c])]
        if _d:
            _bad.append((_k, _b, _d))
    check(_n >= 1333 and not _bad,
          "hexjoin's per-build table is the extractor's own: every vault skills row agrees, on "
          "activation / type_code / duration0 / duration15, with the table read from the "
          "pristine image of the build the row records",
          str((_n, dict(_vb), _bad[:6])))

    def _exact_179(s):
        return (s["i_per_port"] == hexjoin.EXPECT_179_PER_PORT and s["i_completed"] == 28
                and s["i_scheduled"] == 20 and s["i_scheduled_with_words"] == 18
                and len(s["i_payoff_tick"]) == 1 and s["i_payoff_tick"][0][:2] == ("54071", 689.819)
                and len(s["i_removed"]) == 4 and all(n == 0 for _p, _t, _d, n in s["i_removed"])
                and len(s["i_target_died"]) == 3 and sum(1 for x in s["i_target_died"] if x[3]) == 2
                and len(s["i_caster_died"]) == 1 and s["i_takers_hist"] == {1: 10, 2: 5, 3: 5, 4: 1}
                and s["i_takers_not_foe"] == 0 and s["i_observer_struck"] == 3
                and s["i_observer_prefix_ok"] == 3
                and [x[:2] for x in s["i_observer_burning"]] == [(3, 3.0)] * 3
                and len(s["i_payoff_mixed"]) == 2)

    def _exact_185(s):
        return (s["m_per_port"] == hexjoin.EXPECT_185_PER_PORT and s["m_completed"] == 25
                and s["m_twin"] == 22 and s["m_single"] == 3 and s["m_none"] == 0
                and len(s["m_mixed"]) == 4 and s["m_target_single_adjacent_twin"] == [("54071", 647.3)]
                and s["m_twin_no_burning"] == 0 and s["m_single_with_burning"] == 1
                and [x[:2] for x in s["m_observer_burning"]] == [(9, 9.0)] * 2 and s["m_rank_fits"]
                and s["l_adds"].get("179 [1, 12]") == 28 and s["l_adds"].get("1097 [1, 12]") == 5
                and s["l_adds"].get("1097 [12]") == 1 and s["l_adds"].get("26 [1, 4]") == 5
                and s["l_adds"].get("222 []") == 14 and len(s["l_snare"]) == 6
                and s["l_ascending"] == 24 and len(s["l_not_ascending"]) == 1
                and s["l_not_ascending"][0][:3] == (185, "54071", 640.689)
                and s["c_effect_ids_witness"] == {"Burning": {25: 3}}
                and s["c_observer_no_id"].get("Burning") == 2)

    check(_exact_179(hs) and hs["i_hex_applies"][0]["field3"] == 13
          and authsrv.hex_end_damage(179, 13) == (72, "standalone"),
          "179 on 20260817T231139 (exact, PER TAPE -- scored on the witness capture alone): 30 "
          "announces (19 / 4 / 4 / 3 per port), 28 completed; 20 scheduled ends at +3.0, 18 with "
          "the payoff and ONE (689.819) whose only word is the caster's Fire Storm tick -- a mixed "
          "instant, not a payoff (the review's EV-6) -- 4 REMOVED by Remove Hex with 0 payoff, 3 "
          "ended on the target's death (2 striking an adjacent foe), 1 in the caster's death "
          "batch; takers 1..4 (10 / 5 / 5 / 1), every one a foe; 2 mixed instants; the observer "
          "struck 3 times with the 0x00CF -> [10] -> word prefix and Burning (3, 3.0) each; the "
          "caster's rank 13 -- the server's hex_end_damage(179, 13) is the tape's 72 on the "
          "ASSUMPTION the taker's armour factor is 1 (CORROBORATED, the armour is off the wire)",
          str({k: hs[k] for k in ("i_per_port", "i_scheduled", "i_removed", "i_target_died",
                                  "i_takers_hist", "i_observer_burning", "i_payoff_tick")}))
    # "the ONE hex 0x0042 in the corpus is on the observer" was a corpus count: it is scored
    # on the registration's corpus (1); the whole corpus keeps the SIGNATURE (every hex 0x0042
    # on the observer, none elsewhere); the Zaishen tape's seven are its exact witness
    check(_exact_185(hs)
          and hs["h_42_elsewhere"] == 0 and hsp["h_42_on_observer"] == 1
          and hsz["h_42_on_observer"] == 7 and hs["h_42_on_observer"] >= 1
          and hsp["m_ranks_corpus"] == [13] and hsz["m_ranks_corpus"] == [0]
          and {0, 13} <= set(hs["m_ranks_corpus"])
          and len(hs["c_dazed"]) >= 1 and len(hs["c_cracked"]) >= 2
          and hs["c_cast_applied"] >= 20 and hs["c_environmental"] >= 30
          and hs["c_observer_no_id_corpus"].get("Crippled", 0) >= 4 and hs["c_observer_no_id_corpus"].get("Deep Wound", 0) >= 4
          and set(hs["c_effect_ids"]["Burning"]) == {25} and hs["c_effect_ids"]["Burning"][25] >= 5
          and hs["c_effect_ids"]["Cracked Armor"].get(29, 0) >= 2 and hs["c_effect_ids"]["Weakness"].get(29, 0) >= 9,
          "185 on the same tape (exact, per tape): 27 announces (17 / 4 / 3 / 3), 25 completed, 22 "
          "twins / 3 singles on the target, 4 casts mixing twins and singles, 647.300 the one "
          "target-single adjacent-twin; no twin without a Burning signal, one single (780.235) "
          "with a new one; the observer's Burning (9, 9.0) twice, the caster's 13 predicting both "
          "3 and 9 (its rank read on the witness's own hex; the registration's corpus held that "
          "one rank, 13, and the Zaishen tape adds agent 3's 179 at field3 0, its own Fire "
          "Magic -- ranks 0 and 13 among the whole corpus's); the ONE hex 0x0042 of the registration's corpus is on "
          "the observer (the Zaishen tape: seven more, all on the observer); [6, T, ids] on their "
          "tapes: 179 [1, 12] x28, 1097 [1, 12] x5 + [12] x1, Empathy [1, 4] x5, Lightning Strike "
          "none x14; 6 snares; the order census 24 of 25 ascending, the one exception 640.689 "
          "(the review's M12 / EV-12); Burning's [6] id on the witness tape 25 x3 and TWO observer "
          "Burnings (Mind Burn's twin) carry NO [6] at all (and corpus-wide the observer's Crippled "
          "and Deep Wound applies carry none either -- an id is not every condition's); corpus FLOORS: Dazed >= 1, Cracked "
          "Armor >= 2, every Burning id 25 (>= 5), id 29 shared by Weakness and Cracked Armor "
          "(a class, not a per-condition id -- the review's R34-8)",
          str(dict({k: hs[k] for k in ("m_per_port", "m_twin", "m_single", "m_mixed", "l_adds",
                                       "l_not_ascending", "c_effect_ids", "c_observer_no_id")},
                   m_ranks=(hsp["m_ranks_corpus"], hsz["m_ranks_corpus"], hs["m_ranks_corpus"]))))
    # EV-3: a later capture holding the SAME casts again is confirming evidence and must
    # redden nothing -- append a copy of the witness's 54071 connection under a new stamp
    import copy as _copy
    _src = [c for c in hc["conns"] if c.stamp == hexjoin.EXPECT_CAPTURE and str(c.port) == "54071"]
    _dup = _copy.copy(_src[0])
    _dup.stamp = "SYNTHETIC-CONFIRMING"
    hs2p = hexjoin.score(dict(hcp, conns=list(hcp["conns"]) + [_dup]))
    hv2p = hexjoin.verdicts(hs2p)
    check(all(hv2p.values()) and _exact_179(hs2p) and _exact_185(hs2p)
          and hs2p["i_completed_corpus"] == hsp["i_completed_corpus"] + 18
          and hs2p["m_completed_corpus"] == hsp["m_completed_corpus"] + 16
          and hs2p["c_effect_ids"]["Burning"][25] == hsp["c_effect_ids"]["Burning"][25] + 3
          and hs2p["l_adds_corpus"]["179 [1, 12]"] == 46,
          "the arm: the witness's busiest connection appended again under another stamp leaves "
          "the verdict HOLDING and every exact number above unmoved while the corpus floors grow "
          "(+18 / +16 completions, +3 Burning ids, 179's [1, 12] 28 -> 46) -- the counts are "
          "scored per tape and confirming evidence cannot redden them (the review's EV-3 flipped "
          "the first port to THE READING FAILS this way) (on the registration's corpus)",
          str((hv2p, hs2p["i_completed_corpus"], hs2p["m_completed_corpus"], hs2p["i_takers_hist"])))
    hs2 = hexjoin.score(dict(hc, conns=list(hc["conns"]) + [_dup]))
    hrv2 = hexjoin.restated_verdicts(hs2)
    check(all(hrv2.values()) and _exact_179(hs2) and _exact_185(hs2)
          and {k for k in hexjoin.REGISTERED if hs2[k] is False} == failed_now
          and hs2["i_completed_corpus"] == hs["i_completed_corpus"] + 18
          and hs2["m_completed_corpus"] == hs["m_completed_corpus"] + 16
          and hs2["c_effect_ids"]["Burning"][25] == hs["c_effect_ids"]["Burning"][25] + 3
          and hs2["l_adds_corpus"]["179 [1, 12]"] == hs["l_adds_corpus"]["179 [1, 12]"] + 18,
          "and on the whole corpus the same copy leaves the re-stated verdict HOLDING, the same "
          "predictions FAILED and every exact number unmoved, the floors +18 / +16 / +3 / +18",
          str((hrv2, hs2["i_completed_corpus"], hs2["m_completed_corpus"])))

    print("\n13. the corpus: the CONVERTED hit's word (healjoin P6, RUN-SKILLS-RB)")
    # RUN-SKILLS-RB (2026-09-16, 20260916T213125): ten hits taken under
    # Reversal of Fortune at a cap of 50 -- the first prevention heals in the
    # corpus (F46.8 had counted zero). The zero is +0.0, never the graze's
    # -0.0; the rest are negative remainders; the heal precedes the damage.
    import healjoin
    cv = healjoin.score_conversions(healjoin.conversions())
    check(cv["n"] >= 10 and cv["zero_words"] >= 7 and cv["remainders"] >= 3
          and cv["plus_zero"] == cv["zero_words"]
          and cv["minus_zero_anywhere"] == 0 and cv["positive_damage"] == 0,
          "P6 a fully converted hit's damage word is +0.0 (0x00000000) and a "
          "partly converted one's is the negative remainder -- never -0.0, "
          "on the conversions or on the coincident self-heals beside them",
          f"{cv} -- floors 10 / 7 / 3 from the RB tape (a conversion is the "
          f"row with the enchantment's 0x0044 on the tick; the coincident rows "
          f"are Healing Signets closing under fire); a -0.0 here would mean "
          f"retail spells the converted zero like the graze after all")
    check(cv["n"] >= 10 and cv["heal_first"] == cv["n"],
          "and the heal word precedes the damage word on every conversion tick",
          f"heal first {cv['heal_first']} of {cv['n']} (the coincident rows: "
          f"{cv['coincident_heal_first']} of {cv['coincident']}, which is not "
          f"a claim) -- WIKI (GWW, \"Reversal of Fortune\" Notes): healing "
          f"before damage")


def section_label_tier():
    """Section 14. Its own function since 2026-10-07, so that it runs -- or declares its
    skip -- whether the corpus ran or not: its subject is the vault's label tier, not a
    capture, and the corpus's early return used to take it along unannounced."""
    import agents
    import authsrv

    print("\n14. the LABEL tier through the SAME consumers (SKILLS-LT, DESKWORK-D4 step 4)")
    # vault/content/skill_labels.toml -- `python toolkit/clientscan/skilldesc.py
    # --emit-labels` -- carries a `tier = "label"` skill_effect row per plain
    # SERVED skill (studies/skills 55). No second path: skill_damage and
    # skill_condition read the row exactly as they read a hand row, and
    # `World.drop_tier` (what --no-skill-labels does at startup) leaves the
    # server as it was before 2026-09-23. Skipped where the overlay is not
    # loaded: a bare machine, or one that has not regenerated it.
    lab = {k: r for k, r in agents.WORLD.rows("skill_effect").items()
           if r.get("tier") == "label"}
    if "187" not in lab or "220" not in lab:
        LEDGER.skip("14. the label tier (12 checks)",
                    "skill_labels.toml not loaded -- `python toolkit/clientscan/"
                    "skilldesc.py --emit-labels` regenerates it into vault/content/")
    else:
        import contextlib
        import io
        check(authsrv.skill_damage(187, 0) == (7, "standalone")
              and authsrv.skill_damage(187, 15) == (112, "standalone"),
              "a label-tier fire spell (187: scale 7..112 at str1, a Spell aimed at "
              "the burst's byte 16) resolves through skill_damage at both ends of "
              "the ladder -- the record's own numbers",
              (authsrv.skill_damage(187, 0), authsrv.skill_damage(187, 15)))
        check(authsrv.skill_condition(220, 0) == (479, 3.0)
              and authsrv.skill_condition(220, 15) == (479, 8.0),
              "a label-tier Blind (220: bonus 3..8 at str2, a foe Spell) resolves "
              "through skill_condition's first slot: 479 for 3 s at rank 0, 8 s "
              "at rank 15 (784 was this example until the fix pass excluded it: "
              "its chain requirement has no gate on a Spell)",
              (authsrv.skill_condition(220, 0), authsrv.skill_condition(220, 15)))
        # The build is the one the FILE declares (skilldesc.py --emit-labels stamps its
        # header from the image's own sha256), and every label row must record it; the
        # expectation is keyed on it -- the label-row count each build's table emits,
        # MEASURED from its generated file (38797: 56, the table until 2026-09-28; 38888:
        # 55, 831's row dropping out) -- so a table of any other build FAILS naming it.
        import re
        _lp = vaultpath.vault_path("content", "skill_labels.toml")
        try:
            with open(_lp, encoding="utf-8") as _fh:
                _hm = re.search(r"^# build: (\d+) ", _fh.read(4096), re.M)
        except OSError:
            _hm = None
        _lb = int(_hm.group(1)) if _hm else None
        _lrb = {r.provenance.get("build") for r in lab.values()}
        check(lab["187"]["tier"] == "label" and "AREA_BURST" in lab["187"]["tier_detail"]
              and all(r.provenance.get("source") == "client-table" for r in lab.values())
              and _lrb == {_lb} and _lb in LABEL_ROWS_BY_BUILD
              and len(lab) == LABEL_ROWS_BY_BUILD[_lb]
              and lab["220"]["tier_detail"] == ["TARGET_FOE"],
              "the rows say what they are: tier label, 187's area is spell_burst's "
              "(AREA_BURST), 220 reaches its one target; client-table provenance, every "
              "row stamped with the build its file declares, a build with a measured "
              "expectation (38797: 56 rows; 38888: 55)",
              (dict(lab["187"]), dict(lab["220"]), f"file build {_lb}, row builds "
               f"{sorted(_lrb, key=str)}, rows {len(lab)}, expected "
               f"{LABEL_ROWS_BY_BUILD.get(_lb, 'NO EXPECTATION FOR THIS BUILD')}"))
        check(authsrv.skill_label_tier(187) == list(lab["187"]["tier_detail"])
              and authsrv.skill_label_tier(312) is None
              and authsrv.skill_label_tier(999999) is None,
              "skill_label_tier -- what the per-cast log prints -- returns the label row's "
              "detail, None for a hand row (Holy Strike) and None for no row")
        # ENG-5: the per-cast line itself, and its two call sites in the source.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv._label_tier_note(187, 7, "the player's")
            authsrv._label_tier_note(312, 7, "the player's")
        out = buf.getvalue()
        check(out.startswith("[c7] the player's skill 187 resolves through a LABEL-tier row (")
              and "AREA_BURST" in out and "not hand-verified" in out and "--no-skill-labels" in out
              and out.count("\n") == 1 and "312" not in out,
              "_label_tier_note prints ONE line for a label-tier skill naming the tier "
              "and its detail, and nothing for a hand row (Holy Strike)", out)
        src = open(authsrv.__file__, encoding="utf-8").read()
        check(src.count('_label_tier_note(cast["skill_id"], conn_id, "the player\'s")') == 1
              and src.count('_label_tier_note(skill_id, conn_id, f"agent {agent_id}\'s")') == 1,
              "SOURCE LOCK: the note is called at the player's E5 and at a body's landing, "
              "once each")
        # ENG-4 / LT-R11: the revert flag's WIRING -- it parses, and main() drops the
        # tier before the listener opens (an early WORLD read would otherwise see it).
        import serverargs
        ap = serverargs.build_parser(
            doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
            HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
            GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
            VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
        i_main = src.index("\ndef main():")
        i_flag = src.index("    if a.no_skill_labels:", i_main)
        i_drop = src.index('drop_tier("skill_effect", agents.content.LABEL_TIER)', i_flag)
        i_listen = src.index("srv.listen(", i_main)
        check(ap.parse_args([]).no_skill_labels is False
              and ap.parse_args(["--no-skill-labels"]).no_skill_labels is True
              and i_main < i_flag < i_drop < i_listen and i_drop - i_flag < 200
              and "SKILL_LABELS" not in src.replace("NO SKILL LABELS", ""),
              "--no-skill-labels parses (default off), and main()'s block calls "
              "World.drop_tier(skill_effect, LABEL_TIER) BEFORE srv.listen; no dead "
              "SKILL_LABELS global is left to look load-bearing")
        # ENG-2 / LT-R7: the AREA_BURST mark agrees with the server's OWN predicate,
        # row by row -- spell_burst's radius AND a standalone damage to burst with
        # (118's area Weakness has the radius and no damage: one target here).
        lab_ids = sorted(int(k) for k in lab)

        def _bursts(sid):
            d = authsrv.skill_damage(sid, 0)
            return authsrv.spell_burst(sid) is not None and bool(d) and d[1] == "standalone"
        disagree = [s for s in lab_ids if ("AREA_BURST" in lab[str(s)]["tier_detail"]) != _bursts(s)]
        # 2026-09-26 (DESKWORK-D6 step 2, studies/weapons 42): 192 and 197 are HAND rows now --
        # areas over TIME the server serves through area_over_time, its own predicate -- so
        # they are no longer in the label tier; spell_burst still refuses both (a duration).
        check(disagree == [] and authsrv.spell_burst(192) is None and authsrv.spell_burst(197) is None
              and authsrv.spell_burst(187) == 156.0 and "192" not in lab and "197" not in lab
              and authsrv.area_over_time(192, 0) is not None
              and authsrv.area_over_time(197, 0) is not None
              and agents.WORLD.get("skill_effect", "192").get("tier") is None,
              f"AREA_BURST agrees with spell_burst + a standalone damage on all {len(lab_ids)} "
              f"label rows; the areas over time 192 and 197 are refused by spell_burst (a "
              f"duration) and served by area_over_time from their HAND rows, which shadow the "
              f"label rows (ONE_TARGET + DURATION_UNMODELLED) since 2026-09-26", disagree)
        # LT-R4 / SKILLS-LU: a shipped non-attack with a chain requirement carries the
        # CHAIN_GATED mark -- the player's E5 judges it (NONATTACK_CHAIN_GATE) -- and
        # 784 (combo_req 2, a Spell) is such a row once the overlay is regenerated
        # (skills 59); on the 2026-09-23 overlay before that it is simply absent.
        chained = [s for s in lab_ids
                   if authsrv.skill_chain_fields(s)[1] and not authsrv._is_attack_skill(s)]
        unmarked = [s for s in chained if "CHAIN_GATED" not in lab[str(s)]["tier_detail"]]
        check(unmarked == [] and authsrv.skill_chain_fields(784)[1] == 2
              and not authsrv._is_attack_skill(784)
              and ("784" not in lab or "CHAIN_GATED" in lab["784"]["tier_detail"])
              and authsrv.NONATTACK_CHAIN_GATE is True,
              f"every label row that is a non-attack with combo_req ({len(chained)} loaded) "
              f"carries CHAIN_GATED, the mark of the E5's non-attack chain gate; 784 -- "
              f"combo_req 2, a Spell -- carries it when present", (chained, unmarked))
        gone = agents.WORLD.drop_tier("skill_effect", "label")
        try:
            check(authsrv.skill_damage(187, 15) is None
                  and authsrv.skill_condition(220, 15) is None and len(gone) >= 40,
                  f"with the tier DROPPED (--no-skill-labels) both resolve to nothing "
                  f"-- the hand rows alone; {len(gone)} rows gone",
                  (authsrv.skill_damage(187, 15), authsrv.skill_condition(220, 15)))
            check(authsrv.skill_damage(312, 15) is not None
                  and authsrv.skill_condition(382, 15) is not None
                  and authsrv.skill_condition(320, 15) == (481, 15.0),
                  "and the hand rows are untouched by the drop: Holy Strike, Sever "
                  "Artery and Hamstring's 54.8 fix (Crippled 15 s) still resolve -- the "
                  "flag reverts the TIER, not the hand fixes of the same day")
        finally:
            agents.WORLD.tables["skill_effect"].update(gone)
        check(authsrv.skill_damage(187, 15) == (112, "standalone"),
              "restored: the label row resolves again (the drop is a removal, not a "
              "rewrite)")


def section_record_rows():
    """Section 15, the carried rows against the vault's own -- the one check that says
    sections 2-4 and 6-11d ran on the rows a vault run would have read.

    Its SUBJECT is the vault's table, so it skips without one; but the skip is decided
    on the vault/content DIRECTORY and on nothing that loaded. With the directory there
    and the rows absent (a skills.toml that did not load), every row reads "absent" and
    the check FAILS. Column for column BOTH ways: a column the vault's row has and RECORD
    lacks is a difference too.
    """
    import agents

    print("\n15. the rows this file carries, against the vault's own (2026-10-07)")
    try:
        vaultpath.require_dir("content", why="section 15: the vault's skills table, "
                                             "which RECORD copies")
    except SystemExit as exc:
        LEDGER.skip("15. the carried rows against the vault's (1 check)",
                    str(exc).splitlines()[0])
        return
    loaded = agents.WORLD.rows("skills")
    off, builds = {}, {}
    for k, row in RECORD.items():
        got = loaded.get(k)
        if got is None:
            off[k] = "absent"
            continue
        builds[k] = getattr(got, "provenance", {}).get("build")
        cols = sorted(c for c in set(row) | set(got) if got.get(c, "absent") != row.get(c, "absent"))
        if cols:
            off[k] = cols
    check(not off,
          f"every one of the {len(RECORD)} skills rows RECORD carries is the vault's own, "
          f"column for column -- so sections 2-4 and 6-11d ran on the rows the vault's "
          f"table would have given them",
          f"off={off}, loaded builds={sorted(set(builds.values()), key=str)} (RECORD copied "
          f"from {RECORD_BUILD}; a regenerated table that moves a carried column reds this, "
          f"and the fix is to re-copy that row with its build)")


if __name__ == "__main__":
    sys.exit(main())
