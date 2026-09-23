"""Every c2s send site in the client, read from the bytes without a disassembler.

    python toolkit/clientscan/sendsites.py                 # the pinned build
    python toolkit/clientscan/sendsites.py --exe <path>
    python toolkit/clientscan/sendsites.py --all           # every vaulted build
    python toolkit/clientscan/sendsites.py --anchors        # just the five pins
    python toolkit/clientscan/sendsites.py --opcode 0x001F  # one opcode's site(s)
    python toolkit/clientscan/sendsites.py --channel auth   # one channel's rows

WHY THIS EXISTS, and it is a specific failure this closes for good. Every "c2s
NOT FOUND" verdict in this repo -- hero kick, hero add, henchman hire (heroes
§3.3), and the roster of "which client actions does our server ignore" -- rested
on a scratch enumeration that was never committed, and one of them censused the
WRONG family (s2c ids fed through a c2s search). `codescan.py --xrefs` can count
a framer's callers, but it needs `capstone`, and a census that must be re-run
after every ArenaNet build to answer "did a new opcode appear" cannot depend on
a pip install the owner may not have at 2am. So this is a BARE-MACHINE byte scan:
`gwpe` (the stdlib PE reader), `asserts` (fixed byte patterns, bare-machine by
rule) and `buildid`, nothing else.

WHAT A SEND SITE LOOKS LIKE, MEASURED on build 38797. The client wraps each
outbound message in a small function that stores the opcode into a stack buffer,
fetches a connection, and calls one of two framers. The `0x001F` wrapper is the
clean example (0x0091FF30):

    8d 45 f8              lea eax, [ebp-8]        THE BUFFER SLOT
    50                    push eax
    6a 08                 push 8                  the buffer length (bytes)
    c7 45 f8 1f 00 00 00  mov [ebp-8], 0x1f       THE OPCODE, into that slot
    e8 <rel32>            call 0x491de0           the GAME-connection getter
    50                    push eax
    e8 <rel32>            call 0x7dcf00           THE FRAMER

So the scan keys on the LAST thing every site does -- an `E8` whose target is a
framer -- and reads the whole containing function back from there for (a) the
`lea reg,[ebp+D]` buffer slot and (b) the `C7 45 D <imm32>` / `C7 85 D32 <imm32>`
store INTO THAT SLOT, whose imm32 is the opcode. Tying the store to the pushed
slot is what makes a row CONFIDENT: a generic sender that holds a size 0x40 in
some other local fails the tie -- MEASURED, it is what separates the true
`0x0040` wrapper (0x009207B0) from 0x0091FB20's `mov [ebp-0x48], 0x40`.

THE WINDOW IS THE FUNCTION, NOT 64 BYTES. The first cut of this scan read back a
fixed 64 bytes and reported 7 of 214 sites "opcode passed in a register (a
forwarding thunk)". That was FALSE (both D1 reviewers, 2026-09-22, from the
bytes): six of the seven store their opcode 80-348 bytes before the call --
0x002B COMPASS_DRAW at 0x00920230 stores it at +0x1B and calls at +0x75 -- and
the seventh (0x00491D30) pushes a STATIC buffer in .rdata whose first dword is
the opcode (8). A census whose failure mode is a plausible-sounding excuse for a
missing row is the one this module exists to replace, so the window is now the
containing function (bounded by `MAX_WINDOW`), a static image-address push is
read for its first dword, and the footer's `unresolved` must be 0 on the pinned
builds (`test_sendsites.py`).

TWO FRAMERS, BUT THE CHANNEL IS THE CONNECTION ARGUMENT, NOT THE FRAMER. The
image has two framers with different calling conventions, MEASURED on 38797:

    0x007DCF00  (conn, nbytes,  buf)   174 sites   `push buf; push 8; push conn`
    0x007DCB10  (conn, buf, ndwords)    40 sites   `push 3; push buf; push conn`

The first cut called the second one "the AUTH framer". That was also FALSE: it
is called with the GAME connection at three sites -- 0x00491E50 (opcode 0x0009,
2,687 c2s on the live game wire), 0x00852930 (0x0092, 305 on the wire) and the
static-buffer sender 0x00491D30 (0x0008) -- so a census that attributed the
channel per framer reported GAME 0x0009 and 0x0092 as having NO send site. The
connection argument picks the channel, so every row carries `channel` read from
its own bytes:

  * `game`  -- the site calls the GAME-connection getter (a 6-byte `A1 <abs>;
    C3` function, derived per build as the dominant `call X; push eax` before a
    framer call: 171 of 214 sites on 38797), or pushes/loads that same global
    directly (`FF 35 <abs>`, `A1 <abs>`, `8B xD <abs>`).
  * `auth`  -- the site pushes `[reg+0x14]` of a struct it loaded from the AUTH
    global (derived per build as the dominant absolute load in those sites'
    windows: [0x00C03524]+0x14 on 38797), the shape 37 of the 40 dword-framer
    sites take and NO byte-framer site does. Named for the nearest assert
    module of its wrappers (GcAuthCmd) -- a LABEL.
  * `?`     -- neither shape in the window; counted in the footer, never
    guessed. 0 on both pinned builds.

The two framers' VAs did NOT swap order between 38797 and 38888 (the first cut
said they did): the dword framer is the lower VA on both builds (0x007DCB10 <
0x007DCF00; 0x007DCF70 < 0x007DD360). They are found by a MASKED PROLOGUE
SIGNATURE (below), not by a hardcoded VA, because 38888 moved both.

THE KNOWN-BAD ARMS. A wrong framer VA yields zero rows: `census(pe,
framers=[0xDEADBEEF])` returns []. And the CLI REFUSES a zero-row or a
not-two-framers result with exit status 2 -- the first cut printed
"coverage: 0 sites" and exited 0, which on a new ArenaNet build whose signature
drifted reads as a clean "no c2s opcodes". `main()` returns 2 in both cases.

STANDARD LIBRARY ONLY. READ ONLY: opens the exe for reading and nothing else.
Not `codescan.py`'s job -- that disassembles, this counts, and the boundary is
the bare-machine rule (CLAUDE.md carve-out (1)).
"""
import argparse
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE                                          # noqa: E402
import pinned                                                # noqa: E402
import buildid                                               # noqa: E402
import asserts as assertsmod                                 # noqa: E402

