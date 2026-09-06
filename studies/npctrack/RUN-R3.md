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
