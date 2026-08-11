"""Burrowing: what ArenaNet's own bytes do, and what our server does about it.

Two halves, deliberately kept apart.

SECTION 2 re-measures the mechanic from the live capture rather than from any study
doc. That matters here more than usual, because the study doc was wrong: T3 concluded
burrowing "runs entirely through the two opcodes we already implement" and every worm
re-creation is in fact a five-message burst. A test that asserted the doc would have
locked the error in. So this half counts the real messages and will go red if the
capture ever stops saying what we claim it says.

SECTION 3 drives our own implementation with a fake `send`, and asserts the things
that would break a live session rather than the things that are easy to assert. The
failure it is really aimed at: a re-create that emits the wire messages but forgets the
state write. `remove_agent` refuses a double-remove, so the NEXT submerge raises inside
the world-tick daemon thread and stops the world for the rest of the session, with a
traceback nowhere near the cause. That is why `create_agent_world` owns both halves and
why the guard is checked from both directions here.

WHAT THIS FILE USED TO SAY IT COULD NOT SETTLE -- SETTLED 2026-08-11. ArenaNet sends the
NPC definition (0x0056) exactly ONCE for 140 re-creates of the same worm, so their client
keeps a definition across a removal. Ours had never been asked -- the D1 probe re-sent the
definition every single time, which is precisely why its success proved nothing about
this -- and `agents.npc_properties` warns that an agent whose definition was never sent
takes the client down on `index < m_count`, with no server-side symptom.

The `burrow` probe ran (studies/enemy/PLAN.md 10.8, capture authsrv-20260811T135809): our
Hatcher was removed and re-created twice with no 0x0056/0x0057 -- once at the same id, once
at a fresh one -- and both drew a correct collector. A definition is per-INSTANCE.
`burrow_tick` now passes send_definition=False and THIS FILE ASSERTS THAT NO RE-CREATE
RESENDS. The first create still declares; only re-creates skip it.

This paragraph is dated because its predecessor was not: the commit that flipped the check
below rewrote the check's own message, create_agent_world's docstring, burrow_tick's
comment and the probe note, and left this header saying the opposite of all four.
"""
import inspect
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import authsrv  # noqa: E402
import checks  # noqa: E402
import tape  # noqa: E402
import vaultpath  # noqa: E402
from codec import Codec  # noqa: E402

# The Lakeside County connection, whose 186 s hold 140 worm re-creations. Named rather
# than picked by position: "the longest tape" silently became a different map the first
# time the vault grew, and studies/tape T7 records that costing a run.
LIVE_CAPTURE = "20260807T143055"
LAKESIDE = "10.0.0.210:64103"

WORM_MODEL = 0x200005A2          # monster class nibble | definition 1442
CREATE = 0x0020
REMOVE = 0x0021
EFFECTS = 0x00F1
INITIAL_EFFECTS = 0x00F0

# Decoded value lists always begin with the RAW HEADER -- codec.decode_one appends it
# for the msg_header field -- so an agent id is at index 1 and never at 0. The first
# version of this file read agent ids at index 0 throughout and found zero worms in a
# tape containing 140, because index 0 is the constant 0x0020. Same class of mistake as
# test_rotate.py pairing against a position vec2. Both are now pinned by a check that
# reads the schema, so a layout change breaks the test instead of silently emptying it.
V_AGENT = 1                      # 0x0020 / 0x0021 / 0x00F0 / 0x00F1
V_MODEL = 2                      # 0x0020 only
V_POS = 5                        # 0x0020 only
V_EFFECT = 2                     # 0x00F0 / 0x00F1

# Measured 2026-08-10 over the two Lakeside tapes. Held slightly under the real counts
# so ordinary decode churn does not go red, while the SHAPE claim stays absolute: the
# burst census must return exactly one shape, with no exceptions at all.
MIN_WORM_CREATES = 120
TRANSITION_SECONDS = 2.00
TRANSITION_TOLERANCE = 0.08      # the capture's own spread is +/-60 ms

