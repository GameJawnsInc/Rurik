# HANDOFF — the stationary waiver, from a cold session

**Written 2026-09-05 at commit `990c6d7`, at the close of the session that shipped
`MOVECODE-1z-bn` and then spent the rest of the day trying to break it.**

**Read [PLAN.md](../../PLAN.md) §3 for status and §8 for the live next-actions list. This
file does not restate either** — that is the failure mode `CLAUDE.md` opens with, and three
documents in this repo have already disagreed about status because they tried. What this file
carries is the part that does not live in a status table: **one open decision, its four
independent evidence readings, the single experiment that could still overturn it, and the
traps that cost this session real time.**

---

## 1. Where it stands, in one paragraph

The keyboard "seam stall" was **ours**. `agtrack_guard`'s AGTRACK re-pin fires a `0x002C` into
the client's own silent opening glide; the `0x002C` SetPositions **both** world copies and
rewinds the drawn body to the leg's start, killing the held key. The cause was localised to one
predicate — `stationary()` waives the 0.347222 s report-freshness gate whenever the last two
accepted reports coincide — and to one report ordering, `{0x0047 stop → 0x003D walk-start}`,
which is *every keyboard leg's opening report pair* and is 0.000 u apart only because the body
has not moved **yet**. `WAIVER_WALKSTART_ENDS_STILL` refuses that one ordering. It shipped ON
(`c72c585`), was confirmed on the client (`9ef5cde`), and its revert arm was run the same day
(`9c65829`). **The fix is settled. What is open is whether the waiver it narrows should exist
at all.**

Full detail: `FINDINGS.md` §1z-bl (the defect), §1z-bn (the fix), §1z-bo (the confirming run
and two defects it found in §1z-bn), §1z-bp (the revert arm), §1z-bq (the founding specimen),
§1z-br (the wall press).

---

## 2. ★ THE ONE OPEN DECISION — PLAN §7 **Q15**: should `STATIONARY_WAIVER` exist at all?

Do not re-derive this. Four independent readings, three from the archive and one from the
client, all reached the same place:

| # | reading | where |
|---|---|---|
| 1 | Of **82** real re-pin fires in 1,310 captures, the **22** the waiver carried are **all** on the refused pair. **Zero** on a pair the clause keeps. | §1z-bo.9, `waiverbenefit.py` |
| 2 | Replaying the whole corpus with the waiver **deleted** is identical to the shipped build in **zero** of 71 control-OK runs. | §1z-bo.5(b), `waiverretro.py` third arm |
| 3 | The waiver's **founding specimen** (RUN-1zAB run A) is on the refused pair too, and would have cost **~394 u** — its justifying "harm 0.000 u" measured the distance to the *report*, which is zero by construction. | §1z-bq.2 |
| 4 | Parking a body against geometry on purpose, with the lead on, produced **zero** kept-pair windows — structurally, because a parked body emits `0x0047` then restarts with `0x003D` at the same point, **which is the refused pair**. | §1z-br.2 |

Readings 1 and 2 are **corroborating, not independent** — both read `_repin_block`'s
`age > gate and not stationary()` conjunction. §1z-bo.9 says so; do not count them twice.

**Standing recommendation: delete `STATIONARY_WAIVER`, or equivalently make the clause
unconditional.** It is the owner's call and this session did not move it. Note for honesty that
my recommendation on Q15 **flipped once** (§1z-bo.9 said keep, §1z-bq.5 said delete) — the
evidence moved, not the reasoning, but a cold session should know the history before adding a
fifth reading.

### 2.1 The ONE experiment that could still overturn it

**The click path, and it is the only route left.** Of the 180 stale coincident
`{0x003D → 0x003D}` pairs in the corpus — the waiver's surviving branch — **124 have a click in
flight** and only 19 are keyboard-only (§1z-br.3). Clicks and the keyboard lead are **different
movers**. Every run in this arc drove the keyboard. So:

> A **click leg** with a re-pin risk on a kept pair has never been tested, and it is where the
> waiver could still earn its keep.

If you run it, pre-register it the way `RUN-1zBR.md` is written, and copy that sheet's
discipline of **deciding in advance what a null means** — 1zBR's P1 was refuted and the
refutation was the answer, which only worked because the sheet said so before launching.
§1z-bl already showed clicks produce long report silences, so the ingredients are there.

---

## 3. The instruments built this session, and how to run them

All read-only, stdlib only, whole corpus. In `studies/movecode/review/`.

```bash
python studies/movecode/review/waiverretro.py --all
```
Retrodicts the clause. Population selected by each capture's own logged verdicts; the clause
scored against the captures' **real `0x002C` fires**. Carries a **third arm** that deletes the
waiver entirely (Q15 reading 2).

```bash
python studies/movecode/review/waiverbenefit.py
```
Every re-pin the waiver actually carried, split by report pair (Q15 reading 1).

```bash
python studies/movecode/review/waiverlive.py
```
Every coincident report pair by ordering and gap — says whether the waiver's branch is
*reachable*, separately from whether it has *fired*.

