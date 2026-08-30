"""CANCELWALK-R7's guard: the addresses are ArenaNet's, the verdict is ours.

Two halves, and the first is the one that matters. `gatetrace.py` reads two
operands out of a running client at one instruction and decides the arc's
open question from them, so **a wrong address does not error -- it returns a
confident number that never changes**, which reads exactly like "the walk-start
never ran" and would be indistinguishable from the finding. So section 1
ENCODES the expected instruction bytes FROM the module's own constants and
matches them against the pinned image: change `OFF_STATUS` to 0x110 and the
expected encoding becomes `8b 83 10 01 00 00`, which is not what the image
holds, and this file goes red. Comparing a literal against a copy of itself
would pass forever.

THAT IS THE PARAGRAPH THIS FILE HAS ALWAYS OPENED WITH, AND UNTIL 2026-08-30
IT WAS TRUE OF THE WRONG CONSTANTS. `buildpins.py --live` charges `gatetrace`
four build-coupled pins -- VA_APPLIER, VA_GATE_BAIL, VA_NAVMESH_EXIT and BUILD
-- and section 1 guarded none of them: the four derived rows read their
ADDRESSES from literals typed here, the three rows that did use the counted VAs
had hand-typed patterns matching 14,765, 94 and 531 places in .text, and the
control moved OFF_STATUS. MEASURED: all three VAs pointed at decoys four
megabytes away, 9 of 9 PASS. Section 1 now (a) hangs the four derived rows off
VA_APPLIER as offsets, (b) widens the three VA patterns until each occurs
EXACTLY ONCE in .text and re-measures that every run rather than asserting it,
and (c) carries one control per counted pin, BUILD included -- which is what
`pinned.find(gatetrace.BUILD)` is for, since a guard aimed at one image by a
hardcoded directory name can never redden on a rebase.

The second half drives the pure verdict functions over every combination they
can meet, including the ones where the client CONTRADICTS the operand read --
because that contradiction is the file's own falsifier and a version that
quietly agreed with itself would be worthless.

No client. Reads the pinned exe, and -- for the BUILD control, which needs a
second image to be a control at all -- whatever other builds the vault holds.
Stdlib only.
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import checks     # noqa: E402
import gatetrace  # noqa: E402

# FLOOR 35, and the number is the BARE-MACHINE one on purpose. A green run with
# the pinned snapshot present executes 51; section 1's sixteen checks are the
# difference -- 15 where the vault holds no build but the pinned one, since the
# BUILD control then declares a skip instead. It was 44 until 2026-08-30, when
# paying the build-pin census bill added seven: three uniqueness measurements,
# one control per counted VA, and the BUILD control.
# THIS WAS WRONG UNTIL AN ADVERSARIAL REVIEW CAUGHT IT, and the way it was
# wrong is worth keeping: the floor was 42 with section 1 calling
# `LEDGER.skip(..., 9)` in the belief that a skip LOWERS the floor by its
# count. It does not -- `Ledger.skip(label, why)` takes two strings, records a
# line, and lowers nothing -- so on any machine without the vault snapshot
# this file was RED (33 of a declared 42) while five documents claimed it
# "drops to 33 on a bare machine". The floor is now the number a bare machine
# really executes, so the file is honest in both configurations.
LEDGER = checks.Ledger("gatetrace (CANCELWALK-R7)", floor=35)
check = LEDGER.ok


# ---------------------------------------------------------------------------
# WHAT THE EXPECTATIONS BELOW ARE ANCHORED TO. Read this before adding a row.
#
# `buildpins.py --live` charges `gatetrace.py` FOUR class-(a) build-coupled
# constants: VA_APPLIER, VA_GATE_BAIL and VA_NAVMESH_EXIT at :142-144, and
# BUILD at :160. Until 2026-08-30 this section guarded none of them.
#
#   * the four rows that DERIVE their bytes from module constants read their
#     ADDRESSES from literals typed here (0x0081A925/931/93C/946), and not one
#     of those is a counted pin;
#   * the three rows that DO use the counted VAs had hand-typed patterns --
#     `55 8b ec`, `ff 73 14`, `5f 5e 33 c0` -- which occur 14,765, 94 and 531
#     times in .text. MEASURED: pointing all three VAs at decoys four megabytes
#     away left the section 9 of 9 GREEN, under a control line reading "the
#     byte checks above are load-bearing";
#   * and the control moved OFF_STATUS, which is real but is not one of the
#     four.
#
# The repair has three parts and they are separable: addresses that hang off
# the pin (below), patterns that IDENTIFY rather than merely match (measured to
# occur exactly once in .text, and the section re-measures it every run rather
# than trusting this comment), and a control per counted pin.
# ---------------------------------------------------------------------------

# The four gate instructions, as offsets from the applier's ENTRY instead of as
# absolute VAs. That is the whole of the first part: written this way they hang
# off VA_APPLIER, so moving it reddens five rows rather than none. It also
# takes four class-(c) literals back out of this file -- an offset inside a
# function is not a fact about a build in the way its load address is.
OFF_GATE_LOAD = 0x35        # mov eax,[ebx+OFF_STATUS]   -- GATE A/C's operand
OFF_GATE_A = 0x41           # test eax,BIT_GATE_A
OFF_GATE_B = 0x4C           # test byte[ebx+OFF_FLAGBYTE],BIT_GATE_B
OFF_GATE_C = 0x56           # shr eax,<log2 BIT_GATE_C>

# The two callees the applier's exits reach, read out of the pinned image and
# used to ASSEMBLE the expected `e8 <rel32>` FROM the VA under test. rel32 is
# relative, so this is what makes those two rows position-DEPENDENT rather than
# merely byte-matching: the identical run of bytes read at any other address
# decodes to a different callee and the expectation misses.
VA_BAIL_CALLEE = 0x005FCA80     # the gate bail's helper; 3 call sites in .text
VA_SECURITY_CHECK = 0x005AE7A9   # __security_check_cookie; 3,175 call sites

Row = collections.namedtuple("Row", "key va pattern what pin unique")


def _rel32(target, site):
    """The `e8 <rel32>` reaching `target` from a call instruction at `site`."""
    return b"\xe8" + struct.pack("<i", target - (site + 5))


def _rows():
    """The expectation table, REBUILT from the module's constants on every call.

    Rebuilt rather than built once because the controls at the end of the
    section move a constant and then ask for the table again; a table captured
    at import time would not notice, which is the same shape of mistake as
    comparing a literal against a copy of itself.

    `pin` names which counted constant the row rests on -- that is what lets a
    control assert "every row resting on VA_APPLIER went red" instead of
    hand-listing them. `unique` marks the rows whose pattern must be the only
    occurrence in .text.
    """
    app = gatetrace.VA_APPLIER
    return [
        # THE FIRST FOUR ARE BUILT, NOT TYPED. Each pattern is assembled from
        # the module constant it guards, so the check cannot pass with the
        # constant wrong: change OFF_STATUS to 0x110 and the expected encoding
        # becomes `8b 83 10 01 00 00`, which is not what sits in the image.
        # Their ADDRESSES are now assembled too, from VA_APPLIER.
        Row("gate-load", app + OFF_GATE_LOAD,
            b"\x8b\x83" + struct.pack("<I", gatetrace.OFF_STATUS),
            f"mov eax,[ebx+{gatetrace.OFF_STATUS:#x}] -- GATE A/C's operand "
            f"load, at VA_APPLIER+{OFF_GATE_LOAD:#x}",
            "VA_APPLIER", False),
        Row("gate-a", app + OFF_GATE_A,
            b"\xa9" + struct.pack("<I", gatetrace.BIT_GATE_A),
            f"test eax,{gatetrace.BIT_GATE_A:#x} -- GATE A, at "
            f"VA_APPLIER+{OFF_GATE_A:#x}",
            "VA_APPLIER", False),
        Row("gate-b", app + OFF_GATE_B,
            bytes([0xF6, 0x43, gatetrace.OFF_FLAGBYTE, gatetrace.BIT_GATE_B]),
            f"test byte[ebx+{gatetrace.OFF_FLAGBYTE:#x}],"
            f"{gatetrace.BIT_GATE_B} -- GATE B, at VA_APPLIER+{OFF_GATE_B:#x}",
            "VA_APPLIER", False),
        Row("gate-c", app + OFF_GATE_C,
            bytes([0xC1, 0xE8, gatetrace.BIT_GATE_C.bit_length() - 1]),
            f"shr eax,{gatetrace.BIT_GATE_C.bit_length() - 1} -- GATE C's bit, "
            f"at VA_APPLIER+{OFF_GATE_C:#x}",
            "VA_APPLIER", False),

        # THE APPLIER'S ENTRY, and this one is hand-typed because it has to be:
        # nothing in `gatetrace` describes a prologue. So it is widened until it
        # IDENTIFIES. `55 8b ec` alone matches 14,765 places -- one in every 370
        # bytes of .text -- and the first 24 bytes still match TWO functions
        # (0x00754EF0 is a near-twin: same 0xC0 frame, same cookie load, same
        # first three reads). Thirty bytes, through the first spill, is the
        # shortest run that is unique, and the `unique` flag makes the section
        # re-measure that rather than take this comment's word for it.
        #
        # AND IT DOUBLES AS THE REBASE INSTRUMENT, which was not the intent and
        # is worth writing down. MEASURED 2026-08-30 against the two newer
        # vaulted builds: these thirty bytes occur exactly once in each of them
        # too -- 0x0081A940 on 38833, 0x0081A9C0 on 38849 -- and with
        # VA_APPLIER moved there all four gate rows match at the SAME offsets.
        # Both exits are still where they were relative to it too: `ff 73 14
        # e8 ..` at +0x41F and the whole epilogue at +0x40A, `ret 0x10`
        # included. Their ROWS would not match as written, because the two
        # rel32 displacements differ -- as they must when a function moves --
        # and that is the measurement, not a caveat on it. So the applier
        # relocated as a unit twice without changing shape, and a rebase is:
        # search .text for this pattern, take the single hit, and derive the
        # rest. That is an OBSERVATION about two updates, not a promise about
        # the next one -- the section is still required to go red first.
        Row("applier", app,
            b"\x55\x8b\xec"                      # push ebp; mov ebp,esp
            b"\x81\xec\xc0\x00\x00\x00"          # sub esp,0xC0
            b"\xa1\x40\x44\xbf\x00"              # mov eax,[__security_cookie]
            b"\x33\xc5"                          # xor eax,ebp
            b"\x89\x45\xfc"                      # mov [ebp-4],eax
            b"\x8b\x45\x0c"                      # mov eax,[ebp+0xC]
            b"\x53\x56"                          # push ebx; push esi
            b"\x89\x85\x64\xff\xff\xff",         # mov [ebp-0x9C],eax
            "the applier's entry: prologue, 0xC0 frame, cookie, first spill",
            "VA_APPLIER", True),

        # THE SHARED GATE BAIL. `ff 73 14` matches 94 places; the call that
        # follows it is what says WHICH bail, and the module's own docstring
        # already names the callee ("the gate bail at 0x0081AD0F calls
        # 0x005FCA80 and returns 1"). Assembling the rel32 from VA_GATE_BAIL
        # turns that sentence into the check.
        Row("gate-bail", gatetrace.VA_GATE_BAIL,
            b"\xff\x73\x14"                      # push [ebx+0x14]
            + _rel32(VA_BAIL_CALLEE, gatetrace.VA_GATE_BAIL + 3),
            f"the shared gate bail: push [ebx+0x14]; call "
            f"{VA_BAIL_CALLEE:#010x}",
            "VA_GATE_BAIL", True),

        # THE NAVMESH-EMPTY EXIT, the whole epilogue rather than its first four
        # bytes (`5f 5e 33 c0` matches 531 places). Two of its pieces are
        # derived: the rel32 to __security_check_cookie, from the VA; and the
        # `ret` imm16, from ARG_MT_ESP_OFF. The second is not a coincidence to
        # be tidied away -- the applier takes four dword args, so the one
        # pushed first, `mt`, sits at [esp+0x10] at the entry breakpoint and
        # `ret 0x10` pops exactly those four. Move ARG_MT_ESP_OFF and this row
        # goes red, which is correct: the module would be reading `mt` off the
        # wrong slot of a function that never had that shape.
        Row("navmesh-exit", gatetrace.VA_NAVMESH_EXIT,
            b"\x5f\x5e\x33\xc0"                  # pop edi; pop esi; xor eax,eax
            b"\x5b"                              # pop ebx
            b"\x8b\x4d\xfc\x33\xcd"              # mov ecx,[ebp-4]; xor ecx,ebp
            + _rel32(VA_SECURITY_CHECK, gatetrace.VA_NAVMESH_EXIT + 10)
            + b"\x8b\xe5\x5d"                    # mov esp,ebp; pop ebp
            + b"\xc2" + struct.pack("<H", gatetrace.ARG_MT_ESP_OFF),
            f"the navmesh-empty exit: xor eax,eax through "
            f"ret {gatetrace.ARG_MT_ESP_OFF:#x}",
            "VA_NAVMESH_EXIT", True),
    ]


def _row(key):
    return next(r for r in _rows() if r.key == key)


def _va_to_off(data, va):
    """File offset for a VA, via the PE section table (struct, no pefile)."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    rva = va - base
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        sva = struct.unpack_from("<I", data, o + 12)[0]
        vsz = struct.unpack_from("<I", data, o + 8)[0]
        raw = struct.unpack_from("<I", data, o + 20)[0]
        if sva <= rva < sva + vsz:
            return raw + (rva - sva), base
    return None, base


