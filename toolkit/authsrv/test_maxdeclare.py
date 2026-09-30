"""A held item's maximum health moves the player's 0x009F 42 -- RANGERPRE-S11
(MAXHP-2), studies/presearing/RANGERPRE.md.

    python toolkit/authsrv/test_maxdeclare.py

WHAT THIS PINS, and what each part rests on:

  * §1 RETAIL (OBSERVED, vault-gated; capture 20260929T150923, the Reforged
    pre-Searing Ranger, 11 game connections -- the live root absent is a
    declared skip, present without this capture a FAIL): on :56064 the shield
    equip (c2s 0x0030 [696]) is answered by exactly RETAIL_EQUIP_BATCH at
    t=932.526 -- 0x014B, 0x006F, then 0x009F [42, 9, 135], the 42 LAST; item
    696's 0x0161 carries RETAIL_SHIELD_WORDS and the SERVER'S OWN reader
    (authsrv.item_word, combatmath.HEALTH_MODIFIER) reads 564 arg 15 off them,
    the exact rise of the connection's 42 (120 -> 135). NEGATIVE CONTROL: the
    sword the same connection equipped at 930.405 (697, no 564) drew no 42.
    And every load after the equip declares 135 (3 of 3) while every load
    before it declares 100 or 120 (8 of 8) -- the reader reads either value.
  * §2 OURS (bare machine: the tracked starter_sword / starter_shield rows,
    the shield given retail's 564 word by a patched item_template for the
    drive): the bonus is in player_max_health and NOT player_full_max_health
    (land_swing scales the enemy's blow from that); held_max_moved's one 42
    and its signed health delta; the REAL equip path (handle_equip_item in a
    field) sends retail's three in retail's order; the plain shield, and the
    564 shield under --no-held-health (KNOWN-BAD: every run before today),
    send the planned two and no 42; the drag back out declares the lower
    maximum (RECONSTRUCTION: no retail unequip of a 564 item); a set switch
    carries the 42 after its energy pair (INFERRED) in the batch it returns,
    and the plain shield's switch none; the load's 42 (the real
    _handle_request_players burst after the dress) is base + 15 with the 564
    shield in set 0 -- that part needs the overlay's attribute rows, as
    test_skillloadorder's drives do, and declares a skip without them.
  * §3 SOURCE: the bonus term in player_max_health only; held_max_moved in
    _item_moves_commit after _item_hands_mirror with the bonus read before the
    batch, and in select_weapon_set after the energy pair with the bonus read
    before the hands change; HELD_HEALTH True at module level, and
    --no-held-health parsing and flipping it in main().

MAXHP-1 (an NPC's maximum declared on the player's first landed hit) is a
separate step and is not pinned here. Floor from the green run (the ledger line).
"""
import ast
import contextlib
import inspect
import io
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import itemstore                                             # noqa: E402
import authsrv                                               # noqa: E402
import combatmath                                            # noqa: E402

led = checks.Ledger("a held item's maximum health (RANGERPRE-S11)", floor=20)   # 2026-09-29: 20 from the first green run with the vault (§1 5, §2 11, §3 4); a bare machine (RURIK_VAULT at an empty directory) runs 14 and declares §1 and the load's check skipped, under the floor on purpose -- the retail fixture counts inside it, so a missing capture is RED

INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT             # 0x009F
CHG = authsrv.GAME_SMSG_ITEM_CHANGE_LOCATION                  # 0x014B
VIS = authsrv.GAME_SMSG_AGENT_UPDATE_VISUAL_EQUIPMENT_SLOT    # 0x006F
P42 = authsrv.agents.PROP_HEALTH_MAX
P = authsrv.PLAYER_AGENT_ID
assert (INT, CHG, VIS, P42) == (0x009F, 0x014B, 0x006F, 42)
assert combatmath.HEALTH_MODIFIER == 564

TAPE = "20260929T150923"
TAPE_CONNS = 11
EQUIP_CONN = "_56064-"
# OBSERVED, :56064 (§1 pins each against the tape).
RETAIL_EQUIP_T = 932.526
RETAIL_EQUIP_BATCH = [(0x014B, [2, 696, 5, 1]), (0x006F, [9, 1, 696]),
                      (0x009F, [42, 9, 135])]
