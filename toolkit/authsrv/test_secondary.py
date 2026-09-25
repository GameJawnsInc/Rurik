"""The K panel's secondary-profession change -- SECONDARY-B1..B5
(studies/profession/SECONDARY.md, 2026-09-25).

    python toolkit/authsrv/test_secondary.py

WHAT THIS PINS, and what each part rests on:

  * §1 THE LOAD's 0x00B6 (OBSERVED, 95 of 95 live game connections): the
    default mask is retail's PvP form, 0x7FF & ~(1 << primary) -- the two
    literals on tape, 2045 for a Warrior and 1919 for an Assassin -- and
    `load_secondary_offer()` is the three regimes in one expression (the
    default, the --secondary-bits override, the revert's 0). The burst site
    is locked on its SOURCE: the 0x00B6 send is guarded by `if _offer:`,
    sits IMMEDIATELY after the player's 0x00B7 with no other send between
    (retail's adjacency, 95 of 95) and before the 0x00A6, and the 0x00B7
    carries player_secondary(state) through the builder.
  * §2 THE PLAYER'S CHANGE (the n=1 witness, capture 20260824T074002 :61329):
    c2s 0x0041 [player, 4] answers ONE batch in retail's order, 0x00B7 ->
    0x00A6 -> 0x00DB, the pair fields equal to the witness's ([.., 1, 4, ..]),
    the library byte-identical to the load's, no 0x00B6 re-send, the flag 0
    by decision (SECONDARY-F6). The current secondary re-picked is a no-op
    that still answers.
  * §3 REFUSALS send NOTHING and move nothing (RECONSTRUCTION -- retail's
    refusal is unobserved): outside the offered mask, the primary itself, a
    field (0x0199 field 3 = 1, with OUTPOST's override as the control), a
    foreign agent, a kicked hero, id 0 and 11, a malformed payload.
  * §4 A HERO's change: 0x00B7 + 0x00A6 for the hero's agent and NO 0x00DB
    (the hero list re-enumerates on 0x00B7's own event), the client's own
    0x7FF-minus-primary mask (the player's 0x00B6 override does not gate it),
    and the next load's hero block carries the pair.
  * §5 THE OLD SECONDARY'S STATE (RECONSTRUCTION): its ranks are zeroed and
    refunded BEFORE the 0x00B7 through 0x0038 + 0x003B (the mid-session
    shapes, 14 of 14 retail spends), the primary's and the common skills'
    rows untouched, and its skills leave the bar through 0x00D9 after the
    0x00DB; --no-secondary-cleanup keeps both (the arm's own revert).
  * §6 PERSISTENCE through a scratch charstore: the change writes the row,
    a reopened store reads it, a fresh connection's player_secondary and
    attribute state carry it OVER the launch value (the bar's precedent), a
    stored secondary equal to a moved primary is ignored loudly, the revert
    does not read it; the hero's likewise; the store's three refusals; the
    mirrored CHAR_PROFESSIONS; the CLI; and the client's own AUTH 0x0009 blob
    round-trips VERBATIM with its secondary bits intact (verified, not
    assumed).
  * §7 THE MASTER REVERT against literals recorded from the 57e89956 tree
    before any edit (scratch head_literals.py): no 0x00B6 without
    --secondary-bits, 0x00B7 [1, 1, 0, 0] / [200, 7, 0, 0], 0x00A6 [1, 1, 0],
    0x0041 dropped with nothing sent and no state written.
  * §8 SOURCE LOCKS: the arm, main()'s two flags, serverargs' two strings,
    the dropped-list row gone, overrides.json's name, the hero sites.

SABOTAGE HOOK: RURIK_SECONDARY_AUTHSRV=<path> loads THAT copy of authsrv.py
as `authsrv` (siblings still from toolkit/authsrv), so each new guard can be
inverted in a scratch copy and shown to redden -- the study records which
mutation reddens which section.

Drives the real handlers with a fake send and a scratch store, like
test_heroadd.py. Floor from the green run (see the ledger line).
"""
import ast
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import charstore                                             # noqa: E402
import charsummary                                           # noqa: E402
import agents                                                # noqa: E402
import skillunlock                                           # noqa: E402

_ALT = os.environ.get("RURIK_SECONDARY_AUTHSRV")
if _ALT:
    _spec = importlib.util.spec_from_file_location("authsrv", _ALT)
    authsrv = importlib.util.module_from_spec(_spec)
    sys.modules["authsrv"] = authsrv
    _spec.loader.exec_module(authsrv)
    print(f"SABOTAGE HOOK: authsrv loaded from {_ALT}")
else:
    import authsrv                                           # noqa: E402

led = checks.Ledger("secondary profession change (SECONDARY-B1..B5)", floor=108)   # 2026-09-25, from the green run (108 checks)

SRC_PATH = authsrv.__file__
ARGS_PATH = os.path.join(HERE, "serverargs.py")
CHANGE = authsrv.GAME_CMSG_SET_SECONDARY_PROFESSION
PROFS, BITS, SETPROF = 0x00B7, 0x00B6, 0x00A6
LIBRARY, POINTS_AVAIL, ATTR_ONE, BAR_ONE = 0x00DB, 0x0038, 0x003B, 0x00D9
UUID = "33333333333333333333333333333333"
assert CHANGE == 0x0041
assert authsrv.GAME_SMSG_AGENT_PROFESSIONS == PROFS
assert authsrv.GAME_SMSG_AGENT_PROFESSION_BITS == BITS
assert authsrv.GAME_SMSG_AGENT_SET_PROFESSION == SETPROF
assert authsrv.GAME_SMSG_UPDATE_UNLOCKED_SKILLS == LIBRARY
assert authsrv.GAME_SMSG_ATTRIBUTE_POINTS_AVAILABLE == POINTS_AVAIL
assert authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTE == ATTR_ONE
assert authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL == BAR_ONE

