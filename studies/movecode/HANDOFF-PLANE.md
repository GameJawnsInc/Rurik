# HANDOFF — the plane channel and the movement LOCK, from a cold session

> **⚠ THIS IS A DEEP-DIVE, NOT THE ENTRY POINT. Start at
> [studies/movement/HANDOFF.md](../movement/HANDOFF.md)**, which is the arc's entry
> point as of 2026-08-30 and carries the staleness table for every document here.
>
> **CURRENCY, stated so it cannot lie:** this file was last edited at `2882627`
> (section 1z-i) and its old self-stamp claimed `dcf9484`, which was already wrong.
> **Sections 4.1–4.3 below are current only through `2882627`.** Four commits landed
> after it that this file does not otherwise record, all of them defects in the arc's
> OWN instruments rather than findings about the client:
>
> | commit | what it was |
> |---|---|
> | `1ce0171` | 1z-j — the map identifier picked the WRONG map; a scoring pass believed it and read OFF-MESH 3 instead of 63 |
> | `30055e0` | 1z-k — the motion window: one expression, three defects, and the reader had been CRASHING on run 1 |
> | `d710a67` | 1z-l — `nearest_walkable`: an axis clamp is not a nearest point, and off-mesh depths were up to 3× too big |
> | `131c84a` | 1z-m — `RET_MAX_POINTS` 4 → 9 as capture v8; v7 stays readable on purpose |
>
> **They did NOT move this arc's headline** — `pathdiff` on r7 still reproduces
> AGREE 97 / DIFFER 34 / UNCOMPARED 13 / OFF-MESH 63 — but they moved older figures
> **per figure, not as a blanket invalidation**: r4a's off-mesh depths moved
> materially (median 239 → 228.2 u), while 1z-g.1's 20.2 u moved 0.5 %. Re-derive the
> specific number you are about to lean on.

> ## ⚠⚠ THE REPAIR'S ONLY LIVE ARMING WAS PROBABLY A FALSE FIRE — MEASURED 2026-08-30
>
> R7's server log carries three `arming` rows and two `holding` rows — the furthest
> the shipped repair has ever advanced, and **scored nowhere**: section 1z-i reports
> the return tap and says nothing about the repair, the ladder or the tripwire.
>
> All three arming points — (−1908.33, 6407.31), (−2006.48, 6424.53),
> (−2067.12, 6515.66) — land inside a **single plane-37 trapezoid**, the west
> bridge deck. The client declared plane **0** at each. Our mesh offers only 37 there,
> so `plane_at` resolved unambiguously and the ladder armed. Had the streak reached
> `PLANE_REPAIR_HOLD` (it peaked at 1.02 s of 5.0 s) the repair would have restamped
> the player **onto the bridge above them**.
>
> **AND THE SAFETY TEST IS INVERTED, WHICH IS THE GENERAL FORM OF IT.** The repair
> claims authority only on an unambiguous single candidate — so where our decode
> HOLDS a stacked deck it returns two planes and DISARMS, and where our decode MISSES
> the ground under a deck it returns one and ARMS. Fine scan at 8 u over both bridges
> on map 280, bucketing each sample by `len(containing())`:
>
> | deck | our decode | offers ONE → **arms** | offers 2+ → disarms |
> |---|---|---|---|
> | west bridge, plane 37 | misses the under-deck ground (1z-f.4) | **4,671 / 4,723 = 98.9 %** | 52 = 1.1 % |
> | NE bridge, plane 42 | holds the `{0,42}` stack (1z-g.5) | 3,572 / 6,821 = 52.4 % | 3,249 = 47.6 % |
>
> **The repair is most confident exactly where it is least entitled to be.** That is a
> structural property of the design, not a tuning problem, and it is not in the
> doctrine block, in section 5's traps, or in this file's constants note — which
> prices the false-fire class as having "no measured instance". There is now a
> candidate instance. The next action is the corpus-wide plane-disagreement census;
> the reasoning is in the arc handoff's section D.

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

**UPDATE 2026-08-29, night (§1z-g): R6b RAN and P1's floor is MET** — zero
fires through 16.33 min, echo census 30/797, all at glitch structures. The
landmark was unplanned: an **off-mesh S-press stuck** (11.16 s frozen stream
the repair structurally cannot arm on — off-mesh disarms by design; a
confirmed coverage gap, filed as an owner question) whose recovery
**corroborated the heal mechanism live**: a routed grant's plane word revived
the dead walker in 81 ms, and the all-locks census shows every historical lock
received ZERO fresh plane words while locked (r5stuck 0/33, Ascalon 0/11, K1
0/3 — kbd-drop suppressed every in-lock click; the zero-lead echo relays the
poison by design). The 0x002C repair is the fresh-plane source that depends on
neither idling nor luck; registered expectation for its first fire: heal
within ~100 ms. Also: the NE bridge is the first BY-DESIGN stacked pair and
our decode HOLDS it ({0,42} on 359/747 points) — the west bridge's
{37}-only footprint is the contrast, not the norm.