RETAIL_SWORD_BATCH = [(0x0152, [2, 698, 697]), (0x006F, [9, 0, 697])]   # t=930.441
RETAIL_SHIELD_WORDS = [0x21A83205, 0x23480F00, 0xA3C80400]     # item 696
RETAIL_SWORD_WORDS = [0x24B80200, 0xA4880705]                  # item 697
TICK = authsrv.GAME_SMSG_WORLD_SIMULATION_TICK                 # 0x001E closes a batch
SHIELD_564 = RETAIL_SHIELD_WORDS[1]                            # 564 arg 15

_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "ITEM_MOVES_ENABLED", "EXPLORABLE", "OUTPOST", "EQUIP_WEAPON",
           "EQUIP_ARMOUR", "EQUIP_COSTUME", "EQUIP_COSTUME_HEAD", "WEAPON_SETS",
           "PLAYER_SWING_DAMAGE", "WEAPON_ATTACK_SPEED", "ATTACK_INTERVAL",
           "HELD_HEALTH", "SPAWN_PROFESSION", "SPAWN_SECONDARY")}
_saved_off, _saved_wpn = authsrv.agents.PLAYER_OFFHAND, authsrv.agents.PLAYER_WEAPON
_saved_slots, _saved_over = dict(authsrv.WEAPON_SET_BACKPACK_SLOTS), dict(authsrv.SET_ITEMS_OVERRIDE)
_saved_bar = list(authsrv.SKILLBAR)
_real_template = authsrv.agents.item_template


def template_with_564(key):
    """starter_shield with retail's 564 word appended; every other row as is."""
    row = _real_template(key)
    if key == "starter_shield":
        row = dict(row, modifiers=list(row.get("modifiers", ())) + [SHIELD_564])
    return row


def recorder():
    sent = []

    def send(op, vals, label=None, **_k):
        sent.append((op, list(vals)))
    return sent, send


def fresh(*, with_564, held=True, set0_off=None):
    """A real field layout: set 0 = starter_sword (+ `set0_off`), set 1 =
    starter_sword + starter_shield, the shield carrying 564 when `with_564`."""
    authsrv.agents.item_template = template_with_564 if with_564 else _real_template
    authsrv.HELD_HEALTH = held
    authsrv.PERSIST, authsrv.ITEM_MOVES_ENABLED = False, True
    authsrv.EQUIP_WEAPON, authsrv.EQUIP_ARMOUR = True, True
    authsrv.EQUIP_COSTUME, authsrv.EQUIP_COSTUME_HEAD = False, False
    authsrv.OUTPOST, authsrv.EXPLORABLE = False, True
    authsrv.WEAPON_SETS = [{"lead": "starter_sword", "off": set0_off}, None, None, None]
    authsrv.agents.PLAYER_OFFHAND = None
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.configure_weapon_sets(["1=starter_sword+starter_shield"])
        st = {"agents": {}, "char_uuid": "5" * 32, "map_id": 145}
        items = authsrv.item_layout_begin(st, 0)
        authsrv.player_pools(st)
    sid = next(i for i, r in items.items()
               if r.get("key") == "starter_shield" and r["bag"] == authsrv.BACKPACK_BAG_ID) \
        if set0_off is None else None
    return st, items, sid


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args)


# ---- §1 retail ----------------------------------------------------------------------

def load_max(s2c, me):
    """The value of the own load 42: the last own [42, me, X] at the wire t of
    the first own 42 (the load sends [42, me, 1] earlier in the same batch)."""
    own = [(t, v[3]) for t, op, v in s2c if op == INT and v[1] == P42 and v[2] == me]
    if not own:
        return None, None
    t0 = own[0][0]
    return t0, [x for t, x in own if t == t0][-1]


