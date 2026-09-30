"""The heroes' inventory container: retail's PLACE and retail's FIELD 2 --
HEROINV (studies/pvpui/FINDINGS.md 35).

    python toolkit/authsrv/test_heroinvorder.py

THE DEFECT. Under --party (which sets --hero-bags) the client drew no backpack:
grey silhouettes in the bag row, no Backpack grid, a drag from a backpack cell
answered as a world click (c2s 0x003E). Our load sent 0x0144 [1, 0] (the
player), then 0x0144 [2, 0] (the heroes) and the hero's 0x013F, THEN the
backpack and the player's nine bags -- all in the REQUEST_ITEMS reply.

WHAT THIS PINS, and what each part rests on:

  * §1 RETAIL (OBSERVED, vault-gated). The four live connections with a hero
    IN THE PARTY (20260914T005758 :56011 :51659 :56881, 20260916T150306
    :62321): the player's 0x0144 [P, 0] is the first, its nine bags follow it;
    the hero's 0x0144 [H, 1] comes after all nine, after the connection's
    0x0073, IMMEDIATELY ahead of its own 0x013F [H, 2, 21, _, 9, 0], then the
    hero agent's 0x0037, then 0x0072 naming H -- 4 of 4. The two with an
    OWNED but unpartied hero (20260916T150306 :56865, and :50807 after the
    kick) carry 0x0073, no 0x0072 and ONE 0x0144. The two sets are each
    other's control: the same predicate says yes on one and no on the other.
  * §2 THE CLIENT MODEL (static, build 38797; no vault). 0x0144's insert
    0x84A060 writes the container to [itemctx+0xF8] -- the local inventory the
    inventory window reads -- when field 2 is 0 and ONLY then; last one wins.
    `local_key` replays a send list under that rule. It is a model of a static
    read, labelled as one: the KNOWN-BAD arm is that it retrodicts the
    observed failure (the legacy order leaves the HERO's key local).
  * §3 OURS: the REAL _handle_request_players under the commander rig
    (test_secondary's drive_load "retail" rig). One 0x0144 in the players
    burst, [2, 1], in retail's relative order; the legacy rig's lands ahead of
    every 0x0072; a load with no party hero declares nothing and marks the key
    absent, and the ADD then declares it first. KNOWN-BAD ARM:
    --hero-inv-legacy (HERO_INV_RETAIL False) puts none in the players burst,
    field 2 goes back to 0, and every order predicate above REJECTS it.
  * §4 SOURCE: the REQUEST_ITEMS arm's hero call sits under `if not
    HERO_INV_RETAIL:` only (mutation reddens it); that arm opens with the
    player's [1, INVENTORY_LOCAL]; _handle_request_players calls the
    declaration; the flag defaults True; --hero-inv-legacy parses and main()
    flips it.

The REQUEST_ITEMS reply is inline in handle()'s socket loop and cannot be
driven, so §3 composes the full load as the player's [1, 0] (§4 pins it as
that arm's first send), the legacy arm's pair when the flag says so, then the
driven players burst -- the client requests the items before the players, so
that is the wire order.
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
import authsrv                                               # noqa: E402

led = checks.Ledger("the heroes' inventory container: place and field 2 (HEROINV)",
                    floor=23)   # 2026-09-30: 23 from the first green run with the vault (§1 6, §2 2, §3 9, §4 6); with HERO_INV_RETAIL's default flipped to False the same run fails 9. a bare machine runs §2 + §4 (8), declares §1 / §3 skipped and reports the shortfall against this floor -- §3's load needs the overlay's attribute rows, as test_skillloadorder's does

INV_CREATE, BAG_CREATE, HERO_INFO, ATTR_POINTS, HERO_ACTIVATE = (
    0x0144, 0x013F, 0x0073, 0x0037, 0x0072)
assert authsrv.GAME_SMSG_ITEM_STREAM_CREATE == INV_CREATE
assert authsrv.GAME_SMSG_INVENTORY_CREATE_BAG == BAG_CREATE
assert authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTE_POINTS == ATTR_POINTS
# Retail's relative order of the hero's five, pinned against the tape in §1.
RETAIL_HERO_ORDER = [HERO_INFO, INV_CREATE, BAG_CREATE, ATTR_POINTS, HERO_ACTIVATE]
# The hero's bag as retail sends it, minus the two per-connection handles
# (inventory key, bag id): (type, model, slots, item).
RETAIL_HERO_BAG = (2, 21, 9, 0)

PARTY_HERO = {"20260914T005758": (":56011->", ":51659->", ":56881->"),
              "20260916T150306": (":62321->",)}
NO_PARTY_HERO = {"20260916T150306": (":56865->", ":50807->")}
UUID = "4" * 32
ADD = authsrv.GAME_CMSG_HERO_ADD


class FakeRec:
    def event(self, kind, **kw):
        pass


# -- §1 retail ---------------------------------------------------------------
def hero_container_row(msgs):
    """The retail predicate over one connection's decoded s2c [(t, op, v)]
    (v[0] is the header, fields from v[1]). Returns a dict of what it read,
    with ok True only when the hero's container is retail's shape and place."""
    ops = [op for _t, op, _v in msgs]
    creates = [i for i, op in enumerate(ops) if op == INV_CREATE]
    out = {"creates": [msgs[i][2][1:] for i in creates], "ok": False}
    if len(creates) != 2:
        return out
    p, h = creates
    P, pf = msgs[p][2][1], msgs[p][2][2]
    H, hf = msgs[h][2][1], msgs[h][2][2]
    # The player's bags up to the hero's container (a session may add a bag
    # later; "nine, all between the two 0x0144" is the claim).
    bags_p = [i for i, (_t, op, v) in enumerate(msgs[:h]) if op == BAG_CREATE and v[1] == P]
    nxt = msgs[h + 1] if h + 1 < len(msgs) else None
    acts = [(i, v) for i, (_t, op, v) in enumerate(msgs) if op == HERO_ACTIVATE]
    i73 = next((i for i, op in enumerate(ops) if op == HERO_INFO), None)
    act = acts[0] if len(acts) == 1 else None
    agent = act[1][2] if act else None
    i37 = next((i for i, (_t, op, v) in enumerate(msgs)
                if op == ATTR_POINTS and v[1] == agent), None)
    order = None
    if act and i73 is not None and i37 is not None:
        seq = sorted([(i73, HERO_INFO), (h, INV_CREATE), (h + 1, BAG_CREATE),
                      (i37, ATTR_POINTS), (act[0], HERO_ACTIVATE)])
        order = [op for _i, op in seq]
    out.update(player=(P, pf), hero=(H, hf), nbags=len(bags_p),
               bag=(tuple(nxt[2][2:4]) + tuple(nxt[2][5:7])) if nxt and nxt[1] == BAG_CREATE else None,
               order=order, act_key=act[1][3] if act else None)
    out["ok"] = (pf == 0 and hf == 1 and P != H and len(bags_p) == 9
                 and p < min(bags_p)
                 and nxt is not None and nxt[1] == BAG_CREATE and nxt[2][1] == H
                 and out["bag"] == RETAIL_HERO_BAG
                 and order == RETAIL_HERO_ORDER and out["act_key"] == H)
    return out


def section_retail():
    print("\n1. retail: the hero's container, where and how (OBSERVED)")
    import vaultpath
    try:
        vaultpath.require_dir("captures", "live", why="the hero-container witness")
    except (Exception, SystemExit) as exc:                     # noqa: BLE001
        led.skip("1. retail's hero container", f"no live captures: {exc} -- 5 checks")
        return
    import npcdefs
    import tape
    from codec import Codec
    codec = Codec()
    wanted = sorted(set(PARTY_HERO) | set(NO_PARTY_HERO))
    try:
        caps = npcdefs.live_captures(names=wanted)
    except SystemExit as exc:
        caps = []
        print(f"  live_captures refused: {exc}")
    decoded = {}
    for cap in caps:
        name = os.path.basename(cap)
        for row in tape.whole_channels(cap, []):
            conn = row["connection"]
            if not any(tag in conn for tag in PARTY_HERO.get(name, ())
                       + NO_PARTY_HERO.get(name, ())):
                continue
            info, events = tape.load_tape(cap, conn)
            msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            decoded[(name, conn)] = (info.get("origin"), msgs,
                                     receipt[2] is None and receipt[0] == receipt[1])
    n_want = sum(len(v) for v in PARTY_HERO.values()) + sum(
        len(v) for v in NO_PARTY_HERO.values())
    led.ok(len(decoded) == n_want
           and all(o == "live" and whole for o, _m, whole in decoded.values()),
           f"the live root is present, so both captures must be: {n_want} named "
           f"connections, origin live, every one decoding closed (a FAIL, never a skip)",
           f"{len(decoded)} found: {[(k[0], k[1][:22]) for k in decoded]}")
    if len(decoded) != n_want:
        return

    def rows(table):
        return {(n, c): hero_container_row(m) for (n, c), (_o, m, _w) in decoded.items()
                if any(tag in c for tag in table.get(n, ()))}

    party, bare = rows(PARTY_HERO), rows(NO_PARTY_HERO)
    good = [k for k, r in party.items() if r["ok"]]
    led.ok(len(party) == 4 and len(good) == 4,
           "PARTY HERO, 4 of 4: player's 0x0144 [P, 0] first with its nine bags "
           "after it, then the hero's 0x0144 [H, 1] after all nine, after the 0x0073, "
           "immediately ahead of its own 0x013F [H, 2, 21, _, 9, 0], then the hero "
           "agent's 0x0037, then 0x0072 naming H",
           "; ".join(f"{c[11:17]} P{r.get('player')} H{r.get('hero')} bags {r.get('nbags')} "
                     f"bag {r.get('bag')} order {[hex(o) for o in (r.get('order') or [])]}"
                     for (_n, c), r in party.items()))
    led.ok(all(r["order"] == RETAIL_HERO_ORDER for r in party.values()),
           "RETAIL_HERO_ORDER is the tape's: 0x0073, 0x0144, 0x013F, 0x0037, 0x0072 "
           "on all four")
    bare_msgs = {k: decoded[k][1] for k in bare}
    bare_ok = [k for k, m in bare_msgs.items()
               if any(op == HERO_INFO for _t, op, _v in m)
               and not any(op == HERO_ACTIVATE for _t, op, _v in m)
               and [v[1:] for _t, op, v in m if op == INV_CREATE][:1]
               and len([1 for _t, op, _v in m if op == INV_CREATE]) == 1
               and [v[2] for _t, op, v in m if op == INV_CREATE] == [0]]
    led.ok(len(bare) == 2 and len(bare_ok) == 2,
           "OWNED, NOT PARTIED, 2 of 2 (:56865, and :50807 after the kick): 0x0073 "
           "but no 0x0072, and ONE 0x0144 -- the player's [P, 0]; a hero's container "
           "belongs to a party hero",
           f"{[(c[11:17], [v[1:] for _t, op, v in bare_msgs[(n, c)] if op == INV_CREATE]) for n, c in bare]}")
    led.ok(not any(r["ok"] for r in bare.values()),
           "CONTROL: the party-hero predicate says NO on both of those -- it can "
           "answer either way, so 4 of 4 is the tape's and not the reader's")
    # A mutated connection: the hero's field 2 flipped to ours-before-the-fix.
    k0 = sorted(party)[0]
    m0 = [(t, op, list(v)) for t, op, v in decoded[k0][1]]
    h0 = [i for i, (_t, op, _v) in enumerate(m0) if op == INV_CREATE][1]
    m0[h0][2][2] = 0
    led.ok(not hero_container_row(m0)["ok"],
           "KNOWN-BAD: the same connection with the hero's field 2 set to 0 FAILS "
           "the predicate")


# -- §2 the client model -----------------------------------------------------
def local_key(sent):
    """[itemctx+0xF8] after a send list, under the static model of 0x84A060
    (38797): a 0x0144 with field 2 == 0 makes its container the local
    inventory, last one wins; a non-zero field 2 leaves the slot alone."""
    local = None
    for op, vals in sent:
        if op == INV_CREATE and vals[1] == 0:
            local = vals[0]
    return local


def section_model():
    print("\n2. the client model: which container the inventory window draws")
    led.ok(local_key([(INV_CREATE, [1, 0])]) == 1
           and local_key([(INV_CREATE, [1, 0]), (INV_CREATE, [2, 0])]) == 2
           and local_key([(INV_CREATE, [1, 0]), (INV_CREATE, [2, 1])]) == 1,
           "the model: [1, 0] alone -> 1; then [2, 0] -> 2 (last wins); then "
           "[2, 1] -> still 1 (a non-zero field 2 writes nothing)")
    led.ok((authsrv.INVENTORY_LOCAL, authsrv.INVENTORY_OTHER) == (0, 1),
           "INVENTORY_LOCAL, INVENTORY_OTHER are 0 and 1 -- retail's two values of "
           "field 2 (the player's, a hero's)")


# -- §3 ours -----------------------------------------------------------------
_saved = {k: getattr(authsrv, k) for k in
          ("PERSIST", "SPAWN_PROFESSION", "SPAWN_SECONDARY", "OUTPOST", "EXPLORABLE",
           "HERO", "HERO_IDS", "HERO_AGENT_ID", "HERO_ROWS", "HERO_BODY",
           "HERO_BODY_NPC", "HERO_ACTIVATE", "HERO_PIPELINE_FIRST", "HERO_CHAR",
           "HERO_INVENTORY", "HERO_BAGS", "HERO_RIG_RETAIL", "HERO_INV_RETAIL",
           "HERO_ACTIVATE_FIRST", "HERO_KICK_ENABLED", "PARTY_COMMANDS")}


def rig(*, retail_inv=None, retail_rig=True):
    """The commander rig. `retail_inv` None keeps the MODULE'S DEFAULT for
    HERO_INV_RETAIL, so the fix's checks drive what a session gets by not
    choosing -- flip the default and they redden; only the known-bad arm
    sets it (False)."""
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    for k, v in {"PERSIST": False, "SPAWN_PROFESSION": 1, "SPAWN_SECONDARY": 0,
                 "OUTPOST": True, "EXPLORABLE": False, "HERO": 6, "HERO_IDS": [6],
                 "HERO_AGENT_ID": 200,
                 "HERO_ROWS": {6: {"hero": 6, "body": "academy_monk", "profession": 3,
                                   "skills": [105, 1, 2]}},
                 "HERO_BODY": True, "HERO_BODY_NPC": "academy_monk",
                 "HERO_ACTIVATE": True, "HERO_PIPELINE_FIRST": retail_rig,
                 "HERO_CHAR": True, "HERO_INVENTORY": 2, "HERO_BAGS": True,
                 "HERO_RIG_RETAIL": retail_rig, "HERO_KICK_ENABLED": True}.items():
        setattr(authsrv, k, v)
    if retail_inv is not None:
        authsrv.HERO_INV_RETAIL = retail_inv


def drive_load(*, retail_inv=None, retail_rig=True, kicked=None):
    """The REAL players burst under the commander rig. [(op, vals)], state."""
    rig(retail_inv=retail_inv, retail_rig=retail_rig)
    st = {"agents": {}, "char_uuid": UUID, "map_id": 148}
    if kicked:
        st["kicked_heroes"] = set(kicked)
    sent = []
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv._handle_request_players(
            lambda op, vals, label=None: sent.append((op, list(vals))),
            st, 0, threading.Event(), FakeRec())
    return sent, st


def items_arm_hero_rows():
    """What the REQUEST_ITEMS arm's hero call sends, flag as currently set --
    the arm is inline in handle(), so the call itself is driven here and §4
    pins that it is the arm's only hero send and sits under the flag."""
    out = []
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.hero_inventory_declare(lambda op, vals, label=None: out.append((op, list(vals))),
                                       {}, "")
    return out


