# RUN-1zAH — the retract: does the stationary waiver pre-empt the arrival that armed the lock?

**One question, two arms, four runs of ~90 s of client time, no human aiming.**
Registered before the run, per the probe rule. This scores `MOVECODE-1z-ah`
(`studies/movecode/FINDINGS.md` §1z-ah, main `632b3c1`), whose §1z-ah.7 registered the
prediction this sheet expands into a procedure.

Behaviour under test: `agtrack_guard.STATIONARY_WAIVER` — the AgTrack re-pin's
report-freshness gate is waived when the last two **accepted** reports agree to within
the client's own `ZERO_DIST_SQ`, because a body measured still has a re-pin harm bound of
1.0 u rather than `RUN_SPEED × age`. Everything else is the shipped default of `main` at
`632b3c1` or later, and the lead is still opt-in (`--kbd-lead`), exactly as RUN-1zAB ran it.

**Status: RAN 2026-09-03 21:42-21:51, four runs. MECHANISM CONFIRMED (four retracts, every one at 0.0 u of harm, zero violations); OUTCOME **REFUTED** by this sheet's own clause -- arm T's second run had a held-key parked leg. The result block is below; `--kbd-lead` stays OFF and the waiver stays ON.**

---

## 1. The question

> On the same script that locked three times in four runs, does the retract fire —
> and does the lock stop arming?

§1z-ag identified the armer: a keyboard lead matures, the client snaps the drawn body
onto the granted point across a gate-1 separation, and the AgTrack fence clears and never
re-arms. §1z-ah found the guard had **already predicted that exact snap 0.425 s early**
and was refused by one precondition. This run asks whether lifting that precondition does
what the mirror says it does, on the client.

**Two questions, and they are not the same question.** The *mechanism* (does the retract
fire, on the body, without a yank) is a positive event — one firing settles it. The
*outcome* (does the lock stop arming) is a race by construction (§1z-ae.1), and RUN-1zAB
ran clean once and locked once on an identical script, so it needs both arms.

## 2. The prediction, registered

### 2a. The mechanism — the rows, verbatim

| registered before the run | |
|---|---|
| **The row that was `blocked` becomes `due`** | `agtrack_repin code=due why=arrival-risk` where run A logged `code=blocked` / `blocked_by=stale-report` |
| **A retract goes out** | `agtrack_repin_fire why=arrival-risk`, and an `AGTRACK RE-PIN 0x002C` wire label |
| **THE HARM BOUND — this is the whole safety argument** | every fired re-pin's point is **within 1.0 u of the report immediately preceding it**. The mirror measured 0.000 u on run A's leg |
| **The dead leg is collected** | `kbd_leg act=clear by=0x002C` beside the fire |
| **The arrival it pre-empts does not snap** | no 520 u body jump onto our granted point in the samples after the fire |
| **CONFIRMS the mechanism** | all five above, on at least one fired retract |
| **REFUTES the mechanism, on safety** | **any** re-pin fired where the last two accepted reports were **> 1.0 u apart** — that is the walking body, and `AgMsg.cpp` 584 means it drags the drawn copy. The corpus says this should never happen (§3) |
| **REFUTES the mechanism, on effect** | the retract fires and the fence still shuts on that leg's arrival anyway |

### 2b. The outcome — the lock

