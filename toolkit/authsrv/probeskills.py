"""Skill bar, casting, buffs, minions, conditions, effect extension.

The skill arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the skillbar copy and disable arms, the partial-bar arm, the three
casting-property arms and the real-spell control, the 211 unlock arm, the
deep-wound, heal-number and condition-render arms, the effect-extension arm, the
lone property-17 control, the buff-type and buff-side arms, the minion counter,
the cast-modifier ordering arm, the pool-fraction arm, and the nineteen registry
entries that fire them.

It is leaf shaped by the same rule `probebase.py` is, and one step further in:
this module reads NO `agents` name at all, so its imports are the standard
library plus `probebase` and nothing else. It MUST NOT import `probes`:
`probes.py` runs as `__main__` under `python toolkit/authsrv/probes.py`, so a
leaf importing it back would load a SECOND copy of that module, with its own
`PROBES` dict and its own flags.

WHERE THE REFERENTS WENT. Every "above" and "below" in the comments that travel
with this code points INSIDE this file -- `_cast_spell_steps`' "the pair above
used an attack" is `_cast_one_steps`, still directly above it here, and the rest
are step orderings and readings within one arm -- so none of them is reworded.
The three outward references name PROBES, not source: `health_shrink` and
`health_max` (in `probes.py`, headed for `probeunitsetup.py`) and `die_0x2d` (in
`probes.py`) are all still in `probes.PROBES` and still run as `--probe <name>`,
which is what those sentences are about. `use_skill_capture` moved with the
skill entries it sits among even though it builds nothing: it carries
`steps=[]`, because it is a press-the-keys-and-read-the-capture arm.

`PROBES` here holds only the nineteen skill entries. `probes.py` opens its own
dict, merges this one in with a duplicate-key raise, and keeps `get`, `names`,
`describe` and `check_encodable` -- so `probes.get("cast_anim", ...)` answers
exactly as it did, and `names()` is still `sorted(PROBES)` and still returns the
same 97 names in the same order. Every name this module binds except `PROBES` is
also re-exported by `probes.py`, at the two sites the builders were cut from, so
`vars(probes)` still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probebase import (                                     # noqa: E402
    ENEMY_AGENT_ID, PROBE_BAR_SKILL, PROP_CAST_SKILL, PROP_CAST_TIME,
    Probe, Step, _f32)


def _skill_copy_steps(agent_id):
    """Does the lifecycle's third dword have to match the skillbar's 2nd array?

    studies/skillcast/FINDINGS.md section 3: the client walks its eight bar
    slots and acts only on the one where BOTH slot+0x0C == field 2 and
    slot+0x10 == field 3, and slot+0x10 is filled straight out of
    SKILLBAR_UPDATE's second array -- the one every catalogue calls
    `pvp_masks`. If that reading is right, a recharge addressed to the wrong
    copy finds no slot and does nothing at all, silently.

    This is the whole point of the probe: the failure mode is silence, so it
    has to be run against a bar whose copies are deliberately NOT zero.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1],
             "skillbar with copy = 0 in every slot",
             "the bar. Eight icons, as usual."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 0, 10],
             "recharge (skill, copy=0) for 10s",
             "slot 1. The cooldown sweep should start and count down 10s."),
        Step(14.0, 0x00DA, [agent_id, bar, [7] * 8, 1],
             "same skillbar, copy = 7 in every slot",
             "the bar. Eight icons still -- copy is not the id, so nothing "
             "should look different."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 0, 10],
             "recharge (skill, copy=0) -- now the WRONG copy",
             "slot 1. PREDICTION: nothing happens. If it greys out anyway, "
             "field 3 is not matched against the bar and section 3 is wrong."),
        Step(6.0, 0x00E5, [agent_id, bar[0], 7, 10],
             "recharge (skill, copy=7) -- the right copy",
             "slot 1. PREDICTION: NOW it greys out and counts 10s."),
    ]


def _skill_disable_steps(agent_id):
    """Is unnamed opcode 231 'skill disabled'?"""
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E5, [agent_id, bar[1], 0, 30], "229: recharge slot 2, 30s",
             "slot 2 starts a 30-second sweep."),
        Step(6.0, 0x00E7, [agent_id, bar[1], 0], "231 on the same slot",
             "slot 2. PREDICTION: the sweep stops counting down and the icon "
             "stays dark indefinitely -- 231 writes recharge = 0xFFFFFFFF, "
             "which the client's own getter turns into INT_MAX remaining."),
        Step(10.0, 0x00E6, [agent_id, bar[1], 0], "230: recharged",
             "slot 2. PREDICTION: instantly ready again, well before 30s have "
             "passed. 230 writes recharge = 0 with no arithmetic."),
    ]


def _skill_partial_steps(agent_id):
    """Opcode 232 carries a float. Is it 'remaining', with field 4 the total?

    The handler multiplies field 5 by 1000.0 and adds the skill timer, so
    field 5 is seconds and it is what sets the clock. Field 4 is converted to
    a float and handed to the UI alongside it, and never touched otherwise.
    The obvious reading is remaining-vs-total; the sweep's ANGLE is what would
    show it, because a quarter-full arc means the client knows about a 40s
    total it was not given anywhere else.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E8, [agent_id, bar[2], 0, 40, _f32(10.0)],
             "232 on slot 3: field4 = 40, field5 = 10.0f",
             "slot 3. PREDICTION: it counts down TEN seconds, not forty. "
             "Then look at the sweep's starting angle: about a quarter dark "
             "means field 4 is the total; a full dark disc means field 4 is "
             "something else and the UI ignores it."),
        Step(14.0, 0x00E8, [agent_id, bar[3], 0, 0, _f32(2.5)],
             "232 on slot 4: field4 = 0, field5 = 2.5f",
             "slot 4. PREDICTION: a 2.5-second sweep -- fractional, which 229 "
             "cannot express. If it is instead instant or 2 seconds flat, "
             "field 5 is not a float and the fld we read is doing something "
             "else."),
    ]


def _cast_anim_steps(agent_id):
    """What makes a body play the cast animation -- 228, or property 60?

    The headline question of studies/skills section 8, and the static answer
    is unambiguous enough to be worth stating hard: the opcode 228 handler
    touches only a bookkeeping array and a UI notification, it never reaches
    AgentView, AND it returns immediately without doing even that when the
    message names the local player. Property 60 is the one that reaches
    AvApi and queues the animation event.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(5.0, 0x00E4, [agent_id, bar[4], 0], "228 SKILL_ACTIVATE on us",
             "the CHARACTER's body, and slot 5. PREDICTION: absolutely "
             "nothing, in both places. The handler compares the message's "
             "agent id against the local player's and returns."),
        Step(8.0, 0x009F, [PROP_CAST_SKILL, agent_id, bar[4]],
             "property 60 = the same skill id",
             "the character's body. PREDICTION: THIS is the one that plays "
             "the casting animation. If it does, the cast animation is a "
             "property update and 228 is bookkeeping."),
        Step(8.0, 0x00E3, [agent_id, bar[4], 0], "227 to close the cast",
             "nothing should visibly change; the client is releasing a "
             "pending entry it never created for us. Watch Gw.log for "
             "'Pending skill 320 copy 0 not found' -- that message is the "
             "client telling us in words what field 3 is called."),
    ]


