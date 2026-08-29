# MOVECODE-R5 — the router vs the no-clip: does granting only legal legs kill the through-rock walk?

**Written 2026-08-28, after the obstacle dig (FINDINGS §1x) and the pocket
forensics (§1y).** One run, ~6 minutes of play, four pre-registered predictions.

## 0. What this run is

R4-A measured the no-clip under `--click-echo`: the server echoes the verbatim
clicked point, the client walks the straight line (its geometry consult is
non-gating, §1x.4), and the body crosses carved prop holes — 39 of 84 rapid-pair
chords crossed holes, and the body stood inside three different massifs
(props 127, 179, 221; `noclipscore.py` section A).

`--router` (ROUTER-B2, studies/movement/ROUTER.md) answers clicks with
`route()` legs on our own mesh instead. §1y establishes the mesh's voids at the
router-arc's two failure specimens are REAL structures, so the router's grants
are legal by construction. **This run asks whether that is sufficient: with
only legal legs on the wire, does the displayed body stop walking through
rock?**

## 1. Preconditions

Same as R4 (the DLL and sites are unchanged — do NOT regenerate sites):

```
python toolkit/clientscan/movehook/test_movehook.py
```

## 2. The commands

Terminal 1 — the server, **router on, click-echo OFF, no d1-lead**:

```
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--router --map 280"
```

Terminal 2 — arm the hook once you are in the map:

```
python toolkit/clientscan/movehook/attach.py --minutes 8 --out vault/research/movecode/r5
```

When done playing (`--stop` reads `movehook.cfg` for the armed run's output
directory, so it needs no `--out`; it now WAITS for the capture and tells you if
it did not appear):

```
python toolkit/clientscan/movehook/attach.py --stop
```

> **`--stop` ENDS THE CAPTURE. It is the LAST thing you do, after everything you
> want measured.** On 2026-08-29 a run was stopped, then played on — and the most
> interesting thing the operator saw (terrain walking near the west bridge) happened
> after the hook had disarmed and is not on the wire. A second `--stop` is harmless
> (it now reports the finished run and its capture), but it cannot bring the play
> back.

**The capture now survives either way the client goes down** — a snapshot every
15 s covers a hard kill, and a `DLL_PROCESS_DETACH` write covers a graceful
close (FINDINGS §2b). Killing the server before `--stop` is no longer fatal to
the run, but stop first anyway: it is the only path that writes `movehook.txt`.

## 3. What to do in the map, in order

1. **The repro, at the same rock.** Go to the massif you no-clipped through in
   R4-A (the one in your screenshots). Do the corner-click manoeuvre **at least
   6 times**: click around the corner, wait ~1 s, click a point on the far side
   of the rock. Note what the body does — walks around, stops, or cuts through.
2. **Click ON the rock twice.** Predicted: nothing happens (the click is
   refused — the destination is inside the carved hole). That refusal is
   correct behaviour, not a bug.
3. **The compound question (your eyes are the instrument).** Walk west to the
   spawn area, stand near it, and click far east (toward the practice targets
   side). In the router arc's last run this routed you south-west first —
   "a shape no player would ever accept". **Look at the direct line east: is
   there actually a building or wall on it, or open walkable ground?** Two
   structures sit on our mesh there (~250 u deep each, one with a big terrain
   drop). What you see decides §1y's one open question.
4. Free play the rest — corners, WASD mixes, whatever. Keyboard warps
   (reconcile drags while you fight a chain) are the KNOWN residual; note them
   but they do not score this run.

## 4. Predictions, registered before the run

| # | Prediction | REFUTED IF | Floor |
|---|---|---|---|
| P1 | The click-driven body crosses no carved hole: `noclipscore.py` section A deep off-mesh (>50 u) during click-only movement is **0** | any click-ordered walk puts the body >50 u inside a hole/outline | ≥6 corner-click attempts at the rock, ≥30 clicks total |
| P2 | **The dissociation signature**: section B still counts crossing CHORDS (the straight line still crosses the rock — geometry did not change) while section A goes clean — that split is the router working | B goes to ~0 crossings too (means the manoeuvre was not exercised — re-run, not a pass) | ≥6 rapid pairs at the rock |
| P3 | Clicks with the destination on the rock are refused (`dest-off-mesh` in the server log), not granted | such a click is granted and the body enters the rock | ≥2 on-rock clicks |
| P4 | The operator sees real walls/buildings on the old run-5 direct line east | the line is visibly open walkable ground end to end — then mesh fattening / a decode gap is live again and the next instrument is dumping the client's own imported mesh (§1y.4) | one honest look |

**Zero exposure is not a null** (the standing rule): if the rock manoeuvre was
not actually performed ≥6 times, P1/P2 are unread, not passed.

## 5. Scoring, after the run

```
python toolkit/clientscan/noclipscore.py --bin vault/research/movecode/r5/movehook.bin
```

Section A is the no-clip census (off-mesh body samples with prop-outline
attribution); section B is the rapid-pair chord coverage. Under `--router` the
signature is A clean while B still counts crossings.

```
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r5/movehook.bin
```

Report with the section A census, the section B pair counts, the server log's
router verdict lines (`routed` / `refused` / `tour-capped` counts), and your
own answer to P4 in words.
