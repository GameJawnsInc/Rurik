"""Which AgentView event each agent property queues, and of what kind.

    python toolkit/clientscan/avevents.py --exe <pinned exe>
    python toolkit/clientscan/avevents.py --exe <pinned exe> --id 60
    python toolkit/clientscan/avevents.py --exe <pinned exe> --census

WHY THIS EXISTS. `genericvalue.py` next door recovers which of the client's
seven switches acts on a property id. That says a property is handled; it does
not say what handling it DOES. For the whole cast and effect family the answer
is one step further on: the case body calls into `AvApi.cpp`, which resolves an
AgentView character and calls a method on it, which allocates an event, stamps
a KIND into its first dword and links it onto a list for the renderer to drain.

The kind is the second, independent grouping `studies/skillcast` §15.4 asked
for. The property ids are ArenaNet's *wire* vocabulary and the reconstructions
disagree about them; the event kinds are ArenaNet's *internal* vocabulary and no
reconstruction has them at all. Where the two groupings agree, a naming is
corroborated from a direction no catalogue can reach. They do agree, and
tightly: the three properties every lineage calls "attack started / finished /
stopped" come out as event kinds 0x03 / 0x00 / 0x02, and the attack-SKILL and
SKILL families repeat the shape at 0x15 / 0x11 / 0x13 and 0x19 / 0x16 / 0x17.

TWO ALLOCATORS, AND WHY THEY ARE CALLED WHAT THEY ARE. Their id spaces are
separate, so "kind 3" is ambiguous until you say which queue:

    0x007F2E90   payload written from +0x30 up.  ACTION.
    0x007F5340   payload written from +0x1C up.  EFFECT.

Those two names are INFERRED, not quoted, and the inference is worth stating so
it can be attacked. Neither allocator contains an assert. The function that
begins at the next byte after 0x007F2E90's `ret` asserts
`action->queueLink.IsLinked()` (AvChar:1243) and
`action->sequenceLink.IsLinked()` (AvChar:1251); the function that ends just
before 0x007F5340 asserts `effect->effectLink.IsLinked()` (AvChar:2433) and
`effect->queueLink.IsLinked()` (AvChar:2438). Adjacency alone would be thin.
What makes it more than that: each of those assert pairs names exactly TWO
links, and each allocator, in its own code, links its fresh record onto exactly
TWO intrusive lists. `AvChar:2646-2648` names three of them outright --
`m_actionQueue`, `m_actionSidelineQueue`, `m_triggerList`.

Both allocators write the kind to event+0x00 and the subsystem's counter at
+0x2C to event+4.

HOW IT WORKS, AND WHAT IT REFUSES TO DO. Everything here is derived from bytes;
nothing about the mapping is hardcoded. Two walks, both bounded:

  * BACKWARD, from an allocator call site, for the `push <kind>` that supplies
    its argument. MSVC often puts an instruction or two between the two, so a
    candidate push is accepted only when a length walk forward from it lands
    EXACTLY on the call. Two of the 44 sites have their push hoisted above a
    branch; they come back as None and print as `?` rather than being guessed
    at from the nearest number.
  * FORWARD, from a property's case body, following direct `call`/`jmp` targets
    to a bounded depth to find the function that allocates. A target is only
    followed when it looks like a function entry, and the whole walk stops dead
    on any opcode the length table does not know -- a wrong length would
    desynchronise the stream and produce confident nonsense, which is the exact
    failure `msgshape.py` documents from the other direction.

The refutable check is `--census`: every call site of both allocators must
resolve to a kind, and each property must resolve to at most ONE kind. A stray
`E8` byte misread as a call would show up as a second path with a second kind.

WHAT THIS DOES NOT SEE, stated because it changes an answer. The forward walk
follows straight-line code and unconditional jumps; it does not take the taken
side of a conditional branch. Property 22 is the case that matters: its body
tries `charContext + 0x55C`, `+0x560`, `+0x558` and finally `+0x550`/`+0x554`
in that order, calling a DIFFERENT AvApi entry point for whichever is set
first, so it can queue action kind 0x07, 0x08, 0x06 or 0x05. This tool reports
0x07, the fall-through. Read 0x00812B90 with `msghandler.py` before treating a
single kind here as the whole story for a branching case body.

STANDARD LIBRARY ONLY. The length table below covers what these particular
functions use and nothing more; it is not a disassembler and does not pretend
to be one. `msghandler.py` (capstone) is the tool for reading code.

READ ONLY. Opens the exe for reading and nothing else.
"""

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

