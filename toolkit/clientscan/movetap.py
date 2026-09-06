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

    fence open,  world != 1   -> the test at 0x006055E0; the exits decide
    fence open,  world == 1   -> 0x00605840, the history APPENDER, no test
    fence shut,  world == 0   -> 0x00605840, the history APPENDER, no test
    fence shut,  world != 0   -> return; nothing happens at all

so `gate_reach` below is a four-valued string, not a boolean.

0x00605840 IS THE HISTORY APPENDER, NOT AN APPLY -- it allocates a node
(0x00605A50), links it to the old head (0x00605A5D) and push-fronts it, with a
2500 ms dedup at 0x0060593A, and it never touches the ASYNC agent. So a shut
fence does NOT mean the server's position was applied; it means no correction
happens at all and the player's prediction is left alone. Both of those values
ended in `:apply` until 2026-08-20, which reads as the exact opposite and would
have driven server work at a problem that is not there. They are now
`shut:append` / `world1:append`, because a capture field is permanent, and the
old spelling is not written anywhere in this file -- a grep for it is the
landing check.

AND `gate_reach` IS A COUNTERFACTUAL LABEL ON A STATE READ, not an observation
of an execution. This is a SAMPLER OF STATE. It reads clientControlled and the
world index and names the branch 0x00605FC0 WOULD take if it ran; nothing here
sees 0x00605FC0 execute. "test-runs" does not mean the test ran and
"shut:append" does not mean the appender ran. Every sentence this file prints is
written that way on purpose, and a write-up that says "the caller reached
0x00605840" is stating an inference as an observation.

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
same way the real answer is and a consumer cannot tell them apart. Every field
this file added on 2026-08-20 -- `gate1`, `early_out_a`, `point_invalid` --
follows the same rule for the same reason: `False` is a real answer to "did
this exit fire", so a failed read renders as an "unread:<why>" STRING and never
as a bool.

THE FIVE EXITS OF 0x006055E0, AND WHY THIS FILE NOW READS THEIR OPERANDS.
Reaching the test is only half the question; which exit fires is the other half,
and until 2026-08-20 nothing here measured either. Two exits sit ABOVE gate 1:

    0x00605634-0x00605641   agent+0x48 != 0 && agent+0xC4 == 9  -> 1, NO SNAP
    0x00605643-0x0060567F   agent+0x78 and +0x7C both +inf      -> 1, NO SNAP

both of which present on a capture as "above the cut and nothing snapped" --
the exact shape the fence hypothesis claims as its own confirmation. Both
operands lie inside AGENT_SPAN, which is read in one block, so they cost ZERO
extra reads (`early_outs()`).

GATE 1 (0x006057E1) compares 300.0 against the separation between the SYNC
agent and its ASYNC twin. The twin is `[[AGBASE+0x14C] + id*4]`, bounded by
`[AGBASE+0x154]` (0x0060577A / 0x0060575E, where esi = AgTrack = AGBASE+0x1CC,
so the displacements are -0x80 and -0x78). The two sides are NOT dated to the
same clock: 0x006057A3 passes `[AgTrack-0x84]` = AGBASE+0x148 = the world-0
clock for the SYNC copy, and 0x006057A0 passes `[AgTrack-0x20]` = AGBASE+0x1AC
= the world-1 clock for the ASYNC one. Both are recorded per sample.

AND THE RECONSTRUCTION IS NOT THE ONE ABOVE -- 0x005FF820 CLAMPS. It returns
m_segmentPoint (+0x88..+0x94) verbatim whenever `agent+0x48 != 0` and the
requested time is at or past it, and only integrates otherwise (0x005FFB40,
`(t - +0x58)` as a signed 32-bit ms count times the 0.001 at 0x00A53748).
`position_at()` replicates that, clamp first. The older `live` field does NOT
clamp and is left alone because movesync scores against it; `sync_branch` says
which branch the faithful one took, so a consumer of `live` can tell when it is
reading past a stop. 0 of the 4,115-sample corpus was in the clamp branch, so
this is a divergence that has never yet fired -- which is exactly when it is
cheap to get right.

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
import math
import os
import statistics
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
# --- CANCELWALK-R7's operands, reachable from the SAME `ctx` (2026-08-24) ----
# The local walk-start applier 0x0081A8F0 gates on two fields of the
# CONTROLLER, and MOVE-DISPATCH 0x008163A0 resolves that object in its own
# first six instructions -- read out of the image at 0x008163A7:
#     e8 b492c6ff   call 0x0047F660        the TLS ctx accessor this file
#                                          already drives (OFF_CTX_IN_TLS)
#     8b 40 2c      mov eax,[eax+0x2C]     <- OFF_CTRL_CTX
#     8b b0 80060000 mov esi,[eax+0x680]   <- OFF_PLAYER_CONTROLLED
#     85 f6 / 0f84  test esi,esi / je      the null guard, mirrored below
#     8b 86 0c0100  mov eax,[esi+0x10C]    GATE A/C's operand
# So the operands are TWO dereferences from a pointer resolve() already holds,
# on an object whose identity the applier asserts for itself
# (`this == context->playerControlledChar`, ChCliBase.cpp:164).
# WHY THIS IS HERE AND NOT IN A DEBUGGER. An adversarial review of the
# hardware-breakpoint version (CANCELWALK-R7, `gatetrace.py`) established that
# the arc's stated reason for needing one was wrong on both halves: these are
# PERSISTENT OBJECT FIELDS, not per-frame transients, and the object is not
# unreachable. A poll sees them for as long as they are set. It cannot see a
# bit set and cleared inside one frame -- that residual, and only that, is what
# a breakpoint would still buy.
OFF_CTRL_CTX = 0x2C        # [ctx + 0x2C] -> the controller's context
OFF_PLAYER_CONTROLLED = 0x680   # [that + 0x680] -> playerControlledChar
CTRL_STATUS = 0x10C        # dword; bit 0x100 = GATE A, bit 0x10 = GATE C
CTRL_FLAGBYTE = 0x64       # byte;  bit 0x01   = GATE B
CTRL_BIT_A, CTRL_BIT_B, CTRL_BIT_C = 0x100, 0x01, 0x10
OFF_SYNC_ARRAY = 0xE8      # [AGBASE + 0xE8] -> AgAgent*[] (0x005FD8CE)
OFF_SYNC_COUNT = 0xF0      # [AGBASE + 0xF0]               (0x005FD8B2, Array:587)
OFF_WORLD_STRIDE = 0x64    # imul eax,[esi+0x24],0x64      (0x005FF896)
OFF_WORLD_CLOCK = 0x148    # [AGBASE + world*0x64 + 0x148] (0x005FF89E)

# --- the ASYNC twin, which is what gate 1 measures the SYNC agent against ----
# Displacements written as -0x80 / -0x78 / -0x20 from AgTrack in the image, and
# derived back to AGBASE-relative here so selftest section 5 can re-encode them.
OFF_ASYNC_ARRAY = 0x14C    # mov eax,[esi-0x80]            (0x0060577A)
OFF_ASYNC_COUNT = 0x154    # cmp eax,[esi-0x78]            (0x0060575E)
# The two clocks gate 1 dates its two operands to. They are DIFFERENT: the SYNC
# copy gets world 0's, the ASYNC copy world 1's, and using one for both would
# manufacture a separation out of nothing but clock skew.
OFF_WORLD1_CLOCK = OFF_WORLD_CLOCK + OFF_WORLD_STRIDE   # 0x1AC (0x006057A0)
# One read covers the world-0 clock, the ASYNC array, its count and the world-1
# clock -- 0x148 through 0x1AF. Two cross-process round trips per poll is the
# difference between 12 Hz and 10 Hz on this reader, so they are fetched as one.
GATE1_HDR_SPAN = OFF_WORLD1_CLOCK + 4 - OFF_WORLD_CLOCK

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
# +0x08..+0x14 is a four-dword point on the chain NODES (0x0060571A..0x0060572F).
#
# THE REST OF THIS COMMENT USED TO READ "on the RECORD itself only +0x00 and
# +0x04 are touched by any code read so far, and +0x18 is UNVERIFIED". BOTH
# HALVES ARE REFUTED BY THE BYTES, read 2026-08-21 out of the pinned build for
# REALFIX-I1, and the bytes win. The appender at 0x00605840 WRITES all five of
# +0x08..+0x18 on the record every time it runs (0x00605A0E `mov [esi+8],ebx`
# through 0x00605A25 `mov [esi+0x18],eax`, and again on the allocating path at
# 0x00605A38..0x00605A4D), and the walker READS +0x08..+0x14 back as the
# polyline's FIRST vertex before it ever touches a node (0x0060569A..0x006056AC,
# then 0x006056AF steps to the head). The appender's own head-match test
# compares the incoming point against record +0x08 / +0x0C / +0x10
# (0x00605948 / 0x0060595B / 0x0060596B). So:
S_HIST_POINT = 0x08        # x f, y f, plane i, w i -- the polyline's vertex 0
S_HIST_AT = 0x18           # the ms that vertex is dated to. Written from the
                           # agent's m_timeStopMovement when it is parked
                           # (0x00605904, off +0x48) and from the world clock
                           # when it is not (0x0060591B) -- so "the epoch of the
                           # cached point", RECONSTRUCTION for the semantics,
                           # OBSERVED for the two write sites.
# The whole 28 bytes are still stored raw as well: naming five of seven dwords
# is not the same as having read the eighth.
AGTRACK_MAX_AGENTS = 100000   # same sanity bound resolve() uses on the SYNC count

# --- REALFIX-I1: the history chain the match test walks --------------------
# EVERY DISPLACEMENT BELOW WAS READ OUT OF build 38797's OWN BYTES on
# 2026-08-21 (vault/client/2026-07-29_221c13772c7a/Gw.exe), from the appender
# 0x00605840-0x00605A93, its allocator 0x00604BB0-0x00604DD9 and the walker
# 0x006056A0-0x00605737. Nothing here is inherited from a prior comment.
#
#   ALLOCATION (0x00604DBB-0x00604DD9). A block is `count` at +0x00 then nodes
#   from +0x04 at a stride of 0x2C (`imul eax,ecx,0x2c` / `add eax,4` /
#   `add eax,edi`). The new node's +0x00 is written from the allocator's own
#   argument -- the world clock the appender passed (0x00604DCC) -- and its
#   +0x04 is written to ZERO (0x00604DCE). A block holds at most 0x100 nodes
#   (`cmp dword[edi],0x100`, 0x00604BD0; the allocation is 0x2c0c bytes).
#
#   RECYCLING, AND THIS COMMENT USED TO NAME THE WRONG NODE. It read "recycled
#   when its OLDEST node is more than 5000 ms old", printed inside a green
#   [PASS] line, and CONTRADICTED this repo's own FINDINGS.md:2894/:3674, which
#   had it right. REFUTED at the bytes, re-read 2026-08-21 out of build 38797:
#   the age test at 0x00604BFF is `sub ecx,[eax+edi-0x28]` with eax already
#   `count * 0x2C` (0x00604BFC), so the address is `block + 0x2C*count - 0x28`
#   = `block + 4 + (count-1)*0x2C` = node index count-1 -- the LAST APPENDED,
#   i.e. the block's NEWEST node. The bump allocator two hundred bytes down
#   (0x00604DBB) is what makes that identification: it takes `count`, forms
#   `block + 4 + count*0x2C`, then increments, so the node just written is
#   always index count-1. The SENSE was right and stays: `cmp ecx,0x1388` /
#   `jle 0x604d04` allocates a fresh 0x2c0c block when the delta is <= 5000 ms,
#   so recycling needs the newest node to be MORE than 5000 ms old -- a
#   strictly stronger guarantee than the old sentence claimed. And it is
#   reached ONLY when the current block is full (0x00604BD0's `jb 0x604dbb`
#   short-circuits straight to the bump allocator otherwise), which is why a
#   NODE may legitimately be minutes old: blocks turn over every 256 appends,
#   not every 5 s. Any age bound on a node would refuse real data.
#   The operand and the sense are both encoded into selftest section 5 now
#   (HIST_RECYCLE_OPERAND), so this paragraph can go red.
#
#   AND WHY A CHAIN CANNOT DANGLE INTO A RECYCLED BLOCK -- the real mechanism,
#   which was NOT in this file and is stronger than the 5 s bound it used to
#   argue from. Before reusing a block the client SEVERS every reference into
#   it. 0x00604C30-0x00604C77 walks every block's nodes and zeroes any
#   `node+0x04` landing in [block+4, block+0x2C04) (`mov dword[eax+4],0` at
#   0x00604C56, bound `lea ecx,[esi+0x2c04]` at 0x00604C49); 0x00604C89-
#   0x00604CC7 then walks the record array at [this+0x20] with count [this+0x28]
#   and stride 0x1C -- the SAME T_STATE_ARRAY / T_STATE_COUNT / STATE_STRIDE
#   this file reads -- and zeroes any `record+0x04` in that range (0x00604CBB).
#   So a walker that starts after the sever sees NULL, not garbage.
#
#   THE ONE HAZARD THAT SURVIVES THE SEVER, named because nothing else names it.
#   0x00604CF9 resets only the block's COUNT; the node bytes are left alone
#   (0x00605AA0, the call just above it, is a doubly-linked-list splice that
#   moves the block between lists and writes no node), and the pool is shared by
#   every agent's record -- which is exactly why the sever pass has to scan all
#   of them. So a read of a parent's `next` that lands BEFORE the sever, with
#   the target read landing AFTER the slot has been re-appended, yields another
#   agent's node under our agent's id. TORN-READ TEST 2 catches the realistic
#   form of this for free: a re-appended slot is stamped with the CURRENT world
#   clock, which is newer than the parent that (staleley) links to it, and a
#   node newer than its parent is `unread:node-time-inverted`. The residual
#   window is a re-append landing in the SAME MILLISECOND as the parent's own
#   stamp, which this walk cannot distinguish and does not claim to. Modelled in
#   selftest section 13 rather than asserted here.
#
#   LINKAGE (0x00605A55-0x00605A5D). `mov ecx,[esi+4]` then
#   `mov [edx+4],ecx` -- push-front, so +0x04 is the NEXT (older) node and the
#   head is the newest. The allocator having just zeroed it means the FIRST node
#   of a chain keeps next = 0, so THE TERMINATOR IS NULL. Confirmed from the
#   consumer side too: the walker advances with `mov esi,[esi+4]` and loops on
#   `test esi,esi / jne` (0x00605732-0x00605737).
#
#   POINT (0x00605A60-0x00605A75). Four consecutive dwords at +0x08, +0x0C,
#   +0x10, +0x14 -- x, y, plane, w -- copied from the same four the appender
#   read off the agent at +0x78..+0x84. The walker reads exactly those four
#   back at 0x0060571A..0x0060572F and hands `&node+8` to the segment test at
#   0x006056F5.
#
#   AND THE REST OF THE NODE, which this walk does NOT read and is recorded here
#   so the stride is auditable rather than asserted: +0x18/+0x1C velocity
#   (0x00605A81/0x00605A87, and the appender's own asserts 0x24d/0x24e require
#   them zero when the agent is parked), +0x20 m_maxSpeed (0x00605A7B), +0x24
#   m_moveSpeed (0x00605A8D), +0x28 the movement mode (0x00605A90). 0x2C total.
N_TIME = 0x00
N_NEXT = 0x04
N_POINT = 0x08             # x f, y f, plane i, w i
N_VEL = 0x18               # vx f, vy f      -- not read by this walk
N_MAXSPEED = 0x20          # float           -- not read by this walk
N_MOVESPEED = 0x24         # float           -- not read by this walk
N_MODE = 0x28              # int             -- not read by this walk
HIST_NODE_STRIDE = 0x2C
HIST_NODE_SPAN = 0x18      # +0x00..+0x17: time, next and the point, ONE read.
                           # OURS, not the client's: it is the read BUDGET the
                           # whole gate argument is priced in, so it is pinned
                           # to N_POINT+16 in section 13 rather than left free.
HIST_BLOCK_MAX = 0x100     # cmp dword[edi],0x100        (0x00604BD0)
HIST_BLOCK_RECYCLE_MS = 5000    # cmp ecx,0x1388         (0x00604C03), per BLOCK,
                           # measured on the block's NEWEST node -- see above
HIST_NODE_AGE_MS = 2500    # cmp eax,0x9c4 / jg          (0x0060593A), per node

# HOW FAR INTO THE FUTURE A NODE MAY BE DATED, and this number used to be
# HIST_NODE_AGE_MS on a ground that does not exist. The comment said the
# tolerance was "world-0/world-1 clock skew"; it is not, because there is only
# ONE clock in play. `sample()` reads `now` from
# AGBASE + world*OFF_WORLD_STRIDE + OFF_WORLD_CLOCK with `world` = the agent's
# own +0x24, and the appender stamps a node from the SAME slot -- 0x00605893
# `imul eax,[esi+0x24],0x64` with esi the agent, then 0x006058A5
# `mov edi,[eax+ecx-0x84]` with ecx the AgTrack `this` = AGBASE+0x1CC, and
# 0x1CC-0x84 = 0x148 = OFF_WORLD_CLOCK. Same agent, same world, same int32.
# THE REAL GROUND IS READ ORDERING: `sample()` reads the clock first and the
# nodes last, so a node appended in between is legitimately dated after `now`.
# The bound is therefore our own sample latency, not a client property -- 250 ms
# is 5x the 50 ms period REALFIX-T3 requires at 20 Hz and ~3x the ~13 Hz this
# reader sustains. A node further ahead than that means the sample straddled a
# stall, which is worth naming rather than folding into the data.
HIST_FUTURE_TOL_MS = 250

# HOW MANY NODES, AND WHY THIS IS GATED. A full sample is ~20 cross-process
# ReadProcessMemory calls and this reader sustains ~13 Hz; eight unconditional
# node reads is ~+40% and would drop it to ~7 Hz, which fights REALFIX-T3's
# residual budget directly (the sample phase IS the binding term after T1). The
# match test only matters where gate 1 could fire, so the chain is read only
# above 250 u -- comfortably below the 299.3326 u cut and below the 295 u edge
# of GATE1_BAND, so no sample that could be classified `above` is ever skipped.
# REALFIX.md section 2.4: "This conditional is a design requirement, not an
# optimisation."
HIST_MAX_NODES = 8
HIST_SEP_GATE = 250.0

# Pointer plausibility, on the same principle as the array/count refusals above:
# a node address that cannot be a node must NAME that rather than be read.
# LOW: the 64 KB null-guard region is never mapped in any Windows process.
# HIGH: Gw.exe's PE Characteristics are 0x0122, so IMAGE_FILE_LARGE_ADDRESS_AWARE
# (0x0020) is SET -- measured, not assumed -- which under WOW64 on 64-bit Windows
# puts the ceiling at 0xFFFEFFFF rather than 0x7FFEFFFF. A bound of 0x7FFF0000
# would therefore refuse legitimate high allocations. That sentence was true and
# CHECKED BY NOTHING until 2026-08-21: section 5 now reads the Characteristics
# word out of the pinned image, and section 13 walks a chain living ABOVE the
# 2 GB line, so lowering this ceiling "for safety" goes red instead of silently
# refusing real nodes. The old ceiling case planted its head AT PTR_MAX and so
# refused whatever the constant was -- a check that cannot fail.
# ALIGNMENT: nodes sit at block+4+i*0x2C and 0x2C is a multiple of 4, so every
# node address is 4-aligned whatever the block is. An unaligned candidate is a
# torn or mis-scaled pointer, not a node.
PTR_MIN = 0x00010000
PTR_MAX = 0xFFFF0000

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
# THE FOURTH WORD IS A HARDCODED ZERO, AND IT IS NOT A HEIGHT (MOVECODE-1z-cb).
# Asked for as "the z column" after an operator saw a body sunk ankle-deep into a
# stair tread, and settled from the binary rather than by a run: the client's own
# position reader at 0x005FFB40 does
#     0x005FFBD7  mov eax, [esi+0x80]      ; the agent's PLANE
#     0x005FFBDD  mov [ecx+8], eax         ; -> the out-point's plane slot
#     0x005FFBE0  mov dword [ecx+0xC], 0   ; -> the out-point's w slot, LITERAL 0
# so `w` is padding the client zeroes on every read. There is NO z in the agent's
# movement record at all, and AgAgent's 70 assert sites name no height, z,
# elevation or terrain field. Do not add a "z column" here: the field does not
# exist in this block, and the only candidate is that constant. If a rendered
# height is ever needed it lives on the render/model object, not on AgAgent.
A_POINT = 0x78             # m_point   : x f, y f, plane i, w i (w == 0, see above)
A_SEGMENT = 0x88           # m_segmentPoint (assert AgAgent:1143)
A_TARGET = 0x9C            # m_targetPoint  (assert AgAgent:1144) -- the landing point
A_VEL = 0xB0               # vx f, vy f, units/second
A_MODE = 0xC4              # movement mode; early-out A compares it as an INT
                           # against 9 (0x0060563A), and 0x00602660's own switch
                           # runs 1..8, so 9 is outside the normal range
# --- CANCELWALK-R5, added 2026-08-24. DECODE-ONLY: both offsets already lie
# inside the AGENT_SPAN block every poll fetches for BOTH copies, so surfacing
# them costs zero new cross-process reads. They exist to answer ONE question --
# does the async (drawn) body's walk-start run at all at a frozen cancel press?
A_REQ_TOKEN = 0x50         # the MOVE-REQUEST CORRELATION TOKEN, and the name
                           # matters because this file called it "planner" for
                           # one day and a hypothesis was built on the wrong
                           # noun. It is NOT a planner, NOT a queued-move
                           # store and NOT a path index. OBSERVED, three
                           # witnesses: the local applier increments a counter
                           # at `ChCliBase+0x68` (`0081ABD7 inc [ebx+0x68]`)
                           # and passes it as arg5 to AgApi MoveToPoint
                           # 0x005FC7A0, which stores it here (`005FC8ED mov
                           # [esi+0x50],eax`); the server command dispatcher
                           # 0x00606120 writes it from the message's own field
                           # +8 on its STOP/MOVE cases; and every READ in the
                           # image is the same payload push into the
                           # completion notifier 0x00603D40 (`ff7650 push
                           # [esi+0x50]`, guarded by `cmp [esi+0x24],1`), after
                           # which it is zeroed. **NOTHING BRANCHES ON IT** --
                           # zero cmp/test operands image-wide, and zero
                           # accesses of any kind inside the walk-start
                           # applier 0x0081A8F0's whole transitive closure
                           # (131 functions, positive-controlled).
                           # WHY IT IS STILL THE FIELD TO SAMPLE, and it is
                           # now a BETTER instrument than the wrong name
                           # implied: a fresh token is allocated on every
                           # SUCCESSFUL walk-start call and on nothing else,
                           # so `0 -> N` is direct evidence that the applier
                           # reached 0x005FC7A0 rather than bailing at a gate.
                           # It is a walk-start DETECTOR, never a cause.
                           # Capture movetap-20260824T141620 predates the
                           # rename and carries the old `planner` key.
A_DIR = 0xBC               # the facing/heading cache pair (f32 x, f32 y),
                           # FINDINGS:1628's atan2 lazy-angle operand at
                           # 0x005FFA1D. Which side of the walk gates writes it
                           # is exactly what R5 classifies -- do not assume.
AGENT_SPAN = 0xD0          # every field above lies inside; do NOT extend blind

FLAG_IN_WORLD = 0x00020000
FLAG_GLIDE = 0x00040000    # SET = re-issue a timed move; CLEAR = teleport
FLAG_STALE = 0x00080000    # INTERNAL_FLAG_MOVEMENT_STALE (assert AgAgent:1198)
INVALID_POS = 0x7F800000   # +inf, AGENT_INVALID_POSITION
VA_INVALID_POS = 0x00948654   # where the client keeps it; early-out B's operand
EARLY_OUT_A_MODE = 9       # cmp dword[ebx+0xC4],9         (0x0060563A)

# --- gate 1 (0x006057E1) ---------------------------------------------------
VA_GATE1_CUT = 0x00946564  # fld dword[0x946564] at 0x006057BF and 0x006057D8
GATE1_CUT = 300.0          # the float AT that address; selftest 5 reads it back
# The client's sqrt at 0x0046E870 is a LUT approximation biased high, so the
# effective cut is 299.3326 u rather than 300.0 -- a quantisation step this
# reader cannot resolve. Everything within +/- this band is REFUSED rather than
# classified. A probe that pretended to resolve it would be inventing a digit.
GATE1_BAND = 5.0
GATE1_ABOVE, GATE1_BELOW, GATE1_UNDECIDED = "above", "below", "undecided"


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
    0x00606013, 0x00606103, 0x0060610B). Each value names the branch the caller
    WOULD take on this state -- it is a COUNTERFACTUAL LABEL, not a witness that
    anything executed, because nothing in this file observes 0x00605FC0 running:

        "test-runs"     fence open, world != 1 -- the test at 0x006055E0
        "world1:append" fence open, world == 1 -- 0x00605840, the appender
        "shut:append"   fence shut, world == 0 -- 0x00605840, the appender
        "shut:noop"     fence shut, world != 0 -- the caller returns

    0x00605840 APPENDS TO THE HISTORY CHAIN. It is not an apply, and the two
    values above said `:apply` until 2026-08-20 -- which reads as "the server's
    position was written onto the player", the opposite of what a shut fence
    means. The string goes into every stored row permanently, so it was worth
    the rename.
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
    out["gate_reach"] = (("test-runs" if world != 1 else "world1:append")
                         if controlled
                         else ("shut:append" if world == 0 else "shut:noop"))
    return out


# The four values above, split by the one thing the aliasing ratio is about:
# would the caller CALL 0x006055E0 at all? `world1:append` is NOT open -- world
# 1 is the branch on which the caller skips the test entirely -- so it sits with
# the two shut values, and a `world1` <-> `shut` change is not a fence flip.
REACH_TEST_RUNS = "test-runs"
REACH_FENCED = ("world1:append", "shut:append", "shut:noop")

# THE TWO WAYS A POLL PRODUCES NO ROW AT ALL, which is a THIRD thing again --
# not a state the fence was in, and not a record we tried and failed to read.
# `agtrack_fence` never sees these: the loop gives up before `sample()` returns.
# They exist so the SEQUENCE has a row where the wall clock has a gap. Without
# one, `count_flips` scores the samples either side of an arbitrary stall as an
# adjacent pair and `episodes` merges two runs across it -- the exact
# contamination C3 removed, arriving by the door C3 did not cover. They are
# deliberately NOT tallied into `reach` or `n`: those two carry the shares and
# the floor, and a poll that produced no sample is not a sample. A run that
# drops many of them is caught by the floor (`n < elapsed * target_hz * 0.5`),
# which is the check that is actually about the reader's throughput.
REACH_DROPPED = "unread:sample-dropped"
REACH_UNRESOLVED = "unread:resolve-failed"


