"""The agent's GROUND Z, read out of the client's AgentView object (GROUNDZ-F1..F5).

    from groundz import read_groundz
    row = read_groundz(read, module_base, agent_id)

WHY THIS EXISTS. MOVECODE sec.1z-cb proved the height cannot come from the agent: its
movement record is (x, y, plane, w) with w a literal zero the client writes on every read,
and there is no z anywhere in the 0xD0 span. studies/renderobj/FINDINGS.md then decoded
where it does come from, and the answer is a different object graph entirely --
ArenaNet's AgentView, reached from the agent id through AvManager's array.

THE WALK (GROUNDZ-F1, all VAs in the pinned build 38797, ImageBase 0x00400000):

    count = [0x00BF96D4]                  ; AvManager's agent array count
    if id >= count:            REFUSE
    view  = [[0x00BF96CC] + id*4]         ; the array is indexed by the AGENT ID
    if view == 0:              REFUSE
    if [view+0x9C] != 0xDB:    REFUSE     ; the AvChar type tag 0x00802160 checks
    if [view+0x2C] != id:      REFUSE     ; THE ROUND TRIP -- see below

THE ROUND TRIP IS THE POINT, and it is why this file can be trusted on a build it has
never seen. The registrar at 0x008014B0 reads [obj+0x2C] *as* the array slot it writes
the object into (`mov [eax + esi*4], edi` at 0x00801515), so `array[id]->+0x2C == id` is
guaranteed by ArenaNet's own code. A wrong base, a wrong offset or a stale pointer breaks
it, and this file then returns a NAMED REFUSAL rather than a plausible float. That is the
same contract movetap already keeps on the agent side (it re-checks the agent's own id
field against the index it used) and the same reason vaultpath.require_dir() raises: a
fixture that silently resolves to the wrong thing turns every assertion behind it into a
no-op.

WHAT IT RETURNS, and why it is more than one number (GROUNDZ-F6). `+0x8C` is the ground
z, and every non-init write of it is the x87 return of AvAgent::GetGroundHeight
(0x007EBF00), which stores `MapQueryAltitude() - 1.0`. But the drawn height is NOT +0x8C
alone: a refuter found a per-agent vertical term at `+0x40` that three read sites subtract
from it. And `+0x30` is the memo the getter returns, so `+0x8C == +0x30` immediately after
a store is a self-check with no free parameter. All three are returned, plus the cache key
`+0x74/+0x78/+0x7C`, so a later session can tell a wrong query from a wrong offset from a
stale cache instead of guessing between them.

NOT INCLUDED, deliberately: the model's own copy at `model+0x18`. Reaching it needs the
'mdl ' handle table resolve at 0x0046FE40, which is a function rather than a table walk
and is not decoded yet (GROUNDZ-F5). The model handle at `+0x60` is returned raw so the
next session starts from it.

READ LIVE ON 2026-09-06 AND IT HELD, and this paragraph said the exact opposite for two
days -- "NOTHING HERE HAS BEEN READ OUT OF A RUNNING CLIENT ... treat a number from this
file as UNVERIFIED" -- which is a stale warning telling a reader to distrust a measured
result. Every offset began as static disassembly of
vault/client/2026-07-29_221c13772c7a/Gw.exe; GROUNDZ-R1 (studies/renderobj/FINDINGS.md,
RUN-R1.md) then put it against a running 38797 client and it held: 799 of 799 samples ok
for both agents with ZERO refusals, the round trip holding on every one, and +0x8C ==
+0x30 on every one -- the self-check with no free parameter. The height varies 171.30 u
across the stairs against 21.60 u on the flat, so it is not a constant a wrong offset
happened to land on. A number from this file is OBSERVED on 38797.

WHAT IS STILL OPEN is GROUNDZ-F5, the model's own copy named below. And what this file
cannot tell you is whether its two array VAs are stale on a DIFFERENT build: it names no
build constant and resolves nothing through `pinned`, so a rebase surfaces as a named
refusal at run time rather than as a red test at a desk. test_buildpins.py's census
entry for 2026-09-08 is the record of that, and of why it was not fixed there.

Pure stdlib. Takes a `read(addr, n)` closure so it runs on a bare machine with fake
memory -- the same shape movetap.agtrack_fence uses, and the reason it can be tested
without a client.
"""
import struct

