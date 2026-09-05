# RUN-1zBP — the revert arm: `--waiver-walkstart-stands`, the known-bad control RUN-1zBO never had

**Registered before launching.** `MOVECODE-1z-bp`. One run, agent-driven, hands off, owner
away. This is the run §1z-bo.8 named as still owed: *"a shipped default whose revert arm has
never been exercised against the client is an assertion."*

## 1. What is being asked, and why RUN-1zBL cannot answer it

§1z-bo scored RUN-1zBO against RUN-1zBL and reached the right answer for a weaker reason than
it looked. Two problems with 1zBL as the control, both in §1z-bo.4 and §1z-bo.5:

- **1zBL is a different code revision.** By `waiverretro`'s own verdict control it was a
  different guard, and it took the §1z-bf population fix to bring it back into the evidence
  population at all.
- **Only ONE of the four removed re-pins is a state-matched trial.** Legs 1–2 start 0.0 u and
  2.7 u apart in the two runs; legs 3–7 start **503–714 u** apart on different planes, because
  1zBL's leg 2 was rewound and the runs diverge from there. Everything after leg 2 pairs on
  wall clock only.

**The revert arm fixes both at once.** Same binary, same day, same route, same instruments,
**one flag**. Whatever it reproduces of 1zBL's behaviour is attributable to the clause and to
nothing else, because nothing else differs.

**And it is the known-bad arm, which this repo requires and this arc has not run.** A scoring
instrument that reads the same in both arms is measuring the wrong quantity, not the wrong
threshold. Every number §1z-bo published — the in-glide `0x002C` census, the walk-start/stop
identity, the backward-excursion scorer, the moving-only separation — has been run against a
capture from a different build and never against a same-build negative. This run supplies one.

## 2. The configuration — RUN-1zBO's exactly, plus the revert flag

`--kbd-lead` ON, same `WSWQESW` route on map 146, `wait:8` opening, `--hold 30`, hook armed at
the same 26 sites. The single difference from RUN-1zBO is `--waiver-walkstart-stands`, which
sets `agtrack_guard.WAIVER_WALKSTART_ENDS_STILL = False`. The capture header records the flag,
so the arm is readable off the capture rather than off this document — and §1z-bo.3's flags-diff
check will be repeated: the two captures' whole `flags` dictionaries must differ in **exactly
that one key**.

## 3. THE PREDICTION

Every clause below is the mirror of RUN-1zBO's, because the point of a known-bad arm is that
the instruments must **redden**.

**P1 — EXPOSURE, and it gates everything.** At least **3 legs** whose opening committed segment
is long: bake target ≥ 300 u ahead and ≥ 1.0 s of report silence after the walk-start. 1zBO
scored 5 of 7, 1zBL 4 of 7, 1zBM 7 of 7 on this route.
**REFUTED IF fewer than 3** — the run has zero trials and scores nothing in either direction.

**P2 — THE DECISIVE ONE, AND IT IS THE INVERSE OF 1zBO's.** **At least one AGTRACK re-pin
FIRES during a held-key leg's opening glide** — a `due` transition reaching the wire as a
`0x002C`, where 1zBO had 0 of 7 and seven `stale-report` blocks.
**REFUTED IF ZERO FIRE.** That is the outcome that would matter most, and it would mean one of
three things, all bad for §1z-bo: the clause is not what suppressed the re-pins; something else
changed between the two runs; or the route stopped producing the condition. **A null here does
not confirm the fix — it invalidates §1z-bo's attribution**, and this sheet says so before the
run rather than after.

**P3 — THE BODY IS THROWN BACK.** At least one leg reports an **identical point** (≤ 1.0 u) at
its walk-start and its stop, and the largest backward step along the body's own heading (live
column, grouped on object address) is **≥ 100 u on both world copies**. 1zBO: 0 of 7 and
0.0 u. 1zBL: 3 of 7 and −449.7 / −452.6 u.
**REFUTED IF the body is never thrown back** while P2 is met — then the re-pin fires without
the rewind, and §1z-bl's mechanism needs re-examining rather than §1z-bn's fix.

**P4 — THE GUARD NAMES THE DIFFERENCE ITSELF.** On the `{0x0047 stop → 0x003D walk-start}`
pairs where 1zBO logged `blocked / stale-report`, this run logs **`due`** with `blocked_by`
null. This is the clause's behavioural delta read straight off the server's own telemetry, at
the same decision points, in the same build.