def reach_is_real(g):
    """A read that happened, whatever it said. The `unread:` domain is not one."""
    return isinstance(g, str) and not g.startswith("unread:")


def test_would_run(g):
    """The binary phi and p are both computed over. See REACH_FENCED."""
    return g == REACH_TEST_RUNS


# --------------------------------------------------------------------------
# THE FIVE EXITS OF 0x006055E0, read from operands rather than guessed at.
#
# `early_outs` costs nothing -- both its fields are already inside the block
# `sample()` fetches. `gate1_read` costs two reads and is the only thing that
# separates "gate 1 emptied the above-threshold population" from "an early-out
# vetoed it", which is the question the whole probe turns on.
# --------------------------------------------------------------------------
def _s32(x):
    """The client does this arithmetic in 32-bit signed ints. So do we.

    The world clock is a wrapping int32; `time - stop` and `time - updated` are
    both computed as `sub` + a sign test in 0x005FF820 / 0x005FFB40. Python's
    unbounded ints get the wrap wrong exactly once every 24.9 days of client
    uptime, and get it wrong in the direction that inverts the clamp test.
    """
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x


def position_at(blk, when):
    """AgAgent::position_at (0x005FF820), replicated -- and it CLAMPS FIRST.

    Returns (x, y, plane, branch), branch being "segment" or "integrated".

    THE CLAMP IS THE PART A REIMPLEMENTATION GETS WRONG. 0x005FF829 reads
    m_timeStopMovement; if it is non-zero AND `when - stop` is not negative
    (0x005FF832 `sub eax,ecx` / 0x005FF834 `js`), the client copies
    m_segmentPoint (+0x88..+0x94) out verbatim and never integrates at all.
    Only otherwise does it call 0x005FFB40, which is
    `m_point + m_velocity * (when - m_timeUpdated) * 0.001` with the plane taken
    from +0x80 and the 0.001 read from the double at 0x00A53748.

    So an agent that has reached its arrival tick sits ON its segment point, and
    dead-reckoning it past that point would invent a separation the client never
    computes. 0 of the existing 4,115-sample corpus was in this branch, which is
    why it has cost nothing so far and why it is cheap to get right now.
    """
    stop = i32(blk, A_STOP)
    if stop != 0 and _s32(when - stop) >= 0:
        return (f32(blk, A_SEGMENT), f32(blk, A_SEGMENT + 4),
                i32(blk, A_SEGMENT + 8), "segment")
    dt = _s32(when - i32(blk, A_UPDATED)) * 0.001
    return (f32(blk, A_POINT) + f32(blk, A_VEL) * dt,
            f32(blk, A_POINT + 4) + f32(blk, A_VEL + 4) * dt,
            i32(blk, A_POINT + 8), "integrated")


EARLY_KEYS = ("mode", "early_out_a", "point_invalid")


def early_outs(blk):
    """The two exits ABOVE gate 1, from bytes we already hold. Zero extra reads.

    `False` is a REAL answer here -- "this exit did not fire" is the finding in
    the case that matters -- so a block we could not read returns the
    "unread:<why>" STRING rather than False, exactly as `agtrack_fence` does for
    the fence. A caller writing `if row["early_out_a"]:` over the sentinel is
    wrong in a way `is True` is not; that is the price of a three-valued field
    and it is cheaper than a silent False.
    """
    if blk is None or len(blk) < AGENT_SPAN:
        return {"mode": None, "early_out_a": "unread:agent-block-short",
                "point_invalid": "unread:agent-block-short"}
    mode = i32(blk, A_MODE)
    return {
        "mode": mode,
        # 0x00605634 cmp [ebx+0x48],0 / je -> 0x0060563A cmp [ebx+0xC4],9 / je
        "early_out_a": bool(i32(blk, A_STOP) != 0 and mode == EARLY_OUT_A_MODE),
        # 0x00605643-0x0060567F: BOTH halves of m_point equal the +inf at
        # 0x00948654. One half alone is not the sentinel.
        "point_invalid": bool(u32(blk, A_POINT) == INVALID_POS
                              and u32(blk, A_POINT + 4) == INVALID_POS),
    }


R5_KEYS = ("reqtoken", "dir", "stop", "point_raw", "vel_raw")

GATE1_KEYS = ("sep", "gate1", "gate1_why", "async_ptr", "async_count",
              "async_id", "async_world", "sync_clock", "async_clock",
              "sync_at", "sync_branch", "async_at", "async_branch",
              # CANCELWALK-R5's async decodes ride here because this is where
              # the twin's block is in hand. GENERATED from R5_KEYS rather
              # than retyped: section 10 asserts every refusal carries the
              # FULL key set, and two hand-kept lists of the same names is
              # exactly the drift that makes such a check pass while the row
              # it guards is ragged.
              ) + tuple("async_" + k for k in R5_KEYS)


def _gate1_blank(why):
    blank = {"sep": None, "gate1": "unread:" + why, "gate1_why": None,
             "async_ptr": None, "async_count": None, "async_id": None,
             "async_world": None, "sync_clock": None, "async_clock": None,
             "sync_at": None, "sync_branch": None,
             "async_at": None, "async_branch": None}
    blank.update({"async_" + k: None for k in R5_KEYS})
    return blank


def _gate1_refuse(out, why):
    """Name the failure and wipe every DERIVED number, keeping the diagnostics.

    `async_count` and the two clocks are what a reader needs to tell "the twin
    array is not where we think" from "the id is out of range this frame", so
    they survive. Everything computed FROM the twin does not.
    """
    out = dict(out)
    out.update({"sep": None, "gate1": "unread:" + why, "gate1_why": None,
                "sync_at": None, "sync_branch": None,
                "async_at": None, "async_branch": None})
    # R5's async fields blank on the SAME rule as everything else computed from
    # the twin: a refused read must not leave last row's numbers standing, and
    # a missing key downstream is indistinguishable from a zero.
    out.update({"async_" + k: None for k in R5_KEYS})
    return out


def _r5_fields(blk, prefix=""):
    """CANCELWALK-R5's decode-only field set, for either world copy.

    `blk` is an AGENT_SPAN block already in hand -- this adds NO read. Returns
    the five keys under `prefix` ("" for the sync copy, "async_" for the twin).

    WHY RAW, and why every one of these is deliberately un-derived: R5 asks
    whether the local walk-start RAN, and the answer is a CHANGE across one
    press instant, not a quantity. `point_raw` and `vel_raw` are the stored
    fields (NOT `position_at`'s dead-reckoned reading, which moves on the world
    clock alone and would look like motion on a body that never moved), so a
    reader comparing two consecutive rows sees the client's own writes and
    nothing else. `reqtoken` is the move-request correlation token (see
    A_REQ_TOKEN): a fresh value is allocated per SUCCESSFUL walk-start call, so
    `0 -> N` is direct evidence the applier ran rather than bailing at a gate.
    It is never a distance, an index, or a cause -- nothing branches on it.
    """
    if blk is None or len(blk) < AGENT_SPAN:
        return {prefix + k: None for k in R5_KEYS}
    return {
        prefix + "reqtoken": u32(blk, A_REQ_TOKEN),
        prefix + "dir": [round(f32(blk, A_DIR), 4),
                         round(f32(blk, A_DIR + 4), 4)],
        prefix + "stop": i32(blk, A_STOP),
        prefix + "point_raw": [round(f32(blk, A_POINT), 2),
                               round(f32(blk, A_POINT + 4), 2)],
        prefix + "vel_raw": [round(f32(blk, A_VEL), 3),
                             round(f32(blk, A_VEL + 4), 3)],
    }


CTRL_KEYS = ("ctrl_ptr", "ctrl_status", "ctrl_flagbyte",
             "gate_a", "gate_b", "gate_c", "walk_suppressed", "ctrl_why")


def controller_read(read, ctx):
    """CANCELWALK-R7's gate operands, polled instead of trapped.

    `read(addr, n) -> bytes|None`, so this is drivable from a fake memory.
    Walks `[[ctx+0x2C]+0x680]` -- MOVE-DISPATCH's own first six instructions --
    and decodes the two fields the walk-start applier gates on.

    EVERY FAILURE IS NAMED, on this file's standing rule: a controller that
    could not be resolved must not read as "no gate set", because that is
    precisely the value the arc's primary hypothesis predicts. `gate_*` stay
    None unless the operands were really read, and `walk_suppressed` -- the
    one-line answer -- is None rather than False.

    The null guard mirrors the client's own (`test esi,esi / je` at
    0x008163B5): a null controller is a real state, not a read failure, and it
    gets its own reason.
    """
    blank = {k: None for k in CTRL_KEYS}
    if not ctx:
        blank["ctrl_why"] = "no-ctx"
        return blank
    raw = read(ctx + OFF_CTRL_CTX, 4)
    if not raw or not u32(raw):
        blank["ctrl_why"] = "ctrl-ctx-unreadable"
        return blank
    raw = read(u32(raw) + OFF_PLAYER_CONTROLLED, 4)
    if not raw:
        blank["ctrl_why"] = "controller-slot-unreadable"
        return blank
    ptr = u32(raw)
    if not ptr:
        blank["ctrl_ptr"], blank["ctrl_why"] = 0, "controller-null"
        return blank
    sw = read(ptr + CTRL_STATUS, 4)
    fb = read(ptr + CTRL_FLAGBYTE, 1)
    if not sw or not fb:
        blank["ctrl_ptr"], blank["ctrl_why"] = ptr, "operands-unreadable"
        return blank
    status, flag = u32(sw), fb[0]
    a = bool(status & CTRL_BIT_A)
    b = bool(flag & CTRL_BIT_B)
    c = bool(status & CTRL_BIT_C)
    return {"ctrl_ptr": ptr, "ctrl_status": status, "ctrl_flagbyte": flag,
            "gate_a": a, "gate_b": b, "gate_c": c,
            # The applier bails on ANY of the three, so this is the answer the
            # arc asks for -- but C is also tested by MOVE-DISPATCH before it
            # sends 0x003D, so a press that reached the wire had C clear.
            "walk_suppressed": (a or b or c), "ctrl_why": "ok"}


def gate1_read(read, agbase, aid, agent_block):
    """Gate 1's own operands: the SYNC agent against its ASYNC twin.

    `read(addr, n) -> bytes|None`, so this is drivable from a fake memory.

    THE SEPARATION IS NOT A WIRE PROXY. Every previous number in this arc came
    from comparing our own grants against the client's reported position, and
    that over-stated separation badly enough to be this arc's most frequent
    failure mode. This is the client's own two operands, each dated to the clock
    the client dates it to (world 0 for SYNC at 0x006057A3, world 1 for ASYNC at
    0x006057A0) and each run through `position_at`'s clamp.

    WHAT IT REFUSES. The 295-305 u band, because the client's LUT sqrt biases
    the effective cut to 299.3326 and this reader cannot resolve a quantisation
    step. And a plane mismatch: 0x00709990 compares the two points' plane words
    at 0x007099F1 and takes an entirely different path when they differ, which
    is not decoded here -- a 2D distance across two planes is not the number the
    client computes, so `gate1` says "undecided" and `gate1_why` says why.
    `sep` is still reported there; it is a real measurement of a 2D distance,
    just not of gate 1's predicate.
    """
    if agent_block is None or len(agent_block) < AGENT_SPAN:
        return _gate1_blank("agent-block-short")
    hdr = read(agbase + OFF_WORLD_CLOCK, GATE1_HDR_SPAN)
    if not hdr or len(hdr) < GATE1_HDR_SPAN:
        return _gate1_blank("clock-block-unreadable")
    out = _gate1_blank("no-attempt")
    out["sync_clock"] = i32(hdr, 0)
    out["async_clock"] = i32(hdr, OFF_WORLD1_CLOCK - OFF_WORLD_CLOCK)
    array = u32(hdr, OFF_ASYNC_ARRAY - OFF_WORLD_CLOCK)
    count = u32(hdr, OFF_ASYNC_COUNT - OFF_WORLD_CLOCK)
    out["async_count"] = count
    for why, bad in (
            # THE SYNC SIDE IS AN OBJECT WE MIGHT ALSO BE WRONG ABOUT, and this
            # check was missing while the identical one guarded `agtrack_fence`
            # (`agent-id-mismatch`) on the identical two inputs. Without it a
            # SYNC block whose +0x10 disagreed with the id we resolved produced
            # `gate_reach = "unread:agent-id-mismatch"` and `gate1 = "above"`
            # with a `sep` in the SAME ROW: a separation measured between two
            # different agents, classified, and shipped into the field
            # escalation trigger 2(b) reads. `below`/`above` with the fence open
            # is what buys the compiler, so a wrong-object read must not be able
            # to mint one.
            ("sync-id-mismatch", u32(agent_block, A_ID) != aid),
            ("async-array-null", not array),
            ("async-count-implausible",
             not (0 < count < AGTRACK_MAX_AGENTS)),
            # ArenaNet's own bound, asserted at 0x0060575E before the
            # index is used. Past it we are not reading the array.
            ("async-id-out-of-bounds", aid >= count)):
        if bad:
            return _gate1_refuse(out, why)
    slot = read(array + aid * 4, 4)
    if not slot or len(slot) < 4:
        return _gate1_refuse(out, "async-slot-unreadable")
    out["async_ptr"] = u32(slot)
    if not out["async_ptr"]:
        # The client asserts on this too, at 0x00605783/0x00605787.
        return _gate1_refuse(out, "async-slot-null")
    ablk = read(out["async_ptr"], AGENT_SPAN)
    if not ablk or len(ablk) < AGENT_SPAN:
        return _gate1_refuse(out, "async-agent-unreadable")
    out["async_id"] = u32(ablk, A_ID)
    out["async_world"] = i32(ablk, A_WORLD)
    if out["async_id"] != aid:
        # Same check, same reason, as agtrack_fence's: the array said this slot
        # is agent `aid` and the object says otherwise, so one of them is stale
        # and every number below would be about somebody else.
        return _gate1_refuse(out, "async-id-mismatch")
    sx, sy, sp, sbr = position_at(agent_block, out["sync_clock"])
    ax, ay, ap, abr = position_at(ablk, out["async_clock"])
    out["sync_at"] = [round(sx, 2), round(sy, 2), sp]
    out["async_at"] = [round(ax, 2), round(ay, 2), ap]
    out["sync_branch"], out["async_branch"] = sbr, abr
    # CANCELWALK-R5. The ASYNC block is the DRAWN body -- the one the operator
    # watches fail to move -- and until now only its position came out of this
    # 0xD0-byte read. These are decodes of bytes already in `ablk`: the
    # walk-start's own footprint (+0x50), its leg state (+0x48/+0xB0), where
    # the body actually is unclamped (+0x78) and the facing pair (+0xBC). A
    # frozen press with all of them unchanged says the walk-start never ran.
    out.update(_r5_fields(ablk, "async_"))
    # Classified on the value that gets STORED, not on the full-precision one,
    # so a reader can recompute `gate1` from the row and get the same answer. A
    # verdict that cannot be reproduced from the record it ships with is a
    # verdict nobody can audit.
    sep = round(math.hypot(sx - ax, sy - ay), 2)
    out["sep"] = sep
    if sp != ap:
        out["gate1"], out["gate1_why"] = GATE1_UNDECIDED, "plane-mismatch"
    elif abs(sep - GATE1_CUT) <= GATE1_BAND:
        out["gate1"], out["gate1_why"] = GATE1_UNDECIDED, "band"
    else:
        out["gate1"] = GATE1_ABOVE if sep > GATE1_CUT else GATE1_BELOW
    return out


# --------------------------------------------------------------------------
# REALFIX-I1 -- THE HISTORY CHAIN, WALKED.
#
# This is the measurement that turns round 6's elimination into observation.
# The match test the client runs at 0x006055E0 does not ask where the client IS;
# it asks whether the granted point lies within MATCH_RADIUS of the polyline the
# client has been walking, and that polyline is `record+0x08` followed by the
# chain. Every reading in this arc so far has had to INFER what was on it. This
# reads it.
#
# WHAT IT REFUSES. Everything, loudly, into `hist_why` -- the file's own
# `_fence_blank` idiom. A chain that does not terminate inside N, a node address
# outside the plausibility bounds, a node that cannot be read, a cycle, and a
# time sequence that could only come from a torn read all produce a named reason
# and the nodes read BEFORE the failure, never a silent short chain. A short
# chain and a refused chain look identical downstream unless the record says
# which it was, and "the polyline had no node near q" is exactly the reading
# candidate B is revived by.
# --------------------------------------------------------------------------
HIST_KEYS = ("hist", "hist_n", "hist_why", "hist_seed", "hist_seed_at",
             "hist_sync_plane", "hist_async_plane", "hist_reads")

HIST_OK = "ok"                      # walked to a null terminator inside N
HIST_EMPTY = "empty:head-null"      # a REAL empty chain: armed or cleared


def _hist_blank(why):
    return {"hist": None, "hist_n": None, "hist_why": why, "hist_seed": None,
            "hist_seed_at": None, "hist_sync_plane": None,
            "hist_async_plane": None, "hist_reads": 0}


def hist_is_complete(why):
    """The chain was walked end to end. An EMPTY chain counts; a truncated one
    does not, and neither does a refusal."""
    return why in (HIST_OK, HIST_EMPTY)


def _ptr_plausible(addr, span):
    """Could this be a node? See PTR_MIN / PTR_MAX / the 4-alignment note."""
    return (PTR_MIN <= addr and addr + span <= PTR_MAX and addr % 4 == 0)


def history_chain(read, rec, sep, async_ptr, agent_block, now,
                  max_nodes=None, gate=None):
    """The AgTrack polyline for one agent, newest vertex first.

    `read(addr, n) -> bytes|None`, so this is drivable from a fake memory and is
    tested that way -- no client, no ReadProcessMemory, no vault.

    `rec` is the 28 bytes `agtrack_fence` already fetched, so vertex 0 and the
    head pointer cost NOTHING here. `sep` and `async_ptr` come from
    `gate1_read`; `now` is the agent's own world clock, the same one the
    appender stamps a node with (0x006058A5 reads it at
    `[AgTrack + world*0x64 - 0x84]`, which is AGBASE + 0x148 + world*0x64).

    GATED ON `sep > gate`. Above 250 u and nowhere else -- see HIST_SEP_GATE.
    A sample below the gate is `not-attempted:below-gate`, which is a THIRD
    thing again on this file's usual rule: not a chain we read, not a chain we
    failed to read, and emphatically not an empty one.

    `max_nodes` and `gate` default to None and are resolved HERE rather than in
    the signature, because a default argument is bound at import: written
    `gate=HIST_SEP_GATE` the module constant is a copy, and rebinding
    `movetap.HIST_SEP_GATE` afterwards would change nothing while appearing to.
    THE CLAIM ABOUT WHICH CHECK PROVES THIS WAS WRONG, and it is corrected
    here: `test_movesync.py`'s three section-17 controls pass the parameters
    EXPLICITLY, so they stayed green when this was moved back into the
    signature. What proves it is section 13's own rebinding control, which
    moves the module global and calls this function WITHOUT the argument.
    """
    if max_nodes is None:
        max_nodes = HIST_MAX_NODES
    if gate is None:
        gate = HIST_SEP_GATE
    if rec is None or len(rec) < STATE_STRIDE:
        return _hist_blank("not-attempted:no-state-record")
    if sep is None:
        # gate 1 refused, so we do not know whether the gate would have fired.
        # Reading the chain anyway would spend the budget exactly where the
        # answer cannot be used.
        return _hist_blank("not-attempted:sep-unread")
    if not (sep > gate):
        return _hist_blank("not-attempted:below-gate")

    out = _hist_blank("no-attempt")
    out["hist_seed"] = [round(f32(rec, S_HIST_POINT), 2),
                        round(f32(rec, S_HIST_POINT + 4), 2),
                        i32(rec, S_HIST_POINT + 8), i32(rec, S_HIST_POINT + 12)]
    out["hist_seed_at"] = i32(rec, S_HIST_AT)
    # BOTH COPIES' OWN PLANE WORDS, at every chain sample. Without the pair,
    # grant #37 -- the only case separating "the plane echo CAUSES snaps" from
    # "the plane echo PERMITS them" -- stays unadjudicable. These are the raw
    # `agent+0x80` dwords and NOT `position_at`'s plane, which on the segment
    # branch returns m_segmentPoint's +0x90 instead.
    if agent_block is not None and len(agent_block) >= A_POINT + 12:
        out["hist_sync_plane"] = i32(agent_block, A_POINT + 8)
    if async_ptr and _ptr_plausible(async_ptr, A_POINT + 12):
        ap = read(async_ptr + A_POINT + 8, 4)
        out["hist_reads"] += 1
        if ap and len(ap) >= 4:
            out["hist_async_plane"] = i32(ap)

    head = u32(rec, S_HIST_HEAD)
    nodes = []
    out["hist"], out["hist_n"] = nodes, 0
    if not head:
        # 0x00605F48/0x00605F4F arms a record as (controlled=1, head=0) and
        # 0x006060A2/0x006060A9 clears it as (0, 0). An empty chain is a state
        # the client really is in, not a failure, and calling it one would turn
        # every re-arm into a fake refusal.
        out["hist_why"] = HIST_EMPTY
        return out

    seen = set()
    addr = head
    prev_t = None
    for _ in range(max_nodes):
        if addr in seen:
            out["hist_why"] = "unread:node-revisited"
            return out
        if not _ptr_plausible(addr, HIST_NODE_SPAN):
            out["hist_why"] = "unread:node-pointer-implausible"
            return out
        seen.add(addr)
        blk = read(addr, HIST_NODE_SPAN)
        out["hist_reads"] += 1
        if not blk or len(blk) < HIST_NODE_SPAN:
            out["hist_why"] = "unread:node-unreadable"
            return out
        t = i32(blk, N_TIME)
        # TORN-READ TEST 1: a node cannot be dated far into the future. THE
        # TOLERANCE IS READ ORDERING AND NOTHING ELSE -- `sample()` reads `now`
        # off the world clock before it reads any node, so an append that lands
        # in between is legitimately ahead of it. It is NOT cross-world clock
        # skew: the appender stamps from the agent's own world clock, the same
        # slot `sample()` read (0x00605893 / 0x006058A5; see HIST_FUTURE_TOL_MS).
        # That wrong ground shipped with a control fixture that could not
        # measure it, which is a control with no referent.
        if _s32(now - t) < -HIST_FUTURE_TOL_MS:
            out["hist_why"] = "unread:node-time-future"
            return out
        # TORN-READ TEST 2: push-front means times are non-increasing down the
        # chain. Equal is allowed -- two appends inside one millisecond are
        # reachable when the movement command changes twice in a frame -- but a
        # node NEWER than the one that links to it cannot happen. This is also
        # the ONLY defence against the recycle hazard named at HIST_BLOCK_MAX:
        # a slot re-appended under our read carries the current world clock, so
        # it is newer than the stale parent that pointed at it.
        if prev_t is not None and _s32(prev_t - t) < 0:
            out["hist_why"] = "unread:node-time-inverted"
            return out
        prev_t = t
        nodes.append({
            "addr": addr, "t": t,
            "p": [round(f32(blk, N_POINT), 2), round(f32(blk, N_POINT + 4), 2),
                  i32(blk, N_POINT + 8), i32(blk, N_POINT + 12)],
            "age_ms": _s32(now - t),
        })
        out["hist_n"] = len(nodes)
        addr = u32(blk, N_NEXT)
        if not addr:
            out["hist_why"] = HIST_OK
            return out
    # Ran out of budget with the chain still going. NOT "ok" and not "empty":
    # the oldest vertex we hold is not the oldest vertex there is, so "no node
    # within MATCH_RADIUS of q" is not a conclusion this sample supports.
    out["hist_why"] = "truncated:max-nodes"
    return out


def sample(handle, agbase, agent_ptr, aid=None, hist_gate=None, ctx=None):
    """One agent snapshot plus the world clock it must be read against.

    `ctx` is the TLS context `resolve()` already returns and both call sites
    already discard; passing it adds CANCELWALK-R7's controller gate operands
    to the row for four extra reads. A caller that does not pass it gets the
    same named-blank treatment every other optional operand gets -- never a
    silent False on the field the arc's primary hypothesis turns on.
    """
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
    def rd(a, n):
        return keytap.read_handle(handle, a, n)

    fence = (agtrack_fence(rd, agbase, aid, blk)
             if aid is not None else _fence_blank("no-agent-id-passed"))
    # GATE 1's operands, on the same "a caller who did not ask is a THIRD thing"
    # rule as the fence: no id means no twin lookup, and that is not a failure.
    g1 = (gate1_read(rd, agbase, aid, blk)
          if aid is not None else _gate1_blank("no-agent-id-passed"))
    # REALFIX-I1. Last, because it needs both of the above: the record for the
    # head pointer and vertex 0 (already fetched -- free), and gate 1's `sep`
    # for the gate and its `async_ptr` for the twin's plane word. The record
    # comes back from `agtrack_fence` as hex, which is the form that goes in the
    # file; decoding it here costs nothing and beats a second read of memory
    # that has moved on since.
    hist = history_chain(
        rd, bytes.fromhex(fence["state_record"]) if fence["state_record"] else None,
        g1["sep"], g1["async_ptr"], blk, now, gate=hist_gate)
    return {
        "now": now, "stop": i32(blk, A_STOP), "updated": updated,
        **fence,
        **g1,
        **hist,
        **early_outs(blk),
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
        # CANCELWALK-R7's operands, on the SAME "a caller who did not ask is a
        # THIRD thing" rule as the fence and gate 1 above.
        **(controller_read(rd, ctx) if ctx is not None
           else {k: None for k in CTRL_KEYS} | {"ctrl_why": "no-ctx-passed"}),
        # CANCELWALK-R5, sync side. `point_raw`/`vel_raw` deliberately duplicate
        # values this dict already carries under other names, so a reader
        # diffing the two copies compares LIKE WITH LIKE (`point` is rounded and
        # carries a plane, `live` is dead-reckoned) instead of re-deriving the
        # correspondence at read time and getting it wrong.
        # `stop` is EXCLUDED and the exclusion is the point: this dict already
        # ships `"stop"` from the same offset, and `**` would have let the
        # splice silently win -- the exact clobber section 12's uniqueness check
        # exists to catch, which is how this was found. The async side keeps its
        # own `async_stop` because nothing else carries the twin's.
        **{k: v for k, v in _r5_fields(blk).items() if k != "stop"},
    }


