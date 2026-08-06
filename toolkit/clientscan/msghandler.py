"""Find and disassemble the client's own handler for a message.

    python toolkit/clientscan/msghandler.py 0x0029
    python toolkit/clientscan/msghandler.py 0x0029 --follow      # + called fn
    python toolkit/clientscan/msghandler.py --table 0xa52d70     # whole table

WHY THIS EXISTS. Every other source we have for what a message MEANS is a
reconstruction, and on the one message this project needed most -- 0x0029
AGENT_MOVE_TO_POINT -- the two best reconstructions gave contradictory answers
and both were shipped and playtested before anyone thought to ask the client.
Field SHAPES we can already recover (schema/messages.json came from the binary's
own format tables). Field MEANINGS live in the code that consumes them, and this
is the shortest path to reading it.

HOW IT WORKS. The msgtable study recovered the message-format tables and the two
descriptor layouts. The receive descriptor is 12 bytes and its third member is a
dispatch function pointer:

    struct MsgFormatRecv { uint32 *cmds; uint32 count; void *dispatch; };
    struct MsgFormatSend { uint32 *cmds; uint32 count; };   // 8 bytes, no dispatch

so a handler is a table lookup, not a search. cmds[0] is the opcode.

Only RECEIVE tables have handlers -- from the client's point of view that is
everything the server sends, which is what we care about. Send tables are listed
so a lookup can say "that message has no handler because the client only ever
transmits it" rather than "not found".

READ ONLY. Opens Gw.exe for reading and does nothing else. The install at
C:\\gw is the player's own and is never written, patched or launched from here.
"""

import argparse
import os
import sys

try:
    import capstone
    import pefile
except ImportError:                                           # pragma: no cover
    sys.exit("needs capstone and pefile: python -m pip install capstone pefile")

DEFAULT_EXE = r"C:\gw\Gw.exe"

# (VA, entry count, direction). SOURCED: studies/msgtable/FINDINGS.md section 3,
# recovered from the 14 callers of MsgChannel::RegisterMsgs at VA 0x007de010.
# Measured against build 38797; a different build moves all of these.
TABLES = (
    (0x00a52d70, 18, "RECV"),    # AgMsg -- agents and movement
    (0x00a52e48, 2, "SEND"),
    (0x00a96598, 1, "SEND"), (0x00a965a0, 1, "RECV"),
    (0x00b97958, 2, "SEND"),
    (0x00bc89b0, 15, "RECV"),
    (0x00bc8cb8, 86, "SEND"),
    (0x00bc8f68, 203, "RECV"),   # largest
    (0x00bc9a10, 1, "SEND"), (0x00bc9a18, 8, "RECV"),
    (0x00bca740, 15, "RECV"),
    (0x00bca808, 13, "SEND"), (0x00bca870, 31, "RECV"),
    (0x00bcac48, 34, "SEND"), (0x00bcad58, 56, "RECV"),
    (0x00bcb030, 15, "SEND"), (0x00bcb0a8, 68, "RECV"),
    (0x00bcb9f8, 27, "SEND"), (0x00bcb788, 52, "RECV"),
    (0x00bcbaf0, 8, "SEND"), (0x00bcbb30, 10, "RECV"),
    (0x00bec384, 2, "SEND"), (0x00bec394, 5, "RECV"),
    (0x00bec3d0, 46, "SEND"),    # ch3 AUTH_CMSG
    (0x00bec540, 32, "RECV"),    # ch3 AUTH_SMSG
)


class Image:
    def __init__(self, path=DEFAULT_EXE):
        self.path = path
        self.pe = pefile.PE(path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        with open(path, "rb") as fh:
            self.blob = fh.read()

    def off(self, va):
        rva = va - self.base
        for s in self.pe.sections:
            size = max(s.Misc_VirtualSize, s.SizeOfRawData)
            if s.VirtualAddress <= rva < s.VirtualAddress + size:
                return s.PointerToRawData + (rva - s.VirtualAddress)
        return None

    def u32(self, va):
        o = self.off(va)
        return None if o is None else int.from_bytes(self.blob[o:o + 4], "little")


def read_table(img, va, count, direction):
    """Yield (opcode, cmds, dispatch_or_None) for one table."""
    stride = 12 if direction == "RECV" else 8
    for i in range(count):
        e = va + stride * i
        cmds_va = img.u32(e)
        n = img.u32(e + 4)
        dispatch = img.u32(e + 8) if direction == "RECV" else None
        if not cmds_va or n is None or n > 64 or img.off(cmds_va) is None:
            continue
        cmds = [img.u32(cmds_va + 4 * k) for k in range(n)]
        if not cmds or cmds[0] is None:
            continue
        # NO & 0xFF HERE, and the mask that used to be here was a real defect.
        # MEASURED on build 38797: 229 of the 477 receive opcodes are above
        # 0xFF, so masking to a byte collapsed 0x0129 onto 0x0029 and a lookup
        # returned whichever entry the table walk reached first. Nearly half the
        # catalogue could resolve to somebody else's handler, and it would have
        # looked like a successful read -- the failure mode this repository
        # cares about most, since nothing in the output says which one you got.
        yield cmds[0], cmds, dispatch


def disasm(img, va, limit=90, indent="  "):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        print(f"{indent}(0x{va:08x} is not mapped)")
        return []
    calls = []
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va)):
        print(f"{indent}0x{ins.address:08x}  {ins.mnemonic:<7} {ins.op_str}")
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
        if ins.mnemonic == "ret" or n >= limit:
            break
    return calls


