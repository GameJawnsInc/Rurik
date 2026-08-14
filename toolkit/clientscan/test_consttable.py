r"""The `Gw\Const\*.cpp` table locator: the closure, and the four ways it refuses.

`consttable.py` claims a general, build-independent locator: a static table is
followed immediately by a string, so `base + count*stride` lands on that
string's first byte. This file is that claim's evidence, and most of it is
negative controls, because the failure mode that matters is not "it did not
find the table" -- it is "it found a table, reported a base and a count, and
they were the wrong ones." Every value downstream of that is sourced,
plausible and wrong.

WHAT EACH CONTROL IS FOR, since a list of refusals reads as boilerplate:

  duplicated anchor  A second copy of the anchor string makes `data.find()`
                     return the FIRST, which is a different table. Section 1
                     plants two anchors over two DIFFERENT tables and requires
                     the refusal -- and it checks that the first-hit answer
                     really would have been wrong, so the control cannot pass
                     by the two happening to agree.

  missing anchor     Zero hits and two hits are the same defect (the module
                     cannot say which table is meant) and must take the same
                     exit.

  wrong stride       Two shapes, and only measuring both is honest. A stride
                     that does NOT divide the span must break the closure and
                     refuse. A stride that DOES divide it closes on the same
                     base with a multiple of the true count, and NOTHING in the
                     left-edge path can see that -- so section 3 requires the
                     divisor to still close, and then requires the index column
                     to refute it. That is not a formality: `s_glow` was
                     entered in the corpus as 2 x 44, it closed on the correct
                     base, and the index column is what turned it into 11 x 8.

  positive control   A locator that refuses everything protects nothing,
                     because nobody runs it. Sections 0 and 5 require real
                     tables to resolve, on a synthetic image and on the client.

Sections 0-4 build a small PE32 image byte by byte and need NO vault and NO
client -- a locator defect is not a property of any one binary. Sections 5-8
need the vaulted pristine client and declare a skip without it.

THE STRONGEST CHECKS HERE ARE NOT THIS MODULE'S. Section 6 requires the located
`s_skill` and `s_attrib` to equal what `skilltable.locate_table` and
`reskin.locate_attrib` find -- two implementations that share no method with
the anchor arithmetic (one scans for a self-declared count, the other for an
ascending id column). Agreement there is a fact about the client; agreement
inside this module would be a fact about this module.

Section 7 pins the corpus census against LITERALS written in this file rather
than against numbers the module computes. `test_agentlife.py` records why:
twelve of fourteen combat constants could be set to a wrong value with 125
checks green, because every section computed its expectation FROM the symbol
under test. A symbol appearing in a test file is not a check.
"""

import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import checks                                                   # noqa: E402
import consttable                                               # noqa: E402
import pinned                                                   # noqa: E402
import vaultpath                                                # noqa: E402
from gwpe import PE                                             # noqa: E402

# Set from a real green run on the pinned pristine client: 69 (was 61 before
# section 7b). Sections 0-4 score 28 without a vault, so a vault-less run goes
# RED and says so -- the synthetic half cannot refute anything about ArenaNet's
# own layout, and a green exit code that measured only the fixtures would be
# the exact defect `checks.py` exists for.
#
# Which of 7b's checks are load-bearing was MEASURED, by patching the live
# corpus row and running this file against each. The counts below are what the
# runs printed; a first draft of this comment GUESSED them and had three of the
# four wrong, which is the mistake test_png.py and test_glyphs.py both record.
#   the EXACT pre-fix row, 20 x 24 ........................ 3 red
#   right stride, wrong declared count, 20 x 48 ........... 5 red (refused at
#                                                           load by the pad)
#   stride 16, a divisor of 48 that also closes ........... 2 red
#   the declared count dropped, left edge derives it ...... 1 red
# The last is not a defect and reddens on purpose: the number is unchanged and
# the PROVENANCE is not, which is the entire subject of the section.
#
# What the pre-fix row does NOT redden is the more useful half. The left-edge
# corroboration check passes under it, because 24 divides 480 and both
# witnesses then agree on 20 -- a corroboration between two readings of the
# SAME 480 bytes cannot see a divisor stride, by construction. Only the two
# checks that read the client's own code can, which is the section's point.
LEDGER = checks.Ledger("consttable", floor=69)

IMAGE_BASE = 0x00400000
TEXT_RVA, TEXT_OFF, TEXT_SIZE = 0x1000, 0x400, 0x400
RDATA_RVA, RDATA_OFF, RDATA_SIZE = 0x2000, 0x800, 0x800
PREV = b"PREVSTRING\x00"

_TMP = []