def _text_span(data):
    """(.text as bytes, the VA of its first byte) -- the uniqueness haystack.

    Uniqueness is measured in .text alone on purpose: it is the only section a
    code address can live in, so counting a run of bytes that also happens to
    appear in .rdata would understate how well the pattern discriminates.
    """
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    for i in range(nsec):
        o = pe + 24 + optsz + 40 * i
        if data[o:o + 8].rstrip(b"\x00") != b".text":
            continue
        sva = struct.unpack_from("<I", data, o + 12)[0]
        rsz = struct.unpack_from("<I", data, o + 16)[0]
        raw = struct.unpack_from("<I", data, o + 20)[0]
        return data[raw:raw + rsz], base + sva
    return b"", base


def _occurrences(text, text_va, pattern):
    """Every VA in .text where `pattern` sits. A measurement, not a claim."""
    out, i = [], text.find(pattern)
    while i != -1:
        out.append(text_va + i)
        i = text.find(pattern, i + 1)
    return out


def _row_matches(data, row):
    """Does this image hold the row's expected bytes at the row's VA?"""
    off, _base = _va_to_off(data, row.va)
    if off is None:
        return False
    return data[off:off + len(row.pattern)] == row.pattern


def section_addresses():
    print("1. every address and offset re-derived from ArenaNet's own bytes")
    try:
        sys.path.insert(0, HERE)
        import pinned
    except Exception as exc:
        LEDGER.skip("section 1 (address bytes)",
                    f"pinned.py did not import: {exc}")
        print(f"   [SKIP] pinned.py did not import: {exc}")
        return

    # THE MODULE'S OWN CONSTANT SELECTS THE IMAGE, since 2026-08-30. This was
    # `os.path.join(root, "client", "2026-07-29_221c13772c7a", "Gw.exe")` under
    # an `os.path.exists`, and that is DEFECT 2: `gatetrace.BUILD` was read by
    # NOTHING -- `git grep gatetrace.BUILD` came back empty, while the positive
    # control `git grep atex.TABLES_BUILD` returned six -- so bumping it after a
    # client update moved nothing and this guard could never be aimed at the
    # newer image it exists to redden against. It is `atex.TABLES_BUILD`'s own
    # 2026-08-15 fix (`studies/crossbuild/FINDINGS.md` §7.9), one build later.
    # `find()` also hashes what it hands back and refuses a copy that is neither
    # pristine nor a registered patch, which `os.path.exists` cannot.
    #
    # The two ways this can go wrong are kept apart deliberately:
    #   BUILD names a build the registry does not know -> this file's bug, FAIL
    #   a known build that is not in this vault        -> bare machine,   SKIP
    # The first used to be indistinguishable from the second, which is the
    # "refuses rather than silently skipping" half of the repair.
    try:
        build = pinned.select(gatetrace.BUILD)
    except SystemExit as exc:
        check(False,
              f"gatetrace.BUILD ({gatetrace.BUILD}) names a build pinned.py "
              f"knows -- no image can be selected otherwise, and a SKIP here "
              f"would read exactly like a bare machine",
              str(exc).splitlines()[0])
        return
    try:
        exe, why = pinned.find(build)
    except SystemExit as exc:
        LEDGER.skip("section 1 (address bytes)",
                    f"no vaulted client for build {gatetrace.BUILD}: "
                    f"{str(exc).splitlines()[0]}")
        print(f"   [SKIP] no pinned Gw.exe for build {gatetrace.BUILD} "
              f"-- 16 checks not run (15 where the vault holds no other "
              f"build)")
        return
    print(f"    image: build {gatetrace.BUILD} -- {why}")
    with open(exe, "rb") as fh:
        data = fh.read()
    text, text_va = _text_span(data)

    for row in _rows():
        off, _base = _va_to_off(data, row.va)
        got = data[off:off + len(row.pattern)] if off is not None else b""
        check(got == row.pattern, f"{row.va:#010x}: {row.what}",
              f"want {row.pattern.hex()} got {got.hex()}")

    # THE IDENTIFICATION, and it is the difference between this section and the
    # one it replaces. A pattern that occurs exactly once in .text cannot be
    # satisfied by any address but its own, so this is the general statement
    # the three controls below then demonstrate. The count is PRINTED because
    # the number is the claim: `55 8b ec` was 14,765 and read as a check.
    for row in _rows():
        if not row.unique:
            continue
        hits = _occurrences(text, text_va, row.pattern)
        check(hits == [row.va],
              f"{row.va:#010x}: its {len(row.pattern)}-byte pattern is UNIQUE "
              f"in .text -- {len(hits)} occurrence(s) in {len(text):,} bytes, "
              f"and it sits at this VA, so no other address can satisfy the "
              f"row above",
              f"hits {[hex(h) for h in hits]}")

    _off, base = _va_to_off(data, gatetrace.VA_APPLIER)
    check(base == gatetrace.IMAGE_BASE,
          f"the image base the VA table assumes ({gatetrace.IMAGE_BASE:#x}) is "
          f"the one the PE declares", f"PE says {base:#x}")

    # --- CONTROLS. A check that cannot fail is not a check ------------------
    # And a control that moves a constant NOBODY COUNTS is not a control: the
    # one that used to stand here moved OFF_STATUS, which is real but is not
    # one of the four pins `buildpins.py --live` charges this file for. Each of
    # those four now has one, and the decoys are the OTHER pins rather than
    # invented addresses -- a transposed constant is the error actually
    # available to a future editor, and it is a far nearer miss than the four-
    # megabyte decoys that used to pass.
    for pin, decoy_from in (("VA_APPLIER", "VA_NAVMESH_EXIT"),
                            ("VA_GATE_BAIL", "VA_NAVMESH_EXIT"),
                            ("VA_NAVMESH_EXIT", "VA_GATE_BAIL")):
        saved, decoy = getattr(gatetrace, pin), getattr(gatetrace, decoy_from)
        try:
            setattr(gatetrace, pin, decoy)
            resting = [r for r in _rows() if r.pin == pin]
            survived = [r.key for r in resting if _row_matches(data, r)]
        finally:
            setattr(gatetrace, pin, saved)
        # THE VACUITY GUARD IS PART OF THE CONTROL, not decoration. Two ways
        # this could pass while proving nothing: the decoy is another pin, so
        # collapsing two constants to the same value would make the move a
        # no-op; and a pin with no rows resting on it would trivially have none
        # survive -- which is EXACTLY the state this whole section was in
        # before 2026-08-30, when `resting` would have been empty for all three.
        vacuous = ("the decoy IS the pin" if decoy == saved else
                   "no row rests on this pin" if not resting else "")
        check(not survived and not vacuous,
              f"CONTROL: {pin} moved {saved:#010x} -> {decoy:#010x} and all "
              f"{len(resting)} row(s) resting on it go red",
              f"VACUOUS: {vacuous}" if vacuous
              else f"still matched: {survived}")

    # The old control, kept: the DERIVED half is load-bearing too, and the
    # sharpest way to say so is still to move the constant the encoding is
    # built from.
    saved = gatetrace.OFF_STATUS
    try:
        gatetrace.OFF_STATUS = 0x110
        moved = _row_matches(data, _row("gate-load"))
    finally:
        gatetrace.OFF_STATUS = saved
    check(not moved,
          "CONTROL: OFF_STATUS moved one dword to 0x110 no longer matches the "
          "image -- the derived byte patterns are load-bearing too")

    # AND THE FOURTH PIN. BUILD is only load-bearing if pointing it somewhere
    # else changes the answer, so: read every OTHER build this vault holds
    # through the same `pinned.find`, and require the rows to fail there. That
    # is the property DEFECT 2 removed -- with the snapshot path hardcoded, a
    # rebase could bump BUILD and this section would carry on reading 38797 and
    # printing green.
    others = []
    for b in pinned.BUILDS:
        if b.number == gatetrace.BUILD:
            continue
        try:
            others.append((b, pinned.find(b)[0]))
        except SystemExit:
            continue
    if not others:
        LEDGER.skip("CONTROL: gatetrace.BUILD",
                    f"this vault holds no build other than {gatetrace.BUILD}")
    else:
        survivors = []
        for b, path in others:
            with open(path, "rb") as fh:
                other = fh.read()
            kept = [r.key for r in _rows() if _row_matches(other, r)]
            if kept:
                survivors.append(f"build {pinned.name_of(b)}: {kept}")
        check(not survivors,
              "CONTROL: every row fails against the other vaulted build(s) "
              + ", ".join(pinned.name_of(b) for b, _ in others)
              + " -- these addresses really are build-coupled, so bumping "
                "gatetrace.BUILD after a client update reddens this section "
                "instead of silently re-aiming it",
              "; ".join(survivors))


