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

# OBSERVED 2026-08-10: a 5.0 s cadence that has nothing to do with what the operator is
# doing, so it means nothing about the window it lands in. It is COUNTED and reported
# separately, never dropped silently -- a filter you cannot see is a filter you cannot
# check, and that counting is what produced the correction below.
#
# CORRECTED the same day (studies/cmsg/FINDINGS.md section 3): it is NOT an unconditional
# heartbeat. All 37 sends in the labelled capture fall during the tape and ZERO fall in
# the three and a half minutes of play after it -- the client stops the moment the server
# goes silent. Our server will have to send something for a real client to keep sending
# this, which matters the day we stop replaying tapes.
KEEPALIVE = 0x0009

SILENCE, TRAFFIC = "silence", "traffic"


class Step:
    """One prompted action, and what we predict the client does about it.

    `control` separates the two very different reasons a step can predict SILENCE, and
    getting this wrong cost a real run its credibility on 2026-08-10:

      * A CONTROL (the idle steps) predicts silence because the operator was told to do
        NOTHING. Traffic there means the marks and the messages disagree, and no opcode
        from the run may be named.
      * An ORDINARY step predicting silence is a HYPOTHESIS -- "we think the camera is
        client-side". Traffic there REFUTES it, which is a finding and the entire point
        of running this.

    The first version reported both as "CONTROL FAILURE ... this run is suspect". The
    operator's camera step refuted a prediction, both idle windows were spotless, and
    the tool told them to throw the run away.
    """

    def __init__(self, key, prompt, seconds, expect, why="", control=False):
        if expect not in (SILENCE, TRAFFIC):
            raise ValueError(f"{key}: expect must be {SILENCE!r} or {TRAFFIC!r}")
        if seconds <= 0:
            raise ValueError(f"{key}: seconds must be positive")
        if control and expect != SILENCE:
            raise ValueError(f"{key}: a control must predict {SILENCE!r}")
        self.key, self.prompt, self.seconds = key, prompt, seconds
        self.expect, self.why, self.control = expect, why, control


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
COMBAT = [
    Step("idle_a", "Do nothing. Hands off the mouse and keyboard.", 12, SILENCE,
         "Establishes the idle floor. Anything but keepalives here means the "
         "timestamps are wrong and the whole run is suspect.", control=True),
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
    Step("target_tab", "Target the nearest creature (Tab, if that is bound).",
         9, TRAFFIC,
         "0x00C1 is the candidate target-select, and Tab gets it without needing "
         "anything under the cursor."),
    Step("target_clear", "Clear your target, however you normally do it.",
         9, TRAFFIC,
         "Predicts 0x00C1 with agent id 0. Deliberately does NOT name a key: this "
         "said 'press Escape' on 2026-08-10, Clear Target was UNBOUND on that "
         "keyboard, the operator clicked the nameplate button instead, and the "
         "window's three 0x0028 messages were very nearly attributed to a key "
         "nobody pressed. A prompt cannot know what is bound."),
    Step("attack", "Target something, then attack it.", 10, TRAFFIC,
         "0x0026 is the candidate attack/interact. Re-targeting first keeps this "
         "from depending on a target surviving the previous step -- and in a map "
         "full of burrowing worms, targets do not survive."),
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
         "trustworthy as an early one.", control=True),
    Step("gateway", "Walk into the zone exit. This may end the run.", 15, TRAFFIC,
         "The client will dial ArenaNet from a recorded GAME_SERVER_INFO and the cage "
         "will refuse it. Last on purpose."),
]