def _cast_one_steps(agent_id, which):
    """`cast_anim` with ONE variable, because timing discrimination failed.

    The combined probe fires 228 and property 60 in the same run, eight
    seconds apart, and asks the operator which one animated. On 2026-08-15
    that failed for a plain reason: the operator saw a sparkle, lost count
    of the gaps, and could not attribute it -- and an observation that
    cannot be attributed is not evidence about either message. (The agent
    running it had also quoted the gaps wrong, as ~3 s, because `Step`'s
    first field is a DELAY from the previous step rather than an absolute
    time. Both halves of that failure are worth recording.)

    So: same bar, same map, same everything, and exactly ONE message under
    test per run. The operator answers "did anything visible happen after
    the bar settled" -- yes or no, no counting. Run both and the pair is a
    control for each other.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    steps = [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready. THE SHARED CONTROL: this message is "
             "in both runs, so anything it causes is not the variable."),
    ]
    if which == "228":
        steps.append(
            Step(8.0, 0x00E4, [agent_id, bar[4], 0], "228, and NOTHING else",
                 "the CHARACTER's body and the bar, for the whole rest of "
                 "the run. PREDICTION: nothing, ever. Its handler compares "
                 "the named agent against the local player and returns."))
    else:
        steps.append(
            Step(8.0, 0x009F, [PROP_CAST_SKILL, agent_id, bar[4]],
                 "property 60, and NOTHING else",
                 "the CHARACTER's body. PREDICTION: the cast animation "
                 "plays. This is the run that should show the sparkle."))
    return steps


def _cast_spell_steps(agent_id):
    """Property 60 with a REAL SPELL, because the pair above used an attack.

    `cast_prop60_only` sent property 60 with `PROBE_BAR_SKILL + 4` = 320,
    Hamstring -- `type_code` 14, an attack skill, `activation = 0.0 s`. It
    does not cast, and the client's own table gives it ONE animation id
    (566) with the other five slots null. So a weapon sparkle is the whole
    of what that skill has, and calling the result "the cast animation" was
    an overclaim the owner caught.

    105 Deathly Swarm is the opposite end: a 2.0 s Necromancer spell whose
    six animation ids are [204, -, 201, -, -, 199] -- THREE components in
    three different slots. If one property-60 send reproduces a full cast,
    this is where a body animation shows; if it still renders only an
    effect, then property 60 drives the EFFECT and the body animation comes
    from somewhere else, which is a different and more useful answer than
    the one we nearly wrote down.

    The bar is sent first with 105 in slot 5 so the client has the skill in
    hand -- the pair above showed the client will render for a skill it has
    on the bar, and changing that variable too would spoil the comparison.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    bar[4] = 105
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1],
             "bar with 105 Deathly Swarm in slot 5",
             "the bar. Slot 5 should now be a Necromancer spell, not "
             "Hamstring."),
        Step(8.0, 0x009F, [PROP_CAST_SKILL, agent_id, 105],
             "property 60 = 105 Deathly Swarm (2.0 s spell)",
             "THE CHARACTER'S BODY, not the weapon. PREDICTION: a casting "
             "stance -- arms, posture, something the model does -- because "
             "this skill carries three animation components where Hamstring "
             "carried one. If all that appears is another weapon effect, "
             "property 60 drives EFFECTS and the body animation has another "
             "source."),
    ]


def _unlock_211_steps(agent_id):
    """Opcode 211 is unnamed everywhere and shaped like both unlock messages.

    Statically it writes a second skill bitmap into ChCliSkill's context, at
    the member BEFORE the one 219 writes, and -- unlike 219 -- broadcasts no
    UI notification. Its write path has exactly one caller, its own handler,
    and nothing in the image reads the array it fills. So the prediction is
    that it does nothing observable, and the value of running it is that a
    NULL result here is informative rather than a dead end.
    """
    empty = [0] * 128
    ours = [0] * 128
    for sid in range(PROBE_BAR_SKILL, PROBE_BAR_SKILL + 8):
        ours[sid // 32] |= 1 << (sid % 32)
    return [
        Step(2.0, 0x00DB, [empty], "219: character skills -> none",
             "the Skills and Attributes panel (K). Note what is listed."),
        Step(8.0, 0x00D3, [ours], "211: our eight bar skills",
             "the same panel, and the skill picker. PREDICTION: no change "
             "anywhere. If something DOES change, 211 has a reader we did "
             "not find and section 5 needs reopening."),
        Step(8.0, 0x00DB, [ours], "219: the same eight, via 219 this time",
             "the same panel. PREDICTION: this one does change it -- 219 is "
             "the bitmap the client bit-tests before answering 'how many "
             "copies of this skill do you own'."),
    ]


def _deep_wound_steps(agent_id):
    """SKILLS-DW: retail's Deep Wound batch, arm by arm, read off the HUD number.

    Retail's apply is three messages in one batch -- [0x0042 482, 0x00F1
    word|0x22, 0x009F 42 = max*0.8] -- and its close the mirror (isle 8.2,
    deepwoundjoin.py, 2 of 2 each). The server now sends exactly that. What a
    capture cannot say is what each message DOES on screen, so this sends them
    one arm at a time: the episode alone, then the full batch on a full pool,
    then the full batch on a damaged pool (where the client's signed delta,
    `health_shrink`, predicts a number no other reading predicts).
    """
    a = agent_id
    return [
        Step(4.0, 0x0042, [a, 482, 0, 1, _f32(12.0)],
             "ARM A: 66 skill 482 for 12 s, ALONE -- no status word, no maximum",
             "the condition icon and its brown arrow appear; the HUD number "
             "stays 100/100. THE QUESTION: does the right 20% of the health "
             "bar turn grey? Prediction: NO -- the grey rides status bit 0x20 "
             "(step 4), not the episode. Grey here refutes that and says the "
             "client types Deep Wound from the skill id alone."),
        Step(8.0, 0x0044, [a, 1], "68: remove it", "icon goes, nothing else moves."),
        Step(4.0, 0x0042, [a, 482, 0, 2, _f32(12.0)],
             "ARM B: the retail batch on a FULL pool -- 1 of 3, the apply",
             "icon back."),
        Step(0.0, 0x00F1, [a, 0x22],
             "ARM B 2 of 3: status word 0x22 (0x02 condition | 0x20 deep wound)",
             "prediction: the right 20% of the bar greys NOW, before the "
             "maximum moves."),
        Step(0.0, 0x009F, [42, a, 80],
             "ARM B 3 of 3: int property 42 = 80",
             "HUD 80/80 with the bar FULL -- the delta (100 + (80-100) = 80) "
             "lands on the new maximum exactly, so a full pool stays full, "
             "which is the wiki's 'still considered at full health'."),
        Step(8.0, 0x0044, [a, 2], "68: remove -- the close, 1 of 3", "icon goes."),
        Step(0.0, 0x00F1, [a, 0], "close 2 of 3: status word 0",
             "the grey 20% clears."),
        Step(0.0, 0x009F, [42, a, 100], "close 3 of 3: int property 42 = 100",
             "HUD 100/100: the 20 came back with the maximum."),
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.75)],
             "damage -0.75 -- the pool to a quarter",
             "HUD 25/100. The run's own control, measured twice before."),
        Step(4.0, 0x0042, [a, 482, 0, 3, _f32(12.0)],
             "ARM C: the retail batch on a DAMAGED pool -- the apply", "icon."),
        Step(0.0, 0x00F1, [a, 0x22], "ARM C: status 0x22", "grey 20%."),
        Step(0.0, 0x009F, [42, a, 80],
             "ARM C: int property 42 = 80 onto 25 of 100",
             "THE HUD NUMBER. Signed delta (health_shrink, MEASURED): 25 + "
             "(80-100) = 5 of 80. A FRACTION reading gives 20; 'ignored' gives "
             "25. Three mechanisms, three numbers -- and 5 is what the server's "
             "own book now says, so the orb must read what the log reads."),
        Step(8.0, 0x0044, [a, 3], "ARM C close 1 of 3", "icon goes."),
        Step(0.0, 0x00F1, [a, 0], "ARM C close 2 of 3: status 0", "grey clears."),
        Step(0.0, 0x009F, [42, a, 100], "ARM C close 3 of 3: maximum 100",
             "HUD 25/100 -- the delta gives the 20 back and the pool is where "
             "the damage left it. 45 would mean the restore was a refill to "
             "the fraction; 5 would mean the maximum moved without the "
             "health."),
    ]