# A RUN THAT MEASURED NOTHING FAILED, and this selftest is a run. Set from a
# real green run on 2026-08-20 with every section executing, NOT from a guess:
# a section that stops running silently is exactly the failure this number
# catches, and it is the reason `--selftest` can be trusted as a gate at all.
# Section 5 is the one that can legitimately not run (no vault snapshot); it
# declares how many checks it would have executed and the floor drops by that,
# so a bare machine is honest rather than either red or falsely green.
# 122 -> 144 on 2026-08-20 when the review's FIX-FIRST list landed: 8 checks on
# the EPISODE LINE ITSELF and its seconds axis (section 8, 7 -> 15), 10 on
# main()'s wiring asked of the syntax tree (section 9, 12 -> 22) and 4 on
# gate1_verdict's printed share table (section 10, 27 -> 31). Read off the run,
# not predicted: 6+1+1+0+28+13+7+15+22+31+13+7.
# 144 -> 154 later the same day, closing the two holes a second review OPENED THE
# MUTATIONS FOR and watched pass at 144/144: 6 checks on `fence_verdict`'s own
# per-label share table (section 7, 7 -> 13), which was ruled on by NOTHING but a
# return code while gate1_verdict's table one function down had just been pinned;
# and 4 on gate1_read's DISTANCE METRIC (section 10, 31 -> 35), which all ten
# separation fixtures left free by being axis-aligned. Read off the run, not
# predicted: 6+1+1+0+28+13+13+15+22+35+13+7.
# 154 -> 158 later still, closing the two holes a THIRD review opened the
# mutations for and watched pass at 154/154. Both are the same defect in a
# narrower place: the fixture pinned a QUANTITY but left an OPERAND free.
# `fence_verdict`'s share table bound only 3 of `gate_reach`'s 4 values --
# `shut:noop` was in no fixture at all, so relabelling it to `test-runs` in the
# print loop inflated the share H1's refutation rule 1 is stated over, silently
# (section 7, 13 -> 14); and every sync-side agent in section 10 sat at the
# ORIGIN, where hypot(sx-ay, sy-ax), hypot(ax, ay) and hypot(sx+ax, sy+ay) all
# equal the right answer (section 10, 35 -> 38). Read off the run, not
# predicted: 6+1+1+0+28+13+14+15+22+38+13+7.
# 158 -> 202 on 2026-08-21 with REALFIX-I1. Section 5 grew 28 -> 44 with the
# sixteen node-layout displacements read out of the appender, its allocator and
# the walker; section 12 grew 7 -> 8 (sample() must actually CALL
# history_chain -- eight blank keys spliced from nowhere look identical in the
# file); section 9's wiring table grew 22 -> 25 with the three rows that keep
# REALFIX-I1's OUTPUT alive (`chain_cost` priced, `print_hist_summary` called
# with its own three tallies, `hist_why` tallied at all), because an
# output-only obligation is the class this file has already watched go missing
# green twice; and section 13 is the new 28-check walk over a synthetic chain.
# Read off the run, not predicted: 6+1+1+0+44+13+14+15+25+38+13+8+28.
# 206 -> 230 on 2026-08-21 after a verifier lane re-derived the node layout from
# the binary and a mutation lane opened 36 holes in this file and watched ten of
# them stay green. The layout SURVIVED; what did not was the prose around it and
# three fixtures that could not express the failure they named. Section 3 grew
# 1 -> 2 (movetap must take no third-party import -- `import pefile` was planted
# at the top of this file and the whole affected set stayed green, on a machine
# where pefile happens to be installed). Section 5 grew 44 -> 50 with the recycle
# OPERAND (the comment beside it named the wrong node), the two SEVER sites and
# the block span that make "a chain cannot dangle into a recycled block" a
# byte-level fact rather than an argument, and the COFF Characteristics word
# PTR_MAX's ceiling rests on. Section 9 grew 25 -> 26: main() must PRINT the
# chain cost, not merely call `chain_cost` -- a mutation kept the call, threw the
# result away and ran 206/206. Section 13 grew 28 -> 44: a short read (the
# `len(blk) <` half of its own refusal was unreachable), the sync copy's plane
# word (the fixture's plane and w were both 0, so the two dwords were
# interchangeable), a legitimate allocation above the 2 GB line (the old ceiling
# case planted its head AT the constant and refused whatever it was), the
# module-global rebinding control the landing commit wrongly credited to
# test_movesync's section 17, the recycle hazard modelled end to end, the
# future-tolerance bound pinned from both sides on its REAL ground, the read
# budget itself, and six checks that read print_hist_summary's and
# chain_cost_line's OUTPUT back out of stdout.
# 230 -> 231: the future-tolerance block's own first draft wrote every case
# as HIST_FUTURE_TOL_MS +/- 1, so all three scaled WITH the constant and
# widening 250 back to 2500 ran green -- the self-referential defect this
# round was closing, reproduced inside the fix for it. A FIXED 400 ms case
# pins the tolerance into [40, 400).
# Read off the run, not predicted: 6+1+2+0+50+13+14+15+26+38+13+8+45.
# 231 -> 240 on 2026-08-24 with CANCELWALK-R5's decode-only field set: section
# 14 is the new 9-check block (five offsets decoded from distinct non-zero
# bytes, the offsets' own placement inside the already-fetched span, the ASYNC
# copy surfacing its OWN values rather than a second decode of the sync block,
# a refused twin blanking every async key, and sample() calling the shared
# decoder). Section 12's uniqueness check earned its keep in the same commit:
# it caught `stop` colliding with the key sample() already ships from the same
# offset, which `**` would have let the splice silently win.
# Read off the run, not predicted: 6+1+2+0+50+13+14+15+26+38+13+8+45+9.
# 240 -> 250 on 2026-08-24 with CANCELWALK-R7's controller operands, which an
# adversarial review of the hardware-breakpoint version established were
# POLLABLE all along -- two dereferences from a ctx `resolve()` already holds.
# Ten checks: five gate combinations over a fake memory, the four named
# refusals (none of which may read as "no gate set", the value the arc's
# primary hypothesis predicts), and the sample() call check.
SELFTEST_FLOOR = 250


def _say_check(ok, text):
    print(f"   [{'PASS' if ok else 'FAIL'}] {text}")
    return (0 if ok else 1), 1


def selftest():
    """Everything that can be checked without a client. Exits non-zero on any gap."""
    bad = ran = skipped = 0
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
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {need:14} {why}")
    print("\n2. the TEB32 walk validates itself rather than trusting 0x2000")
    ok = "TEB32_SELF" in src and "!= (teb32 & 0xFFFFFFFF)" in src
    bad += not ok
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] agentprobe is used for {sorted(used)} and "
          f"nothing else. AgentView's +0x9C is the 0xDB type tag while AgAgent's "
          f"+0x9C is m_targetPoint.x, so resolving an agent through agentprobe's "
          f"array would pass a CHARACTER check on the wrong object")
    # AND THIS MODULE TAKES NO THIRD-PARTY IMPORT. CLAUDE.md carve-out (1)
    # scopes capstone/pefile to msghandler.py and codescan.py; movetap is
    # neither, its reader is pure ctypes, and it has to load on a bare machine.
    # NOTHING CHECKED THIS until 2026-08-21: `import pefile` was planted at the
    # top of this file and movetap --selftest, test_srclint and test_bareimport
    # were all green, because both packages happen to be installed on the
    # machine that would have caught it. The pattern is lifted from
    # test_worldmap.py's own guard. Asked of the tree for the same reason as
    # above: a grep matches the grep's own literal.
    imported = set()
    for nd in ast.walk(ast.parse(src)):
        if isinstance(nd, ast.Import):
            imported |= {al.name.split(".")[0] for al in nd.names}
        elif isinstance(nd, ast.ImportFrom) and nd.module:
            imported.add(nd.module.split(".")[0])
    banned = imported & {"capstone", "pefile", "PIL", "numpy"}
    ok = not banned
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and movetap takes NO third-party "
          f"import ({'clean' if ok else 'FOUND ' + str(sorted(banned))}) -- "
          f"carve-out (1) names two files and this is not one of them; the "
          f"reader is ctypes and must run on a bare machine")
    print("\n4. a client is present?")
    pids = agentprobe.gw_pids()
    print(f"   {'yes, pid(s) ' + str(pids) if pids else 'no Gw.exe running -- '
          'start one with session.py --keep-open to go further'}")

    for section in (_selftest_fence_bytes, _selftest_fence_refuses,
                    _selftest_fence_verdict, _selftest_episodes,
                    _selftest_flip_denominator, _selftest_gate1,
                    _selftest_early_outs, _selftest_naming,
                    _selftest_chain, _selftest_r5):
        got = section()
        bad += got[0]
        ran += got[1]
        skipped += got[2] if len(got) > 2 else 0

    floor = SELFTEST_FLOOR - skipped
    short = ran < floor
    if skipped:
        print(f"\ndeclared skip(s) worth {skipped} check(s); the floor drops "
              f"from {SELFTEST_FLOOR} to {floor} accordingly")
    if short:
        print(f"\nONLY {ran} OF A FLOOR OF {floor} CHECKS RAN -- "
              f"{floor - ran} did not execute. A section that stops running is "
              f"not a section that passed.")
    print("\nselftest " + ("FAILED" if (bad or short) else "passed")
          + f" -- {ran} checks, floor {floor}")
    return 1 if (bad or short) else 0


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


IMAGE_FILE_LARGE_ADDRESS_AWARE = 0x0020


def _pe_characteristics(buf):
    """The COFF Characteristics word. Stdlib, same 16 lines as _pe_sections.

    PTR_MAX's comment asserts this image is LARGE_ADDRESS_AWARE and therefore
    that a 0x7FFF0000 ceiling would refuse legitimate allocations. That was
    prose. This is the word itself.
    """
    pe = struct.unpack_from("<I", buf, 0x3C)[0]
    return struct.unpack_from("<H", buf, pe + 22)[0]


def _bytes_at(buf, secs, va, n):
    for sva, sz, raw in secs:
        if sva <= va < sva + sz:
            return buf[raw + (va - sva): raw + (va - sva) + n]
    return b""


def _modrm_disp(op, modrm_reg_bits, base_reg, disp):
    """`op /r [base+disp]` the way MSVC emits it: disp8 in range, else disp32.

    `disp` is SIGNED. The AgTrack fields the caller reads sit at negative
    displacements from `esi` (the record pointer is AGBASE+0x1CC while the ASYNC
    array is AGBASE+0x14C), and encoding -0x80 as an unsigned byte would build a
    pattern that matches nothing -- which is a check that cannot pass, the
    mirror of one that cannot fail.
    """
    if -0x80 <= disp < 0x80:
        return bytes([op, 0x40 | modrm_reg_bits | base_reg]) + struct.pack("<b", disp)
    return bytes([op, 0x80 | modrm_reg_bits | base_reg]) + struct.pack("<i", disp)


def _fence_byte_cases():
    """(name, VA, expected bytes BUILT FROM the constant, what it means).

    Built without the image so a machine with no vault snapshot can still say
    how many checks it is skipping. A skip that cannot state its own size turns
    the floor into a wish.
    """
    ebx, esi, edi, eax = 3, 6, 7, 0
    # The caller holds AgTrack in esi; the ASYNC array and the two clocks are
    # NEGATIVE displacements from it. Deriving them here rather than writing
    # -0x80 is the point: change OFF_ASYNC_ARRAY and the pattern changes.
    d_async_array = OFF_ASYNC_ARRAY - OFF_AGTRACK
    d_async_count = OFF_ASYNC_COUNT - OFF_AGTRACK
    d_clock0 = OFF_WORLD_CLOCK - OFF_AGTRACK
    d_clock1 = OFF_WORLD1_CLOCK - OFF_AGTRACK
    return [
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

        # --- C6/C7/C8's operands, on the same rule: encoded FROM the constant.
        ("OFF_ASYNC_COUNT", 0x0060575E,
         _modrm_disp(0x3B, eax << 3, esi, d_async_count),
         f"cmp eax,[esi{d_async_count:+#x}] -- the ASYNC array's bound, and esi "
         f"is AgTrack, so the count is AGBASE+0x{OFF_ASYNC_COUNT:X}"),
        ("OFF_ASYNC_ARRAY", 0x0060577A,
         _modrm_disp(0x8B, eax << 3, esi, d_async_array),
         f"mov eax,[esi{d_async_array:+#x}] -- the ASYNC array itself, "
         f"AGBASE+0x{OFF_ASYNC_ARRAY:X}, indexed by the SYNC agent's own id"),
        ("OFF_WORLD1_CLOCK", 0x006057A0,
         _modrm_disp(0x8B, esi << 3, esi, d_clock1),
         f"mov esi,[esi{d_clock1:+#x}] -- the clock the ASYNC copy is dated to. "
         f"AGBASE+0x{OFF_WORLD1_CLOCK:X} is world 1's, not world 0's"),
        ("OFF_WORLD_CLOCK", 0x006057A3,
         _modrm_disp(0xFF, 6 << 3, eax, d_clock0),
         f"push [eax{d_clock0:+#x}] -- and the SYNC copy gets world 0's, "
         f"AGBASE+0x{OFF_WORLD_CLOCK:X}. Two different clocks, by construction"),
        ("A_STOP (early-out A)", 0x00605634,
         _modrm_disp(0x83, 7 << 3, ebx, A_STOP) + b"\x00",
         "cmp dword[ebx+stop],0 -- early-out A's first conjunct"),
        ("A_MODE (early-out A)", 0x0060563A,
         _modrm_disp(0x83, 7 << 3, ebx, A_MODE) + bytes([EARLY_OUT_A_MODE]),
         f"cmp dword[ebx+mode],{EARLY_OUT_A_MODE} -- the second conjunct, and "
         f"the literal 9 is encoded here too, so a wrong mode value goes red"),
        ("A_POINT (early-out B)", 0x00605643,
         _modrm_disp(0x8B, eax << 3, ebx, A_POINT),
         "mov eax,[ebx+point.x] -- early-out B's first operand"),
        ("A_POINT+4 (early-out B)", 0x00605649,
         _modrm_disp(0x8B, eax << 3, ebx, A_POINT + 4),
         "mov eax,[ebx+point.y] -- and its second. BOTH must be +inf"),
        ("VA_INVALID_POS", 0x0060564F,
         b"\xd9\x05" + struct.pack("<I", VA_INVALID_POS),
         "fld dword[0x948654] -- the +inf both halves are compared against"),
        ("VA_GATE1_CUT", 0x006057BF,
         b"\xd9\x05" + struct.pack("<I", VA_GATE1_CUT),
         "fld dword[0x946564] -- gate 1's cut, loaded twice around the call"),
        ("A_STOP (the clamp)", 0x005FF829,
         _modrm_disp(0x8B, 1 << 3, 2, A_STOP),
         "mov ecx,[edx+stop] in 0x005FF820 -- the clamp `position_at` copies"),
        ("A_SEGMENT (the clamp)", 0x005FF839,
         _modrm_disp(0x8B, 1 << 3, 2, A_SEGMENT),
         "mov ecx,[edx+segment.x] -- what the clamp returns INSTEAD of "
         "integrating, which is the half a reimplementation drops"),
        ("A_UPDATED (the integrator)", 0x005FFBB3,
         _modrm_disp(0x2B, ebx << 3, esi, A_UPDATED),
         "sub ebx,[esi+updated] in 0x005FFB40 -- the dt the other branch uses"),
        ("A_VEL (the integrator)", 0x005FFBAD,
         _modrm_disp(0xD9, eax << 3, esi, A_VEL),
         "fld dword[esi+vel.x] -- the velocity it integrates with"),

        # --- REALFIX-I1's node layout, encoded FROM the constants ------------
        # The committed comment at S_HIST_HEAD used to assert that only +0x00
        # and +0x04 of the RECORD were ever touched. These cases are why that
        # sentence is gone: the appender writes the record's own point and the
        # walker reads it back as the polyline's first vertex, and both are
        # here as bytes rather than as a claim.
        ("HIST_NODE_STRIDE", 0x00604DBD,
         b"\x6b\xc1" + bytes([HIST_NODE_STRIDE]),
         f"imul eax,ecx,0x{HIST_NODE_STRIDE:X} -- the allocator's own stride, "
         f"so a node is {HIST_NODE_STRIDE} bytes and not the 0x1C of a record"),
        ("N_TIME", 0x00604DCC,
         (b"\x89\x08" if N_TIME == 0
          else b"\x89\x48" + bytes([N_TIME])),
         "mov [eax],ecx in the allocator -- the node's time comes from the "
         "argument the appender passed, and mod=00 IS the proof it is at +0x00"),
        ("N_NEXT (allocator nulls it)", 0x00604DCE,
         b"\xc7\x40" + bytes([N_NEXT]) + b"\x00\x00\x00\x00",
         "mov dword[eax+next],0 -- so the FIRST node of a chain keeps next=0 "
         "and THE TERMINATOR IS NULL"),
        ("N_NEXT (push-front)", 0x00605A5D,
         _modrm_disp(0x89, 1 << 3, 2, N_NEXT),
         "mov [edx+next],ecx where ecx was [record+head] -- the new node points "
         "at the OLD head, so +0x04 walks from newest to oldest"),
        ("N_POINT.x", 0x00605A63, _modrm_disp(0x89, 1 << 3, 2, N_POINT),
         "mov [edx+point.x],ecx -- the first of the four dwords"),
        ("N_POINT.plane", 0x00605A6F,
         _modrm_disp(0x89, 1 << 3, 2, N_POINT + 8),
         "mov [edx+point.plane],ecx -- the PLANE WORD, which is the whole of "
         "why REALFIX-I1 exists"),
        ("N_POINT.w", 0x00605A75, _modrm_disp(0x89, eax << 3, 2, N_POINT + 12),
         "mov [edx+point.w],eax -- the fourth dword, so the point is 0x10 wide"),
        ("HIST_BLOCK_MAX", 0x00604BD0,
         b"\x81\x3f" + struct.pack("<I", HIST_BLOCK_MAX),
         f"cmp dword[edi],0x{HIST_BLOCK_MAX:X} -- a block holds at most "
         f"{HIST_BLOCK_MAX} nodes"),
        ("HIST_BLOCK_RECYCLE_MS", 0x00604C03,
         b"\x81\xf9" + struct.pack("<I", HIST_BLOCK_RECYCLE_MS),
         f"cmp ecx,{HIST_BLOCK_RECYCLE_MS} -- the ~5 s bound is per BLOCK, "
         f"never per node"),
        # THE OPERAND OF THAT COMPARE, which nothing pinned while the comment
        # beside it named the wrong node for a day. `eax` is already
        # count*HIST_NODE_STRIDE (0x00604BFC), so the displacement selects
        # node index count-1 -- the NEWEST. Encoded FROM the stride: a belief
        # that the client tests the OLDEST node would have to write +4 here.
        ("HIST_RECYCLE_OPERAND", 0x00604BFF,
         b"\x2b\x4c\x38" + struct.pack("<b", 4 - HIST_NODE_STRIDE),
         f"sub ecx,[eax+edi{4 - HIST_NODE_STRIDE:+#x}] with eax = "
         f"count*0x{HIST_NODE_STRIDE:X}: block+4+(count-1)*0x{HIST_NODE_STRIDE:X}"
         f" is the LAST APPENDED node, so the 5 s test is on the block's NEWEST"),
        # THE SEVER. This is the real reason a chain cannot dangle into a
        # recycled block, and it was missing from this file entirely -- the
        # comment argued safety from a 5 s bound instead.
        ("HIST_SEVER_NODE", 0x00604C56,
         b"\xc7\x40" + bytes([N_NEXT]) + b"\x00\x00\x00\x00",
         "mov dword[eax+next],0 -- before reusing a block the client zeroes "
         "every node NEXT pointing into it, so a stale walk sees NULL"),
        ("HIST_BLOCK_SPAN", 0x00604C49,
         b"\x8d\x8e" + struct.pack("<I",
                                   HIST_NODE_STRIDE * HIST_BLOCK_MAX + 4),
         f"lea ecx,[esi+0x{HIST_NODE_STRIDE * HIST_BLOCK_MAX + 4:X}] -- the "
         f"sever's upper bound, and 0x{HIST_NODE_STRIDE:X}*"
         f"0x{HIST_BLOCK_MAX:X}+4 is the block span both constants imply"),
        ("HIST_SEVER_RECORD", 0x00604CBB,
         b"\xc7\x42" + bytes([S_HIST_HEAD]) + b"\x00\x00\x00\x00",
         "mov dword[edx+head],0 -- and the same pass zeroes the RECORD's head "
         "across the array, so the record we read cannot dangle either"),
        ("HIST_SEVER_STRIDE", 0x00604CC2,
         b"\x83\xc2" + bytes([STATE_STRIDE]),
         f"add edx,0x{STATE_STRIDE:X} -- the sever walks the record array at "
         f"the SAME stride this file reads it at, which is what makes the "
         f"array it protects the array we parse"),
        ("HIST_NODE_AGE_MS", 0x0060593A,
         b"\x3d" + struct.pack("<I", HIST_NODE_AGE_MS),
         f"cmp eax,{HIST_NODE_AGE_MS} -- the head-age rule that forces a new "
         f"node, and the 2.5 s REALFIX.md 4.4 prices the sagitta at"),
        ("S_HIST_HEAD (the walker's entry)", 0x006056AF,
         _modrm_disp(0x8B, esi << 3, esi, S_HIST_HEAD),
         "mov esi,[esi+head] -- the consumer side of the same offset"),
        ("N_NEXT (the walker's advance)", 0x00605732,
         _modrm_disp(0x8B, esi << 3, esi, N_NEXT),
         "mov esi,[esi+next] at the bottom of the loop, then `test esi,esi / "
         "jne` -- null terminates, confirmed from BOTH ends of the chain"),
        ("N_POINT (the walker's read)", 0x0060571A,
         _modrm_disp(0x8B, eax << 3, esi, N_POINT),
         "mov eax,[esi+point.x] with esi a NODE -- the four dwords read back"),
        ("S_HIST_POINT (on the RECORD)", 0x0060569A,
         _modrm_disp(0x8B, eax << 3, esi, S_HIST_POINT),
         "mov eax,[esi+point.x] with esi the RECORD, BEFORE 0x006056AF steps "
         "to the head -- the record's point is the polyline's vertex 0, which "
         "the old comment said nothing touched"),
        ("S_HIST_POINT (written)", 0x00605A0E,
         _modrm_disp(0x89, ebx << 3, esi, S_HIST_POINT),
         "mov [esi+point.x],ebx -- the appender caching the newest vertex on "
         "the record itself"),
        ("S_HIST_AT", 0x00605A25, _modrm_disp(0x89, eax << 3, esi, S_HIST_AT),
         "mov [esi+at],eax -- record+0x18, which the old comment called "
         "UNVERIFIED: the epoch the cached vertex is dated to"),
    ]


def _selftest_fence_bytes():
    print("\n5. the AgTrack fence offsets, re-derived from the pinned binary")
    cases = _fence_byte_cases()
    # +5: the STATE_STRIDE arithmetic, the two float constants read back out of
    # the image, the INVALID_POS bit-pattern check, and the COFF Characteristics
    # word PTR_MAX's ceiling rests on.
    declared = len(cases) + 5
    try:
        path, why = pinned.find()
    except SystemExit as e:
        print(f"   [SKIP] {e}")
        print(f"   this section proves nothing on a machine with no vault "
              f"snapshot; it is NOT counted as a pass, and it declares the "
              f"{declared} checks it did not run")
        return 0, 0, declared
    buf = open(path, "rb").read()
    imgbase, secs = _pe_sections(buf)
    if imgbase != IMAGE_BASE_PE32:
        print(f"   [FAIL] image base 0x{imgbase:08X}, and every VA below is "
              f"absolute for 0x{IMAGE_BASE_PE32:08X}")
        return 1, 1, 0
    print(f"   against {os.path.basename(os.path.dirname(path))}/Gw.exe -- {why}")

    n = ran = 0
    for name, va, want, meaning in cases:
        got = _bytes_at(buf, secs, va, len(want))
        ok = got == want
        n += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {name:24} 0x{va:08X} "
              f"{want.hex():<18} {'' if ok else 'GOT ' + got.hex() + '  '}"
              f"{meaning}")

    # The stride is a product, not a displacement, so it gets its own arithmetic
    # check against the two instructions that build it.
    lea8 = _bytes_at(buf, secs, 0x00605FF9, 7) == b"\x8d\x0c\xdd\x00\x00\x00\x00"
    sub1 = _bytes_at(buf, secs, 0x00606000, 2) == b"\x2b\xcb"
    ok = lea8 and sub1 and STATE_STRIDE == (8 - 1) * 4
    n += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] STATE_STRIDE   0x00605FF9 "
          f"lea ecx,[ebx*8] then sub ecx,ebx, scaled by 4 in the SIB: "
          f"(8-1)*4 = {(8 - 1) * 4}, constant says {STATE_STRIDE}")

    # THE TWO FLOATS, READ BACK OUT OF THE IMAGE. The cases above prove the
    # client loads the dword at these addresses; only this proves our copy of
    # what is IN them. A wrong GATE1_CUT would classify every sample and never
    # error -- the most expensive kind of wrong number in this file.
    for name, va, want, meaning in (
            ("GATE1_CUT", VA_GATE1_CUT, GATE1_CUT,
             "gate 1's own compare constant, not a number we chose"),
            ("INVALID_POS", VA_INVALID_POS, math.inf,
             "AGENT_INVALID_POSITION, early-out B's sentinel")):
        raw = _bytes_at(buf, secs, va, 4)
        got = f32(raw) if len(raw) == 4 else None
        ok = got == want
        n += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {name:24} 0x{va:08X} "
              f"= {got!r}, constant says {want!r}   {meaning}")
    # PTR_MAX's CEILING, READ OUT OF THE COFF HEADER rather than asserted in a
    # comment. If the flag is set the process address space runs to 0xFFFEFFFF
    # under WOW64, so a 0x7FFF0000 bound would refuse real nodes silently.
    ch = _pe_characteristics(buf)
    laa = bool(ch & IMAGE_FILE_LARGE_ADDRESS_AWARE)
    ok = laa and PTR_MAX > 0x7FFF0000
    n += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] {'PTR_MAX / LARGE_ADDR':24} "
          f"COFF Characteristics 0x{ch:04X}, "
          f"IMAGE_FILE_LARGE_ADDRESS_AWARE {'SET' if laa else 'CLEAR'}, so the "
          f"ceiling must sit above 0x7FFF0000 and PTR_MAX is 0x{PTR_MAX:08X} "
          f"-- the 2 GB bound would refuse legitimate high allocations")

    ok = struct.unpack("<f", struct.pack("<I", INVALID_POS))[0] == math.inf
    n += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] {'INVALID_POS bits':24} "
          f"0x{INVALID_POS:08X} is the f32 +inf the image holds -- the constant "
          f"is compared as a BIT PATTERN by early_outs(), so it must be that "
          f"exact encoding and not merely infinite")
    return n, ran, 0


