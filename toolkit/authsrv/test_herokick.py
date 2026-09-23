"""The hero kick, c2s 0x001F HERO_KICK -- SANDBOX-N2 (studies/cmsg/FINDINGS.md
DESKWORK-D1).

    python toolkit/authsrv/test_herokick.py

WHAT THIS PINS.

  * §1 THE BATCH, against the TAPE'S OWN BYTES. `hero_kick_batch` is pure; its
    six messages are encoded through the codec and compared byte for byte with
    the s2c plaintext chunk at t=158.7182 on 20260916T150306 :62321 (35 bytes,
    the chunk's prefix; the remaining 6 are 0x001E [62]). The KNOWN-BAD arm is a
    rotated batch through the SAME comparator, which must NOT match -- the
    first cut compared the order to a hand-typed list and its "known-bad" was
    `reversed(order) != ORDER`, which no six-element list can fail. Vault-gated;
    a missing capture declares a skip.
  * §2 THE HANDLER, driven like the 0x005E swap (test_charstore): the real
    `handle_hero_kick`, a fake send, a state. Arms: (a) the DEFAULT rig
    (--hero-bags off, key 0) sends FIVE messages and no 0x0145 -- the first cut
    sent 0x0145 [0], which the client's handler asserts on (ItCliApi:2024);
    (b) a hero WITH A BODY leaves through remove_agent (0x0021 first,
    RECONSTRUCTION), its standing orders cleared; (c) a bags rig in a town
    sends retail's exact six with OUR ids; (d) TWO heroes sharing one key: the
    first kick keeps the key (hero 7 still names it), the second destroys it;
    (e) refusals -- an unowned index and an already-kicked hero send NOTHING;
    (f) a kicked hero takes no commands (the hero_command guard).
  * §3 PERSIST across a zone, the acceptance. A kick on a --persist store
    writes the character's `kicked_heroes`; a FRESH connection seeds it back, so
    `hero_slots()` still OWNS the hero (0x0073 goes out) while
    `party_hero_slots()` EXCLUDES it (no 0x0072/0x01C2) -- the tape's next two
    loads. Controls: --persist OFF writes nothing; `--no-hero-kick` with a SAVED
    kick puts every owned hero back in the party without reading the store (a
    revert that left a saved kick in force was not a revert); `--reset-hero-kicks`
    clears the store (the un-kick until the ADD ships).
  * §4 SOURCE LOCKS on authsrv.py, the repo's syntax-tree style: every hero
    loop in `_handle_request_players` iterates `party_hero_slots(state)` or
    guards on `hero_kicked` (the first cut's acceptance had no test that could
    fail: reverting any of the twelve loops stayed green); the dispatch arm calls
    `handle_hero_kick` only under `HERO_KICK_ENABLED`; `main()` wires both
    flags; `hero_locks_release` and `handle_hero_command` iterate the party.
    Each lock has a KNOWN-BAD mutation of the source text that must redden it.

`handle_hero_kick` needs the server, so this cannot live in the bare-machine
`test_herolib.py` (that module imports no server); it drives the real handler
with a scratch store instead, like `test_charstore.py`. Floor 52.
"""
import ast
import json
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
import codec as codecmod                                     # noqa: E402
import authsrv                                               # noqa: E402
import livewire                                              # noqa: E402

led = checks.Ledger("hero kick (SANDBOX-N2)", floor=52)

# The tape's own reply order (20260916T150306 :62321, t=158.718).
RETAIL_ORDER = [0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0, 0x0145]
CAPTURE, CONN_FILE = "20260916T150306", "game-10.0.0.210_62321-to-3.228.147.153_80.jsonl"
KICK_T = 158.7182
COD = codecmod.Codec()
SRC_PATH = os.path.join(HERE, "authsrv.py")


def encode_batch(batch):
    return b"".join(COD.encode("GAME_SMSG", op, vals) for op, vals, _l in batch)


# -- §1 the batch, byte for byte against the tape ----------------------------
batch = authsrv.hero_kick_batch(379, 68, 28, 96, 1)
led.ok(len(batch) == 6, "the kick batch is six messages", f"got {len(batch)}")
order = [op for op, _v, _l in batch]
led.ok(order == RETAIL_ORDER,
       "the batch is in retail's order 0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0, "
       "0x0145", f"got {[hex(x) for x in order]}")
