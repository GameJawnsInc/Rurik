# Wire order and build in the live readers — two latent defects from DIVERGENCE-D13.4

**Written 2026-10-07.** Both defects were found by the `DIVERGENCE-D13.4` lane
([../divergence/FINDINGS.md](../divergence/FINDINGS.md) D13.4, review RV-2) and fixed here.
Claim labels are the vocabulary in [../character/FINDINGS.md](../character/FINDINGS.md):
OBSERVED, UPSTREAM, RECONSTRUCTION, CORROBORATED, CONTESTED, UNVERIFIED, NOT FOUND.

**Identifiers.** `WIREORDER-A<n>` = the decode_conn ORDER defect and what was measured
about it. `WIREORDER-B<n>` = the BUILD-drop defect. `WIREORDER-P<n>` = a prediction
registered before the differential ran. Convention:
[studies/idents/CONVENTION.md](../idents/CONVENTION.md).

**Headline.**

- **A.** `livewire.decode_conn` sorted its merged stream by segment time. That time runs
  backwards inside s2c on 41 of 127 live connections, so the sort was not wire order.
  It now keeps each direction in wire order (`livewire.interleave`).
- **Effect of the fix.** All 29 tests that reach `decode_conn` keep every verdict and
  every check label. Two printed details move: one is a correction, the other only the
  print order of the same counts. The one published table that moves,
  `retail_c2s.json`, loses its time-sort artefacts.
- **B.** Four readers that re-time a tape dropped its client build, and four smaller
  sites did the same. All eight now keep it, and `test_tape.py` §11 reddens if any of
  the four readers drops it again.

---

## WIREORDER-A1 — what the time sort did (OBSERVED, 2026-10-07)

Measured over the live corpus: 128 game connections in the 32 live captures that carry
one (38 live capture directories in all). 127 of them close their byte accounting; the
one declared gap, 20260928T103123 :65009, is set aside by its manifest.

| | |
|---|---|
| connections whose s2c segment clock steps BACK in TCP-sequence order | **41 of 127** (c2s: 0) |
| backward steps | 53, of 0.04–14.0 ms (median of the per-connection max 2.0 ms) |
| where | **51 of 53 in the first ~1 s of the connection**, the map-load burst; the other 2 both on 20260810T235916 :61193, at 3.0 s and 34.2 s |
| s2c messages the sort moved out of wire order (n − LIS) | **3,495** of 350,851 s2c messages; led by 0x015E 601, 0x009F 294, 0x0020 290, 0x00F0 249, 0x00A6 162, 0x00B0 144, 0x00B1 140, 0x003C 140, 0x0048 139 — load-burst traffic |
| c2s messages with a DIFFERENT set of s2c messages ahead of them, time sort vs wire order | **0** (every connection) |

**Why the clock steps back.** In `wire.jsonl` the capture's own timestamps are monotone
in line order, which is arrival order. That held on all five connections checked
(:55934, :51534, :60935, :61193, :58557). For all 9 backward steps on those five, the
segment that follows in TCP sequence was written EARLIER in the file.

- **OBSERVED:** the segments reached the capture point out of sequence.
- `tape._segments` correctly keeps the FIRST arrival per sequence number.
- **UNVERIFIED:** whether the network or the capture layer reordered them.

**What the sort broke.**

- The manifest family on two connections (D13.4 RV-2):
  - 20260916T213125 :51534: a `0x0196` body lands where no phase is open, and
    `manifestbody.rebuild` refuses it (MsCliMan:457).
  - 20260929T150923 :55934: a kind-0 DONE moves ahead of the kind-2 bracket. It closes
    two empty buffers, and the 17 + 504 body bytes after it are never closed.
- Four load-time c2s requests were credited with the wrong "first reply" (A4).

## WIREORDER-A2 — who consumes `decode_conn` (static, four read-only Sonnet recons)

Inventory:

- **55 files call `decode_conn` in code.** These were found with the AST, not a text
  grep, so prose citations do not count.
