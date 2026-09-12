"""Quest log, markers, dialog options, NPC interaction, completion and rewards.

The quest arm of the probe family, lifted verbatim from `probes.py` on
2026-09-11: the step builders for the quest log and the compass marker, the
0x007E dialog-option constants, the 0x009F property-11 marker band, the two
live-giver definitions the probes replay, the completion and reward arms, and
the twenty registry entries that fire them.

It is leaf shaped by the same rule `probebase.py` is -- standard library plus
`agents`, `probebase` and `questdefs` -- and it MUST NOT import `probes`:
`probes.py` runs as `__main__` under `python toolkit/authsrv/probes.py`, so a
leaf importing it back would load a SECOND copy of that module, with its own
`PROBES` dict and its own flags.

`import questdefs` is DUPLICATED here rather than moved. `probes.py` still owns
`_title_track_steps`, which calls `questdefs.coded_literal` four times, so the
import stays there too until that builder leaves in its own lane. The failure
mode of getting this wrong is silent: `check_encodable` wraps `get()` in
`except Exception`, so a `NameError` for `questdefs` would be reported as a
printed SKIP and every `failures == 0` assertion in `test_agentlife.py` would
stay green.

WHERE THE REFERENTS WENT. `check_encodable`'s docstring is the one comment that
points INTO this file from outside it: it names `_dialog_icons_steps` reaching
`giver_npc()` -> `_vault_npc("def_1480")` as the probe whose steps bind vault
content at build time. That docstring stays in `probes.py` beside the function
it documents and is not reworded; this paragraph is the pointer. `_vault_npc`'s
own docstring says "made EVERY importer of this file die" -- "this file" was
`probes.py` when it was written and is this one now, and the sentence is true of
both, because `probes.py` imports this module.

`PROBES` here holds only the quest entries. `probes.py` opens its own dict,
merges this one in with a duplicate-key raise, and keeps `get`, `names`,
`describe` and `check_encodable` -- so `probes.get("quest_panel", ...)` answers
exactly as it did, and `names()` is still `sorted(PROBES)` and still returns the
same 97 names in the same order. Every name this module binds except `PROBES` is
also re-exported by `probes.py`, at the site it was cut from, so `vars(probes)`
still answers for all of them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import questdefs                                            # noqa: E402
from agents import (                                        # noqa: E402
    AGENT_KIND_NPC, CHAR_CLASS_MONSTER_BASE,
    create_agent, npc_model, npc_properties, npc_template)
from probebase import Probe, Step                           # noqa: E402


# QUEST MARKER AND THE NULL CONTROL (PLAN C4's two untouched arms).
# 0x0049's vec2 is in ABSOLUTE WORLD UNITS -- unlike the compass knots, which
# are world/96 -- so it takes the spawn coordinate verbatim from
# content/maps.toml rather than the cell pair the draw arm uses. Getting that
# wrong would put the marker 96x too far out and read as "nothing drew".
_SPAWN_WORLD = (9826.0, 8077.0)

# ONE code unit, 0x3D64 -- the WIRE WORD, not the archive string id. textrec
# takes the id, which is 0x3D64 - 0x100 = 15460 and resolves to 'Ascalon'; the
# two differ by exactly the coded-string bias, and conflating them is the trap
# studies/quests/FINDINGS.md 3.5 names (15716 resolves to None). Built with
# chr() rather than a literal glyph because that is the sender form 3.5
# documents -- codec.py takes a str, not a list of code units -- and because a
# CJK character in a source literal does not survive every editor intact.
_ENC_ASCALON = chr(0x3D64)


def _compass_quest_steps():
    return [
        Step(3.0, 0x008D, [1, _SPAWN_WORLD, 0, 0, 0, 0, ""],
             "0x008D indexed marker record -- THE NULL CONTROL",
             "NOTHING, predicted before the run. 0x008D writes a 40-byte record "
             "into charContext+0x7EC and posts 0x10000091, so it is not inert "
             "in the client -- the prediction is that it is a static catalogue "
             "entry with no compass glyph of its own. If something DOES draw "
             "here, the null control is the finding and 0x0049's arm below is "
             "confounded by it."),
        Step(8.0, 0x0049, [1, _SPAWN_WORLD, 0, 148, 32,
                           _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, 148],
             "0x0049 QUEST_ADD carrying ArenaNet's own string id 0x3D64 in all "
             "three slots, with plane/flags/home_map moved inside ArenaNet's "
             "observed distribution",
             "THE QUEST LOG READS 'Ascalon' RATHER THAN '?'. 0x3D64 is the word "
             "ArenaNet itself puts in slot 0 of every quest add in the live "
             "corpus (10 of 10); textrec.py resolves it as string id 15460 -> "
             "'Ascalon', a PLAIN record needing no key, while the rival "
             "raw-word reading gives 15716 -> None. One literal therefore tests "
             "the whole chain -- wire code unit, the client's own id->text seam "
             "at 0x007C93F0, rendered glyph. A '?' or a blank means our coded "
             "string is wrong ON THE WIRE even though it re-encodes "
             "byte-identically offline (66 of 66 against ArenaNet's own words), "
             "and every authored string downstream is suspect.\n"
             "SECOND ARM, a free rider on the same run: 6f.5 recorded 'no "
             "compass starburst' as NOT FOUND, but the run that produced it "
             "sent plane=148 and home_map=0 -- values ArenaNet NEVER sends "
             "(observed n=10: plane in {0,26}, home_map in {146,148}, flags=32 "
             "in 8 of 10). Corrected here. If a starburst now draws, 6f.5's "
             "NOT FOUND was a malformed probe rather than an unknown protocol, "
             "and CompassQuestEffect.cpp does not need disassembling."),
    ]


# Q0 from studies/quests/AUTHORING.md, isolated from the compass question.
#
# WHY THIS IS A SEPARATE PROBE RATHER THAN A FLAG ON compass_quest. That probe
# is a MARKER experiment on map 148 and its vec2 is that map's spawn in
# absolute world units -- its own note says MAP 148 ONLY, and changing its
# coordinates would silently invalidate the 6f.5 result it is the control for.
# Map 148 is unrunnable today for a reason that has nothing to do with quests:
# contentids.py refuses the launch because no client archive in the vault binds
# 0x1B97D the way the server's does -- four run dirs hold it only under the
# bit-31 mid-replacement spelling, and the 38833 copy binds it to a rewritten
# file 8 bytes larger than the server's.
#
# So this probe asks the ONE Q0 question that does not need map 148 -- does a
# string id WE choose come back as rendered text -- and it takes its position
# from the LIVE origin, so the payload is coherent on whatever map loads. What
# it deliberately does NOT measure is the compass starburst: that needs 148's
# own coordinates, and answering it here would be answering a question this
# run cannot ask.
_QUEST_NAME_MAP = 449          # Kamadan -- both archives agree on it today


def _quest_name_steps(origin):
    x, y, plane = origin
    return [
        Step(8.0, 0x0049,
             [1, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, _QUEST_NAME_MAP],
             "0x0049 QUEST_ADD carrying string id 0x3D64 in all three string "
             "slots, at the live map's own spawn",
             "THE QUEST TRACKER READS 'Ascalon' RATHER THAN '?'. The run that "
             "produced 6f.5's '?' sent three EMPTY strings deliberately, "
             "because the marker was what was under test. This sends the one "
             "word ArenaNet itself puts in slot 0 of every quest add in the "
             "live corpus (10 of 10). textrec.py resolves 0x3D64 as string id "
             "15460 -> 'Ascalon', a PLAIN record needing no key; the rival "
             "raw-word reading gives 15716 -> None. One literal therefore "
             "tests the whole chain -- our wire code unit, the client's own "
             "id->text seam at 0x007C93F0, a rendered glyph. A '?' or a blank "
             "means our coded-string construction is wrong ON THE WIRE even "
             "though it re-encodes byte-identically offline against "
             "ArenaNet's own words (66 of 66), and every authored string "
             "downstream is suspect."),
    ]


def _completion_gate_steps():
    """The 0x0096/0x0097 ladder: which field feeds the completion-flag gate,
    and what the simple-reward triple renders.

    Both bodies are READ (FINDINGS.md 9.7 follow-up, disassembled 2026-08-19):
    0x0096 normalizes f1 and f2 into two independent 2-bit masks, builds a
    tagged record {4, f3, f5, f4} -- tag 4 is GmQuestComplete's own
    isSimpleReward tag -- skipped when f3 == f5 == 0, and posts frame
    0x10000158. THE HANDLER NEVER ASSERTS: the 2026-08-12 sweep's "at least
    one of two mission-completion flag bits" death on all-zero lives in the
    SUBSCRIBER, so which mask the gate reads is exactly what the arm order
    below can settle even if a crash ends the run early. 0x0097 pairs its
    string with two STASHED context values ([edi+0x5C]/[edi+0x64]) that some
    earlier message deposits, posts frame 0x10000157, then frees and zeroes
    the stash -- a cold fire posts over a null stash, so its arm goes LAST,
    crash-accepted, the assert being the answer.

    Every value is an invented sentinel (the family is 0 of 22,524); the
    111/222/333 triple follows quest_panel's precedent -- if the panel
    renders a reward line, the numbers name their own fields.
    """
    return [
        Step(12.0, 0x0096, [1, 0, 0, 0, 0],
             "f1 = bit0, everything else zero",
             "no assert is the first answer (the gate is satisfied by f1);"
             " a crash here says the gate reads f2 or needs the reward."),
        Step(15.0, 0x0096, [2, 0, 0, 0, 0],
             "f1 = bit1",
             "same gate, other bit -- two survivals mean either bit of f1 "
             "suffices."),
        Step(15.0, 0x0096, [0, 1, 0, 0, 0],
             "f2 = bit0, f1 zero",
             "the discriminator: surviving BOTH this and arm 1 means either "
             "mask satisfies the gate; dying here after arm 1 survived pins "
             "the gate to f1."),
        Step(15.0, 0x0096, [1, 0, 111, 222, 333],
             "f1 set plus the simple-reward triple as sentinels",
             "a reward line rendering 111/222/333 names f3/f4/f5 the way the "
             "quest_panel run named 0x004E's dwords. The record built is "
             "{tag 4, f3, f5, f4} -- note f5 rides the MIDDLE slot."),
        Step(15.0, 0x0097,
             [1, questdefs.coded_literal("Rurik", "template", limit=127)],
             "0x0097 cold: u8 = 1, a plain authored literal in the string",
             "LAST ON PURPOSE: the handler posts over a null stash and the "
             "sweep's closed-enum assert may fire regardless of our u8. A "
             "render is a result; an assert NAMING the gate is also a "
             "result; the run ends either way."),
    ]


def _completion_reward_steps():
    """The two arms 20260819T094757 could not measure: the crash at arm 3
    (GmQuestComplete.cpp:729, the completionFlagsGained gate -- the ladder's
    own answer) froze the client before the reward-triple and 0x0097 arms
    landed, so they were sent into a modal dialog and measured nothing. Same
    values, crash-proof order: the known-safe flag bit rides along.
    """
    return [
        Step(12.0, 0x0096, [1, 0, 111, 222, 333],
             "f1 = mission bit plus the simple-reward triple as sentinels",
             "the scene plus a REWARD LINE reading 111/222/333 -- a rendered "
             "number names its field, quest_panel's precedent. The record "
             "the handler builds is {tag 4, f3, f5, f4}: f5 rides the middle "
             "slot, so watch the ORDER of the rendered numbers."),
        Step(20.0, 0x0097,
             [1, questdefs.coded_literal("Rurik", "template", limit=127)],
             "0x0097 cold: u8 = 1, a plain authored literal in the string",
             "LAST ON PURPOSE: the handler posts over a null stash and the "
             "sweep's closed-enum assert may fire regardless of our u8. A "
             "render is a result; an assert NAMING the gate is also a "
             "result; the run ends either way."),
    ]


def _walk_to_npc_steps(origin):
    """Does 0x002A actually move the client, and does the held interact fire?

    THE VARIABLE IS THE ORDER, AND NOTHING ELSE. The NPC is placed 900 units
    out -- far past INTERACT_RANGE (250) and far enough that a walk takes a
    visible ~2.3 s at 288 u/s -- and then this probe stops sending. The
    interact is driven off the wire by `toolkit/harness/control.py`
    request_interact, so no click and no keystroke is involved and nothing here
    aims at anything: the whole readout is the server's own log plus the
    client's position reports.

    WHAT WOULD FALSIFY IT. `_handle_interact` orders the walk and holds the
    request; if the client ignores 0x002A the position reports never change,
    the held interact never arrives, and the gamesrv log simply never prints
    "ARRIVES" -- which refutes the fix without ambiguity, because the previous
    behaviour (drop it and print nothing) and the new one differ in exactly
    that line. If instead the client walks and the dialog opens on arrival,
    both halves are shown at once: 0x002A is the auto-walk order, and holding
    the interact is what makes arriving on foot mean something.

    Note the probe sends NO 0x0080/0x0081 of its own -- the dialog that appears
    must be the one the held interact produced, not one this list staged.
    """
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 900, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}) at +900u",
             "a body with a nameplate, 900 units away -- well past the "
             "250-unit interact range, and far enough that the walk itself "
             "takes about 2.3 s at run speed."),
        Step(4.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} -- the green '!'",
             "the marker, so the body reads as a giver rather than scenery."),
        Step(3.0, 0x0000, [], "NOW DRIVE THE INTERACT OFF THE WIRE",
             "run, in another terminal: python -c \"import sys; "
             "sys.path.insert(0,'toolkit'); from harness import control; "
             f"control.request_interact({_GIVER_AGENT})\" -- then WATCH THE "
             "GAMESRV LOG. Expect, in order: 'walking the player over and "
             "HOLDING the interact (~2.3 s at run speed)', the character "
             "actually running to the NPC on screen, and then 'held INTERACT "
             f"for agent {_GIVER_AGENT} ARRIVES -- answering it now' followed "
             "by the dialog window opening. No 'ARRIVES' line means the "
             "client ignored 0x002A and the fix is refuted.", sends=False),
    ]


def _completion_panel_steps():
    """0x0098 stages reward lines, 0x0097 consumes them -- and the gate that
    killed the first cold fire was THE MAP, not the payload.

    SELF-CORRECTION. FINDINGS 9.8 read 20260819T095219's crash
    (GmQuestComplete.cpp:678, "No valid case for switch variable") as an
    unstaged stash. Two independent static re-derivations say otherwise: the
    switch variable is loaded ONCE at 0x0052F935 as `[esi+4]` where esi =
    s_missionClientData[current_map_id] -- the CLIENT'S OWN per-mission table,
    indexed by the map the player is standing on -- and its valid cases are
    {2, 4, 5}. It never reads the posted record at all. That run was on the
    default map (world 1), which cannot satisfy it. Arm 1 below is the
    one-variable test of that correction: the SAME payload that crashed,
    on --map 449 (world 4).

    The stash is real, and now attributed: ctx[0x2c]+0x5C/+0x60/+0x64 is an
    ArenaNet Array<T> {data, capacity, count} (+0x68 is its growth chunk,
    written by the RTL grower as [ebx+0] and invisible to a --field scan --
    which is why 9.8 called +0x60 "a field nobody accounted for": it is the
    capacity). Its sole writer image-wide is GAME_SMSG 0x0098, whose body
    0x00812510 is an INLINED Array push/grow (element stride 0x20, four dwords
    written per push). 0x0097 reads count and data, posts them, frees the
    buffer and zeroes all three -- so each arm below re-primes from empty and
    the arms do not contaminate each other.

    Field d0 of 0x0098 is the reward TYPE tag, read by the consumer at
    0x0052F084 and compared against 4 (isSimpleReward) at 0x0052F089. Assert
    :246 is `!(isSimpleReward && rewardCount > 1)`, so an arm using d0 = 4
    must push exactly ONE element. Arm 3 respects that deliberately rather
    than discovering it the expensive way.
    """
    lit = questdefs.coded_literal("Rurik's own completion notes.",
                                  "template", limit=127)
    return [
        Step(12.0, 0x0097, [1, lit],
             "ARM 1, the correction's own test: the payload that crashed "
             "20260819T095219, unchanged, on a world-4 map",
             "NO :678 assert. Surviving proves the gate was the MAP and "
             "clears FINDINGS 9.8's stash reading. Crashing at :678 again "
             "refutes the correction and sends it back to the disassembly."),
        Step(18.0, 0x0098, [1, 111, 222, 333],
             "ARM 2a: push ONE reward element, type tag 1, sentinels",
             "nothing yet -- 0x0098 only appends to the array. A crash HERE "
             "would be new: no assert is known on the push path."),
        Step(6.0, 0x0097, [2, lit],
             "ARM 2b: consume it, medal 2",
             "the panel with a REWARD LINE reading 111/222/333, and the "
             "array count now 1 rather than 0. Which slot each sentinel "
             "lands in names d1/d2/d3."),
        Step(18.0, 0x0098, [4, 444, 555, 666],
             "ARM 3a: push ONE element with type tag 4 = isSimpleReward",
             "still nothing on screen. Exactly one push, deliberately: "
             ":246 asserts if isSimpleReward rides a count above 1."),
        Step(6.0, 0x0097, [3, lit],
             "ARM 3b: consume it, medal 3",
             "the SIMPLE-reward rendering of 444/555/666 -- compare against "
             "arm 2's type-1 rendering. A difference names what the type tag "
             "selects; identical output means d0 does not reach the render."),
    ]


def _quest_name_authored_steps(origin):
    """Q2b's screen half: does OUR OWN string render where Ascalon's did?

    quest_name (above) proved the id->text seam with ArenaNet's one corpus
    word, 0x3D64. This is the same experiment with the variable moved one
    step: the treatment's words come from the CONTENT ROW -- the two-word
    varint [0x8103, 0x0CC8] naming string id 100552, text file 98 record 200,
    written 2026-08-19 by textwrite.py --set into the reskin-roster archive.
    The control re-sends 0x3D64 first as the rig check, and 0x0049's
    last-pushed-becomes-active write (charContext+0x528, the trap HANDOFF
    warns about in replay) is exactly what makes an A/B possible in ONE run:
    the tracker follows the active quest, so it should read 'Ascalon' after
    the control and SWITCH to 'A First Errand' after the treatment.

    THE CLIENT IS PART OF THE EXPERIMENT: only an archive holding record 200
    can resolve 100552, and today that is vault/run/reskin-roster/ alone. Run
    against any other client and the treatment arm measures the wrong thing
    (a blank there would indict the archive, not the encoding).
    """
    x, y, plane = origin
    row = questdefs.load()[1463]
    nm = questdefs.enc_string(row.get("enc_name") or [])
    return [
        Step(8.0, 0x0049,
             [1, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, _QUEST_NAME_MAP],
             "CONTROL: quest 1 named with ArenaNet's 0x3D64, the Q0 word",
             "the tracker reads 'Ascalon' -- the rig check, quest_name's own "
             "result reproduced. Absent means the rig, not the record; stop "
             "reading here."),
        Step(20.0, 0x0049,
             [1463, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              nm, nm, nm, _QUEST_NAME_MAP],
             "TREATMENT: quest 1463 named from the content row -- our id "
             "100552 as the varint the row commits",
             "the tracker SWITCHES to 'A First Errand'. 'Ascalon' persisting "
             "= the add landed but the client kept the old active quest, or "
             "our words did not parse -- check the log for the 0x0049 before "
             "deciding which. Blank or '?' = the client could not resolve "
             "100552: wrong archive (this run MUST use the reskin-roster "
             "client) before wrong encoding."),
    ]


def _quest_description_steps(origin):
    """Q3: add two quests that differ ONLY in how their prose is framed.

    The server answers each GAME_CMSG 0x0012 from its content row, so the two
    0x004C bodies come back with `bare` and `template` framing respectively.
    Adding both in ONE run is what makes them comparable -- two runs would
    differ in session, camera and frame timing as well as in the variable.
    """
    x, y, plane = origin
    return [
        Step(6.0, 0x0049,
             [1463, (x, y), int(plane), _QUEST_NAME_MAP, 32,
              _ENC_ASCALON, _ENC_ASCALON, _ENC_ASCALON, _QUEST_NAME_MAP],
             "0x0049 QUEST_ADD for quest 1463, whose description our server "
             "will answer with TEMPLATE framing",
             "the interesting message is not this one -- it is the 0x0012 the "
             "client sends back within ~30 ms, and the 0x004C the server "
             "answers it with, built from content/quests.toml. OPEN THE QUEST "
             "LOG: the tracker shows the NAME (Q0 already proved that path), "
             "the DESCRIPTION PANE is what this probe is about."),
    ]


# The standing test NPC's agent id (content/world.toml, spawn.test_enemy). It is
# placed 300 units from the player's arrival point on whatever map loads, which
# is why this probe needs no per-map coordinates -- and why it needs --enemy,
# since the harness defaults a probe run to an empty world.
_TEST_NPC_AGENT = 10


def _npc_dialog_steps():
    """Q4: does the 0x0080/0x0081 pair open an NPC dialog window?

    Sends the pair UNSOLICITED rather than waiting for a click. The window is
    what is under test, and making it depend on the harness landing a mouse
    click on a body 300 units away would confound "the messages do not work"
    with "the click missed" -- two failures with one appearance.
    """
    line = questdefs.coded_literal(
        "Well met, traveller. This window is ours.",
        limit=questdefs.DIALOG_UNITS)
    return [
        Step(6.0, 0x0080, [line],
             "0x0080 NPC_DIALOG_TEXT -- one line into the accumulator",
             "NOTHING YET, predicted. 0x0080's body appends into a buffer at "
             "charContext+0x2C and posts no frame message, so a window here "
             "would refute the accumulator reading outright."),
        Step(10.0, 0x0081, [_TEST_NPC_AGENT],
             f"0x0081 NPC_DIALOG_SHOW -- flush, attributed to agent "
             f"{_TEST_NPC_AGENT}",
             "A DIALOG WINDOW OPENS carrying the line above, attributed to the "
             "standing NPC. 0x0081's body builds {1, agent_id, text_ptr} over "
             "that same buffer, posts UI frame 0x100000A6 -- whose ONE "
             "subscriber is at 0x004ECEAF -- and zeroes the count. If nothing "
             "opens, the pair is not the dialog mechanism and 2.5's naming is "
             "wrong; if a window opens but names the wrong speaker, the agent "
             "field is not the speaker."),
    ]


# ArenaNet's OWN dialog line from vault/captures/live/20260807T143055 at
# t=26.816 -- the one whose window the player clicked to produce
# `0x003B quest=80 code=0x03`. Ten code units, transcribed as MEASUREMENT: these
# are string IDS and markers, not text. We cannot read what it says and do not
# need to -- 44 of 44 name slots in the corpus resolve to encrypted archive
# records whose key is NOT FOUND, which is exactly why transcribing this is
# permitted and transcribing their prose is not.
#
# WHY REPLAY IT AT ALL. Q5 needs the client to send 0x003B, and the client only
# sends it when the player clicks an OPTION. Our own Q4 window had text and no
# option, so the markup that makes one is unrecovered. There is no server
# message between INTERACT and that click naming quest 80, so the quest id must
# be IN this string. Replaying it asks the client where: if it comes back as
# `0x003B quest=80`, the id is in these ten words and the client has told us so.
_ARENANET_OFFER_LINE = [0x2AE6, 0xF9CB, 0xE939, 0x5DD2, 0x010A,
                        0x3377, 0xDF18, 0xF3B0, 0x201F, 0x0001]


# The definitions the three live quest givers actually carried, MEASURED off
# WORLD_CREATE_AGENT in vault/captures/live/20260807T143055 by the interval join
# (the create in effect when the agent SPOKE, not its last create):
#
#   agent 99  t=20.140  model 0x200005C8  def 1480  allegiance 'play'  kind 9
#   agent 40  t=17.941  model 0x200005B3  def 1459  allegiance 'nonc'  kind 9
#   agent 36  t=66.737  model 0x200005C1  def 1473  allegiance 'nonc'  kind 9
#
# All three are CHAR_CLASS_MONSTER_BASE | def with AGENT_KIND_NPC -- the same
# class and kind our own spawns already use -- so the definition NUMBER is the
# only thing that differs, which is what makes this a one-variable test. Note
# the allegiances differ between givers ('play' against 'nonc'), so allegiance
# is not what marks a giver.
#
# THE DEFINITION MUST BE PUSHED FIRST, and this comment is here because the
# first version of this probe did not and TOOK THE CLIENT DOWN:
#
#     Assertion: index < m_count
#     P:\Code\Base\rtl\Array.h(587)                          build 38833
#
# which is exactly what `agents.npc_properties` already documents -- "the
# definition index is a raw array index on the client, and creating an agent
# whose definition was never sent takes the client down". The mistake was not
# the missing push, it was a BAD NUMBER: 536872392 was read as 0x20000188 and
# so as definition 392, when it is 0x200005C8 and definition 1480. 392 was
# never defined by anyone, so the create indexed past the end. Slot 1480 is in
# vault/content/npcs.toml already, extracted from this same capture, and
# npcdefs' own docstring cites it.
GIVER_DEFINITION = 1480         # agent 99's, the one whose line we replay
_GIVER_AGENT = 99
_VAULT_NPC_CACHE = {}


def _vault_npc(key):
    """An NPC row that lives ONLY in `vault/content/npcs.toml`, read at CALL time.

    NOT at import time, and that distinction is the entire function. `def_1480`
    and `def_1473` are bulk-extracted live definitions, so they are vault rows by
    the repo/vault split `toolkit/content.py` documents -- and binding one at
    module level made EVERY importer of this file die on a machine with no vault.
    MEASURED 2026-08-18, `RURIK_VAULT` pointed at a nonexistent directory: the
    server's own `import authsrv` raised `no npc row 'def_1480'`, and so did
    twelve tests, four of whose docstrings say "no vault, no socket, no client"
    flatly. They did not fail their floors -- the exception escaped before
    `checks.py` could report, so `test_quests.py` never reached check 1 of the 73
    its floor claims a bare machine runs.

    Call time is the RIGHT time, not merely a workaround: these rows are only ever
    read to build Step sequences that drive a real client, and client builds live
    in the vault too. A machine that cannot resolve the row could not have run the
    probe anyway, which is also why the fix is not a repo-side copy of the row --
    that would buy an import rather than a capability, and the vault row would
    override it by key on every machine where the probe can actually run.

    `toolkit/test_bareimport.py` is the guard, and it goes red on a new one.
    """
    # npc_template, NOT WORLD.rows(...) -- the raw row's `enc_name` is a LIST of
    # string ids and the codec wants an encoded str. Reaching for the row directly
    # gives `string of 26 code units exceeds cap 8`, which is the error
    # npc_template's own docstring exists to prevent. Hit it anyway on the first try.
    if key not in _VAULT_NPC_CACHE:
        _VAULT_NPC_CACHE[key] = npc_template(key)
    return _VAULT_NPC_CACHE[key]


def giver_npc():
    """The live giver's own type row. A CALL, not a constant -- see `_vault_npc`."""
    return _vault_npc("def_1480")


