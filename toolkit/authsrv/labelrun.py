"""A labelled input run: name client->server messages by watching a human send them.

THE GAP THIS EXISTS TO CLOSE. `schema/messages.json` carries field layouts for 194
GAME_CMSG opcodes and **names for none of them** -- authsrv.py's own dispatch says so at
the c2s print site ("No semantic names exist for GAME_CMSG in this repo yet; the schema
knows shapes only"). Our server names 11 by hand. Exactly 15 have ever been witnessed
coming out of a real client, all of them in one unplanned five minutes on 2026-08-10 when
the operator poked at a client after a tape ran out.

Those five minutes produced the strongest naming evidence in the repo -- `GAME_CMSG
0x0046` field 1 is a skill id, not a bar slot, because the operator named the two skills
they cast BEFORE anything was decoded and the client's own skill and string tables then
agreed (studies/tape/FINDINGS.md T4). This module is that method done on purpose.

HOW IT WORKS. Play a tape to get a populated world (or run the ordinary server), then
walk the operator through a numbered script printed to the gamesrv terminal -- the client
launches `-windowed`, so both are visible at once. Each step is recorded into the capture
as a `label_step` event the instant it is prompted, so a message is attributed to a step
BY TIMESTAMP against a mark the server wrote, not by inferring boundaries from gaps
afterwards. That distinction is the whole reason this is a tool and not a note in the
runbook: gap inference silently misaligns when a step produces nothing, and a step
producing nothing is a RESULT here, not an error.

WHAT IT CANNOT DO. Nothing answers. Under a tape the server is silent by construction
(studies/tape/FINDINGS.md T6), so these are the client's unanswered requests: what it
sends when it *wants* something, not what a completed action looks like. Multi-step
interactions that need a server reply to advance will stop after their first message, and
that is a real limit on steps like `gateway` and `item_move`.

THE OPERATOR CANNOT CLICK THIS WINDOW. Acting in the game needs the game focused, so the
prompts are read by glancing, never by clicking -- and that is why pacing is on a timer
rather than on a key press to advance. It also means the per-message c2s echo has to get
out of the way while a step is open; see ACTIVE below.

EVERY STEP STATES A PREDICTION, per the house rule, in the `expect` field -- SILENCE for
the ones we believe are client-side only, TRAFFIC otherwise. `analyse` reports agreement
and disagreement both, and the two idle steps are controls that can go red: if traffic
lands in a window where the operator was told to keep their hands off, the timestamps are
wrong and every other attribution in the run is suspect.

standard library only.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

# The client masks its opcodes; `rec.event("decoded", ...)` already stores them stripped,
# so this is defence against a future recorder that does not.
CMSG_MASK = 0x8000

# OBSERVED 2026-08-10 (studies/tape/FINDINGS.md T5): 37 sends at a dead-regular 5.0 s
# cadence over a 186 s run, independent of anything on screen. It lands in every window
# and means nothing about the step it lands in. It is REPORTED SEPARATELY, never dropped
# silently -- a filter you cannot see is a filter you cannot check.
KEEPALIVE = 0x0009

SILENCE, TRAFFIC = "silence", "traffic"


class Step:
    """One prompted action, and what we predict the client does about it."""

    def __init__(self, key, prompt, seconds, expect, why=""):
        if expect not in (SILENCE, TRAFFIC):
            raise ValueError(f"{key}: expect must be {SILENCE!r} or {TRAFFIC!r}")
        if seconds <= 0:
            raise ValueError(f"{key}: seconds must be positive")
        self.key, self.prompt, self.seconds = key, prompt, seconds
        self.expect, self.why = expect, why


# WRITTEN FOR THE OPERATOR, NOT FOR THE READER OF THIS FILE. The first draft put opcode
# rationale into the prompt itself, which made a 9-second window unreadable -- the
# operator's words were "what the hell are these instructions". The rationale moved to
# `why`, which the standalone script prints beforehand and the live run never shows; the
# prompt is now one short imperative sentence.
#
# TIMING is roughly 9-10 s, and that is FINE now that the window renders a countdown and
# a live message count -- the original complaint was legibility, not duration. The only
# long windows are the ones that involve typing. A step that ends before the operator
# finishes is indistinguishable in the data from an action that sends nothing, so where
# there was doubt the extra seconds went in.
#
# Ordered: controls at both ends, no-hunting actions before ones that need something on
# screen, and `gateway` LAST because it asks the client to leave the map -- the cage
# refuses the dial and that may end the connection.
STEPS = [
    Step("idle_a", "Do nothing. Hands off the mouse and keyboard.", 12, SILENCE,
         "Establishes the idle floor. Anything but keepalives here means the "
         "timestamps are wrong and the whole run is suspect."),
    Step("move_click", "Click the ground far away. Let your character walk.",
         10, TRAFFIC,
         "0x003E MOVE_TO_COORD is UPSTREAM-named and was CORROBORATED once; this "
         "isolates a click from held-key movement."),
    Step("move_hold", "Walk using the keyboard for a few seconds, then stop.",
         10, TRAFFIC,
         "0x003D carries position AND facing, which is what held-key movement should "
         "produce if the UPSTREAM name TURN_TO_DIRECTION is right."),
    Step("camera", "Rotate the camera only. Do not move your character.", 10, SILENCE,
         "Camera is believed client-side. A message here would be a find."),
    Step("target_tab", "Press Tab to target the nearest creature.", 9, TRAFFIC,
         "0x00C1 is the candidate target-select, and Tab gets it without needing "
         "anything under the cursor."),
    Step("target_clear", "Press Escape to drop the target.", 9, TRAFFIC,
         "Predicts 0x00C1 with agent id 0 -- the clear form seen 2026-08-10."),
    Step("attack", "Press Tab, then Space to attack it.", 10, TRAFFIC,
         "Tab first so this does not depend on a target surviving the previous step. "
         "0x0026 is the candidate attack/interact."),
    Step("skill_1", "Press 1.", 9, TRAFFIC, "0x0046 field 1."),
    Step("skill_2", "Press 2.", 9, TRAFFIC,
         "Field 1 must CHANGE between slots if it is a skill id, and must read 0,1 "
         "if it is a slot index. That is the refutation of T4."),
    Step("skill_8", "Press 8.", 9, TRAFFIC,
         "The far end of the bar -- a slot index would read 7 here, a skill id would "
         "not. Two adjacent slots could agree by coincidence; this one cannot."),
    Step("chat_say", "Press Enter, type   rurik one   and press Enter again.",
         18, TRAFFIC,
         "A known plaintext of known length -- the one step whose payload can be "
         "recognised in the bytes without decoding anything."),
    Step("emote_dance", "Press Enter, type   /dance   and press Enter again.",
         14, TRAFFIC,
         "Emotes are animation-only; whether they reach the server at all is unknown."),
    Step("inventory", "Press I to open your bags. Do not move anything.", 9, SILENCE,
         "Opening a bag is believed client-side."),
    Step("item_move", "Drag one item to an empty slot. Then press I to close.",
         16, TRAFFIC,
         "Inventory layout is server-authoritative in every MMO; this should send even "
         "with nothing answering."),
    Step("weapon_set", "Switch weapon sets, then switch back.", 10, TRAFFIC,
         "0x0148 ITEM_SET_ACTIVE_WEAPON_SET appears in the tape's s2c; this looks for "
         "the client's half of it."),
    Step("map_open", "Press M to open the world map, then close it.", 9, SILENCE,
         "Believed client-side."),
    Step("idle_b", "Do nothing. Hands off again.", 12, SILENCE,
         "The second control, and it matters more than the first: it proves the run "
         "was still quiet AFTER a dozen actions, so a late attribution is as "
         "trustworthy as an early one."),
    Step("gateway", "Walk into the zone exit. This may end the run.", 15, TRAFFIC,
         "The client will dial ArenaNet from a recorded GAME_SERVER_INFO and the cage "
         "will refuse it. Last on purpose."),
]


# Set while a step window is open, and read by authsrv's c2s print site. During a
# labelled run the per-message log is SUPPRESSED and counted instead. Not cosmetic: a
# movement step prints tens of lines a second, and the operator has to read a countdown
# in that same terminal. The messages still go to the capture -- this only affects what
# is echoed to the screen, and the count that replaces it is better feedback anyway,
# because it tells the operator their key press actually reached the server.
ACTIVE = False
SEEN = [0]


def run(rec, conn_id, stop, steps=STEPS, out=None, ready=6.0):
    """Prompt the operator through `steps`, marking each one into the capture.

    The mark is written BEFORE the prompt is printed, so a recorded window can only ever
    start early relative to what the operator saw -- never late. A late mark would steal
    the first message of a step and hand it to the previous one.

    `out` is for tests: pass a collector and the cursor rendering is skipped, so the
    output is deterministic lines instead of a live countdown.
    """
    global ACTIVE
    live = out is None
    say = out or (lambda s: print(s, flush=True))
    if live:
        say = lambda s: print(s, flush=True)  # noqa: E731
    bar = "=" * 68
    total = sum(s.seconds for s in steps) + ready
    say(f"\n{bar}\n"
        f"  LABELLED INPUT RUN -- {len(steps)} steps, about {total / 60:.0f} minutes\n"
        f"{bar}\n"
        f"  KEEP THE GAME WINDOW FOCUSED. Read these prompts by GLANCING at this\n"
        f"  window -- do not click on it, or your next click goes to the terminal\n"
        f"  instead of the game and the step records nothing.\n\n"
        f"  Each step shows a countdown and how many messages your input produced.\n"
        f"  Do the action ONCE and wait. If you miss one, let it go -- an empty\n"
        f"  step is a readable result; a rushed one done twice is not.\n\n"
        f"  Nothing will answer you. The server is silent by design, so this\n"
        f"  records what the client ASKS for, not what a finished action looks like.\n"
        f"{bar}")
    rec.event("label_run_start", steps=len(steps), keys=[s.key for s in steps])
    say(f"\n  starting in {ready:.0f}s -- get the game window focused now")
    if _hold(ready, stop, live, None):
        return False

    try:
        for i, step in enumerate(steps, 1):
            if stop.is_set():
                say(f"\n  stopped before step {i}/{len(steps)}")
                rec.event("label_run_stopped", at_index=i, at_key=step.key)
                return False
            SEEN[0] = 0
            rec.event("label_step", index=i, key=step.key, prompt=step.prompt,
                      seconds=step.seconds, expect=step.expect)
            ACTIVE = True
            nxt = steps[i].prompt if i < len(steps) else "(last step)"
            say(f"\n{bar}\n"
                f"  STEP {i} of {len(steps)}\n\n"
                f"      >>>  {step.prompt}\n\n"
                f"  next: {nxt}\n{bar}")
            stopped = _hold(step.seconds, stop, live, step)
            ACTIVE = False
            if not live:
                say(f"  ({SEEN[0]} message(s))")
            if stopped:
                say(f"\n  stopped during step {i}, {step.key}")
                rec.event("label_run_stopped", at_index=i, at_key=step.key)
                return False
    finally:
        ACTIVE = False

    rec.event("label_run_end", steps=len(steps))
    say(f"\n{bar}\n  DONE -- {len(steps)} steps recorded.\n\n"
        f"      python toolkit/authsrv/labelrun.py --analyse\n\n"
        f"  Check the idle_a and idle_b rows FIRST. If either shows traffic, the\n"
        f"  run cannot be used to name anything.\n{bar}")
    return True


def _hold(seconds, stop, live, step):
    """Wait out one window. True if stopped. Renders a countdown when `live`.

    Sleeps in slices so a Ctrl-C or a closed client lands within a fifth of a second
    rather than at the end of a 22-second step.
    """
    end = time.monotonic() + seconds
    last = None
    while True:
        now = time.monotonic()
        if stop.is_set():
            if live:
                sys.stdout.write("\r" + " " * 46 + "\r")
                sys.stdout.flush()
            return True
        if now >= end:
            break
        left = int(end - now) + 1
        if live and left != last:
            tag = f"  {left:>3}s" + (f"   messages: {SEEN[0]}" if step else "")
            sys.stdout.write("\r" + tag.ljust(46))
            sys.stdout.flush()
            last = left
        time.sleep(min(0.2, max(0.0, end - now)))
    if live:
        tail = f"  done   messages: {SEEN[0]}" if step else "  go"
        sys.stdout.write("\r" + tail.ljust(46) + "\n")
        sys.stdout.flush()
    return stop.is_set()


# ------------------------------------------------------------------ analysis ----

def load(path):
    """(marks, messages) from a gamesrv capture. Both lists are in timestamp order."""
    marks, msgs = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            k = r.get("kind")
            if k in ("label_step", "label_run_end", "label_run_stopped"):
                marks.append(r)
            elif k == "decoded":
                msgs.append(r)
    marks.sort(key=lambda r: r.get("t", 0.0))
    msgs.sort(key=lambda r: r.get("t", 0.0))
    return marks, msgs


def segment(marks, msgs):
    """[{step, opcodes, keepalives, messages}] -- one entry per prompted step.

    A step's window runs from its own mark to the NEXT mark, whatever that next mark is
    (another step, the end, or a stop). Messages before the first mark are returned
    separately rather than folded into step 1: they belong to the tape or the load, and
    quietly absorbing them would inflate the first action.
    """
    steps = [m for m in marks if m.get("kind") == "label_step"]
    if not steps:
        return [], msgs
    bounds = []
    for i, m in enumerate(steps):
        end = steps[i + 1]["t"] if i + 1 < len(steps) else None
        if end is None:
            closers = [x["t"] for x in marks
                       if x.get("kind") in ("label_run_end", "label_run_stopped")
                       and x.get("t", 0.0) >= m["t"]]
            end = min(closers) if closers else float("inf")
        bounds.append((m, m["t"], end))

    out, before = [], [r for r in msgs if r.get("t", 0.0) < steps[0]["t"]]
    for m, lo, hi in bounds:
        inside = [r for r in msgs if lo <= r.get("t", 0.0) < hi]
        opcodes, keepalives = {}, 0
        for r in inside:
            op = int(r.get("opcode", -1)) & ~CMSG_MASK
            if op == KEEPALIVE:
                keepalives += 1
                continue
            opcodes.setdefault(op, []).append(r)
        out.append({"step": m, "opcodes": opcodes, "keepalives": keepalives,
                    "messages": inside})
    return out, before


def report(segments, before, say=print):
    """Print the run, and return (violations, silent_steps) for a caller to act on."""
    say(f"\n{'step':>3} {'key':<14} {'expect':<8} {'n':>4} {'ka':>3}  opcodes")
    violations, silent = [], []
    for i, seg in enumerate(segments, 1):
        st = seg["step"]
        n = sum(len(v) for v in seg["opcodes"].values())
        ops = "  ".join(f"0x{op:04X}x{len(v)}"
                        for op, v in sorted(seg["opcodes"].items()))
        say(f"{i:>3} {st['key']:<14} {st['expect']:<8} {n:>4} {seg['keepalives']:>3}  "
            f"{ops or '--'}")
        if st["expect"] == SILENCE and n:
            violations.append((st["key"], n, ops))
        if st["expect"] == TRAFFIC and not n:
            silent.append(st["key"])

    if before:
        say(f"\n{len(before)} message(s) arrived BEFORE the first step and belong to no "
            f"action (tape / instance load). Not attributed.")
    if violations:
        say(f"\nPREDICTION REFUTED -- traffic in a window predicted SILENT:")
        for key, n, ops in violations:
            say(f"   {key}: {n} message(s)  {ops}")
        say("   For the two idle steps this is a CONTROL FAILURE: the operator was told\n"
            "   to keep their hands off, so either they did not, or the timestamps are\n"
            "   wrong and every attribution in this run is suspect. Do not name an\n"
            "   opcode from a run whose idle windows are dirty.")
    if silent:
        say(f"\nNo traffic at all from: {', '.join(silent)}")
        say("   Either the action is client-side, or it needs a server reply to send,\n"
            "   or the operator did not perform it. This tool cannot tell those apart.")
    return violations, silent


def main(argv=None):
    import argparse
    sys.path.insert(0, os.path.dirname(HERE))
    import vaultpath
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--analyse", "--analyze", dest="analyse", action="store_true",
                    help="analyse a capture instead of listing the script")
    ap.add_argument("capture", nargs="?",
                    help="gamesrv capture .jsonl; default: the newest")
    a = ap.parse_args(argv)

    if not a.analyse:
        total = sum(s.seconds for s in STEPS)
        print(f"{len(STEPS)} steps, {total:.0f}s ({total / 60:.1f} min)\n")
        for i, s in enumerate(STEPS, 1):
            print(f"{i:>3} {s.key:<14} {s.seconds:>4.0f}s  [{s.expect}]  {s.prompt}")
            if s.why:
                print(f"      why: {s.why}")
        return 0

    cap = a.capture
    if not cap:
        root = vaultpath.require_dir("captures", "gamesrv", why="analysing a label run")
        files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".jsonl")]
        if not files:
            print(f"no gamesrv captures in {root}")
            return 1
        cap = max(files, key=os.path.getmtime)
    print(f"capture: {os.path.basename(cap)}")
    marks, msgs = load(cap)
    segments, before = segment(marks, msgs)
    if not segments:
        print("no label_step marks in this capture -- was it run with --labelrun?")
        return 1
    violations, _silent = report(segments, before)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
