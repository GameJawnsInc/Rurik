#!/usr/bin/env python3
"""Watch the client's own movement solution while the operator plays.

    python toolkit/clientscan/movetap.py --selftest     # no client needed
    python toolkit/clientscan/movetap.py --seconds 120  # poll a running client

WHAT THIS IS FOR. Our server grants a click with GAME_SMSG 0x0029 and, seconds
later, the CLIENT teleports onto that destination -- 2,305 u in 0.23 s = 9,878
u/s, measured on the wire in run 20260819T135526. The wire cannot say WHY,
because everything that decides it happens inside the client between two
packets. This reads that decision out of the running process.

THE MECHANISM, read out of the pinned binary (build 38797, and see BUILDS
below). 0x0029's handler 0x005FD890 calls 0x00602A40, which writes the wire
point into BOTH m_segmentPoint (+0x88) and m_targetPoint (+0x9C), and calls
0x005FE950, which caches a velocity at +0xB0/+0xB4 and an arrival time at +0x48:

    m_timeStopMovement = m_timeUpdated + floor(dist * 1000 / (maxSpeed * moveSpeed))

in absolute milliseconds on the world clock. Until that instant the agent is
dead-reckoned. AT that instant -- and the compare at 0x006001EB is `time == +0x48`
EXACTLY, not `>=` -- the movement tick either glides again or TELEPORTS, chosen
by m_flags bit 18 (0x40000) at 0x0060029F. 0x00602A40 passes isWaypoint = 0
(push at 0x00602A7F), which CLEARS bit 18 at 0x005FEA49. **So every grant we
send arms the teleport branch and never the glide branch.**

WHAT THIS PROBE ASKS, and it is not the obvious question. The arrival formula,
applied to the flagship run's own numbers with no free parameter, predicts the
jump at t = 45.6 s. It happened at t = 40.1 s -- 5.4 s EARLY. Two readings
survive and nothing static can separate them:

    (A) +0x58 was stale, so the arrival time was computed from an old clock;
    (B) something client-side re-armed +0x48 after the grant.

So the record below is built around +0x48 and the world clock, NOT around the
position.

WHY NOT THE POSITION -- and this is the mistake this file exists to avoid.
+0x78 is not where the agent is. It is where the agent was at +0x58, advanced
only when 0x005FF880 runs, and that has 8 call sites, all event-driven, none per
frame. Across a PERFECTLY NORMAL glide the +0x78 trace is therefore: flat for
the whole leg, then one step onto the destination -- which is exactly what a
teleport looks like. A probe that watched +0x78 would have called every
ordinary click-to-move a teleport. The live position has to be reconstructed:

    live = (+0x78, +0x7C) + (+0xB0, +0xB4) * (now - +0x58) * 0.001

which is why every sample carries +0x58, the velocity and the world clock, and
why `--selftest` refuses to pass without them.

THE PREDICTION, stated before any run (toolkit/authsrv/probes.py's rule, applied
to a memory probe): at the moment a grant lands, +0x48 holds the exact
millisecond the jump will occur and +0x9C..+0xA8 holds the exact point it will
land on. So the observed lag must equal (+0x48 - world clock at grant), and NOT
any function of distance. REFUTED IF: +0x48 changes between the grant and the
jump (that names a re-armer, reading B), or the jump lands at a time that is
neither +0x48 nor any value +0x48 ever held (that means the tick was missed and
the agent reckoned past its destination, which is a third mechanism).

THE SECOND QUESTION, added 2026-08-20: IS THE SNAP TEST EVEN REACHED?
----------------------------------------------------------------------------
The client decides whether to hard-copy the SYNC agent onto the locally
predicted ASYNC one in 0x006055E0 (return 1 = NO SNAP, 0 = SNAP). Prior
measurement over 623 paired intervals in 5 movetap x gamesrv pairs: 0 of 24
snaps began below the 300 u gate, yet 303 of 327 above-threshold intervals
(92.7%) did NOT snap. A gate that 92.7% of its own population walks past is
not the thing doing the deciding, so the leading hypothesis is that the test
is FENCED OFF for long stretches and never evaluated at all.

THE FENCE IS TWO CONDITIONS IN THE CALLER, 0x00605FC0, and both are readable
from here. Every displacement below was read out of the pinned binary and is
re-checked against its bytes by `--selftest` section 5:

    00605FCE  mov ebx,[edi+0x10]        agent id            (A_ID)
    00605FD1  mov edx,[edi+0x24]        world index         (A_WORLD)
    00605FDA  cmp ebx,[esi+0x28]        id < count          (T_STATE_COUNT)
    00605FF6  mov eax,[esi+0x20]        the record array    (T_STATE_ARRAY)
    00605FF9  lea ecx,[ebx*8] / sub ecx,ebx / [eax+ecx*4]   stride 7*4 = 0x1C
    00606002  cmp dword[record+0x00],0  clientControlled    (S_CONTROLLED)
    00606009  je  0x00606103            zero -> the test is SKIPPED
    00606013  cmp edx,1 / je 0x0060610B world 1 -> SKIPPED too
    0060601C  call 0x006055E0           the test, only here

`esi` is AgTrack, and it is AGBASE + 0x1CC: 0x005FE9CC calls the TLS accessor
0x0047F660, takes `[eax+8]` (the same AGBASE this file already resolves) and
0x005FEBE5 adds 0x1CC to it. Two other call sites do the same (0x005FC77E,
0x00602BB7).

WHAT HAPPENS WHEN THE FENCE IS SHUT IS NOT "NOTHING", and this is the part a
summary gets wrong. Reading the caller's tail:

    fence open,  world != 1   -> call 0x006055E0; the three gates decide
    fence open,  world == 1   -> call 0x00605840 unconditionally (no test)
    fence shut,  world == 0   -> call 0x00605840 unconditionally (no test)
    fence shut,  world != 0   -> return; nothing happens at all

so `gate_reach` below is a four-valued string, not a boolean.

clientControlled is ONE-SHOT. 0x00605F10 sets record+0x00 to 1 and record+0x04
to 0 **only when record+0x00 is currently zero** (0x00605F3F/0x00605F43), and
its two call sites hang off local player input; 0x00605F70 (Clear) zeroes both
again, and the caller invokes it at 0x0060602E on exactly the SNAP branch.

THE PREDICTION, stated before the run: `fence_state` is "shut" for a majority
of samples taken while the operator walks under our grants, and the snaps
movesync finds fall in the "test-runs" minority. That would explain 92.7%
without any gate doing anything.
REFUTED IF: `fence_state` reads "test-runs" on essentially every sample -- then
the fence is not the explanation and the gates are, which contradicts gate 1
subsuming all 24 snaps. INCONCLUSIVE, AND THE RUN MUST SAY SO, if the state
flips at a rate approaching the reader's own sample rate: polling at ~12 Hz
cannot resolve a fence that toggles faster, and that is the one outcome that
buys the hook route (toolkit/clientscan/trnhook/) its cost. The transition
count is printed for exactly this reason.

0 IS A MEANINGFUL VALUE HERE -- it means the fence is SHUT -- so a failed read
must never produce one. `agtrack_fence()` returns a STRING state whose failure
values live in a different value domain ("unread:<why>") than its two real
answers ("open"/"shut"), because a `None` or a `0` sentinel is falsy in the
same way the real answer is and a consumer cannot tell them apart.

READ ONLY, by construction: PROCESS_VM_READ only, via toolkit/harness/keytap.py.
It never writes, never injects, never launches anything. Start a client with
`python toolkit/harness/session.py --keep-open` first.

BUILDS. The struct DISPLACEMENTS below are stable across builds 38519, 38797 and
38833 (measured: `fld [esi+0x9c]` sits at the same displacement in all three
while the code around it moved 0x3600). The ADDRESSES are not, and the two this
file dereferences -- _tls_index and the module base -- are the kind that do not
return a wrong number, they read whatever else is mapped. Hence the build gate
and the self-checks, which are the whole reason this file is longer than the
poll loop it contains.
"""
import argparse
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import keytap      # noqa: E402
import pinned      # noqa: E402
import vaultpath   # noqa: E402
import agentprobe  # noqa: E402  (gw_pids only -- its ARRAY is a DIFFERENT struct)

