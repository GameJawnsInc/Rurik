# MOVECODE-R7 — the return tap's first live run, and the only lock ever seen from both ends

> **RAN 2026-08-29 16:39, scored twice.** Client side:
> **[FINDINGS §1z-i](FINDINGS.md)** — `pathCount == 0` ⟺ an impossible from-plane,
> 187 / 10 / 17, exceptionless, with a natural experiment that holds the from-point
> bit-identical and varies only the plane word. Server side:
> **[FINDINGS §1z-o](FINDINGS.md)** — the 9 ladder rows and 9 echo rows, the streak
> decomposition (max **1.02 s** of a 5.0 s `HOLD`), a second lock morphology the
> trigger structurally cannot catch, and the coordinate join between the two halves.
>
> **This sheet is RETROSPECTIVE.** R7 was opportunistic — the first live exercise of
> the tap built in §1z-h, not a numbered experiment — so §4 records what was
> actually registered beforehand, which is *not* a prediction table, and refuses to
> invent one. Written 2026-08-30, the day §1z-o scored the server half.

> ## ⚠ THERE ARE TWO R7s, AND THE OTHER ONE OWNS THE GREP
>
> `grep -rn "R7" studies/` returns **CANCELWALK-R7** far more often than this run —
> a different experiment entirely (a hardware-breakpoint gate trace, 2026-08-24,
> `studies/movement/CANCELWALK.md` §7.4e/§7.6, shipped as `movetap.controller_read()`).
> This run is **MOVECODE-R7**. Disambiguate by the section, never by the number:
> this one iff `grep -n '^## 1z-i' studies/movecode/FINDINGS.md` returns a heading
> whose title contains `THE RETURN TAP RAN`.

**Every command in this sheet runs from `C:\gd\Rurik`.** `git rev-parse --show-toplevel`
if in doubt — a worktree has no vault, and the scorers below crash on an empty glob
rather than saying so.

## 0. What this run was

§1z-h built the `MapFindPath` **return** tap: four `ret` sites added to movehook so
the client's own navmesh ANSWER could be read, not just its question. Until then the
arc had entry-only data and could say "the client asked this and we cannot answer it",
never "the client could not answer it either". R7 is that instrument's first live run.

It was **not** designed to catch a plane lock. The operator walked, clicked rocks,
deliberately triggered under-bridge walks, and happened to end the session standing
underneath the west bridge — which is why the capture contains what it does. The lock
episode is 9 seconds of a 302-second run.

Its importance is that **both instruments were recording at once**: movehook inside
the client and the ordinary gamesrv tape on the wire. That has not happened for any
other lock, and it is why §1z-o can join the two by coordinate.

## 1. The exact configuration

| | |
|---|---|
| exe | `C:/gd/Rurik/vault/run/2026-07-29_221c13772c7a/Gw.exe` (build 38797) |
| map | **280**, explorable — `MAP OVERRIDE: 280` / `[map] navmesh 0x287B3: 68 planes, 2769 trapezoids` |
| server flags ON | `--zero-lead`, **plane repair (default ON)**, `--grant-suppress`, `--cast-stop=pin`, **`--router`** |
| router readout | 204 `router_route` rows, 94 `router_leg` rows in the capture |
| hook | movehook v7, 19 sites, both controls FIRED, ended by `--stop` |
| duration | 301,600 ms hook / ~302 s of tape |
| capture, client | `vault/research/movecode/r7/movehook.bin` (5,627 records) |
| capture, server | `vault/captures/gamesrv/authsrv-20260829T163930-c1.jsonl` |
| harness dir | `vault/captures/harness/20260829T163859/` |