- **29 tests reach it**, through those files or by calling it themselves.
- The differential shim counted calls, and all 29 actually called it (3–296 calls each).
- Two studies scripts are imported by a test: `stalepair_retail` (test_stalepair) and
  `swingcensus` (test_playerswing).

How each consumer relies on order:

| reliance | consumers (tests in **bold**) |
|---|---|
| ORDER-FREE (counts, sets, own re-sort) | `henchjoin.whose_agent`/`party_of`, `adrenjoin.whose_agent`, `meleecensus`, `swingcensus.retail` (re-sorts), `rlib`, the two c2s-only movement-2026-09-04 scripts, **test_livewire** §3 counts |
| WITHIN-DIRECTION order (first/last of a kind, s2c state machines, adjacency, brackets) | `adrenreplay`, `chainjoin`, `instantjoin`, `latehitjoin`, `pressstopjoin`, `attackskilljoin`, `walkstartjoin`, `swingclockjoin`, `swingcanceljoin`, `reachjoin`, `risejoin`, `timingjoin`, `weaponcensus` (`launch_events`, `hands_timeline`), `routerbench`, `castethogram`, `noticeradius`, `leashreturn`, `h_core`, `chasercensus`, `tick_pairing_census`, `stalepair_retail`; **test_skillloadorder, test_visstatus, test_purse, test_maxdeclare, test_questflow, test_itemmoves, test_maptravel, test_approachroute, test_smsgnames3, test_townweapon, test_damagelatch, test_daggers** |
| CROSS-DIRECTION (the first s2c after a c2s) | `c2striage`, `kbdclickjoin`, `pressstopjoin`, `floorcensus`, `operandcensus`, `parkedcopy`, `stillwindup`; **test_c2striage, test_heroenergy, test_deadbout, test_pendskill** |
| EQUAL-`t` = "same segment" | `weaponcensus` ties, `routerbench.hold_verdict` (1e-6), `shoutjoin` (`announce_t == t`), `instantjoin` (`dt_same`), `adrenreplay` (`last_core == t`), `stalepair_retail` (`gap == 0`), `tick_pairing_census`; **test_questflow, test_maxdeclare, test_purse, test_itemmoves §7b, test_smsgnames3, test_weapons, test_approachroute** |
| MONOTONE `t` (bisect, early break, two-pointer) | `routerbench` (`player_agent`, `heading_clip_agreement`), `shoutjoin.observer_of`, `instantjoin`, `henchjoin.scan`, `floorcensus`, `parkedcopy`, every early-`break` scan above |

Static exposure is broad. Whether it MOVES a number depends on where the reordered spans
fall, and they fall almost entirely in the first second's load burst (A1). That is
something only a run can settle, so the next section ran one.

## WIREORDER-P1..P3 — predictions, registered before the differential ran

Written to the session scratchpad before either arm ran, and copied here verbatim in
substance:

- **P1** No test's verdict changes under either arm.
- **P2 (raw)** Every retail-census line of the 29 tests stays identical, except possibly
  in readers of load-burst order.
  - Candidates: test_skillloadorder, test_itemmoves, test_questflow, test_purse,
    test_townweapon, test_weaponcensus, test_visstatus, test_maxdeclare, test_smsgnames3.
  - Expected: at most 3 of these change a printed line, and ZERO of the
    combat/movement joins change.
- **P3 (clamp)** Clamp changes a superset of raw's lines. The extras would appear only
  where a reader uses a displaced load-burst message's `t` as an interval end or in an
  equality.

**Decision rule, stated with them.**

- **Both arms leave every retail number:** fix with **raw**. Clamp invents a time and
  gives two segments one, and the equal-`t` readers above treat that as "same segment".
- **Raw moves a number:** classify each line as CORRECTION or BREAK. A BREAK is fixed
  in its reader, never by re-sorting.

## WIREORDER-A3 — the differential (OBSERVED)

**Harness.** A shim swaps `livewire.decode_conn` in-process and runs each test via
`runpy`. Four arms ran:

