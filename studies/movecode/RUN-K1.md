# MOVECODE-K1 — the runsheet for the keep-alive re-grant

**Two arms, one session, treatment FIRST.** The flag is `--keepalive-grant` and it is
off by default. The prediction it is scored against is
[FINDINGS.md](FINDINGS.md) §1k.3 and was registered before this run existed.

Read §1 before launching anything. This is the **sixth** candidate in a family that
killed five, and four of those five improved one number while making the warp worse.

---

## 1. What is predicted, and what refutes it

Scored with `readhook`, which separates the two world copies by object address — no
earlier candidate had an instrument that could do that, and §1i.1 records what
pooling them cost.

| quantity | run 5 (control) | K1 predicts | where it prints |
|---|---|---|---|
| twin idle time | **100.2 s** of 207.6 s | falls toward the local copy's **37.8 s** | `in motion … of …` |
| twin grant gaps, p50 | **1.78 s** | falls toward retail's **0.82 s** | `grant gaps s:` |
| reseeds past the 299.33 cut | **11 of 14** | falls toward **0** | `over 299.33` |
| **reseeds that DISPLACED the player** | **2** (691 u, 511 u) | **0** | `following a RESEED:` |

**REFUTED IF the reseed count does not fall, OR if any displaced reseed appears that
the control arm did not have.** The second clause is the one that matters.
`--client-endpoint` met both terms it was designed for and went from 5.7 to 14.6
jumps/min. **A fall in idle time with no fall in reseeds is a REFUTATION, not a
partial win.**

**TWO EXPOSURE FLOORS, and neither is a result.** Zero exposure is not a null:

* **The control arm must produce ≥ 5 reseeds past the cut.** Below that the treatment's
  zero is a quiet session, not an effect. Re-run; do not conclude.
* **The treatment arm's server log must show `keepalive_verdict` rows with
  `fired: true`.** If none fired, the flag never ran and the arm measures nothing —
  check `reason` on the rows that are there (`no-report`, `report-rejected`,
  `unseeded`, `rate-limited`, `twin-walking`, `in-band`), because each names a
  different thing to fix.

---

## 2. Preconditions

Run these before touching the game. A red test names the broken thing; the client
says `Code=058` thirty seconds later and tells you nothing.

```bash
python toolkit/authsrv/test_keepalive.py
```

```bash
python toolkit/clientscan/movehook/test_movehook.py
```

Expect **32** and **81**. Then confirm the DLL is current — `gensites.py` can
regenerate `sites.h` while the previous DLL is still LOCKED by a running client, so
the build fails with `LNK1104` and the `.dll` on disk keeps the OLD site set:

```bash
cd toolkit/clientscan/movehook && powershell -ExecutionPolicy Bypass -File ./build.ps1 movehook.c
```

`attach.py` refuses a DLL older than `sites.h`, so this is checked rather than
trusted — but building first saves a launch.

---

## 3. The run — TREATMENT FIRST, and the order is deliberate

**Announce the launch.** The client fights for input focus and the machine is shared.

The operator gets more fluent at walking the same route as the session goes on, and a
smoother walk flatters whichever arm runs second. Putting the **treatment first** makes
that bias work **against** the hypothesis. Do not reorder for convenience.

### Arm A — TREATMENT

**Shell 1.** `--exe` is not optional: `session.py` defaults to the *newest* build under
`vault/run/` and every movehook address is **38797**. A 38797 RVA in another build's
image points at the middle of some unrelated instruction and the `0xCC` goes in anyway.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--keepalive-grant --map 280"
```

Use the `=` form for `--game-args`. argparse reads a value starting with `-` as a
flag otherwise.

Expect in the gamesrv log:

```
[map] --keepalive-grant ON (MOVECODE-K1). Re-granting the player's own LAST REPORTED
      position, unclipped, when the sync copy is modelled parked more than 100 u away.
```

If that banner is absent the flag did not reach the game instance — the arm is void.

**Shell 2**, once the character is in the world and standing where the run starts:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6
```