from gwpe import PE                                            # noqa: E402
import genericvalue as GV                                      # noqa: E402

DEFAULT_EXE = r"C:\gw\Gw.exe"

# Build 38797. MEASURED: the two AgentView event allocators. See the docstring
# for the asserts that name what each one allocates.
ACTION = 0x007F2E90
EFFECT = 0x007F5340
ALLOCATORS = {ACTION: "action", EFFECT: "effect"}

# How far each walk is allowed to run. The functions involved are tiny -- the
# largest AvApi entry point on this build is under 0x60 bytes -- so a bound this
# tight is a check in itself: a walk that needs more than this has desynced.
BACK_WINDOW = 24
FUNC_WINDOW = 160
MAX_DEPTH = 6

# Opcodes whose length is (1 + modrm + sib + disp), with no immediate. Enough
# for the register moves, address computations and x87 loads that sit between a
# push and its call, plus the compares and tests in the entry points. 0xD8..0xDF
# is the whole x87 escape range: every one of them is ModRM-encoded, including
# the register forms like `fldz` (D9 EE) and `fnstsw ax` (DF E0), which the
# mod == 3 branch below sizes correctly.
MODRM_NOIMM = {0x01, 0x03, 0x29, 0x2B, 0x31, 0x33, 0x39, 0x3B, 0x85, 0x88,
               0x89, 0x8A, 0x8B, 0x8D, 0x8F,
               0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF}
# Same, plus a trailing imm8 / imm32.
MODRM_IMM8 = {0x6B, 0x83, 0xC0, 0xC1, 0xC6}
MODRM_IMM32 = {0x69, 0x81, 0xC7}
# ModRM opcodes reached through the 0x0F escape (movzx/movsx/setcc).
MODRM_0F = {0xB6, 0xB7, 0xBE, 0xBF}
# Fixed lengths, opcode included.
FIXED = {0x90: 1, 0x98: 1, 0x99: 1, 0xC3: 1, 0xC9: 1, 0xCC: 1,
         0x6A: 2, 0xA8: 2, 0xEB: 2, 0xC2: 3,
         0x05: 5, 0x25: 5, 0x2D: 5, 0x3D: 5, 0xA1: 5, 0xA3: 5, 0xA9: 5,
         0x68: 5, 0xE8: 5, 0xE9: 5}
for _b in range(0x40, 0x60):                                   # inc/dec/push/pop
    FIXED[_b] = 1
for _b in range(0xB8, 0xC0):                                   # mov r32, imm32
    FIXED[_b] = 5
for _b in range(0x70, 0x80):                                   # jcc rel8
    FIXED[_b] = 2


def _modrm_extra(data, i):
    """Bytes after the ModRM byte at data[i]: sib + displacement."""
    modrm = data[i]
    mod, rm = modrm >> 6, modrm & 7
    if mod == 3:
        return 1
    sib = 1 if rm == 4 else 0
    if mod == 1:
        return 1 + sib + 1
    if mod == 2:
        return 1 + sib + 4
    if rm == 5:                                                # disp32, no base
        return 1 + 4
    if sib and (data[i + 1] & 7) == 5:                         # SIB with no base
        return 1 + sib + 4
    return 1 + sib


def insn_len(data, i):
    """Length of the instruction at data[i], or None if the table has no rule.

    None is the whole point: it stops the walk instead of advancing by a wrong
    amount and disassembling the middle of an immediate as an opcode.
    """
    op = data[i]
    if op == 0x66 or op == 0xF2 or op == 0xF3:                 # prefix
        n = insn_len(data, i + 1)
        return None if n is None else n + 1
    if op == 0x0F:
        if data[i + 1] in MODRM_0F:
            return 2 + _modrm_extra(data, i + 2)
        if 0x80 <= data[i + 1] <= 0x8F:                        # jcc rel32
            return 6
        return None
    if op in FIXED:
        return FIXED[op]
    if op in MODRM_NOIMM:
        return 1 + _modrm_extra(data, i + 1)
    if op in MODRM_IMM8:
        return 1 + _modrm_extra(data, i + 1) + 1
    if op in MODRM_IMM32:
        return 1 + _modrm_extra(data, i + 1) + 4
    if op == 0xFF:                                             # group 5
        return 1 + _modrm_extra(data, i + 1)
    if op in (0xF6, 0xF7):                                     # group 3
        # /0 and /1 are `test rm, imm`; /2../7 (not/neg/mul/div) take none.
        n = 1 + _modrm_extra(data, i + 1)
        if (data[i + 1] >> 3) & 7 in (0, 1):
            n += 1 if op == 0xF6 else 4
        return n
    return None


