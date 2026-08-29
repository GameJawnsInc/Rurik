# MOVECODE-R6 — the plane repair's first live trial: zero fires healthy, and if a lock comes, the HEAL

> **RAN 2026-08-29, scored — [FINDINGS §1z-f](FINDINGS.md).** P1 healthy on
> every observable (zero fires, ladder never armed, 0/202 reports impossible)
> but its 15-min floor UNMET at 7.8 min; P2 UNREAD — the wall SLID (~94 u/s,
> longest byte-identical streak 0.837 s; a future press needs a pinning
> corner); P3 MET (73 stacked, 24 deck stints); P4 UNREAD (no lock — the heal
> is still untried). Bonus: the echo census read 4/349 — all four the
> operator's under-bridge GLITCH clicks relayed verbatim (a new subclass), and
> the under-bridge itself is settled as a glitch, not a decode gap.
> **The completion run is §6** — ordinary play to the 15-minute floor, hook ON
> as lock insurance, fresh out dir `r6b`.

**Written 2026-08-29, after §1z-e; four-skeptic review applied before it landed**
(the review found the original watch-terminal-1 protocol unexecutable and the
scoring one-liner a PowerShell SyntaxError — both fixed and tested below).
Opportunistic by design — one ordinary session, and **both outcomes score**: a
healthy session is the specificity claim's first prospective live test, and a
lock is the heal's first trial. Cold start for the whole channel:
[HANDOFF-PLANE.md](HANDOFF-PLANE.md).

**Every command in this sheet runs from `C:\gd\Rurik`.** The worktrees have no
vault: from a worktree, the `--exe` path fails loudly but `attach.py --out`
silently captures into a stray worktree-local directory, and the §5 scorer
crashes on an empty glob. One tree, stated once, checked with
`git rev-parse --show-toplevel` if in doubt.

## 0. What this run is

The plane repair (`plane_repair_track`, §1z-d.2 — ON by default since `dcf9484`)
has **never fired against a live client**. Its trigger is now validated offline in
both directions: the r5stuck replay is the true-positive side (fires at
t=44.98/55.12/70.80, first 5.11 s after the freeze), and §1z-e.2's whole-corpus
replay is the specificity side (three lock sessions fire, **zero of the other 109**
— and the three are the corpus's only locks, two of them retro-discovered by the
replay itself). What no replay can score is the **HEAL**: whether the 0x002C
restamp of agent+0x80 actually revives a locked client's walker. That is this
run's conditional question.

Two revisions from §1z-e.5 govern how a lock is scored, and they change what the
OPERATOR does — the victim's behaviour is part of the experiment this time:

* **"Exactly one fire" does NOT confirm the heal.** All three historical locks
  show one fire in replay because the victim gave up and the stream ended. The
  heal's signal is **movement resuming after fire #1**, followed by continued
  play with no further fires.
* **"~5 s to first fire" holds only for continuous mashing.** A pause over 5 s
  re-arms the clock by design (lock #2's burst–36 s pause–burst pushed the fire
  to ~45 s). A locked operator who keeps pressing gets the fire in ~5 s.

## 1. Preconditions (~2 min)

The arc's test set — HANDOFF-PLANE §5's trap 5 names the first six (~1 min
total); `test_noclipscore` is added because §1z-e changed that scorer:

```
python toolkit/authsrv/test_planerepair.py
```

```
python toolkit/authsrv/test_position_trust.py
```

```
python toolkit/authsrv/test_poschecksum.py
```

```
python toolkit/authsrv/test_cancelwalk.py
```

```
python toolkit/authsrv/test_router.py
```

```
python toolkit/authsrv/test_familyrate.py
```

```
python toolkit/clientscan/test_noclipscore.py
```

Before touching the instrument (the DLL and sites are unchanged since R5b —
do **NOT** regenerate sites):

```
python toolkit/clientscan/movehook/test_movehook.py
```

And the vault audit — never select a build by filename; the command in §2 names
the loopback build explicitly, and this proves every build is filed where it
belongs:

```
python toolkit/clientpatch/dhbuild.py
```

## 2. The commands

Terminal 1 — the server, **shipped default: the repair is ON without a flag.**
The launch configuration (flags, build, map) is the one the r5stuck lock
happened under — **plus the repair that has since shipped, which is what this
run trials.** `--hold 2400` bounds the client at 40 minutes — the window closes
itself.

```
python toolkit/harness/session.py --exe vault/run/2026-07-29_221c13772c7a/Gw.exe --keep-open --hold 2400 --game-args="--router --map 280"
```

