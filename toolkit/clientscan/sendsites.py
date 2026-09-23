"""Every c2s send site in the client, read from the bytes without a disassembler.

    python toolkit/clientscan/sendsites.py                 # the pinned build
    python toolkit/clientscan/sendsites.py --exe <path>
    python toolkit/clientscan/sendsites.py --all           # every vaulted build
    python toolkit/clientscan/sendsites.py --anchors        # just the five pins
    python toolkit/clientscan/sendsites.py --opcode 0x001F  # one opcode's site(s)

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
outbound message in a tiny function that stores the opcode into a stack buffer,
packs it, and calls one of two channel framers. The `0x001F` wrapper is the
clean example (0x0091FF30):

    6a 08                 push 8                  the buffer length
    c7 45 f8 1f 00 00 00  mov [ebp-8], 0x1f       THE OPCODE
    e8 <rel32>            call 0x491de0           the pack helper
    50                    push eax
    e8 <rel32>            call 0x7dcf00           THE FRAMER

So the scan keys on the LAST thing every site does -- an `E8` whose target is a
framer -- and reads backward at most 64 bytes for the `C7 45 YY <imm32>` opcode
store. A site whose opcode is passed in a register (a forwarding thunk) resolves
to None and is COUNTED in the coverage footer rather than dropped, because a
clean confident zero is the exact shape the §6o and the "NOT FOUND" failures
took.

THE TWO FRAMERS, and why both. `0x007DCF00` has 174 call sites and `0x007DCB10`
has 40 -- 214 in all. The submitted D1 survey counted only the first; a census
that claims it cannot go stale must enumerate both, because a message sent
through the second framer is exactly the kind a single-framer census reports as
absent. They are found by a MASKED PROLOGUE SIGNATURE (below), not by a
hardcoded VA, because build 38888 moved every address in the image -- the same
reason `test_sendsites.py` pins the anchors per build.

THE KNOWN-BAD ARM. A wrong framer VA yields zero sites: `census(pe,
framers=[0xDEADBEEF])` returns []. The test feeds exactly that, because a census
whose failure mode is "silently finds nothing" is the one that reads as a green
"no c2s opcodes" the day the signature drifts.

STANDARD LIBRARY ONLY. READ ONLY: opens the exe for reading and nothing else.
Not `codescan.py`'s job -- that disassembles, this counts, and the boundary is
the bare-machine rule (CLAUDE.md carve-out (1)).
"""
import argparse
import os
import struct
import sys

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

# The channel framer's prologue, with every build-specific dword masked to None.
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
MOV_EBP_D8 = b"\xc7\x45"    # mov dword [ebp+disp8], imm32
MOV_EBP_D32 = b"\xc7\x85"   # mov dword [ebp+disp32], imm32
PROLOGUE = b"\x55\x8b\xec"  # push ebp; mov ebp, esp
INT3 = 0xCC
OPCODE_WINDOW = 64          # how far back the opcode store may sit


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
    both framers and a per-wrapper caller count share it.
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


LEA_EBP_D8 = b"\x8d\x45"    # lea eax, [ebp+disp8]
LEA_EBP_D32 = b"\x8d\x85"   # lea eax, [ebp+disp32]


