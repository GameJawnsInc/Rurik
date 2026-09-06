# RUN-1zCA — the stairs, with the plane column: does ANIMREF-RE §42.5's fix do what it derived?

**Registered before the run.** `MOVECODE-1z-ca`. This is the run §42.5 specified a month ago
and could not do, because it needs the client's own plane belief and `agenttap` had no column
for it. **The column exists as of §1z-bx.5 and has never recorded a run.** The PASS and REFUTED
clauses below are §42.5's, quoted, not re-derived here.

## 1. What is under test

**MOVECODE-1z-bz** (`NPC_PLANE_TRACK`): the follow's field 4 is the mover's own plane, tracked
at the copy's point; field 3 is the destination's. It replaced the plane the hostile **spawned**
on, stamped into both words for the life of the session.

Two other defaults shipped the same day and **this run cannot separate them**: the fence-gate
bound (§1z-bw) and the routed NPC follow (§1z-by). §1z-by in particular changes how the Hatcher
moves, so a difference from RUN-1zAB is not automatically the plane fix. That is stated here
rather than discovered afterwards.

## 2. THE EXPOSURE FLOOR — and this run has a real one

§42's own data came from RUN-1zAB: of 48 follow orders, **24 named a point our mesh places on
plane 29 only**. So the route is known to produce the exposure. But it is not guaranteed:

| | floor |
|---|---|
| follow orders whose destination our mesh puts on **plane 29 only** | **≥ 5** |
| tape samples with the player's own `plane` column reading **29** | **≥ 20** |
| the Hatcher receiving at least one follow order while the player is on 29 | **≥ 1** |

**ABORT:** below any of those the run is written as a **targeting failure** and scores nothing
in either direction — the same words RUN-FEEL earned. It does **not** become evidence that the
fix is fine.

## 3. THE PREDICTIONS — §42.5's PASS, quoted

> PASS: a `(29, 0)` follow at the foot, `(29, 29)` after the crossing, the Hatcher's copies on
> plane-29 ground with plane 29 in the new column, and one screenshot with the body on the
> treads. REFUTED if the Hatcher does not move on the `(29, 0)` order, or snaps — the P-17
> phasing door is a controlled-agent (AgTrack) mechanism and whether an NPC has one is UNREAD.

Restated as four checks:

**P1 — THE WORDS CHANGE.** At least one follow order reads field 3 = 29 with field 4 = 0 (at
the foot), and at least one reads `(29, 29)` (after the crossing). **REFUTED IF every order
still reads `(0, 0)`** — then the fix is not reaching the wire and everything else is moot.

**P2 — THE CLIENT ACCEPTS IT.** The Hatcher **moves** on the `(29, 0)` order. **REFUTED IF it
does not move, or snaps.** This is the one that could send the fix back: `(dest, cur)` is
DERIVED from 1,164 crossing *grants*, never observed on a *follow*, because no retail hostile
ever chased a player across a plane in 21 captures. If the client refuses it, §42.5's stated
fallback is the mover's plane twice — `--no-npc-plane-track` — and that is the next run, not a
patch invented at the keyboard.

**P3 — THE COLUMN AGREES WITH THE MESH.** The Hatcher's own `plane` column reads 29 while its
x/y sit on plane-29 ground. **This is the check the old tape could not make at all**, and it is
what turns §1z-bx.2's RECONSTRUCTION into an observation.

**P4 — THE BODY IS ON THE TREADS.** One frame with the Hatcher visibly on the stairs rather
than under them. The operator's original report was *"terrain-walks UNDER the stairs"*; this is
the only check that speaks to what they actually saw.

**Not predicted, recorded:** whether the routed follow (§1z-by) changes the order count against
RUN-1zAB's 48. It will; it is not this run's question.

## 4. The run — scripted, no human aiming

RUN-1zAB's route exactly, which is the one §42.5 names. The lead is now the default so
`--kbd-lead` is dropped (it would parse as a no-op).

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress and the script's presses ARE the arm. It ends on its own,
> about **60 s** of client time after the spawn verdict.

Both commands run from `C:\gd\Rurik`. Terminal 1:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

Terminal 2, started **immediately** — not after the client is up:

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/movecode/1zca-agenttap.jsonl
```

`--enemy` spawns the Hatcher and `--enemy-hit 0.02` keeps it survivable; the default kills in
about 7.5 s. The two `shot:1` verbs fire on the walk's own clock right after the climb and
right after the descent, and `--shots 2.0` samples the rest. The exe is named explicitly, never
discovered — `sorted(exes)[-1]` has picked the wrong build three times in this repo.

## 5. Scoring — decided now

| what | instrument | bar |
|---|---|---|
| exposure | follow orders joined to `pathmap.planes_at`; the tape's new `plane` column | §2's floors, **first** |
| P1 the words | decode every agent-10 `0x002A` from its own payload bytes, **never the label** | a `(29, 0)` and a `(29, 29)` |
| P2 the client | the tape: did agent 10's drawn copy move after the `(29, 0)` order, and by how much | movement, no snap |
| P3 the column | agent 10's `plane` against `planes_at(x, y)` | agreement on plane-29 ground |
| P4 the frame | the shots under `vault/captures/harness/<stamp>/` | body on the treads |
| regression | `review/followroute.py`, `review/fencelatency.py`, `review/repincheck.py` | unchanged; 0 violations |

Score P1–P3 off the wire and the tape **before** looking at the screenshots, so the frames are
not read to fit the numbers.

**One instrument caveat, known in advance:** the tape samples at about 11 Hz against a 30 Hz
nominal, with a ~57 ms stamp-to-read lag (§1z-bw.7). A crossing that lasts under ~90 ms can
fall between samples. If P3 comes back thin, that is why, and it is a sampling limit rather
than a null.

---

## RESULT — RAN 2026-09-05 23:32, 77.2 s. **ALL FOUR CLAUSES PASS.** Scored in [FINDINGS.md](FINDINGS.md) §1z-ca.

| | |
|---|---|
| exposure | **all three floors MET** — 24 orders onto plane-29-only (RUN-1zAB's own 24), 511 player samples on 29, 28 orders while the player is on 29 |
| **P1** the words change | **MET** — `(29,0)` → `(29,29)` → `(0,29)`, retail's NPC 11 sequence, **three times over**; 4 classes against RUN-1zAB's 48-of-48 `(0,0)` |
| **P2** the client accepts | **MET** — 262–321 u walked in the 1.5 s after each `(29,0)`, largest single step 31.7 u against ~26 u of ordinary walking. No snap |
| **P3** the column agrees | **MET** — the Hatcher reads plane 29 in 642 of 846 samples; **486 of the 511 samples the player is on 29 (95.1%)**; 471 agree / 9 disagree with our mesh |
| **P4** the body on the treads | **MET** — `walk3-shot.png`, t=17.64 |

**And a residual the predictions did not name, found by the operator:** the body sinks about
ankle-deep into a tread while parked (`hold007.png`). **The plane words do not explain it** —
through the whole hold every one reads 29, the segment and target points are INFINITE (so their
zero plane is residue, not an order), field 3 demonstrably reaches the segment plane 0.06 s
after the first crossing order, and the player shows the same pattern on a different message
family. It is a render-height question and **the tape has no z**. §1z-ca.5, registered.
