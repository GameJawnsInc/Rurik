# MOVECODE-R1-B1 / R1-B2 — the runsheet for the two desk fixes

**Two arms, run SEPARATELY.** Both flags widen the same funnel and they are sequential
gates, so a combined run cannot attribute an outcome to either. `CLAUDE.md` says one
change per test and this is what that costs: two walks of about six minutes.

**The baseline for both is the K2 arm** — `vault/research/movecode/k2/`, already
captured, same map and operator. Largest displacement **446 u**, total **1,101 u**,
3 displacements, 18 grants, sync copy 89.3% in motion.

Each arm therefore differs from the baseline by **exactly one flag**.

| arm | flags | what it unlocks |
|---|---|---|
| baseline (done) | `--click-echo` | echo a click refused for STALENESS |
| **B1** | `--click-echo --answer-kbd-click` | clicks arriving while the keyboard latch is armed |
| **B2** | `--click-echo --echo-any-refusal` | echo a click refused for GEOMETRY |

**Every command here is `python` or `powershell`.** The K1 runsheet used bash `cp` and
`mkdir -p` and died at the owner's terminal mid-run.

---

## 1. What is predicted, and what refutes it

Both arms are scored on the number that survives all four configurations: **largest
displacement**, printed by `readhook`.

| quantity | K2 baseline | both arms predict | where it prints |
|---|---|---|---|
| largest displacement | **446 u** | **≤ 446 u** | `readhook` — `largest` |
| displacements within 300 u of spawn | **0** | **0** | `readhook` — the coordinates |
| clicks answered | 8 | **rises** | `keepalivelog` |

**REFUTED IF the largest displacement exceeds 446 u, or if any displacement lands
within 300 u of spawn** — spawn on map 280 is `(−6036.0, −2519.0)`. Read the
coordinates, not just the magnitudes.

**B2 has a second, pre-registered outcome that is NOT a refutation: more no-clip.**
Every metric above is blind to it by construction (§1n.2 — no-clip is a legal walk at
288 u/s with both `m_point` and its `+0x58` stamp advancing), and §1p.11 measured that
7 of K2's own 8 echoed clicks were already granting blocked lines. **The operator's
report is the instrument for this and nothing else is.** Record it as its own row.

---

## 2. THE EXPOSURE FLOORS, AND THEY NEED DIFFERENT WALKS

This is the part to read twice. **The two arms need walking patterns the K2 run did not
contain**, and a walk that does not produce the situation measures nothing — which is
the mistake §1l made and reported through anyway.

### B1 — "click while the keyboard latch is armed"

The latch is armed by a `0x003D` with a non-zero `movementType` and **cleared by a
`0x0047`**, which is what a stop sends. So a click after you have stopped does **not**
test this arm.

> **Hold a movement key and click while still holding it.** Do not release first.
> Repeat at least **five** times, spread across the walk.

**Floor: ≥ 3 grant_verdict rows FIRED with a non-null `keyboard_age` ≤ 3.0 s.**
`keepalivelog` prints this as the `R1-B1:` line. That pair is unreachable with the flag
off, so it is an exact signature of the arm.

### B2 — "stop, then click immediately at something that is not a straight shot"

A geometry refusal needs the position to be **fresh** (a report inside 1.0 s) *and* the
straight line to fail. During pure click-walking the client sends no position at all,
so every click is `geo-stale` and this arm never fires. The report has to come from the
keyboard.

> **Keyboard-walk, stop, then click within about a second** at a point behind a prop,
> around a corner, or across the map. Prefer the **north-east** of map 280
> (y ≈ 6,900–8,500): §1i.5 found 4 of 4 geometry refusals there and §1p.11 found two
> granted points our mesh does not contain at all.
> Repeat at least **five** times.

**Floor: ≥ 3 `click_verdict` rows with `echo_any_refusal: true` AND a reason other than
`geo-stale`.** `keepalivelog` prints this as the `R1-B2 ECHOES` line.

**AND AN ECHO IS NOT A GRANT — this is the arm's main way to look busy while measuring
nothing.** The echo decision is taken in the geometry block; `_grant_verdict` runs
about eighty lines later, so **rule 1 can still drop an echoed click** as
`locally-moving`. That is why the recipe says *stop, then click*: clicking while still
holding a key arms the latch and the echo dies downstream, counted as exposure and
never reaching the wire. `keepalivelog` warns when it sees both, but the walk is what
prevents it.

