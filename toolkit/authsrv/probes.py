"""Scripted one-packet experiments, fired at our own client after it spawns.

studies/character/FINDINGS.md ends with a probe queue: a set of questions where
all read-only research is exhausted and only the client can settle them. Reading
more mirrors cannot help, because for several of these every mirror is the same
witness wearing different clothes. The client is the last court.

Each probe is a short sequence of packets with a stated question, a stated
prediction, and an instruction about what to look at. The prediction matters: a
probe that does not say in advance what it expects can be rationalised after the
fact into agreeing with whatever happened, which is how we ended up with three
comments in authsrv.py stating inference as fact.

Usage, once the character is standing in the map:

    python toolkit/authsrv/authsrv.py --probe level
    python toolkit/authsrv/authsrv.py --list-probes

The server runs the sequence after the spawn burst, prints what to watch for
before each step, and records every packet to the capture as usual. Nothing here
touches anything but our own loopback client.

WHY DELAYS. The steps are spaced so a person can see one result before the next
arrives. A probe that fires three packets in 50 ms tells you only what the last
one did.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import questdefs                                            # noqa: E402
# The `agents` surface and the probe constants above moved WHOLE to
# `probebase.py`, the leaf every module in this family imports: this block was
# the one thing all seven of `probes.py`'s subjects referenced, so nothing else
# could move until it had a home. Re-exported here because the step builders
# below read every one of them by bare name. `_ENEMY_ROW`, `WORLD` and
# `PROBE_BAR_SLOT` have no reader left in this file and are carried anyway, so
# `vars(probes)` still answers for exactly what it did before the split.
# CORRECTION 2026-09-11, appended rather than reworded: `PROP_CAST_SKILL` and
# `PROP_CAST_TIME` joined that set later the same day, when the skill builders
# that were their only readers here left for `probeskills.py`. They are carried
# for the same reason the other three are, that module imports both from
# `probebase.py` directly, and the last sentence above still holds.
# CORRECTION 2026-09-11, appended the same way and on the same day: after the
# unit-setup, character and combat arms left, TWENTY-FIVE of the thirty-six
# names in this block have no reader left in this file. The eleven that do are
# AGENT_KIND_NPC, ALLEGIANCE_HOSTILE, CHAR_CLASS_MONSTER_BASE,
# EFFECT_TRANSITION, ENEMY_AGENT_ID, ENEMY_DEFINITION, FRESH_AGENT_ID,
# PROBE_SPAWN_NEAR, PROP_APPEARANCE_65, PROP_APPEARANCE_66 and create_agent,
# read by the burrow, encoded-name, coded-chat and property-66 arms, which are
# what is left here. The other twenty-five are carried for the reason the first
# paragraph gives, and every sibling imports what it needs from `probebase.py`
# directly rather than through this line.
from probebase import (                                     # noqa: F401,E402
    AGENT_KIND_NPC, AGENT_KIND_PLAYER, AGENT_TYPE_LIVING,
    ALLEGIANCE_HOSTILE, APPEARANCE_WARRIOR,
    CHAR_CLASS_MONSTER_BASE, CHAR_CLASS_PLAYER_BASE,
    DEFAULT_RUN_SPEED, EFFECT_DEAD, EFFECT_TRANSITION, HATCHER, INF, WORLD,
    agent_set_profession, agent_set_secondary_bits,
    agent_set_tabard_visible, create_agent, item_template, named_item,
    npc_model, npc_properties, npc_template,
    ENEMY_AGENT_ID, ENEMY_DEFINITION, FRESH_AGENT_ID,
    PROBE_BAR_SKILL, PROBE_BAR_SLOT, PROBE_PLAYER_NUMBER, PROBE_SPAWN_NEAR,
    PROP_APPEARANCE_65, PROP_APPEARANCE_66, PROP_CAST_SKILL, PROP_CAST_TIME,
    PROP_LEVEL, WARRIOR_ARMOR, _ENEMY_ROW)


# `Step` and `Probe` moved to `probebase.py`. Re-exported here because every
# step builder below constructs them by bare name, and because `authsrv.py`
# (the probe runner) and `test_agentlife.py` both read `probes.Step`.
from probebase import Probe, Step                           # noqa: F401,E402


# The unit-setup and level arms that stood HERE moved WHOLE -- the agent-removal
# and id-reuse arm, the health-maximum and health-shrink arms and the party
# row's bar, and the 0x003C player-flag word to `probeunitsetup.py`; the `level`
# arm and the henchman agent id it is measured against to `probecharacter.py`.
# Re-exported here because `vars(probes)` is this module's public surface:
# NOTHING outside reads any of these seven names today (measured -- zero
# referrers in the tree, and the only monkeypatch sites anywhere are on
# `probes.get`), and dropping seven attributes nobody happens to read is a
# behaviour change no test in the suite would have caught. `PROBES` is
# deliberately NOT in either list; the registry entries are merged in where the
# `PROBES` literal closes below.
from probeunitsetup import (                                # noqa: F401,E402
    _agent_removal_steps, _health_max_steps, _health_shrink_steps,
    _party_health_steps, _player_flags_steps)
from probecharacter import (                                # noqa: F401,E402
    HENCHMAN_AGENT_ID, _level_steps)


# The armour-slot item ids moved to `probebase.py`, taking the 2026-08-27
# collision banner with them -- all five `_*_ITEM` ids together, because that
# banner is what names the 40s band and it cross-references the drain three by
# name. Re-exported here because `_armor_slots_steps` below reads them, and
# `test_armour.py` section 2 scores every `_*_ITEM*` name in `probes` AND in
# every `probe*.py` beside it.
# CORRECTION 2026-09-11, appended rather than reworded: `_armor_slots_steps`
# left for `probeunitsetup.py` later the same day and imports both ids from
# `probebase.py` directly, so there is no reader for either in this file. The
# re-export stays for the second half of the sentence, which is unchanged --
# `test_armour.py` section 2 walks every `probe*.py` on disk and scores the
# `_*_ITEM` band, and `vars(probes)` must keep answering for what it answered
# for before.
from probebase import (                                     # noqa: F401,E402
    _ARMOR_BOOTS_ITEM, _ARMOR_LEGS_ITEM)


# `_armor_slots_steps` moved to `probeunitsetup.py` with the other unit-setup
# arms, and `_allegiance_split_steps` -- the 0x00AA-versus-0x002F
# discriminator -- moved to `probecombat.py` with the rest of the allegiance
# family. Re-exported here for the reason the block above gives.
from probeunitsetup import _armor_slots_steps               # noqa: F401,E402
from probecombat import _allegiance_split_steps             # noqa: F401,E402


# The three accum-drain item ids moved to `probebase.py`, with the two comment
# lines that are about them, so all five `_*_ITEM` ids sit under the one
# collision banner that already cross-references "`_DRAIN_ITEM_A/B/C` are
# 40/41/42". Re-exported here because the merchant and drain probes below read
# them, and `test_armour.py` section 2 scores them.
# CORRECTION 2026-09-11, appended rather than reworded: "the merchant and
# drain probes below" left for `probemerchant.py` later the same day, and
# that module imports these three from `probebase.py` directly. The
# re-export stays for the second half of the sentence -- `test_armour.py`
# section 2 walks every `probe*.py` on disk and scores the `_*_ITEM` band,
# and `vars(probes)` must keep answering for what it answered for before.
from probebase import (                                     # noqa: F401,E402
    _DRAIN_ITEM_A, _DRAIN_ITEM_B, _DRAIN_ITEM_C)


# The merchant probes' step builders and their constants moved WHOLE to
# `probemerchant.py` -- the stock table and its flags override, the 0x00C3
# window-kind sweep, the merchant window, the gold purse, the price-scale
# arm and the two accumulator-drain arms. Re-exported here because
# `vars(probes)` is this module's public surface: NOTHING outside reads any
# of these seventeen names today (measured -- zero referrers in the tree,
# and the only monkeypatch sites anywhere are on `probes.get`), and dropping
# seventeen attributes nobody happens to read is a behaviour change no test
# in the suite would have caught. `PROBES` is deliberately NOT in this list;
# the merchant registry entries are merged in where the `PROBES` literal
# closes below.
from probemerchant import (                                 # noqa: F401,E402
    EQUIPPED_BAG_ID, PLAYER_INVENTORY, _MERCHANT_NPC_AGENT, _STOCK,
    _STOCK_COUNT, _STOCK_FIRST_ID, _STOCK_FLAGS, _STOCK_TEMPLATES,
    _WINDOW_KINDS, _WINDOW_KIND_CONTROL, _accum_drain_e1_steps,
    _accum_drains_steps, _gold_purse_steps, _merchant_window_steps,
    _shop_price_scale_steps, _shop_window_kinds_steps, _stock_item)


# The composite-withheld arm with its four fresh definition and agent slots,
# and the exploratory 0x006F armour arm that stood further down this run, moved
# to `probeunitsetup.py`. Everything else cut from HERE moved to
# `probecharacter.py` -- the henchman level arm, the six profession arms, the
# attribute panel and its three sweeps, the two morale arms, the regeneration
# channel, property 54, the faction maximum and the title track. Re-exported
# here for the reason the blocks above give.
from probeunitsetup import (                                # noqa: F401,E402
    _COMPOSITE_CONTROL_AGENT, _COMPOSITE_CONTROL_DEF, _COMPOSITE_PROBE_AGENT,
    _COMPOSITE_PROBE_DEF, _armor_steps, _composite_withheld_steps)
from probecharacter import (                                # noqa: F401,E402
    _attr_legend_steps, _attr_sweep_steps, _attribute_steps,
    _faction_max_steps, _henchman_level_steps, _morale_steps,
    _morale_store_steps, _player_attrs_steps, _profession_ab_steps,
    _profession_panel_steps, _profession_secondary_steps,
    _profession_skillbar_steps, _profession_steps, _profession_trigger_steps,
    _prop54_steps, _regen_channel_steps, _title_track_steps)


# `_f32` moved to `probebase.py`, and took `import struct` with it -- it is the
# only user of that import in this file. Re-exported here because 53 step
# builders below call it by bare name.
# CORRECTION 2026-09-11, appended rather than reworded: "53 step builders
# below" is now ZERO. `_f32`'s last readers here -- the health-pool, regen,
# damage, death and kill arms -- left for `probeunitsetup.py`,
# `probecharacter.py` and `probecombat.py` on the same day, and all three
# import it from `probebase.py` directly. The line is kept because
# `vars(probes)` is this module's public surface and `probes._f32` answered
# before the split.
from probebase import _f32                                  # noqa: F401,E402


# The damage arm, the superseded 0x002D arm, the three allegiance FourCCs and
# the three-body allegiance arm moved to `probecombat.py`. `ALLEGIANCE` is
# re-exported with the builders and not left behind: `PLAN.md` section 6.1's
# derivation-register row was re-aimed at `probecombat.py` BEFORE the constants
# moved, and that row says `probes.py` re-exports them.
from probecombat import (                                   # noqa: F401,E402
    ALLEGIANCE, _allegiance_steps, _damage_steps, _die_0x2d_steps)


# `PROBE_DEFINITION`, and the note above it, moved to `probebase.py` with the
# other reserved ids. Re-exported here because the NPC, allegiance and burrow
# probes below read it.
# CORRECTION 2026-09-11, appended rather than reworded, and it corrects a
# second thing besides the move: the NPC and allegiance probes left for
# `probecombat.py`, which imports `PROBE_DEFINITION` from `probebase.py`
# directly -- and the burrow probe, which is still in this file, turns out
# never to have read this name at all (measured on the AST, not read off the
# sentence). No reader is left here. Kept for `vars(probes)`, like the
# re-exports above.
from probebase import PROBE_DEFINITION                      # noqa: F401,E402


# The rest of the combat family moved to `probecombat.py` -- the monster-class
# NPC arm, the two NPC allegiance arms, the enemy-damage and attack-animation
# arms, the EFFECTS bitfield and its death bit, the death, health-property,
# moving-die and kill arms, and the superseded v1 kill arm kept for its record.
# Re-exported here for the reason the blocks above give. `EFFECT_DEAD` is in
# the list because it is REBOUND here and not merely read: it arrives from
# `probebase` at the top of this file, and the assignment that stood at this
# site is what this line stands in for -- so `probes.EFFECT_DEAD` is bound in
# the same order, after the same import, to the same value it always was.
from probecombat import (                                   # noqa: F401,E402
    EFFECT_DEAD, _allegiance_pair_steps, _attack_anim_steps, _death_steps,
    _enemy_damage_steps, _health_props_steps, _kill_steps,
    _kill_steps_v1_unused, _moving_die_steps, _npc_agent_steps,
    _npc_allegiance_steps)


def _team_token_steps(agent_id):
    # Not a packet probe: the token now goes out at spawn. This exists so the
    # run is recorded with a question attached rather than being assumed fine.
    return []


# The skill probes' step builders moved WHOLE to `probeskills.py` -- the
# skillbar copy and disable arms, the partial-bar arm, the three casting-
# property arms and the real-spell control, the 211 unlock arm, and the
# deep-wound, heal-number, condition-render, effect-extension and lone
# property-17 arms. Re-exported here because `vars(probes)` is this module's
# public surface: NOTHING outside reads any of these twelve names today
# (measured -- zero referrers in the tree, and the only monkeypatch sites
# anywhere are on `probes.get`), and dropping twelve attributes nobody happens
# to read is a behaviour change no test in the suite would have caught.
# `PROBES` is deliberately NOT in this list; the skill registry entries are
# merged in where the `PROBES` literal closes below.
from probeskills import (                                   # noqa: F401,E402
    _cast_anim_steps, _cast_one_steps, _cast_spell_steps,
    _condition_render_steps, _deep_wound_steps, _effect_silent_extend_steps,
    _heal_number_steps, _lone_p17_steps, _skill_copy_steps,
    _skill_disable_steps, _skill_partial_steps, _unlock_211_steps)


# The live 0x5D chat line this probe replays and then rewrites. MEASURED off
# ArenaNet's own wire (capture 20260807T143055 :60935 t=21.1, byte-identical
# again in 20260810T235916 :61193): template sid 1796 -- a PLAIN archive record,
# no key needed -- followed by four single-word numeric args, no terminator.
# Words are ids and numbers, not text; the prose lives in the owner's archive
# and is resolved by the client at render time.
CHAT_TEMPLATE_SID = 1796
CHAT_LIVE_ARGS = [13, 51, 1, 17]         # what ArenaNet sent, verbatim
CHAT_OUR_ARGS = [42, 7, 3, 99]           # ours -- distinct from every live value
CHAT_BIG_VALUE = 40000                   # forces the multi-word varint path


def _chat_units(sid, args):
    """[sid+0x100] + one 0x100-biased word per small arg."""
    return "".join(chr(0x100 + v) for v in [sid] + list(args))


def _chat_varint_units(sid, big):
    """The multi-word encoding for a value >= 0x7F00.

    studies/textrec (TextParser.cpp 0x7ccd2a): acc = acc*0x7F00 + (word-0x100),
    continuation = 0x8000. UNVERIFIED in the send direction until this probe --
    the decode rule is measured, our encode of it has never been through a
    client.
    """
    hi, lo = divmod(big, 0x7F00)
    words = [0x8000 | (0x100 + hi), 0x100 + lo]
    return "".join(chr(0x100 + sid)) + "".join(chr(w) for w in words) + \
        "".join(chr(0x100 + v) for v in CHAT_OUR_ARGS[1:])


def _coded_chat_steps(agent_id):
    """Isle rung 4, the probe rung 7 waits on: our coded-string ENCODE, rendered.

    studies/isle/FINDINGS.md B8: numeric arguments in coded strings are cleartext
    varints on a code path with no RC4 -- measured in the DECODE direction on 50
    live 0x5D messages. What has never happened is the SEND direction: no coded
    string with numeric args built by us has been through a client. The Master
    of Damage plan reads DPS numbers out of exactly this format, so if our
    encode does not round-trip, rung 7's analysis tooling is built on a guess.
    """
    # RUN 2026-08-16 (twice, operator watching): all three bare 0x5D steps
    # rendered NOTHING, with exactly ONE 'Invalid coded string' in Gw.log per
    # run -- so two were ACCEPTED and still not displayed. Live traffic never
    # sends 0x5D bare: every one is paired with an 0x5E channel/color tag
    # (t=21.06 in 20260807T143055: 0x5D [sid 1796 + args] then 0x5E [51, 10]).
    # This revision replays the pair, verbatim tag after each line.
    TAG = [51, 10]
    return [
        Step(2.0, 0x005D, [_chat_units(CHAT_TEMPLATE_SID, CHAT_LIVE_ARGS)],
             "93: ArenaNet's own level-up line, replayed verbatim",
             "nothing yet -- the channel tag comes next."),
        Step(0.5, 0x005E, list(TAG),
             "94: its channel tag [51, 10], the captured partner",
             "the CHAT PANEL. The control: these are the exact words ArenaNet "
             "sent on 2026-08-07 WITH their tag, so SOMETHING should render, "
             "with 13, 51, 1 and 17 somewhere in it."),
        Step(10.0, 0x005D, [_chat_units(CHAT_TEMPLATE_SID, CHAT_OUR_ARGS)],
             "93: the same template, OUR numbers 42/7/3/99",
             "nothing yet."),
        Step(0.5, 0x005E, list(TAG),
             "94: the tag again",
             "THE MEASUREMENT. The same line with 42, 7, 3, 99 in the roles "
             "the control's numbers held. If the numbers on screen are ours, "
             "the value-word encode round-trips and rung 7 can read the "
             "Master of Damage."),
        Step(10.0, 0x005D, [_chat_varint_units(CHAT_TEMPLATE_SID,
                                               CHAT_BIG_VALUE)],
             "93: first arg as a MULTI-WORD varint carrying 40000",
             "nothing yet."),
        Step(0.5, 0x005E, list(TAG),
             "94: the tag again",
             "the same line with 40000 as its first number -- the encoding a "
             "five-digit damage total needs, never exercised in the send "
             "direction."),
        Step(10.0, 0x005F, [ENEMY_AGENT_ID, 0,
                            "".join(chr(0x100 + 2972))],
             "95: NPC overhead text on the hostile -- one bare sid, 2972",
             "text ABOVE THE HOSTILE's head. Sid 2972 is the Isle of the "
             "Nameless map name, a PLAIN record the archive resolves without "
             "a key -- if the words appear over the body, 0x5F works end to "
             "end and the overhead half of the Master of Damage's announce "
             "channel is proven too. The u8 field is 0 on a guess; if "
             "nothing draws, that byte is the first suspect."),
    ]


def _encname_render_steps(origin):
    """Isle rung 4: a CAPTURED enc_name, rendered by our own client.

    The Hatcher precedent, pointed at the Isle's naming problem: rung 6's roster
    will identify NPCs by their 0x0056 enc_name tuples, which no tool can decode
    (the RC4 key pair's location is NOT FOUND -- studies/textrec). The one
    working route is this: send the captured tuple to our own client and read
    the nameplate. def_1470 is the cross-session station agentroster.py pins
    (slot 1470, model 116698, byte-identical three days apart on map 148), so
    its name is also a check against the operator's own memory of Ascalon City.
    """
    ox, oy = (origin[0], origin[1]) if origin else (0.0, 0.0)
    # The def_1470 declaration, verbatim from vault/content/npcs.toml (OBSERVED
    # on ArenaNet's wire, 8 connections, 2 captures, byte-identical) -- EXCEPT
    # the index. OBSERVED 2026-08-16 (harness 20260816T211432): declaring INDEX
    # 1470 into our minimal instance made the 38833 client send its goodbye
    # family (0x0008/0x000A/0x000B/0x000D) and reset the connection -- the
    # declare path evidently will not take an index ~1460 above anything the
    # instance has seen, on a table retail populates densely. The index carries
    # no naming semantics, so the probe uses a small unused one; the rejection
    # itself is recorded as a real bound on any replay idea rung 6 might have.
    DEF, FILE_ID, MODEL = 25, 116227, 116698
    SCALE, FLAGS, PROF, LEVEL = 1677721600, 524, 3, 2
    ENC = [3943, 39638, 36630, 30448]
    enc_str = "".join(chr(u) for u in ENC)
    return [
        Step(2.0, 0x0056, [DEF, FILE_ID, 0, SCALE, 0, FLAGS, PROF, LEVEL,
                           enc_str],
             "86: declare definition 1470, the captured payload verbatim",
             "nothing yet -- a declaration draws nothing on its own."),
        Step(1.0, 0x0057, [DEF, [MODEL]],
             "87: its model, 116698", "still nothing."),
        Step(1.0, 0x0020,
             create_agent(FRESH_AGENT_ID,
                          CHAR_CLASS_MONSTER_BASE | DEF, AGENT_KIND_NPC,
                          ox + PROBE_SPAWN_NEAR, oy, 0,
                          allegiance=ALLEGIANCE_HOSTILE),
             "32: a body wearing it, 150u out",
             "THE NAMEPLATE. Hold Ctrl and read the name over the body out "
             "loud -- that string is the measurement, and it is the exact "
             "route rung 6 uses to identify all ~50 Isle bodies. If the "
             "plate is blank or garbage, the enc_name path our roster plan "
             "depends on does not work and rung 6 needs the marks ordinals "
             "instead. Bonus check: the model should be an Ascalon City "
             "guard-ish human, the station agentroster pins on map 148."),
        Step(12.0, 0x0021, [FRESH_AGENT_ID], "33: remove it", "clean up."),
    ]


# The second block of skill builders moved to `probeskills.py` too -- the
# buff-type and buff-side arms, the minion counter, the cast-modifier ordering
# arm and the pool-fraction arm. They are re-exported from HERE rather than
# folded into the list above because that is where they were cut from: the
# chat and enc-name builders that sit between the two blocks are a different
# subject and stayed, so a reader who greps for one of these five names lands
# on the site it left.
from probeskills import (                                   # noqa: F401,E402
    _buff_side_steps, _buff_type_steps, _cast_modifier_order_steps,
    _minion_count_steps, _pool_fraction_steps)


def _burrow_steps(agent_id, origin):
    """Does an NPC definition survive a removal, and does 0x1000 do anything?

    THE QUESTION THIS EXISTS FOR, and it is the one thing burrowing needs that no
    offline test can reach. ArenaNet sends the NPC definition (0x0056) exactly ONCE
    for 140 re-creates of the same Plague Worm, so their client evidently keeps a
    definition across a removal. Ours has never been asked: `agent_removal`'s step 2
    resends 0x0056 and 0x0057 every single time -- deliberately, because the FIRST
    version of that probe omitted them along with two other things and produced a
    negative that meant nothing. So its success tells us the id is reusable and says
    nothing whatever about the definition.

    That matters because the failure mode is asymmetric. `npc_properties`' own
    docstring: an agent whose definition was never sent takes the client down on
    `index < m_count` in Base\\rtl\\Array.h. If definitions do NOT survive, a burrow
    that stops resending crashes the client on the first re-emergence. So the server
    resends today and this probe is what would let it stop.

    THE CONTROL IS THE DESIGN, same as D1's. Step 3 re-creates at the SAME id with no
    definition; step 4 does it at a FRESH id, also with no definition.

        3 works, 4 works  -> a definition is per-INSTANCE and outlives its agents.
                             Burrowing can stop resending; ArenaNet's 1-for-140 is
                             explained.
        3 fails, 4 works  -> the id is the problem, not the definition, and that
                             contradicts agent_removal's positive result -- look at
                             this file before believing it.
        both fail         -> definitions are bound to the agent that used them. Keep
                             resending, and ArenaNet must be doing something else we
                             have not seen.

    WHAT IS DELIBERATELY NOT HERE. The clean negative control -- create an agent
    referring to a definition that was NEVER sent, and confirm the client asserts --
    is the experiment that would nail this down, and it is exactly the crash the
    docstring above describes. Taking the client down to prove it goes down is not
    worth the run; the asymmetry is recorded instead.

    Steps 1-2 are cheap and ride along: EFFECT_TRANSITION (0x1000) is the bit
    ArenaNet sets on 140 of 140 worm creates and clears 2.00 s later -- and the two
    windows have different n, because a capture starts and ends mid-cycle: emerge
    n=137 in [1.976, 2.021], submerge n=132 in [1.973, 2.037]. What the
    client DOES with it is UNVERIFIED -- we know only its timing. Property 66, which
    also appears in the worm burst, is NOT probed here: `prop66_sweep` already owns
    that question and section 16.4 has already bounded it to one byte at AvChar+0x113.
    """
    ox, oy, plane = origin if origin else (0.0, 0.0, 0)
    same = (ox + PROBE_SPAWN_NEAR, oy)
    fresh = (ox + 2 * PROBE_SPAWN_NEAR, oy)
    model_id = CHAR_CLASS_MONSTER_BASE | ENEMY_DEFINITION
    return [
        Step(3.0, 0x00F1, [ENEMY_AGENT_ID, EFFECT_TRANSITION],
             "set the TRANSITION bit (0x1000) on the hostile",
             "the hostile. Does anything change at all -- an animation, a fade, the "
             "nameplate, whether you can still click it? ArenaNet sets this bit for "
             "exactly 2.00 s as a worm comes up and again for 2.00 s as it goes down. "
             "If nothing visible happens, the bit is bookkeeping and our burrow does "
             "not need it."),
        Step(4.0, 0x00F1, [ENEMY_AGENT_ID, 0],
             "clear it again",
             "whether whatever step 1 did reverses. If step 1 made it untargetable, "
             "this should give it back."),
        Step(3.0, 0x0021, [ENEMY_AGENT_ID],
             "REMOVE the hostile",
             "a clean vanish, as agent_removal already established. TARGET IT FIRST "
             "-- the target frame is where a stale reference shows."),
        # --- step 3: the same id, and NO definition resend ----------------------
        Step(4.0, 0x0020,
             create_agent(ENEMY_AGENT_ID, model_id, AGENT_KIND_NPC,
                          same[0], same[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"RE-CREATE at the SAME id ({ENEMY_AGENT_ID}) with NO 0x0056/0x0057",
             f"{PROBE_SPAWN_NEAR:.0f} units out. Does the body appear, and does it "
             "look RIGHT -- a collector, correctly named -- or is it a default/blank "
             "model? A wrong-looking body is as informative as no body: it would mean "
             "the definition slot survived but its contents did not."),
        # --- step 4: the CONTROL, a fresh id, also with no definition -----------
        Step(6.0, 0x0020,
             create_agent(FRESH_AGENT_ID, model_id, AGENT_KIND_NPC,
                          fresh[0], fresh[1], plane,
                          allegiance=ALLEGIANCE_HOSTILE),
             f"CONTROL: a FRESH id ({FRESH_AGENT_ID}), still no definition",
             f"{2 * PROBE_SPAWN_NEAR:.0f} units out. If this one appears and step 3 "
             "did not, the id is the problem rather than the definition -- which "
             "would contradict agent_removal and means this file is wrong before the "
             "protocol is."),
    ]


def _prop66_sweep_steps(agent_id):
    """What is property 66? Walk the byte and watch the character.

    Section 16.4 bounded this one without naming it. The chain is short and
    every step of it is MEASURED:

        0x00812EBD  case 66  ->  AvApi 0x007E0550   (assert(agent), AvApi:1474)
        0x007E0550  resolve  ->  0x007F7C40 if the agent has an AvChar,
                                 0x007F7C60 if it does not
        0x007F7C40  av->m108->byte7 = (uint8)value ; av->byte113 = (uint8)value

    Three things follow, and they are what make this probe cheap:

      * THE VALUE IS ONE BYTE. Everything above bit 7 is discarded silently, so
        a server sending a large int loses it without a word.
      * IT IS AN APPEARANCE ATTRIBUTE, NOT AN EVENT. The else-branch writes the
        same byte into a global agent-indexed table for agents that have no
        AgentView object yet, which only makes sense for something applied when
        a body is next built.
      * IT IS PROPERTY 65'S NEIGHBOUR. 65 writes byte +5 of the same record and
        66 writes byte +7. OpenTyria names 65 `PvPTeam`; 66 is past the end of
        its enum and unnamed everywhere.

    WHY 65 IS IN THIS PROBE AT ALL. 65's setter compares the old byte against
    the new one and calls a refresh (0x007F3BC0) when it changed; 66's writes
    unconditionally and calls nothing. So 66's byte may sit in the record doing
    nothing visible until something else rebuilds the character -- and toggling
    65 is the cheapest way we know to force that rebuild. Every value of 66
    below is therefore followed by a 65 toggle.

    WHICH MAKES STEP 1 THE CONTROL, and it is not optional: a 65 toggle may well
    change the character by itself, so what a BARE toggle looks like has to be
    established before any of it can be attributed to 66.

    NOT A FULL SWEEP, deliberately. A byte has 256 values and the `attr_legend`
    lesson says a result read at rest shows only the last state, so this walks
    six spaced values with the observer watching each one land. 255 goes last:
    it is outside any plausible enum, so if the earlier values do nothing and
    255 does something ugly, that is still an answer.
    """
    def toggle(delay):
        return [
            Step(delay, 0x009F, [PROP_APPEARANCE_65, agent_id, 1],
                 "  65 -> 1 (force a refresh)", "watch the character."),
            Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                 "  65 -> 0 (and back)", "watch the character."),
        ]

    steps = [
        Step(2.0, 0x009F, [PROP_APPEARANCE_66, agent_id, 0],
             "CONTROL: property 66 = 0, then a bare 65 toggle",
             "the character. 66 = 0 should be whatever it already was."),
    ]
    steps += toggle(3.0)
    steps[-1] = Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                     "  65 -> 0 (and back)",
                     "THE CONTROL. Whatever changed across these two packets is "
                     "65's doing, not 66's, and must be discounted below. If the "
                     "character flickered, changed colour, changed nameplate or "
                     "moved at all, write down exactly what.")
    for value in (1, 3, 8, 255):
        steps.append(Step(
            8.0, 0x009F, [PROP_APPEARANCE_66, agent_id, value],
            f"property 66 = {value}",
            f"the character, immediately. Anything at all? "
            f"{'255 is outside any plausible enum, so ugly is informative. ' if value == 255 else ''}"
            f"Then the refresh pair lands."))
        steps += toggle(4.0)
    steps[-1] = Step(2.0, 0x009F, [PROP_APPEARANCE_65, agent_id, 0],
                     "  65 -> 0 (and back)",
                     "the last packet. Read the character at leisure -- nothing "
                     "follows. It is standing at 66 = 255, 65 = 0. If nothing "
                     "differed from the control at ANY value, 66 needs a "
                     "rebuild this probe cannot trigger, and the next move is "
                     "finding what reads AvChar+0x113 rather than sending a "
                     "seventh value.")
    return steps


def _smsgsweep_steps(a, o, dwell=0.4):
    """One step per planned opcode: the loopback half of the never-seen sweep.

    Unlike every other probe here the steps are NOT seconds apart for a human to watch.
    The readout is the capture, not the screen -- `smsgsweep.analyse` attributes each
    c2s reply by IDENTITY, so the dwell only has to exceed the client's reaction time,
    not a person's. 0.4 s over 324 opcodes is about two minutes.

    THE FIRST STEP'S DELAY IS THE EXPERIMENT'S CONTROL, and it is why this probe waits
    ten seconds before doing anything. The pilot of 2026-08-12 fired its first packet
    3.66 s in, 0.2 s after the client's own load traffic stopped arriving
    (INSTANCE_LOAD_REQUEST_SPAWN_POINT, MISSION_MASK_REPORT, TARGET_SELECT) -- and a c2s
    0x0000 landing 5 ms later was scored as a reply to that first send. It may be one.
    That run had no way to tell. So: `settle` seconds of nothing for the load to finish,
    then `control` seconds of nothing that the analyser MEASURES -- whatever the client
    says in that window it said unprompted, and a "reply" on one of those opcodes is
    downgraded to CONTESTED rather than counted as a binding.

    The plan owns both numbers, so the analyser reads back exactly what the run used.
    Passing them separately is how a control window silently moves off the quiet part.

    An empty plan is a REFUSAL rather than an empty run: a probe that sends nothing and
    prints "complete" is exactly the shape of a green run that measured nothing.
    """
    import smsgsweep
    p = smsgsweep.load_plan()
    if not p or not p.get("rows"):
        return [Step(0.0, 0x0000, [], "NO PLAN -- run smsgsweep.py --plan first",
                     "nothing was sent; this run measures nothing", sends=False)]
    codec = _sweep_codec()
    dwell = float(p.get("dwell", dwell))
    quiet = (float(p.get("settle", smsgsweep.SETTLE))
             + float(p.get("control", smsgsweep.CONTROL)))
    steps = []
    for i, row in enumerate(p["rows"], 1):
        opcode = row["opcode"]
        # THE OVERRIDES ARE PER ROW, and reading them off `p` is not a near miss -- it is
        # silent. `plan()` resolves `--set 5=1` and `--set 0x0083:2=1` against EACH opcode
        # (sets_for) and writes the result into THAT ROW.
        #
        # It also wrote a top-level copy for about an hour on 2026-08-12 -- which is the
        # whole story. `p.get("set")` was correct when --set shipped (f3e0d95, 10:59) and
        # became a no-op when the qualified `0x0083:2=1` form replaced the top-level key
        # with sets_for (c7c7da6, 12:00). This line was not updated, so from then on every
        # --set run put the DEGENERATE payload on the wire while reporting the experiment.
        # Nothing downstream could catch it: the plan file is right, the capture is right,
        # and `record` scores the capture -- so the run reads as a measurement of a payload
        # that was never sent, and five of studies/smsgsweep/FINDINGS.md 5c's experiments
        # were retracted for it. Keys are strings because the plan is JSON.
        try:
            values = smsgsweep.apply_set(smsgsweep.degenerate(codec, opcode,
                                        encstring=p.get("encstring")),
                                        {int(k): v for k, v in
                                         (row.get("set") or {}).items()})
        except ValueError:
            continue                       # recorded in the plan's `refused` already
        steps.append(Step(quiet if i == 1 else dwell, opcode, values,
                          f"[{i}/{len(p['rows'])}] 0x{opcode:04X} "
                          f"({row.get('predicted', '?')})",
                          "any c2s the control window did not also produce is a reply"))
    return steps


def _sweep_codec():
    from codec import Codec
    return Codec()


# ------------------------------------------------------- minimap / compass --
#
# PLAN C4. Every value below is computed from a measurement rather than chosen,
# and the two that could not be computed are REPLAYED VERBATIM from ArenaNet.
#
# KNOTS (0x0091). Two SIGNED int16 packed in one dword, LOW half = x, in
# ABSOLUTE world units divided by 96.0 -- the terrain cell pitch
# (studies/minimap/FINDINGS.md §4.1, closed against the one live 0x002B and
# three rival readings). The compass hit-test bounds a click at exactly 4500.0
# world units, so a knot must sit beside the player to be inside the disc at
# all; map 148's spawn is (9826, 8077), i.e. cell (102, 84).
COMPASS_CELL = 96.0
_SPAWN_CELL = (102, 84)                    # 9826/96, 8077/96, round-away-from-zero


def _knot(cx, cy):
    """Pack one knot the way CompassCanvas does: low half x, high half y."""
    return ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)


# THE FOG INIT PAIR IS ARENANET'S OWN, NOT OURS, AND THAT IS THE POINT.
# The RLE stream is 16-row bands, u16 band length, 0xFF-continuation runs of
# alternating colour (rung S8, re-derived and closed 8/8 on live payloads).
# Building one by hand is the single most likely way for this arm to fail for a
# reason that has nothing to do with the opcodes, so it replays a REAL pair
# instead: capture 20260807T143055, connection :64102, the largest of the eight.
# Its declared byteCount is 38 and its band chain closes at EXACTLY 38 --
# lengths (0, 22, 0, 0, 0, 0, 0, 0) over 128/16 = 8 bands -- which is the same
# arithmetic S8 used and is re-checked in test_fogrle.py §1 rather than trusted.
# (This line named "test_probes.py" from 2026-08-15 to 2026-08-24; no such file
# was ever written, and the check it promised first existed when fogrle landed.)
# Only the two trailing 0xCCCC padding dwords beyond the declared count are ours
# to ignore; everything inside the count is verbatim ArenaNet.
FOG_INIT_DIMS = (64, 128)                  # continent 1's block grid, 64 % 32 == 0
FOG_INIT_BYTES = 38
FOG_INIT_PAYLOAD = [1441792, 973218303, 956578308, 889600005, 939930889,
                    1006778885, 41474, 0, 0, 3435921408]

# The mark, in CONTINENT-ABSOLUTE blocks (footprint cells >> 5), not map-local.
# Map 148's footprint is (768, 512)-(1184, 1024) cells = blocks x 24..36,
# y 16..31, and the init pair declares a 64x128 grid, so (30, 24) is inside both
# and satisfies ChCliApi:201 `x + markSpanCount <= mapDims.x` (30 + 1 <= 64).
# Field 3 is the HALF-SPAN, so 1 reveals a 3x3 block window.
FOG_MARK = (30, 24, 1)

# ...AND THE ONE ABOVE IS A NO-OP, WHICH IS WHY THERE ARE TWO.
# The 2026-08-15 isolation run diffed init-only against init+mark and got a
# BYTE-IDENTICAL world map -- 0 pixels of 2,013,440. The mark was not refused:
# block (30, 24) was ALREADY SET by the replayed init payload, so writing it
# again changes nothing. Decoding that payload's band 1 (the only non-empty
# band, rows 16..31) settles it -- and the band chain consumes exactly its
# declared 38 bytes, independently reproducing rung S8.
#
# `FOG_MARK_UNSET` is a block the SAME decode says is CLEAR, inside map 148's
# footprint (blocks x 24..36, y 16..31) and beside revealed neighbours so a
# 3x3 reveal lands against known terrain rather than in empty space. 68 of the
# footprint's blocks are clear; this is one of them. Keeping both marks means
# the null and the positive are the same experiment with one coordinate
# changed, which is what makes the null interpretable.
FOG_MARK_UNSET = (26, 22, 1)


def _compass_draw_steps():
    ping = _knot(*_SPAWN_CELL)
    line = [_knot(_SPAWN_CELL[0] + dx, _SPAWN_CELL[1] + dy)
            for dx, dy in ((0, 0), (2, 0), (4, 1), (6, 2), (8, 2))]
    return [
        Step(3.0, 0x0091, [7, 1, [ping]],
             "0x0091 PING: knotCount=1, owner=7 (NON-zero), at the player's cell",
             "a red ping ripple ON THE COMPASS at the player's own position. "
             "knotCount==1 takes the ripple path at 0x008BE6B3 and needs no "
             "0x0092 at all. Owner is 7 rather than 0 on purpose: 0 is the "
             "LOCAL client's own tag, and a zero echo makes the client merge "
             "the broadcast into its own line."),
        Step(6.0, 0x0091, [7, 2, line],
             "0x0091 POLYLINE: knotCount=5, a short stroke beside the player",
             "a red line on the compass. CompassCanvas:1372 needs knotCount >= 2 "
             "to render a polyline, so this is the arm the ping cannot test."),
        Step(6.0, 0x008B, [FOG_INIT_DIMS[0], FOG_INIT_DIMS[1], FOG_INIT_BYTES],
             "0x008B fog INIT DECLARE (64 x 128 blocks, 38 bytes to follow)",
             "NOTHING, and that is the prediction rather than a caution: the "
             "init path posts no frame message at all, so no repaint is due "
             "until the mark lands."),
        Step(1.0, 0x008A, [FOG_INIT_PAYLOAD],
             "0x008A fog INIT PAYLOAD -- ArenaNet's own RLE, replayed verbatim",
             "still nothing visible. This allocates and fills mapBits; until it "
             "has run, 0x008C returns immediately at 0x00811BEE and measures "
             "nothing, which is why smsgsweep's 108 prior sends of 0x008C were "
             "inert."),
        Step(6.0, 0x008C, list(FOG_MARK),
             "0x008C fog MARK at continent block (30, 24), half-span 1",
             "THE REPAINT. This is the only message of the three that posts "
             "0x10000090, whose subscribers are Compass.cpp, GmMapWorld.cpp and "
             "GmMapWindow.cpp. Watch the COMPASS first, then press M: whether "
             "the compass GROUND IMAGE is fog-masked is an open question "
             "(CompassMarker tests the bits, CompassMap's blit does not, "
             "GmMapView does), so a change on the world map with none on the "
             "compass is a REAL result and not a failure."),
    ]


def _fog_pair_steps():
    """The init pair alone -- the NO-MARK half of C4's isolation arm."""
    return [
        Step(3.0, 0x008B, [FOG_INIT_DIMS[0], FOG_INIT_DIMS[1], FOG_INIT_BYTES],
             "0x008B fog INIT DECLARE (no mark will follow)",
             "nothing yet; the init posts no frame message."),
        Step(1.0, 0x008A, [FOG_INIT_PAYLOAD],
             "0x008A fog INIT PAYLOAD -- ArenaNet's own RLE, replayed verbatim",
             "still nothing on the compass. The world map should now OPEN "
             "rather than assert, which is the 6f.2 result; what it must NOT "
             "show is whatever the 0x008C mark adds."),
    ]


def _fog_mark_steps():
    """The same pair PLUS the mark. Identical timing, one extra message."""
    return _fog_pair_steps() + [
        Step(6.0, 0x008C, list(FOG_MARK),
             "0x008C fog MARK at continent block (30, 24), half-span 1",
             "the only difference from compass_fog_nomark. Any world-map pixel "
             "that differs between the two runs is THIS message's doing."),
    ]


# The quest probes' step builders, their constants and the vault-NPC row
# helpers moved WHOLE to `probequest.py` -- the quest log and compass marker
# arms, the 0x007E dialog options, the 0x009F property-11 marker band, the live
# givers' definitions, and the completion and reward arms. Re-exported here
# because `vars(probes)` is this module's public surface: NOTHING outside reads
# any of these forty-six names today (measured -- zero referrers in the tree,
# and the only monkeypatch sites anywhere are on `probes.get`), and dropping
# forty-six attributes nobody happens to read is a behaviour change no test in
# the suite would have caught. `PROBES` is deliberately NOT in this list; the
# quest registry entries are merged in where the `PROBES` literal closes below.
from probequest import (                                    # noqa: F401,E402
    DIALOG_OPTION, GENERIC_VALUE, GIVER_DEFINITION, OPTION_FIELD4_ALWAYS,
    OPTION_KIND_QUEST, PROP_QUEST_MARKER, PROP_QUEST_MARKER_CLEAR,
    QUEST_MARKER_ADVANCE, QUEST_MARKER_OFFER, QUEST_MARKER_TURN_IN,
    _ARENANET_OFFER_LINE, _ENC_ASCALON, _GIVER_AGENT, _MARKER_SWEEP,
    _OBJECTIVE_AGENT, _OBJECTIVE_DEFINITION, _QUEST_NAME_MAP, _REWARD_A,
    _REWARD_B, _REWARD_QUEST, _SPAWN_WORLD, _TEST_NPC_AGENT, _VAULT_NPC_CACHE,
    _compass_quest_steps, _completion_gate_steps, _completion_panel_steps,
    _completion_reward_steps, _dialog_icons_steps, _npc_dialog_steps,
    _objective_npc, _quest_description_steps, _quest_giver_def_steps,
    _quest_giver_mark_steps, _quest_marker_states_steps,
    _quest_marker_sweep_steps, _quest_name_authored_steps, _quest_name_steps,
    _quest_objective_steps, _quest_offer_steps, _quest_option_steps,
    _quest_panel_steps, _quest_reward_steps, _quest_turnin_steps, _vault_npc,
    _walk_to_npc_steps, giver_npc)


PROBES = {
    # The nineteen quest entries that stood HERE -- `quest_objective` through
    # `completion_gates` -- moved to `probequest.PROBES` with the step builders
    # they call, and are merged back into this dict where it closes below.
    "compass_fog_nomark": lambda a, o: Probe(
        question="PLAN C4 isolation, half 1 of 2: what does the fog INIT PAIR "
                 "alone reveal, with no 0x008C mark?",
        predicts="The world map OPENS rather than asserting (6f.2), and shows "
                 "whatever ArenaNet's own replayed payload encodes -- which is "
                 "most of what 6f.2's screenshot showed. This run exists to "
                 "prove that, so that the mark's own contribution can be "
                 "measured as a DIFFERENCE rather than assumed from a single "
                 "picture that contained both.",
        steps=_fog_pair_steps(),
        note="Run this and compass_fog_mark back to back with identical flags, "
             "then diff the two world-map frames. 6f.4 records that C4's first "
             "pass could not separate them because one run sent both.",
    ),
    "compass_fog_mark": lambda a, o: Probe(
        question="PLAN C4 isolation, half 2 of 2: what does the 0x008C MARK add "
                 "on top of the init pair?",
        predicts="A 3x3-block patch revealed at continent block (30, 24) that "
                 "compass_fog_nomark does not have. If the two world maps are "
                 "pixel-identical, the mark did nothing -- and the per-map "
                 "explorable mask from Engine\\Map\\Map.cpp, which nothing has "
                 "read, is the first suspect rather than the opcode.",
        steps=_fog_mark_steps(),
        note="Identical to compass_fog_nomark except for the trailing 0x008C, "
             "so the world-map difference is attributable to one message.",
    ),
    "compass_fog_mark_unset": lambda a, o: Probe(
        question="PLAN C4 isolation, the RETRY: does 0x008C reveal a block the "
                 "init payload left CLEAR?",
        predicts="A 3x3 patch appears on the world map at continent block "
                 "(26, 22) that compass_fog_nomark does not have. The first "
                 "attempt marked (30, 24), which decoding the payload shows was "
                 "ALREADY SET -- so its byte-identical result measured nothing "
                 "about the opcode. If THIS one is also identical, the mark is "
                 "genuinely inert and the per-map explorable mask "
                 "(0x0070A120 -> 0x00721D00, unread) is the first suspect.",
        steps=_fog_pair_steps() + [
            Step(6.0, 0x008C, list(FOG_MARK_UNSET),
                 "0x008C fog MARK at continent block (26, 22) -- a CLEAR block",
                 "the world map, diffed against compass_fog_nomark. This is the "
                 "same experiment as compass_fog_mark with one coordinate "
                 "changed, which is what makes either outcome interpretable."),
        ],
        note="Diff against compass_fog_nomark, not against compass_fog_mark.",
    ),
    # `compass_quest` stood HERE, between the two fog arms it is the marker
    # control for. It moved to `probequest.PROBES` with `_compass_quest_steps`.
    "compass_draw": lambda a, o: Probe(
        question="PLAN C4. Does the compass draw/ping pair render from the wire, "
                 "and can the three-message fog sequence unfog a block on our "
                 "own server?",
        predicts="THE PING AND THE POLYLINE RENDER. Both ends of the draw pair "
                 "are named from the client's own asserts and the handler's "
                 "unpack loop is the exact inverse of the sender's pack, so a "
                 "well-formed 0x0091 beside the player should draw. A null "
                 "there would mean the broadcast needs party state we do not "
                 "have. THE FOG SEQUENCE IS THE HARD ARM and its first two "
                 "steps are predicted to show NOTHING -- the init posts no "
                 "frame message -- with the repaint arriving only on the "
                 "0x008C. Two things can defeat it for reasons unrelated to the "
                 "opcodes, both named in advance: 0x008C's bit writes are gated "
                 "by a per-map explorable mask from Engine\\Map\\Map.cpp that "
                 "nothing in this repo has read, and if the compass ground is "
                 "not fog-masked the reveal is visible only on the world map.",
        steps=_compass_draw_steps(),
        note="RUN ON MAP 148 (the default) -- every coordinate here is computed "
             "for it and is wrong anywhere else: the knots are absolute world "
             "units/96 around ITS spawn, and the mark is in continent-1 blocks "
             "inside ITS footprint. The fog init pair is ArenaNet's own bytes "
             "replayed verbatim rather than a payload we built, because a "
             "hand-rolled RLE stream failing would look exactly like the client "
             "refusing the opcode. Give the run --keep-open and enough hold to "
             "see all five steps, and press M after the last one.",
    ),
    "smsgsweep": lambda a, o: Probe(
        question="Of the GAME_SMSG opcodes ArenaNet has never sent us, which ones does "
                 "the client visibly act on -- and which of those answer back?",
        predicts="EVERY planned opcode reaches a handler: all 477 receive-table entries "
                 "carry a non-null dispatch pointer (msghandler.py --classify), so a "
                 "silent row is a fact about the all-zero payload or the readout, NEVER "
                 "about reachability. Most will be silent for exactly that reason -- a "
                 "handler that early-outs on a zero id looks identical to one that does "
                 "nothing. The result worth having is a REPLY: the client sending a c2s "
                 "message names the request a panel makes, which is the binding a live "
                 "session would otherwise have to go and discover. A channel teardown is "
                 "also a result -- but it is NOT a crash until the session report's "
                 "endpoint table says the client stopped: 0x000B tore the game channel "
                 "down in the pilot and the client was alive on a loading screen 42 s "
                 "later, with no assert in Gw.log and no fatal-error dialog.",
        steps=_smsgsweep_steps(a, o),
        note="NEEDS A PLAN: run `smsgsweep.py --plan` first, or this probe sends "
             "nothing and the run measures nothing -- it says so as a step marked "
             "`sends=False`, which carries the warning to the operator without "
             "having to survive the codec. "
             "Loopback only -- both endpoints ours, ours-DH client, cage verified. "
             "Score with `smsgsweep.py --from-report <the run's report.json> --record`. "
             "Attribution is by opcode identity, against this run's OWN control window "
             "-- the quiet seconds before the first send -- and not by timing."),
    # The `agent_removal` entry stood HERE, between `smsgsweep` and `burrow`.
    # It moved to `probeunitsetup.PROBES` with `_agent_removal_steps`, and is
    # merged back into this dict where it closes below.
    # The two entries that stood HERE -- `cast_modifier_order` and
    # `pool_fraction` -- moved to `probeskills.PROBES` with the step builders
    # they call, and are merged back into this dict where it closes below.
    "burrow": lambda a, o: Probe(
        question="Does an NPC definition survive WORLD_REMOVE_AGENT, and does the "
                 "0x1000 effect bit do anything the player can see?",
        predicts="Steps 3 AND 4 both draw a correct-looking collector, because "
                 "ArenaNet sends one 0x0056 for 140 re-creates of the same worm and "
                 "the only reading of that is a definition table which outlives the "
                 "agents using it. If BOTH fail, definitions are bound to their agent "
                 "and our burrow must keep resending -- which is what it does today, "
                 "so a negative costs nothing but a resend. Steps 1-2: no prediction "
                 "worth the name. The bit's TIMING is measured (2.00 s each way, "
                 "n=132) and its EFFECT is unverified; the honest expectation is that "
                 "nothing visible happens, because a client that hid an agent on this "
                 "bit would not also need the removal ArenaNet sends 2.00 s later.",
        steps=_burrow_steps(a, o),
        note="RUN 2026-08-11, and BOTH re-creates drew a correct collector -- same id "
             "and fresh id, neither given a 0x0056/0x0057. A definition is per-INSTANCE; "
             "burrow_tick now passes send_definition=False (studies/enemy/PLAN.md 10.8, "
             "capture authsrv-20260811T135809). THE STEPS-1-2 PREDICTION WAS REFUTED and "
             "that is the better half: 0x1000 is an ANIMATION, not bookkeeping. Set it "
             "and the agent falls prone, clear it and it gets up; it stays rendered and "
             "keeps its nameplate throughout. The reasoning behind 'nothing visible "
             "happens' -- that a client hiding an agent on this bit would not need the "
             "removal 2.00 s later -- was sound, and the answer is that the bit animates "
             "while the REMOVAL hides. Re-running is still useful; the note below stands. "
             "Do NOT add the clean negative control (an agent citing a "
             "definition never sent) -- that is the `index < m_count` client assert "
             "npc_properties warns about, and crashing the client to confirm it "
             "crashes is not worth a run. TARGET THE HOSTILE BEFORE STEP 1 and keep "
             "watching the target frame through step 3. Grounded on "
             "vault/captures/live/20260807T143055 conn :64103, where 140 worm "
             "re-creations are one five-message burst with no exceptions "
             "(toolkit/authsrv/test_burrow.py re-measures it every run).",
    ),
    "prop66_sweep": lambda a, o: Probe(
        question="What is agent property 66, the one id past the end of "
                 "OpenTyria's enum that no source anywhere names?",
        predicts="Uncertain by construction, which is the point -- static "
                 "analysis bounded this one and could not name it. Something "
                 "visible should change for at least one value, because the "
                 "byte is stored per agent even for agents with no AgentView "
                 "object yet, which is what an appearance attribute looks like. "
                 "If nothing changes at any value, 66 needs a character rebuild "
                 "the 65 toggle does not trigger.",
        steps=_prop66_sweep_steps(a),
        note="MEASURED (section 16.4): 66 writes ONE BYTE to AvChar+0x113 and "
             "to +7 of the record at AvChar+0x108, where property 65 -- "
             "OpenTyria's PvPTeam -- writes +5. Anything above bit 7 of the "
             "value is discarded silently. UNRUN. The 65 toggles are there "
             "because 66's setter calls no refresh and 65's does; step 1 "
             "establishes what a bare toggle does so it can be discounted.",
    ),
    # The five entries that stood HERE -- `effect_silent_extend` through
    # `lone_p17` -- moved to `probeskills.PROBES` the same way.
    "coded_chat": lambda a, o: Probe(
        question="Does OUR encode of coded-string numeric args render -- same "
                 "template, our numbers -- and does the multi-word varint "
                 "path work in the send direction?",
        predicts="Step 1 renders ArenaNet's level-up line with 13/51/1/17; "
                 "step 2 renders the SAME line with 42/7/3/99 in the same "
                 "roles; step 3 renders 40000 via the two-word varint; step "
                 "4 draws the Isle's own map name over the hostile's head. "
                 "Any step that instead logs 'Invalid coded string received "
                 "from server' in Gw.log names exactly which encoding rule "
                 "we hold wrong -- which is worth more than a render.",
        steps=_coded_chat_steps(a),
        note="Isle rung 4, and rung 7 waits on step 2: the Master of Damage "
             "plan reads DPS numbers out of exactly this format "
             "(studies/isle/FINDINGS.md B8 -- decode direction measured on "
             "50 live 0x5D messages, send direction never exercised). CHECK "
             "GW.LOG AFTERWARD either way. "
             "RUN 2026-08-16/17, operator watching, three sessions. Bare 0x5D "
             "renders NOTHING and is silently held -- the 0x5E channel tag is "
             "REQUIRED (paired verbatim, the control rendered). The control "
             "drew the level-up line with its numeric arg IN THE CLEAR ('is "
             "now level 17!'), so the announcement-number path rung 7 needs "
             "is proven on a real render. BOTH our-arg variants were refused "
             "('Invalid coded string' x2): arg value 7 encodes to 0x107, "
             "which is the LITERAL-RUN MARKER record -- the biased-varint "
             "range contains control ids and 7 collides. The varint rule "
             "itself is therefore STILL UNEXERCISED. And step 7's 0x5F with "
             "a bare non-chat sid CRASHED the client -- c0000005, null read "
             "-- so 0x5F is never to be sent with an arbitrary record; the "
             "overhead half of the oracle stays unproven. Next iteration: "
             "args avoiding 0x100-0x1FF control ids, and no 0x5F.",
    ),
    "encname_render": lambda a, o: Probe(
        question="Does a CAPTURED enc_name tuple render as a readable "
                 "nameplate on our client -- the route rung 6's roster "
                 "naming depends on?",
        predicts="The body 150u out wears a readable name (and an Ascalon "
                 "City-ish human model) -- def_1470 is the byte-identical "
                 "cross-session station agentroster.py pins. A blank or "
                 "garbled plate refutes the naming route and rung 6 falls "
                 "back to marks ordinals.",
        steps=_encname_render_steps(o),
        note="Isle rung 4, the Hatcher precedent re-run on a roster row. "
             "HOLD CTRL and read the plate out loud; the string the client "
             "resolves from its own archive is the measurement, and it "
             "never enters the repo -- the ids already have. "
             "RUN 2026-08-16, operator-confirmed: the body spawned, wore the "
             "outfitter/merchant model (pack and all -- the operator matched "
             "it to Gelsan the Outfitter's family on the wiki), carried a "
             "readable red 'Outfitter' plate, and despawned clean. The "
             "captured-tuple -> nameplate route is PROVEN, and the "
             "agentroster station (slot 1470, model 116698, map 148, pos "
             "8436,4819) is NAMED: the Ascalon City outfitter.",
    ),
    # The twelve entries that stood HERE -- `buff_type_field` through
    # `unlock_211` -- moved to `probeskills.PROBES` the same way. That run is
    # where `use_skill_capture` sits: it builds no steps (`steps=[]`) and moved
    # with the skill arms it is read beside.
    # The thirty-eight entries that stood HERE -- `health_max` through
    # `allegiance_split` -- moved with the step builders they call: seven to
    # `probeunitsetup.PROBES`, twenty-one to `probecharacter.PROBES` and ten to
    # `probecombat.PROBES`. All three are merged back into this dict where it
    # closes below.
    # The six merchant entries that stood HERE -- `gold_purse` through
    # `accum_drains` -- moved to `probemerchant.PROBES` with the step
    # builders they call, and are merged back into this dict where it
    # closes below.
    # The three entries that stood HERE -- `npc_agent`, `die_0x2d` and
    # `allegiance` -- moved to `probecombat.PROBES` the same way.
    "spawn": lambda a, o: Probe(
        question="Does the character still spawn correctly with team token 'play'?",
        predicts="Identical behaviour to 0xBAADF00D. A regression here means the "
                 "three-lineage value is wrong for this build and we revert.",
        steps=_team_token_steps(a),
        note="No extra packets: the change is already in the spawn burst. Just "
             "confirm the character appears and moves as before.",
    ),
}


# The twenty quest entries cut from the two sites above, merged back in.
# `probes.PROBES` is what `get`, `names`, `describe` and `check_encodable` read
# and it must answer for the whole family: the split decides where the code
# lives, not what the registry holds. `names()` is still `sorted(PROBES)`, so
# neither it nor `check_encodable`'s print order changes.
#
# THE DUPLICATE-KEY RAISE IS NOT NEW CAUTION -- it restores a property the split
# removed. Two entries with the same name inside ONE dict literal were a
# review-visible adjacency and the second silently won; across two files nothing
# shows it at all, and a probe run would fire the wrong sequence under the right
# name.
import probequest                                           # noqa: E402

if set(PROBES) & set(probequest.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probequest.PROBES))}")
PROBES.update(probequest.PROBES)


