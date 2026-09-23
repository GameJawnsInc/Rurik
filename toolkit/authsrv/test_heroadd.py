"""The hero add, c2s 0x001E HERO_ADD -- SANDBOX-N2's other half (studies/cmsg/
FINDINGS.md DESKWORK-D1 step 4), and the 0x0018 hero-unlock mask that ships
with it.

    python toolkit/authsrv/test_heroadd.py

WHAT THIS PINS. The add is RECONSTRUCTION end to end -- no tape carries a c2s
0x001E -- so nothing here compares to a retail chunk; what it pins is that the
handler sends exactly the load pipeline's own messages for the hero, in
retail's LOAD order, and that it is the kick's inverse.

  * §1 THE BATCH, town rig: `handle_hero_add` on a kicked hero sends the
    hero's character block (byte-identical to `hero_character_block`, the
    load's own), then 0x0072, then 0x00B0 with the hero COUNTED, then a bare
    0x01C2 -- and NO 0x0073 (the record exists from load). The order predicate
    is `retail_load_order`, and its KNOWN-BAD arms are a rotated batch and a
    row-before-size swap through the same predicate (the kick's order), which
    must fail it.
  * §2 REFUSALS send NOTHING: an unowned index, a hero already in the party,
    and an EIGHTH hero (HEROES_PARTY_MAX, the cap in one name) -- with the
    positive control that the SEVENTH is accepted.
  * §3 THE ROUND TRIP under --persist: kick writes the store, add clears it, a
    fresh connection seeds an empty set and parties the hero (the kick's
    acceptance in reverse); a second add is refused; --persist OFF writes
    nothing.
  * §4 THE BODY, field rig: after 0x01C2 the body's create burst goes out
    through `hero_body_create` -- the SAME function the load calls -- at the
    player's side in formation slot 0; kick-then-add re-creates it at the same
    agent id; a town rig (known-bad for the field claim) sends no create.
  * §5 THE 0x0018 MASK: `hero_unlock_mask` reproduces the tape's two values
    from the owned set ([64] for hero 6, [224] for 5/6/7), keeps OpenTyria's
    all-ones with no hero authored or under --no-hero-unlock-mask, and needs a
    second dword for an index >= 32; the sender is ONE site and the old
    literal is gone.
  * §6 SOURCE LOCKS (syntax tree over authsrv.py): the 0x001E arm calls
    handle_hero_add only under HERO_ADD_ENABLED; main() wires both flags;
    hero_body_create is called from BOTH the load path and the add; the load's
    _party_size counts party_hero_slots. Each has a mutation that reddens it.

Drives the real handler with a fake send and a scratch store, like
test_herokick.py. Floor 48.
"""
import ast
import os
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
import authsrv                                               # noqa: E402

led = checks.Ledger("hero add (SANDBOX-N2)", floor=48)

SRC_PATH = os.path.join(HERE, "authsrv.py")
KICK, ADD = authsrv.GAME_CMSG_HERO_KICK, authsrv.GAME_CMSG_HERO_ADD
HERO_ACTIVATE, PARTY_SIZE, PARTY_HERO_ADD = 0x0072, 0x00B0, 0x01C2
HERO_INFO, ATTR_POINTS, ATTRIBUTES = 0x0073, 0x0037, 0x003A
UUID = "22222222222222222222222222222222"


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals) if isinstance(vals, (list, tuple)) else vals))
    return sent, send


def ops(sent):
    return [op for op, _v in sent]


