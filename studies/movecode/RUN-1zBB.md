# RUN-1zBB — does the seam-aware router ray close RUN-1zBA's door?

**Registered before launching.** `MOVECODE-1z-bb`. Two runs, **RUN-1zBA run 4's
script verbatim** (walk onto the bridge deck, click over the west railing at
fy 0.46, then controls), one per arm:

| arm | server flags | what it is |
|---|---|---|
| **A — fix** | default (`ROUTER_SEAM_CLIP = True`) | the router's two rays walk the body's plane and stop where it ends without a portal |
| **B — known-bad** | `--router-blind-clip` | the plane-blind `clip()` RUN-1zBA convicted, re-armed on purpose |

Same script, same spot, same click. The only variable is the ray.

## 1. THE PREDICTION

The click over the railing lands off-mesh on the far hillside (~(8500, 4340),
as in runs 2 and 4), so the router takes its **clip fallback** both times.

| | arm A (fix) | arm B (known-bad) |
|---|---|---|
| the fallback's stop | **within 20 u of x = 10860** — the deck's west edge — a leg of ~130 u (the desk says (10861, 5190), 136 u) | ~2,000 u past the edge, as in run 4 (2,158 u) |
| the drawn body | **WALKS** it: velocity > 0, arrives within 40 u, no live jump ≥ 150 u | **PARKED+SNAP**: velocity 0 at x = 10860.0 for the leg's ETA (~7 s) while the sync copy walks, then a ~2,000 u teleport |
| the fence | stays **open** through the leg | **shuts** at the snap |

**REFUTED IF** arm A's body parks or snaps on its fallback leg, or arm A grants
past the edge. **UNEXPOSED IF** click 1's `MOVE_TO_COORD` lands on-mesh in either
arm (aim drift onto the deck) — then that arm's fallback never ran and it is
re-run, not scored.

**Arm B is the control that makes A a measurement**: it re-arms the defect on
the same geometry the same afternoon. If B does not reproduce run 4, the
harness or the scene moved and A's clean leg is not evidence.

## 2. EXPOSURE FLOOR

- Each arm: click 1 produces a `MOVE_TO_COORD` that is off-mesh, and a
  `router_route` row with `verdict = clip-fallback`.
- Each arm: a tape window of ≥ 3 samples over the fallback leg.

## 3. The runs

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> `--walk` drives everything. **Each run ends on its own, ~60 s, nothing
> parked.** Arm A first.

**Terminal A** (each run):

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 90
```

**Terminal B, arm A (fix):**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:812 W:9.6 yaw:297 W:1.3 yaw:891 wait:2 shot:1 click:0.5,0.46 wait:9 click:0.5,0.44 wait:9 click:0.5,0.48 wait:9 yaw:-875 click:0.5,0.46 wait:9" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0"
```

**Terminal B, arm B (known-bad):**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:3 yaw:812 W:9.6 yaw:297 W:1.3 yaw:891 wait:2 shot:1 click:0.5,0.46 wait:9 click:0.5,0.44 wait:9 click:0.5,0.48 wait:9 yaw:-875 click:0.5,0.46 wait:9" --hold 5 --game-args "--map 146 --explorable --no-enemy-skills --skills 0,0,0,0,0,0,0,0 --router-blind-clip"
```

## 4. Scoring

```powershell
python studies/movecode/review/seamscore.py <run id>
```

Per granted leg: the walker's seam verdict on the granted origin→dest, the
fallback's stop distance from the origin, and the drawn body's class from the
live track (WALKED / PARKED+SNAP), with the fence transitions. Arm A's
fallback leg must be short and WALKED; arm B's long and PARKED+SNAP.
