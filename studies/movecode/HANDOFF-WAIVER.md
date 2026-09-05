# HANDOFF — the stationary waiver, from a cold session

**Written 2026-09-05 at commit `990c6d7`, at the close of the session that shipped
`MOVECODE-1z-bn` and then spent the rest of the day trying to break it. REWRITTEN the same
day by the next session (`MOVECODE-1z-bs`), which closed the one experiment this file named,
at a desk, and shipped the clause that fell out of it.**

**Read [PLAN.md](../../PLAN.md) §3 for status and §8 for the live next-actions list. This
file does not restate either** — that is the failure mode `CLAUDE.md` opens with, and three
documents in this repo have already disagreed about status because they tried. What this file
carries is the part that does not live in a status table: **one open decision, its five
independent evidence readings, why no experiment is needed before ruling on it, and the traps
that cost two sessions real time.**

---

## 1. Where it stands, in one paragraph

The keyboard "seam stall" was **ours**. `agtrack_guard`'s AGTRACK re-pin fires a `0x002C` into
the client's own silent opening glide; the `0x002C` SetPositions **both** world copies and
rewinds the drawn body to the leg's start, killing the held key. The cause was localised to one
predicate — `stationary()` waives the 0.347222 s report-freshness gate whenever the last two
accepted reports coincide — and to the report ordering `{0x0047 stop → 0x003D walk-start}`,
which is *every keyboard leg's opening report pair* and is 0.000 u apart only because the body
has not moved **yet**. `WAIVER_WALKSTART_ENDS_STILL` refuses that one ordering (1z-bn, confirmed
on the client at 1z-bo, revert arm run at 1z-bp). **`WAIVER_NEWEST_MUST_BE_STOP` (1z-bs) then
applied the same argument to the only member of the pair whose kind bears on what is true after
it:** the waiver now survives only when the NEWEST report is a stop, because the corpus says a
coincident pair ending in a walk-start is followed by a walking body one time in six, at the
client's own speeds, and a pair ending in a stop is followed by a still body in 151 of 151.
**Both fixes are settled. What is open is whether the waiver's one surviving branch,
`{walk-start → stop}`, should exist at all.**

Full detail: `FINDINGS.md` §1z-bl (the defect), §1z-bn (the fix), §1z-bo (the confirming run
and two defects it found in §1z-bn), §1z-bp (the revert arm), §1z-bq (the founding specimen),
§1z-br (the wall press), **§1z-bs (the click path at desk, the ordering split, the clause)**.

---

## 2. ★ THE ONE OPEN DECISION — PLAN §7 **Q15**: should `STATIONARY_WAIVER` exist at all?

Do not re-derive this. Five readings, four from the archive and one from the client, all
reached the same place:

| # | reading | where |
|---|---|---|
| 1 | Of **85** real re-pin fires in 1,311 captures, the **25** the waiver carried are **all** on the refused pair. **Zero** on a pair the clause keeps. | §1z-bo.9, `waiverbenefit.py`; re-confirmed by three independent joins at §1z-bs |
| 2 | Replaying the corpus with the waiver **deleted** is identical to the shipped build in **zero** of 71 control-OK runs. | §1z-bo.5(b), `waiverretro.py` third arm |
| 3 | The waiver's **founding specimen** (RUN-1zAB run A) is on the refused pair and would have cost ~394 u. | §1z-bq.2 |
| 4 | Parking a body against geometry with the lead on produced **zero** kept-pair windows: a parked body restarts with the refused pair. | §1z-br.2 |
| 5 | **Where the waiver is live, the kept branch is a still body when the newest report is a stop (151 of 151) and a walking body 14 times in 87 when it is a walk-start.** The walking half is now refused. No kept window in the corpus has ever carried a re-pin want (317 windows; a complete enumeration of the sampled instants, not a sample). `{stop → stop}` never coincides. | §1z-bs.2–.4, `waiverclick.py` |

Readings 1 and 2 are **corroborating, not independent** — both read `_repin_block`'s
`age > gate and not stationary()` conjunction. Do not count them twice.

**Standing recommendation: delete `STATIONARY_WAIVER`, or equivalently leave the shipped
clause in place — on every capture held the two differ on nothing.** It is the owner's call.
The recommendation has moved once (§1z-bo.9 said keep, §1z-bq.5 said delete) and has not
moved since; a cold session should know that before adding a sixth reading.

