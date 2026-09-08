"""MOVECODE-1z-cm: the rate/destination pair may not be split by a simulation tick.

The client asserts `!(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)` (AgAgent.cpp:1198) when
an arrival record fires on an agent whose 0x002B has landed and whose 0x0029/0x002A has
not. Our server sends the two from the receive thread, the world tick from its own, and
the per-message send lock let a 0x001E slip between them: seq 2723 / 2724 / 2725 of
RUN-1zCG session 5's capture, 0.3 ms apart, the client's last frame the click that
caused them. Retail never does this: 2,403 of 2,403 pairs at a wire gap of zero.

What this file refuses to let rot:
  1. the gate's bookkeeping -- open on 0x002B, close on the same agent's destination,
     other-thread vs own-thread pairs, the bare drop;
  2. hold_tick against a REAL condition and a second thread: a tick ordered after the
     destination that closes the pair, the bound on a pair nobody closes, and the
     own-thread pair that must never be waited on (it would be waiting on itself);
  3. census() on synthetic rows, on the crash capture (exactly ONE split, at seq 2723),
     and on session 4's (none) -- the known-bad arm measured on the thing itself;
  4. the retail control over the live corpus: a floor on the pair count, an INVARIANT on
     the splits (retail 0), and the zero-gap packetization;
  5. source pins on authsrv.py: the hold sits under the send lock before sendall for a
     tick, a closing destination notifies, the flag and its revert exist.
Sections that need the vault or the live corpus SKIP loudly on a bare machine.
"""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks       # noqa: E402
import stalepair    # noqa: E402
import vaultpath    # noqa: E402

LEDGER = checks.Ledger("MOVECODE-1z-cm, the stale-pair gate", floor=44)   # from the green run
check = checks.adopt(LEDGER)

RATE, TICK, DEST, DEST2 = (stalepair.OPCODE_RATE, stalepair.OPCODE_TICK,
                           stalepair.OPCODE_DESTS[0], stalepair.OPCODE_DESTS[1])
CRASH_CAP = ("captures", "gamesrv", "authsrv-20260908T183848-c1.jsonl")   # session 5
S4_CAP = ("captures", "gamesrv", "authsrv-20260907T144522-c1.jsonl")      # session 4
RETAIL_PAIRS_FLOOR = 2404   # 2026-09-08, 61 live connections; the corpus only grows