# The 57e89956 literals, recorded by scratch head_literals.py BEFORE any edit
# of this arc (commit 57e89956, the tree the branch was cut from).
HEAD = {"player_0x00B7": [1, 1, 0, 0], "hero_0x00B7_prof7_agent200": [200, 7, 0, 0],
        "player_0x00A6": [1, 1, 0], "SECONDARY_BITS": 0,
        "unhandled_count_after_one_0x0041": 1}
# The retail witness (OBSERVED, capture 20260824T074002 :61329, map 248).
WITNESS_REQ = [568, 4]
WITNESS_0x00B7, WITNESS_0x00A6 = [568, 1, 4, 1], [568, 1, 4]


class FakeRec:
    def __init__(self):
        self.events = []

    def event(self, kind, **kw):
        self.events.append((kind, kw))


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals) if isinstance(vals, (list, tuple)) else vals))
    return sent, send


def ops(sent):
    return [op for op, _v in sent]


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


def town_state(**extra):
    st = {"agents": {}, "char_uuid": UUID, "map_id": 148}
    st.update(extra)
    return st


def change(state, agent, prof, rec=None):
    sent, send = fake_send_factory()
    rec = rec or FakeRec()
    _r, out = quiet(authsrv.handle_secondary_change, [CHANGE, agent, prof],
                    send, state, 0, rec)
    return sent, rec, out


def library_words(store=None):
    return skillunlock.resolve_library(store, UUID, authsrv.UNLOCKED,
                                       authsrv.UNLOCK_LABEL)[2]


_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "SECONDARY_BITS",
           "SECONDARY_CHANGE_ENABLED", "SECONDARY_CLEANUP_ENABLED", "HERO_IDS",
           "HERO_AGENT_ID", "HERO_ROWS", "HERO_KICK_ENABLED", "EXPLORABLE",
           "OUTPOST", "HERO_BODY", "HERO_ATTRIBUTES", "HERO_SKILLS")}