def _quest_giver_def_steps(origin):
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION} -- the live "
             f"giver's own type, from vault/content/npcs.toml",
             "nothing yet. This defines a TYPE, not a body -- and it is NOT "
             "optional: without it the create indexes past the end of the "
             "definition array and the client dies on Array.h:587."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION} -> model "
             f"{giver_npc()['model_id']}",
             "still nothing. One more message before a body can appear."),
        Step(4.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}) with the LIVE GIVER's "
             f"definition {GIVER_DEFINITION}, 150u from the player",
             "a body appears, carrying the same type ArenaNet's own quest giver "
             "carried. The definition is the ONLY thing changed from the "
             "quest_offer run, which used the hatcher's."),
        Step(8.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080 carrying the same captured greeting as quest_offer",
             "nothing yet -- 0x0080 accumulates."),
        Step(12.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "THE WHOLE QUESTION: does a CLICKABLE OPTION appear now that the "
             "speaker carries a real giver's definition? quest_offer sent this "
             "identical line at a hatcher (definition 3) and got text with no "
             "option and no 0x003B. If an option renders here, the client reads "
             "what a dialog offers from the AGENT, and definition 1480 is enough "
             "to arm it. If it still does not, the definition is not the "
             "discriminator either and the remaining candidates are a message "
             "earlier in the session, or the 43-unit OFFER line rather than "
             "this greeting."),
    ]


