"""When a maximum health goes on the wire (0x009F 42) -- a held item's moves the
player's (RANGERPRE-S11, MAXHP-2), and an NPC's rides the player's first landed
word, not its create (RANGERPRE-S10, MAXHP-1). studies/presearing/RANGERPRE.md.

    python toolkit/authsrv/test_maxdeclare.py

WHAT THIS PINS, and what each part rests on (§1-§3 MAXHP-2, §4-§6 MAXHP-1):

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
    before it declares 100 or 120 (8 of 8) -- the reader reads either value;
    RANGERPRE-S21 (critic C10) pins those three by connection and wire t
    (LATER_LOADS: :53753 994.024, :53756 998.208, :59427 1217.429).
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
    test_skillloadorder's drives do, and declares a skip without them. THE
    LATER LOAD (RANGERPRE-S21, same rows): set 0 = the bow, the 564 shield
    equipped IN GAME under --persist, then a new connection -- under
    --hand-restore the next load's 42 is the equip's base+15 (retail's 135
    after the equip), with the arm off (KNOWN-BAD, the default) it is base.
  * §3 SOURCE: the bonus term in player_max_health only; held_max_moved in
    _item_moves_commit after _item_hands_mirror with the bonus read before the
    batch, and in select_weapon_set after the energy pair with the bonus read
    before the hands change; HELD_HEALTH True at module level, and
    --no-held-health parsing and flipping it in main().
  * §4 RETAIL, MAXHP-1 (OBSERVED, the same capture, plus the MANTID tape
    20260913T210901 for Empathy): 526 NPC-class create intervals, 12 carry a
    42, and each is the message immediately before the observer's first 0x00A3
    on the body at the same wire t -- 0 declared-unhit, 0 hit-undeclared (the
    exact 12 are pinned); :53756's moved maximum (64 -> 52) re-declared at
    1117.382 right before [16, 30, 9, f]; Empathy's first word on each of four
    agents carries [42, a, 25], its 4 later words none.
  * §5 OURS, MAXHP-1, bare machine through the real functions: the create burst
    withholds an NPC's 42 and marks the tracker stale; the player's first landed
    hit declares it immediately before the word, after the chain state (0x005C),
    and the hit after none; a blocked hit sends none and the next landed one
    declares; a Deep Wound (64 -> 52) re-declares 52 on the next hit (RANGERPRE-S1's
    value); a re-create (the burrow's) re-declares; a party hit (hurt_agent_row)
    declares nothing; the scythe's extra hit declares right before its word;
    Empathy (armour_ignoring_damage's default) declares on the player's first word
    only and never on a hero's; a party body keeps its create-time 42 (PARTYMAX, a
    follow-up); the deferred refill's 42 marks the tracker; the KNOWN-BAD arm
    (--npc-max-at-create) puts the 42 back in the burst, the first hit then
    sends none, and every Empathy word declares whatever its source. The
    preparation splash's neighbour (INFERRED, no retail witness) needs the
    overlay's skill 431 rows and declares a skip without them.
  * §6 SOURCE: declare_body_max_on_hit called exactly once in each of the four
    player damage sites and nowhere else, the hit's and the scythe's AFTER
    everything else they send and right before the word, no inline
    PROP_HEALTH_MAX left in either; create_agent_world's gate;
    NPC_MAX_AT_CREATE False at module level, --npc-max-at-create parsing and
    flipping it in main().

Floor from the green run (the ledger line).
"""
import ast
import contextlib
import inspect
import io
import os
import random
import sys
import threading
import time

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

led = checks.Ledger("maximum-health declarations (RANGERPRE-S10, S11)", floor=44)   # 2026-09-29: 20 from the first green run with the vault (§1 5, §2 11, §3 4); RANGERPRE-S21 +2 (critic C10: §1's LATER_LOADS pin, §2's LATER LOAD drive, both vault-gated); 2026-09-30 RANGERPRE-S10 (MAXHP-1) +22 (§4 4, §5 14, §6 4); merged on rangerpre 2026-09-30 (S10 + S21): 44 with the vault, 31 bare (both measured) -- a bare machine (RURIK_VAULT at an empty directory) runs fewer and declares §1, §4, the load checks and the splash skipped, under the floor on purpose -- the retail fixtures count inside it, so a missing capture is RED

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
# RANGERPRE-S21 (critic C10): the loads after the equip, (connection port, the own
# load 42's wire t), each declaring 135 with the shield restored into the hand.
LATER_LOADS = {("53753", 994.024), ("53756", 998.208), ("59427", 1217.429)}
TICK = authsrv.GAME_SMSG_WORLD_SIMULATION_TICK                 # 0x001E closes a batch
SHIELD_564 = RETAIL_SHIELD_WORDS[1]                            # 564 arg 15