# 25 from the green run of 2026-08-11: 24 as before, plus the byte-accounting check
# section 2 gained when it moved onto tape.decode_all. Section 2 is the only one that
# can skip, and it takes the floor with it -- the same call test_rotate.py makes: a
# claim about ArenaNet's bytes that did not read ArenaNet's bytes has not been checked,
# and a green exit code would say otherwise.
LEDGER = checks.Ledger("burrowing", floor=25)


class FakeSend:
    """Records (opcode, values, label) instead of encrypting anything."""

    def __init__(self):
        self.sent = []

    def __call__(self, opcode, values, label="", quiet=False):
        self.sent.append((opcode, list(values), label))

    def opcodes(self):
        return [op for op, _v, _l in self.sent]

    def clear(self):
        self.sent = []


def make_entry(agent_id=10, burrow=True, out=0.05, hidden=0.05):
    entry = {
        "pos": (100.0, 200.0), "plane": 0,
        "health": 100.0, "max_health": 100.0, "dead": False,
        "name": "test", "npc": agents.HATCHER, "definition": 3,
        "allegiance": agents.ALLEGIANCE_HOSTILE,
        "attack_speed": agents.ATTACK_SPEED["axe"], "effects": 0,
    }
    if burrow:
        entry.update({
            "burrow_phase": authsrv.BURROW_EMERGING,
            "burrow_at": 0.0,
            "burrow_out_seconds": out,
            "burrow_hidden_seconds": hidden,
            "effects": agents.EFFECT_TRANSITION,
        })
    return entry


# ------------------------------------------------------- 1. the create/remove guard
def section_guard():
    send = FakeSend()
    state = {}
    entry = make_entry(burrow=False)
    authsrv.create_agent_world(send, state, 10, entry, "first")
    LEDGER.ok(10 in state["agents"],
              "create_agent_world puts the agent in state['agents'], not only on the wire",
              "the whole point: spawn_enemy used to do the state write as a bare "
              "assignment while remove_agent guarded its side")

    ops = send.opcodes()
    LEDGER.ok(ops[:3] == [authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES,
                          authsrv.GAME_SMSG_MONSTER_COMPOSITE,
                          authsrv.GAME_SMSG_WORLD_CREATE_AGENT],
              "the definition still precedes the agent that uses it",
              f"{[hex(o) for o in ops]} -- the definition index is a raw array index "
              "on the client and an undefined one crashes it outright")

    try:
        authsrv.create_agent_world(send, state, 10, make_entry(burrow=False), "again")
        refused = False
    except authsrv.AgentLifetimeError:
        refused = True
    LEDGER.ok(refused,
              "and creating over an id that is already live is REFUSED",
              "symmetric to remove_agent's two refusals; without it a re-create over "
              "a live id leaves the client holding one agent's state under another's "
              "name and nothing on the wire says so")

    # The other direction: a create that reaches the wire but not the state is exactly
    # what makes the NEXT remove raise. Prove remove_agent really would raise, so the
    # guard above is protecting against something real rather than something imagined.
    n_before = len(send.sent)
    try:
        authsrv.remove_agent(send, state, 999, "never created")
        raised = False
    except authsrv.AgentLifetimeError:
        raised = True
    LEDGER.ok(raised and len(send.sent) == n_before,
              "removing an id that is not in the world raises and sends NOTHING",
              "this is the exception a forgotten state write would hit, from inside "
              "the world-tick daemon thread")

    entry_back = authsrv.remove_agent(send, state, 10, "burrowed")
    LEDGER.ok(entry_back is entry and 10 not in state["agents"],
              "remove_agent hands back the entry, which is where a hidden agent lives",
              "its docstring promised this for 'a caller respawning the same id'; "
              "burrow_tick is the first caller that actually is one")

    authsrv.create_agent_world(send, state, 10, entry_back, "re-created")
    LEDGER.ok(10 in state["agents"] and state["agents"][10] is entry,
              "and the same id can then be re-created -- D1's finding, in code",
              "a removed id is not poisoned (25701dd), so reuse needs nothing beyond "
              "the ordinary burst")