# GENERIC_VALUE 0x009F is [property_id, agent_id, value]. Property 11 is the
# QUEST MARKER, MEASURED across both keyed sessions -- it lands on 5 of 68
# created agents in :60935 and 9 of 88 in :62994, covers every dialog speaker in
# both, and takes only two values. The trace that fixes their meaning:
#
#   17.941  PROP11 agent 40 = 5                       map load, no interaction yet
#   28.179  QUEST_ADD 80        + PROP11 agent 40 = 4  accepted; 40 becomes turn-in
#   46.797  QUEST_REMOVE 80     + PROP11 agent 40 = 5  turned in at 40; back to 5
#   66.737  PROP11 agent 36 = 4                        quest 218 held, turned in at 36
#
# So 5 = "has a quest to OFFER" and 4 = "turn one in HERE" -- the green '!' and
# green '?' every Guild Wars player knows. Agent 99 holds 5 throughout, being an
# offerer the whole time. RECONSTRUCTION for the two English words; OBSERVED for
# the transitions, which flip with the quest lifecycle 2 of 2 in each direction.
GENERIC_VALUE = 0x009F
PROP_QUEST_MARKER = 11
QUEST_MARKER_OFFER = 5
QUEST_MARKER_TURN_IN = 4
# The third value, n=4 in the corpus, on the agent that offers code 0x04
# (advance). We emit it nowhere, because what it DRAWS is unmeasured.
QUEST_MARKER_ADVANCE = 3
# The CLEAR is a different PROPERTY, not a property-11 value: no value of 11
# ever removes a marker, and sending [11, agent, 0] would invent one.
PROP_QUEST_MARKER_CLEAR = 12