_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "ITEM_MOVES_ENABLED", "EXPLORABLE", "OUTPOST", "EQUIP_WEAPON",
           "EQUIP_ARMOUR", "EQUIP_COSTUME", "EQUIP_COSTUME_HEAD", "WEAPON_SETS",
           "PLAYER_SWING_DAMAGE", "WEAPON_ATTACK_SPEED", "ATTACK_INTERVAL",
           "HELD_HEALTH", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "HAND_RESTORE",
           "NPC_MAX_AT_CREATE", "DEEP_WOUND", "blocks")}
_saved_random = random.random
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


def quiet(fn, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kw)


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
        led.skip("1. retail's shield equip", f"no live captures: {exc} -- 6 checks")
        return None
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
        return {}
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
    # RANGERPRE-S21 (critic C10): the three later loads by connection and wire t --
    # what §2's LATER LOAD drive reproduces under --hand-restore.
    pinned = {(g.split("_")[1].split("-")[0], t) for g, t, _x in after}
    led.ok(pinned == LATER_LOADS,
           "the three later loads declaring 135 are :53753 t=994.024, :53756 t=998.208 and "
           ":59427 t=1217.429 -- the loads after the in-game equip, which §2's LATER LOAD drive "
           "reproduces under --hand-restore",
           f"{sorted(pinned)}")
    return decoded


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
                 "(clientscan/attribpoints.py --emit-content) -- 2 checks")
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

    # THE LATER LOAD (RANGERPRE-S21, critic C10): the 564 shield EQUIPPED IN GAME under
    # --persist, then a new connection -- retail's :56064 equip then :53753 / :53756 /
    # :59427 (LATER_LOADS, §1). Only --hand-restore puts the shield back in the hand at
    # the dress, so only it carries the equip's maximum into the next load's 42.
    later = {arm: later_load(arm) for arm in (True, False)}
    led.ok(later[True] == ([int(base) + 15], [int(base) + 15])
           and later[False] == ([int(base) + 15], [int(base)]),
           "THE LATER LOAD: the in-game equip declares base+15 (S11) and, under --hand-restore, "
           "the NEXT load's 42 is base+15 too -- retail's 135 on the three loads after the equip "
           "(:53753 994.024, :53756 998.208, :59427 1217.429); KNOWN-BAD (the default, the "
           "hands at set 0's record): the next load drops back to base", f"{later}")


