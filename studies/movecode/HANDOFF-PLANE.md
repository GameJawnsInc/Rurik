# HANDOFF — the plane channel and the movement LOCK, from a cold session

**Written 2026-08-29 at commit `dcf9484`, tree clean, branch `main`.** This hands off
two days of work on a channel the arc had never scored and a client failure mode it had
never seen. Read §5 before you propose a fix — the most obvious one is refused twice in
this repo's own history, and a cold session will propose it within ten minutes.

The status authority is still `PLAN.md` §3, and the live next-actions list is `PLAN.md`
§8 (its top two ★ bullets are this work). The full record is
[FINDINGS.md](FINDINGS.md) §1z-c (the channel, the bridge, the lock) and §1z-d (the
onset and the repair). How far to trust any number here:
[studies/method/FINDINGS.md](../method/FINDINGS.md).

---

## 1. Where it stands, in one paragraph

`m_point` is `float x, float y, int plane, int` and **the plane is a second channel the
arc scored nothing on for two weeks.** `pathmap.containing()` unions all 68 planes, so a
body on a bridge deck and a body on the ground *under* it are the same query — which is
why `noclipscore.py` read **0 off-mesh on a capture the operator took because they had
just walked under a bridge twice.** Section C now asks the plane-aware question and
finds 6 anomalies in `r5bridge` where section A read 0. Separately, the operator's
client **locked** — froze in open ground, no move command worked — and that capture
(`r5stuck`) is the arc's most diagnostic: the body sat on a plane the mesh does not
offer at its position, all 49 of the client's own path queries started from that
impossible plane, and the walker never ran. **A plane desync is a LOCK where a position
desync is only a warp**, because a client that cannot resolve its own position cannot
walk to ground that would re-plane it.

## 2. What is measured, and what is still inference

Keep this split. §1z-d's headline rests on the left column; the right column is what the
next measurement is for.

