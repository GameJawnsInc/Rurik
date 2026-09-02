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

# FLOOR 121, from the green run of 2026-08-25 that landed the
# --resync-separation lever (P8's negative-control dial: refused alone,
# refused non-positive/non-finite, allowed with --resync with the override
# named in the note, the pin-x-resync cell still outranking it, and -- after
# the review's mutation pass showed the rebind unpinned -- the main()
# assignment source-locked by name, CAST_STOP-style.
# 113 with the 8.3g SHIP
# ruling ("pin it") -- the resolve_cast_stop_default cell table and its
# source locks; 102 with F34's pin-or-nothing fix after R10's owner run
# measured the bare 0x0028 warping a parked body onto a converging copy;
# 100 with the re-review's
# yield: the wire-plane burst, the legacy-bool refusal, the M7 subscript
# hardening; 98 with the 8.3a review fixes: B1's click-walk latch, B2's
# census rate families, and the plane-at-est / off-mesh-refusal /
# model-park REALs; 82 when R10's --cast-stop=pin arm landed; 59 after
# the R8 review pass; 58 when R8's section landed; 43 with R1-R6's arms;
# 29 with R1-R4's alone; 24 with R1-R3).
LEDGER = checks.Ledger("cancelwalk arms", floor=121)
check = LEDGER.ok

PLAYER = 1


def section_parse():
    import authsrv

    print("1. parse_cancel_answer: three arms in, everything else refused")
    check(authsrv.parse_cancel_answer(None) == (None, None, False, None),
          "no flag parses to no arm, no refusal")
    check(authsrv.parse_cancel_answer("suppress")
          == ("suppress", None, False, None),
          "R1: suppress")
    check(authsrv.parse_cancel_answer("retail-lead")
          == ("lead", None, False, None),
          "R2: retail-lead, lead None = the D1 expression")
    check(authsrv.parse_cancel_answer("lead:16") == ("lead", 16.0, False, None),
          "R3: lead:16 parses to 16.0 units")
    check(authsrv.parse_cancel_answer("retail-lead,stop")
          == ("lead", None, True, None),
          "R4: the ,stop modifier rides the retail-lead form")
    check(authsrv.parse_cancel_answer("lead:288,stop")
          == ("lead", 288.0, True, None),
          "R4: and the fixed-lead form")
    m, l, s, why = authsrv.parse_cancel_answer("suppress,stop")
    check(m is None and why is not None and "nothing for it to stop" in why,
          "suppress,stop is refused -- no leg is granted, so the stop "
          "modifier would be inert while the run log said R4 was on",
          f"{why!r}")
    m, l, s, why = authsrv.parse_cancel_answer("lead:0")
    check(m is None and why is not None and "768.5" in why,
          "lead:0 is the shipped answer wearing a flag -- refused, and the "
          "refusal names the bounds", f"({m}, {l}, {why!r})")
    m, l, s, why = authsrv.parse_cancel_answer("lead:banana")
    check(m is None and why is not None,
          "a non-number lead is refused, not defaulted")
    m, l, s, why = authsrv.parse_cancel_answer("supress")
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
    check('state["cancelwalk_leg_until"] = 0.0' in src
          and src.count("cw_leg / 288.0 + 1.0") == 1,
          "R4's leg window: cleared on every grant, re-armed only when the "
          "send was a cancelwalk lead under ,stop, sized to the leg at the "
          "client's own 288 u/s")
    check(src.count("if CANCEL_STOP and") == 1
          and "cw_dest is not None and CANCEL_STOP" in src
          and "cancelwalk stop" in src,
          "the stop arm's answer is guarded on CANCEL_STOP AND the live "
          "window -- outside it the general stop arm stays silent, which is "
          "what keeps this from being --stop-echo (REFUTED) under a new name")


