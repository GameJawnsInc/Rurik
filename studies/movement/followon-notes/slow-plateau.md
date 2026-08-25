# The slow-plateau "rate regime" (§8.3c residual) — MEASURED AND CLOSED AS A RATE QUESTION

Recon note. Static analysis + existing vault captures only. No client, harness or
`session.py` was launched. Nothing outside this directory was modified.

Every claim below is tagged **OBSERVED** (I measured it here), **SOURCED** (a doc
or the pinned binary says it and I checked the citation resolves), or
**UNVERIFIED** (I am reasoning, or I could not measure it).

---

## 0. VERDICT

**The slow plateaus are REAL MOTION but they are NOT A SPEED REGIME. They are
CONSTRAINED motion — the body pinned against map collision geometry and sliding
along it. There is no missing row in the reckon's rate table, because the thing
the reckon gets wrong during a plateau is the DIRECTION, not the rate.**

Three findings, in order of how much they change what is on file:

1. **The client never reports a sub-cruise speed anywhere.** Across 42,784
   movetap samples the client's own `maxspeed` (`+0x5C`) is `288.0` and its
   `movespeed` multiplier (`+0x60`) is `1.0`, with *zero* other values; the
   cached velocity `+0xB0/+0xB4` has magnitude `288.0` in **all 13,767** moving
   samples and `0` otherwise. **The client's locomotion rate is bang-bang: 288
   or nothing.** (§2)
2. **Every plateau I could geometrically test lies on a straight line to within
   ~0.002 world units, for seconds at a time, at round map coordinates** —
   `x = 0`, `x = 1248`, `x = 3072`, `y = 0`, `y = 1728`, `x − y = 9792`,
   `x + 5y = 17184` — reproduced across separate sessions days apart at the same
   places. That is a wall, not a walking speed. (§4)
3. **The slide obeys a two-part law:** `speed = max(288·cos(incidence), FLOOR)`
   with `FLOOR = 94.0 u/s` measured, `= 0.3307 [0.3290, 0.3320]` of same-instrument
   cruise. The projection half is ordinary collide-and-slide. The **floor** is the
   genuinely new constant and its mechanism is UNVERIFIED. (§5)

And the correction the brief asked me to make explicitly:

> **DOC CLAIM CONTRADICTED.** `studies/movement/FINDINGS.md:1209-1211` — "sustained
> plateaus at ½ and ⅓ of each type's own cruise, 27% of forward moving time".
> The **27%** reproduces (I measure 22.3% below 0.85×cruise on my slicing, 25.6%
> on a looser one — same phenomenon). **The "½" plateau does not exist**: there is
> no 144 u/s cluster in the corpus at all (§3, histogram). The "⅓" plateau exists
> but sits at **0.331 of cruise, not 0.333**, and it is *not a cruise fraction at
> all* — it is a collision floor. My reading of how the "½ and ⅓" phrasing arose
> is UNVERIFIED but cheap: **93.8 u/s is simultaneously ~⅓ of the forward cruise
> (288) and ~½ of the backward cruise (187.8)**, so one constant read under two
> family baselines produces exactly that sentence.

**Risk to the shipped `--cast-stop=pin`: REAL, PRICED, and NOT the shape the
§8.3c signature predicts.** A pin fired during a slide misses by
`~294 u/s × gap` unclipped (not `(288−94)=194 u/s`, because the error is a vector
difference at ~84°), which breaches the 32 u and 35 u bars at any gap above
~0.11 s. Clipped perfectly against our navmesh it degrades to `93.8 u/s × gap`,
breaching at 0.34 s. **However: 0 of 80 casts in the whole corpus landed in a
slide**, so this is an unexercised door, not an observed defect. (§6)

---

## 1. WHAT I MEASURED, AND THE POSITIVE CONTROLS

**Corpus.** OBSERVED.
- `C:\gd\Rurik\vault\captures\movetap\*.jsonl` — 32 files, 42,784 `kind:"sample"`
  rows (13,767 with a non-zero cached velocity).
