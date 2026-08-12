#!/usr/bin/env python3
"""The behaviour-run analyser, against a session this file builds out of nothing.

    python toolkit/authsrv/test_behaviourrun.py

NO VAULT, NO SOCKET, NO CLIENT. Every message below is a tuple written here, which is
what lets this run on a bare machine and what makes each check a statement about the
analyser rather than about one capture.

WHAT IT IS FOR. `behaviourrun.py` decides which monster behaviour belongs to which
operator action, and every number the capture campaign will ever produce comes out of
that attribution. The three defects it must be unable to have are all ones this project
has already paid for:

  * **The mark-after-prompt defect**, which is `labelrun.py`'s own, recorded in its
    docstring. A mark taken AFTER the operator has been told what to do hands that step's
    first messages to the previous window. Section 2 builds both orderings of the same
    session and requires them to be distinguishable, then requires `narrate` to write the
    mark first.
  * **The estimated position**, which produced four separation numbers of which two were
    wrong by 481 and 1,594 units. Section 4 requires a subject that moved to come back
    UNRESOLVED and `separation` to return None for it -- a refusal, not a wide error bar.
  * **The wrong control predicate.** On our own server a control window predicts no
    traffic; against ArenaNet the world talks throughout, so that predicate reddens
    always, and a check that always reddens is as useless as one that never does. Section
    3's decisive case is a control window carrying HEAVY server traffic and zero player
    actions, which must pass.

standard library only.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import behaviourrun as BR  # noqa: E402
import checks  # noqa: E402

LEDGER = checks.Ledger("behaviourrun", floor=36)
check = checks.adopt(LEDGER)

ATTACK_STARTED = 4          # agents.GV_ATTACK_STARTED, written as a literal on purpose


def mark(n, label, wire_t):
    return {"kind": "mark", "n": n, "label": label, "wire_t": wire_t,
            "wall": 1_700_000_000.0 + wire_t, "perf": 500.0 + wire_t}


def main():
    # ---- 1. the script itself ------------------------------------------------
    print("1. the operator script is well formed")
    keys = [s.key for s in BR.STEPS]
    check(len(keys) == len(set(keys)), "every step key is unique",
          f"{len(keys)} steps -- a duplicate key silently merges two windows")
    check(all(s.seconds > 0 for s in BR.STEPS), "every step has a positive duration")
    controls = [s.key for s in BR.STEPS if s.control]
    check(len(controls) >= 2, "there are at least TWO control windows",
          f"{controls} -- one control clean by luck is not a control")
    check(all(s.why for s in BR.STEPS), "every step says WHY it exists",
          "a step with no stated purpose gets rationalised into agreeing afterwards")
    check(BR.STEP_BY_KEY["play"].key == "play" and not BR.STEP_BY_KEY["play"].control,
          "the free-play step exists and is not a control",
          "it makes the session a session; it is deliberately not analysed")
    try:
        BR.Step("bad", "x", 0)
        bad = False
    except ValueError:
        bad = True
    check(bad, "a step with a non-positive duration is refused at construction")

    # ---- 2. windowing, and labelrun's own defect -----------------------------
    print("\n2. windows, and the mark-after-prompt defect")
    # A session: step A at t=10, step B at t=20. The operator acted at t=10.5 (inside A)
    # and t=20.5 (inside B). Two messages before the first mark belong to the LOAD.
    msgs = [(1.0, 0x0026, [0]), (2.0, 0x0026, [0]),        # before any mark: the load
            (10.5, 0x0026, [0]), (12.0, 0x0026, [0]),      # step A
            (20.5, 0x0027, [0])]                           # step B
    good = [mark(1, "A", 10.0), mark(2, "B", 20.0)]
    wins = BR.window_steps(good)
    check([w[0] for w in wins] == ["A", "B"], "windows come out in mark order",
          str([w[0] for w in wins]))
    inside = {w[0]: [m for m in msgs if w[1] <= m[0] < w[2]] for w in wins}
    check(len(inside["A"]) == 2 and len(inside["B"]) == 1,
          "each step gets its own messages", f"A={len(inside['A'])} B={len(inside['B'])}")
    before = [m for m in msgs if m[0] < wins[0][1]]
    check(len(before) == 2,
          "messages before the first mark are NOT folded into step 1",
          f"{len(before)} held out -- they belong to the load, and absorbing them "
          "inflates the first action")

    # THE DEFECT: marks written a beat LATE (after the operator acted) shift each
    # window right, so step A's own first message falls before its mark and is
    # attributed to the load -- or worse, to the previous step.
    late = [mark(1, "A", 11.0), mark(2, "B", 21.0)]
    late_wins = BR.window_steps(late)
    late_A = [m[0] for m in msgs if late_wins[0][1] <= m[0] < late_wins[0][2]]
    ontime_A = [m[0] for m in inside["A"]]
    # ASSERT ON CONTENT, NOT COUNT. Both windows hold two messages here -- the late one
    # drops step A's own first and picks up step B's, so a count comparison is equal and
    # the check could not fail for the right reason. That was this check's first version.
    check(10.5 in ontime_A and 10.5 not in late_A and 20.5 in late_A,
          "a mark written LATE loses its own first message AND steals the next step's",
          f"on-time A={ontime_A}, late A={late_A} -- both are length 2, which is why "
          "this asserts contents. labelrun's own defect, and the reason narrate() "
          "writes the mark before it prints the prompt")

    # ---- 3. the control predicate, redefined for live ------------------------
    print("\n3. the control predicate is about the CLIENT half only")
    quiet = [(1.0, 0x0009, []), (2.0, 0x0009, [])]
    clean, detail = BR.control_verdict("idle_a", quiet)
    check(clean, "a control with only keepalives is clean", detail)

    dirty = quiet + [(3.0, 0x0026 | BR.CMSG_MASK, [])]
    clean, detail = BR.control_verdict("idle_a", dirty)
    check(not clean, "a control carrying a PLAYER ACTION is dirty", detail)
    check("0x26" in detail, "and the offending opcode is named, not just counted", detail)

    # THE DECISIVE CASE. Against ArenaNet a control window is FULL of server traffic --
    # 0x001E alone is about a third of the stream. A predicate that reddens on that
    # reddens on every window ever captured.
    noisy = quiet + [(float(i), 0x001E, [0, 50]) for i in range(200)]
    clean, detail = BR.control_verdict("idle_a", noisy)
    check(clean,
          "a control BUSY with server traffic is still clean -- this is the live "
          "redefinition", f"{detail}. A no-traffic predicate would redden here and in "
          "every control window of every live capture ever taken")

    # masking: the client ORs 0x8000 into every game-channel opcode it sends
    masked = [(1.0, 0x0026 | BR.CMSG_MASK, [])]
    clean, _d = BR.control_verdict("idle_a", masked)
    check(not clean, "a masked client opcode is still recognised as a player action",
          "without masking off 0x8000 not one client message decodes at all")

    # ---- 4. encounters: resolved, or withheld -------------------------------
    print("\n4. a subject that moved is UNRESOLVED, never estimated")
    still = [(1.0, BR.CREATE, [0x20, 100, 0x20000001, 1000.0, 0.0]),
             (5.0, BR.INT_TARGET, [0xA0, ATTACK_STARTED, 100, 7])]
    rows = BR.encounters(still)
    check(len(rows) == 1 and rows[0]["resolved"] and rows[0]["reaction"] is not None,
          "a subject that never moved is RESOLVED at its create coordinate",
          f"{rows[0]['pos']}, moved={rows[0]['moved']}")
    d = BR.separation(rows[0], (0.0, 0.0))
    check(d is not None and abs(d - 1000.0) < 1e-6,
          "and its separation is a real measurement", f"{d}")

    for op, name in ((BR.MOVE_TO_POINT, "0x0029"), (BR.UPDATE_DESTINATION, "0x002A"),
                     (BR.UPDATE_SPEED, "0x002B")):
        moved = [(1.0, BR.CREATE, [0x20, 100, 0x20000001, 1000.0, 0.0]),
                 (3.0, op, [op, 100, 0.0, 0.0]),
                 (5.0, BR.INT_TARGET, [0xA0, ATTACK_STARTED, 100, 7])]
        r = BR.encounters(moved)[0]
        check(not r["resolved"] and BR.separation(r, (0.0, 0.0)) is None,
              f"a subject that sent {name} before reacting is WITHHELD",
              f"moved={r['moved']}, separation=None -- estimation produced four numbers "
              "here once and two were wrong by 481 and 1,594 units")

    # movement AFTER the reaction does not disqualify: the position at the reaction is
    # still the create coordinate. Getting this backwards would withhold every subject
    # that chased the player after striking, which is most of them.
    after = [(1.0, BR.CREATE, [0x20, 100, 0x20000001, 1000.0, 0.0]),
             (5.0, BR.INT_TARGET, [0xA0, ATTACK_STARTED, 100, 7]),
             (6.0, BR.MOVE_TO_POINT, [0x29, 100, 0.0, 0.0])]
    check(BR.encounters(after)[0]["resolved"],
          "but movement AFTER the reaction does not disqualify the sample",
          "the position at the reaction is what is being measured, and that is settled "
          "by then")

    # ---- 5. models are never pooled -----------------------------------------
    print("\n5. no summary pools across model ids")
    two = [(1.0, BR.CREATE, [0x20, 100, 0x20000001, 100.0, 0.0]),
           (1.1, BR.CREATE, [0x20, 200, 0x20000002, 900.0, 0.0]),
           (5.0, BR.INT_TARGET, [0xA0, ATTACK_STARTED, 100, 7]),
           (5.1, BR.INT_TARGET, [0xA0, ATTACK_STARTED, 200, 7])]
    groups = BR.by_model(BR.encounters(two))
    check(len(groups) == 2 and all(len(v) == 1 for v in groups.values()),
          "two creature models stay in two groups",
          f"{ {hex(k): len(v) for k, v in groups.items()} } -- pooling three models is "
          "what produced the refuted 269-1594 unit range band")

    # ---- 6. the tick clock ---------------------------------------------------
    print("\n6. the tick clock against the wire clock")
    ticks = [(0.0, BR.TICK, [0x1E, 0]), (1.0, BR.TICK, [0x1E, 1000]),
             (2.0, BR.TICK, [0x1E, 1000])]
    drift, ratio = BR.tick_drift(ticks)
    check(drift is not None and abs(drift) < 1e-6 and abs(ratio - 1.0) < 1e-9,
          "a tape whose ticks sum to its own span has zero drift", f"{drift} / {ratio}")
    bad = [(0.0, BR.TICK, [0x1E, 0]), (1.0, BR.TICK, [0x1E, 5000])]
    drift, _r = BR.tick_drift(bad)
    check(drift is not None and abs(drift) > BR.TICK_BOUND_MS,
          "and a tape whose ticks disagree with it is caught", f"{drift:+.0f} ms")
    check(BR.tick_drift([(0.0, BR.TICK, [0x1E, 0])]) == (None, None),
          "a tape with too few ticks answers None, which is NOT a pass",
          "a short connection is a real case and must not read as agreement")

    # ---- 7. the in-band channel, whose existence is a prediction -------------
    print("\n7. the in-band mark channel is checked, not assumed")
    check(BR.chat_marks([(1.0, 0x0026 | BR.CMSG_MASK, [])]) == [],
          "a session with no chat reports NO in-band marks",
          "CHAT_SEND is 0 of 500 client messages in the existing corpus, so step 0 is a "
          "stated prediction; an empty result must be visible rather than fall back to "
          "the out-of-band file and call the binding checked")
    check(len(BR.chat_marks([(1.0, BR.CHAT | BR.CMSG_MASK, [])])) == 1,
          "and one that does carry chat finds it, mask and all")

    # ---- 8. narrate marks BEFORE it prompts, and drives nothing --------------
    print("\n8. narrate() marks before it prompts")
    with tempfile.TemporaryDirectory() as tmp:
        seen = []

        def say(line):
            mf = os.path.join(tmp, "MARK")
            # the KEY only: the file also carries the two clocks the mark is
            # stamped with, and this check is about ordering, not about them
            txt = open(mf, encoding="utf-8").read() if os.path.exists(mf) else None
            seen.append((line, txt.splitlines()[0] if txt else None))

        # A clock that ADVANCES. A constant one makes `while now() < end` spin forever,
        # which is how the first version of this check hung instead of failing -- worth
        # a line, because a fake clock that does not move is a fixture that silently
        # resolves to the wrong thing.
        ticker = [0.0]

        def now():
            ticker[0] += 0.5
            return ticker[0]

        two_steps = [BR.Step("one", "do one", 1), BR.Step("two", "do two", 1)]
        BR.narrate(tmp, steps=two_steps, say=say, sleep=lambda s: None, now=now)
        first = next((mark_txt for line, mark_txt in seen if "do one" in line), None)
        check(first == "one",
              "the MARK file already names the step when its prompt is printed",
              f"{first!r} -- marking after the prompt is exactly labelrun's defect")
        second = next((mark_txt for line, mark_txt in seen if "do two" in line), None)
        check(second == "two", "and it advances for the next step", f"{second!r}")

    # THE MARK CARRIES ITS OWN CLOCKS. The driver polls the MARK file every 5 s, so a
    # mark stamped when the driver NOTICES it is late by up to that -- coarser than the
    # binding exists to provide, and invisible in the artifact.
    with tempfile.TemporaryDirectory() as tmp:
        # AN ADVANCING CLOCK. A constant `now` makes narrate's wait loop spin forever;
        # this is the second time in this file, so it is worth a line rather than a
        # third. `wall`/`clock` ARE constant on purpose -- they are the values under
        # test, not the loop's driver.
        tick = [0.0]

        def step_now():
            tick[0] += 0.5
            return tick[0]

        BR.narrate(tmp, steps=[BR.Step("approach", "x", 1)], say=lambda s: None,
                   sleep=lambda s: None, now=step_now,
                   wall=lambda: 1_700_000_123.5, clock=lambda: 42.25)
        lines = open(os.path.join(tmp, "MARK"), encoding="utf-8").read().splitlines()
        check(lines[0] == "approach" and float(lines[1]) == 1_700_000_123.5
              and float(lines[2]) == 42.25,
              "the MARK file carries the key AND both clocks at the taken instant",
              f"{lines} -- the driver reads these through instead of stamping at pickup")

    src = open(os.path.join(HERE, "behaviourrun.py"), encoding="utf-8").read()
    for banned in ("SendInput", "keybd_event", "PostMessage", "mouse_event",
                   "hold_key", "click"):
        check(banned not in src,
              f"the analyser contains no `{banned}` -- it drives nothing",
              "the driver sends no keystrokes and no clicks; that is the rule that "
              "protects the account and no guard substitutes for it")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