⚠ **`--router` WAS ON, and this sheet's first draft said the opposite.** That draft
grepped `report.json` for "router", found nothing, and published the negative. The
gamesrv banner says `[map] --router ON (ROUTER-B2 ...)` in as many words, and the
capture carries 204 `router_route` and 94 `router_leg` rows. `HANDOFF.md` §F is
correct: pass `--router` to reproduce R6/R6b/**R7**. **This is §C's own rule —
the server's startup banner is the authority, not a flag census taken somewhere
else — and it was broken by a session that had just quoted it.** A capture's own
verdict rows are the second witness; use both.

⚠ **R7 ran with the plane repair ARMED.** It shipped at `a481a88`, 2026-08-29
11:22:45; R7 started at 16:39. So R7's zero fires are a real prospective observation,
unlike the pre-`a481a88` sessions whose replayed fires are counterfactual (§1z-e.2).

## 2. What it produced, in one place

Neither half is restated here — the sections are the record and they supersede any
summary. What this table is for is knowing which section answers which question.

| question | answer | where |
|---|---|---|
| Does the client's own pathfinder fail on an impossible plane? | Yes — 10 of 10, and 187 of 187 the other way, with 17 off-mesh queries succeeding as the control | §1z-i.2 |
| Is it the PLANE, or the location? | The plane. Bit-identical from-point, 1.19 s apart, plane 37 → `pathCount 1`, plane 0 → `0` | §1z-i.2 |
| What happens after a failed query? | No `setdest`; the correction machinery fires; fence SHUT 43/43 in the window | §1z-i.3 |
| What did the SERVER see? | 9 ladder transitions + 9 echoes, all plane 0 where the mesh offers [37] | §1z-o.1 |
| How close did the repair come to firing? | **1.02 s of 5.0 s — 20%**, in four streaks | §1z-o.2 |
| Why didn't it fire? | The lock is INTERMITTENT — freeze ~1 s, jump ~100 u, freeze again. Each new coordinate re-arms the clock | §1z-o.3 |
| Are the two halves the same event? | Yes, twice over — 2 of the server's 4 arming/holding coordinates are client-side `pathCount == 0` points (**0-of-192** negative control), and under the adopted clock offset the window holds **7 consecutive zeros** ending the instant the declared plane flips to 37 | §1z-o.4 |
| Can the two captures be time-aligned? | Yes — `t_server = tick_ms/1000 − 762353.145`, **±8 ms**, three independent anchors (204/204, 117/122, 176/176) | §1z-o.6 |
| **Did the snap's gate 2 ever fire?** | **Yes — 3 times, and the handoff says it never has.** Gate 2's own query returned 0 three times, each followed by `reseed` in the SAME client tick; 0 of its 7 normal answers did | §1z-o.5 |
| **Who put the plane 0 there?** | Recovery was **ours** (a router clip-fallback computing 37 off our own mesh). Onset is probably ours too — three router sites call a `--d1-lead`-only override with `D1_LEAD` False — but the LOCAL write is inferred, not observed | §1z-o.6 |
| R7's own ladder breakdown | `plane-legal` 3, `arming` 3, `holding` 2, `off-mesh` 1. **The 17/13/3/2 figure is the corpus-wide total, not R7's** | §1z-o.1 |
| Where does R7 sit in the corpus? | 8th of 134 on disagreements, 31st on size; **4x the corpus rate** (9.09% vs 2.34%); 100% inverse-class where the corpus is 80% forward | §1z-o.7 |
| Is that geometry or session? | **Neither, as first read.** R6 had 74 plane-37 reports to R7's 41 and disagreed zero — but §1z-f.4's ground truth says R6 was ON the deck and R7 UNDER it. On-deck vs under-deck, not session vs session | §1z-o.8 |

⚠ **The biggest result is not in the plane channel at all.** Splitting
`MapFindPath`'s answers by CALLER — which no section had done — shows the snap's
**gate 2 (`0x00605807`) firing three times**, against a handoff block that says it
has *"n = 0 observed firings"* and *"do not build a fix against it"*. The plane
word is what fired it, which makes the plane channel a **warp** cause and not only
a lock cause. §1z-o.5.

## 3. The corrections this run forced

1. **The commissioned framing was wrong.** `HANDOFF.md` §D′ asked for *"a near-miss
   on a false fire, not an encouraging arming."* Plane 0 was invalid at that point by
   the client's OWN navmesh — seven consecutive `pathCount == 0` answers, ending when
   the plane flipped to 37 — so a fire would have restamped 0 → 37, the plane the
   client declared 8.9 s later, after OUR grant put a 37 on the wire (§1z-o.6).
   **A true positive that could not reach
   the bar.** Recorded here because the instruction to write it the other way is still
   in the file's history.
2. **"Gate 2 has never fired" was an inference, and it is refuted** (§1z-o.5).
3. **"Exceptionless in both directions" needs its restriction attached.** Over all
   214 queries the plane law breaks 17 times; all 17 are from-points where our mesh
   offers nothing. Restricted to the 197 our mesh can speak about, separation is
   perfect. State the restriction or state something false.
4. **The natural experiment is not a controlled A/B.** The pair shares its from-point
   dwords but differs in caller, range, maxCount and destination. Suggestive, and the
   best single pair in the run — not an experiment anyone designed. §1z-i.2's "not the
   location, not the destination, not the range" is struck.
5. **"The client recovered unaided" was wrong.** The only 37 on the wire in that
   interval was **ours**, computed from our own mesh, and the client adopted it 1.05 s
   later (§1z-o.6).
6. **The nine echoes are 5 zero-lead + 4 router one-leg**, not nine zero-lead — so
   `test_position_trust`'s verbatim-echo licence covers five of them, not all.

## 4. What was registered before the run — honestly, not much

R7 has **no prediction table**, and this sheet does not manufacture one. What existed
beforehand:

* §1z-h.2 registered the tap's own arm census as a prediction — that `ret1` would
  never fire (its guard is `dist² ≤ FLT_EPSILON`), and that entry/ret would pair on
  `(tid, esp)`. **Both MET**: 214/214 paired with zero esp mismatches, `ret1/2/3`
  zero. §1z-i.1 scores them.
* §1z-h.3 predicted `pathCount == 0` would split `OURS-FAILED` in half. **MET.**
* Nothing was registered about a plane lock, because nobody expected one.

Everything in §1z-o is therefore **post-hoc scoring of an opportunistic capture**.
That is a weaker epistemic position than R6's registered table and the sections say
so; the compensation is that the two instruments were independent and the join has a
negative control.

## 5. How to re-score it

Client side — the return tap and the query table:

```bash
python toolkit/clientscan/movehook/pathdiff.py --bin vault/research/movecode/r7/movehook.bin --map 0x287B3
```

Server side — the plane channel, and the census this run's geometry now sits inside:

```bash
python toolkit/clientscan/planecensus.py
```

The raw readout, if you want the 18 rows rather than a summary:

```bash
python -c "import json;[print(l.strip()[:200]) for l in open(r'vault/captures/gamesrv/authsrv-20260829T163930-c1.jsonl',encoding='utf-8') if 'plane_repair' in l or 'plane_echo' in l]"
```

⚠ `--map 0x287B3` is not optional and not a guess: `pathdiff` REFUSES to identify a
map when the signal is weak, and its identifier is measured wrong on 16 of the 58
captures it accepts (§1z-n.7). Pin it.

## 6. What R7 leaves for a successor run

* **The HEAL is still untried.** Zero fires means the `0x002C` restamp has never met
  a live locked client. R7 got 20% of the way.
* **The intermittent morphology has n = 1.** Everything in §1z-o.3 rests on one
  9-second episode.
* **Whether the echo prolongs a lock is unmeasured.** The server echoed plane 0 back
  nine times while the client was stuck and the client recovered anyway; nothing
  separates "inert" from "delayed it". A `--no-zero-lead` run would.
* **Where to press.** §1z-n's census names the geometry: the **west bridge on map
  280**, where our mesh offers only the deck and plane 0 appears nowhere across
  4,488 samples at 8 u. Stand still there — the streak dies on movement, which is
  exactly what defeated R7.
* **Run the return tap again.** It is the only instrument that has ever adjudicated
  a stale plane against a decode gap, geometry cannot do it (§1z-n's
  distance discriminator puts R7's own armings in an ambiguous band), and it has
  been run **once**.
