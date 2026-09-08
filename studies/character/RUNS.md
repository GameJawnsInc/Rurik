# Character-storage probe runs

Run sheets for the two probes [STORAGE.md](STORAGE.md) built on 2026-08-16.
Owner-driven, loopback, one probe per session. Both are Hero-window
experiments: no combat, no clicks beyond opening panels, default map. Results
get filled in below, then folded into STORAGE.md §2/§3 with labels.

Both probes' predictions are printed by the gamesrv at run time
(`--list-probes` shows them offline). The terminal echoes every step with its
own "watch" line — follow along there. **Before believing any result, confirm
the terminal printed all of the probe's steps** (6 for `faction_max`, 5 for
`title_track`) — a probe that half-ran looks like a refutation.

One mechanic bites both runs: **the Hero window does not live-refresh.** A
panel open while a packet lands keeps showing the old state. Close and reopen
it at every read point.

**Both runs must pass `--map 449`** (Kamadan, our authored area). The first
attempt (2026-08-16) was refused by the content-id preflight: maps 146/148
currently load from NO client archive in the vault — the 38797 run dirs hold
`0x1B97D` only in its bit-31 mid-replacement spelling, and the 38833 copy
binds a file the terrain arc rewrote (`studies/quests/AUTHORING.md` §"free
riders", where fixing it is already named prior work). Map 449 agrees across
both archives — preflight verified green with `served={449}` against the
exact archive the harness selects. Kamadan is an outpost in the client's own
area table, so the title-display step keeps its staging-area chance.

> **Update 2026-08-16, later:** the canonical 38797 archive is repaired —
> `datwrite --relink-plain 0x1B97D` re-bound the plain id to row 7982, and the
> preflight is green for 146/148 against the archive the harness selects by
> default, so `--map 449` is no longer forced for default-selection runs. It
> **is** still required for a run passing an explicit 38833 `--exe`: that
> generation's file differs from `dat_study`'s bytes (a same-generation
> `RURIK_DAT` also clears it). Also corrected: the 38833 copy's file is
> ArenaNet's own 38833 build — sha-identical to the pristine snapshot and its
> run-live copy — not a terrain-arc rewrite. Neither probe's procedure needs
> to change; `--map 449` stays valid either way.

---

## Run 1 — `faction_max`

```bash
python toolkit/harness/session.py --keep-open --shots 5 --game-args '--probe faction_max --map 449'
```

Ignore the "a --probe is running in a world with NO HOSTILE" warning — this
probe fights nothing. The harness logs in by itself (synthetic account,
loopback); hands off keyboard and mouse during its countdown. Steps land at
roughly +3s (the `0x00E9` legend), +9..+12s (the four maxima), +24s (Kurzick
re-sent as 31000).

**Nothing has to be read mid-run.** After the terminal prints step 6, open
the Hero window → Faction tab and read at leisure — the end state answers
every question:

| Row | Predicted | If instead… |
|---|---|---|
| Kurzick | **1001 / 31000** | `/ 21000` = the client latched the first cap and ignores later ones; `/ 0` = `0x00EA` did nothing |
| Luxon | **1003 / 22000** | |
| Balthazar | **1011 / 23000** | `/ 24000` here (and 23000 on Imperial) = the EC/ED naming is swapped — note it, that is a measurement |
| Imperial | **1005 / 24000** | |
| All four | | still `/ 0` everywhere = the cluster reading is refuted outright |

Hold the tab open a few seconds so `--shots` catches it, note the capture
directory the harness prints, then close the client.

### Attempts

- **2026-08-16, twice, neither a probe result — both diagnosed.**
  Attempt 1 (38797 client, map 449): client hung up right after `0x0199` —
  the 38797 run archive cannot satisfy a 449 load (the load burst never got
  past the map id; same family as the 146/148 condition, different row).
  **← CORRECTED by `93523b8` (recorded here 2026-08-18): the archive reading
  was WRONG.** That commit measured the 38797 archive binding `0x345CC`
  byte-identical to `dat_study`, so the NameError below explains attempt 1
  too — "a server-side NameError and a bad map row present IDENTICALLY from
  the client's side" is that commit's own sentence, earned at this session's
  expense. One diagnosis, two attempts, and the archive was innocent
  throughout.
  Attempt 2 (38833 client via `--exe
  vault/run/2026-08-13_64fae3b1369b/Gw.exe`, map 449): **the client loaded
  the map and took the entire burst through `INSTANCE_LOAD_FINISH`** — then
  OUR gamesrv's handler died: `authsrv.py:6884` `NameError: HERO_ATTRIBS`,
  dead socket, `Code=007` on screen. That is the heroes-party commit at
  `main`'s tip (`85fd12b`): `HERO_ATTRIBS`, `HERO_SKILLBAR` and
  `HERO_BODY_NPC` are assigned only inside the `--hero` CLI block with no
  module-level default, and the load path evaluates `HERO_ATTRIBS`
  unconditionally — so **every loopback instance load on current main
  crashes**, probes or not. The fix belongs to the heroes arc (in flight,
  worktree `sleepy-cartwright-4143ba`); once it lands, relaunch with the
  38833 `--exe` line above. PLAN.md's rule held: the client was innocent
  both times until the gamesrv log said otherwise.

### Result — RUN 2026-08-18, agent-piloted, ALL FOUR QUESTIONS ANSWERED

- **Date/build:** 2026-08-18, build 38797 (default client selection, default
  map — Ascalon City post-relink), harness `20260818T112259`, agent-piloted
  end to end: `--actions '0:play 45:key:h'`, no operator, no clicks. The
  Hero window opened already on the Faction tab, so the planned phase-B tab
  click was never needed.
- **Terminal showed 6/6 steps** — each verified in the gamesrv log before
  reading a pixel. RUN VERDICT: PASS; teardown clean.
- **Rows read (frames hold003 and hold022, identical 76 s apart):**
  Kurzick **1,001 / 31,000** · Luxon **1,003 / 22,000** · Balthazar
  **1,011 / 23,000** · Imperial **1,005 / 24,000**.
- **Verdict — OBSERVED, all predictions hit:**
  1. `0x00EA`–`0x00ED` fill the four denominators that read `/ 0` on every
     prior run.
  2. The opcode→bar mapping is ldufr's naming exactly: EA=Kurzick,
     EB=Luxon, EC=Balthazar, ED=Imperial — no swap.
  3. Kurzick shows **31,000**, the step-6 re-send: a cap moves mid-session;
     the client does not latch the first value.
  4. In-frame controls all held: numerators are legend fields 1/3/5/11,
     level 17, 424,242 xp, skill points 1,013 — the known `0x00E9` field map
     re-confirmed in the same frame.
- **Free rider for Run 2:** the Hero panel's tab bar reads
  `Faction | Titles | Account`; the **Titles** tab center measures
  ≈ `(0.816, 0.263)` in window fractions (1936×1048 frame) — the click
  target an agent-piloted `title_track` run needs.

---

## Run 2 — `title_track`

```bash
python toolkit/harness/session.py --keep-open --shots 5 --game-args '--probe title_track --map 449'
```

Kamadan is an outpost — a *staging area*, which is the one place GWW says a
displayed title renders under a nameplate — so step 4 keeps its best chance.
(The original sheet said to use the default map, Ascalon City; that map
cannot load from any current client archive, see above.)

Steps land at ~+3s (`0x00F3` tier seed — nothing visible predicted), ~+11s
(`0x00F6` track for title 7), ~+21s (`0x00F5` update to 6000), ~+31s
(`0x00F4` display), ~+41s (the out-of-range legend track — LAST because it
may assert, and by then everything else is already measured).

Read points, in order:

1. **~+15s, optional but valuable:** Hero window → Titles tab (reopen it).
   Is there a track row? Note its **name** — our literal `Rurik`, or a real
   title name the client resolved from its own 48-row table? That single bit
   is the sharpest in the run. Note its numbers: 4200 progress, and whether
   the target reads **1000 or 8400** (the two rival field-namings disagree;
   whichever renders names its lineage).
2. **Missed the window? The at-rest state still discriminates:** a row
   reading **6000** = both `0x00F6` and `0x00F5` work; stuck at **4200** =
   the update message is dead; **no row at all** = the track message is dead.
3. **After step 4 (~+31s):** target/hover your own character. Any text under
   the nameplate? (Silence here is weak evidence — the word field could be
   player number or agent id, ours are both 1 — but any change is signal.)
4. **After step 5 (~+41s):** reopen the Titles tab. Either a second row
   whose numbers (9002…9009) name their own fields — settling the
   ldufr/GWCA naming dispute — or the client asserts.

**If the client crashes: copy the assert dialog verbatim before dismissing
it** — module, line, expression. That names the unchecked tier-index
consumer, which is the best possible output of step 5. The run directory's
`crash-dialog.txt` captures it too; note which step was the last one printed.

### Result — THREE RUNS 2026-08-18, agent-piloted; answered except one loose end

**Run 1 (harness `20260818T113252`): instant `Code=007` on the original
step 1** — a clean client hangup the moment `0x00F3` landed, no assert. The
step's own watch text had named this outcome as its own result.

**Run 2 (harness `20260818T113658`): the one-variable ladder convicts the
string, and the stress step names its consumer.** Verbatim retail bytes
(`[0,0,0,0x0101]`) ACCEPTED; our ids/values with retail's string ACCEPTED;
our 7-unit template literal ACCEPTED — so run 1's killer was the 8-unit
literal sitting exactly at the `string16(8)` cap: **the field admits at most
7 units on receive; at-cap is an instant hangup** (off-by-one / terminator
semantics — measured for `0x00F3`; other string16 fields untested at cap,
and every prior literal in this repo rode far below its cap). All later
steps accepted too. Then the stress record — rank ids 9006/9009 referencing
no `0x00F3` record — was **silent on receive and fatal on first render**:
the Hero window's first open died on `Assertion: index < m_count`
`Array.h(587)`, build 38797, full dump captured (`crash-dialog.txt` in the
capture), stack rebasing into the AttribTitles render path and the
`ctx+0x81C` accessor neighborhood `studies/newopcodes` measured. **Server
rule: never ship a `0x00F6` referencing ranks you have not sent** — same
class as the buffId constraint (`studies/reconstruction` §2.9.5). The
stress step is retired from the probe (question closed; a guaranteed crash
in a registered probe is a hazard).

**Run 3 (harness `20260818T114312`): the render, OBSERVED.** Stress step
removed, 7/7 steps sent and verified, client alive throughout. Frame
`3-click.png`: the Titles tab shows our track — row label **"Ruri (1,000)"**,
bar reading **6,000**, filled ≈ 6000/8400.
- The row's NAME is the **current rank's `0x00F3` string** — ours, not a
  `s_titleClientData` entry. Prediction refuted, and the better outcome:
  **title rows are fully wire-authorable, name included**; the compiled
  48-row table constrains the title *id space*, not the display text.
- The parenthesized **1,000** is rank 1's field-3 value as we sent it;
  whether retail renders that field as a threshold or a rank number there
  is OPEN (retail's `[364, 0, 4]` reads either way).
- The bar's denominator is the **next-rank minimum** (field 8) — 6000/8400
  visibly, confirming the field map's reading.
- `0x00F5`'s update is what the bar shows (4,200 was never rendered; 6,000
  was) — the patch works, gated on the prior `0x00F6` as measured.
- **Loose end:** `0x00F4`'s under-nameplate display is still unread — the
  scripted self-click at `(0.50, 0.62)` became a ground move-order (green
  marker, no target frame). Needs a real self-target (owner click, or a
  future click calibrated on the model's pixel), in a staging area, with a
  rank record bound. Weak-evidence question anyway: our player number and
  agent id are both 1.