def later_load(arm):
    """(the equip's own 42s, the next load's own 42s) for set 0 = the bow and set 1 =
    sword + the 564 shield: c2s 0x0030 [sword] then [shield] in a field under
    --persist (a temporary store the load's find_character is pointed at), then a new
    connection's item half of the dress (item_layout_begin, item_hands_at_dress) and
    the real _handle_request_players."""
    import shutil
    import tempfile
    import charstore
    base_dir = tempfile.mkdtemp(prefix="maxdeclare-hands-")
    uuid = "6" * 32
    store = charstore.Store.open("hands@rurik.invalid", base=base_dir)
    store.ensure_character(uuid, "Hands", "ee" * 37)
    saved_find = authsrv.charstore.find_character
    authsrv.charstore.find_character = lambda u, base=None: (store, store.character_by_uuid(u))
    lead_id, off_id = authsrv.WEAPON_SET_ITEM_IDS[0]
    try:
        authsrv.agents.item_template = template_with_564
        authsrv.HELD_HEALTH, authsrv.HAND_RESTORE = True, arm
        authsrv.PERSIST, authsrv.ITEM_MOVES_ENABLED = True, True
        authsrv.EQUIP_WEAPON, authsrv.EQUIP_ARMOUR = True, True
        authsrv.EQUIP_COSTUME, authsrv.EQUIP_COSTUME_HEAD = False, False
        authsrv.OUTPOST, authsrv.EXPLORABLE = False, True
        authsrv.WEAPON_SETS = [{"lead": "starter_bow", "off": None}, None, None, None]
        authsrv.agents.PLAYER_OFFHAND = None
        authsrv.SET_ITEMS_OVERRIDE.clear()
        authsrv.WEAPON_SET_BACKPACK_SLOTS.clear()
        authsrv.SPAWN_PROFESSION, authsrv.SPAWN_SECONDARY = 1, 0
        del authsrv.SKILLBAR[:]
        authsrv.SKILLBAR.extend(_saved_bar)
        eq_sent, eq_send = recorder()
        load_sent, load_send = recorder()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.apply_party_character({"player_weapon": "starter_bow"})
            authsrv.configure_weapon_sets(["1=starter_sword+starter_shield"])
            st = {"agents": {}, "char_uuid": uuid, "map_id": 160}
            authsrv.item_layout_begin(st, 0)
            authsrv.player_pools(st)
            authsrv.handle_equip_item([authsrv.GAME_CMSG_EQUIP_ITEM, lead_id], eq_send, st, 0)
            authsrv.handle_equip_item([authsrv.GAME_CMSG_EQUIP_ITEM, off_id], eq_send, st, 0)
            st2 = {"agents": {}, "char_uuid": uuid, "map_id": 146}
            authsrv.item_layout_begin(st2, 0)
            authsrv.item_hands_at_dress(st2, 0)
            authsrv._handle_request_players(load_send, st2, 0, threading.Event(), FakeRec())
        own = [P42, P]
        return ([v[2] for op, v in eq_sent if op == INT and v[:2] == own],
                [v[2] for op, v in load_sent if op == INT and v[:2] == own and v[2] != 1])
    finally:
        authsrv.charstore.find_character = saved_find
        authsrv.agents.item_template = _real_template
        shutil.rmtree(base_dir, ignore_errors=True)


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


# ---- §4 retail: an NPC's maximum (MAXHP-1) ---------------------------------------------

FLT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET    # 0x00A3
assert FLT == 0x00A3
NPC_INTERVALS = 526
# OBSERVED (connection port, agent, wire t, max): every NPC-class 42 on the tape, each
# the message immediately before the observer's first 0x00A3 on the body, same t.
RETAIL_NPC_DECLARED = sorted([
    ("53756", 22, 1046.303, 64), ("53756", 28, 1089.022, 64), ("53756", 30, 1113.41, 64),
    ("53756", 27, 1132.708, 64), ("55934", 43, 261.606, 8), ("55934", 45, 336.622, 80),
    ("55934", 46, 380.837, 4), ("55934", 48, 414.32, 64), ("55934", 61, 455.167, 64),
    ("55934", 215, 516.989, 96), ("55934", 161, 565.03, 80), ("56025", 56, 838.445, 112)])
MANTID_TAPE, MANTID_CONN = "20260913T210901", "_60877-"
EMPATHY_AGENTS = (18, 24, 26, 32)


def npc_intervals(s2c, me):
    """{(agent, create index): (first 42 (j, t, max) | None, observer's first 0x00A3
    (j, t) | None)} over the NPC-class creates (0x0020 v[2] >> 28 == 2)."""
    cur, tag, first42, firsthit = {}, {}, {}, {}
    for j, (t, op, v) in enumerate(s2c):
        if op == 0x0020:
            cur[v[1]] = (v[1], j)
            tag[(v[1], j)] = v[2] >> 28
        elif op == INT and len(v) > 3 and v[1] == P42 and v[2] in cur:
            first42.setdefault(cur[v[2]], (j, t, v[3]))
        elif op == FLT and len(v) > 4 and v[3] == me and v[2] in cur:
            firsthit.setdefault(cur[v[2]], (j, t))
    return {k: (first42.get(k), firsthit.get(k)) for k, g in tag.items() if g == 2}


