"""The effect channel, checked against retail's own 102 applies.

`effects.py` is the writer for `0x0042`/`0x0044`; `bufflog.py` is the reader,
and it was written first against the live corpus. This test is where the two
meet, and section 2 is the one that matters:

    RETAIL'S OWN BYTES, WITH NO FREE PARAMETER. For every apply in the live
    corpus, predict the f32 duration on the wire from the applying skill's
    `duration0`/`duration15` endpoints in the CLIENT'S OWN TABLE and the
    integer in field 3, using the client's own two-point scaler. 96 of 96
    non-condition applies must land exactly. Nothing in the prediction was
    tuned to the corpus: the endpoints are ArenaNet's, the formula was measured
    at 0x005A8920 for the DAMAGE scale, and field3 comes off the wire.

    THE FINDING IS NOT THIS TEST'S. `studies/isle/FINDINGS.md` rung-8 prep
    section 2 settled field3 = the applier's attribute rank on 2026-08-18, and
    CORROBORATED it against GWW across five values and four skills -- a
    stronger kind of evidence than arithmetic, because the wiki and the wire
    share no author or ancestry. What this section adds is scale and
    mechanisation: the whole corpus rather than five hand-checked rows, re-run
    every suite, guarding the reading the server now depends on.
    `bufflog.field3_report`'s docstring said the question was still open for
    two days after it was answered; that is corrected too.

Everything else here guards the two ways this could go wrong quietly: reading a
duration slot that holds a sentinel, and opening an episode for a skill whose
duration means something the table never says.

standard library only.

    python toolkit/authsrv/test_effects.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import checks  # noqa: E402
import effects  # noqa: E402
from codec import Codec  # noqa: E402

LEDGER = checks.Ledger("the effect channel", floor=74)



def _needs_skill_rows(label):
    """True, and a declared skip, when the vault-only `skills` table is absent.

    Five sections here type real skills out of that table -- which stance 346
    is, that 253 is a hex, that 319 replaces 346 -- so on a machine with no
    overlay there is nothing for them to measure. Until 2026-08-31 they did not
    skip, they CRASHED: section 3 on a bare `WORLD.get`, and section 4d on
    `sent[0]` after `apply_effect` correctly did nothing for a skill it could
    not type. An IndexError two frames from the missing row reads like a logic
    bug, which is why this is a guard and not a comment.
    """
    import agents
    try:
        agents.WORLD.get("skills", "346")      # Frenzy, this file's exemplar
    except Exception:                                          # noqa: BLE001
        LEDGER.skip(label,
                    "no 'skills' content rows -- the vault overlay is absent "
                    "(run skilltable.py --emit-content), so the skills this "
                    "section types cannot be read")
        return True
    return False


def section_arithmetic():
    """The scaler, and the four branches of the duration rule.

    Each PERMITTED branch names the retail skill that witnesses it and each
    REFUSED branch names the count of skills shaped that way and the zero
    witnesses they have. A branch with no witness that returns a number
    anyway is the whole failure mode this module was built to avoid.
    """
    print("1. the duration rule, branch by branch, with its witness")

    LEDGER.ok(effects.interp(5, 13, 15) == 13 and effects.interp(5, 13, 0) == 5,
              "the scaler lands on both endpoints at rank 0 and rank 15",
              "max(0, round(lo + (hi-lo)*rank/15.0)) -- the client's own, at "
              "0x005A8920, with a literal 15.0 divisor")
    LEDGER.ok(effects.interp(5, 13, 10) == 10,
              "and on retail's own midpoint: skill 364 at rank 10 is 10.0",
              "5 + 8*10/15 = 10.333 -> 10, which is what the wire carries 27 "
              "times")
    LEDGER.ok(effects.interp(5, 13, 30) == 21,
              "ranks above 15 EXTRAPOLATE rather than saturating",
              "there is no upper clamp in the client's helper; a saturating "
              "reimplementation would agree on every skill we can currently "
              "test and diverge the moment a rank goes over 15")
    LEDGER.ok(effects.interp(0, 0, 12) == 0 and effects.interp(10, -100, 0) == 10,
              "and it floors at zero, which is ArenaNet's own assert",
              "ConstSkill:3769 `(int)result >= 0`")

    scaling = {"duration0": 8, "duration15": 20, "skill_arguments": 1}
    LEDGER.ok(effects.resolve_duration(scaling, 12) == 18.0,
              "bit SET -> interpolate. Rush (319) at Strength 12 is 18 s",
              "witnessed by skills 160, 364, 348 and 814 in the live corpus")

    flat = {"duration0": 30, "duration15": 30, "skill_arguments": 0}
    LEDGER.ok(effects.resolve_duration(flat, 0) == 30.0,
              "bit CLEAR with EQUAL endpoints -> the flat value, 30 s",
              "witnessed, and this is the branch a strict reading gets wrong: "
              "skills 984 and 998 have the duration bit CLEAR and retail sent "
              "duration 30.0 for both. The bit means the duration SCALES, not "
              "that the slot is meaningful")

    none = {"duration0": 0, "duration15": 0, "skill_arguments": 0}
    LEDGER.ok(effects.resolve_duration(none, 12) is None,
              "both endpoints 0 -> None, not 0.0",
              "488 of the 1,333-skill corpus. None makes the caller decide "
              "what no duration means; 0.0 would open a zero-length episode")

    sentinel = {"duration0": 131072, "duration15": 131072,
                "skill_arguments": 2}
    try:
        got = effects.resolve_duration(sentinel, 12)
        refused = None
    except effects.EffectError as ex:
        got, refused = None, str(ex)
    LEDGER.ok(refused is not None and "sentinel" in refused,
              "a SENTINEL in the duration slot is REFUSED, not published",
              f"131072 is 0x20000 and 196608 is 0x30000 -- an enum in the high "
              f"word. 30 corpus skills carry one, 24 of them enchantments, "
              f"which is where 'maintained until removed' belongs. Vital "
              f"Blessing (289) is one, and it is on our own enemy's bar, so "
              f"this refusal fires in every session. Got: {got!r}")

    differ = {"duration0": 1, "duration15": 11, "skill_arguments": 0}
    try:
        got = effects.resolve_duration(differ, 7)
        refused = None
    except effects.EffectError as ex:
        got, refused = None, str(ex)
    LEDGER.ok(refused is not None and "no witness" in refused,
              "and so are DIFFERING endpoints with the scaling bit clear",
              f"49 skills are shaped like this and not one appears in the 102 "
              f"live applies. Interpolating anyway would be a reading with no "
              f"evidence either way. Got: {got!r}")


def section_type_coverage():
    """Every skill in the five effect types has a duration. None of the rest.

    THE CHECK THAT LICENSED ADDING GLYPH without waiting for a run, and it is
    refutable by construction: if "this type_code IS a timed effect" were the
    wrong mapping, the giveaway would be a type full of skills with nothing to
    time. There is not one.
    """
    print("\n1c. does the TABLE agree that these five types are timed effects?")
    if _needs_skill_rows("2. type coverage"):
        return
    try:
        import skilltable
        from pathlib import Path
        exe, _why = skilltable.find_exe()
        data = Path(exe).read_bytes()
        base, count, _score = skilltable.locate_table(data)
    except (Exception, SystemExit) as ex:                                    # noqa: BLE001
        LEDGER.skip("the type-coverage check", f"no pinned client here ({ex})")
        return
    rows = [skilltable.parse_record(data, base, i) for i in range(count)]
    corpus = set(skilltable.player_corpus(rows))
    rows = [r for r in rows if r["id"] in corpus]

    tally = {}
    for r in rows:
        fam = effects.applies_effect(r)
        if fam is None:
            continue
        try:
            d = effects.resolve_duration(r, 0)
            key = "resolves" if d else "NO DURATION"
        except effects.EffectError:
            key = "refused"
        tally[key] = tally.get(key, 0) + 1

    n = sum(tally.values())
    LEDGER.ok(n > 400,
              f"{n} corpus skills fall in the five effect types",
              f"{tally} -- stance, hex, enchantment, glyph, preparation")
    LEDGER.ok(tally.get("NO DURATION", 0) == 0,
              "and NOT ONE of them resolves to 'no duration'",
              f"{tally.get('resolves', 0)} resolve and "
              f"{tally.get('refused', 0)} refuse on a sentinel or an "
              f"unwitnessed shape. This is what says the type list is the right "
              f"mapping rather than five codes we liked the look of -- a type "
              f"that was NOT definitionally a timed effect would be full of "
              f"skills with nothing to time")

    zeros = [r for r in rows
             if r["duration0"] == 0 and r["duration15"] == 0]
    LEDGER.ok(len(zeros) > 400
              and not any(effects.applies_effect(r) for r in zeros),
              f"CONTROL: {len(zeros)} corpus skills DO have 0/0 endpoints, and "
              f"none is an effect type",
              "so the check above is discriminating. 488 skills have no "
              "duration at all -- attacks, signets, most spells -- and the "
              "partition between them and the five types is clean")


def section_corpus_oracle():
    """RETAIL'S OWN APPLIES, predicted with no free parameter.

    Reads every `0x0042` in the live capture corpus through `bufflog.py` and
    predicts each one's f32 duration from the client's skill table. This is the
    check the whole module rests on, and it is the kind this repo prefers: our
    decoder cannot force it true, because both inputs come from outside.
    """
    print("\n2. the live corpus: does field3 predict the duration on the wire?")
    try:
        import bufflog
        import skilltable
        import tape
        import vaultpath
        from pathlib import Path
        live = vaultpath.require_dir("captures", "live",
                                     why="the effect-channel oracle")
        exe, why = skilltable.find_exe()
        data = Path(exe).read_bytes()
        base, count, _score = skilltable.locate_table(data)
    except (Exception, SystemExit) as ex:                                    # noqa: BLE001
        LEDGER.skip("the live-corpus oracle",
                    f"no vault captures or no pinned client here ({ex}). "
                    f"This is the section that carries the module -- a green "
                    f"run without it has checked the arithmetic and none of "
                    f"the evidence")
        return

    codec = Codec()
    applies = []
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        for conn in tape.channel_files(cap):
            try:
                ev = bufflog.read_effects(cap, conn["connection"], codec)
            except Exception:                                  # noqa: BLE001
                continue
            applies.extend(ev["applies"])

    LEDGER.ok(len(applies) >= 100,
              f"the corpus still holds its {len(applies)} effect applies",
              f"102 when this was written. A corpus that shrank is a vault "
              f"that moved, and the numbers below would quietly get easier")

    hits = misses = conds = 0
    worst = []
    for a in applies:
        row = skilltable.parse_record(data, base, a["skill"])
        pred = effects.interp(row["duration0"], row["duration15"], a["field3"])
        if a["skill"] in bufflog.CONDITION_SKILLS:
            conds += 1
        elif abs(pred - a["duration"]) < 1e-6:
            hits += 1
        else:
            misses += 1
            worst.append((a["skill"], a["field3"], a["duration"], pred))

    LEDGER.ok(misses == 0 and hits >= 90,
              f"{hits} of {hits + misses} NON-CONDITION applies predicted "
              f"exactly, {misses} missed",
              f"interp(duration0, duration15, field3) == the f32 on the wire. "
              f"The endpoints are the client's, the formula was measured for "
              f"the DAMAGE scale, and field3 and the duration are retail's "
              f"bytes -- nothing was fitted. Misses: {worst[:4]}")

    # The two rows that carry the refutation on their own.
    by_skill = {}
    for a in applies:
        by_skill.setdefault(a["skill"], set()).add((a["field3"], a["duration"]))
    LEDGER.ok(any(f3 != dur for f3, dur in by_skill.get(160, {(0, 0.0)})),
              "skill 160 carries field3 = 15 against a duration of 13.0",
              f"{sorted(by_skill.get(160, []))} -- reading (b), 'field3 is a "
              f"duration-shaped field', requires those to be the same number. "
              f"REFUTED for non-conditions. This is the row isle section 2 "
              f"calls its cleanest: skill 160 is Windborne Speed, and GWW's "
              f"Master of Winds page supplies BOTH numbers independently -- "
              f"'15 Air Magic' and 13 s at rank 15")
    LEDGER.ok(len(by_skill.get(364, ())) >= 2,
              "and skill 364 appears at TWO ranks, with two different durations",
              f"{sorted(by_skill.get(364, []))} against endpoints 5->13. One "
              f"skill, two field3 values, two durations, both predicted. A "
              f"constant-per-skill field cannot do that, and neither can a "
              f"duration-shaped one")

    cond_rows = [a for a in applies if a["skill"] in bufflog.CONDITION_SKILLS]
    off = [a for a in cond_rows
           if abs(effects.interp(
               skilltable.parse_record(data, base, a["skill"])["duration0"],
               skilltable.parse_record(data, base, a["skill"])["duration15"],
               a["field3"]) - a["duration"]) > 1e-6]
    LEDGER.ok(conds and off,
              f"CONDITIONS are the named exception, and {len(off)} of "
              f"{conds} genuinely break the rule",
              "a condition's duration is set by the skill that INFLICTED it, "
              "not by the condition row's own endpoints -- skill 480 has "
              "endpoints 3/3 and appears on the wire at 9.0. They are excluded "
              "from the count above rather than quietly absorbed into it, and "
              "this check exists so 'excluded' cannot become 'they agree too'. "
              "NOT A HOLE IN THE RULE: isle section 2 fits 481 Crippled to the "
              "same rank reading using PIN DOWN's 3->15 progression. Same rule, "
              "different join -- and this server has no model of which skill "
              "inflicted a condition to make that join with")


def section_dispatch():
    """Which skills open an episode -- and the ones that look like they should.

    The negative is the point. Desperation Blow carries a real 2-second
    duration and is an ATTACK; nothing in the client's table says what those
    two seconds are, so it opens nothing.
    """
    print("\n3. dispatch: a duration is not a licence to apply an effect")
    if _needs_skill_rows("3. dispatch: a duration is not a licence to apply"):
        return
    import agents
    import authsrv

    def row(sid):
        return agents.WORLD.get("skills", str(sid))

    # The `skills` table is VAULT-ONLY (skilltable.py --emit-content), and every
    # check in this section reads eleven rows out of it, so there is nothing
    # here a bare machine can measure. Unguarded until 2026-08-31, when it was
    # the last thing between this file and a verdict without a vault.
    try:
        row(317)
    except Exception as exc:                                   # noqa: BLE001
        LEDGER.skip("3. dispatch: a duration is not a licence to apply",
                    f"no 'skills' content rows ({exc}) -- the vault overlay is "
                    f"absent, so the eleven skills this section types cannot "
                    f"be read")
        return
    fam = {sid: effects.applies_effect(row(sid))
           for sid in (317, 319, 253, 289, 316, 318, 322, 323, 346, 135, 307)}
    LEDGER.ok(fam[317] == "stance" and fam[319] == "stance",
              "Battle Rage and Rush are stances", str(fam[317]))
    LEDGER.ok(fam[253] == "hex" and fam[289] == "enchantment",
              "Scourge Sacrifice is a hex, Vital Blessing an enchantment")
    LEDGER.ok(fam[346] == "stance" and fam[135] == "hex"
              and fam[307] == "enchantment",
              "and R4b's own three exemplars type correctly",
              "Frenzy 346, Faintheartedness 135, Reversal of Fortune 307 -- "
              "the manifest's proposed exemplars for Stance, Hex and "
              "Enchantment (PLAN.md 3.2)")
    LEDGER.ok(fam[322] is None and fam[323] is None,
              "attacks open NOTHING, including one that carries a duration",
              f"Desperation Blow (323) has duration endpoints "
              f"{row(323)['duration0']}/{row(323)['duration15']} and is an "
              f"Attack. What those seconds are is stated nowhere in the "
              f"table, so reading them would be an invention in a "
              f"measurement's clothes -- the same refusal SCALE_MEANS_DAMAGE "
              f"makes one layer up")
    LEDGER.ok(fam[316] is None and fam[318] is None,
              "and so do a Shout and an unnamed type, on our own bar",
              "316 is a Shout: the corpus witnesses TWO shouts opening "
              "episodes (348, 364), which says a shout CAN and not what any "
              "other shout does -- party-wide shouts break the premise that "
              "the target byte names the recipient. 318 is type 16, which no "
              "source in this repo has named at all")

    print("\n3b. and who WEARS it -- the target byte, not the caster's choice")
    LEDGER.ok(effects.effect_recipient(row(319), caster_id=1, target_id=99) == 1,
              "a self stance lands on the caster even with a target selected",
              "Rush's target byte is 0. 75 of 76 stances in the corpus are, "
              "and all 199 attacks are 5 -- the type column is what resolves "
              "the enum rather than a guess")
    LEDGER.ok(effects.effect_recipient(row(253), caster_id=10,
                                       target_id=authsrv.PLAYER_AGENT_ID)
              == authsrv.PLAYER_AGENT_ID,
              "and the enemy's hex lands on the PLAYER, not on the enemy",
              "Scourge Sacrifice's target byte is 5")
    LEDGER.ok(effects.effect_recipient({"target": 4}, caster_id=7,
                                       target_id=None) == 7,
              "an UNRESOLVED target code falls through to the caster's choice",
              "codes 1, 3, 4, 6, 14 and 16 exist and are not decoded here. "
              "Degrading to what the caster aimed at is a known-wrong-but-"
              "bounded answer; inventing a meaning for the enum is not")

    print("\n3c. the durations our two bars actually resolve to")
    got = {}
    for sid in (317, 319, 253):
        rank = (authsrv.player_rank_for_skill(sid) if sid in (317, 319)
                else authsrv.ENEMY_SKILL_RANK)
        got[sid] = effects.resolve_duration(row(sid), rank)
    LEDGER.ok(got == {317: 17.0, 319: 18.0, 253: 18.0},
              "Battle Rage 17 s, Rush 18 s, Scourge Sacrifice 18 s",
              f"{got} -- Strength rank 12 for the player's two, "
              f"ENEMY_SKILL_RANK {authsrv.ENEMY_SKILL_RANK} for the hex. The "
              f"ranks are OURS (content/world.toml says so at length); the "
              f"endpoints and the curve between them are not")
    try:
        authsrv.effects.resolve_duration(row(289), authsrv.ENEMY_SKILL_RANK)
        refused = None
    except effects.EffectError as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None,
              "and Vital Blessing, on that same bar, REFUSES",
              "an honest gap in a running session rather than 131072 seconds "
              "on the wire. The server logs it loudly for exactly that reason")


def section_table():
    """The episode table: ids, expiry, strip."""
    print("\n4. the table -- buff ids, expiry, and death")
    t = effects.EffectTable()
    a = t.apply(1, 319, 12, 18.0, 1000.0)
    b = t.apply(1, 317, 12, 17.0, 1000.0)
    c = t.apply(10, 253, 12, 18.0, 1000.0)
    LEDGER.ok(len({a["buff"], b["buff"], c["buff"]}) == 3,
              "three live episodes get three distinct buff ids",
              f"{[a['buff'], b['buff'], c['buff']]} -- the corpus reuses ids "
              f"within a session but never between two LIVE episodes, and "
              f"`bufflog.episodes` pairs on (target, buff) in time order "
              f"precisely because reuse is real")
    LEDGER.ok(max(a["buff"], b["buff"], c["buff"]) <= 121,
              "and they are small, which is all the corpus actually pins",
              "ids run 5..121 with at most 2 live at once. The allocator is "
              "OURS; what retail does between those constraints is NOT FOUND")

    LEDGER.ok(t.due(1000.0) == [] and len(t.due(1017.5)) == 1,
              "nothing is due before its stated duration; Battle Rage is at 17 s",
              "expiry is scheduled off the duration the APPLY declared, which "
              "is the corpus's measured close rule: the removal lands at "
              "apply + duration, 57 of 88 within 5 ms")
    LEDGER.ok(t.due(1018.0)[0]["skill"] == 317,
              "and `due` returns them oldest-expiry first",
              "so a tick that fires late closes them in the order they should "
              "have closed, not in id order")

    freed = t.close(b["buff"])
    LEDGER.ok(freed is not None and b["buff"] not in t.live,
              "closing releases the id")
    d = t.apply(1, 346, 8, 8.0, 1002.0)
    LEDGER.ok(d["buff"] == b["buff"],
              "and the NEXT apply reuses it -- the corpus's own pattern",
              f"buff {d['buff']} again. One connection in the corpus reuses "
              f"ids 9 times")
    LEDGER.ok(t.close(b["buff"] + 900) is None,
              "closing an id that is not live returns None rather than raising",
              "the tick and a death can both reach a given episode, and a "
              "double close must not stop the world")

    gone = t.strip_agent(1)
    LEDGER.ok(len(gone) == 2 and all(e["agent"] == 1 for e in gone),
              "a strip takes every episode off ONE agent",
              "death is a strip, not an expiry -- `bufflog` classifies an "
              "early removal as `stripped` and names death as a cause")
    LEDGER.ok(t.on_agent(10) and t.on_agent(1) == [],
              "and leaves the other agent's alone",
              f"{[e['skill'] for e in t.on_agent(10)]} still on agent 10")

    try:
        t.apply(1, 321, 0, None, 1000.0)
        refused = None
    except effects.EffectError as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None,
              "and a zero-length episode is REFUSED at the table",
              "two messages that cancel out say nothing and force every "
              "reader to special-case them")

    print("\n4b. an OVERLAPPING re-application gets a NEW id -- retail's rule")
    r = effects.EffectTable()
    first = r.apply(1, 253, 12, 18.0, 1000.0)
    again = r.apply(1, 253, 12, 18.0, 1005.0)
    LEDGER.ok(len(r.live) == 2 and again["buff"] != first["buff"],
              "a second apply while the first is LIVE allocates a new buff id",
              f"buffs {first['buff']} and {again['buff']}. This was built the "
              f"other way for one commit -- collapsed to one episode per "
              f"(agent, skill) -- on the strength of a run in which the client "
              f"drew one icon. THE CORPUS REFUTES THE COLLAPSE: retail has 15 "
              f"overlapping re-applications and every one carries a new id "
              f"(120->121 at a 0.43 s gap, 110->114 at 0.50 s, 121->120 at "
              f"0.09 s), with the first still closing `expired` on its own "
              f"duration")
    LEDGER.ok(first["expires_at"] == 1018.0 and again["expires_at"] == 1023.0,
              "and the FIRST keeps its own expiry rather than being extended",
              f"{first['expires_at']} and {again['expires_at']} -- which is "
              f"what makes retail's overlapping episodes close as `expired` "
              f"instead of `stripped`")
    LEDGER.ok(first["overlapping"] is False and again["overlapping"] is True,
              "the second is FLAGGED as overlapping, because the client drops it",
              "MEASURED twice on 2026-08-20: a repeat 0x0042 for a live "
              "(agent, skill) draws no second icon and does not reset the "
              "timer -- once under a new buff id, and once under the SAME id, "
              "which was a stated prediction and was REFUTED. So re-sending "
              "the apply is not how an effect gets refreshed, and how retail "
              "refreshes one is NOT FOUND")
    r.close(first["buff"])
    later = r.apply(1, 253, 12, 18.0, 1030.0)
    LEDGER.ok(later["buff"] == first["buff"] and later["overlapping"] is True,
              "an id is reused only after its episode CLOSED -- also retail's",
              f"buff {later['buff']} again. Every same-id repeat in the corpus "
              f"has a gap LONGER than the first episode's duration (51->51 at "
              f"14.98 s against 13.0 s, five times over); the overlapping ones "
              f"never reuse. `overlapping` is still true here because the "
              f"OTHER copy is live, which is the honest reading")


def section_exclusive():
    """One stance, one glyph, one preparation -- and hexes stacking as control.

    WIKI, and for two of the three it is text the game itself shows a player:
      * (GWW, "Stance", rev. 2020-10-23), quoting Isokeh in game: "Only one
        Stance can be active at any time... using a new Stance will replace the
        previous one."
      * (GWW, "Preparation", rev. 2020-06-18): "Only one preparation can be
        active at a time. Activating another preparation will override the
        previous one."
      * (GWW, "Glyph", rev. 2024): "If a glyph is cast while another glyph is
        already active, the new one replaces the old one."

    This is also the FIRST answer to "how does an effect get replaced", which
    was NOT FOUND before: re-sending `0x0042` does nothing (measured, both id
    choices), so a replacement must be a real `0x0044` and then a `0x0042`.
    """
    print("\n4c. one stance / glyph / preparation at a time -- the wiki's rule")
    if _needs_skill_rows("4. exclusivity: one stance per character"):
        return
    import authsrv

    t = effects.EffectTable()
    a = t.apply(1, 346, 0, 8.0, 1000.0, type_code=3)
    LEDGER.ok([e["skill"] for e in t.exclusive_on(1, 3)] == [346],
              "a live stance is named as what a NEW stance must replace",
              "the rule is per TYPE, not per skill -- any stance replaces any "
              "stance, which is why this asks by type_code and not by id")
    LEDGER.ok(t.exclusive_on(1, 4) == [] and t.exclusive_on(1, 6) == [],
              "CONTROL: hexes and enchantments name nothing to replace",
              "neither type carries a one-at-a-time rule on GWW and many can "
              "be live at once. A rule applied to all five types would be the "
              "easy wrong generalisation")
    b = t.apply(1, 319, 12, 18.0, 1001.0, type_code=3)
    LEDGER.ok([e["skill"] for e in t.exclusive_on(1, 3)] == [346, 319],
              "the TABLE does not enforce it -- the caller does, and says so",
              "both stances are live here because `apply` is a table operation "
              "and the replacement is a WIRE operation: the old episode has to "
              "leave under its own 0x0044 or the client keeps drawing it. "
              "Enforcing it silently in the table would drop the message")
    LEDGER.ok(t.exclusive_on(2, 3) == [],
              "and it is per AGENT: another agent's stance is not replaced",
              "one stance per CHARACTER, in the wiki's words")

    print("\n4d. and the server actually sends the replacement")
    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))    # noqa: E731
    state = {}
    first = authsrv.apply_effect(send, state, authsrv.PLAYER_AGENT_ID, 346, 0,
                                 None, 0)
    sent.clear()
    second = authsrv.apply_effect(send, state, authsrv.PLAYER_AGENT_ID, 319, 12,
                                  None, 0)
    ops = [op for op, _v, _w in sent]
    LEDGER.ok(ops == [effects.OP_EFFECT_REMOVE, effects.OP_EFFECT_APPLY],
              "casting a second stance sends REMOVE then APPLY, in that order",
              f"{[hex(o) for o in ops]} -- and the order matters: an apply "
              f"before the removal would have two stance icons on screen for "
              f"one frame, and the client discards a second apply anyway")
    LEDGER.ok(sent[0][1] == [authsrv.PLAYER_AGENT_ID, first["buff"]],
              "the removal names the OLD episode's buff id",
              f"{sent[0][1]} against the first episode's buff {first['buff']}")
    LEDGER.ok(len(authsrv.effect_table(state).live) == 1
              and authsrv.effect_table(state).on_agent(
                  authsrv.PLAYER_AGENT_ID)[0]["skill"] == 319,
              "and exactly one stance is left, the new one",
              "the server's own table and the client's screen agree, which is "
              "the whole point of announcing the replacement")


def section_degeneration():
    """What a condition DOES: property 44, and the pips are the wiki's.

    `studies/isle` B4 CONFIRMED property 44 as the net health-regeneration
    rate in max-health fractions per second, quantised at 2/H, riding `0x00A2`
    -- correcting PLAN.md 3.3, which had it on `0x009F` ("the value census
    matches 3.3 exactly; the opcode did not"). It left ONE clause unverified:
    "that one 2 hp/s step equals one HUD pip (needs a screen, not the wire)".

    WIKI (GWW, "Health degeneration"): "each pip represents a loss of two
    health per second"; Bleeding 3, Burning 7, Disease 4, Poison 4; capped at
    10 pips.
    """
    print("\n4e. degeneration -- what a condition actually does")
    import authsrv

    LEDGER.ok(effects.CONDITION_PIPS == {478: 3, 480: 7, 483: 4, 484: 4},
              "four of the ten conditions degenerate, at GWW's own pip counts",
              "Bleeding 3, Burning 7, Disease 4, Poison 4. The other six do "
              "other things -- miss chance, movement, maximum health, casting, "
              "damage, armour -- and giving every condition a pip would be the "
              "easy wrong generalisation")
    fake = [{"skill": 478}, {"skill": 480}]
    LEDGER.ok(effects.pips_from(fake) == 10.0,
              "and the total CAPS at 10, which is reachable",
              "Burning alone is 7 and Bleeding takes it past the cap. An "
              "uncapped sum would out-degenerate retail the moment two "
              "conditions land together")
    LEDGER.ok(effects.pips_from([{"skill": 479}, {"skill": 481}]) == 0.0,
              "CONTROL: Blind and Crippled degenerate nothing",
              "both are real conditions with real durations and neither costs "
              "health")

    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))    # noqa: E731
    state = {"player_health": 100.0, "player_energy": 50.0, "agents": {}}
    authsrv.effect_table(state).apply(authsrv.PLAYER_AGENT_ID, 478, 3, 9.0,
                                      1000.0, type_code=8)
    rate = authsrv.push_regen(send, state, authsrv.PLAYER_AGENT_ID, 0)
    LEDGER.ok(abs(rate - (-0.06)) < 1e-9,
              "Bleeding on a 100-health player is -0.06 per second",
              f"{rate} -- 3 pips x 2 health / 100. The rate is a FRACTION of "
              f"the pool, which is what B4 measured (prop-42 100 with prop-44 "
              f"0.02 and 0.04, exact in f32, twice)")
    LEDGER.ok(len(sent) == 1
              and sent[0][0] == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
              and sent[0][1][:2] == [agents_gv_regen(), authsrv.PLAYER_AGENT_ID],
              "and it rides 0x00A2, the NO-TARGET float twin",
              f"{sent[0][1][:2] if sent else sent} -- PLAN.md 3.3 had these "
              f"properties on 0x009F and the corpus put them here")
    before = len(sent)
    authsrv.push_regen(send, state, authsrv.PLAYER_AGENT_ID, 0)
    LEDGER.ok(len(sent) == before,
              "an UNCHANGED rate sends nothing",
              "the corpus's mid-life property-44s fire when the rate CHANGES; "
              "streaming it every tick is a message retail does not send")

    print("\n4f0. a condition NEVER STACKS -- the longer duration wins")
    # WIKI (GWW, "Condition", Notes): "Reapplied conditions will last the
    # original time period, unless the reapplied duration is greater than the
    # remaining amount of time." A RUN forced this check: with the enemy's
    # Sever Artery on a 0 s recharge the player picked up FIVE Bleeding
    # episodes -- 3 pips, then 6, then 9, then the cap at 10, i.e. TWENTY
    # health a second (run 20260820T191725).
    st = {"player_health": 100.0, "player_energy": 50.0, "agents": {}}
    log = []
    quiet = lambda op, vals, why="": log.append((op, vals))         # noqa: E731
    authsrv.apply_condition(quiet, st, authsrv.PLAYER_AGENT_ID, 478, 9.0, 3,
                            0, 382)
    n_first = len(log)
    authsrv.apply_condition(quiet, st, authsrv.PLAYER_AGENT_ID, 478, 5.0, 3,
                            0, 382)
    tbl = authsrv.effect_table(st)
    LEDGER.ok(len(tbl.live) == 1 and len(log) == n_first,
              "a SHORTER re-application changes nothing and sends nothing",
              f"{len(tbl.live)} episode(s), {len(log) - n_first} extra "
              f"message(s) -- 'reapplied conditions will last the original "
              f"time period'. Nothing about the target changed, so the wire "
              f"stays quiet")
    LEDGER.ok(effects.pips_from(tbl.on_agent(authsrv.PLAYER_AGENT_ID)) == 3.0,
              "and the degeneration stays at ONE Bleeding's three pips",
              "two Bleedings at six pips is the number the run put on screen, "
              "and there is no such thing in the game")
    authsrv.apply_condition(quiet, st, authsrv.PLAYER_AGENT_ID, 478, 21.0, 12,
                            0, 382)
    tail = [op for op, _v in log[n_first:]]
    LEDGER.ok(len(tbl.live) == 1
              and tail == [effects.OP_EFFECT_REMOVE, effects.OP_EFFECT_APPLY],
              "a LONGER one EXTENDS it -- as REMOVE then APPLY, still one",
              f"{[hex(o) for o in tail]}. Not a bare second apply: re-sending "
              f"the apply alone is discarded by the client, measured twice, so "
              f"an extension the client can SEE has to close and reopen")

    print("\n4f. and it spends health WITHOUT drawing a number")
    import time as _time
    state["degen_at"] = _time.time() - 2.0
    sent.clear()
    authsrv.degen_tick(send, state, 0)
    LEDGER.ok(abs(state["player_health"] - 88.0) < 0.01,
              "two seconds of Bleeding costs 12 health",
              f"{state['player_health']:.2f}/100 -- 3 pips x 2 x 2 s")
    damage = [v for op, v, _w in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(not damage,
              "and sends NO property-16 damage while doing it",
              "B4: 'passive ticks are never streamed'. Retail sends the RATE "
              "once and the client animates the bar, so a tick that also sent "
              "damage would draw a stream of red numbers retail never draws")
    LEDGER.ok(not sent,
              "in fact it sends nothing at all on a steady rate",
              f"{len(sent)} message(s) -- the whole point of a rate is that "
              f"the client does the arithmetic")

    print("\n4g. an expiry clears the rate, which is the easy thing to forget")
    table = authsrv.effect_table(state)
    for ep in list(table.live.values()):
        ep["expires_at"] = 0.0
    sent.clear()
    authsrv.effect_tick(send, state, 0)
    regens = [v for op, v, _w in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT
              and v[0] == agents_gv_regen()]
    LEDGER.ok(regens and abs(authsrv._f32_of(regens[-1][2])) < 1e-9,
              "when the condition runs out the rate goes back to 0",
              f"{[round(authsrv._f32_of(v[2]), 4) for v in regens]} -- the "
              f"icon going away and the arrows staying is exactly the bug this "
              f"catches, and it is invisible from the server side")


def agents_gv_regen():
    import agents
    return agents.GV_CHANGE_HEALTH_REGEN


def section_wire():
    """Our own emission, through the reader that was written for retail's.

    The strongest available check short of a client: `bufflog.episodes` pairs
    an apply to a removal and scores the residual against the duration the
    apply declared. Feeding it OUR pair has to produce `expired` with a
    residual at zero -- which is the same verdict it gives 83 of retail's 88.
    """
    print("\n5. our own apply/remove pair, read by bufflog")
    if _needs_skill_rows("6. the wire shape of an effect"):
        return
    import authsrv
    codec = Codec()

    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))    # noqa: E731
    state = {}
    ep = authsrv.apply_effect(send, state, caster_id=authsrv.PLAYER_AGENT_ID,
                              skill_id=319, rank=12, target_id=None,
                              conn_id=0)
    LEDGER.ok(ep is not None and len(sent) == 1
              and sent[0][0] == effects.OP_EFFECT_APPLY,
              "pressing Rush sends exactly one 0x0042", str(sent[:1])[:120])
    vals = sent[0][1]
    LEDGER.ok(vals[0] == authsrv.PLAYER_AGENT_ID and vals[1] == 319
              and vals[2] == 12,
              "[target, skill, field3=RANK, buff, duration]",
              f"{vals} -- field 3 is 12, the player's Strength rank, not the "
              f"18-second duration. That is the corpus's answer and it is "
              f"the field most likely to be filled in wrong")
    LEDGER.ok(abs(authsrv._f32_of(vals[4]) - 18.0) < 1e-6,
              "and the duration is an f32 REINTERPRETED into the dword slot",
              f"raw {vals[4]} -> {authsrv._f32_of(vals[4])}. The schema types "
              f"it `dword` and the client does `fld` on it; writing the "
              f"integer 18 puts 2.5e-44 on the wire")

    blob = codec.encode("GAME_SMSG", effects.OP_EFFECT_APPLY, vals)
    msgs, consumed, err = codec.decode_stream("GAME_SMSG", blob)
    LEDGER.ok(err is None and consumed == len(blob) and msgs[0][1][1:] == vals,
              f"it frames to its final byte and round-trips ({len(blob)}B)",
              str(msgs)[:120])

    # Close it the way the tick does, then read the pair back.
    table = authsrv.effect_table(state)
    for e in list(table.live.values()):
        e["expires_at"] = 0.0
    authsrv.effect_tick(send, state, conn_id=0)
    LEDGER.ok(len(sent) == 2 and sent[1][0] == effects.OP_EFFECT_REMOVE
              and sent[1][1] == [authsrv.PLAYER_AGENT_ID, ep["buff"]],
              "and the tick closes it with 0x0044 [target, buff]",
              str(sent[1][:2]))
    LEDGER.ok(not table.live,
              "leaving no live episode behind",
              "an episode the tick forgets is one our own census scores as "
              "`open` for the rest of the session")

    try:
        import bufflog
        read = bufflog.episodes({
            "applies": [{"t": 100.0, "target": vals[0], "skill": vals[1],
                         "field3": vals[2], "buff": vals[3],
                         "duration": authsrv._f32_of(vals[4])}],
            "removes": [{"t": 118.0, "target": vals[0], "buff": vals[3]}]})
        LEDGER.ok(len(read) == 1 and read[0]["state"] == "expired"
                  and abs(read[0]["residual"]) < bufflog.EXPIRY_TOLERANCE,
                  "and OUR pair reads back as `expired` through bufflog",
                  f"residual {read[0]['residual']:+.3f}s. The reader was "
                  f"written for retail's episodes and knows nothing about "
                  f"this server; it gives the same verdict to 83 of retail's "
                  f"own 88 closes")
        early = bufflog.episodes({
            "applies": [{"t": 100.0, "target": vals[0], "skill": vals[1],
                         "field3": vals[2], "buff": vals[3],
                         "duration": authsrv._f32_of(vals[4])}],
            "removes": [{"t": 104.0, "target": vals[0], "buff": vals[3]}]})
        LEDGER.ok(early[0]["state"] == "stripped",
                  "CONTROL: closing the same episode early reads as `stripped`",
                  "so the check above is discriminating between two outcomes "
                  "rather than agreeing with whatever it is handed -- which "
                  "is also what a death has to look like")
    except Exception as ex:                                    # noqa: BLE001
        LEDGER.skip("the bufflog round-trip", f"reader unavailable ({ex})")


def section_deaths():
    """A corpse carries no effects, on either side."""
    print("\n6. death strips, both halves")
    if _needs_skill_rows("7. death clears the table"):
        return
    import authsrv

    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))    # noqa: E731
    state = {}
    t = authsrv.effect_table(state)
    t.apply(authsrv.PLAYER_AGENT_ID, 319, 12, 18.0, 1000.0)
    t.apply(authsrv.PLAYER_AGENT_ID, 317, 12, 17.0, 1000.0)
    t.apply(10, 253, 12, 18.0, 1000.0)

    gone = authsrv.strip_effects(send, state, authsrv.PLAYER_AGENT_ID, 0,
                                 "the player died")
    LEDGER.ok(len(gone) == 2 and len(sent) == 2
              and all(op == effects.OP_EFFECT_REMOVE for op, _v, _w in sent),
              "both of the player's effects come off, with a 0x0044 each",
              f"{[v for _o, v, _w in sent]}")
    LEDGER.ok(len(t.live) == 1 and t.on_agent(10),
              "and the hex on the ENEMY survives the player's death",
              "a strip is per-agent; stripping the world on any death is the "
              "obvious wrong generalisation")
    LEDGER.ok(authsrv.strip_effects(send, state, 999, 0, "nobody") == [],
              "stripping an agent with no effects sends nothing",
              "every tick a death is processed would otherwise emit an empty "
              "log line")

    print("\n6b. the flag, so the channel can be isolated in a run")
    saved = authsrv.EFFECTS
    authsrv.EFFECTS = False
    try:
        quiet = []
        none = authsrv.apply_effect(
            lambda op, v, why="": quiet.append(op),
            {}, authsrv.PLAYER_AGENT_ID, 319, 12, None, 0)
    finally:
        authsrv.EFFECTS = saved
    LEDGER.ok(none is None and not quiet,
              "--no-effects applies nothing and sends nothing",
              "the same shape as --no-armour-term: a control that removes ONE "
              "term, so a run can say whether this channel is what the client "
              "reacted to")
    LEDGER.ok(authsrv.EFFECTS is True,
              "and the flag is ON by default",
              "an effect that only appears behind a flag is an effect nobody "
              "watches")


def main():
    section_arithmetic()
    section_type_coverage()
    section_corpus_oracle()
    section_dispatch()
    section_table()
    section_exclusive()
    section_degeneration()
    section_wire()
    section_deaths()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