# 111 and 222 are chosen to be UNMISTAKABLE and outside every observed value.
# ArenaNet's slot A takes 100/250/500 and slot B takes 10/25/100, so a rendered
# pane showing 100 or 25 would be ambiguous about which slot drew it. Nothing in
# the corpus takes 111 or 222, they are different lengths on screen, and neither
# is a prefix of the other.
_REWARD_A, _REWARD_B = 111, 222
_REWARD_QUEST = 1463


def _quest_reward_steps():
    row = questdefs.load()[_REWARD_QUEST]
    framing = row.get("wire_framing", "template")
    body = questdefs.with_reward(row["description"], _REWARD_A, _REWARD_B,
                                 framing)
    return [
        Step(4.0, 0x0049,
             [_REWARD_QUEST, _SPAWN_WORLD, 0, 148, 32,
              questdefs.enc_string(row.get("enc_name") or []),
              questdefs.enc_string(row.get("enc_name") or []),
              questdefs.enc_string(row.get("enc_name") or []), 148],
             f"0x0049 QUEST_ADD[{_REWARD_QUEST}] so there is a log entry to "
             f"describe",
             "a quest in the log, as Q0 already established."),
        Step(3.0, 0x004C,
             [_REWARD_QUEST, body,
              questdefs.coded_literal(row["objectives"], framing)],
             f"0x004C description + a REWARD BLOCK carrying A={_REWARD_A} and "
             f"B={_REWARD_B}",
             "the log's detail pane shows our description followed by TWO "
             "reward lines. THE MEASUREMENT IS WHICH LINE CARRIES WHICH "
             "NUMBER: ref 10730 is fed 111 and ref 10732 is fed 222, so "
             "whichever line reads 111 is slot A. If one says '111 experience' "
             "and the other '222 gold', the seven-quest magnitude argument was "
             "right; if it is the other way round, a RECONSTRUCTION that has "
             "looked obvious all week was backwards."),
        Step(3.0, 0x0080, [body],
             "the SAME string on the dialog line, which is where ArenaNet puts "
             "it too -- byte-identical in 17 of 17 (screen, quest) pairs",
             "nothing yet; 0x0080 accumulates."),
        Step(2.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "the reward lines rendered in a DIALOG WINDOW as well, which needs "
             "no clicking and no log keypress to read. Two independent views of "
             "the same string is the point: if they disagree, the suffix is not "
             "position-independent and that is its own finding."),
    ]


# The values quest_marker_states already drew: 5 -> '!', 4 and 3 -> a down
# arrow, and 12=0 -> nothing. None of them is a '?', which the owner reports
# seeing over an NPC whose given quest is in progress. So either the '?' is a
# value ArenaNet never sent in our two-session corpus, or it is not this
# property at all.
#
# STATIC SEARCH BOUNDED NOTHING, and that is why this is a sweep. 0x009F's body
# at 0x008128F0 dispatches on the PROPERTY id through a 61-entry table at
# 0x00812EE0, and 56 of the 61 -- including 11 and 12 -- fall through to one
# shared case at 0x008129B0. The glyph choice is made further downstream, so the
# property switch cannot tell us how many VALUES are meaningful.
_MARKER_SWEEP = (5, 0, 1, 2, 6, 7, 8, 9)


_OBJECTIVE_AGENT = 98
# A DIFFERENT definition from the giver's 1480, and that is the point: the
# first version gave both bodies 1480 and put two identical 'Ascalonian Guard'
# nameplates on screen with nothing to tell the giver from the objective. 1473
# is another live NPC from the same capture, with its own model id and its own
# profession. An ambiguous frame is an unreadable result.
_OBJECTIVE_DEFINITION = 1473


def _objective_npc():
    """The gate guard's own type row. A CALL, not a constant -- see `_vault_npc`."""
    return _vault_npc("def_1473")


def _quest_objective_steps(origin):
    """Two NPCs: the giver, and the gate guard who completes the objective.

    The whole point is the MIDDLE state. With one NPC and no objective the
    quest goes '!' -> bag and kind 22 never fires; with a second NPC to walk to,
    the giver shows '?' between accept and completion, which is what a real
    quest looks like and what our server could not express until now.

    The two bodies carry DIFFERENT definitions so a screenshot can never be
    ambiguous about which is which -- see _OBJECTIVE_DEFINITION.
    """
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(2.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy - 130, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}) -- THE GIVER",
             "a body ahead and to one side."),
        Step(1.0, 0x0056,
             npc_properties(_OBJECTIVE_DEFINITION, _objective_npc()),
             f"NPC_UPDATE_PROPERTIES def {_OBJECTIVE_DEFINITION} -- the "
             f"GUARD's OWN type, so the two are told apart on sight",
             "nothing yet."),
        Step(0.5, 0x0057, npc_model(_OBJECTIVE_DEFINITION, _objective_npc()),
             f"NPC_UPDATE_MODEL def {_OBJECTIVE_DEFINITION}",
             "still nothing."),
        Step(1.0, 0x0020,
             create_agent(_OBJECTIVE_AGENT,
                          CHAR_CLASS_MONSTER_BASE | _OBJECTIVE_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy + 130, plane),
             f"WORLD_CREATE_AGENT({_OBJECTIVE_AGENT}) -- THE GATE GUARD",
             "a second body BESIDE the first rather than opposite it. The first "
             "placement put them 150u east and west, which is the camera's own "
             "axis -- they stacked vertically on screen and no pair of clicks "
             "could be unambiguous. Same distance, perpendicular."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"property 11 = 5 on the giver", "a green '!' over the giver."),
    ]


def _dialog_icons_steps(origin):
    """One option of EVERY kind in one window, each labelled with its own kind.

    The '?' is in the dialog, not over the NPC's head -- so the candidates are
    0x007E's two unexplained fields. Field 4 is 0xFFFFFFFF in 41 of 41 and this
    repo named it OPTION_FIELD4_ALWAYS on that evidence alone, which was a guess
    dressed as a name. The KIND field is the other candidate and it is the
    better one: kind 22 IS the in-progress code (0x05) and kind 18 IS the
    available one (0x03), which is exactly the '!' / '?' distinction the owner
    describes.

    Every kind in ONE window so the icons are compared side by side in a single
    frame -- six separate runs would compare six screenshots, and this arc has
    already learned what that costs.

    Kind 15 is omitted: its tag carries the 0x800000 bit CLEAR, so
    encode_service_select cannot express it and a click would hit
    decode_service_select's None branch.
    """
    ox, oy, plane = origin
    row = questdefs.load()[1463]
    framing = row.get("wire_framing", "template")
    kinds = [(questdefs.SERVICE_ACCEPT, 16), (questdefs.SERVICE_DECLINE, 17),
             (questdefs.SERVICE_SHOW, 18), (questdefs.SERVICE_ADVANCE, 21),
             (questdefs.SERVICE_IN_PROGRESS, 22), (questdefs.SERVICE_TURN_IN, 23)]
    steps = [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})", "a body."),
        Step(3.0, 0x0080,
             [questdefs.coded_literal("Every option kind, one per line.",
                                      framing,
                                      limit=questdefs.DIALOG_UNITS)],
             "0x0080, the window's text", "nothing yet; it accumulates."),
        Step(2.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "a window with text and no options yet."),
    ]
    for code, kind in kinds:
        steps.append(Step(
            1.0, 0x007E,
            [kind, questdefs.coded_literal(f"kind {kind} code {code}", framing),
             questdefs.encode_service_select(1463, code),
             questdefs.OPTION_FIELD4_ALWAYS],
            f"0x007E kind {kind} (code 0x{code:02X}), labelled with its own kind",
            "one more line in the open window. THE MEASUREMENT IS THE ICON TO "
            "THE LEFT OF EACH LABEL. If kind 18 draws a '!' and kind 22 a '?', "
            "the owner's description is the kind field and this is the answer. "
            "If every line has the same icon, or none, the '?' is not the kind "
            "and field 4 -- 0xFFFFFFFF in 41 of 41, which this repo named "
            "OPTION_FIELD4_ALWAYS on no other evidence -- is the next suspect."))
    return steps


def _quest_marker_sweep_steps(origin):
    """Walk property 11 across the values the corpus never showed us.

    5 goes FIRST as an in-run control: it is the one value whose glyph is
    already measured, so if the '!' does not appear the run is broken and no
    later frame means anything. Everything after it is unmeasured.
    """
    ox, oy, plane = origin
    hold = 5.0
    steps = [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})",
             "a bare head -- the baseline every frame below is read against."),
    ]
    # A CLEAR BETWEEN EVERY VALUE, and it is what makes the run readable. The
    # first version ran the values back to back and the frame-to-value mapping
    # then rested on arithmetic across two clocks that start at different
    # events -- the exact reasoning that has already misled this arc twice.
    # With a clear between each, every value is a RUN of glyph-bearing frames
    # bracketed by bare ones, so the boundaries are visible in the green-pixel
    # trace and no mapping has to be assumed.
    for i, v in enumerate(_MARKER_SWEEP):
        if v == 5:
            watch = ("the green '!', ALREADY MEASURED. The control: if it does "
                     "not draw, the run is broken and no later frame counts.")
        else:
            watch = (f"UNKNOWN. Value {v} appears in neither keyed session, so "
                     f"nothing predicts it -- a '?', another glyph, or nothing "
                     f"at all are all live. A '?' here names the value the "
                     f"owner has been describing.")
        steps.append(Step(hold if i else 3.0, GENERIC_VALUE,
                          [PROP_QUEST_MARKER, _GIVER_AGENT, v],
                          f"property 11 = {v}", watch))
        steps.append(Step(3.0, GENERIC_VALUE,
                          [PROP_QUEST_MARKER_CLEAR, _GIVER_AGENT, 0],
                          f"clear, separating {v} from what follows",
                          "a bare head. This frame is a SEPARATOR, not a "
                          "measurement -- it is what lets the value above be "
                          "attributed without counting frames."))
    return steps


