# MOVECODE-K2 — the runsheet for the click echo

**One arm.** The baseline is **K1 arm A**, already captured at
`vault/research/movecode/k1-treatment/` — same map, same operator, same walking style.
The prediction is [FINDINGS.md](FINDINGS.md) §1m.4 and was registered before this run.

**Every command here is `python` or `powershell`.** The K1 runsheet used bash `cp` and
`mkdir -p` and died at the owner's terminal mid-run; `python …` lines work in any
shell, which is what `CLAUDE.md` already says.

---

## 1. What is predicted, and what refutes it

Against K1 arm A:

| quantity | arm A | K2 predicts | where it prints |
|---|---|---|---|
| `geo-stale` clicks answered | **0 of 4** | **all of them** | `keepalivelog.py` |
| grants to the sync copy | 13 | **> 13** | `readhook` — `took N setter call(s)` |
| sync copy idle | **74.3%** of its span | falls | `readhook` — `in motion … of …` |
| displacements within 300 u of spawn | **2** | **0** | `readhook` — the coordinates |
| largest displacement | **5,970 u** | **< 5,970 u** | `readhook` — `largest` |

**REFUTED IF the largest displacement exceeds 5,970 u, or if any displacement still
lands within 300 u of spawn** — spawn on map 280 is `(−6036.0, −2519.0)`. The second
clause is the operator's own report turned into a number, and it is the one that
matters.

**EXPOSURE FLOOR: ≥ 3 `click_verdict` rows with `click_echo: true`.** Fewer means you
did not click-walk enough for the flag to act, and the arm measures nothing — re-run,
do not conclude. K1 arm A failed exactly this floor with 2 fires, and §1l led with its
result anyway. Do not repeat that.

**A THIRD OUTCOME THAT IS NOT A REFUTATION.** If the spawn warps stop but the character
starts cutting through railings on clicked routes, that is a *measured* harm of
answering clicks arriving as predicted (`authsrv.py`, the staircase note), and it
argues for `--router`, not against K2. Report it as its own row.

---

## 2. Preconditions

```bash
python toolkit/authsrv/test_clickecho.py
```

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **19** and **81**. The DLL is unchanged since arm A, so no rebuild is needed —
but if `attach.py` refuses with *"older than sites.h"*, close the client (the hook does
not unload itself) and rebuild:

```bash
powershell -ExecutionPolicy Bypass -File toolkit/clientscan/movehook/build.ps1 toolkit/clientscan/movehook/movehook.c
```

---

## 3. The run

**Announce the launch.** The client fights for input focus and the machine is shared.

**Shell 1.** `--exe` is not optional — `session.py` defaults to the newest build and
every movehook address is **38797**.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --map 280"
```

Expect this banner in the gamesrv log. If it is absent the flag did not reach the game
instance and the arm is void:

```
[map] --click-echo ON (MOVECODE-K2). A click refused for STALENESS is now answered
      with the VERBATIM clicked point; geometry refusals still refuse.
```

**Shell 2**, once the character is in the world and standing at the run's start:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6 --out vault/research/movecode/k2
```

**Walk the sequence that produced the warps**, because that is what this is scored
against — it is not "walk around for five minutes":

1. **Click-walk several long legs.** Clicks only, no keyboard. This is the mode where
   the client reports nothing and every click was previously refused.
2. **Then press a movement key.** In arm A this is the moment the body snapped to
   spawn, twice. Do it after 3–4 clicked legs, as you did before.
3. Repeat that pattern several times, and **stand still for a few seconds after
   arriving** at least twice.
4. Some ordinary keyboard walking at the end, for comparison.

Then:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

---

## 4. Reading it — run both, and run them before relaunching anything

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/k2/movehook.bin
```

```bash
python toolkit/clientscan/movehook/keepalivelog.py
```

`keepalivelog.py` reads the newest gamesrv log by mtime, so run it **before** any
further launch. It prints the click-refusal census — that is where the exposure floor
is read, and where `geo-stale` answered-vs-refused shows up.

The baseline, for the side-by-side:

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/k1-treatment/movehook.bin
```

Map 280's mesh differential should be **unchanged** — K2 does not touch geometry, so a
difference here means the walks were not comparable:

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/k2/movehook.bin
```

---

## 5. Traps

* **Spawn is `(−6036.0, −2519.0)`.** The refuting clause is about distance to *that*
  point; read the displacement coordinates, not just the magnitudes.
* **`--map auto` refuses on these captures** (two meshes tie at 95.0%). Pass
  `--map 0x287B3`.
* **The version record says `map_id 148`** — that is the client's connect parameter,
  not where the session ran. The spawn coordinate is the tell.
* **A reseed is not a warp.** Score displacements, not the reseed count. §1l is the
  worked example of getting that wrong.
* **The DLL does not unload.** Close the client before any rebuild.
* **Do not pass `--host`.** See `RUNBOOK.md`.

---

## 6. If it is refuted

Add K2 to the graveyard block in `authsrv.py` beside `HEADING_GRANT`,
`CLIENT_ENDPOINT` and `KEEPALIVE_GRANT` **with its numbers attached**, and write §1n in
the shape §1i–§1m use. A refuted candidate carrying its measurement is worth more than
a deleted one — which is why the other six are still there, and why K2 was written
against their epitaphs rather than around them.