# ------------------------------------------------------- 2. ArenaNet's own bytes
def worm_events(codec):
    """([(t, opcode, values)], receipt) for the Lakeside tape, or None if it is absent.

    DECODES THE TAPE WHOLE. Until 2026-08-11 this framed each event separately, which
    is wrong for the reason `tape.decode_all` documents at length: a tape event is one
    TCP segment, a message can straddle two, and the old idiom both dropped the rest of
    the segment behind a straddle and invented opcodes out of the next segment's
    mid-message head. On THIS tape it read 3,500 messages where the stream holds 3,604,
    among them five fictitious 0x0000s and a missing 0x0059 PLAYER_INFO.

    The worm counts happen not to move -- 140 creates across 13 ids either way, because
    the 0x0020s it lost were players rather than worms -- and that is worth stating
    rather than leaving implied: this file's headline numbers were never wrong, they
    were right by luck, and the surrounding census could have gone either way.

    Hands the receipt back rather than swallowing it. `strict=False` so a tape that
    stops framing becomes a RED CHECK naming the shortfall instead of an exception, and
    never a skip -- a skip here would say "no capture on this machine", which would be
    a lie about a capture that is right there and no longer parses.
    """
    try:
        root = vaultpath.vault_path("captures", "live", LIVE_CAPTURE)
    except Exception:
        return None
    if not os.path.isdir(root):
        return None
    # Resolve the client port to the full "client->server" key rather than hardcoding
    # the whole string: the server address is ArenaNet's and there is no reason for us
    # to depend on it. Refuse an ambiguous match instead of taking the first -- picking
    # a tape by position is exactly what studies/tape T7 records costing a run.
    matches = [c["connection"] for c in tape.channel_files(root)
               if c["connection"].startswith(LAKESIDE + "->")]
    if len(matches) != 1:
        return None
    try:
        _info, events = tape.load_tape(root, matches[0])
    except Exception:
        return None
    return tape.decode_all(events, codec, "GAME_SMSG", strict=False)


