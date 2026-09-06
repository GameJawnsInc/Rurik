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

## RESULT — not yet run.
