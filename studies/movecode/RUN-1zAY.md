# RUN-1zAY — does the READ-CAMERA projection predict where a click lands?

**Registered before launching.** `MOVECODE-1z-ay`. One run. **No aiming is
required and none is attempted**, which is the whole point of the design.

## 1. The design, and why it needs no aim

§1z-ax built the projection on the camera `fovread.py` reads. It is exact
arithmetic *given* the camera, and has never faced a client.

**The validation does not need to aim at anything.** Click at arbitrary
fractions, log the camera on the same clock, and then ask whether the projection
**predicts where each click landed** — the client's own `MOVE_TO_COORD` is the
answer key. Aiming is the *inverse* of a projection that predicts; there is no
point attempting it before the forward direction is shown to work.

**And the ground height is MEASURED, not assumed.** The agent block carries
`(x, y)` only and the pathing file has no height, so `to_ground` has no `z` to
be handed. Instead each click *measures* one: the ray is known, the landing
`(x, y)` is known, so the parameter along the ray that reaches it implies a
ground `z`. That turns the missing term into an observable and splits the test
in two.

## 2. THE PREDICTION

| | expected |
|---|---|
| **P1 — BEARING** | each click's landing lies along the ray's own horizontal direction from the camera. Residual **< 2°**. This tests the camera basis and the horizontal FOV term, and is **independent of any ground height**. |
| **P2 — HEIGHT CONSISTENCY** | the ground `z` implied by each click agrees across clicks on level ground, spread **< 150 u**. This tests the vertical term. |
| **P3 — the camera reads at all** | `camera` is present and non-`unread:` on a large majority of samples, and `pos` ≠ `tgt`. |

**REFUTED IF:**

- **P1 fails — bearings are wrong.** The basis, `UP_AXIS` or the FOV
  interpretation is wrong. **§1z-ax names both unsettled terms, so this is the
  clause that settles them**: the same capture can be re-scored offline with
  `UP_AXIS` on another axis and `fov` as the half angle, and whichever
  combination makes P1 pass is the measurement.
- **P2 fails while P1 passes** — the horizontal model is right and the vertical
  one is not, which points at the full/half-angle reading or the viewport span.
- **P3 fails** — the addresses do not hold a camera on this build, and nothing
  else in the run means anything.

**A large residual is not a failed run.** Because the capture is re-scorable
offline against every variant, the run's value is the DATA; only P3 failing makes
it worthless.

## 3. EXPOSURE FLOOR

- **≥ 5 clicks** that produced a `MOVE_TO_COORD` with a readable camera.
- Clicks landing on **GROUND** (`clickcal.py`'s prop sensor) are the scoreable
  subset — a prop hit is a ray-prop intersection and tests nothing about ground
  geometry. **≥ 4 of them.**
- The capture must reach the map.

## 4. The run

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress. **Ends on its own, ~110 s, nothing parked.**

**Terminal A:**

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 110
```

**Terminal B** — walk to open country (the clearance peak §1z-av found), then a
spread of fractions across the screen, both columns and rows:

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:1618 W:27.2 yaw:-876 W:4.9 click:0.5,0.40 wait:3 click:0.35,0.46 wait:3 click:0.65,0.46 wait:3 yaw:2250 click:0.5,0.52 wait:3 click:0.40,0.44 wait:3 click:0.60,0.50 wait:3" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```

**Off-centre columns are deliberate.** Every calibration so far has been
`fx = 0.5`, which cannot see the horizontal FOV term at all — a wrong `FOV_h`
would be invisible. These clicks span 0.35–0.65.

## 5. Scoring

Per click: the camera at that instant from the tape, the ray from `clickaim.ray`,
the bearing residual against the actual `MOVE_TO_COORD`, and the implied ground
`z`. Then the same re-scored under the `UP_AXIS` and full/half-angle variants —
**which is how §1z-ax's two declared-but-unestablished terms get settled from one
capture.**

---

## RESULT — RAN 2026-09-04. **P3 and P1 PASS; P2 FAILS and cannot be attributed.**

Capture `20260904T142759`, tape `agenttap-20260904T142831`.

**P3 PASS** — 1,056 of 1,056 samples carry a readable camera, reading
`fov = 1.30900 rad = 75.000 deg EXACTLY`, `pos = (9426.3, 8077.0, -731.8)`,
`tgt = (9826.0, 8077.0, -716.6)`. sec.fovaxis confirmed live.

**P1 PASS** — bearing residual over 6 GROUND clicks: **mean 1.02 deg, max 1.81**
against a registered < 2. And the variant re-score settles sec.1z-ax's two
declared terms:

| variant | bearing mean |
|---|---|
| **UP=+z, fov FULL** | **1.02 deg** |
| UP=+z, fov HALF | 20.93 |
| UP=+y, fov FULL | 9.35 |
| UP=+y, fov HALF | 17.06 |
| UP=-z, fov FULL | 15.84 |

A factor of nine over the next best. The off-centre columns (0.35-0.65) are what
made it a real test.

**P2 FAIL** — implied ground z spread **407.8 u** (-519 to -111) against < 150.
**This run cannot say whose fault it is**: our vertical term, or ground that is
not level. It was chosen for clearance, not flatness, and sec.1z-as.3 already
measured range varying with slope. Separating them needs a run designed for it --
the same world point from two camera heights, or a spot whose flatness is
established first. Full write-up: FINDINGS sec.1z-ay.
