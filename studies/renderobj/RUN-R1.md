# GROUNDZ-R1 — the stairs again, with the height column: is the reader real?

**Registered before the run.** `GROUNDZ-R1`. The whole render-object arc so far is **static
disassembly of build 38797 and nothing else** — not one float in it has been read out of a
running process. This is the run that can break it.

**Identifiers.** `GROUNDZ-R<n>` = runs. (Legend in [FINDINGS.md](FINDINGS.md); `-F` facts,
`-Q` questions.)

## 1. What is under test — the reader, not the server

`toolkit/clientscan/groundz.py`, wired into `agenttap` and ON by default. It walks an agent id
to the client's AgentView object and reads the ground z at `view+0x8C`, guarded by the count,
a non-null slot, the `0xDB` type tag, and the round trip `[view+0x2C] == id`.

**No server behaviour changes.** The three defaults shipped 2026-09-05 (the fence bound, the
NPC router, the plane words) are unchanged and are not what this run scores. If the wire looks
different from RUN-1zCA, that is a finding about them, not about the reader.

## 2. THE EXPOSURE FLOOR, and here it is mostly about the reader working at all

| | floor |
|---|---|
| tape samples where `groundz.ok` is **true** for the player | **≥ 200** |
| the same for the Hatcher (agent 10) | **≥ 200** |
| samples with the player's plane column reading **29** | **≥ 20** |

**ABORT:** if `groundz.ok` is false everywhere, this is **not** a null about height — it is the
walk being wrong, and the `why` column names which guard refused. That is a useful result and
it is written up as a decode failure, never as "no height found". If `ok` is true but the
plane-29 count is short, the height numbers still score P1 and P4 but **not** P3.

## 3. THE PREDICTIONS — GROUNDZ-F3/F5's own, made refutable

**P1 — THE ROUND TRIP HOLDS.** `groundz.ok` is true for both agents on essentially every
sample. **REFUTED IF** the `why` column is dominated by `id-roundtrip` — that would mean the
array is not indexed by the agent id, and GROUNDZ-F1 is wrong at its foundation.

**P2 — THE MEMO SELF-CHECK, and it has NO free parameter.** `view+0x8C` must equal `view+0x30`
on essentially every sample: `0x007EBFC4` returns exactly what `0x007EBFA0` stored, so the two
are the same number unless our offsets are wrong. **REFUTED IF they differ systematically** —
then `+0x30` is not the memo, and GROUNDZ-F3 needs redoing. A handful of disagreements at a
store boundary are expected and are not a refutation.

**P3 — THE HEIGHT MOVES WITH THE GEOMETRY.** The player's `+0x8C` must **change** while they
climb and descend the stairs, and hold **much** flatter while they walk level ground.
**REFUTED IF it is constant across the whole run** — a constant is what a wrong offset that
happens to point at a stable float looks like, and it is the single most likely way this reader
is quietly wrong.

**P4 — IT IS A PLAUSIBLE HEIGHT, NOT A COORDINATE.** `+0x8C` must be a small-magnitude float
distinct from `+0x84`/`+0x88`, which are the agent's x and y (thousands of units on this map).
**REFUTED IF** `+0x8C` tracks x or y.

**P5 — THE SINK, and this is the one the arc actually wants.** During a parked stretch on the
stairs, capture `+0x8C`, `+0x30` and `+0x40` together. GROUNDZ-F6 left three separable
candidates for the ankle-deep sink; this is the first data that can tell them apart. **Not a
pass/fail** — it is the measurement, and it is recorded whatever it says.

**Explicitly NOT tested:** `model+0x18`. Reaching it needs the `'mdl '` handle-table resolve at
`0x0046FE40`, which is not decoded. The raw handle is recorded so the next session starts there.

## 4. The run — scripted, driven by the agent, no human aiming