find_exe = pinned.find

# The framer's prologue, with every build-specific dword masked to None.
# MEASURED on 38797: both framers open with these 42 bytes, differing only in the
# `sub esp` immediate (0x50 vs 0x40, itself masked) and the pushed assert line and
# file pointer (masked). The register loads from [ebp+8]/[ebp+0xc]/[ebp+0x10], the
# `test edi,edi; jne` null-check on arg1, and the `push line; mov edx, file` assert
# idiom are the fixed spine. On 38797 this matches EXACTLY the two framers and
# nothing else (test_sendsites §1).
#
# Bytes, with . for a wildcard:
#   55 8b ec 83 ec ..  a1 .. .. .. ..  33 c5 89 45 fc
#   53 8b 5d 10 56 8b 75 0c 57 8b 7d 08 85 ff 75 14
#   68 .. .. .. ..  ba .. .. .. ..
FRAMER_SIG = bytes.fromhex(
    "55 8b ec 83 ec 00 a1 00 00 00 00 33 c5 89 45 fc"
    "53 8b 5d 10 56 8b 75 0c 57 8b 7d 08 85 ff 75 14"
    "68 00 00 00 00 ba 00 00 00 00".replace(" ", ""))
FRAMER_MASK = bytes.fromhex(
    "ff ff ff ff ff 00 ff 00 00 00 00 ff ff ff ff ff"
    "ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff"
    "ff 00 00 00 00 ff 00 00 00 00".replace(" ", ""))

