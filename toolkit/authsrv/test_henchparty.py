"""The party family's henchman add, c2s 0x009F HENCHMAN_ADD -- DESKWORK-D1 step
5 (studies/cmsg/FINDINGS.md "The party family"), and the ONE party count the hero
kick and hero add share with it since the fix pass.

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
    Vault-gated; a missing capture declares a skip (13 checks, outside the floor).
  * §2 THE HANDLERS, driven like the hero add (test_heroadd): the real
    handle_henchman_add, handle_hero_kick and handle_hero_add, a fake send, a
    state seeded with hireable henchmen. Arms: a valid add sends exactly 0x00B0
    then 0x01BF and no 0x0021 (the standing NPC is seeded into state["agents"]
    and is still there after -- a destroy would have to go through
    remove_agent, which the empty-agents version of this check could not see);
    refusals (not hireable, already in the party, over the cap) send NOTHING;
    a second henchman fills toward the cap and the one past it is refused; the
    cap counts heroes. THE FIX PASS'S CASES (HENCH-EVR-1 / ENG-HENCH-1): with a
    hero and two hired henchmen in the party, the hero KICK's 0x00B0 says 3 --
    the landing's own sum (1 + henchman + heroes) said 1 and is run here as the
    KNOWN-BAD value; the hero ADD back says 4; and a hero add into a party the
    henchmen filled to the cap is REFUSED, with the same add accepted under a
    raised cap so the refusal is the cap's. The two ACCEPTING hero adds need
    the hero character block, which reads the vault's attribute-cost rows
    (attribspend), so on a bare machine they declare a skip (2 checks, outside
    the floor). Under --party-size-no-heroes the henchman add's 0x00B0 leaves
    the hero out as the load does while the cap still counts it (HENCH-EVR-11 /
    ENG-HENCH-11). The three opcode constants henchparty names are locked equal
    to authsrv's (ENG-HENCH-9).
  * §3 THE SPAWN WIRING: spawn_population over the shipped `outpost_henchmen`
    rows sends, for each hireable row and BEFORE its 0x0020 create, the
    displayed level (0x009F [36, agent, 3]) then 0x0071 -- retail's position
    (EVR-5 / ENG-6) -- and records state["hireable_henchmen"] so the add has
    something to hire. Under --no-henchman-add nothing is marked; in a FIELD
    (--explorable) the bodies are created but neither message goes out
    (retail marks henchmen in outposts only, 11 of 96 live connections, all
    outposts -- ENG-HENCH-11).
  * §4 SOURCE LOCKS on authsrv.py, EACH WITH A MUTATION THAT REDDENS IT (the
    landing claimed mutations it did not carry -- HENCH-EVR-3 / ENG-HENCH-8):
    the 0x009F arm is gated on HENCHMAN_ADD_ENABLED; main() wires
    --no-henchman-add and --henchman-cap (refusing N < 1); spawn_population's
    hireable arm is flag-gated, sends hireable_bringup and skips a field;
    handle_henchman_add caps on party_member_count vs OUTPOST_PARTY_CAP and
    sizes through party_size_on_wire; handle_hero_kick and handle_hero_add size
    through party_size_on_wire (the old sum is the mutation) and the hero add
    refuses at the same cap; party_size_on_wire reads PARTY_SIZE_COUNTS_HEROES;
    0x009F is OFF the DROPPED_ON_PURPOSE allowlist (its arm landed; the
    mutation puts it back in memory). The source is parsed ONCE; each mutation
    edits the extracted function's text, so the lock is re-run on the text it
    would see.

  * THE KICK (CLEANUP-3, 2026-09-24; henchparty.py THE KICK): §1k the batch
    `henchman_kick_batch` is 0x01C0 [party, agent] THEN 0x00B0 -- row before
    size, the hero kick's shape, RECONSTRUCTION (no tape carries it), encoded
    through the codec to the schema's 6 + 5 bytes; the KNOWN-BAD arm is the
    add's size-then-row through the same encoder; the builder refuses agent 0
    and party 0 (0 means 'the own party' to the client's worker). §2 (g)-(k)
    the real `handle_henchman_kick`: a hired henchman's kick sends exactly
    0x01C0 [1, agent] then 0x00B0, the henchman leaves the party, the standing
    NPC stays (no 0x0021), stays hireable and can be re-added; six refusals
    (never hired, a stranger, malformed, a hero's agent, zero, a non-int) and a
    second kick send NOTHING; with a hero and two henchmen (4 of 4) a kick's
    0x00B0 says 3 and the freed slot takes the third henchman; under
    --party-size-no-heroes the kick's 0x00B0 leaves the hero out while the cap
    counts it; under --persist with an opaque store attached the handler
    touches it not at all (the hire is not persisted, so neither is the kick).
    §4 locks: the 0x00A8 arm gated on HENCHMAN_KICK_ENABLED; main() wires
    --no-henchman-kick through a `global`; handle_henchman_kick refuses through
    kick_refusal, pops the party, sizes through party_size_on_wire and sends
    henchman_kick_batch, and names no store; serverargs.py declares the flag;
    0x00A8 is OFF the DROPPED_ON_PURPOSE allowlist; the leaf's 0x01C0 equals
    authsrv's. Each lock with a mutation that reddens it.

Floor = the bare-machine core, measured with RURIK_VAULT pointed at an empty
directory (§1 and the two accepting hero adds declare skips there); the vault
adds 15.
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

led = checks.Ledger("henchman add (DESKWORK-D1 step 5)", floor=79)   # 2026-09-24 (CLEANUP-3, the kick): the bare-machine core from the green run with RURIK_VAULT pointed at an empty directory (49 before; +30: the kick batch and its refusals, the handler's (g)-(k), the locks and their mutations); the vault adds 15 (94 vaulted)

COD = codecmod.Codec()
SRC_PATH = os.path.join(HERE, "authsrv.py")
with open(SRC_PATH, encoding="utf-8") as _fh:
    SRC = _fh.read()

CAPTURE = "20260819T132414"
CONN = "game-10.0.0.210_53419-to-34.196.135.145_80.jsonl"
# (reply time, party, player, size, agent) for the three adds -- OBSERVED.
ADDS = [(126.273, 11, 14, 2, 4), (128.232, 11, 14, 3, 2), (130.318, 11, 14, 4, 6)]
UUID = "11111111111111111111111111111111"


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


# -- §1k the KICK batch (bare-machine: no tape carries it) -------------------
kb = henchparty.henchman_kick_batch(1, 14, 1, 4)
led.ok([op for op, _v, _l in kb] == [0x01C0, 0x00B0] and kb[0][1] == [1, 4] and kb[1][1] == [14, 1]
       and "RECONSTRUCTION" in kb[0][2],
       "(§1k) the kick batch is 0x01C0 [party 1, agent 4] THEN 0x00B0 [player 14, size 1] -- row "
       "before size, the hero kick's shape, labelled RECONSTRUCTION (no tape carries it)",
       f"{[(hex(o), v) for o, v, _l in kb]}")
wire_k = encode_batch(kb)
led.ok(len(wire_k) == 11 and wire_k[:6] == bytes.fromhex("c001" "0100" "0400")
       and wire_k[6:] == bytes.fromhex("b000" "0e00" "01"),
       "(§1k) ...it encodes through the codec: 0x01C0 is the schema's 6 bytes (header + two words) "
       "and 0x00B0 its 5 (header + word + byte), 11 in all", f"{wire_k.hex()}")
led.ok(encode_batch([kb[1], kb[0]]) != wire_k,
       "(§1k) KNOWN-BAD: the add's shape (size before row) through the same encoder differs")
for bad_args in ((1, 14, 1, 0), (0, 14, 1, 4), (1, 14, 1, -3)):
    try:
        henchparty.henchman_kick_batch(*bad_args)
        led.ok(False, f"(§1k) henchman_kick_batch{bad_args} is refused")
    except ValueError:
        led.ok(True, f"(§1k) henchman_kick_batch{bad_args} is refused (agent 0 / party 0 / a negative "
                     f"agent: 0 means 'the own party' to the client's worker, not our declared id)")
led.ok(henchparty.kick_refusal({4: {}}, 4) is None
       and henchparty.kick_refusal({4: {}}, 2) is not None
       and henchparty.kick_refusal({}, 4) is not None
       and henchparty.kick_refusal({4: {}}, 0) is not None
       and henchparty.kick_refusal({4: {}}, "x") is not None
       and henchparty.kick_refusal(None, 4) is not None,
       "(§1k) kick_refusal: a hired henchman passes; an unhired agent, an empty party, zero, a "
       "non-int and no party at all are each refused with a reason")


# -- §2 the real handlers ----------------------------------------------------
def fake_send():
    sent = []
    return sent, (lambda op, vals, label=None: sent.append((op, list(vals))))


def ops_of(sent):
    return [op for op, _v in sent]


def sizes_of(sent):
    return [v[1] for op, v in sent if op == 0x00B0]


def hero_add_or_skip(what, send, state):
    """handle_hero_add's ACCEPTING path builds the hero character block, which
    reads the vault's attribute-cost rows; on a bare machine attribspend
    refuses to invent a cost curve. Returns True when the add ran."""
    try:
        authsrv.handle_hero_add([HADD, 6], send, state, 0)
        return True
    except ValueError as exc:
        if "attribute cost rows" not in str(exc):
            raise
        # the handler discards the kick BEFORE it builds the block, so put the
        # state back where the caller left it (hero 6 kicked, nothing sent).
        authsrv.kicked_heroes_set(state).add(6)
        led.skip(what, "no attribute cost rows in vault/content (bare machine)")
        return False


ADD, KICK = authsrv.GAME_CMSG_HENCHMAN_ADD, authsrv.GAME_CMSG_HERO_KICK
HADD = authsrv.GAME_CMSG_HERO_ADD
KICKH = authsrv.GAME_CMSG_HENCHMAN_KICK

_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "HENCHMAN", "PLAYER_NUMBER", "HENCHMAN_ADD_ENABLED", "HENCHMAN_KICK_ENABLED",
           "OUTPOST_PARTY_CAP", "PARTY_SIZE_COUNTS_HEROES", "HERO_AGENT_ID",
           "PERSIST", "HERO_KICK_ENABLED", "HERO_ADD_ENABLED", "RESET_HERO_KICKS",
           "PARTY_COMMANDS", "HERO_BAGS", "HERO_INVENTORY", "HERO_CHAR",
           "HERO_BODY", "EXPLORABLE", "OUTPOST", "PARTY_BODY_IN_OUTPOST",
           "HERO_RIG_RETAIL", "HERO_ACTIVATE")}
try:
    authsrv.HERO_IDS = []
    authsrv.HENCHMAN = None
    authsrv.PLAYER_NUMBER = 14
    authsrv.HENCHMAN_ADD_ENABLED = True
    authsrv.HENCHMAN_KICK_ENABLED = True
    authsrv.OUTPOST_PARTY_CAP = 4
    authsrv.PARTY_SIZE_COUNTS_HEROES = True
    # the commander rig the hero kick/add are armed for (test_heroadd's own
    # setup): a town, no bags, no body.
    authsrv.HERO_AGENT_ID = 200
    authsrv.PERSIST = False
    authsrv.HERO_KICK_ENABLED, authsrv.HERO_ADD_ENABLED = True, True
    authsrv.RESET_HERO_KICKS = False
    authsrv.PARTY_COMMANDS = True
    authsrv.HERO_BAGS, authsrv.HERO_INVENTORY, authsrv.HERO_CHAR = False, 0, False
    authsrv.HERO_BODY = False
    authsrv.EXPLORABLE, authsrv.OUTPOST, authsrv.PARTY_BODY_IN_OUTPOST = False, False, False
    authsrv.HERO_RIG_RETAIL, authsrv.HERO_ACTIVATE = True, True

    HENCH = {4: {"enc_name": "AAAA", "profession": 2, "level": 3, "name": "R"},
             2: {"enc_name": "BBBB", "profession": 1, "level": 3, "name": "W"},
             6: {"enc_name": "CCCC", "profession": 7, "level": 3, "name": "A"}}

    def seeded(agents_map, **more):
        # the standing NPCs ARE in the world, so a destroy would have to go
        # through remove_agent and show as 0x0021 (or raise).
        st = {"agents": {a: {"name": r["name"]} for a, r in agents_map.items()},
              "hireable_henchmen": dict(agents_map), "char_uuid": UUID}
        st.update(more)
        return st

    # (a) a valid add: 0x00B0 then 0x01BF, size = player + this henchman = 2,
    #     no 0x0021 and the standing NPC still in the world.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    led.ok(ops_of(sent) == [0x00B0, 0x01BF],
           "(a) a valid add sends exactly 0x00B0 then 0x01BF", f"{[hex(o) for o in ops_of(sent)]}")
    led.ok(sizes_of(sent) == [2], "(a) the size is [player 14, 2] -- player + one henchman",
           f"{sizes_of(sent)}")
    bf = next((v for op, v in sent if op == 0x01BF), None)
    # sent values = [party, agent, enc_name, profession, level]
    led.ok(bf is not None and bf[0] == 1 and bf[1] == 4 and bf[3] == 2 and bf[4] == 3,
           "(a) the roster row is [party 1, agent 4, name, prof 2, level 3]", f"{bf}")
    led.ok(0x0021 not in ops_of(sent) and 4 in st["agents"] and 4 in st["party_henchmen"],
           "(a) no 0x0021: the standing NPC (seeded in state[agents]) is still in the "
           "world and recorded in the party")

    # (b) not hireable: nothing sent.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 99], send, st, 0)
    led.ok(sent == [] and not st.get("party_henchmen"),
           "(b) an agent that is not a hireable henchman is refused, nothing sent")

    # (c) already in the party: nothing sent the second time.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    n1 = len(sent)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    led.ok(len(sent) == n1 and len(st["party_henchmen"]) == 1,
           "(c) a henchman already in the party is refused, nothing more sent")

    # (d) the cap: three henchmen fill 1 player -> 4, the fourth is refused.
    sent, send = fake_send()
    st = seeded(HENCH)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([ADD, a], send, st, 0)
    led.ok(len(st["party_henchmen"]) == 3 and ops_of(sent) == [0x00B0, 0x01BF] * 3,
           "(d) three adds fill the party (1 player + 3 = cap 4), six messages", f"{len(st['party_henchmen'])}")
    led.ok(sizes_of(sent) == [2, 3, 4], "(d) the size climbs 2, 3, 4 across the three adds",
           f"{sizes_of(sent)}")
    st["hireable_henchmen"][8] = {"enc_name": "DDDD", "profession": 3, "level": 3, "name": "M"}
    st["agents"][8] = {"name": "M"}
    sent2, send2 = fake_send()
    authsrv.handle_henchman_add([ADD, 8], send2, st, 0)
    led.ok(sent2 == [] and 8 not in st["party_henchmen"],
           "(d) a henchman over the cap is refused, nothing sent")

    # (d') the cap counts HEROES too -- one hero + two henchmen = 4, a third refused.
    authsrv.HERO_IDS = [6]
    sent, send = fake_send()
    st = seeded(HENCH)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], send, st, 0)
    led.ok(len(st["party_henchmen"]) == 2 and sizes_of(sent) == [3, 4],
           "(d') with one hero in the party, two henchmen reach the cap of 4 and the "
           "sizes say 3, 4 (player + hero + henchmen)", f"{sizes_of(sent)}")
    sent3, send3 = fake_send()
    authsrv.handle_henchman_add([ADD, 6], send3, st, 0)
    led.ok(sent3 == [],
           "(d') the third henchman is refused because the hero counts against the cap")

    # (e) THE FIX PASS: the hero kick and add count the hired henchmen.
    #     Party = player + hero 6 + henchmen 4 and 2 (4 of 4).
    stk = seeded(HENCH)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], stk, 0)
    sk, sendk = fake_send()
    authsrv.handle_hero_kick([KICK, 6], sendk, stk, 0)
    led.ok(sizes_of(sk) == [3] and authsrv.party_member_count(stk) == 3,
           "(e) kicking the hero with two hired henchmen in the party: 0x00B0 says 3 "
           "(player + 2 henchmen)", f"sizes {sizes_of(sk)} count {authsrv.party_member_count(stk)}")
    # KNOWN-BAD: the landing's own sum at the kick site -- the value it sent.
    _old_sum = 1 + (1 if authsrv.HENCHMAN is not None else 0) + len(authsrv.party_hero_slots(stk))
    led.ok(_old_sum == 1 and _old_sum != sizes_of(sk)[0],
           "(e) KNOWN-BAD: the pre-fix sum `1 + henchman + heroes` is 1 here -- two "
           "members short of what the kick now sends", f"old {_old_sum}")
    sa, senda = fake_send()
    if hero_add_or_skip("(e) the hero re-added with two henchmen: 0x00B0 = 4", senda, stk):
        led.ok(0x01C2 in ops_of(sa) and sizes_of(sa) == [4]
               and authsrv.party_member_count(stk) == 4,
               "(e) re-adding the hero: 0x00B0 says 4 (player + hero + 2 henchmen) and "
               "the 0x01C2 row goes out", f"sizes {sizes_of(sa)} ops {[hex(o) for o in ops_of(sa)]}")
        authsrv.handle_hero_kick([KICK, 6], fake_send()[1], stk, 0)
    # the hero is kicked (count 3); hire the third henchman (count 4 = cap);
    # a re-add is REFUSED before the block, so this runs bare too.
    authsrv.handle_henchman_add([ADD, 6], fake_send()[1], stk, 0)
    sr, sendr = fake_send()
    authsrv.handle_hero_add([HADD, 6], sendr, stk, 0)
    led.ok(sr == [] and authsrv.hero_kicked(stk, 6)
           and authsrv.party_member_count(stk) == 4,
           "(e) a hero add into a party the henchmen filled to the cap (player + 3 = "
           "4 of 4) is REFUSED: nothing sent, the hero stays kicked, the count stays 4",
           f"ops {[hex(o) for o in ops_of(sr)]} count {authsrv.party_member_count(stk)}")
    # vacuity: the same add under a raised cap goes through, so the refusal
    # above was the cap's and not another gate's.
    authsrv.OUTPOST_PARTY_CAP = 8
    sv, sendv = fake_send()
    if hero_add_or_skip("(e) VACUITY GUARD: the same hero add under --henchman-cap 8", sendv, stk):
        led.ok(0x01C2 in ops_of(sv) and sizes_of(sv) == [5],
               "(e) VACUITY GUARD: the same hero add under --henchman-cap 8 goes through "
               "with 0x00B0 = 5, so the refusal was the cap's", f"sizes {sizes_of(sv)}")
    authsrv.OUTPOST_PARTY_CAP = 4

    # (f) --party-size-no-heroes: the WIRE size leaves the hero out as the load's
    #     does; the CAP still counts it.
    authsrv.PARTY_SIZE_COUNTS_HEROES = False
    sf, sendf = fake_send()
    stf = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], sendf, stf, 0)
    led.ok(sizes_of(sf) == [2] and authsrv.party_member_count(stf) == 3,
           "(f) --party-size-no-heroes: the henchman add's 0x00B0 says 2 (player + "
           "henchman, the hero left out as at load) while the count is 3",
           f"sizes {sizes_of(sf)} count {authsrv.party_member_count(stf)}")
    authsrv.handle_henchman_add([ADD, 2], sendf, stf, 0)
    led.ok(sizes_of(sf) == [2, 3], "(f) ...and 3 after the second", f"{sizes_of(sf)}")
    sf2, sendf2 = fake_send()
    authsrv.handle_henchman_add([ADD, 6], sendf2, stf, 0)
    led.ok(sf2 == [] and authsrv.party_member_count(stf) == 4,
           "(f) ...and the third is refused: the cap counts the hero whatever the "
           "wire size said (4 of 4)")
    authsrv.PARTY_SIZE_COUNTS_HEROES = True
    authsrv.HERO_IDS = []

    # (g) THE KICK (CLEANUP-3): hire 4, kick 4 -> 0x01C0 [1, 4] then 0x00B0 [14, 1];
    #     the henchman out of the party, the NPC still standing and hireable, re-addable.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    sent.clear()
    authsrv.handle_henchman_kick([KICKH, 4], send, st, 0)
    led.ok(ops_of(sent) == [0x01C0, 0x00B0] and sent[0][1] == [1, 4] and sizes_of(sent) == [1],
           "(g) kicking the hired henchman sends exactly 0x01C0 [party 1, agent 4] then 0x00B0 "
           "[player 14, 1] -- row then size, the hero kick's shape (RECONSTRUCTION)",
           f"{[(hex(o), v) for o, v in sent]}")
    led.ok(4 not in st["party_henchmen"] and 4 in st["agents"] and 4 in st["hireable_henchmen"]
           and 0x0021 not in ops_of(sent) and authsrv.party_member_count(st) == 1,
           "(g) ...the henchman leaves the party (count 1), the standing NPC stays in the world "
           "(no 0x0021) and stays hireable")
    sent.clear()
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    led.ok(ops_of(sent) == [0x00B0, 0x01BF] and sizes_of(sent) == [2] and 4 in st["party_henchmen"],
           "(g) ...and can be hired again: the add goes through, size 2", f"{sizes_of(sent)}")

    # (h) refusals send NOTHING and leave the party alone.
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    n = len(sent)
    authsrv.handle_henchman_kick([KICKH, 2], send, st, 0)        # hireable, never hired
    authsrv.handle_henchman_kick([KICKH, 99], send, st, 0)       # a stranger
    authsrv.handle_henchman_kick([KICKH], send, st, 0)           # malformed: no word
    authsrv.handle_henchman_kick([KICKH, 200], send, st, 0)      # the hero's agent
    authsrv.handle_henchman_kick([KICKH, 0], send, st, 0)        # zero
    authsrv.handle_henchman_kick([KICKH, "x"], send, st, 0)      # not an int
    led.ok(len(sent) == n and sorted(st["party_henchmen"]) == [4] and 2 in st["hireable_henchmen"],
           "(h) six refusals -- a hireable never hired, a stranger, a malformed request, the "
           "hero's agent, zero, a non-int -- send NOTHING and the party is untouched",
           f"sent {len(sent) - n} more")
    authsrv.handle_henchman_kick([KICKH, 4], send, st, 0)
    m = len(sent)
    authsrv.handle_henchman_kick([KICKH, 4], send, st, 0)
    led.ok(m == n + 2 and len(sent) == m and not st["party_henchmen"],
           "(h) a second kick of the same henchman is refused, nothing more sent")

    # (i) the count: a hero and two henchmen (4 of 4); kick one -> 0x00B0 says 3;
    #     the freed slot takes the third henchman.
    authsrv.HERO_IDS = [6]
    sent, send = fake_send()
    st = seeded(HENCH)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], send, st, 0)
    sent.clear()
    authsrv.handle_henchman_kick([KICKH, 4], send, st, 0)
    led.ok(sizes_of(sent) == [3] and authsrv.party_member_count(st) == 3,
           "(i) with a hero and two henchmen (4 of 4), kicking one henchman: 0x00B0 says 3 "
           "(player + hero + 1) -- the ONE count", f"sizes {sizes_of(sent)}")
    sent.clear()
    authsrv.handle_henchman_add([ADD, 6], send, st, 0)
    led.ok(sizes_of(sent) == [4] and authsrv.party_member_count(st) == 4,
           "(i) ...and the freed slot takes the third henchman: 4 of 4 again", f"{sizes_of(sent)}")
    # (j) --party-size-no-heroes: the kick's wire size leaves the hero out, the cap counts it.
    authsrv.PARTY_SIZE_COUNTS_HEROES = False
    sent.clear()
    authsrv.handle_henchman_kick([KICKH, 2], send, st, 0)
    led.ok(sizes_of(sent) == [2] and authsrv.party_member_count(st) == 3,
           "(j) --party-size-no-heroes: the kick's 0x00B0 says 2 (player + one henchman, the "
           "hero left out as at load) while the count is 3", f"sizes {sizes_of(sent)}")
    authsrv.PARTY_SIZE_COUNTS_HEROES = True
    authsrv.HERO_IDS = []
    # (k) not persisted: under --persist with an OPAQUE store attached, the handler
    #     touches it not at all (any method call would raise AttributeError).
    authsrv.PERSIST = True
    sent, send = fake_send()
    st = seeded(HENCH, charstore_game=object())
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    sent.clear()
    authsrv.handle_henchman_kick([KICKH, 4], send, st, 0)
    led.ok(ops_of(sent) == [0x01C0, 0x00B0] and not st["party_henchmen"],
           "(k) under --persist with a store attached the kick writes nothing to it (an opaque "
           "object would raise): the hire is not persisted, so neither is the kick")
    authsrv.PERSIST = False

    led.ok(henchparty.party_is_full(4, 4) and not henchparty.party_is_full(3, 4),
           "party_is_full: 4/4 full, 3/4 not -- the boundary the cap refuses on")
    led.ok(authsrv.GAME_SMSG_PARTY_HENCHMAN_HIREABLE == henchparty.HENCHMAN_HIREABLE == 0x0071
           and authsrv.GAME_SMSG_PLAYER_PARTY_SIZE == henchparty.PLAYER_PARTY_SIZE == 0x00B0
           and authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT == henchparty.AGENT_PROPERTY_UPDATE_INT == 0x009F
           and authsrv.GAME_SMSG_PARTY_HENCHMAN_REMOVE == henchparty.PARTY_HENCHMAN_REMOVE == 0x01C0
           and authsrv.GAME_CMSG_HENCHMAN_KICK == 0x00A8,
           "the leaf's four opcode constants equal authsrv's (one value per opcode, "
           "0x0071 / 0x00B0 / 0x009F / 0x01C0) and the kick's c2s is 0x00A8")

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
        lv = sorted((v[1], v[2]) for op, v in sent
                    if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT and v[0] == 36)
        led.ok(lv == [(31, 3), (32, 3), (33, 3)],
               "(§3) and sends each one's displayed level, prop 36 = 3 (retail: 6 of 6 "
               "henchmen, 0 of 38 other kind-9 NPCs)", f"{lv}")

        def _idx(pred):
            return next((i for i, (op, v) in enumerate(sent) if pred(op, v)), None)
        order_ok = True
        for aid in (31, 32, 33):
            i36 = _idx(lambda op, v, a=aid: op == 0x009F and v[0] == 36 and v[1] == a)
            i71 = _idx(lambda op, v, a=aid: op == 0x0071 and v[0] == a)
            i20 = _idx(lambda op, v, a=aid: op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT and v[0] == a)
            order_ok = order_ok and None not in (i36, i71, i20) and i36 < i71 < i20
        led.ok(order_ok,
               "(§3) retail's position: for each henchman the level, then 0x0071, then "
               "its 0x0020 create (the landing sent the mark after the create)")
        led.ok(sorted(st.get("hireable_henchmen") or {}) == [31, 32, 33]
               and all("enc_name" in r for r in st["hireable_henchmen"].values()),
               "(§3) and records each with its enc_name/profession/level for 0x01BF")
        profs = {a: r["profession"] for a, r in st["hireable_henchmen"].items()}
        led.ok(profs == {31: 1, 32: 2, 33: 7},
               "(§3) the recorded professions are the content's (31 W, 32 R, 33 A)", f"{profs}")
        # a real add of a spawned henchman produces a valid batch with the level.
        sent2, send2 = fake_send()
        authsrv.handle_henchman_add([ADD, 31], send2, st, 0)
        bf2 = next((v for op, v in sent2 if op == 0x01BF), None)
        led.ok(ops_of(sent2) == [0x00B0, 0x01BF] and bf2 is not None and bf2[4] == 3 and bf2[3] == 1,
               "(§3) hiring a spawned henchman (agent 31) sends the add batch, the "
               "row's level byte 3 and profession 1 from the record", f"{bf2}")

        # KNOWN-BAD: with the flag off, no 0x0071 and no prop 36 go out.
        authsrv.HENCHMAN_ADD_ENABLED = False
        sent3, send3 = fake_send()
        st3 = {"agents": {}, "map_id": 148, "pathmap": _Mesh()}
        authsrv.spawn_population(send3, st3, (9826.0, 8077.0, 0), 0)
        led.ok(henchparty.HENCHMAN_HIREABLE not in ops_of(sent3)
               and not any(op == 0x009F and v[0] == 36 for op, v in sent3)
               and not st3.get("hireable_henchmen"),
               "(§3) KNOWN-BAD: --no-henchman-add marks nothing hireable and sends no level")
        authsrv.HENCHMAN_ADD_ENABLED = True

        # THE REGIME: a FIELD creates the bodies but marks none (retail: outposts only).
        authsrv.EXPLORABLE = True
        sent4, send4 = fake_send()
        st4 = {"agents": {}, "map_id": 148, "pathmap": _Mesh()}
        authsrv.spawn_population(send4, st4, (9826.0, 8077.0, 0), 0)
        creates4 = [v[0] for op, v in sent4 if op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT]
        led.ok(sorted(creates4) == [31, 32, 33]
               and henchparty.HENCHMAN_HIREABLE not in ops_of(sent4)
               and not any(op == 0x009F and v[0] == 36 for op, v in sent4)
               and not st4.get("hireable_henchmen"),
               "(§3) in a FIELD (--explorable) the three bodies are created but none is "
               "marked or levelled: retail offers henchmen in outposts only",
               f"creates {sorted(creates4)} ops {sorted(set(hex(o) for o in ops_of(sent4)))}")
        authsrv.EXPLORABLE = False
    finally:
        authsrv.place_on_mesh = _saved_place
        authsrv.AREA_NAME = _saved_area
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)


# -- §4 source locks, each with a mutation that reddens it -------------------
# The source is parsed ONCE (authsrv.py is ~38k lines; a parse per mutant made
# this section take two minutes). Each lock reads the extracted text of one
# function, and its mutation edits that text.
TREE = ast.parse(SRC)
FUNCS = {n.name: (ast.get_source_segment(SRC, n) or "")
         for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)
         and n.name in ("main", "spawn_population", "handle_henchman_add",
                        "handle_hero_kick", "handle_hero_add", "party_size_on_wire",
                        "handle_henchman_kick")}
with open(os.path.join(HERE, "serverargs.py"), encoding="utf-8") as _fh:
    ARGS = _fh.read()


def _mut(text, old, new):
    """`text` with the first `old` -> `new`; an absent `old` returns the text
    unchanged, and the caller's `msrc != src` check then reddens (a stale
    mutation string cannot pass as a redden)."""
    return text.replace(old, new, 1) if old in text else text


def lock_arm(src):
    at = src.find("elif opcode == GAME_CMSG_HENCHMAN_ADD:")
    arm = src[at:at + 400] if at >= 0 else ""
    return (at >= 0 and "if HENCHMAN_ADD_ENABLED:" in arm
            and "handle_henchman_add(values, send, state, conn_id)" in arm
            and src.count("def handle_henchman_add(") == 1)


def lock_main_flag(m):
    return "a.no_henchman_add" in m and "HENCHMAN_ADD_ENABLED = False" in m


def lock_main_cap(m):
    return ("a.henchman_cap" in m and "OUTPOST_PARTY_CAP = int(a.henchman_cap)" in m
            and "int(a.henchman_cap) < 1" in m)


def lock_spawn(s):
    return ('row.get("hireable") and HENCHMAN_ADD_ENABLED' in s
            and "henchparty.hireable_bringup(" in s
            and 'state.setdefault("hireable_henchmen"' in s
            and "if instance_is_field(state):" in s)


CAP_CHECK = "henchparty.party_is_full(party_member_count(state), OUTPOST_PARTY_CAP)"
OLD_SUM = "1 + (1 if HENCHMAN is not None else 0)"


def lock_hench_add(s):
    return (CAP_CHECK in s and 'state.setdefault("party_henchmen"' in s
            and "size = party_size_on_wire(state)" in s)


def lock_hero_kick(s):
    return "party_size = party_size_on_wire(state)" in s and OLD_SUM not in s


def lock_hero_add(s):
    return ("party_size = party_size_on_wire(state)" in s and OLD_SUM not in s
            and CAP_CHECK in s)


def lock_wire(s):
    return "count_heroes=PARTY_SIZE_COUNTS_HEROES" in s


def lock_allowlist(dropped):
    return 0x009F not in dropped


# THE KICK's locks (CLEANUP-3)
def lock_kick_arm(src):
    at = src.find("elif opcode == GAME_CMSG_HENCHMAN_KICK:")
    arm = src[at:at + 500] if at >= 0 else ""
    return (at >= 0 and "if HENCHMAN_KICK_ENABLED:" in arm
            and "handle_henchman_kick(values, send, state, conn_id)" in arm
            and src.count("def handle_henchman_kick(") == 1
            and "GAME_CMSG_HENCHMAN_KICK = 0x00A8" in src)


def lock_main_kick(m):
    return ("a.no_henchman_kick" in m and "HENCHMAN_KICK_ENABLED = False" in m
            and "global HENCHMAN_KICK_ENABLED" in m)


KICK_REFUSAL = "henchparty.kick_refusal(party, values[1])"
KICK_BATCH = "henchparty.henchman_kick_batch(1, PLAYER_NUMBER, size, aid)"


def lock_hench_kick(s):
    return (KICK_REFUSAL in s and "hench = party.pop(aid)" in s
            and "size = party_size_on_wire(state)" in s and KICK_BATCH in s
            and "charstore" not in s and "set_hero_kicked" not in s
            and 'state.setdefault("party_henchmen"' in s)


def lock_kick_allowlist(dropped):
    return 0x00A8 not in dropped


# the arm's gate: mutate the first "if HENCHMAN_ADD_ENABLED:" AFTER the anchor.
_at = SRC.find("elif opcode == GAME_CMSG_HENCHMAN_ADD:")
_g = SRC.find("if HENCHMAN_ADD_ENABLED:", _at) if _at >= 0 else -1
MUT_ARM = (SRC[:_g] + "if True:" + SRC[_g + len("if HENCHMAN_ADD_ENABLED:"):]) if _g >= 0 else SRC
_atk = SRC.find("elif opcode == GAME_CMSG_HENCHMAN_KICK:")
_gk = SRC.find("if HENCHMAN_KICK_ENABLED:", _atk) if _atk >= 0 else -1
MUT_KICK_ARM = (SRC[:_gk] + "if True:" + SRC[_gk + len("if HENCHMAN_KICK_ENABLED:"):]) if _gk >= 0 else SRC

M, SP, HA, HK, HD, PW, HKK = (FUNCS.get(k, "") for k in
                               ("main", "spawn_population", "handle_henchman_add",
                                "handle_hero_kick", "handle_hero_add", "party_size_on_wire",
                                "handle_henchman_kick"))
LOCKS = [
    ("the 0x00A8 arm exists, is gated on HENCHMAN_KICK_ENABLED, calls the handler once, and the "
     "constant is 0x00A8 (CLEANUP-3)",
     lock_kick_arm, SRC, [("the gate removed", MUT_KICK_ARM),
                          ("the constant renumbered", _mut(SRC, "GAME_CMSG_HENCHMAN_KICK = 0x00A8",
                                                            "GAME_CMSG_HENCHMAN_KICK = 0x00A9"))]),
    ("main() reads --no-henchman-kick and turns the arm off through a `global`",
     lock_main_kick, M,
     [("the assignment inverted", _mut(M, "HENCHMAN_KICK_ENABLED = False",
                                       "HENCHMAN_KICK_ENABLED = True")),
      ("the global dropped", _mut(M, "global HENCHMAN_KICK_ENABLED", "pass"))]),
    ("handle_henchman_kick refuses through kick_refusal, pops the party, sizes through "
     "party_size_on_wire, sends henchman_kick_batch and names no store",
     lock_hench_kick, HKK,
     [("the refusal removed", _mut(HKK, KICK_REFUSAL, "None")),
      ("the pop made a get", _mut(HKK, "hench = party.pop(aid)", "hench = party.get(aid)")),
      ("the size taken from the count", _mut(HKK, "size = party_size_on_wire(state)",
                                              "size = party_member_count(state)")),
      ("a store write added", HKK.replace("hench = party.pop(aid)",
                                          "hench = party.pop(aid)\n    "
                                          "state['charstore_game'].set_hero_kicked(0, aid)", 1))]),
]
led.ok('"--no-henchman-kick"' in ARGS and ARGS.index('"--no-henchman-kick"') > ARGS.index('"--no-henchman-add"'),
       "LOCK: serverargs.py declares --no-henchman-kick, beside --no-henchman-add")
LOCKS += [
    ("the 0x009F arm exists, is gated on HENCHMAN_ADD_ENABLED, and calls the handler once",
     lock_arm, SRC, [("the gate removed", MUT_ARM)]),
    ("main() reads --no-henchman-add and turns the arm off",
     lock_main_flag, M,
     [("the assignment inverted", _mut(M, "HENCHMAN_ADD_ENABLED = False",
                                       "HENCHMAN_ADD_ENABLED = True"))]),
    ("main() reads --henchman-cap, refuses N < 1 and overrides the cap",
     lock_main_cap, M,
     [("the override dropped", _mut(M, "OUTPOST_PARTY_CAP = int(a.henchman_cap)",
                                    "OUTPOST_PARTY_CAP = 4")),
      ("the N < 1 refusal dropped", _mut(M, "int(a.henchman_cap) < 1", "False"))]),
    ("spawn_population marks a hireable row (flag-gated) through hireable_bringup, records "
     "it, and skips a field",
     lock_spawn, SP,
     [("the flag gate removed", _mut(SP, 'row.get("hireable") and HENCHMAN_ADD_ENABLED',
                                     'row.get("hireable")')),
      ("the field gate removed", _mut(SP, "if instance_is_field(state):", "if False:"))]),
    ("handle_henchman_add caps on party_member_count vs OUTPOST_PARTY_CAP, records the "
     "henchman and sizes through party_size_on_wire",
     lock_hench_add, HA,
     [("the cap check removed", _mut(HA, CAP_CHECK, "False")),
      ("the size taken from the count", _mut(HA, "size = party_size_on_wire(state)",
                                              "size = party_member_count(state)"))]),
    ("handle_hero_kick sizes through party_size_on_wire (hired henchmen counted)",
     lock_hero_kick, HK,
     [("the landing's sum restored", _mut(HK, "party_size = party_size_on_wire(state)",
                                          "party_size = " + OLD_SUM + " + len(remaining)"))]),
    ("handle_hero_add sizes through party_size_on_wire and refuses at the same cap",
     lock_hero_add, HD,
     [("the landing's sum restored", _mut(HD, "party_size = party_size_on_wire(state)",
                                          "party_size = " + OLD_SUM + " + len(party_hero_slots(state))")),
      ("the cap check removed", _mut(HD, CAP_CHECK, "False"))]),
    ("party_size_on_wire rides PARTY_SIZE_COUNTS_HEROES (the load's revert arm)",
     lock_wire, PW,
     [("the flag ignored", _mut(PW, "count_heroes=PARTY_SIZE_COUNTS_HEROES", "count_heroes=True"))]),
]
for what, lock, text, muts in LOCKS:
    led.ok(bool(text) and lock(text), f"LOCK: {what}")
    for mname, mtext in muts:
        led.ok(mtext != text and not lock(mtext),
               f"KNOWN-BAD: {what} -- {mname} reddens the lock")

# 0x009F is OFF the allowlist (its arm landed); putting it back in memory reddens.
import test_dispatch                                          # noqa: E402
led.ok(lock_allowlist(test_dispatch.DROPPED_ON_PURPOSE),
       "LOCK: 0x009F HENCHMAN_ADD is off DROPPED_ON_PURPOSE -- a handled opcode "
       "on the allowlist would silently re-permit the drop (test_dispatch section 7)")
led.ok(not lock_allowlist(set(test_dispatch.DROPPED_ON_PURPOSE) | {0x009F}),
       "KNOWN-BAD: 0x009F back on the allowlist reddens the lock")
led.ok(lock_kick_allowlist(test_dispatch.DROPPED_ON_PURPOSE),
       "LOCK: 0x00A8 HENCHMAN_KICK is off DROPPED_ON_PURPOSE (its arm landed, CLEANUP-3)")
led.ok(not lock_kick_allowlist(set(test_dispatch.DROPPED_ON_PURPOSE) | {0x00A8}),
       "KNOWN-BAD: 0x00A8 on the allowlist reddens the lock")

sys.exit(led.verdict())