| OBSERVED | RECONSTRUCTION |
|---|---|
| The client acquired plane 41 **where 41 is correct** (t=29.03, (−2921.0, 523.4); our mesh offers exactly {41} there) — the strongest plane-index corroboration the arc has | That the client's path queries *failed to resolve* — we observe the queries and the silence after them, not the failure |
| It carried 41 across a boundary 150 u on, onto ground offering only {0}, and kept claiming it | That an 0x002C restamp **heals** the lock (this is the repair's whole premise, and it has never been tried) |
| Our trust guard **rejected** that report while the zero-lead grant echoed its plane anyway | That our plane indices are the client's (assumed, though the onset above is strong evidence) |
| The freeze: 82 accepted reports (81 `in-budget` + 1 `stop-report`), one byte-identical coordinate, plane 41, **40.4 s** (t=39.87..80.23) | |
| The echo census: **43 of 65** outbound plane-bearing sends impossible in the stuck session, against **0 of 285** across three healthy ones (r5bridge 53, r5 128, 08-28 104) — r5bridge's 9 legitimate plane-37 deck grants are the positive control | |
| Fence SHUT 110/110 in the lock vs 804 OPEN/11 SHUT healthy; `agapi_setdest`/`chcli_advance` **0 hits** against 49 clicks that each solved a path | |

**Refuted by its own control, do not re-propose:** zero-length grants as the lock's
cause. The healthy run has 76/76 zero-length grants and a 46.7 s stretch at one
position, and does not lock.

## 3. What landed in `dcf9484`

* **The plane repair** — `plane_repair_track` / `_maybe_plane_repair` in
  `toolkit/authsrv/authsrv.py`, **ON by default**, `--no-plane-repair` reverts. After
  5.0 s of accepted 0x003D reports repeating an identical (x, y) with a plane the mesh
  does not offer there and an unambiguous single-candidate resolution, it sends a
  numbered, labelled `PLANE-REPAIR` 0x002C at the client's own frozen point with the
  mesh's plane — at most once per 10 s. 0x002C's slot-2 plane is what the client writes
  to `agent+0x80`, the field its path queries read from.
* **The plane-echo tripwire** in `_note_wire_move` (the send() choke point all three
  player-moving opcodes route through) — an impossible outbound plane gets a
  `plane_echo` row and a transition print, **and goes out unchanged**. Observation only.
  The 43 silent echoes above would each have been a named row.
* `toolkit/authsrv/test_planerepair.py`, 41 checks, floor 36.

**Constants, and where they came from** (`PLANE_REPAIR_HOLD` 5.0, `PLANE_REPAIR_GAP`
5.0, `PLANE_REPAIR_MIN_INTERVAL` 10.0): HOLD is 8× inside the one measured lock; the
freeze test is **exact float equality** because the lock's reports were byte-identical
in both captures; GAP comes from that capture's own gap structure — intra-episode gaps
reach 2.47 s and must survive, the one inter-episode gap is 10.3 s and must re-arm.
**REFUSED-IF** a future lock shows the position drifting or a shorter freeze: re-derive
from that capture, do not loosen these.

**The first draft of the trigger was refuted before it ever ran**, and the method is
worth stealing: it disarmed the streak on every 0x0047 stop-report, which sounds
obviously right — and replaying the source capture through it showed the measured lock
*interleaves* stop-reports (a locked victim mashes keys), pushing the first fire from
5.1 s to 9.3 s and tripling the sends. **Any trigger you design here, replay `r5stuck`
through it before you believe it.**

## 4. The next actions, in the order I would take them

### 4.1 The repair's first live trial — opportunistic, costs one ordinary session

It has never fired against a client. Any map-280 session on the shipped default scores
it, because a healthy run is supposed to produce **zero** fires. Registered prediction
(FINDINGS §1z-d.3, timing restated from the offline replay, which is its authority):
the `plane_repair_due` ladder reaches `plane-lock` within ~5 s of the first continuous
report episode at a frozen point; numbered `PLANE-REPAIR` rows go out at most every
10 s; and — the part no replay can score — **the client walks on the next click after
fire #1, so a healed lock shows exactly ONE fire.** Repeat fire numbers refute the
`agent+0x80` heal reconstruction, not the trigger.

The offline replay of the shipped design over `r5stuck` fires at t=44.98, 55.12, 70.80
— first fire 5.11 s after the freeze, and all three legitimate, since that client
stayed locked for the whole capture with no repair in existence.

### 4.2 The `MapFindPath` RETURN tap — the cheapest measurement left

This is the one link §1z-c.3 infers, and it now buys a second thing: whether a repair's
restamp actually revives the walker. Ret sites `0x00709F0F`, `0x00709F44`, `0x0070A0AD`,
`0x0070A0D4` — named in `content/movecode.toml`'s own `limits` note, whose sentence is
the design constraint: *"AN ENTRY HOOK CAPTURES THE QUESTION, NOT THE ANSWER"* (arg5/arg6
point at uninitialised caller memory at entry; the backends write the results during the
call).

**Cost, honestly:** movehook's persistent-`int3` design leans on every hooked site being
a function ENTRY beginning `55 push ebp`, which is why one emulation shape covers all of
them, and why `[esp]` at a hook is still the caller's return address. A `ret` site is
neither. This is a real extension to `movehook.c`, testable offline the way §16 of
`test_movehook.py` tests the entry shape. Predict before you build: the locked client's
queries return `pathCount == 0`, and the first post-repair query starts from the
restamped plane and returns `pathCount > 0`.

### 4.3 Sweep the corpus with section C

Cheap, no client. `noclipscore.py` section C has only ever run on three captures. The
corpus holds many more, and `r4a` already carries the mirror anomaly 200 u from the lock
site (declaring plane 0 where the mesh offers 41) — that neighbourhood produces plane
confusion under both policies. Mine before registering another run; the corpus often
already holds the event.

### 4.4 Known blind spots, none of them closed

* **A lock whose victim stops pressing keys entirely is invisible** — no 0x003D stream,
  no evidence. (Key-*mashing* victims are covered; that was the first draft's bug.)
* **The residual false fire**: a client frozen 5 s on a deck our decode missed (the
  9/198 class) is restamped. Priced out loud in the constants block, **not prevented**,
  and not established recoverable — the client carries plane words rather than
  re-deriving them, so a wrong restamp rides along.
* **The onset is not prevented.** The client's plane-carry is the client's; we heal the
  consequence. Whether a server could prevent it at all is unasked.
* NPC planes are untouched. So is the keyboard channel (100/127 `kbd-drop` in the stuck
  session — a policy question, not a measurement gap; the plane explains the lock
  without it).

## 5. Traps — read these before proposing anything

1. **DO NOT make the server rewrite outbound grant planes.** "Never emit a plane the
   mesh does not offer at the emitted point" is the obvious fix, it is wrong, and it is
   refused twice in `authsrv.py`'s own comment blocks: `plane_at`'s 9-of-198 failure
   class is exactly *"the client's plane is CORRECT and our decode's coverage is
   missing"* (bridge-over-ground), a send site that second-guessed the client through
   `plane_at` was reverted for overruling it in precisely the wrong place, and
   `test_position_trust` pins verbatim echo at the zero-lead site **as design**. An
   instantaneous geometry test cannot tell a deck we failed to decode from a stale
   plane. That is why the repair's trigger is BEHAVIOUR (frozen movement reports), and
   why the tripwire only watches.
2. **`attach.py --stop` ENDS THE CAPTURE.** It is the last thing you do. On 2026-08-29
   a run was stopped and then played on, and the most interesting thing the operator saw
   is not on the wire.
3. **Establish which tree you are in** (`git rev-parse --show-toplevel`) and pin
   subagents to *that* path, with every command beginning `cd <tree> &&`. Naming a tree
   in prose does not move the shell.
4. **Never pick a client build by filename** — `sorted(exes)[-1]` has chosen wrong three
   times. The loopback build these runs used is
   `vault/run/2026-07-29_221c13772c7a/Gw.exe`; `python toolkit/clientpatch/dhbuild.py`
   audits the whole vault and currently reports every build where it belongs.
5. **Run only affected tests.** The full suite is ~40 minutes. For this arc:
   `test_planerepair.py`, `test_position_trust.py`, `test_poschecksum.py`,
   `test_cancelwalk.py`, `test_router.py`, `test_familyrate.py` — 500 checks, ~1 min.
6. **A number you did not measure yourself gets re-derived.** The pre-commit review
   re-derived every figure in §1z-d from the raw JSONL and caught the record's own
   "33 s" being 40.4 s — a figure that was doing load-bearing work as the empirical
   anchor for a design constant.

## 6. Commands (PowerShell — these are the operator's terminal, not bash)

Terminal 1, the server (shipped default; the repair is ON without a flag). This is the
configuration the lock happened under:

```bash
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--router --map 280"
```

Terminal 2, arm the client-side hook once you are in the map (the DLL and sites are
unchanged — **do not** regenerate sites):

```bash
python toolkit/clientscan/movehook/attach.py --minutes 8 --out vault/research/movecode/r6
```

Last thing, after everything you want measured:

```bash
python toolkit/clientscan/movehook/attach.py --stop
```

Scoring — the plane channel is section C, and it is orthogonal to sections A and B:

```bash
python toolkit/clientscan/noclipscore.py --bin vault/research/movecode/r6/movehook.bin
```

The server-side readout is the session's own JSONL under `vault/captures/gamesrv/`:
grep it for `plane_repair` (fires, numbered), `plane_repair_due` (the reason ladder,
logged on transition only), and `plane_echo` (impossible emissions, observation only).
A healthy session should show a `plane_repair_due` ladder that never reaches
`plane-lock`, and zero `plane_echo` rows.

Before touching the instrument:

```bash
python toolkit/clientscan/movehook/test_movehook.py
```