def full_load(retail_inv, players):
    """The wire order: the player's [1, 0] (the REQUEST_ITEMS arm's first
    send), the arm's hero pair when the flag sends one there, then the
    players burst. `retail_inv` as rig()."""
    rig(retail_inv=retail_inv)
    return ([(INV_CREATE, [1, authsrv.INVENTORY_LOCAL])]
            + ([] if authsrv.HERO_INV_RETAIL else items_arm_hero_rows()) + players)


def hero_order(sent, agent=200):
    """The relative order of the hero's five in our burst (each once), or None."""
    idx = {}
    for i, (op, v) in enumerate(sent):
        if op in (HERO_INFO, INV_CREATE, BAG_CREATE, HERO_ACTIVATE) or (
                op == ATTR_POINTS and v and v[0] == agent):
            if op in idx:
                return None
            idx[op] = i
    if len(idx) != 5:
        return None
    return [op for op, _i in sorted(idx.items(), key=lambda kv: kv[1])]


def section_ours():
    print("\n3. ours: the real players burst, the fix and the known-bad arm")
    if not authsrv.agents.WORLD.rows("attribute"):
        led.skip("3. our load burst", "no attribute cost rows in the content "
                 "(clientscan/attribpoints.py --emit-content) -- 9 checks")
        return
    on, st_on = drive_load()                    # the module's default
    creates = [(i, v) for i, (op, v) in enumerate(on) if op == INV_CREATE]
    led.ok(len(creates) == 1 and creates[0][1] == [2, 1],
           "commander rig: ONE 0x0144 in the players burst, [2, 1] -- the heroes' "
           "key with retail's field 2", f"{creates}")
    i44 = creates[0][0] if len(creates) == 1 else None
    led.ok(i44 is not None and i44 + 1 < len(on) and on[i44 + 1] == (
               BAG_CREATE, [2, authsrv.BAG_TYPE_EQUIPPED, authsrv.BAG_MODEL_EQUIPPED,
                            authsrv.EQUIPPED_BAG_ID, authsrv.EQUIPPED_SLOT_COUNT, 0])
           and (authsrv.BAG_TYPE_EQUIPPED, authsrv.BAG_MODEL_EQUIPPED,
                authsrv.EQUIPPED_SLOT_COUNT, 0) == RETAIL_HERO_BAG,
           "...immediately followed by the hero's 0x013F, retail's (type 2, model "
           "21, 9 slots, item 0)", f"{on[i44 + 1] if i44 is not None else None}")
    led.ok(hero_order(on) == RETAIL_HERO_ORDER,
           "...and the hero's five run in retail's order: 0x0073, 0x0144, 0x013F, "
           "0x0037 (hero agent 200), 0x0072",
           f"{[hex(o) for o in (hero_order(on) or [])]}")
    acts = [v for op, v in on if op == HERO_ACTIVATE]
    led.ok(acts and all(v[2] == 2 for v in acts) and st_on.get("hero_inv_destroyed") is False,
           "0x0072 names key 2, and the connection records the key as held",
           f"{acts}, destroyed={st_on.get('hero_inv_destroyed')}")
    led.ok(local_key(full_load(None, on)) == 1,
           "THE DEFECT, FIXED (§2's model over the full load): the player's key 1 "
           "stays the local inventory -- the window draws the player's bags")

    off, st_off = drive_load(retail_inv=False)
    full_off = full_load(False, off)
    led.ok(not any(op == INV_CREATE for op, _v in off)
           and [v for op, v in full_off if op == INV_CREATE] == [[1, 0], [2, 0]]
           and hero_order(off) is None and local_key(full_off) == 2,
           "KNOWN-BAD ARM (--hero-inv-legacy): no 0x0144 in the players burst, the "
           "REQUEST_ITEMS arm's [2, 0] right after the player's [1, 0], the "
           "retail-order predicate REJECTS it, and the model makes key 2 -- the "
           "hero's -- the local inventory: the observed no-backpack",
           f"{[v for op, v in full_off if op == INV_CREATE]}, local {local_key(full_off)}")

    leg, _st = drive_load(retail_rig=False)
    ops_leg = [op for op, _v in leg]
    c_leg = [v for op, v in leg if op == INV_CREATE]
    first_act = ops_leg.index(HERO_ACTIVATE) if HERO_ACTIVATE in ops_leg else None
    led.ok(c_leg == [[2, 1]] and first_act is not None
           and ops_leg.index(INV_CREATE) < first_act,
           "LEGACY RIG (--hero-rig-legacy, no 0x0073): the container is still [2, 1] "
           "and precedes every 0x0072", f"{c_leg}, 0x0144 at "
           f"{ops_leg.index(INV_CREATE) if INV_CREATE in ops_leg else None}, "
           f"first 0x0072 at {first_act}")

    kick, st_k = drive_load(kicked={6})
    led.ok(not any(op in (INV_CREATE, BAG_CREATE, HERO_ACTIVATE) for op, _v in kick)
           and any(op == HERO_INFO for op, _v in kick)
           and st_k.get("hero_inv_destroyed") is True,
           "NO HERO IN THE PARTY (hero 6 kicked, as :50807): 0x0073 goes out, no "
           "container, no 0x0072, and the key is marked absent")
    sent_add = []
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_hero_add([ADD, 6], lambda op, vals, label=None:
                                sent_add.append((op, list(vals))), st_k, 0)
    led.ok(sent_add[:2] and sent_add[0] == (INV_CREATE, [2, 1])
           and sent_add[1][0] == BAG_CREATE
           and any(op == HERO_ACTIVATE and v[2] == 2 for op, v in sent_add)
           and st_k.get("hero_inv_destroyed") is False,
           "...and the ADD then declares [2, 1] + 0x013F FIRST, ahead of the 0x0072 "
           "that names it (ItCliApi:488 otherwise)",
           f"{[(hex(op), v) for op, v in sent_add[:3]]}")