RUN-1zCA's route exactly, so the two are comparable leg for leg.

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/renderobj/r1-agenttap.jsonl
```

## 5. Scoring — decided now

| what | instrument | bar |
|---|---|---|
| exposure | `groundz.ok` counts per agent | §2's floors, **first** |
| P1 | the `why` column histogram | no `id-roundtrip` |
| P2 | `+0x8C` vs `+0x30` per sample | equal on essentially all |
| P3 | `+0x8C` variance on the stairs vs on the flat, split by the plane column | moves on stairs |
| P4 | `+0x8C` magnitude vs `+0x84`/`+0x88` | distinct, small |
| P5 | `+0x8C`, `+0x30`, `+0x40` during the hold | recorded, whatever it says |
| regression | the wire against RUN-1zCA | the plane words unchanged |

**One known limit:** the tape samples at ~11 Hz, so a crossing shorter than ~90 ms falls between
samples (§1z-bw.7). If P3 is thin, that is why.

---

## RESULT — RAN 2026-09-06 01:32, 76 s. **ALL FIVE PREDICTIONS MET, the reader is real, and P5 found the sink's mechanism end to end.**

| | |
|---|---|
| exposure | **799 of 799 samples `ok` for BOTH agents, zero refusals**; player plane-29 samples 451 (floor 20) |
| **P1** the round trip | **MET** — zero `id-roundtrip` refusals. `array[id]->+0x2C == id` holds live, so GROUNDZ-F1's walk is right |
| **P2** the memo self-check | **MET, exactly** — `+0x8C == +0x30` on **799 of 799** for both agents. No free parameter, no tolerance |
| **P3** moves with the geometry | **MET** — 243 distinct values; on plane 29 the range is **171.30 u** (stdev 50.05), on plane 0 **21.60 u** (stdev 7.15). An 8× wider spread on the stairs |
| **P4** a height, not a coordinate | **MET** — −641 to −837 against x/y in the ten-thousands |

**A bonus the run settled for free: GROUNDZ-F7's `up is -Z` is no longer a reconstruction.**
Heights are negative and grow MORE negative up the stairs (−837 at the top of the plane-29
range against −641 on the flat). The static case rested on two independent witnesses; this is
a live measurement agreeing with them.

### P5 — THE SINK, MEASURED, and it is OUR stale plane word

During the 22 s hold the two bodies are 74 u apart and:

| | client plane | `groundz` | query plane |
|---|---|---|---|
| player | **29** | −695.904 | 29 |
| Hatcher | **0** | −663.403 | 0 |

**32.5 u apart in height** — the Hatcher below — while our own navmesh says **both** stand on
plane-29 ground: it stopped at (10375, 8293), and `planes_at` there is `(29,)`.

**The chain, every link measured:**

1. our last follow order to it was `(29, 0)` at t=51.75 — field 4 = **0**, because
   `_npc_plane` resolved the mover's plane **at send time**, while it was still on the flat;
2. it then walked onto plane-29 ground and **arrived**, so no further order went out;
3. **the halt `0x0028` carries no plane** — retail's shape, and §42.5 explicitly said it
   "needs nothing", which was written before anyone could measure this;
4. so the client's agent keeps plane **0** while standing on the stairs;
5. and `MapQueryAltitude` (GROUNDZ-F4) **skips the prop branch entirely when plane == 0**,
   returning the raw terrain height underneath the staircase.

That is the ankle-deep sink, from wire to render, with no inference left in it.

**It is bounded, which is why it took a parked body to see.** While the player keeps moving the
follow re-paths and every new order carries a fresh plane. The stale word only survives when the
hostile arrives on a different plane and everything then stands still — exactly the operator's
scenario, and exactly what a scripted route ending in a hold reproduces.

**The fix is one condition, inside the existing message vocabulary:** re-path when the MOVER'S
OWN PLANE CHANGES, not only when the player has moved. That sends one more `0x002A` carrying the
corrected `(dest, cur)` and needs no new message and no deviation from retail's shape. It is a
fourth default in two days, so it is registered here rather than shipped in the same breath as
the run that found it.

**Registered next:** `GROUNDZ-Q5` — ship the plane-change re-path, with `--no-plane-repath` as
its revert and this run's 32.5 u as the number it has to move.

