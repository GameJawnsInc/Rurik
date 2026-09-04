"""Checks for agenttap.py's AGTRACK FENCE wiring (MOVECODE-1z-an).

The offsets and the record walk are `movetap`'s and are owned by
`movetap --selftest`; this file checks the things agenttap adds on top, all of
which are places a live run would have failed silently:

  1. `memo_reader` answers each address ONCE per sample and does NOT persist
     across samples -- a memo that outlived the sample would stamp a stale
     fence with a fresh timestamp, which is worse than not reading it.
  2. the four `gate_reach` branches come back as agenttap drives them, with the
     SYNC block (world 0) handed over -- the branch on which the snap test is
     actually reached.
  3. `read_copy` returns the raw block beside the fields, and still refuses an
     id mismatch and a short block.
  4. THE NEGATIVE CONTROL GOES RED. The Hatcher's record must read `shut` for a
     whole run, and the summary must SAY SO when it does not -- a control that
     cannot fail is not a control, so this drives it both ways.
  5. an old tape with no `fence` key summarises without raising.

BARE MACHINE: fake memory throughout, no client, no vault. `agtrack_fence` takes
a `read(addr, n)` closure precisely so this is possible, which is why the fence
could be wired and verified without a client run.
"""

import io
import os
import struct
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import checks                                                  # noqa: E402
import agenttap                                                # noqa: E402
from movetap import (OFF_AGTRACK, T_STATE_ARRAY, T_ARMED_ID,   # noqa: E402
                     STATE_STRIDE, AGENT_SPAN, A_ID, A_WORLD,
                     REACH_TEST_RUNS, REACH_FENCED)

LEDGER = checks.Ledger("agenttap fence wiring", floor=18)
check = checks.adopt_named(LEDGER)

AG, ARRAY = 0x10000000, 0x0A000000
PLAYER, HATCH = 1, 10


def agent_block(aid, world=0):
    b = bytearray(AGENT_SPAN)
    struct.pack_into("<I", b, A_ID, aid)
    struct.pack_into("<i", b, A_WORLD, world)
    return bytes(b)


def fake_mem(controlled_by_id, counter=None):
    """A `read` over an AgTrack whose record for each id carries `controlled`."""
    def read(addr, n):
        if counter is not None:
            counter[addr] = counter.get(addr, 0) + 1
        if addr == AG + OFF_AGTRACK + T_STATE_ARRAY:
            return struct.pack("<III", ARRAY, 0, 64)
        if addr == AG + OFF_AGTRACK + T_ARMED_ID:
            return struct.pack("<I", PLAYER)
        for aid, ctrl in controlled_by_id.items():
            if addr == ARRAY + aid * STATE_STRIDE:
                return (struct.pack("<II", ctrl, 0) + bytes(STATE_STRIDE - 8))[:n]
        return None
    return read


# ---- 1. the memo ----------------------------------------------------------
print("\n1. memo_reader: one read per address per sample, and no bleed across")

calls = {}
raw = fake_mem({PLAYER: 1}, counter=calls)


class _H:                       # a stand-in for the process handle
    pass


_real = agenttap.keytap.read_handle
try:
    agenttap.keytap.read_handle = lambda h, a, n: raw(a, n)
    rd = agenttap.memo_reader(_H())
    a1 = rd(AG + OFF_AGTRACK + T_STATE_ARRAY, 0x0C)
    a2 = rd(AG + OFF_AGTRACK + T_STATE_ARRAY, 0x0C)
    check("the same address is fetched once and served twice",
          a1 == a2 and calls[AG + OFF_AGTRACK + T_STATE_ARRAY] == 1,
          f"{calls.get(AG + OFF_AGTRACK + T_STATE_ARRAY)} reads -- the AgTrack "
          f"header is per-AgTrack, not per-agent, and this tape is already at "
          f"~9 Hz of the 30 it asks for")
    rd2 = agenttap.memo_reader(_H())
    rd2(AG + OFF_AGTRACK + T_STATE_ARRAY, 0x0C)
    check("a NEW sample's reader refetches -- the memo does not outlive the sample",
          calls[AG + OFF_AGTRACK + T_STATE_ARRAY] == 2,
          "a memo that persisted would report a stale fence with a fresh "
          "timestamp, which is worse than not reading it")
finally:
    agenttap.keytap.read_handle = _real

