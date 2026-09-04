# RUN-1zBA — does the client WALK a router leg that crosses a BLIND plane seam?

**Registered before launching.** `MOVECODE-1z-ba`. One run, five clicks, no
aiming beyond the calibrated yaw. This is §1z-ar's question put to the client
for the first time — §1z-az produced a routed grant that crossed no seam.

## 1. The target, and how it was chosen

`studies/movecode/review/seamscout.py` walks every trapezoid edge on map 146
and asks, per plane change a body can make by stepping off an edge, whether the
file carries a portal there. It finds **195 blind seams** (a plane change with
no portal; the pull walks straight across them, the A* never would), and both
its positive controls pass — **168 of 168** cross-plane portal pairs that link
anything are found (21 more have an empty side and link nothing), and the
per-leg walker agrees with the census on 99% of seam-local walks.

The nearest usable blind structure is **plane 18**: a strip 263 u wide and
1,047 u long (x 10860..11123, y 4532..5579), water on both sides in the
middle, its only two portals at its ENDS — zero-height lines at y = 4532 and
y = 5579 — and the east bank abutting its east side for ~260 u near the north
end. For the chord below the A* corridor is **41 waypoints and 6,180 u** (west
around the water, up the strip from its south end) and the string pull
collapses it to **one straight 600 u leg through the strip's east side**. That
is §1z-ar.1's mechanism on the desk. Basin score **0.96**: 104 of 108 chords
inside the run's error budget (origin ±120 u, bearing ±3°, range 0.75–1.6×)
still cross blind.

- **Stand:** (11174, 5175), plane 0, the east bank. 3,199 u from the spawn, one
  straight mesh leg.
- **Chord A (forward), bearing 116.5°:** every range from 200 u to 800 u crosses
  the blind seam 0→18 at (11104, 5316); ranges ≥ 600 u also exit through the
  north-end portal 18→0 at (10972, 5579).
- **Chord B (back), bearing 296.5°:** from anywhere on the deck, crosses 18→0
  blind at (11123, ~5278).

## 2. The script