| | |
|---|---|
| **Prior, this exact script** | locked 3 of 4 runs. Run A: **1 reported stop for 7 key legs**, 5 of 8 legs parked, `w0score` ENSLAVED 29 of 60 (48.3 %). The clean one: 7 stops of 7 |
| **CONFIRMS** | arm T (waiver ON) reads **FREE** on both runs with reported stops ≈ 1:1 per key leg, **and** arm C (waiver OFF) locks at least once — the known-bad arm must score badly, or the metric is measuring the wrong thing |
| **REFUTES** | arm T locks (ENSLAVED, or a held-key leg moving ≤ 50 u, or stops ≪ legs) on a run where a retract **fired** |
| **INCONCLUSIVE** | arm T clean but **no retract fired** (see §3 — that is run B's luck, not evidence); or arm C clean twice, which leaves the treatment uninterpretable because the regime never produced the defect |

**A failed control must not void the treatment.** If arm C happens not to lock in either
run, arm T's *mechanism* result (§2a) still stands on its own — it is a positive
observation of rows, and the control interprets a null, it has no authority over a
positive.

## 3. The exposure floor — mined from the corpus, not guessed

Every `agtrack_repin ... why=arrival-risk code=blocked` row in the whole gamesrv corpus
was re-scored against the waiver's predicate (the last two accepted reports before it):

| | |
|---|---|
| captures with arrival-risk rows | 11 |
| blocked rows total | 38 |
| **would convert to a retract** (body measured still) | **11** |
| **stay blocked** (body had moved — the warp case) | **27** |
| distance between the last two reports, in those 27 | **min 12.7 u, p50 101.9, max 524.4 — none under 10 u** |
| the lock run's three rows | 101.9 u → blocked · **0.0 u → RETRACT (the fatal leg)** · 520.0 u → blocked |

**The population is bimodal — exactly 0.0 u or ≥ 12.7 u — so the 1.0 u boundary is
nowhere near marginal.** That is the pre-registered basis for expecting no false retract.

**Per-run exposure, from the same scan:** `--kbd-lead` captures produced 0, 0, 0, 0, 1, 1,
2, 2, 2, 3 convertible rows. **Six of ten had at least one; four had none.**

- **FLOOR: arm T must produce ≥ 1 fired retract across its two runs.** Two runs at the
  observed rate is ~84 %. **Zero fired retracts = this run measured nothing about the
  mechanism** — say exactly that, repeat, and do not read arm T's clean result as
  evidence for anything.
- `w0score` refuses a verdict under **500 u** of body translation across **20** moving
  samples; **≥ 8 `KBD LEAD`** grants must be on the wire.
- **Zero exposure is not a pass.** A census zero for the KILL or the FENCE GATE is zero
  exposure by the script's construction, as it was for RUN-1zAB.

## 4. The run

**Announce it first — the machine is shared and `Gw.exe` fights for input focus.**

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> **`--walk` drives every keypress. The script's own presses ARE the arm.** The run
> opens with `wait:3` and the character stands still — it is not waiting for you. A
> helpful press produces a double-driven regime (RUN-1zT's first attempt: 720 u of travel
> no script asked for). Each run ends on its own: ~90 s from launch to the window closing,
> nothing is left parked.
>
> **The one useful thing a human can do is WATCH for a backward yank.** A re-pin that
> reached a walking body would drag the drawn character backward — the warp this repo
> removed once before. The rows should make it impossible (§3); an eye on it is free.

### Pre-flight (once, before the first run)

```powershell
python toolkit/clientpatch/dhbuild.py
```

Must end `Every build is where it belongs.` — the loopback build carries OUR parameters
and may only be pointed at our server.

```powershell
python toolkit/clientscan/w0score.py --baseline
```

Must print all three: `control reproduces: live p50 237.0 / max 516.1`, `the zero-lead
baseline reads FREE`, and `RUN-1zT's registered arm reads ENSLAVED from 17.77 s`. If any
is missing, stop — the detector cannot find the known contamination and cannot clear a
new run.

### The four runs, in this order: **T, C, T, C**

Alternating, so a drift in machine state cannot line up with one arm. Terminal A first
(the tap waits for a client to reach a map, so starting it early is free), then Terminal B.

**Terminal A — the tap, once per run:**

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

**Terminal B, ARM T (runs 1 and 3) — the shipped default, waiver ON:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

**Terminal B, ARM C (runs 2 and 4) — the known-bad arm, run A's configuration:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --no-repin-stationary-waiver"
```

The script, the build and every other flag are **RUN-1zAB's, verbatim** — one variable
changes between the arms. `--exe` is not optional (every address in this arc is build
38797). `--enemy-hit 0.02` keeps the Hatcher chasing without killing the player. **Do not
add `--resync`** (§1z-ab.3 ii).

**Which arm a capture was is recorded, not remembered.** Each capture's header row now
carries `agtrack_guard.STATIONARY_WAIVER` (added for this run — `capture_flags`
discovered only `authsrv`'s own globals, so a switch in a policy module beside it was
invisible). Arm C also prints a banner line naming itself.

## 5. Scoring

Read-only, in this order, per capture.

```powershell
python studies/movecode/review/gatecensus.py
```

The gates' rows from the newest gamesrv capture. **This is the primary readout**: the
`agtrack_repin` rows with their `code` and, when blocked, `blocked_by`; every `0x002C` by
sender; the `kbd_leg` lifecycle.

```powershell
python toolkit/clientscan/w0score.py
```

The FREE / MIXED / ENSLAVED verdict with its onset, the world-0 vs body separation and
the exposure block. It finds the newest tap and the gamesrv capture whose wall span
overlaps it. For the per-leg table (each leg's travel against its hold), add the harness
report the session printed — the option takes a path and errors without one:

```powershell
python toolkit/clientscan/w0score.py --legs vault/captures/harness/<stamp>/report.json
```

**And the harm check, which no existing tool performed — this is the safety readout:**

```powershell
python studies/movecode/review/repincheck.py
```

Per fired `0x002C`: the point sent (decoded from the wire bytes, because the label rounds
to integers and cannot answer a 1.0 u question), the age of the report it carries, the
distance between the last **two** accepted reports — the waiver's whole predicate — and
where the **next** report lands. Scoped to the `AGTRACK RE-PIN` sender, because the other
`0x002C` arms never pass through the re-pin's preconditions.

**Every stale re-pin must read `prev_d` ≤ 1.0 u.** One row above it refutes §2a on
safety whatever else the run says, and the script exits non-zero so it cannot be skimmed
past.

> **This metric discriminates, checked both ways before the run.** It reads **0
> violations over the 1,262-capture corpus** (89 `0x002C` sent, all licensed), and it
> goes **red, exit 1**, on a synthetic capture where a stale re-pin fires at a body that
> moved 512 u. Scoring the other senders by this rule made the corpus read 7 violations
> that predate §1z-ah entirely — a metric red before the change ran cannot score the
> change, which is why it is scoped.

Optional, for the maturation reading per lead leg (distance still to go at the re-aim,
any park). The option takes a path; bare, it runs a whole-corpus census instead:

```powershell
python toolkit/clientscan/leadmargin.py --tap vault/research/animref/agenttap-<stamp>.jsonl
```

## 6. What each outcome means

- **CONFIRMED (mechanism + outcome).** The armer §1z-ag identified is closed by a derived
  gate change, and `--kbd-lead` becoming the default returns to `PLAN.md` §7 Q13 as a
  bundle question for the owner, with these captures as evidence. Next is `0x005FCAA0`.
- **REFUTED on safety** (a re-pin at a moved body). The discriminator in §1z-ah.4 is
  wrong and the waiver reverts the same day — `--no-repin-stationary-waiver` is already
  the flag. Read which two reports the guard compared: the answer is whether
  `prev_pos` tracks what §1z-ah.4 says it tracks.
- **REFUTED on effect** (retract fires, lock still arms). Then the arrival is not the only
  armer after all, which re-opens §1z-af's "something else arms it too" — and that is a
  finding about the client, not about this fix.
- **INCONCLUSIVE (no retract fired).** Say so, repeat once. If a repeat also produces no
  exposure, the script is the wrong instrument for this and the next move is a route with
  a wall — a body held against geometry parks while its key is held, which is run A's
  shape by construction rather than by luck.

## 7. Honest limits, before the fact

- **n is one map, one route, one build**, chosen to match RUN-1zAB per leg on identical
  input.
- **§1z-ah shipped a second change on the same commit**: a `0x002C` now clears the
  keyboard leg record. It is reachable only through a `0x002C`, and the waiver makes more
  of those, so the two interact in arm T. It cannot cause a lock (it only stops the kill,
  the refresh and the watchdog acting on a leg the client has already discarded), and arm
  C carries it too — so **arm C is run A's configuration except for that clear and the
  new telemetry field**. The fatal leg arms from a fresh report *after* the `0x002C` that
  would trigger it, so the compared path is unaffected; that is an argument, not a
  measurement, and it is why it is written here rather than assumed.
- **The retract shuts the fence** (§1z-ah.6). The census will show a shut window per
  fire; that is the trade, not a surprise.
- **This run cannot price the click path** — nothing here clicks — and the KILL still has
  zero exposure by the script's construction.
- **`movetap` is not used**: it cannot certify a capture taken under the harness
  (§1z-ag.6, 10.2 / 12.0 Hz against a 50 Hz floor). The mechanism is scored from the
  gamesrv rows, whose timing the tap's rate cannot affect.

## 8. Who should drive this

**Nobody needs to aim, so it does not have to be handed over.** Every input is scripted,
the tap sends nothing (read-only `ReadProcessMemory`), and each session closes itself.
The repo's boundary is aiming, not seeing. The session that set this up can drive all
four runs on a go-ahead — ≈ 6 minutes of client time in total, announced first, with
nothing left parked. If the operator would rather watch, §4's block says the one thing
worth watching for.

---

## ★ RESULT — RAN 2026-09-03 21:42–21:51, four runs, **MECHANISM CONFIRMED / OUTCOME REFUTED BY THIS SHEET'S OWN CLAUSE**

Agent-driven, hands off. Captures: T1 `authsrv-20260903T214318-c1` × `agenttap-20260903T214319`,
C1 `…214558-c1` × `…214600`, T2 `…214815-c1` × `…214816`, C2 `…215027-c1` × `…215028`.
Full record: `studies/movecode/FINDINGS.md` §1z-ai.

| run | arm | reported stops / 7 key legs | legs armed | parked legs | retracts | travel |
|---|---|---|---|---|---|---|
| T1 | waiver **ON** | 7 / 7 | 32 | **0** | 3 | 5,894 u |
| C1 | waiver OFF | 7 / 7 | 25 | 2 | 0 | 3,514 u |
| T2 | waiver **ON** | 7 / 7 | 33 | **1** | 1 | 4,727 u |
| C2 | waiver OFF | **1 / 7** | **7** | **5** | 0 | **773 u** |

### §2a THE MECHANISM — CONFIRMED, every registered row

**Four retracts fired, all in arm T.** Every one of §2a's five rows appeared:
`agtrack_repin code=due why=arrival-risk` (T1 at 18.10 / 30.31 / 40.49, T2 at 30.27) exactly
where arm C logged `code=blocked blocked_by=stale-report` (C1 ×2, C2 ×2); the
`AGTRACK RE-PIN 0x002C` went out; `kbd_leg act=clear by=0x002C` sat beside it.

**THE HARM BOUND HELD ABSOLUTELY.** Every fired retract read `prev_d = 0.0 u` — the body
had not moved a unit across the two reports that licensed it — and **`next_d = 0.0 u`**:
the next accepted report landed exactly on the point we pinned to, which is the closest
the wire can come to saying "the body really was standing there and we did not move it."
**Zero violations across all four runs**, on a checker that reads 0 over the
1,262-capture corpus and goes red with exit 1 on a synthetic stale re-pin. No backward
yank was seen or recorded.

**The waiver refused what it should refuse**, live: T1's first arrival-risk row at 10.46 s
was still `blocked / stale-report` with the waiver ON, because the body had moved.

### §2b THE OUTCOME — the registered REFUTES clause FIRED, and the bar does not move

§2b registered: *"REFUTES — arm T locks (ENSLAVED, or a held-key leg moving ≤ 50 u, or
stops ≪ legs) on a run where a retract fired."* **T2 had a retract fire and a held-key leg
that moved 0 u in 4.0 s. By this sheet's own words that is REFUTED, and it is recorded as
refuted.**

**What the same rows also show, offered as analysis and NOT as a rescue.** T2's parked leg
cannot be the mechanism under test:

- its lead was **ZERO-LENGTH** — armed at 15.71 s with `dest = (10368.68, 8281.62)` against
  a report of `(10368.7, 8281.6)`, i.e. the grant was to the point the body already
  occupied. There was no 520 u arrival to pre-empt, and nothing for a retract to do;
- the guard logged **no `arrival-risk` row at all** in that window, correctly — with zero
  separation nothing was predicted to snap;
- it follows the `gate2-offmesh` AGTRACK RE-PIN that fires at **≈11.9 s in all four runs**,
  arm T and arm C alike, and whose fence shut is pre-existing behaviour this change did
  not introduce.

So the clause caught a **different** defect from the one it was written for. That is a flaw
in my pre-registration, not a finding about the waiver — and the correction belongs in a
new registration, not in a re-reading of this one.

### The persistent lock, which is what §1z-ag identified

Run A's signature is not "a parked leg", it is a fence that never re-arms: **1 reported
stop for 7 key legs, ~7 legs armed instead of ~30, and every subsequent leg parked.**
**C2 reproduces it exactly** (1/7 stops, 7 legs, 5 parked, 773 u, plus 5 leads degraded
`fence-shut` by §1z-aa's gate). **Neither arm-T run produced it** — both ran 7/7 stops and
32–33 legs, and T2's single parked leg recovered on the next leg (1,014 u). n = 2 per arm.

### ★ THE EXPOSURE WAS MUCH THINNER THAN §3 BELIEVED, and §3's floor was the wrong quantity

§3 required "≥ 8 `KBD LEAD` grants" and every run cleared it (25–33). But the census of
`lead_clip_why` shows what those grants actually were:

| run | `clear` (full 520 u) | `clipped` | `origin-unwalkable` (zero-length) | `fence-shut` |
|---|---|---|---|---|
| T1 | **4** | 18 | 10 | 0 |
| C1 | **4** | 11 | 10 | 0 |
| T2 | **2** | 16 | 15 | 0 |
| C2 | **2** | 4 | 1 | 5 |

**Only 2–4 leads per run are long enough to mature at 520 u**; 26 of T1's 32 legs and 27 of
T2's 33 carried a lead of ≤ 1 u once clipped, because on this route the client's reported
position is repeatedly off our navmesh (ROUTER-B3's origin-unwalkable door, working as
designed). **A floor that counts lead grants does not measure the arm under test** — it
should count leads that survive the clip. This is the same defect class as the floor
itself exists to prevent.

### Verdict

**The mechanism is confirmed and safe; the outcome is not confirmed, and this sheet's
REFUTES clause fired.** The waiver does what §1z-ah derived — it converts exactly the
blocked re-pins it was meant to, lands them on a stationary body for 0.0 u, and never
fires at a moved one. What has NOT been shown is that it prevents the lock: arm T avoided
the persistent lock in both runs while arm C hit it once, but with 2–4 maturing leads per
run and n = 2, that is a direction, not a result. **`--kbd-lead` stays OFF; the waiver
stays ON** (it is additive, bounded at 1 u, and refutation would be a violation row, of
which there are none).