def section_gate_verdict():
    print("\n2. gate_verdict: all eight operand combinations, in test order")
    A, B, C = (gatetrace.BIT_GATE_A, gatetrace.BIT_GATE_B, gatetrace.BIT_GATE_C)
    cases = [
        (0, 0, [], None),
        (A, 0, [gatetrace.GATE_A], gatetrace.GATE_A),
        (0, B, [gatetrace.GATE_B], gatetrace.GATE_B),
        (C, 0, [gatetrace.GATE_C], gatetrace.GATE_C),
        (A | C, 0, [gatetrace.GATE_A, gatetrace.GATE_C], gatetrace.GATE_A),
        (A, B, [gatetrace.GATE_A, gatetrace.GATE_B], gatetrace.GATE_A),
        (C, B, [gatetrace.GATE_B, gatetrace.GATE_C], gatetrace.GATE_B),
        (A | C, B, [gatetrace.GATE_A, gatetrace.GATE_B, gatetrace.GATE_C],
         gatetrace.GATE_A),
    ]
    for word, byte, bail, first in cases:
        v = gatetrace.gate_verdict(word, byte)
        check(v["gates_bail"] == bail and v["first_bail"] == first,
              f"status={word:#05x} flag={byte:#04x} -> bails {bail or 'none'}, "
              f"first {first or 'none'}", f"got {v}")
    # ORDER IS THE CLAIM, not just membership: the applier tests A, then B,
    # then C, and only the FIRST one reached explains the frame.
    v = gatetrace.gate_verdict(A | C, B)
    check(v["gates_bail"].index(gatetrace.GATE_A) == 0
          and v["gates_bail"].index(gatetrace.GATE_B) == 1
          and v["gates_bail"].index(gatetrace.GATE_C) == 2,
          "with all three set the list is in the client's own test order "
          "A,B,C -- a set would lose the only thing that explains the frame")
    v = gatetrace.gate_verdict(None, None)
    check(v["why"] == "operands-unread" and v["gates_bail"] is None,
          "an unread operand yields no verdict at all rather than a "
          "plausible 'no gates set' -- a failed read must not read as a pass")
    v = gatetrace.gate_verdict(0, 0)
    check(v["predicted_exit"] is None,
          "no gate set predicts NO bail -- and deliberately does NOT predict a "
          "walk, because the navmesh query and the dedup are downstream")