def _heal_number_steps(agent_id):
    """SKILLS-HN: the heal number on a damaged pool, then on a full one.

    Retail's heal batch is `[58, 21, 21, 55, 55]` or just `[58, 55]` -- no
    property rides beside a 55 that does not also ride beside damage
    (healjoin.py, 800 events), so whatever the client draws it draws from the
    55 alone. The 2026-08-20 frames show it: a pale blue '+46' over the
    player, 3 of 3, missed by a scan for green. What no capture can show is
    OUR client's screen on a full pool, where retail sends the number anyway.
    """
    a = agent_id
    return [
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.46)],
             "damage -0.46: the pool to 54 of 100",
             "orb 54; a damage number draws (the run's own control)."),
        Step(3.0, 0x00A3, [55, a, a, _f32(0.46)],
             "ARM A: heal +0.46 onto 54 -- lands whole",
             "a pale blue '+46' rises from the player's head, orb 100."),
        Step(4.0, 0x00A3, [55, a, a, _f32(0.46)],
             "ARM B: heal +0.46 onto a FULL pool -- the overheal",
             "WIKI: the same '+46', orb stays 100. The retired rule sent "
             "nothing here. An assert dialog is the refutation that matters."),
        Step(4.0, 0x00A3, [55, a, a, _f32(0.10)],
             "ARM B again, smaller: +0.10 onto full",
             "'+10' if the number is the amount SENT rather than the amount "
             "that landed (which is 0)."),
    ]


def _condition_render_steps(agent_id):
    """Isle rung 4: does 0x0042 carrying a CONDITION skill id render a condition?

    studies/isle/FINDINGS.md B3/B6 background: the client's skill table marks ids
    478-486 + 2077 as type_code 8 (the ten conditions), s_charCondition names the
    nine condition strings, and the buff opcode family has ZERO ArenaNet witnesses
    for 0x0042 -- so whether a condition arrives as a buff-add with the condition
    skill's id is exactly the channel assumption rung 8's live session would
    otherwise spend its first two minutes on. The tooltip is the measurement:
    the client resolves the skill name from its own table, so whatever name the
    operator reads settles the id -> condition mapping for that id, which no
    offline pass could (the mapping order is UNVERIFIED).
    """
    return [
        Step(2.0, 0x0042, [agent_id, 478, 0, 1, _f32(15.0)],
             "66: skill 478 (type_code 8), 15 s",
             "TWO places at once: the effects area above the skill bar, and "
             "the health bar. A CONDITION shows a small brown DOWN arrow on "
             "the bar and a gold-bordered icon; a plain buff icon with no "
             "arrow means 0x0042 carries the skill but the client does not "
             "classify it as a condition from the id alone. READ THE TOOLTIP "
             "and say the name out loud -- that name is the measurement."),
        Step(9.0, 0x0044, [agent_id, 1], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, 480, 0, 2, _f32(15.0)],
             "66: skill 480, 15 s",
             "same two places, same tooltip read. A DIFFERENT condition name "
             "than step 1 means the ids are per-condition, not a family id."),
        Step(9.0, 0x0044, [agent_id, 2], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, 2077, 0, 3, _f32(15.0)],
             "66: skill 2077 (Cracked Armor's id, the out-of-block member)",
             "if this renders a condition too, the type-8 set travels as a "
             "set; if it renders nothing or a bare buff, 2077 is special."),
        Step(9.0, 0x0044, [agent_id, 3], "68: remove it", "clean up."),
    ]


def _effect_silent_extend_steps(agent_id):
    """Does the client self-expire an effect, or does it wait for `0x0044`?

    THIS QUESTION IS RETAIL'S, and the Isle arc is what raised it.
    `studies/isle/FINDINGS.md` 8.6 measured ArenaNet extending a live effect by
    sending NOTHING: across two live captures, 15 episodes closed LATE -- by
    +1.25 s to +55.0 s against their own stated duration -- with no intervening
    `0x0042`, no `0x0044`, and no other traffic in the window. The seven
    episodes that were NOT being refreshed closed within +/-0.042 s of
    `apply + duration`, over three different durations and both captures, which
    is what rules out a coarse sweep and makes the long holds real.

    OUR SERVER DOES SOMETHING RETAIL DOES NOT. `effects.EffectTable.apply`'s own
    docstring ends "how retail refreshes one is NOT FOUND", and
    `studies/skills` concluded from OUR implementation that a longer
    re-application "extends as REMOVE-then-APPLY -- the only replacement shape
    the client honours". Retail plainly does not do that here. But 8.6 is a
    WIRE measurement and cannot see the screen, so it leaves the half that
    decides what our server may emit: between `apply + duration` and the late
    `0x0044`, IS THE EFFECT STILL DRAWN?

    The probe sends raw messages and keeps no server-side effect table, which is
    the point -- it isolates the CLIENT's own timer from ours.
    """
    return [
        Step(2.0, 0x0042, [agent_id, 478, 0, 1, _f32(10.0)],
             "CONTROL apply: skill 478 (Bleeding), duration 10.0",
             "the effects area above the skill bar. Icon appears with a brown "
             "down-arrow. Note the timer bar -- it should start full."),
        Step(10.0, 0x0044, [agent_id, 1],
             "CONTROL remove: 0x0044 at exactly apply + duration",
             "the icon goes. This is the shape our server emits today and the "
             "rig's positive control: it proves a removal removes, so a "
             "persisting icon later cannot be blamed on a dead channel."),

        Step(4.0, 0x0042, [agent_id, 480, 0, 2, _f32(10.0)],
             "TREATMENT apply: skill 480 (Burning), duration 10.0 -- and then "
             "NOTHING is sent for 25 s",
             "icon appears, bar full. From here the server goes silent, which "
             "is exactly what retail does while you stand in a Student's ring."),
        Step(13.0, 0x0000, [],
             "WATCH at apply + 13 s -- THREE SECONDS PAST THE STATED DURATION. "
             "This is the measurement the whole probe exists for.",
             "IS THE ICON STILL THERE? Say yes or no out loud before anything "
             "else, then describe the timer bar: full, empty, drained, absent, "
             "or refilled. PREDICTION: the icon is STILL DRAWN and the bar has "
             "drained to empty, because retail holds effects far past their "
             "stated duration with no traffic and a client that self-expired "
             "would leave ArenaNet rendering nothing while the condition is "
             "still costing health. THE RIVAL OUTCOME IS THE BIGGER RESULT: if "
             "the icon is GONE, the client runs its own authoritative timer, "
             "retail's silent extension is invisible to the player, and our "
             "server cannot extend silently for anything that must be SEEN.",
             sends=False),
        Step(7.0, 0x0000, [],
             "WATCH at apply + 20 s -- twice the stated duration",
             "same two questions. A yes here rules out a slow fade or a "
             "one-frame lag at the boundary being mistaken for persistence.",
             sends=False),
        Step(5.0, 0x0044, [agent_id, 2],
             "TREATMENT remove: the late 0x0044, at apply + 25 s",
             "does the icon go NOW? If it was still drawn and this removes it, "
             "the client is server-authoritative on expiry and a silent "
             "extension is legal -- our substrate can stop emitting the "
             "REMOVE-then-APPLY pair retail never sends. If the icon had "
             "already gone, watch for anything odd here: a removal for an "
             "effect the client has forgotten is a shape we would be emitting "
             "blind."),
        Step(6.0, 0x0000, [],
             "END: quiet frames",
             "the final state of the effects area, and whether the client is "
             "still alive.",
             sends=False),
    ]