**The question is now narrower than it was.** What survives is one branch, `{walk-start →
stop}`, and its case is a priori: a re-pin there could correct a drawn body that has diverged
from its reported point by *less* than the ≥ 299 u the client's own arrival test would
otherwise snap. No report chord can measure that (the reported point is where the re-pin goes,
so the chord is zero by construction — §1z-bq's error), no capture in the corpus has produced
it, and it has never met a re-pin want. **Keeping the branch also means closing a latent hole
found at §1z-bs.6**: `_approach_send` arms authsrv's click latch without reaching the guard's
`on_click`, so over an attack approach leg the waiver's own click refusal does not fire (zero
exposure: 9 grants in 3 captures). Deleting the waiver closes that for free.

### 2.1 ~~The ONE experiment that could still overturn it~~ — there isn't one, and the one this file used to name is closed

This section used to say the **click path** was the last route: "of the 180 stale coincident
`{0x003D → 0x003D}` pairs, 124 have a click in flight and 19 are keyboard-only." **All three
numbers are retracted** (§1z-bs.1): 180 was `waiverlive.py` scoring staleness with the pair's
own gap — trap 4.3 below, inside the instrument this file recommended; 124 reproduces only as
"a click within ~10 s before the pair"; 19 reproduces from nothing. And the guard's own click
contract — `on_click` sets `async_dest`, ANY report clears it, `stationary()` refuses while it
is set — makes the waiver **dead by construction** wherever a click has the body moving. Where
it is live after a click, the body is still.

**RUN-1zBS** ([RUN-1zBS.md](RUN-1zBS.md)) is registered as *optional confirmation* and is not
runnable today: it is a keyboard run that needs a harness verb for two overlapping keys, the
chord is W+Q / W+E (A and D are turn keys), the exposure floor is ~32 leg openings because
coincidence is a ~10 % lottery per opening, and the informative arm is the **revert**
(`--waiver-walkstart-pair-stands`) — the shipped build can only show zero. Q15 does not wait
on it.

---

## 3. The instruments, and how to run them

All read-only, stdlib only, whole corpus. In `studies/movecode/review/`. **Every window count
depends on two knobs — whether an open-ended last pair is closed on the capture's last row, and
whether pre-telemetry captures are read via their `t` field — and three honest scanners in one
fan-out produced 154 / 167 / 175 for "the same" census by varying them. Print the knobs.**

```bash
python studies/movecode/review/waiverclick.py --list --movers
```
**The 1z-bs instrument.** Joins every coincident pair to the guard's OWN state: its click
contract, the REAL stale window (t_b + gate → the next accepted report), its 2 Hz transition
log by sample-and-hold. Section D is the ordering split; section E the double walk-start.
Closed windows, wall-clock rows.

```bash
python studies/movecode/review/waiverretro.py --all
```
Retrodicts the 1z-bn clause; its stock/fix arms are now pinned with the 1z-bs clause OFF so
they keep measuring what their names say. Its **third arm** (waiver deleted) is also the shipped
build's retrodiction, since the two are one object on every capture held.

```bash
python studies/movecode/review/waiverbenefit.py
```
Every re-pin the waiver actually carried, split by report pair (reading 1).

```bash
python studies/movecode/review/waiverlive.py
```
Every coincident pair and whether it leaves a stale window — **corrected at 1z-bs** to use the
gap after the newer report.

**Do not reach for `guardretro.py` for anything to do with the waiver.** Its arms vary
`GATE2_SEAM_TOL` only. Reading its `removed by the fix: N` as a waiver clause's effect is a
category error and was nearly published as one (§1z-bo.5a).

---

## 4. ★★ Traps. Every one of these cost a session real time

**4.1 A control aimed at the wrong build is not a weak control, it is a filter.**
`waiverretro` first replayed **every** capture at `GATE2_SEAM_TOL = 0.0`; RUN-1zBL was silently
dropped from its own evidence population. Fixed at §1z-bo.5a: each capture replays at its own
recorded `AGTRACK_GATE2_SEAM`.

**4.2 A report pair and a guard decision are different events.** Joining them by a time window
produces false positives. **Join on the guard's own state at the decision instant.** §1z-br.5.
And a `blocked`/`due` row 40–60 ms *before* the pair formed was decided on the *previous* pair
(§1z-bs.4: two of the four "kept-pair wants" were exactly that).

**4.3 A census instrument can carry the trap it warns about.** `waiverlive.py` scored "stale"
with the pair's own gap (the gap *before* the newer report) for three sections and one handoff;
the waiver's window opens 0.347 s *after* the newer report. §1z-bs.1.

**4.4 A report-stream classification is not a guard-state census.** "124 with a click in
flight" was a fitted lookback; under the guard's `async_dest` contract that population is
50 pending / 17 going pending / 87 live. The waiver reads its own state, not the stream.

