"""Which agent properties the client acts on, and whether they are int or float.

    python toolkit/clientscan/genericvalue.py --exe <pinned exe>
    python toolkit/clientscan/genericvalue.py --exe <pinned exe> --id 60
    python toolkit/clientscan/genericvalue.py --exe <pinned exe> --csv

WHY THIS EXISTS. `studies/skills` calls the agent-property enum "the one place
in the whole pass where three lineages agree across thirteen years" and says
that if Rurik ever builds a skill-effect oracle, this enum is its vocabulary.
It is also where those lineages disagree most: OpenTyria and GWCA give
different names to ids 8, 35, 49, 52, 53, 58 and 59, and 14 of OpenTyria's 66
entries are named only by their own number.

The client settles part of it structurally, without needing any name. There are
**two** dispatchers, not one:

    AGENT_PROPERTY_UPDATE_INT     159 / 0x009F  -.
    AGENT_PROPERTY_UPDATE_INT_TARGET  160 / 0x00A0 -> ChCliApi 0x008128F0
    AGENT_PROPERTY_UPDATE_FLOAT   162 / 0x00A2  -.
    AGENT_PROPERTY_UPDATE_FLOAT_TARGET 163 / 0x00A3 -> ChCliApi 0x00813040

and their MAIN switch tables are **disjoint and complementary**: every id the
float dispatcher's main switch handles falls to the int dispatcher's default,
and vice versa. So a property id is an INT property or a FLOAT property, and
sending one on the wrong message is silently ignored -- no error, no log line,
nothing. That is worth knowing before a server spends an evening wondering why
a health-regen update does nothing.

SEVEN SWITCHES, NOT TWO, and the correction that forced this note. Each
dispatcher runs the property id past more than one switch before the main one,
and the first version of this module modelled only three of the seven. It
therefore reported ids 5, 8, 40 and 51 as "handled by neither", and three of
those four were wrong -- 5 and 51 are handled by the float dispatcher's
AgentView switch and 8 by the int one's. Only 40 is genuinely untouched. The
lesson is the same one msgshape.py carries: a partial model of the client
produces answers that are self-consistent and false, and nothing in the output
says so. The seven, in the order each dispatcher runs them -- addresses ON BUILD
38797, cited so a reader can check the claim against that image, and NOT how the
module finds them (see `locate()`; run `--locate` to print any build's):

    int   0x008128F0  ->  int-store       0x00818170  compare chain, 3 ids
                          int-agentview   0x0081BC60  table, only when the
                                                      agent resolves to type 1
                          int-pre         table, ids 4..64
                          int-main        table, ids 0..66
    float 0x00813040  ->  float-store     0x00818210  table, ids 16..62
                          float-agentview 0x0081BD80  compare chain, 3 ids
                          float-main      table, ids 16..63

Two of the seven are compare chains rather than jump tables, so they cannot be
read as data. Their ids and case bodies are PARSED out of the comparisons, and
the byte string encoding those comparisons is checked first, so a build that
renumbers or reorders one is refused rather than answered from memory.

Both dispatchers also gate the main switch behind `test byte [charContext +
0x53C], 2` -- when that bit is set the main switch is skipped entirely and only
the earlier switches run. The gate is located inside each dispatcher, and there
must be exactly one.

This module extracts every table from the image and reports, per id, which
switches act on it and what their case bodies are. The names alongside are the
reconstructions', quoted so a disagreement is visible; the binary supplies the
grouping, not the vocabulary.

NOTHING HERE IS LOOKED UP BY ADDRESS, as of 2026-08-14. Every switch is found
from the client's own receive table downwards, which is why this file reads
build 38519, 38797 and 38833 alike and why its class-(a) census went 27 -> 0.
The addresses above are CITATIONS: provenance for a reader, checked by
`test_genericvalue.py` against a fresh derivation, and never consulted at run
time. `studies/crossbuild/FINDINGS.md` §8.

STANDARD LIBRARY ONLY, and the derivation keeps it that way. The dispatchers are
reached through `msgshape.py`, which is also stdlib-only; the two instruction
shapes this file needs (`call rel32` and the `movzx`/`jmp` pair) are matched as
bytes inside a single function body, with every count asserted. Carve-out (1)
covers `msghandler.py` and `codescan.py`, not this file, so importing a
disassembler here would be a new dependency rather than an existing one.

READ ONLY. Opens the exe for reading and nothing else.
"""

import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE                                          # noqa: E402
import pinned                                                # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory, and names the copy it returned so a surprising result can be
# diagnosed in one line. This module used to spell it `C:\gw\Gw.exe` -- the
# owner's live install, which auto-updates and is therefore not necessarily the
# build every address in the studies is measured against.
find_exe = pinned.find

