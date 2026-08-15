#!/usr/bin/env python3
"""Check the `s_attribPoints` locator, and the off-by-one it corrects.

    python toolkit/clientscan/test_attribpoints.py

WHY THIS FILE IS MOSTLY SABOTAGE. The number under test -- `arrsize` is 13 --
replaced a 14 that had been in `consttable.py` for days, and the 14 was not a
typo: it CLOSED on its anchor, it had a code reference behind it, and the row
carrying it noted the anomaly it caused ("the leading 5 ... is what `dead data`
looks like from the outside") without that being enough to overturn it. So a
run of this file that merely confirms 13 would be worth about as much as the
run that confirmed 14. Sections 3 and 4 break each structural leg on a
synthetic image and require the locator to REFUSE, which is the only evidence
that the legs are load-bearing rather than decorative.

THE CROSS-BUILD SECTION IS THE OTHER HALF. Section 2 runs the locator over
every ArenaNet build in `pinned.BUILDS` and requires the same 13, the same
twelve costs and the same sentinel from all of them -- with the base at a
DIFFERENT address on the oldest build, which is what distinguishes a structural
locator from an address that happens to still work. `test_srctree.py` is the
pattern.

WHAT IT WOULD MEAN IF THIS GOES RED. Not "the tool broke". `arrsize` is a bound
the server codes against: `authsrv.ATTRIBUTE_RANK_MAX = 12` is `arrsize - 1`,
and 0x003A's rank column is refused against it. A build that moves this number
moves what the client will accept, and `attribute_columns` needs to hear about
it before a session does. That is not hypothetical -- the crash that produced
this file is what a rank past this bound looks like from the player's side
(studies/combat/PLAN.md 14).

READ-ONLY. Opens the vaulted pristine clients and writes nothing but temp
fixtures of its own making.
"""

import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import attribpoints                                              # noqa: E402
import checks                                                    # noqa: E402
import pinned                                                    # noqa: E402

# Set from a real green run on 2026-08-15 with all three vaulted builds
# present: 6 on the pinned client, 3 builds + the moved-address check, 3
# synthetic positives, 7 sabotages = 20.
#
# A vault missing a build SKIPS it by name and then goes RED on the floor,
# which is deliberate and follows `test_consttable.py`: the cross-build
# agreement IS the claim that this locator is structural, so a run that could
# not make it has not checked the thing this file is for. The skip lines say
# which build was absent, so the red names its own cause.
LEDGER = checks.Ledger("attribpoints", floor=20)

# UPSTREAM, and deliberately NOT read from the table under test: these are the
# published per-rank attribute-point costs any Guild Wars player can read off
# the attribute panel, and 97 is the number every build guide quotes for a
# rank-12 attribute. If the locator ever drifts onto a lookalike run of dwords,
# this is the check that does not move with it.
RETAIL_COSTS = [1, 2, 3, 4, 5, 6, 7, 9, 11, 13, 16, 20]
RETAIL_TOTAL = 97

IMAGE_BASE = 0x00400000
TEXT_RVA, TEXT_OFF, TEXT_SIZE = 0x1000, 0x400, 0x400
RDATA_RVA, RDATA_OFF, RDATA_SIZE = 0x2000, 0x800, 0x800

_TMP = []


# ------------------------------------------------------- synthetic fixture

def build_image(rdata: bytes, text: bytes) -> str:
    """A minimal PE32 carrying a planted .rdata and .text. Same shape as
    `test_consttable.py`'s fixture, for the same reason: `gwpe.PE` parses a
    real header, so a bag of bytes would exercise a different path."""
    e = 0x80
    hdr = bytearray(b"\x00" * RDATA_OFF)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, e)
    hdr[e:e + 4] = b"PE\x00\x00"
    struct.pack_into("<H", hdr, e + 4, 0x014C)
    struct.pack_into("<H", hdr, e + 6, 2)
    struct.pack_into("<H", hdr, e + 20, 0xE0)
    struct.pack_into("<H", hdr, e + 24, 0x010B)
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
    fd, path = tempfile.mkstemp(suffix=".exe", prefix="attribpoints_")
    os.write(fd, bytes(body))
    os.close(fd)
    _TMP.append(path)
    return path


