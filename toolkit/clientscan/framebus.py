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

WHICH CLIENT IT READ, and the header now says so from the FILE. Until
2026-08-17 the label was `len(blob) == pinned.SIZE`, printed as "the pinned
build 38797" -- and build 38833 ships at exactly 38797's length, 10,483,904
bytes, so `--exe`'d at the 38833 client this tool reported the pin. Every VA
below was measured on 38797 and addresses drift between the two by 0x20..0x160
per region, so that header sat above a table of 38797's offsets applied to
another build's bytes. `pinned.py`'s own BUILDS comment had already written down
that "a size check written anywhere else is now a bug"; this was that bug, and
three sibling tools had it too (`worldmap.py`, `consttable.py`,
`heroes_table.py`, all stamping 38797 onto extracted content rows). The build
comes from `buildid.of_image` now -- registry sha256, falling back to the
client's own build getter -- and a non-pinned image gets a loud warning rather
than a friendly wrong label. `test_framebus.py` §3 turns it red.

WHAT THIS DOES NOT DO. It reads `push imm32` / `call rel32` and nothing else, so
an id loaded into a register, or posted through an indirect call, is invisible to
it. Treat a NEGATIVE ("this body posts nothing") as "nothing in the direct form",
which is how `0x004A` and `0x004B` are recorded. Standard library only -- no
disassembler -- because `CLAUDE.md`'s carve-out (1) is scoped to two named files
and this is not one of them.
"""
import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import buildid   # noqa: E402
import pinned    # noqa: E402
import srctree   # noqa: E402

_UNREAD = object()

# The two bus helpers, MEASURED on build 38797. `studies/quests/FINDINGS.md` §1.6
# records a refuted reading here worth keeping: a lane reported two subscribe
# helpers, `0x00637BD0` for the quest UI and `0x00633BD0` for GmQuestComplete.
# The bytes it quoted were right and the arithmetic was not -- every call target
# in the band resolves to `0x00633BD0`, and the only difference is the argument
# form (`[reg+4]` vs `[reg]`), which is a frame-pointer offset and not a second API.
POST = 0x00633D70
SUBSCRIBE = 0x00633BD0

# PER-BUILD TABLES, added 2026-09-14 when build 38888 -- the first image since
# 38797 whose SIZE changed (10,483,904 -> 10,493,120) -- moved every VA below.
# `test_quests.py` §20 went red on it (12 of 12 sites drifted, the frame-bus
# scan found nothing in any quest body), which is that check doing its job.
# The 38888 column was MEASURED by a masked byte search (operands that are an
# absolute address or a rel32 wildcarded) from 38797's bytes into 38888's, and
# then VERIFIED the only way that counts: the relocated bodies, scanned with the
# relocated bus helper, post exactly QUEST_EXPECTED / COMPLETION_EXPECTED, 11 of
# 11 and 4 of 4. The two families moved by different amounts -- the bus helpers
# by +0x430, the quest bodies by +0x460, three of the four completion bodies by
# +0x360 -- so there is no single delta to apply, and a caller that "adds the
# offset" would be wrong on one of the three. Each body's prologue was matched
# too (`push ebp; mov ebp, esp; sub esp, N` with N unchanged per body).
#
# 38833 AND 38849 HAVE ROWS TOO, and the first draft of this table did not give
# them any: `test_quests.py` §20 proves the quest family's twelve sites
# byte-identical to 38797 on both, and the draft read that as "the whole table
# holds" -- then `framebus.py --exe <38833>` printed 1 of 4 completion bodies.
# The completion family was never in §20's twelve, and it did move: 0x0096,
# 0x0097 and 0x00FB sit 0x160 lower on 38833 and 0x100 lower on 38849 than on
# the pin (0x006C's start held, its bytes did not). Each row below carries the
# pin's quest bodies (proven) and its OWN completion bodies (measured the same
# way as 38888's: the publisher's offset inside every body is unchanged -- 0x57,
# 0x93, 0x38, 0x3E -- so the old lengths bound them). A build with no row gets
# NO table: `tables_for` returns None and the caller says so, rather than
# applying the pin's offsets to a stranger's bytes (the 38833 header bug, above).
BuildTables = collections.namedtuple(
    "BuildTables", "build post subscribe quest_bodies completion_bodies")

_PIN_QUEST_BODIES = [
    (0x0080F0A0, 0x0049), (0x0080F250, 0x004A), (0x0080F270, 0x004B),
    (0x0080F290, 0x004C), (0x0080F3C0, 0x004D), (0x0080F470, 0x0050),
    (0x0080F670, 0x004E), (0x0080F6F0, 0x0051), (0x0080F7A0, 0x0052),
    (0x0080F8E0, 0x0053), (0x0080F990, 0x0054),
]

TABLES = {
    38797: BuildTables(
        38797, 0x00633D70, 0x00633BD0, _PIN_QUEST_BODIES,
        [(0x00810AF0, 0x00810B61, 0x006C), (0x008123E0, 0x0081248D, 0x0096),
         (0x00812490, 0x00812505, 0x0097), (0x00815260, 0x008152D4, 0x00FB)]),
    38833: BuildTables(
        38833, 0x00633D70, 0x00633BD0, _PIN_QUEST_BODIES,
        [(0x00810AF0, 0x00810B61, 0x006C), (0x00812280, 0x0081232D, 0x0096),
         (0x00812330, 0x008123A5, 0x0097), (0x00815100, 0x00815174, 0x00FB)]),
    38849: BuildTables(
        38849, 0x00633D70, 0x00633BD0, _PIN_QUEST_BODIES,
        [(0x00810AF0, 0x00810B61, 0x006C), (0x008122E0, 0x0081238D, 0x0096),
         (0x00812390, 0x00812405, 0x0097), (0x00815160, 0x008151D4, 0x00FB)]),
    38888: BuildTables(
        38888, 0x006341A0, 0x00634000,
        [(0x0080F500, 0x0049), (0x0080F6B0, 0x004A), (0x0080F6D0, 0x004B),
         (0x0080F6F0, 0x004C), (0x0080F820, 0x004D), (0x0080F8D0, 0x0050),
         (0x0080FAD0, 0x004E), (0x0080FB50, 0x0051), (0x0080FC00, 0x0052),
         (0x0080FD40, 0x0053), (0x0080FDF0, 0x0054)],
        [(0x00810F50, 0x00810FC1, 0x006C), (0x00812740, 0x008127ED, 0x0096),
         (0x008127F0, 0x00812865, 0x0097), (0x008155C0, 0x00815634, 0x00FB)]),
}


def tables_for(build):
    """The table measured on `build`, or None for a build nobody has measured.
    `None` (an image whose build could not be read -- the synthetic images
    test_framebus §1 plants) gets the pin's table, because those tests plant
    the pin's VAs."""
    if build is None:
        return TABLES[pinned.BUILD]
    return TABLES.get(build)