- `C:\gd\Rurik\vault\captures\gamesrv\*.jsonl`, origin `"ours"` only — 55 files
  carry c2s movement reports; 4,905 consecutive-report intervals, of which 3,751
  are heading→heading. Forward `{1,2,3}` heading→heading time = **1,352.7 s**.
- Every gamesrv capture that contains a plateau is `map_id = 148`. **Scope caveat:
  the wall inventory in §4 is one map's geometry.** The *law* in §5 is client
  behaviour, but I only exercised it on map 148.
- I did **not** pool `ours` and `live`. The live corpus (`vault/captures/live/`)
  is off-wire ciphertext with no decoded rows (`kind` ∈ {wire, frame, origin,
  session_key, …}); decoding it needs `replay.py` over 21 sessions, which I did
  not do. **The live control is therefore NOT RUN** — see §7.

**Positive controls, because three of my claims are negative.**
- *"`movespeed` is never anything but 1.0"* — control 1: the same reader shows
  `|vel|` flipping 0↔288 thousands of times in the same rows, so the reader is
  live, not logging a frozen snapshot. Control 2, from the binary:
  `codescan.py --field 0x60 --in AgAgent` returns **8 instructions, 2 stores**
  (`0x0060243E`, `0x00602A30` — both `fstp dword ptr [esi+0x60]`) and 6 reads.
  The field is writable and written; this corpus simply never exercised it.
  SOURCED + OBSERVED.
- *"there is no 144 u/s plateau"* — control: the identical detector, on the
  identical data, finds the 93.8 cluster at n=143 and 34 forward plateau runs.
  It can find plateaus; there is no 144 one to find.
- *"no cast landed in a slide"* — control: the same scan finds 80 casts, 68 with
  a prior report, 20 preceded by a `0x003D`, and 12 of those 20 whose bracketing interval was
  slow. It is finding casts; slides are absent from that set.

**Scripts** (scratch, deliberately NOT in the repo):
`%TEMP%\claude\C--gd-JawnRPG\<session>\scratchpad\{mt_survey,census,deep,plateaus,pooled,geom,castgap,pinmiss,dump}.py`.

---

## 2. THE DECISIVE CHECK (brief item 2e): the client's own speed fields

**OBSERVED.** Offsets SOURCED from `toolkit/clientscan/movetap.py:461-466`
(`A_MAXSPEED = 0x5C  # float, units/second`, `A_MOVESPEED = 0x60  # float
multiplier, AGENT_MAX_MOVE_SPEED = 1.0`, `A_VEL = 0xB0  # vx f, vy f,
units/second`).

| field | distinct values over 42,784 samples | count |
|---|---|---|
| `maxspeed` `+0x5C` | `288.0` — one value | 42,784 |
| `movespeed` `+0x60` | `1.0` — one value | 42,784 |
| `|vel|` `+0xB0/+0xB4` (moving rows) | `288.0` — **one** bin at 0.1 u/s resolution | 13,767 |

There is no intermediate value. Not one sample at 144, at 96, at 190.1, at any
ramp value.

**Three candidates die on this table.**
- **(2b) a speed effect / cripple / snare: cannot be the cause here.** The
  multiplier a snare would ride is constant 1.0 for the whole corpus.
  `--move-speed-effects` in `authsrv.py:16967` is `store_true` (opt-in, off by
  default) and the captures do not record the flag set — but the *client-side*
  read settles it regardless of server intent. NOTE the residual honesty: this
  refutes the effect hypothesis **for this corpus**, it does not establish what
  a real snare would look like; that is untested.