def opcode_before(data, base, site_va, window=OPCODE_WINDOW):
    """(opcode, length, confident) from the store just before a framer call.

    Scans back at most `window` bytes for the LAST `C7 45 YY <imm32>` (or the
    disp32 form `C7 85`), whose imm32 is the opcode, and for the nearest
    `push imm8/imm32` before that, the declared buffer length. Either may be
    None: a thunk that takes the opcode in a register has no store, and its
    row says so rather than guessing.

    `confident` is the guard against a COINCIDENTAL local. A dedicated wrapper
    stores the opcode into the very stack slot it then `lea`s and pushes as the
    framer's buffer, so the store's displacement equals a `lea eax,[ebp+D]` in
    the same window. A generic sender that pushes a real buffer pointer and
    happens to hold a size 0x40 or a count 0x1e in some other `[ebp+D]` local
    fails this tie -- MEASURED on 38797, it is what separated the true 0x0040
    wrapper (0x009207B0) from 0x0091FB20's `mov [ebp-0x48], 0x40`. Only
    confident rows feed the anchors.
    """
    end = site_va - base                    # offset of the E8
    lo = max(0, end - window)
    opcode = op_off = op_disp = None
    # Walk forward through the window and keep the last matching store, because
    # the store nearest the call is the one whose value reaches it.
    p = lo
    while p < end:
        if data[p:p + 2] == MOV_EBP_D8 and p + 7 <= end:
            opcode = struct.unpack_from("<I", data, p + 3)[0] & 0xFFFF
            op_off, op_disp = p, data[p + 2:p + 3]      # disp8 byte
            p += 7
            continue
        if data[p:p + 2] == MOV_EBP_D32 and p + 10 <= end:
            opcode = struct.unpack_from("<I", data, p + 6)[0] & 0xFFFF
            op_off, op_disp = p, data[p + 2:p + 6]      # disp32 bytes
            p += 10
            continue
        p += 1
    length = None
    confident = False
    if op_off is not None:
        q = max(0, op_off - 8)
        while q < op_off:
            if data[q] == 0x6A and q + 2 <= op_off:      # push imm8
                length = data[q + 1]
            elif data[q] == 0x68 and q + 5 <= op_off:    # push imm32
                length = struct.unpack_from("<I", data, q + 1)[0]
            q += 1
        # The buffer tie: a `lea eax,[ebp+D]` with the SAME displacement as the
        # opcode store, anywhere in the window.
        lea8 = LEA_EBP_D8 + op_disp if len(op_disp) == 1 else None
        lea32 = LEA_EBP_D32 + op_disp if len(op_disp) == 4 else None
        window_bytes = data[lo:end]
        confident = ((lea8 is not None and lea8 in window_bytes)
                     or (lea32 is not None and lea32 in window_bytes))
    return opcode, length, confident


def wrapper_start(data, base, site_va):
    """The VA of the function that contains a send site.

    Scans back for a `55 8b ec` prologue that sits at a function boundary --
    immediately after INT3 padding, or at the section start. Best effort, like
    `codescan`'s own boundary note: a function without the standard prologue
    (a naked thunk) resolves to the nearest one before it, which the caller can
    still use as a caller-count key.
    """
    off = site_va - base
    p = off
    while p >= 0:
        if data[p:p + 3] == PROLOGUE:
            if p == 0 or data[p - 1] == INT3:
                return base + p
        p -= 1
    return None


def census(pe, framers=None):
    """One row per c2s send site: dict(opcode, length, site_va, wrapper_va,
    framer_va, callers, module).

    `framers` overrides the signature scan -- the known-bad arm passes a bogus
    VA and gets [] back. `callers` is the number of `E8 rel32` sites that call
    the wrapper; `module` is the nearest assert's source module (a label).
    """
    data, base = _text(pe)
    if framers is None:
        framers = find_framers(pe)
    targets = _call_targets(data, base)
    az = assertsmod.Asserts(pe.path)
    assert_vas = sorted((a.va, a.module) for a in az.items)
    rows = []
    for framer in framers:
        for site in targets.get(framer & 0xFFFFFFFF, []):
            opcode, length, confident = opcode_before(data, base, site)
            wrap = wrapper_start(data, base, site)
            ncall = len(targets.get(wrap & 0xFFFFFFFF, [])) if wrap else 0
            rows.append({
                "opcode": opcode,
                "length": length,
                "confident": confident,
                "site_va": site,
                "wrapper_va": wrap,
                "framer_va": framer,
                "callers": ncall,
                "module": _nearest_module(assert_vas, site),
            })
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


