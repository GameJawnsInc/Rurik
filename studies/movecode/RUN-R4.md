# MOVECODE-R4 — the factorial run

**Written 2026-08-28 after R3 ([FINDINGS.md](FINDINGS.md) §1u). Two runs, not one.**
**Run B rewritten 2026-08-28** — the first draft asked for a distance band in world units,
which is not something anyone can judge in-game, and said "interleave the cells" without
saying how. Both are fixed below.

---

## 0. WHAT R3 TAUGHT, and it is a rule about runsheets

`RUN-R3.md` asked for **≥ 30 clicks** and **≥ 8 displacements** while prescribing a
**click-dominated** walk to get the clicks. Those cannot both happen: that regime warps at
**3.7% per click**, so 8 displacements needs **~216 clicks**. The operator did exactly what
was asked and the design could not fill its own outcome floor.

> **THE RULE: multiply the exposure floor by the rate the previous run measured, and check
> it clears the outcome floor. Before the run. It costs one division.**

Applied out loud for every floor in §3.

**R3 also left three factors mutually confounded** — corner, distance and keyboard — and
none separable from the run, because its design was **blocked** (all cornered, then all
open, then all interrupted). R4 interleaves, and it breaks the corner/distance correlation
on purpose.

---

## 1. RUN A FIRST — the instrument, 3 minutes, any walk

Do this as its own short run and read it back **before** Run B. It proves the new site
behaves, and answers a question that needs no experiment.

The tick (`0x00600140`) fires **per agent per frame**, strided 1-in-64.

* **The hit count should be a frame count.** `hits / (seconds × 2 agents)` should land near
  your frame rate. If it does not, the denominator this arc now depends on is wrong.
* **Its return address names the tick's dispatcher** — closing §4 item 2, open since B1.

**Walk:** anything at all. Stand still a minute, walk a minute, click twice.

**Floor:** `tick` hits **≥ 5,000**. At 30 fps × 2 agents × 180 s that predicts ~10,800, so
2× headroom. **If it is missed, stop** — the site is not firing per frame and Run B is
worthless.

---

## 2. RUN B — the cycle

**Eight clicks, repeated ten times.** That is the whole instruction. The eight cover every
combination being tested, and repeating them in order is what "interleaved" means — you are
never doing all of one kind in a row, which is what broke R3.

### The two things you vary

**1. The click destination — CLEAR or BLOCKED.**
*CLEAR* = you can see an unobstructed straight line to it.
*BLOCKED* = something is in the way and the character will have to go around — a building,
a rock, a railing, a doorway.
Judge it by eye. **You do not need to be right**: the capture records both endpoints and
the classifier decides afterwards. It agreed with your eye-labels **23 times out of 24** in
R3, so your judgement is already known to be good.

**2. The keyboard — NONE, AFTER, or INTERRUPT.**
*NONE* = hands off WASD for that whole click, from before you click until the character has
fully stopped.
*AFTER* = let the character arrive and come to a complete stop, **then** hold W for about a
second.
*INTERRUPT* = while the character is **still walking**, hold W for about a second.

### The cycle — do these eight in this order

| # | click at | keyboard |
|---|---|---|
| 1 | **CLEAR** | none |
| 2 | **BLOCKED** | **interrupt** |
| 3 | **BLOCKED** | none |
| 4 | **CLEAR** | **interrupt** |
| 5 | **CLEAR** | after |
| 6 | **BLOCKED** | **interrupt** |
| 7 | **BLOCKED** | after |
| 8 | **CLEAR** | **interrupt** |

Four of the eight are *interrupt* because that is the cell the measurement lives in;
*none* and *after* are two each. Corner is balanced 4 CLEAR / 4 BLOCKED.

### Distance — judged in SECONDS, not units

The first draft asked for 1,800–2,200 world units, which you have no way to measure. Use
walking time instead — the character walks 288 u/s, so:

* **SHORT ≈ 3 seconds of walking** (~1,000 u)
* **LONG ≈ 10 seconds of walking** (~3,000 u)

**Odd-numbered cycles: all eight clicks SHORT. Even-numbered cycles: all eight LONG.**

That is the entire distance rule, and it exists for a specific reason: in R3 corner and
distance were **71% collinear** — you naturally clicked *far* when going around things —
and distance actually outscored corner as a predictor. Alternating whole cycles gives every
condition five short and five long, which breaks the correlation without you having to
think about it per click.

### Tally

Ten cycles of eight = **80 clicks**, about 20 minutes. Tick them off:

```
cycle  1 (short)  [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  2 (long)   [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  3 (short)  [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  4 (long)   [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  5 (short)  [ ][ ][ ][ ][ ][ ][ ][ ]   <-- stop capture 1 here
cycle  6 (long)   [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  7 (short)  [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  8 (long)   [ ][ ][ ][ ][ ][ ][ ][ ]
cycle  9 (short)  [ ][ ][ ][ ][ ][ ][ ][ ]
cycle 10 (long)   [ ][ ][ ][ ][ ][ ][ ][ ]
```