def retail_load_order(op_list):
    """Retail's load order for one hero (20260916T150306 :62321): the block
    (0x0037 first, 0x003A last) then 0x0072, then 0x00B0, then 0x01C2 -- and
    no 0x0073. False when any is missing or out of order."""
    try:
        i37, i3a = op_list.index(ATTR_POINTS), op_list.index(ATTRIBUTES)
        i72, ib0, ic2 = (op_list.index(HERO_ACTIVATE), op_list.index(PARTY_SIZE),
                         op_list.index(PARTY_HERO_ADD))
    except ValueError:
        return False
    return (i37 == 0 and i37 < i3a < i72 < ib0 < ic2
            and HERO_INFO not in op_list)


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "PERSIST", "HENCHMAN", "HERO_INVENTORY", "HERO_BAGS",
           "HERO_AGENT_ID", "PLAYER_NUMBER", "HERO_KICK_ENABLED", "HERO_ADD_ENABLED",
           "HERO_UNLOCK_MASK", "RESET_HERO_KICKS", "PARTY_COMMANDS", "HERO_BODY",
           "EXPLORABLE", "OUTPOST", "PARTY_BODY_IN_OUTPOST")}
base = tempfile.mkdtemp(prefix="heroadd-test-")
try:
    authsrv.HERO_IDS = [6]
    authsrv.HERO_AGENT_ID = 200
    authsrv.PLAYER_NUMBER = 68
    authsrv.HENCHMAN = None
    authsrv.PERSIST = False
    authsrv.HERO_KICK_ENABLED = True
    authsrv.HERO_ADD_ENABLED = True
    authsrv.RESET_HERO_KICKS = False
    authsrv.PARTY_COMMANDS = True
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY = False, 0
    authsrv.HERO_BODY = False
    authsrv.EXPLORABLE, authsrv.OUTPOST, authsrv.PARTY_BODY_IN_OUTPOST = False, False, False

    # -- §1 the batch, town rig -----------------------------------------------
    state = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}}
    led.ok([h for h, _a, _d in authsrv.party_hero_slots(state)] == [],
           "the rig starts with hero 6 OWNED and KICKED (not in the party)")
    block = [op for op, _v, _l in authsrv.hero_character_block(state, 200, 6)]
    sent, send = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], send, state, 0)
    got = ops(sent)
    led.ok(got[:len(block)] == block and len(block) >= 6,
           "the add opens with the hero's character block, op for op the load "
           "pipeline's own (hero_character_block)",
           f"block {[hex(o) for o in block]}; got {[hex(o) for o in got[:len(block)]]}")
    led.ok(got[len(block):] == [HERO_ACTIVATE, PARTY_SIZE, PARTY_HERO_ADD],
           "...then exactly 0x0072, 0x00B0, 0x01C2 -- activation, size, a bare "
           "roster row -- and nothing else",
           f"tail {[hex(o) for o in got[len(block):]]}")
    led.ok(retail_load_order(got),
           "the whole batch is in retail's LOAD order for a hero (block, 0x0072, "
           "0x00B0, 0x01C2; no 0x0073)")
    led.ok(dict(sent).get(PARTY_SIZE) == [68, 2],
           "0x00B0 counts the hero: [player 68, size 2]",
           f"got {dict(sent).get(PARTY_SIZE)}")
    led.ok(dict(sent).get(PARTY_HERO_ADD) == [1, 68, 200, 6, authsrv.HERO_MSG14],
           "0x01C2 is [party 1, owner 68, agent 200, hero 6, HERO_MSG14] -- the "
           "load path's own arguments", f"got {dict(sent).get(PARTY_HERO_ADD)}")
    led.ok(dict(sent).get(HERO_ACTIVATE) == [6, 200, 0, 0],
           "0x0072 is [hero 6, agent 200, inventory 0, aiMode 0] on the default rig",
           f"got {dict(sent).get(HERO_ACTIVATE)}")
    led.ok(not authsrv.hero_kicked(state, 6)
           and [h for h, _a, _d in authsrv.party_hero_slots(state)] == [6],
           "the hero is back in the party set")
    led.ok(authsrv.GAME_SMSG_WORLD_CREATE_AGENT not in got
           and 200 not in state["agents"],
           "a TOWN rig creates no body (as at load)")
    # KNOWN-BAD arms through the SAME predicate.
    rotated = got[1:] + got[:1]
    led.ok(not retail_load_order(rotated),
           "KNOWN-BAD: a rotated batch fails the order predicate")
    ib0, ic2 = got.index(PARTY_SIZE), got.index(PARTY_HERO_ADD)
    swapped = list(got)
    swapped[ib0], swapped[ic2] = swapped[ic2], swapped[ib0]
    led.ok(not retail_load_order(swapped),
           "KNOWN-BAD: row-before-size (the KICK's order) fails it -- the add "
           "mirrors the henchman add's size-then-row, 3 of 3 on tape")
    led.ok(not retail_load_order([HERO_INFO] + got),
           "KNOWN-BAD: a batch that re-sends 0x0073 fails it")

    # -- §2 refusals ------------------------------------------------------------
    s2, send2 = fake_send_factory()
    st2 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}}
    authsrv.handle_hero_add([ADD, 99], send2, st2, 0)
    led.ok(s2 == [] and authsrv.hero_kicked(st2, 6),
           "an UNOWNED index sends nothing and changes nothing")
    s3, send3 = fake_send_factory()
    st3 = {"agents": {}, "char_uuid": UUID}                  # hero 6 in the party
    authsrv.handle_hero_add([ADD, 6], send3, st3, 0)
    led.ok(s3 == [],
           "a hero ALREADY IN THE PARTY sends nothing (the kick's 'already "
           "kicked' mirror)")
    authsrv.HERO_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
    s4, send4 = fake_send_factory()
    st4 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {8}}
    led.ok(len(authsrv.party_hero_slots(st4)) == authsrv.HEROES_PARTY_MAX == 7,
           "the cap rig: eight owned, seven in the party, HEROES_PARTY_MAX 7")
    authsrv.handle_hero_add([ADD, 8], send4, st4, 0)
    led.ok(s4 == [] and authsrv.hero_kicked(st4, 8),
           "the EIGHTH hero is refused: nothing sent, still kicked (the cap lives "
           "in HEROES_PARTY_MAX, PtPlayer:332)")
    authsrv.HERO_IDS = [1, 2, 3, 4, 5, 6, 7]
    s5, send5 = fake_send_factory()
    st5 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {7}}
    authsrv.handle_hero_add([ADD, 7], send5, st5, 0)
    led.ok(retail_load_order(ops(s5)) and dict(s5).get(PARTY_SIZE) == [68, 8],
           "CONTROL: the SEVENTH is accepted -- party 8 (player + 7 heroes)",
           f"size {dict(s5).get(PARTY_SIZE)}")
    authsrv.HERO_IDS = [6]

    # -- §3 the round trip under --persist ---------------------------------------
    authsrv.PERSIST = True
    store = charstore.Store.open("heroadd@rurik.invalid", base=base)
    store.ensure_character(UUID, "Adder", "bb" * 37)
    stp = {"agents": {}, "char_uuid": UUID, "charstore_game": store}
    authsrv.handle_hero_kick([KICK, 6], fake_send_factory()[1], stp, 0)
    led.ok(store.kicked_heroes(UUID) == [6] and authsrv.hero_kicked(stp, 6),
           "KICK under --persist: the store holds [6]")
    sp, sendp = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendp, stp, 0)
    led.ok(store.kicked_heroes(UUID) == [] and not authsrv.hero_kicked(stp, 6)
           and retail_load_order(ops(sp)),
           "ADD under --persist: the store's kick is CLEARED and the batch goes out")
    reopened = charstore.Store.open("heroadd@rurik.invalid", base=base)
    fresh = {"agents": {}, "char_uuid": UUID, "charstore_game": reopened}
    led.ok(reopened.kicked_heroes(UUID) == []
           and authsrv.kicked_heroes_set(fresh) == set()
           and [h for h, _a, _d in authsrv.party_hero_slots(fresh)] == [6],
           "the next connection seeds an EMPTY kicked set and parties hero 6 "
           "again -- the kick's acceptance (b), inverted")
    sq, sendq = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendq, stp, 0)
    led.ok(sq == [], "a second add of the same hero is refused (already in)")
    # kick -> add -> kick: the store follows every step.
    authsrv.handle_hero_kick([KICK, 6], fake_send_factory()[1], stp, 0)
    led.ok(store.kicked_heroes(UUID) == [6],
           "kick again after the add: the store holds [6] again")
    authsrv.PERSIST = False
    store2 = charstore.Store.open("heroadd@rurik.invalid", base=base)
    stn = {"agents": {}, "char_uuid": UUID, "charstore_game": store2,
           "kicked_heroes": {6}}
    sn, sendn = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendn, stn, 0)
    led.ok(retail_load_order(ops(sn))
           and charstore.Store.open("heroadd@rurik.invalid",
                                    base=base).kicked_heroes(UUID) == [6],
           "with --persist OFF the add sends its batch and writes NOTHING to the "
           "store (which still holds the earlier kick)")

    # -- §4 the body, field rig ---------------------------------------------------
    authsrv.HERO_BODY = True
    authsrv.EXPLORABLE = True
    led.ok(authsrv.party_bodies_here({"map_id": 168}),
           "the field rig: party_bodies_here is True under --explorable")
    stf = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6},
           "pos": (500.0, 500.0), "plane": 0, "map_id": 168,
           "spawn_point": (500.0, 500.0, 0)}
    sf, sendf = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendf, stf, 0)
    gf = ops(sf)
    create_i = gf.index(authsrv.GAME_SMSG_WORLD_CREATE_AGENT) \
        if authsrv.GAME_SMSG_WORLD_CREATE_AGENT in gf else -1
    led.ok(retail_load_order(gf) and create_i > gf.index(PARTY_HERO_ADD),
           "in a FIELD the body's 0x0020 follows the roster row (the load's own "
           "order: roster, then bodies)",
           f"{[hex(o) for o in gf]}")
    body = stf["agents"].get(200)
    led.ok(body is not None and body.get("hero") == 6 and body.get("party_slot") == 0
           and body.get("pos") == (500.0 + authsrv.HERO_BODY_OFFSET[0], 500.0)
           and body.get("plane") == 0,
           "the body is agent 200, hero 6, formation slot 0, HERO_BODY_OFFSET from "
           "the player's position -- hero_body_create's placement",
           f"{ {k: body.get(k) for k in ('hero', 'party_slot', 'pos', 'plane')} if body else None}")
    # kick then add again: the body leaves through 0x0021 and comes back at 200.
    sk, sendk = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendk, stf, 0)
    led.ok(ops(sk)[0] == authsrv.GAME_SMSG_WORLD_REMOVE_AGENT and 200 not in stf["agents"],
           "the kick removes the body first (0x0021) -- the add's inverse")
    sr, sendr = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendr, stf, 0)
    led.ok(authsrv.GAME_SMSG_WORLD_CREATE_AGENT in ops(sr)
           and stf["agents"].get(200, {}).get("hero") == 6,
           "add again: the body is re-created at the SAME agent id 200 (a "
           "definition is per instance; the burrow probe proved the re-create)")
    # KNOWN-BAD for the field claim: a town sends no create.
    authsrv.EXPLORABLE = False
    stt = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}, "map_id": 449}
    st_, sendt = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendt, stt, 0)
    led.ok(authsrv.GAME_SMSG_WORLD_CREATE_AGENT not in ops(st_)
           and retail_load_order(ops(st_)),
           "KNOWN-BAD for the field arm: the same rig in a TOWN sends the roster "
           "batch and no create")
    authsrv.HERO_BODY = False

    # -- §5 the 0x0018 mask ---------------------------------------------------------
    authsrv.HERO_UNLOCK_MASK = True
    authsrv.HERO_IDS = [6]
    led.ok(authsrv.hero_unlock_mask() == [64],
           "hero 6 owned -> [64]: bit 6, the 2026-08 tapes' value (34 connections)")
    authsrv.HERO_IDS = [5, 6, 7]
    led.ok(authsrv.hero_unlock_mask() == [224],
           "heroes 5, 6, 7 owned -> [224]: the 20260913+ tapes' value")
    authsrv.HERO_IDS = [6, 35]
    led.ok(authsrv.hero_unlock_mask() == [64, 8],
           "an index >= 32 takes a second dword (bit 35 -> word 1 bit 3)")
    authsrv.HERO_IDS = []
    led.ok(authsrv.hero_unlock_mask() == [0xFFFFFFFF] * 8,
           "no hero authored -> OpenTyria's eight all-ones, verbatim (UPSTREAM; "
           "the no-hero rig is byte-identical)")
    authsrv.HERO_IDS = [6]
    authsrv.HERO_UNLOCK_MASK = False
    led.ok(authsrv.hero_unlock_mask() == [0xFFFFFFFF] * 8,
           "--no-hero-unlock-mask -> all-ones even with a hero authored (the revert)")
    authsrv.HERO_UNLOCK_MASK = True
    led.ok(authsrv.hero_unlock_mask() != [0xFFFFFFFF] * 8,
           "CONTROL: the flag is read -- back on, the mask is not all-ones")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    shutil.rmtree(base, ignore_errors=True)


