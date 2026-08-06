"""The wire shape of any message, decoded from the client's own format tables.

    python toolkit/clientscan/msgshape.py 0x00E5 --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --table 0x00bc8f68 --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --all --exe <pinned exe>
    python toolkit/clientscan/msgshape.py --census --exe <pinned exe>

WHY THIS EXISTS. `schema/messages.json` is a byte-faithful import of OpenTyria's
`msgdefs.c` and carries `"validated_against_build": null`. Where it and the
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
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwpe import PE                                          # noqa: E402

DEFAULT_EXE = r"C:\gw\Gw.exe"

# (VA, entry count, direction). SOURCED: studies/msgtable/FINDINGS.md section 3,
# recovered from the 14 callers of MsgChannel::RegisterMsgs at VA 0x007de010.
# Measured on build 38797; a different build moves every one of these.
TABLES = (
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


class Image:
    """The exe, with the load-time cmd writes resolved."""

    def __init__(self, path=DEFAULT_EXE):
        self.pe = PE(path)
        self.path = path
        self.base = self.pe.image_base
        self.entries = []            # (table_va, direction, cmds_va, count)
        self.slots = set()
        self._enumerate()
        self.stores = self._recover_stores()

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
        for tva, n, direction in TABLES:
            stride = 12 if direction == "RECV" else 8
            for i in range(n):
                e = tva + stride * i
                cmds_va, count = self.u32(e), self.u32(e + 4)
                if not cmds_va or not self.mapped(cmds_va):
                    continue
                if not count or count > 64:
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
        out = []
        for op, want in sorted(ORACLE.items()):
            got = None
            for o, d, tva, disp, cmds in self.messages():
                if o == op and tva == 0x00A52D70 and d == "RECV":
                    got = cmds
                    break
            out.append((op, got == want, got))
        return out

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
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--table", help="dump one table by VA")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--census", action="store_true",
                    help="slot counts, the four-message oracle, and the "
                         "client's own descriptor invariants")
    a = ap.parse_args()

    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    img = Image(a.exe)

    if a.census:
        c = img.census()
        print(f"cmd slots {c['slots']}, statically present {c['static']}, "
              f"zero in file {c['zero']}, recovered {c['recovered']}, "
              f"unaccounted {c['zero'] - c['recovered']}")
        for op, ok, got in img.oracle_check():
            print(f"  oracle 0x{op:04X}  {'PASS' if ok else 'FAIL'}")
            if not ok:
                print(f"    got {[hex(x) if x is not None else '?' for x in got or []]}")
        bad = img.invariants()
        print(f"  descriptor invariant violations: {len(bad)}")
        for b in bad[:10]:
            print(f"    {b}")
        return 0

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
        sys.exit(f"opcode 0x{want:04x} is in no table on this build")
    for op, direction, tva, disp, cmds in hits:
        print(_line(op, direction, tva, disp, cmds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
