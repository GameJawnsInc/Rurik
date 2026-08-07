"""Prove the key-tap patch plants a correct cave, and touches nothing else.

The design is in studies/livekey/CODECAVE.md; this checks the implementation against the
real client without launching it. A wrong displacement here would produce a client that
crashes on the first handshake -- the worst place to discover it -- so the edges are
checked arithmetically (the patcher is dependency-free; no disassembler), and the patch is
diffed against the original to prove it changed exactly the 44 bytes it claims and not one
more.

Section 1 is fixture-free -- it exercises build_cave()'s arithmetic on arbitrary addresses,
so the core logic is covered on a machine with no client. Section 2 applies the patch to
the pinned client and is skip-guarded.

Read-only, standard library only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
import checks  # noqa: E402
import keytap_patch as kp  # noqa: E402

# Floor 5 = section 1, which needs no client. Section 2 adds 8 with the pinned client
# present; a green run there is 13.
LEDGER = checks.Ledger("keytap_patch", floor=5)


def main():
    # ---- 1. build_cave arithmetic, on addresses we choose (no client needed) ----
    print("1. build_cave emits a 38-byte cave whose edges resolve, for arbitrary VAs")
    cave_va, slot_va, back_va = 0x00450000, 0x00c00000, 0x007d0006
    cave = kp.build_cave(cave_va, slot_va, back_va)
    LEDGER.ok(len(cave) == kp.CAVE_SIZE, "the cave is exactly CAVE_SIZE bytes",
              f"{len(cave)}")
    LEDGER.ok(cave[:3] == b"\x9c\x60\xfc",
              "it opens by saving flags and registers (pushfd; pushad; cld)",
              cave[:3].hex())
    disp = struct.unpack("<i", cave[11:15])[0]
    LEDGER.ok((cave_va + 8) + disp == slot_va,
              "the PIC slot write resolves to the slot (eax=cave+8, +disp)",
              f"resolves 0x{(cave_va+8)+disp:x}")
    LEDGER.ok(cave[-11:-5] == kp.STOLEN,
              "the six stolen bytes are replayed before returning",
              cave[-11:-5].hex())
    back = (cave_va + kp.CAVE_SIZE) + struct.unpack("<i", cave[-4:])[0]
    LEDGER.ok(back == back_va, "the tail jump returns to back_va",
              f"0x{back:x}")

    # ---- 2. the real client ----------------------------------------------------
    print("\n2. planted into the pinned client, and nothing else moves")
    try:
        import pinned  # noqa: E402
        from gwpe import PE  # noqa: E402
        exe = pinned.find()[0]
    except SystemExit:
        exe = None
    if not exe or not os.path.isfile(exe):
        LEDGER.skip("real client", "no pinned client to patch")
        return LEDGER.verdict()

    pe = PE(exe)
    data = pe.data
    patched, report = kp.plant(data, pe)

    LEDGER.ok(kp.verify(patched, pe, report) is True,
              "verify() follows every control-flow edge and accepts the result")

    # The two ranges hold exactly the expected bytes, and NOTHING outside them changed.
    # (A byte count is not the invariant: the jump-back displacement contains a 0xCC that
    # coincidentally matches the original int3 padding, so 43 bytes "differ" though 44 were
    # written -- checking contents and containment is what actually matters.)
    tap_off = pe.rva_to_off(report["tap_va"] - pe.image_base)
    cave_off = pe.rva_to_off(report["cave_va"] - pe.image_base)
    exp_jmp = b"\xe9" + struct.pack("<i", report["cave_va"] - (report["tap_va"] + 5)) + b"\x90"
    exp_cave = kp.build_cave(report["cave_va"], report["slot_va"], report["tap_va"] + 6)
    LEDGER.ok(patched[tap_off:tap_off + 6] == exp_jmp,
              "the tap holds the 6-byte jump-to-cave", patched[tap_off:tap_off + 6].hex())
    LEDGER.ok(patched[cave_off:cave_off + kp.CAVE_SIZE] == exp_cave,
              "the cave holds exactly build_cave()'s output")
    allowed = set(range(tap_off, tap_off + 6)) | set(range(cave_off, cave_off + kp.CAVE_SIZE))
    changed = {i for i in range(len(data)) if data[i] != patched[i]}
    LEDGER.ok(changed <= allowed and changed,
              "and no byte outside the tap and the cave changed",
              f"{len(changed)} bytes changed, all within the two declared ranges")

    # The slot the patch chose is a real, safe target.
    slot_rva = report["slot_va"] - pe.image_base
    dsec = [s for s in pe.sections if s["name"].rstrip("\x00") == ".data"][0]
    in_data = dsec["vaddr"] <= slot_rva < dsec["vaddr"] + dsec["rawsize"]
    LEDGER.ok(in_data, "the slot is in file-backed .data (not BSS, not another section)",
              f"slot RVA 0x{slot_rva:x}")
    soff = pe.rva_to_off(slot_rva)
    LEDGER.ok(not any(patched[soff:soff + kp.SLOT_SIZE]),
              "the slot is still zero -- the cave writes it at runtime, not the patch")

    # Guards: the check can fail, and the patcher refuses a wrong or already-patched binary.
    try:
        kp.verify(data, pe, report)
        refused_unpatched = False
    except kp.KeyTapError:
        refused_unpatched = True
    LEDGER.ok(refused_unpatched,
              "verify() REJECTS the unpatched client -- the edges do not resolve there")

    try:
        kp.plant(patched, pe)
        refused_double = False
    except kp.KeyTapError:
        refused_double = True
    LEDGER.ok(refused_double,
              "planting into an already-tapped client is refused",
              "the stolen bytes are now a jump, so the tap no longer matches")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