c3 = next((v for op, v, _l in batch if op == authsrv.GAME_SMSG_PARTY_HERO_REMOVE), None)
led.ok(c3 == [28, 68, 379],
       "0x01C3 PARTY_HERO_REMOVE is [party, owner, agent]", f"got {c3}")
b0 = next((v for op, v, _l in batch if op == authsrv.GAME_SMSG_PLAYER_PARTY_SIZE), None)
led.ok(b0 == [68, 1], "0x00B0 PLAYER_PARTY_SIZE is [player, size]", f"got {b0}")
five = authsrv.hero_kick_batch(379, 68, 28, None, 1)
led.ok([op for op, _v, _l in five] == RETAIL_ORDER[:-1],
       "inventory None OMITS the 0x0145 row and leaves the other five in order",
       f"got {[hex(op) for op, _v, _l in five]}")

capdir = os.path.join(livewire.captures_root(), CAPTURE)
if os.path.exists(os.path.join(capdir, CONN_FILE)):
    _c, events, err = livewire.build_events(capdir, CONN_FILE, "s2c")
    chunk = next((p for t, p in (events or []) if abs(t - KICK_T) < 0.005), None)
    wire = encode_batch(batch)
    led.ok(err is None and chunk is not None,
           f"the tape's s2c stream closes and has a chunk at t={KICK_T}",
           f"err {err}, chunk {chunk is not None}")
    led.ok(chunk is not None and len(wire) == 35 and chunk[:35] == wire,
           "hero_kick_batch(379, 68, 28, 96, 1) encodes to the tape's 35 bytes at "
           "t=158.7182, byte for byte",
           f"ours {wire.hex()} tape {(chunk or b'')[:35].hex()}")
    led.ok(chunk is not None and chunk[35:] == bytes.fromhex("1e003e000000"),
           "and the rest of that 41-byte chunk is 0x001E [62] -- the batch is a "
           "prefix, so the comparison window is the right one",
           f"rest {(chunk or b'')[35:].hex()}")
    rotated = batch[1:] + batch[:1]
    bad_wire = encode_batch(rotated)
    led.ok(chunk is not None and bad_wire != chunk[:len(bad_wire)],
           "KNOWN-BAD: a rotated batch through the same comparator does NOT match "
           "the tape -- the order check can fail")
    swapped = [batch[0], batch[1], batch[3], batch[2], batch[4], batch[5]]
    led.ok(chunk is not None and encode_batch(swapped) != chunk[:35],
           "KNOWN-BAD: swapping 0x00F8/0x003E alone does NOT match either")
else:
    led.skip("§1 tape replay", f"capture {CAPTURE} {CONN_FILE} not in the vault")


# -- §2 the real handler -----------------------------------------------------
def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals)))
    return sent, send


def ops(sent):
    return [op for op, _v in sent]


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "PERSIST", "HENCHMAN", "HERO_INVENTORY", "HERO_BAGS",
           "HERO_AGENT_ID", "PLAYER_NUMBER", "HERO_KICK_ENABLED",
           "RESET_HERO_KICKS", "PARTY_COMMANDS")}
