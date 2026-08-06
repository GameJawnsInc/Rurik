"""Find and disassemble the client's own handler for a message.

    python toolkit/clientscan/msghandler.py 0x0029
    python toolkit/clientscan/msghandler.py 0x0029 --follow      # + called fn
    python toolkit/clientscan/msghandler.py --table 0xa52d70     # whole table
    python toolkit/clientscan/msghandler.py 0x00E5 --follow --annotate
    python toolkit/clientscan/msghandler.py --callers 0x00822b80 # who calls it

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

A WARNING THIS TOOL CANNOT GIVE YOU, so read it here. The `cmds` arrays it
prints are, for more than half the catalogue, ZERO in the file and written at
load time -- and a zero decodes as a legal four-byte field. Do not read wire
shapes off the raw `cmds` this prints. `msgshape.py` next door recovers the
load-time writes and refuses to guess past a slot it could not account for;
that is the module to ask about shapes.

DEPENDENCIES. capstone and pefile. This used to be an unresolved exception to
CLAUDE.md's standard-library-only rule; **the owner settled it on 2026-08-06 as
an explicit carve-out for read-only client analysis**, and it now covers this
file and `codescan.py` next door and nothing else. `asserts.py`, `msgshape.py`,
`areatable.py` and `genericvalue.py` stay stdlib on purpose, so a bare machine
keeps every tool whose byte patterns are fixed, and a *claim* still wants a
stdlib checker even when a disassembler found it.

READ ONLY. Opens Gw.exe for reading and does nothing else. The install at
C:\\gw is the player's own and is never written, patched or launched from here.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    import capstone
    import pefile
except ImportError:                                           # pragma: no cover
    sys.exit("needs capstone and pefile: python -m pip install capstone pefile")

from msgshape import TABLES                                   # noqa: E402,F401

DEFAULT_EXE = r"C:\gw\Gw.exe"


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


def _cstr(img, va, cap=140):
    """The ASCII string at a VA, or None. Used only to annotate operands."""
    o = img.off(va)
    if o is None:
        return None
    b = img.blob[o:o + cap]
    z = b.find(b"\0")
    if z < 1:
        return None
    b = b[:z]
    if len(b) < 4 or not all(32 <= c < 127 for c in b):
        return None
    return b.decode("ascii")


def _annotator(img, exe):
    """A per-instruction comment: the client's own asserts and strings.

    A handler that logs `"Pending skill %u copy %d not found"` has told you
    what its arguments are called. That one string settled `skill_instance`
    after every written source had it as NOT FOUND, so surfacing them is worth
    a flag.
    """
    from asserts import Asserts
    az = Asserts(exe)
    by_va = {a.va: a for a in az.items}

    def note(ins):
        out = []
        a = by_va.get(ins.address)
        if a:
            out.append(f"ASSERT {a.module}:{a.line} {a.expr}")
        for tok in ins.op_str.replace(",", " ").replace("[", " ") \
                             .replace("]", " ").split():
            if tok.startswith("0x") and len(tok) >= 8:
                try:
                    s = _cstr(img, int(tok, 16))
                except ValueError:
                    s = None
                if s:
                    out.append(f'"{s[:100]}"')
        return ("   ; " + "  ".join(out)) if out else ""
    return note


def disasm(img, va, limit=90, indent="  ", note=None):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = img.off(va)
    if o is None:
        print(f"{indent}(0x{va:08x} is not mapped)")
        return []
    calls = []
    for n, ins in enumerate(md.disasm(img.blob[o:o + limit * 8], va)):
        print(f"{indent}0x{ins.address:08x}  {ins.mnemonic:<7} {ins.op_str}"
              f"{note(ins) if note else ''}")
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
        # A one-line `push ebp / mov ebp,esp / pop ebp / jmp target` is MSVC's
        # tail-call thunk. Following it is the difference between reading a
        # trampoline and reading the function.
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x") and n <= 4:
            try:
                calls.append(int(ins.op_str, 16))
            except ValueError:
                pass
            break
        if ins.mnemonic == "ret" or n >= limit:
            break
    return calls


def callers(exe, target):
    """Every direct `call` to a VA. One implementation, in asserts.py."""
    from asserts import Asserts
    return Asserts(exe).direct_callers(target)


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
                    help="also disassemble the functions the handler calls, "
                         "and step through MSVC tail-call thunks")
    ap.add_argument("--annotate", action="store_true",
                    help="comment each line with the assert or string it "
                         "references -- the client's own words")
    ap.add_argument("--callers", help="VA; list every direct call to it")
    ap.add_argument("--depth", type=int, default=1,
                    help="how many call levels --follow descends (default 1)")
    ap.add_argument("--limit", type=int, default=90)
    a = ap.parse_args()

    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    img = Image(a.exe)
    print(f"{a.exe}  {len(img.blob):,} bytes, image base 0x{img.base:08x}")
    note = _annotator(img, a.exe) if a.annotate else None

    if a.map:
        print_map(img)
        return 0

    if a.callers:
        target = int(a.callers, 0)
        hits = callers(a.exe, target)
        print(f"{len(hits)} direct caller(s) of 0x{target:08x}")
        for h in hits:
            print(f"  0x{h:08x}")
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
        calls = disasm(img, disp, a.limit, note=note)
        if a.follow:
            # Breadth-first to --depth. Depth 1 is the old behaviour. Depth 3
            # is what it takes to get from a skill opcode to the code that
            # means something: the handler is a trampoline into ChCliApi,
            # which is a trampoline into ChCliSkill, which is where the
            # asserts and the log strings live.
            seen, queue = set(), [(c, 1) for c in dict.fromkeys(calls)]
            while queue:
                c, depth = queue.pop(0)
                if c in seen or depth > a.depth:
                    continue
                seen.add(c)
                print(f"\n  depth {depth}, reached from the handler: 0x{c:08x}")
                print("  " + "-" * 66)
                for m in disasm(img, c, a.limit, indent="    ", note=note):
                    queue.append((m, depth + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
