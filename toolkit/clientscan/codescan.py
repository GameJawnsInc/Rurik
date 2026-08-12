"""Find the code that touches a struct field, or that reaches a function.

    python toolkit/clientscan/codescan.py --field 0xEC --in AvChar
    python toolkit/clientscan/codescan.py --xrefs 0x007FBD30
    python toolkit/clientscan/codescan.py --dis 0x007F82C0 --count 24
    python toolkit/clientscan/codescan.py --bounds AvChar

WHY THIS EXISTS, and it is a specific failure rather than a general wish.

studies/enemy/PLAN.md §6o recorded that nothing in the image writes the agent
field at +0xEC: "No `mov` and no `fstp` writes either offset by displacement
anywhere in the image." Four separate attempts to find the write had failed, and
that sentence closed the question for a session. It is false. There are 238
instructions touching +0xEC on build 38797 (233 until the anchoring below was
made exact, which added five `A1 <moffs32>` absolute forms outside AvChar),
**two of which write it from inside AvChar**, and one of those two is the setter
the whole combat arc was blocked on
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

WHAT THE SCAN COVERS, STATED IN THE OUTPUT. "Absence is reported as a range"
was not enough. On 2026-08-10 a reservation-safety pass found this module
under-reporting in two ways, both of which produce a clean confident zero -- the
same shape as the §6o failure above, from inside the tool written to prevent it:

  * **`--xrefs` swept data words at 4-byte alignment only** (`if p % 4 == 0`),
    so three of four alignments were never examined. `--xrefs 0x00479280`
    answered "0 direct rel32 reference(s), 0 data word(s)" while
    `0x00478CF5 push 0x479280` sits in `.text` with its operand at 0x00478CF6
    -- two off aligned. Fixed: every alignment, in every section, and a `.text`
    hit is now decoded back to the instruction that carries it, so the answer
    reads `push 0x479280` rather than "a word, somewhere".
  * **`--field` knew one displacement encoding.** It searched for the
    displacement's four bytes, which is the disp32 form (mod=10) only. Every
    displacement under 0x80 is normally emitted as disp8 (mod=01, ONE byte),
    and `--field 0xE --in ExeArchive` therefore reported "0 instructions, 0
    stores" with `0x00478FB8 mov byte [edi+0xe], al` inside the range. Fixed:
    both encodings, anchored exactly (see below).

So the range is no longer the only thing said out loud. `--field` prints which
ENCODINGS it searched and which it provably cannot reach; `--xrefs` prints which
alignments and sections. A zero now carries the discipline that produced it,
because a reader cannot otherwise tell "not encoded that way" from "not there."

The one encoding no anchored scan can reach is mod=00 `[reg]` -- displacement
zero, written as no bytes at all. `--field 0x0` says so rather than implying its
count is complete; finding those needs a linear sweep, and a linear sweep is the
thing this module refuses (see above).

ANCHORING IS EXACT, not a window. A candidate decode is kept only when
capstone's own encoding record puts the displacement on the bytes we found it
at -- `start + insn.encoding.disp_offset == p` and `disp_size` equal to the
width searched. The previous rule ("the instruction must END within four bytes
of the displacement") was a proxy for that, and it is both looser and, for the
`A1 <disp32>` forms whose displacement starts one byte in, tighter than the
truth: the candidate-start loop began at 2 and could not see them.

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
no reasonable stdlib x86 disassembler, and `asserts.py`, `msgshape.py`,
`areatable.py` and `avevents.py` stay stdlib so a bare machine keeps the tools
whose byte patterns are fixed.

TWO DECODERS, ON PURPOSE. `avevents.py` was written in a parallel session and
carries its own hand-rolled x86 length table, so for a day this repository had
two independent decoders and no statement about which to use. Reconciled
2026-08-06, and the answer is not "delete one":

  * **This module is the default.** Reading code you have not read before,
    finding what touches a field, following xrefs including data references --
    all of that needs a real disassembler and none of it has a fixed pattern.
  * **`avevents.py` stays stdlib** because its pattern IS fixed (`push <imm>`
    then a call to one of two known addresses), which keeps
    `test_skillcast.py` -- and every claim in studies/skillcast §16 -- runnable
    with nothing installed.
  * **The overlap is now a check rather than a risk.** `test_codescan.py` §6
    disassembles every byte `avevents.py` walks and asserts the two agree
    instruction for instruction: 127 functions, 1601 instructions, no
    disagreement. Two independent decoders over the same bytes is an
    independent witness, which is the same argument `msgshape.py` makes when
    its initializer recovery lands on the identical count studies/msgtable
    reached through PE relocations.

What was genuinely redundant has gone: `avevents.py` used to carry a third copy
of the `call rel32` scan that `asserts.direct_callers` already had, with
byte-identical results. It now calls that. `xrefs()` here is the one that is
not redundant -- it also finds `jmp rel32` and data words holding the VA, which
is what §6o's four rel32-only searches missed.

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

import pinned as _pinned                                      # noqa: E402

# The build every address in the studies is measured against. `pinned.py` owns
# the resolution now, because the vault holds TWO copies of 38797 at the SAME
# size -- pristine and our patched one -- and this module used to ask for the
# patched copy by name while `srctree.py` asked for the pristine one. Neither
# said so, and a size check cannot tell them apart.
FALLBACK_EXE = _pinned.LIVE_INSTALL

# Legacy prefixes that make one instruction decode twice at consecutive offsets.
_PREFIXES = (0x66, 0x67, 0xF2, 0xF3)

# x87 memory stores. capstone marks their memory operand as a READ, so the
# access flag alone would hide every floating-point store in the image.
_FPU_STORES = ("fst", "fstp", "fist", "fistp", "fisttp", "fbstp")


find_exe = _pinned.find


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
    @staticmethod
    def field_encodings(disp):
        """(searched, blind) for `[reg + disp]`, each [(name, detail)].

        The scope statement `--field` prints. An anchored scan can only find a
        displacement that is written into the instruction stream, so which
        encodings exist for THIS displacement decides what a zero can mean --
        and that is a property of the number, not of the image.
        """
        searched = [("disp32", "mod=10, the four-byte form")]
        blind = []
        if 0 <= disp <= 0x7F:
            searched.append(("disp8", "mod=01, the one-byte form -- how a "
                                      "compiler normally emits this offset"))
        else:
            blind.append(("disp8", f"0x{disp:X} does not fit a signed byte, so "
                                   f"no disp8 encoding of it can exist"))
        if disp == 0:
            blind.append(("no displacement", "mod=00 `[reg]` writes NO "
                          "displacement bytes, so there is nothing to anchor "
                          "on. Accesses to +0x0 through a plain `[reg]` are "
                          "absent from the rows above and this scan cannot "
                          "count them"))
        blind.append(("disp16", "needs a 0x67 address-size prefix, which "
                                "32-bit compiled code does not emit"))
        return searched, blind

    def field_access(self, disp, lo=None, hi=None):
        """Every instruction whose memory operand is [reg + disp].

        Returns [(va, is_write, base_reg, index_reg, text, hexbytes)], sorted.

        SEARCHES EVERY ENCODING THE DISPLACEMENT CAN HAVE -- see
        `field_encodings`, which is what `--field` prints alongside the count.
        Searching disp32 alone reported zero for `+0xE` in ExeArchive with a
        `mov byte [edi+0xe], al` sitting inside the range.
        """
        out, seen = [], set()
        blob, tva = self.tdata, self.tva

        # One anchor per encoding: the displacement's own bytes, as written.
        anchors = [(struct.pack("<I", disp), 4)]
        if 0 <= disp <= 0x7F:
            anchors.append((bytes([disp]), 1))

        # Restrict the sweep to the requested range when there is one. An
        # instruction inside [lo, hi] carries its displacement after its own
        # first byte, so the anchor cannot lie before `lo` nor more than one
        # instruction past `hi`. This is what keeps the one-byte disp8 anchor
        # -- which matches roughly every 256th byte of a 5 MB section -- cheap
        # on the `--in <module>` path that is the flagship entry point.
        blo = 0 if lo is None else max(0, lo - tva)
        bhi = len(blob) if hi is None else min(len(blob), hi - tva + 16)

        for needle, ndisp in anchors:
            p = blob.find(needle, blo, bhi)
            while p != -1:
                # `back` starts at 1: `A1 <disp32>` and friends put the
                # displacement one byte in, and a loop starting at 2 could not
                # see them.
                for back in range(1, 12):
                    start = p - back
                    if start < 0:
                        continue
                    ins = next(iter(self.md.disasm(blob[start:start + 24],
                                                   tva + start, 1)), None)
                    if ins is None:
                        continue
                    # EXACT, from capstone's own encoding record: this
                    # instruction's displacement field must BE the bytes we
                    # found, at the width we searched. No window, no proxy.
                    enc = ins.encoding
                    if enc.disp_size != ndisp or start + enc.disp_offset != p:
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
                p = blob.find(needle, p + 1, bhi)

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
    def carrier(self, va, value):
        """The .text instruction whose own operand is the four bytes at `va`.

        A VA held in the instruction stream is a reference exactly as much as
        one held in a table -- `push 0x479280` is how the archive allocator's
        comparator reaches its caller -- and naming the instruction is the
        difference between an answer and a coordinate. Anchored the same way
        `field_access` is: candidate starts, kept only when capstone's encoding
        record puts an immediate or an absolute displacement precisely on those
        four bytes. Returns None outside .text or when nothing decodes.
        """
        if not (self.tva <= va < self.tva + len(self.tdata)):
            return None
        blob, p = self.tdata, va - self.tva
        for back in range(1, 12):
            start = p - back
            if start < 0:
                continue
            ins = next(iter(self.md.disasm(blob[start:start + 24],
                                           self.tva + start, 1)), None)
            if ins is None:
                continue
            enc = ins.encoding
            if not ((enc.imm_size == 4 and start + enc.imm_offset == p)
                    or (enc.disp_size == 4 and start + enc.disp_offset == p)):
                continue
            # Placement says these four bytes are the operand field; this says
            # capstone decoded them to the value we searched for. Implied, and
            # checked anyway -- an operand printed next to an address the reader
            # will trust should not rest on the two agreeing by construction.
            if not any(
                    (op.type == capstone.x86.X86_OP_IMM
                     and op.imm & 0xFFFFFFFF == value)
                    or (op.type == capstone.x86.X86_OP_MEM
                        and op.mem.disp & 0xFFFFFFFF == value)
                    for op in ins.operands):
                continue
            return (ins.address, f"{ins.mnemonic} {ins.op_str}")
        return None

    def xrefs(self, target):
        """(rel32 call/jmp sites, four-byte windows holding the VA).

        BOTH, because either alone misses real callers: the client reaches
        plenty of code through tables and callbacks, and §6o's four failed
        searches for a send site were all rel32-only.

        EVERY ALIGNMENT. This swept `if p % 4 == 0` until 2026-08-10, which
        examined one alignment in four and answered a clean "0 data word(s)"
        for `0x00479280` -- whose only reference in the image is the immediate
        of a `push` at 0x00478CF5, landing two bytes off aligned. Nothing
        requires a pointer to be aligned, least of all one baked into an
        instruction, and the filter was reporting an absence it had not looked
        for. Each hit now carries whether it is aligned and, in .text, the
        instruction that carries it, so a table entry and an immediate stay
        distinguishable without the filter that was hiding one of them.

        Words are [(va, section, aligned, carrier_or_None)].
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

        words, needle = [], struct.pack("<I", target)
        for s in self.pe.sections:
            d, sbase = s.get_data(), self.base + s.VirtualAddress
            name = s.Name.rstrip(b"\x00").decode(errors="replace") or "?"
            p = d.find(needle)
            while p != -1:
                va = sbase + p
                words.append((va, name, va % 4 == 0, self.carrier(va, target)))
                p = d.find(needle, p + 1)
        return sorted(set(calls)), sorted(words)