**Walk for about five minutes**: long walks across open ground, a few clicks where
something is in the way, some keyboard walking, and — this is the case both of run 5's
real warps came from — **several stops where you stand still for a few seconds after
arriving**. Then:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

**File the capture before the next arm overwrites it:**

```bash
mkdir -p vault/research/movecode/k1-treatment && cp vault/research/movecode/movehook.bin vault/research/movecode/movehook.txt vault/research/movecode/k1-treatment/
```

### Arm B — CONTROL

Close the client (the DLL does not unload itself), then relaunch with the band set
out of reach. **The flag stays ON**: same code path, same verdict rows, same logging —
only the grant is disarmed. That is a tighter control than turning the flag off.

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 900 --game-args="--keepalive-grant --keepalive-separation 100000 --map 280"
```

Then attach, walk **the same route for the same length of time**, stop, and file it:

```bash
python toolkit/clientscan/movehook/attach.py --minutes 6
```

```bash
mkdir -p vault/research/movecode/k1-control && cp vault/research/movecode/movehook.bin vault/research/movecode/movehook.txt vault/research/movecode/k1-control/
```

---

## 4. Reading it — run BOTH, on BOTH arms

This is the step I failed to hand over after run 5. Every predicted quantity is in
the first command.

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/k1-treatment/movehook.bin
```

```bash
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/k1-control/movehook.bin
```

Map 280's mesh differential, which K1 does **not** address and which should be
unchanged between arms — a difference here means the arms were not the same walk:

```bash
python toolkit/clientscan/movehook/pathdiff.py --map 0x287B3 --bin vault/research/movecode/k1-treatment/movehook.bin
```

And the server side, for the exposure floor and the refusal census:

```bash
python -c "import json,collections,glob,os; p=sorted(glob.glob('vault/captures/gamesrv/authsrv-*-c1.jsonl'),key=os.path.getmtime)[-1]; rows=[json.loads(l) for l in open(p,encoding='utf-8')]; print(p); print('keepalive:',collections.Counter((r.get('reason'),r.get('fired')) for r in rows if r.get('kind')=='keepalive_verdict')); print('clicks:',collections.Counter(r.get('reason') for r in rows if r.get('kind')=='click_verdict')); print('0x0029 sent:',sum(1 for r in rows if r.get('kind')=='sent' and r.get('opcode')==41))"
```

Run that **after each arm**, before the next launch overwrites the newest log.

---

## 5. Known traps, all of them things that have already happened here

* **`--map auto` REFUSES on this capture** — two meshes tie at 95.0%. Pass
  `--map 0x287B3` explicitly. Map 280 is Isle of the Nameless; the version record in
  the server log will say `map_id 148`, which is the client's *connect parameter*, not
  where the session ran. The spawn `(−6036, −2519)` is the tell.
* **One agent id names TWO objects.** Never read a trajectory filtered on `id == 1`;
  `readhook` groups on the address and raises if you are about to. §1i.1.
* **A reseed is not a warp.** 14 reseeds and 2 displacements in run 5. Score the
  `following a RESEED:` line, not the reseed count alone.
* **The DLL does not unload.** Close the client between arms, or the rebuild fails
  with `LNK1104` and the second arm silently runs the first arm's site set.
* **`--keepalive-separation` on its own is refused**, deliberately — a run carrying
  only the override would look configured and change nothing.
* **Do not pass `--host`.** See `RUNBOOK.md`.

---

## 6. If it is refuted

That is a real outcome and the sixth in a row would still be worth having. The two
things to record are which of §1k.3's rows moved and which did not, and whether any
**new** displaced reseed appeared. Write it into FINDINGS as §1l with the same shape
§1i–§1k use, and add K1 to the graveyard block in `authsrv.py` beside `HEADING_GRANT`
and `CLIENT_ENDPOINT` **with its numbers attached** — a refuted candidate with its
measurement is worth more than a deleted one, which is why those two are still there.
