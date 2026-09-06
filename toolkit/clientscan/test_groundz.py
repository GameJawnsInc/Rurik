"""Checks for groundz.py -- the AgentView height read (GROUNDZ-F1..F6).

Every offset in groundz.py is STATIC DISASSEMBLY that has never been read out of a running
client, so what this file can check is not "the number is right" -- it is that the walk is
the one studies/renderobj/FINDINGS.md describes, and that **every way of being wrong
produces a NAMED REFUSAL rather than a plausible float**. That second half is the whole
point of the module: a wrong base or a stale pointer must not return 0.0 and look like a
body at ground level.

The client's own registrar guarantees `array[id]->+0x2C == id` (0x00801515 writes the
object into the slot its +0x2C names), so the round-trip check below is not a heuristic --
it is ArenaNet's invariant, and a build where it fails is a build where our base is wrong.

BARE MACHINE: fake memory throughout, no client, no vault. groundz.read_groundz takes a
`read(addr, n)` closure precisely so this is possible -- the same shape movetap's
agtrack_fence uses.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                    # noqa: E402
import groundz as G              # noqa: E402

# Floor from this file's first green run.
LEDGER = checks.Ledger("groundz: the AgentView height read", floor=18)
check = checks.adopt_named(LEDGER)

BASE, ARRAY, VIEW = 0x00400000, 0x0A000000, 0x0B000000
AID = 10


def make_view(aid=AID, tag=G.TYPE_AVCHAR, ground=-1234.5, cached=-1234.5,
              vext=8.0, px=100.0, py=200.0, qplane=29, model=0x1234):
    b = bytearray(0xC4)
    struct.pack_into("<I", b, G.V_ID, aid)
    struct.pack_into("<I", b, G.V_TYPE, tag)
    struct.pack_into("<f", b, G.V_GROUND, cached)
    struct.pack_into("<f", b, G.V_VEXT, vext)
    struct.pack_into("<f", b, G.V_POS, px)
    struct.pack_into("<f", b, G.V_POS + 4, py)
    struct.pack_into("<f", b, G.V_POS + 8, ground)
    struct.pack_into("<f", b, G.V_QUERY, px)
    struct.pack_into("<f", b, G.V_QUERY + 4, py)
    struct.pack_into("<i", b, G.V_QUERY + 8, qplane)
    struct.pack_into("<I", b, G.V_MODEL, model)
    return bytes(b)


def mem(count=64, array=ARRAY, view=VIEW, blk=None, slot_id=AID):
    """A fake client. Every argument is a way to be wrong."""
    block = make_view() if blk is None else blk

    def read(addr, n):
        if addr == BASE + G.RVA_VIEW_COUNT:
            return struct.pack("<I", count)
        if addr == BASE + G.RVA_VIEW_ARRAY:
            return struct.pack("<I", array)
        if array and addr == array + slot_id * 4:
            return struct.pack("<I", view)
        if view and addr == view:
            return block[:n]
        return None
    return read


# ---- 1. the happy path, and the fields it must carry ---------------------
r = G.read_groundz(mem(), BASE, AID)
check("a correct walk returns ok with the ground z from +0x8C",
      r["ok"] is True and abs(r["ground_z"] - (-1234.5)) < 1e-6,
      f"{r}")
check("and it returns the MEMO at +0x30 and the per-agent vertical term at "
      "+0x40 beside it -- the drawn height is not +0x8C alone (GROUNDZ-F6), so "
      "a caller that gets only one number cannot tell a wrong query from a "
      "wrong offset",
      abs(r["cached_z"] - (-1234.5)) < 1e-6 and abs(r["vext"] - 8.0) < 1e-6)
check("and the cache KEY (+0x74/+0x78/+0x7C), so `+0x8C == +0x30` can be "
      "checked against the point that produced it",
      abs(r["qx"] - 100.0) < 1e-6 and abs(r["qy"] - 200.0) < 1e-6
      and r["qplane"] == 29)
check("and the 'mdl ' handle at +0x60, raw -- the model's own copy at "
      "model+0x18 needs a handle-table resolve that is NOT decoded yet",
      r["model_handle"] == 0x1234)
check("the plane is read SIGNED: the ctor seeds the key's plane to -1 as a "
      "never-match sentinel, and an unsigned read would report 4294967295",
      G.read_groundz(mem(blk=make_view(qplane=-1)), BASE, AID)["qplane"] == -1)

# ---- 2. EVERY WAY OF BEING WRONG IS A NAMED REFUSAL ----------------------
# This is the section the module exists for. None of these may return a float.
bad = [
    ("id past the count", G.read_groundz(mem(count=4), BASE, AID)),
    ("the count itself unreadable", G.read_groundz(lambda a, n: None, BASE, AID)),
    ("a wild count from a wrong base",
     G.read_groundz(mem(count=0x7FFFFFFF), BASE, AID)),
    ("a zero count", G.read_groundz(mem(count=0), BASE, AID)),
    ("a null array pointer", G.read_groundz(mem(array=0), BASE, AID)),
    ("a null slot", G.read_groundz(mem(view=0), BASE, AID)),
    ("a short view block",
     G.read_groundz(mem(blk=make_view()[:0x40]), BASE, AID)),
    ("the wrong class tag", G.read_groundz(mem(blk=make_view(tag=0x200)), BASE, AID)),
    ("THE ROUND TRIP FAILING", G.read_groundz(mem(blk=make_view(aid=11)), BASE, AID)),
    ("a negative agent id", G.read_groundz(mem(), BASE, -1)),
]
for name, res in bad:
    check("REFUSED, by name: %s" % name,
          res["ok"] is False and res["why"] and res["ground_z"] is None,
          f"{res['why']!r}")

check("and every refusal names a DIFFERENT reason -- a single generic 'failed' "
      "would make a wrong base indistinguishable from an absent agent",
      len({res["why"].split()[0].split(":")[0] for _n, res in bad}) >= 8,
      f"{sorted({res['why'] for _n, res in bad})}")

# ---- 3. the constants are RVAs, not absolute -- the client is ASLR'd -----
check("the array constants are stored as RVAs against IMAGE_BASE, so a live "
      "reader rebases them onto the module instead of reading a fixed VA",
      G.RVA_VIEW_ARRAY == 0x00BF96CC - 0x00400000
      and G.RVA_VIEW_COUNT == 0x00BF96D4 - 0x00400000
      and G.IMAGE_BASE == 0x00400000)
check("the offsets are the ones studies/renderobj/FINDINGS.md decoded",
      (G.V_ID, G.V_GROUND, G.V_VEXT, G.V_QUERY, G.V_POS, G.V_MODEL, G.V_TYPE)
      == (0x2C, 0x30, 0x40, 0x74, 0x84, 0x60, 0x9C)
      and G.TYPE_AVCHAR == 0xDB)

raise SystemExit(LEDGER.verdict())
