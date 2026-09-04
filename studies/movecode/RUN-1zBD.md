# RUN-1zBD — the `MapFindPath` return tap on a LEAD run: what does the client's pathfinder say at a portal the body will not cross?

**Registered before launching.** `MOVECODE-1z-bd`. Two runs, same arm. §1z-bc's
open question, put to the instrument built for it.

## 1. What is being asked

Six leads locked the client (§1z-ao, §1z-ap.3). Every one crossed a seam the pathing
file links as a portal — plane 29's end body trapezoids, linked along their whole
slanted edges — and the body walked none of them (§1z-bc). R7 (§1z-i) found the
client's own `MapFindPath` returning `pathCount == 0` **exactly** when the declared
from-plane is impossible at the from-point — on click walks. Nobody has armed the tap
on a lead run. This does.

**The arm:** `--kbd-lead --lead-seam-clip --no-repin-stationary-waiver`. The seam
clip (§1z-bc's opt-in) grants the portal-crossing leads at the full 520 u — the
retrodiction says so for every fatal lead — so this run re-arms the door on purpose,
with the tap watching. The waiver revert is the campaign's own condition (RUN-1zAO,
RUN-1zAQ) so the body's response is comparable.

**The script:** RUN-1zAQ's, from the spawn beside the bridge, with the opening wait
stretched so the hook can attach after the map loads:
`wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4`. RUN-1zAQ's known-bad arm produced 3 and 1
portal-crossing full-length leads per run on it.

**Three captures, one clock:** the gamesrv capture (the grants), the agenttap tape
(the drawn body), and `movehook.bin` (19 sites — `mapfindpath` and its four `ret`s,
`agapi_setdest`, `bake`, `agtrack`, `chcli_dir`, `inputeval`, …), attached by
`attach.py --minutes 1.0` the moment the harness prints "body is in the map".
Hook ticks are aligned to the wall on `agapi_setdest` points matched to grant rows.

## 2. THE PREDICTION

| | expected |
|---|---|
| **P1 — EXPOSURE** | across the two runs, **≥ 2 leads granted at or past gate 1 where §1z-ap's clip would have stopped short** (portal-crossing), each with a tape window and hook records in its window. |
| **P2 — THE QUESTION**, per portal-crossing lead | one of three, counted, none pre-decided: **(a)** a `MapFindPath` query within [−0.3, +2.5] s whose declared from-plane is the body's plane and whose **`pathCount == 0`** — R7's class, the pathfinder refusing an "impossible" plane; **(b)** a query with `pathCount > 0` while the body PARKED — the refusal is not the pathfinder's; **(c)** **no query at all** — the keyboard mover does not consult `MapFindPath`, and the other sites say what it did instead. |
| **P3 — CONTROLS** | the DLL's two controls FIRED; entries pair 1:1 with answers on (tid, esp); the R7 table for this run keeps its shape (a `pathCount == 0` only where the declared plane is not one our mesh offers at the from-point); same-plane leads WALK. |

**What each P2 outcome means, before the run:** (a) confirms the plane channel as the
lead's lock mechanism and hands the fix to the plane word (the grant's plane fields /
the client's declared plane), not to any ray; (b) says the body refuses for a reason
the pathfinder does not share — a prop or the mover's own per-step consult
(`0x0070A150`, untapped); (c) says the same, and additionally that R7's finding does
not transfer to keyboard movement at all.

**REFUTED IF** P1 fails — the seam clip did not grant a portal-crossing lead at gate
1 in two runs — then the retrodiction's exposure model is wrong and the run is a
targeting failure, not a null.

## 3. EXPOSURE FLOOR

- ≥ 2 portal-crossing leads across the two runs (P1).
- Hook alignment from ≥ 3 setdest anchors with spread < 50 ms.
- Both DLL controls FIRED; tape inside the run's window.

## 4. The runs

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver launches the tape, the harness and the hook. **Each run ends on its own,
> ~100 s.**

Driver (scratchpad, this session): starts `agenttap --seconds 95`, starts
`session.py -u` and watches its checkpoints; on "body is in the map" runs
`C:\gd\Rurik\toolkit\clientscan\movehook\attach.py --minutes 1.0 --out <dir>` (the
DLL lives in the main tree); the harness holds 30 s so the hook's timer elapses and
writes before the client closes. Equivalent by hand, from `C:\gd\Rurik`:

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 95
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 30 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --lead-seam-clip --no-repin-stationary-waiver"
```

```powershell
# the moment the harness prints "body is in the map":
python toolkit/clientscan/movehook/attach.py --minutes 1.0 --out vault/research/movecode/1zbd-run1
```

## 5. Scoring

```powershell
python studies/movecode/review/leadtap.py <run id> --hook vault/research/movecode/1zbd-run1/movehook.bin
```

Per portal-crossing lead: the body's class from the tape, every `MapFindPath`
question in the window with its declared plane, our mesh's planes there, its to-point
and its `pathCount`, the other sites' hits; then R7's table for the run and the
(a)/(b)/(c) counts. `readhook.py --bin` and `pathdiff.py --map 0x1B97D --bin` are
the tap's own readers and stay authoritative for anything this joins.