# THE TOWN SCRIPT. A script has to match the world the tape leaves behind, and the two
# tapes leave very different ones -- which is not a detail, it decides what can be asked:
#
#   Lakeside #2  25 agents, 11 NPC rows, ONE player, skillbar [153, 105, 0*6]
#   Ascalon City 45 agents, 19 NPC rows, 40 players,  skillbar [0]*8
#
# So skills can only be tested on the Lakeside tape (COMBAT above), and NPCs, merchants
# and other players only on the Ascalon one. Running the combat script against Ascalon
# would produce eight silent skill steps and read as "the client sends nothing for
# skills", which is false.
#
# THE QUESTION THIS SCRIPT EXISTS FOR: is 0x0026 *attack* or *interact*? On 2026-08-10 it
# was seen once, on a hostile worm, immediately after a target-select. Ascalon City is a
# town -- Guild Wars forbids attacking in one -- so the same gesture aimed at a friendly
# NPC either sends the same opcode (it is INTERACT) or a different one (it is ATTACK).
# That is a clean discriminator and it needs no new capture.
TOWN = [
    Step("idle_a", "Do nothing. Hands off the mouse and keyboard.", 12, SILENCE,
         "The idle floor, same as the combat script.", control=True),
    Step("camera", "Rotate the camera only. Do not move your character.", 10, TRAFFIC,
         "Predicts TRAFFIC now, not silence: the combat run refuted the client-side "
         "guess with 8 x 0x0040. This is the reproduction -- a refutation seen once "
         "in one map is a fact about one map."),
    Step("target_npc", "Click on an NPC to target it. Do not interact yet.",
         12, TRAFFIC,
         "Isolates the select from the act, so the next step's traffic is only the "
         "act. Expect 0x00C1 with the NPC's agent id."),
    Step("interact_npc", "Now interact with that NPC (talk to it).", 14, TRAFFIC,
         "THE DISCRIMINATOR. 0x0026 here means it is a general INTERACT; a different "
         "opcode means 0x0026 was ATTACK and this is its friendly counterpart. Either "
         "answer settles C4."),
    Step("target_player", "Click on another PLAYER to target them.", 12, TRAFFIC,
         "A third allegiance. If 0x00C1 is uniform across worm, NPC and player, it is "
         "target-select and nothing more."),
    Step("merchant", "Open a merchant or trader panel, then close it.", 20, TRAFFIC,
         "A panel that must be server-backed: prices and stock cannot be local. "
         "Nothing will answer, so expect the OPENING request only."),
    Step("emote_sit", "Press Enter, type   /sit   and press Enter again.", 18, TRAFFIC,
         "A PERSISTENT emote, unlike /dance. If both are just 0x0064 chat lines, the "
         "server parses them and the client does not care -- which is what C2 implies "
         "and this tests."),
    Step("emote_dance", "Press Enter, type   /dance   and press Enter again.",
         18, TRAFFIC,
         "The paired comparison, in the SAME run as /sit so the two cannot differ for "
         "some reason belonging to a different session."),
    Step("chat_all", "Press Enter, type   rurik two   and press Enter again.",
         20, TRAFFIC,
         "Reproduces C2's known plaintext, and the '!' prefix the client adds itself."),
    Step("chat_me", "Press Enter, type   /me waves   and press Enter again.",
         20, TRAFFIC,
         "A different chat CHANNEL. If the prefix byte changes and the opcode does "
         "not, 0x0064's field 1 is the channel -- which would explain the 0 vs 284 "
         "that C2 could not."),
    Step("skills_panel", "Open the skills panel, look, then close it.", 12, SILENCE,
         "Believed client-side, like the bags and the map were."),
    Step("quest_log", "Open the quest log, look, then close it.", 12, SILENCE,
         "Quests are server state, so this one is a genuine coin-toss."),
    Step("idle_b", "Do nothing. Hands off again.", 12, SILENCE,
         "The closing control.", control=True),
    Step("gateway", "Walk into the zone exit. This may end the run.", 18, TRAFFIC,
         "Ascalon City's exit, for comparison with Lakeside's -- which sent only "
         "movement and no zone request at all."),
]