_saved_bar = list(authsrv.SKILLBAR)
_saved_store_dir = charstore.store_dir
base = tempfile.mkdtemp(prefix="secondary-test-")
try:
    authsrv.PERSIST = False
    authsrv.SPAWN_PROFESSION, authsrv.SPAWN_SECONDARY = 1, 0
    authsrv.SECONDARY_BITS = 0
    authsrv.SECONDARY_CHANGE_ENABLED = True
    authsrv.SECONDARY_CLEANUP_ENABLED = True
    authsrv.HERO_IDS, authsrv.HERO_AGENT_ID = [6], 200
    authsrv.HERO_ROWS = {6: {"hero": 6, "body": "koss", "profession": 3,
                             "skills": [105, 1, 2]}}
    authsrv.HERO_KICK_ENABLED = True
    authsrv.HERO_BODY = False
    authsrv.HERO_ATTRIBUTES = {}
    authsrv.EXPLORABLE, authsrv.OUTPOST = False, False
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])

    # -- §1 the load's 0x00B6 ---------------------------------------------------
    led.ok(authsrv.secondary_offer_mask(1) == 2045,
           "a Warrior's default mask is 2045 = 0x7FD (OBSERVED, 46 of 46 loads "
           "of the PvP Warrior)", f"{authsrv.secondary_offer_mask(1):#06x}")
    led.ok(authsrv.secondary_offer_mask(7) == 1919,
           "an Assassin's is 1919 = 0x77F (OBSERVED, 4 of 4)",
           f"{authsrv.secondary_offer_mask(7):#06x}")
    m = authsrv.secondary_offer_mask(1)
    led.ok((m & 1) == 1 and not (m >> 1) & 1
           and all((m >> p) & 1 for p in range(2, 11)) and not m >> 11,
           "bit 0 kept, the primary's bit clear, ids 2..10 set, nothing past 10",
           f"{m:#06x} -- the builder loops `cmp edi, 0xb` and never adds id 0 "
           f"from the mask, so bit 0 is harmless fidelity")
    led.ok(authsrv.secondary_offer_mask(12) == 0x7FF,
           "a custom primary past 10 has no bit to clear: 0x7FF",
           f"{authsrv.secondary_offer_mask(12):#06x}")
    led.ok(authsrv.load_secondary_offer() == 2045,
           "load_secondary_offer(): the default regime is the primary's mask",
           f"{authsrv.load_secondary_offer():#06x} with SPAWN_PROFESSION 1")
    authsrv.SPAWN_PROFESSION = 7
    led.ok(authsrv.load_secondary_offer() == 1919,
           "...and follows the launch primary (7 -> 1919)",
           f"{authsrv.load_secondary_offer():#06x}")
    authsrv.SPAWN_PROFESSION = 1
    authsrv.SECONDARY_BITS = 0x44
    led.ok(authsrv.load_secondary_offer() == 0x44,
           "--secondary-bits OVERRIDES the default (0x44 -> 0x44)",
           f"{authsrv.load_secondary_offer():#06x}")
    authsrv.SECONDARY_CHANGE_ENABLED = False
    led.ok(authsrv.load_secondary_offer() == 0x44,
           "...and still sends under --no-secondary-change (the pre-arc flag "
           "keeps working)", f"{authsrv.load_secondary_offer():#06x}")
    authsrv.SECONDARY_BITS = 0
    led.ok(authsrv.load_secondary_offer() == 0,
           "the revert without the override is 0: NOT sent (57e89956's bytes)",
           f"{authsrv.load_secondary_offer()}")
    authsrv.SECONDARY_CHANGE_ENABLED = True

    # The burst site, on its SOURCE: the sends of _handle_request_players in
    # file order, so adjacency can be asked rather than inferred.
    SRC = open(SRC_PATH, encoding="utf-8").read()
    TREE = ast.parse(SRC)

    def func_node(name):
        for node in TREE.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    players = func_node("_handle_request_players")
    psrc = ast.get_source_segment(SRC, players) if players else ""
    led.ok(bool(psrc), "the load burst is _handle_request_players (read for its sends)")
    sends = [(n.lineno, n.args[0].id) for n in ast.walk(players)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "send" and n.args and isinstance(n.args[0], ast.Name)]
    sends.sort()
    names = [nm for _l, nm in sends]
    i_b7 = names.index("GAME_SMSG_AGENT_PROFESSIONS") if "GAME_SMSG_AGENT_PROFESSIONS" in names else None
    i_b6 = names.index("GAME_SMSG_AGENT_PROFESSION_BITS") if "GAME_SMSG_AGENT_PROFESSION_BITS" in names else None
    i_a6 = names.index("GAME_SMSG_AGENT_SET_PROFESSION") if "GAME_SMSG_AGENT_SET_PROFESSION" in names else None
    led.ok(i_b7 is not None and i_b6 is not None and i_b6 == i_b7 + 1,
           "the load's 0x00B6 send is the NEXT send after the player's 0x00B7 "
           "(retail: adjacent on 95 of 95; the record 0x00B6 writes into is "
           "created by 0x00B7)",
           f"sends around it: {names[max(0, (i_b7 or 0) - 1):(i_b7 or 0) + 3]}")
    led.ok(i_a6 is not None and i_b6 is not None and i_b6 < i_a6,
           "...and before the player's 0x00A6 (it sat after it under "
           "--secondary-bits until 2026-09-25)",
           f"0x00B6 at index {i_b6}, 0x00A6 at {i_a6}")
    b6_call = [n for n in ast.walk(players)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "send" and n.args and isinstance(n.args[0], ast.Name)
               and n.args[0].id == "GAME_SMSG_AGENT_PROFESSION_BITS"]
    guard_ok = False
    for node in ast.walk(players):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) \
                and node.test.id == "_offer":
            if any(c is b6_call[0] for c in ast.walk(node)) if b6_call else False:
                guard_ok = True
    led.ok(guard_ok and "_offer = load_secondary_offer()" in psrc,
           "the 0x00B6 send is guarded by `if _offer:` with `_offer = "
           "load_secondary_offer()` -- one expression for the three regimes",
           "a second copy of the regime logic at the site is where the handler "
           "and the burst would drift apart")
    led.ok("_psec = player_secondary(state)" in psrc
           and "spawn_profession_values(secondary=_psec)" in psrc,
           "the player's 0x00B7 carries player_secondary(state) through the "
           "builder (the stored change over the launch value)")
    led.ok(len(b6_call) == 1 and all(
        isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute)
        and inner.func.attr == "agent_set_secondary_bits"
        for inner in [b6_call[0].args[1]]),
           "and the mask goes through agents.agent_set_secondary_bits (the u32 "
           "bound)")

    # -- §2 the player's change: the witness's shape ---------------------------
    st = town_state()
    led.ok(not authsrv.instance_is_explorable(st),
           "map 148 is a town for instance_is_explorable (the 0x0199 field 3 "
           "expression)")
    led.ok(authsrv.player_secondary(st) == 0
           and authsrv.attribute_state(st).secondary == 0,
           "a fresh connection starts at the launch value (0) in both the "
           "session and the attribute state")
    sent, rec, out = change(st, 1, 4)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY],
           "c2s 0x0041 [player, 4] answers EXACTLY 0x00B7 -> 0x00A6 -> 0x00DB, "
           "retail's order (the witness's one segment), and no 0x00B6 re-send",
           f"got {[hex(o) for o in ops(sent)]}")
    b7 = dict(sent).get(PROFS)
    led.ok(b7 == [1, 1, 4, 0],
           "0x00B7 is [player, primary 1, NEW secondary 4, 0]",
           f"got {b7}")
    led.ok(b7 is not None and b7[1:3] == WITNESS_0x00B7[1:3]
           and dict(sent).get(SETPROF)[1:] == WITNESS_0x00A6[1:],
           "the pair fields equal the witness's (1, 4) on both messages "
           "(0x00B7 [568, 1, 4, 1] / 0x00A6 [568, 1, 4]; agent ids differ by "
           "server)", f"ours {b7} / {dict(sent).get(SETPROF)}")
    led.ok(b7 is not None and b7[3] == 0 and WITNESS_0x00B7[3] == 1,
           "the 0x00B7 flag is 0 BY DECISION where the witness had 1 -- "
           "SECONDARY-F6: its sole reader selects a chapter mask this server's "
           "account data has not been shown to fill",
           f"ours {b7[3] if b7 else None}, witness {WITNESS_0x00B7[3]}")
    led.ok(dict(sent).get(SETPROF) == [1, 1, 4],
           "0x00A6 is [player, 1, 4]", f"got {dict(sent).get(SETPROF)}")
    led.ok(dict(sent).get(LIBRARY) == [library_words()],
           "0x00DB is the CHARACTER library exactly as the load resolves it "
           "(retail's re-send was byte-identical to the load's)",
           f"{len(dict(sent).get(LIBRARY, [[]])[0])} words")
    led.ok(st["player_secondary"] == 4 and authsrv.player_secondary(st) == 4
           and authsrv.attribute_state(st).secondary == 4,
           "the session now holds 4 -- player_secondary and the live attribute "
           "state agree")
    led.ok(authsrv.spawn_profession_values(secondary=authsrv.player_secondary(st))
           == [1, 1, 4, 0],
           "...so the next 0x00B7 built from it carries the new pair")
    led.ok(rec.events and rec.events[-1][0] == "secondary_change"
           and rec.events[-1][1].get("refused") is None
           and rec.events[-1][1].get("old") == 0 and rec.events[-1][1].get("new") == 4,
           "the capture records the change (old 0, new 4, not refused)",
           f"{rec.events[-1] if rec.events else None}")
    # the no-op
    sent, rec, out = change(st, 1, 4)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY] and "no-op" in out,
           "the CURRENT secondary re-picked is a no-op that still answers the "
           "batch (the client's record update is idempotent)",
           f"got {[hex(o) for o in ops(sent)]}")
    led.ok(st["player_secondary"] == 4, "...and moves nothing")
    # a second real change, from 4 to 6, no ranks and no bar skill of 4 yet
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([1, 2, 0, 0, 0, 0, 0, 0])
    sent, rec, out = change(st, 1, 6)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY] and dict(sent)[PROFS] == [1, 1, 6, 0],
           "a change with NOTHING of the old secondary on the bar or in the "
           "ranks is the bare batch again (the witness's exact case)",
           f"got {[hex(o) for o in ops(sent)]}")

    # -- §3 refusals -------------------------------------------------------------
    def refused(state, agent, prof, why_has):
        before = (authsrv.player_secondary(state),
                  dict(state.get("hero_secondary") or {}))
        sent, rec, out = change(state, agent, prof)
        ev = rec.events[-1][1] if rec.events else {}
        after = (authsrv.player_secondary(state),
                 dict(state.get("hero_secondary") or {}))
        return (sent == [] and "REFUSED" in out and why_has in out
                and ev.get("refused") is not None and after == before), out

    st = town_state()
    authsrv.SECONDARY_BITS = 0x44                      # offers 2 and 6 only
    ok, out = refused(st, 1, 4, "outside the mask")
    led.ok(ok, "OUTSIDE THE OFFERED MASK (--secondary-bits 0x44, asking 4): "
               "refused, nothing sent, nothing moved", out.strip()[-160:])
    sent, _r, _o = change(st, 1, 6)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY] and st["player_secondary"] == 6,
           "CONTROL: 6 is inside 0x44 and is accepted")
    authsrv.SECONDARY_BITS = 0
    st = town_state()
    ok, out = refused(st, 1, 1, "IS the player's primary")
    led.ok(ok, "THE PRIMARY ITSELF (1 on a Warrior): refused (GmDeckBuilder:2321)",
           out.strip()[-160:])
    authsrv.EXPLORABLE = True
    st = town_state()
    led.ok(authsrv.instance_is_explorable(st), "--explorable makes the instance a field")
    ok, out = refused(st, 1, 4, "explorable")
    led.ok(ok, "A FIELD (0x0199 field 3 = 1): refused -- the client's own "
               "drop-down is disabled there", out.strip()[-160:])
    authsrv.OUTPOST = True
    led.ok(not authsrv.instance_is_explorable(st),
           "CONTROL: OUTPOST overrides --explorable, as at the 0x0199 send site")
    sent, _r, _o = change(st, 1, 4)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY], "...and the change is accepted there")
    authsrv.EXPLORABLE, authsrv.OUTPOST = False, False
    st = town_state(map_id=146)
    led.ok(authsrv.instance_is_explorable(st),
           "map 146 (a Pre-Searing explorable in MAP_STATIC_CONFIG) is a field")
    ok, out = refused(st, 1, 4, "explorable")
    led.ok(ok, "...and refuses by the map row alone", out.strip()[-120:])
    st = town_state()
    ok, out = refused(st, 77, 4, "neither this connection's player")
    led.ok(ok, "A FOREIGN AGENT (77): refused", out.strip()[-160:])
    st = town_state(kicked_heroes={6})
    ok, out = refused(st, 200, 4, "neither this connection's player")
    led.ok(ok, "A KICKED HERO's agent (200, hero 6 kicked): refused -- no panel "
               "opens on a hero out of the party", out.strip()[-160:])
    st = town_state()
    sent, _r, _o = change(st, 1, 4)
    led.ok(st["player_secondary"] == 4, "(a W/N to ask 'None' of)")
    ok, out = refused(st, 1, 0, "outside 1..10")
    led.ok(ok, "ID 0 when the current secondary is 4: refused (only the CURRENT "
               "secondary may be re-picked, and 'None' is offered only when it "
               "is the current one)", out.strip()[-120:])
    ok, out = refused(st, 1, 11, "outside 1..10")
    led.ok(ok, "ID 11 (past CHAR_PROFESSIONS - 1): refused", out.strip()[-120:])
    st = town_state()
    sent, send = fake_send_factory()
    rec = FakeRec()
    _r, out = quiet(authsrv.handle_secondary_change, [CHANGE, 1], send, st, 0, rec)
    led.ok(sent == [] and "malformed" in out
           and rec.events and rec.events[-1][1].get("refused") == "malformed"
           and "player_secondary" not in st,
           "A MALFORMED PAYLOAD ([agent] alone): refused, nothing sent, no "
           "state written", out.strip()[-120:])
    st = town_state()
    sent, _r, _o = change(st, 1, 4)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY],
           "CONTROL: the same request, well-formed and in a town, is accepted")

    # -- §4 a hero's change ----------------------------------------------------
    st = town_state()
    led.ok(authsrv.hero_profession(6) == 3 and authsrv.hero_secondary(st, 6) == 0,
           "the rig's hero 6 is a Monk (row profession 3) with no secondary")
    sent, rec, out = change(st, 200, 5)
    led.ok(ops(sent) == [PROFS, SETPROF],
           "a HERO's 0x0041 [200, 5] answers 0x00B7 -> 0x00A6 for the hero's "
           "agent and NO 0x00DB (its list re-enumerates on 0x00B7's own event "
           "0x1000004E from heroData + the account set)",
           f"got {[hex(o) for o in ops(sent)]}")
    led.ok(dict(sent).get(PROFS) == [200, 3, 5, 0] and dict(sent).get(SETPROF) == [200, 3, 5],
           "0x00B7 [200, 3, 5, 0] and 0x00A6 [200, 3, 5]",
           f"{dict(sent).get(PROFS)} / {dict(sent).get(SETPROF)}")
    led.ok(st["hero_secondary"][6] == 5 and authsrv.hero_secondary(st, 6) == 5
           and authsrv.hero_attribute_state(st, 6).secondary == 5,
           "the session holds the hero's 5 in hero_secondary and its attribute state")
    block = authsrv.hero_character_block(st, 200, 6)
    bops = {op: vals for op, vals, _l in block}
    led.ok(bops.get(PROFS) == [200, 3, 5, 0] and bops.get(SETPROF) == [200, 3, 5],
           "...and the hero's character block (the next load's own) carries the pair",
           f"{bops.get(PROFS)} / {bops.get(SETPROF)}")
    ok, out = refused(st, 200, 3, "IS the hero 6's primary")
    led.ok(ok, "the hero's own primary (3): refused", out.strip()[-120:])
    authsrv.SECONDARY_BITS = 0x44
    sent, _r, _o = change(st, 200, 10)
    led.ok(ops(sent) == [PROFS, SETPROF] and st["hero_secondary"][6] == 10,
           "the player's --secondary-bits (0x44) does NOT gate a hero: 10 is "
           "accepted (the client offers a hero 0x7FF minus its primary on its "
           "own, 0x005023DE)")
    authsrv.SECONDARY_BITS = 0
    ok, out = refused(st, 200, 11, "outside 1..10")
    led.ok(ok, "a hero's 11: refused", out.strip()[-100:])

    # -- §5 the old secondary's state -----------------------------------------
    authsrv.SPAWN_SECONDARY = 4                        # a W/N by launch
    st = town_state()
    ast_ = authsrv.attribute_state(st)
    led.ok(ast_.secondary == 4, "a W/N by --spawn-secondary: the attribute state says 4")
    ast_.points_total = 200
    ast_.ranks.clear()
    ast_.ranks.update({5: 3, 18: 2})                   # Necro attr 5 at 3, Warrior attr 18 at 2
    spent_before, avail_before = ast_.spent, ast_.available
    led.ok(int(agents.WORLD.rows("attribute")["5"]["profession"]) == 4
           and int(agents.WORLD.rows("attribute")["18"]["profession"]) == 1
           and authsrv.skill_profession(105) == 4 and authsrv.skill_profession(1) == 1
           and authsrv.skill_profession(2) == 0,
           "the fixture's professions are the content rows' (attr 5 -> 4, attr 18 "
           "-> 1; skill 105 -> 4, skill 1 -> 1, skill 2 -> common)")
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])
    sent, rec, out = change(st, 1, 2)                  # N -> Mo
    got = ops(sent)
    led.ok(got == [POINTS_AVAIL, ATTR_ONE, PROFS, SETPROF, LIBRARY, BAR_ONE],
           "with a rank in the old secondary and its skill on the bar: 0x0038 -> "
           "0x003B BEFORE the 0x00B7 (so the client's rebuild sees zeros), the "
           "batch, then 0x00D9 after the 0x00DB",
           f"got {[hex(o) for o in got]}")
    refund = ast_.rules.spent_on(3)
    led.ok(dict(sent).get(POINTS_AVAIL) == [1, avail_before + refund] and refund == 6,
           "0x0038 refunds exactly the rank's cumulative price (rank 3 = 1+2+3 = 6 "
           "on the client's own cost table)",
           f"got {dict(sent).get(POINTS_AVAIL)}, before {avail_before}, refund {refund}")
    led.ok(dict(sent).get(ATTR_ONE) == [1, 5, 0, 0],
           "0x003B [player, attr 5, base 0, effective 0] zeroes the Necromancer "
           "rank", f"got {dict(sent).get(ATTR_ONE)}")
    led.ok(5 not in ast_.ranks and ast_.ranks.get(18) == 2 and ast_.secondary == 2
           and ast_.available == avail_before + refund,
           "the live state: attr 5 gone, the Warrior's 18 untouched, secondary "
           "now 2, the points back in the pool")
    led.ok(dict(sent).get(BAR_ONE) == [1, 0, 0, 0],
           "0x00D9 [player, slot 0, 0, 0] empties the slot that held 105 (a "
           "Necromancer skill)", f"got {dict(sent).get(BAR_ONE)}")
    led.ok(list(authsrv.SKILLBAR) == [0, 1, 2, 0, 0, 0, 0, 0],
           "the bar keeps the primary's skill 1 and the common skill 2",
           f"{list(authsrv.SKILLBAR)}")
    led.ok(rec.events[-1][1].get("zeroed") == [5] and rec.events[-1][1].get("refunded") == 6
           and rec.events[-1][1].get("stripped") == [[0, 105]],
           "the capture names what was zeroed, refunded and stripped",
           f"{rec.events[-1][1]}")
    # the arm's own revert
    authsrv.SECONDARY_CLEANUP_ENABLED = False
    st = town_state()
    ast_ = authsrv.attribute_state(st)
    ast_.points_total = 200
    ast_.ranks.clear()
    ast_.ranks.update({5: 3, 18: 2})
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])
    sent, rec, out = change(st, 1, 2)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY] and ast_.ranks.get(5) == 3
           and list(authsrv.SKILLBAR)[0] == 105,
           "--no-secondary-cleanup: the bare batch, the rank and the bar skill "
           "kept (the RECONSTRUCTION's own revert)",
           f"got {[hex(o) for o in ops(sent)]}")
    authsrv.SECONDARY_CLEANUP_ENABLED = True
    # a hero with a rank and a bar skill in its old secondary
    st = town_state(hero_secondary={6: 4})
    hst = authsrv.hero_attribute_state(st, 6)
    led.ok(hst.secondary == 4 and hst.primary == 3,
           "hero 6 as a Mo/N (session secondary 4)")
    hst.points_total = 30
    hst.ranks.clear()
    hst.ranks.update({5: 2})
    h_avail = hst.available
    sent, rec, out = change(st, 200, 1)
    got = ops(sent)
    led.ok(got == [POINTS_AVAIL, ATTR_ONE, PROFS, SETPROF, BAR_ONE],
           "the hero's cleanup: 0x0038 -> 0x003B, 0x00B7 -> 0x00A6 (no 0x00DB), "
           "then 0x00D9 -- all to the hero's agent",
           f"got {[hex(o) for o in got]}")
    led.ok(dict(sent).get(POINTS_AVAIL) == [200, h_avail + hst.rules.spent_on(2)]
           and dict(sent).get(ATTR_ONE) == [200, 5, 0, 0]
           and dict(sent).get(BAR_ONE) == [200, 0, 0, 0],
           "0x0038 [200, +3], 0x003B [200, 5, 0, 0], 0x00D9 [200, 0, 0, 0]",
           f"{dict(sent).get(POINTS_AVAIL)} / {dict(sent).get(ATTR_ONE)} / {dict(sent).get(BAR_ONE)}")
    led.ok(st["hero_bars"][6] == [0, 1, 2, 0, 0, 0, 0, 0]
           and authsrv.hero_panel_bar_ids(st, 6) == [0, 1, 2, 0, 0, 0, 0, 0],
           "the session's hero bar (what the panel and the body read) has slot 0 "
           "emptied", f"{st['hero_bars'].get(6)}")
    led.ok(5 not in hst.ranks and hst.secondary == 1,
           "the hero's attribute state: attr 5 gone, secondary 1")
    authsrv.SPAWN_SECONDARY = 0

    # -- §6 persistence ----------------------------------------------------------
    authsrv.PERSIST = True
    store = charstore.Store.open("secondary@rurik.invalid", base=base)
    store.ensure_character(UUID, "Sec Tester")
    store.save()
    led.ok(store.character_secondary(UUID) is None and store.hero_secondary(UUID, 6) is None,
           "a fresh row stores NO secondary (absent = never changed)")
    st = town_state(charstore_game=store)
    led.ok(authsrv.player_secondary(st) == 0,
           "player_secondary on an absent field is the launch value (0)")
    sent, rec, out = change(st, 1, 4)
    led.ok(store.character_secondary(UUID) == 4 and "persisted" in out
           and rec.events[-1][1].get("persisted") is True,
           "the change writes the character's `secondary` = 4 and says so",
           out.strip()[-140:])
    reopened = charstore.Store.open("secondary@rurik.invalid", base=base)
    led.ok(reopened.character_secondary(UUID) == 4,
           "a reopened store reads 4 back (the file, not the object)")
    fresh = town_state(charstore_game=reopened)
    led.ok(authsrv.player_secondary(fresh) == 4 and authsrv.SPAWN_SECONDARY == 0,
           "a FRESH connection's player_secondary is the STORED 4 over the launch "
           "0 -- the bar's and the ranks' precedent: the launch value seeds, the "
           "store wins")
    led.ok(authsrv.spawn_profession_values(secondary=authsrv.player_secondary(fresh))
           == [1, 1, 4, 0]
           and authsrv.attribute_state(fresh).secondary == 4,
           "...so the next load's 0x00B7 is [1, 1, 4, 0] and its attribute state "
           "spends on Necromancer lines")
    authsrv.SPAWN_PROFESSION = 4                       # the launch primary moved under the store
    fresh2 = town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))
    val, out = quiet(authsrv.player_secondary, fresh2)
    led.ok(val == 0 and "ignored" in out and "2321" in out,
           "a stored secondary EQUAL to a moved launch primary (4/4) is ignored "
           "LOUDLY and the launch value answers (GmDeckBuilder:2321)",
           out.strip()[-160:])
    authsrv.SPAWN_PROFESSION = 1
    authsrv.SECONDARY_CHANGE_ENABLED = False
    fresh3 = town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))
    led.ok(authsrv.player_secondary(fresh3) == 0,
           "under --no-secondary-change the store is NOT read: the launch value "
           "(the revert arm, --no-hero-kick's precedent)")
    authsrv.SECONDARY_CHANGE_ENABLED = True
    # a stored secondary with a stored rank in it survives a reload as ranks do
    # (the ranks are the store's own field; this only pins that both persist)
    store2 = charstore.Store.open("secondary@rurik.invalid", base=base)
    st = town_state(charstore_game=store2)
    led.ok(authsrv.player_secondary(st) == 4, "(the stored 4 is this connection's start)")
    ast_ = authsrv.attribute_state(st)
    ast_.points_total = 200
    ast_.ranks.clear()
    ast_.ranks.update({5: 2, 18: 1})
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])
    sent, rec, out = change(st, 1, 6)
    row = charstore.Store.open("secondary@rurik.invalid", base=base).character_by_uuid(UUID)
    led.ok(row.get("secondary") == 6 and row.get("attributes") == [[18, 1]]
           and row.get("skillbar") == [0, 1, 2, 0, 0, 0, 0, 0],
           "a change with a rank and a bar skill in the old secondary persists "
           "all three: secondary 6, the ranks without attr 5, the bar without 105",
           f"row secondary {row.get('secondary')}, attributes {row.get('attributes')}, "
           f"skillbar {row.get('skillbar')}")
    # the hero
    store3 = charstore.Store.open("secondary@rurik.invalid", base=base)
    st = town_state(charstore_game=store3)
    sent, rec, out = change(st, 200, 5)
    led.ok(store3.hero_secondary(UUID, 6) == 5
           and charstore.Store.open("secondary@rurik.invalid", base=base).hero_secondary(UUID, 6) == 5,
           "a hero's change writes heroes[6].secondary = 5 and reopens to it")
    freshh = town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))
    led.ok(authsrv.hero_secondary(freshh, 6) == 5
           and {op: v for op, v, _l in authsrv.hero_character_block(freshh, 200, 6)}[PROFS]
           == [200, 3, 5, 0],
           "a fresh connection's hero block carries [200, 3, 5, 0]")
    # the store's refusals
    def refuses_file(mutate):
        p = charstore.path_for("bad@rurik.invalid", base)
        data = charstore._fresh("bad@rurik.invalid")
        data["characters"][UUID] = {"name": "Bad", "settings_blob": "", "level": 1,
                                    "xp": 0, "skill_points": 0, "attributes": []}
        mutate(data["characters"][UUID])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)
        try:
            charstore.Store.open("bad@rurik.invalid", base=base)
        except ValueError as ex:
            return "secondary" in str(ex)
        return False
    led.ok(refuses_file(lambda r: r.__setitem__("secondary", 11)),
           "the store REFUSES secondary 11 (past the client's bound)")
    led.ok(refuses_file(lambda r: r.__setitem__("secondary", True)),
           "...and a bool")
    led.ok(refuses_file(lambda r: r.setdefault("heroes", {}).__setitem__("6", {"secondary": -1})),
           "...and a hero's -1")
    led.ok(not refuses_file(lambda r: r.__setitem__("secondary", 0)),
           "CONTROL: a stored 0 (none) loads")
    led.ok(charstore.CHAR_PROFESSIONS == agents.CHAR_PROFESSIONS == 11,
           "charstore's mirrored CHAR_PROFESSIONS equals agents' (11)")
    try:
        store3.set_character_secondary(UUID, 12)
        led.ok(False, "the setter refuses 12")
    except ValueError:
        led.ok(True, "the setter refuses 12 through the same validator")
    # the CLI, on the scratch base
    charstore.store_dir = lambda: base
    _r, out = quiet(charstore._main, ["--account", "secondary@rurik.invalid",
                                      "--character", "Sec Tester", "--secondary", "3",
                                      "--hero", "6", "--hero-secondary", "2"])
    led.ok(charstore.Store.open("secondary@rurik.invalid", base=base).character_secondary(UUID) == 3
           and charstore.Store.open("secondary@rurik.invalid", base=base).hero_secondary(UUID, 6) == 2
           and "secondary: 3" in out and "secondary=2" in out,
           "the CLI's --secondary / --hero-secondary write and print both",
           out.strip()[-160:])
    charstore.store_dir = _saved_store_dir
    # the client's own AUTH 0x0009 blob: verbatim, secondary bits intact
    blob = charsummary.encode({"appearance": 1 << 20, "level": 20, "campaign": 0,
                               "is_pvp": 1, "secondary": 4, "last_outpost": 248})
    led.ok(charsummary.decode(blob)["secondary"] == 4,
           "a summary blob encodes secondary 4 in its flag bits (the client's "
           "0 -> 4 push on the witness, 9 s after the change)")
    store4 = charstore.Store.open("secondary@rurik.invalid", base=base)
    hit = store4.update_settings("Sec Tester", blob)
    stored_blob = charstore.Store.open("secondary@rurik.invalid", base=base).character_by_uuid(UUID)["settings_blob"]
    led.ok(hit and stored_blob == blob.hex()
           and charsummary.decode(bytes.fromhex(stored_blob))["secondary"] == 4,
           "update_settings stores it VERBATIM and it decodes back with "
           "secondary 4 -- the existing store absorbs the client's push "
           "(verified, not assumed)")
    authsrv.PERSIST = False

    # -- §7 the master revert against 57e89956's literals ----------------------
    authsrv.SECONDARY_CHANGE_ENABLED = False
    authsrv.SECONDARY_BITS = 0
    led.ok(authsrv.load_secondary_offer() == 0 and HEAD["SECONDARY_BITS"] == 0,
           "REVERT: no 0x00B6 (offer 0; 57e89956 sent none with SECONDARY_BITS 0)")
    led.ok(authsrv.spawn_profession_values() == HEAD["player_0x00B7"],
           "REVERT: the player's default 0x00B7 is 57e89956's [1, 1, 0, 0]",
           f"{authsrv.spawn_profession_values()}")
    led.ok(authsrv.spawn_profession_values(7, 200) == HEAD["hero_0x00B7_prof7_agent200"],
           "REVERT: a hero's is 57e89956's [200, 7, 0, 0]",
           f"{authsrv.spawn_profession_values(7, 200)}")
    led.ok(agents.agent_set_profession(1, 1, 0) == HEAD["player_0x00A6"],
           "REVERT: the player's 0x00A6 is 57e89956's [1, 1, 0]")
    st = town_state()
    sent, rec, out = change(st, 1, 4)
    led.ok(sent == [] and "dropped" in out and "--no-secondary-change" in out
           and "player_secondary" not in st
           and rec.events[-1][1].get("refused") == "--no-secondary-change",
           "REVERT: c2s 0x0041 is dropped -- nothing sent, no state written, "
           "the log says which flag", out.strip()[-140:])
    led.ok(authsrv.player_secondary(st) == 0 and authsrv.attribute_state(st).secondary == 0,
           "REVERT: the pair the burst would carry is the launch pair (1/0)")
    authsrv.SECONDARY_BITS = 0x44
    led.ok(authsrv.load_secondary_offer() == 0x44,
           "REVERT + --secondary-bits 0x44: 0x00B6 with 0x44, as 57e89956 sent it")
    authsrv.SECONDARY_BITS = 0
    authsrv.SECONDARY_CHANGE_ENABLED = True

    # -- §8 source locks ---------------------------------------------------------
    import test_dispatch                                  # its harvesters, not its run
    arms = test_dispatch.dispatch_arms(TREE)
    led.ok(arms is not None and arms["GAME_CMSG"].get(CHANGE) == "GAME_CMSG_SET_SECONDARY_PROFESSION",
           "the dispatch chain has an arm on GAME_CMSG_SET_SECONDARY_PROFESSION "
           "(57e89956 had no constant at 0x0041 at all)",
           f"{arms['GAME_CMSG'].get(CHANGE) if arms else arms}")
    led.ok(CHANGE not in test_dispatch.DROPPED_ON_PURPOSE,
           "and 0x0041 is OFF test_dispatch's DROPPED_ON_PURPOSE list")
    arm_calls = [n for n in ast.walk(TREE)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "handle_secondary_change"]
    led.ok(len(arm_calls) == 1, "handle_secondary_change has exactly one call site (the arm)",
           f"{len(arm_calls)}")
    main_src = ast.get_source_segment(SRC, func_node("main"))
    led.ok("a.no_secondary_change" in main_src and "SECONDARY_CHANGE_ENABLED = False" in main_src
           and "a.no_secondary_cleanup" in main_src and "SECONDARY_CLEANUP_ENABLED = False" in main_src,
           "main() wires --no-secondary-change and --no-secondary-cleanup through "
           "their globals")
    args_src = open(ARGS_PATH, encoding="utf-8").read()
    led.ok('"--no-secondary-change"' in args_src and '"--no-secondary-cleanup"' in args_src,
           "serverargs.py declares both flags")
    led.ok("15 ARENA MAPS" not in args_src and "823-836), so" not in args_src,
           "serverargs' --secondary-bits help no longer claims the 15-map whitelist")
    ov = json.load(open(os.path.join(os.path.dirname(HERE), "..", "schema", "overrides.json"),
                        encoding="utf-8"))["channels"]
    row = ov["GAME_CMSG"].get("65", {})
    led.ok(row.get("name") == "SET_SECONDARY_PROFESSION" and row.get("name_confidence") == "medium"
           and [f["type"] for f in row.get("fields", [])] == ["msg_header", "agent_id", "byte"],
           "overrides.json names 0x0041 SET_SECONDARY_PROFESSION at medium with the "
           "catalog's [agent_id, byte] layout")
    led.ok("never sent or captured" not in ov["GAME_SMSG"]["182"]["why"].split("until 2026-09-25")[-1]
           and "95 of 95" in ov["GAME_SMSG"]["182"]["why"],
           "row 182's 'never captured' is corrected to the 95-of-95 census")
    hcb = ast.get_source_segment(SRC, func_node("hero_character_block"))
    led.ok("_hsec = hero_secondary(state, hid)" in hcb
           and "spawn_profession_values(_hprof, haid, secondary=_hsec)" in hcb
           and "agents.agent_set_profession(haid, int(_hprof), _hsec)" in hcb,
           "hero_character_block carries hero_secondary on both the 0x00B7 and the 0x00A6")
    led.ok("hero_secondary(state, _hid)" in psrc and "agents.hero_info(" in psrc,
           "the load's 0x0073 HERO_INFO carries the hero's secondary (field 4)")
    hsc = ast.get_source_segment(SRC, func_node("handle_secondary_change"))
    order = [hsc.index(s) for s in ("GAME_SMSG_ATTRIBUTE_POINTS_AVAILABLE",
                                    "GAME_SMSG_AGENT_UPDATE_ATTRIBUTE,",
                                    "GAME_SMSG_AGENT_PROFESSIONS,",
                                    "GAME_SMSG_AGENT_SET_PROFESSION,",
                                    "GAME_SMSG_UPDATE_UNLOCKED_SKILLS,",
                                    "GAME_SMSG_SKILLBAR_UPDATE_SKILL,")]
    led.ok(order == sorted(order),
           "the handler's send sites sit in the batch's order in the source "
           "(0x0038, 0x003B, 0x00B7, 0x00A6, 0x00DB, 0x00D9)", f"{order}")
    led.ok("GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS" not in hsc
           and "GAME_SMSG_AGENT_UPDATE_ATTRIBUTES" not in hsc.replace("GAME_SMSG_AGENT_UPDATE_ATTRIBUTE,", "")
           and "GAME_SMSG_AGENT_PROFESSION_BITS" not in hsc,
           "the handler never sends 0x0037 (the CREATOR asserts ChCliAttrib:313 on "
           "a live record), 0x003A (the load's bulk fill) or a 0x00B6 re-send")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(_saved_bar)
    charstore.store_dir = _saved_store_dir
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