def section_capture(codec):
    # Pin the indices this whole section reads by. Without it, a schema change turns
    # every count below into 0 and every "all(...)" into a vacuous pass.
    c20 = [f["type"] for f in codec.fields_for("GAME_SMSG", CREATE)]
    cf0 = [f["type"] for f in codec.fields_for("GAME_SMSG", INITIAL_EFFECTS)]
    LEDGER.ok(c20[0] == "msg_header" and c20[V_MODEL] == "dword"
              and c20[V_POS] == "vec2"
              and cf0 == ["msg_header", "agent_id", "dword"],
              "the create/effects layouts still put agent, model and position where "
              "this section reads them",
              f"0x0020[{V_AGENT},{V_MODEL},{V_POS}] of {len(c20)} fields, "
              f"0x00F0 {cf0} -- index 0 is the raw header on every message")

    loaded = worm_events(codec)
    if not loaded:
        LEDGER.skip("ArenaNet's own burrow bytes",
                    f"no live capture {LIVE_CAPTURE} / {LAKESIDE} on this machine -- "
                    "the burst shape and the 2.00 s windows went unmeasured")
        return
    events, receipt = loaded

    # Everything below counts messages, so the first claim has to be that the count is
    # of the whole tape. This is the check the old per-event idiom could never fail: it
    # threw the error away, so a tape framed 97% of the way through looked complete and
    # every census beneath it was quietly short.
    LEDGER.ok(receipt.err is None and receipt.consumed == receipt.total,
              "the tape frames end to end, so the counts below are of ALL of it",
              f"{receipt.consumed:,}/{receipt.total:,} bytes, err={receipt.err!r}, "
              f"{len(events):,} messages -- per-EVENT decoding read 3,500 of these "
              f"3,604 and invented five 0x0000s, because a message can straddle a TCP "
              f"segment boundary and the segment after one starts mid-message")

    # Which agent ids are worms: the three-part signature, not "created more than once".
    # That distinction is load-bearing -- the Ascalon OUTPOST tape has 53 multi-create
    # ids and most of them are players walking in and out of range.
    worms = {v[V_AGENT] for _t, op, v in events
             if op == CREATE and v[V_MODEL] == WORM_MODEL}
    creates = [(t, v[V_AGENT]) for t, op, v in events
               if op == CREATE and v[V_MODEL] == WORM_MODEL]
    LEDGER.ok(len(creates) >= MIN_WORM_CREATES and len(worms) >= 10,
              "the tape still holds the worm population it was measured on",
              f"{len(creates)} creates across {len(worms)} worm ids "
              f"(floor {MIN_WORM_CREATES}/10)")

    # The burst shape. Walk each create and collect every message naming that agent in
    # a small window around it, ignoring the 20 Hz world tick.
    shapes = {}
    for i, (_t, op, v) in enumerate(events):
        if op != CREATE or v[V_MODEL] != WORM_MODEL:
            continue
        agent = v[V_AGENT]
        shape = []
        for j in range(max(0, i - 3), min(len(events), i + 4)):
            _tj, opj, vj = events[j]
            if opj == 0x001E:
                continue
            named = len(vj) > V_AGENT and (vj[V_AGENT] == agent
                                          or (len(vj) > 2 and vj[2] == agent))
            if named:
                shape.append(hex(opj))
        shapes[tuple(shape)] = shapes.get(tuple(shape), 0) + 1
    LEDGER.ok(len(shapes) == 1,
              "every worm create is the SAME burst -- one shape, no exceptions",
              f"{ {k: v for k, v in shapes.items()} } -- PLAN and studies/tape T3 both "
              "said this 'runs entirely through 0x0020/0x0021'; it is five messages")
    shape = next(iter(shapes))
    LEDGER.ok(len(shape) == 5 and shape[2] == hex(CREATE)
              and hex(INITIAL_EFFECTS) in shape,
              "and the burst is five messages with 0x00F0 among them",
              f"{list(shape)} -- 0x00F0 is D2, the highest-count message our server "
              "has never sent")

    f0 = {tuple(v) for _t, op, v in events
          if op == INITIAL_EFFECTS and v[V_AGENT] in worms}
    LEDGER.ok(f0 and all(v[V_EFFECT] == agents.EFFECT_TRANSITION for v in f0),
              "0x00F0 carries EFFECT_TRANSITION on every worm create",
              f"{sorted({hex(v[V_EFFECT]) for v in f0})} of {len(f0)} distinct -- 0x{agents.EFFECT_TRANSITION:04X}")

    # The two fixed windows. Everything else about the cycle varies; these do not.
    emerge, submerge = [], []
    for agent in worms:
        times = [(t, op, v) for t, op, v in events
                 if len(v) > V_AGENT and v[V_AGENT] == agent
                 and op in (CREATE, REMOVE, EFFECTS)]
        for i, (t, op, v) in enumerate(times):
            if op == EFFECTS and v[V_EFFECT] == 0:
                prev = [p for p in times[:i] if p[1] == CREATE]
                if prev:
                    emerge.append(t - prev[-1][0])
            elif op == EFFECTS and v[V_EFFECT] == agents.EFFECT_TRANSITION:
                nxt = [p for p in times[i + 1:] if p[1] == REMOVE]
                if nxt:
                    submerge.append(nxt[0][0] - t)
    ok_e = emerge and all(abs(d - TRANSITION_SECONDS) <= TRANSITION_TOLERANCE
                          for d in emerge)
    ok_s = submerge and all(abs(d - TRANSITION_SECONDS) <= TRANSITION_TOLERANCE
                            for d in submerge)
    LEDGER.ok(ok_e and ok_s,
              "the two transition windows are 2.00 s, every sample",
              f"emerge n={len(emerge)} "
              f"[{min(emerge):.3f}, {max(emerge):.3f}], submerge n={len(submerge)} "
              f"[{min(submerge):.3f}, {max(submerge):.3f}] -- the ONLY fixed numbers "
              "in the mechanic; out and hidden are not periods at all")

    # Every worm re-emerges where it went down. The wiki predicts this independently
    # (a submerged worm cannot move), which is the kind of agreement worth recording.
    spots = {}
    for _t, op, v in events:
        if op == CREATE and v[V_MODEL] == WORM_MODEL:
            pos = tuple(v[V_POS]) if isinstance(v[V_POS], (list, tuple)) else None
            spots.setdefault(v[V_AGENT], set()).add(pos)
    LEDGER.ok(spots and all(len(s) == 1 for s in spots.values()),
              "and each worm re-emerges at byte-identical coordinates",
              f"{sum(len(s) for s in spots.values())} distinct positions across "
              f"{len(spots)} worms -- one apiece")


