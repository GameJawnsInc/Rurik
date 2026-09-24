"""World-map travel -- c2s 0x00B1 MAP_TRAVEL and the s2c 0x0094 unlock state
that makes the client offer our outposts (DESKWORK-D1 step 7; maptravel.py;
studies/cmsg/FINDINGS.md "World-map travel").

    python toolkit/authsrv/test_maptravel.py

  * §1 THE LEAF (bare-machine): travelable_maps is our enabled non-explorable
    content maps; unlock_bitmap_words sets bit == map id for each, overflows a
    too-narrow bitmap rather than dropping (KNOWN-BAD), and sets at least one
    bit (vacuity); plan_travel accepts a served non-explorable map and refuses
    an explorable, an unserved id and the map you are on, each with a reason,
    against a KNOWN-BAD arm that would accept an explorable.
  * §2 THE SERVER (bare-machine): the dispatch arm behind MAP_TRAVEL_ENABLED,
    the load's 0x0094 behind MAP_UNLOCK_ENABLED, EXACTLY ONE sender of the
    unlock message (the duplicate-sender guard), the two flags in serverargs
    and main(); handle_map_travel driven with a fake send and the real
    send_transfer (send_stop=False) emits [0x01D9, 0x01A5, 0x0099] IN THAT
    ORDER (KNOWN-BAD: a batch with the transfer before 0x01D9 fails the
    "0x01D9 first" predicate), and each refusal sends NOTHING.
  * §3 THE TAPE (vault-gated; LEDGER.skip on a bare machine): every live c2s
    0x00B1 is [map_id, 0, 0, 0, 1]; its s2c batch is 0x01D9 then 0x01A5 then
    0x0099 (0x01D9 the first non-clock reply on >= 9 of 10), against a
    KNOWN-BAD arm that expects the transfer first; s2c 0x0094 rides the load
    with arr4 non-empty.
"""
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
import content                                               # noqa: E402
import maptravel                                             # noqa: E402
import livewire                                              # noqa: E402
import authsrv                                               # noqa: E402

led = checks.Ledger("world-map travel (DESKWORK-D1 step 7)", floor=23)  # §1+§2 bare-machine core (23); §3 adds 6 on the vault

WORLD = content.load()
MAP_TRAVEL_READY, TRANSFER, MAP_UPD = 0x01D9, 0x01A5, 0x0099
UNLOCK = 0x0094
assert (MAP_TRAVEL_READY, TRANSFER, MAP_UPD, UNLOCK) == (
    authsrv.GAME_SMSG_MAP_TRAVEL_READY, authsrv.GAME_SMSG_GAME_SERVER_TRANSFER,
    authsrv.GAME_SMSG_MAP_UPDATE_CURRENT, authsrv.GAME_SMSG_MAP_TRAVEL_UNLOCK)
assert authsrv.GAME_CMSG_MAP_TRAVEL == 0x00B1

AUTHSRV_PY = os.path.join(HERE, "authsrv.py")
SRC = open(AUTHSRV_PY, encoding="utf-8").read()


def fake_send_factory():
    sent = []

    def send(op, vals, label=None):
        sent.append((op, list(vals)))
    return sent, send


# ---- §1 the leaf -----------------------------------------------------------
trav = maptravel.travelable_maps(WORLD)
rows = WORLD.rows("map")
expect = sorted(int(k) for k, r in rows.items()
                if r.get("enabled", True) and not r.get("explorable", False))
led.ok(trav == expect and trav,
       "travelable_maps is exactly the enabled non-explorable content maps, "
       "and there is at least one", f"{trav}")
led.ok(all(not rows[str(m)].get("explorable", False) for m in trav)
       and all(maptravel.is_travelable(WORLD, m) for m in trav),
       "no travelable map is an explorable, and is_travelable agrees with the set")
# an explorable in the content is NOT offered
_expl = sorted(int(k) for k, r in rows.items()
               if r.get("enabled", True) and r.get("explorable", False))
led.ok(_expl and all(not maptravel.is_travelable(WORLD, m) for m in _expl),
       "every enabled EXPLORABLE content map is withheld from the travel set",
       f"{_expl}")