# -- §6 source locks on authsrv.py ---------------------------------------------
def _func(tree, name):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _calls(node):
    return {c.func.id for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def dispatch_lock(tree, const, flag, handler):
    """arm_ok: the `opcode == const` arm calls `handler` only under `if flag:`
    and never in its else (test_herokick's lock, parameterised)."""
    handle = _func(tree, "handle")
    for n in ast.walk(handle):
        if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
            continue
        t = n.test
        if not (isinstance(t.left, ast.Name) and t.left.id == "opcode"
                and len(t.comparators) == 1
                and isinstance(t.comparators[0], ast.Name)
                and t.comparators[0].id == const):
            continue
        inner = [s for s in n.body if isinstance(s, ast.If)]
        direct = any(handler in _calls(s) for s in n.body if not isinstance(s, ast.If))
        return (len(inner) == 1 and not direct
                and isinstance(inner[0].test, ast.Name) and inner[0].test.id == flag
                and any(handler in _calls(s) for s in inner[0].body)
                and not any(handler in _calls(s) for s in inner[0].orelse))
    return False


def main_flags(tree, attrs):
    main = _func(tree, "main")
    flags = {}
    for n in ast.walk(main):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                and n.test.attr in attrs):
            for s in n.body:
                if (isinstance(s, ast.Assign) and len(s.targets) == 1
                        and isinstance(s.targets[0], ast.Name)
                        and isinstance(s.value, ast.Constant)):
                    flags[n.test.attr] = (s.targets[0].id, s.value.value)
    return flags


