"""Read the client's own assertions: file, line, and the expression as written.

    python toolkit/clientscan/asserts.py --file ChCliSkill        # one module
    python toolkit/clientscan/asserts.py --grep skillInstance     # by expression
    python toolkit/clientscan/asserts.py --modules                # what exists
    python toolkit/clientscan/asserts.py --at 0x004e6630 --span 3000

WHY THIS EXISTS. Everything else this project can read out of the client is
shapes: how many bytes, what width, which offset. Shapes do not say what a field
MEANS, and meaning is exactly what the reconstructions disagree about. ArenaNet
compiled its assert expressions into the shipping image as ASCII, and those
expressions are written in ArenaNet's own identifiers -- `skill->skillId`,
`hotKey < arrsize(hotKeyState->hotKey)`, `m_trapezoid->portalLeft <
pathMap.portalCount`. That is the closest thing to source code that exists
outside ArenaNet, and it has now settled three questions in this repository that
data-side reasoning could not.

WHAT AN ASSERT LOOKS LIKE. MSVC compiled every one of them to the same four
instructions, in the same order, with the operands in registers:

    push  <line>            6A ll                 or  68 ll ll ll ll
    mov   edx, <file>       BA <va of "P:\\Code\\...">
    mov   ecx, <expr>       B9 <va of "skill->skillId != 0">
    call  <assert>          E8 <rel32>

So a scan for `BA imm32 / B9 imm32 / E8 rel32` where the edx string starts with
`P:\\Code\\` finds them all with no disassembler. MEASURED on build 38797: 19,618
sites, and every single one calls the same routine at VA 0x00487bc0. That
unanimity is the check -- a byte pattern this short would otherwise be expected
to collide with unrelated code, and 19618/19618 agreeing on one callee says the
matches are real. The tool asserts it, so a future build that changes the idiom
fails loudly instead of returning a thinner list that still looks plausible.

WHAT IT CANNOT TELL YOU. An assert names an identifier; it does not define it.
`skill->recharge` proves a member of that name is read at that line -- not what
units it is in, and not that the member at any particular offset is the one being
named. Claims built on this are SOURCED (the client's own words) or INFERRED
(our reading of them), never OBSERVED.

READ ONLY. Opens the exe for reading. Standard library only -- no capstone, no
pefile -- because the byte pattern is fixed and this is the tool you want working
on a bare machine.
"""

import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwpe import PE                                          # noqa: E402

DEFAULT_EXE = r"C:\gw\Gw.exe"

# The one routine every assert site on build 38797 calls. Not used to FIND the
# sites -- used to check that what we found is what we think it is.
ASSERT_VA_38797 = 0x00487BC0


class Assert:
    __slots__ = ("va", "file", "line", "expr", "callee")

    def __init__(self, va, file, line, expr, callee):
        self.va, self.file, self.line = va, file, line
        self.expr, self.callee = expr, callee

    @property
    def module(self):
        """Basename without extension: ChCliSkill, AgMsg, PathDir."""
        return self.file.rsplit("\\", 1)[-1].rsplit(".", 1)[0]

    def __repr__(self):
        line = self.line if self.line is not None else "?"
        return f"{self.module}:{line}  {self.expr}"