# Build 38797. Each entry: (dispatcher VA, first id, last id, the switch's own
# dispatch site, default-case VA).
#
# THE TABLE ADDRESSES ARE NO LONGER STORED -- `studies/crossbuild/PLAN.md` §6.
# They used to be, as `jt=` and `bt=`, and nothing checked them: this module's
# docstring claimed "a build that moves them fails loudly instead of returning a
# stale map that still looks plausible", which was true of `CHAINS` below and
# false of everything here. `read_switch` verified only that an index landed
# inside the table it had just read -- internal consistency, which catches a
# corrupt read and not a moved one.
#
# `at` is the switch's own `movzx`/`jmp` pair, and the two table addresses are
# read OUT of it:
#
#     0f b6 80 <bt32>       movzx eax, byte [eax + byte-index table]
#     ff 24 85 <jt32>       jmp   [jump table + eax*4]
#
# so the tables are derived from the instruction that references them rather
# than remembered beside it, and the opcode framing is what makes `at` refutable.
# That removes 10 of this file's hardcoded addresses and gates the rest.
#
# ~~WHY `at` IS STILL PINNED~~ -- IT IS NOT, as of 2026-08-14. That paragraph
# read: "this instruction shape occurs 596 times in `.text` on build 38797, so
# it is not an anchor. Making these fully derived means anchoring the
# DISPATCHERS first -- they are reached from the message handler -- which is a
# separate job and is not this one." Both halves were right, and build 38833
# turned the second one into the job: this module REFUSED that build (its
# int-main site is restructured) and took `avevents.py`'s property map with it.
# `studies/crossbuild/FINDINGS.md` §7.1.
#
# So the dispatchers are anchored first, exactly as that note said they must be,
# and everything else falls out of them. `locate()` below is the whole
# derivation; nothing in this file is looked up by address any more. The route:
#
#   1. the client's own RECEIVE table gives the handler for opcode 0x009F (int)
#      and 0x00A2 (float). `msgshape.derive_tables` finds those tables from
#      `MsgChannel::RegisterMsgs`, anchored BY BYTE SHAPE -- so the chain bottoms
#      out in a shape, not an address.
#   2. each handler is a FORWARDER: exactly one `call rel32` in its body, and its
#      target is the dispatcher. Exactly one is asserted, not assumed.
#   3. inside the int dispatcher: exactly TWO `movzx`/`jmp [table]` sites, which
#      are int-pre then int-main. Inside the float one: exactly ONE, float-main.
#   4. the dispatcher's call targets that themselves contain an id switch are
#      exactly TWO, in call order the STORE then the AGENTVIEW.
#   5. each switch's default case is the jump target the most ids share; each
#      chain's ids and case bodies are parsed out of its compare/jz pairs.
#
# Every "exactly N" above is checked and refused on, which is what makes this a
# derivation rather than a search that takes the first plausible hit.
INT_OPCODE, FLOAT_OPCODE = 0x009F, 0x00A2

# WHAT BUILD 38797 MEASURED BY HAND now lives in `test_genericvalue.py`, not
# here, and the move is the point rather than tidiness. Under
# `studies/crossbuild/PLAN.md` §6's taxonomy a hand-measured address is class
# (a) -- the per-build liability -- for exactly as long as the tool COMPUTES
# with it, and class (c) -- a wanted expectation -- once its only reader is a
# test. Keeping the witness in this file would have left `buildpins` counting
# 25 live constants in a module that no longer looks anything up, which is the
# census lying in the safe direction. The test asserts the derivation
# reproduces every one of them on 38797.
#
# The id RANGE each switch covers is derived too, from the guard MSVC emits
# ahead of each one (`lea`/`add` to rebase, `cmp` against the span, `ja` to the
# default) -- see `_switch_span`. Ranges are property ids rather than addresses,
# so they were never build-coupled the way a VA is, but reading them means a
# build that WIDENS a switch is read correctly instead of truncated.

# The two compare-chain switches. MSVC emitted `sub`/`cmp` + `je` rather than a
# jump table because each has only three cases, so there is no table to read as
# data. These byte strings encode the comparisons and are what make the parsed
# ids refutable: a build that renumbers a property, adds a case or reorders the
# chain changes them. MEASURED unchanged on all three vaulted builds.
CHAIN_VERIFY = {"int-store": "83ea20745e83ea09742483ea017572",
                "float-agentview": "83f805740a83f833740583f83d7509"}

# `test byte ptr [edi/esi + 0x53C], 2` in each dispatcher: when that bit is set
# the MAIN switch is skipped and only the earlier switches run. Located by this
# shape INSIDE the dispatcher body -- on its own it is not an anchor (7 and 3
# hits in `.text` for the esi and edi forms), which is why it is scoped.
GATE_TAIL = bytes.fromhex("3c05000002")