def section_retail():
    print(f"\n1. retail: the shield equip, capture {TAPE}")
    import vaultpath
    try:
        vaultpath.require_dir("captures", "live", why="the shield-equip witness")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        # require_dir raises SystemExit on a bare machine (test_srclint's rule)
        led.skip("1. retail's shield equip", f"no live captures: {exc} -- 5 checks")
        return
    import livewire
    import adrenjoin
    cap = vaultpath.vault_path("captures", "live", TAPE)
    files = livewire.connections(cap) if os.path.isdir(cap) else []
    decoded = {g: livewire.decode_conn(cap, g) for g in files}
    ok_all = all(ok for _c, _m, ok in decoded.values())
    led.ok(len(files) == TAPE_CONNS and ok_all
           and livewire.capture_origin(cap)[0] == "live",
           f"the live root is present, so {TAPE} must be in it: {TAPE_CONNS} game "
           f"connections, origin live, every one decoding closed (a FAIL, never a skip)",
           f"{len(files)} files, ok {[ok for _c, _m, ok in decoded.values()]}")
    if not files or not ok_all:
        return
    wit = [g for g in files if EQUIP_CONN in g]
    merged = decoded[wit[0]][1] if len(wit) == 1 else []
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    me = adrenjoin.whose_agent(s2c) if s2c else None

    def answer(item):
        """(t, [(op, values)]) of the s2c batch answering c2s 0x0030 [item]: the
        wire t of the first item move naming it (0x014B / 0x0152) after the
        request, every s2c at that t, the closing WORLD_SIMULATION_TICK aside
        (the first s2c after a request can be a movement tick's batch -- the
        sword's is, at 930.421)."""
        i = next((k for k, (_t, d, op, v) in enumerate(merged)
                  if d == "c2s" and op == 0x0030 and v[1] == item), None)
        if i is None:
            return None, None
        t0 = next((t for t, d, op, v in merged[i + 1:] if d == "s2c"
                   and op in (0x014B, 0x0152) and item in v[1:]), None)
        return t0, [(op, list(v[1:])) for t, d, op, v in merged[i + 1:]
                    if d == "s2c" and t == t0 and op != TICK]

    def words(item):
        return next(([w[0] for w in v[-1]] for _t, op, v in s2c
                     if op == 0x0161 and v[1] == item), None)

    t_eq, batch = answer(696)
    led.ok(me == 9 and t_eq is not None and round(t_eq, 3) == RETAIL_EQUIP_T
           and batch == RETAIL_EQUIP_BATCH,
           f"OBSERVED: the shield equip (c2s 0x0030 [696]) is answered at "
           f"t={RETAIL_EQUIP_T} by exactly 0x014B [2, 696, 5, 1], 0x006F [9, 1, 696], "
           f"0x009F [42, 9, 135] -- the observer's maximum, the batch's LAST message "
           f"(its closing 0x001E tick aside)",
           f"me {me}, t {t_eq}, {batch}")
    before = [v[3] for t, op, v in s2c if op == INT and v[1] == P42 and v[2] == me
              and t_eq is not None and t < t_eq and v[3] != 1]
    w696 = words(696)
    got = authsrv.item_word({"modifiers": w696 or []}, combatmath.HEALTH_MODIFIER)
    led.ok(w696 == RETAIL_SHIELD_WORDS and got == (15, 0) and before
           and 135 - before[-1] == got[0],
           "item 696's 0x0161 carries 0x23480F00 and the server's own reader "
           "(item_word, HEALTH_MODIFIER) reads 564 arg 15 off it -- the exact rise of the "
           "connection's declared maximum (120 -> 135)",
           f"words {[hex(w) for w in w696 or []]}, read {got}, 42s before {before}")
    t_sw, b_sw = answer(697)
    w697 = words(697)
    led.ok(t_sw is not None and round(t_sw, 3) == 930.441 and b_sw == RETAIL_SWORD_BATCH
           and w697 == RETAIL_SWORD_WORDS
           and authsrv.item_word({"modifiers": w697}, combatmath.HEALTH_MODIFIER) is None,
           "NEGATIVE CONTROL: the sword the same connection equipped at 930.405 (697, "
           "no 564) was answered at 930.441 by exactly 0x0152 [2, 698, 697], 0x006F "
           "[9, 0, 697] -- no 42",
           f"t {t_sw}, {b_sw}, words {[hex(w) for w in w697 or []]}")
    after, earlier = [], []
    for g, (_c, m, _ok) in decoded.items():
        s = [(t, op, v) for t, d, op, v in m if d == "s2c"]
        t0, x = load_max(s, adrenjoin.whose_agent(s))
        if t0 is not None:
            (after if t0 > RETAIL_EQUIP_T else earlier).append((g[5:22], round(t0, 3), x))
    led.ok(len(after) == 3 and all(x == 135 for _g, _t, x in after)
           and len(earlier) == 8 and all(x in (100, 120) for _g, _t, x in earlier),
           "every load after the equip declares 135 (3 of 3: :53753, :53756, :59427) while "
           "every load before it declares 100 or 120 (8 of 8) -- the maximum the shield "
           "held at load carries, and the same reader reads the other values",
           f"after {after}, before {earlier}")