# The five opcodes the test pins per build. 0x0040 ROTATE_PLAYER (cmsg §C13),
# 0x0016 HERO_LOCK_TARGET, 0x00B1 travel, 0x001E hero ADD, 0x001F hero KICK.
# One dedicated single-opcode wrapper each, so each resolves to one site.
ANCHOR_OPCODES = (0x0040, 0x0016, 0x00B1, 0x001E, 0x001F)

CALL = 0xE8              # call rel32
PUSH_EAX = 0x50
PUSH_IMM8 = 0x6A
PUSH_IMM32 = 0x68
MOV_EBP_D8 = b"\xc7\x45"    # mov dword [ebp+disp8], imm32
MOV_EBP_D32 = b"\xc7\x85"   # mov dword [ebp+disp32], imm32
PUSH_MEM_ABS = b"\xff\x35"  # push dword [abs32]
MOV_EAX_ABS = 0xA1          # mov eax, [abs32]
MOV_REG_ABS = 0x8B          # mov r32, [abs32]   (modrm 0x05|0x0D|0x15|0x1D|0x35|0x3D)
LEA = 0x8D                  # lea r32, [ebp+disp]
PROLOGUE = b"\x55\x8b\xec"  # push ebp; mov ebp, esp
INT3 = 0xCC
RET = 0xC3
MAX_WINDOW = 1024           # the containing function, bounded (largest measured
                            # store-to-call distance on 38797/38888 is 348 bytes)
LENGTH_WINDOW = 32          # the `push imm` length sits in the arg-setup tail
CHANNEL_GAME, CHANNEL_AUTH, CHANNEL_UNKNOWN = "game", "auth", "?"


def _text(pe):
    """(bytes, base_va) for the .text section."""
    sec = pe.section(".text")
    if sec is None:
        raise ValueError("no .text section")
    data = pe.data[sec["rawptr"]:sec["rawptr"] + sec["rawsize"]]
    return data, pe.image_base + sec["vaddr"]


def _masked_find(data, sig, mask):
    """Every offset in `data` where `sig` matches under `mask` (0 = wildcard)."""
    out = []
    n, m = len(data), len(sig)
    # Anchor the scan on the first fixed byte to keep it near memchr speed.
    first = sig[0]
    i = data.find(bytes([first]))
    while i != -1 and i + m <= n:
        ok = True
        for j in range(m):
            if mask[j] and data[i + j] != sig[j]:
                ok = False
                break
        if ok:
            out.append(i)
        i = data.find(bytes([first]), i + 1)
    return out


def find_framers(pe):
    """Every framer VA in the image, by the masked prologue signature.

    On 38797 this is exactly {0x007DCB10, 0x007DCF00}; on a later build it is
    wherever they moved. Returned sorted, so the caller can compare a set.
    """
    data, base = _text(pe)
    return sorted(base + off for off in _masked_find(data, FRAMER_SIG,
                                                     FRAMER_MASK))


def _call_targets(data, base):
    """{target_va: [call_site_va, ...]} for every `E8 rel32` in .text.

    One pass over the section builds the whole call graph, so a census over
    both framers and a per-wrapper caller list share it.
    """
    out = {}
    i = data.find(bytes([CALL]))
    n = len(data)
    while i != -1:
        if i + 5 <= n:
            rel = struct.unpack_from("<i", data, i + 1)[0]
            tgt = (base + i + 5 + rel) & 0xFFFFFFFF
            out.setdefault(tgt, []).append(base + i)
        i = data.find(bytes([CALL]), i + 1)
    return out


def wrapper_start(data, base, site_va):
    """The VA of the function that contains a send site.

    Scans back for a `55 8b ec` prologue that sits at a function boundary --
    immediately after INT3 padding or a `ret`, or at the section start. Best
    effort, like `codescan`'s own boundary note: a function without the
    standard prologue (a naked thunk) resolves to the nearest one before it,
    which the caller can still use as a caller-count key.
    """
    off = site_va - base
    p = off
    while p >= 0:
        if data[p:p + 3] == PROLOGUE:
            if p == 0 or data[p - 1] in (INT3, RET):
                return base + p
        p -= 1
    return None


