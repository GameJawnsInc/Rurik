"""CANCELWALK-R7's guard: the addresses are ArenaNet's, the verdict is ours.

Two halves, and the first is the one that matters. `gatetrace.py` reads two
operands out of a running client at one instruction and decides the arc's
open question from them, so **a wrong address does not error -- it returns a
confident number that never changes**, which reads exactly like "the walk-start
never ran" and would be indistinguishable from the finding. So section 1
ENCODES the expected instruction bytes FROM the module's own constants and
matches them against the pinned image: change `OFF_STATUS` to 0x110 and the
expected encoding becomes `8b 83 10 01 00 00`, which is not what sits at
0x0081A925, and this file goes red. Comparing a literal against a copy of
itself would pass forever.

The second half drives the pure verdict functions over every combination they
can meet, including the ones where the client CONTRADICTS the operand read --
because that contradiction is the file's own falsifier and a version that
quietly agreed with itself would be worthless.

No client, no vault snapshot beyond the pinned exe, stdlib only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import checks     # noqa: E402
import gatetrace  # noqa: E402

# FLOOR 42, read off the first green run with every section executing, never
# from a guess: 9 + 11 + 7 + 4 + 4 + 7 = 42 (addresses incl. the image base and
# the moved-constant control; the eight operand combinations plus test-order,
# unread and no-predict; the three agreements, three disagreements and the
# unread third thing; the four control-rule cases; four address-math; and the
# seven house rules, four of which are the write-API bans).
# Section 1 is the one that can legitimately not run (no vault snapshot); it
# declares LEDGER.skip(9) and the floor drops by that, so a bare machine is
# honest rather than either red or falsely green.
LEDGER = checks.Ledger("gatetrace (CANCELWALK-R7)", floor=42)
check = LEDGER.ok


def _pinned_exe():
    """The pinned pristine client, or None on a bare machine."""
    try:
        sys.path.insert(0, os.path.join(HERE, ".."))
        import vaultpath
        root = vaultpath.require_dir()
    except Exception:
        return None
    d = os.path.join(root, "client", "2026-07-29_221c13772c7a", "Gw.exe")
    return d if os.path.exists(d) else None


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


def section_addresses():
    print("1. every address and offset re-derived from ArenaNet's own bytes")
    exe = _pinned_exe()
    if exe is None:
        LEDGER.skip("no pinned client snapshot in the vault", 9)
        print("   [SKIP] no pinned Gw.exe -- 9 checks not run")
        return
    data = open(exe, "rb").read()

    # THE EXPECTATIONS ARE BUILT, NOT TYPED. Each pattern below is assembled
    # from the module constant it guards, so the check cannot pass with the
    # constant wrong. This is movetap section 5's rule, applied to the four
    # numbers R7's verdict actually rests on.
    status_disp = struct.pack("<I", gatetrace.OFF_STATUS)
    want = [
        # mov eax,[ebx+OFF_STATUS]  ->  8b 83 <disp32>
        (0x0081A925, b"\x8b\x83" + status_disp,
         f"mov eax,[ebx+{gatetrace.OFF_STATUS:#x}] -- GATE A/C's operand load"),
        # test eax,BIT_GATE_A  ->  a9 <imm32>
        (0x0081A931, b"\xa9" + struct.pack("<I", gatetrace.BIT_GATE_A),
         f"test eax,{gatetrace.BIT_GATE_A:#x} -- GATE A"),
        # test byte[ebx+OFF_FLAGBYTE],BIT_GATE_B  ->  f6 43 <disp8> <imm8>
        (0x0081A93C, bytes([0xF6, 0x43, gatetrace.OFF_FLAGBYTE,
                            gatetrace.BIT_GATE_B]),
         f"test byte[ebx+{gatetrace.OFF_FLAGBYTE:#x}],"
         f"{gatetrace.BIT_GATE_B} -- GATE B"),
        # shr eax,4 -- GATE C's bit index, encoded from BIT_GATE_C
        (0x0081A946, bytes([0xC1, 0xE8, gatetrace.BIT_GATE_C.bit_length() - 1]),
         f"shr eax,{gatetrace.BIT_GATE_C.bit_length() - 1} -- GATE C's bit"),
        (gatetrace.VA_APPLIER, b"\x55\x8b\xec",
         "the applier's own prologue (push ebp; mov ebp,esp)"),
        (gatetrace.VA_GATE_BAIL, b"\xff\x73\x14",
         "the shared gate bail (push [ebx+0x14])"),
        (gatetrace.VA_NAVMESH_EXIT, b"\x5f\x5e\x33\xc0",
         "the navmesh-empty exit (pop edi; pop esi; xor eax,eax)"),
    ]
    for va, pattern, what in want:
        off, base = _va_to_off(data, va)
        got = data[off:off + len(pattern)] if off else b""
        check(got == pattern,
              f"{va:#010x}: {what}",
              f"want {pattern.hex()} got {got.hex()}")
    off, base = _va_to_off(data, gatetrace.VA_APPLIER)
    check(base == gatetrace.IMAGE_BASE,
          f"the image base the VA table assumes ({gatetrace.IMAGE_BASE:#x}) is "
          f"the one the PE declares", f"PE says {base:#x}")

    # CONTROL: a check that cannot fail is not a check. Move one constant and
    # the section must go red -- proved here rather than asserted.
    saved = gatetrace.OFF_STATUS
    try:
        gatetrace.OFF_STATUS = 0x110
        bad = struct.pack("<I", gatetrace.OFF_STATUS)
        off, _ = _va_to_off(data, 0x0081A925)
        check(data[off:off + 6] != b"\x8b\x83" + bad,
              "CONTROL: OFF_STATUS moved one dword to 0x110 no longer matches "
              "the image -- the byte checks above are load-bearing")
    finally:
        gatetrace.OFF_STATUS = saved


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
    check("DebugSetProcessKillOnExit" in src,
          "detaching leaves the client ALIVE -- without this the operator's "
          "session dies when the trace ends")
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