def build_image(rdata: bytes, text: bytes) -> str:
    """A minimal PE32 with a .text and a .rdata, written to a temp file.

    `gwpe.PE` reads a real header, so the fixture has to be a real image -- a
    bag of bytes would exercise a different code path from the one that runs on
    the client. Everything else is deliberately tiny.
    """
    e = 0x80
    hdr = bytearray(b"\x00" * RDATA_OFF)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, e)
    hdr[e:e + 4] = b"PE\x00\x00"
    struct.pack_into("<H", hdr, e + 4, 0x014C)       # machine: x86
    struct.pack_into("<H", hdr, e + 6, 2)            # sections
    struct.pack_into("<H", hdr, e + 20, 0xE0)        # optional header size
    struct.pack_into("<H", hdr, e + 24, 0x010B)      # PE32
    struct.pack_into("<I", hdr, e + 52, IMAGE_BASE)
    sec = e + 24 + 0xE0
    for i, (name, vaddr, rawsize, rawptr) in enumerate((
            (b".text", TEXT_RVA, TEXT_SIZE, TEXT_OFF),
            (b".rdata", RDATA_RVA, RDATA_SIZE, RDATA_OFF))):
        o = sec + i * 40
        hdr[o:o + len(name)] = name
        struct.pack_into("<I", hdr, o + 8, rawsize)
        struct.pack_into("<I", hdr, o + 12, vaddr)
        struct.pack_into("<I", hdr, o + 16, rawsize)
        struct.pack_into("<I", hdr, o + 20, rawptr)
    body = bytearray(hdr)
    body[TEXT_OFF:TEXT_OFF + len(text)] = text
    body += b"\x00" * RDATA_SIZE
    body[RDATA_OFF:RDATA_OFF + len(rdata)] = rdata
    fd, path = tempfile.mkstemp(suffix=".exe", prefix="consttable_")
    os.write(fd, bytes(body))
    os.close(fd)
    _TMP.append(path)
    return path


def rdata_va(off_in_rdata: int) -> int:
    return IMAGE_BASE + RDATA_RVA + off_in_rdata


def synth(anchor=b"P:\\Fake\\Const.cpp\x00", count=6, stride=12,
          index_off=0, second_anchor_at=None, ref_at=None, pad=0,
          indices=None):
    """(path, base_file_offset) for an image holding one planted table.

    Layout, which is the client's own: [previous string][pad][table][anchor].
    `ref_at` is the .rdata offset whose VA is planted in .text as the
    accessor's absolute load; it defaults to the table base. `index_off=None`
    plants records with NO index column, which is the shape 16 of the 24 real
    tables have and the one the blind spot lives in.
    """
    body = bytearray()
    if second_anchor_at is not None:
        # A DIFFERENT table, then a copy of the anchor. `data.find()` returns
        # this one, so a first-hit locator answers with the wrong base.
        body += b"DECOYSTRING\x00"
        while len(body) % 4:
            body.append(0)
        for i in range(second_anchor_at):
            body += bytes(bytearray(struct.pack("<3I", i, 0xDEAD0000 + i, 0)
                                    )[:stride]).ljust(stride, b"\x00")
        body += anchor
    body += PREV
    while len(body) % 4:
        body.append(0)
    body += b"\x00" * pad
    base = len(body)
    for i in range(count):
        rec = bytearray(b"\x00" * stride)
        idx = i if indices is None else indices[i]
        if index_off is not None and index_off + 4 <= stride:
            struct.pack_into("<I", rec, index_off, idx)
            if stride >= 8:
                struct.pack_into("<I", rec, 4 if index_off == 0 else 0, 1000 + i)
        else:
            for o in range(0, stride - 3, 4):
                struct.pack_into("<I", rec, o, 0x11110000 + i * 16 + o)
        body += rec
    body += anchor
    ref = base if ref_at is None else ref_at
    text = struct.pack("<I", rdata_va(ref))
    return build_image(bytes(body), text), base + RDATA_OFF


def refuses(fn, kind, needle=""):
    try:
        fn()
    except kind as exc:
        return needle in str(exc)
    except Exception:
        return False
    return False


# --------------------------------------------------------------------------

def section_positive():
    print("\n0. the positive control: a planted table resolves")
    path, base = synth(count=6, stride=12)
    pe = PE(path)
    t = consttable.locate(pe, b"P:\\Fake\\Const.cpp\x00", 12, symbol="s_fake",
                          index_off=0)
    LEDGER.ok(t.base == base and t.count == 6 and t.stride == 12,
              "base, count and stride come back as planted",
              f"base 0x{t.base:X} (planted 0x{base:X}), {t.count} x {t.stride}")
    LEDGER.ok(t.closes,
              "and base + count*stride lands exactly on the anchor's first byte",
              f"0x{t.end:X} == 0x{t.anchor_off:X}")
    LEDGER.ok(t.pad == 0 and t.edge is not None,
              "the left edge is the previous string, with zero pad",
              f"edge 0x{t.edge:X} {bytes(t.edge_text or b'')!r}")
    LEDGER.ok(t.refs == 1,
              "and the planted accessor load corroborates the base",
              f"{t.refs} reference(s) to VA 0x{rdata_va(base):08X} in .text")
    LEDGER.ok(len(t.witnesses) == 3,
              "three independent witnesses on this row: index, left edge, code",
              str(t.witnesses))

    # A locator that only ever sees one shape has not been shown to locate.
    path2, base2 = synth(count=17, stride=20, pad=4)
    t2 = consttable.locate(PE(path2), b"P:\\Fake\\Const.cpp\x00", 20,
                           symbol="s_fake2", index_off=0, pad=4)
    LEDGER.ok(t2.count == 17 and t2.base == base2 and t2.pad == 4,
              "a second table with a different stride, count and pad also resolves",
              f"{t2.count} x {t2.stride} at 0x{t2.base:X}, pad {t2.pad:+d}")