**Two captures of five cycles each**, ~10 minutes apiece. Don't do it as one long capture.

### Rules that apply throughout

* **Let each click finish** (or, for *interrupt*, let it get properly moving first). A click
  abandoned two steps in produces a query and no exposure.
* **One click at a time.** Don't re-click while the character is already walking to a
  destination — that is a different treatment and it is not in this design.
* **Say what warped and roughly when.** Your report has disagreed with a metric twice in
  this arc and been right both times.
* **Watch for clipping** — walking through props, or on ground the body should not reach.
  There is still no instrument but your eyes, and *"I watched and saw none"* is a result.
* If you lose your place in the cycle, just start the next cycle cleanly. A missed click is
  much cheaper than a mislabelled one.

---

## 3. THE FLOORS, each checked against its own exposure

**Measured per-click warp rates** (§1u.2): keyboard-interrupted **78.6%** [CI 49.2–95.3],
click-only **3.7%** [CI 0.09–19.0].

| quantity | floor | the arithmetic |
|---|---|---|
| clicks total | **≥ 64** | 80 planned; 8 cycles' worth is enough |
| *interrupt* clicks | **≥ 32** | 40 planned (4 per cycle × 10) |
| displacements in the *interrupt* row | **≥ 12** | 40 × 78.6% = **31 expected**, floor well under |
| displacements in the *none* row | **0 is the EXPECTED result** | 20 × 3.7% = **0.7 expected**. This is a CONTROL — its emptiness is the measurement, not a failed run |
| `tick` hits | **≥ 15,000** | the denominator for all of the above |

**What is and is not powered, stated plainly.** The keyboard contrast is powered several
times over: 31-vs-1 out of 40-vs-20 is Fisher p < 1e-9, and even a quarter of that clears
0.05. **The corner contrast is the one at risk.** It is testable only *within* the
*interrupt* row, where 20 CLEAR against 20 BLOCKED with ~16 warps each side separates only
if the corner effect is large. **If it comes back null, that is a real answer** — it
retires the cornered hypothesis on a design that could have shown it, which is exactly what
R3 could not deliver.

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
`tick 0x00600140`, and a last line saying `sites.h is already current -- not
rewritten`. **The DLL is already built and stamped against that header.**

> **This step used to break the run it was checking.** `gensites.py` rewrote
> `sites.h` unconditionally, so running it as a precondition bumped the header's
> mtime past the DLL's and armed `attach.py`'s stale-DLL refusal against a DLL that
> was perfectly current — which is exactly what happened on the first R4-A attempt.
> The write is idempotent now, and the staleness check is decided by a **content
> hash** written at build time rather than by timestamps. If you do see the refusal,
> it now means the header genuinely differs and a rebuild is genuinely needed.

---

## 5. The commands

Announce the launch. Shell 1, once for the whole session:

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--click-echo --map 280"
```

**Run A** — shell 2, once you are in the world and standing still:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 3 --out vault/research/movecode/r4a
```

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r4a/movehook.bin
```

**Check Run A before continuing:** both controls FIRED, and `tick` shows a large `hits`
with `STRIDE 1-in-64: stored is a SAMPLE, use hits` beside it. That note is correct — the
hit count is the number being checked.

**Run B, capture 1** — cycles 1–5:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 11 --out vault/research/movecode/r4b1
```

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

**Run B, capture 2** — cycles 6–10:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 11 --out vault/research/movecode/r4b2
```

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

Read both back:

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r4b1/movehook.bin
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r4b2/movehook.bin
```

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r4b1/movehook.bin
```

---

## 6. What is being tested, and what refutes it

**R4-P1 — the tick is a frame clock.** `hits / (seconds × agents)` lands within 2× of a
plausible frame rate. **REFUTED IF** it does not, and Run B does not happen.

**R4-P2 — the tick's retaddr names its dispatcher**, closing §4 item 2. **REFUTED IF** the
return addresses are not a small set, which would mean "the caller" is not a well-formed
question for this function.

**R4-P3 — the keyboard factor separates.** Displacements in the *interrupt* row exceed the
*none* row, Fisher p ≤ 0.05. **REFUTED IF** they do not — which kills the last standing
rival and sends the arc back to the corner.

**R4-P4 — the corner factor, tested WITHIN the interrupt row** where the events are.
BLOCKED against CLEAR, Fisher p ≤ 0.05. **REFUTED IF** they do not separate, which retires
the cornered hypothesis on a design that could have shown it.

**A third outcome that is not a refutation of either:** the floors are missed. Then the run
is re-run, not concluded from — that is R3's whole lesson and it is why §3 does the
arithmetic in public.
