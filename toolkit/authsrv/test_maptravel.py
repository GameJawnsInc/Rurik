"""World-map travel -- c2s 0x00B1 MAP_TRAVEL and the s2c 0x0094 unlock state
that makes the client offer our outposts (DESKWORK-D1 step 7; maptravel.py;
studies/cmsg/FINDINGS.md "World-map travel", corrected by the fix pass).

    python toolkit/authsrv/test_maptravel.py

  * §1 THE LEAF (bare-machine): travelable_maps is our enabled non-explorable
    content maps with a KNOWN spawn (the (0, 0) placeholder rows withheld, and
    a KNOWN-BAD fake world where the same row is given a spawn puts it back);
    an exclusion dict withholds an unwarmed destination; unlock_bitmap_words
    sets bit == map id at the SERVER's own width, overflows a too-narrow bitmap
    rather than dropping (KNOWN-BAD), and sets at least one bit (vacuity);
    unlock_message puts the words in arr4 and the payload predicate refuses
    them in arr0 (KNOWN-BAD); plan_travel accepts a served map and refuses an
    explorable, an unserved id, the map you are on, a placeholder spawn and an
    unwarmed destination, each with a reason -- and a KNOWN-BAD fake world
    with the explorable flag stripped is ACCEPTED, so the refusal reads the
    flag; travel_batch_ok is True on retail's batch and False on a reordered,
    a 0x01D9-less and a 0x0028-bearing one; arrival_skips_unlock is one-shot,
    map-checked and stale-aware.
  * §2 THE SERVER (bare-machine): the dispatch arm behind MAP_TRAVEL_ENABLED;
    the login's 0x0094 behind its gate, locked by CONTEXT (a KNOWN-BAD text with
    the gate replaced by `if True:` fails the same predicate); EXACTLY ONE
    0x0094 send site across toolkit/authsrv/*.py counted over EVERY spelling;
    BOTH writers of arr4 present and in order -- 0x0199, then 0x0094, then the
    fog pair, then the burst's 0x0099 (a KNOWN-BAD swapped text fails the
    order predicate); the revert flags applied contiguously; the prewarm gated
    on --map and the arm; handle_map_travel driven with a fake send and the real
    send_transfer emits retail's batch (travel_batch_ok), and the SAME predicate
    goes False when a send wrapper DROPS 0x01D9 from the real handler's output
    (KNOWN-BAD); the transfer records the one-shot arrival marker, which the
    load's check then consumes; each refusal sends NOTHING.
  * §3 THE TAPE (vault-gated; LEDGER.skip on a bare machine): every live c2s
    0x00B1 is [map_id, 0, 0, 0, 1]; its s2c batch is 0x01D9 then 0x01A5 then
    0x0099 (0x01D9 the first non-clock reply on >= 9 of 10), against a
    KNOWN-BAD arm that expects the transfer first; s2c 0x0094 rides a LOGIN's
    first map-loading connection and NEVER a transfer arrival, sits after
    0x0199 and before 0x008B, is 27 dwords wide with a non-empty arr4; and the
    JOIN: every 0x00B1 destination's bit was set before the click, by the
    login's 0x0094 or by a prior 0x0099 -- with at least one set by 0x0099
    alone (the 281 case that refuted "every destination set at load").
"""
import glob
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

led = checks.Ledger("world-map travel (DESKWORK-D1 step 7)", floor=45)  # §1+§2 bare-machine core (45, from the green run with RURIK_VAULT empty); §3 adds 10 on the vault (55)

WORLD = content.load()
MAP_TRAVEL_READY, TRANSFER, MAP_UPD = 0x01D9, 0x01A5, 0x0099
UNLOCK = 0x0094
assert (MAP_TRAVEL_READY, TRANSFER, MAP_UPD, UNLOCK) == (
    authsrv.GAME_SMSG_MAP_TRAVEL_READY, authsrv.GAME_SMSG_GAME_SERVER_TRANSFER,
    authsrv.GAME_SMSG_MAP_UPDATE_CURRENT, authsrv.GAME_SMSG_MAP_TRAVEL_UNLOCK)