# The two absolute minimums, below which nothing is readable whatever the
# reader's rate: a run has to have lasted long enough for the phenomenon to
# occur and to hold enough samples to see it. Set from the shortest run in this
# arc that produced a real finding (60.8 s, 786 samples) with a wide margin --
# NOT from a guess, and deliberately far below it so this pair never becomes the
# binding constraint. The rate floor in main() is the one that does the work.
MIN_SPAN_SECONDS = 5.0
MIN_SAMPLES = 40

IMAGE_BASE = 0x00400000
# _tls_index. The PE TLS directory's AddressOfIndex reads 0x00C0F300, and
# 0x0047F660 -- the accessor every Agent-context read goes through -- is
# literally `mov ecx,[0xC0F300] / mov eax,fs:[0x2C] / mov eax,[eax+ecx*4] /
# mov eax,[eax+8] / ret`.
RVA_TLS_INDEX = 0x00C0F300 - IMAGE_BASE

# --- the Agent context, reached from the TLS block -------------------------
OFF_CTX_IN_TLS = 0x08      # [tls_block + 8] -> ctx        (0x0047F660)
OFF_AGBASE = 0x08          # [ctx + 8] -> AGBASE           (0x005FD8A1)
OFF_CHCLI = 0x44           # [ctx + 0x44] -> ChCli ctx     (0x0084DCB5)
OFF_CONTROLLED = 0x2AC     # [chcli + 0x2AC] -> agent ID   (0x0084DCB8)
OFF_SYNC_ARRAY = 0xE8      # [AGBASE + 0xE8] -> AgAgent*[] (0x005FD8CE)
OFF_SYNC_COUNT = 0xF0      # [AGBASE + 0xF0]               (0x005FD8B2, Array:587)
OFF_WORLD_STRIDE = 0x64    # imul eax,[esi+0x24],0x64      (0x005FF896)
OFF_WORLD_CLOCK = 0x148    # [AGBASE + world*0x64 + 0x148] (0x005FF89E)

# --- AgTrack, the record that FENCES the snap test at 0x006055E0 -----------
# `this` = AGBASE + 0x1CC. Read out of build 38797 and re-derived from its own
# bytes by selftest section 5, which encodes each instruction FROM the constant
# below rather than comparing two copies of a literal.
OFF_AGTRACK = 0x1CC        # lea ecx,[edi+0x1cc]           (0x005FC77E)
T_ARMED_ID = 0x14          # mov [edi+0x14],esi            (0x00605F45)
T_STATE_ARRAY = 0x20       # mov eax,[esi+0x20]            (0x00605FF6)
T_STATE_COUNT = 0x28       # cmp ebx,[esi+0x28]            (0x00605FDA)
STATE_STRIDE = 0x1C        # [ebx*8]-ebx, scaled by 4      (0x00605FF9, 0x006060EB)
S_CONTROLLED = 0x00        # cmp dword[rec],0              (0x00606002)
S_HIST_HEAD = 0x04         # the history chain head        (0x00605F4F, 0x006056AF)
# +0x08..+0x14 is a four-dword point on the chain NODES (0x0060571A..0x0060572F);
# on the RECORD itself only +0x00 and +0x04 are touched by any code read so far,
# and +0x18 is UNVERIFIED -- which is why the whole 28 bytes are stored raw
# rather than named field by field.
AGTRACK_MAX_AGENTS = 100000   # same sanity bound resolve() uses on the SYNC count

FENCE_OPEN = "open"        # clientControlled != 0 -- 0x006055E0 can be reached
FENCE_SHUT = "shut"        # clientControlled == 0 -- the test is never evaluated

# --- AgAgent displacements. Stable across 38519/38797/38833. ---------------
A_ID = 0x10                # the agent id. 0x00605758 uses it to index the
                           # ASYNC array at AGBASE+0x14C and 0x00605FCE uses it
                           # to index AgTrack, so it is the id and not a
                           # look-alike -- and requiring it to equal the id we
                           # resolved is a check the artifact can refute.
A_FLAGS = 0x20             # bit 17 IN_WORLD, bit 18 glide-vs-teleport, bit 19 STALE
A_WORLD = 0x24
A_STOP = 0x48              # m_timeStopMovement, absolute ms, 0 = not moving
A_UPDATED = 0x58           # m_timeUpdated -- the epoch m_point is dated to
A_MAXSPEED = 0x5C          # float, units/second
A_MOVESPEED = 0x60         # float multiplier, AGENT_MAX_MOVE_SPEED = 1.0
A_POINT = 0x78             # m_point   : x f, y f, plane i, w i
A_SEGMENT = 0x88           # m_segmentPoint (assert AgAgent:1143)
A_TARGET = 0x9C            # m_targetPoint  (assert AgAgent:1144) -- the landing point
A_VEL = 0xB0               # vx f, vy f, units/second
AGENT_SPAN = 0xD0          # every field above lies inside; do NOT extend blind

FLAG_IN_WORLD = 0x00020000
FLAG_GLIDE = 0x00040000    # SET = re-issue a timed move; CLEAR = teleport
FLAG_STALE = 0x00080000    # INTERNAL_FLAG_MOVEMENT_STALE (assert AgAgent:1198)
INVALID_POS = 0x7F800000   # +inf, AGENT_INVALID_POSITION


class TapFail(Exception):
    """Loud. Every failure here is 'we read the wrong thing', never a bad number."""


def u32(b, off=0):
    return struct.unpack_from("<I", b, off)[0]


def i32(b, off=0):
    return struct.unpack_from("<i", b, off)[0]


def f32(b, off=0):
    return struct.unpack_from("<f", b, off)[0]


