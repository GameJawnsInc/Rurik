r"""The tick clock vs the wire clock, over the WHOLE live corpus.

    python toolkit/authsrv/test_tickclock.py

`test_smsgnames.py` 1 proved `0x001E`'s payload IS elapsed milliseconds -- on
the TWO 2026-08-07/10 captures its corpus deliberately pins. Every timed claim
since then (the respawn pins, the burrow windows, the adrenaline orderings)
rides captures that check never covered. This file runs the same integral over
every wire-bearing live connection through `behaviourrun.corpus_tick_sweep()`
and pins what the 2026-08-23 sweep found:

  * the residual is a bounded transport-jitter WALK, not a clock skew -- it
    returns to <= 20 ms on 52 of 54 connections, and the longest connection
    (1,076 s) closes at -4.6 ms, a ~4 ppm rate agreement;
  * exactly TWO connections carry non-cancelling steps, both in
    `20260817T183756` (the Shing Jea armour capture): +219 ms and -110 ms,
    acquired in their map-load phase and flat after. They are pinned by
    IDENTITY so a third joining them goes red;
  * the per-connection ENVELOPE (max |residual|) is the wire-timestamp error
    bar a timed claim from that connection inherits. The claim-bearing
    connections are pinned: the 120.499 s revive and the 30 s respawn ride
    <= 100 ms envelopes (their claims stand), while the 10.044 s player
    revive rides the +219 ms step -- that figure's honest bar is +/- 0.22 s,
    recorded in studies/isle/FINDINGS.md 10.

Floors are from the green run they were measured on, never guessed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks           # noqa: E402
import behaviourrun     # noqa: E402

# Floor set from a real green run (14 checks, 2026-08-23).
LEDGER = checks.Ledger("tick clock vs wire clock", floor=14)
check = checks.adopt(LEDGER)

# The two known step connections, by identity (stamp, client port).
STEP_UP = ("20260817T183756", ":52294->")     # +219 ms, 2 Hz town ticks
STEP_DOWN = ("20260817T183756", ":58389->")   # -110 ms

try:
    rows = list(behaviourrun.corpus_tick_sweep())
except Exception as exc:                                    # noqa: BLE001
    LEDGER.skip("everything", f"vault unavailable: {exc}")
    sys.exit(LEDGER.verdict())

live = [(s, c, r) for s, c, k, r in rows if k == "live"]
check(len(live) == len(rows),
      "every file under vault/captures/live classifies LIVE -- no pooling "
      "question arises", f"{len(rows) - len(live)} non-live row(s)")
meas = [(s, c, r) for s, c, r in live if r is not None]
short = len(live) - len(meas)

print("== 1. coverage ==")
check(len(meas) >= 54,
      "the sweep measured the whole live corpus (>= 54 connections)",
      f"{len(meas)} measurable, {short} with too few ticks")
# A SHARE, NOT A COUNT. This was `short <= 6` against 5 in the corpus, and it
# caps an ABSOLUTE number over a corpus that grows: every live session brings its
# own short town hops, so the sixth one reddens a check whose own sentence says
# "stays small". Small is a proportion, and the count is what the campaign is
# supposed to increase. Found 2026-08-27 by doubling the live corpus with
# IDENTICAL content -- 5 -> 10 reddened the old form having changed nothing.
# The share is flat across that same doubling (8.5% -> 8.5%), which is what says
# it is measuring the sweep rather than the vault.
frac = short / len(live) if live else 1.0
check(len(live) > 0 and frac <= 0.15,
      "the too-short remainder stays a small SHARE and is COUNTED, never dropped",
      f"{short} of {len(live)} = {frac:.1%} -- short town hops with 0-1 ticks. "
      f"The count is REPORTED, not asserted: it rises with the corpus and that "
      f"is the capture campaign working. What would mean something is the share "
      f"climbing, i.e. the sweep starting to find most connections unmeasurable "
      f"-- the cap is a little under 2x today's share")

print("== 2. the breakage guard: bounds real damage, passes honest jitter ==")
over = [(s, c, r["final_ms"]) for s, c, r in meas
        if abs(r["final_ms"]) > behaviourrun.CORPUS_DRIFT_MS
        or abs(r["final_ms"]) > behaviourrun.CORPUS_DRIFT_RATE
        * r["span_s"] * 1000.0]
check(not over,
      "no connection drifts past |final| <= 500 ms and <= 1% of span -- "
      "real breakage (a lost chunk, a misordered decode, a wrong scale) "
      "would blow both", f"over: {over}")

print("== 3. the walk returns to zero everywhere but the two named steps ==")
loose = [(s, c, r) for s, c, r in meas
         if abs(r["final_ms"]) > behaviourrun.TICK_BOUND_MS]
check(len(meas) - len(loose) >= 52,
      ">= 52 connections end within the tight 50 ms bound",
      f"{len(meas) - len(loose)}/{len(meas)}")
ids = {(s, STEP_UP[1] in c or STEP_DOWN[1] in c) for s, c, _r in loose}
check(all(s == "20260817T183756" and hit for s, hit in ids) and len(loose) == 2,
      "the ONLY connections beyond 50 ms are the two known 20260817T183756 "
      "steps -- pinned by identity, so a third appearing goes red",
      f"loose: {[(s, c[:22], round(r['final_ms'], 1)) for s, c, r in loose]}")


def one(stamp, portfrag):
    got = [r for s, c, r in meas if s == stamp and portfrag in c]
    if len(got) != 1:
        raise AssertionError(f"{stamp} {portfrag}: {len(got)} matches")
    return got[0]


up = one(*STEP_UP)
down = one(*STEP_DOWN)
check(abs(up["final_ms"] - 219.1) < 1.0 and abs(down["final_ms"] + 109.5) < 1.0,
      "the two steps are the measured ones (+219.1 / -109.5 ms) -- fixed "
      "files, so a moved value means the DECODE moved",
      f"up={up['final_ms']:+.1f} down={down['final_ms']:+.1f}")
check(up["mode_ms"] == 500,
      "the +219 connection ticks at 2 Hz (modal payload 500 ms) -- a town "
      "cadence, where jitter averages away slowest",
      f"mode={up['mode_ms']}")

print("== 4. the rate witness ==")
long_tight = [(s, c, r) for s, c, r in meas
              if r["span_s"] >= 1000 and abs(r["final_ms"]) <= 10.0]
check(bool(long_tight),
      "at least one connection spans >= 1,000 s and closes within 10 ms -- "
      "a ~4 ppm rate agreement, which is what rules out clock SKEW as the "
      "outliers' mechanism",
      f"{[(s, round(r['span_s']), round(r['final_ms'], 1)) for s, c, r in long_tight]}")

print("== 5. the error bars under the standing timed claims ==")
# test_respawn's pinned connections, each with the envelope its claim inherits.
r63805 = one("20260817T231139", ":63805->")
r54071 = one("20260817T231139", ":54071->")
check(r63805["envelope_ms"] <= 100.0,
      "the 120.499 s Student-revive connection carries a <= 100 ms envelope "
      "-- that claim's bar is +/- 0.08 s and it stands",
      f"envelope {r63805['envelope_ms']:.1f} ms over {r63805['span_s']:.0f}s")
check(r54071["envelope_ms"] <= 100.0,
      "the 30 s practice-target connection carries a <= 100 ms envelope -- "
      "the +/- 0.011 s SPREAD is at the jitter floor (the true clock is at "
      "least that tight), and the 30.0 s mean stands",
      f"envelope {r54071['envelope_ms']:.1f} ms")
check(up["envelope_ms"] >= 200.0,
      "the 10.044 s player-revive claim rides the +219 ms step -- its honest "
      "error bar is +/- 0.22 s, recorded in studies/isle 10 (the n=2 "
      "disagreement of 2.1 s already dwarfed it)",
      f"envelope {up['envelope_ms']:.1f} ms")
worst_env = max(r["envelope_ms"] for _s, _c, r in meas)
check(worst_env <= 800.0,
      "no envelope anywhere exceeds 800 ms (worst measured: a 750 ms "
      "transient on the -110 step connection)",
      f"worst {worst_env:.1f} ms")

print("== 6. the legacy two-capture bound still holds through this path ==")
legacy = [r for s, c, r in meas if s in ("20260807T143055", "20260810T235916")]
check(legacy and max(abs(r["final_ms"]) for r in legacy)
      <= behaviourrun.TICK_BOUND_MS,
      "the original preflight corpus stays within 50 ms through "
      "corpus_tick_sweep too -- same verdict, third code path",
      f"{len(legacy)} connections, worst "
      f"{max(abs(r['final_ms']) for r in legacy):+.1f} ms")

sys.exit(LEDGER.verdict())