def section_npc_retail(decoded):
    print(f"\n4. retail: an NPC's maximum rides the player's first landed word, {TAPE}")
    if decoded is None:
        led.skip("4. retail's NPC maximum", "no live captures (section 1's skip) -- 4 checks")
        return
    import adrenjoin
    import livewire
    import vaultpath
    total, declared, unhit, undeclared = 0, [], [], []
    per = {}
    for g, (_c, merged, _ok) in decoded.items():
        s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
        me = adrenjoin.whose_agent(s2c)
        port = g.split("_")[1].split("-")[0] if "_" in g else g
        per[port] = (s2c, me)
        for (aid, _j), (a42, hit) in npc_intervals(s2c, me).items():
            total += 1
            if a42 and hit and hit[0] == a42[0] + 1 and hit[1] == a42[1]:
                declared.append((port, aid, round(a42[1], 3), a42[2]))
            elif a42 and not hit:
                unhit.append((port, aid))
            elif hit and not a42:
                undeclared.append((port, aid))
            elif a42:
                unhit.append((port, aid, "not adjacent"))
    led.ok(len(decoded) == TAPE_CONNS and all(m is not None for _s, m in per.values())
           and total == NPC_INTERVALS,
           f"POSITIVE CONTROL: all {TAPE_CONNS} connections name their observer, and they "
           f"hold {NPC_INTERVALS} NPC-class create intervals (0x0020 tag 2)",
           f"{len(decoded)} connections, observers {[m for _s, m in per.values()]}, {total}")
    led.ok(sorted(declared) == RETAIL_NPC_DECLARED and not unhit and not undeclared,
           "OBSERVED: exactly 12 of the 526 carry a 0x009F [42, agent, max], each the message "
           "IMMEDIATELY before the observer's FIRST 0x00A3 on the body at the same wire t; 0 "
           "declared on a body the observer never hit, 0 hit bodies left undeclared -- no "
           "create carries one", f"{sorted(declared)} / unhit {unhit} / undeclared {undeclared}")
    s2c, me = per.get("53756", ([], None))
    at = [j for j, (t, op, v) in enumerate(s2c) if op == INT and list(v[1:4]) == [P42, 30, 52]]
    ok_dw = (len(at) == 1 and round(s2c[at[0]][0], 3) == 1117.382
             and s2c[at[0] + 1][1] == FLT and list(s2c[at[0] + 1][2][1:4]) == [16, 30, me]
             and s2c[at[0] + 1][0] == s2c[at[0]][0])
    led.ok(ok_dw and me == 9,
           "OBSERVED: a MOVED maximum is declared on the next hit -- :53756 agent 30's 64 -> 52 "
           "(Deep Wound, RANGERPRE-S1) is [42, 30, 52] at 1117.382, immediately before "
           "[16, 30, 9, f] at the same t",
           f"{[(round(s2c[j][0], 3), s2c[j + 1][1], s2c[j + 1][2][1:4]) for j in at]}")
    try:
        vaultpath.require_dir("captures", "live", MANTID_TAPE, why="MAXHP-1 Empathy")
        cap = vaultpath.vault_path("captures", "live", MANTID_TAPE)
        g = [x for x in livewire.connections(cap) if MANTID_CONN in x]
        _c, merged, ok = livewire.decode_conn(cap, g[0])
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        led.ok(False, f"the MANTID tape {MANTID_TAPE} :60877 decodes (the live root is "
               "present, so its absence is a FAIL)", str(exc))
        return
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    me = adrenjoin.whose_agent(s2c)
    firsts, laters = [], []
    for aid in EMPATHY_AGENTS:
        idx = [j for j, (t, op, v) in enumerate(s2c)
               if op == FLT and list(v[1:4]) == [55, aid, me]]
        for n, j in enumerate(idx):
            prev = s2c[j - 1]
            has42 = (prev[1] == INT and list(prev[2][1:3]) == [P42, aid]
                     and prev[0] == s2c[j][0])
            (firsts if n == 0 else laters).append((aid, round(s2c[j][0], 3), has42,
                                                  prev[2][3] if has42 else None))
    led.ok(ok and me == 9 and len(firsts) == 4 and all(h and x == 25 for _a, _t, h, x in firsts)
           and len(laters) == 4 and not any(h for _a, _t, h, _x in laters)
           and [(a, t) for a, t, _h, _x in laters if a == 24] == [(24, 697.028), (24, 698.779)],
           "OBSERVED (MANTID :60877): Empathy's FIRST [55, agent, 9] on each of agents 18, 24, "
           "26, 32 carries [42, agent, 25] right before it; its 4 later words (agent 24 at "
           "697.028 and 698.779, 26, 18) carry none -- 'declare before every word' is refuted",
           f"firsts {firsts}, laters {laters}")


# ---- §5 ours: an NPC's maximum (MAXHP-1) -----------------------------------------------

HERO = 30