def _lone_p17_steps(agent_id, origin):
    """Isle rung 4: what does a LONE property 17 draw, and does the orb move?

    studies/isle/FINDINGS.md B6 settled the ledger half on ArenaNet's wire: a
    lone p17 debits the server's health ledger and can kill (agent 38, 9 damage
    on a 3/8 body, death 244 ms later). What the corpus cannot show is the
    CLIENT's presentation -- studies/agentprops/FINDINGS.md 1 reads the handler
    as raising a damage notification WITHOUT modifying the client-side health
    record, which predicts a number that draws while the orb stays put.
    """
    return [
        Step(2.0, 0x00A3, [16, agent_id, ENEMY_AGENT_ID, _f32(-0.10)],
             "163: property 16, -0.10 of max, the control",
             "the player orb and the space over the character. Expect the orb "
             "to drop ~10 points and a damage number to draw. This is the "
             "known-good kind; read the next two against it."),
        Step(8.0, 0x00A3, [17, agent_id, ENEMY_AGENT_ID, _f32(-0.10)],
             "163: property 17 ALONE, same magnitude",
             "BOTH questions at once. (1) Does a number draw, and does it look "
             "DIFFERENT from step 1 -- size, colour, anything? Say what you "
             "see, not what a crit 'should' look like. (2) Does the ORB move? "
             "PREDICTION from the client read: the number draws, the orb does "
             "NOT move -- 17's handler raises the notification and skips the "
             "health record. If the orb moves too, 17 is a full damage kind "
             "client-side and the agentprops reading is wrong."),
        Step(8.0, 0x00A3, [18, agent_id, ENEMY_AGENT_ID, _f32(-0.10)],
             "163: property 18, the third kind in the dispatch",
             "same two questions. 18 shares 17's notification path in the "
             "dispatch read; no live capture has ever carried one."),
        Step(6.0, 0x00A2, [34, agent_id, _f32(1.0)],
             "162: property 34 = 1.0, the pool setter, restore",
             "the orb refills to full (pool_fraction measured 34 as a SETTER: "
             "fraction x maximum). If it was already full, nothing changes "
             "-- which is itself the answer to step 2's orb question."),
    ]


def _buff_type_steps(agent_id):
    """Opcode 66 field 3: Headquarter's `effect_type` or GWCA's `attribute_level`?

    studies/skillcast section 14: the client stores field 3 at buff record
    +0x04 and does not interpret it in ChCliBuff at all, so static analysis
    runs out here. The two readings predict visibly different things, which is
    what makes this worth a probe rather than an argument.

    KEEP buffId SMALL. GmEffect:3030 asserts
    `buffId < (CTL_EFFECT_UPKEEP_TERM - CTL_EFFECT_UPKEEP_FIRST)` -- the id
    indexes a UI frame-code range, so a large one asserts in the client the way
    an out-of-range unlock bit does.
    """
    skill = PROBE_BAR_SKILL
    return [
        Step(2.0, 0x0042, [agent_id, skill, 0, 1, _f32(30.0)],
             "66: field3 = 0 (Headquarter: condition/shout)",
             "the effect area above the skill bar. Note WHERE the icon "
             "appears and what its tooltip says."),
        Step(7.0, 0x0044, [agent_id, 1], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, skill, 14, 2, _f32(30.0)],
             "66: field3 = 14 (Headquarter: enchantment)",
             "PREDICTION A (effect_type): the icon lands in a DIFFERENT "
             "place or draws a different border from the first one. "
             "PREDICTION B (attribute_level): it looks identical and only "
             "the numbers in the tooltip change."),
        Step(7.0, 0x0044, [agent_id, 2], "68: remove it", "the icon goes."),
        Step(4.0, 0x0042, [agent_id, skill, 12, 3, _f32(30.0)],
             "66: field3 = 12 (a plausible attribute rank, not a "
             "Headquarter type code)",
             "if 12 renders as happily as 0 and 14 did, the field is not a "
             "four-value enum and Headquarter's effect_type reading is in "
             "trouble."),
        Step(7.0, 0x0044, [agent_id, 3], "68: remove it", "clean up."),
    ]


def _minion_count_steps(agent_id):
    """Is 0x0093's value dword the agent's MINION COUNT?

    ANSWERED YES, 2026-08-20 (captures 20260820T081504 and 20260820T082018,
    studies/pvpui/FINDINGS.md 33.5): 7 drew a minion icon reading 7 with the
    tooltip 'You are currently controlling 7 minions.', 1 redrew it as
    '1 minion.' -- template 50499's own [s] plural resolving -- and 0 removed
    the row. Kept runnable as the calibration for that finding.

    THE BUFF IN STEP 1 IS A DISCRIMINATOR, NOT A PRECONDITION, and the
    distinction is a correction to this docstring's first version. The bare
    three-send form works perfectly with no buff at all; a session read the
    wrong screenshots (hold*.png, which begin AFTER the --walk plan and so
    after the probe has cleaned up), called it a null, and invented a
    'the monitor must exist first' mechanism to explain the artifact. What
    the buff actually buys is the control on step 4: with an icon sent
    alongside, count 0 must clear the MINION row and leave the buff icon
    standing, which separates 'the row went' from 'the monitor went'.

    Read w*.png when a --walk is in play. Seven is deliberate: not 0, not 1,
    not a plausible default, so a sentence reading '7' cannot be a
    coincidence of some other field.
    """
    skill = PROBE_BAR_SKILL
    return [
        Step(2.0, 0x0042, [agent_id, skill, 0, 1, _f32(120.0)],
             "0x0042 first: a buff on our own agent, as the DISCRIMINATOR "
             "for step 4 (not a precondition -- the bare form works)",
             "an effect icon appears top-left."),
        Step(5.0, 0x0093, [agent_id, 7],
             "0x0093: minion count 7",
             "OBSERVED 2026-08-20: a minion icon appears to the LEFT of the "
             "buff icon carrying the number 7, tooltip 'You are currently "
             "controlling 7 minions.' Any other number refutes pvpui 33."),
        Step(9.0, 0x0093, [agent_id, 1],
             "0x0093: minion count 1 -- the singular",
             "OBSERVED: the same row reading 1, and the tooltip drops the "
             "s -- 'controlling 1 minion.'"),
        Step(9.0, 0x0093, [agent_id, 0],
             "0x0093: minion count 0",
             "OBSERVED: the minion row disappears and the step-1 buff icon "
             "STAYS. That contrast is the control."),
        Step(7.0, 0x0044, [agent_id, 1], "0x0044: drop the buff",
             "cleanup -- now the effect icon goes too."),
    ]


def _buff_side_steps(agent_id):
    """Do 63 and 65 file the same buff under two different agents?

    The client keeps TWO lists per agent -- a source list at BuffState+0x04
    and a target list at +0x14 -- and 63/64 touch the first while 65/66/67/68
    touch the second. A maintained enchantment should therefore need BOTH 63
    and 65 with the same buffId: one to say 'you are maintaining this' and one
    to say 'this is on them'.
    """
    skill = PROBE_BAR_SKILL
    return [
        Step(2.0, 0x0041, [agent_id, agent_id, skill, 0, 4],
             "65 BuffTargetAdd: source and target both us",
             "the effect area. An icon with NO countdown -- opcode 65 stores "
             "duration 0.0f, so it should sit there indefinitely."),
        Step(8.0, 0x003F, [agent_id, agent_id, skill, 0, 4],
             "63 BuffSourceAdd: the same buffId, the source side",
             "PREDICTION: a SECOND indicator appears, in the maintained-"
             "enchantment upkeep row rather than the effects row. If nothing "
             "changes, the two lists do not both drive UI and section 14's "
             "source/target split matters less than it looks."),
        Step(8.0, 0x0040, [agent_id, 4], "64 BuffSourceRemove",
             "PREDICTION: the upkeep indicator goes and the effect icon "
             "stays -- they are separate records keyed by the same buffId."),
        Step(6.0, 0x0044, [agent_id, 4], "68 BuffTargetRemove",
             "now the effect icon goes too."),
    ]


