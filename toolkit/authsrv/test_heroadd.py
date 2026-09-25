"""The hero add, c2s 0x001E HERO_ADD -- SANDBOX-N2's other half (studies/cmsg/
FINDINGS.md DESKWORK-D1 step 4), and the 0x0018 hero-unlock mask that ships
with it. Rewritten by the D1 fix pass of 2026-09-23 after two reviews: the
first cut pinned only the rig it was written in (--hero-bags, --hero-char and
--hero-activate all OFF) and every blocker lived outside it.

    python toolkit/authsrv/test_heroadd.py

WHAT THIS PINS. The add is RECONSTRUCTION end to end -- no tape carries a c2s
0x001E -- so nothing here compares to a retail chunk; what it pins is that the
handler sends exactly the COMMANDER rig's own load messages for the hero, in
that rig's order, that it is the kick's inverse in the rig the owner runs, and
that it refuses where it cannot be.

  * §1 THE BATCH, town, commander rig (HERO_RIG_RETAIL and HERO_ACTIVATE),
    bags and char off: the hero's character block (byte-identical to
    `hero_character_block`, the load's own), then 0x0072, then 0x00B0 with the
    hero COUNTED and a bare 0x01C2 adjacent -- and NO 0x0073/0x0074. The order
    predicate is `add_order`; its KNOWN-BAD arms are a rotated batch, the
    KICK's row-before-size, a re-sent 0x0073, a body AFTER the row, and an
    inventory re-declaration that is not first.
  * §1b THE RIG GATE: with HERO_ACTIVATE off (plain --hero) or under
    --hero-rig-legacy the add REFUSES with nothing sent -- that load holds no
    hero record for a kicked hero, so 0x0072 would assert ChCliHero:199 -- and
    the commander rig is the control.
  * §2 REFUSALS send NOTHING: an unowned index that IS in the kicked set (so
    only the owned check can refuse it -- the first cut's 99 was refused by
    the kicked check instead), a hero already in the party, an EIGHTH hero
    (HEROES_PARTY_MAX, the cap in one name, which main() now reads too), with
    the SEVENTH accepted as the control.
  * §3 THE ROUND TRIP under --persist: kick writes the store, add clears it, a
    fresh connection seeds an empty set and parties the hero; a second add is
    refused; --persist OFF writes nothing.
  * §4 THE BODY, field rig: the body's create burst goes out through
    `hero_body_create` BEFORE the roster row (the commander rig's load order),
    at the hero's OWNED formation slot -- with heroes [5, 6, 7] and 5 kicked at
    load, the re-added 5 takes slot 0 / item 210 while 6 and 7 keep 1 / 211 and
    2 / 212 (the first cut's compacting rule handed 5 hero 6's slot and item);
    kick-then-add re-creates at the same agent id; a town sends no create.
  * §5 THE SANDBOX RIG (--hero-bags, --hero-inventory 2, --hero-char): a kick
    of the last hero destroys key 2 (0x0145) and records it; the add
    RE-DECLARES it FIRST (0x0144 [2, 0] + the equipped bag 0x013F, the load's
    own pair) before the block, registers the agent (0x009A), and a second kick
    destroys the live key again -- while kick -> kick never sends a second
    0x0145 (the guard's known-bad), a hero still naming the key keeps it, and
    with bags off nothing is re-declared.
  * §6 THE 0x0018 MASK: `hero_unlock_mask` reproduces the tape's two values
    ([64] for hero 6, [224] for 5/6/7), keeps OpenTyria's all-ones with no hero
    or under --no-hero-unlock-mask, and needs a second dword for an index >= 32.
  * §7 SOURCE LOCKS (syntax tree over authsrv.py): the 0x001E arm calls
    handle_hero_add only under HERO_ADD_ENABLED; main() wires the three flags;
    hero_body_create is called from BOTH the load and the add with
    hero_owned_slot as its slot; the load's _party_size counts
    party_hero_slots behind PARTY_SIZE_COUNTS_HEROES; hero_inventory_declare
    is ONE implementation with two callers; the kick batch carries the 0x00F8
    the block's ChCliAttrib:313 depends on; 0x0018 has one sender. Each lock
    has a mutation that reddens it.

Drives the real handlers with a fake send and a scratch store, like
test_herokick.py. Floor from the green run (see the ledger line).
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

led = checks.Ledger("hero add (SANDBOX-N2)", floor=86)   # 2026-09-25 desk-partycap, from the green run: +6 in section 2b (the per-map cap) and +2 locks; 78 at the 2026-09-23 fix pass (48 in the first cut)

SRC_PATH = os.path.join(HERE, "authsrv.py")
KICK, ADD = authsrv.GAME_CMSG_HERO_KICK, authsrv.GAME_CMSG_HERO_ADD
HERO_ACTIVATE, PARTY_SIZE, PARTY_HERO_ADD = 0x0072, 0x00B0, 0x01C2
HERO_INFO, MERC_INFO, ATTR_POINTS, ATTRIBUTES = 0x0073, 0x0074, 0x0037, 0x003A
INV_CREATE, BAG_CREATE, INV_DESTROY = 0x0144, 0x013F, 0x0145
CHAR_TABLE, CREATE_AGENT, REMOVE_AGENT = 0x009A, 0x0020, 0x0021
DESPAWN_SWEEP = 0x00F8
UUID = "22222222222222222222222222222222"
assert authsrv.GAME_SMSG_ITEM_STREAM_CREATE == INV_CREATE
assert authsrv.GAME_SMSG_INVENTORY_CREATE_BAG == BAG_CREATE
assert authsrv.GAME_SMSG_INVENTORY_DESTROY == INV_DESTROY
assert authsrv.GAME_SMSG_CHAR_TABLE_VALUE == CHAR_TABLE
assert authsrv.GAME_SMSG_AGENT_DESPAWN_SWEEP == DESPAWN_SWEEP


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals) if isinstance(vals, (list, tuple)) else vals))
    return sent, send


def ops(sent):
    return [op for op, _v in sent]


def add_order(op_list):
    """The add's order in the commander rig -- that rig's own load order for one
    hero with the size/row pair adjacent (the henchman add's shape): an optional
    inventory re-declaration FIRST (0x0144 then 0x013F, and nowhere else), the
    block (0x0037 first, 0x003A last of it), 0x0072, then optionally 0x009A and
    the body's 0x0020 (in that order), and 0x00B0 then 0x01C2 as the LAST TWO.
    No 0x0073 and no 0x0074 anywhere. False when anything is missing, out of
    order, or after the row."""
    o = list(op_list)
    if INV_CREATE in o or BAG_CREATE in o:
        if o[:2] != [INV_CREATE, BAG_CREATE] or INV_CREATE in o[2:] or BAG_CREATE in o[2:]:
            return False
        o = o[2:]
    try:
        i37, i3a, i72 = o.index(ATTR_POINTS), o.index(ATTRIBUTES), o.index(HERO_ACTIVATE)
        ib0, ic2 = o.index(PARTY_SIZE), o.index(PARTY_HERO_ADD)
    except ValueError:
        return False
    if HERO_INFO in o or MERC_INFO in o:
        return False
    ok = (i37 == 0 and i37 < i3a < i72 and ib0 == len(o) - 2 and ic2 == len(o) - 1)
    i9a = o.index(CHAR_TABLE) if CHAR_TABLE in o else None
    i20 = o.index(CREATE_AGENT) if CREATE_AGENT in o else None
    if i9a is not None:
        ok = ok and i72 < i9a < ib0
    if i20 is not None:
        ok = ok and i72 < i20 < ib0 and (i9a is None or i9a < i20)
    return ok


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "PERSIST", "HENCHMAN", "HERO_INVENTORY", "HERO_BAGS", "HERO_CHAR",
           "HERO_AGENT_ID", "PLAYER_NUMBER", "HERO_KICK_ENABLED", "HERO_ADD_ENABLED",
           "HERO_UNLOCK_MASK", "RESET_HERO_KICKS", "PARTY_COMMANDS", "HERO_BODY",
           "EXPLORABLE", "OUTPOST", "PARTY_BODY_IN_OUTPOST", "HERO_ACTIVATE",
           "HERO_RIG_RETAIL", "PARTY_SIZE_COUNTS_HEROES")}
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
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY, authsrv.HERO_CHAR = False, 0, False
    authsrv.HERO_BODY = False
    authsrv.EXPLORABLE, authsrv.OUTPOST, authsrv.PARTY_BODY_IN_OUTPOST = False, False, False
    # THE COMMANDER RIG -- what --party sets (HERO_RIG_RETAIL default, HERO_ACTIVATE
    # on): the only rig whose load sends 0x0072, and the one the add is armed for.
    authsrv.HERO_RIG_RETAIL, authsrv.HERO_ACTIVATE = True, True

    # -- §1 the batch, town, commander rig --------------------------------------
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
           "roster row -- and nothing else (no 0x0144, no 0x009A: bags and char off)",
           f"tail {[hex(o) for o in got[len(block):]]}")
    led.ok(add_order(got),
           "the whole batch passes the order predicate (block, 0x0072, size then "
           "row last and adjacent; no 0x0073, no 0x0074)")
    led.ok(dict(sent).get(PARTY_SIZE) == [68, 2],
           "0x00B0 counts the hero: [player 68, size 2]",
           f"got {dict(sent).get(PARTY_SIZE)}")
    led.ok(dict(sent).get(PARTY_HERO_ADD) == [1, 68, 200, 6, authsrv.HERO_MSG14],
           "0x01C2 is [party 1, owner 68, agent 200, hero 6, HERO_MSG14] -- the "
           "load path's own arguments", f"got {dict(sent).get(PARTY_HERO_ADD)}")
    led.ok(dict(sent).get(HERO_ACTIVATE) == [6, 200, 0, 0],
           "0x0072 is [hero 6, agent 200, inventory 0, aiMode 0] with bags off",
           f"got {dict(sent).get(HERO_ACTIVATE)}")
    led.ok(not authsrv.hero_kicked(state, 6)
           and [h for h, _a, _d in authsrv.party_hero_slots(state)] == [6],
           "the hero is back in the party set")
    led.ok(CREATE_AGENT not in got and 200 not in state["agents"],
           "a TOWN rig creates no body (as at load)")
    # KNOWN-BAD arms through the SAME predicate.
    led.ok(not add_order(got[1:] + got[:1]),
           "KNOWN-BAD: a rotated batch fails the order predicate")
    ib0, ic2 = got.index(PARTY_SIZE), got.index(PARTY_HERO_ADD)
    swapped = list(got)
    swapped[ib0], swapped[ic2] = swapped[ic2], swapped[ib0]
    led.ok(not add_order(swapped),
           "KNOWN-BAD: row-before-size (the KICK's order) fails it -- the add "
           "mirrors the henchman add's size-then-row, 3 of 3 on tape")
    led.ok(not add_order([HERO_INFO] + got) and not add_order([MERC_INFO] + got),
           "KNOWN-BAD: a batch that re-sends 0x0073 (or 0x0074) fails it -- the "
           "add's CHOICE, read statically: our load sends 0x0073 for every owned "
           "hero and neither 0x0075 nor the 0x00F8 sweep deletes the hero record "
           "(they zero heroData->agentId and drop the activation record; cmsg "
           "DESKWORK-D1 'The hero add')")
    led.ok(not add_order(got + [CREATE_AGENT]),
           "KNOWN-BAD: a body AFTER the roster row fails it (the first cut's order; "
           "the commander rig's load creates the body before its deferred 0x01C2)")
    led.ok(add_order([INV_CREATE, BAG_CREATE] + got)
           and not add_order(got[:1] + [INV_CREATE, BAG_CREATE] + got[1:])
           and not add_order([INV_CREATE] + got),
           "KNOWN-BAD: an inventory re-declaration is legal only as the FIRST pair "
           "(0x0144 then 0x013F, retail's load order); later, or 0x0144 alone, fails")

    # -- §1b the rig gate -----------------------------------------------------------
    authsrv.HERO_ACTIVATE = False
    sl, sendl = fake_send_factory()
    stl = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}}
    authsrv.handle_hero_add([ADD, 6], sendl, stl, 0)
    led.ok(sl == [] and authsrv.hero_kicked(stl, 6),
           "LEGACY RIG (HERO_ACTIVATE off, plain --hero): the add REFUSES -- nothing "
           "sent, the hero stays kicked (that load holds no hero record for it, so "
           "0x0072 would assert ChCliHero:199 -- ENG-B2/R5)")
    authsrv.HERO_ACTIVATE, authsrv.HERO_RIG_RETAIL = True, False
    sl2, sendl2 = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendl2, stl, 0)
    led.ok(sl2 == [] and authsrv.hero_kicked(stl, 6),
           "--hero-rig-legacy with --hero-activate: refused too (the gate is the "
           "COMMANDER rig, both halves)")
    authsrv.HERO_RIG_RETAIL = True
    sl3, sendl3 = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendl3, stl, 0)
    led.ok(add_order(ops(sl3)) and not authsrv.hero_kicked(stl, 6),
           "CONTROL: back in the commander rig the same state sends the batch")

    # -- §2 refusals ------------------------------------------------------------
    s2, send2 = fake_send_factory()
    st2 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6, 99}}
    authsrv.handle_hero_add([ADD, 99], send2, st2, 0)
    led.ok(s2 == [] and authsrv.hero_kicked(st2, 6) and 99 in st2["kicked_heroes"],
           "an UNOWNED index sends nothing and changes nothing -- 99 IS in the "
           "kicked set, so only the OWNED check can be what refused it (the first "
           "cut's arm was refused by the kicked check and proved nothing -- ENG-M3)")
    s3, send3 = fake_send_factory()
    st3 = {"agents": {}, "char_uuid": UUID}                  # hero 6 in the party
    authsrv.handle_hero_add([ADD, 6], send3, st3, 0)
    led.ok(s3 == [],
           "a hero ALREADY IN THE PARTY sends nothing (the kick's 'already "
           "kicked' mirror)")
    # A party of eight needs an EIGHT-cap map: since DESKWORK-D1 step 5's fix
    # pass the hero add also refuses at the served map's party cap (party_cap:
    # the map's own AreaInfo max_party from content/partycap.toml since
    # 2026-09-25, the constant OUTPOST_PARTY_CAP for a state with no map id;
    # --henchman-cap overrides), with heroes AND hired henchmen counted --
    # test_henchparty drives that refusal. These two checks are about the
    # client's own hero cap, so they run under the largest max_party (8): the
    # states carry no map id, so the constant is what party_cap answers.
    _saved_cap = authsrv.OUTPOST_PARTY_CAP
    authsrv.OUTPOST_PARTY_CAP = 8
    authsrv.HERO_IDS = [1, 2, 3, 4, 5, 6, 7, 8]
    s4, send4 = fake_send_factory()
    st4 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {8}}
    led.ok(len(authsrv.party_hero_slots(st4)) == authsrv.HEROES_PARTY_MAX == 7,
           "the cap rig: eight owned, seven in the party, HEROES_PARTY_MAX 7 -- a "
           "rig main() refuses (both CLI gates cap the OWNED set), so this check is "
           "the handler's DEFENSIVE half")
    authsrv.handle_hero_add([ADD, 8], send4, st4, 0)
    led.ok(s4 == [] and authsrv.hero_kicked(st4, 8),
           "the EIGHTH hero is refused: nothing sent, still kicked (the cap lives "
           "in HEROES_PARTY_MAX, PtPlayer:332)")
    authsrv.HERO_IDS = [1, 2, 3, 4, 5, 6, 7]
    s5, send5 = fake_send_factory()
    st5 = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {7}}
    authsrv.handle_hero_add([ADD, 7], send5, st5, 0)
    led.ok(add_order(ops(s5)) and dict(s5).get(PARTY_SIZE) == [68, 8],
           "CONTROL: the SEVENTH is accepted -- party 8 (player + 7 heroes)",
           f"size {dict(s5).get(PARTY_SIZE)}")
    authsrv.OUTPOST_PARTY_CAP = _saved_cap
    authsrv.HERO_IDS = [6]

    # -- §2b THE PER-MAP CAP (desk-partycap, 2026-09-25) -------------------------
    # The hero add refuses at the SERVED MAP's own max_party (content/partycap.toml
    # through authsrv.party_cap), not at a constant: the same party -- the player and
    # three hired henchmen, 4 members -- takes the re-added hero on map 248 (8) and
    # refuses it on map 148 (4); a map with no row falls back to 4 and the log says
    # so; --constant-party-cap is the KNOWN-BAD flag arm; --henchman-cap overrides.
    import contextlib
    import io
    _saved_pm = authsrv.PARTY_CAP_PER_MAP
    authsrv.PARTY_CAP_PER_MAP = True
    HIRED = {31: {"name": "W"}, 32: {"name": "R"}, 33: {"name": "A"}}

    def _party_of_four(map_id):
        return {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}, "map_id": map_id,
                "party_henchmen": dict(HIRED)}

    def _add(st):
        s, snd = fake_send_factory()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.handle_hero_add([ADD, 6], snd, st, 0)
        return s, buf.getvalue()
    led.ok(authsrv.MAP_PARTY_CAPS.get(248) == 8 and authsrv.MAP_PARTY_CAPS.get(148) == 4,
           "the content rows: map 248's max_party is 8, map 148's is 4 (client-table, build 38797)")
    st8 = _party_of_four(248)
    s8, log8 = _add(st8)
    led.ok(add_order(ops(s8)) and dict(s8).get(PARTY_SIZE) == [68, 5] and not authsrv.hero_kicked(st8, 6)
           and "the party cap here is 8" in log8,
           "map 248 (max_party 8): the player + 3 hired henchmen + the re-added hero = 5 goes THROUGH, "
           "0x00B0 = 5, the cap line naming 8", f"size {dict(s8).get(PARTY_SIZE)}")
    st4 = _party_of_four(148)
    s4, log4 = _add(st4)
    led.ok(s4 == [] and authsrv.hero_kicked(st4, 6) and "HERO_ADD(6) refused" in log4
           and "(4: map 148's own AreaInfo max_party" in log4,
           "KNOWN-BAD per map: the same party on map 148 (max_party 4) is REFUSED -- nothing sent, the "
           "hero stays kicked, the line names the map's own row", log4.strip()[:150])
    st9 = _party_of_four(999)
    s9, log9 = _add(st9)
    led.ok(s9 == [] and authsrv.hero_kicked(st9, 6) and "map 999 has NO map_party_cap row" in log9
           and "UNVERIFIED" in log9 and "the constant 4 stands in" in log9,
           "the fallback: map 999 has no row, the constant 4 stands in (refused at 4 of 4) and the log "
           "SAYS so -- NO row, UNVERIFIED", log9.strip()[:150])
    authsrv.PARTY_CAP_PER_MAP = False
    stc = _party_of_four(248)
    sc, logc = _add(stc)
    led.ok(sc == [] and authsrv.hero_kicked(stc, 6) and "--constant-party-cap" in logc,
           "KNOWN-BAD flag arm: --constant-party-cap on map 248 refuses at 4 -- the behaviour before "
           "the table, exactly", logc.strip()[:150])
    authsrv.OUTPOST_PARTY_CAP = 8                      # what --henchman-cap 8 sets (with PER_MAP off)
    sth = _party_of_four(148)
    sh, logh = _add(sth)
    led.ok(add_order(ops(sh)) and dict(sh).get(PARTY_SIZE) == [68, 5] and "the party cap here is 8" in logh,
           "--henchman-cap 8 overrides map 148's 4: the same add goes through at 5")
    authsrv.OUTPOST_PARTY_CAP = _saved_cap
    authsrv.PARTY_CAP_PER_MAP = _saved_pm

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
           and add_order(ops(sp)),
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
    authsrv.handle_hero_kick([KICK, 6], fake_send_factory()[1], stp, 0)
    led.ok(store.kicked_heroes(UUID) == [6],
           "kick again after the add: the store holds [6] again")
    authsrv.PERSIST = False
    store2 = charstore.Store.open("heroadd@rurik.invalid", base=base)
    stn = {"agents": {}, "char_uuid": UUID, "charstore_game": store2,
           "kicked_heroes": {6}}
    sn, sendn = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendn, stn, 0)
    led.ok(add_order(ops(sn))
           and charstore.Store.open("heroadd@rurik.invalid",
                                    base=base).kicked_heroes(UUID) == [6],
           "with --persist OFF the add sends its batch and writes NOTHING to the "
           "store (which still holds the earlier kick)")

    # -- §4 the body, field rig ---------------------------------------------------
    authsrv.HERO_BODY = True
    authsrv.EXPLORABLE = True
    led.ok(authsrv.party_bodies_here({"map_id": 168}),
           "the field rig: party_bodies_here is True under --explorable (reachable "
           "from a real client only under --party-body-in-outpost -- the client "
           "sends 0x001E in an outpost only)")
    stf = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6},
           "pos": (500.0, 500.0), "plane": 0, "map_id": 168,
           "spawn_point": (500.0, 500.0, 0)}
    sf, sendf = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendf, stf, 0)
    gf = ops(sf)
    led.ok(add_order(gf) and CREATE_AGENT in gf
           and gf.index(HERO_ACTIVATE) < gf.index(CREATE_AGENT) < gf.index(PARTY_SIZE),
           "in a FIELD the body's 0x0020 comes after 0x0072 and BEFORE the roster "
           "pair -- the commander rig's load order (body, then the deferred build)",
           f"{[hex(o) for o in gf]}")
    body = stf["agents"].get(200)
    led.ok(body is not None and body.get("hero") == 6 and body.get("party_slot") == 0
           and body.get("pos") == (500.0 + authsrv.HERO_BODY_OFFSET[0], 500.0)
           and body.get("plane") == 0 and body.get("weapon_item_id") == authsrv.HERO_WEAPON_ITEM_ID,
           "the body is agent 200, hero 6, formation slot 0, item 210, HERO_BODY_OFFSET "
           "from the player's position -- hero_body_create's placement",
           f"{ {k: body.get(k) for k in ('hero', 'party_slot', 'pos', 'plane', 'weapon_item_id')} if body else None}")
    sk, sendk = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendk, stf, 0)
    led.ok(ops(sk)[0] == REMOVE_AGENT and 200 not in stf["agents"],
           "the kick removes the body first (0x0021) -- the add's inverse")
    sr, sendr = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendr, stf, 0)
    led.ok(CREATE_AGENT in ops(sr) and stf["agents"].get(200, {}).get("hero") == 6,
           "add again: the body is re-created at the SAME agent id 200 (a "
           "definition is per instance; the burrow probe proved the re-create)")
    # THE SLOTS (ENG-B3): heroes [5, 6, 7], 5 kicked at load. The load gives 6
    # and 7 their OWNED slots (1, 2); the re-added 5 takes slot 0 -- three
    # distinct slots, items and positions.
    authsrv.HERO_IDS = [5, 6, 7]
    led.ok([authsrv.hero_owned_slot(h) for h in (5, 6, 7)] == [0, 1, 2],
           "hero_owned_slot is the position in hero_slots(): 5 -> 0, 6 -> 1, 7 -> 2")
    sts = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {5},
           "pos": (500.0, 500.0), "plane": 0, "map_id": 168,
           "spawn_point": (500.0, 500.0, 0)}
    _, sends = fake_send_factory()
    for _hid, _haid, _hdef in authsrv.party_hero_slots(sts):       # the load's body loop
        authsrv.hero_body_create(sends, sts, authsrv.hero_owned_slot(_hid), _hid, _haid,
                                 _hdef, (500.0, 500.0), 0, 0)
    before = {a: (r["party_slot"], r["weapon_item_id"], r["pos"]) for a, r in sts["agents"].items()}
    led.ok(before == {201: (1, 211, (350.0, 620.0)), 202: (2, 212, (350.0, 740.0))},
           "the load with 5 kicked: hero 6 holds slot 1 / item 211, hero 7 slot 2 / "
           "item 212 -- the hole at slot 0 is 5's", f"{before}")
    s6, send6 = fake_send_factory()
    authsrv.handle_hero_add([ADD, 5], send6, sts, 0)
    after = {a: (r["party_slot"], r["weapon_item_id"], r["pos"]) for a, r in sts["agents"].items()}
    led.ok(after.get(200) == (0, 210, (350.0, 500.0)) and add_order(ops(s6))
           and len({v[0] for v in after.values()}) == 3
           and len({v[1] for v in after.values()}) == 3
           and len({v[2] for v in after.values()}) == 3,
           "ADD 5: agent 200 takes slot 0 / item 210 / its own spot -- three "
           "distinct slots, item ids and positions", f"{after}")
    # The first cut's rule was `[h for h, _a, _d in party_hero_slots(state)].index(hid)`.
    party_at_load, party_after = [6, 7], [h for h, _a, _d in authsrv.party_hero_slots(sts)]
    led.ok(party_after == [5, 6, 7]
           and party_at_load.index(6) == 0 == party_after.index(5)
           and authsrv.hero_owned_slot(6) == 1 != authsrv.hero_owned_slot(5),
           "KNOWN-BAD (the first cut's rule): the index AMONG PARTY HEROES gave hero "
           "6 slot 0 at load (party [6, 7]) and 5 slot 0 on the add (party [5, 6, 7]) "
           "-- one slot, one item id, one spot for two bodies; the owned-slot rule "
           "gives 1 and 0")
    authsrv.HERO_IDS = [6]
    authsrv.EXPLORABLE = False
    stt = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}, "map_id": 449}
    st_, sendt = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendt, stt, 0)
    led.ok(CREATE_AGENT not in ops(st_) and add_order(ops(st_)),
           "KNOWN-BAD for the field arm: the same rig in a TOWN sends the roster "
           "batch and no create")
    authsrv.HERO_BODY = False

    # -- §5 the sandbox rig: bags, inventory 2, char ----------------------------
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY, authsrv.HERO_CHAR = True, 2, True
    stb = {"agents": {}, "char_uuid": UUID}                  # hero 6 in the party
    sb1, sendb1 = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendb1, stb, 0)
    led.ok(dict(sb1).get(INV_DESTROY) == [2] and stb.get("hero_inv_destroyed") is True,
           "SANDBOX RIG, kick of the LAST hero: 0x0145 [2] destroys the shared key "
           "and the connection records it")
    sb2, sendb2 = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendb2, stb, 0)
    gb = ops(sb2)
    led.ok(gb[:2] == [INV_CREATE, BAG_CREATE] and add_order(gb),
           "the add RE-DECLARES the key FIRST: 0x0144 then 0x013F, before the block "
           "(retail's load declares the hero's container before its block; without "
           "it 0x0072 names a key the table lost -- ItCliApi:488, R1/ENG-B1)",
           f"{[hex(o) for o in gb[:6]]}")
    led.ok(sb2[0][1] == [2, 0]
           and sb2[1][1] == [2, authsrv.BAG_TYPE_EQUIPPED, authsrv.BAG_MODEL_EQUIPPED,
                             authsrv.EQUIPPED_BAG_ID, authsrv.EQUIPPED_SLOT_COUNT, 0],
           "...and the pair is the load's own bytes: 0x0144 [2, 0], 0x013F [2, type, "
           "model, bag 1, 9 slots, 0]", f"{sb2[:2]}")
    led.ok(dict(sb2).get(HERO_ACTIVATE) == [6, 200, 2, 0]
           and stb.get("hero_inv_destroyed") is False,
           "0x0072 names key 2 and the connection no longer holds it as destroyed")
    led.ok(dict(sb2).get(CHAR_TABLE) == [200, 100 << 24]
           and gb.index(HERO_ACTIVATE) < gb.index(CHAR_TABLE) < gb.index(PARTY_SIZE),
           "under --hero-char the add registers the agent (0x009A [200, 100<<24]) "
           "between 0x0072 and the roster pair -- the load registers party heroes "
           "only, so a hero kicked across a zone would be missing (ENG-M6)")
    sb3, sendb3 = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendb3, stb, 0)
    led.ok(dict(sb3).get(INV_DESTROY) == [2] and stb.get("hero_inv_destroyed") is True,
           "kick -> add -> kick: the second kick destroys the LIVE key again (0x0145 "
           "[2]) -- legal because the add re-declared it")
    # KNOWN-BAD for the guard: a key already destroyed is never destroyed twice.
    stbb = {"agents": {}, "char_uuid": UUID, "hero_inv_destroyed": True}
    sb4, sendb4 = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendb4, stbb, 0)
    led.ok(INV_DESTROY not in ops(sb4) and len(sb4) == 5,
           "KNOWN-BAD guarded: a kick on a connection whose key is already destroyed "
           "sends the five-message batch and NO 0x0145 (ItCliApi:2024)")
    # CONTROL: a second hero still naming the key -- nothing destroyed, nothing re-declared.
    authsrv.HERO_IDS = [6, 7]
    stc = {"agents": {}, "char_uuid": UUID}
    sc1, sendc1 = fake_send_factory()
    authsrv.handle_hero_kick([KICK, 6], sendc1, stc, 0)
    sc2, sendc2 = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendc2, stc, 0)
    led.ok(INV_DESTROY not in ops(sc1) and not stc.get("hero_inv_destroyed")
           and INV_CREATE not in ops(sc2) and add_order(ops(sc2))
           and dict(sc2).get(HERO_ACTIVATE) == [6, 200, 2, 0],
           "CONTROL, two heroes on one key: the kick keeps the key (hero 7 names it), "
           "the add re-declares nothing and still names key 2")
    authsrv.HERO_IDS = [6]
    # KNOWN-BAD for the re-declaration gate: bags off -> nothing to declare.
    authsrv.HERO_BAGS = False
    std = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}, "hero_inv_destroyed": True}
    sd, sendd = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sendd, std, 0)
    led.ok(INV_CREATE not in ops(sd) and BAG_CREATE not in ops(sd) and add_order(ops(sd)),
           "with --hero-bags OFF nothing is re-declared even if the flag says "
           "destroyed (nothing was ever declared to destroy)")
    authsrv.HERO_BAGS, authsrv.HERO_CHAR = True, False
    ste = {"agents": {}, "char_uuid": UUID, "kicked_heroes": {6}}
    se, sende = fake_send_factory()
    authsrv.handle_hero_add([ADD, 6], sende, ste, 0)
    led.ok(CHAR_TABLE not in ops(se) and add_order(ops(se)),
           "CONTROL: with --hero-char OFF no 0x009A (the flag is read, as at load)")
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY, authsrv.HERO_CHAR = False, 0, False
    # The block's ChCliAttrib:313 dependency: the kick batch ALWAYS carries the
    # 0x00F8 whose sweep clears the agent's attribState.
    kb = [op for op, _v, _l in authsrv.hero_kick_batch(200, 68, 1, None, 1)]
    led.ok(DESPAWN_SWEEP in kb,
           "the kick batch carries 0x00F8 AGENT_DESPAWN_SWEEP -- the sweep that "
           "clears the agent's attribState (pvpui 31.1), which is what makes the "
           "add's 0x0037 legal against ChCliAttrib:313 (R6/ENG-M2)")

    # -- §6 the 0x0018 mask ---------------------------------------------------------
    authsrv.HERO_UNLOCK_MASK = True
    authsrv.HERO_IDS = [6]
    led.ok(authsrv.hero_unlock_mask() == [64],
           "hero 6 owned -> [64]: bit 6, the 2026-08 tapes' value")
    authsrv.HERO_IDS = [5, 6, 7]
    led.ok(authsrv.hero_unlock_mask() == [224],
           "heroes 5, 6, 7 owned -> [224]: the 20260913+ tapes' value (bit = hero "
           "index CORROBORATED on 15 of 17 comparable connections; the 2 contrary "
           "make it the ACCOUNT's superset, so owned-set is a labelled policy)")
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


# -- §7 source locks on authsrv.py ---------------------------------------------
def _func(tree, name):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _calls(node):
    return {c.func.id for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def _call_nodes(node, name):
    return [c for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == name]


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


def party_size_lock(tree):
    """In _handle_request_players, the assignment to `_party_size` calls
    party_hero_slots AND reads PARTY_SIZE_COUNTS_HEROES (the revert arm)."""
    fn = _func(tree, "_handle_request_players")
    for n in ast.walk(fn):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "_party_size"):
            names = {x.id for x in ast.walk(n.value) if isinstance(x, ast.Name)}
            return ("party_hero_slots" in _calls(n.value)
                    and "PARTY_SIZE_COUNTS_HEROES" in names)
    return False


def body_slot_lock(tree, fn_name):
    """Every hero_body_create call in `fn_name` passes hero_owned_slot(...) as its
    slot (the third positional argument)."""
    calls = _call_nodes(_func(tree, fn_name), "hero_body_create")
    return bool(calls) and all(
        len(c.args) >= 3 and isinstance(c.args[2], ast.Call)
        and isinstance(c.args[2].func, ast.Name) and c.args[2].func.id == "hero_owned_slot"
        for c in calls)


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

flags = main_flags(TREE, ("no_hero_add", "no_hero_unlock_mask", "party_size_no_heroes"))
led.ok(flags == {"no_hero_add": ("HERO_ADD_ENABLED", False),
                 "no_hero_unlock_mask": ("HERO_UNLOCK_MASK", False),
                 "party_size_no_heroes": ("PARTY_SIZE_COUNTS_HEROES", False)},
       "LOCK: main() wires --no-hero-add, --no-hero-unlock-mask and "
       "--party-size-no-heroes to their globals", f"got {flags}")
led.ok(_saved["HERO_ADD_ENABLED"] is True and _saved["HERO_UNLOCK_MASK"] is True
       and _saved["PARTY_SIZE_COUNTS_HEROES"] is True,
       "all three are ON by default -- the flags are the revert arms (the "
       "defaults' comments carry the evidence and the rig each claim is scoped to)")

# The rig gate is in the handler, not only in prose.
add_fn = _func(TREE, "handle_hero_add")
_add_src = ast.get_source_segment(SRC, add_fn)
led.ok("HERO_RIG_RETAIL and HERO_ACTIVATE" in _add_src
       and _add_src.index("HERO_RIG_RETAIL and HERO_ACTIVATE")
       < _add_src.index("kicked_heroes_set(state).discard(hid)"),
       "LOCK: handle_hero_add tests the commander rig (HERO_RIG_RETAIL and "
       "HERO_ACTIVATE) BEFORE it un-kicks anything")
led.ok("hero_kicked" in _calls(add_fn),
       "LOCK: handle_hero_add checks hero_kicked -- the guard the block's "
       "ChCliAttrib:313 depends on (a kick sent 0x00F8, or the load skipped the block)")
# desk-partycap: the cap is resolved per map (party_cap) before the cap check, and the
# constant is never compared directly.
_CAP_CALL = "cap, cap_why = party_cap(state)"
led.ok("party_cap" in _calls(add_fn) and _add_src.count(_CAP_CALL) == 1
       and _add_src.index(_CAP_CALL) < _add_src.index("henchparty.party_is_full(party_member_count(state), cap)")
       and "party_is_full(party_member_count(state), OUTPOST_PARTY_CAP)" not in _add_src,
       "LOCK: handle_hero_add resolves the cap through party_cap(state) BEFORE the cap check and "
       "never compares OUTPOST_PARTY_CAP directly (the per-map cap, 2026-09-25)")
_mut_cap = ast.parse(SRC.replace(_CAP_CALL, 'cap, cap_why = OUTPOST_PARTY_CAP, ""'))
led.ok("party_cap" not in _calls(_func(_mut_cap, "handle_hero_add")),
       "KNOWN-BAD: the constant restored in place of party_cap(state) fails the lock")

# One body implementation, two callers, both keyed on the OWNED slot.
load_fn = _func(TREE, "_handle_request_players")
led.ok("hero_body_create" in _calls(load_fn) and "hero_body_create" in _calls(add_fn)
       and _func(TREE, "hero_body_create") is not None
       and "create_agent_world" not in _calls(add_fn)
       and SRC.count("create_agent_world(") >= 2,
       "LOCK: hero_body_create exists and is called from BOTH the load path and "
       "the add; the add calls create_agent_world only through it")
led.ok(SRC.count('f"hero body (hero {_hid})", conn_id=conn_id)') == 1,
       "and the body's label appears once -- the load loop's body moved, not copied")
led.ok(body_slot_lock(TREE, "_handle_request_players") and body_slot_lock(TREE, "handle_hero_add"),
       "LOCK: both callers pass hero_owned_slot(...) as the body's slot (ENG-B3)")
led.ok(SRC.count("hero_body_create(send, state, hero_owned_slot(_hid),") == 1,
       "the add's call has the expected text (so the mutation below hits it)")
mut4 = ast.parse(SRC.replace("hero_body_create(send, state, hero_owned_slot(_hid),",
                             "hero_body_create(send, state, 0,", 1))
led.ok(not body_slot_lock(mut4, "handle_hero_add") and body_slot_lock(mut4, "_handle_request_players"),
       "KNOWN-BAD: a literal slot in the add fails the lock (and the load's is untouched)")

led.ok(party_size_lock(TREE),
       "LOCK: the load path's _party_size counts party_hero_slots behind "
       "PARTY_SIZE_COUNTS_HEROES (retail's load sent [68, 2] with one hero)")
led.ok("_party_size = 1 if HENCHMAN is None else 2" not in SRC,
       "and the under-counting literal is gone")
_ps_old = ("+ (len(party_hero_slots(state))\n"
           "                      if PARTY_SIZE_COUNTS_HEROES else 0))")
led.ok(SRC.count(_ps_old) == 1, "the size expression has the expected text")
led.ok(not party_size_lock(ast.parse(SRC.replace(_ps_old, "+ 0)", 1))),
       "KNOWN-BAD: a _party_size that drops the hero count fails the lock")
led.ok(not party_size_lock(ast.parse(SRC.replace(_ps_old, "+ len(party_hero_slots(state)))", 1))),
       "KNOWN-BAD: a _party_size that counts heroes with NO revert flag fails it too")

# The inventory pair: one implementation, the load and the add.
inv_fn = _func(TREE, "hero_inventory_declare")
led.ok(inv_fn is not None and "hero_inventory_declare" in _calls(add_fn)
       and "hero_inventory_declare" in _calls(_func(TREE, "handle"))
       and SRC.count("ITEM_STREAM_CREATE(hero inv") == 1
       and SRC.count("INVENTORY_CREATE_BAG(hero equipped)") == 1,
       "LOCK: hero_inventory_declare exists, the REQUEST_ITEMS arm and the add both "
       "call it, and the pair's labels appear once (moved, not copied)")
kick_fn = _func(TREE, "handle_hero_kick")
_kick_src = ast.get_source_segment(SRC, kick_fn)
_inv_src = ast.get_source_segment(SRC, inv_fn) if inv_fn else ""
led.ok('state["hero_inv_destroyed"] = True' in _kick_src
       and 'state["hero_inv_destroyed"] = False' in _inv_src
       and 'state.get("hero_inv_destroyed")' in _kick_src
       and 'state.get("hero_inv_destroyed")' in _add_src,
       "LOCK: the kick SETS hero_inv_destroyed when it sends 0x0145 and READS it "
       "before sending another; the declaration CLEARS it; the add reads it")

led.ok(SRC.count("send(GAME_SMSG_PVP_UPDATE_UNLOCKED_HEROES,") == 1
       and "[[0xFFFFFFFF] * 8]" not in SRC
       and "_hum = hero_unlock_mask()" in SRC,
       "LOCK: 0x0018 has ONE sender, it calls hero_unlock_mask(), and the "
       "all-ones literal is gone from the send site (a second sender of unlock "
       "state once wiped a library -- the 0x001D comment)")
led.ok("len(HERO_IDS) > 7" not in SRC and "len(_pheroes) > 7" not in SRC
       and SRC.count("> HEROES_PARTY_MAX") >= 2 and SRC.count(">= HEROES_PARTY_MAX") >= 1,
       "LOCK: main()'s --hero and --party gates read HEROES_PARTY_MAX, not the "
       "literal 7 (R7/ENG-M7), and the handler reads it too")

sys.exit(led.verdict())