Terminal 1b — **the live readout.** The gamesrv's prints do NOT reach
terminal 1 under this invocation (session.py echoes them only for
`--labelrun`/`--probe` runs); they go to the harness capture's `gamesrv.log`.
Once terminal 1 has printed its `gamesrv up:` line, start this tail in a second
window and keep it visible while you play:

```
Get-Content -Wait -Tail 5 ((Get-ChildItem C:\gd\Rurik\vault\captures\harness\*\gamesrv.log | Sort-Object LastWriteTime)[-1].FullName)
```

What to watch for there — a healthy session prints NEITHER:

* `[plane-repair] fire #N: ...` — the repair fired (also a numbered
  `PLANE-REPAIR` send label and a `plane_repair` JSONL row).
* `[plane-echo] emitting plane P at (x,y) where the mesh offers [...]`
  (paraphrased tail; the `[plane-echo]` prefix is exact) — the tripwire's
  transition print. Observation only; the send goes out unchanged.

Terminal 2 — arm the hook **when you ARRIVE at the bridge (§3 step 3)**. The
DLL's run timer starts at injection, so arming on site spends the window on the
behaviour being measured. 15 minutes is ring-safe (stop-on-full at 32,768
records; the corpus peak rate ~29 rec/s fills it in ~18 min) and covers a lock
late in the exposure phase:

```
python toolkit/clientscan/movehook/attach.py --minutes 15 --out vault/research/movecode/r6
```

Last thing, after everything you want measured:

```
python toolkit/clientscan/movehook/attach.py --stop
```

> **`--stop` ENDS THE CAPTURE. It is the LAST thing you do.** Twice now
> (2026-08-27 k1, 2026-08-29 r5b) the most interesting event of a run happened
> after the hook was disarmed. **If a lock happens, the hook stays armed through
> the lock, the fire, and the recovery attempt** — stop only when play is over.
> One caveat the other way: when the 15-minute window expires the DLL disarms
> and writes the capture BY ITSELF, and a second attach is **refused by design**
> (a double arm would leave a live 0xCC) — do not re-run `attach.py` into that
> refusal. A lock after the window still scores fully: P4's whole readout is
> server-side (the gamesrv log, the JSONL, and your own words); the bin feeds
> only P3.

## 3. What to do in the map, in order

1. **Ordinary play, ~2 minutes.** Walk and click around spawn. Terminal 1b
   should stay silent.
2. **The wall-press negative control, ~10 s.** On plain single-plane ground —
   a wall of the walled compound east of spawn (R5's P4; its approach ground is
   measured single-plane {0}) — hold a movement key INTO the wall for a slow
   ten-count, then release. **Note the wall clock.** The body stands still
   while the client streams movement claims — the FREEZE half of the lock
   signature without the plane half. Predicted: **no fire, no echo** — a legal
   plane disarms the streak on every report (`plane-legal`). The premise that a
   blocked client streams reports at all is corpus-supported (a 2026-08-22
   session ends with 10.6 s of byte-identical accepted 0x003D rows at a legal
   plane), but §5 checks it for THIS run — a press that produced no report
   stream leaves P2 unread, not passed.
3. **Walk to the bridge, arm the hook (terminal 2) on arrival, then the
   plane-exposure phase, ~6 minutes.** The two highest-carry sites the corpus
   knows:
   * **The bridge you walked under for r5bridge** — the record's "west bridge";
     its decks measured at (−1032, 6283) and (−2822, 6404): cross the deck
     fully, turn around, come back UNDER it. Three round trips (= P3's six
     crossings), mixing clicks and keys. r5bridge produced 8 carry anomalies in
     45 s here under the shipped section C (6 under the pre-fix scorer §1z-c
     published; the fix moved the count, §1z-e.1).
   * **The lock's own structure** (plane 41 — a ~430×414 u patch near
     (−2921, 523), where r5stuck acquired its plane legally and carried it off
     the east edge): walk onto it and off it repeatedly, several directions,
     clicks and keys mixed. **Press-and-release at the edges — never a
     sustained hold into a wall or edge here.** A sustained press during an
     active plane-carry would manufacture the true lock signature on a
     non-locked client (frozen point + carried plane + live stream ≥ 5 s): the
     trigger would fire CORRECTLY and the fire would be unscoreable against
     P1's specificity. The sustained hold belongs only in step 2, on
     single-plane ground.
