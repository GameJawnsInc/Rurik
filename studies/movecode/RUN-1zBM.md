# RUN-1zBM — the lead-OFF control: a long opening segment with the re-pin suppressed

**Registered before launching.** `MOVECODE-1z-bm`. The control §1z-bl.8 correction 4 says the
corpus does not contain, and the run §1z-bl.7 / §1z-bk registered as next. One run,
agent-driven, hands off, owner away.

## 1. What is being asked, and why lead-OFF is the control

§1z-bl showed our AGTRACK re-pin rewinding a walking body 311–468 u to the leg's start on
every leg whose opening committed segment is long enough to keep the client silent. The
adversarial panel (§1z-bl.8) confirmed the mechanism but narrowed the claim: **the re-pin is
sufficient, not shown necessary**, because "re-pin fired" and "long silent first segment" are
the same four legs `{2,4,5,7}` in every capture we hold. **No leg anywhere has a long opening
segment with the re-pin suppressed.**

Lead-OFF supplies exactly that leg, *if* §1z-bl.8's correction 3 is right. That correction
says the opening glide is **the client's own keyboard reach (460–767 u, geometry-clipped),
not our lead** — the drawn copy bakes the client's own waypoint while the sync copy bakes our
grant, and on leg 4Q of RUN-1zBL they differed by 247 u. With `KBD_SYNC_LEAD_ON` false our
grant becomes the client's own reported point (zero-lead, the ≤ 1.0 u short-circuit), so our
model stops walking ahead of the report and the guard's `arrival-risk` / `budget-red`
arithmetic should never go red — **while the client's glide is unchanged**.

This is therefore two checks in one: the control the necessity claim needs, and a direct test
of correction 3.

## 2. The configuration — RUN-1zBL's exactly, minus `--kbd-lead`

The shipped default (`KBD_SYNC` on, lead off, `AGTRACK_REPIN` on, router on, guard's gate-2
tolerance on), no enemy, same `WSWQESW` route on map 146, `wait:8` opening and `--hold 30` so
the hook attaches and writes. The hook is armed again so the comparison with RUN-1zBL is
like-for-like at the same 26 sites.

## 3. THE PREDICTION

**P1 — THE CONTROL'S EXPOSURE, and it gates everything.** At least **3 legs whose opening
committed segment is long**: the drawn copy's bake target ≥ 300 u ahead, and no c2s `0x003D`
for ≥ 1.0 s after the press.
**REFUTED IF the client's opening segments are all short** (< 300 u) — then the glide length
*does* track our lead, §1z-bl.8's correction 3 is wrong, this run is not the control, and the
necessity question stays open.

**P2 — THE DECISIVE ONE.** **Zero AGTRACK re-pins during held-key legs.** With the model on
the report there is nothing for `arrival-risk` or `budget-red` to go red about.
**If a re-pin fires anyway**, record its trigger: that is a re-pin arm independent of the
lead, and it makes the harm a property of the shipped default rather than of the opt-in lead.

**P3 — THE OUTCOME.** Given P1 and P2: **zero legs thrown back**; every leg's net travel is
within 15% of its commanded distance; no leg reports an identical point at its walk-start and
its stop.
**REFUTED IF a leg still nets ≈ 0 u with no re-pin in it** — then the re-pin is not necessary,
something else rewinds the body, and §1z-bl's attribution needs a third explanation.

**P4 — THE LEAD-OFF LAW, as a cross-check on the review.** Moving-only world-0 separation
(`w0score`'s §1z-bh line) **≥ 300 u**, against 26 u with the lead on (**RUN-1zBI's** tape,
not 1zBL's — corrected at FINDINGS §1z-bo.6; 1zBL's own is 31.2 u) — the review's
fact 1 and §1z-bh.5 predict ~515 u. This costs nothing and ties the two runs together.

**P5 — CONTROLS.** Both DLL controls FIRED, ring not full. Nulls are not quotable otherwise.

## 4. EXPOSURE FLOOR and ABORT

P1's three long segments, or the run does not supply the control and is written as a
targeting failure. Both controls fired; the tape covers the legs; the gamesrv capture joins.
Per §1z-bl.8, only zeros at sites **proven live in other captures** are quotable —
`mapfindpath` and `chcli_point` qualify; `heldbit`, `movecache` and `mapfindpath_ret1/2/3`
do not and will not be cited as findings.

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver starts the tape, the harness and the hook. **It ends on its own, ~85 s.**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 30 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

with `agenttap.py --agents 1 --seconds 100` beside it and
`movehook/attach.py --minutes 1.1 --out vault/research/movecode/1zbm` fired at "body is in
the map". **The DLL is the main tree's build**, as in RUN-1zBL; said out loud per the
cross-tree rule. The worktree stays until scoring is finished (§1z-bl.8's process note).

## 6. Scoring

Per leg: the drawn copy's bake target and the opening segment's duration (hook), the
re-pin census (wire), net and peak travel through `w0score.live` — **never raw `m_point`** —
and `w0score`'s moving-only line for P4. Compared leg-for-leg against RUN-1zBL.

---

## RESULT — RAN 2026-09-05 12:46. Scored in [FINDINGS.md](FINDINGS.md) §1z-bm.

Capture valid: 5,863 records, ring 18% full, **both controls FIRED**. Flags confirm the
shipped default (`KBD_SYNC_LEAD_ON` false, `AGTRACK_REPIN` true).

| | |
|---|---|
| **P1** | **MET 7 of 7** — every leg opened with a 410–514 u committed glide and 1.57–2.77 s of silence, the same window 1zBL's re-pins fired inside (1.2–2.4 s) |
| **P2** | **MET decisively — ZERO re-pins, ZERO `0x002C` sent, whole run** |
| **P3** | **MET** — nothing thrown back; per-leg net travel 589–888 u (leg 7W peaks 683 / nets 589, no `0x002C` in the run, left UNVERIFIED) |
| **P4** | **MET** — moving-only separation p50 **251.6 u** / p90 509.2 / max 523.9, against 26.3 u with the lead on (**RUN-1zBI's** tape; RUN-1zBL's own is **31.2 u** — FINDINGS §1z-bo.6) |
| **P5** | MET — controls fired, ring not full |

**The control is supplied and the re-pin is NECESSARY as well as sufficient.** Long silent
segment with a re-pin → rewind (7 of 8 legs, 1zBK/1zBL); long silent segment without one →
the leg walks (7 of 7 here). §1z-bl.8's correction 4 is closed. Correction 3 is confirmed at
the byte: the client's opening waypoint is identical lead-on and lead-off (0.0, 0.0, 2.9 u on
the three comparable presses). **The warp is a cost of the opt-in lead, not of the shipped
default** — and it is not intrinsic to the lead, it is the guard's `stationary()` predicate.

**Instrument note:** `leadtap.align` finds no anchors on a lead-off capture (zero-lead grants
sit on the reported point; the client's setdest is 400–500 u ahead, so nothing pairs). All
timing here is wire and tape only.