def npc_entry(max_health=100.0, allegiance=None, pos=(0.0, 0.0)):
    """A hostile the way spawn_enemy hands one to create_agent_world (test_burrow's shape)."""
    return {"pos": pos, "plane": 0, "health": max_health, "max_health": max_health,
            "dead": False, "name": "maxhp", "npc": authsrv.agents.HATCHER, "definition": 3,
            "allegiance": allegiance or authsrv.agents.ALLEGIANCE_HOSTILE,
            "attack_speed": authsrv.agents.ATTACK_SPEED["axe"], "effects": 0,
            "armor_rating": 60, "last_hit": 0.0}


def world():
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0}
    authsrv.effect_table(st)
    quiet(authsrv.player_pools, st)
    return st


def spawn(st, aid=11, **kw):
    burst, send = recorder()
    entry = npc_entry(**kw)
    quiet(authsrv.create_agent_world, send, st, aid, entry, "hostile", 0)
    return burst, entry


def maxes(sent, aid=None):
    return [v for op, v in sent if op == INT and v[0] == P42 and (aid is None or v[1] == aid)]


def hit(st, aid=11, **kw):
    st["agents"][aid]["last_hit"] = 0.0
    sent, send = recorder()
    quiet(authsrv.hit_enemy, send, st, aid, 0, **kw)
    return sent


def right_before_word(sent, aid, value):
    """The 42 [42, aid, value] is the message immediately before the player's first word
    on `aid`, and there is exactly one 42 on `aid` in the batch."""
    words = [i for i, (op, v) in enumerate(sent) if op == FLT and v[1] == aid and v[2] == P]
    m = [i for i, (op, v) in enumerate(sent) if op == INT and v[:2] == [P42, aid]]
    return (len(m) == 1 and bool(words) and m[0] == words[0] - 1
            and sent[m[0]][1] == [P42, aid, int(value)])


