r"""The respawn analyser, proved on fabricated streams and pinned on the corpus.

    python toolkit/authsrv/test_respawn.py

Section 1 fabricates message streams that commit each of the three traps
`studies/isle/PLAN.md` 3.4 names (agent-id recycling, visibility churn, the
corpse re-create) and demands the analyser refuse each one -- INCLUDING a check
that `naive_intervals` still falls for them, because a sabotage that stops
disagreeing has drifted from the defect it indicts (`npcdefs.Intervals.last`'s
pattern). Section 2 pins the analyser to per-connection numbers measured
2026-08-22 on sealed captures; per-connection rather than corpus totals so the
pins survive the corpus growing.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks       # noqa: E402
import respawn      # noqa: E402
import vaultpath    # noqa: E402

# Floor set from a real green run (46 checks, 2026-08-22).
LEDGER = checks.Ledger("respawn", floor=46)
check = checks.adopt(LEDGER)


# --------------------------------------------------------------------------
# Stream fabrication. Values carry THE OPCODE AT INDEX 0, matching what
# tape.decode_all returns (adrenjoin.py documents the two conventions).
def mk_create(t, agent, slot, kind=9, pos=(100.0, 200.0), tag=2, plane=0):
    ref = (tag << 28) | slot
    return (t, respawn.CREATE,
            [respawn.CREATE, agent, ref, 1, kind, pos, plane])


def mk_remove(t, agent):
    return (t, respawn.REMOVE, [respawn.REMOVE, agent])


def mk_flags(t, agent, val):
    return (t, respawn.FLAGS, [respawn.FLAGS, agent, val])


def mk_status(t, agent, val):
    return (t, respawn.STATUS, [respawn.STATUS, agent, val])


def mk_frac(t, agent, frac):
    import struct
    dw = struct.unpack("<I", struct.pack("<f", frac))[0]
    return (t, respawn.PROP_FLOAT_SELF,
            [respawn.PROP_FLOAT_SELF, respawn.PROP_HEALTH_FRACTION, agent, dw])


def deaths_of(res):
    return [d for key in res["keys"].values() for d in key["deaths"]]


# --------------------------------------------------------------------------
print("== 1. trap 1: a recycled agent id is not a respawn (agent 38's shape) ==")
msgs = [mk_create(0.6, 38, 1434, pos=(4605.0, 581.0)),
        mk_flags(19.9, 38, 8),
        mk_remove(47.5, 38),
        mk_create(74.8, 38, 1343, pos=(-8003.3, -3308.6))]
res = respawn.analyse(msgs)
ds = deaths_of(res)
check(len(ds) == 1 and ds[0]["resolution"] == "open",
      "keyed: the death stays OPEN, no respawn is claimed")
check(res["counters"]["id_recycled_over_open_death"] == 1,
      "the recycle is counted, not silently dropped")
naive = respawn.naive_intervals(msgs)
check(len(naive) == 1 and abs(naive[0]["interval"] - 54.9) < 0.1,
      "naive STILL manufactures the 54.9 s interval",
      f"naive={naive}")

print("== 2. trap 2: visibility churn claims nothing ==")
msgs = [mk_create(1.0, 50, 1421),
        mk_remove(20.0, 50),
        mk_create(52.0, 50, 1421),
        mk_remove(90.0, 50),
        mk_create(135.0, 50, 1421)]
res = respawn.analyse(msgs)
check(not deaths_of(res), "three creates, two removes, zero deaths claimed")
check(res["counters"]["churn_removes"] == 2, "the churn is counted as churn")
check(not respawn.naive_intervals(msgs),
      "naive agrees here -- churn without a death fools neither")

print("== 3. trap 3: a corpse re-create is a STILL-DEAD witness (agent 43) ==")
msgs = [mk_create(18.6, 43, 1434, pos=(5670.0, -4379.0)),
        mk_flags(36.3, 43, 8),
        mk_remove(52.4, 43),
        mk_create(79.2, 43, 1434, kind=8, pos=(5805.3, -3909.0)),
        mk_frac(79.2, 43, 0.0),
        mk_remove(81.3, 43)]
res = respawn.analyse(msgs)
ds = deaths_of(res)
check(len(ds) == 1 and ds[0]["resolution"] == "open",
      "keyed: still no respawn -- the creature came back DEAD")
check(abs(ds[0]["dead_at_least"] - 42.9) < 0.1,
      "the corpse extends the still-dead bound to 42.9 s",
      f"dead_at_least={ds[0]['dead_at_least']}")
check(res["counters"]["corpse_creates"] == 1
      and not res["counters"]["corpse_creates_health_nonzero"],
      "the corpse create carries health fraction 0.0")
naive = respawn.naive_intervals(msgs)
check(len(naive) == 1 and abs(naive[0]["interval"] - 42.9) < 0.1,
      "naive STILL reads the corpse as a 42.9 s respawn")

print("== 4. the real thing: revive in place, corpse witnessed between ==")
msgs = [mk_create(8.4, 69, 161, pos=(-10830.0, 1173.0)),
        mk_status(419.1, 69, 0x10),
        mk_flags(419.1, 69, 8),
        mk_remove(424.9, 69),
        mk_create(530.6, 69, 161, kind=8, pos=(-10830.0, 1173.0)),
        mk_frac(530.6, 69, 0.0),
        mk_status(539.6, 69, 0x0),
        mk_flags(539.6, 69, 9)]
res = respawn.analyse(msgs)
ds = deaths_of(res)
check(len(ds) == 1 and ds[0]["resolution"] == "revived",
      "death -> corpse-in-view -> FLAGS alive is ONE revived death")
check(abs(ds[0]["interval"] - 120.5) < 0.1,
      "the interval runs death -> revive, THROUGH the corpse create",
      f"interval={ds[0]['interval']}")
check(ds[0]["corroborated"] is True and ds[0]["revive_corroborated"] is True,
      "0x00F1's dead bit corroborates both ends")
naive = respawn.naive_intervals(msgs)
check(abs(naive[0]["interval"] - 111.5) < 0.1,
      "naive is wrong EVEN WHEN THE RESPAWN IS REAL -- it joins the corpse",
      f"naive={naive[0]['interval']}")

print("== 5. a corpse-first chain revives with an UNKNOWN interval ==")
msgs = [mk_create(10.0, 7, 156, kind=8, pos=(-10879.0, 2945.0)),
        mk_frac(10.0, 7, 0.0),
        mk_flags(264.9, 7, 9)]
res = respawn.analyse(msgs)
ds = deaths_of(res)
check(len(ds) == 1 and ds[0]["resolution"] == "revived"
      and ds[0]["interval"] is None,
      "the revive is recorded, the interval refuses to exist")
check(res["counters"]["revives_of_unwitnessed_death"] == 1,
      "and it is counted as a revive of an unwitnessed death")

print("== 6. a living re-create after the corpse left view: an UPPER BOUND ==")
msgs = [mk_create(1.0, 9, 152, pos=(-5915.0, 2079.0)),
        mk_flags(40.0, 9, 8),
        mk_remove(45.0, 9),
        mk_create(100.0, 9, 152, pos=(-5915.0, 2079.0))]
res = respawn.analyse(msgs)
ds = deaths_of(res)
check(len(ds) == 1 and ds[0]["resolution"] == "recreated",
      "same slot, same position, previously dead: recreated")
check(abs(ds[0]["interval_upper"] - 60.0) < 1e-9
      and "interval" not in ds[0],
      "it carries interval_upper and NO exact interval -- never pooled")

print("== 7. the player track: 4/5, kept out of the NPC census ==")
msgs = [mk_create(0.9, 27, 1, kind=5, tag=3, pos=(20323.0, -8150.0)),
        mk_status(78.8, 27, 0x10),
        mk_flags(78.8, 27, 4),
        mk_status(88.9, 27, 0x0),
        mk_flags(88.9, 27, 5)]
res = respawn.analyse(msgs)
check(not res["keys"], "a player creates NO spawn key")
pd = res["player_deaths"]
check(len(pd) == 1 and abs(pd[0]["interval"] - 10.1) < 0.1,
      "the player death revives at its own interval",
      f"player_deaths={pd}")
check(res["counters"]["non_npc_creates"] == 1, "the create counted as non-NPC")

print("== 8. FLAGS alive with no open death claims nothing (burrow tails) ==")
msgs = [mk_create(1.0, 30, 1500),
        mk_flags(1.0, 30, 9)]
res = respawn.analyse(msgs)
check(res["counters"]["alive_flag_no_open_death"] == 1
      and not deaths_of(res),
      "a create-tail FLAGS 9 is counted and claims no revive")

print("== 9. a death with no create refuses to be keyed ==")
msgs = [mk_flags(5.0, 99, 8)]
res = respawn.analyse(msgs)
check(res["counters"]["deaths_unattributed"] == 1
      and len(res["unattributed"]) == 1 and not res["keys"],
      "unattributed death: reported, never keyed")

print("== 10. two same-slot creatures at different positions stay separate ==")
msgs = [mk_create(1.0, 60, 115, pos=(1815.98, -3100.91)),
        mk_create(1.5, 61, 115, pos=(2065.69, -2673.13)),
        mk_flags(47.8, 61, 8),
        mk_flags(51.3, 61, 9)]
res = respawn.analyse(msgs)
check(len(res["keys"]) == 2,
      "same definition slot, two positions: two keys")
k1 = res["keys"][(115, (1815.98, -3100.91))]
k2 = res["keys"][(115, (2065.69, -2673.13))]
check(not k1["deaths"] and len(k2["deaths"]) == 1
      and k2["deaths"][0]["resolution"] == "revived",
      "the death and revive land on the dying creature's key only")

print("== 11. --radius merges keys and SAYS SO; the default never does ==")
msgs = [mk_create(1.0, 60, 115, pos=(1000.0, 1000.0)),
        mk_remove(10.0, 60),
        mk_create(20.0, 60, 115, pos=(1080.0, 1000.0))]
res = respawn.analyse(msgs)
check(len(res["keys"]) == 2 and not res["merges"],
      "default exact join: the wanderer fragments, nothing merges")
res = respawn.analyse(msgs, radius=100.0)
check(len(res["keys"]) == 1 and len(res["merges"]) == 1
      and abs(res["merges"][0]["distance"] - 80.0) < 1e-9,
      "radius 100: one key, and the merge is on the record with its distance")

print("== 12. a value/tag disagreement is counted, not resolved ==")
msgs = [mk_create(1.0, 40, 1346),
        mk_flags(23.5, 40, 4)]        # player-track value on an NPC chain
res = respawn.analyse(msgs)
check(res["counters"]["flags_value_tag_mismatch"] == 1
      and res["counters"]["npc_deaths"] == 1,
      "NPC chain + player death value: counted as mismatch, tag wins")

print("== 13. a STATUS that disagrees with the death is flagged ==")
msgs = [mk_create(1.0, 40, 1346),
        mk_status(23.5, 40, 0x0),     # dead bit CLEAR on the death tick
        mk_flags(23.5, 40, 8)]
res = respawn.analyse(msgs)
check(deaths_of(res)[0]["corroborated"] is False,
      "corroborated=False when 0x00F1 contradicts the FLAGS value")

print("== 14. mixed-origin pooling refuses ==")
try:
    respawn.refuse_mixed([{"origin": "live"}, {"origin": "ours"}])
    check(False, "mixed origins must raise")
except SystemExit:
    check(True, "live + ours in one pool raises")
check(respawn.refuse_mixed([{"origin": "live"}, {"origin": "live"},
                            {"origin": "ours", "skipped": "undecodable"}])
      == {"live"},
      "a SKIPPED connection's origin does not poison the pool")

# --------------------------------------------------------------------------
print("== 15. the corpus pins -- per connection, so they survive growth ==")
try:
    live = vaultpath.require_dir("captures", "live", why="respawn corpus pins")
except (Exception, SystemExit) as exc:                                    # noqa: BLE001
    live = None
    LEDGER.skip("corpus pins", f"vault unavailable: {exc}")

if live is not None:
    def conn_result(stamp, port):
        cap = os.path.join(live, stamp)
        results, _origins = respawn.scan(captures=[cap])
        for r in results:
            if not r.get("skipped") and f":{port}->" in r["connection"]:
                return r
        raise AssertionError(f"{stamp} port {port} not found")

    # Trap 1 on the real bytes: agent 38's 54.9 s never happened.
    r = conn_result("20260807T143055", 62994)
    ds = deaths_of(r)
    check(len(ds) == 1 and ds[0]["resolution"] == "open",
          "20260807 conn 62994: one death, open, ZERO respawns")
    n38 = [n for n in r["naive"] if n["agent"] == 38]
    check(len(n38) == 1 and abs(n38[0]["interval"] - 54.867) < 0.01,
          "and naive still claims 54.867 s on the same bytes",
          f"naive={n38}")

    # Trap 3 on the real bytes: agent 43's corpse.
    r = conn_result("20260810T235916", 61624)
    ds = deaths_of(r)
    check(len(ds) == 1 and ds[0]["resolution"] == "open"
          and abs(ds[0]["dead_at_least"] - 42.857) < 0.01,
          "20260810 conn 61624: still dead 42.857 s after death, no claim")

    # The 120.5 s Zaishen revive, through a corpse create.
    r = conn_result("20260817T231139", 63805)
    revived = [d for d in deaths_of(r) if d["resolution"] == "revived"
               and d.get("interval") is not None]
    check(len(revived) == 1 and abs(revived[0]["interval"] - 120.499) < 0.01,
          "20260817 conn 63805: slot 161 revives at 120.499 s",
          f"revived={[d.get('interval') for d in revived]}")
    n69 = [n for n in r["naive"] if n["agent"] == 69]
    check(len(n69) == 1 and abs(n69[0]["interval"] - 111.491) < 0.01,
          "naive joins the corpse instead and is 9 s wrong",
          f"naive={n69}")
    unknown = [d for d in deaths_of(r)
               if d["resolution"] == "revived" and d.get("interval") is None]
    check(len(unknown) == 3,
          "three corpse-first chains revive with UNKNOWN intervals, not guesses")

    # The Isle sparring squad: every death in view, wave revives.
    r = conn_result("20260817T231139", 54071)
    ds = deaths_of(r)
    revived = [d for d in ds if d["resolution"] == "revived"]
    check(len(ds) == 19 and len(revived) == 15,
          "Isle conn 54071: 19 deaths, 15 revived in place, 4 open at cut",
          f"deaths={len(ds)} revived={len(revived)}")
    check(all(d.get("corroborated") for d in ds),
          "all 19 deaths corroborated by 0x00F1's dead bit")

    # THE HEADLINE: practice-target respawn is 30 s, measured eleven times
    # over in one connection at under +/-15 ms of jitter.
    r = conn_result("20260818T132739", 53202)
    ivs = [d["interval"] for d in deaths_of(r)
           if d["resolution"] == "revived" and d.get("interval") is not None]
    check(len(ivs) == 9 and all(abs(iv - 30.0) < 0.05 for iv in ivs),
          "20260818 conn 53202: NINE revives, every one 30.0 +/- 0.05 s",
          f"intervals={[round(i, 3) for i in ivs]}")

    # The player track on the real bytes.
    r = conn_result("20260817T183756", 52294)
    pd = r["player_deaths"]
    check(len(pd) == 1 and abs(pd[0]["interval"] - 10.044) < 0.01,
          "20260817T183756: the player death revives at 10.044 s")

    # The two-track FLAGS reading holds corpus-wide: pool everything and
    # demand no mismatch and no fifth value anywhere.
    results, origins = respawn.scan()
    check(all(o == "live" for o in origins.values()),
          "every pooled connection is origin live",
          f"origins={sorted(set(origins.values()))}")
    import collections
    total = collections.Counter()
    for r in results:
        if not r.get("skipped"):
            total.update(r["counters"])
    check(total["flags_value_tag_mismatch"] == 0,
          "zero value/tag mismatches over the whole corpus")
    check(not any(k.startswith("flags_value_") for k in total),
          "no fifth FLAGS value exists anywhere in the corpus")
    check(total["corpse_creates_health_nonzero"] == 0,
          "every corpse create in the corpus carries health fraction 0.0")
    check(total["npc_deaths"] >= 64 and total["npc_revives"] >= 38,
          "the corpus holds at least the 64 deaths / 38 revives measured "
          "2026-08-22 (floor, not equality -- the corpus grows)",
          f"deaths={total['npc_deaths']} revives={total['npc_revives']}")

sys.exit(LEDGER.verdict())
