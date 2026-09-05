# RUN-1zBO — lead ON, under the walk-start clause: is the rewind gone while the 26 u tracking stays?

**Registered before launching.** `MOVECODE-1z-bo`. The run §1z-bn.7 registers as the only
thing left on Q13, and the one §1z-bl.7 and §1z-bm.5 have each deferred. One run,
agent-driven, hands off, owner away.

## 1. What is being asked

§1z-bm measured the trade on both sides of the same route:

| | lead OFF (shipped) | lead ON (opt-in) |
|---|---|---|
| copy tracks the walking body | p50 **252 u** / p90 509 u behind | p50 **26 u** (retail's own ~74 u) |
| our `0x002C` rewinds the body | **never**, 0 in 7 long silent legs | **3 of 4** re-pinned legs, −298 to −433 u |

§1z-bn shipped the fix that is supposed to buy the right-hand column's tracking without its
rewind: `agtrack_guard.stationary()` no longer treats `{0x0047 stop → 0x003D walk-start}` as a
measurement that the body is still, so the freshness gate stands through a leg's opening glide
and the re-pin does not fire into it. **That is a retrodiction and a unit test — two of our own
components agreeing. This run is the verbatim check.**

**Both numbers must hold together, and either alone is uninformative.** Lead-off already
buys "no rewind" by not leading at all, which is exactly what RUN-1zBM measured; a lead-on run
that merely stops rewinding by also losing the tracking has reproduced RUN-1zBM with extra
steps.

## 2. The configuration — RUN-1zBL's exactly, plus the shipped fix

RUN-1zBL's arm (`KBD_SYNC` on, **`--kbd-lead` ON**, `AGTRACK_REPIN` on, router on, gate-2
tolerance on), no enemy, same `WSWQESW` route on map 146, `wait:8` opening, `--hold 30`. The
only difference from RUN-1zBL is `WAIVER_WALKSTART_ENDS_STILL`, which now ships ON — so this is
a one-change A/B against a run we already hold, at the same 26 hook sites.

**One change per test, and it is the one that matters.** `--waiver-walkstart-stands` exists and
is NOT passed; the capture header records the flag either way, so the arm is readable off the
capture rather than off this document.

## 3. THE PREDICTION

**P1 — EXPOSURE, and it gates everything.** At least **3 legs whose opening committed segment
is long**: the drawn copy's bake target ≥ 300 u ahead of the press point, and no c2s `0x003D`
for ≥ 1.0 s after the press. RUN-1zBM produced 7 of 7 and RUN-1zBL 4 of 7 on this route.
**REFUTED IF fewer than 3** — then the run never met the condition the fix acts on, it has
**zero trials**, and no null from it is quotable in either direction.

**P2 — THE DECISIVE ONE, and it is the fix's own claim.** **Zero AGTRACK re-pins fire during a
held-key leg's opening glide** (no `0x002C` to the player between a leg's walk-start and its
first subsequent `0x003D` or `0x0047`), against RUN-1zBL's **4**.
**REFUTED IF one fires.** Then record the guard's own `blocked_by` and `why` at that instant:
the fix predicts `stale-report`, so a re-pin that fires anyway is either a class the census
never saw or a defect in the clause, and either way §1z-bn's retrodiction is measuring
something other than what ships.

**P3 — THE TRACKING SURVIVES.** Moving-only world-0 separation (`w0score`'s §1z-bh line, via
`live` = `AgAgent::position_at`, **never raw `m_point`**) at **p50 ≤ 60 u**, against RUN-1zBL's
26.3 u with the lead on and RUN-1zBM's 251.6 u with it off.
**REFUTED IF p50 > 150 u** — then blocking the re-pin has cost the lead its tracking, the fix
has bought nothing over simply leaving the lead off, and Q13's answer is that the lead does not
come back.

**P4 — THE OUTCOME.** **Zero legs thrown back**; every leg's net travel within 15% of its
commanded distance; no leg reports an identical point at its walk-start and its stop.
**REFUTED IF a leg still nets ≈ 0 u.** If that happens *with* P2 met, the re-pin was not the
whole cause and §1z-bl's attribution needs a third explanation; §1z-bm's 7-of-7 makes that
unlikely, which is what makes it worth registering.

**P5 — CONTROLS.** Both DLL controls FIRED, ring not full. Nulls are not quotable otherwise.
Per §1z-bl.8, only zeros at sites **proven live in other captures** are quotable —
`mapfindpath` and `chcli_point` qualify; `heldbit`, `movecache` and `mapfindpath_ret1/2/3` do
not and will not be cited as findings.

## 4. EXPOSURE FLOOR and ABORT

P1's three long segments, or the run is written as a targeting failure and scores nothing —
not a null. A run that reaches P1 but loses a control is scored on P2/P3 positives only.

**What a partial result means, decided now rather than afterwards:** P2 met and P3 refuted is a
real answer (the fix works and the lead still does not earn its keep), and it is the outcome
that would send Q13 back to the owner as a plain trade. P2 refuted is a defect report against
§1z-bn and reopens the arc.

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver starts the tape, the harness and the hook. **It ends on its own, ~85 s.**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 30 --kbd-lead --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

with `agenttap.py --agents 1 --seconds 100` beside it and
`movehook/attach.py --minutes 1.1 --out vault/research/movecode/1zbo` fired at "body is in the
map". **The DLL is the main tree's build**, as in RUN-1zBL and RUN-1zBM; said out loud per the
cross-tree rule.

## 6. Scoring

Leg for leg against **RUN-1zBL**, which is the same configuration without the fix:

| what | instrument | 1zBL's value |
|---|---|---|
| opening segment length and silence | hook (`agapi_setdest` bake target) + wire | 460–767 u, 1.2–2.4 s |
| re-pins during the opening glide | wire (`agtrack_repin_fire`, `0x002C` label) | 4 |
| bodies thrown back | tape via `w0score.live` | 3, −298 to −433 u |
| moving-only separation | `w0score` §1z-bh line | p50 26.3 u |
| net travel per leg | tape via `w0score.live` | 0 u on the frozen legs |

`leadtap.align` works on a lead-ON capture (it failed on RUN-1zBM's lead-off one, §1z-bm.3),
so hook timing is anchorable here and the guard's `blocked_by` rows can be joined to the
client's own waypoints.