# ---- §2 ours --------------------------------------------------------------------------

def section_ours():
    print("\n2. ours: the bonus, the move, the equip, the switch, the load")
    base = authsrv.player_full_max_health({})
    st, _items, _sid = fresh(with_564=True)
    full_bare = authsrv.player_full_max_health(st)
    authsrv.agents.PLAYER_OFFHAND = template_with_564("starter_shield")
    led.ok(authsrv.held_health_bonus(st) == 15
           and authsrv.player_max_health(st) == full_bare + 15
           and authsrv.player_full_max_health(st) == full_bare == base,
           "a held 564 arg 15 is +15 on player_max_health and NOTHING on "
           "player_full_max_health (land_swing's blow is scaled from that one)",
           f"bonus {authsrv.held_health_bonus(st)}, max {authsrv.player_max_health(st)}, "
           f"full {authsrv.player_full_max_health(st)} vs {full_bare}")
    authsrv.agents.PLAYER_OFFHAND = _real_template("starter_shield")
    led.ok(authsrv.held_health_bonus(st) == 0 and authsrv.player_max_health(st) == full_bare,
           "VACUITY: the content starter_shield carries no 564 -- held_health_bonus is 0")

    # held_max_moved: one 42, the signed delta on a seeded book, a fresh book seeded once
    authsrv.agents.PLAYER_OFFHAND = template_with_564("starter_shield")
    st["player_health"] = 60.0
    sent, send = recorder()
    r1 = authsrv.held_max_moved(send, st, 15, "probe")
    sent0, send0 = recorder()
    r0 = authsrv.held_max_moved(send0, st, 0, "probe")
    led.ok(r1 is True and sent == [(INT, [P42, P, int(base) + 15])]
           and st["player_health"] == 75.0 and st["player_max_declared"] == int(base) + 15
           and r0 is False and sent0 == [],
           "held_max_moved(+15): exactly [0x009F [42, player, base+15]], current health "
           "60 -> 75 (the client's own health += delta), the tracker seeded; a zero delta "
           "sends nothing", f"{sent} {st['player_health']} {r0} {sent0}")
    st2 = {"agents": {}}
    sent2, send2 = recorder()
    authsrv.held_max_moved(send2, st2, 15, "probe")
    led.ok(st2["player_health"] == base + 15 and sent2 == [(INT, [P42, P, int(base) + 15])],
           "...and a book that did not exist is seeded at the NEW maximum, not given the "
           "delta twice", f"{st2.get('player_health')} {sent2}")

    # THE EQUIP: the real handler, a field, the 564 shield from the backpack
    st, items, sid = fresh(with_564=True)
    sent, send = recorder()
    quiet(authsrv.handle_equip_item, [authsrv.GAME_CMSG_EQUIP_ITEM, sid], send, st, 0)
    eq = authsrv.EQUIPPED_BAG_ID
    led.ok(sent == [(CHG, [1, sid, eq, 1]), (VIS, [P, 1, sid]), (INT, [P42, P, int(base) + 15])]
           and st["player_health"] == base + 15 and authsrv.player_max_health(st) == base + 15,
           "THE EQUIP (handle_equip_item, field): 0x014B, 0x006F, then 0x009F [42, player, "
           "base+15] -- retail's three in retail's order, the 42 last (:56064 t=932.526); "
           "health follows the maximum", f"{sent}, health {st['player_health']}")
    # ...and back out: the lower maximum (RECONSTRUCTION: no retail unequip of a 564 item)
    sent.clear()
    quiet(authsrv.handle_item_move, [authsrv.GAME_CMSG_ITEM_MOVE, 1, authsrv.BACKPACK_BAG_ID, 9],
          send, st, 0)
    led.ok(sent == [(CHG, [1, sid, authsrv.BACKPACK_BAG_ID, 9]), (VIS, [P, 1, 0]),
                    (INT, [P42, P, int(base)])]
           and st["player_health"] == base and authsrv.held_health_bonus(st) == 0,
           "the shield dragged back out: 0x014B, 0x006F [player, 1, 0], then 0x009F [42, "
           "player, base] and health -15 (RECONSTRUCTION, the signed delta)",
           f"{sent}, health {st['player_health']}")
    st, items, sid = fresh(with_564=False)
    sent, send = recorder()
    quiet(authsrv.handle_equip_item, [authsrv.GAME_CMSG_EQUIP_ITEM, sid], send, st, 0)
    led.ok(sent == [(CHG, [1, sid, eq, 1]), (VIS, [P, 1, sid])]
           and authsrv.player_max_health(st) == base,
           "NEGATIVE CONTROL: the content starter_shield (no 564) equips with exactly the "
           "planned two and no 42 -- retail's sword, and its 24 hand changes without 564",
           f"{sent}")
    st, items, sid = fresh(with_564=True, held=False)
    sent, send = recorder()
    quiet(authsrv.handle_equip_item, [authsrv.GAME_CMSG_EQUIP_ITEM, sid], send, st, 0)
    led.ok(sent == [(CHG, [1, sid, eq, 1]), (VIS, [P, 1, sid])]
           and authsrv.player_max_health(st) == base and st["player_health"] == base,
           "KNOWN-BAD ARM (--no-held-health): the 564 shield equips with the two and no 42, "
           "the maximum unmoved -- every run before today, one message short of retail's",
           f"{sent}")

    # THE SWITCH: set 1 holds the 564 shield (INFERRED position: after the energy pair)
    st, items, sid = fresh(with_564=True)
    sent, send = recorder()
    out = quiet(authsrv.select_weapon_set, send, st, 1, 0)
    back_sent, back_send = recorder()
    back = quiet(authsrv.select_weapon_set, back_send, st, 0, 0)
    led.ok(sent and sent[-1] == (INT, [P42, P, int(base) + 15]) and out[-1] == sent[-1]
           and sum(1 for op, v in sent if op == INT and v[0] == P42) == 1
           and back_sent and back_sent[-1] == (INT, [P42, P, int(base)]) and back[-1] == back_sent[-1]
           and st["player_health"] == base,
           "SET SWITCH 0 -> 1 onto the 564 shield ends with 0x009F [42, player, base+15], in "
           "the batch select_weapon_set returns; 1 -> 0 ends with [42, player, base]",
           f"{sent[-2:]} / {back_sent[-2:]}")
    st, items, sid = fresh(with_564=False)
    sent, send = recorder()
    quiet(authsrv.select_weapon_set, send, st, 1, 0)
    led.ok(sent and not any(op == INT and v[0] == P42 for op, v in sent),
           "NEGATIVE CONTROL: the same switch onto the plain shield sends no 42 (retail's "
           "15 switches, none moving a 564 item, none drew one)", f"{sent}")

    # THE LOAD: the real burst after the dress, set 0 = sword + 564 shield
    if not authsrv.agents.WORLD.rows("attribute"):
        led.skip("2. the load's 42", "no attribute cost rows in the content "
                 "(clientscan/attribpoints.py --emit-content) -- 1 check")
        return
    got = {}
    for with_564 in (True, False):
        st, _items, _sid = fresh(with_564=with_564, set0_off="starter_shield")
        authsrv.SPAWN_PROFESSION, authsrv.SPAWN_SECONDARY = 1, 0
        del authsrv.SKILLBAR[:]
        authsrv.SKILLBAR.extend(_saved_bar)
        sent, send = recorder()
        quiet(authsrv._handle_request_players, send, st, 0, threading.Event(), FakeRec())
        got[with_564] = [v[2] for op, v in sent if op == INT and v[:2] == [P42, P] and v[2] != 1]
    led.ok(got[True] == [int(base) + 15] and got[False] == [int(base)],
           "THE LOAD (_handle_request_players after the dress): the player's 42 is base+15 "
           "with the 564 shield held in set 0, base with the plain one -- the later loads' "
           "135 on retail", f"{got}")