# Read the docstring before shrinking this.
CALL_WINDOW = 48

# The quest bus, MEASURED: every id in 0x1000014C..0x1000015F is published from
# inside ChCliApi's VA range, and 0x10000160 is published five times from
# MsCliTourn, so the upper edge is a real boundary rather than a round number.
QUEST_BAND = (0x1000014C, 0x10000160)

# `studies/quests/FINDINGS.md` §2.1's handler bodies, sorted by VA so each body's
# extent is [va, next va). 0x0054 is last and gets a bounded tail rather than an
# open one -- its own publisher sits at 0x0080FA12, 0x82 in.
QUEST_BODIES = TABLES[38797].quest_bodies      # the pin's; see TABLES for 38888
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

# The completion family, MEASURED 2026-08-19 (`studies/quests/FINDINGS.md`
# §9.7). §9.3's table left the four publishers above 0x10000155 as "not a
# quest-family handler" -- true, and incomplete: they are the OTHER FOUR
# completion-family opcodes' bodies. Each body was located through the receive
# table (`msghandler.py <op>` prints the dispatch stub and its one call) and
# bounded by its own ret; the bodies are not contiguous the way QUEST_BODIES
# are, so each row carries an explicit end rather than borrowing its
# neighbour's start. Two instruments agree on the pairing: msghandler's linear
# disassembly and this module's own scan.
COMPLETION_BODIES = TABLES[38797].completion_bodies   # the pin's; see TABLES