def _cast_modifier_order_steps(agent_id):
    """Must the cast-time modifier arrive AFTER the cast-start property?

    studies/skillcast section 16.2, and this probe exists because that section
    makes a claim no other reading can check. Three properties -- 5, 51 and 61
    -- write one float at the agent object's +0x124, and the cast-start
    properties 4, 50 and 60 END their case body by ZEROING it:

        0x0081BCE1   fldz
        0x0081BCE3   fstp dword ptr [esi+0x124]

    So a modifier sent before the cast it was meant to modify is wiped by that
    cast. That is the opposite ordering from property 10 before the damage
    property, and from 23-27 before the animation that consumes them -- three
    sticky-parameter mechanisms in one dispatcher, two wanting the parameter
    first and one wanting it second. Getting it backwards would mean every cast
    this server ever speeds up or slows down silently plays at normal speed.

    DEPENDS ON THE `cast_anim` PROBE. Everything here assumes property 60 plays
    the animation, which is section 6's static answer and has never been
    observed. Step 2 is therefore the self-control: if a bare property 60 does
    not visibly cast, steps 3-5 are uninterpretable and the run should stop --
    the same rule `die_0x2d` follows by re-running the damage measurement first.

    UNITS ARE UNKNOWN and this probe does not try to settle them. Nothing in the
    image names +0x124 or says whether it is a multiplier, a scale or an added
    time, so two magnitudes go out on the correct ordering: if 2.0 does nothing
    and 0.25 does, the field is a multiplier being clamped at the top end rather
    than the ordering being wrong.
    """
    bar = [PROBE_BAR_SKILL + i for i in range(8)]
    skill = bar[4]
    return [
        Step(2.0, 0x00DA, [agent_id, bar, [0] * 8, 1], "fresh skillbar",
             "the bar, all eight ready."),
        Step(6.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "BASELINE: property 60 alone, no modifier",
             "the character's body. Time the cast animation, roughly -- this is "
             "the length everything below is compared against. IF NOTHING CASTS "
             "AT ALL, stop here: the `cast_anim` probe has not been run and this "
             "one cannot be read."),
        Step(10.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(2.0)],
             "modifier FIRST: property 61 = 2.0 (float channel, 0x00A2)",
             "nothing yet -- 61 on its own has no animation to modify. Note "
             "whether anything happens anyway, which would itself be news."),
        Step(2.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "... then property 60",
             "PREDICTION: a cast the SAME length as the baseline, because 60's "
             "own case body zeroed the modifier before the animation started. "
             "If this one is visibly different, the zeroing does not do what "
             "section 16.2 says and that claim needs withdrawing."),
        Step(10.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "modifier SECOND: property 60 first ...",
             "a cast starts. Keep watching -- the next packet lands during it."),
        Step(1.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(2.0)],
             "... then property 61 = 2.0, one second into the cast",
             "PREDICTION: THIS is the one that looks different -- the animation "
             "speeding up or slowing down mid-cast. If steps 4 and 6 are "
             "indistinguishable, either the ordering does not matter or +0x124 "
             "is not a cast-time modifier, and this probe cannot separate those "
             "two. Step 7 is the tiebreak on magnitude."),
        Step(10.0, 0x009F, [PROP_CAST_SKILL, agent_id, skill],
             "again, with a small modifier: property 60 ...",
             "a cast starts."),
        Step(1.0, 0x00A2, [PROP_CAST_TIME, agent_id, _f32(0.25)],
             "... then property 61 = 0.25",
             "the last step. If 2.0 did nothing and 0.25 does, the field is a "
             "multiplier and 2.0 was out of range rather than out of order. "
             "Nothing follows this -- take your time."),
    ]


def _pool_fraction_steps(agent_id, origin):
    """Is property 34 an ABSOLUTE amount or a FRACTION of the pool?

    THE TWO WITNESSES DISAGREE, and that is why this exists.

    SECTION 1b (OBSERVED 2026-08-06) says absolute: property 34 = -50.0 against a
    100-max agent took the bar from 50 to ~0, and 1b reads that as "it arrived as
    exactly 50". THE DISASSEMBLY (OBSERVED 2026-08-11, section 1d) says the client
    calls it a fraction: arm 2 at 0x0081828D passes our value through with NO fmul
    into 0x009215F0, whose line 84 asserts `fraction <= 1.0f` -- which is how the
    revive crash was found.

    1b'S STEP COULD NOT HAVE REFUTED THE FRACTION READING, and that is the flaw
    rather than a quibble. The bar was ALREADY at 50 when -50.0 landed. Absolute
    predicts 50 - 50 = 0. Fraction predicts 50 - (50 x 100) = 0. Both predict an
    empty bar, and 1b's own next row records that the follow-up did nothing
    because "the bar was already at the floor". A measurement whose two rival
    hypotheses make the same prediction is not evidence for either.

    1b's OTHER rows are unaffected and are the calibration this probe leans on:
    property 16 = -0.5 gave exactly 50 damage on a 100 bar, and property 55 = -1.0
    gave exactly 100. Both are the fraction reading landing on the nose, and both
    were read off a FULL bar, which is what makes them refutable.

    SO: the discriminator is -0.5 on property 34 against a FULL bar, which nobody
    has ever sent. The two readings differ by a factor of 100 there.

        step 2 (control, property 16 = -0.10)  ->  10 off, a known fraction
        step 3 (the question, property 34 = -0.50):
              FRACTION -> ~50 off, the bar drops to about half
              ABSOLUTE -> 0.5 off, the bar does not visibly move
        step 4 (the same again) separates fraction-of-MAX (bar empties) from
              fraction-of-CURRENT (bar halves again)

    PREDICTION, stated before the run: FRACTION. The client's own assert names the
    parameter, and a function that meant "absolute health" has no reason to bound
    its argument at 1.0. If the bar instead does not move, the disassembly is
    right about the arithmetic and wrong about the meaning, section 1d needs its
    headline changed, and `_fraction`'s range check is guarding the wrong thing.

    NOT SENT HERE: a positive value larger than 1.0. That is the CharPool.cpp:84
    crash, it is already OBSERVED, and re-running a known client-killer to watch it
    kill the client again buys nothing.
    """
    return [
        Step(2.0, 0x009F, [42, agent_id, 100],
             "max health -> 100 on the PLAYER (int property 42)",
             "the PLAYER's health orb, bottom centre -- it shows a NUMBER, which is a better readout than any bar. It should be 100. Every reading below "
             "is against this baseline, so if it is not full, stop -- the rest of "
             "the run measures nothing."),
        Step(5.0, 0x00A3, [16, agent_id, agent_id, _f32(-0.10)],
             "CONTROL: property 16 = -0.10, a known fraction",
             "the orb number and the floating number. 1b measured this channel at "
             "exactly fraction x max, so this should read 10 and leave the orb at "
             "90. This is the ruler for step 3 -- without it, 'about half' is an "
             "impression rather than a measurement."),
        Step(6.0, 0x00A3, [34, agent_id, agent_id, _f32(-0.50)],
             "THE QUESTION: property 34 = -0.50",
             "the bar, and ONLY the bar -- 1b established 34 is silent, so expect "
             "no floating number either way. Bar drops to about HALF => FRACTION. "
             "Bar stays at 90% => ABSOLUTE, and 0.5 of 100 was too small to see."),
        Step(6.0, 0x00A3, [34, agent_id, agent_id, _f32(-0.50)],
             "the same value again",
             "the bar. EMPTY means the fraction is of MAXIMUM (another 50 off a "
             "bar holding 40). About HALF OF WHAT WAS LEFT means it is of CURRENT. "
             "Still 90% means step 3 was absolute after all and this is 0.5 more."),
    ]