# --------------------------------------------------------------------------
# The 32-bit TEB of a WOW64 target, read from 64-bit Python.
#
# THIS IS THE STEP MOST LIKELY TO BE SILENTLY WRONG, so it validates itself.
# NtQueryInformationThread(ThreadBasicInformation) hands back the SIXTY-FOUR bit
# TEB for a WOW64 thread; ThreadLocalStoragePointer at +0x2C belongs to the
# THIRTY-TWO bit TEB, which is a different structure living at a fixed offset
# after it. Using +0x2C on the 64-bit TEB reads an unrelated dword and every
# read after it is garbage that looks like data.
#
# The 32-bit TEB carries a self-pointer at +0x18 (NT_TIB.Self). Requiring it to
# equal the address we think we are reading is a check the artifact can refute,
# so a wrong WOW64_TEB_OFFSET fails here rather than three dereferences later.
# --------------------------------------------------------------------------
WOW64_TEB_OFFSET = 0x2000
TEB32_SELF = 0x18
TEB32_TLS_POINTER = 0x2C


def _threads_of(pid):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    TH32CS_SNAPTHREAD = 0x4

    class TE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ThreadID", wintypes.DWORD),
                    ("th32OwnerProcessID", wintypes.DWORD),
                    ("tpBasePri", ctypes.c_long),
                    ("tpDeltaPri", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD)]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    out, e = [], TE32()
    e.dwSize = ctypes.sizeof(TE32)
    if k32.Thread32First(snap, ctypes.byref(e)):
        while True:
            if e.th32OwnerProcessID == pid:
                out.append(e.th32ThreadID)
            if not k32.Thread32Next(snap, ctypes.byref(e)):
                break
    k32.CloseHandle(snap)
    return out


def _teb64_of(tid):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    THREAD_QUERY_INFORMATION = 0x0040

    class TBI(ctypes.Structure):
        _fields_ = [("ExitStatus", ctypes.c_long),
                    ("TebBaseAddress", ctypes.c_void_p),
                    ("UniqueProcessId", ctypes.c_void_p),
                    ("UniqueThreadId", ctypes.c_void_p),
                    ("AffinityMask", ctypes.c_void_p),
                    ("Priority", ctypes.c_long),
                    ("BasePriority", ctypes.c_long)]
    k32.OpenThread.restype = wintypes.HANDLE
    h = k32.OpenThread(THREAD_QUERY_INFORMATION, False, tid)
    if not h:
        return None
    try:
        tbi = TBI()
        n = ctypes.c_ulong(0)
        rc = ntdll.NtQueryInformationThread(h, 0, ctypes.byref(tbi),
                                            ctypes.sizeof(tbi), ctypes.byref(n))
        return None if rc else tbi.TebBaseAddress
    finally:
        k32.CloseHandle(h)


def tls_blocks(pid, handle, tls_index):
    """Every thread's TLS block for `tls_index`, with the TEB32 self-check.

    Returns [(tid, block_address)], validated. Empty is a hard failure upstream,
    never a quiet zero -- a probe that reads nothing must say so.
    """
    out = []
    for tid in _threads_of(pid):
        teb64 = _teb64_of(tid)
        if not teb64:
            continue
        teb32 = teb64 + WOW64_TEB_OFFSET
        raw = keytap.read_handle(handle, teb32 + TEB32_SELF, 4)
        if not raw or u32(raw) != (teb32 & 0xFFFFFFFF):
            continue          # not a WOW64 TEB32 at that offset -- skip, loudly upstream
        raw = keytap.read_handle(handle, teb32 + TEB32_TLS_POINTER, 4)
        if not raw or not u32(raw):
            continue
        slot = keytap.read_handle(handle, u32(raw) + tls_index * 4, 4)
        if not slot or not u32(slot):
            continue
        out.append((tid, u32(slot)))
    return out


def resolve(pid, handle, base, verbose=False):
    """(ctx, agbase, agent_id, agent_ptr). Raises TapFail with a reason.

    Re-resolved on EVERY poll on purpose. The agent array is ArenaNet's growable
    Array template -- its own bounds assert (Array:587) fires in this very
    lookup -- and array[id] is a heap object destroyed across map loads. A
    cached pointer would keep returning plausible numbers from freed memory.
    """
    raw = keytap.read_handle(handle, base + RVA_TLS_INDEX, 4)
    if not raw:
        raise TapFail("could not read _tls_index")
    tls_index = u32(raw)
    blocks = tls_blocks(pid, handle, tls_index)
    if not blocks:
        raise TapFail(
            "no thread yielded a TLS block. Either WOW64_TEB_OFFSET (0x2000) is "
            "wrong for this Windows build -- the TEB32 self-check at +0x18 "
            "rejected every thread -- or the process is not the 32-bit client.")
    for _tid, block in blocks:
        raw = keytap.read_handle(handle, block + OFF_CTX_IN_TLS, 4)
        if not raw or not u32(raw):
            continue
        ctx = u32(raw)
        raw = keytap.read_handle(handle, ctx + OFF_AGBASE, 4)
        if not raw or not u32(raw):
            continue
        agbase = u32(raw)
        cnt = keytap.read_handle(handle, agbase + OFF_SYNC_COUNT, 4)
        arr = keytap.read_handle(handle, agbase + OFF_SYNC_ARRAY, 4)
        if not cnt or not arr:
            continue
        count, array = u32(cnt), u32(arr)
        if not array or not (0 < count < 100000):
            continue
        raw = keytap.read_handle(handle, ctx + OFF_CHCLI, 4)
        if not raw or not u32(raw):
            continue
        raw = keytap.read_handle(handle, u32(raw) + OFF_CONTROLLED, 4)
        if not raw:
            continue
        aid = u32(raw)
        if aid == 0 or aid >= count or (aid & 0xF0000000):
            continue          # ChCliApi's own bound: !(id & 0xF0000000)
        raw = keytap.read_handle(handle, array + aid * 4, 4)
        if not raw or not u32(raw):
            continue
        if verbose:
            print(f"  ctx 0x{ctx:08X}  AGBASE 0x{agbase:08X}  array 0x{array:08X}"
                  f"  count {count}  controlled agent {aid}")
        return ctx, agbase, aid, u32(raw)
    raise TapFail("found TLS blocks but none resolved to an Agent context with a "
                  "controlled agent -- is the client actually in a map?")


# The shape every fence read returns, including the ones that read nothing.
# Every value here is a SENTINEL: the two strings say "not read" in a value
# domain that cannot collide with "open"/"shut"/"test-runs", and every number
# is None. A caller that forgets a key gets None, never a plausible zero.
FENCE_KEYS = ("fence_state", "gate_reach", "fence_raw", "hist_head",
              "state_record", "agtrack_count", "agtrack_armed",
              "agent_id_field")


def _fence_blank(why):
    return {"fence_state": "unread:" + why, "gate_reach": "unread:" + why,
            "fence_raw": None, "hist_head": None, "state_record": None,
            "agtrack_count": None, "agtrack_armed": None,
            "agent_id_field": None}


