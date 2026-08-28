"""MOVECODE-K2: the click echo answers STALENESS and never geometry.

    python toolkit/authsrv/test_clickecho.py

WHY THE CHECKS ARE MOSTLY STRUCTURAL. The change lives inside the 0x003E handler in
`handle()`, which needs a socket, a key exchange and a live client to reach -- so
there is no pure function to drive the way `_keepalive_ok` and `_position_verdict`
can be driven. What CAN be pinned is the shape of the decision, and for this flag the
shape IS the claim:

  * it must fall through on `not fresh` and on NOTHING ELSE. `geo-unplaced` and
    `geo-blocked` are a different defect (FINDINGS §1i.5 separates them: 13 staleness
    against 4 geometry) and a flag that quietly answered geometry refusals too would
    be re-running the railing graveyard with a new name.
  * the point it sends must be the CLICK'S OWN `dest`, unclipped. Both of
    `--heading-grant`'s named failures were about the point: computed from
    `state["pos"]` rather than the report in hand, and shortened by our navmesh.

Those are exactly the properties a later edit would break without breaking anything
observable, which is what `test_movehook.py` §11 exists for on the other side of the
repo. §5 is the negative control: `CLICK_ECHO` off must leave the shipped refusal
literally unchanged.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import checks                                                    # noqa: E402
import authsrv                                                   # noqa: E402

# MEASURED off a real green run, 2026-08-27, counted per section off the banner.
#   §1  3  the flag is off, and registered            process-free
#   §2  5  the gate is STALENESS-ONLY                 process-free (source)
#   §3  5  the echoed point is the click's own dest   process-free (source)
#   §4  3  the verdict row records the echo           process-free (source)
#   §5  3  off leaves the shipped refusal untouched   process-free (source)
#  ---- every section is process-free, so the floor is the whole run.
LEDGER = checks.Ledger("clickecho", floor=19)
check = checks.adopt(LEDGER)

SRC = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()


def refusal_block():
    """The geometry/staleness refusal, as source text.

    Anchored on its own content rather than on line numbers, so these checks cannot
    drift onto a different block when the file moves.
    """
    start = SRC.index("k2_echo = bool(CLICK_ECHO)")
    end = SRC.index("if TRACE_MOVE:", start)
    return SRC[start:end]


# ------------------------------------------------------------------ §1
def section_1():
    check(authsrv.CLICK_ECHO is False,
          "1. CLICK_ECHO defaults to False",
          "a seventh candidate that shipped ON would put an unmeasured answer on "
          "the wire for every session")
    names = set()
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.Call) and getattr(
                node.func, "attr", None) == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.add(arg.value)
    check("--click-echo" in names, "1. --click-echo is registered in argparse")
    check("MOVECODE-K2" in SRC and "sec.1m" in SRC,
          "1. and it names its arc and its registered prediction",
          "a flag whose prediction is not written down can be rationalised into "
          "agreeing with whatever the run produced")


# ------------------------------------------------------------------ §2
def section_2():
    blk = refusal_block()
    check("k2_echo = bool(CLICK_ECHO) and not fresh" in blk,
          "2. the echo gate is CLICK_ECHO **and not fresh**",
          "staleness only -- this is the whole scope of the flag")
    check("not placed" not in blk.split("k2_echo =")[1].split("\n")[0],
          "2. and the gate does not consult `placed`",
          "geo-unplaced is a geometry refusal and must keep refusing")
    # The fall-through condition must require BOTH the shipped flag being off AND
    # the echo being off, or the flag would change behaviour under D1_LEAD too.
    check("if not D1_LEAD and not k2_echo:" in blk,
          "2. the refusal fires only when D1_LEAD is off AND the echo is off",
          "so K2 composes with the bundle instead of racing it")
    # And the three reasons must still be distinguishable in the row.
    check(all(r in blk for r in ("geo-stale", "geo-unplaced", "geo-blocked")),
          "2. all three refusal reasons are still named separately",
          "FINDINGS sec.1i.5 needs the split to stay countable per arm")
    check("continue" in blk,
          "2. and a refusal still ends the handler for that click",
          "a fall-through that forgot to refuse would answer geometry too")


# ------------------------------------------------------------------ §3
def section_3():
    """The point that goes out must be the click's own, unclipped."""
    i = SRC.index("send(GAME_SMSG_AGENT_MOVE_TO_POINT,\n"
                  "                             [PLAYER_AGENT_ID, list(dest),")
    send = SRC[i:i + 400]
    check("list(dest)" in send,
          "3. the click answer sends `dest` -- the client's own clicked point",
          "not a lead, not a model position; --heading-grant died of computing "
          "its point from state[\"pos\"]")
    check("state[\"pos\"]" not in send,
          "3. and never state[\"pos\"]")
    check("clip" not in send,
          "3. and it is not clipped",
          "--heading-grant's other named failure was a point shortened by OUR "
          "navmesh where the client's own collision disagrees")
    # The echo reaches that send by FALLING THROUGH, so every `continue` between
    # the gate and the send is a place the echo can still die. There are exactly
    # two and both are deliberate:
    #   1. the refusal itself, which the echo has just skipped;
    #   2. the RATE GATE (`if not may_grant`), which the echo passes through ON
    #      PURPOSE -- it is where GRANT_SUPPRESS's floor and its
    #      "dropped under active keyboard authority" rule live, and retail's
    #      measured contract drops that click too. An echo that bypassed the rate
    #      gate would out-run retail's own cadence, which is how the
    #      reproduction ran at 0.13 s against retail's 0.49 s.
    # A THIRD would be a path that swallows the echo silently, and that is what
    # this count is here to catch.
    between = SRC[SRC.index("if not D1_LEAD and not k2_echo:"):i]
    check(between.count("continue") == 2,
          "3. exactly TWO `continue`s sit between the gate and the send",
          f"found {between.count('continue')} -- the refusal and the rate gate. "
          f"A third would swallow the echo before it reached the wire")
    check("if not may_grant:" in between,
          "3. and the second is the RATE GATE, which the echo passes through",
          "so K2 cannot out-run retail's cadence and a click under active "
          "keyboard authority is still dropped")