- **old**: a verbatim copy of the HEAD sort. It equals HEAD `decode_conn` on 128 of 128
  connections.
- **old2**: the same code again, for the noise floor.
- **raw**: wire order per direction, `t` verbatim, heads interleaved.
- **clamp**: wire order with `t` raised to the running maximum.

Comparison is check-line by check-line: verdict + label as a multiset, and the detail
string wherever old and old2 agreed. The noise is the server simulation's unseeded
`random.randint` damage rolls, temp paths and wall clocks.

**Order equivalences.**

- raw and clamp give the same ORDER on 128 of 128 connections.
- The committed `decode_conn` equals the raw arm on 128 of 128, and differs from the
  time sort on exactly 41.

| result | raw | clamp |
|---|---|---|
| tests run / green | 29 / 29 | 29 / 29 |
| verdict + label multiset and banner identical to old | **29 of 29** | **29 of 29** |
| stable details identical | 26 of 29 | 26 of 29 |

The three detail moves are the same in both arms:

- **test_skillloadorder — CORRECTION.** On 20260929T150923 :59969 the first
  `0x00DA`/`0x00DB` sit at s2c index **145/151** in wire order. The time sort put them
  at 252/258: 107 messages from later segments had sorted ahead of them. The claim
  ("first 0x00DA precedes first 0x00DB, 11 of 11"; "0x001D before the pair on :59969")
  holds either way.
- **test_visstatus — no number moved.** The same four counts (860 / 1600 / 68 / 62)
  print in a different first-seen order.
- **test_playerswing — NOISE, proven.** The "walks out of reach" synthetic swing's
  damage is an unseeded roll. Under the OLD order it came out 97, 97, 95, 96 over four
  runs, against 96 in both arms.

**Score.** P1 HELD. P2 HELD: two load-burst readers moved a printed detail and no
combat/movement join moved. P3 was WRONG in the harmless direction: clamp moved exactly
what raw moved, no more. So the decision rule picks **raw**, and that is what is
committed.

## WIREORDER-A4 — a published table the tests do not check: `retail_c2s.json` (OBSERVED)

`c2striage.census` credits each c2s request with the first s2c message after it.
`test_c2striage` compares the committed table's opcode set and counts, which c2s never
moves, so it stays green. The reply columns, however, do move.

Four c2s opcodes sent during the map load sit directly in front of a reordered span. On
the current corpus, old order → wire order:

| c2s | first_reply, time sort | first_reply, wire order | reply p50 |
|---|---|---|---|
| 0x000A | 0x0144 24, 0x0186 5, 0x000D 2, **0x0196 1** | 0x0144 25, 0x0186 5, 0x000D 2 | 41.2 → 41.2 ms |
| 0x000B | 0x0144 24, 0x0186 5, 0x000D 2, **0x0196 1** | 0x0144 25, 0x0186 5, 0x000D 2 | 41.2 → 41.2 ms |
| 0x0090 | 0x01AD 56, 0x001D 29, 0x000F 28, **0x0057 3, 0x006D 2, 0x015E 1, 0x009F 1** | 0x01AD 58, 0x000F 32, 0x001D 30 | 38.8 → 39.1 ms |
| 0x0091 | 0x0144 117, **0x0197 2**, 0x000D 1, **0x0196 1** | 0x0144 120, 0x000D 1 | 40.0 → 40.0 ms |

Every bolded "reply" is a message from a LATER segment that the sort moved ahead. Two of
them are the manifest body and DONE.

**The committed file was NOT regenerated here.** It is from 2026-09-29: 116 connections
in 31 captures, against today's 127. A `--write` would fold that growth into this
change. Its next `--write` reads wire order and drops the bolded artefacts. Until then,
its 0x0196/0x0197/0x0057/0x006D/0x015E/0x009F "first replies" to those four requests
are time-sort artefacts, not retail.

## WIREORDER-A5 — the consumers no test runs (OBSERVED)