def agtrack_fence(read, agbase, aid, agent_block):
    """Is the snap test at 0x006055E0 REACHED for agent `aid`? Never guesses.

    `read(addr, n) -> bytes|None` so this is drivable from a fake memory in
    `--selftest`; at run time it is a `keytap.read_handle` closure.

    RETURNS A STRING, and that is the whole design. `clientControlled == 0` is
    a REAL ANSWER -- it means the fence is shut and the test never runs -- so a
    failed read that returned 0, or None, or False would be indistinguishable
    from it to every downstream `if`. The failure values are therefore
    "unread:<why>", which is truthy, is not equal to "shut", and names what
    went wrong in the record itself rather than in a log line nobody keeps.

    `gate_reach` is four-valued because the caller's tail is (0x00606009,
    0x00606013, 0x00606103, 0x0060610B):

        "test-runs"    fence open, world != 1 -- 0x006055E0 decides
        "world1:apply" fence open, world == 1 -- 0x00605840, no test
        "shut:apply"   fence shut, world == 0 -- 0x00605840, no test
        "shut:noop"    fence shut, world != 0 -- the caller returns
    """
    if agent_block is None or len(agent_block) < A_WORLD + 4:
        return _fence_blank("agent-block-short")
    out = _fence_blank("no-attempt")
    agent_id = u32(agent_block, A_ID)
    world = i32(agent_block, A_WORLD)
    out["agent_id_field"] = agent_id
    if agent_id != aid:
        # We resolved `aid` through ChCli and dereferenced the SYNC array with
        # it; the client indexes AgTrack with the agent's OWN +0x10. If those
        # disagree we are holding the wrong object, and every field below it
        # would be a confident number about somebody else.
        return dict(_fence_blank("agent-id-mismatch"), agent_id_field=agent_id)

    # +0x20, +0x24 and +0x28 in one read -- three cross-process round trips per
    # poll is the difference between 12 Hz and 10 Hz on this reader.
    hdr = read(agbase + OFF_AGTRACK + T_STATE_ARRAY, 0x0C)
    if not hdr or len(hdr) < 0x0C:
        return dict(_fence_blank("agtrack-header-unreadable"),
                    agent_id_field=agent_id)
    array = u32(hdr, 0x00)
    count = u32(hdr, T_STATE_COUNT - T_STATE_ARRAY)
    out["agtrack_count"] = count
    for why, bad in (("state-array-null", not array),
                     ("state-count-implausible",
                      not (0 < count < AGTRACK_MAX_AGENTS)),
                     # ArenaNet's own bound, asserted at 0x00605FDA as
                     # `index < count` (Array:587). Past it the client would
                     # fire its own assert, so past it we are not reading
                     # AgTrack.
                     ("id-out-of-bounds", aid >= count)):
        if bad:
            return dict(_fence_blank(why), agent_id_field=agent_id,
                        agtrack_count=count)

    # Best effort, and deliberately NOT allowed to void the answer: which agent
    # the re-armer last touched (0x00605F45). Useful for reading a shut fence,
    # not load-bearing for it.
    armed = read(agbase + OFF_AGTRACK + T_ARMED_ID, 4)
    if armed and len(armed) >= 4:
        out["agtrack_armed"] = u32(armed)

    rec = read(array + aid * STATE_STRIDE, STATE_STRIDE)
    if not rec or len(rec) < STATE_STRIDE:
        return dict(_fence_blank("record-unreadable"), agent_id_field=agent_id,
                    agtrack_count=count, agtrack_armed=out["agtrack_armed"])

    controlled = u32(rec, S_CONTROLLED)
    out["state_record"] = rec.hex()      # all 28 bytes: +0x18 is UNVERIFIED and
    out["fence_raw"] = controlled        # is kept raw rather than given a name
    out["hist_head"] = u32(rec, S_HIST_HEAD)
    out["fence_state"] = FENCE_OPEN if controlled else FENCE_SHUT
    out["gate_reach"] = (("test-runs" if world != 1 else "world1:apply")
                         if controlled
                         else ("shut:apply" if world == 0 else "shut:noop"))
    return out


def sample(handle, agbase, agent_ptr, aid=None):
    """One agent snapshot plus the world clock it must be read against."""
    blk = keytap.read_handle(handle, agent_ptr, AGENT_SPAN)
    if not blk or len(blk) < AGENT_SPAN:
        return None
    world = i32(blk, A_WORLD)
    clk = keytap.read_handle(
        handle, agbase + world * OFF_WORLD_STRIDE + OFF_WORLD_CLOCK, 4)
    if not clk:
        return None
    now = i32(clk)
    flags = u32(blk, A_FLAGS)
    updated = i32(blk, A_UPDATED)
    vx, vy = f32(blk, A_VEL), f32(blk, A_VEL + 4)
    px, py = f32(blk, A_POINT), f32(blk, A_POINT + 4)
    # THE RECONSTRUCTION. m_point is dated to m_timeUpdated; the live position is
    # that plus the cached velocity over the elapsed milliseconds. Sampling
    # m_point alone is what would have made every ordinary glide look like a
    # teleport -- it only moves when 0x005FF880 runs, which is event-driven.
    dt = (now - updated) * 0.001
    # THE FENCE. `aid=None` is a caller that did not ask, which is a THIRD
    # thing again -- not "open", not "shut", not "we tried and failed" -- so it
    # gets its own reason string rather than being folded into a read error.
    fence = (agtrack_fence(lambda a, n: keytap.read_handle(handle, a, n),
                           agbase, aid, blk)
             if aid is not None else _fence_blank("no-agent-id-passed"))
    return {
        "now": now, "stop": i32(blk, A_STOP), "updated": updated,
        **fence,
        "flags": flags,
        "in_world": bool(flags & FLAG_IN_WORLD),
        "glide": bool(flags & FLAG_GLIDE),
        "stale": bool(flags & FLAG_STALE),
        "maxspeed": round(f32(blk, A_MAXSPEED), 3),
        "movespeed": round(f32(blk, A_MOVESPEED), 4),
        "point": [round(px, 2), round(py, 2), i32(blk, A_POINT + 8)],
        "live": [round(px + vx * dt, 2), round(py + vy * dt, 2)],
        "segment": [round(f32(blk, A_SEGMENT), 2), round(f32(blk, A_SEGMENT + 4), 2),
                    i32(blk, A_SEGMENT + 8)],
        "target": [round(f32(blk, A_TARGET), 2), round(f32(blk, A_TARGET + 4), 2),
                   i32(blk, A_TARGET + 8)],
        "target_invalid": u32(blk, A_TARGET) == INVALID_POS,
        "vel": [round(vx, 2), round(vy, 2)],
    }