def section_anchor_refusals():
    print("\n1. an anchor that cannot name one table")
    anchor = b"P:\\Fake\\Const.cpp\x00"
    path, base = synth(count=6, stride=12, second_anchor_at=4)
    pe = PE(path)
    first_hit = pe.data.find(anchor)
    true_hit = pe.data.rfind(anchor)
    LEDGER.ok(first_hit != true_hit and pe.data.count(anchor) == 2,
              "the fixture really does hold two anchors over two DIFFERENT tables",
              f"first at 0x{first_hit:X}, real at 0x{true_hit:X} -- without this "
              f"the refusal below could pass by the two agreeing")
    naive_base = first_hit - 6 * 12
    LEDGER.ok(naive_base != base,
              "and a first-hit locator would answer with the wrong base",
              f"first-hit 0x{naive_base:X} vs planted 0x{base:X}")
    LEDGER.ok(refuses(lambda: consttable.locate(pe, anchor, 12, symbol="s_fake",
                                                index_off=0),
                      consttable.AnchorNotUnique, "occurs 2 time(s)"),
              "a DUPLICATED anchor is REFUSED, not resolved to the first hit",
              "two candidates and no rule to choose between them is exactly when "
              "a locator must stop")

    path3, _ = synth(count=6, stride=12)
    pe3 = PE(path3)
    LEDGER.ok(refuses(lambda: consttable.locate(pe3, b"NOT-IN-THIS-IMAGE\x00", 12,
                                                symbol="s_missing", index_off=0),
                      consttable.AnchorNotUnique, "occurs 0 time(s)"),
              "a MISSING anchor takes the same exit as a duplicated one",
              "zero hits and two hits are one defect: the module cannot say "
              "which table is meant")


def section_wrong_stride():
    print("\n2. a wrong stride must break the closure, not invent a count")
    anchor = b"P:\\Fake\\Const.cpp\x00"
    # A table with NO index column -- the shape 16 of the 24 real tables have,
    # and the one the blind spot lives in.
    path, base = synth(count=6, stride=12, index_off=None)
    pe = PE(path)
    span = pe.data.find(anchor) - base
    LEDGER.ok(span == 72, "the planted span is 72 bytes", f"{span}")

    # 16 does not divide 72. The left-edge path must refuse rather than round.
    LEDGER.ok(refuses(lambda: consttable.locate(pe, anchor, 16, symbol="s_fake"),
                      consttable.NoClosure, "residual"),
              "a NON-DIVISOR stride refuses, and the message names the residual",
              "72 / 16 is 4 remainder 8, so base + count*stride cannot land on "
              "the anchor -- it does NOT round to 4 records and carry on")
    LEDGER.ok(refuses(lambda: consttable.locate(pe, anchor, 16, symbol="s_fake",
                                                count=5),
                      consttable.Refusal, ""),
              "and a DECLARED count with the wrong stride refuses too, by the "
              "code reference",
              "5 x 16 puts the base 8 bytes off, somewhere the planted "
              "accessor never loads")

    # 4 DOES divide 72. This is the measured blind spot, not an accident.
    loose = consttable.locate(pe, anchor, 4, symbol="s_fake")
    LEDGER.ok(loose.closes and loose.count == 18 and loose.base == base,
              "a DIVISOR stride closes on the SAME base with 3x the count -- "
              "the blind spot, measured rather than assumed",
              f"{loose.count} x 4 at 0x{loose.base:X}, and the true table is "
              f"6 x 12. The left edge fixes the BASE, never the stride")
    LEDGER.ok(4 in consttable.locate(pe, anchor, 12,
                                     symbol="s_fake").rival_strides(pe),
              "so the surviving rivals are REPORTED rather than hidden",
              f"{consttable.locate(pe, anchor, 12, symbol='s_fake').rival_strides(pe)}"
              f" -- a blind spot nobody prints is a blind spot nobody closes")

    # The same table WITH an index column: now the rivals are refutable.
    path2, base2 = synth(count=6, stride=12, index_off=0)
    pe2 = PE(path2)
    good = consttable.locate(pe2, anchor, 12, symbol="s_fake", index_off=0)
    LEDGER.ok(good.count == 6 and good.base == base2 and good.closes,
              "the same layout with an index column still resolves",
              f"{good.count} x {good.stride} at 0x{good.base:X}")
    LEDGER.ok(good.rival_strides(pe2) == [],
              "and NO rival stride survives its index column",
              "which is the difference between s_effect (0 rivals) and s_eula "
              "(4, 36, 44, 132) in the real corpus")
    LEDGER.ok(refuses(lambda: consttable.locate(pe2, anchor, 4, symbol="s_fake",
                                                index_off=0),
                      consttable.Refusal, ""),
              "and asking for the divisor stride outright is REFUSED rather "
              "than answered with 18 records",
              "s_glow was entered in the corpus as 2 x 44, closed on the "
              "correct base, and is 11 x 8; the index column is what caught it")