# The pairing, stated so a caller can assert on it. THE SWAP IS REAL AND
# MEASURED: 0x0096 posts 0x10000158 and 0x0097 posts 0x10000157 -- frame-id
# order does not follow opcode order, which is exactly what a range-only or
# assume-adjacent reading would get wrong. Do not "fix" it.
COMPLETION_EXPECTED = {
    0x006C: [0x10000156], 0x0096: [0x10000158],
    0x0097: [0x10000157], 0x00FB: [0x10000159],
}

# Who listens, from §1.6's subscribe-side scan. Prose for the reader; the module
# asserts nothing about it. 0x10000155-0x10000159 were scanned as ONE band row,
# so the set shown for those five is the band's, not resolved per id.
SUBSCRIBERS = {
    0x1000014E: "QuestLog, QuestTaskTracker, GmView, GmHelpGuide, Compass, UiCtlInstance",
    0x1000014F: "QuestChallenge, QuestTaskTracker",
    0x10000150: "QuestTaskTracker, GmMapCtlLocationTag, Compass",
    0x10000151: "QuestTaskTracker, Compass",
    0x10000152: "QuestLog, QuestTaskTracker, GmHelpGuide, GmMapCtlLocationTag, Compass",
    0x10000153: "QuestLog, QuestTaskTracker, GmMapCtlLocationTag, Compass",
    0x10000154: "QuestChallenge, QuestTaskTracker, Compass",
    0x10000155: "GmQuestComplete, GmView, QuestTaskTracker",
    0x10000156: "GmQuestComplete, GmView, QuestTaskTracker (band row)",
    0x10000157: "GmQuestComplete, GmView, QuestTaskTracker (band row)",
    0x10000158: "GmQuestComplete, GmView, QuestTaskTracker (band row)",
    0x10000159: "GmQuestComplete, GmView, QuestTaskTracker (band row)",
}


class Image:
    """A PE opened for VA reads. Stdlib section walk, no dependency."""

    def __init__(self, path=None):
        self.path = path or srctree.default_exe()
        self.blob = open(self.path, "rb").read()
        self._id = _UNREAD
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

    # WAS A SIZE CHECK, and it was wrong the day 38833 shipped. This read
    # `self.pinned = len(self.blob) == pinned.SIZE`, and build 38833 is
    # byte-for-byte the same LENGTH as 38797 -- 10,483,904 -- so `--exe`'d at
    # the 38833 client the header printed "the pinned build 38797" while every
    # VA below meant something else. `pinned.py`'s own BUILDS comment had
    # called it two days earlier: "a size check written anywhere else is now a
    # bug". This is that bug, found 2026-08-17 by pointing the tool at 38833.
    #
    # Lazy because §1 of `test_framebus.py` builds dozens of synthetic images
    # on a bare machine and none of them wants a sha256 or a PE scan; the label
    # is read once, in `main`, from the file that was actually opened.
    @property
    def identity(self):
        """(build number or None, how we know) for the file actually opened."""
        if self._id is _UNREAD:
            self._id = buildid.of_image(self.path)
        return self._id

    @property
    def build(self):
        return self.identity[0]

    @property
    def is_pinned(self):
        """Do this file's bytes mean what the VAs in this module say?

        Addresses drift between builds by 0x20..0x160 per region, so this is
        the difference between a measurement and a confident wrong number --
        not a cosmetic label.
        """
        return self.build == pinned.BUILD


def publishes(img, lo, hi, band=QUEST_BAND):
    """Every `push imm32` in [lo, hi) whose imm is in `band`, with its call.

    Returns (frame_id, kind, push_va, call_va) where kind is 'post',
    'subscribe', 'none' (no call inside the window) or a raw target string. The
    kinds are kept apart rather than collapsed to a boolean because publishing
    to a band you also SUBSCRIBE to would mean something quite different, and a
    scan that reported only 'found an id here' could not tell the two apart.
    """
    # The bus helpers are per build (+0x430 on 38888). An image with no table
    # keeps the pin's, so a caller scanning a stranger's bytes sees raw call
    # targets rather than 'post' -- which is the honest reading of them.
    t = tables_for(img.build)
    post, subscribe = (t.post, t.subscribe) if t else (POST, SUBSCRIBE)
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
        kind = ("post" if tgt == post else "subscribe" if tgt == subscribe else
                "none" if tgt is None else f"{tgt:#010x}")
        out.append((imm, kind, lo + i, call_va))
    return out


