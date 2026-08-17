#!/usr/bin/env python3
"""The labelled BEHAVIOUR run: what the monster did, windowed by what the operator did.

    python toolkit/authsrv/behaviourrun.py --narrate <outdir>    # during the session
    python toolkit/authsrv/behaviourrun.py <stamp>               # after it
    python toolkit/authsrv/behaviourrun.py --preflight           # before the first one

Sibling to `labelrun.py`, and the difference is the whole point. `labelrun` labels the
PLAYER's own traffic: a human is told to do one thing, the messages in that window are
attributed to it, and what is being named is a GAME_CMSG opcode. This labels the
MONSTER's behaviour instead -- the windows are the same idiom, but the thing being
measured is on the server's half of the wire and was produced by an AI nobody here can
read. studies/monsterai/FINDINGS.md is the study that says why: monster AI is not shipped
in the client and is never transmitted, so its OUTPUT on the wire is the only surface
there is.

THE THREE THINGS THIS REFUSES TO DO, each because something already went wrong:

  * **It never estimates a position.** A subject that moved between its create and its
    first reaction is UNRESOLVED, not interpolated. The first pass at the live corpus
    estimated four separation distances by zero-order hold; two were wrong by 481 and
    1,594 units, and the resulting "monsters strike from 269-1594 units" band was refuted
    outright. A subject qualifies iff it sent ZERO 0x0029, ZERO 0x002A and ZERO 0x002B in
    that interval, in which case its position is exactly its create coordinate and no
    estimate is involved. See FINDINGS §6 items 5, 6 and 7.
  * **It never pools across model ids.** One creature model closes to ~65 units before
    striking; two others strike from ~599 and ~706 without closing. Pooling those three
    produced the refuted band above. Every row carries its model id and any summary that
    would merge them is withheld with a named reason.
  * **It never reports a control window as clean without checking the right predicate.**
    On our own server a control predicts NO TRAFFIC. Against ArenaNet the world keeps
    talking -- 0x001E alone is roughly a third of the server stream -- so a no-traffic
    predicate reddens in every window, and a check that always reddens is as useless as
    one that never does. The live control is a predicate on the CLIENT half only.

standard library only.
"""
import argparse
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))

import agents  # noqa: E402
import checks  # noqa: E402
import origin  # noqa: E402

CMSG_MASK = 0x8000

# ---------------------------------------------------------------------------
# The opcodes the control predicate is written in terms of.
#
# PLAYER ACTIONS: the client only sends these because a person did something. Their
# presence in a control window means the marks and the messages disagree about when the
# operator's hands were on the keyboard, and no number from that run may be named.
PLAYER_ACTION = {
    0x0026,   # ATTACK_AGENT
    0x0027,   # attack-skill  (a Ranger's Power Shot leaves on this, not 0x0046)
    0x0039,   # movement
    0x003D,   # self position / heading
    0x003E,   # movement stop
    0x0046,   # USE_SKILL
    0x00C1,   # TARGET_SELECT
}
# PERMITTED IN A CONTROL, and COUNTED rather than ignored: a keepalive is the client
# breathing, and a ping reply is it answering. Counting them is what distinguishes "the
# operator held still" from "the client was gone".
CONTROL_PERMITTED = {0x0009, 0x0092}

TICK = 0x001E                # WORLD_SIMULATION_TICK: payload is elapsed milliseconds
CREATE = 0x0020              # WORLD_CREATE_AGENT
MOVE_TO_POINT = 0x0029
UPDATE_DESTINATION = 0x002A
UPDATE_SPEED = 0x002B
UPDATE_ROTATION = 0x002E
CHAT = 0x0064                # GAME_CMSG CHAT_SEND, the in-band mark channel
INT_TARGET = 0x00A0          # value 4 = attack_started; slot 1 is the ATTACKER

# A subject that emitted any of these between its create and its first reaction MOVED,
# and its position at the reaction is therefore unknown. Not estimated. Withheld.
MOVEMENT_OPS = (MOVE_TO_POINT, UPDATE_DESTINATION, UPDATE_SPEED)

