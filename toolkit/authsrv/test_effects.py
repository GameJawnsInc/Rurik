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

    That check is what settles `bufflog.field3_report`'s open question -- (a)
    field3 is the applying skill's attribute RANK, or (b) it is a
    duration-shaped field -- which that docstring says is "one session away".
    It was zero sessions away.

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

LEDGER = checks.Ledger("the effect channel", floor=47)


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
    except Exception as ex:                                    # noqa: BLE001
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
              f"REFUTED for non-conditions")
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
              "this check exists so 'excluded' cannot become 'they agree too'")


def section_dispatch():
    """Which skills open an episode -- and the ones that look like they should.

    The negative is the point. Desperation Blow carries a real 2-second
    duration and is an ATTACK; nothing in the client's table says what those
    two seconds are, so it opens nothing.
    """
    print("\n3. dispatch: a duration is not a licence to apply an effect")
    import agents
    import authsrv

    def row(sid):
        return agents.WORLD.get("skills", str(sid))

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


def section_wire():
    """Our own emission, through the reader that was written for retail's.

    The strongest available check short of a client: `bufflog.episodes` pairs
    an apply to a removal and scores the residual against the duration the
    apply declared. Feeding it OUR pair has to produce `expired` with a
    residual at zero -- which is the same verdict it gives 83 of retail's 88.
    """
    print("\n5. our own apply/remove pair, read by bufflog")
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
    section_corpus_oracle()
    section_dispatch()
    section_table()
    section_wire()
    section_deaths()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