def _window(data, base, site_va):
    """(lo, end) .text offsets: the containing function up to the E8, bounded."""
    end = site_va - base
    wrap = wrapper_start(data, base, site_va)
    lo = (wrap - base) if wrap is not None else max(0, end - 64)
    if end - lo > MAX_WINDOW:
        lo = end - MAX_WINDOW
    return lo, end


def _disp(buf):
    """A signed displacement from its 1- or 4-byte little-endian encoding."""
    if len(buf) == 1:
        return struct.unpack("<b", buf)[0]
    return struct.unpack("<i", buf)[0]


def _imm_stores(data, lo, end):
    """[(offset, disp, imm32)] for every `C7 45 d8 imm32` / `C7 85 d32 imm32` in
    [lo, end) -- a dword store of an immediate to an ebp-relative slot."""
    out = []
    p = lo
    while p < end:
        if data[p:p + 2] == MOV_EBP_D8 and p + 7 <= end:
            out.append((p, _disp(data[p + 2:p + 3]),
                        struct.unpack_from("<I", data, p + 3)[0]))
            p += 7
            continue
        if data[p:p + 2] == MOV_EBP_D32 and p + 10 <= end:
            out.append((p, _disp(data[p + 2:p + 6]),
                        struct.unpack_from("<I", data, p + 6)[0]))
            p += 10
            continue
        p += 1
    return out


# lea r32,[ebp+disp8] has modrm 0x45|0x4D|0x55|0x5D|0x75|0x7D (eax ecx edx ebx
# esi edi); the disp32 form 0x85|0x8D|0x95|0x9D|0xB5|0xBD.
_LEA_D8 = {0x45, 0x4D, 0x55, 0x5D, 0x75, 0x7D}
_LEA_D32 = {0x85, 0x8D, 0x95, 0x9D, 0xB5, 0xBD}


def _lea_slots(data, lo, end):
    """{disp} for every `lea r32,[ebp+disp]` in [lo, end)."""
    out = set()
    p = lo
    while p < end - 2:
        if data[p] == LEA:
            m = data[p + 1]
            if m in _LEA_D8 and p + 3 <= end:
                out.add(_disp(data[p + 2:p + 3]))
            elif m in _LEA_D32 and p + 6 <= end:
                out.add(_disp(data[p + 2:p + 6]))
        p += 1
    return out


def _static_buffer(pe, data, lo, end):
    """The first dword of a STATIC buffer pushed as an image address, or None.

    0x00491D30 (38797) does `push 1; push 0x941B94; push [conn]; call framer`
    with the message prebuilt in .rdata. Only a `68 imm32` in the tail whose
    imm32 lands in a non-.text, file-backed section counts.
    """
    q = max(lo, end - LENGTH_WINDOW)
    while q < end - 4:
        if data[q] == PUSH_IMM32:
            va = struct.unpack_from("<I", data, q + 1)[0]
            rva = va - pe.image_base
            sec = pe.section_of_rva(rva) if rva >= 0 else None
            if sec is not None and sec["name"] != ".text":
                off = pe.rva_to_off(rva)
                if off is not None and off + 4 <= len(pe.data):
                    return struct.unpack_from("<I", pe.data, off)[0]
        q += 1
    return None


def _length_before(pe, data, lo, end):
    """The LAST `push imm8/imm32` in the arg-setup tail, or None.

    The framers take the buffer length as an immediate -- bytes for the
    (conn, nbytes, buf) framer, dwords for (conn, buf, ndwords) -- pushed in
    the last few instructions before the call. A `68 imm32` that is an image
    address (a static buffer or an assert's file pointer) is not a length.
    Best effort; the anchors pin it (0x001F/0x001E push 8, 0x00A2 pushes 4).
    """
    q = max(lo, end - LENGTH_WINDOW)
    length = None
    while q < end:
        if data[q] == PUSH_IMM8 and q + 2 <= end:
            length = data[q + 1]
        elif data[q] == PUSH_IMM32 and q + 5 <= end:
            v = struct.unpack_from("<I", data, q + 1)[0]
            if not (pe.image_base <= v < pe.image_base + 0x10000000):
                length = v
        q += 1
    return length