base = tempfile.mkdtemp(prefix="herokick-test-")
UUID = "11111111111111111111111111111111"
try:
    authsrv.HERO_IDS = [6]
    authsrv.HERO_AGENT_ID = 200
    authsrv.PLAYER_NUMBER = 68
    authsrv.HENCHMAN = None
    authsrv.PERSIST = False
    authsrv.HERO_KICK_ENABLED = True
    authsrv.RESET_HERO_KICKS = False
    authsrv.PARTY_COMMANDS = True

    # (a) THE DEFAULT RIG: --hero-bags off, key 0, a town (no body).
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY = False, 0
    sent, send = fake_send_factory()
    state = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], send, state, 0)
    led.ok(ops(sent) == RETAIL_ORDER[:-1],
           "the DEFAULT rig sends five messages and NO 0x0145 -- no container "
           "was ever declared, and 0x0145 [0] asserts the client (ItCliApi:2024)",
           f"got {[hex(x) for x in ops(sent)]}")
    led.ok(authsrv.GAME_SMSG_INVENTORY_DESTROY not in ops(sent)
           and authsrv.GAME_SMSG_WORLD_REMOVE_AGENT not in ops(sent),
           "...and no 0x0021 either: a town hero has no body to remove")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_HERO_UNLINK) == [200],
           "0x0075 carries OUR hero agent id (200), not the tape's 379")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_PARTY_HERO_REMOVE) == [1, 68, 200],
           "0x01C3 is [party 1, owner PLAYER_NUMBER, agent 200] with our ids")
    led.ok(dict(sent).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE) == [68, 1],
           "0x00B0 drops the party to 1 (the player alone)")
    led.ok(authsrv.hero_kicked(state, 6),
           "the hero is now in the connection's kicked set")
    led.ok([h for h, _a, _d in authsrv.party_hero_slots(state)] == []
           and [h for h, _a, _d in authsrv.hero_slots()] == [6],
           "party_hero_slots excludes the kicked hero; hero_slots still OWNS it")

    # (b) A HERO WITH A BODY, bags rig: remove_agent (0x0021) leads.
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY = True, 96
    sentb, sendb = fake_send_factory()
    stateb = {"agents": {200: {"name": "Koss"}}, "char_uuid": UUID,
              "hero_cmd": {200: {"ai_mode": 1, "lock": 5, "flag": None}}}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendb, stateb, 0)
    led.ok(ops(sentb) == [authsrv.GAME_SMSG_WORLD_REMOVE_AGENT] + RETAIL_ORDER,
           "a hero WITH A BODY: 0x0021 WORLD_REMOVE_AGENT first (RECONSTRUCTION "
           "-- the retail witness had no body), then retail's six",
           f"got {[hex(x) for x in ops(sentb)]}")
    led.ok(sentb[0][1] == [200] and 200 not in stateb["agents"]
           and stateb.get("removed_agents") == [200],
           "the body is removed through remove_agent: id 200 leaves state[agents] "
           "and is logged in removed_agents (so the id is never reused under a "
           "stale client object)")
    led.ok(200 not in stateb["hero_cmd"],
           "the kicked hero's standing orders (hero_cmd) are cleared with it")
    led.ok(dict(sentb).get(authsrv.GAME_SMSG_INVENTORY_DESTROY) == [96],
           "with --hero-bags and a single hero, 0x0145 destroys the declared key")

    # (c) A bags rig in a TOWN: retail's exact six with our ids.
    sentc, sendc = fake_send_factory()
    statec = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendc, statec, 0)
    led.ok(ops(sentc) == RETAIL_ORDER,
           "a bags rig in a town emits exactly retail's six, in order",
           f"got {[hex(x) for x in ops(sentc)]}")

    # (d) TWO heroes sharing ONE key: the first kick keeps it, the second kills it.
    authsrv.HERO_IDS = [6, 7]
    authsrv.HERO_INVENTORY = 2
    sentd, sendd = fake_send_factory()
    stated = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendd, stated, 0)
    led.ok(ops(sentd) == RETAIL_ORDER[:-1],
           "two heroes, one shared key: kicking hero 6 sends NO 0x0145 -- hero 7 "
           "still names key 2 (the first cut destroyed it under hero 7's feet)",
           f"got {[hex(x) for x in ops(sentd)]}")
    led.ok(dict(sentd).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE) == [68, 2],
           "...and the party is 2 (player + hero 7)",
           f"got {dict(sentd).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE)}")
    sente, sende = fake_send_factory()
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 7], sende, stated, 0)
    led.ok(ops(sente) == RETAIL_ORDER
           and dict(sente).get(authsrv.GAME_SMSG_INVENTORY_DESTROY) == [2]
           and dict(sente).get(authsrv.GAME_SMSG_PLAYER_PARTY_SIZE) == [68, 1],
           "kicking the LAST hero destroys key 2 (nobody names it now) and the "
           "party is 1", f"got {[(hex(o), v) for o, v in sente]}")

    # (e) Refusals.
    authsrv.HERO_IDS = [6]
    sent2, send2 = fake_send_factory()
    state2 = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 99], send2, state2, 0)
    led.ok(sent2 == [] and not authsrv.hero_kicked(state2, 99),
           "kicking a hero this run does not own sends nothing "
           "(the known-bad arm: it would emit a teardown for a phantom agent)")
    sent3, send3 = fake_send_factory()
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], send3, state, 0)
    led.ok(sent3 == [],
           "kicking an already-kicked hero sends nothing -- no double teardown")

    # (f) A kicked hero takes no commands.
    sentf, sendf = fake_send_factory()
    statef = {"agents": {}, "char_uuid": UUID}
    authsrv.handle_hero_command([0, 200, 1], sendf, statef, 0,
                                authsrv.GAME_CMSG_HERO_AI_MODE)
    before = len(sentf)
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6],
                             fake_send_factory()[1], statef, 0)
    authsrv.handle_hero_command([0, 200, 1], sendf, statef, 0,
                                authsrv.GAME_CMSG_HERO_AI_MODE)
    led.ok(before == 1 and len(sentf) == 1,
           "a hero command for agent 200 is echoed BEFORE the kick and ignored "
           "AFTER it (the hero_command guard reads the party, not the roster)",
           f"before {before}, after {len(sentf)}")

    # -- §3 persist across a zone ---------------------------------------------
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY = False, 0
    authsrv.PERSIST = True
    store = charstore.Store.open("herokick@rurik.invalid", base=base)
    store.ensure_character(UUID, "Kicker", "aa" * 37)
    led.ok(store.kicked_heroes(UUID) == [],
           "a fresh character has no kicked heroes (the positive control)")

    sp, sendp = fake_send_factory()
    statep = {"agents": {}, "char_uuid": UUID, "charstore_game": store}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendp, statep, 0)
    led.ok(store.kicked_heroes(UUID) == [6],
           "under --persist the kick is written to the character store")

    reopened = charstore.Store.open("herokick@rurik.invalid", base=base)
    led.ok(reopened.kicked_heroes(UUID) == [6],
           "and it survives a store reopen (the next zone reads it back)")

    fresh = {"agents": {}, "char_uuid": UUID, "charstore_game": reopened}
    led.ok(authsrv.kicked_heroes_set(fresh) == {6},
           "the next connection seeds the kicked set from the store")
    led.ok(authsrv.hero_kicked(fresh, 6),
           "so the kicked hero is still kicked after the zone")
    led.ok([h for h, _a, _d in authsrv.hero_slots()] == [6]
           and [h for h, _a, _d in authsrv.party_hero_slots(fresh)] == [],
           "the next zone-in OWNS hero 6 (0x0073) but does NOT party it "
           "(no 0x0072/0x01C2) -- SANDBOX-N2 acceptance (b)")

    # THE REVERT ARM with a SAVED kick: --no-hero-kick reads no store.
    authsrv.HERO_KICK_ENABLED = False
    off = {"agents": {}, "char_uuid": UUID, "charstore_game": reopened}
    led.ok(authsrv.kicked_heroes_set(off) == set()
           and [h for h, _a, _d in authsrv.party_hero_slots(off)] == [6],
           "--no-hero-kick with a SAVED kick in the store: every owned hero is in "
           "the party -- the revert reverts (the first cut read the store anyway)")
    led.ok(reopened.kicked_heroes(UUID) == [6],
           "...and the store is left as it was (the flag reads nothing, writes "
           "nothing)")
    authsrv.HERO_KICK_ENABLED = True

    # THE UN-KICK: --reset-hero-kicks clears the store at the first seed.
    authsrv.RESET_HERO_KICKS = True
    reset = {"agents": {}, "char_uuid": UUID, "charstore_game": reopened}
    led.ok(authsrv.kicked_heroes_set(reset) == set()
           and reopened.kicked_heroes(UUID) == []
           and charstore.Store.open("herokick@rurik.invalid",
                                    base=base).kicked_heroes(UUID) == [],
           "--reset-hero-kicks: the seed clears the character's kicked_heroes in "
           "the store (and on disk) and hero 6 is back in the party",
           f"set {authsrv.kicked_heroes_set(reset)}, store {reopened.kicked_heroes(UUID)}")
    authsrv.RESET_HERO_KICKS = False

    # Control: with --persist off, the store is untouched.
    authsrv.PERSIST = False
    store3 = charstore.Store.open("herokick@rurik.invalid", base=base)
    store3.set_hero_kicked(UUID, 6, kicked=False)          # reset
    sc, sendc2 = fake_send_factory()
    statec2 = {"agents": {}, "char_uuid": UUID, "charstore_game": store3}
    authsrv.handle_hero_kick([authsrv.GAME_CMSG_HERO_KICK, 6], sendc2, statec2, 0)
    led.ok(charstore.Store.open("herokick@rurik.invalid", base=base)
           .kicked_heroes(UUID) == [],
           "with --persist OFF the kick sends its batch but writes NOTHING to "
           "the store -- the pre-N2 store shape is unchanged")
    led.ok(ops(sc) == RETAIL_ORDER[:-1],
           "...and the batch still goes out on the wire regardless of persist")

    # The store REFUSES a bad kicked_heroes list at load (the validate guard).
    good = json.loads(json.dumps(
        charstore.Store.open("herokick@rurik.invalid", base=base).data))
    chars = list((good.get("characters") or {}).values())
    led.ok(len(chars) == 1, "the scratch store holds the one character",
           f"got {len(chars)}")
    refused = False
    if chars:
        chars[0]["kicked_heroes"] = [0]                     # index 0 is not a hero
        bad = os.path.join(base, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump(good, f)
        try:
            charstore.validate(json.load(open(bad, encoding="utf-8")), bad)
        except ValueError:
            refused = True
    led.ok(refused,
           "the store refuses kicked_heroes holding index 0 -- a shape error, "
           "not a silent default")
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    shutil.rmtree(base, ignore_errors=True)


# -- §4 source locks on authsrv.py -------------------------------------------
def _func(tree, name):
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


def _calls(node):
    """The names of every function called anywhere under `node`."""
    return {c.func.id for c in ast.walk(node)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def load_path_lock(tree):
    """(hero_slots_loops, unguarded_linenos, party_loops) for the world load.

    Every `for` over `hero_slots()` in `_handle_request_players` must guard on
    `hero_kicked` in its body (the 0x0073 HERO_INFO loops: owned heroes get
    0x0073, kicked ones nothing further); every other hero loop iterates
    `party_hero_slots(state)`.
    """
    fn = _func(tree, "_handle_request_players")
    hs = party = 0
    unguarded = []
    for n in ast.walk(fn):
        if not isinstance(n, ast.For):
            continue
        it = _calls(n.iter)
        if "party_hero_slots" in it:
            party += 1
        elif "hero_slots" in it:
            hs += 1
            body = set()
            for stmt in n.body:
                body |= _calls(stmt)
            if "hero_kicked" not in body:
                unguarded.append(n.lineno)
    return hs, unguarded, party


def dispatch_lock(tree):
    """(arm_ok, flags): the 0x001F arm calls handle_hero_kick only under
    HERO_KICK_ENABLED; main() sets the two globals from the two flags."""
    handle = _func(tree, "handle")
    arm_ok = False
    for n in ast.walk(handle):
        if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
            continue
        t = n.test
        if not (isinstance(t.left, ast.Name) and t.left.id == "opcode"
                and len(t.comparators) == 1
                and isinstance(t.comparators[0], ast.Name)
                and t.comparators[0].id == "GAME_CMSG_HERO_KICK"):
            continue
        inner = [s for s in n.body if isinstance(s, ast.If)]
        direct = any("handle_hero_kick" in _calls(s) for s in n.body
                     if not isinstance(s, ast.If))
        if (len(inner) == 1 and not direct
                and isinstance(inner[0].test, ast.Name)
                and inner[0].test.id == "HERO_KICK_ENABLED"
                and any("handle_hero_kick" in _calls(s) for s in inner[0].body)
                and not any("handle_hero_kick" in _calls(s)
                            for s in inner[0].orelse)):
            arm_ok = True
    main = _func(tree, "main")
    flags = {}
    for n in ast.walk(main):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Attribute)
                and n.test.attr in ("no_hero_kick", "reset_hero_kicks")):
            for s in n.body:
                if (isinstance(s, ast.Assign) and len(s.targets) == 1
                        and isinstance(s.targets[0], ast.Name)
                        and isinstance(s.value, ast.Constant)):
                    flags[n.test.attr] = (s.targets[0].id, s.value.value)
    return arm_ok, flags


