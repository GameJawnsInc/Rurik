"""MOVECODE-1z-cm: a rate message and its destination may not be split by a simulation tick.

THE CRASH (RUN-1zCG session 5, 2026-09-08 18:40:20, capture
authsrv-20260908T183848-c1, tape 1zcg5). The owner stood in the corner at the foot of
the stairs, the Hatcher walked up and boxed them in, they spammed clicks, and the client
asserted:

    Assertion: !(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)
    P:/Code/Engine/Agent/AgAgent.cpp(1198)                    (build 38797)

Every link of the chain is decoded in the pinned binary and was re-read for this file
(OBSERVED, static; the arc's earlier record in studies/movecode/FINDINGS.md sec.1j.3 and
studies/movement/FINDINGS.md :1147 said the same):

  * 0x002B (AGENT_UPDATE_SPEED) -> handler -> the rate/facing setter 0x00602990, which at
    0x00602A22 does `or dword [esi+0x20], 0x80000`: it SETS bit 19, MOVEMENT_STALE.
  * 0x0029 / 0x002A -> the destination setter 0x00602A40, which at 0x00602A65 does
    `and dword [ebx+0x20], 0xfff7ffff`: it CLEARS the bit.
  * 0x001E (WORLD_SIMULATION_TICK) -> handler 0x005fcf70 -> AgTimer::Advance 0x00603FE0
    (call at 0x005FCFA3; the dump's return 0x005fcfa8 rebased) -> the due ARRIVAL record
    -> the movement tick 0x00600140, whose first instructions are
    `mov eax,[esi+0x20]; shr eax,0x13; not eax; test al,1; jne ok; push 0x4ae; ...` --
    the assert, line 1198.

So the flag means "my rate changed, I am waiting for a destination", and the movement
tick refuses to run an ARRIVAL on an agent in that state. The tick fires at arrivals
only (0.62/s, sec.1v.1), which is why the flag can sit set across ticks without harm --
the tape shows it set for 90 ms over two ticks at 29.3 s of the same session -- and why
24 earlier splits in our September corpus did not assert: no arrival was due at their
tick. Session 5's split had a zero-distance STOP-ECHO 50 ms earlier, its arrival due at
the very next advance.

THE WIRE (OBSERVED). Our capture: seq 2723 0x002B to the player at 92.2903 s, seq 2724
0x001E at 92.2905, seq 2725 the click's 0x0029 at 92.2906. The client's last frame is
the click at 92.289; the tape's world-0 copy of the player reads flags 0xA0005 (bit 19
set) from that instant to the end, its target point still the STOP-ECHO's. The seq is
taken under the send lock at crypt time, so this IS the wire order.

WHY IT CAN HAPPEN HERE AND NOT AT RETAIL. authsrv.py's `send()` takes the lock per
message. The receive thread answers a click with two sends -- the 0x002B, then the
0x0029 after route() -- and the world-tick thread sends 0x001E every 50 ms between
whatever two sends it lands in. Retail's control (studies/movecode/review/
stalepair_retail.py over the LIVE corpus, origin-gated): 2,404 0x002B on 61 connections,
2,403 followed by the same agent's destination at a wire gap of exactly ZERO -- the same
packet, every time -- and a 0x001E between them 0 times. Ours before this file: 24 splits
in 2,701 pairs (studies/movecode/FINDINGS.md sec.1z-cm).

WHAT THIS MODULE DOES. One gate at the chokepoint every send passes through: a 0x002B
OPENS a pair for its agent; that agent's next 0x0029/0x002A CLOSES it; a 0x001E from
another thread WAITS on the send lock's condition while a pair is open, bounded by
HOLD_MAX_S, and a pair still open at the bound is a BARE rate message -- the class that
produced the loading-screen assert of 2026-08 (PLAN.md sec.8 "asserts as the loading
screen fades") -- which is dropped and named loudly rather than held forever. A pair
opened by the ticking thread itself cannot be waited on (it would be waiting on itself)
and is reported the same way. `--no-stale-pair-gate` reverts to the per-message lock.

`census(rows)` reads a capture's `sent` rows back and counts the pairs, the splits and
the bares, so sessionscore.py can print the invariant on every session and the test can
refuse a regression on the crash capture itself.

Standard library only: this is on the server path.
"""
import collections
import threading
import time

OPCODE_TICK = 0x001E
OPCODE_RATE = 0x002B
OPCODE_DESTS = (0x0029, 0x002A)

# The pair's measured window is 0.3 ms (session 5); route() is bounded at 35 ms per
# test_pathmap's tick bar. A tick held 100 ms is one late simulation delta, and it only
# happens on a bare rate message, which is a defect this hold exists to name.
HOLD_MAX_S = 0.10


def agent_of(values):
    """The agent a 0x002B / 0x0029 / 0x002A addresses: field 0 of every one of them."""
    if isinstance(values, (list, tuple)) and values:
        try:
            return int(values[0])
        except (TypeError, ValueError):
            return None
    return None