assert authsrv.GAME_CMSG_MAP_TRAVEL == 0x00B1

AUTHSRV_PY = os.path.join(HERE, "authsrv.py")
SRC = open(AUTHSRV_PY, encoding="utf-8").read()
N_WORDS = authsrv.mission_mask_bytes(authsrv.MAP_ID_COUNT) // 4   # the server's own width


class FakeWorld:
    """A world whose map rows are a modified copy of the real ones -- the
    KNOWN-BAD arms change ONE field of ONE row and show the gate follows it."""
    def __init__(self, rows):
        self._rows = rows

    def rows(self, kind):
        assert kind == "map"
        return self._rows


def world_with(map_id, **changes):
    rows = {k: dict(r) for k, r in WORLD.rows("map").items()}
    rows[str(map_id)].update(changes)
    return FakeWorld(rows)


def fake_send_factory(drop=()):
    sent = []

    def send(op, vals, label=None):
        if op in drop:
            return
        sent.append((op, list(vals)))
    return sent, send


# ---- §1 the leaf -----------------------------------------------------------
trav = maptravel.travelable_maps(WORLD)
rows = WORLD.rows("map")


def _known(r):
    return not (float(r.get("spawn_x", 0.0)) == 0.0 and float(r.get("spawn_y", 0.0)) == 0.0)


expect = sorted(int(k) for k, r in rows.items()
                if r.get("enabled", True) and not r.get("explorable", False) and _known(r))
led.ok(trav == expect and trav,
       "travelable_maps is exactly the enabled non-explorable content maps with a "
       "known spawn, and there is at least one", f"{trav}")
led.ok(all(not rows[str(m)].get("explorable", False) for m in trav)
       and all(maptravel.is_travelable(WORLD, m) for m in trav),
       "no travelable map is an explorable, and is_travelable agrees with the set")
_expl = sorted(int(k) for k, r in rows.items()
               if r.get("enabled", True) and r.get("explorable", False))
led.ok(_expl and all(not maptravel.is_travelable(WORLD, m) for m in _expl),
       "every enabled EXPLORABLE content map is withheld from the travel set",
       f"{_expl}")
# the (0, 0) placeholder rows ([map.194], [map.55]: "not a coordinate") are withheld
_placeholder = sorted(int(k) for k, r in rows.items()
                      if r.get("enabled", True) and not r.get("explorable", False)
                      and not _known(r))
led.ok(_placeholder and all(m not in trav for m in _placeholder),
       "every enabled outpost row with the (0, 0) placeholder spawn is withheld "
       "(no spawn point is known)", f"{_placeholder}")
# KNOWN-BAD: the same row GIVEN a spawn is offered -- the gate reads the spawn
_fw = world_with(_placeholder[0], spawn_x=1234.0, spawn_y=-567.0)
led.ok(_placeholder[0] in maptravel.travelable_maps(_fw)
       and _placeholder[0] not in trav,
       f"KNOWN-BAD: map {_placeholder[0]} with a spawn written into its row IS "
       f"offered (the withholding reads the spawn, not the id)")
# the exclusion dict withholds an unwarmed destination
_ex = {trav[0]: "no navmesh in this archive"}
led.ok(maptravel.travelable_maps(WORLD, _ex) == [m for m in trav if m != trav[0]]
       and not maptravel.is_travelable(WORLD, trav[0], _ex),
       f"an excluded (unwarmed) destination {trav[0]} is withheld and the rest kept")

