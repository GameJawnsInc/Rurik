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
  Attempt 2 (38833 client via `--exe
  vault/run/2026-08-13_64fae3b1369b/Gw.exe`, map 449): **the client loaded
  the map and took the entire burst through `INSTANCE_LOAD_FINISH`** — then
  OUR gamesrv's handler died: `authsrv.py:6884` `NameError: HERO_ATTRIBS`,
  dead socket, `Code=007` on screen. That is the heroes-party commit at
  `main`'s tip (`c96242f`): `HERO_ATTRIBS`, `HERO_SKILLBAR` and
  `HERO_BODY_NPC` are assigned only inside the `--hero` CLI block with no
  module-level default, and the load path evaluates `HERO_ATTRIBS`
  unconditionally — so **every loopback instance load on current main
  crashes**, probes or not. The fix belongs to the heroes arc (in flight,
  worktree `sleepy-cartwright-4143ba`); once it lands, relaunch with the
  38833 `--exe` line above. PLAN.md's rule held: the client was innocent
  both times until the gamesrv log said otherwise.

### Result (fill in)

- Date/build:
- Terminal showed 6/6 steps:
- Kurzick / Luxon / Balthazar / Imperial rows read:
- Verdict:

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

### Result (fill in)

- Date/build:
- Terminal showed 5/5 steps (or last step printed before a crash):
- Row present after step 2? Name shown (Rurik vs real title):
- Progress target shown (1000 / 8400 / other):
- At-rest points (6000 / 4200 / no row):
- Nameplate after step 4:
- Step 5: second row's visible numbers, or assert text verbatim:
- Verdict:
