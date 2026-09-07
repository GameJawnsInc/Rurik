# RUN-FEEL2 — the owner's own session under the wall slide and F11's reach slack

**Registered before the session.** `main` at `7edcfb8`. RUN-1zCE confirmed MOVECODE-1z-ce
(the wall slide) and the F11 reach slack on the scripted climb; what a script cannot say is
how a body sliding along a wall FEELS with world-0 running beside it instead of 111 u behind,
and whether the parked Hatcher now looks right to an eye. Hand-driven, no walk script, enemy
on and survivable, the tape recording both copies of both bodies.

## The two arms, one question each

**A — walls.** Run along walls with the Hatcher chasing: the stairs' right side on the way
up, and any fence or cliff face on the flat. Press INTO the wall while you run so the body
slides along it (that is the case: the client reports the key's direction, the body goes the
wall's).

- **A1:** *does your own body ever jerk, stall, or get pulled while sliding along a wall?*
  Prediction: no — the slide lead only moves the client's sync copy; the fence stays open and
  the body is the client's. REFUTED by any yank or stall you can reproduce.
- **A2:** *when you stop against a wall with the Hatcher behind you, does it park beside you
  at melee range?* Prediction: yes, where Q5 already looked right on the flat.

**B — the top of the stairs.** Lead it up the stairs and STOP on the landing at the top, then
stand still for a few seconds.

- **B1:** *is the Hatcher standing on the stone beside you, feet on the surface?* Prediction:
  yes — the 52 u sink you photographed is gone (R3 and 1zCE run 2 both read the client's
  plane 0 and a live height). REFUTED if it is in the ground again.

**Skip:** going around the wall at the top into the pocket. The Hatcher will still cut
straight through it and may stand below you at the pocket's floor — that is NPCTRACK-Q9, our
wire carries no corridor yet, and it is a scripted run of mine, not yours.

## The run

Two PowerShell windows in `C:\gd\Rurik`. Start the tape first; it waits for the client.

```powershell
python toolkit/clientscan/agenttap.py --agents 1,10 --seconds 240 --wait 300 --out vault/research/movecode/feel2-agenttap.jsonl
```

```powershell
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --enemy --hold 200 --game-args "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"
```

The stack comes up, the client logs itself in and spawns (about 25 s, HANDS OFF until "body
is in the map"), then the keyboard is yours for 200 s; the session tears itself down after.
The Hatcher is 316 u from the spawn and will come to you. Answer A1, A2 and B1 in your own
words; the tape and capture score the rest.

---

## RESULT — the owner's session, 2026-09-06 23:51 (capture `authsrv-20260906T235141-c1`, tape `movecode/feel2-agenttap.jsonl`, 81 s, 108 accepted reports, 29 wall-slide grants)

| | in their words | the tape |
|---|---|---|
| **A1** | *"no, feels good"* | world-0 vs the drawn body, moving-only p50 97 u over a hand-driven session of turns and presses (the scripted climbs read 14–20); one `0x002C` at 71.06 s, a predicted budget-red snap pre-empted at the top of the stairs as the body crossed onto plane 0; fence `open` and `shut` both seen; 21 climb grants, 13 of them wall-slides ≥ 50 u, 0 zero leads. **MET.** |
| **A2** | *"yes but sometimes still falls through the stairs onto the ground below or is slightly sunken at least"* | **half MET, half a new defect, found and fixed (1z-cf).** The Hatcher parked beside you at melee range (F15's shape) — but on four of the climb's parks its copy stood **25, 96, 0 and 17 u EAST of the stairs' right edge**, off any trapezoid, plane word 29, and was drawn **67–170 u below you** on the terrain under the stairs. Parked ON the edge line it reads only the slope (p50 +31 u below a player 80 u up the stairs); 2–30 u off it reads +145. |
| **B** | *"yes"* | the terrace park at 18.3 s: the correction `29 -> 0` went out, the Hatcher's client plane 0 through the exposure, height live. **MET.** |

**A2's cause is ours, and it is not the mesh and not the plane word.** The follow orders the
hostile to *"the player at (10694, 8458)"* at 9.03 s while your body stood at (10644, 8550)
on the stairs' edge — 145 u east of the stairs, inside the wall. That point is the server's own
position MODEL, `state["pos"]` advanced between reports along your reported heading, and
`clip_to_walkable` had suspended its collision because the model's standing point — your
report, 0.0–0.4 u outside the stairs' side, the edge class the client always reports from on a
slide (1z-bd.2) — failed exact containment: *"standing outside the navmesh disables the
check"*, a door built for a spawn on uncovered ground. 25 of the session's 108 reports were in
that class, and after each the model walked the raw heading (due east or south-east) into the
wall for up to 136 u before the next report pulled it back; the follow aimed there, the
client's copy parked there, and the client drew it on the terrain below. The lead had had the
same two doors closed since 1z-bg and 1z-ce; the model had neither.

**Fixed, MOVECODE-1z-cf:** `clip_to_walkable` takes the lead's doors — an origin the mesh holds
within SEAM_TOL clips on the plane `plane_near` names (an ambiguous sliver stands), and a leg
the clip stops at the body slides to the wall's next vertex. Replayed through the receive arm
on the real map, the session's edge-class reports now give a model leg **up the wall at 44.3°
to the same vertex the lead names** (245 / 263 / 170 u) instead of 136 u east into it.
`MODEL_ORIGIN_SEAM` / `MODEL_WALL_SLIDE`, reverts `--model-origin-exact` /
`--no-model-wall-slide`; `test_kbdsync` §19 (+9, floor 153 → 162). RECONSTRUCTION on the client
until the next stairs session: the prediction is no park more than 5 u off the stairs' edge
while you climb, and the "falls through" gone; the "slightly sunken" that remains is 1z-ca's
ankle sink on stair geometry, the client's own height resolution, unchanged by anything here.
