# Handoff — the props arc, 2026-08-12

> **(e10d) IS DONE — FINDINGS 46.** Both client runs happened the same day
> with the owner driving the go/no-go: the compiler kept our prop
> bit-faithfully in both, the oracle hit on OUR input (50 and 90), B's
> authored ring came back as collision geometry edge-for-edge, and run A
> discovered the compiler also instances the model's own collision
> footprint. Run record: `vault/research/e10d-props-2026-08-12/`. The
> banner below describes the state between the pickup and the runs.
>
> **PICKED UP the same day (FINDINGS 45), and both loose threads are closed.**
> The Bloated props chunk `0x20000004` is read (`props.BloatedProps`,
> READ-only, no encode) and **the cross-stream oracle is `test_props.py`
> section 9** — 349/349 under `--all` (110 checks, 718 s, floor 99), with
> record-for-record correspondence 285,670/285,670 that took the scale
> formula and the rot-basis reading from INFERRED to compiler-corroborated.
> The "known trap" below is now a refusal: `stripbuild.build()` takes
> `prop_dep_ids` and generates `0x11000004` (present iff props, 349/349 —
> `test_stripbuild` §3d). **(e10d) is STAGED and holding for the owner's
> go**: `vault/research/e10d-props-2026-08-12/` has builds A/B (one
> variable: the outline), `PREDICTIONS.md` recorded before arming, and
> `readback.py` proven against the study archive. Loose thread 1 (the silent
> second gate) is covered by the prediction protocol: a compile with no path
> chunk and no assert is read as the props chunk failing to bloat, not as
> "the compiler ignored our navmesh". Two of §44's population figures were
> corrected in place on the way (§45).

Written at the end of the session that read `0x10000004`, for whoever picks it
up. **Everything below is committed and merged to `main`** (`a459718`, merged).
Suite green: **61 of 61 in 934 s**.

## Where things stand

| | |
|---|---|
| `toolkit/mapdata/props.py` | the codec. 349/349 byte-identical. |
| `toolkit/mapdata/test_props.py` | 70 checks default, **79 under `--all` in ~205 s**, floor 70. 61st test in the suite. |
| `stripbuild.BORROWED` | Header + Zones only. **42 bytes, 98.20% generated.** |
| `PLAN.md` | (e10c) ✅ done, (e10d) ⬜ is the next rung. |
| `studies/customarea/FINDINGS.md` §44 | the full write-up. |
| `studies/customarea/PROPS.md` | superseded, corrected in place, kept for its lesson. |

## The next rung is (e10d), and it is small

**`stripbuild.build()` already takes `props=`.** Every map built so far passes
`minimal()` — the empty chunk. What has NOT happened is a client run with props
we authored: a real `model`, a real position, a real outline.

The pieces are all in place:

```python
from toolkit.mapdata.props import StrippedProps, Prop
sp = StrippedProps(props=[Prop(model=5, x=1536.0, y=1536.0, z=-13.0,
                               rot=(0, 0, 0), scale=0x7F)],
                   refs4=(), refs6=None)
rep = stripbuild.build(32, 32, heights, seed=(2112.0, 1536.0),
                       constants=constants, dep_ids=dep_ids, props=sp)
```

Then rung E3's normal path: `datmove`/`datwrite` the row in, `rebloat --arm`,
launch the client. `RUNBOOK.md` has the procedure; **the harness is a shared
single resource and a client run needs the owner's explicit go-ahead.**

**Two things to predict before arming**, because a probe with no stated
expectation can be rationalised into agreeing with anything:

1. Does the compiled Bloated props chunk hold our prop? Check its tag-0 size
   against the cross-stream oracle — `2 + 48*props + 8*points` — which is
   349/349 on retail and would be an exact prediction for ours.
2. Does the navmesh change around it? An outline is collision geometry, so a
   prop with a real ring should carve the mesh. A prop with `points=0` should
   not. **That pair is the experiment**: one variable, two runs.

**The known trap:** `model` is a filename index into chunk `0x21000004`
(`0x0073DE0E`), NOT a global id. Its pooled range is 0..439. A map that does not
list the model will not resolve it, and the failure mode is unknown — check what
`0x21000004` the donor map carries before picking a number.

## What is measured, and what is not

MEASURED, from the archive and confirmed independently by a disassembly read
afterwards and by an adversarial refutation that wrote its own walker:

* the whole framing; 349/349 byte-identical both ways
* tag 6's stride is 4 and no other value closes the 149 maps where it matters
* tags 4 and 6 index the prop array (17,002 references, 0 outside)
* every prop position is inside its map's rect (285,670 of 285,670)
* the cross-stream oracle, **349/349**
* tag 4's count is a u16 — from the CODE (`0x0073E1A6`); the corpus cannot
  decide it and `test_props.py` asserts that ambiguity on purpose

INFERRED or UNVERIFIED — do not quote these as facts:

* the three `rot` bytes and `scale` are named from the client's arithmetic.
  Widths measured, meanings inferred. Formulas: angle `b * 2*pi/256`, scale
  `b * (255/128)/256 + 1/128`.
* the tag-4 / tag-6 `value` u16s are ids of some kind. Not identified.
* `flags` is named for its shape (powers of two), not from any read of its use.

DELIBERATELY REFUSED: the client's version gate accepts `0x11` **and** `0x12`
(`0x0073E224` / `0x0073E228`). The corpus is `0x11` on 349/349. `props.py`
refuses `0x12` — no version branch was found in the framing, but "probably the
same" is a guess. If a `0x12` file ever turns up, that refusal is the thing to
revisit first.

## Two loose threads worth someone's time

1. **A second props gate exists that FINDINGS 34 does not name.** The Path bloat
   handler tests `cmp dword ptr [ecx+0x24], 0` at `0x00712678` and returns 0, so
   **a props chunk that fails to bloat silently kills the Path chunk with no
   assert**. That is a failure mode our tooling would currently misread as "the
   compiler ignored our navmesh". Worth a deliberate provocation.
2. **The cross-stream oracle deserves to be a test.** It is the strongest check
   in this arc and it currently lives only in an agent's scratchpad and in
   §44. Adding it to `test_props.py` would mean decoding the Bloated props
   chunk too — which nothing in this tree can do yet. That is its own small rung.

## Housekeeping for the next session

* The worktree is `C:\gd\Rurik\.claude\worktrees\nifty-fermi-7e2a8a` on branch
  `claude/custom-area-export-pipeline-e9d755`, merged to `main`. **Run
  `git rev-parse --show-toplevel` first** — the trees drift.
* A parallel session was writing in `C:\gd\Rurik` during this one. Stage by
  path there, never `git add -A`.
* The workflow `wf_d72f637e-347` finished: six agents, zero errors. All three
  refutations confirmed the framing. **One found a real defect in the codec and
  it is fixed** — see "only tag 6 is optional" in §44. Transcripts are under the
  session's `subagents/workflows/` directory if you want the VA detail.