def section_reconcile():
    print("\n3. reconcile: the file's own falsifier can fire")
    A = gatetrace.BIT_GATE_A
    bail = gatetrace.gate_verdict(A, 0)
    clear = gatetrace.gate_verdict(0, 0)

    ok, note = gatetrace.reconcile(bail, gatetrace.EXIT_GATE_BAIL)
    check(ok is True and gatetrace.GATE_A in note,
          "operands said GATE A bails and the client bailed -- agrees, and "
          "the note names which gate", note)
    ok, note = gatetrace.reconcile(clear, gatetrace.EXIT_UNSEEN)
    check(ok is True, "no gate set and no bail seen -- agrees", note)
    ok, note = gatetrace.reconcile(clear, gatetrace.EXIT_NAVMESH)
    check(ok is True and "navmesh" in note,
          "no gate set and the navmesh came back empty -- agrees, and this is "
          "the H7 shape", note)
    # THE TWO DISAGREEMENTS. These are why the entry read and the exit
    # breakpoints are both armed; a tool that could not report them would be
    # agreeing with itself by construction.
    ok, note = gatetrace.reconcile(bail, gatetrace.EXIT_NAVMESH)
    check(ok is False and "predicted" in note,
          "operands said BAIL but the client left via the navmesh exit -- "
          "DISAGREES, loudly", note)
    ok, note = gatetrace.reconcile(bail, gatetrace.EXIT_UNSEEN)
    check(ok is False and "SET but no bail" in note,
          "operands said BAIL and no bail fired -- DISAGREES", note)
    ok, note = gatetrace.reconcile(clear, gatetrace.EXIT_GATE_BAIL)
    check(ok is False,
          "gates all clear yet the client bailed -- DISAGREES, and this one "
          "would mean the operands were read off the wrong object", note)
    ok, note = gatetrace.reconcile(gatetrace.gate_verdict(None, None),
                                   gatetrace.EXIT_UNSEEN)
    check(ok is None and note == "operands-unread",
          "an unread operand yields NO agreement verdict -- not True, not "
          "False, a third thing", note)