def selftest():
    """Everything that can be checked without a client. Exits non-zero on any gap."""
    bad = 0
    print("movetap selftest -- no client required\n")
    print("1. the reconstruction is present, because sampling m_point alone")
    print("   would call every ordinary glide a teleport")
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    for need, why in (
            ('"updated"', "m_timeUpdated -- the epoch m_point is dated to"),
            ('"now"', "the world clock, the only shared time base"),
            ('"live"', "the reconstructed position"),
            ("vx * dt", "the actual integration"),
            ('"glide"', "m_flags bit 18 -- which decides teleport vs glide"),
            ('"stop"', "m_timeStopMovement -- the whole question")):
        ok = need in src
        bad += not ok
        print(f"   [{'PASS' if ok else 'FAIL'}] {need:14} {why}")
    print("\n2. the TEB32 walk validates itself rather than trusting 0x2000")
    ok = "TEB32_SELF" in src and "!= (teb32 & 0xFFFFFFFF)" in src
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] the self-pointer check is present -- a wrong "
          f"WOW64_TEB_OFFSET must fail here, not three dereferences later")
    print("\n3. we do NOT reuse agentprobe's array, which is a different struct")
    # Asked of the SYNTAX TREE, not of a grep. A grep for the forbidden name
    # matches the grep's OWN literal -- the first draft of this check failed
    # itself for exactly that reason, which is a check that cannot pass, the
    # mirror of a check that cannot fail.
    import ast
    used = {n.attr for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "agentprobe"}
    ok = used == {"gw_pids"}
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] agentprobe is used for {sorted(used)} and "
          f"nothing else. AgentView's +0x9C is the 0xDB type tag while AgAgent's "
          f"+0x9C is m_targetPoint.x, so resolving an agent through agentprobe's "
          f"array would pass a CHARACTER check on the wrong object")
    print("\n4. a client is present?")
    pids = agentprobe.gw_pids()
    print(f"   {'yes, pid(s) ' + str(pids) if pids else 'no Gw.exe running -- '
          'start one with session.py --keep-open to go further'}")

    bad += _selftest_fence_bytes()
    bad += _selftest_fence_refuses()
    bad += _selftest_fence_verdict()

    print("\nselftest " + ("FAILED" if bad else "passed"))
    return 1 if bad else 0


# --------------------------------------------------------------------------
# 5. THE FENCE OFFSETS, RE-DERIVED FROM ARENANET'S OWN BYTES.
#
# Sections 1-3 ask the source about itself, which cannot catch a wrong NUMBER:
# every constant this file added on 2026-08-20 would pass all three while
# pointing at the wrong dword, and reading the wrong dword here does not
# error -- it returns a confident 0, which is the answer that means "the fence
# is shut". So each instruction below is ENCODED FROM the module constant and
# then matched against the pinned image. Change `T_STATE_ARRAY` to 0x24 and the
# expected bytes become `8b 46 24`, which is not what sits at 0x00605FF6, and
# this section goes red. Comparing a literal to a copy of itself would not.
#
# Stdlib only: the patterns are fixed, so no disassembler is needed and the
# bare-machine rule that governs asserts.py / msgshape.py is respected here too.
# --------------------------------------------------------------------------
IMAGE_BASE_PE32 = 0x00400000


def _pe_sections(buf):
    pe = struct.unpack_from("<I", buf, 0x3C)[0]
    nsec = struct.unpack_from("<H", buf, pe + 6)[0]
    optsz = struct.unpack_from("<H", buf, pe + 20)[0]
    imgbase = struct.unpack_from("<I", buf, pe + 24 + 28)[0]
    tbl = pe + 24 + optsz
    out = []
    for i in range(nsec):
        o = tbl + 40 * i
        vsz, va, rsz, raw = struct.unpack_from("<IIII", buf, o + 8)
        out.append((imgbase + va, max(vsz, rsz), raw))
    return imgbase, out


def _bytes_at(buf, secs, va, n):
    for sva, sz, raw in secs:
        if sva <= va < sva + sz:
            return buf[raw + (va - sva): raw + (va - sva) + n]
    return b""


def _modrm_disp(op, modrm_reg_bits, base_reg, disp):
    """`op /r [base+disp]` the way MSVC emits it: disp8 under 0x80, else disp32."""
    if disp < 0x80:
        return bytes([op, 0x40 | modrm_reg_bits | base_reg, disp])
    return bytes([op, 0x80 | modrm_reg_bits | base_reg]) + struct.pack("<I", disp)


def _selftest_fence_bytes():
    print("\n5. the AgTrack fence offsets, re-derived from the pinned binary")
    try:
        path, why = pinned.find()
    except SystemExit as e:
        print(f"   [SKIP] {e}")
        print("   this section proves nothing on a machine with no vault "
              "snapshot; it is NOT counted as a pass")
        return 0
    buf = open(path, "rb").read()
    imgbase, secs = _pe_sections(buf)
    if imgbase != IMAGE_BASE_PE32:
        print(f"   [FAIL] image base 0x{imgbase:08X}, and every VA below is "
              f"absolute for 0x{IMAGE_BASE_PE32:08X}")
        return 1
    print(f"   against {os.path.basename(os.path.dirname(path))}/Gw.exe -- {why}")

    # (constant name, VA, expected bytes BUILT FROM the constant, what it means)
    ebx, esi, edi, eax = 3, 6, 7, 0
    cases = [
        ("A_ID", 0x00605FCE, _modrm_disp(0x8B, ebx << 3, edi, A_ID),
         "mov ebx,[edi+id] -- the agent id the client indexes AgTrack with"),
        ("A_WORLD", 0x00605FD1, _modrm_disp(0x8B, 2 << 3, edi, A_WORLD),
         "mov edx,[edi+world] -- the other half of the fence"),
        ("T_STATE_COUNT", 0x00605FDA, _modrm_disp(0x3B, ebx << 3, esi,
                                                  T_STATE_COUNT),
         "cmp ebx,[esi+count] -- ArenaNet's own id<count bound"),
        ("T_STATE_ARRAY", 0x00605FF6, _modrm_disp(0x8B, eax << 3, esi,
                                                  T_STATE_ARRAY),
         "mov eax,[esi+array] -- the record array"),
        ("T_ARMED_ID", 0x00605F45, _modrm_disp(0x89, esi << 3, edi, T_ARMED_ID),
         "mov [edi+armed],esi -- the id the re-armer last touched"),
        ("S_HIST_HEAD", 0x00605F4F,
         b"\xc7\x44\x88" + bytes([S_HIST_HEAD]) + b"\x00\x00\x00\x00",
         "mov dword[record+head],0 -- the chain the re-armer resets"),
        ("OFF_AGTRACK", 0x005FC77E,
         b"\x8d\x8f" + struct.pack("<I", OFF_AGTRACK),
         "lea ecx,[edi+0x1CC] where edi is [ctx+8], i.e. AGBASE"),
        ("OFF_AGBASE", 0x005FE9D2, _modrm_disp(0x8B, 1 << 3, eax, OFF_AGBASE),
         "mov ecx,[eax+8] straight out of the TLS accessor 0x0047F660"),
        # mod=00 IS the proof the field sits at +0x00: any other displacement
        # would be encoded, and encoding it is what this line does.
        ("S_CONTROLLED", 0x00606002,
         (b"\x83\x3c\x88\x00" if S_CONTROLLED == 0
          else b"\x83\x7c\x88" + bytes([S_CONTROLLED]) + b"\x00"),
         "cmp dword[array+id*4+ctl],0 -- clientControlled, the fence itself"),
        ("STATE_STRIDE", 0x006060EB, b"\x83\xc3" + bytes([STATE_STRIDE]),
         "add ebx,stride -- the caller's own walk of the same array"),
    ]
    n = 0
    for name, va, want, meaning in cases:
        got = _bytes_at(buf, secs, va, len(want))
        ok = got == want
        n += not ok
        print(f"   [{'PASS' if ok else 'FAIL'}] {name:14} 0x{va:08X} "
              f"{want.hex():<18} {'' if ok else 'GOT ' + got.hex() + '  '}"
              f"{meaning}")

    # The stride is a product, not a displacement, so it gets its own arithmetic
    # check against the two instructions that build it.
    lea8 = _bytes_at(buf, secs, 0x00605FF9, 7) == b"\x8d\x0c\xdd\x00\x00\x00\x00"
    sub1 = _bytes_at(buf, secs, 0x00606000, 2) == b"\x2b\xcb"
    ok = lea8 and sub1 and STATE_STRIDE == (8 - 1) * 4
    n += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] STATE_STRIDE   0x00605FF9 "
          f"lea ecx,[ebx*8] then sub ecx,ebx, scaled by 4 in the SIB: "
          f"(8-1)*4 = {(8 - 1) * 4}, constant says {STATE_STRIDE}")
    return n


