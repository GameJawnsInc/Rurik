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

SECTIONS 6-9, ADDED 2026-08-13, are about the OTHER half of D9(a), and the
distinction is the point of them. Making a drop VISIBLE is not the same as not
dropping it, and for two years the visible answer was accepted as the whole fix.
Measured over `vault/captures/gamesrv/*.jsonl` on 2026-08-13 -- 425 connections,
17,770 framed c2s messages -- 2,858 of them (16.1%) reached the `else` and were
thrown away, and FOUR of the opcodes in that pile were ones `overrides.json` had
already NAMED from the client's own binary and ArenaNet's own wire:

    0x0039 INTERACT            3.2% of live c2s, and NO ARM AT ALL, while
                               0x0033 -- which does have one -- has been sent
                               ZERO times in all 17,770 messages since
                               2026-08-06
    0x0092 MISSION_MASK_REPORT 803 arrivals, a 112-byte progress bitmask
    0x00C1 TARGET_SELECT       363 arrivals, fully named
    0x0040 ROTATE_PLAYER       108 arrivals, fully named

Sections 6 and 8 pin the arms that were added for those. Section 7 is the check
that could have caught the class, and its DESIGN is deliberate:

  * The forward direction -- every opcode with an arm is one the schema knows --
    is a hard failure. An arm on an opcode the framer will refuse can never run,
    so it is dead code that reads as coverage.
  * The direction that matters -- an opcode `overrides.json` has NAMED and no arm
    dispatches on -- is a REPORT against a named allowlist, not a bare failure.
    194 GAME_CMSG layouts have arms for sixteen, and demanding an arm per layout
    would be a permanently red test that gets deleted. But a NAME in
    `overrides.json` is not free: somebody read the client's binary or narrated a
    live session to earn it, and every one of the four above was named and then
    dropped anyway. So the rule is: named implies handled OR listed, and the
    failure text is "a named opcode was dropped and nobody listed it as
    intentional". `DROPPED_ON_PURPOSE` carries a REASON per row, so listing one
    is a decision on the record rather than a silent skip -- the same shape
    `test_provlint.py` uses for its citation ceiling.
  * The allowlist is checked in BOTH directions too, because a stale row is how
    this check would quietly stop working: a row for an opcode that IS handled
    would sit there silently re-permitting the drop if the arm were ever removed.