def section_run_verdict():
    print("\n4. run_verdict: the control rule, enforced not described")
    rc, head = gatetrace.run_verdict(0, 5)
    check(rc == 2 and "VOID" in head and "NOTHING" in head,
          "no control hit is a REFUSAL even with applier hits recorded -- the "
          "route's own known failure mode is silence, so silence cannot be "
          "reported as a null", head)
    rc, head = gatetrace.run_verdict(0, 0)
    check(rc == 2, "no control and no applier is the same refusal", head)
    rc, head = gatetrace.run_verdict(1, 0)
    check(rc == 1 and "READABLE and EMPTY" in head,
          "control fired and the applier did not: a REAL measurement, and it "
          "is labelled differently from the void case", head)
    rc, head = gatetrace.run_verdict(1, 3)
    check(rc == 0 and "3 applier hit" in head,
          "control fired and the applier ran -- readable", head)


def section_addr_math():
    print("\n5. address resolution against ASLR")
    got = gatetrace.resolve_addrs(0x00400000)
    check(got["applier"] == gatetrace.VA_APPLIER,
          "at the declared image base the runtime address IS the VA")
    rebased = gatetrace.resolve_addrs(0x10000000)
    check(rebased["applier"] == 0x10000000 + (gatetrace.VA_APPLIER
                                              - gatetrace.IMAGE_BASE),
          "a relocated module shifts every address by the same delta")
    check(rebased["gate_bail"] - rebased["applier"]
          == gatetrace.VA_GATE_BAIL - gatetrace.VA_APPLIER,
          "and the offsets between them are preserved")
    check(len(set(rebased.values())) == 3,
          "the three watched addresses are distinct -- two Dr slots on one "
          "address would silently halve the trace")