**What ran.** Every CLI that calls `decode_conn`, under the same shim: old, old2 (noise
floor), and the committed fix. Each comparison is its stdout, line by line.

- The `toolkit/authsrv` joins: `attackskilljoin`, `kbdclickjoin`, `latehitjoin`,
  `pressstopjoin`, `henchjoin`, `swingclockjoin`, `swingcanceljoin`, `reachjoin`,
  `risejoin`, `walkstartjoin`, `chainjoin`, `instantjoin`, `shoutjoin`, `timingjoin`,
  `weaponcensus`, `adrenreplay`, `c2striage`; and `routerbench`.
- The studies scripts: `castethogram --no-save` (its default writes into the vault),
  `noticeradius`, `leashreturn`, `meleecensus`, `floorcensus`, `operandcensus`,
  `parkedcopy`, `stillwindup`, `swingcensus`, `stalepair_retail`, the four `h_*`
  scorers, `c_retail_sametick`, `r_windup_follow`, `r_death_any`, `chasercensus`, and
  the three movement-2026-09-04 scripts.

None of the 38 had a noise line between old and old2.

**Results.**

- **36 of 38 print byte-identical output.** That includes every tool whose docstring
  census the static read flagged as exposed:
  - `swingclockjoin`, `swingcanceljoin`, `walkstartjoin` ("release first"),
    `pressstopjoin`, `kbdclickjoin`, `latehitjoin`
  - `castethogram` (the re-cast latency)
  - the monsterai leash and notice tables
- **Read that precisely.** Wire order moves none of the numbers these tools print
  today. Whether today's numbers still equal the figures their docstrings quote from a
  smaller corpus is a different question, and this does not answer it.
- **`c2striage`** moves exactly the A4 rows.
- **`tick_pairing_census`** (unpromoted, no test) moves three lines:
  - its CONTROL (non-tick s2c with a tick ≤ 3 ms before): 88,723 → 88,263, 37.12 % →
    36.92 %
  - its bare-tick count: 43,242 → 43,245, with the matching histogram cell
  - None of these is cited anywhere. The figures `MOVEMENT-2026-09-04.md` publishes
    (93.5 %, 39.2 %, 43,457 ticks) come from lines that did not move, and they are
    from the 2026-09-04 corpus anyway.
- **`zaishenrun --prefix --rows`**: byte-identical (A6).

- **`routerbench --census` (155 lines) and `--score` (80 lines)**: byte-identical
  (old = old2 = fix). This is the one consumer built on a monotone two-pointer over
  `t`; its default run only prints usage, so it was run with both flags.

## WIREORDER-A6 — the fix, and the contract it leaves

**What changed.** `decode_conn` returns `interleave(c2s, s2c)`:

- Each direction keeps the order `build_events` + `tape.decode_all` hand over, which is
  TCP sequence.
- At every step, the head with the smaller `t` goes first, c2s on a tie.
- It is never a sort.
- `t` is the segment's capture time, verbatim, so it **may step back** by a reordering's
  width inside s2c.

**Why not clamp.** Clamping (raising `t` to the running maximum) was measured and
refused (P3, decision rule). It changes no test result here. But it manufactures a time,
and it merges two segments' `t` into one for every equal-`t` reader in A2.

**What the reader owns.** A reader that needs a non-decreasing clock now owns that need.
Today that costs nothing measurable: 51 of the 53 dips are inside load bursts, and every
bisect and early-break reader above produced identical output (A3, A5).

**Tests** (`test_livewire.py`, floor 18 → 23, red 4 of the 5 new checks against the
pre-fix `decode_conn`, measured):

- **1b.** A capture built in the test (bare machine): the second s2c segment was
  captured 10 ms EARLIER than the first.
  - `decode_conn` keeps it behind, with one c2s message interleaved.
  - KNOWN-BAD: the time sort applied to the same rows puts it ahead.
