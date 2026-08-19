"""Agents other than the player: what the client must be told to render one.

Extracted so the server and the probes cannot drift apart. Every constant and
every field order here was proven against our own client before it was moved
into this file -- see studies/enemy/PLAN.md for the run that established each,
and studies/agentprops/FINDINGS.md for the ones read out of the binary.

WHERE THE NUMBERS LIVE, changed 2026-08-06. This module keeps PROTOCOL VOCABULARY --
what the wire MEANS, read out of the client's own code: ALLEGIANCE_ENEMY, PROP_HEALTH_MAX,
the GV_ event ids, the class-tag bases. Those are not authorable and moving them would
be a category error.

WORLD FACTS -- the Hatcher, the starter hammer, the player's health and energy, the
weapon swing rates -- moved to `content/*.toml` and are loaded below. They were Python
literals with their provenance in comments no tool could read; each row now carries its
own source and verification as data, and the loader refuses a row that cites an
unlicensed upstream without saying what we checked it against. That is what settles the
licence question this docstring used to defer: see `toolkit/content.py`, and
`content/npcs.toml` for the Hatcher's own entry.

The names below are unchanged and still dicts, so every call site -- including the
eight in probes.py -- reads exactly as it did.
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import content  # noqa: E402

WORLD = content.load()


def _encstring(words):
    """GW string ids as the wire carries them: one UTF-16 code unit per id.

    The content store holds them as a list of integers, because that is what they
    are -- ids the client resolves against its own string table, not text. The wire
    wants them packed into a string.
    """
    return "".join(chr(w) for w in words)


def _row(kind, key):
    row = dict(WORLD.get(kind, key))
    if "enc_name" in row:
        row["enc_name"] = _encstring(row["enc_name"])
    return row


def npc_template(key):
    """A usable NPC template by name -- NOT the raw content row.

    The difference is the whole reason this is public. `enc_name` is stored as
    a list of 16-bit GW string ids and must be ENCODED before it can go on the
    wire; a caller that reaches for `WORLD.get("npc", key)` gets the list and
    `npc_properties` builds a message the codec refuses
    (`string of 28 code units exceeds cap 8`). MEASURED 2026-08-13: the area
    population did exactly that, and because the throw happened inside instance
    bring-up the harness still reported PASS and the map readback was still
    green -- every body was simply absent.
    """
    return _row("npc", key)


INF = float("inf")

# GmAgent.h: the top nibble of model_id is a class tag. OBSERVED both ways --
# a player-class body renders as another player, complete with a Trade button,
# and a monster-class body renders as an NPC (studies/enemy/PLAN.md 6c, 6d).
CHAR_CLASS_PLAYER_BASE = 0x30000000
CHAR_CLASS_MONSTER_BASE = 0x20000000

AGENT_TYPE_LIVING = 1
AGENT_KIND_PLAYER = 5          # WORLD_CREATE_AGENT's h000B byte
AGENT_KIND_NPC = 9             # 0 item, 5 player, 9 NPC

DEFAULT_RUN_SPEED = 288.0
APPEARANCE_WARRIOR = 1 << 20

# Field 12 of WORLD_CREATE_AGENT is an allegiance FourCC, and it is an opaque
# team IDENTITY rather than a vocabulary the client looks up: 'play' appears
# NOWHERE in Gw.exe as a dword constant, and the only allegiance-shaped
# constants in the image are 'nonc' and 'nonn', inside one four-instruction
# predicate. OBSERVED: an agent carrying the player's own token reads green, the
# two client constants read green, and an unrecognised token reads RED.
# See studies/enemy/PLAN.md section 6e.
ALLEGIANCE_PLAYER = 0x706C6179        # 'play'  -- same team as the player
ALLEGIANCE_NONCOMBATANT = 0x6E6F6E63  # 'nonc'  -- the client's own constant
ALLEGIANCE_HOSTILE = 0x6D6F6E73       # 'mons'  -- any UNRECOGNISED value is an
                                      # enemy. See the correction below: these
                                      # bytes turned out NOT to be arbitrary.

# THE TOKEN VOCABULARY, MEASURED 2026-08-17 over the whole live corpus (1,207
# creates, 6 captures). The comment above used to end "these particular bytes
# are not special and nothing in the client knows them", and half of that is
# now refuted by ArenaNet's own wire:
#
#   play 470   every kind-5 player, and 51 allied kind-9 NPCs
#   nonc 401   noncombatants
#   mon1 233   the hostile token retail actually uses in these areas
#   0000 216   every kind-0 item and kind-1 gadget, exceptionless
#   anim  41   animals
#   band  37   bandits
#   mons  19   REAL, and ours by luck: retail sends exactly these bytes for the
#              Shing Jea training monsters (definitions 3965/3975)
#   0x616E698F 6   'ani' + 0x8F -- consistent across 6 creates of definition
#              3973, so a real value rather than corruption
#
# WHAT SURVIVES of the old claim: the BINARY scan. 'mons' is still not a dword
# constant in Gw.exe, and the client still renders any unrecognised token
# hostile -- that was measured and stands. WHAT IS REFUTED is the implication
# that we invented an arbitrary value: it is retail's own token for a real
# family of monsters. The choice was lucky, not informed, and the corpus is
# what turned one into the other.
#
# NOT EXPLAINED, and worth a look before anyone leans on the set: 'mon1'/'mons'
# and 'anim'/0x616E698F each differ ONLY in the last byte, which hints at a
# 3-character class plus a team/variant byte. 'play', 'nonc' and 'band' are
# ordinary four-letter words, so that reading is RECONSTRUCTION and one more
# area would test it.

# Agent property ids (float channel, GAME_SMSG 0x00A3 -- prop_id, target, cause,
# value). Which ones the client acts on is SOURCED from its own jump tables;
# see studies/agentprops/FINDINGS.md.
# BOTH OF THESE ARE FRACTIONS, and the difference is only WHO MULTIPLIES.
# OBSERVED 2026-08-11 from the dispatcher at 0x00818210, a switch over property
# ids 16..62 (index bytes at 0x008183B8, arm pointers at 0x00818394):
#   16 -> arm 0, 0x0081823C:  fld [esi+0x24] (the MAX) / fmul [ebp+0xc] (our
#                             value) -> call 0x00921510. The CLIENT scales it.
#   34 -> arm 2, 0x0081828D:  fld [ebp+0xc] / fstp [esp] -> call 0x009215F0.
#                             No fmul in the ARM -- 0x009215F0 does the scaling
#                             itself, because 34 is a SETTER rather than a
#                             subtraction. It sets the pool to fraction x max.
#                             OBSERVED 2026-08-11 (FINDINGS 1e): the player orb
#                             went 100 -> 90 (property 16, -0.10) -> 1 (property
#                             34, -0.50). A delta predicts 40. -0.5 SETS it to
#                             -50, which clamps to the floor of 1.
#                             That is why 0x009215F0 asserts `fraction <= 1.0f`
#                             at CharPool.cpp:84 -- a setter cannot exceed the
#                             maximum -- and why sending 100.0 killed the client.
PROP_LEVEL = 36           # int channel (0x009F): the agent's DISPLAYED level.
                          # OBSERVED three ways in three days: the player's
                          # roster row tracked W1/W15/W20 (RESKIN 18.4), the
                          # HENCHMAN'S row tracked Mo1/Mo15/Mo20 (harness
                          # 20260817T142147 -- the store is per-agent both
                          # ways), and the case body is read: int-main
                          # 0x00812D6E writes entry+0x2C keyed by the agent id
                          # (unitsetup Q3/Q4). Retail sends it BEFORE the
                          # player's create (344/366, createburst census).
PROP_DAMAGE = 16          # SUBTRACTS fraction x max. Floors at 1: cannot kill.
PROP_HEALTH_ABSOLUTE = 34 # badly named: it SETS health to fraction x max, and is the one the client range-checks. SILENT: no damage number.
PROP_HEALTH_MAX = 42      # int channel (0x009F). Sets the maximum; see below.
# "AND refills" is REFUTED, 2026-08-13. That reading came from ldufr/Headquarter
# ("assigns health_max = value and health = 1.f") -- UPSTREAM, never observed on
# retail -- and it is wrong. MEASURED (harness 20260813T215004, RESKIN.md 18.13):
#
#   health += (new_max - old_max)
#
# From 25/100, setting the maximum to 200 gave a HUD reading of 125 -- not 200 --
# and a bar at 62.3% against the 62.5% that 125/200 predicts. Setting it back to
# 100 returned exactly 25, so it is reversible rather than a latch. A
# maximum-health increase GRANTS that health, the way a rune does.
#
# The practical consequence, and why the old comment was worth more than a
# footnote: sending 42 with the value the agent ALREADY has is a NO-OP, because
# the delta is zero. A run that tried to use it as "restore to full" measured
# nothing and looked like a dead property (RESKIN.md 18.12).
#
# THE SHRINK DIRECTION, and the store is SIGNED. MEASURED (harness
# 20260817T143333, probe health_shrink, studies/unitsetup/FINDINGS.md 8 Q5):
# from 25/100, max -> 50 DISPLAYED 1 on the orb, and max -> 100 then read
# exactly 25 again. Only 25 + (50-100) = -25 held in an UNCLAMPED signed store
# explains the round trip -- a store clamped at 1 restores to 51, a refill to
# 50. So the delta can drive current health BELOW ZERO silently, the HUD
# floors the DISPLAY at 1, and the arithmetic survives the excursion intact.
# The "floors at 1: cannot kill" on PROP_DAMAGE above is therefore at least
# partly a display floor; what the STORE does under prop 16 is unmeasured.

# The agent effects bitfield, carried by GAME_SMSG 0x00F1. Bit 4 is death:
# setting it kills, clearing it revives. OBSERVED both directions.
#
# Reviving is TWO operations. The client's death path zeroes the health and
# energy pools, so clearing the bit alone returns a body at ~0-1 health that
# dies to any scratch. Clear the bit, then set health.
EFFECT_DEAD = 0x10

# Bit 12, and the NAME is the careful part. OBSERVED on ArenaNet's own traffic: it is
# set on 151 of 151 Plague Worm creates (via GAME_SMSG 0x00F0) and cleared exactly
# 2.00 s later, then set again exactly 2.00 s before the agent is removed -- n=132 each
# way, every sample inside +/-60 ms.
#
# So it is set during BOTH transitions and CLEAR for the whole time the worm is out and
# targetable, which is the opposite of "hidden". Calling it EFFECT_BURROWED would name
# it for the mechanic and be wrong; naming it for the window it actually covers keeps
# the claim inside what was measured. It is not exclusive to worms either -- two other
# agents in the first Lakeside tape carry it on unrelated models. What the client DOES
# with the bit is UNVERIFIED; only its timing is observed.
EFFECT_TRANSITION = 0x1000

# One NPC definition, transcribed from gw-preservation's agent table as a lead
# and then CONFIRMED against our own client: 'Hatcher [Collector]' rendered with
# a collector's body and its real localised name. File id 116228 also appears in
# GWLP-R's mock NPC from 2013, so it is two lineages thirteen years apart.
#
# enc_name is an EncString -- references into the client's own localised text
# resources, not characters. It cannot be invented; this one was copied whole
# and the client resolved it to English.
HATCHER = _row("npc", "hatcher")


def npc_properties(definition, npc, level=None):
    """GAME_SMSG 0x0056 -- defines an NPC TYPE. Must precede any agent using it.

    Not optional and not decoration: the definition index is a raw array index
    on the client, and creating an agent whose definition was never sent takes
    the client down on `index < m_count` in Base\\rtl\\Array.h. OBSERVED.
    """
    return [definition, npc["file_id"], 0, npc["scale"], 0, npc["flags"],
            npc["profession"], npc["level"] if level is None else level,
            npc["enc_name"]]


def npc_model(definition, npc):
    """GAME_SMSG 0x0057 -- the model files for an NPC type."""
    return [definition, [npc["model_id"]]]


# --- the four messages named on 2026-08-10 that this server could not send ----
#
# Each enforces a bound the CLIENT asserts on itself. That is the point: every
# one of these values is out of range for some argument a caller might
# reasonably pass, and the client's answer to an out-of-range value is an assert
# dialog mid-session, not a wrong pixel. Raising here names the caller instead.
# See studies/smsg/FINDINGS.md.

AGENT_MIN_MOVE_SPEED = 0.01     # AgAgent.cpp:2366; the .rdata constant is the
AGENT_MAX_MOVE_SPEED = 1.0      # float32 of 0.01.  AgAgent.cpp:2367
AGENT_FACING_MASK = 0xF         # AgAgent.cpp:2368 "!(facing & ~AGENT_FACING_MASK)"
MAX_TURN_RATE = 20.0 * math.pi  # rad/s. Observed: 0.24892, 0.89012, 2.0943952
FACING_FORWARD = 1              # 119 of 163 samples, and every varied speed
# Three different numbers that used to be one, and the one they were collapsed
# into was the weakest of them. See studies/profession/FINDINGS.md.
CHAR_PROFESSIONS = 11           # the CLIENT's own compiled bound: ids 0..10 are
                                # valid, 0 = None. MEASURED on build 38797 at 29
                                # assert sites across 13 modules, and reproduced
                                # on the 2026-04-30 build.
OBSERVED_PRIMARY_MAX = 6        # the largest primary our live corpus ever showed
                                # (387 samples of 0x00A6, all early-Prophecies).
                                # A fact about the CORPUS, not a limit on the
                                # field -- professions 7..10 ship and are legal.
PROFESSION_FIELD_MAX = 0xFF     # the wire field is a plain u8 on 0x00A6/0x00B7,
                                # and the setter at 0x007F7330 contains no
                                # comparison instruction at all. 255 is the
                                # field's width, not a claim the client copes.

# GAME_SMSG 0x0026's setter is ((old ^ new) & 0x3f0000) ^ new -- it KEEPS the old
# bits inside this mask and takes the new bits everywhere else. A server cannot
# write these through this message at all.
FLAGS_CLIENT_OWNED_MASK = 0x3F0000


def _as_u32(f):
    """A float32's bits, as the u32 the wire actually carries.

    0x002E's two payload fields are typed `dword` in the client's own tables and
    hold IEEE-754 floats. The typing is CORRECT and must not be "fixed" to
    float -- the values are floats, the marshalling is not. Same split as
    GAME_CMSG 0x0040 ROTATE_PLAYER, where the same confusion cost days.
    """
    return struct.unpack("<I", struct.pack("<f", float(f)))[0]


def agent_update_speed(agent_id, speed, facing=FACING_FORWARD):
    """GAME_SMSG 0x002B -- an agent's NORMALISED movement rate, and its facing.

    `speed` is a fraction of the reference run speed, NOT a distance: 1.0 is 288
    units/s, and 7 of the 15 distinct values ArenaNet sent are exact multiples
    of 1/288. The client asserts both bounds on itself, so a caller passing
    288.0 -- the obvious mistake, since create_agent's field 9 IS in units/s --
    is named here rather than by a dialog thirty seconds later.

    This drives the WALK CYCLE's playback rate. An agent that moves without it
    animates at whatever default the client is holding, which reads as smooth
    movement carrying a wrong-cadence, sliding-feet animation. CONFIRMED by eye
    on our own server 2026-08-11. It is NOT an explanation for jank seen during
    a TAPE REPLAY -- there the tape is the whole channel, this server sends
    nothing of its own, and ArenaNet's tapes carry 163 of these themselves.

    UPSTREAM's gloss was "SpeedModifier -> agent, modifier, type" and it is
    REFUTED: a field capped at 1.0 cannot carry a movement buff, and the third
    field is `facing` in the client's own assert.
    """
    speed = float(speed)
    if not AGENT_MIN_MOVE_SPEED <= speed <= AGENT_MAX_MOVE_SPEED:
        raise ValueError(
            f"speed {speed!r} is outside the client's own asserted "
            f"[{AGENT_MIN_MOVE_SPEED}, {AGENT_MAX_MOVE_SPEED}] "
            f"(AgAgent.cpp:2366-2367). This field is a FRACTION of the run "
            f"speed, not units/s -- {speed} units/s would be "
            f"{speed / DEFAULT_RUN_SPEED:.4f} here")
    if facing & ~AGENT_FACING_MASK:
        raise ValueError(f"facing {facing:#x} sets bits outside "
                         f"AGENT_FACING_MASK ({AGENT_FACING_MASK:#x}) -- "
                         f"AgAgent.cpp:2368")
    return [agent_id, speed, facing]


def agent_update_rotation(agent_id, angle, rate):
    """GAME_SMSG 0x002E -- absolute facing angle, and how fast to turn to it.

    `angle` is absolute radians in [-pi, pi], or +/-inf to spin freely: the
    infinities are a real sentinel the client loads from two .rdata constants,
    not garbage. `rate` is rad/s and is per-CREATURE rather than per-message --
    29 of the 31 agents that sent this never changed it, and 28 of 31 used
    2.0943952 = 2*pi/3 exactly (120 deg/s).

    UPSTREAM called the fields rotation_cos and rotation_sin. REFUTED:
    sin^2+cos^2 over the live corpus ranges 1.23-4.87 and is never 1. That gloss
    is the reason this message went unsent for weeks.
    """
    angle = float(angle)
    if math.isnan(angle):
        raise ValueError("angle is NaN; use +/-inf for the free-spin sentinel")
    if math.isfinite(angle) and not -math.pi <= angle <= math.pi:
        raise ValueError(f"angle {angle!r} rad is outside +/-pi -- every finite "
                         f"value in the live corpus is inside it. Wrap first")
    rate = float(rate)
    if not 0.0 < rate <= MAX_TURN_RATE:
        raise ValueError(f"turn rate {rate!r} rad/s is not in "
                         f"(0, {MAX_TURN_RATE:.3f}]")
    return [agent_id, _as_u32(angle), _as_u32(rate)]


def agent_update_flags(agent_id, flags):
    """GAME_SMSG 0x0026 -- MERGE into the agent's m_flags (offset 0x20).

    Not an assignment. The client's setter computes ((old ^ new) & 0x3f0000) ^ new,
    keeping the old bits inside that mask and taking the new bits elsewhere. A
    server cannot set or clear anything in the mask through this message, and a
    caller that tries gets silence rather than an error -- so this refuses.

    OBSERVED as the tail of ArenaNet's five-message create burst (151 of 155
    immediately follow 0x006D), and again at the instant of death.
    """
    if flags & FLAGS_CLIENT_OWNED_MASK:
        raise ValueError(
            f"flags {flags:#x} sets bits inside {FLAGS_CLIENT_OWNED_MASK:#x}, "
            f"which the client's own merge KEEPS FROM THE OLD VALUE -- they "
            f"would be silently ignored rather than applied")
    return [agent_id, flags]


def agent_set_profession(agent_id, primary, secondary=0, custom=False):
    """GAME_SMSG 0x00A6 -- the profession pair: icons, roster, nameplate.

    The client's own invariant is GmDeckBuilder:2321
    `agentPrimaryProf != agentSecondaryProf`, and across 387 live samples the
    primary is 1..6 and NEVER 0 while the secondary is 0 about half the time.
    A primary of 0 is therefore not "no profession"; it is out of band.

    THE BOUND USED TO BE 6 AND THAT WAS WRONG IN BOTH DIRECTIONS. Six is the
    largest primary our capture corpus happens to contain, and every one of
    those captures is early-Prophecies content; it was never the client's
    limit. Enforcing it refused professions 7..10 -- Assassin, Ritualist,
    Paragon, Dervish -- which ship, are legal, and reach this function straight
    from content via authsrv.py's NPC loop. Any such NPC raised.

    `custom=True` raises the ceiling to the wire field's own width so a
    profession experiment can send an id the client does not ship. It is opt-in
    because out-of-band is exactly what an ordinary caller must not send by
    accident, and because what the client does with such an id is the
    QUESTION -- studies/profession/ measures 29 bound-check sites, every one
    of which ends the session (the assert reporter is noreturn). Passing
    custom=True means "I am the experiment", not "this is safe".
    """
    limit = PROFESSION_FIELD_MAX if custom else CHAR_PROFESSIONS - 1
    if not 1 <= primary <= limit:
        why = ("the wire field is a u8" if custom else
               f"the client's compiled bound is {CHAR_PROFESSIONS} "
               f"(ids 0..{CHAR_PROFESSIONS - 1}); pass custom=True to go past it")
        raise ValueError(f"primary profession {primary} outside 1..{limit}: {why}. "
                         f"0 does not mean 'none' and never occurs in the corpus")
    if not 0 <= secondary <= limit:
        raise ValueError(f"secondary profession {secondary} outside 0..{limit} "
                         f"(0 means none)")
    if secondary and secondary == primary:
        raise ValueError(f"primary == secondary == {primary} violates the "
                         f"client's own assert (GmDeckBuilder:2321)")
    return [agent_id, primary, secondary]


def secondary_bits(*professions):
    """Build 0x00B6's mask from profession ids. Bit N = id N is offerable.

    OBSERVED (build 38797): the drop-down builder tests the mask with
    `mov eax,1 / shl eax,cl / test edx,eax` at 0x00502414 where cl is the loop
    index, so the bit index IS the profession id. Bit 0 is effectively dead --
    id 0 is skipped at 0x00502404 unless it is the current secondary.
    """
    mask = 0
    for p in professions:
        if not 1 <= p <= CHAR_PROFESSIONS - 1:
            raise ValueError(f"profession {p} outside 1..{CHAR_PROFESSIONS - 1}: "
                             f"the builder's loop is `cmp edi, 0xb` (ids 0..10), "
                             f"so a bit above 10 can never be read and a custom "
                             f"id cannot be offered as a secondary at all")
        mask |= 1 << p
    return mask


ALL_SECONDARIES = secondary_bits(*range(1, CHAR_PROFESSIONS))


def party_build(party_id=1, player_number=None, inside_window=()):
    """The four messages that BUILD a party and make it yours.

    THE PARTY WINDOW'S GATE, and it is one value read in two places
    (studies/profession/RESKIN.md 17). `PyCliGetMyPartyId` at 0x00856250 is
    `[[ctx+0x4C]+0x54]` dereferenced, and it is 0 on our server because
    nothing we sent ever wrote that pointer. In an OUTPOST the key router's
    availability filter refuses both start-menu items bound to P and discards
    the key at 0x004E8C61 before P's arm ever runs; with is_explorable set the
    arm runs and bails at 0x004EC115 before the only party FrameCreate
    (0x004EC1BF, child 0x66 = CONTROL_PARTY_MAIN). One value, two silent
    refusals -- which is why forcing is_explorable changed nothing.

    0x00B0/0x00B1 are NOT this. They write the per-player display array at
    ChCliApi ctx+0x80C; the gate is the party manager's own vector.

    THIS IS RETAIL'S OWN SEQUENCE, 8 of 8 live connections, in retail's own
    position -- immediately after PLAYER_SET_PARTY. The alternative of
    allocating a record directly was considered and rejected: it is fewer
    messages but it is not what the client is built around, and the adversarial
    pass measured this order on the wire.

    THE CONSTRAINTS ARE ASSERTS, not taste:
      * 0x01D2 exactly ONCE per connection -- a second with a build already
        open fires PyCliParty.cpp:1228 at 0x00859DC1.
      * 0x01CB must sit BETWEEN begin and commit, with the SAME party id, and
        its player number must be the one 0x00B0/0x00B1 carry.
      * 0x01D3's party id must equal 0x01D2's, else PyCliParty.cpp:1238 at
        0x00859E39.
      * The id must be NON-ZERO: 0x01B2 with 0 means "keep current" and is a
        documented no-op at 0x0085879E, so a zero here fails SILENTLY, which
        is the one failure mode we cannot see.

    `inside_window` is any extra roster rows -- party_henchman_add() results --
    to send BETWEEN add-member and commit. They go here rather than at the call
    site because the window is where the asserts above live, and a caller that
    places them itself has to re-derive the same three constraints. Whether
    0x01BF must sit inside the window or also works post-commit is UNTESTED:
    its worker never READS the [record+0x78] build flag, it SETS it, exactly as
    0x01CB's worker does -- which leans "post-commit works too" without closing
    it. Inside is the position that matches the sibling we have measured.

    Returns [(opcode, values, label)] in the order they must be sent.
    """
    if not 1 <= party_id <= 20:
        raise ValueError(
            f"party id {party_id} outside 1..20: the manager's own bound is "
            f"`cmp [esi+8], 0x14` (max 20 parties), and 0 is the client's "
            f"'keep current' no-op rather than a party")
    if player_number is None:
        raise ValueError("player_number is required: it must match the value "
                         "0x00B0/0x00B1 carry, or the member added is not you")
    for msg in inside_window:
        if msg[1][0] != party_id:
            raise ValueError(
                f"{msg[2]} names party {msg[1][0]} but the window being "
                f"opened is party {party_id}: the roster row would index a "
                f"different manager slot, and 0x01BF fails SILENTLY when the "
                f"slot is empty -- no assert, no reply, nothing to see")
    return [
        (0x01D2, [party_id], f"PARTY_BUILD_BEGIN({party_id})"),
        (0x01CB, [party_id, player_number, 1],
         f"PARTY_ADD_MEMBER({party_id}, player {player_number})"),
        *inside_window,
        (0x01D3, [party_id], f"PARTY_BUILD_COMMIT({party_id})"),
        party_set_mine(party_id),
    ]


def party_set_mine(party_id=1):
    """GAME_SMSG 0x01B2 / 434 -- "this party is mine", and it RAISES an event.

    Factored out of `party_build` because it is now sent twice: once as the
    build's last step, and once again late (`authsrv.PARTY_MINE_LATE`).

    WHAT IT DOES BEYOND SETTING A POINTER, all OBSERVED on build 38833.
    Handler `0x008569E0` passes `this = [globals+0x4C]+4` and both message
    fields to `0x00858850`, which:

      * resolves the container -- field 1 == 0 selects the DEFAULT container
        `[this+0x50]`, i.e. `[[globals+0x4C]+0x54]`; 1..20 index
        `[[this+0x3c] + n*4]`;
      * STORES it back to `[this+0x50]`. That store is the one
        `PyCliGetMyPartyId` (`0x00856250`) reads and RESKIN 17.1/18 measured
        as 1 after the build -- and the one a displacement scan for `+0x54`
        cannot see, because the base is pre-biased by four so the instruction
        reads `0x50` (studies/pvpui/FINDINGS.md 16);
      * RAISES `0x10000114` on BOTH branches -- at `0x008588AD` when field 2 is
        non-zero, and via `mov eax,0x10000114` at `0x008588D1` otherwise.

    That raise is why this is worth sending twice. `0x10000114` is the only
    event whose GmView case calls the commander-model rebuild, and FINDINGS 19
    timestamped GmView subscribing to it **53 ms after** our first send.

    Returns the same `(opcode, values, label)` triple as everything else here.
    """
    if not 0 <= party_id <= 20:
        raise ValueError(
            f"party id {party_id} outside 0..20. Zero is NOT invalid here and "
            f"is not a no-op: it selects the DEFAULT container at "
            f"[[globals+0x4C]+0x54] rather than a numbered one "
            f"(studies/pvpui/FINDINGS.md 13.2 -- and read 14.1, which measured "
            f"that the default container IS party 1, so the two agree here)")
    return (0x01B2, [party_id, 1], f"PARTY_SET_MINE({party_id})")


def party_henchman_add(party_id, agent_id, enc_name, unk_a=0, unk_b=0):
    """GAME_SMSG 0x01BF / 447 -- one henchman row in the party roster.

    THE SHAPE IS THE CLIENT'S OWN, not an upstream's: read from descriptor
    table 0x00bcb788, handler 0x00856b00, worker 0x00858cb0, traced
    store-by-store (studies/heroes/FINDINGS.md 1.1). `[u16, u16,
    string16(20), u8, u8]`, 50 bytes. This CORROBORATES GWCA's published
    shape from an independent witness -- and `schema/messages.json` "447"
    carries the same string16 cap of 20, a third agreement.

    THE FIELDS, by what the client DOES with them rather than by name:
      * party_id indexes the party manager's pointer array at [this+0x3c],
        bound-checked against [this+0x44]. THE PARTY MUST BE BUILT FIRST.
        This is the gate the 2026-08-12 sweep hit: an all-zero 0x01BF takes
        the party_id==0 branch at 0x00858CD0, which resolves the "current
        party" slot from [this+0x50] -- NULL, because nothing had been
        built -- and returns SILENTLY. Zero is the one failure we cannot
        see, exactly as for 0x01B2, so it is refused here.
      * agent_id is the DEDUPE KEY: the worker scans existing 0x34-byte
        entries for it (loop 0x858D06-0x858D3C) before appending, then
        stores it as the entry's first dword.
      * enc_name is a REAL WIRE STRING, and it is the whole reason the
        henchman is easier than the hero: a henchman carries its identity
        with it, while 0x01C2 carries no name and must resolve through
        s_heroClientData. Pre-encoded string ids, never text.

    THE TWO TRAILING BYTES ARE NOT FOUND. GWCA and OpenTyria call them
    profession and level; the client stores them to entry+0x2c and
    entry+0x30 and NO ASSERT ANYWHERE NAMES THEM (`asserts.py --grep
    henchman` returns four sites, none about a level or a profession). They
    are unk_a/unk_b here on purpose -- naming them after one lineage's word
    is how UPSTREAM becomes fact by repetition. Send distinguishable values
    and read the rendered row.

    Returns (opcode, values, label).
    """
    if not 1 <= party_id <= 20:
        raise ValueError(
            f"party id {party_id} outside 1..20: same manager bound as "
            f"party_build (`cmp [esi+8], 0x14`), and 0 is the silent "
            f"'current party' branch at 0x00858CD0 -- with no party built it "
            f"resolves NULL and the message vanishes with no assert, which "
            f"is exactly the 2026-08-12 sweep's SILENT result")
    if not isinstance(agent_id, int) or agent_id <= 0:
        raise ValueError(
            f"agent_id {agent_id!r} must be a positive int: it is the "
            f"worker's dedupe key and the entry's first dword, and "
            f"PtRoster:602 looks the roster row's frame up BY it")
    if not isinstance(enc_name, str):
        raise ValueError(
            f"enc_name must be an ENCODED string (see _encstring), not "
            f"{type(enc_name).__name__}: the content store holds string ids "
            f"as a list of ints and the codec refuses the raw list")
    if len(enc_name) > 20:
        raise ValueError(
            f"enc_name is {len(enc_name)} code units, over 0x01BF's cap of "
            f"20 -- the client's own descriptor says string16(20) and so "
            f"does schema/messages.json. The measured failure mode is the "
            f"2026-08-13 one: the codec throws inside instance bring-up, the "
            f"harness still reports PASS, and the row is simply absent")
    for nm, v in (("unk_a", unk_a), ("unk_b", unk_b)):
        if not 0 <= v <= 255:
            raise ValueError(f"{nm}={v} does not fit the u8 the client reads")
    return (0x01BF, [party_id, agent_id, enc_name, unk_a, unk_b],
            f"PARTY_HENCHMAN_ADD(party {party_id}, agent {agent_id}, "
            f"{len(enc_name)} name ids, {unk_a}, {unk_b})")


HEROES = 40          # ChCliApi:4446 `hero < HEROES`, `cmp esi,0x28`. OBSERVED.
HERO_UNUSED = 0      # ChCliApi:4447, fires only on `test esi,esi`. OBSERVED.


def party_hero_add(party_id, owner_player_number, agent_id, scan_key=0,
                   unk_b=0):
    """GAME_SMSG 0x01C2 / 450 -- one hero row in the party roster.

    THE SHAPE CORRECTS THE UPSTREAM. OpenTyria's GameMsg.h:466-473 gives
    PARTY_HERO_ADD "a uint8 level"; the client's own descriptor (table
    0x00bcb788, handler 0x00856b80, worker 0x00858f50) is `[u16, u16, u16,
    u8, u8]`, 10 bytes. Three words and two bytes.
    studies/heroes/FINDINGS.md 1.2.

    WHAT EACH IDENTITY FIELD IS, and how sure. This signature was renamed
    FOUR times across 2026-08-16 as the arms ran, and the history is the
    warning: `word_a` -> `hero_index` (11.1, WRONG) -> `word_a` again (17.3
    doubted it) -> `owner_player_number` (21 measured it). Each name change
    tracked a measurement; the one that didn't (hero_index) lasted six
    hours. 0x01C2 itself carries NO hero identity at all (19) -- identity
    lives in 0x0074's data-cache record; this message only binds a party
    slot to an agent.

    * `owner_player_number` is msg+8 (stored to entry+0x4). OBSERVED (21):
      with --player-number 2 splitting player number from agent id, the
      roster row renders exactly when this word equals the declared player
      number, across three rigs. One nuance worth carrying (21.2): the
      roster UI and GmHeroCommander's scan compare entry+0x4 against
      DIFFERENT "my id" notions -- the arm that renders the row is the arm
      whose commander binding vanishes -- so this name is the roster's
      reading, and the commander's is ctx[0x44][0x2ac], which did not
      track the declared number.
    * `agent_id` is msg+0xc (stored to entry+0x0). MEASURED, the one thing
      H1/H2 truly settled: the body lived at agent 200, outside every other
      candidate range, and the row rendered only with 200 here (11.1).
    * `scan_key` is msg+0x10 (stored to entry+0x8). That the commander
      scan reads entry+0x8 as its container key is SOURCED (17.1); every
      OBSERVABLE consequence is indifferent to the value (19.2: a wrong
      value changes nothing, the right one fixed nothing), consistent with
      the scan never running in our sessions. Callers send the hero id as
      the best guess; the name deliberately does NOT say 'hero', because
      19's headline is that this message carries no hero identity.
      **RETIRED 2026-08-17: the scan RUNS now.** studies/pvpui/FINDINGS.md
      19 found the rebuild being raised into a subscriber map 53 ms too
      early; with `--party-mine-late` the raise lands late enough that
      0x00524C40 executes, and it takes THIS field as the key the
      commander is filed under (22.1; 23 steers it to 200 with
      `--hero-roster-id`). The hedge in the sentence above is why this
      retires cleanly rather than reading as a contradiction -- 19.2 was
      right about every observable it had.

    No range guard on owner_player_number or scan_key beyond the wire
    widths, deliberately: the settling arms themselves had to send
    out-of-range values (H1 put 200 at msg+8), and a guard here would have
    refused the experiments that earned these notes.

    The client also pushes TWO HARDCODED ZERO DWORDS into entry+0xc and
    +0x10 that never touch the wire -- worth knowing before anyone reads the
    entry layout and looks for the fields that fill them.

    Returns (opcode, values, label).
    """
    if not 1 <= party_id <= 20:
        raise ValueError(
            f"party id {party_id} outside 1..20: same bound and the same "
            f"silent-on-zero branch as party_henchman_add, and 0x01C2 uses "
            f"the IDENTICAL [this+0x3c]/[this+0x44] party lookup (OBSERVED), "
            f"so it inherits the same 'party must be built first' gate")
    for nm, v in (("owner_player_number", owner_player_number),
                  ("agent_id", agent_id)):
        if not 0 <= v <= 0xFFFF:
            raise ValueError(f"{nm}={v} does not fit the u16 the client reads")
    for nm, v in (("scan_key", scan_key), ("unk_b", unk_b)):
        if not 0 <= v <= 255:
            raise ValueError(f"{nm}={v} does not fit the u8 the client reads")
    return (0x01C2, [party_id, owner_player_number, agent_id, scan_key,
                     unk_b],
            f"PARTY_HERO_ADD(party {party_id}, owner {owner_player_number}, "
            f"agent {agent_id}, key {scan_key}, {unk_b})")


def mercenary_info(hero_id, b1=0, b2=0, b3=0, d1=0, d2=0, b4=0, b5=0,
                   d3=0, chunk=None, enc_name=""):
    """GAME_SMSG 0x0074 / 116 -- the per-hero DATA CACHE record.

    THE UPSTREAM SHAPE IS REFUTED. GWCA and OpenTyria publish
    `{hero_id, level, primary, secondary}`; the client's own decoder reads
    TWENTY fields, 127 bytes: `[u16, u8,u8,u8, u32,u32, u8,u8, u32, u32x10,
    string16(32)]`. Handler 0x0091e2f0 -> 0x00811560 -> 0x0081db20, which
    looks up OR CREATES a record keyed by the first field inside the LOCAL
    PLAYER's context at ctx+0x2c+0x584. studies/heroes/FINDINGS.md 1.3.

    Every field but the first is named for its TYPE and defaulted to zero,
    because that is what we know. What survives of the upstream reading is
    only that b1/b2/b3 land at record +8/+0xc/+0x10 -- consistent with
    level/primary/secondary and NOT confirmed, since no consumer of +0xc or
    +0x10 was traced to a profession bound-check. Do not rename them until
    one is.

    `chunk` is the ten trailing dwords, which the client splits into TWO
    5-dword groups stored at record +0x4c and +0x60 (with a conditional
    third copy to +0x74). Two parallel 20-byte groups, meaning NOT FOUND.

    Returns (opcode, values, label).
    """
    if not HERO_UNUSED < hero_id < HEROES:
        raise ValueError(
            f"hero id {hero_id} outside 1..{HEROES - 1}: ChCliApi:4446 "
            f"asserts `hero < HEROES` (cmp esi,0x28, HEROES==40) and :4447 "
            f"asserts `hero != HERO_UNUSED` (==0). Row 0 of "
            f"s_heroClientData is the reserved placeholder and its name "
            f"resolves to the empty string, so 0 is not merely rejected -- "
            f"it is the sentinel meaning 'no hero'")
    chunk = list(chunk or [0] * 10)
    if len(chunk) != 10:
        raise ValueError(
            f"chunk is {len(chunk)} dwords, not 10: the client copies it as "
            f"two 5-dword groups to record +0x4c and +0x60, so a short list "
            f"would silently shift the second group")
    if not isinstance(enc_name, str):
        raise ValueError("enc_name must be an ENCODED string (see _encstring)")
    if len(enc_name) > 32:
        raise ValueError(
            f"enc_name is {len(enc_name)} code units, over 0x0074's cap of 32")
    return (0x0074,
            [hero_id, b1, b2, b3, d1, d2, b4, b5, d3, *chunk, enc_name],
            f"MERCENARY_INFO(hero {hero_id}, {len(enc_name)} name ids)")


def hero_activate(hero_id, agent_id, inventory_id=0, ai_mode=0):
    """GAME_SMSG 0x0072 / 114 -- HERO ACTIVATE.

    THIS MESSAGE IS AN EXPERIMENT WITH ITS PREDICTION ALREADY ON RECORD.
    The 2026-08-12 smsgsweep sent it all-zero and the client ASSERTED:
    charHeroData wants a hero record and a level-1 character has none. That
    is a CLIENT-STATE gate, not a payload gate -- no value on the wire opens
    it (studies/smsgsweep/FINDINGS.md 5d).

    So sending it LAST, after 0x0074 and 0x01C2, is a refutable question
    with two outcomes and both are informative: assert again means nothing
    we sent created the record the gate wants, and silence means something
    did. What creates charHeroData is NOT FOUND by any static route --
    ChCliHero has two structures (0x9C-stride via 0x0081D830, a 36-byte
    list via 0x0081D880) and no message was traced into either.

    THE FIELD NAMES ARE THE CLIENT'S OWN. `0x0072`'s worker calls out through
    0x0046ed40 with the format string at 0xa95888:
    `HeroActivate (hero %d, agent %d, inventoryId %d, aiMode %d)` -- four
    fields, in this order, matching the descriptor
    `[word, agent_id, dword, dword]` exactly. `aiMode` is the Fight/Guard/
    Avoid-Combat stance (CHAR_AI_MODES == 3), so the stance IS server-settable,
    which is a partial answer to the arc's c2s question: we cannot yet see the
    client CHANGE it, but we can set it.

    Returns (opcode, values, label).
    """
    if not HERO_UNUSED < hero_id < HEROES:
        raise ValueError(f"hero id {hero_id} outside 1..{HEROES - 1}")
    return (0x0072, [hero_id, agent_id, inventory_id, ai_mode],
            f"HERO_ACTIVATE(hero {hero_id}, agent {agent_id}, "
            f"inventory {inventory_id}, aiMode {ai_mode})")


def player_flags(player_number, value, mask=7):
    """GAME_SMSG 0x003C -- three bits in the player record, cleared then written.

    OBSERVED 2026-08-13 over ArenaNet's own captures, read whole with
    `tape.decode_all`: **423 sends across 12 of 12 live game connections**, all
    inside the instance load (t = 0.23-0.73 s). This server had sent it ZERO times
    in 190 played captures.

        mask (the second dword) is 7 in 423 of 423
        value (the first)       is 4 x287, 5 x60, 0 x48, 7 x12, 6 x12, 1 x4

    Every value lies inside the mask and the mask never varies, which is what makes
    this (value, mask) rather than the (set, clear) an earlier read proposed. It
    matches the handler clearing with an `and` at 0x0080EC26 and writing with an
    `or` at 0x0080EC48 into `[playerRec+0x34]` -- the same ctx+0x80C stride-0x50
    array 0x00B0/0x00B1 write. UPSTREAM for the two addresses (the party dive);
    OBSERVED for everything above.

    **A lone player is (player, 4, 7) in every single-connection capture**, three
    times, and 5/6/7/1 appear only in the busy ones -- so 4 is the value to send for
    a party of one and the others are not ours to guess at.

    Sending it LATE does nothing: studies/profession/RESKIN.md 18.8 swept 4 -> 0 -> 7
    at 5-17 s with the party roster open and measured 0.000% change in the party
    region across all 18 frame transitions. That is why this exists as a burst
    message rather than a probe -- the open question is whether bits read once at
    BUILD time behave differently, and only a load-time send can ask it.
    """
    if not 0 <= player_number <= 0xFFFF:
        raise ValueError(f"player number {player_number} does not fit the u16 field")
    if mask == 0:
        raise ValueError("mask 0 writes nothing: the handler clears with ~mask and "
                         "ors the value in, so a zero mask is a no-op message")
    if value & ~mask:
        raise ValueError(
            f"value {value:#x} has bits outside mask {mask:#x}: the handler ANDs "
            f"with ~mask before ORing the value, so bits {value & ~mask:#x} would "
            f"be discarded. All 423 observed sends satisfy value & ~mask == 0")
    return [player_number, value, mask]


def player_party_size(player_number, size):
    """GAME_SMSG 0x00B0 -- how many members the player's party holds.

    OBSERVED (build 38797): handler 0x0091EFC0 forwards to 0x00813850, a thin
    two-argument worker that writes the per-PLAYER array at ChCliApi
    ctx+0x80C, stride 0x50. It touches no agent, so it depends only on
    PLAYER_CREATE (0x0059) having made the player record -- never on the
    agent create.

    Five bytes on the wire: u16 player, u8 size.
    """
    if size < 1:
        raise ValueError(f"party size {size} < 1: the local player is always a "
                         f"member of their own party, so 0 is not a state the "
                         f"client is ever sent")
    return [player_number, size]


def player_set_party(player_number, leader_number):
    """GAME_SMSG 0x00B1 -- which party (by leader) a player belongs to.

    OBSERVED: handler 0x0091F050 -> 0x00813980, the same shape and the same
    per-player array as 0x00B0. A solo player is their own leader, so both
    fields are the player's own number.

    ORDER, and it is the one thing measured about these two: 0x00B0 fires no
    event for a fresh entry and 0x00B1 fires only on a LEADER CHANGE, so the
    pair is sent size-then-leader. Sending the leader first makes the change
    a no-op against the default and the roster is never notified.
    """
    return [player_number, leader_number]


def agent_set_secondary_bits(agent_id, mask):
    """GAME_SMSG 0x00B6 -- which professions this agent may take as SECONDARY.

    The client's own name for it, SOURCED from the format string at 0xA95A70
    which names both fields: `OnProfessionSecondaryBits (agent %d,
    secondaryBits %d)`. studies/profession/RUNS.md §13.

    ORDER MATTERS AND THE FAILURE IS SILENT. The handler writes field +0xC of
    the per-agent record at ctx[0x2c]+0x6BC, and it finds that record by
    binary search: on a MISS it logs the string above and RETURNS WITHOUT
    STORING (0x0081FD00). The record is created by 0x00B7, so a 0x00B6 sent
    before this agent's first 0x00B7 is dropped with no wire error and no
    visible effect. A later 0x00B7 does NOT clobber the mask -- the zeroing at
    0x0081FD95 is on the record-CREATION path only.

    WHAT IT CANNOT DO. The consumer loops `cmp edi, 0xb` (ids 0..10), so this
    message cannot offer a custom profession as a secondary however the mask
    is set. That bound is compiled in; no server message moves it.
    """
    if not 0 <= mask <= 0xFFFFFFFF:
        raise ValueError(f"secondary mask {mask:#x} does not fit the u32 field")
    return [agent_id, mask]


def agent_set_tabard_visible(agent_id, visible):
    """GAME_SMSG 0x0048 -- gate the guild cape/tabard composite for one agent.

    Send 0 for any agent whose guild id we never populated, which is all of
    ours: it makes the client skip a guild lookup on an id that does not exist.
    ArenaNet sends this after EVERY 0x006E -- 366 of 366 across both captures.
    """
    return [agent_id, 1 if visible else 0]


def create_agent(agent_id, model_id, kind, x, y, plane,
                 allegiance=ALLEGIANCE_PLAYER, speed=DEFAULT_RUN_SPEED):
    """GAME_SMSG 0x0020, 23 fields, 99 bytes on the wire.

    The field order is the one the player's own body has always used and which
    the client's message-format table confirms; the offset-named fields are
    unknowns carried verbatim rather than guessed at. See
    studies/character/FINDINGS.md section d for what is and is not known here.
    """
    return [agent_id, model_id, AGENT_TYPE_LIVING, kind,
            (float(x), float(y)), plane, (1.0, 0.0), 1,
            speed, 1.0, 0x41400000, allegiance,
            0, 0, 0, 0, 0, (0.0, 0.0), (INF, INF), 0, 0, (INF, INF), 0]


# ---------------------------------------------------------------- items
#
# A character with no weapon cannot attack and cannot use a weapon skill, and
# until 2026-08-06 ours had none: we sent four ITEM_WEAPON_SET slots of zeros
# and never created an item. The visible symptoms were that ATTACK_AGENT was
# never sent by the client at all -- not on click, not on space, in an outpost
# or in an explorable -- and that weapon skills would not even begin to cast.
#
# ItemType, from OpenTyria's GmItem.h enum. UPSTREAM.
ITEM_TYPE_HAMMER = 15

# The Prophecies warrior's starting weapon, verbatim from OpenTyria's
# GmDefaultArmors.c:80-93 (the sixth and last entry of
# g_DefWarriorPropheciesPveEquipments -- that array is 5 armour pieces plus one
# ItemType_Hammer). UPSTREAM: it is one lineage's hand-written table, and no
# capture of ours has ever carried these bytes. The two things worth watching
# if the client refuses it are file_id and flags.
#
# The name words are pre-encoded GW string ids, not text -- the same class of
# value as the NPC EncStrings. They can be copied and cannot be invented.
STARTER_HAMMER = _row("item", "starter_hammer")


def item_template(key):
    """A usable ITEM template by name -- npc_template's sibling, same reason.

    `enc_name` arrives as a list of GW string ids and must be ENCODED before
    named_item() can put it on the wire; a caller reaching for the raw row
    builds a message the codec refuses. See npc_template's docstring for the
    day that cost a silent empty population.
    """
    return _row("item", key)


def named_item(item_id, item):
    """GAME_SMSG 0x0161 CREATE_NAMED_ITEM -- declares an item's bytes.

    Declares only. Nothing is placed in a bag and nothing is worn: those are
    ITEM_MOVED_TO_LOCATION and the equipment messages respectively. See
    studies/character/FINDINGS.md section 2.

    The trailing modifier list is the client's field type 12, whose element
    layout is the schema tail and whose wire count is ONE byte -- so each
    modifier is passed as a single-element row.
    """
    return [item_id, item["file_id"], item["item_type"], item["dye_tint"],
            item["dye_colors"], item["materials"], item["unk1"], item["flags"],
            item["value"], item["model_id"], item["quantity"], item["enc_name"],
            [[m] for m in item["modifiers"]]]


# ------------------------------------------------- generic values (combat)
#
# The agent-property channel does not only carry health. Py4GW calls these
# GENERIC_VALUE_IDS (Py4GWCoreLib/PacketSniffer.py:263-277) and they are how the
# server drives combat animation on the client.
#
# UPSTREAM for the NAMES -- that is Py4GW's vocabulary, one lineage, no capture
# of ours carries them. CORROBORATED for the GROUPING, and by our own bytes:
# studies/agentprops/FINDINGS.md section 3b measured the int channel's second
# dispatch and found properties {4, 50, 60} sharing a single case. Py4GW
# independently names 50 attack_skill_activated and 60 skill_activated. Two
# lineages putting the same two ids in the same bucket is worth more than
# either alone -- but it is still not a wire OBSERVATION, and until one of
# these visibly changes the client these stay UPSTREAM.
GV_MELEE_ATTACK_FINISHED = 1
GV_ATTACK_STOPPED = 3
GV_DISABLED = 8
GV_SKILL_DAMAGE = 10
GV_MAX_HP_REACHED = 32
GV_INTERRUPTED = 35
GV_ATTACK_SKILL_FINISHED = 46
GV_INSTANT_SKILL_ACTIVATED = 48
GV_ATTACK_SKILL_STOPPED = 49
GV_ATTACK_SKILL_ACTIVATED = 50
GV_SKILL_FINISHED = 58
GV_SKILL_STOPPED = 59
GV_SKILL_ACTIVATED = 60


# ------------------------------------------------- the player's own pools
#
# We gave the ENEMY a health pool on the day it was spawned and never gave the
# player one. Not health, not energy, in any session. Every skill on the default
# bar costs 5 energy or 4-5 adrenaline, so an empty pool refuses all eight, which
# is exactly the observed symptom: the press animation plays and the cast never
# starts.
#
# Property 41 = energy, 42 = health, both on the int channel. CORROBORATED:
# gw-preservation's working server sends exactly these two in
# gameservice/player.go:268-269 with a comment naming each, and our own binary
# read of the int-record dispatch found cases for {32, 41, 42} and nothing else
# (studies/agentprops/FINDINGS.md section 3b). We had already MEASURED 42 as
# maximum health. 41 is the only remaining slot in that dispatch, and the one
# upstream calls energy.
PROP_ENERGY_MAX = 41

# Property 43 on the FLOAT channel. gw-preservation sends 0.0396 and its own
# comment says "REVERSE THIS MORE", so nobody upstream knows what it is either;
# our float-record dispatch does have a real case for 43. Energy regeneration is
# the obvious reading and is a GUESS -- it is here because it travels with the
# pair above in a server that works, not because we know what it does.
PROP_UNKNOWN_FLOAT_43 = 43
_PLAYER = WORLD.get("player", "defaults")
PLAYER_ENERGY = _PLAYER["energy"]
PLAYER_HEALTH = _PLAYER["health"]
PLAYER_FLOAT_43 = _PLAYER["float_43"]

# The player's attribute ranks, as (attribute_id, rank) pairs. The IDS are the
# client's own s_attrib indices (attribtable.py); the RANKS are invented and
# the content row says so -- nothing in the vault can source them, because
# 0x003A never appears in a live capture and no c2s spend opcode was found.
# Tuples rather than the TOML's lists so a caller cannot mutate the module's
# copy, which is the same reason ENEMY_SKILLS is a tuple of tuples.
PLAYER_ATTRIBUTE_RANKS = tuple(
    (int(a), int(r)) for a, r in WORLD.get("player", "attributes")["ranks"])


# ------------------------------------------------- what an agent WIELDS
#
# Two different questions, and we had only answered the first:
#   0x006E UPDATE_AGENT_VISUAL_EQUIPMENT -- what the weapon LOOKS like (item ids)
#   0x006D NPC_UPDATE_WEAPONS            -- what KIND of weapon the agent wields
#
# The second drives attack range, speed and animation. GWCA reads the field it
# sets as AgentLiving::weapon_type at +h01B2, a uint16 sitting immediately after
# allegiance at +h01B1 (GameEntities/Agent.h:222-223) -- the combat block of the
# agent struct.
#
# This enum is NOT ItemType. A hammer is ItemType 15 and weapon_type 3, and
# using one where the other belongs is the obvious way to get this wrong.
# UPSTREAM: GWCA's comment is the only source, and it lists no value for 0.
WEAPON_TYPE_BOW = 1
WEAPON_TYPE_AXE = 2
WEAPON_TYPE_HAMMER = 3
WEAPON_TYPE_DAGGERS = 4
WEAPON_TYPE_SCYTHE = 5
WEAPON_TYPE_SPEAR = 6
WEAPON_TYPE_SWORD = 7
WEAPON_TYPE_WAND = 10
WEAPON_TYPE_STAFF = 12


# ------------------------------------------------- how fast an agent swings
#
# GAME_SMSG 0x0035 is the ONLY thing in the client that gives an agent an
# attack speed, and without it the client cannot animate a melee attack at all.
# SOURCED, read end to end out of build 38797 -- see studies/enemy/PLAN.md 6q:
#
#   0x0035 handler 0x0091D810   reads {agent_id, float, float} off the message
#     -> 0x0080EA60             thin forwarder, same three arguments
#     -> 0x007E0690  AvApi      agent id -> AvChar*, asserts the lookup
#     -> 0x007FBD30  AvChar::SetAttackSpeed(base, modifier)
#          asserts base != 0     AvChar.cpp:7207, ArenaNet's own name `base`
#          asserts modifier != 0 AvChar.cpp:7208, their name `modifier`
#          [this+0xEC] = base ; [this+0xF0] = modifier
#
# The constructor at 0x007F1FD2 initialises BOTH to 0.0, and the animation path
# asserts both non-zero on the way in (AvChar.cpp:4791 m_attackInterval, 4792
# m_attackModifier). So an agent the server never told has an attack speed of
# zero, and telling the client to start a swing kills it. That is the whole of
# the m_attackInterval crash, and it is why nothing we equipped ever helped:
# equipment was never the channel. This message is.
#
# The two fields, and what they mean -- CORROBORATED, wiki + GWCA + our own
# disassembly, three sources with no shared ancestry:
#
#   +0xEC `base`     seconds between attacks for the weapon type
#   +0xF0 `modifier` multiplier on that duration; 1.0 = none, 0.75 = +25% IAS,
#                    0.67 = +33% IAS (an IAS makes each attack SHORTER)
#
# The client multiplies them at 0x007F837E (`fld [esi+0xf0]; fmul [esi+0xec]`),
# and that product reproduces the wiki's published IAS table exactly for three
# weapon classes and two modifiers -- 1.33/1.5/1.75 against 0.67 and 0.75 give
# 0.8911/1.005/1.1725 and 0.9975/1.125/1.3125, six for six to four decimals.
# A check that could have failed and did not.
#
# WIKI (GWW, "Attack speed" section "Attack durations and effect of IAS and
# DAS", read 2026-08-06), whose table says outright "These are the exact values
# used by the game". GWCA's Agent.h:181-182 independently names the same two
# offsets weapon_attack_speed and attack_speed_modifier and gives 1.33 for
# axe/sword/daggers and "0.67 = 33% increase", agreeing on both.
_RATES = dict(WORLD.get("attack_speed", "rates"))
ATTACK_SPEED_UNMODIFIED = _RATES.pop("unmodified_modifier")
ATTACK_SPEED = _RATES
# No increase and no decrease. The field may not be zero -- the client asserts
# on that at both ends -- so "unmodified" is 1.0, never 0.


# ------------------------------------------------- attackable, or merely red
#
# Being RED and being ATTACKABLE turned out to be two different things, and we
# had only ever arranged the first. The FourCC team token in WORLD_CREATE_AGENT
# field 12 decides colour: ours says 'mons', the client does not recognise it,
# and an unrecognised token renders hostile. But clicking the result made the
# client send INTERACT_PLAYER (0x0033) and never ATTACK_AGENT (0x0026) --
# OBSERVED across every session so far -- which is what it does for an NPC you
# talk to, not one you fight. It did not help that we built the thing out of a
# Collector definition.
#
# The field that actually decides is AgentLiving::allegiance at +h01B1, a single
# byte. UPSTREAM: GWCA GameEntities/Agent.h:222 is the only source for the
# values, and it names 1 as "ally/non-attackable" and 3 as "enemy" outright.
# GAME_SMSG_AGENT_UPDATE_ALLEGIANCE 0x002F carries it: the handler at 0x005fdd70
# reads field 1 as an agent-array index (bounds-checked, asserts if out of
# range) and hands field 2 to a setter for that agent in two collections --
# SOURCED, read from this build.
ALLEGIANCE_ALLY_NONATTACKABLE = 1
ALLEGIANCE_NEUTRAL = 2
ALLEGIANCE_ENEMY = 3
ALLEGIANCE_SPIRIT_PET = 4
ALLEGIANCE_MINION = 5
ALLEGIANCE_NPC_MINIPET = 6


# ------------------------------------------------- the fuller generic-value table
#
# GWCA's GenericValueID namespace (Packets/StoC.h:36-70) is a second, richer
# lineage than the Py4GW list above, and it corrects one of our sends: 1 is
# melee_attack_FINISHED, the end of a swing, not the start. We sent it and got
# no animation, which is exactly right for an id that means "that one is over".
#
# It also corroborates three things we had already measured ourselves --
# 16 damage, 34 health, 55 armour-ignoring -- and it names 4 attack_started,
# which lands in the same client dispatch case as 50 and 60 that our own read
# of the int table found ({4, 50, 60}, studies/agentprops/FINDINGS.md 3b).
# Independent naming agreeing with our own bytes is the best support anything
# in this file has.
#
# GWCA also names the four message shapes these travel on:
#   GenericValue          int,   no target    -- 0x009F
#   GenericValueTarget    int,   with target  -- 0x00A0 (same shape as 0x00A3)
#   GenericFloat          float, no target    -- 0x00A2
#   GenericTargetModifier float, with target  -- 0x00A3
# The first and last are OBSERVED working. The middle two were INFERRED from the
# field shapes matching, with nothing confirming them on the wire --
# CORROBORATED 2026-08-11 by the client's own dispatch table, which is a witness
# that was not consulted to make the claim. `msghandler.py --classify` reads the
# handler each opcode forwards to: 0x009F and 0x00A0 both hand off to
# 0x008128F0, 0x00A2 and 0x00A3 both hand off to 0x00813040, and the two
# functions are different. So the client itself splits these four exactly along
# the int/float line GWCA names them by, and the with-target member of each pair
# carries one more field than the no-target member -- 5 against 4.
# It is evidence rather than a coincidence because sharing is RARE: 241
# forwarding handlers resolve to 215 distinct callees and only 8 callees are
# shared by more than one opcode at all. `test_msghandler.py` pins both the
# pairing and that base rate, since the pairing means nothing without it.
# Still not confirmation of the SEMANTICS -- it says these four are two pairs of
# the same kind, not what any of them does.
# GenericValueTarget. GWCA's note reads "caster_id is victim, target_id is
# attacker"; OBSERVED on our own client, the FIRST agent slot is the one that
# plays the swing -- the attacker. See hit_enemy() for the run that showed it
# and why a crash proved it more cleanly than watching the screen could.
GV_ATTACK_STARTED = 4
GV_ADD_EFFECT = 6
GV_REMOVE_EFFECT = 7
GV_CRITICAL = 17
# CONFIRMED 2026-08-18 on retail traffic -- this name was UPSTREAM from ONE
# lineage (Py4GW) and CONTESTED for months; the corpus could only say "17 is a
# damage kind occupying a swing slot", which blocked, glancing and a bonus kind
# all satisfy. The Isle rung-7 damage pass settles it four ways at once
# (`studies/isle/FINDINGS.md` "Rung 7, LIVE #2" 4):
#   * the pre-registered ZERO-VARIANCE law holds 10 of 10 blocks, 100 of 100
#     events -- a critical always deals the weapon range's MAXIMUM, so it pins
#     to one value while property 16 spreads over the range;
#   * p16 + p17 = 495 = exactly one event per swing at a 1.330 s median gap in
#     every block, so 17 REPLACES 16 rather than annotating it;
#   * one multiplier fits NINE blocks inside a 0.83% window, [1.40866,
#     1.42045), which contains sqrt(2) -- i.e. the target's armour reduced by
#     20, since 2^(20/40) = sqrt(2). To +-0.8%, so 1.41 and 1.42 also fit;
#   * crit RATE rises monotonically with attribute rank on one body at one
#     armour rating: 6.25 / 15.69 / 18.60 / 23.68 / 34.29% at ranks
#     8/9/11/12/13. A cap or a fixed bonus has no reason to do that.
# The one block it does NOT fit is the unmet-requirement rank-8 block, and that
# failure belongs to the unmet-requirement term rather than to this one: rank 8
# admits c in [1.20530, 1.36600), disjoint from the nine met blocks, and no
# rounding rule reconciles them. OPEN, and named in that study 9.
GV_EFFECT_ON_TARGET = 20
GV_EFFECT_ON_AGENT = 21
GV_ANIMATION = 22
GV_ANIMATION_SPECIAL = 23
GV_ANIMATION_LOOP = 28
# Same wire property as PROP_HEALTH_ABSOLUTE above -- read that comment first.
# ITS OLD NOTE WAS EXACTLY BACKWARDS and is recorded here because the mistake is
# instructive. It said "a DELTA, not a setter -- we measured -50.0 as -50 health";
# 34 is a SETTER and nothing else, and the -50.0 measurement was reading the pool's
# FLOOR rather than a subtraction (the bar was already at 50, where a delta and a
# setter both predict empty). The `pool_fraction` probe sent -0.5 at a FULL bar,
# where the two differ by a factor of 100, and the orb went to 1.
GV_HEALTH = 34
GV_CHANGE_HEALTH_REGEN = 44
GV_ENERGY_GAIN = 52
GV_ARMOR_IGNORING = 55
GV_CASTTIME = 61
GV_ENERGY_SPENT = 62
GV_KNOCKED_DOWN = 63