def section_npc_ours():
    print("\n5. ours: the create withholds an NPC's maximum; the player's first word declares it")
    authsrv.PLAYER_SWING_DAMAGE = (5, 5)
    authsrv.NPC_MAX_AT_CREATE = False
    random.random = lambda: 1.0                    # no critical, no block, no Blind miss
    # the create
    st = world()
    burst, entry = spawn(st)
    ops = [op for op, _v in burst]
    led.ok(authsrv.GAME_SMSG_WORLD_CREATE_AGENT in ops and not maxes(burst)
           and entry.get("max_declared_on_hit", "absent") is None,
           "create_agent_world (a hostile): the burst carries its 0x0020 and NO [42, agent, "
           "max] -- 0 of 526 retail creates did -- and the tracker is marked stale (None)",
           f"{[hex(o) for o in ops]}, tracker {entry.get('max_declared_on_hit', 'absent')}")
    # the first landed hit, and the one after
    s1 = hit(st)
    s2 = hit(st)
    led.ok(right_before_word(s1, 11, 100) and not maxes(s2)
           and st["agents"][11]["max_declared_on_hit"] == 100.0,
           "the player's FIRST landed hit declares [42, 11, 100] as the message immediately "
           "before its [16, 11, player, f] (12 of 12); the second hit carries none",
           f"{s1} / {maxes(s2)}")
    # the chain state goes ahead of the 42
    st = world()
    spawn(st)
    sent, send = recorder()
    st["agents"][11]["last_hit"] = 0.0
    quiet(authsrv.hit_enemy, send, st, 11, 0, before_damage=lambda: send(0x005C, [P, 11, 1]))
    i5c = [i for i, (op, _v) in enumerate(sent) if op == 0x005C]
    led.ok(i5c and right_before_word(sent, 11, 100)
           and sent[i5c[0] + 1] == (INT, [P42, 11, 100]),
           "ORDER: a chain hit's 0x005C goes AHEAD of the 42 and the 42 stays the message "
           "right before the word (:62557 122.012: E5, 9F 46, 5C, 9F 42, A3 -- 122 of 122 "
           "batches)", f"{sent}")
    # a block declares nothing; the next landed hit does
    st = world()
    spawn(st)
    authsrv.blocks = lambda state, agent_id: True
    sb = hit(st)
    stale = st["agents"][11].get("max_declared_on_hit", "absent")
    authsrv.blocks = _saved["blocks"]
    sl = hit(st)
    fails = [v for op, v in sb if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
             and v[0] == authsrv.agents.GV_ATTACK_FAIL]
    led.ok(not maxes(sb) and fails == [[authsrv.agents.GV_ATTACK_FAIL, 11, P,
                                        authsrv.agents.ATTACK_FAIL_BLOCK]]
           and not any(op == FLT for op, _v in sb) and stale is None,
           "a BLOCKED hit sends its fail word [38, 11, player, 0], no damage word and no 42 "
           "(a miss draws none: 0 of 7 retail), and the tracker stays stale",
           f"{sb}, tracker {stale}")
    led.ok(right_before_word(sl, 11, 100),
           "...and the next LANDED hit declares [42, 11, 100] right before its word",
           f"{maxes(sl)}")
    # a moved maximum: Deep Wound 64 -> 52 (RANGERPRE-S1's floor)
    authsrv.DEEP_WOUND = True
    st = world()
    spawn(st, max_health=64.0)
    h1 = hit(st)
    dw, dsend = recorder()
    quiet(authsrv.deep_wound_open, dsend, st, 11, 0)
    h2 = hit(st)
    h3 = hit(st)
    led.ok(right_before_word(h1, 11, 64) and not maxes(dw) and right_before_word(h2, 11, 52)
           and not maxes(h3),
           "a MOVED maximum: declared 64 on the first hit; the Deep Wound's batch carries no "
           "42; the next hit declares 52 right before its word (retail :53756 1117.382) and "
           "the one after none", f"{maxes(h1)} {maxes(dw)} {maxes(h2)} {maxes(h3)}")
    # a re-create (the burrow's) re-declares
    st = world()
    spawn(st)
    hit(st)
    rm, rsend = recorder()
    back = quiet(authsrv.remove_agent, rsend, st, 11, "burrowing")
    quiet(authsrv.create_agent_world, rsend, st, 11, back, "emerging from burrow", 0, False)
    rh = hit(st)
    led.ok(not maxes(rm) and right_before_word(rh, 11, 100),
           "a RE-CREATE resets it: remove, re-create the same entry (no 42 in either), and the "
           "next hit declares again (retail n = 2, the burrower 0x5A2 and agent 80)",
           f"{maxes(rm)} / {maxes(rh)}")
    # a party member's hit declares nothing; the player's then does
    st = world()
    spawn(st)
    st["agents"][HERO] = dict(npc_entry(allegiance=authsrv.agents.ALLEGIANCE_PLAYER),
                              pos=(10.0, 0.0))
    ph, psend = recorder()
    quiet(authsrv.hurt_agent_row, psend, st, HERO, 11, 5.0, authsrv._f32(-0.05), 0, "a hero's hit")
    pl = hit(st)
    led.ok([op for op, _v in ph].count(FLT) == 1 and not maxes(ph)
           and right_before_word(pl, 11, 100),
           "a PARTY member's hit on an undeclared body carries no 42 (0 of 2,458 retail); the "
           "player's first hit after it declares", f"{ph} / {maxes(pl)}")
    # the scythe's extra hit -- a CRITICAL one, its energy (a sentinel here) ahead of the 42
    st = world()
    spawn(st, aid=12, pos=(20.0, 0.0))
    sc, ssend = recorder()
    _gain = authsrv.critical_energy_gain
    authsrv.critical_energy_gain = lambda send, state, conn_id: send("CRIT", [])
    random.random = lambda: 0.0                    # the roll crits
    try:
        quiet(authsrv.scythe_extra_hit, ssend, st, 12, 0, 0, 0.0, 1.0, time.time(), "extra")
    finally:
        authsrv.critical_energy_gain = _gain
        random.random = lambda: 1.0
    i_crit = [i for i, (op, _v) in enumerate(sc) if op == "CRIT"]
    led.ok(right_before_word(sc, 12, 100) and i_crit
           and sc[i_crit[0] + 1] == (INT, [P42, 12, 100])
           and any(op == FLT and v[0] == authsrv.agents.GV_CRITICAL for op, v in sc),
           "the scythe's EXTRA hit on an undeclared body, a critical: its energy, THEN [42, 12, "
           "100], then its [17] word -- the 42 right before the word (until today it went "
           "ahead of the critical's energy)", f"{sc}")
    # Empathy: armour_ignoring_damage's default, the player's first word only; a hero's none
    st = world()
    spawn(st)
    spawn(st, aid=12, pos=(20.0, 0.0))
    e1, e1s = recorder()
    quiet(authsrv.armour_ignoring_damage, e1s, st, 11, P, 10.0, 0, "hex 26 punishes the attack")
    e2, e2s = recorder()
    quiet(authsrv.armour_ignoring_damage, e2s, st, 11, P, 10.0, 0, "hex 26 punishes the attack")
    eh, ehs = recorder()
    quiet(authsrv.armour_ignoring_damage, ehs, st, 12, HERO, 10.0, 0, "a hero's hex punishes")
    led.ok(right_before_word(e1, 11, 100) and not maxes(e2) and not maxes(eh)
           and [op for op, _v in eh].count(FLT) == 1,
           "EMPATHY (armour_ignoring_damage's default): the player's first [55] word on a body "
           "carries [42, agent, max] right before it, the second none (MANTID agent 24); a "
           "HERO-cast word none", f"{e1} / {e2} / {eh}")
    # a party body keeps its create-time 42 (PARTYMAX, a follow-up)
    st = world()
    pb, pentry = spawn(st, aid=HERO, allegiance=authsrv.agents.ALLEGIANCE_PLAYER)
    led.ok(maxes(pb) == [[P42, HERO, 100]] and "max_declared_on_hit" not in pentry,
           "a PARTY body ('play') keeps its create-time [42, agent, max] -- retail declares none "
           "of 509, but a hero's rides its character block (PARTYMAX, a follow-up)", f"{maxes(pb)}")
    # the deferred refill's 42 marks the tracker
    st = world()
    spawn(st)
    st["agents"][11]["refill_due_at"] = 1.0
    rf, rfs = recorder()
    quiet(authsrv.agent_refill_due, rfs, st, 0)
    ra = hit(st)
    led.ok(maxes(rf) == [[P42, 11, 100]] and not maxes(ra),
           "a revive's refill declares the maximum and marks it told -- the next hit repeats "
           "nothing", f"{maxes(rf)} / {maxes(ra)}")
    # KNOWN-BAD ARM: --npc-max-at-create
    authsrv.NPC_MAX_AT_CREATE = True
    try:
        st = world()
        kb, kentry = spawn(st)
        spawn(st, aid=12, pos=(20.0, 0.0))
        k1 = hit(st)
        i20 = [i for i, (op, _v) in enumerate(kb) if op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT]
        ka, kas = recorder()
        quiet(authsrv.armour_ignoring_damage, kas, st, 12, HERO, 10.0, 0, "a hero's hex")
        quiet(authsrv.armour_ignoring_damage, kas, st, 12, HERO, 10.0, 0, "a hero's hex")
        led.ok(i20 and kb[i20[0] + 1] == (INT, [P42, 11, 100]) and not maxes(k1)
               and "max_declared_on_hit" not in kentry and maxes(ka) == [[P42, 12, 100]] * 2,
               "KNOWN-BAD ARM (--npc-max-at-create, every run before today): the 42 right after "
               "the 0x0020, the first hit then carries none, and every armour-ignoring word "
               "declares whatever its source",
               f"{[hex(op) for op, _v in kb]} / {maxes(kb)} / {maxes(k1)} / {maxes(ka)}")
    finally:
        authsrv.NPC_MAX_AT_CREATE = False
    # the splash (INFERRED): needs the overlay's skill 431 rows
    try:
        radius = float(authsrv.agents.WORLD.get("skills", "431").get("aoe_range", 0.0))
    except Exception:                                          # noqa: BLE001
        radius = 0.0
    if radius <= 0.0 or not authsrv.skill_effect_row(431).get("adjacent_damage"):
        led.skip("5. the preparation splash's neighbour", "no skills row for 431 in the "
                 "content (the vault overlay) -- 1 check")
        return
    st = world()
    st["agents"][10] = dict(npc_entry(), pos=(0.0, 0.0))      # the target, already declared
    spawn(st, aid=11, pos=(50.0, 0.0))
    sp, sps = recorder()
    reached = quiet(authsrv.preparation_splash, sps, st, 431, 10.0, 10, 0, 12, None)
    led.ok(reached == [11] and right_before_word(sp, 11, 100),
           "the preparation SPLASH onto an undeclared neighbour declares its maximum right "
           "before its word (INFERRED: 0 Ignite Arrows in the corpus)", f"{reached} {sp}")


