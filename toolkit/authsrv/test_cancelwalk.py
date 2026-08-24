"""CANCELWALK's experiment arms: parsing, the lead formula, composition, wiring.

What this locks, and what it deliberately does not: the arms themselves are
pre-registered DIAGNOSTICS (studies/movement/CANCELWALK.md §5) whose verdicts
come from operator runs, so this file tests everything AROUND the run -- the
flag parses or refuses loudly, the lead arithmetic reproduces retail's own
granted points from the live capture's numbers, the composition matrix
refuses the inert and the confounded combinations, cancel_on_move names what
a press hit, and the handler's suppress gates exist in the source. A wrong
verdict from a run is the run's business; a wrong ANSWER SHAPE from the
server would be this file's.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 24, from the green run of 2026-08-24 that landed the file.
LEDGER = checks.Ledger("cancelwalk arms", floor=24)
check = LEDGER.ok

PLAYER = 1


def section_parse():
    import authsrv

    print("1. parse_cancel_answer: three arms in, everything else refused")
    check(authsrv.parse_cancel_answer(None) == (None, None, None),
          "no flag parses to no arm, no refusal")
    check(authsrv.parse_cancel_answer("suppress") == ("suppress", None, None),
          "R1: suppress")
    check(authsrv.parse_cancel_answer("retail-lead") == ("lead", None, None),
          "R2: retail-lead, lead None = the D1 expression")
    check(authsrv.parse_cancel_answer("lead:16") == ("lead", 16.0, None),
          "R3: lead:16 parses to 16.0 units")
    m, l, why = authsrv.parse_cancel_answer("lead:0")
    check(m is None and why is not None and "768.5" in why,
          "lead:0 is the shipped answer wearing a flag -- refused, and the "
          "refusal names the bounds", f"({m}, {l}, {why!r})")
    m, l, why = authsrv.parse_cancel_answer("lead:banana")
    check(m is None and why is not None,
          "a non-number lead is refused, not defaulted")
    m, l, why = authsrv.parse_cancel_answer("supress")
    check(m is None and why is not None and "suppress" in why,
          "a typo'd arm is refused LOUDLY and the refusal lists the real "
          "arms -- a mistyped experiment must not run the shipped default "
          "under an experiment's name", f"{why!r}")


def section_lead_formula():
    import authsrv

    print("2. cancelwalk_lead_dest reproduces retail's own granted points")
    # The three movement-cancel instants of live capture 20260824T074002:
    # (reported, vec2) -> the 0x0029 point retail actually sent. cancelwalk.py
    # prints all three; the vec2 is the client's LATCHED heading, bit-identical
    # across the presses (CANCELWALK-F2).
    VEC2 = (13.093545913696289, 767.5670776367188)
    RETAIL = [((-5996.01611328125, 1547.1153564453125),
               (-5982.915, 2315.182)),    # t=81.660, W mid-cast
              ((-5928.83935546875, 2011.6990966796875),
               (-5915.738, 2779.766)),    # t=114.641, W mid-windup
              ((-5957.63623046875, 2012.1395263671875),
               (-5944.535, 2780.207))]    # t=128.805, W mid-cast again
    for (reported, granted) in RETAIL:
        d = authsrv.cancelwalk_lead_dest(reported, VEC2, None)
        check(abs(d[0] - granted[0]) < 0.02 and abs(d[1] - granted[1]) < 0.02,
              f"reported {reported} + vec2 + 0.5u lands on retail's own "
              f"granted point {granted} within 0.02 u -- the D1 formula, "
              f"confirmed at a cancel instant", f"got {d}")
    d = authsrv.cancelwalk_lead_dest((0.0, 0.0), (0.0, 500.0), 16.0)
    check(abs(d[0]) < 1e-9 and abs(d[1] - 16.0) < 1e-9,
          "a fixed lead is measured along the UNIT heading, not the raw "
          "765-768 u vec2", f"got {d}")
    d = authsrv.cancelwalk_lead_dest((5.0, 6.0), (0.0, 0.0), None)
    check(d == [5.0, 6.0],
          "a degenerate heading grants the reported point rather than "
          "inventing a direction")


def section_composition():
    import authsrv

    print("3. the composition matrix: inert and confounded combinations refuse")
    why, _ = authsrv.zero_lead_composition(zero_lead=False,
                                           cancel_answer="suppress")
    check(why is not None and "--cancel-answer requires --zero-lead" in why,
          "without --zero-lead the arm is INERT while the run log says "
          "otherwise -- the --plane-carry defect, refused the same way",
          f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, arrival_carry=True,
                                           cancel_answer="retail-lead")
    check(why is not None and "--arrival-carry" in why,
          "with --arrival-carry the F1b queue would model the reported point "
          "while the wire carried the led one -- refused", f"{why!r}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                               cancel_answer="retail-lead")
    check(why is None and any("CANCELWALK" in n and "DIAGNOSTIC" in n
                              for n in notes),
          "allowed with --zero-lead, and the startup note names the arm and "
          "its diagnostic-only status", f"notes={notes}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True)
    check(why is None and notes == [],
          "the shipped default is untouched: no arm, no note")


def section_hit_kind():
    import authsrv

    print("4. cancel_on_move names what the press hit")
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals))
        state = {"agents": {}}
        authsrv.handle_skill_press([0, 42, 7, 0], send, state, 0,
                                   authsrv.GAME_CMSG_USE_SKILL)
        hit = authsrv.cancel_on_move(send, state, 0)
        check(hit == "cast",
              "a press that released a mid-activation cast returns 'cast' -- "
              "the instant the CANCELWALK arms change", f"hit={hit!r}")
        hit2 = authsrv.cancel_on_move(send, state, 0)
        check(hit2 is None,
              "the SAME cast is not hit twice: the release is once per entry, "
              "so a second movement report is an ordinary press",
              f"hit={hit2!r}")
        state2 = {"agents": {}, "attacking": {"target": 2}}
        hit3 = authsrv.cancel_on_move(send, state2, 0)
        check(hit3 == "swing",
              "a press that stopped the attack chain returns 'swing'",
              f"hit={hit3!r}")
        hit4 = authsrv.cancel_on_move(send, {"agents": {}}, 0)
        check(hit4 is None, "an idle press hits nothing and returns None")
    finally:
        authsrv.skill_timing = saved


def section_handler_wiring():
    import authsrv

    print("5. the handler's gates exist where the run will need them")
    src = open(os.path.join(os.path.dirname(authsrv.__file__), "authsrv.py"),
               encoding="utf-8").read()
    check("(legacy_dir or zero_ok) and not cw_suppress" in src,
          "the 0x0025 send is gated on NOT cw_suppress -- R1 answers with "
          "the burst alone")
    check("if legacy_dir and not cw_suppress:" in src,
          "the walking latch is unwritten under suppress, so the SECOND "
          "press's 0x0025 is not swallowed by a walking=True the suppressed "
          "report never earned")
    check(src.count("zl_point = cw_dest") == 1
          and src.count("[PLAYER_AGENT_ID, zl_point,") == 1,
          "ONE 0x0029 send site serves both the shipped default and the lead "
          "arms -- a second site would be the two-arms-one-clock defect the "
          "composition matrix refuses")
    check("cw_hit = cancel_on_move(send, state, conn_id)" in src,
          "the 0x003D arm captures what the press hit from the return value "
          "-- a state latch would leak through the click arm, which calls "
          "cancel_on_move too")


def main():
    section_parse()
    section_lead_formula()
    section_composition()
    section_hit_kind()
    section_handler_wiring()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
