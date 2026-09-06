# NPCTRACK-FEEL — the owner's own session on the F14/F15 tree: Q5, Q6 and Q3 in their words, joined to the tape

**Asked before the session** (the three questions the arc could not answer from a scripted
route): does the parked hostile stand where you expect (Q5); does the halt-and-refollow cadence
behind you while you run feel wrong (Q6); and lead the Hatcher around a wall so a wall sits
between it and you before the follow reopens (Q3). Enemy on, survivable, no walk script, the tape
recording both copies of both bodies. Server `main` at `b610bcf`.

**Ran 2026-09-06 15:48** — capture `authsrv-20260906T154850-c1` (63 s of sends; 40 follows,
22 halts, 1 plane correction, zero `0x002C`), tape `feel-agenttap.jsonl` (575 paired samples).

## The owner's answers

| | in their words | the tape |
|---|---|---|
| **Q5** | *"looks like real melee range"* | the disc parks at a standing player 62–79 u from world-0 (F15's shape: 8 of 8 inside the disc on R4, 36 of 37 on the seven tapes); Q1 at the halts 6.2 u p50, 0 of 22 over 40 |
| **Q6** | *"the follow is good"* | 40 follows / 22 halts in 63 s, nothing inside 0.5 s; the mirror's frame while moving p90 21.0 u |
| **Q3** | *"I led the hatcher up the stairs, around the wall at the top. he pathed around the wall well"* | the hostile's sync copy against its drawn body over the whole session: p50 0.0 / p90 9.2 / p99 12.5 / **max 27.9 u** (the spawn chase's first second), nothing wider around the wall |

**Q5 and Q6 are closed on the owner's word, Q3 on their route** — the drawn body pathed around
the wall and the sync copy never left it by more than 28 u. No sidestep fired on this session
(the hostile was never parked dead ahead of a lead) and one avoidance halt was predicted and
confirmed, so F14 had one trial each way.

## What the owner saw instead, and it is a real defect: **the Hatcher in the ground**

*"check the screenshot - he is in the ground instead of on it. he didn't walk up the slope like my
character did."* The tape has it exactly (`t` in capture seconds, planes and heights the client's
own, `mesh` = our navmesh's planes at each body's point):

| t | player | hostile | dz |
|---|---|---|---|
| 43.0 | (11046, 8943) plane 29, z −1038, mesh {29} | (10806, 8709) plane 29, z −924, mesh {29} | the stairs' slope, 335 u apart |
| 45.1 | (11238, 9120) **plane 0**, z −1051, mesh {0} | (11185, 9070) plane 29, z **−1050.1**, mesh **NONE** | +0.9 — level, at the top |
| 46.6 → 62 | (11459, 8849) plane 0, z **−1102**, mesh {0} | (11413, 8910) plane **29**, z **−1050.1 frozen**, mesh **NONE** | **+51.9 u for 16 s** |

From 44.1 s every point the hostile stood on has **no trapezoid in our mesh**; the nearest
covered ground is 5–45 u away and, from 46.6 s, it is **plane 0** — the plane the player had
just reported for the ground 77 u away. Our follow orders carried "mover 29 → destination 0"
the whole way (`_npc_plane` holds the carried word where `plane_at` is silent), the client kept
the Hatcher on plane 29, and its height reader — `ok`, no refusal — answered the **cached
−1050.1 across 230 u of walking**, because plane 29 has no surface there. The correction
GROUNDZ-F9 ships could not fire: it compares the word against `plane_at`, which had nothing to
say. **That is the sink: not a wrong trapezoid but a missing one, on the terrace above the
stairs, and a stale word held for want of any other.** [GROUNDZ-F11](../renderobj/FINDINGS.md)
ships the fix: where the mesh has no trapezoid under the mover and the mover stands within its
follow stop radius of the player's last report, the player's REPORTED plane names the ground —
the client's own word, never a guess between our trapezoids. `--no-npc-plane-reach` reverts.
**RECONSTRUCTION until the next session shows the body on the surface**: the prediction is that
on the same terrace the Hatcher's client plane reads 0 within one half-second of parking and its
ground z tracks the player's within 15 u.