# --------------------------------------------------------------------------
# 6. THE REFUSALS. 0 MEANS "THE FENCE IS SHUT", so every way of failing to read
# it must land somewhere a consumer cannot confuse with that.
#
# Driven off a FAKE memory rather than a client, so it runs on a bare machine
# and so each failure can actually be provoked -- a null array pointer and an
# out-of-bounds id do not occur on demand in a live process, which is precisely
# why they would otherwise never be tested.
# --------------------------------------------------------------------------
def _fake_agent(agent_id, world=0, point=(0.0, 0.0), plane=0, vel=(0.0, 0.0),
                updated=0, stop=0, segment=(0.0, 0.0), seg_plane=0, mode=0,
                point_bits=None, reqtoken=0, direction=(0.0, 0.0)):
    """An AgAgent block. Every default is the zero the old two-argument form
    produced, so section 6's fixtures are byte-for-byte what they were --
    including R5's `reqtoken`/`direction`, whose defaults write the zeros those
    offsets already held."""
    b = bytearray(AGENT_SPAN)
    struct.pack_into("<I", b, A_ID, agent_id)
    struct.pack_into("<i", b, A_WORLD, world)
    struct.pack_into("<ff", b, A_POINT, *point)
    if point_bits is not None:      # for the +inf sentinel, set as raw bits
        struct.pack_into("<II", b, A_POINT, *point_bits)
    struct.pack_into("<i", b, A_POINT + 8, plane)
    struct.pack_into("<ff", b, A_VEL, *vel)
    struct.pack_into("<i", b, A_UPDATED, updated)
    struct.pack_into("<i", b, A_STOP, stop)
    struct.pack_into("<ff", b, A_SEGMENT, *segment)
    struct.pack_into("<i", b, A_SEGMENT + 8, seg_plane)
    struct.pack_into("<i", b, A_MODE, mode)
    struct.pack_into("<I", b, A_REQ_TOKEN, reqtoken)
    struct.pack_into("<ff", b, A_DIR, *direction)
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
         mem(ARRAY, 64, shut_rec), _fake_agent(7), "shut", "shut:append", 0),
        ("world 1 skips the test even with the fence open",
         mem(ARRAY, 64, open_rec), _fake_agent(7, world=1), "open",
         "world1:append", 1),
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
    n = ran = 0
    for what, read, blk, want_state, want_reach, want_raw in cases:
        r = agtrack_fence(read, AG, 7, blk)
        ok = (r["fence_state"] == want_state and r["gate_reach"] == want_reach
              and r["fence_raw"] == want_raw
              and set(r) == set(FENCE_KEYS))
        n += not ok
        ran += 1
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
             and f["gate_reach"] not in ("shut:append", "shut:noop")
             for f in fails)
    n += not ok
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a healthy read populates every "
          f"field: raw={good['fence_raw']!r} head={good['hist_head']!r} "
          f"count={good['agtrack_count']!r} armed={good['agtrack_armed']!r} "
          f"record={(good['state_record'] or '')[:16]}... "
          f"-- a stub that only ever refused would fail here")
    return n, ran


def _selftest_fence_verdict():
    """7. the summary REFUSES a bad denominator and an aliased fence."""
    print("\n7. the run-level fence verdict can go red")
    import contextlib
    import io
    cases = [
        ("a clean run passes", {"shut:append": 800, "test-runs": 200}, 4, 0),
        ("nothing read at all", {}, 0, 1),
        ("a quarter of samples unread refuses the shares",
         {"shut:append": 700, "unread:record-unreadable": 300}, 4, 1),
        ("a fence flipping near the sample rate refuses",
         {"shut:append": 500, "test-runs": 500}, 260, 1),
        # THE REGRESSION CASE, and it is why the bar changed on 2026-08-20.
        # A 15 ms open window against a 185 ms shut one at ~10 Hz is about ten
        # TRUE transitions per second -- nothing a 12 Hz reader can resolve --
        # and it lands at a 7.5% open share with phi = 0.138. The old
        # `flips * 4 >= n` bar needed 0.25 and therefore PASSED it, printing
        # "not aliased" over a number that was pure sampling phase. Simulated
        # A = 0.998. If this case ever returns 0 again the instrument is lying
        # in exactly the band H1 lives in.
        ("a SKEWED fast fence refuses too -- the old bar could not see this",
         {"shut:append": 925, "test-runs": 75}, 138, 1),
        ("a slow fence at the same skewed share still passes",
         {"shut:append": 925, "test-runs": 75}, 7, 0),
        ("just under both bars still passes",
         {"shut:append": 700, "test-runs": 60, "unread:record-unreadable": 240},
         6, 0),
    ]
    bad = ran = 0
    for what, reach, flips, want in cases:
        n = sum(reach.values())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            # `pairs = n - 1` is what this bar was calibrated against, so the
            # cases above keep it. Section 9 is where the pair count is varied
            # independently of `n`, which is the thing C3 changed.
            got = fence_verdict(reach, flips, max(0, n - 1), n or 1, 12.0)
        ok = got == want
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}: returned {got}, "
              f"wanted {want}")

    # ----------------------------------------------------------------------
    # THE PER-LABEL SHARE TABLE, CELL BY CELL.
    #
    # Every check above rules on the RETURN CODE and on nothing else, so the
    # four-row block an operator actually reads -- the one
    # studies/movement/PROBE-GATEFIRE.md section 6 quotes VERBATIM -- was
    # asserted by nothing at all. A review ran three mutations of it and watched
    # `--selftest` stay green at 144/144 on every one: hard-wiring every row to
    # `0      0.0%`; printing only the top row so the other labels vanish
    # outright; and -- the one that matters -- SWAPPING the `test-runs` and
    # `shut:append` labels. Demonstrated on a 521-shut / 40-test-runs capture,
    # that last mutation prints `test-runs 521 92.9%` for a run in which
    # test-runs was 7.1%, which REFUTES H1 (refutation rule 1: test-runs >= 50%
    # of real samples) off data that CONFIRMS it.
    #
    # gate1_verdict's share table one function down was pinned this way in the
    # previous round; this one, the more consequential of the two, was left
    # free. Same remedy, and the shape of it is the point: hand-computed
    # fixtures, whole lines matched against `out.splitlines()`, label AND count
    # AND percentage together. A check that sums counts, or counts rows, or
    # totals percentages CANNOT SEE A SWAP -- every one of those is invariant
    # under it -- so the binding has to be label-to-cell.
    import re
    ROW = re.compile(r"^  (\S+) +(\d+) +(\d+\.\d)%$")

    # ALL FOUR `gate_reach` VALUES, NOT THREE. This fixture read
    # 640/210/100/50 over shut:append / test-runs / world1:append / unread and
    # stopped there, so `shut:noop` -- the fourth branch of agtrack_fence's tail
    # (fence shut, world != 0, at 0x0060610B) -- appeared in NO fixture in this
    # section and was bound to no cell. A review inserted
    # `k = "test-runs" if k == "shut:noop" else k` into the print loop above and
    # watched --selftest stay green at 154/154. That mutation folds a FENCED
    # label into the OPEN one, INFLATING the printed test-runs share, which is
    # the exact quantity H1's refutation rule 1 turns on ("test-runs >= 50% of
    # real samples"). Three of four cells pinned is the same hole as none.
    #
    # 600/210/100/60/30 over n = 1,000: five distinct labels, five distinct and
    # strictly decreasing counts so "count order" is a real constraint, 30
    # unread (3%, under the 25% bar) and flips/pairs = 100/999 against
    # p_open = 210/970 = 21.65% (A = 0.30, under the 0.5 bar), so the lane
    # returns 0 and the whole block prints.
    fx = {"shut:append": 600, "test-runs": 210, "world1:append": 100,
          "shut:noop": 60, "unread:record-unreadable": 30}

    # A CONTROL THAT JUDGES ZERO ROWS IS A DEFECT, and so is one that judges
    # three rows of a four-valued domain. Bind the fixture to the PRODUCER's own
    # enumeration rather than to a hand-written list: section 12 proves
    # agtrack_fence emits exactly REACH_TEST_RUNS + REACH_FENCED, so a fifth
    # branch added there turns THIS red instead of arriving unpinned the way
    # shut:noop did.
    domain = {REACH_TEST_RUNS} | set(REACH_FENCED)
    missing = sorted(domain - set(fx))
    ok = len(domain) == 4 and not missing
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture below carries every one "
          f"of the {len(domain)} gate_reach values agtrack_fence can emit "
          f"{sorted(domain)}; missing: {missing or 'none'}. `shut:noop` was in "
          f"no fixture in this section at all, so relabelling it to "
          f"`{REACH_TEST_RUNS}` in the print loop was green in all "
          f"{ran - 1} checks above")

    rc, out = _capture(fence_verdict, fx, 100, 999, 1000, 12.0)
    lines = out.splitlines()
    rows = [m for m in (ROW.match(L) for L in lines) if m]
    ok = len(fx) == 5 and len(rows) == 5 and rc == 0
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture carries {len(fx)} "
          f"labels and the table printed {len(rows)} row(s) (rc {rc}) -- "
          f"asserted BEFORE anything is judged with it, because a control that "
          f"judges zero rows is a defect, and \"print only the top row\" was "
          f"green in all {ran - 1} checks above")

    want = ["  shut:append                           600   60.0%",
            "  test-runs                             210   21.0%",
            "  world1:append                         100   10.0%",
            "  shut:noop                              60    6.0%",
            "  unread:record-unreadable               30    3.0%"]
    at = [lines.index(w) for w in want if w in lines]
    ok = len(at) == 5 and at == list(range(at[0], at[0] + 5))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] all five cells print VERBATIM and "
          f"CONSECUTIVELY in count order -- 600/60.0%, 210/21.0%, 100/10.0%, "
          f"60/6.0%, 30/3.0% over n = 1,000, hand-computed. Hard-wiring the "
          f"whole table to `0      0.0%` passed every return-code case above"
          + ("" if ok else f"  MATCHED {at} OF {want!r} IN {lines!r}"))

    got = {m.group(1): (int(m.group(2)), m.group(3)) for m in rows}
    ok = got == {"shut:append": (600, "60.0"), "test-runs": (210, "21.0"),
                 "world1:append": (100, "10.0"), "shut:noop": (60, "6.0"),
                 "unread:record-unreadable": (30, "3.0")}
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and every COUNT and PERCENTAGE "
          f"is bound to its OWN label: {got}. THIS is the check that sees a "
          f"LABEL SWAP or a RELABEL -- swapping `test-runs` with `shut:append`, "
          f"or folding `shut:noop` into `test-runs`, leaves the count total, "
          f"the percentage total and all seven return codes untouched, and a "
          f"relabel leaves the ROW COUNT untouched too")

    # THE REVIEWER'S OWN CAPTURE, and the reason a swap is fatal rather than
    # cosmetic. 521 shut : 40 test-runs, n = 561, nothing unread -- so every
    # sample is real and `test-runs / real samples` IS the quantity H1's
    # refutation rule 1 is stated over. 40/561 = 7.130% -> 7.1%;
    # 521/561 = 92.870% -> 92.9%. Both hand-computed.
    rc2, out2 = _capture(fence_verdict, {"shut:append": 521, "test-runs": 40},
                         6, 560, 561, 12.0)
    lines2 = out2.splitlines()
    ok = (rc2 == 0
          and "  shut:append                           521   92.9%" in lines2
          and "  test-runs                              40    7.1%" in lines2)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] on the 521/40 capture the table "
          f"reads `shut:append 521 92.9%` and `test-runs 40 7.1%` (rc {rc2}), "
          f"hand-computed from 40/561 and 521/561 -- not a substring match, the "
          f"whole line including the column positions section 6 quotes")

    rows2 = [m for m in (ROW.match(L) for L in lines2) if m]
    hits = [m for m in rows2 if m.group(1) == REACH_TEST_RUNS]
    ok = (len(rows2) == 2 and len(hits) == 1
          and float(hits[0].group(3)) < 50.0)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and the "
          f"{len(hits)} `{REACH_TEST_RUNS}` row(s) of that capture's "
          f"{len(rows2)} print "
          f"{', '.join(m.group(3) + '%' for m in hits) or 'NOTHING AT ALL'} "
          f"against H1's 50% bar. Refutation rule 1 is `test-runs >= 50% of "
          f"real samples` and this capture has no unread samples, so the "
          f"swapped table prints 92.9% and REFUTES H1 off data that CONFIRMS "
          f"it -- one printed label deciding whether this project spends an "
          f"evening writing a hook DLL")

    # A REFUSED RUN STILL PRINTS ITS TABLE, because the shares and the refusal
    # are two different statements and a failed control must not void what it
    # was not measuring. 600/100/300 over n = 1,000: 30% unread -> rc 1, and all
    # three cells still print above the refusal so the operator can see WHICH
    # label carried the unread third.
    rc3, out3 = _capture(fence_verdict,
                         {"shut:append": 600, "test-runs": 100,
                          "unread:record-unreadable": 300}, 20, 999, 1000, 12.0)
    lines3 = out3.splitlines()
    ok = (rc3 == 1
          and "  shut:append                           600   60.0%" in lines3
          and "  unread:record-unreadable              300   30.0%" in lines3
          and "  test-runs                             100   10.0%" in lines3
          and any(L.startswith("  REFUSED:") for L in lines3))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a run REFUSED for 30% unread (rc "
          f"{rc3}) still prints all three cells VERBATIM above the refusal -- "
          f"60.0%/30.0%/10.0% hand-computed over n = 1,000 -- so a table that "
          f"only prints on a clean run cannot pass either")
    return bad, ran