# And the six merchant entries, cut from the ONE site above -- they stood
# contiguously, where the quest entries came from two -- merged the same way
# and for the same reasons. The check runs AFTER the quest merge, so it
# also rules on a name defined in BOTH siblings rather than only on a clash
# with what is left in this file.
import probemerchant                                        # noqa: E402

if set(PROBES) & set(probemerchant.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probemerchant.PROBES))}")
PROBES.update(probemerchant.PROBES)


# And the nineteen skill entries, cut from the THREE sites above, merged the
# same way and for the same reasons. The check runs after both earlier merges,
# so it also rules on a name defined in any two of the three siblings rather
# than only on a clash with what is left in this file.
import probeskills                                          # noqa: E402

if set(PROBES) & set(probeskills.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probeskills.PROBES))}")
PROBES.update(probeskills.PROBES)


# And the eight unit-setup entries, cut from the TWO sites above -- the
# agent-removal arm stood among the sweeps, the other seven in the long run that
# starts at `health_max` -- merged the same way and for the same reasons. The
# check runs after the three earlier merges, so it also rules on a name defined
# in any two of the four siblings merged so far.
import probeunitsetup                                       # noqa: E402

if set(PROBES) & set(probeunitsetup.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probeunitsetup.PROBES))}")
PROBES.update(probeunitsetup.PROBES)