def party_size_counts_heroes(tree):
    """In _handle_request_players, the assignment to `_party_size` calls
    party_hero_slots (the SANDBOX-N2 follow-up: the load under-counted)."""
    fn = _func(tree, "_handle_request_players")
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "_party_size"):
            return "party_hero_slots" in _calls(n.value)
    return False


with open(SRC_PATH, encoding="utf-8") as f:
    SRC = f.read()
TREE = ast.parse(SRC)

led.ok(dispatch_lock(TREE, "GAME_CMSG_HERO_ADD", "HERO_ADD_ENABLED", "handle_hero_add"),
       "LOCK: the GAME_CMSG_HERO_ADD arm calls handle_hero_add ONLY under "
       "`if HERO_ADD_ENABLED:` (and never in its else)")
led.ok(dispatch_lock(TREE, "GAME_CMSG_HERO_KICK", "HERO_KICK_ENABLED", "handle_hero_kick"),
       "CONTROL: the same lock still holds for the kick's arm")
led.ok(SRC.count("if HERO_ADD_ENABLED:") == 1,
       "the add arm's condition appears once (so the mutations below hit it)")
mut1 = ast.parse(SRC.replace("if HERO_ADD_ENABLED:", "if True:", 1))
led.ok(not dispatch_lock(mut1, "GAME_CMSG_HERO_ADD", "HERO_ADD_ENABLED", "handle_hero_add"),
       "KNOWN-BAD: an arm that ignores HERO_ADD_ENABLED fails the lock")