def section_shape_and_pad():
    print("\n3. the shape and the pad, each refusing on its own")
    anchor = b"P:\\Fake\\Const.cpp\x00"

    # An index column that runs the wrong way: its last entry still predicts a
    # count and a base, and every earlier row contradicts it.
    path, _base = synth(count=6, stride=12, index_off=0,
                        indices=[5, 4, 3, 2, 1, 5])
    pe = PE(path)
    LEDGER.ok(refuses(lambda: consttable.locate(pe, anchor, 12, symbol="s_fake",
                                                index_off=0),
                      consttable.ShapeDisagrees, "index column"),
              "an index column that is not 0..count-1 is REFUSED",
              "the anchor and the shape must agree or one of the two "
              "assumptions is wrong for this build")

    # A declared pad that does not match the image.
    path2, base2 = synth(count=6, stride=12, pad=4)
    pe2 = PE(path2)
    LEDGER.ok(refuses(lambda: consttable.locate(pe2, anchor, 12, symbol="s_fake",
                                                index_off=0, pad=0),
                      consttable.NoClosure, "pad byte(s)"),
              "a pad of 4 declared as 0 is REFUSED, not tolerated",
              "the four +4 tables in the corpus are MSVC 8-alignment; a "
              "tolerance would also accept a base that is 4 bytes wrong for "
              "any other reason")
    ok = consttable.locate(pe2, anchor, 12, symbol="s_fake", index_off=0, pad=4)
    LEDGER.ok(ok.pad == 4 and ok.closes,
              "and declaring the measured pad makes it close -- the positive "
              "half, so the pad check is not just 'refuse everything'",
              f"pad {ok.pad:+d}, {ok.count} x {ok.stride} at 0x{ok.base:X}")

    # No code reference at all.
    path3, base3 = synth(count=6, stride=12, ref_at=0)
    pe3 = PE(path3)
    LEDGER.ok(refuses(lambda: consttable.locate(pe3, anchor, 12, symbol="s_fake",
                                                index_off=0),
                      consttable.NoClosure, "never loads"),
              "a base the planted code never loads is REFUSED",
              "the accessor's absolute load is the one witness that shares no "
              "method with the anchor arithmetic")
    LEDGER.ok(consttable.locate(pe3, anchor, 12, symbol="s_fake", index_off=0,
                                require_refs=False).base == base3,
              "...and the same image resolves with the code witness waived, so "
              "the refusal above is about the reference and nothing else",
              f"0x{base3:X}")

    # A count that walks the base out of its section.
    path4, _ = synth(count=6, stride=12)
    pe4 = PE(path4)
    LEDGER.ok(refuses(lambda: consttable.locate(pe4, anchor, 12, symbol="s_fake",
                                                count=4096),
                      consttable.BaseOutOfSection, ""),
              "a count that puts the base outside the anchor's section is REFUSED",
              "a table cannot straddle a section boundary, and a base in .text "
              "would decode instructions as records")


def section_left_edge():
    print("\n4. the left edge, and the chance string that broke it once")
    anchor = b"P:\\Fake\\Const.cpp\x00"

    # A printable run inside the record data, exactly the s_skill failure.
    body = bytearray(PREV)
    while len(body) % 4:
        body.append(0)
    base = len(body)
    for i in range(8):
        rec = bytearray(struct.pack("<3I", i, 1000 + i, 0))
        if i == 5:
            rec[4:12] = b"iDr4iDr\x00"
        body += rec
    body += anchor
    path = build_image(bytes(body), struct.pack("<I", rdata_va(base)))
    pe = PE(path)
    LEDGER.ok(refuses(lambda: consttable.locate(pe, anchor, 12, symbol="s_fake"),
                      consttable.Refusal, ""),
              "a chance printable run INSIDE the table breaks the left-edge "
              "derivation, and it refuses rather than reporting a short table",
              "eight bytes of `iDr4iDr4` sit 233 KB inside s_skill and the "
              "first version of consttable.py reported them as its left edge")
    LEDGER.ok(consttable.locate(pe, anchor, 12, symbol="s_fake", index_off=0,
                                pad=None).count == 8,
              "...while the index column, which does not depend on the left "
              "edge, still gets it right",
              "which is why s_skill's corpus row declares pad=None and takes "
              "its count from the index column")

    # A table with no string neighbour at all.
    body2 = bytearray(struct.pack("<4I", 0xFFFFFFFF, 0, 0, 0))
    base2 = len(body2)
    for i in range(5):
        body2 += struct.pack("<3I", i, 2000 + i, 0)
    body2 += anchor
    path2 = build_image(bytes(body2), struct.pack("<I", rdata_va(base2)))
    pe2 = PE(path2)
    LEDGER.ok(refuses(lambda: consttable.locate(pe2, anchor, 12, symbol="s_fake"),
                      consttable.NoClosure, "no index column"),
              "no index column, no declared count and no string on the left is "
              "REFUSED rather than guessed",
              "three of the 24 corpus tables have no string neighbour, and each "
              "carries another witness instead. The search is also floored at "
              "the section start, because the PE section table itself spells "
              "`.rdata\\0`, which is exactly the shape it looks for")
    LEDGER.ok(consttable.locate(pe2, anchor, 12, symbol="s_fake", count=5,
                                pad=None).base == base2 + RDATA_OFF,
              "and a declared count resolves the same image",
              f"0x{base2 + RDATA_OFF:X} -- the positive half of the refusal above")