def quest_family(img=None):
    """{opcode: [frame ids POSTED]} for the eleven quest handler bodies.

    On a build with no table this returns every opcode EMPTY rather than
    raising: 'nothing in the direct form' is what a scan of the pin's VAs
    over a stranger's bytes measures, and test_quests §20's control (38519)
    relies on the empty answer to prove the pairing is a measurement."""
    img = img or Image()
    t = tables_for(img.build)
    bodies = t.quest_bodies if t else QUEST_BODIES
    out = {}
    for i, (va, op) in enumerate(bodies):
        end = bodies[i + 1][0] if i + 1 < len(bodies) else va + QUEST_TAIL
        out[op] = sorted(f for f, kind, _p, _c in publishes(img, va, end)
                         if kind == "post")
    return out


def completion_family(img=None):
    """{opcode: [frame ids POSTED]} for the four completion-family bodies."""
    img = img or Image()
    t = tables_for(img.build)
    bodies = t.completion_bodies if t else COMPLETION_BODIES
    return {op: sorted(f for f, kind, _p, _c in publishes(img, lo, hi)
                       if kind == "post")
            for lo, hi, op in bodies}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine build")
    ap.add_argument("--at", type=lambda s: int(s, 0),
                    help="body VA; scan from here to --end")
    ap.add_argument("--end", type=lambda s: int(s, 0))
    ap.add_argument("--band", nargs=2, type=lambda s: int(s, 0), default=QUEST_BAND)
    args = ap.parse_args()

    exe, why = ((args.exe, "given on the command line") if args.exe
                else pinned.find())
    img = Image(exe)
    build, how = img.identity
    print(f"client: {exe}")
    print(f"        ({why})")
    print(f"        build {build if build is not None else 'UNKNOWN'}, "
          f"{len(img.blob):,} bytes -- {how}")
    t = tables_for(build)
    if t is None:
        print(f"        ^^ this is NOT build {pinned.BUILD} and NO table was "
              f"measured on it. Addresses drift between builds by 0x20..0x160 "
              f"per region,\n"
              f"           so the rows below are not a reading of this client -- "
              f"they are {pinned.BUILD}'s offsets applied to someone else's bytes.")
    elif not img.is_pinned:
        print(f"        ^^ this is NOT build {pinned.BUILD}; the rows below use "
              f"build {t.build}'s own table, MEASURED on it.")
    bodies = t.quest_bodies if t else QUEST_BODIES
    cbodies = t.completion_bodies if t else COMPLETION_BODIES
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
    for va, op in bodies:
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
    print(f"{agree} of {len(bodies)} bodies match the recorded pairing")

    cgot = completion_family(img)
    cagree = 0
    print(f"\ncompletion family (GmQuestComplete's other four publishers, §9.7)")
    print("-" * 100)
    for lo, _hi, op in cbodies:
        ids = cgot[op]
        ok = ids == sorted(COMPLETION_EXPECTED[op])
        cagree += ok
        shown = ", ".join(f"{f:#010x}" for f in ids) or "(none)"
        print(f"0x{op:04X}   {lo:#012x}  {shown:<12} "
              f"{SUBSCRIBERS.get(ids[0], '') if ids else '(none)'}")
        if not ok:
            print(f"{'':8} {'':12}  ^^ DISAGREES with COMPLETION_EXPECTED "
                  f"{[hex(x) for x in COMPLETION_EXPECTED[op]]}")
    print("-" * 100)
    print(f"{cagree} of {len(cbodies)} completion bodies match the "
          f"recorded pairing")
    return 0 if (agree == len(bodies)
                 and cagree == len(cbodies)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