TICK_BOUND_MS = 50.0         # the same bound test_smsgnames.py section 1 uses


class Step:
    """One prompted action, its window, and whether it is a control.

    `control` carries the distinction labelrun learned the hard way: a control predicts
    the operator did NOTHING, so traffic there voids the run; an ordinary step predicting
    silence is a HYPOTHESIS, and traffic there is a finding. Reporting the second as the
    first told an operator to throw away a run that had just refuted a prediction.
    """

    def __init__(self, key, prompt, seconds, why="", control=False):
        if seconds <= 0:
            raise ValueError(f"{key}: seconds must be positive")
        self.key, self.prompt, self.seconds = key, prompt, seconds
        self.why, self.control = why, control


# THE OPERATOR SCRIPT (studies/monsterai §7.2). Written for the person at the keyboard:
# one short imperative sentence each, rationale in `why` where only a reader of this file
# sees it. labelrun's operator said of an earlier draft "what the hell are these
# instructions" when the rationale was in the prompt.
#
# THE WHOLE SESSION MUST READ AS ORDINARY PLAY, because it IS ordinary play -- that is the
# behavioural control that actually protects the account, and no code here substitutes for
# it. Step 7 exists for that reason and is deliberately not analysed.
STEPS = [
    Step("mark_smoke",
         "Type two short chat lines, anything at all.", 30,
         why="Settles whether the in-band mark channel EXISTS. CHAT_SEND appears ZERO "
             "times in capture B's 500 client messages, so this is a stated prediction "
             "and not an assumption: if no chat reaches the game channel, the in-band "
             "half of the clock binding does not exist and the analyser must say so "
             "rather than proceed on one unchecked channel."),
    Step("idle_a",
         "Stand still where a creature is visible. Hands off the keyboard.", 45,
         control=True,
         why="The ONLY thing that can answer whether monster movement correlates with "
             "the player at all. Ambient patrol with a known-motionless player is the "
             "null model every aggro number is scored against."),
    Step("approach",
         "Pick a creature nothing has touched. Close in bursts: run ~1s, stand ~3s. "
         "STOP the instant it reacts.", 90,
         why="Forced by measurement rather than taste. The client's self-position "
             "arrives at median 0.501 s and p90 1.769 s, i.e. 144 u median and 509 u p90 "
             "of travel between fixes; a 50% error band cannot tell a per-creature aggro "
             "radius from a global one. Reacting while you STAND gives a point "
             "measurement; reacting mid-burst gives a bracket you sized yourself."),
    Step("retreat",
         "Do NOT fight it. Run straight back past where you started until it stops "
         "following, then stand 10s.", 60,
         why="The disengage question, which the entire existing corpus cannot speak to: "
             "it contains no case of a player walking away. All three outcomes are "
             "findings -- it turns for home, it stops where it stands, or it never "
             "stops."),
    Step("idle_b", "Stand still again. Hands off.", 30, control=True,
         why="Second ambient sample, and the control that catches a first one that was "
             "clean by luck."),
    Step("kill",
         "Fight a third creature to death. Stand still while you do it.", 120,
         why="A third declared attack speed is what separates 'windup scales with "
             "declared speed' from 'windup is per-creature and happens to track it' -- "
             "the confound §3.5 could not resolve with two. Also drops and corpse "
             "timing."),
    Step("narrate",
         "One chat line for each thing you saw that you cannot explain.", 30,
         why="Settles `band` and `anim` -- two allegiance tokens in the corpus that "
             "nothing in this repo can name -- in one session, for the cost of typing."),
    Step("play", "Play normally. Nothing here is analysed.", 180,
         why="Makes the session a session. NOT used for attribution, and the analyser "
             "drops it: a block of scripted-looking windows with nothing around them is "
             "the traffic pattern the behavioural rule is about."),
]

STEP_BY_KEY = {s.key: s for s in STEPS}


# ---------------------------------------------------------------------------
# Analysis. Every function here is PURE -- it takes decoded messages and returns
# findings -- so the test can build a session out of dicts and never touch the vault.
# ---------------------------------------------------------------------------