- **6.** Every closing live connection, each direction, against `build_events` +
  `decode_all`: 127 of 127.
  - The time sort differs on ≥ 41. This is a floor, because a newly reordered
    connection is good news.
  - Both D13.4 connections close every body byte through `manifestbody.rebuild` in
    wire order.
  - Under the time sort, :51534 is refused and :55934 strands 521 of 539 body bytes.

**Siblings fixed or marked.**

- `studies/monsterai/review/zaishenrun.py prefix_decode`: its own copy of the time sort,
  over the gapped connection's s2c prefix. The prefix has one backward step (0.16 ms, at
  segment 545 of 709).
  - Now `livewire.interleave`.
  - `--prefix --rows` output is **byte-identical** before and after, and the old run
    reproduced itself byte for byte.
- `studies/movecode/review/retail_conns.py`: `RURIK_LIVE_CACHE` pickles the decode. A
  pickle written before this change holds the time sort. A comment there says to delete
  it.
- `manifestbody.chain_streams` and `test_manifestbody.py` describe the sort in the past
  tense now. Their own known-bad arm re-sorts by itself, so it is unaffected.

---

## WIREORDER-B1 — four readers dropped the tape's build (OBSERVED, latent)

`tape.Events` carries the connection's client build, so `decode_all` reads a 38974 tape
in 38974's numbering. 38974 renumbered GAME_SMSG from 0x0194 up
(`codec.GAME_SMSG_RENUMBER`).

The four readers each rebase `load_tape`'s events onto the capture clock with a bare list
comprehension:

- `deepwoundjoin.sequence`
- `speedwords.sequence`
- `bufflog.read_effects`
- `damagepass.read_events`

The bare list drops `.build`, so their `decode_all` fell back to the caller's codec.

**Latent: there is no 38974 live tape yet.** The live corpus by connection build is:

| build | connections |
|---|---|
| unstamped | 12 |
| 38833 | 37 |
| 38849 | 12 |
| 38888 | 67 |

**The hazard is silent.** Schema 0x01C4 [word] goes on the 38974 wire as 0x01C5, which
is also a [word] in the pin. So the pin decode frames to the last byte and labels it
0x01C5.

**Fix.** `tape.Events.of(rebased, events)` in all four. `deepwoundjoin.sequence` alone
has ~20 callers (`aotjoin`, `healjoin`, `hexjoin`, `iaswindup`, `interruptjoin`,
`missjoin`, `rechargeprobe`, `spellhitjoin`, eight tests), and all of them now inherit
the right numbering.

**Same pattern, also fixed.**

- **`test_damagepass.py`**: an inline copy of the rebase.
- **`test_henchparty.py`**: a one-chunk list handed to `decode_all`.
- **`toolkit/schema/test_codec.py`**: the live round trip walks the whole corpus and
  decoded a joined blob with the caller's codec. It now uses `tape.codec_for(events, c)`
  for both decode and re-encode.
- **`zaishenrun.prefix_decode`**: `livewire._get_codec()` with no build. It now uses
  the connection's own build.

All of these are no-ops today: `Codec.for_build` returns the codec itself for every build
not in the renumber table.

**Test.** `test_tape.py` §11, floor 41 → 47, on a capture it builds itself:

- A premise check.
- Each of the four readers must hand `decode_all` an `Events` naming 38974 and read
  0x01C4 through a plain `Codec()`.
- A KNOWN-BAD arm reverts `Events.of` to a bare list and must read 0x01C5.
- Against the pre-fix readers it is **red 4 of 6**, measured with the HEAD files
  swapped in and then restored.

**Named and left, because they cannot meet a 38974 tape without an edit.** These decode
a joined blob with their own codec, but over NAMED pre-38974 captures:

- `test_npcdefs.py` §2
- `test_smsgnames.py`
- `test_killwindow.py`
- `test_loot.py` `_s2c`
- `test_tape.py` §4

`toolkit/harness/wiresplit.py` frames a fresh capture's plaintext with `Codec()` to
accept a key. On a 38974 capture that fails loudly (a refused key), not silently.