# ------------------------------------------------------- 3. our own cycle
def section_cycle():
    # The two transition constants are the measured ones and a real cycle therefore
    # takes over four seconds of wall clock. Drive the phase machine with them shrunk
    # to zero and assert their REAL values separately -- a test that slept for the
    # honest duration would be four seconds of suite time buying nothing, and one that
    # quietly redefined them without saying so would be asserting a fiction.
    LEDGER.ok(authsrv.BURROW_EMERGE_SECONDS == TRANSITION_SECONDS
              and authsrv.BURROW_SUBMERGE_SECONDS == TRANSITION_SECONDS,
              "the server's transition constants are the measured 2.00 s",
              f"emerge {authsrv.BURROW_EMERGE_SECONDS}, "
              f"submerge {authsrv.BURROW_SUBMERGE_SECONDS} -- section 2 checks these "
              "against the capture they came from")
    real = (authsrv.BURROW_EMERGE_SECONDS, authsrv.BURROW_SUBMERGE_SECONDS)
    authsrv.BURROW_EMERGE_SECONDS = authsrv.BURROW_SUBMERGE_SECONDS = 0.0
    try:
        _drive_cycle()
    finally:
        authsrv.BURROW_EMERGE_SECONDS, authsrv.BURROW_SUBMERGE_SECONDS = real


