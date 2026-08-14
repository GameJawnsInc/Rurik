"""The wire shape of any message, decoded from the client's own format tables.

    python toolkit/clientscan/msgshape.py 0x00E5 --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --table 0x00bc8f68 --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --all --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --census --exe <pinned exe>

WHY THIS EXISTS. `schema/messages.json` is a byte-faithful import of OpenTyria's
`msgdefs.c`. It carried `"validated_against_build": null` when this module was
written -- the stamp now reads 38797, filled in by the work this module made
possible, and `test_buildid.py` §3 checks it against the number read out of the
binary. Where it and the
client disagree, the client is the thing we actually talk to, and this reads the
shape straight out of the image so a disagreement can be seen rather than argued.

THE TRAP THIS TOOL EXISTS TO AVOID. Most `cmds[]` field arrays live in `.data`
and are written at load time by MSVC dynamic initializers, so they are ZERO in
the file. **A zero dword decodes as a perfectly legal type-0 four-byte field.**
A naive reader therefore reports a shape that is plausible, self-consistent,
totals a believable number of bytes, and is wrong in every field. That already
happened once inside studies/msgtable, and it happened again while this module
was being written: opcode 0x00E5 read as four dwords (18 bytes) when it is
really `agent_id, u16, u32, u32` (16 bytes). Nothing in the output said so.

So this module recovers the initializer writes rather than trusting the file:

  A1 <src32> ... A3 <dst32>        mov eax,[src] ; mov [dst],eax
  8B 0D <src32> ... 89 0D <dst32>  same through ecx/edx/ebx/esi/edi
  B8 <imm32> ... A3 <dst32>        mov eax,imm   ; mov [dst],eax
  C7 05 <dst32> <imm32>            mov [dst],imm

and a slot that neither the file nor a recovered store accounts for comes back
as `None` and prints as `?`. It is never guessed past. MEASURED on build 38797:
2420 cmd slots, 1321 statically present, 1099 zero in the file, **1097
recovered** -- exactly the count studies/msgtable measured by a completely
different method (PE base relocations). The two left over are the genuinely
never-written opcode-0 slots that study also found.

WHAT MAKES THE RECOVERY CHECKABLE, rather than merely confident:

  * `oracle_check()` reproduces the four known-good AgMsg messages from
    studies/msgtable section 4 -- 0x001E, 0x0029, 0x002C, 0x0020 -- whose cmds
    are 100% zero in the file. If the recovery were wrong those would not come
    out right, and before the recovery existed all four came out wrong.
  * `invariants()` re-runs the six rules the client asserts about its own
    descriptors over all 2008 of them. Zero violations on this build.

The bit layout and the type table are SOURCED from studies/msgtable, recovered
there from `MsgChannel.cpp`'s own switch bounds and asserts. Nothing here
re-derives them.

STANDARD LIBRARY ONLY, deliberately -- see the note in `msghandler.py` about
where the capstone/pefile dependency is allowed to live.

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

# (VA, entry count, direction). SOURCED: studies/msgtable/FINDINGS.md section 3,
# recovered from the 14 callers of MsgChannel::RegisterMsgs at VA 0x007de010.
# Measured on build 38797; a different build moves every one of these.
#
# THIS IS NO LONGER THE LOOKUP. It is a CROSS-CHECK, and the difference is the
# whole of `studies/crossbuild/PLAN.md` §3. Used as the lookup it made this tool
# answer confidently and wrongly on any other build: MEASURED on
# 2026-04-30_b174de1f2d8d, `--census` reported `cmd slots 0` and `descriptor
# invariant violations: 0` -- a line printed after examining ZERO descriptors,
# byte-identical to the healthy build's -- and exited 0, while
# `msgshape.py 0x00E5` answered "opcode 0x00e5 is in no table on this build",
# which is a claim about ArenaNet's client when the truth is a claim about these
# 25 numbers. 651 of the 751 table entries died at the unmapped-`cmds_va` check
# in `_enumerate`, silently, because a `continue` is not a refusal.
#
# `derive_tables()` now recovers these from the image on whatever build it is
# given. This tuple stays so the derivation can be checked against a known-good
# answer on 38797 -- a class-(c) expectation under §6 of that plan, and going red
# on a new build is the correct behaviour rather than a defect.
TABLES_38797 = (
    (0x00A52D70, 18, "RECV"),    # AgMsg -- agents and movement
    (0x00A52E48, 2, "SEND"),
    (0x00A96598, 1, "SEND"), (0x00A965A0, 1, "RECV"),
    (0x00B97958, 2, "SEND"),
    (0x00BC89B0, 15, "RECV"),
    (0x00BC8CB8, 86, "SEND"),
    (0x00BC8F68, 203, "RECV"),   # largest -- the whole skill block lives here
    (0x00BC9A10, 1, "SEND"), (0x00BC9A18, 8, "RECV"),
    (0x00BCA740, 15, "RECV"),
    (0x00BCA808, 13, "SEND"), (0x00BCA870, 31, "RECV"),
    (0x00BCAC48, 34, "SEND"), (0x00BCAD58, 56, "RECV"),
    (0x00BCB030, 15, "SEND"), (0x00BCB0A8, 68, "RECV"),
    (0x00BCB9F8, 27, "SEND"), (0x00BCB788, 52, "RECV"),
    (0x00BCBAF0, 8, "SEND"), (0x00BCBB30, 10, "RECV"),
    (0x00BEC384, 2, "SEND"), (0x00BEC394, 5, "RECV"),
    (0x00BEC3D0, 46, "SEND"),    # ch3 AUTH_CMSG
    (0x00BEC540, 32, "RECV"),    # ch3 AUTH_SMSG
)


class NoTables(SystemExit):
    """The message tables could not be located. Never a silent empty result."""


# MsgChannel::RegisterMsgs, anchored by byte shape rather than by address --
# `studies/crossbuild/PLAN.md` §7 rule 2: encode the bytes that have a reason to
# stay put, never an address. These seventeen are the middle of the routine:
#
#   8b f0            mov esi,eax        <- the anchor starts here, entry+0x22
#   83 c4 08         add esp,8
#   8b 45 14         mov eax,[ebp+0x14]     ; sendCount
#   85 c0            test eax,eax
#   74 0d            jz  +0xd
#   50               push eax
#   ff 75 10         push [ebp+0x10]        ; sendMsgs
#   56               push esi
#
# Not one address, not one rel32, not one byte that differs between the two
# vaulted builds -- the routine's own prologue loads a /GS cookie by absolute
# address, which is exactly the kind of byte left OUT. MEASURED: one hit in
# `.text` on both builds, and one in the whole file.
REGISTER_SIG = bytes.fromhex("8bf083c4088b451485c0740d50ff751056")
REGISTER_SIG_DELTA = 0x22
REGISTER_PROLOGUE = bytes.fromhex("558bec")      # push ebp / mov ebp,esp

# The six arguments are pushed right-to-left by a __cdecl caller, so in ADDRESS
# order they read: recvCount, recvMsgs, sendCount, sendMsgs, arg1, chanSel.
PUSH_IMM8, PUSH_IMM32 = 0x6A, 0x68
ARG_WINDOW = 40                  # how far back a six-push run can start

HEADER_BYTES = 2                 # the opcode on the wire; not a field type

# MEASURED on build 38797. A regression on any of these means the recovery
# changed, and a changed recovery invalidates every shape this module prints.
CENSUS_38797 = {"slots": 2420, "static": 1321, "zero": 1099, "recovered": 1097}

# studies/msgtable/FINDINGS.md section 4. All four live in the AgMsg table,
# whose cmds arrays are 100% zero in the file -- the hardest case in the image.
ORACLE = {
    0x001E: [0x1E, 0x404],
    0x0029: [0x29, 0x404, 0x12, 0x204, 0x204],
    0x002C: [0x2C, 0x404, 0x12, 0x204],
    0x0020: [0x20, 0x404, 0x404, 0x104, 0x104, 0x12, 0x204, 0x2, 0x104, 0x21,
             0x1, 0x404, 0x404, 0x404, 0x404, 0x404, 0x404, 0x404, 0x2, 0x12,
             0x204, 0x404, 0x12, 0x204],
}

_REG = ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi")

# Types 0 and 1 are both a 4-byte scalar on the wire, so printing both as
# "dword" costs nothing in framing and hides the only two semantic tags the
# client's own descriptors carry. That is not hypothetical: this module printed
# 0x00E3 as `[dword, u16, u32]`, a reader reconstructed "the binary is dword,
# agent_id, word" from it, and studies/enemy/PLAN.md 6o recorded our (correct)
# schema entry as a live hazard on the strength of it. Naming the tags makes
# the output directly comparable to schema/messages.json.
#
# INFERRED, and the inference is studies/msgtable/FINDINGS.md's, not this
# module's: across the 748 shared messages the binary has exactly 127 type-0
# fields and our catalog exactly 127 `agent_id` fields, and type 1 appears 4
# times, only inside the agent-position messages our catalog types as `float`.
# The wire width is 4 either way, so a wrong label here cannot misframe
# anything -- it can only mislabel.
TYPE01_NAME = {0: "agent_id", 1: "float"}


def decode_cmd(cmd):
    """(type, index, count). index is a log2 element size; count is unmasked."""
    return cmd & 0xF, (cmd >> 4) & 0xF, cmd >> 8


class Field:
    __slots__ = ("kind", "type", "index", "count", "elem", "cap", "wire")

    def __init__(self, kind, type_, index, count, elem=0, cap=0, wire=0):
        self.kind, self.type, self.index = kind, type_, index
        self.count, self.elem, self.cap = count, elem, cap
        self.wire = wire            # max wire bytes

    def __repr__(self):
        if self.kind == "array":
            return f"array{self.elem * 8}[{self.cap}]"
        if self.kind == "blob":
            return f"blob({self.wire})"
        if self.kind == "wstring":
            return f"string16({self.cap})"
        if self.kind == "uint":
            return {1: "u8", 2: "u16", 4: "u32"}.get(self.wire, f"uint{self.wire}")
        if self.kind == "dword":
            return TYPE01_NAME[self.type]
        return self.kind


class Undecodable(Exception):
    """A cmd this build does not let us read. Never guessed past."""


def fields(cmds):
    """Decode cmds[1:] into fields. cmds[0] is the raw opcode, not a cmd.

    An array is TWO cmds -- a type-11 header and a type-6 payload -- but ONE
    field, so a raw cmd count compared against a reconstruction's field count is
    off by one per array. That is the commonest way to misread these tables.
    """
    out = []
    i = 1
    while i < len(cmds):
        cmd = cmds[i]
        if cmd is None:
            raise Undecodable(f"cmd slot {i} is zero in the file and no "
                              f"initializer store was recovered for it")
        t, index, count = decode_cmd(cmd)
        elem = 1 << index
        if t == 11:
            # The length prefix is ALWAYS 16 bits regardless of element width;
            # `index` names the ELEMENT size. Reading OpenTyria's
            # TYPE_ARRAY_8/16/32 as prefix widths misframes every array.
            nxt = cmds[i + 1] if i + 1 < len(cmds) else None
            if nxt is None or decode_cmd(nxt)[0] not in (6, 10):
                raise Undecodable(f"array header at {i} is not followed by a "
                                  f"type-6 payload")
            out.append(Field("array", t, index, count, elem=elem, cap=count,
                             wire=2 + count * elem))
            i += 2
            continue
        if t in (0, 1):
            out.append(Field("dword", t, index, count, wire=4))
        elif t == 2:
            out.append(Field("vec2", t, index, count, wire=8))
        elif t == 3:
            out.append(Field("vec3", t, index, count, wire=12))
        elif t in (4, 8):
            out.append(Field("uint", t, index, count, wire=count))
        elif t in (5, 9):
            out.append(Field("blob", t, index, count, wire=count))
        elif t == 7:
            out.append(Field("wstring", t, index, count, wire=2 + 2 * count))
        elif t == 12:
            out.append(Field("nested", t, index, count, wire=1))
        else:
            raise Undecodable(f"cmd 0x{cmd:08x}: type {t} is outside the "
                              f"client's own switch bound of 0..12")
        i += 1
    return out


def wire_max(cmds):
    """Largest legal wire size: header plus every array at capacity."""
    return HEADER_BYTES + sum(f.wire for f in fields(cmds))


def wire_min(cmds):
    """Wire size with every array EMPTY -- the floor a framer must accept."""
    return HEADER_BYTES + sum(2 if f.kind == "array" else f.wire
                              for f in fields(cmds))


def describe(cmds):
    """One line: the field list and the wire size (or why it cannot be read)."""
    try:
        fs = fields(cmds)
    except Undecodable as exc:
        return f"UNDECODABLE: {exc}"
    lo, hi = wire_min(cmds), wire_max(cmds)
    size = f"{lo}" if lo == hi else f"{lo}..{hi}"
    return (f"{len(fs)} field(s): [{', '.join(repr(f) for f in fs)}]  "
            f"wire {size} bytes")


Registration = collections.namedtuple(
    "Registration", "va count direction caller chan")


def measured_nothing(img):
    """Did this run establish anything at all about the client?

    Lifted out of `main()` so it can be driven against a doctored image, because
    the defect it guards is precisely a run that prints zeros and exits 0. The
    two terms are not redundant: a table set can resolve slots that all decode
    to nothing, and a descriptor count of zero is what makes
    `invariant violations: 0` a vacuous line rather than a pass.
    """
    return not img.slots or not img.invariant_coverage()[1]


def find_register_msgs(pe):
    """(entry_va, entry_off) of MsgChannel::RegisterMsgs, located by byte shape.

    REFUSES on 0 hits and on 2+ hits rather than taking the first --
    `studies/crossbuild/PLAN.md` §7 rule 1. Taking the first hit is how a tool
    keeps returning a number after the thing it was looking for moved.

    The -0x22 delta is then VERIFIED rather than assumed: the bytes it lands on
    must be the routine's prologue and must be preceded by MSVC's `int3` pad.
    That matters because the prologue is NOT usable as the anchor -- MEASURED,
    `55 8b ec 83 ec 20 a1` occurs 56 times in `.text` on 38797 and 57 times on
    the older build, so a tool that searched on it and took the first hit would
    resolve to the wrong routine in silence.
    """
    hits = pe.find(REGISTER_SIG, ".text")
    if not hits:
        raise NoTables(
            "MsgChannel::RegisterMsgs is not in this client -- the routine was "
            "recompiled or its shape changed.\n"
            "  That is a real finding, not a crash: every message shape this "
            "module reports comes from\n"
            "  the tables that routine installs. Re-derive the anchor in "
            "studies/msgtable/ before\n"
            "  trusting any shape against this build.")
    if len(hits) > 1:
        raise NoTables(
            f"{len(hits)} matches for the RegisterMsgs anchor, expected 1; "
            f"refusing to guess which is the real one.")
    off = hits[0] - REGISTER_SIG_DELTA
    if pe.data[off:off + len(REGISTER_PROLOGUE)] != REGISTER_PROLOGUE:
        raise NoTables(
            "the RegisterMsgs anchor matched but the routine entry is not where "
            "it should be:\n"
            f"  expected {REGISTER_PROLOGUE.hex()} at file offset {off:#x}, found "
            f"{pe.data[off:off + len(REGISTER_PROLOGUE)].hex()}.\n"
            "  The anchor's offset into the routine has moved; re-measure it.")
    if off > 0 and pe.data[off - 1] != 0xCC:
        raise NoTables(
            f"the byte before the RegisterMsgs entry at {off:#x} is "
            f"{pe.data[off - 1]:#04x}, not an int3 pad -- this is the middle of "
            f"something, not a function entry.")
    return pe.image_base + pe.off_to_rva(off), off


def callers_of(pe, entry_va):
    """Every file offset in `.text` holding a `call rel32` to `entry_va`."""
    sec = pe.section(".text")
    lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
    base_va = pe.image_base + sec["vaddr"]
    data, out, p = pe.data, [], lo
    while True:
        p = data.find(b"\xe8", p, hi - 5)
        if p == -1:
            return out
        rel = struct.unpack_from("<i", data, p + 1)[0]
        if base_va + (p - lo) + 5 + rel == entry_va:
            out.append(p)
        p += 1


def _six_pushes(data, call_off):
    """The six pushed immediates before a __cdecl call site, or None.

    Parsed FORWARD with backtracking and accepted only if a run of exactly six
    push-immediates lands exactly on the call. Ambiguity is refused rather than
    resolved: if two start offsets both parse, we cannot tell which is the real
    argument list from the bytes alone.
    """
    found = []
    for start in range(max(0, call_off - ARG_WINDOW), call_off):
        vals, p = [], start
        for _ in range(6):
            if p >= call_off:
                break
            b = data[p]
            if b == PUSH_IMM8:
                vals.append(int.from_bytes(data[p + 1:p + 2], "little", signed=True))
                p += 2
            elif b == PUSH_IMM32:
                vals.append(int.from_bytes(data[p + 1:p + 5], "little"))
                p += 5
            else:
                break
        if len(vals) == 6 and p == call_off:
            found.append(vals)
    return found[0] if len(found) == 1 else None


def derive_tables(pe):
    """Every message table this image registers, recovered from the image.

    Returns a tuple of `Registration`. This is what replaced the hardcoded
    `TABLES_38797` as the lookup -- see that constant's comment for what the
    hardcoded version did on a build it was not measured on.

    MEASURED 2026-08-12: on build 38797 this reproduces `TABLES_38797` exactly,
    all 25 entries, same VAs, same counts, same directions. On
    2026-04-30_b174de1f2d8d it recovers 25 tables and 751 declared entries --
    the same count per table, in the same order, with every VA moved.
    """
    entry_va, _ = find_register_msgs(pe)
    out = []
    for call_off in callers_of(pe, entry_va):
        vals = _six_pushes(pe.data, call_off)
        if vals is None:
            raise NoTables(
                f"the argument list at call site {call_off:#x} could not be read "
                f"as six pushed immediates.\n"
                f"  The calling convention or the compiler's scheduling changed. "
                f"Refusing to report a\n"
                f"  partial table set, because a missing table reads downstream "
                f"as 'that opcode does not exist'.")
        recv_count, recv_va, send_count, send_va, _arg1, chan = vals
        caller_va = pe.image_base + pe.off_to_rva(call_off)
        if send_va:
            out.append(Registration(send_va, send_count, "SEND", caller_va, chan))
        if recv_va:
            out.append(Registration(recv_va, recv_count, "RECV", caller_va, chan))
    if not out:
        raise NoTables(
            f"RegisterMsgs was found at {entry_va:#010x} but has no callers that "
            f"register a table.")
    return tuple(sorted(out, key=lambda r: r.va))


class Image:
    """The exe, with the load-time cmd writes resolved."""

    def __init__(self, path=None, tables=None):
        path = path or find_exe()[0]
        self.pe = PE(path)
        self.path = path
        self.base = self.pe.image_base
        # Derived from THIS image, never from a constant. `tables` is an
        # override for tests that want to drive the walk with a known set.
        self.tables = derive_tables(self.pe) if tables is None else tuple(tables)
        self.entries = []            # (table_va, direction, cmds_va, count)
        self.slots = set()
        # Why each rejected entry was rejected. `_enumerate` skips with a bare
        # `continue`, which is fine as long as somebody counts: 651 of 751
        # entries vanished into the first of these on the older build and the
        # tool reported an empty census as though it were a finding.
        self.skipped_unmapped = 0
        self.skipped_count = 0
        self._enumerate()
        self.stores = self._recover_stores()

    @property
    def agmsg_table(self):
        """The AgMsg RECV table -- the one the four oracles live in.

        Identified as the RECV table registered by the LOWEST call site, which
        is what it is on both vaulted builds. It used to be the literal
        `0x00A52D70`, which made `oracle_check()` fail on any other build for a
        reason that had nothing to do with the oracles.
        """
        recv = [r for r in self.tables if r.direction == "RECV"]
        return min(recv, key=lambda r: r.caller).va if recv else None

    # -- raw reads ------------------------------------------------------
    def u32(self, va):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            return None
        return int.from_bytes(self.pe.data[off:off + 4], "little")

    def mapped(self, va):
        return self.pe.rva_to_off(va - self.base) is not None

    # -- table walk -----------------------------------------------------
    def _enumerate(self):
        for reg in self.tables:
            tva, n, direction = reg.va, reg.count, reg.direction
            stride = 12 if direction == "RECV" else 8
            for i in range(n):
                e = tva + stride * i
                cmds_va, count = self.u32(e), self.u32(e + 4)
                if not cmds_va or not self.mapped(cmds_va):
                    self.skipped_unmapped += 1
                    continue
                if not count or count > 64:
                    self.skipped_count += 1
                    continue
                self.entries.append((tva, direction, e, cmds_va, count))
                for k in range(count):
                    self.slots.add(cmds_va + 4 * k)

    # -- initializer recovery -------------------------------------------
    def _recover_stores(self):
        """dst VA -> value, for every cmd slot an initializer writes.

        A linear byte walk, not a disassembly: MSVC packs these initializers
        back to back with no int3 padding, so anything that finds function
        boundaries first misses writes -- studies/msgtable records two agents
        hitting exactly that. Only stores whose destination is already a known
        cmd slot are accepted, which is what keeps a desynced decode from
        inventing one.
        """
        sec = self.pe.section(".text")
        blob = self.pe.data[sec["rawptr"]:sec["rawptr"] + sec["rawsize"]]
        regs, out = {}, {}
        i, n = 0, len(blob)
        while i < n - 6:
            b = blob[i]
            if b == 0xA1:                                  # mov eax,[disp32]
                regs["eax"] = ("mem", struct.unpack_from("<I", blob, i + 1)[0])
                i += 5
                continue
            if b == 0xA3:                                  # mov [disp32],eax
                dst = struct.unpack_from("<I", blob, i + 1)[0]
                if dst in self.slots and "eax" in regs:
                    out.setdefault(dst, regs["eax"])
                i += 5
                continue
            if 0xB8 <= b <= 0xBF:                          # mov r32,imm32
                regs[_REG[b - 0xB8]] = ("const",
                                        struct.unpack_from("<I", blob, i + 1)[0])
                i += 5
                continue
            if b in (0x8B, 0x89) and (blob[i + 1] & 0xC7) == 0x05:
                reg = _REG[(blob[i + 1] >> 3) & 7]
                addr = struct.unpack_from("<I", blob, i + 2)[0]
                if b == 0x8B:
                    regs[reg] = ("mem", addr)
                elif addr in self.slots and reg in regs:
                    out.setdefault(addr, regs[reg])
                i += 6
                continue
            if b == 0xC7 and blob[i + 1] == 0x05:          # mov [disp32],imm32
                dst, imm = struct.unpack_from("<II", blob, i + 2)
                if dst in self.slots:
                    out.setdefault(dst, ("const", imm))
                i += 10
                continue
            i += 1
        return {dst: (v if kind == "const" else self.u32(v))
                for dst, (kind, v) in out.items()}

    # -- queries --------------------------------------------------------
    def cmds(self, cmds_va, count):
        """The cmds array as the loader will see it. None = not recovered."""
        out = []
        for k in range(count):
            va = cmds_va + 4 * k
            v = self.u32(va)
            out.append(v if v else self.stores.get(va))
        return out

    def messages(self):
        """(opcode, direction, table_va, dispatch, cmds) for every entry."""
        for tva, direction, e, cmds_va, count in self.entries:
            cmds = self.cmds(cmds_va, count)
            if cmds[0] is None:
                cmds[0] = 0                # the four genuine opcode-0 messages
            dispatch = self.u32(e + 8) if direction == "RECV" else None
            # NEVER mask the opcode to a byte: 229 of the 477 receive opcodes
            # on this build are above 0xFF, so a mask collapses 0x0129 onto
            # 0x0029 and a lookup silently returns somebody else's message.
            yield cmds[0], direction, tva, dispatch, cmds

    def lookup(self, opcode, direction=None):
        return [m for m in self.messages()
                if m[0] == opcode and (direction is None or m[1] == direction)]

    # -- self-checks ----------------------------------------------------
    def census(self):
        static = sum(1 for va in self.slots if self.u32(va))
        zero = len(self.slots) - static
        rec = sum(1 for va in self.slots if not self.u32(va) and va in self.stores)
        return {"slots": len(self.slots), "static": static, "zero": zero,
                "recovered": rec}

    def oracle_check(self):
        """[(opcode, ok, got)] for the four known-good AgMsg messages."""
        agmsg = self.agmsg_table
        out = []
        for op, want in sorted(ORACLE.items()):
            got = None
            for o, d, tva, disp, cmds in self.messages():
                if o == op and tva == agmsg and d == "RECV":
                    got = cmds
                    break
            out.append((op, got == want, got))
        return out

    def invariant_coverage(self):
        """(messages, descriptors) the invariant check actually examined.

        Reported beside the violation count, always. "0 violations" over 0
        descriptors is not a pass, it is the shape of a run that measured
        nothing -- and it printed byte-identically to a healthy run on the
        older build while every table address was wrong.
        """
        msgs = descs = 0
        for op, d, tva, disp, cmds in self.messages():
            if any(c is None for c in cmds[1:]):
                continue
            msgs += 1
            descs += len(cmds) - 1
        return msgs, descs

    def invariants(self):
        """Violations of the six rules the client asserts about descriptors."""
        bad = []
        for op, d, tva, disp, cmds in self.messages():
            if any(c is None for c in cmds[1:]):
                continue
            for k in range(1, len(cmds)):
                t, idx, cnt = decode_cmd(cmds[k])
                where = (op, d, k)
                if t > 12:
                    bad.append(("type > 12", where))
                if t == 7 and idx != 1:
                    bad.append(("type-7 index != 1", where))
                if t in (6, 10) and decode_cmd(cmds[k - 1])[0] != 11:
                    bad.append(("type-6 not preceded by type-11", where))
                if t in (4, 8) and cnt not in (1, 2, 4):
                    bad.append(("type-4 count not in {1,2,4}", where))
                if t == 12 and cnt > 128:
                    bad.append(("type-12 count > 128", where))
                if t in (5, 9) and cnt == 0:
                    bad.append(("type-5 count == 0", where))
        return bad


def _line(op, direction, tva, disp, cmds):
    d = f"handler 0x{disp:08x}" if disp else "send-only"
    shown = [hex(c) if c is not None else "?" for c in cmds]
    return (f"0x{op:04X}  {direction}  table 0x{tva:08x}  {d}\n"
            f"        {describe(cmds)}\n"
            f"        cmds {shown}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opcode", nargs="?")
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--table", help="dump one table by VA")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--census", action="store_true",
                    help="slot counts, the four-message oracle, and the "
                         "client's own descriptor invariants")
    a = ap.parse_args()

    a.exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    print(f"client: {a.exe}\n        ({why})\n")
    img = Image(a.exe)

    if a.census:
        rc = 0
        declared = sum(r.count for r in img.tables)
        print(f"tables {len(img.tables)} (derived), declared entries {declared}, "
              f"usable {len(img.entries)}, skipped {img.skipped_unmapped} unmapped "
              f"+ {img.skipped_count} bad-count")
        c = img.census()
        print(f"cmd slots {c['slots']}, statically present {c['static']}, "
              f"zero in file {c['zero']}, recovered {c['recovered']}, "
              f"unaccounted {c['zero'] - c['recovered']}")

        # The cross-check, not the lookup. Only meaningful against the build the
        # constant was measured on, so it is scoped by hash rather than assumed.
        what, _ = pinned.identify(a.exe, build=pinned.BUILD)
        if what in ("pristine", "patched"):
            derived = sorted((r.va, r.count, r.direction) for r in img.tables)
            if derived == sorted(TABLES_38797):
                print(f"  cross-check: the derivation reproduces the pinned "
                      f"build-{pinned.BUILD} table exactly ({len(derived)} tables)")
            else:
                print(f"  cross-check: DISAGREES with the pinned build-"
                      f"{pinned.BUILD} table -- derived {len(derived)}, pinned "
                      f"{len(TABLES_38797)}")
                rc = max(rc, 1)

        oracles = img.oracle_check()
        for op, ok, got in oracles:
            print(f"  oracle 0x{op:04X}  {'PASS' if ok else 'FAIL'}")
            if not ok:
                print(f"    got {[hex(x) if x is not None else '?' for x in got or []]}")
        if not all(ok for _, ok, _ in oracles):
            rc = max(rc, 1)

        bad = img.invariants()
        msgs, descs = img.invariant_coverage()
        print(f"  descriptor invariant violations: {len(bad)}  "
              f"(over {descs} descriptor(s) in {msgs} message(s))")
        for b in bad[:10]:
            print(f"    {b}")
        if bad:
            rc = max(rc, 1)

        # A run that measured nothing FAILED. This is the whole point of the
        # section: the older build used to print an empty census, four FAILing
        # oracles and `violations: 0` and then exit 0.
        if measured_nothing(img):
            print("\nNOTHING WAS MEASURED. The tables were located but no usable "
                  "descriptor came out of\n"
                  "them, so every count above is a fact about this tool and not "
                  "about the client.")
            rc = 2
        return rc

    if a.all or a.table:
        want = int(a.table, 0) if a.table else None
        for op, direction, tva, disp, cmds in img.messages():
            if want is None or tva == want:
                print(_line(op, direction, tva, disp, cmds))
        return 0

    if not a.opcode:
        ap.error("give an opcode, or --table / --all / --census")
    want = int(a.opcode, 0)
    hits = img.lookup(want)
    if not hits:
        # Say what was actually established. The old wording -- "is in no table
        # on this build" -- is a claim about ArenaNet's client, and when the
        # table addresses were wrong it was a false one; the tool had walked
        # 25 addresses that no longer named tables and reported the client's
        # message set as missing an opcode it has.
        sys.exit(f"opcode 0x{want:04x} is in none of the {len(img.tables)} tables "
                 f"this build registers\n"
                 f"  ({len(img.entries)} usable entries, {len(img.slots)} cmd "
                 f"slots). Run --census to check the tables resolved at all.")
    for op, direction, tva, disp, cmds in hits:
        print(_line(op, direction, tva, disp, cmds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