_ASSERTS = {}


def _asserts(exe):
    """One `Asserts` per exe per process. Scanning 5.4 MB is not free and the
    two queries below plus `test_codescan.py` ask for it several times a run."""
    from asserts import Asserts
    if exe not in _ASSERTS:
        _ASSERTS[exe] = Asserts(exe)
    return _ASSERTS[exe]


def module_bounds(name, exe):
    """(lo, hi, count) for an ArenaNet source module, from its own asserts.

    APPROXIMATE ON PURPOSE. A module's code is not required to be contiguous and
    a module with no asserts has no bounds at all -- `asserts.py` calls that
    silence, not absence. This is a filter over an exhaustive scan, so a range
    that is slightly too wide costs nothing and a range that is too narrow shows
    up as a hit count that disagrees with the unbounded one.

    "SLIGHTLY" DOES NOT COVER A BASENAME COLLISION, though, which is why
    `module_files` exists beside this. `name` is matched as a substring, and nine
    basenames on build 38797 name two source files each: `PrApi` bounds
    0x00499B01..0x0073943A because ArenaNet has a preferences PrApi.cpp and a
    props PrApi.cpp 2.4 MB apart, and a `--field --in PrApi` inside that range is
    drawn from most of the image. Call `module_files` and say what was bounded.
    """
    hits = _asserts(exe).by_module(name.lower())
    if not hits:
        return None
    vas = [h.va for h in hits]
    return min(vas), max(vas), len(vas)