# ldufr/OpenTyria `code/GmAgentProperties.h`. 66 entries, 0..65. UPSTREAM.
OPENTYRIA = {
    0: "Appearance", 1: "Value1", 2: "MeleeAttack", 3: "MeleeSkillAttack1",
    4: "Attack", 5: "Value5", 6: "ApplyAura", 7: "RemoveAura",
    8: "FreezePlayer", 9: "ShakeScreen", 10: "SkillDamage", 11: "ApplyMarker",
    12: "RemoveMarker", 13: "Value13", 14: "AddArmor", 15: "ArmorColor",
    16: "DamageModifier1", 17: "DamageModifier2", 18: "Value18",
    19: "Value19", 20: "ApplyEffect1", 21: "ApplyEffect2",
    22: "ApplyAnimation", 23: "DivineAura", 24: "Value24", 25: "ShowWings",
    26: "ShowRank", 27: "ShowZaishenRank", 28: "ApplyAnimationLoop",
    29: "BossGlow", 30: "ApplyGuild1", 31: "ApplyGuild2", 32: "Value32",
    33: "EnergyModifier1", 34: "HealthModifier1", 35: "Knockdown1",
    36: "PublicLevel", 37: "LevelUp", 38: "AttackFail", 39: "PickUpItem",
    40: "Value40", 41: "Energy", 42: "Health", 43: "EnergyRegen",
    44: "HealthRegen", 45: "Value45", 46: "MeleeSkillAttack2", 47: "Value47",
    48: "Value48", 49: "InterruptAttack", 50: "CastAttackSkill",
    51: "Value51", 52: "EnergyModifier2", 53: "EnergyModifier3",
    54: "EnergyVisual", 55: "HealthModifier2", 56: "HealthModifier3",
    57: "Value57", 58: "FightStance", 59: "InterruptSkill", 60: "CastSkill",
    61: "CastTimeModifier", 62: "EnergyModifier4", 63: "Knockdown2",
    64: "Value64", 65: "PvPTeam",
}

# GregLando113/GWCA `Include/GWCA/Packets/StoC.h`, namespace GenericValueID.
# Partial by design -- GWCA only names what it needed. UPSTREAM.
GWCA = {
    1: "melee_attack_finished", 3: "attack_stopped", 4: "attack_started",
    6: "add_effect", 7: "remove_effect", 8: "disabled", 10: "skill_damage",
    11: "apply_marker", 12: "remove_marker", 16: "damage", 17: "critical",
    20: "effect_on_target", 21: "effect_on_agent", 22: "animation",
    23: "animation_special", 28: "animation_loop", 32: "max_hp_reached",
    34: "health", 35: "interrupted", 44: "change_health_regen",
    46: "attack_skill_finished", 48: "instant_skill_activated",
    49: "attack_skill_stopped", 50: "attack_skill_activated",
    52: "energygain", 55: "armorignoring", 58: "skill_finished",
    59: "skill_stopped", 60: "skill_activated", 61: "casttime",
    62: "energy_spent", 63: "knocked_down",
}

# MEASURED on build 38797. The client's own name for the 0/1 discriminator
# passed to the AgentView stat helpers, from AvChar.cpp's assert
# `stat == AV_CHAR_STAT_ENERGY`, which is guarded by `if (stat != 0)` -- so
# ENERGY is 0 and the other value is health.
AV_CHAR_STAT_ENERGY = 0


class Image:
    def __init__(self, path=None):
        path = path or find_exe()[0]
        self.pe = PE(path)
        self.base = self.pe.image_base

    def read(self, va, n):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            raise ValueError(f"0x{va:08x} is not backed by file bytes")
        return self.pe.data[off:off + n]

    def mapped(self, va):
        """Is `va` backed by file bytes? Asked before trusting an address the
        image itself named, so a wild pointer is a refusal and not a traceback
        from somewhere further down."""
        return self.pe.rva_to_off(va - self.base) is not None

    def off(self, va):
        return self.pe.rva_to_off(va - self.base)

    def va_of(self, off):
        return self.base + self.pe.off_to_rva(off)

    def u32(self, va):
        o = self.off(va)
        return None if o is None else struct.unpack_from("<I", self.pe.data, o)[0]

    def body(self, va):
        """(start_off, end_off) of the function at `va`, by MSVC's int3 padding.

        The same boundary rule `avevents.py` and `test_worldmap.py` use. It ends
        at the first `int3`, which is a pad byte between functions and never a
        real instruction in compiled MSVC output.
        """
        o = self.off(va)
        if o is None:
            raise ValueError(f"0x{va:08x} is not backed by file bytes")
        d, i = self.pe.data, o
        while i < len(d) and d[i] != 0xCC:
            i += 1
        return o, i

    # -- the derivation ----------------------------------------------------
    @property
    def located(self):
        """The derived switch map, computed once per image."""
        if getattr(self, "_located", None) is None:
            self._located = locate(self)
        return self._located

    @property
    def switches(self):
        """The five TABLE switches, name -> spec, in the order each runs."""
        return self.located["tables"]

    @property
    def chains(self):
        """The two COMPARE-CHAIN switches, name -> spec."""
        return self.located["chains"]

    @property
    def gates(self):
        """The two main-switch gate VAs, int first."""
        return self.located["gates"]


