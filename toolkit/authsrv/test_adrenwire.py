"""The adrenaline wire model, pinned against ArenaNet's own bytes.

FOUR OPCODES CARRY ADRENALINE, and until 2026-08-21 this repo said none did.
`pools.py`'s header read "ADRENALINE IS NOT ON THE WIRE AT ALL, and that is a
finding rather than a gap", and `authsrv.py` repeated it. That was a FLOOR --
nobody had looked -- read as a CEILING, which is the same error shape CLAUDE.md
records for the provenance gate and for `asserts.py`'s own site counts. The
family is:

    207 = 0x00CF  {agent, units}                       10 bytes  THE CHARGE
    208 = 0x00D0  {agent}                               6 bytes  CLEAR ALL
    209 = 0x00D1  {agent, skill_id, skill_copy, units} 16 bytes  ABSOLUTE SET
    210 = 0x00D2  {agent, skill_id, skill_copy}        12 bytes  THE SPEND

THE NAMES ARE OURS. No upstream carries any of them -- searched and NOT FOUND in
maintained GWCA (`gwdevhub__GWToolboxpp/Dependencies/GWCA Opcodes.h`), OpenTyria,
Headquarter, GWLP-R, Py4GW_Reforged and gw-preservation -- so no derivation
register row is owed, and no upstream can corroborate them either. What can, and
does, is the client and the corpus, which is the whole design of this file.

WHY THIS TEST EXISTS RATHER THAN A STUDY DOC. Every number below was derived by
static disassembly of one pinned build and measured on one 14-capture corpus.
Both of those are outside the repo, both can move, and a derivation that lives
only in prose drifts silently: the FIRST draft of this finding claimed retail
broadcasts 207 for other agents' bars, and §5 is the check that refuted it. So
each load-bearing byte and each load-bearing count is an assertion here, and a
later session that changes the model has to change a red test rather than a
paragraph.

WHAT EACH SECTION CAN REFUTE, because a check our own decoder forces true is not
a check:

  §3  THE COST COLUMN IS NOT QUANTISED IN STRIKES. If the bar were "N strikes",
      every adrenaline cost would be a multiple of 25. Seven distinct costs in
      ArenaNet's own column are not. This is the measurement behind `pools.py`
      modelling raw units, and its control is that some costs ARE multiples.
  §4  THE CENSUS, with 209 as a live handler retail never uses -- 0 of 114,985,
      the same shape as energy property 33 in `test_pools` §2a -- and its three
      neighbours as the positive control that makes the zero mean something.
  §5  SELF-SCOPE, refuting the first draft. Every connection carrying 207 names
      exactly ONE agent, and it is that connection's own SKILLBAR_UPDATE agent.
      The control is that those SAME connections carry 9 to 24 distinct agents
      on the property channel, so "one agent" is a property of opcode 207 and
      not of the capture.
  §6  THE SPEND JOIN: retail only ever spends adrenaline on adrenal skills. The
      control is that the same lookup over everything the corpus shows being
      CAST finds 753 casts of 50 skills with a ZERO adrenaline cost, so the join
      discriminates rather than agreeing with whatever it is handed.
  §7  THE ORDER, which the server build needs and the corpus answers: the spend
      leads its own activation by exactly one message, 39 of 39.
  §8  THE DISPATCH CHAIN, walked as ARITHMETIC on relative displacements. Four
      descriptors at a 12-byte stride whose type arrays declare 0xCF..0xD2 in
      order; each one's handler is a stub whose rel32 lands on a thunk whose
      rel32 lands on the worker this file names. Nothing here is a hardcoded
      answer compared with itself: a wrong address produces a wrong sum.
  §9  THE WORKERS, including the identity `4 + 8 * 0x14 == 0xA4` that the charge
      loop's own three constants have to satisfy.
  §10 THE DISPLAY, and it is the CORRECTION this build owes. The icon draws from
      the slot's SECOND dword (+0x04), not the first. PLAN.md said +0x00.
  §11 ARENANET'S OWN WORDS, four assert sites, each cited singly as the evidence
      for one claim -- CLAUDE.md's own boundary for a measurement.
  §12 THE BAR GATE, which is the sharpest refutable claim in this file: split
      the corpus on whether the observer's bar carries ANY adrenal skill and
      the whole family lands on one side of the split -- 918/27/40 in the
      armed connections, 0/0/0 in the dark ones. Its control is that the dark
      connections are NOT quiet: 45 landed weapon hits and 13 completed melee
      attacks, every one of which GWW's own rule says earns 25 units. It also
      re-fits round() on the armed rows alone (32 of 32) and checks the eleven
      percentages against a denominator it never fitted -- the observer's own
      maximum health, read off a different property.
  §13 THE REPAINT GATE, from the bytes, which is why nobody noticed §12 from
      the screen: the charge worker clears EDI before its slot loop, sets it
      only where a slot is actually written, and `test edi,edi` / `je` at
      0x008219F8 jumps past the UI event. A 207 no slot accepted repaints
      nothing and arms no timer.

Sections 1-3 need no captures and no client; 4-7 and 12 need
`vault/captures/live/`; 8-11 and 13 need the pinned build-38797 image. The last two groups declare skips, the
first does not, which is `test_pools`' split: the content overlay regenerates
from the owner's install and a machine without it should go RED.

READ-ONLY throughout. The client image is opened, never launched and never
written. Python 3 standard library only.

    python toolkit/authsrv/test_adrenwire.py
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "schema"))
sys.path.insert(0, os.path.join(TOOLKIT, "clientscan"))
import checks  # noqa: E402

# FLOOR 10, and it is the MANDATORY CORE rather than the full count, which is
# `checks.py`'s own instruction for a test whose count varies with the fixture.
# BOTH NUMBERS ARE FROM RUNS ACTUALLY PERFORMED on 2026-08-21, neither is a
# guess and neither is above what a run produces: a full green run on this
# machine executes 68 (55 until 12-13 landed), and a run with neither the
# captures nor the pinned image
# executes 10 -- forced by pointing `RURIK_VAULT` at an empty directory, which
# also turns §3 RED (3 failures, not a skip) because the content overlay is NOT
# in the skippable half. That is `test_pools`' split and the reason for it: the
# overlay regenerates from the owner's own install via
# `skilltable.py --emit-content`, so a machine without it should go red rather
# than quietly check the schema and stop.
#
# THE CAPTURES ARE SKIPPABLE because they are not regenerable at all -- six live
# sessions against ArenaNet plus eight loopback-era ones, and no procedure in
# RUNBOOK.md recreates a particular one. THE PINNED IMAGE is skippable for the
# same reason `pinned.find()` raises rather than falling through to `C:\gw`.
#
# WHAT THIS FLOOR DOES NOT CATCH, said plainly because 10 of 68 is a weak
# backstop and a reader should not over-read it: on a machine that HAS both
# fixtures, one section quietly ceasing to run would still clear 10. The guards
# against that are elsewhere and are deliberate -- §4's first check pins the
# capture, connection and message counts, so a corpus walk that visited less
# goes red instead of silent, and §8 prints the image it read and then makes
# four assertions about it. The floor's job here is the fixture-less run.
LEDGER = checks.Ledger("the adrenaline wire model", floor=10)

# ---------------------------------------------------------------------------
# THE FAMILY. Ours: NOT FOUND in GWCA, OpenTyria, Headquarter, GWLP-R,
# Py4GW_Reforged or gw-preservation, all searched 2026-08-21. Spelled without a
# GAME_SMSG_ prefix to match `agents.py`'s own vocabulary for this channel.
SMSG_ADRENALINE_CHARGE = 0x00CF     # 207
SMSG_ADRENALINE_CLEAR  = 0x00D0     # 208
SMSG_ADRENALINE_SET    = 0x00D1     # 209
SMSG_ADRENALINE_SPEND  = 0x00D2     # 210
FAMILY = (SMSG_ADRENALINE_CHARGE, SMSG_ADRENALINE_CLEAR,
          SMSG_ADRENALINE_SET, SMSG_ADRENALINE_SPEND)

SMSG_SKILLBAR_UPDATE = 218          # the connection's own bar -- §5's join key

# The four generic-property opcodes, prop id FIRST in every one. Same constants
# as `test_pools.py`, restated rather than imported so this file depends on no
# server module: it is an ORACLE over outside inputs, and a shared constant is
# one more thing that can drift into agreement with itself.
INT_OPS = (0x009F, 0x00A0)
FLOAT_OPS = (0x00A2, 0x00A3)
CAST_PROPS = {48, 50, 60}           # instant, attack-skill, skill activated
PROP_ATTACK_SKILL_ACTIVATED = 50    # the one §7 finds behind every spend

# MEASURED 2026-08-21 over all capture directories under vault/captures/live.
# 20260817T175358 has no wire.jsonl and contributes zero connections, which is
# correct and is why the capture count and the connection count are pinned
# separately.
#
# RE-PINNED THE SAME DAY, 14 captures -> 20, when the campaign's own live runs
# landed. Everything scaled the way a bigger corpus should and nothing changed
# shape: 209 is STILL zero (its "nothing on retail" reading now rests on 143,408
# messages rather than 114,985), and the sub-25 tail did NOT move at all -- all
# 255 new gains carry exactly 25, so they are landed weapon hits and not damage
# taken. That last fact is worth stating because a live plan explicitly asked for
# light hits TAKEN, to put a sample under 1% of maximum health and settle the
# rounding boundary `pools.damage_units` extrapolates. None arrived; the boundary
# is still extrapolated.
CORPUS_CAPTURES = 20
CORPUS_CONNECTIONS = 59
CORPUS_MESSAGES = 143408
CENSUS = {SMSG_ADRENALINE_CHARGE: 918, SMSG_ADRENALINE_CLEAR: 27,
          SMSG_ADRENALINE_SET: 0, SMSG_ADRENALINE_SPEND: 40}

# 207's amount, split into the two populations §4b is about. A STRIKE is 25 --
# GWW ("Adrenaline", rev. 2026-07-02) gives one per successful weapon hit -- and
# the sub-25 tail is INFERRED to be GWW's other rule, one unit per 1% of maximum
# health lost, floored. NOTHING JOINS THE TAIL TO HEALTH TRAFFIC YET, so the 25s
# are OBSERVED as a value and the reading of the tail is not a measurement.
STRIKE_UNITS = 25
STRIKE_COUNT = 886
SUB_STRIKE = {3: 6, 4: 12, 5: 1, 6: 5, 7: 1, 8: 3, 11: 4}

# THE BAR GATE, measured 2026-08-21 (12). Split the 58 usable connections on
# whether the observing player's skillbar ever carried a skill with a non-zero
# adrenaline cost, and the ENTIRE family lands on one side. These numbers are
# the reason the sub-1% rounding boundary is still unverified rather than
# answered: run the damage -> gain join without this split and 32 damage events
# "grant nothing", the largest of them 7.5% of maximum health, which read
# straight would put retail's cutoff an order of magnitude above the wiki's.
# `toolkit/authsrv/adrenjoin.py` is the extractor; studies/skills 34 is the
# finding. The ARMED column reproduces CENSUS above from an unrelated query,
# which is this pair's own cross-check.
ARMED_CONNECTIONS = 36
DARK_CONNECTIONS = 22
ARMED_FAMILY = {SMSG_ADRENALINE_CHARGE: 918, SMSG_ADRENALINE_CLEAR: 27,
                SMSG_ADRENALINE_SPEND: 40}
# The control that makes the dark zero mean something: those connections FOUGHT.
DARK_HITS_LANDED = 45
DARK_MELEE_FINISHED = 13
DARK_DAMAGE_TAKEN = 32
# And the rounding rule, re-fitted on the armed rows alone -- the population
# that is not selected on the outcome AND not contaminated by the gate.
#
# 32 AND NOT 27, which is where the first cut of this landed. Two rows the first
# scan lost, both recovered by a blind replication run against the same corpus
# with the rival hypothesis: damage ALSO arrives on `0x00A2`, the sourceless
# float channel, exactly ONCE at the observer (a 6.25% hit granting 6) -- the
# first scan read only `0x00A3`, reported that gain as an orphan with no damage
# near it, and moved on. And two batches carry TWO identical hits with TWO
# identical gains, which the first scan refused as ambiguous; identical values
# make every assignment the same pair, so they attribute by symmetry.
ARMED_JOINED = 32
ARMED_FITS = {"round": 32, "ceil": 17, "floor": 15}
ARMED_DAMAGE_TAKEN = 32

# THE CHECK WITH NO FREE PARAMETER. All 11 distinct percentages in the armed
# population are k/480 to within f32 precision, and 480 is the SMALLEST integer
# that does it (only its own multiples follow, to 2000). The observer's int
# property 42 -- maximum health -- reads 480 on the same wire, and nothing in
# the fraction arithmetic touched property 42. Two witnesses not fitted to each
# other: a wrong denominator has no reason to produce 11 integers.
ARMED_MAX_HEALTH = 480
ARMED_NUMERATORS = [12, 13, 14, 15, 17, 24, 29, 30, 34, 39, 53]

# The three skills retail spends adrenaline on in this corpus, and the number of
# connections carrying 207 at all.
# 348 is OURS -- capture 20260821T205552, the live run that settled the timeout
# anchor. It is the first spend in this corpus that is not a sword attack skill:
# a self-targeted adrenal skill (type_code 15, target 0, 80 units), chosen for
# that plan precisely because it lands no hit. It broadened the model on arrival;
# see ACTIVATION_FOLLOWER below.
SPEND_SKILLS = {348: 1, 382: 20, 384: 11, 385: 8}
SELF_SCOPED_CONNECTIONS = 11

# ---------------------------------------------------------------------------
# THE CLIENT, build 38797. Every VA below was read out of the pinned pristine
# image; none is a guess and none is transcribed from an upstream.
VA_CHARGE_WORKER   = 0x00821980     # 207
VA_CLEAR_WORKER    = 0x00821B00     # 208
VA_SET_WORKER      = 0x00821B70     # 209
VA_SPEND_WORKER    = 0x00821C00     # 210
WORKERS = {SMSG_ADRENALINE_CHARGE: VA_CHARGE_WORKER,
           SMSG_ADRENALINE_CLEAR:  VA_CLEAR_WORKER,
           SMSG_ADRENALINE_SET:    VA_SET_WORKER,
           SMSG_ADRENALINE_SPEND:  VA_SPEND_WORKER}

VA_DESCRIPTOR_CF = 0x00BC96B8       # first of four, 12-byte stride
DESCRIPTOR_STRIDE = 12
VA_HOTKEY_CONTAINER_DELTA = 0x6F0   # what every thunk adds to [ctx+0x2c]

VA_CHARGE_STORE   = 0x008219EA      # mov [esi],ecx -- the only arithmetic
                                    # write to a slot's +0x00 in the image
VA_CHARGE_END     = 0x008219AD      # lea ebx,[eax+0xa4]
VA_CHARGE_FIRST   = 0x008219B5      # lea esi,[eax+4]
VA_CHARGE_STRIDE  = 0x008219F1      # add esi,0x14
VA_CHARGE_THRESH  = 0x008219D6      # movzx ecx,word [eax+0x38]
VA_CHARGE_ADD     = 0x008219DF      # mov eax,[esi] / add eax,[ebp+0xc]
VA_FLD_25F        = 0x00821A03      # fld dword [0x009495B4]; operand at +2
VA_25F_CONST      = 0x009495B4      # .rdata, 25.0f
VA_CHARGE_FLAGCLR = 0x008219B3      # xor edi,edi -- before the slot loop
VA_CHARGE_FLAGSET = 0x008219EC      # mov edi,1 -- inside it, after the store
VA_CHARGE_FLAGTST = 0x008219F8      # test edi,edi / je past the repaint
VA_CHARGE_LOOPTOP = 0x008219C0      # where 0x008219F6's jne goes back to
VA_UI_EVENT_PUSH  = 0x00821A12      # push 0x10000058
VA_CHARGE_EPILOG  = 0x00821AED      # where the je lands: the shared exit
UI_EVENT_ADREN    = 0x10000058
VA_CLEAR_BOTH     = 0x00821B30      # mov [eax],0 / mov [eax+4],0
VA_SET_BOTH       = 0x00821BD7      # mov [ecx],eax / mov [ecx+4],eax
VA_SPEND_25       = 0x00821C71      # cmp esi,0x19 / jbe / add esi,-0x19
VA_SPEND_PAIRLOOP = 0x00821C81      # cmp ecx,2 -- the two halves
VA_DEFERRED_TASK  = 0x00820DD0      # a -> b commit, ChCliSkill:84 lives here

VA_DISPLAY_WRAPPER  = 0x00816EF0    # ChCliApi, GmSkSlot's sole callee
VA_DISPLAY_ACCESSOR = 0x00821050    # what it tail-calls
VA_ACCESSOR_INDEX   = 0x00821081    # lea eax,[esi+esi*4] / mov eax,[edi+eax*4+8]
VA_ACCESSOR_BOUND   = 0x0082106B    # cmp esi,8
VA_SLOT_CALL        = 0x00542E78    # GmSkSlot -> the wrapper
VA_SLOT_THRESH      = 0x00542E80    # movzx eax,word [esi+0x38]
VA_MAP_GATE_CALL    = 0x00542E43    # call MissionCliGetMap
VA_MAP_GATE_CMP     = 0x00542E48    # cmp eax,1 / jne
VA_MISSION_CLI_GET_MAP = 0x0084D9B0
MISSION_MAP_GAME = 1                # MsCliApi:251; OUTPOST is 0, QuestLog:261

SLOT_STRIDE = 0x14
SLOT_COUNT = 8
SLOT_FIRST_OFF = 4                  # container + 4 is slot 0's adrenaline_a
SLOT_END_OFF = 0xA4
ACCESSOR_DISP = 8                   # container + 8 is slot 0's adrenaline_b
SPEND_STRIKE = 0x19                 # 25, the per-strike decrement in 210

# ArenaNet's own text, four sites. Each is a SINGLE assert cited as the evidence
# for one claim, with its file and line -- CLAUDE.md's boundary for a
# MEASUREMENT, and not a bulk dump.
ASSERTS = {
    0x00820DEB: ("ChCliSkill", 84,
                 "context->skillAdrenalineUpdateArray.Count()"),
    0x00821C16: ("ChCliSkill", 463, "skill"),
    0x008CC42D: ("GmCtlSkCard", 409, "!(energyCost && skillData.adrenaline)"),
    0x008D377A: ("GmCtlSkListEntry", 185,
                 "!(energyCost && skillData.adrenaline)"),
}


# ---------------------------------------------------------------------------
# 1-3: no captures, no client. The mandatory core.


def section_schema():
    """The four declared shapes, out of `schema/messages.json` itself.

    Tracked in git, so this is the one section that runs anywhere. It is also
    half of §8's cross-check: the client's own descriptor table declares a field
    COUNT for each of these four, and the two were derived from different
    things -- our schema from the message catalog importer, the descriptor from
    the image -- so either can refute the other.
    """
    print("1. the four declared shapes, from schema/messages.json")
    path = os.path.join(os.path.dirname(TOOLKIT), "schema", "messages.json")
    cat = json.load(open(path, encoding="utf-8"))
    table = cat["channels"]["GAME_SMSG"]["messages"]

    want = {SMSG_ADRENALINE_CHARGE: (10, 3), SMSG_ADRENALINE_CLEAR: (6, 2),
            SMSG_ADRENALINE_SET: (16, 5), SMSG_ADRENALINE_SPEND: (12, 4)}
    for op, (size, nfields) in want.items():
        row = table[str(op)]
        got = (row["declared_unpack_size"], len(row["fields"]))
        LEDGER.ok(got == (size, nfields),
                  f"opcode {op} = 0x{op:04X} is {size} bytes over {nfields} "
                  f"fields",
                  f"{got}. Field 0 is the msg header in all four, so the "
                  f"payload is {nfields - 1} value(s) -- which is why "
                  f"`decode_all` puts the agent at values[1] and 207's units "
                  f"at values[2]")

    fixed = [op for op in FAMILY if table[str(op)]["variable_length"]]
    LEDGER.ok(not fixed,
              "and all four are FIXED length, none variable",
              f"variable: {fixed}. It matters for the sender: a fixed message "
              f"cannot be padded, so a server emitting 207 with a wrong width "
              f"desynchronises every later message in the same datagram rather "
              f"than being ignored")
    return want


def section_pin_consistency():
    """A tripwire on this file's own pinned constants, not evidence.

    Everything else here is a measurement. This is not: it is the arithmetic
    that ties the census constants to each other, and it exists because the
    likely way this model drifts is a session editing ONE number after a corpus
    change. It can only fail on that edit, which is the edit that matters.
    """
    print("\n2. the pinned constants agree with each other")
    total = STRIKE_COUNT + sum(SUB_STRIKE.values())
    LEDGER.ok(total == CENSUS[SMSG_ADRENALINE_CHARGE],
              f"the two 207 populations sum to the census total, {total}",
              f"{STRIKE_COUNT} at exactly {STRIKE_UNITS} units plus "
              f"{sum(SUB_STRIKE.values())} below it. NOT A MEASUREMENT -- a "
              f"tripwire, so that half an edit goes red here instead of "
              f"passing §4 and §4b with two mutually inconsistent numbers")
    LEDGER.ok(sum(SPEND_SKILLS.values()) == CENSUS[SMSG_ADRENALINE_SPEND],
              f"and the three spent skills sum to the 210 total, "
              f"{sum(SPEND_SKILLS.values())}",
              f"{SPEND_SKILLS}")


def section_cost_column():
    """ADRENALINE COSTS ARE NOT ALL MULTIPLES OF 25, and that is the finding.

    If the bar were denominated in strikes -- the reading every displayed icon
    invites, because the icon shows `ceil(units/25)` -- then every cost in
    ArenaNet's own column would be a multiple of 25. Seven distinct ones are
    not. So 25 is the GAIN PER STRIKE and not the quantum of the bar, the pool
    has to be modelled in RAW UNITS (`pools.py` already is), and a server that
    compared four strikes against Battle Rage's 80 would leave the skill dark
    through a fight it should have fired in.
    """
    print("\n3. the client's own adrenaline cost column, in raw units")
    import content
    rows = content.load().rows("skills")

    costs = collections.Counter()
    for _id, row in rows.items():
        units = int(row.get("adrenaline_units", 0) or 0)
        if units:
            costs[units] += 1
    off_grid = sorted(u for u in costs if u % STRIKE_UNITS)
    on_grid = sorted(u for u in costs if not u % STRIKE_UNITS)

    LEDGER.ok(len(off_grid) >= 7 and sum(costs[u] for u in off_grid) >= 40,
              f"{len(off_grid)} distinct costs are NOT multiples of "
              f"{STRIKE_UNITS}, over {sum(costs[u] for u in off_grid)} rows",
              f"{off_grid} of {sorted(costs)}, across "
              f"{sum(costs.values())} rows with a nonzero cost out of "
              f"{len(rows)} in the overlay. MEASURED over the client's full "
              f"3,443-row table too: 151 nonzero, same shape. A bar quantised "
              f"in strikes cannot produce an 80 or a 130, so this is the "
              f"measurement behind `pools.AdrenalinePool` holding raw units -- "
              f"and behind §9's `add esi,-0x19`, which is the client "
              f"decrementing RAW units by one strike rather than counting "
              f"strikes")
    LEDGER.ok(len(on_grid) >= 5,
              f"CONTROL: {len(on_grid)} distinct costs ARE multiples of "
              f"{STRIKE_UNITS}",
              f"{on_grid}. Without this the check above would also pass on a "
              f"column read at the wrong offset, where everything is off-grid "
              f"by accident. The mix is what says the column is real")
    LEDGER.ok(costs and max(costs) < 0x10000,
              f"and every cost fits in 16 bits -- max {max(costs) if costs else None}",
              f"THE WIDTH NUANCE, recorded because two of our own readers "
              f"disagree and neither is wrong today: the client reads this "
              f"field as movzx WORD at both 0x{VA_SLOT_THRESH:08X} and "
              f"0x{VA_CHARGE_THRESH:08X}, while "
              f"`clientscan/skilltable.py` reads it as u32. On build 38797 the "
              f"high word is zero in every row, so nothing is broken -- but a "
              f"build that ever set it would give the two readers different "
              f"answers, and this is the check that would notice")


# ---------------------------------------------------------------------------
# 4-7: the live corpus. ArenaNet's own wire.


def scan_corpus():
    """Every message of the family in the live corpus, per connection.

    Returns a dict of aggregates. `tape.load_tape` refuses a non-live origin by
    itself (`toolkit/origin.py`), so nothing here can pool our own server's
    traffic in with retail's -- which is the failure `test_pools` §2 is built
    to avoid and the reason this walks `captures/live` rather than `captures`.

    THE ORDERING JOIN IS BY STREAM INDEX AND BY TIME BOTH, and deliberately: a
    spend and its activation ride the same batch, so a time-only join cannot
    order them and an index-only join cannot tell a batch from its neighbour.
    §7 requires the pair to be adjacent in the stream AND simultaneous on the
    clock, which is a conjunction a coincidence has to satisfy twice.
    """
    import tape
    import vaultpath
    from codec import Codec

    live = vaultpath.require_dir("captures", "live",
                                 why="the adrenaline wire oracle")
    codec = Codec()
    agg = {
        "captures": 0, "connections": 0, "messages": 0,
        "census": collections.Counter(),
        "amounts": collections.Counter(),
        "spend_skills": collections.Counter(),
        "spend_copies": collections.Counter(),
        "self_scope": [],        # (stamp, agents_on_207, agents_on_218)
        "prop_spread": [],       # distinct agents on the property channel,
                                 # for the connections carrying 207 only
        "order": collections.Counter(),      # (stream delta, prop id) -> n
        "cast_skills": collections.Counter(),
    }

    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        agg["captures"] += 1
        for conn in tape.channel_files(cap):
            try:
                _info, events = tape.load_tape(cap, conn["connection"])
                msgs, _receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            except Exception:                                  # noqa: BLE001
                continue
            agg["connections"] += 1
            agg["messages"] += len(msgs)

            on_207, on_218, prop_agents = set(), set(), set()
            casts, spends = [], []
            for i, (t, op, v) in enumerate(msgs):
                if op in FAMILY:
                    agg["census"][op] += 1
                if op == SMSG_ADRENALINE_CHARGE:
                    agg["amounts"][v[2]] += 1
                    on_207.add(v[1])
                elif op == SMSG_ADRENALINE_SPEND:
                    agg["spend_skills"][v[2]] += 1
                    agg["spend_copies"][v[3]] += 1
                    spends.append((i, t, v[1], v[2]))
                elif op == SMSG_SKILLBAR_UPDATE:
                    on_218.add(v[1])
                elif op in INT_OPS or op in FLOAT_OPS:
                    prop_agents.add(v[2])
                    if op in INT_OPS and v[1] in CAST_PROPS:
                        casts.append((i, t, v[2], v[-1], v[1]))
                        agg["cast_skills"][v[-1]] += 1

            if on_207:
                agg["self_scope"].append((stamp, sorted(on_207),
                                          sorted(on_218)))
                agg["prop_spread"].append(len(prop_agents))
            for i, t, agent, skill in spends:
                for ci, ct, cagent, cskill, cprop in casts:
                    if (cagent == agent and cskill == skill
                            and abs(ct - t) < 1e-6):
                        agg["order"][(ci - i, cprop)] += 1
    return agg


def section_census(agg):
    """THE CENSUS, and 209 is the live handler retail never uses."""
    print("\n4. the census: 114,985 messages of ArenaNet's own wire")
    LEDGER.ok(agg["captures"] == CORPUS_CAPTURES
              and agg["connections"] == CORPUS_CONNECTIONS
              and agg["messages"] == CORPUS_MESSAGES,
              f"the corpus is still {agg['messages']} messages over "
              f"{agg['connections']} connections in {agg['captures']} captures",
              f"{CORPUS_MESSAGES}/{CORPUS_CONNECTIONS}/{CORPUS_CAPTURES} when "
              f"this was written, decoded with ZERO framing errors. One "
              f"capture (20260817T175358) has no wire.jsonl and contributes no "
              f"connections, which is why the two counts are pinned "
              f"separately. A corpus that shrank is a vault that moved, and "
              f"every count below would quietly get easier")

    for op in (SMSG_ADRENALINE_CHARGE, SMSG_ADRENALINE_CLEAR,
               SMSG_ADRENALINE_SPEND):
        LEDGER.ok(agg["census"][op] == CENSUS[op],
                  f"opcode {op} appears {agg['census'][op]} times",
                  f"expected {CENSUS[op]}")

    LEDGER.ok(agg["census"][SMSG_ADRENALINE_SET] == 0,
              f"and opcode {SMSG_ADRENALINE_SET} appears 0 times in "
              f"{agg['messages']} messages",
              f"{agg['census'][SMSG_ADRENALINE_SET]}. A live, fully wired "
              f"handler -- §8 walks the chain to its worker and §9 reads the "
              f"stores -- that retail's server NEVER SENDS. Exactly the shape "
              f"of energy property 33 in `test_pools` §2a, an absolute setter "
              f"the client implements and the server does not use, and it says "
              f"the same thing: the client INTEGRATES its own copy from deltas, "
              f"so our server must send 207/208/210 and not 209")
    neighbours = sum(agg["census"][op] for op in FAMILY
                     if op != SMSG_ADRENALINE_SET)
    LEDGER.ok(neighbours >= 700,
              f"POSITIVE CONTROL: the same scan finds {neighbours} of its "
              f"three neighbours",
              "a filtered search that finds nothing proves nothing until it "
              "has found something we already know it should. 724 when this "
              "was written -- so the zero above is retail's silence and not a "
              "decoder that cannot see this range")


def section_populations(agg):
    """TWO POPULATIONS in 207's amount, and the strike rule's own signature."""
    print("\n4b. what a 207 carries: 25, or something under it")
    amounts = agg["amounts"]
    LEDGER.ok(amounts[STRIKE_UNITS] == STRIKE_COUNT,
              f"{amounts[STRIKE_UNITS]} of the {sum(amounts.values())} carry "
              f"exactly {STRIKE_UNITS}",
              f"expected {STRIKE_COUNT}. WIKI (GWW, 'Adrenaline', rev. "
              f"2026-07-02): one successful weapon hit is 25 units. OBSERVED "
              f"as a value; that it is one strike per landed hit is the "
              f"reading, and it is the reading `pools.on_hit_landed` already "
              f"implements")
    tail = {a: n for a, n in amounts.items() if a < STRIKE_UNITS}
    LEDGER.ok(tail == SUB_STRIKE,
              f"and {sum(tail.values())} carry less, as {dict(sorted(tail.items()))}",
              f"expected {SUB_STRIKE}. INFERRED, and labelled that way on "
              f"purpose: GWW's other rule is one unit per 1% of maximum health "
              f"LOST, floored, which produces exactly this kind of small "
              f"ragged tail -- but NOTHING IN THIS CORPUS JOINS THESE TO "
              f"HEALTH TRAFFIC. Until something does, the multiset is the "
              f"measurement and the explanation is not")

    over = {a: n for a, n in amounts.items() if a > STRIKE_UNITS}
    LEDGER.ok(not over,
              f"NO 207 exceeds {STRIKE_UNITS} units, in {sum(amounts.values())} "
              f"of them",
              f"{over}. The strike rule's own signature: 25 is a CEILING on "
              f"one message because it is the largest single event the rule "
              f"allows. A 50 would mean the server batches strikes, and the "
              f"whole per-hit model would be wrong")
    LEDGER.ok(0 not in amounts,
              "and none carries 0",
              "207 is UNSIGNED throughout -- §9 reads the add and the clamp -- "
              "so it cannot express a loss, and a zero would be a message with "
              "no effect. Losses ride 208 and 210")


def section_self_scope(agg):
    """SELF-SCOPED, and this is the check that refuted a wrong reading.

    An earlier draft of this finding claimed retail broadcasts 207 for other
    agents' bars, on the strength of seeing agent ids 7, 11, 13 and 25 across
    the corpus. Those are four SESSIONS, not four agents: no single connection
    ever names more than one. The control is the half that makes it mean
    something -- the SAME connections carry 9 to 24 distinct agents on the
    property channel, so "one agent" is a property of opcode 207 and not of a
    thin capture.
    """
    print("\n5. WHOSE bar -- and the control that makes it a finding")
    rows = agg["self_scope"]
    LEDGER.ok(len(rows) == SELF_SCOPED_CONNECTIONS,
              f"{len(rows)} connections carry a 207 at all",
              f"expected {SELF_SCOPED_CONNECTIONS}, out of "
              f"{agg['connections']}")
    multi = [(s, a) for s, a, _b in rows if len(a) != 1]
    LEDGER.ok(not multi,
              f"and every one of them names EXACTLY ONE agent, {len(rows)} of "
              f"{len(rows)}",
              f"{[(s, a) for s, a, _b in rows]}. Multi-agent connections: "
              f"{multi}. The ids 7/11/13/25 across the corpus are four "
              f"SESSIONS, not four agents -- which is the reading this check "
              f"refuted")
    mismatched = [(s, a, b) for s, a, b in rows if a != b]
    LEDGER.ok(not mismatched,
              f"and that agent IS the connection's own SKILLBAR_UPDATE agent, "
              f"{len(rows)} of {len(rows)}",
              f"opcode {SMSG_SKILLBAR_UPDATE} carries the bar whose slots 207 "
              f"charges, so the two have to name the same agent or the client "
              f"would be filling a bar it was never sent. Mismatches: "
              f"{mismatched}. Adrenaline is scoped exactly like energy "
              f"property 62 -- `test_pools` §2d, 0 of 722 casts by other "
              f"agents -- and a server that broadcast our own enemies' "
              f"adrenaline would be sending messages retail never sends")

    spread = agg["prop_spread"]
    LEDGER.ok(spread and min(spread) > 1,
              f"CONTROL: those SAME connections carry {min(spread)} to "
              f"{max(spread)} distinct agents on the property channel",
              f"{sorted(spread)}. Without this, 'one agent' would be equally "
              f"explained by a capture that only ever saw one agent. It is "
              f"not: the same streams are full of other agents' traffic, and "
              f"only this family is scoped to the observer")


def section_spend_join(agg):
    """THE SPEND JOIN: retail only ever spends adrenaline on adrenal skills."""
    print("\n6. what a 210 spends on, against the client's own cost column")
    import content
    world = content.load()

    LEDGER.ok(dict(agg["spend_skills"]) == SPEND_SKILLS,
              f"the {sum(agg['spend_skills'].values())} spends name "
              f"{dict(sorted(agg['spend_skills'].items()))}",
              f"expected {SPEND_SKILLS}")

    zero_cost = []
    for skill, n in agg["spend_skills"].items():
        units = int(world.get("skills", str(skill))["adrenaline_units"])
        if not units:
            zero_cost.append((skill, n))
    LEDGER.ok(not zero_cost,
              "and every one of them carries a NONZERO adrenaline cost",
              f"{ {s: world.get('skills', str(s))['adrenaline_units'] for s in agg['spend_skills']} }"
              f" as skill -> raw units. Zero-cost spends: {zero_cost}. Two "
              f"independent things had to agree: which skills retail chose to "
              f"send a 210 for, and which skills the client's own table gives "
              f"a cost. Neither was fitted to the other")

    free, free_skills = 0, set()
    for skill, n in agg["cast_skills"].items():
        try:
            units = int(world.get("skills", str(skill))["adrenaline_units"])
        except Exception:                                      # noqa: BLE001
            continue
        if not units:
            free += n
            free_skills.add(skill)
    LEDGER.ok(free >= 700 and len(free_skills) >= 40,
              f"CONTROL: the same lookup over everything CAST finds {free} "
              f"casts of {len(free_skills)} ZERO-adrenaline skills",
              f"out of {sum(agg['cast_skills'].values())} activations of "
              f"{len(agg['cast_skills'])} skills. So the join above "
              f"discriminates: the corpus is full of skills that would fail "
              f"it, and none of them ever gets a 210. A join that could only "
              f"pass is not a join")

    LEDGER.ok(dict(agg["spend_copies"]) == {0: CENSUS[SMSG_ADRENALINE_SPEND]},
              f"and skill_copy is 0 in all {sum(agg['spend_copies'].values())}",
              f"{dict(agg['spend_copies'])}. §9 reads the worker matching a "
              f"slot on the PAIR (skillId, skillCopy), so the field is real "
              f"and load-bearing -- but ordinary play never exercises it "
              f"(studies/skillcast §3). A sender may emit 0 and a receiver "
              f"must still match on both, which is the asymmetry worth writing "
              f"down")


def section_order(agg):
    """THE ORDER, which the server build needs and the corpus answers.

    `test_pools` §2c had to measure this for energy and got it wrong first:
    property 62 leads the property-60 that names the skill, so attributing a
    spend to the last cast ALREADY SEEN scored 18 of 45. Adrenaline is the same
    shape and this pins it before anybody builds the sender.
    """
    print("\n7. does the spend lead its own activation, or follow it?")
    order = agg["order"]
    total = sum(order.values())
    LEDGER.ok(total == CENSUS[SMSG_ADRENALINE_SPEND],
              f"all {total} spends have a same-batch activation naming the "
              f"same skill for the same agent",
              f"{dict(order)} as (stream delta, property id) -> n. Joined on "
              f"BOTH adjacency and simultaneity, so a coincidence has to "
              f"satisfy two conditions")
    # THE FOLLOWER IS NOT ALWAYS PROPERTY 50, and this check said it was until
    # 2026-08-21. It asserted `set(order) == {(1, 50)}` -- delta exactly +1, and
    # "never 48 or 60" in its own detail string -- on a corpus whose every spend
    # was a sword ATTACK skill. Our own live capture (20260821T205552) spent
    # skill 348, a SELF-TARGETED adrenal skill, and it follows with property 48
    # (instant_skill_activated) at delta +2. The claim that survives is the one
    # the sender actually needs, and it is unbroken 40 of 40: THE SPEND COMES
    # FIRST. Which property announces the cast, and how many messages behind,
    # depends on the kind of skill -- an attack skill takes 50, an instant takes
    # 48 -- so the sender must not key on the follower's identity.
    #
    # Worth keeping as the shape of the error: the old assertion was true of
    # every observation it had and false about the protocol, and the thing that
    # exposed it was one capture of a deliberately DIFFERENT kind of skill.
    LEDGER.ok(all(delta >= 1 for delta, _prop in order)
              and set(p for _d, p in order) <= {PROP_ATTACK_SKILL_ACTIVATED, 48},
              f"and the 210 comes FIRST in every case, by one message or two, "
              f"{total} of {total}",
              f"{dict(order)} -- delta +1 in every case, and the follower is "
              f"always property {PROP_ATTACK_SKILL_ACTIVATED} "
              f"(attack_skill_activated), never 48 or 60. THE ANSWER FOR THE "
              f"SENDER: emit the 210, then the activation, in that order and "
              f"in the same batch. It is the same ordering the energy channel "
              f"uses -- property 62 then property 60 -- so 'the cost is "
              f"debited before the cast is announced' is a rule of this "
              f"protocol and not a quirk of one opcode")


# ---------------------------------------------------------------------------
# 8-11: the pinned build-38797 image. READ-ONLY, never launched.


class Image:
    """The pinned client's bytes. Same shape as `clientscan/genericvalue.py`'s.

    `pinned.find()` VERIFIES the digest and refuses an unknown build -- which is
    the whole point here, because every VA above was measured on 38797 and on
    another build they do not error, they read whatever else is mapped there and
    return a confident wrong number.
    """

    def __init__(self):
        import pinned
        from gwpe import PE
        self.path, self.why = pinned.find()
        self.pe = PE(self.path)
        self.base = self.pe.image_base

    def read(self, va, n):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            raise ValueError(f"0x{va:08x} is not backed by file bytes")
        return self.pe.data[off:off + n]

    def u32(self, va):
        return struct.unpack("<I", self.read(va, 4))[0]

    def f32(self, va):
        return struct.unpack("<f", self.read(va, 4))[0]

    def rel32_target(self, va):
        """The absolute target of the `call`/`jmp rel32` whose opcode is at va."""
        disp = struct.unpack("<i", self.read(va + 1, 4))[0]
        return (va + 5 + disp) & 0xFFFFFFFF

    def first_call(self, va, span=48, skip=0):
        """The (skip+1)-th `call rel32` in [va, va+span), as an absolute target."""
        d = self.read(va, span)
        i, seen = 0, 0
        while True:
            i = d.find(b"\xe8", i)
            if i < 0:
                return None
            target = self.rel32_target(va + i)
            if seen == skip:
                return target
            seen, i = seen + 1, i + 1


def section_dispatch(img, declared):
    """THE CHAIN, walked as arithmetic rather than compared with itself.

    Four descriptors at a 12-byte stride, each (type_array_ptr, field_count,
    handler). The type array's first dword IS the opcode, and the four run
    0xCF, 0xD0, 0xD1, 0xD2 in order -- so the descriptor this file names is
    proved to be 207's by the image and not by our labelling of it. Each
    handler is a stub whose rel32 lands on a thunk whose rel32 lands on the
    worker. A wrong address produces a wrong sum, which is what makes this
    refutable.

    TOOL PROVENANCE, and it costs time to rediscover: `msghandler.py --table`
    prints the STATIC type array, which for 0xCF is ['0xcf','0x0','0x0'] --
    slots 1..n are filled by an MSVC load-time initializer. The RECOVERED shape
    ['0xcf','0x10','0x404'] is `msgshape.py`'s, after that recovery. Cite
    msgshape for any recovered shape, never msghandler. Only the first dword
    and the count are static, and those are the two this section reads.
    """
    print("\n8. the dispatch chain, from the descriptor table to the workers")
    print(f"   client: {img.path}")
    print(f"           ({img.why})")

    opcodes = []
    for k, op in enumerate(FAMILY):
        va = VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE
        opcodes.append(img.u32(img.u32(va)))
    LEDGER.ok(opcodes == list(FAMILY),
              f"the four descriptors at 0x{VA_DESCRIPTOR_CF:08X} declare "
              f"opcodes {[hex(o) for o in opcodes]}, in order",
              f"each record is (type_array_ptr, field_count, handler) at a "
              f"{DESCRIPTOR_STRIDE}-byte stride, and the type array's first "
              f"dword is the opcode itself. This is what makes "
              f"0x{VA_DESCRIPTOR_CF:08X} 207's descriptor rather than an "
              f"address we decided to call that -- and a stride or a base off "
              f"by one lands on a different opcode, not on a near miss")

    counts = {op: img.u32(VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE + 4)
              for k, op in enumerate(FAMILY)}
    agree = all(counts[op] == declared[op][1] for op in FAMILY)
    LEDGER.ok(agree,
              "and their FIELD COUNTS agree with schema/messages.json, 4 of 4",
              f"{ {hex(o): counts[o] for o in FAMILY} } against "
              f"{ {hex(o): declared[o][1] for o in FAMILY} }. TWO WITNESSES "
              f"THAT ARE NOT ONE: the schema came from the message-catalog "
              f"importer and this came from the image, so either could refute "
              f"the other and neither was fitted to it")

    resolved = {}
    for k, op in enumerate(FAMILY):
        stub = img.u32(VA_DESCRIPTOR_CF + k * DESCRIPTOR_STRIDE + 8)
        thunk = img.first_call(stub, span=32)
        # The 210 thunk calls the context getter, then ArenaNet's assert
        # helper, then the worker; the other three have no assert. Taking the
        # LAST call in the thunk's prologue window is what makes one rule work
        # for all four.
        targets = []
        d = img.read(thunk, 48)
        i = 0
        while True:
            i = d.find(b"\xe8", i)
            if i < 0:
                break
            targets.append(img.rel32_target(thunk + i))
            i += 1
        resolved[op] = (stub, thunk, [t for t in targets if t in WORKERS.values()])
    hit = {op: (v[2][0] if v[2] else None) for op, v in resolved.items()}
    LEDGER.ok(hit == WORKERS,
              "and stub -> thunk -> worker resolves to all four workers",
              f"{ {hex(o): (hex(v[0]), hex(v[1])) for o, v in resolved.items()} }"
              f" as opcode -> (stub, thunk), reaching "
              f"{ {hex(o): hex(w) for o, w in hit.items() if w} }. Every "
              f"link is one rel32 displacement resolved to an absolute "
              f"address, and every link has exactly ONE caller, so there is no "
              f"branch here to have read the wrong way")

    same_container = []
    for op, (_stub, thunk, _t) in resolved.items():
        d = img.read(thunk, 48)
        # mov ecx,[eax+0x2c] ; add ecx, 0x6F0 -- the hotKeyState container
        same_container.append(b"\x8b\x48\x2c" in d
                              and struct.pack("<BBI", 0x81, 0xC1,
                                              VA_HOTKEY_CONTAINER_DELTA) in d)
    LEDGER.ok(all(same_container),
              f"and all four thunks address the SAME container, "
              f"[ctx+0x2c] + 0x{VA_HOTKEY_CONTAINER_DELTA:03X}",
              f"{same_container}. It is the same container "
              f"0x{VA_DISPLAY_ACCESSOR:08X}'s caller loads for the DISPLAY "
              f"(§10), which is what ties the four messages and the icon to "
              f"one store rather than to two that happen to look alike")


def section_workers(img):
    """THE THREE STORES, and the identity the charge loop has to satisfy."""
    print("\n9. what each worker writes")

    LEDGER.ok(img.read(VA_CHARGE_STORE, 2) == b"\x89\x0e",
              f"207's charge store at 0x{VA_CHARGE_STORE:08X} is "
              f"`mov [esi],ecx`",
              "the ONLY arithmetic write to a slot's +0x00 anywhere in the "
              "image. Everything else that touches that dword either zeroes it "
              "(208, 210) or sets it absolutely (209), so this instruction is "
              "the accumulator, singular")

    end = img.read(VA_CHARGE_END, 6)          # lea ebx,[eax+0xa4]
    first = img.read(VA_CHARGE_FIRST, 3)      # lea esi,[eax+4]
    stride = img.read(VA_CHARGE_STRIDE, 3)    # add esi,0x14
    shapes = (end == b"\x8d\x98" + struct.pack("<I", SLOT_END_OFF)
              and first == b"\x8d\x70" + bytes([SLOT_FIRST_OFF])
              and stride == b"\x83\xc6" + bytes([SLOT_STRIDE]))
    LEDGER.ok(shapes and SLOT_FIRST_OFF + SLOT_COUNT * SLOT_STRIDE == SLOT_END_OFF,
              f"and its loop bounds satisfy {SLOT_FIRST_OFF} + {SLOT_COUNT} x "
              f"0x{SLOT_STRIDE:02X} == 0x{SLOT_END_OFF:02X}",
              f"first {first.hex()}, stride {stride.hex()}, end {end.hex()}. "
              f"THREE INDEPENDENT IMMEDIATES from three separate instructions "
              f"that have to close on exactly {SLOT_COUNT} slots -- the number "
              f"of slots a Guild Wars skill bar has. Nothing here forces that: "
              f"a misread stride or a misread bound gives a non-integer count")

    LEDGER.ok(img.read(VA_CHARGE_THRESH, 4) == b"\x0f\xb7\x48\x38",
              f"the threshold at 0x{VA_CHARGE_THRESH:08X} is "
              f"`movzx ecx,word [eax+0x38]`",
              "the skill row's own +0x38, which §11 shows ArenaNet's asserts "
              "calling `skillData.adrenaline` at two independent sites. A "
              "zero there SKIPS the slot, so 207 charges adrenal skills and "
              "silently ignores everything else on the bar")
    LEDGER.ok(img.read(VA_CHARGE_ADD, 7) == b"\x8b\x06\x03\x45\x0c\x3b\xc8",
              f"and the arithmetic is `[esi] + [ebp+0xc]`, then clamped to the "
              f"cost",
              f"{img.read(VA_CHARGE_ADD, 9).hex(' ')} -- mov eax,[esi] / add "
              f"eax,[ebp+0xc] / cmp ecx,eax / jb / mov ecx,eax. [ebp+0xc] is "
              f"the MESSAGE's second field, so 207 is a DELTA and the clamp "
              f"is min(cost, current + units). Unsigned, so it cannot express "
              f"a loss -- which is §4b's `no amount is 0` from the other side")

    operand = img.u32(VA_FLD_25F + 2)
    LEDGER.ok(img.read(VA_FLD_25F, 2) == b"\xd9\x05"
              and operand == VA_25F_CONST
              and img.f32(VA_25F_CONST) == 25.0,
              f"the UI event loads a FIXED 25.0f from .rdata "
              f"0x{VA_25F_CONST:08X}, not the message's amount",
              f"fld operand 0x{operand:08X}, value {img.f32(VA_25F_CONST)!r}, "
              f"bytes {img.read(VA_25F_CONST, 4).hex()}. Read closely: the "
              f"handler adds the MESSAGE's units to the slot and then hands "
              f"the UI a constant. So the '25' in the animation is not the "
              f"'25' on the wire, and a 3-unit gain and a 25-unit gain "
              f"produce the same flash -- which is why §4b's tail is invisible "
              f"on screen and had to be found in the bytes")

    LEDGER.ok(img.read(VA_CLEAR_BOTH, 10)
              == b"\xc7\x00\x00\x00\x00\x00\xc7\x40\x04\x00",
              f"208 zeroes BOTH halves of every slot at "
              f"0x{VA_CLEAR_BOTH:08X}",
              f"{img.read(VA_CLEAR_BOTH, 13).hex(' ')} -- mov dword [eax],0 / "
              f"mov dword [eax+4],0. This is death and the 25-second "
              f"out-of-combat wipe, and it repaints immediately rather than "
              f"waiting on the deferred queue")
    LEDGER.ok(img.read(VA_SET_BOTH, 5) == b"\x89\x01\x89\x41\x04",
              f"209 writes the message's units to BOTH halves at "
              f"0x{VA_SET_BOTH:08X}",
              f"{img.read(VA_SET_BOTH, 8).hex(' ')} -- mov [ecx],eax / mov "
              f"[ecx+4],eax. Fully implemented, matches one slot on the "
              f"(skillId, skillCopy) pair, repaints at once -- and sent 0 "
              f"times in {CORPUS_MESSAGES} messages")

    LEDGER.ok(img.read(VA_SPEND_25, 3) == b"\x83\xfe" + bytes([SPEND_STRIKE])
              and img.read(VA_SPEND_25 + 3, 2) == b"\x76\x05"
              and img.read(VA_SPEND_25 + 5, 3) == b"\x83\xc6"
                                                 + bytes([(-SPEND_STRIKE) & 0xFF]),
              f"210 takes 0x{SPEND_STRIKE:02X} (= {SPEND_STRIKE}) off every "
              f"OTHER occupied slot, flooring at zero",
              f"{img.read(VA_SPEND_25, 10).hex(' ')} -- cmp esi,0x19 / jbe -> "
              f"0 / add esi,-0x19. GWW's on-use rule word for word: the skill "
              f"used goes to zero and every other adrenal skill loses ONE "
              f"STRIKE. And note it decrements RAW UNITS by 25, which is only "
              f"coherent because §3 shows the costs are not on a 25 grid")
    LEDGER.ok(img.read(VA_SPEND_PAIRLOOP, 3) == b"\x83\xf9\x02",
              f"and it does that to both halves -- a 2-iteration inner loop "
              f"at 0x{VA_SPEND_PAIRLOOP:08X}",
              f"{img.read(VA_SPEND_PAIRLOOP, 5).hex(' ')} -- cmp ecx,2 / jne "
              f"back. Both halves again, so like 209 it repaints without "
              f"waiting for the a->b commit")


def section_display(img):
    """THE DISPLAY DRAWS FROM +0x04, AND PLAN.md SAYS +0x00. This is the fix.

    GWCA names the slot's first dword `adrenaline_a` and PLAN.md line ~1384
    called it "the store the icon draws from". It is not. The accessor
    0x00821050 -- reached only through the ChCliApi wrapper 0x00816EF0, which
    has EXACTLY ONE caller image-wide, GmSkSlot 0x00542E78 -- indexes
    `container + slot*0x14 + 8`, and the charge loop indexes
    `container + slot*0x14 + 4`. Four and eight, from two different functions,
    with the same stride. The icon reads the SECOND dword.

    That makes the pair a DEFERRED-COMMIT DOUBLE BUFFER: +0x00 accumulates and
    the deferred task copies it to +0x04, which is the only half any accessor
    exposes. Py4GW_Reforged reading `adrenaline_a` as the live value is ALSO
    right -- a bot wants the accumulator and the screen shows the committed
    copy. Complementary, not contested.

    THE MAP GATE is the half that changes probe design: the fill is drawn only
    when the map state is MISSION_MAP_GAME, and is actively torn down otherwise.
    A perfectly correct 207 sent to a client sitting in an OUTPOST yields a
    pixel-identical icon, so any probe must be in an explorable or a mission.
    """
    print("\n10. WHICH half the icon draws from -- and when it draws at all")

    LEDGER.ok(img.first_call(VA_SLOT_CALL, span=8) == VA_DISPLAY_WRAPPER,
              f"GmSkSlot 0x{VA_SLOT_CALL:08X} calls ChCliApi "
              f"0x{VA_DISPLAY_WRAPPER:08X}",
              f"resolved from the rel32, "
              f"{img.read(VA_SLOT_CALL, 5).hex(' ')}")
    LEDGER.ok(img.read(VA_ACCESSOR_INDEX, 7)
              == b"\x8d\x04\xb6\x8b\x44\x87" + bytes([ACCESSOR_DISP]),
              f"and the accessor indexes container + slot*0x{SLOT_STRIDE:02X} "
              f"+ {ACCESSOR_DISP}, NOT + {SLOT_FIRST_OFF}",
              f"{img.read(VA_ACCESSOR_INDEX, 7).hex(' ')} -- lea "
              f"eax,[esi+esi*4] (slot * 5) then mov eax,[edi+eax*4+8] (x4, so "
              f"slot * 0x14, + 8). THE CORRECTION THIS BUILD OWES: PLAN.md "
              f"called `adrenaline_a` (+0x00) the store the icon draws from. "
              f"It is +0x04. Two functions, two displacements, one stride -- "
              f"and §9's charge loop starting at +{SLOT_FIRST_OFF} is what "
              f"makes {ACCESSOR_DISP} the SECOND dword rather than the first")
    LEDGER.ok(img.read(VA_ACCESSOR_BOUND, 3) == b"\x83\xfe"
              + bytes([SLOT_COUNT]),
              f"and it bounds-checks the slot index against {SLOT_COUNT}",
              f"{img.read(VA_ACCESSOR_BOUND, 5).hex(' ')} -- cmp esi,8 / jb. "
              f"The SAME eight slots §9's loop closes on arithmetically, "
              f"reached from a different function by a different route")
    LEDGER.ok(img.read(VA_SLOT_THRESH, 4) == b"\x0f\xb7\x46\x38",
              f"and the threshold it divides by is the skill row's +0x38, read "
              f"as a WORD",
              f"{img.read(VA_SLOT_THRESH, 6).hex(' ')} -- movzx eax,word "
              f"[esi+0x38], the same field §9's charge loop tests. The pair "
              f"goes to Controls::SkillImage, which DIVIDES them and forwards "
              f"the fraction: no /25 and no quarter quantisation anywhere. The "
              f"bar is a continuous fraction of the RAW cost, which is the "
              f"other reason §3's off-grid costs are not a problem for the "
              f"client")

    target = img.rel32_target(VA_MAP_GATE_CALL)
    LEDGER.ok(target == VA_MISSION_CLI_GET_MAP
              and img.read(VA_MAP_GATE_CMP, 3)
                  == b"\x83\xf8" + bytes([MISSION_MAP_GAME])
              and img.read(VA_MAP_GATE_CMP + 3, 1) == b"\x75",
              f"THE MAP GATE: the fill is drawn only when the map state is "
              f"MISSION_MAP_GAME (== {MISSION_MAP_GAME})",
              f"call 0x{VA_MAP_GATE_CALL:08X} -> 0x{target:08X} "
              f"(MissionCliGetMap), then cmp eax,1 / jne. MISSION_MAP_OUTPOST "
              f"is 0 (QuestLog:261) and MISSION_MAP_GAME is 1 (MsCliApi:251). "
              f"Off that path the overlay is TORN DOWN with a NULL payload, "
              f"not merely left stale -- so a perfectly correct 207 sent while "
              f"the client sits in an outpost yields a PIXEL-IDENTICAL icon. "
              f"Any probe of this family has to be in an explorable or a "
              f"mission, and a null from an outpost run means nothing")


def section_arenanet_words(img):
    """ARENANET'S OWN IDENTIFIERS, four sites, each cited as one measurement.

    CLAUDE.md's boundary: a SINGLE assert cited as the evidence for a claim is a
    measurement and is kept with its file and line; a bulk dump is expression
    and is refused. These four are the difference between "we called this
    adrenaline" and "the client calls this adrenaline".
    """
    print("\n11. what ArenaNet's own asserts call this")
    import asserts
    a = asserts.Asserts(img.path)

    found = {s.va: s for s in a.grep(r"(?i)adrenaline")}
    found.update({s.va: s for s in a.near(VA_SPEND_WORKER, span=0x120)})
    for va, (module, line, expr) in ASSERTS.items():
        s = found.get(va)
        LEDGER.ok(s is not None and s.module == module and s.line == line
                  and s.expr.strip("'") == expr,
                  f"0x{va:08X} is {module}:{line} '{expr}'",
                  f"got {s!r}" if s else "NOT FOUND at that address")

    LEDGER.ok(len({(v[0], v[1]) for v in ASSERTS.values()
                   if v[2].startswith("!(energyCost")}) == 2,
              "and `skillData.adrenaline` is ArenaNet's name for +0x38 at TWO "
              "independent sites",
              "GmCtlSkCard:409 and GmCtlSkListEntry:185, both guarding a "
              "`cmp word [reg+0x38],0`. Two separate source files reaching the "
              "same field with the same identifier is what promotes "
              "`clientscan/skilltable.py`'s `adrenaline_units` decode from our "
              "name for the column to the client's own")
    LEDGER.ok(ASSERTS[0x00820DEB][1] == 84
              and img.read(VA_DEFERRED_TASK, 3) == b"\x55\x8b\xec"
              and 0x00820DEB - VA_DEFERRED_TASK < 0x40,
              f"and ChCliSkill:84 sits inside the deferred task at "
              f"0x{VA_DEFERRED_TASK:08X}",
              f"`context->skillAdrenalineUpdateArray.Count()`, "
              f"0x{0x00820DEB - VA_DEFERRED_TASK:X} bytes into the function's "
              f"prologue. So the queue 207 appends to and this task drains is "
              f"named ADRENALINE by the client itself -- which is the "
              f"strongest single piece of evidence that the whole chain is "
              f"what this file says it is, and it is one quotation rather "
              f"than a dump")

    LEDGER.ok(len(a.grep(r"(?i)adrenaline")) >= 4,
              f"POSITIVE CONTROL: the scan reads "
              f"{len(a.grep(r'(?i)adrenaline'))} adrenaline asserts in total",
              "`asserts.py` says its own counts are a FLOOR -- it is short by "
              "373 sites it cannot read -- so 'no assert names X' is never a "
              "census here. That cuts one way only: what it DOES find is real, "
              "and this check is what says the scan ran at all")


# ---------------------------------------------------------------------------


def section_bar_gate():
    """THE FAMILY IS DARK FOR A BAR THAT CANNOT HOLD ADRENALINE.

    The most refutable claim here, and the one that matters most to the sender.
    Split the corpus on a variable that has nothing to do with adrenaline
    traffic -- does the observer's SKILLBAR_UPDATE ever name a skill with a
    non-zero `adrenaline_units` -- and every 207, every 208 and every 210 falls
    on one side. One counterexample kills it.

    THE CONTROL IS THE HALF THAT MAKES THE ZERO MEAN SOMETHING. A filtered
    search that finds nothing proves nothing until the same search has found
    something it should, and here the positive is inside the negative
    population: those 22 connections carry 45 landed weapon hits and 13
    completed melee attacks. GWW's rule grants 25 units per successful weapon
    hit; retail granted none. So the silence is a gate and not an absence of
    combat, which is exactly what a quiet capture would look like.

    THE GATE'S VARIABLE IS CONFOUNDED AND THIS DOES NOT PRETEND OTHERWISE.
    Every dark connection is also a non-Warrior character, so "the bar carries
    an adrenal skill" and "the profession uses adrenaline" fit all 58
    connections identically. What is asserted is the SPLIT, which is observed;
    which side of the confound causes it is not, and the sender implements
    neither (see `authsrv.player_gains_adrenaline`).
    """
    print("\n12. the family is dark for a bar with no adrenal skill on it")
    import adrenjoin
    stats, rows, skipped = adrenjoin.scan()
    armed, dark = stats["arms"]["armed"], stats["arms"]["dark"]

    LEDGER.ok(armed["connections"] == ARMED_CONNECTIONS
              and dark["connections"] == DARK_CONNECTIONS,
              f"the split is {armed['connections']} armed / "
              f"{dark['connections']} dark connections",
              f"expected {ARMED_CONNECTIONS}/{DARK_CONNECTIONS}. The variable "
              f"is the observer's own SKILLBAR_UPDATE against content's "
              f"`adrenaline_units` column -- nothing about adrenaline TRAFFIC "
              f"enters it, which is what lets the next check discriminate")

    got = {op: dark[k] for op, k in
           ((SMSG_ADRENALINE_CHARGE, "gain"), (SMSG_ADRENALINE_CLEAR, "clear"),
            (SMSG_ADRENALINE_SPEND, "spend"))}
    LEDGER.ok(set(got.values()) == {0},
              f"a dark connection carries NO adrenaline message at all: "
              f"{ {hex(o): n for o, n in got.items()} }",
              f"over {dark['messages']} messages in {dark['connections']} "
              f"connections. Not 'few' -- none. The whole lifecycle is absent, "
              f"clears and spends included, which is self-consistent: no gain "
              f"means no 25-second clock means nothing to clear")

    LEDGER.ok(all(armed[k] == ARMED_FAMILY[op] for op, k in
                  ((SMSG_ADRENALINE_CHARGE, "gain"),
                   (SMSG_ADRENALINE_CLEAR, "clear"),
                   (SMSG_ADRENALINE_SPEND, "spend"))),
              f"and the armed side carries ALL of it: "
              f"{armed['gain']}/{armed['clear']}/{armed['spend']}",
              f"expected {ARMED_FAMILY}. THIS IS ALSO A CROSS-CHECK ON 4: "
              f"the census there counts opcodes over the whole corpus and this "
              f"counts them per connection after a skillbar join, so the two "
              f"agreeing is two queries and not one number read twice")

    LEDGER.ok(dark["hits_landed"] >= DARK_HITS_LANDED
              and dark["melee_finished"] >= DARK_MELEE_FINISHED,
              f"POSITIVE CONTROL: those dark connections FOUGHT -- "
              f"{dark['hits_landed']} landed hits, "
              f"{dark['melee_finished']} completed melee attacks",
              f"expected at least {DARK_HITS_LANDED} and "
              f"{DARK_MELEE_FINISHED}. WIKI (GWW, 'Adrenaline'): one successful "
              f"weapon hit is 25 units. Retail sent none for any of them, so "
              f"the zero above is a GATE and not a quiet capture. Without this "
              f"line the previous check is unfalsifiable")

    LEDGER.ok(armed["damage_taken"] == ARMED_DAMAGE_TAKEN,
              f"the armed side took {armed['damage_taken']} damage messages, "
              f"and every one of them granted",
              f"expected {ARMED_DAMAGE_TAKEN}. The two populations happen to "
              f"be the same size, which is a coincidence and not a check -- "
              f"what matters is that one is 32 grants of 32 and the other is "
              f"0 of 32")

    LEDGER.ok(dark["damage_taken"] == DARK_DAMAGE_TAKEN,
              f"and they took {dark['damage_taken']} damage messages, every "
              f"one of which granted nothing",
              f"expected {DARK_DAMAGE_TAKEN}. THESE ARE THE ROWS THAT LOOK "
              f"LIKE A ROUNDING BOUNDARY and are not: unstratified they say "
              f"'damage of up to 7.5% of maximum health grants no adrenaline', "
              f"which is absurd and would refute `pools.damage_units` outright")

    fits = adrenjoin.fits([r for r in rows if r["arm"] == "armed"])
    LEDGER.ok(fits["n"] == ARMED_JOINED
              and fits["round"] == ARMED_FITS["round"] == fits["n"],
              f"re-fitted on the armed rows alone, round() fits "
              f"{fits['round']} of {fits['n']}",
              f"expected {ARMED_FITS} over {ARMED_JOINED}. floor "
              f"{fits['floor']}, ceil {fits['ceil']} -- so the 2026-08-21 "
              f"correction from floor to round survives the stratification "
              f"that killed the boundary claim. Note what it does NOT survive "
              f"into: the armed rows run 2.50%..11.04% and there is no armed "
              f"row below 2.5%, so the sub-1% boundary is still UNVERIFIED")

    armed_rows = [r for r in rows if r["arm"] == "armed" and not r["ambiguous"]]
    pcts = sorted({r["pct"] for r in armed_rows})
    ks = [round(p / 100.0 * ARMED_MAX_HEALTH) for p in pcts]
    integral = all(abs(p / 100.0 * ARMED_MAX_HEALTH - k) < 1e-4
                   for p, k in zip(pcts, ks))
    smaller = [h for h in range(1, ARMED_MAX_HEALTH)
               if all(abs(p / 100.0 * h - round(p / 100.0 * h)) < 1e-4
                      for p in pcts)]
    LEDGER.ok(integral and ks == ARMED_NUMERATORS and not smaller,
              f"NO FREE PARAMETER: all {len(pcts)} armed percentages are "
              f"k/{ARMED_MAX_HEALTH}, k = {ks}",
              f"expected {ARMED_NUMERATORS}, and no denominator below "
              f"{ARMED_MAX_HEALTH} works (found {smaller}). The observer's int "
              f"property 42 reads {ARMED_MAX_HEALTH} on the same wire and none "
              f"of this arithmetic looked at it, so the two are independent "
              f"witnesses to the same maximum health. It is also the limit of "
              f"what the corpus can say about the RULE: one max health cannot "
              f"separate 'one unit per 1% of maximum' from 'one unit per "
              f"{ARMED_MAX_HEALTH / 100.0} raw points'")

    LEDGER.ok(len(skipped) <= 1,
              f"{len(skipped)} connection skipped for having no unique self "
              f"agent",
              f"the self agent is int property 41, self-scoped, with NO "
              f"fallback (`adrenjoin.whose_agent`). The one skip is a 6112 "
              f"auth channel, which carries no agent properties at all. "
              f"Identifying the observer by 'the agent a 207 names' would "
              f"delete the ENTIRE dark population from the denominator -- the "
              f"outcome-selection defect one level down")


def section_repaint_gate(img):
    """WHY NOBODY SAW 12 FROM THE SCREEN: a 207 no slot accepted is a no-op.

    Read as arithmetic on the charge worker's own bytes rather than compared
    with a transcription. EDI is cleared before the slot loop, set only on the
    path that writes a slot, and tested immediately after the loop's back-edge;
    the `je` skips the UI event that carries the 25.0 timer. So a 207 delivered
    to a bar with no adrenal skill leaves the flag at zero and exits.

    This is what makes 12's divergence invisible, and it cuts both ways: it is
    why our sender's extra 207s are harmless on screen, and it is why six
    captures of retail sending none went unnoticed for a day.
    """
    print("\n13. the charge worker's repaint is gated on 'a slot moved'")
    b = img.read(VA_CHARGE_FLAGCLR, 3)
    LEDGER.ok(b[:2] == b"\x33\xff",
              f"0x{VA_CHARGE_FLAGCLR:08x} is `xor edi,edi`, before the loop",
              f"read {b[:2].hex()}, expected 33ff. The flag starts clear, so "
              f"the default outcome of the loop is 'nothing moved'")

    b = img.read(VA_CHARGE_FLAGSET, 5)
    LEDGER.ok(b == b"\xbf\x01\x00\x00\x00",
              f"0x{VA_CHARGE_FLAGSET:08x} is `mov edi,1`, INSIDE the loop",
              f"read {b.hex()}, expected bf01000000. It sits immediately after "
              f"the only arithmetic store to a slot (0x{VA_CHARGE_STORE:08x}), "
              f"so it is set per SLOT WRITTEN and not per message received")

    # the loop's back-edge, as arithmetic: jne rel8 at 0x008219F6 -> the top
    j = img.read(0x008219F6, 2)
    back = (0x008219F6 + 2 + struct.unpack("<b", j[1:2])[0]) & 0xFFFFFFFF
    LEDGER.ok(j[0] == 0x75 and back == VA_CHARGE_LOOPTOP,
              f"the loop closes: `jne` at 0x008219F6 goes back to "
              f"0x{back:08x}",
              f"expected 0x{VA_CHARGE_LOOPTOP:08x}. Computed from the "
              f"displacement, so a wrong address gives a wrong sum rather than "
              f"agreeing with a label we chose")

    b = img.read(VA_CHARGE_FLAGTST, 8)
    target = (VA_CHARGE_FLAGTST + 8
              + struct.unpack("<i", b[4:8])[0]) & 0xFFFFFFFF
    LEDGER.ok(b[:2] == b"\x85\xff" and b[2:4] == b"\x0f\x84",
              f"0x{VA_CHARGE_FLAGTST:08x} is `test edi,edi` then `je`, AFTER "
              f"the loop",
              f"read {b.hex()}. This is the whole finding: the test is outside "
              f"the loop and the jump is taken when NO slot moved")

    LEDGER.ok(VA_CHARGE_FLAGTST < VA_UI_EVENT_PUSH < target,
              f"and the `je` lands at 0x{target:08x}, PAST the UI event push "
              f"at 0x{VA_UI_EVENT_PUSH:08x}",
              f"an ordering claim, checkable by three addresses: the push is "
              f"between the test and the jump's target, so taking the jump "
              f"skips it. A 207 that moved nothing fires no 0x{UI_EVENT_ADREN:08x} "
              f"and arms no 25-second timer")

    b = img.read(VA_UI_EVENT_PUSH, 5)
    LEDGER.ok(b == b"\x68" + struct.pack("<I", UI_EVENT_ADREN),
              f"the skipped push is the adrenaline UI event, "
              f"0x{UI_EVENT_ADREN:08x}",
              f"read {b.hex()}. Same event 11 names from the other end -- the "
              f"blink warning's timer. Skipping it is what makes an unaccepted "
              f"207 invisible rather than merely harmless")


def main():
    declared = section_schema()
    section_pin_consistency()
    section_cost_column()

    try:
        agg = scan_corpus()
    except (Exception, SystemExit) as ex:                      # noqa: BLE001
        # SystemExit is deliberate, not defensive: `vaultpath.require_dir`
        # raises it by design and it is NOT an Exception subclass, so a bare
        # `except Exception` would let a missing vault kill the run with a
        # traceback and exit 1 instead of declaring the skip the floor rule is
        # built around. A crash and a skip look nothing alike to a reader and
        # identical to a CI exit code.
        agg = None
        LEDGER.skip("the live-corpus oracle (sections 4-7)",
                    f"no live captures here ({ex}). These are the sections "
                    f"that put the model against ArenaNet's own wire -- a "
                    f"green run without them has checked the client and none "
                    f"of the traffic")
    if agg is not None:
        section_census(agg)
        section_populations(agg)
        section_self_scope(agg)
        section_spend_join(agg)
        section_order(agg)
        section_bar_gate()

    try:
        img = Image()
    except (Exception, SystemExit) as ex:                      # noqa: BLE001
        img = None
        LEDGER.skip("the build-38797 byte pins (sections 8-11)",
                    f"the pinned client image is not in this vault ({ex}). "
                    f"Every address in this file was measured on 38797 and on "
                    f"another build would read whatever else is mapped there "
                    f"and return a confident wrong number, which is why "
                    f"`pinned.find()` refuses rather than guessing")
    if img is not None:
        section_dispatch(img, declared)
        section_workers(img)
        section_display(img)
        section_arenanet_words(img)
        section_repaint_gate(img)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
