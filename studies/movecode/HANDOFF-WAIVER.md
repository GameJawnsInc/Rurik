# HANDOFF — the stationary waiver, from a cold session

**Written 2026-09-05 at commit `908a654`, at the close of the session that shipped
`MOVECODE-1z-bn`. Rewritten the same day by the next session (`MOVECODE-1z-bs`), which closed
the one experiment this file named, at a desk. UPDATED again the same day: the owner ruled on
Q15 and the waiver is DELETED (`MOVECODE-1z-bt`). This file is now the record of a closed
question and the traps it cost; it stays because the next cold session will otherwise
re-derive it.**

**Read [PLAN.md](../../PLAN.md) §3 for status and §8 for the live next-actions list. This
file does not restate either.** What it carries is the part that does not live in a status
table: the decision, its five evidence readings, what its deletion cost and did not cost, and
the traps that cost two sessions real time.

---

## 1. Where it stands, in one paragraph

The keyboard "seam stall" was **ours**. `agtrack_guard`'s AGTRACK re-pin fired a `0x002C`
into the client's own silent opening glide; the `0x002C` SetPositions **both** world copies and
rewinds the drawn body to the leg's start, killing the held key. The cause was one predicate —
`stationary()` waived the 0.347222 s report-freshness gate whenever the last two accepted
reports coincided — and the report ordering `{0x0047 stop → 0x003D walk-start}`, which is every
keyboard leg's opening pair and is 0.000 u apart only because the body has not moved **yet**.
1z-bn refused that ordering (confirmed on the client at 1z-bo, revert arm at 1z-bp); 1z-bs
showed the branch it kept splits by ordering, refused the half that walks, and found the
surviving half — `{walk-start → stop}` — still in 151 of 151 windows and never once met by a
re-pin want; **1z-bt deleted the waiver on the owner's ruling.** The freshness gate now stands
on report age alone. On every capture held that is zero behavioural change; RUN-1zBO is its
client-side witness.

Full detail: `FINDINGS.md` §1z-bl (the defect), §1z-bn (the fix), §1z-bo (the confirming
run), §1z-bp (the revert arm), §1z-bq (the founding specimen), §1z-br (the wall press), §1z-bs
(the click path at desk, the ordering split), **§1z-bt (the deletion)**.

---

## 2. ✅ THE DECISION — PLAN §7 Q15: `STATIONARY_WAIVER` is deleted

Do not re-derive this. Five readings, four from the archive and one from the client, all
reached the same place, and the owner ruled on them:

| # | reading | where |
|---|---|---|
| 1 | Of **85** real re-pin fires in 1,311 captures, the **25** the waiver carried are **all** on the refused pair. **Zero** on a pair the clause kept. | §1z-bo.9, `waiverbenefit.py`; three independent joins at §1z-bs |
| 2 | Replaying the corpus with the waiver **deleted** was identical to the shipped build in **zero** of 71 control-OK runs. | §1z-bo.5(b), `waiverretro.py` third arm (now retired) |
| 3 | The waiver's **founding specimen** (RUN-1zAB run A) was on the refused pair and would have cost ~394 u. | §1z-bq.2 |
| 4 | Parking a body against geometry with the lead on produced **zero** kept-pair windows: a parked body restarts with the refused pair. | §1z-br.2 |
| 5 | Where the waiver was live, the kept branch was a still body when the newest report was a stop (151 of 151) and a walking body 14 times in 87 when it was a walk-start. No kept window ever carried a re-pin want (317 windows, a complete enumeration of the sampled instants). `{stop → stop}` never coincides. | §1z-bs.2–.4, `waiverclick.py` |

Readings 1 and 2 were corroborating, not independent — both read the same conjunction.

**What the deletion removed:** the predicate, three switches, three CLI revert flags, the
report-kind bookkeeping, and every `agtrack_guard.*` key from the capture header. **What it
cost:** a maturing lead over a stale report is no longer pre-empted; the arrival matures and
the client's own test decides — the class 1z-bn already accepted, with zero corpus exposure.
**What it closed for free:** the approach-leg hole (§1z-bs.6) — nothing safety-bearing reads
`async_dest` any more. **No revert flag:** the arms of that era live in the captures' flags
rows and in FINDINGS.

### 2.1 ~~The ONE experiment that could still overturn it~~ — none was needed, and none is registered

The click path was closed at desk (§1z-bs.1): the three numbers this section used to rest on
are retracted, the guard's own click contract made the waiver dead wherever a click had the
body moving, and where it was live the body was still. **RUN-1zBS is withdrawn** — it existed
to witness the waiver's refused half, and there is nothing left to witness. A verbatim run of
the deleted build would reproduce RUN-1zBO by construction and is not registered.

---

## 3. The instruments, and how to run them

All read-only, stdlib only, whole corpus. In `studies/movecode/review/`. **Every window count
depends on two knobs — whether an open-ended last pair is closed on the capture's last row, and
whether pre-telemetry captures are read via their `t` field — and three honest scanners in one
fan-out produced 154 / 167 / 175 for "the same" census by varying them. Print the knobs.**

```bash
python studies/movecode/review/waiverclick.py --list --movers
```
The 1z-bs instrument: every coincident pair joined to the guard's OWN state — its click
contract, the REAL stale window (t_b + gate → the next accepted report), its 2 Hz transition
log by sample-and-hold. Section D is the ordering split. Measures the corpus as it was.

```bash
python studies/movecode/review/waiverbenefit.py
python studies/movecode/review/waiverlive.py
```
Every re-pin the waiver carried, by pair; every coincident pair and its real stale window
(corrected at 1z-bs). Both measure the corpus as it was; a waiver-carried fire cannot occur on a
post-1z-bt capture.