def section_gate():
    print("\n[1] the gate's bookkeeping")
    g = stalepair.StalePairGate()
    A, B = 111, 222   # thread idents
    check(g.note(RATE, [1, 1.0, 1], A, 10.0) == "open", "a 0x002B opens a pair for its agent")
    check(g.blocking(B) == [1] and g.blocking(A) == [], "another thread is blocked by it; the opener is not")
    check(g.own(A) == [1] and g.own(B) == [], "the opener owns it")
    check(g.note(TICK, [50], B, 10.01) is None, "a tick notes nothing")
    check(g.note(DEST, [7, [0.0, 0.0], 0, 0], A, 10.02) is None,
          "a destination for ANOTHER agent does not close it")
    check(g.note(DEST2, [1, [0.0, 0.0], 0, 0, 1], A, 10.03) == "close" and not g.pending,
          "the same agent's 0x002A closes it")
    check(g.note(DEST, [1, [0.0, 0.0], 0, 0], A, 10.04) is None, "a destination with nothing open notes nothing")
    g.note(RATE, [1, 1.0, 9], A, 11.0)
    g.note(RATE, [10, 1.0, 1], B, 11.0)
    check(sorted(g.blocking(B)) == [1] and sorted(g.blocking(A)) == [10],
          "two pairs from two threads: each blocks only the other")
    g.drop([1, 10], 11.5, B)
    check(not g.pending and len(g.bare) == 2 and g.bare[0][3] is False and g.bare[1][3] is True,
          "drop names each bare pair with its age and whether the dropper owned it",
          f"bare={g.bare}")
    check(g.opened == 3 and g.closed == 1, "the counters", f"opened {g.opened} closed {g.closed}")
    check(stalepair.agent_of([]) is None and stalepair.agent_of(None) is None
          and stalepair.agent_of(["x"]) is None and stalepair.agent_of([5, 1.0]) == 5,
          "agent_of: field 0 as an int, else None")

    # note_blob: the tape player's door, which has no decoded values. Byte LISTS, not
    # escapes -- every one of these three messages is [u16 opcode][u32 agent][payload].
    g2 = stalepair.StalePairGate()
    rate_blob = bytes([0x2B, 0x00]) + (1).to_bytes(4, "little") + bytes(5)
    dest_blob = bytes([0x29, 0x00]) + (1).to_bytes(4, "little") + bytes(16)
    tick_blob = bytes([0x1E, 0x00]) + (50).to_bytes(4, "little")
    check(stalepair.note_blob(g2, rate_blob, A, 1.0) == "open" and g2.blocking(B) == [1],
          "note_blob opens a pair from raw tape bytes")
    check(stalepair.note_blob(g2, tick_blob, A, 1.1) is None
          and stalepair.note_blob(g2, b"", A, 1.1) is None
          and stalepair.note_blob(g2, bytes([0x2B, 0x00, 0x01]), A, 1.1) is None,
          "a tick, an empty blob and a truncated one note nothing")
    check(stalepair.note_blob(g2, dest_blob, A, 1.2) == "close" and not g2.pending,
          "and the destination blob closes it")


def section_hold():
    print("\n[2] hold_tick under a real condition, against a second thread")
    lock = threading.Lock()
    cond = threading.Condition(lock)
    g = stalepair.StalePairGate()
    T = threading.get_ident()

    with lock:
        w, bo, bown = stalepair.hold_tick(g, cond, T)
    check(w == 0.0 and not bo and not bown and g.holds == 0, "nothing open: the tick does not wait", f"w={w}")

    # A second thread opens a pair, sleeps 30 ms, closes it under the lock and notifies.
    order = []

    def opener():
        with lock:
            g.note(RATE, [1, 1.0, 1], threading.get_ident(), time.monotonic())
            order.append("rate")
        time.sleep(0.03)
        with lock:
            r = g.note(DEST, [1, [1.0, 2.0], 0, 0], threading.get_ident(), time.monotonic())
            order.append("dest")
            if r == "close":
                cond.notify_all()

    th = threading.Thread(target=opener)
    th.start()
    time.sleep(0.005)          # let the pair open
    with lock:
        w, bo, bown = stalepair.hold_tick(g, cond, T, max_wait=1.0)
        order.append("tick")
    th.join()
    check(order == ["rate", "dest", "tick"], "the tick waits for the destination that closes the pair",
          f"order={order}")
    check(0.02 <= w < 0.5 and not bo and not bown and g.holds == 1,
          "it waited about the pair's width and reports no bare", f"waited {w*1000:.1f} ms")

    # A pair nobody closes: the bound, then the drop, named as another thread's.
    g2 = stalepair.StalePairGate()
    with lock:
        g2.note(RATE, [1, 1.0, 1], T + 1, time.monotonic())
        t0 = time.monotonic()
        w, bo, bown = stalepair.hold_tick(g2, cond, T, max_wait=0.05)
        dt = time.monotonic() - t0
    check(bo == [1] and not bown and not g2.pending, "a pair nobody closes is dropped at the bound as a bare",
          f"bare_other={bo} pending={g2.pending}")
    check(0.045 <= dt < 0.5, "and the bound is the wait", f"{dt*1000:.1f} ms")
    check(len(g2.bare) == 1 and g2.bare[0][3] is False, "the bare row says another thread left it open")

    # A pair this thread opened itself: reported, never waited on.
    g3 = stalepair.StalePairGate()
    with lock:
        g3.note(RATE, [10, 1.0, 1], T, time.monotonic())
        t0 = time.monotonic()
        w, bo, bown = stalepair.hold_tick(g3, cond, T, max_wait=0.5)
        dt = time.monotonic() - t0
    check(bown == [10] and not bo and dt < 0.05 and not g3.pending,
          "the ticking thread's own open pair is named and dropped without a wait",
          f"own={bown} waited {dt*1000:.1f} ms")
    check(len(g3.bare) == 1 and g3.bare[0][3] is True, "and its bare row says so")

    # A fake clock: the deadline arithmetic without sleeping.
    clock = [100.0]

    def now():
        clock[0] += 0.01
        return clock[0]

    g4 = stalepair.StalePairGate()
    with lock:
        g4.note(RATE, [1, 1.0, 1], T + 1, now())
        w, bo, bown = stalepair.hold_tick(g4, cond, T, now_fn=now, max_wait=0.1)
    check(bo == [1] and w > 0.1 - 1e-9 and g4.hold_s == w, "the deadline reads the clock it is given",
          f"waited {w:.3f}")