# --------------------------------------------------------------------------
# from here on: the real client

def client():
    try:
        vaultpath.require_dir("client", why="consttable corpus")
    except SystemExit:
        return None
    path, _why = pinned.find()
    kind, _detail = pinned.identify(path)
    if kind != "pristine":
        return None
    return PE(path)


def section_corpus(pe):
    print("\n5. the corpus, located on the pinned client")
    tables, refusals = consttable.verify(pe)
    LEDGER.ok(not refusals, "every corpus row locates",
              "; ".join(f"{s}: {e}" for s, e in refusals) or "24 of 24")
    LEDGER.ok(len(tables) == 24 and all(t.closes for t in tables),
              "and every one closes: base + count*stride lands on its anchor",
              f"{sum(1 for t in tables if t.closes)} of {len(tables)}")
    by = {t.symbol: t for t in tables}
    LEDGER.ok(all(t.refs >= 1 for t in tables),
              "every located base is loaded by the client's own code",
              f"minimum {min(t.refs for t in tables)} reference(s), "
              f"{sum(t.refs for t in tables)} in total")
    snug = [t for t in tables if t.pad == 0]
    padded = [t for t in tables if t.pad not in (None, 0)]
    noedge = [t for t in tables if t.pad is None]
    LEDGER.ok(len(snug) == 17 and len(padded) == 4 and len(noedge) == 3,
              "17 tables butt against their left neighbour, 4 sit +4, 3 have "
              "no string neighbour",
              f"{len(snug)}/{len(padded)}/{len(noedge)} -- the +4 four are "
              f"{sorted(t.symbol for t in padded)}")
    LEDGER.ok(sorted(t.pad for t in padded) == [4, 4, 4, 4],
              "and every one of the four deviations is exactly +4, i.e. "
              "8-byte alignment and nothing else",
              "measured, not tolerated: the pad is asserted per row")
    LEDGER.ok(sorted(t.symbol for t in noedge)
              == ["s_attribPoints", "s_missionClientData", "s_skill"],
              "the three without a string neighbour are the three whose left "
              "neighbour is another datum",
              "s_skill's is s_energyTable (FF FF FF FF terminated), and the "
              "other two are preceded by tables")
    return by


def section_cross_tools(pe, by):
    print("\n6. two other implementations, which share no method with this one")
    import skilltable
    sys.path.insert(0, os.path.join(HERE, "..", "clientpatch"))
    import reskin

    base, count, _score = skilltable.locate_table(pe.data)
    LEDGER.ok(by["s_skill"].base == base and by["s_skill"].count == count,
              "s_skill agrees with skilltable.py, which finds the table by its "
              "own SELF-DECLARED count in row 0",
              f"anchor arithmetic 0x{by['s_skill'].base:X} x {by['s_skill'].count}; "
              f"skilltable 0x{base:X} x {count}")
    LEDGER.ok(by["s_skill"].stride == skilltable.RECORD_SIZE,
              "and on the stride", f"{by['s_skill'].stride}")

    abase, arows = reskin.locate_attrib(pe.data)
    LEDGER.ok(by["s_attrib"].base == abase and by["s_attrib"].count == len(arows),
              "s_attrib agrees with reskin.py, which corroborates its anchor "
              "with an ascending id column and a profession-range check",
              f"0x{abase:X} x {len(arows)}")

    found = reskin.locate(pe.data)
    LEDGER.ok(by["s_charProfession"].base == found["name"][0],
              "s_charProfession agrees with reskin.py's own locator",
              f"0x{found['name'][0]:X}")
    LEDGER.ok(by["s_charProfessionAbbrev"].base == found["abbrev"][0],
              "and so does s_charProfessionAbbrev",
              f"0x{found['abbrev'][0]:X}")


# Literals, written HERE. Not read back from the module, because a check whose
# expectation is computed from the thing under test moves with it.
EXPECTED = {
    # symbol:               (base,      count, stride)
    "s_skill":              (0x587ED0,   3443, 164),
    "s_attrib":             (0x634740,     51,  20),
    "s_titleClientData":    (0x634B80,     48,  12),
    "s_heroClientData":     (0x634E08,     40,  24),
    "s_effect":             (0x7A2CA8,   2077,  16),
    "s_aura":               (0x7AAEB8,     44,  12),
    "s_npcBang":            (0x7A2BE8,      8,  16),
    "s_missionClientData":  (0x56CE38,    888, 124),
    "s_glow":               (0x7A2B58,     11,   8),
    "s_worldData":          (0x635210,     10,  48),
    "s_dayStr":             (0x63738C,      7,   4),
    "s_charCondition":      (0x637580,      9,   4),
    "s_charDamage":         (0x6375CC,     14,   4),
    "s_charFaction":        (0x637624,     18,   4),
    "s_charKind":           (0x637690,     12,   4),
    "s_charKindSlaying":    (0x6376DC,     12,   4),
    "s_charMissionMedal":   (0x637730,      4,   4),
    "s_charProfession":     (0x637794,     11,   4),
    "s_charProfessionAbbrev": (0x6377E8,   11,   4),
    "s_eula":               (0x7BB1D0,     33,  12),
    "s_streakClass":        (0x7BC520,     22,  16),
    "s_ticketName":         (0x639A00,     32,   4),
    "s_categoryName":       (0x639918,     37,   4),
    "s_attribPoints":       (0x7C7B24,     14,   4),
}