# ------------------------------------------------------------------ §4
def section_4():
    blk = refusal_block()
    check("click_echo=bool(k2_echo)" in blk,
          "4. the click_verdict row records whether it echoed",
          "an arm cannot be scored on a decision the log does not carry")
    check("fired=bool(k2_echo)" in blk,
          "4. and `fired` reflects the echo",
          "a row saying fired=False beside a grant on the wire would make the "
          "census disagree with the capture")
    check("rec.event(\"click_verdict\"" in blk,
          "4. and every refusal is still a row",
          "138 of 260 clicks once died on this branch with no trace but a "
          "console line, and the census had to be reconstructed by subtraction")


# ------------------------------------------------------------------ §5
def section_5():
    """OFF must leave the shipped path byte-identical in behaviour."""
    blk = refusal_block()
    # With CLICK_ECHO False, k2_echo is False, so the condition reduces to the
    # original `if not D1_LEAD:` and the print/continue are unchanged.
    check(authsrv.CLICK_ECHO is False and "not k2_echo" in blk,
          "5. with the flag off the gate reduces to the shipped condition",
          "bool(False) and X is False whatever X is, so `not D1_LEAD and not "
          "k2_echo` is exactly `not D1_LEAD`")
    check("leaving it to " in blk and "the client's own pathing" in blk,
          "5. and the shipped refusal message is untouched",
          "the literal is split across two source lines, so match both halves "
          "rather than a string that never appears")
    # The echo's own log line must be distinguishable from the refusal's.
    check("ECHOING it" in blk,
          "5. while the echo announces itself differently",
          "two different decisions printing the same line is how a run gets "
          "scored as the wrong arm")


def main():
    section_1()
    section_2()
    section_3()
    section_4()
    section_5()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