class FakeRec:
    def event(self, kind, **kw):
        pass


# ---- §3 source ------------------------------------------------------------------------

def section_source():
    print("\n3. source: the term, the two calls, the flag, the CLI")
    pmh = inspect.getsource(authsrv.player_max_health)
    pfh = inspect.getsource(authsrv.player_full_max_health)
    led.ok("held_health_bonus(" in pmh and "held_health_bonus(" not in pfh,
           "SOURCE LOCK: the bonus is a term of player_max_health and NOT of "
           "player_full_max_health")
    imc = inspect.getsource(authsrv._item_moves_commit)
    i_read = imc.find("_held_hp = held_health_bonus(state)")
    i_loop = imc.find("for op, vals, label in out:")
    i_mirror = imc.find("_item_hands_mirror(")
    i_move = imc.find("held_max_moved(send, state, held_health_bonus(state) - _held_hp")
    led.ok(imc.count("held_max_moved(") == 1 and -1 < i_read < i_loop < i_mirror < i_move,
           "SOURCE LOCK: _item_moves_commit reads the bonus before the batch goes out and "
           "calls held_max_moved once, AFTER _item_hands_mirror (the 42 last)",
           f"read {i_read}, loop {i_loop}, mirror {i_mirror}, move {i_move}")
    sws = inspect.getsource(authsrv.select_weapon_set)
    j_read = sws.find("_held_hp = held_health_bonus(state)")
    j_clear = sws.find("agents.PLAYER_OFFHAND = None")
    j_regen = sws.find("energy regeneration, rescaled to the new pool [WEAPONS-W9]")
    j_move = sws.find("held_max_moved(_send, state, held_health_bonus(state) - _held_hp")
    led.ok(sws.count("held_max_moved(") == 1 and -1 < j_read < j_clear < j_regen < j_move,
           "SOURCE LOCK: select_weapon_set reads the bonus before the hands change and "
           "calls held_max_moved once, through _send (so the returned batch carries it), "
           "after the energy pair", f"read {j_read}, clear {j_clear}, regen {j_regen}, move {j_move}")
    mod = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    top = [n.value.value for n in mod.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "HELD_HEALTH" for t in n.targets)
           and isinstance(n.value, ast.Constant)]
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    a0, a1 = ap.parse_args([]), ap.parse_args(["--no-held-health"])
    main_fn = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    flips = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
                and node.test.attr == "no_held_health"):
            flips += [s for s in node.body if isinstance(s, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "HELD_HEALTH"
                              for t in s.targets)
                      and isinstance(s.value, ast.Constant) and s.value.value is False]
            flips += [s for s in node.body if isinstance(s, ast.Global)
                      and "HELD_HEALTH" in s.names]
    led.ok(top == [True] and a0.no_held_health is False and a1.no_held_health is True
           and len(flips) == 2,
           "HELD_HEALTH defaults True at module level; --no-held-health parses (default "
           "off) and main() sets the global False under it", f"{top}, {len(flips)} of 2")


try:
    section_retail()
    section_ours()
    section_source()
finally:
    authsrv.agents.item_template = _real_template
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    authsrv.agents.PLAYER_OFFHAND, authsrv.agents.PLAYER_WEAPON = _saved_off, _saved_wpn
    authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
    authsrv.WEAPON_SET_BACKPACK_SLOTS.update(_saved_slots)
    authsrv.SET_ITEMS_OVERRIDE.clear()
    authsrv.SET_ITEMS_OVERRIDE.update(_saved_over)
    del authsrv.SKILLBAR[:]
    authsrv.SKILLBAR.extend(_saved_bar)

sys.exit(led.verdict())
