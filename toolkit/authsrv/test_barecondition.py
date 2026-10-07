"""A skill's condition on a machine with no vault: unreadable, announced, never a crash.

    python toolkit/authsrv/test_barecondition.py

WHAT EARNS THIS FILE (2026-10-07, PLAN-LOG "`test_guards.py` and
`test_labelconsumers.py` run on a bare machine"). `skill_condition` guards its
`skill_effect` read, and that table is REPO content (`content/world.toml`, 72 hand
rows). Behind it `_condition_terms` called `skill_scale_value`, which reads the
`skills` table, and that table is VAULT-only apart from the 14 rows in
`content/overrides/skills_38888.toml`. The catch there was `ValueError` alone,
for the bit-clear refusal. So with no vault, 8 of the 72 hand rows raised
`ContentError` out of `skill_condition`: 167, 320, 337, 352, 392, 782, 799 and
2059. Two more, 179 and 185, raised out of `_condition_terms` when it was called
directly (hex_end_burst, adjacent_player_spell / adjacent_body_spell). 320 is on
the default bar, so pressing it at a foe killed the world tick in `cast_tick`, two
lines after `skill_timing` printed its "fall back to 0" announcement for the same
row. This is shape 1 of the bare-machine class: `skill_damage`, `skill_heal`,
`skill_timing` and `skill_cost` all take the fallback, and this reader did not.

THE FIX (`_condition_terms`): `skill_damage`'s narrow catch, `ContentError` only
and only around the `skills` read. The slot is skipped, so the skill inflicts no
condition, which is the inert direction rather than a guessed duration. The
missing row is announced once per id through `skill_timing`, as `skill_cost`
does. A bit-clear slot's `ValueError` keeps its own arm.

BARE ON EVERY MACHINE. The `skills` table is REPLACED for each block
(`skills_table`), not merged, so a vault run takes the bare path too. The
replacement is `{}`, which is stronger than a real bare machine: the 14 tracked
override rows go as well, so 382 and 384 test the fallback alongside the eight.
The sweeps read every LOADED `skill_effect` row: the repo's 72 hand rows (12
subjects) on a bare machine, and those plus the vault's label tier (127 rows, 30
subjects on 2026-10-07) on a vault one. Section 5 is the known-good arm. With
320's own row carried (`RECORD`), the same reads return Crippled and the same
press lands it, so the catch has not swallowed the readable case and the press
really reaches the condition read. Section 6, vault-only, holds the carried row
to the vault's.

RED-FIRST, against f04cc8cc's `authsrv.py` (the fix reverted): 5 checks FAIL,
in sections 1, 2, 3 and 4, on a vault run and on a nonexistent vault alike.
With the table emptied, `skill_condition` raised for 10 of the repo's 72 rows
(the defect's eight, plus 382 and 384, whose tracked rows the replacement
removes) and `_condition_terms` for 12 (179 and 185 join them). A vault run's
127 rows raised 26 and 30. Nothing was announced, and the press died in
`cast_tick` with "no skills row '320'". Sections 0, 5 and 6 pass, as they should.

No socket, no client. Only section 6 needs the vault, and it declares its skip
when vault/content is absent.
"""
import contextlib
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import checks  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR 12, MEASURED 2026-10-07 on a green run with RURIK_VAULT at an empty
# directory and at a nonexistent path alike: 12 checks and 1 declared skip
# (section 6, vault-only by subject). A vault run gives 13.
LEDGER = checks.Ledger("a condition with no skills row", floor=12)
check = LEDGER.ok

# The defect's eight, named in PLAN-LOG as raising out of skill_condition.
DEFECT_IDS = (167, 320, 337, 352, 392, 782, 799, 2059)
RANKS = (0, 12, 15)
FOE = 10

# 320 (Hamstring) as vault/content/skills.toml holds it: skilltable.py's row,
# build 38974 (CLAUDE.md's gate, a measured row with its extractor and build).
# Its bonus slot is enabled (skill_arguments 4) and runs 3..15, so Crippled lasts
# 3 s at rank 0 and 15 s at rank 15. weapon_req 0x80 is a sword, which is why
# section 5 hands the player the starter sword.
RECORD_BUILD = 38974
RECORD = {
    "320": {"activation": 0.0, "aftercast": 0.0, "recharge": 10, "energy": 5,
            "adrenaline": 0, "adrenaline_units": 0, "attribute": 20, "profession": 1,
            "type_code": 14, "target": 5, "combo": 0, "combo_req": 0,
            "weapon_req": 128, "aoe_range": 0.0, "skill_arguments": 4,
            "duration0": 0, "duration15": 0, "scale0": 0, "scale15": 0,
            "bonus_scale0": 3, "bonus_scale15": 15, "projectile": 2077,
            "impact_visual": 2077, "touch_range": False, "half_range": False},
}

ANNOUNCED = re.compile(r"\[skills\] no content row for skill (\d+) ")


