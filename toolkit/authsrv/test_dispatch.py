"""D9(a) -- unhandled-but-known c2s is visible, and both chains have an else.

    python toolkit/authsrv/test_dispatch.py

studies/divergence D9(a): both dispatch chains in `handle()` used to end
without an `else`, so a schema-KNOWN opcode with no handler was printed as
received and then fell off the end of the chain -- nothing sent, nothing
logged as a miss, socket healthy. 19 distinct GAME_CMSG opcodes and 1,126 of
11,502 game-channel messages in our own corpus, and worse against live shapes.

Two halves, kept apart deliberately.

**Behaviour** (sections 1-3) exercises `note_unhandled`/`report_unhandled`
directly, because the thing that matters is not that an `else` exists but that
the miss becomes READABLE without burying the log. The design is
first-occurrence-prints, rest-counted, tally-at-disconnect, and each of those
three is checked including the one that is easy to get wrong: a labelled run
suppresses the ECHO and must still COUNT, or the fix silently turns itself off
in exactly the sessions where an operator is watching for it.

**Structure** (section 4) asserts the two `else` arms exist, VIA THE AST rather
than by matching source text. `test_cmsgnames.py` had a grep that asserted its
arm's formatting instead of its content, and went red the day the arm grew a
guard and wrapped across two lines. An `else` is a syntactic fact, so ask the
syntax tree: a real `else` is an `If.orelse` that is not a lone nested `If`
(which is what an `elif` compiles to). Section 5 then breaks each structural
claim on purpose and requires the detector to go red -- a structural check that
cannot fail is not a check, and this one is easy to write so that it cannot.

Standard library only. No vault, no socket, no client.
"""
import ast
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402

LEDGER = checks.Ledger("dispatch catch-all (D9a)", floor=18)

AUTHSRV_PY = os.path.join(HERE, "authsrv.py")


class FakeRec:
    """Minimal stand-in for the capture recorder: remembers what it was told."""

    def __init__(self):
        self.events = []

    def event(self, kind, **kw):
        self.events.append((kind, kw))


def else_block_calls(tree, fname):
    """String-literal args of calls to `fname` that sit in a REAL `else`.

    An `elif` is represented as a lone `If` inside `orelse`; a real `else` is
    anything else. That distinction is the whole point -- a check that accepted
    an `elif` would pass against the very shape D9(a) describes.
    """
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        orelse = node.orelse
        if not orelse or (len(orelse) == 1 and isinstance(orelse[0], ast.If)):
            continue
        for stmt in orelse:
            for call in ast.walk(stmt):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == fname):
                    out.extend(a.value for a in call.args
                               if isinstance(a, ast.Constant)
                               and isinstance(a.value, str))
    return out


def has_kind_ne_auth(tree):
    """Is the unreachable `kind != "auth"` branch back?"""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "kind"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.NotEq)
                and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value == "auth"):
            return True
    return False