def source_files(img, va, limit=400):
    """The ArenaNet source paths an assert inside this handler names.

    Every assert compiles to `mov edx, <expr string>; mov ecx, <file string>;
    call <assert>`, so the file a message is implemented in is readable straight
    out of its handler. That turns "which reconstruction do we believe" into
    "which file did ArenaNet write it in", and it is the strongest naming source
    this project has. Discovered while failing to find the death message.
    """
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        return set()
    out = set()
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va)):
        if ins.mnemonic == "mov" and ins.op_str.startswith(("edx, 0x", "ecx, 0x")):
            so = img.off(int(ins.op_str.split("0x")[1], 16))
            if so is not None:
                text = img.blob[so:so + 120].split(b"\0")[0]
                if text.startswith(b"P:"):
                    out.add(text.decode("ascii", "replace"))
        if ins.mnemonic == "ret" or n >= limit:
            break
    return out


def print_map(img):
    """opcode -> the source file its handler asserts in, for every RECV table."""
    import collections
    byfile = collections.defaultdict(list)
    n = 0
    for tva, count, direction in TABLES:
        if direction != "RECV":
            continue
        for op, cmds, disp in read_table(img, tva, count, direction):
            if not disp:
                continue
            n += 1
            for f in source_files(img, disp):
                byfile[f].append(op)
    print(f"{n} receive handlers read; {len(byfile)} source files named\n")
    for f in sorted(byfile, key=lambda k: -len(byfile[k])):
        ops = sorted(set(byfile[f]))
        print(f"{len(ops):5}  {f}")
        print("       " + " ".join(f"0x{o:04X}" for o in ops))
    print("\nHandlers with no assert name no file. That is silence, not absence.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opcode", nargs="?", help="e.g. 0x0029")
    ap.add_argument("--map", action="store_true",
                    help="map every receive opcode to the ArenaNet source file "
                         "its handler asserts in")
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--table", help="dump one table by VA instead")
    ap.add_argument("--follow", action="store_true",
                    help="also disassemble the functions the handler calls")
    ap.add_argument("--limit", type=int, default=90)
    a = ap.parse_args()

    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    img = Image(a.exe)
    print(f"{a.exe}  {len(img.blob):,} bytes, image base 0x{img.base:08x}")

    if a.map:
        print_map(img)
        return 0

    if a.table:
        tva = int(a.table, 0)
        entry = next((t for t in TABLES if t[0] == tva), None)
        if entry is None:
            sys.exit(f"0x{tva:08x} is not a known table; see TABLES")
        for op, cmds, disp in read_table(img, *entry):
            d = f"dispatch 0x{disp:08x}" if disp else "(send: no dispatch)"
            print(f"  0x{op:04x}  {d}  cmds {[hex(c) for c in cmds]}")
        return 0

    if not a.opcode:
        ap.error("give an opcode, or --table")
    want = int(a.opcode, 0)

    found = []
    for tva, count, direction in TABLES:
        for op, cmds, disp in read_table(img, tva, count, direction):
            if op == want:
                found.append((tva, direction, cmds, disp))
    if not found:
        sys.exit(f"opcode 0x{want:04x} is in no table")

    for tva, direction, cmds, disp in found:
        print(f"\ntable 0x{tva:08x} [{direction}]  cmds {[hex(c) for c in cmds]}")
        if disp is None:
            print("  the client only SENDS this one; there is no handler to read")
            continue
        print(f"  handler 0x{disp:08x}")
        print("  " + "-" * 66)
        calls = disasm(img, disp, a.limit)
        if a.follow:
            for c in dict.fromkeys(calls):
                print(f"\n  called from the handler: 0x{c:08x}")
                print("  " + "-" * 66)
                disasm(img, c, a.limit, indent="    ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