def opcode_before(pe, data, base, site_va):
    """dict(opcode, length, confident, static, store_distance) for one site.

    The opcode is the imm32 of the LAST store into a slot that a `lea` in the
    same function hands to the framer (CONFIDENT). Failing that: a STATIC
    buffer's first dword (confident, `static`); failing that, the last
    ebp-relative imm32 store within 64 bytes (NOT confident); else None.
    `store_distance` is bytes from the store to the call -- the footer's max
    is the number the old 64-byte window was too short for.
    """
    lo, end = _window(data, base, site_va)
    stores = _imm_stores(data, lo, end)
    slots = _lea_slots(data, lo, end)
    tied = [s for s in stores if s[1] in slots]
    opcode = None
    confident = False
    static = False
    dist = None
    if tied:
        p, _d, imm = tied[-1]
        opcode, confident, dist = imm & 0xFFFF, True, end - p
    else:
        sb = _static_buffer(pe, data, lo, end)
        if sb is not None:
            opcode, confident, static = sb & 0xFFFF, True, True
        else:
            near = [s for s in stores if end - s[0] <= 64]
            if near:
                p, _d, imm = near[-1]
                opcode, dist = imm & 0xFFFF, end - p
    return {"opcode": opcode, "length": _length_before(pe, data, lo, end),
            "confident": confident, "static": static, "store_distance": dist}


# ---------------------------------------------------------------- the channel

def _abs_loads(data, lo, end):
    """{abs32} loaded or pushed from an absolute address in [lo, end):
    `A1 abs` (mov eax), `8B xD abs` (mov r32), `FF 35 abs` (push)."""
    out = set()
    p = lo
    while p < end - 4:
        b = data[p]
        if b == MOV_EAX_ABS and p + 5 <= end:
            out.add(struct.unpack_from("<I", data, p + 1)[0])
        elif b == MOV_REG_ABS and p + 6 <= end and (data[p + 1] & 0xC7) == 0x05:
            out.add(struct.unpack_from("<I", data, p + 2)[0])
        elif data[p:p + 2] == PUSH_MEM_ABS and p + 6 <= end:
            out.add(struct.unpack_from("<I", data, p + 2)[0])
        p += 1
    return out


def _has_push_reg_14(data, lo, end):
    """Is there a `FF 7x 14` (push dword [r32+0x14]) in [lo, end)?"""
    p = lo
    while p < end - 2:
        if data[p] == 0xFF and (data[p + 1] & 0xF8) == 0x70 and data[p + 2] == 0x14:
            return True
        p += 1
    return False


def _calls_in(data, base, lo, end):
    """{target_va} of every `E8 rel32` in [lo, end)."""
    out = set()
    p = lo
    while p < end - 4:
        if data[p] == CALL:
            rel = struct.unpack_from("<i", data, p + 1)[0]
            out.add((base + p + 5 + rel) & 0xFFFFFFFF)
        p += 1
    return out