class Image:
    def __init__(self, path=DEFAULT_EXE):
        self.path = path
        self.pe = PE(path)
        self.base = self.pe.image_base
        sec = self.pe.section(".text")
        if sec is None:
            raise ValueError("no .text section")
        self.tlo = self.base + sec["vaddr"]
        self.raw = sec["rawptr"]
        self.size = sec["rawsize"]
        self.text = self.pe.data[self.raw:self.raw + self.size]

    def off(self, va):
        """Offset into self.text, or None if the VA is outside .text."""
        i = va - self.tlo
        return i if 0 <= i < self.size else None

    def call_sites(self, target):
        """Every `call rel32` in .text landing on target. Same rule as asserts.py."""
        out = []
        for i in range(len(self.text) - 5):
            if self.text[i] == 0xE8:
                rel = struct.unpack_from("<i", self.text, i + 1)[0]
                if self.tlo + i + 5 + rel == target:
                    out.append(self.tlo + i)
        return out

    # -- the two walks ---------------------------------------------------
    def kind_at(self, site):
        """The `push <kind>` that feeds the allocator call at `site`, or None."""
        i = self.off(site)
        if i is None:
            return None
        for back in range(2, BACK_WINDOW + 1):
            p = i - back
            if p < 0:
                continue
            if self.text[p] == 0x6A:
                val, plen = self.text[p + 1], 2
            elif self.text[p] == 0x68:
                val, plen = struct.unpack_from("<I", self.text, p + 1)[0], 5
            else:
                continue
            q = p + plen
            while q < i:                                       # must land exactly
                n = insn_len(self.text, q)
                if n is None:
                    break
                q += n
            if q == i:
                return val
        return None

    def is_entry(self, va):
        """Does `va` look like a function ArenaNet's compiler emitted?

        Every AvApi entry point and AvChar method on this build starts with one
        of a handful of prologues. Requiring one is what keeps a stray 0xE8
        inside somebody's immediate from being followed as a call.
        """
        i = self.off(va)
        if i is None:
            return False
        b = self.text[i:i + 3]
        return (b[:3] == b"\x55\x8b\xec"                       # push ebp; mov ebp,esp
                or b[:1] in (b"\x53", b"\x56", b"\x57")        # push ebx/esi/edi
                or b[:1] == b"\x6a")                           # push imm8

    def walk(self, va, window=FUNC_WINDOW):
        """(targets, allocations) for the function at va.

        targets     direct call/jmp destinations, in order
        allocations [(which, kind, site)] for calls to either allocator
        """
        i = self.off(va)
        targets, allocs = [], []
        if i is None:
            return targets, allocs
        # -16 so the length decoder can always read a full ModRM + SIB + disp32
        # without running off the end of the section.
        end = min(i + window, len(self.text) - 16)
        while i < end:
            op = self.text[i]
            n = insn_len(self.text, i)
            if n is None:
                break
            if op in (0xE8, 0xE9):
                rel = struct.unpack_from("<i", self.text, i + 1)[0]
                tgt = self.tlo + i + 5 + rel
                if tgt in ALLOCATORS:
                    allocs.append((ALLOCATORS[tgt], self.kind_at(self.tlo + i),
                                   self.tlo + i))
                elif tgt not in targets and self.is_entry(tgt):
                    targets.append(tgt)
                if op == 0xE9:
                    break                                      # tail call
            # An unconditional short jump ENDS the straight-line walk. Skipping
            # over one instead is how the first draft of this file read property
            # 56 as property 61: 56's whole case body is `push 1; jmp <56's real
            # body>`, and stepping past the jmp fell into 61's case, which sits
            # at the very next byte and allocates a different event kind. The
            # answer was wrong, plausible, and silent -- the same trap §10 of the
            # study documents from the descriptor side.
            if op == 0xEB:
                tgt = self.tlo + i + 2 + struct.unpack_from("<b", self.text,
                                                            i + 1)[0]
                if tgt not in targets:
                    targets.append(tgt)
                break
            if op in (0xC3, 0xC2, 0xCC):
                break
            i += n
        return targets, allocs

    def chase(self, va, depth=MAX_DEPTH, seen=None, path=None):
        """[(path, allocations)] for every allocation reachable from va."""
        seen = set() if seen is None else seen
        path = path or [va]
        if va in seen or depth < 0:
            return []
        seen.add(va)
        targets, allocs = self.walk(va)
        if allocs:
            return [(path, allocs)]
        out = []
        for t in targets:
            out += self.chase(t, depth - 1, seen, path + [t])
        return out