mut2 = ast.parse(SRC.replace(
    "if HERO_ADD_ENABLED:\n                            handle_hero_add(values, send, state, conn_id)",
    "handle_hero_add(values, send, state, conn_id)\n                        if HERO_ADD_ENABLED:\n                            pass", 1))
led.ok(not dispatch_lock(mut2, "GAME_CMSG_HERO_ADD", "HERO_ADD_ENABLED", "handle_hero_add"),
       "KNOWN-BAD: calling the handler BEFORE the flag check fails it too")

flags = main_flags(TREE, ("no_hero_add", "no_hero_unlock_mask"))
led.ok(flags == {"no_hero_add": ("HERO_ADD_ENABLED", False),
                 "no_hero_unlock_mask": ("HERO_UNLOCK_MASK", False)},
       "LOCK: main() wires --no-hero-add -> HERO_ADD_ENABLED=False and "
       "--no-hero-unlock-mask -> HERO_UNLOCK_MASK=False", f"got {flags}")
led.ok(_saved["HERO_ADD_ENABLED"] is True and _saved["HERO_UNLOCK_MASK"] is True,
       "both are ON by default -- the flags are the revert arms (see the "
       "defaults' comments for why the RECONSTRUCTION ships on)")

# One body implementation, two callers.
load_fn = _func(TREE, "_handle_request_players")
add_fn = _func(TREE, "handle_hero_add")
led.ok("hero_body_create" in _calls(load_fn) and "hero_body_create" in _calls(add_fn)
       and _func(TREE, "hero_body_create") is not None
       and "create_agent_world" not in _calls(add_fn)
       and SRC.count("create_agent_world(") >= 2,
       "LOCK: hero_body_create exists and is called from BOTH the load path and "
       "the add; the add calls create_agent_world only through it")