def synth(arrsize=13, bias=4, slot_count=8, values=None, sentinel=-1,
          slot_gap=0, sites=2, x3=True):
    """An image reproducing the client's layout, with one knob per leg.

    .rdata:  [s_appearanceSlot: slot_count x 12][s_attribPoints][CharData.cpp]
    .text:   the two accessors, `cmp esi, arrsize` / `mov eax,[esi*4 + disp]`,
             plus one s_appearanceSlot accessor for the left-edge witness.

    Defaults reproduce the real client; every named argument breaks exactly
    one leg so section 3 can require a refusal per leg.
    """
    values = RETAIL_COSTS[:arrsize - 1] if values is None else values
    slot_base_off = 0x10
    slot_bytes = slot_count * attribpoints.SLOT_STRIDE
    base_off = slot_base_off + slot_bytes + slot_gap

    rd = bytearray(b"\x00" * RDATA_SIZE)
    for i in range(slot_count * 3):                       # 3 columns of dwords
        struct.pack_into("<I", rd, slot_base_off + 4 * i, (i % 7) + 1)
    body = list(values) + [sentinel]
    for i, v in enumerate(body[:arrsize]):
        struct.pack_into("<i", rd, base_off + 4 * i, v)
    anchor_off = base_off + arrsize * 4
    rd[anchor_off:anchor_off + len(attribpoints.FILE_ANCHOR)] = \
        attribpoints.FILE_ANCHOR
    expr_off = anchor_off + len(attribpoints.FILE_ANCHOR) + 4
    rd[expr_off:expr_off + len(attribpoints.EXPR_POINTS)] = \
        attribpoints.EXPR_POINTS
    slot_expr_off = expr_off + len(attribpoints.EXPR_POINTS) + 4
    rd[slot_expr_off:slot_expr_off + len(attribpoints.EXPR_SLOT)] = \
        attribpoints.EXPR_SLOT

    def va(off):
        return IMAGE_BASE + RDATA_RVA + off

    def accessor(bound, expr_va, disp, sib):
        # push <line>; mov edx,<file>; mov ecx,<expr>; call rel32; mov <reg>,[ix*4+disp]
        return (bytes([0x83, 0xFE, bound, 0x72, 0x14, 0x6A, 0xCA, 0xBA])
                + struct.pack("<I", va(anchor_off))
                + b"\xb9" + struct.pack("<I", expr_va)
                + b"\xe8" + struct.pack("<i", 0x20)
                + bytes([0x8B, 0x04, sib]) + struct.pack("<I", disp))

    tx = bytearray()
    for k in range(sites):                       # the biased one, then the plain
        tx += accessor(arrsize, va(expr_off),
                       va(base_off) - (bias if k == 0 else 0), 0xB5)
        tx += b"\xcc" * 8
    # s_appearanceSlot's accessor: bound, the x3, and an edi*4 column load.
    tx += bytes([0x83, 0xFE, slot_count, 0x72, 0x14, 0x6A, 0xA5, 0xBA])
    tx += struct.pack("<I", va(anchor_off))
    tx += b"\xb9" + struct.pack("<I", va(slot_expr_off))
    tx += b"\xe8" + struct.pack("<i", 0x20)
    if x3:
        tx += bytes([0x8D, 0x3C, 0x76])                    # lea edi,[esi+esi*2]
    tx += bytes([0x8B, 0x0C, 0xBD]) + struct.pack("<I", va(slot_base_off))
    return build_image(bytes(rd), bytes(tx))


def refuses(**kw):
    """(refused, detail) for one sabotaged fixture."""
    try:
        r = attribpoints.locate(attribpoints.Image(synth(**kw)))
    except attribpoints.NotFound as exc:
        return True, str(exc)[:90]
    return False, f"accepted: arrsize={r['arrsize']} base=0x{r['base']:08X}"


# ------------------------------------------------------------- the sections

def section_client():
    print("1. the pinned client, and what the number means")
    try:
        exe, why = pinned.find()
    except SystemExit as exc:
        LEDGER.skip("every check about ArenaNet's own client",
                    f"no pristine build in the vault: {exc}")
        return None
    print(f"   {exe}\n   ({why})")
    r = attribpoints.locate(attribpoints.Image(exe))

    LEDGER.ok(r["arrsize"] == attribpoints.EXPECTED_ARRSIZE,
              f"arrsize(s_attribPoints) is {attribpoints.EXPECTED_ARRSIZE}, "
              f"read out of the client's own bound check",
              f"`cmp esi, {r['arrsize']}` in BOTH accessors "
              f"(0x{r['sites']['biased']:08X}, 0x{r['sites']['unbiased']:08X})"
              f" -- not divided out of a span, which is how 14 happened")
    LEDGER.ok(r["costs"] == RETAIL_COSTS,
              "the twelve values are retail's published per-rank costs",
              f"{r['costs']} -- an UPSTREAM list this module does not read "
              f"from the table, so drifting onto other bytes reddens here")
    LEDGER.ok(sum(r["costs"]) == RETAIL_TOTAL,
              f"and they sum to {RETAIL_TOTAL}, retail's cost of a rank-12 "
              f"attribute",
              f"{sum(r['costs'])} -- the 14-element reading sums to 102")
    LEDGER.ok(r["values"][-1] == attribpoints.SENTINEL,
              "the last element is the -1 terminator, so index 12 is a legal "
              "read that means 'no rank above this'",
              f"{r['values']}")
    LEDGER.ok(r["biased_disp"] == r["base"] - 4,
              "the CharData:202 accessor addresses base-4 -- MSVC folding the "
              "`- 1` of `s_attribPoints[level - 1]` into the displacement",
              f"0x{r['biased_disp']:08X} vs base 0x{r['base']:08X}. Reading "
              f"THAT as the base is the whole of the old off-by-one")
    LEDGER.ok(r["neighbour_abuts"],
              "s_appearanceSlot's 8 records of 12 bytes end exactly on the "
              "base -- an independent left edge, from a different table",
              f"0x{r['neighbour']['base']:08X} + {r['neighbour']['count']}"
              f"*{attribpoints.SLOT_STRIDE} = 0x{r['neighbour_end']:08X}")
    return r