PROBES = {
    "cast_modifier_order": lambda a, o: Probe(
        question="Must the cast-time modifier (property 61) be sent AFTER the "
                 "cast-start property (60) rather than before it?",
        predicts="61-then-60 casts at the SAME speed as a bare 60, because 60's "
                 "own case body zeroes the modifier field before the animation "
                 "starts. 60-then-61 casts visibly differently. If the two "
                 "orderings are indistinguishable, either the ordering does not "
                 "matter or +0x124 is not the cast-time modifier -- this probe "
                 "cannot separate those, and says so.",
        steps=_cast_modifier_order_steps(a),
        note="Tests a claim studies/skillcast section 16.2 makes and nothing "
             "else can check: 4, 50 and 60 end with `fldz; fstp [esi+0x124]` at "
             "0x0081BCE1, zeroing the float that 5, 51 and 61 write. UNRUN. "
             "Depends on the `cast_anim` probe -- step 2 is the self-control and "
             "the run should stop there if a bare property 60 does not cast. "
             "Note 61 goes out on 0x00A2, the FLOAT channel: on 0x009F it would "
             "be discarded in silence and look like a negative result.",
    ),
    "pool_fraction": lambda a, o: Probe(
        question="Is agent property 34 an ABSOLUTE amount or a FRACTION of the "
                 "pool? Section 1b says absolute; the client's own assert calls it "
                 "a fraction.",
        predicts="FRACTION -- the bar drops to about half on step 3. The client "
                 "asserts `fraction <= 1.0f` on this exact argument "
                 "(CharPool.cpp:84, reached from arm 2 at 0x0081828D), and a "
                 "function meaning 'absolute health' has no reason to bound its "
                 "input at 1.0. The rival prediction is a bar that does not "
                 "visibly move, which would mean section 1d is right about the "
                 "arithmetic and wrong about the meaning. Step 2 is a known-good "
                 "fraction on property 16 and exists so that 'about half' is read "
                 "against a measured 10% rather than guessed.",
        steps=_pool_fraction_steps(a, o),
        note="RUN 2026-08-11, AND BOTH EARLIER READINGS ARE WRONG -- including the prediction above, which is left standing because it was. Observed on the player orb: 100 -> (property 16 = -0.10) -> 90 -> (property 34 = -0.50) -> 1 -> (again) -> 1. A DELTA of 0.5 x 100 from 90 predicts 40; the prediction above said 'about half'; the floor is what happened. "
             "PROPERTY 34 IS A SETTER: it sets the pool to fraction x maximum. -0.5 sets it to -50, which clamps to the floor of 1, and does so again on a second send because a setter is idempotent. That is also why revive's 1.0 refilled a bar sitting at zero all the way to full, and why the client asserts fraction <= 1.0f -- a setter cannot exceed the maximum. studies/agentprops/FINDINGS.md 1e. "
             "Section 1b's own step for this question could not have refuted the "
             "fraction reading: it sent -50.0 at a bar ALREADY down to 50, where "
             "absolute predicts 0 and fraction predicts 0. This sends -0.5 at a "
             "FULL bar, where the two readings differ by a factor of 100. Watch "
             "the HOSTILE's floating bar, not the player's orb. Nothing here can "
             "crash the client: every value is inside the asserted range, and the "
             "one known killer (a positive value above 1.0) is deliberately "
             "absent.",
    ),
    "effect_silent_extend": lambda a, o: Probe(
        question="Between apply+duration and a LATE 0x0044, is the effect still "
                 "drawn? Retail extends effects by sending nothing; does the "
                 "client self-expire, or wait to be told?",
        predicts="THE ICON IS STILL DRAWN AT +13 s AND +20 s on a 10 s "
                 "duration, with the timer bar drained to empty, and it goes "
                 "only when the late 0x0044 lands at +25 s. That is what "
                 "retail's own traffic requires: studies/isle 8.6 measured 15 "
                 "episodes closing +1.25 s to +55.0 s late with NO intervening "
                 "traffic, against 7 un-refreshed ones closing within 42 ms of "
                 "their own duration -- so the durations are honest, the close "
                 "is precise, and something held those effects open silently. "
                 "THE RIVAL OUTCOME IS THE MORE VALUABLE ONE: if the icon "
                 "vanishes at +10 s unprompted, the client owns the timer, "
                 "retail's silent extension never reaches the player's eye, "
                 "and our server may NOT extend silently for any effect the "
                 "player has to see -- which would make effects.py's "
                 "REMOVE-then-APPLY correct after all, for a reason nobody has "
                 "stated.",
        steps=_effect_silent_extend_steps(a),
        note="Cross-arc: the Isle arc measured the wire, this reads the screen, "
             "and neither half decides it alone. effects.EffectTable.apply's "
             "docstring currently ends 'how retail refreshes one is NOT FOUND' "
             "-- studies/isle 8.6 answers the wire half (retail sends nothing "
             "and delays the removal) and this probe answers whether that is "
             "renderable. FIXED-POSITION UI ONLY: the whole readout is the "
             "effects area above the skill bar, so no aiming and no world "
             "click is involved. Run with --shots so the boundary at +10 s is "
             "caught in frames rather than from memory; the two sends=False "
             "steps are observation points and deliberately transmit nothing.",
    ),
    "deep_wound": lambda a, o: Probe(
        question="What does each message of retail's Deep Wound batch do on "
                 "screen -- the episode, the status word 0x22, and the "
                 "maximum -- and does the client's signed delta hold when the "
                 "maximum falls onto a damaged pool?",
        predicts="ARM A (episode alone): icon, no grey, 100/100. ARM B (full "
                 "batch, full pool): grey 20% at the status word, HUD 80/80 at "
                 "the maximum, 100/100 again at the close. ARM C (full batch on "
                 "25/100): HUD 5/80, then 25/100 at the close. Any grey in ARM "
                 "A refutes the status-bit reading; 20 or 25 in ARM C refutes "
                 "the signed delta for this message pair.",
        steps=_deep_wound_steps(a),
        note="SKILLS-DW (studies/skills/FINDINGS.md 41). Run --explorable, "
             "like health_max and health_shrink: damage on an outpost map is "
             "swallowed. The readout is the HUD orb's printed NUMBER, bottom "
             "centre -- bar fills are only good to a few points, the number "
             "is exact (RESKIN 18.13) -- plus whether the right 20% of the "
             "health bar is greyed. Every message here is one the server now "
             "sends on its own when --enemy-skills 337 lands an axe; this "
             "probe separates the three so the run that follows has one "
             "question per message.",
    ),
    "heal_number": lambda a, o: Probe(
        question="Does a property-55 gain draw its number on a FULL pool, the "
                 "way it does on a damaged one -- and does the client take "
                 "the overheal without asserting?",
        predicts="ARM A (damaged pool): a pale blue '+46' floats up from the "
                 "player and the orb reads 100 -- the positive control, "
                 "already seen 3 of 3 in 20260820T190917 once the frames "
                 "were read for BLUE instead of green. ARM B (full pool): "
                 "WIKI says the same '+46' draws with the orb unmoved; the "
                 "retired rule predicted nothing to send at all. No assert "
                 "either arm -- retail sends 55 onto full pools 46 times in "
                 "the corpus and its client survives. A '+46' in A and "
                 "nothing in B refutes the wiki for this client; an assert "
                 "in B (CharPool.cpp:84's `fraction <= 1.0f`) means the "
                 "clamp is ours to do and OVERHEAL_NUMBER must cap.",
        steps=_heal_number_steps(a),
        note="SKILLS-HN (studies/skills/FINDINGS.md 42). Run --explorable. "
             "The number floats above the player's own head at screen "
             "centre and fades in ~1.5 s, so per-second frames catch it "
             "about once each; read the frame, do not trust a colour "
             "threshold -- the 2026-08-20 null was a scan for saturated "
             "GREEN, and the glyphs are (151,233,250)-ish sky blue on a "
             "white core. Fixed-position readout: agent-drivable.",
    ),
    "condition_render": lambda a, o: Probe(
        question="Does 0x0042 carrying a CONDITION skill id (type_code 8) "
                 "render as a condition -- brown down-arrow, gold-bordered "
                 "icon -- and which condition does each id name?",
        predicts="Renders as a condition, named by its tooltip. The rival "
                 "outcome is a plain buff icon with no arrow, which would "
                 "mean the client does not classify conditions from the "
                 "skill id and the Students' applications ride something "
                 "else -- the refutation branch rung 8's live session would "
                 "otherwise spend its first two minutes on. Either answer "
                 "changes rung 8; only silence changes nothing, and a bare "
                 "icon is not silence.",
        steps=_condition_render_steps(a),
        note="Isle rung 4 (studies/isle/PLAN.md). 0x0042 has ZERO ArenaNet "
             "witnesses, so everything here is our layout from the client's "
             "own handler -- a render is also the first proof of that layout "
             "against a running client. SAY THE TOOLTIP NAMES OUT LOUD: the "
             "id -> condition mapping order is UNVERIFIED and the tooltip is "
             "the only instrument that settles it. "
             "RUN 2026-08-16, operator watching: 478 rendered BLEEDING and "
             "480 BURNING, both classified as CONDITIONS on the operator's "
             "character -- two points landing exactly in s_charCondition's "
             "order, so the mapping (478 Bleeding, 479 Blind, 480 Burning, "
             "481 Crippled, 482 Deep Wound, 483 Disease, 484 Poison, 485 "
             "Dazed, 486 Weakness) moves to CORROBORATED. 'They did no "
             "damage': the client renders the condition and does NOT "
             "self-apply degeneration -- the server must send it (the 0x00A2 "
             "prop-44 rate, FINDINGS B4). Step 5 (2077) went unobserved; "
             "Cracked Armor's out-of-block id is still open.",
    ),
    "lone_p17": lambda a, o: Probe(
        question="What does a LONE property 17 draw, and does the client-side "
                 "orb move?",
        predicts="A damage number draws and the orb does NOT move -- the "
                 "handler read (studies/agentprops 1) raises the notification "
                 "and skips the health record. ArenaNet's ledger half is "
                 "already settled the other way (a lone p17 kills -- "
                 "studies/isle/FINDINGS.md B6), so if the orb DOES move, "
                 "client and server agree and the agentprops reading is "
                 "wrong; if it does not, our server must debit health "
                 "server-side when it ever sends 17, or the two drift.",
        steps=_lone_p17_steps(a, o),
        note="Isle rung 4. Step 1 is the known-good p16 control at the same "
             "magnitude -- read 17 and 18 AGAINST it, not against memory of "
             "what a crit should look like. Step 4 restores the orb via the "
             "property-34 setter. "
             "RUN 2026-08-16, measured off the harness screenshots (bar "
             "values legible): 100 -> 90 on the p16 control, 90 -> 80 on the "
             "LONE p17 -- THE ORB MOVED, refuting this probe's own stated "
             "prediction -- and 80 -> 80 on p18. So the three kinds separate "
             "on screen: 16 debits, 17 debits, 18 notifies only. The "
             "agentprops 'notification without a health record' reading was "
             "right about the MECHANISM and wrong about the ID -- it belongs "
             "to 18. Client and server agree on 17 (B6: a lone p17 kills "
             "server-side; here it debits client-side): 17 is a full damage "
             "kind, and '17 replaces 16' is settled on both halves.",
    ),
    "buff_type_field": lambda a, o: Probe(
        question="Is opcode 66's third field Headquarter's `effect_type` or "
                 "GWCA's `attribute_level`?",
        predicts="If effect_type, 0 and 14 render as visibly different KINDS "
                 "of effect and an out-of-enum 12 misbehaves. If "
                 "attribute_level, all three render identically and only the "
                 "tooltip numbers move. The binary cannot separate these: it "
                 "stores the field at buff record +0x04 and never reads it in "
                 "ChCliBuff.",
        steps=_buff_type_steps(a),
        note="ANSWERED 2026-08-19 (captures 20260819T232426 and 20260819T233451, "
             "skillcast FINDINGS 14.7): prediction B, exactly -- the icons are "
             "pixel-identical across 0/14/12 and the tooltip's numbers are "
             "round(lo+(hi-lo)*rank/15) of the field (10/57/50 max-Health on "
             "skill 316's 10..60 window). The field is the ATTRIBUTE RANK the "
             "effect renders at; GWCA's attribute_level confirmed, Headquarter's "
             "effect_type refuted. Kept runnable as the effect-tooltip "
             "calibration; read the tooltip with --walk hover:0.0442,0.0543,38. "
             "Keep buffId small -- GmEffect:3030 bounds it against a UI "
             "frame-code range.",
    ),
    "minion_count": lambda a, o: Probe(
        question="Is 0x0093's value dword the number of minions the agent "
                 "controls?",
        predicts="Sending 7 makes the effects monitor read 'You are "
                 "currently controlling 7 minion[s]'; sending 0 makes the "
                 "indicator vanish. Any other number refutes the reading.",
        steps=_minion_count_steps(a),
        note="STATIC-ONLY until this runs: studies/pvpui 33 names the field "
             "from the client's own template (string 50499, value as "
             "%num1%), with three GmEffect readers agreeing, but the opcode "
             "has ZERO occurrences in 114,985 live s2c messages and this "
             "repo has never sent one. Confirming it raises the "
             "AGENT_MINION_COUNT name from medium.",
    ),
    "buff_side": lambda a, o: Probe(
        question="Do opcodes 63 and 65 file the same buff under two different "
                 "agents, in two different lists?",
        predicts="65 alone gives one effect icon with no countdown. Adding 63 "
                 "with the same buffId gives a SECOND, separate indicator "
                 "(the upkeep row). Removing one leaves the other.",
        steps=_buff_side_steps(a),
        note="ANSWERED 2026-08-19 (capture 20260819T235007, skillcast FINDINGS "
             "14.8): every clause held. 65 alone draws the effect icon with NO "
             "countdown bar (duration 0.0); 63 with the same buffId adds the "
             "skill's icon to the maintained-enchantment UPKEEP MONITOR above "
             "the energy bar (~x1120,y880 at the standard window); 64 clears "
             "the upkeep icon and the effect icon STAYS; 68 clears the effect "
             "icon. Two records, independent lifecycles, joined by buffId -- "
             "and the upkeep icon needs no 0x0093, so the +0x5BC table does "
             "not gate it. SOURCED: BuffState keeps a source list at +0x04 and "
             "a target list at +0x14, and the client's own log strings are "
             "BuffSourceAdd/BuffSourceRemove for 63/64 and "
             "BuffTargetAdd/ExtendTimed/Remove for 65/66/67/68.",
    ),
    "use_skill_capture": lambda a, o: Probe(
        question="What does the client SEND when a skill key is pressed, and "
                 "does the message number depend on the skill's TYPE?",
        predicts="Two different opcodes from the same eight keys. Keys 1-4 "
                 "(To the Limit!, Battle Rage, Defy Pain, Rush -- types 15, 3, "
                 "16, 3) send GAME_CMSG 70 / 0x0046. Keys 5-8 (Hamstring, Wild "
                 "Blow, Power Attack, Desperation Blow -- all type 14, attack "
                 "skills) send GAME_CMSG 39 / 0x0027 instead. Both are 15 "
                 "bytes. In 70 the fields are {skill id, skill copy, target "
                 "agent id, u8}; in 39 the same four values go out in the same "
                 "order against a differently typed table. Skill copy will be "
                 "0 unless the skillbar was sent with a non-zero second array.",
        steps=[],
        note="No packets from us -- press the keys and read the capture. It "
             "settles USE_SKILL's field NAMES (unnamed in every source; "
             "Headquarter guesses field 2 is `flags`, apoguita guesses `type`, "
             "and the client's own builder says it is the skill copy) and the "
             "existence of a second, unnamed cast message at the same time. "
             "The type split is SOURCED from ChCliApiUseSkill at VA 0x00816660 "
             "branching on skill record +0x0C; the type-14 = attack-skill "
             "reading is from this build's own skill table. If BOTH halves of "
             "the bar send 70, that branch is not on skill type and the "
             "reading is wrong.",
    ),
    "skill_copy": lambda a, o: Probe(
        question="Is the lifecycle messages' third dword the bar slot's "
                 "`skillCopy`, delivered by SKILLBAR_UPDATE's second array?",
        predicts="With copies set to 7, a recharge addressed to copy 0 does "
                 "NOTHING and the same recharge addressed to copy 7 works. If "
                 "both work, the client is not matching on field 3; if neither "
                 "works, the second array of 218 is not what fills the slot.",
        steps=_skill_copy_steps(a),
        note="The decisive experiment for the field GWCA calls skill_instance "
             "and every other lineage records as NOT FOUND. Cheapest and most "
             "informative probe in this group; run it first. Note the failure "
             "mode is SILENCE, which is why the run alternates right and wrong "
             "copies rather than testing one.",
    ),
    "skill_disable": lambda a, o: Probe(
        question="Is unnamed opcode 231 the 'skill disabled' message?",
        predicts="231 freezes an in-progress cooldown permanently dark, and a "
                 "subsequent 230 clears it instantly. If 231 instead behaves "
                 "like 230, the -1 we read is being treated as ready.",
        steps=_skill_disable_steps(a),
        note="231 writes recharge = 0xFFFFFFFF where 229 explicitly SKIPS both "
             "0 and -1 when computing a timestamp; those are two reserved "
             "values and this asks what the second one looks like.",
    ),
    "skill_partial": lambda a, o: Probe(
        question="Does unnamed opcode 232 carry a fractional recharge, and is "
                 "its fourth field the total the UI draws the sweep against?",
        predicts="Field 5 is seconds as an IEEE float: 10.0f counts ten "
                 "seconds and 2.5f counts two and a half. Field 4 = 40 with "
                 "field 5 = 10.0f starts the sweep about a quarter dark.",
        steps=_skill_partial_steps(a),
        note="The remaining/total reading is INFERRED, not sourced -- the "
             "binary shows only that field 5 sets the clock and field 4 is "
             "reported to the UI beside it. The sweep angle is the only thing "
             "that can separate the two readings.",
    ),
    "cast_anim": lambda a, o: Probe(
        question="What triggers the cast animation -- opcode 228, or agent "
                 "property 60?",
        predicts="228 does nothing visible at all when addressed to the local "
                 "player. Property 60 with a skill id plays the animation. If "
                 "228 animates anything, the read of its handler is wrong.",
        steps=_cast_anim_steps(a),
        note="Open question in studies/skills section 8, and the static answer "
             "is strong enough to be worth trying to break. Watch Gw.log as "
             "well as the screen: step 4 should produce the client's own "
             "'Pending skill %u copy %d not found'.",
    ),
    "cast_228_only": lambda a, o: Probe(
        question="Does opcode 228 addressed to the LOCAL player animate "
                 "anything -- on its own, with nothing else sent?",
        predicts="Nothing, for the whole run. 228's handler compares the "
                 "named agent against the local player and returns before "
                 "it reaches AgentView. Corroborated from the wire: all 7 "
                 "0x00E4 in the live corpus name the receiving connection's "
                 "OWN player (studies/combat 6, step 0a), so the real "
                 "service broadcasts it uniformly and relies on this "
                 "discard. A sparkle here REFUTES that reading.",
        steps=_cast_one_steps(a, "228"),
        note="ANSWERED 2026-08-15 and the prediction HELD: nothing, for the "
             "whole run. Capture authsrv-20260815T184213-c1.jsonl -- bar at "
             "t=2.87, 0x00E4 at t=10.88, nothing else sent, operator saw no "
             "change. Its pair cast_prop60_only, identical but for the one "
             "message, DID render the cast. So 228 is bookkeeping, and the "
             "handler read, the live wire (7 of 7 name the receiving "
             "player) and the screen all agree. Keep the probe: it is the "
             "control half, and re-running it is how a future change to "
             "0x00E4's handling gets caught.",
    ),
    "cast_prop60_only": lambda a, o: Probe(
        question="Does agent property 60 alone play the cast animation?",
        predicts="THIS is the one that animates -- property 60 reaches "
                 "AvApi and queues the animation event, where 228 never "
                 "leaves its bookkeeping array. If this run shows nothing "
                 "and the 228 run does, the two are swapped and "
                 "studies/skills section 8 is wrong.",
        steps=_cast_one_steps(a, "prop60"),
        note="ANSWERED 2026-08-15 and the prediction HELD: the operator saw "
             "the cast sparkle on the weapon. Capture "
             "authsrv-20260815T184317-c1.jsonl -- bar at t=2.85, property "
             "60 at t=10.85, nothing else sent. Its pair cast_228_only, "
             "identical but for the one message and firing at the same "
             "t=10.88, rendered NOTHING. Same bar, same map, same hold: the "
             "animation follows property 60. This closes studies/skills "
             "section 8's headline question and refutes its own guess that "
             "the client predicts the animation itself.",
    ),
    "cast_spell_only": lambda a, o: Probe(
        question="Does one property-60 send reproduce a FULL cast -- the "
                 "body animation -- or only the skill's visible effect?",
        predicts="A casting stance on the model. 105 Deathly Swarm is a "
                 "2.0 s spell carrying THREE animation components "
                 "([204, -, 201, -, -, 199] at +0x74..+0x88) where "
                 "Hamstring, the skill the earlier pair used, carries one. "
                 "If only an effect appears, property 60 drives EFFECTS and "
                 "the body animation has another source -- which is the "
                 "more useful answer of the two.",
        steps=_cast_spell_steps(a),
        note="ANSWERED 2026-08-15 and the prediction HELD: the operator "
             "reports the MODEL animated, not just a weapon effect. "
             "Capture authsrv-20260815T190337-c1.jsonl. So property 60 "
             "drives the cast including the body, and what renders is "
             "PER-SKILL -- one component for an attack skill, a full "
             "casting animation for a 2 s spell carrying three. "
             "Follow-up to cast_prop60_only, which the owner correctly "
             "objected was tested with an ATTACK skill (320 Hamstring, "
             "activation 0.0 s, one animation id) and so could never have "
             "shown a body animation. That probe settled the DRIVER; this "
             "one asks about the CONTENT. Watch the model, not the weapon.",
    ),
    "unlock_211": lambda a, o: Probe(
        question="What is opcode 211, the third unlock-list-shaped message?",
        predicts="Nothing observable. It writes a bitmap nothing in the image "
                 "reads and broadcasts no UI event, unlike 219.",
        steps=_unlock_211_steps(a),
        note="A NULL result is the expected result and is worth having: it "
             "would let the server stop worrying about a message it has never "
             "sent. Any visible effect refutes the read and is more "
             "interesting still.",
    ),
}