def _quest_marker_states_steps(origin):
    """Walk one NPC through every marker state, holding each long enough to see.

    Four questions in one run, and each state is a separate screenshot rather
    than a separate session so the glyphs are comparable pixel for pixel: same
    NPC, same camera, same frame position, one variable.
    """
    ox, oy, plane = origin
    hold = 7.0
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}",
             "nothing yet, and mandatory before the create."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})",
             "a body, with NO marker over its head. This is the baseline every "
             "state below is compared against, and it matters: without it, "
             "'a glyph is there' cannot be told from 'a glyph changed'."),
        Step(3.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             "property 11 = 5",
             "A GREEN '!'. Already seen in quest_giver_mark; here it is the "
             "control that proves the sequence is working before the states "
             "nobody has looked at."),
        Step(hold, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_TURN_IN],
             "property 11 = 4",
             "MEASURED: A GREEN DOWN ARROW, not a '?'. Our server sends this "
             "on every accept and three runs went by without capturing it, "
             "because the accept/turn-in cycles outran the screenshot interval. "
             "The '?' reading was INFERENCE and it was WRONG -- the glyph is an "
             "arrow, which reads as 'this NPC is your objective'. The STATE the "
             "value marks is unchanged and still fixed by the corpus."),
        Step(hold, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_ADVANCE],
             "property 11 = 3",
             "UNKNOWN, and that is why it is here. Value 3 occurs 4 times in "
             "the corpus on the agent that offers code 0x04 (advance). Whether "
             "it draws a THIRD glyph or repeats 4's is unmeasured, and we emit "
             "it nowhere precisely because nobody knows. MEASURED: the same "
             "down arrow as 4, four frames of each, differing only in bob "
             "phase -- so 3 and 4 are INDISTINGUISHABLE on this surface, and "
             "whatever separates them is not the overhead glyph."),
        Step(hold, GENERIC_VALUE,
             [PROP_QUEST_MARKER_CLEAR, _GIVER_AGENT, 0],
             "property 12 = 0 -- THE CLEAR",
             "NO GLYPH AT ALL, back to the baseline frame. This is "
             "RECONSTRUCTION today: property 12 is 0 in 22 of 22 and 16 of 16 "
             "sends, so its value range is never exercised and the reading "
             "rests on consequence alone. If the marker survives, our server "
             "has no way to take a marker down and every giver keeps its glyph "
             "forever."),
    ]


def _quest_giver_mark_steps(origin):
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}",
             "nothing yet -- and mandatory before the create, or Array.h:587."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}",
             "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT}), the giver's own definition",
             "a body with the guard's nameplate, as quest_giver_def already "
             "showed. No marker over its head yet."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} = "
             f"{QUEST_MARKER_OFFER} on agent {_GIVER_AGENT} -- THE MARKER",
             "A GREEN '!' OVER THE NPC'S HEAD. This is the message ArenaNet "
             "sends at map load for every quest giver, and the one this arc "
             "missed twice by searching only between INTERACT and the click. "
             "If the exclamation appears, property 11 is named."),
        Step(4.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080, the same captured greeting as the two runs before",
             "nothing yet -- 0x0080 accumulates."),
        Step(8.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "THE QUESTION: is the last line CLICKABLE NOW? Two runs sent this "
             "identical greeting -- one at a hatcher, one at this very "
             "definition -- and both rendered plain text with no option and no "
             "0x003B. The marker is the only thing added. If an option renders, "
             "the client arms a dialog's quest options from property 11 and "
             "candidate 2 is confirmed. If it still does not, the marker is "
             "only the overhead glyph and the option needs the quest id from "
             "somewhere this arc has still not found."),
    ]


# GAME_SMSG 0x007E IS THE DIALOG OPTION. [u8 kind, string16(128) label,
# u32 tag, u32 0xFFFFFFFF], from the client's own RECV descriptor and
# schema/messages.json, which agree.
#
# The tag is the DWORD THE CLIENT WILL SEND BACK in GAME_CMSG 0x003B if the
# player clicks that line -- the same 0x800000 | (quest_id << 8) | code the
# accept arm already decodes. MEASURED, and the check could have failed:
# **22 of 22 clicks across both keyed sessions were announced by a prior 0x007E
# on the same connection, with zero counterexamples.** t=26.816 announces
# 0x805003 and the player sends exactly that at t=27.679; t=28.479 announces
# 0x85B603 and the player sends it at t=28.780.
#
# This is what two earlier runs were missing, and it was never in the dialog
# string, the agent's definition or the quest marker. It arrives beside the
# 0x0080/0x0081 pair and nothing had looked at it.
#
# field1 takes 15,16,17,18,21,22,23 in the corpus -- an option KIND or icon,
# unnamed. 18 is what the quest offers used. field4 is 0xFFFFFFFF in 37 of 37.
DIALOG_OPTION = 0x007E
# The kind that goes with code 0x03, "show me this quest". The corpus binds
# kind to code 1:1 in 41 of 41, so a probe that hardcodes a kind is only correct
# for one code -- questdefs.option_kind() is the general answer and this
# constant exists because the quest_option probe below predates the table and is
# kept as the record of that run.
OPTION_KIND_QUEST = 18
OPTION_FIELD4_ALWAYS = 0xFFFFFFFF


def _quest_turnin_steps(origin):
    """Place the giver and stop. The SERVER drives everything after that.

    Unlike every other probe in this arc, the interesting messages here are not
    steps -- they are the server's replies to what the player does. That is the
    point: Q7 is the first rung where our server runs a quest lifecycle rather
    than replaying a script at a client.
    """
    ox, oy, plane = origin
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})",
             "the giver, 150u out, with its own nameplate."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} = "
             f"{QUEST_MARKER_OFFER}",
             "the green '!'. NOW CLICK THE NPC, then the option, then the NPC "
             "again, then the option again -- the server answers each."),
    ]