# ---- 2. the four branches, driven the way agenttap drives them -------------
print("\n2. the fence states and gate_reach, with the SYNC block handed over")

from movetap import agtrack_fence                              # noqa: E402

seen = set()
for ctrl, world in ((1, 0), (1, 1), (0, 0), (0, 2)):
    r = agtrack_fence(fake_mem({PLAYER: ctrl}), AG, PLAYER,
                      agent_block(PLAYER, world))
    seen.add(r["gate_reach"])
check("all four branches are reachable through agenttap's call shape",
      seen == set(REACH_FENCED) | {REACH_TEST_RUNS}, f"got {sorted(seen)}")

openr = agtrack_fence(fake_mem({PLAYER: 1}), AG, PLAYER, agent_block(PLAYER, 0))
shutr = agtrack_fence(fake_mem({PLAYER: 0}), AG, PLAYER, agent_block(PLAYER, 0))
check("world 0 + controlled reads `open` and REACHES the snap test",
      openr["fence_state"] == "open" and openr["gate_reach"] == REACH_TEST_RUNS,
      f"{openr['fence_state']} / {openr['gate_reach']} -- world 0 is the branch "
      f"the test at 0x006055E0 is actually reached on, which is why the SYNC "
      f"block is the one agenttap passes")
check("clientControlled == 0 reads `shut`, never a failure value",
      shutr["fence_state"] == "shut" and shutr["fence_raw"] == 0,
      f"{shutr['fence_state']} -- 0 is a REAL answer here and must not be "
      f"confusable with an unread record")
check("an unreadable AgTrack yields an `unread:` state, not a shut one",
      str(agtrack_fence(lambda a, n: None, AG, PLAYER,
                        agent_block(PLAYER, 0))["fence_state"]).startswith("unread:"),
      "a failed read that returned 0 would be indistinguishable from a shut fence")
check("a block whose id is not the one we indexed with is refused",
      str(agtrack_fence(fake_mem({PLAYER: 1}), AG, PLAYER,
                        agent_block(99, 0))["fence_state"]).startswith("unread:"),
      "we resolve through the array and the client indexes AgTrack by the "
      "agent's OWN id field; a mismatch means we hold the wrong object")

# ---- 3. read_copy's two-value return --------------------------------------
print("\n3. read_copy returns (fields, raw block) and still refuses the bad cases")


def _rc(blk_for_ptr, aid=PLAYER, count=64):
    def rh(h, a, n):
        if a in (AG + 0x100, AG + 0x104):
            return struct.pack("<I", count if a == AG + 0x100 else ARRAY)
        if a == ARRAY + aid * 4:
            return struct.pack("<I", 0x0B000000)
        if a == 0x0B000000:
            return blk_for_ptr
        return None
    return rh


_real = agenttap.keytap.read_handle
try:
    agenttap.keytap.read_handle = _rc(agent_block(PLAYER, 0))
    fields, blk = agenttap.read_copy(_H(), AG, 0x104, 0x100, PLAYER)
    check("a good read returns both the decoded fields and the raw block",
          fields is not None and blk is not None and len(blk) == AGENT_SPAN,
          "agtrack_fence needs the RAW block -- handing it our decoded dict "
          "would mean trusting our own decode twice")
    agenttap.keytap.read_handle = _rc(agent_block(77, 0))
    fields, blk = agenttap.read_copy(_H(), AG, 0x104, 0x100, PLAYER)
    check("an id mismatch reports bad_id and still returns the block",
          fields == {"bad_id": 77} and blk is not None, f"{fields}")
    agenttap.keytap.read_handle = _rc(b"\x00" * 4)
    fields, blk = agenttap.read_copy(_H(), AG, 0x104, 0x100, PLAYER)
    check("a short block is refused as (None, None), never a partial agent",
          fields is None and blk is None, f"{fields!r}, {blk!r}")
finally:
    agenttap.keytap.read_handle = _real


# ---- 4. the negative control, driven BOTH ways -----------------------------
print("\n4. the Hatcher control: shut passes, open must go RED")


def sample(t, player_state, hatcher_state):
    def one(st):
        return {"sync": {"x": 0.0, "y": 0.0, "flags": 0, "follow": 0, "stop": 0},
                "async": {"x": 0.0, "y": 0.0, "flags": 0, "follow": 0, "stop": 0},
                "fence": {"fence_state": st, "gate_reach":
                          REACH_TEST_RUNS if st == "open" else "shut:append",
                          "fence_raw": 1 if st == "open" else 0}}
    return {"kind": "sample", "t": t,
            "agents": {str(PLAYER): one(player_state), str(HATCH): one(hatcher_state)}}


