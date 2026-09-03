# MOVECODE-R8 — the empty cell, and the heal: the shipped default has NEVER been run armed

> **2026-09-03 late (MOVECODE-1z-v): the router is now the DEFAULT click policy.**
> This sheet's "armed, router off" cell — the shipped default when it was written —
> now needs `--no-router` to reproduce, and the "armed, router on" cell IS the
> shipped default. Read every `--router` below with that inversion.
>
> **NOT RUN. This sheet is a pre-registration.** It ran iff
> `studies/movecode/FINDINGS.md` grows a §1z-p heading —
> `grep -n '^## 1z-p' studies/movecode/FINDINGS.md`. Until then every number
> below is a prediction, and §4/§6.2 are the only places predictions live.

**Written 2026-08-30, after [FINDINGS §1z-o.10](FINDINGS.md).** That section
split the census by whether the repair was actually running and found the arm's
prospective record is **3 sessions, 549 reports, 11 disagreements, 0 fires** —
and that all four armed runs passed `--router`, an arm used in **14 of 1,210**
banner-carrying runs. **The cell "armed, router off" is empty.** Since the
repair is ON by default and `--router` is not, that empty cell is the shipped
default configuration: **the configuration this repo actually ships has never
once been run with the repair armed.** R8 is that run. R8b (§6) is the heal.

**Every command in this sheet runs from `C:\gd\Rurik`.** `git rev-parse
--show-toplevel` if in doubt — a worktree has no vault, `--exe` fails loudly
there but `attach.py --out` captures silently into a stray directory, and §5's
scorers crash on an empty glob.

> ## ⚠ WHY THIS IS TWO RUNS AND NOT ONE
>
> `RUN-R6.md` §3 states the rule and it governs here: **a sustained press during
> an active plane-carry manufactures the true lock signature on a client that is
> not locked** — frozen point + carried plane + live stream ≥ 5 s — and the
> trigger then fires CORRECTLY. Such a fire is real, and it is **unscoreable
> against specificity**, because specificity is the claim that fires happen only
> to genuinely stuck clients.
>
> So: **R8 provokes NOTHING** and scores specificity + the router confound.
> **R8b provokes deliberately** and scores authorship and the heal. Running them
> in one session contaminates both, and the contamination is not recoverable
> afterwards — you cannot tell a provoked fire from a spontaneous one in the
> tape. Two sessions, in this order, R8 first.

## 0. What these runs are

**R8 fills the empty cell.** Same shipped default the repair rides on, minus the
router. It answers one question the corpus cannot: **is the plane channel's
behaviour a property of the client, or of our click policy?** §1z-o.10 measured
the armed sessions granting **2.35 times per report** against the corpus's
**0.56** — a 4.2× difference, entirely attributable to routed legs — while the
disagreement rate barely moved (2.26% armed vs 2.34% replay). If disagreement is
the client's own business, R8 reproduces ~2.3% at a quarter of the grant rate.
If it is ours, it moves.

**R8b tries the heal, and tests §1z-o.6 on the way.** §1z-o.6 traced R7's lock
onset to our own router leg overriding the plane carry off the body's true 37,
and its recovery to our own clip-fallback grant computing a 37 from our mesh —
**both halves of that chain are router paths.** With `--router` off they cannot
run. So R8b is a genuine two-outcome experiment: an under-deck plane-0 episode
WITHOUT the router refutes §1z-o.6's authorship reading; the absence of one,
where R7 produced it reliably, supports it.

**The heal itself remains the prize.** Zero fires in four armed runs, and the
`0x002C` restamp has never met a live locked client. R7 reached **1.02 s of a
5.0 s `HOLD`** — 20% — and died because the client jumped ~100 u between
freezes (§1z-o.2/§1z-o.3). A *continuous* freeze is what the trigger needs.

## 1. Preconditions

The tree, stated once rather than assumed:

```bash
git rev-parse --show-toplevel
```

The instrument, before it is trusted:

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

The arm under test, and the census that motivated the run:

```bash
python toolkit/authsrv/test_planerepair.py
```