class Asserts:
    """Every assert in the image, indexed by module and by call site."""

    def __init__(self, path=DEFAULT_EXE):
        self.pe = PE(path)
        self.base = self.pe.image_base
        self.items = list(self._scan())
        self.items.sort(key=lambda a: a.va)
        self._by_va = [a.va for a in self.items]

    # -- string reading -------------------------------------------------
    def cstr(self, va, cap=400):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            return None
        blob = self.pe.data[off:off + cap]
        z = blob.find(b"\0")
        if z < 0:
            return None
        blob = blob[:z]
        if not blob or not all(32 <= c < 127 for c in blob):
            return None
        return blob.decode("ascii")

    # -- the scan -------------------------------------------------------
    def _scan(self):
        sec = self.pe.section(".text")
        if sec is None:
            raise ValueError("no .text section")
        data = self.pe.data
        lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
        i = lo
        while True:
            i = data.find(b"\xba", i, hi)
            if i == -1:
                return
            if i + 15 <= hi and data[i + 5] == 0xB9 and data[i + 10] == 0xE8:
                fva = struct.unpack_from("<I", data, i + 1)[0]
                eva = struct.unpack_from("<I", data, i + 6)[0]
                fname = self.cstr(fva)
                if fname and fname.startswith("P:\\"):
                    expr = self.cstr(eva)
                    if expr is not None:
                        rel = struct.unpack_from("<i", data, i + 11)[0]
                        va = self.pe.off_to_rva(i) + self.base
                        yield Assert(va, fname, self._line_before(data, i),
                                     expr, va + 15 + rel)
            i += 1

    @staticmethod
    def _line_before(data, i):
        """The `push <line>` that MSVC emits just ahead of the two movs.

        Returned as None rather than guessed when the byte before is not a
        push: some sites reuse a register or hoist the push, and a wrong line
        number is worse than no line number when the point of this tool is to
        quote the client accurately.
        """
        if i >= 2 and data[i - 2] == 0x6A:
            return data[i - 1]
        if i >= 5 and data[i - 5] == 0x68:
            return struct.unpack_from("<I", data, i - 4)[0]
        return None

    # -- queries --------------------------------------------------------
    def check(self, expect_callee=ASSERT_VA_38797):
        """(n_sites, n_distinct_callees, agreed). See the docstring."""
        callees = {a.callee for a in self.items}
        return len(self.items), len(callees), callees == {expect_callee}

    def modules(self):
        out = {}
        for a in self.items:
            out.setdefault(a.module, []).append(a)
        return out

    def by_module(self, name):
        name = name.lower()
        return [a for a in self.items
                if name in a.module.lower() or name in a.file.lower()]

    def grep(self, pattern):
        rx = re.compile(pattern, re.I)
        return [a for a in self.items if rx.search(a.expr)]

    def direct_callers(self, target):
        """Every `call rel32` in .text that lands on `target`.

        Lives here because it is the question you ask immediately after an
        assert names something: who reaches this code? It is at its most
        useful in the negative -- opcode 211's write path has exactly ONE
        caller, its own message handler, which is how we know nothing else
        fills the array it writes. Direct calls only; an indirect call through
        a vtable or function-pointer table will not appear, so an empty result
        is "no direct caller", not "no caller".
        """
        sec = self.pe.section(".text")
        if sec is None:
            return []
        lo, size = sec["rawptr"], sec["rawsize"]
        blob = self.pe.data[lo:lo + size]
        base = self.base + sec["vaddr"]
        out = []
        for i in range(len(blob) - 5):
            if blob[i] == 0xE8:
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                va = base + i
                if va + 5 + rel == target:
                    out.append(va)
        return out

    def near(self, va, span=2000):
        """Asserts whose call site lies in [va, va+span).

        The cheapest way to ask "what does this function think it is doing":
        an assert inside it names the file it was compiled from and usually a
        member of the struct it is walking.
        """
        import bisect
        lo = bisect.bisect_left(self._by_va, va)
        hi = bisect.bisect_left(self._by_va, va + span)
        return self.items[lo:hi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--file", help="module substring, e.g. ChCliSkill")
    ap.add_argument("--grep", help="regex over the assert expression")
    ap.add_argument("--at", help="VA; show asserts inside the function there")
    ap.add_argument("--span", type=lambda s: int(s, 0), default=2000)
    ap.add_argument("--modules", action="store_true",
                    help="every source module that asserts, by count")
    ap.add_argument("--callers", help="VA; every direct call site")
    ap.add_argument("--unique", action="store_true",
                    help="collapse repeated expressions")
    a = ap.parse_args()

    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    az = Asserts(a.exe)
    n, ncallee, agreed = az.check()
    print(f"{a.exe}: {n} assert sites, {ncallee} distinct callee(s), "
          f"single-routine={agreed}")
    if not agreed:
        print("  WARNING: the idiom moved on this build; treat results as partial")

    if a.modules:
        mods = az.modules()
        for m in sorted(mods, key=lambda k: -len(mods[k])):
            print(f"{len(mods[m]):5}  {mods[m][0].file}")
        return 0

    if a.callers:
        target = int(a.callers, 0)
        sites = az.direct_callers(target)
        print(f"{len(sites)} direct caller(s) of 0x{target:08x}")
        for s in sites:
            ctx = az.near(s - 3000, 3000)
            where = f"  (nearest earlier assert: {ctx[-1]})" if ctx else ""
            print(f"  0x{s:08x}{where}")
        return 0

    if a.at is not None:
        hits = az.near(int(a.at, 0), a.span)
    elif a.file:
        hits = az.by_module(a.file)
    elif a.grep:
        hits = az.grep(a.grep)
    else:
        ap.error("give --file, --grep, --at or --modules")

    seen = set()
    for h in sorted(hits, key=lambda x: (x.file, x.line or 0, x.va)):
        if a.unique:
            k = (h.file, h.expr)
            if k in seen:
                continue
            seen.add(k)
        ln = f"{h.line}" if h.line is not None else "?"
        print(f"0x{h.va:08x}  {h.module}:{ln:<6} {h.expr}")
    print(f"\n{len(hits)} site(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