def section_cross_build(pinned_result):
    print("\n2. every build in the vault, which is what makes it structural")
    seen = []
    for b in pinned.BUILDS:
        try:
            exe, _ = pinned.find(build=b.number)
        except SystemExit as exc:
            LEDGER.skip(f"build {b.number}", f"not in the vault: {exc}")
            continue
        r = attribpoints.locate(attribpoints.Image(exe))
        seen.append((b.number, r))
        LEDGER.ok(r["arrsize"] == attribpoints.EXPECTED_ARRSIZE
                  and r["costs"] == RETAIL_COSTS
                  and r["values"][-1] == attribpoints.SENTINEL,
                  f"build {b.number}: {r['arrsize']} x 4 at "
                  f"0x{r['base']:08X}, the same twelve costs and sentinel")
    if len(seen) < 2:
        LEDGER.skip("the moved-address check",
                    f"only {len(seen)} build(s) available; two are needed for "
                    f"'the address moved and the answer did not' to mean "
                    f"anything")
        return
    bases = {n: r["base"] for n, r in seen}
    LEDGER.ok(len(set(bases.values())) > 1,
              "and the base is at DIFFERENT addresses across builds, so the "
              "agreement above is structural rather than an address that "
              "happens to survive",
              ", ".join(f"{n}: 0x{b:08X}" for n, b in bases.items()))


def section_synthetic_positive():
    print("\n3. the fixture reproduces the client, before anything breaks it")
    r = attribpoints.locate(attribpoints.Image(synth()))
    LEDGER.ok(r["arrsize"] == 13, "a clean synthetic image resolves to 13",
              "a locator that refuses everything would pass section 4 "
              "trivially, so this is what stops that")
    LEDGER.ok(r["costs"] == RETAIL_COSTS and r["neighbour_abuts"],
              "with the same costs and a closing left edge")
    r2 = attribpoints.locate(attribpoints.Image(synth(arrsize=9)))
    LEDGER.ok(r2["arrsize"] == 9,
              "and a fixture built at a DIFFERENT arrsize reports 9, not 13",
              "the tool reads the bound; it does not know the answer. A "
              "hardcoded 13 would pass every other check in this file")


def section_sabotage():
    """One broken leg per case. Each must REFUSE, not report a number.

    The refusals are what the 14 never had to survive: `consttable.py` could
    not refuse, because with a free left edge every count closes on something.
    """
    print("\n4. break one leg at a time; every case must refuse")
    cases = [
        (dict(bias=0),
         "both accessors unbiased -- the 4-byte gap that identifies the true "
         "base is gone"),
        (dict(bias=8),
         "an 8-byte bias, so neither displacement can be trusted as the base"),
        (dict(sites=1),
         "only one accessor, so the biased/unbiased pair cannot be formed"),
        (dict(sentinel=7),
         "no -1 terminator"),
        (dict(values=[1, 2, 3, 9, 4, 5, 6, 7, 11, 13, 16, 20]),
         "a value run that is not strictly increasing"),
        (dict(slot_gap=8),
         "the neighbour's right edge no longer lands on the base"),
        (dict(x3=False),
         "no `lea edi,[esi+esi*2]`, so stride 12 would be an assumption"),
    ]
    for kw, why in cases:
        ref, detail = refuses(**kw)
        LEDGER.ok(ref, f"REFUSES {why}", detail)


def main():
    print("attribpoints: s_attribPoints, its arrsize, and the 14 it replaces.\n")
    try:
        r = section_client()
        section_cross_build(r)
        section_synthetic_positive()
        section_sabotage()
    finally:
        for p in _TMP:
            try:
                os.unlink(p)
            except OSError:
                pass
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
