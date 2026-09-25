"""The rel32 branch forms a caller search reads, in ONE place for two tools.

`codescan.py --xrefs` (capstone, CLAUDE.md carve-out (1)) and `sendsites.py`'s
caller column (a BARE-MACHINE byte scan) both answer "what reaches this function
by a direct branch", and until 2026-09-25 they answered it over different forms
without saying so. codescan scanned `E8`/`E9` and missed a conditional tail-jump
(its FIFTH defect). sendsites scanned `E8` alone, and on build 38797 that made
75 of its 82 "0 callers" rows wrong -- each is reached by a `jmp` or a `jcc`.
studies/cmsg/FINDINGS.md read one of those zeros, the MAP_TRAVEL wrapper
0x0085C280, as "reached through a pointer", against a route survey that had the
caller right one hop back (the thunk 0x008576E0, called from 0x004A791F). The
forms and the scan live here so the two tools cannot drift apart again, and
each builds the scope it prints from this tuple.

A BYTE SCAN, NOT A DECODE. An `E8` inside some longer instruction matches as
well as a real one. `codescan` can walk a hit from its function's start
(`Image.boundary_status`); a census counting callers takes the odds -- a random
rel32 lands on one given VA about once in 2**32.

STANDARD LIBRARY ONLY. sendsites.py's bare-machine rule reaches through this
import, so nothing here may take a dependency.
"""
import struct

# Every rel32 branch a caller search reads, as (opcode bytes, kind). `0F 80..8F`
# is jcc: sixteen condition codes, one rel32 form.
BRANCHES = ((b"\xE8", "call"), (b"\xE9", "jmp")) + tuple(
    (bytes([0x0F, cc]), "jcc") for cc in range(0x80, 0x90))

# The direct-branch forms NOT searched, as a (name, detail) scope row.
REL8_BLIND = ("rel8 short branches",
              "`jmp short` (EB), `jcc short` (70..7F), `loop`/`jecxz` -- a "
              "one-byte displacement reaches only 128 bytes either side, so "
              "`codescan.py --dis` the neighbourhood when the answer is zero")


def kinds():
    """The branch kinds in scan order, each once: ('call', 'jmp', 'jcc')."""
    return tuple(dict.fromkeys(k for _op, k in BRANCHES))


def searched():
    """[(name, detail)], one row per kind, built from `BRANCHES` -- the scope
    as data, so a test can read what a zero was looked for in."""
    ops = {}
    for op, kind in BRANCHES:
        ops.setdefault(kind, []).append(op.hex(" ").upper())
    out = []
    for kind, spell in ops.items():
        detail = (spell[0] if len(spell) == 1 else
                  f"{spell[0]}..{spell[-1]}, all {len(spell)} conditions")
        out.append((f"{kind} rel32", f"{detail}, over .text"))
    return out


def refs(data, base, targets):
    """{target_va: sorted [(site_va, kind)]} for every rel32 branch in `data`
    (a code section loaded at `base`) that lands on a VA in `targets`.

    `site_va` is the branch's first opcode byte. One pass over `data` per
    form, so asking for two hundred targets costs what asking for one does.
    """
    want = set(targets)
    out = {}
    for op, kind in BRANCHES:
        # The rel32 follows the opcode, and the branch is relative to the END
        # of the instruction: 5 bytes for E8/E9, 6 for 0F 8x.
        end = len(op) + 4
        p = data.find(op)
        while p != -1:
            if p + end <= len(data):
                rel = struct.unpack_from("<i", data, p + len(op))[0]
                t = (base + p + end + rel) & 0xFFFFFFFF
                if t in want:
                    out.setdefault(t, []).append((base + p, kind))
            p = data.find(op, p + 1)
    return {t: sorted(v) for t, v in out.items()}
