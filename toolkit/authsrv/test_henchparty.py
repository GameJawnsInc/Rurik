"""The party family's henchman add, c2s 0x009F HENCHMAN_ADD -- DESKWORK-D1 step
5 (studies/cmsg/FINDINGS.md "The party family").

    python toolkit/authsrv/test_henchparty.py

WHAT THIS PINS.

  * §1 THE BATCH, against the TAPE'S OWN BYTES. henchparty.henchman_add_batch is
    pure; its two messages (0x00B0 PLAYER_PARTY_SIZE then the 0x01BF roster row)
    are encoded through the codec and compared byte for byte with the s2c
    plaintext chunks that answer the three c2s 0x009F adds on 20260819T132414
    :53419 (t=126.273/128.232/130.318, 23-byte prefixes; the tails are 0x001E
    clock ticks). The enc_name, profession and level fed to the batch are READ
    from the tape's own 0x01BF, so nothing ArenaNet authored is committed here.
    The KNOWN-BAD arm is the KICK's shape -- row before size -- through the same
    comparator, which must NOT match: size comes first for the henchman.
    Vault-gated; a missing capture declares a skip.
  * §2 THE HANDLER, driven like the hero add (test_heroadd): the real
    handle_henchman_add, a fake send, a state seeded with a hireable henchman.
    Arms: a valid add sends exactly 0x00B0 then 0x01BF and no 0x0021 (the
    standing NPC is not destroyed); the size counts the player + the henchman;
    refusals (not hireable, already in the party, over the map cap) send
    NOTHING; a second henchman fills toward the cap and the one past it is
    refused; the cap counts heroes too.
  * §3 THE SPAWN WIRING: spawn_population over the shipped `outpost_henchmen`
    rows sends 0x0071 for each and records state["hireable_henchmen"] -- so the
    add has something to hire -- and does NOT mark a non-hireable row. Under
    --no-henchman-add no 0x0071 goes out.
  * §4 SOURCE LOCKS on authsrv.py (syntax tree): the 0x009F arm calls
    handle_henchman_add only under HENCHMAN_ADD_ENABLED; main() wires
    --no-henchman-add and --henchman-cap; spawn_population's hireable arm is
    gated on HENCHMAN_ADD_ENABLED; and 0x009F is OFF the DROPPED_ON_PURPOSE
    allowlist (its arm landed). Each lock has a mutation that reddens it.

handle_henchman_add and spawn_population need the server, so this drives the real
functions with a fake send and a scratch state, like test_herokick.py. Floor set
from the green run below.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
if os.path.join(os.path.dirname(HERE), "schema") not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks                                                # noqa: E402
import codec as codecmod                                     # noqa: E402
import henchparty                                            # noqa: E402
import authsrv                                               # noqa: E402
import livewire                                              # noqa: E402

led = checks.Ledger("henchman add (DESKWORK-D1 step 5)", floor=27)

COD = codecmod.Codec()
SRC_PATH = os.path.join(HERE, "authsrv.py")
with open(SRC_PATH, encoding="utf-8") as _fh:
    SRC = _fh.read()
TREE = ast.parse(SRC)

CAPTURE = "20260819T132414"
CONN = "game-10.0.0.210_53419-to-34.196.135.145_80.jsonl"
# (reply time, party, player, size, agent) for the three adds -- OBSERVED.
ADDS = [(126.273, 11, 14, 2, 4), (128.232, 11, 14, 3, 2), (130.318, 11, 14, 4, 6)]


def encode_batch(batch):
    return b"".join(COD.encode("GAME_SMSG", op, vals) for op, vals, _l in batch)


# -- §1 the batch, byte for byte against the tape ----------------------------
import tape as tapemod                                        # noqa: E402
capdir = os.path.join(livewire.captures_root(), CAPTURE)
if os.path.exists(os.path.join(capdir, CONN)):
    _c, events, err = livewire.build_events(capdir, CONN, "s2c")
    led.ok(err is None and events,
           f"the tape's s2c stream closes ({CAPTURE} {CONN[:24]})",
           f"err {err}")
    for tt, party, player, size, agent in ADDS:
        chunk = next((p for t, p in (events or []) if abs(t - tt) < 0.004), None)
        if chunk is None:
            led.skip(f"§1 add at t={tt}", "chunk not found")
            continue
        msgs, _r = tapemod.decode_all([(tt, chunk)], COD, channel="GAME_SMSG",
                                      mask=0, strict=False)
        row = next((v for _t, op, v in msgs if op == 0x01BF), None)
        led.ok(row is not None and row[1] == party and row[2] == agent,
               f"t={tt}: the tape's 0x01BF is [party {party}, agent {agent}, ...]",
               f"{row}")
        # decoded row = [opcode, party, agent, enc_name, profession, level]
        enc, prof, level = row[3], row[4], row[5]
        batch = henchparty.henchman_add_batch(party, player, size, agent,
                                              enc, prof, level)
        ops = [op for op, _v, _l in batch]
        led.ok(ops == [0x00B0, 0x01BF],
               f"t={tt}: the batch is 0x00B0 then 0x01BF (size before row)",
               f"{[hex(o) for o in ops]}")
        wire = encode_batch(batch)
        led.ok(len(wire) == 23 and chunk[:23] == wire,
               f"t={tt}: henchman_add_batch encodes to the tape's 23 bytes, byte "
               f"for byte", f"ours {wire.hex()} tape {chunk[:23].hex()}")
        # KNOWN-BAD: the KICK's shape (row before size) does NOT match.
        bad = encode_batch([batch[1], batch[0]])
        led.ok(bad != chunk[:23],
               f"t={tt}: KNOWN-BAD row-before-size does NOT match the tape")
else:
    led.skip("§1 tape replay", f"{CAPTURE} {CONN} not in the vault")


# -- §2 the real handler -----------------------------------------------------
def fake_send():
    sent = []
    return sent, (lambda op, vals, label=None: sent.append((op, list(vals))))


def ops_of(sent):
    return [op for op, _v in sent]


_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "HENCHMAN", "PLAYER_NUMBER", "HENCHMAN_ADD_ENABLED",
           "OUTPOST_PARTY_CAP")}
try:
    authsrv.HERO_IDS = []
    authsrv.HENCHMAN = None
    authsrv.PLAYER_NUMBER = 14
    authsrv.HENCHMAN_ADD_ENABLED = True
    authsrv.OUTPOST_PARTY_CAP = 4

    def seeded(agents_map):
        return {"agents": {}, "hireable_henchmen": dict(agents_map)}

    HENCH = {4: {"enc_name": "AAAA", "profession": 2, "level": 3, "name": "R"},
             2: {"enc_name": "BBBB", "profession": 1, "level": 3, "name": "W"},
             6: {"enc_name": "CCCC", "profession": 7, "level": 3, "name": "A"}}

    # (a) a valid add: 0x00B0 then 0x01BF, size = player + this henchman = 2,
    #     no 0x0021 (the standing NPC is not destroyed).
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 4], send, st, 0)
    led.ok(ops_of(sent) == [0x00B0, 0x01BF],
           "(a) a valid add sends exactly 0x00B0 then 0x01BF", f"{[hex(o) for o in ops_of(sent)]}")
    b0 = next((v for op, v in sent if op == 0x00B0), None)
    led.ok(b0 == [14, 2], "(a) the size is [player 14, 2] -- player + one henchman", f"{b0}")
    bf = next((v for op, v in sent if op == 0x01BF), None)
    # sent values = [party, agent, enc_name, profession, level]
    led.ok(bf is not None and bf[0] == 1 and bf[1] == 4 and bf[3] == 2 and bf[4] == 3,
           "(a) the roster row is [party 1, agent 4, name, prof 2, level 3]", f"{bf}")
    led.ok(0x0021 not in ops_of(sent) and 4 in st["party_henchmen"],
           "(a) no 0x0021: the standing NPC is kept and recorded in the party")

    # (b) not hireable: nothing sent.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 99], send, st, 0)
    led.ok(sent == [] and not st.get("party_henchmen"),
           "(b) an agent that is not a hireable henchman is refused, nothing sent")

    # (c) already in the party: nothing sent the second time.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 4], send, st, 0)
    n1 = len(sent)
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 4], send, st, 0)
    led.ok(len(sent) == n1 and len(st["party_henchmen"]) == 1,
           "(c) a henchman already in the party is refused, nothing more sent")

    # (d) the cap: three henchmen fill 1 player -> 4, the fourth is refused.
    sent, send = fake_send()
    st = seeded(HENCH)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, a], send, st, 0)
    led.ok(len(st["party_henchmen"]) == 3 and ops_of(sent) == [0x00B0, 0x01BF] * 3,
           "(d) three adds fill the party (1 player + 3 = cap 4), six messages", f"{len(st['party_henchmen'])}")
    b0s = [v[1] for op, v in sent if op == 0x00B0]
    led.ok(b0s == [2, 3, 4], "(d) the size climbs 2, 3, 4 across the three adds", f"{b0s}")
    # a fourth hireable henchman over the cap is refused.
    st["hireable_henchmen"][8] = {"enc_name": "DDDD", "profession": 3, "level": 3, "name": "M"}
    sent2, send2 = fake_send()
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 8], send2, st, 0)
    led.ok(sent2 == [] and 8 not in st["party_henchmen"],
           "(d) a henchman over the cap is refused, nothing sent")

    # (d') the cap counts HEROES too -- one hero + two henchmen = 4, a third refused.
    authsrv.HERO_IDS = [6]
    sent, send = fake_send()
    st = seeded(HENCH)
    for a in (4, 2):
        authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, a], send, st, 0)
    led.ok(len(st["party_henchmen"]) == 2,
           "(d') with one hero owned, two henchmen reach the cap of 4 (player + hero + 2)")
    sent3, send3 = fake_send()
    authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 6], send3, st, 0)
    led.ok(sent3 == [],
           "(d') the third henchman is refused because the hero counts against the cap")
    authsrv.HERO_IDS = []

    # KNOWN-BAD (the flag): with HENCHMAN_ADD_ENABLED off the dispatch arm never
    # calls the handler -- checked as a source lock in §4; here the cap check
    # itself: party_is_full is what refuses, so a wrong comparison would let the
    # over-cap add through.
    led.ok(henchparty.party_is_full(4, 4) and not henchparty.party_is_full(3, 4),
           "party_is_full: 4/4 full, 3/4 not -- the boundary the cap refuses on")

    # -- §3 the spawn wiring -------------------------------------------------
    class _Mesh:
        def walkable(self, x, y):
            return True

    def _place_all(pm, x, y, what):
        return (x, y, False)

    _saved_place = authsrv.place_on_mesh
    _saved_area = authsrv.AREA_NAME
    try:
        authsrv.place_on_mesh = _place_all
        authsrv.AREA_NAME = "outpost_henchmen"
        sent, send = fake_send()
        st = {"agents": {}, "map_id": 148, "pathmap": _Mesh()}
        authsrv.spawn_population(send, st, (9826.0, 8077.0, 0), 0)
        marks = [v[0] for op, v in sent if op == henchparty.HENCHMAN_HIREABLE]
        led.ok(sorted(marks) == [31, 32, 33],
               "(§3) spawn_population marks the three outpost henchmen hireable "
               "(0x0071 for agents 31, 32, 33)", f"{sorted(marks)}")
        led.ok(sorted(st.get("hireable_henchmen") or {}) == [31, 32, 33]
               and all("enc_name" in r for r in st["hireable_henchmen"].values()),
               "(§3) and records each with its enc_name/profession/level for 0x01BF")
        # and the recorded professions match the content (W1/R2/A7).
        profs = {a: r["profession"] for a, r in st["hireable_henchmen"].items()}
        led.ok(profs == {31: 1, 32: 2, 33: 7},
               "(§3) the recorded professions are the content's (31 W, 32 R, 33 A)", f"{profs}")
        # a real add of a spawned henchman produces a valid batch.
        sent2, send2 = fake_send()
        authsrv.handle_henchman_add([authsrv.GAME_CMSG_HENCHMAN_ADD, 31], send2, st, 0)
        led.ok(ops_of(sent2) == [0x00B0, 0x01BF],
               "(§3) hiring a spawned henchman (agent 31) sends the add batch")

        # KNOWN-BAD: with the flag off, no 0x0071 goes out.
        authsrv.HENCHMAN_ADD_ENABLED = False
        sent3, send3 = fake_send()
        st3 = {"agents": {}, "map_id": 148, "pathmap": _Mesh()}
        authsrv.spawn_population(send3, st3, (9826.0, 8077.0, 0), 0)
        led.ok(henchparty.HENCHMAN_HIREABLE not in ops_of(sent3)
               and not st3.get("hireable_henchmen"),
               "(§3) KNOWN-BAD: --no-henchman-add marks nothing hireable")
        authsrv.HENCHMAN_ADD_ENABLED = True
    finally:
        authsrv.place_on_mesh = _saved_place
        authsrv.AREA_NAME = _saved_area
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)


# -- §4 source locks ---------------------------------------------------------
def _func(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef,)) and n.name == name:
            return n
    return None


def _seg(node):
    return ast.get_source_segment(SRC, node) if node else ""


# the dispatch arm calls handle_henchman_add only under HENCHMAN_ADD_ENABLED.
# (the call text appears in the def line too, so anchor on the arm.)
_arm_at = SRC.find("elif opcode == GAME_CMSG_HENCHMAN_ADD:")
_arm_txt = SRC[_arm_at:_arm_at + 400] if _arm_at >= 0 else ""
led.ok(_arm_at >= 0
       and "if HENCHMAN_ADD_ENABLED:" in _arm_txt
       and "handle_henchman_add(values, send, state, conn_id)" in _arm_txt
       and SRC.count("def handle_henchman_add(") == 1,
       "LOCK: the 0x009F arm exists, is gated on HENCHMAN_ADD_ENABLED, and calls "
       "the handler once")

# main() wires --no-henchman-add and --henchman-cap.
main_fn = _func(TREE, "main")
main_src = _seg(main_fn)
led.ok("a.no_henchman_add" in main_src and "HENCHMAN_ADD_ENABLED = False" in main_src,
       "LOCK: main() reads --no-henchman-add and turns the arm off")
led.ok("a.henchman_cap" in main_src and "OUTPOST_PARTY_CAP = int(a.henchman_cap)" in main_src,
       "LOCK: main() reads --henchman-cap and overrides the cap")

# spawn_population's hireable arm is gated on HENCHMAN_ADD_ENABLED and sends the mark.
spawn_src = _seg(_func(TREE, "spawn_population"))
led.ok('row.get("hireable") and HENCHMAN_ADD_ENABLED' in spawn_src
       and "henchparty.hireable_mark(" in spawn_src
       and 'state.setdefault("hireable_henchmen"' in spawn_src,
       "LOCK: spawn_population marks a hireable row (gated on the flag) and "
       "records it")

# the handler refuses through party_is_full and party_member_count.
add_src = _seg(_func(TREE, "handle_henchman_add"))
led.ok("henchparty.party_is_full(party_member_count(state), OUTPOST_PARTY_CAP)" in add_src
       and 'state.setdefault("party_henchmen"' in add_src,
       "LOCK: handle_henchman_add caps on party_member_count vs OUTPOST_PARTY_CAP "
       "and records the party henchman")

# 0x009F is OFF the allowlist (its arm landed).
import test_dispatch                                          # noqa: E402
led.ok(0x009F not in test_dispatch.DROPPED_ON_PURPOSE,
       "LOCK: 0x009F HENCHMAN_ADD is off DROPPED_ON_PURPOSE -- a handled opcode "
       "on the allowlist would silently re-permit the drop (test_dispatch section 7)")

sys.exit(led.verdict())