def _quest_option_steps(origin):
    ox, oy, plane = origin
    row = questdefs.load()[1463]
    tag = questdefs.encode_service_select(1463, questdefs.SERVICE_ACCEPT)
    return [
        Step(2.0, 0x0056, npc_properties(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_PROPERTIES def {GIVER_DEFINITION}", "nothing yet."),
        Step(1.0, 0x0057, npc_model(GIVER_DEFINITION, giver_npc()),
             f"NPC_UPDATE_MODEL def {GIVER_DEFINITION}", "still nothing."),
        Step(3.0, 0x0020,
             create_agent(_GIVER_AGENT,
                          CHAR_CLASS_MONSTER_BASE | GIVER_DEFINITION,
                          AGENT_KIND_NPC, ox + 150, oy, plane),
             f"WORLD_CREATE_AGENT({_GIVER_AGENT})", "a body with a nameplate."),
        Step(2.0, GENERIC_VALUE,
             [PROP_QUEST_MARKER, _GIVER_AGENT, QUEST_MARKER_OFFER],
             f"GENERIC_VALUE property {PROP_QUEST_MARKER} = "
             f"{QUEST_MARKER_OFFER} -- the green '!'",
             "the exclamation mark, already confirmed by quest_giver_mark."),
        Step(3.0, 0x0080,
             [questdefs.coded_literal(row["giver_dialogue"],
                                      row.get("wire_framing", "template"),
                                      limit=questdefs.DIALOG_UNITS)],
             "0x0080 carrying OUR OWN giver line from content/quests.toml",
             "nothing yet -- 0x0080 accumulates. Note this is our prose, not "
             "ArenaNet's replayed greeting: the two earlier runs borrowed their "
             "line because ours had never been tested in a dialog."),
        # ORDER MATTERS AND THE FIRST ATTEMPT HAD IT BACKWARDS. ArenaNet's own
        # t=26.816 burst is 0x0080, then 0x0081, THEN the two 0x007E options,
        # then the marker. Sending the option before the flush put it into a
        # text buffer that 0x0081 then zeroed, and the window opened with our
        # prose and no clickable line -- which looked exactly like "0x007E does
        # not work" and was really "0x0081 opens the window; options are
        # appended to an open one".
        Step(6.0, 0x0081, [_GIVER_AGENT],
             f"0x0081 flush at agent {_GIVER_AGENT}",
             "the window opens with OUR prose. The option arrives next."),
        Step(1.0, DIALOG_OPTION,
             [OPTION_KIND_QUEST,
              questdefs.coded_literal("Accept: A First Errand",
                                      "template", limit=128),
              tag, OPTION_FIELD4_ALWAYS],
             f"0x007E DIALOG OPTION -- our label, tag 0x{tag:06X} "
             f"(quest 1463, code 0x{questdefs.SERVICE_ACCEPT:02X} ACCEPT)",
             "THE WHOLE LOOP: a CLICKABLE LINE appended to the open window. "
             f"Clicking it must send `c2s 0x003B 0x{tag:06X}`, which our accept "
             "arm decodes to quest 1463 code 1 and answers with 0x0049 built "
             "from the content row -- so the quest appears in the log named "
             "'Ascalon'. Red at any link: no option drawn, no 0x003B, a "
             "different dword, or a 0x0049 that draws no log entry."),
    ]


def _quest_offer_steps():
    return [
        Step(6.0, 0x0080, [questdefs.enc_string(_ARENANET_OFFER_LINE)],
             "0x0080 carrying ArenaNet's own captured offer line, verbatim",
             "nothing yet -- 0x0080 accumulates."),
        Step(10.0, 0x0081, [_TEST_NPC_AGENT],
             f"0x0081 flush at agent {_TEST_NPC_AGENT}",
             "A WINDOW WITH A CLICKABLE OPTION, unlike Q4's, which had text "
             "and no option. THE MEASUREMENT IS WHAT THE CLICK SENDS: if "
             "`c2s 0x003B quest=80` appears in the log, the quest id lives in "
             "those ten words and the client has just told us where. Our server "
             "will then answer 'quest 80 NOT IN content/quests.toml', which is "
             "the correct refusal and not a failure of this probe."),
    ]


def _quest_panel_steps():
    """QUEST_COMPLETE_PANEL (0x004E): which of its three dwords does the render read?

    The whole completion family is 0 of 22,524 s2c in the corpus, so unlike
    merchant_window there is no retail sequence to replicate: every value
    below is an INVENTED sentinel, chosen to be unmistakable, and the probe's
    job is to let the render -- or an assert -- name the fields. The one
    prior firing is the 2026-08-13 screen pass (20260813T123003): all-zero
    payload, centre-screen victory animation, no assert. So (0,0,0) is the
    known-safe replication arm, and it goes first because nothing after it
    is readable if it does not reproduce.

    Arm 2 re-sends the IDENTICAL payload and is the load-bearing control:
    nothing anywhere says the panel renders twice in one session. If arm 2
    draws nothing, every later arm is unreadable in this rig and the design
    moves to one arm per launch -- both outcomes are wanted, neither is a
    broken run.

    Arm 3 carries the one semantic hypothesis worth pre-registering: field 1
    as a quest id. 1463 is OUR authored quest (content/quests.toml), so if
    the panel binds it, text we control appears on a completion screen and
    the reward arc joins the authoring arc. RECONSTRUCTION, admitted as such.

    Arm 4's 111/222/333 follow the quest_reward precedent -- sentinels
    outside every corpus range, so a numerically rendered field names its
    own screen position. Arm 5 is the assert fisher, max dword in all three
    fields, deliberately LAST: 0x0096/0x0097 taught that out-of-range
    completion values kill the client, and an assert here ends the run --
    its dialog text names the gate, which is a result, not a failure.

    The panel is fed by FIVE frame ids and this probe supplies exactly one
    (0x10000155, posted by 0x004E's own handler at 0x0080F6C7). An underfed
    or partial render is EXPECTED and is not evidence the fields are wrong
    (studies/quests/FINDINGS.md 9.3).
    """
    QUEST_COMPLETE_PANEL = 0x004E  # deliberately NOT in authsrv.py's constants:
    # the server's own turn-in path refuses the completion family on purpose
    # (authsrv.py's SERVICE_TURN_IN comment), and this probe must not change that.
    return [
        Step(15.0, QUEST_COMPLETE_PANEL, [0, 0, 0],
             "all-zero replication of 20260813T123003",
             "the centre-screen victory animation. Absent means the rig, not "
             "the fields -- stop reading here."),
        Step(20.0, QUEST_COMPLETE_PANEL, [0, 0, 0],
             "identical re-fire -- the one-shot control",
             "whether a SECOND render happens at all. No render here makes "
             "every later arm unreadable in this rig, and that is a finding."),
        Step(20.0, QUEST_COMPLETE_PANEL, [1463, 0, 0],
             "field 1 = 1463, our authored quest id",
             "any TEXT on the render: quest 1463's strings are ours, so "
             "authored text appearing binds field 1 to a quest id."),
        Step(20.0, QUEST_COMPLETE_PANEL, [111, 222, 333],
             "distinct sentinels in all three fields",
             "any NUMBER on the render: 111/222/333 sit outside every corpus "
             "range, so a rendered value names which field it came from."),
        Step(20.0, QUEST_COMPLETE_PANEL,
             [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF],
             "max-dword assert fisher, deliberately last",
             "an assert dialog naming a gate (a result -- the run ends with "
             "it), or a render identical to arm 1 (the fields are unread)."),
    ]


PROBES = {
    "quest_objective": lambda a, o: Probe(
        question="Does a quest with a real objective show the gold '?' between "
                 "accept and completion?",
        predicts="THREE DIFFERENT SCREENS FROM THE SAME NPC, in order. Talk to "
                 "the giver: kind 18, a gold '!', accept/decline. Accept, then "
                 "talk to it again: kind 22, a gold '?', because the objective "
                 "is not met. Walk to the gate guard and talk: the objective "
                 "completes and 0x0054 rewrites the tracker line. Talk to the "
                 "giver a third time: kind 23, the bag. Until now our server "
                 "returned the bag the instant a quest was held, so kind 22 "
                 "was unreachable -- the state existed on the wire and had no "
                 "way to happen. If the '?' screen does not appear, the "
                 "objective state is not reaching _quest_lines; if 0x0054 "
                 "changes nothing on screen, DESC_FILLED was not set and the "
                 "update was swallowed by the gate at 0x0080F9CD.",
        steps=_quest_objective_steps(o),
        note="RUN ON --map 449 with --shots 2. The giver is 150u EAST and the "
             "gate guard 150u WEST, so no screenshot is ambiguous about which "
             "is which. Click the giver, accept, click the giver again to see "
             "the '?', then the guard, then the giver once more. The interact "
             "click lands near (0.499, 0.625) and dialog options around "
             "(0.491, 0.52-0.55).",
    ),
    "dialog_icons": lambda a, o: Probe(
        question="The '?' is in the DIALOG, not over the NPC. Does it come from "
                 "0x007E's option KIND?",
        predicts="KIND 18 DRAWS A '!' AND KIND 22 DRAWS A '?'. Kind is bound to "
                 "the 0x003B code 1:1, and the two codes are exactly the states "
                 "the owner describes -- 18 goes with 0x03 (a quest available "
                 "to take) and 22 with 0x05 (one already in progress). Three "
                 "runs looked for this over the NPC's head, where property 11 "
                 "turned out to draw eight glyphs and no '?' at all; the dialog "
                 "is where it was all along. If every line shows the same icon "
                 "or none, the kind is not it, and the suspect becomes field 4 "
                 "-- 0xFFFFFFFF in 41 of 41, which this repo named "
                 "OPTION_FIELD4_ALWAYS on that and nothing else.",
        steps=_dialog_icons_steps(o),
        note="RUN ON --map 449 with --shots 1. Every kind lands in ONE window, "
             "each line labelled with its own kind number, so the icons are "
             "compared in a single frame rather than across six screenshots. "
             "No clicks: the whole measurement is the left edge of the option "
             "lines. Kind 15 is omitted -- its tag has the 0x800000 bit clear "
             "and our encoder cannot express it.",
    ),
    "quest_marker_sweep": lambda a, o: Probe(
        question="Where does the '?' over a quest NPC's head actually come "
                 "from? Is it a property-11 value the corpus never showed us?",
        predicts="ONE OF 0, 1, 2, 6, 7, 8, 9 DRAWS A '?', and the rest draw "
                 "nothing. The corpus only ever carries 3, 4 and 5 -- and it is "
                 "one operator's route run twice, so absence there is weak "
                 "evidence about the protocol. quest_marker_states measured "
                 "5 -> '!', 4 and 3 -> a down arrow, none of them a '?'. The "
                 "rival outcome is real and would be worth as much: if NOTHING "
                 "in this sweep draws a '?', the glyph is not property 11 at "
                 "all, and the next places to look are the dialog window and "
                 "the compass -- neither of which any run has touched.",
        steps=_quest_marker_sweep_steps(o),
        note="RUN WITH --shots 1, --map 449, no clicks. Value 5 goes first as "
             "an in-run control. Read the frames as a strip against the bare "
             "head, not one at a time -- reading frames in isolation is how the "
             "'?' claim survived three runs unchallenged.",
    ),
    "quest_marker_states": lambda a, o: Probe(
        question="What does each 0x009F property-11 value actually DRAW, and "
                 "does property 12 = 0 take a marker down?",
        predicts="5 draws '!', 4 draws '?', and 12=0 clears back to a bare "
                 "head. Value 3 is genuinely open -- it may draw a third glyph "
                 "or repeat 4's. The '?' is the one this run exists for: our "
                 "server has sent 4 on every accept since the two-screen flow "
                 "landed, three runs have gone by, and not one captured it, "
                 "because the accept/turn-in cycles ran faster than the "
                 "screenshot interval. The reading is inference from the owner "
                 "and the corpus, and inference is not what this project "
                 "counts as an answer.",
        steps=_quest_marker_states_steps(o),
        note="RUN WITH --shots 1 and a hold long enough for all four states -- "
             "each is held 7 s, so ~7 frames apiece and no state can be missed "
             "between shots the way it was three times before. --map 449, no "
             "clicks, no keys: the whole measurement is the NPC's head across "
             "five frames, including the pre-marker baseline. Compare frames, "
             "do not read one in isolation.",
    ),
    "quest_reward": lambda a, o: Probe(
        question="Which of the reward block's two numeric slots is experience "
                 "and which is gold?",
        predicts="TWO REWARD LINES render under our description, one reading "
                 "111 and one reading 222. The seven-quest magnitude argument "
                 "says slot A (ref 10730) is experience and slot B (ref 10732) "
                 "is gold -- A takes 100/250/500 and B takes 10/25/100 across "
                 "the corpus -- but that is PLAUSIBILITY, not measurement: both "
                 "templates are encrypted and the RC4 key is NOT FOUND, so "
                 "neither the wire nor the archive can settle it and only a "
                 "rendered pane can. 111 and 222 sit outside every observed "
                 "value on purpose, so no reading is ambiguous. A THIRD "
                 "outcome is live and worth naming: if only ONE line renders, "
                 "or the numbers come out as anything other than 111 and 222, "
                 "then `0101 <word>` is not a 0x100-biased numeric argument and "
                 "a CORROBORATED reading falls with it.",
        steps=_quest_reward_steps(),
        note="RUN ON --map 449 with a hold long enough for all four steps, and "
             "press L. Two views of the same string are produced deliberately "
             "-- the log's detail pane and a dialog window -- because ArenaNet "
             "puts the identical suffix in both (17 of 17), and a disagreement "
             "between them would itself be the finding. The dialog needs no "
             "keypress, so read that one first.",
    ),
    "quest_turnin": lambda a, o: Probe(
        question="Does a quest LEAVE the log on turn-in -- and is ArenaNet's "
                 "DOUBLED 0x0052 a protocol requirement or a party broadcast?",
        predicts="The whole lifecycle runs from four clicks: interact -> accept "
                 "-> interact -> turn in, and the quest LEAVES the log. The "
                 "second prediction is the one worth the run: our server sends "
                 "0x0052 ONCE, not twice. ArenaNet sends it twice 3 of 3, but "
                 "every live session is a SOLO operator, so the corpus cannot "
                 "tell a protocol requirement from one player's copy of a "
                 "two-player broadcast -- and 0x0052's body is a deleter that "
                 "binary-searches the id, so a second one has nothing to find. "
                 "If the quest leaves the log on a single 0x0052, the doubling "
                 "was never for us. If it does NOT leave, the double is "
                 "load-bearing and that is the finding instead. NO REWARD is "
                 "granted and none should be looked for: the whole completion "
                 "family is 0 of 22,524 in the corpus.",
        steps=_quest_turnin_steps(o),
        note="RUN ON --map 449. The probe only PLACES the giver; every quest "
             "message after that is the server answering a click, which is what "
             "makes this the first rung where our server runs a lifecycle "
             "rather than replaying a script. Click the NPC around "
             "(0.499, 0.625) and the option around (0.480, 0.545) at "
             "1936x1040, twice each, then press L.",
    ),
    "quest_panel": lambda a, o: Probe(
        question="Which of QUEST_COMPLETE_PANEL's three dwords does the "
                 "render read -- the reward arc's first real question?",
        predicts="Arm 1 reproduces the 2026-08-13 centre-screen victory "
                 "animation from an all-zero payload; that much is OBSERVED "
                 "(20260813T123003) and everything else is invention, stated "
                 "as such. Arm 2's identical re-fire renders AGAIN -- "
                 "RECONSTRUCTION from the handler's unconditional frame post "
                 "at 0x0080F6C7 -- and a one-shot panel instead is itself a "
                 "finding that moves the design to one arm per launch. If "
                 "field 1 is a quest id, arm 3 puts OUR text on the render "
                 "(quest 1463 is ours); if any field renders numerically, "
                 "arm 4's 111/222/333 names it; arm 5's max dwords either "
                 "change nothing or buy an assert whose text names the gate. "
                 "An underfed render is expected throughout: this supplies "
                 "one of the FIVE frame ids the scene subscribes to.",
        steps=_quest_panel_steps(),
        note="ANSWERED 2026-08-19, agent-piloted (harness 20260819T071548, "
             "studies/quests/FINDINGS.md 9.6): dword 1 EXPERIENCE, dword 2 "
             "GOLD, dword 3 SKILL POINTS, read from the panel's own toast on "
             "the 111/222/333 arm. Zero fields are omitted from the sentence "
             "(all-zero draws the banner with NO toast, which explains the "
             "2026-08-13 sweep's silent picture), max dwords render unsigned "
             "with no assert, and the panel re-fires per send. The arm-3 "
             "quest-id hypothesis is REFUTED: 1463 rendered as '1,463 "
             "experience'. Display only -- the Level chip sat at 1 beside a "
             "4.29-billion-experience toast; the grant protocol remains "
             "0-of-corpus. Kept runnable as the completion-panel calibration. "
             "Launch recipe: caged loopback, actions '0:play', --shots 1 "
             "--hold 120; sends land at about t+15/35/55/75/95. Read the "
             "gamesrv log for all five PROBE lines before believing any "
             "screen reading, and read frames by EYE as well as by diff: "
             "the committed scorer has no player-body mask, and the panel "
             "draws exactly where a mask would sit.",
    ),
    "quest_option": lambda a, o: Probe(
        question="Can a player accept OUR quest, from OUR dialog, by clicking "
                 "an option we sent -- the whole Q5 loop end to end?",
        predicts="A WINDOW WITH OUR TEXT AND A CLICKABLE LINE, and clicking it "
                 "sends `c2s 0x003B 0x85B701` (quest 1463, code 1), which the "
                 "accept arm answers with 0x0049 from content/quests.toml so "
                 "the quest appears in the log. 0x007E is the option message "
                 "and the confidence is high for one reason: 22 of 22 clicks "
                 "in both keyed sessions were announced by a prior 0x007E "
                 "carrying the exact dword, zero counterexamples. Four things "
                 "can still go red independently -- no option drawn, no 0x003B, "
                 "a dword we did not predict, or a 0x0049 that draws no log "
                 "entry -- and each names a different broken link.",
        steps=_quest_option_steps(o),
        note="RUN ON --map 449. Click the option line in the window, around "
             "(0.491, 0.541) at 1936x1040. This is the first probe in the arc "
             "whose dialog text is OURS rather than ArenaNet's replayed line.",
    ),
    "quest_giver_mark": lambda a, o: Probe(
        question="Does GENERIC_VALUE property 11 -- the quest marker -- arm the "
                 "clickable option that two earlier runs could not produce?",
        predicts="A GREEN '!' OVER THE NPC, and the greeting's last line "
                 "becomes CLICKABLE, sending 0x003B. Property 11 was found by "
                 "widening the corpus scan from the INTERACT-to-click window to "
                 "the whole session, which is where it was hiding: ArenaNet "
                 "writes it AT MAP LOAD, 4 of 4 speakers covered, on 5 of 68 "
                 "created agents, with exactly two values whose transitions "
                 "track the quest lifecycle (5 -> 4 on accept, 4 -> 5 on turn "
                 "in, 2 of 2 each way). The marker alone may still not carry "
                 "WHICH quest, in which case the '!' appears and no option "
                 "does -- and that separates the glyph from the option "
                 "cleanly, which no run so far has done.",
        steps=_quest_giver_mark_steps(o),
        note="RUN ON --map 449. One variable against quest_giver_def: the "
             "0x009F property-11 write. Click the window's last line around "
             "(0.491, 0.541) at 1936x1040. Watch the NPC's HEAD as well as the "
             "window -- the glyph and the option are two separate outcomes and "
             "this run can produce either without the other.",
    ),
    "quest_giver_def": lambda a, o: Probe(
        question="Does the clickable quest option come from the AGENT rather "
                 "than the dialog string -- specifically, from its definition?",
        predicts="A CLICKABLE OPTION APPEARS, where quest_offer's identical "
                 "line at a hatcher produced text and none. quest_offer "
                 "refuted 'the option is in the string' by replaying "
                 "ArenaNet's own ten words verbatim and getting no option and "
                 "no 0x003B; the surviving difference is the speaker. Theirs "
                 "was definition 392 and ours was 3. A SECOND prediction, "
                 "cheaper and independent: the body renders at all WITHOUT a "
                 "0x0056/0x0057 pair, because ArenaNet never defines 392 in the "
                 "capture -- if it does render, these types live in the "
                 "client's own data, which is a fact worth having whatever the "
                 "option does.",
        steps=_quest_giver_def_steps(o),
        note="RUN ON --map 449 and CLICK THE LINE the window's text ends with, "
             "around (0.491, 0.541) at 1936x1040 -- that is where quest_offer's "
             "greeting put it. One variable against quest_offer: the definition. "
             "Everything else, including the replayed line, is identical.",
    ),
    "quest_offer": lambda a, o: Probe(
        question="Where does the clickable quest option come from -- and is the "
                 "quest id inside the dialog string itself?",
        predicts="A CLICKABLE OPTION RENDERS, and clicking it sends "
                 "`0x003B quest=80 code=0x03`. The corpus shows no server "
                 "message between INTERACT and that click naming quest 80, and "
                 "the two captured offer lines differ ONLY in one varint group "
                 "(3377 DF18 F3B0 201F against 3375 FE11 D56F 2195) while "
                 "sharing the prefix 2AE6 F9CB E939 5DD2 010A -- so that group "
                 "is where the quest lives. If NO option renders, the option is "
                 "not carried by the string and something else in the corpus "
                 "arms it. If an option renders but the click reports a "
                 "DIFFERENT quest id, the mapping is client-side and the string "
                 "is only a label.",
        steps=_quest_offer_steps(),
        note="RUN WITH --enemy --practice-target --map 449, and CLICK THE "
             "OPTION -- an --actions `click:` step lands during the hold, since "
             "the action script runs on the client's clock rather than after "
             "the probe. The line is ArenaNet's own bytes replayed verbatim: "
             "string ids and markers, never text, and we could not read the "
             "text if we wanted to.",
    ),
    "npc_dialog": lambda a, o: Probe(
        question="Is GAME_SMSG 0x0080 + 0x0081 the NPC dialog window -- the "
                 "reply to INTERACT that test_dispatch called this server's "
                 "missing gate?",
        predicts="THE PAIR OPENS A DIALOG WINDOW, and the order matters: the "
                 "0x0080 alone shows NOTHING and the 0x0081 is what displays "
                 "it. Named in FINDINGS 2.5 from the two handler bodies plus a "
                 "correlation on ArenaNet's wire (0x0080 precedes 11 of 11 "
                 "quest selects per session against a 0.13% background rate, "
                 "0x0081 names the interacted agent 23 of 23), and the "
                 "clincher: a 0x0080 string at t=27.719 is byte-identical for "
                 "22 code units to the 0x004C description that follows it. But "
                 "NEITHER HAS EVER BEEN SENT TO A CLIENT -- the whole naming is "
                 "read-side, and this is the first time either goes out.",
        steps=_npc_dialog_steps(),
        note="RUN WITH --enemy --practice-target --map 449. The NPC only needs "
             "to EXIST for 0x0081 to name it; nothing here requires the player "
             "to reach or click it. Without --enemy the world is empty, agent "
             "10 does not exist, and a window naming a missing agent is a "
             "different experiment than the one intended.\n"
             "The line is framed, because a bare literal starting below 0x100 "
             "crashes the client on TextApi.cpp:585 -- MEASURED on 2026-08-15, "
             "and questdefs refuses to build one now.",
    ),
    "quest_description": lambda a, o: Probe(
        question="Does OUR OWN PROSE render in a real client's quest log -- and "
                 "does a literal have to carry ArenaNet's framing to do it?",
        predicts="THE DESCRIPTION PANE READS 'Speak to the gate guard, then "
                 "return to me.' -- our sentence, our words, chosen by us.\n"
                 "THE CONTROL HALF OF THIS PROBE HAS ALREADY RUN AND IS NOT "
                 "REPEATED. On 2026-08-15 the same probe sent a second quest "
                 "whose description was the same sentence with NO framing, and "
                 "it did not merely fail to render -- it killed the client on "
                 "its own bound check, `(codedString[0] & ~WORD_BIT_MORE) >= "
                 "WORD_VALUE_BASE`, TextApi.cpp:585, with our sentence sitting "
                 "verbatim as UTF-16 in the crash stack. So the marker/varint "
                 "rule is confirmed by ArenaNet's own assert and the bare arm "
                 "is settled; questdefs now REFUSES to build one. Re-running it "
                 "would buy a second crash and no second finding.\n"
                 "IF THE PANE IS EMPTY, the framing is necessary but not "
                 "sufficient and the next suspect is the 0x0107 marker rather "
                 "than the 0x0BA9 template id. IF THE CLIENT ASSERTS AGAIN, our "
                 "framing constants are wrong and the crash names which.",
        steps=_quest_description_steps(o),
        note="RUN WITH --map 449, and OPEN THE QUEST LOG once both quests are "
             "in. The tracker shows the NAME; the description pane is what this "
             "probe is about, and it is behind the log. Q0 already proved the "
             "name path, so a tracker reading 'Ascalon' twice is the setup "
             "working, not the result.\n"
             "WATCH THE ORDER TRAP: 0x004C sets flag bit 0 "
             "(CHAR_CHALLENGE_FLAG_DESC_FILLED) and 0x0054's body returns "
             "immediately when that bit is clear, so objectives sent before the "
             "description are a SILENT no-op. This probe sends no 0x0054 at all "
             "for exactly that reason -- one variable.",
    ),
    "quest_name": lambda a, o: Probe(
        question="Does a quest name we chose render as text in a real client, "
                 "or is 'commit the id, resolve the string at run time' "
                 "something this project has only ever done in one direction?",
        predicts="THE QUEST TRACKER READS 'Ascalon'. Everything the quests arc "
                 "established about coded strings is DECODE-side: we have "
                 "parsed ArenaNet's and re-encoded them byte-identically, but "
                 "no string we built has ever been sent to a client -- "
                 "compass_quest sent three empty ones on purpose. If this "
                 "renders, the naming half of quest authoring is done and the "
                 "problem reduces to 'which string id'. If it renders '?' or "
                 "blank, an offline round trip agreeing with itself was never "
                 "evidence and the string16 encoding becomes rung 1.",
        steps=_quest_name_steps(o),
        note="RUN WITH --map 449. The map is not incidental: map 148, which "
             "the sibling compass_quest probe uses, cannot load at all right "
             "now because no client archive in the vault binds its file id the "
             "way the server's does (contentids.py refuses the launch, and it "
             "is right to). 449 is one of the eight rows both archives agree "
             "on. The quest tracker is map-independent, so nothing about this "
             "question is weakened by the substitution -- but the COMPASS arm "
             "is not measured here and must not be read out of this run.",
    ),
    "quest_name_authored": lambda a, o: Probe(
        question="Does the quest name WE authored (string id 100552, written "
                 "by textwrite.py --set) render in the tracker where "
                 "ArenaNet's 0x3D64 did?",
        predicts="An A/B in one run, riding 0x0049's last-pushed-becomes-"
                 "active write: the tracker reads 'Ascalon' after the control "
                 "and SWITCHES to 'A First Errand' after the treatment, whose "
                 "words come from content/quests.toml's committed varint "
                 "[0x8103, 0x0CC8] rather than a probe literal. That would "
                 "close rung Q2b end to end: our record, our id, our words, "
                 "their renderer. Blank or '?' on the treatment alone indicts "
                 "the archive/encoding seam, with the control proving the rig.",
        steps=_quest_name_authored_steps(o),
        note="RUN WITH --exe pointing at a client whose ARCHIVE holds record "
             "200: vault/run/reskin-roster/Gw.exe (the original, --map 449) "
             "or, since SLICE-B9, vault/run/slice/Gw.exe with RURIK_DAT at "
             "its Gw.dat (`compose.py --name slice --verify` prints the "
             "recipe). The default run archive resolves 100552 to an empty "
             "record and the treatment arm would measure the wrong thing. "
             "Agent-pilotable (fixed-position tracker, no "
             "clicks): actions '0:play', cadence shots, hold ~60 s. "
             "ANSWERED 2026-08-19, agent-piloted (harness 20260819T085654): "
             "control tracker 'Ascalon:' + toast 'Quest Added: Ascalon'; "
             "treatment tracker 'A First Errand: Speak with the scout, then "
             "return.' + toast 'Quest Added: A First Errand' -- BOTH screen "
             "surfaces render the authored record, the tracker switched on "
             "the second add exactly as the last-pushed-becomes-active write "
             "predicts, and the client's own 0x8012 for 1463 was answered "
             "with the template 0x004C mid-run. Rung Q2b closed end to end. "
             "Kept runnable as the authored-name calibration.",
    ),
    "walk_to_npc": lambda a, o: Probe(
        question="Does GAME_SMSG 0x002A walk the client to an NPC, and does "
                 "the held interact fire when it arrives?",
        predicts="Both halves of the 2026-08-19 fix, in one run and with one "
                 "variable. The corpus says 0x002A is the auto-walk order (17 "
                 "name the player's agent, 16 within a round trip of the "
                 "interact naming the agent walked to) and that ArenaNet "
                 "answers an out-of-range interact LATE rather than dropping "
                 "it. So: the character should run ~900 u to the NPC, and the "
                 "gamesrv log should print 'HOLDING' and then 'ARRIVES' about "
                 "2.3 s later, with the dialog opening on arrival. A missing "
                 "'ARRIVES' line refutes it cleanly -- the old behaviour and "
                 "the new one differ in exactly that line.",
        steps=_walk_to_npc_steps(o),
        note="RUN ON --map 449. Agent-pilotable and CLICK-FREE by "
             "construction: the interact is driven through "
             "toolkit/harness/control.py request_interact(99), not a mouse, so "
             "nothing here aims at anything. The last step sends no packet -- "
             "it carries the operator/driver instruction. Watch the GAMESRV "
             "LOG first and the screen second; the log lines are the "
             "measurement and the walking character is the corroboration.",
    ),
    "completion_panel": lambda a, o: Probe(
        question="Was 0x0097's crash the MAP rather than the payload -- and "
                 "does 0x0098 stage the reward lines it consumes?",
        predicts="Arm 1 sends the exact payload that crashed at "
                 "GmQuestComplete.cpp:678 on 2026-08-19, unchanged, on a "
                 "world-4 map, and does NOT assert -- because the switch at "
                 ":678 reads s_missionClientData[map]+0x4 (cases {2,4,5}), "
                 "never the record. Arms 2-3 then prove 0x0098 is the "
                 "reward-line append: one push, then a consume, should draw "
                 "a reward line carrying 111/222/333, and a second pair with "
                 "type tag 4 (isSimpleReward, exactly ONE element or :246 "
                 "fires) should render 444/555/666 differently if the tag "
                 "reaches the render. A :678 crash on arm 1 refutes the whole "
                 "correction and FINDINGS 9.8's stash reading stands.",
        steps=_completion_panel_steps(),
        note="MUST RUN WITH --map 449. The map IS the experiment: 449 is "
             "world 4, and the client's own mission table gates the panel on "
             "{2,4,5}. Do NOT use the default map or 146/148/143 (world 1) -- "
             "that is what the superseded run did. Agent-pilotable, no "
             "clicks: actions '0:play', --shots 1 --hold 90.",
    ),
    "completion_rewards": lambda a, o: Probe(
        question="Does 0x0096's tag-4 simple-reward triple render its "
                 "sentinels, and what does a cold 0x0097 do?",
        predicts="Arm 1 draws the mission-complete scene (proven repeatable "
                 "by 20260819T094757's arms 1-2) PLUS a reward line reading "
                 "111/222/333 in some order -- the order names f3/f4/f5, "
                 "remembering the handler builds {4, f3, f5, f4}. Arm 2 "
                 "(0x0097 cold) renders text or dies on the closed-enum/"
                 "null-stash gate with an assert naming it; either is the "
                 "answer and the run may end there.",
        steps=_completion_reward_steps(),
        note="Caged loopback, any map, no clicks, actions '0:play', "
             "--shots 1 --hold 60. The follow-up to completion_gates, whose "
             "arm-3 crash (GmQuestComplete.cpp:729 -- the gate answer) "
             "blocked these two arms; here the known-safe mission bit rides "
             "with the triple so nothing crashes before the readout.",
    ),
    "completion_gates": lambda a, o: Probe(
        question="Which field feeds 0x0096's completion-flag gate, and does "
                 "the tag-4 simple-reward triple render its sentinels?",
        predicts="Arms 1-3 survive (either 2-bit mask satisfies the gate, "
                 "since the handler forwards both and the sweep's assert "
                 "named 'two flag bits' without naming a field); arm 4 draws "
                 "a reward line reading 111/222/333, naming f3/f4/f5; arm 5 "
                 "(0x0097 cold, LAST) either renders text or dies on the "
                 "closed-enum/null-stash gate with an assert that names it. "
                 "Every survival and every crash placement is a measurement; "
                 "an early death simply moves the answer earlier.",
        steps=_completion_gate_steps(),
        note="Caged loopback, any map, no clicks -- the frames land in "
             "GmQuestComplete's band like quest_panel's do. Cadence shots "
             "(--shots 1 --hold 90), actions '0:play'. Read the gamesrv log "
             "for which arms LANDED before reading any pixel: a crash ends "
             "the run and the surviving-arm count is the gate map. Expect "
             "asserts; they are answers here, not failures.",
    ),
    "compass_quest": lambda a, o: Probe(
        question="PLAN C4's two untouched arms: does 0x0049 draw a quest marker "
                 "on the compass, and is 0x008D really the null it is predicted "
                 "to be?",
        predicts="0x008D draws NOTHING and 0x0049 draws a GREEN STARBURST at "
                 "the player's own position, plus a quest-log entry. The order "
                 "matters and is deliberate: the control goes FIRST, so that if "
                 "a glyph appears after 0x0049 there is already a clean frame "
                 "proving 0x008D did not put it there.",
        steps=_compass_quest_steps(),
        note="MAP 148 ONLY -- the vec2 is that map's spawn in ABSOLUTE world "
             "units. Note the unit differs from the compass draw arm, whose "
             "knots are world/96; using the cell pair here would place the "
             "marker 96x too close to the origin and look like a null.",
    ),
}
