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

**And a THIRD, 2026-08-13, which is why the paragraph below now says what it is
NOT looking for and not only how it looks.** `--field` searched for the constant
as a MEMORY DISPLACEMENT and nothing else, so it was blind to the field address
being computed in a register and dereferenced somewhere else:

  * `--field 0x6bc` reported **14 instructions** over the whole image and did
    not contain `0x00813AD1 add ecx, 0x6bc`, which studies/profession/RUNS.md
    §13 had just identified as the writer reached from GAME_SMSG 0x00B6's
    handler -- **the writer of the very field that search was run to find.**
    Four more `add ecx, 0x6bc` sites and an `add ebx, 0x6bc` were missing with
    it: 5 of 19, a quarter of the answer, absent from a report whose footer
    disclaimed the disp8 and disp16 encodings and therefore read as complete.

The lesson is the one the first two already taught and this module had only
half-learned: a scope statement that lists encodings answers "how is this number
written" and not "what does the code do with it". `MOV`-through-a-displacement
and `ADD`-then-dereference are the same access at the source level and the
second leaves the displacement in an IMMEDIATE field. So `--field` now runs two
scans over the same anchors -- see `field_encodings` for the memory half and
`address_forms` for the arithmetic one -- and prints both scope statements.

ADDRESS-TAKING IS ITS OWN CLASS, not a third kind of read. `add ecx, 0x6bc` and
`lea ecx, [edi+0x6bc]` compute where the field IS; whether anything is loaded or
stored through the pointer happens in another instruction and usually in another
function (0x00813AD1's callee `0x0081FD00` is where 0x00B6's mask actually
lands). Folding them into R would claim a read the scan has not seen, so rows
are `W` / `R` / `A` and the counts are printed separately. It also means
`--writes` alone cannot answer "who writes this field" -- a store through a
computed pointer is an `A` row here and a `W` row at some other displacement --
so `--writes` says how many address-taking rows it dropped rather than dropping
them quietly.

So the range is no longer the only thing said out loud. `--field` prints which
ENCODINGS and which ADDRESS FORMS it searched and which it provably cannot
reach; `--xrefs` prints which alignments and sections. A zero now carries the
discipline that produced it, because a reader cannot otherwise tell "not encoded
that way" from "not there."

The one encoding no anchored scan can reach is mod=00 `[reg]` -- displacement
zero, written as no bytes at all. `--field 0x0` says so rather than implying its
count is complete; finding those needs a linear sweep, and a linear sweep is the
thing this module refuses (see above). The arithmetic scan has the matching hole
and it is wider: an address the image builds through a register (`mov eax,
0x6BC` then `add ecx, eax`) or in more than one step writes the constant into an
instruction this scan does find, but the ADDITION carries no constant at all.
Both are named in the footer instead of being left to the count.

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
import collections
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

