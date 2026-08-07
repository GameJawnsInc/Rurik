"""Plant the key-tap code cave: make the transient master_secret persistent to read.

The design and its verification are in studies/livekey/CODECAVE.md; this is the
implementation. It relocates entirely from byte signatures -- the tap site, the executable
cave space, and the data slot are all FOUND in the binary, never hardcoded to an address --
so it survives a client rebuild the way dump_dh_params.py's DH accessor does, and refuses
loudly when the client changed rather than patching the wrong place.

WHAT IT DOES. At the instruction where MsgConn.cpp finishes master_secret in the stack
buffer [ebp-0x18] (just before the RC4 key schedule), it overwrites 6 bytes with a jump to
a 38-byte cave in .text int3 padding. The cave saves state, copies the 20 bytes to a data
slot by a PIC (call/pop) address that is correct under ASLR, restores state, replays the 6
stolen bytes, and jumps back. toolkit/harness/keytap.py reads the slot at runtime.

DEPENDENCY-FREE, like make_custom_client.py which calls it: no capstone, no pefile. The
cave is emitted as fixed byte templates with arithmetic displacements, and verify() checks
the result by FOLLOWING those displacements (does the tap jump land in the cave, does the
cave jump back to tap+6, does the slot write resolve to the slot) rather than by
disassembling -- a check the artifact can fail, on a bare machine.
"""
import struct

# Anchored at the tap and unique in build 38797 (studies/livekey/CODECAVE.md). Encodes
# protocol constants unlikely to move across a rebuild: the stolen prologue, the 20-byte
# key length (push 0x14), the RC4 state offset ([ebx+0x7c]), and the stage-2 transition.
TAP_SIG = bytes.fromhex("8b5ddc8d45e8506a148d737cc743600200")
# The 6 bytes the jump overwrites, which the cave replays. Refuse if the site is not these.
STOLEN = bytes.fromhex("8b5ddc8d45e8")
SLOT_SIZE = 20          # a master_secret
CAVE_SIZE = 38          # emitted below; must fit the padding run found
CAVE_MIN_RUN = 40       # ask for a little slack over CAVE_SIZE
MASTER_OFF = 0x18       # [ebp-0x18], the master_secret buffer


class KeyTapError(Exception):
    """The tap could not be planted. Never patches on a guess."""