```bash
python toolkit/clientscan/planecensus.py --armed
```

That last one prints the empty cell this run exists to fill. **Read it before
you launch** — but as of 2026-08-30 the armed-router-off cell is no longer a
reliable staleness test: TWO armed router-off captures exist and neither
completes R8. **The staleness test is the header's**: R8 ran iff FINDINGS has
a §1z-p heading.

> **WHERE R8 STANDS, 2026-08-30 evening — partially read; only the bridge is
> still owed.**
>
> * `authsrv-20260830T183051-c1.jsonl` — attempt 1, ABORTED: spontaneous
>   carve-entry stuck at (−4314, −2206), walker dead 464 s, 117 clicks all
>   refused, client closed. Every floor unmet. See §7's last bullet.
> * `authsrv-20260830T185109-c1.jsonl` — attempt 2, banner CORRECT (armed,
>   router off), 5.7 min, 228 reports, ended early after an `attach.py`
>   mis-arm (a second attach is refused by design; the bin is only the
>   client-side cross-check, so nothing scoreable was lost). Against §4's
>   pre-registered floors:
>   **P2 READ and CONFIRMED** — grants/report **0.59** (predicted ~0.56,
>   refuted if >1.5, armed-router sessions 2.35; floor ≥100 reports met at
>   228). The armed sessions' 4.2× grant density WAS the router.
>   **P4 READ** — 0 echo rows against predicted <10 (floor = P2's, met);
>   session shorter than the 15 min the prediction assumed, stated honestly.
>   **P1 zero fires observed** but UNREAD — the ≥15-min full-sequence floor
>   was not met.
>   **P3 UNREAD** — zero plane-37 exposure; all 220 on-mesh reports sit on
>   plane-[0] ground. The deck was never crossed.
>
> **What completes R8: the §3 step-3 bridge phase alone** — six crossings of
> the west deck, ~10 min, hook optional — plus enough ordinary play to give
> P1 its 15 minutes. Do not re-run what is already read; do fold attempt 2
> into §1z-p when it is written.

## 2. The commands — R8

Terminal 1 — the server. **The only difference from `RUN-R6.md` §2 is that
`--router` is GONE**, which is the whole point. The repair still needs no flag;
it is ON by default.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--map 280"
```

> **`--exe` IS NOT OPTIONAL.** `session.py` defaults to the NEWEST build under
> `vault/run`, and `sorted(exes)[-1]` has chosen wrong three times; `vault/run/`
> also holds `reskin-roster`, which sorts last and is not a build.
>
> **`--game-args` needs the `=` form**, and the value must contain a space or
> argparse reads it as another option. `"--map 280"` does.

Terminal 1b — the live readout. The gamesrv's prints do not reach terminal 1
under this invocation; they go to the harness capture's `gamesrv.log`.

```bash
Get-Content -Wait -Tail 5 ((Get-ChildItem C:\gd\Rurik\vault\captures\harness\*\gamesrv.log | Sort-Object LastWriteTime)[-1].FullName)
```

**Before you play, confirm the banner in that tail says what you think it does.**
It must contain `plane repair (default ON)` and must NOT contain
`[map] --router ON`. That is a two-second check and it is the run's entire
premise — §C's rule is that the banner is the authority, and this sheet's whole
subject is a flag combination nobody has recorded.

> ⚠ **The banner scrolls past a `-Tail 5` attach** (observed 2026-08-30: the
> operator's tail opened after it printed and the premise went unconfirmed).
> If you missed it, check without disturbing the tail, in a separate window:
>
> ```bash
> Select-String -SimpleMatch -Pattern 'plane repair (default ON)','--router ON' -Path (Get-ChildItem C:\gd\Rurik\vault\captures\harness\*\gamesrv.log | Sort-Object LastWriteTime)[-1].FullName
> ```
>
> Exactly one hit — `plane repair (default ON)` — and no `--router ON` hit is
> a pass.

Terminal 2 — arm the hook on arrival at the bridge (§3 step 3), not at launch:
the DLL's timer starts at injection.

```bash
python toolkit/clientscan/movehook/attach.py --minutes 15 --out vault/research/movecode/r8
```

Last thing, after everything you want measured:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

> **`--stop` ENDS THE CAPTURE. It is the LAST thing you do.** Twice the most
> interesting event of a run happened after the hook was disarmed. When the
> 15-minute window expires the DLL disarms and writes by itself, and a second
> attach is refused by design — do not re-run `attach.py` into that refusal.

## 3. What to do in the map — R8. PROVOKE NOTHING.

1. **Ordinary play, ~3 minutes.** Walk and click around spawn, mixing keys and
   clicks. ⚠ The tail is the FULL gamesrv log and it is a firehose by design —
   every keypress prints heading and grant traffic. **"Silent" means the plane
   channel only: no line starting `[plane-echo]` and no line starting
   `[plane-repair]`.** Everything else is noise. (Observed 2026-08-30: the
   firehose was read as a step-1 failure; the run was healthy. The ladder never
   prints to console at all — it is JSONL-only, scored afterward.)
2. **The negative control, ~10 s.** On plain single-plane {0} ground — the
   walled compound east of spawn — hold a movement key INTO the wall for a slow
   ten-count, then release. **Note the wall clock.** This is the FREEZE half of
   the lock signature without the plane half, and it must not fire.
3. **Walk to the west bridge; arm the hook on arrival (§2 terminal 2).** Then
   the exposure phase, **~8 minutes**: cross the deck fully, turn, come back
   ACROSS it. Decks at (−1032, 6283) and (−2822, 6404). **Six crossings
   minimum** — that is P3's floor and it is what R6 did to reach 74 plane-37
   reports.
   * **ON the deck only. Do NOT go under it.** Under-deck is R8b's job, and an
     under-deck episode here contaminates P1.
   * **Press-and-release at the deck edges. Never a sustained hold** on or near
     plane-37 ground — that manufactures a lock (see the box above).
4. **Free play to a total of at least 15 minutes**, ordinary movement, no
   provocation, no sustained holds anywhere except step 2's wall.
5. `--stop`.

## 4. Predictions for R8, registered before the run

| # | Prediction | REFUTED IF | Floor |
|---|---|---|---|
| **P1** | **Specificity under the shipped default**: zero `[plane-repair]` fires; the `plane_repair_due` ladder never reaches `plane-lock`. | a fire in a session where the operator never experienced a stuck body — the first false fire on record. **NOT a refutation:** a fire after a sustained hold the operator was told not to do (report it separately, it scores nothing here); a `plane_echo` row without a fire (the tripwire watching a carry, which refutes nothing by itself); an `arming`/`holding` ladder row, which is ordinary churn. | ≥15 min of play including the full §3 sequence |
| **P2** | **THE CONFOUND TEST — grant density collapses.** On-mesh `0x0029`-family sends per position_report falls to the corpus's **~0.56**, from the armed-router sessions' **2.35**. | grants/report stays **above 1.5** — then the armed sessions' grant density was NOT the router and §1z-o.10's confound reading is wrong. | ≥100 position_reports, or P2 is UNREAD |
| **P3** | **The plane channel is the CLIENT's business, not our click policy's.** Disagreement per on-mesh report lands near the corpus rate — **predict 1.0–5.0%**, against 2.26% armed-with-router and 2.34% replay-only. | a rate **outside 0.5–8.0%** with the exposure floor met — either direction is news, and a rate near ZERO with real plane-37 exposure would say our own grants were producing the disagreements all along. | **≥20 reports on ground the mesh calls plane 37**, measured by §5. **Zero exposure is not a null**: under the floor, P3 is UNREAD, not passed |
| **P4** | **The echo channel scales with grants, not with time.** `plane_echo` rows fall roughly in proportion to P2's drop — predict **under 10 rows** for a 15-minute session, against R6b's 30 in a comparable one. | ≥30 echo rows at a grant rate near 0.56 — the echo channel would then not be grant-driven, and §1z-o.8's "the two channels are independent" needs restating. | P2's floor |

**No lock is the expected result and the run still scores**: P1–P4 are the first
prospective measurement of the configuration this repo ships.

## 5. Scoring R8, after the run

The census tool does all four in one pass, and the run's own capture is in it:

```bash
python toolkit/clientscan/planecensus.py --armed
```

That must now show **an armed capture with router off** — the empty cell filled.
Then the session on its own terms, which prints the exposure block P3's floor is
read from:

```bash
python toolkit/clientscan/planecensus.py --focus <the new capture's timestamp>
```

The raw plane channel, if you want rows rather than rates:

```bash
python -c "import glob,os,json; p=max(glob.glob(r'vault/captures/gamesrv/authsrv-*.jsonl'), key=os.path.getmtime); print(p); [print(l.strip()[:200]) for l in open(p,encoding='utf-8') if 'plane_repair' in l or 'plane_echo' in l]"
```

> **Check the filename's timestamp is THIS run's start before believing it** — a
> parallel session's capture can be newer.

**Report with:** the flags from the banner (quoted, not remembered), minutes of
play, position_report count, on-mesh count, plane-37 exposure count,
grants/report, disagreement count and rate, echo rows, fire count. **State which
denominator every rate used.**

## 6. R8b — the provocation run: authorship, and the heal

**A SEPARATE SESSION, after R8 is scored.** Same command as §2 (router still
off), fresh out dir `r8b`.

```bash
python toolkit/clientscan/movehook/attach.py --minutes 15 --out vault/research/movecode/r8b
```

### 6.1 What to do

1. **Straight to the west bridge.** Arm the hook on arrival.
2. **Get UNDER the deck**, by whatever technique produced R7's and r5bridge's
   under-walks. ⚠ §1z-f.4 established there is **no under-deck walkable ground
   of any plane and no legal path in** — the under-deck body is outside its own
   navmesh, and entry is a glitch, not a walk. If you cannot reproduce it in ~5
   minutes, **stop and say so**: "the glitch could not be reproduced" is a real
   result and it bounds every under-deck claim in the record.
3. **Once under: STAND STILL AND KEEP PRESSING.** This is the whole difference
   from R7. R7's client froze ~1 s, jumped ~100 u, froze ~0.55 s, and the
   trigger's EXACT float-equality point test re-armed on every jump — max streak
   **1.02 s of 5.0 s**. The trigger needs **5 s of continuous byte-identical
   reports**. Press one direction into the geometry and hold; do not click, do
   not turn, do not let go.
4. **Watch terminal 1b for `[plane-repair] fire #1`.** Note the wall clock.
5. **After the fire: RELEASE every key, count THREE seconds, THEN click once on
   nearby open ground.** ⚠ The release is not optional — the server drops any
   click within **3.0 s** of keyboard movement (`kbd-drop`), and a dropped
   heal-click reads as "heal refuted" when the click never reached the walker.
   If the body does not move: release, pause, click **again** before concluding
   anything.
6. **If the body walks — the heal is measured.** Keep playing several more
   minutes: a healed lock must show **no further fires**.
7. **If it does not walk** on release-paused clicks: keep keys and clicks going
   another 30 s. Repeat fires at ≤10 s intervals are themselves the measurement.
8. `--stop`, last.

### 6.2 Predictions for R8b

| # | Prediction | REFUTED IF | Floor |
|---|---|---|---|
| **P5** | **§1z-o.6's authorship, tested by removal.** With the router off, an under-deck body still declares plane 0 where the mesh offers only [37] — i.e. the glitch state's plane word is the CLIENT's, not our router leg's. | under-deck play produces **no** impossible-plane reports across ≥20 under-deck reports — then the plane-0 word was ours, §1z-o.6's chain is promoted from "probable" to "supported", and the router's ungated plane-matching (§1z-o.6) becomes a defect with a live witness. | ≥20 reports taken while under the deck. Fewer ⇒ UNREAD |
| **P6** | **The trigger CAN be provoked**: continuous byte-identical reports under an impossible plane reach `plane-lock` in ~5 s, and the ladder shows `arming → holding → plane-lock`. | 30 s of continuous mash **with a visible report stream** and no fire — then the trigger cannot fire even when handed its exact signature, which is a far bigger finding than the heal. | the press must produce ≥5 s of accepted byte-identical `0x003D` rows in the JSONL. **No stream ⇒ P6 UNREAD, not passed** |
| **P7** | **THE HEAL**: the body walks on the first release-paused click after fire #1, and play continues with no further fires. | movement does **not** resume on release-paused clicks, or fires repeat at ≤10 s with a live stream → the `agent+0x80` heal reconstruction is refuted (the trigger is not). **NOT a refutation:** a heal-click whose JSONL verdict is `kbd-drop` — that click never reached the walker; the probe is void and the next release-paused click is the real one. | conditional on P6. No fire ⇒ P7 UNREAD |

⚠ **R8b SCORES NOTHING ABOUT SPECIFICITY.** Its fire, if it comes, is
manufactured by design. Do not carry it into P1, and do not let a later reader
carry it either — say "provoked" beside every R8b fire count.

## 7. Known failure modes

- **The banner is the authority, and this run turns on a flag.** Confirm
  `plane repair (default ON)` present and `[map] --router ON` ABSENT in the tail
  before playing. A sheet that assumed `report.json` recorded the flags was
  wrong about R7 for exactly this reason.
- **`--stop` last.** Both prior runs lost their most interesting event to an
  early stop.
- **A relative `--exe` fails in an agent shell** and is not a `session.py` bug:
  agent shells set `NODEFAULTCURRENTDIRECTORYINEXEPATH=1`. Use an absolute path.
- **The hook window is 15 min and the ring fills at ~18 min.** A lock late in
  play still scores fully — P1/P5/P6/P7 are all server-side; the bin feeds only
  the client-side cross-check.
- **movehook's observer effect is unmeasured** (19 persistent `int3` taps). Every
  timing claim here rides through them, including the 5 s `HOLD` the run turns
  on.
- **Do not quit on a lock.** It is the jackpot. The heal is the one thing four
  armed sessions have not been able to try.
- **A spontaneous CARVE-ENTRY STUCK is possible under this configuration, and
  it has no rescue channel. It happened on the first attempt (2026-08-30,
  `authsrv-20260830T183051-c1.jsonl`).** With `--router` off, a click the
  server refuses is left to the client's own pathing, and the client
  dead-reckons: on the abort tape it took a **530 u step in 0.27 s** toward a
  refused click behind the compound wall, landed on rendered ground the mesh
  deliberately carves out (off-mesh — RECONSTRUCTION for the step's mechanism,
  OBSERVED for everything after), and its walker died. ⚠ **And the stuck was
  not the session's only anomaly — the operator reported multiple warps, and
  the tape confirms it**: three more warp-scale corrections during ~1.6 min of
  ordinary click-heavy play (implied 476 / 664 / **3,198** u/s, the last one
  backward — the drag-back), ~2.5/min against the pre-router default's
  measured 2.67. RECONSTRUCTION: refused clicks starve the sync copy while
  the client self-paths, and the desync test drags the body back — the
  pre-router warp regime returns for click-driven play under this
  configuration. **Expect visible warps in step 1; they are data, not a
  failed run.** The park itself: **464 s of
  byte-identical reports with changing headings, 117 clicks all refused, 53
  zero-lead grants echoing the stuck point back, zero ladder rows after the
  entry transition, zero `[plane-echo]` lines** (the tripwire is off-mesh
  blind by design), and the repair correctly DISARMED throughout (off-mesh
  clause — there is no plane to restamp to). R6b's identical class was healed
  in 81 ms by a routed grant; with the router off the only exit is closing the
  client. If it happens: note the wall clock, try release-3s-then-click twice,
  then close the client, Ctrl+C the harness, relaunch, and restart the sheet
  from step 1 — the abort capture is still real data, scored on its own.
  **Do not press M to orient** — the world map crashes the client on this map
  (the FOG INIT SKIPPED line in the banner).