with open(SRC_PATH, encoding="utf-8") as f:
    SRC = f.read()
TREE = ast.parse(SRC)

hs, unguarded, party = load_path_lock(TREE)
led.ok(hs == 2 and unguarded == [],
       "LOCK: the two hero_slots() loops in the world load (the 0x0073 HERO_INFO "
       "sites) both guard on hero_kicked; no unguarded owned-hero loop remains",
       f"hero_slots loops {hs}, unguarded at lines {unguarded}")
led.ok(party >= 9,
       "LOCK: at least nine hero loops in the world load iterate "
       "party_hero_slots(state) (body, profession, level, vitals, attributes, "
       "skillbar, char, activate, party build)", f"got {party}")
# KNOWN-BAD: revert ONE party loop to hero_slots() and the lock must redden.
fn_src_start = SRC.index("def _handle_request_players(")
mut = (SRC[:fn_src_start]
       + SRC[fn_src_start:].replace("party_hero_slots(state)", "hero_slots()", 1))
hs_m, unguarded_m, party_m = load_path_lock(ast.parse(mut))
led.ok(hs_m == 3 and len(unguarded_m) == 1 and party_m == party - 1,
       "KNOWN-BAD: reverting one party loop to hero_slots() is caught -- three "
       "hero_slots loops, one unguarded", f"{hs_m}, {unguarded_m}, {party_m}")

