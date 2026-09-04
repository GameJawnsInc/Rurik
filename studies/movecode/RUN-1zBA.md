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