# THE WORLD-ACTION SCRIPT, and it is the only one of the three aimed at OUR OWN world.
# `combat` and `town` both need a tape, so all three labelled runs in the vault are
# ArenaNet's agents. That is exactly the gap: studies/enemy/PLAN.md 10.5 measured a
# 206-to-0 split -- nineteen hand-driven sessions on our server sent GAME_CMSG 0x0033
# 206 times and 0x0026 never, while two tape sessions sent 0x0026 seven times and 0x0033
# never -- with zero overlap, the same client and the same authsrv.py. The `attack` step
# of `combat` has never once been aimed at an agent WE created.
#
# WHAT CHANGED THE QUESTION (PLAN.md 8.0 item 0k, studies/enemy/PLAN.md 10.6). 0x0033 is
# not a refusal and not "interact": 0x00514840 is a SIX-ARM world-action switch, 0x0026
# is arm 0 and 0x0033 is arm 1, and the client picks the arm. Four target properties and
# our own weapon are all now measured CORRECT (10.1, 10.2, 10.4) and `is_explorable` is
# REFUTED as the lever -- ten of the nineteen zero-attack sessions had it set. So this
# script does not test another hypothesis about the agent. It reads the answer off the
# client:
#
#   * `menu_open` and `menu_attack` are RETIRED IN PLACE -- kept as keys so the run of
#     2026-08-11 stays reproducible, but they ask for something that does not exist.
#     THERE IS NO RIGHT-CLICK CONTEXT MENU ON A WORLD AGENT. 0x005144F0 really does
#     build an `actionsList` with a `displayOrder` (its own asserts say so), but nothing
#     anywhere says that list is opened by right-clicking an agent, or that it surfaces
#     in the world at all -- I supplied the gesture, and A GESTURE IS NOT IN THE
#     DISASSEMBLY. Both steps drew zero messages and 20 s of frame grabs show no menu.
#     Left standing as the negative result rather than deleted.
#   * `dbl_click` is the discriminator, and it does not need a menu to be one: the
#     client resolves the gesture to an action itself and sends that arm.
#   * `skill_attack` is the second face of the same refusal: with the attack-skill arm in
#     place the harness pressed slots 5-7 (skills 320-323, Warrior attack skills) at a
#     taken target on 2026-08-11 and NOT ONE message left the client, which is 0x0027
#     going the same way 0x0026 does.
#
# NOTHING HERE PREDICTS 0x0026. It is the outcome we want and predicting it would be
# wishing; each step predicts only that the client says SOMETHING, and `analyse` reports
# which opcode it was. What the run cannot do is tell 0x0026's absence apart from a
# gesture the operator did not manage -- which is what the two controls and the
# per-step message count are for.
WORLDACTION = [
    Step("idle_a", "Do nothing. Hands off the mouse and keyboard.", 12, SILENCE,
         "The idle floor. Our server ANSWERS, unlike a tape, so this window is also "
         "the only measurement of what our own traffic looks like with the operator "
         "still -- if it is not silent, every count below is against a moving floor.",
         control=True),
    Step("target_click", "Left-click the Hatcher once to target it. Do not attack yet.",
         10, TRAFFIC,
         "Isolates the select from the act. Predicts 0x00C1 with the Hatcher's agent "
         "id and nothing else -- which is all every session of 2026-08-11 produced, "
         "so this step is also the check that the world is in the state we think."),
    Step("menu_open",
         "Right-click the Hatcher and hold for a moment, then release. (There is no "
         "menu -- this step is kept only as the control that says so.)",
         20, SILENCE,
         "REFUTED 2026-08-11 and kept as the negative result. It was written to read "
         "an available-actions menu off the screen; there is no such menu on a world "
         "agent, and the step's real content is that right-click produces NO wire "
         "traffic at all. Silence remains the prediction, now for a different reason."),
    Step("dbl_click", "Double-click the Hatcher.", 10, TRAFFIC,
         "THE DISCRIMINATOR. The client resolves a double-click to an action itself "
         "and sends that arm: 0x0026 means the blocker died to work already landed, "
         "0x0033 again means it survives every property measured in 10.1-10.4."),
    Step("menu_attack",
         "Skip this one -- hands off. (It asked for a menu item that does not exist.)",
         15, SILENCE,
         "RETIRED with menu_open, same error, kept as its second control. It asked the "
         "operator to pick Attack out of a menu there is no evidence exists, to compare "
         "a PICKED action against a RESOLVED gesture. The comparison was worth wanting; "
         "the route into it was invented."),
    Step("attack_other",
         "Attack it once more, however you normally would -- not by double-clicking.",
         12, TRAFFIC,
         "Deliberately does NOT name a key. The 2026-08-10 run nearly attributed "
         "three messages to a key nobody pressed because the prompt assumed a "
         "binding; a prompt cannot know what is bound."),
    Step("skill_attack", "With the Hatcher targeted, press 5.", 10, TRAFFIC,
         "Slot 5 is skill 320, a Warrior ATTACK skill. On 2026-08-11 slots 5-7 sent "
         "nothing at all at a taken target, so this is 0x0027 refused the same way "
         "0x0026 is. Traffic here would separate the two refusals."),
    Step("skill_nonattack", "Now press 1.", 10, TRAFFIC,
         "Slot 1 is skill 316, and the PAIRED CONTROL for the step above: if 1 sends "
         "0x0046 and 5 sends nothing, the refusal belongs to attack skills rather "
         "than to our skillbar, our unlocks or the client's idea of the target."),
    Step("idle_b", "Do nothing. Hands off again.", 12, SILENCE,
         "The closing control, and it matters more than the first -- it proves the "
         "run was still quiet after the actions, so a late attribution is as good as "
         "an early one.", control=True),
    Step("gateway", "Walk into the zone exit. This may end the run.", 15, TRAFFIC,
         "Last on purpose, as in the other two scripts. Unlike them this is OUR "
         "handoff rather than a recorded one, so what it does is unknown rather "
         "than refused-by-the-cage."),
]