Standard library only. No vault, no socket, no client -- deliberately, and it
constrains what sections 6-9 may assert. The capture tree is append-only and
GROWING WHILE THIS RUNS (0x00C1 went 363 -> 429 between two reads minutes apart
on 2026-08-13, because another session's server was writing into it), so not one
corpus count appears as an assertion here. The counts above are dated prose; the
assertions are all about the source and the schema, which are in git.
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
from codec import Codec, Undecodable  # noqa: E402

# 45, MEASURED from the green run of 2026-08-13 and not guessed. Every check in
# this file is unconditional -- no vault, no socket, no client, and the one loop
# runs a fixed four -- so the floor is the exact count rather than a mandatory
# core. It was 20 against a run of 23 before sections 6-9; a floor left trailing
# its run is a floor that would not notice a whole section going missing.
LEDGER = checks.Ledger("dispatch catch-all (D9a)", floor=45)

AUTHSRV_PY = os.path.join(HERE, "authsrv.py")

# GAME_CMSG opcodes `overrides.json` NAMES and this server deliberately does not
# dispatch. Each row is a decision on the record; an unlisted named opcode is the
# failure section 7 exists for. Delete a row when you add its arm -- section 7
# fails on a stale row too, because a row for a handled opcode would silently
# re-permit the drop if the arm were ever taken back out.
#
# Loopback counts are from the 2026-08-13 sweep and are prose, not assertions.
DROPPED_ON_PURPOSE = {
    0x000A: "SEND_MACHINE_SPEC (421 loopback arrivals) -- a one-shot hardware "
            "census the client pushes from a connection-established callback: "
            "CoCreateGuid, GetSystemInfo, CPUID, RtlGetVersion, "
            "GlobalMemoryStatusEx. Every field is about the MACHINE and none is "
            "about the world, and ArenaNet's server sends nothing back. There is "
            "no state here for a game server to hold.",
# 0x0012 REQUEST_QUEST_INFO was here, and its reason was "answering it needs a
# quest table this repo does not have, and inventing quest text is worse than
# the drop". ARMED 2026-08-15: content/quests.toml is that table, and the text
# is invented ON PURPOSE rather than transcribed -- ArenaNet's own description
# ids resolve to encrypted archive records whose key is NOT FOUND, so their
# words were never reachable to copy. studies/quests/ is the study the reason
# was waiting on.
    0x002B: "COMPASS_DRAW (5 loopback, 1 live) -- the player drawing or "
            "pinging on their own compass: a client-allocated stroke handle "
            "plus 1-16 knots, each two signed int16 packed low-half-first in "
            "one dword, in ABSOLUTE world coordinates divided by the terrain "
            "cell pitch. Answering it means rebroadcasting GAME_SMSG 0x0091 to "
            "the rest of the party with a NON-ZERO owner tag -- zero is the "
            "drawing client's own value (0x008BF43B), so a zero echo makes the "
            "drawer's client merge the broadcast into its own line and double "
            "the stroke -- and the drawer probably should not receive the echo "
            "at all. THIS SERVER HAS NO PARTY, so there is nobody to broadcast "
            "to; the drop costs nothing today and the work is one arm the day a "
            "second client connects. studies/minimap/FINDINGS.md 4.1.",
# 0x003B NPC_SERVICE_SELECT was here, blocked behind 0x0039 -- "this server does
# not answer an interaction, so no window is ever open and no selection can be
# made. Handle it when INTERACT gets a reply." ARMED 2026-08-15: INTERACT got its
# reply (0x0080 + 0x0081, Q4, a window on screen), so the block is gone and the
# arm decodes 0x800000 | (quest_id << 8) | code. Only the QUEST family is
# handled; the other four service families named in overrides.json have never
# appeared on any wire this repo holds, and the arm says so rather than guessing.
    0x0060: "CHAR_CREATE_SET_CHAPTER_PROFESSION (0 loopback, 10 live) -- "
            "character creation, which this server does not implement at all: "
            "it serves one fixed character from content/, and the create flow "
            "has never been driven end to end.",
    0x0064: "CHAT_SEND (7 loopback) -- REAL MISSING WORK. Field 2 carries the "
            "typed text verbatim, emotes included, so this is the whole chat and "
            "emote surface. It needs a GAME_SMSG echo to be worth anything, and "
            "a handler that stored the text and echoed nothing would look "
            "implemented while the client showed silence.",
    0x0084: "CHAR_CREATE_SET_EQUIP_COLOR (0 loopback, 70 live) -- character "
            "creation, same as 0x0060.",
}


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


def called_in_finally(tree, fname):
    """Is `fname` called from a `finally:` block?

    Reachability, not behaviour -- and it is the check that was missing. The
    summary calls sat after the read loop inside the `try` and NEVER RAN: the
    loop exits by ConnectionResetError because the harness kills the client, so
    control jumps to `except`. Every behavioural test passed the whole time,
    because they call the function directly and so never ask whether anything
    else does.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for stmt in node.finalbody:
            for call in ast.walk(stmt):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == fname):
                    return True
    return False


def int_constants(tree):
    """{name: value} for every module-level `NAME = <int literal>` in `tree`.

    The dispatch arms compare against constants by name, so an arm harvester has
    to resolve them. Reading them out of the SAME tree rather than off the
    imported module is what lets section 9 build a self-contained fixture -- a
    control that had to import a module could only ever be run against the real
    one, which is the shape of control that cannot fail.
    """
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (isinstance(tgt, ast.Name)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, int)
                    and not isinstance(node.value.value, bool)):
                out[tgt.id] = node.value.value
    return out


def game_dispatch_if(tree):
    """The `if kind == "game":` node that OWNS the game dispatch chain, or None.

    There are three `kind == "game"` tests in `authsrv.py` and only one of them
    is the dispatch chain -- the other two are the connection-setup bursts. This
    picks the one whose BODY reaches `note_unhandled`, i.e. the one carrying
    D9(a)'s own catch-all, which is the same fact section 4 asserts from the
    other side.

    It returns None rather than guessing when the count is not exactly one. That
    matters more than it looks: every check built on this harvest is of the form
    "the arm set contains X" or "the arm set is a subset of Y", and a harvester
    that silently returned nothing would make the second kind pass vacuously.
    A refactor that moves the chain must redden here, loudly, not soften the
    checks underneath it.
    """
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "kind"
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Eq)
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == "game"):
            continue
        for stmt in node.body:
            for call in ast.walk(stmt):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == "note_unhandled"):
                    found.append(node)
                    break
            else:
                continue
            break
    return found[0] if len(found) == 1 else None


def dispatch_arms(tree):
    """{"GAME_CMSG": {opcode: const_name}, "AUTH_CMSG": {...}} read off the chains.

    Both forms are read, and reading only the first is a real defect rather than
    a hypothetical: `elif opcode == X` AND `elif opcode in (X, Y)`. Two of the
    game arms are tuples -- (0x0026, 0x0033) and (0x0046, 0x0027) -- so an
    `==`-only harvester would report ATTACK, INTERACT_PLAYER, USE_SKILL and
    ATTACK_SKILL as unhandled and send somebody hunting four arms that are
    already there. Section 9 reproduces that harvester inline and requires the
    two to disagree.

    The channel split is positional and is the chain's own shape: the game arms
    are inside the `kind == "game"` body, the auth arms are the elif chain
    hanging off its `orelse`. Names are filtered by prefix on top of that, so a
    constant from the wrong catalog appearing on the wrong side reads as absent
    rather than as an arm -- and the two catalogs collide numerically, which is
    the mistake `note_unhandled`'s own docstring is about.
    """
    consts = int_constants(tree)
    node = game_dispatch_if(tree)
    if node is None:
        return None

    def harvest(stmts, prefix):
        out = {}
        for stmt in stmts:
            for sub in ast.walk(stmt):
                if not isinstance(sub, ast.If):
                    continue
                for name in ast.walk(sub.test):
                    if (isinstance(name, ast.Name)
                            and name.id.startswith(prefix)
                            and name.id in consts):
                        out.setdefault(consts[name.id], name.id)
        return out

    return {"GAME_CMSG": harvest(node.body, "GAME_CMSG_"),
            "AUTH_CMSG": harvest(node.orelse, "AUTH_CMSG_")}


def _state_writing_helpers(tree):
    """Module-level functions that take `state` and assign into it.

    An arm may DELEGATE its whole body to one -- `_handle_interact` exists
    because the harness's `interact:` verb drives the same consequence without a
    click, and the two callers must not be two implementations. Following one
    level of delegation keeps this check honest about that while leaving its
    teeth in: `elif opcode == X: pass` still stores nothing, and so does a call
    to a helper that stores nothing.

    ONE LEVEL ONLY, deliberately. Chasing arbitrary depth would eventually
    credit an arm for a store several hops away that no longer has anything to
    do with the message, which is the same over-crediting the `orelse` rule
    above refuses.
    """
    out = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(a.arg == "state" for a in node.args.args):
            continue
        if any(_writes_state(s) for s in node.body):
            out.add(node.name)
    return out


def _calls_state_writer(stmt, helpers):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id in helpers for n in ast.walk(stmt))


def _writes_state(stmt):
    """Does `stmt` assign into `state[...]` anywhere inside it?"""
    for node in ast.walk(stmt):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        for tgt in targets:
            if (isinstance(tgt, ast.Subscript)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "state"):
                return True
    return False


def state_writing_arms(tree):
    """{opcode} for game arms whose OWN body assigns into `state[...]`.

    Section 5 already learned this lesson one level up: `else: pass` satisfies
    "the chain has an else" while restoring exactly the silence D9(a) is about.
    An `elif opcode == X: pass` is the same trick one level down -- it satisfies
    "0x00C1 has an arm" and drops the message just as completely, and the whole
    claim of FIX 6b is that these three opcodes now STORE what arrives. So the
    arm's existence and the arm doing something are asked separately.

    An arm's body is its own `body`, never its `orelse` -- the orelse IS the next
    arm, and folding them together would credit every arm with the work of the
    one after it.
    """
    consts = int_constants(tree)
    helpers = _state_writing_helpers(tree)
    node = game_dispatch_if(tree)
    if node is None:
        return set()
    out = set()
    for stmt in node.body:
        for sub in ast.walk(stmt):
            if not isinstance(sub, ast.If):
                continue
            ops = {consts[n.id] for n in ast.walk(sub.test)
                   if isinstance(n, ast.Name)
                   and n.id.startswith("GAME_CMSG_") and n.id in consts}
            if ops and any(_writes_state(s) or _calls_state_writer(s, helpers)
                           for s in sub.body):
                out |= ops
    return out


def eq_only_arms(tree):
    """`dispatch_arms`' GAME half as it would be with only `opcode == X` read.

    Section 9's control, and it is reproduced here rather than described so the
    comparison is between two live answers instead of between an answer and a
    number somebody wrote down. Same shape as `test_codescan.py` section 8.
    """
    consts = int_constants(tree)
    node = game_dispatch_if(tree)
    if node is None:
        return {}
    out = {}
    for stmt in node.body:
        for sub in ast.walk(stmt):
            if not (isinstance(sub, ast.If)
                    and isinstance(sub.test, ast.Compare)
                    and isinstance(sub.test.left, ast.Name)
                    and sub.test.left.id == "opcode"
                    and isinstance(sub.test.ops[0], ast.Eq)
                    and isinstance(sub.test.comparators[0], ast.Name)):
                continue
            nm = sub.test.comparators[0].id
            if nm in consts:
                out.setdefault(consts[nm], nm)
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

    LEDGER.ok(called_in_finally(tree, "report_unhandled"),
              "and the tally is reported from a `finally`, so a reset still "
              "prints it",
              "MEASURED 2026-08-11: with the call sitting after the read loop "
              "inside the `try`, a 45 s loopback run recorded 7 unhandled "
              "events and wrote ZERO summaries -- the loop always exits by "
              "ConnectionResetError because the harness kills the client. The "
              "tally was right and unreachable, which is D9(a) one file over")

    # ---- 5. the structural checks must be able to go RED ---------------------
    sab0 = ast.parse("def f():\n"
                     "    try:\n"
                     "        report_unhandled(s, c, r)\n"
                     "    except OSError:\n"
                     "        pass\n"
                     "    finally:\n"
                     "        rec.close()\n")
    LEDGER.ok(not called_in_finally(sab0, "report_unhandled"),
              "CONTROL: a call in the TRY body is not counted as reachable",
              "this is exactly the arrangement that shipped and never ran")
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

    # ---- 6. the arms added 2026-08-13, asked of the syntax tree ---------------
    arms = dispatch_arms(tree)
    LEDGER.ok(arms is not None,
              "the game dispatch chain is locatable at all",
              "three `kind == \"game\"` tests exist and exactly one carries "
              "note_unhandled in its body; if that is no longer true every "
              "check below this line would be measuring an empty set, so the "
              "harvester refuses rather than returning one")
    game = (arms or {}).get("GAME_CMSG", {})
    auth = (arms or {}).get("AUTH_CMSG", {})
    LEDGER.ok(len(game) >= 16 and len(auth) >= 12,
              "and it harvests both chains, and the harvest has not SHRUNK",
              f"{len(game)} game arms (16 on 2026-08-13), {len(auth)} auth arms "
              f"(12). Same idiom as test_rotate.py's MIN_SAMPLES: the counts can "
              f"only go up, so a smaller number means either the harvester "
              f"collapsed -- which is what makes every subset check below "
              f"vacuous -- or an arm was deleted, and both of those are things "
              f"somebody should have to argue for rather than absorb. Raise the "
              f"numbers when you add an arm; do not lower them")

    for op, why in ((0x0039, "INTERACT -- 3.2% of ArenaNet's own live c2s and "
                             "dropped entirely until 2026-08-13"),
                    (0x0092, "MISSION_MASK_REPORT -- 803 loopback arrivals of a "
                             "112-byte bitmask, all discarded"),
                    (0x00C1, "TARGET_SELECT -- 363 arrivals, fully named in "
                             "overrides.json, all discarded"),
                    (0x0040, "ROTATE_PLAYER -- 108 arrivals, fully named, all "
                             "discarded")):
        LEDGER.ok(op in game,
                  f"GAME_CMSG 0x{op:04x} has a dispatch arm",
                  f"{why}. Arms found: "
                  f"{', '.join(f'0x{o:04x}' for o in sorted(game))}")

    stores = state_writing_arms(tree)
    LEDGER.ok({0x0039, 0x0092, 0x00C1, 0x0040} <= stores,
              "and each of the four arms actually STORES what arrived",
              f"state-writing arms: "
              f"{', '.join(f'0x{o:04x}' for o in sorted(stores))}. `elif opcode "
              f"== X: pass` satisfies the four checks above and drops the "
              f"message exactly as completely -- the same trick section 5's "
              f"sabotage 4 catches one level up, where `else: pass` satisfies "
              f"'the chain has an else'. Existence and effect are asked apart")

    LEDGER.ok(0x0033 in game,
              "and 0x0033's arm is STILL THERE, dead as it is",
              "the client has not sent one since 2026-08-06 (0 of 17,770 c2s), "
              "and deleting the arm would delete the record that it used to. We "
              "do not know why it stopped, so the arm and its comment are the "
              "evidence -- this check exists so a tidying pass has to argue with "
              "a test rather than with a blank space")

    # ---- 7. every arm is real, and no NAMED opcode is dropped unlisted --------
    codec = Codec()

    def schema_knows(channel, opcode):
        try:
            codec.fields_for(channel, opcode)
            return True
        except Undecodable:
            return False

    phantom = {ch: sorted(o for o in ops if not schema_knows(ch, o))
               for ch, ops in (("GAME_CMSG", game), ("AUTH_CMSG", auth))}
    LEDGER.ok(not phantom["GAME_CMSG"] and not phantom["AUTH_CMSG"],
              "every opcode with an arm is one the schema can frame",
              f"phantom arms {phantom} -- an arm on an opcode the catalog does "
              f"not contain can never run: decode_stream refuses the message and "
              f"the connection closes on the desync long before dispatch. Dead "
              f"code that reads as coverage is how a feature gets ticked off "
              f"twice and shipped never")

    named = {int(k): m["name"]
             for k, m in codec.channels["GAME_CMSG"]["messages"].items()
             if m.get("name")}

    def unlisted_named(armed):
        """Named GAME_CMSG opcodes with neither an arm nor an allowlist row."""
        return sorted(set(named) - set(armed) - set(DROPPED_ON_PURPOSE))

    unlisted = unlisted_named(game)
    LEDGER.ok(not unlisted,
              "and no opcode overrides.json NAMES is dropped without a reason "
              "on the record",
              "DROPPED AND UNLISTED: "
              + (", ".join(f"0x{o:04x} {named[o]}" for o in unlisted)
                 or f"none -- {len(named)} named, {len(set(named) & set(game))} "
                    f"handled, {len(DROPPED_ON_PURPOSE)} listed on purpose")
              + ". A name in overrides.json costs somebody a binary read or a "
                "narrated live session; four of them (0x0039, 0x0040, 0x0092, "
                "0x00C1) were earned and then dropped on the floor anyway. Add "
                "the arm, or add the row to DROPPED_ON_PURPOSE saying why not")

    stale = sorted(set(DROPPED_ON_PURPOSE) & set(game))
    LEDGER.ok(not stale,
              "and no allowlist row names an opcode that IS handled",
              f"stale rows {[f'0x{o:04x}' for o in stale]} -- a row for a handled "
              f"opcode is inert today and armed tomorrow: remove the arm and the "
              f"row silently re-permits the drop, which is this check's own "
              f"failure mode rather than the server's")

    orphan = sorted(set(DROPPED_ON_PURPOSE) - set(named))
    LEDGER.ok(not orphan,
              "and no allowlist row names an opcode nothing has named",
              f"orphan rows {[f'0x{o:04x}' for o in orphan]} -- the allowlist "
              f"answers 'why is this NAMED opcode dropped'. A row for an unnamed "
              f"one answers a question nobody asked and inflates the list until "
              f"nobody reads it")

    # ---- 8. the dword/float trap, behaviourally ------------------------------
    # The one check here that is not structural, and it is on the thing most
    # likely to be got wrong. These three dwords are real 0x0040 field values off
    # our own wire; they are written as literals so this section needs no vault.
    # test_rotate.py's docstring is the long version: the values are IEEE-754
    # float32 and the MARSHALLING is u32, the client's own send table says so,
    # and reading `values[1]` at face value never errors -- it just answers
    # 2,139,095,040 where the truth is +inf.
    naive = 2139095040                      # 0x7F800000
    LEDGER.ok(authsrv._f32_of(naive) == float("inf"),
              "a dword-typed 0x0040 angle reinterprets to the +inf sentinel",
              f"_f32_of(0x{naive:08X}) = {authsrv._f32_of(naive)}; the naive read "
              f"is {naive}, which is a plausible-looking number and wrong. The "
              f"sentinel means 'turning continuously, sign gives the direction' "
              f"and is loaded from .rdata -- it is not a computed angle")
    LEDGER.ok(authsrv._f32_of(0xFF800000) == float("-inf")
              and authsrv._f32_of(0x3F800000) == 1.0
              and abs(authsrv._f32_of(0x3F6147AE) - 0.88) < 1e-6,
              "and the -inf sentinel, 1.0 and a finite turn amount all read back",
              f"-inf / {authsrv._f32_of(0x3F800000)} / "
              f"{authsrv._f32_of(0x3F6147AE):.6f}. 1.0 is 105 of 108 loopback "
              f"turn amounts; the client refuses to send below 0.1")
    LEDGER.ok(authsrv._f32_of(naive) != naive,
              "CONTROL: the reinterpretation is not the identity",
              "a `_f32_of` that returned its argument would pass every check "
              "above that only asks 'is it finite' -- this is the one that "
              "separates reading the bits from reading the number")

    # ---- 9. controls for section 6-7's machinery -----------------------------
    # 9a: the tuple form. Two real arms are `opcode in (A, B)`, so an ==-only
    # harvester loses four opcodes -- reproduced live rather than asserted from
    # a written-down number.
    eq_only = eq_only_arms(tree)
    missed = sorted(set(game) - set(eq_only))
    LEDGER.ok(0x0026 in missed and 0x0033 in missed and 0x0046 in missed
              and 0x0027 in missed,
              "CONTROL: an `==`-only harvester loses the four tuple-form arms",
              f"{len(eq_only)} arms against {len(game)}; missed "
              f"{[f'0x{o:04x}' for o in missed]}. That version would report "
              f"ATTACK, INTERACT_PLAYER, USE_SKILL and ATTACK_SKILL as dropped "
              f"and send somebody hunting four arms already in the file")

    # 9b: the locator must refuse rather than return an empty harvest.
    sab5 = ast.parse("def f():\n"
                     "    if kind == \"lobby\":\n"
                     "        if opcode == GAME_CMSG_X:\n"
                     "            pass\n"
                     "        else:\n"
                     "            note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    LEDGER.ok(dispatch_arms(sab5) is None,
              "CONTROL: no `kind == \"game\"` chain means None, not {}",
              "an empty dict would make 'every arm is schema-known' and 'no "
              "phantom arms' both pass by having nothing to check, which is the "
              "vacuity toolkit/checks.py exists to refuse")
    sab6 = ast.parse("def f():\n"
                     "    if kind == \"game\":\n"
                     "        pass\n"
                     "def g():\n"
                     "    if kind == \"game\":\n"
                     "        note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n"
                     "def h():\n"
                     "    if kind == \"game\":\n"
                     "        note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    LEDGER.ok(dispatch_arms(sab6) is None,
              "CONTROL: TWO candidate chains is also a refusal",
              "picking the first would silently harvest half the arms and every "
              "subset check below would still pass")

    # 9c: the named-opcode report must actually name a missing arm.
    fixture = ast.parse(
        "GAME_CMSG_KEPT = 0x0092\n"
        "GAME_CMSG_GONE = 0x0039\n"
        "def f():\n"
        "    if kind == \"game\":\n"
        "        if opcode == GAME_CMSG_KEPT:\n"
        "            pass\n"
        "        else:\n"
        "            note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    fixture_game = dispatch_arms(fixture)["GAME_CMSG"]
    LEDGER.ok(0x0092 in fixture_game and 0x0039 not in fixture_game,
              "CONTROL: an arm the chain does not have is not harvested",
              f"fixture arms {[f'0x{o:04x}' for o in sorted(fixture_game)]} -- "
              f"both constants are defined at module level in the fixture and "
              f"only one is dispatched on, so the harvester is reading the CHAIN "
              f"and not the constant block")

    # The report predicate itself, run against the real arm set with 0x0039 taken
    # back out. That is FIX 6a's world, and it must name exactly 0x0039 -- not
    # nothing (the check would be inert) and not nine (the six allowlist rows and
    # the other arms would be doing the work).
    without_39 = {o: n for o, n in game.items() if o != 0x0039}
    LEDGER.ok(unlisted_named(without_39) == [0x0039],
              "CONTROL: remove the 0x0039 arm and the report names 0x0039, alone",
              f"unlisted becomes "
              f"{[f'0x{o:04x}' for o in unlisted_named(without_39)]}. This is the "
              f"check that would have caught FIX 6a on the day INTERACT was "
              f"named, and it is run rather than reasoned about")

    # 9d: an arm that does nothing must not count as one that stores.
    inert = ast.parse(
        "GAME_CMSG_A = 0x0092\n"
        "GAME_CMSG_B = 0x00C1\n"
        "def f():\n"
        "    if kind == \"game\":\n"
        "        if opcode == GAME_CMSG_A:\n"
        "            pass\n"
        "        elif opcode == GAME_CMSG_B:\n"
        "            state['target'] = values[1]\n"
        "        else:\n"
        "            note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    inert_stores = state_writing_arms(inert)
    LEDGER.ok(inert_stores == {0x00C1}
              and 0x0092 in dispatch_arms(inert)["GAME_CMSG"],
              "CONTROL: `elif opcode == X: pass` is an arm that does not store",
              f"stores {[f'0x{o:04x}' for o in sorted(inert_stores)]} while BOTH "
              f"are harvested as arms. The two checks disagree on exactly the "
              f"case that matters, which is what makes the second one worth "
              f"running -- and it also proves an arm is not credited with the "
              f"NEXT arm's body, since 0x0092 sits immediately above a storing "
              f"one")

    # 9e: the phantom-arm check must catch an opcode the schema cannot frame.
    phantom_fixture = ast.parse(
        "GAME_CMSG_NOPE = 0x00FE\n"
        "def f():\n"
        "    if kind == \"game\":\n"
        "        if opcode == GAME_CMSG_NOPE:\n"
        "            pass\n"
        "        else:\n"
        "            note_unhandled(s, c, 'GAME_CMSG', o, n, r)\n")
    pf = dispatch_arms(phantom_fixture)["GAME_CMSG"]
    LEDGER.ok(pf == {0x00FE: "GAME_CMSG_NOPE"}
              and not schema_knows("GAME_CMSG", 0x00FE),
              "CONTROL: an arm on an opcode the schema lacks is detected",
              f"harvested {pf}; the catalog has no GAME_CMSG 0x00FE, so the "
              f"forward check above is refutable rather than true by "
              f"construction")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