# -- §4 source ---------------------------------------------------------------
def _func(tree, name):
    return next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == name), None)


def _calls_to(fn, name):
    """[guard] for each call to `name` under fn: 'not flag' when an enclosing
    `if not HERO_INV_RETAIL:` holds it, else None."""
    out = []

    def walk(node, guard):
        for child in ast.iter_child_nodes(node):
            g = guard
            if isinstance(node, ast.If) and child in node.body:
                t = node.test
                g = ("not flag" if isinstance(t, ast.UnaryOp)
                     and isinstance(t.op, ast.Not) and isinstance(t.operand, ast.Name)
                     and t.operand.id == "HERO_INV_RETAIL" else guard)
            if (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id == name):
                out.append(g)
            walk(child, g)
    walk(fn, None)
    return out


def items_arm_lock(tree):
    """(hero calls in handle() and their guards, the arm's player send ok)."""
    fn = _func(tree, "handle")
    guards = _calls_to(fn, "hero_inventory_declare") if fn else []
    player = False
    for c in ast.walk(fn) if fn else ():
        if (isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "send"
                and len(c.args) >= 2 and isinstance(c.args[0], ast.Name)
                and c.args[0].id == "GAME_SMSG_ITEM_STREAM_CREATE"
                and isinstance(c.args[1], ast.List) and len(c.args[1].elts) == 2
                and isinstance(c.args[1].elts[0], ast.Constant)
                and c.args[1].elts[0].value == 1
                and isinstance(c.args[1].elts[1], ast.Name)
                and c.args[1].elts[1].id == "INVENTORY_LOCAL"):
            player = True
    return guards, player