def connection_globals(pe, data, base, sites):
    """The per-build connection map, derived from the sites themselves:
    dict(getter, game_conn, auth_struct).

    `getter`: the dominant X in `call X; push eax; call framer` -- on 38797 it
    is 0x00491DE0, six bytes `A1 D4 34 C0 00 C3` (mov eax,[0xC034D4]; ret), so
    `game_conn` is the dword it returns. REFUSES (ValueError) when no site has
    that shape or the winner is not a 6-byte getter: a census that cannot tell
    the channels apart must not print rows that look as if it could.

    `auth_struct`: the dominant absolute address loaded in the windows of the
    sites that push `[r32+0x14]`, [0x00C03524] on 38797. None when no site has
    the shape (then no row is `auth`, and the footer says so).
    """
    getters = Counter()
    for s in sites:
        end = s - base
        if end >= 6 and data[end - 6] == CALL and data[end - 1] == PUSH_EAX:
            rel = struct.unpack_from("<i", data, end - 5)[0]
            getters[(base + end - 6 + 5 + rel) & 0xFFFFFFFF] += 1
    if not getters:
        raise ValueError("no `call X; push eax; call framer` site: cannot "
                         "derive the game-connection getter")
    getter, _n = getters.most_common(1)[0]
    goff = pe.rva_to_off(getter - pe.image_base)
    gb = pe.data[goff:goff + 6] if goff is not None else b""
    if len(gb) != 6 or gb[0] != MOV_EAX_ABS or gb[5] != RET:
        raise ValueError(f"the dominant getter 0x{getter:08X} is not "
                         f"`mov eax,[abs]; ret` (bytes {gb.hex()}): refusing "
                         f"to name a game connection")
    game_conn = struct.unpack_from("<I", gb, 1)[0]
    loads = Counter()
    for s in sites:
        lo, end = _window(data, base, s)
        if _has_push_reg_14(data, lo, end):
            for a in _abs_loads(data, lo, end):
                if a != game_conn:
                    loads[a] += 1
    auth_struct = loads.most_common(1)[0][0] if loads else None
    return {"getter": getter, "game_conn": game_conn,
            "auth_struct": auth_struct}


def channel_of(data, base, site_va, conns):
    """`game`, `auth` or `?` for one site, from its own window's bytes."""
    lo, end = _window(data, base, site_va)
    if conns["getter"] in _calls_in(data, base, lo, end):
        return CHANNEL_GAME
    loads = _abs_loads(data, lo, end)
    if conns["game_conn"] in loads:
        return CHANNEL_GAME
    if (conns["auth_struct"] is not None and conns["auth_struct"] in loads
            and _has_push_reg_14(data, lo, end)):
        return CHANNEL_AUTH
    return CHANNEL_UNKNOWN


# ---------------------------------------------------------------- the census

def census(pe, framers=None):
    """One row per c2s send site: dict(opcode, length, confident, static,
    store_distance, site_va, wrapper_va, framer_va, channel, callers, module).

    `framers` overrides the signature scan -- the known-bad arm passes a bogus
    VA and gets [] back. `callers` is the sorted list of `E8 rel32` sites that
    call the wrapper; `module` is the nearest assert's source module (a label).
    """
    data, base = _text(pe)
    if framers is None:
        framers = find_framers(pe)
    targets = _call_targets(data, base)
    sites_by_framer = {f: targets.get(f & 0xFFFFFFFF, []) for f in framers}
    all_sites = [s for ss in sites_by_framer.values() for s in ss]
    if not all_sites:
        return []
    conns = connection_globals(pe, data, base, all_sites)
    az = assertsmod.Asserts(pe.path)
    assert_vas = sorted((a.va, a.module) for a in az.items)
    rows = []
    for framer, sites in sites_by_framer.items():
        for site in sites:
            fields = opcode_before(pe, data, base, site)
            wrap = wrapper_start(data, base, site)
            callers = sorted(targets.get(wrap & 0xFFFFFFFF, [])) if wrap else []
            row = {
                "site_va": site,
                "wrapper_va": wrap,
                "framer_va": framer,
                "channel": channel_of(data, base, site, conns),
                "callers": callers,
                "module": _nearest_module(assert_vas, site),
            }
            row.update(fields)
            rows.append(row)
    rows.sort(key=lambda r: (r["framer_va"], r["site_va"]))
    return rows