def _rows(spec):
    """[(kind, opcode, agent, label)] -> capture-shaped sent rows."""
    out = []
    for i, (op, agent, label) in enumerate(spec):
        plain = "%04x" % op if op == TICK else ("%02x00" % op) + agent.to_bytes(4, "little").hex()
        out.append({"kind": "sent", "seq": i, "t": i * 0.01, "opcode": op,
                    "label": label, "plain": plain})
    return out


def section_census():
    print("\n[3] census()")
    rows = _rows([
        (RATE, 1, "speed A"), (DEST, 1, "dest A"),                       # clean pair
        (RATE, 1, "speed B"), (TICK, 0, "tick"), (DEST, 1, "dest B"),    # SPLIT
        (RATE, 10, "npc speed"), (DEST2, 10, "follow"),                  # clean 0x002A pair
        (RATE, 1, "speed C"), (0x25, 1, "dir"), (DEST, 1, "dest C"),     # something else between
        (RATE, 1, "speed E"), (DEST, 10, "npc dest"), (DEST, 1, "dest E"),  # another agent's dest does not close
        (RATE, 1, "speed D"),                                            # bare (end of capture)
    ])
    c = stalepair.census(rows)
    check(c["pairs"] == 5 and c["split"] == 1 and c["bare"] == 1,
          "5 pairs, 1 split, 1 bare on the synthetic stream",
          f"pairs {c['pairs']} split {c['split']} bare {c['bare']}")
    check(c["splits"][0][2] == "speed B" and c["bares"][0][2] == "speed D",
          "and each is named by its 0x002B", f"{c['splits']} {c['bares']}")
    check(c["between"][(TICK,)] == 1 and c["between"][(0x25,)] == 1
          and c["between"][(DEST,)] == 1 and c["between"][()] == 2,
          "what sat between is tallied per pair", f"{dict(c['between'])}")
    check(stalepair.census([]) == {"pairs": 0, "split": 0, "bare": 0, "between": {},
                                   "splits": [], "bares": []},
          "an empty capture censuses to zeros")
    # lookahead: a destination 3 sends away is found with lookahead 3, not 2
    rows2 = _rows([(RATE, 1, "s"), (TICK, 0, "t"), (TICK, 0, "t"), (DEST, 1, "d")])
    check(stalepair.census(rows2, lookahead=3)["pairs"] == 1
          and stalepair.census(rows2, lookahead=2)["bare"] == 1,
          "the lookahead bounds the search and a miss is a bare")

    import json
    for parts, want_pairs, want_split, want_seq, what in (
            (CRASH_CAP, 130, 1, 2723, "session 5, the crash capture"),
            (S4_CAP, 134, 0, None, "session 4")):
        path = vaultpath.vault_path(*parts)
        if not os.path.isfile(path):
            LEDGER.skip(f"3. {what}", f"no capture at {path}")
            continue
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(l) for l in fh]
        c = stalepair.census(rows)
        check(c["pairs"] == want_pairs and c["split"] == want_split and c["bare"] == 0,
              f"{what}: {want_pairs} pairs, {want_split} split, 0 bare -- the known-bad arm measured",
              f"pairs {c['pairs']} split {c['split']} bare {c['bare']} splits={c['splits']}")
        if want_seq is not None:
            check(c["splits"] and c["splits"][0][0] == want_seq
                  and c["splits"][0][2].startswith("AGENT_UPDATE_SPEED(player"),
                  f"the split is seq {want_seq}, the click's rate message at 92.29 s",
                  f"{c['splits']}")


