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

---

## RESULT — RAN 2026-09-04 17:37 (run 1) and 17:40 (run 2). **P1 met (4 portal-crossing leads). P2: outcome (c), four of four — the keyboard mover never calls `MapFindPath`. The park is the client's, at the wedge tip, before our re-pin.**

| | run 1 `20260904T173704` | run 2 `20260904T174050` |
|---|---|---|
| hook | v9, 8,234 records, both controls FIRED, attached 4.4 s after the map line | 8,363 records, both FIRED, 2.7 s |
| tape | 917 samples, Hatcher control shut 917/917 | 772, shut 772/772 |
| `MapFindPath` calls | **0** in 60 s | **2**, both from caller `0x00605807` — snaptest's gate 2, not the mover |
| portal-crossing leads | 1 — the wedge, `(10369, 8282)` → 520 u W: **WALKED** (528 u, separation 9 u) | 3 — the wedge `(10374, 8287)` → 520 u W: **PARKED** through the S hold; NE end `(11112, 9008)` → N: WALKED, then a gate-2 **reseed** at +2.48 s; bank → deck: WALKED |

**The pre-lead stall, both runs, to the tenth of a second.** Under the W hold the
body reaches the wedge tip; from **−4.46 / −4.49 s** the mover re-targets the tip
vertex `(10366, 8279)` **35 times at 16 ms** with no advance; the client's own
report at **−3.87 / −3.85** already has it stationary there; our `gate2-offmesh`
AGTRACK RE-PIN follows at **−3.72 / −3.71**. Our re-pin is downstream. The body
stands at the tip for the rest of W.

**The lead, both runs.** S at −0.03 → the walk-start report → the 520 u lead west
(the fatal shape) → the fence re-arms. The hook shows the same client sequence in
both: `movecmd → movedispatch → chcli_dir → agapi_setdest` with a first
quarterstep whose target lies **on the wedge's west edge** — `(10363.0, 8282.0)`
and `(10358.0, 8287.0)`, 0.01–0.03 u outside plane 29 by our decode, i.e. the
seam line itself. Then they part: **run 1 fires `chcli_advance` 47 ms later and
feeds the 767 u segment `(9602, 8283)` across the portal; the body walks at 190
u/s. Run 2 never advances; the body stands on the seam with the fence OPEN for the
whole 4 s hold**, while `resume_fire` runs at +0.29 with the same gate words
(flags 2, status 0) run 1's +0.31 carried. Run 2's lead did not mature into a
warp only because the sync copy left the ray — 105 u NW and stopped — so RUN-1zAO's
+2.96 arrival snap had nothing to fire on.

**R7's class appeared once, elsewhere:** at the NE end the lead carried plane 29 onto
plane-0 ground; snaptest's gate 2 asked `MapFindPath` from the granted point
declaring 29 (mesh offers 0) → `pathCount 0` → `reseed` in the next records — a
warp from the plane word a lead carries across a portal. The other gate-2 query
(from the sync copy's stop at `(10277, 8327)` declaring 29 on plane-0 ground)
returned **1**, which R7's exceptionless rule does not predict; one query, noted.

**Verdict.** The instrument answered: keyboard movement does not consult
`MapFindPath` (0 of ~880 step commands), so the plane-class pathfinder failure is not
the lead's park; file-linked portals are crossable (2 of 4 crossed at speed, one at
the fatal spot); **the park is the client's keyboard mover stalling at the wedge
tip — its first step lands on the seam line and the waypoint feeder sometimes does
not carry it across** — intermittent, preceding our re-pin. Our lead's only part is
the warp that follows when a full-length lead matures during the stall, which
§1z-ap's clip prevents. Write-up: FINDINGS §1z-bd.