def census(img):
    """{allocator name: {kind: [sites]}} plus the sites that would not resolve."""
    kinds, unresolved = {}, []
    for target, name in ALLOCATORS.items():
        kinds[name] = {}
        for s in img.call_sites(target):
            k = img.kind_at(s)
            if k is None:
                unresolved.append((name, s))
            else:
                kinds[name].setdefault(k, []).append(s)
    return kinds, unresolved


def by_property(img):
    """id -> [(which, kind, path)] for every property that queues an event.

    The switch tables come from `genericvalue.py` reading the SAME file -- not
    a default path. Reading the property tables out of one build and the event
    kinds out of another would produce a map that looks entirely reasonable.
    """
    table = GV.classify(GV.Image(img.path))
    out = {}
    for i in sorted(table):
        _, body = table[i]
        if body is None:
            continue
        hits = []
        for path, allocs in img.chase(body):
            for which, kind, _site in allocs:
                hits.append((which, kind, path))
        if hits:
            out[i] = hits
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--id", type=lambda s: int(s, 0), help="one property id")
    ap.add_argument("--census", action="store_true",
                    help="every allocator call site and the kind it pushes")
    a = ap.parse_args()
    if not os.path.exists(a.exe):
        sys.exit(f"no such file: {a.exe}")
    img = Image(a.exe)

    if a.census:
        kinds, unresolved = census(img)
        for name, ks in kinds.items():
            n = sum(len(v) for v in ks.values())
            bad = sum(1 for w, _ in unresolved if w == name)
            print(f"{name} allocator: {n + bad} call sites, {n} resolved, "
                  f"{len(ks)} distinct kinds")
            for k in sorted(ks):
                print(f"   0x{k:02x}  " + " ".join(f"0x{s:08x}" for s in ks[k]))
        print(f"\n{len(unresolved)} site(s) whose push could not be resolved "
              f"(reported, never guessed):")
        for name, s in unresolved:
            print(f"   {name} 0x{s:08x}")
        clash = {i: {k for _w, k, _p in h}
                 for i, h in by_property(img).items()}
        clash = {i: v for i, v in clash.items() if len(v) > 1}
        print(f"\nproperties resolving to more than one kind: "
              f"{ {i: sorted(v) for i, v in clash.items()} or 'none'}")
        return 0

    props = by_property(img)
    if a.id is not None:
        hits = props.get(a.id)
        if not hits:
            print(f"property {a.id} queues no AgentView event")
            return 0
        for which, kind, path in hits:
            ks = "?" if kind is None else f"0x{kind:02x}"
            print(f"property {a.id}: {which} event kind {ks}")
            print("   " + " -> ".join(f"0x{v:08x}" for v in path))
        return 0

    print(f"{len(props)} of the 67 property ids queue an AgentView event\n")
    print(f"  {'id':>3}  {'queue':<7} {'kind':<5} {'chain':<36} name")
    for i in sorted(props):
        for which, kind, path in props[i]:
            ks = "?" if kind is None else f"0x{kind:02x}"
            chain = " -> ".join(f"0x{v:06x}" for v in path[1:])
            name = GV.GWCA.get(i) or GV.OPENTYRIA.get(i, "")
            print(f"  {i:3}  {which:<7} {ks:<5} {chain:<36} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