def section_stop_answer():
    import authsrv

    print("6. R6 --stop-answer: parse, composition, wire shape, wiring")
    # Parse. Same contract as parse_cancel_answer: a mistyped arm must not
    # run the shipped default under an experiment's name.
    check(authsrv.parse_stop_answer(None) == (None, None),
          "no flag parses to no arm, no refusal")
    check(authsrv.parse_stop_answer("ack") == ("ack", None),
          "R6: ack")
    m, why = authsrv.parse_stop_answer("repin")
    check(m is None and why is not None and "--stop-echo" in why,
          "repin is refused as DELIBERATELY UNBUILT, and the refusal names "
          "the refuted flag whose wire effect it would resurrect -- the "
          "licensing decision lives in the refusal, where a cold session "
          "trips over it", f"{why!r}")
    m, why = authsrv.parse_stop_answer("akc")
    check(m is None and why is not None and "ack" in why,
          "a typo'd arm is refused LOUDLY and the refusal names the real "
          "arm", f"{why!r}")
    # Composition. R6 is registered against the SHIPPED configuration and
    # against ONE lever per run.
    why, _ = authsrv.zero_lead_composition(zero_lead=False, stop_answer="ack")
    check(why is not None and "--stop-answer requires --zero-lead" in why,
          "without --zero-lead the run answers a question nobody "
          "registered -- refused", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, stop_answer="ack",
                                           cancel_answer="suppress")
    check(why is not None and "--stop-answer and --cancel-answer" in why,
          "with --cancel-answer the run changes two levers and could "
          "attribute its outcome to neither -- refused", f"{why!r}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                               stop_answer="ack")
    check(why is None and any("R6" in n and "DIAGNOSTIC" in n
                              for n in notes),
          "allowed with --zero-lead, and the startup note names R6 and its "
          "diagnostic-only status", f"notes={notes}")
    why, _ = authsrv.zero_lead_composition(zero_lead=False,
                                           stop_answer="ack",
                                           cancel_answer="suppress")
    check(why is not None and "--stop-answer and --cancel-answer" in why,
          "all three flags at once gets the PAIRWISE refusal, not "
          "requires-zero-lead -- 'you passed two levers' is the more useful "
          "thing to be told, the plane/arrival pair's own precedent",
          f"{why!r}")
    # The constant, tied to the schema rather than restated beside it.
    check(authsrv.GAME_SMSG_AGENT_STOP_MOVING == 0x0028,
          "the constant is s2c 0x0028")
    import json
    here = os.path.dirname(os.path.abspath(authsrv.__file__))
    with open(os.path.join(here, "..", "..", "schema", "overrides.json"),
              encoding="utf-8") as fh:
        row = json.load(fh)["channels"]["GAME_SMSG"]["40"]
    check(row.get("name") == "AGENT_STOP_MOVING"
          and row.get("name_confidence") == "high",
          "the schema row this arm sends is the high-confidence "
          "AGENT_STOP_MOVING -- if the name or confidence moves, this arm's "
          "mechanism story moves with it and this check goes red",
          f"row name={row.get('name')!r}")
    # Wire shape. "A wrong ANSWER SHAPE from the server would be this
    # file's" (module docstring) -- encode THE BUILDER'S OWN OUTPUT, not a
    # literal this file typed for itself: a mutation pass planted
    # [PLAYER, 0] at the send site and a literal-encoding version of this
    # check stayed green. The send routes through agents.agent_stop_moving,
    # this check drives that same builder, and the source lock below pins
    # the send to it -- so corrupting the payload now reddens one of the
    # three.
    import agents
    body = agents.agent_stop_moving(PLAYER)
    check(body == [PLAYER],
          "the builder emits exactly [agent] -- one field, no destination, "
          "no plane, no speed, which is the whole licensing argument",
          f"{body}")
    try:
        agents.agent_stop_moving(0)
        check(False, "agent id 0 must raise -- it resolves no agent and the "
              "halt silently no-ops")
    except ValueError:
        check(True, "agent id 0 raises ValueError rather than building a "
              "silent no-op")
    sys.path.insert(0, os.path.join(here, "..", "schema"))
    import codec
    c = codec.Codec(overrides=os.path.join(here, "..", "..", "schema",
                                           "overrides.json"))
    wire = c.encode("GAME_SMSG", 0x0028, body)
    check(len(wire) == 6,
          "the ack is 6 bytes -- header + one agent dword, nothing else",
          f"{wire.hex()}")
    op, vals, used = c.decode_one("GAME_SMSG", wire)
    check(op == 0x0028 and vals[1] == PLAYER and used == 6,
          "and it decodes back to [0x0028, player] with zero residual",
          f"({op:#06x}, {vals}, {used})")
    # Wiring. The send site exists once, gated on the global, inside the
    # 0x0047 arm -- and the general stop arm stays otherwise silent.
    src = open(os.path.join(here, "authsrv.py"), encoding="utf-8").read()
    check(src.count('if STOP_ANSWER == "ack":') == 1
          and src.count("[cancelwalk R6 ") == 1
          and src.count("send(GAME_SMSG_AGENT_STOP_MOVING,") == 2
          and src.count("agents.agent_stop_moving(PLAYER_AGENT_ID)") == 2,
          "ONE R6 gate, ONE R6-labelled send, and exactly TWO 0x0028 send "
          "sites in the file (R6's stop-ack and R8's cast-stop, each behind "
          "its own gate), every payload from the builder the wire-shape "
          "check above drives -- a gate with the send deleted, a third "
          "site, or a hand-built payload would each redden this")
    check("STOP_ANSWER = None" in src,
          "the global defaults to None -- defaults are an owner ruling in "
          "this repo and no diagnostic ships on")
    check("_sa_mode, _sa_refusal = parse_stop_answer(a.stop_answer)" in src
          and "stop_answer=_sa_mode" in src
          and "STOP_ANSWER = _sa_mode" in src,
          "main() parses the flag through the pure parser, hands the MODE "
          "to the composition matrix, AND arms the global -- the refusals "
          "above cannot fire on a flag main() never routes, and the arm "
          "cannot regress to a banner-only inert flag (the R8 review "
          "found this arming pin missing HERE too)")


def section_cast_stop():
    import authsrv
    import agents

    print("7. R8/R10 --cast-stop: parse, reckon, composition, the burst")
    # Parse. Bare --cast-stop is 'halt' via argparse const; the parser
    # sees the two arm names and refuses everything else LOUDLY, the
    # refusal carrying the owner's ruling on the halt arm.
    check(authsrv.parse_cast_stop(None) == (None, None),
          "no flag parses to no arm, no refusal")
    check(authsrv.parse_cast_stop("halt") == ("halt", None),
          "R8: halt (also what bare --cast-stop parses to via const)")
    check(authsrv.parse_cast_stop("pin") == ("pin", None),
          "R10: pin")
    m, why = authsrv.parse_cast_stop("halr")
    check(m is None and why is not None and "pin" in why
          and "owner ruling 2026-08-25" in why,
          "a typo'd arm is refused LOUDLY, the refusal names both real "
          "arms AND the ruling that refused halt as a ship -- where a "
          "cold session trips over it", f"{why!r}")
    # Composition. Both arms are registered against the SHIPPED
    # configuration and against ONE lever per run; halt shares an opcode
    # with R6 and pin shares one with --resync, so each pair gets its own
    # cell.
    for mode in ("halt", "pin"):
        why, _ = authsrv.zero_lead_composition(zero_lead=False,
                                               cast_stop=mode)
        check(why is not None and "--cast-stop requires --zero-lead" in why,
              f"{mode}: without --zero-lead the run answers a question "
              f"nobody registered -- refused", f"{why!r}")
        why, _ = authsrv.zero_lead_composition(zero_lead=True,
                                               cast_stop=mode,
                                               cancel_answer="suppress")
        check(why is not None and "--cast-stop and --cancel-answer" in why,
              f"{mode}: with --cancel-answer the run changes two levers -- "
              f"refused", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, cast_stop="halt",
                                           stop_answer="ack")
    check(why is not None and "--cast-stop and --stop-answer" in why
          and "SAME opcode" in why,
          "with --stop-answer BOTH levers send 0x0028 on different "
          "triggers, so no halt could be attributed -- refused, and the "
          "refusal names the shared opcode", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, cast_stop="halt",
                                           arrival_carry=True)
    check(why is not None and "--cast-stop and --arrival-carry" in why,
          "with --arrival-carry the F1b queue would model an arrival the "
          "halt cut short -- refused", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=False, cast_stop="halt",
                                           arrival_carry=True)
    check(why is not None and "--cast-stop and --arrival-carry" in why,
          "and WITHOUT --zero-lead the same PAIRWISE cell fires, not "
          "arrival-requires-zero-lead -- placed low, that check handed out "
          "advice (--zero-lead --arrival-carry) the pairwise cell then "
          "refused on the next restart, which the adversarial pass caught "
          "live", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=False, cast_stop="halt",
                                           stop_answer="ack")
    check(why is not None and "--cast-stop and --stop-answer" in why,
          "all the levers at once gets the PAIRWISE refusal, not "
          "requires-zero-lead -- 'you passed two levers' is the more "
          "useful thing to be told, the plane/arrival pair's own "
          "precedent", f"{why!r}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, cast_stop="pin",
                                           resync=True)
    check(why is not None and "--cast-stop=pin and --resync" in why
          and "SAME opcode" in why,
          "pin with --resync: TWO 0x002C policies whose position models "
          "fight (extrapolate past vs teleport back to the report) -- "
          "refused, naming the shared opcode", f"{why!r}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                               cast_stop="halt", resync=True)
    check(why is None and any("REFUSED AS A SHIP" in n for n in notes),
          "halt with --resync still composes (different opcodes), and "
          "halt's note now carries the owner's ruling", f"notes={notes}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                               cast_stop="pin")
    check(why is None and any("R10" in n and "SHIPPED DEFAULT" in n
                              and "8.3g" in n for n in notes),
          "pin allowed with --zero-lead, and the startup note names R10 "
          "and its SHIPPED-DEFAULT status with the 8.3g ruling (it "
          "said DIAGNOSTIC ONLY until the owner ruled)", f"notes={notes}")
    # --resync-separation (2026-08-25, the P8 lever): a MODIFIER on the
    # resync verdict's one distance dial, wired for the registered negative
    # control (p5-resync-disarm.md sec.8 P8: raise it to 2000 so nothing
    # fires and the F35 snap must RETURN). Refused alone -- the inert-flag
    # defect --plane-carry's cell documents -- and refused non-positive or
    # non-finite; allowed with --resync, with the note naming the override
    # so a run log cannot claim the shipped cell it did not run.
    why, _ = authsrv.zero_lead_composition(zero_lead=True,
                                           resync_separation=2000.0)
    check(why is not None and "--resync-separation requires --resync" in why
          and "P8" in why,
          "--resync-separation alone: refused, naming its base flag and "
          "its registered use", f"{why!r}")
    for bad in (0.0, -100.0, float("nan"), float("inf")):
        why, _ = authsrv.zero_lead_composition(zero_lead=True, resync=True,
                                               resync_separation=bad)
        check(why is not None and "not a separation" in why,
              f"--resync-separation {bad!r}: refused as not a separation",
              f"{why!r}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True, resync=True,
                                               resync_separation=2000.0)
    check(why is None and any("THRESHOLD OVERRIDDEN" in n and "2000.0" in n
                              for n in notes),
          "--resync --resync-separation 2000: ALLOWED, and the note names "
          "the override and the P8 protocol", f"notes={notes}")
    why, _ = authsrv.zero_lead_composition(zero_lead=True, cast_stop="pin",
                                           resync=True,
                                           resync_separation=2000.0)
    check(why is not None and "--cast-stop=pin and --resync" in why,
          "and the pin-x-resync cell still outranks the modifier: two "
          "0x002C policies stay refused whatever the threshold",
          f"{why!r}")
    # The legacy bool, refused loudly at entry (re-review 2026-08-25):
    # cast_stop=True armed every shared refusal cell on truthiness while
    # matching neither mode -- no startup note, the pin-x-resync cell
    # dead, an on-but-unnamed arm for any API caller.
    try:
        authsrv.zero_lead_composition(zero_lead=True, cast_stop=True)
        legacy = None
    except ValueError as e:
        legacy = str(e)
    check(legacy is not None and "halt" in legacy and "pin" in legacy,
          "cast_stop=True (the pre-R10 bool) raises a loud ValueError "
          "naming both real modes -- never an on-but-unnamed arm",
          f"{legacy!r}")
    # The shipped-default resolver (8.3g: "pin it" -- the owner's ship
    # ruling, wired zero-lead-style), driven cell by cell. The DEFAULT
    # yields where an explicit mode refuses, so both halves are pinned:
    # yield here, the matrix's refusals above.
    R = authsrv.resolve_cast_stop_default
    check(R(None, False, True, None, None, False, False)
          == ("pin", "default", None),
          "bare startup runs pin -- the shipped default, owner's ruling "
          "2026-08-25 (8.3g), F28's fix")
    check(R(None, True, True, None, None, False, False)
          == (None, "off", None),
          "--no-cast-stop reverts the default")
    check(R(None, False, False, None, None, False, False)
          == (None, "no-zero-lead", None),
          "under --no-zero-lead the default follows the regime it "
          "modifies -- silently off with a note, never stranded on the "
          "requires-zero-lead refusal")
    for lever_args, name in (
            (("suppress", None, False, False), "--cancel-answer"),
            ((None, "ack", False, False), "--stop-answer"),
            ((None, None, True, False), "--arrival-carry"),
            ((None, None, False, True), "--resync")):
        got = R(None, False, True, *lever_args)
        check(got == (None, "lever:" + name, None),
              "the default YIELDS to an explicit " + name + " so that "
              "run keeps ONE variable -- the matrix still refuses the "
              "EXPLICIT pair", str(got))
    check(R("halt", False, True, None, None, False, False)
          == ("halt", "explicit", None)
          and R("pin", False, False, None, None, False, False)
          == ("pin", "explicit", None),
          "an explicit mode passes through untouched -- even without "
          "zero-lead, because the composition matrix owns that refusal "
          "and its message names the fix")
    m, w, why = R("pin", True, True, None, None, False, False)
    check(m is None and why is not None and "--no-cast-stop" in why
          and "contradict" in why,
          "--no-cast-stop alongside an explicit --cast-stop refuses "
          "loudly as a contradiction", repr(why))
    check(R(None, False, True, None, None, False, False)[0] != "halt",
          "and the default NEVER resolves to halt -- the control arm "
          "is explicit-only, REFUSED as a ship (Q10, F31/F34)")

    # The reckon, driven as a pure function -- the arithmetic the 0x002C
    # aims with, and every refusal door. The mesh is REQUIRED since the
    # 8.3a review (R2), so the base motion state carries a permissive
    # fake: walkable everywhere, clips nothing, resolves every plane to
    # the preferred one -- each door then closes it one way on purpose.
    class _FakePM:
        def __init__(self, ok=True, stop_at=None, plane="prefer"):
            self._ok, self._stop, self._plane = ok, stop_at, plane
        def walkable(self, x, y):
            return self._ok
        def clip(self, x0, y0, x1, y1, step=None):
            return self._stop if self._stop is not None else (x1, y1)
        def plane_at(self, x, y, prefer=None):
            return prefer if self._plane == "prefer" else self._plane

    def motion(**over):
        base = {"client_pos": (1000.0, -500.0), "client_pos_at": 100.0,
                "client_plane": 0, "kbd_moving_at": 100.0,
                "heading": (766.0, 0.0), "heading_mt": 1,
                "pathmap": _FakePM()}
        base.update(over)
        return base
    pt, pl, why = authsrv.cast_stop_reckon(motion(), 101.5)
    check(pt is not None and abs(pt[0] - 1432.0) < 1e-6
          and abs(pt[1] - (-500.0)) < 1e-6 and pl == 0
          and why == "reckoned",
          "a straight run reckons pos + unit(vec2) x 288 x dt exactly "
          "(1.5 s at 288 = 432 u east)", f"({pt}, {pl}, {why})")
    # B2 (review 2026-08-25): the rate is the census FAMILY's. The old
    # table (mt 4 = 0.66, everything else 1.0) reckoned a kiting or
    # strafing cast at 288 and hard-set the body FORWARD past the
    # registered 35 u bar.
    for mt in (2, 3):
        pt, _, _ = authsrv.cast_stop_reckon(motion(heading_mt=mt), 101.0)
        check(pt is not None and abs(pt[0] - 1288.0) < 1e-6,
              f"mt {mt} rides the forward family at 1.0 x 288", f"{pt}")
    for mt in (4, 5, 6):
        pt, _, _ = authsrv.cast_stop_reckon(motion(heading_mt=mt), 101.0)
        check(pt is not None
              and abs(pt[0] - (1000.0 + 0.652 * 288.0)) < 1e-6,
              f"mt {mt} rides the backward family at 0.652 x 288 = 187.8 "
              f"-- the census's OBSERVED 187.89, which R8's own mt=4 tape "
              f"corroborates at 190.1 (the old 0.66-for-mt-4-alone table "
              f"was B2)", f"{pt}")
    for mt in (7, 8):
        pt, _, _ = authsrv.cast_stop_reckon(motion(heading_mt=mt), 101.0)
        check(pt is not None
              and abs(pt[0] - (1000.0 + 0.75 * 288.0)) < 1e-6,
              f"mt {mt} rides the side family at 0.75 x 288 = 216 -- the "
              f"census's ~215, the weak row, LABELLED", f"{pt}")
    _, _, why = authsrv.cast_stop_reckon(motion(heading_mt=9), 101.0)
    check(why == "unverified-rate",
          "an mt outside the census's 1..8 has no observed rate and "
          "REFUSES instead of guessing -- the future-build door")
    # B1 (review 2026-08-25): the click-walk door, and its PRECEDENCE.
    _, _, why = authsrv.cast_stop_reckon(motion(click_moving_at=100.5),
                                         101.0)
    check(why == "click-walk",
          "a click in flight refuses as click-walk, not as parked or "
          "no-heading -- the label the send site suppresses the whole "
          "cast-stop on")
    _, _, why = authsrv.cast_stop_reckon({"click_moving_at": 1.0}, 101.0)
    check(why == "click-walk",
          "and it outranks no-report: a first-ever movement that is a "
          "click must not fire the halt through another door -- the "
          "0x0028 alone on a click-walking body is the B1 warp (corpus "
          "p50 1,164 u)")
    _, _, why = authsrv.cast_stop_reckon(motion(kbd_moving_at=None), 101.0)
    check(why == "parked",
          "kbd_moving_at cleared (the 0x0047 arm's stop) refuses: a "
          "parked body needs no pin")
    _, _, why = authsrv.cast_stop_reckon({}, 101.0)
    check(why == "no-report", "nothing heard yet refuses")
    _, _, why = authsrv.cast_stop_reckon(motion(pos_rejects=1), 101.0)
    check(why == "report-refused",
          "a refused newest report refuses the reckon -- _resync_verdict's "
          "own hole, guarded here too: a hard-set computed from a "
          "pre-refusal point is the warp through a new door")
    _, _, why = authsrv.cast_stop_reckon(
        motion(cast_stop_pin=(105.0, (9.0, 9.0))), 106.0)
    check(why == "pinned-parked",
          "a pin NEWER than the last report refuses: WE parked the body "
          "and the client never reports the halt -- the R8 second-cast "
          "trap, guarded")
    pt, _, why = authsrv.cast_stop_reckon(
        motion(cast_stop_pin=(99.0, (9.0, 9.0))), 101.0)
    check(pt is not None and why == "reckoned",
          "but a REPORT newer than the pin re-opens the reckon -- the "
          "client has spoken since we parked it")
    _, _, why = authsrv.cast_stop_reckon(motion(client_pos_at=200.0), 101.0)
    check(why == "future-report", "a future-dated report refuses")
    pt, _, why = authsrv.cast_stop_reckon(
        motion(pathmap=_FakePM(stop_at=(1100.0, -500.0))), 101.5)
    check(pt == (1100.0, -500.0) and why == "reckoned:clipped",
          "the navmesh clips the EXTRAPOLATED leg and the why says so",
          f"({pt}, {why})")
    # R2 (review 2026-08-25): a wire consumer gets NO standing-outside
    # suspension. This check used to assert the OPPOSITE -- that an
    # off-mesh start suspends the clip and reckons raw, clip_to_walkable's
    # own rule -- which shipped an unclipped ray of up to ~3.7 k u into a
    # hard-set of both copies from exactly the positions (5.5% of stops,
    # mesh edges) where our trapezoids are known-wrong.
    _, _, why = authsrv.cast_stop_reckon(
        motion(pathmap=_FakePM(ok=False)), 101.5)
    check(why == "off-mesh",
          "a reported point the mesh cannot vouch for REFUSES the reckon "
          "-- the honest degradation for a hard-set is the bare halt, "
          "never a raw ray")
    _, _, why = authsrv.cast_stop_reckon(motion(pathmap=None), 101.5)
    check(why == "no-mesh",
          "and no mesh in hand refuses the same way -- nothing can vouch "
          "for any point of the extrapolation")
    # R1 (review 2026-08-25): the plane is resolved AT the extrapolated
    # point, never copied from the report.
    pt, pl, why = authsrv.cast_stop_reckon(
        motion(client_plane=12, pathmap=_FakePM(plane=5)), 101.5)
    check(pt is not None and pl == 5 and why == "reckoned",
          "the 0x002C's plane comes from plane_at(est), not from the "
          "report -- slot 2 becomes the client's own current plane "
          "(agent+0x80), and a stale value there is the click arm's "
          "measured fall-through-under-stairs corruption", f"pl={pl}")
    _, _, why = authsrv.cast_stop_reckon(
        motion(pathmap=_FakePM(plane=None)), 101.5)
    check(why == "no-plane",
          "and where the geometry cannot say (plane_at None -- 'say "
          "nothing, never a guess'), the reckon refuses like every other "
          "door")
    # The burst, driven -- not grepped. handle_skill_press per mode and
    # per seeded motion state; labels recorded, because the pin arm's
    # refusal telemetry IS the 0x0028's label.
    saved_timing = authsrv.skill_timing
    saved_attack = authsrv._is_attack_skill
    saved_flag = authsrv.CAST_STOP
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        import contextlib
        import io

        def burst(flag, attack, seed=None):
            authsrv.CAST_STOP = flag
            authsrv._is_attack_skill = lambda sid: attack
            st = {"agents": {}}
            st.update(seed or {})
            sent = []
            send = lambda op, vals, label="", quiet=False: \
                sent.append((op, vals, label))
            # The console is captured because under pin-or-nothing (F34,
            # 8.3d) a REFUSED cast's label rides the print, not a 0x0028
            # -- the console line IS the scorable record, so a test that
            # cannot see it cannot protect the telemetry.
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                authsrv.handle_skill_press([0, 42, 7, 0], send, st,
                                           0, authsrv.GAME_CMSG_USE_SKILL)
            st["_console"] = buf.getvalue()
            return sent, st
        stops = lambda sent: [i for i, (op, _, _) in enumerate(sent)
                              if op == authsrv.GAME_SMSG_AGENT_STOP_MOVING]
        pins = lambda sent: [i for i, (op, _, _) in enumerate(sent)
                             if op == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION]
        off, _ = burst(None, False)
        check(stops(off) == [] and pins(off) == [],
              "flag OFF (the default): a spell press sends no 0x0028 and "
              "no 0x002C -- no diagnostic ships on", f"{off}")
        on, _ = burst("halt", False)
        check(len(stops(on)) == 1
              and on[stops(on)[0]][1] == [PLAYER]
              and pins(on) == []
              and "cancelwalk R8 cast-stop" in on[stops(on)[0]][2],
              "halt: a spell press sends exactly one 0x0028 [player], the "
              "builder's own payload, R8-labelled, and NO 0x002C", f"{on}")
        anim = [i for i, (op, vals, _) in enumerate(on)
                if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
                and vals[0] == agents.GV_SKILL_ACTIVATED]
        hold = [i for i, (op, vals, _) in enumerate(on)
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                and vals[0] == agents.GV_DISABLED and vals[2] == 1]
        check(len(anim) == 1 and len(hold) == 1
              and stops(on)[0] < anim[0] < hold[0],
              "and it rides first in the cast-begin TAIL: before the cast "
              "animation, which precedes the prop-8 hold -- the movement "
              "family closes before the action family opens (the E4 and "
              "the debits legitimately precede it; 'first in the burst' "
              "was the review-corrected overstatement)",
              f"stop={stops(on)}, anim={anim}, hold={hold}")
        atk, _ = burst("pin", True,
                       seed={"client_pos": (0.0, 0.0), "client_pos_at": 0.0,
                             "client_plane": 0, "kbd_moving_at": 0.0,
                             "heading": (766.0, 0.0), "heading_mt": 1,
                             "pathmap": _FakePM()})
        atk_anim = [i for i, (op, vals, _) in enumerate(atk)
                    if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
                    and vals[0] == agents.GV_ATTACK_SKILL_ACTIVATED]
        check(stops(atk) == [] and pins(atk) == [] and len(atk_anim) == 1,
              "ATTACK skill under pin, even with a moving belief seeded: "
              "the burst goes out (its own animation proves the press was "
              "not refused) and carries neither message -- both arms are "
              "scoped to NON-ATTACK casts", f"{atk}")
        # Pin, moving belief: 0x002C at the reckoned point, then the
        # 0x0028, in that order, and the pin note lands in state.
        import time as _time
        seed = {"client_pos": (1000.0, -500.0),
                "client_pos_at": _time.time() - 1.0, "client_plane": 0,
                "kbd_moving_at": _time.time() - 1.0,
                "heading": (766.0, 0.0), "heading_mt": 1,
                "pathmap": _FakePM(), "pos": (700.0, -500.0),
                "dest": (9999.0, -500.0)}
        pon, pst = burst("pin", False, seed=dict(seed))
        check(len(pins(pon)) == 1 and len(stops(pon)) == 1
              and pins(pon)[0] < stops(pon)[0],
              "pin, moving: exactly one 0x002C then one 0x0028, hard-set "
              "before halt", f"{pon}")
        pvals = pon[pins(pon)[0]][1]
        check(pvals[0] == PLAYER and pvals[2] == 0
              and 1250.0 < pvals[1][0] < 1330.0
              and abs(pvals[1][1] - (-500.0)) < 1e-6,
              "the 0x002C payload is [player, reckoned point, plane] -- "
              "~288 u east of a report ~1 s old", f"{pvals}")
        check("pin:reckoned" in pon[stops(pon)[0]][2]
              and isinstance(pst.get("cast_stop_pin"), tuple),
              "the 0x0028's label carries the fired reckon verdict and "
              "the pin note lands in state for the second-cast guard",
              f"label={pon[stops(pon)[0]][2]!r}")
        # R3 (review 2026-08-25): a SENT pin parks the server's own
        # integrator, not just the client's two copies.
        check(pst.get("dest") is None
              and pst.get("pos") == (pvals[1][0], pvals[1][1]),
              "the sent pin parks the model at the pin -- dest dropped, "
              "pos hard-set to the 0x002C's own point, so the 20 Hz tick "
              "stops walking a phantom past the pinned body",
              f"pos={pst.get('pos')}, dest={pst.get('dest')}")
        # R1 on the WIRE, not just at the pure reckon: the re-review's
        # lattice pass caught that every burst seed had client_plane=0
        # with a prefer-echoing fake mesh, so a mutation shipping the
        # REPORT's plane in the 0x002C payload stayed green. Report 12,
        # mesh 5: the sent plane must be the mesh's.
        pw, _ = burst("pin", False, seed=dict(seed, client_plane=12,
                                              pathmap=_FakePM(plane=5)))
        check(len(pins(pw)) == 1 and pw[pins(pw)[0]][1][2] == 5,
              "the SENT 0x002C carries plane_at(est)'s answer, not the "
              "report's: report says 12, the mesh says 5, the wire says "
              "5 -- the stale-plane fall-through corruption cannot ride "
              "the payload", f"{pw[pins(pw)[0]][1]}")
        # Pin, second cast, no report since: the guard refuses the
        # 0x002C and the label says why. `.get`, not a subscript: under
        # the M7 mutation (the pin note never written) a subscript
        # KeyError'd here and ABORTED the section, so every later check
        # ran as a traceback instead of a named FAIL -- the weaker
        # guard, caught by the re-run mutation probe.
        p2, p2st = burst("pin", False, seed=dict(seed,
                         cast_stop_pin=pst.get("cast_stop_pin")))
        check(pins(p2) == [] and stops(p2) == []
              and "[cancelwalk pin:pinned-parked]" in p2st["_console"],
              "pin, second cast with no report between: NOTHING goes out "
              "-- pin-or-nothing (F34) -- the R8 second-cast trap "
              "guarded live, the refusal named on the console line",
              f"{p2st['_console']!r}")
        # Pin, parked belief: NOTHING goes out. Until 8.3d the 0x0028
        # went alone here, licensed by 'no-ops on a parked body' --
        # REFUTED by R10's run (F34): with the SYNC COPY still
        # converging it warped a genuinely parked body 167.6 u backward
        # onto the copy. The handler answers for the copy, not the
        # drawn body, so the only send that cannot warp is none.
        pk, pkst = burst("pin", False, seed=dict(seed, kbd_moving_at=None))
        check(pins(pk) == [] and stops(pk) == []
              and "[cancelwalk pin:parked]" in pkst["_console"]
              and "pin-or-nothing" in pkst["_console"],
              "pin, parked belief: NO 0x002C and NO 0x0028 -- the F34 "
              "regime (parked body, converging copy) gets no message to "
              "warp with -- and the console line carries the label",
              f"{pkst['_console']!r}")
        pk_anim = [i for i, (op, vals, _) in enumerate(pk)
                   if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
                   and vals[0] == agents.GV_SKILL_ACTIVATED]
        check(len(pk_anim) == 1,
              "and the cast itself still goes out -- the suppression is "
              "the cast-stop's, not the cast's", f"{pk}")
        # B1 (review 2026-08-25): a click-walk suppresses the WHOLE
        # cast-stop -- both arms, both messages. The seed keeps the
        # moving keyboard belief armed, so without the click latch this
        # is exactly the burst that fired both messages above.
        for mode in ("pin", "halt"):
            ck, ckst = burst(mode, False,
                             seed=dict(seed, click_moving_at=_time.time()))
            ck_anim = [
                i for i, (op, vals, _) in enumerate(ck)
                if op in (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
                and vals[0] == agents.GV_SKILL_ACTIVATED]
            check(stops(ck) == [] and pins(ck) == [] and len(ck_anim) == 1
                  and "[cancelwalk pin:click-walk]" in ckst["_console"],
                  f"{mode}, click-walk in flight: NO 0x0028 and NO 0x002C "
                  f"-- a click-walking body is one no belief can place, "
                  f"and the 0x0028 alone is the B1 warp (sync copy parked "
                  f"at the leg's start, corpus p50 1,164 u); the burst "
                  f"itself still goes out (the animation proves the press "
                  f"was not refused) and the cast glides -- F28, a defect "
                  f"but not a warp", f"{ck}")
    finally:
        authsrv.skill_timing = saved_timing
        authsrv._is_attack_skill = saved_attack
        authsrv.CAST_STOP = saved_flag
    # Source locks: one gate, one site per opcode, default None, and
    # main() routes the PARSED mode into the composition matrix and the
    # global.
    here = os.path.dirname(os.path.abspath(authsrv.__file__))
    src = open(os.path.join(here, "authsrv.py"), encoding="utf-8").read()
    check(src.count("if CAST_STOP and not is_attack:") == 1
          and src.count("cancelwalk R8 cast-stop") == 1
          and src.count("CAST-STOP PIN 0x002C") == 1
          and src.count("cancelwalk R10") >= 1,
          "ONE gate carrying the non-attack scoping, ONE R8-labelled "
          "0x0028 site, ONE R10 0x002C site")
    check(src.count("if _cs_send_stop:") == 1
          and src.count("_cs_send_stop = False") == 1
          and src.count("_cs_send_stop = True") == 1,
          "pin-or-nothing (F34) is wired as ONE gate on the 0x0028 send: "
          "armed once (halt's default), disarmed once (the pin refusal "
          "branch), consulted once -- with the gate deleted the bare "
          "0x0028 returns and F34's 167.6 u parked-body warp with it")
    check(src.count('state["click_moving_at"] = time.time()') == 1
          and src.count('state["click_moving_at"] = None') == 3
          and src.count('_cs_click = state.get("click_moving_at")') == 1
          and "pin:click-walk" in src,
          "B1's latch is wired where the review said it must be: armed "
          "in ONE place (the 0x003E arm, every click), cleared in THREE "
          "(the 0x003D and 0x0047 arms -- the client speaking again -- and "
          "since ANIMREF-RE 39 the attack press, which ENDS the leg it "
          "finds in flight: _press_supersedes), "
          "and the send site consults it before EITHER arm, printing the "
          "click-walk label the capture scores")
    check(src.count("_cs_mode, _cs_why, _cs_refusal = resolve_cast_stop_default(") == 1
          and '"--no-cast-stop", action="store_true"' in src
          and 'if _cs_why == "default":' in src
          and "ON by default -- owner's ruling" in src,
          "the shipped default is wired through the PURE resolver -- "
          "called once in main(), --no-cast-stop registered, and the "
          "default-on short banner keyed on the resolver's own "
          "provenance, so the log always says WHY the arm is on")
    check(src.count("CAST_STOP = None") == 1
          and src.count("CAST_STOP = _cs_mode") == 1
          and "cast_stop=_cs_mode" in src
          and "_cs_mode, _cs_refusal = parse_cast_stop(a.cast_stop)" in src
          and "global CAST_STOP" in src,
          "the global defaults to None (defaults are an owner ruling), "
          "main() parses through the pure parser and routes the MODE into "
          "both the composition matrix and the global, AND the arming "
          "assignment itself is pinned -- with 'CAST_STOP = _cs_mode' "
          "deleted the flag would print a full banner and send NOTHING, "
          "the inert-flag defect on a readout the wire cannot even see")
    # The --resync-separation rebind, pinned the same way and for the same
    # reason (the 2026-08-25 review's mutation (c) survived every test in
    # the tree until this check): the rebind in main() is the lever's ONLY
    # action, so with it deleted `--resync --resync-separation 2000` would
    # print THRESHOLD OVERRIDDEN on the composition note AND the RULE tail
    # while _resync_verdict fired at the shipped 100.0 -- P8's
    # nothing-fires control firing ~5.6/min under a console that claims
    # the 2000 u cell. That is the inert-flag defect the lever's own
    # refusal text documents, on the lever itself.
    check(src.count("RESYNC_SEPARATION = a.resync_separation") == 1
          and src.count("if a.resync_separation is not None:") >= 1
          and "resync_separation=a.resync_separation" in src
          and src.count("global RESYNC, RESYNC_SEPARATION") == 1,
          "the override rebind is pinned by name: threaded into the "
          "composition call, guarded on the flag being passed, and "
          "assigned through the declared global exactly once -- with the "
          "assignment deleted the console would claim a threshold the "
          "verdict does not run")


def main():
    section_parse()
    section_lead_formula()
    section_composition()
    section_hit_kind()
    section_handler_wiring()
    section_stop_answer()
    section_cast_stop()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