---

## 3. Preconditions

```bash
python toolkit/authsrv/test_clickecho.py
```

```bash
python toolkit/authsrv/test_position_trust.py
```

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **25**, **224** and **81**. The DLL is unchanged since K2, so no rebuild is
needed — but if `attach.py` refuses with *"older than sites.h"*, close the client (the
hook does not unload itself) and rebuild:

```bash
powershell -ExecutionPolicy Bypass -File toolkit/clientscan/movehook/build.ps1 toolkit/clientscan/movehook/movehook.c
```

---

## 4. ARM B1

**Announce the launch.** The client fights for input focus and the machine is shared.

**Shell 1.** `--exe` is not optional — `session.py` defaults to the newest build and
every movehook address is **38797**. `--hold 900` bounds the window; without it the
client parks on the owner's screen indefinitely.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --answer-kbd-click --map 280"
```

Expect **both** banners in the gamesrv log. If either is absent the flag did not reach
the game instance and the arm is void:

```
[map] --click-echo ON (MOVECODE-K2). ...
[map] --answer-kbd-click ON (MOVECODE-R1-B1). A click no longer dies because the
      player is ALSO on the keyboard; it falls through to the rate floor like any
      other click.
```

**Shell 2**, once the character is in the world and standing at the run's start:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6 --out vault/research/movecode/r1b1
```

Then walk **§2's B1 pattern** — hold a key, click while holding, at least five times —
plus some ordinary click-walking and keyboard walking for comparison. Then:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

**Read it before relaunching anything** (`keepalivelog` takes the newest gamesrv log by
mtime):

```bash
python toolkit/clientscan/movehook/keepalivelog.py
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r1b1/movehook.bin
```

---

## 5. ARM B2

Same shape, one flag different. **`--echo-any-refusal` requires `--click-echo` and the
server refuses to start without it** — that is deliberate: alone it is one inert term
inside `CLICK_ECHO and (...)`, and a run launched on it would file a capture of the
shipped policy under this arm's name.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--click-echo --echo-any-refusal --map 280"
```

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6 --out vault/research/movecode/r1b2
```

Walk **§2's B2 pattern** — keyboard-walk, stop, click within a second at something that
is not a straight shot, in the north-east. At least five times.

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

```bash
python toolkit/clientscan/movehook/keepalivelog.py
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r1b2/movehook.bin
```

---

## 6. The side-by-side

The baseline, for both arms:

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/k2/movehook.bin
```

Map 280's mesh differential should be **unchanged** — neither flag touches geometry, so
a difference here means the walks were not comparable:

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r1b1/movehook.bin
```

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/r1b2/movehook.bin
```

---

## 7. Traps

* **Spawn is `(−6036.0, −2519.0)`.** The refuting clause is about distance to *that*
  point.
* **`--map auto` refuses on these captures** (two meshes tie at 95.0%). Pass
  `--map 0x287B3`.
* **The version record says `map_id 148`** — the client's connect parameter, not where
  the session ran. The spawn coordinate is the tell.
* **A reseed is not a warp.** Score displacements, not the reseed count.
* **The DLL does not unload.** Close the client before any rebuild.
* **`readhook` with no `--bin` reads `vault/research/movecode/movehook.bin`**, which is
  byte-identical to the **K1** arm's capture. Always pass `--bin`.
* **Do not pass `--host`.** See `RUNBOOK.md`.

---

## 8. If an arm is refuted

Add it to the graveyard block in `authsrv.py` beside `HEADING_GRANT`,
`CLIENT_ENDPOINT`, `KEEPALIVE_GRANT` and `CLICK_ECHO` **with its numbers attached**, and
write the section in the shape §1i–§1p use. A refuted candidate carrying its
measurement is worth more than a deleted one.

**And if both pass, the third arm is the combined one** — `--click-echo
--answer-kbd-click --echo-any-refusal`. It is worth running only then, because the two
flags compose into a case neither reaches alone: a click made *while keyboard-walking*
at a geometrically blocked point needs B1 to survive rule 1 and B2 to be answered at
all.