arm_ok, flags = dispatch_lock(TREE)
led.ok(arm_ok,
       "LOCK: the GAME_CMSG_HERO_KICK dispatch arm calls handle_hero_kick ONLY "
       "under `if HERO_KICK_ENABLED:` (and never in its else)")
led.ok(flags == {"no_hero_kick": ("HERO_KICK_ENABLED", False),
                 "reset_hero_kicks": ("RESET_HERO_KICKS", True)},
       "LOCK: main() wires --no-hero-kick -> HERO_KICK_ENABLED=False and "
       "--reset-hero-kicks -> RESET_HERO_KICKS=True", f"got {flags}")
led.ok(_saved["HERO_KICK_ENABLED"] is True and _saved["RESET_HERO_KICKS"] is False,
       "the kick is ON by default and the reset OFF -- OBSERVED and tested, so "
       "--no-hero-kick and --reset-hero-kicks are both opt-in")
# KNOWN-BAD: `if HERO_KICK_ENABLED:` -> `if True:` and the arm lock must redden.
led.ok(SRC.count("if HERO_KICK_ENABLED:") == 1,
       "the dispatch arm's condition appears exactly once in the source (so the "
       "mutation below hits the arm)", f"count {SRC.count('if HERO_KICK_ENABLED:')}")
arm_m, _f = dispatch_lock(ast.parse(SRC.replace("if HERO_KICK_ENABLED:",
                                                "if True:", 1)))
led.ok(arm_m is False,
       "KNOWN-BAD: an arm that ignores HERO_KICK_ENABLED fails the lock")
arm_m2, _f = dispatch_lock(ast.parse(SRC.replace(
    "if HERO_KICK_ENABLED:\n                            handle_hero_kick(values, send, state, conn_id)",
    "handle_hero_kick(values, send, state, conn_id)\n                        if HERO_KICK_ENABLED:\n                            pass", 1)))
led.ok(arm_m2 is False,
       "KNOWN-BAD: an arm that calls handle_hero_kick BEFORE the flag check fails "
       "the lock too")

for name in ("hero_locks_release", "handle_hero_command"):
    fn = _func(TREE, name)
    calls = _calls(fn)
    led.ok("hero_slots" not in calls and "party_hero_slots" in calls,
           f"LOCK: {name} iterates party_hero_slots(state), never hero_slots() -- "
           f"a kicked hero holds no lock and takes no orders",
           f"calls {sorted(c for c in calls if 'hero_slots' in c)}")

sys.exit(led.verdict())