**Do not reach for `guardretro.py` for anything to do with this clause.** Its two arms vary
`agtrack_mirror.GATE2_SEAM_TOL` (the §1z-bf fix) and the walk-start clause is ON in both, so it
is blind to this change. Reading its `removed by the fix: N` as this clause's effect is a
straight category error and was nearly published as one (§1z-bo.5a).

---

## 4. ★★ Traps. Every one of these cost this session real time

**4.1 A control aimed at the wrong build is not a weak control, it is a filter.**
`waiverretro` first replayed **every** capture at `GATE2_SEAM_TOL = 0.0` while computing the
shipped-tolerance arm and never reading it. Captures recorded *with* the tolerance then failed
a control checking them against a guard they never ran — and **RUN-1zBL, the run the whole
clause is A/B'd against, was silently dropped from its own evidence population.** The runs such
a filter excludes are biased toward sliver geometry, which is exactly where `gate2-offmesh`
lives. Published figures were wrong for a day. Fixed at §1z-bo.5a: each capture replays at its
own recorded `AGTRACK_GATE2_SEAM`.

**4.2 A report pair and a guard decision are different events.** Joining them by a time window
produces false positives: a scan of mine flagged a kept-pair re-pin risk, and at that decision
instant the guard was reading `{0x0047 → 0x003D}` because a new report had arrived in between.
**Join on the guard's own state at the decision instant.** §1z-br.5.

**4.3 The client's keyboard headings are CAMERA-RELATIVE.** A raycast on world axes gave a
wrong wall distance for RUN-1zBR (`S` moves in **−x**, not +y). The run survived only because
the capture proved the park independently of the prediction. §1z-br.1.

**4.4 A module-global flag is read at CALL time.** `old, new = arm(False), arm(True)` builds
both objects before either is queried and gives **both** the last arm's answer. A known-bad
check in `test_agtrack_guard.py` §14 went green **against itself** exactly this way. Interrogate
each arm under its own setting. Pinned in the test's own comments.

**4.5 A test fixture can invent the data it claims to replay.** §9's `run_a` built all three of
RUN-1zAB run A's reports as walk-starts via a 2-tuple sig. The capture carries
`0x003D` / **`0x0047`** / `0x003D`. That invention is why §14 could assert "the specimen still
waives" — the opposite of the truth. The fixture is now explicitly SYNTHETIC and stays so on
purpose (it is the suite's only kept-pair case); what changed is that it is no longer *described
as* the specimen. §1z-bq.4.

**4.6 Score body motion through `w0score`'s `live` column, never raw `m_point`.** `m_point`
(+0x78) is sample-and-hold, settling every ~0.8–1.6 s. Four published mistakes in this arc came
from this, including §1z-ai's "harm 0.000 u" that justified the waiver.

**4.7 Group trajectories on the OBJECT ADDRESS.** One agent id names two objects (world 0
`WORLD_SYNC` and the drawn copy). Filtering on `id == 1` interleaves two bodies hundreds of
units apart.

**4.8 A separation number from a rewound run is uninterpretable.** The `0x002C` reseeds *both*
copies, so on a rewound leg the divergence `w0score` exists to see never opens. RUN-1zBP's
51.6 u against RUN-1zBO's 13.0 u is **not** evidence the fix improves tracking, and neither was
the comparison against 1zBL. §1z-bl.6, §1z-bo.6, §1z-bp.4.

**4.9 Quote RUN-1zBO's 13.0 u with its p90 of 170.2 beside it.** One leg (the E strafe) ran
p50 133.3 u because world 0 parked 1.42 s at a plane-seam-clipped destination. The number is a
property of the **route**, not of the fix. §1z-bo.7.

---

## 5. What NOT to redo

- **The tracking comparators are settled and were mis-attributed for days.** Re-scored per tape:
  RUN-1zBI **26.3 u**, RUN-1zBK **9.9 u**, **RUN-1zBL 31.2 u**, RUN-1zBM 251.6 u, RUN-1zBO
  **13.0 u**. The 26.3 u attributed to 1zBL in five documents was 1zBI's; 1zBL's own had never
  been published. §1z-bo.6. Cite the tape, not the section.
- **The revert arm has been run** (`9c65829`) — `--waiver-walkstart-stands` restores the old
  behaviour on the same binary, three decision points matched to 0.01–0.02 s.
- **`gate2-offmesh` is UNTESTED, not confirmed.** Zero exposure in every arm on map 146's
  keyboard route. Do not read the clause's "0 of 9 removed" as a run result; it is the
  retrodiction's.
- **RUN-1zAB run A is not a parked-body specimen.** Anyone re-reading §1z-ah's comment block
  should find the correction already in it.

---

## 6. Standing debt this session did not clear

1. **Q15** — above.
2. **The clause's KEEP branch is unwitnessed in a decision that mattered.** Not once, anywhere,
   has the guard wanted to re-pin while reading a kept pair. §2.1 is the way to change that.
3. **`gate2-offmesh` exposure** — no route walked so far produces one.
4. **PLAN Q13** (`D1_LEAD` on by default) — its blocking precondition is now met (§1z-bo), but
   the ruling is the owner's and has not been made.