def _drive_cycle():
    send = FakeSend()
    state = {"agents": {}}
    # A small non-zero hidden dwell. With zero, burrow_tick's two loops run in the SAME
    # call -- submerge pops the agent and the hidden sweep immediately re-creates it --
    # so the HIDDEN phase is real but never observable from outside. Asserting on WHERE
    # the agent lives is the better check anyway: the label is bookkeeping, the dict it
    # is in is the thing a live session depends on.
    entry = make_entry(out=0.0, hidden=0.02)
    authsrv.create_agent_world(send, state, 10, entry, "spawn")
    send.clear()

    seen, places = [], []
    for _ in range(12):
        authsrv.burrow_tick(send, state, None)
        here = state["agents"].get(10) or state.get("hidden", {}).get(10) or {}
        seen.append(here.get("burrow_phase"))
        places.append("world" if 10 in state["agents"]
                      else "hidden" if 10 in state.get("hidden", {}) else "gone")
        time.sleep(0.005)
    LEDGER.ok(authsrv.BURROW_OUT in seen and authsrv.BURROW_SUBMERGING in seen
              and "hidden" in places and "world" in places
              and "gone" not in places,
              "the cycle runs emerging -> out -> submerging -> hidden -> emerging",
              f"phases {seen}; whereabouts {places} -- 'gone' would mean an agent that "
              "left state['agents'] and never reached state['hidden'], which is the "
              "leak that makes the next remove raise inside the world tick")

    ops = send.opcodes()
    LEDGER.ok(REMOVE in ops and CREATE in ops and INITIAL_EFFECTS in ops,
              "and it removes, re-creates, and sends the initial-effects message",
              f"{sorted({hex(o) for o in ops})}")

    # The transition bit must be SET on the way down and CLEAR while out -- the thing
    # that makes EFFECT_TRANSITION the honest name rather than EFFECT_BURROWED.
    effect_values = [v[1] for op, v, _l in send.sent if op == EFFECTS]
    LEDGER.ok(0 in effect_values and agents.EFFECT_TRANSITION in effect_values,
              "the transition bit is cleared coming up and set going down",
              f"{[hex(v) for v in effect_values]} -- set during BOTH transitions and "
              "clear while the agent is out, which is why it is not named 'burrowed'")

    # `== ` alone would pass at 0 == 0, which is what this check did on its first run
    # while the cycle was stalled and nothing had been created at all. Require a
    # re-create to have actually happened before comparing the counts.
    n_def = ops.count(authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES)
    n_new = ops.count(CREATE)
    LEDGER.ok(n_new >= 1 and n_def == 0,
              "and NO re-create resends the NPC definition",
              f"{n_def} definitions for {n_new} creates. This check asserted the "
              "OPPOSITE until 2026-08-11 and said so in its own message: resending was "
              "the side whose failure mode is not a client assert, and the `burrow` "
              "probe was what would settle it. It ran (studies/enemy/PLAN.md 10.8): our "
              "Hatcher was removed and re-created twice with no 0x0056/0x0057 -- same "
              "id, then a fresh id -- and both drew a correct collector. A definition is "
              "per-INSTANCE. The FIRST create still declares; only re-creates skip it, "
              "and this cycle starts from an already-declared agent.")

    # AND THE ESCAPE HATCH IS REAL, which it was not when the comment promising it
    # shipped. `burrow_tick` reads entry.get("resend_definition", False), and `entry`
    # is a closed literal built in spawn_enemy -- so until ENEMY_RESEND_DEFINITION was
    # added, a `resend_definition = true` in content/world.toml loaded silently, never
    # reached `entry`, and left the operator believing they had restored the old
    # behaviour while the client still died on Array.h's `index < m_count`. The
    # documented mitigation for a SILENT client assert must not itself be silent.
    sendh = FakeSend()
    stateh = {"agents": {}}
    hatch = make_entry(out=0.0, hidden=0.02)
    hatch["resend_definition"] = True
    authsrv.create_agent_world(sendh, stateh, 12, hatch, "spawn")
    sendh.clear()
    for _ in range(12):
        authsrv.burrow_tick(sendh, stateh, None)
        time.sleep(0.005)
    ops_h = sendh.opcodes()
    h_def = ops_h.count(authsrv.GAME_SMSG_NPC_UPDATE_PROPERTIES)
    h_new = ops_h.count(CREATE)
    LEDGER.ok(h_new >= 1 and h_def == h_new,
              "but resend_definition=True on the entry brings the definition back",
              f"{h_def} definitions for {h_new} creates with the hatch set, against "
              f"{n_def} for {n_new} without it -- the two runs differ only in that key")

    # And the key has to be able to GET there from content, which is the half that was
    # missing: spawn_enemy builds `entry` and only names it copies survive.
    LEDGER.ok("resend_definition" in inspect.getsource(authsrv.spawn_enemy),
              "and spawn_enemy carries the key from the content row into the entry",
              "without that line the hatch is unreachable from content/world.toml no "
              "matter what an operator writes there -- the key loads, and stops at a "
              "dict literal that never names it")

    # A dead agent does not burrow. If it did, remove_agent would pop the corpse out of
    # state['agents'] and revive_due -- which only ever walks that dict -- could never
    # stand it back up. The agent would simply never return.
    send2 = FakeSend()
    state2 = {"agents": {}}
    dead = make_entry(out=0.0, hidden=0.0)
    authsrv.create_agent_world(send2, state2, 11, dead, "spawn")
    dead["dead"] = True
    dead["burrow_phase"] = authsrv.BURROW_OUT
    dead["burrow_at"] = 0.0
    send2.clear()
    for _ in range(4):
        authsrv.burrow_tick(send2, state2, None)
    LEDGER.ok(11 in state2["agents"] and not send2.sent,
              "a DEAD agent does not burrow, and nothing goes on the wire for it",
              "otherwise the corpse leaves state['agents'] with its revive timer "
              "pending and revive_due can never see it again")