@contextlib.contextmanager
def skills_table(rows):
    """WORLD's skills table REPLACED by `rows` for the block, with a fresh
    announced-once set so each block sees its own announcements; both put back."""
    import authsrv
    tables = authsrv.agents.WORLD.tables
    had, kept = "skills" in tables, tables.get("skills")
    seen = authsrv._MISSING_SKILL_ROWS
    tables["skills"] = {k: dict(v) for k, v in rows.items()}
    authsrv._MISSING_SKILL_ROWS = set()
    try:
        yield
    finally:
        authsrv._MISSING_SKILL_ROWS = seen
        if had:
            tables["skills"] = kept
        else:
            del tables["skills"]


def effect_rows():
    import authsrv
    return {int(k): row for k, row in authsrv.agents.WORLD.rows("skill_effect").items()}


def subjects(rows):
    """The skill_effect rows whose bonus or scale slot NAMES a condition: the only ones
    `_condition_terms` reads a skills row for."""
    import authsrv
    return sorted(s for s, row in rows.items()
                  if any(authsrv.effects.condition_id(row.get(m)) is not None
                         for m in ("bonus_scale_means", "scale_means")))


def sweep(reader, rows):
    """{(skill, rank): result or the exception's class name}, stdout captured."""
    out, got = io.StringIO(), {}
    with contextlib.redirect_stdout(out):
        for s, row in sorted(rows.items()):
            for r in RANKS:
                try:
                    got[(s, r)] = reader(s, row, r)
                except Exception as exc:                       # noqa: BLE001
                    got[(s, r)] = type(exc).__name__
    return got, out.getvalue()


def worn(state):
    """The skill ids of every episode on the foe."""
    table = state.get("effects")
    return sorted(ep["skill"] for ep in table.on_agent(FOE)) if table else []


def press_320(weapon=None):
    """Press 320 at a hostile agent and run the world tick past its completion.
    Returns (state, the exception's text or None, the skill_condition calls the
    tick made, stdout)."""
    import authsrv
    agents = authsrv.agents
    state = {"agents": {FOE: {"name": "foe", "dead": False, "last_hit": 0.0,
                              "max_health": 100.0, "health": 100.0, "pos": (60.0, 0.0),
                              "allegiance": agents.ALLEGIANCE_HOSTILE}},
             "pos": (0.0, 0.0)}
    send = lambda op, vals, label="", quiet=False: None        # noqa: E731
    calls, real = [], authsrv.skill_condition

    def spy(skill_id, rank):
        result = real(skill_id, rank)
        calls.append((skill_id, result))
        return result

    held, out, err = agents.PLAYER_WEAPON, io.StringIO(), None
    try:
        if weapon is not None:
            agents.PLAYER_WEAPON = weapon
        with contextlib.redirect_stdout(out):
            authsrv.handle_skill_press([0, 320, 0, FOE], send, state, 0,
                                       authsrv.GAME_CMSG_USE_SKILL)
            # Rewind rather than sleep, as test_guards and test_castcycle do.
            for cast in state.get("pending_casts", []):
                for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                    if cast.get(k) is not None:
                        cast[k] -= 30.0
            authsrv.skill_condition = spy
            try:
                authsrv.cast_tick(send, state, 0)
            finally:
                authsrv.skill_condition = real
    except Exception as exc:                                   # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"[:160]
    finally:
        agents.PLAYER_WEAPON = held
    return state, err, calls, out.getvalue()


def section_fixture(rows, subj):
    import authsrv

    print("0. the fixture: no skills row, and the defect's ids are subjects")
    try:
        authsrv.agents.WORLD.get("skills", "320")
        gone = False
    except authsrv.agents.content.ContentError:
        gone = True
    check(gone and not authsrv.agents.WORLD.rows("skills"),
          "the skills table is EMPTY for the block -- 320's row is unreachable, "
          "the tracked overrides' 14 included",
          f"rows={len(authsrv.agents.WORLD.rows('skills'))} -- a replacement that "
          f"left a row would test a vault machine, not a bare one")
    missing = [s for s in DEFECT_IDS if s not in subj]
    check(len(rows) >= 72 and not missing,
          f"{len(rows)} skill_effect rows load (the repo's 72 at least), and all "
          f"{len(DEFECT_IDS)} of the defect's ids name a condition slot ({len(subj)} "
          f"subjects)",
          f"subjects={subj}, missing={missing} -- a subject that left the hand rows "
          f"would make the sweeps below pass without reading it")


def section_skill_condition(rows):
    import authsrv

    print("\n1. skill_condition over every skill_effect row: nothing raises, nothing lands")
    got, _ = sweep(lambda s, _row, r: authsrv.skill_condition(s, r), rows)
    raised = sorted({s for (s, _r), v in got.items() if isinstance(v, str)})
    check(not raised,
          f"skill_condition raises for none of the {len(rows)} skill_effect rows at ranks "
          f"{RANKS}",
          f"raised={raised} -- f04cc8cc raised ContentError for {list(DEFECT_IDS)}: "
          f"_condition_terms caught ValueError only around the skills read")
    landed = sorted({s for (s, _r), v in got.items() if v is not None and not isinstance(v, str)})
    check(not landed,
          "and every one returns None: no skills row, no condition -- never a "
          "guessed duration",
          f"landed={landed}")