def main():
    import authsrv
    import labelrun

    src = open(AUTHSRV_PY, encoding="utf-8").read()
    tree = ast.parse(src)

    # ---- 1. the first occurrence is loud, the rest are counted ---------------
    state, rec = {}, FakeRec()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.note_unhandled(state, 1, "GAME_CMSG", 0x0092, "?", rec)
    first_out = buf.getvalue()
    LEDGER.ok("UNHANDLED" in first_out and "0x8092" in first_out,
              "a first unhandled opcode prints, and prints the wire form",
              f"got {first_out.strip()!r} -- the client ORs 0x8000 into every "
              f"game-channel opcode it sends, so 0x8092 is what an operator "
              f"reading a packet log will be looking for, not 0x0092")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        for _ in range(40):
            authsrv.note_unhandled(state, 1, "GAME_CMSG", 0x0092, "?", rec)
    LEDGER.ok(buf.getvalue() == "",
              "and the next 40 of the same opcode print NOTHING",
              f"got {buf.getvalue()!r}. 0x8009 alone is 19.3% of live game "
              f"c2s -- printing every one is how a real defect gets scrolled "
              f"off the top of a terminal")
    LEDGER.ok(state["unhandled"][("GAME_CMSG", 0x0092)] == 41,
              "but all 41 are counted",
              f"count={state['unhandled'].get(('GAME_CMSG', 0x0092))}")

    unhandled_events = [e for e in rec.events if e[0] == "unhandled"]
    LEDGER.ok(len(unhandled_events) == 1,
              "the capture records the miss exactly once, not 41 times",
              f"{len(unhandled_events)} events")
    LEDGER.ok(unhandled_events[0][1].get("opcode") == 0x0092
              and unhandled_events[0][1].get("channel") == "GAME_CMSG",
              "and it names the channel, because the two catalogs collide",
              f"{unhandled_events[0][1]} -- GAME_CMSG 0x0002 is TRADE_ADD_ITEM "
              f"and AUTH_CMSG 0x0002 is SEND_COMPUTER_HASH, so an opcode "
              f"without its channel is ambiguous")

    # a second distinct opcode is its own first occurrence
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.note_unhandled(state, 1, "GAME_CMSG", 0x0027, "ATTACK_SKILL", rec)
    LEDGER.ok("UNHANDLED" in buf.getvalue(),
              "a DIFFERENT opcode is loud on its own first occurrence",
              f"got {buf.getvalue().strip()!r}")
    LEDGER.ok(len(state["unhandled"]) == 2,
              "and the two are tracked separately",
              f"{sorted(state['unhandled'])}")

    # ---- 2. a labelled run silences the echo and must NOT silence the count --
    state2, rec2 = {}, FakeRec()
    was_active = labelrun.ACTIVE
    try:
        labelrun.ACTIVE = True
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            for _ in range(5):
                authsrv.note_unhandled(state2, 2, "GAME_CMSG", 0x0040, "ROTATE", rec2)
        echo = buf.getvalue()
    finally:
        labelrun.ACTIVE = was_active
    LEDGER.ok(echo == "",
              "a labelled run suppresses the echo",
              f"got {echo!r} -- the operator is reading a countdown in that "
              f"terminal and one movement step prints tens of lines a second")
    LEDGER.ok(state2["unhandled"][("GAME_CMSG", 0x0040)] == 5,
              "and STILL COUNTS all five -- the failure that would turn this "
              "fix off in exactly the sessions someone is watching",
              f"count={state2['unhandled'].get(('GAME_CMSG', 0x0040))}")
    LEDGER.ok(any(e[0] == "unhandled" for e in rec2.events),
              "and still records to the capture, which no terminal owns",
              f"{[e[0] for e in rec2.events]}")

    # ---- 3. the tally at disconnect -----------------------------------------
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.report_unhandled({}, 3, FakeRec())
    LEDGER.ok(buf.getvalue() == "",
              "a session that handled everything reports NOTHING",
              f"got {buf.getvalue()!r} -- a summary line that always prints "
              f"is one an operator learns to skip")

    rec3 = FakeRec()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.report_unhandled(state, 1, rec3)
    tally = buf.getvalue()
    LEDGER.ok("42" in tally and "2 opcodes" in tally,
              "and one that did names the total and the opcode count",
              f"got {tally.strip()!r} (41 of 0x0092 + 1 of 0x0027 = 42)")
    LEDGER.ok("0x8092x41" in tally,
              "with a per-opcode breakdown, busiest first",
              f"got {tally.strip()!r}")
    summary = [e for e in rec3.events if e[0] == "unhandled_summary"]
    LEDGER.ok(len(summary) == 1 and summary[0][1].get("total") == 42,
              "and the capture carries the same number the terminal showed",
              f"{summary}")

    # ---- 4. both chains really do end in an else, asked of the syntax tree ---
    channels = else_block_calls(tree, "note_unhandled")
    LEDGER.ok("GAME_CMSG" in channels,
              "the GAME dispatch chain ends in a real else (AST, not a grep)",
              f"else-blocks calling note_unhandled: {channels}")
    LEDGER.ok("AUTH_CMSG" in channels,
              "and so does the AUTH chain",
              f"else-blocks calling note_unhandled: {channels}")
    LEDGER.ok(not has_kind_ne_auth(tree),
              "and the unreachable `kind != \"auth\"` branch is gone",
              "`kind` is two-valued from one site, so that branch could never "
              "run -- dead code that reads like a catch-all, directly above a "
              "real catch-all, is worse than no code")

    # ---- 5. the structural checks must be able to go RED ---------------------
    # Sabotage 1: demote the game else to an elif. This is the exact shape
    # D9(a) describes, so a detector that passes it is measuring nothing.
    sab = ast.parse(
        "def f():\n"
        "    if a == 1:\n"
        "        pass\n"
        "    elif a == 2:\n"
        "        note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    LEDGER.ok(else_block_calls(sab, "note_unhandled") == [],
              "CONTROL: a call in an ELIF is not counted as an else",
              "an elif is a lone If inside orelse; accepting it would pass "
              "against the very defect being fixed")

    # Sabotage 2: no else at all.
    sab2 = ast.parse(
        "def f():\n"
        "    if a == 1:\n"
        "        pass\n"
        "    elif a == 2:\n"
        "        pass\n")
    LEDGER.ok(else_block_calls(sab2, "note_unhandled") == [],
              "CONTROL: a chain with no else at all scores zero",
              "this is authsrv.py as it stood before 2026-08-11")

    # Sabotage 3: the dead branch, reintroduced.
    sab3 = ast.parse('def f():\n    if kind != "auth":\n        pass\n')
    LEDGER.ok(has_kind_ne_auth(sab3),
              "CONTROL: the dead-branch detector finds it when it IS there",
              "otherwise the check above passes for the wrong reason")

    # Sabotage 4: a real else that calls something else entirely.
    sab4 = ast.parse(
        "def f():\n"
        "    if a == 1:\n"
        "        pass\n"
        "    else:\n"
        "        something_else(s, c, 'GAME_CMSG')\n")
    LEDGER.ok(else_block_calls(sab4, "note_unhandled") == [],
              "CONTROL: an else that does not call note_unhandled scores zero",
              "an empty `else: pass` would satisfy 'has an else' while "
              "restoring the silence D9(a) is about")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