def _nearest_module(assert_vas, va):
    """The source module of the assert nearest `va`, or '?' -- a LABEL.

    `assert_vas` is a sorted [(va, module)]; nearest by absolute VA distance,
    which for a small wrapper lands inside its own module.
    """
    if not assert_vas:
        return "?"
    import bisect
    i = bisect.bisect_left(assert_vas, (va,))
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(assert_vas):
            d = abs(assert_vas[j][0] - va)
            if best is None or d < best[0]:
                best = (d, assert_vas[j][1])
    return best[1] if best else "?"


def framer_roles(rows):
    """{"bytes": va, "dwords": va} -- the two framers by calling convention.

    MEASURED on 38797: the busier framer (174 sites) takes (conn, nbytes, buf)
    -- the 0x001F wrapper pushes 8 for its two-dword buffer -- and the other
    (40 sites) takes (conn, buf, ndwords) -- 0x00491E50 pushes 3 for three
    dwords. 'Busier' is the build-independent way to tell them apart; NEITHER
    is a channel (see the module docstring).
    """
    per = Counter(r["framer_va"] for r in rows)
    order = [va for va, _n in per.most_common()]
    return {"bytes": order[0] if order else None,
            "dwords": order[1] if len(order) > 1 else None}


def anchors(rows):
    """{opcode: sorted[wrapper_va]} for the five pinned GAME_CMSG opcodes.

    CONFIDENT rows only -- the buffer tie in `opcode_before` -- so a coincidental
    `mov [ebp+D], 0x40` local never nominates a wrapper for opcode 0x0040; and
    the GAME CHANNEL only (per row, from the connection argument), so an
    AUTH-channel homonym (0x16, 0x1e) does not.
    """
    return {op: sorted({r["wrapper_va"] for r in rows
                        if r["opcode"] == op and r["confident"]
                        and r["channel"] == CHANNEL_GAME
                        and r["wrapper_va"] is not None})
            for op in ANCHOR_OPCODES}


def coverage(rows):
    """A summary footer: totals, resolved opcodes, channels, distinct wrappers."""
    resolved = [r for r in rows if r["opcode"] is not None]
    confident = [r for r in rows if r["confident"]]
    per_framer = Counter(r["framer_va"] for r in rows)
    per_channel = Counter(r["channel"] for r in rows)
    per_framer_channel = Counter((r["framer_va"], r["channel"]) for r in rows)
    dists = [r["store_distance"] for r in rows if r["store_distance"] is not None]
    return {
        "sites": len(rows),
        "resolved": len(resolved),
        "unresolved": len(rows) - len(resolved),
        "confident": len(confident),
        "static": sum(1 for r in rows if r["static"]),
        "distinct_opcodes": len({(r["channel"], r["opcode"]) for r in resolved}),
        "distinct_wrappers": len({r["wrapper_va"] for r in rows
                                  if r["wrapper_va"] is not None}),
        "per_framer": dict(per_framer),
        "per_channel": dict(per_channel),
        "per_framer_channel": dict(per_framer_channel),
        "max_store_distance": max(dists) if dists else None,
    }


def _fmt_op(op):
    return "  ????" if op is None else f"0x{op:04X}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None, help="client to read (default: pinned)")
    ap.add_argument("--all", action="store_true",
                    help="run over every vaulted build")
    ap.add_argument("--anchors", action="store_true",
                    help="print only the five pinned anchors")
    ap.add_argument("--opcode", default=None,
                    help="print only sites sending this opcode, e.g. 0x001F")
    ap.add_argument("--channel", default=None, choices=("game", "auth", "?"),
                    help="print only sites on this channel")
    ap.add_argument("--framer", default=None,
                    help="override the framer VA (a wrong one yields zero rows "
                         "and exit status 2)")
    args = ap.parse_args(argv)

    if args.all:
        import vaultpath
        root = vaultpath.vault_path("client")
        exes = [os.path.join(root, name, "Gw.exe")
                for name in sorted(os.listdir(root))
                if os.path.exists(os.path.join(root, name, "Gw.exe"))]
        worst = 0
        for exe in exes:
            worst = max(worst, _report(exe, args))
            print()
        return worst
    exe = args.exe or find_exe()[0]
    return _report(exe, args)