def window_steps(marks, first_key=None):
    """[(step_key, lo, hi)] in mark order, each window running to the NEXT mark.

    Messages before the first mark belong to the load, not to step 1. labelrun's own
    defect was the mirror of this: a mark written AFTER the prompt steals the first
    message of a step and hands it to the previous one, which is why the driver writes
    the mark BEFORE printing.
    """
    got = [m for m in marks if m.get("kind") == "mark"]
    out = []
    for i, m in enumerate(got):
        lo = m.get("wire_t")
        hi = got[i + 1].get("wire_t") if i + 1 < len(got) else float("inf")
        if lo is None:
            continue
        out.append((m.get("label"), lo, float("inf") if hi is None else hi))
    return out


def control_verdict(label, msgs):
    """(clean, detail) for one control window, on the CLIENT half only.

    A live control cannot predict silence -- ArenaNet's server talks throughout. What it
    predicts is that the OPERATOR did nothing, and that is a statement about client
    opcodes and nothing else.
    """
    actions = collections.Counter()
    permitted = collections.Counter()
    other = collections.Counter()
    for _t, op, _v in msgs:
        op &= ~CMSG_MASK
        if op in PLAYER_ACTION:
            actions[op] += 1
        elif op in CONTROL_PERMITTED:
            permitted[op] += 1
        else:
            other[op] += 1
    clean = not actions
    detail = (f"{sum(actions.values())} player-action message(s) "
              f"{ {hex(k): v for k, v in actions.items()} }; "
              f"permitted {sum(permitted.values())} "
              f"{ {hex(k): v for k, v in permitted.items()} }; "
              f"other client opcodes {sum(other.values())}")
    return clean, detail


def tick_drift(smsg):
    """(drift_ms, ratio) -- 0x001E's payload summed against the tape's own wire span.

    The check that says the wire clock and the server's own clock agree. Returns
    (None, None) when there are too few ticks to say anything, which is a real case for a
    very short connection and must not read as a pass.
    """
    ticks = [(t, v[1]) for t, op, v in smsg if op == TICK and len(v) > 1]
    if len(ticks) < 2:
        return None, None
    total = sum(v for _t, v in ticks[1:])         # the first covers time before it
    span = (ticks[-1][0] - ticks[0][0]) * 1000.0
    if span <= 0:
        return None, None
    return total - span, total / span


def encounters(smsg, player_agent=None):
    """One row per (model_id, agent_id) subject, with its position resolved or WITHHELD.

    A row is a dict:
        model      the create's definition/class field -- the thing you may NOT pool over
        agent      the wire agent id, per connection
        created_t  when it entered the world
        pos        its create coordinate
        moved      how many movement messages it sent before its first reaction
        reaction   (t, what) of the first thing it did, or None
        resolved   True iff `moved == 0`, i.e. the create coordinate is still its
                   position at the reaction. False means UNRESOLVED, not estimated.
    """
    born = {}
    order = []
    for t, op, v in smsg:
        if op == CREATE and len(v) > 5:
            agent = v[1]
            # v[0] is the opcode, so agents.create_agent's 23 payload fields sit at
            # v[1:] and the position TUPLE at v[5]. v[3:5] is (type, kind) = (1, 9)
            # on a real create, and this line read exactly that as a coordinate
            # until the Isle study caught it (studies/isle/PLAN.md 3.2).
            born[agent] = {"model": v[2], "agent": agent, "created_t": t,
                           "pos": tuple(v[5]), "moved": 0, "reaction": None,
                           "resolved": True}
            order.append(agent)
        elif op in MOVEMENT_OPS and len(v) > 1:
            row = born.get(v[1])
            if row is not None and row["reaction"] is None:
                row["moved"] += 1
        elif op == INT_TARGET and len(v) > 2 and v[1] == agents.GV_ATTACK_STARTED:
            row = born.get(v[2])
            if row is not None and row["reaction"] is None:
                row["reaction"] = (t, "attack_started")
    for a in order:
        row = born[a]
        row["resolved"] = row["moved"] == 0
    return [born[a] for a in order if a in born]