def build_cave(cave_va, slot_va, back_va):
    """The 38-byte cave for a cave at `cave_va`, writing to `slot_va`, returning to `back_va`.

    ASLR-safe: the slot is reached by a link-time-constant delta from the runtime EIP the
    call/pop reads, so no absolute address and no relocation entry is embedded.
    """
    c = bytearray()
    c += b"\x9C"                       # pushfd
    c += b"\x60"                       # pushad
    c += b"\xFC"                       # cld              (rep movsd must increment)
    c += b"\xE8\x00\x00\x00\x00"       # call $+5         (push EIP)
    pop_va = cave_va + len(c)          # eax will equal the VA of the next byte (the pop)
    c += b"\x58"                       # pop eax          (eax = pop_va)
    disp = slot_va - pop_va            # link-time constant; correct at any load base
    c += b"\x8D\xB8" + struct.pack("<i", disp)   # lea edi,[eax+disp]  -> runtime slot
    c += b"\x8D\x75" + struct.pack("<b", -MASTER_OFF)  # lea esi,[ebp-0x18]
    c += b"\xB9" + struct.pack("<I", SLOT_SIZE // 4)    # mov ecx, 5
    c += b"\xF3\xA5"                   # rep movsd        (20 bytes -> slot)
    c += b"\x61"                       # popad
    c += b"\x9D"                       # popfd
    c += STOLEN                        # replay the 6 stolen bytes
    jmp_from_end = cave_va + len(c) + 5
    c += b"\xE9" + struct.pack("<i", back_va - jmp_from_end)   # jmp back_va
    if len(c) != CAVE_SIZE:
        raise KeyTapError(f"cave is {len(c)} bytes, expected {CAVE_SIZE} -- template drift")
    return bytes(c)


def _text_section(pe):
    for s in pe.sections:
        if s["name"].rstrip("\x00") == ".text":
            return s
    raise KeyTapError("no .text section")


def _find_tap(data, pe):
    """(file offset, VA) of the tap, or raise. Unique, and the stolen bytes must match."""
    hits = []
    i = data.find(TAP_SIG)
    while i != -1:
        hits.append(i)
        i = data.find(TAP_SIG, i + 1)
    if not hits:
        raise KeyTapError(
            "the key-tap signature is not in this client -- it was recompiled or the key\n"
            "exchange changed. That is a real finding: re-derive the tap in\n"
            "studies/livekey/ before trusting this patch against a new build.")
    if len(hits) > 1:
        raise KeyTapError(f"{len(hits)} key-tap signature matches, expected 1; refusing "
                          f"to guess which is the real key exchange")
    off = hits[0]
    if bytes(data[off:off + len(STOLEN)]) != STOLEN:
        raise KeyTapError(f"the 6 bytes at the tap are {bytes(data[off:off+6]).hex()}, "
                          f"expected {STOLEN.hex()} -- the cave replays these, so a "
                          f"mismatch would corrupt control flow")
    va = pe.image_base + pe.off_to_rva(off)
    return off, va


def _find_cave(data, pe, need=CAVE_MIN_RUN):
    """(file offset, VA) of an int3 padding run of at least `need` bytes in .text."""
    sec = _text_section(pe)
    start, size = sec["rawptr"], sec["rawsize"]
    best = None
    i = start
    end = start + size
    while i < end:
        if data[i] == 0xCC:
            j = i
            while j < end and data[j] == 0xCC:
                j += 1
            if j - i >= need and (best is None or j - i > best[1]):
                best = (i, j - i)
            i = j
        else:
            i += 1
    if best is None:
        raise KeyTapError(f"no int3 padding run of >= {need} bytes in .text for the cave")
    off = best[0]
    return off, pe.image_base + pe.off_to_rva(off)


def _references_window(data, pe, lo_va, hi_va):
    """True if any .text 4-byte little-endian value lands in [lo_va, hi_va)."""
    sec = _text_section(pe)
    text = data[sec["rawptr"]:sec["rawptr"] + sec["rawsize"]]
    for va in range(lo_va, hi_va):
        if struct.pack("<I", va) in text:
            return True
    return False


def _find_slot(data, pe, size=SLOT_SIZE):
    """(file offset, VA) of a file-backed, zero, UNREFERENCED window in .data.

    Not just any zero run: the "slack" in this client's .data is its own zero-init globals,
    so the window must be one no code addresses. Picks the middle of a large zero run and
    checks nothing in .text references it, the way CODECAVE.md verified the design's slot.
    """
    want = max(size, 32)
    dsec = None
    for s in pe.sections:
        if s["name"].rstrip("\x00") == ".data":
            dsec = s
            break
    if dsec is None:
        raise KeyTapError("no .data section for the slot")
    start, rawsize = dsec["rawptr"], dsec["rawsize"]
    block = data[start:start + rawsize]
    # Walk zero runs; for each large one, try a window in its interior, away from either
    # edge (so a buffer whose base is just outside the run cannot reach our window).
    i = 0
    n = len(block)
    while i < n:
        if block[i] == 0:
            j = i
            while j < n and block[j] == 0:
                j += 1
            run_len = j - i
            if run_len >= want + 0x80:
                # centre a window in the run
                w = i + (run_len - want) // 2
                w &= ~0xF                      # 16-byte align
                if w < i:
                    w = i
                off = start + w
                va = pe.image_base + pe.off_to_rva(off)
                if not _references_window(data, pe, va, va + want):
                    return off, va
            i = j
        else:
            i += 1
    raise KeyTapError("no unreferenced zero window in .data large enough for the slot; "
                      "fall back to appending a section (CODECAVE.md)")


def plant(data, pe):
    """Return (patched bytes, report). Pure: `data` is not mutated.

    `pe` is a gwpe.PE of the ORIGINAL client. The patch is in-place -- no section grows or
    moves -- so the same PE's offset maps describe the patched bytes too, and the caller
    (make_custom_client) already holds one. report = {tap_va, cave_va, slot_va,
    patched_ranges:[(va,len,what),...]}.
    """
    tap_off, tap_va = _find_tap(data, pe)
    cave_off, cave_va = _find_cave(data, pe)
    slot_off, slot_va = _find_slot(data, pe)

    back_va = tap_va + 6
    cave = build_cave(cave_va, slot_va, back_va)

    out = bytearray(data)
    out[cave_off:cave_off + len(cave)] = cave
    # The 6-byte tap jump: E9 rel32 + one NOP to fill the 6th stolen byte.
    jmp = b"\xE9" + struct.pack("<i", cave_va - (tap_va + 5)) + b"\x90"
    out[tap_off:tap_off + 6] = jmp

    report = {
        "tap_va": tap_va, "cave_va": cave_va, "slot_va": slot_va,
        "patched_ranges": [(tap_va, 6, "key-tap jump"),
                           (cave_va, len(cave), "key-tap cave")],
    }
    return bytes(out), report


def locate_slot(data, pe):
    """(slot_rva, slot_va) in a key-tapped client, by reading the cave itself. Raises if
    the client is not tapped.

    keytap.py reads the slot as module_base + slot_rva; this is how a reader recovers that
    rva from the build on disk rather than being told it, so it stays correct per build.
    """
    from dhbuild import KEY_TAP_CAVE_SIG  # the cave prologue, through the lea opcode
    hits = []
    i = data.find(KEY_TAP_CAVE_SIG)
    while i != -1:
        hits.append(i)
        i = data.find(KEY_TAP_CAVE_SIG, i + 1)
    if not hits:
        raise KeyTapError("no key-tap cave in this client -- it was not built with --key-tap")
    if len(hits) > 1:
        raise KeyTapError(f"{len(hits)} key-tap caves found, expected 1")
    cave_off = hits[0]
    cave_va = pe.image_base + pe.off_to_rva(cave_off)
    # KEY_TAP_CAVE_SIG ends at the `8D B8` (lea edi,[eax+disp]); the disp follows it.
    disp_off = cave_off + len(KEY_TAP_CAVE_SIG)
    disp = struct.unpack("<i", data[disp_off:disp_off + 4])[0]
    slot_va = (cave_va + 8) + disp        # eax = cave_va+8 at the lea
    return slot_va - pe.image_base, slot_va


def verify(data, pe, report):
    """Follow the displacements in the patched bytes. Raise on any inconsistency.

    No disassembler: this checks the three control-flow edges arithmetically, which is
    exactly what a bare-machine patcher can afford and what a wrong displacement would fail.
    `pe` is the original client's PE (offset maps unchanged by an in-place patch).
    """
    def off(va):
        return pe.rva_to_off(va - pe.image_base)

    tap_va, cave_va, slot_va = report["tap_va"], report["cave_va"], report["slot_va"]

    # 1. tap -> cave
    t = off(tap_va)
    if data[t] != 0xE9:
        raise KeyTapError("tap is not a jump after patching")
    dest = tap_va + 5 + struct.unpack("<i", data[t + 1:t + 5])[0]
    if dest != cave_va:
        raise KeyTapError(f"tap jump lands at 0x{dest:x}, not the cave 0x{cave_va:x}")
    if data[t + 5] != 0x90:
        raise KeyTapError("tap jump not NOP-padded to 6 bytes")

    # 2. cave -> back to tap+6, and the stolen bytes are replayed
    c = off(cave_va)
    cave = data[c:c + CAVE_SIZE]
    if bytes(cave[-11:-5]) != STOLEN:
        raise KeyTapError("the cave does not replay the 6 stolen bytes")
    jb = cave_va + CAVE_SIZE
    back = jb + struct.unpack("<i", cave[-4:])[0]
    if back != tap_va + 6:
        raise KeyTapError(f"cave returns to 0x{back:x}, not tap+6 0x{tap_va+6:x}")

    # 3. the slot write resolves to the slot (PIC: eax = cave_va+8, +disp)
    disp = struct.unpack("<i", cave[11:15])[0]
    resolved = (cave_va + 8) + disp
    if resolved != slot_va:
        raise KeyTapError(f"cave slot write resolves to 0x{resolved:x}, not 0x{slot_va:x}")

    # 4. the slot is still zero and file-backed (nothing was written into it at patch time)
    s = off(slot_va)
    if s is None or any(data[s:s + SLOT_SIZE]):
        raise KeyTapError("slot is not a zero file-backed window after patching")
    return True
