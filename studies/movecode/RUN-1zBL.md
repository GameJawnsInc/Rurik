# RUN-1zBL — the hook on the seam stall: what does the client do while four held keys move nothing?

**Registered before launching.** `MOVECODE-1z-bl`. The check §1z-bk.4 named the priority.
One run, agent-driven, hands off, owner away.

## 1. What is being asked

RUN-1zBK (§1z-bk) walked `WSWQESW` on map 146 with no enemy and the lead on. Leg 3 crossed
the plane 29→0 seam and stopped at `(11456, 9151)` plane 0; **from that stop the client's
reported position never changed again** — the last four held-key legs each opened a `0x003D`
walk-start and closed a `0x0047` stop from that one point, the drawn body pinned there, and
four AGTRACK re-pins reseeded it back (all *after* the freeze, so consequence not cause).
`stopcensus` and `w0score` both scored the run clean. The onset is client-side and this run
puts the hook on it.

**The tap is the whole hook, not only `MapFindPath`.** §1z-bd.1 already measured that the
keyboard mover **never calls `MapFindPath`**, so the return tap alone would very likely see
nothing here; that is registered below as the EXPECTED branch rather than a surprise. What
answers the question is the input path — `movecmd` / `movedispatch` / `inputeval` /
`heldbit`, `chcli_dir`'s trace, the `bake`, and `setposition` / `reseed` / `snaptest` — with
legs 1–3 of the same run as the within-run walking control.

## 2. The configuration — RUN-1zBK's, with the opening stretched for the hook

RUN-1zBK's command with `wait:3` → `wait:8` (RUN-1zBD's stretch, so the hook attaches before
the first key) and `--hold 30` (so the DLL's timer elapses and it writes before the client
closes). Everything else identical: shipped guard, lead ON, no enemy, same route, map 146.

## 3. THE PREDICTION

**P1 — EXPOSURE, and it gates everything else.** The stall reproduces: **≥ 2 held-key legs
whose reported position never changes and whose drawn-body travel is < 100 u**, following a
leg that crossed the 29→0 seam.
**REFUTED IF all seven legs walk** — then the stall is not deterministic on this route, this
run is a targeting failure rather than a null, and §1z-bk's specimen stands at n = 1.

**P2 — THE INPUT PATH, per frozen leg.** Exactly one of three, counted, none pre-decided:

| | what the hook shows | what it means |
|---|---|---|
| **(a)** | `movecmd` / `movedispatch` fire on the held key, but no `bake` follows / `chcli_dir` yields no advance | the mover consumes the key and refuses internally; the last record before the silence names the site |
| **(b)** | **`movecmd` fires 0 times** while the key is held (§1z-be.4's post-halt class) | GmWalk stopped re-dispatching; the freeze is in the input path, not the pathfinder |
| **(c)** | `movecmd` fires, a `bake` follows, and the body's `+0x78` advances in the hook records | the body DID move client-side and only the c2s REPORT froze — a reporting defect, not a movement one |

**P3 — `MapFindPath`.** Registered expectation, from §1z-bd.1: **zero** `mapfindpath` entries
attributable to the frozen legs. If queries do appear, record each one's from-point, declared
plane and `pathCount`. **A `pathCount == 0` from `(11456,9151)` on a plane our mesh offers
there would refute §1z-i's law out of sample** (the law says zero only when the declared
from-plane is impossible) and is the single most important record the run could produce.

**P4 — CONTROLS.** Both DLL controls FIRED (A: the DLL's own-buffer `int3`; B: a byte the
client's own EIP was sampled executing); entry/ret records pair 1:1 on `(tid, esp)`; the ring
is **not** full. **REFUTED IF** a control did not fire or the ring is full — the capture is
void and no null from it is quotable (§5.2's rule).

## 4. EXPOSURE FLOOR and ABORT

- P1's two frozen legs, or the run is a targeting failure and is written as one.
- Both controls fired; ring not full; the tape covers the frozen legs; the gamesrv capture
  joins on the `agapi_setdest` anchors.
- **ABORT** the interpretation if the Hatcher control cannot be read (no enemy this run, so
  the tape's own validity is the sample count and zero `unread:`).

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver starts the tape, the harness and the hook. **It ends on its own, ~85 s.**

```powershell
python toolkit/clientscan/agenttap.py --agents 1 --seconds 100
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 30 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

```powershell
# the moment the harness prints "body is in the map":
python toolkit/clientscan/movehook/attach.py --minutes 1.1 --out vault/research/movecode/1zbl
```

**The DLL is the main tree's build** (`C:\gd\Rurik\toolkit\clientscan\movehook\`, sites
generated 2026-09-01 against build 38797); this run attaches that binary while the write-up
happens on `MOVECODE-1z-bl`. Said out loud per the cross-tree rule.

## 6. Scoring

`readhook.py --bin` for the controls, the ring and the census; `leadtap.py <run> --hook` for
the per-leg join; `pathdiff.py --bin --map 0x1B97D` if any `MapFindPath` records exist. The
frozen legs are scored against legs 1–3 of the same capture.

---

## RESULT — RAN 2026-09-05 11:33. Scored in [FINDINGS.md](FINDINGS.md) §1z-bl.

Capture valid: 7,962 records, ring 24% full, **both controls FIRED**, timer elapsed.

| | |
|---|---|
| **P1** | MET — three legs (2S, 4Q, 7W) reported the identical point at walk-start and stop |
| **P2** | resolves to a fourth outcome the registration did not list: the body **walked** (branch c's clause) AND the input path stopped re-dispatching (branch b's clause), with our `0x002C` the hinge between them. `movecmd` 1 per frozen leg vs 163/227/108 per walking leg; `inputeval` 179–240 throughout |
| **P3** | MET as registered — **`mapfindpath` 0 hits on all five sites.** The keyboard mover never consults the pathfinder; the stall is not a client path refusal and MOVECODE-Q2 is not its explanation |
| **P4** | MET — controls fired, ring not full, alignment 2 anchors / 12 ms spread |

**The finding.** The body walks the held key exactly as commanded (443 / 426 / 308 u by the
client's own `position_at`) and **our AGTRACK re-pin throws it 294–433 u BACKWARD** to the
leg's start, after which GmWalk never re-dispatches the key. The trigger is **report
silence**: across the three runs' 21 legs, **9 of 9 legs with no mid-leg `0x003D` were
re-pinned against 1 of 12 that reported**. §1z-bk's "the onset is client-side and upstream of
our re-pin" is **REFUTED** — the re-pin is the cause, and the error was reading a
sample-and-hold `m_point` as a body that had not moved.

