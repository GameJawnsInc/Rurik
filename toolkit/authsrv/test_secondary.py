"""The K panel's secondary-profession change -- SECONDARY-B1..B5
(studies/profession/SECONDARY.md, 2026-09-25).

    python toolkit/authsrv/test_secondary.py

WHAT THIS PINS, and what each part rests on:

  * §1 THE LOAD's 0x00B6 (OBSERVED, 95 of 95 live game connections): the
    default mask is retail's PvP form, 0x7FF & ~(1 << primary) -- the two
    literals on tape, 2045 for a Warrior and 1919 for an Assassin -- and
    `load_secondary_offer()` is the three regimes in one expression (the
    default, the --secondary-bits override, the revert's 0). The burst has
    TWO 0x00B6 sites (the fix pass, EV-3/CD-4): the feature's, IMMEDIATELY
    after the player's 0x00B7 (retail's adjacency, 95 of 95) and before the
    0x00A6, guarded by `_offer and SECONDARY_CHANGE_ENABLED`; and 57e89956's
    own, after the 0x00A6, taken only under the revert. Both are locked on
    the syntax tree, and §7 DRIVES the real burst in each regime. The 0x00B7
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
    does not read it; the hero's likewise (its equal-pair guard and its
    revert, the fix pass CD-5); the hero's cleanup REOPENED from the file
    (bar and ranks, CD-5); the store's three refusals; the mirrored
    CHAR_PROFESSIONS; the CLI, whose `--secondary 0` CLEARS the key so the
    launch value answers again (the fix pass, CD-2/EV-6 -- a stored 0 used
    to WIN over --spawn-secondary); a skill granted this session rides the
    change batch's 0x00DB without a store (the fix pass, CD-6); and the
    client's own AUTH 0x0009 blob round-trips VERBATIM with its secondary
    bits intact (verified, not assumed).
  * §7 THE MASTER REVERT against literals recorded from a `git archive
    57e89956` export of that tree (the fix pass; the first pass recorded the
    builders' values only): the REAL load burst driven in three regimes --
    the revert with --secondary-bits 0x44 reproduces the export's 43-send
    opcode list and whole-burst digest with the 0x00B6 AFTER the 0x00A6
    (57e89956's site), the revert alone reproduces its 42-send list and
    digest, and the feature on is that list plus ONE 0x00B6 right after the
    player's 0x00B7; 0x0041 under the revert takes 57e89956's PATH
    (note_unhandled: the census the disconnect report reads, the "unhandled"
    capture event) with nothing sent and no state written.
  * §8 SOURCE LOCKS: the arm, main()'s two flags, serverargs' two strings,
    the dropped-list row gone, overrides.json's name, the hero sites.
  * §9 THE LOAD WITH A STORED PAIR (the fix pass, CD-1/EV-1): the real burst
    under --persist with a scratch store holding the player's 4 and hero 6's
    5, in a town and a field, on the retail and the legacy rig -- EVERY
    0x00B7 / 0x00A6 addressed to the hero's agent carries [3, 5] (the town's
    bodiless-row 0x00A6, the field's body-create 0x00A6 and the legacy rig's
    0x00B7 all defaulted the secondary to 0 and, being LAST, overwrote the
    roster's summary record), the player's 0x00B7 / 0x00A6 carry 4, the
    0x0073 HERO_INFO's field 4 carries 5, and the 0x00B6 still follows the
    0x00B7.

SABOTAGE HOOK: RURIK_SECONDARY_AUTHSRV=<path> loads THAT copy of authsrv.py
as `authsrv` (siblings still from toolkit/authsrv), so each new guard can be
inverted in a scratch copy and shown to redden -- the study records which
mutation reddens which section.

Drives the real handlers with a fake send and a scratch store, like
test_heroadd.py. Floor from the green run (see the ledger line).
"""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading

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

