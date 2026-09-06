# RUN-1zBW — the shipped default, as the operator actually plays it

**Registered before the run** (`MOVECODE-1z-bw`). Everything below is written down first so
the answers cannot be rationalised into agreeing with the shipped default afterwards.

**What is under test is a STACK, not a switch.** Since the operator last played, three things
changed: the AgTrack guard's stationary waiver was narrowed (1z-bn) and then **deleted**
(1z-bt), and the **keyboard lead is ON by default** (1z-bu, the owner's ruling on PLAN Q13).
The lead has been the default for zero minutes of ordinary play.

## 1. The primary question — ONE

> **Does your own body warp, rubber-band or stick while you are walking?**

That is the symptom the whole arc has been chasing, and it is the one the deleted waiver was
convicted of causing (§1z-bl.8: our `0x002C` re-pinning a body that had already left, 300–430 u
backward). Everything else below is secondary and must not be allowed to blur it.

## 2. ★★★ THE EXPOSURE FLOOR, AND IT IS THE WHOLE RISK OF THIS RUN

**RUN-FEEL is the precedent and it is exactly this trap.** On 2026-09-03 the operator played
for 24 s, reported "still seeing desync", and the capture showed **40 clicks and 5 keyboard
reports**: the treatment under test was keyboard-only, so it ran **zero trials** and the
session convicted a fix that had never executed. That is a zero-exposure result, not evidence.

The keyboard lead engages on `0x003D` — **held-key walking only**. Clicking to move does not
exercise it. So this run needs both arms, and the floors are registered here, in advance:

| arm | what it exercises | FLOOR — below this the arm scores NOTHING |
|---|---|---|
| **A. play as you actually play** (mouse, clicks) | the waiver deletion, the router, the stop echo | ≥ 60 s of movement |
| **B. deliberate keyboard walking** — hold W/A/S/D, several long legs, including turns | **the lead (1z-t term 1), the thing 1z-bu turned on** | **≥ 8 held-key legs, each ≥ 2 s**, and ≥ 20 `0x003D` reports in the capture |

**ABORT / re-read:** if arm B's floor is not met, the run is written as a **targeting failure
for the lead** and says nothing about it in either direction — the same words as RUN-FEEL, and
the reason they are here before the run rather than after it. Arm A still scores on its own.

Do the two arms in whichever order you like, but **do enough of B**. Roughly: two minutes of
ordinary play, then a minute of just holding movement keys around open ground.

## 3. THE PREDICTIONS

**P1 — THE PRIMARY.** No warp, rubber-band or stick during **keyboard** walking on open
ground. **REFUTED IF** it happens at anything like the frequency of the 08:46 session.

**P2 — NO NEW CLASS.** No warp class the previous default did not have. **This outranks every
number**: the lead is additive on the wire, so a new warp class would mean it is ordering
walks our mesh should have refused. Registered ahead because it is the failure mode a
"looks better" report hides.

**P3 — THE CLICK PATH IS UNCHANGED BY THE LEAD.** Warps during a long **click**-walk are NOT a
refutation of 1z-bu; that path has its own graveyard (the router, §1z-v). Recorded separately
so a mouse-driven complaint is not scored against a keyboard fix a second time.

**P4 — THE WIRE.** Zero AGTRACK `0x002C` on the player during a held-key leg's opening glide,
and zero legs that report the same point at their walk-start and their stop. RUN-1zBO's arm
gave 0 and 0; RUN-1zBP's revert arm gave 3 and 3. **REFUTED IF either is non-zero** — that is
the deleted waiver's symptom returning by another route.

**P5 — VALIDITY.** The capture's own `flags` row must read `KBD_SYNC_LEAD_ON: True` and carry
**no** `agtrack_guard.STATIONARY_WAIVER` key at all (it is deleted; a capture that still has it
is the wrong binary and the run is void). Origin `ours`.

**The first moment of a walk is the weakest point and is expected**: RUN-1zT measured the whole
residual as an opening-leg transient. A small jolt as you *start* moving is already recorded.
A warp *mid*-walk is not.

## 4. The run — **you drive this one**

No `--walk`: the question is about experience and there is no scripted substitute. Two
terminals, in this order. **The session ends when you close the client**; nothing times out.

Both commands are run from `C:\gd\Rurik` (the paths below are relative to it, and a git
worktree has no vault of its own).

Terminal 1 — the stack and the client:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --enemy --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02"
```

Terminal 2 — the tape, started **immediately**, not after the client is up (RUN-FEEL lost its
first 40 s to a tap that timed out waiting):

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 420 --wait 300 --out vault/research/movecode/1zbw-agenttap.jsonl
```

`--enemy-hit 0.02` keeps the Hatcher survivable; the default kills in about 7.5 s. The exe is
named explicitly and not discovered — `sorted(exes)[-1]` has picked the wrong build three times
in this repo. It is a loopback build carrying **our** DH parameters, so it may only be pointed
at our own server, which is what `session.py` does.

## 5. The four questions, in your own words

Asked verbatim **after** the session, not during:

1. **Did your own body warp, rubber-band or stick while walking?** — and was it while holding
   a key, or after a click? (this distinction is the whole run)
2. **Did anything feel different from your last session** — better, worse, or the same?
3. **Did the Hatcher swing at you from further away than it should have, or warp into you?**
4. **Did anything feel wrong that these questions did not ask about?**

Free-form after that. The operator's unprompted reports have been the reliable instrument in
this arc more than once; the questions are a floor, not a ceiling.

## 6. Scoring — decided now, not afterwards

| what | instrument | the bar |
|---|---|---|
| arm B exposure | `kbd_leg` + `0x003D` count in the capture | §2's floor, **first** — nothing else is read until this passes |
| the lead was really leading | grant rows: each grant's destination against the last accepted report | non-zero leads present, as RUN-1zBO's 13 of 48 |
| body enslaved rather than tracking | `w0score.py --grants …` enslavement block | must read **FREE**; ENSLAVED voids the separation number (§1z-x) |
| separation | `w0score.py` moving-only line | quote the p50 **with its p90 beside it** — §1z-bo.7, the number is a property of the route |
| our re-pins | `review/repincheck.py` | **0 violations**, and note the waiver-era licence no longer applies to a post-1z-bt capture |
| gate-2 | `review/gate2census.py` | any gate-2 fire here is the **first since the tolerance shipped** (§1z-bv.4) and is a finding in itself |

Score the wire **before** reading the operator's words, so the numbers are not fitted to them.

---

## RESULT — RAN 2026-09-05 21:31, 190 s. **P1 MET ("felt good"), and the run found a defect nobody had registered.** Scored in [FINDINGS.md](FINDINGS.md) **§1z-bw** (movement, the fence-gate latch, the corrected comparator) and **§1z-bx** (the two plane faults, the aggro death, the plane column).

### The operator, verbatim (asked after the session, answers unedited)

1. *"there were maybe 2 or 3 short warps"*
2. *"felt good"*
3. *"didn't swing, but had inconsistent aggro behavior and didn't walk on the bridge but
   rather terrain-walked on the ground below"*
4. *"i was able to get a terrain walk myself near the stairs by the spawn by spam clicking
   the top and bottom floors of the stairs over and over (hard to replicate, but did
   happen)"*

**Compare RUN-FEEL, 2026-09-03 08:46, the session that convicted the lead:** *"still seeing
desync, enemy at long range, and couldn't resume attacking after some point. bad run."*
Q3's "didn't swing" answers a question about swinging **from too far**, so the long-range
swing symptom reads ABSENT here. That is the 08:46 primary symptom, gone.

### The wire, scored BEFORE the answers were read

| | |
|---|---|
| validity (P5) | **MET** — `KBD_SYNC_LEAD_ON` True, **no `agtrack_guard.*` key** (waiver deleted = right binary), `D1_LEAD` False, origin `ours` |
| exposure (§2's floor) | **MET, both arms** — 229 × `0x003D`, 92 × `0x003E`, 13 × `0x0047`, 182 `kbd_leg`, 242 accepted reports over 190.4 s |
| tape | 2,064 samples / 189.2 s, 64 lost polls (3%) |
| re-pins | 5 × `0x002C`, **0 violations of the harm bound**, every one on a FRESH report (age 0.00–0.16 s). Classes: `gate1-red` ×3, `arrival-risk` ×1, plus one APPROACH re-pin (other sender) |
| enslavement | **MIXED at 0.1%** (2 of 1,930 moving samples) — under the 25% bar, so the body was substantially FREE and the separation figure stands |
| enemy's own two copies | p50 **0.0**, p90 9.8, max 39.7 — the Hatcher is faithful to itself; this is the player's desync, as §40.11 read it |
| gate 2 | no `gate2-offmesh` fire — consistent with §1z-bv |

**Separation, split by regime before quoting** (moving-only, `position_at` semantics; the
pooled figure is two populations with different treatments and must not be compared to a
scripted run):

| regime | n | p50 | p75 | p90 | max | body moved |
|---|---|---|---|---|---|---|
| **keyboard** (the lead's arm) | 1404 | **110.5** | 225.9 | 421.2 | 680.0 | 34,016 u |
| click (router's arm) | 525 | 91.5 | 387.5 | **849.6** | 872.9 | 14,066 u |
| pooled (what `w0score` prints) | 1930 | 107.9 | 263.1 | 507.5 | 872.9 | — |

Comparators, all moving-only p50 on **scripted** keyboard routes: RUN-1zBO **13.0**,
RUN-1zBI 26.3, RUN-1zBL 31.2, RUN-1zBM (lead OFF) **251.6**; retail's own copy trails
**~74**.

### What is open, and it is the interesting part

**The keyboard arm reads 110.5 u where RUN-1zBO read 13.0 u** — same binary, same map, same
arm. The regime split does NOT explain it away, and the three `gate1-red` re-pins corroborate
it from a second instrument (the server's own model independently found the copies > 299.33 u
apart). It sits between the lead-off 251.6 and retail's 74. **And the operator called it
"felt good", which is the recalibration that matters: 110 u of world-0 lag did not produce the
symptom.** Free play turns; the scripted route did not. Being scored.

**Two NEW plane faults, and they are probably one bug with two faces** — the NPC's follow
crossing under a bridge, and the player's own body terrain-walking at a staircase under
alternating clicks. A bridge and a staircase are separate planes. ANIMREF §42 derived exactly
this for the Hatcher (the follow's plane words frozen at spawn, retail tracking the mover's
plane) and did **not** ship it, for two stated reasons: **zero cross-plane hostile exposure in
the corpus, and no plane column in `agenttap`.** This session carries the exposure — the player
crossed planes **6 times** (0→19 at 53.8 s, back at 59.3; 0→29 at 81.9, back at 90.4; 0→29 at
173.2, back at 176.2) with **7 `plane_repair_due`** rows, four of them clustered in the two
seconds around the plane-19 crossing. The instrument gap is real and confirmed here: the tape's
per-copy fields are `flags, follow, maxspeed, movespeed, ptr, segx, segy, stop, tx, ty,
updated, vx, vy, world, x, y` — **no plane**. So every claim about what plane the CLIENT
believed an agent was on is RECONSTRUCTION until that column exists.

**One thing to reconcile with the operator:** the wire carries **5 × `attack_started: agent 10
swings at the player`**. Read together with Q3 that most likely means the swings happened but
not from an impossible range; if the operator saw *no* swing at all, that is a separate symptom
and this row is the evidence for asking again.