def _calls(img, start, end):
    """Every `call rel32` target in [start, end), in address order, deduped.

    A byte scan rather than a disassembly: this module takes no third-party
    dependency (carve-out (1) names `msghandler.py` and `codescan.py`, not this
    file), and `E8` immediately followed by a displacement that lands inside
    `.text` is specific enough when the window is one function body. Every
    consumer below checks a COUNT, so a stray match is refused rather than used.
    """
    d, out = img.pe.data, []
    for i in range(start, max(start, end - 5)):
        if d[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", d, i + 1)[0]
        tgt = img.va_of(i + 5) + rel
        if img.mapped(tgt) and tgt not in out:
            out.append(tgt)
    return out


def _switch_sites(img, start, end):
    """Every `movzx`/`jmp [table]` site in [start, end), in address order."""
    d, out = img.pe.data, []
    for i in range(start, max(start, end - SWITCH_SITE_LEN)):
        if d[i:i + 2] == MOVZX and d[i + 7:i + 9] == JMP_TABLE:
            out.append(img.va_of(i))
    return out


def _switch_span(img, at):
    """(lo, hi) for the switch at `at`, read out of the guard MSVC puts ahead.

    The shape is `lea/add r32, -lo` (optional, absent when lo is 0) then
    `cmp r32, hi-lo` then `ja default`. Reading it means a build that widens a
    switch is read correctly instead of truncated to the range we remember.
    """
    o = img.off(at)
    d = img.pe.data
    # `cmp r32, imm8` is the 3 bytes ending where the `ja` begins.
    for back in (6, 2):                      # ja rel32, then ja rel8
        j = o - back
        if back == 6 and not (d[j] == 0x0F and d[j + 1] == 0x87):
            continue
        if back == 2 and d[j] != 0x77:
            continue
        c = j - 3
        if d[c] != 0x83 or d[c + 1] not in (0xF8, 0xFA, 0xF9, 0xFB):
            break
        span = d[c + 2]
        # The rebase that makes the switch zero-based is NOT always adjacent to
        # the `cmp`: `int-agentview` puts `push esi; mov esi, ecx` between them,
        # and reading only the three bytes before the compare scored it (0, 56)
        # against a true (4, 60) -- a range that starts four ids early and ends
        # four short, which would have mapped every id in the switch to the
        # wrong case body. So scan back a short window and take the NEAREST.
        #
        #   8d /r disp8   lea r32, [r32 - lo]
        #   83 /0 ib      add r32, -lo
        #
        # A switch whose lo is 0 has no rebase at all (`int-main`), so finding
        # none is a real answer rather than a failure.
        lo = 0
        for r in range(c - 3, max(0, c - 12), -1):
            if d[r] == 0x8D and 0x40 <= d[r + 1] <= 0x7F and d[r + 2] >= 0x80:
                lo = 256 - d[r + 2]
                break
            if d[r] == 0x83 and 0xC0 <= d[r + 1] <= 0xC7 and d[r + 2] >= 0x80:
                lo = 256 - d[r + 2]
                break
        return lo, lo + span
    raise ValueError(
        f"no `cmp`/`ja` guard ahead of the switch site at 0x{at:08x}, so its id "
        f"range cannot be read -- this build compiled the switch differently")


def _modal_default(img, spec):
    """The default case: the jump target the most ids share.

    MSVC gives every unhandled id in range the same jump-table entry, so the
    default is the modal target. Derived rather than recorded because the
    default VA is what separates "this switch acts on the id" from "it does
    not", and a stale one silently reclassifies every id in the switch.
    """
    counts = collections.Counter(read_switch(img, spec).values())
    (va, n), = counts.most_common(1)
    if n < 2:
        raise ValueError(
            f"{spec['name']}: no jump target is shared by two ids, so there is "
            f"no default to identify -- this is not the dense switch we read")
    return va


def _parse_chain(img, fn, name):
    """{property id: case-body VA} for a three-case compare chain.

    Two encodings, both present: `sub r32, imm8` accumulates (so the ids are
    running totals) and `cmp r32, imm8` is absolute. Each is followed by
    `jz rel8` to that id's body, and the chain ends on a `jnz` whose FALL-
    THROUGH is the last id's body. Parsed rather than recorded, then checked
    against `CHAIN_VERIFY` so a build that reorders the chain is refused.
    """
    start, end = img.body(fn)
    d = img.pe.data
    want = bytes.fromhex(CHAIN_VERIFY[name])
    at = d.find(want, start, end)
    if at < 0:
        raise ValueError(
            f"{name}: the compare chain is not in the function at 0x{fn:08x} -- "
            f"expected the bytes {CHAIN_VERIFY[name]}, which encode its three "
            f"comparisons. This build renumbered or restructured it, so no id "
            f"map read here would be trustworthy")
    ids, acc, i = {}, 0, at
    while i < at + len(want):
        op = d[i:i + 2]
        if op in (b"\x83\xea", b"\x83\xe8"):          # sub edx/eax, imm8
            acc += d[i + 2]
        elif op in (b"\x83\xf8", b"\x83\xfa"):        # cmp eax/edx, imm8
            acc = d[i + 2]
        else:
            break
        i += 3
        if d[i] == 0x74:                              # jz rel8 -> that id's body
            ids[acc] = img.va_of(i + 2) + struct.unpack_from("<b", d, i + 1)[0]
        elif d[i] == 0x75:                            # jnz rel8 -> falls through
            ids[acc] = img.va_of(i + 2)
        else:
            break
        i += 2
    if len(ids) != 3:
        raise ValueError(
            f"{name}: parsed {len(ids)} case(s) from the chain at 0x{fn:08x}, "
            f"expected 3 -- {sorted(ids)}")
    # `verify` rides along so `chain_ids` can re-read the bytes at `at` on every
    # call. That is a second reading of the same fact rather than a formality:
    # this parse happens once per image and is cached, and the re-check is what
    # a caller holding a stale spec would trip over.
    return dict(at=img.va_of(at), dispatch=fn, name=name, ids=ids,
                verify=CHAIN_VERIFY[name])


def _table_spec(img, name, dispatch, at):
    """One table switch, fully derived: span, tables and default."""
    lo, hi = _switch_span(img, at)
    spec = dict(name=name, dispatch=dispatch, at=at, lo=lo, hi=hi, default=None)
    switch_tables(img, spec)                 # refuses if `at` is not the pair
    spec["default"] = _modal_default(img, spec)
    return spec


def locate(img):
    """Every switch in this module, derived from the image. Never a lookup.

    Raises `ValueError` naming what did not hold. Each count below is an
    assertion: a search that quietly takes the first plausible hit is the defect
    this whole arc exists to remove, so "exactly one" and "exactly two" are
    checked rather than assumed.
    """
    import msgshape                                          # noqa: PLC0415

    # 1. the two dispatchers, via the client's own receive table.
    handlers = {}
    for va, count, direction, _caller, _chan in msgshape.derive_tables(img.pe):
        if direction != "RECV":
            continue
        for i in range(count):
            e = va + 12 * i
            cmds_va, n = img.u32(e), img.u32(e + 4)
            if not cmds_va or not n or n > 64 or img.off(cmds_va) is None:
                continue
            opcode = img.u32(cmds_va)
            if opcode in (INT_OPCODE, FLOAT_OPCODE) and opcode not in handlers:
                handlers[opcode] = img.u32(e + 8)
    missing = [f"0x{o:04X}" for o in (INT_OPCODE, FLOAT_OPCODE)
               if not handlers.get(o)]
    if missing:
        raise ValueError(
            f"the receive table has no handler for {', '.join(missing)} -- the "
            f"agent-property messages are how both dispatchers are reached, so "
            f"nothing below can be located on this build")

    dispatch = {}
    for opcode, kind in ((INT_OPCODE, "int"), (FLOAT_OPCODE, "float")):
        h = handlers[opcode]
        calls = _calls(img, *img.body(h))
        if len(calls) != 1:
            raise ValueError(
                f"the handler for 0x{opcode:04X} at 0x{h:08x} makes {len(calls)} "
                f"calls, expected exactly 1 -- it is supposed to be a forwarder "
                f"whose single callee is the {kind} dispatcher")
        dispatch[kind] = calls[0]

    # 2. the main switches, inside the dispatchers themselves.
    out, chains = {}, {}
    int_start, int_end = img.body(dispatch["int"])
    sites = _switch_sites(img, int_start, int_end)
    if len(sites) != 2:
        raise ValueError(
            f"the int dispatcher at 0x{dispatch['int']:08x} holds {len(sites)} "
            f"`movzx`/`jmp [table]` site(s), expected 2 (int-pre then int-main)")
    out["int-pre"] = _table_spec(img, "int-pre", dispatch["int"], sites[0])
    out["int-main"] = _table_spec(img, "int-main", dispatch["int"], sites[1])

    fl_start, fl_end = img.body(dispatch["float"])
    sites = _switch_sites(img, fl_start, fl_end)
    if len(sites) != 1:
        raise ValueError(
            f"the float dispatcher at 0x{dispatch['float']:08x} holds "
            f"{len(sites)} `movzx`/`jmp [table]` site(s), expected 1 (float-main)")
    out["float-main"] = _table_spec(img, "float-main", dispatch["float"], sites[0])

    # 3. the store and agentview switches, in the functions each dispatcher calls.
    for kind, (start, end) in (("int", (int_start, int_end)),
                               ("float", (fl_start, fl_end))):
        found = []
        for target in _calls(img, start, end):
            try:
                b0, b1 = img.body(target)
            except ValueError:
                continue
            tables = _switch_sites(img, b0, b1)
            chain = [n for n, h in CHAIN_VERIFY.items()
                     if bytes.fromhex(h) in img.pe.data[b0:b1]]
            if tables:
                found.append(("table", target, tables[0]))
            elif chain:
                found.append(("chain", target, chain[0]))
        if len(found) != 2:
            raise ValueError(
                f"the {kind} dispatcher calls {len(found)} function(s) holding a "
                f"property switch, expected exactly 2 (the store, then the "
                f"AgentView switch): {[hex(f[1]) for f in found]}")
        # The dispatcher runs its per-agent STORE first and its AgentView switch
        # second, so call order names them. Asserted by the pinned cross-check.
        for pos, (shape_, target, extra) in zip(("store", "agentview"), found):
            name = f"{kind}-{pos}"
            if shape_ == "table":
                out[name] = _table_spec(img, name, target, extra)
            else:
                chains[name] = _parse_chain(img, target, extra)

    # 4. the gate that decides whether each MAIN switch runs at all.
    gates = []
    for kind in ("int", "float"):
        start, end = img.body(dispatch[kind])
        d = img.pe.data
        hits = [img.va_of(i) for i in range(start, max(start, end - 7))
                if d[i] == 0xF6 and d[i + 2:i + 7] == GATE_TAIL]
        if len(hits) != 1:
            raise ValueError(
                f"the {kind} dispatcher holds {len(hits)} main-switch gate(s) "
                f"(`test byte [ctx+0x53C], 2`), expected exactly 1 -- which "
                f"switches run is no longer established on this build")
        gates.append(hits[0])

    order = ["int-store", "int-agentview", "int-pre", "int-main",
             "float-store", "float-agentview", "float-main"]
    tables = {n: out[n] for n in order if n in out}
    return {"tables": tables, "chains": chains, "gates": tuple(gates),
            "dispatch": dispatch}


# `movzx r32, byte ptr [r32 + disp32]` then `jmp dword ptr [disp32 + r32*4]`.
# The register bytes differ per switch (`float-store` goes through edx), so the
# framing is checked on the opcodes and the modrm's addressing form, not on the
# whole instruction.
MOVZX = bytes.fromhex("0fb6")
JMP_TABLE = bytes.fromhex("ff24")
SWITCH_SITE_LEN = 14


def switch_tables(img, spec):
    """(jump-table VA, byte-index-table VA), read out of the dispatch site.

    Raises rather than returning a remembered pair when the site no longer holds
    the switch: the addresses live INSIDE the instruction, so if these bytes are
    not that instruction there is nothing to read and the recorded answer would
    be a guess about a build we are not looking at.
    """
    blob = img.read(spec["at"], SWITCH_SITE_LEN)
    if blob[0:2] != MOVZX or blob[7:9] != JMP_TABLE:
        raise ValueError(
            f"{spec['name']}: the switch site at 0x{spec['at']:08x} is "
            f"{blob.hex()}, which is not a `movzx`/`jmp [table]` pair -- this "
            f"build moved or restructured the switch, so any id map read here "
            f"would describe something else")
    bt = struct.unpack_from("<I", blob, 3)[0]
    jt = struct.unpack_from("<I", blob, 10)[0]
    if not img.mapped(jt) or not img.mapped(bt):
        raise ValueError(
            f"{spec['name']}: the tables the site names (jt 0x{jt:08x}, "
            f"bt 0x{bt:08x}) are not backed by file bytes")
    return jt, bt


def read_switch(img, spec):
    """id -> case-body VA, for one MSVC dense switch.

    MSVC compiles these as a byte index into a smaller jump table, so the two
    tables have different lengths and the jump table's length is implied by
    the gap between them. Deriving it that way rather than hardcoding a count
    means a build whose switch grew a case is read correctly or not at all.

    Both table addresses now come from `switch_tables`, i.e. out of the
    instruction that jumps through them, so this can no longer read a stale map
    from addresses that moved.
    """
    n_ids = spec["hi"] - spec["lo"] + 1
    jt_va, bt_va = switch_tables(img, spec)
    n_jumps = (bt_va - jt_va) // 4
    if n_jumps <= 0:
        raise ValueError("jump table must sit before the index table")
    jt = struct.unpack(f"<{n_jumps}I", img.read(jt_va, n_jumps * 4))
    bt = img.read(bt_va, n_ids)
    out = {}
    for i, b in enumerate(bt):
        if b >= n_jumps:
            raise ValueError(f"index {b} at id {i + spec['lo']} is outside the "
                             f"{n_jumps}-entry jump table -- the switch moved")
        out[i + spec["lo"]] = jt[b]
    return out


def handled(img, spec):
    """The ids this switch has a real case body for."""
    return {i for i, va in read_switch(img, spec).items()
            if va != spec["default"]}


def chain_ids(img, spec):
    """A compare-chain switch's ids, but only if its bytes still say so.

    Raises rather than returning the recorded map when the encoding moved: a
    hardcoded table that silently survives a build change is exactly the kind
    of check that cannot fail.
    """
    want = bytes.fromhex(spec["verify"])
    got = img.read(spec["at"], len(want))
    if got != want:
        raise ValueError(
            f"{spec['name']}: the compare chain at 0x{spec['at']:08x} is "
            f"{got.hex()}, not {spec['verify']} -- this build renumbered or "
            f"restructured it, so the recorded ids are not trustworthy")
    return dict(spec["ids"])


def consumers(img):
    """id -> {switch name: case body VA} for every switch that acts on it.

    An id absent from every switch is a genuine no-op: MEASURED, both `store`
    functions fall through to `ret` for anything they do not name, so nothing
    is recorded anywhere on the way past.
    """
    main = img.switches["int-main"]
    out = {i: {} for i in range(main["lo"], main["hi"] + 1)}
    for spec in img.switches.values():
        for i, va in read_switch(img, spec).items():
            if va != spec["default"] and i in out:
                out[i][spec["name"]] = va
    for spec in img.chains.values():
        for i, va in chain_ids(img, spec).items():
            if i in out:
                out[i][spec["name"]] = va
    return out


def handled_by_nothing(img):
    """The ids no switch in either dispatcher acts on. MEASURED: just {40}."""
    return sorted(i for i, c in consumers(img).items() if not c)


def gate_bytes(img, strict=True):
    """[(va, ok)] for the `test byte [ctx+0x53C], 2` that gates each main switch.

    `strict` RAISES when a gate has moved, rather than reporting it and letting
    the caller print "results are suspect" and carry on. That warning was the
    last soft check in this file: the gate decides whether the main switch runs
    at all, so if it is not where we think it is, every `classify()` answer
    below is about a control flow we have not actually read.
    `studies/crossbuild/PLAN.md` §6.
    """
    # The gates are LOCATED by shape inside each dispatcher now (see `locate`),
    # so reaching this function at all means one was found in each. Re-reading
    # the bytes keeps the report honest and keeps `strict` meaningful for a
    # caller that passes a VA list of its own.
    out = [(va, img.read(va, 2) == b"\xf6" + img.read(va, 2)[1:2]
            and img.read(va + 2, 5) == GATE_TAIL)
           for va in img.gates]
    bad = [va for va, ok in out if not ok]
    if bad and strict:
        raise ValueError(
            "the main-switch gate is not at " +
            ", ".join(f"0x{va:08x}" for va in bad) +
            " on this build -- the bytes there are not `test byte [ctx+0x53C], 2`, "
            "so which switches run is no longer established. Re-derive the gate "
            "before trusting any classification from this image.")
    return out


def classify(img):
    """id -> ('int' | 'float' | 'int-pre' | None, case body VA or None).

    The MAIN-switch view: which of the two message types carries this property.
    That is a different question from `consumers()` -- an id can be a no-op in
    both main switches and still be acted on by an earlier one, which is what
    5, 8 and 51 turned out to be. Kept because "int or float message" is the
    question a server actually asks before sending.
    """
    si, sf, sp = (img.switches["int-main"], img.switches["float-main"],
                  img.switches["int-pre"])
    ints = read_switch(img, si)
    floats = read_switch(img, sf)
    pre = read_switch(img, sp)
    out = {}
    for i in range(si["lo"], si["hi"] + 1):
        if ints.get(i, si["default"]) != si["default"]:
            out[i] = ("int", ints[i])
        elif floats.get(i, sf["default"]) != sf["default"]:
            out[i] = ("float", floats[i])
        elif pre.get(i, sp["default"]) != sp["default"]:
            out[i] = ("int-pre", pre[i])
        else:
            out[i] = (None, None)
    return out


def cross_check(img, addrs, spans):
    """[(what, derived, expected)] where the derivation disagrees with `addrs`.

    The expectations are passed IN rather than held here, because a
    hand-measured address stops being a liability only once this module has no
    copy of it -- see the note beside `INT_OPCODE`. `test_genericvalue.py` owns
    build 38797's, and an empty list there is the claim that the derivation
    reproduces every value that used to be typed into this file.
    """
    bad = []
    for name, want in addrs.items():
        if name == "gates":
            if tuple(img.gates) != tuple(want):
                bad.append(("gates", tuple(hex(g) for g in img.gates),
                            tuple(hex(g) for g in want)))
            continue
        got = img.switches.get(name) or img.chains.get(name)
        if got is None:
            bad.append((name, "NOT LOCATED", "expected"))
            continue
        for key, wanted in want.items():
            have = got.get(key)
            if have != wanted:
                def fmt(v):
                    return v if isinstance(v, dict) else f"0x{v:08X}"
                bad.append((f"{name}.{key}", fmt(have), fmt(wanted)))
    for name, (lo, hi) in spans.items():
        s = img.switches.get(name)
        if s and (s["lo"], s["hi"]) != (lo, hi):
            bad.append((f"{name}.span", (s["lo"], s["hi"]), (lo, hi)))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--id", type=lambda s: int(s, 0), help="one property id")
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--locate", action="store_true",
                    help="print every address the derivation found, and stop -- "
                         "the first thing to run against a new build")
    a = ap.parse_args()
    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    print(f"client: {a.exe}\n        ({why})\n")
    img = Image(a.exe)

    if a.locate:
        d = img.located["dispatch"]
        print(f"  dispatchers     int 0x{d['int']:08X}  float 0x{d['float']:08X}"
              f"   (handlers for 0x{INT_OPCODE:04X} / 0x{FLOAT_OPCODE:04X})")
        for name, spec in img.switches.items():
            print(f"  {name:15s} in 0x{spec['dispatch']:08X}  "
                  f"at 0x{spec['at']:08X}  default 0x{spec['default']:08X}  "
                  f"ids {spec['lo']}..{spec['hi']}")
        for name, spec in img.chains.items():
            print(f"  {name:15s} in 0x{spec['dispatch']:08X}  "
                  f"at 0x{spec['at']:08X}  ids "
                  f"{ {k: hex(v) for k, v in sorted(spec['ids'].items())} }")
        print(f"  {'gates':15s} {', '.join(f'0x{g:08X}' for g in img.gates)}")
        print("\nEvery address above is derived from this image; none is stored "
              "in this file.\ntest_genericvalue.py holds build 38797's "
              "hand-measured values and requires\nthis derivation to reproduce "
              "every one of them.")
        return 0

    table = classify(img)
    cons = consumers(img)

    si, sf, sp = (img.switches["int-main"], img.switches["float-main"],
                  img.switches["int-pre"])
    hi = si["hi"]
    ni = sum(1 for k, (w, _) in table.items() if w == "int")
    nf = sum(1 for k, (w, _) in table.items() if w == "float")
    npre = sum(1 for k, (w, _) in table.items() if w == "int-pre")
    none = sorted(k for k, (w, _) in table.items() if w is None)
    overlap = handled(img, si) & handled(img, sf)

    if a.csv:
        print("id,dispatcher,body,switches,opentyria,gwca")
        for i in sorted(table):
            w, va = table[i]
            print(f"{i},{w or ''},{'' if va is None else hex(va)},"
                  f"{'|'.join(sorted(cons[i]))},"
                  f"{OPENTYRIA.get(i,'')},{GWCA.get(i,'')}")
        return 0

    if a.id is not None:
        w, va = table.get(a.id, (None, None))
        print(f"property {a.id}")
        print(f"  main switch: {w or 'NEITHER -- no case body in either'}")
        if va:
            print(f"  case body  : 0x{va:08x}")
        c = cons.get(a.id, {})
        where = ", ".join(f"{k} @0x{v:08x}" for k, v in sorted(c.items()))
        print(f"  acted on by: {where or 'NOTHING, in any of the seven switches'}")
        print(f"  OpenTyria  : {OPENTYRIA.get(a.id, '(past the end of its enum)')}")
        print(f"  GWCA       : {GWCA.get(a.id, '(not named)')}")
        return 0

    print(f"property ids 0..{hi} ({hi + 1} of them; OpenTyria's enum has "
          f"{len(OPENTYRIA)}, ending at {max(OPENTYRIA)})")
    print(f"  int main switch   0x{si['dispatch']:08x}: {ni} handled")
    print(f"  float main switch 0x{sf['dispatch']:08x}: {nf} handled")
    print(f"  int pre-switch only: {npre}")
    print(f"  no case body in either MAIN switch: {none}")
    print(f"  ids both main switches claim: {sorted(overlap) or 'none -- disjoint'}")
    print(f"  acted on by NO switch at all: {handled_by_nothing(img)}")
    for va, ok in gate_bytes(img):
        print(f"  main-switch gate at 0x{va:08x}: "
              f"{'as recorded' if ok else 'MOVED -- results are suspect'}")
    print()
    for i in sorted(table):
        w, va = table[i]
        mark = {"int": "INT  ", "float": "FLOAT", "int-pre": "pre  "}.get(w, "  -  ")
        body = f"0x{va:08x}" if va else "          "
        extra = sorted(set(cons[i]) - {si["name"], sf["name"], sp["name"]})
        print(f"  {i:3}  {mark} {body}  {OPENTYRIA.get(i, '(past enum end)'):<20}"
              f"  {GWCA.get(i, ''):<24}{' +' + ','.join(extra) if extra else ''}")
    return 0


def cli(argv=None):
    """`main()`, with a moved switch reported as a FINDING rather than a crash.

    Exit 0 the map was read, 2 this build moved something and the recorded
    addresses do not describe it. A traceback would be the same information, but
    a reader takes a traceback for a broken tool and this is a fact about the
    client -- the same distinction `datcheck.py` draws between "the archive
    changed" and "the run could not be made".
    """
    try:
        return main()
    except ValueError as exc:
        print(f"\nCANNOT READ THIS BUILD: {exc}", file=sys.stderr)
        print("  This is a finding, not a crash -- and since 2026-08-14 it is a "
              "SHARPER one.\n  Nothing here is looked up by address any more, so "
              "this is not 'the addresses\n  are stale': it is the DERIVATION "
              "failing a check it states, on a build that\n  compiles these "
              "switches differently from all three vaulted ones. The message\n"
              "  above names which. `--locate` prints what it did manage to find.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(cli())
