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
says so. The seven, in the order each dispatcher runs them:

    int   0x008128F0  ->  int-store       0x00818170  compare chain, 3 ids
                          int-agentview   0x0081BC60  table, only when the
                                                      agent resolves to type 1
                          int-pre         table, ids 4..64
                          int-main        table, ids 0..66
    float 0x00813040  ->  float-store     0x00818210  table, ids 16..62
                          float-agentview 0x0081BD80  compare chain, 3 ids
                          float-main      table, ids 16..63

Two of the seven are compare chains rather than jump tables, so they cannot be
read as data. Their ids are recorded here as constants AND pinned to the exact
bytes that encode the comparisons, so a build that moves them fails loudly
instead of returning a stale map that still looks plausible.

Both dispatchers also gate the main switch behind `test byte [charContext +
0x53C], 2` -- when that bit is set the main switch is skipped entirely and only
the earlier switches run. `gate_bytes()` pins it.

This module extracts every table from the image and reports, per id, which
switches act on it and what their case bodies are. The names alongside are the
reconstructions', quoted so a disagreement is visible; the binary supplies the
grouping, not the vocabulary.

STANDARD LIBRARY ONLY. The tables are jump tables at known addresses, read as
data -- no disassembly needed to recover the mapping itself.

READ ONLY. Opens the exe for reading and nothing else.
"""

import argparse
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
# WHY `at` IS STILL PINNED, measured rather than assumed: this instruction shape
# occurs **596 times** in `.text` on build 38797, so it is not an anchor. Making
# these fully derived means anchoring the DISPATCHERS first -- they are reached
# from the message handler -- which is a separate job and is not this one.
INT_SWITCH = dict(name="int-main", dispatch=0x008128F0, lo=0, hi=66,
                  at=0x008129CC, default=0x00812EC7)
FLOAT_SWITCH = dict(name="float-main", dispatch=0x00813040, lo=0x10, hi=0x3F,
                    at=0x008130DB, default=0x00813249)

# A second, earlier switch inside the INT dispatcher, taken before the main one.
PRE_SWITCH = dict(name="int-pre", dispatch=0x008128F0, lo=4, hi=64,
                  at=0x0081298B, default=0x008129B0)

# The AgentView switch each dispatcher runs BEFORE its pre-switch, and only when
# the message's agent resolves to an object of type 1. `int-agentview` is where
# property 8 lives -- the id the first version of this module called unhandled.
INT_AGENTVIEW = dict(name="int-agentview", dispatch=0x0081BC60, lo=4, hi=60,
                     at=0x0081BC78, default=0x0081BD29)

# The per-agent record store each dispatcher runs first, on the 0x34-byte record
# at charContext+0x7C indexed by AGENT id. The float one is a table; the int one
# is a three-way compare chain (see CHAINS). Note its dispatch site indexes
# through edx rather than eax -- `0f b6 92` / `ff 24 95` -- which is why the
# framing check below tests the opcode bytes and not the whole instruction.
FLOAT_STORE = dict(name="float-store", dispatch=0x00818210, lo=0x10, hi=0x3E,
                   at=0x0081822E, default=0x0081838B)

TABLE_SWITCHES = [INT_AGENTVIEW, PRE_SWITCH, INT_SWITCH, FLOAT_STORE,
                  FLOAT_SWITCH]

# The two compare-chain switches. MSVC emitted `sub`/`cmp` + `je` rather than a
# jump table because each has only three cases, so there is no table to read as
# data. `verify` is the exact byte string encoding the comparisons: it is what
# makes these entries refutable rather than a hardcoded answer. A build that
# renumbers a property, adds a case or reorders the chain changes those bytes.
CHAINS = [
    dict(name="int-store", dispatch=0x00818170,
         ids={32: 0x008181E5, 41: 0x008181B0, 42: 0x00818191},
         at=0x00818182, verify="83ea20745e83ea09742483ea017572"),
    # 5, 51 and 61 all store the wire float into the agent object's +0x124.
    dict(name="float-agentview", dispatch=0x0081BD80,
         ids={5: 0x0081BD95, 51: 0x0081BD95, 61: 0x0081BD95},
         at=0x0081BD86, verify="83f805740a83f833740583f83d7509"),
]

# `test byte ptr [edi/esi + 0x53C], 2` in each dispatcher: when that bit is set
# the MAIN switch is skipped and only the earlier switches run.
MAIN_SWITCH_GATE = [(0x008129B6, "f6863c05000002"), (0x008130C2, "f6873c05000002")]

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
    out = {i: {} for i in range(INT_SWITCH["lo"], INT_SWITCH["hi"] + 1)}
    for spec in TABLE_SWITCHES:
        for i, va in read_switch(img, spec).items():
            if va != spec["default"] and i in out:
                out[i][spec["name"]] = va
    for spec in CHAINS:
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
    out = [(va, img.read(va, len(h) // 2) == bytes.fromhex(h))
           for va, h in MAIN_SWITCH_GATE]
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
    ints = read_switch(img, INT_SWITCH)
    floats = read_switch(img, FLOAT_SWITCH)
    pre = read_switch(img, PRE_SWITCH)
    out = {}
    for i in range(INT_SWITCH["lo"], INT_SWITCH["hi"] + 1):
        if ints.get(i, INT_SWITCH["default"]) != INT_SWITCH["default"]:
            out[i] = ("int", ints[i])
        elif floats.get(i, FLOAT_SWITCH["default"]) != FLOAT_SWITCH["default"]:
            out[i] = ("float", floats[i])
        elif pre.get(i, PRE_SWITCH["default"]) != PRE_SWITCH["default"]:
            out[i] = ("int-pre", pre[i])
        else:
            out[i] = (None, None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--id", type=lambda s: int(s, 0), help="one property id")
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args()
    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    print(f"client: {a.exe}\n        ({why})\n")
    img = Image(a.exe)
    table = classify(img)
    cons = consumers(img)

    hi = INT_SWITCH["hi"]
    ni = sum(1 for k, (w, _) in table.items() if w == "int")
    nf = sum(1 for k, (w, _) in table.items() if w == "float")
    npre = sum(1 for k, (w, _) in table.items() if w == "int-pre")
    none = sorted(k for k, (w, _) in table.items() if w is None)
    overlap = handled(img, INT_SWITCH) & handled(img, FLOAT_SWITCH)

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
    print(f"  int main switch   0x{INT_SWITCH['dispatch']:08x}: {ni} handled")
    print(f"  float main switch 0x{FLOAT_SWITCH['dispatch']:08x}: {nf} handled")
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
        extra = sorted(set(cons[i]) - {INT_SWITCH["name"], FLOAT_SWITCH["name"],
                                       PRE_SWITCH["name"]})
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
        print("  This is a finding, not a crash. Every address in this module was "
              "measured on\n  build 38797; re-derive them before trusting any "
              "property map from this image.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(cli())