# And the twenty-one character entries, cut from the ONE run above, merged the
# same way and for the same reasons.
import probecharacter                                       # noqa: E402

if set(PROBES) & set(probecharacter.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probecharacter.PROBES))}")
PROBES.update(probecharacter.PROBES)


# And the thirteen combat entries, cut from the TWO sites above, merged the same
# way and for the same reasons. With this the registry is whole again: TEN
# entries are defined in this file and eighty-seven across the six siblings,
# which is the ninety-seven `probes.PROBES` held before the split, in the same
# sorted order and with the same steps behind every one of them.
import probecombat                                          # noqa: E402

if set(PROBES) & set(probecombat.PROBES):
    raise RuntimeError("probe name defined in two modules: "
                       f"{sorted(set(PROBES) & set(probecombat.PROBES))}")
PROBES.update(probecombat.PROBES)


# Where the character stands when a probe fires, as (x, y, plane).
#
# Only used by probes that place something in the world, and only meaningful
# because a probe fires seconds after the spawn burst, before anyone has walked
# anywhere. The default is Kamadan's spawn point -- the map every session
# actually loads, via MAP_STATIC_CONFIG's fallback -- so that --list-probes and
# the encode self-test work with no server running. A live run passes the real
# one.
DEFAULT_ORIGIN = (-9067.0, 13218.0, 0)