def _report(exe, args):
    """Print one build's census; 0 when it measured something, 2 when it did
    not (no framers, or zero rows) -- a refusal, never a clean empty."""
    pe = PE(exe)
    try:
        b = buildid.of_image(exe)[0]
    except Exception:                                        # noqa: BLE001
        b = "?"
    framers = [int(args.framer, 0)] if args.framer else None
    fr = framers if framers is not None else find_framers(pe)
    print(f"{os.path.basename(os.path.dirname(exe))}: build {b}")
    print(f"  framers: {', '.join('0x%08X' % f for f in fr) or 'NONE'}")
    if framers is None and len(fr) != 2:
        print(f"  REFUSED: the prologue signature found {len(fr)} framers, not "
              f"2 -- the signature drifted; nothing below would be a census")
        return 2
    try:
        rows = census(pe, framers=framers)
    except ValueError as exc:
        print(f"  REFUSED: {exc}")
        return 2
    if not rows:
        print("  REFUSED: zero send sites -- a wrong framer VA, not a clean "
              "'no c2s opcodes'")
        return 2
    data, base = _text(pe)
    conns = connection_globals(pe, data, base, [r["site_va"] for r in rows])
    roles = framer_roles(rows)
    print(f"  game connection: getter 0x{conns['getter']:08X} -> "
          f"[0x{conns['game_conn']:08X}]; auth connection: "
          f"[[0x{conns['auth_struct']:08X}]+0x14]"
          if conns["auth_struct"] is not None else
          f"  game connection: getter 0x{conns['getter']:08X} -> "
          f"[0x{conns['game_conn']:08X}]; auth connection: NOT FOUND")
    print(f"  framer (conn, nbytes, buf): 0x{roles['bytes']:08X}; "
          f"framer (conn, buf, ndwords): "
          f"{'0x%08X' % roles['dwords'] if roles['dwords'] else 'NONE'}")
    if args.anchors:
        an = anchors(rows)
        for op in ANCHOR_OPCODES:
            vas = an.get(op) or []
            print(f"  {_fmt_op(op)} -> "
                  f"{', '.join('0x%08X' % v for v in vas) or 'NOT FOUND'}")
        return 0
    want = int(args.opcode, 0) if args.opcode else None
    for r in rows:
        if want is not None and r["opcode"] != want:
            continue
        if args.channel and r["channel"] != args.channel:
            continue
        wv = "0x%08X" % r["wrapper_va"] if r["wrapper_va"] else "?"
        tag = ("" if r["confident"] and not r["static"]
               else " static" if r["static"] else " ~")
        cs = r["callers"]
        callers = (f"{len(cs)}" + (f" ({', '.join('0x%08X' % c for c in cs[:3])}"
                                   f"{', ...' if len(cs) > 3 else ''})" if cs else ""))
        print(f"  {r['channel']:<4} {_fmt_op(r['opcode'])}{tag:<7} wrap {wv}  "
              f"site 0x{r['site_va']:08X}  len {r['length']}  callers {callers}"
              f"  {r['module']}")
    cov = coverage(rows)
    print(f"  coverage: {cov['sites']} sites, {cov['resolved']} with an opcode "
          f"({cov['confident']} confident, {cov['static']} static), "
          f"{cov['unresolved']} without; {cov['distinct_opcodes']} distinct "
          f"(channel, opcode) over {cov['distinct_wrappers']} wrappers; "
          f"farthest store {cov['max_store_distance']} bytes before its call")
    print(f"            per framer: "
          f"{', '.join('0x%08X=%d' % (k, v) for k, v in sorted(cov['per_framer'].items()))}"
          f"; per channel: "
          f"{', '.join('%s=%d' % (k, v) for k, v in sorted(cov['per_channel'].items()))}")
    print(f"            per framer x channel: "
          f"{', '.join('0x%08X/%s=%d' % (k[0], k[1], v) for k, v in sorted(cov['per_framer_channel'].items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