def section_census(pe, by):
    print("\n7. the census, against literals written in this file")
    LEDGER.ok(sorted(by) == sorted(EXPECTED),
              "the corpus is exactly the 24 symbols this file names",
              f"{len(by)} located, {len(EXPECTED)} expected")
    wrong = [s for s, (b, c, st) in EXPECTED.items()
             if s in by and (by[s].base, by[s].count, by[s].stride) != (b, c, st)]
    LEDGER.ok(not wrong,
              "every base, count and stride matches the literal, on build "
              f"{pinned.BUILD}",
              "; ".join(f"{s}: {by[s].base:#X} x {by[s].count} x {by[s].stride}"
                        for s in wrong) or "24 of 24")
    LEDGER.ok(by["s_effect"].exceptions == [(2036, 2077)],
              "s_effect has exactly one index hole, at row 2036, holding 2077",
              "reported rather than smoothed away: a tolerance that hid it "
              "would also hide a wrong stride's first few disagreements")
    LEDGER.ok(by["s_effect"].rival_strides(pe) == [],
              "and no rival stride survives its index column",
              "2,076 records agreeing is not something a divisor stride does")
    LEDGER.ok(4 in by["s_eula"].rival_strides(pe),
              "while s_eula, which has no index column, keeps stride 4 as a "
              "live rival",
              f"{by['s_eula'].rival_strides(pe)} -- 33 x 12 and 99 x 4 close "
              "identically, and this module cannot choose")