SCRIPTS = {"combat": COMBAT, "town": TOWN, "worldaction": WORLDACTION}
STEPS = COMBAT          # the default, and what `--labelrun` with no name still means


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

    `out` is for tests: pass a collector and the per-second countdown lines are skipped,
    so the output is a deterministic banner sequence instead of a wall-clock-dependent
    one. Everything else -- banners, marks, counts -- is identical either way.
    """
    global ACTIVE
    live = out is None
    say = (lambda s: print(s, flush=True)) if live else out
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
    if _hold(ready, stop, live, None, say):
        return False

    try:
        for i, step in enumerate(steps, 1):
            if stop.is_set():
                say(f"\n  stopped before step {i}/{len(steps)}")
                rec.event("label_run_stopped", at_index=i, at_key=step.key)
                return False
            if getattr(rec, "closed", False):
                # The client left. Checking ONCE before the run is not enough: on
                # 2026-08-10 the Ascalon tape's own last act was walking into a
                # gateway, so the client zoned out during the six-second countdown
                # -- after every up-front check had passed -- and the first mark
                # died on `I/O operation on closed file`. A prompt loop talking to
                # a capture nobody is writing to is worse than useless: it would
                # walk the operator through fourteen steps that record nothing.
                say(f"\n  the client is gone -- stopping at step {i}/{len(steps)}, "
                    f"{step.key}. Nothing after this could have been recorded.")
                return False
            SEEN[0] = 0
            rec.event("label_step", index=i, key=step.key, prompt=step.prompt,
                      seconds=step.seconds, expect=step.expect,
                      control=step.control)
            ACTIVE = True
            nxt = steps[i].prompt if i < len(steps) else "(last step)"
            say(f"\n{bar}\n"
                f"  STEP {i} of {len(steps)}\n\n"
                f"      >>>  {step.prompt}\n\n"
                f"  next: {nxt}\n{bar}")
            stopped = _hold(step.seconds, stop, live, step, say)
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


# How often the countdown emits a line. NOT an in-place `\r` redraw: this process is a
# CHILD of session.py, its stdout is a PIPE, and the parent reads it with
# `for line in proc.stdout` -- which blocks until a newline arrives. A carriage-return
# countdown would therefore have displayed NOTHING at all, and then dumped the whole
# step at once when the next banner's newline finally landed. Discovered the hard way on
# 2026-08-10: the operator saw only "...holding".
TICK = 3


def _hold(seconds, stop, live, step, say):
    """Wait out one window, ticking a countdown. True if stopped.

    Sleeps in slices so a Ctrl-C or a closed client lands within a fifth of a second
    rather than at the end of an 18-second step.
    """
    end = time.monotonic() + seconds
    nxt = seconds - TICK
    while True:
        now = time.monotonic()
        if stop.is_set():
            return True
        left = end - now
        if left <= 0:
            break
        if live and step is not None and left <= nxt:
            say(f"      {int(left) + 1:>2}s left   ({SEEN[0]} message(s) so far)")
            nxt = int(left) - TICK
        time.sleep(min(0.2, max(0.0, left)))
    if live and step is not None:
        say(f"      -- step over, {SEEN[0]} message(s) --")
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


def is_control(mark):
    """Is this recorded step a control?

    Marks written before 2026-08-10 carry no `control` field, so fall back to the
    script's own answer for that key. Without this, re-analysing an older capture
    would demote a dirty idle window from "this run is void" to "interesting
    finding" -- the exact confusion the field was added to end, reintroduced by the
    absence of the field.
    """
    if "control" in mark:
        return bool(mark["control"])
    return any(s.key == mark.get("key") and s.control for s in STEPS)


def report(segments, before, say=print):
    """Print the run, and return (control_failures, refuted, silent_steps).

    The first return value is the only one that invalidates a run. `refuted` is a
    RESULT -- a step that predicted silence and got traffic is exactly what this
    exercise is for, and reporting it as a failure told an operator with two spotless
    idle windows to throw a good run away.
    """
    say(f"\n{'step':>3} {'key':<14} {'expect':<8} {'n':>4} {'ka':>3}  opcodes")
    failures, refuted, silent = [], [], []
    for i, seg in enumerate(segments, 1):
        st = seg["step"]
        n = sum(len(v) for v in seg["opcodes"].values())
        ops = "  ".join(f"0x{op:04X}x{len(v)}"
                        for op, v in sorted(seg["opcodes"].items()))
        ctl = is_control(st)
        tag = "CONTROL " if ctl else ""
        say(f"{i:>3} {st['key']:<14} {tag + st['expect']:<8} {n:>4} "
            f"{seg['keepalives']:>3}  {ops or '--'}")
        if st["expect"] == SILENCE and n:
            (failures if ctl else refuted).append((st["key"], n, ops))
        if st["expect"] == TRAFFIC and not n:
            silent.append(st["key"])

    if before:
        say(f"\n{len(before)} message(s) arrived BEFORE the first step and belong to no "
            f"action (tape / instance load). Not attributed.")
    if failures:
        say("\nCONTROL FAILURE -- traffic in a window where the operator was told to do "
            "NOTHING:")
        for key, n, ops in failures:
            seg = next(s for s in segments if s["step"]["key"] == key)
            offs = [r.get("t", 0.0) - seg["step"].get("t", 0.0)
                    for r in seg["messages"]
                    if (int(r.get("opcode", -1)) & ~CMSG_MASK) != KEEPALIVE]
            span = f"+{min(offs):.1f}s to +{max(offs):.1f}s of a " \
                   f"{seg['step'].get('seconds', 0):.0f}s window" if offs else ""
            say(f"   {key}: {n} message(s)  {ops}")
            say(f"      when: {span}")
        say("   Either they did not sit still, or the marks and the messages disagree.\n"
            "   WHERE it landed decides how much is lost. Traffic in the first moment\n"
            "   of a window is usually an action from BEFORE the mark still settling,\n"
            "   and it says nothing about later steps; traffic spread across the whole\n"
            "   window means the operator was active and the clock cannot be trusted.\n"
            "   Judge it, and say which you concluded -- do not name an opcode from a\n"
            "   run you have not looked at this way.")
    else:
        say("\nControls clean: both idle windows silent. Attributions in this run stand.")
    if refuted:
        say("\nPREDICTION REFUTED -- this is a FINDING, not a fault. These steps were\n"
            "predicted to be client-side only and were not:")
        for key, n, ops in refuted:
            say(f"   {key}: {n} message(s)  {ops}")
    if silent:
        say(f"\nNo traffic at all from: {', '.join(silent)}")
        say("   Either the action is client-side, or it needs a server reply to send,\n"
            "   or the operator did not perform it. This tool cannot tell those apart.")
    return failures, refuted, silent


def main(argv=None):
    import argparse
    sys.path.insert(0, os.path.dirname(HERE))
    import vaultpath
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--analyse", "--analyze", dest="analyse", action="store_true",
                    help="analyse a capture instead of listing a script")
    ap.add_argument("--script", default="combat", choices=sorted(SCRIPTS),
                    help="which script to list (default: combat)")
    ap.add_argument("capture", nargs="?",
                    help="gamesrv capture .jsonl; default: the newest")
    a = ap.parse_args(argv)

    if not a.analyse:
        script = SCRIPTS[a.script]
        total = sum(s.seconds for s in script)
        print(f"{a.script}: {len(script)} steps, {total:.0f}s "
              f"({total / 60:.1f} min)\n")
        for i, s in enumerate(script, 1):
            print(f"{i:>3} {s.key:<14} {s.seconds:>4.0f}s  [{s.expect}]  {s.prompt}")
            if s.why:
                print(f"      why: {s.why}")
        return 0

    cap = a.capture
    if not cap:
        # The newest capture is NOT necessarily the labelled one. The gateway step
        # makes the client dial out and reconnect, so a labelled run routinely
        # leaves a LATER, empty capture behind it -- and defaulting to "newest"
        # then reports "not a labelled run" about a run that was one. Search
        # newest-first for a file that actually carries marks.
        root = vaultpath.require_dir("captures", "gamesrv", why="analysing a label run")
        files = sorted((os.path.join(root, f) for f in os.listdir(root)
                        if f.endswith(".jsonl")), key=os.path.getmtime, reverse=True)
        if not files:
            print(f"no gamesrv captures in {root}")
            return 1
        cap = next((f for f in files
                    if any(m.get("kind") == "label_step" for m in load(f)[0])), None)
        if cap is None:
            print(f"none of the {len(files)} gamesrv capture(s) in {root} contains a "
                  f"labelled run -- was it run with --labelrun?")
            return 1
    print(f"capture: {os.path.basename(cap)}")
    marks, msgs = load(cap)
    segments, before = segment(marks, msgs)
    if not segments:
        print("no label_step marks in this capture -- was it run with --labelrun?")
        return 1
    failures, _refuted, _silent = report(segments, before)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