def module_files(name, exe):
    """The distinct source files `name` matched: {path: (count, lo, hi)}.

    Reported rather than resolved. A substring is a legitimate way to name a
    subsystem -- `--in Rtl` meaning all of it is a real query -- so the caller is
    told what its name actually caught and decides, instead of this guessing that
    two files 2.4 MB apart were not both wanted.
    """
    per = {}
    for h in _asserts(exe).by_module(name.lower()):
        per.setdefault(h.file, []).append(h.va)
    return {f: (len(v), min(v), max(v)) for f, v in per.items()}


def bounds_note(name, exe, indent="  "):
    """The lines `--bounds`/`--in` print when a name caught more than one file.

    Each file's OWN span, not just its name, because the two ways a name catches
    two files are not equally bad and the reader has to be able to tell them
    apart. `AvChar` also matches `AvCharAnim.cpp`, whose two sites sit
    immediately below AvChar.cpp's -- the range grows by 0x17F0 bytes of
    genuinely adjacent code and nothing downstream notices. `PrApi` matches two
    unrelated modules 2.4 MB apart and the range between them is 99.9% neither.
    Printing only the file names would make those look like the same warning.

    Empty list when the name caught one file, which is the usual case.
    """
    files = module_files(name, exe)
    if len(files) < 2:
        return []
    out = [f"WARNING: `{name}` matched {len(files)} source files, so the range "
           f"above is their union and the gaps between them belong to neither:"]
    for path in sorted(files, key=lambda p: files[p][1]):
        n, lo, hi = files[path]
        out.append(f"{indent}{n:5}  0x{lo:08X}..0x{hi:08X}  {path}")
    return out


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
        for line in bounds_note(a.bounds, exe):
            print(line)
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
            for line in bounds_note(a.module, exe):
                print(line)
        rows = img.field_access(disp, lo, hi)
        if a.writes:
            rows = [r for r in rows if r[1]]
        # Say WHERE we looked and HOW, always. "Nothing writes it" is only a
        # finding when the range is stated with it -- and only an honest one
        # when the encodings searched are stated too, because a scan that knew
        # one encoding reported a confident zero over a range containing the
        # instruction it was looking for.
        searched, blind = Image.field_encodings(disp)
        print(f"[reg + 0x{disp:X}] in {where}\n"
              f"{len(rows)} instruction(s)"
              + (" (stores only)" if a.writes else
                 f", {sum(1 for r in rows if r[1])} of them stores"))
        for va, w, base, idx, txt, hx in rows:
            print(f"  {va:08X}  {'W' if w else 'R'}  base={base:<4} "
                  f"{idx:<4} {txt:<40} {hx}")
        if not rows:
            print("  -- none. That is a statement about the range and the "
                  "encodings below, and nothing wider.")
        # A row with no base register is `[0xdisp]`, an absolute address that
        # happens to equal the displacement -- not a struct field. Counted and
        # named rather than filtered out, because a quiet filter is the defect
        # this module was rewritten to stop making.
        noreg = sum(1 for r in rows if r[2] == "-")
        if noreg:
            print(f"\n{noreg} of the above have no base register: those are "
                  f"absolute address 0x{disp:X}, not a field at +0x{disp:X}.")
        print("\nencodings searched: "
              + ", ".join(f"{n} ({d})" for n, d in searched))
        for n, d in blind:
            print(f"NOT searched: {n} -- {d}")
        return 0

    if a.xrefs:
        t = int(a.xrefs, 0)
        calls, words = img.xrefs(t)
        naligned = sum(1 for w in words if w[2])
        print(f"0x{t:08X}: {len(calls)} direct rel32 reference(s), "
              f"{len(words)} word(s) holding the VA "
              f"({naligned} aligned, {len(words) - naligned} not)")
        for va, kind in calls:
            print(f"  {va:08X}  {kind}")
        for va, sec, aligned, carried in words:
            note = f"  <- {carried[0]:08X}  {carried[1]}" if carried else ""
            print(f"  {va:08X}  in {sec:<8} "
                  f"{'aligned' if aligned else f'+{va % 4} off':<9}{note}")
        print(f"\nsearched: `call rel32` and `jmp rel32` over .text; the four "
              f"bytes of 0x{t:08X} at EVERY alignment across all "
              f"{len(img.pe.sections)} sections.")
        print("NOT searched: indirect calls through a register or vtable, and "
              "any address the image computes rather than stores. An empty "
              "result is 'nothing stores or directly branches to it', not "
              "'nothing reaches it'.")
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