**4.5 Pooling two orderings with opposite behaviour reads as "p90 0.0 u" while one of them
walks.** Split `{walk-start → stop}` from `{walk-start → walk-start}` before quoting anything
about "the kept branch". §1z-bs.2.

**4.6 Each JSONL row stamps its own `time.time()`.** A report and its decoded 0x003D never
share a timestamp; join nearest within 2 ms. One blind lane joined on equality, got `None`
for all 1,370 pairs, and correctly refused to substitute a tolerance it was not told to use.

**4.7 Five specimens are not a population.** "The kept branch's live specimen is the
chord-opened leg" was over-read from five hand-picked rows; one of five had the claimed timing,
one was not a chord, 20 of 22 sub-45 ms double walk-starts are a parked body flicking keys,
and the moving population sits at 0.2–1.6 s gaps. §1z-bs.3, §1z-bs.9.

**4.8 The client's keyboard headings are CAMERA-RELATIVE, and A/D are TURN keys.** `S` moves
in −x; RUN-1zBR's `D:8` leg emitted zero wire messages while the heading rotated ~119°, so its
second "park" is a turn-in-place. The diagonals are `mt 2 = W+Q`, `mt 3 = W+E`. §1z-br.1,
§1z-bs.9.

**4.9 A module-global flag is read at CALL time.** Build and interrogate each arm under its own
setting; `old, new = arm(False), arm(True)` gives both the last arm's answer. And **a new
clause that subsumes an old one silently retires the old one's revert flag**: with 1z-bs on,
`--waiver-walkstart-stands` alone changes nothing, and RUN-1zBP's arm needs both flags. The
`[map]` line says so.

**4.10 A test fixture can invent the data it claims to replay.** §9's `run_a` built RUN-1zAB run
A's reports as walk-starts via a 2-tuple sig; the capture carries `0x003D` / `0x0047` /
`0x003D`. The fixture is SYNTHETIC on purpose and says so; sections 9 and 14 are now
interrogated with the 1z-bs clause off so they keep pinning the builds the runs measured.

**4.11 Score body motion through `w0score`'s `live` column, never raw `m_point`** (sample-and-
hold, settling every ~0.8–1.6 s) — and know that every displacement in §1z-bs is a chord to the
next REPORT, an upper bound, because owner-play captures carry no tape.

**4.12 Group trajectories on the OBJECT ADDRESS.** One agent id names two objects.

**4.13 A separation number from a rewound run is uninterpretable.** The `0x002C` reseeds both
copies. RUN-1zBP's 51.6 u against RUN-1zBO's 13.0 u is not evidence of anything.

**4.14 Quote RUN-1zBO's 13.0 u with its p90 of 170.2 beside it.** The number is a property of the
route.

---

## 5. What NOT to redo

- **The tracking comparators are settled.** RUN-1zBI **26.3 u**, RUN-1zBK **9.9 u**, **RUN-1zBL
  31.2 u**, RUN-1zBM 251.6 u, RUN-1zBO **13.0 u**. Cite the tape, not the section. §1z-bo.6.
- **The revert arm of 1z-bn has been run** (`9c65829`, RUN-1zBP). To reproduce it now, pass
  `--waiver-walkstart-stands --waiver-walkstart-pair-stands` together.
- **The click path is closed at desk** (§1z-bs.1–.2). Do not design a click run for the waiver.
- **The four "kept-pair wants" are explained from raw rows** (§1z-bs.4). Do not re-find them.
- **`gate2-offmesh` is UNTESTED, not confirmed.** Zero exposure in every arm on map 146's
  keyboard route, and every guard replay so far used `mesh=None`.
- **RUN-1zAB run A is not a parked-body specimen.** §1z-bq.

---

## 6. Standing debt this session did not clear

1. **Q15** — above, narrowed to one branch. The owner's ruling; no run is needed first.
2. **The approach-leg hole** (§1z-bs.6): `_approach_send` never reaches `on_click`. Closes for
   free under deletion; needs a second call site if the waiver stays. Zero exposure today.
3. **RUN-1zBS** — registered, optional, not runnable: needs a harness verb for two overlapping
   keys (`parse_walk` takes one key per step, `hold_key` blocks). The d1 lane's design is in the
   sheet; its W+A example and 40 ms default were wrong and are corrected there.
4. **`gate2-offmesh` exposure** — no route walked so far produces one, and no replay has run
   with a real mesh.
5. **PLAN Q13** (`D1_LEAD` on by default) — its precondition is met (§1z-bo); the ruling is the
   owner's.
6. **Movement-type census corpus-wide** — the nearest-2 ms join is in `waiverclick.py` §E now;
   nobody has yet tabulated which key transitions produce a coincident double walk-start across
   all 446 pairs rather than the 87 live windows.
