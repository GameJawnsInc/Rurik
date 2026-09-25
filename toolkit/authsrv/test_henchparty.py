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
    outposts -- ENG-HENCH-11). THE 248 SET (the review's RV-1): the same
    wiring over `outpost_henchmen_248` on map 248 creates and marks 34/35/36,
    and that area served on 148 places nothing (spawn_row_on_map) -- the
    per-map cap's client run needs an add on a map whose cap is not 4, and
    the 148 rows could not give it one; §2 (n) checks the set exists and §5
    (vaulted) that its three rows stand on 248's own mesh.
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

  * THE PER-MAP CAP (desk-partycap, 2026-09-25; content/partycap.toml,
    henchparty.party_cap, authsrv.party_cap): §2 (n) the served map's own
    AreaInfo max_party -- on map 248 (8) four henchmen fill 1 -> 5 and the
    cap line prints ONCE naming the row; the same adds on map 148 (4) stop
    at 4 (the per-map KNOWN-BAD); a map with NO row (999) falls back to 4
    and the log SAYS so (NO row, UNVERIFIED); --constant-party-cap on 248
    stops at 4 (the flag's KNOWN-BAD arm, the pre-2026-09-25 behaviour);
    --henchman-cap 6 on 248 stops at 6; a zone from 148 to 248 prints the
    cap again at 8; the pure rule's five answers; every served map has a
    row (the join the server performs); the hero add on 248 goes through at
    5 (vaulted) and on 148 is refused (bare). §5 the rows against the PINNED
    CLIENT (vaulted): the code locator names 0x0096DE38, 888 records
    validate, and every row's max_party equals the client's own -- a check
    the binary can refute.
  * THE LEAVE (desk-partycap, 2026-09-25; henchparty.py THE LEAVE): §1l the
    batch `party_leave_batch` is one 0x01C0 per hired henchman then ONE
    0x00B0, encoded through the codec (6 + 6 + 5 bytes for two); refused
    with no agents, agent 0, party 0. §2 (o) the real `handle_party_leave`
    in an outpost with a hero and two hired henchmen: two 0x01C0 rows then
    0x00B0 [14, 2], the NPCs standing and hireable, the hero still in; the
    client's own companion 0x001F [40] (HEROES_ALL) through the real
    `handle_hero_kick`: hero 6's OBSERVED batch, 0x00B0 [14, 1], the hero
    kicked -- and persisted under --persist (a real store); two heroes ->
    two batches, sizes 2 then 1; [40] with no party hero and a second leave
    send nothing; the dropped henchman can be hired again; the launch
    henchman stays and the line names it; a FIELD's leave is refused with
    nothing sent; under --no-party-leave the [40] is ignored and the hero
    stays; the leave with an opaque store attached touches it not at all.
    §4 locks: the 0x00A2 arm gated on PARTY_LEAVE_ENABLED and the constant;
    main() wires --no-party-leave and --constant-party-cap through globals
    (--henchman-cap turns the per-map read off too); handle_party_leave
    refuses a field first, pops every hired henchman, sizes through
    party_size_on_wire, sends party_leave_batch and names no store;
    handle_hero_kick's HEROES_ALL arm sits BEFORE the owned check and is
    gated on PARTY_LEAVE_ENABLED; both handlers resolve the cap through
    party_cap(state) before the cap check; serverargs declares both flags;
    0x00A2 is off the allowlist. Each with a mutation that reddens it. §5
    (vaulted) the leave's four client sites read as documented and the `ja`
    lands on the 0xA2 wrapper.

Floor = the bare-machine core, measured with RURIK_VAULT pointed at an empty
directory (§1, §5 and the accepting hero adds declare skips there); the vault
adds the rest.
"""
import ast
import contextlib
import io
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
import codec as codecmod                                     # noqa: E402
import charstore                                             # noqa: E402
import henchparty                                            # noqa: E402
import authsrv                                               # noqa: E402
import livewire                                              # noqa: E402

led = checks.Ledger("henchman add (DESKWORK-D1 step 5)", floor=179)   # 2026-09-25 (desk-partycap's review, RV-1): 179 bare from the green run with RURIK_VAULT at an empty directory (204 vaulted: +2 in section 5, the 248 set on 165811's mesh and the arrival control, a declared skip bare) -- +3 bare: (n) the 248 hireable set exists, section 3 the set creates and marks 34/35/36 on 248 and nothing on 148; 176 at the lane's commit (desk-partycap): the bare-machine core from the green run with RURIK_VAULT pointed at an empty directory (199 vaulted: +1 hero add on 248, +6 in section 5 against the pinned client, +16 the tape and the two hero adds as before) -- +68 bare on the per-map cap ((n): the rows, the join, the provenance, the pure rule x6, 248/148/999, the flag arm, --henchman-cap 6, the zone, the hero add refused on 148) and the leave (section 1l x7, (o) x15, the locks: the arm x4, main x3, handle_party_leave x5, the HEROES_ALL arm x4, --constant-party-cap x4, party_cap x3, the caps load x3, serverargs, the allowlist x2, and +2 mutations each on HA and HD); 108 at desk-partyfull's review (124 vaulted; 107 at that lane's commit, +1 at the review: code 81 joins the bad codes; the hero-half vacuity guard is vaulted, a declared skip bare); 82 at CLEANUP-3's review (79 at the lane's commit, +3 at the review: (l) the launch henchman's refusal x2 and the launch-guard mutation; 49 before the kick; +30 on the kick), +25 on the refusal at the cap: (m) the reply's bytes, the off arm, five bad codes, both handlers ARMED, the line, the two silent refusals, the vacuity guard, the OFF arm, and the locks (serverargs, the module default, HA x4, HD x3, main x3)

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


# -- §1l the LEAVE batch (desk-partycap; bare-machine: no tape carries it) ----
lb = henchparty.party_leave_batch(1, 14, 2, [4, 2])
led.ok([op for op, _v, _l in lb] == [0x01C0, 0x01C0, 0x00B0] and lb[0][1] == [1, 4]
       and lb[1][1] == [1, 2] and lb[2][1] == [14, 2] and "RECONSTRUCTION" in lb[0][2],
       "(§1l) the leave batch is one 0x01C0 [party 1, agent] per hired henchman, in hire order, "
       "THEN one 0x00B0 [player 14, size 2] -- the kick's row-then-size once for all rows, "
       "labelled RECONSTRUCTION (no tape carries it)", f"{[(hex(o), v) for o, v, _l in lb]}")
wire_l = encode_batch(lb)
led.ok(len(wire_l) == 17 and wire_l[:6] == bytes.fromhex("c001" "0100" "0400")
       and wire_l[6:12] == bytes.fromhex("c001" "0100" "0200")
       and wire_l[12:] == bytes.fromhex("b000" "0e00" "02"),
       "(§1l) ...it encodes through the codec: two 6-byte 0x01C0 rows then 0x00B0's 5, 17 in all",
       f"{wire_l.hex()}")
for bad_args in ((1, 14, 2, []), (1, 14, 2, None), (0, 14, 2, [4]), (1, 14, 2, [4, 0]), (1, 14, 2, [-1])):
    try:
        henchparty.party_leave_batch(*bad_args)
        led.ok(False, f"(§1l) party_leave_batch{bad_args} is refused")
    except ValueError:
        led.ok(True, f"(§1l) party_leave_batch{bad_args} is refused (no agents / party 0 / agent 0 / "
                     f"a negative agent: nothing to leave sends nothing, and 0 is the client's 'own "
                     f"party' spelling, not our declared id)")


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
LEAVE = authsrv.GAME_CMSG_PARTY_LEAVE

_saved = {k: getattr(authsrv, k) for k in
          ("HERO_IDS", "HENCHMAN", "PLAYER_NUMBER", "HENCHMAN_ADD_ENABLED", "HENCHMAN_KICK_ENABLED",
           "OUTPOST_PARTY_CAP", "PARTY_SIZE_COUNTS_HEROES", "HERO_AGENT_ID", "PARTY_FULL_REPLY_CODE",
           "PERSIST", "HERO_KICK_ENABLED", "HERO_ADD_ENABLED", "RESET_HERO_KICKS",
           "PARTY_COMMANDS", "HERO_BAGS", "HERO_INVENTORY", "HERO_CHAR",
           "HERO_BODY", "EXPLORABLE", "OUTPOST", "PARTY_BODY_IN_OUTPOST",
           "HERO_RIG_RETAIL", "HERO_ACTIVATE", "PARTY_CAP_PER_MAP", "PARTY_LEAVE_ENABLED")}
_saved_caps = dict(authsrv.MAP_PARTY_CAPS)
_store_base = tempfile.mkdtemp(prefix="henchparty-test-")
try:
    authsrv.HERO_IDS = []
    authsrv.HENCHMAN = None
    authsrv.PLAYER_NUMBER = 14
    authsrv.HENCHMAN_ADD_ENABLED = True
    authsrv.HENCHMAN_KICK_ENABLED = True
    authsrv.OUTPOST_PARTY_CAP = 4
    authsrv.PARTY_CAP_PER_MAP = True      # the per-map read ON; the states below carry no
    authsrv.PARTY_LEAVE_ENABLED = True    # map_id (the constant stands in) unless a case says so
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
    authsrv.HERO_IDS = [6]                                       # a hero IN the party for this one
    authsrv.handle_henchman_kick([KICKH, 200], send, st, 0)      # the hero's agent (HERO_AGENT_ID; RV-9)
    authsrv.HERO_IDS = []
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
    # (l) the LAUNCH henchman (--henchman): in party 1 by the load's 0x01BF and counted, so
    #     the client can send 0x00A8 for its row -- refused with ITS reason, nothing sent
    #     (the review's RV-6: the lane said "not a hired henchman ... no 0x01BF row").
    authsrv.HENCHMAN = "hench_warrior"       # any non-None: the count and the handler test `is not None`
    sent, send = fake_send()
    st = seeded(HENCH)
    authsrv.handle_henchman_add([ADD, 4], send, st, 0)
    sent.clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.handle_henchman_kick([KICKH, authsrv.HENCHMAN_AGENT_ID], send, st, 0)
    line = buf.getvalue().strip()
    led.ok(sent == [] and sorted(st["party_henchmen"]) == [4] and authsrv.party_member_count(st) == 3
           and "the LAUNCH henchman (--henchman)" in line and "not a hired henchman" not in line
           and "not modelled" in line,
           f"(l) kicking the LAUNCH henchman (--henchman, agent {authsrv.HENCHMAN_AGENT_ID}: the load's "
           f"0x01BF row, counted in the party of 3) sends nothing and says WHY -- 'the LAUNCH henchman ... "
           f"not modelled', not 'no 0x01BF row' (the review's RV-6); the hired henchman stays", f"{line[:170]}")
    r_launch = henchparty.kick_refusal({4: {}}, 30, launch_agent=30)
    r_plain = henchparty.kick_refusal({4: {}}, 30)
    led.ok(r_launch is not None and "LAUNCH" in r_launch
           and henchparty.kick_refusal({4: {}}, 4, launch_agent=30) is None
           and r_plain is not None and "LAUNCH" not in r_plain,
           "(l) kick_refusal(launch_agent=30): 30 refused as the launch henchman, 4 still passes, and "
           "without the kwarg 30 is refused as an unhired agent (the pre-review reason)")
    authsrv.HENCHMAN = None

    led.ok(henchparty.party_is_full(4, 4) and not henchparty.party_is_full(3, 4),
           "party_is_full: 4/4 full, 3/4 not -- the boundary the cap refuses on")
    led.ok(authsrv.GAME_SMSG_PARTY_HENCHMAN_HIREABLE == henchparty.HENCHMAN_HIREABLE == 0x0071
           and authsrv.GAME_SMSG_PLAYER_PARTY_SIZE == henchparty.PLAYER_PARTY_SIZE == 0x00B0
           and authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT == henchparty.AGENT_PROPERTY_UPDATE_INT == 0x009F
           and authsrv.GAME_SMSG_PARTY_HENCHMAN_REMOVE == henchparty.PARTY_HENCHMAN_REMOVE == 0x01C0
           and authsrv.GAME_CMSG_HENCHMAN_KICK == 0x00A8,
           "the leaf's four opcode constants equal authsrv's (one value per opcode, "
           "0x0071 / 0x00B0 / 0x009F / 0x01C0) and the kick's c2s is 0x00A8")

    # (m) THE REFUSAL AT THE CAP (desk-partyfull, 2026-09-25): --party-full-reply
    #     CODE answers a cap refusal with ONE 0x01BC [CODE]; the default sends
    #     nothing. RECONSTRUCTION -- retail's reply is NOT FOUND (0 of 96), the
    #     client's mechanism is what is measured (studies/cmsg "The refusal at the cap").
    fr = henchparty.party_full_reply(64)
    led.ok([op for op, _v, _l in fr] == [0x01BC] and fr[0][1] == [64]
           and encode_batch(fr) == bytes.fromhex("bc0140"),
           "(m) party_full_reply(64) is ONE 0x01BC [64] and encodes through the codec to "
           "the client's 3-byte [header, byte] shape bc 01 40", f"{encode_batch(fr).hex()}")
    try:
        _ends = (henchparty.party_full_reply(None) == [] and henchparty.party_full_reply(0) != []
                 and encode_batch(henchparty.party_full_reply(80)) == bytes.fromhex("bc0150"))
        _why = ""
    except ValueError as exc:          # a renumbered table max would refuse row 80: score it, do not die
        _ends, _why = False, str(exc)[:80]
    led.ok(_ends, "(m) None is the off arm (nothing), 0 and 80 are the table's first and last rows "
                  "(81 rows: 0x00B97AAC is the NEXT table's row 0 and 81 the client's no-error sentinel "
                  "-- the review of 2026-09-25 corrected 82 / 0..81)", _why)
    # 81 leads the bad codes: it is the sentinel the lane's max let through (the review's RV-1).
    for bad in (81, 82, -1, True, "64", 3.0):
        try:
            henchparty.party_full_reply(bad)
            led.ok(False, f"(m) party_full_reply({bad!r}) is refused (outside the client's 81-row table)")
        except ValueError as exc:
            led.ok("0..80" in str(exc),
                   f"(m) party_full_reply({bad!r}) is refused with the table's range named", str(exc)[:80])
    # the two handlers, ARMED: a party at the cap (player + 3 henchmen = 4 of 4).
    authsrv.HERO_IDS = []
    authsrv.PARTY_FULL_REPLY_CODE = 64
    stm = seeded(HENCH)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], stm, 0)
    stm["hireable_henchmen"][8] = {"enc_name": "DDDD", "profession": 3, "level": 3, "name": "M"}
    stm["agents"][8] = {"name": "M"}
    sm, sendm = fake_send()
    with contextlib.redirect_stdout(io.StringIO()) as _bufm:
        authsrv.handle_henchman_add([ADD, 8], sendm, stm, 0)
    linem = _bufm.getvalue().strip()
    led.ok(sm == [(0x01BC, [64])] and 8 not in stm["party_henchmen"]
           and authsrv.party_member_count(stm) == 4,
           "(m) ARMED: the henchman add refused at the cap sends exactly ONE 0x01BC [64] and adds "
           "nothing (count stays 4)", f"sent {[(hex(o), v) for o, v in sm]}")
    led.ok("0x01BC PARTY_ERROR_PROMPT [code 64] follows" in linem and "RECONSTRUCTION" in linem
           and "nothing sent" not in linem,
           "(m) ARMED: the refusal line says the 0x01BC follows and labels it RECONSTRUCTION, not "
           "'nothing sent'", linem[:160])
    # the hero add at the same cap: hero 6 kicked, party = player + 3 henchmen.
    authsrv.HERO_IDS = [6]
    sth = seeded(HENCH)
    authsrv.kicked_heroes_set(sth).add(6)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], sth, 0)
    sh, sendh = fake_send()
    authsrv.handle_hero_add([HADD, 6], sendh, sth, 0)
    led.ok(sh == [(0x01BC, [64])] and authsrv.hero_kicked(sth, 6)
           and authsrv.party_member_count(sth) == 4,
           "(m) ARMED: the hero add refused at the cap sends exactly ONE 0x01BC [64], the hero "
           "stays kicked, the count stays 4", f"sent {[(hex(o), v) for o, v in sh]}")
    # the HERO half of "a non-full add is untouched" while ARMED (the review's RV-3: a 0x01BC
    # sent after a SUCCESSFUL hero add survived every check above, since the hero cap lock
    # counts only the cap branch's string): the kicked hero re-added into a party BELOW the
    # cap (player + 2 henchmen = 3 of 4) goes through with NO 0x01BC. Vaulted -- the
    # accepting path builds the hero block from the vault's attribute-cost rows; a bare
    # machine declares the skip, as (e)'s hero adds do.
    stv_h = seeded(HENCH)
    authsrv.kicked_heroes_set(stv_h).add(6)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], stv_h, 0)
    sv_h, sendv_h = fake_send()
    if hero_add_or_skip("(m) VACUITY GUARD (hero): armed, the kicked hero re-added BELOW the cap",
                        sendv_h, stv_h):
        led.ok(0x01C2 in ops_of(sv_h) and sizes_of(sv_h) == [4] and 0x01BC not in ops_of(sv_h)
               and not authsrv.hero_kicked(stv_h, 6) and authsrv.party_member_count(stv_h) == 4,
               "(m) VACUITY GUARD (hero): armed, the kicked hero re-added into a party BELOW the cap "
               "(player + 2 henchmen = 3 of 4) goes through as 0x00B0 = 4 + the 0x01C2 row with NO "
               "0x01BC -- the reply is the CAP refusal's, not the flag's on every hero add",
               f"{[hex(o) for o in ops_of(sv_h)]} sizes {sizes_of(sv_h)}")
    # the reply rides the CAP refusal only: the other two refusals stay silent when armed.
    s_nh, send_nh = fake_send()
    authsrv.handle_henchman_add([ADD, 99], send_nh, stm, 0)
    s_dup, send_dup = fake_send()
    authsrv.handle_henchman_add([ADD, 4], send_dup, stm, 0)
    led.ok(s_nh == [] and s_dup == [],
           "(m) ARMED: 'not hireable' and 'already in the party' still send nothing -- the reply "
           "is the CAP refusal's alone")
    # VACUITY GUARD: the same add under a raised cap goes THROUGH with no 0x01BC, so the
    # 0x01BC above was the refusal's and not something the armed flag sends on every add.
    authsrv.OUTPOST_PARTY_CAP = 8
    sv2, sendv2 = fake_send()
    authsrv.handle_henchman_add([ADD, 8], sendv2, stm, 0)
    led.ok(ops_of(sv2) == [0x00B0, 0x01BF] and 0x01BC not in ops_of(sv2) and 8 in stm["party_henchmen"],
           "(m) VACUITY GUARD: armed, the same add under --henchman-cap 8 goes through as 0x00B0 + "
           "0x01BF with NO 0x01BC", f"{[hex(o) for o in ops_of(sv2)]}")
    authsrv.OUTPOST_PARTY_CAP = 4
    # THE OFF ARM (the default): the same two refusals send nothing.
    authsrv.PARTY_FULL_REPLY_CODE = None
    stm["hireable_henchmen"][9] = {"enc_name": "EEEE", "profession": 4, "level": 3, "name": "N"}
    stm["agents"][9] = {"name": "N"}
    so, sendo = fake_send()
    with contextlib.redirect_stdout(io.StringIO()) as _bufo:
        authsrv.handle_henchman_add([ADD, 9], sendo, stm, 0)
    so_h, sendo_h = fake_send()
    authsrv.handle_hero_add([HADD, 6], sendo_h, sth, 0)
    led.ok(so == [] and so_h == [] and "nothing sent (retail's refusal reply NOT FOUND)" in _bufo.getvalue()
           and 9 not in stm["party_henchmen"] and authsrv.hero_kicked(sth, 6),
           "(m) OFF (the default): both cap refusals send nothing and the line says 'nothing sent "
           "(retail's refusal reply NOT FOUND)' -- today's silent refusal is the default arm")
    authsrv.HERO_IDS = []

    # (n) THE PER-MAP CAP (desk-partycap, 2026-09-25): the served map's own AreaInfo
    #     max_party (content/partycap.toml through party_cap), not a constant. A map
    #     at 8 admits a 5th member; the same adds on a map at 4 stop there; a map
    #     with no row falls back to 4 and SAYS so; --constant-party-cap is the
    #     KNOWN-BAD flag arm (4 on the 8-cap map, the pre-2026-09-25 behaviour);
    #     --henchman-cap N overrides every map.
    caps = authsrv.MAP_PARTY_CAPS
    led.ok(caps.get(148) == 4 and caps.get(146) == 4 and caps.get(242) == 4 and caps.get(449) == 4
           and caps.get(248) == 8 and caps.get(280) == 8 and caps.get(55) == 6 and caps.get(143) == 1,
           "(n) content/partycap.toml loads: 148/146/242/449 -> 4 (the old constant's four), 248/280 "
           "-> 8, 55 -> 6, the Ascalon Academy slot 143 -> 1 (client-table, build 38797, areatable.py)",
           f"{sorted(caps.items())}")
    _prov = {k: r.provenance for k, r in authsrv.agents.WORLD.rows("map_party_cap").items()}
    led.ok(all(p["source"] == "client-table" and p["extractor"] == "toolkit/clientscan/areatable.py"
               and int(p["build"]) == 38797 and "OFF_MAX_PARTY" in p["verified"] for p in _prov.values()),
           "(n) every row is client-table, names areatable.py as its extractor, records build 38797 and "
           "says which field it read -- the 2026-08-11 ruling's three conditions, per row")
    _missing = sorted(set(authsrv.MAP_STATIC_CONFIG) - set(caps))
    led.ok(not _missing and len(caps) >= 19,
           f"(n) every served map (content/maps.toml, {len(authsrv.MAP_STATIC_CONFIG)} rows) has a "
           f"map_party_cap row -- the join party_cap performs; a map added without one would fall "
           f"back to 4 in silence but for this check", f"missing {_missing}")
    # THE RUN'S PRECONDITION (the review's RV-1): a cap other than 4 is only
    # observable through an add, and an add needs a hireable row ON THAT MAP --
    # the 148 set pins map = 148 and spawn_row_on_map places it nowhere else.
    _spawns = authsrv.agents.WORLD.rows("spawn")
    _h248 = {k: r for k, r in _spawns.items() if r.get("hireable") and int(r.get("map") or 0) == 248}
    _h148 = {k: r for k, r in _spawns.items() if r.get("hireable") and int(r.get("map") or 0) == 148}
    led.ok(len(_h248) == 3 and {r["area"] for r in _h248.values()} == {"outpost_henchmen_248"}
           and sorted(int(r["agent_id"]) for r in _h248.values()) == [34, 35, 36]
           and not ({int(r["agent_id"]) for r in _h248.values()} & {int(r["agent_id"]) for r in _h148.values()})
           and {r["npc"] for r in _h248.values()} == {r["npc"] for r in _h148.values()}
           and all(r.provenance["source"] == "invented" and "165811" in r.provenance["verified"]
                   for r in _h248.values()),
           "(n) map 248 (cap 8) HAS a hireable set -- content/world.toml's outpost_henchmen_248: three "
           "rows on map 248, fresh agent ids 34/35/36 disjoint from the 148 set's, the 148 set's three "
           "templates, each provenance naming the mesh it was checked on -- so the runsheet's launch "
           "can send an add there at all (RV-1: on 248 the 148 rows place nothing)",
           f"248: {sorted((k, int(r['agent_id'])) for k, r in _h248.items())}")
    pc = henchparty.party_cap
    led.ok(pc({248: 8}, 248, 4) == (8, pc({248: 8}, "248", 4)[1]) and "max_party" in pc({248: 8}, 248, 4)[1]
           and pc({248: 8}, "248", 4)[0] == 8,
           "(n) party_cap: a map with a row returns the row (an int or a string id alike), the why "
           "naming max_party")
    _f = pc({248: 8}, 148, 4)
    led.ok(_f[0] == 4 and "NO map_party_cap row" in _f[1] and "UNVERIFIED" in _f[1] and "148" in _f[1],
           "(n) party_cap: a map with NO row falls back to the constant and the why says NO row, "
           "UNVERIFIED, naming the map", _f[1])
    led.ok(pc({248: 8}, None, 4)[0] == 4 and "no map id" in pc({248: 8}, None, 4)[1]
           and pc({248: 8}, "x", 4)[0] == 4,
           "(n) party_cap: no map id, or a malformed one, is the constant with its own why")
    _c = pc({248: 8}, 248, 4, per_map=False)
    led.ok(_c[0] == 4 and "--constant-party-cap" in _c[1],
           "(n) party_cap(per_map=False): the constant even where a row exists -- the revert arm and "
           "--henchman-cap's override", _c[1])
    led.ok(pc({248: 8}, 248, 6, per_map=False)[0] == 6,
           "(n) ...and the constant is whatever --henchman-cap made it (6)")
    HENCH6 = dict(HENCH)
    HENCH6.update({8: {"enc_name": "DDDD", "profession": 3, "level": 3, "name": "M"},
                   9: {"enc_name": "EEEE", "profession": 4, "level": 3, "name": "N"},
                   10: {"enc_name": "FFFF", "profession": 5, "level": 3, "name": "E"}})

    def adds(st, agents_in):
        out, snd = fake_send()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            for a in agents_in:
                authsrv.handle_henchman_add([ADD, a], snd, st, 0)
        return out, buf.getvalue()

    # map 248 (cap 8): four adds fill 1 -> 5 -- a 5th member the constant refused.
    st8 = seeded(HENCH6, map_id=248)
    s8, log8 = adds(st8, (4, 2, 6, 8))
    led.ok(len(st8["party_henchmen"]) == 4 and sizes_of(s8) == [2, 3, 4, 5],
           "(n) on map 248 (max_party 8) four henchmen are admitted: 0x00B0 climbs 2, 3, 4, 5 -- the "
           "5th member the constant 4 refused", f"sizes {sizes_of(s8)}")
    led.ok(log8.count("the party cap here is") == 1 and "the party cap here is 8" in log8
           and "map 248's own AreaInfo max_party" in log8,
           "(n) the cap line prints ONCE per connection, naming 8 and the row it came from",
           log8.strip().splitlines()[0][:150] if log8.strip() else "")
    # KNOWN-BAD per map: the SAME four adds on map 148 (max_party 4) stop at 4.
    st4 = seeded(HENCH6, map_id=148)
    s4, log4 = adds(st4, (4, 2, 6, 8))
    led.ok(len(st4["party_henchmen"]) == 3 and sizes_of(s4) == [2, 3, 4] and 8 not in st4["party_henchmen"]
           and "HENCHMAN_ADD(8) refused" in log4 and "(4: map 148's own AreaInfo max_party" in log4,
           "(n) the same four adds on map 148 (max_party 4) stop at 4: the fourth is refused and the "
           "line names the map's own row", f"sizes {sizes_of(s4)}")
    # the fallback: a map with NO row -> 4, and the log SAYS so.
    st9 = seeded(HENCH6, map_id=999)
    s9, log9 = adds(st9, (4, 2, 6, 8))
    led.ok(len(st9["party_henchmen"]) == 3 and sizes_of(s9) == [2, 3, 4]
           and "map 999 has NO map_party_cap row" in log9 and "UNVERIFIED" in log9
           and "the constant 4 stands in" in log9 and "the party cap here is 4" in log9,
           "(n) map 999 has no row: the constant 4 stands in, the fourth is refused, and the cap line "
           "says NO row / UNVERIFIED / the constant 4", log9.strip().splitlines()[0][:150] if log9.strip() else "")
    # the KNOWN-BAD flag arm: --constant-party-cap on map 248 -> 4, the pre-2026-09-25 picture.
    authsrv.PARTY_CAP_PER_MAP = False
    stc = seeded(HENCH6, map_id=248)
    sc, logc = adds(stc, (4, 2, 6, 8))
    led.ok(len(stc["party_henchmen"]) == 3 and sizes_of(sc) == [2, 3, 4]
           and "the party cap here is 4" in logc and "--constant-party-cap" in logc,
           "(n) KNOWN-BAD flag arm: --constant-party-cap on map 248 refuses the fourth at 4 and the "
           "cap line names the flag -- exactly the behaviour before the table")
    # --henchman-cap 6 (main sets OUTPOST_PARTY_CAP = 6 and turns the per-map read off): on
    # map 248 five henchmen are admitted (1 + 5 = 6) and the sixth refused, where 8 admitted it.
    authsrv.OUTPOST_PARTY_CAP = 6
    sth = seeded(HENCH6, map_id=248)
    sh, logh = adds(sth, (4, 2, 6, 8, 9, 10))
    led.ok(len(sth["party_henchmen"]) == 5 and sizes_of(sh) == [2, 3, 4, 5, 6] and 10 not in sth["party_henchmen"]
           and "the party cap here is 6" in logh,
           "(n) --henchman-cap 6 overrides map 248's 8: five admitted (1 + 5 = 6), the sixth refused",
           f"sizes {sizes_of(sh)}")
    authsrv.OUTPOST_PARTY_CAP = 4
    authsrv.PARTY_CAP_PER_MAP = True
    # a zone: the cap follows the map and the line prints again.
    stz = seeded(HENCH6, map_id=148)
    bufz = io.StringIO()
    with contextlib.redirect_stdout(bufz):
        c1 = authsrv.party_cap(stz)
        c1b = authsrv.party_cap(stz)
        stz["map_id"] = 248
        c2 = authsrv.party_cap(stz)
    led.ok(c1[0] == 4 and c1b == c1 and c2[0] == 8 and bufz.getvalue().count("the party cap here is") == 2,
           "(n) a zone from 148 to 248: party_cap answers 4 then 8, and the cap line prints once per "
           "answer (twice), not per call (three)", f"{bufz.getvalue().count('the party cap here is')} line(s)")
    # the HERO ADD at the per-map cap: player + 3 hired henchmen (4 of 8) on map 248 -> the
    # re-added hero goes THROUGH at 5 (vaulted: the accepting path builds the hero block);
    # the same party on map 148 (4 of 4) -> REFUSED, bare.
    authsrv.HERO_IDS = [6]
    sth8 = seeded(HENCH6, map_id=248)
    authsrv.kicked_heroes_set(sth8).add(6)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], sth8, 0)
    sv8, sendv8 = fake_send()
    with contextlib.redirect_stdout(io.StringIO()):
        ran = hero_add_or_skip("(n) the hero add on map 248 (cap 8) with 4 members goes through", sendv8, sth8)
    if ran:
        led.ok(0x01C2 in ops_of(sv8) and sizes_of(sv8) == [5] and not authsrv.hero_kicked(sth8, 6),
               "(n) the hero add on map 248 (cap 8) with the player and 3 henchmen goes THROUGH: 0x00B0 "
               "= 5 and the 0x01C2 row", f"{[hex(o) for o in ops_of(sv8)]} sizes {sizes_of(sv8)}")
    sth4 = seeded(HENCH6, map_id=148)
    authsrv.kicked_heroes_set(sth4).add(6)
    for a in (4, 2, 6):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], sth4, 0)
    sr4, sendr4 = fake_send()
    bufr4 = io.StringIO()
    with contextlib.redirect_stdout(bufr4):
        authsrv.handle_hero_add([HADD, 6], sendr4, sth4, 0)
    led.ok(sr4 == [] and authsrv.hero_kicked(sth4, 6) and "HERO_ADD(6) refused" in bufr4.getvalue()
           and "(4: map 148's own AreaInfo max_party" in bufr4.getvalue(),
           "(n) the same hero add on map 148 (cap 4, 4 of 4) is REFUSED, nothing sent, the line naming "
           "the map's row", bufr4.getvalue().strip()[:150])
    authsrv.HERO_IDS = []

    # (o) THE LEAVE (desk-partycap, 2026-09-25; henchparty.py THE LEAVE): 0x00A2 in an
    #     outpost with a hero and two hired henchmen -> two 0x01C0 rows then 0x00B0 [14, 2];
    #     the client's own companion 0x001F [40] -> the hero's kick batch, size 1, kicked.
    led.ok(LEAVE == 0x00A2 and authsrv.HEROES_ALL == 40,
           "(o) the leave's c2s is 0x00A2 and HEROES_ALL is 40 (0x28, the client's HEROES bound: the "
           "kick sender's `hero <= HEROES`, the Leave click's push)")
    authsrv.HERO_IDS = [6]
    sto = seeded(HENCH, map_id=148)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], sto, 0)
    so, sendo = fake_send()
    bufo = io.StringIO()
    with contextlib.redirect_stdout(bufo):
        authsrv.handle_party_leave([LEAVE], sendo, sto, 0)
    led.ok(ops_of(so) == [0x01C0, 0x01C0, 0x00B0] and so[0][1] == [1, 4] and so[1][1] == [1, 2]
           and sizes_of(so) == [2],
           "(o) the leave with a hero and two hired henchmen sends exactly 0x01C0 [1, 4], 0x01C0 [1, 2] "
           "then 0x00B0 [14, 2] -- the rows in hire order, the size with the hero still counted",
           f"{[(hex(o), v) for o, v in so]}")
    led.ok(not sto["party_henchmen"] and 4 in sto["agents"] and 2 in sto["agents"]
           and 4 in sto["hireable_henchmen"] and 2 in sto["hireable_henchmen"]
           and 0x0021 not in ops_of(so) and authsrv.party_member_count(sto) == 2
           and not authsrv.hero_kicked(sto, 6),
           "(o) ...the henchmen leave the party (count 2: player + hero), the NPCs stand (no 0x0021) "
           "and stay hireable, the hero is still in -- the heroes are the [40]'s business")
    led.ok("2 hired henchman(s) dropped" in bufo.getvalue() and "RECONSTRUCTION" in bufo.getvalue()
           and f"0x001F [{authsrv.HEROES_ALL}]" in bufo.getvalue(),
           "(o) the line counts the drop, labels the reply RECONSTRUCTION and names the [40] that follows",
           bufo.getvalue().strip()[:160])
    # the companion: 0x001F [40] through the REAL handle_hero_kick -> hero 6's own batch.
    so.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_hero_kick([KICK, 40], sendo, sto, 0)
    led.ok(ops_of(so) == [0x0075, 0x01C3, 0x00F8, 0x003E, 0x00B0] and sizes_of(so) == [1]
           and authsrv.hero_kicked(sto, 6) and authsrv.party_member_count(sto) == 1,
           "(o) 0x001F [40] (HEROES_ALL) kicks every party hero: hero 6's OBSERVED batch (0x0075, "
           "0x01C3, 0x00F8, 0x003E, 0x00B0 [14, 1]) and the hero is kicked -- the party is the player "
           "alone", f"{[hex(o) for o in ops_of(so)]} sizes {sizes_of(so)}")
    so.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_hero_kick([KICK, 40], sendo, sto, 0)
        authsrv.handle_party_leave([LEAVE], sendo, sto, 0)
    led.ok(so == [] and authsrv.party_member_count(sto) == 1,
           "(o) a second [40] (no party hero) and a second leave (no hired henchman) send NOTHING")
    so.clear()
    authsrv.handle_henchman_add([ADD, 4], sendo, sto, 0)
    led.ok(ops_of(so) == [0x00B0, 0x01BF] and sizes_of(so) == [1 + 1] and 4 in sto["party_henchmen"],
           "(o) a dropped henchman can be hired again after the leave: 0x00B0 [14, 2] + the row")
    # two heroes: [40] kicks both, sizes 2 then 1 (each its own kick, each with its 0x00B0).
    authsrv.HERO_IDS = [6, 7]
    st2 = seeded(HENCH, map_id=148)
    s2o, send2o = fake_send()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_hero_kick([KICK, 40], send2o, st2, 0)
    led.ok(ops_of(s2o).count(0x01C3) == 2 and sizes_of(s2o) == [2, 1]
           and authsrv.hero_kicked(st2, 6) and authsrv.hero_kicked(st2, 7),
           "(o) with two party heroes [40] kicks both: two 0x01C3 rows, sizes 2 then 1, both kicked",
           f"sizes {sizes_of(s2o)}")
    authsrv.HERO_IDS = [6]
    # the launch henchman stays (not modelled, as the kick leaves it) and the line says so.
    authsrv.HENCHMAN = "hench_warrior"
    stl = seeded(HENCH, map_id=148)
    authsrv.handle_henchman_add([ADD, 4], fake_send()[1], stl, 0)
    sl, sendl = fake_send()
    bufl = io.StringIO()
    with contextlib.redirect_stdout(bufl):
        authsrv.handle_party_leave([LEAVE], sendl, stl, 0)
    led.ok(ops_of(sl) == [0x01C0, 0x00B0] and sl[0][1] == [1, 4] and sizes_of(sl) == [3]
           and "the LAUNCH henchman (--henchman" in bufl.getvalue() and "stays" in bufl.getvalue()
           and authsrv.party_member_count(stl) == 3,
           "(o) with the launch henchman in the party the leave drops the HIRED one only (size 3: "
           "player + hero + launch) and the line says the launch henchman stays (not modelled)",
           bufl.getvalue().strip()[:160])
    authsrv.HENCHMAN = None
    # a FIELD's leave: refused, nothing sent, the party untouched.
    authsrv.EXPLORABLE = True
    stf = seeded(HENCH, map_id=148)
    for a in (4, 2):
        authsrv.handle_henchman_add([ADD, a], fake_send()[1], stf, 0)
    sf, sendf = fake_send()
    buff = io.StringIO()
    with contextlib.redirect_stdout(buff):
        authsrv.handle_party_leave([LEAVE], sendf, stf, 0)
    led.ok(sf == [] and sorted(stf["party_henchmen"]) == [2, 4] and "FIELD" in buff.getvalue()
           and "not modelled" in buff.getvalue(),
           "(o) in a FIELD the leave is refused with nothing sent and the party kept (retail's return "
           "to the outpost is UNVERIFIED and not modelled)", buff.getvalue().strip()[:150])
    authsrv.EXPLORABLE = False
    # --no-party-leave: the [40] arm is ignored as before (the 0x00A2 arm's gate is a lock).
    authsrv.PARTY_LEAVE_ENABLED = False
    stn = seeded(HENCH, map_id=148)
    sn, sendn = fake_send()
    bufn = io.StringIO()
    with contextlib.redirect_stdout(bufn):
        authsrv.handle_hero_kick([KICK, 40], sendn, stn, 0)
    led.ok(sn == [] and not authsrv.hero_kicked(stn, 6) and "--no-party-leave" in bufn.getvalue()
           and "ignored" in bufn.getvalue(),
           "(o) under --no-party-leave 0x001F [40] is ignored, nothing sent, the hero stays -- the "
           "picture before 2026-09-25", bufn.getvalue().strip()[:150])
    authsrv.PARTY_LEAVE_ENABLED = True
    # persistence: the [40]'s kicks write the store (the kick's own), the leave touches none.
    authsrv.PERSIST = True
    store = charstore.Store.open("henchparty@rurik.invalid", base=_store_base)
    store.ensure_character(UUID, "Leaver", "cc" * 37)
    stp = seeded(HENCH, map_id=148, charstore_game=store)
    authsrv.handle_henchman_add([ADD, 4], fake_send()[1], stp, 0)
    sp, sendp = fake_send()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_party_leave([LEAVE], sendp, stp, 0)
        authsrv.handle_hero_kick([KICK, 40], sendp, stp, 0)
    led.ok(store.kicked_heroes(UUID) == [6] and ops_of(sp)[:2] == [0x01C0, 0x00B0]
           and 0x01C3 in ops_of(sp),
           "(o) under --persist the [40]'s kick is written to the store (hero 6 kicked, as a click's "
           "kick is) after the leave's rows went out")
    authsrv.HERO_IDS = []        # no hero: the count would otherwise read the store for the kicked set
    stq = seeded(HENCH, map_id=148, charstore_game=object())
    authsrv.handle_henchman_add([ADD, 4], fake_send()[1], stq, 0)
    sq, sendq = fake_send()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_party_leave([LEAVE], sendq, stq, 0)
    led.ok(ops_of(sq) == [0x01C0, 0x00B0] and not stq["party_henchmen"],
           "(o) ...and the leave itself, with an OPAQUE store attached, touches it not at all (the hire "
           "is not persisted, so neither is the leave)")
    authsrv.PERSIST = False
    authsrv.HERO_IDS = []

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

        # THE 248 SET (the review's RV-1): the same wiring on the 8-cap map, and
        # the SLICE-B8 map filter that kept the 148 set OFF 248 keeps the 248
        # set off 148 -- the reason the per-map cap's run needed its own rows.
        authsrv.AREA_NAME = "outpost_henchmen_248"
        sent5, send5 = fake_send()
        st5 = {"agents": {}, "map_id": 248, "pathmap": _Mesh()}
        authsrv.spawn_population(send5, st5, (-5574.0, -4945.0, 0), 0)
        marks5 = [v[0] for op, v in sent5 if op == henchparty.HENCHMAN_HIREABLE]
        creates5 = [v[0] for op, v in sent5 if op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT]
        profs5 = {a: r["profession"] for a, r in (st5.get("hireable_henchmen") or {}).items()}
        led.ok(sorted(marks5) == [34, 35, 36] and sorted(creates5) == [34, 35, 36]
               and profs5 == {34: 1, 35: 2, 36: 7},
               "(§3) on map 248 the outpost_henchmen_248 set creates and marks 34/35/36 hireable "
               "(W/R/A, the 148 set's templates) -- the per-map cap's run has something to add",
               f"marks {sorted(marks5)} creates {sorted(creates5)} profs {profs5}")
        sent6, send6 = fake_send()
        st6 = {"agents": {}, "map_id": 148, "pathmap": _Mesh()}
        authsrv.spawn_population(send6, st6, (9826.0, 8077.0, 0), 0)
        led.ok(not [v for op, v in sent6 if op == henchparty.HENCHMAN_HIREABLE]
               and not [v for op, v in sent6 if op == authsrv.GAME_SMSG_WORLD_CREATE_AGENT]
               and not st6.get("hireable_henchmen"),
               "(§3) ...and the same area served on 148 creates and marks NOTHING (spawn_row_on_map: "
               "a row stands on its own map only -- why the 148 set could not serve the 248 run)",
               f"ops {sorted(set(hex(o) for o in ops_of(sent6)))}")
        authsrv.AREA_NAME = "outpost_henchmen"
    finally:
        authsrv.place_on_mesh = _saved_place
        authsrv.AREA_NAME = _saved_area
finally:
    for k, v in _saved.items():
        setattr(authsrv, k, v)
    authsrv.MAP_PARTY_CAPS.clear()
    authsrv.MAP_PARTY_CAPS.update(_saved_caps)
    shutil.rmtree(_store_base, ignore_errors=True)


# -- §4 source locks, each with a mutation that reddens it -------------------
# The source is parsed ONCE (authsrv.py is ~38k lines; a parse per mutant made
# this section take two minutes). Each lock reads the extracted text of one
# function, and its mutation edits that text.
TREE = ast.parse(SRC)
FUNCS = {n.name: (ast.get_source_segment(SRC, n) or "")
         for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)
         and n.name in ("main", "spawn_population", "handle_henchman_add",
                        "handle_hero_kick", "handle_hero_add", "party_size_on_wire",
                        "handle_henchman_kick", "handle_party_leave", "party_cap",
                        "_load_map_party_caps")}
with open(os.path.join(HERE, "serverargs.py"), encoding="utf-8") as _fh:
    ARGS = _fh.read()


def _mut(text, old, new):
    """`text` with the first `old` -> `new`; an absent `old` returns the text
    unchanged, and the caller's `msrc != src` check then reddens (a stale
    mutation string cannot pass as a redden)."""
    return text.replace(old, new, 1) if old in text else text


def _mut_last(text, old, new):
    """`text` with the LAST `old` -> `new` (the same absent-old rule as _mut)."""
    at = text.rfind(old)
    return text[:at] + new + text[at + len(old):] if at >= 0 else text


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


CAP_CHECK = "henchparty.party_is_full(party_member_count(state), cap)"
# desk-partycap: the cap is RESOLVED per map right before it is checked, in both handlers.
CAP_CALL = "cap, cap_why = party_cap(state)"
OLD_CAP_CHECK = "henchparty.party_is_full(party_member_count(state), OUTPOST_PARTY_CAP)"
OLD_SUM = "1 + (1 if HENCHMAN is not None else 0)"


def lock_cap_resolved(s):
    """party_cap(state) is called once, before the cap check, and the constant is
    not compared directly (the pre-2026-09-25 text is the mutation)."""
    return (s.count(CAP_CALL) == 1 and CAP_CHECK in s and s.find(CAP_CALL) < s.find(CAP_CHECK)
            and OLD_CAP_CHECK not in s)


def lock_hench_add(s):
    return (CAP_CHECK in s and lock_cap_resolved(s) and 'state.setdefault("party_henchmen"' in s
            and "size = party_size_on_wire(state)" in s)


def lock_hero_kick(s):
    return "party_size = party_size_on_wire(state)" in s and OLD_SUM not in s


def lock_hero_add(s):
    return ("party_size = party_size_on_wire(state)" in s and OLD_SUM not in s
            and CAP_CHECK in s and lock_cap_resolved(s))


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


KICK_REFUSAL = "why = henchparty.kick_refusal("
KICK_LAUNCH = "launch_agent=HENCHMAN_AGENT_ID if HENCHMAN is not None else None"
KICK_BATCH = "henchparty.henchman_kick_batch(1, PLAYER_NUMBER, size, aid)"


def lock_hench_kick(s):
    return (KICK_REFUSAL in s and KICK_LAUNCH in s and "hench = party.pop(aid)" in s
            and "size = party_size_on_wire(state)" in s and KICK_BATCH in s
            and "charstore" not in s and "set_hero_kicked" not in s
            and 'state.setdefault("party_henchmen"' in s)


def lock_kick_allowlist(dropped):
    return 0x00A8 not in dropped


# THE LEAVE's locks and THE PER-MAP CAP's (desk-partycap, 2026-09-25)
def lock_leave_arm(src):
    at = src.find("elif opcode == GAME_CMSG_PARTY_LEAVE:")
    arm = src[at:at + 700] if at >= 0 else ""
    return (at >= 0 and "if PARTY_LEAVE_ENABLED:" in arm
            and "handle_party_leave(values, send, state, conn_id)" in arm
            and src.count("def handle_party_leave(") == 1
            and "GAME_CMSG_PARTY_LEAVE = 0x00A2" in src
            and "HEROES_ALL = 40" in src)


def lock_main_leave(m):
    return ("a.no_party_leave" in m and "PARTY_LEAVE_ENABLED = False" in m
            and "global PARTY_LEAVE_ENABLED" in m)


LEAVE_FIELD = "if instance_is_field(state):"
LEAVE_POP = "for aid in ids:\n        party.pop(aid)"
LEAVE_BATCH = "henchparty.party_leave_batch(1, PLAYER_NUMBER, size, ids)"


def lock_party_leave(s):
    return (LEAVE_FIELD in s and LEAVE_POP in s and s.find(LEAVE_FIELD) < s.find(LEAVE_POP)
            and "size = party_size_on_wire(state)" in s and LEAVE_BATCH in s
            and 'state.setdefault("party_henchmen"' in s
            and "charstore" not in s and "set_hero_kicked" not in s)


HK_ALL = "if hid == HEROES_ALL:"
HK_GATE = "if not PARTY_LEAVE_ENABLED:"
HK_EACH = "handle_hero_kick([values[0], h], send, state, conn_id)"


def lock_hero_kick_all(s):
    """The HEROES_ALL arm sits BEFORE the owned-hero lookup (40 is no owned index,
    so after it the arm could never run), is gated on PARTY_LEAVE_ENABLED, and
    kicks each party hero through the handler itself."""
    at = s.find(HK_ALL)
    return (at >= 0 and at < s.find("slot = next(") and s.count(HK_ALL) == 1
            and HK_GATE in s[at:] and HK_EACH in s[at:]
            and s.find(HK_GATE) < s.find(HK_EACH))


def lock_main_constant_cap(m):
    """--constant-party-cap turns the per-map read off, and so does --henchman-cap
    (the override covers every map)."""
    return ("a.constant_party_cap" in m and m.count("PARTY_CAP_PER_MAP = False") == 2
            and "global OUTPOST_PARTY_CAP, PARTY_CAP_PER_MAP" in m)


def lock_party_cap_fn(s):
    return ("henchparty.party_cap(MAP_PARTY_CAPS, state.get(\"map_id\")" in s
            and "per_map=PARTY_CAP_PER_MAP" in s and 'state.get("party_cap_said")' in s)


def lock_caps_load(s):
    return ('world.rows("map_party_cap")' in s and "if n < 1:" in s and "raise SystemExit" in s)


def lock_leave_allowlist(dropped):
    return 0x00A2 not in dropped


# the arm's gate: mutate the first "if HENCHMAN_ADD_ENABLED:" AFTER the anchor.
_at = SRC.find("elif opcode == GAME_CMSG_HENCHMAN_ADD:")
_g = SRC.find("if HENCHMAN_ADD_ENABLED:", _at) if _at >= 0 else -1
MUT_ARM = (SRC[:_g] + "if True:" + SRC[_g + len("if HENCHMAN_ADD_ENABLED:"):]) if _g >= 0 else SRC
_atk = SRC.find("elif opcode == GAME_CMSG_HENCHMAN_KICK:")
_gk = SRC.find("if HENCHMAN_KICK_ENABLED:", _atk) if _atk >= 0 else -1
MUT_KICK_ARM = (SRC[:_gk] + "if True:" + SRC[_gk + len("if HENCHMAN_KICK_ENABLED:"):]) if _gk >= 0 else SRC
_atl = SRC.find("elif opcode == GAME_CMSG_PARTY_LEAVE:")
_gl = SRC.find("if PARTY_LEAVE_ENABLED:", _atl) if _atl >= 0 else -1
MUT_LEAVE_ARM = (SRC[:_gl] + "if True:" + SRC[_gl + len("if PARTY_LEAVE_ENABLED:"):]) if _gl >= 0 else SRC

M, SP, HA, HK, HD, PW, HKK, HPL, PCF, MPC = (
    FUNCS.get(k, "") for k in
    ("main", "spawn_population", "handle_henchman_add", "handle_hero_kick", "handle_hero_add",
     "party_size_on_wire", "handle_henchman_kick", "handle_party_leave", "party_cap",
     "_load_map_party_caps"))
LOCKS = [
    ("the 0x00A2 arm exists, is gated on PARTY_LEAVE_ENABLED, calls handle_party_leave once, and "
     "the constants are 0x00A2 / HEROES_ALL 40 (desk-partycap)",
     lock_leave_arm, SRC, [("the gate removed", MUT_LEAVE_ARM),
                           ("the constant renumbered", _mut(SRC, "GAME_CMSG_PARTY_LEAVE = 0x00A2",
                                                             "GAME_CMSG_PARTY_LEAVE = 0x00A3")),
                           ("HEROES_ALL renumbered", _mut(SRC, "HEROES_ALL = 40", "HEROES_ALL = 41"))]),
    ("main() reads --no-party-leave and turns both arms off through a `global`",
     lock_main_leave, M,
     [("the assignment inverted", _mut(M, "PARTY_LEAVE_ENABLED = False", "PARTY_LEAVE_ENABLED = True")),
      ("the global dropped", _mut(M, "global PARTY_LEAVE_ENABLED", "pass"))]),
    ("handle_party_leave refuses a field FIRST, pops every hired henchman, sizes through "
     "party_size_on_wire, sends party_leave_batch and names no store",
     lock_party_leave, HPL,
     [("the field gate removed", _mut(HPL, LEAVE_FIELD, "if False:")),
      ("the pop made a read", _mut(HPL, LEAVE_POP, "for aid in ids:\n        party.get(aid)")),
      ("the size taken from the count", _mut(HPL, "size = party_size_on_wire(state)",
                                              "size = party_member_count(state)")),
      ("a store write added", HPL.replace(LEAVE_POP, LEAVE_POP + "\n    "
                                          "state['charstore_game'].set_hero_kicked(0, aid)", 1))]),
    ("handle_hero_kick's HEROES_ALL arm sits before the owned-hero lookup, is gated on "
     "PARTY_LEAVE_ENABLED and kicks each party hero through the handler",
     lock_hero_kick_all, HK,
     [("the gate dropped", _mut(HK, HK_GATE, "if False:")),
      ("the arm disabled", _mut(HK, HK_ALL, "if False:")),
      ("the arm moved after the owned check", HK.replace(HK_ALL, "if False:", 1).replace(
          "slot = next(", "if hid == HEROES_ALL:\n        pass\n    slot = next(", 1))]),
    ("main() reads --constant-party-cap and turns the per-map read off, and --henchman-cap turns "
     "it off too (the override covers every map)",
     lock_main_constant_cap, M,
     [("the flag's assignment dropped", _mut(M, "PARTY_CAP_PER_MAP = False", "pass")),
      ("--henchman-cap's line dropped", _mut_last(M, "PARTY_CAP_PER_MAP = False", "pass")),
      ("the global dropped", _mut(M, "global OUTPOST_PARTY_CAP, PARTY_CAP_PER_MAP", "pass"))]),
    ("party_cap(state) resolves through henchparty.party_cap over MAP_PARTY_CAPS and the map id, "
     "rides PARTY_CAP_PER_MAP, and prints once per answer",
     lock_party_cap_fn, PCF,
     [("the flag ignored", _mut(PCF, "per_map=PARTY_CAP_PER_MAP", "per_map=True")),
      ("the once-guard dropped", _mut(PCF, 'state.get("party_cap_said")', "None"))]),
    ("MAP_PARTY_CAPS is built from the map_party_cap content rows and a cap below 1 refuses the launch",
     lock_caps_load, MPC,
     [("the refusal dropped", _mut(MPC, "if n < 1:", "if False:")),
      ("another kind read", _mut(MPC, 'world.rows("map_party_cap")', 'world.rows("map")'))]),
]
led.ok('"--no-party-leave"' in ARGS and ARGS.index('"--no-party-leave"') > ARGS.index('"--no-henchman-kick"')
       and '"--constant-party-cap"' in ARGS
       and ARGS.index('"--constant-party-cap"') > ARGS.index('"--party-full-reply"'),
       "LOCK: serverargs.py declares --no-party-leave beside --no-henchman-kick and "
       "--constant-party-cap beside --party-full-reply")
LOCKS += [
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
    ("handle_henchman_kick refuses through kick_refusal (the launch henchman named to it), pops the "
     "party, sizes through party_size_on_wire, sends henchman_kick_batch and names no store",
     lock_hench_kick, HKK,
     [("the refusal removed", _mut(HKK, KICK_REFUSAL, "why = None and henchparty.kick_refusal(")),
      ("the launch guard dropped (RV-6)", _mut(HKK, KICK_LAUNCH, "launch_agent=None")),
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
    ("handle_henchman_add resolves the cap through party_cap(state), caps on party_member_count vs "
     "it, records the henchman and sizes through party_size_on_wire",
     lock_hench_add, HA,
     [("the cap check removed", _mut(HA, CAP_CHECK, "False")),
      ("the constant compared directly (the pre-2026-09-25 text)",
       _mut(HA, CAP_CHECK, OLD_CAP_CHECK)),
      ("the per-map resolution dropped", _mut(HA, CAP_CALL, 'cap, cap_why = OUTPOST_PARTY_CAP, ""')),
      ("the size taken from the count", _mut(HA, "size = party_size_on_wire(state)",
                                              "size = party_member_count(state)"))]),
    ("handle_hero_kick sizes through party_size_on_wire (hired henchmen counted)",
     lock_hero_kick, HK,
     [("the landing's sum restored", _mut(HK, "party_size = party_size_on_wire(state)",
                                          "party_size = " + OLD_SUM + " + len(remaining)"))]),
    ("handle_hero_add sizes through party_size_on_wire and refuses at the same per-map cap",
     lock_hero_add, HD,
     [("the landing's sum restored", _mut(HD, "party_size = party_size_on_wire(state)",
                                          "party_size = " + OLD_SUM + " + len(party_hero_slots(state))")),
      ("the cap check removed", _mut(HD, CAP_CHECK, "False")),
      ("the per-map resolution dropped", _mut(HD, CAP_CALL, 'cap, cap_why = OUTPOST_PARTY_CAP, ""'))]),
    ("party_size_on_wire rides PARTY_SIZE_COUNTS_HEROES (the load's revert arm)",
     lock_wire, PW,
     [("the flag ignored", _mut(PW, "count_heroes=PARTY_SIZE_COUNTS_HEROES", "count_heroes=True"))]),
]


# -- the refusal at the cap (desk-partyfull): the reply rides the CAP branch of BOTH
# handlers, through the leaf, off PARTY_FULL_REPLY_CODE; main() wires the flag.
FULL_REPLY = "henchparty.party_full_reply(PARTY_FULL_REPLY_CODE)"


def lock_full_reply(s):
    at = s.find(CAP_CHECK)
    branch = s[at:at + 900] if at >= 0 else ""
    return (at >= 0 and FULL_REPLY in branch and s.count(FULL_REPLY) == 1
            and "party_full_refusal_note()" in branch
            and s.find(FULL_REPLY) > at)


def lock_main_full(m):
    return ("a.party_full_reply" in m and "PARTY_FULL_REPLY_CODE = int(a.party_full_reply)" in m
            and "henchparty.party_full_reply(int(a.party_full_reply))" in m)


LOCKS += [
    ("handle_henchman_add's CAP branch sends party_full_reply(PARTY_FULL_REPLY_CODE) once and "
     "prints party_full_refusal_note()",
     lock_full_reply, HA,
     [("the reply dropped", _mut(HA, FULL_REPLY, "[]")),
      ("the reply moved before the cap check", HA.replace(FULL_REPLY, "[]", 1).replace(
          "if " + CAP_CHECK, "for op, vals, label in " + FULL_REPLY + ":\n        send(op, vals, label)\n    if " + CAP_CHECK, 1)),
      ("the note replaced by the old constant", _mut(HA, "party_full_refusal_note()",
                                                    "'nothing sent'"))]),
    ("handle_hero_add's CAP branch sends party_full_reply(PARTY_FULL_REPLY_CODE) once and "
     "prints party_full_refusal_note()",
     lock_full_reply, HD,
     [("the reply dropped", _mut(HD, FULL_REPLY, "[]")),
      ("the note replaced by the old constant", _mut(HD, "party_full_refusal_note()",
                                                    "'nothing sent'"))]),
    ("main() reads --party-full-reply, validates the code through the leaf and sets the global",
     lock_main_full, M,
     [("the assignment dropped", _mut(M, "PARTY_FULL_REPLY_CODE = int(a.party_full_reply)",
                                      "pass")),
      ("the validation dropped", _mut(M, "henchparty.party_full_reply(int(a.party_full_reply))",
                                      "pass"))]),
]
led.ok('"--party-full-reply"' in ARGS and ARGS.index('"--party-full-reply"') > ARGS.index('"--henchman-cap"')
       and "default=None" in ARGS[ARGS.index('"--party-full-reply"'):ARGS.index('"--party-full-reply"') + 120],
       "LOCK: serverargs.py declares --party-full-reply beside --henchman-cap, default None (OFF)")
led.ok(authsrv.PARTY_FULL_REPLY_CODE is None and henchparty.PARTY_ERROR_PROMPT == 0x01BC
       and henchparty.PARTY_ERROR_CODE_MAX == 80,
       "LOCK: the module default is OFF (None), the carrier is 0x01BC and the table's last row 80 "
       "(81 rows; 81 is the client's no-error sentinel -- the review of 2026-09-25 corrected 82)")
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
led.ok(lock_leave_allowlist(test_dispatch.DROPPED_ON_PURPOSE),
       "LOCK: 0x00A2 PARTY_LEAVE is off DROPPED_ON_PURPOSE (its arm landed, desk-partycap)")
led.ok(not lock_leave_allowlist(set(test_dispatch.DROPPED_ON_PURPOSE) | {0x00A2}),
       "KNOWN-BAD: 0x00A2 on the allowlist reddens the lock")


# -- §5 the content rows and the leave's sites against the PINNED CLIENT (vaulted) ---
# A check the binary can refute: every content/partycap.toml max_party equals the
# client's own AreaInfo field, read fresh; and the leave's four sites hold the bytes
# the docstrings quote. A bare machine (no pinned client) declares the skip.
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
try:
    import pinned                                             # noqa: E402
    import areatable                                          # noqa: E402
    from gwpe import PE                                       # noqa: E402
    _exe, _why = pinned.find()
except (SystemExit, Exception) as exc:                        # noqa: BLE001
    led.skip("§5 the pinned client", f"no pinned build 38797 in the vault: {str(exc)[:80]}")
else:
    _pe = PE(_exe)
    _base = 0x0096DE38
    _off = _pe.rva_to_off(_base - _pe.image_base)
    led.ok(_base in areatable.locate_from_code(_pe),
           "(§5) the code locator (`imul reg, reg, 0x7C` + a nearby .rdata base) names VA "
           "0x0096DE38, the area table content/partycap.toml's rows cite")
    led.ok(areatable.extent(_pe.data, _off) == 888,
           "(§5) 888 consecutive records validate from it (the table's own extent)")
    _bad = {}
    _rows = authsrv.agents.WORLD.rows("map_party_cap")
    for _m, _cap in sorted(_saved_caps.items()):
        _rec = areatable.parse_record(_pe.data, _off + _m * areatable.RECORD_SIZE)
        _min = int(_rows[str(_m)]["min_party"])
        if _rec["max_party"] != _cap or _rec["min_party"] != _min:
            _bad[_m] = ((_rec["min_party"], _rec["max_party"]), (_min, _cap))
    led.ok(not _bad and len(_saved_caps) >= 19,
           f"(§5) every content/partycap.toml row ({len(_saved_caps)}) equals the client's own "
           f"min_party / max_party (OFF_MIN_PARTY +0x18 / OFF_MAX_PARTY +0x1C) -- re-read out of "
           f"the pinned build, not recalled (the first cut said min 1 everywhere and this check "
           f"reddened on 167/168, whose retail rows say 7)", f"mismatches (client, row) {_bad}")
    _rec148 = areatable.parse_record(_pe.data, _off + 148 * areatable.RECORD_SIZE)
    led.ok(_rec148["max_party"] == 4 and _rec148["type"] == 10 and _rec148["name_id"] == 10478,
           "(§5) CONTROL: row 148 reads max_party 4, type 10, name id 10478 -- the row the panel's "
           "(2/4) was drawn from", f"{_rec148}")

    def _at(va, n):
        o = _pe.rva_to_off(va - _pe.image_base)
        return _pe.data[o:o + n]
    led.ok(_at(0x0085BEF7, 7) == bytes.fromhex("c745fca2000000")
           and _at(0x008585FD, 2) == bytes.fromhex("0f87")
           and _at(0x0080E2A7, 3) == bytes.fromhex("83fe28")
           and _at(0x0056E95D, 2) == bytes.fromhex("6a28"),
           "(§5) the leave's four sites read as documented on build 38797: the 0xA2 store at "
           "0x0085BEF7, the `ja` at 0x008585FD, the `cmp esi, 0x28` (HEROES) at 0x0080E2A7 and "
           "PtJoin's `push 0x28` at 0x0056E95D")
    _rel = int.from_bytes(_at(0x008585FF, 4), "little", signed=True)
    led.ok(0x008585FD + 6 + _rel == 0x0085BEF0,
           "(§5) ...and the `ja` lands on the 0xA2 wrapper 0x0085BEF0 -- the one reference codescan "
           "--xrefs (call/jmp only) reported as none", f"target 0x{0x008585FD + 6 + _rel:08X}")

# -- §5 the 248 set stands on 248's OWN mesh (vaulted: the archive) -----------------
# A check the archive can refute (the review's RV-1): each outpost_henchmen_248 row
# is walkable on file 165811's compiled pathing chunk with place_on_mesh moving it
# 0 u -- the rows' provenance says so, and this is what says so about the provenance.
# The archive is found through vaultpath (RURIK_VAULT), so a bare machine declares
# the skip and the floor excludes these.
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
try:
    import vaultpath                                          # noqa: E402
    from archive import Archive                               # noqa: E402
    from pathmap import PathingMap                            # noqa: E402
    import population                                         # noqa: E402
    _dat = vaultpath.vault_path("dat_study", "Gw.dat")
    if not os.path.exists(_dat):
        raise FileNotFoundError(_dat)
    _ar = Archive(_dat)
    try:
        _pm248 = PathingMap.load(165811, archive=_ar)
    finally:
        _ar.close()
except (SystemExit, Exception) as exc:                        # noqa: BLE001
    led.skip("§5 the 248 set on its mesh", f"no archive with file 165811 in the vault: {str(exc)[:80]}")
else:
    _rows248 = {k: r for k, r in authsrv.agents.WORLD.rows("spawn").items()
                if r.get("area") == "outpost_henchmen_248"}
    _moved = {}
    for _k, _r in sorted(_rows248.items()):
        _res = population.place_on_mesh(_pm248, float(_r["x"]), float(_r["y"]), _k)
        if _res is None or _res[2] != 0.0:
            _moved[_k] = _res
    led.ok(len(_rows248) == 3 and not _moved,
           "(§5) the three outpost_henchmen_248 rows stand on map 248's own mesh (file 165811, "
           f"{len(_pm248.planes)} planes / {len(_pm248.trapezoids)} trapezoids): place_on_mesh "
           "moves none of them -- re-read out of the archive, as the rows' provenance claims",
           f"nudged/refused {_moved}")
    _arr = authsrv.MAP_STATIC_CONFIG[248][1]
    led.ok(_pm248.walkable(float(_arr[0]), float(_arr[1])),
           "(§5) CONTROL: 248's own arrival (maps.toml spawn_x/spawn_y) is walkable on that mesh -- "
           "the point the three offsets are measured from", f"arrival {_arr}")

sys.exit(led.verdict())