def get(name, agent_id, origin=None):
    factory = PROBES.get(name)
    if factory is None:
        return None
    return factory(agent_id, origin or DEFAULT_ORIGIN)


def names():
    return sorted(PROBES)


def check_encodable(quiet=False, counts=None):
    """Encode every step of every probe. Run this before spending a client run.

    A probe that fails to encode wastes a whole session -- the client has to be
    launched, logged in and walked into a map before the first packet fires, and
    the failure would not surface until then.

    `quiet` suppresses the per-step lines so the suite can call this as one
    check. It was reachable only from `__main__` until 2026-08-12, which meant
    the guard against wasting a client run was itself never run by the suite.

    A PROBE THAT CANNOT BE BUILT HERE IS SKIPPED, NOT FAILED, and that is a
    different thing from a step that will not encode. Some probes bind vault
    content when their steps are built -- `_dialog_icons_steps` reaches
    `giver_npc()` -> `_vault_npc("def_1480")`, the row `test_bareimport.py` was
    written about -- so on a machine with no overlay the BUILD raises before any
    encoding happens. Until 2026-08-31 that escaped this function entirely
    (`get()` sat outside the try below), which is one of the two things that
    stopped `test_agentlife.py` reaching a verdict without a vault. Counting it
    as a failure would be worse than crashing: it would report the probe as
    broken when the machine is merely bare.

    Pass a dict as `counts` to learn what actually happened -- it is filled with
    `checked` / `skipped` / `failed`. The return value is still the failure count
    alone, because four call sites in `test_agentlife.py` compare it to 0 and
    two of those are sabotage arms. **A caller that only reads the return value
    cannot tell "every probe encodes" from "no probe could be built":** both are
    0. That is exactly the `test_codec.py` fixture-glob shape, so a caller on a
    machine that might be bare should assert `counts["checked"] > 0` too.
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "schema"))
    from codec import Codec

    codec = Codec()
    bad = 0
    checked = 0
    skipped = []
    for name in names():
        try:
            probe = get(name, 1)
        except Exception as exc:                               # noqa: BLE001
            # Building the steps needs something this machine does not have --
            # a vault content row, in every case seen so far. NAMED, never
            # silent, and never counted as a broken probe.
            skipped.append((name, f"{type(exc).__name__}: {exc}"))
            if not quiet:
                print(f"  [SKIP] {name}: cannot be built here -- "
                      f"{type(exc).__name__}: {exc}")
            continue
        if not probe.steps:
            if not quiet:
                print(f"  [ -- ] {name}: no packets, observation only")
            continue
        for step in probe.steps:
            if not getattr(step, "sends", True):
                # A declared refusal. It carries a message and no packet, so there is
                # nothing to encode and an encode attempt reports it as a broken probe
                # -- which is what happened on 2026-08-13 when the all-zero sweep
                # finished and the plan emptied. See Step's docstring for why this is a
                # flag and not an `if not step.values` test.
                if not quiet:
                    print(f"  [ -- ] {name}: {step.label} -> refusal, sends nothing")
                continue
            try:
                blob = codec.encode("GAME_SMSG", step.opcode, step.values)
                checked += 1
                if not quiet:
                    print(f"  [PASS] {name}: {step.label} -> "
                          f"0x{step.opcode:04X}, {len(blob)}B")
            except Exception as exc:
                bad += 1
                print(f"  [FAIL] {name}: {step.label} -> "
                      f"{type(exc).__name__}: {exc}")
    if counts is not None:
        counts["checked"] = checked
        counts["skipped"] = skipped
        counts["failed"] = bad
    return bad


def describe(name):
    p = get(name, 1)
    if p is None:
        return f"no probe named {name!r}"
    out = [f"  {name}", f"    Q: {p.question}", f"    predicts: {p.predicts}"]
    if p.note:
        out.append(f"    note: {p.note}")
    for i, s in enumerate(p.steps, 1):
        out.append(f"    {i}. +{s.delay:.0f}s  {s.label}")
    if not p.steps:
        out.append("    (no packets -- observation only)")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    print("Encoding every probe step against the live schema.\n")
    failures = check_encodable()
    print("\n" + ("ALL PROBES ENCODE" if not failures
                  else f"{failures} STEP(S) FAILED TO ENCODE"))
    sys.exit(1 if failures else 0)
