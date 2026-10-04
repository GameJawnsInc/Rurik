"""w0replica.py -- MOVECODE-1z-ds.44: the client's WORLD-0 copy of the player, replicated on the
TICK clock from our own sends.

WHY. The client's world-0 (sync) copy of the player is a deterministic function of what the
server put on the wire, applied in KEYSTREAM order at the client's world clock -- and that clock
is a per-run constant plus the sum of the 0x001E deltas sent before each message (the batch-6
join: constant on 122 of 122 follows; the tap's clock0 takes only tick values, 20,626 of 20,626
samples over 15 launches). Batch 7 (the kill-far / retire-near lanes, three finders and three
verifiers, independent code) replayed our own sends through the decoded bake on that clock and
matched the tap's world-0 at 205 of 206 domain presses within 0.5 u (p50 0.00 u; the one miss an
avoidance halt the client ran at the raider's disc). The server's two older models are wrong for
reasons this module does not share: the legacy model walks on the WALL clock at the declared base
(deaf to 0x002B), and the AgTrack mirror runs on the wall clock and sidesteps party bodies the
client does not avoid (hero 200: 0 of 21 encounters deviated, raider 110: 23 of 23).

WHAT. One `agtrack_mirror.SyncAgent` -- the same transcribed bake (the |d|^2 <= 1 short circuit,
the settle at the application clock, the 0x002C hard set) the mirror uses, so the rules live in
one place -- driven by:
    0x001E  clock += delta                                  (the tick's own arrival needs no write:
                                                             the resolver clamps first)
    0x0020  the player's create seeds the copy PARKED at its point
    0x0029 / 0x002A  consume a due arrival, then the setter + bake at the clock
    0x002C  the hard set (position, velocity 0, both target blocks invalidated)
    0x0028 / 0x002D  park where the copy stands (RECONSTRUCTION: every 0x0028 in the corpus
                     rides a 0x002C in its own tick, 136 of 136; 0x002D n = 1)
    0x002B  the moveSpeed store; 0x0027 the maxSpeed store (both PURE stores, read by the next
            bake: SyncAgent's SLICE-F48 reading. The 0x0027 timing is CONTESTED -- 0 sends in the
            corpus -- and is not this module's to settle)
NO avoidance pass: the client's own F14 halts and sidesteps against a hostile's disc are frame-
timed and are the replica's one blind spot (1 of 206 domain presses). Its consumers must fail
CLOSED on it -- an error that reads "not static" is today's kill.

Wire values are rounded to f32 on the way in, as the client reads them.

THREADING. `apply` runs under the caller's send lock, in keystream order. Readers on other
threads read `snap` -- an immutable tuple replaced whole by every step -- and evaluate it with the
pure `position_at`, so a reader never sees half a step.

Stdlib only; imports its sibling `agtrack_mirror` and nothing else from the repo.
"""

import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import agtrack_mirror  # noqa: E402

OP_TICK = 0x001E
OP_CREATE = 0x0020
OP_SPEED_BASE = 0x0027
OP_STOP = 0x0028
OP_MOVE = 0x0029
OP_DEST = 0x002A
OP_SPEED = 0x002B
OP_POS = 0x002C
OP_CANCEL = 0x002D
OPS = frozenset((OP_TICK, OP_CREATE, OP_SPEED_BASE, OP_STOP, OP_MOVE, OP_DEST, OP_SPEED, OP_POS,
                 OP_CANCEL))

# snap fields
S_CLOCK, S_X, S_Y, S_VX, S_VY, S_EPOCH, S_ARRIVE, S_DX, S_DY = range(9)


def f32(v):
    """The value as the wire carries it."""
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def _xy(p):
    if not (isinstance(p, (list, tuple)) and len(p) == 2):
        return None
    x, y = f32(p[0]), f32(p[1])
    if not (math.isfinite(x) and math.isfinite(y)):
        return None
    return x, y


def position_at(snap, clock=None):
    """(x, y) of a published snapshot at `clock` (default: the snapshot's own clock, the one the
    next send applies at). SyncAgent.position's resolver: CLAMP FIRST -- an armed arrival that is
    due reads the segment end -- else m_point + v * (clock - epoch) * 0.001."""
    if snap is None:
        return None
    c = snap[S_CLOCK] if clock is None else clock
    if snap[S_ARRIVE] != 0 and c >= snap[S_ARRIVE]:
        if snap[S_DX] is not None:
            return (snap[S_DX], snap[S_DY])
        return (snap[S_X], snap[S_Y])
    dt = (c - snap[S_EPOCH]) * 0.001
    return (snap[S_X] + snap[S_VX] * dt, snap[S_Y] + snap[S_VY] * dt)


def walking(snap, clock=None):
    """Does the copy still have a leg to walk at `clock`?"""
    if snap is None:
        return False
    c = snap[S_CLOCK] if clock is None else clock
    return snap[S_ARRIVE] != 0 and c < snap[S_ARRIVE]


class W0Replica(object):
    """The client's world-0 copy of ONE agent (the player), on the 0x001E clock."""

    def __init__(self, agent_id):
        self.agent = agent_id
        self.clock = 0          # ms: the sum of the 0x001E deltas applied (the client's clock less C)
        self.sync = agtrack_mirror.SyncAgent()
        self.seeded = False     # False until the agent's 0x0020: every read is None until then
        self.snap = None        # the published, immutable state (see position_at)
        self.steps = 0

    def apply(self, opcode, values):
        """One s2c message, in keystream order. Returns True when the copy's state changed."""
        if opcode == OP_TICK:
            if values:
                self.clock += int(values[0])
                self._publish()
            return False
        if not values or values[0] != self.agent:
            return False
        s, c = self.sync, self.clock
        if opcode == OP_CREATE:
            p = _xy(values[4]) if len(values) > 4 else None
            if p is None:
                return False
            s.set_position(p[0], p[1], values[5] if len(values) > 5 else None, c)
            self.seeded = True
        elif not self.seeded:
            return False
        elif opcode in (OP_MOVE, OP_DEST):
            p = _xy(values[1]) if len(values) > 1 else None
            if p is None:
                return False
            s.consume_arrival(c)
            s.bake_grant(p[0], p[1], values[2] if len(values) > 2 else None,
                         values[3] if len(values) > 3 else None, c)
        elif opcode == OP_POS:
            p = _xy(values[1]) if len(values) > 1 else None
            if p is None:
                return False
            s.set_position(p[0], p[1], values[2] if len(values) > 2 else None, c)
        elif opcode in (OP_STOP, OP_CANCEL):
            p = s.position(c)
            if p is None:
                return False
            s.set_position(p[0], p[1], s.plane, c)
        elif opcode == OP_SPEED:
            if len(values) < 2:
                return False
            s.move_speed = f32(values[1])
        elif opcode == OP_SPEED_BASE:
            if len(values) < 2:
                return False
            s.max_speed = f32(values[1])
        else:
            return False
        self.steps += 1
        self._publish()
        return True

    def _publish(self):
        s = self.sync
        if not self.seeded or s.x78 is None:
            self.snap = None
            return
        d = s.dest
        self.snap = (self.clock, s.x78, s.y78, s.vx, s.vy, s.t_epoch, s.t_arrive,
                     None if d is None else d[0], None if d is None else d[1])