# ---- §6 source (MAXHP-1) ---------------------------------------------------------------

def section_npc_source():
    print("\n6. source: one declaration helper, four call sites, the gate, the flag")
    src = open(authsrv.__file__, encoding="utf-8").read()
    sites = {fn: inspect.getsource(getattr(authsrv, fn)) for fn in
             ("hit_enemy", "scythe_extra_hit", "preparation_splash", "armour_ignoring_damage")}
    counts = {fn: s.count("declare_body_max_on_hit(") for fn, s in sites.items()}
    led.ok(src.count("declare_body_max_on_hit(") == 5 and set(counts.values()) == {1},
           "SOURCE LOCK: declare_body_max_on_hit is defined once and called exactly once in each "
           "of hit_enemy, scythe_extra_hit, preparation_splash and armour_ignoring_damage -- "
           "and nowhere else", f"{src.count('declare_body_max_on_hit(')} in the file, {counts}")
    he, sc, sp = sites["hit_enemy"], sites["scythe_extra_hit"], sites["preparation_splash"]
    h_call = he.find("declare_body_max_on_hit(")
    h_order = [he.find("before_damage()"), he.find("critical_energy_gain(send, state, conn_id)"),
               he.find("if prep_visual is not None:                          # WEAPONS-W2e"),
               h_call, he.find("[prop, target_id, PLAYER_AGENT_ID, frac]")]
    s_call = sc.find("declare_body_max_on_hit(")
    s_order = [sc.find("critical_energy_gain(send, state, conn_id)"), s_call,
               sc.find("send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET")]
    p_call = sp.find("declare_body_max_on_hit(")
    p_order = [sp.find('f"(the splash)")'), p_call,
               sp.find("send(GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET")]
    led.ok(-1 not in h_order and h_order == sorted(h_order)
           and -1 not in s_order and s_order == sorted(s_order)
           and -1 not in p_order and p_order == sorted(p_order)
           and "agents.PROP_HEALTH_MAX" not in he and "agents.PROP_HEALTH_MAX" not in sc,
           "SOURCE LOCK: the call is the last thing before the word -- hit_enemy after "
           "before_damage, the critical's energy and the preparation's visual; the scythe after "
           "its critical's energy; the splash after its visual -- and no inline PROP_HEALTH_MAX "
           "is left in hit_enemy or scythe_extra_hit",
           f"hit {h_order}, scythe {s_order}, splash {p_order}")
    caw = inspect.getsource(authsrv.create_agent_world)
    aid = inspect.getsource(authsrv.armour_ignoring_damage)
    led.ok("_max_at_create = NPC_MAX_AT_CREATE or entry.get(\"allegiance\") == "
           "agents.ALLEGIANCE_PLAYER" in caw
           and 'entry["max_declared_on_hit"] = None' in caw
           and "declare_max=None" in aid
           and 'declare_max = "always" if NPC_MAX_AT_CREATE else "stale"' in aid,
           "SOURCE LOCK: create_agent_world sends the 42 only under the arm or for a party body "
           "and marks every other create stale; armour_ignoring_damage's default resolves to "
           "'stale' ('always' only under the arm)")
    mod = ast.parse(src)
    top = [n.value.value for n in mod.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "NPC_MAX_AT_CREATE" for t in n.targets)
           and isinstance(n.value, ast.Constant)]
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    a0, a1 = ap.parse_args([]), ap.parse_args(["--npc-max-at-create"])
    main_fn = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    flips = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
                and node.test.attr == "npc_max_at_create"):
            flips += [s for s in node.body if isinstance(s, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "NPC_MAX_AT_CREATE"
                              for t in s.targets)
                      and isinstance(s.value, ast.Constant) and s.value.value is True]
            flips += [s for s in node.body if isinstance(s, ast.Global)
                      and "NPC_MAX_AT_CREATE" in s.names]
    led.ok(top == [False] and a0.npc_max_at_create is False and a1.npc_max_at_create is True
           and len(flips) == 2,
           "NPC_MAX_AT_CREATE defaults False at module level; --npc-max-at-create parses "
           "(default off) and main() sets the global True under it", f"{top}, {len(flips)} of 2")


try:
    _decoded = section_retail()
    section_ours()
    section_source()
    section_npc_retail(_decoded)
    section_npc_ours()
    section_npc_source()
finally:
    random.random = _saved_random
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