def separation(row, player_pos):
    """The subject-to-player distance at its reaction, or None when UNRESOLVED.

    None is the entire point. This returned a number for every row once, and two of the
    four it produced were wrong by 481 and 1,594 units because the subject had walked
    between the sample and the reaction.
    """
    if not row.get("resolved") or row.get("reaction") is None or player_pos is None:
        return None
    dx = row["pos"][0] - player_pos[0]
    dy = row["pos"][1] - player_pos[1]
    return (dx * dx + dy * dy) ** 0.5


def by_model(rows):
    """{model_id: [rows]} -- the ONLY grouping this module will summarise over."""
    out = collections.defaultdict(list)
    for r in rows:
        out[r["model"]].append(r)
    return dict(out)


def chat_marks(cmsg):
    """[(t, opcode)] for every in-band chat message the client sent.

    Step 0's whole purpose. If this is empty the in-band channel does not exist for this
    account/build and the analyser says so -- it does not quietly fall back to the
    out-of-band file and call the binding checked.
    """
    return [(t, op & ~CMSG_MASK) for t, op, _v in cmsg if (op & ~CMSG_MASK) == CHAT]


# ---------------------------------------------------------------------------
# Narration: the operator-facing half. Writes MARK files; sends NOTHING to the client.
# ---------------------------------------------------------------------------

def narrate(outdir, steps=STEPS, say=print, sleep=time.sleep,
            now=time.monotonic, wall=time.time,
            clock=time.perf_counter):
    """Walk the script, marking each step. THE DRIVER STILL SENDS NO INPUT.

    This writes a MARK file that `livesession._hold` picks up; it never touches the
    client. The operator reads a sentence and acts on it. That distinction is the rule
    that protects the account and no code here may erode it.

    THE MARK IS WRITTEN BEFORE THE PROMPT IS PRINTED, which is the defect labelrun
    records from the other side: a mark taken after the operator has been told what to do
    hands that step's first messages to the previous window.
    """
    markfile = os.path.join(outdir, "MARK")
    say("\n  THE SCRIPT. Read each line, do it, and let the timer run out.")
    say("  Nothing here is sent to the game -- you are the one playing.\n")
    for i, s in enumerate(steps, 1):
        # THREE LINES: the key, and the two clocks AT THE INSTANT THE MARK IS TAKEN.
        # The driver polls this file every 5 s, so a mark stamped when the driver
        # NOTICES it is late by up to that much -- coarser than the whole binding is
        # for, and it would never have looked wrong. The driver carries these through
        # and records the pickup lag separately.
        with open(markfile, "w", encoding="utf-8") as fh:
            fh.write("\n".join((s.key, repr(wall()), repr(clock()))) + "\n")
        tag = "  [CONTROL]" if s.control else ""
        say(f"  {i}/{len(steps)}  {s.key}{tag}  ({s.seconds}s)")
        say(f"        {s.prompt}")
        end = now() + s.seconds
        while now() < end:
            sleep(min(1.0, max(0.0, end - now())))
        say("")
    say("  script complete -- play on, or write STOP to end the session.\n")


# ---------------------------------------------------------------------------

