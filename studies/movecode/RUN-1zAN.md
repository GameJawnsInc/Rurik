# RUN-1zAN — does the AgTrack fence column READ, live?

**Registered before launching.** One run, not four: this is an INSTRUMENT
VERIFICATION, not a re-score of the waiver. `MOVECODE-1z-an` wired
`clientControlled` onto `agenttap` and verified the wiring against fake memory
(15 checks); what no test can establish is that this process, on this build,
reads a plausible fence at run time — and what the extra reads cost a tape
already delivering ~9 Hz of the 30 it asks for (§1z-ak.7).

Ident `MOVECODE-1z-an` (the run that closes it). Arm **T only** — the shipped
default, waiver ON.

## 1. The question, and it is one question

**Does the fence column read a plausible `clientControlled` from a live client,
and what does it cost the sample rate?**

Everything else this tape records is already understood; the lead is `--kbd-lead`
so the fence has something to do, not because this run scores the lead.

## 2. THE PREDICTION, and the refutation conditions

Registered before the launch, per the probe rule.

| | expected |
|---|---|
| **P1 — the negative control** | the **Hatcher's** (agent 10) fence reads `shut` on **100%** of samples that read at all. Only the local player's agent is client-controlled — `0x00605F10` has exactly two callers, both in the ChCliBase local-command block. |
| **P2 — the player reads** | agent 1's fence reads `open` or `shut` (never only `unread:`) on a **large majority** of samples. |
| **P3 — it moves** | the player's fence shows **at least one transition** across the run. §1z-aa measured every server `0x002C` shutting it (12/12) and a keyboard walk-start re-arming it (7/8); this route sends `0x002C`s and walks. |
| **P4 — the rate** | the tape stays within a factor of ~2 of the fence-less **9.1 Hz** (§1z-ak.7). |

**REFUTED IF:**

- **P1 fails — the Hatcher ever reads `open`.** Then the reader is indexing the
  wrong record and the player's column is worth nothing. `summarise_fence`
  prints `CONTROL FAILED` itself. **This is the abort: stop, do not interpret
  the player's column, and do not write a finding from it.**
- **P2 fails — the player's fence is `unread:` throughout.** The column is
  reading nothing; the `unread:` reason names which precondition refused
  (`state-array-null`, `state-count-implausible`, `id-out-of-bounds`,
  `agent-id-mismatch`, `record-unreadable`) and that reason is the finding.
- **P4 fails badly — under ~4 Hz.** Then the fence costs more than it is worth
  on this reader and `--no-fence` becomes the default recommendation. Recorded,
  not fatal.

**P3 failing is NOT a refutation of the column.** A fence that reads a constant
`open` for 75 s is a legitimate reading of a run in which nothing shut it; it
would mean this route did not exercise the transition, not that the reader is
broken. Say so rather than reaching for it.

## 3. EXPOSURE FLOOR, so a run that measured nothing cannot pass

- **≥ 200 samples** in the tape (the fence-less tapes on this route run
  550–650 over 60 s; 200 is the floor at which a rate collapse is still
  scoreable rather than a null).
- **≥ 1 sample** in which the player's fence is not `unread:`.
- The gamesrv capture must reach the map (`session.py`'s own spawn checkpoint).

**Below any of these the run measured nothing and is not evidence either way** —
it is re-run, not written up.

## 4. The run

**Announced before launching — the machine is shared and `Gw.exe` takes input
focus.**

> ### ⚠ HANDS OFF THE KEYBOARD ONCE THE CLIENT IS UP
>
> `--walk` drives every keypress; the script opens with `wait:2` and the
> character stands still — it is **not** waiting for anyone. A helpful press
> produces the double-driven regime RUN-1zT's first attempt hit (720 u of travel
> no script asked for). **The run ends on its own: ~75 s from launch to the
> window closing, and nothing is left parked.**

### Pre-flight

```powershell
python toolkit/clientpatch/dhbuild.py
```

Must end `Every build is where it belongs.` — the loopback build carries OUR
parameters and may only be pointed at our server.

```powershell
python toolkit/clientscan/test_agenttap.py
```

Must print `ALL CHECKS PASSED (15 checks)` — the wiring this run exists to
verify live.

### Terminal A — the tap (start first; it waits for a client in a map)

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 75
```

### Terminal B — the session, ARM T (shipped default, waiver ON)

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:2 W:1.5 S:2 W:1.5 S:2 Q:1.5 E:1.5 W:1.5 S:2 D:1 W:1.5 S:2 Q:1.5 E:1.5" --hold 8 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 --kbd-lead"
```

RUN-1zAJ's walk string and flags **verbatim** — the oscillating route that stays
inside ~300 u of spawn and produced 9–14 clear leads per run. `--exe` is not
optional (every address in this arc is build 38797); `--enemy-hit 0.02` keeps the
Hatcher chasing without killing the player.

## 5. Scoring

`agenttap`'s own summary prints the fence block: both columns, the control
verdict, every player transition, and the `gate_reach` tally. Then:

```powershell
python studies/movecode/review/stopcensus.py
```

— because this run adds a lead capture to the corpus and the terminal-silence
signature is free.

**What this run does NOT settle.** It is n = 1 on one route and it scores the
INSTRUMENT. Whether the fence explains the swallowed `0x0047` needs the column
joined to a locked run, and §1z-am's own census says only 6 of 17 lead runs lock
— this one may well be healthy, which is a fine outcome for an instrument check
and no evidence at all about the lock.