led = checks.Ledger("secondary profession change (SECONDARY-B1..B5)", floor=152)   # 2026-09-25: 108 from the first green run; 152 after the fix pass (§7's real-burst drives, §9's four load drives, CD-2/CD-5/CD-6/EV-8/EV-11's checks), from its green run

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
# The 57e89956 LOAD BURST, recorded from `git archive 57e89956` by scratch
# base_ops.py (the fix pass): _handle_request_players driven with the module
# defaults but PERSIST False, SPAWN 1/0, OUTPOST True, state {"agents": {},
# "char_uuid": "3"*32, "map_id": 148}, no hero. Every opcode in send order,
# and the sha256[:16] of repr([(op, vals)]) over the whole list. A change to
# the load by ANOTHER arc reddens the list check legitimately -- the list
# says at which index -- and the relative check below it (revert == feature
# minus one 0x00B6) stays green across such changes.
BASE_OPS_BITS_0x44 = [390, 394, 242, 31, 89, 176, 177, 466, 459, 467, 434, 159, 240, 32, 55,
                      183, 166, 182, 29, 219, 218, 233, 239, 58, 156, 159, 159, 162, 110, 72,
                      53, 34, 398, 86, 87, 240, 32, 159, 166, 38, 53, 159, 159]
BASE_OPS_BITS_0 = [390, 394, 242, 31, 89, 176, 177, 466, 459, 467, 434, 159, 240, 32, 55,
                   183, 166, 29, 219, 218, 233, 239, 58, 156, 159, 159, 162, 110, 72,
                   53, 34, 398, 86, 87, 240, 32, 159, 166, 38, 53, 159, 159]
BASE_DIGEST_BITS_0x44, BASE_DIGEST_BITS_0 = "fb571a5b08ef885b", "85facec2223fa2e9"
BASE_PROF_BITS_0x44 = [(0xB7, [1, 1, 0, 0]), (0xA6, [1, 1, 0]), (0xB6, [1, 0x44])]
assert BASE_OPS_BITS_0x44[15:18] == [0xB7, 0xA6, 0xB6] and BASE_OPS_BITS_0[15:17] == [0xB7, 0xA6]
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
           "OUTPOST", "HERO_BODY", "HERO_ATTRIBUTES", "HERO_SKILLS",
           # the load-drive rig (§7, §9): drive_load's, restored per drive
           "HERO", "HERO_BODY_NPC", "HERO_ACTIVATE", "HERO_PIPELINE_FIRST",
           "HERO_CHAR", "HERO_INVENTORY", "HERO_BAGS", "HERO_RIG_RETAIL",
           "UNLOCKED")}
_saved_bar = list(authsrv.SKILLBAR)
_saved_store_dir = charstore.store_dir
base = tempfile.mkdtemp(prefix="secondary-test-")

# The test's standing fixture (a Koss-shaped hero 6 at agent 200, bodiless),
# re-applied after every load drive so §7/§9's rigs cannot leak forward.
FIXTURE = {"PERSIST": False, "SPAWN_PROFESSION": 1, "SPAWN_SECONDARY": 0,
           "SECONDARY_BITS": 0, "SECONDARY_CHANGE_ENABLED": True,
           "SECONDARY_CLEANUP_ENABLED": True, "HERO_IDS": [6], "HERO_AGENT_ID": 200,
           "HERO_ROWS": {6: {"hero": 6, "body": "koss", "profession": 3,
                             "skills": [105, 1, 2]}},
           "HERO_KICK_ENABLED": True, "HERO_BODY": False, "HERO_ATTRIBUTES": {},
           "EXPLORABLE": False, "OUTPOST": False}


def apply(cfg):
    for k, v in cfg.items():
        setattr(authsrv, k, v)


def drive_load(*, town, rig="retail", cfg=None, state_extra=None, bar=None):
    """Run the REAL load burst (_handle_request_players) and return its send
    list [(op, vals, label)]. `rig="none"` is the module's own defaults (the
    57e89956 recording's configuration); "retail"/"legacy" is drive_load.py's
    party rig: hero 6 at agent 200 with the academy_monk body. `cfg` is
    applied LAST (the regime under test: the two flags, PERSIST)."""
    apply({k: _saved[k] for k in _saved})               # the module's defaults first
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(bar if bar is not None else _saved_bar)
    apply({"PERSIST": False, "SPAWN_PROFESSION": 1, "SPAWN_SECONDARY": 0,
           "OUTPOST": bool(town), "EXPLORABLE": not town})
    if rig != "none":
        apply({"HERO": 6, "HERO_IDS": [6], "HERO_AGENT_ID": 200,
               "HERO_ROWS": {6: {"hero": 6, "body": "academy_monk", "profession": 3,
                                 "skills": [105, 1, 2]}},
               "HERO_BODY": True, "HERO_BODY_NPC": "academy_monk", "HERO_ACTIVATE": True,
               "HERO_PIPELINE_FIRST": rig == "retail", "HERO_CHAR": True,
               "HERO_INVENTORY": 2, "HERO_BAGS": True, "HERO_RIG_RETAIL": rig == "retail"})
    apply(cfg or {})
    st = {"agents": {}, "char_uuid": UUID, "map_id": 148}
    st.update(state_extra or {})
    sent = []

    def send(op, vals, label=None):
        sent.append((op, vals, label))
    quiet(authsrv._handle_request_players, send, st, 0, threading.Event(), FakeRec())
    return sent, st