def game_framer(rows):
    """The GAME_CMSG framer's VA -- the one with the most call sites.

    The image has TWO c2s framers and they are DIFFERENT channels: the game
    channel (CharMsg/AgMsg opcodes, 174 sites on 38797) and the auth channel
    (GcAuthCmd, 40). They collide numerically -- AUTH_CMSG 0x16 is not
    GAME_CMSG 0x16 HERO_LOCK_TARGET -- so an anchor over GAME opcodes must scope
    to the game framer. It is the busier of the two on every build (the order of
    the two VAs itself swapped between 38797 and 38888), so 'most sites' is the
    build-independent way to name it.
    """
    per = {}
    for r in rows:
        per[r["framer_va"]] = per.get(r["framer_va"], 0) + 1
    return max(per, key=per.get) if per else None


def anchors(rows):
    """{opcode: sorted[wrapper_va]} for the five pinned GAME_CMSG opcodes.

    CONFIDENT rows only -- the buffer tie in `opcode_before` -- so a coincidental
    `mov [ebp+D], 0x40` local never nominates a wrapper for opcode 0x0040; and
    the GAME framer only, so an AUTH-channel homonym (0x16, 0x1e) does not.
    """
    gf = game_framer(rows)
    out = {op: sorted({r["wrapper_va"] for r in rows
                       if r["opcode"] == op and r["confident"]
                       and r["framer_va"] == gf
                       and r["wrapper_va"] is not None})
           for op in ANCHOR_OPCODES}
    return out


def coverage(rows):
    """A summary footer: totals, resolved opcodes, distinct wrappers."""
    resolved = [r for r in rows if r["opcode"] is not None]
    confident = [r for r in rows if r["confident"]]
    per_framer = {}
    for r in rows:
        per_framer[r["framer_va"]] = per_framer.get(r["framer_va"], 0) + 1
    return {
        "sites": len(rows),
        "resolved": len(resolved),
        "unresolved": len(rows) - len(resolved),
        "confident": len(confident),
        "distinct_opcodes": len({r["opcode"] for r in resolved}),
        "distinct_wrappers": len({r["wrapper_va"] for r in rows
                                  if r["wrapper_va"] is not None}),
        "per_framer": per_framer,
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
    ap.add_argument("--framer", default=None,
                    help="override the framer VA (a wrong one yields zero rows)")
    args = ap.parse_args(argv)

    if args.all:
        seen = []
        for b in buildid.pinned.BUILDS if hasattr(buildid, "pinned") else ():
            pass
        # Enumerate the vaulted client snapshots.
        import vaultpath
        root = vaultpath.vault_path("client")
        for name in sorted(os.listdir(root)):
            exe = os.path.join(root, name, "Gw.exe")
            if os.path.exists(exe):
                seen.append(exe)
        for exe in seen:
            _report(exe, args)
            print()
        return 0
    exe = args.exe or find_exe()[0]
    return _report(exe, args)


def _report(exe, args):
    pe = PE(exe)
    try:
        b = buildid.of_image(exe)
    except Exception:
        b = "?"
    framers = None
    if args.framer:
        framers = [int(args.framer, 0)]
    fr = framers if framers is not None else find_framers(pe)
    print(f"{os.path.basename(os.path.dirname(exe))}: build {b}")
    print(f"  framers: {', '.join('0x%08X' % f for f in fr) or 'NONE'}")
    rows = census(pe, framers=framers)
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
        wv = "0x%08X" % r["wrapper_va"] if r["wrapper_va"] else "?"
        print(f"  {_fmt_op(r['opcode'])}  wrap {wv}  site 0x{r['site_va']:08X}"
              f"  len {r['length']}  callers {r['callers']}  {r['module']}")
    cov = coverage(rows)
    print(f"  coverage: {cov['sites']} sites, {cov['resolved']} with an opcode "
          f"({cov['confident']} confident), {cov['unresolved']} without; "
          f"{cov['distinct_opcodes']} distinct opcodes over "
          f"{cov['distinct_wrappers']} wrappers")
    print(f"            per framer: "
          f"{', '.join('0x%08X=%d' % (k, v) for k, v in sorted(cov['per_framer'].items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