good = [sample(0.0, "open", "shut"), sample(0.1, "shut", "shut")]
buf = io.StringIO()
with redirect_stdout(buf):
    agenttap.summarise_fence(good, str(PLAYER), str(HATCH))
out = buf.getvalue()
check("a well-formed run prints both columns and does NOT cry control failure",
      "FENCE player" in out and "CONTROL FAILED" not in out, out.strip()[:160])
check("the player's fence TRANSITION is printed, which is the lock's own event",
      "open -> shut" in out, out.strip()[:200])

bad = [sample(0.0, "open", "open")]
buf = io.StringIO()
with redirect_stdout(buf):
    agenttap.summarise_fence(bad, str(PLAYER), str(HATCH))
out = buf.getvalue()
check("A HATCHER READING `open` GOES RED -- the control can fail",
      "CONTROL FAILED" in out,
      "0x00605F10 has two callers, both local-command, so only the player's "
      "agent is client-controlled; an open Hatcher means the wrong record and "
      "the player's column proves nothing. A control that cannot fail is not "
      "a control")

unread = [sample(0.0, "unread:record-unreadable", "unread:record-unreadable")]
buf = io.StringIO()
with redirect_stdout(buf):
    agenttap.summarise_fence(unread, str(PLAYER), str(HATCH))
out = buf.getvalue()
check("an all-`unread:` run does NOT trip the control (unread is a third thing)",
      "CONTROL FAILED" not in out and "unread:" in out, out.strip()[:160])

# ---- 5. old tapes ---------------------------------------------------------
print("\n5. a tape written before the fence existed still summarises")

old = [{"kind": "sample", "t": 0.0, "agents": {
    str(PLAYER): {"sync": {}, "async": {}}, str(HATCH): {"sync": {}, "async": {}}}}]
buf = io.StringIO()
with redirect_stdout(buf):
    agenttap.summarise_fence(old, str(PLAYER), str(HATCH))
check("no `fence` key says so rather than raising",
      "not read" in buf.getvalue(),
      "the 17 tapes already in the vault have no fence column and must still "
      "be readable")

# ---- 6. the camera column (MOVECODE-1z-ay) --------------------------------
print("\n6. the camera read: the client's own view transform, or a sentinel")

from fovread import VA_FOV, VA_POSITION, VA_TARGET, IMAGE_BASE as FIB  # noqa: E402

BASE = 0x00400000
WANT = {FIB + (VA_FOV - FIB): struct.pack("<f", 1.309),
        FIB + (VA_POSITION - FIB): struct.pack("<3f", 10.0, 20.0, 30.0),
        FIB + (VA_TARGET - FIB): struct.pack("<3f", 40.0, 50.0, 60.0)}


def _cam_read(h, a, n):
    for va, blob in WANT.items():
        if a == BASE + (va - FIB):
            return blob[:n]
    return None


_real = agenttap.keytap.read_handle
try:
    agenttap.keytap.read_handle = _cam_read
    cam = agenttap.read_camera(_H(), BASE)
    check("the camera comes back as fov + position + target",
          cam.get("fov") is not None and cam.get("pos") == [10.0, 20.0, 30.0]
          and cam.get("tgt") == [40.0, 50.0, 60.0],
          "%s -- these three ARE the view transform, so sec.1z-ax's projection "
          "needs nothing else" % cam)
    agenttap.keytap.read_handle = lambda h, a, n: None
    cam = agenttap.read_camera(_H(), BASE)
    check("an unreadable camera returns a SENTINEL, never zeros",
          str(cam.get("cam", "")).startswith("unread:"),
          "a (0,0,0) position would project every click to the same fraction "
          "and look exactly like data")
finally:
    agenttap.keytap.read_handle = _real

check("the addresses are IMPORTED from fovread, not restated here",
      "from fovread import" in open(
          os.path.join(os.path.dirname(agenttap.__file__), "agenttap.py"),
          encoding="utf-8").read(),
      "they are the frustum builder's own failure-path arguments; a drift must "
      "break ONE place")

raise SystemExit(LEDGER.verdict())
