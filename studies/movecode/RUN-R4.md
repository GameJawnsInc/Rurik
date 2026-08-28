# MOVECODE-R4 — the factorial run

**Written 2026-08-28 after R3 ([FINDINGS.md](FINDINGS.md) §1u). Two runs, not one.**

---

## 0. WHAT R3 TAUGHT, and it is a rule about runsheets

`RUN-R3.md` asked for **≥ 30 clicks** and **≥ 8 displacements** while prescribing a
**click-dominated** walk to get the clicks. Those cannot both happen: the click-dominated
regime warps at **3.7% per click**, so 8 displacements needs **~216 clicks**. The operator
did exactly what was asked and the design could not fill its own outcome floor.

> **THE RULE: multiply the exposure floor by the rate the previous run measured, and check
> it clears the outcome floor. Before the run. It costs one division.**

Applied below, out loud, for every floor in §3.

**R3 also left three factors mutually confounded** — corner, distance and keyboard — and
**none of them separable from the run**, because every un-interrupted click in the corpus
is an R3 click and R3's design was **blocked** (all cornered, then all open, then all
interrupted). Blocking is what made phase and factor inseparable. R4 interleaves.

---

## 1. RUN A FIRST — the instrument, 3 minutes, no experiment

**Do this as its own short run and read it back before Run B.** It exists to prove the new
site behaves, and to answer a question that needs no walk at all.

The tick (`0x00600140`) fires **per agent per frame**, strided 1-in-64. Two things to check:

* **The hit count is a frame count.** `hits / (seconds × agents)` should land near the
  client's frame rate. If it does not, the denominator this whole arc now depends on is
  wrong and nothing after it is worth running.
* **`tick`'s return address names the dispatcher** — closing §4 item 2, open since B1. The
  tick is a virtual with 0 direct callers; `AgTimer::Advance` (`0x00603FE0`) is the obvious
  candidate and is **ruled out statically**, so the captured retaddr is the answer.

**Walk:** anything. Stand still for one minute, walk for one, click twice. The tick does
not care, which is the entire point of it.

**Floor:** `tick` hits ≥ 5,000. At 30 fps × 2 agents × 180 s that predicts ~10,800, so the
floor is met with 2× headroom — *and if it is missed, stop*: it means the site is not
firing per frame and Run B is worthless.

---

## 2. RUN B — the 2 × 3 factorial

**Two factors, interleaved, with distance held constant so it cannot proxy for corner.**

| | keyboard: NONE | keyboard: AFTER ARRIVING | keyboard: INTERRUPTING |
|---|---|---|---|
| **CLEAR line** | cell 1 | cell 2 | cell 3 |
| **BLOCKED line** | cell 4 | cell 5 | cell 6 |

* **Distance: every click 1,800–2,200 u.** R3 showed distance outscores corner
  (p = 0.0048 vs 0.0335) and is **71% collinear** with it. Holding it fixed is what makes
  the corner factor mean anything. Judge it by eye — roughly a third of the way across the
  map — the classifier records the true value and the analysis can check the band held.
* **INTERLEAVE. Do not block.** Cycle through the cells rather than doing all of one kind.
  R3's blocked design is why nothing separated from run phase.
* **Keyboard levels are distinct treatments**: *none* means hands off the movement keys for
  that whole click; *after arriving* means the click completes, then you press; *interrupting*
  means you press while the character is still walking.

---

## 3. THE FLOORS, each checked against its own exposure

**Measured per-click warp rates** (§1u.2): keyboard-interrupted **78.6%** [CI 49.2–95.3],
click-only **3.7%** [CI 0.09–19.0].

| quantity | floor | the arithmetic |
|---|---|---|
| clicks per cell | **≥ 20** | 120 clicks total |
| clicks in the 1,800–2,200 u band | **≥ 80%** | the band is the design; if it slips the factorial collapses back into R3 |
| displacements in the **interrupting** row | **≥ 15** | 40 clicks × 78.6% = **31 expected**, floor at half |
| displacements in the **none** row | **0 is the expected result** | 40 × 3.7% = **1.5 expected**. This cell is a CONTROL and its emptiness is the measurement — do not treat a zero here as a failed run |
| `tick` hits | **≥ 15,000** | the denominator for everything above |

**The honest reading of that table:** the *interrupting* row is powered and the *none* row
is not — by design. A 2×2 of interrupting-vs-none across CLEAR/BLOCKED reaches p ≤ 0.05 on
Fisher at roughly 15-vs-2 out of 20 per cell, which the rates above clear comfortably.
**The corner factor is the one at risk**, and it is testable only *within* the interrupting
row, where there are enough events to split.

**Duration:** 120 clicks at ~15 s each is ~30 minutes of walking. **Split it across two or
three captures** rather than one — the ring holds 32,768 records and R3 used 2,709 in
268 s, so a 10-minute capture is safe, and three of them is safer than one long one.

---

## 4. Preconditions

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **144** (floor 96).

```bash
python toolkit/clientscan/movehook/gensites.py --exe vault/client/2026-07-29_221c13772c7a/Gw.exe
```

Expect **15 hook site(s), 12 agent offset(s)**, every row `OK`, including
`tick 0x00600140`. **The DLL is already rebuilt** and newer than `sites.h`.

---

## 5. The commands

Identical to R3 except `--out`. Announce the launch.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --map 280"
```

**Run A** (once in world, standing still):

```bash
python toolkit/clientscan/movehook/attach.py --minutes 3 --out vault/research/movecode/r4a
```

**Run B**, one per capture — change the letter each time:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 10 --out vault/research/movecode/r4b1
```

Stop and read back:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r4a/movehook.bin
```

**Both controls must say FIRED.** `tick` will show `STRIDE 1-in-64: stored is a SAMPLE,
use hits` — that is correct and it is the number Run A is checking.

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r4a/movehook.bin
```

---

## 6. What is being tested, and what refutes it

**R4-P1 — the tick is a frame clock.** `hits / (seconds × agents)` lands within 2× of a
plausible frame rate. **REFUTED IF** it does not, and then Run B does not happen.

**R4-P2 — the tick's retaddr names its dispatcher**, closing §4 item 2. **REFUTED IF** the
return addresses are not a small set, which would mean the tick is dispatched from many
sites and "the caller" is not a well-formed question.

**R4-P3 — the keyboard factor separates.** Displacements in the *interrupting* row exceed
the *none* row, Fisher p ≤ 0.05. **REFUTED IF** they do not — which would kill the last
standing rival and send the arc back to the corner.

**R4-P4 — the corner factor, tested WITHIN the interrupting row** where the events are.
BLOCKED against CLEAR, Fisher p ≤ 0.05. **REFUTED IF** they do not separate, and that
retires the operator's cornered hypothesis on a design that could actually have shown it —
which is the outcome R3 could not deliver.

**Say what warped and when, and watch for clipping.** The operator's report has disagreed
with a metric twice in this arc and been right both times.
