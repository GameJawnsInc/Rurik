# NPCTRACK-R3 — the stairs under the hook: WHO re-targets the hostile's sync copy between our orders?

**Registered before the run.** `NPCTRACK-R3`. Scores **NPCTRACK-F13**'s mechanism question. The
tapes say the Hatcher's sync `m_targetPoint` changes 19–24 times a run with no server order
within 0.35 s, at a median 0.56 s cadence, only while `+0x98` names the player, landing on or up
to ~0.5 s of its velocity ahead of the player's world-0. ANIMREF-RE §38.2's static read says
*"nothing reads `+0x98` to fetch the followed agent's current position"*. One of them is wrong,
and a hook on the shared setter names the caller.

**The instrument** is `movehook` (MOVECODE-B2), attached after the client is in the world: it
records every entry to the setter `0x00602A40` and the bake `0x005FE950` with `ecx` (the agent
object), the agent id, the return address and the point blocks. The wall-press capture (1zbr)
had no hostile, so it holds no record for agent 10; this run has one.

## 1. Exposure

| | floor |
|---|---|
| hook controls A and B | both FIRED (readhook refuses otherwise) |
| setter records with `id=10` on the SYNC copy | **≥ 20** |
| a chase with ≥ 3 of our follow orders while the player walks | ≥ 1 |

## 2. Predictions

**P1 — THE LOCAL RE-TARGET HAS A NON-WIRE CALLER.** Among the Hatcher's sync-copy setter
records, **≥ 10 return to an address that is neither `0x005FD918` (the `0x0029` handler) nor
`0x005FD930`/its return (the `0x002A` handler)**, and those records sit on the ~0.5 s cadence
between our orders. **REFUTED IF every sync setter record for agent 10 returns to a wire
handler** — then the tape's target changes were our own orders mis-joined (the join is
`wall_unix` on both sides; a constant offset would show as a constant lag), and §38.2 stands.

**P2 — recorded, not scored.** The non-wire caller's return address, and whether it is the
follow branch of the async tick (`0x00600140`) or something else; the bake's `arg2`
(`isWaypoint`) on those records; the point block written (does it equal the player's world-0,
or world-0 plus a velocity term).

## 3. The run — scripted, agent-driven

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --walk "wait:3 W:5 shot:1 S:4 shot:1 W:5 Q:3 E:3 S:4 W:4" --hold 20 --shots 2.0 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 180 --wait 300 --out vault/research/npctrack/r3-agenttap.jsonl
```

and, once `Gw.exe` is up and in the map (about 25 s after the launch):

```powershell
python toolkit/clientscan/movehook/attach.py --minutes 1.6 --out vault/research/npctrack/r3-hook
```

## 4. Scoring

`python toolkit/clientscan/movehook/readhook.py --bin vault/research/npctrack/r3-hook/movehook.bin --dump 99999`
filtered to `id=10` setter/bake records, grouped by return address and by `ecx` (the two copies
of agent 10 are two objects; the tape's `ptr` fields name them), joined to the capture's sends by
the hook's tick clock against `wall_unix`.

---

## RESULT — RAN 2026-09-06 12:56 under the hook, agent-driven. **P1 REFUTED: no non-wire caller on the sync copy. F13 is withdrawn, §38.2 stands.**

The hook was attached 24 s after the client appeared and armed for 1.6 min; the client exited
with the harness at ~12:57:25, so the capture is the 12:56:58 snapshot — **4,644 records over
~58 s of the route** (no `movehook.txt` sidecar, so the controls are unknown; the counts below
are consistent with the capture's own 26 wire orders to agent 10 in that window). Tape
`r3-agenttap.jsonl` 799 of 799.

**The two objects, named by the tape's pointers:** sync `0x27ADFD38`, async `0x27ADDAA0`.

| site | on the SYNC copy | on the ASYNC copy |
|---|---|---|
| setter `0x00602A40` | **26, all returning to `0x005FD9B9` — the `0x002A` handler** | 41, all to `0x00604A48` (AgTrack: the handoff) |
| bake `0x005FE950` | 26, from the setter | 41 from the setter + 3 from `0x0060193B` (the path solver, waypoint re-bakes) |
| teleport `0x006020B0` | 15 from `0x006025AB` (our `0x0028`): **13 on a parked copy, 2 on a moving one**; 13 from `0x0060181C` (the resolver's disc park); 1 from `0x00600333` (the tick's arrival) | 15 from the halt, 12 tick arrivals, 9 from `0x0060189E` |
| tick | 17 + 10 | 24 + 32 |

**P1 REFUTED as registered, and that was the point of registering it.** Every setter call on the
sync copy is our own `0x002A`. The "unexplained" target changes F13 counted were our orders
seen through a backward-only join window against send stamps that can trail the client by up to
67 ms; with a symmetric window the count is 0 on all three tapes. **P2 recorded:** the non-wire
caller that does exist is on the ASYNC copy and is AgTrack's handoff `0x00604A48`, the mechanism
§37.2 already names; its bakes carry `isWaypoint = 0` except the path solver's three.

**A free third measurement of Q1** off this run's tape: **15.7 u** at the halt's own instant
(6.7 and 11.8 on the two earlier runs; 46–68 on the old arm), 6 of 22 over 40 u (27 %), the model's
parks 13.8 u from the client's copy — with an `int3` hook on five hot sites slowing the client,
which is the fairest reading of why it is the widest of the three.

**And the client-side reading of P3**, which the tape cannot give at ±70 ms: our halts landed on a
parked sync copy **13 of 15 times** in the hook's window and cut a walk twice. The tape's
"walking at the halt" column read 4 of 22 on this run; the two are consistent once the stamp lag
and F8's 50 ms halt-to-follow gap are allowed for, and the hook is the instrument from here.