def section_worlddata(pe, by):
    """The row this corpus got WRONG, and the witness that settled it.

    `s_worldData` shipped here as 20 x 24 with `stride_from="record shape,
    UNSETTLED"`. It closed, on the correct base, with a code reference
    corroborating it -- and it is 10 x 48. 24 divides 48, so every check this
    module owns was satisfied by the wrong answer, which is the blind spot
    doing exactly what the docstring says it does.

    So the checks here deliberately come from OUTSIDE the anchor arithmetic:
    the client's own accessor, read as BYTES. No disassembler -- CLAUDE.md
    carve-out (1) scopes capstone to `msghandler.py` and `codescan.py`, and
    this is neither -- which is the same reason `refs_to` is a raw byte search.
    """
    print("\n7b. s_worldData: the corrected row, against the client's own code")
    w = by["s_worldData"]
    base_va = pe.off_to_rva(w.base) + pe.image_base

    # `lea eax,[esi+esi*2]` ; `shl eax,4` ; `add eax, imm32`  -- index*3 << 4.
    # Found by SHAPE, not at a remembered address: an address copied out of a
    # study doc is a fact about one build, and the whole point of this module
    # is predictions that survive a rebuild.
    ACC = bytes([0x8D, 0x04, 0x76, 0xC1, 0xE0, 0x04, 0x05])
    text = pe.section(".text")
    lo, hi = text["rawptr"], text["rawptr"] + text["rawsize"]
    sites, i = [], pe.data.find(ACC, lo, hi)
    while i != -1:
        sites.append(i)
        i = pe.data.find(ACC, i + 1, hi)
    LEDGER.ok(len(sites) == 1,
              "exactly one site in .text scales an index by 3, shifts it left "
              "4 (x48) and adds an absolute base",
              f"{len(sites)} site(s) -- the `lea`+`shl` pair alone occurs 22 "
              f"times, so it is the trailing absolute `add` that makes this a "
              f"witness and not a coincidence")

    if len(sites) != 1:
        LEDGER.skip("the accessor's base and bound",
                    "the accessor pattern is not unique on this build, so "
                    "nothing below could name which site is meant")
        return

    site = sites[0]
    acc_va = pe.off_to_rva(site) + pe.image_base
    imm = struct.unpack_from("<I", pe.data, site + 7)[0]
    LEDGER.ok(imm == base_va,
              "and the base IT loads is the base the anchor arithmetic "
              "produced -- two witnesses sharing no method, meeting on one byte",
              f"accessor at 0x{acc_va:08X} loads 0x{imm:08X}; the anchor gives "
              f"0x{base_va:08X}. This is the check the old row also passed: the "
              f"base was never in question, only the stride")

    # The bound, in the same function: `cmp esi, imm8` above the lea.
    win = pe.data[site - 32:site]
    g = win.rfind(bytes([0x83, 0xFE]))
    bound = win[g + 2] if g != -1 else None
    LEDGER.ok(bound == w.count,
              "the same function bounds the index with the count this row "
              "declares, so 10 is ArenaNet's own arrsize and not our division",
              f"`cmp esi, {bound}` at 0x{pe.off_to_rva(site - 32 + g) + pe.image_base:08X}"
              f", guarding `index < arrsize(s_worldData)` at ConstWorld.cpp:41 "
              f"-- whose __FILE__ string IS this row's anchor, so the assert "
              f"and the table are the same measurement from two directions")
    LEDGER.ok(pe.data.count(b"index < arrsize(s_worldData)") == 1,
              "and that assert expression occurs exactly once, so the symbol "
              "naming this table is ArenaNet's own",
              "the row is no longer inferred from a record shape")

    # WHERE the 10 came from is the whole subject of this section, so the row
    # is required to still be recording it. Dropping the declaration would put
    # the count back to our own division of the left edge -- the weaker state
    # this row shipped in -- without changing the number, and nothing else
    # here would notice.
    LEDGER.ok(w.count_from == "declared",
              "the row DECLARES its count rather than dividing the left edge, "
              "so what is recorded is ArenaNet's bound and not our arithmetic",
              f"count_from = {w.count_from!r}, the s_missionClientData shape "
              f"(888 off `cmp esi, 0x378`) rather than the s_eula one")
    row = dict(consttable.BY_SYMBOL["s_worldData"])
    row.pop("count", None)
    derived = consttable.locate(pe, **row)
    LEDGER.ok(derived.count == w.count and derived.base == w.base
              and derived.count_from == "left edge",
              "and it is corroborated rather than merely trusted: drop the "
              "declaration and the left edge re-derives the SAME 10 by itself",
              f"left edge alone gives {derived.count} x {derived.stride} at "
              f"0x{derived.base:X}; the client's bound gives {w.count}. Two "
              f"witnesses meeting on one number is what the old 20 never had "
              f"-- it came from the left edge with nothing to meet")

    # 24 is still a rival, and saying so is the doctrine rather than a defect.
    LEDGER.ok(24 in w.rival_strides(pe),
              "24 -- what this row USED to carry -- is STILL a live rival, "
              "because every divisor of 48 closes on the same base",
              f"{w.rival_strides(pe)} -- reported, not hidden. What settled "
              f"this row was the code; the closure arithmetic never could")

    # But the RECORDS can refute it, which `rival_strides` does not know.
    # The retired reading is reproduced live so this is a difference between
    # two answers rather than a sentence claiming one.
    at48 = [struct.unpack_from("<I", pe.data, w.base + r * 48 + 0x14)[0]
            for r in range(10)]
    at24 = [struct.unpack_from("<I", pe.data, w.base + r * 24 + 0x14)[0]
            for r in range(20)]
    LEDGER.ok(set(at48) == {512} and set(at24) != {512},
              "and a COLUMN refutes 24 even though the closure cannot: +0x14 "
              "is 512 on all ten 48-byte records and ragged on the twenty "
              "24-byte ones",
              f"at 48: {sorted(set(at48))}; at 24: {sorted(set(at24))} -- 512 "
              f"is the client's own CONST_WORLD_CHUNK_SIZE (`CompassMap:472 "
              f"m_imageDims == CONST_WORLD_CHUNK_SIZE`). `rival_strides` tests "
              f"CLOSURE and the index column, never column coherence, so it "
              f"keeps 24 and is right to -- this is the limit of that report, "
              f"measured rather than argued")


def section_effect_toml(pe, by):
    print("\n8. s_effect as a content overlay")
    import tomllib
    t = by["s_effect"]
    text = consttable.effect_toml(pe, t, "TEST")
    doc = tomllib.loads(text)
    rows = doc.get("effect", {})
    LEDGER.ok(len(rows) == 2077, "2,077 rows, one per record",
              f"{len(rows)}")
    LEDGER.ok(sorted(int(k) for k in rows) == list(range(2077)),
              "keyed by the ARRAY INDEX 0..2076, with no gap",
              "keying by the id column would drop row 2036 and mint a 2077, "
              "because that one record's id is not its index")
    bad = [k for k, r in rows.items()
           if r.get("provenance", {}).get("source") != "client-table"
           or not r.get("provenance", {}).get("extractor")
           or not r.get("provenance", {}).get("build")]
    LEDGER.ok(not bad,
              "every row carries source, extractor and build -- conditions 1-3 "
              "of the 2026-08-11 ruling, per row",
              f"{len(bad)} row(s) short" if bad else "2,077 of 2,077")
    extractor = rows["0"]["provenance"]["extractor"]
    LEDGER.ok(os.path.exists(os.path.join(HERE, "..", "..",
                                          *extractor.split("/"))),
              "and the extractor it names exists in this checkout",
              f"{extractor} -- content.py resolves and requires this path, so a "
              f"renamed tool fails the load rather than the review")

    # The load itself, through the real store, with the overlay pointed at a
    # temp directory. NEVER vault/content/: that is merged into every server
    # start, and writing there would change a running server's world.
    sys.path.insert(0, os.path.join(HERE, ".."))
    import content
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "effects.toml"), "w", encoding="utf-8") as fh:
            fh.write(text)
        world = content.load(vault_dir=tmp)
        LEDGER.ok(len(world.rows("effect")) == 2077,
                  "and content.load() accepts all 2,077 -- the first "
                  "`client-table` rows this store has ever loaded",
                  f"census {world.census()}")
        row0 = world.get("effect", "0")
        LEDGER.ok(row0["name_id"] == 78727 and row0["id"] == 0,
                  "row 0 reads back as the client has it",
                  f"name_id {row0['name_id']} -- a string ID, not a string: "
                  f"ArenaNet's text stays in the owner's archive")
        LEDGER.ok(world.get("effect", "2036")["id"] == 2077,
                  "and the one hole survives the round trip intact",
                  "recorded as measured rather than repaired")

    # A row stripped of its build must NOT load: the check that condition 2 is
    # enforced rather than merely satisfied.
    broken = text.replace(f"build = {pinned.BUILD}, ", "", 1)
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "effects.toml"), "w", encoding="utf-8") as fh:
            fh.write(broken)
        try:
            content.load(vault_dir=tmp)
            ok = False
        except content.ContentError as exc:
            ok = "build" in str(exc)
        LEDGER.ok(ok, "a row with the build removed is REFUSED by content.py",
                  "condition 2 is enforced at load, not asserted in prose -- "
                  "and this proves the 2,077 above passed it rather than "
                  "skipped it")