def section_hygiene():
    print("\n6. house rules")
    src = open(os.path.join(HERE, "gatetrace.py"), encoding="utf-8").read()
    import ast
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    local = {"arm64", "inject", "keytap", "vaultpath", "test_gatetrace",
             "checks", "gatetrace"}
    third = mods - local - set(sys.stdlib_module_names)
    check(not third,
          "gatetrace takes NO third-party import -- carve-out (1) names "
          "msghandler.py and codescan.py and this is neither, so it must load "
          "on a bare machine", f"third-party: {sorted(third)}")
    # THE REFUSAL IS THE SAFETY PROPERTY NOW, and it is checked by CALLING the
    # function rather than by grepping for a banner. Five measured blockers
    # live in the process half; until they are fixed, trace() must refuse.
    check(bool(gatetrace.UNSAFE_TO_RUN),
          "UNSAFE_TO_RUN is set -- the process half carries five measured "
          "blockers and must not be pointed at a client")
    try:
        gatetrace.trace(1234, 1, "nowhere")
        check(False, "trace() must REFUSE while UNSAFE_TO_RUN is set")
    except SystemExit as e:
        check("STATUS_WX86_SINGLE_STEP" in str(e)
              and "movetap" in str(e),
              "trace() refuses by raising, and the refusal names both the "
              "blocker that kills the client and the poll that replaces it -- "
              "a docstring warning above a main() that still runs is a file "
              "that gets run", str(e)[:90])
    check("DebugSetProcessKillOnExit" in src,
          "the kill-on-exit call is present (ORDERING is a known blocker, "
          "recorded in the docstring -- it is called before the attach, where "
          "it no-ops)")
    check("_disarm_slot" in src and "control" in src,
          "the control disarms after its first hit so it cannot flood the "
          "debugger loop")
    # The client is READ, never written. No memory-write or code-patch API may
    # appear in this file -- the whole licence for pointing it at a running
    # client is that it only reads.
    for banned in ("WriteProcessMemory", "VirtualProtectEx",
                   "CreateRemoteThread", "VirtualAllocEx"):
        check(banned not in src,
              f"{banned} appears nowhere -- R7 reads the client and never "
              f"writes it")


def main():
    section_addresses()
    section_gate_verdict()
    section_reconcile()
    section_run_verdict()
    section_addr_math()
    section_hygiene()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
