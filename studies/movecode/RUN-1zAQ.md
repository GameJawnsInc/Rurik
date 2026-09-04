# RUN-1zAQ — does the plane clip actually fire live, and does it shut the door?

**Registered before launching.** `MOVECODE-1z-aq`. Four runs, alternating
**B, A, B, A**, one variable between the arms: `--no-lead-plane-clip`.

## 1. What this is powered for, and what it is not

§1z-ap is a desk fix. Every number in it is a re-score of captured leads, and
§1z-af is the standing reminder that a derived backstop can be convicted by its
own verification runs. This run exists to put it in front of a client.

**It is powered for the MECHANISM, not the OUTCOME, and that distinction is the
whole design.** The fix's claim is per-LEAD and deterministic — *a cross-seam ray
is clipped below gate 1 instead of granted at 520 u* — and a run produces tens of
leads. The lock is per-RUN and probabilistic: today's measured rate was **1 in 4**
(§1z-ao), so **n = 2 per arm cannot settle it and this sheet does not pretend
otherwise.** Any lock-count difference here is an anecdote, recorded and not
argued from.

## 2. THE PREDICTION

| | expected |
|---|---|
| **P1 — EXPOSURE** | each **arm A** run produces **≥ 1** grant row with `lead_clip_why == "plane-seam"`. Without one the route never met the seam and the run tests nothing. |
| **P2 — THE FIX** | in **arm A**, **no** lead is granted at a reach ≥ **299.33 u** (gate 1) from an origin whose plane differs from the plane under its granted point. Zero, not "fewer". |
| **P3 — THE CONTROL** | in **arm B** (`--no-lead-plane-clip`) exactly such leads **do** go out, at full 520 u, reading `clear`. The known-bad arm must reproduce the defect or the comparison is empty. |
| **P4 — the outcome, WEAK** | arm A locks no more often than arm B. **n = 2 per arm; this cannot be decisive** and is recorded as an anecdote. |

**REFUTED IF:**

- **P2 fails — a cross-seam lead still goes out at full length in arm A.** The fix
  does not do what the desk said. This is the strong refutation and the whole
  reason to run it.
- **P3 fails — arm B produces none either.** Then the route did not exercise the
  seam at all and P1/P2's greens are vacuous; the run measured nothing.
- **arm A locks on a `plane-seam`-clipped leg.** Then clipping below gate 1 is not
  sufficient and §1z-ap's mechanism is incomplete, whatever the counts say.

**A lock in arm A on a leg with NO seam is not a refutation** — §1z-ap.3 already
says one locked run (`073055`) had no lead armed on its silent leg at all, so a
second armer exists and this fix never claimed to close it.

## 3. EXPOSURE FLOOR and ABORT

- **≥ 1 `plane-seam` row per arm-A run** (P1). Zero means zero exposure, and the
  run is re-routed, not written up.
- **≥ 1 cross-seam full-length lead per arm-B run** (P3), for the same reason from
  the other side.
- Every tape: Hatcher control `shut` on 100%, player fence non-`unread:` — **ABORT**
  on a control failure, per §1z-an.3.
- Every capture must reach the map.

## 4. The runs

**Announced before launching — the machine is shared and `Gw.exe` takes focus.**

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress; the script opens with `wait:3` and the character
> stands still deliberately. **Each run ends on its own — ~75 s from launch to the
> window closing — and nothing is left parked.** Four in sequence.

**Terminal A, per run:**

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

**ARM B (runs 1, 3) — the KNOWN-BAD arm, the pre-§1z-ap plane-blind ray:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --no-repin-stationary-waiver --no-lead-plane-clip"
```

**ARM A (runs 2, 4) — the shipped fix:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --no-repin-stationary-waiver"
```

RUN-1zAO's command verbatim; `--no-lead-plane-clip` is the only difference.
`--no-repin-stationary-waiver` is held ON in **both** arms — it is not under test
here, and keeping it constant keeps the lock exposure high while leaving one
variable between the arms (§29's rule).

## 5. Scoring

Per capture, the leads are scored from the `grant_verdict` and `kbd_leg` rows
against the map-146 mesh: reach, the origin's plane, the plane under the granted
point, and `lead_clip_why`. Then `stopcensus.py` for the lock column and
`agenttap`'s fence block for the control.

**What it cannot settle.** One map, one route, one build, and the seam it meets is
the plane-29 structure this route happens to cross. A green P2 says the door is
shut on THIS seam, not that no plane-blind grant survives anywhere — the ROUTER's
own clip is still plane-blind by design (§1z-ap.6) and is not under test.

---

## RESULT — RAN 2026-09-04. **All three powered predictions PASS.**

| run | arm | leads | `plane-seam` | cross-seam >= gate 1 | lock |
|---|---|---|---|---|---|
| `20260904T115542` | B (off) | 32 | 0 | **3** | no |
| `20260904T115725` | A (on) | 31 | **1** | **0** | no |
| `20260904T115909` | B (off) | 30 | 0 | **1** | no |
| `20260904T120055` | A (on) | 34 | **2** | **0** | no |
| | **A** | **65** | **3** | **0** | 0/2 |
| | **B** | **62** | 0 | **4** | 0/2 |

**P1 EXPOSURE PASS** (both arm-A runs met the seam). **P2 THE FIX PASS** — zero of
65 arm-A leads reach gate 1 across a plane change. **P3 CONTROL PASS** — the
known-bad arm produced 4, every one at the full 520 u reading `why="clear"`, two
running plane 29 -> 0 and two plane 0 -> 29, so the term catches both directions.
All four tapes valid: Hatcher control `shut` on 100%, zero `unread:`; no abort.

**Healthy grants unperturbed, live:** arm A's max reach is still 520 u and only 3
of 65 leads were clipped -- sec.1z-ap.4's 7.8% desk figure holding in front of a
client.

**P4: no lock in EITHER arm (0/2, 0/2), so this run set carries NO evidence about
the outcome** -- registered as weak before launching, since at the measured 1-in-4
rate two runs expect 0.5 locks in arm B. "Arm A did not lock" must not be read as
the fix working; arm B did not lock either.

Full write-up: FINDINGS sec.1z-aq.