# --------------------------------------------------------------------------
# 6. THE REFUSALS. 0 MEANS "THE FENCE IS SHUT", so every way of failing to read
# it must land somewhere a consumer cannot confuse with that.
#
# Driven off a FAKE memory rather than a client, so it runs on a bare machine
# and so each failure can actually be provoked -- a null array pointer and an
# out-of-bounds id do not occur on demand in a live process, which is precisely
# why they would otherwise never be tested.
# --------------------------------------------------------------------------
def _fake_agent(agent_id, world=0):
    b = bytearray(AGENT_SPAN)
    struct.pack_into("<I", b, A_ID, agent_id)
    struct.pack_into("<i", b, A_WORLD, world)
    return bytes(b)


def _selftest_fence_refuses():
    print("\n6. the fence read REFUSES rather than returning a plausible 0")
    ARRAY, AG = 0x0A000000, 0x10000000

    def mem(array_ptr, count, record):
        def read(addr, n):
            if addr == AG + OFF_AGTRACK + T_STATE_ARRAY and n == 0x0C:
                return struct.pack("<III", array_ptr, 0, count)
            if addr == AG + OFF_AGTRACK + T_ARMED_ID and n == 4:
                return struct.pack("<I", 7)
            if record is not None and addr == array_ptr + 7 * STATE_STRIDE:
                return record[:n]
            return None
        return read

    open_rec = struct.pack("<II", 1, 0xDEADBEEF) + bytes(STATE_STRIDE - 8)
    shut_rec = struct.pack("<II", 0, 0) + bytes(STATE_STRIDE - 8)
    cases = [
        ("open fence reads open", mem(ARRAY, 64, open_rec), _fake_agent(7),
         "open", "test-runs", 1),
        ("shut fence reads shut -- a REAL 0, and it must survive",
         mem(ARRAY, 64, shut_rec), _fake_agent(7), "shut", "shut:apply", 0),
        ("world 1 skips the test even with the fence open",
         mem(ARRAY, 64, open_rec), _fake_agent(7, world=1), "open",
         "world1:apply", 1),
        ("shut fence in a non-zero world is a NO-OP, not an apply",
         mem(ARRAY, 64, shut_rec), _fake_agent(7, world=2), "shut",
         "shut:noop", 0),
        ("null record array", mem(0, 64, open_rec), _fake_agent(7),
         "unread:state-array-null", "unread:state-array-null", None),
        ("id out of bounds", mem(ARRAY, 3, open_rec), _fake_agent(7),
         "unread:id-out-of-bounds", "unread:id-out-of-bounds", None),
        ("record read fails", mem(ARRAY, 64, None), _fake_agent(7),
         "unread:record-unreadable", "unread:record-unreadable", None),
        ("AgTrack header read fails", lambda a, n: None, _fake_agent(7),
         "unread:agtrack-header-unreadable",
         "unread:agtrack-header-unreadable", None),
        ("the agent's own id disagrees with the one we resolved",
         mem(ARRAY, 64, open_rec), _fake_agent(9),
         "unread:agent-id-mismatch", "unread:agent-id-mismatch", None),
        ("implausible count", mem(ARRAY, 1 << 30, open_rec), _fake_agent(7),
         "unread:state-count-implausible",
         "unread:state-count-implausible", None),
        ("a short agent block", mem(ARRAY, 64, open_rec), bytes(4),
         "unread:agent-block-short", "unread:agent-block-short", None),
    ]
    n = 0
    for what, read, blk, want_state, want_reach, want_raw in cases:
        r = agtrack_fence(read, AG, 7, blk)
        ok = (r["fence_state"] == want_state and r["gate_reach"] == want_reach
              and r["fence_raw"] == want_raw
              and set(r) == set(FENCE_KEYS))
        n += not ok
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}\n"
              f"          -> {r['fence_state']} / {r['gate_reach']} / "
              f"raw={r['fence_raw']!r}"
              + ("" if ok else f"   WANTED {want_state} / {want_reach} / "
                               f"raw={want_raw!r}"))

    # The one that matters most, stated as its own assertion rather than left
    # implicit in the table: no failure mode may produce the string that means
    # "shut", and no failure mode may produce a raw 0.
    fails = [agtrack_fence(read, AG, 7, blk)
             for what, read, blk, s, g, raw in cases if raw is None]
    ok = all(f["fence_state"].startswith("unread:") and f["fence_raw"] is None
             and f["gate_reach"] != "shut:apply" for f in fails)
    n += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] none of the {len(fails)} failure "
          f"modes returns \"shut\" or a raw 0 -- 0 is the answer that means the "
          f"fence is SHUT, so a failed read that produced one would be read as "
          f"the finding")

    # And the mirror: a healthy read must actually POPULATE the field. A
    # selftest that only proves the refusals is one a stub returning
    # "unread:everything" would pass.
    good = agtrack_fence(mem(ARRAY, 64, open_rec), AG, 7, _fake_agent(7))
    ok = (good["fence_raw"] == 1 and good["hist_head"] == 0xDEADBEEF
          and good["state_record"] == open_rec.hex()
          and good["agtrack_count"] == 64 and good["agtrack_armed"] == 7
          and good["agent_id_field"] == 7)
    n += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a healthy read populates every "
          f"field: raw={good['fence_raw']!r} head={good['hist_head']!r} "
          f"count={good['agtrack_count']!r} armed={good['agtrack_armed']!r} "
          f"record={(good['state_record'] or '')[:16]}... "
          f"-- a stub that only ever refused would fail here")
    return n