class StalePairGate:
    """The open rate/destination pairs, keyed by agent, owned by the thread that opened them.

    Every method is meant to be called UNDER the send lock. `note` records a message that
    has just gone on the wire; `blocking(tid)` lists pairs a tick from thread `tid` must
    wait on; `own(tid)` lists pairs that thread opened itself and never closed.
    """

    def __init__(self):
        self.pending = {}          # agent -> (thread_ident, t_opened)
        self.opened = 0
        self.closed = 0
        self.holds = 0             # ticks that actually waited
        self.hold_s = 0.0          # summed wait
        self.bare = []             # (agent, thread_ident, age_s, own) dropped at a bound

    def note(self, opcode, values, tid, now):
        """Record a sent message. Returns 'open', 'close' or None."""
        agent = agent_of(values)
        if agent is None:
            return None
        if opcode == OPCODE_RATE:
            self.pending[agent] = (tid, now)
            self.opened += 1
            return "open"
        if opcode in OPCODE_DESTS and agent in self.pending:
            del self.pending[agent]
            self.closed += 1
            return "close"
        return None

    def blocking(self, tid):
        return [a for a, (owner, _t) in self.pending.items() if owner != tid]

    def own(self, tid):
        return [a for a, (owner, _t) in self.pending.items() if owner == tid]

    def drop(self, agents, now, tid):
        for a in agents:
            owner, t0 = self.pending.pop(a, (None, now))
            self.bare.append((a, owner, now - t0, owner == tid))


def hold_tick(gate, cond, tid, now_fn=time.monotonic, max_wait=HOLD_MAX_S):
    """Call UNDER `cond` (the send lock) just before writing a 0x001E.

    Waits while another thread has a rate/destination pair open, until it closes or
    `max_wait` passes. Returns (waited_s, bare_other, bare_own): the agents whose pair
    was still open at the bound (dropped, so the next tick does not wait again) and the
    agents this very thread left open (never waited on -- it would be waiting on itself).
    """
    t0 = now_fn()
    deadline = t0 + max_wait
    waited_any = False
    while gate.blocking(tid):
        remaining = deadline - now_fn()
        if remaining <= 0:
            break
        waited_any = True
        cond.wait(remaining)
    now = now_fn()
    bare_other = gate.blocking(tid)
    bare_own = gate.own(tid)
    if bare_other or bare_own:
        gate.drop(bare_other + bare_own, now, tid)
    waited = (now - t0) if waited_any else 0.0
    if waited_any:
        gate.holds += 1
        gate.hold_s += waited
    return waited, bare_other, bare_own


def note_blob(gate, blob, tid, now):
    """note() for PRE-FORMED plaintext -- the tape player's door into the socket.

    send_raw() writes whole recorded messages and has no decoded values, but a tape
    carrying a 0x002B is exactly as splittable as a live one. Every one of the three
    opcodes this gate cares about is [u16 opcode][u32 agent], so the agent reads off the
    blob directly. Anything shorter than 6 bytes, or any other opcode, notes nothing.
    """
    if not blob or len(blob) < 2:
        return None
    op = int.from_bytes(blob[:2], "little")
    if op != OPCODE_RATE and op not in OPCODE_DESTS:
        return None
    if len(blob) < 6:
        return None
    return gate.note(op, [int.from_bytes(blob[2:6], "little")], tid, now)


def _agent_from_plain(plain):
    try:
        return int.from_bytes(bytes.fromhex(plain[4:12]), "little")
    except (TypeError, ValueError):
        return None


def census(rows, lookahead=12):
    """The invariant read back off a capture's `sent` rows (dicts with opcode/plain/seq/t).

    Returns {pairs, split, bare, between (Counter of the opcode tuples between a 0x002B
    and its destination), splits ([(seq, t, label)] of the pairs a 0x001E sat inside),
    bares ([(seq, t, label)])}. A 0x002B with no same-agent destination within
    `lookahead` sends is a bare.
    """
    sent = [r for r in rows if r.get("kind") == "sent" and r.get("opcode") is not None]
    out = {"pairs": 0, "split": 0, "bare": 0, "between": collections.Counter(),
           "splits": [], "bares": []}
    for i, r in enumerate(sent):
        if r["opcode"] != OPCODE_RATE:
            continue
        aid = _agent_from_plain(r.get("plain", ""))
        seq = []
        found = None
        for r2 in sent[i + 1:i + 1 + lookahead]:
            if r2["opcode"] in OPCODE_DESTS and _agent_from_plain(r2.get("plain", "")) == aid:
                found = r2
                break
            seq.append(r2["opcode"])
        tag = (r.get("seq"), round(r.get("t") or 0.0, 3), (r.get("label") or "")[:48])
        if found is None:
            out["bare"] += 1
            out["bares"].append(tag)
            continue
        out["pairs"] += 1
        out["between"][tuple(seq)] += 1
        if OPCODE_TICK in seq:
            out["split"] += 1
            out["splits"].append(tag)
    return out