**`waiverretro.py` is RETIRED** — its arms no longer exist in the guard and it refuses to run;
its figures stand in §1z-bn.3, §1z-bo.5 and §1z-bs.5. **Do not reach for `guardretro.py` for
anything to do with the waiver** — its arms vary `GATE2_SEAM_TOL` only (§1z-bo.5a).

---

## 4. ★★ Traps. Every one of these cost a session real time

**4.1 A control aimed at the wrong build is not a weak control, it is a filter.**
`waiverretro` first replayed every capture at `GATE2_SEAM_TOL = 0.0`; RUN-1zBL was silently
dropped from its own evidence population. §1z-bo.5a.

**4.2 A report pair and a guard decision are different events.** Join on the guard's own state
at the decision instant, never a time window (§1z-br.5); and a `due` logged 40–60 ms *before*
a pair formed was decided on the *previous* pair (§1z-bs.4).

**4.3 A census instrument can carry the trap it warns about.** `waiverlive.py` scored "stale"
with the pair's own gap for three sections and one handoff. §1z-bs.1.

**4.4 A report-stream classification is not a guard-state census.** "124 with a click in
flight" was a fitted lookback; the guard's `async_dest` contract split the same population
50 / 17 / 87. The waiver read its own state, not the stream.

**4.5 Pooling two orderings with opposite behaviour reads "p90 0.0 u" while one of them
walks.** §1z-bs.2.

**4.6 Each JSONL row stamps its own `time.time()`.** Join a report to its decoded 0x003D
nearest within 2 ms; one blind lane joined on equality, got `None` for all 1,370 pairs, and
correctly refused to substitute a tolerance it was not told to use.

**4.7 Five specimens are not a population.** "The chord-opened leg" was over-read from five
rows; the moving population sat at 0.2–1.6 s gaps. §1z-bs.3, §1z-bs.9.

**4.8 The client's keyboard headings are CAMERA-RELATIVE, and A/D are TURN keys.** `S` moves
in −x; RUN-1zBR's `D:8` leg emitted zero wire messages while the heading rotated ~119°. The
diagonals are `mt 2 = W+Q`, `mt 3 = W+E`. §1z-br.1, §1z-bs.9.

**4.9 A module-global flag is read at CALL time**, and **a clause that subsumes an older one
silently retires the older one's revert flag** (1z-bs over 1z-bn). Both moot now — the flags
are gone — but the shape recurs.

**4.10 A test fixture can invent the data it claims to replay.** §9's `run_a` built RUN-1zAB
run A's reports as walk-starts; the capture carries `0x003D` / `0x0047` / `0x003D`. §1z-bq.

**4.11 Score body motion through `w0score`'s `live` column, never raw `m_point`** — and every
displacement in §1z-bs is a chord to the next REPORT, an upper bound, because owner-play
captures carry no tape.

**4.12 Group trajectories on the OBJECT ADDRESS.** One agent id names two objects.

**4.13 A separation number from a rewound run is uninterpretable.** The `0x002C` reseeds both
copies. RUN-1zBP's 51.6 u against RUN-1zBO's 13.0 u is not evidence of anything.

**4.14 Quote RUN-1zBO's 13.0 u with its p90 of 170.2 beside it.** A property of the route.

**4.15 Deleting a switch deletes the arms your retrodiction tools replay.** `waiverretro.py`
would have raised on its first attribute read; it now refuses by name. Grep the review tools
for every flag you delete, and for the command strings that pass it (`tapdrive.py` did).

---

## 5. What NOT to redo

- **The tracking comparators are settled.** RUN-1zBI **26.3 u**, RUN-1zBK **9.9 u**, RUN-1zBL
  **31.2 u**, RUN-1zBM 251.6 u, RUN-1zBO **13.0 u**. Cite the tape, not the section. §1z-bo.6.
- **Do not re-run RUN-1zBP's arm.** Its flags no longer exist; its capture is the record.
- **The click path is closed** (§1z-bs.1–.2). **The four "kept-pair wants" are explained**
  (§1z-bs.4). **RUN-1zAB run A is not a parked-body specimen** (§1z-bq).
- ~~**`gate2-offmesh` is UNTESTED, not confirmed.**~~ **CLOSED 2026-09-05, MOVECODE-1z-bv.**
  The deletion could not have removed a gate-2 re-pin: all 17 gate-2 fires in 1,311 captures
  were on a FRESH report with its predecessor ~100 u away, and all 25 waiver-carried fires are
  `arrival-risk` or `budget-red` (`review/gate2census.py`). **And the "every guard replay used
  `mesh=None`" clause was FALSE** — `guardretro.py` and `waiverretro.py` both build
  `MeshAdapter(pm)`. The real gap was that every fixture in `test_agtrack_guard.py` did, and
  §14 now closes it (floor 81), with the known-bad arm run against the old module.

---

## 6. Standing debt this session did not clear

1. ~~**PLAN Q13** (`D1_LEAD` on by default)~~ — **RULED 2026-09-05, landed as MOVECODE-1z-bu:**
   the keyboard lead (`KBD_SYNC_LEAD_ON`) ships ON, `--no-kbd-lead` reverts; the shipped default
   is RUN-1zBO's arm. Applied to the lead the runs measured, not to the `D1_LEAD` bundle — the
   assumption is stated in Q13 (§1z-bu.1).
2. ~~**`gate2-offmesh` exposure**~~ — **CLOSED at a desk, §1z-bv.** Nothing derived is left in this arc; what remains is [RUN-1zBW](RUN-1zBW.md), the operator's own session under the shipped default.
3. **The movement-type census** corpus-wide (all 446 coincident double walk-starts, not the 87
   live windows) — a curiosity, not a debt, now that nothing reads the pair.