# One row of `field_access`. A namedtuple rather than a plain tuple because
# `kind` had to be added to rows that four sections of `test_codescan.py` index
# positionally: appending a field keeps `r[0]`, `r[1]`, `r[2]`, `r[4]` and
# `r[5]` meaning exactly what they meant, so the pins that already exist go on
# measuring what they were written to measure.
#
#   kind  W  a store into [reg + disp]
#         R  a load from it
#         A  the ADDRESS computed, with no access to memory at this instruction
Access = collections.namedtuple(
    "Access", "va is_write base index text hexbytes kind")


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

    def dis_upto(self, va, count=16, search=96):
        """Disassemble the `count` instructions ENDING at `va`, aligned onto it.

        `--dis va-0x20` is a guess, and on x86 a wrong guess is not a near
        miss: starting one byte off decodes a different instruction stream
        that stays wrong for a while and can produce nothing recognisable at
        all. Reading five call sites for their pushed arguments, two came back
        as garbage (`add byte ptr [ebx - 0x7c76fbbf], cl`) purely because the
        chosen start was mid-instruction -- and a reader who does not notice
        will take the operands seriously.

        So this searches instead of guessing: try every start in
        `[va - search, va)`, decode forward, and keep the streams that land
        EXACTLY on `va`. The longest such stream is the one that has been in
        sync the longest, and is returned. Returns [] when nothing aligns,
        which is itself informative -- it means `va` is not an instruction
        boundary in any nearby decode, i.e. a phantom.

        CONSENSUS, NOT LENGTH, decides which candidate is real -- and the
        difference is not cosmetic. x86 re-synchronises within a few
        instructions, so a start that lands mid-instruction produces garbage
        for a while and then joins the true stream, reaching `va` exactly like
        a good start does. Taking the LONGEST such stream therefore prefers
        the one that started earliest, garbage and all: reading the shared
        setter's call site that way returned
        `add byte ptr [ebx - 0x7c76f3bf], cl` for what is really a run of
        `mov dword ptr [ebx+0xNN], eax`.

        So every start that reaches `va` votes on where the instruction
        boundaries are, and a stream is scored by its WEAKEST boundary. The
        true stream's boundaries are agreed by nearly every candidate, because
        they all converge onto it; a garbage prefix is agreed by almost none.

        VOTES ARE NORMALISED BY ELIGIBILITY, which a first cut got wrong. A
        boundary 90 bytes back can only be voted for by the candidates that
        start at least that far back, so raw vote counts punish exactly the
        long streams this function exists to produce -- scoring on the raw
        minimum returned two instructions where fourteen were available. What
        matters is the FRACTION of candidates that could have agreed and did.
        """
        # The function's own start, when the int3 padding gives one, beats any
        # amount of voting: a linear decode from a true boundary is in sync by
        # construction. Best effort, so it is checked rather than trusted --
        # it wins only if its stream actually contains `va`.
        fs = self.func_start(va)
        if fs is not None and 0 < va - fs <= search * 4:
            ins = self.dis(fs, count=(va - fs), nbytes=(va - fs) + 16)
            hit = next((i for i, x in enumerate(ins) if x.address == va), None)
            if hit is not None:
                return ins[max(0, hit - count):hit + 1]

        cands, votes, eligible = [], collections.Counter(), collections.Counter()
        for k in range(1, search + 1):
            start = va - k
            ins = self.dis(start, count=count * 2 + 8,
                           nbytes=k + 16 * (count + 2))
            hit = next((i for i, x in enumerate(ins) if x.address == va), None)
            if hit is None:
                continue
            stream = ins[max(0, hit - count):hit + 1]
            cands.append((start, stream))
            votes.update(x.address for x in stream)
        if not cands:
            return []
        for start, _ in cands:
            for a in set(votes):
                if a >= start:
                    eligible[a] += 1

        def agreement(stream):
            return min(votes[x.address] / max(1, eligible[x.address])
                       for x in stream)

        # THRESHOLD, THEN LENGTH -- not `max((agreement, length))`, which is
        # still the short-stream bug wearing a normalised coat: any long stream
        # with one merely-good boundary loses to a two-instruction stream with
        # two perfect ones, and the positive control came back as two
        # instructions when six were available and known correct. A boundary
        # agreed by three quarters of the candidates that could see it is
        # real; among the streams built only of those, longest wins.
        good = [c for c in cands if agreement(c[1]) >= 0.75]
        if good:
            return max(good, key=lambda c: len(c[1]))[1]
        return max(cands, key=lambda c: (agreement(c[1]), len(c[1])))[1]

    def boundary_status(self, va):
        """"confirmed" | "phantom" | "unknown" -- is `va` a real instruction?

        The phantom filter. A one-byte anchor -- the mask 0x04, a shift count,
        a disp8 -- matches roughly every 256th byte of the section, and some of
        those bytes are in the MIDDLE of a longer instruction. MEASURED on
        build 38797: `d9 5c 24 04` is `fstp dword ptr [esp+4]` at 0x00600FD2,
        and its last two bytes decode on their own as `and al, 4` -- which put
        three phantom "reads of bit 18" at 0x00600FD4, 0x00601974 and
        0x00602526 into the first run of `bit_access`, indistinguishable in the
        output from the one real site.

        ANCHORED ON THE FUNCTION'S OWN START, not on whether SOME decode
        reaches `va`. Searching 96 starts, something almost always aligns:
        0x00600FD4 -- a phantom confirmed by hand against the true stream --
        aligns from 0x00600FCE as `or cl, bl / inc ebp / rcr cl, 1 / pop esp`,
        four plausible instructions of pure coincidence. Only a decode from a
        REAL boundary settles it, and the int3 padding before a function is the
        one real boundary available for free.

        Returns "unknown" rather than guessing when no padding is found or the
        function is too long to walk -- an honest third answer, because
        treating "unknown" as "phantom" would silently drop real sites.
        """
        fs = self.func_start(va)
        if fs is None or not 0 < va - fs <= 0x800:
            return "unknown"
        ins = self.dis(fs, count=(va - fs), nbytes=(va - fs) + 16)
        if not ins or ins[-1].address < va - 16:
            return "unknown"          # decode died early; says nothing
        return "confirmed" if any(x.address == va for x in ins) else "phantom"

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

        Half of the scope statement `--field` prints -- the MEMORY half, where
        the constant is a displacement inside a memory operand.
        `address_forms` is the other half. An anchored scan can only find a
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

    @staticmethod
    def address_forms(disp):
        """(searched, blind) for computing `reg + disp`, each [(name, detail)].

        The other half of `--field`'s scope statement, and the half that did not
        exist until 2026-08-13. A field can be reached without its offset ever
        appearing in a memory operand -- take the address, then dereference the
        register -- and `--field 0x6bc` reported 14 sites with `0x00813AD1
        add ecx, 0x6bc` not among them, five sites short and missing the one the
        search was run for.

        Blind is the honest part here, because the arithmetic hole is wider than
        the memory one: an addition whose operand is a REGISTER carries no
        constant for an anchored scan to find, and nothing about the offset is
        recoverable from the instruction that performs it.
        """
        searched = [("add r32, imm32", "`81 /0` and the `05` eax short form"),
                    ("sub r32, -imm32",
                     "the same address spelled as a subtraction, and not "
                     "hypothetical -- 265 sites of `sub eax, -0x80` on build "
                     "38797. Its anchor is -disp, so it is the one form here "
                     "that costs a second sweep of the section")]
        if 0 <= disp <= 0x7F:
            searched.append(("add/sub r32, imm8",
                             "`83 /0` and `83 /5`, the one-byte forms a "
                             "compiler prefers for an offset this small"))
        searched.append(("lea r32, [reg + disp]",
                         "found by the memory scan above -- lea's constant IS "
                         "a displacement -- and reported `A` rather than `R`, "
                         "because it touches no memory"))
        blind = [("the constant held in a register",
                  f"`mov eax, 0x{disp:X}` then `add ecx, eax` puts 0x{disp:X} "
                  f"in a row above and the ADDITION nowhere. `--xrefs` on the "
                  f"function is the fallback"),
                 ("an address built in more than one step",
                  "`add ecx, 0x600` then `add ecx, 0xBC` reaches +0x6BC "
                  "carrying neither constant. Nothing anchored can see this"),
                 ("a narrow destination register",
                  "an 8- or 16-bit destination cannot hold an address in "
                  "32-bit code, so those rows are dropped rather than "
                  "reported. MEASURED: `add al, 0xe` at 0x00479BC8 is the one "
                  "`--field 0xE --in ExeArchive` would otherwise carry"),
                 ("a field reached through a BIASED `this`",
                  f"where the code holds a pointer to a SUBOBJECT, the same "
                  f"field is spelled with a smaller displacement and "
                  f"0x{disp:X} never appears at all. MEASURED, and it cost a "
                  f"published claim: every message worker in `PyCliParty` "
                  f"takes `this = party_object + 4`, so `m_partyClient` at "
                  f"+0x54 is written as `mov [esi+0x50], eax` (0x00858872). "
                  f"`--field 0x54 --writes` found the two +0x54 stores that "
                  f"DO exist off the object base and reported them correctly "
                  f"-- and the answer still read as 'only 0x01D9 writes it', "
                  f"which was wrong. When a subsystem's answer looks too "
                  f"small, re-run at disp-4 and disp+4 before believing it "
                  f"(studies/pvpui/FINDINGS.md 21.2)")]
        return searched, blind

    def _mem_row(self, ins, disp):
        """An `Access` when this instruction's memory operand is [reg + disp]."""
        for op in ins.operands:
            if op.type != capstone.x86.X86_OP_MEM or op.mem.disp != disp:
                continue
            # `lea` is decided by the mnemonic and not by the access flag. It
            # neither loads nor stores -- the whole instruction is the address
            # computation -- so calling it a read would claim an access this
            # scan has not seen.
            if ins.mnemonic == "lea":
                is_w, kind = False, "A"
            else:
                is_w = (bool(op.access & capstone.CS_AC_WRITE)
                        or ins.mnemonic in _FPU_STORES)
                kind = "W" if is_w else "R"
            return Access(ins.address, is_w,
                          ins.reg_name(op.mem.base) if op.mem.base else "-",
                          ins.reg_name(op.mem.index) if op.mem.index else "",
                          f"{ins.mnemonic} {ins.op_str}", ins.bytes.hex(), kind)
        return None

    def _arith_row(self, ins, disp, mnemonics):
        """An `Access` when this instruction computes `reg + disp` in place."""
        if ins.mnemonic not in mnemonics:
            return None
        ops = ins.operands
        if len(ops) != 2:
            return None
        dst, src = ops
        if (dst.type != capstone.x86.X86_OP_REG
                or src.type != capstone.x86.X86_OP_IMM):
            return None
        # Named in `address_forms`' blind list rather than left silent: a byte
        # or word register is not an address in 32-bit code, and `add al, 0xe`
        # at 0x00479BC8 is what a scan without this rule reports for `--field
        # 0xE --in ExeArchive`.
        if dst.size != 4:
            return None
        want = disp if ins.mnemonic == "add" else (-disp) & 0xFFFFFFFF
        if src.imm & 0xFFFFFFFF != want:
            return None
        return Access(ins.address, False, ins.reg_name(dst.reg), "",
                      f"{ins.mnemonic} {ins.op_str}", ins.bytes.hex(), "A")

    def field_access(self, disp, lo=None, hi=None):
        """Every instruction that accesses [reg + disp] OR computes its address.

        Returns a sorted list of `Access`, which is a tuple of
        (va, is_write, base_reg, index_reg, text, hexbytes, kind).

        SEARCHES EVERY ENCODING THE DISPLACEMENT CAN HAVE -- see
        `field_encodings` -- AND EVERY ARITHMETIC FORM THAT REACHES THE SAME
        ADDRESS -- see `address_forms`. Both are what `--field` prints alongside
        the count. Searching disp32 alone reported zero for `+0xE` in ExeArchive
        with a `mov byte [edi+0xe], al` sitting inside the range; searching
        memory operands alone reported 14 sites for `+0x6BC` with the writer at
        0x00813AD1 sitting outside them.

        ONE SWEEP, TWO ACCEPTANCE RULES. The bytes are the same either way --
        `8d 8f bc 06 00 00` carries 0x6BC as a displacement and `81 c1 bc 06 00
        00` carries it as an immediate -- so the arithmetic form costs no extra
        pass over the section, only an extra test per candidate decode. The
        `sub` spelling does cost a pass, because -disp is different bytes:
        MEASURED 2026-08-13, an unbounded `--field 0x14` goes from 7.5 s and
        19,125 rows to 14.4 s and 21,703, while `--field 0x6bc` stays under a
        tenth of a second and the `--in <module>` path that is the flagship
        stays in milliseconds. Paid, because `sub eax, -0x80` is not
        hypothetical -- 265 sites on this build.
        """
        out, seen = [], set()
        blob, tva = self.tdata, self.tva

        # One anchor per encoding: the constant's own bytes, as written. Keyed
        # by (bytes, width) so a displacement whose negation is itself -- 0 --
        # does not sweep `\x00` over 5 MB twice.
        anchors = {}

        def anchor(needle, width, mem=False, arith=()):
            was_mem, was_arith = anchors.get((needle, width), (False, ()))
            anchors[(needle, width)] = (was_mem or mem,
                                        tuple(set(was_arith) | set(arith)))

        anchor(struct.pack("<I", disp), 4, mem=True, arith=("add",))
        if 0 <= disp <= 0x7F:
            anchor(bytes([disp]), 1, mem=True, arith=("add",))
        # The subtraction spelling. `sub ecx, -0x6BC` lands on +0x6BC, and its
        # anchor is a different four bytes, so it is the one form here that is
        # not free.
        anchor(struct.pack("<I", (-disp) & 0xFFFFFFFF), 4, arith=("sub",))
        if -0x80 <= -disp <= 0x7F:
            anchor(struct.pack("<b", -disp), 1, arith=("sub",))

        # Restrict the sweep to the requested range when there is one. An
        # instruction inside [lo, hi] carries its displacement after its own
        # first byte, so the anchor cannot lie before `lo` nor more than one
        # instruction past `hi`. This is what keeps the one-byte disp8 anchor
        # -- which matches roughly every 256th byte of a 5 MB section -- cheap
        # on the `--in <module>` path that is the flagship entry point.
        blo = 0 if lo is None else max(0, lo - tva)
        bhi = len(blob) if hi is None else min(len(blob), hi - tva + 16)

        for (needle, width), (mem_ok, mnemonics) in anchors.items():
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
                    if ins is None or ins.address in seen:
                        continue
                    # EXACT, from capstone's own encoding record: this
                    # instruction's displacement -- or its immediate, for the
                    # arithmetic forms -- must BE the bytes we found, at the
                    # width we searched. No window, no proxy.
                    enc = ins.encoding
                    row = None
                    if (mem_ok and enc.disp_size == width
                            and start + enc.disp_offset == p):
                        row = self._mem_row(ins, disp)
                    elif (mnemonics and enc.imm_size == width
                            and start + enc.imm_offset == p):
                        row = self._arith_row(ins, disp, mnemonics)
                    if row is not None:
                        seen.add(ins.address)
                        out.append(row)
                p = blob.find(needle, p + 1, bhi)

        # Drop the prefix-shadow duplicate: same displacement, address one byte
        # after a real hit whose first byte is a legacy prefix.
        addrs = {r.va for r in out}
        out = [r for r in out
               if not (r.va - 1 in addrs
                       and self.read(r.va - 1, 1)[:1]
                       and self.read(r.va - 1, 1)[0] in _PREFIXES)]

        if lo is not None:
            out = [r for r in out if lo <= r.va <= hi]
        return sorted(out)

    # -- one bit of one field -------------------------------------------
    #
    # WHY THIS IS NOT `--field` WITH A FILTER, and it is the same lesson this
    # module already learned twice above. `--field 0x20` on build 38797 returns
    # thousands of rows, because +0x20 is a displacement every third structure
    # in the image happens to use; and the thing that distinguishes a bit-18
    # site from the rest is the IMMEDIATE, which `--field` never looks at.
    # Filtering `--field`'s rows for `0x40000` finds the dword spellings and
    # reports a confident zero for the rest, because:
    #
    #   **BIT 18 OF THE DWORD AT +0x20 IS ALSO BIT 2 OF THE BYTE AT +0x22.**
    #
    # MSVC narrows `flags |= 0x40000` to `or byte [esi+0x22], 4` and
    # `flags &= ~0x40000` to `and byte [esi+0x22], 0xFB` as a matter of routine.
    # Those instructions carry neither 0x20 nor 0x40000 anywhere in their bytes.
    # A sweep that does not DERIVE the narrowed views cannot see them, and it
    # will not say so -- it will return a short, clean, wrong list. That is the
    # exact failure shape of studies/enemy/PLAN.md §6o, of the disp8 hole, and
    # of the `add ecx, 0x6bc` hole, arriving for a fourth time by a new road.
    #
    # So `bit_access` enumerates every WIDTH the bit can be addressed at, and
    # every displacement each width implies, and sweeps them all -- and then
    # says which forms it searched and which it is blind to, the same way
    # `--field` and `--xrefs` do.

    # What an instruction does to the bits under test.
    #
    #   SET/CLEAR/TOGGLE  the bit is written
    #   TEST              the bit is read and nothing is written
    #   LOAD/STORE        the whole word moves; the bit goes with it, and what
    #                     happens to it happens somewhere else
    #   SHIFT             a bit-extraction idiom (`shr eax, 18`) -- a candidate
    #                     read whose target bit is implied by the shift count
    #   OTHER             carries the constant, does something else with it
    BitAccess = collections.namedtuple(
        "BitAccess", "va effect text hexbytes form width note")

    # Instructions whose immediate is a MASK over the destination.
    _MASK_OPS = ("test", "and", "or", "xor", "cmp")
    # Instructions whose immediate is a BIT INDEX into the destination.
    _BIT_OPS = {"bt": "TEST", "bts": "SET", "btr": "CLEAR", "btc": "TOGGLE"}
    # Instructions whose immediate is a SHIFT COUNT. Only two counts extract a
    # given bit and the count DEPENDS ON WHICH -- `shr eax, 18` brings bit 18
    # down to bit 0, and `shl eax, 13` drives it up to the sign bit for a `js`.
    # An earlier draft accepted any shift by the bit's index, which made every
    # `shl edx, 2` in the image a candidate read of bit 2; a multiply by four is
    # not a bit test, and three such rows were in the first run's output.
    _SHIFT_DOWN = ("shr", "sar")
    _SHIFT_UP = ("shl", "sal")

    @staticmethod
    def bit_views(disp, bit):
        """Every (width, displacement, mask, bit_index) that addresses this bit.

        THE POINT OF THE WHOLE FUNCTION. A bit in a dword field can be spelled
        at four widths, and three of them move the displacement:

            bit 18 of dword [esi+0x20]
              = bit  2 of byte  [esi+0x22]     (byte 2 of the dword)
              = bit  2 of word  [esi+0x22]     (word 1 of the dword)
              = bit 18 of dword [esi+0x20]

        Returned little-endian, which is what x86 is: byte `k` of the dword
        lives at `disp + k`, so the narrowed displacement is `disp + bit//8`
        for a byte view and `disp + 2*(bit//16)` for a word view.
        """
        views = []
        b_off = bit // 8
        views.append((1, disp + b_off, 1 << (bit % 8), bit % 8))
        w_off = 2 * (bit // 16)
        views.append((2, disp + w_off, 1 << (bit % 16), bit % 16))
        views.append((4, disp, 1 << bit, bit))
        return views

    def _anchored(self, needle, width, kind, lo=None, hi=None):
        """Decodes where capstone puts a `kind` field of `width` bytes on `needle`.

        The shared primitive under both halves of `bit_access`, and the same
        exactness rule `field_access` uses: a candidate decode is kept only when
        capstone's own encoding record puts the field we are anchoring on
        precisely at the bytes we found it at. `kind` is "disp" or "imm".
        """
        blob, tva = self.tdata, self.tva
        blo = 0 if lo is None else max(0, lo - tva)
        bhi = len(blob) if hi is None else min(len(blob), hi - tva + 16)
        seen = set()
        p = blob.find(needle, blo, bhi)
        while p != -1:
            for back in range(1, 12):
                start = p - back
                if start < 0:
                    continue
                ins = next(iter(self.md.disasm(blob[start:start + 24],
                                               tva + start, 1)), None)
                if ins is None or ins.address in seen:
                    continue
                enc = ins.encoding
                size = enc.disp_size if kind == "disp" else enc.imm_size
                off = enc.disp_offset if kind == "disp" else enc.imm_offset
                if size == width and start + off == p:
                    seen.add(ins.address)
                    yield ins
            p = blob.find(needle, p + 1, bhi)

    @staticmethod
    def _bit_effect(ins, mask, bit_index, width):
        """(effect, note) for what `ins` does to `mask` in an operand of `width`.

        `mask` is the bit's mask WITHIN this instruction's operand width -- 0x04
        for a byte view of bit 18, 0x40000 for the dword view. Everything below
        compares in that width, because `and eax, 0xFFFFFFFB` and
        `and al, 0xFB` are the same clear at two sizes and capstone reports
        their immediates differently (the first sign-extends an imm8).
        """
        full = (1 << (width * 8)) - 1
        m = ins.mnemonic
        ops = ins.operands
        imm = next((o.imm & full for o in ops
                    if o.type == capstone.x86.X86_OP_IMM), None)
        dst = ops[0] if ops else None
        dst_is_mem = dst is not None and dst.type == capstone.x86.X86_OP_MEM

        if m in Image._BIT_OPS and imm is not None:
            # `bt/bts/btr/btc r/m, imm8` -- the immediate is a bit NUMBER, and
            # the hardware masks it to the operand width.
            if (imm % (width * 8)) == bit_index:
                return Image._BIT_OPS[m], "bit-number form"
            return None, None

        if imm is not None and (m in Image._SHIFT_DOWN or m in Image._SHIFT_UP):
            if m in Image._SHIFT_DOWN and imm == bit_index:
                return "SHIFT", (f"shift right by {imm} brings bit {bit_index} "
                                 f"down to bit 0 -- the `(f >> {bit_index}) & 1` "
                                 f"idiom")
            if m in Image._SHIFT_UP and imm == (width * 8 - 1 - bit_index):
                return "SHIFT", (f"shift left by {imm} drives bit {bit_index} "
                                 f"into the sign bit of a {width * 8}-bit "
                                 f"operand -- the `if ((int)(f << {imm}) < 0)` "
                                 f"idiom, usually followed by `js`")
            return None, None

        if m in Image._MASK_OPS and imm is not None:
            # THE BIT MUST ACTUALLY BE IN THE MASK. The first run of this
            # scanner reported `test dword [edi+0x20], 0x10000` as a bit-18
            # site: it was found because it touches the right displacement, and
            # classified TEST because it is a `test` with an immediate. It
            # tests bit SIXTEEN. Every branch below now decides on `hits`, and
            # what does not cover the bit is reported as a NEIGHBOUR rather
            # than dropped -- a quiet filter is the defect this module exists
            # to stop making, and the neighbouring bits of a flags word are
            # exactly what tells you whether it is one field or several.
            hits = bool(imm & mask)
            others = (imm if m in ("or", "xor", "test", "cmp")
                      else (~imm) & full) & ~mask & full
            def neighbour(verb):
                bits = [i for i in range(width * 8) if others >> i & 1]
                which = (", ".join(str(b) for b in bits) if len(bits) <= 6
                         else f"{len(bits)} bits")
                return "NEIGHBOUR", (f"{verb} 0x{imm:X}: NOT bit {bit_index}. "
                                     f"Touches bit(s) {which} of the same field")
            if m == "or":
                return ("SET", "") if hits else neighbour("sets")
            if m == "xor":
                return ("TOGGLE", "") if hits else neighbour("toggles")
            if m == "and":
                # `and dst, m` CLEARS bit b when m's bit b is 0 and PRESERVES it
                # when it is 1. So a hit here means the instruction leaves our
                # bit alone -- the opposite of every other mnemonic in this
                # block, and the second bug the first run exposed
                # (`and [edi+0x20], 0xfffdffff` clears bit 17, preserves 18,
                # and was reported as a bit-18 TEST).
                if not hits:
                    return "CLEAR", ""
                if imm == mask:
                    # Isolating the bit. Into memory that is a destructive
                    # write of every other bit -- vanishingly rare and worth
                    # flagging rather than calling a read.
                    return ("OTHER" if dst_is_mem else "TEST",
                            "isolates the bit"
                            + (" -- and CLEARS every other bit of the field, "
                               "which is a write" if dst_is_mem else ""))
                return neighbour("clears the complement of")
            if m in ("test", "cmp"):
                if not hits:
                    return neighbour("tests")
                return "TEST", ("" if imm == mask
                                else f"masks 0x{imm:X}, which covers the bit")
            return None, None

        # No immediate relating to the bit: this is the whole word moving.
        if m.startswith("mov") or m in ("push", "lea"):
            if dst_is_mem:
                return "STORE", "the whole field is written; the bit goes with it"
            return "LOAD", ("the whole field is read into a register -- any "
                            "test of the bit happens at another instruction")
        return "OTHER", ""

    def bit_access(self, disp, bit, lo=None, hi=None):
        """Every instruction that reads or writes bit `bit` of the field at `disp`.

        Returns (rows, scope) where scope is (searched, blind), each a list of
        (name, detail) exactly like `field_encodings`.

        TWO SWEEPS, because the bit is reachable two ways and neither sweep can
        see the other's half:

          * **Memory sweep** -- anchored on the DISPLACEMENT of each view from
            `bit_views`, filtered to instructions whose memory operand really is
            that width. This finds `test dword [esi+0x20], 0x40000` and
            `or byte [esi+0x22], 4` alike, and it finds the `mov` that loads the
            field without touching the bit, which is the head of the second
            form.
          * **Immediate sweep** -- anchored on the MASK and its complement, at
            each width. This finds `test eax, 0x40000` and `and eax, 0xFFFBFFFF`
            operating on a register some earlier instruction loaded. Those rows
            are CANDIDATES, not sites: nothing here proves the register holds
            THIS field, and the caller must trace the load. They are reported in
            their own class and labelled, never merged into the memory rows.
        """
        rows, seen = [], set()

        # What sweep 2 is allowed to report. An instruction is only a CANDIDATE
        # bit site if it MANIPULATES the bit; carrying the constant is not
        # enough. `mov dl, 4` matched the 8-bit mask in the first run and was
        # classified LOAD, putting a byte-register initialisation in a list of
        # bit-18 accesses. The one exception is `mov r32, mask`, which is the
        # visible head of this scan's widest blind spot -- the mask about to be
        # held in a register, where the instruction that USES it carries no
        # constant at all -- so that one is kept and labelled as such.
        _SWEEP2_OK = ("SET", "CLEAR", "TOGGLE", "TEST", "SHIFT")

        def add(ins, form, width, mask, bit_index, klass, sweep=1):
            if ins.address in seen:
                return
            effect, note = Image._bit_effect(ins, mask, bit_index, width)
            if effect is None:
                return
            if sweep == 2 and effect not in _SWEEP2_OK:
                if not (effect == "LOAD" and width == 4
                        and ins.mnemonic.startswith("mov")):
                    return
                effect = "OTHER"
                note = ("the mask itself is materialised in a register here. "
                        "Whatever TESTS or WRITES the bit with it carries no "
                        "constant and is invisible to this scan -- this row is "
                        "the only trace of it")
            seen.add(ins.address)
            rows.append(Image.BitAccess(
                ins.address, effect, f"{ins.mnemonic} {ins.op_str}",
                ins.bytes.hex(), form, width,
                (note + (" " if note else "") + klass).strip()))

        views = Image.bit_views(disp, bit)

        # -- sweep 1: the field's own displacement, at each width -------
        for width, vdisp, mask, bidx in views:
            needles = [(struct.pack("<I", vdisp), 4)]
            if 0 <= vdisp <= 0x7F:
                needles.append((bytes([vdisp]), 1))
            for needle, nwidth in needles:
                for ins in self._anchored(needle, nwidth, "disp", lo, hi):
                    mem = next((o for o in ins.operands
                                if o.type == capstone.x86.X86_OP_MEM
                                and o.mem.disp == vdisp), None)
                    if mem is None or mem.size != width:
                        continue
                    add(ins, f"memory [reg+0x{vdisp:X}] as {width * 8}-bit",
                        width, mask, bidx, "")

        # -- sweep 2: the mask and its complement as an immediate -------
        for width, _vdisp, mask, bidx in views:
            full = (1 << (width * 8)) - 1
            for value in (mask, (~mask) & full):
                for nwidth in (1, 2, 4):
                    if value > (1 << (nwidth * 8)) - 1:
                        continue
                    needle = value.to_bytes(nwidth, "little")
                    for ins in self._anchored(needle, nwidth, "imm", lo, hi):
                        if any(o.type == capstone.x86.X86_OP_MEM
                               and o.mem.disp in (v[1] for v in views)
                               for o in ins.operands):
                            continue      # already a sweep-1 row
                        if not any(o.type == capstone.x86.X86_OP_REG
                                   and o.size == width for o in ins.operands):
                            continue
                        # TWO VERY DIFFERENT STRENGTHS OF CANDIDATE, and
                        # collapsing them is how a reader gets misled. At 32
                        # bits, `or eax, 0x40000` names bit 18 unambiguously
                        # and only the FIELD is open. At 8 bits, `test al, 4`
                        # names bit 2 of *some* byte: it is bit 18 of this
                        # field only if that byte came from +0x22, and after
                        # the far more common `mov eax, [esi+0x20]` the same
                        # instruction tests bit TWO. The first run of this
                        # scanner put three such rows next to the real site
                        # with the same label.
                        if width == 4:
                            warn = ("[CANDIDATE -- the BIT is certain, the "
                                    "FIELD is not: trace the register's load]")
                        else:
                            warn = (f"[WEAK CANDIDATE -- this is bit {bidx} of "
                                    f"an {width * 8}-bit register. It is bit "
                                    f"{bit} of THIS field only if that register "
                                    f"was loaded from +0x{disp + bit // 8:X}; "
                                    f"after a load of the whole field from "
                                    f"+0x{disp:X} it is bit {bidx}, a different "
                                    f"bit entirely]")
                        add(ins, f"immediate 0x{value:X} on a {width * 8}-bit "
                                 f"register", width, mask, bidx, warn, sweep=2)
            # The bit-number and shift-count forms carry an INDEX, not the mask,
            # and the index differs per form: `bt` and `shr` take the bit's own
            # number, `shl` takes the distance to the sign bit.
            counts = {bidx: "bit-number / shift-right count",
                      width * 8 - 1 - bidx: "shift-left-to-sign count"}
            for count, what in counts.items():
                if not 0 <= count <= 0xFF:
                    continue
                for ins in self._anchored(bytes([count]), 1, "imm", lo, hi):
                    if (ins.mnemonic in Image._BIT_OPS
                            or ins.mnemonic in Image._SHIFT_DOWN
                            or ins.mnemonic in Image._SHIFT_UP):
                        add(ins, f"{what} {count}, {width * 8}-bit view",
                            width, mask, bidx, "[CANDIDATE -- trace the operand]",
                            sweep=2)

        searched = [
            ("the field's own displacement at every width the bit has a view "
             "at", ", ".join(f"{w * 8}-bit [reg+0x{d:X}] mask 0x{m:X}"
                             for w, d, m, _ in views)),
            ("the mask and its complement as an immediate on a register",
             "finds `test eax, 0x40000` after a load -- reported as CANDIDATE, "
             "because nothing here proves the register holds this field"),
            ("the bit-number forms", "bt / bts / btr / btc with an imm8 equal "
                                     "to the bit's index in that view"),
            ("the shift-count forms", "shr / sar / shl / rol / ror by the "
                                      "bit's index -- the `(f >> 18) & 1` idiom"),
        ]
        blind = [
            ("the mask held in a register",
             f"`mov eax, 0x{1 << bit:X}` then `test ecx, eax` puts the constant "
             f"in a row above and the TEST nowhere. Nothing anchored can see it"),
            ("a mask covering the bit that is neither it nor its complement",
             "a compound test like `and eax, 0x60000` IS found (the mask covers "
             "the bit) only when its own bytes are swept -- which happens only "
             "if it equals the mask or the complement. A wider compound mask is "
             "NOT searched"),
            ("the field reached through a biased `this`",
             f"where the code holds a pointer to a subobject, the same bit is "
             f"spelled at a smaller displacement and 0x{disp:X} never appears. "
             f"Re-run at disp-4 and disp+4 when an answer looks too small "
             f"(studies/pvpui/FINDINGS.md 21.2)"),
            ("a displacement of zero",
             "mod=00 `[reg]` writes no displacement bytes, so a bit of the "
             "field at +0x0 has nothing to anchor on") if disp == 0 else None,
        ]
        return sorted(rows), (searched, [b for b in blind if b])

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
    ap.add_argument("--bit", metavar="DISP:N",
                    help="one BIT of one field, e.g. 0x20:18 -- every "
                         "instruction that sets, clears, tests or moves it, "
                         "including the narrowed byte/word spellings")
    ap.add_argument("--xrefs", help="VA: every call/jmp and data word to it")
    ap.add_argument("--dis", help="VA: disassemble from here")
    ap.add_argument("--upto", help="VA: disassemble the instructions ENDING "
                                   "at this VA, aligned onto it by search "
                                   "rather than by a guessed start")
    ap.add_argument("--phantoms", action="store_true",
                    help="--bit: keep rows whose VA is not on any nearby "
                         "instruction boundary. Off by default; the count of "
                         "what was dropped is printed either way.")
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
        dropped_addr = 0
        if a.writes:
            # `--writes` cannot answer "who writes this field" on its own and
            # says so. The store through a computed pointer is an `A` row here
            # and a `W` row at whatever displacement the callee uses -- which
            # is exactly the shape of GAME_SMSG 0x00B6's writer, `add ecx,
            # 0x6bc` at 0x00813AD1 storing at +0xC inside 0x0081FD00.
            dropped_addr = sum(1 for r in rows if r.kind == "A")
            rows = [r for r in rows if r.is_write]
        # Say WHERE we looked and HOW, always. "Nothing writes it" is only a
        # finding when the range is stated with it -- and only an honest one
        # when the encodings and the address forms searched are stated too,
        # because a scan that knew one encoding, and later a scan that knew
        # only memory operands, each reported a confident zero over a range
        # containing the instruction it was looking for.
        searched, blind = Image.field_encodings(disp)
        asearched, ablind = Image.address_forms(disp)
        kinds = collections.Counter(r.kind for r in rows)
        print(f"[reg + 0x{disp:X}] in {where}\n"
              f"{len(rows)} instruction(s)"
              + (" (stores only)" if a.writes else
                 f": {kinds['W']} store(s), {kinds['R']} read(s), "
                 f"{kinds['A']} address-taking"))
        for r in rows:
            print(f"  {r.va:08X}  {r.kind}  base={r.base:<4} "
                  f"{r.index:<4} {r.text:<40} {r.hexbytes}")
        if not rows:
            print("  -- none. That is a statement about the range and the "
                  "encodings and forms below, and nothing wider.")
        if dropped_addr:
            print(f"\n--writes dropped {dropped_addr} address-taking row(s). A "
                  f"store through a pointer computed there is NOT in the list "
                  f"above; drop --writes to see them.")
        # A row with no base register is `[0xdisp]`, an absolute address that
        # happens to equal the displacement -- not a struct field. Counted and
        # named rather than filtered out, because a quiet filter is the defect
        # this module was rewritten to stop making.
        noreg = sum(1 for r in rows if r.base == "-")
        if noreg:
            print(f"\n{noreg} of the above have no base register: those are "
                  f"absolute address 0x{disp:X}, not a field at +0x{disp:X}.")
        # Same rule, same reason, for the arithmetic rows: `add esp, 0x14` is a
        # stack frame being unwound and `add ebp, ...` is almost always the
        # same. On an unbounded `--field 0x14` that is 2,421 of the 2,579
        # address-taking rows, so a reader who is not told will read the count
        # as a field with two thousand users.
        stack = sum(1 for r in rows if r.kind == "A" and r.base in ("esp", "ebp"))
        if stack:
            print(f"\n{stack} of the address-taking rows target esp/ebp: those "
                  f"are stack-frame arithmetic, not a field at +0x{disp:X}.")
        print("\nmemory accesses -- encodings searched: "
              + ", ".join(f"{n} ({d})" for n, d in searched))
        for n, d in blind:
            print(f"NOT searched: {n} -- {d}")
        print("\naddress computations -- forms searched: "
              + ", ".join(f"{n} ({d})" for n, d in asearched))
        for n, d in ablind:
            print(f"NOT searched: {n} -- {d}")
        return 0

    if a.bit:
        if ":" not in a.bit:
            ap.error("--bit takes DISP:N, e.g. --bit 0x20:18")
        dpart, bpart = a.bit.split(":", 1)
        disp, bit = int(dpart, 0), int(bpart, 0)
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
        rows, (searched, blind) = img.bit_access(disp, bit, lo, hi)
        # The phantom pass. Rows found by a ONE-BYTE anchor can sit mid-
        # instruction (see `on_boundary`), and those are indistinguishable from
        # real sites in the listing. Dropped by default and COUNTED out loud --
        # never silently, which is this module's standing rule. Rows from a
        # four-byte anchor are left alone: a false four-byte alignment is rare
        # enough that paying a boundary search for every one of 11,504
        # image-wide rows is not worth the minutes.
        phantoms = []
        if not a.phantoms:
            keep = []
            for r in rows:
                narrow = len(r.hexbytes) // 2 <= 4
                if narrow and img.boundary_status(r.va) == "phantom":
                    phantoms.append(r)
                else:
                    keep.append(r)
            rows = keep
        views = Image.bit_views(disp, bit)
        print(f"bit {bit} (mask 0x{1 << bit:X}) of the field at +0x{disp:X}, "
              f"in {where}")
        print("the same bit, spelled at each width:")
        for w, d, m, bi in views:
            print(f"  {w * 8:2}-bit  [reg+0x{d:X}]  mask 0x{m:X}  "
                  f"(bit {bi} of that operand)")
        effects = collections.Counter(r.effect for r in rows)
        tally = ", ".join(f"{n} {e}" for e, n in sorted(effects.items()))
        print(f"\n{len(rows)} instruction(s)" + (f": {tally}" if rows else ""))
        # Grouped by what they DO, because the question `--bit` exists to answer
        # is "what sets this and what reads it", and a flat address-sorted list
        # buries a single SET among forty LOADs.
        for eff in ("SET", "CLEAR", "TOGGLE", "TEST", "SHIFT", "STORE",
                    "LOAD", "OTHER", "NEIGHBOUR"):
            group = [r for r in rows if r.effect == eff]
            if not group:
                continue
            print(f"\n{eff}  ({len(group)})")
            for r in group:
                print(f"  {r.va:08X}  {r.text:<38} {r.hexbytes:<20} "
                      f"{r.form}")
                if r.note:
                    print(f"            {r.note}")
        if not rows:
            print("  -- none. That is a statement about the range and the "
                  "forms below, and nothing wider.")
        if phantoms:
            print(f"\ndropped {len(phantoms)} row(s) whose VA is not on any "
                  f"instruction boundary within 64 bytes -- a one-byte anchor "
                  f"landing mid-instruction. `--phantoms` keeps them:")
            for r in phantoms:
                print(f"  {r.va:08X}  {r.text:<38} {r.hexbytes}")
        print("\nforms searched: ")
        for n, d in searched:
            print(f"  {n} -- {d}")
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

    if a.upto:
        va = int(a.upto, 0)
        stream = img.dis_upto(va, count=a.count)
        if not stream:
            print(f"0x{va:08X} is not on an instruction boundary in any decode "
                  f"starting within 96 bytes before it. That is the signature "
                  f"of a PHANTOM -- an anchor that landed inside a longer "
                  f"instruction.")
            return 0
        print(f"the {len(stream)} instruction(s) ending at 0x{va:08X}, aligned "
              f"by search from 0x{stream[0].address:08X}:")
        for ins in stream:
            mark = "->" if ins.address == va else "  "
            print(f"{mark} {ins.address:08X}  {ins.bytes.hex():<16} "
                  f"{ins.mnemonic} {ins.op_str}")
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

    ap.error("give --field, --bit, --xrefs, --dis, --upto or --bounds")


if __name__ == "__main__":
    sys.exit(main())