def _selftest_fence_verdict():
    """7. the summary REFUSES a bad denominator and an aliased fence."""
    print("\n7. the run-level fence verdict can go red")
    import contextlib
    import io
    cases = [
        ("a clean run passes", {"shut:apply": 800, "test-runs": 200}, 4, 0),
        ("nothing read at all", {}, 0, 1),
        ("a quarter of samples unread refuses the shares",
         {"shut:apply": 700, "unread:record-unreadable": 300}, 4, 1),
        ("a fence flipping near the sample rate refuses",
         {"shut:apply": 500, "test-runs": 500}, 260, 1),
        # THE REGRESSION CASE, and it is why the bar changed on 2026-08-20.
        # A 15 ms open window against a 185 ms shut one at ~10 Hz is about ten
        # TRUE transitions per second -- nothing a 12 Hz reader can resolve --
        # and it lands at a 7.5% open share with phi = 0.138. The old
        # `flips * 4 >= n` bar needed 0.25 and therefore PASSED it, printing
        # "not aliased" over a number that was pure sampling phase. Simulated
        # A = 0.998. If this case ever returns 0 again the instrument is lying
        # in exactly the band H1 lives in.
        ("a SKEWED fast fence refuses too -- the old bar could not see this",
         {"shut:apply": 925, "test-runs": 75}, 138, 1),
        ("a slow fence at the same skewed share still passes",
         {"shut:apply": 925, "test-runs": 75}, 7, 0),
        ("just under both bars still passes",
         {"shut:apply": 700, "test-runs": 60, "unread:record-unreadable": 240},
         6, 0),
    ]
    bad = 0
    for what, reach, flips, want in cases:
        n = sum(reach.values())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = fence_verdict(reach, flips, n or 1, 12.0)
        ok = got == want
        bad += not ok
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}: returned {got}, "
              f"wanted {want}")
    return bad


def calibrate(handle, agbase, ptr, aid=None, reads=40):
    """How fast can this reader ACTUALLY sample? Measured, before the run.

    WHY THIS EXISTS. The floor used to be `seconds * hz * 0.5` -- half the
    REQUESTED rate. But a full sample is one resolve plus ~20 cross-process
    ReadProcessMemory calls, and on the owner's machine that sustains about
    13 Hz against a default request of 50. So the floor could not be met by a
    healthy run at the default flags, and run 20260819T171436 duly printed FAIL
    over 786 samples that contained 304 re-arms, 7 arrivals and the measurement
    that overturned this arc's mechanism. A floor that fires on every good run
    is worse than no floor: it is how a REAL failure gets waved through.

    The fix must not be "compute the floor from the achieved rate" -- that is
    circular and could never fail, which is the other half of the same rule.
    So capability is measured HERE, before the run, and the floor is set from
    it. A run that then samples at half its own demonstrated capability really
    did stall, and that is a finding.
    """
    # Calibrated WITH the fence read, because the floor it sets is scored
    # against a loop that does one. Measuring a cheaper sample than the run
    # performs would set a floor the run cannot meet -- the exact defect this
    # function was written to fix, from the other side.
    t0 = time.perf_counter()
    got = 0
    for _ in range(reads):
        if sample(handle, agbase, ptr, aid) is not None:
            got += 1
    dt = time.perf_counter() - t0
    if dt <= 0 or got == 0:
        return None
    return got / dt


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int)
    ap.add_argument("--hz", type=float, default=50.0)
    ap.add_argument("--seconds", type=float, default=180.0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--any-build", action="store_true",
                    help="read a build the pin does not recognise. The struct "
                         "displacements are stable across 38519/38797/38833 but "
                         "_tls_index's ADDRESS is not.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    pids = [a.pid] if a.pid else agentprobe.gw_pids()
    if not pids:
        print("no Gw.exe running. Start one: python toolkit/harness/session.py "
              "--keep-open")
        return 2
    pid = pids[-1]
    base, path = keytap.module_info(pid, "Gw.exe")
    pinned.assert_build(path, why=f"reading the movement model out of pid {pid}",
                        allow_any=a.any_build)

    print("PREDICTION, stated before the run and not after it:")
    print("  When a grant lands, +0x48 (m_timeStopMovement) holds the exact")
    print("  millisecond the jump will occur and m_targetPoint holds the exact")
    print("  point it will land on, so the observed lag must equal")
    print("  (+0x48 - the world clock at grant) and NOT any function of distance.")
    print("REFUTED IF: +0x48 changes between the grant and the jump (that names a")
    print("  re-armer), or the jump lands at a time +0x48 never held (the tick was")
    print("  missed and the agent reckoned past its destination).\n")

    print("SECOND PREDICTION, for the fence on the snap test at 0x006055E0:")
    print("  clientControlled (AgTrack record+0x00) is ZERO for a majority of")
    print("  samples taken while the operator walks under our grants, so the")
    print("  test is never evaluated -- which would explain 303 of 327")
    print("  above-threshold intervals not snapping without any gate acting.")
    print("REFUTED IF: gate_reach reads \"test-runs\" on essentially every sample.")
    print("  Then the fence is not the explanation and the gates are, which")
    print("  contradicts gate 1 subsuming all 24 observed snaps.")
    print("INCONCLUSIVE IF: the state flips at a rate approaching this reader's")
    print("  own -- polling cannot resolve that, and the transition count printed")
    print("  at the end is what says so. That is the outcome, and the only one,")
    print("  that buys the trnhook route its compiler and its injection.\n")

    out_dir = vaultpath.vault_path("captures", "movetap")
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    out = os.path.join(out_dir, f"movetap-{stamp}.jsonl")
    handle = keytap.open_read(pid)
    n = 0
    changes = 0
    last = None
    interrupted = False
    reach = {}                 # gate_reach -> count, every value including unread
    flips = 0                  # gate_reach transitions -- the aliasing witness
    t_start = time.time()
    t_end = t_start + a.seconds
    period = 1.0 / a.hz
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": "head", "pid": pid, "exe": path,
                                 "hz": a.hz, "wall": stamp}) + "\n")
            _ctx, agbase, aid, ptr = resolve(pid, handle, base, verbose=True)
            cap_hz = calibrate(handle, agbase, ptr, aid)
            target_hz = a.hz if cap_hz is None else min(a.hz, cap_hz)
            if cap_hz is None:
                print("could not calibrate the reader; floor falls back to the "
                      "requested rate")
            else:
                print(f"reader capability {cap_hz:.1f} Hz (measured, 40 reads)"
                      + (f" -- BELOW the requested {a.hz:.0f} Hz, so the floor "
                         f"is set from {target_hz:.1f}"
                         if cap_hz < a.hz * 0.95 else ""))
            print(f"polling agent {aid} at {a.hz:.0f} Hz for {a.seconds:.0f}s "
                  f"-> {out}\n")
            while time.time() < t_end:
                try:
                    _ctx, agbase, aid, ptr = resolve(pid, handle, base)
                except TapFail:
                    time.sleep(period)
                    continue
                s = sample(handle, agbase, ptr, aid)
                if s is None:
                    time.sleep(period)
                    continue
                s["kind"] = "sample"
                s["t"] = round(time.time(), 4)
                s["agent"] = aid
                fh.write(json.dumps(s) + "\n")
                n += 1
                reach[s["gate_reach"]] = reach.get(s["gate_reach"], 0) + 1
                # Print only what a human needs to see live: the arrival time
                # changing is the entire experiment.
                if last is not None and s["stop"] != last["stop"]:
                    changes += 1
                    d = s["stop"] - s["now"]
                    print(f"  +0x48 {last['stop']} -> {s['stop']} "
                          f"({'due in %.2fs' % (d / 1000.0) if s['stop'] else 'CLEARED'})"
                          f"  target {s['target'][:2]} glide={s['glide']}")
                # The fence opening or shutting is the second experiment, and
                # every transition is printed rather than summarised, because
                # the summary cannot distinguish "it changed twice" from "it
                # changed on every other sample and we are aliasing".
                if last is not None and s["gate_reach"] != last["gate_reach"]:
                    flips += 1
                    print(f"  fence {last['gate_reach']} -> {s['gate_reach']} "
                          f"(raw {last['fence_raw']!r} -> {s['fence_raw']!r}, "
                          f"armed {s['agtrack_armed']!r}) at "
                          f"t+{time.time() - t_start:.2f}s")
                last = s
                time.sleep(period)
    except KeyboardInterrupt:
        # Ctrl+C IS THE NORMAL WAY TO END A RUN. The operator stops when the
        # thing they were reproducing has happened, which is usually before
        # --seconds elapses. This used to escape as a traceback, so the summary
        # and the floor verdict never printed and the operator was left holding
        # a file with no idea whether it measured anything.
        interrupted = True
        print("\n  (interrupted -- scoring what was captured)")
    finally:
        import ctypes
        ctypes.WinDLL("kernel32").CloseHandle(handle)

    elapsed = max(1e-9, time.time() - t_start)
    rate = n / elapsed
    print(f"\n{n} samples over {elapsed:.1f}s = {rate:.1f} Hz, "
          f"{changes} change(s) to +0x48 -> {out}")
    if interrupted:
        print(f"  stopped early: {elapsed:.1f}s of the {a.seconds:.0f}s "
              f"requested. That is not a failure -- the floor below is scored "
              f"against the time actually run.")
    # A RUN THAT MEASURED NOTHING FAILED. Two things can make that true and they
    # are different: the poller never resolved an agent / sampled a handful of
    # times, or it ran for no time at all. Score them separately, and score the
    # rate against what this reader DEMONSTRATED it can do rather than against
    # what was asked for -- see calibrate().
    floor = int(elapsed * target_hz * 0.5)
    if elapsed < MIN_SPAN_SECONDS or n < MIN_SAMPLES:
        print(f"FAIL: {n} samples over {elapsed:.1f}s is too little to read "
              f"anything from (need {MIN_SAMPLES} samples and "
              f"{MIN_SPAN_SECONDS:.0f}s). This run measured nothing.")
        return 1
    if n < floor:
        print(f"FAIL: {n} samples is below the floor of {floor} -- half of "
              f"{target_hz:.1f} Hz over {elapsed:.1f}s, and this reader "
              f"measured itself at {target_hz:.1f} Hz before the run. It "
              f"stalled; do not read a null out of it.")
        return 1
    print(f"  floor {floor} met ({n} samples at half of {target_hz:.1f} Hz "
          f"over {elapsed:.1f}s).")
    return fence_verdict(reach, flips, n, rate)