Walk in, face the chord, screenshot, then five clicks at `fy = 0.46`
(~330 u on level ground, §1z-az's calibration — meant to land ON the deck):

| click | facing | expected leg | seam |
|---|---|---|---|
| A | 116.5° | east bank → onto the deck's east side | **BLIND 0→18** |
| B | 296.5° | deck → off its east side to the bank | **BLIND 18→0** |
| C | 116.5° | as A | **BLIND 0→18** |
| D | 90.0° | deck → north along the strip, out its north end | PORTAL 18→0 (control) |
| E | 283.2° | north shore → in through the north end, out the east side | PORTAL then BLIND |

Every leg is scored on what the wire actually granted, not on this table.

## 3. THE PREDICTION

| | expected |
|---|---|
| **P1 — EXPOSURE** | at least **2 granted legs** cross a blind seam by `seamscout.seam_crossings` on the granted origin→dest. Below that the run measured nothing. |
| **P2 — THE QUESTION** | on each blind leg the drawn body (world 1) either **WALKS** it — reaches the granted point, no jump ≥ 150 u — or **PARKS**: moves < 40 u while the sync copy (world 0) walks the leg, then jumps to the granted point at the leg's ETA (RUN-1zAO's arrival snap, §1z-ao.2). |
| **P3 — CONTROL** | legs that cross a **portal** or no seam (D, and E's first crossing) are WALKED normally. |

**What each P2 outcome means, stated before the run:**

- **PARKED on blind legs, WALKED on control legs** → the router's plane-blind
  pull produces grants the client cannot walk. §1z-ar's harm is real and
  observed; the two-line plane term in `_visible` is justified — **and it is
  not sufficient**, because the router's clip *fallback* is plane-blind too and
  would grant this same straight leg on a capped tour. Both sites, or neither.
- **WALKED on blind legs** → the client walks straight across this seam class
  (abutting deck edge over ground). No harm on the only blind geometry a run
  can reach on this map; §1z-ar stays unshipped with a measured null against it.
- **Anything PARKED on control legs** → the instrument or the harness is at
  fault (a parked body is not a seam finding) and nothing here scores.

**REFUTED IF** P1 fails: the aim did not put a granted leg across the seam,
and the run is a targeting failure, not a null.

## 4. EXPOSURE FLOOR

- **≥ 2** granted legs scored BLIND by the walker, with a tape window of ≥ 3
  samples each.
- **≥ 1** control leg (PORTAL or none) with a tape window.
- The capture must reach the map and the tape must be inside the run's window.

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress. **Ends on its own, ~55 s, nothing parked.**

**Terminal A** (first — it waits for the client):

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 80
```

**Terminal B:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:814 W:11.1 yaw:2230 wait:2 shot:1 click:0.5,0.46 wait:5 yaw:-2250 click:0.5,0.46 wait:5 yaw:-2250 click:0.5,0.46 wait:5 yaw:332 click:0.5,0.46 wait:5 yaw:2085 click:0.5,0.46 wait:5" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```

The yaw pixel counts come from `mapscout.yaw_to` at the calibrated 12.5 px/deg
(§1z-as, confirmed predictively at §1z-at and §1z-az).

## 6. Scoring

```powershell
python studies/movecode/review/seamscore.py
```

Per click: the `MOVE_TO_COORD`, the router's verdict, then per granted leg the
walker's seam verdict on the granted origin→dest and the tape's reading of both
player copies over [grant, grant + ETA + 1 s] — body travel before any snap,
sync travel, max separation, largest single-sample jump, arrival, fence
transitions — classified WALKED / PARKED+SNAP / PARKED / OTHER. Then the three
clauses. Smoke-tested on §1z-az's run B before this sheet was written: its
three plane-23 legs score `none` / WALKED.

---

## RESULT, run 1 — RAN 2026-09-04 15:37. **P1 FAILS (0 blind legs): a targeting failure, and the failure is the mechanism under study.**

Capture `20260904T153746`, tape `agenttap-20260904T153817` (918 samples). All
five clicks landed on GROUND and were granted; all five legs WALKED; **none
crossed a blind seam**, because click 1 fired from **(11123, 5213) on plane 18**
— the deck's east edge — not from the bank.

**Why:** the walk-in was planned by `mapscout.emit_script` over `pm.route()`,
whose string pull is the plane-blind one this whole sheet is about. Spawn →
bank came out as ONE straight 3,200 u leg through the bridge (the corridor that
respects planes is 8,831 u, around the west). The body crossed onto the deck
through the north portal — and then, **under the held key, stopped at
x = 11123.0, the deck's east edge, and slid south along it for the last 77 u
while the server's straight-line model put it 37 u past the edge on the bank**
(`position_report` drift 37.35 at the stop). The screenshot is the stone bridge
into Ascalon City, parapet and all; the on-deck camera puts the deck **~155 u
above the north shore**.

So the census's blind seam is a physical barrier to the client's body — seen
under the keyboard, not yet under a router grant, which is what P2 asks. The
operator touched the mouse ~15 s from the end; that can only have affected
clicks 4–5 (control legs, both WALKED) and is not the failure.

## Run 2 — the deck as origin, the WEST exit as the treatment

Two corrections. **The walk-in is now planned with a plane-aware pull**
(`seamscout.seam_route`: a shortcut must clip clear, cross no blind seam on the
kept point's plane, and end on the corridor's plane) — the §1z-ar fix
prototyped in the harness planner where it can do no harm. And **the origin is
the deck**, because a click from beside a raised deck hits its side wall
(§1z-as's prop trap), while from the deck the camera is high and a low click
lands on the bank beyond the edge.

- **Stand:** (11000, 5200), plane 18, via the north portal — 3,136 u, 11 s, one
  portal crossing and no blind one.
- **Treatment, bearing 200° (west bank):** blind 100% over ranges 250–750 u
  and a ±80 u origin spread; every range 300–900 u lands on plane 0.
- **`fy` is BRACKETED** — 0.60, 0.40, 0.70, 0.30 — because the projection's
  vertical sign is unresolved (§1z-ay P2; re-scoring that run with the vertical
  basis negated took the spread from 408 to 276 u, no collapse). Under the
  code's sign fy 0.30/0.40 reach ~450/690 u; under the flipped one fy 0.70/0.60
  do. The first click that lands moves the body off the deck; later ones fire
  from the bank, further west, as seam-free controls.
- **Control, bearing 270°** (`fy` 0.46): south along the bank, no seam.
- One exit per run, deliberately: a mid-run keyboard return to the deck would
  be planned from a landing the run cannot confirm. The **east exit** — the edge
  that blocked run 1's body — is run 3, same script mirrored.

**P1's floor of 2 is therefore across runs 2 + 3**; each run's own floor is
**≥ 1 blind leg with a tape window**. P2 and P3 as registered above.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 80
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:812 W:9.6 yaw:297 W:1.3 yaw:891 wait:2 shot:1 click:0.5,0.60 wait:6 click:0.5,0.40 wait:6 click:0.5,0.70 wait:6 click:0.5,0.30 wait:6 yaw:-875 click:0.5,0.46 wait:6" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```

---

## RESULT, run 2 — RAN 2026-09-04 15:55. **P2: PARKED+SNAP on the one blind leg. P3 controls WALKED. The harm is real, on a router grant.**

Capture `20260904T155523`, tape `agenttap-20260904T155554` (868 samples). The
walk-in landed on the deck at **(10989, 5236)**, 39 u from the plan.

| click | fy | landed | router | leg | seam | body |
|---|---|---|---|---|---|---|
| 1 | 0.60 | (10871, 5193) deck, 126 u | verbatim | on the deck | none | WALKED |
| **2** | **0.40** | (8500, 4330) **off-mesh**, 2,522 u — over the railing | **clip-fallback** to (8961, 4498) | **2,032 u** | **BLIND 18→0 at (10861, 5189), f = 0.01** | **PARKED+SNAP** |
| 3, 4 | 0.70, 0.30 | off-mesh | refused | — | — | — |
| 5 | 0.46 | (8959, 3968) ground | clip-fallback, 331 u | ground | none | WALKED |

**The specimen, from the tape:** at the grant the drawn body stood at
(10870.8, 5192.8); within 0.17 s it was at **(10860.0, 5188.9) — x = 10860.0,
the deck's west edge — velocity 0**, and it stayed there for **7.08 s while the
sync copy walked 2,002 u away at 288 u/s**. At **+7.17 s** (the leg's ETA is
7.06 s) the body was **teleported 2,021 u** to the granted point and **the fence
shut** in the same sample. The server saw none of it — a click-walk sends no
position reports — except its own AgTrack guard blocking a re-pin at +6.42
(`gate1-red`). §1z-ao.2's signature, reproduced on a router grant.

**Two things the specimen is NOT.** It is the router's **clip fallback**, not
its string pull: the click landed off-mesh (the railing put the far hills under
the cursor), the router fell back to the plane-blind `clip()` of the straight
line, and that clip walked off the deck at 10 u and on for two kilometres. The
pull's version — a `verbatim` leg onto a walkable bank — needs the click to
LAND on the bank, which is run 3's job. And the lock was **not permanent**: the
fence re-armed **2.5 s later on the next click** (click 3, itself refused), so
under click movement the client's own local-command path re-arms what the snap
shut — unlike RUN-1zAO's keyboard case.

**And a measurement the bracket was designed to make:** three on-mesh landings
from one camera — fy 0.60 → 126 u, fy 0.70 → 17 u, fy 0.46 → 523 u — say
**lower on the screen is nearer**, and `clickaim.basis`'s screen-up vector
pointed the other way (the world is z-DOWN; `cross(r, f)` points at the
ground). Fixed in `clickaim.py`; §1z-ay's open P2 was this sign plus terrain.

## Run 3 — the EAST exit, aimed to LAND on the bank

Same walk-in and stand. Bearing **330°** (blind 100% from the stand). With the
corrected sign and run 2's on-deck camera (337 u behind, 76.8 u above the
target), fy **0.70 / 0.65 / 0.75** land **231–567 u** out for any bank height
between 60 and 155 u below the deck — on the bank (plane 0, which extends
≥ 350 u east of the edge at this y), never on the deck. The first landing moves
the body off the deck; the later clicks fire from the bank as controls. Then
bearing 270°, fy 0.46 — a seam-free control.

**What run 3 adds:** the pull's specimen (a `verbatim` blind leg onto walkable
ground), the mirror edge (the one that blocked run 1's keyboard body), and the
second blind leg P1's floor asks for.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 80
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:812 W:9.6 yaw:297 W:1.3 yaw:-734 wait:2 shot:1 click:0.5,0.70 wait:6 click:0.5,0.65 wait:6 click:0.5,0.75 wait:6 yaw:750 click:0.5,0.46 wait:6" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```