IMAGE_BASE = 0x00400000

# AvManager's array, as RVAs so a live reader can rebase onto the module.
RVA_VIEW_ARRAY = 0x00BF96CC - IMAGE_BASE     # the AvAgent*[] base pointer
RVA_VIEW_COUNT = 0x00BF96D4 - IMAGE_BASE     # its element count

V_ID      = 0x2C    # the id it was registered under -- THE ROUND TRIP
V_GROUND  = 0x30    # the memoised ground z (= MapQueryAltitude - 1.0)
V_VEXT    = 0x40    # per-agent vertical term, subtracted from +0x8C at 3 read sites
V_QUERY   = 0x74    # the cache key: x f, y f, plane i  (+0x80 is a 4th, unread word)
V_POS     = 0x84    # x f, y f, z f -- the position triple; z at +0x8C
V_MODEL   = 0x60    # the 'mdl ' handle (AvAgent:818 asserts it non-null)
V_TYPE    = 0x9C    # class tag
TYPE_AVCHAR = 0xDB


def _u32(b, off=0):
    return struct.unpack_from("<I", b, off)[0]


def _i32(b, off=0):
    return struct.unpack_from("<i", b, off)[0]


def _f32(b, off=0):
    return struct.unpack_from("<f", b, off)[0]


def blank(why):
    """A refusal, named. Never a zero that could pass for a reading."""
    return {"ok": False, "why": why, "ground_z": None, "cached_z": None,
            "vext": None, "view": None, "model_handle": None,
            "qx": None, "qy": None, "qplane": None, "px": None, "py": None}


def read_groundz(read, module_base, agent_id):
    """One agent's AgentView height row, or a named refusal.

    `read(addr, n) -> bytes|None` is the caller's cross-process reader.
    `module_base` is Gw.exe's loaded base (keytap.module_info); every constant
    above is an RVA against it, because the client is ASLR'd.
    """
    if agent_id is None or agent_id < 0:
        return blank("bad-agent-id")
    raw = read(module_base + RVA_VIEW_COUNT, 4)
    if not raw or len(raw) < 4:
        return blank("no-view-count")
    count = _u32(raw)
    # A sanity bound of our own: the array is ArenaNet's growable Array and a
    # wrong base reads a wild dword. 1<<20 is far above any live agent count
    # and far below a pointer-shaped value.
    if count == 0 or count > (1 << 20):
        return blank("view-count-implausible:%d" % count)
    if agent_id >= count:
        return blank("id-past-count")
    raw = read(module_base + RVA_VIEW_ARRAY, 4)
    if not raw or len(raw) < 4:
        return blank("no-view-array")
    array = _u32(raw)
    if not array:
        return blank("view-array-null")
    raw = read(array + agent_id * 4, 4)
    if not raw or len(raw) < 4:
        return blank("no-view-slot")
    view = _u32(raw)
    if not view:
        return blank("view-null")
    blk = read(view, 0xC4)              # AvAgent's span; AvChar's own fields start here
    if not blk or len(blk) < 0xC4:
        return blank("short-view-block")
    tag = _u32(blk, V_TYPE)
    if tag != TYPE_AVCHAR:
        return blank("type-tag-0x%X" % tag)
    vid = _u32(blk, V_ID)
    if vid != agent_id:
        # THE ROUND TRIP FAILED. The client's own registrar makes this
        # impossible on a correct read, so this is our error, not the client's.
        return blank("id-roundtrip %d != %d" % (vid, agent_id))
    return {
        "ok": True, "why": None, "view": view,
        "ground_z": _f32(blk, V_POS + 8),      # +0x8C
        "cached_z": _f32(blk, V_GROUND),       # +0x30, what the getter returns
        "vext": _f32(blk, V_VEXT),             # +0x40
        "px": _f32(blk, V_POS), "py": _f32(blk, V_POS + 4),
        "qx": _f32(blk, V_QUERY), "qy": _f32(blk, V_QUERY + 4),
        "qplane": _i32(blk, V_QUERY + 8),
        "model_handle": _u32(blk, V_MODEL),
    }