**UPDATE 2026-08-29, evening (§1z-f): RUN-R6 RAN.** The trigger stayed silent
through 18 live carry episodes (P1 healthy on every observable; its 15-min
floor unmet at 7.8 min), the operator's under-bridge walking turned out to be a
GLITCHED state and is settled as such (not a decode gap — §1z-c's reading of
r5bridge's anomalies is revised in §1z-f.4), the carry mechanism measured
fully client-internal (the grant channel wrote correct planes 17/17 while the
client's own walk bake re-asserted stale ones), and the census found a new
relay subclass: click-dest planes echoed verbatim (4/349). The HEAL is still
untried — no lock has recurred under the shipped default.

**UPDATE 2026-08-29, later the same day (§1z-e): §4.3 below was executed and the
corpus already held TWO MORE LOCKS** — Ascalon 08-27 05:52 (§1c's own session, 10.2
minutes from freeze to force-close) and the K1 treatment session 08-27 21:23. The
shipped repair replayed over all 1,209 session JSONLs fires on exactly those three
sessions and nowhere else (verified by an independent replay on both clocks; no
other session's streak held even 3 s). A first-draft claim that the K1 tape showed
the server POISONING the client's plane was **refuted in review** — the client's own
0x0047 stop-report carried plane 0 first and the keepalive echoed it; the flap is
the client's own reseed machinery (§1z-e.4 keeps the refutation). Read §1z-e before
§4.1 — it weakens the "one fire = healed" discriminator (both historical locks show
one fire because the victim GAVE UP, not because anything healed).

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
| **NEW (§1z-e):** two more locks in the historical corpus, both 08-27, both preceded by a client-side rollback jump carrying a stale plane; the replayed trigger fires on exactly the three lock sessions across 1,209 files, zero others | Whether either 08-27 victim experienced the freeze as a lock (the tape shape says yes — mash, silence, force-close — but nobody asked the operator) |
| **NEW (§1z-e.4):** the K1 session's plane flap 0↔22 is the CLIENT's own reseed/teleport machinery — first flip precedes any keepalive; the keepalive's plane word is a verbatim echo of the client's own 0x0047 stop (a first-draft "server poisons the client" reading was REFUTED in review: the draft's dump filtered out the stop arm); §1z-d's "the server never invents a wrong plane" survives a second test | Whether ZERO LEAD's field-4 carry word contributes to the flap — two flips landed on the same frame as a matching carry word; the first flip had no wire trigger. A probe question, not a claim |
| **NEW (§1z-e.1):** the plane-carry is common and self-healing — 13/22 corpus episodes are strict carries (declared = just-left plane), both directions at one boundary, 20/22 heal on tape; the 2 that do not are the two locks' onsets | That every carry episode is temporal rather than a decode hole — argued from direction-follows-travel and 1,667–2,717 u episode spans, but no specific episode is ruled either way |

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

### 4.1 The repair's first live trial — RAN 2026-08-29, scored as §1z-f; the heal is STILL untried

> **EXPOSURE, stated once because it has been quoted three different wrong ways**
> (47 sessions; 27 minutes; 1,216 logs). The tracker only exists in builds after
> `dcf9484`, and the set of sessions carrying any `plane_repair_due` row is exactly
> the set started after it — a clean natural experiment. **Three sessions have ever
> run armed: R6, R6b and R7.** That is **63.0 min wall**, of which only **23.9 min
> carries position reports at all** (R6b's last ~23 min carry none). Never write a
> bare minute figure without its denominator, and never write "47 sessions".
>
> **The streak IS readable from the log**, contrary to what this file used to imply:
> the tracker keys on consecutive accepted 0x003D reports with a byte-identical
> `reported`, so the report stream *is* the streak — R6 0.837 s, R6b 11.162 s
> (swallowed by the off-mesh clause), R7 1.021 s, against a 5.0 s HOLD. No duration
> field is needed. But note the ladder logs on reason **transition** only, so an
> arming count read off the log is a floor, not a total.

**The runsheet is [RUN-R6.md](RUN-R6.md), and its first execution is scored in
FINDINGS §1z-f**: the trigger stayed silent through the heaviest plane-anomaly
exposure ever captured (18 carry episodes, 60.7 s; zero fires, the ladder never
armed, 0/202 reports impossible), the tripwire caught a NEW echo subclass (4/349
— router one-leg answers relaying the client's own under-bridge glitch clicks),
and the carry mechanism measured fully client-internal (grants correct 17/17 on
the reseed channel while the client's own walk bake re-asserts the stale
plane). **Two floors fell short and the trial is not complete**: the session
was 7.8 min against P1's 15, and P2's wall SLID instead of pinning. The next
ordinary session at full length (and a pinning corner, or P2 dropped)
completes the healthy branch; **a lock remains the only path to the heal
measurement**, and no lock has occurred under the shipped default since
r5stuck. The original registered prediction stands
(FINDINGS §1z-d.3, timing restated from the offline replay, which is its authority):
the `plane_repair_due` ladder reaches `plane-lock` within ~5 s of the first continuous
report episode at a frozen point; numbered `PLANE-REPAIR` rows go out at most every
10 s; and — the part no replay can score — **the client walks on the next click after
fire #1.** Repeat fire numbers refute the `agent+0x80` heal reconstruction, not the
trigger. **REVISED by §1z-e.5: "exactly ONE fire" alone does NOT confirm the heal** —
both historical locks show exactly one replayed fire because the victim's stream ends
(gives up, force-closes). The heal's signal is specifically movement resuming after
fire #1. And ~5 s holds only for a continuously mashing victim: lock #2's
burst–36 s pause–burst cadence pushes the first fire to ~45 s after onset (the GAP
re-arm working as designed; the victim is healed on their next burst instead).

The offline replay of the shipped design over `r5stuck` fires at t=44.98, 55.12, 70.80
— first fire 5.11 s after the freeze, and all three legitimate, since that client
stayed locked for the whole capture with no repair in existence. §1z-e.2 extends this
replay to the whole session corpus: three lock sessions fire, zero of the other 109
do — all 112 movement sessions scored once the review closed the first pass's
label-parse holes (§1z-e.2), the two map-167 sessions included (clean under the
run archive's own authored mesh).

### 4.2 The `MapFindPath` RETURN tap — ✅ BUILT AND RUN 2026-08-29. **ANSWERED.**

**§1z-i: the client's own pathfinder returns pathCount == 0 EXACTLY when its
declared from-plane is one the mesh does not offer — exceptionless in both
directions** (187 plane-matched → 0 zeros; 10 mismatched → 10 zeros; 17
off-mesh-entirely → 0 zeros), with a decisive natural experiment: two queries
1.2 s apart with **bit-identical from-point x/y dwords**, differing only in the
plane word (37 vs 0), answered 1 and 0. And §1z-c.3's inferred link is now
OBSERVED: `pathCount > 0` → setdest fires 0.95×; `pathCount == 0` → setdest
**0.00, ten times out of ten**, with the correction machinery firing instead and
the fence SHUT. The lock's middle term is supplied. Caveats: r7's state was
transient and the body was not frozen, so "cannot resolve" is corroborated and
"cannot move" is not.

The instrument itself passed: 214/214 paired, zero esp mismatches, ~0.004 % cost.
One defect of my own was found and fixed — the shape metric was a tautology
(§1z-i.5). The rest of this section is the pre-run reasoning.

### 4.2-built The RETURN tap — BUILT 2026-08-29

**Landed as FINDINGS §1z-h**: four `mapfindpath_ret*` rows, a second emulation
shape (`SHAPE_RET`), capture v7 carrying `out_count` (the client's own
pathCount) and the first four waypoints, and a (tid, esp) join that audits its
own premise. `pathdiff` now scores five-valued, which **splits `OURS-FAILED`**:
that verdict assumed the client had succeeded, so every query neither side
could answer inflated our decode-gap number — `BOTH-FAILED` is now its own row.
It has not been armed against a client yet; the next ordinary session scores
it, and the registered prediction below is unchanged.

The rest of this section is the pre-build reasoning, kept because the cost
estimate and the design constraint are what the build was priced against.

### 4.2-orig The `MapFindPath` RETURN tap — the cheapest measurement left

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

### 4.3 Sweep the corpus with section C — ✅ DONE 2026-08-29, and it paid twice

**Executed as §1z-e** (client-capture census + whole-corpus repair replay), scripts
and outputs in `vault/research/movecode/plane-sweep/`. Found: two more locks (both
08-27), the carry-class census, and the whole-corpus false-positive validation of
the shipped trigger (three lock sessions fire, zero others across 1,209 files).
Also found, by the review: a first-draft "server poisons the client's plane" story
refuted (the client's own 0x0047 stop carried the plane first — §1z-e.4), and a
real alias defect in section C's plane lookup (it erases 2 real anomalies in k2-2).
What it did NOT find: any lock under the router-era defaults other than r5stuck,
and any fire that dissolves into trigger noise.

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