def section_retail():
    print("\n[4] the retail control over the live corpus")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                    "studies", "movecode", "review"))
    try:
        import stalepair_retail
        import livewire
    except ImportError as e:
        LEDGER.skip("4. the retail control", f"import failed: {e}")
        return
    if not livewire.live_captures():
        LEDGER.skip("4. the retail control", "no LIVE captures under the vault")
        return
    c = stalepair_retail.retail_census()
    check(c["conns"] >= 61 and c["bad_conns"] == 0,
          "the live corpus decodes closed on every connection",
          f"{c['conns']} connections, {c['bad_conns']} not closed")
    check(c["pairs"] >= RETAIL_PAIRS_FLOOR - 1,
          f"retail pairs at or above the 2026-09-08 floor ({RETAIL_PAIRS_FLOOR - 1})",
          f"{c['pairs']} pairs, {c['bare']} bare of {c['total']}")
    check(c["split"] == 0, "retail NEVER puts a 0x001E between a 0x002B and its destination",
          f"split {c['split']}: {c['splits'][:3]}")
    check(c["zero_gap"] == c["pairs"],
          "and the wire gap is zero on every pair: the same packet",
          f"{c['zero_gap']} of {c['pairs']}")


def section_pins():
    print("\n[5] source pins on authsrv.py")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check("import stalepair" in src, "authsrv imports stalepair")
    check("STALE_PAIR_GATE = True" in src, "the gate ships ON")
    check('"--no-stale-pair-gate"' in src and "STALE_PAIR_GATE = not a.no_stale_pair_gate" in src,
          "--no-stale-pair-gate is the revert arm and resolves the global")
    check("send_cond = threading.Condition(send_lock)" in src and "stale_gate = stalepair.StalePairGate()" in src,
          "the condition shares the send lock, one gate per connection")
    i_hold = src.find("stalepair.hold_tick(stale_gate, send_cond")
    i_send = src.find("sock.sendall(s2c.crypt(blob))")
    i_note = src.find("stale_gate.note(opcode, values")
    check(0 < i_hold < i_send < i_note, "in send(): the hold, then the write, then the note -- all under the lock",
          f"hold@{i_hold} sendall@{i_send} note@{i_note}")
    check('== "close"' in src[i_note:i_note + 400] and "send_cond.notify_all()" in src[i_note:i_note + 400],
          "a closing destination wakes the waiting tick")
    check('rec.event("stale_pair_gate"' in src, "a hold or a bare lands in the capture as its own row")
    check("if STALE_PAIR_GATE and opcode == GAME_SMSG_WORLD_SIMULATION_TICK" in src,
          "only a tick waits; the revert arm restores the per-message lock exactly")
    i_raw = src.find("def send_raw(")
    check(i_raw > 0 and "stalepair.note_blob(stale_gate, blob" in src[i_raw:i_raw + 2500],
          "send_raw -- the tape player's door -- notes through the gate too, so a "
          "replayed 0x002B still blocks the world tick")


def main():
    section_gate()
    section_hold()
    section_census()
    section_retail()
    section_pins()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