def main():
    codec = Codec()
    print("\n1. the create/remove guard")
    section_guard()
    print("\n2. ArenaNet's own burrow bytes")
    section_capture(codec)
    print("\n3. our own cycle")
    section_cycle()
    print("\n4. a tape that hands the client on must hang up")
    section_transfer_close(codec)
    return LEDGER.verdict()


def section_transfer_close(codec):
    """The close that R1.5 chaining needs, and the one it must NOT do.

    OBSERVED 2026-08-10 from build 38797: the 0x01A5 handler at 0x0084f290 branches on
    bit 0x20 of [esi+0x190] -- clear means dial now, set means stash and wait -- and the
    connect function 0x850df0 sets that bit itself at 0x00850e56. So exactly one
    game-channel transfer per session dials immediately and every later one defers until
    the connection it already holds goes away. The recorded server hangs up 0.14 s after
    each handoff; ours did not, and hop 3 of the first chained run sat on a loading
    screen with the right address on it and never opened a socket.

    Both directions matter. Hanging up on a tape that does NOT transfer would break the
    last hop and every --tape-no-transfer run, whose entire purpose is that the client
    keeps playing afterwards.
    """
    import socket as _socket

    class FakeSock:
        """Records HOW it was closed, because that is the part that matters.

        A deferred transfer is released only by the reason code a clean shutdown
        produces (the client's own dispatch: reason 0 re-dials at 0x008515b7, reason >= 3
        does nothing). shutdown(SHUT_RDWR) with bytes still unread makes Windows send an
        RST instead of a FIN, which is a different reason code -- so this fake asserts the
        half-close and the drain rather than merely that close() happened.
        """

        def __init__(self, pending=(b"\x80\x08", b"")):
            self.how = None
            self.closed = False
            self.timeout = None
            self._pending = list(pending)

        def shutdown(self, how):
            self.how = how

        def settimeout(self, t):
            self.timeout = t

        def recv(self, _n):
            return self._pending.pop(0) if self._pending else b""

        def close(self):
            self.closed = True

    try:
        cap = vaultpath.vault_path("captures", "live", "20260807T143055")
        have = os.path.isdir(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("transfer close", "no live capture in this vault")
        return

    order = tape.chain(cap)
    _i, linking = tape.load_tape(cap, order[0])      # ends in a handoff
    _j, last = tape.load_tape(cap, order[-1])        # stays in its map

    s1 = FakeSock()
    closed1 = authsrv.close_after_transfer(s1, linking, codec, 1)
    LEDGER.ok(closed1 and s1.closed,
              "a tape ending in a handoff closes the connection",
              "the client DEFERS a second transfer while it still holds a game "
              "connection (bit 0x20 at +0x190, set by the connect at 0x850df0), so "
              "holding the socket open is what left hop 3 on a loading screen")
    LEDGER.ok(s1.how == _socket.SHUT_WR and s1.timeout is not None,
              "and it HALF-closes and drains, rather than shutting both ways",
              f"how={s1.how} (SHUT_WR={_socket.SHUT_WR}) -- SHUT_RDWR with bytes still "
              "unread makes Windows send an RST, and the client only re-dials on the "
              "reason code a clean FIN produces: reason 0 reaches the connect at "
              "0x008515b7, reason >= 3 returns and does nothing")

    s2 = FakeSock()
    closed2 = authsrv.close_after_transfer(s2, last, codec, 1)
    LEDGER.ok(not closed2 and not s2.closed,
              "and a tape with NO handoff is left alone",
              "the last hop and every --tape-no-transfer run exist so the client keeps "
              "playing after the tape -- hanging up on those would break the labelled "
              "run, which is the whole reason stop_before_transfer exists")


if __name__ == "__main__":
    sys.exit(main())
