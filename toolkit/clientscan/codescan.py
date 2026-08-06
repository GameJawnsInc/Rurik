"""Find the code that touches a struct field, or that reaches a function.

    python toolkit/clientscan/codescan.py --field 0xEC --in AvChar
    python toolkit/clientscan/codescan.py --xrefs 0x007FBD30
    python toolkit/clientscan/codescan.py --dis 0x007F82C0 --count 24
    python toolkit/clientscan/codescan.py --bounds AvChar

WHY THIS EXISTS, and it is a specific failure rather than a general wish.

studies/enemy/PLAN.md §6o recorded that nothing in the image writes the agent
field at +0xEC: "No `mov` and no `fstp` writes either offset by displacement
anywhere in the image." Four separate attempts to find the write had failed, and
that sentence closed the question for a session. It is false. There are 233
instructions touching +0xEC on build 38797, **two of which write it from inside
AvChar**, and one of those two is the setter the whole combat arc was blocked on
(§6q). The earlier scan was not lying about its own results -- it was scoped to
the wrong place and reported as a global absence.

So this module exists to make the honest version of that search cheap:

  * **`--field` finds every access, not every write**, and prints reads and
    writes together. A field with no writer but eleven readers is a real and
    interesting shape; a scan that filters to writes up front cannot show it.
  * **`--in <module>` bounds the search by ArenaNet's own assert sites**, via
    `asserts.py`. That is the step that turned "233 hits, unreadable" into
    "5 hits in AgentView, two of them stores" in under a minute. A module's
    range is min..max of the VAs where its asserts live -- approximate by
    construction, and it does not matter, because it is a filter over an
    exhaustive scan rather than the scan itself.
  * **Absence is reported as a range, never as "nowhere."** `--field 0x1B1`
    prints the range it searched, so the next reader can tell "not in AvChar"
    from "not in the image" -- the exact distinction §6o lost.

HOW THE SCAN WORKS, and why it is not a linear disassembly. A linear sweep of
.text desyncs on data and silently drops whatever follows until it re-syncs,
which is how a store can be missed by a tool that looks like it read everything.
Instead: find every occurrence of the displacement's own four bytes, then try to
decode an instruction *ending on them* from several candidate starts, and keep
the ones whose decoded operand really carries that displacement. Exhaustive over
the section, and it cannot desync because it never assumes an instruction
boundary.

Two decoding traps it handles, both of which produce confident duplicates:

  * A legacy prefix byte makes the SAME instruction decode twice, at `A` and
    `A+1`, with different operand widths -- `66 89 83 b8 01 00 00` is
    `mov word [ebx+0x1B8], ax`, and starting one byte later gives
    `mov dword [ebx+0x1B8], eax`. Both look real. The later one is dropped.
  * **x87 stores are reported by capstone as operand reads.** `fstp dword ptr
    [esi+0xEC]` is a write and capstone does not say so. MEASURED, and it is
    the whole story of how §6o went wrong: filter `+0xEC` on the access flag
    alone and you get **zero** stores in AvChar -- not a thin list, not a
    suspicious one, a clean and confident nothing. Both real writers of the
    field this arc was blocked on are `fstp`. A float field will essentially
    always be written this way, so any tool that trusts the flag is blind to
    exactly the fields most worth chasing.

DEPENDENCIES. capstone and pefile, alongside `msghandler.py`. CLAUDE.md says the
toolkit is standard library only and that file has been the one exception since
it was written, with studies/skillcast/FINDINGS.md flagging whether that is a
carve-out or a debt as the owner's call. **Decided 2026-08-06: it is a carve-out,
and this module joins it.** The rule is unchanged for everything else -- there is
no reasonable stdlib x86 disassembler, and `asserts.py`, `msgshape.py` and
`areatable.py` stay stdlib so a bare machine keeps the tools whose byte patterns
are fixed.

READ ONLY. Opens the exe for reading and does nothing else. `C:\\gw` is the
owner's own install and is never written, patched or launched from here.
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

try:
    import capstone
    import pefile
except ImportError:                                           # pragma: no cover
    sys.exit("needs capstone and pefile: python -m pip install capstone pefile")

from vaultpath import vault_path                              # noqa: E402

# The build every address in the studies is measured against. Prefer the vaulted
# snapshot over the live install: the live one auto-updates, and an offset read
# from a different build is not wrong-looking, it is just wrong.
PINNED = ("run", "2026-07-29_221c13772c7a", "Gw.exe")
FALLBACK_EXE = r"C:\gw\Gw.exe"

# Legacy prefixes that make one instruction decode twice at consecutive offsets.
_PREFIXES = (0x66, 0x67, 0xF2, 0xF3)

# x87 memory stores. capstone marks their memory operand as a READ, so the
# access flag alone would hide every floating-point store in the image.
_FPU_STORES = ("fst", "fstp", "fist", "fistp", "fisttp", "fbstp")


def find_exe():
    """The pinned snapshot, else the live install. Never silently either."""
    pinned = vault_path(*PINNED)
    if os.path.exists(pinned):
        return pinned, "pinned vault snapshot"
    if os.path.exists(FALLBACK_EXE):
        return FALLBACK_EXE, "live install (pinned snapshot not in the vault)"
    raise SystemExit(f"no client to read.\n  looked for {pinned}\n"
                     f"  and for {FALLBACK_EXE}\n  See RUNBOOK.md.")


class Image:
    """The exe, disassembled on demand."""

    def __init__(self, path=None):
        self.path = path or find_exe()[0]
        self.pe = pefile.PE(self.path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        self.md.detail = True
        self.text = next(s for s in self.pe.sections
                         if s.Name.rstrip(b"\x00") == b".text")
        self.tva = self.base + self.text.VirtualAddress
        self.tdata = self.text.get_data()

    # -- raw reads ------------------------------------------------------
    def read(self, va, n):
        rva = va - self.base
        for s in self.pe.sections:
            size = max(s.Misc_VirtualSize, s.SizeOfRawData)
            if s.VirtualAddress <= rva < s.VirtualAddress + size:
                o = rva - s.VirtualAddress
                return s.get_data()[o:o + n]
        return b""

    def cstr(self, va, cap=200):
        b = self.read(va, cap)
        z = b.find(b"\0")
        return b[:z].decode("latin-1") if z > 0 else None

    def dis(self, va, count=0, nbytes=None):
        return list(self.md.disasm(self.read(va, nbytes or max(16 * (count or 8), 64)),
                                   va, count))

    def func_start(self, va, back=0x800):
        """Best-effort walk back to the int3 padding before a function.

        BEST EFFORT, and it says so: MSVC does not pad every boundary, so this
        can return the start of an earlier function. Use it to get a listing to
        read, never as evidence about where a function begins.
        """
        blob = self.read(va - back, back)
        best = None
        for i in range(len(blob) - 2):
            if blob[i:i + 2] == b"\xcc\xcc":
                j = i + 2
                while j < len(blob) and blob[j] == 0xCC:
                    j += 1
                if j < len(blob):
                    best = va - back + j
        return best

    # -- field accesses -------------------------------------------------
    def field_access(self, disp, lo=None, hi=None):
        """Every instruction whose memory operand is [reg + disp].

        Returns [(va, is_write, base_reg, index_reg, text, hexbytes)], sorted.
        """
        out, seen = [], set()
        blob, tva = self.tdata, self.tva
        needle = struct.pack("<I", disp)

        spots, p = [], blob.find(needle)
        while p != -1:
            spots.append(p)
            p = blob.find(needle, p + 1)

        for p in spots:
            for back in range(2, 12):
                start = p - back
                if start < 0:
                    continue
                ins = next(iter(self.md.disasm(blob[start:start + 16],
                                               tva + start, 1)), None)
                if ins is None:
                    continue
                # The instruction must END on the displacement bytes (a trailing
                # immediate may follow), or we are looking at an unrelated
                # decode that happens to span them.
                if not (p + 4 <= start + ins.size <= p + 8):
                    continue
                for op in ins.operands:
                    if op.type != capstone.x86.X86_OP_MEM:
                        continue
                    if op.mem.disp != disp:
                        continue
                    if ins.address in seen:
                        continue
                    seen.add(ins.address)
                    is_w = (bool(op.access & capstone.CS_AC_WRITE)
                            or ins.mnemonic in _FPU_STORES)
                    out.append((ins.address, is_w,
                                ins.reg_name(op.mem.base) if op.mem.base else "-",
                                ins.reg_name(op.mem.index) if op.mem.index else "",
                                f"{ins.mnemonic} {ins.op_str}", ins.bytes.hex()))

        # Drop the prefix-shadow duplicate: same displacement, address one byte
        # after a real hit whose first byte is a legacy prefix.
        addrs = {r[0] for r in out}
        out = [r for r in out
               if not (r[0] - 1 in addrs
                       and self.read(r[0] - 1, 1)[:1]
                       and self.read(r[0] - 1, 1)[0] in _PREFIXES)]

        if lo is not None:
            out = [r for r in out if lo <= r[0] <= hi]
        return sorted(out)

    # -- cross references -----------------------------------------------
    def xrefs(self, target):
        """(rel32 call/jmp sites, data words holding the VA).

        BOTH, because either alone misses real callers: the client reaches
        plenty of code through tables and callbacks, and §6o's four failed
        searches for a send site were all rel32-only.
        """
        calls = []
        blob, tva = self.tdata, self.tva
        for opcode, kind in ((0xE8, "call"), (0xE9, "jmp")):
            p = blob.find(bytes([opcode]))
            while p != -1:
                if p + 5 <= len(blob):
                    rel = struct.unpack_from("<i", blob, p + 1)[0]
                    if tva + p + 5 + rel == target:
                        calls.append((tva + p, kind))
                p = blob.find(bytes([opcode]), p + 1)

        data, needle = [], struct.pack("<I", target)
        for s in self.pe.sections:
            d, sbase = s.get_data(), self.base + s.VirtualAddress
            p = d.find(needle)
            while p != -1:
                if p % 4 == 0:
                    data.append((sbase + p,
                                 s.Name.rstrip(b"\x00").decode() or "?"))
                p = d.find(needle, p + 1)
        return sorted(set(calls)), data


def module_bounds(name, exe):
    """(lo, hi, count) for an ArenaNet source module, from its own asserts.

    APPROXIMATE ON PURPOSE. A module's code is not required to be contiguous and
    a module with no asserts has no bounds at all -- `asserts.py` calls that
    silence, not absence. This is a filter over an exhaustive scan, so a range
    that is slightly too wide costs nothing and a range that is too narrow shows
    up as a hit count that disagrees with the unbounded one.
    """
    from asserts import Asserts
    hits = Asserts(exe).by_module(name.lower())
    if not hits:
        return None
    vas = [h.va for h in hits]
    return min(vas), max(vas), len(vas)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=None)
    ap.add_argument("--field", help="struct displacement, e.g. 0xEC")
    ap.add_argument("--xrefs", help="VA: every call/jmp and data word to it")
    ap.add_argument("--dis", help="VA: disassemble from here")
    ap.add_argument("--bounds", help="module name: its address range")
    ap.add_argument("--in", dest="module",
                    help="restrict --field to one ArenaNet module, e.g. AvChar")
    ap.add_argument("--count", type=int, default=24,
                    help="instructions for --dis")
    ap.add_argument("--writes", action="store_true",
                    help="--field: stores only. Off by default -- a field's "
                         "readers are usually what tells you what it is for.")
    a = ap.parse_args()

    exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
    print(f"client: {exe}\n        ({why})\n")
    img = Image(exe)

    if a.bounds:
        b = module_bounds(a.bounds, exe)
        if not b:
            return print(f"{a.bounds}: no asserts, so no bounds. That is "
                         f"silence, not absence -- the module may still be "
                         f"there with nothing to assert.")
        print(f"{a.bounds}: 0x{b[0]:08X}..0x{b[1]:08X}  ({b[2]} assert sites)")
        return 0

    if a.field:
        disp = int(a.field, 0)
        lo = hi = None
        where = "the whole .text section"
        if a.module:
            b = module_bounds(a.module, exe)
            if not b:
                return print(f"cannot bound {a.module}: it has no asserts.")
            lo, hi, n = b
            where = f"{a.module} 0x{lo:08X}..0x{hi:08X} ({n} assert sites)"
        rows = img.field_access(disp, lo, hi)
        if a.writes:
            rows = [r for r in rows if r[1]]
        # Say WHERE we looked, always. "Nothing writes it" is only a finding
        # when the range is stated with it.
        print(f"[reg + 0x{disp:X}] in {where}\n"
              f"{len(rows)} instruction(s)"
              + (" (stores only)" if a.writes else
                 f", {sum(1 for r in rows if r[1])} of them stores"))
        for va, w, base, idx, txt, hx in rows:
            print(f"  {va:08X}  {'W' if w else 'R'}  base={base:<4} "
                  f"{idx:<4} {txt:<40} {hx}")
        if not rows:
            print("  -- none. That is a statement about the range above and "
                  "nothing wider.")
        return 0

    if a.xrefs:
        t = int(a.xrefs, 0)
        calls, data = img.xrefs(t)
        print(f"0x{t:08X}: {len(calls)} direct rel32 reference(s), "
              f"{len(data)} data word(s)")
        for va, kind in calls:
            print(f"  {va:08X}  {kind}")
        for va, sec in data:
            print(f"  {va:08X}  in {sec}")
        return 0

    if a.dis:
        va = int(a.dis, 0)
        start = img.func_start(va)
        if start and start != va:
            print(f"(nearest earlier int3 padding: 0x{start:08X} -- best "
                  f"effort, not proof of a function boundary)\n")
        for ins in img.dis(va, count=a.count):
            print(f"  {ins.address:08X}  {ins.bytes.hex():<16} "
                  f"{ins.mnemonic} {ins.op_str}")
        return 0

    ap.error("give --field, --xrefs, --dis or --bounds")


if __name__ == "__main__":
    sys.exit(main())
