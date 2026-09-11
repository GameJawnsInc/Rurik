"""Health pool, party row, player flags, armour slots, the composite-withheld arm.

The unit-setup arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the agent-removal and id-reuse arm, the health-maximum arm and the
shrink onto a damaged pool, the party row's bar, the 0x003C player-flag word,
the two armour arms -- the 0x006E/0x006F slot question and the exploratory
argument-order arm it grew out of -- the composite-withheld arm with its four
fresh definition and agent slots, and the eight registry entries that fire them.

It is leaf shaped by the same rule `probebase.py` is -- standard library plus
`agents` and `probebase` -- and it MUST NOT import `probes`: `probes.py` runs as
`__main__` under `python toolkit/authsrv/probes.py`, so a leaf importing it back
would load a SECOND copy of that module, with its own `PROBES` dict and its own
flags.

WHY THE AGENT-REMOVAL ARM IS HERE, said out loud because the one-line subject
above does not name it and `burrow` -- which asks a neighbouring question about
the same opcode -- stayed in `probes.py`. Two of the section brief's own
MEASURED figures resolve only if this arm moves with the unit-setup run: it
scoped this module at ELEVEN `agents` names, and the set without the removal arm
is nine (the two it adds are `ALLEGIANCE_HOSTILE` and `HATCHER`); and it scoped
the lane at 3,279 gross lines, where the ranges actually cut total 3,270 WITH
this arm and its registry entry and 3,168 without them -- nine lines of
blank-line padding from the first figure and a hundred and eleven from the
second. It is also the right file on the merits: what this
arm measures is the ORDINARY SPAWN BURST -- 0x0056, 0x0057, 0x0020, once at a
reused id and once at a fresh one -- which is how a unit gets set up, where
`burrow` is about an effect bit.

WHERE THE REFERENTS WENT. Every "above" and "below" in the comments that travel
with this code points INSIDE one step list or one registry note -- step
orderings and readings within one arm -- so none of them is reworded. The two
sentences that say "a bug in this file" are the agent-removal arm's own record
of its first, broken step 2: the code they are about is in THIS file now, so
they are as true here as they were there. `_armor_slots_steps`' docstring names
"unitsetup Q6" and `_health_shrink_steps`' names "unitsetup Q5" -- those are
`studies/unitsetup/FINDINGS.md` sections, not file pointers, and they are what
this module is named after.

`PROBES` here holds only the eight unit-setup entries. `probes.py` opens its own
dict, merges this one in with a duplicate-key raise, and keeps `get`, `names`,
`describe` and `check_encodable` -- so `probes.get("health_max", ...)` answers
exactly as it did, and `names()` is still `sorted(PROBES)` and still returns the
same 97 names in the same order. Every name this module binds except `PROBES` is
also re-exported by `probes.py`, at the three sites they were cut from, so
`vars(probes)` still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, ALLEGIANCE_HOSTILE, CHAR_CLASS_MONSTER_BASE, HATCHER,
    agent_set_tabard_visible, create_agent, item_template, named_item,
    npc_model, npc_properties, npc_template)
from probebase import (                                     # noqa: E402
    ENEMY_AGENT_ID, ENEMY_DEFINITION, FRESH_AGENT_ID, PROBE_PLAYER_NUMBER,
    PROBE_SPAWN_NEAR, WARRIOR_ARMOR, Probe, Step,
    _ARMOR_BOOTS_ITEM, _ARMOR_LEGS_ITEM, _f32)


def _agent_removal_steps(agent_id, origin):
    """WORLD_REMOVE_AGENT (0x0021), and then the id reuse it is supposed to unlock.

    The hostile is spawned by the normal map load, so this probe removes THAT
    agent rather than making one: the interesting question is what the client does
    with an object it is already drawing, tracking and possibly targeting.

    THE FIRST VERSION OF STEP 2 WAS BROKEN AND ITS NEGATIVE MEANT NOTHING.
    RUN 2026-08-10: step 1 vanished cleanly and step 2 drew nothing, which read
    like "id reuse is impossible". It was not. That step sent a BARE 0x0020, and
    three things were wrong with it: no NPC_UPDATE_PROPERTIES and no
    NPC_UPDATE_MODEL first (npc_properties' own docstring says the definition
    "must precede any agent using it" -- the definition index is a raw array
    index); `npc_model(...)` was passed where a model_id belongs, and it returns a
    MESSAGE PAYLOAD, not an id; and the plane was hardcoded 0 instead of the
    player's. A malformed create drawing nothing is not evidence about the id.
    The re-created agent was also missing the hostile allegiance the real spawn
    sets, so even a success would have measured a different body.

    So step 2 now sends the SAME three-message burst spawn_enemy does, and a
    CONTROL follows it. That control is the whole design: the same burst at a
    FRESH id nothing has ever used.

        step 2 fails, step 3 works  -> the id really is poisoned by removal
        both fail                   -> our burst is wrong, and the id is innocent
        both work                   -> reuse is fine and the first run measured a
                                       bug in this file, nothing more
    """
    ox, oy, plane = origin if origin else (0.0, 0.0, 0)
    reuse = (ox + PROBE_SPAWN_NEAR, oy)
    fresh = (ox + 2 * PROBE_SPAWN_NEAR, oy)
    model_id = CHAR_CLASS_MONSTER_BASE | ENEMY_DEFINITION
    return [
        Step(3.0, 0x0021, [ENEMY_AGENT_ID], "REMOVE the hostile",
             "the hostile. Does it vanish cleanly -- no corpse, no nameplate, no "
             "health bar? If you had it TARGETED, does the target frame clear or "
             "does the UI keep a dead reference?"),
        # --- step 2: the FULL burst, at the SAME id -----------------------------
        Step(6.0, 0x0056, npc_properties(ENEMY_DEFINITION, HATCHER),
             "redefine the NPC type",
             "nothing yet -- this defines the type the next create refers to."),
        Step(0.5, 0x0057, npc_model(ENEMY_DEFINITION, HATCHER),
             "and its model", "still nothing yet."),
        Step(0.5, 0x0020,
             create_agent(ENEMY_AGENT_ID, model_id, AGENT_KIND_NPC,
                          reuse[0], reuse[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"RE-CREATE at the SAME id ({ENEMY_AGENT_ID})",
             f"{PROBE_SPAWN_NEAR:.0f} units east. Does a fresh hostile appear? "
             "This is the id reuse "
             "removal is supposed to make safe -- 301 of 301 live re-creations "
             "were preceded by a removal of that id."),
        # --- step 3: the CONTROL, same burst at an id never used ---------------
        Step(6.0, 0x0020,
             create_agent(FRESH_AGENT_ID, model_id, AGENT_KIND_NPC,
                          fresh[0], fresh[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"CONTROL: the SAME create at a FRESH id ({FRESH_AGENT_ID})",
             f"{2 * PROBE_SPAWN_NEAR:.0f} units east. If THIS one appears and the "
             "one before it did not, "
             "the removed id is genuinely poisoned. If neither appears, the burst "
             "is wrong and the id was never the problem."),
    ]


def _health_max_steps(agent_id):
    """Does int property 42 refill only when the MAXIMUM actually changes?

    RESKIN.md 18.12: with the bar at a quarter, int property 42 = 100 did nothing
    -- row stayed 24.0%, HUD kept reading 25, nine frames. The "assigns
    health_max = value AND health = 1.f" reading is ldufr/Headquarter's, which is
    UPSTREAM rather than a retail observation. Our player's maximum is ALREADY
    100, so that run could not tell a same-value no-op from a wrong reading.

    200 separates them, and the HUD's own NUMBER is the discriminator rather than
    the bar, because three outcomes are distinguishable and only one of them is
    "nothing happened":

      HUD 200, bar full  -> the refill is real and fires on a CHANGE of maximum.
      HUD  50, bar 25%   -> the maximum moved and the FRACTION was preserved:
                            0.25 * 200 = 50. Upstream's health_max half is right
                            and its `health = 1.f` half is wrong.
      HUD  25, bar 25%   -> property 42 does not carry the maximum either, and
                            2026-08-06's "raised a health bar reading 100" was
                            something else establishing it.

    Step 3 puts it back to 100 -- if step 2 moved anything, a return is the
    cheapest check that we are driving a live value rather than watching a
    one-way latch.
    """
    a = agent_id
    return [
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.75)],
             "damage -0.75 -- take the bar to a quarter",
             "the party row and the HUD must both read a quarter (bar ~25%, "
             "HUD number 25). This is setup, and it is the step already "
             "measured twice, so it doubles as the run's own control."),
        Step(7.0, 0x009F, [42, a, 200],
             "int property 42 = 200 -- a DIFFERENT maximum",
             "READ THE HUD NUMBER, not just the bar. 200 means refill-on-change; "
             "50 means the maximum moved and the fraction survived; 25 means "
             "property 42 does not carry the maximum at all."),
        Step(7.0, 0x009F, [42, a, 100],
             "int property 42 = 100 -- put it back",
             "whatever step 2 moved should move back. If step 2 changed nothing "
             "this changes nothing either, and the run's answer is the third "
             "outcome above."),
    ]


def _party_health_steps(agent_id):
    """Is the party row's red bar THIS player's health, or a constant?

    RESKIN.md 18.10: the row `W0 Test Warrior` draws on a full-width red bar, and
    the red is not a fault -- WIKI (GWW, "User interface" section Party window,
    rev. 2026-07-15): "The red bars represent the allies' or party members'
    health. A disconnected player will have its health bar greyed out." So the row
    is correct, and the bar is a live per-member readout this server has never
    deliberately driven.

    Property 16 is DAMAGE and is a FRACTION of the agent's maximum health -- it
    multiplies by `[esi+0x24]`, which is why -0.5 takes a full bar to half rather
    than removing half a point. Two cuts rather than one, because a single step
    cannot tell a bar that TRACKS health from one that merely reacts once: after
    -0.5 then -0.25 the bar must be at roughly a quarter, not back at a half and
    not empty.

    The recovery step matters as much as the cuts. Damage floors at 1 (it cannot
    kill), so a bar that empties and STAYS empty would mean the row stopped
    tracking rather than that the character died -- and healing back is the only
    way to tell those apart from outside.
    """
    a = agent_id
    return [
        Step(4.0, 0x00A3, [16, a, a, _f32(-0.5)],
             "damage -0.5 on the PLAYER (half of maximum)",
             "the PARTY ROW's red bar, not the HUD bar at the bottom. It must "
             "shorten to about half its width with the name still in place."),
        Step(7.0, 0x00A3, [16, a, a, _f32(-0.25)],
             "damage -0.25 more (quarter of maximum)",
             "about a quarter of the original width. If it went back to half, "
             "the bar is reacting to the message rather than tracking health."),
        # RECOVERY, and the first version of this step KILLED THE CLIENT.
        # `0x00A3 [16, a, a, +0.75]` -- damage as a signed health delta -- is
        # refused fatally: `Assertion: damage.amount <= 0`, AvChar.cpp:5893,
        # OBSERVED 2026-08-13 (harness 20260813T212610, crash dialog captured).
        # Property 16 is DAMAGE, not health, and the client asserts the sign.
        # Int property 42 is the documented refill instead: it assigns
        # health_max = value AND health = 1.0, which this repo has observed
        # since 2026-08-06.
        Step(7.0, 0x009F, [42, a, 100],
             "RECOVERY: int property 42 = 100 (sets max AND refills)",
             "the bar must grow back to full width. A bar that never returns was "
             "not tracking health -- damage floors at 1 and cannot have killed "
             "the character. RUN 2026-08-13 and it DOES NOT REFILL: the row "
             "stayed at 24.0% and the HUD kept reading 25 for nine frames. The "
             "'assigns health_max AND health = 1.f' reading is ldufr/Headquarter's "
             "-- UPSTREAM, not a retail observation -- and this is the run that "
             "shows it does not reproduce when the value EQUALS the existing "
             "maximum. Try 200 to separate a same-value no-op from a wrong "
             "reading; see RESKIN.md 18.12."),
    ]


def _player_flags_steps(agent_id):
    """GAME_SMSG 0x003C -- the player-record flag word this server has never sent.

    MEASURED 2026-08-13 over ArenaNet's own captures, read whole with
    `tape.decode_all` (the per-event idiom loses and invents messages): **12 of 12
    live game connections carry it**, at t=0.23-0.73s, i.e. inside the instance
    load. Our server has sent it ZERO times in 190 played captures.

    The SHAPE is the part worth writing down, because the party dive reported it as
    "(player_number, set=4, clear=7)" and the corpus says otherwise. Censused over
    all 423 sends in those 12 connections:

        mask (the second dword) is 7 in 423 of 423
        value (the first) is 4 x287, 5 x60, 0 x48, 7 x12, 6 x12, 1 x4

    Every value lies inside the mask and the mask never varies. That is a
    (value, mask) pair, not (set, clear): three bits, cleared then written, which
    matches the handler doing an `and` at 0x0080EC26 and an `or` at 0x0080EC48 into
    `[playerRec+0x34]` -- the same ctx+0x80C stride-0x50 array 0x00B0/0x00B1 write.
    UPSTREAM for the two addresses (the party dive); OBSERVED for the wire values.

    A solo player is (player, 4, 7) in every single-connection capture, so bit 2 is
    the one a lone character carries. This sweeps all three bits rather than sending
    only retail's value, because a null on 4 alone would not say whether the message
    does nothing or whether 4 is simply what we already look like.
    """
    p = PROBE_PLAYER_NUMBER
    return [
        Step(2.0, 0x003C, [p, 4, 7], "flags -> 4 (retail's own solo value)",
             "anything at all: the party row, the nameplate, the chat, the "
             "compass. Retail sends exactly this for a lone player."),
        Step(6.0, 0x003C, [p, 0, 7], "flags -> 0 (all three bits CLEAR)",
             "if step 1 changed nothing, does REMOVING the bits change "
             "something? We may already look like 4 by default."),
        Step(6.0, 0x003C, [p, 7, 7], "flags -> 7 (all three bits SET)",
             "bits 0 and 1, which no solo capture carries. If nothing has "
             "moved by here, 0x003C is invisible in a one-player instance."),
    ]


def _health_shrink_steps(agent_id):
    """The delta model under a DECREASING maximum -- unitsetup Q5.

    `health += (new_max - old_max)` is MEASURED for an increase (health_max,
    2026-08-13: 25/100 -> max 200 read 125). Nobody has measured a DECREASE
    except studies/enemy/PLAN.md 6g's max -> 0, which rendered a FULL bar and
    then asserted `range > 0` -- recorded as a mystery under the old refill
    reading and still flagged UNVERIFIED-in-mechanism under the delta. It is
    only a mystery if the pool was damaged: a shrink onto a FULL pool lands
    exactly at the new maximum under the delta model (100 + (50-100) = 50 of
    50), so 6g's full bar is the delta model's own prediction. Step 1 shows
    that legally (50 asserts nothing). The discriminator is step 4, a shrink
    onto a DAMAGED pool, where the three readings finally part company.
    """
    a = agent_id
    return [
        Step(4.0, 0x009F, [42, a, 50],
             "int property 42 = 50 at FULL health -- 6g's shape, legal value",
             "HUD number. Delta predicts 50 with the bar FULL (100-50 = -50 "
             "grant lands exactly on the new max) -- 6g's 'refilled to full' "
             "reproduced with nothing mysterious about it. Refill predicts "
             "the same 50/50 here, which is why this step alone settles "
             "nothing and step 4 exists."),
        Step(5.0, 0x009F, [42, a, 100],
             "int property 42 = 100 -- restore",
             "HUD 100, bar full. Reversibility before the discriminator."),
        Step(5.0, 0x00A3, [16, a, a, _f32(-0.75)],
             "damage -0.75 -- the bar to a quarter",
             "HUD 25. The step measured twice before; the run's own control."),
        Step(5.0, 0x009F, [42, a, 50],
             "int property 42 = 50 onto the DAMAGED pool -- the discriminator",
             "THE HUD NUMBER. Delta: 25 + (50-100) = -25, which cannot stand; "
             "the damage path floors at 1, and if the grant shares that clamp "
             "the orb reads 1 on a bar of 50. Refill: 50. Fraction-survives: "
             "12 or 13. Three mechanisms, three different numbers."),
        Step(5.0, 0x009F, [42, a, 100],
             "int property 42 = 100 -- what did the clamp destroy?",
             "HUD number again. If step 4 clamped to 1, delta predicts 51 "
             "(1 + 50) -- the shrink LOST the 24 health the clamp ate, and a "
             "restore does not give it back. 25 here means the pool remembers "
             "through the clamp; 100 means refill was hiding all along."),
    ]


def _armor_slots_steps(agent_id):
    """Which of 0x006E's nine positions is which body slot -- unitsetup Q6.

    CONTESTED at studies/character/FINDINGS.md "Where every source is silent":
    positions 3-6 are Legs/Head/Boots/Gloves in bag order (2 lineages) or
    Boots/Legs/Gloves/Head permuted (1 lineage), NOT FOUND for build 38797
    after fifteen mirrors. A sibling track also doubted the 0x006F mapping
    itself ("if 111 does nothing, the mapping is wrong"). The probe crosses
    two visually loud pieces -- leggings and boots, gray on a bare-legged
    body -- through the one position (3) where the readings disagree
    hardest, with 0x006E-array and 0x006F-per-slot arms both represented.
    The character is otherwise naked from the waist down but for shorts:
    gray leggings versus bare calves versus booted feet are all readable
    from the default camera with no aiming.
    """
    a = agent_id
    return [
        Step(4.0, 0x0161, named_item(_ARMOR_LEGS_ITEM,
                                     item_template("warrior_legs")),
             "0x0161: declare the LEGGINGS (item 2)",
             "nothing -- a declaration renders nothing, measured 621/621."),
        Step(1.0, 0x0161, named_item(_ARMOR_BOOTS_ITEM,
                                     item_template("warrior_boots")),
             "0x0161: declare the BOOTS (item 3)",
             "nothing yet either."),
        Step(3.0, 0x006F, [a, 3, _ARMOR_LEGS_ITEM],
             "0x006F: LEGGINGS into position 3 -- the contested cell",
             "the body. Gray LEGGINGS appearing = position 3 wears what bag "
             "order says (Legs@3) or the render is item-driven; something on "
             "the FEET = the permuted reading (Boots@3) with slot-driven "
             "render; NOTHING = 0x006F is not per-slot wear and the sibling "
             "track's doubt about the 109/110/111 mapping wins."),
        Step(6.0, 0x006E, [a, 0, 0, 0, 0, 0, 0, 0, 0, 0],
             "0x006E: nine zeros -- the reset (gw-preservation's own idiom)",
             "everything visual vanishes, hammer included. A clean slate "
             "so the next arm cannot inherit this one's pixels."),
        Step(1.0, 0x0048, agent_set_tabard_visible(a, 0),
             "0x0048 after 0x006E, retail's own 366/366 pairing",
             "nothing."),
        Step(4.0, 0x006F, [a, 5, _ARMOR_LEGS_ITEM],
             "0x006F: the SAME leggings into position 5",
             "if the leggings LAND SOMEWHERE ELSE (feet under bag order's "
             "Boots@5, hands under permuted Gloves@5), the slot drives the "
             "render and position semantics are directly readable. If they "
             "draw as leggings again, the ITEM drives its own placement and "
             "the slot-order contest is invisible to pixels."),
        Step(6.0, 0x006E, [a, 0, 0, 0, 0, 0, 0, 0, 0, 0],
             "0x006E: reset again", "clean slate again."),
        Step(1.0, 0x0048, agent_set_tabard_visible(a, 0),
             "0x0048, the pairing", "nothing."),
        Step(4.0, 0x006E, [a, 0, 0, 0, _ARMOR_LEGS_ITEM, 0,
                           _ARMOR_BOOTS_ITEM, 0, 0, 0],
             "0x006E array arm: leggings at position 3, boots at position 5 "
             "-- BAG ORDER's own claim, through the nine-dword message",
             "BOTH pieces correctly placed (gray legs AND booted feet) = bag "
             "order confirmed for 0x006E on 38797, the 2-lineage reading. "
             "Pieces on wrong body parts = the permuted reading. One piece "
             "missing = that position is neither."),
        Step(1.0, 0x0048, agent_set_tabard_visible(a, 0),
             "0x0048, the pairing", "nothing -- and the run is done; the "
             "frames from here back are the verdict."),
    ]


# Fresh definition slots and agent ids for the composite arm. Chosen clear of
# everything any co-loading path uses: definitions 3 (test enemy), 5 (sculpt),
# 9 (henchman), 10..16 (heroes), 1480 (quest giver); agents 1, 10, 20..22, 30,
# 99, 200..206.
_COMPOSITE_PROBE_DEF = 76       # 0x0056 sent, 0x0057 WITHHELD
_COMPOSITE_CONTROL_DEF = 77     # identical, plus its 0x0057
_COMPOSITE_PROBE_AGENT = 60
_COMPOSITE_CONTROL_AGENT = 61


def _composite_withheld_steps(origin):
    """A declared definition whose file NEEDS a composite, with 0x0057 withheld.

    unitsetup Q10. The unitmodels study measured the law both directions --
    0x0057 is sent exactly when the 0x0056 file's own skeleton carries the
    COMPOSITED flag ('no own geometry'), wire 43/43 and archive 14,571/14,571
    -- but nobody has ever watched the client RENDER the withheld case. Only
    the undeclared-slot case is measured, and that one is a crash (Array.h
    587), which says nothing about this one: here the definition IS declared,
    so the create indexes cleanly and whatever fails, fails later and softer.
    The hatcher's file is on the COMPOSITED side of the law (its template
    carries model_id, and every retail declaration of a composited file came
    with its 0x0057).
    """
    ox, oy, plane = origin
    h = npc_template("hatcher")
    return [
        Step(2.0, 0x0056, npc_properties(_COMPOSITE_PROBE_DEF, h),
             f"0x0056 def {_COMPOSITE_PROBE_DEF}: the hatcher's COMPOSITED "
             f"file id, and NO 0x0057 will follow",
             "nothing yet -- a type, not a body."),
        Step(1.0, 0x0056, npc_properties(_COMPOSITE_CONTROL_DEF, h),
             f"0x0056 def {_COMPOSITE_CONTROL_DEF}: the control's identical "
             f"declaration",
             "nothing yet."),
        Step(1.0, 0x0057, npc_model(_COMPOSITE_CONTROL_DEF, h),
             f"0x0057 def {_COMPOSITE_CONTROL_DEF} -- the composite, CONTROL "
             f"ONLY. The two definitions now differ in exactly one message",
             "nothing yet."),
        Step(4.0, 0x0020,
             create_agent(_COMPOSITE_CONTROL_AGENT,
                          CHAR_CLASS_MONSTER_BASE | _COMPOSITE_CONTROL_DEF,
                          AGENT_KIND_NPC, ox - 150, oy, plane),
             f"WORLD_CREATE_AGENT({_COMPOSITE_CONTROL_AGENT}) -- the control "
             f"body, 150u WEST",
             "a hatcher renders 150u WEST (the quest arc's proven frame "
             "geometry). If THIS one does not draw, the run is void -- fix "
             "the control before reading anything off the probe arm."),
        Step(4.0, 0x0020,
             create_agent(_COMPOSITE_PROBE_AGENT,
                          CHAR_CLASS_MONSTER_BASE | _COMPOSITE_PROBE_DEF,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_COMPOSITE_PROBE_AGENT}) -- the probe "
             f"body, 150u EAST, composite withheld",
             "THE QUESTION, 150u EAST: a body (the COMPOSITED flag does not "
             "gate rendering and unitmodels needs a second look), NOTHING or "
             "a floating name over empty ground (the flag means what the "
             "study says), or a crash (the missing 0x0057 is load-bearing at "
             "create time and every no-model row is living dangerously)."),
    ]


def _armor_steps(agent_id):
    # EXPLORATORY, and labelled as such. 0x006F is {agent_id, dword, dword} and
    # which dword is the slot and which the model is NOT established -- the
    # study calls the 0x006D/6E/6F mapping disputed. So try both orders on one
    # piece before doing anything with the rest.
    name, file_id, model_id = WARRIOR_ARMOR[0]
    return [
        Step(2.0, 0x006F, [agent_id, 0, model_id],
             f"equip {name}: (slot 0, model {model_id})",
             "the character. Any chest armour? Any change at all?"),
        Step(6.0, 0x006F, [agent_id, model_id, 0],
             f"equip {name}: (model {model_id}, slot 0)",
             "the character. Did the reversed argument order do something?"),
        Step(6.0, 0x006F, [agent_id, file_id, model_id],
             f"equip {name}: (file 0x{file_id:X}, model {model_id})",
             "the character. Third reading of the same two fields."),
    ]


PROBES = {
    "agent_removal": lambda a, o: Probe(
        question="Does GAME_SMSG 0x0021 remove an agent the client is already "
                 "drawing, and is its id then safe to reuse?",
        predicts="The hostile vanishes cleanly on step 1 -- no corpse, no "
                 "nameplate -- because 0x005FD2F0 walks the agent's bound objects "
                 "and clears them rather than just hiding a model. Step 2 then "
                 "shows a fresh healthy hostile at the SAME id. The informative "
                 "failure is step 1 leaving a ghost (nameplate, health bar or a "
                 "target frame that will not clear), which would mean removal is "
                 "necessary but not sufficient and something else must precede "
                 "it. If step 2 asserts or draws nothing, id reuse needs more "
                 "than a removal and our respawn cannot use it.",
        steps=_agent_removal_steps(a, o),
        note="RUN 2026-08-10. POSITIVE, both halves. Step 1: 0x0021 removes an "
             "agent the client is already DRAWING -- clean vanish, no corpse, no "
             "nameplate, no stale target frame, exactly what reading the handler "
             "at 0x005FD2F0 predicted. Steps 2-3: the removed id was RE-CREATED "
             "successfully and the fresh-id control also appeared, so a removed "
             "id is NOT poisoned and reuse needs nothing beyond the ordinary "
             "spawn burst. This is what unblocks remove-then-recreate for "
             "respawn, which is what ArenaNet does (301 of 301 live re-creations "
             "preceded by a removal of that id). AN EARLIER RUN OF THIS PROBE "
             "REPORTED THE OPPOSITE and was wrong: step 2 sent a bare 0x0020 with "
             "no NPC definition, a message payload where a model_id belongs, and "
             "the wrong plane, so it measured a bug in this file. The control at "
             "a fresh id is what separated the two, and is why it is there. "
             "Implements studies/divergence/FINDINGS.md D1, the highest-"
             "ranked protocol gap from the first live capture: ArenaNet sent "
             "0x0021 416 times, we have sent it 0 times in 271,449 messages, and "
             "301 of 301 live id re-creations were preceded by a removal of that "
             "id. TARGET THE HOSTILE BEFORE RUNNING and watch the target frame -- "
             "that is the case most likely to expose a stale reference, and it is "
             "not visible if you only watch the model. This probe deliberately "
             "does NOT touch the death/revive path: that behaviour is measured "
             "and works, and swapping it for remove-then-recreate is a separate "
             "decision that needs this probe's answer first.",
    ),
    "health_max": lambda a, o: Probe(
        question="Does int property 42 refill only when the MAXIMUM actually "
                 "changes -- or does it not carry the maximum at all?",
        predicts="THE FRACTION SURVIVES: HUD reads 50 with the bar still at a "
                 "quarter. Reasoning: the damage handler clamps against "
                 "health_max and the client stores health as a fraction "
                 "(0.25 * 200 = 50), so moving the maximum should rescale the "
                 "displayed number without touching the fraction. That makes "
                 "upstream's health_max half right and its `health = 1.f` half "
                 "wrong. A refill to 200 refutes this and vindicates upstream "
                 "on a change of value; a flat 25 says property 42 is not the "
                 "maximum either.",
        steps=_health_max_steps(a),
        note="ANSWERED 2026-08-13, and it is NONE of the three outcomes above -- "
             "the HUD read 125. `health += (new_max - old_max)`: 25 + (200-100) "
             "= 125, bar 62.5% predicted against 61.7% and 62.3% measured on two "
             "independent bars, and putting the maximum back returns exactly 25. "
             "A maximum-health increase GRANTS that health, as a rune does. So "
             "upstream's `health = 1.f` refill is REFUTED for retail, and so is "
             "this probe's own fraction prediction. Kept runnable: it is the "
             "calibration for maximum health the way `damage` is for current. "
             "Press P first; the HUD NUMBER is the measurement, not the bar.",
    ),
    "party_health": lambda a, o: Probe(
        question="Is the party row's red bar this player's HEALTH, or a constant "
                 "the row draws whatever we send?",
        predicts="It SHRINKS. WIKI (GWW, 'User interface' section Party window) "
                 "says the party window's red bars are party members' health, and "
                 "property 16 is a fraction of maximum -- so -0.5 then -0.25 must "
                 "leave the bar at about half then about a quarter of its width, "
                 "horizontally, with the name in place and the colour unchanged. "
                 "The party region must move well above the 0.007% within-arm "
                 "floor measured in RESKIN.md 18.9. A bar that stays FULL is the "
                 "more interesting result: the row would be drawing a constant "
                 "rather than this member's health.",
        steps=_party_health_steps(a),
        note="ANSWERED 2026-08-13 -- IT IS HEALTH, and to within half a percent: "
             "the bar measured 100.0%, then 49.7%, then 24.0% of its own detected "
             "extent against a prediction of 100/50/25. Kept because the third "
             "step is still UNRUN: the original recovery sent damage +0.75 and "
             "killed the client on `damage.amount <= 0` (AvChar.cpp:5893), which "
             "is a bound worth knowing and was a design error -- property 16 is "
             "DAMAGE, not a signed health delta. Press P first; with no roster on "
             "screen this measures nothing. Watch the PARTY ROW, not the HUD bar "
             "at the bottom -- both are red, both track health, and the HUD one "
             "is not what is being asked about.",
    ),
    "player_flags": lambda a, o: Probe(
        question="What does GAME_SMSG 0x003C do? It is in 12 of 12 live ArenaNet "
                 "connections, 423 sends, and this server has never sent it once "
                 "in 190 played captures.",
        predicts="NOTHING VISIBLE in a one-player instance, and that is the "
                 "honest prediction rather than a hedge: the handler's two "
                 "writes land in the same ctx+0x80C player array 0x00B0/0x00B1 "
                 "already populate, and the party roster ALREADY draws its row "
                 "without it. If something does move, the three bits are worth "
                 "far more than the message -- watch the party row first, since "
                 "that array is what a row resolves a member through.",
        steps=_player_flags_steps(a),
        note="Run this with the roster OPEN (press P first) -- a change to the "
             "player record with no window showing it is a null we could not "
             "attribute. The sweep is 4 -> 0 -> 7 rather than retail's 4 alone, "
             "because a null on 4 cannot tell 'the message does nothing' from "
             "'we already look like 4'.",
    ),
    "armor_slots": lambda a, o: Probe(
        question="Which of 0x006E's nine positions is which body slot on "
                 "build 38797 -- bag order (2 lineages) or GWLP-R's "
                 "permutation -- and is 0x006F really per-slot wear?",
        predicts="0x006F wears (the mapping stands, 3 lineages on shape), "
                 "and the ITEM drives its own placement: leggings render on "
                 "the legs from position 3 AND from position 5, making the "
                 "slot-order contest invisible to pixels -- in which case "
                 "the array arm (leggings@3 + boots@5, bag order's claim) "
                 "still renders both correctly and 0x006E order stays a "
                 "protocol-bookkeeping question, not a visual one. If "
                 "instead the SLOT drives the render, the leggings visibly "
                 "move between arms and the order is read straight off the "
                 "screen. If position-3 wear never draws at all, the "
                 "permuted reading or the sibling's mapping doubt takes it.",
        steps=_armor_slots_steps(a),
        note="The two pieces are the Prophecies warrior starters "
             "(content/items.toml, UPSTREAM from OpenTyria's own table, gray "
             "dye) -- visually loud on a body that spawns in shorts with "
             "bare calves, feet and hands. Every 0x006E is followed by "
             "0x0048, retail's 366/366 pairing. Weapon item id is 1; the "
             "probe declares its pieces as items 2 and 3. Verdict frames: "
             "after steps 3, 6 and 9. Model-appearance verdicts are the "
             "fuzzy kind -- ship the frames to the owner rather than "
             "over-reading a compressed screenshot. "
             "ANSWERED 2026-08-17 (harness 20260817T150232): 0x006F WEARS "
             "(the mapping stands), the ITEM drives its own placement "
             "(leggings on legs from position 3 AND 5, reset proven clean "
             "between), and the array arm dressed both pieces -- so the "
             "slot-order contest is invisible to pixels and survives only "
             "as bookkeeping. studies/unitsetup/FINDINGS.md 8 Q6.",
    ),
    "health_shrink": lambda a, o: Probe(
        question="What does int property 42 do to CURRENT health when the "
                 "maximum DECREASES -- and what really happened in "
                 "studies/enemy/PLAN.md 6g's max->0 full-bar frame?",
        predicts="Pure delta, both directions. Step 1 (shrink at full): 50, "
                 "bar full -- 6g's shape, no mystery. Step 4 (shrink onto a "
                 "quarter pool): the grant is 25 + (50-100) = -25, the pool "
                 "clamps at its floor of 1, orb reads 1. Step 5 (restore): "
                 "51, because the clamp DESTROYED 24 health and += cannot "
                 "know that. A 50 at step 4 resurrects the refill reading "
                 "for the shrink direction only; 12-13 means the fraction "
                 "survives shrink and the mechanism is direction-split.",
        steps=_health_shrink_steps(a),
        note="Run --explorable like the health_max run it extends (damage on "
             "an outpost map is swallowed). The readout is the HUD orb's "
             "printed NUMBER, bottom centre -- RESKIN 18.13's method note: "
             "bar fills are only good to a few points, the number is exact. "
             "ANSWERED 2026-08-17 (harness 20260817T143333): 50/100/25/1/25. "
             "The 25-out kills all three candidates -- the store is SIGNED "
             "and unclamped (-25 survived the excursion), the HUD floors the "
             "DISPLAY at 1. studies/unitsetup/FINDINGS.md 8 Q5.",
    ),
    "composite_withheld": lambda a, o: Probe(
        question="What does the client RENDER for a declared definition whose "
                 "COMPOSITED file gets no 0x0057 -- the one cell of the "
                 "composite law no study has watched?",
        predicts="The control hatcher renders 150u WEST; the probe arm 150u "
                 "EAST draws NO geometry and does NOT crash -- the definition "
                 "is declared so the create indexes cleanly, and COMPOSITED "
                 "means the skeleton has no geometry of its own to fall back "
                 "on. A rendered body EAST refutes unitmodels' reading of the "
                 "flag; a crash promotes the missing 0x0057 from cosmetic to "
                 "load-bearing.",
        steps=_composite_withheld_steps(o),
        note="RUN ON --map 449 (the quest arc's proven +/-150u frame "
             "geometry -- both spots visible without touching the camera). "
             "Definitions 76/77 and agents 60/61 are chosen clear of every "
             "co-loading id. Verdict frames: after step 4 (control WEST must "
             "draw) and after step 5 (the question, EAST). "
             "ANSWERED 2026-08-17 (harness 20260817T143717): a solid WHITE "
             "BOX, body-sized, at the probe body's spot -- no crash, no "
             "invisibility, a positive placeholder. The white box is now a "
             "known on-screen signature for 'composite needed, none sent'. "
             "studies/unitsetup/FINDINGS.md 8 Q10.",
    ),
    "armor": lambda a, o: Probe(
        question="What are the two dwords in 0x006F, and does it dress the agent?",
        predicts="One of the three argument orders produces visible chest armour. "
                 "If none does, 0x006F is not the visual-equip message on this "
                 "build and the 0x006D/6E/6F mapping needs revisiting.",
        steps=_armor_steps(a),
        note="EXPLORATORY. The study calls this mapping disputed; we are trying "
             "readings, not confirming a known one.",
    ),
}