def section_judgements(pe, by):
    print("\n9. the judgements this corpus was asked to confirm or correct")
    import skilltable

    # s_energyTable: skilltable.py approximates it with two magic numbers.
    # Located from s_skill's base backwards -- the array is the reason s_skill
    # has no left-edge witness, so this closes that loop rather than leaving it
    # as an assertion in a docstring.
    base, count, _ = skilltable.locate_table(pe.data)
    sentinel = pe.data.rfind(b"\xff\xff\xff\xff", base - 256, base)
    energy_base = sentinel - 18 * 4
    table = [struct.unpack_from("<I", pe.data, energy_base + 4 * i)[0]
             for i in range(19)]
    LEDGER.ok(table[:18] == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 25, 40, 60,
                             90, 135, 200] and table[18] == 0xFFFFFFFF,
              "s_energyTable is 18 values and an FF FF FF FF terminator, and it "
              "is what sits between the previous string and s_skill",
              f"{table[:18]}")
    raws = {pe.data[base + i * skilltable.RECORD_SIZE + 0x35] for i in range(count)}
    LEDGER.ok(max(raws) == 12,
              "no shipped skill row carries an energy code above 12",
              f"codes present: {sorted(raws)}")
    LEDGER.ok(all(skilltable.decode_energy(r) == table[r] for r in raws),
              "so skilltable.decode_energy agrees with the real table on 0 of "
              f"{count} disagreements -- the approximation is exactly right on "
              "the shipped corpus",
              "and becomes wrong the moment a skill costs 40 energy or more, "
              "which is a reskin arc away, not a bug today")

    # The four symbols that are not tables at all.
    for sym in ("s_avoidCount", "s_sortedList", "s_refCountAlert", "s_indexTotal"):
        LEDGER.ok(pe.data.count(f"arrsize({sym})".encode()) == 0,
                  f"{sym} never appears inside arrsize(), so it is not an array",
                  "it is a scalar or a container object; there is nothing here "
                  "to extract")
    named = sum(1 for s in EXPECTED
                if pe.data.count(f"arrsize({s})".encode()) >= 1)
    LEDGER.ok(named >= 8,
              "and the arrsize test is not vacuous: corpus symbols DO appear "
              "that way",
              f"{named} of {len(EXPECTED)} -- a predicate that says no to "
              f"everything says nothing")

    # s_charCondition is a name vocabulary and nothing more.
    t = by["s_charCondition"]
    vals = [struct.unpack_from("<I", pe.data, t.base + 4 * i)[0]
            for i in range(t.count)]
    LEDGER.ok(t.stride == 4 and all(0 < v < 1 << 24 for v in vals)
              and vals == sorted(vals),
              "s_charCondition is 9 ascending string ids and carries no "
              "duration, magnitude or stack rule",
              f"{vals} -- a 4-byte record has room for exactly one field, so "
              f"there is nothing here that could block R4b")


def main():
    print("consttable: the Gw\\Const table locator, its closure and its refusals.")
    try:
        section_positive()
        section_anchor_refusals()
        section_wrong_stride()
        section_shape_and_pad()
        section_left_edge()
        pe = client()
        if pe is None:
            LEDGER.skip("the corpus, the cross-tool checks, the census, the "
                        "s_effect overlay and the judgements",
                        "no pristine client in the vault -- sections 5-9 are "
                        "about ArenaNet's own layout and cannot be simulated")
        else:
            by = section_corpus(pe)
            section_cross_tools(pe, by)
            section_census(pe, by)
            section_worlddata(pe, by)
            section_effect_toml(pe, by)
            section_judgements(pe, by)
    finally:
        for p in _TMP:
            try:
                os.unlink(p)
            except OSError:
                pass
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