**P5 — CONTROLS.** Both DLL controls FIRED, ring not full. Per §1z-bl.8, only zeros at sites
proven live in other captures are quotable; `setposition` and `reseed` qualify, `heldbit`,
`movecache`, `chcli_point` and `mapfindpath*` do not.

## 4. EXPOSURE FLOOR and ABORT

P1's three long segments, or the run is a targeting failure and scores nothing — not a null.

**Decided now rather than afterwards:** P2 met and P3 met is the clean known-bad arm and closes
§1z-bo's "assertion" debt. **P2 refuted (zero fires) is the serious outcome** and it reopens
§1z-bo rather than confirming it; it must be written up that way even though it is the result
that would superficially look like "the fix works so well it works with the flag off".

## 5. The run

> ### ⚠ HANDS OFF THE KEYBOARD AND MOUSE ONCE THE CLIENT IS UP
>
> The driver starts the tape, the harness and the hook. **It ends on its own, ~2–3 min.**
> **Expect the character to warp backward during this run — that is the point of it.**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --walk "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 30 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --waiver-walkstart-stands"
```

with `agenttap.py --agents 1 --seconds 100` beside it and
`movehook/attach.py --minutes 1.1 --out vault/research/movecode/1zbp` fired at "body is in the
map". **The DLL is the main tree's build**, as in 1zBL/1zBM/1zBO; said out loud per the
cross-tree rule.

## 6. Scoring

Leg for leg against **RUN-1zBO**, which is this run's own build with the flag the other way.
Every instrument §1z-bo used, re-run unchanged — that is the point:

| what | instrument | 1zBO's value | this run must |
|---|---|---|---|
| long silent opening legs | hook bake target + wire | 5 of 7 | ≥ 3 |
| in-glide `0x002C` | wire | 0 | **≥ 1** |
| client `setposition` hits | `readhook.py` | 0 | **≥ 2** (one per world copy) |
| legs same point at walk-start/stop | wire only | 0 of 7 | **≥ 1** |
| largest backward step, both copies | tape, live column | 0.0 u | **≥ 100 u** |
| guard rows on the `{stop → walk-start}` pair | wire | 7 × `blocked/stale-report` | **≥ 1 × `due`** |
| moving-only separation | `w0score` §1z-bh line | 13.0 u | *reported, not predicted* |

The separation is deliberately **not** predicted: §1z-bl.6 showed the `0x002C` reseeds both
copies together, so a rewound run's separation is biased low by its own defect and the number
is uninterpretable as a quality measure. Report it; do not score it.

---

## RESULT — RAN 2026-09-05 15:37. Scored in [FINDINGS.md](FINDINGS.md) §1z-bp.

Harness `20260905T153758`, PASS, all 8 legs full duration. Capture valid: 8,736 hook records,
**both controls FIRED**. Flags diff against RUN-1zBO is exactly one key:
`agtrack_guard.WAIVER_WALKSTART_ENDS_STILL` True → False.

| | prediction | 1zBO (clause ON) | **1zBP (clause OFF)** | |
|---|---|---|---|---|
| **P1** | ≥ 3 long silent windows | 7 | **5** | MET |
| **P2** | ≥ 1 in-glide `0x002C` | 0 | **3**, all `arrival-risk` | MET |
| **P3** | ≥ 1 leg same point; ≥ 100 u backward | 0 of 7; 0.0 u | **3 of 7**; **−432.2 / −432.4 u** both copies @ t=34.47 | MET |
| **P4** | ≥ 1 `due` on the refused pair | 7 × `blocked/stale-report` | **3 × `due`** | MET |
| **P5** | controls fired | FIRED | FIRED | MET |

Client-side: `setposition` **6 hits** against 1zBO's 0 — exactly 3 sends × 2 world copies.

**The matched decision points**, 0.01–0.02 s apart: +15.4 s blocked in **both** arms (leg 1W,
`prev_pos is None` — §1z-bo.2's source-derived correction, now measured); +23.1, +35.3 and
+44.9 s `blocked/stale-report` under the clause and **`due`** with it reverted.

Moving-only separation **51.6 u** (n=261) against 13.0 u — reported, **not scored**, per §6 of
this sheet: the `0x002C` reseeds both copies so a rewound arm's separation is uninterpretable,
and 51.6 > 13.0 is not evidence the fix improves tracking.

**Unchanged by this run:** `gate2-offmesh` still has zero exposure on this route, and PLAN §7
Q15 (should `STATIONARY_WAIVER` exist at all) is untouched. This run reproduces the *defect*,
which is the easier half — the clause's KEEP branch remains unwitnessed.
