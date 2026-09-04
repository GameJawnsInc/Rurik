# RUN-1zAO — catch the lock with the fence column reading

**Registered before launching.** `MOVECODE-1z-ao`. Up to four runs, stopping as
soon as one **locks with a valid tape** — the point is one good specimen, not a
rate.

## 1. The question

§1z-am established that the swallowed `0x0047` is real, terminal, and **not**
caused by a lead maturing before its release. REALFIX §0.11's surviving account
is two-stage: a snap clears `clientControlled` (**stage 1**), composed with a
click-walk regime in which *"releases are ignored, no `0x0047` is emitted, and the
keyboard walk-start applier — the only fence re-armer — never runs"* (**stage 2**).

§1z-am could not test that, because the only fence signal available was
`lead_clip_why == "fence-shut"` — **our own flag**, uncleared *because* the reports
stopped, i.e. the same silence read from the server's side. §1z-an put the
client's own `clientControlled` dword on `agenttap` and §1z-an.6 verified it live.

**So: in a run whose stop reports go terminally silent, what does the client's own
fence do?**

## 2. Why this configuration, and it is deliberately the KNOWN-BAD arm

`stopcensus` over every scripted lead run says the **script** decides the exposure:

| script | runs | locked |
|---|---|---|
| `WSWQESW` (RUN-1zAH's long legs) | 13 | **6** |
| `WSWSQEWSDWSQE` (RUN-1zAJ's oscillating route) | 5 | **0** |

So the route is RUN-1zAH's. And within it, the arm attributable from the headers
is arm **C**: RUN-1zAH's four runs read T-healthy, C-healthy, T-healthy,
**C-LOCKED**, which is §1z-ai's *"the persistent lock reproduced in arm C only"*.
The eight older `WSWQESW` runs predate `STATIONARY_WAIVER` entirely and are arm-C
equivalent; five of them locked. Pooled, the arm-C-equivalent lock rate is
**6 of 10**.

**This run therefore uses `--no-repin-stationary-waiver`, the KNOWN-BAD revert,
chosen to PROVOKE the defect rather than to score the fix.** It is not the shipped
default and nothing here is evidence about the shipped default's safety. At 60% a
run, four runs miss a lock about 2.6% of the time.

## 3. THE PREDICTION, and it can fail

Registered before launching, per the probe rule. On a run that **locks**
(`stopcensus` trailing silence ≥ 2):

| | expected |
|---|---|
| **P1** | the player's fence **SHUTS at or before the lock onset** — the last leg that reported a stop |
| **P2** | and **STAYS shut for the whole silent tail**: no `shut → open` transition after the onset, while stops go on being missing |
| **P3** | the same run's **healthy prefix** shows at least one shut→open **re-arm**, as RUN-1zAN's healthy run did (shut 21.44 → open 23.91) — so the difference is the *re-arm*, not the shut |

**REFUTED IF** — and these are live possibilities, not formalities:

- **the fence is OPEN through the silent tail.** Then `clientControlled` is not
  the gate on the stop report, §0.11 stage 2's stated mechanism is wrong, and the
  suppression has another cause. This is the strong refutation.
- **the fence re-opens during the tail and the stops stay missing.** Same
  conclusion: the walk-start applier ran and the reports still did not come.
- **the fence never shuts at all in a locked run.** Then stage 1 did not happen
  and the lock is not §0.11's object.

**P3 failing alone is weak** — a run with no re-arm in its prefix is uninformative
about the contrast, not a refutation.

## 4. EXPOSURE FLOOR and ABORT

- **A scoreable specimen is a run that (a) LOCKS, (b) has a tape whose player
  fence reads non-`unread:` on ≥ 90% of samples, and (c) whose HATCHER control
  reads `shut` on 100%.**
- **ABORT on (c):** a tape whose Hatcher ever reads `open` is void — the reader is
  on the wrong record — and is not interpreted, per §1z-an.3.
- **If four runs produce no lock, the campaign measured NOTHING about the lock.**
  That is the honest outcome and gets written as one; it is not evidence that the
  fence stays open.

## 5. The runs

**Announced before launching — the machine is shared and `Gw.exe` takes focus.**

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress; the script opens with `wait:3` and the character
> stands still deliberately. **Each run ends on its own — ~75 s from launch to the
> window closing — and nothing is left parked.** Up to four in sequence.

**Terminal A, per run** (start first; it waits for a client in a map):

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

**Terminal B, per run — ARM C, the known-bad revert:**

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 S:4 W:5 Q:3 E:3 S:4 W:4" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead --no-repin-stationary-waiver"
```

RUN-1zAH §4's command verbatim, plus the revert flag. `--exe` is not optional
(every address in this arc is build 38797).

## 6. Scoring

Per run: `stopcensus.py` for the lock verdict, then `agenttap`'s own fence block
for the control and the transitions. On the first valid locked specimen, join the
fence transitions to the leg boundaries and to the gamesrv `0x002C` / `0x003D`
rows — the same cross-check RUN-1zAN passed to one sample.

**What this cannot settle even on success.** n = 1 locked specimen on one route
and one build. It can *refute* §0.11 stage 2 outright; confirming it would be one
observation consistent with the account, not a proof of the mechanism.