def section_source():
    print("\n4. source: the two sites, the flag, the CLI")
    src = open(authsrv.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    guards, player = items_arm_lock(tree)
    led.ok(guards == ["not flag"] and player,
           "handle()'s REQUEST_ITEMS arm opens with the player's send(ITEM_STREAM_"
           "CREATE, [1, INVENTORY_LOCAL]) and calls hero_inventory_declare exactly "
           "once, under `if not HERO_INV_RETAIL:` (the revert arm only)",
           f"guards {guards}, player send {player}")
    old = ("                        if not HERO_INV_RETAIL:\n"
           "                            hero_inventory_declare(send, state,\n")
    led.ok(src.count(old) == 1, "the guarded call has the expected text (so the "
           "mutation below hits it)")
    mut = src.replace(old, "                        if True:\n"
                           "                            hero_inventory_declare(send, state,\n", 1)
    led.ok(items_arm_lock(ast.parse(mut))[0] == [None],
           "KNOWN-BAD: the call un-guarded (the pre-fix site) fails the lock")
    players = ast.parse(inspect.getsource(authsrv._handle_request_players).lstrip())
    led.ok(len(_calls_to(players, "hero_inventory_declare")) == 1,
           "_handle_request_players calls hero_inventory_declare once (the retail site)")
    top = [n.value.value for n in tree.body if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "HERO_INV_RETAIL" for t in n.targets)
           and isinstance(n.value, ast.Constant)]
    led.ok(top == [True] and _saved["HERO_INV_RETAIL"] is True,
           "HERO_INV_RETAIL defaults True at module level", f"{top}")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    a0, a1 = ap.parse_args([]), ap.parse_args(["--hero-inv-legacy"])
    main_fn = _func(tree, "main")
    flips = []
    for node in ast.walk(main_fn):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
                and node.test.attr == "hero_inv_legacy"):
            flips += [s for s in node.body if isinstance(s, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "HERO_INV_RETAIL"
                              for t in s.targets)
                      and isinstance(s.value, ast.Constant) and s.value.value is False]
            flips += [s for s in node.body if isinstance(s, ast.Global)
                      and "HERO_INV_RETAIL" in s.names]
    led.ok(a0.hero_inv_legacy is False and a1.hero_inv_legacy is True and len(flips) == 2,
           "--hero-inv-legacy parses (default off) and main() sets the global "
           "HERO_INV_RETAIL = False under it", f"{len(flips)} of 2 statements")


try:
    section_retail()
    section_model()
    section_ours()
    section_source()
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)

sys.exit(led.verdict())
