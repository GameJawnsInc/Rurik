"""Which frame ids does a handler body PUBLISH, and which module subscribes?

WHY THIS EXISTS. The client's UI does not read the wire. A message handler in
`ChCliApi.cpp` writes the store and then posts a numbered FRAME to a bus; UI
modules subscribe to ids and repaint. So the question "what does opcode X
actually DO on screen" has a static answer -- follow the id -- and that answer is
the strongest evidence available for NAMING an opcode without a client run.

`studies/quests/FINDINGS.md` used it twice and both times by hand. §1.6 scanned
`.text` for `push imm32` of an id in the quest band and tabulated PUBLISHER VAs;
§2.1 tabulated HANDLER BODY VAs from the dispatch block. Nobody joined the two
per opcode, so the frame-bus argument sat one arithmetic step away from being
usable for eleven opcodes, and §7.6 concluded "Nothing static will substitute"
about a question the join answers. This module is that step, committed, so the
`why` text in `schema/overrides.json` is reproducible by RUNNING rather than by
rewriting a scratch script -- which is the debt §7.9 names in its own words.

    python toolkit/clientscan/framebus.py                  # the quest family
    python toolkit/clientscan/framebus.py --at 0x0080F670 --end 0x0080F6F0
    python toolkit/clientscan/framebus.py --band 0x10000140 0x10000180

TWO SCAN-WINDOW LESSONS, both paid for, both encoded in `CALL_WINDOW` below.
The push and the call that consumes it are not adjacent: the body stages the
frame payload in between. §1.6's own scan used a 6-byte window and missed two
sites outright; a 24-byte window missed `0x0050`'s, whose call sits at +29
behind three `mov [ebp-x], imm32` -- one of them `0x378` == 888, the "no marker"
map id. A window too small does not error, it returns a confident short list,
which is the same failure shape as a stale worktree returning a confident number.

WHAT THIS DOES NOT DO. It reads `push imm32` / `call rel32` and nothing else, so
an id loaded into a register, or posted through an indirect call, is invisible to
it. Treat a NEGATIVE ("this body posts nothing") as "nothing in the direct form",
which is how `0x004A` and `0x004B` are recorded. Standard library only -- no
disassembler -- because `CLAUDE.md`'s carve-out (1) is scoped to two named files
and this is not one of them.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import pinned    # noqa: E402
import srctree   # noqa: E402

# The two bus helpers, MEASURED on build 38797. `studies/quests/FINDINGS.md` §1.6
# records a refuted reading here worth keeping: a lane reported two subscribe
# helpers, `0x00637BD0` for the quest UI and `0x00633BD0` for GmQuestComplete.
# The bytes it quoted were right and the arithmetic was not -- every call target
# in the band resolves to `0x00633BD0`, and the only difference is the argument
# form (`[reg+4]` vs `[reg]`), which is a frame-pointer offset and not a second API.
POST = 0x00633D70
SUBSCRIBE = 0x00633BD0

# Read the docstring before shrinking this.
CALL_WINDOW = 48

# The quest bus, MEASURED: every id in 0x1000014C..0x1000015F is published from
# inside ChCliApi's VA range, and 0x10000160 is published five times from
# MsCliTourn, so the upper edge is a real boundary rather than a round number.
QUEST_BAND = (0x1000014C, 0x10000160)

# `studies/quests/FINDINGS.md` §2.1's handler bodies, sorted by VA so each body's
# extent is [va, next va). 0x0054 is last and gets a bounded tail rather than an
# open one -- its own publisher sits at 0x0080FA12, 0x82 in.
QUEST_BODIES = [
    (0x0080F0A0, 0x0049), (0x0080F250, 0x004A), (0x0080F270, 0x004B),
    (0x0080F290, 0x004C), (0x0080F3C0, 0x004D), (0x0080F470, 0x0050),
    (0x0080F670, 0x004E), (0x0080F6F0, 0x0051), (0x0080F7A0, 0x0052),
    (0x0080F8E0, 0x0053), (0x0080F990, 0x0054),
]
QUEST_TAIL = 0x100

# What the join says, so a caller can assert on it. This is the PREDICTION that
# was stated before the bytes were read (probes.py's rule) and then held 11 of 11.
# The part a coincidence does not produce is the two SHARED ids: the two adds
# agree with each other and the two text-fills agree with each other, while the
# three marker ops -- which share one payload layout -- do not.
QUEST_EXPECTED = {
    0x0049: [0x1000014E], 0x0050: [0x1000014E],     # both add a quest
    0x004C: [0x1000014F], 0x0054: [0x1000014F],     # both fill log text
    0x004D: [0x10000154], 0x0051: [0x10000151], 0x0053: [0x10000153],
    0x0052: [0x10000152], 0x004E: [0x10000155],     # GmQuestComplete's band
    0x004A: [], 0x004B: [],                          # measured negatives
}

# Who listens, from §1.6's subscribe-side scan. Prose for the reader; the module
# asserts nothing about it.
SUBSCRIBERS = {
    0x1000014E: "QuestLog, QuestTaskTracker, GmView, GmHelpGuide, Compass, UiCtlInstance",
    0x1000014F: "QuestChallenge, QuestTaskTracker",
    0x10000150: "QuestTaskTracker, GmMapCtlLocationTag, Compass",
    0x10000151: "QuestTaskTracker, Compass",
    0x10000152: "QuestLog, QuestTaskTracker, GmHelpGuide, GmMapCtlLocationTag, Compass",
    0x10000153: "QuestLog, QuestTaskTracker, GmMapCtlLocationTag, Compass",
    0x10000154: "QuestChallenge, QuestTaskTracker, Compass",
    0x10000155: "GmQuestComplete, GmView, QuestTaskTracker",
}


class Image:
    """A PE opened for VA reads. Stdlib section walk, no dependency."""

    def __init__(self, path=None):
        self.path = path or srctree.default_exe()
        self.blob = open(self.path, "rb").read()
        self.pinned = len(self.blob) == pinned.SIZE
        e = struct.unpack_from("<I", self.blob, 0x3C)[0]
        nsec = struct.unpack_from("<H", self.blob, e + 6)[0]
        opt = struct.unpack_from("<H", self.blob, e + 20)[0]
        base = struct.unpack_from("<I", self.blob, e + 52)[0]
        self.sections = []
        for i in range(nsec):
            _n, vsize, va, rsize, roff = struct.unpack_from(
                "<8sIIII", self.blob, e + 24 + opt + i * 40)
            self.sections.append((base + va, max(vsize, rsize), roff))

    def offset(self, va):
        for sva, size, roff in self.sections:
            if sva <= va < sva + size:
                return roff + (va - sva)
        raise ValueError(f"VA {va:#010x} is in no section of {self.path}")


def publishes(img, lo, hi, band=QUEST_BAND):
    """Every `push imm32` in [lo, hi) whose imm is in `band`, with its call.

    Returns (frame_id, kind, push_va, call_va) where kind is 'post',
    'subscribe', 'none' (no call inside the window) or a raw target string. The
    kinds are kept apart rather than collapsed to a boolean because publishing
    to a band you also SUBSCRIBE to would mean something quite different, and a
    scan that reported only 'found an id here' could not tell the two apart.
    """
    a, b = img.offset(lo), img.offset(hi)
    span = img.blob[a:b]
    out = []
    for i in range(len(span) - 5):
        if span[i] != 0x68:
            continue
        imm = struct.unpack_from("<I", span, i + 1)[0]
        if not (band[0] <= imm < band[1]):
            continue
        tgt = call_va = None
        for k in range(5, CALL_WINDOW):
            if i + k < len(span) and span[i + k] == 0xE8:
                rel = struct.unpack_from("<i", span, i + k + 1)[0]
                call_va = lo + i + k
                tgt = call_va + 5 + rel
                break
        kind = ("post" if tgt == POST else "subscribe" if tgt == SUBSCRIBE else
                "none" if tgt is None else f"{tgt:#010x}")
        out.append((imm, kind, lo + i, call_va))
    return out


def quest_family(img=None):
    """{opcode: [frame ids POSTED]} for the eleven quest handler bodies."""
    img = img or Image()
    out = {}
    for i, (va, op) in enumerate(QUEST_BODIES):
        end = QUEST_BODIES[i + 1][0] if i + 1 < len(QUEST_BODIES) else va + QUEST_TAIL
        out[op] = sorted(f for f, kind, _p, _c in publishes(img, va, end)
                         if kind == "post")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine build")
    ap.add_argument("--at", type=lambda s: int(s, 0),
                    help="body VA; scan from here to --end")
    ap.add_argument("--end", type=lambda s: int(s, 0))
    ap.add_argument("--band", nargs=2, type=lambda s: int(s, 0), default=QUEST_BAND)
    args = ap.parse_args()

    img = Image(args.exe)
    print(f"exe: {img.path}")
    print(f"     {len(img.blob)} bytes, {'the pinned build ' + str(pinned.BUILD) if img.pinned else 'NOT the pinned image -- VAs may not mean what this file says'}")
    print(f"band: {args.band[0]:#010x}..{args.band[1]:#010x}\n")

    if args.at:
        end = args.end or args.at + 0x100
        for f, kind, pv, cv in publishes(img, args.at, end, tuple(args.band)):
            where = f" call {cv:#010x}" if cv else ""
            print(f"  {f:#010x} {kind:<10} push {pv:#010x}{where}"
                  f"   {SUBSCRIBERS.get(f, '')}")
        return 0

    got = quest_family(img)
    agree = 0
    print(f"{'opcode':8} {'body':>12}  posts        subscribers")
    print("-" * 100)
    for va, op in QUEST_BODIES:
        ids = got[op]
        ok = ids == sorted(QUEST_EXPECTED[op])
        agree += ok
        shown = ", ".join(f"{f:#010x}" for f in ids) or "(none)"
        print(f"0x{op:04X}   {va:#012x}  {shown:<12} "
              f"{SUBSCRIBERS.get(ids[0], '') if ids else 'nothing in the direct push/call form'}")
        if not ok:
            print(f"{'':8} {'':12}  ^^ DISAGREES with QUEST_EXPECTED "
                  f"{[hex(x) for x in QUEST_EXPECTED[op]]}")
    print("-" * 100)
    print(f"{agree} of {len(QUEST_BODIES)} bodies match the recorded pairing")
    return 0 if agree == len(QUEST_BODIES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