led.ok(SRC.count('f"hero body (hero {_hid})", conn_id=conn_id)') == 1,
       "and the body's label appears once -- the load loop's body moved, not copied")

led.ok(party_size_counts_heroes(TREE),
       "LOCK: the load path's _party_size counts party_hero_slots (retail's load "
       "sent [68, 2] with one hero; this site sent 1 + henchman)")
led.ok("_party_size = 1 if HENCHMAN is None else 2" not in SRC,
       "and the under-counting literal is gone")
mut3 = ast.parse(SRC.replace(
    "+ len(party_hero_slots(state)))\n    send(GAME_SMSG_PLAYER_PARTY_SIZE,",
    "+ 0)\n    send(GAME_SMSG_PLAYER_PARTY_SIZE,", 1))
led.ok(not party_size_counts_heroes(mut3),
       "KNOWN-BAD: a _party_size that drops the hero count fails the lock")

led.ok(SRC.count("send(GAME_SMSG_PVP_UPDATE_UNLOCKED_HEROES,") == 1
       and "[[0xFFFFFFFF] * 8]" not in SRC
       and "_hum = hero_unlock_mask()" in SRC,
       "LOCK: 0x0018 has ONE sender, it calls hero_unlock_mask(), and the "
       "all-ones literal is gone from the send site (a second sender of unlock "
       "state once wiped a library -- the 0x001D comment)")

sys.exit(led.verdict())