- **(2c) acceleration/deceleration ramps: not in the velocity model.** `|vel|` is
  bang-bang 0↔288 with no intermediate value, so nothing ramps in the field the
  client dead-reckons from. Independently, my plateau detector requires ≥3
  consecutive intervals and ≥1.5 s within ±10% before it will call something a
  plateau, so transients cannot enter the population by construction. **Sustain
  threshold justified:** the report cadence during a plateau is the ~0.5 s
  heartbeat, so ≥3 intervals is the smallest window in which "constant" is
  distinguishable from "two points and a line", and 1.5 s is ≥ 4× the 0.35 s
  `RESYNC_MAX_REPORT_AGE` scale the rest of the arc uses for "fresh".
- **(2a) an under-sampled movementType: dead.** During every plateau I examined
  the reported `mt` is **1** — plain forward. See §3. The plateaus are not a
  family the census missed; they happen *inside* family `{1,2,3}`.

**A caution on `live`/`+0x78` that matters for anyone re-running this.** movetap's
`point` (`+0x78`) advances only at event sites, so differentiating it gives
"flat, then a step" (movetap.py's own header says so, lines 38-46), and its
reconstructed `live` = `point + vel·dt` will by construction report exactly 288
u/s. **During a slide that reconstruction is wrong**: I verified on the 50 Hz tap
(`movetap-20260821T124010.jsonl`, wall 1787330429-1787330436) that `|vel|` reads
288 with a direction that re-aims every ~0.4 s while the position genuinely
advances at ~114 u/s along a wall. Anyone scoring a cast against movetap `live`
inside a slide is scoring against a fiction.

---

## 3. WHAT THE "27%" ACTUALLY IS

**OBSERVED**, forward `{1,2,3}` heading→heading intervals, chord ÷ wall-clock dt,
n = 2,362, total 1,352.7 s:

| bucket | time | share of the slow band |
|---|---|---|
| all forward moving time | 1,352.7 s | — |
| **slow band** (`< 0.85 × 288 = 244.8 u/s`) | **302.2 s** | **22.3% of forward time** |
| ⤷ heading TURNED > 20° inside the interval | 115.0 s | 38.1% |
| ⤷ heading steady, travel > 20° off it (constrained) | 141.8 s | 46.9% |
| ⤷ heading steady AND travel on-heading (a real rate candidate) | 45.4 s | **15.0%** |

- The **38.1%** is brief item **(2d)** — the sampling artifact — and it is real
  and large. A chord across a heading change is shorter than the arc; the
  low-speed tail is dominated by it (in the 0-40 u/s band, turn p90 = 180.0°,
  i.e. the player reversed inside the interval and the chord went to ~0).
  **OBSERVED and confirmed as a contributor.**
- The **46.9%** is the slide. **86% of that time** (121.4 of 141.8 s, 247 of 268
  intervals) is fit within 15% by `max(288·cos(dev), 94.0)` — §5.
- The **15.0%** left is the only bucket that could be a locomotion rate, and it
  is **45.4 s = 3.4% of forward moving time** spread over 35 intervals, nine of
  which are dt = 0.03 s (single-frame noise). Its speed histogram is a smear
  from 0 to 244 with **no cluster anywhere**. There is no plateau left in it.

**The 144 u/s question, settled.** Forward intervals at the 0.5 s cadence,
6 u/s bins:

```
  90- 95  n=144  20.9%   <-- the floor
 114-119  n= 15   2.2%
 144-149  n=  1   0.1%   <-- "half cruise"
 210-215  n= 20   2.9%
 276-287  n=375  54.5%   <-- cruise
```

**There is no half-cruise plateau.** OBSERVED.

---

## 4. THE PLATEAUS ARE WALLS — the geometry

**OBSERVED.** 38 sustained plateau runs (≥3 intervals, ≥1.5 s, all speeds within
±10% of the run mean, mean below 0.85 × family cruise), 116.4 s total. For each I
fit a total-least-squares line through every reported endpoint and took the
**maximum perpendicular residual**:

| capture (date-time) | n | dur (s) | mean speed | dev₅₀ | fitted line | max residual (u) |
|---|---|---|---|---|---|---|
| 20260821T1709 | 16 | 8.04 | 93.8 | 89.7° | `x = 0.00` | **0.0000** |
| 20260821T2120 | 10 | 5.01 | 93.7 | 78.2° | `x + 5y = 17184.0` | **0.0011** |
| 20260821T2008 | 10 | 5.00 | 93.7 | 78.2° | `x + 5y = 16608.4` | **0.0009** |
| 20260821T1239 | 9 | 4.50 | 114.6 | 66.8° | `−0.677x + 0.736y = −1403.30` | **0.0017** |
| 20260823T1836 | 7 | 3.53 | 93.9 | 74.0° | `−0.99968x + 0.02525y = −10996.00` | **0.0018** |
| 20260821T1325 | 6 | 3.03 | 75.3 (bwd) | 66.9° | `−0.887x + 0.463y = −9688.68` | **0.0011** |
| 20260821T1319 | 5 | 2.52 | 93.7 | 84.4° | `y − x = −9792.0` | **0.0006** |
| 20260821T1325 | 5 | 2.52 | 93.8 | 84.4° | `y − x = −9792.0` | **0.0005** |
| 20260821T1434 | 5 | 2.50 | 93.7 | 84.4° | `y − x = −9792.0` | **0.0005** |
| 20260821T2008 | 5 | 2.50 | 93.8 | 89.8° | `y = 0.00` | **0.0000** |
| 20260821T2012 | 5 | 2.50 | 93.8 | 89.8° | `y = 0.00` | **0.0000** |
| 20260821T1712 | 5 | 2.50 | 93.9 | 89.7° | `x = −1248.00` | **0.0000** |
| 20260821T2325 | 3 | 1.50 | 94.0 | 90.0° | `x = −3072.00` | **0.0000** |
| 20260821T2119 | 4 | 2.00 | 94.0 | 78.2° | `x + 5y = 17184.0` | **0.0004** |

A human holding a key cannot produce a track that is straight to a **thousandth
of a world unit for eight seconds**. These are constraint surfaces. Note that
three separate captures — 20260821T1319, T1325, T1434, minutes to hours apart —
land on the **same** diagonal `x − y = 9792.0`, and two more sessions land on the
same `x + 5y = 17184.0` (a clean 1:5 slope). `9792 = 34 × 288`,
`1728 = 6 × 288`, `3072`, `1248`, `0` — map-authoring numbers.

**The wire itself shows the pin.** Raw dump, `authsrv-20260821T201224-c1.jsonl`
(OBSERVED, `dump.py`):

```
 11.777 HEAD mt=1 pos=( 1545.90,    0.00) hdg= -89.8deg | dt=1.853 chord= 508.2 sp= 274.3
 12.278 HEAD mt=1 pos=( 1593.42,    0.00) hdg= -89.8deg | dt=0.501 chord=  47.5 sp=  94.9 dir=0.0
 12.778 HEAD mt=1 pos=( 1639.70,    0.00) hdg= -89.8deg | dt=0.500 chord=  46.3 sp=  92.5 dir=0.0
 13.278 HEAD mt=1 pos=( 1686.94,    0.00) hdg= -89.8deg | dt=0.500 chord=  47.2 sp=  94.4 dir=0.0
 13.779 HEAD mt=1 pos=( 1734.46,    0.00) hdg= -89.8deg | dt=0.501 chord=  47.5 sp=  94.8 dir=0.0
```

The player runs south at cruise, reaches `y = 0.0000`, and from there the heading
never changes (still −89.8°, straight into the wall) while the body tracks
**east**, 90° off it, at 94 u/s. `mt` stays **1** the whole way. Report cadence
switches from the ~512 u chord (1.85 s) to the 0.5 s heartbeat, because 47 u per
report never reaches the chord trigger.

---

## 5. THE LAW: `speed = max(288·cos(incidence), 94.0)`

**OBSERVED.** Forward `{1,2,3}`, 0.5 s cadence intervals, binned by the angle
between the reported heading and the travelled chord (`dev`):

| dev bin | n | mean speed | sd | `288·cos(dev)` | ratio |
|---|---|---|---|---|---|
| 0–5° | 84 | 277.8 | 37.3 | 287.9 | 0.97 |
| 10–15° | 257 | 280.6 | 9.7 | 281.4 | 1.00 |
| 30–35° | 17 | 229.8 | 29.3 | 244.1 | 0.94 |
| 40–45° | 39 | 210.4 | 4.6 | 210.9 | **1.00** |
| 65–70° | 18 | 115.3 | 3.4 | 113.4 | **1.02** |
| 70–75° | 18 | 90.5 | 13.1 | 84.9 | 1.07 |
| 75–80° | 34 | **93.9** | **0.94** | 61.0 | 1.54 |
| 80–85° | 31 | **93.8** | **0.98** | 29.0 | 3.23 |
| 85–90° | 52 | **93.8** | **0.93** | 1.9 | 48.4 |
| 90–95° | 8 | **93.8** | **0.86** | 0.0 | ∞ |

Up to ~70° the body moves at **exactly the projection of cruise onto the wall**
(pooled `measured / (288·cos dev)` over 20°<dev<78°, n=126: **0.967 ± 0.045**,
95% CI). Past ~71° it stops falling and **pins at 93.8 u/s regardless of
incidence**: within the floor population, `dev < 80°` gives 93.77 and
`dev ≥ 85°` gives 93.80 — **a 0.04 u/s difference across a 10× change in the
projection**. It is a floor, not a projection.

**Floor estimates, with error bars.** OBSERVED.
- Pooled floor intervals (fwd, dt ≈ 0.5 s, dev > 78°, 60 < sp < 130):
  **n = 115, median 93.95 u/s, bootstrap 95% CI [93.50, 94.25]**, IQR
  92.91–94.64. Total floor time **57.7 s across 13 captures on 2 separate dates**.
- Tighter cluster cut (85–102 u/s, dev > 60°): n = 143, **mean 93.784, sd 0.954,
  sem 0.080, 95% CI [93.63, 93.94]**; chord per report **47.070 ± 0.098 u** at
  dt = 0.5019 ± 0.0042 s.
- Grid-search best fit of `max(288·cos dev, F)` over all 688 forward 0.5 s
  intervals: **F = 94.0 u/s**, mean absolute error 20.1 u/s (that MAE is carried
  by the turn-artifact intervals the model does not claim to cover; the model's
  own residual is p50 **−0.7 u/s**, p10 −7.2, p90 +2.7).

**As a fraction of cruise, same instrument (this cancels the 2D-chord bias):**
- cruise = long straight legs only (dt > 1.5 s, dev < 2°), n = 307,
  **median 284.08, bootstrap 95% CI [283.93, 284.21]**
- **FLOOR / CRUISE = 0.3307, 95% envelope [0.3290, 0.3320]**
- `1/3 = 0.3333` sits **just outside** that envelope, by 0.0013–0.0043.

**Honest reading:** I cannot call the floor exactly ⅓ — the interval excludes it.
I also cannot exclude ⅓, because the 2D-chord bias between a possibly-sloped
cruise leg and a flat wall slide is of the same order (~1%: FINDINGS.md:1214
records the 284.96-vs-288 contest for exactly this reason). **Report it as
0.331 ± 0.002 of cruise, ≈ 94 u/s absolute, and do not build ⅓ into anything.**

**Mechanism of the floor: UNVERIFIED.** I did not find it in the binary and I did
not look hard — `codescan.py` anchors on displacements and cross-references, not
on float constants, so a hard-coded `94.0f` or `0.3256f` is not a thing it can
search for. The two shapes I can distinguish already:
- It is **not geometry-derived**: the same 93.8 appears on an axis-aligned wall
  (`y=0`), on a 45° diagonal (`x−y=9792`) and on a 1:5 slope (`x+5y=17184`).
- It is **not incidence-derived**: flat across dev 78°–95°.
So it behaves like a scalar constant of the client's blocked-movement path.
**Named next measurement** (bounded, static): disassemble the movement tick
`0x00600140` and the collide/slide callee reached from it, and look for a `fmul`
against an `.rdata` float in `[93.0, 96.5]` or a ratio in `[0.324, 0.336]`.
`--xrefs` on the constant's address once found gives the writer set.

**Backward and side families: NOT ESTABLISHED.** Backward has only 79 intervals
at the 0.5 s cadence and side has 14 — too thin to fit a floor. The one backward
plateau that does fit the projection law cleanly is
20260821T1325 (75.3 u/s at incidence 66.9°, `187.8·cos(66.9°) = 73.6`, ratio
1.02). **I could not determine whether the backward family has its own floor.**

---

## 6. PRICING THE RISK TO THE SHIPPED `--cast-stop=pin`

**The reckon** (SOURCED, `toolkit/authsrv/authsrv.py:1899-1909`) is
`est = pos + ĥ · rate·288 · dt`, with `rate` 1.0 for mt {1,2,3}. **There is no
freshness gate on `dt`** — I read the whole of `cast_stop_reckon` (`:1813-1948`)
and the doors are `click-walk / no-report / report-refused / pinned-parked /
parked / no-heading / degenerate-heading / future-report`, then
`no-mesh / off-mesh / no-plane`. None of them is "the report is too old", and
none of them can see a slide.

During a slide the reckon's preconditions are all *satisfied*: `kbd_moving_at` is
armed (0x003D heartbeats every 0.5 s), `client_pos` is ≤0.5 s old, `heading` is
non-degenerate, `mt` = 1. **It will reckon, and it will reckon forward along a
heading the body is not following.**

**The error is a vector difference, not a rate difference. This is the part the
§8.3c "forward-miss" signature would get wrong.** §8.3c says to price a rate miss
as `(family rate − measured speed) × gap`, which here would read
`(288 − 93.8) = 194.2 u/s`. The true magnitude is

```
|288·ĥ − 93.8·t̂|  with  angle(ĥ, t̂) = 84.4°   =   294.1 u/s
```

— 51% larger, and **pointing sideways**, so the §8.3c "backward ≤ 20 u" bar and
the "forward miss" bar are both the wrong instrument for it.

| cast gap | unclipped pin error | if `pm.clip` stops the ray dead at the wall |
|---|---|---|
| 0.10 s | 29.4 u | 9.4 u |
| 0.25 s | 73.5 u | 23.4 u |
| 0.35 s | 102.9 u | 32.8 u |
| 0.50 s | 147.0 u | 46.9 u |

Against the registered bars (`0x002C`-vs-body ≤ 32 u, across-halt ≤ 35 u,
backward ≤ 20 u):

- **unclipped:** breaches 32 u at gap > **0.109 s**, 35 u at > **0.119 s**.
- **perfectly clipped:** breaches 32 u at gap > **0.341 s**, 35 u at > **0.373 s**.

**Measured cast-gap distribution** (OBSERVED, 68 casts with a prior report in the
`ours` corpus): p10 0.245, p25 0.385, **p50 0.834**, p75 2.011, p90 8.398 s.
**98.5%** of measured gaps exceed the unclipped breach threshold; **79.4%**
exceed the perfectly-clipped one. So *if* a cast lands in a slide, a breach is
near-certain on either clipping assumption.

**But it has never happened.** OBSERVED: **0 of 80** casts in the corpus fall in
a slide interval; 12 of the 20 casts whose prior report was a `0x003D` fall in *some* slow forward interval. Slide time is
57.7 s out of 1,352.7 s of forward motion (4.3%), and casting while running face
first into a wall is evidently not something the operator does.

**Two things I could not determine and will not guess.**
1. **Whether `pm.clip` actually stops the ray.** That needs our trapezoid mesh
   for map 148 evaluated at those points; building it is a `pathmap` construction
   I judged out of scope for a recon pass. The two rows above bracket the answer.
2. **Whether `pm.walkable(pos)` even admits the point.** The body sits *exactly*
   on the constraint line (`y = 0.0000`, residual < 0.002 u), which is the worst
   possible input for an on-mesh test. If it refuses, the whole cast-stop
   suppresses (pin-or-nothing, F34) and the correct outcome is F28's glide, not a
   warp. **That is the good case and it is plausible — but it is unmeasured.**

**One adjacent observation, flagged as thin (n=1) and NOT part of the verdict.**
Reconstructing what the reckon *would* have produced at each corpus cast that had
a `0x003D` before it, a report after it and no `0x002C` in the window (n = 11,
`pinmiss.py`), the four cruise cases miss by p50 5.6 u — but the one that was
**turning** (sp 281 u/s, dev 25.2°, gap 0.435 s) misses by **54.1 u**, over both
bars, from *heading staleness alone at full cruise*. n=1 proves nothing; I record
it because if it replicates it is a bigger and far more common exposure than the
slide, and it is the same class of defect: **the reckon's weak axis is direction,
not rate.**

---

## 7. WHAT I COULD NOT MEASURE

Stated plainly rather than padded.

- **The floor's mechanism.** UNVERIFIED. §5 gives the bounded next probe.
- **The `live` control.** NOT RUN. The retail corpus is ciphertext with no
  decoded rows; separating "the 94 u/s floor is a client constant" from "our
  server induces it" needs `replay.py` over `vault/captures/live/*/game-*.jsonl`.
  *Partial substitute, OBSERVED:* the floor reproduces across 13 of our captures
  on two dates with different server arms, and the wire is silent through it —
  the client slides on its own with nothing arriving. That makes an
  our-server cause unlikely but does not close it.
- **Backward/side floors.** Exposure too thin (n = 79 and 14).
- **Whether our navmesh clips the slide ray** (see §6).
- **Whether a real snare would show on `+0x60`.** The field is writable
  (2 stores, SOURCED) but nothing in this corpus wrote it.
- **Anything off map 148.** All plateau captures are map 148.

---

## 8. THE UNTESTED RECKON BAND (277–524 u) — a run recipe

**Where the bound comes from.** SOURCED, `CANCELWALK.md:2580-2584`: the reckon is
tested to 277 u (residual −0.1 u) plus 67.2 u clean, and bounded ≈524 u by the
~512 u `0x003D` chord (that run's `sep` max 524.45 u). Extrapolation distance is
`rate·288·dt`, so **the band 277–524 u is exactly a cast whose gap since the last
accepted report is 0.96 s – 1.82 s at forward cruise.**

**Is that reachable? OBSERVED, yes, and often.** Over 743 straight-cruise
intervals (dev < 5°, turn < 5°, sp > 265 u/s): the dt distribution is bimodal —
**38.2% at dt = 1.8 s** (the chord) and a burst mode at 0.0–0.1 s (36.7%, micro
direction corrections). **39.9% of straight-cruise TIME sits in the 0.96–1.82 s
post-report window.** A cast dropped blind during a straight leg lands in the
band ~2 times in 5.

**Recipe (an owner can execute this without a stopwatch).**

1. Stand still, **in the open interior of the map, ≥300 u from any wall.**
   *(This is my finding's rider: a wall slide puts the body 90° off its heading
   and would be mis-scored as a band failure. Do not run this along a wall.)*
2. Start both instruments; note the wall clock on each (the arc's alignment rule).
3. Press and **hold W only** — no A, no D, no mouse steering. A constant heading
   is what suppresses the burst-mode reports; the observed cadence on a held
   straight leg is a clean 1.80–1.85 s (measured: 1.803 / 1.818 / 1.802 / 1.853 s).
   The walk start itself emits a `0x003D`, so the clock starts at the press.
4. **Count "one-one-thousand, two-one-thousand" and press a NON-ATTACK skill on
   "two"** — i.e. ~1.3–1.8 s after the press. That is `dt` ≈ 1.3–1.8 s →
   extrapolation **374–518 u**, inside the band with margin at both ends.
5. Release, walk back, **repeat 6×**, deliberately varying the count between
   "on two" and "just after two". Overshooting past 1.82 s is safe — a fresh
   chord report lands and the rep is merely wasted, not misleading. Undershooting
   below 0.96 s repeats the already-tested regime.
6. One rep must be a cast the operator then **cancels**, to keep the cancel path
   exposed; otherwise the §8.3c exposure floor applies unchanged.

**Cost: ≤5 minutes of owner time** (6 reps × ~8 s of motion, plus tap start/stop
and the walk-backs).

**Scoring bar — the §8.3c bars stand unchanged, plus two additions:**
- `0x002C`-labelled point within **32 u** of the movetap body position at the send;
- total across-halt displacement **≤ 35 u**; backward component **≤ 20 u**;
  `sep` ≈ 0 through the cast; at rest within ~0.15 s.
- **NEW (band accounting):** for every cast, record `dt` = (cast time − last
  accepted report time) and the extrapolation `rate·288·dt` from the console
  line. **The run is VOID for this question unless ≥3 casts land with the
  extrapolation in [277, 524] u** — the same "exposure floor or the arm is VOID"
  discipline §8.3c applies to in-motion casts.
- **NEW (my §5 rider):** record the angle between the reported heading and the
  movetap-derived travel direction at each cast. If it exceeds ~20°, the cast was
  turning or sliding and its miss must be scored against §5's law, **not** against
  the band. A miss at a large heading deviation says nothing about extrapolation
  distance.

**Predicted result, registered before the run (UNVERIFIED, this is a prediction):**
the misses stay ≤ 32 u and scale with the *heading* deviation, not with the
extrapolation distance — because §5 says the rate model is exact at 288 whenever
the body is unconstrained and on-heading. **REFUTED IF** a clean straight-leg cast
at 400–500 u extrapolation misses > 35 u *forward along its own heading*: that
would name a rate error the 288 constant does not cover, which is the one thing
this whole note says does not exist.

---

## 9. WHAT TO CHANGE ON FILE

1. `studies/movement/FINDINGS.md:1209-1211` — strike "sustained plateaus at ½ and
   ⅓ of each type's own cruise". Replace with the collide-and-slide law and the
   94.0 u/s floor. The "27% of forward moving time" figure survives; its
   *attribution* does not.
2. `CANCELWALK.md:2245-2257` (§8.3c's forward-miss signature, cause (1)
   "rate-regime error") — the arithmetic is wrong for this regime. It prices the
   miss as `(family rate − measured speed) × gap` = 194 u/s; the true magnitude
   is the vector difference, 294 u/s, and it points sideways. Amend to: *if the
   body's travel direction at the cast is more than ~20° off the reported
   heading, price the miss as `|rate·288·ĥ − v_measured| × gap` and score it
   against §5's law, not against the rate table.*
3. `CANCELWALK.md:2600` residual list — "the slow-plateau rate regime (bounded,
   §8.3c)" should now read as **closed as a rate question** and **re-opened as a
   direction question**: the residual is the reckon's blindness to constrained
   motion, exposure 4.3% of forward moving time, **0 of 80 corpus casts**, and it
   is unmeasured whether the navmesh doors catch it.
4. `cast_stop_reckon` — **no code change is recommended from this note.** A
   "refuse when the last two reports disagree with the heading by > 20°" door is
   the obvious candidate, but it needs the §8 run and the `pm.walkable` question
   answered first, and adding a door on an unexercised path is how this arc got
   its guard that went 0-for-72.

---

**COMPLETE.** Measurements re-runnable from the scratch scripts named in §1.