def analyse(stamp, ledger, say=print):
    """The nine checks, against a real capture. Needs the vault."""
    import cmsgstream
    import tape as tapemod
    from codec import Codec

    cap = tapemod.resolve_capture(stamp)
    who, why = origin.origin_of(os.path.join(cap, "wire.jsonl"))
    ledger.ok(who == origin.LIVE,
              "1. the capture is ArenaNet's, not ours",
              f"origin={who} ({why}) -- a behaviour claim about monster AI made from our "
              "own server's traffic would be a claim about code we wrote")
    if who != origin.LIVE:
        ledger.skip("checks 2-9", "not a live capture; nothing below would mean anything")
        return

    # TWO dirnames: HERE is toolkit/authsrv, and the overrides live at the REPO root,
    # not under toolkit/. One dirname builds toolkit/schema/overrides.json, which does
    # not exist -- and a Codec with no overrides still decodes 1,913 messages of this
    # corpus before hitting a wall, which is precisely the "plausible, short, silently
    # wrong" decode tape.decode_all's strict mode refuses. It caught this.
    codec = Codec(overrides=os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                         "schema", "overrides.json"))
    clean = True
    for conn in tapemod.chain(cap):
        _meta, events = tapemod.load_tape(cap, conn)
        msgs, receipt = tapemod.decode_all(events, codec, channel="GAME_SMSG")
        ok = receipt[0] == receipt[1]
        clean = clean and ok
        drift, ratio = tick_drift(msgs)
        if drift is not None:
            ledger.ok(abs(drift) <= TICK_BOUND_MS,
                      f"3. the tick clock and the wire clock agree on {conn[:12]}",
                      f"{drift:+.1f} ms (ratio {ratio:.4f})")
    ledger.ok(clean, "2. every connection accounts for all of its bytes",
              "consumed == total, per connection")

    marks = []
    mpath = os.path.join(cap, "marks.jsonl")
    if os.path.exists(mpath):
        import wirecapture as wc
        marks = wc.read_marks(mpath)
    ledger.ok(bool(marks), "4. the capture carries a narration binding",
              f"{len(marks)} mark(s) -- an EMPTY marks.jsonl is a red flag rather than a "
              "neutral result: session_start and session_end are automatic")
    say(f"\n  {len(marks)} mark(s), {len(STEPS)} scripted steps")


def preflight(ledger, stamps=("20260807T143055", "20260810T235916")):
    """Check 3 against the captures ALREADY in the vault, before any new session.

    §7.3 asks for this explicitly and the reason is worth keeping: if the tick clock and
    the wire clock disagree on captures we already trust, the mapping every timed claim
    in this repo rests on is broken and the campaign is not the thing to fix first.
    """
    import tape as tapemod
    from codec import Codec
    # TWO dirnames: HERE is toolkit/authsrv, and the overrides live at the REPO root,
    # not under toolkit/. One dirname builds toolkit/schema/overrides.json, which does
    # not exist -- and a Codec with no overrides still decodes 1,913 messages of this
    # corpus before hitting a wall, which is precisely the "plausible, short, silently
    # wrong" decode tape.decode_all's strict mode refuses. It caught this.
    codec = Codec(overrides=os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                         "schema", "overrides.json"))
    worst, where = 0.0, None
    n = 0
    for stamp in stamps:
        cap = tapemod.resolve_capture(stamp)
        for conn in tapemod.chain(cap):
            _meta, events = tapemod.load_tape(cap, conn)
            msgs, _r = tapemod.decode_all(events, codec, channel="GAME_SMSG")
            drift, _ratio = tick_drift(msgs)
            if drift is None:
                continue
            n += 1
            if abs(drift) > abs(worst):
                worst, where = drift, f"{stamp} {conn[:12]}"
    ledger.ok(n > 0, "the preflight measured something",
              f"{n} connection(s) with enough ticks to say anything")
    ledger.ok(n > 0 and abs(worst) <= TICK_BOUND_MS,
              "the tick clock and the wire clock agree on the EXISTING corpus",
              f"worst {worst:+.1f} ms at {where} over {n} connections. If this is red, "
              f"the wire-clock-to-plaintext mapping is broken and every timed claim in "
              f"this repo is suspect -- fix that before spending a live session")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stamp", nargs="?", help="live capture stamp to analyse")
    ap.add_argument("--narrate", metavar="OUTDIR",
                    help="walk the operator script, writing MARK files")
    ap.add_argument("--preflight", action="store_true",
                    help="check the tick clock against the existing corpus")
    ap.add_argument("--script", action="store_true", help="print the script and exit")
    a = ap.parse_args(argv)

    if a.script:
        for i, s in enumerate(STEPS, 1):
            tag = "  [CONTROL]" if s.control else ""
            print(f"\n{i}. {s.key}{tag}  ({s.seconds}s)\n   {s.prompt}\n   why: {s.why}")
        return 0

    if a.narrate:
        narrate(a.narrate)
        return 0

    led = checks.Ledger("behaviourrun", floor=1)
    if a.preflight:
        preflight(led)
        return led.verdict()
    if not a.stamp:
        ap.error("give a stamp, --narrate, --preflight or --script")
    analyse(a.stamp, led)
    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