def fence_verdict(reach, flips, n, rate):
    """Print what the fence did, and REFUSE a percentage over a bad denominator.

    Separate from main() so `--selftest` can prove it goes red: a summariser
    that only ever prints is one nobody can tell is working.
    """
    print("\nTHE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00):")
    if not reach:
        print("  no sample carried a gate_reach at all. This run says NOTHING "
              "about the fence.")
        return 1
    unread = sum(c for k, c in reach.items() if k.startswith("unread:"))
    for k, c in sorted(reach.items(), key=lambda kv: -kv[1]):
        print(f"  {k:34} {c:6d}  {100.0 * c / n:5.1f}%")
    # THE DENOMINATOR REFUSAL. A share of "shut" computed over a run that could
    # not read the record for a third of its samples is a number about the
    # reader, and this arc has already shipped one of those.
    if unread * 4 >= n:
        print(f"  REFUSED: {unread} of {n} samples ({100.0 * unread / n:.0f}%) "
              f"could not read the record. No share above is a fact about the "
              f"client. Fix the read before quoting any of them.")
        return 1
    # THE ALIASING REFUSAL, and it is the one that decides the route. A fence
    # that changes on a large share of consecutive samples is changing at or
    # above the reader's own rate, which polling cannot resolve at all -- the
    # counts would then be an artifact of WHEN we happened to look.
    # `flips * 4 >= n` was the bar here until 2026-08-20 and it COULD NOT FIRE
    # where the hypothesis lives. Under full aliasing consecutive samples are
    # near-independent Bernoulli(p), so E[flips]/pairs -> 2p(1-p), whose maximum
    # is 0.5 -- a duty cycle outside [14.6%, 85.4%] can never reach a raw 0.25 at
    # ANY flip rate. Simulated at 10.4 Hz over 45 s with exponential dwells: a
    # 15 ms open window against a 185 ms shut one is ~10 true transitions/s,
    # utterly unresolvable, and prints phi = 0.138 -- under the old bar it read
    # "not aliased" and the run would have reported a 7.5%/92.5% split as fact.
    # That is the exact shape of H1's own worked example.
    #
    # So compare phi against what full aliasing WOULD produce at the observed
    # duty cycle. A -> 1 means "indistinguishable from independent samples", i.e.
    # aliased; A -> 0 means the state persists across many samples and the shares
    # are real. Same simulation: 0.998 and 0.989 for the two skewed fast cases,
    # 0.853 balanced-fast, against 0.037 and 0.050 for 5 s and 2 s dwells.
    pairs = n - 1
    # "Open" is the share where the test would RUN -- `test-runs` alone. world1
    # is NOT open: world == 1 is the branch on which the caller skips the test
    # entirely. An earlier draft of this line added it and would have inflated
    # p, deflating A toward "not aliased" -- the wrong direction for a guard.
    p_open = reach.get("test-runs", 0) / n
    denom = 2.0 * p_open * (1.0 - p_open)
    alias = (flips / pairs) / denom if (pairs > 0 and denom > 0.0) else None
    if alias is not None and alias >= 0.5:
        print(f"  REFUSED: {flips} transition(s) over {pairs} usable pair(s) at "
              f"{rate:.1f} Hz is {alias:.2f} of what INDEPENDENT samples would "
              f"give at this {100.0 * p_open:.1f}% open share. The fence is "
              f"changing at or above this reader's own rate, so the shares "
              f"above are aliased and mean nothing. THIS is the outcome that "
              f"earns the hook: an int3 at 0x00606002 on the trnblock.c pattern "
              f"counts every evaluation instead of sampling them "
              f"(toolkit/clientscan/trnhook/).")
        return 1
    if alias is None:
        print(f"  {flips} transition(s) over {pairs} usable pair(s) at "
              f"{rate:.1f} Hz. The fence never changed state, so there is no "
              f"aliasing ratio to compute -- a single-state run is reported as "
              f"one, NOT as a resolved measurement.")
    else:
        print(f"  {flips} transition(s) over {pairs} usable pair(s) at "
              f"{rate:.1f} Hz = {alias:.2f} of the independent-sample "
              f"expectation at a {100.0 * p_open:.1f}% open share -- the fence "
              f"persists across many samples, so the shares above are not "
              f"aliased.")
    print("  Pair this file with its gamesrv capture: "
          "python toolkit/clientscan/movesync.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