def _capture(fn, *args, **kw):
    """Run a printer, return (its return value, everything it printed)."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rv = fn(*args, **kw)
    return rv, buf.getvalue()


def _seq(states, t0=0.0, dt=0.1):
    return [(t0 + i * dt, s) for i, s in enumerate(states)]


def _selftest_episodes():
    """8. run lengths, censoring, and the refusal of a median that is a lie."""
    print("\n8. EPISODES -- the effective n is runs, not samples (C2)")
    bad = ran = 0

    # A -> A -> B -> B -> B -> A. Three runs; the first and last touch the
    # capture boundary and are therefore CENSORED -- they have no measured start
    # or no measured end, and their lengths are lower bounds.
    runs = episodes(_seq(["a", "a", "b", "b", "b", "a"]))
    ok = ([(r["state"], r["length"], r["censored"]) for r in runs]
          == [("a", 2, True), ("b", 3, False), ("a", 1, True)])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] three runs, and the two touching "
          f"the capture boundary are marked censored: "
          f"{[(r['state'], r['length'], r['censored']) for r in runs]}")

    # A flaky read cuts one true episode in two. That is the episode count's
    # version of the flip denominator's defect, so it is MARKED rather than
    # silently inflating the count.
    runs = episodes(_seq(["shut:append", "unread:x", "shut:append"]))
    ok = (len(runs) == 3 and runs[0]["split"] and runs[2]["split"]
          and not runs[1]["split"])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a run bounded by an `unread:` "
          f"sample is marked SPLIT, so the episode count is reported as an "
          f"upper bound: {[r['split'] for r in runs]}")

    # THE MEDIAN REFUSAL. Two runs, both censored: a median over them is a
    # statement about the block length. This is the H1 shape at a 40 s block --
    # the criterion this probe was originally written with was satisfied by
    # construction, which is why it was replaced by the episode count.
    # 300 shut, 100 open, 164 shut: the shut state has two runs and BOTH touch
    # the capture boundary, while the open one has a single measured run in the
    # middle. One output, two opposite verdicts.
    _, out = _capture(print_episodes,
                      _seq(["shut:append"] * 300 + ["test-runs"] * 100
                           + ["shut:append"] * 164), 10.4)
    ok = "median REFUSED" in out and "2 of 2 runs censored" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a majority-censored state REFUSES "
          f"its median instead of quoting a block length as a dwell")

    # And the mirror: a state with an uncensored majority DOES get one, or the
    # refusal above is a printer that always refuses.
    ok = "median 100 samples" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and the median is not refused "
          f"unconditionally -- the state with a measured run in the middle of "
          f"the same capture still gets one, checked on the same output so a "
          f"stub that always refused could not pass both")

    _, out = _capture(print_episodes,
                      _seq(["a", "b"] * 4 + ["a"] * 30 + ["b"] * 30), 10.4)
    ok = ("effective n = " in out and "episode(s)" in out
          and "QUOTE THE EPISODES" in out)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the effective n is printed as "
          f"EPISODES: a 92% share over 564 samples with 3 transitions has an "
          f"effective n of about 4, and this file used to print the 564")

    ok = "UNRESOLVED" in out and "Nyquist bar" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a state showing a 1-2 sample run is "
          f"called UNRESOLVED, with the Nyquist bar printed beside it -- a "
          f"one-sample run is a dwell this reader cannot see the bottom of")

    _, out = _capture(print_episodes, [], 10.4)
    ok = "measured nothing" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] an empty sequence says it measured "
          f"nothing rather than printing zero runs as a result")

    # ----------------------------------------------------------------------
    # THE PRINTED LINE ITSELF, CELL BY CELL. Everything above this point asked
    # `episodes()` for a return structure and the printer for eight SUBSTRINGS,
    # and a review found ELEVEN mutations that make the line LIE while leaving
    # the whole selftest green at 122/122: the per-state run count hard-wired to
    # 1, the minimum run to 99, the censored count to 0, the SPLIT/"UPPER bound"
    # clause never printed, the state NAME replaced with "x", `effective n` set
    # to `len(real) * 100`, `real` widened to include the unread runs, `secs()`
    # made arbitrary, the Nyquist CHARACTERISE threshold moved from 5 samples to
    # 50, and the call itself deleted from `fence_verdict` or handed [].
    #
    # That is C2's own defect one level up -- C2 exists because this file
    # printed 564 where the answer was 4 -- so the line that travels into the
    # write-up is now asserted VERBATIM against two hand-computed fixtures.
    # Literal expected strings, never strings this file builds from the same
    # expressions the printer uses, which would be a check that cannot fail.
    # ----------------------------------------------------------------------
    # FIXTURE A: 300 shut / 100 open / 164 shut at 10 Hz. 564 polls, span
    # 563 * 0.1 = 56.30 s, poll rate 563 / 56.30 = 10.00 Hz. `shut:append` has
    # two runs (300 and 164), BOTH touching a capture boundary -> median
    # refused, min 164, measured span (164 - 1) / 10 = 16.30 s. `test-runs` has
    # one run of 100 in the middle -> median 100, span (100 - 1) / 10 = 9.90 s,
    # 0 censored. Three real episodes over 564 real samples: the 3-and-564 pair
    # C2's rationale is written around.
    _, out = _capture(print_episodes,
                      _seq(["shut:append"] * 300 + ["test-runs"] * 100
                           + ["shut:append"] * 164), 10.4)
    want_a = [
        "    shut:append                2 run(s), median REFUSED (2 of 2 runs "
        "censored by the capture boundary), min 164 (16.30 s, a LOWER BOUND -- "
        "censored), 2 censored",
        "    test-runs                  1 run(s), median 100 samples (9.90 s), "
        "min 100 (9.90 s), 0 censored",
        "    effective n = 3 episode(s) of real state over 564 real sample(s). "
        "QUOTE THE EPISODES.",
    ]
    lines = out.splitlines()
    missing = [w for w in want_a if w not in lines]
    ok = not missing
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the per-state line is asserted CELL "
          f"BY CELL, not by substring: 2 runs / median REFUSED / min 164 / "
          f"16.30 s / 2 censored, against 1 run / median 100 / 9.90 s / 0 "
          f"censored, and `effective n = 3 ... over 564` -- the exact 3-and-564"
          + ("" if ok else f"  MISSING {missing!r} FROM {lines!r}"))

    # FIXTURE B: 10 shut / 2 unread / 10 shut / 5 open. Every cell that fixture
    # A leaves at a constant moves here: run count 2 vs 1 vs 1, censored 1 vs 1
    # vs 0, a median that is NOT refused beside one that is, the split clause
    # with its own count, an unread state that must appear in the table AND be
    # excluded from `effective n`, and a min whose runs are not all censored so
    # the "LOWER BOUND" clause must NOT print. 27 polls, span 2.60 s, 10.00 Hz.
    _, out = _capture(print_episodes,
                      _seq(["shut:append"] * 10 + ["unread:x"] * 2
                           + ["shut:append"] * 10 + ["test-runs"] * 5), 8.0)
    want_b = [
        "    shut:append                2 run(s), median 10 samples (0.90 s), "
        "min 10 (0.90 s), 1 censored, 2 split by an unread sample -- the run "
        "count is an UPPER bound",
        "    test-runs                  1 run(s), median REFUSED (1 of 1 runs "
        "censored by the capture boundary), min 5 (0.40 s, a LOWER BOUND -- "
        "censored), 1 censored",
        "    unread:x                   1 run(s), median 2 samples (0.10 s), "
        "min 2 (0.10 s), 0 censored",
        "    effective n = 3 episode(s) of real state over 25 real sample(s). "
        "QUOTE THE EPISODES.",
    ]
    lines = out.splitlines()
    missing = [w for w in want_b if w not in lines]
    ok = not missing
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...on a fixture where every one of "
          f"those cells takes a DIFFERENT value: 2/1/1 runs, 1/1/0 censored, a "
          f"median refused beside one that is not, `2 split ... UPPER bound`, "
          f"and `effective n = 3 ... over 25` with the 2-sample unread run "
          f"tabled but NOT counted -- widening `real` prints 4 over 27"
          + ("" if ok else f"  MISSING {missing!r} FROM {lines!r}"))

    # THE NYQUIST BAR'S OWN NUMBERS. `2.0 / hz` and `5.0 / hz` are the two
    # thresholds the whole "is this resolvable" question is scored against, and
    # moving the 5 to 50 -- i.e. claiming this reader can characterise a dwell
    # it cannot -- left every substring check above green.
    ok = ("    Nyquist bar: two samples per half-cycle at 10.00 Hz means this "
          "reader can only DETECT alternation whose every dwell exceeds 0.20 s, "
          "and can only CHARACTERISE one above 0.50 s." in lines)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the Nyquist bar prints its two "
          f"thresholds as NUMBERS -- 2 poll intervals to DETECT (0.20 s) and 5 "
          f"to CHARACTERISE (0.50 s) at the measured 10.00 Hz -- so moving "
          f"either bar is red rather than invisible")

    # ----------------------------------------------------------------------
    # THE SECONDS AXIS, which was wrong twice and both errors OVER-stated dwell.
    # ----------------------------------------------------------------------
    # (1) k samples SPAN k - 1 intervals. `a` runs 1 then 3; `b` runs 3.
    _, out = _capture(print_episodes, _seq(["a", "b", "b", "b", "a", "a", "a"]))
    lines = out.splitlines()
    ok = (any("min 1 (0.00 s" in L for L in lines)
          and any("median 3 samples (0.20 s), min 3 (0.20 s)" in L
                  for L in lines))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a k-sample run spans k-1 poll "
          f"intervals: a 1-sample run reads 0.00 s and a 3-sample run 0.20 s at "
          f"10 Hz. `k / hz` printed 0.10 s and 0.30 s -- it charged every run "
          f"one interval it never measured, in the direction that makes an "
          f"aliased fence look resolvable")

    # (2) THE AXIS IS THE POLL RATE, NOT THE SAMPLE RATE. Same sequence, two
    # `rate` arguments five-fold apart: every dwell must be identical, because
    # `rate` counts SAMPLES per second while a run length counts POLLS -- and
    # since C5 the sequence carries drop markers that are in neither `n` nor
    # `reach`. Asserted with the value present as well as equal, so two empty
    # outputs could not pass it.
    body = _seq(["shut:append"] * 100 + ["test-runs"] * 100)
    _, slow = _capture(print_episodes, body, 10.4)
    _, fast = _capture(print_episodes, body, 50.0)
    dwell = [L for L in slow.splitlines() if "run(s)," in L]
    ok = (dwell == [L for L in fast.splitlines() if "run(s)," in L]
          and len(dwell) == 2 and all("9.90 s" in L for L in dwell))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the dwells are identical at "
          f"rate=10.4 and rate=50.0 and both read 9.90 s over {len(dwell)} "
          f"state(s): the axis comes from the sequence's timestamps, not from "
          f"main()'s `n / elapsed`. Scoring a 100-poll run against a "
          f"20%-dropped sample rate printed 12.23 +/- 0.17 s (n = 32 seeds) "
          f"for a run whose measured span is 9.90 s")

    # And the two rates are printed BESIDE each other, because their gap is the
    # drop rate -- the number that used to be silently folded into every dwell.
    ok = ("    poll rate 10.00 Hz over 19.90 s, from the sequence's own "
          "timestamps and NOT from the sample rate; the sample rate is 10.40 Hz"
          in " ".join(slow.splitlines()))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and both rates are printed, "
          f"10.00 Hz of polls against 10.40 Hz of samples, so a reader can see "
          f"the gap that used to corrupt the axis instead of inferring it")

    # THE MIRROR: a sequence with no measured span says UNRATED rather than
    # borrowing `rate`, so the check above is not passing on a printer that
    # always ignores its argument by printing nothing.
    _, out = _capture(print_episodes, [(1.0, "shut:append")], 10.4)
    ok = "UNRATED" in out and "unrated" in out and "10.4" not in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a single-poll sequence prints "
          f"UNRATED and every dwell `unrated` rather than falling back to the "
          f"sample rate -- a fallback would be the same units bug reintroduced "
          f"exactly where the sequence is shortest")

    # AND THE CALL SITE, behaviourally. Deleting `print_episodes(seq, rate)`
    # from `fence_verdict`, or handing it [], were both green: nothing outside
    # this section ever looked for the episode block in the output a run
    # actually prints. `fence_verdict` is what main() calls.
    _, out = _capture(fence_verdict, {"shut:append": 464, "test-runs": 100},
                      2, 563, 564, 10.0,
                      _seq(["shut:append"] * 300 + ["test-runs"] * 100
                           + ["shut:append"] * 164))
    ok = (want_a[1] in out.splitlines() and want_a[2] in out.splitlines())
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] fence_verdict prints the episode "
          f"block for the sequence it was HANDED -- the same `1 run(s), median "
          f"100 samples (9.90 s)` and `effective n = 3 ... over 564` lines. "
          f"Deleting the call, or passing [], leaves every check above green "
          f"because they all drive the printer directly")
    return bad, ran


def _selftest_flip_denominator():
    """9. C3: a flake is not a flip, and world1 <-> shut is not a fence change."""
    print("\n9. the flip denominator refuses to count a flaky read (C3)")
    bad = ran = 0
    cases = [
        ("real -> unread -> real counts NOTHING, not two transitions",
         ["shut:append", "unread:record-unreadable", "test-runs"], (0, 0)),
        ("a genuine fence change over two real samples counts once",
         ["shut:append", "test-runs"], (1, 1)),
        ("world1 <-> shut is a world-index change, not a fence flip",
         ["world1:append", "shut:append", "shut:noop"], (0, 2)),
        ("and the pair is still USABLE -- it is counted, just not as a flip",
         ["shut:append", "shut:append"], (0, 1)),
        ("an alternating fence over real samples counts every change",
         ["test-runs", "shut:append", "test-runs", "shut:append"], (3, 3)),
    ]
    for what, states, want in cases:
        got = count_flips(_seq(states))
        ok = got == want
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}: "
              f"(flips, pairs) = {got}, wanted {want}")

    # THE BAND THE OLD CODE DIED IN. 10% flaky reads over a fence that never
    # actually changes. The old rule counted `real -> unread` and
    # `unread -> real` as two transitions each time, manufacturing ~0.20
    # flips/sample -- 80% of the escalation bar -- while staying under the 25%
    # unread refusal that was supposed to catch a bad read.
    flaky = ["shut:append"] * 1000
    for i in range(9, 1000, 10):
        flaky[i] = "unread:record-unreadable"
    flips, pairs = count_flips(_seq(flaky))
    naive = sum(1 for i in range(1, len(flaky)) if flaky[i] != flaky[i - 1])
    ok = flips == 0 and pairs == 800 and naive == 199
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a 10% flaky read over a fence that "
          f"never changes scores {flips} flips over {pairs} usable pairs; the "
          f"rule this replaced scored {naive} over 999, i.e. "
          f"{naive / 999:.2f}/sample against an escalation bar of 0.5")

    # And the pair count has to REACH the verdict, not just be computed. Three
    # flips over six usable pairs is phi = 0.5 at a 50% open share: fully
    # aliased. Scored against `n - 1` = 999 it is phi = 0.003 and reads clean.
    reach = {"shut:append": 500, "test-runs": 500}
    rc, out = _capture(fence_verdict, reach, 3, 6, 1000, 12.0)
    ok = rc == 1 and "6 usable pair(s)" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] fence_verdict scores flips against "
          f"the PAIRS it was handed, not against n-1: 3 flips over 6 usable "
          f"pairs REFUSED (returned {rc}); the same 3 over 999 would have "
          f"printed 'not aliased'")

    rc, _ = _capture(fence_verdict, reach, 3, 999, 1000, 12.0)
    ok = rc == 0
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and the same call with 999 pairs "
          f"passes (returned {rc}), so the case above is discriminating on the "
          f"denominator and on nothing else")

    # BOTH HALVES OF `A` OVER THE SAME POPULATION. C3 moved `phi` onto real
    # pairs and left `p_open` on `n`, which REOPENED the hole C1 exists to
    # close -- from the other side and only above p = 0.5, which is exactly
    # where C1's calibration cells sit. A genuinely aliased fence at a 92.5%
    # open share, seen through a 20% flaky read: 740 test-runs and 60 shut over
    # 800 real samples, 200 unread (under the 25% bar, and inside the failure
    # table's expected operating band), 89 flips over 639 real pairs.
    # phi = 0.1393, which is what INDEPENDENT samples give at p = 0.925.
    # Split denominators: p = 0.740, A = 0.36 -- "not aliased", over a fence
    # flipping ten times a second. Same population: p = 0.925, A = 1.00.
    skewed = {"test-runs": 740, "shut:append": 60,
              "unread:record-unreadable": 200}
    rc, out = _capture(fence_verdict, skewed, 89, 639, 1000, 10.4)
    ok = rc == 1 and "92.5% open share" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] `p` is computed over the REAL "
          f"samples, like `phi` is: an aliased 92.5% fence behind a 20% flaky "
          f"read REFUSES (returned {rc}) and prints the share as 92.5%; scoring "
          f"p over all 1,000 samples calls it 74.0% and A = 0.36, which passes")

    rc, _ = _capture(fence_verdict, skewed, 9, 639, 1000, 10.4)
    ok = rc == 0
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and a SLOW fence at the same "
          f"92.5% share and the same 20% flake rate still passes (returned "
          f"{rc}), so the case above discriminates on the flip rate and not on "
          f"the presence of unread samples")

    # C5-adjacent, and it is the OTHER door into the contamination C3 shut:
    # main() used to `continue` past a failed resolve or a short agent block
    # WITHOUT appending anything, so a multi-second gap was joined into a
    # contiguous run -- no `censored`, no `split`, no unread sentinel -- and
    # `count_flips` scored the two samples either side of it as an adjacent
    # pair. The timestamps needed to see it were already in the tuple and were
    # discarded. Asked of the SYNTAX TREE, because the loop cannot be run
    # without a client, and counted first: a control that judges zero `continue`
    # statements is a control that passes forever.
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    loop = next(nd for nd in ast.walk(next(
        f for f in ast.walk(ast.parse(src))
        if isinstance(f, ast.FunctionDef) and f.name == "main"))
        if isinstance(nd, ast.While))

    def _stmt_lists(node):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list):
                yield block
                for st in block:
                    yield from _stmt_lists(st)
        for h in getattr(node, "handlers", None) or []:
            yield from _stmt_lists(h)

    def _appends_seq(node):
        return any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                   and c.func.attr == "append"
                   and isinstance(c.func.value, ast.Name)
                   and c.func.value.id == "seq" for c in ast.walk(node))

    marked = [any(_appends_seq(p) for p in block[:i])
              for block in _stmt_lists(loop)
              for i, st in enumerate(block) if isinstance(st, ast.Continue)]
    ok = len(marked) == 2 and all(marked)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] every one of the {len(marked)} "
          f"`continue` paths in the sampling loop appends to `seq` first "
          f"({marked}) -- a dropped sample that leaves no row lets "
          f"`count_flips` call the samples either side of a multi-second gap "
          f"an adjacent pair, and `episodes` merge two runs across it")

    ok = (not reach_is_real(REACH_DROPPED) and not reach_is_real(REACH_UNRESOLVED)
          and count_flips(_seq(["test-runs", REACH_DROPPED, "shut:append"]))
          == (0, 0)
          and [r["split"] for r in
               episodes(_seq(["shut:append", REACH_UNRESOLVED, "shut:append"]))]
          == [True, False, True])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the two markers "
          f"({REACH_DROPPED!r}, {REACH_UNRESOLVED!r}) are in the `unread:` "
          f"domain, so the gap breaks the pair chain in both directions and "
          f"marks the runs it bounds SPLIT rather than joining them")

    # ----------------------------------------------------------------------
    # THE REST OF THE WIRING, asked of the same syntax tree. The check above
    # covers 2 of the 9 points at which main() feeds this file's analysers, and
    # a review cut the other SEVEN with the selftest green at 122 and the suite
    # green at 147: `print_episodes(seq, rate)` deleted from `fence_verdict`,
    # `count_flips(seq)` deleted from main, the SUCCESS-path `seq.append`
    # deleted (which feeds C2 and C3 a sequence made of nothing but drop
    # markers), the `g1` / `g1why` / `early_a` / `point_bad` tallies never
    # filled, and `sample()` rewritten so it never calls `gate1_read` at all.
    # None of those is visible to a selftest that drives every analyser
    # DIRECTLY with a fixture, which is what every other check in this file
    # does; with `early_a = {}` the tool prints `early_out_a  0  0.0%
    # (0 unread)` -- a confident zero that reads as the finding, and the
    # `unread * 4 >= n` refusal is computed from `g1`, not from that tally.
    #
    # Counted BEFORE it is judged, and the three functions are located rather
    # than assumed: a table of requirements against a tree that does not
    # contain `main` would pass every row vacuously.
    tree = ast.parse(src)
    fns = {f.name: f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    f_main, f_fence, f_sample = (fns.get("main"), fns.get("fence_verdict"),
                                 fns.get("sample"))

    def _calls(node, name):
        return [c for c in ast.walk(node) if isinstance(c, ast.Call)
                and isinstance(c.func, ast.Name) and c.func.id == name] \
            if node is not None else []

    def _pos(call):
        return [a.id for a in call.args if isinstance(a, ast.Name)]

    # The one `seq.append` that is a DIRECT statement of the loop body: the two
    # give-up paths sit inside a handler and an `if`, so this is the success
    # path and nothing else. Requiring it to mention `gate_reach` stops the row
    # being satisfied by hoisting one of the markers up out of its branch --
    # which would redden the `continue` check above, so the two are a pair.
    direct = [st for st in loop.body
              if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
              and isinstance(st.value.func, ast.Attribute)
              and st.value.func.attr == "append"
              and isinstance(st.value.func.value, ast.Name)
              and st.value.func.value.id == "seq"]
    tallied = {a.targets[0].value.id for a in ast.walk(loop)
               if isinstance(a, ast.Assign)
               and isinstance(a.targets[0], ast.Subscript)
               and isinstance(a.targets[0].value, ast.Name)}
    want_tallies = {"reach", "g1", "g1why", "early_a", "point_bad"}
    rows = [
        ("the SUCCESS path appends (t, gate_reach) to `seq`",
         len(direct) == 1 and "gate_reach" in ast.dump(direct[0]),
         "without it C2 and C3 score a sequence of drop markers"),
        (f"main() tallies all of {', '.join(sorted(want_tallies))}",
         want_tallies <= tallied,
         f"missing {sorted(want_tallies - tallied)} -- an empty tally prints a "
         f"confident 0.0%, and gate1_verdict's unread refusal reads `g1`, not "
         f"these"),
        ("main() scores the sequence with `count_flips(seq)`",
         any(_pos(c)[:1] == ["seq"] for c in _calls(f_main, "count_flips")),
         "the aliasing ratio has no numerator otherwise"),
        ("main() hands `seq` to fence_verdict",
         any("seq" in _pos(c) for c in _calls(f_main, "fence_verdict")),
         "the episode block would print for an empty sequence"),
        ("main() hands g1/g1why/early_a/point_bad to gate1_verdict",
         any({"g1", "g1why", "early_a", "point_bad"} <= set(_pos(c))
             for c in _calls(f_main, "gate1_verdict")),
         "the C6/C7/C8 lane prints someone else's dict"),
        ("fence_verdict calls `print_episodes(seq, rate)`",
         any(_pos(c)[:2] == ["seq", "rate"]
             for c in _calls(f_fence, "print_episodes")),
         "C2's whole output vanishes from the run and from every fixture-driven "
         "check in section 8"),
        ("sample() calls gate1_read", bool(_calls(f_sample, "gate1_read")),
         "C6 measures nothing and every row carries no `sep`"),
        ("sample() calls early_outs", bool(_calls(f_sample, "early_outs")),
         "C7 and C8 measure nothing"),
        ("sample() calls agtrack_fence", bool(_calls(f_sample, "agtrack_fence")),
         "the fence lane measures nothing"),
        # REALFIX-I1's printed obligations. All three are output-only, which is
        # the class this arc has already watched go missing green twice:
        # movesync's C5 printer deleted from `print_fence` and the whole
        # section vanishing at 147/147, and five of PROBE-GATEFIRE.md 6's
        # blocks wrong under a RECONSTRUCTION label that checked nothing.
        ("main() prices the chain walk with `chain_cost`",
         bool(_calls(f_main, "chain_cost")),
         "REALFIX.md 2.4 requires the sample-rate impact to be MEASURED and "
         "printed, not predicted -- without this call the ~+40%% figure stays "
         "an argument in a comment"),
        # ...AND PRINTS IT. The row above judges the CALL and nothing else,
        # which a mutation proved by keeping the call, discarding the result
        # and printing neither figure at 206/206 green. This one requires the
        # cost to reach stdout: a `print(...)` whose arguments contain a
        # `chain_cost_line(...)` call. Section 13 pins what that string SAYS.
        ("main() PRINTS it -- `print(chain_cost_line(...))`",
         any(any(isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                 and arg.func.id == "chain_cost_line" for arg in c.args)
             for c in _calls(f_main, "print")),
         "a measured cost nobody prints is the assumption it was supposed to "
         "replace; the wiring row above keeps the CALL alive, not the OUTPUT"),
        ("main() prints `print_hist_summary(hist_why, hist_reads, n)`",
         any(_pos(c)[:3] == ["hist_why", "hist_reads", "n"]
             for c in _calls(f_main, "print_hist_summary")),
         "the refusal shares are the denominator every later claim about the "
         "polyline rests on; a run that dropped them would still print a "
         "confident chain"),
        ("main() tallies `hist_why` per sample",
         "hist_why" in tallied,
         "an untallied vocabulary prints an empty table and reads as "
         "\"nothing was refused\""),
    ]
    ok = (len(rows) == 13 and None not in (f_main, f_fence, f_sample)
          and len(tallied) > 0)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the wiring table judges "
          f"{len(rows)} call sites and located all three functions it asks "
          f"about (main / fence_verdict / sample), over {len(tallied)} "
          f"subscript-assigned name(s) in the loop -- a table run against a "
          f"tree missing `main` would pass every row below vacuously")
    for what, got, why in rows:
        bad += not got
        ran += 1
        print(f"   [{'PASS' if got else 'FAIL'}] {what}"
              + ("" if got else f" -- {why}"))
    return bad, ran


# --------------------------------------------------------------------------
# 10. GATE 1's OWN OPERANDS. Driven off a fake memory for the same reason the
# fence is: a null ASYNC slot and an out-of-bounds id do not happen on demand in
# a live process, so they would otherwise be the branches nobody ever executed.
# --------------------------------------------------------------------------
def _gate1_mem(array_ptr, count, slot_ptr, ablk, clock0, clock1, ag):
    hdr = bytearray(GATE1_HDR_SPAN)
    struct.pack_into("<i", hdr, 0, clock0)
    struct.pack_into("<I", hdr, OFF_ASYNC_ARRAY - OFF_WORLD_CLOCK, array_ptr)
    struct.pack_into("<I", hdr, OFF_ASYNC_COUNT - OFF_WORLD_CLOCK, count)
    struct.pack_into("<i", hdr, OFF_WORLD1_CLOCK - OFF_WORLD_CLOCK, clock1)

    def read(addr, n):
        if addr == ag + OFF_WORLD_CLOCK and n == GATE1_HDR_SPAN:
            return bytes(hdr)
        if array_ptr and addr == array_ptr + 7 * 4 and n == 4:
            return None if slot_ptr is None else struct.pack("<I", slot_ptr)
        if slot_ptr and addr == slot_ptr and n == AGENT_SPAN:
            return ablk
        return None
    return read


def _selftest_gate1():
    """10. C6: the ASYNC twin, the clamp, and the band this reader refuses."""
    print("\n10. gate 1 from memory: the ASYNC twin, the clamp, the band (C6)")
    bad = ran = 0
    ARRAY, AG, SLOT = 0x0A000000, 0x10000000, 0x0B000000

    # --- position_at, which is the half a reimplementation gets wrong --------
    moving = _fake_agent(7, point=(100.0, 200.0), vel=(10.0, -5.0),
                         updated=1000, stop=0, segment=(999.0, -999.0),
                         plane=3, seg_plane=4)
    x, y, plane, branch = position_at(moving, 3000)
    ok = (round(x, 3), round(y, 3), plane, branch) == (120.0, 190.0, 3,
                                                       "integrated")
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] with no arrival time it integrates: "
          f"(100,200) + (10,-5)*2.000 s = {(round(x, 3), round(y, 3))}, plane "
          f"from +0x80")

    arrived = _fake_agent(7, point=(100.0, 200.0), vel=(10.0, -5.0),
                          updated=1000, stop=2000, segment=(999.0, -999.0),
                          plane=3, seg_plane=4)
    got = position_at(arrived, 3000)
    ok = got == (999.0, -999.0, 4, "segment")
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] 0x005FF820 CLAMPS: past +0x48 it "
          f"copies m_segmentPoint verbatim and never integrates -> {got}. "
          f"Integrating instead would have said {position_at(moving, 3000)[:2]}"
          f", which is a separation the client never computes")

    ok = position_at(arrived, 2000)[3] == "segment"
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the boundary is `>=`, not `>` "
          f"-- 0x005FF834 branches on the SIGN of (time - stop), so time == "
          f"stop clamps")

    ok = position_at(arrived, 1999)[3] == "integrated"
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and one millisecond earlier it "
          f"still integrates, so the clamp is a boundary and not a constant")

    # --- the two clocks, which are NOT the same clock ------------------------
    # The SYNC agent is dated to world 0's clock and the ASYNC one to world 1's.
    # Both agents below sit still AT their own clock and move fast; if either
    # side were dated to the other's clock, its position would be off by the
    # skew times the velocity and the separation would be manufactured.
    sync = _fake_agent(7, point=(0.0, 0.0), vel=(1000.0, 0.0), updated=5000)
    asy = _fake_agent(7, world=1, point=(400.0, 0.0), vel=(1000.0, 0.0),
                      updated=9000)
    r = gate1_read(_gate1_mem(ARRAY, 64, SLOT, asy, 5000, 9000, AG),
                   AG, 7, sync)
    ok = (r["sync_at"][:2] == [0.0, 0.0] and r["async_at"][:2] == [400.0, 0.0]
          and r["sep"] == 400.0 and r["gate1"] == GATE1_ABOVE
          and r["sync_clock"] == 5000 and r["async_clock"] == 9000)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] each side is dated to ITS OWN clock "
          f"(world 0 = {r['sync_clock']}, world 1 = {r['async_clock']}): "
          f"sync {r['sync_at']}, async {r['async_at']}, sep {r['sep']}. Using "
          f"one clock for both would have moved a side by 4,000 u")

    def sep_case(dx, dy=0.0, plane=0, aplane=0):
        s = _fake_agent(7, point=(0.0, 0.0), plane=plane)
        a = _fake_agent(7, world=1, point=(float(dx), float(dy)), plane=aplane)
        return gate1_read(_gate1_mem(ARRAY, 64, SLOT, a, 0, 0, AG), AG, 7, s)

    for dx, want, want_why in ((400, GATE1_ABOVE, None),
                               (100, GATE1_BELOW, None),
                               (300, GATE1_UNDECIDED, "band"),
                               (296, GATE1_UNDECIDED, "band"),
                               (304, GATE1_UNDECIDED, "band"),
                               (294, GATE1_BELOW, None),
                               (306, GATE1_ABOVE, None)):
        r = sep_case(dx)
        ok = r["gate1"] == want and r["gate1_why"] == want_why
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] sep {dx:4} u -> {r['gate1']}"
              f"{'/' + r['gate1_why'] if r['gate1_why'] else ''}"
              f"{'' if ok else '  WANTED ' + str(want) + '/' + str(want_why)}")

    # ----------------------------------------------------------------------
    # THE DISTANCE METRIC ITSELF, WHICH EVERY FIXTURE ABOVE LEAVES FREE.
    #
    # All ten separation fixtures in this section -- the seven in the loop just
    # above, the plane case below, the two-clock case and the healthy-read case --
    # put the twin at (dx, 0) against a sync at (0, 0). Ten axis-aligned, zero
    # diagonal; and ON AN AXIS `abs(dx)`, `max(|dx|,|dy|)` (Chebyshev) and
    # `|dx|+|dy|` (Manhattan) are each the SAME NUMBER as the Euclidean hypot the
    # client computes. A review ran all three as mutations of `gate1_read` and
    # watched the whole 144-check selftest stay green on every one.
    #
    # This is not cosmetic. On a (283, 283) offset the true separation is
    # 400.22 u -> `above`, while Chebyshev reads 283.00 -> `below`, and `below`
    # with the fence open and neither early-out satisfied is the procedure's
    # escalation trigger 2(b) -- the outcome that buys a compiler. So the
    # fixtures below are OFF-AXIS, at more than one angle so a metric tuned to a
    # single 45-degree case cannot satisfy them, and each asserts the NUMBER as
    # well as the verdict: a metric that happens to agree on the verdict but
    # disagrees on `sep` is still the wrong metric, because `sep` is the value
    # the row ships with and the value a reader recomputes the classification
    # from.
    #
    # Hand-computed. The tolerance is half of `sep`'s own 2-dp rounding step, so
    # nothing wider than that rounding can hide inside it:
    #   ( 283,  283) -> 283*sqrt(2)      = 400.2224  above  (|dx| 283, cheb 283 -> BELOW)
    #   (-240,  -70) -> sqrt(57600+4900) = 250.0000  below  (manh 310           -> ABOVE)
    #   (  60,   80) -> sqrt(3600+6400)  = 100.0000  below  (|dx| 60, cheb 80, manh 140)
    SEP_TOL = 0.005
    diagonals = ((283.0, 283.0, 400.2224, GATE1_ABOVE),
                 (-240.0, -70.0, 250.0, GATE1_BELOW),
                 (60.0, 80.0, 100.0, GATE1_BELOW))
    # A CONTROL THAT JUDGES ZERO ROWS IS A DEFECT: say what this set has to be
    # before judging anything with it, or a later edit that quietly empties it
    # (or flattens it back onto an axis) restores the hole silently.
    angles = {round(math.degrees(math.atan2(abs(dy), abs(dx))), 3)
              for dx, dy, _s, _v in diagonals}
    ok = (len(diagonals) >= 3
          and all(dx and dy for dx, dy, _s, _v in diagonals)
          and len(angles) >= 2)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the metric fixtures are "
          f"{len(diagonals)} offsets, all off-axis on BOTH axes, at "
          f"{len(angles)} distinct angles {sorted(angles)} deg -- the ten "
          f"fixtures above are all axis-aligned, and on an axis |dx|, "
          f"max(|dx|,|dy|) and |dx|+|dy| are indistinguishable from hypot")

    for dx, dy, want_sep, want in diagonals:
        r = sep_case(dx, dy)
        ok = (r["sep"] is not None and abs(r["sep"] - want_sep) <= SEP_TOL
              and r["gate1"] == want)
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] ({dx:g}, {dy:g}) -> sep "
              f"{r['sep']} u = hand-computed {want_sep:.4f} +/- {SEP_TOL} u -> "
              f"{r['gate1']}; |dx| would read {abs(dx):g}, Chebyshev "
              f"{max(abs(dx), abs(dy)):g}, Manhattan {abs(dx) + abs(dy):g}"
              + ("" if ok else f"  WANTED {want_sep} / {want}"))

    # ----------------------------------------------------------------------
    # THE OPERAND PAIRING, WHICH EVERY FIXTURE ABOVE ALSO LEAVES FREE -- the
    # metric fixtures included, because they only moved the TWIN off the axis.
    #
    # Every sync-side agent handed to `gate1_read` in this section sits at the
    # ORIGIN: `_fake_agent`'s default `point=(0.0, 0.0)` plus the two that pass
    # it explicitly. With sx = sy = 0, `sep` is a function of the ASYNC point
    # alone and the PAIRING of the four operands is unconstrained --
    # `hypot(sx - ay, sy - ax)` (axes crossed), `hypot(ax, ay)` (the sync
    # position ignored entirely) and `hypot(sx + ax, sy + ay)` (sum instead of
    # difference) each reproduce `hypot(sx - ax, sy - ay)` EXACTLY on every one
    # of them, diagonals included. A review ran all three as mutations of
    # `gate1_read` and watched the whole 154-check selftest stay green on each.
    #
    # So these fixtures move the SYNC agent OFF the origin, with sx != sy, and
    # the twin off it too. Hand-computed, both scaled 3-4-5 triangles:
    #   sync (100, 400) vs twin (340, 720): d = (-240, -320) -> 400.0000  above
    #        crossed 622.8965, sync-ignored 796.2412, sum 1203.3287
    #   sync (500, 250) vs twin (620, 410): d = (-120, -160) -> 200.0000  below
    #        crossed 380.7887, sync-ignored 743.3034, sum 1300.0000
    # The second flips the VERDICT under all three and not merely the number,
    # and `below` with the fence open and neither early-out satisfied is the
    # procedure's escalation trigger 2(b) -- the outcome that buys a compiler.
    def pair_case(sx, sy, ax, ay):
        s = _fake_agent(7, point=(sx, sy))
        a = _fake_agent(7, world=1, point=(ax, ay))
        return gate1_read(_gate1_mem(ARRAY, 64, SLOT, a, 0, 0, AG), AG, 7, s)

    def mispairings(sx, sy, ax, ay):
        """What each NAMED wrong pairing would read on this fixture."""
        return (("axes crossed", math.hypot(sx - ay, sy - ax)),
                ("sync ignored", math.hypot(ax, ay)),
                ("sum not difference", math.hypot(sx + ax, sy + ay)))

    PAIRED = ((100.0, 400.0, 340.0, 720.0, 400.0, GATE1_ABOVE),
              (500.0, 250.0, 620.0, 410.0, 200.0, GATE1_BELOW))
    # A CONTROL THAT JUDGES ZERO ROWS IS A DEFECT: say what this set has to be,
    # and PROVE it discriminates, before judging anything with it. The second
    # clause is the one that matters -- a set can satisfy "sync off-origin,
    # sx != sy" and still land on a coincidence where a mispairing returns the
    # same number, and then the fixtures would be decoration.
    deltas = [abs(v - want_sep)
              for sx, sy, ax, ay, want_sep, _v in PAIRED
              for _nm, v in mispairings(sx, sy, ax, ay)]
    ok = (len(PAIRED) >= 2
          and all(sx and sy and sx != sy
                  for sx, sy, _ax, _ay, _s, _v in PAIRED)
          and all(ax or ay for _sx, _sy, ax, ay, _s, _v in PAIRED)
          and len(deltas) == 3 * len(PAIRED)
          and min(deltas) > SEP_TOL)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the pairing fixtures are "
          f"{len(PAIRED)} offsets whose SYNC agent is off the origin with "
          f"sx != sy, and all {len(deltas)} of the three named mispairings "
          f"across them miss the true separation by at least "
          f"{min(deltas):.2f} u (> {SEP_TOL} u) -- every other fixture in this "
          f"section puts the sync side at (0, 0), where all three read the "
          f"RIGHT answer")

    for sx, sy, ax, ay, want_sep, want in PAIRED:
        r = pair_case(sx, sy, ax, ay)
        ok = (r["sep"] is not None and abs(r["sep"] - want_sep) <= SEP_TOL
              and r["gate1"] == want)
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] sync ({sx:g}, {sy:g}) vs twin "
              f"({ax:g}, {ay:g}) -> sep {r['sep']} u = hand-computed "
              f"{want_sep:.4f} +/- {SEP_TOL} u -> {r['gate1']}; "
              + ", ".join(f"{nm} would read {v:.2f}"
                          for nm, v in mispairings(sx, sy, ax, ay))
              + ("" if ok else f"  WANTED {want_sep} / {want}"))

    r = sep_case(1000, plane=0, aplane=1)
    ok = (r["gate1"] == GATE1_UNDECIDED and r["gate1_why"] == "plane-mismatch"
          and r["sep"] == 1000.0)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] two different planes REFUSE the "
          f"classification even at 1,000 u: 0x00709990 compares the plane words "
          f"at 0x007099F1 and takes an undecoded path when they differ, so a 2D "
          f"distance across them is not gate 1's predicate. sep is still "
          f"reported ({r['sep']}) because it is a real measurement of something "
          f"else")

    # --- the refusals -------------------------------------------------------
    good_a = _fake_agent(7, world=1, point=(400.0, 0.0))
    refusals = [
        ("the clock/array block is unreadable", lambda a, n: None,
         "unread:clock-block-unreadable"),
        ("a null ASYNC array", _gate1_mem(0, 64, SLOT, good_a, 0, 0, AG),
         "unread:async-array-null"),
        ("an implausible ASYNC count",
         _gate1_mem(ARRAY, 1 << 30, SLOT, good_a, 0, 0, AG),
         "unread:async-count-implausible"),
        ("an id past ArenaNet's own bound at 0x0060575E",
         _gate1_mem(ARRAY, 3, SLOT, good_a, 0, 0, AG),
         "unread:async-id-out-of-bounds"),
        ("the slot itself unreadable",
         _gate1_mem(ARRAY, 64, None, good_a, 0, 0, AG),
         "unread:async-slot-unreadable"),
        ("a null twin pointer -- the client asserts on this too",
         _gate1_mem(ARRAY, 64, 0, good_a, 0, 0, AG),
         "unread:async-slot-null"),
        ("the twin's own block unreadable",
         _gate1_mem(ARRAY, 64, SLOT, None, 0, 0, AG),
         "unread:async-agent-unreadable"),
        ("the twin says it is a different agent",
         _gate1_mem(ARRAY, 64, SLOT, _fake_agent(9, world=1), 0, 0, AG),
         "unread:async-id-mismatch"),
    ]
    got_all = []
    for what, read, want in refusals:
        r = gate1_read(read, AG, 7, _fake_agent(7))
        got_all.append(r)
        ok = (r["gate1"] == want and r["sep"] is None
              and set(r) == set(GATE1_KEYS))
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {what} -> {r['gate1']}"
              f"{'' if ok else '  WANTED ' + want}")

    r = gate1_read(_gate1_mem(ARRAY, 64, SLOT, good_a, 0, 0, AG), AG, 7,
                   bytes(4))
    got_all.append(r)
    ok = r["gate1"] == "unread:agent-block-short" and r["sep"] is None
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a short SYNC block -> {r['gate1']}")

    # THE SYNC SIDE, which had no id guard at all until 2026-08-20 while the
    # ASYNC side had one and `agtrack_fence` had one on the same two inputs.
    # This exact fixture -- aid 7, a SYNC block that says it is agent 9, a
    # readable twin 1,000 u away -- used to return `gate1 = "above"` and
    # `sep = 1000.0` in the same row as `gate_reach = "unread:agent-id-mismatch"`.
    far = _fake_agent(7, world=1, point=(1000.0, 0.0))
    r = gate1_read(_gate1_mem(ARRAY, 64, SLOT, far, 0, 0, AG), AG, 7,
                   _fake_agent(9))
    got_all.append(r)
    ok = r["gate1"] == "unread:sync-id-mismatch" and r["sep"] is None
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a SYNC block that says it is a "
          f"DIFFERENT agent -> {r['gate1']} (sep {r['sep']!r}); without this "
          f"refusal the same fixture classified a 1,000 u separation between "
          f"agent 9 and agent 7 as `above`, which is escalation trigger 2(b)")

    # The aggregate assertion, stated rather than left implicit: no failure mode
    # may present as a classification. "below" is the interesting answer here --
    # a snap that began below the cut is escalation trigger 2(b) -- so a failed
    # read that produced one would be read as the finding, exactly as a raw 0
    # would be for the fence.
    ok = all(r["gate1"].startswith("unread:") and r["sep"] is None
             and r["gate1_why"] is None for r in got_all)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] none of the {len(got_all)} failure "
          f"modes returns above/below/undecided or a plausible `sep` -- "
          f"`below` with the fence open is an escalation trigger, so a failed "
          f"read that produced one would buy a compiler")

    # And the mirror, so a stub that refuses everything cannot pass this section.
    r = gate1_read(_gate1_mem(ARRAY, 64, SLOT, good_a, 111, 222, AG), AG, 7,
                   _fake_agent(7))
    ok = (r["async_ptr"] == SLOT and r["async_count"] == 64
          and r["async_id"] == 7 and r["async_world"] == 1
          and r["sync_clock"] == 111 and r["async_clock"] == 222
          and r["sync_branch"] == "integrated" and r["async_branch"] == "integrated"
          and r["sep"] == 400.0 and r["gate1"] == GATE1_ABOVE)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a healthy read populates every "
          f"field: ptr=0x{r['async_ptr']:08X} count={r['async_count']} "
          f"id={r['async_id']} world={r['async_world']} sep={r['sep']} "
          f"branches={r['sync_branch']}/{r['async_branch']}")

    # ----------------------------------------------------------------------
    # THE PRINTED SHARE TABLE, CELL BY CELL -- and PROBE-GATEFIRE section 6 reads
    # exactly this table to answer the probe's question. Every check above this
    # point drives `gate1_read` and asks it for a dict; a review found that the
    # whole per-state table could print `0  0.0%`, that the `undecided` reason
    # breakdown could be deleted, and that the 295-305 u refusal prose could
    # vanish outright, all three green in `--selftest` AND in the suite. Same
    # argument the early-out line already carries one function away: the line IS
    # the output, so it is asserted VERBATIM against a hand-computed fixture.
    # 700/150/100/50 over n = 1000 -- four distinct cells, ordered by count, one
    # of them unread but under the 25% bar so the lane still returns 0.
    rc, out = _capture(gate1_verdict,
                       {GATE1_ABOVE: 700, GATE1_BELOW: 150, GATE1_UNDECIDED: 100,
                        "unread:async-slot-null": 50},
                       {"band": 60, "plane-mismatch": 40},
                       {False: 1000}, {False: 1000}, 1000)
    lines = out.splitlines()
    want = ["  above                                 700   70.0%",
            "  below                                 150   15.0%",
            "  undecided                             100   10.0%"
            "  (band 60, plane-mismatch 40)",
            "  unread:async-slot-null                 50    5.0%"]
    at = [lines.index(w) for w in want if w in lines]
    ok = rc == 0 and len(at) == 4 and at == sorted(at)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the share table prints its four "
          f"cells with their counts AND their percentages, in count order -- "
          f"700/70.0%, 150/15.0%, 100/10.0%, 50/5.0% over n = 1,000. Hard-"
          f"wiring the whole table to `0  0.0%` was green in every check above"
          + ("" if ok else f"  rc={rc} MATCHED {at} OF {want!r} IN {lines!r}"))

    ok = ("  undecided                             100   10.0%"
          "  (band 60, plane-mismatch 40)" in lines
          and not any(L.startswith("  above") and "(" in L for L in lines)
          and not any(L.startswith("  below") and "(" in L for L in lines))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and the reason breakdown rides "
          f"the `undecided` row ONLY -- `band 60, plane-mismatch 40` is what "
          f"separates \"this reader cannot resolve the step\" from \"the client "
          f"took an undecoded path\", and deleting it left every other check "
          f"green")

    _, out2 = _capture(gate1_verdict,
                       {GATE1_ABOVE: 700, GATE1_BELOW: 150, GATE1_UNDECIDED: 100,
                        "unread:async-slot-null": 50},
                       {}, {False: 1000}, {False: 1000}, 1000)
    ok = ("  undecided                             100   10.0%" in
          out2.splitlines())
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and with no reasons recorded the "
          f"same row prints bare, so the check above discriminates on the "
          f"breakdown rather than matching a parenthesis that is always there")

    ok = ("  the 295-305 u band is REFUSED rather than classified: the client's "
          "sqrt at 0x0046E870" in lines
          and "  reader cannot resolve the step. A plane mismatch is refused "
              "too -- 0x00709990" in lines)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the table names the 295-305 u band "
          f"it refuses, and the plane mismatch, in the block that prints the "
          f"shares -- GATE1_CUT +/- GATE1_BAND spelled out, so a reader of section 6 "
          f"cannot take `above`/`below` for a resolved step at 300 u")

    rc, out = _capture(gate1_verdict,
                       {GATE1_ABOVE: 700, "unread:async-slot-null": 300},
                       {}, {False: 1000}, {False: 1000}, 1000)
    ok = rc == 1 and "REFUSED" in out and "FENCE VERDICT ABOVE IS UNAFFECTED" in out
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a gate-1 lane that could not read "
          f"the twin for 30% of samples REFUSES its shares (returned {rc}) and "
          f"says in the same breath that the fence verdict is untouched -- a "
          f"failed control must not void the other lane")

    rc, _ = _capture(gate1_verdict, {}, {}, {}, {}, 1)
    ok = rc == 1
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a lane that read nothing at all "
          f"returns {rc} rather than printing 0% of nothing")
    return bad, ran


def _selftest_early_outs():
    """11. C7/C8: the two exits above gate 1, and their three-valued sentinel."""
    print("\n11. the two early-outs above gate 1 (C7, C8)")
    bad = ran = 0
    INF = (INVALID_POS, INVALID_POS)
    cases = [
        ("+0x48 set and mode 9 -- early-out A FIRES",
         _fake_agent(7, stop=1234, mode=9), True, False),
        ("mode 9 but +0x48 clear -- the first conjunct fails",
         _fake_agent(7, stop=0, mode=9), False, False),
        ("+0x48 set but mode 1 (every 0x002B we send carries mode 1)",
         _fake_agent(7, stop=1234, mode=1), False, False),
        ("mode 8 is the top of 0x00602660's own switch, and is not 9",
         _fake_agent(7, stop=1234, mode=8), False, False),
        ("both halves of m_point are +inf -- early-out B FIRES",
         _fake_agent(7, point_bits=INF), False, True),
        ("only the x half is +inf -- B needs BOTH",
         _fake_agent(7, point_bits=(INVALID_POS, 0)), False, False),
        ("only the y half is +inf",
         _fake_agent(7, point_bits=(0, INVALID_POS)), False, False),
        ("an ordinary agent trips neither",
         _fake_agent(7, point=(1.0, 2.0), stop=5, mode=1), False, False),
    ]
    for what, blk, want_a, want_b in cases:
        r = early_outs(blk)
        ok = r["early_out_a"] is want_a and r["point_invalid"] is want_b
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}: a={r['early_out_a']!r} "
              f"b={r['point_invalid']!r}"
              f"{'' if ok else f'  WANTED {want_a}/{want_b}'}")

    r = early_outs(_fake_agent(7, mode=9))
    ok = r["mode"] == 9 and set(r) == set(EARLY_KEYS)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] +0xC4 is recorded raw as well as "
          f"derived ({r['mode']!r}) -- the derivation is ours, the field is the "
          f"client's, and only the second survives a change of mind")

    # THE SENTINEL. `False` is a real answer to "did this exit fire", so a block
    # we could not read must not produce one. Same rule as the fence's 0.
    r = early_outs(bytes(4))
    ok = (isinstance(r["early_out_a"], str) and isinstance(r["point_invalid"], str)
          and not isinstance(r["early_out_a"], bool)
          and r["early_out_a"].startswith("unread:")
          and r["point_invalid"].startswith("unread:") and r["mode"] is None)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a short block yields "
          f"{r['early_out_a']!r}, a STRING and not False -- `False` here means "
          f"\"the exit did not fire\", which is the finding, so a failed read "
          f"must not be able to say it")

    r = early_outs(None)
    ok = isinstance(r["early_out_a"], str) and set(r) == set(EARLY_KEYS)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a missing block does the same "
          f"rather than raising: {r['early_out_a']!r}")

    # AND THE PRINTED LINE, which is the whole product of C7 and C8. Everything
    # above asks `early_outs()` for a dict; the run prints one line per exit and
    # nothing was asserting on it, so forcing that line to a constant
    # `0 / 0.0% / (0 unread)` -- and deleting the "IT FIRED" sentence outright
    # -- both left this selftest green. `sample()` returns None on a short
    # block, so the unread sentinel can never reach the tally in production
    # either: the line IS the output.
    rc, out = _capture(gate1_verdict, {GATE1_BELOW: 1000}, {},
                       {True: 40, False: 948, "unread:agent-block-short": 12},
                       {False: 1000}, 1000)
    ok = (rc == 0 and "    40    4.0%   (12 unread)" in out
          and "IT FIRED" in out)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the early-out line prints the "
          f"tally it was handed -- 40 fired, 4.0%, 12 unread -- and says "
          f"*** IT FIRED, which is the single most consequential sentence this "
          f"lane can emit and was asserted nowhere")

    rc, out = _capture(gate1_verdict, {GATE1_BELOW: 1000}, {},
                       {False: 1000}, {False: 1000}, 1000)
    ok = (rc == 0 and "IT FIRED" not in out
          and "     0    0.0%   (0 unread)" in out)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and a run where neither exit "
          f"fired does NOT say it, so the check above discriminates in both "
          f"directions rather than matching a sentence that is always printed")
    return bad, ran


def _selftest_naming():
    """12. C9: the stored strings, and no printed sentence asserting a call."""
    print("\n12. the capture's own vocabulary (C9)")
    bad = ran = 0
    src = open(os.path.abspath(__file__), encoding="utf-8").read()

    # BUILT, never written. A literal here would match itself -- the same defect
    # section 3's comment describes, and it turns a landing check into a check
    # that cannot pass. It also has to stay out of the file for the DOCUMENTED
    # grep in the probe's step 2 (which must return 0) to mean anything.
    for gone in (s + ":" + "app" + "ly" for s in ("shut", "world1")):
        ok = gone not in src
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] `{gone}` appears nowhere in "
              f"this file -- 0x00605840 APPENDS to the history chain, it does "
              f"not apply anything, and that string goes into every stored row "
              f"permanently. `grep -c` for it is the documented landing check, "
              f"so even a historical mention in prose would break it")

    # The four real values, taken from the function rather than from a copy of
    # the list: if a fifth branch is ever added and not classified, this goes red
    # rather than silently dropping it out of both phi and p.
    ARRAY, AG = 0x0A000000, 0x10000000

    def mem(controlled):
        rec = struct.pack("<II", controlled, 0) + bytes(STATE_STRIDE - 8)

        def read(addr, n):
            if addr == AG + OFF_AGTRACK + T_STATE_ARRAY:
                return struct.pack("<III", ARRAY, 0, 64)
            if addr == ARRAY + 7 * STATE_STRIDE:
                return rec[:n]
            return None
        return read

    seen = {agtrack_fence(mem(c), AG, 7, _fake_agent(7, world=w))["gate_reach"]
            for c, w in ((1, 0), (1, 1), (0, 0), (0, 2))}
    ok = seen == set(REACH_FENCED) | {REACH_TEST_RUNS}
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the four branches emit exactly the "
          f"values the flip rule classifies: {sorted(seen)}. A branch outside "
          f"REACH_FENCED + REACH_TEST_RUNS would fall out of both phi and p "
          f"without any error")

    ok = (test_would_run(REACH_TEST_RUNS)
          and not any(test_would_run(v) for v in REACH_FENCED))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and `world1:append` is NOT counted "
          f"as open: world 1 is the branch on which the caller skips the test "
          f"entirely, so folding it in would inflate p and deflate the aliasing "
          f"ratio -- the wrong direction for a guard")

    # THE PRINTED SENTENCE. `gate_reach` names a branch nobody watched execute,
    # and the summary has to say so where the number is read, not in a doc.
    _, out = _capture(fence_verdict, {"shut:append": 900, "test-runs": 100},
                      2, 999, 1000, 12.0, _seq(["shut:append"] * 900
                                               + ["test-runs"] * 100))
    ok = ("COUNTERFACTUAL" in out and "NOT an observation" in out
          and "WOULD take" in out)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fence summary names itself a "
          f"counterfactual label on a state read, in the block that prints the "
          f"shares -- nothing here observes 0x00605FC0 executing")

    # THE PHRASE, not the word. This asserted `"would" in docstring.lower()`
    # until 2026-08-20, and the docstring says "a failed read that returned 0,
    # or None, or False would be indistinguishable" four hundred characters
    # earlier -- about something else entirely. Rewriting the four-value table's
    # own sentence to "the branch the caller takes" left the check green, so it
    # was a check that could not fail. Whitespace-normalised because the phrase
    # straddles a line break, and a check that a reflow can redden is a check
    # about the formatter.
    doc = " ".join((agtrack_fence.__doc__ or "").split())
    ok = "Each value names the branch the caller WOULD take on this state" in doc
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the docstring the four values "
          f"are defined in is written in the conditional too -- the phrase "
          f"itself, in the table's own sentence, not the word 'would' anywhere "
          f"in 2,000 characters")

    # NO FIELD MAY BE OVERWRITTEN BY ANOTHER. `sample()` merges three dicts into
    # a literal one with `**`, and a duplicate key there is not an error in
    # Python -- the last writer silently wins and the field it clobbered is
    # simply absent from every stored row for the rest of the arc. Asked of the
    # SYNTAX TREE, like section 3, because the groups are built at run time.
    import ast
    fn = next(nd for nd in ast.walk(ast.parse(src))
              if isinstance(nd, ast.FunctionDef) and nd.name == "sample")
    ret = next(nd for nd in ast.walk(fn)
               if isinstance(nd, ast.Return) and isinstance(nd.value, ast.Dict))
    literal = [k.value for k in ret.value.keys
               if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    groups = {"literal": literal, "fence": list(FENCE_KEYS),
              "gate1": list(GATE1_KEYS), "early": list(EARLY_KEYS),
              # REALFIX-I1's group, and the collision it was one character from
              # making: the fence already ships `hist_head`, so a chain key
              # spelled `hist_head` would have silently replaced the head
              # pointer with something else in every stored row.
              "hist": list(HIST_KEYS),
              # CANCELWALK-R5's SYNC group, minus the one name sample() already
              # ships from the same offset. `stop` is filtered at the splice
              # rather than renamed, and this list records that decision where
              # the collision would be caught: this check is what found it.
              "r5": [k for k in R5_KEYS if k != "stop"],
              # CANCELWALK-R7's controller operands.
              "ctrl": list(CTRL_KEYS)}
    seen, dupes = set(), set()
    for keys in groups.values():
        dupes |= seen & set(keys)
        dupes |= {k for k in keys if keys.count(k) > 1}
        seen |= set(keys)
    ok = not dupes and sum(k is None for k in ret.value.keys) == 6
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the {len(seen)} fields a row "
          f"carries are unique across all {len(groups)} groups "
          f"({', '.join(f'{g} {len(k)}' for g, k in groups.items())}) and "
          f"sample() splices exactly 6 of them"
          + (f" -- COLLIDING: {sorted(dupes)}" if dupes else ""))

    # AND THE SPLICE REALLY IS THE FUNCTION'S OWN. `sample()` calling
    # `history_chain` is what makes every I1 number a measurement of the client
    # rather than of a fixture; a row could carry all eight `hist_*` keys from a
    # blank and look identical in the file. Asked of the syntax tree for the
    # same reason as the group check above -- C3's "a paraphrase that agrees
    # with the predicate by construction" defect, one arc over.
    calls = {nd.func.id for nd in ast.walk(fn)
             if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name)}
    ok = "history_chain" in calls
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and sample() actually CALLS "
          f"history_chain (it calls {sorted(calls)}) -- eight blank hist_* "
          f"keys spliced from nowhere would look the same in the file")
    return bad, ran


# --------------------------------------------------------------------------
# 13. REALFIX-I1's WALK, DRIVEN OVER A CHAIN WE BUILT.
#
# No client, no vault, no ReadProcessMemory: the fixture is a bytearray and a
# `read()` closure over it, which is the same trick sections 6 and 10 use. The
# point is not that the parser can walk a healthy chain -- it is that every way
# a chain can be WRONG produces a named reason and never a short chain that
# reads as a finding. "No node within the radius of q" is the sentence that
# revives candidate B, and a torn read produces it for free.
# --------------------------------------------------------------------------
CHAIN_BLOCK = 0x0B000000       # where the fixture's nodes live
CHAIN_AGENT = 0x0C000000       # the ASYNC twin's block


def _chain_mem(nodes, extra=None, async_plane=None, short=None):
    """A `read(addr, n)` over a synthetic chain. -> (read, reads_list).

    `nodes` is [(addr, time, x, y, plane, w, next_addr)] laid out verbatim, so a
    test can build a chain the client could never produce -- which is the whole
    point of the refusal cases.

    `short` is {addr: bytes_to_return} and exists because WITHOUT IT THE SHORT
    READ WAS UNREACHABLE. `history_chain` refuses on `len(blk) < HIST_NODE_SPAN`
    as well as on `blk is None`, and every fixture here returned either a
    full-span buffer or None -- so dropping the length half of that condition
    and zero-padding the buffer ran green, fabricating a vertex at the origin
    with next=0 that terminates the chain and reports `ok`. That is the exact
    phantom the refusal vocabulary exists to prevent. (Live exposure today is
    nil: `keytap.read_handle` returns None when ReadProcessMemory transfers
    fewer bytes than asked -- keytap.py's `got.value != size`. The branch is a
    contract of `history_chain`'s own `read(addr, n)` interface, which the
    docstring advertises as drivable from any reader.)
    """
    mem = dict(extra or {})
    cut = dict(short or {})
    for addr, t, x, y, plane, w, nxt in nodes:
        b = bytearray(HIST_NODE_SPAN)
        struct.pack_into("<i", b, N_TIME, t)
        struct.pack_into("<I", b, N_NEXT, nxt)
        struct.pack_into("<ffii", b, N_POINT, x, y, plane, w)
        mem[addr] = bytes(b)
    if async_plane is not None:
        mem[CHAIN_AGENT + A_POINT + 8] = struct.pack("<i", async_plane)
    log = []

    def read(addr, n):
        log.append((addr, n))
        got = mem.get(addr)
        if got is None:
            return None
        return got[:min(n, cut[addr])] if addr in cut else got[:n]
    return read, log


CHAIN_AGBASE = 0x0A000000
CHAIN_STATE_ARRAY = 0x0B100000
CHAIN_ASYNC_ARRAY = 0x0B200000
CHAIN_SYNC_PTR = 0x0D000000


def _sample_mem(rec, nodes, sync, async_blk, clock=9000):
    """A whole-sample memory: enough regions for `sample()` to run end to end.

    Region-based rather than exact-address-keyed, because `gate1_read` reads
    0x68 bytes spanning the world-0 clock, the ASYNC array pointer, its count
    and the world-1 clock while `sample()` reads 4 bytes at the front of the
    same span -- a dict keyed on (addr, n) cannot serve both, and pretending it
    can is how a fixture ends up measuring itself.

    -> (read, counter) where `counter` is a one-element list of read calls, so
    the COST of the chain walk is a measurement rather than an estimate.
    """
    hdr = bytearray(GATE1_HDR_SPAN)
    struct.pack_into("<i", hdr, 0, clock)
    struct.pack_into("<I", hdr, OFF_ASYNC_ARRAY - OFF_WORLD_CLOCK,
                     CHAIN_ASYNC_ARRAY)
    struct.pack_into("<I", hdr, OFF_ASYNC_COUNT - OFF_WORLD_CLOCK, 64)
    struct.pack_into("<i", hdr, OFF_WORLD1_CLOCK - OFF_WORLD_CLOCK, clock)
    track = bytearray(T_STATE_ARRAY + 0x0C)
    struct.pack_into("<I", track, T_ARMED_ID, 7)
    struct.pack_into("<I", track, T_STATE_ARRAY, CHAIN_STATE_ARRAY)
    struct.pack_into("<I", track, T_STATE_COUNT, 64)
    regions = [
        (CHAIN_AGBASE + OFF_WORLD_CLOCK, bytes(hdr)),
        (CHAIN_AGBASE + OFF_AGTRACK, bytes(track)),
        (CHAIN_STATE_ARRAY + 7 * STATE_STRIDE, rec),
        (CHAIN_ASYNC_ARRAY + 7 * 4, struct.pack("<I", CHAIN_SYNC_PTR + 0x100000)),
        (CHAIN_SYNC_PTR, sync),
        (CHAIN_SYNC_PTR + 0x100000, async_blk),
    ]
    for addr, t, x, y, plane, w, nxt in nodes:
        b = bytearray(HIST_NODE_SPAN)
        struct.pack_into("<i", b, N_TIME, t)
        struct.pack_into("<I", b, N_NEXT, nxt)
        struct.pack_into("<ffii", b, N_POINT, x, y, plane, w)
        regions.append((addr, bytes(b)))
    count = [0]

    def read(addr, n):
        count[0] += 1
        for base, blob in regions:
            if base <= addr and addr + n <= base + len(blob):
                return blob[addr - base:addr - base + n]
        return None
    return read, count


def _chain_record(head, point=(11.0, 22.0, 18, 0), at=1000):
    """The 28-byte AgTrack record: controlled, head, the cached vertex, its epoch."""
    b = bytearray(STATE_STRIDE)
    struct.pack_into("<I", b, S_CONTROLLED, 1)
    struct.pack_into("<I", b, S_HIST_HEAD, head)
    struct.pack_into("<ffii", b, S_HIST_POINT, point[0], point[1], point[2],
                     point[3])
    struct.pack_into("<i", b, S_HIST_AT, at)
    return bytes(b)


def _straight_chain(n, first=CHAIN_BLOCK + 4, t0=9000, dt=300):
    """n nodes, push-front order (newest first), null-terminated."""
    out = []
    for i in range(n):
        addr = first + i * HIST_NODE_STRIDE
        nxt = 0 if i == n - 1 else first + (i + 1) * HIST_NODE_STRIDE
        out.append((addr, t0 - i * dt, 100.0 * i, 200.0 * i, 18 if i else 0,
                    0, nxt))
    return out


def _selftest_chain():
    """13. the history-chain walk refuses rather than returning a short chain."""
    import contextlib
    import io
    print("\n13. REALFIX-I1: the history chain, and every way it can refuse")
    bad = ran = 0
    NOW = 9000
    # THE SYNC AGENT'S PLANE IS 19 AND ITS W WORD IS 77, and neither is an
    # accident. This fixture used to be `_fake_agent(7, plane=0)`, where the
    # plane dword and the w dword beside it were BOTH zero -- so reading
    # A_POINT+12 instead of A_POINT+8 was invisible, and that is the half of
    # the pair grant #37 turns on. Three distinct values (sync 19, w 77, async
    # 3) make every substitution nameable.
    _ag = bytearray(_fake_agent(7, plane=19))
    struct.pack_into("<i", _ag, A_POINT + 12, 77)
    AGENT = bytes(_ag)

    def run(nodes, rec, sep=400.0, async_ptr=CHAIN_AGENT, extra=None,
            async_plane=3, gate=HIST_SEP_GATE, agent=AGENT, short=None):
        read, log = _chain_mem(nodes, extra, async_plane, short)
        return history_chain(read, rec, sep, async_ptr, agent, NOW,
                             gate=gate), log

    def case(what, got, want_why, want_n, why_it_matters=""):
        nonlocal bad, ran
        ok = (got["hist_why"] == want_why
              and (got["hist_n"] == want_n)
              and set(got) == set(HIST_KEYS))
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {what}\n"
              f"          -> {got['hist_why']} / n={got['hist_n']}"
              + ("" if ok else f"   WANTED {want_why} / n={want_n}")
              + (f"\n          {why_it_matters}" if why_it_matters and not ok
                 else ""))
        return got

    # --- the healthy walk -------------------------------------------------
    good, log = run(_straight_chain(4), _chain_record(CHAIN_BLOCK + 4))
    case("a 4-node chain walks to its null terminator", good, HIST_OK, 4)
    want = [{"addr": CHAIN_BLOCK + 4 + i * HIST_NODE_STRIDE,
             "t": 9000 - i * 300,
             "p": [round(100.0 * i, 2), round(200.0 * i, 2), 18 if i else 0, 0],
             "age_ms": i * 300} for i in range(4)]
    ok = good["hist"] == want
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and every node carries its ADDRESS, "
          f"its +0x00 time, its age, and the four-dword point INCLUDING the "
          f"plane word -- {(good['hist'] or [])[:1]}...")
    ok = (good["hist_seed"] == [11.0, 22.0, 18, 0] and good["hist_seed_at"] == 1000)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the RECORD's own cached vertex is "
          f"decoded too ({good['hist_seed']} at {good['hist_seed_at']}) -- it "
          f"is the polyline's vertex 0 (0x0060569A reads it before 0x006056AF "
          f"steps to the head) and it costs no read at all")
    ok = (good["hist_sync_plane"] == 19 and good["hist_async_plane"] == 3)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] BOTH copies' own +0x80 plane words "
          f"are recorded (sync {good['hist_sync_plane']}, async "
          f"{good['hist_async_plane']}) -- without the pair, grant #37 stays "
          f"unadjudicable, and that grant is the whole of 'causes' vs 'permits'")
    ok = (good["hist_sync_plane"] == i32(AGENT, A_POINT + 8) == 19
          and i32(AGENT, A_POINT + 12) == 77
          and good["hist_sync_plane"] != i32(AGENT, A_POINT + 12)
          and good["hist_sync_plane"] != good["hist_async_plane"])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the SYNC read really is the "
          f"plane word at +0x{A_POINT + 8:X} and not the w word at "
          f"+0x{A_POINT + 12:X} beside it ({i32(AGENT, A_POINT + 8)} vs "
          f"{i32(AGENT, A_POINT + 12)}, async {good['hist_async_plane']}) -- "
          f"all three distinct, so no substitution reads as agreement")
    ok = (good["hist_reads"] == 5 and len(log) == 5
          and log[0] == (CHAIN_AGENT + A_POINT + 8, 4))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it spent exactly "
          f"{good['hist_reads']} read(s): one per node plus one 4-byte read for "
          f"the twin's plane. The budget is the whole reason for the gate, so "
          f"it is asserted rather than assumed")

    # --- the gate ---------------------------------------------------------
    below, log = run(_straight_chain(4), _chain_record(CHAIN_BLOCK + 4),
                     sep=HIST_SEP_GATE)
    case(f"exactly at the gate ({HIST_SEP_GATE:.0f} u) is BELOW it",
         below, "not-attempted:below-gate", None)
    ok = not log
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and NO read was issued at all "
          f"({len(log)}) -- the gate is a design requirement, not a filter on "
          f"the output: 8 unconditional node reads is ~+40% of a sample and "
          f"would fight REALFIX-T3's residual budget")
    ok = HIST_SEP_GATE < GATE1_CUT - GATE1_BAND
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the gate ({HIST_SEP_GATE:.0f} u) "
          f"sits below the bottom of GATE1_BAND "
          f"({GATE1_CUT - GATE1_BAND:.0f} u), so no sample that could ever be "
          f"classified `above` is skipped by it")
    case("gate 1 could not read `sep`, so the walk does not guess",
         run(_straight_chain(4), _chain_record(CHAIN_BLOCK + 4), sep=None)[0],
         "not-attempted:sep-unread", None)
    case("no state record is a THIRD thing, not an empty chain",
         run(_straight_chain(4), None)[0],
         "not-attempted:no-state-record", None)

    # --- a real empty chain -----------------------------------------------
    empty = case("head == 0 is EMPTY, which is a state the client is really in",
                 run([], _chain_record(0))[0], HIST_EMPTY, 0)
    ok = empty["hist"] == [] and hist_is_complete(empty["hist_why"])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it counts as COMPLETE -- "
          f"0x00605F48/0x00605F4F arms a record as (1, 0) and "
          f"0x006060A2/0x006060A9 clears it as (0, 0), so calling a re-arm a "
          f"failure would manufacture a refusal on every one of them")

    # --- the refusals -----------------------------------------------------
    long_chain = _straight_chain(HIST_MAX_NODES + 3)
    trunc = case(f"a chain longer than N={HIST_MAX_NODES} is TRUNCATED, not ok",
                 run(long_chain, _chain_record(CHAIN_BLOCK + 4))[0],
                 "truncated:max-nodes", HIST_MAX_NODES)
    ok = (not hist_is_complete(trunc["hist_why"])
          and len(trunc["hist"] or []) == HIST_MAX_NODES)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the {len(trunc['hist'] or [])} nodes "
          f"it did read are kept while the reason says the walk is incomplete "
          f"-- the oldest vertex held is not the oldest there is, so \"no node "
          f"within the radius\" is not a conclusion this sample supports")

    # THE CEILING CASE USED TO PLANT ITS HEAD AT PTR_MAX, so it refused whatever
    # PTR_MAX was and could not tell 0xFFFF0000 from 0x7FFF0000 -- a check that
    # cannot fail. It now uses a FIXED literal above any plausible ceiling, and
    # the case under it walks a chain in the 2-4 GB band that a non-LARGE-
    # ADDRESS-AWARE bound would wrongly refuse.
    HIGH_BAD = 0xFFFFF000
    for what, head, nodes in (
            ("a head in the 64 KB null-guard region", 0x400,
             [(0x400, NOW, 0.0, 0.0, 0, 0, 0)]),
            (f"a head at 0x{HIGH_BAD:08X}, above any ceiling", HIGH_BAD,
             [(HIGH_BAD, NOW, 0.0, 0.0, 0, 0, 0)]),
            ("an unaligned head (nodes are block+4+i*0x2C, always 4-aligned)",
             CHAIN_BLOCK + 5, [(CHAIN_BLOCK + 5, NOW, 0.0, 0.0, 0, 0, 0)])):
        case(what, run(nodes, _chain_record(head))[0],
             "unread:node-pointer-implausible", 0)

    HIGH_OK = 0x90000000
    high = case(f"but a chain at 0x{HIGH_OK:08X} -- above the 2 GB line -- is "
                f"WALKED, not refused",
                run(_straight_chain(2, first=HIGH_OK),
                    _chain_record(HIGH_OK))[0], HIST_OK, 2)
    ok = high["hist"] and high["hist"][0]["addr"] == HIGH_OK
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it really read node 0 at "
          f"0x{HIGH_OK:08X} -- Gw.exe's COFF Characteristics carry "
          f"IMAGE_FILE_LARGE_ADDRESS_AWARE (section 5 reads the word), so a "
          f"0x7FFF0000 ceiling would silently refuse legitimate allocations "
          f"while every fixture that plants its head AT the constant stays "
          f"green. PTR_MAX is 0x{PTR_MAX:08X}")

    case("a node the reader cannot fetch",
         run([], _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-unreadable", 0)
    # THE OTHER HALF OF THAT REFUSAL, and it was unreachable until 2026-08-21.
    # `not blk` and `len(blk) < HIST_NODE_SPAN` are two conditions; every
    # fixture here could only produce the first. Dropping the length half and
    # zero-padding the buffer ran 206/206 green while fabricating a vertex at
    # (0, 0, 0, 0) with next=0 -- an `ok` chain that terminates on a node the
    # client never wrote.
    short = case(f"a node read that comes back SHORT (12 of "
                 f"{HIST_NODE_SPAN} bytes) is unreadable, not zero-padded",
                 run(_straight_chain(3), _chain_record(CHAIN_BLOCK + 4),
                     short={CHAIN_BLOCK + 4 + HIST_NODE_STRIDE: 12})[0],
                 "unread:node-unreadable", 1)
    ok = len(short["hist"] or []) == 1 and short["hist"][0]["t"] == 9000
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the node ABOVE the short read "
          f"survives ({short['hist_n']} of 3, t="
          f"{(short['hist'] or [{}])[0].get('t')}) -- a partial transfer is a "
          f"refusal, and a padded one would read as a real vertex at the origin")
    # The SECOND node fails: a partial walk must keep what it read and still
    # refuse, which is the case a blank-on-failure would silently zero.
    partial = _straight_chain(3)
    part = case("a node that fails PART WAY down keeps the nodes above it",
                run(partial[:1], _chain_record(CHAIN_BLOCK + 4))[0],
                "unread:node-unreadable", 1)
    ok = part["hist"] and part["hist"][0]["addr"] == CHAIN_BLOCK + 4
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and node 0 survives in the row "
          f"({part['hist_n']} of 3) -- a real measurement is not wiped by a "
          f"later failure, it is labelled by one")

    cyc = _straight_chain(2)
    cyc[1] = (cyc[1][0], cyc[1][1], 0.0, 0.0, 0, 0, cyc[0][0])
    case("a cycle terminates the walk instead of spinning",
         run(cyc, _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-revisited", 2)

    inv = _straight_chain(3)
    inv[1] = (inv[1][0], inv[0][1] + 1, 0.0, 0.0, 0, 0, inv[1][6])
    case("a node NEWER than the node linking to it is a torn read",
         run(inv, _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-time-inverted", 1)

    # THE RECYCLE HAZARD, MODELLED. A read of a parent's `next` that lands
    # before the client severs the block, with the target read landing after the
    # slot has been re-appended, yields ANOTHER AGENT'S node under our agent's
    # id -- the pool is shared and 0x00604CF9 resets only the block's count, so
    # the bytes are live rather than zeroed. The re-appended slot carries the
    # CURRENT world clock, which is newer than the stale parent that points at
    # it, so torn-read test 2 is what catches it. This is the only defence, and
    # it is a real one; the residual window is a re-append landing in the same
    # millisecond as the parent's own stamp, which this walk cannot see.
    # The parent was appended a second ago (t0 = NOW-1000, which is what a real
    # chain looks like); the slot below it has been re-appended just now and
    # carries a stranger's point.
    recyc = _straight_chain(3, t0=NOW - 1000)
    recyc[1] = (recyc[1][0], NOW, 500.0, 600.0, 4, 0, recyc[1][6])
    case("a node re-appended under the read (the recycle hazard) is caught as "
         "a torn read, not attributed to our agent",
         run(recyc, _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-time-inverted", 1)

    fut = _straight_chain(2)
    fut[0] = (fut[0][0], NOW + HIST_FUTURE_TOL_MS + 1, 0.0, 0.0, 0, 0,
              fut[0][6])
    case(f"a node dated more than {HIST_FUTURE_TOL_MS} ms into the future is a "
         f"torn read", run(fut, _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-time-future", 0)

    # AND THE TOLERANCE IS PINNED FROM BOTH SIDES. Its ground used to be named
    # as "world-0/world-1 clock skew" with a 40 ms control beside it -- a
    # control with no referent, because `sample()` and the appender read the
    # SAME world clock (0x00605893 / 0x006058A5 vs A_WORLD; see
    # HIST_FUTURE_TOL_MS). The real ground is read ordering: the clock is read
    # before the nodes, so an append in between is legitimately ahead. With the
    # case above and these two the constant cannot move without reddening.
    # AND TWO OF THE THREE ARE FIXED LITERALS, WHICH IS THE WHOLE POINT. The
    # first draft of this block wrote every case as `HIST_FUTURE_TOL_MS + 1` and
    # `HIST_FUTURE_TOL_MS - 1`, so all of them scaled WITH the constant and
    # widening 250 back to 2500 ran green -- the same self-referential defect
    # this section was written to close in the PTR_MAX case, reproduced inside
    # the fix for it. 40 and 400 do not move: together they pin the tolerance
    # into [40, 400), and only the boundary pair below is relative.
    for lag, want, n_want, why in (
            (40, HIST_OK, 2, "one reader-latency's worth of append lag"),
            (HIST_FUTURE_TOL_MS - 1, HIST_OK, 2, "and right up to the bound")):
        lagged = _straight_chain(2)
        lagged[0] = (lagged[0][0], NOW + lag, 0.0, 0.0, 0, 0, lagged[0][6])
        case(f"but {lag} ms ahead does NOT redden -- {why}",
             run(lagged, _chain_record(CHAIN_BLOCK + 4))[0], want, n_want)
    wide = _straight_chain(2)
    wide[0] = (wide[0][0], NOW + 400, 0.0, 0.0, 0, 0, wide[0][6])
    case("and a FIXED 400 ms ahead still refuses -- the bound is a sample "
         "latency, not the client's 2500 ms head-age rule it was borrowed from",
         run(wide, _chain_record(CHAIN_BLOCK + 4))[0],
         "unread:node-time-future", 0)

    # --- the mirror of section 6's rule -----------------------------------
    fails = [run(n, _chain_record(h))[0] for h, n in (
        (0x400, [(0x400, NOW, 0.0, 0.0, 0, 0, 0)]),
        (CHAIN_BLOCK + 4, []),
        (CHAIN_BLOCK + 4, cyc),
        (CHAIN_BLOCK + 4, inv),
        (CHAIN_BLOCK + 4, fut),
        (CHAIN_BLOCK + 4, long_chain))]
    ok = all(not hist_is_complete(f["hist_why"]) for f in fails)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] none of the {len(fails)} failure "
          f"modes reports a COMPLETE walk -- a short chain and a refused chain "
          f"are indistinguishable downstream unless the row says which, and "
          f"the refused one is exactly the shape that revives candidate B")
    ok = all(f["hist_why"].startswith(("unread:", "truncated:"))
             and set(f) == set(HIST_KEYS) for f in fails)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and each names its reason in the "
          f"`unread:`/`truncated:` vocabulary, with the full key set intact -- "
          f"never a silent null, never a missing field")

    # --- THE MODULE GLOBALS REALLY ARE RESOLVED IN THE BODY ----------------
    # `history_chain` takes `max_nodes=None, gate=None` and resolves both from
    # the module globals INSIDE the function. The commit that landed it said
    # the three section-17 controls in test_movesync depended on that; they do
    # not -- they pass both parameters explicitly and stayed green when the
    # defaults were moved back into the signature. This is the control that
    # actually proves it: rebind the global and call WITHOUT the argument, the
    # way an operator or a later control would.
    g = globals()
    keep = (g["HIST_MAX_NODES"], g["HIST_SEP_GATE"])
    try:
        g["HIST_MAX_NODES"] = 2
        read, _log = _chain_mem(_straight_chain(5), None, 3)
        bound = history_chain(read, _chain_record(CHAIN_BLOCK + 4), 400.0,
                              CHAIN_AGENT, AGENT, NOW)
        g["HIST_MAX_NODES"] = keep[0]
        g["HIST_SEP_GATE"] = 1.0e9
        read, _log = _chain_mem(_straight_chain(3), None, 3)
        shut = history_chain(read, _chain_record(CHAIN_BLOCK + 4), 400.0,
                             CHAIN_AGENT, AGENT, NOW)
    finally:
        g["HIST_MAX_NODES"], g["HIST_SEP_GATE"] = keep
    ok = (bound["hist_why"] == "truncated:max-nodes" and bound["hist_n"] == 2
          and shut["hist_why"] == "not-attempted:below-gate")
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] both bounds are read from the "
          f"MODULE at call time, not bound at import: with HIST_MAX_NODES "
          f"moved to 2 a 5-node chain is {bound['hist_why']} at n="
          f"{bound['hist_n']}, and with HIST_SEP_GATE moved to 1e9 a 400 u "
          f"sample is {shut['hist_why']} -- as signature defaults both moves "
          f"are silently ignored, which is a control that appears to work")
    ok = (HIST_MAX_NODES, HIST_SEP_GATE) == keep
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and the control RESTORED them "
          f"({HIST_MAX_NODES}, {HIST_SEP_GATE:.0f}) -- a fixture that leaks a "
          f"rebound global turns every later section into a different test")

    # --- THE READ BUDGET THE WHOLE GATE ARGUMENT IS PRICED IN -------------
    ok = (HIST_NODE_SPAN == N_POINT + 16 and HIST_NODE_SPAN <= HIST_NODE_STRIDE
          and HIST_NODE_SPAN == 0x18)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] HIST_NODE_SPAN is "
          f"0x{HIST_NODE_SPAN:X} = N_POINT + 16, the last dword this walk "
          f"reads, and fits inside the 0x{HIST_NODE_STRIDE:X} stride -- it is "
          f"OUR budget rather than a client constant, so no fence byte anchors "
          f"it and both fixtures size themselves FROM it; widening it costs "
          f"every node read and nothing else would notice")

    # --- THE REPORT ITSELF, READ BACK OUT OF STDOUT -----------------------
    # The section-9 wiring rows ask whether main() CALLS print_hist_summary.
    # That is not the same as its printing anything: gutting the body to a bare
    # `return`, and separately deleting the refusal warning, both ran 206/206
    # green. This is movesync's `_selftest_print_fence` idiom -- capture the
    # real output and require the numbers a reader acts on to be in it.
    tally = {"not-attempted:below-gate": 60, HIST_OK: 25,
             "truncated:max-nodes": 9, "unread:node-time-inverted": 6}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_hist_summary(tally, 240, 100)
    text = buf.getvalue()
    ok = ("walked on 40 of 100" in text and "40.0%" in text
          and "25 complete" in text and "2.40 per sample" in text)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] print_hist_summary prints the "
          f"denominator: 40 of 100 walked, 25 complete, 2.40 reads/sample "
          f"-- attempted EXCLUDES `not-attempted:*` and complete excludes the "
          f"truncation, so the three numbers are all different by construction")
    present = [w for w in tally if w in text]
    ok = (len(present) == len(tally)
          and all(f"{100.0 * c / 100:5.1f}%" in text for c in tally.values()))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and every reason in the vocabulary "
          f"gets its own row with its own share ({len(present)} of "
          f"{len(tally)} present) -- the shares are over n, not over the "
          f"attempted subset, and all four differ")
    ok = ("6 refusal(s) and 9 truncation(s)" in text
          and "Do not pool them" in text)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the REFUSAL WARNING fires with "
          f"its own counts -- \"6 refusal(s) and 9 truncation(s) ... Do not "
          f"pool them\". Deleting that sentence is what turns a refused walk "
          f"into \"no node near q\", which is the reading candidate B lives on")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_hist_summary({HIST_OK: 5}, 40, 5)
    clean = buf.getvalue()
    ok = "Do not pool them" not in clean and "walked on 5 of 5" in clean
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it does NOT fire on a run "
          f"with nothing refused -- a warning that always prints is not a "
          f"warning, it is a footer")

    # --- AND main()'s TWO Hz FIGURES, WHICH ARE ALSO OUTPUT-ONLY ----------
    line = chain_cost_line((13.1, 6.9), 40)
    ok = ("13.1 Hz" in line and "6.9 Hz" in line and "-47%" in line
          and f"sep > {HIST_SEP_GATE:.0f} u" in line and "2 x 40" in line)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] chain_cost_line prints BOTH "
          f"figures and the delta: {line[:78]}... -- a mutation that kept the "
          f"`chain_cost` call, discarded the result and printed nothing ran "
          f"green against the wiring row, which judges the CALL")
    none_line = chain_cost_line(None, 40)
    ok = "UNMEASURED" in none_line
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a run that could not price it "
          f"says UNMEASURED rather than printing nothing -- a missing line "
          f"reads as a run that did not need one")

    # --- THE COST, MEASURED THROUGH `sample()` ITSELF ---------------------
    # REALFIX.md section 2.4 argues the gate from "a full sample is ~20
    # ReadProcessMemory calls; 8 unconditional node reads is ~+40%". The first
    # half of that was never measured. This drives the REAL `sample()` over a
    # whole-sample fake memory and counts the reads, with the gate at its
    # shipped value and with it forced open -- so the multiplier is a number
    # this file produces rather than one a comment asserts. (The Hz cost is a
    # different quantity, needs a client, and is what `chain_cost()` measures
    # before every run for main() to print.)
    full = _straight_chain(HIST_MAX_NODES)
    sync = _fake_agent(7, plane=0, point=(0.0, 0.0))
    # The ONLY difference between the two runs is where the ASYNC twin stands:
    # 100 u apart is below the gate, 4,000 u apart is above it. Same code path,
    # same shipped gate, no flag -- so the delta is the chain walk and nothing
    # else. Forcing the gate open instead would measure a configuration the run
    # never uses.
    costs = {}
    old_read = keytap.read_handle
    try:
        for label, dx in (("below", 100.0), ("above", 4000.0)):
            rd, count = _sample_mem(_chain_record(full[0][0]), full, sync,
                                    _fake_agent(7, plane=3, point=(dx, 0.0)))
            keytap.read_handle = lambda _h, a, n, _rd=rd: _rd(a, n)
            s = sample(None, CHAIN_AGBASE, CHAIN_SYNC_PTR, 7)
            costs[label] = (count[0], None if s is None else s["hist_why"])
    finally:
        keytap.read_handle = old_read
    base_n, base_why = costs["below"]
    full_n, full_why = costs["above"]
    ok = (base_why == "not-attempted:below-gate" and full_why == HIST_OK
          and base_n > 0 and full_n == base_n + HIST_MAX_NODES + 1)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] MEASURED through sample(): a "
          f"below-gate sample costs {base_n} read(s) ({base_why}) and one that "
          f"walks a full {HIST_MAX_NODES}-node chain costs {full_n} "
          f"({full_why}), +{full_n - base_n} = "
          f"+{100.0 * (full_n - base_n) / max(base_n, 1):.0f}% -- REALFIX.md "
          f"2.4's \"+40%\" assumed a ~20-read sample; sample() issues "
          f"{base_n}, so an UNGATED walk would roughly DOUBLE it. That makes "
          f"the gate MORE load-bearing than the design note argued, not less")

    # A stub that only ever refused would pass every check above, which is the
    # defect section 6 records from the other side.
    tail = (good["hist"] or [{}])[-1].get("t")
    ok = (good["hist_why"] == HIST_OK and good["hist_n"] == 4
          and tail == 9000 - 3 * 300)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the healthy walk really did "
          f"produce {good['hist_n']} nodes ending at t={tail} "
          f"-- a parser that refused everything would pass all the refusals")
    return bad, ran


def _selftest_r5():
    """14. CANCELWALK-R5's fields: decoded from the right bytes, on BOTH copies,
    and blanked rather than stale when the twin read refuses."""
    print("\n14. CANCELWALK-R5: the walk-start footprint, both copies (H5/H7)")
    bad = ran = 0

    # THE OFFSETS, ASKED OF THE BYTES. Every value distinct and none of them
    # zero, so a decode that read a neighbouring dword names itself. This is
    # the check that would catch A_REQ_TOKEN pointing at 0x54 -- the failure
    # mode section 5's comment describes for the fence constants, in the one
    # place R5's verdict actually rests.
    blk = _fake_agent(7, reqtoken=0x1234ABCD, direction=(0.25, -0.75),
                      point=(11.5, -22.25), vel=(3.5, -4.25), stop=4242)
    got = _r5_fields(blk)
    for key, want in (("reqtoken", 0x1234ABCD), ("dir", [0.25, -0.75]),
                      ("stop", 4242), ("point_raw", [11.5, -22.25]),
                      ("vel_raw", [3.5, -4.25])):
        ok = got[key] == want
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] {key:10} decodes to {want} "
              f"(got {got[key]}) -- distinct non-zero values, so reading a "
              f"neighbouring dword cannot pass")

    # THE OFFSETS THEMSELVES, against the fields they must not collide with.
    ok = (A_REQ_TOKEN == 0x50 and A_DIR == 0xBC
          and A_REQ_TOKEN + 4 <= A_UPDATED and A_DIR + 8 <= A_MODE
          and A_DIR + 8 <= AGENT_SPAN)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] A_REQ_TOKEN {A_REQ_TOKEN:#x} and "
          f"A_DIR {A_DIR:#x} sit where the client writes them and inside the "
          f"span already fetched -- R5 adds NO cross-process read")

    # BOTH COPIES, and the prefix really lands on the twin. A version that
    # decoded the sync block twice would look identical in one row and be
    # useless for the only question R5 asks.
    ARRAY, AG, ASYNC = 0x0A000000, 0x10000000, 0x0B000000
    sync_blk = _fake_agent(7, reqtoken=1, direction=(1.0, 0.0),
                           point=(100.0, 0.0))
    async_blk = _fake_agent(7, world=1, reqtoken=2, direction=(0.0, 1.0),
                            point=(200.0, 0.0))

    def read(addr, n):
        if addr == AG + OFF_WORLD_CLOCK:
            b = bytearray(GATE1_HDR_SPAN)
            struct.pack_into("<I", b, OFF_ASYNC_ARRAY - OFF_WORLD_CLOCK, ARRAY)
            struct.pack_into("<I", b, OFF_ASYNC_COUNT - OFF_WORLD_CLOCK, 64)
            return bytes(b[:n])
        if addr == ARRAY + 7 * 4:
            return struct.pack("<I", ASYNC)
        if addr == ASYNC:
            return async_blk[:n]
        return None

    g1 = gate1_read(read, AG, 7, sync_blk)
    ok = (g1.get("async_reqtoken") == 2 and g1.get("async_dir") == [0.0, 1.0]
          and g1.get("async_point_raw") == [200.0, 0.0])
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] gate1_read surfaces the ASYNC "
          f"copy's own values (reqtoken={g1.get('async_reqtoken')}, "
          f"dir={g1.get('async_dir')}) -- not a second decode of the sync "
          f"block, which is the one substitution that would void the run")

    # A REFUSED TWIN BLANKS THEM. Same rule the rest of gate1_read obeys: last
    # row's numbers standing in a refused row is how a frozen press would get
    # scored from stale bytes.
    blanked = gate1_read(lambda a, n: None, AG, 7, sync_blk)
    ok = (all(blanked.get("async_" + k) is None for k in R5_KEYS)
          and blanked["gate1"].startswith("unread:"))
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a refused twin read blanks every "
          f"async R5 key rather than leaving the previous row's numbers "
          f"standing ({blanked['gate1']})")

    # AND sample() MUST CARRY THEM. The floor comment's own lesson: eight blank
    # keys spliced from nowhere look identical in the file to eight real ones,
    # so this asks the syntax tree that sample() calls the decoder rather than
    # trusting that the keys appear.
    import ast
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    fn = next(f for f in ast.walk(ast.parse(src))
              if isinstance(f, ast.FunctionDef) and f.name == "sample")
    calls = {n.func.id for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ok = "_r5_fields" in calls
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] sample() CALLS _r5_fields for the "
          f"sync copy -- keys typed out by hand would drift from the decoder "
          f"the async side uses")

    # --- CANCELWALK-R7's controller operands, polled not trapped ------------
    # The two fields the walk-start applier gates on, reached from the SAME
    # ctx resolve() already returns. Driven over a fake memory here, because
    # the whole point of these being POLLABLE is that no debugger is needed.
    CTX, CCTX, CTRL = 0x0C000000, 0x0D000000, 0x0E000000

    def ctrl_mem(status, flag, ctrl_ptr=CTRL):
        def read(addr, n):
            if addr == CTX + OFF_CTRL_CTX:
                return struct.pack("<I", CCTX)
            if addr == CCTX + OFF_PLAYER_CONTROLLED:
                return struct.pack("<I", ctrl_ptr)
            if addr == ctrl_ptr + CTRL_STATUS:
                return struct.pack("<I", status)
            if addr == ctrl_ptr + CTRL_FLAGBYTE:
                return bytes([flag])
            return None
        return read

    for status, flag, wa, wb, wc in ((0, 0, False, False, False),
                                     (CTRL_BIT_A, 0, True, False, False),
                                     (0, CTRL_BIT_B, False, True, False),
                                     (CTRL_BIT_C, 0, False, False, True),
                                     (CTRL_BIT_A | CTRL_BIT_C, CTRL_BIT_B,
                                      True, True, True)):
        r = controller_read(ctrl_mem(status, flag), CTX)
        ok = (r["gate_a"] == wa and r["gate_b"] == wb and r["gate_c"] == wc
              and r["walk_suppressed"] == (wa or wb or wc)
              and r["ctrl_why"] == "ok" and r["ctrl_ptr"] == CTRL)
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] controller status={status:#05x} "
              f"flag={flag:#04x} -> A={r['gate_a']} B={r['gate_b']} "
              f"C={r['gate_c']} suppressed={r['walk_suppressed']}")

    # EVERY REFUSAL NAMED, and none of them reading as "no gate set" -- that
    # value is exactly what the arc's primary hypothesis predicts, so a failed
    # read that returned it would manufacture the finding.
    for why, read, ctx_arg in (
            ("no-ctx", ctrl_mem(0, 0), 0),
            ("ctrl-ctx-unreadable", lambda a, n: None, CTX),
            ("controller-null", ctrl_mem(0, 0, ctrl_ptr=0), CTX),
            ("operands-unreadable",
             lambda a, n: (struct.pack("<I", CCTX) if a == CTX + OFF_CTRL_CTX
                           else struct.pack("<I", CTRL)
                           if a == CCTX + OFF_PLAYER_CONTROLLED else None),
             CTX)):
        r = controller_read(read, ctx_arg)
        ok = (r["ctrl_why"] == why and r["gate_a"] is None
              and r["walk_suppressed"] is None)
        bad += not ok
        ran += 1
        print(f"   [{'PASS' if ok else 'FAIL'}] a {why} read names itself and "
              f"leaves every gate None -- never False, which is the value the "
              f"hypothesis predicts", )

    ok = "controller_read(rd, ctx)" in src
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] sample() CALLS controller_read -- "
          f"eight blank ctrl_* keys spliced from nowhere look identical in the "
          f"file, the same defect this section already caught once")
    return bad, ran


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


def chain_cost(handle, agbase, ptr, aid=None, reads=40):
    """REALFIX-I1's price, MEASURED on this machine rather than predicted.

    -> (hz_gated, hz_forced) or None. The first is the run's real configuration
    (the chain read only above HIST_SEP_GATE); the second forces the walk on
    every sample by dropping the gate below zero, which is the worst case the
    design note argued against (~+40% of reads, ~13 Hz -> ~7 Hz predicted).

    Two passes rather than an arithmetic estimate because the prediction is the
    thing being checked: 8 node reads is ~+40% of a ~20-read sample ONLY if a
    node read costs what an agent-block read costs, and nothing had measured
    that. REALFIX.md section 2.4 asks for the impact to be measured and printed,
    not asserted.
    """
    out = []
    for gate in (HIST_SEP_GATE, -1.0):
        t0 = time.perf_counter()
        got = 0
        for _ in range(reads):
            if sample(handle, agbase, ptr, aid, hist_gate=gate) is not None:
                got += 1
        dt = time.perf_counter() - t0
        if dt <= 0 or got == 0:
            return None
        out.append(got / dt)
    return tuple(out)


def chain_cost_line(cost, reads):
    """The two Hz figures as ONE string, so the OUTPUT can be pinned offline.

    WHY THIS IS A FUNCTION. The wiring table in section 9 asks the syntax tree
    whether `main()` CALLS `chain_cost` -- and that is all it ever asked. A
    mutation that kept the call, threw the result away and printed neither
    figure ran green at 206/206, which makes the wiring row's claim ("so the
    chain walk's OUTPUT cannot vanish") false as written: it keeps the CALL from
    vanishing. Moving the text here lets section 13 read the string back and
    lets section 9 require the call to be an argument of a `print`, so both
    halves are held. REALFIX.md 2.4 asks for the impact to be measured AND
    printed; a measured number nobody prints is the assumption it replaced.
    """
    if cost is None:
        return ("could not price the REALFIX-I1 chain walk (no sample "
                "completed); its cost is UNMEASURED for this run")
    gated, forced = cost
    return (f"REALFIX-I1 chain walk: {gated:.1f} Hz gated at "
            f"sep > {HIST_SEP_GATE:.0f} u vs {forced:.1f} Hz forced on every "
            f"sample ({100.0 * (forced - gated) / max(gated, 1e-9):+.0f}% Hz "
            f"if the gate were removed, {HIST_MAX_NODES} nodes max) -- measured "
            f"here, 2 x {reads} samples. The read count behind it is pinned "
            f"offline by movetap's section 13: 8 reads below the gate, 17 for "
            f"a full walk")


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
    # THE SEQUENCE, not just the tally. Run lengths and the flip denominator are
    # both properties of the ORDER, and neither can be recovered from counts --
    # which is why this file could report a 92.4% share with an effective n of
    # about 4 and print only the 564. One tuple per POLL, not per sample: a poll
    # that produced no row still appends its marker, so `len(seq) >= n` and the
    # gap is visible. Reading `pairs` against `n - 1` would therefore be wrong
    # in the other direction now; read it against `len(seq) - 1`.
    seq = []
    g1 = {}                    # gate1 -> count, including its unread values
    g1why = {}                 # why an `undecided` was undecided
    early_a = {}               # early_out_a -> count: True / False / "unread:*"
    point_bad = {}             # point_invalid -> count, same three-valued domain
    hist_why = {}              # REALFIX-I1: hist_why -> count, every value
    hist_reads = 0             # and what the walk actually spent, in reads
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
            # REALFIX-I1's price on THIS machine, printed before the run so a
            # reader can see what the chain walk cost the residual budget.
            CAL_READS = 40
            cost = chain_cost(handle, agbase, ptr, aid, reads=CAL_READS)
            print(chain_cost_line(cost, CAL_READS))
            print(f"polling agent {aid} at {a.hz:.0f} Hz for {a.seconds:.0f}s "
                  f"-> {out}\n")
            while time.time() < t_end:
                # A POLL THAT PRODUCED NO ROW STILL LEAVES A MARK IN `seq`.
                # These two `continue`s used to append nothing, so a stalled
                # resolve or a short agent block put a hole in the wall clock
                # that the sequence could not see: `count_flips` then called the
                # samples either side of it an adjacent pair and `episodes`
                # merged the runs across it, with `censored=False` and
                # `split=False`. See REACH_DROPPED. Not counted into `reach` or
                # `n` -- a poll that produced no sample is not a sample.
                try:
                    _ctx, agbase, aid, ptr = resolve(pid, handle, base)
                except TapFail:
                    seq.append((round(time.time(), 4), REACH_UNRESOLVED))
                    time.sleep(period)
                    continue
                s = sample(handle, agbase, ptr, aid, ctx=_ctx)
                if s is None:
                    seq.append((round(time.time(), 4), REACH_DROPPED))
                    time.sleep(period)
                    continue
                s["kind"] = "sample"
                s["t"] = round(time.time(), 4)
                s["agent"] = aid
                fh.write(json.dumps(s) + "\n")
                n += 1
                reach[s["gate_reach"]] = reach.get(s["gate_reach"], 0) + 1
                seq.append((s["t"], s["gate_reach"]))
                g1[s["gate1"]] = g1.get(s["gate1"], 0) + 1
                if s["gate1_why"]:
                    g1why[s["gate1_why"]] = g1why.get(s["gate1_why"], 0) + 1
                early_a[s["early_out_a"]] = early_a.get(s["early_out_a"], 0) + 1
                hist_why[s["hist_why"]] = hist_why.get(s["hist_why"], 0) + 1
                hist_reads += s["hist_reads"]
                point_bad[s["point_invalid"]] = point_bad.get(
                    s["point_invalid"], 0) + 1
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
                # The COUNT is not accumulated here: `count_flips` scores the
                # whole sequence at the end under C3's rule (both ends real, and
                # world1 <-> shut is not a fence change). A running counter here
                # would be a second, laxer definition of the same statistic.
                if last is not None and s["gate_reach"] != last["gate_reach"]:
                    print(f"  fence {last['gate_reach']} -> {s['gate_reach']} "
                          f"(raw {last['fence_raw']!r} -> {s['fence_raw']!r}, "
                          f"armed {s['agtrack_armed']!r}) at "
                          f"t+{time.time() - t_start:.2f}s"
                          + ("" if reach_is_real(s["gate_reach"])
                             and reach_is_real(last["gate_reach"])
                             else "   [NOT a counted flip: a read failed]"))
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
    print_hist_summary(hist_why, hist_reads, n)
    flips, pairs = count_flips(seq)
    # Both lanes run, and both verdicts print, whichever of them refuses. A
    # gate-1 lane that could not read the twin says nothing about the fence, and
    # a refused fence share says nothing about gate 1's operands.
    rc = fence_verdict(reach, flips, pairs, n, rate, seq)
    return max(rc, gate1_verdict(g1, g1why, early_a, point_bad, n))


def print_hist_summary(hist_why, hist_reads, n, indent="  "):
    """REALFIX-I1's own report: how often the walk ran, and what it cost.

    NOT a verdict. The chain walk is an instrument for the offline adjudication
    in REALFIX-L2 section 2.4, so there is no bar it can fail here -- what this
    prints is the denominator every later claim about the polyline rests on,
    and the share of samples where the walk was REFUSED rather than short. A
    reader who takes "no node within the radius" from a run whose chain reads
    were 40% `unread:*` would be reading the reader, not the client.
    """
    if not n:
        print(f"{indent}REALFIX-I1: no samples, so no chain was walked.")
        return
    attempted = sum(c for w, c in hist_why.items()
                    if not w.startswith("not-attempted:"))
    complete = sum(c for w, c in hist_why.items() if hist_is_complete(w))
    print(f"{indent}REALFIX-I1 history chain: walked on {attempted} of {n} "
          f"sample(s) ({100.0 * attempted / n:.1f}%, gated at "
          f"sep > {HIST_SEP_GATE:.0f} u), {complete} complete, "
          f"{hist_reads} extra read(s) = {hist_reads / n:.2f} per sample")
    for why, c in sorted(hist_why.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{indent}  {why:34} {c:6}  {100.0 * c / n:5.1f}%")
    refused = sum(c for w, c in hist_why.items() if w.startswith("unread:"))
    trunc = hist_why.get("truncated:max-nodes", 0)
    if refused or trunc:
        print(f"{indent}  ^ {refused} refusal(s) and {trunc} truncation(s): "
              f"neither supports \"no node near q\", which is the reading "
              f"candidate B is revived by. Do not pool them with the "
              f"complete walks.")


def count_flips(seq):
    """(flips, usable_pairs) over the gate_reach sequence. Never counts a flake.

    A FLIP IS COUNTED ONLY WHEN BOTH SAMPLES OF A CONSECUTIVE PAIR ARE REAL.
    Until 2026-08-20 this was `s != last` over every sample, and `real -> unread
    -> real` therefore scored TWO transitions against a denominator of `n`. A
    10% flaky read manufactures ~0.20 flips/sample that way -- 80% of the
    escalation bar -- while sitting under the 25% unread refusal that is
    supposed to catch a bad read. The printed consequence of tripping that bar
    is "THIS is the outcome that earns the hook", so the direction of the error
    was an evening spent writing a hook DLL for a bad read.

    AND `world1` <-> `shut` IS NOT A FLIP. Both mean the test would not run, so
    the transition is a world-index change, not a fence change. The flip count
    and the open share `p` must be about the SAME two-state signal or the ratio
    between them is meaningless: both are computed over `test_would_run`.
    """
    flips = pairs = 0
    prev = None
    for _t, g in seq:
        real = reach_is_real(g)
        if real and prev is not None:
            pairs += 1
            if test_would_run(g) != test_would_run(prev):
                flips += 1
        # An unread sample breaks the chain in BOTH directions: neither the pair
        # before it nor the pair after it has two real ends.
        prev = g if real else None
    return flips, pairs


def episodes(seq):
    """Contiguous runs of one gate_reach value, each with how it was bounded.

    Returns [{state, length, start, end, censored, split}] in order.

    CENSORED means a run touches the first or last sample of the capture, so it
    has no measured start or no measured end and its length is a LOWER BOUND.
    At a 30-40 s block with the fence hypothesis true, every run is censored at
    both ends -- which is why "median shut-run >= 5 s" was unfalsifiable at this
    block length and was replaced by the episode count.

    SPLIT means a run is bounded by an `unread:` sample rather than by a state
    change. A flaky read cuts one true episode into two, so the episode count is
    an UPPER bound whenever this is non-zero. Same defect as the flip
    denominator, from the other side.
    """
    runs = []
    for i, (_t, g) in enumerate(seq):
        if runs and runs[-1]["state"] == g:
            runs[-1]["end"] = i
            runs[-1]["length"] += 1
        else:
            runs.append({"state": g, "start": i, "end": i, "length": 1})
    last = len(seq) - 1
    for r in runs:
        before = seq[r["start"] - 1][1] if r["start"] > 0 else None
        after = seq[r["end"] + 1][1] if r["end"] < last else None
        r["censored"] = r["start"] == 0 or r["end"] == last
        r["split"] = bool(reach_is_real(r["state"])
                          and ((before is not None and not reach_is_real(before))
                               or (after is not None and not reach_is_real(after))))
    return runs


def print_episodes(seq, rate=None):
    """C2. Run lengths per state -- and the effective n is EPISODES, not samples.

    A 92.4% share over 564 samples with 3 transitions has an effective n of
    about 4. This file printed the 564 and not the 4, and the prediction this
    whole probe is scored against is stated in run lengths.

    THE SECONDS AXIS IS DERIVED FROM `seq`'s OWN TIMESTAMPS. It came from
    main()'s `rate` until 2026-08-20 and was wrong TWICE, both times in the
    direction that OVER-states dwell -- which is the direction that makes an
    aliased fence look resolvable, i.e. the direction that would have retired
    the hook route on a number the instrument invented.

      (1) `k / hz` charges a k-sample run k intervals when k samples SPAN k - 1.
          A two-sample run therefore printed 2.00x its measured span, and a
          one-sample run printed 0.096 s against a measured span of 0.000 s --
          precisely the runs the Nyquist bar calls unresolved.
      (2) `rate` is main()'s `n / elapsed` in SAMPLES per second, while a run
          length is in POLLS, and since C5 `seq` carries the drop markers, which
          are in neither `n` nor `reach`. Measured on synthetic 1,000-poll
          captures at 10.00 Hz carrying a planted 100-poll run whose true span
          is 9.90 s, n = 32 seeds per cell: at a 20% drop rate the old axis
          printed 12.23 +/- 0.17 s (1.23x), at 30% 13.73 +/- 0.28 s (1.39x).
          The per-sample timestamps that give the right answer were already in
          the tuples and were thrown away.

    `rate` survives as an argument only to be printed BESIDE the poll rate: the
    gap between the two is the share of polls that produced no row, which is a
    number worth seeing next to the dwells it used to corrupt.
    """
    if not seq:
        print("  EPISODES: not computed -- no gate_reach sequence was passed. "
              "This section measured nothing rather than measuring zero.")
        return
    runs = episodes(seq)
    # THE POLL RATE, measured from the sequence itself. `seq` is one tuple per
    # POLL -- a poll that produced no row still appends its marker -- so this is
    # the rate the run lengths below are actually counted in.
    span = seq[-1][0] - seq[0][0] if len(seq) > 1 else 0.0
    hz = (len(seq) - 1) / span if span > 0 else None

    def secs(k):
        # k samples SPAN k - 1 poll intervals. A one-sample run reads 0.00 s
        # because its measured span really is zero; the true dwell is bounded
        # BELOW by this and never above, so every number here is a lower bound
        # and the instrument cannot flatter itself with it.
        return f"{(k - 1) / hz:.2f} s" if hz else "unrated"

    print("  EPISODES (this is the effective n, not the sample count):")
    if hz is None:
        print("    poll rate: UNRATED -- the sequence carries no measured span, "
              "so every dwell below is in samples only.")
    else:
        print(f"    poll rate {hz:.2f} Hz over {span:.2f} s, from the "
              f"sequence's own timestamps and NOT from the sample rate"
              + ("." if rate is None else
                 f"; the sample rate is {rate:.2f} Hz and the gap between the "
                 f"two is the share of polls that produced no row."))
    for state in sorted({r["state"] for r in runs},
                        key=lambda s: -sum(r["length"] for r in runs
                                           if r["state"] == s)):
        mine = [r for r in runs if r["state"] == state]
        lens = sorted(r["length"] for r in mine)
        cens = sum(1 for r in mine if r["censored"])
        split = sum(1 for r in mine if r["split"])
        lo = lens[0]
        # THE MEDIAN REFUSAL. A median over runs that mostly have no measured
        # start or end is a statement about the block length, not the fence.
        if cens * 2 > len(mine):
            med = (f"median REFUSED ({cens} of {len(mine)} runs censored by the "
                   f"capture boundary)")
        else:
            m = statistics.median(lens)
            med = f"median {m:g} samples ({secs(m)})"
        print(f"    {state:24} {len(mine):3d} run(s), {med}, "
              f"min {lo} ({secs(lo)}"
              + (", a LOWER BOUND -- censored" if all(r["censored"] for r in mine
                                                      if r["length"] == lo)
                 else "")
              + f"), {cens} censored"
              + (f", {split} split by an unread sample -- the run count is an "
                 f"UPPER bound" if split else ""))
    real = [r for r in runs if reach_is_real(r["state"])]
    print(f"    effective n = {len(real)} episode(s) of real state over "
          f"{sum(r['length'] for r in real)} real sample(s). QUOTE THE EPISODES.")
    # THE NYQUIST BAR, printed with the result rather than left in a doc.
    short = sorted({r["state"] for r in runs if r["length"] <= 2})
    # The two thresholds are true-DWELL durations, not measured spans: a dwell
    # has to last 2 poll intervals to be sure of landing 2 samples in it, so
    # these stay `2.0 / hz` and `5.0 / hz` while `secs()` uses k - 1. Two
    # different quantities, deliberately.
    bar = ("a run of 1-2 samples is UNRESOLVED, not short"
           if hz is None else
           f"two samples per half-cycle at {hz:.2f} Hz means this reader can "
           f"only DETECT alternation whose every dwell exceeds "
           f"{2.0 / hz:.2f} s, and can only CHARACTERISE one above "
           f"{5.0 / hz:.2f} s")
    print(f"    Nyquist bar: {bar}.")
    if short:
        print(f"    UNRESOLVED: {', '.join(short)} each show a run of <= 2 "
              f"samples. That is not a short dwell, it is a dwell this "
              f"instrument cannot see the bottom of.")


def fence_verdict(reach, flips, pairs, n, rate, seq=()):
    """Print what the fence did, and REFUSE a percentage over a bad denominator.

    Separate from main() so `--selftest` can prove it goes red: a summariser
    that only ever prints is one nobody can tell is working.

    `pairs` is the count of consecutive sample pairs whose BOTH ends were real
    (`count_flips`), and it is the denominator `flips` is scored against. It
    used to be `n - 1` computed in here, which counted every flake twice.
    """
    print("\nTHE FENCE ON 0x006055E0 (clientControlled, AgTrack record+0x00) -- "
          "a COUNTERFACTUAL\nlabel on a state read, NOT an observation that the "
          "caller ran. Nothing here sees\n0x00605FC0 execute; each value names "
          "the branch it WOULD take on this state:")
    if not reach:
        print("  no sample carried a gate_reach at all. This run says NOTHING "
              "about the fence.")
        return 1
    unread = sum(c for k, c in reach.items() if k.startswith("unread:"))
    for k, c in sorted(reach.items(), key=lambda kv: -kv[1]):
        print(f"  {k:34} {c:6d}  {100.0 * c / n:5.1f}%")
    # C2. The shares above are over SAMPLES; the effective n is episodes, and
    # this prints before the refusals on purpose -- a run whose shares are
    # refused still has a run-length structure worth reading, and a failed
    # control must not void what it was not measuring.
    print_episodes(seq, rate)
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
    # `pairs` ARRIVES FROM count_flips AND IS NOT `n - 1`. It counts only the
    # consecutive pairs whose two ends were both real reads, so a flaky read can
    # no longer manufacture flips against a denominator that never noticed. Its
    # distance below `len(seq) - 1` is the flake rate PLUS the dropped-sample
    # rate -- not below `n - 1`, because a dropped sample is in `seq` (as
    # `unread:sample-dropped`) and is not in `n` at all. Read `pairs` against the
    # sequence length, never against the sample count, before escalating on a
    # high A.
    #
    # BOTH HALVES OF THE RATIO ARE OVER THE SAME POPULATION, and this line is
    # the one that got it wrong. `phi` is flips over REAL pairs (C3); `p_open`
    # was left over `n`, which includes the unread samples that can never be in
    # the numerator. That is not the conservative direction -- it is only
    # conservative for p < 0.5. Deflating p pushes 2p(1-p) TOWARD its maximum
    # when p > 0.5, inflating the denominator of A and shrinking A: measured
    # here over n = 8 seeds x 1,000 samples, a truly aliased fence at a 92.5%
    # open share (independent Bernoulli per sample) seen through a 20% flaky
    # read gave A = 0.33-0.41 and refused 0/8 with the split denominator,
    # against A = 0.97-1.12 and 8/8 with this one -- while printing the share
    # as 73% rather than 92%, so both halves of the sentence were wrong. A
    # p_open above 0.5 is exactly where C1's own calibration set lives (the
    # 185/15 and 300/30 ms cells, p = 0.925 and 0.909), and 20% unread sits
    # under the 25% refusal above and inside the failure table's expected
    # operating band -- so the hole was open in the band the hypothesis lives in
    # for the second time.
    # "Open" is the share where the test would RUN -- `test-runs` alone. world1
    # is NOT open: world == 1 is the branch on which the caller skips the test
    # entirely. An earlier draft of this line added it and would have inflated
    # p, deflating A toward "not aliased" -- the wrong direction for a guard.
    p_open = reach.get(REACH_TEST_RUNS, 0) / max(1, n - unread)
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


def gate1_verdict(g1, g1why, early_a, point_bad, n):
    """C6/C7/C8's summary, with the same denominator refusal as the fence.

    RETURNS 1 ON A REFUSAL, AND THAT DOES NOT VOID THE FENCE. The fence verdict
    is printed above this and stands on its own denominator; this lane failing
    means the gate-1 question went unmeasured, not that the run did. The text
    says so, because an exit code is read as a verdict on everything.
    """
    print("\nGATE 1 (0x006057E1) ON ITS OWN OPERANDS -- the SYNC agent against "
          "its ASYNC\ntwin, each dated to the clock the client dates it to and "
          "each clamped the way\n0x005FF820 clamps. NOT a wire proxy:")
    if not g1:
        print("  no sample carried a gate1 at all. This run says NOTHING about "
              "gate 1. The fence verdict above is unaffected.")
        return 1
    unread = sum(c for k, c in g1.items() if str(k).startswith("unread:"))
    for k, c in sorted(g1.items(), key=lambda kv: -kv[1]):
        why = ""
        if k == GATE1_UNDECIDED and g1why:
            why = "  (" + ", ".join(f"{w} {c2}" for w, c2 in
                                    sorted(g1why.items())) + ")"
        print(f"  {str(k):34} {c:6d}  {100.0 * c / n:5.1f}%{why}")
    print(f"  the {GATE1_CUT - GATE1_BAND:.0f}-{GATE1_CUT + GATE1_BAND:.0f} u "
          f"band is REFUSED rather than classified: the client's sqrt at "
          f"0x0046E870\n  is a LUT approximation biased high, so the effective "
          f"cut is 299.3326 and this\n  reader cannot resolve the step. A "
          f"plane mismatch is refused too -- 0x00709990\n  takes a different "
          f"path there and it is not decoded.")

    print("\nTHE TWO EARLY-OUTS ABOVE GATE 1 (each returns 1 = NO SNAP before "
          "gate 1 is\nreached, and each presents on a capture as \"above the "
          "cut and nothing snapped\"):")
    for label, tally in (("early_out_a (+0x48 != 0 && +0xC4 == 9)", early_a),
                         ("point_invalid (m_point == +inf)", point_bad)):
        fired = tally.get(True, 0)
        miss = sum(c for k, c in tally.items() if isinstance(k, str))
        print(f"  {label:42} {fired:6d}  {100.0 * fired / n:5.1f}%"
              f"   ({miss} unread)")
        if fired:
            print(f"    *** IT FIRED. That is a mechanism finding, not a "
                  f"puzzle: on those samples the test returns NO SNAP above "
                  f"gate 1, so no gate is deciding anything.")

    if unread * 4 >= n:
        print(f"\n  REFUSED: {unread} of {n} samples ({100.0 * unread / n:.0f}%) "
              f"could not read the ASYNC twin. No share in this block is a fact "
              f"about the client -- and the 'above the cut, no snap' population "
              f"is exactly what an unreadable twin would fabricate. THE FENCE "
              f"VERDICT ABOVE IS UNAFFECTED; it has its own denominator.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