def section_condition_terms(rows):
    import authsrv

    print("\n2. _condition_terms directly (hex_end_burst, the adjacent spells)")
    got, _ = sweep(authsrv._condition_terms, rows)
    raised = sorted({s for (s, _r), v in got.items() if isinstance(v, str)})
    check(not raised,
          f"_condition_terms raises for none of the {len(rows)} skill_effect rows -- 179's "
          f"end burst and 185's energy clause call it past skill_condition's early "
          f"return",
          f"raised={raised}")
    landed = sorted({s for (s, _r), v in got.items() if v is not None and not isinstance(v, str)})
    check(not landed, "and every one returns None", f"landed={landed}")


def section_announced(rows, subj):
    import authsrv

    print("\n3. the missing row is announced, once per id, for exactly the subjects")
    _, text1 = sweep(lambda s, _row, r: authsrv.skill_condition(s, r), rows)
    _, text2 = sweep(authsrv._condition_terms, rows)
    ids = [int(m) for m in ANNOUNCED.findall(text1 + text2)]
    twice = sorted({s for s in ids if ids.count(s) > 1})
    check(sorted(set(ids)) == subj and not twice,
          f"skill_timing's announcement names each of the {len(subj)} subjects "
          f"exactly once across {2 * len(RANKS)} reads apiece, and no other id",
          f"announced={sorted(set(ids))}, twice={twice}, subjects={subj} -- a "
          f"silent fallback leaves the inert condition to be found on screen; a "
          f"second copy doubles every line")


def section_press():
    import authsrv

    print("\n4. the default bar's 320, pressed at a foe: the world tick completes")
    state, err, calls, _ = press_320()
    check(err is None and not state.get("pending_casts"),
          "handle_skill_press then cast_tick raise nothing, and the cast completes "
          "(no pending cast left)",
          f"error={err!r}, pending={state.get('pending_casts')} -- f04cc8cc raised "
          f"'no skills row 320' out of cast_tick, the world tick's own call")
    check((320, None) in calls,
          "cast_tick's completion READ 320's condition and got None -- the path "
          "reached the read rather than going round it",
          f"skill_condition calls in the tick={calls}")
    check(not authsrv.agent_has_condition(state, FOE, authsrv.effects.CONDITION_BY_NAME["Crippled"]),
          "and the foe carries no Crippled: nothing inflicted on an unreadable row",
          f"worn by {FOE}: {worn(state)}")


def section_control():
    import authsrv

    print("\n5. CONTROL: 320's own row carried -- the same reads and press land Crippled")
    crippled = authsrv.effects.CONDITION_BY_NAME["Crippled"]
    with skills_table(RECORD):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            at0, at15 = authsrv.skill_condition(320, 0), authsrv.skill_condition(320, 15)
        check(at0 == (crippled, 3.0) and at15 == (crippled, 15.0)
              and "skill 320 " not in out.getvalue(),
              "with the row, skill_condition(320) is Crippled for 3 s at rank 0 and "
              "15 s at rank 15, and nothing is announced for 320",
              f"rank 0 {at0}, rank 15 {at15} -- a catch that swallowed the readable "
              f"case would make sections 1-4 pass on a server that inflicts nothing")
        sword = authsrv.agents.item_template("starter_sword")
        state, err, calls, _ = press_320(weapon=sword)
        check(err is None
              and authsrv.agent_has_condition(state, FOE, crippled)
              and any(s == 320 and r and r[0] == crippled for s, r in calls),
              "and the same press, with a sword held (320's weapon_req 0x80), lands "
              "Crippled on the foe through cast_tick's condition read",
              f"error={err!r}, calls={calls}, worn by {FOE}: {worn(state)}")


def section_record_rows():
    """The carried row against the vault's own -- the one vault-only check. It skips
    on the vault/content DIRECTORY, never on what loaded."""
    import authsrv

    print("\n6. the row this file carries, against the vault's own")
    try:
        vaultpath.require_dir("content", why="the vault's skills table, which RECORD copies")
    except SystemExit as exc:
        LEDGER.skip("6. the carried row against the vault's (1 check)",
                    str(exc).splitlines()[0])
        return
    loaded = authsrv.agents.WORLD.rows("skills")
    off, builds = {}, {}
    for k, row in RECORD.items():
        got = loaded.get(k)
        if got is None:
            off[k] = "absent"
            continue
        builds[k] = (getattr(got, "provenance", None) or {}).get("build")
        cols = [c for c, v in row.items() if got.get(c, "absent") != v]
        if cols:
            off[k] = cols
    check(not off,
          f"the {len(RECORD)} carried skills row is the vault's own, column for column",
          f"off={off}, loaded builds={builds} (RECORD copied from {RECORD_BUILD}; a "
          f"regenerated table that moves a carried column reds this -- re-copy the row "
          f"with its build)")


def main():
    rows = effect_rows()
    subj = subjects(rows)
    with skills_table({}):
        section_fixture(rows, subj)
        section_skill_condition(rows)
        section_condition_terms(rows)
    with skills_table({}):
        section_announced(rows, subj)
    with skills_table({}):
        section_press()
    section_control()
    section_record_rows()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
