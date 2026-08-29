"""The plane-lock repair and the plane-echo tripwire (MOVECODE sec.1z-d).

WHY THIS FILE EXISTS. On 2026-08-29 the operator's client froze in open
ground (r5stuck): it had crossed a plane boundary carrying its old plane
word, its own path queries then started from a plane that does not contain
its position, no path was ever solved, and it could not walk to ground that
would re-plane it. The server watched 82 accepted, byte-identical 0x003D
reports claiming the impossible plane over 40.4 s and did nothing -- there
was no code that could act, and none that even named the anomaly while it
happened (43 of 58 zero-lead grants echoed the impossible plane silently).

The design here is the PRE-COMMIT REVIEW'S, not the first draft's: the draft
disarmed the streak on every 0x0047 stop-report, and replaying the source
capture through it refuted its own registered prediction (the measured lock
INTERLEAVES stops -- a victim mashes keys -- so the reset pushed the first
fire from 5.1 s to 9.3 s). Stops are now ignored and evidence freshness is
the PLANE_REPAIR_GAP stream-continuity bound instead, derived from the
capture's own gap structure (intra-episode 2.47 s must survive, the 10.3 s
inter-episode gap must not).

Two additions, tested here:

  * `plane_repair_track`/`_maybe_plane_repair` -- ONE labelled 0x002C at the
    client's own accepted frozen position with the mesh's plane, fired only
    on the measured lock signature. The tests hold it to the signature and
    to every clause that must DISARM it, because the failure mode of a
    repair is firing on a client that is fine: the DECODED deck-stroller
    and the bridge no-clipper below must never fire it. (The 9/198 class --
    the client's plane is right, our decode's COVERAGE is missing -- is the
    one case the trigger cannot see through: a client frozen there 5 s IS
    restamped. That residual is priced in the constants block, not
    prevented, and it is why the blanket "never emit an impossible plane"
    rewrite was refused outright while this narrow repair was not.)
  * the plane-echo tripwire in `_note_wire_move` -- observation, NEVER a
    rewrite. The test that the emitted values are unchanged is the load-
    bearing one: the rewrite is the documented, twice-refused design.

Fixtures follow test_cancelwalk's _FakePM discipline (drive the logic with a
controllable mesh), plus one section against the REAL map-280 mesh that
proves the r5stuck coordinate's premise -- skipped with a ledger row, never
silently, when the archive is not readable.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
for _p in (TOOLKIT, HERE, os.path.join(TOOLKIT, "mapdata")):
    sys.path.insert(0, _p)

import checks                                                  # noqa: E402
import authsrv                                                 # noqa: E402

LEDGER = checks.Ledger("planerepair", floor=36)
check = checks.adopt(LEDGER)

# The r5stuck measurement this whole feature encodes
# (vault/captures/gamesrv/authsrv-20260829T091543-c1.jsonl; FINDINGS 1z-d).
FROZEN = (-2803.415283203125, 509.3924560546875)
STUCK_PLANE = 41
MAP_FID = 0x287B3


class _FakePM:
    """containing()/plane_at() with scripted offers, test_cancelwalk-style."""

    def __init__(self, offered):
        self._offered = list(offered)

    def containing(self, x, y):
        out = []
        for p in self._offered:
            t = type("T", (), {})()
            t.plane = p
            out.append(t)
        return out

    def plane_at(self, x, y, prefer=None):
        if prefer in self._offered:
            return prefer
        if len(self._offered) == 1:
            return self._offered[0]
        return None


class _Rec:
    def __init__(self):
        self.rows = []

    def event(self, kind, **kw):
        self.rows.append(dict(kw, kind=kind))


def _sends():
    sent = []

    def send(opcode, values, label, quiet=False):
        sent.append((opcode, values, label))
    return sent, send


def track(state, pt, plane, accepted, pm, now, moving=1):
    return authsrv.plane_repair_track(state, pt, plane, accepted, moving,
                                      pm, now)


def main():
    # ---- 1. the measured lock, replayed against a scripted mesh ----------
    pm = _FakePM([0])                       # mesh offers only 0; client says 41
    st = {}
    f, why, fix = track(st, FROZEN, STUCK_PLANE, True, pm, 100.0)
    check((f, why) == (False, "arming"),
          "first impossible frozen report ARMS, it does not fire",
          f"got {(f, why)}")
    f, why, fix = track(st, FROZEN, STUCK_PLANE, True, pm, 104.9)
    check((f, why) == (False, "holding"),
          "under PLANE_REPAIR_HOLD the streak holds without firing",
          f"got {(f, why)}")
    f, why, fix = track(st, FROZEN, STUCK_PLANE, True, pm, 105.1)
    check((f, why, fix) == (True, "plane-lock", 0),
          "past HOLD the verdict fires with the mesh's plane",
          f"got {(f, why, fix)}")

    # ---- 2. the rate limit, and the refire ------------------------------
    st["pr_fired_at"] = 105.1
    f, why, _ = track(st, FROZEN, STUCK_PLANE, True, pm, 110.0)
    check((f, why) == (False, "rate-limited"),
          "a second fire inside PLANE_REPAIR_MIN_INTERVAL is refused",
          f"got {(f, why)}")
    # The stream must stay LIVE between fires -- a silent 10.5 s would be a
    # legitimate stale-stream re-arm, which is its own check below.
    for dt in (2.0, 4.0, 6.0, 8.0, 10.0):
        f, why, fix = track(st, FROZEN, STUCK_PLANE, True, pm, 105.1 + dt)
    check((f, why, fix) == (True, "plane-lock", 0),
          "an un-healed lock with a LIVE report stream refires after the "
          "interval",
          f"got {(f, why, fix)}")

    # ---- 3. every disarm clause, each against the SAME lock-shaped run ---
    # A moving client re-arms every report and can never accumulate HOLD --
    # this is the r5bridge no-clip shape (impossible plane, changing point),
    # and it must never fire however long it persists.
    st = {}
    t = 200.0
    seen = set()
    for i in range(40):                     # 40 reports over 20 s, all moving
        f, why, _ = track(st, (FROZEN[0] + i, FROZEN[1]), STUCK_PLANE,
                          True, pm, t + i * 0.5)
        seen.add((f, why))
    check(seen == {(False, "arming")},
          "a MOVING client with an impossible plane never fires (r5bridge "
          "no-clip shape) -- ALL 40 verdicts are re-arms, not just the last",
          f"verdicts seen: {seen}")

    # The 9/198 protection: the client's plane IS offered (deck over ground)
    # -- frozen or not, 'plane-legal' and the streak is cleared.
    pm_deck = _FakePM([0, 37])
    st = {}
    track(st, FROZEN, STUCK_PLANE, True, pm, 300.0)      # arm a real streak
    f, why, _ = track(st, FROZEN, 37, True, pm_deck, 300.5)
    check((f, why) == (False, "plane-legal") and st.get("pr_point") is None,
          "a plane the mesh OFFERS disarms -- every DECODED deck is safe. "
          "(The 9/198 hole -- deck coverage our decode LACKS -- is the "
          "opposite case: single wrong candidate, and a client frozen there "
          "5 s IS restamped. That false fire is priced out loud in the "
          "constants block, not prevented; do not read this check as "
          "preventing it.)",
          f"got {(f, why)}, pr_point={st.get('pr_point')}")

    # Ambiguous stack: reported plane matches neither of two candidates --
    # plane_at returns None and the repair refuses to guess.
    f, why, _ = track({}, FROZEN, 5, True, pm_deck, 310.0)
    check((f, why) == (False, "ambiguous"),
          "two candidates and a match with neither REFUSES (plane_at's None "
          "is 'say nothing', never a guess)",
          f"got {(f, why)}")

    # Off-mesh: no authority.
    f, why, _ = track({}, FROZEN, STUCK_PLANE, True, _FakePM([]), 320.0)
    check((f, why) == (False, "off-mesh"),
          "an off-mesh point disarms -- the mesh has no authority there",
          f"got {(f, why)}")

    # A refused report disarms MID-HOLD: the trust radius is the
    # anti-teleport guard and the repair inherits it by counting accepts.
    st = {}
    track(st, FROZEN, STUCK_PLANE, True, pm, 400.0)
    f, why, _ = track(st, FROZEN, STUCK_PLANE, False, pm, 402.0)
    check((f, why) == (False, "report-refused")
          and st.get("pr_point") is None,
          "a trust-refused report DISARMS the streak, not just skips it",
          f"got {(f, why)}, pr_point={st.get('pr_point')}")
    f, why, _ = track(st, FROZEN, STUCK_PLANE, True, pm, 406.0)
    check((f, why) == (False, "arming"),
          "after a refusal the clock starts over -- 6 s of wall time did "
          "not accumulate across the disarm",
          f"got {(f, why)}")

    # No mesh loaded: no-op, matching _router_plane's pm-is-None door.
    f, why, _ = track({}, FROZEN, STUCK_PLANE, True, None, 500.0)
    check((f, why) == (False, "no-mesh"),
          "pm None is a no-op, never a refusal-to-serve",
          f"got {(f, why)}")

    # STOPS ARE IGNORED, and the capture's own gap structure is the spec:
    # the measured lock's episode-1 stream has a 2.47 s gap and one
    # interleaved stop-report, and still fired at 5.11 s in the replay --
    # so a sub-GAP gap must accumulate...
    st = {}
    track(st, FROZEN, STUCK_PLANE, True, pm, 600.0)
    track(st, FROZEN, STUCK_PLANE, True, pm, 602.47)    # the measured gap
    f, why, fix = track(st, FROZEN, STUCK_PLANE, True, pm, 605.2)
    check((f, why, fix) == (True, "plane-lock", 0),
          "a 2.47 s intra-stream gap (the capture's own largest surviving "
          "gap) accumulates across it -- the lock still fires at ~5 s",
          f"got {(f, why, fix)}")
    # ...and a stream gap over PLANE_REPAIR_GAP must RE-ARM, not fire: one
    # keypress cannot inherit a minutes-old streak.
    st = {}
    track(st, FROZEN, STUCK_PLANE, True, pm, 700.0)
    f, why, _ = track(st, FROZEN, STUCK_PLANE, True, pm, 760.0)
    check((f, why) == (False, "stale-stream"),
          "a report gap over GAP re-arms -- evidence must be a LIVE stream",
          f"got {(f, why)}")
    f, why, _ = track(st, FROZEN, STUCK_PLANE, True, pm, 762.0)
    check((f, why) == (False, "holding"),
          "and the re-armed clock counts from the gap's end, not the "
          "original arming 62 s ago",
          f"got {(f, why)}")
    # There is deliberately NO reset call anywhere: plane_repair_reset was
    # the first draft, refuted by replaying the source capture (see the
    # module docstring); section 7 below pins its absence from the 0x0047
    # arm.

    # A non-finite coordinate disarms BEFORE the mesh sees it -- containing()
    # does int(y // BAND) and int(nan) raises out of the recv loop.
    f, why, _ = track({}, (float("nan"), 509.39), STUCK_PLANE, True, pm,
                      800.0)
    check((f, why) == (False, "bad-point"),
          "a NaN coordinate is refused before the mesh read, not crashed on",
          f"got {(f, why)}")

    # A pure-turn 0x003D (movementType 0 -- never seen in 7,988 corpus
    # records, guarded anyway per the cancel arm's own precedent) disarms:
    # a client standing still turning is not claiming to move.
    st = {}
    track(st, FROZEN, STUCK_PLANE, True, pm, 650.0)
    f, why, _ = track(st, FROZEN, STUCK_PLANE, True, pm, 650.5, moving=0)
    check((f, why) == (False, "not-moving") and st.get("pr_point") is None,
          "a pure-turn report DISARMS -- no movement claim, no lock evidence",
          f"got {(f, why)}, pr_point={st.get('pr_point')}")

    # The flag.
    old = authsrv.PLANE_REPAIR
    try:
        authsrv.PLANE_REPAIR = False
        f, why, _ = track({}, FROZEN, STUCK_PLANE, True, pm, 700.0)
        check((f, why) == (False, "off"),
              "--no-plane-repair short-circuits before any mesh read",
              f"got {(f, why)}")
    finally:
        authsrv.PLANE_REPAIR = old

    # ---- 4. the impure half: what actually goes on the wire --------------
    st = {"pathmap": pm}
    rec = _Rec()
    sent, send = _sends()
    for i, now in enumerate((800.0, 802.0, 806.0)):
        fired = authsrv._maybe_plane_repair(
            send, st, rec, FROZEN, STUCK_PLANE, True, 1, now=now)
    check(fired and len(sent) == 1,
          "three lock-shaped reports over 6 s produce exactly ONE send",
          f"fired={fired}, sent={len(sent)}")
    check(st.get("zl_last_grant_plane") == 0,
          "the fire HEALS the plane carry -- the same packet's zero-lead "
          "grant reads zl_last_grant_plane for field 4, and left stale it "
          "would restamp the sync copy with the plane the 0x002C just "
          "corrected (review skeptic finding 1)",
          f"zl_last_grant_plane={st.get('zl_last_grant_plane')}")
    op, values, label = sent[0]
    check(op == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
          and values == [authsrv.PLAYER_AGENT_ID,
                         [FROZEN[0], FROZEN[1]], 0],
          "the send is 0x002C at the client's OWN frozen point with the "
          "mesh's plane -- no positional yank, plane restamped",
          f"got opcode 0x{op:04X} values {values}")
    check("PLANE-REPAIR" in label,
          "the send is labelled PLANE-REPAIR -- attribution by label is the "
          "licence for a third 0x002C sender existing at all",
          f"label: {label}")
    dues = [r for r in rec.rows if r["kind"] == "plane_repair_due"]
    check([r["why"] for r in dues] == ["arming", "holding", "plane-lock"],
          "plane_repair_due rows log on REASON TRANSITION only",
          f"got {[r['why'] for r in dues]}")
    fires = [r for r in rec.rows if r["kind"] == "plane_repair"]
    check(len(fires) == 1 and fires[0]["plane_from"] == STUCK_PLANE
          and fires[0]["plane_to"] == 0 and fires[0]["held_s"] >= 5.0
          and fires[0]["n"] == 1,
          "the fire row names from-plane, to-plane, held duration and the "
          "fire NUMBER (a repeat fire means NOT HEALING, and the operator "
          "must be able to count them)",
          f"got {fires}")

    # ---- 5. the plane-echo tripwire: observes, NEVER rewrites ------------
    st = {"pathmap": pm}
    rec = _Rec()
    vals = [authsrv.PLAYER_AGENT_ID, [FROZEN[0], FROZEN[1]],
            STUCK_PLANE, STUCK_PLANE]
    before = [vals[0], list(vals[1]), vals[2], vals[3]]
    authsrv._note_wire_move(st, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            vals, 900.0, rec=rec)
    echoes = [r for r in rec.rows if r["kind"] == "plane_echo"]
    check(len(echoes) == 1 and echoes[0]["plane"] == STUCK_PLANE
          and echoes[0]["offered"] == [0],
          "emitting an impossible slot-2 plane logs a plane_echo row "
          "(43 of these went unnamed in the r5stuck session)",
          f"got {echoes}")
    check(vals[0] == before[0] and list(vals[1]) == before[1]
          and vals[2] == before[2] and vals[3] == before[3],
          "and the values are UNCHANGED -- the rewrite is the twice-refused "
          "design (plane_at's 9/198 class; test_position_trust's verbatim "
          "echo pin), so a mutation here is the exact regression",
          f"values now {vals}")
    check(st.get("plane_echo_bad") is True,
          "the transition flag arms so the console prints once, not per row",
          f"plane_echo_bad={st.get('plane_echo_bad')}")

    # CONTROL: a legitimate deck plane on stacked geometry does not log.
    st2 = {"pathmap": _FakePM([0, 37])}
    rec2 = _Rec()
    authsrv._note_wire_move(st2, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            [authsrv.PLAYER_AGENT_ID, [1.0, 2.0], 37, 37],
                            901.0, rec=rec2)
    check(not [r for r in rec2.rows if r["kind"] == "plane_echo"]
          and st2.get("plane_echo_bad") is False,
          "CONTROL: a plane the mesh OFFERS logs nothing -- the tripwire "
          "must pass r5bridge's 9 legitimate deck grants",
          f"rows={rec2.rows}")

    # And the 0x002C shape (3 fields) is covered by the same wire.
    rec3 = _Rec()
    authsrv._note_wire_move(st, authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
                            [authsrv.PLAYER_AGENT_ID,
                             [FROZEN[0], FROZEN[1]], STUCK_PLANE],
                            902.0, rec=rec3)
    check(len([r for r in rec3.rows if r["kind"] == "plane_echo"]) == 1,
          "the tripwire also reads 0x002C's slot-2 plane -- it would catch "
          "a wrong plane in the repair's OWN send",
          f"rows={rec3.rows}")

    # The sync model is untouched by the tripwire: same inputs, same
    # sync_to as an un-tripwired call on a state with no pathmap.
    st_pm, st_no = {"pathmap": pm}, {}
    vals_b = [vals[0], list(vals[1]), vals[2], vals[3]]   # independent copy,
    # or a tripwire that mutated values would leave both models identically
    # wrong and this A/B would stay green (review NIT 11)
    authsrv._note_wire_move(st_pm, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            vals, 903.0)
    authsrv._note_wire_move(st_no, authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT,
                            vals_b, 903.0)
    check(st_pm.get("sync_to") == st_no.get("sync_to")
          and st_pm.get("grant_at") == st_no.get("grant_at"),
          "the tripwire leaves _note_wire_move's real job (the sync model) "
          "byte-identical with and without a mesh",
          f"{st_pm.get('sync_to')} vs {st_no.get('sync_to')}")

    # ---- 6. composition -------------------------------------------------
    check(authsrv.zero_lead_composition() == (None, []),
          "the bare composition call is unchanged (pinned by "
          "test_position_trust too; this is the note's default-off proof)",
          f"got {authsrv.zero_lead_composition()}")
    r, n = authsrv.zero_lead_composition(zero_lead=True, plane_carry=True,
                                         resync=True, plane_repair=True)
    check(r is None and any("PLANE-REPAIR" in x for x in n),
          "repair beside --resync is ALLOWED WITH A NOTE naming the third "
          "0x002C sender",
          f"refusal={r}, notes={n}")
    r, n = authsrv.zero_lead_composition(zero_lead=True, plane_carry=True,
                                         d1_lead=True, cast_stop="pin",
                                         plane_repair=True)
    check(r is None and any("PLANE-REPAIR" in x for x in n),
          "repair beside --cast-stop=pin gets the same note",
          f"refusal={r}, notes={n}")
    r, n = authsrv.zero_lead_composition(zero_lead=True, plane_carry=True,
                                         plane_repair=True)
    check(r is None and not any("PLANE-REPAIR" in x for x in n),
          "with NO second 0x002C policy the note is absent -- note that the "
          "SHIPPED default resolves cast_stop to 'pin', so a real default "
          "run DOES print the note (previous wording claimed the opposite; "
          "review finding 3)",
          f"refusal={r}, notes={n}")

    # ---- 7. the wiring is real: source checks on the two arms ------------
    import inspect
    src = inspect.getsource(authsrv)
    i_resync = src.find("_maybe_resync(send, state, rec)")
    # Search FORWARD from the resync call, or this finds the def instead of
    # the call -- the verify-the-operand trap, hit while writing this check.
    i_repair = src.find("_maybe_plane_repair(send, state, rec, reported, "
                        "plane,", i_resync)
    check(0 < i_resync < i_repair < i_resync + 1200,
          "the 0x003D arm calls the repair right AFTER _maybe_resync "
          "(ordering: the client applies them in packet order)",
          f"resync at {i_resync}, repair at {i_repair}")
    i_stop_take = src.find('"0x0047", stop=True')
    stop_window = src[i_stop_take:i_stop_take + 2000]
    check(i_stop_take > 0 and "plane_repair" not in stop_window,
          "the 0x0047 arm does NOT touch the repair -- the first draft's "
          "stop-reset was refuted by replaying the source capture (the "
          "measured lock interleaves stops), so its reappearance here is "
          "the refuted design coming back",
          f"take at {i_stop_take}; window contains plane_repair: "
          f"{'plane_repair' in stop_window}")

    # ---- 8. the real map-280 mesh: the r5stuck premise -------------------
    # The scripted-mesh sections above prove the LOGIC; this proves the
    # PREMISE -- that at the real frozen coordinate the real mesh offers
    # exactly plane 0 and resolves 41 -> 0, i.e. the repair the lock would
    # actually have received. Needs the archive; a ledger skip when absent.
    try:
        import pathmap
        real = pathmap.PathingMap.load(MAP_FID)
    except Exception as ex:                                     # noqa: BLE001
        LEDGER.skip("real-mesh premise",
                    f"map 0x{MAP_FID:X} not loadable here: {ex}")
        real = None
    if real is not None:
        offered = sorted({t.plane for t in real.containing(*FROZEN)})
        check(offered == [0],
              "the real mesh offers exactly [0] at the r5stuck coordinate",
              f"offers {offered} -- if this moved, re-derive 1z-d before "
              f"trusting the repair's constants")
        check(real.plane_at(FROZEN[0], FROZEN[1], prefer=STUCK_PLANE) == 0,
              "and plane_at(prefer=41) resolves to 0 -- the exact restamp "
              "the locked client needed",
              "resolution changed")
        f, why, fix = track({}, FROZEN, STUCK_PLANE, True, real, 1000.0)
        check((f, why) == (False, "arming"),
              "the verdict runs against the REAL PathingMap object "
              "unmodified -- the fake and the real share an interface",
              f"got {(f, why)}")
        # The ambiguous door against REAL stacked geometry (review NIT 12:
        # the door that distinguishes this from the REJECTED
        # plane_at(copy_estimate) variant was proved only on the fake).
        STACKED = (-1643.0, 6448.0)          # r5bridge, deck over ground
        got = sorted({tr.plane for tr in real.containing(*STACKED)})
        check(len(got) > 1,
              f"premise: {STACKED} really is stacked on the real mesh",
              f"offers {got} -- find another stacked point before trusting "
              f"the next check")
        f, why, _ = track({}, STACKED, 5, True, real, 1001.0)
        check((f, why) == (False, "ambiguous"),
              "on REAL stacked geometry with a plane matching neither "
              "candidate, the door REFUSES -- plane_at's None against the "
              "real trapezoids, not a scripted fake",
              f"got {(f, why)} against offers {got}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