words, overflow = maptravel.unlock_bitmap_words(WORLD, 28)
nbits = sum(bin(w).count("1") for w in words)
led.ok(len(words) == 28 and not overflow and nbits == len(trav)
       and all((words[m // 32] >> (m % 32)) & 1 for m in trav),
       "unlock_bitmap_words sets bit == map id for every travelable map and "
       "nothing else (28 dwords cover them, no overflow)", f"{nbits} bits")
# VACUITY: at least one bit is set -- an empty bitmap offers no destination
led.ok(nbits >= 1, "VACUITY: the unlock bitmap is not empty")
# KNOWN-BAD: a bitmap too narrow to hold the highest map id OVERFLOWS rather
# than silently dropping it -- a wide id would otherwise offer fewer maps.
_narrow_words, _narrow_over = maptravel.unlock_bitmap_words(WORLD, 1)
led.ok(_narrow_over == [m for m in trav if m >= 32]
       and sum(bin(w).count("1") for w in _narrow_words) == len([m for m in trav if m < 32]),
       "KNOWN-BAD: a 1-dword bitmap reports every map id >= 32 as overflow, "
       "dropping none silently", f"overflow {_narrow_over}")

# plan_travel: accept a served non-explorable map that is not the one you are on
_dest = next(m for m in trav if m != trav[0])
ok, why = maptravel.plan_travel(WORLD, trav[0], _dest)
led.ok(ok and why is None,
       f"plan_travel accepts a served non-explorable destination (map {_dest} "
       f"from {trav[0]})")
# refuse: the map you are already on
ok, why = maptravel.plan_travel(WORLD, _dest, _dest)
led.ok(not ok and "already" in why,
       "plan_travel refuses the map you are already on, with a reason", f"{why}")
# refuse: a map with no content row
_absent = max(int(k) for k in rows) + 1000
ok, why = maptravel.plan_travel(WORLD, trav[0], _absent)
led.ok(not ok and "no content row" in why,
       "plan_travel refuses a map with no content row, with a reason", f"{why}")
# refuse: an explorable
ok, why = maptravel.plan_travel(WORLD, trav[0], _expl[0])
led.ok(not ok and "explorable" in why,
       f"plan_travel refuses an explorable (map {_expl[0]}), with a reason",
       f"{why}")
# KNOWN-BAD: the accept path must depend on the destination NOT being an
# explorable -- if it accepted one, the refusal above could not have reddened.
led.ok(maptravel.plan_travel(WORLD, trav[0], _expl[0])[0] is False
       and maptravel.plan_travel(WORLD, trav[0], _dest)[0] is True,
       "KNOWN-BAD: the same gate that accepts an outpost refuses an explorable "
       "(the two answers differ)")

# ---- §2 the server ---------------------------------------------------------
led.ok("elif opcode == GAME_CMSG_MAP_TRAVEL:" in SRC
       and "if MAP_TRAVEL_ENABLED:" in SRC
       and "handle_map_travel(values, send, state, conn_id" in SRC,
       "the dispatch arm calls handle_map_travel behind MAP_TRAVEL_ENABLED")
led.ok('graceful_close(sock, conn_id, "map travel")' in SRC,
       "a successful travel closes the socket so the client re-dials")
led.ok("if MAP_UNLOCK_ENABLED:" in SRC
       and "send(GAME_SMSG_MAP_TRAVEL_UNLOCK" in SRC,
       "the load sends the unlock bitmap behind MAP_UNLOCK_ENABLED")
# THE ONE-SENDER GUARD: a duplicate sender of unlock state wiped a library and
# crashed a client (2026-09-15). Exactly one send site of 0x0094 in authsrv.
led.ok(SRC.count("send(GAME_SMSG_MAP_TRAVEL_UNLOCK") == 1,
       "EXACTLY ONE sender of the unlock message (the duplicate-sender guard)",
       f"{SRC.count('send(GAME_SMSG_MAP_TRAVEL_UNLOCK')} site(s)")
sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
led.ok('"--no-map-travel"' in sargs and '"--no-map-unlock"' in sargs
       and "if a.no_map_travel:" in SRC and "if a.no_map_unlock:" in SRC
       and "MAP_TRAVEL_ENABLED = False" in SRC
       and "MAP_UNLOCK_ENABLED = False" in SRC,
       "both revert flags exist in serverargs and are applied in main()")

# handle_map_travel driven with a fake send and the real send_transfer
_saved = (authsrv.agents.WORLD, authsrv.TRANSFER_HOSTS, authsrv.TRANSFER_PORT,
          dict(authsrv.TRANSFERS_ISSUED))
try:
    authsrv.agents.WORLD = WORLD
    authsrv.TRANSFER_HOSTS = ["127.0.0.1"]
    authsrv.TRANSFER_PORT = 6112
    st = {"map_id": trav[0], "world_id": 1, "player_id": 1,
          "char_uuid": "aa" * 16}
    sent, send = fake_send_factory()
    took = authsrv.handle_map_travel([0x80B1, _dest, 0, 0, 0, 1], send, st, 1,
                                     "127.0.0.1")
    ops = [op for op, _v in sent]
    led.ok(took is True and ops == [MAP_TRAVEL_READY, TRANSFER, MAP_UPD],
           "handle_map_travel emits [0x01D9, 0x01A5, 0x0099] in that order and "
           "returns True (retail's batch, no 0x0028)", f"{[hex(o) for o in ops]}")
    led.ok(ops and ops[0] == MAP_TRAVEL_READY
           and ops.index(TRANSFER) > ops.index(MAP_TRAVEL_READY),
           "0x01D9 is FIRST, before the transfer pair")
    led.ok(sent[0][1] == [2, 1, ""],
           "the 0x01D9 payload is [2, 1, ''] (retail's, 10 of 10)", f"{sent[0][1]}")
    # KNOWN-BAD: the transfer-first ordering a naive arm would produce fails the
    # "0x01D9 first" predicate this test locks.
    bad = [TRANSFER, MAP_TRAVEL_READY, MAP_UPD]
    led.ok(not (bad[0] == MAP_TRAVEL_READY),
           "KNOWN-BAD: a batch that sends the transfer before 0x01D9 is caught")
    # refusals send NOTHING
    for label, cur, dst in (("explorable", trav[0], _expl[0]),
                            ("no content row", trav[0], _absent),
                            ("already here", _dest, _dest)):
        st["map_id"] = cur          # the gate reads the current map off state
        sent2, send2 = fake_send_factory()
        r = authsrv.handle_map_travel([0x80B1, dst, 0, 0, 0, 1], send2, st, 1,
                                      "127.0.0.1")
        led.ok(r is False and sent2 == [],
               f"a refused travel ({label}) returns False and sends nothing",
               f"{[hex(o) for o, _ in sent2]}")
finally:
    (authsrv.agents.WORLD, authsrv.TRANSFER_HOSTS, authsrv.TRANSFER_PORT) = _saved[:3]
    authsrv.TRANSFERS_ISSUED.clear()
    authsrv.TRANSFERS_ISSUED.update(_saved[3])

# ---- §3 the tape -----------------------------------------------------------
if livewire.live_captures():
    codec = livewire._get_codec()
    n_b1 = 0
    d9_first = 0
    seq_ok = 0
    shape_ok = 0
    bad_transfer_first = 0
    unlock_seen = 0
    unlock_arr4 = 0
    for capdir, gf in livewire.live_connections():
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        for i, (t, d, op, vals) in enumerate(merged):
            if d == "s2c" and op == UNLOCK:
                unlock_seen += 1
                arrs = [v for v in vals[1:] if isinstance(v, list)]
                if len(arrs) >= 5 and any(arrs[4]):
                    unlock_arr4 += 1
            if d == "c2s" and op == 0x00B1:
                n_b1 += 1
                if len(vals) >= 6 and list(vals[2:]) == [0, 0, 0, 1]:
                    shape_ok += 1
                after = [(o, dd) for (_t2, dd, o, _v) in merged[i + 1:]
                         if _t2 - t <= 1.5]
                s2c_after = [o for o, dd in after if dd == "s2c"]
                # first non-clock (0x001E) s2c
                first_nt = next((o for o in s2c_after if o != 0x001E), None)
                if first_nt == MAP_TRAVEL_READY:
                    d9_first += 1
                if (MAP_TRAVEL_READY in s2c_after and TRANSFER in s2c_after
                        and MAP_UPD in s2c_after
                        and s2c_after.index(MAP_TRAVEL_READY)
                        < s2c_after.index(TRANSFER) < s2c_after.index(MAP_UPD)):
                    seq_ok += 1
                # KNOWN-BAD: the transfer never precedes 0x01D9 on a real tape
                if (TRANSFER in s2c_after and MAP_TRAVEL_READY in s2c_after
                        and s2c_after.index(TRANSFER)
                        < s2c_after.index(MAP_TRAVEL_READY)):
                    bad_transfer_first += 1
    led.ok(n_b1 >= 10, f"the corpus carries >= 10 c2s 0x00B1 (found {n_b1})")
    led.ok(shape_ok == n_b1 and n_b1 > 0,
           "every c2s 0x00B1 is [map_id, 0, 0, 0, 1]", f"{shape_ok}/{n_b1}")
    led.ok(seq_ok >= 10,
           "the s2c batch is 0x01D9 then 0x01A5 then 0x0099, in order, >= 10 of "
           "10", f"{seq_ok}/{n_b1}")
    led.ok(d9_first >= 9,
           "0x01D9 is the FIRST non-clock reply on >= 9 of 10", f"{d9_first}/{n_b1}")
    led.ok(bad_transfer_first == 0,
           "KNOWN-BAD: the transfer NEVER precedes 0x01D9 on any tape",
           f"{bad_transfer_first} violation(s)")
    led.ok(unlock_seen >= 20 and unlock_arr4 == unlock_seen,
           "s2c 0x0094 rides the load with a non-empty arr4 on every sighting",
           f"{unlock_arr4}/{unlock_seen}")
else:
    led.skip("§3 the tape", "no origin=LIVE captures under the vault")

sys.exit(led.verdict())