4. **IF THE BODY LOCKS** — you press and nothing moves **on open ground, no
   wall in front of you** (that visible difference is what separates this from
   step 2's control). This is the jackpot; do not quit, and do these in order:
   * Note the wall clock.
   * **KEEP PRESSING movement keys, continuously, for at least 15 seconds.**
     The trigger needs a LIVE report stream: ~5 s of continuous mash reaches
     `plane-lock`; any pause over 5 s re-arms and delays the fire to your next
     burst (that is design, not failure — but continuous is the clean
     measurement).
   * Watch terminal 1b for `[plane-repair] fire #1`.
   * **After the fire: RELEASE every key, count three seconds, THEN click once
     on nearby open ground.** The release matters — the server drops any click
     within 3.0 s of keyboard movement (`kbd-drop`, the keyboard-authority
     window; the r5stuck victim's own clicks went 100/127 kbd-dropped), and a
     dropped heal-click would read as "heal refuted" when the click never
     reached the walker at all. If the body does not walk on the first click:
     release, pause, click again before concluding anything.
   * If the body walks — the HEAL is measured. Keep playing normally for a few
     more minutes: a healed lock must show **no further fires**.
   * If the body does NOT walk on release-paused clicks: keep keys and clicks
     going for at least another 30 s. Repeat fires at ≤10 s intervals are
     themselves the measurement — they refute the agent+0x80 heal
     reconstruction, not the trigger.
   * Only then wind the run down. The hook needs no attention either way
     (§2's caveat: armed it stays armed; expired it has already written).
5. **Free play until the session reaches at least 15 minutes of total play** —
   P1's floor. The hook window ending does not end P1/P4 scoring (both are
   server-side); `--hold 2400` leaves ~25 minutes of headroom past the scripted
   phases.

## 4. Predictions, registered before the run

Restated from §1z-d.3 with §1z-e.5's revisions, which are their authority.

| # | Prediction | REFUTED IF | Floor |
|---|---|---|---|
| P1 | **Healthy branch**: zero `[plane-repair]` fires; the JSONL `plane_repair_due` ladder never reaches `plane-lock`; zero `plane_echo` rows expected (the 0/285 census) | a fire in a session where the operator never experienced a stuck body — the 9/198 false-fire class made real (§1z-e saw zero such fires in 109 sessions, so one here is news). NOT a refutation: a fire manufactured by a sustained edge-hold the operator was told not to do (§3.3 — report it separately); a `plane_echo` row **without** a fire (the tripwire watching a carry mid-flight — cross-check §C's carry episodes and report it, it refutes nothing by itself) | ≥15 min of play including the full §3 sequence |
| P2 | **The wall-press control**: no fire and no `plane-lock` transition during the press — `plane-legal` disarms every report of a frozen body on a legal plane | a fire (or a `plane-lock` ladder row) during the press — the freeze test alone can trip on blocked movement, in a way 109 replayed sessions never exercised | one press held ≥8 s **whose report stream is visible in the JSONL** (§5's exposure check: ≥8 s of accepted byte-identical 0x003D rows in the press window; no stream ⇒ P2 UNREAD, not passed) |
| P3 | **Exposure**: `noclipscore.py` section C on the r6 bin shows stacked-ground samples > 0, from the bridge round trips | — (a floor, not a hypothesis: stacked = 0 means the deck case was not exercised, and P1's echo half is UNREAD, not passed — zero exposure is not a null) | ≥6 deck/under-deck crossings |
| P4 | **Lock branch, conditional**: the due-ladder reaches `plane-lock` within ~5 s of continuous mash; numbered fires at most every 10 s; **the body walks on the first release-paused click after fire #1**, and continued play shows no further fires | repeat fires with a live stream, or movement NOT resuming on release-paused clicks → the agent+0x80 heal reconstruction is refuted (the trigger is not — §1z-e.5: a single fire followed by giving up confirms NOTHING, which is why §3.4 says keep playing). NOT a refutation: a heal-click whose JSONL verdict is `kbd-drop` — that click never reached the walker; the probe is void and the next release-paused click is the real one | opportunistic — no lock means P4 is UNREAD, not passed, and that is the expected outcome |

**No lock is the likely result and it still scores**: P1+P2+P3 make one healthy
prospective session under the shipped default — the specificity claim's first
live data point that is not a replay.

## 5. Scoring, after the run

The gamesrv log is the primary readout — it persists at the harness capture dir
terminal 1b tailed (fires and echoes print there; healthy is silence). Then the
session's own JSONL — the newest gamesrv capture; **check the filename's
timestamp is this run's start** before believing it, a parallel session's
capture can be newer (this line is PowerShell-tested; the bare substrings
deliberately match all three row kinds):

```
python -c "import glob,os; p=max(glob.glob(r'vault/captures/gamesrv/authsrv-*.jsonl'), key=os.path.getmtime); print(p); [print(l.strip()[:220]) for l in open(p,encoding='utf-8') if 'plane_repair' in l or 'plane_echo' in l]"
```

A healthy session shows a `plane_repair_due` ladder that never reaches
`plane-lock` (transitions like `plane-legal`/`arming` are normal churn), zero
`plane_echo` rows, and zero `plane_repair` rows.

**P2's exposure check**: in the same JSONL, the `position_report` rows
(source 0x003D, accepted) inside the noted press window must repeat one
byte-identical coordinate for ≥8 s. No such stream ⇒ the blocked client went
quiet and P2 is UNREAD.

**If a lock happened**: pull every row in a ±60 s window around the fire (any
JSON reader; `vault/research/movecode/plane-sweep/` shows the patterns) and
check the heal click's verdict row — a `kbd-drop` voids that click as a heal
probe (§3.4's release-pause protocol exists precisely for this; the next
release-paused click is the probe).

The client side, plane channel first (section C is the one that can see a deck;
A and B come free; the default `--map-fid` is already map 280's mesh):

```
python toolkit/clientscan/noclipscore.py --bin vault/research/movecode/r6/movehook.bin
```

```
python toolkit/clientscan/movehook/readhook.py --bin vault/research/movecode/r6/movehook.bin
```

Report with: the fire count (with numbers, times, planes if any), the echo rows
(expected zero; any present cross-checked against §C's carry episodes), the
due-ladder transitions around any event, section C's stacked and anomaly
counts, P2's exposure verdict, and — if a lock happened — the operator's own
words for what the body did after each release-paused click. That last sentence
is the heal's verdict; no instrument substitutes for it.

## 6. The COMPLETION RUN (R6b) — after §1z-f scored the first execution

> **RAN 2026-08-29, scored — [FINDINGS §1z-g](FINDINGS.md). P1 MET** (16.33
> min, zero fires, ladder never armed, echoes 30/797 all at the glitch
> structures). P2 unread and proposed retired (both disarm clauses now have
> live demonstrations from natural play). **The run's landmark was unplanned:**
> an off-mesh S-press stuck — a SECOND lock class the repair structurally
> cannot see — whose recovery corroborated the heal mechanism live (a routed
> grant's plane word revived the dead walker in 81 ms), and the follow-up
> census showed all three historical locks received ZERO fresh plane words
> while locked. The repair's premise now has its evidence; its first fire is
> still owed.

The first execution (§1z-f) left two floors short: P1 needs ≥15 minutes of
play (R6 gave 7.8) and P2's wall slid instead of pinning. This section is that
completion, simplified — **no bridge phase is required** (P3 is MET; more
carry exposure is free bonus, not a floor) and there is nothing to provoke:
the run is ordinary play, at length.

**The hook is ON as lock insurance, not for any registered floor.** P1's whole
readout is server-side, so `movehook` buys nothing this run is scored on —
but a lock is the one event that cannot be scheduled, and with the hook armed
a heal gets its MECHANICAL witness: r5stuck's client-side signature was 49
clicks and queries with **zero** `agapi_setdest`/`chcli_advance`, so a
post-fire click that makes the walker sites fire again is the walker
demonstrably reviving — the nearest thing to §4.2's RETURN-tap answer the
current instrument can give. Skipping the hook loses only that; if the
two minutes of overhead are unwanted, run without it and a lock still scores
per §3.4 (server-side + the operator's words).

Terminals 1 and 1b: identical to §2. Terminal 2, **armed right after you are
in the map** (no bridge-arrival wait — there is no exposure phase to cover),
with a FRESH out dir — never re-point at `r6`, the first run's capture lives
there:

```
python toolkit/clientscan/movehook/attach.py --minutes 16 --out vault/research/movecode/r6b
```

(16 min covers the 15-min floor from map entry; ring-safe — 32,768 records at
16 min tolerates a 34 rec/s average against a measured corpus peak of ~30,
and an ordinary session idles more than R6's bridge phase did. Ring-full is a
truncation that still writes the bin, not a loss.)

Play: **at least 15 minutes of ordinary walking and clicking, timed by the
clock, not by feel.** Optionally, ONE more P2 attempt — a concave corner
(two walls meeting) rather than a flat wall face, ~10 s, wall clock noted;
if the body slides again, P2 is dropped at this site and that is the answer
(one attempt, not a hunt — the control is optional, the floor is not). If the
body locks, §3.4's protocol applies unchanged, release-paused clicks and all.

Scoring: §5 unchanged (the one-liner, the ladder, the press-window check if
attempted; with the hook on, `noclipscore.py --bin
vault/research/movecode/r6b/movehook.bin` comes free). The healthy-branch
deliverable is one line: ≥15 min, zero fires, ladder never armed — P1's floor
finally met on a prospective session.