def burst_digest(sent):
    return hashlib.sha256(repr([(op, vals) for op, vals, _l in sent]).encode()).hexdigest()[:16]


def to_agent(sent, agent, *ops):
    """[(index, op, vals)] of the sends of `ops` addressed to `agent`."""
    return [(i, op, vals) for i, (op, vals, _l) in enumerate(sent)
            if op in ops and isinstance(vals, list) and vals and vals[0] == agent]
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
           "the load's FIRST 0x00B6 send site is the NEXT send after the player's "
           "0x00B7 (retail: adjacent on 95 of 95; the record 0x00B6 writes into is "
           "created by 0x00B7)",
           f"sends around it: {names[max(0, (i_b7 or 0) - 1):(i_b7 or 0) + 3]}")
    led.ok(i_a6 is not None and i_b6 is not None and i_b6 < i_a6,
           "...and before the player's 0x00A6 (it sat after it under "
           "--secondary-bits until 2026-09-25)",
           f"0x00B6 at index {i_b6}, 0x00A6 at {i_a6}")
    i_b6_all = [i for i, nm in enumerate(names) if nm == "GAME_SMSG_AGENT_PROFESSION_BITS"]
    led.ok(len(i_b6_all) == 2 and i_a6 is not None and i_b6_all[1] > i_a6,
           "and there is exactly ONE more 0x00B6 site, AFTER the 0x00A6 -- "
           "57e89956's own placement, the revert's (the fix pass, EV-3/CD-4)",
           f"0x00B6 sites at send indices {i_b6_all}, 0x00A6 at {i_a6}")
    b6_calls = [n for n in ast.walk(players)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "send" and n.args and isinstance(n.args[0], ast.Name)
                and n.args[0].id == "GAME_SMSG_AGENT_PROFESSION_BITS"]
    b6_calls.sort(key=lambda n: n.lineno)

    def guard_of(call):
        best = None
        for node in ast.walk(players):
            if isinstance(node, ast.If) and any(c is call for c in ast.walk(node)):
                if best is None or node.lineno > best.lineno:
                    best = node                      # the innermost If holding the call
        return ast.unparse(best.test) if best is not None else None
    guards = [guard_of(c) for c in b6_calls]
    led.ok(guards == ["_offer and SECONDARY_CHANGE_ENABLED",
                      "_offer and (not SECONDARY_CHANGE_ENABLED)"]      # ast.unparse's spelling
           and "_offer = load_secondary_offer()" in psrc,
           "the two sites are guarded by the SAME `_offer = load_secondary_offer()` "
           "split on SECONDARY_CHANGE_ENABLED -- the feature's site and the "
           "revert's, one expression for the mask in every regime",
           f"guards {guards}")
    led.ok("_psec = player_secondary(state)" in psrc
           and "spawn_profession_values(secondary=_psec)" in psrc,
           "the player's 0x00B7 carries player_secondary(state) through the "
           "builder (the stored change over the launch value)")
    led.ok(len(b6_calls) == 2 and all(
        isinstance(c.args[1], ast.Call) and isinstance(c.args[1].func, ast.Attribute)
        and c.args[1].func.attr == "agent_set_secondary_bits"
        for c in b6_calls),
           "and both masks go through agents.agent_set_secondary_bits (the u32 "
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
    # (the fix pass, CD-5 M4) a no-op re-pick with a RANK in the current
    # secondary: the cleanup is gated on `changed`, so nothing is zeroed
    ast_noop = authsrv.attribute_state(st)
    ast_noop.points_total = 200
    ast_noop.ranks.clear()
    ast_noop.ranks.update({5: 2})                      # Necro attr 5, the CURRENT secondary's
    sent, rec, out = change(st, 1, 4)
    led.ok(ops(sent) == [PROFS, SETPROF, LIBRARY] and ast_noop.ranks.get(5) == 2
           and rec.events[-1][1].get("zeroed") == [],
           "a no-op re-pick with a rank in the CURRENT secondary sends exactly the "
           "batch and keeps the rank (the cleanup is gated on a real change)",
           f"got {[hex(o) for o in ops(sent)]}, attr 5 at {ast_noop.ranks.get(5)}")
    ast_noop.ranks.clear()
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
    # a hero with a rank and a bar skill in its old secondary -- and a BODY
    # in the world (the fix pass, CD-5 M5): the body row casts the edited bar
    st = town_state(hero_secondary={6: 4})
    st["agents"][200] = {"skills": list(authsrv.bar_triples([105, 1, 2])),
                         "skill_ready": [0.0, 0.0, 0.0], "hero": 6}
    hst = authsrv.hero_attribute_state(st, 6)
    led.ok(hst.secondary == 4 and hst.primary == 3,
           "hero 6 as a Mo/N (session secondary 4)")
    hst.points_total = 30
    hst.ranks.clear()
    hst.ranks.update({5: 2})
    h_avail = hst.available
    sent, rec, out = change(st, 200, 1)
    led.ok([s[0] for s in st["agents"][200]["skills"]] == [1, 2]
           and "now casts [1, 2]" in out,
           "the hero's BODY casts the edited bar from now on (sync_hero_body_bar: "
           "105 gone from its skills)", f"{st['agents'][200]['skills']}")
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
    # (the fix pass, CD-5 M1/M8) the hero's equal-pair guard and its revert
    store_h = charstore.Store.open("secondary@rurik.invalid", base=base)
    store_h.set_hero_secondary(UUID, 6, 3)             # == hero 6's row profession
    val, out = quiet(authsrv.hero_secondary,
                     town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base)), 6)
    led.ok(val == 0 and "ignored" in out and "hero 6" in out,
           "a stored hero secondary EQUAL to the hero's primary (3/3) is ignored "
           "loudly and 0 answers", out.strip()[-140:])
    store_h.set_hero_secondary(UUID, 6, 5)
    authsrv.SECONDARY_CHANGE_ENABLED = False
    led.ok(authsrv.hero_secondary(
        town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base)), 6) == 0,
           "under --no-secondary-change a stored HERO secondary is not read either")
    authsrv.SECONDARY_CHANGE_ENABLED = True
    # (the fix pass, CD-5 M2/M3) the hero's cleanup, REOPENED from the file:
    # a Mo/N hero with a rank in 5 and 105 on its stored bar goes to Mo/W
    store_c = charstore.Store.open("secondary@rurik.invalid", base=base)
    store_c.set_hero_secondary(UUID, 6, 4)
    store_c.set_hero_skillbar(UUID, 6, [105, 1, 2, 0, 0, 0, 0, 0])
    store_c.set_hero_attributes(UUID, 6, [(5, 2)])
    st = town_state(charstore_game=store_c)
    hst = authsrv.hero_attribute_state(st, 6)
    led.ok(hst.secondary == 4 and hst.ranks.get(5) == 2
           and authsrv.hero_panel_bar_ids(st, 6)[0] == 105,
           "(a Mo/N hero from the store: attr 5 at 2, 105 on the stored bar)")
    sent, rec, out = change(st, 200, 1)
    reopened_h = charstore.Store.open("secondary@rurik.invalid", base=base).hero_row(UUID, 6)
    led.ok(ops(sent) == [POINTS_AVAIL, ATTR_ONE, PROFS, SETPROF, BAR_ONE]
           and reopened_h.get("secondary") == 1
           and reopened_h.get("skillbar") == [0, 1, 2, 0, 0, 0, 0, 0]
           and [list(p) for p in reopened_h.get("attributes") or []] == [],
           "the hero's cleanup PERSISTS all three, read back from the FILE: "
           "secondary 1, the bar without 105, the ranks without attr 5",
           f"row {reopened_h}")
    # (the fix pass, CD-2/EV-6) the documented reset restores the LAUNCH value
    store_r = charstore.Store.open("secondary@rurik.invalid", base=base)
    store_r.set_character_secondary(UUID, 4)
    authsrv.SPAWN_SECONDARY = 2                        # --spawn-secondary 2 / a party row's 2
    led.ok(authsrv.player_secondary(
        town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))) == 4,
           "(a stored 4 wins over the launch 2, as §6 says)")
    charstore.store_dir = lambda: base
    _r, out = quiet(charstore._main, ["--account", "secondary@rurik.invalid",
                                      "--character", "Sec Tester", "--secondary", "0"])
    charstore.store_dir = _saved_store_dir
    row_r = charstore.Store.open("secondary@rurik.invalid", base=base).character_by_uuid(UUID)
    led.ok("secondary" not in row_r
           and authsrv.player_secondary(
               town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))) == 2,
           "`charstore.py --secondary 0` CLEARS the key and the launch value (2) "
           "answers again -- a stored 0 used to WIN over --spawn-secondary "
           "(reviewers' CD-2/EV-6)", f"row keys {sorted(row_r)}")
    store_z = charstore.Store.open("secondary@rurik.invalid", base=base)
    store_z.character_by_uuid(UUID)["secondary"] = 0   # a hand-edited file holding 0
    store_z.save()
    led.ok(charstore.Store.open("secondary@rurik.invalid", base=base).character_by_uuid(UUID).get("secondary") == 0
           and charstore.Store.open("secondary@rurik.invalid", base=base).character_secondary(UUID) is None
           and authsrv.player_secondary(
               town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base))) == 2,
           "...and a file that still HOLDS a 0 reads as absent (the launch value)")
    led.ok(charstore.Store.open("secondary@rurik.invalid", base=base).hero_secondary(UUID, 6) == 1
           and charstore.Store.open("secondary@rurik.invalid", base=base).set_hero_secondary(UUID, 6, 0) == 0
           and "secondary" not in charstore.Store.open("secondary@rurik.invalid", base=base).hero_row(UUID, 6)
           and authsrv.hero_secondary(
               town_state(charstore_game=charstore.Store.open("secondary@rurik.invalid", base=base)), 6) == 0,
           "the hero's setter clears on 0 the same way")
    authsrv.SPAWN_SECONDARY = 0
    # (the fix pass, CD-6) a skill GRANTED this session rides the batch's 0x00DB
    authsrv.PERSIST = False
    authsrv.UNLOCKED = skillunlock.words_from_ids([1, 2])
    st = town_state()                                  # no store attached
    sent, send = fake_send_factory()
    quiet(authsrv.grant_skill, send, st, 105, 0)
    granted_ops = ops(sent)
    sent, rec, out = change(st, 1, 4)
    lib_ids = set(skillunlock.ids_from_words(dict(sent)[LIBRARY][0]))
    led.ok(0x00DC in granted_ops and st.get("skills_known") == {105}
           and lib_ids == {1, 2, 105},
           "without a store, a skill grant_skill taught this session (0x00DC 105) is "
           "in the change batch's 0x00DB beside the flag library {1, 2} -- the "
           "re-send cannot contradict the server's own grant",
           f"granted {[hex(o) for o in granted_ops]}, library {sorted(lib_ids)}")
    authsrv.UNLOCKED = _saved["UNLOCKED"]
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])
    authsrv.PERSIST = True
    # the store's refusals
    BAD_UUID = "44444444444444444444444444444444"   # its own uuid: §9's directory scan must not find it

    def refuses_file(mutate):
        p = charstore.path_for("bad@rurik.invalid", base)
        data = charstore._fresh("bad@rurik.invalid")
        data["characters"][BAD_UUID] = {"name": "Bad", "settings_blob": "", "level": 1,
                                        "xp": 0, "skill_points": 0, "attributes": []}
        mutate(data["characters"][BAD_UUID])
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
           and "player_secondary" not in st,
           "REVERT: c2s 0x0041 is dropped -- nothing sent, no state written, "
           "the log says which flag", out.strip()[-140:])
    led.ok(st.get("unhandled", {}).get(("GAME_CMSG", CHANGE))
           == HEAD["unhandled_count_after_one_0x0041"]
           and rec.events and rec.events[-1][0] == "unhandled"
           and rec.events[-1][1].get("opcode") == CHANGE
           and "UNHANDLED GAME_CMSG 0x8041" in out,
           "REVERT: 0x0041 takes 57e89956's PATH -- note_unhandled's census counts "
           "it once (the disconnect report's and msgmix.py's number) and the "
           "capture records an 'unhandled' event (the fix pass, EV-8/CD-4)",
           f"unhandled {st.get('unhandled')}, events {[e[0] for e in rec.events]}")
    led.ok(authsrv.player_secondary(st) == 0 and authsrv.attribute_state(st).secondary == 0,
           "REVERT: the pair the burst would carry is the launch pair (1/0)")
    authsrv.SECONDARY_BITS = 0x44
    led.ok(authsrv.load_secondary_offer() == 0x44,
           "REVERT + --secondary-bits 0x44: 0x00B6 with 0x44, as 57e89956 sent it")
    # THE REAL BURST, three regimes, against the export's recording (the fix
    # pass, EV-3/CD-4). drive_load restores the module defaults first, so the
    # configuration is the recording's.
    sent44, _st = drive_load(town=True, rig="none",
                             cfg={"SECONDARY_CHANGE_ENABLED": False, "SECONDARY_BITS": 0x44})
    prof44 = [(op, vals) for op, vals, _l in sent44 if op in (PROFS, BITS, SETPROF)
              and isinstance(vals, list) and vals and vals[0] == 1]
    led.ok(prof44 == BASE_PROF_BITS_0x44,
           "REVERT + --secondary-bits 0x44, the real burst: 0x00B7 [1,1,0,0] -> "
           "0x00A6 [1,1,0] -> 0x00B6 [1, 0x44] -- 57e89956's ORDER (the 0x00B6 "
           "after the 0x00A6), not the feature's",
           f"got {[(hex(o), v) for o, v in prof44]}")
    def first_diff(a, b):
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return i
        return None if len(a) == len(b) else min(len(a), len(b))
    ops44 = [op for op, _v, _l in sent44]
    led.ok(ops44 == BASE_OPS_BITS_0x44,
           f"...and the whole {len(BASE_OPS_BITS_0x44)}-send opcode list is the export's",
           f"{len(ops44)} sends; first difference at index {first_diff(ops44, BASE_OPS_BITS_0x44)}")
    led.ok(burst_digest(sent44) == BASE_DIGEST_BITS_0x44,
           "...values included (the whole-burst digest is the export's)",
           f"{burst_digest(sent44)} vs {BASE_DIGEST_BITS_0x44}")
    sent0, _st = drive_load(town=True, rig="none",
                            cfg={"SECONDARY_CHANGE_ENABLED": False, "SECONDARY_BITS": 0})
    ops0 = [op for op, _v, _l in sent0]
    led.ok(ops0 == BASE_OPS_BITS_0 and BITS not in ops0,
           f"REVERT alone, the real burst: the export's {len(BASE_OPS_BITS_0)}-send "
           f"opcode list, no 0x00B6",
           f"{len(ops0)} sends; first difference at index {first_diff(ops0, BASE_OPS_BITS_0)}")
    led.ok(burst_digest(sent0) == BASE_DIGEST_BITS_0,
           "...and its whole-burst digest", f"{burst_digest(sent0)} vs {BASE_DIGEST_BITS_0}")
    senton, _st = drive_load(town=True, rig="none",
                             cfg={"SECONDARY_CHANGE_ENABLED": True, "SECONDARY_BITS": 0})
    opson = [op for op, _v, _l in senton]
    i_on = opson.index(BITS) if BITS in opson else None
    led.ok(i_on is not None and opson.count(BITS) == 1 and opson[i_on - 1] == PROFS
           and senton[i_on][1] == [1, 2045]
           and [(op, vals) for op, vals, _l in senton if op != BITS]
           == [(op, vals) for op, vals, _l in sent0],
           "the FEATURE ON is the revert's burst plus exactly ONE 0x00B6 [1, 2045] "
           "right after the player's 0x00B7 -- values included, nothing else moves "
           "(the relative check that outlives another arc's change to the load)",
           f"0x00B6 at index {i_on}, {len(senton)} sends vs {len(sent0)}")
    apply(FIXTURE)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend([105, 1, 2, 0, 0, 0, 0, 0])

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
    led.ok("return instance_is_field(state)" in ast.get_source_segment(SRC, func_node("instance_is_explorable"))
           and "1 if instance_is_field(state) else 0" in ast.get_source_segment(SRC, func_node("handle")),
           "instance_is_explorable is an alias of instance_is_field and the 0x0199 "
           "send site evaluates the same helper -- one copy of the town byte's rule "
           "(the fix pass, EV-11)")

    # -- §9 the LOAD with a stored pair (the fix pass, CD-1/EV-1, CD-5) ----------
    # A scratch store holding the player's 4 and hero 6's 5, found by the REAL
    # --persist path (charstore.find_character over a patched store_dir).
    store9 = charstore.Store.open("secondary@rurik.invalid", base=base)
    store9.set_character_secondary(UUID, 4)
    store9.set_hero_secondary(UUID, 6, 5)
    charstore.store_dir = lambda: base
    try:
        for town, rig in ((True, "retail"), (False, "retail"), (True, "legacy"), (False, "legacy")):
            where = f"{'town' if town else 'field'}/{rig}"
            sent9, st9 = drive_load(town=town, rig=rig, cfg={"PERSIST": True})
            led.ok(st9.get("charstore_game") is not None
                   and st9["charstore_game"].character_secondary(UUID) == 4,
                   f"[{where}] the load found the scratch store through --persist's own path",
                   f"{len(sent9)} sends")
            hero_pairs = to_agent(sent9, 200, PROFS, SETPROF)
            led.ok(len(hero_pairs) >= 2
                   and all(vals[1:3] == [3, 5] for _i, _op, vals in hero_pairs),
                   f"[{where}] EVERY 0x00B7 / 0x00A6 addressed to the hero's agent carries "
                   f"the stored pair [3, 5] -- {len(hero_pairs)} of them, the LAST included "
                   f"(the summary record the roster reads is last-write-wins)",
                   f"{[(i, hex(op), vals) for i, op, vals in hero_pairs]}")
            led.ok(hero_pairs and hero_pairs[-1][2][1:3] == [3, 5],
                   f"[{where}] ...and the last one in particular",
                   f"last {hero_pairs[-1] if hero_pairs else None}")
            info = [vals for op, vals, _l in sent9 if op == 0x0073 and vals and vals[0] == 6]
            if rig == "retail":                        # the legacy rig sends no 0x0073 (JARIN's message)
                led.ok(info and info[0][2:4] == [3, 5],
                       f"[{where}] the 0x0073 HERO_INFO for hero 6 carries the pair in fields 3-4",
                       f"{info[0][:5] if info else None}")
            player_pairs = to_agent(sent9, 1, PROFS, SETPROF)
            led.ok([vals for _i, _op, vals in player_pairs] == [[1, 1, 4, 0], [1, 1, 4]],
                   f"[{where}] the player's 0x00B7 [1, 1, 4, 0] and 0x00A6 [1, 1, 4] carry the "
                   f"stored 4 over the launch 0",
                   f"{[(hex(op), vals) for _i, op, vals in player_pairs]}")
            i_b7p = [i for i, op, vals in to_agent(sent9, 1, PROFS)][0]
            led.ok(sent9[i_b7p + 1][0] == BITS and sent9[i_b7p + 1][1] == [1, 2045],
                   f"[{where}] the 0x00B6 [1, 2045] still follows the player's 0x00B7",
                   f"{hex(sent9[i_b7p + 1][0])} {sent9[i_b7p + 1][1]}")
            if not town:
                body = [(i, vals, l) for i, (op, vals, l) in enumerate(sent9)
                        if op == SETPROF and vals and vals[0] == 200]
                led.ok(body and (body[-1][2] or "").startswith("AGENT_SET_PROFESSION(200, 3/5")
                       and body[-1][1] == [200, 3, 5],
                       f"[{where}] the LAST hero 0x00A6 is the body's create-burst send "
                       f"(create_agent_world), and it carries the pair", f"{body}")
    finally:
        charstore.store_dir = _saved_store_dir
        apply(FIXTURE)
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(_saved_bar)
    charstore.store_dir = _saved_store_dir
    shutil.rmtree(base, ignore_errors=True)

sys.exit(led.verdict())