words, overflow = maptravel.unlock_bitmap_words(WORLD, N_WORDS)
nbits = sum(bin(w).count("1") for w in words)
led.ok(len(words) == N_WORDS and not overflow and nbits == len(trav)
       and all((words[m // 32] >> (m % 32)) & 1 for m in trav),
       f"unlock_bitmap_words sets bit == map id for every travelable map and "
       f"nothing else, at the server's own width ({N_WORDS} dwords; retail's "
       f"arr4 is 27 -- ours is wider, RECONSTRUCTION, safe: CopyBits grows the "
       f"store before its Array:130 check)", f"{nbits} bits")
# VACUITY: at least one bit is set -- an empty bitmap offers no destination
led.ok(nbits >= 1, "VACUITY: the unlock bitmap is not empty")
# KNOWN-BAD: a bitmap too narrow to hold the highest map id OVERFLOWS rather
# than silently dropping it -- a wide id would otherwise offer fewer maps.
_narrow_words, _narrow_over = maptravel.unlock_bitmap_words(WORLD, 1)
led.ok(_narrow_over == [m for m in trav if m >= 32]
       and sum(bin(w).count("1") for w in _narrow_words) == len([m for m in trav if m < 32]),
       "KNOWN-BAD: a 1-dword bitmap reports every map id >= 32 as overflow, "
       "dropping none silently", f"overflow {_narrow_over}")
# unlock_message: the words ride arr4, arr0-3 empty; the predicate refuses arr0
_payload, _label, _over = maptravel.unlock_message(WORLD, N_WORDS)
led.ok(maptravel.unlock_payload_ok(_payload, words) and not _over
       and str(nbits) in _label,
       "unlock_message puts the bitmap in arr4 with arr0-3 empty, and the label "
       "names the count", f"{_label}")
led.ok(not maptravel.unlock_payload_ok([words, [], [], [], []], words)
       and not maptravel.unlock_payload_ok([[], [], [], [], [0] * N_WORDS], [0] * N_WORDS),
       "KNOWN-BAD: the words in arr0, or an all-zero arr4, fail the payload predicate")

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
# KNOWN-BAD: the SAME row with its explorable flag stripped is ACCEPTED (given a
# spawn), so the refusal above reads the flag and not the id.
_fw2 = world_with(_expl[0], explorable=False, spawn_x=100.0, spawn_y=100.0)
led.ok(maptravel.plan_travel(_fw2, trav[0], _expl[0])[0] is True,
       f"KNOWN-BAD: map {_expl[0]} with `explorable` stripped from its row is "
       f"accepted -- the refusal reads the flag")
# refuse: the (0, 0) placeholder spawn
ok, why = maptravel.plan_travel(WORLD, trav[0], _placeholder[0])
led.ok(not ok and "no spawn point" in why,
       f"plan_travel refuses the placeholder-spawn row (map {_placeholder[0]}), "
       f"with a reason", f"{why}")
# refuse: an unwarmed destination
ok, why = maptravel.plan_travel(WORLD, trav[0], _dest, exclude={_dest: "no navmesh"})
led.ok(not ok and "withheld" in why and "no navmesh" in why,
       f"plan_travel refuses an unwarmed destination (map {_dest}) with the "
       f"prewarm's reason", f"{why}")

# travel_batch_ok: retail's batch and the three naive shapes
led.ok(maptravel.travel_batch_ok([MAP_TRAVEL_READY, TRANSFER, MAP_UPD])
       and not maptravel.travel_batch_ok([TRANSFER, MAP_TRAVEL_READY, MAP_UPD])
       and not maptravel.travel_batch_ok([TRANSFER, MAP_UPD])
       and not maptravel.travel_batch_ok([0x0028, MAP_TRAVEL_READY, TRANSFER, MAP_UPD]),
       "travel_batch_ok: True on [0x01D9, 0x01A5, 0x0099]; False reordered, "
       "False without 0x01D9, False with a portal's 0x0028")

# arrival_skips_unlock: one-shot, map-checked, stale-aware
_arr = {}
led.ok(maptravel.arrival_skips_unlock(_arr, (1, 1), 248, 1000.0) is False,
       "arrival_skips_unlock: a fresh login (no marker) does NOT skip -> 0x0094 goes out")
_arr = {(1, 1): (248, 1000.0)}
led.ok(maptravel.arrival_skips_unlock(_arr, (1, 1), 248, 1003.0) is True
       and (1, 1) not in _arr
       and maptravel.arrival_skips_unlock(_arr, (1, 1), 248, 1004.0) is False,
       "arrival_skips_unlock: a re-entry on the transferred map SKIPS once, and "
       "the marker is consumed -- a relaunch on the same map gets its 0x0094")
_arr = {(1, 1): (248, 1000.0)}
led.ok(maptravel.arrival_skips_unlock(_arr, (1, 1), 449, 1003.0) is False
       and (1, 1) not in _arr,
       "arrival_skips_unlock: a login on a DIFFERENT map does not skip and consumes "
       "the stale marker")
_arr = {(1, 1): (248, 1000.0)}
led.ok(maptravel.arrival_skips_unlock(_arr, (1, 1), 248, 1000.0 + 301.0) is False,
       "arrival_skips_unlock: a marker older than the TTL (the re-dial never came) "
       "does not skip")

# ---- §2 the server ---------------------------------------------------------
led.ok("elif opcode == GAME_CMSG_MAP_TRAVEL:" in SRC
       and "if MAP_TRAVEL_ENABLED:" in SRC
       and "handle_map_travel(values, send, state, conn_id" in SRC,
       "the dispatch arm calls handle_map_travel behind MAP_TRAVEL_ENABLED")
led.ok('graceful_close(sock, conn_id, "map travel")' in SRC,
       "a successful travel closes the socket so the client re-dials")
led.ok("exclude=TRAVEL_UNSERVABLE)" in SRC
       and SRC.count("exclude=TRAVEL_UNSERVABLE") == 2,
       "both the arm (plan_travel) and the login's 0x0094 (unlock_message) read "
       "TRAVEL_UNSERVABLE, the prewarm's record of unwarmed destinations")

# the 0x0094 gate, locked by CONTEXT: the gate line immediately precedes the
# unlock_message call, and the send takes that call's payload and label.
GATE = ("if MAP_UNLOCK_ENABLED and not _zoned_in:\n"
        "                _mu_payload, _mu_label, _mu_over = maptravel.unlock_message(")
SEND_SITE = "send(GAME_SMSG_MAP_TRAVEL_UNLOCK, _mu_payload, _mu_label)"


def gate_ok(src):
    return src.count(GATE) == 1 and src.count(SEND_SITE) == 1 and src.index(GATE) < src.index(SEND_SITE)


led.ok(gate_ok(SRC),
       "the login's 0x0094 send is gated on MAP_UNLOCK_ENABLED AND not-a-re-entry, "
       "and sends unlock_message's payload and label (locked by context)")
led.ok(not gate_ok(SRC.replace("if MAP_UNLOCK_ENABLED and not _zoned_in:", "if True:")),
       "KNOWN-BAD: the same text with the gate replaced by `if True:` fails the lock")

# THE ONE-SENDER GUARD, over EVERY spelling, across every server source: a
# duplicate sender of unlock state wiped a library and crashed a client
# (2026-09-15); with two writers of arr4 a second 0x0094 would also wipe what
# 0x0099 set. Counts send(GAME_SMSG_MAP_TRAVEL_UNLOCK|0x0094|0x94|148, ...).
_sites = []
for _p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
    if os.path.basename(_p).startswith("test_"):
        continue
    _txt = open(_p, encoding="utf-8", errors="replace").read()
    for _m in maptravel.UNLOCK_SEND_RE.finditer(_txt):
        _sites.append((os.path.basename(_p), _txt[:_m.start()].count("\n") + 1))
led.ok(len(_sites) == 1 and _sites[0][0] == "authsrv.py",
       "EXACTLY ONE 0x0094 send site across toolkit/authsrv/*.py, counted over "
       "every spelling (the duplicate-sender guard)", f"{_sites}")
led.ok(len(maptravel.UNLOCK_SEND_RE.findall(
           'send(0x0094, [[], [], [], [], []], "second")\n'
           'send(GAME_SMSG_MAP_TRAVEL_UNLOCK, p, l)\nsend(148, x, y)\nsend(0x94,z,w)')) == 4,
       "KNOWN-BAD: the guard's pattern sees a literal 0x0094, 0x94 and 148 sender "
       "as well as the named one (4 of 4 spellings)")

# BOTH WRITERS of arr4, and the order: 0x0199, then 0x0094, then the fog pair,
# then the burst's 0x0099 [map, 0] (which SETS the current map's bit AFTER our
# REPLACE); send_transfer's 0x0099 [dest, 0] is the writer that pre-sets a
# destination on the way out.
LOAD_INFO = "send(GAME_SMSG_INSTANCE_LOAD_INFO,"
FOG_BEGIN = "send(GAME_SMSG_MAP_EXPLORATION_INIT_BEGIN,"
LOAD_99 = 'send(GAME_SMSG_MAP_UPDATE_CURRENT, [state["map_id"], 0]'
XFER_99 = "send(GAME_SMSG_MAP_UPDATE_CURRENT, [int(dest_map), 0]"


def order_ok(src):
    if not all(src.count(a) == 1 for a in (LOAD_INFO, SEND_SITE, FOG_BEGIN, LOAD_99, XFER_99)):
        return False
    return src.index(LOAD_INFO) < src.index(SEND_SITE) < src.index(FOG_BEGIN) < src.index(LOAD_99)


led.ok(order_ok(SRC),
       "BOTH writers of arr4 are present once each (the burst's and the transfer's "
       "0x0099), and the login's 0x0094 sits after 0x0199, before the fog pair, "
       "before the burst's 0x0099 -- retail's bracket, and the replace-then-set order")
_swapped = SRC.replace(SEND_SITE, "@@S@@").replace(LOAD_99, SEND_SITE).replace("@@S@@", LOAD_99)
led.ok(not order_ok(_swapped),
       "KNOWN-BAD: the same text with 0x0094 and the burst's 0x0099 swapped fails "
       "the order predicate (the 0x0094 replace would then wipe the current map)")

sargs = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
led.ok('"--no-map-travel"' in sargs and '"--no-map-unlock"' in sargs
       and "if a.no_map_travel:\n        MAP_TRAVEL_ENABLED = False" in SRC
       and "if a.no_map_unlock:\n        MAP_UNLOCK_ENABLED = False" in SRC,
       "both revert flags exist in serverargs and are applied CONTIGUOUSLY in main() "
       "(a commented-out assignment would fail this)")
PREWARM_GATE = "if a.map is not None and not a.no_map_travel:"
led.ok(SRC.count(PREWARM_GATE) == 1
       and "for _dest in maptravel.travelable_maps(agents.WORLD):" in SRC
       and SRC.index(PREWARM_GATE) < SRC.index("for _dest in maptravel.travelable_maps(agents.WORLD):")
       and 'TRAVEL_UNSERVABLE[_dest] = "no navmesh in this archive"' in SRC,
       "the travel prewarm is gated on --map (the portal convention) and on the ARM "
       "read off the argparse namespace, and records an unwarmed destination")
led.ok("TRANSFER_ARRIVALS[(world_id, player_id)] = (int(dest_map), time.time())" in SRC
       and "TRANSFER_ARRIVALS, (state[\"world_id\"], state[\"player_id\"])" in SRC,
       "send_transfer writes the one-shot arrival marker and the load's check reads it")

# handle_map_travel driven with a fake send and the real send_transfer
_saved = (authsrv.agents.WORLD, authsrv.TRANSFER_HOSTS, authsrv.TRANSFER_PORT,
          dict(authsrv.TRANSFERS_ISSUED), dict(authsrv.TRANSFER_ARRIVALS),
          dict(authsrv.TRAVEL_UNSERVABLE))
try:
    authsrv.agents.WORLD = WORLD
    authsrv.TRANSFER_HOSTS = ["127.0.0.1"]
    authsrv.TRANSFER_PORT = 6112
    authsrv.TRANSFER_ARRIVALS.clear()
    authsrv.TRAVEL_UNSERVABLE.clear()
    st = {"map_id": trav[0], "world_id": 1, "player_id": 1,
          "char_uuid": "aa" * 16}
    sent, send = fake_send_factory()
    took = authsrv.handle_map_travel([0x80B1, _dest, 0, 0, 0, 1], send, st, 1,
                                     "127.0.0.1")
    ops = [op for op, _v in sent]
    led.ok(took is True and maptravel.travel_batch_ok(ops),
           "handle_map_travel emits [0x01D9, 0x01A5, 0x0099] in that order and "
           "returns True (retail's batch, no 0x0028)", f"{[hex(o) for o in ops]}")
    led.ok(sent and sent[0][0] == MAP_TRAVEL_READY and sent[0][1] == [2, 1, ""],
           "0x01D9 is FIRST and its payload is [2, 1, ''] (retail's, 10 of 10)",
           f"{sent[0] if sent else sent}")
    led.ok(authsrv.TRANSFER_ARRIVALS.get((1, 1), (None,))[0] == _dest,
           f"the transfer recorded the one-shot arrival marker for map {_dest}",
           f"{authsrv.TRANSFER_ARRIVALS}")
    led.ok(maptravel.arrival_skips_unlock(authsrv.TRANSFER_ARRIVALS, (1, 1), _dest,
                                          authsrv.time.time()) is True
           and (1, 1) not in authsrv.TRANSFER_ARRIVALS,
           "the re-entry's check consumes the marker and says SKIP the 0x0094")
    # KNOWN-BAD: the REAL handler's output with 0x01D9 dropped by the send wrapper
    # fails the SAME predicate the positive check used.
    st["map_id"] = trav[0]
    sent_bad, send_bad = fake_send_factory(drop=(MAP_TRAVEL_READY,))
    authsrv.handle_map_travel([0x80B1, _dest, 0, 0, 0, 1], send_bad, st, 1, "127.0.0.1")
    ops_bad = [op for op, _v in sent_bad]
    led.ok(ops_bad == [TRANSFER, MAP_UPD] and not maptravel.travel_batch_ok(ops_bad),
           "KNOWN-BAD: the real handler's batch with 0x01D9 dropped by the send "
           "wrapper fails travel_batch_ok", f"{[hex(o) for o in ops_bad]}")
    # refusals send NOTHING
    authsrv.TRAVEL_UNSERVABLE.clear()
    for label, cur, dst, unwarmed in (("explorable", trav[0], _expl[0], None),
                                      ("no content row", trav[0], _absent, None),
                                      ("already here", _dest, _dest, None),
                                      ("placeholder spawn", trav[0], _placeholder[0], None),
                                      ("unwarmed destination", trav[0], _dest, _dest)):
        st["map_id"] = cur          # the gate reads the current map off state
        authsrv.TRAVEL_UNSERVABLE.clear()
        if unwarmed is not None:
            authsrv.TRAVEL_UNSERVABLE[unwarmed] = "no navmesh in this archive"
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
    authsrv.TRANSFER_ARRIVALS.clear()
    authsrv.TRANSFER_ARRIVALS.update(_saved[4])
    authsrv.TRAVEL_UNSERVABLE.clear()
    authsrv.TRAVEL_UNSERVABLE.update(_saved[5])

# ---- §3 the tape -----------------------------------------------------------
if livewire.live_captures():
    def bitset(ws):
        return {i * 32 + b for i, w in enumerate(ws) for b in range(32) if (int(w) >> b) & 1}

    n_b1 = d9_first = seq_ok = shape_ok = bad_transfer_first = 0
    unlock_seen = unlock_arr4 = unlock_w27 = unlock_pos_ok = 0
    unlock_on_arrival = unlock_on_first_loader = 0
    joined = at_load = 0
    n_99_flag1 = 0
    bycap = {}
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if merged:
            bycap.setdefault(os.path.basename(capdir), []).append((merged[0][0], conn, merged))
    for cap, rows_ in bycap.items():
        rows_.sort(key=lambda r: r[0])
        unlocks = []        # (t, arr4set)
        all99 = []          # (t, map, flag)
        for _t0, conn, merged in rows_:
            for (t, d, op, vals) in merged:
                if d == "s2c" and op == MAP_UPD:
                    all99.append((t, int(vals[1]), vals[2] if len(vals) > 2 else None))
                    if len(vals) > 2 and vals[2] == 1:
                        n_99_flag1 += 1
                if d == "s2c" and op == UNLOCK:
                    arrs = [v for v in vals[1:] if isinstance(v, list)]
                    unlocks.append((t, bitset(arrs[4]) if len(arrs) >= 5 else set()))
        for idx, (_t0, conn, merged) in enumerate(rows_):
            i199 = next((i for i, (_t, d, op, _v) in enumerate(merged) if d == "s2c" and op == 0x0199), None)
            i8b = next((i for i, (_t, d, op, _v) in enumerate(merged) if d == "s2c" and op == 0x008B), None)
            prev_transfer = idx > 0 and any(d == "s2c" and op == TRANSFER for (_t, d, op, _v) in rows_[idx - 1][2])
            first_loader = all(not any(d2 == "s2c" and op2 == 0x0199 for (_t2, d2, op2, _v2) in rows_[j][2])
                               for j in range(idx))
            for i, (t, d, op, vals) in enumerate(merged):
                if d == "s2c" and op == UNLOCK:
                    unlock_seen += 1
                    arrs = [v for v in vals[1:] if isinstance(v, list)]
                    if len(arrs) >= 5 and any(arrs[4]):
                        unlock_arr4 += 1
                    if len(arrs) >= 5 and len(arrs[4]) == 27:
                        unlock_w27 += 1
                    if i199 is not None and i199 < i and i8b is not None and i < i8b:
                        unlock_pos_ok += 1
                    if prev_transfer:
                        unlock_on_arrival += 1
                    if first_loader:
                        unlock_on_first_loader += 1
                if d == "c2s" and op == 0x00B1:
                    n_b1 += 1
                    dest = int(vals[1])
                    if len(vals) >= 6 and list(vals[2:]) == [0, 0, 0, 1]:
                        shape_ok += 1
                    prior = [(tt, s) for (tt, s) in unlocks if tt < t]
                    latest = max(prior, key=lambda r: r[0]) if prior else None
                    in94 = bool(latest and dest in latest[1])
                    in99 = any(tt < t and m == dest for (tt, m, _f) in all99)
                    at_load += in94
                    joined += (in94 or in99)
                    after = [(o, dd) for (_t2, dd, o, _v) in merged[i + 1:] if _t2 - t <= 1.5]
                    s2c_after = [o for o, dd in after if dd == "s2c"]
                    first_nt = next((o for o in s2c_after if o != 0x001E), None)
                    if first_nt == MAP_TRAVEL_READY:
                        d9_first += 1
                    if (MAP_TRAVEL_READY in s2c_after and TRANSFER in s2c_after
                            and MAP_UPD in s2c_after
                            and s2c_after.index(MAP_TRAVEL_READY)
                            < s2c_after.index(TRANSFER) < s2c_after.index(MAP_UPD)):
                        seq_ok += 1
                    if (TRANSFER in s2c_after and MAP_TRAVEL_READY in s2c_after
                            and s2c_after.index(TRANSFER) < s2c_after.index(MAP_TRAVEL_READY)):
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
    led.ok(unlock_on_arrival == 0 and unlock_on_first_loader >= unlock_seen - 1,
           "retail sends 0x0094 on a LOGIN's first map-loading connection and NEVER "
           "on a transfer arrival (the one non-first sighting is a second login)",
           f"first-loader {unlock_on_first_loader}, arrival {unlock_on_arrival}, of {unlock_seen}")
    led.ok(unlock_pos_ok == unlock_seen,
           "every retail 0x0094 sits after 0x0199 and before 0x008B (where ours now sits)",
           f"{unlock_pos_ok}/{unlock_seen}")
    led.ok(unlock_w27 == unlock_seen,
           f"retail's arr4 is 27 dwords on every sighting (ours is {N_WORDS}, labelled)",
           f"{unlock_w27}/{unlock_seen}")
    led.ok(joined == n_b1 and at_load < n_b1 and n_99_flag1 >= 1,
           "THE JOIN: every 0x00B1 destination's bit was set BEFORE the click -- by "
           "the login's 0x0094 or a prior 0x0099 -- and at least one by 0x0099 alone "
           "(the tape refutes 'every destination set at load'); a 0x0099 [map, 1] exists",
           f"set before click {joined}/{n_b1}; at load {at_load}/{n_b1}; "
           f"0x0099 [map, 1] rows {n_99_flag1}")
else:
    led.skip("§3 the tape", "no origin=LIVE captures under the vault")

sys.exit(led.verdict())
